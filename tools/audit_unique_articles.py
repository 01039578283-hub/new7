#!/usr/bin/env python3
"""Audit the page-specific long-form article blocks without changing site files.

The audit is intentionally report-only by default.  Set AUDIT_STRICT=1 when the
results have been reviewed and it is appropriate to use failures as a CI gate.
"""

from __future__ import annotations

import csv
import hashlib
import heapq
import html
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
NATIONAL_ROOT = ROOT / "전국학원"
REPORT_DIR = ROOT / "reports"
EXPECTED_TARGET_COUNT = 1_856
UNIQUE_COPY_ROLE = "unique-copy"
ARTICLE_ANCHORS = (
    "local-article-evidence",
    "local-article-plan",
    "local-article-review",
)

SPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
NUMBER_RE = re.compile(r"\d+(?:[\s,.:/~\-–—]\d+)*")
NON_TOKEN_RE = re.compile(r"[^0-9A-Za-z가-힣]+")
LD_JSON_RE = re.compile(
    r"<script\b[^>]*\btype\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)


def clean_text(value: Any) -> str:
    return SPACE_RE.sub(" ", html.unescape(str(value or ""))).strip()


def clean_fragment(value: str) -> str:
    return clean_text(TAG_RE.sub(" ", value))


def canonical_lines(value: Any) -> str:
    return "\n".join(
        clean_text(line) for line in str(value or "").replace("\r\n", "\n").split("\n")
        if clean_text(line)
    )


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fragment_id(value: Any) -> str:
    value = str(value or "")
    return value.rsplit("#", 1)[-1] if "#" in value else value


def node_has_type(node: dict[str, Any], expected: str) -> bool:
    value = node.get("@type")
    return value == expected or (isinstance(value, list) and expected in value)


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


@dataclass
class ArticlePanel:
    anchor: str = ""
    heading: str = ""
    paragraphs: list[str] = field(default_factory=list)
    sequence: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class UniqueCapture:
    panels: list[ArticlePanel] = field(default_factory=list)
    kicker_count: int = 0
    content_paragraph_count: int = 0

    @property
    def anchors(self) -> list[str]:
        return [panel.anchor for panel in self.panels]

    @property
    def headings(self) -> list[str]:
        return [panel.heading for panel in self.panels]

    @property
    def visible_article_text(self) -> str:
        lines: list[str] = []
        for panel in self.panels:
            lines.extend(text for kind, text in panel.sequence if kind != "kicker" and text)
        return canonical_lines("\n".join(lines))


class UniqueCopyParser(HTMLParser):
    """Capture the semantic panels inside data-content-role=unique-copy."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.captures: list[UniqueCapture] = []
        self.active: UniqueCapture | None = None
        self.root_depth = -1
        self.current_panel: ArticlePanel | None = None
        self.panel_depth = -1
        self.text_tag = ""
        self.text_depth = -1
        self.text_kind = ""
        self.text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): value or "" for key, value in attrs}
        self.stack.append(tag)
        if attr.get("data-content-role") == UNIQUE_COPY_ROLE:
            capture = UniqueCapture()
            self.captures.append(capture)
            self.active = capture
            self.root_depth = len(self.stack)
        if self.active is None:
            return
        if tag == "article":
            self.current_panel = ArticlePanel(anchor=attr.get("id", ""))
            self.active.panels.append(self.current_panel)
            self.panel_depth = len(self.stack)
        elif tag in {"h2", "p"} and self.current_panel is not None:
            self.text_tag = tag
            self.text_depth = len(self.stack)
            classes = set(attr.get("class", "").split())
            self.text_kind = "heading" if tag == "h2" else (
                "kicker" if "section-kicker" in classes else "paragraph"
            )
            self.text_buffer = []

    def handle_data(self, data: str) -> None:
        if self.active is not None and self.text_tag:
            self.text_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        depth = len(self.stack)
        if self.active is not None and self.text_tag == tag and self.text_depth == depth:
            value = clean_text("".join(self.text_buffer))
            if self.current_panel is not None and value:
                self.current_panel.sequence.append((self.text_kind, value))
                if self.text_kind == "heading":
                    self.current_panel.heading = value
                elif self.text_kind == "paragraph":
                    self.current_panel.paragraphs.append(value)
                    self.active.content_paragraph_count += 1
                elif self.text_kind == "kicker":
                    self.active.kicker_count += 1
            self.text_tag = ""
            self.text_depth = -1
            self.text_kind = ""
            self.text_buffer = []
        if self.active is not None and tag == "article" and self.panel_depth == depth:
            self.current_panel = None
            self.panel_depth = -1
        if self.active is not None and self.root_depth == depth and tag == self.stack[-1]:
            self.active = None
            self.root_depth = -1
        if self.stack:
            self.stack.pop()


def page_category(path: Path) -> tuple[str, str]:
    parts = path.relative_to(NATIONAL_ROOT).parts[:-1]
    town = parts[0]
    return town, "PARENT" if len(parts) == 1 else parts[1]


def parse_jsonld(source: str) -> tuple[list[dict[str, Any]], list[str]]:
    nodes: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw in enumerate(LD_JSON_RE.findall(source), 1):
        try:
            nodes.extend(walk_json(json.loads(raw.strip())))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            errors.append(f"script {index}: {exc}")
    return nodes, errors


def typed_names(nodes: list[dict[str, Any]], types: set[str]) -> set[str]:
    names: set[str] = set()
    for node in nodes:
        if any(node_has_type(node, item) for item in types):
            name = node.get("name")
            if isinstance(name, str) and clean_text(name):
                names.add(clean_text(name))
    return names


def normalization_terms(
    nodes: list[dict[str, Any]], title: str, h1: str, town: str, category: str
) -> list[str]:
    terms = {title, h1, town, category}
    terms.update(typed_names(nodes, {
        "School", "EducationalOrganization", "LocalBusiness", "Place", "WebPage"
    }))
    for node in nodes:
        for key in ("headline", "addressRegion", "addressLocality", "streetAddress"):
            value = node.get(key)
            if isinstance(value, str):
                terms.add(clean_text(value))
        if node_has_type(node, "PostalAddress"):
            for key in ("addressRegion", "addressLocality", "streetAddress"):
                value = node.get(key)
                if isinstance(value, str):
                    terms.add(clean_text(value))
    expanded: set[str] = set()
    for term in terms:
        term = clean_text(term)
        if len(term) >= 2:
            expanded.add(term)
            if " | " in term:
                expanded.add(term.split(" | ", 1)[0].strip())
    return sorted(expanded, key=lambda item: (-len(item), item))


def normalize_text(value: str, terms: list[str]) -> str:
    value = canonical_lines(value).lower()
    for term in terms:
        value = re.sub(re.escape(term.lower()), " ", value, flags=re.IGNORECASE)
    value = NUMBER_RE.sub(" ", value)
    value = NON_TOKEN_RE.sub(" ", value)
    return clean_text(value)


def split_sentences(value: str) -> list[str]:
    result: list[str] = []
    for line in canonical_lines(value).splitlines():
        for part in re.split(r"(?<=[.!?。！？])\s+", line):
            part = clean_text(part)
            if part:
                result.append(part)
    return result


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * ratio
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def distribution(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {key: None for key in ("count", "min", "p25", "median", "mean", "p95", "max")}
    floats = [float(value) for value in values]
    return {
        "count": len(values),
        "min": min(values),
        "p25": round(percentile(floats, 0.25) or 0, 2),
        "median": round(statistics.median(floats), 2),
        "mean": round(statistics.fmean(floats), 2),
        "p95": round(percentile(floats, 0.95) or 0, 2),
        "max": max(values),
    }


def duplicate_summary(pages: list[dict[str, Any]], field_name: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        groups[page[field_name]].append(page)
    duplicates = [group for group in groups.values() if len(group) > 1]
    duplicates.sort(key=lambda group: (-len(group), group[0]["path"]))
    return {
        "unique_count": len(groups),
        "duplicate_group_count": len(duplicates),
        "duplicate_page_count": sum(len(group) for group in duplicates),
        "largest_group_size": max((len(group) for group in duplicates), default=1),
        "groups": [
            {
                "hash": group[0][field_name],
                "count": len(group),
                "pages": [item["path"] for item in group],
            }
            for group in duplicates[:50]
        ],
    }


def shingle_set(value: str, size: int = 5) -> set[tuple[str, ...]]:
    tokens = value.split()
    if len(tokens) < size:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def category_jaccard(pages: list[dict[str, Any]], top_limit: int = 10) -> dict[str, Any]:
    if len(pages) < 2:
        return {
            "method": "all_pairs", "page_count": len(pages), "pair_count": 0,
            "mean": None, "p95": None, "max": None, "top_pairs": [],
        }
    prepared = [(page, shingle_set(page["normalized_text"])) for page in pages]
    similarities: list[float] = []
    top: list[tuple[float, str, str, str, str]] = []
    for left_index, (left, left_set) in enumerate(prepared):
        for right, right_set in prepared[left_index + 1:]:
            union_size = len(left_set | right_set)
            similarity = len(left_set & right_set) / union_size if union_size else 1.0
            similarities.append(similarity)
            candidate = (
                similarity, left["path"], right["path"], left["title"], right["title"]
            )
            if len(top) < top_limit:
                heapq.heappush(top, candidate)
            elif candidate > top[0]:
                heapq.heapreplace(top, candidate)
    top.sort(reverse=True)
    return {
        "method": "all_pairs",
        "page_count": len(pages),
        "pair_count": len(similarities),
        "mean": round(statistics.fmean(similarities), 6),
        "p95": round(percentile(similarities, 0.95) or 0, 6),
        "max": round(max(similarities), 6),
        "top_pairs": [
            {
                "similarity": round(item[0], 6), "left_path": item[1],
                "right_path": item[2], "left_title": item[3], "right_title": item[4],
            }
            for item in top
        ],
    }


def first_match(pattern: re.Pattern[str], source: str) -> str:
    match = pattern.search(source)
    return clean_fragment(match.group(1)) if match else ""


def extract_anchor_chain(
    nodes: list[dict[str, Any]], capture: UniqueCapture | None
) -> dict[str, Any]:
    dom_ids = capture.anchors if capture else []
    dom_names = capture.headings if capture else []
    articles = [node for node in nodes if node_has_type(node, "Article")]
    article = articles[0] if len(articles) == 1 else {}
    has_part = article.get("hasPart", []) if isinstance(article, dict) else []
    if isinstance(has_part, dict):
        has_part = [has_part]
    has_part_ids = [fragment_id(item.get("@id")) for item in has_part if isinstance(item, dict)]

    web_elements = {
        fragment_id(node.get("@id")): node
        for node in nodes
        if node_has_type(node, "WebPageElement") and node.get("@id")
    }
    web_ids = [item for item in has_part_ids if item in web_elements]
    web_names = [clean_text(web_elements[item].get("name")) for item in has_part_ids if item in web_elements]

    item_lists = [
        node for node in nodes
        if node_has_type(node, "ItemList") and "article-sections" in str(node.get("@id", ""))
    ]
    item_list = item_lists[0] if len(item_lists) == 1 else {}
    entries = item_list.get("itemListElement", []) if isinstance(item_list, dict) else []
    entries = entries if isinstance(entries, list) else [entries]
    entries = sorted(
        (item for item in entries if isinstance(item, dict)),
        key=lambda item: int(item.get("position", 0) or 0),
    )
    item_ids = [fragment_id(item.get("url") or item.get("item", "")) for item in entries]
    item_names = [clean_text(item.get("name")) for item in entries]
    chain_match = (
        dom_ids == list(ARTICLE_ANCHORS)
        and dom_ids == has_part_ids == web_ids == item_ids
        and dom_names == web_names == item_names
    )
    return {
        "article_count": len(articles),
        "article": article,
        "article_item_list_count": len(item_lists),
        "dom_ids": dom_ids,
        "has_part_ids": has_part_ids,
        "web_element_ids": web_ids,
        "item_list_ids": item_ids,
        "dom_names": dom_names,
        "web_element_names": web_names,
        "item_list_names": item_names,
        "anchor_chain_match": chain_match,
    }


def audit_page(path: Path) -> tuple[dict[str, Any], list[tuple[str, str]], list[tuple[str, str]]]:
    source = path.read_text(encoding="utf-8")
    parser = UniqueCopyParser()
    parser.feed(source)
    nodes, json_errors = parse_jsonld(source)
    title = first_match(TITLE_RE, source)
    h1 = first_match(H1_RE, source)
    town, category = page_category(path)
    capture = parser.captures[0] if len(parser.captures) == 1 else None
    visible_text = capture.visible_article_text if capture else ""
    chain = extract_anchor_chain(nodes, capture)
    article = chain.pop("article")
    article_body = canonical_lines(article.get("articleBody", "")) if article else ""
    terms = normalization_terms(nodes, title, h1, town, category)
    normalized = normalize_text(visible_text, terms)

    sentences = split_sentences(visible_text)
    raw_sentences: list[tuple[str, str]] = []
    normalized_sentences: list[tuple[str, str]] = []
    sentence_multiset: list[str] = []
    for sentence in sentences:
        normalized_sentence = normalize_text(sentence, terms)
        if normalized_sentence:
            sentence_multiset.append(normalized_sentence)
        if len(re.sub(r"\s+", "", sentence)) >= 25:
            raw_sentences.append((sentence, sentence))
            if normalized_sentence:
                normalized_sentences.append((normalized_sentence, sentence))

    rel_path = path.relative_to(ROOT).as_posix()
    row: dict[str, Any] = {
        "path": rel_path,
        "town": town,
        "category": category,
        "title": title,
        "h1": h1,
        "unique_copy_count": len(parser.captures),
        "section_count": len(capture.panels) if capture else 0,
        "paragraph_count": capture.content_paragraph_count if capture else 0,
        "kicker_count": capture.kicker_count if capture else 0,
        "article_char_count": len(visible_text),
        "article_nonspace_char_count": len(re.sub(r"\s+", "", visible_text)),
        "raw_hash": digest(visible_text),
        "normalized_hash": digest(normalized),
        "sentence_multiset_hash": digest(json.dumps(sorted(sentence_multiset), ensure_ascii=False)),
        "normalized_text": normalized,
        "normalization_term_count": len(terms),
        "jsonld_parse_error_count": len(json_errors),
        "jsonld_parse_errors": json_errors,
        "article_body_match": bool(article) and article_body == visible_text,
        **chain,
    }
    row["structure_pass"] = (
        row["unique_copy_count"] == 1
        and row["section_count"] == 3
        and row["paragraph_count"] == 6
    )
    row["jsonld_alignment_pass"] = (
        row["jsonld_parse_error_count"] == 0
        and row["article_count"] == 1
        and row["article_item_list_count"] == 1
        and row["anchor_chain_match"]
        and row["article_body_match"]
    )
    return row, raw_sentences, normalized_sentences


def write_pages_csv(path: Path, pages: list[dict[str, Any]]) -> None:
    fields = [
        "path", "town", "category", "title", "h1", "unique_copy_count",
        "section_count", "paragraph_count", "kicker_count", "article_char_count",
        "article_nonspace_char_count", "raw_hash", "normalized_hash",
        "sentence_multiset_hash", "normalization_term_count", "jsonld_parse_error_count",
        "article_count", "article_item_list_count", "structure_pass",
        "anchor_chain_match", "article_body_match", "jsonld_alignment_pass",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for page in pages:
            writer.writerow({key: page.get(key, "") for key in fields})


def write_sentence_csv(
    path: Path,
    raw_documents: dict[str, set[str]],
    normalized_documents: dict[str, set[str]],
    normalized_examples: dict[str, str],
) -> None:
    rows: list[dict[str, Any]] = []
    for sentence, documents in raw_documents.items():
        if len(documents) > 1:
            rows.append({
                "mode": "raw", "document_frequency": len(documents),
                "sentence": sentence, "example": sentence,
                "sample_paths": " | ".join(sorted(documents)[:10]),
            })
    for sentence, documents in normalized_documents.items():
        if len(documents) > 1:
            rows.append({
                "mode": "normalized", "document_frequency": len(documents),
                "sentence": sentence, "example": normalized_examples.get(sentence, ""),
                "sample_paths": " | ".join(sorted(documents)[:10]),
            })
    rows.sort(key=lambda row: (-row["document_frequency"], row["mode"], row["sentence"]))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "mode", "document_frequency", "sentence", "example", "sample_paths"
        ))
        writer.writeheader()
        writer.writerows(rows)


def write_pairs_csv(path: Path, similarities: dict[str, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ("category", "similarity", "left_path", "right_path", "left_title", "right_title")
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for category, stats in similarities.items():
            for pair in stats["top_pairs"]:
                writer.writerow({"category": category, **pair})


def main() -> int:
    target_paths = sorted(
        path for path in NATIONAL_ROOT.rglob("index.html")
        if path != NATIONAL_ROOT / "index.html"
    )
    pages: list[dict[str, Any]] = []
    raw_documents: dict[str, set[str]] = defaultdict(set)
    normalized_documents: dict[str, set[str]] = defaultdict(set)
    normalized_examples: dict[str, str] = {}

    for path in target_paths:
        page, raw_sentences, normalized_sentences = audit_page(path)
        pages.append(page)
        for key, example in set(raw_sentences):
            raw_documents[key].add(page["path"])
        for key, example in set(normalized_sentences):
            normalized_documents[key].add(page["path"])
            normalized_examples.setdefault(key, example)

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        by_category[page["category"]].append(page)
    similarities = {
        category: category_jaccard(category_pages)
        for category, category_pages in sorted(by_category.items())
    }

    raw_repeats = sorted(
        (
            {
                "sentence": sentence, "document_frequency": len(documents),
                "sample_paths": sorted(documents)[:10],
            }
            for sentence, documents in raw_documents.items() if len(documents) > 1
        ),
        key=lambda item: (-item["document_frequency"], item["sentence"]),
    )
    normalized_repeats = sorted(
        (
            {
                "sentence": sentence, "example": normalized_examples.get(sentence, ""),
                "document_frequency": len(documents), "sample_paths": sorted(documents)[:10],
            }
            for sentence, documents in normalized_documents.items() if len(documents) > 1
        ),
        key=lambda item: (-item["document_frequency"], item["sentence"]),
    )

    failures = {
        "missing_unique_copy": [page["path"] for page in pages if page["unique_copy_count"] == 0],
        "multiple_unique_copy": [page["path"] for page in pages if page["unique_copy_count"] > 1],
        "section_count_not_3": [page["path"] for page in pages if page["section_count"] != 3],
        "paragraph_count_not_6": [page["path"] for page in pages if page["paragraph_count"] != 6],
        "jsonld_parse_error": [page["path"] for page in pages if page["jsonld_parse_error_count"]],
        "article_count_not_1": [page["path"] for page in pages if page["article_count"] != 1],
        "article_item_list_count_not_1": [
            page["path"] for page in pages if page["article_item_list_count"] != 1
        ],
        "anchor_chain_mismatch": [page["path"] for page in pages if not page["anchor_chain_match"]],
        "article_body_mismatch": [page["path"] for page in pages if not page["article_body_match"]],
    }
    structural_pass = (
        len(pages) == EXPECTED_TARGET_COUNT and all(not values for values in failures.values())
    )
    category_lengths = {
        category: {
            "article_char_count": distribution([page["article_char_count"] for page in category_pages]),
            "article_nonspace_char_count": distribution([
                page["article_nonspace_char_count"] for page in category_pages
            ]),
        }
        for category, category_pages in sorted(by_category.items())
    }
    report: dict[str, Any] = {
        "audit": "unique page article audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "report_only": os.environ.get("AUDIT_STRICT") != "1",
        "expected_target_count": EXPECTED_TARGET_COUNT,
        "actual_target_count": len(pages),
        "target_count_match": len(pages) == EXPECTED_TARGET_COUNT,
        "status": "PASS" if structural_pass else "REVIEW",
        "structural_and_jsonld_alignment_pass": structural_pass,
        "failure_counts": {key: len(value) for key, value in failures.items()},
        "failure_paths": {key: value[:100] for key, value in failures.items()},
        "category_page_counts": {
            category: len(category_pages) for category, category_pages in sorted(by_category.items())
        },
        "character_length": {
            "overall_article_char_count": distribution([page["article_char_count"] for page in pages]),
            "overall_article_nonspace_char_count": distribution([
                page["article_nonspace_char_count"] for page in pages
            ]),
            "by_category": category_lengths,
        },
        "exact_hashes": {
            "raw": duplicate_summary(pages, "raw_hash"),
            "normalized_location_title_center_school_number_removed": duplicate_summary(
                pages, "normalized_hash"
            ),
            "normalized_sentence_multiset": duplicate_summary(pages, "sentence_multiset_hash"),
        },
        "repeated_sentences_min_25_nonspace_chars": {
            "raw_repeat_count": len(raw_repeats),
            "normalized_repeat_count": len(normalized_repeats),
            "raw_max_document_frequency": max(
                (item["document_frequency"] for item in raw_repeats), default=1
            ),
            "normalized_max_document_frequency": max(
                (item["document_frequency"] for item in normalized_repeats), default=1
            ),
            "raw_top_100": raw_repeats[:100],
            "normalized_top_100": normalized_repeats[:100],
        },
        "within_category_normalized_word_5gram_jaccard": similarities,
        "pages": [
            {key: value for key, value in page.items() if key != "normalized_text"}
            for page in pages
        ],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "unique_articles_audit.json"
    pages_path = REPORT_DIR / "unique_articles_pages.csv"
    sentences_path = REPORT_DIR / "unique_articles_repeated_sentences.csv"
    pairs_path = REPORT_DIR / "unique_articles_top_jaccard_pairs.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_pages_csv(pages_path, pages)
    write_sentence_csv(sentences_path, raw_documents, normalized_documents, normalized_examples)
    write_pairs_csv(pairs_path, similarities)

    print(f"Target pages: {len(pages):,} / expected {EXPECTED_TARGET_COUNT:,}")
    print(f"Structural + JSON-LD alignment: {'PASS' if structural_pass else 'REVIEW'}")
    print("Failures: " + ", ".join(f"{key}={len(value)}" for key, value in failures.items()))
    print(
        "Exact unique hashes: "
        f"raw={report['exact_hashes']['raw']['unique_count']:,}, "
        f"normalized={report['exact_hashes']['normalized_location_title_center_school_number_removed']['unique_count']:,}, "
        f"sentence-multiset={report['exact_hashes']['normalized_sentence_multiset']['unique_count']:,}"
    )
    print(
        "Repeated sentences (25+ chars): "
        f"raw={len(raw_repeats):,}, normalized={len(normalized_repeats):,}"
    )
    print(f"JSON: {json_path}")
    print(f"Pages CSV: {pages_path}")
    print(f"Sentences CSV: {sentences_path}")
    print(f"Top pairs CSV: {pairs_path}")

    strict = os.environ.get("AUDIT_STRICT") == "1"
    return 1 if strict and not structural_pass else 0


if __name__ == "__main__":
    sys.exit(main())
