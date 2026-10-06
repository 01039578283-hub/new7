(() => {
  'use strict';
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\*/g, '').trim();
  const library = document.querySelector('[data-teacher-library]');
  if (library) {
    const query = library.querySelector('#teacher-query');
    const region = library.querySelector('#teacher-region');
    const program = library.querySelector('#teacher-program');
    const result = library.querySelector('#teacher-result');
    const empty = library.querySelector('#teacher-empty');
    const cards = [...library.querySelectorAll('[data-teacher-branch]')];
    const groups = [...library.querySelectorAll('[data-teacher-region]')];
    const filter = () => {
      const words = normalize(query.value).split(/\s+/).filter(Boolean);
      let count = 0;
      let profiles = 0;
      for (const card of cards) {
        const matches = (region.value === 'all' || card.dataset.region === region.value)
          && (program.value === 'all' || card.dataset.program === program.value)
          && words.every(word => normalize(card.dataset.search).includes(word));
        card.hidden = !matches;
        if (matches) { count++; profiles += Number(card.dataset.count); }
      }
      for (const group of groups) group.hidden = ![...group.querySelectorAll('[data-teacher-branch]')].some(card => !card.hidden);
      result.textContent = `${count}개 지점별 소개 · 선생님 소개 ${profiles.toLocaleString('ko-KR')}건`;
      empty.hidden = count > 0;
    };
    const reset = () => { query.value = ''; region.value = 'all'; program.value = 'all'; filter(); query.focus(); };
    query.addEventListener('input', filter);
    region.addEventListener('change', filter);
    program.addEventListener('change', filter);
    library.querySelectorAll('[data-teacher-reset]').forEach(button => button.addEventListener('click', reset));
    library.querySelector('[data-teacher-controls]').hidden = false;
    filter();
  }
  const branch = document.querySelector('[data-teacher-profiles]');
  if (!branch) return;
  const select = document.querySelector('#teacher-focus');
  const result = document.querySelector('#profile-result');
  const empty = document.querySelector('#profile-empty');
  const profiles = [...branch.querySelectorAll('[data-teacher-profile]')];
  const filter = () => {
    let count = 0;
    for (const profile of profiles) {
      profile.hidden = select.value !== 'all' && !profile.dataset.focus.split('|').includes(select.value);
      if (!profile.hidden) count++;
    }
    result.textContent = `선생님 소개 ${count}건을 볼 수 있습니다.`;
    empty.hidden = count > 0;
  };
  select.addEventListener('change', filter);
  document.querySelector('[data-profile-reset]').addEventListener('click', () => { select.value = 'all'; filter(); select.focus(); });
  document.querySelector('[data-profile-controls]').hidden = false;
  filter();
})();
