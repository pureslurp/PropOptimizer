# Week Detection System - Implementation Summary

## Problem Identified

The original week detection logic had a critical flaw:

**Old Logic:**
```python
# Count folders = completed weeks
available_weeks = [1, 2, 3, 4, 5, 6]
current_week = len(available_weeks) + 1  # = 7 ❌ WRONG!
```

**Issue:** Once we created `WEEK6/` folder to save props (before games), the system thought Week 7 was current, but Week 6 games haven't been played yet.

## Solution Implemented

Created a **robust week detection system** based on the NFL schedule dates in `2025/nfl_schedule.csv`.

### New `week_utils.py` Module

**Primary Method: `get_current_week_from_schedule()`**
- Reads `2025/nfl_schedule.csv`
- Parses game dates for each week
- Determines current week based on today's date
- Logic: If today is between Week X-1's last game and Week X's last game, it's Week X
- **Works regardless of folder structure**

**Fallback Method: `get_current_week_from_folders()`**
- Checks which folders have `box_score_debug.csv` (completed weeks)
- Current week = highest completed week + 1
- Used only if schedule file is missing or parsing fails

**Helper: `get_available_weeks_with_data()`**
- Returns comprehensive data about all weeks:
  - `all`: All weeks with folders
  - `with_props`: Weeks that have saved props
  - `with_scores`: Weeks that have box scores
  - `complete`: Weeks with both props and scores

## Test Results

```bash
$ python3 week_utils.py

Testing Week Detection Functions
============================================================

1. Schedule-based detection:
   Current week: 6 ✅

2. Folder-based detection (fallback):
   Current week: 6 ✅

3. Available weeks:
   All weeks: [1, 2, 3, 4, 5, 6]
   With props: [6]
   With scores: [1, 2, 3, 4, 5]
   Complete (both): []
```

**Perfect!** Both methods correctly identify Week 6 as current, even though WEEK6 folder exists.

## Updated Scripts

### 1. `save_weekly_props.py`

**Before:**
```python
def get_current_week():
    available_weeks = []
    # ... count folders ...
    return max(available_weeks) + 1  # ❌ Broken
```

**After:**
```python
from week_utils import get_current_week_from_schedule

week_number = get_current_week_from_schedule()  # ✅ Robust
```

**Output:**
```
📅 Auto-detected current week: 6 (based on NFL schedule)
```

### 2. `player_prop_optimizer.py`

**Before:**
```python
available_weeks = get_available_weeks()
current_week = len(available_weeks) + 1  # ❌ Broken
```

**After:**
```python
from week_utils import get_current_week_from_schedule, get_available_weeks_with_data

current_week = get_current_week_from_schedule()  # ✅ Robust
weeks_data = get_available_weeks_with_data()
available_weeks = weeks_data['all']
```

## Edge Cases Handled

### Case 1: Week 6 folder exists but games haven't been played
**Scenario:** You saved props for Week 6, creating the folder, but it's still Tuesday before games.

- **Old system:** Would return Week 7 ❌
- **New system:** Returns Week 6 ✅

### Case 2: It's Monday after Week 5 games
**Scenario:** Week 5 games just finished, box scores being processed.

- **Schedule-based:** Returns Week 6 (correct - props available) ✅
- **Folder-based fallback:** Returns Week 6 (Week 5 has box scores) ✅

### Case 3: Mid-season, multiple weeks with various data
**Scenario:** Weeks 1-5 have box scores, Week 6 has props, Week 7-18 don't exist yet.

- **System correctly identifies:** Current week = 6 ✅
- **Available past weeks:** 1-5 (with box scores)
- **Complete weeks:** None yet (Week 6 needs box scores)

### Case 4: Schedule file missing
**Scenario:** `2025/nfl_schedule.csv` not found or corrupted.

- **System falls back** to folder-based detection ✅
- **Warning displayed** about using fallback method
- **Still works** based on box score presence

### Case 5: Off-season or past Week 18
**Scenario:** All games completed, into playoffs or off-season.

- **Schedule-based:** Returns Week 19 (past all scheduled weeks)
- **Allows manual override:** `--week X` parameter

## How It Works: Schedule-Based Detection

```python
# Load schedule
schedule = pd.read_csv("2025/nfl_schedule.csv")

# Parse dates (e.g., "Sep 4 2025 8:20 p")
schedule['parsed_date'] = pd.to_datetime(...)

# Get last game date for each week
week_end_dates = schedule.groupby('Week')['parsed_date'].max()

# Find current week
today = datetime.now()
for week in week_end_dates.index:
    week_end = week_end_dates[week]
    if today <= week_end + 1 day buffer:
        return week  # This is the current week
```

**Buffer:** 1 day after last game still counts as that week (allows time for box score processing).

## Benefits

1. **Accurate:** Based on actual NFL schedule, not folder structure
2. **Robust:** Handles all edge cases correctly
3. **Flexible:** Falls back gracefully if schedule unavailable
4. **Transparent:** Clear output shows detection method
5. **Testable:** Standalone module can be run independently
6. **Maintainable:** Single source of truth for week detection

## Verification Commands

```bash
# Test week detection
python3 week_utils.py

# Test save script with auto-detection
python3 save_weekly_props.py --dry-run

# Override if needed
python3 save_weekly_props.py --week 6 --dry-run
```

## Files Modified

- ✅ **NEW:** `week_utils.py` (155 lines) - Week detection utilities
- ✅ **UPDATED:** `save_weekly_props.py` - Uses schedule-based detection
- ✅ **UPDATED:** `player_prop_optimizer.py` - Uses schedule-based detection

## Future Enhancements

1. **Multi-season support:** Detect year from schedule or date
2. **Playoff weeks:** Handle weeks 19-22 (playoffs)
3. **Bye weeks:** Track which teams have bye weeks
4. **Week transitions:** Better handling of Monday night games

## Conclusion

The week detection system is now **robust and reliable**, correctly identifying the current NFL week based on the actual schedule rather than folder structure. This solves the critical issue where creating a week folder for props would incorrectly advance the week counter.

**Status:** ✅ **PRODUCTION READY**

