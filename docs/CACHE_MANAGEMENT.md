# Cache Management System

## Overview

The Player Prop Optimizer uses aggressive caching to improve performance. However, caches can become stale when new data is added (especially on Tuesdays when new week data arrives). This document explains the comprehensive cache protection system.

## Cache Files

### Main Caches (in `data/` directory)

1. **`player_season_cache.pkl`** (≈500KB)
   - Contains all player statistics for the season
   - Includes week-by-week stats, home/away splits
   - Rebuilt when: CSV files are newer OR age > 168 hours

2. **`team_defensive_cache.pkl`** (≈1.6KB)
   - Contains defensive rankings for all teams
   - Used for matchup scoring
   - Rebuilt when: CSV files are newer OR age > 168 hours

3. **`nfl_defensive_td_cache.pkl`** (≈1KB)
   - Contains NFL.com defensive TD data
   - Age limit: 168 hours (1 week)

4. **`defensive_rankings_week{N}.pkl`** (one per week)
   - Historical defensive rankings through week N-1
   - Used for historical analysis
   - Created on-demand for each week

## Cache Validation System

### Three-Layer Protection

The `_is_cache_valid()` function checks:

1. **File Exists**: Cache file must exist
2. **Age Check**: Cache must be less than `max_age_hours` old
3. **Source File Check**: For player/team caches, ALL CSV files must be older than cache

```python
# Example: Cache validation flow
if cache_exists and cache_age < 168_hours:
    # Check if any CSV is newer than cache
    for week in range(1, 19):
        if csv_file_exists and csv_time > cache_time:
            # Cache is INVALID - rebuild needed
            return False
    return True  # Cache is valid
return False  # Cache too old or doesn't exist
```

### Critical: CSV Timestamp Checking

**Problem Solved**: Before this fix, caches would persist even when new week data was added, causing "N/A" stats and incorrect calculations.

**Solution**: Both `player_season` and `team_defensive` caches now check ALL week CSV files. If ANY CSV is newer than the cache, the cache is invalidated.

This means:
- ✅ Add Week 7 data on Tuesday → Caches automatically rebuild
- ✅ Update Week 3 data → Caches automatically rebuild
- ✅ Add missing player to Week 5 → Caches automatically rebuild

## Cache Management Script

### Usage

```bash
# Check cache status
python manage_cache.py status

# Clear all caches (prompts for confirmation)
python manage_cache.py clear

# Show help
python manage_cache.py --help
```

### Status Command Output

```
======================================================================
Cache Status Report
======================================================================

Main Caches:
----------------------------------------------------------------------
✅ player_season        | Age:   0.0 days | Modified: 2025-10-14 11:30:35
✅ team_defensive       | Age:   0.0 days | Modified: 2025-10-14 11:30:35
⚠️  nfl_defensive_td     | Age:   8.2 days | Modified: 2025-10-10 07:09:08
   ⚠️  Cache is INVALID - will be rebuilt on next use

Historical Defensive Rankings Caches:
----------------------------------------------------------------------
   Week 3  | Age:  51.1 hours | Modified: 2025-10-12 08:35:07
   Week 6  | Age:   2.4 hours | Modified: 2025-10-14 09:18:03

======================================================================
```

## Programmatic Cache Management

### In Python Code

```python
from enhanced_data_processor import EnhancedFootballDataProcessor

# Get cache status
processor = EnhancedFootballDataProcessor()
status = processor.get_cache_status()

# Check specific cache
if not status['player_season']['is_valid']:
    print("Player season cache is stale!")

# Clear all caches
processor.clear_all_caches()
```

## When Caches Auto-Rebuild

Caches rebuild automatically when:

1. **Cache doesn't exist** - First run or after clearing
2. **Cache is too old** - Older than 168 hours (7 days)
3. **Source CSV is newer** - Any week's CSV has been updated
4. **Missing week tracking** - Old cache format without week numbers

## Weekly Workflow (Tuesdays)

### Typical Tuesday Process

1. **Run scripts to add new week data**
   ```bash
   python save_weekly_props.py  # Saves Week N props
   python save_box_scores.py    # Saves Week N-1 results
   ```

2. **Automatic cache invalidation**
   - New CSV files are created with current timestamp
   - Next time app runs, `_is_cache_valid()` detects newer CSVs
   - Caches are automatically rebuilt with new data

3. **Optional: Check cache status**
   ```bash
   python manage_cache.py status
   ```

### Manual Cache Clear (if needed)

If you suspect cache issues:

```bash
# Option 1: Use the management script
python manage_cache.py clear

# Option 2: Delete cache files directly
rm data/player_season_cache.pkl
rm data/team_defensive_cache.pkl
```

## Performance Considerations

### Cache Rebuild Times

- **Player Season Cache**: ~2-3 seconds for 6 weeks of data
- **Team Defensive Cache**: ~1-2 seconds (includes ESPN scraping)
- **Historical Rankings**: ~1 second per week

### When to Clear Manually

Normally, automatic validation handles everything. Clear manually when:

1. **Debugging**: Suspect calculation errors
2. **After code changes**: Updated stat calculation logic
3. **Data corruption**: Weird results that persist
4. **Testing**: Want to verify fresh calculations

## Troubleshooting

### Issue: Stats show "N/A" for players who played

**Cause**: Stale cache doesn't include recent weeks

**Solution**: 
```bash
python manage_cache.py status  # Check cache age
python manage_cache.py clear   # If needed
```

**Prevention**: Automatic CSV checking now prevents this!

### Issue: Calculations seem wrong

**Cause**: Cache might have old data or calculation logic changed

**Solution**:
```bash
python manage_cache.py clear
```

### Issue: App is slow on first run

**Cause**: Cache is being rebuilt (normal)

**Solution**: Wait for rebuild to complete. Subsequent runs will be fast.

## Best Practices

1. **Check cache status weekly** - Especially after adding new data
2. **Don't manually edit cache files** - Always let the system rebuild
3. **Clear cache after code changes** - If you modify calculation logic
4. **Monitor cache age** - If > 7 days and new data exists, investigate

## Technical Details

### Cache File Format

All caches use Python pickle format (`.pkl`):

```python
# player_season_cache.pkl structure
{
    'Player Name': {
        'team': 'Team Name',
        'Passing Yards': [244, 203, 139, ...],
        'Passing Yards_weeks': [1, 2, 3, ...],
        'Passing Yards_home': [203, 200, ...],
        'Passing Yards_home_weeks': [2, 4, ...],
        'Passing Yards_away': [244, 139, ...],
        'Passing Yards_away_weeks': [1, 3, ...],
        # ... other stats
    },
    # ... other players
}
```

### Cache Invalidation Logic

```python
def _is_cache_valid(cache_file, max_age_hours=24):
    # Layer 1: Existence check
    if not os.path.exists(cache_file):
        return False
    
    # Layer 2: Age check
    cache_age = get_file_age(cache_file)
    if cache_age >= max_age_hours:
        return False
    
    # Layer 3: Source file check (player/team caches only)
    if 'player_season' in cache_file or 'team_defensive' in cache_file:
        for week in range(1, 19):
            csv_file = f"2025/WEEK{week}/box_score_debug.csv"
            if csv_exists and csv_is_newer_than_cache:
                return False  # CSV was updated - rebuild cache
    
    return True  # Cache is valid
```

## Future Enhancements

Potential improvements:

1. **Cache versioning** - Invalidate when code changes
2. **Selective cache updates** - Only rebuild affected weeks
3. **Cache compression** - Reduce file sizes
4. **Cache warmup** - Rebuild in background
5. **Cache metrics** - Track hit rates and rebuild frequency

## Summary

✅ **Automatic Protection**: Caches auto-rebuild when CSV files are newer  
✅ **Manual Control**: `manage_cache.py` for status and clearing  
✅ **Dual Validation**: Age check + source file timestamp check  
✅ **Tuesday-Ready**: Handles new week data automatically  

The cache system is now robust against stale data issues!

