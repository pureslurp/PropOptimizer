# 🏈 NFL Player Prop Optimizer - Integration Guide

## Overview

The Player Prop Optimizer now integrates with your existing `position_vs_team_analysis.py` script to use **real NFL data** instead of mock data. This provides accurate player performance history and team defensive rankings based on actual games.

## 🔄 Data Flow

```
1. Scrape Box Scores (dfs_box_scores.py)
   ↓
2. Position vs Team Analysis (position_vs_team_analysis.py) 
   ↓
3. Enhanced Data Processor (enhanced_data_processor.py)
   ↓
4. Player Prop Optimizer (player_prop_optimizer.py)
```

## 📁 File Structure

```
PropOptimizer/
├── dfs_box_scores.py                    # Your existing box score scraper
├── position_vs_team_analysis.py         # Your existing team analysis
├── enhanced_data_processor.py           # NEW: Integrates real data
├── player_prop_optimizer.py            # Updated to use real data
├── data_viewer.py                       # NEW: View player/team data
├── update_data.py                       # NEW: Weekly data updates
├── test_integration.py                  # NEW: Test the integration
├── config.py                           # Configuration
├── scoring_model.py                    # Scoring algorithm
├── utils.py                           # Helper functions
└── 2025/                              # Your existing data directory
    ├── WEEK1/
    │   ├── box_score_debug.csv
    │   └── DKSalaries_*.csv
    ├── WEEK2/
    └── ...
```

## 🚀 Getting Started

### Step 1: Scrape Initial Data
```bash
# Scrape data for specific weeks (run this first)
python dfs_box_scores.py 1 2 3 4 5

# This creates:
# - 2025/WEEK1/box_score_debug.csv
# - 2025/WEEK1/DKSalaries_*.csv
# - 2025/WEEK2/box_score_debug.csv
# - etc.
```

### Step 2: Test the Integration
```bash
# Test that everything works together
python test_integration.py
```

### Step 3: Run the Player Prop Optimizer
```bash
# Start the main application
streamlit run player_prop_optimizer.py
```

## 📊 Weekly Data Updates

### After Each Week's Games:
```bash
# Update data for new week (e.g., Week 6)
python dfs_box_scores.py 6

# Then update the optimizer's data cache
python update_data.py --week 6
```

### Force Refresh All Data:
```bash
# Re-process all weeks
python update_data.py --force
```

## 🔍 Data Viewing

### View Player and Team Statistics:
```bash
streamlit run data_viewer.py
```

This shows:
- **Player Stats**: Game-by-game performance, averages, consistency
- **Team Defense**: Defensive rankings by position
- **Player Analysis**: Most consistent players, over rates

## 🎯 How It Works

### Real Data Integration:
1. **Box Score Scraping**: `dfs_box_scores.py` scrapes FootballDB for game stats
2. **Team Analysis**: `position_vs_team_analysis.py` calculates how teams perform vs positions
3. **Data Processing**: `enhanced_data_processor.py` converts this to prop optimizer format
4. **Caching**: Data is cached for 1 week to avoid re-scraping
5. **Scoring**: Real player history and team defensive data feeds the scoring model

### Data Sources:
- **Player History**: From `box_score_debug.csv` files (game-by-game stats)
- **Team Defense**: From `position_vs_team_analysis.py` (DFS points allowed by position)
- **Matchups**: From DKSalaries files (team vs opponent mapping)

## 🔧 Configuration

### API Key:
```python
# In config.py
ODDS_API_KEY = "your_api_key_here"
```

### Data Directory:
```python
# In enhanced_data_processor.py
base_dir = "2025"  # Your existing data directory
```

## 🐛 Troubleshooting

### No Data Available:
```bash
# Check if you have scraped data
ls 2025/WEEK*/

# If no data, run the scraper first
python dfs_box_scores.py 1
```

### 50% Over Rates:
- This happens when players aren't in your scraped data
- Run `python dfs_box_scores.py` for more weeks to get more players
- Or check the data viewer to see which players have data

### Cache Issues:
```bash
# Clear cache and re-process
rm -rf data/
python update_data.py --force
```

## 📈 Benefits of Real Data

### Before (Mock Data):
- ❌ 50% over rates for most players
- ❌ Generic team defensive rankings
- ❌ No real player history
- ❌ Static data that never changes

### After (Real Data):
- ✅ Actual player performance history
- ✅ Real team defensive rankings based on games played
- ✅ Accurate over rates based on actual performance
- ✅ Updates weekly with new games
- ✅ Cached for performance (1 week cache)

## 🎮 Usage Examples

### Weekly Workflow:
```bash
# Monday: Scrape previous week's data
python dfs_box_scores.py 5

# Tuesday: Update optimizer data
python update_data.py --week 5

# Wednesday-Sunday: Use the optimizer
streamlit run player_prop_optimizer.py
```

### Data Exploration:
```bash
# View all available data
streamlit run data_viewer.py

# Test integration
python test_integration.py

# Check specific week
python position_vs_team_analysis.py --week 5
```

## 🔄 Migration from Mock Data

The system automatically falls back to mock data if no real data is available:

1. **First Run**: Uses mock data until you scrape real data
2. **After Scraping**: Automatically uses real data
3. **Missing Players**: Falls back to 50% for players not in scraped data
4. **Missing Teams**: Falls back to default defensive rankings

## 📞 Support

If you encounter issues:
1. Run `python test_integration.py` to diagnose
2. Check the data viewer to see what data is available
3. Ensure you've run the box score scraper for the weeks you want to analyze
4. Verify your data directory structure matches the expected format

## 🎉 Next Steps

Now that you have real data integration:
1. **Scrape more weeks** for better historical data
2. **Tune the scoring model** based on real performance
3. **Add more stat types** (touchdowns, interceptions, etc.)
4. **Enhance team analysis** with more sophisticated defensive metrics
