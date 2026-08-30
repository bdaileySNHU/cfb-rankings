// Self-check for isPlayed, the played/scheduled split on the games table.
//   node tests/frontend/test_game_status.js
//
// The bug this guards: scheduled games arrive with placeholder 0-0 scores, so a
// null-only check sent them down the results branch, where `home > away` is
// false and the away team was rendered as the winner of a game nobody played.

const assert = require('assert');
const { isPlayed } = require('../../frontend/js/date-utils.js');

// A real result is played, whichever side won.
assert.strictEqual(isPlayed({ home_score: 15, away_score: 10 }), true, 'home win is played');
assert.strictEqual(isPlayed({ home_score: 10, away_score: 15 }), true, 'away win is played');

// The regression: placeholder 0-0 is a scheduled game, not a tie.
assert.strictEqual(isPlayed({ home_score: 0, away_score: 0 }), false, '0-0 placeholder is scheduled');

// A shutout still counts — only BOTH sides at zero means unplayed.
assert.strictEqual(isPlayed({ home_score: 33, away_score: 0 }), true, 'home shutout is played');
assert.strictEqual(isPlayed({ home_score: 0, away_score: 33 }), true, 'away shutout is played');

// Missing scores in any form are not a result.
assert.strictEqual(isPlayed({ home_score: null, away_score: 3 }), false, 'null home score');
assert.strictEqual(isPlayed({ home_score: 3, away_score: null }), false, 'null away score');
assert.strictEqual(isPlayed({}), false, 'undefined scores');
assert.strictEqual(isPlayed(null), false, 'no game at all');

console.log('✓ test_game_status.js — all assertions passed');
