from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAV_RE = re.compile(
    r'(<nav\b[^>]*class=["\'][^"\']*\bnav-menu\b[^"\']*["\'][^>]*>)([\s\S]*?)(</nav>)',
    re.IGNORECASE,
)


def subject_href(page: Path) -> str:
    relative = os.path.relpath(ROOT / "과목별학원", page.parent).replace("\\", "/")
    if relative == ".":
        return "./"
    return relative.rstrip("/") + "/"


def update_page(page: Path) -> bool:
    source = page.read_text(encoding="utf-8")
    match = NAV_RE.search(source)
    if not match:
        return False
    body = match.group(2)
    if "\n" not in body and "과목별학원" in body:
        return False
    indent_match = re.search(r"\n([ \t]*)<a\b", body)
    indent = indent_match.group(1) if indent_match else "          "
    closing_indent = indent[:-2] if len(indent) >= 2 else ""
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if "과목별학원" not in body:
        lines.append(f'{indent}<a href="{subject_href(page)}">과목별학원</a>')
    normalized_body = "\n" + "\n".join(lines) + "\n" + closing_indent
    updated = source[: match.start(2)] + normalized_body + source[match.start(3) :]
    if updated == source:
        return False
    page.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    pages = sorted(ROOT.rglob("index.html"))
    changed = sum(update_page(page) for page in pages)
    print({"pages": len(pages), "changed": changed})


if __name__ == "__main__":
    main()
