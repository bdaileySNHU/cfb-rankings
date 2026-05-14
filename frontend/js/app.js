// Main Application Logic for Rankings Page

// State
let currentLimit = 25;
let currentSeason = null;  // EPIC-024: Selected season
let activeSeason = null;   // EPIC-024: Current active season
let rankingsData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadSeasons();  // EPIC-024: Load seasons first
  loadStats();
  loadPredictionAccuracy(); // EPIC-009
  loadPredictions();
  setupEventListeners();
  setupPredictionListeners();
  setupHistoricalSimListeners();
});

// Setup Event Listeners
function setupEventListeners() {
  const limitSelect = document.getElementById('limit-select');
  if (limitSelect) {
    limitSelect.addEventListener('change', (e) => {
      currentLimit = parseInt(e.target.value);
      loadRankings();
    });
  }

  // EPIC-024: Season selector
  const seasonSelect = document.getElementById('season-select');
  if (seasonSelect) {
    seasonSelect.addEventListener('change', (e) => {
      currentSeason = e.target.value ? parseInt(e.target.value) : activeSeason;
      updateHistoricalBanner();
      loadRankings();
      loadPredictions({ nextWeek: currentSeason === activeSeason });
    });
  }

  // EPIC-024: Return to current season button
  const returnBtn = document.getElementById('return-to-current');
  if (returnBtn) {
    returnBtn.addEventListener('click', () => {
      currentSeason = activeSeason;
      document.getElementById('season-select').value = activeSeason;
      updateHistoricalBanner();
      loadRankings();
      loadPredictions({ nextWeek: true });
    });
  }

  // EPIC-036: Share Top 25 button
  const shareTop25Btn = document.getElementById('share-top25-btn');
  if (shareTop25Btn) {
    shareTop25Btn.addEventListener('click', () => {
      const rankings = rankingsData ? rankingsData.rankings : null;
      downloadTop25Card(rankings, currentSeason);
    });
  }
}

// EPIC-024: Load available seasons
async function loadSeasons() {
  try {
    const seasonsResponse = await fetch('/api/seasons');
    const seasons = await seasonsResponse.json();

    // Get active season
    const activeResponse = await fetch('/api/seasons/active');
    const activeSeasonData = await activeResponse.json();
    activeSeason = activeSeasonData.year;
    currentSeason = activeSeason;  // Default to active season

    // Populate season selector
    const seasonSelect = document.getElementById('season-select');
    seasonSelect.innerHTML = '';

    seasons.forEach(season => {
      const option = document.createElement('option');
      option.value = season.year;
      option.textContent = `${season.year} Season${season.is_active ? ' (Current)' : ''}`;
      if (season.year === activeSeason) {
        option.selected = true;
      }
      seasonSelect.appendChild(option);
    });

    // Load rankings after seasons are loaded
    loadRankings();
  } catch (error) {
    console.error('Error loading seasons:', error);
    // Fallback: load rankings anyway
    loadRankings();
  }
}

// EPIC-024: Update historical season banner
function updateHistoricalBanner() {
  const banner = document.getElementById('historical-banner');
  const seasonYear = document.getElementById('historical-season-year');

  if (currentSeason && currentSeason !== activeSeason) {
    // Show historical banner
    seasonYear.textContent = currentSeason;
    banner.style.display = 'flex';
  } else {
    // Hide historical banner
    banner.style.display = 'none';
  }
}

// Load System Stats
async function loadStats() {
  try {
    const stats = await api.getStats();

    document.getElementById('current-week').textContent = stats.current_week;
    document.getElementById('current-season').textContent = stats.current_season;
    document.getElementById('total-teams').textContent = stats.total_teams;
    document.getElementById('games-played').textContent = stats.total_games_processed;

    const lastUpdated = new Date(stats.last_updated);
    document.getElementById('last-updated').textContent = lastUpdated.toLocaleTimeString();
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

// Load Rankings
async function loadRankings() {
  const loading = document.getElementById('loading');
  const error = document.getElementById('error');
  const container = document.getElementById('rankings-container');
  const tbody = document.getElementById('rankings-tbody');

  // Show loading
  loading.classList.remove('hidden');
  error.classList.add('hidden');
  container.classList.add('hidden');

  try {
    // EPIC-024: Pass season parameter
    const data = await api.getRankings(currentLimit, currentSeason);
    rankingsData = data;

    // Clear existing rows
    tbody.innerHTML = '';

    // Populate table
    data.rankings.forEach(team => {
      const row = createRankingRow(team);
      tbody.appendChild(row);
    });

    // Show table
    loading.classList.add('hidden');
    container.classList.remove('hidden');
  } catch (err) {
    console.error('Error loading rankings:', err);
    loading.classList.add('hidden');
    error.classList.remove('hidden');
    document.getElementById('error-message').textContent = ` ${err.message}`;
  }
}

// Create Ranking Row
function createRankingRow(team) {
  const row = document.createElement('tr');
  row.onclick = () => {
    window.location.href = `team.html?id=${team.team_id}`;
  };

  // Rank with badge
  const rankCell = document.createElement('td');
  const rankBadge = document.createElement('span');
  rankBadge.className = 'rank-badge';
  if (team.rank <= 5) {
    rankBadge.classList.add('top-5');
  } else if (team.rank <= 10) {
    rankBadge.classList.add('top-10');
  } else {
    rankBadge.classList.add('top-25');
  }
  rankBadge.textContent = team.rank;
  rankCell.appendChild(rankBadge);
  row.appendChild(rankCell);

  // EPIC-031 Story 31.2: Rank change cell (column 2)
  const changeCell = document.createElement('td');
  changeCell.className = 'rank-change-cell col-change';
  if (team.rank_change === null || team.rank_change === undefined) {
    changeCell.innerHTML = '<span class="rank-new">NEW</span>';
  } else if (team.rank_change > 0) {
    changeCell.innerHTML = `<span class="rank-up">▲${team.rank_change}</span>`;
  } else if (team.rank_change < 0) {
    changeCell.innerHTML = `<span class="rank-down">▼${Math.abs(team.rank_change)}</span>`;
  } else {
    changeCell.innerHTML = '<span class="rank-same">—</span>';
  }
  row.appendChild(changeCell);

  // Team Name (with ESPN logo)
  const teamCell = document.createElement('td');
  teamCell.className = 'team-name-cell';
  const teamInner = document.createElement('div');
  teamInner.className = 'team-name-inner';
  // Small logo or initials fallback
  const logoEl = document.createElement('span');
  logoEl.className = 'team-logo-small';
  if (team.espn_id) {
    const img = document.createElement('img');
    img.src = `https://a.espncdn.com/i/teamlogos/ncaa/500/${team.espn_id}.png`;
    img.width = 24; img.height = 24;
    img.alt = '';
    img.onerror = () => { logoEl.innerHTML = smallInitials(team.team_name); };
    logoEl.appendChild(img);
  } else {
    logoEl.innerHTML = smallInitials(team.team_name);
  }
  const teamName = document.createElement('span');
  teamName.className = 'team-name';
  teamName.textContent = team.team_name;
  teamInner.appendChild(logoEl);
  teamInner.appendChild(teamName);
  teamCell.appendChild(teamInner);
  row.appendChild(teamCell);

  // EPIC-012: Conference with actual conference name
  const confCell = document.createElement('td');
  const confBadge = document.createElement('span');
  confBadge.className = 'conference-badge';
  if (team.conference === 'P5') {
    confBadge.classList.add('p5');
  } else if (team.conference === 'G5') {
    confBadge.classList.add('g5');
  } else {
    confBadge.classList.add('fcs');
  }
  if (team.conference_name) {
    confBadge.textContent = `${team.conference_name} (${team.conference})`;
  } else {
    confBadge.textContent = team.conference;
  }
  confCell.appendChild(confBadge);
  row.appendChild(confCell);

  // Record (FBS games only)
  const recordCell = document.createElement('td');
  recordCell.style.display = 'flex';
  recordCell.style.alignItems = 'center';
  recordCell.style.gap = '4px';

  const recordSpan = document.createElement('span');
  recordSpan.className = 'record';
  if (team.losses === 0 && team.wins > 0) {
    recordSpan.classList.add('undefeated');
  }
  recordSpan.textContent = `${team.wins}-${team.losses}`;
  recordCell.appendChild(recordSpan);

  // Add FBS Only note
  const recordNote = document.createElement('span');
  recordNote.className = 'record-note';
  recordNote.textContent = 'FBS';
  recordNote.title = 'Record includes FBS opponents only';
  recordNote.style.fontSize = '0.7rem';
  recordCell.appendChild(recordNote);

  row.appendChild(recordCell);

  // ELO Rating
  const eloCell = document.createElement('td');
  eloCell.textContent = team.elo_rating.toFixed(2);
  eloCell.style.fontWeight = '600';
  row.appendChild(eloCell);

  // EPIC-031 Story 31.2: Sparkline cell (column 7)
  const sparkCell = document.createElement('td');
  sparkCell.className = 'sparkline-cell col-sparkline';
  if (team.elo_history && team.elo_history.length >= 2) {
    sparkCell.innerHTML = createSparklineSVG(team.elo_history);
  } else {
    sparkCell.innerHTML = '<span style="color:var(--text-muted);font-size:0.75rem;">—</span>';
  }
  row.appendChild(sparkCell);

  // SOS
  const sosCell = document.createElement('td');
  sosCell.className = 'col-sos';
  const sosIndicator = document.createElement('span');
  sosIndicator.className = 'sos-indicator';
  if (team.sos >= 1700) {
    sosIndicator.classList.add('elite');
  } else if (team.sos >= 1600) {
    sosIndicator.classList.add('hard');
  } else if (team.sos >= 1500) {
    sosIndicator.classList.add('average');
  } else {
    sosIndicator.classList.add('easy');
  }
  sosCell.appendChild(sosIndicator);
  const sosText = document.createTextNode(team.sos.toFixed(2));
  sosCell.appendChild(sosText);
  row.appendChild(sosCell);

  // SOS Rank
  const sosRankCell = document.createElement('td');
  sosRankCell.className = 'col-sos';
  sosRankCell.textContent = team.sos_rank || '--';
  sosRankCell.style.color = 'var(--text-secondary)';
  row.appendChild(sosRankCell);

  return row;
}

// EPIC-037: Tiny initials circle for teams without ESPN logo
function smallInitials(name) {
  const initials = name.split(' ').filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const hue = [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) & 0xffff, 0) % 360;
  return `<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="12" fill="hsl(${hue},55%,35%)"/>
    <text x="12" y="12" text-anchor="middle" dominant-baseline="central"
      font-family="system-ui,sans-serif" font-size="9" font-weight="700" fill="white">${initials}</text>
  </svg>`;
}

// EPIC-031 Story 31.2: Create SVG sparkline for ELO trend
function createSparklineSVG(values) {
  const W = 64, H = 24, pad = 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = values.length;

  const pts = values.map((v, i) => {
    const x = pad + (i / (n - 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / range) * (H - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // Colour: compare last vs first value
  const trend = values[values.length - 1] - values[0];
  const colour = trend > 0 ? 'var(--success-color)' : trend < 0 ? 'var(--error-color)' : 'var(--text-muted)';

  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="sparkline-svg">
    <polyline points="${pts.join(' ')}" fill="none" stroke="${colour}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${pts[pts.length-1].split(',')[0]}" cy="${pts[pts.length-1].split(',')[1]}" r="2" fill="${colour}"/>
  </svg>`;
}

// Utility: Format Date
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

// Utility: Format Time
function formatTime(dateString) {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit'
  });
}

// ============================================================================
// PREDICTIONS
// ============================================================================

// Setup Prediction Event Listeners
function setupPredictionListeners() {
  const nextWeekBtn = document.getElementById('next-week-btn');
  const weekSelector = document.getElementById('week-selector');
  const refreshBtn = document.getElementById('refresh-predictions-btn');

  if (nextWeekBtn) {
    nextWeekBtn.addEventListener('click', () => {
      setActiveFilterButton('next-week-btn');
      weekSelector.value = '';
      loadPredictions({ nextWeek: true });
    });
  }

  if (weekSelector) {
    weekSelector.addEventListener('change', (e) => {
      const week = e.target.value;
      if (week) {
        setActiveFilterButton(null);
        loadPredictions({ nextWeek: false, week: parseInt(week) });
      }
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      const selectedWeek = weekSelector.value;
      if (selectedWeek) {
        loadPredictions({ nextWeek: false, week: parseInt(selectedWeek) });
      } else {
        loadPredictions({ nextWeek: true });
      }
    });
  }
}

// Set Active Filter Button
function setActiveFilterButton(buttonId) {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });

  if (buttonId) {
    const btn = document.getElementById(buttonId);
    if (btn) btn.classList.add('active');
  }
}

// Load Predictions
async function loadPredictions(filters = { nextWeek: true }) {
  const loading = document.getElementById('predictions-loading');
  const empty = document.getElementById('predictions-empty');
  const historical = document.getElementById('predictions-historical');
  const error = document.getElementById('predictions-error');
  const container = document.getElementById('predictions-container');

  // Hide all states first
  loading.classList.add('hidden');
  empty.classList.add('hidden');
  if (historical) historical.classList.add('hidden');
  error.classList.add('hidden');
  container.innerHTML = '';

  // Toggle live controls visibility based on historical vs current season
  const liveControls = document.getElementById('predictions-live-controls');

  // Historical seasons have no upcoming games — show simulator instead
  if (currentSeason && activeSeason && currentSeason !== activeSeason) {
    if (liveControls) liveControls.style.display = 'none';
    if (historical) historical.classList.remove('hidden');
    return;
  }

  // Current season: show live controls
  if (liveControls) liveControls.style.display = '';

  // Show loading
  loading.classList.remove('hidden');

  try {
    // Always include the currently selected season
    const seasonFilters = { ...filters, season: currentSeason };
    const predictions = await api.getPredictions(seasonFilters);

    // Hide loading
    loading.classList.add('hidden');

    // Handle empty results
    if (predictions.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    // EPIC-020 Story 20.2: Sort predictions by highest team rating (best matchups first)
    predictions.sort((a, b) => {
      // Get highest rating from each matchup
      const maxRatingA = Math.max(a.home_team_rating || 0, a.away_team_rating || 0);
      const maxRatingB = Math.max(b.home_team_rating || 0, b.away_team_rating || 0);
      // Sort descending (highest rating first)
      return maxRatingB - maxRatingA;
    });

    // Render predictions
    predictions.forEach(pred => {
      const card = createPredictionCard(pred);
      container.appendChild(card);
    });

    // EPIC-031 Story 31.3: Animate probability bars after all cards are in DOM
    animatePredictionBars();

  } catch (err) {
    console.error('Error loading predictions:', err);
    loading.classList.add('hidden');
    error.classList.remove('hidden');
    document.getElementById('predictions-error-message').textContent = ` ${err.message}`;
  }
}

// Create Prediction Card (EPIC-031 Story 31.3 redesign)
function createPredictionCard(prediction) {
  const card = document.createElement('div');
  card.className = 'prediction-card';

  const homeWins = prediction.predicted_winner === prediction.home_team;
  const spread = Math.abs(prediction.predicted_home_score - prediction.predicted_away_score).toFixed(1);
  const favoredTeam = homeWins ? prediction.home_team : prediction.away_team;
  const isLock = prediction.home_win_probability >= 80 || prediction.away_win_probability >= 80;
  const homeProb = parseFloat(prediction.home_win_probability);
  const awayProb = parseFloat(prediction.away_win_probability);

  const gameDate = formatGameDate(prediction.game_date, true);
  const fullDateTime = getFullDateTime(prediction.game_date);

  // Location label
  const locationLabel = prediction.is_neutral_site
    ? '⚖ Neutral Site'
    : `🏠 ${prediction.home_team}`;

  card.innerHTML = `
    <div class="pred-header">
      <div class="pred-header-left">
        <span class="pred-badge">PREDICTED</span>
        <span class="pred-meta" title="${fullDateTime}">Week ${prediction.week}${gameDate ? ' · ' + gameDate : ''}</span>
      </div>
      ${isLock ? '<span class="pred-lock-badge">🔒 Lock</span>' : ''}
    </div>

    <div class="pred-matchup">
      <div class="pred-team ${!homeWins ? 'pred-team--winner' : ''}">
        <span class="pred-team-name">${prediction.away_team}</span>
        <span class="pred-team-score">${prediction.predicted_away_score}</span>
        <span class="pred-team-label">Away</span>
      </div>
      <div class="pred-vs">VS</div>
      <div class="pred-team pred-team--home ${homeWins ? 'pred-team--winner' : ''}">
        <span class="pred-team-name">${prediction.home_team}</span>
        <span class="pred-team-score">${prediction.predicted_home_score}</span>
        <span class="pred-team-label">Home</span>
      </div>
    </div>

    <div class="pred-prob-bar-wrap">
      <div class="pred-prob-bar">
        <div class="pred-prob-fill pred-prob-fill--away" style="width: 0%" data-width="${awayProb}"></div>
        <div class="pred-prob-fill pred-prob-fill--home" style="width: 0%" data-width="${homeProb}"></div>
      </div>
      <div class="pred-prob-labels">
        <span class="pred-prob-pct ${!homeWins ? 'pred-prob-pct--winner' : ''}">${awayProb.toFixed(1)}%</span>
        <span class="pred-prob-pct pred-prob-pct--right ${homeWins ? 'pred-prob-pct--winner' : ''}">${homeProb.toFixed(1)}%</span>
      </div>
    </div>

    <div class="pred-footer">
      <span class="pred-spread">${favoredTeam} favored by <strong>${spread} pts</strong></span>
      <span class="pred-location">${locationLabel}</span>
    </div>
    <div class="pred-confidence confidence-indicator confidence-${prediction.confidence.toLowerCase()}">
      <span class="confidence-label">Confidence:</span>
      <span class="confidence-value">${prediction.confidence}</span>
    </div>
    <div class="pred-share-row">
      <button class="copy-link-btn pred-copy-link"
        data-home-id="${prediction.home_team_id}"
        data-away-id="${prediction.away_team_id}"
        title="Copy matchup link">🔗 Copy Link</button>
    </div>
  `;

  // Wire up copy-link button
  card.querySelector('.pred-copy-link').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    sharePrediction(btn.dataset.homeId, btn.dataset.awayId);
  });

  return card;
}

// EPIC-031 Story 31.3: Animate probability bars from 0 to actual width
function animatePredictionBars() {
  requestAnimationFrame(() => {
    document.querySelectorAll('.pred-prob-fill[data-width]').forEach(el => {
      el.style.width = el.dataset.width + '%';
    });
  });
}

// EPIC-009: Load Prediction Accuracy
async function loadPredictionAccuracy() {
  try {
    const activeSeason = await api.getActiveSeason();
    const accuracy = await api.getPredictionAccuracy(activeSeason);

    if (accuracy.evaluated_predictions > 0) {
      const banner = document.getElementById('accuracy-banner');
      const accuracyEl = document.getElementById('overall-accuracy');
      const detailsEl = document.getElementById('accuracy-details');

      accuracyEl.textContent = `${accuracy.accuracy_percentage.toFixed(1)}%`;
      detailsEl.textContent = `${accuracy.correct_predictions} correct out of ${accuracy.evaluated_predictions} predictions`;

      banner.style.display = 'block';
    }
  } catch (error) {
    console.error('Error loading prediction accuracy:', error);
    // Don't show error - just hide the banner
  }
}

// ============================================================================
// HISTORICAL PREDICTION SIMULATOR
// ============================================================================

function setupHistoricalSimListeners() {
  const weekSel = document.getElementById('historical-week-selector');
  if (weekSel) {
    weekSel.addEventListener('change', (e) => {
      const week = parseInt(e.target.value);
      if (week && currentSeason) loadHistoricalPredictions(currentSeason, week);
    });
  }
}

async function loadHistoricalPredictions(season, week) {
  const loading  = document.getElementById('historical-sim-loading');
  const empty    = document.getElementById('historical-sim-empty');
  const summary  = document.getElementById('historical-sim-summary');
  const container = document.getElementById('historical-sim-container');

  loading.classList.remove('hidden');
  empty.classList.add('hidden');
  summary.classList.add('hidden');
  container.innerHTML = '';

  try {
    const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000/api' : '/api';
    const resp = await fetch(`${baseUrl}/predictions/historical?season=${season}&week=${week}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    loading.classList.add('hidden');

    if (!data.predictions || data.predictions.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    // Accuracy summary bar
    if (data.games_with_results > 0) {
      const pct = data.accuracy_percentage;
      const colour = pct >= 70 ? 'var(--success-color)' : pct >= 55 ? 'var(--warning-color)' : 'var(--error-color, #e53e3e)';
      summary.innerHTML = `
        <span>Week ${week} — <strong>${data.correct_predictions}/${data.games_with_results}</strong> correct
        (<strong style="color:${colour}">${pct}%</strong>)</span>
        <span style="color:var(--text-secondary);font-size:0.85rem;">${data.total_games} games total</span>`;
      summary.classList.remove('hidden');
    }

    // Sort: incorrect first (more interesting), then correct, then no-result
    const sorted = [...data.predictions].sort((a, b) => {
      const rank = p => p.prediction_correct === false ? 0 : p.prediction_correct === true ? 1 : 2;
      return rank(a) - rank(b);
    });

    container.innerHTML = sorted.map(p => createHistoricalCard(p)).join('');

    // EPIC-031 Story 31.3: Animate probability bars after cards are in DOM
    animatePredictionBars();

  } catch (err) {
    loading.classList.add('hidden');
    console.error('Historical predictions error:', err);
    empty.classList.remove('hidden');
    empty.querySelector('p').textContent = `Error loading simulations: ${err.message}`;
  }
}

// EPIC-031 Story 31.3: Historical card with new visual design
function createHistoricalCard(p) {
  const homeWinner = p.predicted_winner_id === p.home_team_id;
  const homeProb   = parseFloat(p.home_win_probability);
  const awayProb   = parseFloat(p.away_win_probability);
  const spread     = Math.abs(p.predicted_home_score - p.predicted_away_score).toFixed(1);
  const favoredTeam = homeWinner ? p.home_team : p.away_team;

  // Result badge
  let resultBadge = '';
  if (p.prediction_correct === true) {
    resultBadge = `<span class="hist-result-badge hist-correct">✓ Correct</span>`;
  } else if (p.prediction_correct === false) {
    resultBadge = `<span class="hist-result-badge hist-wrong">✗ Wrong</span>`;
  }

  // Actual score line
  let actualLine = '';
  if (p.actual_home_score !== null && p.actual_away_score !== null) {
    const homeWon = p.actual_home_score > p.actual_away_score;
    actualLine = `
      <div class="hist-actual">
        <span class="hist-actual-label">Actual:</span>
        <span class="${homeWon ? 'hist-winner' : ''}">${p.home_team} ${p.actual_home_score}</span>
        <span class="hist-vs">–</span>
        <span class="${!homeWon ? 'hist-winner' : ''}">${p.away_team} ${p.actual_away_score}</span>
      </div>`;
  }

  const gameDate = p.game_date ? ` · ${new Date(p.game_date).toLocaleDateString('en-US', {month:'short', day:'numeric'})}` : '';

  // Location label
  const locationLabel = p.is_neutral_site ? '⚖ Neutral Site' : `🏠 ${p.home_team}`;

  const cardClass = `prediction-card hist-card${p.prediction_correct === false ? ' hist-card-wrong' : p.prediction_correct === true ? ' hist-card-correct' : ''}`;

  return `
    <div class="${cardClass}">
      <div class="pred-header">
        <div class="pred-header-left">
          <span class="pred-badge hist-badge">SIMULATED</span>
          <span class="pred-meta">Week ${p.week}${gameDate}</span>
        </div>
        ${resultBadge}
      </div>

      <div class="pred-matchup">
        <div class="pred-team ${!homeWinner ? 'pred-team--winner' : ''}">
          <span class="pred-team-name">${p.away_team}</span>
          <span class="pred-team-score">${p.predicted_away_score}</span>
          <span class="pred-team-label">Away</span>
        </div>
        <div class="pred-vs">VS</div>
        <div class="pred-team pred-team--home ${homeWinner ? 'pred-team--winner' : ''}">
          <span class="pred-team-name">${p.home_team}</span>
          <span class="pred-team-score">${p.predicted_home_score}</span>
          <span class="pred-team-label">Home</span>
        </div>
      </div>

      <div class="pred-prob-bar-wrap">
        <div class="pred-prob-bar">
          <div class="pred-prob-fill pred-prob-fill--away" style="width: 0%" data-width="${awayProb}"></div>
          <div class="pred-prob-fill pred-prob-fill--home" style="width: 0%" data-width="${homeProb}"></div>
        </div>
        <div class="pred-prob-labels">
          <span class="pred-prob-pct ${!homeWinner ? 'pred-prob-pct--winner' : ''}">${awayProb.toFixed(1)}%</span>
          <span class="pred-prob-pct pred-prob-pct--right ${homeWinner ? 'pred-prob-pct--winner' : ''}">${homeProb.toFixed(1)}%</span>
        </div>
      </div>

      <div class="pred-footer">
        <span class="pred-spread">${favoredTeam} favored by <strong>${spread} pts</strong></span>
        <span class="pred-location">${locationLabel}</span>
      </div>
      <div class="pred-confidence confidence-indicator confidence-${p.confidence.toLowerCase()}">
        <span class="confidence-label">Confidence:</span>
        <span class="confidence-value">${p.confidence}</span>
      </div>
      ${actualLine}
    </div>`;
}
