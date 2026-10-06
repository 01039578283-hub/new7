(() => {
  'use strict';
  const directory = document.querySelector('[data-english-directory]');
  if (!directory) return;
  const form = directory.querySelector('form');
  const query = form.querySelector('[name="query"]');
  const region = form.querySelector('[name="region"]');
  const grade = form.querySelector('[name="grade"]');
  const inquiries = form.querySelector('[name="inquiries"]');
  const result = directory.querySelector('[data-results]');
  const empty = directory.querySelector('[data-empty]');
  const groups = [...directory.querySelectorAll('[data-region-group]')];
  const compact = value => value.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g, '');
  const cards = [...directory.querySelectorAll('[data-english-card]')].map(node => ({
    node,
    // Search actual fields separately. Exclusion notes are not school listings.
    searchFields: [node.dataset.area, ...[...node.querySelectorAll('.nm-find-center, .nm-find-address, .nm-find-school-names')].map(field => field.textContent)].map(compact),
    schools: node.querySelector('[data-school-list]'),
    region: node.dataset.region,
    grades: node.dataset.grades.split(' ').filter(Boolean),
    inquiryGrades: node.dataset.inquiryGrades.split(' ').filter(Boolean),
    center: node.dataset.center
  }));
  const gradeMatches = (card, value) => card.grades.includes(value)
    || (inquiries.checked && card.inquiryGrades.includes(value));
  const update = () => {
    const terms = query.value.trim().split(/\s+/).filter(Boolean).map(compact);
    const centers = new Set();
    let count = 0;
    for (const card of cards) {
      const visible = (!region.value || card.region === region.value)
        && (!grade.value || gradeMatches(card, grade.value))
        && terms.every(term => /^고[1-3]$/.test(term) ? gradeMatches(card, term) : card.searchFields.some(field => field.includes(term)));
      card.node.hidden = !visible;
      if (!visible) continue;
      count += 1;
      centers.add(card.center);
      if (card.schools) {
        const schoolNames = compact(card.schools.querySelector('p').textContent);
        card.schools.open = terms.some(term => schoolNames.includes(term));
      }
    }
    const filtering = Boolean(terms.length || region.value || grade.value || inquiries.checked);
    for (const group of groups) {
      const visibleCards = [...group.querySelectorAll('[data-english-card]')].filter(card => !card.hidden);
      group.hidden = visibleCards.length === 0;
      group.querySelector('[data-group-count]').textContent = `${visibleCards.length}개 지역 안내 · 연결 센터 ${new Set(visibleCards.map(card => card.dataset.center)).size}곳`;
      if (filtering && visibleCards.length) group.open = true;
    }
    result.textContent = `${filtering ? '검색 결과' : '전체'} ${count}개 지역 안내 · 연결 영어센터 ${centers.size}곳${inquiries.checked ? ' · 별도 문의 학년 포함' : ''}`;
    empty.hidden = count !== 0;
  };
  const applyRegionAnchor = () => {
    const target = groups.find(group => `#${group.id}` === location.hash);
    if (!target) return;
    query.value = '';
    grade.value = '';
    inquiries.checked = false;
    region.value = target.dataset.regionGroup;
    update();
    target.open = true;
  };
  form.addEventListener('submit', event => event.preventDefault());
  query.addEventListener('input', update);
  region.addEventListener('change', update);
  grade.addEventListener('change', update);
  inquiries.addEventListener('change', update);
  form.addEventListener('reset', event => {
    event.preventDefault();
    query.value = '';
    region.value = '';
    grade.value = '';
    inquiries.checked = false;
    groups.forEach(group => { group.open = false; });
    update();
    query.focus();
  });
  form.querySelector('[data-expand]').addEventListener('click', () => groups.forEach(group => { if (!group.hidden) group.open = true; }));
  form.querySelector('[data-collapse]').addEventListener('click', () => groups.forEach(group => { group.open = false; }));
  form.hidden = false;
  update();
  applyRegionAnchor();
  window.addEventListener('hashchange', applyRegionAnchor);
})();
