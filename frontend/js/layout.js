// Shared Ticker chrome (header bar + ticker tape) injected on every page so the
// markup lives in one place. Runs synchronously via document.currentScript so
// #theme-toggle exists before theme.js attaches.
//
// Per-page config via data-attributes on the <script> tag:
//   data-active="teams.html"   override highlighted nav link
//   data-season="false"        omit the season selector
(function () {
  var script = document.currentScript;
  var cfg = (script && script.dataset) || {};

  var currentPage = location.pathname.split('/').pop() || 'index.html';
  var active = cfg.active || currentPage;
  var showSeason = cfg.season !== 'false';
  var isBoard = currentPage === 'index.html' || currentPage === '';

  var links = [
    ['index.html', 'Rankings'],
    ['games.html', 'Games'],
    ['comparison.html', 'Compare'],
    ['elo-formula.html', 'How It Works'],
    ['simulator.html', 'Simulator'],
    ['matchup.html', 'Matchup'],
  ];
  var navLinks = links.map(function (l) {
    return '<a href="' + l[0] + '"' + (l[0] === active ? ' class="active"' : '') + '>' + l[1] + '</a>';
  }).join('');

  var seasonWrap = showSeason
    ? '<select id="nav-season-select" class="tkr-season" aria-label="Season"></select>' : '';

  var tape = isBoard
    ? '<div class="tkr-tape"><div class="tkr-tape-inner">' +
      '<div class="tkr-live">LIVE</div>' +
      '<div class="tkr-tape-viewport"><div class="tkr-tape-track" id="tkr-tape-track"></div></div>' +
      '</div></div>'
    : '';

  var html =
    '<header class="tkr-header">' +
      '<div class="tkr-header-inner">' +
        '<div class="tkr-brand">' +
          '<span class="tkr-badge">S</span>' +
          '<span class="tkr-wordmark">STATURDAY<span class="dot">.TKR</span></span>' +
          '<span class="tkr-week" id="tkr-week"></span>' +
        '</div>' +
        '<div class="tkr-header-right">' +
          '<nav class="tkr-nav">' + navLinks + '</nav>' +
          seasonWrap +
          '<div class="theme-pill" id="theme-toggle" role="button" tabindex="0" aria-label="Toggle theme">' +
            '<span class="seg seg-sun">☀</span><span class="seg seg-moon">☾</span>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</header>' + tape;

  if (script) {
    script.insertAdjacentHTML('afterend', html);
  } else {
    document.addEventListener('DOMContentLoaded', function () {
      document.body.insertAdjacentHTML('afterbegin', html);
    });
  }
})();
