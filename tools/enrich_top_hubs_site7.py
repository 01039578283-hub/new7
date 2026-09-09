"""Enrich only the 8 national/topic coaching hubs; never regenerate locality copy."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/hub-guides'
REPORTS = ROOT / 'tools/reports/hub-enrichment'
DOMAIN = 'https://xn--zb0b93vh4ggmeqzwda.com'
CSS = '/assets/hub-guide-v1.css?v=20260910-2'
PHOTOS = [
    ('classroom-desks.webp', 500, 300, '개별 책상과 칸막이가 있는 학습 공간', '개별 학습에 집중할 수 있도록 책상과 칸막이를 배치한 공간 예시'),
    ('classroom-study.webp', 800, 600, '책상에서 교재를 살펴보는 학습 공간', '교재를 펼쳐 문제를 풀고 학습 과정을 점검하는 공간 예시'),
]


def esc(value):
    return html.escape(str(value), quote=True)


def p(value):
    return '<p>' + esc(value) + '</p>'


def fragment(value):
    return BeautifulSoup(value, 'html.parser')


def has_type(node, name):
    types = node.get('@type', [])
    return name in ([types] if isinstance(types, str) else types)


def scoped_subject(subject, stage):
    """Show only this school stage, retaining relevant and unscoped conditions."""
    import re

    if not stage:
        return subject
    prefix = stage[0]
    grades = [g for g in subject['grades'] if g.startswith(prefix)]
    numbers = sorted({int(g[1:]) for g in grades})
    runs = []
    for number in numbers:
        if runs and number == runs[-1][-1] + 1:
            runs[-1].append(number)
        else:
            runs.append([number])
    grade_summary = ' · '.join(prefix + str(run[0]) + ('~' + prefix + str(run[-1]) if len(run) > 1 else '') for run in runs)
    # The reviewed summary starts with exact grade/range tokens. Remove only
    # those tokens, not grade limits embedded in a condition sentence.
    grade_token = r'(?:초[1-6]|중[1-3]|고[1-3])(?:[~～-](?:초[1-6]|중[1-3]|고[1-3]))?'
    conditions = [part.strip() for part in subject['summary'].split(' · ')
                  if part.strip() and not re.fullmatch(grade_token, part.strip())]
    relevant, unscoped = [], []
    for detail in conditions:
        inherited_scope = set()
        for clause in (part.strip(' ,;') for part in re.split(r'[,;]', detail)):
            if not clause:
                continue
            scope = set(re.findall(r'([초중고])(?:[1-6]|등|학생)', clause))
            leading = re.match(r'^([초중고\s]{2,})', clause)
            if leading:
                scope.update(re.findall(r'[초중고]', leading.group(1)))
            for start, end in re.findall(r'([초중고])[1-6]\s*[~～-]\s*([초중고])[1-6]', clause):
                scope.update('초중고'['초중고'.index(start):'초중고'.index(end) + 1])
            explicit_scope = set(scope)
            # These are named high-school courses/exams, not a guess based on
            # a student's age. Other unscoped notes remain explicitly labeled.
            if not scope and re.search(r'미적(?:분)?|기하|확통|확률과\s*통계|수능|사탐|모의고사|통합과학|통합사회|현대사회와\s*윤리|[ⅠⅡ]|(?:화학|물리|생명|생물|지구과학)\s*[12]', clause):
                scope.add('고')
            if explicit_scope:
                inherited_scope = explicit_scope
            elif not scope and inherited_scope and not re.search(r'파닉스', clause):
                # A comma does not cancel the preceding grade condition:
                # '고3 사탐과목, 한국사 모두 가능' remains high-school scoped.
                # Phonics is independently stated without a grade in this source.
                # A course-name inference such as 수능 must not scope a later
                # independent 수행 condition to high school.
                scope = set(inherited_scope)
            if scope:
                if prefix in scope:
                    relevant.append(clause)
            else:
                unscoped.append(clause)
    parts = [grade_summary]
    if relevant:
        parts.append('안내 조건: ' + '; '.join(relevant))
    if unscoped:
        parts.append('지점 과목 안내 조건: ' + '; '.join(unscoped))
    return {**subject, 'grades': grades, 'summary': ' · '.join(parts)}


def choose_centers(rel, examples):
    slug = rel.split('/')[-2]
    required = ['영어', '수학'] if '영수' in slug else ['영어'] if '영어' in slug else ['수학'] if '수학' in slug else []
    stage = '초등' if slug.startswith('초등') else '중등' if slug.startswith('중') else '고등' if slug.startswith('고등') else None
    def matches_stage(subject):
        return not stage or any(g.startswith(stage[0]) for g in subject['grades'])
    candidates = []
    for original in examples:
        # Source addresses end with a bare single digit whose floor/unit is
        # missing. Preserve the catalog; do not guess a 층/호 suffix in a hub.
        if original['locality'] in {'옥계동', '복산동', '온천동'}:
            continue
        c = deepcopy(original)
        selected = [s for s in c['subjects'] if not required or s['name'] in required]
        if any(not any(s['name'] == name and matches_stage(s) for s in selected) for name in required):
            continue
        if stage and not any(matches_stage(s) for s in selected):
            continue
        if stage:
            selected = [scoped_subject(s, stage) for s in selected if matches_stage(s)]
        if required == ['영어', '수학']:
            shared_grades = set(next(s['grades'] for s in selected if s['name'] == '영어'))
            shared_grades.intersection_update(next(s['grades'] for s in selected if s['name'] == '수학'))
            if not shared_grades:
                continue
        path = c.get('targetPaths', {}).get(slug) if rel.startswith('과목별학원/') and slug != '과목별학원' else c['targetPath']
        if not path:
            continue
        assert (ROOT / unquote(urlsplit(path).path).strip('/') / 'index.html').is_file(), path
        c['targetPath'] = path
        c['organizationId'] = c.get('categoryOrganizationIds', {}).get(slug, c['organizationId'])
        c['subjects'] = selected
        c['_displayStage'] = stage
        candidates.append(c)
    if not candidates:
        raise ValueError('No verified examples for ' + rel)
    offset = int(hashlib.sha256(rel.encode()).hexdigest()[:8], 16) % len(candidates)
    candidates = candidates[offset:] + candidates[:offset]
    chosen = []
    for c in candidates:
        if c['region'] not in {x['region'] for x in chosen}:
            chosen.append(c)
        if len(chosen) == 3:
            break
    return chosen


def guide_markup(copy):
    cards = ''.join(f'<article class="hub-guide-card"><span class="hub-guide-number">0{i}</span><h3>{esc(s["heading"])}</h3>{"".join(p(t) for t in s["paragraphs"])}</article>' for i, s in enumerate(copy['sections'], 1))
    return f'<section class="hub-guide" data-hub-enrichment="guide" id="hub-learning-guide"><div class="hub-wrap"><div class="hub-guide-heading"><p class="eyebrow">LEARNING CHECK</p><h2>{esc(copy["label"])} 선택 전에 살펴볼 내용</h2></div><div class="hub-guide-grid">{cards}</div></div></section>'


def centers_markup(copy, centers):
    cards = []
    for c in centers:
        subjects = ' / '.join(s['name'] + ': ' + s['summary'] for s in c['subjects'])
        scope_label = (c['_displayStage'] + ' 과목·학년') if c.get('_displayStage') else '안내된 과목·학년'
        cards.append(f'<article class="hub-guide-card hub-center-card"><p class="hub-guide-note">{esc(c["region"])} · {esc(c["locality"])} 안내 연결</p><h3>{esc(c["centerName"])}</h3><dl><dt>주소</dt><dd>{esc(c["address"])}</dd><dt>등록 학원명</dt><dd>{esc(c["registeredAcademyName"])}</dd><dt>등록번호</dt><dd>{esc(c["registrationNumber"])}</dd><dt>{esc(scope_label)}</dt><dd>{esc(subjects)}</dd></dl><a href="{esc(c["targetPath"])}">{esc(c["locality"])} 상세 안내 보기 <span aria-hidden="true">→</span></a></article>')
    return f'<section class="hub-guide" data-hub-enrichment="centers" id="hub-center-examples"><div class="hub-wrap"><div class="hub-guide-heading"><p class="eyebrow">CENTER INFORMATION</p><h2>연결된 지점 정보도 확인하세요</h2><p>아래는 {esc(copy["label"])} 안내에서 살펴볼 수 있는 일부 지점입니다. 동네별 안내 수와 실제 지점 수는 다를 수 있으므로 방문할 곳의 주소와 가능 과목을 확인하세요.</p></div><div class="hub-guide-grid hub-center-grid">{"".join(cards)}</div><p class="hub-guide-note">지점 예시는 추천 순위가 아닙니다. 기재된 학년 범위 안에서도 현재 개설 여부와 희망 시간은 상담에서 확인하세요. 표시되지 않은 과목이 없다는 뜻은 아닙니다.</p></div></section>'


def after_markup(copy, centers):
    photos = ''.join(f'<figure><img src="/assets/hub-guide/{name}" width="{w}" height="{h}" alt="{esc(copy["label"])} {esc(alt)}" loading="lazy" decoding="async"><figcaption>{esc(caption)}</figcaption></figure>' for name,w,h,alt,caption in PHOTOS)
    return centers_markup(copy, centers) + '<section class="hub-guide" data-hub-enrichment="consultation" id="hub-consultation-guide"><div class="hub-wrap"><div class="hub-guide-heading"><p class="eyebrow">CONSULTATION NOTE</p><h2>상담에 가져갈 세 가지 기록</h2><p>자료를 예쁘게 정리하기보다 학생이 어디까지 혼자 할 수 있는지 드러나는 기록을 준비해 보세요.</p></div><div class="hub-guide-grid"><article class="hub-guide-card"><h3>풀이가 남아 있는 교재</h3><p>틀린 답을 지우기 전에 어떤 생각으로 풀었는지 표시해 두세요. 답만 틀린 것인지, 문제의 조건을 놓친 것인지 구별하면 되짚을 내용을 정하기 쉽습니다.</p></article><article class="hub-guide-card"><h3>실제로 공부한 시간</h3><p>계획한 분량과 완료한 분량을 나누고 오래 멈춘 부분을 적어 보세요. 수업을 늘릴지 결정하기 전에 집에서 이어 갈 수 있는 복습량도 함께 살펴야 합니다.</p></article><article class="hub-guide-card"><h3>학교 일정과 우선 질문</h3><p>다음 평가 날짜와 현재 학교 진도, 가장 어려운 과목을 준비하세요. 원하는 요일과 도착 가능한 시간을 전달하고, 개설 학년과 교습비·교재비 포함 여부를 같은 기준으로 확인합니다.</p></article></div><div class="hub-guide-reading"><a href="/학습가이드/">학습관리 기준 읽기</a><a href="/과목별학원/">과목·학년별 안내 보기</a><a href="/상담문의/">상담 방법 확인하기</a></div></div></section>' + f'<section class="hub-guide" data-hub-enrichment="photos" id="hub-learning-space"><div class="hub-wrap"><div class="hub-guide-heading"><p class="eyebrow">LEARNING SPACE</p><h2>학습 공간 살펴보기</h2><p>와와 학습 공간의 공통 예시입니다. 실제 책상 배치와 시설은 지점별로 다를 수 있습니다.</p></div><div class="hub-guide-gallery">{photos}</div></div></section>'


def update_schema(soup, canonical, copy, centers, qa, modified, rel):
    scripts = soup.select('script[type="application/ld+json"]')
    graphs = []
    for script in scripts:
        data = json.loads(script.get_text())
        graphs.extend(data.get('@graph', [data]) if isinstance(data, dict) else data)
    def absolute(value):
        if isinstance(value, dict): return {k: absolute(v) for k,v in value.items()}
        if isinstance(value, list): return [absolute(v) for v in value]
        if isinstance(value, str) and value.startswith('/'):
            return DOMAIN + value
        return value
    graphs = absolute(graphs)
    replacements = {n['@id']: canonical + '#' + n['@id'].split('#', 1)[1]
                    for n in graphs if '@id' in n and '#' in n['@id']
                    and unquote(n['@id'].split('#')[0]) == unquote(canonical)}
    def normalize(value):
        if isinstance(value, dict): return {k: normalize(v) for k,v in value.items()}
        if isinstance(value, list): return [normalize(v) for v in value]
        return replacements.get(value, value) if isinstance(value, str) else value
    graphs = normalize(graphs)
    # Rebuild managed entities each time: no stale examples, invented opening hours,
    # offers, ratings or reviews. A directory itself is not a class or an article.
    graphs = [n for n in graphs if not any(has_type(n,t) for t in
              ['FAQPage','Article','Service','EducationalOrganization','WebSite'])
              and not str(n.get('@id','')).startswith(canonical+'#hub-')]
    page = next(n for n in graphs if has_type(n,'WebPage') or has_type(n,'CollectionPage'))
    page.update({'@type':['WebPage','CollectionPage'],'url':canonical,
                 'description':copy['description'],'dateModified':modified,
                 'isPartOf':{'@id':DOMAIN+'/#website'},
                 'publisher':{'@id':DOMAIN+'/#organization'}})
    page['about'] = [{'@type':'Thing','name':copy['label']}] + [
        {'@type':'Thing','name':s['heading']} for s in copy['sections']]
    page['mentions'] = [{'@id':c['organizationId']} for c in centers]
    directory = next(n for n in graphs if has_type(n,'ItemList'))
    directory.setdefault('@id', canonical+'#directory')
    for n in graphs:
        if has_type(n,'BreadcrumbList'): n.setdefault('@id', canonical+'#breadcrumb')
    page['mainEntity'] = {'@id':directory['@id']}
    sections = [(x['id'],x.h2.get_text(' ',strip=True))
                for x in soup.select('section[data-hub-enrichment]') if x.get('id') and x.h2]
    page['hasPart'] = [{'@id':canonical+'#'+sid} for sid,_ in sections]+[{'@id':canonical+'#hub-faq'}]
    graphs += [
        {'@type':'WebSite','@id':DOMAIN+'/#website','url':DOMAIN+'/',
         'name':'학습관리학원.com','publisher':{'@id':DOMAIN+'/#organization'}},
        {'@type':'EducationalOrganization','@id':DOMAIN+'/#organization',
         'name':'학습관리학원','url':DOMAIN+'/'}
    ]
    for sid,label in sections:
        graphs.append({'@type':'WebPageElement','@id':canonical+'#'+sid,
            'url':canonical+'#'+sid,'name':label,'isPartOf':{'@id':page['@id']}})
    graphs.append({'@type':'FAQPage','@id':canonical+'#hub-faq',
        'url':canonical+'#hub-questions','isPartOf':{'@id':page['@id']},
        'mainEntity':[{'@type':'Question','name':q['question'],
          'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in qa]})
    for c in centers:
        if not any(n.get('@id') == c['organizationId'] for n in graphs):
            graphs.append({'@type':'EducationalOrganization','@id':c['organizationId'],
              'name':c['centerName'],'url':DOMAIN+quote(unquote(urlsplit(c['targetPath']).path),safe='/'),
              'address':c['address']})
    for script in scripts[1:]: script.decompose()
    scripts[0].string = json.dumps({'@context':'https://schema.org','@graph':graphs},
        ensure_ascii=False,separators=(',',':')).replace('</','<\\/')

def update_page(rel, copy, examples, modified):
    path = ROOT / rel
    before = path.read_text(encoding='utf-8')
    soup = BeautifulSoup(before, 'html.parser')
    fixed = (soup.title.get_text(), soup.h1.get_text(), soup.select_one('[rel=canonical]')['href'], soup.select_one('[property="og:url"]')['content'])
    canonical = fixed[2]
    for old in soup.select('[data-hub-enrichment]'): old.decompose()
    soup.body['class'] = list(dict.fromkeys(soup.body.get('class', []) + ['hub-enhanced-page']))
    hero = soup.main.select_one('.local-hero, .academy-hero')
    assert hero and hero.h1, rel
    summary = hero.h1.find_next_sibling('p')
    assert summary is not None, rel
    summary.clear(); summary.append(copy['summary'])
    # Retain the published category links, search markup and useful process/CTA.
    if rel == '전국학원/index.html':
        directory = soup.select_one('.region-directory-grid').find_parent('section')
        for section in soup.main.find_all('section',recursive=False):
            kicker = section.select_one('.section-kicker')
            if kicker and kicker.get_text(strip=True) == 'Focus Page':
                kicker.string = 'LEARNING EXAMPLE'
                section.h2.string = '지역별 학습 안내 예시'
                section.select_one('.section-desc').string = '동네별 안내에서 학생의 학년과 과목에 맞는 상담 준비 내용을 살펴보세요. 아래는 불당동 고등 수학 안내입니다.'
    elif rel == '과목별학원/index.html':
        directory = soup.select_one('.academy-category-grid').find_parent('section')
    else:
        directory = soup.select_one('.academy-directory').find_parent('section')
    assert directory is not None, rel
    directory['id'] = 'hub-directory'
    jumps = [('hub-directory','지역·분류 찾기'),('hub-learning-guide','학습 선택 기준'),('hub-center-examples','지점 정보'),('hub-consultation-guide','상담 준비'),('hub-learning-space','학습 공간'),('hub-questions','자주 묻는 질문')]
    hero.insert_after(fragment('<nav class="hub-guide-jumps" data-hub-enrichment="navigation" aria-label="이 페이지 빠른 이동"><div class="hub-wrap">'+''.join(f'<a href="#{sid}">{label}</a>' for sid,label in jumps)+'</div></nav>'))
    soup.select_one('.hub-guide-jumps').insert_after(fragment(guide_markup(copy)))
    centers = choose_centers(rel, examples)
    soup.main.append(fragment(after_markup(copy, centers)))
    qa = copy['faq'] + [
        {'question':'동네 이름과 실제 방문할 지점은 어떻게 확인하나요?','answer':'여러 동네의 안내가 같은 센터로 연결될 수 있습니다. 관심 동네의 상세 페이지에서 지점명과 주소를 확인하고, 현재 운영 과목·가능 학년·방문 시간을 상담으로 확인하세요.'},
        {'question':'사진과 학습 안내가 모든 지점에 그대로 적용되나요?','answer':'사진은 공통 학습 공간 예시이며 실제 시설과 배치는 지점마다 다릅니다. 학습 점검 방법은 학생의 현재 상태를 살펴보기 위한 안내입니다. 실제 개설 과목·학년·시간표와 교습비, 기록·소통 방식은 해당 지점에서 확인하세요.'},
    ]
    faq_markup = '<section class="hub-guide hub-guide-faq" id="hub-answer" data-hub-enrichment="faq"><div class="hub-wrap" id="hub-questions"><p class="eyebrow">FAQ</p><h2>'+esc(copy['label'])+' 자주 묻는 질문</h2><div id="hub-faq-list">'+''.join(f'<details><summary>{esc(q["question"])}</summary>{p(q["answer"])}</details>' for q in qa)+'</div></div></section>'
    soup.main.append(fragment(faq_markup))
    for attr,key in [('name','description'),('property','og:description'),('name','twitter:description')]:
        meta = soup.find('meta',attrs={attr:key})
        if meta: meta['content'] = copy['description']
    style = next((x for x in soup.select('link[href]') if x['href'].split('?')[0] == CSS.split('?')[0]),None)
    if style: style['href'] = CSS
    else: soup.head.append(soup.new_tag('link',rel='stylesheet',href=CSS))
    update_schema(soup,canonical,copy,centers,qa,modified,rel)
    assert fixed == (soup.title.get_text(), soup.h1.get_text(), soup.select_one('[rel=canonical]')['href'],soup.select_one('[property="og:url"]')['content'])
    after = str(BeautifulSoup(str(soup),'html.parser'))
    if before != after: path.write_text(after,encoding='utf-8',newline='\n')
    return {'path':rel,'changed':before!=after,'url':canonical,'faq':len(qa),'centerLocalities':[c['locality'] for c in centers],'sha256':hashlib.sha256(after.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date',default=date.today().isoformat())
    args = parser.parse_args()
    topics = json.loads((DATA/'subject-copy.json').read_text(encoding='utf-8'))
    examples = json.loads((DATA/'center-examples.json').read_text(encoding='utf-8'))
    if isinstance(examples,dict): examples = examples.get('centers',examples.get('examples'))
    assert len(topics) == 8
    REPORTS.mkdir(parents=True,exist_ok=True)
    results = [update_page(rel, copy, examples, args.date) for rel,copy in topics.items()]
    (REPORTS/'generation.json').write_text(json.dumps({'date':args.date,'targets':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'targets':len(results),'changed':sum(x['changed'] for x in results),'faq':sum(x['faq'] for x in results)},ensure_ascii=False))


if __name__ == '__main__': main()
