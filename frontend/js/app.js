// Main Application Logic for Rankings Page

// State
let currentLimit = 25;
let rankingsData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadPredictions();
  loadRankings();
  setupEventListeners();
  setupPredictionListeners();
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
}

// Load System Stats
async function loadStats() {
  try {
    const stats = await api.getStats();

    document.getElementById('current-week').textContent = stats.current_week;
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
    const data = await api.getRankings(currentLimit);
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

  // Team Name
  const teamCell = document.createElement('td');
  const teamName = document.createElement('span');
  teamName.className = 'team-name';
  teamName.textContent = team.team_name;
  teamCell.appendChild(teamName);
  row.appendChild(teamCell);

  // Conference
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
  confBadge.textContent = team.conference;
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

  // SOS
  const sosCell = document.createElement('td');
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
  sosRankCell.textContent = team.sos_rank || '--';
  sosRankCell.style.color = 'var(--text-secondary)';
  row.appendChild(sosRankCell);

  return row;
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
  const error = document.getElementById('predictions-error');
  const container = document.getElementById('predictions-container');

  // Show loading
  loading.classList.remove('hidden');
  empty.classList.add('hidden');
  error.classList.add('hidden');
  container.innerHTML = '';

  try {
    const predictions = await api.getPredictions(filters);

    // Hide loading
    loading.classList.add('hidden');

    // Handle empty results
    if (predictions.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    // Render predictions
    predictions.forEach(pred => {
      const card = createPredictionCard(pred);
      container.appendChild(card);
    });

  } catch (err) {
    console.error('Error loading predictions:', err);
    loading.classList.add('hidden');
    error.classList.remove('hidden');
    document.getElementById('predictions-error-message').textContent = ` ${err.message}`;
  }
}

// Create Prediction Card
function createPredictionCard(prediction) {
  const card = document.createElement('div');
  card.className = 'prediction-card';

  // Determine winner styling
  const homeIsWinner = prediction.predicted_winner === prediction.home_team;
  const awayIsWinner = prediction.predicted_winner === prediction.away_team;

  // Format game date
  let gameDate = '';
  if (prediction.game_date) {
    const date = new Date(prediction.game_date);
    gameDate = date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  card.innerHTML = `
    <div class="prediction-header">
      <span class="prediction-badge">PREDICTED</span>
      <span class="game-info">Week ${prediction.week}${gameDate ? ' • ' + gameDate : ''}</span>
    </div>

    <div class="matchup">
      <div class="team away-team ${awayIsWinner ? 'predicted-winner' : ''}">
        <span class="team-name">${prediction.away_team}</span>
        <span class="score">${prediction.predicted_away_score}</span>
      </div>

      <div class="matchup-separator">
        <span class="at-symbol">@</span>
      </div>

      <div class="team home-team ${homeIsWinner ? 'predicted-winner' : ''}">
        <span class="team-name">${prediction.home_team}</span>
        <span class="score">${prediction.predicted_home_score}</span>
      </div>
    </div>

    <div class="prediction-details">
      <div class="win-probability">
        <span class="prob-label">Win Probability:</span>
        <span class="prob-values">
          ${prediction.home_team}: ${prediction.home_win_probability}%
          •
          ${prediction.away_team}: ${prediction.away_win_probability}%
        </span>
      </div>
      <div class="confidence-indicator confidence-${prediction.confidence.toLowerCase()}">
        <span class="confidence-label">Confidence:</span>
        <span class="confidence-value">${prediction.confidence}</span>
      </div>
    </div>

    ${prediction.is_neutral_site ? '<div class="neutral-site-badge">Neutral Site</div>' : ''}
  `;

  return card;
}
