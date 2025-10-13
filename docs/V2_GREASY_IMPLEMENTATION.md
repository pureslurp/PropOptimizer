# V2 Greasy Implementation Summary

## Overview
Successfully implemented v2 Greasy strategy with mid-range score targeting and larger parlay size.

## Implementation Date
**Completed**: Today

## V2 Greasy Specifications

### Criteria
| Parameter | Value | Comparison to v2 Optimal |
|-----------|-------|--------------------------|
| **Max Players** | 6 | +2 more (v2 Optimal = 4) |
| **Odds Range** | -150 to -300 | Same |
| **Score Range** | 65 to 80 | Lower (v2 Optimal = 80+) |
| **Min Streak** | 3+ | Same |
| **Position Filter** | Yes | Same |

### Strategy Philosophy

**v2 Greasy** targets the "sweet spot" between high-confidence and value:
- **Mid-Range Scores** (65-80): Not as elite as v2 Optimal, but still solid performers
- **Larger Parlay** (6 players): Higher potential payout, but all must hit
- **Same Quality Gates**: Maintains streak and position requirements for consistency
- **Risk/Reward**: Higher risk than v2 Optimal (more players) but targets undervalued mid-tier props

### Comparison: v2 Optimal vs v2 Greasy

```
v2 Optimal:
- "Quality over quantity"
- 4 elite players (score 80+)
- Smaller parlay = more likely to hit
- Lower potential payout
- Conservative approach

v2 Greasy:
- "Balanced value play"  
- 6 solid players (score 65-80)
- Bigger parlay = higher potential
- Higher risk of one player missing
- Aggressive value approach
```

## Code Changes

### 1. Strategy Definition
**File**: `player_prop_optimizer.py`  
**Location**: Lines 826-834

Added v2_Greasy to strategy dictionary:
```python
'v2_Greasy': {
    'score_min': 65,
    'score_max': 80,
    'odds_min': -300,
    'odds_max': -150,
    'streak_min': 3,
    'max_players': 6,
    'position_filter': True
}
```

### 2. UI Implementation
**File**: `player_prop_optimizer.py`  
**Location**: Lines 1787-1804

Replaced placeholder with actual display_prop_picks call:
```python
with st.expander("🧈 Greasy v2", expanded=False):
    display_prop_picks(
        results_df, 
        score_min=65, 
        score_max=80,
        odds_min=-300,
        odds_max=-150,
        streak_min=3,
        max_players=6,
        position_filter=True
    )
```

### 3. ROI Tracking
**File**: `player_prop_optimizer.py`  
**Location**: Lines 1847, 1863

Added ROI extraction and display:
```python
v2_greasy_roi = roi_data.get('v2_Greasy', {}).get('total_roi', 0) or 0

# In ROI table:
'Greasy': format_roi(v2_greasy_roi),
'Greasy_numeric': v2_greasy_roi,
```

### 4. Updated Caption
**Location**: Line 1902

Updated to explain all strategies:
```
v1 strategies pick top 5 props. 
v2 Optimal picks top 4, v2 Greasy picks top 6 with mid-range scores (65-80). 
All strategies parlay props - all must hit to win.
```

## Position Filtering

v2 Greasy uses the same position filtering as v2 Optimal:

**Filtered Out:**
- ❌ QB Rushing Yards/TDs
- ❌ RB Receiving Yards/Receptions/TDs

**Allowed:**
- ✅ QB Passing Yards/TDs
- ✅ RB Rushing Yards/TDs
- ✅ WR/TE Receiving Yards/Receptions/TDs

This ensures we're betting on players' primary skills, not secondary/unpredictable stats.

## Error Handling

v2 Greasy inherits all error handling from the reusable functions:
- ✅ Returns empty set if no props meet criteria
- ✅ Shows informative message with criteria details
- ✅ Handles missing data gracefully
- ✅ Logs warnings without crashing
- ✅ ROI calculation wrapped in try-except

## Testing Checklist

- [x] Strategy defined in `calculate_all_strategies_roi()`
- [x] UI section displays picks correctly
- [x] ROI table shows v2_Greasy performance
- [x] Position filtering works correctly
- [x] Error handling for no results
- [x] No linter errors
- [x] Documentation updated

## Usage

### Viewing v2 Greasy Picks

1. Run the app: `streamlit run player_prop_optimizer.py`
2. Scroll to "Plum Props v2" section
3. Click "🧈 Greasy v2" expander
4. View 6 props with scores 65-80 and 3+ game streaks

### Expected Output

```
• **Player Name** 100.5+ RecYds -200 odds
• **Player Name** 75.5+ RushYds -225 odds
• **Player Name** 50.5+ RecYds -180 odds
• **Player Name** 225.5+ PassYds -250 odds
• **Player Name** 65.5+ RecYds -190 odds
• **Player Name** 80.5+ RushYds -275 odds
• If Parlayed: +450 odds
```

If no props meet criteria:
```
*No props meet the criteria: Score 65+ (max 80) | Odds -300 to -150 | Streak 3+ | Position-appropriate only*
💡 Try adjusting filters or check back when more games are available
```

## Historical Performance

The ROI table will show historical performance across all weeks 4+:

```
Version | Optimal | Greasy | Degen
--------|---------|--------|-------
v1      | +X.XXu  | +X.XXu | +X.XXu
v2      | +X.XXu  | +X.XXu | -
```

**Interpretation:**
- Green background = Profitable strategy
- Red background = Losing strategy
- Compare v2 Greasy to v2 Optimal to see risk/reward tradeoff

## Strategy Selection Guide

### When to Use v2 Greasy

✅ **Good Times:**
- When there are many props in the 65-80 score range
- When you want higher potential payout (6-leg parlay)
- When confident in mid-tier players with hot streaks
- When value betting (finding underpriced props)

❌ **Avoid When:**
- Limited props available (may not find 6 players)
- Prefer safer, smaller parlays
- Week with many elite props (use v2 Optimal instead)
- Risk-averse betting approach

### When to Use v2 Optimal

✅ **Good Times:**
- When you want higher hit rate (fewer legs = more likely)
- When there are elite props (80+ scores)
- Conservative approach
- Building bankroll steadily

### Strategy Combination

You can use both strategies:
- **Conservative Week**: Use v2 Optimal only
- **Balanced Week**: Split bankroll between v2 Optimal and v2 Greasy
- **Aggressive Week**: Use v2 Greasy or both

## Performance Metrics to Monitor

Track these over time:
1. **Hit Rate**: How often does the parlay hit?
2. **ROI**: Total units won/lost
3. **Average Score**: Are you finding quality props?
4. **Weeks with No Props**: How often do criteria filter out all props?
5. **Comparison**: v2 Optimal vs v2 Greasy performance

## Next Steps

1. **Run Live Test**: Use v2 Greasy for current week
2. **Monitor Results**: Track actual vs expected performance
3. **Adjust Criteria**: If too strict/loose, modify score range
4. **Implement v2 Degen**: Complete the v2 suite
5. **Create v3**: Build on learnings from v2 performance

## Files Modified

- ✅ `player_prop_optimizer.py` - Main implementation
- ✅ `V2_STRATEGY_IMPLEMENTATION.md` - Updated with v2 Greasy details
- ✅ `V2_QUICK_REFERENCE.md` - Added v2 Greasy to comparison table
- ✅ `V2_GREASY_IMPLEMENTATION.md` - This document

## Support

If you encounter issues:

1. **No Props Found**: Criteria may be too strict for available data
   - Lower score_min to 60
   - Increase score_max to 85
   - Reduce streak_min to 2

2. **ROI Not Showing**: Insufficient historical data
   - Need weeks 4+ with box scores
   - Check console for error messages

3. **Position Filter Issues**: Player not in data processor
   - Will default to allowing the prop (safe fallback)
   - Check console for warnings

## Summary

✅ **v2 Greasy successfully implemented**  
✅ **6-player mid-tier strategy with position filtering**  
✅ **Full ROI tracking and error handling**  
✅ **Ready for live use**

The v2 Greasy strategy provides a balanced approach between the elite-focused v2 Optimal and future risk-seeking v2 Degen. It targets the valuable middle ground of consistent performers with hot streaks, offering higher potential payouts through larger parlays while maintaining quality gates for streak and position appropriateness.

