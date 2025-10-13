# Default Values Fix - Show N/A Instead of Misleading Defaults

## Issue Description

Several functions in the data processor were returning default numeric values (like `0.5`, `0.0`, `16`) when data was not available. This made it difficult to identify data issues because the defaults looked like real data values in the table.

## Examples of Misleading Defaults

**Before the fix:**
- `get_player_over_rate()` returned `0.5` (50%) when no data available
- `get_player_average()` returned `0.0` when no data available  
- `get_player_last_n_over_rate()` returned `0.5` (50%) when no data available
- `get_team_defensive_rank()` returned `16` (middle ranking) when team not found
- `get_player_home_over_rate()` returned `0.5` (50%) when no home games
- `get_player_away_over_rate()` returned `0.5` (50%) when no away games

These defaults made it impossible to distinguish between:
- A player who actually had a 50% over rate
- A player with no data available

## Solution

Changed all functions to return `None` instead of numeric defaults, then updated display logic to show **"N/A"** for `None` values.

## Files Modified

### 1. `enhanced_data_processor.py`

Updated 6 functions to return `None` instead of default numeric values:

#### `get_player_over_rate()`
```python
# Before
return 0.5  # Default 50% if no data

# After  
return None  # Return None if no data available
```

#### `get_player_home_over_rate()`
```python
# Before
return 0.5  # Default 50% if no data

# After
return None  # Return None if no home game data available
```

#### `get_player_away_over_rate()`
```python
# Before
return 0.5  # Default 50% if no data

# After
return None  # Return None if no away game data available
```

#### `get_player_average()`
```python
# Before
return 0.0

# After
return None  # Return None if no data available
```

#### `get_player_last_n_over_rate()`
```python
# Before
return 0.5

# After
return None  # Return None if no data available
```

#### `get_team_defensive_rank()`
```python
# Before
return 16  # Default middle ranking if team not found

# After
return None  # Return None if team not found (will display as N/A)
```

#### `_get_historical_team_defensive_rank()`
```python
# Before
return 16  # Default middle ranking if team not found

# After
return None  # Return None if team not found (will display as N/A)
```

### 2. `scoring_model.py`

Updated to handle `None` values while still using fallback values for calculations:

```python
# Get raw values (may be None)
season_over_rate_raw = self.data_processor.get_player_over_rate(player, stat_type, line)
l5_over_rate_raw = self.data_processor.get_player_last_n_over_rate(player, stat_type, line, n=5)
player_avg_raw = self.data_processor.get_player_average(player, stat_type)

# Create fallback values for calculations
season_over_rate = season_over_rate_raw if season_over_rate_raw is not None else 0.5
l5_over_rate = l5_over_rate_raw if l5_over_rate_raw is not None else 0.5
player_avg = player_avg_raw if player_avg_raw is not None else 0.0

# Use fallbacks for scoring calculations
matchup_score = self._calculate_matchup_score(team_rank if team_rank is not None else 16, stat_type)

# Return original None values for display
return {
    'team_rank': team_rank,  # Original value (may be None)
    'over_rate': season_over_rate_raw,  # Original value (may be None)
    'l5_over_rate': l5_over_rate_raw,  # Original value (may be None)
    'player_avg': player_avg_raw,  # Original value (may be None)
    # ... etc
}
```

Updated `_calculate_confidence()` to handle `None` for team_rank:
```python
# Before
if team_rank <= 5 or team_rank >= 28:  # Could crash if None

# After
if team_rank is not None and (team_rank <= 5 or team_rank >= 28):  # Safe
```

### 3. `player_prop_optimizer.py`

Updated display formatting to show "N/A" for `None` values:

#### Team Rank
```python
# Format Team Rank (show "N/A" if None)
display_df['team_rank'] = display_df['team_rank'].apply(
    lambda x: x if pd.notna(x) and x is not None else "N/A"
)
```

#### Season Over Rate (25/26)
```python
# Before (would crash on None)
display_df['25/26_numeric'] = display_df['25/26'] * 100

# After (handles None)
display_df['25/26_numeric'] = display_df['25/26'].apply(
    lambda x: x * 100 if x is not None and pd.notna(x) else None
)
display_df['25/26'] = display_df['25/26_numeric'].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
)
```

#### L5 Over Rate
```python
# Updated to handle None
display_df['L5_numeric'] = display_df['L5'].apply(
    lambda x: x * 100 if x is not None and pd.notna(x) else None
)
display_df['L5'] = display_df['L5_numeric'].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
)
```

#### Home/Away Over Rates
Already updated in previous fix, now consistent with all other rates.

## Result

### Before Fix
```
Player: Unknown Player
Team Rank: 16          ← Looks like real data but is actually "team not found"
L5: 50.0%              ← Looks like real data but is actually "no data"
Home: 50.0%            ← Looks like real data but is actually "no data"
Away: 50.0%            ← Looks like real data but is actually "no data"
25/26: 50.0%           ← Looks like real data but is actually "no data"
```

### After Fix
```
Player: Unknown Player
Team Rank: N/A         ← Clearly indicates missing data
L5: N/A                ← Clearly indicates missing data
Home: N/A              ← Clearly indicates missing data
Away: N/A              ← Clearly indicates missing data
25/26: N/A             ← Clearly indicates missing data
```

## Benefits

✅ **Easy to spot data issues** - "N/A" stands out visually  
✅ **No confusion between real and default values** - 50% means 50%, not "no data"  
✅ **Scoring still works** - Calculations use sensible fallbacks internally  
✅ **Better debugging** - Can quickly identify props with missing player/team data  
✅ **Consistent behavior** - All rate columns handle None the same way

## Testing Recommendations

To verify the fix is working:

1. Look for any "N/A" values in the table
2. These indicate missing data that should be investigated
3. Common scenarios:
   - New players with no historical games
   - Players who haven't played home/away games yet
   - Teams with misspelled or unrecognized names
   - Players with injuries (no recent games)

## Backward Compatibility

The changes maintain backward compatibility:
- Scoring calculations use the same fallback values as before
- Props with complete data display identically
- Only missing data now shows "N/A" instead of misleading defaults

