// Self-check for the "What changed this week?" panel.
//   node tests/frontend/test_whats_changed.js
//
// The panel reads rank_change, which is null for every team in week 0 - there
// is no previous week to diff against. Rendering it anyway produced a card of
// dashes claiming nothing moved, which is not the same statement as "the season
// has not started". It also has to get the direction right: rank_change is
// positive when a team moved UP, so the biggest riser is the maximum, and the
// biggest faller the minimum, of a signed number that is easy to sort backwards.

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

/** Minimal stand-in for the card element the renderer writes into. */
function makeCard() {
  return {
    innerHTML: '',
    classes: new Set(['hidden']),
    classList: {
      add(c) { this.owner.classes.add(c); },
      remove(c) { this.owner.classes.delete(c); },
    },
    get hidden() { return this.classes.has('hidden'); },
  };
}

function render(entries, week) {
  const card = makeCard();
  card.classList.owner = card;

  const preamble = `
    var ENTRIES = ${JSON.stringify(entries)};
    var CURRENT_WEEK = ${week};
    var esc = function (s) { return String(s == null ? '' : s); };
    var fmtPct = function (v) { return v == null ? '-' : v.toFixed(1) + '%'; };
    var deltaText = function (d) { return d == null ? '-' : (d > 0 ? '+' + d : String(d)); };
    var abbrOf = function (e) { return e.team_name.slice(0, 3).toUpperCase(); };
    var teamLink = function (name, inner) { return inner; };
    var document = { getElementById: function () { return CARD; } };
  `;
  new Function('CARD',
    preamble +
    extract('eloSwing') + extract('changedItem') + extract('changedCol') +
    extract('renderWhatChanged') +
    'renderWhatChanged();'
  )(card);
  return card;
}

const team = (name, rankChange, history, bid) => ({
  team_id: name.length, team_name: name, rank_change: rankChange,
  elo_history: history, bid_pct: bid,
});

// ── Week 0: nothing to compare against ───────────────────────────────────────
const preseason = [
  team('Alpha', null, [1500], null),
  team('Bravo', null, [1500], null),
];
assert.ok(render(preseason, 0).hidden,
  'the panel must stay hidden in the preseason, when no team has moved');

// Mid-season but no movement recorded yet - same story, no card.
assert.ok(render(preseason, 4).hidden,
  'with every rank_change null there is nothing to report');

// ── A normal week ────────────────────────────────────────────────────────────
const entries = [
  team('Alpha', 2, [1700, 1720], 90.0),
  team('Bravo', 9, [1600, 1680], 50.0),   // biggest riser, biggest Elo swing
  team('Delta', -7, [1650, 1610], 30.0),  // biggest faller
  team('Echo', -3, [1590, 1585], 10.0),
  team('Foxtrot', 5, [1560, 1575], 70.0),
  team('Golf', -1, [1550, 1548], 5.0),
];
const card = render(entries, 6);
assert.ok(!card.hidden, 'the panel should render once teams have moved');

const html = card.innerHTML;
assert.ok(html.includes('Week 6'), 'the card should name the week it describes');

/** Team abbreviations in the order they appear under a given heading. */
function section(heading) {
  const start = html.indexOf(heading);
  assert.notStrictEqual(start, -1, `no "${heading}" section`);
  const end = html.indexOf('tkr-changed-col', start + heading.length);
  const body = html.slice(start, end === -1 ? undefined : end);
  return [...body.matchAll(/tkr-changed-team">([A-Z]+)</g)].map((m) => m[1]);
}

// rank_change > 0 means the team moved up, so risers sort descending.
assert.deepStrictEqual(section('Biggest risers'), ['BRA', 'FOX', 'ALP'],
  'risers should be the largest positive rank_change first');
// Fallers are the most negative first - the easy bug is listing them backwards.
assert.deepStrictEqual(section('Biggest fallers'), ['DEL', 'ECH', 'GOL'],
  'fallers should be the most negative rank_change first');
// Elo swing is |last - previous|, regardless of which direction rank went.
assert.deepStrictEqual(section('Largest Elo swings')[0], 'BRA',
  'Bravo gained 80 Elo, the largest absolute swing');
assert.deepStrictEqual(section('Best playoff odds'), ['ALP', 'FOX', 'BRA'],
  'playoff odds should be the highest bid_pct first');

// The odds column is a standing, not a delta, and has to say so - there is no
// cached previous-week simulation to diff against.
assert.ok(/Current standing, not a weekly change/.test(html),
  'the playoff column must not imply it shows weekly movement');

// Only three entries per column, even with more candidates.
for (const heading of ['Biggest risers', 'Biggest fallers', 'Largest Elo swings']) {
  assert.ok(section(heading).length <= 3, `${heading} should show at most 3 teams`);
}

// A team with too little history must not crash the swing calculation.
const thin = render([team('Alpha', 3, [1700], 50.0), team('Bravo', -2, [], 10.0)], 3);
assert.ok(!thin.hidden && /Nothing yet\./.test(thin.innerHTML),
  'a column with no qualifying teams should say so rather than render empty');

console.log('what-changed self-check passed');
