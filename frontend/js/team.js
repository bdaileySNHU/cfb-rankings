// Team Details Page Logic

let teamId = null;
let teamData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Get team ID from URL
  const params = new URLSearchParams(window.location.search);
  teamId = params.get('id');

  if (!teamId) {
    showError('No team ID provided');
    return;
  }

  loadTeamDetails();
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
    // Load team data
    teamData = await api.getTeam(teamId);

    // Populate team info
    populateTeamInfo(teamData);

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

// Populate Team Info
function populateTeamInfo(team) {
  // Team name
  document.getElementById('team-name').textContent = team.name;
  document.title = `${team.name} - College Football Rankings`;

  // Conference badge
  const confBadge = document.getElementById('conference-badge');
  confBadge.textContent = team.conference;
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

  // Preseason Factors
  document.getElementById('recruiting-rank').textContent = team.recruiting_rank === 999 ? 'N/A' : `#${team.recruiting_rank}`;
  document.getElementById('transfer-rank').textContent = team.transfer_rank === 999 ? 'N/A' : `#${team.transfer_rank}`;
  document.getElementById('returning-production').textContent = `${(team.returning_production * 100).toFixed(0)}%`;
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
    // Fetch active season from API
    const activeSeason = await api.getActiveSeason();
    const schedule = await api.getTeamSchedule(teamId, activeSeason);

    if (schedule.games.length === 0) {
      scheduleLoading.classList.add('hidden');
      noSchedule.classList.remove('hidden');
      return;
    }

    // Clear existing rows
    tbody.innerHTML = '';

    // Populate schedule
    schedule.games.forEach(game => {
      const row = createScheduleRow(game);
      tbody.appendChild(row);
    });

    scheduleLoading.classList.add('hidden');
    scheduleContainer.classList.remove('hidden');
  } catch (err) {
    console.error('Error loading schedule:', err);
    scheduleLoading.classList.add('hidden');
    noSchedule.classList.remove('hidden');
  }
}

// Create Schedule Row
function createScheduleRow(game) {
  const row = document.createElement('tr');

  // Check if game has been played
  const isPlayed = game.is_played && game.score;

  // Check if FCS game (excluded from rankings)
  const isFCS = game.is_fcs || game.excluded_from_rankings;

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
  } else {
    // Future FBS game - grayed out
    oppLink.style.color = 'var(--text-secondary)';
    oppLink.style.fontStyle = 'italic';
    oppCell.appendChild(oppLink);
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
