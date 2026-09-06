// Self-check for the playoff odds strip under the projected bracket.
//   node tests/frontend/test_bracket_odds.js
//
// board.js is an IIFE with no exports, so — like the CSS grid self-check next
// door — this reads the source and pulls out just the functions under test.
//
// What it guards: the odds strip carries per-team probabilities that only exist
// when the projection came from a Monte Carlo run. The deterministic
// current-ratings fallback has no bid_pct, and rendering it would print a row of
// "undefined%" under the bracket.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  path.join(__dirname, '../../frontend/js/board.js'), 'utf8'
);

/** Pull a top-level `function name(...) { ... }` block out of the source by
 *  walking braces from its opening one. */
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

// Minimal stand-ins for the board helpers the odds strip leans on.
const preamble = `
  var esc = function (s) { return String(s); };
  var abbrName = function (s) { return s; };
  var stripeName = function () { return '#123456'; };
  var TeamVisuals = { confLabel: function (c) { return c; } };
  var host = { innerHTML: '', classList: { _v: new Set(),
    add: function (c) { this._v.add(c); }, remove: function (c) { this._v.delete(c); },
    has: function (c) { return this._v.has(c); } } };
  var document = { getElementById: function () { return host; } };
`;

const sandbox = new Function(
  'var ENTRIES = [], IDS = null;' + extract('idOf') + extract('teamLink') +
  preamble + extract('fmtPct') + extract('fmtRec') + extract('aqHint') +
  extract('confHint') +
  extract('oddsRow') + 'var RACE_CONTENDERS = 4;' + extract('confRaceRows') +
  extract('confRaces') + extract('methodPanel') + extract('renderOdds') +
  'return { fmtPct: fmtPct, fmtRec: fmtRec, aqHint: aqHint, confHint: confHint, ' +
  'confRaces: confRaces, renderOdds: renderOdds, host: host };'
)();

const { fmtPct, fmtRec, aqHint, confHint, confRaces, renderOdds, host } = sandbox;

// ── fmtPct: one decimal below 10%, whole numbers above, em dash for missing ──
assert.strictEqual(fmtPct(null), '—', 'absent probability must not print "null%"');
assert.strictEqual(fmtPct(undefined), '—');
assert.strictEqual(fmtPct(0), '0.0%');
assert.strictEqual(fmtPct(4.26), '4.3%', 'small odds keep a decimal');
assert.strictEqual(fmtPct(28.34), '28%', 'large odds round to whole numbers');
assert.strictEqual(fmtPct(100), '100%');

// ── fmtRec: mean wins/losses round to a whole record, em dash when absent ──
assert.strictEqual(fmtRec({ proj_wins: 8.4, proj_losses: 3.6 }), '8-4');
assert.strictEqual(fmtRec({ proj_wins: 9.5, proj_losses: 3.5 }), '10-4');
assert.strictEqual(fmtRec({ proj_wins: null, proj_losses: 3.6 }), '—',
  'a half-populated projection must not print "null-4"');
assert.strictEqual(fmtRec({}), '—');

// ── renderOdds gating ──
function team(id, seed, bid) {
  return {
    team_id: id, seed: seed, name: 'Team ' + id, bid_pct: bid,
    conf_title_pct: 10, title_pct: 2, proj_wins: 8.4, proj_losses: 3.6,
    ccg_pct: 25, conference_name: 'Test Conference',
  };
}
const field = Array.from({ length: 12 }, (_, i) => team(i + 1, i + 1, 30 - i));
const bubble = Array.from({ length: 13 }, (_, i) => team(100 + i, null, 18 - i));

// The Monte Carlo payload renders.
const teams = field.concat(bubble);
renderOdds({
  method: 'monte_carlo', field: field, bubble: bubble, teams: teams,
  runs: 10000, through_week: 3, generated_at: '2026-09-06T00:00:00Z',
});
assert.ok(!host.classList.has('hidden'), 'simulated projection must show the strip');
const rows = host.innerHTML.match(/class="bk-odds-row/g) || [];
assert.strictEqual(rows.length, 12 + 8, 'twelve seeds plus eight bubble teams');
assert.ok(host.innerHTML.includes('ON THE BUBBLE'), 'bubble section is labelled');
assert.ok(!/undefined/.test(host.innerHTML), 'no undefined leaked into the markup');
const recs = host.innerHTML.match(/class="bk-odds-rec"[^>]*>8-4</g) || [];
assert.strictEqual(recs.length, 12 + 8, 'every row carries a projected record');

// ── "How this is projected" panel ──
// Conference odds look wrong without their two halves shown, so the panel has
// to survive alongside the table rather than replace it.
assert.ok(/<details class="bk-work"/.test(host.innerHTML), 'method panel renders');
assert.ok(host.innerHTML.includes('10,000 simulated seasons'),
  'the panel reports the run count from the payload, not a hardcoded one');
assert.ok(host.innerHTML.includes('through week 3'), 'the panel reports the week');
assert.ok(/REACH CCG/.test(host.innerHTML), 'the conference race table renders');

// ── aqHint: the fifth bid is not a champion's bid ──
// Four auto-bids are conference champions; the fifth is the top Group of Six
// team, title or not. Calling that one a champion is simply wrong.
assert.strictEqual(aqHint({ auto_bid: false, is_champ: false }), '',
  'a team without an auto-bid gets no tooltip');
assert.ok(/conference champion/.test(aqHint({ auto_bid: true, is_champ: true })));
assert.ok(/does not require winning/.test(aqHint({ auto_bid: true, is_champ: false })),
  'the Group of Six bid must not be described as a championship');

// confHint spells out reach x convert = title, and never divides by zero.
assert.strictEqual(confHint({ ccg_pct: null }), '',
  'a payload without CCG odds gets no hint rather than "null%"');
assert.ok(/independent/i.test(confHint({ ccg_pct: 0, conf_title_pct: 0 })),
  'a team that can never reach a title game is explained, not shown as 0/0');
assert.ok(confHint({ ccg_pct: 20, conf_title_pct: 10 }).includes('50%'),
  'the conditional win rate is reach-normalised');

// The race table needs two teams in a conference to be a race at all, and only
// covers leagues the projection actually mentions.
const races = confRaces({
  teams: [
    { team_id: 1, name: 'A', conference_name: 'X', ccg_pct: 40, conf_title_pct: 22 },
    { team_id: 2, name: 'B', conference_name: 'X', ccg_pct: 30, conf_title_pct: 15 },
    { team_id: 3, name: 'C', conference_name: 'Y', ccg_pct: 50, conf_title_pct: 30 },
    { team_id: 4, name: 'D', conference_name: 'Z', ccg_pct: 10, conf_title_pct: 4 },
    { team_id: 5, name: 'E', conference_name: 'Z', ccg_pct: 9, conf_title_pct: 3 },
    { team_id: 6, name: 'F', conference_name: 'Ind', ccg_pct: 0, conf_title_pct: 0 },
    { team_id: 7, name: 'G', conference_name: 'Ind', ccg_pct: 0, conf_title_pct: 0 },
    { team_id: 8, name: 'H', conference_name: 'W', ccg_pct: 90, conf_title_pct: 60 },
    { team_id: 9, name: 'I', conference_name: 'W', ccg_pct: 80, conf_title_pct: 40 },
  ],
  field: [{ conference_name: 'X' }, { conference_name: 'Ind' }, { conference_name: 'W' }],
  bubble: [{ conference_name: 'Y' }],
});
assert.ok(races.includes('>X<'), 'a represented league with two teams is a race');
assert.ok(!races.includes('>Y<'), 'a one-team league is not a race');
assert.ok(!races.includes('>Z<'), 'a league absent from field and bubble is skipped');
assert.ok(!races.includes('>Ind<'),
  'independents play no title game, so an all-zero race is not shown');
// A small league where reaching the title game is easy must not outrank the
// league that actually produced the top seed.
assert.ok(races.indexOf('>X<') < races.indexOf('>W<'),
  'races follow the field order, not raw reach probability');
assert.strictEqual(confRaces({ teams: [], field: [], bubble: [] }), '',
  'no teams means no race table');
assert.strictEqual(
  confRaces({ teams: [{ conference_name: 'X', ccg_pct: null }], field: [], bubble: [] }), '',
  'a cached payload predating ccg_pct renders no race table instead of "null%"');

// ── Rows are ordered by the metric the bar draws, and auto-bids are marked ──
// Five of the twelve bids go to conference champions, so a low-probability
// champion can be seeded ahead of teams with far longer odds. The bars would
// jump around at random if the rows kept seed order, and the AQ tag is what
// explains a seeded team sitting below the bubble.
const jumbled = [
  { team_id: 1, seed: 1, name: 'Champ', bid_pct: 16.2, conf_title_pct: 15.6,
    title_pct: 0.7, auto_bid: true },
  { team_id: 2, seed: 2, name: 'AtLarge', bid_pct: 70.7, conf_title_pct: 23,
    title_pct: 11.6, auto_bid: false },
  { team_id: 3, seed: 3, name: 'Middle', bid_pct: 41.9, conf_title_pct: 11.5,
    title_pct: 4.1, auto_bid: false },
];
renderOdds({ method: 'monte_carlo', field: jumbled, bubble: [], teams: [], runs: 2000 });
const order = [...host.innerHTML.matchAll(/class="bk-odds-name">([^<]+)/g)]
  .map((m) => m[1]).slice(1); // drop the header's TEAM cell
assert.deepStrictEqual(order, ['AtLarge', 'Middle', 'Champ'],
  'rows sort by playoff odds, the metric the bar draws');
assert.deepStrictEqual(jumbled.map((t) => t.team_id), [1, 2, 3],
  'sorting is display-only and must not reorder the caller\'s field');
const aq = host.innerHTML.match(/class="bk-odds-aq"[^>]*>AQ</g) || [];
assert.strictEqual(aq.length, 1, 'only the auto-bid team carries the AQ tag');
assert.ok(/five automatic bids/.test(host.innerHTML),
  'the note explains why a bubble team can out-odds a seeded team');
assert.ok(/Seeds are straight by rating/.test(host.innerHTML),
  'the note explains why an at-large team can seed above an AQ team');

// The deterministic fallback must stay hidden rather than print empty columns.
renderOdds({
  method: 'current_ratings',
  field: field.map((t) => ({ ...t, bid_pct: undefined })),
  bubble: [],
});
assert.ok(host.classList.has('hidden'), 'current-ratings fallback hides the strip');
assert.strictEqual(host.innerHTML, '', 'hidden strip is emptied, not left stale');

// A monte_carlo payload that somehow lacks probabilities is also refused.
renderOdds({ method: 'monte_carlo', field: [team(1, 1, undefined)], bubble: [] });
assert.ok(host.classList.has('hidden'), 'missing bid_pct hides the strip');

// An empty field must not throw.
renderOdds({ method: 'monte_carlo', field: [], bubble: [] });
assert.ok(host.classList.has('hidden'));

// Bar widths stay inside the track even at 0%.
renderOdds({ method: 'monte_carlo', field: [team(1, 1, 0)], bubble: [] });
const widths = [...host.innerHTML.matchAll(/width:(\d+)%/g)].map((m) => Number(m[1]));
assert.ok(widths.every((w) => w >= 1 && w <= 100), 'bar width clamped to 1-100%');

console.log('bracket odds self-check passed');
