# Real-Time Alternate Lines Update

## Summary

Successfully migrated the alternate lines feature from using cached JSON files to **fetching data in real-time** from The Odds API.

## What Changed

### Before
- Alternate lines loaded from static JSON files (e.g., `alternate_passing_yards.json`)
- Only Passing Yards had data available
- Required manual file creation for other stat types
- Data could be stale/outdated

### After  
- ✅ Alternate lines fetched in real-time from The Odds API
- ✅ Works for ALL stat types automatically
- ✅ Always has the latest odds
- ✅ Session caching for performance
- ✅ Progress indicators during fetch

## Technical Changes

### 1. AlternateLineManager Class Refactored

**Previous Implementation:**
```python
class AlternateLineManager:
    def __init__(self):
        self.alternate_lines = {}
        self._load_alternate_lines()  # Loaded from JSON files
```

**New Implementation:**
```python
class AlternateLineManager:
    def __init__(self, api_key: str, odds_data: List[Dict] = None):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.alternate_lines = {}
        self.odds_data = odds_data or []
        # Fetches from API in real-time
```

### 2. New fetch_alternate_lines_for_stat() Method

Fetches alternate lines directly from The Odds API:

```python
def fetch_alternate_lines_for_stat(self, stat_type: str, bookmaker: str = 'fanduel', progress_callback=None):
    """Fetch alternate lines for a specific stat type in real-time"""
    
    # Maps stat type to API market key
    market_key = self.stat_market_mapping.get(stat_type)
    # e.g., 'Passing Yards' → 'player_pass_yds_alternate'
    
    # Fetches from each event
    for event_id in event_ids:
        odds_url = f"{base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
        params = {
            'markets': market_key,
            'bookmakers': 'fanduel',
            'includeAltLines': 'true'
        }
        # Parse and cache results
```

### 3. Main Function Integration

**Added initialization with API key and odds data:**
```python
# After fetching main odds data
alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)

# Pre-fetch alternate lines for selected stat with progress indicator
with st.spinner(f"Fetching alternate lines for {selected_stat}..."):
    alt_line_manager.alternate_lines[selected_stat] = 
        alt_line_manager.fetch_alternate_lines_for_stat(selected_stat)
```

### 4. Stat Type to Market Mapping

All stat types are pre-configured:

```python
stat_market_mapping = {
    'Passing Yards': 'player_pass_yds_alternate',
    'Rushing Yards': 'player_rush_yds_alternate',
    'Receiving Yards': 'player_reception_yds_alternate',
    'Receptions': 'player_receptions_alternate',
    'Passing TDs': 'player_pass_tds_alternate',
    'Rushing TDs': 'player_rush_tds_alternate',
    'Receiving TDs': 'player_rec_tds_alternate'
}
```

## User Experience Improvements

### Before
1. Select stat type
2. See "No alternate lines available" for most stats
3. Manual JSON file creation required

### After
1. Select stat type
2. See spinner: "Fetching alternate lines for {Stat Type}..."
3. Alternate lines appear automatically (if available)
4. Subsequent views are instant (cached)

## Performance Characteristics

### API Calls
- **Per Stat Type**: ~5-15 API calls (depends on number of games)
- **Rate Limiting**: 0.3 seconds between calls
- **Total Time**: ~2-5 seconds per stat type on first load

### Caching
- **Session-based**: Results cached in memory during Streamlit session
- **Per Stat Type**: Each stat type cached independently
- **Refresh**: Clear by refreshing the page (🔄 button)

### API Usage
**Example for a typical week with 5 games:**
- Main props fetch: 5 API calls
- Alternate lines fetch (Passing Yards): 5 API calls
- **Total per stat type selection**: 10 API calls

**With caching:**
- First view of Passing Yards: 10 calls
- Switch to Rushing Yards: +5 calls (reuses main props)
- Back to Passing Yards: 0 calls (cached)

## Code Quality

### Error Handling
- Continues on individual event failures
- Gracefully handles missing alternate markets
- No crashes if API is unavailable

### Rate Limiting
```python
# Built-in delay between API calls
time.sleep(0.3)
```

### Progress Indicators
```python
# User sees what's happening
with st.spinner(f"Fetching alternate lines for {selected_stat}..."):
    # Fetch alternate lines
```

## API Requirements

### What You Need
- **Odds API Account** with alternate player props access
- **Paid Plan** recommended (free plans may not include alternate markets)
- **API Key** configured in `config.py`

### Market Availability
- All markets depend on FanDuel availability
- Not all stat types may have alternate lines for all games
- Availability varies by game/week

## Testing Recommendations

### 1. Basic Functionality Test
```bash
streamlit run player_prop_optimizer.py
```
1. Select "Passing Yards"
2. Wait for alternate lines to fetch
3. Look for rows with "+" suffix
4. Verify odds and lines match expected values

### 2. Multi-Stat Test
1. Select "Passing Yards" (waits ~3 seconds)
2. Switch to "Rushing Yards" (waits ~3 seconds)
3. Switch back to "Passing Yards" (instant - cached)

### 3. Error Handling Test
1. Temporarily use invalid API key
2. Verify system continues to work without alternate lines
3. Check for appropriate error messages

## Migration Notes

### What's Preserved
- ✅ 70% threshold calculation logic (unchanged)
- ✅ Closest alternate line matching (unchanged)
- ✅ Display format with "+" suffix (unchanged)
- ✅ Table grouping by player (unchanged)

### What Changed
- ❌ No longer uses JSON files
- ❌ `_load_alternate_lines()` removed
- ❌ `_parse_alternate_lines()` simplified
- ✅ `fetch_alternate_lines_for_stat()` added
- ✅ Real-time API integration added

### Backward Compatibility
- Old JSON files (like `alternate_passing_yards.json`) are **no longer used**
- Can safely delete them if desired
- No impact on functionality

## Future Enhancements

Potential improvements:
1. **Persistent Caching**: Save to disk to avoid re-fetching between sessions
2. **Batch Fetching**: Fetch multiple stat types at once
3. **Smart Prefetching**: Fetch alternate lines in background for all stats
4. **Custom Thresholds**: Allow user to configure target over rate (not just 70%)
5. **Multiple Alternates**: Show 60%, 70%, and 80% thresholds
6. **Async Fetching**: Use async/await for faster parallel requests

## Benefits

1. ✅ **Always Current**: Real-time data, not stale JSON
2. ✅ **All Stat Types**: Works for any stat type automatically
3. ✅ **No Manual Work**: No need to create/update JSON files
4. ✅ **Better UX**: Progress indicators show what's happening
5. ✅ **Maintainable**: Single source of truth (API)
6. ✅ **Scalable**: Easily add new stat types

## Conclusion

The migration from JSON files to real-time API fetching provides a **more robust, maintainable, and user-friendly** solution for alternate lines. Users now have access to all stat types with current data, without any manual file management.

