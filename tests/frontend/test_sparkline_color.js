// Self-check for the ratings board sparkline stroke colour.
//   node tests/frontend/test_sparkline_color.js
//
// The line is drawn from elo_history, so it has to be coloured from the same
// series. Colouring it by rank_change put red on climbing lines and grey on
// moving ones whenever the field shifted around a team, which reads as a bug.

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

const sparkline = new Function(
  extract('trendVar') + extract('sparkline') + 'return sparkline;'
)();

function stroke(history) {
  const m = /stroke="var\((--[a-z0-9]+)\)"/.exec(sparkline(history));
  return m && m[1];
}

assert.strictEqual(stroke([1500, 1520, 1560]), '--pos', 'rising Elo is positive');
assert.strictEqual(stroke([1600, 1560, 1500]), '--neg', 'falling Elo is negative');
assert.strictEqual(stroke([1500, 1560, 1500]), '--fg3', 'net-flat Elo is neutral');
// Sub-point wobble rounds to the displayed integers, so it stays flat.
assert.strictEqual(stroke([1500.2, 1502, 1500.4]), '--fg3', 'rounding noise is flat');
assert.strictEqual(sparkline([1500]), '', 'a single point draws nothing');
assert.strictEqual(sparkline(null), '', 'no history draws nothing');

console.log('sparkline colour: ok');
