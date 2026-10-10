// Self-check for the live game cards.
//   node tests/frontend/test_game_card.js
//
// Numbers come from the design handoff (Oct 2026): Houston at the Kansas
// State 20, driving right, puts the ball at 75% and the line to gain at 75.8%.

const assert = require('assert');
const GC = require('../../frontend/js/game-card.js');
const TV = require('../../frontend/js/team-visuals.js');
const meta = require('../../frontend/data/teams-meta.json');

const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 0.05, `${msg}: ${a} != ${b}`);

// ── Field geometry ───────────────────────────────────────────────────────────
const sit = GC.parseSituation('4th & 1 at KSU 20');
assert.deepStrictEqual([sit.down, sit.toGo, sit.side, sit.yard, sit.text], [4, 1, 'KSU', 20, '4th & 1']);
let spot = GC.fieldSpot(sit, 'away', 'HOU', 'KSU');
near(spot.ball, 75, 'HOU ball at KSU 20');
near(spot.ltg, 75.83, 'line to gain one yard on');

// Home ball drives left; the field never flips.
spot = GC.fieldSpot(GC.parseSituation('2nd & 5 at ARK 13'), 'home', 'TENN', 'ARK');
near(spot.ball, (10 + 87) / 120 * 100, 'home ball on its own 13');
assert.strictEqual(spot.dir, -1);
near(spot.ltg, (10 + 82) / 120 * 100, 'line to gain toward the left');

// Goal to go puts the line to gain on the goal line.
spot = GC.fieldSpot(GC.parseSituation('1st & Goal at KSU 3'), 'away', 'HOU', 'KSU');
near(spot.ltg, 110 / 120 * 100, 'goal line');
assert.strictEqual(GC.parseSituation('1st & Goal at KSU 3').text, '1st & Goal');

// Midfield has no team; unknown abbreviation draws no field.
near(GC.fieldSpot(GC.parseSituation('2nd & 7 at 50'), 'away', 'A', 'B').ball, 50, 'midfield');
assert.strictEqual(GC.fieldSpot(GC.parseSituation('1st & 10 at XYZ 20'), 'away', 'A', 'B'), null);
assert.strictEqual(GC.parseSituation(null), null);

// ── Status words ─────────────────────────────────────────────────────────────
const g = (o) => Object.assign({ status: 'in_progress', period: 2, clock: '00:12' }, o);
assert.strictEqual(GC.statusText(g()), '● LIVE — 2ND QUARTER, 0:12 LEFT');
assert.strictEqual(GC.statusText(g({ clock: '00:00' })), 'HALFTIME');
assert.strictEqual(GC.statusText(g({ period: 1, clock: '0:00' })), 'END OF 1ST');
assert.strictEqual(GC.statusText(g({ period: 5 })), '● LIVE — OT1');
assert.strictEqual(GC.statusText(g({ status: 'completed', period: 6 })), 'FINAL / OT');
assert.strictEqual(GC.statusText(g({ status: 'scheduled', start_date: '2026-10-10T19:30:00.000Z' })), 'KICKOFF 3:30 PM ET');
assert.strictEqual(GC.clockLabel(g({ period: 3, clock: '10:53' })), 'Q3 10:53');
assert.strictEqual(GC.clockLabel(g({ period: 5 })), 'OT1');

// ── Last play ────────────────────────────────────────────────────────────────
assert.deepStrictEqual(
  GC.cleanPlay('(00:15) #44 G.Spetic field goal attempt from 23 yards GOOD (H: #1 C.Nix, LS: #45 D.Musgrove)'),
  { clock: '0:15', text: 'G. Spetic 23-yard field goal — good.' });
assert.strictEqual(
  GC.cleanPlay('(00:13) No Huddle-Shotgun #10 A.Colandrea pass complete deep middle to #2 J.Barney Jr. caught at NEB34, for 23 yards to the NEB11').text,
  'A. Colandrea pass to J. Barney Jr. for 23 yards.');
assert.strictEqual(
  GC.cleanPlay('(01:05) No Huddle-Shotgun #26 J.Belford rush right for 3 yards gain to the LU20 (#18 S.Bey), 1ST DOWN').text,
  'J. Belford rush for 3 yards. First down.');
assert.strictEqual(GC.cleanPlay('Shotgun #7 A.Flores sacked for loss of 8 yards to the Ohio41').text,
  'A. Flores sacked for a loss of 8.');
assert.strictEqual(GC.cleanPlay('(E. Kenney KICK)').text, 'E. Kenney extra point — good.');
// Anything unparsed comes back as the feed wrote it.
assert.strictEqual(GC.cleanPlay('End of 2nd quarter.').text, 'End of 2nd quarter.');

// ── Overtime columns ─────────────────────────────────────────────────────────
const labels = (a) => GC.periodCols({ away_line_scores: a, home_line_scores: a }).map((c) => c.label);
assert.deepStrictEqual(labels([7]), ['1', '2', '3', '4']);
assert.deepStrictEqual(labels([7, 0, 3, 7, 7, 3]), ['1', '2', '3', '4', 'OT1', 'OT2']);
assert.deepStrictEqual(labels([7, 0, 3, 7, 7, 7, 2]), ['1', '2', '3', '4', 'OT']);

// ── Team colours clear 3:1 on the card surface ───────────────────────────────
for (const [name, m] of Object.entries(meta)) {
  if (name.startsWith('_') || !m.primary) continue;
  const c = TV.readable(m.primary, { light: false, surface: '#1a1a1f' });
  assert.ok(TV.contrast(c, '#1a1a1f') >= 3 - 0.001, `${name}: ${c} under 3:1 on the card`);
}

// ── Renders every state without throwing, and escapes feed text ──────────────
const base = {
  home: 'Kansas State', away: 'Houston', period: 3, clock: '10:53', possession: 'away',
  situation: '4th & 1 at KSU 20', home_points: 17, away_points: 21, tv: 'ESPN',
  home_line_scores: [7, 10, 0], away_line_scores: [7, 7, 7], home_win_prob: 0.39,
  spread: -3.5, over_under: 52.5, last_play: '<script>x</script>',
};
const ctx = { meta: (n) => meta[n] };
for (const status of ['scheduled', 'in_progress', 'completed']) {
  const game = Object.assign({}, base, { status });
  for (const html of [GC.front(game, ctx), GC.games(game, ctx)]) {
    assert.ok(!html.includes('<script>'), `${status}: feed text escaped`);
  }
}
const liveHtml = GC.games(Object.assign({}, base, { status: 'in_progress' }), ctx);
assert.ok(liveHtml.includes('left:75.00%'), 'ball drawn at 75%');
assert.ok(liveHtml.includes('Houston ball, 4th and 1 at the Kansas State 20, driving toward the Kansas State end zone.'));
assert.ok(!GC.games(Object.assign({}, base, { status: 'in_progress', clock: '00:00', period: 2 }), ctx).includes('gc-field'),
  'no field at halftime');

console.log('game card: ok');
