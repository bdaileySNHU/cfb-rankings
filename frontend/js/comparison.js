/**
 * Prediction Accuracy Comparison Page
 * EPIC-010: AP Poll Prediction Comparison
 */

let comparisonChart = null;
let activeSeason = null;
let currentSeason = null;

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();

  window.seasonModule.onSeasonReady(async (selected, active) => {
    currentSeason = selected;
    activeSeason = active;
    try {
      await loadComparisonData(currentSeason);
    } catch (error) {
      console.error('Error loading comparison page:', error);
      showError('Failed to load comparison data. Please try again later.');
    }
  });

  document.addEventListener('seasonchange', async (e) => {
    currentSeason = e.detail.season;
    try {
      await loadComparisonData(currentSeason);
    } catch (error) {
      showError('Failed to load comparison data. Please try again later.');
    }
  });
});

function setupEventListeners() {
  // Season changes handled globally via seasonchange event in DOMContentLoaded
}

/**
 * Load and display all comparison data
 */
async function loadComparisonData(season = null) {
  const loading = document.getElementById('loading');
  const content = document.getElementById('comparison-content');

  try {
    // Use provided season or default to active season
    const selectedSeason = season || activeSeason || await api.getActiveSeason();

    // Fetch comparison data
    const comparison = await api.getPredictionComparison(selectedSeason);

    // Check if we have comparison data (empty state)
    if (comparison.total_games_compared === 0) {
      const message = comparison.message || "No comparison data available for this season yet.";
      loading.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 3rem 2rem;">
          <p style="font-size: 1.3rem; margin-bottom: 1rem; color: var(--text-primary);">📊 No Comparison Data Yet</p>
          <p style="color: var(--text-secondary); margin-bottom: 0.5rem;">${message}</p>
          <p style="color: var(--text-secondary); font-size: 0.9rem;">
            AP Poll rankings will be available once games with rankings are imported.
          </p>
        </div>
      `;
      return;
    }

    // Hide loading, show content
    loading.classList.add('hidden');
    content.classList.remove('hidden');

    // Display all sections
    displayHeroStats(comparison);
    displayBreakdownStats(comparison);
    displayPostseasonStats(comparison);  // EPIC-COMPARISON-BOWL-PLAYOFF
    displayAccuracyChart(comparison);
    displayDisagreements(comparison);

  } catch (error) {
    console.error('Error in loadComparisonData:', error);
    loading.innerHTML = `
      <div style="text-align: center; color: var(--error-color); padding: 2rem;">
        <p style="font-size: 1.2rem; margin-bottom: 1rem;">⚠️ Error Loading Data</p>
        <p style="color: var(--text-secondary);">${error.message}</p>
        <p style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem;">
          This feature requires AP Poll data to be imported. Data will be available once games are imported with AP rankings.
        </p>
      </div>
    `;
  }
}

/**
 * Display hero stats (overall accuracy and comparison)
 */
function displayHeroStats(comparison) {
  // Overall ELO Accuracy (all games)
  const overallEloAccuracy = (comparison.overall_elo_accuracy * 100).toFixed(1);
  document.getElementById('overall-elo-accuracy-pct').textContent = `${overallEloAccuracy}%`;
  document.getElementById('overall-elo-correct-count').textContent =
    `${comparison.overall_elo_correct} of ${comparison.overall_elo_total} games predicted correctly`;

  // ELO Accuracy (vs AP Poll subset)
  const eloAccuracy = (comparison.elo_accuracy * 100).toFixed(1);
  document.getElementById('elo-accuracy-pct').textContent = `${eloAccuracy}%`;
  document.getElementById('elo-correct-count').textContent =
    `${comparison.elo_correct} of ${comparison.total_games_compared} correct`;

  // AP Accuracy
  const apAccuracy = (comparison.ap_accuracy * 100).toFixed(1);
  document.getElementById('ap-accuracy-pct').textContent = `${apAccuracy}%`;
  document.getElementById('ap-correct-count').textContent =
    `${comparison.ap_correct} of ${comparison.total_games_compared} correct`;

  // ELO Advantage
  const advantage = (comparison.elo_advantage * 100).toFixed(1);
  const advantageSign = advantage >= 0 ? '+' : '';
  const advantageColor = advantage >= 0 ? 'var(--pos)' : 'var(--neg)';

  const advantageEl = document.getElementById('elo-advantage');
  advantageEl.textContent = `${advantageSign}${advantage}%`;
  advantageEl.className = 'comp-value ' + (advantage >= 0 ? 'delta-pos' : 'delta-neg');

  const advSub = document.getElementById('elo-advantage-sub');
  if (advSub) {
    advSub.textContent = advantage >= 0 ? 'ELO leads AP' : 'ELO trails AP';
  }

  document.getElementById('games-compared').textContent =
    `${comparison.total_games_compared} games compared`;

  // Set mini progress bar widths & markers
  const fillEl = document.getElementById('mini-bar-fill');
  const markerEl = document.getElementById('mini-bar-marker');
  if (fillEl && markerEl) {
    fillEl.style.width = `${eloAccuracy}%`;
    markerEl.style.left = `${apAccuracy}%`;
  }
}

/**
 * Display breakdown stats
 */
function displayBreakdownStats(comparison) {
  document.getElementById('both-correct').textContent = comparison.both_correct;
  document.getElementById('elo-only-correct').textContent = comparison.elo_only_correct;
  document.getElementById('ap-only-correct').textContent = comparison.ap_only_correct;
  document.getElementById('both-wrong').textContent = comparison.both_wrong;
}

/**
 * Display postseason vs regular season statistics
 * EPIC-COMPARISON-BOWL-PLAYOFF: Story 3
 */
function displayPostseasonStats(comparison) {
  const postseasonCard = document.getElementById('postseason-stats-card');
  const postseasonEmptyState = document.getElementById('postseason-empty-state');

  // Check if we have postseason data (any week >= 16 in by_week array)
  const hasPostseasonData = comparison.by_week && comparison.by_week.some(w => w.week >= 16);

  // Show the card
  postseasonCard.style.display = 'block';

  if (!hasPostseasonData) {
    // Show empty state if no postseason data
    postseasonEmptyState.style.display = 'block';
    // Hide postseason stats section
    document.querySelector('#postseason-stats-card > div:nth-child(3)').style.display = 'none';
    return;
  }

  // Hide empty state and show postseason stats
  postseasonEmptyState.style.display = 'none';
  document.querySelector('#postseason-stats-card > div:nth-child(3)').style.display = 'block';

  // Calculate game counts for regular season and postseason
  const regularSeasonGames = comparison.by_week
    .filter(w => w.week <= 15)
    .reduce((sum, w) => sum + w.games, 0);
  const postseasonGames = comparison.by_week
    .filter(w => w.week >= 16)
    .reduce((sum, w) => sum + w.games, 0);

  // Regular Season Stats
  const regularSeasonEloAccuracy = (comparison.regular_season_elo_accuracy * 100).toFixed(1);
  const regularSeasonApAccuracy = (comparison.regular_season_ap_accuracy * 100).toFixed(1);

  document.getElementById('regular-season-elo-accuracy').textContent = `${regularSeasonEloAccuracy}%`;
  document.getElementById('regular-season-ap-accuracy').textContent = `${regularSeasonApAccuracy}%`;
  document.getElementById('regular-season-elo-subtext').textContent = `${regularSeasonGames} game${regularSeasonGames !== 1 ? 's' : ''}`;
  document.getElementById('regular-season-ap-subtext').textContent = `${regularSeasonGames} game${regularSeasonGames !== 1 ? 's' : ''}`;

  // Postseason Stats
  const postseasonEloAccuracy = (comparison.postseason_elo_accuracy * 100).toFixed(1);
  const postseasonApAccuracy = (comparison.postseason_ap_accuracy * 100).toFixed(1);

  document.getElementById('postseason-elo-accuracy').textContent = `${postseasonEloAccuracy}%`;
  document.getElementById('postseason-ap-accuracy').textContent = `${postseasonApAccuracy}%`;
  document.getElementById('postseason-elo-subtext').textContent = `${postseasonGames} game${postseasonGames !== 1 ? 's' : ''}`;
  document.getElementById('postseason-ap-subtext').textContent = `${postseasonGames} game${postseasonGames !== 1 ? 's' : ''}`;
}

/**
 * Get descriptive week label for chart
 * EPIC-COMPARISON-BOWL-PLAYOFF: Maps week numbers to user-friendly labels
 *
 * @param {number} week - Week number (1-20)
 * @param {string|null} gameType - Game type ('bowl', 'playoff', 'conference_championship', or null)
 * @param {string|null} postseasonName - Full postseason name (e.g., "CFP Semifinal - Rose Bowl")
 * @returns {string} Formatted week label
 */
function getWeekLabel(week, gameType, postseasonName) {
  // Regular season weeks (1-15)
  if (week <= 15) {
    return `Week ${week}`;
  }

  // Postseason weeks (16-20): Use postseason_name if available
  if (postseasonName) {
    // Abbreviate common terms for chart readability
    return postseasonName
      .replace('College Football Playoff', 'CFP')
      .replace('Conference Championship', 'Conf. Champ.');
  }

  // Fallback generic labels based on week number
  const postseasonLabels = {
    16: 'Bowl Week 1',
    17: 'Bowl Week 2',
    18: 'CFP Semifinals',
    19: 'Conf. Championships',
    20: 'CFP Championship'
  };

  return postseasonLabels[week] || `Week ${week}`;
}

/**
 * Display accuracy over time chart
 */
function displayAccuracyChart(comparison) {
  const container = document.getElementById('accuracy-chart-container');
  if (!container) return;

  const data = comparison.by_week || [];
  if (!data.length) {
    container.innerHTML = '<div style="color:var(--fg3);text-align:center;padding:2rem;">No chart data available.</div>';
    return;
  }

  // Dimensions
  const W = 1000;
  const H = 250;
  const padL = 48;
  const padR = 14;
  const padT = 14;
  const padB = 14;
  const innerW = W - padL - padR; // 938
  const innerH = H - padT - padB; // 222

  const baseY = padT + innerH; // 236

  // Scales
  const getX = (index) => padL + (index / (data.length - 1)) * innerW;
  const getY = (val) => baseY - (val / 100) * innerH;

  // Gridlines: 5 horizontals at 0, 25, 50, 75, 100%
  let gridSvg = '';
  const gridTicks = [0, 25, 50, 75, 100];
  gridTicks.forEach(tick => {
    const y = getY(tick);
    gridSvg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="var(--grid)" stroke-width="1" />`;
    gridSvg += `<text x="${padL - 6}" y="${y}" text-anchor="end" dominant-baseline="central" fill="var(--fg3)" font-family="var(--font-mono)" font-size="10">${tick}%</text>`;
  });

  // Plot lines and points
  let eloPoints = [];
  let apPoints = [];
  data.forEach((w, idx) => {
    const x = getX(idx);
    const yElo = getY(w.elo_accuracy * 100);
    const yAp = getY(w.ap_accuracy * 100);
    eloPoints.push({ x, y: yElo, val: (w.elo_accuracy * 100).toFixed(1) });
    apPoints.push({ x, y: yAp, val: (w.ap_accuracy * 100).toFixed(1) });
  });

  const eloPath = eloPoints.map(p => `${p.x},${p.y}`).join(' ');
  const apPath = apPoints.map(p => `${p.x},${p.y}`).join(' ');

  const eloAreaPath = `${padL},${baseY} ${eloPath} ${eloPoints[eloPoints.length - 1].x},${baseY}`;
  const apAreaPath = `${padL},${baseY} ${apPath} ${apPoints[apPoints.length - 1].x},${baseY}`;

  // Dots
  let eloDots = '';
  let apDots = '';
  eloPoints.forEach(p => {
    eloDots += `<circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--bg)" stroke="var(--accent)" stroke-width="2"><title>ELO: ${p.val}%</title></circle>`;
  });
  apPoints.forEach(p => {
    apDots += `<circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--bg)" stroke="#7c9fe6" stroke-width="2"><title>AP: ${p.val}%</title></circle>`;
  });

  // X labels
  let xLabelsSvg = '';
  data.forEach((w, idx) => {
    const x = getX(idx);
    const y = baseY + 12;
    const label = getWeekLabel(w.week, w.game_type, w.postseason_name);
    xLabelsSvg += `<text x="${x}" y="${y}" text-anchor="middle" fill="var(--fg3)" font-family="var(--font-mono)" font-size="10">${label}</text>`;
  });

  // Draw vertical line if postseason starts (week 16)
  let verticalLine = '';
  const postseasonIndex = data.findIndex(w => w.week >= 16);
  if (postseasonIndex !== -1) {
    const x = getX(postseasonIndex - 0.5);
    verticalLine = `<line x1="${x}" y1="${padT}" x2="${x}" y2="${baseY}" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="4,4" />
      <text x="${x}" y="${padT + 12}" text-anchor="middle" fill="var(--fg3)" font-family="var(--font-sans)" font-size="11">Postseason →</text>`;
  }

  container.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" width="100%" height="250" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="elo-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.22" />
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0" />
        </linearGradient>
        <linearGradient id="ap-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#7c9fe6" stop-opacity="0.16" />
          <stop offset="100%" stop-color="#7c9fe6" stop-opacity="0" />
        </linearGradient>
      </defs>
      ${gridSvg}
      ${verticalLine}
      <polygon points="${eloAreaPath}" fill="url(#elo-grad)" />
      <polygon points="${apAreaPath}" fill="url(#ap-grad)" />
      <polyline points="${eloPath}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
      <polyline points="${apPath}" fill="none" stroke="#7c9fe6" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
      ${eloDots}
      ${apDots}
      ${xLabelsSvg}
    </svg>
  `;
}

/**
 * Display disagreement games table
 */
function displayDisagreements(comparison) {
  const tbody = document.getElementById('disagreements-tbody');
  const noDisagreements = document.getElementById('no-disagreements');
  const container = document.getElementById('disagreements-container');

  if (comparison.disagreements.length === 0) {
    noDisagreements.classList.remove('hidden');
    container.classList.add('hidden');
    return;
  }

  noDisagreements.classList.add('hidden');
  container.classList.remove('hidden');

  tbody.innerHTML = comparison.disagreements.map(game => {
    let resultBadge;
    if (game.elo_correct && !game.ap_correct) {
      resultBadge = '<span class="res-badge elo-win">ELO ✓</span>';
    } else if (!game.elo_correct && game.ap_correct) {
      resultBadge = '<span class="res-badge ap-win">AP ✓</span>';
    } else {
      resultBadge = '<span class="res-badge" style="color: var(--fg3); background: var(--panel2);">Both Wrong</span>';
    }

    const weekLabel = getWeekLabel(game.week, game.game_type, game.postseason_name);

    return `
      <div class="disagreed-row">
        <div>${weekLabel}</div>
        <div class="matchup-cell">${game.matchup}</div>
        <div>${game.elo_predicted}</div>
        <div>${game.ap_predicted}</div>
        <div class="winner-cell">${game.actual_winner}</div>
        <div style="display: flex; justify-content: center; align-items: center;">${resultBadge}</div>
      </div>
    `;
  }).join('');
}

/**
 * Show error message
 */
function showError(message) {
  const loading = document.getElementById('loading');
  loading.innerHTML = `
    <div style="text-align: center; color: var(--error-color); padding: 2rem;">
      <p style="font-size: 1.2rem; margin-bottom: 1rem;">⚠️ Error</p>
      <p style="color: var(--text-secondary);">${message}</p>
    </div>
  `;
}
