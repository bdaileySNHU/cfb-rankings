# EPIC-026 Phase 1 Deployment - Quick Checklist

**Quick reference for deploying Transfer Portal Rankings to production**

---

## Pre-Flight Check (Local Machine)

```bash
cd "/Users/bryandailey/Stat-urday Synthesis"

# 1. Verify commit
git log --oneline -1
# Expected: 2d9befd Complete EPIC-026 Phase 1

# 2. Push to remote
git push origin main
```

---

## Production Deployment (SSH to Server)

```bash
# 1. SSH to server
ssh cfb

# 2. Navigate to app directory
cd /var/www/cfb-rankings

# 3. Backup database
cp cfb_rankings.db cfb_rankings.db.backup_epic26_$(date +%Y%m%d_%H%M%S)
ls -lh cfb_rankings.db.backup_epic26_*

# 4. Stop service
sudo systemctl stop cfb-rankings
sudo systemctl status cfb-rankings  # Verify stopped

# 5. Pull code
git pull origin main
git log --oneline -1  # Verify 2d9befd

# 6. Run migration
sudo python3 migrate_add_transfer_portal_fields.py
# Expected: "MIGRATION COMPLETE" message

# 7. Verify migration
sqlite3 cfb_rankings.db "PRAGMA table_info(teams);" | grep -E "transfer_portal|transfer_count"
# Should show 3 columns

# 8. Check API key
echo $CFBD_API_KEY
# If empty: export CFBD_API_KEY='your-key-here'

# 9. Re-import data
echo "yes" | python3 import_real_data.py
# Look for: "Fetching transfer portal data..." and "Loaded transfer data for 297 teams"

# 10. Verify data populated
sqlite3 cfb_rankings.db "SELECT name, transfer_portal_rank, transfer_portal_points FROM teams WHERE transfer_portal_rank <= 5 ORDER BY transfer_portal_rank;"
# Should see Colorado, Georgia, Alabama, etc.

# 11. Restart service
sudo systemctl restart cfb-rankings
sudo systemctl status cfb-rankings  # Should show "active (running)"

# 12. Test API
curl http://localhost:8000/api/rankings | head -20
# Should return JSON rankings

# 13. Check logs
sudo journalctl -u cfb-rankings -n 50 --no-pager
# Look for: No errors
```

---

## Verification Checklist

After deployment, verify:

- [ ] Service running: `sudo systemctl status cfb-rankings`
- [ ] API responding: `curl http://localhost:8000/api/rankings`
- [ ] Transfer data populated: Top teams have ranks 1-5, not 999
- [ ] No errors in logs: `sudo journalctl -u cfb-rankings -n 50`

---

## If Something Goes Wrong

### Rollback
```bash
sudo systemctl stop cfb-rankings
cp cfb_rankings.db.backup_epic26_TIMESTAMP cfb_rankings.db
git reset --hard HEAD~1
sudo systemctl start cfb-rankings
```

### Re-run Import Only
```bash
echo "yes" | python3 import_real_data.py
```

---

## Expected Results

**Migration Output:**
```
✓ Added transfer_portal_points
✓ Added transfer_portal_rank
✓ Added transfer_count
MIGRATION COMPLETE
```

**Import Output:**
```
Fetching transfer portal data...
Calculating transfer portal rankings...
Loaded transfer data for 297 teams
```

**Top 5 Teams (2024 example):**
```
Colorado        | 1  | 2540 | 41
Georgia         | 2  | 2380 | 35
Alabama         | 3  | 2210 | 32
...
```

---

## Time Estimate

- Pre-flight: 2 minutes
- Deployment: 10-15 minutes
  - Migration: 1 minute
  - Import: 5-10 minutes
  - Verification: 2-3 minutes

**Total: ~15-20 minutes**

---

## Support

If issues arise:
1. Check logs: `sudo journalctl -u cfb-rankings -n 100`
2. Verify database: `sqlite3 cfb_rankings.db "PRAGMA integrity_check;"`
3. Test API key: `curl -H "Authorization: Bearer $CFBD_API_KEY" "https://api.collegefootballdata.com/player/portal?year=2024" | head -50`
4. Review full deployment guide: `docs/EPIC-026-PHASE-1-DEPLOYMENT.md`

---

**Version:** 1.0
**Created:** 2025-12-04
