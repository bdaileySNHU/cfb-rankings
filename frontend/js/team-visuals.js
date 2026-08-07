// Shared team display helpers: brand-colour contrast and CFBD logo URLs.
//
// Two related problems this solves:
//
//   1. Team brand colours are frequently near-black (8 teams are literally
//      #000000, and 92 of 135 fall below the 3:1 WCAG non-text contrast
//      minimum against the dark panel). Painted straight onto #121419 they are
//      invisible — UConn's #000e2f scores 1.03:1.
//
//   2. Logos have the same failure mode, which is why CFBD publishes a
//      `logos-dark` variant of every mark. Picking the variant by theme is the
//      whole fix, and it has to re-pick when the theme toggles.
//
// Exposed globally as window.TeamVisuals; also exported for the node self-check.
(function () {
  var MIN_CONTRAST = 3.0;   // WCAG 2.1 SC 1.4.11, non-text contrast
  var DARK_SURFACE = '#121419';  // --panel, dark theme
  var LIGHT_SURFACE = '#ffffff'; // --panel, light theme

  function isLightTheme() {
    return typeof document !== 'undefined' &&
      document.documentElement.getAttribute('data-theme') === 'light';
  }

  function parseHex(hex) {
    var m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(hex || '').trim());
    if (!m) return null;
    var h = m[1];
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function toHex(rgb) {
    return '#' + rgb.map(function (v) {
      var s = Math.round(Math.max(0, Math.min(255, v))).toString(16);
      return s.length === 1 ? '0' + s : s;
    }).join('');
  }

  /** WCAG relative luminance. */
  function luminance(rgb) {
    var c = rgb.map(function (v) {
      var s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }

  /** WCAG contrast ratio between two rgb triplets, 1..21. */
  function contrast(a, b) {
    var la = luminance(a), lb = luminance(b);
    var hi = Math.max(la, lb), lo = Math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
  }

  function rgbToHsl(rgb) {
    var r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var h = 0, s = 0, l = (max + min) / 2;
    var d = max - min;
    if (d !== 0) {
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === r) h = ((g - b) / d + (g < b ? 6 : 0));
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h /= 6;
    }
    return [h, s, l];
  }

  function hslToRgb(hsl) {
    var h = hsl[0], s = hsl[1], l = hsl[2];
    if (s === 0) { var v = l * 255; return [v, v, v]; }
    function hue2rgb(p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    }
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    return [hue2rgb(p, q, h + 1 / 3) * 255, hue2rgb(p, q, h) * 255, hue2rgb(p, q, h - 1 / 3) * 255];
  }

  /**
   * Nudge a brand colour until it clears MIN_CONTRAST against the current
   * theme's panel, preserving hue so the team is still recognisable — navy
   * stays navy, just light enough to see.
   *
   * Pure black and pure white have no hue to preserve, so they get lifted to a
   * neutral grey that reads on either surface.
   */
  function readable(hex, opts) {
    opts = opts || {};
    var lightTheme = opts.light !== undefined ? opts.light : isLightTheme();
    var surface = parseHex(opts.surface || (lightTheme ? LIGHT_SURFACE : DARK_SURFACE));
    var rgb = parseHex(hex);
    if (!rgb || !surface) return hex;

    if (contrast(rgb, surface) >= MIN_CONTRAST) return toHex(rgb);

    var hsl = rgbToHsl(rgb);
    // On a dark surface lighten; on a light surface darken.
    var step = lightTheme ? -0.02 : 0.02;
    for (var i = 0; i < 60; i++) {
      hsl[2] = Math.max(0, Math.min(1, hsl[2] + step));
      // Test the *rounded* colour: hslToRgb returns floats, and rounding them
      // to a hex triplet can nudge the ratio back under the threshold — Baylor's
      // #154734 landed at 2.9996:1 that way.
      var candidate = toHex(hslToRgb(hsl));
      if (contrast(parseHex(candidate), surface) >= MIN_CONTRAST) return candidate;
      if (hsl[2] <= 0 || hsl[2] >= 1) break;
    }
    // Ran out of headroom (very desaturated colours) — fall back to a neutral
    // that is guaranteed to clear the bar.
    return lightTheme ? '#4a4a4a' : '#b8bcc4';
  }

  // ── Telling two teams apart in a split bar ──────────────────────────────────

  var MIN_PAIR_CONTRAST = 1.6;  // lightness separation that reads at a glance
  var MIN_HUE_DELTA = 40;       // degrees; below this two colours read as "same"
  var GREY_SAT = 0.15;          // below this, hue carries no information

  function hueDegrees(hsl) { return hsl[0] * 360; }

  /**
   * True when two colours are hard to tell apart side by side.
   *
   * Lightness alone can separate them (dark red vs pink), and hue alone can
   * (red vs blue) — it takes *both* being close to be a problem. Near-greys are
   * judged on lightness only, since their hue is noise.
   */
  function tooSimilar(a, b) {
    var ra = parseHex(a), rb = parseHex(b);
    if (!ra || !rb) return false;
    if (contrast(ra, rb) >= MIN_PAIR_CONTRAST) return false;

    var ha = rgbToHsl(ra), hb = rgbToHsl(rb);
    if (ha[1] < GREY_SAT || hb[1] < GREY_SAT) return true;

    var d = Math.abs(hueDegrees(ha) - hueDegrees(hb));
    if (d > 180) d = 360 - d;
    return d < MIN_HUE_DELTA;
  }

  /**
   * Pick a colour for `away` that is distinguishable from `home` in a split bar.
   *
   * Ladder, stopping at the first rung that works:
   *   1. the away team's own colour, if it already separates
   *   2. the away team's alternate ("away") colour — keeps team identity
   *   3. lightness-shift the away colour, preserving hue
   *   4. a neutral, as a last resort
   *
   * Every candidate must also clear the panel contrast floor, so nothing
   * returned here is invisible against the background.
   */
  function distinguish(awayMeta, homeColor, opts) {
    opts = opts || {};
    var lightTheme = opts.light !== undefined ? opts.light : isLightTheme();
    var o = { light: lightTheme };
    var home = readable(homeColor, o);

    var away = readable((awayMeta && awayMeta.primary) || '', o);
    if (!parseHex(away)) return away;
    if (!tooSimilar(away, home)) return away;

    // 2. The away team's alternate colour — still their brand.
    if (awayMeta && awayMeta.secondary) {
      var alt = readable(awayMeta.secondary, o);
      if (parseHex(alt) && !tooSimilar(alt, home)) return alt;
    }

    // 3. Shift lightness, keeping hue so it still reads as the team's colour.
    var surface = parseHex(lightTheme ? LIGHT_SURFACE : DARK_SURFACE);
    var hsl = rgbToHsl(parseHex(away));
    for (var dir = 0; dir < 2; dir++) {
      var step = dir === 0 ? (lightTheme ? 0.03 : -0.03) : (lightTheme ? -0.03 : 0.03);
      var l = hsl[2];
      for (var i = 0; i < 33; i++) {
        l = Math.max(0, Math.min(1, l + step));
        var cand = toHex(hslToRgb([hsl[0], hsl[1], l]));
        if (!tooSimilar(cand, home) && contrast(parseHex(cand), surface) >= MIN_CONTRAST) {
          return cand;
        }
        if (l <= 0 || l >= 1) break;
      }
    }

    // 4. Neutral. Distinguishable from any hue, still readable on the panel.
    return lightTheme ? '#4a4a4a' : '#b8bcc4';
  }

  /** CFBD logo URL for a team meta entry, or null when the team has no id. */
  function logoUrl(meta, size, opts) {
    opts = opts || {};
    var id = meta && meta.cfbd_id;
    if (id == null) return null;
    var lightTheme = opts.light !== undefined ? opts.light : isLightTheme();
    // CFBD publishes 16/32/48/64/96/128/256/500. Ask for the smallest that
    // covers the render size so a 32px row cell isn't fetching a 500px png.
    var sizes = [16, 32, 48, 64, 96, 128, 256, 500];
    var want = size || 64;
    var pick = sizes.filter(function (s) { return s >= want; })[0] || 500;
    // logos-dark is the light-on-dark variant, for the dark theme.
    var dir = lightTheme ? 'logos' : 'logos-dark';
    return 'https://cdn.collegefootballdata.com/' + dir + '/' + pick + '/' + id + '.png';
  }

  /**
   * <img> markup for a team logo, carrying both variants so the theme toggle
   * can repoint it without a re-render. Returns '' when the team has no id,
   * letting callers fall back to their existing stripe or initials.
   */
  function logoImg(meta, size, alt) {
    if (!meta || meta.cfbd_id == null) return '';
    var light = logoUrl(meta, size, { light: true });
    var dark = logoUrl(meta, size, { light: false });
    var src = isLightTheme() ? light : dark;
    return '<img class="team-logo" src="' + src + '"' +
      ' data-logo-light="' + light + '" data-logo-dark="' + dark + '"' +
      ' width="' + size + '" height="' + size + '"' +
      ' alt="' + String(alt || '').replace(/"/g, '&quot;') + '"' +
      ' loading="lazy" decoding="async">';
  }

  /** Repoint every rendered logo when the theme changes. */
  function syncLogos() {
    if (typeof document === 'undefined') return;
    var attr = isLightTheme() ? 'data-logo-light' : 'data-logo-dark';
    var imgs = document.querySelectorAll('img.team-logo[data-logo-dark]');
    for (var i = 0; i < imgs.length; i++) {
      var next = imgs[i].getAttribute(attr);
      if (next && imgs[i].getAttribute('src') !== next) imgs[i].setAttribute('src', next);
    }
  }

  // Display names for conferences whose CFBD label is too long for a table
  // cell. Presentation only — the stored value stays as CFBD sends it, because
  // ranking_service matches independents on the exact string.
  var CONF_LABELS = {
    'FBS Independents': 'Ind',
    'Independents': 'Ind',
    'Independent': 'Ind',
  };

  function confLabel(name) {
    if (!name) return '';
    return CONF_LABELS[name] || name;
  }

  var api = {
    confLabel: confLabel,
    readable: readable,
    tooSimilar: tooSimilar,
    distinguish: distinguish,
    contrast: function (a, b) {
      var ra = parseHex(a), rb = parseHex(b);
      return ra && rb ? contrast(ra, rb) : null;
    },
    logoUrl: logoUrl,
    logoImg: logoImg,
    syncLogos: syncLogos,
    MIN_CONTRAST: MIN_CONTRAST,
    DARK_SURFACE: DARK_SURFACE,
    LIGHT_SURFACE: LIGHT_SURFACE,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') {
    window.TeamVisuals = api;
    window.addEventListener('themechange', syncLogos);
  }
})();
