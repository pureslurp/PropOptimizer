# Early Historical Fetch Proposal

## Future Enhancement: Lock in 2-Hour Snapshot Earlier

### Current Behavior

- Historical props are fetched **AFTER** the game starts
- User might see live props at 1 hour before game, then they disappear when game starts
- Historical merge happens on next app load after game starts

### Desired Behavior

**Lock in the 2-hour snapshot as early as possible** (ideally right at 2 hours before game time)

This would ensure:
- Even at 1 hour before game, users see the canonical 2-hour snapshot
- No confusion about which lines are being used for analysis
- Props remain consistent from 2 hours before through game completion

---

## Key Question: When is Historical API Available?

**Need to investigate**: Can you call the historical odds API BEFORE the game starts?

### Scenario 1: Historical API Available at 2 Hours Before

If the API provides historical data at exactly 2 hours before game time:

```
Timeline:
11:00 AM - 2 hours before game
  ↓ Can we fetch historical props NOW?
  ↓ If YES → Lock them in immediately
  ↓
1:00 PM - Game starts
```

**If this works**: We can fetch early and lock in the canonical data

### Scenario 2: Historical API Only Available After Game Starts

If the API only provides historical data AFTER the game begins:

```
Timeline:
11:00 AM - 2 hours before game
  ↓ Historical API not available yet
  ↓
1:00 PM - Game starts
  ↓ NOW historical API becomes available
  ↓ Fetch on next app load (current implementation)
```

**If this is the case**: Current implementation is correct

---

## Implementation Options

### Option A: Scheduled Background Job (Ideal if API allows early fetch)

**When**: Run every 15 minutes

**Logic**:
```python
def scheduled_historical_fetch():
    """Run every 15 minutes via cron/scheduler"""
    current_time = datetime.utcnow()
    target_window_start = current_time - timedelta(minutes=15)
    target_window_end = current_time
    
    # Find games where (commence_time - 2 hours) is in the last 15 minutes
    games = session.query(Game).filter(
        Game.commence_time - timedelta(hours=2) >= target_window_start,
        Game.commence_time - timedelta(hours=2) <= target_window_end,
        Game.historical_merged == False
    ).all()
    
    for game in games:
        # Fetch and store historical props right at 2-hour mark
        historical_props = fetch_historical_props_for_game(game.id)
        merge_historical_props(game.id, historical_props)
        game.historical_merged = True
```

**Advantages**:
- Props locked at exactly 2 hours before
- Consistent data from 2 hours before through game completion
- Users never see fluctuating live props close to game time

**Requirements**:
- Cron job or scheduler (systemd, supervisord, etc.)
- Server/machine running 24/7
- Verify API allows historical fetch before game starts

---

### Option B: Opportunistic Early Fetch (Simpler)

**When**: On app load, if game is between 2 hours before and game start

**Logic**:
```python
def check_and_merge_historical_props(week, odds_api):
    current_time = datetime.utcnow()
    
    # Find games where we're in the window: [2 hours before, game start]
    games_in_window = session.query(Game).filter(
        Game.week == week,
        Game.commence_time - timedelta(hours=2) <= current_time,
        Game.commence_time > current_time,
        Game.historical_merged == False
    ).all()
    
    for game in games_in_window:
        # Try to fetch historical props early
        try:
            historical_props = fetch_historical_props_for_game(game.id)
            if historical_props:
                merge_historical_props(game.id, historical_props)
                game.historical_merged = True
        except Exception as e:
            # API might not allow early fetch - that's OK, try after game starts
            pass
```

**Advantages**:
- No infrastructure needed (works within app)
- Automatically tries early fetch if user loads app in that window
- Falls back to post-game fetch if early fetch fails

**Disadvantages**:
- Requires user to load app in that 2-hour window
- Not guaranteed to catch every game

---

### Option C: Hybrid Approach

1. **Opportunistic**: Try to fetch in 2-hour window if user loads app
2. **Fallback**: Fetch after game starts if not already fetched

```python
def check_and_merge_historical_props(week, odds_api):
    current_time = datetime.utcnow()
    
    # Games that need historical props
    games_needing_merge = session.query(Game).filter(
        Game.week == week,
        Game.historical_merged == False,
        or_(
            # Case 1: In 2-hour window (try early fetch)
            and_(
                Game.commence_time - timedelta(hours=2) <= current_time,
                Game.commence_time > current_time
            ),
            # Case 2: Game has started (must fetch now)
            Game.commence_time <= current_time
        )
    ).all()
    
    for game in games_needing_merge:
        try:
            historical_props = fetch_historical_props_for_game(game.id)
            if historical_props:
                merge_historical_props(game.id, historical_props)
                game.historical_merged = True
        except Exception as e:
            # If early fetch fails, that's OK - will try again after game starts
            if game.commence_time <= current_time:
                # Game has started, this is critical
                print(f"❌ Failed to fetch historical props for started game: {e}")
            else:
                # Game hasn't started yet, not critical
                print(f"⚠️ Early historical fetch not available, will retry: {e}")
```

---

## Testing Required

Before implementing early fetch, test:

1. **Can historical API be called before game starts?**
   ```python
   # Try fetching 2 hours before a game that hasn't started yet
   game_time = "2025-10-20T13:00:00Z"  # 1 PM game
   fetch_time = "2025-10-20T11:00:00Z"  # 11 AM (2 hours before)
   
   # At 11:05 AM, try calling:
   response = requests.get(
       f"{base_url}/historical/sports/americanfootball_nfl/events/{event_id}/odds",
       params={'date': fetch_time, ...}
   )
   ```

2. **What does API return if called too early?**
   - Empty data?
   - Error message?
   - Actual props?

3. **When does historical data become available?**
   - At exactly 2 hours before?
   - Only after game completes?
   - Some delay after 2-hour mark?

---

## Recommendation

**Phase 1** (Current): Post-game fetch ✅ **COMPLETED**
- Simple, reliable, works with current API understanding
- Ensures we always get historical data

**Phase 2** (Future): Test early fetch capability
- Manually test API at different times
- Document when historical data becomes available
- Implement Option B or C based on findings

**Phase 3** (Optional): Scheduled job
- Only if perfect consistency is critical
- Requires infrastructure investment
- Consider API usage costs

---

## API Usage Considerations

Each historical fetch = 1 API call per game

**Current approach**: ~1 call per game (when it transitions to historical)

**Scheduled approach**: ~1 call per game (at exactly 2 hours before)

**Hybrid approach**: ~1-2 calls per game (early attempt + fallback if needed)

All approaches have similar API costs, so choose based on desired UX rather than cost.

---

## Summary

**Current Implementation**: ✅ Working, reliable, simple

**Future Enhancement**: Lock in 2-hour snapshot earlier IF the API supports it

**Next Steps**:
1. Test if historical API works before game starts
2. Document findings in this file
3. Implement hybrid approach if early fetch is possible
4. Maintain current post-game fetch as reliable fallback

The current system ensures consistency and completeness. Early fetch would enhance UX but is not critical for correctness.

