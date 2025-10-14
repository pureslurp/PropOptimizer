# Strategy Refactoring Guide

## Overview
The strategy definitions and display logic have been centralized to a new file `prop_strategies.py` to reduce code duplication and make maintenance easier.

## What Changed

### New File: `prop_strategies.py`
Contains:
- **`STRATEGIES` dict** - Centralized strategy configurations (v1_Optimal, v1_Greasy, v1_Degen, v2_Optimal, v2_Greasy, v2_Degen)
- **`get_strategies_for_roi()`** - Returns strategy configs formatted for ROI calculation
- **`display_prop_picks()`** - Function to display props based on strategy criteria
- **`display_strategy_section()`** - Displays a single strategy with expander
- **`display_all_strategies()`** - Displays all v1 and v2 strategies in organized sections
- **`display_time_window_strategies()`** - Displays strategies for a specific time window

### Updated File: `player_prop_optimizer.py`
- **Imports** from `prop_strategies` module
- **ROI calculation** uses `get_strategies_for_roi()` instead of hardcoded dict
- **Display sections** use imported functions instead of local definitions
- **Removed** ~200 lines of duplicated display logic

## How to Update Strategies

### Before (Error-Prone - Multiple Locations)
To change strategy parameters, you had to update:
1. The `strategies` dict in `calculate_all_strategies_roi()` (line ~880)
2. The `display_prop_picks()` calls in Plum Props section (lines ~1806-1814)
3. The `display_prop_picks()` calls in Plum Props v2 section (lines ~1820-1867)
4. The `display_prop_picks()` calls in Time Window sections (lines ~1733-1806)

### After (Single Location)
To change strategy parameters, update **ONLY** the `STRATEGIES` dict in `prop_strategies.py`:

```python
STRATEGIES = {
    'v1_Optimal': {
        'name': 'Optimal',
        'emoji': '🎯',
        'version': 'v1',
        'score_min': 70,       # ← Change here
        'score_max': float('inf'),
        'odds_min': -400,      # ← Change here
        'odds_max': -150,      # ← Change here
        'max_players': 5,      # ← Change here
        'streak_min': None,
        'position_filter': False
    },
    # ... other strategies
}
```

That's it! Changes automatically apply to:
- ROI calculations
- Plum Props display
- Plum Props v2 display
- Time window displays

## Strategy Configuration Fields

Each strategy in the `STRATEGIES` dict has:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Display name (e.g., "Optimal", "Greasy v2") |
| `emoji` | str | Emoji icon (🎯, 🧈, 🎲) |
| `version` | str | Version identifier ("v1" or "v2") |
| `score_min` | float | Minimum score threshold |
| `score_max` | float | Maximum score threshold (use `float('inf')` for no max) |
| `odds_min` | int | Minimum American odds (e.g., -400) |
| `odds_max` | int | Maximum American odds (e.g., -150) |
| `max_players` | int | Maximum number of props to select |
| `streak_min` | int/None | Minimum streak value (None = no streak filter) |
| `position_filter` | bool | Whether to apply position-appropriate filtering |

## Adding a New Strategy

To add a new strategy (e.g., "v1_Conservative"):

1. Add to `STRATEGIES` dict in `prop_strategies.py`:
```python
'v1_Conservative': {
    'name': 'Conservative',
    'emoji': '🛡️',
    'version': 'v1',
    'score_min': 80, 
    'score_max': float('inf'),
    'odds_min': -500,
    'odds_max': -200,
    'max_players': 3,
    'streak_min': None,
    'position_filter': False
}
```

2. Add display section in `player_prop_optimizer.py`:
```python
# In the main strategy display section
with col_4:  # Add a 4th column
    display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v1_Conservative')
```

3. Add to ROI table display in `player_prop_optimizer.py` (if desired):
```python
# In the ROI table building section
for version in ['v1', 'v2']:
    for window in time_windows:
        conservative_key = f'{version}_Conservative'
        conservative_roi = roi_data.get(conservative_key, {}).get(window, {}).get('roi', 0) or 0
        # Add to roi_table_data
```

That's it! The new strategy will automatically be calculated in ROI and displayed everywhere.

## Benefits

1. **Single Source of Truth** - Strategy configs defined once, used everywhere
2. **Easier Maintenance** - Update one place instead of 4+
3. **Less Error-Prone** - No risk of forgetting to update a display section
4. **Cleaner Code** - `player_prop_optimizer.py` is ~200 lines shorter
5. **Better Organization** - Strategy logic separated from display logic
6. **Easier Testing** - Strategy configs can be tested independently

## Files Modified

- ✅ **Created:** `prop_strategies.py` (new file, ~400 lines)
- ✅ **Updated:** `player_prop_optimizer.py` (removed ~200 lines, added imports)
- ✅ **No Changes:** ROI calculation logic (same behavior, cleaner implementation)

## Backward Compatibility

- ✅ All existing functionality preserved
- ✅ ROI calculations produce identical results
- ✅ Display format unchanged
- ✅ No breaking changes to user interface

