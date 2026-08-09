from __future__ import annotations

import email.utils
import html
import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://xn--zb0b93vh4ggmeqzwda.com"
MAX_ITEMS = 20


def extract(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    return html.unescape(match.group(1).strip()) if match else ""


def main_text(source: str) -> str:
    """Return the complete visible main content as readable plain text.

    Naver treats RSS as a content feed, so an item should contain more than
    the short meta description.  Keeping the extraction in the generator also
    means future builds automatically publish the latest page body.
    """
    match = re.search(r"<main\b[^>]*>([\s\S]*?)</main>", source, re.I)
    fragment = match.group(1) if match else source
    fragment = re.sub(
        r"<(script|style|noscript|template)\b[^>]*>[\s\S]*?</\1>",
        " ",
        fragment,
        flags=re.I,
    )
    fragment = re.sub(
        r"</(?:address|article|aside|blockquote|dd|details|div|dl|dt|fieldset|figcaption|figure|footer|h[1-6]|header|li|main|nav|ol|p|section|summary|table|tbody|td|tfoot|th|thead|tr|ul)\s*>",
        "\n",
        fragment,
        flags=re.I,
    )
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment).replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in fragment.splitlines()]
    return "\n".join(line for line in lines if line)


def page_data(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    title = extract(r"<title>(.*?)</title>", source)
    meta_description = extract(r'<meta\s+name="description"\s+content="([^"]*)"', source)
    body = main_text(source)
    description = body or meta_description
    canonical = extract(r'<link\s+rel="canonical"\s+href="([^"]*)"', source)
    modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    return {
        "title": title,
        "description": description,
        "link": canonical,
        "pubDate": email.utils.format_datetime(modified),
    }


def selected_pages() -> list[Path]:
    pages = [
        ROOT / "index.html",
        ROOT / "학습가이드" / "index.html",
        ROOT / "전국학원" / "index.html",
        ROOT / "전국학원" / "불당동" / "고등수학학원" / "index.html",
        ROOT / "과목별학원" / "index.html",
        ROOT / "과목별학원" / "고등학생수학학원" / "index.html",
        ROOT / "과목별학원" / "고등학생영어학원" / "index.html",
        ROOT / "과목별학원" / "중학생수학학원" / "index.html",
        ROOT / "과목별학원" / "중학생영어학원" / "index.html",
        ROOT / "과목별학원" / "초등학생수학학원" / "index.html",
        ROOT / "과목별학원" / "초등학생영어학원" / "index.html",
    ]
    # RSS는 전체 대량 페이지 목록이 아니라 광역권별 대표 동네 안내만 포함합니다.
    region_seen: set[str] = set()
    for path in sorted((ROOT / "전국학원").glob("*/index.html")):
        source = path.read_text(encoding="utf-8")
        region = extract(r'<div class="local-badges">\s*<span>(.*?)</span>', source)
        if not region or region in region_seen:
            continue
        region_seen.add(region)
        pages.append(path)
        if len(pages) >= MAX_ITEMS:
            break
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in pages:
        if path.exists() and path not in seen:
            seen.add(path)
            unique.append(path)
    return unique[:MAX_ITEMS]


def main() -> None:
    pages = selected_pages()
    items = [page_data(path) for path in pages]
    if pages:
        latest_modified = datetime.fromtimestamp(
            max(path.stat().st_mtime for path in pages)
        ).astimezone()
    else:
        latest_modified = datetime.now().astimezone()
    latest = email.utils.format_datetime(latest_modified)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>학습관리학원 학습 안내</title>",
        f"    <link>{BASE_URL}/</link>",
        "    <description>학습관리 기준과 전국 지역별 상담 안내의 핵심 업데이트입니다.</description>",
        "    <language>ko-KR</language>",
        "    <generator>학습관리학원 RSS Generator</generator>",
        "    <ttl>60</ttl>",
        f'    <atom:link href="{BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />',
        f"    <lastBuildDate>{escape(latest)}</lastBuildDate>",
    ]
    for item in items:
        lines.extend(
            [
                "    <item>",
                f"      <title>{escape(item['title'])}</title>",
                f"      <link>{escape(item['link'])}</link>",
                f"      <guid isPermaLink=\"true\">{escape(item['link'])}</guid>",
                f"      <description>{escape(item['description'])}</description>",
                f"      <pubDate>{escape(item['pubDate'])}</pubDate>",
                "    </item>",
            ]
        )
    lines.extend(["  </channel>", "</rss>"])
    (ROOT / "rss.xml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated rss.xml with {len(items)} items")


if __name__ == "__main__":
    main()
