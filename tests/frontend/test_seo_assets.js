// Self-check for the crawlability assets.
//   node tests/frontend/test_seo_assets.js
//
// Before these files existed, nginx's SPA-style `try_files $uri $uri/
// /index.html` answered /robots.txt and /sitemap.xml with HTTP 200 and the
// homepage HTML - worse than a 404, because a crawler cannot tell it is wrong.
// The files are static and easy to let rot, so this pins the parts that break
// silently: a sitemap listing a page that no longer exists, a page losing its
// description, an og:image pointing back at the SVG that social platforms will
// not render.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, '../../frontend');
const read = (p) => fs.readFileSync(path.join(dir, p), 'utf8');
const exists = (p) => fs.existsSync(path.join(dir, p));

const SITE = 'https://cfb.bdailey.com';

// Pages that should be indexed. team.html and admin.html are excluded on
// purpose: the first only redirects to index.html, the second is the dashboard.
const PUBLIC_PAGES = [
  'index.html', 'games.html', 'comparison.html',
  'elo-formula.html', 'simulator.html', 'matchup.html',
];

// ── robots.txt ───────────────────────────────────────────────────────────────
assert.ok(exists('robots.txt'), 'frontend/robots.txt is missing');
const robots = read('robots.txt');
assert.ok(/^User-agent:\s*\*/m.test(robots), 'robots.txt needs a wildcard User-agent group');
assert.ok(new RegExp(`^Sitemap:\\s*${SITE}/sitemap\\.xml$`, 'm').test(robots),
  'robots.txt must point at the sitemap, absolute-URL as the spec requires');
for (const blocked of ['/admin.html', '/api/', '/docs', '/redoc', '/openapi.json']) {
  assert.ok(robots.includes('Disallow: ' + blocked),
    `robots.txt should disallow ${blocked}`);
}

// ── sitemap.xml ──────────────────────────────────────────────────────────────
assert.ok(exists('sitemap.xml'), 'frontend/sitemap.xml is missing');
const sitemap = read('sitemap.xml');
assert.ok(sitemap.includes('http://www.sitemaps.org/schemas/sitemap/0.9'),
  'sitemap.xml needs the sitemaps.org namespace');

const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
assert.ok(locs.length > 0, 'sitemap.xml lists no URLs');

for (const loc of locs) {
  assert.ok(loc.startsWith(SITE + '/'), `sitemap URL is not absolute or off-site: ${loc}`);
  // Every listed URL must resolve to a file that is actually deployed.
  const rel = loc.slice(SITE.length + 1) || 'index.html';
  assert.ok(exists(rel), `sitemap lists ${loc} but frontend/${rel} does not exist`);
}
for (const bad of ['admin.html', 'team.html']) {
  assert.ok(!locs.some((l) => l.endsWith('/' + bad)),
    `${bad} must not be in the sitemap`);
}
// Every public page should be findable.
for (const page of PUBLIC_PAGES) {
  const want = page === 'index.html' ? SITE + '/' : `${SITE}/${page}`;
  assert.ok(locs.includes(want), `sitemap is missing ${want}`);
}

// ── Per-page head tags ───────────────────────────────────────────────────────
for (const page of PUBLIC_PAGES) {
  const html = read(page);

  const desc = /<meta name="description" content="([^"]+)">/.exec(html);
  assert.ok(desc, `${page} has no <meta name="description"> - Google does not use og:description`);
  assert.ok(desc[1].length >= 50 && desc[1].length <= 160,
    `${page}: description is ${desc[1].length} chars, want 50-160`);

  assert.ok(/<link rel="canonical" href="https:\/\/cfb\.bdailey\.com/.test(html),
    `${page} is missing its canonical link`);

  // Facebook, X and LinkedIn do not render SVG cards.
  const og = /<meta property="og:image" content="([^"]+)">/.exec(html);
  assert.ok(og, `${page} has no og:image`);
  assert.ok(og[1].endsWith('.png'), `${page}: og:image must be a raster image, got ${og[1]}`);
  assert.ok(exists(og[1].slice(SITE.length + 1)), `${page}: og:image file is not deployed`);
  assert.ok(/<meta property="og:image:alt"/.test(html), `${page} is missing og:image:alt`);
  assert.ok(!/og-default\.svg/.test(html), `${page} still references the SVG card`);
}

// team.html redirects; it must say so rather than compete with the homepage.
const team = read('team.html');
assert.ok(/<meta name="robots" content="noindex,follow">/.test(team),
  'team.html only redirects, so it must be noindex');
assert.ok(/<link rel="canonical" href="https:\/\/cfb\.bdailey\.com\/">/.test(team),
  'team.html should point its canonical at its redirect destination');

// ── Icons browsers fetch by convention ───────────────────────────────────────
for (const icon of ['favicon.ico', 'apple-touch-icon.png']) {
  assert.ok(exists(icon),
    `frontend/${icon} must sit at the site root, where browsers look for it unprompted`);
}

console.log(`SEO asset self-check passed (${locs.length} sitemap URLs, ${PUBLIC_PAGES.length} pages)`);
