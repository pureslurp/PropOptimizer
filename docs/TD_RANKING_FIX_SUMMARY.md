# Passing TD Defensive Ranking Fix Summary

## Problem Identified
All Passing TDs props were showing Team Rank as **16** instead of the correct defensive rankings based on actual TDs allowed by each team.

## Root Causes Found

### 1. Missing TD Ranking Calculation
The `defensive_scraper.py` was collecting raw TD counts from NFL.com but **not calculating rankings** from those counts. It was only ranking ESPN stats (yards and points).

### 2. Double Ranking Conversion
The `enhanced_data_processor.py` had a `_convert_td_counts_to_rankings()` method that was trying to convert what it thought were TD counts into rankings. However, after fixing issue #1, the defensive scraper was already providing rankings, causing a double-conversion that produced incorrect values.

### 3. Team Name Inconsistencies
Different data sources used different team name formats (e.g., "49ers" vs "San Francisco 49ers" vs "SF"), potentially causing team matching issues.

## Solutions Implemented

### 1. Created Team Name Normalization Utility (`team_name_utils.py`)
- Comprehensive `TeamNameNormalizer` class with mappings for all team name variations
- Handles abbreviations (SF, KC, etc.), short names (49ers, Chiefs), and full names
- Provides bidirectional conversion (full name ↔ abbreviation)
- Includes legacy team names (e.g., "Oakland Raiders" → "Las Vegas Raiders")

### 2. Updated Defensive Scraper (`defensive_scraper.py`)
- Added `_calculate_td_rankings()` method to properly rank teams by TDs allowed
- Fewer TDs allowed = better defense = lower rank number (Rank 1 is best)
- Integrated team name normalization utility for consistent team matching
- Both raw TD counts AND rankings are now properly calculated and stored

### 3. Fixed Enhanced Data Processor (`enhanced_data_processor.py`)
- Removed redundant `_convert_td_counts_to_rankings()` call
- Now correctly uses rankings already provided by defensive scraper
- Updated to use normalized team names

## Verification Results

After fixes, TD rankings are now correct:

| Team | TDs Allowed | Correct Rank |
|------|-------------|--------------|
| Houston Texans | 3 | 1 (best) |
| LA Chargers | 4 | 2 |
| Denver Broncos | 4 | 3 |
| San Francisco 49ers | 8 | 17 (middle) |
| Baltimore Ravens | 13 | 32 (worst) |

## Data Source
Rankings calculated from NFL.com official stats:
https://www.nfl.com/stats/team-stats/defense/passing/2025/reg/all

## How Rankings Work

### Defensive Rankings Logic
- **Lower rank = Better defense** (Rank 1 is the best)
- **For TDs Allowed**: Fewer TDs allowed = better defense = lower rank
  - Team allowing 3 TDs = Rank 1 (best)
  - Team allowing 13 TDs = Rank 32 (worst)

### Scoring Impact
- The `scoring_model.py` uses these rankings to calculate matchup scores
- Higher defensive rank (worse defense) = better matchup for offense = higher score
- Example: Rank 32 defense (worst) gives a high score for the offensive player

## Files Modified
1. `team_name_utils.py` - NEW: Comprehensive team name normalization
2. `defensive_scraper.py` - Added TD ranking calculation, integrated team name normalization
3. `enhanced_data_processor.py` - Removed double-conversion bug
4. `player_prop_optimizer.py` - Now sorts by Score (descending) by default

## Testing
- Verified rankings match NFL.com official data
- Tested team name normalization for all 32 teams
- Confirmed data processor retrieves correct rankings
- All linter checks pass

## Next Steps
- Run `python3 defensive_scraper.py --force` weekly to update TD statistics
- The prop optimizer will now show accurate defensive rankings for Passing TDs
- Rankings for Rushing TDs are also fixed using the same methodology

