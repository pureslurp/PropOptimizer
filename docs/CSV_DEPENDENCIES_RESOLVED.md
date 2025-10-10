# CSV Dependencies - Resolution Summary

## Question 1: Can we delete `nfl_schedule.csv`?

### ✅ **YES - It's now optional!**

**What Changed:**
1. Updated `scoring_model.py` to accept `home_team` and `away_team` parameters
2. Updated all scoring call sites to pass home/away team info from API data
3. The API already provides this data in every event/prop
4. Props CSV already saves this data (columns: "Home Team", "Away Team")

**How it works:**
```python
# Old way (required nfl_schedule.csv):
is_home = data_processor.is_home_game(player_team, week)  # Looked up in CSV

# New way (uses API data):
score = scorer.calculate_comprehensive_score(
    player, opposing_team, stat_type, line, odds,
    home_team=row.get('Home Team'),      # From API
    away_team=row.get('Away Team')       # From API  
)
is_home = (player_team == home_team)  # Calculated directly
```

**Current Status:**
- `nfl_schedule.csv` is now **OPTIONAL**
- If present: Used as fallback (currently inactive since we pass home/away)
- If missing: System works fine using API data
- **Recommendation**: Keep it for now (it's small), but you can delete it

**Files Updated:**
- ✅ `scoring_model.py` - Added home_team/away_team parameters
- ✅ `player_prop_optimizer.py` - Passes home/away from props data  
- ✅ All scoring works with API data only

---

## Question 2: Can we delete `props.csv`?

### ⚠️ **Not yet - but here's why and what we can do**

**Current Workflow:**
```
1. save_weekly_props.py:
   - Fetches props from API
   - Saves to 2025/WEEK{X}/props.csv
   
2. player_prop_optimizer.py:
   - Reads props.csv
   - Scores props
   - Shows recommendations
```

**Why you originally created props.csv:**
- You wanted to "save historical odds" for later analysis
- At the time, you didn't know about the historical odds API
- Now we have `save_historical_odds.py` which uses the actual historical API

**The Issue:**
- `props.csv` is the **input** to the optimizer
- The optimizer currently expects to read from CSV
- It's not just for historical storage - it's part of the active workflow

**Three Options:**

### Option 1: Keep props.csv (Current Setup)
- ✅ Works perfectly
- ✅ Easy to view/debug props in spreadsheet
- ✅ Can analyze props without re-fetching from API
- ❌ Duplicates storage (have both props.csv and historical JSON)

### Option 2: Skip props.csv, Use Historical API for Analysis
- Fetch historical odds JSON files
- Build analyzer that reads JSON instead of CSV
- **Pros**: Single source of truth (historical JSON)
- **Cons**: Requires refactoring optimizer to read JSON

### Option 3: Hybrid Approach (Recommended)
**Keep props.csv for current week's live analysis:**
- `save_weekly_props.py` - saves current week props.csv (for live optimization)
- Delete old props.csv files after the week ends
- Use historical odds API for post-game analysis

**Store historical data differently:**
- `save_historical_odds.py` - saves historical JSON (for backtesting)
- Build separate analysis tool that reads historical JSON
- Compare predictions (from props.csv) vs actuals (from historical JSON)

---

## What We Have Now

### Historical Odds System:
```
save_historical_odds.py
├── Uses: utils.NFL_2025_WEEK_DATES
├── Fetches: Historical alternate lines from API
├── Saves: 2025/WEEK{X}/{eventId}_{teams}_historical_odds.json
└── Cost: ~50 credits per game
```

### Live Props System:
```
save_weekly_props.py  
├── Uses: Live odds API
├── Fetches: Current week props
├── Saves: 2025/WEEK{X}/props.csv
└── Used by: player_prop_optimizer.py
```

### Scoring System:
```
player_prop_optimizer.py
├── Reads: props.csv (current week)
├── Uses: enhanced_data_processor (player stats)
├── Uses: scoring_model (with API home/away data)
└── No longer needs: nfl_schedule.csv ✅
```

---

## Recommendations

### Immediate Action:
1. ✅ **Keep `nfl_schedule.csv`** (for now, it's optional backup)
2. ✅ **Keep `props.csv`** workflow (it's the optimizer input)
3. ✅ **Use `save_historical_odds.py`** for post-game analysis

### Future Enhancements:
1. **Backtest System**: Build tool to compare props.csv predictions vs historical JSON actuals
2. **CSV Cleanup**: Auto-delete old props.csv files after week ends  
3. **Unified Analyzer**: Read historical JSON instead of props.csv for past weeks

---

## Summary

### ✅ Accomplished Today:
1. Centralized week dates in `utils.py`
2. Eliminated hard dependency on `nfl_schedule.csv`
3. Created `save_historical_odds.py` for true historical data
4. Updated scoring to use API home/away data

### 📂 Files You Can Delete:
- **`nfl_schedule.csv`** - SAFE TO DELETE (system uses API data now)
- **Old props.csv files** - SAFE TO DELETE (keep current week only)

### 📂 Files You Should Keep:
- **Current week's `props.csv`** - Used by optimizer
- **Historical JSON files** - True historical odds data

### 🎯 Next Steps:
1. Test optimizer without nfl_schedule.csv (it should work!)
2. Build backtesting tool using historical JSON
3. Consider cleaning up old props.csv files automatically

