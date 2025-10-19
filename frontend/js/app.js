// Main Application Logic for Rankings Page

// State
let currentLimit = 25;
let rankingsData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadRankings();
  setupEventListeners();
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
