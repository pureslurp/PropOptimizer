# Game Time Filtering - Preventing Updates for Started Games

## Overview

The `save_weekly_props.py` script now includes **automatic filtering** to prevent updating props for games that have already started or finished.

## How It Works

### 1. **Commence Time Capture**
Every prop now includes the game's start time:
```
Commence Time: 2025-10-12T17:00:00Z  (UTC timezone)
```

### 2. **Automatic Filtering**
When you run the save script:
```bash
python3 save_weekly_props.py
```

The script automatically:
1. ✅ Fetches current props from Odds API
2. 🕐 Checks each game's start time
3. 🚫 **Filters out props for games that have already started**
4. 💾 Only updates props for games that haven't started yet
5. ✅ **Preserves old props** for games that have started (doesn't delete them)

### 3. **Smart Merging**
The script uses intelligent merging logic:

**Scenario A: Before Any Games Start (Tuesday-Thursday)**
```
Run script → All props are future → All get updated
```

**Scenario B: After Thursday Night Game (Friday-Saturday)**
```
Run script → Thursday game filtered out → Other games updated
Old Thursday props preserved with original lines
```

**Scenario C: During Sunday Games**
```
Run script → Early games filtered out → Late games still updated
Props for started games remain unchanged
```

## Example Output

### Before Games Start
```
✅ Fetched 121 current player props
📊 Updating 117 existing props
➕ Adding 4 new props
✅ Keeping 0 props not in current fetch
```

### After Thursday Night Game
```
✅ Fetched 100 current player props
🚫 Skipping 21 props for games that have already started
📊 Updating 90 existing props
➕ Adding 10 new props
✅ Keeping 21 props not in current fetch (games already started)
```

## Why This Matters

### **Problem Without Filtering:**
If a player gets injured during warm-ups, the bookmaker pulls their props. Without filtering, re-running the script would **delete** that player's historical prop line.

### **Solution With Filtering:**
The script preserves the original prop line even if it's no longer available from the API. This gives you a complete historical record.

## Use Cases

### 1. **Line Shopping Throughout the Week**
```bash
# Tuesday: Save initial lines
python3 save_weekly_props.py

# Friday: Check for line movements, update future games
python3 save_weekly_props.py

# Sunday morning: Final update before afternoon games
python3 save_weekly_props.py
```

Each run only updates games that haven't started yet!

### 2. **Handling Injuries/Scratches**
Player scratched before Thursday game? Their original props are preserved in your database even though the bookmaker removed them.

### 3. **Multi-Day Slate**
NFL has Thursday, Saturday, Sunday, and Monday games. You can safely run the script multiple times throughout the week without corrupting data.

## Technical Details

### Time Comparison
```python
# All times compared in UTC
now = datetime.now(timezone.utc)
game_time = "2025-10-12T17:00:00Z"  # From API

if game_time > now:
    # Game hasn't started - OK to update
else:
    # Game started/finished - preserve old data
```

### Data Preservation
The script uses **set operations** to identify which props to keep:
- **Update Set**: Props in both old and new data (future games only)
- **Add Set**: Props only in new data (future games only)
- **Keep Set**: Props only in old data (games that started + removed props)

## Verification

Check game times in your saved data:
```bash
head -5 2025/WEEK6/props.csv
```

You'll see the `Commence Time` column with timestamps like:
```
2025-10-10T00:15:00Z  (Thursday 8:15 PM ET)
2025-10-13T17:00:00Z  (Sunday 1:00 PM ET)
```

## Edge Cases Handled

✅ **Games with no commence time** (API error): Treated as future games (updated)  
✅ **All games started**: Script returns existing data unchanged  
✅ **Clock changes**: Uses UTC (no daylight saving issues)  
✅ **Manual week override**: Works the same for any week

## Command Reference

```bash
# Standard use - only updates future games
python3 save_weekly_props.py

# Dry run to see what would be filtered
python3 save_weekly_props.py --dry-run

# Manual week (same filtering applies)
python3 save_weekly_props.py --week 7
```

## Best Practices

1. **Run Early in the Week**: Tuesday-Wednesday to capture opening lines
2. **Monitor Line Movements**: Safe to re-run Friday-Saturday
3. **Final Update**: Sunday morning before early games
4. **Don't Run During Games**: Not necessary, but won't hurt if you do

## Status Messages

The script tells you what it's doing:

```
🚫 Skipping X props for games that have already started
📊 Updating Y existing props
➕ Adding Z new props  
✅ Keeping W props not in current fetch
```

This transparency helps you understand what's being updated vs. preserved.

## Summary

✅ **Automatic Protection**: No manual tracking needed  
✅ **Complete History**: Never lose prop lines for started games  
✅ **Safe to Re-run**: Run as many times as you want  
✅ **No Configuration**: Works out of the box  

The system is now **production-ready** and protects your historical data automatically!

