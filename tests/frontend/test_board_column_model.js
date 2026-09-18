// Self-check for the ratings board's column model.
//   node tests/frontend/test_board_column_model.js
//
// The head row and the body rows used to be two hand-written markup strings
// sharing one CSS grid, so a cell added to one without the other silently
// shifted every column after it — ELO printed under the SOS heading, and so on.
// They now both come from the COLUMNS array in board.js, which makes that
// specific drift impossible but introduces three new ways to get it wrong:
//
//   1. the grid track list (--tkr-cols) not matching the rendered cell count,
//   2. a responsive rule dropping a column the board cannot do without,
//   3. a column preset selecting a group that no column belongs to.
//
// All three are checked below, at every width the array actually distinguishes.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  path.join(__dirname, '../../frontend/js/board.js'), 'utf8'
);

/** Pull a top-level `function name(...) { ... }` or `var NAME = [...];` out of
 *  the source, so the checks run against the real thing rather than a copy. */
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

function extractVar(name) {
  const start = src.indexOf('var ' + name + ' = ');
  assert.notStrictEqual(start, -1, 'missing var ' + name);
  const end = src.indexOf('\n  };', start);
  const endArr = src.indexOf('\n  ];', start);
  const stop = endArr !== -1 && (end === -1 || endArr < end) ? endArr + 5 : end + 5;
  return src.slice(start, stop);
}

// Board helpers a cell leans on, stubbed down to what affects cell count.
const preamble = `
  var esc = function (s) { return String(s == null ? '' : s); };
  var fmtElo = function (v) { return String(Math.round(v)); };
  var trendClass = function () { return 'trend-flat'; };
  var deltaText = function () { return '-'; };
  var stripeOf = function () { return '#123456'; };
  var logoImgFor = function () { return null; };
  var sparkline = function () { return '<svg class="tkr-spark"></svg>'; };
  var TeamVisuals = { confLabel: function (c) { return c || ''; } };
  var window = { innerWidth: 1400 };
  var activeView = 'all';
`;

const api = new Function(
  preamble +
  extract('fmtPct') +
  extractVar('COLUMNS') +
  extractVar('VIEWS') +
  extract('visibleColumns') +
  extract('rowHTML') +
  extract('headHTML') +
  `return {
     COLUMNS: COLUMNS, VIEWS: VIEWS,
     visibleColumns: visibleColumns, rowHTML: rowHTML, headHTML: headHTML,
     setWidth: function (w) { window.innerWidth = w; },
     setView: function (v) { activeView = v; },
   };`
)();

const entry = {
  team_id: 7, rank: 3, team_name: 'Ohio State', conference: 'P5',
  conference_name: 'Big Ten', wins: 9, losses: 1, elo_rating: 1822.4,
  rank_change: 2, off: 34.2, def: 15.1, sos: 0.631,
  bid_pct: 88.2, conf_title_pct: 41.0, title_pct: 17.5, proj_wins: 10.4,
  elo_history: [1700, 1720, 1755, 1790, 1822],
};

const countDivs = (s) => (s.match(/<div/g) || []).length;

// ── 1. Header cells, row cells and grid tracks agree at every width ──────────
// The widths below are every distinct minWidth in COLUMNS, plus one either
// side, so each rung of the responsive ladder is exercised.
const minWidths = [...new Set(api.COLUMNS.map((c) => c.minWidth))].sort((a, b) => a - b);
const widths = [320, ...minWidths.flatMap((w) => [w - 1, w]), 1400].filter((w) => w > 0);

let checked = 0;
for (const width of widths) {
  api.setWidth(width);
  const cols = api.visibleColumns();

  // Each cell() must emit exactly one top-level <div>; the head wraps its own.
  const rowCells = countDivs(api.rowHTML(entry, cols)) - 1;
  const headCells = countDivs(api.headHTML(cols)) - 1;
  const tracks = cols.map((c) => c.width).join(' ').trim().split(/\s+/).length;

  assert.strictEqual(
    rowCells, cols.length,
    `${width}px: ${cols.length} columns visible but rowHTML emitted ${rowCells} cells`
  );
  assert.strictEqual(
    headCells, cols.length,
    `${width}px: ${cols.length} columns visible but headHTML emitted ${headCells} cells`
  );
  // minmax(140px, 1fr) is one track written with a space in it.
  const minmaxes = cols.filter((c) => c.width.includes('minmax')).length;
  assert.strictEqual(
    tracks - minmaxes, cols.length,
    `${width}px: ${cols.length} columns but --tkr-cols declares ${tracks - minmaxes} tracks`
  );

  // Rank, team and rating are the board. Nothing may shed them.
  for (const key of ['rk', 'team', 'elo']) {
    assert.ok(
      cols.some((c) => c.key === key),
      `${width}px: column "${key}" must never be hidden`
    );
  }
  checked++;
}

// The narrowest viewport leaves exactly the irreducible three.
api.setWidth(320);
assert.deepStrictEqual(
  api.visibleColumns().map((c) => c.key), ['rk', 'team', 'elo'],
  'the narrowest board should be rank, team and rating alone'
);

// ── 2. Every column preset selects something, and always keeps the id group ──
api.setWidth(1400);
for (const name of Object.keys(api.VIEWS)) {
  api.setView(name);
  const cols = api.visibleColumns();
  assert.ok(cols.length >= 3, `view "${name}" shows only ${cols.length} columns`);
  for (const key of ['rk', 'team', 'elo']) {
    assert.ok(cols.some((c) => c.key === key), `view "${name}" dropped "${key}"`);
  }
  const groups = api.VIEWS[name].groups;
  if (groups) {
    // A preset naming a group no column belongs to would silently show less.
    for (const g of groups) {
      assert.ok(
        api.COLUMNS.some((c) => c.group === g),
        `view "${name}" selects group "${g}", which no column uses`
      );
    }
  }
}
api.setView('all');

// A preset ignores minWidth on purpose - the visitor asked for those columns.
api.setWidth(320);
api.setView('odds');
assert.ok(
  api.visibleColumns().some((c) => c.key === 'bid'),
  'an explicit preset should show its columns at any width'
);
api.setView('all');

// ── 3. The numbers that need explaining carry help text ──────────────────────
const NEEDS_HELP = ['elo', 'delta', 'off', 'def', 'sos', 'bid', 'confpct', 'natpct', 'projw', 'spark'];
for (const key of NEEDS_HELP) {
  const col = api.COLUMNS.find((c) => c.key === key);
  assert.ok(col, `no column with key "${key}"`);
  assert.ok(
    col.help && col.help.length > 25,
    `column "${key}" needs a plain-language definition in its help text`
  );
}

// The help text reaches assistive tech, not just the hover popover.
const head = api.headHTML(api.COLUMNS);
const elo = api.COLUMNS.find((c) => c.key === 'elo');
assert.ok(head.includes('aria-label="ELO: ' + elo.help.slice(0, 20)),
  'header help buttons should carry their definition in aria-label');
assert.strictEqual(
  (head.match(/<button type="button" class="th-help"/g) || []).length, NEEDS_HELP.length,
  'every helped column should render exactly one help button'
);

console.log(`board column model self-check passed (${checked} widths, ${api.COLUMNS.length} columns)`);
