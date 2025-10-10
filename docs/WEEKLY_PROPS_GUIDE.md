# Weekly Props Historical Database Guide

## Overview

The **Weekly Props Historical Database** system allows you to save player prop data each week, building up a historical database over time. This enables you to:

- View past week's props with actual game results
- Compare historical performance against prop lines
- Track prop line movements over time
- Validate your prediction accuracy

## ⚠️ CRITICAL: You MUST Save Props Each Week!

**The Odds API only provides current/upcoming props. Once a week's games are played, you CANNOT retrieve those prop lines.**

This means:
- ✅ You CAN save props for the current week (before games start)
- ❌ You CANNOT save props for past weeks (after games are played)
- 🎯 You MUST run the save script each week to build your historical database

**If you miss saving a week's props, that data is lost forever!**

## How It Works

### 1. Saving Props Weekly

Run the `save_weekly_props.py` script each week (ideally BEFORE games start) to capture the current prop lines:

```bash
# Auto-detect current week and save props
python save_weekly_props.py

# Manually specify a week
python save_weekly_props.py --week 6

# Test without saving (dry run)
python save_weekly_props.py --dry-run
```

**When to run this:**
- Run BEFORE games start for the week
- Ideally Tuesday-Friday when lines are posted
- Can re-run multiple times - it will update existing records

### 2. Data Storage

Props are saved to `data/historical_props.csv` with the following information:
- Week number
- Player name
- Team and opposing team
- Stat type (Passing Yards, Receiving Yards, etc.)
- Prop line
- Odds
- Bookmaker
- Timestamp when saved

### 3. Viewing Historical Props

In the Streamlit app (`player_prop_optimizer.py`), use the **Week Selector** dropdown:

- **Current Week (X)**: Shows live props from the Odds API (default)
- **Week 1, Week 2, etc.**: Shows saved historical props with actual results

### 4. Understanding the "Actual" Column

When viewing past weeks, you'll see an **Actual** column that shows:

- **Green highlight**: Player went OVER the prop line ✅
- **Red highlight**: Player went UNDER the prop line ❌
- **"N/A"**: Player didn't record this stat (didn't play or no stats)

**Example:**

| Player | Line | Odds | Actual | Result |
|--------|------|------|--------|--------|
| J.K. Dobbins | 69.5 | -110 | **100** 🟢 | Hit over! |
| C. McCaffrey | 85.5 | -120 | **45** 🔴 | Went under |

## Workflow Example

### Week 6 Workflow

**Tuesday (October 8):**
```bash
# Props are posted, save them
python save_weekly_props.py
```
Output:
```
📊 NFL Player Props - Weekly Save Script
📅 Auto-detected current week: 6
✅ Loaded 0 existing historical prop records
🔄 Fetching current player props from Odds API...
✅ Fetched 350 current player props
➕ Adding 350 new props to empty database
💾 Saved 350 total props to data/historical_props.csv
```

**Tuesday-Sunday:**
- Use the app normally to analyze props
- Select "Current Week (6)" in the dropdown

**Monday (October 14 - After games):**
- Select "Week 6" in dropdown to see historical props
- View actual results vs. prop lines
- Analyze your accuracy

**Tuesday (October 15):**
```bash
# Save Week 7 props
python save_weekly_props.py
```
Output:
```
📅 Auto-detected current week: 7
✅ Loaded 350 existing historical prop records
🔄 Fetching current player props from Odds API...
✅ Fetched 340 current player props
➕ Adding 340 new props to empty database
💾 Saved 690 total props to data/historical_props.csv

📈 Historical database now contains:
   - Weeks: 6 to 7 (2 weeks)
   - Total props: 690
   - Unique players: 245
   - Stat types: Passing Yards, Rushing Yards, Receiving Yards, ...
```

## Database Management

### Updating Props for Same Week

If you want to update props for a week (e.g., lines changed), just re-run:

```bash
python save_weekly_props.py --week 6
```

This will:
- Remove old Week 6 records
- Add new Week 6 records
- Keep all other weeks intact

### Viewing Database

```bash
# See what's in the database
head -20 data/historical_props.csv
```

### Backup Database

```bash
# Backup your historical data
cp data/historical_props.csv data/historical_props_backup.csv
```

## Troubleshooting

### "No historical prop data available for Week X"

**Problem:** You tried to view a past week but haven't saved props for it.

**Solution:** 
```bash
# If the week hasn't happened yet, wait for props to be posted
# If you missed saving it, you can manually add it:
python save_weekly_props.py --week X
```

Note: You can only save props if they're currently available from the Odds API.

### "No box score data available for Week X"

**Problem:** Actual stats aren't available yet (games haven't been played).

**Solution:** Wait until after games are played and box scores are processed.

## Advanced Usage

### Automating Weekly Saves

**IMPORTANT:** You cannot backfill past weeks! Start from this week forward.

```bash
# Set up a weekly cron job (Mac/Linux)
# Run every Tuesday at 10 AM
crontab -e

# Add this line:
0 10 * * 2 cd /path/to/PropOptimizer && python save_weekly_props.py
```

### Analyzing Historical Accuracy

You can use the saved data to:
1. Compare your predictions vs. actual results
2. Calculate hit rate on props you would have bet
3. Track which stat types and players are most reliable
4. Identify line movement patterns

## Data Schema

The `historical_props.csv` file contains:

| Column | Description |
|--------|-------------|
| week | NFL week number (1-18) |
| saved_date | When the props were saved |
| Player | Player name |
| Team | Player's team |
| Opposing Team | Defense they're facing |
| Stat Type | Type of prop (Passing Yards, etc.) |
| Line | The prop line value |
| Odds | American odds for OVER |
| Bookmaker | Which bookmaker (FanDuel, DraftKings, etc.) |

## Tips

1. **Save Early**: Run the script Tuesday/Wednesday when lines first post
2. **Re-run Before Games**: If you want the latest lines, re-run Friday/Saturday
3. **Check Your Data**: Use `--dry-run` first to preview what will be saved
4. **Regular Schedule**: Set up a weekly reminder or automate it
5. **Keep Backups**: Periodically backup `data/historical_props.csv`

## Support

If you encounter issues:
1. Check that your API key is valid
2. Ensure you have box score data in `2025/WEEKX/` folders
3. Verify the `data/` directory exists and is writable
4. Check the script output for specific error messages

