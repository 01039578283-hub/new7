from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class ArticleSection:
    anchor: str
    kicker: str
    heading: str
    paragraphs: tuple[str, ...]
    schema_label: str


def _rng(key: str) -> random.Random:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _choice(items: list[str], key: str) -> str:
    return items[_rng(key).randrange(len(items))]


def _particle(text: str, consonant: str, vowel: str) -> str:
    for char in reversed(text.strip()):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            return consonant if (code - 0xAC00) % 28 else vowel
    return vowel


def _with_particle(text: str, consonant: str, vowel: str) -> str:
    return f"{text}{_particle(text, consonant, vowel)}"


def build_unique_article(
    *,
    page_key: str,
    title: str,
    area_phrase: str,
    town: str,
    page_role: str,
    subject_pair: str,
    primary: str,
    secondary: str,
    primary_scope: str,
    secondary_scope: str,
    school_context: str,
    center_reference: str,
    scenario: str,
) -> tuple[ArticleSection, ...]:
    """Build a deterministic, evidence-bounded manuscript for one local page.

    The banks deliberately vary reasoning and paragraph structure, not only the
    town name.  Every factual reference is supplied by the verified CSV context;
    the function never invents schools, landmarks, outcomes, or operating rules.
    """

    key = f"local-article-v2::{page_key}::{page_role}"
    title_obj = _with_particle(title, "을", "를")
    role_obj = _with_particle(page_role, "을", "를")
    pair_obj = _with_particle(subject_pair, "을", "를")
    primary_topic = _with_particle(primary, "은", "는")
    secondary_topic = _with_particle(secondary, "은", "는")
    primary_and = _with_particle(primary, "과", "와")
    center_and = _with_particle(center_reference, "과", "와")
    center_obj = _with_particle(center_reference, "을", "를")
    primary_scope_obj = _with_particle(primary_scope, "을", "를")
    primary_scope_and = _with_particle(primary_scope, "과", "와")
    secondary_scope_obj = _with_particle(secondary_scope, "을", "를")
    secondary_scope_subj = _with_particle(secondary_scope, "이", "가")
    school_context_obj = _with_particle(school_context, "을", "를")

    openers = [
        f"{title_obj} 알아볼 때 첫 기준은 수업 횟수보다 학생의 현재 기록을 얼마나 구체적으로 읽어 주는지입니다. {area_phrase}에서 상담을 준비한다면 최근 결과만 보지 말고, 지금 배우는 단원과 혼자 해결할 수 있는 범위를 먼저 나누어 보는 편이 좋습니다.",
        f"{title} 선택은 ‘어디까지 진도를 나갔는가’보다 ‘어디에서 풀이와 복습이 멈추는가’를 확인하는 일에서 시작합니다. {town} 학생에게 필요한 계획도 현재 교재, 시험지, 과제 기록을 함께 놓고 볼 때 비로소 현실적으로 정리할 수 있습니다.",
        f"{area_phrase}에서 {role_obj} 찾는다면 성적표 한 장만으로 수업 방향을 결정하기 어렵습니다. {title} 상담에서는 최근 학습 기록을 과목별로 펼쳐 놓고, 이해한 내용과 다시 설명하기 어려운 내용을 분리하는 과정이 우선입니다.",
        f"{title} 페이지가 바로 답해야 할 질문은 ‘우리 아이가 지금 무엇부터 다시 해야 하는가’입니다. 답을 찾으려면 {town} 학생의 학교 진도, 사용 교재, 오답 재풀이 여부를 같은 시간선 위에서 확인해야 합니다.",
        f"{title_obj} 비교할 때는 홍보 문구보다 진단 절차를 살펴보는 것이 안전합니다. {area_phrase} 학생의 현재 단원과 학습 습관을 기록으로 확인하고, 그 결과가 다음 주 계획으로 이어지는지가 핵심 기준입니다.",
        f"{town}에서 {page_role} 상담을 준비하는 학부모라면 공부량을 늘리는 방법보다 먼저 학습이 끊기는 지점을 찾아야 합니다. {title} 안내는 확인된 자료를 토대로 시작점과 재학습 순서를 구분하는 데 초점을 둡니다.",
        f"{title} 상담의 출발점은 학생을 막연히 ‘잘한다’거나 ‘부족하다’고 평가하는 데 있지 않습니다. {area_phrase}에서 실제로 사용하는 교재와 최근 실행 기록을 살펴, 설명 가능한 부분과 도움이 필요한 부분을 구체적으로 나눕니다.",
        f"{title_obj} 찾는 검색 의도에는 위치뿐 아니라 관리 방식에 대한 질문도 들어 있습니다. {town} 학생의 시험 준비와 평소 복습이 따로 움직이지 않도록 현재 자료를 먼저 읽고 우선순위를 세우는 과정이 필요합니다.",
        f"{area_phrase}의 {page_role} 선택 기준은 학생마다 달라질 수 있지만 확인 순서는 분명합니다. {title} 상담에서는 현재 단원, 과제 완료 상태, 반복되는 오답을 먼저 보고 수업과 자기학습 사이의 연결을 점검합니다.",
        f"{title} 안내에서 가장 먼저 정리할 것은 ‘더 많이 풀기’가 아니라 ‘어떤 문제를 왜 다시 풀어야 하는가’입니다. {town} 학생이 가진 최근 자료를 기준으로 학습 공백의 위치와 완료 기준을 함께 찾아야 합니다.",
        f"{role_obj} 고를 때 결과만 빠르게 비교하면 학생에게 필요한 과정이 가려질 수 있습니다. {title} 상담은 {area_phrase} 학생의 실제 기록에서 출발해 진단, 계획, 실행 확인, 오답 재학습의 순서를 세우는 방식이 적절합니다.",
        f"{title_obj} 알아보는 학부모에게 필요한 것은 추상적인 약속보다 확인 가능한 기준입니다. {town} 학생의 현재 교재와 최근 시험 자료를 바탕으로 무엇을 유지하고 무엇을 다시 배울지 구분해야 다음 계획이 선명해집니다.",
    ]

    evidence_paragraphs = [
        f"이 페이지는 {center_and} {school_context}처럼 제공 자료에서 확인할 수 있는 범위만 사용합니다. {title}에서는 학교별 출제 경향이나 통학 환경을 임의로 단정하지 않고, 학생이 가져온 진도표와 시험 범위를 현재 교재와 대조하도록 안내합니다.",
        f"지역 정보는 {center_obj} 기준으로 확인했고, 학교 학습은 {school_context}를 직접 살펴보는 방식으로 구분했습니다. {title} 안내에는 확인되지 않은 생활권이나 학교 특징을 덧붙이지 않기 때문에 학생의 실제 자료가 판단의 중심이 됩니다.",
        f"{town} 관련 사실은 {center_reference}에서 확인되는 내용에 한정했습니다. 학습 범위 역시 {school_context}를 토대로 점검하며, 자료가 없는 부분은 추측하지 않고 상담 시 재학 학교와 현재 진도를 다시 확인합니다.",
        f"상담 전 근거가 되는 두 축은 {center_reference}, 그리고 {school_context}입니다. {town} 상담에서 이 둘을 최근 시험지·교재·플래너와 맞춰 보면 위치 정보와 학습 정보가 섞이지 않고, 필요한 보완 순서를 따로 정리할 수 있습니다.",
        f"{title} 안내에는 검증되지 않은 학교명이나 성적 결과를 넣지 않았습니다. {center_obj} 지역 기준으로 삼고 {school_context}를 학생별 확인 자료로 사용해, 실제 기록이 있을 때만 구체적인 진도와 시험 범위를 판단합니다.",
        f"확인 가능한 정보는 {center_and} {school_context}입니다. 따라서 같은 {town} 학생이라도 재학 학교와 사용 교재가 다르면 상담 내용이 달라질 수 있으며, 페이지의 설명을 개인별 결과로 단정해서는 안 됩니다.",
        f"{area_phrase}에 관한 설명은 제공된 센터 자료를 벗어나지 않습니다. {school_context}도 참고 목록이 아니라 학생이 가져온 실제 자료와 함께 확인해야 하므로, 상담에서는 학교명보다 현재 배우는 범위와 수행 기록을 먼저 묻습니다.",
        f"이 원고의 지역 근거는 {center_reference}이며 학습 근거는 {school_context}입니다. 두 자료를 분리해 확인하면 주소나 학교명이 단순 키워드로 반복되는 것을 피하고, 학생의 현재 상태를 설명하는 정보로 사용할 수 있습니다.",
        f"{title} 상담 자료는 지역 근거인 {center_reference}, 학습 근거인 {school_context_obj} 바탕으로 구성됩니다. 따라서 {town} 원고에는 제공 자료에 없는 학교 운영 방식, 주변 시설, 예상 성적을 만들지 않으며 필요한 내용은 실제 상담에서 확인합니다.",
        f"페이지에 반영한 사실 정보는 {center_reference}, {school_context} 두 범주로 나뉩니다. {town} 페이지는 지역 사실과 학생별 학습 사실을 섞어 일반화하지 않고, 현재 교재와 최근 기록이 있을 때 구체적인 학습 순서를 제안합니다.",
    ]

    scenario_paragraphs = [
        f"예를 들어 {scenario}라면 문제 수를 바로 늘리기보다 멈춘 단계가 개념 이해인지, 풀이 적용인지, 재확인 부족인지부터 나눠야 합니다. {town} 학생의 기록에서 같은 현상이 반복되는지 확인한 뒤 첫 주의 완료 기준을 작게 정합니다.",
        f"학생에게 {scenario}가 보인다면 의지 부족으로 단정하지 않는 것이 중요합니다. {title} 상담에서는 시작 시간, 교재 범위, 오답 재풀이 시점을 따로 확인해 실제로 바꿀 수 있는 행동 한두 가지를 먼저 선택합니다.",
        f"{scenario}에는 진도 추가보다 기록 점검이 먼저입니다. {area_phrase} 학생의 최근 과제와 시험지를 시간 순서로 놓고 어느 단계에서 계획과 실행이 달라졌는지 확인하면, 필요한 보완이 설명 수업인지 반복 연습인지 구분하기 쉬워집니다.",
        f"{town} 학생이 {scenario}에 해당하는지는 한 번의 시험만으로 판단하지 않습니다. 교재의 풀이 흔적, 플래너 완료 표시, 며칠 뒤 재풀이 결과를 함께 보아 같은 어려움이 이어지는지 확인해야 합니다.",
        f"상담에서 {scenario}가 확인되면 공부 시간을 더 확보하라는 말만으로는 부족합니다. {title}에서는 해야 할 분량, 끝났다고 판단할 기준, 다시 확인할 날짜를 구분해 학생이 스스로 실행 결과를 남길 수 있게 계획합니다.",
        f"{scenario}일 때는 학생이 알고 있는 내용과 시험에서 꺼내 쓰는 능력 사이에 간격이 있는지 살펴봅니다. {area_phrase}에서 가져온 실제 학습 기록을 활용해 설명, 적용, 검산, 재풀이 중 어디가 비어 있는지 확인합니다.",
        f"{town} 학생의 상담 기록에서 {scenario}가 드러난다면 과목 전체를 다시 시작할 필요는 없습니다. 막힌 단원과 문제 유형을 좁힌 뒤, 먼저 복구할 부분과 현재 진도를 유지할 부분을 나누는 것이 현실적입니다.",
        f"{scenario}는 플래너의 계획량과 실제 완료량을 비교할 때 더 선명하게 보입니다. {title} 상담에서는 계획을 지켰는지만 묻지 않고, 완료 표시가 학습 결과를 제대로 보여 주는지까지 확인합니다.",
        f"학생이 {scenario}라면 같은 설명을 반복해서 듣는 것보다 스스로 풀이를 다시 구성하는 시간이 필요할 수 있습니다. {town}의 실제 학교 범위와 교재를 기준으로 짧은 확인 문제와 재풀이 간격을 조정합니다.",
        f"{scenario}가 반복될 때는 원인을 한 과목의 성적만으로 해석하지 않습니다. {area_phrase} 학생의 수면이나 생활 습관을 임의로 추정하지 않고, {title}에서는 과제·오답·플래너 기록 안에서 실행이 끊긴 지점을 찾습니다.",
        f"{title} 상담에서 {scenario}를 확인했다면 가장 먼저 바꿀 것은 계획의 표현입니다. ‘{primary} 공부’처럼 넓은 문구를 교재, 단원, 문제 번호, 재확인 날짜로 쪼개야 학생도 완료 여부를 판단할 수 있습니다.",
        f"{town} 학생에게 {scenario}가 나타날 경우 현재 진도와 복습을 무조건 동시에 늘리지 않습니다. 시험 일정과 남은 범위를 확인한 뒤, 회복할 공백과 유지할 학습을 서로 다른 칸으로 관리합니다.",
    ]

    diagnosis_paragraphs = [
        f"{primary_topic} {primary_scope_obj} 기준으로 학생이 혼자 설명하고 다시 수행할 수 있는 범위를 확인합니다. {secondary_topic} {secondary_scope_subj} 끊기지 않는지 별도로 살펴, {subject_pair}의 부담이 한쪽으로 몰리지 않도록 시작 순서를 정합니다.",
        f"{pair_obj} 한 묶음으로 평가하지 않습니다. 먼저 {primary}에서 {primary_scope_obj} 점검하고, 이어 {secondary}의 {secondary_scope_obj} 확인해 두 영역이 각각 어떤 도움을 필요로 하는지 나눕니다.",
        f"{page_role} 진단에서는 {primary}의 결과만 보지 않고 {primary_scope}의 과정을 확인합니다. 그다음 {secondary_scope_obj} 점검해 {secondary} 학습이 현재 계획 안에서 유지되는지 살펴봅니다.",
        f"{title}의 과목 기준은 우선순위와 병행 항목을 구분하는 데 있습니다. {primary_topic} {primary_scope}부터, {secondary_topic} {secondary_scope}부터 확인한 뒤 두 계획이 같은 주간 일정에서 충돌하지 않게 조정합니다.",
        f"진단표에는 {primary_scope_and} {secondary_scope_obj} 서로 다른 항목으로 기록합니다. 이렇게 나누면 {subject_pair} 가운데 무엇을 먼저 보완하고 무엇을 꾸준히 유지할지 학부모도 확인하기 쉽습니다.",
        f"{town} 학생의 {page_role} 계획은 과목 수보다 학습 단계에 따라 달라집니다. {primary_scope}의 안정 여부를 먼저 보고, {secondary_scope_subj} 누적되는지를 이어서 확인해 실제 가능한 분량을 정합니다.",
        f"{primary_topic} ‘안다’는 대답보다 {primary_scope_obj} 혼자 수행할 수 있는지로 판단합니다. {secondary_topic} {secondary_scope}의 최근 기록을 확인해 복습이 특정 시기에만 몰리지 않는지도 살펴봅니다.",
        f"{title} 상담에서는 {primary_and} {secondary}의 점수를 단순 비교하지 않습니다. {primary_scope_and} {secondary_scope} 가운데 학생이 멈추는 세부 단계가 무엇인지 찾아 각각 다른 완료 기준을 둡니다.",
        f"{subject_pair} 관리의 핵심은 같은 시간을 똑같이 나누는 것이 아닙니다. {primary_scope_obj} 먼저 살피고, {secondary_scope_obj} 근거로 시험 일정 전까지 필요한 우선순위를 조정합니다.",
        f"{page_role} 학습 설계는 {primary}의 기초 확인과 {secondary}의 누적 관리를 동시에 보되 순서를 구분합니다. {primary_scope_obj} 점검한 결과와 {secondary_scope}의 실행 기록이 실제 주간 계획에 반영되어야 합니다.",
        f"{town} 학생에게 필요한 {subject_pair} 계획은 최근 기록에서 출발합니다. {primary_scope} 중 재설명이 필요한 항목과 {secondary_scope} 중 꾸준히 유지할 항목을 분리하면 과도한 분량을 피할 수 있습니다.",
        f"{title}에서는 {primary_and} {secondary}를 모두 공부했다는 사실보다 무엇을 남겼는지를 확인합니다. {primary_scope}의 결과물과 {secondary_scope}의 누적 기록이 다음 수업에서 다시 사용되는지가 중요한 기준입니다.",
    ]

    execution_paragraphs = [
        f"계획은 진단 결과를 교재·단원·분량으로 바꾸는 단계에서 구체화됩니다. {title}에서는 완료 표시 뒤에 짧은 확인 문제를 두고, 틀린 문항은 원인 기록과 재풀이 날짜를 남겨 다음 점검 때 실제 변화가 있었는지 확인합니다.",
        f"{title}의 실행 순서는 ‘진단→이번 주 계획→수업과 과제→오답 재학습’으로 연결합니다. {town} 학생의 플래너에는 해야 할 양뿐 아니라 끝났다고 볼 기준을 적고, 다음 확인 때 계획과 결과의 차이를 다시 조정합니다.",
        f"{page_role} 계획은 한 번 작성하고 끝나는 시간표가 아닙니다. {area_phrase} 학생이 실제로 끝낸 범위와 남긴 오답을 확인해 다음 분량을 줄이거나 늘리고, 재풀이 결과가 확인된 뒤 새 진도로 이동합니다.",
        f"{title}의 실행 관리는 학습량보다 연결 상태를 봅니다. 수업에서 이해한 내용이 과제로 이어지고, 과제에서 발견한 오답이 며칠 뒤 재풀이까지 이어졌는지를 확인해야 계획이 실제 공부 기록이 됩니다.",
        f"첫 계획은 학생이 수행 가능한 작은 단위로 시작합니다. {town}에서 가져온 시험 범위와 현재 교재를 기준으로 우선순위를 정하고, 완료 기록이 쌓이면 다음 주에 난도와 분량을 다시 조정합니다.",
        f"{title}에서 진단 결과가 좋더라도 실행 기록이 남지 않으면 관리 방향을 평가하기 어렵습니다. 교재 쪽수, 문제 번호, 오답 이유, 다시 푼 날짜를 연결해 학생과 학부모가 같은 기준으로 진행 상황을 확인하도록 합니다.",
        f"{subject_pair} 계획은 시험 직전 목록과 평소 누적 목록을 나누어 관리합니다. {area_phrase} 학생의 일정에 맞춰 긴급한 범위와 꾸준히 유지할 항목을 구분하고, 어느 한쪽도 기록 없이 밀리지 않도록 점검합니다.",
        f"실행 확인은 ‘했는가’ 한마디로 끝내지 않습니다. {title}에서는 학생이 풀이 과정을 설명할 수 있는지, 같은 유형을 다시 풀 수 있는지, 플래너의 완료 표시와 결과가 일치하는지 차례로 봅니다.",
        f"{town} 학생의 주간 계획에는 복습과 새 진도의 경계를 표시합니다. 앞 단원의 공백을 보완하는 날과 현재 학교 범위를 따라가는 날을 구분하고, 오답 재학습을 완료한 뒤 다음 단계로 넘어갑니다.",
        f"{page_role} 수업 후에는 피드백이 다음 행동으로 번역되어야 합니다. ‘더 꼼꼼히’라는 표현 대신 검산할 지점, 다시 읽을 문장, 재풀이할 번호처럼 학생이 바로 실행할 수 있는 기준을 남깁니다.",
        f"{title} 학습 흐름은 계획의 정확성보다 수정 가능성을 중요하게 봅니다. 예상보다 오래 걸린 단원은 이유를 기록해 분량을 바꾸고, 빠르게 끝낸 단원도 확인 문제를 거쳐 실제 이해 여부를 점검합니다.",
        f"{area_phrase} 학생의 실행 기록은 상담에서 정한 우선순위를 검증하는 자료가 됩니다. 일주일 뒤 완료율만 보지 않고 오답의 종류와 재풀이 결과까지 살펴, 다음 계획의 순서와 밀도를 조정합니다.",
    ]

    parent_paragraphs = [
        f"학부모는 ‘몇 문제를 풀었는가’와 함께 ‘틀린 이유를 설명하고 다시 풀 수 있는가’를 확인해 보세요. {title} 상담 뒤에는 학생이 오늘의 범위를 말할 수 있는지, 플래너와 실제 교재 기록이 일치하는지를 같은 기준으로 살펴보는 것이 좋습니다.",
        f"상담 후 확인할 변화는 단기간의 점수 약속이 아닙니다. {town} 학생이 해야 할 일을 더 구체적으로 말하는지, 질문을 미루지 않는지, 오답 재확인 날짜를 지키는지처럼 관찰 가능한 행동으로 판단해야 합니다.",
        f"{title_obj} 선택한 뒤에는 수업 설명보다 학생의 기록이 달라지는지를 보아야 합니다. 교재의 풀이 흔적, 과제 완료 기준, 재풀이 결과가 이어지면 다음 상담에서도 무엇을 유지하고 조정할지 분명해집니다.",
        f"{town} 상담 뒤 학부모가 물어볼 질문은 ‘성적이 언제 오르는가’보다 ‘이번 주 진단 결과가 어떤 계획으로 바뀌었는가’에 가깝습니다. {area_phrase} 학생의 실제 수행 자료를 함께 보면 과장된 기대 없이 관리 과정을 확인할 수 있습니다.",
        f"{town} 학생의 변화는 질문의 내용에서도 확인할 수 있습니다. 모른다는 말에서 끝나지 않고 막힌 단원과 풀이 단계를 설명하는지, 다음 재풀이 시점을 스스로 알고 있는지 살펴보면 학습 주도성이 조금씩 형성되는 과정을 볼 수 있습니다.",
        f"{page_role} 상담에서는 학부모와 학생이 같은 완료 기준을 공유하는 것이 중요합니다. {title} 페이지의 기준을 참고하되 실제 수업 가능 여부와 세부 운영은 상담에서 확인하고, 확인되지 않은 결과를 미리 약속받지 않는 편이 안전합니다.",
        f"상담 뒤에는 계획표가 예쁜지보다 실제 기록이 남는지를 확인하세요. {title} 관리가 맞는 학생이라면 교재·단원·분량·재확인 날짜가 구체화되고, 다음 점검에서 그 결과를 근거로 계획을 수정할 수 있어야 합니다.",
        f"{area_phrase}에서 학원을 비교할 때는 같은 질문을 사용하면 판단이 쉬워집니다. 진단 근거는 무엇인지, {subject_pair}의 우선순위를 어떻게 나눴는지, 오답을 언제 다시 확인하는지 물어보고 학생의 기록과 답변이 일치하는지 보세요.",
        f"{title} 상담의 적합성은 학생이 관리 절차를 이해하는지로도 판단할 수 있습니다. 오늘 배운 내용, 남은 공백, 다음 과제, 재풀이 날짜를 학생 자신의 말로 설명할 수 있다면 계획이 단순 지시를 넘어 실행 기준으로 자리 잡고 있는 것입니다.",
        f"{town} 학부모 피드백은 학생을 재촉하는 목록보다 확인 질문에 가까워야 합니다. 이번 주 가장 어려웠던 단계와 다시 확인할 문제를 묻고, 답이 모호하면 담당 선생님과 완료 기준을 다시 맞추는 것이 좋습니다.",
        f"{title} 선택 후에는 한 번의 결과보다 계획과 점검이 반복되는 구조를 보세요. {primary_and} {secondary}에서 각각 남은 과제가 무엇인지, 오답 재학습이 끝났는지, 다음 진도와 연결되었는지를 확인하면 관리의 지속성을 판단할 수 있습니다.",
        f"마지막 판단 기준은 학생에게 필요한 지원이 구체적으로 설명되는가입니다. {area_phrase} 학생의 확인된 자료를 근거로 현재 할 일과 다음 점검 시점이 제시되어야 하며, 성적 상승이나 입시 결과를 단정하는 표현은 상담 기준으로 삼지 않습니다.",
    ]

    headings_1 = [
        f"{title}, 기록에서 출발점을 찾는 방법",
        f"{town} 학습 자료를 먼저 읽어야 하는 이유",
        f"{title} 상담 전 확인할 실제 근거",
        f"현재 위치부터 정리하는 {town} 학습 상담",
        f"{area_phrase}에서 학원을 비교하는 첫 기준",
        f"{title} 선택을 기록으로 판단하기",
    ]
    headings_2 = [
        f"{subject_pair}의 막힌 단계와 실행 순서",
        f"{town} 학생에게 맞는 진단과 주간 계획",
        f"{primary} 우선순위와 {secondary} 병행 기준",
        f"진단에서 오답 재학습까지 연결하는 방법",
        f"{page_role} 계획을 학생 기록에 맞추기",
        f"{title}의 과목별 관리 기준",
    ]
    headings_3 = [
        f"{title} 상담 후 학부모가 확인할 변화",
        f"계획이 실제 실행으로 이어지는지 보는 기준",
        f"{town} 학생의 학습 기록을 함께 확인하는 법",
        f"결과 약속보다 관리 과정을 확인하세요",
        f"학생과 학부모가 공유할 완료 기준",
        f"{page_role} 선택 후 점검할 질문",
    ]
    kickers = [
        ("Verified Starting Point", "Learning Sequence", "Parent Check"),
        ("Local Evidence", "Study Design", "Progress Review"),
        ("Record First", "Plan & Practice", "Family Guide"),
        ("Consultation Notes", "Action Plan", "After Consultation"),
        ("Evidence Based", "Learning Flow", "Parent Questions"),
        ("Current Position", "Coaching Route", "Review Standard"),
    ]
    kicker_set = kickers[_rng(f"{key}::kickers").randrange(len(kickers))]

    return (
        ArticleSection(
            anchor="local-article-evidence",
            kicker=kicker_set[0],
            heading=_choice(headings_1, f"{key}::heading-1"),
            paragraphs=(
                _choice(openers, f"{key}::opener"),
                _choice(evidence_paragraphs, f"{key}::evidence"),
            ),
            schema_label="확인된 자료와 학습 출발점",
        ),
        ArticleSection(
            anchor="local-article-plan",
            kicker=kicker_set[1],
            heading=_choice(headings_2, f"{key}::heading-2"),
            paragraphs=(
                _choice(scenario_paragraphs, f"{key}::scenario"),
                _choice(diagnosis_paragraphs, f"{key}::diagnosis"),
                _choice(execution_paragraphs, f"{key}::execution"),
            ),
            schema_label="학생 상황별 진단과 실행 계획",
        ),
        ArticleSection(
            anchor="local-article-review",
            kicker=kicker_set[2],
            heading=_choice(headings_3, f"{key}::heading-3"),
            paragraphs=(_choice(parent_paragraphs, f"{key}::parent"),),
            schema_label="학부모 상담 후 확인 기준",
        ),
    )


def article_plain_text(sections: tuple[ArticleSection, ...]) -> str:
    chunks: list[str] = []
    for section in sections:
        chunks.append(section.heading)
        chunks.extend(section.paragraphs)
    return "\n".join(chunks)


def render_article_sections(sections: tuple[ArticleSection, ...]) -> str:
    articles: list[str] = []
    for section in sections:
        paragraphs = "\n".join(f"              <p>{escape(text)}</p>" for text in section.paragraphs)
        articles.append(
            f'''          <article class="story-panel local-article-panel" id="{escape(section.anchor)}">
            <div class="story-copy">
              <p class="section-kicker">{escape(section.kicker)}</p>
              <h2>{escape(section.heading)}</h2>
{paragraphs}
            </div>
          </article>'''
        )
    return f'''      <section class="section local-article" data-content-role="unique-copy" aria-label="페이지별 학습 설계 원고">
        <div class="container">
{chr(10).join(articles)}
        </div>
      </section>'''


def article_section_nodes(page_url: str, sections: tuple[ArticleSection, ...], article_id: str) -> list[dict[str, object]]:
    return [
        {
            "@type": "WebPageElement",
            "@id": f"{page_url}#{section.anchor}",
            "url": f"{page_url}#{section.anchor}",
            "name": section.heading,
            "description": section.paragraphs[0],
            "isPartOf": {"@id": article_id},
            "inLanguage": "ko-KR",
        }
        for section in sections
    ]


def article_section_itemlist(page_url: str, title: str, sections: tuple[ArticleSection, ...]) -> dict[str, object]:
    return {
        "@type": "ItemList",
        "@id": f"{page_url}#article-sections",
        "name": f"{title} 페이지별 학습 설계 목차",
        "numberOfItems": len(sections),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": section.heading,
                "url": f"{page_url}#{section.anchor}",
            }
            for index, section in enumerate(sections, 1)
        ],
    }
