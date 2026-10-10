// Live game cards (design handoff, Oct 2026).
//   GameCard.front(g, ctx)  — high-contrast labeled card for the Rankings page
//   GameCard.games(g, ctx)  — situation card with the field for the Games page
// `g` is one /api/live game. `ctx`: { meta(name) -> teams-meta entry,
// rank(name) -> number|null, pred -> /api/predictions row|null, href, id }.
// Pure helpers are exported for tests/frontend/test_game_card.js.
(function () {
  'use strict';
  var TV = (typeof window !== 'undefined' && window.TeamVisuals) ||
    (typeof require !== 'undefined' ? require('./team-visuals.js') : null);
  var CARD = '#1a1a1f';   // --gc-card; team colours must clear 3:1 against it
  var NEUTRAL = '#b8bcc4';
  var STALE_MS = 60000;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }
  function ord(n) { return n + (['th', 'st', 'nd', 'rd'][n] || 'th'); }
  function clockText(c) { return String(c || '').replace(/^0(\d)/, '$1'); }
  function isBreak(g) {
    return g.status === 'in_progress' && g.period <= 4 && /^0?0:00$/.test(g.clock || '');
  }
  function breakText(g) { return g.period === 2 ? 'Halftime' : 'End of ' + ord(g.period); }
  function kickoffText(g) {
    var d = new Date(g.start_date);
    if (isNaN(d)) return 'TBD';
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' }) + ' ET';
  }
  function finalText(g) { return 'FINAL' + (g.period > 4 ? ' / OT' : ''); }

  // Front status band: game state in plain words.
  function statusText(g) {
    if (g.status === 'scheduled') return 'KICKOFF ' + kickoffText(g);
    if (g.status === 'completed') return finalText(g);
    if (g.status !== 'in_progress') return String(g.status || '').toUpperCase();
    if (g.period > 4) return '● LIVE — OT' + (g.period - 4);
    if (isBreak(g)) return breakText(g).toUpperCase();
    return '● LIVE — ' + ord(g.period).toUpperCase() + ' QUARTER, ' + clockText(g.clock) + ' LEFT';
  }

  // Games-card clock: "Q3 10:53", "OT1", "HALFTIME", kickoff time, "FINAL".
  function clockLabel(g) {
    if (g.status === 'scheduled') return kickoffText(g);
    if (g.status === 'completed') return finalText(g);
    if (g.period > 4) return 'OT' + (g.period - 4);
    if (isBreak(g)) return breakText(g).toUpperCase();
    return 'Q' + g.period + ' ' + clockText(g.clock);
  }

  // CFBD situation, e.g. "4th & 1 at KSU 20", "1st & Goal at ARK 3", "2nd & 7 at 50".
  function parseSituation(s) {
    var m = /^(\d)(?:st|nd|rd|th) & (goal|\d+) at (?:(\S+) )?(\d+)$/i.exec(String(s || '').trim());
    if (!m) return null;
    var down = +m[1], goal = /goal/i.test(m[2]);
    return { down: down, toGo: goal ? 'goal' : +m[2], side: m[3] || null, yard: +m[4],
             text: ord(down) + ' & ' + (goal ? 'Goal' : m[2]) };
  }

  function pct(yardsFromLeftGoal) { return (10 + yardsFromLeftGoal) / 120 * 100; }

  // Field geometry. Away end zone is fixed on the left, home on the right;
  // positions are yards from the left (away) goal line, 0-100.
  function fieldSpot(sit, possession, awayAbbr, homeAbbr) {
    if (!sit || (possession !== 'home' && possession !== 'away')) return null;
    var side = (sit.side || '').toUpperCase(), x;
    if (sit.yard === 50) x = 50;
    else if (side === String(awayAbbr).toUpperCase()) x = sit.yard;
    else if (side === String(homeAbbr).toUpperCase()) x = 100 - sit.yard;
    else return null;
    var dir = possession === 'away' ? 1 : -1;
    var ltg = sit.toGo === 'goal' ? (dir > 0 ? 100 : 0) : Math.max(0, Math.min(100, x + dir * sit.toGo));
    return { x: x, dir: dir, ball: pct(x), ltg: pct(ltg) };
  }

  // ponytail: the feed has no explicit kickoff/PAT state, so infer it from the
  // last play. Swap for a real field if CFBD ever adds one.
  function specialTeams(g) {
    var p = g.last_play || '';
    if (/KICK\)|extra point|two-point|conversion|field goal attempt.*\bGOOD\b|safety/i.test(p)) return 'Kickoff';
    if (/TOUCHDOWN/i.test(p)) return 'PAT attempt';
    return '';
  }

  // ── Last play: raw feed text -> short sentence case ──
  var NAME = "(?:#\\d+ )?([A-Z][\\w'-]*\\.\\s?[A-Z][\\w'-]*(?: (?:Jr|Sr|II|III|IV)\\.?)?)";
  function nm(s) { return s.replace(/^([A-Z])\.\s?/, '$1. '); }
  function rx(s) { return new RegExp(s, 'i'); }
  function cleanPlay(raw) {
    raw = String(raw || '').trim();
    var clock = '', m = /^\((\d{1,2}:\d{2})\)\s*/.exec(raw);
    if (m) { clock = clockText(m[1]); raw = raw.slice(m[0].length); }
    raw = raw.replace(/,\s*clock \d{1,2}:\d{2}$/, '');
    var text = null, yards = /for (\d+) yards? (gain|loss)|for no gain/i.exec(raw);
    var gain = !yards ? '' : !yards[1] ? ' for no gain' :
      /loss/i.test(yards[2]) ? ' for a loss of ' + yards[1] : ' for ' + yards[1] + (yards[1] === '1' ? ' yard' : ' yards');
    if ((m = rx(NAME + ' field goal attempt from (\\d+) yards? (NO GOOD|GOOD|BLOCKED|MISSED)').exec(raw))) {
      text = nm(m[1]) + ' ' + m[2] + '-yard field goal — ' + (/^good$/i.test(m[3]) ? 'good' : m[3].toLowerCase());
    } else if ((m = rx(NAME + ' pass complete[^#]*? to ' + NAME).exec(raw))) {
      var py = /for (\d+) yards?/i.exec(raw);
      text = nm(m[1]) + ' pass to ' + nm(m[2]) + (py ? ' for ' + py[1] + (py[1] === '1' ? ' yard' : ' yards') : '');
    } else if ((m = rx(NAME + ' pass incomplete').exec(raw))) {
      text = nm(m[1]) + ' pass incomplete';
    } else if ((m = rx(NAME + ' sacked for (?:a )?loss of (\\d+)').exec(raw))) {
      text = nm(m[1]) + ' sacked for a loss of ' + m[2];
    } else if ((m = rx(NAME + ' rush\\b').exec(raw))) {
      text = nm(m[1]) + ' rush' + gain;
    } else if ((m = rx(NAME + ' (punt|kickoff) (\\d+) yards?').exec(raw))) {
      text = nm(m[1]) + ' ' + m[3] + '-yard ' + m[2].toLowerCase();
    } else if ((m = /^\(([^()]+) KICK\)$/.exec(raw))) {
      text = nm(m[1]) + ' extra point — good';
    } else if (/^kneel down/i.test(raw)) {
      text = 'Kneel down';
    } else if ((m = /^Timeout (.+)$/i.exec(raw))) {
      text = 'Timeout, ' + m[1];
    }
    if (text == null) return { clock: clock, text: raw };
    if (/TOUCHDOWN/.test(raw)) text += '. Touchdown';
    else if (/INTERCEPT/i.test(raw)) text += '. Intercepted';
    else if (/FUMBLE/.test(raw)) text += '. Fumble';
    else if (/TURNOVER ON DOWNS/.test(raw)) text += '. Turnover on downs';
    else if (/1ST DOWN/.test(raw)) text += '. First down';
    return { clock: clock, text: /[.!]$/.test(text) ? text : text + '.' };
  }

  // Quarter columns; OT1, OT2, or one combined OT column past 2OT.
  function periodCols(g) {
    var a = g.away_line_scores || [], h = g.home_line_scores || [];
    var v = function (x) { return x == null ? null : x; };
    var cols = [1, 2, 3, 4].map(function (i) { return { label: String(i), away: v(a[i - 1]), home: v(h[i - 1]) }; });
    var ot = Math.max(a.length, h.length) - 4;
    var sum = function (arr) { return arr.slice(4).reduce(function (s, x) { return s + (x || 0); }, 0); };
    if (ot > 2) cols.push({ label: 'OT', away: sum(a), home: sum(h) });
    else for (var i = 0; i < ot; i++) cols.push({ label: 'OT' + (i + 1), away: v(a[4 + i]), home: v(h[4 + i]) });
    return cols;
  }

  // ── Shared bits ──
  function teams(g, ctx) {
    var meta = (ctx && ctx.meta) || function () { return {}; };
    var am = meta(g.away) || {}, hm = meta(g.home) || {};
    var hc = hm.primary && TV ? TV.readable(hm.primary, { light: false, surface: CARD }) : NEUTRAL;
    var ac = am.primary && TV ? (hm.primary ? TV.distinguish(am, hm.primary, { light: false, surface: CARD })
                                            : TV.readable(am.primary, { light: false, surface: CARD })) : NEUTRAL;
    var abbr = function (m, name) { return m.abbr || String(name || '???').slice(0, 3).toUpperCase(); };
    var rank = (ctx && ctx.rank) || function () { return null; };
    var ap = g.away_points || 0, hp = g.home_points || 0;
    return {
      away: { side: 'away', name: g.away, abbr: abbr(am, g.away), color: ac, pts: ap, lead: ap >= hp, rank: rank(g.away) },
      home: { side: 'home', name: g.home, abbr: abbr(hm, g.home), color: hc, pts: hp, lead: hp >= ap, rank: rank(g.home) },
    };
  }

  function spreadText(g, t) {
    if (g.spread == null) return '';
    if (g.spread === 0) return 'PK';
    return (g.spread < 0 ? t.home.abbr : t.away.abbr) + ' -' + Math.abs(g.spread);
  }
  function mlText(n) { return n == null ? '—' : (n > 0 ? '+' : '') + n; }
  function weatherText(w) {
    if (!w || w.temperature == null) return '';
    var s = Math.round(w.temperature) + '°';
    if (w.description) s += ' ' + w.description.toLowerCase();
    if (w.wind_speed) s += ', wind ' + Math.round(w.wind_speed) + ' mph';
    return s;
  }
  function staleText(ctx) {
    var age = ctx && ctx.age;
    if (!(age > STALE_MS)) return '';
    return 'Updated ' + Math.floor(age / 60000) + 'm ago';
  }

  // Score flash + screen-reader announcements. Cards re-render as HTML on each
  // poll, so an aria-live region inside them would be replaced, not updated;
  // one persistent polite region announces the changes instead.
  var seen = {};
  var pending = [];
  function changed(key, value) {
    var prev = seen[key];
    seen[key] = value;
    return prev != null && prev !== value;
  }
  function announce(msg) {
    if (typeof document === 'undefined' || !msg) return;
    if (!pending.length) setTimeout(function () {
      var el = document.getElementById('gc-announcer');
      if (!el) {
        el = document.createElement('div');
        el.id = 'gc-announcer';
        el.className = 'sr-only';
        el.setAttribute('aria-live', 'polite');
        document.body.appendChild(el);
      }
      el.textContent = pending.join('. ');
      pending = [];
    }, 0);
    pending.push(msg);
  }
  function scoreFlash(g, t) {
    var hit = changed('score|' + g.home + '|' + g.away, t.away.pts + '-' + t.home.pts);
    if (hit) announce(t.away.name + ' ' + t.away.pts + ', ' + t.home.name + ' ' + t.home.pts);
    return hit ? ' gc-flash' : '';
  }

  function cell(v) {
    return v == null ? '<td class="gc-q"><span class="gc-dim" aria-hidden="true">—</span><span class="sr-only">not played</span></td>'
                     : '<td class="gc-q">' + v + '</td>';
  }

  // ── Front page: high-contrast, labeled ──
  function front(g, ctx) {
    ctx = ctx || {};
    var t = teams(g, ctx), pre = g.status === 'scheduled', fin = g.status === 'completed';
    var cols = periodCols(g), flash = pre ? '' : scoreFlash(g, t);
    var stale = g.status === 'in_progress' ? staleText(ctx) : '';
    var band = '<div class="gc-band' + (pre || fin ? ' is-quiet' : '') + '">' +
      '<span>' + esc(statusText(g)).replace('●', '<span class="gc-dot" aria-hidden="true">●</span>') +
        (stale ? ' <span class="gc-stale">' + stale + '</span>' : '') + '</span>' +
      (g.tv ? '<span class="gc-net">' + esc(g.tv) + '</span>' : '') + '</div>';

    var row = function (s) {
      return '<tr class="' + (s.lead ? 'is-lead' : 'is-trail') + '">' +
        '<th scope="row"><span class="gc-team"><span class="gc-swatch" style="background:' + s.color + '"></span>' +
        esc(s.name) + (s.rank ? ' <span class="gc-rank">#' + s.rank + '</span>' : '') + '</span></th>' +
        cols.map(function (c) { return cell(c[s.side]); }).join('') +
        '<td class="gc-score' + flash + '">' + s.pts + '</td></tr>';
    };
    var lines = pre ? '' : '<table class="gc-ls"><caption class="sr-only">Score by quarter</caption><thead><tr>' +
      '<th scope="col">Team</th>' + cols.map(function (c) { return '<th scope="col" class="gc-q">' + c.label + '</th>'; }).join('') +
      '<th scope="col" class="gc-score-h">Score</th></tr></thead><tbody>' + row(t.away) + row(t.home) + '</tbody></table>';

    var wpBlock;
    var pred = ctx.pred;
    if (fin) {
      wpBlock = '';
      if (pred) {
        var winner = t.home.pts > t.away.pts ? t.home : t.away, loser = winner === t.home ? t.away : t.home;
        var hit = winner.name === pred.predicted_winner;
        var conf = Math.round(Math.max(pred.home_win_probability, pred.away_win_probability));
        wpBlock = '<p class="gc-call">Model picked <b>' + esc(pred.predicted_winner) + '</b> (' + conf + '%) · ' +
          esc(winner.name) + ' won ' + winner.pts + '–' + loser.pts + ' · <b>' + (hit ? 'Correct' : 'Missed') + '</b></p>';
      }
    } else {
      var hp = pre ? (pred ? pred.home_win_probability / 100 : null) : g.home_win_prob;
      if (hp == null) {
        wpBlock = '<p class="gc-caption">Win probability unavailable</p>';
      } else {
        var a = ((1 - hp) * 100).toFixed(1), h = (hp * 100).toFixed(1);
        wpBlock = '<div class="gc-wp"><div class="gc-wp-row">' +
          '<span><span class="gc-short">' + esc(t.away.abbr) + ' </span><b>' + a + '%</b><span class="gc-long"> ' + esc(t.away.name) + ' wins</span></span>' +
          '<span><span class="gc-long">' + esc(t.home.name) + ' wins </span><span class="gc-short">' + esc(t.home.abbr) + ' </span><b>' + h + '%</b></span></div>' +
          '<div class="gc-wpbar" aria-hidden="true"><span style="flex:' + a + ';background:' + t.away.color + '"></span>' +
          '<span style="flex:' + h + ';background:' + t.home.color + '"></span><i></i></div>' +
          '<p class="gc-caption">' + (pre ? 'Pregame model win probability (Staturday)' : 'Live win probability (CFBD)') + '</p></div>';
      }
    }

    var play = '';
    if (!pre && g.last_play) {
      var lp = cleanPlay(g.last_play);
      play = '<div class="gc-play"><div class="gc-label">Last play' + (lp.clock ? ' (' + lp.clock + ')' : '') + '</div>' +
        '<p>' + esc(lp.text) + '</p></div>';
    }

    var odds = [['Spread', spreadText(g, t) || '—'], ['Over/Under', g.over_under != null ? g.over_under : '—'],
      ['Moneyline', g.home_ml == null && g.away_ml == null ? '—' :
        t.away.abbr + ' ' + mlText(g.away_ml) + ' / ' + t.home.abbr + ' ' + mlText(g.home_ml)]];
    var wx = weatherText(g.weather);
    if (wx) odds.push(['Weather', wx]);
    var grid = '<dl class="gc-odds" style="--n:' + odds.length + '">' + odds.map(function (o) {
      return '<div><dt class="gc-label">' + o[0] + '</dt><dd>' + esc(o[1]) + '</dd></div>';
    }).join('') + '</dl>';

    var body = band + '<div class="gc-body">' + lines + wpBlock + play + grid + '</div>';
    return ctx.href
      ? '<a class="gc gc-front" href="' + esc(ctx.href) + '">' + body + '</a>'
      : '<article class="gc gc-front">' + body + '</article>';
  }

  // ── Games view: situation card ──
  function games(g, ctx) {
    ctx = ctx || {};
    var t = teams(g, ctx), pre = g.status === 'scheduled', fin = g.status === 'completed';
    var live = g.status === 'in_progress', brk = isBreak(g);
    var flash = pre ? '' : scoreFlash(g, t);
    var neutral = g.neutral_site || (ctx.pred && ctx.pred.is_neutral_site);
    var stale = live ? staleText(ctx) : '';

    var side = function (s) {
      var sub = live && !brk && g.possession === s.side ? '<span class="gc-ball-sub">● BALL</span>'
        : neutral ? 'Neutral' : s.side === 'home' ? 'Home' : 'Away';
      return '<div class="gc-side gc-' + s.side + (s.lead ? ' is-lead' : ' is-trail') + '">' +
        '<span class="gc-bar" style="background:' + s.color + '"></span>' +
        '<div class="gc-nm"><div class="gc-name">' + esc(s.name) + '</div><div class="gc-sub">' + sub + '</div></div>' +
        (pre ? '' : '<div class="gc-pts' + flash + '"><span class="sr-only">' + esc(s.name) + ' </span>' + s.pts + '</div>') + '</div>';
    };
    var head = '<div class="gc-head">' + side(t.away) +
      '<div class="gc-clock"><div class="gc-time">' + esc(clockLabel(g)) + '</div>' +
        (g.tv ? '<div class="gc-net">' + esc(g.tv) + '</div>' : '') +
        (stale ? '<div class="gc-stale">' + stale + '</div>' : '') + '</div>' +
      side(t.home) + '</div>';

    var sitLine = '', field = '';
    if (live) {
      var sit = parseSituation(g.situation);
      var spot = !brk && fieldSpot(sit, g.possession, t.away.abbr, t.home.abbr);
      if (brk) sitLine = '<span class="gc-dd">' + breakText(g) + '</span>';
      else if (sit) {
        var poss = g.possession === 'away' ? t.away : g.possession === 'home' ? t.home : null;
        sitLine = '<span class="gc-dd">' + esc(sit.text) + '</span> <span class="gc-spot">at ' +
          (sit.side ? esc(sit.side) + ' ' : '') + sit.yard + '</span>' +
          (poss && spot ? '<span class="gc-dir">' + (spot.dir > 0 ? esc(poss.abbr) + ' DRIVING →' : '← ' + esc(poss.abbr) + ' DRIVING') + '</span>' : '');
      } else {
        var st = specialTeams(g);
        if (st) sitLine = '<span class="gc-dd">' + st + '</span>';
      }
      if (sitLine && changed('sit|' + g.home + '|' + g.away, g.situation || '')) {
        announce(t.away.abbr + ' at ' + t.home.abbr + ': ' + (g.situation || ''));
      }
      if (spot) field = fieldHtml(sit, spot, t);
    }

    var cols = periodCols(g);
    var lsRow = function (s) {
      return '<tr><th scope="row">' + esc(s.abbr) + '</th>' + cols.map(function (c) { return cell(c[s.side]); }).join('') +
        '<td class="gc-tot">' + s.pts + '</td></tr>';
    };
    var lsTile = '<div class="gc-tile"><div class="gc-label">Linescore</div><table class="gc-mini">' +
      '<caption class="sr-only">Score by quarter</caption><thead><tr><th scope="col"><span class="sr-only">Team</span></th>' +
      cols.map(function (c) { return '<th scope="col">' + c.label + '</th>'; }).join('') + '<th scope="col">T</th></tr></thead>' +
      '<tbody>' + lsRow(t.away) + lsRow(t.home) + '</tbody></table></div>';

    var wp = g.home_win_prob, wpTile;
    if (wp == null) wpTile = '<div class="gc-tile"><div class="gc-label">Live win prob · CFBD</div><div class="gc-big">—</div></div>';
    else {
      var lead = wp >= 0.5 ? t.home : t.away, lp = (Math.max(wp, 1 - wp) * 100).toFixed(1);
      wpTile = '<div class="gc-tile"><div class="gc-label">Live win prob · CFBD</div>' +
        '<div class="gc-big">' + esc(lead.abbr) + ' ' + lp + '%</div>' +
        '<div class="gc-minibar" aria-hidden="true"><span style="flex:' + (1 - wp) + ';background:' + t.away.color + '"></span>' +
        '<span style="flex:' + wp + ';background:' + t.home.color + '"></span></div></div>';
    }

    var vegas = [spreadText(g, t) ? 'Vegas ' + spreadText(g, t) : '', g.over_under != null ? 'O/U ' + g.over_under : '']
      .filter(Boolean).join(' · ') || 'No line';
    var p = ctx.pred, model = '';
    if (p) {
      var margin = Math.abs(p.predicted_home_score - p.predicted_away_score).toFixed(1);
      var fav = p.predicted_winner === t.home.name ? t.home.abbr : p.predicted_winner === t.away.name ? t.away.abbr : p.predicted_winner;
      model = '<div class="gc-model">Model ' + esc(fav) + ' -' + margin + ' · ' + esc(String(p.confidence).toUpperCase()) + '</div>';
    }
    var preTile = '<div class="gc-tile"><div class="gc-label">Pregame</div><div class="gc-val">' + esc(vegas) + '</div>' + model + '</div>';

    var tiles = pre ? [preTile] : fin ? [lsTile, preTile] : [wpTile, lsTile, preTile];
    return '<article class="gc gc-games"' + (ctx.id ? ' id="' + esc(ctx.id) + '"' : '') + '>' + head +
      (sitLine ? '<div class="gc-sit">' + sitLine + '</div>' : '') + field +
      '<div class="gc-tiles" style="--n:' + tiles.length + '">' + tiles.join('') + '</div></article>';
  }

  function fieldHtml(sit, spot, t) {
    var poss = spot.dir > 0 ? t.away : t.home, def = spot.dir > 0 ? t.home : t.away;
    var where = sit.yard === 50 ? 'the 50' : 'the ' + (sit.side.toUpperCase() === t.away.abbr.toUpperCase() ? t.away.name : t.home.name) + ' ' + sit.yard;
    var label = poss.name + ' ball, ' + sit.text.replace(' & ', ' and ').replace('Goal', 'goal') + ' at ' + where +
      ', driving toward the ' + def.name + ' end zone.';
    var bands = '';
    for (var i = 0; i < 10; i++) {
      var n = i ? (i <= 5 ? i * 10 : 100 - i * 10) : '';
      bands += '<span class="gc-band10">' + (n ? '<b' + (n % 20 && n !== 50 ? ' class="gc-odd"' : '') + '>' + n + '</b>' : '') + '</span>';
    }
    return '<div class="gc-field" role="img" aria-label="' + esc(label) + '">' +
      '<span class="gc-ez" style="--team:' + t.away.color + '"><b>' + esc(t.away.abbr) + '</b></span>' + bands +
      '<span class="gc-ez" style="--team:' + t.home.color + '"><b>' + esc(t.home.abbr) + '</b></span>' +
      '<span class="gc-los" style="left:' + spot.ball.toFixed(2) + '%"></span>' +
      '<span class="gc-ltg" style="left:' + spot.ltg.toFixed(2) + '%"></span>' +
      '<span class="gc-pigskin" style="left:' + spot.ball.toFixed(2) + '%"></span></div>' +
      '<div class="gc-legend" aria-hidden="true"><span><i class="gc-k-los"></i>Line of scrimmage</span>' +
      '<span><i class="gc-k-ltg"></i>Line to gain</span></div>';
  }

  var api = {
    front: front, games: games,
    statusText: statusText, clockLabel: clockLabel, parseSituation: parseSituation,
    fieldSpot: fieldSpot, cleanPlay: cleanPlay, periodCols: periodCols, specialTeams: specialTeams,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.GameCard = api;
})();
