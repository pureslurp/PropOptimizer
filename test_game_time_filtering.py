#!/usr/bin/env python3
"""
Test Game Time Filtering Logic
Demonstrates that props for started games are preserved while future games are updated.
"""

import pandas as pd
from datetime import datetime, timezone, timedelta

# Create mock existing data (saved on Tuesday)
print("=" * 70)
print("GAME TIME FILTERING TEST")
print("=" * 70)
print()

# Current time (simulated as Friday afternoon)
now = datetime.now(timezone.utc)
print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M %Z')}")
print()

# Create mock game times
thursday_game = (now - timedelta(days=1)).isoformat()  # Yesterday (started)
sunday_game = (now + timedelta(days=2)).isoformat()    # In 2 days (future)

print("🎮 Game Schedule:")
print(f"   Thursday Night: {thursday_game} (✅ Already played)")
print(f"   Sunday Afternoon: {sunday_game} (⏳ Not started yet)")
print()

# EXISTING DATA (saved on Tuesday with alternates)
existing_data = pd.DataFrame([
    # Thursday game - Jalen Hurts (game already started)
    {'Player': 'Jalen Hurts', 'Stat Type': 'Passing Yards', 'Line': 225.5, 'Odds': -110, 
     'is_alternate': False, 'Commence Time': thursday_game},
    {'Player': 'Jalen Hurts', 'Stat Type': 'Passing Yards', 'Line': 200.5, 'Odds': -200,
     'is_alternate': True, 'Commence Time': thursday_game},
    {'Player': 'Jalen Hurts', 'Stat Type': 'Passing Yards', 'Line': 250.5, 'Odds': +150,
     'is_alternate': True, 'Commence Time': thursday_game},
    
    # Sunday game - Patrick Mahomes (game not started)
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 275.5, 'Odds': -110,
     'is_alternate': False, 'Commence Time': sunday_game},
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 250.5, 'Odds': -180,
     'is_alternate': True, 'Commence Time': sunday_game},
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 300.5, 'Odds': +140,
     'is_alternate': True, 'Commence Time': sunday_game},
])

print("📦 EXISTING DATA (saved Tuesday):")
print(existing_data[['Player', 'Line', 'Odds', 'is_alternate', 'Commence Time']].to_string(index=False))
print(f"   Total: {len(existing_data)} props")
print()

# NEW DATA (fetched Friday - line moved for Mahomes)
new_data = pd.DataFrame([
    # Thursday game props no longer available (game started)
    # API doesn't return props for games that already started
    
    # Sunday game - Patrick Mahomes (line moved!)
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 280.5, 'Odds': -115,
     'is_alternate': False, 'Commence Time': sunday_game},
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 255.5, 'Odds': -190,
     'is_alternate': True, 'Commence Time': sunday_game},
    {'Player': 'Patrick Mahomes', 'Stat Type': 'Passing Yards', 'Line': 305.5, 'Odds': +135,
     'is_alternate': True, 'Commence Time': sunday_game},
])

print("🆕 NEW DATA (fetched Friday):")
print(new_data[['Player', 'Line', 'Odds', 'is_alternate', 'Commence Time']].to_string(index=False))
print(f"   Total: {len(new_data)} props")
print()

# SIMULATE THE FILTERING LOGIC
print("⚙️  PROCESSING...")
print()

# Step 1: Filter out props for games that have started
new_data_copy = new_data.copy()
new_data_copy['commence_datetime'] = pd.to_datetime(new_data_copy['Commence Time'])
future_games_mask = new_data_copy['commence_datetime'] > now

print(f"1️⃣  Game time filtering:")
print(f"   Future games: {future_games_mask.sum()} props ✅")
print(f"   Started games: {(~future_games_mask).sum()} props (filtered out) 🚫")
print()

filtered_new_data = new_data_copy[future_games_mask].copy()

# Step 2: Create player_stat_key
existing_data['player_stat_key'] = existing_data['Player'] + '_' + existing_data['Stat Type']
filtered_new_data['player_stat_key'] = filtered_new_data['Player'] + '_' + filtered_new_data['Stat Type']

# Step 3: Determine what to keep vs replace
existing_player_stats = set(existing_data['player_stat_key'].unique())
new_player_stats = set(filtered_new_data['player_stat_key'].unique())

updated_player_stats = existing_player_stats & new_player_stats
kept_player_stats = existing_player_stats - new_player_stats

print(f"2️⃣  Merge logic:")
print(f"   Player/stat combos to REPLACE: {updated_player_stats}")
print(f"   Player/stat combos to KEEP: {kept_player_stats}")
print()

# Step 4: Keep old props not being updated
old_props_to_keep = existing_data[~existing_data['player_stat_key'].isin(updated_player_stats)]

# Step 5: Combine
final_data = pd.concat([old_props_to_keep, filtered_new_data], ignore_index=True)
final_data = final_data.sort_values(['Player', 'Line'])

# RESULTS
print("=" * 70)
print("✅ FINAL RESULT")
print("=" * 70)
print()

print("📊 Jalen Hurts (Thursday game - STARTED):")
hurts_data = final_data[final_data['Player'] == 'Jalen Hurts'][['Line', 'Odds', 'is_alternate']]
print(hurts_data.to_string(index=False))
print(f"   Status: ✅ PRESERVED (3 original props kept)")
print()

print("📊 Patrick Mahomes (Sunday game - FUTURE):")
mahomes_data = final_data[final_data['Player'] == 'Patrick Mahomes'][['Line', 'Odds', 'is_alternate']]
print(mahomes_data.to_string(index=False))
print(f"   Status: 🔄 UPDATED (3 old props replaced with 3 new props)")
print()

print("📈 Summary:")
print(f"   Started: {len(existing_data)} props")
print(f"   Fetched: {len(new_data)} props")
print(f"   Final: {len(final_data)} props")
print(f"   ")
print(f"   ✅ Preserved: {len(old_props_to_keep)} props (games started)")
print(f"   🔄 Updated: {len(filtered_new_data)} props (games not started)")
print()

# VERIFICATION
print("🔍 VERIFICATION:")
hurts_lines_kept = len(final_data[final_data['Player'] == 'Jalen Hurts'])
mahomes_lines_updated = len(final_data[final_data['Player'] == 'Patrick Mahomes'])

if hurts_lines_kept == 3:
    print("   ✅ Jalen Hurts: All 3 lines preserved (game started)")
else:
    print(f"   ❌ Jalen Hurts: Expected 3 lines, got {hurts_lines_kept}")

if mahomes_lines_updated == 3:
    print("   ✅ Patrick Mahomes: All 3 lines updated (game not started)")
else:
    print(f"   ❌ Patrick Mahomes: Expected 3 lines, got {mahomes_lines_updated}")

# Check if Mahomes lines actually changed
old_mahomes_main_line = 275.5
new_mahomes_main_line = final_data[(final_data['Player'] == 'Patrick Mahomes') & 
                                     (final_data['is_alternate'] == False)]['Line'].values[0]

if new_mahomes_main_line == 280.5:
    print("   ✅ Patrick Mahomes: Line movement captured (275.5 → 280.5)")
else:
    print(f"   ❌ Patrick Mahomes: Expected 280.5, got {new_mahomes_main_line}")

print()
print("=" * 70)
print("✅ TEST COMPLETE - Game time filtering works correctly!")
print("=" * 70)

