# CSV Mode Usage

## Overview

The app can be run in **CSV Mode** to use saved props data instead of making API calls. This is useful for:
- Avoiding API quota usage during development/testing
- Working offline or when API is unavailable
- Analyzing historical saved props data

## How to Use

### Command Line Flag

Run the Streamlit app with the `--use-csv` or `--csv` flag:

```bash
streamlit run player_prop_optimizer.py -- --use-csv
```

or

```bash
streamlit run player_prop_optimizer.py -- --csv
```

**Note:** The `--` before the flag is important! It tells Streamlit that the following arguments are for your app, not for Streamlit itself.

### What Happens in CSV Mode

1. ✅ **Skips API calls** - No requests made to The Odds API (saves quota!)
2. 📁 **Loads from CSV** - Automatically loads from current week's `2025/WEEK{X}/props.csv`
3. 📊 **Full functionality** - All features work: scoring, filtering, alternates, player selection, graphs
4. 🔧 **Clear indicator** - Shows "CSV Mode: Using saved props" message at startup

### Requirements

For CSV mode to work, you need:
- A saved props file for the current week: `2025/WEEK{X}/props.csv`
- To generate this file, run: `python save_weekly_props.py`

### Example Workflow

```bash
# 1. Save current week's props (uses API)
python save_weekly_props.py

# 2. Run app in CSV mode (no API usage)
streamlit run player_prop_optimizer.py -- --use-csv

# 3. Work with the data without using API quota!
```

## Normal Mode (Default)

Without the flag, the app runs in normal mode:

```bash
streamlit run player_prop_optimizer.py
```

This will:
1. Try to fetch from API first
2. Automatically fall back to CSV if API fails (quota exceeded, etc.)
3. Show appropriate messages for each scenario

## Comparison

| Feature | Normal Mode | CSV Mode (--use-csv) |
|---------|-------------|----------------------|
| API Calls | Yes, then CSV fallback | No, CSV only |
| API Quota Used | Yes | No |
| Real-time Data | Yes (if API available) | No (saved data) |
| Works Offline | Only with CSV fallback | Yes |
| Speed | Slower (API fetch) | Faster (local CSV) |

## Use Cases

### Development & Testing
```bash
# Don't waste API quota during dev
streamlit run player_prop_optimizer.py -- --use-csv
```

### API Quota Exhausted
```bash
# When you've hit your limit but still want to analyze
streamlit run player_prop_optimizer.py -- --use-csv
```

### Historical Analysis
```bash
# Analyze past week's data
# (manually change week detection or modify CSV path)
streamlit run player_prop_optimizer.py -- --use-csv
```

### Production (Real-time)
```bash
# Normal mode with automatic fallback
streamlit run player_prop_optimizer.py
```

## Troubleshooting

### Error: "No saved props found for Week X"

**Solution:** Save props first:
```bash
python save_weekly_props.py
```

### CSV Mode not working

**Check:**
1. Are you using `--` before the flag?
   - ✅ `streamlit run player_prop_optimizer.py -- --use-csv`
   - ❌ `streamlit run player_prop_optimizer.py --use-csv`
2. Is the props CSV file present?
   - Check: `ls 2025/WEEK{X}/props.csv`

### Want to test if flag is detected

Look for this message when app starts:
```
🔧 CSV Mode: Using saved props (--use-csv flag detected)
```

## Related Documentation

- [CSV Fallback Feature](CSV_FALLBACK_FEATURE.md) - Automatic CSV fallback
- [API Optimization](API_OPTIMIZATION_SUMMARY.md) - Reducing API usage
- [Weekly Props Guide](WEEKLY_PROPS_GUIDE.md) - Saving props data

