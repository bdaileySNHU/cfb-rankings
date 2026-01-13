/**
 * Prediction Accuracy Comparison Page
 * EPIC-010: AP Poll Prediction Comparison
 */

let comparisonChart = null;
let activeSeason = null;
let currentSeason = null;

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadSeasons();
    setupEventListeners();
    await loadComparisonData(currentSeason);
  } catch (error) {
    console.error('Error loading comparison page:', error);
    showError('Failed to load comparison data. Please try again later.');
  }
});

/**
 * Load available seasons and populate selector
 */
async function loadSeasons() {
  try {
    const seasons = await api.getSeasons();
    activeSeason = await api.getActiveSeason();
    currentSeason = activeSeason;  // Default to active season

    populateSeasonSelector(seasons);
  } catch (error) {
    console.error('Error loading seasons:', error);
    // Continue with default season
  }
}

/**
 * Populate season selector dropdown
 */
function populateSeasonSelector(seasons) {
  const seasonSelect = document.getElementById('season-select');
  seasonSelect.innerHTML = '';

  // Sort seasons (newest first)
  seasons.sort((a, b) => b.year - a.year);

  seasons.forEach(season => {
    const option = document.createElement('option');
    option.value = season.year;
    option.textContent = `${season.year} Season${season.is_active ? ' (Current)' : ''}`;
    if (season.year === activeSeason) {
      option.selected = true;
    }
    seasonSelect.appendChild(option);
  });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  const seasonSelect = document.getElementById('season-select');
  if (seasonSelect) {
    seasonSelect.addEventListener('change', async (e) => {
      const selectedSeason = e.target.value ? parseInt(e.target.value) : activeSeason;
      currentSeason = selectedSeason;

      // Show loading state
      const loading = document.getElementById('loading');
      const content = document.getElementById('comparison-content');
      content.classList.add('hidden');
      loading.classList.remove('hidden');
      loading.innerHTML = `
        <div class="loading">
          <div class="spinner"></div>
          <span>Loading comparison data for ${currentSeason} season...</span>
        </div>
      `;

      try {
        await loadComparisonData(currentSeason);
      } catch (error) {
        console.error('Error loading season data:', error);
        showError(`Failed to load comparison data for ${currentSeason} season. Please try again.`);
      }
    });
  }
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
  const advantageColor = advantage >= 0 ? '#10b981' : '#ef4444';

  const advantageEl = document.getElementById('elo-advantage');
  advantageEl.textContent = `${advantageSign}${advantage}%`;
  advantageEl.style.color = advantageColor;

  document.getElementById('games-compared').textContent =
    `${comparison.total_games_compared} games compared`;
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
  const ctx = document.getElementById('accuracy-chart');

  // Destroy existing chart if present
  if (comparisonChart) {
    comparisonChart.destroy();
  }

  // Prepare data
  // EPIC-COMPARISON-BOWL-PLAYOFF: Use descriptive labels for postseason weeks
  const weeks = comparison.by_week.map(w => getWeekLabel(w.week, w.game_type, w.postseason_name));
  const eloData = comparison.by_week.map(w => (w.elo_accuracy * 100).toFixed(1));
  const apData = comparison.by_week.map(w => (w.ap_accuracy * 100).toFixed(1));

  // EPIC-COMPARISON-BOWL-PLAYOFF: Find index where postseason starts (week 16+)
  const postseasonStartIndex = comparison.by_week.findIndex(w => w.week >= 16);
  const hasPostseason = postseasonStartIndex !== -1;

  // Create chart
  comparisonChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: weeks,
      datasets: [
        {
          label: 'ELO System',
          data: eloData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        },
        {
          label: 'AP Poll',
          data: apData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        }
      ]
    },
    // EPIC-COMPARISON-BOWL-PLAYOFF: Add custom plugin for postseason visual separator
    plugins: hasPostseason ? [{
      id: 'postseasonSeparator',
      afterDraw: (chart) => {
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const yAxis = chart.scales.y;

        // Draw vertical line after week 15 (before postseason)
        if (postseasonStartIndex > 0) {
          const x = xAxis.getPixelForValue(postseasonStartIndex - 0.5);

          ctx.save();
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);
          ctx.moveTo(x, yAxis.top);
          ctx.lineTo(x, yAxis.bottom);
          ctx.stroke();
          ctx.restore();

          // Add "Postseason" label
          ctx.save();
          ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
          ctx.font = '12px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('← Regular Season | Postseason →', x, yAxis.top - 5);
          ctx.restore();
        }
      }
    }] : [],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: {
              size: 14
            },
            padding: 20
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y}%`;
            },
            // EPIC-COMPARISON-BOWL-PLAYOFF: Show game count in tooltip
            afterLabel: function(context) {
              const weekData = comparison.by_week[context.dataIndex];
              if (weekData && weekData.games) {
                return `(${weekData.games} game${weekData.games !== 1 ? 's' : ''})`;
              }
              return '';
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: function(value) {
              return value + '%';
            }
          },
          title: {
            display: true,
            text: 'Prediction Accuracy (%)',
            font: {
              size: 14
            }
          }
        },
        x: {
          title: {
            display: true,
            text: 'Week',
            font: {
              size: 14
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  });
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
    // Determine result styling
    let resultBadge;
    if (game.elo_correct && !game.ap_correct) {
      resultBadge = '<span class="prediction-correct">ELO ✓</span>';
    } else if (!game.elo_correct && game.ap_correct) {
      resultBadge = '<span class="prediction-incorrect">AP ✓</span>';
    } else {
      resultBadge = '<span style="color: var(--text-secondary);">Both Wrong</span>';
    }

    // EPIC-COMPARISON-BOWL-PLAYOFF: Use descriptive week labels for postseason
    const weekLabel = getWeekLabel(game.week, game.game_type, game.postseason_name);

    return `
      <tr>
        <td>${weekLabel}</td>
        <td><strong>${game.matchup}</strong></td>
        <td>${game.elo_predicted}</td>
        <td>${game.ap_predicted}</td>
        <td><strong>${game.actual_winner}</strong></td>
        <td>${resultBadge}</td>
      </tr>
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
