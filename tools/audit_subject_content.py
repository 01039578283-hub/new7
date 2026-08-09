#!/usr/bin/env python3
"""Read-only content-quality audit for the six subject-page families.

The structural auditor checks URLs and schema shape.  This companion focuses
on what a parent actually reads: answer-first copy, authoring-language leaks,
Korean join errors, FAQ/schema parity, and variation after local facts are
masked.  It never writes to the site tree.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
from collections import Counter
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "과목별학원"
CATEGORIES = (
    ("고등학생수학학원", "고등학생 수학학원"),
    ("고등학생영어학원", "고등학생 영어학원"),
    ("중학생수학학원", "중학생 수학학원"),
    ("중학생영어학원", "중학생 영어학원"),
    ("초등학생수학학원", "초등학생 수학학원"),
    ("초등학생영어학원", "초등학생 영어학원"),
)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.I | re.S)

BLOCKING_PATTERNS = {
    "double_recheck": re.compile(r"재확인\s+확인"),
    "weekly_study_review": re.compile(r"주간\s+학습\s+복습"),
    "repeated_learning": re.compile(r"학습(?:\s+학습)+"),
    "repeated_student": re.compile(r"(?:초등학생|중학생|고등학생)\s+학생"),
    "repeated_case": re.compile(r"경우인\s+경우"),
    "double_demonstrative": re.compile(r"(?:이\s+){2,}(?:영어|수학)\s+관리\s+기준"),
    "double_possessive": re.compile(r"(?:영어|수학)\s+(?:학습|관리)\s+기준의\s+[가-힣]+의"),
    "damaged_school_name": re.compile(r"(?:서|상|신|강|중|국|심|효|해|퇴계|덕|세)안내"),
    "author_body": re.compile(r"(?:^|[.!?]\s+)본문은\s+"),
    "author_explanatory_copy": re.compile(r"설명문에\s+넣기\s+좋게"),
    "author_schema": re.compile(r"(?:JSON-LD|JSON)\s*(?:구조화\s*데이터)?\s*요약|구조화\s*데이터\s*요약"),
}
STYLE_PATTERNS = {
    "check_check_join": re.compile(r"(?:점검|보완)\s+확인(?:\s+(?:질문|포인트|항목|기준))?"),
    "robot_english_reference": re.compile(r"이\s+영어\s+관리\s+기준"),
    "robot_math_reference": re.compile(r"이\s+수학\s+관리\s+기준"),
    "content_narration": re.compile(r"(?:학원|안내)\s+콘텐츠는"),
}
THRESHOLDS = {
    "meta_masked_unique": 120,
    "summary_masked_unique": 180,
    "faq_question_set_masked_unique": 120,
    "case_set_masked_unique": 180,
}


def plain(value: str) -> str:
    value = SCRIPT_RE.sub(" ", value)
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()


def capture(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def capture_all(pattern: str, source: str) -> list[str]:
    return [plain(value) for value in re.findall(pattern, source, re.I | re.S)]


def graph_from(source: str) -> list[dict]:
    raw = capture(r'<script\s+type="application/ld\+json">(.*?)</script>', source)
    if not raw:
        return []
    try:
        graph = json.loads(raw).get("@graph", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    return graph if isinstance(graph, list) else []


def fact_tokens(graph: list[dict], locality: str, label: str, slug: str) -> list[str]:
    tokens = [locality, label, label.replace(" ", ""), slug]
    for node in graph:
        node_type = node.get("@type")
        node_types = {node_type} if isinstance(node_type, str) else {
            value for value in node_type or [] if isinstance(value, str)
        }
        if {"EducationalOrganization", "LocalBusiness"}.intersection(node_types):
            if isinstance(node.get("name"), str):
                tokens.append(node["name"])
            address = node.get("address", {})
            if isinstance(address, dict):
                tokens.extend(
                    address[key] for key in ("streetAddress", "addressLocality", "addressRegion")
                    if isinstance(address.get(key), str)
                )
        if "Article" in node_types:
            tokens.extend(
                value["name"] for value in node.get("mentions", [])
                if isinstance(value, dict) and isinstance(value.get("name"), str)
            )
    return sorted(set(filter(None, tokens)), key=len, reverse=True)


def mask(value: str, tokens: list[str]) -> str:
    value = plain(value)
    for token in tokens:
        if len(token) > 1:
            value = value.replace(token, " {FACT} ")
    value = re.sub(r"\d+(?:[.,]\d+)*", " {NUMBER} ", value)
    return re.sub(r"\s+", " ", re.sub(r"[^가-힣A-Za-z]+", " ", value)).strip()


def shingles(value: str, size: int = 5) -> set[str]:
    """Use word shingles so ordinary Korean syllables do not inflate overlap."""
    tokens = re.findall(r"[가-힣A-Za-z]+", value)
    return {
        "\x1f".join(tokens[index:index + size])
        for index in range(max(0, len(tokens) - size + 1))
    }


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def percentile(values: list[float], point: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * point)] if ordered else 0.0


def snippet(value: str, match: re.Match[str], width: int = 85) -> str:
    start = max(0, match.start() - width)
    end = min(len(value), match.end() + width)
    return value[start:end]


def audit_category(directory: str, label: str) -> tuple[dict, list[str]]:
    category_root = SUBJECT_ROOT / directory
    rows = []
    errors: list[str] = []
    issue_samples: dict[str, list[dict]] = {}
    issue_pages: dict[str, set[str]] = {
        name: set() for name in (*BLOCKING_PATTERNS, *STYLE_PATTERNS)
    }
    for path in sorted(category_root.glob("*/index.html")):
        source = path.read_text(encoding="utf-8")
        graph = graph_from(source)
        title = plain(capture(r"<h1[^>]*>(.*?)</h1>", source))
        locality = title[:-len(label)].strip() if title.endswith(label) else path.parent.name
        tokens = fact_tokens(graph, locality, label, path.parent.name)
        meta = capture(r'<meta\s+name="description"\s+content="([^"]*)"', source)
        summary = plain(capture(
            r'<section[^>]*class="[^"]*academy-summary[^"]*"[^>]*>(.*?)</section>', source
        ))
        article_html = capture(
            r'<article[^>]*class="[^"]*academy-article[^"]*"[^>]*>(.*?)</article>', source
        )
        article = plain(article_html)
        faq_questions = capture_all(
            r"<details[^>]*>\s*<summary[^>]*>(.*?)</summary>", source
        )
        faq_answers = capture_all(
            r"<details[^>]*>\s*<summary[^>]*>.*?</summary>\s*<p[^>]*>(.*?)</p>\s*</details>", source
        )
        cases = capture_all(
            r'<blockquote[^>]*class="[^"]*academy-case-card[^"]*"[^>]*>(.*?)</blockquote>', source
        )
        json_faq: list[tuple[str, str]] = []
        for node in graph:
            if node.get("@type") == "FAQPage":
                json_faq = [
                    (item.get("name", ""), item.get("acceptedAnswer", {}).get("text", ""))
                    for item in node.get("mainEntity", [])
                ]
        if faq_questions != [question for question, _ in json_faq] or faq_answers != [answer for _, answer in json_faq]:
            errors.append(f"{path.relative_to(ROOT)}: visible FAQ != FAQPage JSON-LD")

        visible = plain(SCRIPT_RE.sub(" ", source))
        inspection = " ".join((meta, visible))
        for name, pattern in {**BLOCKING_PATTERNS, **STYLE_PATTERNS}.items():
            match = pattern.search(inspection)
            if not match:
                continue
            relative = str(path.relative_to(ROOT))
            issue_pages[name].add(relative)
            samples = issue_samples.setdefault(name, [])
            if len(samples) < 5:
                samples.append({"file": relative, "text": snippet(inspection, match)})

        rows.append({
            "path": str(path.relative_to(ROOT)),
            "locality": locality,
            "meta": meta,
            "summary": summary,
            "article": article,
            "questions": faq_questions,
            "answers": faq_answers,
            "cases": cases,
            "tokens": tokens,
        })

    def signatures(field: str, sequence: bool = False) -> dict[str, dict[str, int]]:
        def raw_value(row: dict) -> str | tuple[str, ...]:
            if sequence:
                return tuple(plain(item) for item in row[field])
            return plain(row[field])

        def masked_value(row: dict) -> str | tuple[str, ...]:
            if sequence:
                return tuple(mask(item, row["tokens"]) for item in row[field])
            return mask(row[field], row["tokens"])

        exact = Counter(raw_value(row) for row in rows)
        masked = Counter(masked_value(row) for row in rows)
        return {
            "exact": {
                "unique": len(exact),
                "top_reuse": max(exact.values(), default=0),
            },
            "masked": {
                "unique": len(masked),
                "top_reuse": max(masked.values(), default=0),
            },
        }

    article_sets = [shingles(mask(row["article"], row["tokens"])) for row in rows]
    similarities = [jaccard(article_sets[left], article_sets[right]) for left, right in combinations(range(len(rows)), 2)]
    variation = {
        "meta": signatures("meta"),
        "summary": signatures("summary"),
        "faq_question_set": signatures("questions", sequence=True),
        "case_set": signatures("cases", sequence=True),
        "article": signatures("article"),
    }
    stats = {
        "pages": len(rows),
        "meta_length": {
            "min": min((len(row["meta"]) for row in rows), default=0),
            "median": statistics.median((len(row["meta"]) for row in rows)) if rows else 0,
            "max": max((len(row["meta"]) for row in rows), default=0),
        },
        "variation": variation,
        "article_similarity": {
            "average": round(statistics.mean(similarities), 4) if similarities else 0,
            "p95": round(percentile(similarities, 0.95), 4),
            "maximum": round(max(similarities), 4) if similarities else 0,
            "pairs_at_or_above_0_75": sum(value >= 0.75 for value in similarities),
        },
        "issues": {name: len(paths) for name, paths in issue_pages.items()},
        "samples": issue_samples,
    }
    if len(rows) != 371:
        errors.append(f"{directory}: expected 371 detail pages, got {len(rows)}")
    for metric, threshold in THRESHOLDS.items():
        section, key = metric.rsplit("_masked_unique", 1)[0], "unique"
        lookup = {
            "meta": stats["variation"]["meta"]["masked"][key],
            "summary": stats["variation"]["summary"]["masked"][key],
            "faq_question_set": stats["variation"]["faq_question_set"]["masked"][key],
            "case_set": stats["variation"]["case_set"]["masked"][key],
        }[section]
        if lookup < threshold:
            errors.append(f"{directory}: {metric}={lookup} below {threshold}")
    if stats["article_similarity"]["pairs_at_or_above_0_75"]:
        errors.append(f"{directory}: article pairs >= 0.75")
    for name in BLOCKING_PATTERNS:
        if stats["issues"][name]:
            errors.append(f"{directory}: {name} in {stats['issues'][name]} page(s)")
    return stats, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="과목별학원 콘텐츠 품질 읽기 전용 감사")
    parser.add_argument("--no-fail", action="store_true", help="결함이 있어도 종료 코드 0을 반환")
    parser.add_argument("--output", type=Path, help="JSON 보고서를 선택 경로에 저장")
    args = parser.parse_args()

    report = {"categories": {}, "errors": []}
    for directory, label in CATEGORIES:
        stats, errors = audit_category(directory, label)
        report["categories"][directory] = stats
        report["errors"].extend(errors)
    report["digest"] = hashlib.sha256(
        json.dumps(report["categories"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if report["errors"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
