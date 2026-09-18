// Self-check for the responsive CSS-grid tables.
//   node tests/frontend/test_board_columns.js
//
// Each of these tables commits most of its width to fixed tracks and leaves one
// or two `fr` columns to absorb the remainder. Below the fixed total, the `fr`
// columns are the only ones that can give — so the *most* important column
// (matchup, opponent) is the first to vanish while fixed decoration survives.
// The fix is to drop columns as the viewport narrows.
//
// The invariant checked here: at every breakpoint the number of visible columns
// must equal the number of tracks in grid-template-columns. Too many tracks
// leaves phantom empty columns; too few makes cells wrap onto a second row.
// Media queries are cumulative, so each narrower breakpoint inherits everything
// hidden above it.
//
// .tkr-grid (the ratings board) is NOT checked here any more. Its columns moved
// into the COLUMNS array in board.js, which renders only the visible ones and
// sets --tkr-cols to match, so there are no nth-child rules left to verify.
// test_board_column_model.js checks the same invariant against that array.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const css = fs.readFileSync(
  path.join(__dirname, '../../frontend/css/components/board.css'), 'utf8'
);

/** Grids to verify: selector, total column count, and the 1-based columns that
 *  must never be hidden at any width. */
const GRIDS = [
  {
    selector: '.tkr-pgrid',
    total: 5, // MATCHUP PROJ WIN-PROB SPREAD CONF
    mustKeep: { 1: 'MATCHUP', 3: 'WIN PROB' },
    narrowestVisible: 2,
  },
  {
    selector: '.tkr-sched-grid',
    total: 6, // WK LOC OPPONENT PROJ WIN-BAR ODDS
    mustKeep: { 1: 'WK', 3: 'OPPONENT', 6: 'ODDS' },
    narrowestVisible: 4,
  },
];

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Extract `@media (max-width: N px) { ... }` blocks, brace-matched. */
function mediaBlocks(source) {
  const blocks = [];
  const re = /@media \(max-width:\s*(\d+)px\)\s*\{/g;
  let m;
  while ((m = re.exec(source)) !== null) {
    let depth = 1;
    let i = re.lastIndex;
    while (i < source.length && depth > 0) {
      if (source[i] === '{') depth++;
      else if (source[i] === '}') depth--;
      i++;
    }
    blocks.push({ width: Number(m[1]), body: source.slice(re.lastIndex, i - 1) });
  }
  return blocks;
}

/** The stylesheet with every @media block removed, i.e. the base rules. */
function withoutMediaBlocks(source) {
  let out = '';
  let i = 0;
  while (i < source.length) {
    const start = source.indexOf('@media', i);
    if (start === -1) { out += source.slice(i); break; }
    out += source.slice(i, start);
    let j = source.indexOf('{', start) + 1;
    let depth = 1;
    while (j < source.length && depth > 0) {
      if (source[j] === '{') depth++;
      else if (source[j] === '}') depth--;
      j++;
    }
    i = j;
  }
  return out;
}

/** Columns hidden by `<sel> > div:nth-child(N)` rules, including grouped
 *  selectors sharing a single display:none. */
function hiddenIn(body, selector) {
  const hidden = new Set();
  const sel = esc(selector);
  const rule = new RegExp(
    `((?:${sel}\\s*>\\s*div:nth-child\\(\\d+\\)\\s*,\\s*)*${sel}\\s*>\\s*div:nth-child\\(\\d+\\))\\s*\\{[^}]*display:\\s*none`,
    'g'
  );
  let m;
  while ((m = rule.exec(body)) !== null) {
    (m[1].match(/nth-child\((\d+)\)/g) || [])
      .forEach((n) => hidden.add(Number(n.match(/\d+/)[0])));
  }
  return hidden;
}

/** Track count of the last grid-template-columns declared for the selector. */
function trackCount(body, selector) {
  const re = new RegExp(`${esc(selector)}\\s*\\{[^}]*grid-template-columns:\\s*([^;]+);`, 'g');
  let m, last = null;
  while ((m = re.exec(body)) !== null) last = m[1];
  return last === null ? null : last.trim().split(/\s+/).length;
}

const base = withoutMediaBlocks(css);
let totalChecked = 0;

for (const grid of GRIDS) {
  const baseTracks = trackCount(base, grid.selector);
  assert.strictEqual(
    baseTracks, grid.total,
    `${grid.selector}: base should declare ${grid.total} tracks, found ${baseTracks}`
  );

  const blocks = mediaBlocks(css)
    .filter((b) => hiddenIn(b.body, grid.selector).size > 0 || trackCount(b.body, grid.selector) !== null)
    .sort((a, b) => b.width - a.width);

  assert.ok(blocks.length >= 2, `${grid.selector}: expected responsive breakpoints`);

  const cumulativeHidden = new Set();
  let checked = 0;

  for (const block of blocks) {
    hiddenIn(block.body, grid.selector).forEach((n) => cumulativeHidden.add(n));
    const tracks = trackCount(block.body, grid.selector);
    if (tracks === null) continue;

    const visible = grid.total - cumulativeHidden.size;
    assert.strictEqual(
      tracks, visible,
      `${grid.selector} at max-width ${block.width}px: ${visible} columns visible but ` +
      `${tracks} grid tracks declared (hidden: ${[...cumulativeHidden].sort((a, b) => a - b).join(',')})`
    );

    for (const [col, name] of Object.entries(grid.mustKeep)) {
      assert.ok(
        !cumulativeHidden.has(Number(col)),
        `${grid.selector}: ${name} (column ${col}) hidden at ${block.width}px`
      );
    }
    checked++;
  }

  assert.ok(checked >= 2, `${grid.selector}: verified only ${checked} breakpoints`);
  assert.strictEqual(
    grid.total - cumulativeHidden.size, grid.narrowestVisible,
    `${grid.selector}: narrowest breakpoint should leave ${grid.narrowestVisible} columns`
  );
  totalChecked += checked;
}

console.log(`grid column self-check passed (${GRIDS.length} grids, ${totalChecked} breakpoints)`);

// ── Sticky ratings-board heading ─────────────────────────────────────────────
// position:sticky resolves against the nearest scrollport, not the viewport. The
// two rules that give .tkr-table `overflow-x: auto` (narrow screens, and any
// explicit column preset) therefore turn the sticky heading into a block parked
// on top of the first row. The sticky rule must stay scoped out of both, and its
// offset must clear the sticky chrome above it: the 60px header and its border,
// then the 40px ticker tape and its own.
{
  const stickyRule = /@media \(min-width:\s*769px\)\s*\{\s*#tkr-board\[data-view="all"\]\s+\.tkr-head\s*\{([^}]*)\}/
    .exec(css);
  assert.ok(stickyRule,
    '.tkr-head sticky rule must be scoped to min-width:769px and the "all" column view');
  assert.ok(/position:\s*sticky/.test(stickyRule[1]), 'the scoped rule should be the sticky one');

  const top = /top:\s*(\d+)px/.exec(stickyRule[1]);
  assert.ok(top, 'the sticky heading needs an explicit top offset');

  const heightOf = (selector) => {
    const rule = new RegExp(`${esc(selector)}\\s*\\{[^}]*?height:\\s*(\\d+)px`, 's').exec(css);
    assert.ok(rule, `could not read the height of ${selector}`);
    return Number(rule[1]);
  };
  // Each contributes its height plus a 1px bottom border.
  const expected = heightOf('.tkr-header-inner') + 1 + heightOf('.tkr-tape') + 1;
  assert.strictEqual(
    Number(top[1]), expected,
    `sticky heading offset should be ${expected}px (header + tape + their borders), ` +
    `found ${top[1]}px — it would sit behind the ticker tape`
  );

  // The base rule must not re-introduce stickiness outside that media query.
  const baseHead = /\.tkr-head\s*\{([^}]*)\}/.exec(withoutMediaBlocks(css));
  assert.ok(baseHead, 'no base .tkr-head rule found');
  assert.ok(!/position:\s*sticky/.test(baseHead[1]),
    '.tkr-head must not be sticky unconditionally — it breaks inside a scrolling table');
}

console.log('sticky heading self-check passed');
