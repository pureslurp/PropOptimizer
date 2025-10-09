# Alternate Lines in Weekly Props Saving

## Overview

The `save_weekly_props.py` script now automatically fetches and saves **alternate lines** alongside standard prop lines.

## What Are Alternate Lines?

Alternate lines are different prop thresholds for the same stat with different odds:

**Standard Line:**
- Jalen Hurts Passing Yards: 196.5 @ -110

**Alternate Lines:**
- Jalen Hurts Passing Yards: 150.5 @ -300 (easier)
- Jalen Hurts Passing Yards: 225.5 @ +150 (harder)
- Jalen Hurts Passing Yards: 275.5 @ +350 (much harder)

## How It Works

### 1. Automatic Fetching (Default)
```bash
# This fetches both standard AND alternate lines
python3 save_weekly_props.py
```

**Output:**
```
✅ Fetched 121 standard player props

🔄 Fetching alternate lines (this may take 30-60 seconds)...
   💡 Making multiple API calls to fetch all available lines
   📋 Found 5 stat types to fetch: Receiving Yards, Receptions, Rushing Yards, Passing TDs, Passing Yards

   [1/5] 📊 Fetching Receiving Yards alternate lines...
        ✅ Found 245 alternate lines (odds between -450 and +200)
   [2/5] 📊 Fetching Receptions alternate lines...
        ✅ Found 180 alternate lines (odds between -450 and +200)
   [3/5] 📊 Fetching Rushing Yards alternate lines...
        ✅ Found 95 alternate lines (odds between -450 and +200)
   [4/5] 📊 Fetching Passing TDs alternate lines...
        ✅ Found 75 alternate lines (odds between -450 and +200)
   [5/5] 📊 Fetching Passing Yards alternate lines...
        ✅ Found 120 alternate lines (odds between -450 and +200)

✨ Added 715 alternate line props
📊 Total props (standard + alternates): 836
```

### 2. Fast Mode (Standard Lines Only)
```bash
# Skip alternates for a quick save (5-10 seconds)
python3 save_weekly_props.py --no-alternates
```

**Output:**
```
⚡ Fast mode: Skipping alternate lines
✅ Fetched 121 standard player props
```

## Filtering Criteria

Only alternate lines with odds between **-450 and +200** are saved.

**Why this range?**
- **Too favorable (< -450)**: Nearly guaranteed, not worth saving
- **Too unlikely (> +200)**: Longshots, less useful for analysis
- **Sweet spot (-450 to +200)**: Good balance of value and probability

## Data Structure

Saved CSV includes an `is_alternate` column to distinguish:

```csv
Player,Stat Type,Line,Odds,is_alternate
Jalen Hurts,Passing Yards,196.5,-110,False    ← Standard
Jalen Hurts,Passing Yards,225.5,+150,True     ← Alternate
Jalen Hurts,Passing Yards,275.5,+350,True     ← Alternate
```

## Benefits

### 1. **Complete Market View**
See all available betting options, not just the main line.

### 2. **Value Finding**
Identify which alternate lines offer the best odds for your predictions.

### 3. **Line Shopping**
Compare different thresholds to find optimal entry points.

### 4. **Historical Analysis**
Track how alternate lines move throughout the week.

## Performance

### With Alternates (Default)
- **Time**: 30-60 seconds
- **API Calls**: ~15-25 calls (one per game per stat type)
- **Props Saved**: 500-1000 total (depending on games available)

### Without Alternates (Fast)
- **Time**: 5-10 seconds
- **API Calls**: ~5-10 calls (one per game)
- **Props Saved**: 100-200 (main lines only)

## Use Cases

### Weekly Full Save
```bash
# Tuesday: Save everything (standard + alternates)
python3 save_weekly_props.py
```
Get the complete picture with all available lines.

### Quick Updates
```bash
# Friday: Quick update for line movements
python3 save_weekly_props.py --no-alternates
```
Fast refresh of main lines only.

### Line Monitoring
```bash
# Saturday morning: Full save to catch any changes
python3 save_weekly_props.py
```
Capture any last-minute alternate line adjustments.

## Example Saved Data

**Standard Prop:**
```csv
week,Player,Stat Type,Line,Odds,is_alternate
6,AJ Brown,Receiving Yards,64.5,-112,False
```

**With Alternates:**
```csv
week,Player,Stat Type,Line,Odds,is_alternate
6,AJ Brown,Receiving Yards,40.5,-300,True
6,AJ Brown,Receiving Yards,50.5,-180,True
6,AJ Brown,Receiving Yards,64.5,-112,False  ← Standard line
6,AJ Brown,Receiving Yards,75.5,+120,True
6,AJ Brown,Receiving Yards,85.5,+200,True
```

## Smart Merging

The merge logic works the same for both standard and alternate lines:

**Unique Key:** `Player_StatType_Line`
- Updates existing lines (same player/stat/line)
- Adds new lines
- Keeps old lines not in current fetch

This means:
- Standard line 64.5 can update independently of alternate 75.5
- Each line is tracked separately
- If an alternate line is removed, it's preserved in your data

## Command Reference

```bash
# Full save with alternates (recommended weekly)
python3 save_weekly_props.py

# Fast save without alternates (for quick checks)
python3 save_weekly_props.py --no-alternates

# Dry run to see what would be fetched
python3 save_weekly_props.py --dry-run

# Fast dry run
python3 save_weekly_props.py --dry-run --no-alternates
```

## Best Practices

1. **Tuesday/Wednesday**: Run full save with alternates
   - Captures opening lines across all thresholds
   
2. **Friday/Saturday**: Optional quick update
   - Use `--no-alternates` for speed if needed
   
3. **Sunday Morning**: Final full save
   - Get last adjustments before games

## Progress Visibility

The script now provides clear feedback:
- ⏱️ Estimated time (30-60 seconds)
- 📊 Progress counter [1/5], [2/5], etc.
- ✅ Results per stat type
- 📈 Final totals

**You'll never wonder if it's frozen again!**

## API Considerations

Alternate lines require more API calls:
- Standard props: 1 call per game
- Alternate lines: 1 additional call per game per stat type

**API Usage Example:**
- 5 games × 5 stat types = 25 extra calls for alternates
- Still well within free tier limits (500 calls/month)

## Summary

✅ **Automatic**: Alternates fetched by default  
✅ **Filtered**: Only useful odds (-450 to +200)  
✅ **Clear Progress**: Never looks frozen  
✅ **Fast Option**: `--no-alternates` when needed  
✅ **Smart Merging**: Each line tracked independently  

The system now saves a **complete picture** of the betting market for each week!

