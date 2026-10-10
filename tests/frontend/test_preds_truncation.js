// Self-check for the game-prediction table's "show more" cut.
//   node tests/frontend/test_preds_truncation.js
//
// A full week is 60+ games, which buried the projected bracket underneath it.
// renderPredictions now prints the first PRED_VISIBLE rows and parks the rest
// behind a button. This checks the split arithmetic and the toggle, which no
// CSS check can see.

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

const visibleMatch = src.match(/var PRED_VISIBLE = (\d+);/);
assert.ok(visibleMatch, 'PRED_VISIBLE should be declared in board.js');
const PRED_VISIBLE = Number(visibleMatch[1]);
assert.ok(
  PRED_VISIBLE >= 10 && PRED_VISIBLE <= 25,
  'PRED_VISIBLE should sit in the 10–25 range the board was designed for'
);

// ── Minimal DOM: only the four ids renderPredictions reaches for ──
function makeEl() {
  const classes = new Set();
  return {
    innerHTML: '', textContent: '', handler: null,
    classList: {
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c),
      toggle: (c) => (classes.has(c) ? (classes.delete(c), false) : (classes.add(c), true)),
    },
    addEventListener: function (_, fn) { this.handler = fn; },
    click: function () { this.handler(); },
  };
}

const els = {
  'tkr-preds': makeEl(),
  'tkr-preds-meta': makeEl(),
  'tkr-preds-body': makeEl(),
  'tkr-preds-rest': makeEl(),
  'tkr-preds-more': makeEl(),
};
// The rest/more elements only exist once the body markup declares them.
global.document = {
  getElementById: (id) => {
    if ((id === 'tkr-preds-rest' || id === 'tkr-preds-more') &&
        els['tkr-preds-body'].innerHTML.indexOf('id="' + id + '"') === -1) return null;
    return els[id] || null;
  },
};
els['tkr-preds-rest'].classList.add('hidden');

const preamble = `
  var esc = function (s) { return String(s); };
  var abbrName = function (n) { return String(n).slice(0, 3).toUpperCase(); };
  var stripeName = function () { return '#123456'; };
  var pairColor = function () { return '#654321'; };
  var CONF = { High: 'HIGH' };
  var set = function (id, txt) { document.getElementById(id).textContent = txt; };
  var PRED_VISIBLE = ${PRED_VISIBLE};
  var window = global.window;
  var live = global.live;
`;
// live.js stand-in: tests flip LIVE to mark games in progress.
const LIVE = {};
global.live = { find: (home) => LIVE[home] || null };
global.window = { live: global.live };

const { renderPredictions } = new Function(
  'var ENTRIES = [], IDS = null;' + extract('idOf') + extract('teamLink') +
  preamble + extract('predRow') + extract('renderPredictions') + extract('isLive') +
  extract('liveLine') + extract('periodLabel') + extract('vegasLine') + extract('weatherText') +
  'return { renderPredictions: renderPredictions };'
)();

function games(n) {
  return Array.from({ length: n }, (_, i) => ({
    game_id: i, week: 4, away_team: 'Away' + i, home_team: 'Home' + i,
    away_win_probability: 40, home_win_probability: 60,
    predicted_away_score: 21, predicted_home_score: 28,
    predicted_winner: 'Home' + i, is_neutral_site: false, confidence: 'High',
  }));
}

const countRows = (s) => (s.match(/tkr-prow/g) || []).length;

// ── Short list: every row visible, no button ──
renderPredictions(games(PRED_VISIBLE));
let body = els['tkr-preds-body'].innerHTML;
assert.strictEqual(countRows(body), PRED_VISIBLE, 'a short list should render in full');
assert.ok(body.indexOf('tkr-preds-more') === -1, 'a short list needs no expand button');
assert.ok(!els['tkr-preds'].classList.contains('hidden'), 'the card should be shown');

// ── Long list: every row still emitted, the overflow parked and hidden ──
const total = PRED_VISIBLE + 47;
renderPredictions(games(total));
body = els['tkr-preds-body'].innerHTML;
assert.strictEqual(countRows(body), total, 'no game may be dropped, only hidden');
const before = body.slice(0, body.indexOf('id="tkr-preds-rest"'));
assert.strictEqual(
  countRows(before), PRED_VISIBLE,
  'exactly PRED_VISIBLE rows belong outside the collapsed block'
);
assert.ok(
  body.indexOf('Show ' + (total - PRED_VISIBLE) + ' more') !== -1,
  'the button should name the remaining game count'
);

// ── The button toggles both ways ──
const more = document.getElementById('tkr-preds-more');
const rest = document.getElementById('tkr-preds-rest');
assert.ok(rest.classList.contains('hidden'), 'the overflow starts collapsed');
more.click();
assert.ok(!rest.classList.contains('hidden'), 'clicking should reveal the overflow');
assert.strictEqual(more.textContent, 'Show fewer');
more.click();
assert.ok(rest.classList.contains('hidden'), 'clicking again should re-collapse');
assert.strictEqual(more.textContent, 'Show ' + (total - PRED_VISIBLE) + ' more');

// ── An empty week hides the card entirely ──
renderPredictions([]);
assert.ok(els['tkr-preds'].classList.contains('hidden'), 'no games means no card');

// ── Live games float to the top; the rest keep kickoff order ──
LIVE['Home7'] = { status: 'in_progress', home: 'Home7', away: 'Away7', period: 2, clock: '5:00',
                  home_points: 7, away_points: 3, home_line_scores: [], away_line_scores: [] };
LIVE['Home3'] = { status: 'completed', home: 'Home3', away: 'Away3', home_points: 28, away_points: 21 };
// Names render abbreviated, so tag each row by its projected away score.
renderPredictions(games(8).map((g, i) => Object.assign(g, { predicted_away_score: i })));
body = els['tkr-preds-body'].innerHTML;
const order = (body.match(/tkr-proj">(\d+)-/g) || []).map((m) => Number(m.match(/(\d+)-/)[1]));
assert.deepStrictEqual(order, [7, 0, 1, 2, 3, 4, 5, 6], 'the live game leads, then kickoff order resumes');
assert.ok(body.indexOf('is-live') !== -1, 'live row carries its sub-line');
assert.ok(/FINAL[^<]*AWA 21–28 HOM/.test(body), 'finished games show the final score');

console.log('prediction table truncation self-check passed (' + PRED_VISIBLE + ' visible)');
