# Week Selection & Historical Props Implementation Summary

## What Was Built

A complete system for saving and viewing historical player prop data, allowing you to compare predictions against actual game results.

## New Features

### 1. Week Selection Dropdown
- Added a **"Select Week"** dropdown next to the "Select Stat Type" dropdown
- Options include:
  - **Current Week (6)** - Default view showing live props from Odds API
  - **Week 1, Week 2, Week 3...** - Past weeks showing saved historical props

### 2. Historical Props Database Script (`save_weekly_props.py`)
A new standalone script that:
- Fetches current player props from the Odds API
- Saves them to `data/historical_props.csv`
- Manages the database intelligently:
  - Keeps existing records
  - Updates props for the same week if re-run
  - Appends new weeks without touching old data
- Auto-detects current week based on available box score folders
- Provides detailed output showing what was saved

**Usage:**
```bash
# Save current week's props
python3 save_weekly_props.py

# Save specific week
python3 save_weekly_props.py --week 6

# Test mode (don't save)
python3 save_weekly_props.py --dry-run
```

### 3. Actual Stats Column (Past Weeks Only)
When viewing a past week with saved props AND box score data:
- New **"Actual"** column appears after the "Odds" column
- Shows the player's actual stat value for that week
- **Color coded:**
  - 🟢 **Green with bold text** = Player went OVER the prop line (hit!)
  - 🔴 **Red with bold text** = Player went UNDER the prop line (missed)
  - **"N/A"** = Player didn't record this stat type
  
**Example:**
| Player | Line | Odds | Actual | Score | L5 | Home | Away | 25/26 |
|--------|------|------|--------|-------|-----|------|------|-------|
| J.K. Dobbins | 69.5 | -110 | **100** 🟢 | 88.54 | 80.0% | 66.7% | 100.0% | 80.0% |
| C. McCaffrey | 85.5 | -120 | **45** 🔴 | 75.23 | 60.0% | 75.0% | 50.0% | 65.0% |

### 4. Updated UI Layout
- Reorganized top row into 4 columns instead of 3:
  1. **Stat Type** dropdown (2 columns wide)
  2. **Week** dropdown (2 columns wide)
  3. **Refresh** button (1 column wide)
  4. **Export** button (1 column wide)
- Export button only works for current week (shows warning for past weeks)
- Alternate lines disabled for past weeks (only available for current week)

### 5. Helper Functions Added

**`get_available_weeks()`**
- Scans `2025/` folder for `WEEK*` directories
- Returns sorted list of available weeks
- Used to populate week dropdown

**`load_historical_props_for_week(week_num)`**
- Loads saved props from `data/historical_props.csv`
- Filters to specific week
- Returns DataFrame of historical props

**`load_box_score_for_week(week_num)`**
- Loads actual game stats from `2025/WEEK{X}/box_score_debug.csv`
- Cleans player names for matching
- Returns DataFrame of actual stats

**`get_actual_stat(player_name, stat_type, box_score_df)`**
- Matches player name (using `clean_player_name()`)
- Maps stat type to correct column (e.g., "Rushing Yards" → "rush_Yds")
- Returns actual stat value or None if not found

**`get_stat_column_mapping()`**
- Maps friendly stat names to box score column names
- Example: "Passing Yards" → "pass_Yds"

## File Changes

### Modified Files

1. **`player_prop_optimizer.py`** (750 lines)
   - Added `import os` for file system operations
   - Added 5 new helper functions
   - Modified main() to handle week selection
   - Updated UI with week dropdown
   - Added logic to load historical props for past weeks
   - Added "Actual" column rendering with color coding
   - Disabled alternate lines and export for past weeks
   - Updated column explanations to include Actual column

2. **`README.md`** (179 lines)
   - Added historical props feature to Features section
   - Added "Saving Weekly Props" usage section
   - Updated main interface instructions
   - Added Actual column explanation

### New Files Created

1. **`save_weekly_props.py`** (224 lines)
   - Standalone script for saving weekly props
   - Command-line interface with argparse
   - Database management logic
   - Auto-week detection
   - Detailed progress output

2. **`WEEKLY_PROPS_GUIDE.md`** (296 lines)
   - Comprehensive user guide
   - Step-by-step workflow examples
   - Troubleshooting section
   - Database management tips
   - Data schema documentation

3. **`IMPLEMENTATION_SUMMARY.md`** (This file)
   - Technical implementation details
   - Complete feature list
   - File changes summary

## Data Flow

### Current Week Flow
```
User selects "Current Week (6)"
    ↓
Fetch props from Odds API
    ↓
Parse and process props
    ↓
Calculate scores with data processor
    ↓
Fetch alternate lines
    ↓
Display with all statistics
```

### Past Week Flow
```
User selects "Week 3"
    ↓
Load historical props from data/historical_props.csv
    ↓
Filter to Week 3 records
    ↓
Load box scores from 2025/WEEK3/box_score_debug.csv
    ↓
Calculate scores with data processor
    ↓
Match player names and get actual stats
    ↓
Display with Actual column (color coded)
    ↓
No alternate lines, no export
```

### Weekly Save Flow
```
Run: python3 save_weekly_props.py
    ↓
Auto-detect current week (based on available box scores)
    ↓
Fetch current props from Odds API
    ↓
Load existing historical_props.csv (if exists)
    ↓
Merge new props with existing data
    ↓
Remove duplicates (keep latest for same week/player/stat)
    ↓
Save to data/historical_props.csv
    ↓
Display summary statistics
```

## Technical Details

### Data Storage Format

**File:** `data/historical_props.csv`

**Columns:**
- `week` - Integer week number (1-18)
- `saved_date` - Timestamp when props were saved
- `Player` - Player name (cleaned format)
- `Team` - Player's team abbreviation
- `Opposing Team` - Defense they're facing (with vs/@ prefix)
- `Stat Type` - One of 7 stat types
- `Line` - Numeric prop line value
- `Odds` - American odds (negative or positive integer)
- `Bookmaker` - Bookmaker name (e.g., "FanDuel")

**Unique Key:** `Player + Stat Type + Week`

### Color Coding Logic

The `apply_all_styles()` function was extended with:

```python
if 'Actual' in row.index and 'Actual_numeric' in row.index and 'Line_numeric' in row.index:
    actual_val = row['Actual_numeric']
    line_val = row['Line_numeric']
    if pd.notna(actual_val) and pd.notna(line_val):
        if actual_val > line_val:
            styles['Actual'] = 'background-color: #d4edda; color: #155724; font-weight: bold'  # Green
        else:
            styles['Actual'] = 'background-color: #f8d7da; color: #721c24; font-weight: bold'  # Red
```

### Conditional Features

Features that are **disabled for past weeks:**
- Alternate line fetching
- CSV export
- API calls to Odds API
- Caching in session state

Features that **work for past weeks:**
- Comprehensive scoring
- Historical statistics (L5, Home, Away, Season)
- Player streak calculation
- Team defensive rankings
- All analysis and recommendations

## User Workflow

### Week-by-Week Workflow

**Tuesday (Props Posted):**
1. Run `python3 save_weekly_props.py` to save current week's props
2. Use app normally with "Current Week" selected

**Throughout the Week:**
- Analyze props using the app
- Make betting decisions
- Lines may update (can re-run save script to update)

**Monday (After Games):**
1. Box score data becomes available in `2025/WEEKX/` folder
2. Switch to past week in dropdown
3. View actual results vs. prop lines
4. Analyze accuracy and outcomes

**Repeat Weekly:**
- Each week, save new props before games
- Historical database grows over time
- Can analyze any past week at any time

## Benefits

1. **Accountability**: See how your predictions actually performed
2. **Learning**: Identify which stat types and situations work best
3. **Validation**: Verify the scoring model's accuracy over time
4. **Historical Analysis**: Compare week-to-week performance
5. **Trend Identification**: Spot patterns in line setting and outcomes
6. **No Manual Work**: Automated data saving and matching

## Future Enhancement Ideas

1. **Auto-save**: Cron job to automatically save props weekly
2. **Accuracy Dashboard**: Show overall hit rate across all saved weeks
3. **Line Movement Tracking**: If props saved multiple times per week
4. **Best Bets Tracking**: Mark props as "bet" and track ROI
5. **Export Historical**: CSV export for past weeks
6. **Multi-season Support**: Extend to multiple years (2025, 2026, etc.)
7. **Alternate Lines Storage**: Save alternate lines in historical data

## Testing

The script was tested with:
- ✅ Dry run mode (fetches but doesn't save)
- ✅ Auto-week detection (correctly identified Week 6)
- ✅ Prop fetching (successfully retrieved 121 props)
- ✅ No errors or warnings

The UI changes need testing with:
- [ ] View current week (should work as before)
- [ ] View past week with saved props and box scores
- [ ] View past week with saved props but no box scores
- [ ] View past week with no saved props (should show warning)

## Dependencies

No new dependencies were added. Uses existing packages:
- `pandas` - DataFrame operations
- `streamlit` - UI components
- `os` - File system operations
- `datetime` - Timestamps
- `argparse` - Command-line interface

## Command Reference

```bash
# Save current week props
python3 save_weekly_props.py

# Save specific week
python3 save_weekly_props.py --week 5

# Test without saving
python3 save_weekly_props.py --dry-run

# View historical props file
cat data/historical_props.csv | head -20

# Backup historical data
cp data/historical_props.csv data/historical_props_backup_$(date +%Y%m%d).csv

# Run the Streamlit app
streamlit run player_prop_optimizer.py
```

## Notes

- Historical props are only as good as when they were saved
- Lines can change throughout the week - consider saving multiple times
- Box score data must exist for Actual column to appear
- The system gracefully handles missing data (shows warnings)
- Week numbering is flexible (can go 1-18 for regular season)

