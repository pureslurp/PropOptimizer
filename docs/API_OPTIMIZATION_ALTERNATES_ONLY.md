# API Optimization: Alternate Lines Only Mode

## Summary

**Optimization implemented:** Remove redundant main props API calls by using ONLY alternate lines as the data source.

**API Call Reduction:** ~45% reduction (from ~11 calls to ~6 calls per launch)

## Previous Flow (Before Optimization)

```
Launch player_prop_optimizer.py:
├── 1 call: GET /v4/sports/americanfootball_nfl/events (free, 0 credits)
├── 5 calls: GET /v4/sports/americanfootball_nfl/events/{eventId}/odds (main props)
│            Markets: player_pass_yds, player_pass_tds, etc. (~5 credits each)
└── 5 calls: GET /v4/sports/americanfootball_nfl/events/{eventId}/odds (alternates)
             Markets: player_pass_yds_alternate, etc. (~5 credits each)
─────────────────────────────────────────────────────────────────────────────
Total: ~11 API calls, ~50 credits
```

**Issue:** Main props and alternate props both provide the same data (player lines and odds). Fetching both is redundant.

## New Flow (After Optimization)

```
Launch player_prop_optimizer.py:
├── 1 call: GET /v4/sports/americanfootball_nfl/events (free, 0 credits)
└── 5 calls: GET /v4/sports/americanfootball_nfl/events/{eventId}/odds (alternates ONLY)
             Markets: player_pass_yds_alternate, etc. (~5 credits each)
             with includeAltLines=true
─────────────────────────────────────────────────────────────────────────────
Total: ~6 API calls, ~25 credits

Savings: ~5 API calls, ~25 credits (45% reduction)
```

## Code Changes

### 1. `odds_api.py` - `get_player_props()`
**Before:** Made individual API calls to get main props for each event
**After:** Only returns event metadata (IDs, teams, commence times)

```python
def get_player_props(self, sport: str = "americanfootball_nfl") -> List[Dict]:
    """
    OPTIMIZED: Only gets event IDs, not main props
    Saves ~5 API calls per launch
    """
    # Get events
    events = fetch_events()
    # Filter active events
    active_events = filter_active(events)
    # Return first 5 events (no props fetching)
    return active_events[:5]
```

### 2. `odds_api.py` - `parse_player_props()`
**Before:** Parsed main props from API response into DataFrame
**After:** Returns empty DataFrame (props come from alternates)

```python
def parse_player_props(self, odds_data: List[Dict]) -> pd.DataFrame:
    """Returns empty DataFrame - props come from alternate lines"""
    return pd.DataFrame(columns=[...])
```

### 3. `odds_api.py` - New `AlternateLineManager.convert_alternates_to_props_df()`
**New method** to convert alternate lines dictionary into props DataFrame format

```python
def convert_alternates_to_props_df(self, events_data: List[Dict]) -> pd.DataFrame:
    """Convert alternate lines dict to props DataFrame format"""
    # Iterate through all stat types and players
    # Create prop rows from alternate lines
    # Return as DataFrame
```

### 4. `player_prop_optimizer.py` - Updated flow
**Before:** 
1. Fetch main props → parse → score
2. Fetch alternates → add to main props

**After:**
1. Fetch events only
2. Fetch alternates only
3. Convert alternates to props DataFrame
4. Score all props (all are alternates)

## Benefits

1. **45% fewer API calls** - Saves ~5 calls per launch
2. **50% fewer credits** - Saves ~25 credits per launch  
3. **Faster loading** - Fewer network requests
4. **Same data quality** - Alternate lines provide complete coverage
5. **Simpler code** - Single data source instead of merging two

## Limitations

1. **Still limited to 5 games** - Can be increased if needed
2. **Can't batch events** - Odds API doesn't support batching player prop requests
3. **Requires alternate lines** - If API doesn't return alternates, no data (fallback to CSV mode handles this)

## API Endpoint Summary

### Used Endpoints:
1. **GET /v4/sports/americanfootball_nfl/events**
   - Cost: 0 credits (free)
   - Returns: Event IDs, teams, commence times
   - Called: 1x per launch

2. **GET /v4/sports/americanfootball_nfl/events/{eventId}/odds**
   - Cost: ~5 credits per call (varies)
   - Parameters:
     - `markets`: player_pass_yds_alternate, player_pass_tds_alternate, etc.
     - `includeAltLines`: true
     - `bookmakers`: fanduel
   - Called: 1x per game (5 games = 5 calls)

### Not Used (Removed):
- ~~GET /v4/sports/americanfootball_nfl/events/{eventId}/odds~~ (main props)
  - Was: ~5 calls × ~5 credits = ~25 credits
  - Now: Eliminated

## Testing

The optimization maintains the same functionality:
- All player props are still available
- Team assignments work correctly
- Scoring calculations unchanged
- Filters and UI unchanged
- CSV fallback mode unchanged

## Future Optimization Opportunities

**Waiting for Odds API response on:**
- Batch event support for player props
- Multi-event endpoint support for player markets
- More efficient alternate lines fetching

If these become available, could potentially reduce to **1-2 API calls total** instead of current 6.

