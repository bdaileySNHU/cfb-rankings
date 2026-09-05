// Self-check for the team detail card's season schedule.
//   node tests/frontend/test_team_schedule.js
//
// The card walks weeks, not games: every regular-season week gets a row even
// when the team is idle, played weeks print the final, and the week the season
// is on is highlighted. An off-by-one in that walk silently drops a game or
// invents a bye, and the win probability has to be read off the side the team
// is actually on — home_win_probability is the *home* team's number, so a road
// game that reads it straight prints the opponent's odds under our name.

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

/** Run loadSchedule against a stubbed API and a stubbed card body. */
function render({ games, preds, currentWeek }) {
  const cell = { innerHTML: '' };
  const preamble = `
    var esc = function (s) { return String(s); };
    var abbrName = function (s) { return String(s); };
    var stripeName = function () { return '#123456'; };
    var ENTRIES = [{ team_id: 99, elo_rating: 1500 }];
    var CURRENT_WEEK = ${currentWeek};
    var window = { __tkrSeason: 2026 };
    var console = { error: function () {} };
    var document = { getElementById: function () { return CELL; } };
    var api = {
      getPredictions: function () { return Promise.resolve(PREDS); },
      getTeamSchedule: function () { return Promise.resolve({ games: GAMES }); },
    };
  `;
  const fn = new Function(
    'CELL', 'GAMES', 'PREDS',
    preamble + extract('loadSchedule') + 'return loadSchedule;'
  )(cell, games, preds);

  fn({ team_id: 1, elo_rating: 1600 });
  // The two stubbed promises resolve on the microtask queue.
  return Promise.resolve().then(() => Promise.resolve()).then(() => cell.innerHTML);
}

const rowsOf = (html) => html.split('<div class="tkr-sched-grid').slice(1);

(async () => {
  // A 3-week-old season: two played, one bye, one upcoming, plus a bowl.
  const games = [
    { game_id: 10, week: 1, opponent_id: 99, opponent_name: 'Rival', is_home: true,
      is_played: true, home_score: 31, away_score: 17 },
    { game_id: 11, week: 2, opponent_id: 99, opponent_name: 'Foe', is_home: false,
      is_played: true, home_score: 28, away_score: 21 },
    // week 3 is a bye
    { game_id: 12, week: 4, opponent_id: 99, opponent_name: 'Next', is_home: false,
      is_played: false },
    { game_id: 13, week: 16, opponent_id: 99, opponent_name: 'Playoff', is_home: true,
      is_played: false },
  ];
  const preds = [
    { game_id: 12, predicted_home_score: 24, predicted_away_score: 30,
      home_win_probability: 28, away_win_probability: 72 },
  ];

  const html = await render({ games, preds, currentWeek: 3 });
  const rows = rowsOf(html);

  // Weeks 1–14 all render (bye rows included), and week 16 tags along; the
  // empty postseason weeks 15 and 17–19 do not become phantom byes.
  assert.strictEqual(rows.length, 15, `expected 15 rows, got ${rows.length}`);
  assert.ok(html.includes('>CFP R1<'), 'postseason week should be labelled');
  assert.ok(!html.includes('>CONF<'), 'empty postseason week should not render a bye');
  assert.strictEqual((html.match(/>BYE</g) || []).length, 22,
    'weeks 3 and 5–14 are byes, two cells each');

  // Played weeks print the final and the result, not a projection.
  assert.ok(/WK1<[\s\S]*?31–17[\s\S]*?tkr-sched-odds fav">W</.test(rows[0]),
    'week 1 should show a win and its score');
  assert.ok(/WK2<[\s\S]*?21–28[\s\S]*?tkr-sched-odds dog">L</.test(rows[1]),
    'week 2 should show the road loss from this team\'s side');

  // The current week is highlighted, and only it.
  assert.strictEqual((html.match(/is-current/g) || []).length, 1, 'exactly one current row');
  assert.ok(rows[2].startsWith(' is-current'), 'week 3 (the current week) is highlighted');

  // A road favourite reads its own side of the prediction, not the home team's.
  assert.ok(rows[3].includes('>72%<'), 'week 4 should show this team\'s 72%, not the home 28%');
  assert.ok(rows[3].includes('30–24'), 'projection prints favourite first');

  // No prediction row falls back to Elo, and the home field goes to us.
  assert.ok(rows[14].includes('CFP R1'), 'last row is the playoff game');
  const elo = Number(rows[14].match(/>(\d+)%</)[1]);
  assert.ok(elo > 50 && elo < 100, `home Elo favourite should be over 50%, got ${elo}`);

  console.log('team schedule self-check passed (%d rows)', rows.length);
})();
