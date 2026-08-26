// Countdown to the next kickoff, rendered into #tkr-countdown in the ticker header.
// Before Week 1 this reads as the countdown to the season opener; once games are
// underway it tracks the next scheduled game.
(function () {
  var TICK_MS = 1000;
  var el = null;
  var target = null;   // Date of the next kickoff
  var label = '';
  var timer = null;

  var base = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : '/api';

  // The API stamps game_date with a UTC offset, but older cached responses (and
  // the raw sqlite " "-separated form) can arrive bare. JS reads an offset-less
  // date-time as LOCAL, which skews the countdown by the viewer's UTC offset.
  function parseUtc(s) {
    if (!s) return null;
    var iso = /(Z|[+-]\d{2}:?\d{2})$/.test(s) ? s : s + 'Z';
    var d = new Date(iso.replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
  }

  function pad(n) { return n < 10 ? '0' + n : String(n); }

  function render() {
    if (!el || !target) return;
    var ms = target.getTime() - Date.now();

    if (ms <= 0) {
      el.textContent = 'KICKOFF';
      clearInterval(timer);
      timer = null;
      // Game has started — roll forward to the next one shortly.
      setTimeout(load, 60000);
      return;
    }

    var s = Math.floor(ms / 1000);
    var d = Math.floor(s / 86400);
    var h = Math.floor((s % 86400) / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    el.textContent = label + ' ' + (d > 0 ? d + 'd ' : '') + pad(h) + ':' + pad(m) + ':' + pad(sec);
  }

  function pickNext(games) {
    var now = Date.now();
    var soonest = null;
    for (var i = 0; i < games.length; i++) {
      var g = games[i];
      if (g.is_processed) continue;
      var when = parseUtc(g.game_date);
      if (!when || when.getTime() <= now) continue;
      if (!soonest || when < soonest.when) soonest = { when: when, week: g.week };
    }
    return soonest;
  }

  function load() {
    fetch(base + '/seasons/active')
      .then(function (r) { return r.json(); })
      .then(function (season) {
        var wk = season.current_week != null ? season.current_week : 1;
        // ponytail: current week + the next one is enough to find the next
        // kickoff. Widen the range if a bye or a gap ever leaves both empty.
        var weeks = [wk, wk + 1];
        return Promise.all(weeks.map(function (w) {
          return fetch(base + '/games?season=' + season.year + '&week=' + w + '&limit=500')
            .then(function (r) { return r.json(); })
            .catch(function () { return []; });
        })).then(function (lists) {
          var games = [];
          for (var i = 0; i < lists.length; i++) {
            if (Array.isArray(lists[i])) games = games.concat(lists[i]);
          }
          return { season: season, next: pickNext(games) };
        });
      })
      .then(function (res) {
        if (!res.next) { if (el) el.textContent = ''; return; }
        target = res.next.when;
        var notStarted = (res.season.current_week == null || res.season.current_week <= 1);
        label = (notStarted && res.next.week <= 1) ? 'KICKOFF IN' : 'NEXT GAME IN';
        render();
        if (!timer) timer = setInterval(render, TICK_MS);
      })
      .catch(function (e) {
        console.warn('Countdown unavailable:', e);
        if (el) el.textContent = '';
      });
  }

  function start() {
    el = document.getElementById('tkr-countdown');
    if (el) load();
  }

  // Expose the two pure helpers so the node self-check can exercise them.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parseUtc: parseUtc, pickNext: pickNext };
  }
  if (typeof document === 'undefined') return;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
