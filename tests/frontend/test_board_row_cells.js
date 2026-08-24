// Self-check for the ratings board's row and header cell counts.
//   node tests/frontend/test_board_row_cells.js
//
// The head and the body rows share one .tkr-grid template, so a cell added to
// rowHTML without a matching header cell (or the reverse) silently shifts every
// column after it — ELO printed under the SOS heading, and so on. CSS cannot
// catch that; the grid self-check next door only compares declared tracks to
// visible ones. This compares the two markup strings to each other.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  path.join(__dirname, '../../frontend/js/board.js'), 'utf8'
);

/** Pull a top-level `function name(...) { ... }` block out of the source. */
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

// The board helpers a row leans on, stubbed down to what affects cell count.
const preamble = `
  var esc = function (s) { return String(s); };
  var fmtElo = function (v) { return String(Math.round(v)); };
  var trendClass = function () { return 'trend-flat'; };
  var deltaText = function () { return '—'; };
  var stripeOf = function () { return '#123456'; };
  var logoImgFor = function () { return null; };
  var sparkline = function () { return '<svg class="tkr-spark"></svg>'; };
  var TeamVisuals = { confLabel: function (c) { return c || ''; } };
`;

const { rowHTML, fmtPct } = new Function(
  preamble + extract('fmtPct') + extract('rowHTML') +
  'return { rowHTML: rowHTML, fmtPct: fmtPct };'
)();

// The header lives inside renderGrid as a string literal; read it from source
// rather than running renderGrid, which touches the DOM and module state.
const headStart = src.indexOf("'<div class=\"tkr-grid tkr-head\">'");
assert.notStrictEqual(headStart, -1, 'could not find the .tkr-head markup');
const headSrc = src.slice(headStart, src.indexOf('</div>\';', headStart));

const EXPECTED = 14; // keep in step with tests/frontend/test_board_columns.js

function countDivs(s) {
  return (s.match(/<div/g) || []).length;
}

const entry = {
  team_id: 7, rank: 3, team_name: 'Ohio State', conference: 'P5',
  conference_name: 'Big Ten', wins: 4, losses: 1, elo_rating: 1838.5,
  rank_change: 2, sos: 0.601, off: 34.2, def: 15.8, elo_history: [1, 2, 3],
  bid_pct: 50.8, conf_title_pct: 18.8, title_pct: 7.4, proj_wins: 8.5,
};

// ── Body row: the wrapper plus one div per column ──
const row = rowHTML(entry);
assert.strictEqual(
  countDivs(row), EXPECTED + 1,
  'rowHTML should emit ' + EXPECTED + ' cells inside one wrapper div'
);

// ── Header: one div per column, wrapper included ──
assert.strictEqual(
  countDivs(headSrc), EXPECTED + 1,
  'the .tkr-head markup must carry the same number of cells as a row'
);

// ── The projection cells actually render their values ──
// fmtPct keeps a decimal below 10% and rounds above it, so 50.8 -> "51%".
['51%', '19%', '7.4%', '8.5'].forEach(function (v) {
  assert.ok(row.indexOf(v) !== -1, 'row should contain ' + v);
});

// ── A team with no simulation gets em dashes, never "undefined" ──
const bare = Object.assign({}, entry, {
  bid_pct: null, conf_title_pct: null, title_pct: null, proj_wins: null,
});
const bareRow = rowHTML(bare);
assert.strictEqual(
  countDivs(bareRow), EXPECTED + 1, 'the empty state must not drop cells'
);
assert.strictEqual(
  (bareRow.match(/—/g) || []).length >= 4, true,
  'four projection cells should read as em dashes'
);
assert.ok(!/undefined/.test(bareRow), 'missing odds must not print "undefined"');
assert.ok(!/null/.test(bareRow), 'missing odds must not print "null"');

console.log('board row cell self-check passed (' + EXPECTED + ' columns)');
