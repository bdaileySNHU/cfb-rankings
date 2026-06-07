// Team Details Page Logic

// Helper: update a single OG/Twitter meta tag by property or name
function _setOgMeta(prop, content) {
  let el = document.querySelector(`meta[property="${prop}"]`) ||
           document.querySelector(`meta[name="${prop}"]`);
  if (el) el.setAttribute('content', content);
}

let teamId = null;
let teamData = null;
let season = null; // Season from URL parameter
let predictionData = {}; // EPIC-009: Store predictions by game_id
let allGames = []; // EPIC-023: Store all games for filtering

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  // Get team ID and season from URL
  const params = new URLSearchParams(window.location.search);
  teamId = params.get('id');
  const urlSeason = params.get('season');

  // Get season from URL or use active season as default
  season = urlSeason ? parseInt(urlSeason) : await api.getActiveSeason();

  if (!teamId) {
    showError('No team ID provided');
    return;
  }

  loadTeamDetails();

  // EPIC-023: Add event listener for game type filter
  const filterDropdown = document.getElementById('game-type-filter');
  if (filterDropdown) {
    filterDropdown.addEventListener('change', () => {
      filterAndDisplayGames(filterDropdown.value);
    });
  }
});

// Load Team Details
async function loadTeamDetails() {
  const loading = document.getElementById('loading');
  const error = document.getElementById('error');
  const content = document.getElementById('team-content');

  loading.classList.remove('hidden');
  error.classList.add('hidden');
  content.classList.add('hidden');

  try {
    // Load current team data (for name, conference, etc.)
    teamData = await api.getTeam(teamId);

    // Get active season to check if viewing historical data
    const activeSeason = await api.getActiveSeason();

    // If viewing a historical season, fetch ranking history for accurate record
    if (season !== activeSeason) {
      try {
        const history = await api.getRankingHistory(teamId, season);
        if (history && history.length > 0) {
          // Get the last week of the season (most recent record)
          const lastWeek = history[history.length - 1];
          // Override current season stats with historical data
          teamData.wins = lastWeek.wins;
          teamData.losses = lastWeek.losses;
          teamData.elo_rating = lastWeek.elo_rating;
        }
      } catch (err) {
        console.warn('Could not load historical data for season', season, err);
      }
    }

    // Populate team info (will use historical data if available)
    populateTeamInfo(teamData);

    // Render team logo
    renderTeamLogo(teamData);

    // EPIC-009: Load prediction accuracy
    loadPredictionAccuracy();

    // EPIC-031 Story 31.4: Load ELO history chart, game log, and preseason breakdown in parallel
    const [history, games] = await Promise.all([
      loadEloHistory(teamId, season),
      loadGameLog(teamId, season),
    ]);
    renderEloChart(history, games);
    loadPreseasonBreakdown(teamId, season);

    // EPIC-038: Position group strength radar
    loadPositionRadar(teamId);

    // Load schedule
    loadSchedule();

    // Show content
    loading.classList.add('hidden');
    content.classList.remove('hidden');
  } catch (err) {
    console.error('Error loading team:', err);
    loading.classList.add('hidden');
    error.classList.remove('hidden');
    document.getElementById('error-message').textContent = ` ${err.message}`;
  }
}

// EPIC-009: Load Prediction Accuracy
async function loadPredictionAccuracy() {
  try {
    const accuracy = await api.getTeamPredictionAccuracy(teamId, season);

    if (accuracy.evaluated_predictions > 0) {
      const card = document.getElementById('prediction-accuracy-card');
      const accuracyEl = document.getElementById('prediction-accuracy');
      const countEl = document.getElementById('prediction-count');

      accuracyEl.textContent = `${accuracy.accuracy_percentage.toFixed(1)}%`;
      countEl.textContent = `${accuracy.correct_predictions}/${accuracy.evaluated_predictions} correct`;

      // Color code based on accuracy
      if (accuracy.accuracy_percentage >= 70) {
        accuracyEl.style.color = 'var(--success-color)';
      } else if (accuracy.accuracy_percentage >= 50) {
        accuracyEl.style.color = 'var(--primary-color)';
      } else {
        accuracyEl.style.color = 'var(--danger-color)';
      }

      card.style.display = 'block';
    }
  } catch (err) {
    console.error('Error loading prediction accuracy:', err);
    // Don't show error - just hide the card
  }
}

// EPIC-031 Story 31.4: Preseason rating breakdown card
async function loadPreseasonBreakdown(teamId, season) {
  const body = document.getElementById('preseason-breakdown-body');
  const totalEl = document.getElementById('preseason-total');
  if (!body) return;

  try {
    const components = await api.getPreseasonComponents(season);
    const entry = components.find(c => c.team_id === teamId);

    if (!entry) {
      body.innerHTML = '<p style="color:var(--text-muted);padding:0.5rem 0;">No preseason data available.</p>';
      return;
    }

    const { base, recruiting_bonus, transfer_bonus, returning_bonus,
            position_strength_bonus, prev_season_elo, current_rating,
            recruiting_rank, transfer_portal_rank, returning_production } = entry;

    const baseFormula = base + recruiting_bonus + transfer_bonus + returning_bonus + position_strength_bonus;
    const regressionDelta = Math.round(current_rating - baseFormula);
    const hasRegression = prev_season_elo !== null && regressionDelta !== 0;

    if (totalEl) totalEl.textContent = Math.round(current_rating).toLocaleString();

    const fmt = (v) => (v >= 0 ? `+${Math.round(v)}` : `${Math.round(v)}`);
    const recruitLabel = recruiting_rank < 999 ? `Recruiting (#${recruiting_rank})` : 'Recruiting';
    const portalLabel = transfer_portal_rank < 999 ? `Transfer Portal (#${transfer_portal_rank})` : 'Transfer Portal';
    const retPct = `${Math.round((returning_production || 0) * 100)}%`;

    const rows = [
      { label: 'Base Rating', detail: '', value: Math.round(base), isBase: true },
      { label: recruitLabel, detail: '247Sports composite', value: recruiting_bonus },
      { label: portalLabel, detail: 'volume-weighted', value: transfer_bonus },
      { label: `Returning Production (${retPct})`, detail: 'returning starters', value: returning_bonus },
      { label: 'Position Strength', detail: 'roster quality bonus', value: position_strength_bonus },
    ];

    if (hasRegression) {
      const prevLabel = prev_season_elo ? ` (from ${Math.round(prev_season_elo).toLocaleString()})` : '';
      rows.push({ label: `Prev Season Regression${prevLabel}`, detail: 'mean regression blend', value: regressionDelta });
    }

    body.innerHTML = `
      <div class="preseason-breakdown">
        ${rows.map((r, i) => {
          const isLast = i === rows.length - 1;
          const prefix = r.isBase ? '' : (isLast ? '└─' : '├─');
          const valClass = r.isBase ? 'breakdown-base' : r.value > 0 ? 'breakdown-pos' : r.value < 0 ? 'breakdown-neg' : 'breakdown-zero';
          const displayVal = r.isBase ? Math.round(r.value).toLocaleString() : fmt(r.value);
          return `
          <div class="breakdown-row">
            <span class="breakdown-prefix">${prefix}</span>
            <span class="breakdown-label">${r.label}</span>
            <span class="breakdown-detail">${r.detail}</span>
            <span class="breakdown-value ${valClass}">${displayVal}</span>
          </div>`;
        }).join('')}
      </div>`;
  } catch (err) {
    console.error('Error loading preseason breakdown:', err);
    body.innerHTML = '<p style="color:var(--text-muted);padding:0.5rem 0;">Could not load preseason breakdown.</p>';
  }
}

// Populate Team Info
function populateTeamInfo(team) {
  // Team name
  document.getElementById('team-name').textContent = team.name;
  document.title = `${team.name} — Stat-urday`;

  // Update OG tags for rich link previews when this page is shared
  const record = `${team.wins || 0}–${team.losses || 0}`;
  const eloStr = team.elo_rating ? ` · ELO ${Math.round(team.elo_rating)}` : '';
  const rankStr = team.rank ? `#${team.rank} · ` : '';
  const ogDesc = `${rankStr}${record}${eloStr} · ${team.conference_name || team.conference || 'CFB'} · Stat-urday college football rankings`;
  const canonUrl = `https://cfb.bdailey.com/team.html?id=${team.id}`;
  _setOgMeta('og:title', `${team.name} — Stat-urday`);
  _setOgMeta('og:description', ogDesc);
  _setOgMeta('og:url', canonUrl);
  _setOgMeta('twitter:title', `${team.name} — Stat-urday`);
  _setOgMeta('twitter:description', ogDesc);

  // EPIC-036: Wire up copy-link button
  const shareTeamBtn = document.getElementById('share-team-btn');
  if (shareTeamBtn) {
    shareTeamBtn.onclick = () => shareTeam(team.id);
  }

  // EPIC-012: Conference badge with actual conference name
  const confBadge = document.getElementById('conference-badge');
  if (team.conference_name) {
    confBadge.textContent = `${team.conference_name} (${team.conference})`;
  } else {
    confBadge.textContent = team.conference;
  }
  confBadge.className = 'conference-badge';
  if (team.conference === 'P5') {
    confBadge.classList.add('p5');
  } else if (team.conference === 'G5') {
    confBadge.classList.add('g5');
  } else {
    confBadge.classList.add('fcs');
  }

  // Record (FBS games only)
  const recordEl = document.getElementById('team-record');
  recordEl.innerHTML = `
    <span class="record-value">${team.wins}-${team.losses}</span>
    <span class="record-note" title="Record includes FBS opponents only">FBS Only</span>
  `;
  if (team.losses === 0 && team.wins > 0) {
    recordEl.querySelector('.record-value').classList.add('undefeated');
  }

  // Rank
  const rankEl = document.getElementById('team-rank');
  if (team.rank) {
    rankEl.textContent = team.rank;
    rankEl.className = 'rank-badge';
    if (team.rank <= 5) {
      rankEl.classList.add('top-5');
    } else if (team.rank <= 10) {
      rankEl.classList.add('top-10');
    } else {
      rankEl.classList.add('top-25');
    }
    rankEl.style.width = '4rem';
    rankEl.style.height = '4rem';
    rankEl.style.fontSize = '2rem';
  } else {
    rankEl.textContent = 'NR';
    rankEl.style.backgroundColor = 'var(--bg-secondary)';
    rankEl.style.color = 'var(--text-secondary)';
  }

  // ELO Rating
  document.getElementById('elo-rating').textContent = team.elo_rating.toFixed(2);

  // Initial Rating
  document.getElementById('initial-rating').textContent = team.initial_rating.toFixed(2);

  // SOS
  const sosEl = document.getElementById('sos-rating');
  if (team.sos) {
    sosEl.textContent = team.sos.toFixed(2);
    document.getElementById('sos-rank').textContent = `Rank: ${team.sos_rank || '--'}`;
  } else {
    sosEl.textContent = '--';
    document.getElementById('sos-rank').textContent = 'No games played';
  }

  // Rating Change
  const change = team.elo_rating - team.initial_rating;
  const changeEl = document.getElementById('rating-change');
  changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2);
  changeEl.style.color = change >= 0 ? 'var(--success-color)' : 'var(--danger-color)';

  // Preseason factors are now rendered by loadPreseasonBreakdown() via /api/preseason/components
}

// Load Schedule
async function loadSchedule() {
  const scheduleLoading = document.getElementById('schedule-loading');
  const scheduleContainer = document.getElementById('schedule-container');
  const noSchedule = document.getElementById('no-schedule');
  const tbody = document.getElementById('schedule-tbody');

  scheduleLoading.classList.remove('hidden');
  scheduleContainer.classList.add('hidden');
  noSchedule.classList.add('hidden');

  try {
    // Use global season variable (set in DOMContentLoaded)
    const schedule = await api.getTeamSchedule(teamId, season);

    // EPIC-009: Fetch stored predictions for this team
    try {
      const predictions = await api.getStoredPredictions({
        teamId: teamId,
        season: season
      });

      // Store predictions by game_id for quick lookup
      predictions.forEach(pred => {
        predictionData[pred.game_id] = pred;
      });
    } catch (err) {
      console.error('Error loading predictions:', err);
      // Continue without predictions
    }

    if (schedule.games.length === 0) {
      scheduleLoading.classList.add('hidden');
      noSchedule.classList.remove('hidden');
      return;
    }

    // EPIC-023: Store all games for filtering
    allGames = schedule.games;

    // Display all games initially
    filterAndDisplayGames('all');

    scheduleLoading.classList.add('hidden');
    scheduleContainer.classList.remove('hidden');
  } catch (err) {
    console.error('Error loading schedule:', err);
    scheduleLoading.classList.add('hidden');
    noSchedule.classList.remove('hidden');
  }
}

// EPIC-023: Filter and Display Games
function filterAndDisplayGames(filterType) {
  const tbody = document.getElementById('schedule-tbody');
  const noSchedule = document.getElementById('no-schedule');
  const scheduleContainer = document.getElementById('schedule-container');

  // Filter games based on selected type
  let filteredGames = allGames;

  if (filterType !== 'all') {
    filteredGames = allGames.filter(game => {
      if (filterType === 'regular') {
        // Regular season games are those without a game_type (NULL)
        return !game.game_type;
      } else {
        // For other types, match exactly
        return game.game_type === filterType;
      }
    });
  }

  // Clear existing rows
  tbody.innerHTML = '';

  // Check if we have any games to display
  if (filteredGames.length === 0) {
    scheduleContainer.classList.add('hidden');
    noSchedule.classList.remove('hidden');
    noSchedule.textContent = 'No games match the selected filter.';
    return;
  }

  // Populate schedule with filtered games
  filteredGames.forEach(game => {
    const row = createScheduleRow(game);
    tbody.appendChild(row);
  });

  scheduleContainer.classList.remove('hidden');
  noSchedule.classList.add('hidden');
}

// Create Schedule Row
function createScheduleRow(game) {
  const row = document.createElement('tr');

  // Check if game has been played
  const isPlayed = game.is_played && game.score;

  // Check if FCS game (excluded from rankings)
  // EPIC-011: Only mark as FCS if game is played AND excluded
  // This prevents future games from showing FCS badge
  const isFCS = (game.is_fcs || game.excluded_from_rankings) && isPlayed;

  // Apply appropriate row styling
  if (!isPlayed) {
    row.classList.add('game-scheduled');
  } else if (isFCS) {
    row.classList.add('game-fcs');  // FCS game styling
  }

  // Week
  const weekCell = document.createElement('td');
  weekCell.textContent = `Week ${game.week}`;
  weekCell.style.fontWeight = '600';
  row.appendChild(weekCell);

  // Date - EPIC-GAME-DATE-SORTING Story 3
  const dateCell = document.createElement('td');
  const formattedDate = formatGameDate(game.game_date, false); // No relative dates for schedules
  const fullDateTime = getFullDateTime(game.game_date);
  dateCell.textContent = formattedDate;
  dateCell.className = 'game-date';
  dateCell.title = fullDateTime;
  dateCell.style.color = 'var(--text-secondary)';
  dateCell.style.whiteSpace = 'nowrap';
  dateCell.style.fontSize = '0.9em';
  if (!isPlayed) {
    dateCell.style.fontStyle = 'italic';
  }
  row.appendChild(dateCell);

  // Opponent
  const oppCell = document.createElement('td');
  const oppLink = document.createElement('a');
  oppLink.href = `team.html?id=${game.opponent_id}`;
  oppLink.textContent = game.opponent_name;

  if (isFCS) {
    // FCS opponent - grayed out styling
    oppLink.style.color = 'var(--text-secondary)';
    oppLink.style.fontStyle = 'normal';

    // Add FCS badge
    const fcsBadge = document.createElement('span');
    fcsBadge.className = 'fcs-badge';
    fcsBadge.textContent = 'FCS';
    fcsBadge.title = 'FCS opponent - not included in rankings';
    oppCell.appendChild(oppLink);
    oppCell.appendChild(document.createTextNode(' '));
    oppCell.appendChild(fcsBadge);
  } else if (isPlayed) {
    // FBS played game - normal styling
    oppLink.style.color = 'var(--primary-color)';
    oppLink.style.fontWeight = '600';
    oppCell.appendChild(oppLink);

    // EPIC-022: Add conference championship badge if applicable
    if (game.game_type === 'conference_championship') {
      const confChampBadge = document.createElement('span');
      confChampBadge.className = 'conf-champ-badge';
      confChampBadge.textContent = 'CONF CHAMP';
      confChampBadge.title = 'Conference Championship Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(confChampBadge);
    }

    // EPIC-023: Add bowl game badge if applicable
    if (game.game_type === 'bowl') {
      const bowlBadge = document.createElement('span');
      bowlBadge.className = 'bowl-badge';
      bowlBadge.textContent = 'BOWL';
      bowlBadge.title = game.postseason_name || 'Bowl Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(bowlBadge);
    }

    // EPIC-023: Add playoff game badge if applicable
    if (game.game_type === 'playoff') {
      const playoffBadge = document.createElement('span');
      playoffBadge.className = 'playoff-badge';
      playoffBadge.textContent = 'PLAYOFF';
      playoffBadge.title = game.postseason_name || 'CFP Playoff Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(playoffBadge);
    }
  } else {
    // Future FBS game - grayed out
    oppLink.style.color = 'var(--text-secondary)';
    oppLink.style.fontStyle = 'italic';
    oppCell.appendChild(oppLink);

    // EPIC-022: Add conference championship badge for scheduled championship games
    if (game.game_type === 'conference_championship') {
      const confChampBadge = document.createElement('span');
      confChampBadge.className = 'conf-champ-badge';
      confChampBadge.textContent = 'CONF CHAMP';
      confChampBadge.title = 'Conference Championship Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(confChampBadge);
    }

    // EPIC-023: Add bowl game badge for scheduled bowl games
    if (game.game_type === 'bowl') {
      const bowlBadge = document.createElement('span');
      bowlBadge.className = 'bowl-badge';
      bowlBadge.textContent = 'BOWL';
      bowlBadge.title = game.postseason_name || 'Bowl Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(bowlBadge);
    }

    // EPIC-023: Add playoff game badge for scheduled playoff games
    if (game.game_type === 'playoff') {
      const playoffBadge = document.createElement('span');
      playoffBadge.className = 'playoff-badge';
      playoffBadge.textContent = 'PLAYOFF';
      playoffBadge.title = game.postseason_name || 'CFP Playoff Game';
      oppCell.appendChild(document.createTextNode(' '));
      oppCell.appendChild(playoffBadge);
    }
  }

  oppLink.style.textDecoration = 'none';
  oppLink.onmouseover = () => oppLink.style.textDecoration = 'underline';
  oppLink.onmouseout = () => oppLink.style.textDecoration = 'none';

  row.appendChild(oppCell);

  // Location
  const locCell = document.createElement('td');
  if (game.is_neutral_site) {
    locCell.textContent = 'Neutral';
  } else {
    locCell.textContent = game.is_home ? 'Home' : 'Away';
  }
  locCell.style.color = 'var(--text-secondary)';
  if (!isPlayed || isFCS) {
    locCell.style.fontStyle = 'italic';
  }
  row.appendChild(locCell);

  // EPIC-009: Prediction
  const predCell = document.createElement('td');
  const prediction = predictionData[game.game_id];

  if (prediction && !isFCS) {
    const predSpan = document.createElement('span');
    predSpan.className = 'prediction-cell';

    // Determine if this team was predicted to win
    const wasPredictedWinner = prediction.predicted_winner_id === parseInt(teamId);
    const predOutcome = wasPredictedWinner ? 'W' : 'L';
    const probability = (prediction.win_probability * 100).toFixed(0);

    predSpan.textContent = `${predOutcome} (${probability}%)`;
    predSpan.style.fontSize = '0.875rem';

    // If game is complete, color-code based on correctness
    if (isPlayed && prediction.was_correct !== null) {
      if (prediction.was_correct) {
        predSpan.className = 'prediction-cell prediction-correct';
        predSpan.title = 'Correct prediction';
      } else {
        predSpan.className = 'prediction-cell prediction-incorrect';
        predSpan.title = 'Incorrect prediction';
      }
    } else if (!isPlayed) {
      // Future game - gray it out
      predSpan.style.color = 'var(--text-secondary)';
      predSpan.style.fontStyle = 'italic';
      predSpan.title = 'Pre-game prediction';
    }

    predCell.appendChild(predSpan);
  } else {
    // No prediction available
    predCell.textContent = '--';
    predCell.style.color = 'var(--text-secondary)';
    predCell.style.fontSize = '0.875rem';
  }
  row.appendChild(predCell);

  // Result
  const resultCell = document.createElement('td');
  if (isPlayed) {
    const resultSpan = document.createElement('span');
    resultSpan.className = 'game-result';

    if (isFCS) {
      // FCS game - de-emphasized result
      resultSpan.textContent = game.score;
      resultSpan.style.color = 'var(--text-secondary)';
      resultSpan.style.fontStyle = 'italic';
      resultSpan.title = 'FCS game - not included in rankings or record';
    } else {
      // FBS game - normal result styling
      const isWin = game.score.startsWith('W');
      resultSpan.classList.add(isWin ? 'win' : 'loss');
      resultSpan.textContent = game.score;
    }

    resultCell.appendChild(resultSpan);
  } else {
    // Future game - show "vs Opponent" or "TBD"
    resultCell.textContent = `vs ${game.opponent_name}`;
    resultCell.style.color = 'var(--text-secondary)';
    resultCell.style.fontStyle = 'italic';
  }
  row.appendChild(resultCell);

  return row;
}

// Show Error
function showError(message) {
  const loading = document.getElementById('loading');
  const error = document.getElementById('error');

  loading.classList.add('hidden');
  error.classList.remove('hidden');
  document.getElementById('error-message').textContent = ` ${message}`;
}

// ── EPIC-038: Position Group Strength Radar ───────────────────────────────

// Axis order around the radar: offense (top/right) → defense → special teams.
const POSITION_RADAR_AXES = [
  { key: 'QB', label: 'QB' },
  { key: 'RB', label: 'RB' },
  { key: 'WR', label: 'WR' },
  { key: 'TE', label: 'TE' },
  { key: 'OL', label: 'OL' },
  { key: 'DL', label: 'DL' },
  { key: 'LB', label: 'LB' },
  { key: 'DB', label: 'DB' },
  { key: 'ST', label: 'ST' },
];

async function loadPositionRadar(teamId) {
  const body = document.getElementById('position-radar-body');
  if (!body) return;

  const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : '/api';
  try {
    const resp = await fetch(`${baseUrl}/teams/${teamId}/position-strength`);
    if (!resp.ok) throw new Error('Failed to load position strength');
    const data = await resp.json();
    renderPositionRadar(data);
  } catch (err) {
    console.error('Error loading position radar:', err);
    body.innerHTML = '<p style="color:var(--text-secondary);padding:1rem 0;">Position data unavailable.</p>';
  }
}

function renderPositionRadar(data) {
  const body = document.getElementById('position-radar-body');
  const yearEl = document.getElementById('position-radar-year');
  if (!body) return;

  const scores = data.position_scores || {};
  // EPIC-039: roster source reports `season`; recruiting source reports `recruiting_year`
  const isRoster = data.source === 'roster';
  const period = isRoster ? data.season : data.recruiting_year;
  const hasData = period != null &&
    POSITION_RADAR_AXES.some(a => (scores[a.key] || 0) > 0);

  if (!hasData) {
    if (yearEl) yearEl.textContent = '';
    body.innerHTML = `<p style="color:var(--text-secondary);padding:1rem 0;">${
      data.message || 'No roster data available for this team yet.'
    }</p>`;
    return;
  }

  if (yearEl) {
    // EPIC-040: note when on-field production is blended in (skill positions)
    const suffix = isRoster ? (data.blend ? ' roster · blended' : ' roster') : ' class';
    yearEl.textContent = `${period}${suffix}`;
  }

  // Square SVG geometry
  const W = Math.min(body.clientWidth || 420, 420);
  const H = W;
  const cx = W / 2;
  const cy = H / 2;
  const radius = (Math.min(W, H) / 2) - 40; // room for labels
  const n = POSITION_RADAR_AXES.length;
  // Start at top (-90°) and go clockwise
  const angleFor = i => (-Math.PI / 2) + (i * 2 * Math.PI / n);
  const pointAt = (i, frac) => {
    const a = angleFor(i);
    return [cx + Math.cos(a) * radius * frac, cy + Math.sin(a) * radius * frac];
  };

  // Concentric grid rings at 25/50/75/100
  const rings = [0.25, 0.5, 0.75, 1].map(frac => {
    const pts = POSITION_RADAR_AXES.map((_, i) => {
      const [x, y] = pointAt(i, frac);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `<polygon points="${pts}" fill="none" stroke="var(--border-color)" stroke-width="1"/>`;
  }).join('');

  // Axis spokes + labels
  const spokes = POSITION_RADAR_AXES.map((axis, i) => {
    const [ex, ey] = pointAt(i, 1);
    const [lx, ly] = pointAt(i, 1.16);
    const score = Math.round(scores[axis.key] || 0);
    const anchor = Math.abs(lx - cx) < 4 ? 'middle' : (lx > cx ? 'start' : 'end');
    return `
      <line x1="${cx}" y1="${cy}" x2="${ex.toFixed(1)}" y2="${ey.toFixed(1)}" stroke="var(--border-color)" stroke-width="1"/>
      <text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${anchor}" dominant-baseline="middle" font-size="12" font-weight="600" fill="var(--text-primary)">${axis.label}</text>
      <text x="${lx.toFixed(1)}" y="${(ly + 13).toFixed(1)}" text-anchor="${anchor}" dominant-baseline="middle" font-size="10" fill="var(--text-secondary)">${score}</text>
    `;
  }).join('');

  // Data polygon
  const dataPts = POSITION_RADAR_AXES.map((axis, i) => {
    const frac = Math.max(0, Math.min(1, (scores[axis.key] || 0) / 100));
    const [x, y] = pointAt(i, frac);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  const dataDots = POSITION_RADAR_AXES.map((axis, i) => {
    const frac = Math.max(0, Math.min(1, (scores[axis.key] || 0) / 100));
    const [x, y] = pointAt(i, frac);
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="var(--accent)"><title>${axis.label}: ${Math.round(scores[axis.key] || 0)}/100</title></circle>`;
  }).join('');

  const bonus = data.position_bonus != null ? Math.round(data.position_bonus) : null;
  const maxBonus = data.max_bonus != null ? data.max_bonus : null;
  const caption = bonus != null
    ? `<p style="text-align:center;color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">Roster quality bonus: <strong style="color:var(--text-primary);">+${bonus}</strong>${maxBonus ? ` / ${maxBonus}` : ''} preseason ELO points</p>`
    : '';

  body.innerHTML = `
    <div style="display:flex;justify-content:center;">
      <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="position-radar-svg" style="max-width:100%;overflow:visible">
        ${rings}
        ${spokes}
        <polygon points="${dataPts}" fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>
        ${dataDots}
      </svg>
    </div>
    ${caption}
  `;
}

// ── EPIC-031 Story 31.4: ELO History Chart ────────────────────────────────

async function loadEloHistory(teamId, season) {
  const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : '/api';
  const url = season
    ? `${baseUrl}/teams/${teamId}/elo-history?season=${season}`
    : `${baseUrl}/teams/${teamId}/elo-history`;
  try {
    const resp = await fetch(url);
    if (!resp.ok) return [];
    return await resp.json();
  } catch (err) {
    console.error('Error loading ELO history:', err);
    return [];
  }
}

function renderEloChart(data, games) {
  const container = document.getElementById('elo-chart-container');
  if (!container || data.length < 2) {
    if (container) {
      container.innerHTML = '<p style="color:var(--text-muted,var(--text-secondary));padding:1rem;">Not enough data to display chart.</p>';
    }
    return;
  }

  const W = container.clientWidth || 600;
  const H = 200;
  const padL = 56, padR = 16, padT = 16, padB = 32;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const weeks = data.map(d => d.week);
  const elos = data.map(d => d.elo_rating);
  const minW = Math.min(...weeks), maxW = Math.max(...weeks);
  const minE = Math.min(...elos) - 20, maxE = Math.max(...elos) + 20;

  const xScale = w => padL + ((w - minW) / (maxW - minW || 1)) * chartW;
  const yScale = e => padT + chartH - ((e - minE) / (maxE - minE || 1)) * chartH;

  // Build polyline points
  const pts = data.map(d => `${xScale(d.week).toFixed(1)},${yScale(d.elo_rating).toFixed(1)}`).join(' ');

  // Y-axis grid lines (4 lines)
  const gridLines = [];
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const e = minE + (i / yTicks) * (maxE - minE);
    const y = yScale(e);
    gridLines.push(`
      <line x1="${padL}" y1="${y.toFixed(1)}" x2="${W - padR}" y2="${y.toFixed(1)}" stroke="var(--border-color)" stroke-width="1"/>
      <text x="${(padL - 4).toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="10" fill="var(--text-secondary)">${Math.round(e)}</text>
    `);
  }

  // X-axis week labels
  const xLabels = data.map(d => `
    <text x="${xScale(d.week).toFixed(1)}" y="${(H - 4).toFixed(1)}" text-anchor="middle" font-size="10" fill="var(--text-secondary)">W${d.week}</text>
  `).join('');

  // Game result dots
  const gameMap = {};
  if (games) games.forEach(g => { gameMap[g.week] = g; });

  const dots = data.map(d => {
    const g = gameMap[d.week];
    if (!g || !g.result) return '';
    const cx = xScale(d.week).toFixed(1);
    const cy = yScale(d.elo_rating).toFixed(1);
    const color = g.result === 'W' ? 'var(--success-color)' : 'var(--danger-color)';
    const delta = g.elo_delta != null ? (g.elo_delta > 0 ? `+${g.elo_delta}` : g.elo_delta) : '';
    const tip = `${g.result} vs ${g.opponent} ${g.team_score}-${g.opponent_score}${delta ? ' (' + delta + ')' : ''}`;
    return `<circle cx="${cx}" cy="${cy}" r="5" fill="${color}" stroke="var(--bg-card)" stroke-width="2"><title>${tip}</title></circle>`;
  }).join('');

  // Gradient fill under the line
  const fillPts = `${padL.toFixed(1)},${(padT + chartH).toFixed(1)} ${pts} ${(W - padR).toFixed(1)},${(padT + chartH).toFixed(1)}`;

  container.innerHTML = `
    <svg width="100%" height="${H}" viewBox="0 0 ${W} ${H}" class="elo-chart-svg" style="overflow:visible">
      <defs>
        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      ${gridLines.join('')}
      <polygon points="${fillPts}" fill="url(#chartFill)"/>
      <polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      ${dots}
      ${xLabels}
    </svg>
  `;
}

// ── EPIC-031 Story 31.4: Game Log ─────────────────────────────────────────

async function loadGameLog(teamId, season) {
  const container = document.getElementById('game-log-container');
  if (!container) return [];

  const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : '/api';
  const url = season
    ? `${baseUrl}/teams/${teamId}/games?season=${season}`
    : `${baseUrl}/teams/${teamId}/games`;

  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('Failed to load games');
    const games = await resp.json();

    if (games.length === 0) {
      container.innerHTML = '<p style="color:var(--text-secondary);padding:1rem 0;">No games played yet this season.</p>';
      return [];
    }

    const rows = games.map(g => {
      const deltaClass = g.elo_delta > 0 ? 'elo-delta-up' : g.elo_delta < 0 ? 'elo-delta-down' : '';
      const deltaText = g.elo_delta != null ? (g.elo_delta > 0 ? `+${g.elo_delta}` : g.elo_delta) : '—';
      const resultClass = g.result === 'W' ? 'result-win' : g.result === 'L' ? 'result-loss' : '';
      const locIcon = g.location === 'Home' ? '🏠' : g.location === 'Away' ? '✈' : '⚖';
      const score = g.team_score != null ? `${g.team_score}–${g.opponent_score}` : '—';
      const fcsNote = g.is_fcs ? ' <span class="record-note">FCS</span>' : '';
      return `<tr>
        <td>Wk ${g.week}</td>
        <td><span title="${g.location}">${locIcon}</span> <a href="team.html?id=${g.opponent_id}" class="team-link">${g.opponent}</a>${fcsNote}</td>
        <td><span class="result-badge ${resultClass}">${g.result || '—'}</span></td>
        <td class="tabular">${score}</td>
        <td class="tabular">${g.elo_before != null ? g.elo_before : '—'}</td>
        <td class="tabular">${g.elo_after != null ? g.elo_after : '—'}</td>
        <td class="tabular"><span class="${deltaClass}">${deltaText}</span></td>
      </tr>`;
    }).join('');

    container.innerHTML = `
      <div class="table-container">
        <table class="game-log-table">
          <thead><tr>
            <th>Week</th><th>Opponent</th><th>Result</th><th>Score</th>
            <th>ELO Before</th><th>ELO After</th><th>Δ ELO</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;

    return games;
  } catch (err) {
    container.innerHTML = `<p style="color:var(--danger-color,var(--error-color));padding:1rem 0;">Error loading games: ${err.message}</p>`;
    return [];
  }
}

// ── EPIC-031 Story 31.4: Team Logo ────────────────────────────────────────

function renderTeamLogo(team) {
  const logoContainer = document.getElementById('team-logo');
  if (!logoContainer) return;

  if (team.espn_id) {
    const img = document.createElement('img');
    img.src = `https://a.espncdn.com/i/teamlogos/ncaa/500/${team.espn_id}.png`;
    img.alt = team.name;
    img.className = 'team-logo-img';
    img.onerror = () => { logoContainer.innerHTML = initialsAvatar(team.name); };
    logoContainer.innerHTML = '';
    logoContainer.appendChild(img);
  } else {
    logoContainer.innerHTML = initialsAvatar(team.name);
  }
}

function initialsAvatar(name) {
  const words = name.split(' ').filter(Boolean);
  const initials = words.length >= 2
    ? words[0][0] + words[words.length - 1][0]
    : name.substring(0, 2);
  // Deterministic color from name hash
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return `<div class="team-logo-initials" style="background:hsl(${hue},55%,35%)">${initials.toUpperCase()}</div>`;
}
