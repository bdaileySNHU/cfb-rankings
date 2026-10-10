// Self-check: the theme follows prefers-color-scheme, including live changes.
//   node tests/frontend/test_theme_follows_browser.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const theme = fs.readFileSync(path.join(__dirname, '../../frontend/js/theme.js'), 'utf8');

const html = { attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } };
const mq = { matches: false, listeners: [], addEventListener(ev, fn) { this.listeners.push(fn); } };
let themechanges = 0;

global.document = { documentElement: html };
global.window = {
  matchMedia: (q) => { assert.strictEqual(q, '(prefers-color-scheme: light)'); return mq; },
  dispatchEvent: (e) => { if (e.type === 'themechange') themechanges++; },
};
global.Event = function (name) { this.type = name; };

new Function(theme)();
assert.strictEqual(html.attrs['data-theme'], 'dark', 'dark browser -> dark theme');

mq.matches = true;
mq.listeners.forEach((fn) => fn());
assert.strictEqual(html.attrs['data-theme'], 'light', 'switching the OS to light flips the page live');
assert.strictEqual(themechanges, 2, 'charts and logos repaint on every change');

assert.ok(!/localStorage/.test(theme), 'no stored manual override any more');

console.log('theme follows browser self-check passed');
