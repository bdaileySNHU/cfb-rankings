/**
 * EPIC-034: Head-to-Head Matchup Page
 * Handles team search/select, fetches /api/matchup, and renders:
 *  - Win probability bar with home/neutral toggle
 *  - Side-by-side season stats grid
 *  - Overlaid dual-team ELO history SVG chart
 *  - All-time head-to-head game table
 */

const BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://cfb.bdailey.com';

// ── State ─────────────────────────────────────────────────────────────────────
let allTeams = [];
let selectedA = null;   // { id, name, conference }
let selectedB = null;
let matchupData = null;
let activeSite = 'neutral';  // 'neutral' | 'home-a' | 'home-b'

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadAllTeams();
  wireSearches();
  wireSiteToggle();
  document.getElementById('compare-btn').addEventListener('click', runComparison);

  // Pre-fill from URL params
  const params = new URLSearchParams(window.location.search);
  const idA = parseInt(params.get('teamA'));
  const idB = parseInt(params.get('teamB'));
  if (idA && idB) {
    const ta = allTeams.find(t => t.id === idA);
    const tb = allTeams.find(t => t.id === idB);
    if (ta) selectTeam('a', ta);
    if (tb) selectTeam('b', tb);
    if (ta && tb) runComparison();
  }
});

// ── Load all teams for autocomplete ──────────────────────────────────────────
async function loadAllTeams() {
  try {
    const resp = await fetch(`${BASE_URL}/api/teams?limit=500`);
    if (!resp.ok) throw new Error('Failed to load teams');
    allTeams = await resp.json();
    allTeams.sort((a, b) => a.name.localeCompare(b.name));
  } catch (e) {
    console.error('Error loading teams:', e);
  }
}

// ── Search / autocomplete ─────────────────────────────────────────────────────
function wireSearches() {
  ['a', 'b'].forEach(side => {
    const input = document.getElementById(`search-${side}`);
    const dropdown = document.getElementById(`dropdown-${side}`);

    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      if (q.length < 1) { dropdown.innerHTML = ''; dropdown.classList.remove('open'); return; }
      const matches = allTeams
        .filter(t => t.name.toLowerCase().includes(q))
        .slice(0, 8);
      renderDropdown(side, matches, dropdown);
    });

    input.addEventListener('focus', () => {
      if (input.value.trim()) input.dispatchEvent(new Event('input'));
    });

    document.addEventListener('click', e => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
      }
    });
  });
}

function renderDropdown(side, teams, container) {
  if (!teams.length) { container.innerHTML = '<div class="matchup-dd-empty">No teams found</div>'; container.classList.add('open'); return; }
  container.innerHTML = teams.map(t =>
    `<div class="matchup-dd-item" data-id="${t.id}">${t.name}<span class="matchup-dd-conf">${t.conference_name || t.conference || ''}</span></div>`
  ).join('');
  container.classList.add('open');
  container.querySelectorAll('.matchup-dd-item').forEach(el => {
    el.addEventListener('click', () => {
      const team = allTeams.find(t => t.id === parseInt(el.dataset.id));
      if (team) {
        selectTeam(side, team);
        container.classList.remove('open');
        document.getElementById(`search-${side}`).value = '';
      }
    });
  });
}

function selectTeam(side, team) {
  if (side === 'a') {
    selectedA = team;
    document.getElementById('name-a').textContent = team.name;
    renderAvatar('avatar-a', team);
  } else {
    selectedB = team;
    document.getElementById('name-b').textContent = team.name;
    renderAvatar('avatar-b', team);
  }
  updateCompareBtn();
  updateURL();
}

function updateCompareBtn() {
  document.getElementById('compare-btn').disabled = !(selectedA && selectedB);
}

function updateURL() {
  if (!selectedA || !selectedB) return;
  const url = new URL(window.location.href);
  url.searchParams.set('teamA', selectedA.id);
  url.searchParams.set('teamB', selectedB.id);
  window.history.replaceState({}, '', url.toString());
}

// ── Avatars ───────────────────────────────────────────────────────────────────
function renderAvatar(containerId, team) {
  const name = typeof team === 'string' ? team : team.name;
  const espnId = typeof team === 'object' ? team.espn_id : null;
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  if (espnId) {
    const img = document.createElement('img');
    img.src = `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png`;
    img.width = 56; img.height = 56;
    img.alt = name;
    img.style.borderRadius = '50%';
    img.onerror = () => { el.innerHTML = initialsAvatarSvg(name, 56); };
    el.appendChild(img);
  } else {
    el.innerHTML = initialsAvatarSvg(name, 56);
  }
}

function initialsAvatarSvg(name, size) {
  const initials = name.split(' ').filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const hue = [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) & 0xffff, 0) % 360;
  const fs = size > 40 ? 20 : 9;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="hsl(${hue},55%,38%)"/>
    <text x="${size/2}" y="${size/2}" text-anchor="middle" dominant-baseline="central"
      font-family="system-ui,sans-serif" font-size="${fs}" font-weight="700" fill="white">${initials}</text>
  </svg>`;
}

// ── Site toggle ───────────────────────────────────────────────────────────────
function wireSiteToggle() {
  document.querySelectorAll('.site-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.site-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeSite = btn.dataset.site;
      if (matchupData) updateProbBar(matchupData);
    });
  });
}

// ── Main comparison ───────────────────────────────────────────────────────────
async function runComparison() {
  if (!selectedA || !selectedB) return;
  showLoading(true);
  hideResults();
  clearError();

  try {
    const resp = await fetch(`${BASE_URL}/api/matchup?teamA=${selectedA.id}&teamB=${selectedB.id}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    matchupData = await resp.json();

    // Update home-button labels
    document.getElementById('home-a-btn').textContent = `${matchupData.team_a.name} at Home`;
    document.getElementById('home-b-btn').textContent = `${matchupData.team_b.name} at Home`;

    document.getElementById('season-display').textContent = `${matchupData.season} Season`;

    updateProbBar(matchupData);
    renderStatsGrid(matchupData);
    renderEloChart(matchupData);
    renderH2H(matchupData);
    updateOgForMatchup(matchupData);

    // EPIC-036: Show & wire copy-link button
    const shareBtn = document.getElementById('share-matchup-btn');
    if (shareBtn) {
      shareBtn.classList.remove('hidden');
      shareBtn.onclick = () => shareMatchup(selectedA.id, selectedB.id);
    }

    showResults();
  } catch (e) {
    showError(`Failed to load matchup data: ${e.message}`);
  } finally {
    showLoading(false);
  }
}

// ── Win probability bar ───────────────────────────────────────────────────────
function updateProbBar(data) {
  let pA, pB, subtext;

  if (activeSite === 'neutral') {
    pA = data.win_prob_neutral;
    pB = 1 - pA;
    subtext = 'Neutral site — no home field adjustment';
  } else if (activeSite === 'home-a') {
    pA = data.win_prob_a_home;
    pB = 1 - pA;
    subtext = `+65 ELO home field advantage for ${data.team_a.name}`;
  } else {
    pA = data.win_prob_b_home;
    pB = 1 - pA;
    subtext = `+65 ELO home field advantage for ${data.team_b.name}`;
  }

  const pctA = Math.round(pA * 100);
  const pctB = 100 - pctA;

  document.getElementById('prob-label-a').textContent = data.team_a.name;
  document.getElementById('prob-label-b').textContent = data.team_b.name;
  document.getElementById('pct-a').textContent = `${pctA}%`;
  document.getElementById('pct-b').textContent = `${pctB}%`;
  document.getElementById('prob-subtext').textContent = subtext;

  // Animate the bar
  requestAnimationFrame(() => {
    document.getElementById('prob-fill-a').style.width = `${pctA}%`;
    document.getElementById('prob-fill-b').style.width = `${pctB}%`;
  });
}

// ── Stats grid ────────────────────────────────────────────────────────────────
function renderStatsGrid(data) {
  const a = data.team_a;
  const b = data.team_b;

  document.getElementById('stats-head-a').textContent = a.name;
  document.getElementById('stats-head-b').textContent = b.name;

  function statVal(v, fallback = '—') {
    return (v !== null && v !== undefined) ? v : fallback;
  }

  document.getElementById('stat-rank-a').textContent = a.rank ? `#${a.rank}` : 'NR';
  document.getElementById('stat-rank-b').textContent = b.rank ? `#${b.rank}` : 'NR';

  document.getElementById('stat-elo-a').textContent = statVal(a.elo_rating);
  document.getElementById('stat-elo-b').textContent = statVal(b.elo_rating);

  document.getElementById('stat-rec-a').textContent = `${a.wins}–${a.losses}`;
  document.getElementById('stat-rec-b').textContent = `${b.wins}–${b.losses}`;

  document.getElementById('stat-sos-a').textContent = statVal(a.sos);
  document.getElementById('stat-sos-b').textContent = statVal(b.sos);

  document.getElementById('stat-sos-rank-a').textContent = a.sos_rank ? `#${a.sos_rank}` : '—';
  document.getElementById('stat-sos-rank-b').textContent = b.sos_rank ? `#${b.sos_rank}` : '—';

  document.getElementById('stat-pre-a').textContent = statVal(a.preseason_elo);
  document.getElementById('stat-pre-b').textContent = statVal(b.preseason_elo);

  document.getElementById('stat-conf-a').textContent = statVal(a.conference_name || a.conference);
  document.getElementById('stat-conf-b').textContent = statVal(b.conference_name || b.conference);

  // Highlight better value
  highlightBetter('stat-rank-a', 'stat-rank-b', a.rank, b.rank, true);  // lower is better
  highlightBetter('stat-elo-a', 'stat-elo-b', a.elo_rating, b.elo_rating, false);
  highlightBetter('stat-sos-rank-a', 'stat-sos-rank-b', a.sos_rank, b.sos_rank, true);
}

function highlightBetter(idA, idB, valA, valB, lowerIsBetter) {
  const elA = document.getElementById(idA);
  const elB = document.getElementById(idB);
  elA.classList.remove('stat-better');
  elB.classList.remove('stat-better');
  if (valA === null || valB === null || valA === undefined || valB === undefined) return;
  const aBetter = lowerIsBetter ? valA < valB : valA > valB;
  if (aBetter) elA.classList.add('stat-better');
  else if (valB !== valA) elB.classList.add('stat-better');
}

// ── ELO history SVG chart ─────────────────────────────────────────────────────
function renderEloChart(data) {
  const container = document.getElementById('elo-chart-container');
  const emptyMsg = document.getElementById('elo-chart-empty');
  const histA = data.elo_history_a || [];
  const histB = data.elo_history_b || [];

  if (!histA.length && !histB.length) {
    emptyMsg.style.display = '';
    return;
  }
  emptyMsg.style.display = 'none';

  // Update legend names
  document.getElementById('legend-name-a').textContent = data.team_a.name;
  document.getElementById('legend-name-b').textContent = data.team_b.name;

  // Combine week sets
  const allWeeks = [...new Set([...histA.map(p => p.week), ...histB.map(p => p.week)])].sort((a,b) => a-b);
  if (!allWeeks.length) return;

  const allElos = [...histA.map(p => p.elo_rating), ...histB.map(p => p.elo_rating)].filter(Boolean);
  const minElo = Math.min(...allElos) - 30;
  const maxElo = Math.max(...allElos) + 30;

  const W = Math.max(container.clientWidth || 700, 400);
  const H = 260;
  const PAD = { top: 20, right: 24, bottom: 40, left: 60 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const xScale = i => PAD.left + (i / Math.max(allWeeks.length - 1, 1)) * chartW;
  const yScale = v => PAD.top + chartH - ((v - minElo) / (maxElo - minElo)) * chartH;

  function buildPoints(hist) {
    return allWeeks
      .map((w, i) => {
        const pt = hist.find(p => p.week === w);
        if (!pt) return null;
        return `${xScale(i).toFixed(1)},${yScale(pt.elo_rating).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(' ');
  }

  const pointsA = buildPoints(histA);
  const pointsB = buildPoints(histB);

  // Y gridlines
  const yTicks = 5;
  let gridLines = '';
  for (let i = 0; i <= yTicks; i++) {
    const v = minElo + (i / yTicks) * (maxElo - minElo);
    const y = yScale(v).toFixed(1);
    gridLines += `<line x1="${PAD.left}" y1="${y}" x2="${W - PAD.right}" y2="${y}" stroke="var(--border-subtle)" stroke-dasharray="4,4"/>`;
    gridLines += `<text x="${PAD.left - 8}" y="${y}" text-anchor="end" dominant-baseline="middle" fill="var(--text-secondary)" font-size="11">${Math.round(v)}</text>`;
  }

  // X axis week labels (every other week)
  let xLabels = '';
  allWeeks.forEach((w, i) => {
    if (i % 2 !== 0 && i !== allWeeks.length - 1) return;
    const x = xScale(i).toFixed(1);
    xLabels += `<text x="${x}" y="${H - PAD.bottom + 16}" text-anchor="middle" fill="var(--text-secondary)" font-size="11">${w === 0 ? 'Pre' : `W${w}`}</text>`;
  });

  // Dots for each data point
  function buildDots(hist, color) {
    return allWeeks.map((w, i) => {
      const pt = hist.find(p => p.week === w);
      if (!pt) return '';
      const x = xScale(i).toFixed(1);
      const y = yScale(pt.elo_rating).toFixed(1);
      return `<circle cx="${x}" cy="${y}" r="3.5" fill="${color}" stroke="var(--bg-card)" stroke-width="1.5">
        <title>Wk ${w === 0 ? 'Pre' : w}: ${pt.elo_rating}</title>
      </circle>`;
    }).join('');
  }

  const svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:100%;">
    <!-- Grid -->
    ${gridLines}
    <!-- X axis -->
    <line x1="${PAD.left}" y1="${H - PAD.bottom}" x2="${W - PAD.right}" y2="${H - PAD.bottom}" stroke="var(--border-color)" stroke-width="1"/>
    <!-- Y axis -->
    <line x1="${PAD.left}" y1="${PAD.top}" x2="${PAD.left}" y2="${H - PAD.bottom}" stroke="var(--border-color)" stroke-width="1"/>
    <!-- Week labels -->
    ${xLabels}
    <!-- Team A line -->
    ${pointsA ? `<polyline points="${pointsA}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>` : ''}
    <!-- Team B line -->
    ${pointsB ? `<polyline points="${pointsB}" fill="none" stroke="var(--accent-secondary, #4a9eff)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>` : ''}
    <!-- Dots A -->
    ${buildDots(histA, 'var(--accent)')}
    <!-- Dots B -->
    ${buildDots(histB, 'var(--accent-secondary, #4a9eff)')}
  </svg>`;

  container.innerHTML = svg;
}

// ── Head-to-head table ────────────────────────────────────────────────────────
function renderH2H(data) {
  const games = data.head_to_head || [];
  const tableWrap = document.getElementById('h2h-table-wrap');
  const emptyEl = document.getElementById('h2h-empty');
  const badge = document.getElementById('h2h-series-badge');
  const tbody = document.getElementById('h2h-tbody');

  // Update table header names
  document.getElementById('h2h-th-a').textContent = data.team_a.name;
  document.getElementById('h2h-th-b').textContent = data.team_b.name;

  // Series badge
  const wA = data.series_wins_a;
  const wB = data.series_wins_b;
  if (wA + wB > 0) {
    let leader, badgeClass;
    if (wA > wB) { leader = `${data.team_a.name} leads`; badgeClass = 'badge-a'; }
    else if (wB > wA) { leader = `${data.team_b.name} leads`; badgeClass = 'badge-b'; }
    else { leader = 'Series tied'; badgeClass = 'badge-neutral'; }
    badge.innerHTML = `<span class="h2h-badge ${badgeClass}">${leader} ${wA}–${wB}</span>`;
  } else {
    badge.innerHTML = '';
  }

  if (!games.length) {
    emptyEl.classList.remove('hidden');
    tableWrap.classList.add('hidden');
    return;
  }

  emptyEl.classList.add('hidden');
  tableWrap.classList.remove('hidden');

  tbody.innerHTML = games.map(g => {
    const winnerName = g.winner_id === data.team_a.id
      ? data.team_a.name
      : g.winner_id === data.team_b.id
        ? data.team_b.name
        : '—';
    const winnerClass = g.winner_id === data.team_a.id ? 'winner-a' : 'winner-b';
    const site = g.neutral_site ? '⚪ Neutral' : '🏠 Home';
    return `<tr>
      <td>${g.season}</td>
      <td>${g.week}</td>
      <td class="${g.winner_id === data.team_a.id ? 'h2h-winner' : ''}">${g.score_a ?? '—'}</td>
      <td class="${g.winner_id === data.team_b.id ? 'h2h-winner' : ''}">${g.score_b ?? '—'}</td>
      <td><span class="result-badge ${g.winner_id === data.team_a.id ? 'result-win' : 'result-loss'} ${winnerClass}">${winnerName}</span></td>
      <td style="color:var(--text-secondary); font-size:0.85rem;">${site}</td>
    </tr>`;
  }).join('');
}

// ── OG meta helpers ───────────────────────────────────────────────────────────
function _setOgMeta(prop, content) {
  let el = document.querySelector(`meta[property="${prop}"]`) ||
           document.querySelector(`meta[name="${prop}"]`);
  if (el) el.setAttribute('content', content);
}

function updateOgForMatchup(data) {
  const a = data.team_a.name;
  const b = data.team_b.name;
  const pct = Math.round(data.win_prob_neutral * 100);
  const title = `${a} vs ${b} — Stat-urday`;
  const desc = `${a} has a ${pct}% win probability vs ${b} · ELO-based CFB matchup analysis`;
  const url = `https://cfb.bdailey.com/matchup.html?teamA=${data.team_a.id}&teamB=${data.team_b.id}`;
  document.title = title;
  _setOgMeta('og:title', title);
  _setOgMeta('og:description', desc);
  _setOgMeta('og:url', url);
  _setOgMeta('twitter:title', title);
  _setOgMeta('twitter:description', desc);
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function showLoading(show) {
  document.getElementById('matchup-loading').classList.toggle('hidden', !show);
}
function showResults() {
  document.getElementById('matchup-results').classList.remove('hidden');
}
function hideResults() {
  document.getElementById('matchup-results').classList.add('hidden');
}
function showError(msg) {
  const el = document.getElementById('matchup-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}
function clearError() {
  document.getElementById('matchup-error').classList.add('hidden');
}
