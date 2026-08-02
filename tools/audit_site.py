from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://xn--zb0b93vh4ggmeqzwda.com"
INTERNAL_HOSTS = {"xn--zb0b93vh4ggmeqzwda.com", "학습관리학원.com"}
REQUIRED_LOCAL_TYPES = {
    "EducationalOrganization",
    "LocalBusiness",
    "Article",
    "Service",
    "FAQPage",
    "BreadcrumbList",
    "ItemList",
}
KNOWN_BROKEN_PHRASES = (
    "영어과 수학",
    "수학과 영어을",
    "국어과 영어",
    "학습관리을",
    "재풀이이",
    "중와 학생",
    "상태과 플래너",
    "점와 실제",
)

SCRIPT_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\']>([\s\S]*?)</script>', re.I
)
DETAIL_RE = re.compile(
    r'<details(?:\s[^>]*)?>\s*<summary>([\s\S]*?)</summary>\s*'
    r'<p(?:\s[^>]*)?>([\s\S]*?)</p>\s*</details>',
    re.I,
)
FAQ_CARD_RE = re.compile(
    r'<article\b[^>]*class=["\'][^"\']*\bfaq-card\b[^"\']*["\'][^>]*>'
    r'[\s\S]*?<h[2-4](?:\s[^>]*)?>([\s\S]*?)</h[2-4]>'
    r'[\s\S]*?<p(?:\s[^>]*)?>([\s\S]*?)</p>[\s\S]*?</article>',
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', re.I)


def plain(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def attr_from_tag(source: str, tag_name: str, attr_name: str, attr_value: str, wanted: str) -> str:
    for tag in re.findall(fr"<{tag_name}\b[^>]*>", source, re.I):
        attrs = dict(
            (key.lower(), html.unescape(value))
            for key, _, value in re.findall(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', tag, re.S)
        )
        if attrs.get(attr_name.lower(), "").lower() == attr_value.lower():
            return attrs.get(wanted.lower(), "")
    return ""


def expected_url(path: Path) -> str:
    relative = path.relative_to(ROOT)
    url_path = "/" if relative.parts == ("index.html",) else "/" + relative.parent.as_posix() + "/"
    return BASE_URL + quote(url_path, safe="/")


def schema_nodes(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from schema_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from schema_nodes(item)


def schema_types(node: dict) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def visible_faqs(source: str) -> list[tuple[str, str]]:
    result = []
    candidates = DETAIL_RE.findall(source) + FAQ_CARD_RE.findall(source)
    for question_html, answer_html in candidates:
        question, answer = plain(question_html), plain(answer_html)
        pair = (question, answer)
        if question and answer and question.endswith("?") and pair not in result:
            result.append(pair)
    return result


def schema_faqs(nodes: list[dict]) -> list[tuple[str, str]]:
    result = []
    for node in nodes:
        if "FAQPage" not in schema_types(node):
            continue
        for entity in node.get("mainEntity", []):
            if not isinstance(entity, dict):
                continue
            answer = entity.get("acceptedAnswer", {})
            if isinstance(answer, dict):
                result.append((str(entity.get("name", "")).strip(), str(answer.get("text", "")).strip()))
    return result


def resolve_internal(page: Path, href: str) -> Path | None:
    href = html.unescape(href.strip())
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlsplit(href)
    if parsed.scheme in {"http", "https"} and parsed.hostname not in INTERNAL_HOSTS:
        return None
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return None
    if raw_path.startswith("/") or parsed.scheme:
        target = ROOT / raw_path.lstrip("/")
    else:
        target = page.parent / raw_path
    if raw_path.endswith("/") or not target.suffix:
        target = target / "index.html"
    return target.resolve()


def main() -> int:
    pages = sorted(ROOT.rglob("index.html"))
    page_urls: set[str] = set()
    errors: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    meta_descriptions: list[str] = []
    org_ids_by_family: dict[Path, set[str]] = {}
    local_pages = 0
    required_type_pages = 0

    def error(kind: str, path: Path | str) -> None:
        errors[kind] += 1
        examples.setdefault(kind, [])
        if len(examples[kind]) < 3:
            examples[kind].append(str(path))

    for path in pages:
        source = path.read_text(encoding="utf-8")
        expected = expected_url(path)
        page_urls.add(expected)

        title_match = re.findall(r"<title>([\s\S]*?)</title>", source, re.I)
        description = attr_from_tag(source, "meta", "name", "description", "content")
        canonical = attr_from_tag(source, "link", "rel", "canonical", "href")
        og_url = attr_from_tag(source, "meta", "property", "og:url", "content")
        h1s = re.findall(r"<h1\b[^>]*>([\s\S]*?)</h1>", source, re.I)
        if len(title_match) != 1:
            error("title_count", path)
        if not description:
            error("meta_description_missing", path)
        else:
            meta_descriptions.append(description)
        if canonical != expected:
            error("canonical_not_self", path)
        if og_url != expected:
            error("og_url_not_self", path)
        if len(h1s) != 1:
            error("h1_count", path)
        if any(phrase in source for phrase in KNOWN_BROKEN_PHRASES):
            error("known_korean_particle_error", path)

        nodes: list[dict] = []
        for raw in SCRIPT_RE.findall(source):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                error("jsonld_parse", path)
                continue
            nodes.extend(node for node in schema_nodes(data) if isinstance(node, dict))
        if not nodes:
            error("jsonld_missing", path)

        for node in nodes:
            if schema_types(node) & {"Review", "AggregateRating"}:
                error("unverified_review_schema", path)
                break
        for node in nodes:
            for key in ("@id", "url", "item", "contentUrl"):
                value = node.get(key)
                if isinstance(value, str) and not value.startswith(("https://", "http://")):
                    error("relative_jsonld_url", path)
                    break

        screen_pairs = visible_faqs(source)
        json_pairs = schema_faqs(nodes)
        if screen_pairs and screen_pairs != json_pairs:
            error("faq_screen_schema_mismatch", path)

        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] == "전국학원" and len(relative.parts) >= 3:
            local_pages += 1
            types = set().union(*(schema_types(node) for node in nodes)) if nodes else set()
            if not REQUIRED_LOCAL_TYPES.issubset(types):
                error("local_schema_types_missing", path)
            else:
                required_type_pages += 1
            family = ROOT / "전국학원" / relative.parts[1]
            org_ids = {
                str(node.get("@id"))
                for node in nodes
                if schema_types(node) & {"EducationalOrganization", "LocalBusiness"}
                and node.get("@id")
            }
            org_ids_by_family.setdefault(family, set()).update(org_ids)

        for href in HREF_RE.findall(source):
            if re.search(r"(?:^|/)index\.html(?:$|[?#])", href):
                error("href_contains_index_html", path)
            target = resolve_internal(path, href)
            if target is not None and not target.exists():
                error("broken_internal_link", f"{path.relative_to(ROOT)} -> {href}")

    for family, org_ids in org_ids_by_family.items():
        if len(org_ids) != 1:
            error("family_org_entity_mismatch", f"{family.relative_to(ROOT)}: {sorted(org_ids)}")

    sitemap_path = ROOT / "sitemap.xml"
    try:
        sitemap_root = ET.parse(sitemap_path).getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemap_urls = [item.text or "" for item in sitemap_root.findall("s:url/s:loc", ns)]
        lastmods = [item.text or "" for item in sitemap_root.findall("s:url/s:lastmod", ns)]
        if len(sitemap_urls) != len(set(sitemap_urls)):
            error("sitemap_duplicate_url", sitemap_path)
        if set(sitemap_urls) != page_urls:
            error("sitemap_canonical_set_mismatch", sitemap_path)
        for value in lastmods:
            try:
                datetime.fromisoformat(value)
            except ValueError:
                error("sitemap_invalid_lastmod", value)
    except (ET.ParseError, OSError) as exc:
        error("sitemap_parse", exc)
        sitemap_urls, lastmods = [], []

    rss_path = ROOT / "rss.xml"
    try:
        rss_root = ET.parse(rss_path).getroot()
        rss_links = [item.findtext("link", "") for item in rss_root.findall("./channel/item")]
        build_date = rss_root.findtext("./channel/lastBuildDate", "")
        if not 1 <= len(rss_links) <= 20:
            error("rss_item_count", len(rss_links))
        if any(link not in page_urls for link in rss_links):
            error("rss_noncanonical_link", rss_path)
        if not build_date:
            error("rss_last_build_missing", rss_path)
    except (ET.ParseError, OSError) as exc:
        error("rss_parse", exc)
        rss_links = []

    special = ROOT / "전국학원" / "불당동" / "고등수학학원" / "index.html"
    if not special.exists():
        error("special_page_missing", special)
    elif "불당동/고등수학학원/" not in (ROOT / "전국학원" / "index.html").read_text(encoding="utf-8"):
        error("special_hub_link_missing", special)

    jang = ROOT / "전국학원" / "장동" / "index.html"
    if jang.exists():
        jang_source = jang.read_text(encoding="utf-8")
        if "광장점" in jang_source or "서울 광진" in jang_source or "전주혁신" not in jang_source:
            error("jangdong_entity_mismatch", jang)

    report = {
        "html_pages": len(pages),
        "canonical_unique": len(page_urls),
        "local_parent_and_child_pages": local_pages,
        "local_pages_with_required_schema_types": required_type_pages,
        "organization_families": len(org_ids_by_family),
        "meta_description_unique": len(set(meta_descriptions)),
        "meta_description_length": {
            "min": min(map(len, meta_descriptions), default=0),
            "max": max(map(len, meta_descriptions), default=0),
            "average": round(sum(map(len, meta_descriptions)) / len(meta_descriptions), 1) if meta_descriptions else 0,
        },
        "sitemap_urls": len(sitemap_urls),
        "sitemap_lastmods": len(lastmods),
        "rss_items": len(rss_links),
        "errors": dict(errors),
        "examples": examples,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
