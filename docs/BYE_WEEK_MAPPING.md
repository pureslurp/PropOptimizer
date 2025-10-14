# Bye Week Mapping Feature

## Overview
Added a comprehensive bye week tracking system to handle NFL teams' bye weeks in the 2025 season. This resolves issues with "N/A" appearing in home/away stats when players' teams have bye weeks.

## The Problem

Players on teams with bye weeks were showing "N/A" for their Away (or Home) stats even though they had played away (or home) games. This happened because:

1. **Cache was incomplete**: The player season cache was missing some weeks (e.g., Aaron Rodgers was missing weeks 1 and 3)
2. **Bye weeks cause gaps**: When a team has a bye week, there's no game data for that week, which can cause confusion in calculations

## Example: Aaron Rodgers (Pittsburgh Steelers)

**Before Fix:**
- Displayed stats only included weeks 2, 4, 6
- Missing weeks 1 and 3 (both away games)
- Away stats showed "N/A"

**After Fix:**
- All 5 games loaded: weeks 1, 2, 3, 4, 6
- Week 5: Bye week (correctly excluded)
- Away stats: 244 yards (Week 1), 139 yards (Week 3)
- Home stats: 203 (Week 2), 200 (Week 4), 235 (Week 6)

## Solutions Implemented

### 1. Bye Week Mapping (`utils.py`)

Added `BYE_WEEK_2025` dictionary in `TeamNameNormalizer` class:

```python
BYE_WEEK_2025 = {
    'Arizona Cardinals': None,  # TODO: Fill in
    'Atlanta Falcons': None,
    ...
    'Pittsburgh Steelers': 5,  # Confirmed
    ...
}
```

### 2. Helper Functions

**Class Methods:**
- `TeamNameNormalizer.get_bye_week(team_name)` - Returns bye week number or None
- `TeamNameNormalizer.is_bye_week(team_name, week)` - Returns True if team is on bye

**Convenience Functions:**
```python
from utils import get_bye_week, is_bye_week

# Get bye week
bye = get_bye_week('Pittsburgh Steelers')  # Returns: 5
bye = get_bye_week('PIT')  # Also works with abbreviations

# Check if specific week is bye
is_bye = is_bye_week('PIT', 5)  # Returns: True
is_bye = is_bye_week('PIT', 6)  # Returns: False
```

### 3. Cache Rebuild

Rebuilt the player season cache with all weeks 1-6 to ensure complete data.

## How to Use

### Fill in Bye Weeks

Edit `utils.py` and update the `BYE_WEEK_2025` dictionary with each team's bye week:

```python
BYE_WEEK_2025 = {
    'Arizona Cardinals': 11,  # Example
    'Atlanta Falcons': 12,
    # ... etc
}
```

### In Code

```python
from utils import get_bye_week, is_bye_week

# Check if a team is on bye
if is_bye_week('Kansas City Chiefs', current_week):
    print("Chiefs are on bye this week")

# Get bye week for display
bye = get_bye_week('KC')
if bye:
    print(f"Chiefs have their bye in week {bye}")
```

### Potential Future Enhancements

1. **Streak Calculations**: Could show "(Bye)" in streak displays when a team had a bye week
2. **Schedule Display**: Show bye weeks in game listings
3. **Validation**: Warn when a player has missing games that aren't explained by bye weeks
4. **Auto-Detection**: Could potentially auto-detect bye weeks from game data files

## Files Modified

- `utils.py`: Added `BYE_WEEK_2025` dictionary and helper functions
- `enhanced_data_processor.py`: Cache validation fix (separate issue)

## Testing

```python
# Test with Pittsburgh Steelers (known bye week 5)
from utils import get_bye_week, is_bye_week

assert get_bye_week('Pittsburgh Steelers') == 5
assert get_bye_week('PIT') == 5
assert is_bye_week('PIT', 5) == True
assert is_bye_week('PIT', 6) == False
```

## Notes

- Bye weeks typically occur in weeks 5-14 of the NFL season
- Each team has exactly ONE bye week
- Players on bye week teams will not have stats for that week
- This is normal and expected - not a data error!

