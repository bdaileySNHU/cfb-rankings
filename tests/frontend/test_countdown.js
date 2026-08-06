// Self-check for the kickoff countdown helpers.
//   node tests/frontend/test_countdown.js
//
// Covers the two things that can silently go wrong: timezone handling on
// offset-less game_date strings, and picking the right game out of the list.

const assert = require('assert');
const { parseUtc, pickNext } = require('../../frontend/js/countdown.js');

// game_date arrives UTC-naive. Parsing it as local time would skew the
// countdown by the viewer's offset, so it must be read as UTC.
assert.strictEqual(
  parseUtc('2026-08-29T16:00:00').toISOString(),
  '2026-08-29T16:00:00.000Z',
  'offset-less datetime must be read as UTC'
);

// SQLite hands back a space separator rather than "T".
assert.strictEqual(
  parseUtc('2026-08-29 16:00:00.000000').toISOString(),
  '2026-08-29T16:00:00.000Z',
  'space-separated datetime must parse'
);

// An explicit offset must be honoured, not double-applied.
assert.strictEqual(
  parseUtc('2026-08-29T12:00:00-04:00').toISOString(),
  '2026-08-29T16:00:00.000Z',
  'explicit offset must be preserved'
);

assert.strictEqual(parseUtc(null), null, 'null date yields null');
assert.strictEqual(parseUtc('not a date'), null, 'garbage date yields null');

// pickNext: soonest future unplayed game wins, regardless of list order.
const future = (mins) => new Date(Date.now() + mins * 60000)
  .toISOString().replace('Z', '');
const past = (mins) => new Date(Date.now() - mins * 60000)
  .toISOString().replace('Z', '');

const picked = pickNext([
  { game_date: future(500), is_processed: false, week: 2 },
  { game_date: future(10), is_processed: false, week: 1 },
  { game_date: future(90), is_processed: false, week: 1 },
]);
assert.strictEqual(picked.week, 1, 'soonest game wins');
assert.ok(picked.when.getTime() - Date.now() < 11 * 60000, 'picked the 10-minute game');

// Completed games and games already kicked off are skipped.
assert.strictEqual(
  pickNext([
    { game_date: past(30), is_processed: false, week: 1 },
    { game_date: future(60), is_processed: true, week: 1 },
    { game_date: future(120), is_processed: false, week: 1 },
  ]).when.getTime() - Date.now() > 119 * 60000,
  true,
  'past and processed games are skipped'
);

// Games without a date (TBD) must not crash the pick.
assert.strictEqual(
  pickNext([{ game_date: null, is_processed: false, week: 1 }]),
  null,
  'all-TBD list yields no target'
);

assert.strictEqual(pickNext([]), null, 'empty list yields no target');

console.log('countdown self-check passed');
