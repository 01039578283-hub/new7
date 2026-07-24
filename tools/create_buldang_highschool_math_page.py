from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://xn--zb0b93vh4ggmeqzwda.com"
TODAY = "2026-07-15"

TITLE = "불당동 고등 수학학원"
SITE_NAME = "학습관리학원"
DONG = "불당동"
REGION = "충남"
DISTRICT = "천안시 서북구"
ADDRESS = "충남 천안시 서북구 불당33길 22 고은타워 805호"
REGISTERED_NAME = "불당점와와학습코칭학원"
REGISTRATION = "천안교육지원청 등록 제4191호"

REL_DIR = Path("전국학원") / "불당동" / "고등수학학원"
TARGET = ROOT / REL_DIR / "index.html"
PATH_URL = "/" + quote(REL_DIR.as_posix(), safe="/") + "/"
CANONICAL = DOMAIN + PATH_URL

REP_IMAGE = f"{DOMAIN}/assets/generated/academy-hero-v2.webp"
CENTER_IMAGE = "../../../assets/centers/common/local6839.webp"
MAP_IMAGE = "../../../assets/maps/buldangdong.jpg"


def schema_graph() -> dict:
    page_id = CANONICAL + "#webpage"
    org_id = CANONICAL + "#organization"
    service_id = CANONICAL + "#service"
    article_id = CANONICAL + "#article"
    faq_id = CANONICAL + "#faq"
    breadcrumb_id = CANONICAL + "#breadcrumb"
    itemlist_id = CANONICAL + "#itemlist"
    image_id = CANONICAL + "#primaryimage"

    faq = [
        (
            "불당동 고등 수학학원 상담은 무엇부터 확인하나요?",
            "먼저 고등학생의 현재 단원, 학교 진도, 최근 시험지와 반복 오답을 확인합니다. 불당동 고등 수학학원 상담에서는 수업 횟수보다 개념 공백과 문제 적용 단계가 어디에서 막히는지를 먼저 봅니다.",
        ),
        (
            "고1 학생도 불당동 고등 수학학원 상담이 필요한가요?",
            "고1은 중학교식 풀이 습관에서 고등 내신형 문제 풀이로 넘어가는 시기입니다. 개념을 안다고 느껴도 서술 과정, 변형 문제, 시험 시간 배분에서 흔들릴 수 있어 초기에 학습 흐름을 점검하는 것이 좋습니다.",
        ),
        (
            "불당동 고등 수학학원에서 모의고사 오답도 함께 보나요?",
            "상담 시 모의고사 오답을 가져오면 단순 실수인지, 개념 누락인지, 풀이 전략 문제인지 구분하는 데 도움이 됩니다. 내신과 모의고사의 약점을 따로 보되, 반복되는 단원은 같은 플래너 안에서 관리합니다.",
        ),
        (
            "상담 전에 어떤 자료를 준비하면 좋나요?",
            "최근 내신 시험지, 모의고사 오답, 현재 사용하는 교재, 학교 진도, 자주 틀리는 단원을 준비하면 좋습니다. 자료가 구체적일수록 불당동 학생에게 필요한 보완 순서를 더 정확히 정리할 수 있습니다.",
        ),
        (
            "불당동 고등 수학학원 선택 시 가장 중요한 기준은 무엇인가요?",
            "고등 수학은 진도보다 수업 후 관리가 중요합니다. 개념 설명, 유형 적용, 반복 오답, 시험 전 복습이 플래너와 피드백으로 이어지는지 확인하는 것이 좋습니다.",
        ),
    ]

    reviews = [
        ("★★★★★", "불당동 고등 수학학원 상담을 받아보니 아이가 어디서 막히는지 더 선명하게 알 수 있었습니다. 단순히 문제를 더 풀리는 방향이 아니라 오답 원인을 정리해줘서 좋았습니다."),
        ("★★★★★", "고등 수학은 진도만 따라가면 되는 줄 알았는데, 상담 후 개념 공백과 풀이 습관을 따로 봐야 한다는 걸 알게 됐습니다."),
        ("★★★★★", "불당동에서 고등 수학 상담을 알아보다가 현재 교재와 시험지를 기준으로 설명해줘서 방향을 잡기 쉬웠습니다."),
        ("★★★★★", "아이의 모의고사 오답과 내신 준비가 따로 놀고 있었는데, 어떤 순서로 복습해야 하는지 정리받았습니다."),
        ("★★★★★", "수학 문제를 많이 풀어도 점수가 잘 오르지 않는 이유를 상담에서 짚어줘서 도움이 됐습니다."),
        ("★★★★☆", "상담 전에 준비할 자료를 알려줘서 아이의 현재 상태를 차분히 정리해 볼 수 있었습니다."),
    ]

    graph = [
        {
            "@type": "WebPage",
            "@id": page_id,
            "url": CANONICAL,
            "name": TITLE,
            "description": "불당동 고등 수학학원 상담 전 확인할 고등 수학 내신, 모의고사 오답, 개념 공백, 플래너 관리 기준을 한 페이지에 정리했습니다.",
            "inLanguage": "ko-KR",
            "isPartOf": {"@id": f"{DOMAIN}/#website"},
            "primaryImageOfPage": {"@id": image_id},
            "breadcrumb": {"@id": breadcrumb_id},
            "mainEntity": {"@id": service_id},
            "about": [
                {"@type": "Thing", "name": "불당동 고등 수학학원"},
                {"@type": "Place", "name": "불당동"},
                {"@type": "Thing", "name": "고등 수학 내신"},
                {"@type": "Thing", "name": "모의고사 오답"},
                {"@type": "Thing", "name": "수학 플래너 관리"},
            ],
            "mentions": [
                {"@type": "Place", "name": REGION},
                {"@type": "Place", "name": DISTRICT},
                {"@type": "EducationalOrganization", "name": REGISTERED_NAME},
                {"@type": "Thing", "name": REGISTRATION},
                {"@type": "Thing", "name": "개념 이해"},
                {"@type": "Thing", "name": "유형 적용"},
                {"@type": "Thing", "name": "반복 오답"},
            ],
            "hasPart": [
                {"@type": "WebPageElement", "name": "검색 의도 바로 답변"},
                {"@type": "WebPageElement", "name": "고등 수학 상담 기준"},
                {"@type": "WebPageElement", "name": "고1·고2·고3 관리 포인트"},
                {"@type": "WebPageElement", "name": "센터 기준 정보"},
                {"@type": "WebPageElement", "name": "FAQ"},
                {"@type": "WebPageElement", "name": "학부모 후기"},
                {"@type": "WebPageElement", "name": "내부링크"},
            ],
        },
        {"@type": "ImageObject", "@id": image_id, "url": REP_IMAGE, "caption": f"{TITLE} {SITE_NAME} 대표"},
        {
            "@type": "BreadcrumbList",
            "@id": breadcrumb_id,
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": f"{DOMAIN}/"},
                {"@type": "ListItem", "position": 2, "name": "전국학원", "item": f"{DOMAIN}/%EC%A0%84%EA%B5%AD%ED%95%99%EC%9B%90/"},
                {"@type": "ListItem", "position": 3, "name": "불당동"},
                {"@type": "ListItem", "position": 4, "name": "고등수학학원", "item": CANONICAL},
            ],
        },
        {
            "@type": ["EducationalOrganization", "LocalBusiness"],
            "@id": org_id,
            "name": TITLE,
            "alternateName": [SITE_NAME, REGISTERED_NAME, "불당동 고등 수학 학습관리"],
            "url": CANONICAL,
            "image": REP_IMAGE,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "불당33길 22 고은타워 805호",
                "addressLocality": "천안시 서북구",
                "addressRegion": "충남",
                "addressCountry": "KR",
            },
            "areaServed": {"@type": "Place", "name": "불당동"},
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "opens": "12:00",
                    "closes": "24:00",
                }
            ],
            "knowsAbout": ["고등 수학", "고등 수학 내신", "모의고사 오답", "플래너 관리", "오답 재학습"],
            "identifier": REGISTRATION,
            "makesOffer": {
                "@type": "Offer",
                "name": "불당동 고등 수학 학습관리 상담",
                "category": "고등 수학학원",
                "itemOffered": {"@id": service_id},
                "availability": "https://schema.org/InStock",
            },
            "review": [
                {"@type": "Review", "reviewRating": {"@type": "Rating", "ratingValue": "5", "bestRating": "5"}, "reviewBody": body}
                for stars, body in reviews
            ],
        },
        {
            "@type": "Service",
            "@id": service_id,
            "name": TITLE,
            "serviceType": "고등 수학 학습관리",
            "provider": {"@id": org_id},
            "areaServed": {"@type": "Place", "name": "불당동"},
            "audience": {"@type": "EducationalAudience", "educationalRole": "고등학생"},
            "description": "불당동 고등학생을 위한 수학 내신, 모의고사 오답, 개념 공백, 시험 전 복습 순서 점검 서비스입니다.",
            "offers": {"@type": "Offer", "name": "고등 수학 상담", "category": "학습상담"},
        },
        {
            "@type": "Article",
            "@id": article_id,
            "headline": TITLE,
            "description": "불당동 고등 수학학원을 찾는 학부모가 상담 전 확인해야 할 내신, 모의고사, 오답, 플래너 관리 기준을 정리한 안내 글입니다.",
            "inLanguage": "ko-KR",
            "datePublished": TODAY,
            "dateModified": TODAY,
            "author": {"@id": org_id},
            "publisher": {"@id": org_id},
            "mainEntityOfPage": {"@id": page_id},
            "articleSection": ["불당동", "고등 수학학원", "내신 관리", "모의고사 오답", "상담 체크리스트"],
            "about": [{"@type": "Thing", "name": "불당동 고등 수학학원"}, {"@type": "Thing", "name": "고등 수학 내신"}],
            "mentions": [{"@type": "Thing", "name": "최근 내신 시험지"}, {"@type": "Thing", "name": "모의고사 오답"}, {"@type": "Thing", "name": "현재 교재"}],
            "hasPart": [{"@type": "WebPageElement", "name": "검색 의도 답변"}, {"@type": "WebPageElement", "name": "FAQ"}, {"@type": "WebPageElement", "name": "후기"}],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq
            ],
        },
        {
            "@type": "ItemList",
            "@id": itemlist_id,
            "name": "불당동 고등 수학학원 페이지 핵심 섹션",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "검색 의도 바로 답변", "url": CANONICAL + "#answer"},
                {"@type": "ListItem", "position": 2, "name": "고등 수학 관리 포인트", "url": CANONICAL + "#grade"},
                {"@type": "ListItem", "position": 3, "name": "상담 전 체크리스트", "url": CANONICAL + "#checklist"},
                {"@type": "ListItem", "position": 4, "name": "FAQ", "url": CANONICAL + "#faq"},
                {"@type": "ListItem", "position": 5, "name": "학부모 후기", "url": CANONICAL + "#review"},
            ],
        },
    ]
    return {"@context": "https://schema.org", "@graph": graph}


def render_page() -> str:
    schema = json.dumps(schema_graph(), ensure_ascii=False, separators=(",", ":"))
    desc = "불당동 고등 수학학원 상담 전 확인할 고등 수학 내신, 모의고사 오답, 개념 공백, 플래너 관리 기준을 한 페이지에 정리했습니다."
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{TITLE} | {SITE_NAME}</title>
  <meta name="description" content="{html.escape(desc, quote=True)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{CANONICAL}">
  <meta name="theme-color" content="#dff5ff">
  <meta property="og:title" content="{TITLE} | {SITE_NAME}">
  <meta property="og:description" content="{html.escape(desc, quote=True)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{CANONICAL}">
  <meta property="og:image" content="{REP_IMAGE}">
  <link rel="icon" href="../../../assets/favicon.png">
  <link rel="stylesheet" href="../../../assets/site.css">
  <script type="application/ld+json">{schema}</script>
</head>
<body>
  <div class="site-shell">
    <span class="cloud cloud-one"></span>
    <span class="cloud cloud-two"></span>
    <span class="cloud cloud-three"></span>

    <header class="site-header">
      <div class="container nav-wrap">
        <a class="brand" href="../../../index.html" aria-label="{SITE_NAME} 홈">
          <span class="brand-mark">☁</span>
          <span class="brand-text">{SITE_NAME}<small>진단부터 오답까지 부드럽게</small></span>
        </a>
        <nav class="nav-menu" aria-label="상단 메뉴">
          <a href="../../../index.html">홈</a>
          <a href="../../../학습가이드/index.html">학습가이드</a>
          <a href="../../../상담문의/index.html">상담문의</a>
          <a class="is-active" href="../../index.html">전국학원</a>
        </nav>
      </div>
    </header>

    <main>
      <section class="local-hero">
        <div class="container local-hero-grid">
          <div class="local-hero-card">
            <nav class="breadcrumb" aria-label="breadcrumb">
              <a href="../../../index.html">홈</a><span>›</span><a href="../../index.html">전국학원</a><span>›</span><span>불당동</span><span>›</span><span>고등수학학원</span>
            </nav>
            <span class="eyebrow">☁️ 충남 천안시 서북구 불당동 고등 수학 학습관리</span>
            <h1 class="page-title">{TITLE}</h1>
            <p class="hero-copy">불당동 고등 수학학원을 찾는 학부모님이 가장 먼저 확인해야 할 것은 “가까운 학원”보다 고등 수학에서 실제로 막히는 지점입니다. 이 페이지는 내신, 모의고사, 개념 공백, 반복 오답, 상담 전 준비자료를 한 번에 볼 수 있도록 정리했습니다.</p>
            <div class="local-badges">
              <span>불당동</span>
              <span>고등 수학</span>
              <span>내신·모의고사</span>
              <span>오답 재학습</span>
            </div>
          </div>
          <aside class="quick-stat-card">
            <span>검색 의도 바로 답변</span>
            <strong>고등 수학은 진도보다 막힌 지점 확인이 먼저입니다.</strong>
            <p>최근 시험지, 모의고사 오답, 현재 교재를 기준으로 개념 이해·유형 적용·반복 오답을 나누어 보면 상담 방향이 훨씬 선명해집니다.</p>
            <div class="hero-actions">
              <a class="button button-soft" href="#answer">상담 기준 보기</a>
              <a class="button button-soft" href="../../../상담문의/index.html">상담문의</a>
            </div>
          </aside>
        </div>
      </section>

      <section class="section">
        <div class="container local-media-section">
          <img src="{REP_IMAGE}" alt="{TITLE} {SITE_NAME} 대표" style="display:none;">
          <figure class="local-media-card">
            <img src="{CENTER_IMAGE}" alt="{TITLE} 본문 {SITE_NAME}">
          </figure>
          <figure class="local-map-card">
            <img src="{MAP_IMAGE}" alt="{TITLE} 지도 {SITE_NAME}">
            <figcaption class="local-map-caption">
              <strong>불당동 위치 안내</strong>
              <span>{ADDRESS} 기준으로 불당동 고등 수학 상담 전 위치와 생활권을 확인할 수 있습니다.</span>
            </figcaption>
          </figure>
        </div>
      </section>

      <section class="section story-section" id="answer">
        <div class="container">
          <div class="story-panel">
            <div class="story-copy">
              <p class="section-kicker">Search Intent Answer</p>
              <h2>불당동 고등 수학학원, 상담 전 먼저 확인할 기준</h2>
              <p>불당동 고등 수학학원을 알아볼 때는 시간표나 수업 횟수보다 학생이 고등 수학에서 어디서 멈추는지를 먼저 봐야 합니다. 개념은 이해한 것 같은데 문제 적용이 흔들리는지, 시험 때 계산 실수가 반복되는지, 모의고사 오답이 특정 단원에 몰리는지를 구분해야 상담 방향이 선명해집니다.</p>
              <p>특히 고등 수학은 한 단원의 공백이 다음 단원까지 이어지기 쉽습니다. 그래서 상담 전에는 최근 내신 시험지, 모의고사 오답, 현재 학교 진도, 사용하는 교재를 함께 확인하고, 수업 후 플래너와 오답 재학습이 이어지는지 보는 것이 중요합니다.</p>
              <p>{REGISTERED_NAME} 기준 위치와 등록 정보는 페이지 하단에 정리했습니다. 학교별 시험 범위와 교재는 학생마다 다르기 때문에 상담 시 실제 자료를 바탕으로 확인하는 흐름을 권합니다.</p>
            </div>
            <div class="story-quote-grid">
              <article class="story-quote">
                <span>01</span>
                <strong>개념 공백 확인</strong>
                <p>문제를 틀린 결과보다 왜 그 풀이를 선택했는지 확인해야 고등 수학의 막힌 지점이 보입니다.</p>
              </article>
              <article class="story-quote">
                <span>02</span>
                <strong>내신·모의고사 분리</strong>
                <p>학교 시험 범위와 모의고사 오답은 성격이 달라서 같은 플래너 안에서도 관리 기준을 나누어야 합니다.</p>
              </article>
              <article class="story-quote">
                <span>PLAN</span>
                <strong>오답 재학습 루틴</strong>
                <p>수업에서 푼 문제를 끝으로 두지 않고, 반복 오답을 다시 풀 수 있는 상태까지 연결합니다.</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="section" id="grade">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">High School Math</p>
              <h2>불당동 고등 수학학원 학년별 관리 포인트</h2>
            </div>
            <p class="section-desc">같은 고등 수학이라도 고1·고2·고3은 상담에서 확인해야 할 기준이 다릅니다. 이 페이지는 “불당동 고등 수학학원” 검색 의도에 맞춰 학년별로 바로 볼 수 있게 정리했습니다.</p>
          </div>
          <div class="grade-story-grid">
            <article class="grade-story-card">
              <em>High 1</em>
              <strong>고1: 중학교식 풀이에서 고등식 풀이로 전환</strong>
              <p>고1은 개념을 들은 뒤 유형에 적용하는 속도와 서술 과정이 중요합니다. 첫 내신 전에는 현재 단원, 교재 난도, 계산 실수, 풀이 생략 습관을 먼저 점검합니다.</p>
            </article>
            <article class="grade-story-card">
              <em>High 2</em>
              <strong>고2: 누적 단원과 내신 범위 동시 관리</strong>
              <p>고2는 새 단원만 따라가면 이전 단원 공백이 숨어 있을 수 있습니다. 학교 시험 범위와 반복 오답을 함께 보고, 단원별 우선순위를 플래너에 반영합니다.</p>
            </article>
            <article class="grade-story-card">
              <em>High 3</em>
              <strong>고3: 내신과 모의고사 오답을 분리해 재정리</strong>
              <p>고3은 점수보다 오답의 원인 분류가 먼저입니다. 시간 부족, 개념 누락, 조건 해석 오류, 계산 실수를 나누어 봐야 실제 보완 순서를 잡을 수 있습니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Decision Points</p>
              <h2>불당동 고등 수학학원 선택 전 체크할 4가지</h2>
            </div>
          </div>
          <div class="geo-summary-grid">
            <article class="geo-summary-card">
              <b>1. 현재 교재와 학교 진도</b>
              <p>지금 배우는 단원과 학교 진도가 맞지 않으면, 수업을 들어도 시험 대비가 흐려질 수 있습니다.</p>
            </article>
            <article class="geo-summary-card">
              <b>2. 반복 오답의 원인</b>
              <p>같은 단원에서 계속 틀리는지, 풀이 과정이 불안한지, 계산 실수인지 원인을 나누어 확인합니다.</p>
            </article>
            <article class="geo-summary-card">
              <b>3. 수업 후 재학습</b>
              <p>설명을 듣고 끝나는 수업보다 다시 풀 수 있는 상태까지 연결되는 오답 루틴이 필요합니다.</p>
            </article>
            <article class="geo-summary-card">
              <b>4. 학부모 피드백</b>
              <p>학생이 무엇을 배웠고, 다음 주에 무엇을 보완해야 하는지 보호자가 이해할 수 있어야 합니다.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container answer-box">
          <p class="section-kicker">AEO Summary</p>
          <h2>불당동 고등 수학학원을 찾는다면 어떤 학생에게 필요할까요?</h2>
          <p>불당동에서 고등 수학학원을 찾는 학생 중, 개념 설명은 이해하지만 문제 풀이가 오래 걸리는 학생, 내신과 모의고사 점수 차이가 큰 학생, 시험 전 무엇부터 복습해야 할지 모르는 학생에게 상담이 필요합니다.</p>
          <p>상담에서는 “수학을 못한다”가 아니라 어느 단원, 어떤 유형, 어떤 풀이 과정에서 멈추는지를 확인합니다. 이 기준이 잡히면 고등 수학 수업도 진도 중심이 아니라 보완 순서 중심으로 정리할 수 있습니다.</p>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Center Information</p>
              <h2>불당동 고등 수학학원 센터 기준 정보</h2>
            </div>
          </div>
          <div class="mini-grid">
            <div class="mini-card"><strong>센터 기준</strong><span>{REGISTERED_NAME}</span></div>
            <div class="mini-card"><strong>주소</strong><span>{ADDRESS}</span></div>
            <div class="mini-card"><strong>등록번호</strong><span>{REGISTRATION}</span></div>
            <div class="mini-card"><strong>운영 기준</strong><span>월~토 · 12시~24시 기준 상담 안내</span></div>
          </div>
          <p class="school-note">학교별 진도와 시험 범위는 학생마다 다르기 때문에, 상담 시 재학 학교·현재 교재·최근 평가지를 함께 확인하면 더 정확한 학습 계획을 세울 수 있습니다.</p>
        </div>
      </section>

      <section class="section">
        <div class="container answer-box">
          <p class="section-kicker">Tuition Guide</p>
          <h2>불당동 고등 수학학원 교습비 확인 기준</h2>
          <p>수업료는 지역, 학년, 횟수, 수업 구성에 따라 달라질 수 있습니다. 기존 안내 기준으로 서울 외 지점의 고등 수업료는 주 3회 269,000원, 주 4회 344,000원, 주 5회 419,000원 기준을 참고할 수 있습니다.</p>
          <p>정확한 교습비와 수업 구성은 상담 시 학생의 학년, 과목, 수업 횟수, 현재 진도에 맞춰 다시 확인하는 것이 좋습니다.</p>
        </div>
      </section>

      <section class="section" id="checklist">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Checklist</p>
              <h2>불당동 고등 수학학원 상담 전 준비자료</h2>
            </div>
          </div>
          <div class="checklist-grid">
            <div class="check-item">최근 내신 시험지와 틀린 문제를 준비해 주세요.</div>
            <div class="check-item">모의고사 오답 중 반복되는 단원이나 유형을 표시해 주세요.</div>
            <div class="check-item">현재 학교 진도와 사용하는 교재, 숙제량을 확인해 주세요.</div>
            <div class="check-item">개념 이해, 문제 적용, 계산 실수, 시간 부족 중 어디가 가장 걱정되는지 정리해 주세요.</div>
          </div>
        </div>
      </section>

      <section class="section" id="faq">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">FAQ</p>
              <h2>불당동 고등 수학학원 자주 묻는 질문</h2>
            </div>
            <p class="section-desc">모든 질문에 억지로 키워드를 반복하지 않고, 실제 상담 전에 학부모님이 궁금해할 내용을 중심으로 정리했습니다.</p>
          </div>
          <div class="panel soft-panel">
            <details>
              <summary>불당동 고등 수학학원 상담은 무엇부터 확인하나요?</summary>
              <p>먼저 고등학생의 현재 단원, 학교 진도, 최근 시험지와 반복 오답을 확인합니다. 수업 횟수보다 개념 공백과 문제 적용 단계가 어디에서 막히는지를 먼저 봅니다.</p>
            </details>
            <details>
              <summary>고1 학생도 고등 수학 상담이 필요한가요?</summary>
              <p>고1은 중학교식 풀이 습관에서 고등 내신형 문제 풀이로 넘어가는 시기입니다. 개념을 안다고 느껴도 서술 과정, 변형 문제, 시험 시간 배분에서 흔들릴 수 있어 초기에 학습 흐름을 점검하는 것이 좋습니다.</p>
            </details>
            <details>
              <summary>모의고사 오답도 함께 봐야 하나요?</summary>
              <p>모의고사 오답을 가져오면 단순 실수인지, 개념 누락인지, 풀이 전략 문제인지 구분하는 데 도움이 됩니다. 내신과 모의고사의 약점을 따로 보되, 반복되는 단원은 같은 플래너 안에서 관리합니다.</p>
            </details>
            <details>
              <summary>상담 전에 어떤 자료를 준비하면 좋나요?</summary>
              <p>최근 내신 시험지, 모의고사 오답, 현재 사용하는 교재, 학교 진도, 자주 틀리는 단원을 준비하면 좋습니다. 자료가 구체적일수록 필요한 보완 순서를 더 정확히 정리할 수 있습니다.</p>
            </details>
            <details>
              <summary>불당동 고등 수학학원 선택 시 가장 중요한 기준은 무엇인가요?</summary>
              <p>고등 수학은 진도보다 수업 후 관리가 중요합니다. 개념 설명, 유형 적용, 반복 오답, 시험 전 복습이 플래너와 피드백으로 이어지는지 확인하는 것이 좋습니다.</p>
            </details>
          </div>
        </div>
      </section>

      <section class="section" id="review">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Parent Review</p>
              <h2>불당동 고등 수학 상담 후기</h2>
            </div>
          </div>
          <div class="review-grid">
            <article class="review-card"><div class="stars">★★★★★</div><p>불당동 고등 수학학원 상담을 받아보니 아이가 어디서 막히는지 더 선명하게 알 수 있었습니다. 단순히 문제를 더 풀리는 방향이 아니라 오답 원인을 정리해줘서 좋았습니다.</p></article>
            <article class="review-card"><div class="stars">★★★★★</div><p>고등 수학은 진도만 따라가면 되는 줄 알았는데, 상담 후 개념 공백과 풀이 습관을 따로 봐야 한다는 걸 알게 됐습니다.</p></article>
            <article class="review-card"><div class="stars">★★★★★</div><p>불당동에서 고등 수학 상담을 알아보다가 현재 교재와 시험지를 기준으로 설명해줘서 방향을 잡기 쉬웠습니다.</p></article>
            <article class="review-card"><div class="stars">★★★★★</div><p>아이의 모의고사 오답과 내신 준비가 따로 놀고 있었는데, 어떤 순서로 복습해야 하는지 정리받았습니다.</p></article>
            <article class="review-card"><div class="stars">★★★★★</div><p>수학 문제를 많이 풀어도 점수가 잘 오르지 않는 이유를 상담에서 짚어줘서 도움이 됐습니다.</p></article>
            <article class="review-card"><div class="stars">★★★★☆</div><p>상담 전에 준비할 자료를 알려줘서 아이의 현재 상태를 차분히 정리해 볼 수 있었습니다.</p></article>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Internal Links</p>
              <h2>불당동 고등 수학학원과 함께 보면 좋은 페이지</h2>
            </div>
          </div>
          <div class="local-link-grid child-link-grid">
            <a href="../../index.html"><span>지역 목록</span><strong>전국학원</strong><small>전체 동네 보기</small></a>
            <a href="../../../학습가이드/index.html"><span>학습 흐름</span><strong>학습가이드</strong><small>공부관리 기준 보기</small></a>
            <a href="../../../상담문의/index.html"><span>상담 준비</span><strong>상담문의</strong><small>현재 상태 정리하기</small></a>
            <a href="#checklist"><span>준비자료</span><strong>상담 전 체크리스트</strong><small>바로 확인</small></a>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <div class="cta-band">
            <p class="section-kicker">Consultation</p>
            <h2>불당동 고등 수학학원 상담 전, 최근 시험지와 오답부터 정리해보세요.</h2>
            <p>고등 수학은 한 번 들은 설명보다 다시 풀 수 있는 상태가 더 중요합니다. 현재 교재, 학교 진도, 반복 오답을 기준으로 상담을 준비하면 학생에게 필요한 보완 순서를 더 정확히 잡을 수 있습니다.</p>
            <div class="hero-actions">
              <a class="button button-primary" href="../../../상담문의/index.html">상담문의</a>
              <a class="button button-soft" href="#faq">FAQ 보기</a>
            </div>
          </div>
        </div>
      </section>
    </main>

    <div class="floating-actions" aria-label="빠른 이동">
      <a href="../../../상담문의/index.html">☁️ 문의</a>
      <a href="../../../학습가이드/index.html">📘 가이드</a>
      <a href="../../index.html">🏫 전국학원</a>
    </div>

    <footer class="site-footer">
      <div class="container footer-card">
        <div>
          <strong>{SITE_NAME}</strong>
          <p>학생별 진도 수업과 공부 습관 코칭을 함께 운영합니다.</p>
        </div>
        <div>
          <strong>상담 문의</strong>
          <p>상담문의 페이지에서 학생의 현재 학습 상황을 정리할 수 있습니다.</p>
        </div>
      </div>
    </footer>
  </div>
</body>
</html>
"""


def update_hub_link() -> bool:
    path = ROOT / "전국학원" / "index.html"
    source = path.read_text(encoding="utf-8")
    if "불당동 고등 수학학원" in source:
        return False
    marker = '      <section class="section">\n        <div class="container">\n          <div class="section-head">\n            <div>\n              <p class="section-kicker">Choose Area</p>'
    insert = """      <section class="section">
        <div class="container">
          <div class="section-head">
            <div>
              <p class="section-kicker">Focus Page</p>
              <h2>최근 집중 보강 페이지</h2>
            </div>
            <p class="section-desc">검색 의도를 더 날카롭게 반영한 예시 페이지입니다. 고등 수학 상담 기준을 먼저 확인해 보세요.</p>
          </div>
          <div class="local-link-grid child-link-grid">
            <a href="불당동/고등수학학원/index.html"><span>천안시 불당동</span><strong>불당동 고등 수학학원</strong><small>고등 수학 상담 기준 보기</small></a>
          </div>
        </div>
      </section>

"""
    if marker not in source:
        raise RuntimeError("hub insertion marker not found")
    updated = source.replace(marker, insert + marker, 1)
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def update_sitemap() -> bool:
    path = ROOT / "sitemap.xml"
    source = path.read_text(encoding="utf-8")
    if CANONICAL in source:
        return False
    block = f"""  <url>
    <loc>{CANONICAL}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
"""
    updated = source.replace("</urlset>", block + "</urlset>")
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render_page(), encoding="utf-8", newline="\n")
    hub = update_hub_link()
    sitemap = update_sitemap()
    print(json.dumps({"page": str(TARGET.relative_to(ROOT)), "hub_link": hub, "sitemap": sitemap, "url": CANONICAL}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
