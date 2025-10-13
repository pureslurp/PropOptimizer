# V2 Strategy Quick Reference

## What Changed?

### New UI Section: "Plum Props v2"
Located right below the original "Plum Props" section, you'll now see a new v2 section with three expanders:
- 🎯 **Optimal v2** ✅ (implemented)
- 🧈 **Greasy v2** ✅ (implemented)
- 🎲 **Degen v2** (coming soon)

### V2 Strategy Comparison

| Criteria | v1 Optimal | v2 Optimal | v2 Greasy | Notes |
|----------|-----------|-----------|-----------|-------|
| **Max Players** | 5 | **4** | **6** | v2 Greasy = bigger parlay |
| **Odds Range** | -150 to -400 | **-150 to -300** | **-150 to -300** | v2 tighter odds range |
| **Score Range** | 70+ | **80+** | **65-80** | v2 Greasy = mid-tier scores |
| **Min Streak** | None | **3+** | **3+** | v2 requires hot streaks |
| **Position Filter** | No | **Yes** | **Yes** | v2 filters inappropriate stats |

### Position Filtering Explained

**What Gets Filtered Out:**
- ❌ QB Rushing Yards/TDs (e.g., Jalen Hurts rushing props)
- ❌ RB Receiving Yards/Receptions/TDs (e.g., Austin Ekeler receiving props)

**What Stays In:**
- ✅ QB Passing Yards/TDs
- ✅ RB Rushing Yards/TDs  
- ✅ WR/TE Receiving Yards/Receptions/TDs

**Why?** This focuses on players' primary roles and avoids unpredictable secondary stats.

## ROI Performance Table

The ROI table now shows both v1 and v2 results:

```
Version | Optimal | Greasy | Degen
--------|---------|--------|-------
v1      | +2.5u   | -1.2u  | -3.4u
v2      | +1.8u   | +0.4u  | -
```

- Green = Positive ROI (profitable)
- Red = Negative ROI (losing)
- `-` = Not yet implemented

**Key Insights:**
- v2 Optimal: Fewer players (4) with higher scores = more consistent but lower total ROI
- v2 Greasy: More players (6) with mid-tier scores = potential for higher ROI but riskier

## How to Create New Versions (v3, v4, etc.)

### Step 1: Define Strategy Parameters
Add to `calculate_all_strategies_roi()` around line 775:

```python
'v3_Optimal': {
    'score_min': 85,              # Higher score threshold
    'score_max': float('inf'),
    'odds_min': -250,             # Even tighter odds
    'odds_max': -150,
    'streak_min': 4,              # 4+ game streak required
    'max_players': 3,             # Only 3 players
    'position_filter': True       # Position filtering enabled
}
```

### Step 2: Add UI Section
Add after v2 section around line 1667:

```python
# V3 Strategy sections
st.subheader("Plum Props v3")
col_1_v3, col_2_v3, col_3_v3 = st.columns(3)

with col_1_v3:
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
```

### Step 3: Update ROI Table
Add to ROI extraction around line 1748:

```python
v3_optimal_roi = roi_data.get('v3_Optimal', {}).get('total_roi', 0)
```

Then add to `roi_table_data` list:

```python
{
    'Version': 'v3',
    'Optimal': format_roi(v3_optimal_roi),
    'Greasy': '-',
    'Degen': '-',
    'Optimal_numeric': v3_optimal_roi,
    'Greasy_numeric': 0,
    'Degen_numeric': 0
}
```

## Reusable Functions

### `filter_props_by_strategy()`
Main filtering function - use this for any strategy:

```python
filtered = filter_props_by_strategy(
    df=results_df,
    data_processor=data_processor,  # Required for position filtering
    score_min=80,                   # Minimum score
    score_max=float('inf'),         # Maximum score
    odds_min=-300,                  # Minimum odds
    odds_max=-150,                  # Maximum odds
    streak_min=3,                   # Minimum streak (optional)
    max_players=4,                  # Max players to return
    position_filter=True            # Enable position filtering
)
```

### `is_position_appropriate_stat()`
Check if a stat type is appropriate for a player's position:

```python
is_valid = is_position_appropriate_stat(
    player_name="Patrick Mahomes",
    stat_type="Rushing Yards",
    data_processor=data_processor
)
# Returns: False (QB rushing not allowed)
```

## Examples

### Conservative Strategy (High Confidence)
```python
display_prop_picks(
    results_df,
    score_min=90,        # Very high scores only
    score_max=float('inf'),
    odds_min=-200,       # Closer to even money
    odds_max=-150,
    streak_min=5,        # 5+ game hot streak
    max_players=2,       # Only 2 players
    position_filter=True
)
```

### Aggressive Strategy (High Risk/Reward)
```python
display_prop_picks(
    results_df,
    score_min=60,        # Lower threshold
    score_max=float('inf'),
    odds_min=-400,       # Accept longer odds
    odds_max=-150,
    streak_min=None,     # No streak requirement
    max_players=6,       # Bigger parlay
    position_filter=False
)
```

### Position-Specific Strategy (WR/RB Focus)
Since position filtering excludes QB rush and RB receiving, you can create receiving-focused strategies:

```python
display_prop_picks(
    results_df,
    score_min=75,
    odds_min=-300,
    odds_max=-150,
    position_filter=True  # Only shows WR/TE receiving stats (no RB rec)
)
```

## Testing Your Changes

1. **Start the app**: `streamlit run player_prop_optimizer.py`
2. **Check v2 Optimal**: Expand the "Optimal v2" section
3. **Verify position filtering**: Look for QB rush or RB receiving props (should be none)
4. **Check ROI table**: Scroll down to see v2 Optimal historical performance
5. **Test with historical weeks**: Use the week dropdown to test with past data

## Tips

1. **Start conservative**: Use higher scores, tighter odds, and stricter requirements
2. **Monitor ROI**: Check the performance table to see what's working
3. **Iterate**: Adjust parameters based on historical performance
4. **Document**: Add comments explaining your strategy's logic
5. **Test thoroughly**: Use multiple historical weeks to validate

## Support for Future Versions

The architecture is designed to support unlimited strategy versions (v3, v4, v5, etc.) with minimal code changes. Just follow the 3-step process above!

