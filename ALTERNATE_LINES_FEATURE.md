# Alternate Lines Feature

## Overview
Added functionality to display alternate betting lines in the Streamlit dashboard tables. For each player and stat type, the system calculates a 70% threshold from their historical performance and finds the closest alternate line from The Odds API.

## Implementation Details

### New Components

#### 1. AlternateLineManager Class
- **Location**: `player_prop_optimizer.py`
- **Purpose**: Fetch and manage alternate lines from The Odds API in real-time
- **Key Methods**:
  - `fetch_alternate_lines_for_stat(stat_type, bookmaker, progress_callback)`: Fetches alternate lines from The Odds API in real-time for a specific stat type
  - `get_closest_alternate_line(player, stat_type, target_line)`: Finds the closest alternate line to a target threshold (fetches if not cached)
- **Caching**: Alternate lines are cached per stat type during the session to avoid redundant API calls

#### 2. calculate_70_percent_threshold() Function
- **Location**: `player_prop_optimizer.py`
- **Purpose**: Calculate the betting line threshold where a player's over rate is closest to 70%
- **Algorithm**:
  1. Examines thresholds between consecutive game performances (e.g., 130.5 is between games of 130 and 152 yards)
  2. Calculates the over rate at each potential threshold
  3. Finds the threshold closest to 70% over rate
  4. When there's a tie, prefers the higher threshold (more conservative)
  5. Rounds to standard .5 betting lines (e.g., 141.5, 224.5)

**Example**: For Jalen Hurts with passing yards: [152, 101, 226, 130, 280]
- Sorted: [101, 130, 152, 226, 280]
- Calculated threshold: 141.5 yards (between 130 and 152)
- Over rate at threshold: 60% (3 out of 5 games over 141.5)
- This is the closest to the 70% target (10% difference)

### Modified Components

#### Main Function Updates
1. **Initialization**: Added `alt_line_manager = AlternateLineManager()` to load alternate lines
2. **Score Calculation Loop**: Extended to calculate 70% thresholds and create alternate line rows
3. **Data Combination**: Merges main props with alternate line props before display
4. **Sorting**: Groups players with their alternate lines by sorting on Player name, then is_alternate flag
5. **Display Formatting**: Adds "+" suffix to alternate lines (e.g., "224.5+")

### Real-Time API Fetching

#### How It Works
The system now fetches alternate lines directly from The Odds API in real-time:

1. **On Stat Selection**: When you select a stat type (e.g., Passing Yards), the system:
   - Uses the event IDs from the main props fetch
   - Makes additional API calls to get alternate lines for that specific stat type
   - Caches the results for the current session

2. **API Endpoints Used**:
   ```
   GET /v4/sports/americanfootball_nfl/events/{event_id}/odds
   
   Parameters:
   - markets: player_pass_yds_alternate, player_rush_yds_alternate, etc.
   - bookmakers: fanduel
   - includeAltLines: true
   - oddsFormat: american
   ```

3. **Supported Markets**:
   - `player_pass_yds_alternate` → Passing Yards
   - `player_rush_yds_alternate` → Rushing Yards
   - `player_reception_yds_alternate` → Receiving Yards
   - `player_receptions_alternate` → Receptions
   - `player_pass_tds_alternate` → Passing TDs
   - `player_rush_tds_alternate` → Rushing TDs
   - `player_rec_tds_alternate` → Receiving TDs

#### Performance Optimization
- **Per-Session Caching**: Alternate lines are fetched once per stat type per session
- **Rate Limiting**: 0.3 second delay between API calls to respect rate limits
- **Progress Indicator**: Shows spinner while fetching alternate lines
- **Error Handling**: Continues on individual event failures

## User Experience

### Table Display
Each stat type table now includes both:
1. **Main lines**: Standard betting lines from the primary odds feed
2. **Alternate lines**: Calculated 70% threshold lines (marked with "+")

Example row for Jalen Hurts (Passing Yards):
```
Player         | Opp Team      | Team Rank | Score | Line    | Odds | Over Rate
Jalen Hurts    | New York Giants| 24        | 36    | 224.5+  | +178 | 40.0%
```

The "+" after "224.5" indicates this is an alternate line based on the 70% threshold calculation.

### Information Message
When alternate lines are added, users see:
```
✨ Added 3 alternate line recommendation(s) based on 70% threshold analysis
```

## How It Works - Step by Step

1. **Load Alternate Lines**: On startup, `AlternateLineManager` loads all available alternate line JSON files

2. **Fetch Main Props**: System fetches standard props from The Odds API

3. **Calculate Scores**: For each prop, calculate comprehensive scores

4. **Calculate 70% Thresholds**: For each player:
   - Retrieve their game-by-game stats from `data_processor`
   - Calculate the threshold where over rate is closest to 70%
   - Example: For games [101, 130, 152, 226, 280], threshold is 141.5 (60% over rate)

5. **Find Closest Alternate Lines**: 
   - Search alternate lines for the player
   - Find the line closest to the calculated threshold
   - Example: For threshold 141.5, might find alternate line 149.5

6. **Create Alternate Rows**: 
   - Calculate scores for the alternate line
   - Add as a new row with `is_alternate = True`
   - Preserve all player/team information from original row

7. **Display**: 
   - Merge main and alternate props
   - Sort by player name to group them together
   - Format alternate lines with "+" suffix
   - Show in the table

## Extending to Other Stat Types

The system automatically supports all stat types! Simply:

1. **Select the Stat Type**: Choose any stat type from the dropdown (Passing Yards, Rushing Yards, Receiving Yards, etc.)

2. **Automatic Fetching**: The system will automatically:
   - Determine the correct alternate market to fetch (e.g., `player_rush_yds_alternate`)
   - Make API calls to get the data
   - Parse and cache the results
   - Add alternate line rows to the table

3. **No Configuration Needed**: All stat types are pre-configured in the `stat_market_mapping` dictionary

**Note**: Requires an Odds API plan that includes alternate player props. Free plans may not have access to all alternate markets.

## Benefits

1. **Data-Driven Recommendations**: Uses actual player performance history to identify value lines
2. **Consistent Strategy**: Targets 70% over rate for all players/stats
3. **Integrated Display**: Alternate lines appear directly in existing tables
4. **Clear Identification**: "+" suffix makes alternate lines easy to spot
5. **Flexible**: Automatically works with any stat type when JSON data is available

## Testing

Tested with Jalen Hurts example:
- Input stats: [152, 101, 226, 130, 280]
- Expected threshold: ~141.5 yards at 60% over rate ✓
- Closest to 70% target (10% difference) ✓
- Properly finds and displays alternate lines ✓

## Future Enhancements

Potential improvements:
1. Allow users to configure the target over rate (default 70%)
2. Show both the calculated threshold and actual alternate line in a tooltip
3. Add multiple alternate lines (e.g., 60%, 70%, 80% thresholds)
4. Fetch alternate lines directly from API instead of using cached JSON
5. Add visual indicators (colors, icons) to distinguish alternate lines

