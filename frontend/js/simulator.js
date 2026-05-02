// Preseason Rating Simulator (EPIC-032 Story 32.2)

// ---- Constants (official defaults) ----
var OFFICIAL_WEIGHTS = {
  recruiting_scale: 1.0,
  transfer_scale: 1.0,
  returning_scale: 1.0,
  position_scale: 1.0,
  prev_season_weight: 0.35,
  mean_regression: 0.60,
  returning_regression_scale: 0.60,
};

var currentWeights = {};
Object.keys(OFFICIAL_WEIGHTS).forEach(function(k) {
  currentWeights[k] = OFFICIAL_WEIGHTS[k];
});

var teamsData = [];      // raw from /api/preseason/components
var showAll = false;
var renderScheduled = false;

// ---- Boot ----
document.addEventListener('DOMContentLoaded', function() {
  loadComponents().then(function() {
    initSliders();
    render();
  });
});

// ---- Data fetch ----
function loadComponents() {
  var baseUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : '/api';

  return fetch(baseUrl + '/preseason/components')
    .then(function(resp) {
      if (!resp.ok) {
        throw new Error('HTTP ' + resp.status);
      }
      return resp.json();
    })
    .then(function(data) {
      teamsData = data || [];
      document.getElementById('sim-loading').classList.add('hidden');
      document.getElementById('sim-table-container').classList.remove('hidden');
      document.getElementById('sim-status').textContent =
        teamsData.length + ' teams loaded';
    })
    .catch(function(err) {
      console.error('Failed to load preseason components:', err);
      document.getElementById('sim-loading').classList.add('hidden');
      document.getElementById('sim-error').classList.remove('hidden');
      document.getElementById('sim-error-message').textContent =
        ' ' + err.message + '. Make sure the API server is running.';
    });
}

// ---- Simulation core ----
function simulate(team, w) {
  var base_formula =
    team.base +
    team.recruiting_bonus        * w.recruiting_scale +
    team.transfer_bonus          * w.transfer_scale +
    team.returning_bonus         * w.returning_scale +
    team.position_strength_bonus * w.position_scale;

  if (w.prev_season_weight > 0 && team.prev_season_elo != null) {
    var dynamic_reg = w.mean_regression +
      (team.returning_production - 0.5) * w.returning_regression_scale;
    var regression = Math.max(0.30, Math.min(0.85, dynamic_reg));
    var prev_regressed = 1500 + (team.prev_season_elo - 1500) * regression;
    return (prev_regressed * w.prev_season_weight) +
           (base_formula  * (1 - w.prev_season_weight));
  }
  return base_formula;
}

// ---- Breakdown component contributions ----
function getComponents(team, w) {
  var recruiting  = team.recruiting_bonus        * w.recruiting_scale;
  var transfer    = team.transfer_bonus          * w.transfer_scale;
  var returning   = team.returning_bonus         * w.returning_scale;
  var position    = team.position_strength_bonus * w.position_scale;

  var prev_contrib = 0;
  if (w.prev_season_weight > 0 && team.prev_season_elo != null) {
    var base_formula =
      team.base + recruiting + transfer + returning + position;
    var dynamic_reg = w.mean_regression +
      (team.returning_production - 0.5) * w.returning_regression_scale;
    var regression = Math.max(0.30, Math.min(0.85, dynamic_reg));
    var prev_regressed = 1500 + (team.prev_season_elo - 1500) * regression;
    // Contribution of prev-season blend vs base formula
    prev_contrib = (prev_regressed - base_formula) * w.prev_season_weight;
  }

  return {
    recruiting:  recruiting,
    transfer:    transfer,
    returning:   returning,
    position:    position,
    prev_season: prev_contrib,
  };
}

// ---- Rank badge class ----
function rankClass(rank) {
  if (rank <= 5)  return 'rank-badge top-5';
  if (rank <= 10) return 'rank-badge top-10';
  if (rank <= 25) return 'rank-badge top-25';
  return 'rank-badge';
}

// ---- Conference badge class ----
function confClass(conf) {
  if (!conf) return '';
  var c = conf.toUpperCase();
  if (c === 'P5') return 'conference-badge p5';
  if (c === 'G5') return 'conference-badge g5';
  if (c === 'FCS') return 'conference-badge fcs';
  return 'conference-badge';
}

// ---- Build breakdown bar HTML ----
function buildBreakdownBar(comps) {
  var vals = [
    { key: 'seg-recruiting',  label: 'Recruiting',   val: comps.recruiting },
    { key: 'seg-transfer',    label: 'Transfer',     val: comps.transfer },
    { key: 'seg-returning',   label: 'Returning',    val: comps.returning },
    { key: 'seg-position',    label: 'Position',     val: comps.position },
    { key: 'seg-prev-season', label: 'Prev Season',  val: comps.prev_season },
  ];

  var positiveVals = vals.filter(function(v) { return v.val > 0; });
  var total = positiveVals.reduce(function(sum, v) { return sum + v.val; }, 0);

  if (total <= 0) {
    return '<span style="color:var(--text-secondary);font-size:0.85rem;">No positive bonuses</span>';
  }

  var segments = '';
  vals.forEach(function(v) {
    if (v.val <= 0) return;
    var pct = (v.val / total * 100).toFixed(1);
    segments += '<div class="breakdown-segment ' + v.key + '" style="width:' + pct + '%"' +
      ' title="' + v.label + ': +' + v.val.toFixed(1) + '">' +
      v.label + ' +' + v.val.toFixed(1) +
      '</div>';
  });

  return '<div class="breakdown-bar">' + segments + '</div>';
}

// ---- Render ----
function render() {
  renderScheduled = false;

  if (teamsData.length === 0) return;

  // Compute simulated ratings
  var simulated = teamsData.map(function(team) {
    return {
      team: team,
      sim_rating: simulate(team, currentWeights),
    };
  });

  // Sort descending
  simulated.sort(function(a, b) { return b.sim_rating - a.sim_rating; });

  // Slice if not showing all
  var display = showAll ? simulated : simulated.slice(0, 25);

  var tbody = document.getElementById('sim-tbody');
  if (!tbody) return;

  var rows = '';
  display.forEach(function(item, idx) {
    var rank = idx + 1;
    var team = item.team;
    var simRating = item.sim_rating;
    var delta = simRating - team.current_rating;
    var deltaStr;
    var deltaClass;
    if (Math.abs(delta) < 0.05) {
      deltaStr = '&mdash;';
      deltaClass = 'delta-neutral';
    } else if (delta > 0) {
      deltaStr = '+' + delta.toFixed(1);
      deltaClass = 'delta-positive';
    } else {
      deltaStr = delta.toFixed(1);
      deltaClass = 'delta-negative';
    }

    var confBadge = '';
    if (team.conference) {
      confBadge = '<span class="' + confClass(team.conference) + '">' +
        escapeHtml(team.conference) + '</span>';
    }

    var rowId = 'row-' + team.team_id;
    var breakdownId = 'breakdown-' + team.team_id;

    rows += '<tr id="' + rowId + '">' +
      '<td><span class="' + rankClass(rank) + '">' + rank + '</span></td>' +
      '<td><span class="team-name">' + escapeHtml(team.team_name) + '</span></td>' +
      '<td>' + confBadge + '</td>' +
      '<td><strong>' + simRating.toFixed(1) + '</strong></td>' +
      '<td class="' + deltaClass + '">' + deltaStr + '</td>' +
      '<td><button class="details-btn" onclick="toggleBreakdown(' + team.team_id + ', this)">&#9654; Details</button></td>' +
      '</tr>' +
      '<tr id="' + breakdownId + '" class="breakdown-row hidden">' +
      '<td colspan="6" id="breakdown-content-' + team.team_id + '"></td>' +
      '</tr>';
  });

  tbody.innerHTML = rows;

  // Update show-all button label
  var btn = document.getElementById('show-all-btn');
  if (btn) {
    btn.textContent = showAll
      ? 'Show Top 25'
      : 'Show All Teams (' + simulated.length + ')';
  }
}

function scheduleRender() {
  if (!renderScheduled) {
    renderScheduled = true;
    requestAnimationFrame(render);
  }
}

// ---- Breakdown toggle ----
function toggleBreakdown(teamId, btn) {
  var row = document.getElementById('breakdown-' + teamId);
  if (!row) return;

  if (row.classList.contains('hidden')) {
    // Build content on first open (or refresh on re-open)
    var team = null;
    for (var i = 0; i < teamsData.length; i++) {
      if (teamsData[i].team_id === teamId) {
        team = teamsData[i];
        break;
      }
    }
    if (team) {
      var comps = getComponents(team, currentWeights);
      var content = document.getElementById('breakdown-content-' + teamId);
      if (content) {
        content.innerHTML = '<div style="margin-bottom:0.4rem;font-size:0.8rem;color:var(--text-secondary);">' +
          'Component breakdown (bonuses above base ' + team.base.toFixed(0) + '):</div>' +
          buildBreakdownBar(comps) +
          '<div class="breakdown-details-grid">' +
          '<span>Recruiting: <strong>+' + comps.recruiting.toFixed(1) + '</strong></span>' +
          '<span>Transfer: <strong>+' + comps.transfer.toFixed(1) + '</strong></span>' +
          '<span>Returning: <strong>+' + comps.returning.toFixed(1) + '</strong></span>' +
          '<span>Position: <strong>+' + comps.position.toFixed(1) + '</strong></span>' +
          (currentWeights.prev_season_weight > 0 && team.prev_season_elo != null
            ? '<span>Prev Season blend: <strong>' + (comps.prev_season >= 0 ? '+' : '') + comps.prev_season.toFixed(1) + '</strong></span>'
            : '<span style="color:var(--text-secondary);">No prev season data</span>') +
          '</div>';
      }
    }
    row.classList.remove('hidden');
    btn.innerHTML = '&#9660; Details';
  } else {
    row.classList.add('hidden');
    btn.innerHTML = '&#9654; Details';
  }
}

// ---- Show All toggle ----
function toggleShowAll() {
  showAll = !showAll;
  render();
}

// ---- Sliders ----
function initSliders() {
  // Nothing extra needed — values already set via HTML defaults.
  // This function exists for parity with the spec interface.
}

function onSliderChange(key, value) {
  currentWeights[key] = parseFloat(value);
  var valEl = document.getElementById('val-' + key);
  if (valEl) {
    valEl.textContent = parseFloat(value).toFixed(
      key === 'prev_season_weight' || key === 'mean_regression' || key === 'returning_regression_scale'
        ? 2 : 1
    );
  }
  scheduleRender();
}

function resetSlider(key) {
  var defaultVal = OFFICIAL_WEIGHTS[key];
  currentWeights[key] = defaultVal;

  var input = document.getElementById(key);
  if (input) input.value = defaultVal;

  var valEl = document.getElementById('val-' + key);
  if (valEl) {
    valEl.textContent = defaultVal.toFixed(
      key === 'prev_season_weight' || key === 'mean_regression' || key === 'returning_regression_scale'
        ? 2 : 1
    );
  }
  scheduleRender();
}

function resetAll() {
  Object.keys(OFFICIAL_WEIGHTS).forEach(function(key) {
    resetSlider(key);
  });
}

// ---- Utility ----
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
