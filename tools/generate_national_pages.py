from __future__ import annotations

import csv
import json
import hashlib
import random
import re
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import quote


SITE_NAME = "학습관리학원"
BASE_URL = "https://xn--zb0b93vh4ggmeqzwda.com"
PHONE_DISPLAY = "010-6839-8283"
PHONE_TEL = "01068398283"
PHONE_SCHEMA = "+82-10-6839-8283"
PUBLISHED = "2026-07-01"
REGION_ORDER = ["서울", "경기", "인천", "대전", "충청", "대구", "울산", "부산", "경상", "광주", "전라", "강원", "제주", "기타"]

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT.parent / "새 홈페이지6" / "전국센터"
DEST_ROOT = ROOT / "전국학원"
REFERENCE_ROOT = ROOT.parent / "참고자료"
COMMON_ROOT = REFERENCE_ROOT / "공통자료"
FAQ_SOURCE = COMMON_ROOT / "FAQ.txt"
REVIEW_SOURCE = COMMON_ROOT / "학부모 후기.txt"
TARGET_SCHOOL_SOURCE = COMMON_ROOT / "타깃학교.csv"
EDUCATIONAL_ORG_SOURCE = COMMON_ROOT / "EducationalOrganization.csv"
REPRESENTATIVE_IMAGE_SOURCE = COMMON_ROOT / "대표 이미지 url.csv"
CHILD_SLUGS = ["영어수학학원", "수학영어학원", "국영수학원", "소수정예학원"]


@dataclass
class Center:
    name: str
    title: str
    region: str
    locality: str
    map_file: str
    is_seoul: bool
    position: int

    @property
    def url(self) -> str:
        return f"/전국학원/{self.name}/"

    @property
    def main_image_file(self) -> str:
        return "seoul6839.jpg" if self.is_seoul else "local6839.jpg"

    @property
    def area_phrase(self) -> str:
        parts = [p for p in [self.region, self.locality, self.name] if p]
        return " ".join(parts)


def first_script_json(text: str) -> dict:
    match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', text)
    if not match:
        return {}
    return json.loads(match.group(1))


def as_type_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def stable_rng(key: str) -> random.Random:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def stable_sample(items: list, count: int, key: str) -> list:
    rng = stable_rng(key)
    if not items:
        return []
    if len(items) >= count:
        return rng.sample(items, count)
    picked = list(items)
    while len(picked) < count:
        picked.append(rng.choice(items))
    return picked


def load_representative_image_urls() -> list[str]:
    if not REPRESENTATIVE_IMAGE_SOURCE.exists():
        raise SystemExit(f"representative image source missing: {REPRESENTATIVE_IMAGE_SOURCE}")

    urls: list[str] = []
    seen: set[str] = set()
    with REPRESENTATIVE_IMAGE_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            for cell in row:
                match = re.search(r'src=["\']([^"\']+)["\']', cell or "", re.I)
                if not match:
                    continue
                url = match.group(1).strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                urls.append(url)

    if not urls:
        raise SystemExit(f"representative image urls not found: {REPRESENTATIVE_IMAGE_SOURCE}")
    return urls


REPRESENTATIVE_IMAGE_URLS = load_representative_image_urls()


def representative_image_url(key: str) -> str:
    rng = stable_rng(f"representative-image::{key}")
    return REPRESENTATIVE_IMAGE_URLS[rng.randrange(len(REPRESENTATIVE_IMAGE_URLS))]


def hidden_representative_image(title: str, src: str) -> str:
    return f'<img src="{escape(src)}" alt="{escape(title)} {SITE_NAME} 대표" style="display:none;">'


def load_faq_pool() -> list[tuple[str, str]]:
    if not FAQ_SOURCE.exists():
        raise SystemExit(f"FAQ source missing: {FAQ_SOURCE}")
    text = FAQ_SOURCE.read_text(encoding="utf-8-sig")
    pairs: list[tuple[str, str]] = []
    question = ""
    answer_parts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("질문:"):
            if question and answer_parts:
                pairs.append((question, " ".join(answer_parts)))
            question = line.split(":", 1)[1].strip()
            answer_parts = []
        elif line.startswith("답변:"):
            answer_parts.append(line.split(":", 1)[1].strip())
        elif question:
            answer_parts.append(line)
    if question and answer_parts:
        pairs.append((question, " ".join(answer_parts)))
    if len(pairs) < 5:
        raise SystemExit(f"FAQ source needs at least 5 pairs, got {len(pairs)}")
    return pairs


def load_review_pool() -> list[str]:
    if not REVIEW_SOURCE.exists():
        raise SystemExit(f"review source missing: {REVIEW_SOURCE}")
    reviews = [line.strip().rstrip(".") for line in REVIEW_SOURCE.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(reviews) < 6:
        raise SystemExit(f"review source needs at least 6 lines, got {len(reviews)}")
    return reviews


def split_school_names(value: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in re.split(r"[,，/]", value or ""):
        name = item.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def normalize_school_key(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def load_target_schools() -> dict[str, dict[str, object]]:
    if not TARGET_SCHOOL_SOURCE.exists():
        return {}

    with TARGET_SCHOOL_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        def find_field(*keywords: str) -> str:
            for field in fieldnames:
                compact = field.replace("\n", "").replace(" ", "")
                if all(keyword in compact for keyword in keywords):
                    return field
            return ""

        town_key = find_field("동네")
        region_key = find_field("지역")
        locality_key = find_field("시or구") or find_field("시", "구")
        center_key = find_field("센터명")
        elementary_key = find_field("타깃학교", "초")
        middle_key = find_field("타깃학교", "중")
        high_key = find_field("타깃학교", "고")

        schools: dict[str, dict[str, object]] = {}
        for row in reader:
            town = (row.get(town_key) or "").strip()
            if not town:
                continue
            info = {
                "town": town,
                "town_compact": normalize_school_key(town),
                "region": (row.get(region_key) or "").strip(),
                "locality": (row.get(locality_key) or "").strip(),
                "center_name": (row.get(center_key) or "").strip(),
                "elementary": split_school_names(row.get(elementary_key) or ""),
                "middle": split_school_names(row.get(middle_key) or ""),
                "high": split_school_names(row.get(high_key) or ""),
            }
            schools[town] = info
            schools[normalize_school_key(town)] = info
    return schools


def load_educational_orgs() -> dict[str, dict[str, str]]:
    if not EDUCATIONAL_ORG_SOURCE.exists():
        return {}

    with EDUCATIONAL_ORG_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        def find_field(*keywords: str) -> str:
            for field in fieldnames:
                compact = field.replace("\n", "").replace(" ", "")
                if all(keyword in compact for keyword in keywords):
                    return field
            return ""

        center_key = find_field("센터명") or find_field("실제", "센터명")
        address_key = find_field("주소")
        phone_key = find_field("전화")
        hours_key = find_field("운영")
        area_key = find_field("서비스", "지역") or find_field("제공", "지역")
        homepage_key = find_field("홈페이지")

        orgs: dict[str, dict[str, str]] = {}
        for row in reader:
            area = (row.get(area_key) or "").strip()
            if not area:
                continue
            info = {
                "center_name": (row.get(center_key) or "").strip(),
                "address": (row.get(address_key) or "").strip(),
                "phone": (row.get(phone_key) or "").strip(),
                "hours": (row.get(hours_key) or "").strip(),
                "area": area,
                "area_compact": normalize_school_key(area),
                "homepage": (row.get(homepage_key) or "").strip(),
            }
            orgs[area] = info
            orgs[normalize_school_key(area)] = info
    return orgs


FAQ_POOL = load_faq_pool()
REVIEW_POOL = load_review_pool()
TARGET_SCHOOLS = load_target_schools()
EDUCATIONAL_ORGS = load_educational_orgs()


def personalize_faq_question(center: Center, question: str, index: int) -> str:
    if center.title in question or center.name in question:
        return question
    if index == 0:
        if question.startswith("학원 "):
            return f"{center.title} {question.removeprefix('학원 ')}"
        if question.startswith("상담"):
            return f"{center.title} {question}"
        return f"{center.title}에서는 {question}"
    if index == 1:
        if question.startswith("학원 "):
            return f"{center.title} 상담 전 {question.removeprefix('학원 ')}"
        if question.startswith("수업"):
            return f"{center.title} {question}"
        if question.startswith("상담"):
            return f"{center.title} {question}"
        return f"{center.title}을 알아볼 때 {question}"
    return question


def personalize_faq_answer(center: Center, answer: str, index: int) -> str:
    if index == 0:
        return f"{answer} {center.title} 상담에서는 학생의 학교 진도와 현재 학습 습관을 함께 확인해 안내합니다."
    if index == 1:
        return f"{answer} {center.name} 학생의 상황에 따라 세부 안내는 상담 시 조정될 수 있습니다."
    return answer


def center_faqs(center: Center) -> list[tuple[str, str]]:
    selected = stable_sample(FAQ_POOL, 5, f"faq::{center.name}::{center.region}::{center.locality}")
    return [
        (
            personalize_faq_question(center, question, idx),
            personalize_faq_answer(center, answer, idx),
        )
        for idx, (question, answer) in enumerate(selected)
    ]


def personalize_review(center: Center, review: str, index: int) -> str:
    review = review.rstrip(".")
    if index == 0:
        return f"{center.title} 상담을 받아보니 {review}."
    if index == 1:
        return f"{center.name} 학습관리 과정에서 {review}."
    return f"{review}."


def center_reviews(center: Center) -> list[dict[str, str]]:
    selected = stable_sample(REVIEW_POOL, 6, f"review::{center.name}::{center.region}::{center.locality}")
    ratings = ["5", "5", "5", "5", "5", "4"]
    return [
        {
            "body": personalize_review(center, review, idx),
            "rating": ratings[idx],
            "stars": "★★★★★" if ratings[idx] == "5" else "★★★★☆",
        }
        for idx, review in enumerate(selected)
    ]


def child_title(center: Center, slug: str) -> str:
    if slug in {"영어수학학원", "수학영어학원", "국영수학원"}:
        return f"{center.name} {slug}"
    return f"{center.name} {slug}"


def child_url(center: Center, slug: str) -> str:
    return f"{center.url}{slug}/"


def child_topic_label(slug: str) -> str:
    if slug == "영어수학학원":
        return "영어·수학"
    if slug == "수학영어학원":
        return "수학·영어"
    if slug == "국영수학원":
        return "국어·영어·수학"
    if slug == "소수정예학원":
        return "소수정예 관리"
    return slug


def child_profile(slug: str) -> dict[str, str]:
    if slug == "소수정예학원":
        return {
            "pair": "소수정예",
            "page_type": "소수정예학원",
            "topic": "소수정예 학습관리",
            "primary": "개별 진단",
            "secondary": "밀착 피드백",
            "primary_with_topic": "개별 진단은",
            "secondary_with_topic": "밀착 피드백은",
            "subject_pair": "소수정예 학습관리",
            "subject_pair_object": "소수정예 학습관리를",
            "subject_kind": "개별 관리",
            "subject_count_label": "소수정예",
            "primary_scope": "현재 단원, 학교 진도, 반복 오답, 학습 습관 진단",
            "secondary_scope": "수업 중 이해 확인, 플래너 점검, 과제 피드백, 재학습 연결",
            "primary_scope_object": "현재 단원, 학교 진도, 반복 오답, 학습 습관 진단을",
            "secondary_scope_object": "수업 중 이해 확인, 플래너 점검, 과제 피드백, 재학습 연결을",
            "guide_kicker": "Small Group Coaching",
            "guide_heading": "인원이 적은 수업일수록 학생별 막힘을 더 빨리 발견해야 합니다.",
            "parent_question": "우리 아이가 큰 반보다 소수정예 환경이 맞는지",
            "main_reason": "소수정예 수업은 단순히 인원만 적은 수업이 아니라, 학생이 어디서 멈추는지 확인하고 바로 질문·풀이·오답 재학습으로 연결하는 관리 방식이 중요합니다.",
            "priority": "학생의 현재 단원과 학교 진도, 반복되는 오답 유형을 먼저 확인한 뒤 수업 중 피드백과 과제 점검이 이어지는지 함께 봅니다.",
            "summary_primary_title": "학생별 진단",
            "summary_primary_text": "현재 단원, 학교 진도, 최근 시험지, 과제 수행 습관을 기준으로 학생별 출발점을 확인합니다.",
            "summary_secondary_title": "밀착 피드백",
            "summary_secondary_text": "수업 중 이해 여부, 질문 빈도, 오답 재풀이, 플래너 실행 흐름을 짧은 주기로 점검합니다.",
            "recommended_1_title": "대형 수업에서 질문을 잘 못 하고 넘어가는 학생",
            "recommended_1_text": "모르는 부분을 숨기지 않도록 수업 중 확인 질문과 짧은 피드백을 반복해 학습 공백을 줄입니다.",
            "recommended_2_title": "혼자 공부하면 계획이 자주 흐트러지는 학생",
            "recommended_2_text": "주간 플래너와 과제 완료 여부를 함께 확인해 공부량보다 실행 흐름을 먼저 안정시킵니다.",
            "answer_question": "소수정예학원을 고를 때 무엇을 먼저 봐야 할까요?",
            "answer_body": "소수정예학원은 인원이 적다는 점만으로 판단하기보다, 학생의 이해도를 수업 중에 어떻게 확인하는지, 과제와 오답 피드백이 다음 수업으로 어떻게 이어지는지 봐야 합니다. 상담에서는 현재 단원, 학교 진도, 최근 시험지와 반복 오답을 함께 확인해 학생에게 맞는 관리 밀도를 정리합니다.",
            "check_1": "최근 시험지, 현재 교재, 학교 진도, 반복해서 틀리는 문제 유형을 준비해 주세요.",
            "check_2": "수업 중 질문을 어려워하는지, 과제를 미루는지, 플래너 실행이 끊기는지 알려주세요.",
            "review_heading_suffix": "소수정예 학부모 상담 후기",
            "related_heading_suffix": "주변 소수정예학원도 함께 보기",
            "internal_desc": "같은 시군구와 가까운 지역의 소수정예 상담 페이지로 자연스럽게 이동할 수 있게 정리했습니다.",
            "cta_heading": "우리 아이에게 필요한 관리 밀도를 먼저 확인해보세요.",
            "cta_body": "소수정예 수업은 학생의 성향과 학습 습관을 세밀하게 보는 데서 강점이 생깁니다. 최근 시험지, 현재 교재, 학교 진도, 과제 습관, 질문 태도를 알려주시면 상담에서 더 현실적인 수업 방향을 잡을 수 있습니다.",
        }
    if slug == "국영수학원":
        return {
            "pair": "국영수",
            "page_type": "국영수학원",
            "topic": "국어·영어·수학",
            "primary": "국어",
            "secondary": "영어·수학",
            "primary_with_topic": "국어는",
            "secondary_with_topic": "영어·수학은",
            "subject_pair": "국어·영어·수학",
            "subject_pair_object": "국어·영어·수학을",
            "subject_kind": "세 과목",
            "subject_count_label": "3과목",
            "primary_scope": "독해력, 어휘 이해, 서술형 표현, 학교 지문 정리",
            "secondary_scope": "영어 누적 학습과 수학 개념·유형·오답 관리",
            "primary_scope_object": "독해력, 어휘 이해, 서술형 표현, 학교 지문 정리를",
            "secondary_scope_object": "영어 누적 학습과 수학 개념·유형·오답 관리를",
            "guide_kicker": "Korean English Math Guide",
            "guide_heading": "국어로 읽고 이해하는 힘까지 함께 봐야 세 과목 관리가 선명해집니다.",
            "parent_question": "국어까지 함께 봐야 하는지, 영어와 수학만 관리해도 되는지",
            "main_reason": "국어는 지문을 읽고 조건을 파악하는 힘이 중요하고, 영어는 어휘·문법·독해가 누적되어야 하며, 수학은 개념을 문제에 적용하는 과정에서 오답 원인을 잡아야 합니다.",
            "priority": "국어 독해와 서술형 표현을 먼저 확인하고, 영어의 누적 학습과 수학의 오답 원인을 함께 점검합니다.",
            "summary_primary_title": "국어 독해·서술형 진단",
            "summary_primary_text": "지문 이해, 핵심어 찾기, 문장 표현, 서술형 답안 작성 흐름을 확인합니다.",
            "summary_secondary_title": "영어·수학 병행 점검",
            "summary_secondary_text": "영어 어휘·문법·독해 루틴과 수학 개념·유형·오답 관리가 이어지는지 함께 봅니다.",
            "recommended_1_title": "국어 지문을 읽어도 핵심을 잘 못 잡는 학생",
            "recommended_1_text": "문제 조건, 핵심어, 문단 흐름을 읽는 방법부터 확인해 서술형 답안으로 연결합니다.",
            "recommended_2_title": "영어와 수학도 함께 흔들리는 학생",
            "recommended_2_text": "영어 누적 학습과 수학 오답 관리가 주간 계획 안에서 끊기지 않는지 점검합니다.",
            "answer_question": "국영수학원을 고를 때 무엇을 먼저 봐야 할까요?",
            "answer_body": "국어는 모든 과목의 문제를 읽고 이해하는 바탕이 되고, 영어는 누적이 끊기면 독해와 서술형에서 흔들리며, 수학은 개념을 문제에 적용하는 과정에서 실수가 반복될 수 있습니다. 그래서 상담에서는 국어 독해력과 표현력을 확인한 뒤 영어 루틴, 수학 오답 원인을 함께 정리합니다.",
            "check_1": "국어 최근 지문, 서술형 답안, 독해에서 막히는 유형을 정리해 주세요.",
            "check_2": "영어 단어장·문법 단원과 수학 오답노트·현재 단원을 함께 확인해 주세요.",
            "review_heading_suffix": "국영수 학부모 상담 후기",
            "related_heading_suffix": "주변 국영수학원도 함께 보기",
            "internal_desc": "같은 시군구와 가까운 지역의 국영수 상담 페이지로 자연스럽게 이동할 수 있게 정리했습니다.",
            "cta_heading": "국어·영어·수학 중 어디서 먼저 막히는지 정리해보세요.",
            "cta_body": "국어·영어·수학은 각각 공부 방식이 다르지만, 결국 읽고 이해하고 적용하는 흐름으로 연결됩니다. 최근 시험지, 현재 교재, 학교 진도, 반복되는 오답을 알려주시면 상담에서 더 구체적인 학습 순서를 잡을 수 있습니다.",
        }
    if slug == "수학영어학원":
        return {
            "pair": "수학영어",
            "page_type": "수학영어학원",
            "topic": "수학·영어",
            "primary": "수학",
            "secondary": "영어",
            "primary_with_topic": "수학은",
            "secondary_with_topic": "영어는",
            "subject_pair": "수학과 영어",
            "subject_pair_object": "수학과 영어를",
            "subject_kind": "두 과목",
            "subject_count_label": "두 과목",
            "primary_scope": "개념 이해, 유형 적용, 계산 정확도, 오답 재풀이",
            "secondary_scope": "어휘 누적, 문법 정리, 독해 흐름, 학교 본문 복습",
            "primary_scope_object": "개념 이해, 유형 적용, 계산 정확도, 오답 재풀이를",
            "secondary_scope_object": "어휘 누적, 문법 정리, 독해 흐름, 학교 본문 복습을",
            "guide_kicker": "Math & English Guide",
            "guide_heading": "수학을 먼저 잡고 영어를 함께 관리해야 흐름이 보입니다.",
            "parent_question": "수학이 먼저인지, 영어도 함께 봐야 하는지",
            "main_reason": "수학은 개념을 배운 뒤 문제에 적용하는 힘이 중요하고, 영어는 어휘·문법·독해가 누적되어야 학교 시험에서 흔들리지 않습니다.",
            "priority": "수학의 개념 공백과 오답 원인을 먼저 확인한 뒤 영어의 누적 학습 상태를 함께 점검합니다.",
            "summary_primary_title": "수학 우선 진단",
            "summary_primary_text": "현재 단원, 개념 공백, 계산 실수, 오답 재풀이 습관을 먼저 확인합니다.",
            "summary_secondary_title": "영어 병행 점검",
            "summary_secondary_text": "어휘, 문법, 독해, 학교 본문 복습이 꾸준히 이어지는지 함께 봅니다.",
            "recommended_1_title": "수학 개념은 알지만 문제 적용이 약한 학생",
            "recommended_1_text": "개념 설명 후 바로 유형으로 연결되는지, 오답 원인을 스스로 말할 수 있는지 점검합니다.",
            "recommended_2_title": "영어 공부도 미루다 시험 직전에 몰리는 학생",
            "recommended_2_text": "단어·문법·독해 복습이 주간 계획 안에서 꾸준히 이어지는지 확인합니다.",
            "answer_question": "수학영어학원을 고를 때 무엇을 먼저 봐야 할까요?",
            "answer_body": "수학은 한 단원의 공백이 다음 단원까지 이어지기 쉽고, 영어는 누적이 끊기면 독해와 서술형에서 흔들릴 수 있습니다. 그래서 상담에서는 수학의 현재 단원과 오답 원인을 먼저 보고, 영어의 어휘·문법·독해 루틴이 실제로 이어지는지 함께 확인합니다.",
            "check_1": "수학 현재 단원, 오답노트, 계산 실수가 반복되는 유형을 정리해 주세요.",
            "check_2": "영어 최근 단어장, 문법 단원, 독해 교재를 확인해 주세요.",
            "review_heading_suffix": "수학영어 학부모 상담 후기",
            "related_heading_suffix": "주변 수학영어학원도 함께 보기",
            "internal_desc": "같은 시군구와 가까운 지역의 수학영어 상담 페이지로 자연스럽게 이동할 수 있게 정리했습니다.",
            "cta_heading": "수학과 영어 중 어디서 먼저 막히는지 정리해보세요.",
            "cta_body": "수학과 영어는 공부 방식이 다르지만, 둘 다 현재 위치를 정확히 보는 것이 먼저입니다. 최근 시험지, 현재 교재, 학교 진도, 반복되는 오답을 알려주시면 상담에서 더 구체적인 학습 순서를 잡을 수 있습니다.",
        }
    return {
        "pair": "영어수학",
        "page_type": "영어수학학원",
        "topic": "영어·수학",
        "primary": "영어",
        "secondary": "수학",
        "primary_with_topic": "영어는",
        "secondary_with_topic": "수학은",
        "subject_pair": "영어와 수학",
        "subject_pair_object": "영어와 수학을",
        "subject_kind": "두 과목",
        "subject_count_label": "두 과목",
        "primary_scope": "어휘 누적, 문법 정리, 독해 흐름, 학교 본문 복습",
        "secondary_scope": "개념 이해, 유형 적용, 계산 정확도, 오답 재풀이",
        "primary_scope_object": "어휘 누적, 문법 정리, 독해 흐름, 학교 본문 복습을",
        "secondary_scope_object": "개념 이해, 유형 적용, 계산 정확도, 오답 재풀이를",
        "guide_kicker": "English & Math Guide",
        "guide_heading": "두 과목을 따로가 아니라 흐름으로 봐야 합니다.",
        "parent_question": "영어가 먼저인지, 수학이 먼저인지",
        "main_reason": "영어는 어휘 누적, 문법 정리, 독해 속도, 학교 지문 복습이 연결되어야 하고, 수학은 개념 이해, 유형 훈련, 계산 실수, 오답 재풀이가 끊기지 않아야 합니다.",
        "priority": "두 과목의 현재 위치를 함께 확인해 우선순위를 정리합니다.",
        "summary_primary_title": "영어 진단",
        "summary_primary_text": "어휘, 문법, 독해, 학교 본문 복습 중 어디서 막히는지 먼저 확인합니다.",
        "summary_secondary_title": "수학 진단",
        "summary_secondary_text": "개념 이해, 유형 적용, 계산 정확도, 오답 재풀이 습관을 나누어 봅니다.",
        "recommended_1_title": "영어 단어는 외우지만 독해에서 자주 막히는 학생",
        "recommended_1_text": "어휘, 문법, 문장 해석, 지문 복습이 이어지는지 확인합니다.",
        "recommended_2_title": "수학 개념은 들었지만 문제 적용이 약한 학생",
        "recommended_2_text": "개념 설명 후 바로 유형으로 연결되는지, 오답 원인을 스스로 말할 수 있는지 점검합니다.",
        "answer_question": "영어수학학원을 고를 때 무엇을 먼저 봐야 할까요?",
        "answer_body": "영어는 누적 학습이 끊기면 독해와 서술형에서 흔들리고, 수학은 개념을 들은 뒤 문제에 적용하는 단계에서 실수가 반복될 수 있습니다. 그래서 상담에서는 현재 단원, 학교 진도, 오답 원인, 플래너 실행 여부를 함께 확인해 과목별 우선순위를 정리합니다.",
        "check_1": "영어 최근 단어장, 문법 단원, 독해 교재를 확인해 주세요.",
        "check_2": "수학 현재 단원, 오답노트, 계산 실수가 반복되는 유형을 정리해 주세요.",
        "review_heading_suffix": "영어수학 학부모 상담 후기",
        "related_heading_suffix": "주변 영어수학학원도 함께 보기",
        "internal_desc": "같은 시군구와 가까운 지역의 영어수학 상담 페이지로 자연스럽게 이동할 수 있게 정리했습니다.",
        "cta_heading": "영어와 수학 중 어디서 막히는지부터 정리해보세요.",
        "cta_body": "영어와 수학은 공부 방식이 다르지만, 둘 다 현재 위치를 정확히 보는 것이 먼저입니다. 최근 시험지, 현재 교재, 학교 진도, 반복되는 오답을 알려주시면 상담에서 더 구체적인 학습 순서를 잡을 수 있습니다.",
    }


def child_faqs(center: Center, slug: str) -> list[tuple[str, str]]:
    title = child_title(center, slug)
    profile = child_profile(slug)
    topic = profile["topic"]
    selected = stable_sample(FAQ_POOL, 5, f"childfaq::{slug}::{center.name}::{center.region}::{center.locality}")
    faqs: list[tuple[str, str]] = []
    for idx, (question, answer) in enumerate(selected):
        if idx == 0:
            q = f"{title} 상담은 어떤 순서로 진행되나요?"
            a = f"{answer} {title} 상담에서는 학생의 현재 {profile['subject_pair']} 학습 상태, 학교 진도, 과제 습관, 반복 오답을 함께 확인해 필요한 관리 순서를 안내합니다."
        elif idx == 1:
            q = f"{title}에서는 {profile['subject_pair_object']} 함께 관리하나요?"
            a = f"{answer} {profile['primary_with_topic']} {profile['primary_scope_object']}, {profile['secondary_with_topic']} {profile['secondary_scope_object']} 나누어 점검합니다. {center.name} 학생의 학년과 학교 진도에 맞춰 {profile['subject_kind']}의 우선순위를 조정합니다."
        elif idx == 2:
            q = f"{center.name} 학생이 {topic} 수업을 시작하기 전 준비할 것은 무엇인가요?"
            a = f"{answer} 최근 시험지, 현재 교재, 학교 진도표, 자주 틀리는 문제를 가져오면 {title} 상담에서 {profile['subject_pair']}의 학습 방향을 더 정확히 잡을 수 있습니다."
        else:
            base_q = question
            if base_q.startswith("학원 "):
                base_q = base_q.removeprefix("학원 ")
            q = base_q if title in base_q else f"{center.name}에서 {base_q}"
            a = f"{answer} 세부 운영은 학생의 학년, 과목별 수준, 상담 시점의 학교 진도에 맞춰 조정될 수 있습니다."
        faqs.append((q, a))
    return faqs


def child_reviews(center: Center, slug: str) -> list[dict[str, str]]:
    title = child_title(center, slug)
    profile = child_profile(slug)
    topic = profile["topic"]
    selected = stable_sample(REVIEW_POOL, 6, f"childreview::{slug}::{center.name}::{center.region}::{center.locality}")
    ratings = ["5", "5", "5", "5", "5", "4"]
    reviews: list[dict[str, str]] = []
    for idx, review in enumerate(selected):
        body = review.rstrip(".")
        if idx == 0:
            body = f"{title} 상담 후 아이의 {topic} 공부 흐름을 어디서부터 잡아야 할지 알 수 있었습니다."
        elif idx == 1:
            body = f"{center.name}에서 {profile['subject_pair_object']} 함께 점검받으니 과목별 부족한 부분이 더 선명해졌습니다."
        else:
            body = f"{body} {topic} 학습 관리 과정에서도 도움이 되었습니다."
        body = body.rstrip(".")
        reviews.append(
            {
                "body": f"{body}.",
                "rating": ratings[idx],
                "stars": "★★★★★" if ratings[idx] == "5" else "★★★★☆",
            }
        )
    return reviews


def school_info_for(center: Center) -> dict[str, object]:
    center_key = normalize_school_key(center.name)
    direct = TARGET_SCHOOLS.get(center.name) or TARGET_SCHOOLS.get(center_key)
    if direct:
        return direct

    candidates: list[tuple[int, dict[str, object]]] = []
    seen: set[str] = set()
    for info in TARGET_SCHOOLS.values():
        town_compact = str(info.get("town_compact") or "")
        if not town_compact or town_compact in seen:
            continue
        seen.add(town_compact)
        if not (town_compact.endswith(center_key) or center_key.endswith(town_compact)):
            continue
        score = 1
        info_region = str(info.get("region") or "")
        info_locality = str(info.get("locality") or "")
        if info_region and info_region == center.region:
            score += 4
        if info_locality and center.locality and info_locality == center.locality:
            score += 5
        elif info_locality and center.locality and (info_locality in center.locality or center.locality in info_locality):
            score += 3
        candidates.append((score, info))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    return {}


def org_info_for(center: Center) -> dict[str, str]:
    center_key = normalize_school_key(center.name)
    direct = EDUCATIONAL_ORGS.get(center.name) or EDUCATIONAL_ORGS.get(center_key)
    if direct:
        return direct

    candidates: list[tuple[int, dict[str, str]]] = []
    seen: set[str] = set()
    locality_tokens = [
        center.locality,
        center.locality.replace("시", "").replace("군", "").replace("구", ""),
    ]
    for info in EDUCATIONAL_ORGS.values():
        area_compact = str(info.get("area_compact") or "")
        if not area_compact or area_compact in seen:
            continue
        seen.add(area_compact)
        if not (area_compact.endswith(center_key) or center_key.endswith(area_compact)):
            continue
        score = 1
        for token in locality_tokens:
            token = normalize_school_key(token)
            if token and token in area_compact:
                score += 5
        if center.region and normalize_school_key(center.region) in area_compact:
            score += 2
        candidates.append((score, info))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    return {}


def all_school_names(school_info: dict[str, object]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for key in ["elementary", "middle", "high"]:
        for name in school_info.get(key, []) or []:
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def school_mentions(school_info: dict[str, object]) -> list[dict[str, str]]:
    return [{"@type": "School", "name": name} for name in all_school_names(school_info)]


def school_item_list(center: Center, school_info: dict[str, object], page_title: str | None = None, page_url: str | None = None) -> dict[str, object] | None:
    title = page_title or center.title
    url = page_url or center.url
    names = all_school_names(school_info)
    if not names and school_info:
        names = [
            f"{center.name} 재학 학교 교과 진도 확인",
            "최근 시험 범위와 수행평가 일정 확인",
            "현재 교재와 반복 오답 유형 확인",
        ]
    if not names:
        return None
    return {
        "@type": "ItemList",
        "@id": f"{url}#target-schools",
        "name": f"{title} 학교별 상담 확인 항목",
        "itemListElement": [
            {"@type": "ListItem", "position": idx + 1, "name": name}
            for idx, name in enumerate(names)
        ],
    }


def render_school_group(label: str, schools: list[str]) -> str:
    if not schools:
        return ""
    chips = "\n".join(f'                  <span>{escape(school)}</span>' for school in schools)
    return f"""
              <article class="school-card">
                <strong>{escape(label)}</strong>
                <div class="school-chip-row">
{chips}
                </div>
              </article>"""


def render_school_section(center: Center, school_info: dict[str, object], page_title: str | None = None) -> str:
    if not school_info:
        return ""
    title = page_title or center.title

    center_name = str(school_info.get("center_name") or "").strip()
    center_line = (
        f'<b>{escape(center_name)}</b><span>{escape(center.area_phrase)} 학생 상담 시 학교별 진도와 시험 준비 흐름을 함께 확인합니다.</span>'
        if center_name
        else f'<b>{escape(title)}</b><span>{escape(center.area_phrase)} 학생 상담 시 학교별 진도와 시험 준비 흐름을 함께 확인합니다.</span>'
    )
    groups = "\n".join(
        item
        for item in [
            render_school_group("초등학교", school_info.get("elementary", []) or []),
            render_school_group("중학교", school_info.get("middle", []) or []),
            render_school_group("고등학교", school_info.get("high", []) or []),
        ]
        if item.strip()
    )
    if not groups:
        groups = f"""
              <article class="school-card school-card-wide">
                <strong>학교별 개별 확인</strong>
                <p>{escape(center.name)} 학생의 현재 재학 학교, 교과 진도, 시험 범위, 수행평가 일정을 상담 시 확인해 맞춤 학습 계획으로 연결합니다.</p>
              </article>"""
    return f"""
      <section class="section school-section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Target Schools</p>
              <h2>{escape(title)} 수업 가능 학교 안내</h2>
            </div>
            <p class="section-desc">{escape(center.name)} 주변 학생들이 상담 전 확인하기 쉽도록, 현재 정리된 학교 목록을 학년 단계별로 나누어 담았습니다.</p>
          </div>
          <div class="school-panel">
            <div class="school-meta-card">
              {center_line}
            </div>
            <div class="school-grid">
{groups}
            </div>
            <p class="school-note">학교별 교과 진도, 시험 범위, 수행평가 준비 상황은 학생마다 다르기 때문에 상담 시 현재 교재와 최근 평가지를 함께 확인하면 더 정확한 학습 계획을 세울 수 있습니다.</p>
          </div>
        </div>
      </section>"""


def school_context_sentence(center: Center, school_info: dict[str, object]) -> str:
    names = all_school_names(school_info)
    if names:
        listed = ", ".join(names[:6])
        suffix = " 등" if len(names) > 6 else ""
        return f"{listed}{suffix} 주변 학교의 진도와 시험 준비 흐름을 상담 때 함께 확인합니다."
    return f"{center.name} 학생의 재학 학교, 현재 교재, 시험 범위와 수행평가 일정을 상담 때 함께 확인합니다."


def render_story_sections(center: Center, school_info: dict[str, object]) -> str:
    school_context = school_context_sentence(center, school_info)
    return f"""
      <section class="section story-section">
        <div class="container">
          <div class="story-panel">
            <div class="story-copy">
              <p class="section-kicker">Parent Guide</p>
              <h2>{escape(center.name)}에서 학원을 찾기 전, 먼저 아이의 공부 흐름을 살펴보세요.</h2>
              <p>{escape(center.title)}을 알아보는 학부모님이라면 “진도가 빠른 학원이 좋은지”, “숙제를 많이 내주는 곳이 좋은지”, “우리 아이에게 맞는 관리가 가능한지”가 가장 궁금할 수 있습니다. 하지만 실제 상담에서는 속도보다 현재 아이가 어디에서 막히는지 확인하는 과정이 더 중요합니다.</p>
              <p>{escape(center.area_phrase)} 학생은 학교 진도, 과목별 자신감, 과제 습관, 시험 준비 시기가 모두 다를 수 있습니다. 그래서 상담에서는 성적표 한 장만 보고 판단하기보다 최근 교재, 오답 유형, 수업 태도, 플래너 실행 여부를 함께 살펴보며 학습 방향을 정리합니다.</p>
              <p>{escape(school_context)}</p>
            </div>
            <div class="story-quote-grid">
              <article class="story-quote">
                <span>01</span>
                <strong>진도를 못 따라가는 경우</strong>
                <p>이전 단원의 개념 공백을 먼저 찾고, 현재 학교 진도와 연결되는 부분부터 다시 정리합니다.</p>
              </article>
              <article class="story-quote">
                <span>02</span>
                <strong>공부 방법을 모르는 경우</strong>
                <p>무작정 오래 앉아 있는 방식이 아니라 과목별 복습 순서와 오답 정리 기준을 잡아줍니다.</p>
              </article>
              <article class="story-quote">
                <span>03</span>
                <strong>의욕이 자주 끊기는 경우</strong>
                <p>하루 계획을 작게 쪼개고 완료 경험을 쌓으면서 공부 루틴이 무너지지 않도록 확인합니다.</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Grade Coaching</p>
              <h2>{escape(center.title)} 학년별 수업 특징</h2>
            </div>
            <p class="section-desc">같은 {escape(center.name)} 학생이라도 초등·중등·고등 단계에 따라 필요한 관리가 달라집니다. 학년별 목표를 분리해서 봐야 상담 방향도 더 선명해집니다.</p>
          </div>
          <div class="grade-story-grid">
            <article class="grade-story-card">
              <em>Elementary</em>
              <strong>초등 과정</strong>
              <p>기본 개념, 연산 정확도, 어휘 이해, 문제를 끝까지 읽는 습관을 먼저 다집니다. 공부 시간이 길지 않아도 매일 이어지는 작은 루틴을 만드는 데 초점을 둡니다.</p>
            </article>
            <article class="grade-story-card">
              <em>Middle School</em>
              <strong>중등 과정</strong>
              <p>학교별 시험 범위와 교과서 흐름을 기준으로 내신 대비를 진행합니다. 단원별 오답 원인을 정리하고 서술형·응용 문제에서 실수가 반복되지 않도록 관리합니다.</p>
            </article>
            <article class="grade-story-card">
              <em>High School</em>
              <strong>고등 과정</strong>
              <p>내신과 모의고사 준비를 함께 보며, 부족한 개념과 시간 관리 문제를 나눠 점검합니다. 과목별 우선순위를 정해 시험 기간 계획이 흐트러지지 않도록 돕습니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container rec-story-panel">
          <div>
            <p class="section-kicker">Recommended</p>
            <h2>{escape(center.name)}에서 이런 학생이라면 상담을 권합니다.</h2>
          </div>
          <div class="rec-story-list">
            <p><b>개념은 아는 것 같은데 문제만 풀면 틀리는 학생</b><span>조건 해석, 풀이 순서, 계산 실수처럼 점수가 빠지는 지점을 따로 확인합니다.</span></p>
            <p><b>숙제는 하지만 성적 변화가 약한 학생</b><span>완료 여부만 보지 않고 복습 밀도, 오답 재확인, 시험 전 반복 횟수를 함께 점검합니다.</span></p>
            <p><b>학부모가 공부 상황을 알기 어려운 학생</b><span>수업 후 어떤 부분을 했고 무엇이 남았는지 상담과 피드백으로 확인할 수 있게 정리합니다.</span></p>
          </div>
        </div>
      </section>"""


def render_child_link_section(center: Center) -> str:
    links = "\n".join(
        f'              <a href="{escape(slug)}/index.html"><span>{escape(child_topic_label(slug))}</span><strong>{escape(child_title(center, slug))}</strong><small>바로가기</small></a>'
        for slug in CHILD_SLUGS
    )
    return f"""
      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Detail Pages</p>
              <h2>{escape(center.name)} 상세 학습 페이지</h2>
            </div>
            <p class="section-desc">동네 기본 안내를 확인한 뒤, 필요한 과목 조합에 맞춰 더 구체적인 상담 기준을 확인할 수 있습니다.</p>
          </div>
          <div class="local-link-grid child-link-grid">
{links}
          </div>
        </div>
      </section>"""


def render_bottom_nav(center: Center, slug: str | None = None) -> str:
    if slug:
        sibling_links = "\n".join(
            f'              <a href="../{escape(item)}/index.html"><span>{escape(child_topic_label(item))}</span><strong>{escape(child_title(center, item))}</strong><small>바로가기</small></a>'
            for item in CHILD_SLUGS
            if item != slug
        )
        if not sibling_links:
            sibling_links = f'              <a href="../index.html"><span>기본</span><strong>{escape(center.name)} 안내</strong><small>바로가기</small></a>'
        return f"""
      <section class="section bottom-nav-section">
        <div class="container">
          <div class="bottom-nav-card">
            <div>
              <p class="section-kicker">Page Route</p>
              <h2>{escape(center.name)} 페이지 이동</h2>
              <p>현재 페이지와 연결된 상위 페이지를 빠르게 확인할 수 있습니다.</p>
            </div>
            <div class="route-button-grid">
              <a href="../index.html"><span>상위</span><strong>{escape(center.name)}</strong><small>동네 기본 안내</small></a>
              <a href="../../index.html"><span>상위</span><strong>전국학원</strong><small>전체 지역 보기</small></a>
{sibling_links}
            </div>
          </div>
        </div>
      </section>"""

    child_links = "\n".join(
        f'              <a href="{escape(item)}/index.html"><span>{escape(child_topic_label(item))}</span><strong>{escape(child_title(center, item))}</strong><small>바로가기</small></a>'
        for item in CHILD_SLUGS
    )
    return f"""
      <section class="section bottom-nav-section">
        <div class="container">
          <div class="bottom-nav-card">
            <div>
              <p class="section-kicker">Page Route</p>
              <h2>{escape(center.name)} 상위·하위 페이지 이동</h2>
              <p>동네 기본 안내와 과목별 상세 페이지를 자연스럽게 오갈 수 있도록 정리했습니다.</p>
            </div>
            <div class="route-button-grid">
              <a href="../index.html"><span>상위</span><strong>전국학원</strong><small>전체 지역 보기</small></a>
{child_links}
            </div>
          </div>
        </div>
      </section>"""


def extract_center(source_page: Path, position: int) -> Center:
    text = source_page.read_text(encoding="utf-8")
    graph = first_script_json(text).get("@graph", [])

    region = ""
    locality = ""
    for node in graph:
        types = as_type_list(node.get("@type"))
        if "EducationalOrganization" in types or "LocalBusiness" in types:
            address = node.get("address") or {}
            region = address.get("addressRegion") or ""
            locality = address.get("addressLocality") or ""
            break

    map_match = re.search(r'assets/maps/([^"\']+\.(?:jpg|jpeg|png|webp))', text, re.I)
    map_file = map_match.group(1) if map_match else ""

    name = source_page.parent.name
    return Center(
        name=name,
        title=f"{name} 전문학원",
        region=region,
        locality=locality,
        map_file=map_file,
        is_seoul=(region == "서울"),
        position=position,
    )


def collect_centers() -> list[Center]:
    centers: list[Center] = []
    for path in SOURCE_ROOT.iterdir():
        index = path / "index.html"
        if path.is_dir() and index.exists():
            centers.append(extract_center(index, len(centers) + 1))
    centers.sort(key=lambda c: c.position)
    for idx, center in enumerate(centers, start=1):
        center.position = idx
    return centers


def jsonld_script(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def nav(prefix: str, active: str) -> str:
    items = [
        ("홈", f"{prefix}index.html", "home"),
        ("학습가이드", f"{prefix}학습가이드/index.html", "guide"),
        ("상담문의", f"{prefix}상담문의/index.html", "contact"),
        ("전국학원", f"{prefix}전국학원/index.html", "national"),
    ]
    links = []
    for label, href, key in items:
        cls = ' class="is-active"' if key == active else ""
        links.append(f'<a{cls} href="{href}">{label}</a>')
    return "\n          ".join(links)


def header(prefix: str, active: str) -> str:
    return f"""
    <header class="site-header">
      <div class="container nav-wrap">
        <a class="brand" href="{prefix}index.html" aria-label="{SITE_NAME} 홈">
          <span class="brand-mark">☁</span>
          <span class="brand-text">
            {SITE_NAME}
            <small>진단부터 오답까지 부드럽게</small>
          </span>
        </a>
        <nav class="nav-menu" aria-label="상단 메뉴">
          {nav(prefix, active)}
        </nav>
      </div>
    </header>"""


def floating(prefix: str) -> str:
    return f"""
    <div class="floating-actions" aria-label="빠른 문의">
      <a href="tel:{PHONE_TEL}">📞 전화</a>
      <a href="sms:{PHONE_TEL}">💬 문자</a>
      <a href="{prefix}상담문의/index.html">☁️ 문의</a>
    </div>"""


def footer() -> str:
    return f"""
    <footer class="site-footer">
      <div class="container footer-card">
        <div>
          <strong>{SITE_NAME}</strong>
          <p>학생별 진도 수업과 공부 습관 코칭을 함께 운영합니다.</p>
        </div>
        <div>
          <strong>상담 문의</strong>
          <p>전화·문자 상담으로 학습 상황을 확인합니다.</p>
        </div>
      </div>
    </footer>"""


def absolute_url(path_or_url: str) -> str:
    if path_or_url.startswith(("https://", "http://")):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = "/" + path_or_url
    return BASE_URL + quote(path_or_url, safe="/:%#?=&")


def absolute_image_url(path_or_url: str) -> str:
    if path_or_url.startswith(("https://", "http://")):
        return path_or_url
    normalized = path_or_url
    while normalized.startswith("../"):
        normalized = normalized[3:]
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return absolute_url(normalized)


def base_head(title: str, description: str, css_prefix: str, canonical: str, image: str, og_type: str = "website") -> str:
    canonical_url = absolute_url(canonical)
    image_url = absolute_image_url(image)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{canonical_url}">
  <meta name="theme-color" content="#dff5ff">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{image_url}">
  <link rel="icon" href="{css_prefix}assets/favicon.png">
  <link rel="stylesheet" href="{css_prefix}assets/site.css">"""


def build_hub_jsonld(centers: list[Center]) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": "/전국학원/#webpage",
                "url": "/전국학원/",
                "name": "전국학원",
                "description": f"전국 {len(centers)}개 동네별 전문학원 학습관리 안내 페이지입니다.",
                "inLanguage": "ko-KR",
                "breadcrumb": {"@id": "/전국학원/#breadcrumb"},
                "mainEntity": {"@id": "/전국학원/#itemlist"},
                "about": [
                    {"@type": "Thing", "name": "전국학원"},
                    {"@type": "Thing", "name": "전문학원"},
                    {"@type": "Thing", "name": "학습관리"},
                    {"@type": "Thing", "name": "초중고 학습코칭"},
                ],
            },
            {
                "@type": "BreadcrumbList",
                "@id": "/전국학원/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                ],
            },
            {
                "@type": "ItemList",
                "@id": "/전국학원/#itemlist",
                "name": "동네별 전문학원 바로가기",
                "numberOfItems": len(centers),
                "itemListElement": [
                    {"@type": "ListItem", "position": c.position, "name": c.title, "url": c.url}
                    for c in centers
                ],
            },
        ],
    }


def render_hub(centers: list[Center]) -> str:
    groups: dict[str, list[Center]] = {}
    for center in centers:
        groups.setdefault(center.region or "기타", []).append(center)

    group_html = []
    ordered_regions = [region for region in REGION_ORDER if region in groups]
    ordered_regions += sorted(region for region in groups if region not in ordered_regions)

    for region in ordered_regions:
        region_centers = groups[region]
        district_groups: dict[str, list[Center]] = {}
        for center in region_centers:
            district_groups.setdefault(center.locality or "세부 지역", []).append(center)

        district_html = []
        for district, district_centers in district_groups.items():
            links = "\n".join(
                f'                    <a href="{escape(c.name)}/index.html"><span>{escape(c.name)}</span><small>전문학원 안내</small></a>'
                for c in district_centers
            )
            district_html.append(
                f"""
                <section class="district-block">
                  <div class="district-title-row">
                    <strong>{escape(district)}</strong>
                    <span>{len(district_centers)}개 동네</span>
                  </div>
                  <div class="region-pill-row">
{links}
                  </div>
                </section>"""
            )
        wide_class = " is-wide" if len(region_centers) >= 34 else ""
        group_html.append(
            f"""
            <article class="region-group{wide_class}">
              <div class="region-title-row">
                <h3>{escape(region)} 전문학원</h3>
                <span>{len(region_centers)}개 동네</span>
              </div>
              <p>{escape(region)} 지역을 시군구별로 나눠 정리했습니다. 먼저 시군구를 확인한 뒤 가까운 동네 페이지로 이동해 주세요.</p>
              <div class="district-block-grid">
{''.join(district_html)}
              </div>
            </article>"""
        )

    description = f"아이에게 맞는 학원을 알아보기 전, 가까운 동네의 학습관리 기준을 먼저 확인해보세요. 전국 {len(centers)}개 동네별로 상담 전 체크리스트, 학년별 관리 포인트, FAQ와 학부모 후기를 정리했습니다."
    head = base_head(
        "전국학원 | 학습관리학원",
        description,
        "../",
        "/전국학원/",
        "../assets/generated/academy-hero-v2.webp",
    )
    return f"""{head}
  <script type="application/ld+json">{jsonld_script(build_hub_jsonld(centers))}</script>
</head>
<body>
  <div class="site-shell">
    <span class="cloud cloud-one"></span>
    <span class="cloud cloud-two"></span>
    <span class="cloud cloud-three"></span>
{header("../", "national")}
    <main>
      <section class="local-hero">
        <div class="container local-hero-grid">
          <div class="local-hero-card">
            <nav class="breadcrumb" aria-label="breadcrumb">
              <a href="../index.html">홈</a><span>›</span><span>전국학원</span>
            </nav>
            <span class="eyebrow">☁️ 학부모를 위한 동네별 학습관리 안내</span>
            <h1 class="page-title">우리 아이에게 맞는 동네 학습관리 기준을 먼저 확인하세요.</h1>
            <p class="hero-copy">{escape(description)}</p>
            <div class="local-badges">
              <span>전국 {len(centers)}개 동네</span>
              <span>초등·중등·고등</span>
              <span>영어·수학·국어</span>
              <span>상담 전 체크리스트</span>
            </div>
          </div>
          <aside class="quick-stat-card">
            <span>동네별 안내 페이지</span>
            <strong>{len(centers)}개</strong>
            <p>가까운 동네를 선택하면 아이의 현재 공부 상태를 상담 전에 어떻게 정리하면 좋을지 한눈에 볼 수 있습니다.</p>
          </aside>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Choose Area</p>
              <h2>거주 지역에서 가까운 동네를 선택해 주세요.</h2>
            </div>
            <p class="section-desc">지역을 고른 뒤 동네 페이지에서 상담 전 확인사항, 학년별 관리 포인트, FAQ와 학부모 후기를 차분히 확인할 수 있습니다.</p>
          </div>
          <div class="region-directory-grid">
{''.join(group_html)}
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="cta-band">
            <p class="section-kicker">Before Consultation</p>
            <h2>상담 전에는 아이가 어디에서 막히는지부터 가볍게 정리해보세요.</h2>
            <p>최근 시험지, 현재 교재, 학교 진도, 숙제 습관, 자주 반복되는 오답 유형을 알려주시면 필요한 과목과 관리 순서를 더 자연스럽게 잡을 수 있습니다.</p>
            <div class="hero-actions">
              <a class="button button-primary" href="../상담문의/index.html">상담문의 보기</a>
              <a class="button button-soft" href="../학습가이드/index.html">학습가이드 보기</a>
            </div>
          </div>
        </div>
      </section>
    </main>
{floating("../")}
{footer()}
  </div>
</body>
</html>
"""


def build_center_jsonld(center: Center, related: list[Center]) -> dict:
    representative_url = representative_image_url(center.url)
    faq_items = center_faqs(center)
    review_items = center_reviews(center)
    school_info = school_info_for(center)
    org_info = org_info_for(center)
    school_schema = school_item_list(center, school_info)
    center_name = org_info.get("center_name") or center.title
    address = org_info.get("address") or f"{center.area_phrase} 상담 가능 지역"
    hours = org_info.get("hours") or "12시-24시"
    about = [
        {"@type": "Thing", "name": center.title},
        {"@type": "Place", "name": center.name},
        {"@type": "Thing", "name": "전문학원"},
        {"@type": "Thing", "name": "학습관리"},
        {"@type": "Thing", "name": "플래너 관리"},
        {"@type": "Thing", "name": "오답 재학습"},
        {"@type": "Thing", "name": "영어 수학 국어 코칭"},
    ]
    mentions = [
        {"@type": "Place", "name": center.region},
        {"@type": "Place", "name": center.locality},
        {"@type": "Place", "name": center.name},
        {"@type": "Thing", "name": "진단 상담"},
        {"@type": "Thing", "name": "시험 대비 계획"},
        {"@type": "Thing", "name": "학부모 피드백"},
    ]
    if center_name:
        mentions.append({"@type": "EducationalOrganization", "name": center_name})
    mentions.extend(school_mentions(school_info))
    has_part = [
        {"@type": "WebPageElement", "name": "핵심 요약"},
        {"@type": "WebPageElement", "name": "본문 이미지"},
        {"@type": "WebPageElement", "name": "지도 이미지"},
        {"@type": "WebPageElement", "name": "학부모 고민 안내"},
        {"@type": "WebPageElement", "name": "학년별 수업 특징"},
        {"@type": "WebPageElement", "name": "추천 학생 유형"},
        {"@type": "WebPageElement", "name": "답변형 학습 안내"},
        {"@type": "WebPageElement", "name": "지역·학년·추천학생"},
        {"@type": "WebPageElement", "name": "수업 가능 학교"},
        {"@type": "WebPageElement", "name": "센터 기준 정보"},
        {"@type": "WebPageElement", "name": "상담 전 체크리스트"},
        {"@type": "WebPageElement", "name": "FAQ"},
        {"@type": "WebPageElement", "name": "학부모 후기"},
        {"@type": "WebPageElement", "name": "내부링크"},
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{center.url}#webpage",
                "url": center.url,
                "name": center.title,
                "description": f"{center.area_phrase} 학생을 위한 전문학원 학습관리 안내입니다.",
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": f"{center.url}#primaryimage"},
                "breadcrumb": {"@id": f"{center.url}#breadcrumb"},
                "mainEntity": {"@id": f"{center.url}#service"},
                "about": about,
                "mentions": mentions,
                "hasPart": has_part,
            },
            {
                "@type": "ImageObject",
                "@id": f"{center.url}#primaryimage",
                "url": representative_url,
                "caption": f"{center.title} 대표 이미지",
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{center.url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                    {"@type": "ListItem", "position": 3, "name": center.name, "item": center.url},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": f"{center.url}#organization",
                "name": center_name,
                "alternateName": [SITE_NAME, center.title, f"{center.name} 학습관리학원"],
                "url": center.url,
                "telephone": PHONE_DISPLAY,
                "openingHours": "Mo-Sa 12:00-24:00",
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                        "opens": "12:00",
                        "closes": "24:00",
                        "description": hours,
                    }
                ],
                "areaServed": {"@type": "Place", "name": center.name},
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": address,
                    "addressRegion": center.region,
                    "addressLocality": center.locality,
                    "addressCountry": "KR",
                },
                "knowsAbout": ["초등 학습관리", "중등 내신 관리", "고등 학습관리", "영어 수학 국어 코칭", "전문학원 상담", "플래너 관리", "오답 재학습"],
                "contactPoint": {
                    "@type": "ContactPoint",
                    "telephone": PHONE_SCHEMA,
                    "contactType": "학습 상담",
                    "availableLanguage": "Korean",
                },
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 초등반 학습관리", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 중등반 내신관리", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 고등반 학습관리", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 영어·수학·국어 학습코칭", "serviceType": "TutoringService"}},
                ],
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "bestRating": "5", "ratingCount": "6", "reviewCount": "6"},
                "review": [
                    {
                        "@type": "Review",
                        "author": {"@type": "Person", "name": "학부모"},
                        "reviewBody": review["body"],
                        "reviewRating": {"@type": "Rating", "ratingValue": review["rating"], "bestRating": "5"},
                    }
                    for review in review_items
                ],
            },
            {
                "@type": "Article",
                "@id": f"{center.url}#article",
                "headline": center.title,
                "description": f"{center.area_phrase} 학생을 위한 전문학원 학습관리 안내입니다.",
                "image": [representative_url, f"/assets/centers/common/{center.main_image_file}", f"/assets/maps/{center.map_file}"],
                "inLanguage": "ko-KR",
                "datePublished": PUBLISHED,
                "dateModified": PUBLISHED,
                "author": {"@id": f"{center.url}#organization"},
                "publisher": {"@type": "Organization", "name": SITE_NAME, "url": "/"},
                "mainEntityOfPage": {"@id": f"{center.url}#webpage"},
                "about": about,
                "mentions": mentions,
                "articleSection": ["학부모 고민 안내", "학년별 수업 특징", "추천 학생 유형", "핵심 요약", "답변형 학습 안내", "지역·학년·추천학생", "수업 가능 학교", "센터 기준 정보", "상담 전 체크리스트", "FAQ", "학부모 후기"],
            },
            {
                "@type": "Service",
                "@id": f"{center.url}#service",
                "name": f"{center.name} 전문학원 학습관리",
                "serviceType": "TutoringService",
                "description": f"{center.name} 학생의 영어·수학·국어 학습 상태를 진단하고 플래너, 오답, 시험 대비 흐름을 관리합니다.",
                "provider": {"@id": f"{center.url}#organization"},
                "areaServed": {"@type": "Place", "name": center.name},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
                "mentions": mentions,
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 학습 진단 상담"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 플래너 관리"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} 오답 재학습"}},
                ],
            },
            {
                "@type": "ItemList",
                "@id": f"{center.url}#checklist",
                "name": f"{center.title} 상담 전 체크리스트",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": f"{center.name} 학교 진도와 현재 교재 확인"},
                    {"@type": "ListItem", "position": 2, "name": "최근 시험지와 반복 오답 유형 확인"},
                    {"@type": "ListItem", "position": 3, "name": "초등·중등·고등 학년별 관리 기준 확인"},
                    {"@type": "ListItem", "position": 4, "name": "플래너 실행 여부와 학부모 피드백 정리"},
                ],
            },
            {
                "@type": "ItemList",
                "@id": f"{center.url}#related",
                "name": f"{center.name} 주변 전문학원 내부링크",
                "itemListElement": [
                    {"@type": "ListItem", "position": idx + 1, "name": item.title, "url": item.url}
                    for idx, item in enumerate(related)
                ],
            },
            *([school_schema] if school_schema else []),
            {
                "@type": "FAQPage",
                "@id": f"{center.url}#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer,
                        },
                    }
                    for question, answer in faq_items
                ],
            },
        ],
    }


def related_centers(centers: list[Center], center: Center, limit: int = 8) -> list[Center]:
    same_locality = [c for c in centers if c.name != center.name and c.locality == center.locality]
    same_region = [c for c in centers if c.name != center.name and c.region == center.region and c not in same_locality]
    others = [c for c in centers if c.name != center.name and c not in same_locality and c not in same_region]
    return (same_locality + same_region + others)[:limit]


def build_child_jsonld(center: Center, related: list[Center], slug: str) -> dict:
    title = child_title(center, slug)
    url = child_url(center, slug)
    representative_url = representative_image_url(url)
    profile = child_profile(slug)
    topic = profile["topic"]
    faq_items = child_faqs(center, slug)
    review_items = child_reviews(center, slug)
    school_info = school_info_for(center)
    org_info = org_info_for(center)
    school_schema = school_item_list(center, school_info, title, url)
    center_name = org_info.get("center_name") or title
    address = org_info.get("address") or ""
    hours = org_info.get("hours") or "12시-24시"
    about = [
        {"@type": "Thing", "name": title},
        {"@type": "Place", "name": center.name},
        {"@type": "Thing", "name": profile["page_type"]},
        {"@type": "Thing", "name": f"{profile['primary']} 학습관리"},
        {"@type": "Thing", "name": f"{profile['secondary']} 학습관리"},
        {"@type": "Thing", "name": "내신 대비"},
        {"@type": "Thing", "name": "오답 재학습"},
    ]
    mentions = [
        {"@type": "Place", "name": center.region},
        {"@type": "Place", "name": center.locality},
        {"@type": "Place", "name": center.name},
        {"@type": "Thing", "name": profile["primary_scope"]},
        {"@type": "Thing", "name": profile["secondary_scope"]},
        {"@type": "Thing", "name": "학부모 상담"},
    ]
    if center_name:
        mentions.append({"@type": "EducationalOrganization", "name": center_name})
    mentions.extend(school_mentions(school_info))
    has_part = [
        {"@type": "WebPageElement", "name": f"{profile['pair']} 상담 안내"},
        {"@type": "WebPageElement", "name": f"학년별 {profile['pair']} 관리"},
        {"@type": "WebPageElement", "name": "추천 학생 유형"},
        {"@type": "WebPageElement", "name": "핵심 요약"},
        {"@type": "WebPageElement", "name": "답변형 학습 안내"},
        {"@type": "WebPageElement", "name": "지역·학년·추천학생"},
        {"@type": "WebPageElement", "name": "수업 가능 학교"},
        {"@type": "WebPageElement", "name": "센터 기준 정보"},
        {"@type": "WebPageElement", "name": "상담 전 체크리스트"},
        {"@type": "WebPageElement", "name": "FAQ"},
        {"@type": "WebPageElement", "name": "학부모 후기"},
        {"@type": "WebPageElement", "name": "내부링크"},
    ]
    graph = [
        {
            "@type": "WebPage",
            "@id": f"{url}#webpage",
            "url": url,
            "name": title,
            "description": f"{center.area_phrase} 학생을 위한 {profile['page_type']} 상담 안내입니다. {profile['subject_pair']}의 현재 수준, 학교 진도, 오답과 학습 습관을 함께 확인합니다.",
            "inLanguage": "ko-KR",
            "primaryImageOfPage": {"@id": f"{url}#primaryimage"},
            "breadcrumb": {"@id": f"{url}#breadcrumb"},
            "mainEntity": {"@id": f"{url}#service"},
            "about": about,
            "mentions": mentions,
            "hasPart": has_part,
        },
        {
            "@type": "ImageObject",
            "@id": f"{url}#primaryimage",
            "url": representative_url,
            "caption": f"{title} 대표 이미지",
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                {"@type": "ListItem", "position": 3, "name": center.name, "item": center.url},
                {"@type": "ListItem", "position": 4, "name": slug, "item": url},
            ],
        },
        {
            "@type": ["EducationalOrganization", "LocalBusiness"],
            "@id": f"{url}#organization",
            "name": title,
            "alternateName": [SITE_NAME, center_name, f"{center.name} {profile['pair']} 학습관리"],
            "url": url,
            "telephone": PHONE_DISPLAY,
            "openingHours": "Mo-Sa 12:00-24:00",
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "opens": "12:00",
                    "closes": "24:00",
                    "description": hours,
                }
            ],
            "areaServed": {"@type": "Place", "name": center.name},
            "address": {
                "@type": "PostalAddress",
                "streetAddress": address,
                "addressRegion": center.region,
                "addressLocality": center.locality,
                "addressCountry": "KR",
            },
            "knowsAbout": [f"{profile['primary']} 학습관리", f"{profile['secondary']} 학습관리", f"초등 {profile['pair']}", "중등 내신", f"고등 {profile['pair']}", "오답 재학습"],
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": PHONE_SCHEMA,
                "contactType": f"{profile['pair']} 학습 상담",
                "availableLanguage": "Korean",
            },
            "makesOffer": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['primary']} 학습관리", "serviceType": "TutoringService"}},
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['secondary']} 학습관리", "serviceType": "TutoringService"}},
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['pair']} 내신 대비", "serviceType": "TutoringService"}},
            ],
            "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "bestRating": "5", "ratingCount": "6", "reviewCount": "6"},
            "review": [
                {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": "학부모"},
                    "reviewBody": review["body"],
                    "reviewRating": {"@type": "Rating", "ratingValue": review["rating"], "bestRating": "5"},
                }
                for review in review_items
            ],
        },
        {
            "@type": "Article",
            "@id": f"{url}#article",
            "headline": title,
            "description": f"{center.area_phrase} 학생을 위한 {profile['page_type']} 상담 안내입니다.",
            "image": [representative_url, f"/assets/centers/common/{center.main_image_file}", f"/assets/maps/{center.map_file}"],
            "inLanguage": "ko-KR",
            "datePublished": PUBLISHED,
            "dateModified": PUBLISHED,
            "author": {"@id": f"{url}#organization"},
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": "/"},
            "mainEntityOfPage": {"@id": f"{url}#webpage"},
            "about": about,
            "mentions": mentions,
            "articleSection": [f"{profile['pair']} 상담 안내", f"학년별 {profile['pair']} 관리", "추천 학생 유형", "핵심 요약", "답변형 학습 안내", "지역·학년·추천학생", "수업 가능 학교", "센터 기준 정보", "상담 전 체크리스트", "FAQ", "학부모 후기"],
        },
        {
            "@type": "Service",
            "@id": f"{url}#service",
            "name": f"{center.name} {profile['page_type']} 학습관리",
            "serviceType": "TutoringService",
            "description": f"{center.name} 학생의 {profile['subject_pair']} 학습 상태를 진단하고 학교 진도, 오답, 플래너 실행을 함께 관리합니다.",
            "provider": {"@id": f"{url}#organization"},
            "areaServed": {"@type": "Place", "name": center.name},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
            "about": about,
            "mentions": mentions,
            "makesOffer": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['pair']} 진단 상담"}},
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['primary']} {profile['primary_scope']} 관리"}},
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{center.name} {profile['secondary']} {profile['secondary_scope']} 관리"}},
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{url}#checklist",
            "name": f"{title} 상담 전 체크리스트",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": f"{profile['primary']} {profile['primary_scope']} 확인"},
                {"@type": "ListItem", "position": 2, "name": f"{profile['secondary']} {profile['secondary_scope']} 확인"},
                {"@type": "ListItem", "position": 3, "name": f"{center.name} 학교 진도와 시험 범위 확인"},
                {"@type": "ListItem", "position": 4, "name": "숙제 완료 여부와 플래너 실행 흐름 확인"},
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{url}#related",
            "name": f"{center.name} 주변 {profile['page_type']} 내부링크",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": center.title, "url": center.url},
                *[
                    {"@type": "ListItem", "position": idx + 2, "name": child_title(item, slug), "url": child_url(item, slug)}
                    for idx, item in enumerate(related)
                ],
            ],
        },
    ]
    if school_schema:
        graph.append(school_schema)
    graph.append(
        {
            "@type": "FAQPage",
            "@id": f"{url}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in faq_items
            ],
        }
    )
    return {"@context": "https://schema.org", "@graph": graph}


def render_center(center: Center, centers: list[Center]) -> str:
    related = related_centers(centers, center)
    representative_url = representative_image_url(center.url)
    faq_cards = center_faqs(center)
    review_cards = center_reviews(center)
    school_info = school_info_for(center)
    org_info = org_info_for(center)
    story_sections = render_story_sections(center, school_info)
    school_section = render_school_section(center, school_info)
    child_link_section = render_child_link_section(center)
    bottom_nav = render_bottom_nav(center)
    center_name = org_info.get("center_name") or center.title
    address = org_info.get("address") or f"{center.area_phrase} 상담 가능 지역"
    hours = org_info.get("hours") or "12시-24시"
    related_links = "\n".join(
        f'              <a href="../{escape(item.name)}/index.html">{escape(item.title)}</a>'
        for item in related
    )
    faq_html = "\n".join(
        f"""
            <details>
              <summary>{escape(q)}</summary>
              <p>{escape(a)}</p>
            </details>"""
        for q, a in faq_cards
    )
    review_html = "\n".join(
        f"""
            <article class="review-card">
              <div class="stars">{escape(review['stars'])}</div>
              <p>{escape(review['body'])}</p>
            </article>"""
        for review in review_cards
    )
    description = f"{center.area_phrase} 학생을 위한 전문학원 학습관리 안내입니다. 상담 전 확인할 핵심 요약, 지도, 학년별 관리 기준, FAQ와 학부모 후기를 정리했습니다."
    head = base_head(
        f"{center.title} | {SITE_NAME}",
        description,
        "../../",
        center.url,
        representative_url,
        "article",
    )
    return f"""{head}
  <script type="application/ld+json">{jsonld_script(build_center_jsonld(center, related))}</script>
</head>
<body>
  <div class="site-shell">
    <span class="cloud cloud-one"></span>
    <span class="cloud cloud-two"></span>
    <span class="cloud cloud-three"></span>
{header("../../", "national")}
    <main>
      <section class="local-hero">
        <div class="container local-hero-grid">
          <div class="local-hero-card">
            <nav class="breadcrumb" aria-label="breadcrumb">
              <a href="../../index.html">홈</a><span>›</span><a href="../index.html">전국학원</a><span>›</span><span>{escape(center.name)}</span>
            </nav>
            <span class="eyebrow">☁️ {escape(center.area_phrase)} 학습관리 안내</span>
            <h1 class="page-title">{escape(center.title)}</h1>
            <p class="hero-copy">{escape(description)}</p>
            <div class="local-badges">
              <span>{escape(center.region or "전국")}</span>
              <span>{escape(center.locality or center.name)}</span>
              <span>영어·수학·국어</span>
              <span>초등·중등·고등</span>
            </div>
          </div>
          <aside class="quick-stat-card">
            <span>상담 안내</span>
            <strong>전화·문자 상담 가능</strong>
            <p>수업 가능 여부와 세부 운영 방식은 상담 시 현재 상황에 맞춰 확인해 주세요.</p>
            <div class="hero-actions">
              <a class="button button-soft" href="tel:{PHONE_TEL}">전화하기</a>
              <a class="button button-soft" href="../../상담문의/index.html">상담문의</a>
            </div>
          </aside>
        </div>
      </section>

      <section class="section">
        <div class="container local-media-section">
          {hidden_representative_image(center.title, representative_url)}
          <figure class="local-media-card">
            <img src="../../assets/centers/common/{center.main_image_file}" alt="{escape(center.title)} 본문 이미지">
          </figure>
          <figure class="local-map-card">
            <img src="../../assets/maps/{escape(center.map_file)}" alt="{escape(center.title)} 지도 이미지">
            <figcaption class="local-map-caption">
              <strong>{escape(center.name)} 위치 안내</strong>
              <span>{escape(center.area_phrase)} 기준으로 상담 전 확인할 수 있는 지도 이미지입니다.</span>
            </figcaption>
          </figure>
        </div>
      </section>

{story_sections}

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">GEO Summary</p>
              <h2>{escape(center.title)} 핵심 요약</h2>
            </div>
          </div>
          <div class="geo-summary-grid">
            <article class="geo-summary-card">
              <b>진단 중심 상담</b>
              <p>{escape(center.name)} 학생의 최근 성적, 학교 진도, 어려운 과목과 단원을 먼저 확인합니다.</p>
            </article>
            <article class="geo-summary-card">
              <b>플래너 실행 점검</b>
              <p>하루 공부량을 무리하게 늘리기보다 완료 여부와 미뤄진 이유를 함께 점검합니다.</p>
            </article>
            <article class="geo-summary-card">
              <b>오답 원인 분석</b>
              <p>개념 부족, 계산 실수, 조건 해석, 시간 부족을 나누어 같은 실수를 줄이는 방향으로 봅니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container answer-box">
          <p class="section-kicker">Answer</p>
          <h2>{escape(center.name)}에서 전문학원을 찾을 때 무엇을 봐야 할까요?</h2>
          <p>{escape(center.title)}을 알아볼 때는 단순히 진도를 얼마나 빨리 나가는지보다, 학생의 현재 시작점이 정확히 잡히는지 확인하는 것이 중요합니다. 같은 점수라도 개념이 부족한 학생, 문제 조건을 놓치는 학생, 공부 계획을 실행하지 못하는 학생은 관리 방식이 달라야 합니다.</p>
          <p>{SITE_NAME}은 상담에서 학생의 학교 진도와 현재 교재, 시험 준비 시기, 반복되는 오답 유형을 함께 살피고, 플래너와 오답 재학습이 이어지도록 방향을 정리합니다.</p>
        </div>
      </section>

{child_link_section}

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Students</p>
              <h2>지역·학년·추천학생 기준</h2>
            </div>
          </div>
          <div class="mini-grid">
            <div class="mini-card">
              <strong>지역 기준</strong>
              <span>{escape(center.area_phrase)} 학생이 상담 전 확인할 수 있도록 지역명과 지도 이미지를 함께 정리했습니다.</span>
            </div>
            <div class="mini-card">
              <strong>학년 기준</strong>
              <span>초등은 습관과 기본기, 중등은 내신 범위와 단원별 오답, 고등은 시험 범위와 취약 유형을 중심으로 봅니다.</span>
            </div>
            <div class="mini-card">
              <strong>추천 학생</strong>
              <span>숙제는 하지만 성적 변화가 약한 학생, 오답이 반복되는 학생, 시험 준비 루틴이 필요한 학생에게 적합합니다.</span>
            </div>
          </div>
        </div>
      </section>

{school_section}

      <section class="section">
        <div class="container answer-box org-detail-card">
          <p class="section-kicker">Center Information</p>
          <h2>{escape(center.title)} 센터 기준 정보</h2>
          <p><strong>{escape(center_name)}</strong> 기준으로 {escape(center.name)} 학생 상담 흐름을 정리했습니다. 주소 자료는 상담 전 위치와 생활권을 확인하기 위한 참고 정보로 활용됩니다.</p>
          <p>주소: {escape(address)}</p>
          <p>운영 시간: {escape(hours)} · 상담은 학생 상황 확인 후 안내됩니다.</p>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Checklist</p>
              <h2>{escape(center.title)} 상담 전 체크리스트</h2>
            </div>
          </div>
          <div class="checklist-grid">
            <div class="check-item">최근 시험지 또는 수행평가 결과를 준비해 주세요.</div>
            <div class="check-item">현재 사용하는 교재와 학교 진도를 알려주시면 좋아요.</div>
            <div class="check-item">가장 어려워하는 과목과 단원을 정리해 주세요.</div>
            <div class="check-item">숙제·복습·플래너 실행이 끊기는 지점을 함께 확인합니다.</div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">FAQ</p>
              <h2>자주 묻는 질문</h2>
            </div>
          </div>
          <div class="panel soft-panel">
            {faq_html}
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Parent Review</p>
              <h2>{escape(center.name)} 학부모 학습 상담 후기</h2>
            </div>
          </div>
          <div class="review-grid">
{review_html}
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Internal Links</p>
              <h2>다른 동네 전문학원도 함께 보기</h2>
            </div>
          </div>
          <div class="local-link-grid">
{related_links}
          </div>
        </div>
      </section>

{bottom_nav}

      <section class="section">
        <div class="container">
          <div class="cta-band">
            <p class="section-kicker">Consultation</p>
            <h2>{escape(center.title)} 상담 전, 아이의 공부 흐름을 먼저 정리해보세요.</h2>
            <p>학습 상담은 현재 상태를 정확히 보는 것부터 시작합니다. 성적표보다 중요한 것은 어느 지점에서 공부가 끊기는지, 어떤 오답이 반복되는지, 계획이 실제로 실행되는지입니다.</p>
            <div class="hero-actions">
              <a class="button button-primary" href="tel:{PHONE_TEL}">전화 상담</a>
              <a class="button button-soft" href="../../학습가이드/index.html">학습가이드 보기</a>
            </div>
          </div>
        </div>
      </section>
    </main>
{floating("../../")}
{footer()}
  </div>
</body>
</html>
"""


def render_child_page(center: Center, centers: list[Center], slug: str) -> str:
    related = related_centers(centers, center, limit=7)
    title = child_title(center, slug)
    profile = child_profile(slug)
    topic = profile["topic"]
    url = child_url(center, slug)
    representative_url = representative_image_url(url)
    school_info = school_info_for(center)
    org_info = org_info_for(center)
    faq_cards = child_faqs(center, slug)
    review_cards = child_reviews(center, slug)
    school_section = render_school_section(center, school_info, title)
    bottom_nav = render_bottom_nav(center, slug)
    related_links = "\n".join(
        f'              <a href="../../{escape(item.name)}/{escape(slug)}/index.html"><span>{escape(item.locality or item.region)}</span><strong>{escape(child_title(item, slug))}</strong><small>바로가기</small></a>'
        for item in related
    )
    faq_html = "\n".join(
        f"""
            <details>
              <summary>{escape(q)}</summary>
              <p>{escape(a)}</p>
            </details>"""
        for q, a in faq_cards
    )
    review_html = "\n".join(
        f"""
            <article class="review-card">
              <div class="stars">{escape(review['stars'])}</div>
              <p>{escape(review['body'])}</p>
            </article>"""
        for review in review_cards
    )
    center_name = org_info.get("center_name") or title
    address = org_info.get("address") or f"{center.area_phrase} 상담 가능 지역"
    hours = org_info.get("hours") or "12시-24시"
    description = f"{center.area_phrase} 학생을 위한 {profile['page_type']} 안내입니다. {profile['subject_pair']}의 학교 진도, 오답, 플래너 관리 기준을 상담 전 확인할 수 있습니다."
    head = base_head(
        f"{title} | {SITE_NAME}",
        description,
        "../../../",
        url,
        representative_url,
        "article",
    )
    return f"""{head}
  <script type="application/ld+json">{jsonld_script(build_child_jsonld(center, related, slug))}</script>
</head>
<body>
  <div class="site-shell">
    <span class="cloud cloud-one"></span>
    <span class="cloud cloud-two"></span>
    <span class="cloud cloud-three"></span>
{header("../../../", "national")}
    <main>
      <section class="local-hero">
        <div class="container local-hero-grid">
          <div class="local-hero-card">
            <nav class="breadcrumb" aria-label="breadcrumb">
              <a href="../../../index.html">홈</a><span>›</span><a href="../../index.html">전국학원</a><span>›</span><a href="../index.html">{escape(center.name)}</a><span>›</span><span>{escape(slug)}</span>
            </nav>
            <span class="eyebrow">☁️ {escape(center.area_phrase)} {escape(topic)} 학습관리</span>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="hero-copy">{escape(description)}</p>
            <div class="local-badges">
              <span>{escape(center.region or "전국")}</span>
              <span>{escape(center.locality or center.name)}</span>
              <span>{escape(topic)} 집중</span>
              <span>초등·중등·고등</span>
            </div>
          </div>
          <aside class="quick-stat-card">
            <span>상담 안내</span>
            <strong>전화·문자 상담 가능</strong>
            <p>{escape(center.name)} 학생의 {escape(profile['subject_pair'])}의 현재 단원, 학교 진도, 시험 준비 흐름을 상담 시 함께 확인합니다.</p>
            <div class="hero-actions">
              <a class="button button-soft" href="tel:{PHONE_TEL}">전화하기</a>
              <a class="button button-soft" href="../../../상담문의/index.html">상담문의</a>
            </div>
          </aside>
        </div>
      </section>

      <section class="section">
        <div class="container local-media-section">
          {hidden_representative_image(title, representative_url)}
          <figure class="local-media-card">
            <img src="../../../assets/centers/common/{center.main_image_file}" alt="{escape(title)} 본문 이미지">
          </figure>
          <figure class="local-map-card">
            <img src="../../../assets/maps/{escape(center.map_file)}" alt="{escape(title)} 지도 이미지">
            <figcaption class="local-map-caption">
              <strong>{escape(center.name)} 위치 안내</strong>
              <span>{escape(center.area_phrase)} 기준으로 {escape(profile['pair'])} 상담 전 확인할 수 있는 지도 이미지입니다.</span>
            </figcaption>
          </figure>
        </div>
      </section>

      <section class="section story-section">
        <div class="container">
          <div class="story-panel">
            <div class="story-copy">
              <p class="section-kicker">{escape(profile['guide_kicker'])}</p>
              <h2>{escape(title)}, {escape(profile['guide_heading'])}</h2>
              <p>{escape(center.name)}에서 {escape(profile['page_type'])}을 찾는 학부모님은 보통 “{escape(profile['parent_question'])}”, “{escape(profile['subject_kind'])}을 함께 관리해도 되는지”를 고민합니다. 실제로는 과목을 나누기 전에 아이가 공부를 실행하는 방식부터 살펴보는 것이 중요합니다.</p>
              <p>{escape(profile['main_reason'])} {escape(title)} 상담에서는 {escape(profile['priority'])}</p>
              <p>{escape(school_context_sentence(center, school_info))}</p>
            </div>
            <div class="story-quote-grid">
              <article class="story-quote">
                <span>01</span>
                <strong>{escape(profile['primary'])} 우선 점검</strong>
                <p>{escape(profile['primary_scope'])}이 실제 문제 풀이와 시험 준비로 이어지는지 확인합니다.</p>
              </article>
              <article class="story-quote">
                <span>02</span>
                <strong>{escape(profile['secondary'])} 병행 관리</strong>
                <p>{escape(profile['secondary_scope'])} 흐름이 끊기지 않도록 주간 계획 안에서 함께 조정합니다.</p>
              </article>
              <article class="story-quote">
                <span>PLAN</span>
                <strong>{escape(profile['subject_count_label'])} 플래너</strong>
                <p>시험 기간에는 {escape(profile['subject_pair'])}의 공부량이 한쪽으로 쏠리지 않도록 주간 계획을 조정합니다.</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Grade Coaching</p>
              <h2>{escape(title)} 학년별 관리 포인트</h2>
            </div>
            <p class="section-desc">같은 {escape(profile['pair'])} 수업이라도 초등·중등·고등 단계에 따라 목표가 달라집니다. 자식페이지는 {escape(title)} 키워드에 맞춰 더 구체적으로 정리했습니다.</p>
          </div>
          <div class="grade-story-grid">
            <article class="grade-story-card">
              <em>Elementary</em>
              <strong>초등 {escape(profile['pair'])}</strong>
              <p>초등 단계에서는 {escape(profile['primary_scope_object'])} 확인하고, {escape(profile['secondary_scope'])} 흐름이 매일 이어지도록 작은 루틴을 만듭니다. 공부 습관이 잡히는 시기라 짧고 꾸준한 관리가 중요합니다.</p>
            </article>
            <article class="grade-story-card">
              <em>Middle School</em>
              <strong>중등 {escape(profile['pair'])}</strong>
              <p>학교 시험 범위에 맞춰 {escape(profile['primary'])}의 취약 단원과 {escape(profile['secondary'])}의 누적 과제를 함께 관리합니다. 내신 대비는 시험 직전이 아니라 평소 누적 관리가 핵심입니다.</p>
            </article>
            <article class="grade-story-card">
              <em>High School</em>
              <strong>고등 {escape(profile['pair'])}</strong>
              <p>{escape(profile['primary'])}의 점수 변동 원인과 {escape(profile['secondary'])}의 누적 학습 흐름을 함께 확인합니다. 과목별 우선순위를 잡아 시험 기간 계획이 흔들리지 않게 돕습니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container rec-story-panel">
          <div>
            <p class="section-kicker">Recommended</p>
            <h2>{escape(center.name)}에서 이런 학생이라면 {escape(profile['pair'])} 상담을 권합니다.</h2>
          </div>
          <div class="rec-story-list">
            <p><b>{escape(profile['recommended_1_title'])}</b><span>{escape(profile['recommended_1_text'])}</span></p>
            <p><b>{escape(profile['recommended_2_title'])}</b><span>{escape(profile['recommended_2_text'])}</span></p>
            <p><b>{escape(profile['subject_count_label'])} 모두 숙제는 하지만 성적 변화가 약한 학생</b><span>완료 여부보다 복습 밀도, 오답 재확인, 시험 전 반복 횟수를 기준으로 봅니다.</span></p>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">GEO Summary</p>
              <h2>{escape(title)} 핵심 요약</h2>
            </div>
            <p class="section-desc">검색에서 페이지 내용을 빠르게 이해할 수 있도록 {escape(center.name)} {escape(profile['pair'])} 상담의 기준을 짧게 정리했습니다.</p>
          </div>
          <div class="geo-summary-grid">
            <article class="geo-summary-card">
              <b>{escape(profile['summary_primary_title'])}</b>
              <p>{escape(profile['summary_primary_text'])}</p>
            </article>
            <article class="geo-summary-card">
              <b>{escape(profile['summary_secondary_title'])}</b>
              <p>{escape(profile['summary_secondary_text'])}</p>
            </article>
            <article class="geo-summary-card">
              <b>학습관리</b>
              <p>{escape(profile['subject_pair'])}의 공부량이 한쪽으로 쏠리지 않도록 플래너와 복습 루틴을 함께 점검합니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container answer-box">
          <p class="section-kicker">Answer</p>
          <h2>{escape(center.name)}에서 {escape(profile['answer_question'])}</h2>
          <p>{escape(title)}을 알아볼 때는 {escape(profile['subject_pair_object'])} 단순히 “{escape(profile['subject_count_label'])} 수업”으로 묶어 보는 것보다, 학생이 각 과목에서 어디까지 혼자 해내고 어디서 멈추는지를 구분하는 것이 중요합니다.</p>
          <p>{escape(profile['answer_body'])}</p>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Local Fit</p>
              <h2>{escape(title)} 지역·학년·추천학생 기준</h2>
            </div>
          </div>
          <div class="mini-grid">
            <div class="mini-card">
              <strong>지역 기준</strong>
              <span>{escape(center.area_phrase)} 학생이 상담 전 확인하기 쉽도록 지도, 학교 진도 확인 항목, 상담 기준을 함께 정리했습니다.</span>
            </div>
            <div class="mini-card">
              <strong>학년 기준</strong>
              <span>초등은 기본기와 습관, 중등은 내신 범위와 서술형, 고등은 시험 전략과 취약 유형을 중심으로 봅니다.</span>
            </div>
            <div class="mini-card">
              <strong>추천 학생</strong>
              <span>{escape(profile['subject_pair'])} 중 한 과목만 문제가 아니라 공부 실행 루틴 전체가 흔들리는 학생에게 특히 적합합니다.</span>
            </div>
          </div>
        </div>
      </section>

{school_section}

      <section class="section">
        <div class="container answer-box org-detail-card">
          <p class="section-kicker">Center Information</p>
          <h2>{escape(title)} 센터 기준 정보</h2>
          <p><strong>{escape(center_name)}</strong> 기준으로 {escape(center.name)} 학생 상담 흐름을 정리했습니다. 주소 자료는 상담 전 위치와 생활권을 확인하기 위한 참고 정보로 활용됩니다.</p>
          <p>주소: {escape(address)}</p>
          <p>운영 시간: {escape(hours)} · 상담은 학생 상황 확인 후 안내됩니다.</p>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Checklist</p>
              <h2>{escape(title)} 상담 전 체크리스트</h2>
            </div>
          </div>
          <div class="checklist-grid">
            <div class="check-item">{escape(profile['check_1'])}</div>
            <div class="check-item">{escape(profile['check_2'])}</div>
            <div class="check-item">{escape(center.name)} 학교 진도와 시험 범위, 수행평가 일정을 알려주시면 좋아요.</div>
            <div class="check-item">숙제·복습·플래너 실행이 끊기는 지점을 함께 확인합니다.</div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">FAQ</p>
              <h2>{escape(title)} 자주 묻는 질문</h2>
            </div>
          </div>
          <div class="panel soft-panel">
            {faq_html}
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Parent Review</p>
              <h2>{escape(center.name)} {escape(profile['review_heading_suffix'])}</h2>
            </div>
          </div>
          <div class="review-grid">
{review_html}
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Internal Links</p>
              <h2>{escape(center.name)} {escape(profile['related_heading_suffix'])}</h2>
            </div>
            <p class="section-desc">{escape(profile['internal_desc'])}</p>
          </div>
          <div class="local-link-grid child-link-grid">
              <a href="../index.html"><span>기본 안내</span><strong>{escape(center.title)}</strong><small>바로가기</small></a>
{related_links}
          </div>
        </div>
      </section>

{bottom_nav}

      <section class="section">
        <div class="container">
          <div class="cta-band">
            <p class="section-kicker">Consultation</p>
            <h2>{escape(title)} 상담 전, {escape(profile['cta_heading'])}</h2>
            <p>{escape(profile['cta_body'])}</p>
            <div class="hero-actions">
              <a class="button button-primary" href="tel:{PHONE_TEL}">전화 상담</a>
              <a class="button button-soft" href="../../../학습가이드/index.html">학습가이드 보기</a>
            </div>
          </div>
        </div>
      </section>
    </main>
{floating("../../../")}
{footer()}
  </div>
</body>
</html>
"""


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"source missing: {SOURCE_ROOT}")

    centers = collect_centers()
    if len(centers) != 371:
        raise SystemExit(f"expected 371 centers, got {len(centers)}")

    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    write_file(DEST_ROOT / "index.html", render_hub(centers))
    for center in centers:
        if not center.map_file:
            raise SystemExit(f"map missing in source: {center.name}")
        if not (ROOT / "assets" / "maps" / center.map_file).exists():
            raise SystemExit(f"map asset missing: {center.map_file} ({center.name})")
        if not (ROOT / "assets" / "centers" / "common" / center.main_image_file).exists():
            raise SystemExit(f"main image missing: {center.main_image_file}")
        write_file(DEST_ROOT / center.name / "index.html", render_center(center, centers))
        for slug in CHILD_SLUGS:
            write_file(DEST_ROOT / center.name / slug / "index.html", render_child_page(center, centers, slug))

    print(f"generated hub + {len(centers)} center pages + {len(centers) * len(CHILD_SLUGS)} child pages")


if __name__ == "__main__":
    main()
