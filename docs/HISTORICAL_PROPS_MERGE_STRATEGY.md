# Historical Props Merge Strategy

## Overview

This document describes the implementation of a smart merge strategy that ensures historical prop data consistency while preserving props that were removed from the API (scratched players, injuries, etc.).

## The Problem

When a game transitions from "upcoming" to "historical":
- **Live captures**: Props are captured whenever the user refreshes the app (could be any time before the game)
- **Historical API**: Provides props from exactly 2 hours before game time (consistent snapshot)
- **Conflict**: We want consistency (2-hour snapshot) but also completeness (preserve removed props)

## The Solution: Smart Merge with Source Tracking

Props are now tracked by their source and automatically merged when games start.

### Key Components

#### 1. Database Schema Changes

**`database_models.py`**

Added two columns:

```python
class Game(Base):
    historical_merged = Column(Boolean, default=False)  # Tracks if historical merge completed

class Prop(Base):
    prop_source = Column(String, nullable=True)  # 'live_capture' or 'historical_api'
```

#### 2. Automatic Merge Logic

**`database_manager.py`**

Two new methods:

1. **`merge_historical_props(game_id, historical_props)`**
   - Merges historical API props with existing props
   - Matching key: `(player, stat_type, bookmaker)` (NOT line, since lines change)
   - If match found → **OVERWRITE** with historical data (2-hour snapshot)
   - If no match → **PRESERVE** as `live_capture` (scratched player)
   - If new → **ADD** from historical API

2. **`check_and_merge_historical_props(week, odds_api)`**
   - Runs on every app load (silent background check)
   - Finds games that: (a) have started, (b) not yet merged
   - Fetches historical props and merges
   - Marks game as `historical_merged=True` to avoid re-processing

#### 3. Historical Props Fetching

**`odds_api_with_db.py`**

New method: **`fetch_historical_props_for_game(game_id)`**
- Gets game from database
- Calculates 2 hours before game time
- Calls historical odds API with that timestamp
- Parses response into prop format
- Returns list of props with `prop_source='historical_api'`

#### 4. Integration

**`player_prop_optimizer.py`**

Added early in `main()` function:
```python
# Check and merge historical props for games that have started
db_manager.check_and_merge_historical_props(selected_week, odds_api=odds_api)
```

Runs silently - only console output for debugging.

---

## How It Works: Timeline Example

### Tuesday 12:00 PM - Initial Capture
User loads app, props are stored:
```
Props in DB:
- Mahomes, Passing Yards, 275.5, -110, prop_source='live_capture'
- Allen, Passing Yards, 285.5, -110, prop_source='live_capture'
```

### Friday - Mahomes Scratched
Mahomes injured, bookmaker removes his props. User refreshes:
```
Props in DB: (unchanged, game hasn't started)
- Mahomes, Passing Yards, 275.5, -110, prop_source='live_capture'
- Allen, Passing Yards, 285.5, -110, prop_source='live_capture'
```

### Sunday 1:30 PM - Game Started, Merge Triggered
Game started at 1:00 PM. User loads app:

**Important Note**: Historical API timing is uncertain. It might be available immediately, or require a delay after game start.

1. **Check runs automatically**:
   ```python
   check_and_merge_historical_props(week=7)
   ```

2. **Finds game needs merge**:
   - Game commenced at 1:00 PM (started)
   - `historical_merged=False` (not yet processed)

3. **Fetches historical props** (2 hours before = 11:00 AM):
   ```python
   historical_props = fetch_historical_props_for_game(game_id)
   # Returns: Allen only (Mahomes was already scratched by 11am)
   ```

4. **Smart merge**:
   - Allen: `(Allen, Passing Yards, fanduel)` found in both
     → **OVERWRITE**: 285.5 → 288.5, odds -110 → -115
     → Set `prop_source='historical_api'`
   
   - Mahomes: `(Mahomes, Passing Yards, fanduel)` only in live capture
     → **PRESERVE**: Keep 275.5, -110
     → Keep `prop_source='live_capture'`

5. **Mark complete**:
   ```python
   game.historical_merged = True
   ```

**Result in DB:**
```
- Allen, Passing Yards, 288.5, -115, prop_source='historical_api' ✅ Canonical
- Mahomes, Passing Yards, 275.5, -110, prop_source='live_capture' ✅ Preserved
```

---

## Retry Logic & Error Handling

### What Happens if Historical API Isn't Ready?

The system automatically retries failed historical fetches:

**Scenario 1: API Available Immediately**
```
Sunday 1:30 PM - Game started 30 minutes ago
→ Fetch historical props (11:00 AM data)
→ ✅ Success! Merge complete
→ Mark game.historical_merged = True
```

**Scenario 2: API Not Ready Yet**
```
Sunday 1:30 PM - Game started 30 minutes ago
→ Try to fetch historical props
→ ⚠️ No data returned
→ Log: "Game started 0.5 hours ago - will retry on next app load"
→ Keep game.historical_merged = False (allows retry)

Sunday 3:00 PM - User refreshes app
→ Try again automatically
→ ✅ Success! (API now ready)
→ Mark game.historical_merged = True
```

**Scenario 3: API Never Returns Data**
```
Sunday 1:30 PM → Retry
Monday 8:00 AM → Retry
Tuesday 10:00 AM → Retry
Wednesday 1:30 PM (48 hours later) → Give up
→ Log: "Game started 48.0 hours ago - marking as merged to stop retrying"
→ Mark game.historical_merged = True
→ Props remain as prop_source='live_capture'
```

### Key Features:
- ✅ **Automatic Retry**: Tries on every app load for up to 48 hours
- ✅ **No Crashes**: Failures are logged but never break the app
- ✅ **Graceful Degradation**: Props stay as 'live_capture' if historical data unavailable
- ✅ **Smart Timeout**: Stops retrying after 48 hours to avoid infinite loops

---

## Using the Data

### For Analysis (Consistent Data)

Query only historical API props:
```python
props = session.query(Prop).filter(
    Prop.game_id == game_id,
    Prop.prop_source == 'historical_api'
).all()
```

Returns: Only Allen (consistent 2-hour snapshot)

### For Completeness (All Props)

Query all props:
```python
props = session.query(Prop).filter(
    Prop.game_id == game_id
).all()
```

Returns: Allen + Mahomes (complete picture including scratched players)

---

## Console Logging (Debugging)

When merge runs, you'll see:
```
🔄 Found 1 game(s) needing historical merge for Week 7

📡 Processing: Kansas City Chiefs @ Buffalo Bills (commenced: 2025-10-20 13:00:00)
  📅 Fetching historical odds at: 2025-10-20T11:00:00Z (2 hours before 13:00:00)
  📊 Fetched 45 historical props from API
  ✏️  Updated: Josh Allen - Passing Yards (line: 288.5)
  ✏️  Updated: Travis Kelce - Receiving Yards (line: 68.5)
  ...
  💾 Preserved: Patrick Mahomes - Passing Yards (scratched/removed from historical)
  ✅ Merged: 44 updated, 0 added, 1 preserved

✅ Historical merge complete:
   1 game(s) processed
   44 props updated
   0 props added
   1 props preserved
```

---

## Future Consideration: Early Historical Fetch

**Current Behavior**: Historical props are fetched AFTER the game starts

**Future Option**: Fetch at exactly 2 hours before game time
- Would require scheduled job/cron running every 15 minutes
- Check for games starting in ~2 hours
- Fetch and store historical props proactively
- More consistent, but requires infrastructure

**Current approach is simpler**: On-demand fetch when game transitions to historical

---

## Database Migration

To add the new columns to existing database:

```python
# Run in Python console or migration script
from database_manager import DatabaseManager
from database_models import Base
from database_config import engine

# This will add the new columns if they don't exist
Base.metadata.create_all(bind=engine)
```

Or manually:
```sql
ALTER TABLE games ADD COLUMN historical_merged BOOLEAN DEFAULT FALSE;
ALTER TABLE props ADD COLUMN prop_source VARCHAR;
```

---

## Summary

✅ **Consistency**: All historical analysis uses 2-hour snapshot data
✅ **Completeness**: Scratched players are preserved for reference
✅ **Automatic**: Runs silently on every app load
✅ **Efficient**: Only processes each game once (via `historical_merged` flag)
✅ **Transparent**: Clear console logging for debugging
✅ **Backward Compatible**: Works with existing data structure

The system now maintains a complete and consistent historical record!

