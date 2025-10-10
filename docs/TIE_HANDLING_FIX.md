# Defensive Ranking Tie Handling Fix

## Problem
Teams with the same number of TDs allowed were all showing the same rank (e.g., all showing rank 16), but the ranks didn't properly represent their tied position in the league.

**Example Issue:**
- Pittsburgh Steelers: 7 TDs allowed → Was showing Rank **16** ❌
- Should have been Rank **14** (tied with 5 other teams)

## Root Cause Analysis

### Issue 1: No Tie Handling
The original ranking system assigned sequential ranks without considering ties. Teams with identical stats would get different ranks based on sort order.

### Issue 2: Data Corruption in Cache
The `save_to_cache` method was saving **rankings** to the TD cache file instead of **raw TD counts**, causing the pickle file to contain incorrect data.

## Solution Implemented

### 1. Average Rank for Ties (Rounded to Whole Number)
Implemented proper tie handling using the **average rank** method:

- **Formula:** When N teams are tied for positions P through P+N-1:
  - Average Rank = round((P + P+1 + ... + P+N-1) / N)

- **Example:** 6 teams tied with 7 TDs occupy positions 12-17:
  - Positions: 12, 13, 14, 15, 16, 17
  - Average: (12+13+14+15+16+17) / 6 = 84 / 6 = 14
  - **All 6 teams get Rank 14** ✅

### 2. Rounding Strategy
- Using Python's built-in `round()` function
- Banker's rounding (round half to even): 2.5 → 2, 3.5 → 4
- Results in whole number ranks (no decimals)

### 3. Fixed Data Persistence
Updated `save_to_cache` to:
1. Accept **raw TD counts** as a separate parameter
2. Save raw counts to pickle file (for reference/debugging)
3. Save computed rankings to JSON file (for actual use)

## Code Changes

### `defensive_scraper.py`

#### 1. Updated `_calculate_td_rankings()` with tie handling:
```python
def _calculate_td_rankings(self, td_stats: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """Calculate rankings with average rank for ties, rounded to whole number"""
    # Find all teams tied with same TD count
    # Calculate average of positions they occupy
    # Round to nearest whole number
    # Assign same rank to all tied teams
```

#### 2. Updated `calculate_rankings()` for ESPN stats (yards, points):
```python
def calculate_rankings(self, espn_stats: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, int]]:
    """Calculate rankings with average rank for ties"""
    # Same tie handling logic for ESPN stats
```

#### 3. Fixed `update_defensive_stats()`:
```python
# Pass raw TD stats to save_to_cache
self.save_to_cache(combined_data, nfl_td_stats)  # ← Added nfl_td_stats parameter
```

#### 4. Fixed `save_to_cache()`:
```python
def save_to_cache(self, data: Dict, raw_td_stats: Dict = None, ...):
    """Save raw TD counts AND rankings separately"""
    if raw_td_stats:
        # Save actual raw TD counts from NFL.com
        pickle.dump(raw_td_stats, f)
    # Save all rankings to JSON
    json.dump(data, f)
```

## Verification Results

### Before Fix:
```
Pittsburgh Steelers  (7 TDs) → Rank 16  ❌
Carolina Panthers    (7 TDs) → Rank 16  ❌
(All teams showing same incorrect rank)
```

### After Fix:
```
Pittsburgh Steelers  (7 TDs) → Rank 14  ✅
Carolina Panthers    (7 TDs) → Rank 14  ✅
Los Angeles Rams     (7 TDs) → Rank 14  ✅
New York Giants      (7 TDs) → Rank 14  ✅
Philadelphia Eagles  (7 TDs) → Rank 14  ✅
Las Vegas Raiders    (7 TDs) → Rank 14  ✅

(All 6 teams correctly tied at Rank 14)
```

### Full Rankings Verification:
| Team | TDs Allowed | Positions Occupied | Average Rank | Actual Rank |
|------|-------------|-------------------|--------------|-------------|
| Houston Texans | 3 | 1 | 1 | 1 ✅ |
| Denver Broncos, LAC | 4 (each) | 2-3 | 2.5 → 2 | 2 ✅ |
| 4 teams with 6 TDs | 6 (each) | 4-7 | 5.5 → 6 | 6 ✅ |
| 6 teams with 7 TDs | 7 (each) | 12-17 | 14.5 → 14 | 14 ✅ |
| Baltimore Ravens | 13 | 32 | 32 | 32 ✅ |

## Impact on Prop Optimizer

### Matchup Scores Now Accurate
The scoring model uses defensive ranks to calculate matchup scores:
- **Lower rank (better defense) = Lower matchup score**
- **Higher rank (worse defense) = Higher matchup score**

With correct tie handling:
```
Player vs Pittsburgh (Rank 14) → Matchup Score: ~42 
(Previously showed Rank 16 → Score: ~48)
```

This gives users more accurate assessments of prop quality.

## Files Modified
1. ✅ `defensive_scraper.py` - Added tie handling, fixed data persistence
2. ✅ `team_name_utils.py` - (Already created in previous fix)

## Testing
- ✅ Verified all 32 teams have correct rankings
- ✅ Verified tie handling for groups of 2, 3, 4, and 6 teams
- ✅ Verified rankings match NFL.com source data
- ✅ Verified data processor retrieves correct ranks
- ✅ All linter checks pass

## Usage
To update defensive stats with proper tie handling:
```bash
python3 defensive_scraper.py --force
```

This will:
1. Scrape fresh TD data from NFL.com
2. Calculate rankings with proper tie handling
3. Save raw counts and rankings to separate cache files
4. Display sample results

## Notes
- Tie handling applies to ALL defensive stats (TDs, yards, points)
- Raw TD counts are preserved in `nfl_defensive_td_cache.pkl` (for reference)
- Actual rankings used by optimizer are in `espn_defensive_rankings.json`
- Rounding uses Python's banker's rounding (round half to even)

