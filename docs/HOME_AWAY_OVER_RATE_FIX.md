# Home/Away Over Rate Display Fix

## Issue Description

When viewing historical week data (e.g., Week 5), players were showing incorrect home/away over rates in the table. For example:

```
Garrett Wilson - Receiving Yards vs DAL - Line: 49.5
Overall: 100.0%
Home: 50.0%  ← WRONG (should be 100% or N/A)
Away: 50.0%  ← WRONG (should be 100% or N/A)
```

This made it appear impossible for a player to have 100% overall but 50% home/away rates.

## Root Cause

The issue was in `enhanced_data_processor.py` functions:
- `get_player_home_over_rate()`
- `get_player_away_over_rate()`

These functions returned **0.5 (50%)** as a default fallback when:
1. No home/away game data was available for the player
2. The filtered game list was empty (after filtering by `max_week`)

This was misleading because `50%` looked like real data when it was actually just a placeholder for "no data available."

## The Fix

### 1. Changed Default Return Value

**Before:**
```python
def get_player_home_over_rate(self, player: str, stat_type: str, line: float) -> float:
    # ... filtering logic ...
    if games:
        over_count = sum(1 for game_stat in games if game_stat > line)
        return over_count / len(games)
    
    return 0.5  # ← Returns 50% when no data
```

**After:**
```python
def get_player_home_over_rate(self, player: str, stat_type: str, line: float) -> float:
    # ... filtering logic ...
    if games:
        over_count = sum(1 for game_stat in games if game_stat > line)
        return over_count / len(games)
    
    return None  # ← Returns None when no data
```

### 2. Updated Display Logic

In `player_prop_optimizer.py`, updated the formatting to handle `None` values:

**Before:**
```python
display_df['Home_numeric'] = display_df['Home'] * 100
display_df['Home'] = display_df['Home_numeric'].round(1).astype(str) + '%'
```

**After:**
```python
display_df['Home_numeric'] = display_df['Home'].apply(
    lambda x: x * 100 if x is not None and pd.notna(x) else None
)
display_df['Home'] = display_df['Home_numeric'].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
)
```

### 3. Updated Scoring Model

In `scoring_model.py`, added fallback logic when home/away data is `None`:

**Before:**
```python
if is_home:
    loc_over_rate = home_over_rate
else:
    loc_over_rate = away_over_rate
```

**After:**
```python
if is_home:
    loc_over_rate = home_over_rate if home_over_rate is not None else season_over_rate
else:
    loc_over_rate = away_over_rate if away_over_rate is not None else season_over_rate
```

## Result

Now the table correctly displays:

✅ **When player has both home and away games:**
```
Garrett Wilson - Receiving Yards - Line: 49.5 (Week 5 Historical)
Overall: 100.0%
Home: 100.0%  ← Correct (2 games, both over)
Away: 100.0%  ← Correct (2 games, both over)
```

✅ **When player has no home games:**
```
Some Player - Stat - Line: X
Overall: 80.0%
Home: N/A     ← Shows N/A instead of misleading 50%
Away: 80.0%
```

✅ **When player has no away games:**
```
Some Player - Stat - Line: X
Overall: 75.0%
Home: 75.0%
Away: N/A     ← Shows N/A instead of misleading 50%
```

## Verification

Created debug scripts to verify the fix works correctly:
- Confirmed that `max_week` filtering works properly (e.g., Week 5 analysis uses only weeks 1-4)
- Confirmed home/away splits are calculated correctly
- Confirmed display shows "N/A" when appropriate

### Example: Garrett Wilson Week 5 Analysis

With `max_week=5` (uses weeks 1-4):
- **Stored data**: 5 games total (weeks 1-5)
  - Home: weeks 1, 2, 5
  - Away: weeks 3, 4
  
- **After filtering** (weeks 1-4 only):
  - Home: weeks 1, 2 → values [95, 50] → 2/2 over 49.5 = **100%**
  - Away: weeks 3, 4 → values [84, 82] → 2/2 over 49.5 = **100%**
  - Overall: 4/4 = **100%**

## Files Modified

1. `enhanced_data_processor.py`
   - `get_player_home_over_rate()` - returns `None` instead of `0.5`
   - `get_player_away_over_rate()` - returns `None` instead of `0.5`

2. `player_prop_optimizer.py`
   - Updated display formatting to handle `None` values
   - Shows "N/A" when home/away data is not available

3. `scoring_model.py`
   - Added fallback to `season_over_rate` when home/away data is `None`
   - Ensures scoring calculations work even without location-specific data

## Impact

- ✅ More accurate and honest display of player statistics
- ✅ Clearer when data is missing vs. when a player actually has 50% over rate
- ✅ Better user experience when analyzing props
- ✅ Scoring model gracefully handles missing location data

