// Self-check for the mobile nav layout.js injects.
//   node tests/frontend/test_layout_nav.js
//
// Under 720px the CSS hides .tkr-nav, so the burger button is the only way to
// reach Games, Compare, How It Works, Simulator and Matchup. Nothing in the
// HTML shows that, and the nav once shipped hidden with no replacement at all.
// This asserts the button is injected, wired, and that the CSS still opens the
// panel rather than just hiding the nav.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const read = (p) => fs.readFileSync(path.join(__dirname, '../../frontend/', p), 'utf8');
const src = read('js/layout.js');
const boardCss = read('css/components/board.css');

/** Run layout.js for one page path; return the chrome HTML it injected. */
function inject(pathname) {
  let injected = '';
  const listeners = {};
  const burger = {
    id: 'tkr-burger', attrs: {},
    addEventListener(ev, fn) { listeners[ev] = fn; },
    setAttribute(k, v) { this.attrs[k] = v; },
    closest: () => header,
  };
  const header = { classes: new Set(), classList: {
    toggle(c) {
      if (header.classes.has(c)) { header.classes.delete(c); return false; }
      header.classes.add(c); return true;
    },
  } };
  const stubEl = () => ({
    dataset: {}, innerHTML: '', className: '', style: {},
    classList: { add() {}, remove() {}, contains: () => false, toggle: () => false },
    appendChild() {}, addEventListener() {}, setAttribute() {},
    insertAdjacentHTML(pos, html) { injected += html; },
  });
  global.location = { pathname: pathname, search: '', href: 'https://x/' + pathname };
  global.document = {
    currentScript: stubEl(),
    head: { appendChild() {} },
    body: stubEl(),
    createElement: () => stubEl(),
    getElementById: (id) => (id === 'tkr-burger' ? burger : null),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
  };
  global.window = { addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) };
  new Function(src)();
  return { html: injected, burger: burger, header: header, listeners: listeners };
}

// ── The burger and every destination are injected on every page ──
const PAGES = ['/index.html', '/', '/games.html', '/comparison.html',
               '/elo-formula.html', '/simulator.html', '/matchup.html', '/admin.html'];
const LINKS = ['index.html', 'games.html', 'comparison.html',
               'elo-formula.html', 'simulator.html', 'matchup.html'];

PAGES.forEach(function (p) {
  const out = inject(p);
  assert.ok(out.html.indexOf('id="tkr-burger"') !== -1, p + ' should inject the burger button');
  assert.ok(out.html.indexOf('aria-expanded="false"') !== -1, p + ' burger should start collapsed');
  LINKS.forEach(function (href) {
    assert.ok(
      out.html.indexOf('href="' + href + '"') !== -1,
      p + ' should offer a link to ' + href
    );
  });
});

// ── Clicking it opens the panel and reports the state to screen readers ──
const out = inject('/index.html');
assert.ok(out.listeners.click, 'the burger should have a click handler');
out.listeners.click();
assert.ok(out.header.classes.has('nav-open'), 'clicking should open the nav');
assert.strictEqual(out.burger.attrs['aria-expanded'], true, 'open should be announced');
out.listeners.click();
assert.ok(!out.header.classes.has('nav-open'), 'clicking again should close the nav');
assert.strictEqual(out.burger.attrs['aria-expanded'], false, 'closed should be announced');

// ── The CSS still has somewhere for the button to lead ──
assert.ok(
  /\.tkr-header\.nav-open\s+\.tkr-nav\s*\{[^}]*display:\s*flex/.test(boardCss),
  'board.css should open .tkr-nav when the header carries .nav-open'
);
assert.ok(
  /\.tkr-burger\s*\{\s*display:\s*block/.test(boardCss),
  'board.css should show the burger inside the mobile breakpoint'
);

// ── Mobile tables scroll rather than clip ──
assert.ok(
  /\.tkr-table\s*\{\s*overflow-x:\s*auto/.test(boardCss),
  'board.css should let .tkr-table scroll horizontally on mobile'
);
assert.ok(
  !/\.tkr-table\s*\{[^}]*overflow:\s*hidden/.test(read('games.html')),
  'games.html must not reintroduce overflow:hidden on .tkr-table - it clips the table'
);

console.log('layout nav self-check passed');
