// Live game data from /api/live (CFBD scoreboard behind a 60s server cache).
// Reuses the global `api` (api.js). Exposes `live.find(home, away)` and
// `live.poll(onUpdate)`.
(function () {
  'use strict';
  var REFRESH_MS = 60000;           // CFBD refreshes the scoreboard about once a minute
  var LEAD_MS = 15 * 60000;         // start polling this long before kickoff
  var games = [];
  var listeners = [];
  var timer = null;

  function key(home, away) { return home + '|' + away; }
  var byKey = {};

  function find(home, away) {
    return byKey[key(home, away)] || null;
  }

  // Next refresh: every minute while anything is live or about to kick off,
  // otherwise wake shortly before the next kickoff today. Nothing pending
  // means no more requests until the page reloads.
  function nextDelay() {
    var now = Date.now(), soonest = Infinity;
    for (var i = 0; i < games.length; i++) {
      var g = games[i];
      if (g.status === 'in_progress') return REFRESH_MS;
      if (g.status === 'scheduled' && g.start_date) {
        var t = Date.parse(g.start_date) - LEAD_MS;
        if (t <= now) return REFRESH_MS;
        soonest = Math.min(soonest, t);
      }
    }
    return soonest - now < 12 * 3600000 ? soonest - now : null;
  }

  function load() {
    clearTimeout(timer);
    // A hidden tab costs nothing; check again in a minute.
    if (document.hidden) { timer = setTimeout(load, REFRESH_MS); return; }
    api.fetch('/live').then(function (list) {
      games = list || [];
      byKey = {};
      games.forEach(function (g) { byKey[key(g.home, g.away)] = g; });
      listeners.forEach(function (fn) { fn(); });
    }).catch(function () {}).then(function () {
      var d = nextDelay();
      if (d != null) timer = setTimeout(load, d);
    });
  }

  function poll(onUpdate) {
    listeners.push(onUpdate);
    if (listeners.length === 1) load(); else onUpdate();
  }

  window.live = { find: find, poll: poll };
})();
