# V2 Strategy Implementation Summary

## Overview
Added v2 versions of player prop strategies with more refined filtering criteria and a reusable function architecture for future strategy versions.

## Key Changes

### 1. **Reusable Filter Function** (`filter_props_by_strategy`)
Created a flexible filtering function that accepts configurable parameters:
- `score_min` / `score_max`: Score range filtering
- `odds_min` / `odds_max`: Odds range filtering  
- `streak_min`: Minimum consecutive over streak
- `max_players`: Maximum number of players to return
- `position_filter`: Toggle for position-appropriate stat filtering

**Location**: Lines 671-720

### 2. **Position-Appropriate Stat Filtering** (`is_position_appropriate_stat`)
Implements smart filtering to exclude inappropriate stat types for positions:
- **QB**: Allows Passing stats, EXCLUDES Rushing stats
- **RB**: Allows Rushing stats, EXCLUDES Receiving stats  
- **WR/TE**: Allows Receiving stats

This prevents picks like:
- QB rushing yards (excludes dual-threat QB rushing props)
- RB receiving yards (excludes pass-catching RB receiving props)

**Location**: Lines 619-668

### 3. **V2 Strategy Definitions**

#### V2 Optimal
- **Max Players**: 4 (down from 5)
- **Odds Range**: -150 to -300 (tighter range than v1's -150 to -400)
- **Score**: ≥80 (higher than v1's ≥70)
- **Streak**: ≥3 consecutive overs required
- **Position Filter**: Enabled (no QB rush, no RB rec)

**Location**: Lines 1642-1659

#### V2 Greasy
- **Max Players**: 6 (more than v2 Optimal)
- **Odds Range**: -150 to -300 (same as v2 Optimal)
- **Score**: 65-80 (mid-range scores, between Optimal and lower tier)
- **Streak**: ≥3 consecutive overs required
- **Position Filter**: Enabled (no QB rush, no RB rec)

**Location**: Lines 1787-1804

#### V2 Degen
- Placeholder section created for future implementation
- Currently displays "Coming soon..."

**Location**: Lines 1806-1808

### 4. **Updated `display_prop_picks` Function**
Refactored to use the new reusable filter function instead of inline filtering logic.
- Now accepts all new filter parameters
- Maintains backward compatibility with v1 calls
- More maintainable for future versions

**Location**: Lines 1539-1557

### 5. **Enhanced ROI Calculation**
Updated `calculate_strategy_roi_for_week` to support new parameters:
- Added support for `streak_min`, `max_players`, and `position_filter`
- Uses reusable filter function for consistency
- Works for both v1 and v2 strategies

**Location**: Lines 467-615

### 6. **ROI Table Updates**
- Added v2 row to the ROI performance table
- Shows v2 Optimal and v2 Greasy historical performance
- Displays "-" for v2 Degen (not yet implemented)
- Updated caption to explain differences between strategies
- Color-coded: Green for positive ROI, Red for negative ROI

**Location**: Lines 1817-1902

## Benefits

### For Current Use
1. **More Selective Picks**: v2 Optimal uses stricter criteria (score 80+) for higher-confidence props
2. **Mid-Range Option**: v2 Greasy targets mid-tier props (scores 65-80) with larger parlay (6 players)
3. **Position Clarity**: Eliminates confusing props like QB rushing or RB receiving
4. **Streak Focus**: Both v2 strategies require hot streaks (3+ games), identifying momentum plays
5. **Better Odds**: Tighter odds range (-150 to -300) for more realistic bankroll management
6. **Strategy Variety**: Different risk/reward profiles with v2 Optimal (4 players, high scores) vs v2 Greasy (6 players, mid scores)

### For Future Development
1. **Reusable Functions**: `filter_props_by_strategy` and `is_position_appropriate_stat` can be used for v3, v4, etc.
2. **Easy to Extend**: Adding new strategies just requires:
   - Define parameters in `calculate_all_strategies_roi()`
   - Add expander in UI with `display_prop_picks()` call
   - Update ROI table data extraction
3. **Maintainable**: Centralized filtering logic reduces code duplication
4. **Testable**: Reusable functions can be tested independently

## Usage

### Viewing V2 Picks
1. Run the Streamlit app: `streamlit run player_prop_optimizer.py`
2. Scroll to "Plum Props v2" section (below v1 section)
3. Expand "🎯 Optimal v2" to see picks

### Adding Future Versions (v3, v4, etc.)
```python
# 1. Add strategy definition in calculate_all_strategies_roi()
'v3_Optimal': {
    'score_min': 85,
    'score_max': float('inf'),
    'odds_min': -250,
    'odds_max': -150,
    'streak_min': 4,
    'max_players': 3,
    'position_filter': True
}

# 2. Add UI section
with st.expander("🎯 Optimal v3", expanded=False):
    display_prop_picks(
        results_df, 
        score_min=85,
        score_max=float('inf'),
        odds_min=-250,
        odds_max=-150,
        streak_min=4,
        max_players=3,
        position_filter=True
    )

# 3. Update ROI table extraction
v3_optimal_roi = roi_data.get('v3_Optimal', {}).get('total_roi', 0)
```

## Error Handling

Comprehensive error handling has been implemented to ensure stability:

### Position Filtering Errors
- Validates all inputs before processing
- Returns safe defaults when player data missing
- Logs warnings but doesn't crash
- **Location**: Lines 631-696

### Filter Function Errors
- Validates DataFrame and required columns
- Handles missing streak or position data
- Returns empty DataFrame on error
- **Location**: Lines 699-774

### Display Function Errors
- Shows informative "no results" messages
- Includes criteria details when no props match
- Wraps filter calls in try-except
- **Location**: Lines 1627-1726

### ROI Calculation Errors
- Each strategy/week wrapped in error handling
- Continues processing on partial failures
- Logs warnings with context
- **Location**: Lines 777-868, 1793-1882

**See ERROR_HANDLING_GUIDE.md for complete details**

## Files Modified
- `player_prop_optimizer.py` (main changes)
- `V2_STRATEGY_IMPLEMENTATION.md` (documentation)
- `V2_QUICK_REFERENCE.md` (quick guide)
- `ERROR_HANDLING_GUIDE.md` (error handling details)

## Testing Recommendations
1. Run app and verify v2 Optimal displays props
2. Verify position filtering works (no QB rush, no RB rec in results)
3. Check ROI table shows v2 Optimal performance
4. Confirm v1 strategies still work as before
5. Test with historical weeks to verify ROI calculations
6. **Test error scenarios:**
   - Set very strict filters (Score 95+, Streak 10+) to trigger "no results"
   - Remove historical data files to test error handling
   - View console for warning messages

## Future Enhancements
- [x] ~~Implement v2 Greasy criteria~~ ✅ **COMPLETED**
- [ ] Implement v2 Degen criteria
- [ ] Add v3 strategies with even more refined criteria
- [ ] Add strategy comparison visualization
- [ ] Export strategy picks to separate CSV files
- [ ] Replace print() with structured logging
- [ ] Add error frequency tracking
- [ ] Add strategy performance charts over time
- [ ] Implement custom strategy builder in UI

