# 새 홈페이지7: 본문 근거형 타이틀 접미사

## 사이트와 변경 범위

- 사이트: 학습관리학원.com
- 도메인: https://xn--zb0b93vh4ggmeqzwda.com
- GitHub: https://github.com/01039578283-hub/new7 (기존 공개 설정 유지)
- Vercel 프로젝트: new7 / scope 1992kjb / main 브랜치 자동 배포
- 수정 전 비교 기준: de7fdeb3e70152642ac0963cfcb200285c3b958a
- DNS, 도메인 연결, 저장소 공개 범위, Vercel 설정은 변경하지 않음.

대상 HTML 4,088개:

| 유형 | 페이지 수 |
| --- | ---: |
| 전국학원 동네 안내 | 371 |
| 국영수학원·소수정예학원·수학영어학원·영어수학학원 | 1,484 |
| 불당동 고등수학학원 개별 페이지 | 1 |
| 초등·중등·고등 영어/수학 지역 상세 | 2,226 |
| 학년·과목별 카테고리 허브 | 6 |

홈, 전국학원 최상위, 과목별학원 최상위, 학습가이드, 상담문의는 수정하지 않음.
전체 HTML과 사이트맵 URL 수는 각각 4,093개. RSS 20개 항목 중
대상에 해당하는 16개 항목의 제목만 동기화함.

## 적용 원칙

- HTML title 태그의 | 앞 제목을 보존하고 뒤의 공통 사이트명을 본문 근거형 접미사로 대체.
- 기존 og:title, twitter:title이 있으면 같은 제목으로 동기화.
- H1, 본문, FAQ, 앵커목차, JSON-LD, canonical, 이미지·ALT·숨김 대표이미지,
  디자인, 사이트맵, robots.txt, llms.txt, vercel.json은 보존.
- 전국학원은 실제 data-content-role="unique-copy" 학습 설계와 학생 상황에 우선순위.
- 과목별 페이지는 academy-article의 실제 도입과 학습 설명을 우선.
- 주소·학교 목록·센터 정보·후기·관련 링크는 접미사 다양성을 만드는 소재로 사용하지 않음.
- 공통 도입 문장은 알려진 동네명/타이틀만 비교용으로 정규화해 반복 빈도를 계산하고
  가중치를 낮춤. 본문 자체를 재작성하거나 동네명 해시로 접미사를 배정하지 않음.
- 학년/과목이 어긋난 주제, 같은 뜻을 반복한 접미사 조합을 제외.
- 카테고리 허브 6개는 본문이 같은 디렉터리 안내이므로 기능에 맞는 공통 접미사를 사용.
- 완성 타이틀 4,088개는 서로 다르며, 접미사 조합은 777개.
  실제 학습 주제가 같은 페이지에는 접미사 재사용을 허용함.
- 제목 길이: 공백 포함 26~41자. 검색엔진이 검색 결과 제목을 다시 구성할 수 있으며
  노출 순위나 변경 반영 시점을 보장하지 않음.

예:

- 명일동 중학생 수학학원 | 첫 식 세우기·계산 실수 구분
- 명일동 초등학생 영어학원 | 긴 지문 읽기 집중·오답 재확인 습관
- 명일동 소수정예학원 | 질문을 미루지 않는 공부·플래너 실행 점검

## 재현과 검증

프로젝트 루트에서 실행:

    python -X utf8 -m unittest discover -s tools -p test_title_suffixes.py
    python -X utf8 tools/personalize_title_suffixes.py --check
    python -X utf8 tools/verify_title_release.py
    python -X utf8 tools/verify_title_release.py --public

- 회귀 테스트: 20개 통과.
- --check: 제목/관련 RSS 추가 변경 0개, 재실행 안정성 통과.
- 전체 지역/카테고리 4,088개 로컬 검증 통과: 실패 0, 고정 Git 기준 대비 제목 외 변경 0.
- 기존 전체 사이트 검사 통과: HTML/사이트맵 4,093개, JSON-LD·FAQ·링크 오류 0.
- 과목별 상세 2,226개 목차 검사 통과: 연결 13,356개, 추가 변경 0.
- title-suffix-audit.json: 페이지별 이전/이후 제목, 실제 본문 근거, 제목 외 원문 SHA-256.
- title-suffix-local-verification.json: 전체 페이지와 고정 Git 기준 비교, 기존 사이트 검사,
  앵커목차 및 XML 검사 결과.
- title-suffix-public-verification.json: 실제 운영 도메인 대표 페이지와 XML의 공개 검증 결과.
- title-suffix-release.json: 배포 후 실제 Git SHA·Vercel 배포·공개 확인 결과.
- 앞의 audit/local 보고서만 Git에 보관. public/plan/release 보고서는 로컬 기록으로 유지.
  tools와 reports는 기존 .vercelignore에 의해 사이트 배포 파일에서 제외됨.

이번 작업은 기존 본문 생성기를 실행하지 않았음. 기존 생성기용
tools.test_subject_fact_guards는 외부 대표 이미지 url.csv가 현재 경로에 없어
import 단계에서 실행 불가였으며, 이를 통과했다고 기록하지 않음.
실제 완성 HTML에 대한 기존 audit_site.py와 목차 검사는 별도로 수행.
외부 원본 자료나 이미지 파일을 새로 만들거나 대체하지 않음.

이후 원래의 전체 페이지 생성기를 다시 실행하면 기존 공통 접미사로 돌아올 수 있음.
그때는 생성 후 이 도구로 제목을 다시 적용해야 함. 본문이나 페이지 수가 실제로
변경된 후의 검증은 해당 작업의 올바른 Git 기준과 범위를 새로 정해야 하며,
현재 고정 기준의 본문 보호 검사를 임의로 무시해서는 안 됨.
