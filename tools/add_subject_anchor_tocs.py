#!/usr/bin/env python3
"""Add page-specific anchor navigation to subject academy detail pages.

Only regional detail pages directly below the six ``과목별학원`` category
folders are targeted. The subject hub and category hubs remain untouched.
The table of contents reuses each page's visible H2 text and adds stable IDs
without rewriting visible copy, metadata, JSON-LD, or hidden representative
images. Missing map-image dimensions are also added so lazy loading cannot
move an anchor target after a visitor clicks the navigation.

Run this idempotent postprocessor again after regenerating subject pages.
"""

from __future__ import annotations

import argparse
import html
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "과목별학원"
SUBJECT_CATEGORIES = (
    "고등학생수학학원",
    "고등학생영어학원",
    "중학생수학학원",
    "중학생영어학원",
    "초등학생수학학원",
    "초등학생영어학원",
)
EXPECTED_PER_CATEGORY = 371

STYLE_MARKER = "<!-- subject-page-anchor-toc:style -->"
STYLE_HREF = "../../../assets/subject-anchor-toc.css"
STYLE_LINK = f'<link rel="stylesheet" href="{STYLE_HREF}">'
TOC_START = "<!-- subject-page-anchor-toc:start -->"
TOC_END = "<!-- subject-page-anchor-toc:end -->"

TOC_BLOCK_RE = re.compile(
    rf"^[ \t]*{re.escape(TOC_START)}\r?\n.*?"
    rf"^[ \t]*{re.escape(TOC_END)}\r?\n",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)
TOC_CAPTURE_RE = re.compile(
    rf"{re.escape(TOC_START)}.*?{re.escape(TOC_END)}",
    re.IGNORECASE | re.DOTALL,
)
SUBJECT_CSS_RE = re.compile(
    r'(?P<indent>^[ \t]*)<link\s+rel=["\']stylesheet["\']\s+'
    r'href=["\']\.\./\.\./\.\./assets/subject\.css["\']\s*>',
    re.IGNORECASE | re.MULTILINE,
)
H2_RE = re.compile(
    r"<h2\b(?P<attrs>[^>]*)>(?P<body>.*?)</h2>",
    re.IGNORECASE | re.DOTALL,
)
ID_RE = re.compile(r'\bid\s*=\s*(["\'])(?P<id>[^"\']+)\1', re.IGNORECASE)
ANY_ID_RE = re.compile(
    r'\bid\s*=\s*(["\'])(?P<id>[^"\']+)\1', re.IGNORECASE
)
SUMMARY_SECTION_RE = re.compile(
    r'<section\b(?=[^>]*\bclass=["\'][^"\']*\bacademy-summary\b[^"\']*["\'])[^>]*>',
    re.IGNORECASE,
)
TOC_LINK_RE = re.compile(
    r'<a href="#(?P<id>[^"]+)">.*?'
    r'<span class="subject-page-toc-text">(?P<label>.*?)</span>\s*</a>',
    re.IGNORECASE | re.DOTALL,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC_RE = re.compile(r'\bsrc\s*=\s*(["\'])(?P<src>[^"\']+)\1', re.IGNORECASE)
WIDTH_RE = re.compile(r'\bwidth\s*=\s*(["\'])(?P<value>\d+)\1', re.IGNORECASE)
HEIGHT_RE = re.compile(r'\bheight\s*=\s*(["\'])(?P<value>\d+)\1', re.IGNORECASE)
MEDIA_PREFIXES = (
    "../../../assets/centers/common/",
    "../../../assets/maps/",
)
JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def class_container(tag: str, class_name: str) -> re.Pattern[str]:
    return re.compile(
        rf'<{tag}\b(?=[^>]*\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'])[^>]*>',
        re.IGNORECASE,
    )


@dataclass(frozen=True)
class TargetSpec:
    target_id: str
    tag: str
    container_re: re.Pattern[str]


@dataclass(frozen=True)
class TocTarget:
    target_id: str
    text: str
    position: int


TARGET_SPECS = (
    TargetSpec("summary-title", "section", class_container("section", "academy-summary")),
    TargetSpec("facts-title", "section", class_container("section", "academy-facts")),
    TargetSpec("article-title", "article", class_container("article", "academy-article")),
    TargetSpec("faq-title", "section", class_container("section", "academy-faq")),
    TargetSpec("case-title", "section", class_container("section", "academy-cases")),
    TargetSpec("related-title", "section", class_container("section", "academy-related")),
)
TARGET_IDS = tuple(spec.target_id for spec in TARGET_SPECS)


def visible_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(text).split())


def detect_newline(source: str) -> str:
    if "\r\n" in source:
        if "\n" in source.replace("\r\n", ""):
            raise ValueError("Mixed newline styles")
        return "\r\n"
    return "\n"


@lru_cache(maxsize=None)
def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 24:
            raise ValueError(f"PNG dimensions not found: {path.relative_to(ROOT)}")
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid PNG dimensions: {path.relative_to(ROOT)}")
        return width, height
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"Unsupported image format: {path.relative_to(ROOT)}")
    offset = 2
    while offset < len(data):
        while offset < len(data) and data[offset] != 0xFF:
            offset += 1
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in JPEG_SOF_MARKERS:
            if segment_length < 7:
                break
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            if width <= 0 or height <= 0:
                break
            return width, height
        offset += segment_length
    raise ValueError(f"JPEG dimensions not found: {path.relative_to(ROOT)}")


def media_asset_path(src: str) -> Path | None:
    if not src.startswith(MEDIA_PREFIXES):
        return None
    relative = src.removeprefix("../../../")
    path = ROOT / Path(relative)
    if not path.is_file():
        raise ValueError(f"Local image is missing: {relative}")
    return path


def ensure_media_dimensions(source: str) -> tuple[str, int]:
    replacements: list[tuple[int, int, str]] = []
    matched = 0
    added = 0
    for image in IMG_RE.finditer(source):
        tag = image.group(0)
        src_match = SRC_RE.search(tag)
        if not src_match:
            continue
        src = src_match.group("src")
        asset = media_asset_path(src)
        if asset is None:
            continue
        matched += 1
        width_match = WIDTH_RE.search(tag)
        height_match = HEIGHT_RE.search(tag)
        if bool(width_match) != bool(height_match):
            raise ValueError(f"Only one intrinsic dimension is present: {src}")
        if width_match and height_match:
            width = int(width_match.group("value"))
            height = int(height_match.group("value"))
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid intrinsic dimensions: {src}")
            if src.startswith("../../../assets/maps/"):
                expected = image_dimensions(asset)
                if (width, height) != expected:
                    raise ValueError(
                        f"Intrinsic dimensions for {src} are {(width, height)}, "
                        f"expected {expected}"
                    )
            continue
        if not src.startswith("../../../assets/maps/"):
            raise ValueError(f"Body image is missing intrinsic dimensions: {src}")
        width, height = image_dimensions(asset)
        closing = " />" if tag.endswith("/>") else ">"
        trim = 2 if tag.endswith("/>") else 1
        replacement = tag[:-trim] + f' width="{width}" height="{height}"' + closing
        replacements.append((image.start(), image.end(), replacement))
        added += 1
    if matched != 2:
        raise ValueError(f"Visible local image count is {matched}, expected 2")
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source, added


def detail_pages() -> list[Path]:
    actual_categories = tuple(
        sorted(path.name for path in SUBJECT_ROOT.iterdir() if path.is_dir())
    )
    if actual_categories != tuple(sorted(SUBJECT_CATEGORIES)):
        raise ValueError(
            "Subject category folders differ from the expected six: "
            f"{actual_categories}"
        )
    result: list[Path] = []
    for category in SUBJECT_CATEGORIES:
        pages = sorted(
            path / "index.html"
            for path in (SUBJECT_ROOT / category).iterdir()
            if path.is_dir() and (path / "index.html").is_file()
        )
        if len(pages) != EXPECTED_PER_CATEGORY:
            raise ValueError(
                f"{category}: expected {EXPECTED_PER_CATEGORY} detail pages, "
                f"found {len(pages)}"
            )
        result.extend(pages)
    return sorted(result, key=lambda path: path.as_posix())


def container_heading(source: str, spec: TargetSpec) -> re.Match[str]:
    containers = list(spec.container_re.finditer(source))
    if len(containers) != 1:
        raise ValueError(
            f"Container count for {spec.target_id} is {len(containers)}, expected 1"
        )
    container = containers[0]
    closing = source.lower().find(f"</{spec.tag}>", container.end())
    if closing < 0:
        raise ValueError(f"Closing {spec.tag} not found for {spec.target_id}")
    heading = H2_RE.search(source, container.end(), closing)
    if not heading:
        raise ValueError(f"H2 not found for {spec.target_id}")
    return heading


def ensure_target_ids(source: str) -> str:
    for spec in TARGET_SPECS:
        heading = container_heading(source, spec)
        id_match = ID_RE.search(heading.group("attrs"))
        if id_match:
            if id_match.group("id") != spec.target_id:
                raise ValueError(
                    f"Target H2 for {spec.target_id} already has ID "
                    f"{id_match.group('id')!r}"
                )
            continue
        replacement = (
            f'<h2 id="{spec.target_id}"'
            + heading.group("attrs")
            + ">"
            + heading.group("body")
            + "</h2>"
        )
        source = source[: heading.start()] + replacement + source[heading.end() :]
    return source


def select_targets(source: str) -> list[TocTarget]:
    targets: list[TocTarget] = []
    for spec in TARGET_SPECS:
        heading = container_heading(source, spec)
        id_match = ID_RE.search(heading.group("attrs"))
        if not id_match or id_match.group("id") != spec.target_id:
            raise ValueError(f"Missing target ID {spec.target_id}")
        label = visible_text(heading.group("body"))
        if not label:
            raise ValueError(f"Empty H2 target {spec.target_id}")
        targets.append(TocTarget(spec.target_id, label, heading.start()))
    if [target.position for target in targets] != sorted(
        target.position for target in targets
    ):
        raise ValueError("Target order differs from the expected reading order")
    return targets


def ensure_style_link(source: str, newline: str) -> str:
    marker_count = source.count(STYLE_MARKER)
    href_count = source.count(STYLE_HREF)
    if marker_count:
        if marker_count != 1 or href_count != 1:
            raise ValueError("Existing TOC stylesheet marker is malformed")
        return source
    if href_count:
        raise ValueError("TOC stylesheet link exists without its marker")
    matches = list(SUBJECT_CSS_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"Subject stylesheet link count is {len(matches)}")
    match = matches[0]
    addition = (
        newline
        + match.group("indent")
        + STYLE_MARKER
        + newline
        + match.group("indent")
        + STYLE_LINK
    )
    return source[: match.end()] + addition + source[match.end() :]


def toc_markup(targets: list[TocTarget], indent: str, newline: str) -> str:
    child = indent + "  "
    grandchild = child + "  "
    item_indent = grandchild + "  "
    lines = [
        indent + TOC_START,
        indent
        + '<nav class="subject-page-toc" '
        + 'aria-labelledby="subject-page-toc-title">',
        child + '<div class="subject-page-toc-panel">',
        grandchild + '<div class="subject-page-toc-heading">',
        item_indent + '<p class="eyebrow">PAGE CONTENTS</p>',
        item_indent + '<strong id="subject-page-toc-title">학습 안내 목차</strong>',
        grandchild + "</div>",
        grandchild + '<ol class="subject-page-toc-list">',
    ]
    for index, target in enumerate(targets, start=1):
        lines.append(
            item_indent
            + "<li>"
            + f'<a href="#{html.escape(target.target_id, quote=True)}">'
            + f'<span class="subject-page-toc-number" aria-hidden="true">{index:02d}</span>'
            + f'<span class="subject-page-toc-text">{html.escape(target.text)}</span>'
            + "</a></li>"
        )
    lines.extend(
        [
            grandchild + "</ol>",
            child + "</div>",
            indent + "</nav>",
            indent + TOC_END,
        ]
    )
    return newline.join(lines) + newline


def render_page(original: str) -> tuple[str, int, int]:
    if original.count(TOC_START) != original.count(TOC_END):
        raise ValueError("Unbalanced TOC markers")
    if original.count(TOC_START) > 1:
        raise ValueError("Multiple TOC blocks found")
    source = TOC_BLOCK_RE.sub("", original, count=1)
    newline = detect_newline(source)
    source = ensure_style_link(source, newline)
    source, dimensions_added = ensure_media_dimensions(source)
    source = ensure_target_ids(source)
    targets = select_targets(source)
    summary_sections = list(SUMMARY_SECTION_RE.finditer(source))
    if len(summary_sections) != 1:
        raise ValueError(f"Summary section count is {len(summary_sections)}")
    insertion_point = summary_sections[0].start()
    line_start = source.rfind(newline, 0, insertion_point) + len(newline)
    indent = source[line_start:insertion_point]
    if indent.strip():
        raise ValueError("Summary section does not start on its own line")
    rendered = (
        source[:line_start]
        + toc_markup(targets, indent, newline)
        + source[line_start:]
    )
    return rendered, len(targets), dimensions_added


def validate_page(source: str) -> list[str]:
    errors: list[str] = []
    if source.count(STYLE_MARKER) != 1 or source.count(STYLE_HREF) != 1:
        errors.append("TOC stylesheet marker or link count is not exactly one")
    if source.count(TOC_START) != 1 or source.count(TOC_END) != 1:
        errors.append("TOC marker count is not exactly one")
    toc = TOC_CAPTURE_RE.search(source)
    if not toc:
        errors.append("TOC block missing")
        return errors
    try:
        targets = select_targets(source)
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
        return errors
    expected = [(target.target_id, target.text) for target in targets]
    links = [
        (match.group("id"), visible_text(match.group("label")))
        for match in TOC_LINK_RE.finditer(toc.group(0))
    ]
    if links != expected:
        errors.append("TOC links or labels do not match visible H2 headings")
    all_ids = [match.group("id") for match in ANY_ID_RE.finditer(source)]
    duplicate_ids = sorted(
        target_id
        for target_id, count in Counter(all_ids).items()
        if count > 1
    )
    if duplicate_ids:
        errors.append(f"Duplicate IDs found: {duplicate_ids}")
    if all_ids.count("subject-page-toc-title") != 1:
        errors.append("TOC title ID count is not exactly one")
    for target_id, _ in links:
        if all_ids.count(target_id) != 1:
            errors.append(
                f"Anchor target count for {target_id!r} is "
                f"{all_ids.count(target_id)}"
            )
    summary = SUMMARY_SECTION_RE.search(source)
    if not summary or toc.end() > summary.start():
        errors.append("TOC is not before the summary section")
    elif source[toc.end() : summary.start()].strip():
        errors.append("Unexpected content appears between TOC and summary section")
    return errors


def validate_hubs() -> list[str]:
    hubs = [SUBJECT_ROOT / "index.html"] + [
        SUBJECT_ROOT / category / "index.html" for category in SUBJECT_CATEGORIES
    ]
    errors: list[str] = []
    for hub in hubs:
        source = hub.read_text(encoding="utf-8")
        if (
            STYLE_MARKER in source
            or TOC_START in source
            or TOC_END in source
            or STYLE_HREF in source
        ):
            errors.append(
                "Hub unexpectedly contains a subject detail TOC: "
                f"{hub.relative_to(ROOT).as_posix()}"
            )
    return errors


def process(write: bool) -> int:
    try:
        pages = detail_pages()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {exc}")
        return 1

    changed = 0
    validated = 0
    dimensions_added = 0
    distribution: Counter[int] = Counter()
    categories: Counter[str] = Counter()
    failures: list[str] = []
    rendered_pages: list[tuple[Path, str]] = []

    for path in pages:
        try:
            raw = path.read_bytes()
            if raw.startswith(b"\xef\xbb\xbf"):
                raise ValueError("UTF-8 BOM is not supported")
            original = raw.decode("utf-8")
            rendered, target_count, page_dimensions_added = render_page(original)
            page_errors = validate_page(rendered)
            if page_errors:
                raise ValueError("; ".join(page_errors))
            if rendered != original:
                changed += 1
                rendered_pages.append((path, rendered))
            dimensions_added += page_dimensions_added
            distribution[target_count] += 1
            categories[path.relative_to(SUBJECT_ROOT).parts[0]] += 1
            validated += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{path.relative_to(ROOT).as_posix()}: {exc}")

    failures.extend(validate_hubs())
    print(f"pages={len(pages)} validated={validated}")
    print(
        "toc_link_distribution="
        + ",".join(
            f"{count}:{page_count}"
            for count, page_count in sorted(distribution.items())
        )
    )
    print(
        "toc_links_total="
        + str(sum(count * page_count for count, page_count in distribution.items()))
    )
    print(
        "categories="
        + ",".join(f"{name}:{count}" for name, count in sorted(categories.items()))
    )
    print(f"map_dimensions_added={dimensions_added}")
    print(f"changed={changed} mode={'write' if write else 'check'}")
    for failure in failures[:50]:
        print("ERROR", failure)
    if len(failures) > 50:
        print(f"ERROR ... and {len(failures) - 50} more")
    if failures:
        return 1
    if write:
        for path, rendered in rendered_pages:
            path.write_bytes(rendered.encode("utf-8"))
    elif changed:
        print("ERROR check mode found pages that need updating")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Apply or refresh TOCs")
    mode.add_argument("--check", action="store_true", help="Validate idempotence")
    args = parser.parse_args()
    raise SystemExit(process(write=args.write))


if __name__ == "__main__":
    main()
