from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import argparse
from collections import OrderedDict
from datetime import date
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT.parent / "참고자료"
SOURCE_DIR = REFERENCE / "사용한 원고" / "학습관리학원.com 추가 원고"
COMMON_DIR = REFERENCE / "공통자료"
TARGET_ROOT = ROOT / "과목별학원"
DOMAIN = "https://xn--zb0b93vh4ggmeqzwda.com"
SITE_NAME = "학습관리학원"
PHONE = "010-6839-8283"
PHONE_LINK = "01068398283"
TODAY = date.today().isoformat()
SHARE_IMAGE_URL = DOMAIN + "/assets/generated/academy-hero-v2.webp"
SHARE_IMAGE_ALT = "학습관리학원 학생별 학습관리 안내 이미지"
REPRESENTATIVE_IMAGE_SOURCE = COMMON_DIR / "대표 이미지 url.csv"

CATEGORIES = [
    {
        "label": "고등학생 수학학원",
        "slug": "고등학생수학학원",
        "zip": "고등학생 수학학원.zip",
        "level": "고등학생",
        "subject": "수학",
        "school_field": "타깃학교\n(고)",
        "grade_field": "가능학년\n(수학)",
        "english": "HIGH SCHOOL MATH",
        "summary": "내신 범위와 모의 학습, 개념·문제 해석·서술형 풀이를 함께 확인하는 지역별 고등 수학 안내입니다.",
    },
    {
        "label": "고등학생 영어학원",
        "slug": "고등학생영어학원",
        "zip": "고등학생 영어학원.zip",
        "level": "고등학생",
        "subject": "영어",
        "school_field": "타깃학교\n(고)",
        "grade_field": "가능학년\n(영어)",
        "english": "HIGH SCHOOL ENGLISH",
        "summary": "학교 지문과 어휘·문법·독해·서술형의 연결을 확인하는 지역별 고등 영어 안내입니다.",
    },
    {
        "label": "중학생 수학학원",
        "slug": "중학생수학학원",
        "zip": "중학생 수학학원.zip",
        "level": "중학생",
        "subject": "수학",
        "school_field": "타깃학교\n(중)",
        "grade_field": "가능학년\n(수학)",
        "english": "MIDDLE SCHOOL MATH",
        "summary": "중학교 진도와 내신 범위, 개념·조건 해석·오답 재현 과정을 함께 확인하는 지역별 중등 수학 안내입니다.",
    },
    {
        "label": "중학생 영어학원",
        "slug": "중학생영어학원",
        "zip": "중학생 영어학원.zip",
        "level": "중학생",
        "subject": "영어",
        "school_field": "타깃학교\n(중)",
        "grade_field": "가능학년\n(영어)",
        "english": "MIDDLE SCHOOL ENGLISH",
        "summary": "중학교 교과 진도와 단어·문법·독해·서술형 연결을 살피는 지역별 중등 영어 안내입니다.",
    },
    {
        "label": "초등학생 수학학원",
        "slug": "초등학생수학학원",
        "zip": "초등학생 수학학원.zip",
        "level": "초등학생",
        "subject": "수학",
        "school_field": "타깃학교\n(초)",
        "grade_field": "가능학년\n(수학)",
        "english": "ELEMENTARY SCHOOL MATH",
        "summary": "연산 정확도와 개념 이해, 문장제 조건 해석, 풀이 습관을 함께 확인하는 지역별 초등 수학 안내입니다.",
    },
    {
        "label": "초등학생 영어학원",
        "slug": "초등학생영어학원",
        "zip": "초등학생 영어학원.zip",
        "level": "초등학생",
        "subject": "영어",
        "school_field": "타깃학교\n(초)",
        "grade_field": "가능학년\n(영어)",
        "english": "ELEMENTARY SCHOOL ENGLISH",
        "summary": "파닉스·어휘·문장 읽기와 쓰기, 복습 습관을 함께 확인하는 지역별 초등 영어 안내입니다.",
    },
]

# These terms describe an academy's administration, facilities, or delivery
# channel rather than a student's English/Math learning need.  Some supplied
# manuscripts use one as a rotating auxiliary keyword.  Never carry the raw
# claim into a public page; replace it with the page's verified learning focus.
UNVERIFIED_ACADEMY_TERM_RE = re.compile(
    r"(?:(?:학원\s*)?(?:온라인\s*수업|대면\s*수업|화상\s*수업|실시간\s*수업)|"
    r"학원\s*(?:자습실|스터디룸|"
    r"상담실|강의실|휴게실|사물함|교재실|자료실|예약\s*관리|전자\s*계약|관리\s*솔루션|"
    r"문자\s*발송|미납\s*관리|출결\s*앱|데스크|데이터\s*관리|코디네이터|창업|"
    r"개인정보\s*관리|안전\s*관리|방역\s*관리|청결\s*관리|출입\s*관리|보안\s*관리|"
    r"수강생\s*관리|회원\s*관리|고객\s*관리|결제\s*관리|결제\s*시스템|매출\s*관리|"
    r"수납\s*관리|문서\s*관리|관리\s*앱|관리\s*프로그램))"
    r"(?:\s*(?:시스템|프로그램|앱))?"
)


def related_categories_for(config: dict[str, str]) -> list[dict[str, str]]:
    """Order nearby guides by user intent, not by generator declaration order."""
    order = {item["slug"]: index for index, item in enumerate(CATEGORIES)}
    candidates = [item for item in CATEGORIES if item["slug"] != config["slug"]]
    return sorted(
        candidates,
        key=lambda item: (
            0 if item["level"] == config["level"] else 1 if item["subject"] == config["subject"] else 2,
            order[item["slug"]],
        ),
    )


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


SCHOOL_NAME_RE = re.compile(
    r"(?<![가-힣A-Za-z0-9])"
    r"([가-힣A-Za-z0-9]{1,24}(?:초등학교|중학교|고등학교|초|중|고))"
    r"(?=$|[\s,.;:!?()\[\]·/]|은|는|이|가|을|를|과|와|도|만|의|처럼|에서|에는|으로|로|부터|까지|입니다|이고|이며)"
)
GENERIC_SCHOOL_VALUE_RE = re.compile(
    r"(?:지역\s*내|관내|인근|주변).*(?:모든|전체)?.*학교.*가능|"
    r"(?:모든|전체)\s*(?:초등학교|중학교|고등학교)\s*가능"
)


def split_school_names(value: str) -> list[str]:
    """Normalize the heterogeneous school-list separators in the center CSV.

    Some rows use commas, while others use middle dots, slashes, newlines, or
    spaces.  Generic availability notes are not school entities and therefore
    must never become ``School`` nodes or visible school tags.
    """
    raw = normalize(value)
    if not raw or GENERIC_SCHOOL_VALUE_RE.search(raw):
        return []
    values: list[str] = []
    for chunk in re.split(r"[,·./|;\n]+", value or ""):
        chunk = normalize(chunk)
        if not chunk:
            continue
        tokens = [normalize(item) for item in chunk.split() if normalize(item)]
        if len(tokens) > 1 and all(SCHOOL_NAME_RE.fullmatch(item) for item in tokens):
            values.extend(tokens)
            continue
        matches = [normalize(item) for item in SCHOOL_NAME_RE.findall(chunk)]
        if matches:
            values.extend(matches)
        elif SCHOOL_NAME_RE.fullmatch(chunk):
            values.append(chunk)
    return list(dict.fromkeys(values))


def clean_html(value: str) -> str:
    """Keep generated HTML deterministic and free of whitespace-only lines."""
    return "\n".join(line.rstrip() for line in value.splitlines()) + "\n"


def compact_locality(value: str) -> str:
    return re.sub(r"\s+", "", normalize(value))


SPECIAL_LOCALITY_ALIASES = {
    "당진읍내동": "읍내동",
    "부천상동": "상동",
    "전주장동": "장동",
}


def national_slug_for(locality: str) -> str:
    national_root = ROOT / "전국학원"
    names = [path.name for path in national_root.iterdir() if path.is_dir()]
    if locality in names:
        return locality
    by_compact = {compact_locality(name): name for name in names}
    compact = compact_locality(locality)
    if compact in by_compact:
        return by_compact[compact]
    alias = SPECIAL_LOCALITY_ALIASES.get(compact, "")
    if alias in names:
        return alias
    raise ValueError(f"Nationwide locality page missing: {locality}")


def absolute_url(*parts: str) -> str:
    path = "/" + "/".join(part.strip("/") for part in parts if part) + "/"
    return DOMAIN + quote(path, safe="/")


def load_csv(name: str) -> list[dict[str, str]]:
    with (COMMON_DIR / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_verified_school_names() -> tuple[str, ...]:
    """Return every school name that appears in the supplied center data.

    The list is used only to detect a school from a different school level in
    a manuscript sentence.  The category-specific school column remains the
    sole source of names that may be rendered on a page.
    """
    values: set[str] = set()
    for row in load_csv("센터정보 정리.csv"):
        for field in ("타깃학교\n(초)", "타깃학교\n(중)", "타깃학교\n(고)"):
            values.update(split_school_names(row.get(field, "")))
    return tuple(sorted(values, key=lambda item: (-len(item), item)))


VERIFIED_SCHOOL_NAMES = load_verified_school_names()
VERIFIED_SCHOOL_NAME_SET = frozenset(VERIFIED_SCHOOL_NAMES)


def build_school_corruption_map() -> dict[str, tuple[str, ...]]:
    """Map legacy whole-word ``원고 -> 안내`` damage back to source schools."""
    values: dict[str, set[str]] = {}
    for name in VERIFIED_SCHOOL_NAMES:
        for token in ("원고", "원중", "원초"):
            if token not in name:
                continue
            damaged = name.replace(token, "안내")
            values.setdefault(damaged, set()).add(name)
    return {
        damaged: tuple(sorted(names))
        for damaged, names in sorted(values.items(), key=lambda item: (-len(item[0]), item[0]))
    }


SCHOOL_CORRUPTION_MAP = build_school_corruption_map()


def protect_verified_school_tokens(value: str) -> tuple[str, dict[str, str]]:
    """Hide verified school names while authoring-language replacements run."""
    protected: dict[str, str] = {}
    placeholders_by_name: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        name = normalize(match.group(1))
        if name not in VERIFIED_SCHOOL_NAME_SET:
            return match.group(0)
        if name not in placeholders_by_name:
            placeholder = f"__VERIFIED_SCHOOL_TOKEN_{len(placeholders_by_name)}__"
            placeholders_by_name[name] = placeholder
            protected[placeholder] = name
        return placeholders_by_name[name]

    return SCHOOL_NAME_RE.sub(replace, value), protected


def restore_verified_school_tokens(value: str, protected: dict[str, str]) -> str:
    text = value
    for placeholder, name in protected.items():
        text = text.replace(placeholder, name)
    return text


def parse_sections(text: str) -> dict[str, str]:
    marker = re.compile(r"^\[([^\]]+)\]\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end():end].strip()
    return sections


def parse_body(body: str) -> tuple[str, list[tuple[str, list[str]]]]:
    heading = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading.finditer(body))
    intro = body[: matches[0].start()].strip() if matches else body.strip()
    sections: list[tuple[str, list[str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[match.end():end].strip()
        paragraphs = [normalize(part) for part in re.split(r"\n\s*\n", content) if normalize(part)]
        sections.append((normalize(match.group(1)), paragraphs))
    return normalize(intro), sections


def parse_faq(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^Q(?:\d+)?\.\s*(.+?)\s*\nA(?:\d+)?\.\s*(.+?)(?=\n(?:\s*\n)?Q(?:\d+)?\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [(normalize(question), normalize(answer)) for question, answer in pattern.findall(text)]


def parse_cases(text: str) -> list[str]:
    value = text.strip()
    if not value:
        return []
    bullet_cases = [
        normalize(item)
        for item in re.findall(r"(?ms)^\s*-\s*(.+?)(?=^\s*-\s*|\Z)", value)
        if normalize(item)
    ]
    if len(bullet_cases) >= 2:
        return bullet_cases
    # Elementary-math manuscripts place two labeled reviews in one block,
    # separated only by "또 다른 후기:". Preserve them as two visible cards.
    if "또 다른 후기:" in value:
        first, second = value.split("또 다른 후기:", 1)
        cases = [normalize(first), normalize("또 다른 후기: " + second)]
        if all(cases):
            return cases
    chunks = re.split(r"(?=후기\s*(?:예시|형\s*문안)?\s*\d+\.)", value)
    cases = [normalize(chunk) for chunk in chunks if normalize(chunk)]
    if len(cases) == 1:
        paragraphs = [normalize(part) for part in re.split(r"\n\s*\n", value) if normalize(part)]
        return paragraphs or cases
    return cases


def stable_choice(seed: str, values: list[str]) -> str:
    """Return a repeatable variant without relying on process-randomized hash()."""
    if not values:
        return ""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return values[int.from_bytes(digest[:4], "big") % len(values)]


def extract_reference_terms(value: str) -> tuple[str, ...]:
    """Find spreadsheet-style reference terms that should not be copied raw.

    The supplied manuscripts intentionally rotate one auxiliary keyword per
    locality.  Some are useful learning concepts, while others describe
    facilities or academy administration.  We retain the page variety but
    replace every such term with a student-facing, subject-specific learning
    focus instead of exposing an unverified operation or feature.
    """
    patterns = (
        r"참고\s*키워드(?:는|은|이|가|을|를|과|와)?\s+"
        r"(?:항목\s*)?[\(\[‘“\"']?\s*([가-힣A-Za-z0-9·_-]+?)"
        r"(?:은|는|이|가|을|를|과|와|으로|로)?(?=\s*(?:함께|같은|처럼|관점|관련|포인트|내용|항목|[,.)]|$))",
        r"(?:오답 관리와|학습 관리와|내신 준비와|가정 확인법과|시험 준비와)\s*"
        r"([가-힣A-Za-z0-9·_-]+)\s*(?:내용|확인 질문|연결점|포인트|관련 기준)",
        r"(?m)^##\s+참고\s*키워드\s+(.+?)(?:으로|로)\s+보는\s+관리\s+포인트\s*$",
        r"참고\s*키워드\s+([가-힣A-Za-z0-9·_-]+?)(?=(?:으로|로|은|는|이|가|을|를|과|와)(?:\s|[,.)]|$))",
        r"([가-힣A-Za-z0-9·_-]+?)(?:은|는)\s+참고\s*키워드로",
        r"([가-힣A-Za-z0-9·_-]+?)(?:과|와)\s+영어\s+수학\s+키워드",
        # Elementary-math manuscripts rotate a single auxiliary term and
        # repeat it in the final summary.  These anchored forms identify that
        # term without treating ordinary subject sentences as keywords.
        r"(?:^|[.!?]\s+)([가-힣A-Za-z0-9· _-]+?)\s+관련\s+상담\s+포인트는\s+학습\s+기록과",
        r"(?:^|[.!?]\s+)([가-힣A-Za-z0-9· _-]+?)\s+키워드는\s+과장된\s+결과\s+표현이\s+아니라",
        r"(?:^|[.!?]\s+)([가-힣A-Za-z0-9· _-]+?)(?:을|를)\s+함께\s+볼\s+때\s+초등\s+수학의",
        r"(?m)^##\s+(.+?)까지\s+함께\s+확인하는\s+학부모를\s+위한\s+안내\s*$",
        r"([가-힣A-Za-z0-9· _-]+?)\s+키워드와\s+연결되는\s+관리도\s+결국",
        r"수업\s+방식\s+관련\s+키워드인\s+(.+?)(?:은|는)\s+아이의",
        r"(?:^|[.!?]\s+)([가-힣A-Za-z0-9· _-]+?)(?:을|를)\s+함께\s+검색한\s+경우에도",
        r"(?:^|[\n.!?]\s*)([가-힣A-Za-z0-9· _-]+?)(?:을|를)\s+함께\s+볼\s+때",
        r"(?:^|[\n.!?]\s*)([가-힣A-Za-z0-9· _-]+?)처럼\s+운영과\s+관련된\s+키워드는",
    )
    found: list[str] = []
    for pattern in patterns:
        for term in re.findall(pattern, value):
            clean = normalize(term)
            if clean and clean not in {"자체", "그"} and clean not in found:
                found.append(clean)
    return tuple(sorted(found, key=lambda item: (-len(item), item)))


def learning_focus_phrase(seed: str, subject: str) -> str:
    if subject == "수학":
        focuses = [
            "개념 빈칸 기록", "문제 조건 표시 습관", "풀이 근거 서술", "계산 과정 검산",
            "서술형 풀이 순서", "오답 원인 분류", "시험 범위 복습 순서", "단원 연결 기록",
            "과제 실행 기록", "복습 시점 계획", "풀이 시간 배분", "주간 학습 계획",
        ]
    else:
        focuses = [
            "어휘 누적 기록", "문법 적용 근거", "독해 근거 표시", "문장 구조 해석",
            "서술형 문장 작성", "교과서 지문 복습", "오답 문장 재작성", "시험 범위 정리",
            "과제 실행 기록", "복습 시점 계획", "읽기 속도 조절", "주간 영어 계획",
        ]
    # These phrases are inserted before words such as ``확인 질문`` and
    # ``상담 포인트`` in several manuscript families.  Return a complete,
    # natural noun phrase rather than crossing an object with an action; the
    # latter produced joins such as "재확인 확인" and "주간 학습 복습".
    return stable_choice(f"{seed}|learning-focus", focuses)


def replace_reference_term(value: str, term: str, replacement: str) -> str:
    """Replace a rotated source term and repair particles around it."""
    text = value
    prefix = rf"(?<![가-힣A-Za-z0-9]){re.escape(term)}"
    for pair, suffix in {
        "은/는": r"(?:은|는)",
        "이/가": r"(?:이|가)",
        "을/를": r"(?:을|를)",
        "과/와": r"(?:과|와)",
        "으로/로": r"(?:으로|로)",
    }.items():
        text = re.sub(
            prefix + suffix,
            lambda _match, word=replacement, particle_pair=pair: korean_josa(word, particle_pair),
            text,
        )
    text = re.sub(prefix + r"(?:이)?라는", replacement + "이라는", text)
    for suffix in ("처럼", "같은", "까지", "부터", "보다", "관련", "관점", "포인트", "내용", "도", "만", "에", "의", "에서"):
        text = re.sub(prefix + re.escape(suffix), replacement + suffix, text)
    return re.sub(prefix + r"(?![가-힣A-Za-z0-9])", replacement, text)


def load_representative_images() -> list[str]:
    """Load the verified representative-image URLs used by the existing site."""
    values: list[str] = []
    seen: set[str] = set()
    with REPRESENTATIVE_IMAGE_SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            for cell in row:
                match = re.search(r'src=["\']([^"\']+)["\']', cell or "", re.IGNORECASE)
                if not match:
                    continue
                value = match.group(1).strip()
                if value and value not in seen:
                    seen.add(value)
                    values.append(value)
    if not values:
        raise ValueError(f"Representative image URLs missing: {REPRESENTATIVE_IMAGE_SOURCE}")
    return values


REPRESENTATIVE_IMAGES = load_representative_images()


def representative_image_url(canonical: str) -> str:
    return stable_choice(f"representative|{canonical}", REPRESENTATIVE_IMAGES)


def korean_josa(value: str, pair: str) -> str:
    """Attach a Korean particle, including the ㄹ + 로 exception."""
    pairs = {
        "은/는": ("은", "는"),
        "이/가": ("이", "가"),
        "을/를": ("을", "를"),
        "과/와": ("과", "와"),
        "으로/로": ("으로", "로"),
    }
    with_batchim, without_batchim = pairs[pair]
    last_hangul = next((char for char in reversed(normalize(value)) if "가" <= char <= "힣"), "")
    if not last_hangul:
        return value + without_batchim
    jongseong = (ord(last_hangul) - 0xAC00) % 28
    if pair == "으로/로" and jongseong in {0, 8}:
        particle = without_batchim
    else:
        particle = with_batchim if jongseong else without_batchim
    return value + particle


def content_context(
    *, title: str, locality: str, slug: str, row: dict[str, str], config: dict[str, str],
    source_text: str,
) -> dict[str, object]:
    seed = f"{config['slug']}|{slug}|{locality}"
    return {
        "seed": seed,
        "title": title,
        "locality": locality,
        "region": normalize(f"{row.get('지역', '')} {row.get('시or구', '')}"),
        "center": normalize(row.get("센터명", "")) or f"{locality} 학습센터",
        "address": normalize(row.get("센터 주소", "")),
        "schools": schools_for(row, config["school_field"]),
        "grades": normalize(row.get(config["grade_field"], "")),
        "level": config["level"],
        "subject": config["subject"],
        "category": config["slug"],
        "reference_terms": extract_reference_terms(source_text),
        "learning_focus": learning_focus_phrase(seed, config["subject"]),
    }


def repair_named_josa(value: str, context: dict[str, object]) -> str:
    """Correct particles attached to generated locality/center strings."""
    text = value
    address = str(context["address"])
    address_token = "__VERIFIED_CENTER_ADDRESS__"
    locality = str(context["locality"])
    protected_road_tokens: dict[str, str] = {}
    # A locality can also be the first part of a legal road name (덕풍동로,
    # 석동로, 율하동로, 좌동로). Protect the verified address before fixing
    # particles so those road names remain byte-for-byte intact.
    if address and address in text:
        text = text.replace(address, address_token)
    if address and locality:
        for index, token in enumerate(normalize(address).split()):
            clean_token = token.strip(",.;:()[]")
            if clean_token.startswith(locality) and clean_token != locality:
                placeholder = f"__VERIFIED_LOCAL_ROAD_{index}__"
                if clean_token in text:
                    text = text.replace(clean_token, placeholder)
                    protected_road_tokens[placeholder] = clean_token
    for noun in (str(context["locality"]), str(context["center"])):
        if not noun:
            continue
        for pair, forms in {
            "은/는": ("은", "는"),
            "이/가": ("이", "가"),
            "을/를": ("을", "를"),
            "과/와": ("과", "와"),
            "으로/로": ("으로", "로"),
        }.items():
            suffix = "(?:으)?로" if pair == "으로/로" else "(?:" + "|".join(forms) + ")"
            text = re.sub(
                re.escape(noun) + suffix + r"(?=\s|[,.;:!?]|$)",
                lambda _match, word=noun, particle_pair=pair: korean_josa(word, particle_pair),
                text,
            )
    if address:
        text = text.replace(address_token, address)
    for placeholder, road_token in protected_road_tokens.items():
        text = text.replace(placeholder, road_token)
    if address:
        # A raw address often ends in 호/층/점. Appending 로 mechanically makes
        # malformed strings, so express the relation with "기준으로" instead.
        text = re.sub(
            re.escape(address) + r"(?:으)?로(?=\s|[,.;:!?]|$)",
            address + " 기준으로",
            text,
        )
        for pair, forms in {
            "은/는": ("은", "는"),
            "이/가": ("이", "가"),
            "을/를": ("을", "를"),
            "과/와": ("과", "와"),
        }.items():
            suffix = "(?:" + "|".join(forms) + ")"
            text = re.sub(
                re.escape(address) + suffix + r"(?=\s|[,.;:!?]|$)",
                lambda _match, word=address, particle_pair=pair: korean_josa(word, particle_pair),
                text,
            )
    return text.replace("주소+로", "주소를 기준으로").replace("주소 + 로", "주소를 기준으로")


def enforce_verified_school_claims(
    value: str, context: dict[str, object], seed_suffix: str,
) -> str:
    """Keep school claims aligned with the category-specific center-data column."""
    markers = ("수업학교", "수업 학교", "학교 정보", "학교명", "학교 기준", "학교군", "학교 범위")
    schools = [str(item) for item in context["schools"]]
    mentioned_in_value = school_names_in_text(value)
    damaged_in_value = [name for name in SCHOOL_CORRUPTION_MAP if name in value]
    has_unverified_level_school = any(name not in schools for name in mentioned_in_value)
    has_unverified_school_like_token = any(
        name not in schools for name in school_like_names_in_text(value)
    )
    if not any(marker in value for marker in markers) and not any(
        (has_unverified_level_school, has_unverified_school_like_token, bool(damaged_in_value))
    ):
        return value
    level = str(context["level"])
    subject = str(context["subject"])
    locality = str(context["locality"])

    if seed_suffix.startswith("heading"):
        if has_unverified_level_school or has_unverified_school_like_token or damaged_in_value:
            return stable_choice(
                f"{context['seed']}|verified-school-heading|{seed_suffix}",
                [
                    f"{locality} 학교 자료를 확인하는 방법",
                    f"재학 학교와 시험 범위를 상담에서 확인하는 순서",
                    f"확인된 학교 자료를 {subject} 학습에 연결하는 기준",
                ],
            )
        return value

    if seed_suffix == "meta-description" and (
        has_unverified_level_school or has_unverified_school_like_token or damaged_in_value
    ):
        return (
            f"{locality} {level} {subject}학원의 학습 진단, 학교 진도, "
            "과제·오답 관리와 상담 전 센터 확인 정보를 정리했습니다."
        )

    if seed_suffix.startswith("faq-question"):
        if schools:
            choices = [
                f"{locality} {level} {subject} 상담에서 학교별 내신 대비는 어떻게 확인하나요?",
                f"{locality} {level} {subject} 수업은 재학 학교 자료를 어떻게 반영하나요?",
                f"{locality} 학생의 학교 시험 범위는 상담에서 어떻게 확인하나요?",
            ]
        else:
            choices = [
                f"{locality} {level} {subject} 상담에서 재학 학교 정보는 어떻게 확인하나요?",
                f"제공 자료에 학교명이 없으면 {locality} 학생의 시험 대비는 어떻게 정하나요?",
                f"{locality} 학생의 실제 학교와 시험 범위는 언제 확인하나요?",
            ]
        return stable_choice(f"{context['seed']}|verified-school-question|{seed_suffix}", choices)

    def verified_sentence(original: str, index: int) -> str:
        if schools:
            names = ", ".join(schools)
            choices = [
                f"현재 안내에 반영된 {level} {subject} 수업 학교는 {names}입니다.",
                f"센터 자료에서 확인되는 {level} {subject} 관련 학교는 {names}입니다.",
                f"{locality} 안내에는 센터 자료에서 확인한 {names} 학교 정보만 반영했습니다.",
            ]
        else:
            choices = [
                f"센터 자료에는 {level} {subject} 관련 학교명이 별도로 기재되어 있지 않습니다. 상담에서는 학생의 실제 재학 학교와 최신 시험 범위를 확인해야 합니다.",
                f"{locality} 센터 자료에는 {level} {subject} 학교 정보가 따로 기재되어 있지 않습니다. 특정 학교를 가정하지 않고 상담에서 실제 학교와 시험 범위를 확인합니다.",
                f"이 안내에는 확인되지 않은 {level} 학교명을 임의로 넣지 않았습니다. {subject} 상담 때 학생의 재학 학교와 최신 범위표를 함께 확인하는 편이 정확합니다.",
            ]
        scope = "faq" if seed_suffix.startswith("faq-") else "summary" if seed_suffix == "summary" else "article"
        return stable_choice(f"{context['seed']}|verified-school|{scope}", choices)

    sentences = [item for item in re.split(r"(?<=[.!?])\s+", value) if normalize(item)]
    normalized = []
    for index, sentence in enumerate(sentences):
        has_marker = any(marker in sentence for marker in markers)
        mentioned_schools = school_names_in_text(sentence)
        has_unverified_level_school = any(name not in schools for name in mentioned_schools)
        has_unverified_school_like_token = any(
            name not in schools for name in school_like_names_in_text(sentence)
        )
        has_damaged_school = any(
            name in sentence for name in SCHOOL_CORRUPTION_MAP
        )
        is_claim = (
            has_marker or has_unverified_level_school
            or has_unverified_school_like_token or has_damaged_school
        )
        normalized.append(verified_sentence(sentence, index) if is_claim else sentence)
    return " ".join(normalized)


def contains_hangul_token(value: str, token: str) -> bool:
    return bool(re.search(
        rf"(?<![가-힣A-Za-z0-9]){re.escape(token)}(?![가-힣A-Za-z0-9])",
        value,
    ))


def school_names_in_text(value: str) -> list[str]:
    return school_like_names_in_text(value)


def school_like_names_in_text(value: str) -> list[str]:
    # A bare suffix regex also sees ordinary Korean words ending in 고/중/초
    # (광고, 참고, 하고).  Only names present in the verified center source
    # are safe to classify as schools in free-form public copy.
    return list(dict.fromkeys(
        normalize(name) for name in SCHOOL_NAME_RE.findall(value)
        if normalize(name) in VERIFIED_SCHOOL_NAME_SET
    ))


GRADE_PREFIX_BY_LEVEL = {"초등학생": "초", "중학생": "중", "고등학생": "고"}
GRADE_LABEL_BY_PREFIX = {"초": "초등학생", "중": "중학생", "고": "고등학생"}
GRADE_CLAIM_RE = re.compile(
    r"(?<![가-힣A-Za-z0-9])"
    r"(?:(초등학교|초등학생|초등|초)|(중학교|중학생|중등|중)|(고등학교|고등학생|고등|고))"
    r"\s*([1-6])\s*(학년)?"
    r"(?![가-힣A-Za-z0-9])"
)


def verified_grade_tokens(context: dict[str, object]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        f"{prefix}{number}"
        for prefix, number in re.findall(r"([초중고])\s*([1-6])", str(context.get("grades", "")))
    ))


def grade_claim_tokens(value: str) -> list[str]:
    values = []
    for match in GRADE_CLAIM_RE.finditer(value):
        raw_prefix = next(item for item in match.groups()[:3] if item is not None)
        prefix = "초" if raw_prefix.startswith("초") else "중" if raw_prefix.startswith("중") else "고"
        values.append(f"{prefix}{match.group(4)}")
    return values


def enforce_verified_grade_claims(value: str, context: dict[str, object]) -> str:
    """Keep every explicit school-grade claim inside the subject CSV range."""
    allowed = verified_grade_tokens(context)
    category_prefix = GRADE_PREFIX_BY_LEVEL.get(str(context.get("level")), "")

    def replacement_for(prefix: str) -> str | None:
        same_level = [item for item in allowed if item.startswith(prefix)]
        category_level = [item for item in allowed if item.startswith(category_prefix)]
        candidates = same_level or category_level
        if not candidates:
            return None
        return stable_choice(
            f"{context['seed']}|verified-grade|{prefix}",
            list(candidates),
        )

    def replace_numeric(match: re.Match[str]) -> str:
        raw_prefix = next(item for item in match.groups()[:3] if item is not None)
        prefix = "초" if raw_prefix.startswith("초") else "중" if raw_prefix.startswith("중") else "고"
        claim = f"{prefix}{match.group(4)}"
        if claim in allowed:
            return match.group(0)
        selected = replacement_for(prefix)
        if selected is None:
            return GRADE_LABEL_BY_PREFIX.get(category_prefix, str(context.get("level", "학생")))
        selected_number = selected[1:]
        has_school_form = raw_prefix.endswith("학교")
        has_student_form = raw_prefix.endswith("학생")
        has_grade_word = bool(match.group(5))
        if has_school_form:
            return f"{GRADE_LABEL_BY_PREFIX[selected[0]].replace('학생', '학교')} {selected_number}학년"
        if has_student_form:
            return f"{GRADE_LABEL_BY_PREFIX[selected[0]]} {selected_number}학년"
        if raw_prefix in {"초등", "중등", "고등"} or has_grade_word:
            long_prefix = {"초": "초등", "중": "중등", "고": "고등"}[selected[0]]
            return f"{long_prefix} {selected_number}학년"
        return selected

    text = GRADE_CLAIM_RE.sub(replace_numeric, value)

    def replace_band(match: re.Match[str]) -> str:
        band = match.group(1)
        allowed_elementary = {int(item[1:]) for item in allowed if item.startswith("초")}
        band_grades = {1, 2, 3} if band == "저" else {4, 5, 6}
        if allowed_elementary.intersection(band_grades):
            return f"초등 {band}학년"
        selected = replacement_for("초")
        if selected and selected.startswith("초"):
            return f"초등 {selected[1:]}학년"
        return GRADE_LABEL_BY_PREFIX.get(category_prefix, str(context.get("level", "학생")))

    return re.sub(r"초등\s*(저|고)학년", replace_band, text)


def assert_verified_fact_claims(
    value: str, context: dict[str, object], field_name: str,
) -> None:
    """Fail generation if public copy escaped the school/grade fact guards."""
    allowed_schools = {str(item) for item in context.get("schools", [])}
    unverified_schools = sorted({
        *[name for name in school_names_in_text(value) if name not in allowed_schools],
        *[name for name in school_like_names_in_text(value) if name not in allowed_schools],
    })
    damaged_schools = sorted(
        name for name in SCHOOL_CORRUPTION_MAP if name in value
    )
    allowed_grades = set(verified_grade_tokens(context))
    unverified_grades = sorted(set(grade_claim_tokens(value)) - allowed_grades)
    errors = []
    if unverified_schools:
        errors.append(f"schools={unverified_schools}")
    if damaged_schools:
        errors.append(f"damaged_schools={damaged_schools}")
    if unverified_grades:
        errors.append(f"grades={unverified_grades}")
    if errors:
        raise ValueError(
            f"Unverified public facts: {context.get('title')} [{field_name}]: "
            + ", ".join(errors)
        )


def verified_public_copy(
    value: str, context: dict[str, object], seed_suffix: str,
) -> str:
    """Apply and then assert the final public-copy factual boundary."""
    text = enforce_verified_school_claims(value, context, seed_suffix)
    text = enforce_verified_grade_claims(text, context)
    text = normalize(repair_named_josa(text, context))
    assert_verified_fact_claims(text, context, seed_suffix)
    return text


def naturalize_text(value: str, context: dict[str, object], seed_suffix: str) -> str:
    """Remove authoring instructions while keeping the supplied facts intact."""
    text = normalize(value)
    if not text:
        return text
    # The authoring cleanup below intentionally replaces words such as
    # ``원고``.  Hide complete verified school tokens first so names such as
    # 서원고/상원고/해원중 can never become 서안내/상안내/해안내.
    text, protected_schools = protect_verified_school_tokens(text)
    seed = f"{context['seed']}|{seed_suffix}"
    focus = str(context["learning_focus"])
    # Replace every spacing variant of an unverified operational/facility term
    # before the narrower reference-keyword parser runs.  Particle repair is
    # handled by the same helper used for ordinary rotated reference terms.
    unsafe_terms = sorted(
        {match.group(0) for match in UNVERIFIED_ACADEMY_TERM_RE.finditer(text)},
        key=len,
        reverse=True,
    )
    for unsafe_term in unsafe_terms:
        text = text.replace(unsafe_term, focus)
    if unsafe_terms:
        text = replace_reference_term(text, focus, focus)
    for reference_term in context.get("reference_terms", ()):
        text = replace_reference_term(text, str(reference_term), focus)
    text = re.sub(
        re.escape(focus) + r"\s+같은\s+참고\s*키워드는\s+학부모에게\s+어떤\s+의미가\s+있나요\?",
        f"{korean_josa(focus, '은/는')} 학습 상담에서 어떻게 확인하나요?",
        text,
    )
    text = re.sub(
        re.escape(focus) + r"(?:이라는|라는)\s+참고\s*키워드는\s+운영\s+편의와\s+학습\s+환경의\s+한\s+단서가\s+될\s+수\s+있지만,?",
        f"{korean_josa(focus, '은/는')} 학생의 현재 상태를 확인하는 기준이며,",
        text,
    )
    text = re.sub(
        re.escape(focus) + r"처럼\s+운영을\s+떠올리게\s+하는\s+키워드도\s+결국",
        f"{korean_josa(focus, '은/는')} 결국",
        text,
    )
    text = re.sub(r"참고\s*키워드(?:는|은|이|가|을|를|과|와)?\s+", "", text)

    if str(context["subject"]) == "영어":
        focus_explanations = [
            f"{korean_josa(focus, '은/는')} 어휘·문법·독해 가운데 막히는 지점을 확인하고 다음 과제 순서를 정하는 기준입니다.",
            f"{korean_josa(focus, '은/는')} 교과서 문장을 이해하고 다시 써 보는 과정에서 어느 단계가 부족한지 살피는 기준입니다.",
            f"{korean_josa(focus, '은/는')} 단어 암기부터 지문 해석까지 학생의 영어 학습 흐름을 구체화하는 확인 항목입니다.",
        ]
    else:
        focus_explanations = [
            f"{korean_josa(focus, '은/는')} 개념 이해와 조건 해석, 풀이 재현 중 어디에서 막히는지 확인하는 기준입니다.",
            f"{korean_josa(focus, '은/는')} 오답 원인을 나누고 다음 복습 순서를 정할 때 확인하는 수학 학습 기준입니다.",
            f"{korean_josa(focus, '은/는')} 계산 결과보다 풀이 과정에서 빠진 근거를 찾고 보완 계획을 세우는 기준입니다.",
        ]
    text = re.sub(
        re.escape(focus)
        + r"(?:은|는)\s+학원\s+운영이나\s+학습\s+관리에서\s+살펴볼\s+수\s+있는\s+보조\s+단서입니다\.?",
        stable_choice(f"{seed}|focus-explanation", focus_explanations),
        text,
    )
    text = re.sub(
        re.escape(focus) + r"(?:이라는|라는)\s+참고어가\s+어떤\s+영역을\s+가리키든,?",
        f"{korean_josa(focus, '이/가')} 어떤 학습 상태를 가리키는지 살핀 뒤,",
        text,
    )
    text = text.replace(
        "수업 운영 방식과 참여도 관리와 연결해 보면",
        "수업 방식과 학습 참여 흐름을 함께 보면",
    )
    text = text.replace(
        "수업 운영 방식과 참여도 관리를 설명하는 보조 단서로 보고",
        "학생의 참여와 복습 흐름을 확인하는 기준으로 삼고",
    )
    text = re.sub(
        r"영어\s+수학\s+(?:확인\s*항목|관련\s*정보|확인\s*기준)(?:을|를)?\s+참고해",
        "영어 학습 흐름을 함께 살펴",
        text,
    )
    text = text.replace("영어 수학", "영어·수학")
    text = re.sub(
        r"영어·수학\s+확인\s*항목(?:을|를)?\s+참고해",
        "영어·수학 학습 시간을 함께 살펴",
        text,
    )
    text = re.sub(
        re.escape(focus)
        + r"(?:은|는)\s+검색\s+유입을\s+위한\s+단어로만\s+쓰기보다\s+[^.!?]*실제로\s+확인할\s+질문으로\s+바꾸는\s+것이\s+좋습니다\.?",
        f"{korean_josa(focus, '은/는')} 학생의 현재 상태와 다음 복습 순서를 확인하는 학습 기준으로 활용하는 것이 좋습니다.",
        text,
    )

    summary_replacements = [
        f"{context['region']} {context['locality']}에서 {context['level']} {context['subject']}학원을 비교할 때는 {focus}, 학교 진도, 과제·오답 피드백이 실제 수업 계획에 반영되는지 확인해야 합니다.",
        f"{context['locality']} {context['level']} {context['subject']} 상담에서는 {korean_josa(focus, '과/와')} 현재 시험 범위를 함께 확인해야 학생에게 필요한 학습 순서를 구체화할 수 있습니다.",
        f"이 안내는 {context['locality']} 학생의 {focus}, 학교별 진도, 과제 수행 기록을 함께 살펴 수업 선택 기준을 분명히 하도록 구성했습니다.",
    ]
    text = re.sub(
        r"검색\s+결과\s+설명에는[^.!?]*정리할\s+수\s+있습니다\.?",
        stable_choice(f"{seed}|search-summary", summary_replacements),
        text,
    )
    text = re.sub(
        r"[^.!?]*(?:원고|페이지|안내)(?:는|에서는)\s+검색\s+결과에서\s+바로\s+답을\s+찾도록\s+구성했습니다\.?",
        stable_choice(
            f"{seed}|direct-answer",
            [
                f"{context['locality']} 상담에서는 {korean_josa(focus, '과/와')} 최근 시험지의 오답을 함께 확인해 필요한 복습 순서를 정합니다.",
                f"{context['locality']} 학생에게 맞는 수업은 {focus}, 학교 진도, 과제 수행 기록을 함께 볼 때 구체적으로 판단할 수 있습니다.",
                f"상담 전에는 {context['locality']} 학생이 어느 단원에서 막히는지와 오답을 다시 풀 수 있는지를 먼저 확인하면 됩니다.",
            ],
        ),
        text,
    )
    text = re.sub(
        r"이\s+(?:안내|원고|페이지)는\s+([^.!?]+?)을\s+기준으로\s+작성했습니다\.",
        r"상담에서는 \1인지 먼저 확인합니다.",
        text,
    )

    # Remove manuscript-production narration from the public copy.  These
    # patterns are deliberately sentence-shaped so ordinary uses such as a
    # school handout (안내문) are not touched.
    def rewrite_body_narration(match: re.Match[str]) -> str:
        student = normalize(match.group(1))
        criteria = normalize(match.group(2))
        return (
            f"상담에서는 {korean_josa(student, '을/를')} 기준으로 "
            f"{korean_josa(criteria, '을/를')} 함께 확인합니다."
        )

    text = re.sub(
        r"본문은\s+(.+?)(?:을|를)\s+기준으로\s+(.+?)\s+확인\s+포인트를\s+설명합니다\.",
        rewrite_body_narration,
        text,
    )
    text = text.replace(
        "확인 질문을 핵심 안내 설명문에 넣기 좋게 정리했습니다",
        "확인 질문을 상담에서 먼저 살펴봅니다",
    )
    text = re.sub(
        r"핵심\s+안내\s+설명문에\s+넣기\s+좋게\s+정리했습니다",
        "상담에서 필요한 기준을 먼저 살펴봅니다",
        text,
    )
    text = re.sub(
        r"(?:JSON-LD|JSON)\s*(?:구조화\s*데이터)?\s*요약(?:문)?|구조화\s*데이터\s*요약(?:문)?",
        "핵심 학습 요약",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace(
        f"{context['title']} 콘텐츠는",
        f"{context['title']} 안내에서는",
    )
    management_reference = stable_choice(
        f"{seed}|management-reference",
        [
            f"{context['locality']} {context['subject']} 학습 기준",
            f"{context['level']} {context['subject']} 관리 기준",
            f"해당 {context['subject']} 학습 기준",
            f"{context['center']} {context['subject']} 상담 기준",
        ],
    )
    text = re.sub(
        r"(?:이\s+)+(?:영어|수학)\s+관리\s+기준",
        management_reference,
        text,
    )
    text = re.sub(
        r"((?:영어|수학)\s+(?:학습|관리)\s+기준)의\s+([가-힣]+)의",
        r"\1에서 \2의",
        text,
    )

    def keyword_variant(term: str, offset: str) -> str:
        term = normalize(term)
        return stable_choice(
            f"{seed}|keyword|{offset}|{term}",
            [f"‘{term}’ 확인 기준", f"‘{term}’ 관리 방식", f"‘{term}’ 운영 항목"],
        )

    text = re.sub(
        r"(?:원고\s*)?(?:참고\s*)?키워드\s*항목\s*\(\s*([^)]+?)\s*\)",
        lambda match: keyword_variant(match.group(1), str(match.start())),
        text,
    )
    text = re.sub(
        r"(?:원고\s*)?(?:참고\s*)?키워드\s*[‘“\"']([^’”\"']+)[’”\"']\s*(?:항목)?",
        lambda match: keyword_variant(match.group(1), str(match.start())),
        text,
    )
    text = re.sub(
        r"(?:참고\s*)?키워드\s+([가-힣A-Za-z0-9·_-]+)(?:\s+항목)?",
        lambda match: stable_choice(
            f"{seed}|plain-keyword|{match.start()}",
            [f"{match.group(1)} 관련 정보", f"{match.group(1)} 확인 기준", f"{match.group(1)} 운영 방식"],
        ),
        text,
    )
    text = re.sub(
        r"운영\s*키워드로\s*제공된\s*([가-힣A-Za-z0-9·_-]+)",
        lambda match: f"제공 자료의 {match.group(1)} 항목",
        text,
    )
    text = re.sub(r"D열에\s*제공된\s*학교\s*정보", "제공된 수업 학교 정보", text)
    text = re.sub(r"D열의\s*학교\s*정보", "제공된 학교 정보", text)
    text = text.replace("D열", "제공 자료")

    replacements = (
        ("정보성 문서 형태로 정리한 원고입니다", "상담 전에 확인할 기준을 정리한 안내입니다"),
        ("페이지에 맞춰 작성한 후기형 문안입니다", "상담 전에 살필 상황을 정리한 예시입니다"),
        ("페이지에 맞춘 학부모 후기 형식 예시입니다", "학부모 상담에서 살필 상황을 정리한 예시입니다"),
        ("페이지 원고입니다", "학습 안내입니다"),
        ("학부모 후기 형식 예시", "학부모 상담 상황 예시"),
        ("학부모 후기입니다", "학부모 상담 상황입니다"),
        ("학부모 후기", "학부모 상담 상황"),
        ("후기형 문안", "상담 상황"),
        ("후기 예시", "상담 상황"),
        ("검색자가", "학부모가"),
        ("검색자", "학부모"),
        ("이번 원고에서는", "이 안내에서는"),
        ("이번 원고는", "이 안내는"),
        ("이번 원고", "이 안내"),
        ("이 원고에서는", "이 안내에서는"),
        ("이 원고는", "이 안내는"),
        ("원고에서는", "안내에서는"),
        ("원고에서", "안내에서"),
        ("원고의", "안내의"),
        ("원고를", "안내를"),
        ("원고가", "안내가"),
        ("원고입니다", "안내입니다"),
        ("페이지에 맞춘", "이 지역 상황을 반영한"),
        ("페이지에 맞춰", "이 지역 상황에 맞춰"),
        ("이 페이지에서는", "이 안내에서는"),
        ("이 페이지는", "이 안내는"),
        ("페이지에서는", "안내에서는"),
        ("페이지에서", "안내에서"),
        ("페이지를", "안내를"),
        ("페이지가", "안내가"),
        ("페이지입니다", "안내입니다"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    text = text.replace(
        f"{context['title']} 페이지용 메타 설명입니다",
        f"{context['title']} 선택 기준을 안내합니다",
    )
    text = text.replace("원고", "안내").replace("키워드", "확인 항목")
    text = text.replace("참고 확인 항목로", "학습 상담의 보조 기준으로")
    text = text.replace("확인 항목를", "확인 항목을")
    text = text.replace("참고어", "학습 참고 항목")
    text = text.replace(
        "학부모의 질문에 직접 답하는 지역 교육 안내문으로 활용할 수 있습니다",
        "학부모가 수업 기준을 구체적으로 판단할 수 있도록 정리했습니다",
    )
    text = text.replace(
        "지역 교육 안내문으로 활용할 수 있습니다",
        "학부모가 수업 기준을 판단할 수 있도록 정리했습니다",
    )
    text = re.sub(r"‘([^’]+)’\s*(?:확인 기준|관리 방식|운영 항목)\s*(?:체크|점검)\s*기준", r"‘\1’ 점검 기준", text)
    text = re.sub(r"(관련 정보|확인 기준|운영 방식)\s+항목", r"\1", text)
    text = re.sub(r"(확인 기준|관리 방식|운영 항목)\s+관점", r"\1의 관점", text)
    text = re.sub(r"상담 상황\s*(?:형식\s*)?예시", "상담 상황 예시", text)
    text = re.sub(r"안내\s+안내", "학습 안내", text)
    text = text.replace("구조화 데이터 설명문으로 요약하기 좋습니다", "상담 전에 핵심 기준을 확인할 수 있도록 정리했습니다")
    text = text.replace("구조화 데이터", "핵심 안내")
    text = text.replace("설명문으로 요약하기 좋습니다", "상담 전에 핵심을 확인할 수 있도록 정리했습니다")
    text = text.replace("학원주소", "학원 주소").replace("수업학교", "수업 학교")
    text = text.replace("제공 학교 정보", "확인된 학교 정보")
    text = text.replace("제공된 학교 범위", "확인된 학교 자료 범위")
    text = text.replace("실제 확인할 운영·학습 항목", "실제 확인할 학습·상담 항목")
    text = text.replace("정보성 페이지로서 가치가 있습니다", "학생의 현재 상태와 관리 방식을 구체적으로 설명할 수 있어야 합니다")
    text = text.replace("해당 확인 항목보다 수학 풀이가", "표현보다 수학 풀이가")
    text = text.replace("초등학생 영어 학교 정보", "초등 영어 관련 학교 정보")
    text = text.replace("초등학생 수학 학교 정보", "초등 수학 관련 학교 정보")
    text = re.sub(r"해당\s+초등학생\s+(영어|수학)\s+상담\s+선택\s*시", r"초등 \1 수업을 선택할 때", text)
    text = re.sub(r"해당\s+초등학생\s+(영어|수학)\s+상담", r"초등 \1 상담", text)
    text = re.sub(r"이\s+(영어|수학)\s+관리\s+기준\s+상담\s+전에는", r"\1 학습 상담 전에는", text)
    text = re.sub(
        r"검색\s+확인\s*항목이\s+말해\s+주는\s+추가\s+상담\s+포인트",
        f"{context['locality']} 상담에서 확인할 {context['subject']} 학습 포인트",
        text,
    )
    text = text.replace("등록 주소", "센터 주소")
    text = text.replace("등 제공 학교 진도", "등 확인된 학교 자료")
    text = text.replace("안내하는 안내입니다", "설명하는 자료입니다")
    text = text.replace("참고할 수 있는 정보형 안내입니다", "확인할 수 있도록 정리했습니다")
    text = text.replace("페이지는", "안내에서는").replace("페이지의", "안내의").replace("페이지를", "안내를")
    text = re.sub(
        r"([가-힣A-Za-z0-9·_-]+)\s+관점\s+학습\s+관리",
        lambda match: f"{korean_josa(match.group(1), '으로/로')} 확인할 학습 관리",
        text,
    )
    text = re.sub(
        r"([가-힣A-Za-z0-9·_-]+)(?:을|를)\s+검색한\s+(?:이유|목적)",
        lambda match: f"{match.group(1)} 정보를 알아본 이유",
        text,
    )
    text = re.sub(
        r"([가-힣A-Za-z0-9·_-]+)(?:을|를)\s+검색한",
        lambda match: f"{match.group(1)} 정보를 알아보는",
        text,
    )
    text = text.replace("학원하원", "등·하원")
    text = text.replace("학원온라인수업라는", "학원온라인수업이라는")
    text = text.replace("학원온라인수업이란는", "학원온라인수업이라는")
    text = re.sub(
        r"(?:확인 항목|관련 정보|확인 기준|운영 방식)\s*자체보다\s*"
        r"(?:그\s*)?(?:확인 항목|관련 정보|확인 기준|운영 방식)(?:이|가)?\s*"
        r"학생의 수업 경험으로 어떻게 바뀌는지 확인해야 합니다\.?",
        "표현보다 진단 결과가 실제 학습 계획과 피드백으로 이어지는지 확인해야 합니다.",
        text,
    )
    text = re.sub(
        r"자체보다\s*(?:관련 정보|확인 기준|운영 방식)\s*(?:그\s*)?확인 항목(?:이|가)?\s*"
        r"학생의 수업 경험으로 어떻게 바뀌는지 확인해야 합니다\.?",
        "표현보다 진단 결과가 실제 학습 계획과 피드백으로 이어지는지 확인해야 합니다.",
        text,
    )
    text = text.replace("실제 페이지에 사용할 때", "실제 상담 기준으로 살필 때")
    text = text.replace("학습 기준 학습 방식", "학습 방식")
    text = re.sub(r"상담\s+상담", "상담", text)
    text = re.sub(r"항목(?=중심|관련|기준|관점)", "항목 ", text)
    text = re.sub(
        r"제공 자료의\s+([가-힣A-Za-z0-9·_-]+)(?:은|는)\s+항목",
        r"제공 자료에서 확인되는 \1 항목은",
        text,
    )
    text = re.sub(r"관리 방식을\s+점검 기준으로", "관리 방식을 점검할 때 기준으로", text)
    text = text.replace("학원알림톡가", "학원알림톡이")
    text = text.replace("관리 방식을 점검할 때 기준으로 두면", "관리 방식을 점검 기준으로 삼으면")
    text = text.replace("관리 방식과 연결된 관리 방식", "관리 방식과 연결된 학습 기록")
    text = text.replace("확인 기준관점의", "확인 기준에 따른")
    text = text.replace("확인 기준기반", "확인 기준에 기반한")
    text = text.replace("라는 질문을 궁금해한다면", "라는 질문에 대한 답이 궁금하다면")
    text = text.replace("라는 질문을 걱정하는 가정이라면", "라는 질문에 대한 답이 필요한 가정이라면")
    text = re.sub(r"(관리 방식|확인 기준)(?=중심|관련|기록|기반|관점)", r"\1 ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(
        r"핵심 안내에는 (.+?)을 연결해 정보성 페이지로 표시하기 좋습니다\.?",
        r"이 안내에는 \1을 함께 정리했습니다.",
        text,
    )
    text = text.replace(
        "정보성 페이지로 표시하기 좋습니다",
        "상담 전에 핵심을 확인할 수 있도록 정리했습니다",
    )
    text = restore_verified_school_tokens(text, protected_schools)
    return verified_public_copy(text, context, seed_suffix)


def select_student_situation(
    intro: str, body_sections: list[tuple[str, list[str]]], context: dict[str, object],
) -> str:
    source = " ".join([intro] + [paragraph for _, paragraphs in body_sections for paragraph in paragraphs])
    sentences = [normalize(item) for item in re.split(r"(?<=[.!?])\s+", source) if normalize(item)]
    signals = (
        "학생", "초1", "초2", "초3", "초4", "초5", "초6",
        "중1", "중2", "중3", "고1", "고2", "고3", "예비",
        "오답", "시험", "단원", "문법", "독해", "서술형", "연산", "문장제", "파닉스",
    )
    candidates = [
        sentence for sentence in sentences
        if 45 <= len(sentence) <= 260 and sum(signal in sentence for signal in signals) >= 2
    ]
    if not candidates:
        candidates = [sentence for sentence in sentences if 35 <= len(sentence) <= 260]
    if not candidates:
        return ""
    # Prefer a concrete sentence, then select deterministically among the best few.
    ranked = sorted(candidates, key=lambda item: (-sum(signal in item for signal in signals), len(item)))[:8]
    return naturalize_text(
        stable_choice(f"{context['seed']}|student-situation", ranked),
        context,
        "student-situation",
    )


def factual_context_paragraphs(
    context: dict[str, object], situation: str,
) -> list[str]:
    locality = str(context["locality"])
    center = str(context["center"])
    address = str(context["address"])
    subject = str(context["subject"])
    grades = str(context["grades"])
    seed = str(context["seed"])

    center_variants = [
        f"{locality}에서 이용 가능한 센터로 확인되는 곳은 {center}입니다. 센터 주소는 {address}입니다.",
        f"센터 자료를 기준으로 {locality} 상담과 연결된 곳은 {center}이며, 실제 방문 주소는 {address}입니다.",
        f"{locality} 학습 상담에 연결된 센터 정보는 {center}입니다. 방문 위치는 {address}로 안내되어 있습니다.",
    ]
    center_fact = stable_choice(f"{seed}|center-fact", center_variants)
    if address and locality not in address:
        center_fact += " 지역 안내명과 실제 센터 주소가 다를 수 있으므로 방문 전에 위치를 함께 확인하는 것이 좋습니다."

    facts = [center_fact]
    if grades:
        facts.append(stable_choice(
            f"{seed}|grade-fact",
            [
                f"센터 자료에 기재된 {subject} 전체 수업 가능 학년은 {grades}입니다. 학생의 현재 학년과 필요한 보강 범위는 상담에서 구체적으로 확인할 수 있습니다.",
                f"센터 전체 학년 정보는 자료상 {grades}로 확인됩니다. 같은 학년이라도 현재 단원과 오답 유형을 확인한 뒤 학습 순서를 정하는 것이 필요합니다.",
                f"{center}의 센터 자료에는 {subject} 전체 가능 학년이 {grades}로 표시되어 있습니다. 상담 전 현재 교재와 최근 학습 자료를 준비하면 출발점을 더 분명히 정할 수 있습니다.",
            ],
        ))
    if situation:
        facts.append(stable_choice(
            f"{seed}|situation-lead",
            [
                f"학생 상황을 구체화할 때 먼저 살필 예시는 다음과 같습니다. {situation}",
                f"이 지역 상담에서 출발점으로 삼을 학생 상황은 다음과 같습니다. {situation}",
                f"수업 순서를 정하기 전에 확인할 학습 상황 예시는 다음과 같습니다. {situation}",
            ],
        ))
    return [normalize(repair_named_josa(value, context)) for value in facts if normalize(value)]


def diversify_title_references(
    intro: str, body_sections: list[tuple[str, list[str]]], context: dict[str, object], keep: int,
) -> tuple[str, list[tuple[str, list[str]]]]:
    title = str(context["title"])
    replacements = [
        f"{context['locality']} {context['subject']} 학습",
        f"해당 {context['level']} {context['subject']} 상담",
        f"{context['center']} {context['subject']} 학습 기준",
        f"{context['level']} {context['subject']} 학습 기준",
        f"{context['region']} {context['subject']} 학습 상담",
    ]
    count = 0

    def vary(value: str, label: str) -> str:
        nonlocal count

        def replacement(_match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            if count <= keep:
                return title
            return stable_choice(f"{context['seed']}|title-ref|{label}|{count}", replacements)

        return re.sub(re.escape(title), replacement, value)

    varied_intro = vary(intro, "intro")
    varied_sections = []
    for section_index, (heading, paragraphs) in enumerate(body_sections):
        varied_sections.append((
            vary(heading, f"heading-{section_index}"),
            [vary(paragraph, f"paragraph-{section_index}-{index}") for index, paragraph in enumerate(paragraphs)],
        ))
    return varied_intro, varied_sections


def final_polish_text(value: str) -> str:
    """Remove awkward joins that can appear after deterministic title substitution."""
    text = normalize(value)
    while "상담 상담" in text:
        text = text.replace("상담 상담", "상담")
    text = re.sub(r"([가-힣]+)\s+기준\s+학습\s+방식", r"\1 방식", text)
    text = re.sub(r"([가-힣]+)\s+기준\s+학습\s+관리", r"\1 관리", text)
    text = text.replace("기준 기준", "기준")
    text = text.replace("안내하는 정보성 안내입니다", "확인할 수 있도록 정리했습니다")
    text = text.replace("정보성 안내입니다", "학습 안내입니다")
    text = text.replace("구조화하기 좋게 요약했습니다", "확인할 수 있도록 정리했습니다")
    text = text.replace("제공된 참고 주제인", "상담에서 살필 항목인")
    text = text.replace("제공된 참고 주제", "상담에서 살필 항목")
    text = text.replace("제공 확인 항목에", "센터 안내에")
    text = text.replace("학습 또는 상담 포인트", "학습 상담 포인트")
    text = text.replace("확인할 내용을 확인할 수 있도록", "핵심을 확인할 수 있도록")
    text = text.replace("제공 주소", "센터 주소")
    text = text.replace("확인 항목가", "확인 항목이")
    text = text.replace("확인 기준 그 확인 항목이", "확인 기준이")
    text = text.replace("관련 정보 그 확인 항목이", "관련 정보가")
    text = re.sub(r"((?:체계적|집중)?학습관리)\s*은", r"\1는", text)
    text = re.sub(r"((?:체계적|집중)?학습관리)\s*을", r"\1를", text)
    text = text.replace("상담 상황로", "상담 상황으로")
    text = text.replace("영어·수학 확인 항목을 참고해", "영어·수학 학습 시간을 함께 살펴")
    text = text.replace("이 영어 관리 기준 상담 전", "영어 학습 상담 전")
    text = text.replace("이 수학 관리 기준 상담 전", "수학 학습 상담 전")
    text = re.sub(r"(?:이\s+){2,}(영어|수학)\s+관리\s+기준", r"이 \1 관리 기준", text)
    text = re.sub(r"((?:영어|수학)\s+(?:학습|관리)\s+기준)의\s+([가-힣]+)의", r"\1에서 \2의", text)
    text = text.replace("검색 확인 항목이 말해 주는 추가 상담 포인트", "학습 기록으로 살펴보는 추가 상담 포인트")
    text = text.replace("함께 검색한 경우에도", "함께 살펴볼 때도")
    text = text.replace("찾는 사용자를 위해", "찾는 학부모가 확인할 수 있도록")
    text = re.sub(r"(초등학생|중학생|고등학생)\s+학생", r"\1", text)
    text = text.replace("경우인 경우에는", "경우에는")
    text = text.replace("경우인 경우", "경우")
    text = text.replace("초등학생으로 넘어가며", "초등 고학년으로 올라가며")
    text = text.replace("재확인 확인 항목", "재확인 항목")
    text = text.replace("재확인 확인", "재확인")
    text = re.sub(r"학습(?:\s+학습)+", "학습", text)
    text = re.sub(r"(점검|보완)\s+확인\s+(질문|포인트|항목|기준)", r"\1 \2", text)
    text = text.replace("학습 기준 선택 기준이", "학습 기준이")
    text = text.replace("주간 학습 복습", "주간 복습")
    text = text.replace("상담 수업", "수업")
    text = text.replace("이 수학 관리 기준 수업 후", "수학 수업 후")
    text = text.replace("제공된 학교", "센터 안내에 기재된 학교")
    text = text.replace("정보성 페이지로 구성했습니다", "학습 기준을 구체적으로 정리했습니다")
    text = text.replace(
        "확인 질문을 핵심 안내 설명문에 넣기 좋게 정리했습니다",
        "확인 질문을 상담에서 먼저 살펴봅니다",
    )
    text = re.sub(
        r"핵심\s+안내\s+설명문에\s+넣기\s+좋게\s+정리했습니다",
        "상담에서 필요한 기준을 먼저 살펴봅니다",
        text,
    )
    text = re.sub(r"([가-힣A-Za-z0-9· ]+학원)\s+요약문은", r"\1 안내에서는", text)
    text = text.replace("요약문은", "안내에서는")
    text = text.replace(" 페이지라면 그 표현이", " 안내를 볼 때는 해당 내용이")
    text = re.sub(
        r"적용하면\s+(.+?)이라는\s+검색어도\s+실제로는\s+빈틈을\s+찾고\s+복습\s+순서를\s+잡는\s+질문으로\s+바꿀\s+수\s+있습니다\.",
        r"적용하면 \1을 살필 때 학습 빈틈과 복습 순서를 더 구체적으로 정할 수 있습니다.",
        text,
    )
    text = re.sub(
        r"이 안내는 (초등\s+\d+학년) 중 (.+?학생)으로, (.+?흐름)을 통해 (.+?학생)을 기준으로 (초등\s+\d+학년 영어 진단.+)$",
        r"이 안내는 \1 가운데 \2을 중심으로 살펴봅니다. \3이 이어진다면 \4인지도 함께 확인하며, \5",
        text,
    )
    for wrong, correct in (
        ("문장제을", "문장제를"),
        ("자료 해석 문제을", "자료 해석 문제를"),
        ("확률의 경우 나누기을", "확률의 경우 나누기를"),
        ("정리을", "정리를"),
        ("유리수와 순환소수을", "유리수와 순환소수를"),
        ("와와학습코칭학원로", "와와학습코칭학원으로"),
        ("와와학습코칭학원와", "와와학습코칭학원과"),
        ("루틴를", "루틴을"),
        ("복습와", "복습과"),
        ("예습를", "예습을"),
        ("확인 항목를", "확인 항목을"),
        ("참고 확인 항목로", "학습 상담의 보조 기준으로"),
    ):
        text = text.replace(wrong, correct)
    text = re.sub(r"상담 상황\s+(\d+)\.\s*상담 상황\s+\1\s*[.｜:]\s*", r"상담 상황 \1. ", text)
    text = re.sub(r"항목(?=중심|관련|기준|관점)", "항목 ", text)
    common_nouns = (
        "학습력검사", "체계적 학습 관리", "집중 학습 관리", "학습 관리",
        "성향검사", "습관검사", "유형검사", "동기검사", "체크리스트",
        "동기부여", "포트폴리오", "우선순위", "완성도", "성취도", "진척도",
        "문장제 해석", "자료 해석", "확인 항목", "보고서", "설명회", "리포트",
        "플래너", "매니저", "클리닉", "세미나", "단원", "관리", "습관",
        "해석", "보완", "유형", "후기", "캠프", "검사", "평가", "대비",
        "준비", "설계", "사례", "숙제", "결과", "상담", "몰입도", "자립도",
        "이해", "강의", "심화", "태도검사", "격려", "일지", "진도", "성과",
        "통계", "수업", "노트", "과제", "위치", "주차", "정보", "정예",
        "강사", "암기", "성적", "태도", "지도", "목표", "동기", "개념", "기록", "표",
    )
    for noun in sorted(common_nouns, key=len, reverse=True):
        for pair, forms in {
            "은/는": ("은", "는"),
            "을/를": ("을", "를"),
            "과/와": ("과", "와"),
        }.items():
            text = re.sub(
                re.escape(noun) + "(?:" + "|".join(forms) + r")(?=\s|[,.;:!?]|$)",
                lambda _match, word=noun, particle_pair=pair: korean_josa(word, particle_pair),
                text,
            )
    text = text.replace("학습 시간 표", "학습 시간표").replace("학원 시간 표", "학원 시간표")
    for wrong, correct in (("표을", "표를"), ("표은", "표는"), ("반를", "반을"), ("자을", "자를")):
        text = text.replace(wrong, correct)
    return normalize(text)


def dedupe_text_sentences(value: str) -> str:
    seen: set[str] = set()
    kept: list[str] = []
    for sentence in [item for item in re.split(r"(?<=[.!?])\s+", normalize(value)) if normalize(item)]:
        key = normalize(sentence)
        if key in seen:
            continue
        seen.add(key)
        kept.append(key)
    return normalize(" ".join(kept))


def dedupe_article_sentences(
    intro: str, sections: list[tuple[str, list[str]]],
) -> tuple[str, list[tuple[str, list[str]]]]:
    """Remove exact repeats within each section while preserving section context."""

    def dedupe(value: str, seen: set[str]) -> str:
        kept = []
        for sentence in [item for item in re.split(r"(?<=[.!?])\s+", value) if normalize(item)]:
            key = normalize(sentence)
            if key in seen:
                continue
            seen.add(key)
            kept.append(sentence)
        clean = normalize(" ".join(kept))
        orphan_leads = {
            "학생 상황을 구체화할 때 먼저 살필 예시는 다음과 같습니다.",
            "이 지역 상담에서 출발점으로 삼을 학생 상황은 다음과 같습니다.",
            "수업 순서를 정하기 전에 확인할 학습 상황 예시는 다음과 같습니다.",
        }
        return "" if clean in orphan_leads else clean

    clean_intro = dedupe(intro, set())
    clean_sections = []
    for heading, paragraphs in sections:
        section_seen: set[str] = set()
        clean_paragraphs = [
            clean for paragraph in paragraphs if (clean := dedupe(paragraph, section_seen))
        ]
        clean_sections.append((heading, clean_paragraphs))
    return clean_intro, clean_sections


def individualize_body(
    intro: str, body_sections: list[tuple[str, list[str]]], context: dict[str, object],
) -> tuple[str, list[tuple[str, list[str]]]]:
    situation = select_student_situation(intro, body_sections, context)
    natural_intro = naturalize_text(intro, context, "intro")
    natural_sections = [
        (
            naturalize_text(heading, context, f"heading-{section_index}"),
            [
                naturalize_text(paragraph, context, f"paragraph-{section_index}-{paragraph_index}")
                for paragraph_index, paragraph in enumerate(paragraphs)
            ],
        )
        for section_index, (heading, paragraphs) in enumerate(body_sections)
    ]

    category = str(context["category"])
    intensive_categories = {
        "초등학생수학학원", "초등학생영어학원",
        "중학생수학학원", "중학생영어학원",
        "고등학생수학학원", "고등학생영어학원",
    }
    if category in intensive_categories and len(natural_sections) in {5, 6, 7}:
        # Keep the opening/closing intent while rotating the meaningful middle
        # sections from each locality's actual headings and facts.
        middle = list(range(1, len(natural_sections) - 1))
        middle.sort(key=lambda index: hashlib.sha256(
            f"{context['seed']}|section-order|{natural_sections[index][0]}".encode("utf-8")
        ).hexdigest())
        natural_sections = [
            natural_sections[index]
            for index in [0, *middle, len(natural_sections) - 1]
        ]

    fact_limit = {
        "초등학생수학학원": 4,
        "초등학생영어학원": 3,
        "중학생수학학원": 4,
        "중학생영어학원": 3,
        "고등학생수학학원": 3,
        "고등학생영어학원": 3,
    }.get(category, 1)
    facts = factual_context_paragraphs(context, situation)[:fact_limit]
    if natural_sections:
        slot_order = list(range(len(natural_sections)))
        slot_order.sort(key=lambda index: hashlib.sha256(
            f"{context['seed']}|fact-slot|{index}".encode("utf-8")
        ).hexdigest())
        for fact_index, fact in enumerate(facts):
            slot = slot_order[fact_index]
            heading, paragraphs = natural_sections[slot]
            natural_sections[slot] = (heading, [fact, *paragraphs])

    keep = 3 if category in {"초등학생수학학원", "중학생수학학원"} else 4
    varied_intro, varied_sections = diversify_title_references(
        natural_intro, natural_sections, context, keep
    )
    varied_intro = dedupe_text_sentences(
        f"{varied_intro} {article_decision_sentence(context)}"
    )
    polished = (
        final_polish_text(varied_intro),
        [
            (final_polish_text(heading), [final_polish_text(paragraph) for paragraph in paragraphs])
            for heading, paragraphs in varied_sections
        ],
    )
    return dedupe_article_sentences(*polished)


def article_decision_sentence(context: dict[str, object]) -> str:
    """Add one useful, high-cardinality decision sentence to each article."""
    subject = str(context["subject"])
    level = str(context["level"])
    focus = str(context["learning_focus"])
    seed = f"{context['seed']}|article-decision"
    if subject == "수학":
        evidence = [
            "최근 오답의 풀이 흔적", "조건 표시가 남은 문제", "서술형 답안의 중간 과정",
            "단원별 재풀이 결과", "계산 실수 기록", "문장제의 조건 해석",
            "과제에서 멈춘 문항", "시험 범위별 정답률", "개념을 말로 설명한 기록",
            "풀이 시간을 나눈 기록", "교재 예제의 재현 여부", "검산 뒤 수정한 과정",
        ]
        decisions = [
            "개념 복습을 먼저 할지", "조건 해석을 다시 연습할지", "오답 재풀이 간격을 줄일지",
            "서술형 근거를 보완할지", "계산 검산 순서를 고정할지", "문제 수보다 재현을 우선할지",
            "현재 단원에 더 머물지", "학교 범위 복습을 앞당길지", "과제 분량을 나누어 볼지",
            "풀이 시간을 다시 배분할지", "질문 목록을 먼저 만들지", "다음 단원 진입을 늦출지",
        ]
    else:
        evidence = [
            "교과서 지문의 근거 표시", "틀린 문장의 재작성 기록", "단어 복습 뒤 회상 결과",
            "문법 적용 문항의 오답", "서술형 답안의 표현 근거", "독해 중 멈춘 문장",
            "과제에서 반복된 오류", "시험 범위별 어휘 기록", "문장을 소리 내어 읽은 기록",
            "지문 풀이 시간 기록", "교재 문장의 재구성 결과", "오답 문장의 수정 과정",
        ]
        decisions = [
            "어휘 복습을 먼저 할지", "문법 적용을 다시 연습할지", "오답 문장 재작성을 늘릴지",
            "독해 근거 표시를 보완할지", "읽기와 쓰기 비중을 바꿀지", "문제 수보다 문장 이해를 우선할지",
            "현재 지문에 더 머물지", "학교 범위 복습을 앞당길지", "과제 분량을 나누어 볼지",
            "풀이 시간을 다시 배분할지", "질문 문장을 먼저 만들지", "다음 문법 단원 진입을 늦출지",
        ]
    outcomes = [
        "이번 주 계획에 반영합니다", "상담의 첫 질문으로 정합니다", "다음 수업의 확인 기준으로 삼습니다",
        "가정 복습 순서와 연결합니다", "학생이 직접 설명할 목표로 바꿉니다", "과제 점검표에 한 가지씩 기록합니다",
        "시험 전 우선순위로 구체화합니다", "다음 상담 때 다시 확인할 항목으로 남깁니다",
        "수업 뒤 재현 여부로 점검합니다", "일주일 뒤 같은 자료로 다시 비교합니다",
    ]
    evidence_value = stable_choice(f"{seed}|evidence", evidence)
    decision_value = stable_choice(f"{seed}|decision", decisions)
    outcome_value = stable_choice(f"{seed}|outcome", outcomes)
    variants = [
        f"{level} {subject} 상담에서는 {korean_josa(evidence_value, '을/를')} 보고 {decision_value} 판단한 뒤, 그 결과를 {outcome_value}.",
        f"학생의 {focus} 상태는 {korean_josa(evidence_value, '으로/로')} 확인하고, {decision_value} 정해 {outcome_value}.",
        f"수업 선택 전에는 {korean_josa(evidence_value, '과/와')} {korean_josa(focus, '을/를')} 함께 비교해 {decision_value} 정하고 {outcome_value}.",
        f"{korean_josa(evidence_value, '이/가')} 보여 주는 학습 상태를 바탕으로 {decision_value} 결정하며, 확인 결과는 {outcome_value}.",
        f"학부모와 학생은 {korean_josa(evidence_value, '을/를')} 함께 살펴 {decision_value} 합의하고, 이를 {outcome_value}.",
        f"진단 결과는 {evidence_value}에서 확인하며, {decision_value} 정한 내용은 {outcome_value}.",
    ]
    return final_polish_text(stable_choice(f"{seed}|syntax", variants))


def case_detail_sentence(context: dict[str, object], index: int) -> str:
    """Return a hypothetical, page-specific consultation detail.

    The sentence describes what could be checked; it never claims that a
    particular student attended, improved, or received an unverified service.
    """
    locality = str(context["locality"])
    level = str(context["level"])
    subject = str(context["subject"])
    focus = str(context["learning_focus"])
    seed = f"{context['seed']}|case-detail|{index}"
    if subject == "수학":
        evidence = [
            "최근 오답", "단원별 정답률", "풀이 과정", "서술형 답안", "계산 기록",
            "학교 범위표", "현재 교재", "재풀이 결과", "과제 수행 기록", "풀이 시간 기록",
        ]
        next_steps = [
            "개념 복습", "오답 재풀이", "문장제 보완", "서술형 연습", "검산 습관",
            "학교 시험 준비", "주간 과제 조정", "선행 속도 조정", "풀이 순서 정리", "시간 배분 연습",
        ]
    else:
        evidence = [
            "최근 오답", "단어 기록", "교과서 지문", "문법 적용 문항", "독해 근거 표시",
            "학교 범위표", "서술형 답안", "현재 교재", "문장 재작성", "과제 수행 기록",
        ]
        next_steps = [
            "어휘 복습", "문법 보완", "독해 근거 확인", "서술형 연습", "문장 재작성",
            "학교 시험 준비", "주간 과제 조정", "읽기 속도 조정", "쓰기 순서 정리", "시간 배분 연습",
        ]
    evidence_value = stable_choice(f"{seed}|evidence", evidence)
    next_value = stable_choice(f"{seed}|next", next_steps)
    variants = [
        f"{locality} 상담에서는 {korean_josa(focus, '과/와')} {korean_josa(evidence_value, '을/를')} 함께 살핀 뒤 {korean_josa(next_value, '을/를')} 우선순위로 정하는 상황을 생각할 수 있습니다.",
        f"이 경우에는 {korean_josa(evidence_value, '을/를')} 기준으로 {korean_josa(focus, '을/를')} 확인하고, 다음 단계로 {korean_josa(next_value, '을/를')} 계획할 수 있습니다.",
        f"{locality} {level} {subject} 상담이라면 {evidence_value}에서 {korean_josa(focus, '이/가')} 드러나는지 살핀 뒤 {korean_josa(next_value, '을/를')} 연결해 볼 수 있습니다.",
        f"학부모는 {korean_josa(evidence_value, '과/와')} {korean_josa(focus, '을/를')} 함께 준비해 {korean_josa(next_value, '이/가')} 필요한 이유부터 질문할 수 있습니다.",
        f"학생의 출발점은 {evidence_value}에서 확인하고, {focus}에 따라 {korean_josa(next_value, '을/를')} 조정하는 상황으로 설명할 수 있습니다.",
        f"{locality} 학생이라면 {korean_josa(evidence_value, '과/와')} {korean_josa(focus, '을/를')} 비교해 {korean_josa(next_value, '을/를')} 먼저 적용할지 상담에서 정할 수 있습니다.",
        f"이 상담 상황에서는 {korean_josa(focus, '을/를')} 단독으로 판단하지 않고 {korean_josa(evidence_value, '과/와')} 함께 보며 {next_value}의 순서를 정합니다.",
        f"{level} {subject} 학습에서는 {korean_josa(evidence_value, '과/와')} {korean_josa(focus, '이/가')} 같은 원인을 가리키는지 확인한 뒤 {korean_josa(next_value, '을/를')} 정할 수 있습니다.",
    ]
    return final_polish_text(stable_choice(f"{seed}|syntax", variants))


def naturalize_cases(cases: list[str], context: dict[str, object]) -> list[str]:
    natural_cases = []
    for index, case in enumerate(cases, 1):
        value = final_polish_text(naturalize_text(case, context, f"case-{index}"))
        value = value.replace("학습 관리 후기", "학습 관리 변화").replace("학부모 후기", "학부모 상담 상황")
        value = value.replace("후기", "상담 상황")
        value = value.replace("“", "").replace("”", "").replace('"', "")
        sentences = [normalize(item) for item in re.split(r"(?<=[.!?])\s+", value) if normalize(item)]
        while sentences and (
            (sentences[0].startswith("아래는 ") and "예시입니다" in sentences[0])
            or ("정리한 예시입니다" in sentences[0] and "상담" in sentences[0])
            or ("실제 특정 학생의 결과를 단정하지 않고" in sentences[0] and "상담 상황" in sentences[0])
            or ("설정의 문장입니다" in sentences[0])
        ):
            sentences.pop(0)
        value = " ".join(sentences) or value
        value = re.sub(r"^(?:상담 상황\s*)+\d+\s*(?:[.｜:·-]\s*)+", "", value)
        value = re.sub(
            r"^학부모\s+상담\s+상황\s+예시(?:\s*\d+)?\s*(?:[.｜:·-]\s*)+",
            "",
            value,
        )
        value = re.sub(
            rf"^{re.escape(str(context['locality']))}\s+학부모\s+상담\s+상황\s*(?:[.｜:·-]\s*)+",
            "",
            value,
        )
        value = re.sub(r"^또\s+다른\s+상담\s+상황\s*(?:[.｜:·-]\s*)+", "", value)
        value = re.sub(r"^[^.!?]*설정의\s+문장입니다\.\s*", "", value)
        value = re.sub(
            rf"(?<=[.!?])\s+{re.escape(str(context['locality']))}\s*$",
            "",
            value,
        )
        detail = case_detail_sentence(context, index)
        if detail and detail not in value:
            value = dedupe_text_sentences(f"{value} {detail}")
        natural_cases.append(f"상담 상황 {index}. {dedupe_text_sentences(value)}")
    return natural_cases


def diversify_faq_question(
    question: str, context: dict[str, object], index: int,
) -> str:
    """Paraphrase a question inside its existing semantic intent.

    Answers are deliberately left untouched.  Intent detection therefore uses
    only explicit words already present in the question and selects a local,
    equivalent formulation rather than inventing a new topic.
    """
    value = final_polish_text(question)
    locality = str(context["locality"])
    level = str(context["level"])
    subject = str(context["subject"])
    focus = str(context["learning_focus"])
    seed = f"{context['seed']}|faq-paraphrase|{index}"
    schools = [str(item) for item in context.get("schools", [])]

    def choose(intent: str, variants: list[str]) -> str:
        return stable_choice(f"{seed}|{intent}", variants)

    if any(marker in value for marker in (
        "학교 자료", "학교별", "학교 일정", "재학 학교", "학교 진도",
        "학교 시험 범위", "학교 시험 대비",
    )):
        if schools:
            variants = [
                f"{locality} {level} {subject} 상담에서는 학교 자료를 어떻게 활용하나요?",
                f"{locality} 학생의 재학 학교 진도는 수업 계획에 어떻게 반영하나요?",
                f"{locality} {subject} 수업에서 학교별 시험 범위는 어떻게 확인하나요?",
                f"학교 자료를 준비하면 {locality} {subject} 상담에 어떤 도움이 되나요?",
                f"{locality} {level} {subject}학원 상담 전 학교 자료도 챙겨야 하나요?",
                f"확인된 학교 정보는 {locality} {subject} 학습 계획에 어떻게 쓰이나요?",
                f"{locality} 학생의 학교 일정과 {subject} 진도는 함께 확인하나요?",
                f"학교마다 다른 진도는 {locality} {subject} 상담에서 어떻게 나누어 보나요?",
            ]
        else:
            variants = [
                f"센터 자료에 학교명이 없으면 {locality} 학생의 시험 범위는 어떻게 확인하나요?",
                f"{locality} {subject} 상담에서는 실제 재학 학교를 언제 확인하나요?",
                f"학교 정보가 없는 경우 {locality} 학생의 내신 계획은 어떻게 정하나요?",
                f"{locality} {level} {subject} 상담 전 학교 범위표를 준비해야 하나요?",
                f"확인된 학교명이 없을 때 {locality} {subject} 수업 계획은 무엇을 기준으로 잡나요?",
                f"{locality} 학생의 학교 진도는 첫 상담에서 어떻게 확인하나요?",
            ]
        return choose("school", variants)

    if "어떤" in value and "학생" in value:
        return choose("student-fit", [
            f"{locality} {level} {subject}학원은 어떤 학습 어려움이 있을 때 살펴보면 좋나요?",
            f"어떤 {level} 학생이 {locality} {subject} 상담을 먼저 받아보면 좋을까요?",
            f"{locality}에서 {subject} 학습 점검이 먼저 필요한 학생은 어떤 경우인가요?",
            f"{locality} {level} {subject} 수업이 필요한지 어떤 기준으로 판단하나요?",
            f"어떤 학습 상황이라면 {locality} {subject}학원을 검토할 만한가요?",
            f"{locality} 학생이 {subject} 공부에서 보이는 어떤 신호를 먼저 살펴야 하나요?",
            f"{locality} {level} 학생에게 {subject} 관리가 필요한 시점은 언제인가요?",
            f"{subject} 학습 흐름이 어떤 상태일 때 {locality} 상담이 도움이 되나요?",
        ])

    if "언제" in value or "시작" in value:
        return choose("timing", [
            f"{locality} {level} {subject} 시험 대비는 언제부터 준비하는 것이 좋나요?",
            f"{locality} 학생의 {subject} 내신 준비는 어느 시점에 시작해야 하나요?",
            f"{subject} 시험 범위를 받은 뒤 {locality} 학생은 무엇부터 시작하면 좋나요?",
            f"{locality} {level} {subject} 복습 계획은 시험 몇 주 전부터 세우나요?",
            f"내신 준비가 늦어지기 전에 {locality} {subject} 상담에서 무엇을 확인하나요?",
            f"{locality} 학생의 {subject} 시험 준비 시점은 어떻게 정하나요?",
            f"{level} {subject} 내신 대비를 시작할 때 {locality} 학부모가 볼 기준은 무엇인가요?",
            f"{locality} {subject} 학습에서 학교 시험 대비로 전환할 시점은 언제인가요?",
        ])

    if "선행" in value and "복습" in value:
        return choose("preview-review", [
            f"{locality} {level} {subject} 공부는 선행과 복습 중 무엇을 먼저 해야 하나요?",
            f"{locality} 학생에게 선행보다 복습이 먼저 필요한지는 어떻게 판단하나요?",
            f"현재 단원이 불안한 {locality} 학생은 {subject} 선행을 멈춰야 하나요?",
            f"{locality} {subject} 상담에서 선행·복습 비중은 어떻게 정하나요?",
            f"{level} {subject} 진도와 복습 사이의 균형은 어떤 자료로 확인하나요?",
            f"{locality} 학생의 {subject} 선행 수준은 최근 오답과 함께 봐야 하나요?",
        ])

    if "숙제" in value or "과제" in value:
        return choose("homework", [
            f"{locality} {level} {subject} 숙제는 어떤 기준으로 정하는 것이 좋나요?",
            f"{locality} 학생에게 문제 양보다 중요한 {subject} 과제 기준은 무엇인가요?",
            f"{subject} 숙제 뒤 오답 확인은 {locality} 상담에서 어떻게 살펴보나요?",
            f"{locality} {subject}학원 과제가 학생에게 맞는지는 어떻게 판단하나요?",
            f"과제를 끝내기 어려운 {locality} 학생은 무엇부터 조정해야 하나요?",
            f"{locality} {level} {subject} 수업 후 복습 과제는 어느 정도가 적당한가요?",
        ])

    if ("영어" in value and "수학" in value) or "시간표" in value:
        return choose("subject-balance", [
            f"{locality} 학생의 영어·수학 학습 시간은 어떻게 나누는 것이 좋나요?",
            f"{locality} {level} 학생이 영어와 수학을 병행할 때 우선순위는 어떻게 정하나요?",
            f"영어·수학 과제를 함께 관리하면 {locality} 학생의 시간표는 어떻게 조정하나요?",
            f"{locality} 상담에서 영어와 수학의 주간 학습량도 함께 확인하나요?",
            f"두 과목을 함께 공부하는 {locality} 학생은 복습 시간을 어떻게 배분하나요?",
            f"{locality} 학생의 영어·수학 일정이 겹칠 때 무엇을 먼저 조정하나요?",
        ])

    if "준비물" in value or "가져갈" in value or "상담 자료" in value:
        return choose("consultation-material", [
            f"{locality} {subject} 상담 전에는 어떤 학습 자료를 준비하면 좋나요?",
            f"{locality} 학부모가 첫 {subject} 상담에 가져갈 자료는 무엇인가요?",
            f"최근 시험지와 오답노트 중 {locality} {subject} 상담에 무엇이 더 필요한가요?",
            f"{locality} 학생의 {subject} 출발점을 확인하려면 어떤 기록을 챙겨야 하나요?",
            f"{subject} 상담을 구체화하기 위해 {locality} 학생이 준비할 것은 무엇인가요?",
            f"{locality} {level} {subject} 상담 전에 교재와 시험지도 확인하나요?",
        ])

    if "주소" in value or "위치" in value or "등원" in value:
        return choose("location", [
            f"{locality} {subject}학원 선택에서 센터 주소를 미리 확인해야 하나요?",
            f"{locality} 학생의 등원 동선은 {subject} 학습 계획과 함께 봐야 하나요?",
            f"센터 위치가 {locality} {level} 학생의 복습 시간에 어떤 영향을 주나요?",
            f"{locality} {subject} 상담 전 실제 방문 주소도 확인하는 것이 좋나요?",
            f"{locality} 학생에게 무리 없는 등원 시간은 어떻게 점검하나요?",
            f"{subject} 수업을 꾸준히 이어가려면 {locality} 센터 위치도 중요한가요?",
        ])

    if "성적" in value or "입시 결과" in value or "확답" in value or "보장" in value:
        return choose("outcome", [
            f"{locality} {subject}학원 상담에서 성적 향상을 보장받을 수 있나요?",
            f"{locality} {level} {subject} 수업은 어떤 변화 기준을 설명해야 하나요?",
            f"성적 결과보다 {locality} {subject} 상담에서 먼저 확인할 것은 무엇인가요?",
            f"{locality} 학생의 {subject} 학습 변화는 어떤 기록으로 살펴보나요?",
            f"{subject} 수업 성과를 단정하기 어려운 이유는 무엇인가요?",
            f"{locality} 학부모는 {subject} 상담에서 어떤 현실적인 목표를 확인해야 하나요?",
        ])

    if "레벨 테스트" in value or "진단" in value:
        return choose("diagnosis", [
            f"{locality} {subject} 상담에서 레벨 테스트만 보면 충분한가요?",
            f"{locality} 학생의 {subject} 출발점은 어떤 자료로 진단하나요?",
            f"점수 외에 {locality} {level} {subject} 진단에서 확인할 것은 무엇인가요?",
            f"{locality} {subject}학원 첫 진단은 어떤 순서로 진행해 확인하나요?",
            f"최근 오답은 {locality} 학생의 {subject} 수준 판단에 어떻게 활용하나요?",
            f"{locality} 학생의 {subject} 약점은 단원별로 나누어 확인하나요?",
        ])

    if "변화" in value:
        return choose("change", [
            f"{locality} {subject} 상담 뒤 학부모가 먼저 확인할 변화는 무엇인가요?",
            f"{locality} 학생의 {subject} 학습 변화는 어떤 기록에서 볼 수 있나요?",
            f"상담 후 {locality} 학생의 공부 습관은 무엇부터 달라져야 하나요?",
            f"{locality} {subject} 학습 계획이 맞는지는 언제 다시 점검하나요?",
            f"{subject} 수업 뒤 {locality} 학부모가 확인할 행동 변화는 무엇인가요?",
            f"{locality} 학생의 다음 복습 계획은 어떤 기준으로 조정하나요?",
        ])

    if focus in value:
        focus_topic = korean_josa(focus, "은/는")
        return choose("learning-focus", [
            f"{focus_topic} {locality} {subject} 상담에서 어떻게 확인하나요?",
            f"{locality} 학생의 {korean_josa(focus, '을/를')} 수업 선택 기준으로 봐야 하나요?",
            f"{subject} 학습에서 {korean_josa(focus, '이/가')} 중요한 이유는 무엇인가요?",
            f"{locality} {level} {subject} 상담에서는 {korean_josa(focus, '을/를')} 어떻게 기록하나요?",
            f"{korean_josa(focus, '이/가')} 필요한 {locality} 학생은 무엇부터 조정해야 하나요?",
            f"{locality} {subject} 수업에서 {korean_josa(focus, '은/는')} 다음 복습에 어떻게 반영되나요?",
        ])
    return value


def individualize_faq_items(
    faq: list[tuple[str, str]], context: dict[str, object],
) -> list[tuple[str, str]]:
    """Diversify FAQ wording while preserving each answer's original intent."""
    if not faq:
        return faq

    locality = str(context["locality"])
    focus = str(context["learning_focus"])
    questions = list(faq)
    if str(context.get("category")) == "초등학생수학학원" and len(questions) >= 4:
        homework_answer = questions[3][1]
        extra = f"{korean_josa(focus, '이/가')} 다음 복습에 반영되는지도 함께 살펴보는 것이 좋습니다."
        if focus not in homework_answer:
            homework_answer = dedupe_text_sentences(f"{homework_answer} {extra}")
        questions[3] = (questions[3][0], homework_answer)
    return [
        (diversify_faq_question(question, context, index), answer)
        for index, (question, answer) in enumerate(questions, 1)
    ]


def compact_meta(original: str, title: str, row: dict[str, str], config: dict[str, str]) -> str:
    original = normalize(original)
    locality = title[: -len(config["label"])].strip() if title.endswith(config["label"]) else ""
    if locality:
        original = re.sub(
            rf"(?<![가-힣A-Za-z0-9]){re.escape(locality)}\s+{re.escape(locality)}(?![가-힣A-Za-z0-9])",
            locality,
            original,
        )
    if 70 <= len(original) <= 100:
        return original
    region = normalize(f"{row['지역']} {row['시or구']}")
    value = (
        f"{region} {title}의 학교·학년별 학습 기준과 {config['subject']} 진단, "
        "과제·오답 관리, 상담 전 확인할 센터 정보를 정리했습니다."
    )
    if len(value) > 100:
        value = value[:97].rstrip(" ,·") + "."
    return value


def individualized_meta_candidates(
    title: str, row: dict[str, str], config: dict[str, str], context: dict[str, object],
) -> list[str]:
    """Build many complete, fact-based descriptions instead of token swaps."""
    locality = str(context["locality"])
    level = str(context["level"])
    subject = str(context["subject"])
    focus = str(context["learning_focus"])
    region = normalize(f"{row['지역']} {row['시or구']}")
    schools = [str(item) for item in context.get("schools", [])]
    if len(schools) > 1:
        school_scope = f"{schools[0]} 등 확인된 학교 자료"
    elif schools:
        school_scope = f"확인된 {schools[0]} 학교 자료"
    else:
        school_scope = "재학 학교의 최신 시험 범위"
    openers = [
        f"{korean_josa(title, '을/를')} 찾는 학부모라면",
        f"{region} {title} 상담 전에는",
        f"{locality} {level} {subject} 학습을 점검할 때는",
        f"{title} 선택에서는",
        f"{locality} 학생의 {subject} 공부를 살필 때는",
        f"{region} {locality} {subject} 상담에서는",
        f"{locality} {level} 학생의 {subject} 수업을 비교할 때는",
        f"{title} 첫 상담에서는",
    ]
    cores = [
        f"{focus}, {school_scope}, 과제·오답 관리 순서를 함께 확인해야 합니다.",
        f"{school_scope}와 {focus}, 최근 오답의 재풀이 여부를 나누어 봅니다.",
        f"현재 단원과 {focus}, 학교 진도에 맞춘 복습 계획을 먼저 확인합니다.",
        f"최근 시험 자료에서 {korean_josa(focus, '과/와')} 과제 수행 기록을 함께 살펴야 합니다.",
        f"{focus}, 시험 범위, 수업 뒤 복습 기록이 연결되는지 확인합니다.",
        f"학교 진도와 {focus}, 학생이 혼자 다시 풀 수 있는지를 비교합니다.",
        f"{school_scope}를 기준으로 {korean_josa(focus, '과/와')} 오답 원인을 함께 살펴봅니다.",
        f"학생의 현재 교재, {focus}, 주간 과제 기록을 순서대로 확인합니다.",
    ]
    closers = [
        "확인된 센터 정보와 상담 준비 항목도 함께 안내합니다.",
        "학생에게 필요한 첫 학습 순서를 정할 기준을 안내합니다.",
        "상담 전에 준비할 자료와 수업 비교 기준을 함께 정리했습니다.",
        "현재 학습 상태에 맞는 복습 우선순위를 확인할 수 있습니다.",
        "과장된 결과 대신 확인 가능한 학습 행동을 기준으로 안내합니다.",
        "센터 방문 전 확인할 위치와 학습 상담 기준도 함께 살펴봅니다.",
        "수업 선택 전에 묻기 좋은 질문과 센터 정보를 정리했습니다.",
        "학생별 진단과 다음 복습 계획을 구체화할 기준을 안내합니다.",
    ]
    return [
        normalize(f"{opening} {core} {closing}")
        for opening in openers for core in cores for closing in closers
        if 70 <= len(normalize(f"{opening} {core} {closing}")) <= 100
    ]


def validated_meta(
    value: str, title: str, row: dict[str, str], config: dict[str, str], context: dict[str, object],
) -> str:
    """Keep the final, transformed description within a complete 70–100 chars."""
    value = normalize(value)
    individualized = individualized_meta_candidates(title, row, config, context)
    if individualized:
        return final_polish_text(
            stable_choice(f"{context['seed']}|individualized-meta", individualized)
        )
    if 70 <= len(value) <= 100:
        return value
    region = normalize(f"{row['지역']} {row['시or구']}")
    candidates = [
        (
            f"{region} {title}의 {config['subject']} 진단, 학교 진도, {context['learning_focus']}, "
            "과제·오답 관리와 상담 전 센터 확인 기준을 정리했습니다."
        ),
        (
            f"{title} 선택 전에 확인할 {config['level']} {config['subject']} 진단, 학교 진도, "
            f"{context['learning_focus']}, 과제·오답 관리와 지역 센터 상담 기준을 정리했습니다."
        ),
    ]
    for candidate in candidates:
        candidate = normalize(candidate)
        if 70 <= len(candidate) <= 100:
            return final_polish_text(candidate)
    compact = normalize(candidates[-1])
    return final_polish_text(compact[:97].rstrip(" ,·") + ".")


def individualize_summary(value: str, context: dict[str, object]) -> str:
    """Add a concrete answer-first sentence with combinatorial variation."""
    locality = str(context["locality"])
    subject = str(context["subject"])
    focus = str(context["learning_focus"])
    if subject == "수학":
        evidence = [
            "최근 오답", "현재 단원", "풀이 과정", "서술형 답안", "계산 기록",
            "학교 범위표", "사용 중인 교재", "단원별 정답률", "과제 수행 기록", "재풀이 결과",
        ]
        next_steps = [
            "개념 복습 순서", "오답 재풀이 시점", "학교 시험 준비", "문장제 보완 순서",
            "서술형 연습 순서", "주간 과제 분량", "선행·복습 비중", "계산 검산 습관",
            "다음 단원 진입 시점", "풀이 시간 배분",
        ]
    else:
        evidence = [
            "최근 오답", "교과서 지문", "단어 기록", "문법 적용 문항", "독해 근거 표시",
            "학교 범위표", "서술형 답안", "사용 중인 교재", "과제 수행 기록", "문장 재작성 결과",
        ]
        next_steps = [
            "어휘 복습 순서", "문법 보완 순서", "독해 근거 확인", "서술형 연습 순서",
            "학교 시험 준비", "주간 과제 분량", "읽기·쓰기 비중", "오답 문장 재작성",
            "다음 지문 학습 시점", "풀이 시간 배분",
        ]
    endings = [
        "먼저 정합니다.", "상담의 첫 기준으로 삼습니다.", "학생에게 맞게 조정합니다.",
        "이번 주 우선순위로 정합니다.", "수업 선택 전에 구체화합니다.",
        "학생이 다시 설명할 수 있는지 확인합니다.", "가정 복습 계획과 연결합니다.",
        "다음 학습 기록에 반영합니다.",
    ]
    evidence_value = stable_choice(f"{context['seed']}|summary-evidence", evidence)
    next_value = stable_choice(f"{context['seed']}|summary-next", next_steps)
    ending = stable_choice(f"{context['seed']}|summary-ending", endings)
    extra = (
        f"{locality} 상담에서는 {korean_josa(focus, '과/와')} {korean_josa(evidence_value, '을/를')} 함께 비교해 "
        f"{korean_josa(next_value, '을/를')} {ending}"
    )
    return dedupe_text_sentences(f"{final_polish_text(value)} {final_polish_text(extra)}")


def paragraph_html(value: str, css: str = "") -> str:
    class_attr = f' class="{css}"' if css else ""
    return f"<p{class_attr}>{esc(normalize(value))}</p>"


def schema_script(graph: list[dict]) -> str:
    value = {"@context": "https://schema.org", "@graph": graph}
    return '<script type="application/ld+json">' + json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "</script>"


def site_header(active: str = "subjects") -> str:
    links = [
        ("home", "/", "홈"),
        ("guide", "/학습가이드/", "학습가이드"),
        ("contact", "/상담문의/", "상담문의"),
        ("national", "/전국학원/", "전국학원"),
        ("subjects", "/과목별학원/", "과목별학원"),
    ]
    nav = "".join(
        f'<a href="{href}"' + (' class="is-active" aria-current="page"' if key == active else "") + f'>{label}</a>'
        for key, href, label in links
    )
    return (
        '<a class="subject-skip-link" href="#main">본문 바로가기</a>'
        '<header class="site-header"><div class="container nav-wrap">'
        f'<a class="brand" href="/" aria-label="{esc(SITE_NAME)} 홈페이지"><span class="brand-mark" aria-hidden="true">L</span>'
        f'<span class="brand-text">{esc(SITE_NAME)}<small>진단 · 계획 · 실행 · 재학습</small></span></a>'
        f'<nav class="nav-menu" aria-label="상단 메뉴">{nav}</nav>'
        '</div></header>'
    )


def site_footer() -> str:
    return (
        '<footer class="site-footer"><div class="container footer-card">'
        '<div><strong>학습관리학원</strong><p>학생별 진도 수업과 공부 습관 코칭을 함께 운영합니다.</p></div>'
        '<div><strong>페이지 안내</strong><p><a href="/과목별학원/">과목별학원</a> · <a href="/전국학원/">전국학원</a> · <a href="/sitemap.xml">사이트맵</a></p></div>'
        '</div></footer>'
        f'<aside class="floating-actions" aria-label="빠른 문의"><a href="tel:{PHONE_LINK}">📞 전화</a>'
        f'<a href="sms:{PHONE_LINK}">💬 문자</a>'
        '<a href="/상담문의/">☁️ 문의</a></aside>'
    )


def page_head(
    *, title: str, description: str, canonical: str, asset_prefix: str,
    image_url: str, graph: list[dict], page_type: str = "article",
) -> str:
    return f'''<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="alternate" type="application/rss+xml" title="학습관리학원 학습 안내" href="{DOMAIN}/rss.xml">
  <link rel="icon" href="{asset_prefix}assets/favicon.png" type="image/png">
  <link rel="stylesheet" href="{asset_prefix}assets/site.css">
  <link rel="stylesheet" href="{asset_prefix}assets/subject.css">
  <meta property="og:type" content="{page_type}">
  <meta property="og:locale" content="ko_KR">
  <meta property="og:site_name" content="학습관리학원">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(SHARE_IMAGE_URL)}">
  <meta property="og:image:width" content="1718">
  <meta property="og:image:height" content="915">
  <meta property="og:image:alt" content="{esc(SHARE_IMAGE_ALT)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{esc(SHARE_IMAGE_URL)}">
  <meta name="twitter:image:alt" content="{esc(SHARE_IMAGE_ALT)}">
  {schema_script(graph)}
</head>'''


def address_schema(row: dict[str, str]) -> dict:
    return {
        "@type": "PostalAddress",
        "streetAddress": normalize(row.get("센터 주소", "")),
        "addressLocality": normalize(row.get("시or구", "")),
        "addressRegion": normalize(row.get("지역", "")),
        "addressCountry": "KR",
    }


def offer_schema(row: dict[str, str]) -> list[dict]:
    url = normalize(row.get("센터 교습비", ""))
    if not url:
        return []
    return [{"@type": "Offer", "name": "센터 교습비 안내", "url": url}]


def center_entity_id(center_name: str, address: str) -> str:
    """Return one site-wide identity for the same verified center."""
    identity = "|".join([normalize(center_name), normalize(address)])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{DOMAIN}/#center-{digest}"


def organization_entity_id(row: dict[str, str], locality: str) -> str:
    return center_entity_id(
        normalize(row.get("센터명", "")) or f"{locality} 학습센터",
        normalize(row.get("센터 주소", "")) or locality,
    )


def schools_for(row: dict[str, str], field: str) -> list[str]:
    return split_school_names(row.get(field, ""))


def resolve_map_file(raw_name: str, slug: str) -> str:
    map_dir = ROOT / "assets" / "maps"
    raw_name = normalize(raw_name)
    candidates = [
        raw_name,
        raw_name.replace(" ", "-"),
        raw_name.replace(" ", ""),
        f"{slug}.jpg",
        f"{slug}.png",
        f"{slug}.webp",
    ]
    for candidate in candidates:
        if candidate and (map_dir / candidate).is_file():
            return candidate
    key = re.sub(r"[^a-z0-9]", "", Path(raw_name).stem.lower())
    slug_key = re.sub(r"[^a-z0-9]", "", slug.lower())
    matches = [
        path.name for path in map_dir.iterdir()
        if path.is_file() and re.sub(r"[^a-z0-9]", "", path.stem.lower()) in {key, slug_key}
    ]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Map missing or ambiguous: raw={raw_name!r}, slug={slug!r}, matches={matches}")


def detail_graph(
    *, title: str, description: str, canonical: str, locality: str, slug: str,
    row: dict[str, str], config: dict[str, str], faq: list[tuple[str, str]],
    body_sections: list[tuple[str, list[str]]], image_url: str, national_slug: str,
) -> list[dict]:
    org_id = organization_entity_id(row, locality)
    service_id = canonical + "#service"
    webpage_id = canonical + "#webpage"
    source_id = DOMAIN + "/#center-information-source"
    schools = schools_for(row, config["school_field"])
    school_nodes = [{"@type": "School", "name": name} for name in schools]
    offers = offer_schema(row)
    grades = list(dict.fromkeys(
        normalize(value)
        for field in ("가능학년\n(수학)", "가능학년\n(영어)")
        for value in row.get(field, "").split(",")
        if normalize(value)
    ))
    organization: dict = {
        "@type": ["EducationalOrganization", "LocalBusiness"], "@id": org_id,
        "name": normalize(row.get("센터명", "")) or f"{locality} 학습센터",
        "url": absolute_url("전국학원", national_slug), "telephone": "+82-10-6839-8283",
        "address": address_schema(row),
        "areaServed": {"@type": "Place", "name": locality},
        "makesOffer": [
            {
                "@type": "Offer",
                "name": f"{title} 학습 상담",
                "itemOffered": {"@id": service_id},
            },
            *offers,
        ],
    }
    if row.get("교육지원청 등록번호"):
        organization["identifier"] = normalize(row["교육지원청 등록번호"])
    if grades:
        organization["educationalLevel"] = grades
    source = {
        "@type": "CreativeWork", "@id": source_id,
        "name": "센터정보 정리 자료", "dateModified": TODAY,
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": DOMAIN + "/"},
    }
    service: dict = {
        "@type": "Service", "@id": service_id,
        "name": title, "serviceType": config["label"],
        "provider": {"@id": org_id},
        "areaServed": {"@type": "Place", "name": locality},
        "audience": {"@type": "EducationalAudience", "educationalRole": "student", "audienceType": config["level"]},
    }
    if offers:
        service["offers"] = offers
    webpage = {
        "@type": "WebPage", "@id": webpage_id, "url": canonical,
        "name": title, "description": description, "inLanguage": "ko-KR",
        "isPartOf": {"@id": DOMAIN + "/#website"},
        "about": [{"@id": org_id}, {"@id": service_id}],
        "mainEntity": {"@id": service_id},
        "breadcrumb": {"@id": canonical + "#breadcrumb"},
        "primaryImageOfPage": {"@type": "ImageObject", "contentUrl": image_url, "caption": f"{title} 수업 안내"},
        "isBasedOn": {"@id": source_id},
        "dateModified": TODAY,
    }
    article = {
        "@type": "Article", "@id": canonical + "#article",
        "headline": title, "description": description,
        "mainEntityOfPage": {"@id": webpage_id},
        "author": {"@id": org_id},
        "publisher": {"@id": org_id},
        "image": {"@type": "ImageObject", "url": image_url, "caption": f"{title} 수업 안내"},
        "isBasedOn": {"@id": source_id},
        "about": [{"@id": service_id}, {"@type": "Thing", "name": locality}, {"@type": "Thing", "name": config["subject"]}],
        "mentions": school_nodes,
        "articleSection": ["과목별학원", config["label"], row.get("지역", ""), row.get("시or구", ""), locality],
        "hasPart": [{"@type": "WebPageElement", "name": heading} for heading, _ in body_sections],
        "datePublished": TODAY, "dateModified": TODAY, "inLanguage": "ko-KR",
    }
    breadcrumb = {
        "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": absolute_url("과목별학원")},
            {"@type": "ListItem", "position": 3, "name": config["label"], "item": absolute_url("과목별학원", config["slug"])},
            {"@type": "ListItem", "position": 4, "name": title, "item": canonical},
        ],
    }
    faq_page = {
        "@type": "FAQPage", "@id": canonical + "#faq",
        "mainEntity": [
            {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
            for question, answer in faq
        ],
    }
    related = []
    related_categories = related_categories_for(config)
    for position, item in enumerate(related_categories, 1):
        related.append({
            "@type": "ListItem", "position": position,
            "name": f"{locality} {item['label']}",
            "url": absolute_url("과목별학원", item["slug"], slug),
        })
    related.extend([
        {
            "@type": "ListItem", "position": len(related) + 1,
            "name": f"{locality} 전국학원 기본 안내",
            "url": absolute_url("전국학원", national_slug),
        },
        {
            "@type": "ListItem", "position": len(related) + 2,
            "name": f"{config['label']} 전체 지역",
            "url": absolute_url("과목별학원", config["slug"]),
        },
        {
            "@type": "ListItem", "position": len(related) + 3,
            "name": "과목별학원 전체 보기",
            "url": absolute_url("과목별학원"),
        },
    ])
    item_list = {"@type": "ItemList", "@id": canonical + "#related", "name": f"{locality} 관련 학원 안내", "itemListElement": related}
    return [organization, source, webpage, breadcrumb, article, service, faq_page, item_list]


def detail_page(
    *, config: dict[str, str], sections: dict[str, str], locality: str,
    slug: str, row: dict[str, str], map_file: str,
) -> str:
    title = normalize(sections["페이지타이틀"])
    source_text = "\n".join(sections.values())
    context = content_context(
        title=title, locality=locality, slug=slug, row=row, config=config,
        source_text=source_text,
    )
    description = validated_meta(
        final_polish_text(naturalize_text(
            compact_meta(sections["메타설명"], title, row, config), context, "meta-description"
        )),
        title,
        row,
        config,
        context,
    )
    raw_intro, raw_body_sections = parse_body(sections["본문"])
    intro, body_sections = individualize_body(raw_intro, raw_body_sections, context)
    # The same transformed FAQ list feeds both the visible accordions and
    # FAQPage JSON-LD, so their questions and answers cannot drift apart.
    faq = [
        (
            final_polish_text(naturalize_text(question, context, f"faq-question-{index}")),
            dedupe_text_sentences(final_polish_text(naturalize_text(answer, context, f"faq-answer-{index}"))),
        )
        for index, (question, answer) in enumerate(parse_faq(sections["FAQ"]), 1)
    ]
    faq = individualize_faq_items(faq, context)
    # Individualization may append a newly composed sentence after the first
    # polish pass.  Run the same public-copy cleanup once more so generated
    # FAQ text and its JSON-LD counterpart stay natural and identical.
    faq = [
        (final_polish_text(question), dedupe_text_sentences(final_polish_text(answer)))
        for question, answer in faq
    ]
    cases = naturalize_cases(parse_cases(sections["학부모후기"]), context)
    summary = individualize_summary(
        dedupe_text_sentences(final_polish_text(naturalize_text(
            sections["JSON-LD 요약"], context, "summary"
        ))),
        context,
    )
    # Validate the actual final strings that feed both visible HTML and JSON-LD.
    # This catches facts introduced by individualization/polish code after the
    # first naturalization pass, without relying on a later site audit.
    assert_verified_fact_claims(description, context, "final-meta-description")
    assert_verified_fact_claims(intro, context, "final-intro")
    for section_index, (heading, paragraphs) in enumerate(body_sections, 1):
        assert_verified_fact_claims(heading, context, f"final-heading-{section_index}")
        for paragraph_index, paragraph in enumerate(paragraphs, 1):
            assert_verified_fact_claims(
                paragraph, context, f"final-paragraph-{section_index}-{paragraph_index}"
            )
    for faq_index, (question, answer) in enumerate(faq, 1):
        assert_verified_fact_claims(question, context, f"final-faq-question-{faq_index}")
        assert_verified_fact_claims(answer, context, f"final-faq-answer-{faq_index}")
    for case_index, case in enumerate(cases, 1):
        assert_verified_fact_claims(case, context, f"final-case-{case_index}")
    assert_verified_fact_claims(summary, context, "final-summary")
    if len(faq) not in {4, 5} or len(body_sections) not in {5, 6, 7}:
        raise ValueError(f"Unexpected content shape: {title}: body={len(body_sections)} faq={len(faq)}")
    canonical = absolute_url("과목별학원", config["slug"], slug)
    representative_url = representative_image_url(canonical)
    national_slug = national_slug_for(locality)
    body_image_name = "seoul6839.webp" if row.get("지역") == "서울" else "local6839.webp"
    body_image = f"../../../assets/centers/common/{body_image_name}"
    map_image = f"../../../assets/maps/{map_file}"
    image_url = representative_url
    graph = detail_graph(
        title=title, description=description, canonical=canonical, locality=locality, slug=slug,
        row=row, config=config, faq=faq, body_sections=body_sections, image_url=image_url,
        national_slug=national_slug,
    )
    body_sections_html = "".join(
        '<section class="academy-article-section">'
        f'<h2>{esc(heading)}</h2>' + "".join(paragraph_html(value) for value in paragraphs) + "</section>"
        for heading, paragraphs in body_sections
    )
    faq_html = "".join(
        f'<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>'
        for question, answer in faq
    )
    cases_html = "".join(f'<blockquote class="academy-case-card">{esc(value)}</blockquote>' for value in cases)
    schools = schools_for(row, config["school_field"])
    school_tags = "".join(f"<span>{esc(value)}</span>" for value in schools)
    grades = normalize(row.get(config["grade_field"], "")) or "상담 시 현재 학년과 과목을 확인합니다."
    identifier = normalize(row.get("교육지원청 등록번호", "")) or "제공 자료에서 확인 후 안내"
    tuition = normalize(row.get("센터 교습비", ""))
    tuition_html = (
        f'<a class="btn btn-outline academy-fee-link" href="{esc(tuition)}" target="_blank" rel="noopener">센터 교습비 안내 확인</a>'
        if tuition else ""
    )
    related_links = "".join(
        f'<a href="/과목별학원/{item["slug"]}/{esc(slug)}/">{esc(locality)} {esc(item["label"])}</a>'
        for item in related_categories_for(config)
    )
    related_links += f'<a href="/전국학원/{esc(national_slug)}/">{esc(locality)} 전국학원 기본 안내</a>'
    head = page_head(
        title=f"{title} | {SITE_NAME}", description=description, canonical=canonical,
        asset_prefix="../../../", image_url=image_url, graph=graph,
    )
    return f'''<!doctype html>
<html lang="ko">
{head}
<body class="general-page subject-page academy-page">
  {site_header("subjects")}
  <main id="main">
    <header class="academy-hero reveal">
      <div class="academy-hero-copy">
        <nav class="academy-breadcrumb" aria-label="현재 위치"><a href="/">홈</a><span aria-hidden="true">›</span><a href="/과목별학원/">과목별학원</a><span aria-hidden="true">›</span><a href="/과목별학원/{esc(config['slug'])}/">{esc(config['label'])}</a><span aria-hidden="true">›</span><span aria-current="page">{esc(title)}</span></nav>
        <p class="eyebrow">{esc(config['english'])} · LOCAL GUIDE</p>
        <h1>{esc(title)}</h1>
        <p class="lead">{esc(description)}</p>
      </div>
      <aside class="academy-hero-aside"><strong>{esc(locality)}</strong><span>{esc(row.get('지역'))} · {esc(row.get('시or구'))} 학습 안내</span></aside>
    </header>

    <section class="academy-media-section" aria-label="{esc(title)} 이미지 안내">
      <img src="{esc(representative_url)}" alt="{esc(title)} {esc(SITE_NAME)} 대표" style="display:none;">
      <div class="academy-media-grid">
        <figure class="academy-main-media reveal"><img src="{esc(body_image)}" width="1300" height="1900" alt="{esc(title)} 수업 안내 {esc(SITE_NAME)}" fetchpriority="high"><figcaption>{esc(title)} 학습관리 안내</figcaption></figure>
        <figure class="academy-map-card reveal"><img src="{esc(map_image)}" alt="{esc(title)} 지도 {esc(SITE_NAME)}" loading="lazy"><figcaption>{esc(locality)} 센터 위치 참고 지도</figcaption></figure>
      </div>
    </section>

    <div class="academy-content-wrap">
      <section class="academy-summary reveal" aria-labelledby="summary-title"><h2 id="summary-title">30초 핵심 요약</h2><p>{esc(summary)}</p></section>

      <section class="academy-facts reveal" aria-labelledby="facts-title">
        <p class="eyebrow">Verified Center Information</p><h2 id="facts-title">상담 전에 확인할 센터 정보</h2>
        <div class="academy-fact-grid">
          <div class="academy-fact-card"><strong>센터</strong><span>{esc(row.get('센터명'))}</span></div>
          <div class="academy-fact-card"><strong>주소</strong><span>{esc(row.get('센터 주소'))}</span></div>
          <div class="academy-fact-card"><strong>센터 전체 수업 가능 학년</strong><span>{esc(grades)}</span></div>
          <div class="academy-fact-card"><strong>교육지원청 등록 정보</strong><span>{esc(identifier)}</span></div>
        </div>
        <p class="academy-provenance"><strong>자료 기준</strong><span>센터정보 정리 자료 · 최종 검수 {TODAY}</span></p>
        {('<div class="academy-school-tags" aria-label="제공 자료에 포함된 수업 학교">' + school_tags + '</div>') if school_tags else ''}
        {tuition_html}
      </section>

      <article class="academy-article reveal" aria-labelledby="article-title">
        <p class="eyebrow">Local Learning Article</p><h2 id="article-title">{esc(title)} 선택과 학습관리 기준</h2>
        {paragraph_html(intro, 'lead')}
        {body_sections_html}
      </article>

      <section class="academy-faq reveal" aria-labelledby="faq-title"><p class="eyebrow">Frequently Asked Questions</p><h2 id="faq-title">{esc(title)} 자주 묻는 질문</h2><div class="faq-list">{faq_html}</div></section>

      <section class="academy-cases reveal" aria-labelledby="case-title"><p class="eyebrow blue">Consultation Scenarios</p><h2 id="case-title">상담 상황 예시</h2><p class="academy-case-note">아래 내용은 학생의 학습 상황을 설명하기 위한 예시이며 실제 학생의 후기나 성과를 뜻하지 않습니다.</p><div class="academy-case-list">{cases_html}</div></section>
    </div>

    <section class="academy-related"><div class="academy-related-panel reveal"><p class="eyebrow">Related Local Guides</p><h2>{esc(locality)} 다른 과목·학년 안내</h2><div class="academy-related-grid">{related_links}<a href="/과목별학원/{esc(config['slug'])}/">{esc(config['label'])} 전체 지역</a><a href="/과목별학원/">과목별학원 전체 보기</a></div></div></section>
  </main>
  {site_footer()}
  <script src="../../../assets/subject-directory.js" defer></script>
</body>
</html>'''


def directory_html(rows: list[dict[str, str]], config: dict[str, str]) -> str:
    grouped: OrderedDict[str, OrderedDict[str, list[dict[str, str]]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["지역"], OrderedDict()).setdefault(row["시or구"], []).append(row)
    groups = []
    for region, cities in grouped.items():
        city_html = []
        region_count = sum(len(values) for values in cities.values())
        for city, values in cities.items():
            links = "".join(
                f'<a class="academy-local-link" data-locality="{esc(value.get("_subject_locality", value["근처 수업가능 동네"]))}" href="/과목별학원/{esc(config["slug"])}/{esc(value.get("_subject_slug", value["근처 수업가능 동네"]))}/"><span>{esc(value.get("_subject_locality", value["근처 수업가능 동네"]))}</span></a>'
                for value in values
            )
            city_html.append(
                f'<section class="academy-city-group" data-city="{esc(city)}"><h3 class="academy-city-title">{esc(city)} <small>{len(values)}곳</small></h3><div class="academy-local-grid">{links}</div></section>'
            )
        groups.append(
            f'<details class="academy-region-group" data-region="{esc(region)}"><summary><span class="academy-region-heading"><strong>{esc(region)}</strong><small>{len(cities)}개 시군구 · {region_count}개 동네</small></span><span class="academy-region-toggle" aria-hidden="true"></span></summary><div class="academy-region-content">{"".join(city_html)}</div></details>'
        )
    return "".join(groups)


def category_hub(rows: list[dict[str, str]], config: dict[str, str]) -> str:
    canonical = absolute_url("과목별학원", config["slug"])
    title = f"지역별 {config['label']} 안내 | {SITE_NAME}"
    description = f"전국 371개 동네의 {config['label']} 학습 기준과 센터 정보를 지역·시군구별로 찾아볼 수 있도록 정리했습니다."
    item_list = {
        "@type": "ItemList", "@id": canonical + "#directory", "name": f"지역별 {config['label']}",
        "numberOfItems": len(rows),
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": f"{row.get('_subject_locality', row['근처 수업가능 동네'])} {config['label']}", "url": absolute_url("과목별학원", config["slug"], row.get("_subject_slug", row["근처 수업가능 동네"]))}
            for index, row in enumerate(rows, 1)
        ],
    }
    graph = [
        {"@type": "CollectionPage", "@id": canonical + "#webpage", "url": canonical, "name": title, "description": description, "isPartOf": {"@id": DOMAIN + "/#website"}, "about": {"@type": "Thing", "name": config["label"]}, "dateModified": TODAY, "inLanguage": "ko-KR"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": absolute_url("과목별학원")},
            {"@type": "ListItem", "position": 3, "name": config["label"], "item": canonical},
        ]},
        item_list,
    ]
    head = page_head(title=title, description=description, canonical=canonical, asset_prefix="../../", image_url=SHARE_IMAGE_URL, graph=graph, page_type="website")
    directory = directory_html(rows, config)
    return f'''<!doctype html><html lang="ko">{head}<body class="general-page subject-page academy-page">{site_header("subjects")}<main id="main">
      <header class="academy-hero reveal"><div class="academy-hero-copy"><nav class="academy-breadcrumb" aria-label="현재 위치"><a href="/">홈</a><span aria-hidden="true">›</span><a href="/과목별학원/">과목별학원</a><span aria-hidden="true">›</span><span aria-current="page">{esc(config['label'])}</span></nav><p class="eyebrow">{esc(config['english'])} DIRECTORY</p><h1>지역별 {esc(config['label'])} 안내</h1><p class="lead">{esc(description)}</p></div><aside class="academy-hero-aside"><strong>371</strong><span>확인된 지역·센터 정보와 개별 학습 안내를 연결한 동네별 자료</span></aside></header>
      <section class="section section-compact"><div class="academy-directory reveal"><div class="academy-directory-head"><div><p class="eyebrow">Local Academy Directory</p><h2>동네 이름으로 빠르게 찾기</h2><p>광역지역과 시군구를 펼치거나 동네 이름을 검색해 해당 페이지로 이동하세요.</p></div><label class="academy-search-label">동네 검색<input class="academy-search-input" type="search" placeholder="예: 명일동, 불당동" autocomplete="off"></label></div><div class="academy-directory-tools"><button type="button" data-action="expand">모두 펼치기</button><button type="button" data-action="collapse">모두 접기</button><span class="academy-result-count" aria-live="polite">전체 371개 동네</span></div><div class="academy-region-list">{directory}</div></div></section>
      <section class="cta-section"><div class="cta-panel shell reveal"><p class="eyebrow">Compare With A Clear Standard</p><h2>지역 이름보다 학생의 현재 학습 상태를 먼저 확인하세요.</h2><p class="lead">각 동네 페이지에서 학습 안내, 수업 가능 학년, 학교 자료와 상담 전 확인 기준을 살펴볼 수 있습니다.</p><div class="actions"><a class="btn btn-primary" href="/상담문의/">상담 준비하기</a><a class="btn btn-blue" href="/과목별학원/">다른 카테고리 보기</a></div></div></section>
    </main>{site_footer()}<script src="../../assets/subject-directory.js" defer></script></body></html>'''


def subject_hub() -> str:
    canonical = absolute_url("과목별학원")
    title = f"과목별학원 | {SITE_NAME}"
    description = "초등학생부터 고등학생까지 영어·수학의 지역별 학습 안내를 학년과 과목, 학생 상황에 따라 찾아볼 수 있도록 정리했습니다."
    items = [
        {"@type": "ListItem", "position": index, "name": config["label"], "url": absolute_url("과목별학원", config["slug"])}
        for index, config in enumerate(CATEGORIES, 1)
    ]
    graph = [
        {"@type": "CollectionPage", "@id": canonical + "#webpage", "url": canonical, "name": title, "description": description, "isPartOf": {"@id": DOMAIN + "/#website"}, "dateModified": TODAY, "inLanguage": "ko-KR"},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": canonical}]},
        {"@type": "ItemList", "name": "과목별학원 카테고리", "numberOfItems": len(items), "itemListElement": items},
    ]
    cards = "".join(
        f'<a class="academy-category-card reveal" href="/과목별학원/{esc(config["slug"])}/"><span class="tag">{esc(config["english"])}</span><h2>{esc(config["label"])}</h2><p>{esc(config["summary"])}</p><span class="arrow" aria-hidden="true">→</span></a>'
        for config in CATEGORIES
    )
    head = page_head(title=title, description=description, canonical=canonical, asset_prefix="../", image_url=SHARE_IMAGE_URL, graph=graph, page_type="website")
    return f'''<!doctype html><html lang="ko">{head}<body class="general-page subject-page academy-page">{site_header("subjects")}<main id="main">
      <header class="academy-hero reveal"><div class="academy-hero-copy"><nav class="academy-breadcrumb" aria-label="현재 위치"><a href="/">홈</a><span aria-hidden="true">›</span><span aria-current="page">과목별학원</span></nav><p class="eyebrow">Subject &amp; Grade Academy Guide</p><h1>과목과 학년을 먼저 고르고,<br>동네별 안내를 확인하세요.</h1><p class="lead">초등·중등·고등 영어와 수학은 현재 단원, 학교 자료, 오답 유형에 따라 확인할 관리 기준이 달라집니다. 필요한 카테고리를 선택하면 371개 동네별 학습 안내와 확인된 센터 정보를 살펴볼 수 있습니다.</p></div><aside class="academy-hero-aside"><strong>{len(CATEGORIES)} × 371</strong><span>{len(CATEGORIES)}개 카테고리 · {len(CATEGORIES) * 371:,}개 지역별 학습 안내</span></aside></header>
      <section class="section"><div class="section-head reveal"><p class="eyebrow blue">Choose A Learning Track</p><h2>현재 학년과 과목에 맞는 안내</h2><p class="lead">학년과 과목별로 확인할 기준을 나누고, 동네 페이지는 지역별 학습 안내와 확인된 센터 자료를 기반으로 구성했습니다.</p></div><div class="academy-category-grid">{cards}</div></section>
      <section class="process-band"><div class="section"><div class="process-intro reveal"><p class="eyebrow">How To Use</p><h2>페이지를 확인하는 순서</h2><p class="lead">광고 문구보다 학생에게 적용할 수 있는 정보가 있는지 차례로 확인하세요.</p></div><div class="process-list"><article class="process-item reveal"><div><h3>학년·과목 선택</h3><p>초등학생·중학생·고등학생 가운데 현재 학년을 고른 뒤 영어와 수학 중 우선 관리가 필요한 과목을 확인합니다.</p></div></article><article class="process-item reveal"><div><h3>동네·센터 정보 확인</h3><p>지역 검색을 사용해 주소, 센터 전체 수업 가능 학년, 학교와 교습비 안내 자료를 확인합니다.</p></div></article><article class="process-item reveal"><div><h3>학습 안내와 FAQ 비교</h3><p>학생 상황, 학교 학습, 과제·오답 관리 기준과 상담 질문을 읽어봅니다.</p></div></article><article class="process-item reveal"><div><h3>상담 전 우선순위 정리</h3><p>최근 학습 결과와 어려운 단원을 준비해 먼저 해결할 문제를 정합니다.</p></div></article></div></div></section>
      <section class="cta-section"><div class="cta-panel shell reveal"><p class="eyebrow">Start With The Student</p><h2>카테고리를 고른 뒤에는 학생의 현재 기록을 함께 보세요.</h2><p class="lead">같은 동네와 학년이어도 필요한 수업 순서는 다를 수 있습니다. 최근 자료를 기준으로 상담의 첫 질문을 정리해보세요.</p><div class="actions"><a class="btn btn-primary" href="/상담문의/">상담 준비하기</a><a class="btn btn-blue" href="/학습가이드/">학습가이드 보기</a></div></div></section>
    </main>{site_footer()}<script src="../assets/subject-directory.js" defer></script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description="학습관리학원 과목별 지역 페이지 생성")
    parser.add_argument(
        "--category",
        action="append",
        choices=[config["slug"] for config in CATEGORIES],
        help="지정한 카테고리만 다시 생성합니다. 여러 번 지정할 수 있습니다.",
    )
    args = parser.parse_args()
    selected_categories = [
        config for config in CATEGORIES
        if not args.category or config["slug"] in set(args.category)
    ]
    center_rows = load_csv("센터정보 정리.csv")
    map_rows = load_csv("이미지링크.csv")
    if len(center_rows) != 371 or len(map_rows) != 371:
        raise ValueError(f"Expected 371 data rows: centers={len(center_rows)} maps={len(map_rows)}")
    center_by_locality = {row["근처 수업가능 동네"]: row for row in center_rows}
    center_by_compact = {compact_locality(key): key for key in center_by_locality}
    map_by_locality = {row["제목"]: row["지도"] for row in map_rows}
    if set(center_by_locality) != set(map_by_locality):
        raise ValueError("Center and map locality sets differ")
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    (TARGET_ROOT / "index.html").write_text(clean_html(subject_hub()), encoding="utf-8")
    generated = 0
    category_report = {}
    all_titles: set[str] = set()
    for config in selected_categories:
        zip_path = SOURCE_DIR / config["zip"]
        if not zip_path.exists():
            raise FileNotFoundError(zip_path)
        category_dir = TARGET_ROOT / config["slug"]
        if category_dir.exists():
            shutil.rmtree(category_dir)
        category_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(zip_path) as archive:
            names = sorted(name for name in archive.namelist() if name.lower().endswith(".txt"))
            if len(names) != 371:
                raise ValueError(f"{config['zip']}: expected 371 TXT, got {len(names)}")
            seen_localities = set()
            hub_row_by_center: dict[str, dict[str, str]] = {}
            meta_lengths = []
            for name in names:
                raw = archive.read(name).decode("utf-8-sig")
                sections = parse_sections(raw)
                required = ["페이지타이틀", "메타설명", "본문", "FAQ", "학부모후기", "JSON-LD 요약"]
                if list(sections) != required:
                    raise ValueError(f"{name}: section mismatch: {list(sections)}")
                title = normalize(sections["페이지타이틀"])
                suffix = " " + config["label"]
                if not title.endswith(suffix):
                    raise ValueError(f"{name}: title/category mismatch: {title}")
                locality = title[: -len(suffix)].strip()
                compact = compact_locality(locality)
                center_locality = (
                    locality
                    if locality in center_by_locality
                    else center_by_compact.get(compact)
                )
                if not center_locality:
                    alias = SPECIAL_LOCALITY_ALIASES.get(compact)
                    if alias in center_by_locality:
                        center_locality = alias
                if not center_locality or center_locality not in center_by_locality:
                    raise ValueError(f"{name}: no center mapping for {locality}")
                if center_locality in seen_localities:
                    raise ValueError(f"{name}: duplicate locality {locality} -> {center_locality}")
                seen_localities.add(center_locality)
                if title in all_titles:
                    raise ValueError(f"Duplicate title across categories: {title}")
                all_titles.add(title)
                row = center_by_locality[center_locality]
                slug = center_locality
                map_file = resolve_map_file(map_by_locality[center_locality], row["동 영어"])
                target = category_dir / slug
                target.mkdir(parents=True, exist_ok=True)
                page = detail_page(config=config, sections=sections, locality=locality, slug=slug, row=row, map_file=map_file)
                (target / "index.html").write_text(clean_html(page), encoding="utf-8")
                hub_row = dict(row)
                hub_row["_subject_slug"] = slug
                hub_row["_subject_locality"] = locality
                hub_row_by_center[center_locality] = hub_row
                meta = compact_meta(sections["메타설명"], title, row, config)
                meta_lengths.append(len(meta))
                generated += 1
            if seen_localities != set(center_by_locality):
                raise ValueError(f"{config['zip']}: locality set mismatch")
        hub_rows = [hub_row_by_center[row["근처 수업가능 동네"]] for row in center_rows]
        (category_dir / "index.html").write_text(clean_html(category_hub(hub_rows, config)), encoding="utf-8")
        category_report[config["slug"]] = {"pages": len(seen_localities), "meta_min": min(meta_lengths), "meta_max": max(meta_lengths)}
    # sitemap/RSS/llms are owned by this site's existing discovery generators.
    # Only count the current HTML inventory here; the build pipeline refreshes
    # the public discovery files after every page and navigation update.
    sitemap_count = sum(1 for _ in ROOT.rglob("index.html"))
    report = {
        "generated_detail_pages": generated,
        "category_hubs": len(selected_categories),
        "sitemap_urls": sitemap_count,
        "categories": category_report,
        "date": TODAY,
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "subject_generation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
