// Theme system (spec §09): twelve tokens, two themes, default dark (fixed).
// localStorage key "staturday-theme" = "dark" | "light".
(function () {
  var KEY = 'staturday-theme';
  // Migrate legacy key once; default dark.
  var saved = localStorage.getItem(KEY) || localStorage.getItem('theme') || 'dark';
  if (saved !== 'light') saved = 'dark';
  document.documentElement.setAttribute('data-theme', saved);

  function current() { return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }

  function syncPill(pill) {
    if (pill) pill.setAttribute('data-active', current() === 'light' ? 'sun' : 'moon');
  }

  function setTheme(next) {
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(KEY, next);
    syncPill(document.getElementById('theme-toggle'));
    window.dispatchEvent(new Event('themechange'));
  }

  document.addEventListener('DOMContentLoaded', function () {
    var pill = document.getElementById('theme-toggle');
    if (!pill) return;
    syncPill(pill);
    function toggle() { setTheme(current() === 'light' ? 'dark' : 'light'); }
    pill.addEventListener('click', toggle);
    pill.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  });
})();
