// Self-check for the list paging helper.
//   node tests/frontend/test_paging.js
//
// The bug this guards: games.html asked for limit=200 against a ~900-game
// season, so every week outside the first page rendered empty.

const assert = require('assert');
const { fetchAllPages } = require('../../frontend/js/paging.js');

// Build a fake endpoint over `total` rows that honours skip/limit and records
// how it was called.
function fakeEndpoint(total) {
  const calls = [];
  const rows = Array.from({ length: total }, (_, i) => i);
  const fetchPage = (skip, limit) => {
    calls.push([skip, limit]);
    return Promise.resolve(rows.slice(skip, skip + limit));
  };
  return { fetchPage, calls };
}

(async () => {
  // A real 2026 season: 894 games must all come back, not the first page.
  const season = fakeEndpoint(894);
  const all = await fetchAllPages(season.fetchPage);
  assert.strictEqual(all.length, 894, 'every row must be collected');
  assert.strictEqual(all[0], 0, 'first row preserved');
  assert.strictEqual(all[893], 893, 'last row preserved');
  assert.deepStrictEqual(season.calls, [[0, 500], [500, 500]], 'should page exactly twice');

  // Fits in one page: must not make a second request.
  const small = fakeEndpoint(12);
  assert.strictEqual((await fetchAllPages(small.fetchPage)).length, 12);
  assert.strictEqual(small.calls.length, 1, 'a short first page ends paging');

  // Exactly one full page: needs the extra probe to learn it is done, and must
  // terminate rather than loop on the empty response.
  const exact = fakeEndpoint(500);
  assert.strictEqual((await fetchAllPages(exact.fetchPage)).length, 500);
  assert.strictEqual(exact.calls.length, 2, 'full final page costs one probe');

  // Empty season must not hang.
  const empty = fakeEndpoint(0);
  assert.deepStrictEqual(await fetchAllPages(empty.fetchPage), []);

  // Custom page size is honoured.
  const custom = fakeEndpoint(25);
  assert.strictEqual((await fetchAllPages(custom.fetchPage, 10)).length, 25);
  assert.deepStrictEqual(custom.calls, [[0, 10], [10, 10], [20, 10]]);

  console.log('✓ paging self-check passed');
})();
