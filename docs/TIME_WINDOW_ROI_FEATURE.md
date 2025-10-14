# Time Window Feature

## Overview
The `player_prop_optimizer.py` has been enhanced with time window functionality in two ways:
1. **ROI Table** - Shows historical ROI broken down by time windows
2. **Prop Sections** - Displays current week's props organized by time windows

This allows you to see how different strategies perform during specific game slots throughout the week and easily find props for specific game times.

## Time Windows
NFL games are classified into five time windows:

1. **TNF (Thursday Night Football)** - Thursday night games (typically 8:15 PM ET)
2. **SunAM (Sunday Morning/Afternoon)** - Sunday 1:00 PM ET games
3. **SunPM (Sunday Afternoon)** - Sunday 4:00 PM ET games  
4. **SNF (Sunday Night Football)** - Sunday night games (typically 8:20 PM ET)
5. **MNF (Monday Night Football)** - Monday night games (typically 8:15 PM ET)

## How It Works

### Game Time Classification
- Each game's `commence_time` (in UTC format) is extracted from the historical odds JSON files
- The time is converted to Eastern Time (ET)
- Based on the day of week and hour, games are classified into one of the five time windows

### ROI Calculation
- For each strategy (v1_Optimal, v1_Greasy, v1_Degen, v2_Optimal, v2_Greasy, v2_Degen)
- Props are filtered by time window
- Up to `max_players` props per time window are selected based on score
- A parlay bet is placed for each time window (1 unit per time window)
- ROI is calculated separately for each time window and aggregated across all historical weeks

### Display Format
The ROI table now shows rows for each version + time window combination:
- v1_TNF, v1_SunAM, v1_SunPM, v1_SNF, v1_MNF
- v2_TNF, v2_SunAM, v2_SunPM, v2_SNF, v2_MNF

Each row shows the Optimal, Greasy, and Degen strategy results for that time window.

## Implementation Details

### Files Modified
1. **player_prop_optimizer.py**
   - Added `classify_game_time_window()` function to classify games by time
   - Modified `calculate_strategy_roi_for_week()` to return ROI by time window
   - Modified `calculate_all_strategies_roi()` to aggregate ROI by time window
   - Updated ROI table display to show version + time window rows

2. **requirements.txt**
   - Added `python-dateutil>=2.8.0` for date parsing
   - Added `pytz>=2023.3` for timezone conversion

### Key Functions

#### `classify_game_time_window(commence_time_str)`
Classifies a game into a time window based on its commence time (in UTC).

**Logic:**
- Converts UTC time to Eastern Time
- Checks day of week and hour
- Returns one of: 'TNF', 'SunAM', 'SunPM', 'SNF', 'MNF', or 'Other'

#### `calculate_strategy_roi_for_week(week_num, ...)`
Now returns a dictionary of ROI by time window instead of a single total.

**Returns:**
```python
{
    'TNF': {'roi': 0.0, 'results': [...]},
    'SunAM': {'roi': 2.5, 'results': [...]},
    'SunPM': {'roi': -1.0, 'results': [...]},
    'SNF': {'roi': 1.3, 'results': [...]},
    'MNF': {'roi': -1.0, 'results': [...]}
}
```

#### `calculate_all_strategies_roi()`
Now aggregates ROI by strategy and time window.

**Returns:**
```python
{
    'v1_Optimal': {
        'TNF': {'roi': 0.0, 'results': [...]},
        'SunAM': {'roi': 2.5, 'results': [...]},
        ...
    },
    'v1_Greasy': {...},
    ...
}
```

## Features

### 1. Time Window Prop Sections (Current and Historical Weeks)
Located after the "Plum Props v2" section, there are expandable sections for each time window that contains props for that time slot.

**Display Format:**
- Each time window has its own expandable section with an emoji indicator
- Shows the count of available props in the header
- Contains both v1 and v2 strategies organized in columns
- Only shows time windows that have available props

**Strategies Displayed Per Time Window:**
- **v1 Strategies:**
  - 🎯 Optimal (Score 70+)
  - 🧈 Greasy (Score 50-70)
  - 🎲 Degen (Score 0-50)
  
- **v2 Strategies:**
  - 🎯 Optimal v2 (Score 75+, Streak 3+, 4 players max)
  - 🧈 Greasy v2 (Score 65-80, Streak 2+, 6 players max)
  - 🎲 Degen v2 (Score 70-100, Wide odds, 3 players max)

### 2. ROI Performance Table
Shows historical ROI data organized by strategy and time window.

**Table Format:**
- Rows: v1_TNF, v1_SunAM, v1_SunPM, v1_SNF, v1_MNF, v2_TNF, v2_SunAM, etc.
- Columns: Optimal, Greasy, Degen
- Color coded (green for positive, red for negative)

## Benefits

1. **Better Strategy Insights** - See which strategies work best for specific game times
2. **Risk Management** - Identify time windows where certain strategies underperform
3. **Betting Strategy** - Make more informed decisions about when to use each strategy
4. **Pattern Recognition** - Spot trends in prop performance across different game slots
5. **Easy Navigation** - Quickly find props for games at specific times (e.g., just Thursday night)
6. **Historical Analysis** - Review past weeks to see how strategies performed during specific time windows
7. **Performance Verification** - Check actual results for historical time windows to validate ROI calculations

## Example Output

| Strategy    | Optimal | Greasy  | Degen   |
|-------------|---------|---------|---------|
| v1_TNF      | +2.50u  | -1.00u  | +0.50u  |
| v1_SunAM    | +5.20u  | +3.10u  | -2.00u  |
| v1_SunPM    | -1.00u  | +1.50u  | +0.80u  |
| v1_SNF      | +3.40u  | +2.20u  | -1.00u  |
| v1_MNF      | +1.10u  | -1.00u  | +2.30u  |
| v2_TNF      | +1.80u  | +0.50u  | -1.00u  |
| v2_SunAM    | +4.50u  | +2.80u  | -1.00u  |
| v2_SunPM    | +2.10u  | +1.20u  | +0.90u  |
| v2_SNF      | +3.00u  | +1.80u  | -1.00u  |
| v2_MNF      | +0.70u  | -1.00u  | +1.50u  |

*Note: Values are examples for illustration*

## Testing

The time window classification has been tested and verified:
- Thursday 8:15 PM ET → TNF ✓
- Sunday 1:00 PM ET → SunAM ✓
- Sunday 4:00 PM ET → SunPM ✓
- Sunday 8:20 PM ET → SNF ✓
- Monday 8:15 PM ET → MNF ✓

## Usage

### Viewing Props by Time Window
1. Navigate to any week in the app (current or historical)
2. Scroll down past "Plum Props v2" to find "Plum Props by Game Time"
3. Expand any time window section (e.g., 🏈 Thursday Night Football)
4. Browse props organized by strategy (Optimal, Greasy, Degen, and v2 variants)
5. Each strategy shows up to the max number of qualifying props for that time slot
6. For historical weeks, you can see actual results (HIT/MISS) for each prop

### Analyzing ROI by Time Window
1. Navigate to the current week in the app
2. Scroll down to "Plum Props Performance (ROI)"
3. Review the table to see which strategy+time window combinations perform best
4. Look for patterns (e.g., "v2_Optimal performs best on Sunday AM games")
5. Use this data to inform your betting strategy for the current week
6. Cross-reference with historical time window sections to verify performance

## Notes

- **Time Window Sections**: Displayed for both current and historical weeks
- **ROI Table**: Only displayed for the current week, uses historical data from Week 4+
- ROI is calculated from Week 4 onwards (requires 3 weeks of history for meaningful props)
- Each time window is treated as a separate parlay (1 unit bet per time window)
- If a time window has no games or no qualifying props, it won't appear in the prop sections
- The feature automatically handles timezone conversion from UTC to Eastern Time
- Props are filtered per time window, so the same player can appear in multiple time windows if they have multiple props

