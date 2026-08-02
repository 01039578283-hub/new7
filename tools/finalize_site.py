from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://xn--zb0b93vh4ggmeqzwda.com"

SCRIPT_RE = re.compile(
    r'(<script\s+type=["\']application/ld\+json["\']>)([\s\S]*?)(</script>)',
    re.I,
)
DETAIL_RE = re.compile(
    r'<details(?:\s[^>]*)?>\s*<summary>([\s\S]*?)</summary>\s*<p(?:\s[^>]*)?>([\s\S]*?)</p>\s*</details>',
    re.I,
)
FAQ_CARD_RE = re.compile(
    r'<article\b[^>]*class=["\'][^"\']*\bfaq-card\b[^"\']*["\'][^>]*>'
    r'[\s\S]*?<h[2-4](?:\s[^>]*)?>([\s\S]*?)</h[2-4]>'
    r'[\s\S]*?<p(?:\s[^>]*)?>([\s\S]*?)</p>[\s\S]*?</article>',
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")


def absolute_url(value: str) -> str:
    if value.startswith(("https://", "http://")):
        return value
    if not value.startswith("/"):
        value = "/" + value
    return BASE_URL + quote(value, safe="/:%#?=&")


def text_content(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def visible_faqs(source: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    candidates = DETAIL_RE.findall(source) + FAQ_CARD_RE.findall(source)
    for question_html, answer_html in candidates:
        question = text_content(question_html)
        answer = text_content(answer_html)
        pair = (question, answer)
        if question and answer and question.endswith("?") and pair not in pairs:
            pairs.append((question, answer))
    return pairs


def clean_schema(value, parent_key: str = ""):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in {"aggregateRating", "review"}:
                continue
            cleaned[key] = clean_schema(item, key)
        return cleaned
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                item_type = item.get("@type")
                types = item_type if isinstance(item_type, list) else [item_type]
                if "Review" in types or "AggregateRating" in types:
                    continue
            result.append(clean_schema(item, parent_key))
        return result
    if isinstance(value, str) and parent_key in {"@id", "url", "item", "contentUrl"}:
        return absolute_url(value)
    if isinstance(value, str) and parent_key == "image" and value.startswith("/"):
        return absolute_url(value)
    return value


def sync_faq_schema(data: dict, pairs: list[tuple[str, str]]) -> dict:
    if not pairs:
        return data
    graph = data.get("@graph") if isinstance(data, dict) else None
    nodes = graph if isinstance(graph, list) else [data]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if "FAQPage" not in types:
            continue
        node["mainEntity"] = [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in pairs
        ]
    return data


def finalize_html(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'href="([^"?#]*?)index\.html([?#][^"]*)?"',
        lambda match: f'href="{match.group(1) or "./"}{match.group(2) or ""}"',
        source,
    )
    if 'type="application/rss+xml"' not in updated:
        updated = updated.replace(
            "</head>",
            f'  <link rel="alternate" type="application/rss+xml" title="학습관리학원 RSS" href="{BASE_URL}/rss.xml">\n</head>',
            1,
        )

    pairs = visible_faqs(updated)

    def replace_script(match: re.Match[str]) -> str:
        try:
            data = json.loads(match.group(2))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSON-LD in {path}: {exc}") from exc
        data = clean_schema(data)
        data = sync_faq_schema(data, pairs)
        return match.group(1) + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + match.group(3)

    updated = SCRIPT_RE.sub(replace_script, updated)
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    changed = 0
    pages = sorted(ROOT.rglob("index.html"))
    for path in pages:
        changed += int(finalize_html(path))
    print(json.dumps({"pages": len(pages), "changed": changed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
