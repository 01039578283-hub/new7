import unittest
from personalize_title_suffixes import (
    learning_blocks, candidates, masked, replace_titles, title_of, plan, eligible,
    hub_copy, clean,
)

def sample(body,subject="combined",stage="high"):
    source='<title>명일동 학원 | 이전 제목</title><main><article class="academy-article">'+body+'</article></main>'
    page=dict(source=source,prefix="명일동 학원",rel="과목별학원/sample/명일동/index.html",kind="subject",group="sample",
              stage=stage,subject=subject,blocks=learning_blocks(source,"subject"))
    page["candidates"]=candidates(page)
    return page

class TitleTests(unittest.TestCase):
    def test_title_only_and_attribute_spacing(self):
        source='<title>명일동 | 기존</title>\r\n<meta property="og:title" content = \'이전\'><meta name="description" content="기존 설명"><h1>그대로</h1>'
        updated=replace_titles(source,"명일동 | 어휘 & 복습")
        self.assertIn("content = '명일동 | 어휘 &amp; 복습'",updated)
        self.assertEqual(masked(source),masked(updated))
        self.assertEqual(title_of(updated),"명일동 | 어휘 & 복습")
        self.assertIn('<h1>그대로</h1>',updated)

    def test_wrapped_intro_priority(self):
        p=sample('<div class="academy-intro-answer"><p>긴 문장에서 핵심 구조를 놓치는 학생입니다.</p></div><section class="academy-article-section"><p>주간 계획과 과제 분량을 정리합니다.</p></section>')
        self.assertEqual(p["blocks"][0]["weight"],6)
        self.assertGreater(p["candidates"]["긴 문장 해석"]["score"],p["candidates"]["주간 학습 흐름"]["score"])

    def test_mixed_address_keeps_learning_sentence(self):
        p=sample('<div class="academy-intro-answer"><p>첫 식을 세우지 못하는 학생입니다. 제공 주소는 서울 강동구입니다.</p></div>',"math")
        self.assertTrue(any("첫 식" in b["text"] for b in p["blocks"]))
        self.assertFalse(any("제공 주소" in b["text"] for b in p["blocks"]))

    def test_exclude_review_nav_hidden_and_facility(self):
        source='<main><article class="academy-article"><div class="academy-intro-answer"><p>수학은 첫 식을 세우는 과정이 중요합니다.</p></div><nav><p>분수 개념을 확인합니다.</p></nav><div style="display: none;"><p>분수 개념을 확인합니다.</p></div><section class="academy-local-context"><p>분수 개념을 확인합니다.</p></section><p>사물함과 분수 개념은 별도입니다.</p></article><section class="academy-review-section"><p>분수 개념을 확인했습니다.</p></section></main>'
        blocks=learning_blocks(source,"subject")
        self.assertTrue(blocks)
        self.assertFalse(any("분수" in b["text"] for b in blocks))

    def test_both_lead_subjects_are_reflected(self):
        p=sample('<div class="academy-intro-answer"><p>긴 문장에서 핵심 구조를 놓치고 수학은 첫 식을 세우지 못하는 학생입니다. 시험이 가까워져야 공부량을 늘립니다.</p></div>')
        plan([p])
        self.assertEqual({x["subject"] for x in p["evidence"]},{"math","english"})

    def test_opposite_subject_is_excluded(self):
        p=sample('<div class="academy-intro-answer"><p>첫 식을 세우고 검산하며 문장 구조와 독해 근거를 확인합니다.</p></div>',"math")
        self.assertTrue(p["candidates"])
        self.assertFalse(any(c["subject"]=="english" for c in p["candidates"].values()))

    def test_grade_rules(self):
        p=dict(subject="general",stage="elementary")
        self.assertFalse(eligible(p,"내신·모의고사 구분",""))
        self.assertFalse(eligible(p,"수행평가 준비",""))
        self.assertTrue(eligible(p,"숙제 시작 습관",""))

    def test_no_fabricated_fallback(self):
        p=sample('<div class="academy-intro-answer"><p>제공 주소와 등록번호만 확인합니다.</p></div>')
        self.assertFalse(p["candidates"])

    def test_name_does_not_randomize_topic(self):
        first=sample('<div class="academy-intro-answer"><p>명일동에서 긴 문장 해석과 첫 식을 세우는 과정을 확인합니다.</p></div>')
        second=sample('<div class="academy-intro-answer"><p>다른동에서 긴 문장 해석과 첫 식을 세우는 과정을 확인합니다.</p></div>')
        second["prefix"]="다른동 학원"
        plan([first,second])
        self.assertEqual(first["suffix"],second["suffix"])

    def test_general_learning_topic_is_allowed_for_math(self):
        p=sample('<div class="academy-intro-answer"><p>문항별 시간 배분을 점검하는 순서입니다.</p></div>',"math")
        plan([p])
        self.assertIn("시험 시간 배분",p["suffix"])

    def test_short_sentence_is_not_automatically_writing(self):
        p=sample('<div class="academy-intro-answer"><p>짧은 문장부터 근거를 말하게 한 뒤 지문 단위로 적용합니다.</p></div>',"english")
        self.assertNotIn("짧은 문장 쓰기",p["candidates"])

    def test_grammar_application_is_not_math_evidence(self):
        p=sample('<div class="academy-intro-answer"><p>문법 개념을 배워도 실전 문항에서 적용 순서가 흐릿한 학생입니다.</p></div>',"general")
        self.assertNotIn("개념의 문제 적용",p["candidates"])
        self.assertIn("문법의 문장 적용",p["candidates"])

    def test_national_case_has_priority(self):
        source='<main><section class="local-article" data-content-role="unique-copy"><article class="local-article-panel" id="local-article-plan"><div class="story-copy"><p>질문을 미루다가 한 단원의 공백이 다음 단원까지 이어지는 경우입니다.</p><p>플래너 실행과 과제 분량을 점검합니다.</p></div></article></section><section class="reviews"><p>분수 개념을 확인했습니다.</p></section></main>'
        p=dict(subject="general",stage="all",blocks=learning_blocks(source,"center"))
        found=candidates(p)
        self.assertIn("질문과 단원 공백 점검",found)
        self.assertNotIn("분수 개념 확인",found)
        self.assertGreater(found["질문과 단원 공백 점검"]["score"],found["플래너 실행 점검"]["score"])

    def test_learning_review_panel_is_not_testimonial(self):
        source='<main><section data-content-role="unique-copy"><article class="local-article-panel" id="local-article-review"><p>과제 분량 조절과 다음 복습 날짜를 점검합니다.</p></article></section></main>'
        self.assertTrue(learning_blocks(source,"center"))

    def test_hesitating_alone_is_not_independent_solving(self):
        p=sample('<p>질문하기 전 혼자 버티다가 풀이 시간이 길어지는 학생입니다.</p>',"math")
        self.assertNotIn("독립 풀이 확인",p["candidates"])

    def test_recall_topics_do_not_repeat_in_one_title(self):
        p=sample('<p>단어 복습 뒤 회상 결과와 문장 구조 이해를 확인합니다.</p>',"english")
        plan([p])
        self.assertFalse("어휘 인출과 복습" in p["suffix"] and "배운 내용 회상" in p["suffix"])

    def test_school_commute_is_not_review_evidence(self):
        p=sample('<p>학교 진도와 생활 동선을 함께 맞출 수 있습니다.</p>',"english")
        self.assertNotIn("학교 진도와 복습",p["candidates"])

    def test_repeated_intro_does_not_outrank_individual_case(self):
        pages=[]
        for i in range(20):
            extra='<p>계산 실수가 많은 학생이 문제 조건을 표시합니다.</p>' if i==0 else '<p>단원 간 개념 연결과 과제 실행 기록을 확인합니다.</p>'
            p=sample('<p>모든 수업에서 검산 습관을 확인합니다.</p>'+extra,"math")
            p["prefix"]=f"지역{i} 수학학원"
            p["rel"]=f"과목별학원/수학학원/지역{i}/index.html"
            pages.append(p)
        plan(pages)
        self.assertIn("계산 실수 구분",pages[0]["suffix"])
        self.assertNotIn("검산 습관",pages[0]["suffix"])
        expected=[p["after"] for p in pages]
        plan(pages)
        self.assertEqual(expected,[p["after"] for p in pages])

    def test_long_passage_concentration_is_not_sentence_parsing(self):
        p=sample('<p>긴 지문이 나오면 집중이 흔들리는 학생은 오답을 다시 확인합니다.</p>',"english","elementary")
        plan([p])
        self.assertIn("긴 지문 읽기 집중",p["suffix"])
        self.assertNotIn("긴 문장 해석",p["suffix"])

    def test_hub_evidence_is_one_contiguous_visible_paragraph(self):
        source='<main><header class="academy-hero"><div class="academy-hero-copy"><p>ENGLISH DIRECTORY</p><h1>지역별 영어학원 안내</h1><p>371개 동네의 학습 기준과 센터 정보를 정리했습니다.</p></div></header></main>'
        text=hub_copy(source,["371개 동네","학습 기준","센터 정보"])
        self.assertIn(text,clean(source))
        self.assertNotIn("DIRECTORY",text)

if __name__=="__main__":
    unittest.main()
