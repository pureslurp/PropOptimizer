# Centralized Week Dates System

## Overview
Refactored the codebase to use a centralized week dates system in `utils.py`, eliminating the dependency on `nfl_schedule.csv` for most week-related operations.

## What Changed

### ✅ Added to `utils.py`

**New Constants:**
- `NFL_2025_WEEK_DATES` - Dictionary mapping week numbers to start dates

**New Functions:**
```python
get_week_start_date(week_number, year="2025")
    # Returns ISO format start date for a given week

get_week_date_range(week_number, year="2025")  
    # Returns (start_date, end_date) tuple for a given week

get_available_weeks(year="2025")
    # Returns list of all available week numbers [1-18]

get_current_week_from_dates(year="2025")
    # Determines current week based on today's date and week ranges
```

**Updated Functions:**
- `get_current_week_from_schedule()` - Now uses date-based detection first, then falls back to schedule file parsing

### ✅ Updated Scripts

**`save_historical_odds.py`:**
- Removed local `week_dates` dictionary
- Removed `get_week_start_date()` and `list_available_weeks()` methods
- Now imports and uses functions from `utils.py`

**Benefits:**
- Single source of truth for week dates
- No duplication across scripts
- Easy to update for future seasons

## Week Detection Hierarchy

The system now uses a 3-tier fallback approach:

1. **Primary: Date-based detection** (fastest, no file dependencies)
   - Uses `NFL_2025_WEEK_DATES` from `utils.py`
   - Determines week based on today's date
   - ✅ No CSV file needed

2. **Fallback 1: Schedule file parsing**
   - Reads `nfl_schedule.csv` if it exists
   - Parses game dates and times
   - Used if date-based detection fails

3. **Fallback 2: Folder-based detection**
   - Checks which `WEEK{X}` folders have data
   - Used if both above methods fail

## Schedule CSV Usage

The `nfl_schedule.csv` is now **optional** for most operations:

### ✅ No longer needed for:
- Week detection (`get_current_week_from_schedule()`)
- Getting week start dates (`get_week_start_date()`)
- Getting week date ranges (`get_week_date_range()`)
- Historical odds fetching (`save_historical_odds.py`)

### ⚠️ Still needed for:
- Home/away game detection (`enhanced_data_processor.is_home_game()`)
- Specific team schedules
- Game time information

## Usage Examples

### Get current week:
```python
from utils import get_current_week_from_schedule

current_week = get_current_week_from_schedule()
# Returns: 6 (based on today's date: Oct 10, 2025)
```

### Get week start date:
```python
from utils import get_week_start_date

week_6_start = get_week_start_date(6)
# Returns: '2025-10-09T00:00:00Z'
```

### Get week date range:
```python
from utils import get_week_date_range

start, end = get_week_date_range(6)
# Returns: ('2025-10-09T00:00:00Z', '2025-10-15T23:59:59Z')
```

### List available weeks:
```python
from utils import get_available_weeks

weeks = get_available_weeks()
# Returns: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
```

## Scripts Updated

1. ✅ `utils.py` - Added centralized week dates and functions
2. ✅ `save_historical_odds.py` - Removed local week dates, uses utils
3. ✅ `player_prop_optimizer.py` - Works with updated `get_current_week_from_schedule()`
4. ✅ `save_weekly_props.py` - Works with updated `get_current_week_from_schedule()`
5. ✅ `enhanced_data_processor.py` - Still uses schedule CSV for home/away detection

## Testing

All functions tested and working:
```bash
✅ get_current_week_from_dates() -> 6
✅ get_week_start_date(6) -> '2025-10-09T00:00:00Z'
✅ get_available_weeks() -> [1, 2, ..., 18]
✅ get_current_week_from_schedule() -> 6
✅ save_historical_odds.py imports work correctly
```

## Future Enhancements

To fully eliminate `nfl_schedule.csv` dependency:

1. **Add opponent data to week dates:**
   ```python
   NFL_2025_SCHEDULE = {
       1: [
           {'home': 'Philadelphia Eagles', 'away': 'Dallas Cowboys', 'date': '2025-09-04', 'time': '20:20'},
           # ... more games
       ]
   }
   ```

2. **Update `enhanced_data_processor.is_home_game()` to use this data**

3. **Remove `nfl_schedule.csv` entirely**

## Benefits

✅ **Single source of truth** - All week dates in one place  
✅ **No file dependencies** - Date-based detection works without any CSV  
✅ **Faster execution** - No file I/O for week detection  
✅ **Easier maintenance** - Update dates in one location  
✅ **Better error handling** - Multiple fallback methods  
✅ **Consistent across scripts** - All use same week dates  

## API Cost Savings

The historical odds API can now efficiently use date ranges:
- Week start/end dates automatically calculated
- No need to parse CSV to determine date ranges
- Properly filters games to specific weeks
- Example: Week 5 correctly returns 14 games (not 29)

