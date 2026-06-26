// Preseason Rating Simulator (EPIC-032 Story 32.2 / 32.3)

// ---- Constants (official defaults — seeded from API on boot) ----
var OFFICIAL_WEIGHTS = {
  recruiting_scale: 1.0,
  transfer_scale: 1.0,
  returning_scale: 1.0,
  position_scale: 1.0,
  prev_season_weight: 0.35,
  mean_regression: 0.60,
  returning_regression_scale: 0.60,
};

// EPIC-030 keys that map to the saved config (the rest are simulator-only)
var EPIC030_KEYS = ['prev_season_weight', 'mean_regression', 'returning_regression_scale'];

// Track the live server values for the EPIC-030 params
var officialEpic030 = {
  prev_season_weight: OFFICIAL_WEIGHTS.prev_season_weight,
  mean_regression: OFFICIAL_WEIGHTS.mean_regression,
  returning_regression_scale: OFFICIAL_WEIGHTS.returning_regression_scale,
};

var currentWeights = {};
Object.keys(OFFICIAL_WEIGHTS).forEach(function(k) {
  currentWeights[k] = OFFICIAL_WEIGHTS[k];
});

var teamsData = [];      // raw from /api/preseason/components
var showAll = false;
var renderScheduled = false;
var teamsMeta = {};

// ---- Admin mode: Save as Official only visible with ?admin in the URL ----
var isAdminMode = (window.location.search.indexOf('admin') !== -1);

function loadTeamsMeta() {
  return fetch('data/teams-meta.json')
    .then(function(resp) {
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    })
    .then(function(data) {
      teamsMeta = data || {};
    })
    .catch(function(err) {
      console.warn('Could not load teams metadata:', err.message);
    });
}

function stripeName(name) {
  var meta = teamsMeta[name] || {};
  return meta.primary || 'var(--accent)';
}

// ---- Boot ----
document.addEventListener('DOMContentLoaded', function() {
  var baseUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? window.location.protocol + '//' + window.location.host + '/api'
    : '/api';

  Promise.all([
    loadComponents(baseUrl),
    loadOfficialWeights(baseUrl),
    loadTeamsMeta(),
  ]).then(function() {
    initSliders();
    checkForChanges();
    render();
  });
});

// ---- Data fetch ----
function loadComponents(baseUrl) {
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

function loadOfficialWeights(baseUrl) {
  return fetch(baseUrl + '/admin/preseason-weights')
    .then(function(resp) {
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    })
    .then(function(data) {
      // API field names → JS key names
      var mapping = {
        previous_season_weight:    'prev_season_weight',
        mean_regression_factor:    'mean_regression',
        returning_regression_scale: 'returning_regression_scale',
      };
      Object.keys(mapping).forEach(function(apiKey) {
        var jsKey = mapping[apiKey];
        if (data[apiKey] != null) {
          OFFICIAL_WEIGHTS[jsKey] = data[apiKey];
          officialEpic030[jsKey]  = data[apiKey];
          currentWeights[jsKey]   = data[apiKey];
        }
      });
    })
    .catch(function(err) {
      // Non-fatal: fall back to hardcoded JS defaults
      console.warn('Could not load official preseason weights:', err.message);
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

  // Compute official ranks (by sorting teamsData by current_rating descending)
  var officialSorted = teamsData.slice().sort(function(a, b) {
    return b.current_rating - a.current_rating;
  });
  var officialRanks = {};
  officialSorted.forEach(function(t, idx) {
    officialRanks[t.team_id] = idx + 1;
  });

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
    if (Math.abs(delta) < 0.005) {
      deltaStr = '—';
      deltaClass = 'delta-neutral';
    } else if (delta > 0) {
      deltaStr = '+' + delta.toFixed(2);
      deltaClass = 'delta-positive';
    } else {
      deltaStr = delta.toFixed(2);
      deltaClass = 'delta-negative';
    }

    // Compute change (CHG) in rank compared to official
    var offRank = officialRanks[team.team_id];
    var chg = offRank - rank;
    var chgStr = '';
    var chgClass = '';
    if (chg > 0) {
      chgStr = '▲' + chg;
      chgClass = 'chg-up';
    } else if (chg < 0) {
      chgStr = '▼' + Math.abs(chg);
      chgClass = 'chg-down';
    } else {
      chgStr = '—';
      chgClass = 'chg-none';
    }

    var confBadge = '';
    if (team.conference) {
      confBadge = '<span class="' + confClass(team.conference) + '">' +
        escapeHtml(team.conference) + '</span>';
    }

    var rowId = 'row-' + team.team_id;
    var breakdownId = 'breakdown-' + team.team_id;

    // Bold simulated ranks for top 4 using inline accent style
    var rankStyle = rank <= 4 ? 'font-weight: 700; color: var(--accent);' : '';

    rows += '<div class="sim-grid-row" id="' + rowId + '" onclick="toggleBreakdown(' + team.team_id + ')">' +
      '<div class="c-rk"><span class="' + rankClass(rank) + '" style="' + rankStyle + '">' + rank + '</span></div>' +
      '<div class="c-chg ' + chgClass + '">' + chgStr + '</div>' +
      '<div class="c-team">' +
        '<span class="c-stripe" style="background:' + stripeName(team.team_name) + '"></span>' +
        '<div class="team-info-block">' +
          '<span class="team-name">' + escapeHtml(team.team_name) + '</span>' +
          '<span class="team-record">' + team.wins + '-' + team.losses + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="c-conf">' + confBadge + '</div>' +
      '<div class="c-simrtg" style="color: var(--accent); font-weight: 700;">' + simRating.toFixed(2) + '</div>' +
      '<div class="c-offrtg">' + team.current_rating.toFixed(2) + '</div>' +
      '<div class="c-delta ' + deltaClass + '">' + deltaStr + '</div>' +
      '</div>' +
      '<div id="' + breakdownId + '" class="sim-grid-details hidden">' +
        '<div id="breakdown-content-' + team.team_id + '"></div>' +
      '</div>';
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
function toggleBreakdown(teamId) {
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
        content.innerHTML = '<div style="margin-bottom:0.4rem;font-size:0.8rem;color:var(--fg2);">' +
          'Component breakdown (bonuses above base ' + team.base.toFixed(0) + '):</div>' +
          buildBreakdownBar(comps) +
          '<div class="breakdown-details-grid">' +
          '<span>Recruiting: <strong>+' + comps.recruiting.toFixed(2) + '</strong></span>' +
          '<span>Transfer: <strong>+' + comps.transfer.toFixed(2) + '</strong></span>' +
          '<span>Returning: <strong>+' + comps.returning.toFixed(2) + '</strong></span>' +
          '<span>Position: <strong>+' + comps.position.toFixed(2) + '</strong></span>' +
          (currentWeights.prev_season_weight > 0 && team.prev_season_elo != null
            ? '<span>Prev Season blend: <strong>' + (comps.prev_season >= 0 ? '+' : '') + comps.prev_season.toFixed(2) + '</strong></span>'
            : '<span style="color:var(--fg3);">No prev season data</span>') +
          '</div>';
      }
    }
    row.classList.remove('hidden');
  } else {
    row.classList.add('hidden');
  }
}

// ---- Show All toggle ----
function toggleShowAll() {
  showAll = !showAll;
  render();
}

// ---- Save as Official (Story 32.3) ----
function checkForChanges() {
  if (!isAdminMode) return;   // button stays hidden for public visitors
  var changed = EPIC030_KEYS.some(function(k) {
    return Math.abs(currentWeights[k] - officialEpic030[k]) > 0.001;
  });
  var btn = document.getElementById('save-official-btn');
  if (btn) {
    btn.classList.toggle('hidden', !changed);
  }
}

function getAdminKey() {
  var key = sessionStorage.getItem('admin_key');
  if (!key) {
    key = window.prompt('Enter admin key:');
    if (key) sessionStorage.setItem('admin_key', key);
  }
  return key || '';
}

function saveAsOfficial() {
  var baseUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? window.location.protocol + '//' + window.location.host + '/api'
    : '/api';

  var adminKey = getAdminKey();
  if (!adminKey) return;

  var payload = {
    previous_season_weight:    currentWeights.prev_season_weight,
    mean_regression_factor:    currentWeights.mean_regression,
    returning_regression_scale: currentWeights.returning_regression_scale,
  };

  var btn = document.getElementById('save-official-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

  fetch(baseUrl + '/admin/preseason-weights', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Key': adminKey,
    },
    body: JSON.stringify(payload),
  })
    .then(function(resp) {
      if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.detail || 'HTTP ' + resp.status); });
      return resp.json();
    })
    .then(function() {
      // Sync official values to current
      EPIC030_KEYS.forEach(function(k) {
        OFFICIAL_WEIGHTS[k] = currentWeights[k];
        officialEpic030[k]  = currentWeights[k];
      });
      if (btn) { btn.disabled = false; btn.textContent = '✓ Saved'; btn.classList.add('hidden'); }
      showSaveNotice(true);
    })
    .catch(function(err) {
      if (btn) { btn.disabled = false; btn.textContent = 'Save as Official'; }
      // If the key was wrong, clear it so the next attempt prompts again
      if (err.message && err.message.indexOf('403') !== -1) {
        sessionStorage.removeItem('admin_key');
      }
      showSaveNotice(false, err.message);
    });
}

function showSaveNotice(success, errMsg) {
  var el = document.getElementById('save-notice');
  if (!el) return;
  el.className = 'save-notice ' + (success ? 'save-notice-success' : 'save-notice-error');
  el.innerHTML = success
    ? '<strong>Weights saved.</strong> Re-run preseason initialization to apply these values to the live rankings.'
    : '<strong>Save failed:</strong> ' + escapeHtml(errMsg || 'Unknown error');
  el.classList.remove('hidden');
  if (success) {
    // Auto-hide after 8 seconds
    setTimeout(function() { el.classList.add('hidden'); }, 8000);
  }
}

function updateSliderTrack(key) {
  var input = document.getElementById(key);
  if (!input) return;
  var min = parseFloat(input.min) || 0;
  var max = parseFloat(input.max) || 1;
  var val = parseFloat(input.value) || 0;
  var pct = ((val - min) / (max - min)) * 100;
  input.style.background = 'linear-gradient(to right, var(--accent) ' + pct + '%, var(--line) ' + pct + '%)';
}

// ---- Sliders ----
function initSliders() {
  // Seed slider positions to match whatever OFFICIAL_WEIGHTS now holds
  // (may have been updated by loadOfficialWeights before initSliders runs)
  Object.keys(OFFICIAL_WEIGHTS).forEach(function(key) {
    var input = document.getElementById(key);
    if (input) input.value = currentWeights[key];
    var valEl = document.getElementById('val-' + key);
    if (valEl) {
      valEl.textContent = currentWeights[key].toFixed(2);
    }
    updateSliderTrack(key);
  });
}

function onSliderChange(key, value) {
  currentWeights[key] = parseFloat(value);
  var valEl = document.getElementById('val-' + key);
  if (valEl) {
    valEl.textContent = parseFloat(value).toFixed(2);
  }
  updateSliderTrack(key);
  checkForChanges();
  scheduleRender();
}

function resetSlider(key) {
  var defaultVal = OFFICIAL_WEIGHTS[key];
  currentWeights[key] = defaultVal;

  var input = document.getElementById(key);
  if (input) input.value = defaultVal;

  var valEl = document.getElementById('val-' + key);
  if (valEl) {
    valEl.textContent = defaultVal.toFixed(2);
  }
  updateSliderTrack(key);
  checkForChanges();
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
