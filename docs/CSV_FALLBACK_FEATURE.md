# CSV Fallback Feature

## 📋 Overview

When the API limit is reached or the API is unavailable, the app automatically falls back to loading props from the current week's saved CSV file. This ensures you can continue analyzing props even when the API quota is exhausted.

## 🔄 How It Works

### Normal Flow (API Available)
1. App fetches fresh data from The Odds API
2. Fetches alternate lines for all stat types
3. Calculates scores for all props
4. Displays results

### Fallback Flow (API Unavailable)
1. API call fails (quota exceeded, network error, etc.)
2. App automatically determines current NFL week
3. Loads props from `2025/WEEK{X}/props.csv`
4. Processes saved props (including alternates)
5. Calculates scores and displays results

## 🎯 Features

### Automatic Detection
- Detects API failures automatically
- No user intervention required
- Seamless transition to CSV data

### Current Week Detection
- Uses `get_current_week_from_schedule()` to determine current week
- Falls back to folder-based detection if schedule unavailable
- Ensures you get the most relevant props

### Complete Data
- CSV includes both main lines and alternate lines
- All necessary metadata preserved (teams, odds, etc.)
- Same scoring and analysis as API data

## 📊 User Experience

### When API Works
```
✅ Loaded 847 total props from 5 games
```

### When Using CSV Fallback
```
⚠️ API Error: [error message]
📁 API limit reached or unavailable. Loading from saved Week 6 props...
📁 Loaded 847 props from saved Week 6 CSV (API unavailable)
```

### When CSV Not Available
```
❌ No saved props found for Week 6. Please try again when API quota resets.
```

## 🔧 Technical Details

### CSV Format
The CSV must include these columns:
- `Player` - Player name
- `Team` - Player's team
- `Opposing Team` - Opponent (formatted as "vs TEAM" or "@ TEAM")
- `Stat Type` - Type of prop (Passing Yards, etc.)
- `Line` - Betting line
- `Odds` - American odds
- `Bookmaker` - Sportsbook name
- `Home Team` - Home team full name
- `Away Team` - Away team full name
- `Commence Time` - Game start time
- `is_alternate` - Boolean flag for alternate lines

### Data Processing
1. **CSV Loading**: `load_props_from_csv(week_num)`
   - Loads CSV from `2025/WEEK{week_num}/props.csv`
   - Converts CSV format to match API format
   - Handles is_alternate flags properly
   - Extracts full team names for lookups

2. **Fallback Logic**: In `main()`
   - Wrapped API calls in try-except
   - Sets `fallback_used` flag when API fails
   - Skips alternate line fetching (already in CSV)
   - Processes all rows including alternates

3. **Score Calculation**
   - Same scoring logic for both sources
   - Calculates L5, home/away rates, streaks
   - Maintains consistency across data sources

## 💾 Saving Props for Fallback

Props are automatically saved when using `save_weekly_props.py`:

```bash
python save_weekly_props.py
```

This saves current week's props to `2025/WEEK{X}/props.csv` for future fallback use.

## ⚙️ Configuration

No configuration needed! The fallback is automatic and uses:
- Current week from `2025/nfl_schedule.csv`
- Props from `2025/WEEK{X}/props.csv`

## 🚨 Error Handling

### API Errors Handled
- Quota exceeded (429 errors)
- Network timeouts
- Invalid responses
- Empty data returns

### Fallback Errors
- Missing CSV file → Clear error message
- Corrupted CSV → Falls back gracefully
- Wrong format → Error with instructions

## 📈 Benefits

1. **No Downtime**: Continue using app even when API unavailable
2. **Cost Savings**: Reduce API usage by using saved data when possible
3. **Reliability**: Always have data available from previous saves
4. **User-Friendly**: Automatic with clear messaging

## 🔍 Example Usage

### Scenario: API Quota Exhausted

```
User opens app → API quota at 100% → Fallback triggered
  ↓
App loads Week 6 CSV automatically
  ↓
User sees warning message but app works normally
  ↓
All features available (filtering, scoring, selection)
```

## 📝 Notes

- CSV data is static (not real-time)
- May not reflect latest odds changes
- Best used when API quota resets soon
- Consider upgrading API tier for real-time data

## 🔗 Related Features

- [API Optimization](API_OPTIMIZATION_SUMMARY.md) - Reducing API calls by 73%
- [Weekly Props Guide](WEEKLY_PROPS_GUIDE.md) - Saving props for fallback
- Check API usage: `python3 check_api_usage.py`

