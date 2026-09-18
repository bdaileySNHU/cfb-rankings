// Self-check for the theme toggle's semantics.
//   node tests/frontend/test_layout_theme_toggle.js
//
// The toggle used to be a <div role="button" tabindex="0"> with a hand-written
// keydown handler. That is a native <button> reimplemented badly: it announced
// no pressed state, and the manual Enter handling sat on top of the click a
// real button would already fire. This asserts we did not drift back, and that
// theme.js keeps aria-pressed in step with the theme it actually applied.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const read = (p) => fs.readFileSync(path.join(__dirname, '../../frontend/', p), 'utf8');
const layout = read('js/layout.js');
const theme = read('js/theme.js');
const boardCss = read('css/components/board.css');

// ── The injected markup ──────────────────────────────────────────────────────
const toggle = layout.slice(layout.indexOf('id="theme-toggle"') - 200,
                            layout.indexOf('id="theme-toggle"') + 300);

assert.ok(/<button type="button" class="theme-pill" id="theme-toggle"/.test(layout),
  'the theme toggle must be a native <button type="button">');
assert.ok(!/role="button"/.test(layout),
  'no role="button" anywhere in layout.js - use the real element');
assert.ok(!/id="theme-toggle"[^>]*tabindex/.test(layout),
  'a <button> is focusable already; tabindex is redundant');
assert.ok(/id="theme-toggle"[^>]*aria-label="Toggle theme"/.test(layout),
  'the toggle needs an accessible name - its label is two glyphs');
assert.ok(/id="theme-toggle"[^>]*aria-pressed=/.test(layout),
  'the toggle needs an initial aria-pressed state');
assert.ok(/class="seg seg-sun" aria-hidden="true"/.test(toggle),
  'the sun/moon glyphs are decorative and should be hidden from the a11y tree');

// ── theme.js behaviour ───────────────────────────────────────────────────────
assert.ok(!/addEventListener\('keydown'/.test(theme),
  'a native button fires click on Enter and Space; a keydown handler double-toggles');
assert.ok(/aria-pressed/.test(theme), 'theme.js must keep aria-pressed in step');

// Run the module against a stub DOM and check the attribute tracks the theme.
function runTheme() {
  const html = { attrs: { 'data-theme': null },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; } };
  const pill = { attrs: {}, listeners: {},
    setAttribute(k, v) { this.attrs[k] = v; },
    addEventListener(ev, fn) { this.listeners[ev] = fn; } };
  const ready = [];
  const store = {};

  global.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = v; },
  };
  global.document = {
    documentElement: html,
    getElementById: (id) => (id === 'theme-toggle' ? pill : null),
    addEventListener: (ev, fn) => { if (ev === 'DOMContentLoaded') ready.push(fn); },
  };
  global.window = { dispatchEvent() {} };
  global.Event = function (name) { this.type = name; };

  new Function(theme)();
  ready.forEach((fn) => fn());
  return { pill, html };
}

const { pill, html } = runTheme();

// Dark is the documented default, so the button starts un-pressed.
assert.strictEqual(html.getAttribute('data-theme'), 'dark');
assert.strictEqual(pill.attrs['aria-pressed'], 'false',
  'dark is the default, so the toggle starts not-pressed');
assert.strictEqual(pill.attrs['data-active'], 'moon');

pill.listeners.click();
assert.strictEqual(html.getAttribute('data-theme'), 'light');
assert.strictEqual(pill.attrs['aria-pressed'], 'true',
  'switching to light must set aria-pressed="true"');

pill.listeners.click();
assert.strictEqual(html.getAttribute('data-theme'), 'dark');
assert.strictEqual(pill.attrs['aria-pressed'], 'false');

// ── The <button> still has to look like the pill ─────────────────────────────
// Two rules share the selector; the multi-line one is the appearance block
// (the other is a one-line `flex-shrink` guard further up).
const pillStart = boardCss.indexOf('.theme-pill {\n');
assert.notStrictEqual(pillStart, -1, 'could not find the .theme-pill appearance rule');
const pillRule = boardCss.slice(pillStart, boardCss.indexOf('}', pillStart));
for (const decl of ['background: none', 'font: inherit']) {
  assert.ok(pillRule.includes(decl),
    `.theme-pill must reset the UA button styles (missing "${decl}")`);
}

console.log('theme toggle self-check passed');
