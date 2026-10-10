// Theme system (spec §09): twelve tokens, two themes. Follows the browser's
// prefers-color-scheme, live, so the CSS keeps keying off [data-theme].
(function () {
  var light = window.matchMedia('(prefers-color-scheme: light)');

  function apply() {
    document.documentElement.setAttribute('data-theme', light.matches ? 'light' : 'dark');
    window.dispatchEvent(new Event('themechange'));
  }

  apply();
  light.addEventListener('change', apply);
})();
