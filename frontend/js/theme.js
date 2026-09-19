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
    if (!pill) return;
    var light = current() === 'light';
    pill.setAttribute('data-active', light ? 'sun' : 'moon');
    // Pressed = light, because dark is the default the button toggles away from.
    pill.setAttribute('aria-pressed', light ? 'true' : 'false');
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
    // No keydown handler: #theme-toggle is a real <button>, so Enter and Space
    // already fire click. A manual one would double-toggle on Enter.
    pill.addEventListener('click', function () {
      setTheme(current() === 'light' ? 'dark' : 'light');
    });
  });
})();
