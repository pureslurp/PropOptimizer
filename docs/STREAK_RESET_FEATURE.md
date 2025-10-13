# Streak Reset Feature

## Overview
Enhanced the streak calculation to account for games where a player did not play (DNP - injuries, rest, etc.). The streak now resets to 0 if a player misses 2 or more consecutive games.

## Problem
Previously, the streak counter would simply count consecutive games where a player went over the line, but it didn't account for missed games. This could lead to inflated streaks:

**Example Problem:**
- Week 2: Player goes over (streak = 1)
- Week 3: Player goes over (streak = 2)
- Week 4: Player goes over (streak = 3)
- Week 5: Player DNP (injured)
- Week 6: Player DNP (still injured)
- Week 7: Player returns and goes over

Previously, this would show a streak of 4, which is misleading since the player missed 2 games.

## Solution
The `get_player_streak()` function now tracks week numbers and checks for gaps between games played.

### Streak Reset Rules
1. **1 game missed**: Streak continues
   - Example: Weeks 6, 4 (missed week 5) → Streak continues
   
2. **2+ games missed**: Streak resets to 0
   - Example: Weeks 7, 4 (missed weeks 6 and 5) → Streak resets

### Implementation Details

**Modified Function:** `enhanced_data_processor.py` → `get_player_streak()`

**Key Changes:**
1. Added `_filter_games_by_week_with_weeks()` helper function that returns both game stats and week numbers
2. Track week numbers while counting the streak
3. Calculate the gap between consecutive games: `week_gap = previous_week - current_week`
4. Reset streak if `week_gap >= 3` (meaning 2+ weeks missed)

**Gap Calculation Examples:**
- Week 6 → Week 5: gap = 1 (consecutive weeks) ✓ Continue
- Week 6 → Week 4: gap = 2 (missed week 5) ✓ Continue  
- Week 6 → Week 3: gap = 3 (missed weeks 5 and 4) ✗ Reset
- Week 7 → Week 4: gap = 3 (missed weeks 6 and 5) ✗ Reset

## Files Modified

### 1. `enhanced_data_processor.py`
- **Updated:** `get_player_streak()` - Now checks for week gaps and resets streak if 2+ games missed
- **Added:** `_filter_games_by_week_with_weeks()` - Helper function that returns both stats and weeks

### 2. `player_prop_optimizer.py`
- **Updated:** Column explanations to document the new streak reset behavior

## Examples

### Example 1: Continuous Play (No Reset)
```
Player's games:
- Week 2: 150 yards (over 149.5 line) ✓
- Week 3: 200 yards (over 149.5 line) ✓
- Week 4: 175 yards (over 149.5 line) ✓

Result: Streak = 3
```

### Example 2: One Game Missed (No Reset)
```
Player's games:
- Week 2: 150 yards (over 149.5 line) ✓
- Week 3: 200 yards (over 149.5 line) ✓
- Week 4: DNP (injured)
- Week 5: 175 yards (over 149.5 line) ✓

Result: Streak = 3 (only 1 game missed, streak continues)
```

### Example 3: Two Games Missed (Reset)
```
Player's games:
- Week 2: 150 yards (over 149.5 line) ✓
- Week 3: 200 yards (over 149.5 line) ✓
- Week 4: DNP (injured)
- Week 5: DNP (still injured)
- Week 6: 175 yards (over 149.5 line) ✓

Result: Streak = 1 (2 games missed, streak resets at week 6)
```

### Example 4: Current Week Scenario
```
Current Week: 6
Player's games:
- Week 2: 150 yards (over line) ✓
- Week 3: 200 yards (over line) ✓
- Week 4: 175 yards (over line) ✓
- Week 5: DNP (missed 1 game)

Result: Streak = 3 (only 1 game missed, streak continues)
```

```
Current Week: 7
Player's games:
- Week 2: 150 yards (over line) ✓
- Week 3: 200 yards (over line) ✓
- Week 4: 175 yards (over line) ✓
- Week 5: DNP (missed)
- Week 6: DNP (missed 2nd game)

Result: Streak = 0 (2 games missed, streak reset)
```

## Benefits

1. **More Accurate Streaks**: Reflects actual playing performance rather than inflated numbers from injury gaps
2. **Better Decision Making**: Bettors can see if a player truly has momentum vs. just came back from injury
3. **Injury Awareness**: Highlights when a player has been out, which is valuable context for prop betting
4. **Fair Comparisons**: Players who played every week are properly distinguished from those who missed time

## Testing

The feature has been implemented and tested with the following scenarios:
- ✅ Consecutive games (no gaps)
- ✅ One game missed (streak continues)
- ✅ Two games missed (streak resets)
- ✅ Multiple streaks with gaps
- ✅ Historical week filtering compatibility

## User Documentation

Users will see the updated behavior in the Streamlit app:
- The "Streak" column will now accurately reflect only consecutive games played
- Tooltip/documentation explains the 2-game reset rule
- Historical data respects the same rules for accurate backtesting

