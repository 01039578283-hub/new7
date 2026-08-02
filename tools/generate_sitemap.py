from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://xn--zb0b93vh4ggmeqzwda.com"


def page_url(index_file: Path) -> str:
    relative = index_file.relative_to(ROOT)
    if relative.parts == ("index.html",):
        path = "/"
    else:
        path = "/" + "/".join(relative.parent.parts) + "/"
    return BASE_URL + quote(path, safe="/")


def priority_for(url: str) -> str:
    path = url.removeprefix(BASE_URL)
    depth = len([part for part in path.split("/") if part])
    if path == "/":
        return "1.0"
    if depth == 1:
        return "0.9"
    if depth == 2:
        return "0.8"
    return "0.7"


def changefreq_for(url: str) -> str:
    path = url.removeprefix(BASE_URL)
    if path == "/":
        return "weekly"
    if path.startswith("/%EC%A0%84%EA%B5%AD%ED%95%99%EC%9B%90/"):
        return "monthly"
    return "weekly"


def main() -> None:
    pages = sorted(ROOT.rglob("index.html"), key=page_url)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in pages:
        url = page_url(path)
        lastmod = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        lines.extend(
            [
                "  <url>",
                f"    <loc>{escape(url)}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                f"    <changefreq>{changefreq_for(url)}</changefreq>",
                f"    <priority>{priority_for(url)}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")

    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated sitemap.xml with {len(pages)} URLs")


if __name__ == "__main__":
    main()
