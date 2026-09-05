// Ticker board renderer (spec v1.0). Reuses the global `api` (api.js).
// Renders header chrome content, ticker tape, stat ribbon, ratings grid,
// and the in-place team detail view.
(function () {
  'use strict';
  // Heat colors per theme: [r,g,b, alphaMax]. Spec §07.
  var HEAT = {
    off: { dark: [63, 179, 127, 0.28], light: [31, 138, 91, 0.18] },
    def: { dark: [232, 99, 90, 0.28], light: [196, 69, 58, 0.18] },
  };

  var META = {};       // teams-meta.json
  var ENTRIES = [];    // current rankings entries (meta merged)
  var COLLAPSE_AT = 25;
  var boardExpanded = false;
  var activeFilter = 'All'; // active filter state
  var PLAYOFF_DATA = null;  // playoff projection data
  var CURRENT_WEEK = 0;     // current week number

  var clamp = function (v, lo, hi) { return Math.max(lo, Math.min(hi, v)); };
  var isLight = function () { return document.documentElement.getAttribute('data-theme') === 'light'; };

  function metaOf(name) { return META[name] || {}; }
  function abbrName(name) { return metaOf(name).abbr || (name || '???').slice(0, 3).toUpperCase(); }
  // Brand colours are often near-black (8 teams are #000000), so run them
  // through the contrast floor before painting onto the panel.
  function stripeName(name) {
    var c = metaOf(name).primary;
    if (!c) return 'var(--accent)';
    return window.TeamVisuals ? window.TeamVisuals.readable(c) : c;
  }
  function logoImgFor(name, size) {
    return window.TeamVisuals ? window.TeamVisuals.logoImg(metaOf(name), size, name) : '';
  }
  function abbrOf(e) { return abbrName(e.team_name); }
  function stripeOf(e) { return stripeName(e.team_name); }

  function rgb(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
    if (!m) return null;
    var n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  // Colour for `awayName` in a split bar shared with `homeName`. Falls back to
  // the away team's alternate colour when the two brands read as the same, so a
  // red-vs-red matchup stays two team colours instead of one going grey.
  function pairColor(awayName, homeName) {
    var awayMeta = metaOf(awayName);
    var homePrimary = metaOf(homeName).primary;
    if (!window.TeamVisuals || !awayMeta.primary || !homePrimary) return stripeName(awayName);
    return window.TeamVisuals.distinguish(awayMeta, homePrimary);
  }

  // d = rank_change (prevRank - rank). >0 up, <0 down, 0 flat.
  function trendClass(d) { return d > 0 ? 'trend-pos' : d < 0 ? 'trend-neg' : 'trend-flat'; }
  function trendVar(d) { return d > 0 ? '--pos' : d < 0 ? '--neg' : '--fg3'; }
  function deltaText(d) { if (d == null) return '—'; if (d === 0) return '0'; return d > 0 ? '+' + d : String(d); }
  function fmtElo(v) { return Math.round(v).toString(); }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }

  // ── Sparkline (70×22 viewBox, non-scaling stroke). Spec §07. ──
  function sparkline(history, d) {
    var h = (history || []).filter(function (x) { return typeof x === 'number'; });
    if (h.length < 2) return '';
    var min = Math.min.apply(null, h), max = Math.max.apply(null, h);
    var range = max - min || 1;
    var pts = h.map(function (v, i) {
      var x = (i / (h.length - 1)) * 70;
      var y = 2 + (1 - (v - min) / range) * 18;
      return x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
    return '<svg class="tkr-spark" viewBox="0 0 70 22" preserveAspectRatio="none" aria-hidden="true">' +
      '<polyline points="' + pts + '" fill="none" stroke="var(' + trendVar(d) + ')" ' +
      'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>';
  }

  function heatBg(kind, v) {
    if (v == null) return 'transparent';
    var c = HEAT[kind][isLight() ? 'light' : 'dark'];
    var t = kind === 'off' ? clamp((v - 28) / 16, 0, 1) : clamp((v - 14) / 12, 0, 1);
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (t * c[3]).toFixed(3) + ')';
  }

  function paintHeat() {
    document.querySelectorAll('.heat').forEach(function (el) {
      var v = el.dataset.v === '' ? null : parseFloat(el.dataset.v);
      el.style.background = heatBg(el.dataset.kind, v);
    });
  }

  // ── Rows ──
  function rowHTML(e) {
    var d = e.rank_change;
    var sosWarn = e.sos != null && e.sos > 0.62;
    var off = e.off, def = e.def;
    return '<div class="tkr-grid tkr-row" data-id="' + e.team_id + '">' +
      '<div class="c-rk">' + String(e.rank).padStart(2, '0') + '</div>' +
      '<div class="c-team">' +
        (logoImgFor(e.team_name, 24) ||
          '<span class="c-stripe" style="background:' + stripeOf(e) + '"></span>') +
        '<span class="c-name">' + esc(e.team_name) + '</span></div>' +
      '<div class="c-conf">' + esc(TeamVisuals.confLabel(e.conference_name) || e.conference || '') + '</div>' +
      '<div class="c-wl ta-r">' + e.wins + '-' + e.losses + '</div>' +
      '<div class="c-elo ta-r">' + fmtElo(e.elo_rating) + '</div>' +
      '<div class="c-delta ta-r ' + trendClass(d) + '">' + deltaText(d) + '</div>' +
      '<div class="heat ta-r" data-kind="off" data-v="' + (off == null ? '' : off) + '">' + (off == null ? '—' : off) + '</div>' +
      '<div class="heat ta-r" data-kind="def" data-v="' + (def == null ? '' : def) + '">' + (def == null ? '—' : def) + '</div>' +
      '<div class="c-sos ta-r' + (sosWarn ? ' warn' : '') + '">' + (e.sos == null ? '—' : e.sos.toFixed(3)) + '</div>' +
      '<div class="c-odds ta-r">' + fmtPct(e.bid_pct) + '</div>' +
      '<div class="c-odds ta-r">' + fmtPct(e.conf_title_pct) + '</div>' +
      '<div class="c-odds ta-r">' + fmtPct(e.title_pct) + '</div>' +
      '<div class="c-projw ta-r">' + (e.proj_wins == null ? '—' : e.proj_wins.toFixed(1)) + '</div>' +
      '<div class="ta-c">' + sparkline(e.elo_history, d) + '</div>' +
    '</div>';
  }

  function renderGrid() {
    var head = '<div class="tkr-grid tkr-head">' +
      '<div>RK</div><div>TEAM</div><div>CONF</div><div class="ta-r">W-L</div>' +
      '<div class="ta-r" style="color:var(--accent)">ELO</div><div class="ta-r">Δ1W</div>' +
      '<div class="ta-r">OFF</div><div class="ta-r">DEF</div><div class="ta-r">SOS</div>' +
      '<div class="ta-r">BID%</div><div class="ta-r">CONF%</div>' +
      '<div class="ta-r">NAT%</div><div class="ta-r">PROJ W</div>' +
      '<div class="ta-c">10WK</div></div>';
    
    // Apply filters
    var filtered = ENTRIES;
    if (activeFilter === 'Power 4') {
      filtered = ENTRIES.filter(function (e) {
        return ["Big Ten", "SEC", "Big 12", "ACC"].indexOf(e.conference_name) >= 0;
      });
    } else if (activeFilter !== 'All') {
      filtered = ENTRIES.filter(function (e) {
        return e.conference_name === activeFilter;
      });
    }

    var shown = boardExpanded ? filtered : filtered.slice(0, COLLAPSE_AT);
    var footer = '';
    if (filtered.length > COLLAPSE_AT) {
      footer = '<button class="tkr-expand" id="tkr-expand">' +
        (boardExpanded ? '▴ Show top ' + COLLAPSE_AT : '▾ Show all ' + filtered.length + ' teams') + '</button>';
    }
    document.getElementById('tkr-table').innerHTML = head + shown.map(rowHTML).join('') + footer;
    var btn = document.getElementById('tkr-expand');
    if (btn) btn.addEventListener('click', function () { boardExpanded = !boardExpanded; renderGrid(); });
    paintHeat();
  }

  // ── Ratings Table Filter Bar (client-side) ──
  function renderFilters() {
    var container = document.getElementById('tkr-filters');
    if (!container) return;
    var pills = ['All', 'Power 4', 'Big Ten', 'SEC', 'Big 12', 'ACC'];
    container.innerHTML = pills.map(function (p) {
      var activeClass = p === activeFilter ? 'active' : 'inactive';
      return '<button class="tkr-filter-pill ' + activeClass + '" data-filter="' + p + '">' + p + '</button>';
    }).join('');
    
    var buttons = container.querySelectorAll('.tkr-filter-pill');
    for (var i = 0; i < buttons.length; i++) {
      (function (btn) {
        btn.addEventListener('click', function () {
          var nextFilter = btn.getAttribute('data-filter');
          if (nextFilter === activeFilter) {
            activeFilter = 'All'; // click active resets to All
          } else {
            activeFilter = nextFilter;
          }
          renderFilters();
          renderGrid();
        });
      })(buttons[i]);
    }
  }

  // ── Auto-open team detail via URL parameter ──
  function checkUrlParams() {
    var params = new URLSearchParams(window.location.search);
    var teamId = params.get('team') || params.get('id');
    if (teamId) {
      var e = null;
      for (var i = 0; i < ENTRIES.length; i++) {
        if (String(ENTRIES[i].team_id) === teamId) {
          e = ENTRIES[i];
          break;
        }
      }
      if (e) {
        openDetail(e);
      }
    }
  }

  // ── Ticker tape (top 12) ──
  function renderTape() {
    var top = ENTRIES.slice(0, 12);
    var ticks = top.map(function (e) {
      var d = e.rank_change;
      return '<span class="tkr-tick"><span class="ab">' + esc(abbrOf(e)) + '</span>' +
        '<span class="el">' + fmtElo(e.elo_rating) + '</span>' +
        '<span class="' + trendClass(d) + '">' + deltaText(d) + '</span></span>';
    }).join('');
    var track = document.getElementById('tkr-tape-track');
    if (track) track.innerHTML = ticks + ticks; // duplicate → seamless -50% loop
  }

  // ── Stat ribbon ──
  function renderRibbon() {
    if (!ENTRIES.length) return;
    var topElo = ENTRIES[0];
    var avg = Math.round(ENTRIES.reduce(function (a, e) { return a + e.elo_rating; }, 0) / ENTRIES.length);
    var mover = ENTRIES.reduce(function (best, e) {
      return (e.rank_change || 0) > (best.rank_change || 0) ? e : best;
    }, ENTRIES[0]);
    set('rib-topelo', fmtElo(topElo.elo_rating));
    set('rib-fieldavg', String(avg));
    set('rib-mover', abbrOf(mover) + ' ' + deltaText(mover.rank_change || 0));
  }

  function set(id, txt) { var el = document.getElementById(id); if (el) el.textContent = txt; }

  // ── Header week/season ──
  function renderHeader(data) {
    var wk = document.getElementById('tkr-week');
    if (wk) wk.textContent = 'WK' + data.week + ' · ' + data.season;
    set('tkr-subtitle', 'Elo model · ' + data.total_teams + ' FBS teams · updated after every final');
  }

  // ── Detail view ──
  function detailChart(history) {
    var h = (history || []).filter(function (x) { return typeof x === 'number'; });
    if (h.length < 2) return '<svg class="tkr-chart" viewBox="0 0 560 210"></svg>';
    var pad = 14, W = 560, H = 210;
    var min = Math.min.apply(null, h) - 7, max = Math.max.apply(null, h) + 7;
    var range = max - min || 1;
    var X = function (i) { return pad + (i / (h.length - 1)) * (W - 2 * pad); };
    var Y = function (v) { return pad + (1 - (v - min) / range) * (H - 2 * pad); };
    var line = h.map(function (v, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); }).join(' ');
    var area = 'M' + X(0).toFixed(1) + ' ' + (H - pad) + ' ' +
      h.map(function (v, i) { return 'L' + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); }).join(' ') +
      ' L' + X(h.length - 1).toFixed(1) + ' ' + (H - pad) + ' Z';
    var grids = [52, 105, 158].map(function (y) {
      return '<line x1="0" y1="' + y + '" x2="560" y2="' + y + '" stroke="var(--grid)" stroke-width="1"/>';
    }).join('');
    var fill = isLight() ? 0.10 : 0.14;
    return '<svg class="tkr-chart" viewBox="0 0 560 210" preserveAspectRatio="none">' + grids +
      '<path d="' + area + '" fill="var(--accent)" fill-opacity="' + fill + '"/>' +
      '<path d="' + line + '" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>' +
      '<circle cx="' + X(h.length - 1).toFixed(1) + '" cy="' + Y(h[h.length - 1]).toFixed(1) + '" r="4" fill="var(--accent)"/></svg>';
  }

  function tile(lbl, val) { return '<div class="tkr-mtile"><div class="lbl">' + lbl + '</div><div class="val">' + val + '</div></div>'; }

  function openDetail(e) {
    var m = metaOf(e.team_name);
    var d = e.rank_change;
    var winpct = (e.wins + e.losses) ? Math.round((e.wins / (e.wins + e.losses)) * 100) + '%' : '—';
    
    // Find CFP seed in playoff projection
    var cfpSeed = '—';
    var cfpSub = 'Not projected';
    if (PLAYOFF_DATA && PLAYOFF_DATA.field) {
      for (var i = 0; i < PLAYOFF_DATA.field.length; i++) {
        var pt = PLAYOFF_DATA.field[i];
        if (pt.team_id === e.team_id) {
          var seed = pt.seed;
          cfpSeed = '#' + seed;
          if (seed <= 4) {
            var bowl = (seed === 1) ? 'Rose' : (seed === 2) ? 'Fiesta' : (seed === 3) ? 'Peach' : 'Sugar';
            cfpSub = 'BYE · ' + bowl + ' QF';
          } else {
            cfpSub = 'HOSTS R1';
          }
          if (pt.bid_pct != null) cfpSub += ' · ' + fmtPct(pt.bid_pct) + ' BID';
          break;
        }
      }
      // Outside the projected field, the simulation still has an opinion.
      if (cfpSeed === '—' && PLAYOFF_DATA.bubble) {
        for (var j = 0; j < PLAYOFF_DATA.bubble.length; j++) {
          var bt = PLAYOFF_DATA.bubble[j];
          if (bt.team_id === e.team_id && bt.bid_pct != null) {
            cfpSeed = fmtPct(bt.bid_pct);
            cfpSub = 'BID ODDS · ON THE BUBBLE';
            break;
          }
        }
      }
    }

    // Monte Carlo projection tiles. The rankings payload carries these per team,
    // so no lookup into PLAYOFF_DATA is needed. The row is dropped entirely when
    // no simulation covers the week — four em-dash tiles say nothing.
    var hasOdds = e.bid_pct != null || e.conf_title_pct != null ||
      e.title_pct != null || e.proj_wins != null;
    var oddsTiles = !hasOdds ? '' :
      '<div class="tkr-tiles-6 tkr-tiles-4">' +
        tile('PLAYOFF BID', fmtPct(e.bid_pct)) +
        tile('CONF TITLE', fmtPct(e.conf_title_pct)) +
        tile('NAT TITLE', fmtPct(e.title_pct)) +
        tile('PROJ WINS', e.proj_wins == null ? '—' : e.proj_wins.toFixed(1)) +
      '</div>';

    var badgeRow = '';
    if (e.rank) {
      badgeRow += '<span class="badge-rank">No. ' + e.rank + '</span>';
    }
    if (e.conference_name) {
      badgeRow += '<span class="badge-conf">' + esc(TeamVisuals.confLabel(e.conference_name)) + '</span>';
    }
    badgeRow += '<span class="badge-record-wk">' + e.wins + '–' + e.losses + ' · WK' + CURRENT_WEEK + '</span>';

    var html =
      '<button class="tkr-back" id="tkr-back">← BACK TO BOARD</button>' +
      
      // Upgraded Hero Card (P1)
      '<div class="tkr-idcard-upgrade">' +
        '<div class="accent-panel" style="background:' + stripeOf(e) + '"></div>' +
        '<div class="content-area">' +
          '<div class="badge-row">' + badgeRow + '</div>' +
          '<h2 class="team-name">' + esc(e.team_name) + '</h2>' +
          '<div class="mascot">' + esc(m.mascot || '') + '</div>' +
        '</div>' +
        '<div class="elo-sidebar">' +
          '<div class="elo-label">ELO RATING</div>' +
          '<div class="elo-value">' + fmtElo(e.elo_rating) + '</div>' +
          '<div class="delta-row ' + trendClass(d) + '">' + deltaText(d) + ' WK</div>' +
        '</div>' +
      '</div>' +
      
      // 6 Metric Tiles (P2)
      '<div class="tkr-tiles-6">' +
        tile('ELO', fmtElo(e.elo_rating)) +
        tile('OFF P/G', e.off == null ? '—' : e.off) +
        tile('DEF P/G', e.def == null ? '—' : e.def) +
        tile('SOS', e.sos == null ? '—' : e.sos.toFixed(3)) +
        tile('WIN%', winpct) +
        '<div class="tkr-mtile cfp-seed"><div class="lbl">CFP SEED</div><div class="val">' + cfpSeed + '</div><div class="sub" style="font-family:var(--font-mono);font-size:9.5px;color:var(--fg3);margin-top:4px;text-transform:uppercase;">' + cfpSub + '</div></div>' +
      '</div>' +

      oddsTiles +

      '<div class="tkr-detail-grid">' +
        '<div>' +
          '<div class="tkr-chartcard" style="margin-bottom:14px;"><h3>Elo history</h3>' + detailChart(e.elo_history) + '</div>' +
          // CFP Path (P6)
          '<div id="tkr-path-container" class="hidden"></div>' +
          // Season Schedule (P4)
          '<div class="tkr-sched-card"><h3>Schedule</h3><div id="tkr-sched-body"><div style="color:var(--fg3);font-family:var(--font-mono);font-size:11px;">Loading predictions…</div></div></div>' +
        '</div>' +
        '<div>' +
          '<div class="tkr-logcard" style="margin-bottom:14px;"><h3>Results</h3><div class="tkr-log" id="tkr-log">' +
            '<div class="tkr-logrow" style="color:var(--fg3)">Loading…</div></div></div>' +
          // Conference Ladder (P5)
          '<div id="tkr-ladder-container"></div>' +
        '</div>' +
      '</div>';

    var d1 = document.getElementById('tkr-detail');
    d1.innerHTML = html;
    document.getElementById('tkr-board').classList.add('hidden');
    d1.classList.remove('hidden');
    window.scrollTo(0, 0);
    document.getElementById('tkr-back').addEventListener('click', showBoard);
    
    loadResults(e);
    loadSchedule(e);
    renderConferenceLadder(e);
    renderCFPPath(e);
  }

  function showBoard() {
    document.getElementById('tkr-detail').classList.add('hidden');
    document.getElementById('tkr-board').classList.remove('hidden');
  }

  // Results log — map the team schedule endpoint.
  function loadResults(e) {
    var season = (window.__tkrSeason) || new Date().getFullYear();
    api.getTeamSchedule(e.team_id, season).then(function (res) {
      var games = (res && (res.games || res.schedule || res)) || [];
      var played = games.filter(function (g) {
        return g.is_played && g.score;
      });
      var log = document.getElementById('tkr-log');
      if (!log) return;
      if (!played.length) { log.innerHTML = '<div class="tkr-logrow" style="color:var(--fg3)">No results yet.</div>'; return; }
      log.innerHTML = played.map(function (g) {
        var home = g.home_team_id === e.team_id || g.is_home === true;
        var pf = home ? g.home_score : g.away_score;
        var pa = home ? g.away_score : g.home_score;
        var win = pf > pa;
        var oppName = g.opponent_name;
        var oppRank = g.opponent_rank;
        return '<div class="tkr-logrow"><span class="tkr-chip ' + (win ? 'w' : 'l') + '">' + (win ? 'W' : 'L') + '</span>' +
          '<span class="va">' + (home ? 'vs' : '@') + '</span>' +
          '<span class="opp">' + (oppRank ? '<span class="rk">#' + oppRank + '</span>' : '') + esc(oppName || '—') + '</span>' +
          '<span class="score">' + pf + '–' + pa + '</span></div>';
      }).join('');
    }).catch(function () {
      var log = document.getElementById('tkr-log');
      if (log) log.innerHTML = '<div class="tkr-logrow" style="color:var(--fg3)">Results unavailable.</div>';
    });
  }

  // Season schedule (P4). Played weeks show the final, the current week is
  // highlighted, and later weeks show the model's projection.
  function loadSchedule(e) {
    var container = document.getElementById('tkr-sched-body');
    if (!container) return;

    var season = (window.__tkrSeason) || new Date().getFullYear();

    Promise.all([
      api.getPredictions({ teamId: e.team_id, nextWeek: false, season: season }),
      api.getTeamSchedule(e.team_id, season)
    ]).then(function (results) {
      var preds = results[0] || [];
      var games = (results[1] || {}).games || [];

      // One row per week from the season opener through the last scheduled
      // game. Regular-season weeks with no game are byes; empty postseason
      // weeks are simply skipped — a team that misses the CFP has no bye there.
      var gameByWeek = {};
      var maxWeek = 14;
      var minWeek = 1;
      for (var i = 0; i < games.length; i++) {
        var g = games[i];
        if (gameByWeek[g.week] == null) gameByWeek[g.week] = g;
        if (g.week > maxWeek) maxWeek = g.week;
        if (g.week < minWeek) minWeek = g.week;
      }

      var rows = [];
      for (var w = minWeek; w <= maxWeek; w++) {
        var game = gameByWeek[w];
        if (game) {
          var pred = null;
          for (var k = 0; k < preds.length; k++) {
            if (preds[k].game_id === game.game_id) { pred = preds[k]; break; }
          }
          rows.push({ type: game.is_played ? 'result' : 'game', week: w, game: game, pred: pred });
        } else if (w <= 14) {
          rows.push({ type: 'bye', week: w });
        }
      }

      if (!rows.length) {
        container.innerHTML = '<div style="color:var(--fg3);font-family:var(--font-mono);font-size:11px;">No games scheduled.</div>';
        return;
      }

      container.innerHTML = rows.map(function (row) {
        var wkLabel = 'WK' + row.week;
        if (row.week === 15) wkLabel = 'CONF';
        else if (row.week === 16) wkLabel = 'CFP R1';
        else if (row.week === 17) wkLabel = 'CFP QF';
        else if (row.week === 18) wkLabel = 'CFP SF';
        else if (row.week === 19) wkLabel = 'CFP CG';

        var rowClass = 'tkr-sched-grid' + (row.week === CURRENT_WEEK ? ' is-current' : '');

        if (row.type === 'bye') {
          return '<div class="' + rowClass + '">' +
            '<div class="tkr-sched-wk">' + wkLabel + '</div>' +
            '<div class="tkr-sched-loc"></div>' +
            '<div class="tkr-sched-opp tkr-sched-bye">BYE</div>' +
            '<div class="tkr-sched-proj"></div>' +
            '<div class="tkr-sched-bar-container"><div class="tkr-sched-bar-fill" style="width:0%;"></div></div>' +
            '<div class="tkr-sched-odds tkr-sched-bye">BYE</div>' +
          '</div>';
        }

        var game = row.game;
        var loc = game.is_neutral_site ? '◇' : (game.is_home ? 'vs' : '@');
        var oppName = game.opponent_name;
        var oppCell = '<div class="tkr-sched-opp ' + '%CLS%' + '">' +
            '<span class="tkr-sched-stripe" style="background:' + stripeName(oppName) + '"></span>' +
            '<span>' + esc(abbrName(oppName)) + '</span>' +
          '</div>';

        if (row.type === 'result') {
          var pf = game.is_home ? game.home_score : game.away_score;
          var pa = game.is_home ? game.away_score : game.home_score;
          var win = pf > pa;
          var resClass = win ? 'fav' : 'dog';
          return '<div class="' + rowClass + '">' +
            '<div class="tkr-sched-wk">' + wkLabel + '</div>' +
            '<div class="tkr-sched-loc">' + loc + '</div>' +
            oppCell.replace('%CLS%', resClass) +
            '<div class="tkr-sched-proj">' + pf + '–' + pa + '</div>' +
            '<div class="tkr-sched-bar-container"></div>' +
            '<div class="tkr-sched-odds ' + resClass + '">' + (win ? 'W' : 'L') + '</div>' +
          '</div>';
        }

        var pred = row.pred;
        var projText = '—';
        var pWin = 0;

        if (pred) {
          var favScore = Math.max(pred.predicted_home_score, pred.predicted_away_score);
          var dogScore = Math.min(pred.predicted_home_score, pred.predicted_away_score);
          projText = favScore + '–' + dogScore;
          // home/away_win_probability are the *home* and *away* team's odds, so
          // pick the side this team is actually on.
          pWin = game.is_home ? pred.home_win_probability : pred.away_win_probability;
        } else {
          var oppElo = 1500;
          for (var m = 0; m < ENTRIES.length; m++) {
            if (ENTRIES[m].team_id === game.opponent_id) { oppElo = ENTRIES[m].elo_rating; break; }
          }
          var teamAdj = e.elo_rating + (game.is_home ? 65 : 0);
          var oppAdj = oppElo + (game.is_home ? 0 : 65);
          pWin = 100 / (1 + Math.pow(10, (oppAdj - teamAdj) / 400));
        }

        var cls = pWin >= 50 ? 'fav' : 'dog';
        return '<div class="' + rowClass + '">' +
          '<div class="tkr-sched-wk">' + wkLabel + '</div>' +
          '<div class="tkr-sched-loc">' + loc + '</div>' +
          oppCell.replace('%CLS%', cls) +
          '<div class="tkr-sched-proj">' + projText + '</div>' +
          '<div class="tkr-sched-bar-container">' +
            '<div class="tkr-sched-bar-fill ' + cls + '" style="width:' + pWin.toFixed(0) + '%;"></div>' +
          '</div>' +
          '<div class="tkr-sched-odds ' + cls + '">' + pWin.toFixed(0) + '%</div>' +
        '</div>';
      }).join('');

    }).catch(function (err) {
      console.error('Error loading schedule:', err);
      container.innerHTML = '<div style="color:var(--fg3);font-family:var(--font-mono);font-size:11px;">Schedule unavailable.</div>';
    });
  }

  // Conference ladder logic (P5)
  function renderConferenceLadder(e) {
    var container = document.getElementById('tkr-ladder-container');
    if (!container) return;

    var confName = e.conference_name || e.conference;
    if (!confName) return;

    var peers = ENTRIES.filter(function (x) {
      return (x.conference_name || x.conference) === confName;
    });

    peers.sort(function (a, b) { return b.elo_rating - a.elo_rating; });

    var top8 = peers.slice(0, 8);
    var maxElo = top8[0] ? top8[0].elo_rating : 1500;

    var html = '<div class="tkr-ladder-card"><h3>' + esc(confName) + ' ladder</h3>';
    html += top8.map(function (t, i) {
      var seed = i + 1;
      var active = t.team_id === e.team_id;
      var pct = (t.elo_rating / maxElo) * 100;
      var primaryColor = stripeName(t.team_name);
      
      var rgbaDim = 'rgba(245, 166, 35, 0.65)';
      var rgbVals = rgb(primaryColor);
      if (rgbVals) {
        rgbaDim = 'rgba(' + rgbVals[0] + ',' + rgbVals[1] + ',' + rgbVals[2] + ',0.65)';
      }

      var rowClass = active ? 'active' : 'inactive';
      var style = active 
        ? 'style="--primary-brand:' + primaryColor + '"'
        : 'style="--primary-brand-dim:' + rgbaDim + '"';

      return '<div class="tkr-ladder-grid ' + rowClass + '" ' + style + '>' +
        '<div class="tkr-ladder-seed">' + String(seed).padStart(2, '0') + '</div>' +
        '<div class="tkr-ladder-abbr">' + esc(abbrName(t.team_name)) + '</div>' +
        '<div class="tkr-ladder-bar-container">' +
          '<div class="tkr-ladder-bar-fill" style="width:' + pct.toFixed(1) + '%;"></div>' +
        '</div>' +
        '<div class="tkr-ladder-elo">' + fmtElo(t.elo_rating) + '</div>' +
      '</div>';
    }).join('');
    html += '</div>';
    container.innerHTML = html;
  }

  // CFP Path logic (P6)
  function renderCFPPath(e) {
    var container = document.getElementById('tkr-path-container');
    if (!container) return;

    if (!PLAYOFF_DATA || !PLAYOFF_DATA.field) {
      container.classList.add('hidden');
      return;
    }

    var playoffTeam = null;
    for (var i = 0; i < PLAYOFF_DATA.field.length; i++) {
      if (PLAYOFF_DATA.field[i].team_id === e.team_id) {
        playoffTeam = PLAYOFF_DATA.field[i];
        break;
      }
    }
    if (!playoffTeam) {
      container.classList.add('hidden');
      return;
    }

    var seedClinched = true;
    var seedActive = false;
    var seedWinProb = 100;
    
    var qfClinched = false;
    var qfActive = false;
    var qfWinProb = 0;
    var qfLabel = 'Quarterfinal';
    var qfDate = 'DEC 31 - JAN 1';

    var sfClinched = false;
    var sfActive = false;
    var sfWinProb = 0;
    var sfLabel = 'Semifinal';
    var sfDate = 'JAN 8–9';

    var titleClinched = false;
    var titleActive = false;
    var titleWinProb = 0;
    var titleLabel = 'Championship';
    var titleDate = 'JAN 19';

    var inFR = playoffTeam.seed >= 5;
    
    if (inFR) {
      var frMatch = null;
      if (PLAYOFF_DATA.first_round) {
        for (var i = 0; i < PLAYOFF_DATA.first_round.length; i++) {
          var m = PLAYOFF_DATA.first_round[i];
          if (m.high.team_id === e.team_id || m.low.team_id === e.team_id) {
            frMatch = m;
            break;
          }
        }
      }
      if (frMatch) {
        var isWinner = frMatch.winner_id === e.team_id;
        var selfObj = frMatch.high.team_id === e.team_id ? frMatch.high : frMatch.low;
        seedWinProb = selfObj.win_prob;
        if (!isWinner) {
          seedClinched = false;
          seedActive = true;
        }
      }
    }

    if (seedClinched) {
      var qfMatch = null;
      if (PLAYOFF_DATA.quarterfinals) {
        for (var i = 0; i < PLAYOFF_DATA.quarterfinals.length; i++) {
          var m = PLAYOFF_DATA.quarterfinals[i];
          if (m.high.team_id === e.team_id || m.low.team_id === e.team_id) {
            qfMatch = m;
            break;
          }
        }
      }
      if (qfMatch) {
        qfLabel = qfMatch.label || qfLabel;
        var isWinner = qfMatch.winner_id === e.team_id;
        var selfObj = qfMatch.high.team_id === e.team_id ? qfMatch.high : qfMatch.low;
        qfWinProb = selfObj.win_prob;
        if (isWinner) {
          qfClinched = true;
        } else {
          qfActive = true;
        }
      }
    }

    if (qfClinched) {
      var sfMatch = null;
      if (PLAYOFF_DATA.semifinals) {
        for (var i = 0; i < PLAYOFF_DATA.semifinals.length; i++) {
          var m = PLAYOFF_DATA.semifinals[i];
          if (m.high.team_id === e.team_id || m.low.team_id === e.team_id) {
            sfMatch = m;
            break;
          }
        }
      }
      if (sfMatch) {
        sfLabel = sfMatch.label || sfLabel;
        var isWinner = sfMatch.winner_id === e.team_id;
        var selfObj = sfMatch.high.team_id === e.team_id ? sfMatch.high : sfMatch.low;
        sfWinProb = selfObj.win_prob;
        if (isWinner) {
          sfClinched = true;
        } else {
          sfActive = true;
        }
      }
    }

    if (sfClinched) {
      var titleMatch = PLAYOFF_DATA.final;
      if (titleMatch) {
        titleLabel = titleMatch.label || titleLabel;
        var isWinner = titleMatch.winner_id === e.team_id;
        var selfObj = titleMatch.high.team_id === e.team_id ? titleMatch.high : titleMatch.low;
        titleWinProb = selfObj.win_prob;
        if (isWinner) {
          titleClinched = true;
        } else {
          titleActive = true;
        }
      }
    }

    function getTileHtml(round, name, date, clinched, active, winProb) {
      var stateClass = clinched ? 'clinched' : (active ? 'active' : 'future');
      var pctText = clinched ? '✓' : (active ? Math.round(winProb) + '%' : '—');
      return '<div class="tkr-path-tile ' + stateClass + '">' +
        '<span class="tkr-path-round">' + esc(round) + '</span>' +
        '<span class="tkr-path-name">' + esc(name) + '</span>' +
        '<span class="tkr-path-site">' + esc(date) + '</span>' +
        '<span class="tkr-path-pct">' + pctText + '</span>' +
      '</div>';
    }

    var arrow = '<div class="tkr-path-arrow">→</div>';

    var html = '<h3>CFP projection path</h3>' +
      '<div class="tkr-path-grid">' +
        getTileHtml('SEED', 'No. ' + playoffTeam.seed + ' Seed', inFR ? 'CAMPUS' : 'BYE', seedClinched, seedActive, seedWinProb) + arrow +
        getTileHtml('QTRFINAL', qfLabel, qfDate, qfClinched, qfActive, qfWinProb) + arrow +
        getTileHtml('SEMIFINAL', sfLabel, sfDate, sfClinched, sfActive, sfWinProb) + arrow +
        getTileHtml('CHAMPION', 'National Champ', titleDate, titleClinched, titleActive, titleWinProb) +
      '</div>';

    container.innerHTML = html;
    container.classList.remove('hidden');
  }

  // ── Game predictions ──
  var CONF = { 'Very High': 'HIGH', 'High': 'HIGH', 'Medium': 'MED', 'Low': 'LOW' };

  function predRow(p) {
    var aw = p.away_team, hm = p.home_team;
    var hmColor = stripeName(hm);
    // The away side gives way when the two brands are hard to tell apart,
    // preferring the away team's own alternate colour over a neutral.
    var awColor = pairColor(aw, hm);
    var awP = Math.round(p.away_win_probability), hmP = Math.round(p.home_win_probability);
    var sep = p.is_neutral_site ? 'v' : '@';
    var margin = Math.abs(p.predicted_home_score - p.predicted_away_score);
    var favAbbr = abbrName(p.predicted_winner);
    return '<div class="tkr-pgrid tkr-prow">' +
      '<div class="tkr-match">' +
        '<span class="stripe" style="background:' + stripeName(aw) + '"></span>' + esc(abbrName(aw)) +
        '<span class="at">' + sep + '</span>' +
        '<span class="stripe" style="background:' + hmColor + '"></span>' + esc(abbrName(hm)) + '</div>' +
      '<div class="tkr-proj">' + p.predicted_away_score + '-' + p.predicted_home_score + '</div>' +
      '<div class="tkr-prob"><div class="tkr-bar">' +
          '<span style="width:' + awP + '%;background:' + awColor + '"></span>' +
          '<span style="width:' + hmP + '%;background:' + hmColor + '"></span></div>' +
        '<div class="tkr-prob-pct"><span>' + awP + '%</span><span>' + hmP + '%</span></div></div>' +
      '<div class="tkr-spread"><span class="fav">' + esc(favAbbr) + '</span> -' + margin.toFixed(1) + '</div>' +
      '<div class="tkr-conf"><span class="tkr-chip2">' + (CONF[p.confidence] || '—') + '</span></div>' +
    '</div>';
  }

  // Rows shown before the "show more" cut. A full week runs 60+ games, which
  // buries the bracket below it.
  var PRED_VISIBLE = 15;

  function renderPredictions(list) {
    var card = document.getElementById('tkr-preds');
    if (!card) return;
    if (!list || !list.length) { card.classList.add('hidden'); return; }
    set('tkr-preds-meta', 'WK' + list[0].week + ' · ' + list.length + ' GAMES');
    var head = '<div class="tkr-pgrid tkr-phead"><div>MATCHUP</div><div>PROJ</div>' +
      '<div>WIN PROB</div><div>SPREAD</div><div>CONF</div></div>';
    var rows = list.map(predRow);
    var body = head + rows.slice(0, PRED_VISIBLE).join('');
    var rest = rows.slice(PRED_VISIBLE);
    if (rest.length) {
      body += '<div id="tkr-preds-rest" class="hidden">' + rest.join('') + '</div>' +
        '<button type="button" class="tkr-preds-more" id="tkr-preds-more">' +
        'Show ' + rest.length + ' more</button>';
    }
    document.getElementById('tkr-preds-body').innerHTML = body;
    var more = document.getElementById('tkr-preds-more');
    if (more) {
      more.addEventListener('click', function () {
        var restEl = document.getElementById('tkr-preds-rest');
        var hidden = restEl.classList.toggle('hidden');
        more.textContent = hidden ? 'Show ' + rest.length + ' more' : 'Show fewer';
      });
    }
    card.classList.remove('hidden');
  }

  function loadPredictions() {
    api.getPredictions({ nextWeek: true }).then(renderPredictions).catch(function () {});
  }

  // ── Projected playoff bracket ──
  var ROUNDS = [
    { key: 'first_round', t: 'FIRST ROUND', d: 'DEC 19–20 · CAMPUS' },
    { key: 'quarterfinals', t: 'QUARTERFINALS', d: 'DEC 31 – JAN 1 · BYES ENTER' },
    { key: 'semifinals', t: 'SEMIFINALS', d: 'JAN 8–9' },
    { key: 'final', t: 'FINAL', d: 'JAN 19 · LAS VEGAS' },
  ];

  function bkTeamRow(t, win, color) {
    return '<div class="bk-team' + (win ? ' win' : ' out') + '">' +
      '<span class="bk-mk">' + (win ? '▸' : '') + '</span>' +
      '<span class="bk-seed">' + t.seed + '</span>' +
      '<span class="bk-stripe" style="background:' + color + '"></span>' +
      '<span class="bk-ab">' + esc(abbrName(t.name)) + '</span>' +
      '<span class="bk-sc">' + t.score + '</span></div>';
  }

  function matchCard(m) {
    var hi = m.high, lo = m.low, hiWin = m.winner_id === hi.team_id;
    var hC = stripeName(hi.name), lC = pairColor(lo.name, hi.name);
    var label = m.neutral ? esc(m.label.toUpperCase()) : '△ ' + esc(abbrName(hi.name));
    return '<div class="bk-card"><div class="bk-label">' + label + '</div>' +
      '<div class="bk-box">' + bkTeamRow(hi, hiWin, hC) + bkTeamRow(lo, !hiWin, lC) +
        '<div class="bk-bar"><span style="width:' + Math.round(hi.win_prob) + '%;background:' + hC + '"></span>' +
          '<span style="width:' + Math.round(lo.win_prob) + '%;background:' + lC + '"></span></div>' +
        '<div class="bk-pct"><span>' + Math.round(hi.win_prob) + '%</span><span>' + Math.round(lo.win_prob) + '%</span></div>' +
      '</div></div>';
  }

  function championCard(ch) {
    if (!ch) return '';
    var c = stripeName(ch.name);
    return '<div class="bk-champ"><div class="bk-champ-lbl">◆ TITLE FAVORITE</div>' +
      '<div class="bk-champ-name"><span class="bk-stripe" style="background:' + c + '"></span>' + esc(abbrName(ch.name)) + '</div>' +
      '<div class="bk-champ-full">' + esc(ch.name) + '</div>' +
      '<div class="bk-champ-sub">No. ' + ch.seed + ' SEED · ' + esc(TeamVisuals.confLabel(ch.conference_name)) + '</div>' +
      '<div class="bk-champ-win"><span>TITLE-GAME WIN</span><span class="v">' + Math.round(ch.title_game_win_prob) + '%</span></div></div>';
  }

  // Percentages read better without a trailing ".0" on whole numbers.
  function fmtPct(v) {
    if (v == null) return '—';
    return (Math.round(v * 10) / 10).toFixed(v < 10 ? 1 : 0) + '%';
  }

  function oddsRow(t, inField) {
    var c = stripeName(t.name);
    return '<div class="bk-odds-row' + (inField ? '' : ' out') + '">' +
      '<span class="bk-odds-seed">' + (inField ? t.seed : '—') + '</span>' +
      '<span class="bk-stripe" style="background:' + c + '"></span>' +
      '<span class="bk-odds-name">' + esc(abbrName(t.name)) + '</span>' +
      '<span class="bk-odds-bar"><i style="width:' + Math.max(1, Math.round(t.bid_pct)) + '%;background:' + c + '"></i></span>' +
      '<span class="bk-odds-pct">' + fmtPct(t.bid_pct) + '</span>' +
      '<span class="bk-odds-sub">' + fmtPct(t.conf_title_pct) + '</span>' +
      '<span class="bk-odds-sub">' + fmtPct(t.title_pct) + '</span></div>';
  }

  // Per-team probabilities only exist for a simulated season; the deterministic
  // current-ratings fallback has nothing to put here.
  function renderOdds(data) {
    var host = document.getElementById('tkr-bracket-odds');
    if (!host) return;
    if (data.method !== 'monte_carlo' || !data.field.length || data.field[0].bid_pct == null) {
      host.innerHTML = '';
      host.classList.add('hidden');
      return;
    }
    var head = '<div class="bk-odds-head"><span class="bk-odds-seed">SD</span>' +
      '<span class="bk-stripe"></span><span class="bk-odds-name">TEAM</span>' +
      '<span class="bk-odds-bar"></span><span class="bk-odds-pct">PLAYOFF</span>' +
      '<span class="bk-odds-sub">CONF</span><span class="bk-odds-sub">TITLE</span></div>';
    var rows = data.field.map(function (t) { return oddsRow(t, true); }).join('');
    var bubble = (data.bubble || []).slice(0, 8);
    if (bubble.length) {
      rows += '<div class="bk-odds-split">ON THE BUBBLE</div>' +
        bubble.map(function (t) { return oddsRow(t, false); }).join('');
    }
    host.innerHTML = '<h3 class="bk-odds-title">Playoff odds</h3>' + head + rows;
    host.classList.remove('hidden');
  }

  function renderBracketHead(data) {
    var sub = document.querySelector('.tkr-bracket-sub');
    var meta = document.querySelector('.tkr-bracket-meta');
    if (sub) {
      sub.textContent = data.method === 'monte_carlo'
        ? 'Consensus field from ' + Number(data.runs).toLocaleString() + ' simulated seasons · ▸ marks the favored side advancing.'
        : 'Seeded from current ratings · ▸ marks the favored side advancing.';
    }
    if (meta) {
      meta.innerHTML = '12-TEAM FIELD<br>SEEDS 1–4 BYE' +
        (data.through_week != null ? '<br>THROUGH WK ' + data.through_week : '');
    }
  }

  function renderBracket(data) {
    var card = document.getElementById('tkr-bracket');
    if (!card) return;
    if (!data || !data.field || !data.field.length) { card.classList.add('hidden'); return; }
    renderBracketHead(data);
    var cols = ROUNDS.map(function (r) {
      var items = r.key === 'final' ? (data.final ? [data.final] : []) : (data[r.key] || []);
      return '<div class="bk-col"><div class="bk-round"><div class="bk-round-t">' + r.t + '</div>' +
        '<div class="bk-round-d">' + r.d + '</div></div>' +
        '<div class="bk-col-body">' + items.map(matchCard).join('') + '</div></div>';
    }).join('');
    cols += '<div class="bk-col champion"><div class="bk-round"><div class="bk-round-t">CHAMPION</div>' +
      '<div class="bk-round-d">PROJECTED</div></div><div class="bk-col-body">' + championCard(data.champion) + '</div></div>';
    document.getElementById('tkr-bracket-cols').innerHTML = cols;
    renderOdds(data);
    card.classList.remove('hidden');
  }

  function loadBracket() {
    api.fetch('/playoff-projection').then(function (data) {
      PLAYOFF_DATA = data;
      renderBracket(data);
    }).catch(function () {});
  }

  // ── Boot ──
  function wireClicks() {
    document.getElementById('tkr-table').addEventListener('click', function (ev) {
      var row = ev.target.closest('.tkr-row');
      if (!row) return;
      var e = null;
      for (var i = 0; i < ENTRIES.length; i++) {
        if (String(ENTRIES[i].team_id) === row.dataset.id) {
          e = ENTRIES[i];
          break;
        }
      }
      if (e) openDetail(e);
    });
  }

  function renderAll(data) {
    ENTRIES = data.rankings || [];
    boardExpanded = false;
    window.__tkrSeason = data.season;
    CURRENT_WEEK = data.week;
    renderHeader(data);
    renderTape();
    renderRibbon();
    renderFilters();
    renderGrid();
    checkUrlParams();
  }

  function init() {
    wireClicks();
    window.addEventListener('themechange', function () { paintHeat(); /* SVGs use CSS vars, auto-update */ });

    Promise.all([
      fetch('data/teams-meta.json').then(function (r) { return r.json(); }).catch(function () { return {}; }),
      api.getRankings(200),
    ]).then(function (out) {
      META = out[0] || {};
      renderAll(out[1]);
      loadPredictions();
      loadBracket();
    }).catch(function (err) {
      console.error('Board load failed:', err);
      var t = document.getElementById('tkr-table');
      if (t) t.innerHTML = '<div style="padding:24px;color:var(--fg2)">Could not load rankings.</div>';
    });
  }

  // Expose hooks so the preview harness can inject endpoint-shaped data
  // (the static preview can't reach the backend — see local-dev memory).
  window.__tkrRender = function (data, meta) { META = meta || META; renderAll(data); };
  window.__tkrRenderPreds = renderPredictions;
  window.__tkrRenderBracket = renderBracket;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
