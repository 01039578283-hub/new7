from __future__ import annotations

import unittest

from tools import generate_subject_pages as generator


def context(
    *, schools: list[str] | None = None, grades: str = "", level: str = "고등학생",
) -> dict[str, object]:
    return {
        "seed": "test-category|test-locality",
        "title": "가경동 고등학생 수학학원",
        "locality": "가경동",
        "region": "충청 청주시",
        "center": "와와학습코칭센터 가경점",
        "address": "충북 청주시 흥덕구 서현북로 18 2층",
        "schools": schools or [],
        "grades": grades,
        "level": level,
        "subject": "수학",
        "category": "고등학생수학학원",
        "reference_terms": (),
        "learning_focus": "풀이 근거 보완",
    }


class SchoolFactGuardTests(unittest.TestCase):
    def test_school_list_supports_space_and_middle_dot_separators(self) -> None:
        self.assertEqual(
            generator.split_school_names("이화초 가내초·자란초"),
            ["이화초", "가내초", "자란초"],
        )

    def test_generic_availability_note_is_not_a_school_entity(self) -> None:
        self.assertEqual(generator.split_school_names("지역내 모든 고등학교 가능"), [])

    def test_ordinary_words_ending_in_school_suffix_syllables_are_not_schools(self) -> None:
        self.assertEqual(
            generator.school_names_in_text("광고보다 기록을 참고하고 30초 안에 확인합니다."),
            [],
        )

    def test_road_name_prefix_is_not_mistaken_for_school(self) -> None:
        self.assertNotIn("갈매중", generator.school_like_names_in_text("갈매중앙로 79"))

    def test_authoring_cleanup_does_not_damage_school_name(self) -> None:
        result = generator.naturalize_text(
            "서원고 학교 정보를 이번 원고에서 확인합니다.",
            context(schools=["서원고"], grades="고1,고2"),
            "paragraph-test",
        )
        self.assertIn("서원고", result)
        self.assertNotIn("서안내", result)

    def test_authoring_cleanup_protects_school_name_before_postposition(self) -> None:
        result = generator.naturalize_text(
            "청라고, 해원고처럼 확인된 학교 자료를 이번 원고에서 살펴봅니다.",
            context(schools=["청라고", "해원고"], grades="고1,고2"),
            "paragraph-test",
        )
        self.assertIn("해원고처럼", result)
        self.assertNotIn("해안내", result)

    def test_wrong_level_school_is_replaced_with_verified_scope(self) -> None:
        result = generator.naturalize_text(
            "학남중 학교 정보를 수업 계획에 반영합니다.",
            context(schools=["도남초", "국우초"], grades="초3,초4", level="초등학생"),
            "paragraph-test",
        )
        self.assertNotIn("학남중", result)
        generator.assert_verified_fact_claims(
            result,
            context(schools=["도남초", "국우초"], grades="초3,초4", level="초등학생"),
            "test-result",
        )

    def test_blank_school_source_neutralizes_named_school(self) -> None:
        result = generator.naturalize_text(
            "학남중 학교 정보를 확인합니다.",
            context(schools=[], grades="초3", level="초등학생"),
            "faq-answer-test",
        )
        self.assertNotIn("학남중", result)
        self.assertIn("학교", result)


class GradeFactGuardTests(unittest.TestCase):
    def test_disallowed_high_school_grade_is_replaced_from_allowed_range(self) -> None:
        result = generator.enforce_verified_grade_claims(
            "고3 학생은 시험 범위를 먼저 확인합니다.",
            context(schools=[], grades="고1,고2"),
        )
        self.assertNotIn("고3", result)
        self.assertTrue("고1" in result or "고2" in result)

    def test_allowed_grade_is_preserved(self) -> None:
        result = generator.enforce_verified_grade_claims(
            "중학교 2학년 학생은 오답을 다시 풉니다.",
            context(schools=[], grades="중1,중2,중3", level="중학생"),
        )
        self.assertEqual(result, "중학교 2학년 학생은 오답을 다시 풉니다.")

    def test_blank_grade_source_uses_neutral_level(self) -> None:
        result = generator.enforce_verified_grade_claims(
            "초3 학생은 연산 기록을 확인합니다.",
            context(schools=[], grades="", level="초등학생"),
        )
        self.assertNotIn("초3", result)
        self.assertIn("초등학생", result)

    def test_assertion_rejects_unverified_final_grade(self) -> None:
        with self.assertRaisesRegex(ValueError, "grades=.*고3"):
            generator.assert_verified_fact_claims(
                "고3 학생은 시험 범위를 먼저 확인합니다.",
                context(schools=[], grades="고1,고2"),
                "unit-test",
            )


class PublicCopyPolishTests(unittest.TestCase):
    def test_final_polish_removes_authoring_narration(self) -> None:
        value = (
            "확인 질문을 핵심 안내 설명문에 넣기 좋게 정리했습니다. "
            "가경동 중학생 영어학원 요약문은 고등학생 학생에게 필요한 기준을 설명합니다. "
            "오답이 반복되는 경우인 경우에는 원인을 확인합니다."
        )
        result = generator.final_polish_text(value)
        self.assertNotIn("설명문에 넣기 좋게", result)
        self.assertNotIn("요약문은", result)
        self.assertNotIn("학생 학생", result)
        self.assertNotIn("경우인 경우", result)


if __name__ == "__main__":
    unittest.main()
