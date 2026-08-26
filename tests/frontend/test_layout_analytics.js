// Self-check for the Umami tag layout.js injects.
//   node tests/frontend/test_layout_analytics.js
//
// The tracker is created in script rather than pasted into eight <head> blocks,
// so nothing in the HTML shows whether it is still wired up. This runs layout.js
// against a stub document and inspects the <script> it appends: every public
// page gets one, admin.html does not, and the website id stays intact.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  path.join(__dirname, '../../frontend/js/layout.js'), 'utf8'
);

const WEBSITE_ID = '130cfa1d-3da5-4015-b68a-a927951aeaf8';
const SCRIPT_SRC = 'https://analytics.bdailey.com/script.js';

/** Run layout.js for one page path; return the scripts it appended to <head>. */
function inject(pathname) {
  const appended = [];
  const stubEl = () => ({
    dataset: {}, innerHTML: '', className: '', style: {},
    classList: { add() {}, remove() {}, contains: () => false, toggle: () => false },
    appendChild() {}, insertBefore() {}, addEventListener() {},
    insertAdjacentHTML() {},
    setAttribute() {}, querySelector: () => null, querySelectorAll: () => [],
  });
  global.location = { pathname: pathname, search: '', href: 'https://x/' + pathname };
  global.document = {
    // layout.js reads config off its own <script> tag.
    currentScript: Object.assign(stubEl(), { dataset: {} }),
    head: { appendChild: (el) => appended.push(el) },
    body: stubEl(),
    documentElement: stubEl(),
    createElement: () => stubEl(),
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
  };
  global.window = { addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) };
  try {
    new Function(src)();
  } catch (err) {
    // The chrome markup needs more DOM than this stub provides. The tracker is
    // injected before any of that, so a later failure does not hide a miss.
    if (appended.length === 0) throw err;
  }
  return appended;
}

// ── Every public page gets exactly one tracker, correctly configured ──
['/index.html', '/', '/games.html', '/team.html', '/simulator.html'].forEach(function (p) {
  const scripts = inject(p);
  assert.strictEqual(scripts.length, 1, p + ' should inject exactly one script');
  const tag = scripts[0];
  assert.strictEqual(tag.src, SCRIPT_SRC, p + ' should point at the Umami host');
  assert.strictEqual(tag.dataset.websiteId, WEBSITE_ID, p + ' should carry the website id');
  assert.strictEqual(tag.defer, true, p + ' should load the tracker deferred');
  assert.strictEqual(
    tag.dataset.domains, 'cfb.bdailey.com',
    p + ' should restrict counting to the production host'
  );
});

// ── The admin page stays out of the numbers ──
assert.strictEqual(
  inject('/admin.html').length, 0, 'admin.html must not load the tracker'
);

// ── The id is a real UUID, not a leftover placeholder ──
assert.ok(
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(WEBSITE_ID),
  'the website id should be a UUID'
);
assert.ok(
  src.indexOf(WEBSITE_ID) !== -1, 'layout.js should still hold the website id'
);

console.log('layout analytics self-check passed');
