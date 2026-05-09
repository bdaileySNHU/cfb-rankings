#!/usr/bin/env python3
"""
EPIC-037: Populate ESPN team IDs in the database.

Maps team names to ESPN's integer team IDs so the frontend can serve
CDN logos from:  https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png

Run from project root:
    python3 utilities/populate_espn_ids.py

The script matches DB team names to the ESPN map using exact match first,
then a case-insensitive contains fallback.  Teams with no match are skipped
and reported at the end so you can add them manually.
"""

import sqlite3
import sys

# ---------------------------------------------------------------------------
# ESPN team ID map  (team name variants → ESPN integer ID)
# ---------------------------------------------------------------------------
ESPN_MAP = {
    # ── SEC ─────────────────────────────────────────────────────────────────
    "Alabama": 333,
    "Arkansas": 8,
    "Auburn": 2,
    "Florida": 57,
    "Georgia": 61,
    "Kentucky": 96,
    "LSU": 99,
    "Mississippi State": 344,
    "Ole Miss": 145,
    "Missouri": 142,
    "South Carolina": 2579,
    "Tennessee": 2633,
    "Texas": 251,
    "Texas A&M": 245,
    "Vanderbilt": 238,

    # ── Big Ten ──────────────────────────────────────────────────────────────
    "Illinois": 356,
    "Indiana": 84,
    "Iowa": 2294,
    "Maryland": 120,
    "Michigan": 130,
    "Michigan State": 127,
    "Minnesota": 135,
    "Nebraska": 158,
    "Northwestern": 77,
    "Ohio State": 194,
    "Penn State": 213,
    "Purdue": 2509,
    "Rutgers": 164,
    "Wisconsin": 275,
    "Oregon": 2483,
    "Washington": 264,
    "UCLA": 26,
    "USC": 30,

    # ── Big 12 ───────────────────────────────────────────────────────────────
    "Arizona": 12,
    "Arizona State": 9,
    "Baylor": 239,
    "BYU": 252,
    "Cincinnati": 2132,
    "Colorado": 38,
    "Houston": 248,
    "Iowa State": 66,
    "Kansas": 2305,
    "Kansas State": 2306,
    "Oklahoma State": 197,
    "TCU": 2628,
    "Texas Tech": 2641,
    "UCF": 2116,
    "Central Florida": 2116,
    "Utah": 254,
    "West Virginia": 277,

    # ── ACC ──────────────────────────────────────────────────────────────────
    "Boston College": 103,
    "California": 25,
    "Cal": 25,
    "Clemson": 228,
    "Duke": 150,
    "Florida State": 52,
    "Georgia Tech": 59,
    "Louisville": 97,
    "Miami": 2390,
    "Miami (FL)": 2390,
    "NC State": 152,
    "North Carolina": 153,
    "Notre Dame": 87,
    "Pittsburgh": 221,
    "Pitt": 221,
    "SMU": 2567,
    "Stanford": 24,
    "Syracuse": 183,
    "Virginia": 258,
    "Virginia Tech": 259,
    "Wake Forest": 154,

    # ── Mountain West ────────────────────────────────────────────────────────
    "Air Force": 2005,
    "Boise State": 68,
    "Colorado State": 36,
    "Fresno State": 278,
    "Hawaii": 62,
    "Nevada": 2440,
    "New Mexico": 2443,
    "San Diego State": 21,
    "San Jose State": 23,
    "UNLV": 2439,
    "Utah State": 328,
    "Wyoming": 2751,

    # ── American (AAC) ───────────────────────────────────────────────────────
    "Army": 349,
    "Army West Point": 349,
    "Charlotte": 2429,
    "East Carolina": 151,
    "Florida Atlantic": 2226,
    "FAU": 2226,
    "Memphis": 235,
    "Navy": 2426,
    "North Texas": 249,
    "Rice": 242,
    "South Florida": 58,
    "USF": 58,
    "Temple": 218,
    "Tulane": 2655,
    "Tulsa": 202,
    "UAB": 2530,
    "UTSA": 2073,
    "Wichita State": 2724,

    # ── Sun Belt ─────────────────────────────────────────────────────────────
    "Appalachian State": 2026,
    "App State": 2026,
    "Arkansas State": 18,
    "Coastal Carolina": 324,
    "Georgia Southern": 290,
    "Georgia State": 2247,
    "James Madison": 2348,
    "Louisiana": 309,
    "Louisiana Lafayette": 309,
    "UL Lafayette": 309,
    "Louisiana Monroe": 2433,
    "UL Monroe": 2433,
    "Marshall": 276,
    "Middle Tennessee": 2393,
    "MTSU": 2393,
    "Old Dominion": 2463,
    "South Alabama": 6,
    "Texas State": 326,
    "Troy": 2653,

    # ── MAC ──────────────────────────────────────────────────────────────────
    "Akron": 2006,
    "Ball State": 2050,
    "Bowling Green": 189,
    "Buffalo": 2084,
    "Central Michigan": 2117,
    "Eastern Michigan": 2199,
    "Kent State": 2309,
    "Miami (OH)": 193,
    "Miami Ohio": 193,
    "Northern Illinois": 2459,
    "Ohio": 195,
    "Toledo": 2649,
    "Western Michigan": 2711,

    # ── C-USA ────────────────────────────────────────────────────────────────
    "FIU": 2229,
    "Florida International": 2229,
    "Jacksonville State": 55,
    "Kennesaw State": 338,
    "Liberty": 2335,
    "Louisiana Tech": 2348,
    "New Mexico State": 2441,
    "Sam Houston": 2534,
    "Sam Houston State": 2534,
    "UTEP": 2638,
    "Western Kentucky": 98,

    # ── Independents ─────────────────────────────────────────────────────────
    "Connecticut": 41,
    "UConn": 41,
    "UMass": 113,
    "Massachusetts": 113,
}


def main():
    conn = sqlite3.connect("cfb_rankings.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM teams ORDER BY name")
    teams = cursor.fetchall()

    updated = 0
    skipped = []

    for team_id, name in teams:
        espn_id = None

        # 1. Exact match
        if name in ESPN_MAP:
            espn_id = ESPN_MAP[name]
        else:
            # 2. Case-insensitive exact
            name_lower = name.lower()
            for key, val in ESPN_MAP.items():
                if key.lower() == name_lower:
                    espn_id = val
                    break

        if espn_id:
            cursor.execute(
                "UPDATE teams SET espn_id = ? WHERE id = ?",
                (espn_id, team_id),
            )
            updated += 1
            print(f"  ✓ {name:40s} → ESPN ID {espn_id}")
        else:
            skipped.append(name)

    conn.commit()
    conn.close()

    print()
    print(f"=" * 70)
    print(f"Updated: {updated} teams")
    if skipped:
        print(f"No ESPN ID found for {len(skipped)} teams:")
        for name in skipped:
            print(f"  - {name}")
    print("=" * 70)
    print("Done. Restart the API service to serve updated team data.")


if __name__ == "__main__":
    main()
