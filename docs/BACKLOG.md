# Feature Backlog

Planned epics not yet scheduled. Ordered roughly by priority.

---

## EPIC-034: Head-to-Head Comparison Page
**Effort:** Medium (3–4 stories)

Dedicated page to compare any two teams side-by-side:
- Overlaid ELO history SVG chart for the season
- Head-to-head all-time record (if data available)
- Side-by-side stat cards (ELO, record, SOS, preseason rating)
- Live win-probability calculator pre-seeded with both teams' current ratings
- URL scheme: `comparison.html?teamA=61&teamB=333`

---

## EPIC-035: Automated Weekly Updates (Cron + Monitoring)
**Effort:** Medium (3 stories)

Extend Story 33.3 into a full monitoring system:
- Slack/email/push notification when weekly import completes or fails
- Dashboard card on the admin view showing last import status
- Retry logic for failed CFBD API calls
- Diff report: which teams moved ≥10 spots after a weekly update

---

## EPIC-036: Share & Social Features
**Effort:** Small–Medium (2–3 stories)

- Generate a shareable top-25 image card (Canvas API or server-side)
- Open Graph meta tags on team pages for rich link previews
- Clean team URL slugs (`/teams/georgia` → redirects to `team.html?id=61`)
- "Copy link" button on prediction cards

---

## EPIC-037: ESPN Team Logo Integration
**Effort:** Small (1–2 stories)
**Logged:** 2026-05-04

Add `espn_id` column to the `Team` model, populate it for all FBS teams,
and serve the real ESPN CDN logos on team cards and the team detail page.
The frontend `renderTeamLogo()` already handles `espn_id` — just needs the
data. Initials avatars remain as fallback.

---

## EPIC-038: Radar Chart — Position Group Strength ✅ Complete
**Effort:** Small (frontend-only — backend endpoint already existed)
**Completed:** 2026-06-06 — see `docs/EPIC-038-POSITION-RADAR.md`

Per-team radar/spider chart showing relative strength across position groups
(QB, RB, WR, TE, OL, DL, LB, DB, ST). Pure SVG, no chart library. Lives on the
team detail page, fed by the existing `/api/teams/{id}/position-strength` endpoint.

---

## EPIC-039: Roster-Based Position Strength ✅ Complete
**Effort:** Medium–Large (6 stories) — see `docs/EPIC-039-ROSTER-BASED-POSITION-STRENGTH.md`
**Logged:** 2026-06-06 · **Completed:** 2026-06-06

Make position strength (the EPIC-038 radar + preseason ELO bonus) reflect each
team's **actual current roster** instead of recruiting-class signings. Pulls CFBD
`/roster`, joins recruiting ratings via athlete-id, and snapshots a
`roster_players` table per season. Fixes three inaccuracies: departed players
still counting, incoming transfers being invisible, and only recent signees being
scored. Prerequisite: backfill recruiting classes 2021–2025 so all class years
resolve a rating.

---

## EPIC-040: Production-Blended Position Strength
**Effort:** Large (6 stories) — see `docs/EPIC-040-PRODUCTION-BLENDED-RATINGS.md`
**Logged:** 2026-06-06

Blend on-field production (CFBD PPA / usage / player season stats) into the
EPIC-039 roster quality score, so position strength reflects what players have
actually done — not just recruiting pedigree. Production covers QB/RB/WR/TE
(PPA), DL/LB/DB (defensive box score), and ST; **OL has no per-player data and
stays on pedigree**. Backward-looking, so freshmen/transfers fall back to
recruiting. Recommendation: build skill-positions-first (PPA), validate top-25
impact, then decide on the noisier defensive phase.

---
