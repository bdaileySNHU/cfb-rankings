// Self-check for the responsive ratings table.
//   node tests/frontend/test_board_columns.js
//
// The table is a CSS grid whose columns are dropped as the viewport narrows.
// The invariant: at every breakpoint the number of *visible* columns must equal
// the number of tracks in grid-template-columns. Too many tracks leaves phantom
// empty columns; too few makes cells wrap onto a second line. Media queries are
// cumulative, so each narrower breakpoint inherits everything hidden above it.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const css = fs.readFileSync(
  path.join(__dirname, '../../frontend/css/components/board.css'), 'utf8'
);

const TOTAL_COLUMNS = 10; // RK TEAM CONF W-L ELO Δ1W OFF DEF SOS 10WK

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

/** Columns hidden by `.tkr-grid > div:nth-child(N)` rules inside a block. */
function hiddenIn(body) {
  const hidden = new Set();
  const re = /\.tkr-grid\s*>\s*div:nth-child\((\d+)\)[^{]*\{[^}]*display:\s*none/g;
  let m;
  while ((m = re.exec(body)) !== null) hidden.add(Number(m[1]));

  // Also handle the grouped form: several selectors sharing one display:none.
  const grouped = /((?:\.tkr-grid\s*>\s*div:nth-child\(\d+\)\s*,\s*)+\.tkr-grid\s*>\s*div:nth-child\(\d+\))\s*\{[^}]*display:\s*none/g;
  while ((m = grouped.exec(body)) !== null) {
    const nums = m[1].match(/nth-child\((\d+)\)/g) || [];
    nums.forEach((n) => hidden.add(Number(n.match(/\d+/)[0])));
  }
  return hidden;
}

/** Track count of the last grid-template-columns declared for .tkr-grid. */
function trackCount(body) {
  const re = /\.tkr-grid\s*\{[^}]*grid-template-columns:\s*([^;]+);/g;
  let m, last = null;
  while ((m = re.exec(body)) !== null) last = m[1];
  if (last === null) return null;
  return last.trim().split(/\s+/).length;
}

/** The stylesheet with every @media block removed, i.e. the base rules. */
function withoutMediaBlocks(source) {
  let out = '';
  let i = 0;
  while (i < source.length) {
    const start = source.indexOf('@media', i);
    if (start === -1) { out += source.slice(i); break; }
    out += source.slice(i, start);
    let j = source.indexOf('{', start);
    let depth = 1;
    j++;
    while (j < source.length && depth > 0) {
      if (source[j] === '{') depth++;
      else if (source[j] === '}') depth--;
      j++;
    }
    i = j;
  }
  return out;
}

// Base (no media query): full 10 columns.
const baseTracks = trackCount(withoutMediaBlocks(css));
assert.strictEqual(
  baseTracks, TOTAL_COLUMNS,
  `base grid should declare ${TOTAL_COLUMNS} tracks, found ${baseTracks}`
);

// Walk breakpoints widest to narrowest, accumulating hidden columns.
const blocks = mediaBlocks(css)
  .filter((b) => hiddenIn(b.body).size > 0 || trackCount(b.body) !== null)
  .sort((a, b) => b.width - a.width);

assert.ok(blocks.length >= 3, 'expected several responsive breakpoints');

const cumulativeHidden = new Set();
let checked = 0;

for (const block of blocks) {
  hiddenIn(block.body).forEach((n) => cumulativeHidden.add(n));
  const tracks = trackCount(block.body);
  if (tracks === null) continue; // block hides nothing / redefines nothing

  const visible = TOTAL_COLUMNS - cumulativeHidden.size;
  assert.strictEqual(
    tracks, visible,
    `at max-width ${block.width}px: ${visible} columns visible but ${tracks} grid tracks declared ` +
    `(hidden: ${[...cumulativeHidden].sort((a, b) => a - b).join(',')})`
  );
  checked++;

  // RK (1), TEAM (2) and ELO (5) must survive every breakpoint — without them
  // the table stops identifying which team a rating belongs to.
  assert.ok(!cumulativeHidden.has(1), `RK hidden at ${block.width}px`);
  assert.ok(!cumulativeHidden.has(2), `TEAM hidden at ${block.width}px`);
  assert.ok(!cumulativeHidden.has(5), `ELO hidden at ${block.width}px`);
}

assert.ok(checked >= 3, `expected to verify at least 3 breakpoints, verified ${checked}`);

// At the narrowest breakpoint we should be down to the essential three.
const narrowest = blocks[blocks.length - 1];
assert.strictEqual(
  TOTAL_COLUMNS - cumulativeHidden.size, 3,
  `narrowest breakpoint (${narrowest.width}px) should leave exactly RK/TEAM/ELO`
);

console.log(`board column self-check passed (${checked} breakpoints verified)`);
