/* Search is an enhancement: every center link exists in the initial HTML. */
(() => {
  const form = document.querySelector('[data-mg-search]');
  if (form) {
    const input = form.querySelector('input');
    const cards = [...document.querySelectorAll('[data-mg-center]')];
    const status = document.querySelector('[data-mg-count]');
    const empty = document.querySelector('[data-mg-empty]');
    const normalize = value => value.normalize('NFC').toLowerCase().replace(/\s+/g, ' ').trim();
    const refresh = () => {
      const words = normalize(input.value).split(' ').filter(Boolean);
      let found = 0;
      for (const card of cards) {
        const haystack = normalize(card.dataset.search || card.textContent);
        card.hidden = !words.every(word => haystack.includes(word));
        if (!card.hidden) found++;
      }
      status.textContent = words.length ? `검색 결과 ${found}곳` : `지점 ${found}곳의 안내를 볼 수 있습니다.`;
      empty.hidden = found > 0;
    };
    form.addEventListener('submit', event => event.preventDefault());
    input.addEventListener('input', refresh);
    form.addEventListener('reset', () => { input.value = ''; refresh(); input.focus(); });
    refresh();
  }
  document.querySelectorAll('[data-mg-video]').forEach(button => {
    button.addEventListener('click', () => {
      const id = button.dataset.mgVideo;
      if (!/^[\w-]{11}$/.test(id)) return;
      const frame = document.createElement('iframe');
      frame.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=0&rel=0`;
      frame.title = button.dataset.title;
      frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      const card = button.closest('.mg-video');
      card.querySelector('img').replaceWith(frame);
      button.remove();
    });
  });
  document.querySelectorAll('.mg-mobile a').forEach(a => a.addEventListener('click', () => { a.closest('details').open = false; }));
})();
