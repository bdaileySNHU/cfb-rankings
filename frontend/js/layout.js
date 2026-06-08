// Shared site chrome (header + primary nav) injected on every page so the
// markup lives in exactly one place. Runs synchronously during parsing via
// document.currentScript, so #theme-toggle and #nav-season-select exist before
// theme.js / season.js attach their DOMContentLoaded handlers.
//
// Per-page configuration via data-attributes on the <script> tag:
//   data-active="teams.html"        override which nav link is highlighted
//   data-brand-sub="Admin Dashboard" override the brand subtitle
//   data-season="false"              omit the season selector
(function () {
  var script = document.currentScript;
  var cfg = (script && script.dataset) || {};

  var currentPage = location.pathname.split('/').pop() || 'index.html';
  var active = cfg.active || currentPage;
  var brandSub = cfg.brandSub || 'College Football Analytics';
  var showSeason = cfg.season !== 'false';

  var links = [
    ['index.html', 'Rankings'],
    ['teams.html', 'All Teams'],
    ['games.html', 'Games'],
    ['comparison.html', 'Prediction Comparison'],
    ['elo-formula.html', 'How It Works'],
    ['simulator.html', 'Simulator'],
    ['matchup.html', 'Matchup'],
  ];

  var navLinks = links.map(function (l) {
    var cls = 'nav-link' + (l[0] === active ? ' active' : '');
    return '<a href="' + l[0] + '" class="' + cls + '">' + l[1] + '</a>';
  }).join('\n        ');

  var seasonWrap = showSeason
    ? '<div class="nav-season-wrap">\n' +
      '        <select id="nav-season-select" class="nav-season-select" aria-label="Season"></select>\n' +
      '      </div>'
    : '';

  var html =
    '<header class="site-header">\n' +
    '  <div class="header-inner">\n' +
    '    <div class="brand">\n' +
    '      <svg class="brand-icon" viewBox="0 0 24 24" width="28" height="28" fill="var(--accent)"><ellipse cx="12" cy="12" rx="10" ry="6.5" transform="rotate(-30 12 12)"/></svg>\n' +
    '      <span class="brand-name">Stat-urday</span>\n' +
    '      <span class="brand-sub">' + brandSub + '</span>\n' +
    '    </div>\n' +
    '    <div class="header-actions">\n' +
    '      <button class="theme-toggle" id="theme-toggle" aria-label="Toggle theme"></button>\n' +
    '    </div>\n' +
    '  </div>\n' +
    '</header>\n' +
    '<nav class="site-nav" id="site-nav">\n' +
    '  <div class="nav-inner">\n' +
    '    <button class="nav-hamburger" id="nav-hamburger" aria-label="Menu" onclick="document.getElementById(\'site-nav\').classList.toggle(\'nav-open\')">☰</button>\n' +
    '    <div class="nav-links" id="nav-links">\n' +
    '        ' + navLinks + '\n' +
    '    </div>\n' +
    '    ' + seasonWrap + '\n' +
    '  </div>\n' +
    '</nav>';

  if (script) {
    script.insertAdjacentHTML('afterend', html);
  } else {
    // Fallback if currentScript is unavailable: prepend to body on load.
    document.addEventListener('DOMContentLoaded', function () {
      document.body.insertAdjacentHTML('afterbegin', html);
    });
  }
})();
