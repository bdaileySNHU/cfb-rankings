// Self-check for the ratings board's OFF/DEF heat cells.
//   node tests/frontend/test_heat_scale.js
//
// Both columns run one red-to-green scale, but they run it in opposite
// directions: scoring a lot is good, allowing a lot is not. Getting the sign
// wrong paints the worst defense in the country the same green as the best
// offense, and the mistake looks plausible on a board where most teams sit
// near the middle. This pins both directions, the uncolored center, and the
// unplayed case.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  path.join(__dirname, '../../frontend/js/board.js'), 'utf8'
);

function extract(name) {
  const start = src.indexOf('function ' + name + '(');
  assert.notStrictEqual(start, -1, 'missing function ' + name);
  let depth = 0;
  for (let i = src.indexOf('{', start); i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error('unbalanced braces in ' + name);
}

/** The heat constants are plain declarations; take them from the source. */
function constant(name) {
  const start = src.indexOf('var ' + name + ' =');
  assert.notStrictEqual(start, -1, 'missing constant ' + name);
  const end = src.indexOf('};', start);
  return src.slice(start, end + 2);
}

const heatBg = new Function(
  'var clamp = function (v, lo, hi) { return Math.max(lo, Math.min(hi, v)); };' +
  'var isLight = function () { return false; };' +
  constant('HEAT_GOOD') + constant('HEAT_BAD') + constant('HEAT') +
  extract('heatBg') + 'return heatBg;'
)();

const GREEN = 63;  // HEAT_GOOD red channel, dark theme
const RED = 232;   // HEAT_BAD red channel, dark theme

/** Parse `rgba(r,g,b,a)` into its channels. */
function parse(css) {
  const m = css.match(/rgba\((\d+),(\d+),(\d+),([\d.]+)\)/);
  assert.ok(m, 'expected an rgba color, got ' + css);
  return { r: Number(m[1]), a: Number(m[4]) };
}

// A team with no games played is left alone in both columns.
assert.strictEqual(heatBg('off', null), 'transparent');
assert.strictEqual(heatBg('def', null), 'transparent');

// Scoring: more is better.
assert.strictEqual(parse(heatBg('off', 40)).r, GREEN, 'a 40 ppg offense is green');
assert.strictEqual(parse(heatBg('off', 13)).r, RED, 'a 13 ppg offense is red');

// Allowing points: less is better — the same numbers flip color.
assert.strictEqual(parse(heatBg('def', 13)).r, GREEN, 'allowing 13 a game is green');
assert.strictEqual(parse(heatBg('def', 40)).r, RED, 'allowing 40 a game is red');

// The center of each scale is uncolored, so an average team does not shout.
for (const kind of ['off', 'def']) {
  assert.strictEqual(parse(heatBg(kind, 26)).a, 0, `${kind} at the center is unshaded`);
}

// Shading deepens with distance from center, and stops at the cap rather than
// running away on an outlier.
const near = parse(heatBg('off', 30)).a;
const far = parse(heatBg('off', 34)).a;
const capped = parse(heatBg('off', 36)).a;
assert.ok(near > 0 && far > near, `shading should deepen: ${near} then ${far}`);
assert.strictEqual(parse(heatBg('off', 80)).a, capped, 'an absurd value clamps to the cap');
assert.strictEqual(parse(heatBg('def', 0)).a, capped, 'a shutout season clamps to the same cap');

console.log('heat scale self-check passed');
