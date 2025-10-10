# Team Rank Display Bug Fix

## Issue
After implementing the player performance graph feature, the main table started showing **Team Rank = 16** for all props, while the graph correctly displayed the actual defensive rankings.

## Root Cause

**Double Conversion Bug** in `scoring_model.py`:

1. **Line 37-43** (OLD CODE): Pre-converted stat types before passing to `get_team_defensive_rank()`
   ```python
   defense_stat_type = f"{stat_type} Allowed"  # "Passing Yards" → "Passing Yards Allowed"
   if stat_type == "Receiving Yards":
       defense_stat_type = "Passing Yards Allowed"
   # ... more conversions ...
   team_rank = self.data_processor.get_team_defensive_rank(opposing_team, defense_stat_type)
   ```

2. **enhanced_data_processor.py** `get_team_defensive_rank()` (lines 522-532):
   - Receives "**Passing Yards Allowed**" (already converted)
   - Has a `stat_mapping` that expects base stat types like "Passing Yards"
   - Doesn't find "Passing Yards Allowed" in the mapping
   - Falls back to: `stat_type + ' Allowed'`
   - Results in: "**Passing Yards Allowed** Allowed" 😱
   - Can't find this malformed key in defensive stats
   - Returns default value: **16**

## Why the Graph Worked

The graph code in `get_player_last_n_games_detailed()` (line 847) correctly passes the **base stat type**:
```python
defensive_rank = self.get_team_defensive_rank(opponent_full, stat_type)
```

This is the correct pattern that `get_team_defensive_rank` expects.

## Solution

**Fixed `scoring_model.py`** to match the graph's pattern:

```python
# OLD (BUGGY):
defense_stat_type = f"{stat_type} Allowed"
if stat_type == "Receiving Yards":
    defense_stat_type = "Passing Yards Allowed"
# ... more conversions ...
team_rank = self.data_processor.get_team_defensive_rank(opposing_team, defense_stat_type)

# NEW (FIXED):
# Pass the base stat type - get_team_defensive_rank will handle the conversion
team_rank = self.data_processor.get_team_defensive_rank(opposing_team, stat_type)
```

## Why get_team_defensive_rank Handles Conversion

The method has its own internal mapping (lines 522-530):
```python
stat_mapping = {
    'Passing Yards': 'Passing Yards Allowed',
    'Passing TDs': 'Passing TDs Allowed',
    'Rushing Yards': 'Rushing Yards Allowed',
    'Rushing TDs': 'Rushing TDs Allowed',
    'Receptions': 'Passing Yards Allowed',      # Use passing defense as proxy
    'Receiving Yards': 'Passing Yards Allowed',  # Use passing defense as proxy
    'Receiving TDs': 'Passing TDs Allowed'       # Use passing TDs as proxy
}
defensive_stat = stat_mapping.get(stat_type, stat_type + ' Allowed')
```

It expects **base stat types** and converts them internally. Passing pre-converted types breaks this logic.

## Testing

After the fix:
1. **Click "🔄 Refresh"** in the Streamlit app to clear cached data
2. The table should now show correct Team Ranks (1-32)
3. Both table and graph now use the same data source

## Data Flow (Fixed)

```
API/CSV Data
    ↓
Player Props with "Opposing Team Full" (e.g., "Jacksonville Jaguars")
    ↓
scoring_model.py:
    team_rank = get_team_defensive_rank("Jacksonville Jaguars", "Passing Yards")
    ↓
enhanced_data_processor.py get_team_defensive_rank():
    Receives: ("Jacksonville Jaguars", "Passing Yards")
    Converts: "Passing Yards" → "Passing Yards Allowed"
    Looks up: team_defensive_stats["Jacksonville Jaguars"]["Passing Yards Allowed"]
    Returns: Actual rank (e.g., 8)
    ↓
Table displays: Team Rank = 8 ✅
```

## Files Modified

- **scoring_model.py** (line 37): Removed pre-conversion logic, pass base stat_type directly

## Related Code

Both code paths now correctly call `get_team_defensive_rank`:
- **Table/Scoring**: `scoring_model.py` line 37
- **Graph**: `enhanced_data_processor.py` line 847

