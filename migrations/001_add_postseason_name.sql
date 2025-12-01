-- Migration: Add postseason_name field for EPIC-023
-- Date: 2025-12-01
-- Story: 23.1 - Bowl Game Import and Storage

-- Add postseason_name column to games table
-- This stores bowl names (e.g., "Rose Bowl Game") or playoff rounds (e.g., "CFP Semifinal")
ALTER TABLE games ADD COLUMN postseason_name VARCHAR(100) NULL;

-- Verify migration
-- Expected: postseason_name column added, all existing rows have NULL value
SELECT COUNT(*) as total_games,
       COUNT(postseason_name) as games_with_names
FROM games;
