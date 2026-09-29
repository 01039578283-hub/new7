"""A factual, static high-school math directory with progressive filtering.

Private inputs retain confirmed grades and subject-specific W+ providers.
No new routes, external accounts, deployment, or reference-file edits.
"""
from __future__ import annotations
import argparse,collections,json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import unquote,urlparse
from lxml import html
from improve_high_math_pages import DOMAIN,esc,plain,serialized,fragment,replace,replace_text,href,link,grade,sha,walk_nodes,elements

ROOT=Path(__file__).resolve().parents[1]
HUB='과목별학원/고등학생수학학원/index.html'
REGIONS={'서울':'seoul','경기':'gyeonggi','인천':'incheon','부산':'busan','대구':'daegu','광주':'gwangju','대전':'daejeon','울산':'ulsan','세종':'sejong','강원':'gangwon','충북':'chungbuk','충남':'chungnam','전북':'jeonbuk','경북':'gyeongbuk','경남':'gyeongnam','제주':'jeju'}
SCHEMA=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)([\s\S]*?)(</script>)')

def region_id(region):return 'math-region-'+REGIONS[region]
def hub_link(label,region=None):
    return '<a data-math-directory-entry href="'+esc(href(HUB)+('#'+region_id(region) if region else '#hub-directory'))+'">'+esc(label)+'</a>'

def directory(facts):
    groups=collections.defaultdict(list)
    for f in facts:groups[f['region']].append(f)
    count=len(facts);centers=len({f['math_center'] for f in facts})
    s=f'''<section id="hub-directory" class="section section-compact nm-find" data-math-directory aria-labelledby="math-directory-title"><div class="nm-find-head"><h2 id="math-directory-title">고등 수학 수강 정보 찾기</h2><p>{count}개 지역 안내에서 연결된 수학센터 {centers}곳의 학년과 방문 주소를 비교하세요. 여러 동네가 같은 센터로 연결될 수 있습니다.</p></div>
<form class="nm-find-form" role="search" aria-label="고등 수학센터 찾기" hidden><div class="nm-find-fields"><label class="nm-find-field" for="math-query">동네·지점·주소·학교명<input id="math-query" name="query" type="search" placeholder="예: 은평점, 부천 중동, 진관고" autocomplete="off" aria-describedby="math-search-help"></label><label class="nm-find-field" for="math-region">센터 소재 지역<select id="math-region" name="region"><option value="">전체 지역</option>'''
    for region in REGIONS:
        if region in groups:s+='<option value="'+esc(region)+'">'+esc(region)+'</option>'
    s+='</select></label><label class="nm-find-field" for="math-grade">수학 안내 학년<select id="math-grade" name="grade"><option value="">전체 학년</option>'+''.join('<option value="'+g+'">'+g+'</option>' for g in ['고1','고2','고3'])+'</select></label><button type="reset">초기화</button></div><p id="math-search-help" class="nm-find-help">여러 단어를 띄어 쓰면 모든 단어를 포함하는 안내를 찾습니다. 지역 필터는 실제 방문 센터의 소재지를 기준으로 합니다.</p><div class="nm-find-tools"><button type="button" data-expand>모두 펼치기</button><button type="button" data-collapse>모두 접기</button><p role="status" aria-live="polite" aria-atomic="true" data-results>전체 '+str(count)+'개 지역 안내 · 연결 수학센터 '+str(centers)+'곳</p></div></form>'
    s+='<p class="nm-find-help">안내 학년은 현재 모집 여부를 뜻하지 않습니다. 화상 병행·학교별 제한 등 수강 조건도 함께 확인하세요. 학교명은 상담 자료 준비를 위한 참고 정보이며 학교별 전용반이나 제휴를 의미하지 않습니다.</p><noscript><p>지역을 펼쳐 동네별 수학 안내를 확인하세요. 검색과 학년 필터는 자바스크립트가 켜진 환경에서 사용할 수 있습니다.</p></noscript><p class="nm-find-empty" data-empty hidden>조건에 맞는 지역 안내가 없습니다. 검색어를 줄이거나 지역·학년 선택을 변경해 보세요. 초기화를 누르면 전체 목록으로 돌아갑니다.</p>'
    for region in REGIONS:
        if region not in groups:continue
        group=groups[region]
        s+='<details class="nm-find-group" id="'+region_id(region)+'" data-region-group="'+esc(region)+'"><summary><h3>'+esc(region)+'</h3><span data-group-count>'+str(len(group))+'개 지역 안내 · 연결 센터 '+str(len({f['math_center'] for f in group}))+'곳</span></summary><div class="nm-find-grid">'
        for f in group:
            s+='<article class="nm-find-card" data-math-card data-area="'+esc(f['area'])+'" data-region="'+esc(region)+'" data-grades="'+esc(' '.join(f['grades']))+'" data-center="'+esc(f['math_center'])+'"><h4>'+link(href(f['branch_path']),f['locality']+' 고등 수학 안내')+'</h4><p class="nm-find-center">'+esc(f['display_branch'])+'</p><p><span class="nm-find-grade">수학 '+esc(grade(f))+'</span></p><p class="nm-find-address">방문 주소: '+esc(f['address'])+'</p>'
            for note in f['directory_notes']:s+='<p class="nm-find-note">'+esc(note.replace('아래 주소','방문 주소'))+'</p>'
            if f['schools']:s+='<details class="nm-find-schools" data-school-list><summary>상담 참고 학교 '+str(len(f['schools']))+'곳</summary><p class="nm-find-school-names">'+esc(' · '.join(f['schools']))+'</p></details>'
            s+='</article>'
        s+='</div></details>'
    return s+'</section>'

def sync(raw,doc,rel,stamp,title=None,desc=None,facts=None):
    old=html.fromstring(raw);main=doc.xpath('//main')[0];old_main=plain(old.xpath('//main')[0])
    title=title or doc.xpath('//title/text()')[0];desc=desc or doc.xpath('//meta[@name="description"]/@content')[0]
    assert 0<len(desc)<=80 and desc.endswith('.'),(rel,desc)
    for e in elements(main,'mg-updated')+elements(main,'nm-updated'):replace_text(e,'내용 업데이트 2026년 9월 28일')
    canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
    newlinks=[DOMAIN+a.get('href') for a in main.xpath('.//a[@data-math-directory-entry]')]
    def schema(m):
        obj=json.loads(m[2])
        for n in walk_nodes(obj):
            ty=n.get('@type',[]);ty=ty if isinstance(ty,list) else [ty]
            if any(t in ['WebPage','CollectionPage','Article','BlogPosting'] for t in ty) and (n.get('url')==canonical or n.get('@id','').startswith(canonical+'#')):
                n['dateModified']=stamp
                if facts:
                    n['description']=desc
                    if 'name' in n:n['name']=title
                if newlinks:n['relatedLink']=list(dict.fromkeys(n.get('relatedLink',[])+newlinks))
            if 'Article' in ty and n.get('articleBody')==old_main:n['articleBody']=plain(main)
            if facts and 'ItemList' in ty and n.get('@id','').endswith('#directory'):
                n['name']='지역별 고등 수학 수강 안내';n['numberOfItems']=len(facts)
                ordered=sorted(facts,key=lambda f:list(REGIONS).index(f['region']))
                n['itemListElement']=[{'@type':'ListItem','position':i,'name':f['locality']+' 고등 수학 안내','url':DOMAIN+href(f['branch_path'])} for i,f in enumerate(ordered,1)]
        return m[1]+json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+m[3]
    raw=re.sub(r'<main\b[^>]*>[\s\S]*?</main>',lambda _:serialized(main),raw,count=1)
    raw=SCHEMA.sub(schema,raw)
    if facts:
        raw=re.sub(r'<title>[\s\S]*?</title>',lambda _:'<title>'+esc(title)+'</title>',raw,count=1)
        values={'description':desc,'og:description':desc,'twitter:description':desc,'og:title':title,'twitter:title':title,'og:image:alt':title,'twitter:image:alt':title}
        def meta(m):
            e=html.fromstring(m[0]);e=e if e.tag=='meta' else e.xpath('//meta')[0];key=e.get('name',e.get('property',''))
            return re.sub(r'content\s*=\s*(["\']).*?\1',lambda _:'content="'+esc(values[key])+'"',m[0],flags=re.S) if key in values else m[0]
        raw=re.sub(r'<meta\b[^>]*>',meta,raw,flags=re.I)
        raw=raw.replace('</head>','<link rel="stylesheet" href="/assets/high-math-directory.css?v=20260928"></head>',1)
        raw=raw.replace('</body>','<script src="/assets/high-math-directory.js?v=20260928-schools" defer></script></body>',1)
    return raw,{'title':title,'description':desc}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--facts',type=Path,required=True);ap.add_argument('--report-dir',type=Path,required=True);args=ap.parse_args()
    out=args.report_dir;data=json.loads(args.facts.read_text(encoding='utf-8'));facts=data['facts']
    manifest_path=out/'changes.json';previous=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    stamp=previous.get('dateModified') or datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
    originals={};planned={};metadata={};types={}
    def original(rel):
        backup=out/'before'/rel
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes((ROOT/rel).read_bytes())
        b=backup.read_bytes();originals[rel]=b;return b.decode('utf-8')
    def page(rel,raw,doc,kind,title=None,desc=None,facts=None):
        value,meta=sync(raw,doc,rel,stamp,title,desc,facts);planned[rel]=value.encode('utf-8');metadata[rel]=meta;types[rel]=kind
    raw=original(HUB);doc=html.fromstring(raw);main=doc.xpath('//main')[0]
    replace(main.get_element_by_id('hub-directory'),directory(facts))
    hero=elements(main,'academy-hero')[0]
    replace_text(hero.xpath('.//p[@class="lead"]')[0],'동네·지점·학교명으로 찾고 고1·고2·고3 안내 학년을 골라 보세요. 연결된 수학센터의 실제 주소와 수강 조건을 비교한 뒤 지역별 상세 안내로 이동할 수 있습니다.')
    replace_text(hero.xpath('.//aside/span')[0],'개 지역 안내 · 연결 수학센터 '+str(len({f['math_center'] for f in facts}))+'곳')
    page(HUB,raw,doc,'directory','지역별 고등 수학학원 | 학년·지점·학교로 찾기','전국 371개 지역의 고등 수학 안내에서 학년·지점·학교로 수업 정보를 찾고 연결 센터의 주소와 수강 조건을 비교하세요.',facts)
    entries=['index.html','과목별학원/index.html','전국학원/index.html','지점안내/index.html']+['지점안내/'+r+'/index.html' for r in REGIONS]
    for rel in entries:
        raw=original(rel);doc=html.fromstring(raw);main=doc.xpath('//main')[0]
        region=Path(rel).parts[1] if rel.startswith('지점안내/') and len(Path(rel).parts)==3 else None
        label=(region+' ' if region else '')+'고등 수학 학년·센터 찾기'
        hero=next(e for e in main if e.tag in ['section','header'])
        if rel=='과목별학원/index.html':container=elements(hero,'academy-hero-copy')[0]
        elif rel=='전국학원/index.html':container=elements(hero,'local-hero-card')[0]
        else:container=hero.find('div')
        boxes=elements(container,'mg-links')
        if boxes:boxes[0].append(fragment(hub_link(label,region)))
        else:container.append(fragment('<div class="mg-links">'+hub_link(label,region)+'</div>'))
        page(rel,raw,doc,'entry')
    for f in facts:
        rel=f['branch_path'];raw=original(rel);doc=html.fromstring(raw);main=doc.xpath('//main')[0]
        hero=elements(main,'mg-hero')[0];actions=elements(hero,'nm-actions')[0]
        actions.append(fragment(hub_link('다른 동네의 고등 수학 찾기',f['region'])))
        page(rel,raw,doc,'return-link')
    config=json.loads(original('seo-descriptions.json'));key='/'+Path(HUB).parent.as_posix();entry=config['pages'][key]
    entry['sources']=list(dict.fromkeys(entry['sources']+[entry['description'],metadata[HUB]['description']]))
    entry['description']=metadata[HUB]['description']
    planned['seo-descriptions.json']=(json.dumps(config,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    routes={('/'+Path(rel).parent.as_posix()+'/').replace('/./','/') for rel in metadata}
    def date(m):
        path=unquote(urlparse(re.search(r'<loc>(.*?)</loc>',m[0])[1]).path)
        return re.sub(r'<lastmod>.*?</lastmod>','<lastmod>'+stamp+'</lastmod>',m[0]) if path in routes else m[0]
    planned['sitemap.xml']=re.sub(r'<url>.*?</url>',date,original('sitemap.xml'),flags=re.S).encode('utf-8')
    records={}
    for rel,b in planned.items():
        current=(ROOT/rel).read_bytes()
        assert sha(current) in {sha(originals[rel]),previous.get('files',{}).get(rel,{}).get('after')},'Concurrent edit: '+rel
        records[rel]={'before':sha(originals[rel]),'after':sha(b)}
    for rel in ['assets/high-math-directory.js','assets/high-math-directory.css']:records[rel]={'before':None,'after':sha((ROOT/rel).read_bytes())}
    result={'status':'prepared','dateModified':stamp,'files':records,'metadata':metadata,'page_types':types,'pages':len(metadata),'directory_regions':len(REGIONS),'localities':len(facts),'centers':len({f['math_center'] for f in facts})}
    manifest_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for rel,b in planned.items():
        p=ROOT/rel
        if p.read_bytes()==b:continue
        temp=p.with_name(p.name+'.nm-discovery-tmp');temp.write_bytes(b);temp.replace(p)
    result['status']='complete';manifest_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','pages','directory_regions','localities','centers']},ensure_ascii=False))
if __name__=='__main__':main()
