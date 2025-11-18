# EPIC-021 Production Deployment Guide

**Epic:** Quarter-Weighted ELO with Garbage Time Adjustment
**Version:** 1.0
**Last Updated:** 2025-11-18

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Requirements](#pre-deployment-requirements)
3. [Deployment Steps](#deployment-steps)
4. [Validation & Testing](#validation--testing)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Post-Deployment Monitoring](#post-deployment-monitoring)

---

## Overview

### What's Being Deployed

EPIC-021 implements quarter-weighted ELO ranking with garbage time adjustment to improve ranking accuracy.

**Key Changes:**
- Database schema: 8 new nullable columns for quarter scores
- CFBD API integration: Fetch quarter-by-quarter scores
- Ranking algorithm: Process games quarter-by-quarter, reduce 4th quarter weight in blowouts
- Data migration: Backfill historical quarter scores
- Validation tools: Before/after ranking comparison reports

**Impact:**
- Rankings will be more accurate (garbage time inflation removed)
- Teams with blowout wins may drop 3-5 spots
- No user-facing UI changes (backend only)
- Full backward compatibility maintained

---

## Pre-Deployment Requirements

### Code Review

- ✅ All 3 stories completed (21.1, 21.2, 21.3)
- ✅ 107/107 tests passing
- ✅ Code reviewed and approved
- ✅ Commit: `a597f5f`

### System Requirements

- Python 3.x with SQLAlchemy
- Database: SQLite or PostgreSQL
- CFBD API key configured
- Sufficient disk space for backups (estimate: 2x current DB size)

### Access Requirements

- SSH access to production server
- Database backup permissions
- Application restart permissions
- Git repository access

### Preparation

1. **Schedule Deployment Window**
   - Recommended: Off-peak hours (early morning or weekend)
   - Duration: 1-2 hours (includes testing)
   - Notify team of deployment window

2. **Review Checklist**
   - Print or open: `docs/EPIC-021-DEPLOYMENT-CHECKLIST.md`
   - Have rollback plan ready
   - Verify contact information for emergency support

3. **Backup Plan**
   - Ensure backup directory exists: `/backups/`
   - Verify backup script works
   - Test restore procedure on staging (if available)

---

## Deployment Steps

### Step 1: Push Code to Repository

**Location:** Local development machine

```bash
cd "/Users/bryandailey/Stat-urday Synthesis"

# Verify current status
git status
git log --oneline -1

# Push to remote
git push origin main

# Verify push
git log origin/main --oneline -1
# Should show: a597f5f Implement quarter-weighted ELO with garbage time adjustment (EPIC-021)
```

**Validation:**
- Commit hash matches: `a597f5f`
- 14 files changed shown in commit
- No errors during push

---

### Step 2: Pull Code on Production Server

**Location:** Production server

```bash
# SSH into production
ssh your-production-server

# Navigate to application directory
cd /var/www/cfb-rankings  # Adjust path as needed

# Check current state
git status
git log --oneline -1

# Pull latest changes
git pull origin main

# Verify
git log --oneline -1
ls -l scripts/backfill_quarter_scores.py  # Verify new files exist
ls -l scripts/generate_ranking_comparison_report.py
```

**Validation:**
- Pull completed without conflicts
- New files present
- Modified files updated
- Commit message matches

---

### Step 3: Backup Production Database

**CRITICAL STEP - DO NOT SKIP**

```bash
# Create backup directory if needed
mkdir -p /backups

# For SQLite
DB_BACKUP="/backups/cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).db"
cp cfb_rankings.db "$DB_BACKUP"
echo "Backup created: $DB_BACKUP"
ls -lh "$DB_BACKUP"

# For PostgreSQL
DB_BACKUP="/backups/cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -U cfb_user -d cfb_rankings > "$DB_BACKUP"
echo "Backup created: $DB_BACKUP"
ls -lh "$DB_BACKUP"
```

**Validation:**
- Backup file exists
- File size reasonable (similar to current DB)
- Backup timestamp correct

**Store backup path for potential rollback:**
```bash
echo $DB_BACKUP > /tmp/last_backup.txt
```

---

### Step 4: Run Database Migration

**Migration adds 8 quarter score columns to games table**

```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Run migration
python3 migrate_add_quarter_scores.py
```

**Expected Output:**
```
Migration: Adding quarter score columns to games table
Column q1_home added
Column q1_away added
Column q2_home added
Column q2_away added
Column q3_home added
Column q3_away added
Column q4_home added
Column q4_away added
Migration complete!
```

**Verify Migration:**

```bash
# SQLite
sqlite3 cfb_rankings.db "PRAGMA table_info(games);" | grep -E "q[1-4]_(home|away)"

# PostgreSQL
psql -U cfb_user -d cfb_rankings -c "\d games" | grep -E "q[1-4]_(home|away)"
```

**Expected:** 8 lines showing quarter score columns (all nullable)

**If Migration Fails:**
1. Check error message
2. Verify database connection
3. Restore from backup if needed
4. Contact database admin

---

### Step 5: Smoke Test (Pre-Backfill)

**Verify application still works before backfilling data**

```bash
# Test API endpoint
curl http://localhost:8000/api/rankings | head -20

# Should return JSON with rankings
# Verify no errors in response

# Check application logs
tail -100 /var/log/cfb-rankings/app.log

# Look for:
# - No error messages
# - Application started successfully
# - API requests being served
```

**If API Not Responding:**
1. Check service status: `sudo systemctl status cfb-rankings`
2. Check error logs: `tail -100 /var/log/cfb-rankings/error.log`
3. Restart if needed: `sudo systemctl restart cfb-rankings`

---

### Step 6: Run Backfill Script

**This populates quarter scores for historical games**

#### Option A: Test with Small Batch (Recommended First)

```bash
# Dry run (no database changes)
python3 scripts/backfill_quarter_scores.py --dry-run --limit 10

# Review output:
# - Should process 10 games
# - Shows success/failure/unavailable counts
# - No errors

# If dry run looks good, run for real
python3 scripts/backfill_quarter_scores.py --limit 50

# Review results
# - Success rate should be ~85-95%
# - "Unavailable" means CFBD doesn't have quarter data (normal)
# - "Failed" means validation error (investigate if >5%)
```

#### Option B: Full Backfill by Season

```bash
# Most recent complete season first (most important)
python3 scripts/backfill_quarter_scores.py --season 2024

# Then previous seasons
python3 scripts/backfill_quarter_scores.py --season 2023
python3 scripts/backfill_quarter_scores.py --season 2022
python3 scripts/backfill_quarter_scores.py --season 2021
python3 scripts/backfill_quarter_scores.py --season 2020
```

#### Option C: Full Backfill (All Games)

**Warning:** May take 30-60 minutes for 1000+ games

```bash
# Start screen session (survives SSH disconnects)
screen -S backfill

# Run full backfill
python3 scripts/backfill_quarter_scores.py

# Detach from screen: Ctrl+A, then D
# Reattach later: screen -r backfill

# Monitor progress in another terminal
watch -n 5 'sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE q1_home IS NOT NULL;"'
```

**Understanding Backfill Results:**

```
Total games: 1500
Backfilled: 1350 (90%)     ← Quarter data found and stored
Unavailable: 120 (8%)      ← CFBD doesn't have quarter data (normal)
Failed: 30 (2%)            ← Validation errors (investigate if high)
Success rate: 90.0%
```

**Success Criteria:**
- Success rate >= 85%: ✅ Excellent
- Success rate 70-84%: ⚠️ Acceptable (older seasons may lack data)
- Success rate < 70%: ❌ Investigate (possible API or data issue)

---

### Step 7: Generate Validation Report

**Creates before/after ranking comparison**

```bash
# Generate report for most recent season
python3 scripts/generate_ranking_comparison_report.py \
  --season 2024 \
  --output /tmp/ranking_comparison_2024.md

# Review report
less /tmp/ranking_comparison_2024.md

# Or copy to local machine for easier review
scp production-server:/tmp/ranking_comparison_2024.md ~/Desktop/
```

**What to Look For in Report:**

1. **Top 25 Comparison**
   - Expected: Garbage time teams drop 2-5 spots
   - Expected: Defensive teams may rise 2-4 spots
   - Red flag: Any team moves >10 spots without clear reason

2. **Biggest Movers**
   - Should make sense (teams with many blowouts affected most)
   - Document unexpected changes for review

3. **Garbage Time Examples**
   - Verify games detected have >21 point differential after Q3
   - Spot-check a few games to confirm correctness

**Action Items:**
- Review with domain expert if available
- Document any concerns in deployment checklist
- Proceed if changes align with expectations

---

### Step 8: Restart Application

**Apply changes and activate new algorithm**

```bash
# Using systemd
sudo systemctl restart cfb-rankings
sudo systemctl status cfb-rankings

# Using supervisor
sudo supervisorctl restart cfb-rankings
sudo supervisorctl status cfb-rankings

# Using gunicorn directly
pkill -HUP gunicorn
ps aux | grep gunicorn

# Wait 30 seconds for initialization
sleep 30

# Check logs
tail -50 /var/log/cfb-rankings/app.log
```

**Expected in Logs:**
- Application started successfully
- Database connection established
- No error messages
- API endpoints ready

**If Service Fails to Start:**
1. Check error logs: `journalctl -u cfb-rankings -n 100`
2. Verify database connection
3. Check for syntax errors in code
4. Consider rollback if unresolvable

---

### Step 9: Post-Deployment Validation

#### API Testing

```bash
# 1. Test rankings endpoint
curl http://localhost:8000/api/rankings | jq '.[0:5]'

# Expected: JSON array with top 5 teams
# Verify structure looks correct

# 2. Test specific team (if endpoint exists)
curl http://localhost:8000/api/teams/Georgia

# 3. Test health check (if exists)
curl http://localhost:8000/health
```

#### Algorithm Verification

```bash
# Check logs for quarter-weighted algorithm usage
tail -200 /var/log/cfb-rankings/app.log | grep -i "quarter"

# Expected to see:
# - "Using quarter-weighted MOV" for games with quarter data
# - "Falling back to legacy MOV" for games without quarter data
```

#### Database Verification

```bash
# Count games with quarter data
sqlite3 cfb_rankings.db <<EOF
SELECT
  COUNT(*) as total_games,
  SUM(CASE WHEN q1_home IS NOT NULL THEN 1 ELSE 0 END) as with_quarters,
  ROUND(100.0 * SUM(CASE WHEN q1_home IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pct
FROM games;
EOF
```

**Expected:**
- Total games: [count]
- With quarters: 85-95% of total
- Percentage aligns with backfill success rate

#### Spot Check Rankings

Compare current top 10 to pre-deployment snapshot:

```bash
# Get current top 10
curl http://localhost:8000/api/rankings | jq '.[0:10] | .[] | {rank: .rank, team: .team.name, rating: .elo_rating}'

# Compare to pre-deployment snapshot
# Document any unexpected changes
```

---

## Validation & Testing

### Integration Testing

If integration tests exist:

```bash
# Run integration test suite
pytest tests/integration/ -v

# All tests should pass
# Document any failures
```

### Performance Testing

```bash
# Measure API response time
time curl http://localhost:8000/api/rankings > /dev/null

# Compare to baseline
# Expected: <10% increase in response time
```

### Load Testing (Optional)

```bash
# Simple load test with ab (Apache Bench)
ab -n 100 -c 10 http://localhost:8000/api/rankings

# Monitor:
# - Requests per second (should be similar to baseline)
# - 95th percentile latency (<10% increase acceptable)
```

---

## Rollback Procedures

### Quick Rollback: Disable Algorithm Only

**Use when:** Algorithm produces unexpected rankings but database is stable

```bash
# 1. SSH to production
ssh production-server
cd /var/www/cfb-rankings

# 2. Create feature flag file
cat > disable_quarter_weighted.flag <<EOF
# Temporary flag to disable quarter-weighted algorithm
# Created: $(date)
# Reason: [Document reason]
EOF

# 3. Modify ranking_service.py (temporary fix)
# Option A: Add at top of RankingService class
# USE_QUARTER_WEIGHTED_ELO = False

# Option B: Force legacy in process_game()
# Change line checking for quarter data to always return False

# 4. Restart application
sudo systemctl restart cfb-rankings

# 5. Verify rankings return to baseline
curl http://localhost:8000/api/rankings | head -20

# 6. Document issue for investigation
```

**Restore Normal Operation:**
- Fix root cause
- Remove feature flag
- Revert code changes
- Restart application
- Verify rankings

---

### Full Rollback: Database + Code

**Use when:** Database migration causes issues or critical bugs found

```bash
# 1. Stop application
sudo systemctl stop cfb-rankings

# 2. Restore database from backup
DB_BACKUP=$(cat /tmp/last_backup.txt)

# For SQLite
mv cfb_rankings.db cfb_rankings.db.broken_$(date +%Y%m%d_%H%M%S)
cp "$DB_BACKUP" cfb_rankings.db

# For PostgreSQL
dropdb cfb_rankings
createdb cfb_rankings
psql -U cfb_user -d cfb_rankings < "$DB_BACKUP"

# 3. Revert code changes
git log --oneline -5  # Verify commit to revert
git revert a597f5f    # Creates new commit that undoes changes

# Or hard reset (only if not pushed to others)
# git reset --hard HEAD~1

# 4. Restart application
sudo systemctl start cfb-rankings

# 5. Verify system operational
curl http://localhost:8000/api/rankings | head -20
sudo systemctl status cfb-rankings

# 6. Document rollback
cat > /tmp/rollback_report.txt <<EOF
Rollback executed: $(date)
Reason: [Document reason]
Database restored from: $DB_BACKUP
Code reverted: Yes
System status: [OK/Issues]
Next steps: [Document]
EOF
```

---

## Troubleshooting

### Issue: Backfill Shows 0% Success Rate

**Symptoms:**
- All games return "unavailable"
- No quarter scores populated

**Diagnosis:**
```bash
# Check CFBD API key
echo $CFBD_API_KEY

# Test API directly
curl -H "Authorization: Bearer $CFBD_API_KEY" \
  "https://api.collegefootballdata.com/games/teams?year=2024&week=1"
```

**Solutions:**
1. Verify CFBD_API_KEY is set
2. Check API key validity
3. Verify network connectivity to CFBD API
4. Try different season (older seasons may lack data)

---

### Issue: Migration Fails - "Column Already Exists"

**Symptoms:**
```
Error: column q1_home already exists
```

**Diagnosis:**
```bash
# Check if columns already exist
sqlite3 cfb_rankings.db "PRAGMA table_info(games);" | grep q1_home
```

**Solutions:**
1. Migration already ran - verify 8 columns exist
2. If incomplete (only some columns), manually add missing ones
3. If all exist, skip migration and proceed to backfill

---

### Issue: Validation Errors During Backfill

**Symptoms:**
- High "Failed" count in backfill results
- Error: "Quarter scores sum to X, expected Y"

**Diagnosis:**
```bash
# Check logs for specific games
tail -200 /var/log/cfb-rankings/backfill.log | grep "Validation failed"
```

**Solutions:**
1. Acceptable if <5% of games
2. If >5%, investigate specific games
3. May indicate CFBD data quality issues
4. Games with validation errors will have NULL quarters (safe)

---

### Issue: Rankings Show Unexpected Large Changes

**Symptoms:**
- Teams move >10 spots
- Changes don't align with expectations

**Diagnosis:**
1. Review validation report
2. Check specific games for the team
3. Verify quarter score data accuracy

**Solutions:**
1. Review with domain expert
2. May need to adjust GARBAGE_TIME_THRESHOLD
3. Check for data quality issues
4. Consider feature flag to disable temporarily

---

### Issue: Application Performance Degradation

**Symptoms:**
- API response time >15% slower
- Database CPU high

**Diagnosis:**
```bash
# Check API response time
time curl http://localhost:8000/api/rankings > /dev/null

# Check database queries
# SQLite: No built-in slow query log
# PostgreSQL: Check pg_stat_statements
```

**Solutions:**
1. Review database indexes (should not be affected)
2. Check if calculate_quarter_weighted_mov() is being called excessively
3. Consider caching rankings
4. Verify batch size in backfill script (shouldn't affect runtime)

---

## Post-Deployment Monitoring

### First 24 Hours

**Hourly Checks:**
- [ ] API response time: `time curl http://localhost:8000/api/rankings`
- [ ] Error rate: `tail -100 /var/log/cfb-rankings/error.log | wc -l`
- [ ] Service status: `sudo systemctl status cfb-rankings`

**Key Metrics:**
- Response time baseline: _____ ms
- Current response time: _____ ms
- Impact: _____%
- Error count: _____

---

### First Week

**Daily Monitoring:**
- Review error logs for patterns
- Monitor database size growth
- Check for user reports/feedback
- Verify new games process correctly with quarter data

**Weekly Review:**
- Analyze ranking stability
- Review garbage time detection accuracy
- Document any issues or improvements needed
- Team meeting to discuss deployment

---

### Long-term Monitoring

**Ongoing:**
- Monthly review of quarter data coverage
- Quarterly review of algorithm performance
- Update GARBAGE_TIME_THRESHOLD if needed based on data
- Monitor CFBD API changes

---

## Contact Information

**Primary On-Call:** _____________
**Database Admin:** _____________
**DevOps:** _____________
**Emergency:** _____________

---

## Reference Documentation

- Epic: `docs/EPIC-021-QUARTER-WEIGHTED-ELO.md`
- Story 21.1: `docs/stories/21.1.story.md`
- Story 21.2: `docs/stories/21.2.story.md`
- Story 21.3: `docs/stories/21.3.story.md`
- Deployment Checklist: `docs/EPIC-021-DEPLOYMENT-CHECKLIST.md`

---

**Guide Version:** 1.0
**Created:** 2025-11-18
**Last Updated:** 2025-11-18
