/* Figure 1: hovering, focusing or tapping a number shows the paper it stands for, with a link.
   The page works with scripts off: every number is already a plain link. */
(function () {
  var svg = document.getElementById('simplex');
  var card = document.getElementById('fig-card');
  if (!svg || !card) return;
  var box = svg.parentNode;
  var tokens = Array.prototype.slice.call(svg.querySelectorAll('a.token'));
  var current = null, hideTimer = null;
  var narrow = window.matchMedia('(max-width: 36rem)');

  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

  function show(tok) {
    clearTimeout(hideTimer);
    if (current === tok) return;
    current = tok;
    tokens.forEach(function (t) { t.classList.toggle('on', t === tok); });
    svg.classList.add('dim');
    var href = tok.getAttribute('href');
    card.innerHTML = '<p class="t">' + tok.getAttribute('data-title') + '</p>' +
      '<p class="d">' + tok.getAttribute('data-desc') + '</p>' +
      '<p class="state">' + (tok.getAttribute('data-link') ? '<a href="' + esc(href) + '">' + esc(tok.getAttribute('data-link')) + '</a>' : esc(tok.getAttribute('data-state'))) + '</p>';
    card.hidden = false;
    if (narrow.matches) { card.style.left = card.style.top = ''; return; }
    var b = box.getBoundingClientRect(), r = tok.getBoundingClientRect();
    var cw = card.offsetWidth, ch = card.offsetHeight;
    var left = r.right - b.left + 10;                       // to the right of the number…
    if (b.left + left + cw > window.innerWidth - 12) left = r.left - b.left - cw - 10;   // …or to its left
    var top = r.top - b.top + r.height / 2 - ch / 2;
    top = Math.max(-6, Math.min(top, b.height - ch + 30));
    card.style.left = left + 'px'; card.style.top = top + 'px';
  }
  function hide() {
    current = null; card.hidden = true; svg.classList.remove('dim');
    tokens.forEach(function (t) { t.classList.remove('on'); });
  }
  function hideSoon() { clearTimeout(hideTimer); hideTimer = setTimeout(hide, 220); }

  tokens.forEach(function (tok) {
    tok.addEventListener('mouseenter', function () { show(tok); });
    tok.addEventListener('mouseleave', hideSoon);
    tok.addEventListener('focus', function () { show(tok); });
    tok.addEventListener('blur', hideSoon);
    // first tap shows the card, the link inside it (or a second tap) opens the paper
    tok.addEventListener('click', function (ev) {
      if (current !== tok || card.hidden) { ev.preventDefault(); show(tok); }
    });
    tok.addEventListener('touchstart', function (ev) {
      if (current !== tok) { ev.preventDefault(); show(tok); }
    }, { passive: false });
  });
  card.addEventListener('mouseenter', function () { clearTimeout(hideTimer); });
  card.addEventListener('mouseleave', hideSoon);
  document.addEventListener('click', function (ev) {
    if (!card.contains(ev.target) && !svg.contains(ev.target)) hide();
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') hide(); });
})();
