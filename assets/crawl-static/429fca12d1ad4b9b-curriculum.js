/* Enhance static curriculum lists; no storage, account access or analytics. */
(() => {
  const normal=value=>value.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g,' ').trim();
  const params=new URLSearchParams(location.search);
  const accept=(select,value)=>{if([...select.options].some(o=>o.value===value))select.value=value;};
  const catalog=document.querySelector('[data-cu-catalog]');
  if(catalog){
    const query=document.getElementById('curriculum-query'),school=document.getElementById('curriculum-school'),grade=document.getElementById('curriculum-grade'),subject=document.getElementById('curriculum-subject');
    const cards=[...catalog.querySelectorAll('[data-cu-card]')],result=catalog.querySelector('[data-cu-result]'),empty=catalog.querySelector('[data-cu-empty]');
    const constrainGrades=()=>{
      const prefix={초등:'초',중등:'중',고등:'고'}[school.value];
      for(const option of grade.options)option.hidden=option.value!=='all'&&!!prefix&&!option.value.startsWith(prefix);
      if(prefix&&grade.value!=='all'&&!grade.value.startsWith(prefix))grade.value='all';
    };
    const update=()=>{
      const words=normal(query.value).split(' ').filter(Boolean);let count=0;
      cards.forEach(card=>{const show=words.every(w=>normal(card.dataset.search).includes(w))&&(school.value==='all'||card.dataset.school===school.value)&&(grade.value==='all'||card.dataset.grade===grade.value)&&(subject.value==='all'||card.dataset.subject===subject.value);card.hidden=!show;if(show)count++;});
      result.textContent=count+'개 과목별 안내';empty.hidden=count!==0;
    };
    accept(school,params.get('school'));accept(grade,params.get('grade'));accept(subject,params.get('subject'));constrainGrades();
    school.addEventListener('change',()=>{constrainGrades();update();});grade.addEventListener('change',()=>{if(grade.value!=='all')school.value={초:'초등',중:'중등',고:'고등'}[grade.value[0]];constrainGrades();update();});
    query.addEventListener('input',update);subject.addEventListener('change',update);
    catalog.querySelector('[data-cu-reset]').addEventListener('click',()=>{query.value='';school.value=grade.value=subject.value='all';constrainGrades();update();query.focus();});
    catalog.querySelector('[data-cu-controls]').hidden=false;update();
  }
  const electives=document.querySelector('[data-cu-electives]');
  if(electives){
    const query=document.getElementById('elective-query'),subject=document.getElementById('elective-subject'),type=document.getElementById('elective-type');
    const cards=[...electives.querySelectorAll('[data-cu-elective]')],result=electives.querySelector('[data-cu-result]'),empty=electives.querySelector('[data-cu-empty]');
    const update=()=>{let count=0;const words=normal(query.value).split(' ').filter(Boolean);cards.forEach(card=>{const show=words.every(w=>normal(card.dataset.search).includes(w))&&(subject.value==='all'||subject.value===card.dataset.subject)&&(type.value==='all'||type.value===card.dataset.type);card.hidden=!show;if(show)count++;});result.textContent=count+'개 과목 묶음';empty.hidden=count!==0;};
    accept(subject,params.get('subject'));query.addEventListener('input',update);subject.addEventListener('change',update);type.addEventListener('change',update);
    electives.querySelector('[data-cu-reset]').addEventListener('click',()=>{query.value='';subject.value=type.value='all';update();query.focus();});
    electives.querySelector('[data-cu-controls]').hidden=false;update();
  }
})();
