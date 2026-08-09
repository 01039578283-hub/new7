from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import generate_subject_pages as generator


ROOT = generator.ROOT
TARGET_ROOT = generator.TARGET_ROOT
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def visible_text(source: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", source, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return generator.normalize(value)


def json_graph(source: str, path: Path) -> list[dict]:
    matches = JSON_LD_RE.findall(source)
    if len(matches) != 1:
        raise ValueError(f"{path}: expected one JSON-LD block, found {len(matches)}")
    value = json.loads(matches[0])
    graph = value.get("@graph", []) if isinstance(value, dict) else []
    if not isinstance(graph, list):
        raise ValueError(f"{path}: JSON-LD @graph is not a list")
    return [item for item in graph if isinstance(item, dict)]


def has_type(node: dict, expected: str) -> bool:
    value = node.get("@type")
    return expected in value if isinstance(value, list) else value == expected


def add_sample(samples: dict[str, list[dict]], key: str, payload: dict) -> None:
    if len(samples[key]) < 12:
        samples[key].append(payload)


def audit() -> dict:
    center_rows = generator.load_csv("센터정보 정리.csv")
    center_by_locality = {row["근처 수업가능 동네"]: row for row in center_rows}
    category_counts: dict[str, Counter] = {
        config["slug"]: Counter() for config in generator.CATEGORIES
    }
    samples: dict[str, list[dict]] = defaultdict(list)
    organization_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    local_business_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    organization_id_owners: dict[str, set[tuple[str, str]]] = defaultdict(set)
    local_business_id_owners: dict[str, set[tuple[str, str]]] = defaultdict(set)
    detail_pages = 0

    for config in generator.CATEGORIES:
        category_dir = TARGET_ROOT / config["slug"]
        detail_files = sorted(category_dir.glob("*/index.html"))
        category = category_counts[config["slug"]]
        category["pages"] = len(detail_files)
        for path in detail_files:
            detail_pages += 1
            locality = path.parent.name
            row = center_by_locality.get(locality)
            if row is None:
                category["missing_center_row"] += 1
                add_sample(samples, "missing_center_row", {"path": str(path.relative_to(ROOT))})
                continue

            allowed_schools = set(generator.schools_for(row, config["school_field"]))
            fact_context = {
                "schools": list(allowed_schools),
                "grades": generator.normalize(row.get(config["grade_field"], "")),
            }
            allowed_grades = set(generator.verified_grade_tokens(fact_context))
            source = path.read_text(encoding="utf-8")
            visible = visible_text(source)

            damaged = sorted(
                token for token in generator.SCHOOL_CORRUPTION_MAP
                if generator.contains_hangul_token(visible, token)
            )
            visible_schools = set(generator.school_names_in_text(visible))
            visible_school_like = set(generator.school_like_names_in_text(visible))
            wrong_schools = sorted((visible_schools | visible_school_like) - allowed_schools)
            wrong_grades = sorted(
                set(generator.grade_claim_tokens(visible)) - allowed_grades
            )
            if damaged:
                category["damaged_school_pages"] += 1
                category["damaged_school_tokens"] += len(damaged)
                category["damaged_school_occurrences"] += sum(
                    len(re.findall(
                        rf"(?<![가-힣A-Za-z0-9]){re.escape(token)}(?![가-힣A-Za-z0-9])",
                        visible,
                    ))
                    for token in damaged
                )
                add_sample(samples, "damaged_school", {
                    "path": str(path.relative_to(ROOT)), "tokens": damaged,
                })
            if wrong_schools:
                category["wrong_school_pages"] += 1
                category["wrong_school_tokens"] += len(wrong_schools)
                add_sample(samples, "wrong_school", {
                    "path": str(path.relative_to(ROOT)), "tokens": wrong_schools,
                    "allowed": sorted(allowed_schools),
                })
            if wrong_grades:
                category["wrong_grade_pages"] += 1
                category["wrong_grade_tokens"] += len(wrong_grades)
                add_sample(samples, "wrong_grade", {
                    "path": str(path.relative_to(ROOT)), "tokens": wrong_grades,
                    "allowed": sorted(allowed_grades),
                })

            try:
                graph = json_graph(source, path)
            except (ValueError, json.JSONDecodeError) as exc:
                category["jsonld_errors"] += 1
                add_sample(samples, "jsonld_error", {
                    "path": str(path.relative_to(ROOT)), "error": str(exc),
                })
                continue

            organizations = [node for node in graph if has_type(node, "EducationalOrganization")]
            if len(organizations) != 1:
                category["organization_count_errors"] += 1
            else:
                organization = organizations[0]
                address = organization.get("address", {})
                address_value = address.get("streetAddress", "") if isinstance(address, dict) else ""
                entity_key = (
                    generator.normalize(str(organization.get("name", ""))),
                    generator.normalize(str(address_value)),
                )
                organization_id = str(organization.get("@id", ""))
                if not organization_id:
                    category["missing_organization_id"] += 1
                else:
                    organization_ids[entity_key].add(organization_id)
                    organization_id_owners[organization_id].add(entity_key)

            local_businesses = [node for node in graph if has_type(node, "LocalBusiness")]
            if len(local_businesses) != 1:
                category["local_business_count_errors"] += 1
            else:
                local_business = local_businesses[0]
                address = local_business.get("address", {})
                address_value = address.get("streetAddress", "") if isinstance(address, dict) else ""
                entity_key = (
                    generator.normalize(str(local_business.get("name", ""))),
                    generator.normalize(str(address_value)),
                )
                local_business_id = str(local_business.get("@id", ""))
                if not local_business_id:
                    category["missing_local_business_id"] += 1
                else:
                    local_business_ids[entity_key].add(local_business_id)
                    local_business_id_owners[local_business_id].add(entity_key)

            articles = [node for node in graph if has_type(node, "Article")]
            mention_names: list[str] = []
            if len(articles) == 1:
                mentions = articles[0].get("mentions", [])
                if isinstance(mentions, list):
                    mention_names = [
                        generator.normalize(str(item.get("name", "")))
                        for item in mentions
                        if isinstance(item, dict) and has_type(item, "School")
                    ]
            if len(mention_names) != len(set(mention_names)):
                category["duplicate_school_mentions_pages"] += 1
                add_sample(samples, "duplicate_school_mentions", {
                    "path": str(path.relative_to(ROOT)), "mentions": mention_names,
                })
            generic_mentions = sorted({
                name for name in mention_names
                if not name or generator.GENERIC_SCHOOL_VALUE_RE.search(name)
            })
            normalized_mentions = {
                school
                for name in mention_names
                if not generator.GENERIC_SCHOOL_VALUE_RE.search(name)
                for school in generator.split_school_names(name)
            }
            wrong_mentions = sorted(normalized_mentions - allowed_schools)
            if generic_mentions:
                category["generic_school_mentions_pages"] += 1
                add_sample(samples, "generic_school_mentions", {
                    "path": str(path.relative_to(ROOT)), "mentions": generic_mentions,
                })
            if wrong_mentions:
                category["wrong_school_mentions_pages"] += 1
                add_sample(samples, "wrong_school_mentions", {
                    "path": str(path.relative_to(ROOT)), "mentions": wrong_mentions,
                    "allowed": sorted(allowed_schools),
                })

    fragmented = {
        " | ".join(key): sorted(value)
        for key, value in organization_ids.items()
        if len(value) > 1
    }
    fragmented_local_businesses = {
        " | ".join(key): sorted(value)
        for key, value in local_business_ids.items()
        if len(value) > 1
    }
    organization_id_collisions = {
        entity_id: [" | ".join(owner) for owner in sorted(owners)]
        for entity_id, owners in organization_id_owners.items()
        if len(owners) > 1
    }
    local_business_id_collisions = {
        entity_id: [" | ".join(owner) for owner in sorted(owners)]
        for entity_id, owners in local_business_id_owners.items()
        if len(owners) > 1
    }
    for key, ids in list(fragmented.items())[:12]:
        add_sample(samples, "fragmented_organization_id", {
            "center": key, "id_count": len(ids), "ids": ids[:4],
        })

    totals = Counter()
    for counts in category_counts.values():
        totals.update(counts)
    totals["fragmented_center_entities"] = len(fragmented)
    totals["center_entities"] = len(organization_ids)
    totals["fragmented_local_business_entities"] = len(fragmented_local_businesses)
    totals["local_business_entities"] = len(local_business_ids)
    totals["organization_id_collisions"] = len(organization_id_collisions)
    totals["local_business_id_collisions"] = len(local_business_id_collisions)
    blocking_keys = (
        "missing_center_row", "damaged_school_pages", "wrong_school_pages",
        "wrong_grade_pages", "jsonld_errors", "organization_count_errors",
        "duplicate_school_mentions_pages", "generic_school_mentions_pages",
        "wrong_school_mentions_pages", "fragmented_center_entities",
        "fragmented_local_business_entities", "missing_organization_id",
        "missing_local_business_id", "organization_id_collisions",
        "local_business_id_collisions", "local_business_count_errors",
    )
    passed = detail_pages == 2226 and not any(totals[key] for key in blocking_keys)
    return {
        "status": "pass" if passed else "fail",
        "detail_pages": detail_pages,
        "categories": {key: dict(value) for key, value in category_counts.items()},
        "totals": dict(totals),
        "samples": dict(samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit subject detail pages against verified center school/grade facts."
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--no-fail", action="store_true", help="Report issues without a non-zero exit.")
    args = parser.parse_args()
    report = audit()
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output + "\n", encoding="utf-8")
    print(output)
    if report["status"] != "pass" and not args.no_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
