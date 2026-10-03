(() => {
  'use strict';
  const library = document.querySelector('[data-learning-library]');
  if (library) {
    const input = library.querySelector('#guide-query');
    const audience = library.querySelector('#guide-audience');
    const buttons = [...library.querySelectorAll('[data-category]')];
    const cards = [...library.querySelectorAll('[data-guide-card]')];
    const groups = [...library.querySelectorAll('[data-guide-group]')];
    const result = library.querySelector('#guide-result');
    const empty = library.querySelector('#guide-empty');
    let category = 'all';
    const normalize = text => text.normalize('NFKC').toLocaleLowerCase('ko').trim();
    const filter = () => {
      const words = normalize(input.value).split(/\s+/).filter(Boolean);
      let count = 0;
      for (const card of cards) {
        const text = normalize(card.textContent);
        const matches = (category === 'all' || card.dataset.guideCategory === category)
          && (audience.value === 'all' || card.dataset.guideAudience.split(',').includes(audience.value))
          && words.every(word => text.includes(word));
        card.hidden = !matches;
        if (matches) count++;
      }
      for (const group of groups) group.hidden = ![...group.querySelectorAll('[data-guide-card]')].some(card => !card.hidden);
      for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.category === category));
      result.textContent = `${count}개 가이드를 볼 수 있습니다.`;
      empty.hidden = count > 0;
    };
    const reset = () => { input.value = ''; audience.value = 'all'; category = 'all'; filter(); input.focus(); };
    input.addEventListener('input', filter);
    audience.addEventListener('change', filter);
    buttons.forEach(button => button.addEventListener('click', () => { category = button.dataset.category; filter(); }));
    library.querySelectorAll('[data-reset-guides]').forEach(button => button.addEventListener('click', reset));
    library.querySelector('[data-guide-controls]').hidden = false;
    library.querySelector('[data-category-controls]').hidden = false;
    library.querySelector('[data-static-categories]').hidden = true;
    filter();
  }
  const form = document.querySelector('[data-guide-record]');
  if (!form) return;
  // Records stay in the page. No submission, storage or network request occurs here.
  const fields = [...form.querySelectorAll('textarea')];
  const date = form.querySelector('#record-date');
  const status = document.querySelector('#record-status');
  const save = form.querySelector('[data-record-save]');
  const print = form.querySelector('[data-record-print]');
  const preview = document.querySelector('[data-print-values]');
  const hasContent = () => fields.some(field => field.value.trim());
  const rows = () => fields.map(field => ({label: field.dataset.recordLabel, value: field.value.trim()}));
  const update = () => {
    save.disabled = print.disabled = !hasContent();
    const nodes = [];
    for (const row of rows()) {
      const dt = document.createElement('dt'); dt.textContent = row.label;
      const dd = document.createElement('dd'); dd.textContent = row.value || '미작성';
      nodes.push(dt, dd);
    }
    preview.replaceChildren(...nodes);
    document.querySelector('[data-print-date]').textContent = date.value ? `작성 날짜: ${date.value}` : '작성 날짜: 미작성';
    status.textContent = hasContent() ? '기록을 저장하거나 인쇄할 수 있습니다. 페이지를 떠나기 전에 저장해 주세요.' : '한 항목 이상 작성하면 기록을 저장하거나 인쇄할 수 있습니다.';
  };
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', update);
  save.addEventListener('click', () => {
    if (!hasContent()) return;
    const lines = [form.dataset.recordTitle, `작성 날짜: ${date.value || '미작성'}`, ''];
    for (const row of rows()) lines.push(`[${row.label}]`, row.value || '미작성', '');
    const text = lines.join('\n').replace(/\r\n?|\n/g, '\r\n');
    const blob = new Blob(['\uFEFF', text], {type: 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = `${form.dataset.recordSlug}-실천기록${date.value ? `-${date.value}` : ''}.txt`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    status.textContent = 'TXT 파일 저장을 요청했습니다. 내려받은 파일에서 작성 내용을 확인해 주세요.';
  });
  const restorePrint = () => document.body.classList.remove('lg-print-only');
  window.addEventListener('afterprint', restorePrint);
  print.addEventListener('click', () => {
    if (!hasContent()) return;
    update(); document.body.classList.add('lg-print-only');
    try { window.print(); } finally { restorePrint(); }
  });
  form.hidden = false;
  update();
})();
