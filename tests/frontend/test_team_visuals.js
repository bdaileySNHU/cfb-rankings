// Self-check for team colour contrast and CFBD logo URLs.
//   node tests/frontend/test_team_visuals.js
//
// The thing being defended: team brand colours are frequently near-black, and
// painting them on the dark panel made 92 of 135 teams fall below the 3:1 WCAG
// non-text contrast minimum (UConn's #000e2f scored 1.03:1 — invisible).

const assert = require('assert');
const TV = require('../../frontend/js/team-visuals.js');
const meta = require('../../frontend/data/teams-meta.json');

const teams = Object.entries(meta).filter(([k]) => !k.startsWith('_'));

// ── Contrast maths ───────────────────────────────────────────────────────────

// Known WCAG values: black on white is the 21:1 maximum, identical colours 1:1.
assert.ok(Math.abs(TV.contrast('#000000', '#ffffff') - 21) < 0.01, 'black/white is 21:1');
assert.ok(Math.abs(TV.contrast('#121419', '#121419') - 1) < 0.01, 'identical colours are 1:1');

// ── Every real team clears the bar, on both themes ───────────────────────────

for (const [name, m] of teams) {
  if (!m.primary) continue;

  const onDark = TV.readable(m.primary, { light: false });
  assert.ok(
    TV.contrast(onDark, TV.DARK_SURFACE) >= TV.MIN_CONTRAST - 0.001,
    `${name}: ${m.primary} -> ${onDark} still fails on dark ` +
    `(${TV.contrast(onDark, TV.DARK_SURFACE).toFixed(2)}:1)`
  );

  const onLight = TV.readable(m.primary, { light: true });
  assert.ok(
    TV.contrast(onLight, TV.LIGHT_SURFACE) >= TV.MIN_CONTRAST - 0.001,
    `${name}: ${m.primary} -> ${onLight} still fails on light ` +
    `(${TV.contrast(onLight, TV.LIGHT_SURFACE).toFixed(2)}:1)`
  );
}

// Colours that already pass must be returned untouched — we are not
// repainting teams whose brand colour is fine.
const bright = '#ff6600';
assert.ok(TV.contrast(bright, TV.DARK_SURFACE) >= TV.MIN_CONTRAST, 'fixture should already pass');
assert.strictEqual(
  TV.readable(bright, { light: false }).toLowerCase(), bright,
  'a colour that already passes must be left alone'
);

// Hue is preserved, so a navy team still reads as navy rather than being
// swapped for some arbitrary accent.
const navy = TV.readable('#0c2340', { light: false }); // Notre Dame
const [r, g, b] = [1, 3, 5].map((i) => parseInt(navy.slice(i, i + 2), 16));
assert.ok(b > r && b > g, `navy should stay blue-dominant, got ${navy}`);

// Pure black has no hue to preserve; it must still become visible.
const black = TV.readable('#000000', { light: false });
assert.ok(
  TV.contrast(black, TV.DARK_SURFACE) >= TV.MIN_CONTRAST,
  `#000000 -> ${black} must clear the bar`
);

// Garbage in, garbage out — but no crash.
assert.strictEqual(TV.readable(null), null);
assert.strictEqual(TV.readable('not-a-colour'), 'not-a-colour');

// ── Logo URLs ────────────────────────────────────────────────────────────────

const nd = meta['Notre Dame'];
assert.strictEqual(
  TV.logoUrl(nd, 32, { light: false }),
  'https://cdn.collegefootballdata.com/logos-dark/32/87.png',
  'dark theme uses the logos-dark variant'
);
assert.strictEqual(
  TV.logoUrl(nd, 32, { light: true }),
  'https://cdn.collegefootballdata.com/logos/32/87.png',
  'light theme uses the standard variant'
);

// Requested sizes round UP to a size CFBD publishes, so a 24px cell fetches 32
// rather than the 500px original.
assert.ok(TV.logoUrl(nd, 24, { light: false }).includes('/32/'), '24 rounds up to 32');
assert.ok(TV.logoUrl(nd, 56, { light: false }).includes('/64/'), '56 rounds up to 64');
assert.ok(TV.logoUrl(nd, 9999, { light: false }).includes('/500/'), 'oversize clamps to 500');

// A team without an id yields nothing, so callers fall back to stripe/initials.
assert.strictEqual(TV.logoUrl({}, 32), null, 'no cfbd_id -> no url');
assert.strictEqual(TV.logoImg({}, 32, 'X'), '', 'no cfbd_id -> no markup');
assert.strictEqual(TV.logoImg(null, 32, 'X'), '', 'no meta -> no markup');

// The markup carries both variants so the theme toggle can repoint it.
const img = TV.logoImg(nd, 24, 'Notre Dame');
assert.ok(img.includes('data-logo-light='), 'markup carries the light variant');
assert.ok(img.includes('data-logo-dark='), 'markup carries the dark variant');
assert.ok(img.includes('loading="lazy"'), '130 logos per page must lazy-load');
assert.ok(img.includes('alt="Notre Dame"'), 'logo needs an accessible name');

// Alt text with a quote must not break out of the attribute.
assert.ok(
  !TV.logoImg(nd, 24, 'A" onerror="x').includes('onerror="x'),
  'alt text must be escaped'
);

// Every team in the meta file should have a logo id — that is the whole
// advantage over the ESPN id map this replaces.
const missing = teams.filter(([, m]) => m.cfbd_id == null).map(([n]) => n);
assert.strictEqual(missing.length, 0, `teams without a cfbd_id: ${missing.join(', ')}`);

// ── Split-bar colour separation ──────────────────────────────────────────────

// Same hue and similar lightness is the case that was slipping through: two
// reds side by side read as one bar.
assert.ok(TV.tooSimilar('#cc0000', '#b00000'), 'two similar reds are too similar');
// Different hue at similar lightness is fine — red vs blue is legible.
assert.ok(!TV.tooSimilar('#cc0000', '#0000cc'), 'red vs blue is distinguishable');
// Same hue at very different lightness is fine — dark red vs pink.
assert.ok(!TV.tooSimilar('#330000', '#ff9999'), 'dark vs light red is distinguishable');

// Every ordered pair of real teams must come out separable, and none may be
// left on the neutral if the team has a usable alternate colour.
let unresolved = [];
let viaNeutral = 0;
for (const [awayName, awayMeta] of teams) {
  for (const [homeName, homeMeta] of teams) {
    if (awayName === homeName) continue;
    for (const light of [false, true]) {
      const home = TV.readable(homeMeta.primary, { light });
      const away = TV.distinguish(awayMeta, homeMeta.primary, { light });
      if (TV.tooSimilar(away, home)) unresolved.push(`${awayName} vs ${homeName} (light=${light})`);
      // Whatever we pick must still be visible on the panel.
      const surface = light ? TV.LIGHT_SURFACE : TV.DARK_SURFACE;
      assert.ok(
        TV.contrast(away, surface) >= TV.MIN_CONTRAST - 0.001,
        `${awayName} vs ${homeName}: ${away} fails panel contrast`
      );
      if (away === '#b8bcc4' || away === '#4a4a4a') viaNeutral++;
    }
  }
}
assert.strictEqual(
  unresolved.length, 0,
  `pairs still indistinguishable: ${unresolved.slice(0, 5).join('; ')}`
);
assert.strictEqual(viaNeutral, 0, `${viaNeutral} pairs fell back to a neutral colour`);

// The screenshot cases specifically: a red away team against a red home team
// should end up on the away team's alternate, not grey.
const usc = meta['USC'];
const uscVsRed = TV.distinguish(usc, '#c8102e', { light: false }); // vs Houston red
assert.ok(
  !TV.tooSimilar(uscVsRed, TV.readable('#c8102e', { light: false })),
  `USC vs a red opponent still clashes: ${uscVsRed}`
);

const pairs = teams.length * (teams.length - 1) * 2;
console.log(
  `team visuals self-check passed (${teams.length} teams, both themes, ${pairs} bar pairings)`
);
