/* Filters and local links use only the rendered public directory; no tracking or storage. */
(() => {
  const library=document.querySelector('[data-education-library]');
  if(library){
    const query=document.getElementById('education-query'),topic=document.getElementById('education-topic'),audience=document.getElementById('education-audience'),kind=document.getElementById('education-kind');
    const cards=[...library.querySelectorAll('[data-education-card]')],groups=[...library.querySelectorAll('[data-education-group]')];
    const normalize=value=>value.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g,' ').trim();
    const update=()=>{
      const words=normalize(query.value).split(' ').filter(Boolean);let visible=0,education=0;
      cards.forEach(card=>{const show=words.every(word=>normalize(card.dataset.search).includes(word))&&(topic.value==='all'||card.dataset.topic===topic.value)&&(audience.value==='all'||card.dataset.audience.split('|').includes(audience.value))&&(kind.value==='all'||card.dataset.kind===kind.value);card.hidden=!show;if(show){visible++;if(card.dataset.kind==='education')education++;}});
      groups.forEach(group=>{const count=[...group.querySelectorAll('[data-education-card]')].filter(card=>!card.hidden).length;group.hidden=count===0;group.querySelector('[data-group-count]').textContent=count+'개 글';});
      document.getElementById('education-result').textContent=visible+'개 글 · 교육정보 '+education+'개 · 학습가이드 '+(visible-education)+'개';
      document.getElementById('education-empty').hidden=visible!==0;
    };
    [query,topic,audience,kind].forEach(control=>control.addEventListener(control===query?'input':'change',update));
    library.querySelectorAll('[data-education-reset]').forEach(button=>button.addEventListener('click',()=>{query.value='';topic.value=audience.value=kind.value='all';update();query.focus();}));
    library.querySelector('[data-education-controls]').hidden=false;update();
  }
  const picker=document.querySelector('[data-education-picker]');
  if(picker){
    const data=JSON.parse(picker.querySelector('[data-public-directory]').textContent),region=picker.querySelector('[data-local-region]'),branch=picker.querySelector('[data-local-branch]'),neighborhood=picker.querySelector('[data-local-neighborhood]');
    const branchLink=picker.querySelector('[data-branch-link]'),localLink=picker.querySelector('[data-neighborhood-link]'),actions=picker.querySelector('[data-selected-actions]'),status=picker.querySelector('[data-local-status]');
    const option=(label,value)=>{const node=document.createElement('option');node.textContent=label;node.value=value;return node;};
    const clear=()=>{actions.hidden=true;branchLink.hidden=localLink.hidden=true;branchLink.removeAttribute('href');localLink.removeAttribute('href');};
    const setNeighborhood=()=>{clear();const selected=data.find(item=>item.path===branch.value);if(!selected){status.textContent='지역과 지점을 선택하면 가까운 안내로 이동할 수 있습니다.';return;}actions.hidden=false;branchLink.hidden=false;branchLink.href=selected.path;branchLink.textContent=selected.name+' 지점 안내';const local=selected.neighborhoods.find(item=>item.path===neighborhood.value);if(local){localLink.hidden=false;localLink.href=local.path;localLink.textContent=local.name+' 동네 안내';}status.textContent=selected.name+'을 선택했습니다.'+(local?' '+local.name+' 안내도 함께 볼 수 있습니다.':selected.neighborhoods.length?' 동네를 선택하면 해당 안내도 볼 수 있습니다.':' 연결된 동네 안내는 전체 동네 목록에서 찾아보세요.');};
    const setBranch=()=>{clear();neighborhood.replaceChildren(option('동네를 선택하세요',''));const selected=data.find(item=>item.path===branch.value);neighborhood.disabled=!selected||selected.neighborhoods.length===0;if(selected)selected.neighborhoods.forEach(item=>neighborhood.append(option(item.name,item.path)));setNeighborhood();};
    const setRegion=()=>{clear();branch.replaceChildren(option('지점을 선택하세요',''));data.filter(item=>item.region===region.value).forEach(item=>branch.append(option(item.name,item.path)));branch.disabled=region.value==='';setBranch();};
    region.addEventListener('change',setRegion);branch.addEventListener('change',setBranch);neighborhood.addEventListener('change',setNeighborhood);picker.querySelector('[data-picker-controls]').hidden=false;setRegion();
  }
})();
