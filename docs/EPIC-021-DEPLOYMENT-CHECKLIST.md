# EPIC-021 Production Deployment Checklist

**Epic:** Quarter-Weighted ELO with Garbage Time Adjustment
**Deployment Date:** _____________
**Deployed By:** _____________
**Server:** Production

---

## Pre-Deployment

- [ ] All 3 stories (21.1, 21.2, 21.3) marked as "Ready for Review"
- [ ] All tests passing locally (107/107)
- [ ] Code committed locally: `a597f5f`
- [ ] Review deployment guide: `docs/EPIC-021-DEPLOYMENT-GUIDE.md`
- [ ] Notify team of deployment window
- [ ] Schedule: Date/Time: _____________

---

## Step 1: Push to Repository

**Local Machine:**

- [ ] `git push origin main`
- [ ] Verify push: `git log origin/main --oneline -1`
- [ ] Commit hash matches: `a597f5f`

**Notes:**
```
Push time: _____________
Commit verified: Yes / No
```

---

## Step 2: Production Server - Pull Code

**SSH into production:**

- [ ] `ssh production-server`
- [ ] `cd /var/www/cfb-rankings`
- [ ] Check current branch: `git branch`
- [ ] `git pull origin main`
- [ ] Verify commit: `git log --oneline -1`
- [ ] Commit shows: "Implement quarter-weighted ELO with garbage time adjustment"

**Notes:**
```
Pull time: _____________
Current commit: _____________
Files changed: 14
Insertions: 3573
```

---

## Step 3: Backup Database

**CRITICAL - DO NOT SKIP**

- [ ] Create backup directory if needed: `mkdir -p /backups`
- [ ] Run backup command:
  ```bash
  # SQLite:
  cp cfb_rankings.db /backups/cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).db

  # PostgreSQL:
  pg_dump -U cfb_user -d cfb_rankings > /backups/cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- [ ] Verify backup file exists: `ls -lh /backups/ | tail -1`
- [ ] Record backup size: _____________ MB

**Backup Location:**
```
File: /backups/cfb_rankings_backup_YYYYMMDD_HHMMSS.db
Size: _____________ MB
Time: _____________
```

---

## Step 4: Run Database Migration

- [ ] Activate venv (if applicable): `source venv/bin/activate`
- [ ] Run migration: `python3 migrate_add_quarter_scores.py`
- [ ] Verify success message: "Migration complete!"
- [ ] Verify columns added:
  ```bash
  sqlite3 cfb_rankings.db "PRAGMA table_info(games);" | grep -E "q[1-4]_(home|away)"
  ```
- [ ] Should see 8 columns: q1_home, q1_away, q2_home, q2_away, q3_home, q3_away, q4_home, q4_away

**Migration Results:**
```
Start time: _____________
End time: _____________
Duration: _____________
Columns added: 8 / 8
Success: Yes / No
Errors (if any): _____________
```

---

## Step 5: Smoke Test (Pre-Backfill)

- [ ] Test API endpoint: `curl http://localhost:8000/api/rankings | head -20`
- [ ] API responds: Yes / No
- [ ] Check app logs: `tail -100 /var/log/cfb-rankings/app.log`
- [ ] No errors in logs: Yes / No
- [ ] Rankings display correctly: Yes / No

**Test Results:**
```
API Status: _____________
Response time: _____________ ms
Errors: _____________
```

---

## Step 6: Backfill Quarter Scores

### Option A: Test Batch First (Recommended)

- [ ] **Dry run test:** `python3 scripts/backfill_quarter_scores.py --dry-run --limit 10`
- [ ] Dry run successful: Yes / No
- [ ] **Small batch:** `python3 scripts/backfill_quarter_scores.py --limit 50`
- [ ] Record results:
  - Total: _____________
  - Backfilled: _____________
  - Unavailable: _____________
  - Failed: _____________
  - Success Rate: _____________%

### Option B: Full Backfill (If test successful)

- [ ] Start screen session: `screen -S backfill`
- [ ] Run backfill: `python3 scripts/backfill_quarter_scores.py`
- [ ] Detach screen: `Ctrl+A, D`
- [ ] Monitor in another terminal: `tail -f /var/log/cfb-rankings/backfill.log`

**Backfill Progress Tracking:**

| Time | Games Processed | Success Rate | Notes |
|------|----------------|--------------|-------|
| _____ | _____ | _____% | _____ |
| _____ | _____ | _____% | _____ |
| _____ | _____ | _____% | _____ |

**Final Backfill Results:**
```
Start time: _____________
End time: _____________
Duration: _____________
Total games: _____________
Successfully backfilled: _____________
Unavailable (no data): _____________
Failed (errors): _____________
Success rate: _____________%

✓ Success rate >= 90%: Yes / No
```

---

## Step 7: Generate Validation Report

- [ ] Run report: `python3 scripts/generate_ranking_comparison_report.py --season 2024 --output /tmp/ranking_comparison_2024.md`
- [ ] Report generated successfully: Yes / No
- [ ] Review report: `less /tmp/ranking_comparison_2024.md`
- [ ] Top 25 comparison looks reasonable: Yes / No
- [ ] Biggest movers make sense: Yes / No
- [ ] Garbage time examples detected: Yes / No
- [ ] No unexpected rank changes (>10 spots): Yes / No

**Report Review:**
```
Report location: /tmp/ranking_comparison_2024.md
Top 25 changes reviewed: Yes / No
Biggest mover: _____________ (change: _____)
Garbage time games detected: _____________
Issues found: _____________
```

---

## Step 8: Restart Application

- [ ] Restart service:
  ```bash
  # Systemd:
  sudo systemctl restart cfb-rankings

  # Or Supervisor:
  sudo supervisorctl restart cfb-rankings
  ```
- [ ] Check status: `sudo systemctl status cfb-rankings`
- [ ] Service active (running): Yes / No
- [ ] Wait 30 seconds for initialization
- [ ] Check logs: `tail -50 /var/log/cfb-rankings/app.log`

**Restart Results:**
```
Restart time: _____________
Service status: _____________
Errors: _____________
```

---

## Step 9: Post-Deployment Validation

### API Tests

- [ ] Rankings endpoint: `curl http://localhost:8000/api/rankings | jq '.[0]'`
- [ ] Response valid JSON: Yes / No
- [ ] Rankings look correct: Yes / No

### Algorithm Verification

- [ ] Check logs for quarter-weighted usage: `tail -100 /var/log/cfb-rankings/app.log | grep -i quarter`
- [ ] Algorithm activated for games with quarter data: Yes / No
- [ ] Fallback to legacy for games without quarters: Yes / No

### Database Check

- [ ] Count games with quarters:
  ```bash
  sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE q1_home IS NOT NULL;"
  ```
- [ ] Games with quarter data: _____________
- [ ] Percentage: _____________%

### Spot Check Rankings

- [ ] Compare top 5 to pre-deployment
- [ ] Changes make sense: Yes / No
- [ ] No major unexpected shifts: Yes / No

**Validation Results:**
```
API Status: OK / ISSUES
Algorithm Status: OK / ISSUES
Database Status: OK / ISSUES
Rankings Status: OK / ISSUES

Issues found:
_____________________________________________
_____________________________________________
```

---

## Step 10: Performance Monitoring

**Initial Check (within 1 hour):**

- [ ] API response time: _____________ ms (baseline: _____ ms)
- [ ] Performance impact: _____________%
- [ ] Impact < 10%: Yes / No
- [ ] Error rate: _____________ (baseline: _____)
- [ ] Database CPU: _____________%
- [ ] Database Memory: _____________%

**Notes:**
```
Performance acceptable: Yes / No
Action needed: _____________
```

---

## Step 11: Update Documentation

- [ ] Update EPIC-021 doc with deployment results:
  - Deployment date: _____________
  - Backfill success rate: _____________%
  - Games with quarters: _____________
- [ ] Commit documentation updates
- [ ] Notify team of successful deployment

---

## Rollback Plan (If Needed)

**Only complete if issues require rollback:**

### Quick Rollback (Algorithm Only)

- [ ] Temporarily disable quarter-weighted algorithm
- [ ] Edit `ranking_service.py`: Set `USE_QUARTER_WEIGHTED_ELO = False`
- [ ] Restart application
- [ ] Verify rankings return to baseline
- [ ] Document issue: _____________

### Full Rollback (Database + Code)

- [ ] Stop application: `sudo systemctl stop cfb-rankings`
- [ ] Restore database backup:
  ```bash
  cp /backups/cfb_rankings_backup_YYYYMMDD_HHMMSS.db cfb_rankings.db
  ```
- [ ] Revert git commit: `git revert a597f5f`
- [ ] Restart application: `sudo systemctl start cfb-rankings`
- [ ] Verify system operational
- [ ] Document rollback reason: _____________

**Rollback Executed:**
```
Time: _____________
Reason: _____________________________________________
Database restored: Yes / No
Code reverted: Yes / No
System operational: Yes / No
```

---

## Sign-Off

**Deployment Status:** ✅ SUCCESS / ⚠️ PARTIAL / ❌ FAILED / 🔄 ROLLED BACK

**Deployed By:** _____________
**Sign-Off Date/Time:** _____________

**Summary:**
```
Total time: _____________
Issues encountered: _____________________________________________
_____________________________________________
_____________________________________________

Resolution: _____________________________________________
_____________________________________________

System status: _____________
Performance impact: _____________%
Backfill success rate: _____________%

Notes for team:
_____________________________________________
_____________________________________________
_____________________________________________
```

**Next Steps:**
- [ ] Monitor system for 24 hours
- [ ] Review error logs daily for first week
- [ ] Collect user feedback on ranking changes
- [ ] Schedule follow-up review meeting: _____________

---

## Emergency Contacts

**Primary:** _____________
**Secondary:** _____________
**Database Admin:** _____________
**On-Call:** _____________

---

## Reference Links

- Epic Documentation: `docs/EPIC-021-QUARTER-WEIGHTED-ELO.md`
- Story 21.1: `docs/stories/21.1.story.md`
- Story 21.2: `docs/stories/21.2.story.md`
- Story 21.3: `docs/stories/21.3.story.md`
- Deployment Guide: `docs/EPIC-021-DEPLOYMENT-GUIDE.md`

---

**Checklist Version:** 1.0
**Last Updated:** 2025-11-18
