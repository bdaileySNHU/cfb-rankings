/**
 * EPIC-036: Share & Social Utilities
 *
 * - copyToClipboard(text)  — copies text, shows toast
 * - showToast(msg)         — temporary top-center notification
 * - shareMatchup(teamAId, teamBId) — copies matchup URL
 * - shareTeam(teamId)      — copies team page URL
 * - downloadTop25Card()    — Canvas top-25 image card → PNG download
 */

const SITE_URL = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? `${location.protocol}//${location.host}`
  : 'https://cfb.bdailey.com';

// ── Toast notification ────────────────────────────────────────────────────────
function showToast(msg, duration = 2200) {
  let toast = document.getElementById('share-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'share-toast';
    toast.className = 'share-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('share-toast-visible');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => toast.classList.remove('share-toast-visible'), duration);
}

// ── Copy to clipboard ─────────────────────────────────────────────────────────
async function copyToClipboard(text, toastMsg = 'Link copied!') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`✓ ${toastMsg}`);
  } catch {
    // Fallback for older browsers
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast(`✓ ${toastMsg}`);
  }
}

// ── Share helpers ─────────────────────────────────────────────────────────────
function shareMatchup(teamAId, teamBId) {
  copyToClipboard(`${SITE_URL}/matchup.html?teamA=${teamAId}&teamB=${teamBId}`, 'Matchup link copied!');
}

function shareTeam(teamId) {
  copyToClipboard(`${SITE_URL}/team.html?id=${teamId}`, 'Team link copied!');
}

function sharePrediction(homeId, awayId) {
  copyToClipboard(`${SITE_URL}/matchup.html?teamA=${homeId}&teamB=${awayId}`, 'Matchup link copied!');
}

// ── Canvas Top-25 Share Card ──────────────────────────────────────────────────
async function downloadTop25Card(rankings, season) {
  if (!rankings || !rankings.length) {
    showToast('No rankings data to share');
    return;
  }

  const W = 1200, H = 800;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  // ── Background ───────────────────────────────────────────────────────────
  ctx.fillStyle = '#0f1117';
  ctx.fillRect(0, 0, W, H);

  // Gold left accent bar
  ctx.fillStyle = '#d69e2e';
  ctx.fillRect(0, 0, 6, H);

  // Header band
  const headerH = 100;
  ctx.fillStyle = '#13161f';
  ctx.fillRect(6, 0, W - 6, headerH);

  // ── Header text ──────────────────────────────────────────────────────────
  // Football emoji via text (Canvas doesn't support emoji reliably — use unicode)
  ctx.fillStyle = '#d69e2e';
  ctx.font = 'bold 38px system-ui, -apple-system, sans-serif';
  ctx.fillText('Stat-urday', 40, 62);

  ctx.fillStyle = '#9aa0b8';
  ctx.font = '22px system-ui, -apple-system, sans-serif';
  ctx.fillText(`Top 25 · ${season || ''} Season`, 280, 62);

  // Site URL top-right
  ctx.fillStyle = '#d69e2e';
  ctx.font = '18px monospace';
  ctx.textAlign = 'right';
  ctx.fillText('cfb.bdailey.com', W - 30, 55);
  ctx.textAlign = 'left';

  // ── Rankings grid (two columns of ~12-13 rows) ────────────────────────────
  const top25 = rankings.slice(0, 25);
  const COL_W = (W - 60) / 2;
  const ROW_H = 26;
  const START_Y = headerH + 20;
  const PAD_X = 30;

  top25.forEach((team, i) => {
    const col = i < 13 ? 0 : 1;
    const row = i < 13 ? i : i - 13;
    const x = PAD_X + col * (COL_W + 20);
    const y = START_Y + row * ROW_H;

    // Alternating row background
    if (row % 2 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.025)';
      ctx.fillRect(x - 6, y - 18, COL_W + 6, ROW_H);
    }

    // Rank number
    ctx.fillStyle = '#d69e2e';
    ctx.font = 'bold 15px system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${i + 1}`, x + 24, y);
    ctx.textAlign = 'left';

    // Record
    const record = `${team.wins || 0}–${team.losses || 0}`;

    // Team name
    ctx.fillStyle = '#f0f2f8';
    ctx.font = '15px system-ui, sans-serif';
    ctx.fillText(team.team_name || team.name || '—', x + 30, y);

    // ELO
    ctx.fillStyle = '#9aa0b8';
    ctx.font = '13px system-ui, sans-serif';
    const elo = team.elo_rating ? Math.round(team.elo_rating) : '';
    ctx.textAlign = 'right';
    ctx.fillText(`${record}  ${elo}`, x + COL_W - 4, y);
    ctx.textAlign = 'left';
  });

  // ── Footer ────────────────────────────────────────────────────────────────
  const footerY = H - 30;
  ctx.fillStyle = '#1e2235';
  ctx.fillRect(0, footerY - 10, W, 40);

  ctx.fillStyle = '#5c6380';
  ctx.font = '14px system-ui, sans-serif';
  const dateStr = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  ctx.fillText(`Generated ${dateStr} · ELO-based rankings · cfb.bdailey.com`, 30, footerY + 10);

  // ── Download ──────────────────────────────────────────────────────────────
  const link = document.createElement('a');
  link.download = `staturday-top25-${season || 'rankings'}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();

  showToast('📥 Top 25 card downloaded!');
}
