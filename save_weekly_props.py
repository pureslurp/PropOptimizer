#!/usr/bin/env python3
"""
Save Weekly Props Script
Fetches current player props and saves them to a historical database.
Run this script weekly to build up a historical prop line database.
"""

import pandas as pd
import os
from datetime import datetime, timezone
import argparse
from enhanced_data_processor import EnhancedFootballDataProcessor
from odds_api import OddsAPI, AlternateLineManager
from config import ODDS_API_KEY, STAT_TYPES
from utils import get_current_week_from_schedule


def get_props_file_path(week_number):
    """Get the file path for props for a specific week"""
    return f"2025/WEEK{week_number}/props.csv"


def load_historical_props(week_number):
    """Load existing historical props data for a specific week"""
    props_file = get_props_file_path(week_number)
    
    if os.path.exists(props_file):
        try:
            df = pd.read_csv(props_file)
            print(f"✅ Loaded {len(df)} existing prop records for Week {week_number}")
            return df
        except Exception as e:
            print(f"⚠️ Error loading props: {e}")
            return pd.DataFrame()
    else:
        print(f"📝 No existing props file found for Week {week_number}. Will create new file.")
        return pd.DataFrame()


def fetch_current_props(include_alternates=True):
    """Fetch current player props from the Odds API"""
    print("🔄 Fetching current player props from Odds API...")
    
    odds_api = OddsAPI(ODDS_API_KEY)
    data_processor = EnhancedFootballDataProcessor()
    
    # Fetch odds data
    odds_data = odds_api.get_player_props()
    
    if not odds_data:
        print("❌ No odds data available")
        return pd.DataFrame()
    
    # Parse player props
    props_df = odds_api.parse_player_props(odds_data)
    
    if props_df.empty:
        print("❌ No player props found")
        return pd.DataFrame()
    
    # Update team assignments
    props_df = odds_api.update_team_assignments(props_df, data_processor)
    
    print(f"✅ Fetched {len(props_df)} standard player props")
    
    # Fetch alternate lines if requested
    if include_alternates:
        alternate_props = fetch_alternate_lines(odds_data, props_df)
        if not alternate_props.empty:
            # Combine standard and alternate props
            props_df = pd.concat([props_df, alternate_props], ignore_index=True)
            print(f"✨ Added {len(alternate_props)} alternate line props")
            print(f"📊 Total props (standard + alternates): {len(props_df)}")
    
    return props_df


def fetch_alternate_lines(odds_data, standard_props_df):
    """Fetch alternate lines for all stat types found in standard props"""
    print("\n🔄 Fetching alternate lines (this may take 30-60 seconds)...")
    print("   💡 Making multiple API calls to fetch all available lines")
    
    # Initialize alternate line manager
    alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
    
    # Get unique stat types from standard props
    stat_types = standard_props_df['Stat Type'].unique()
    
    print(f"   📋 Found {len(stat_types)} stat types to fetch: {', '.join(stat_types)}")
    print()
    
    all_alternate_props = []
    stat_count = 0
    
    for stat_type in stat_types:
        # Skip if not in mapping
        if stat_type not in alt_line_manager.stat_market_mapping:
            print(f"   ⏭️  Skipping {stat_type} (no alternate market available)")
            continue
        
        stat_count += 1
        print(f"   [{stat_count}/{len(stat_types)}] 📊 Fetching {stat_type} alternate lines...")
        
        # Fetch alternate lines for this stat type
        alt_lines_dict = alt_line_manager.fetch_alternate_lines_for_stat(stat_type)
        
        if not alt_lines_dict:
            print(f"        ⚠️  No alternate lines found for {stat_type}")
            continue
        
        # Count lines before filtering
        total_lines = sum(len(lines) for lines in alt_lines_dict.values())
        filtered_count = 0
        
        # Convert alternate lines to prop format
        for player_name, alt_lines in alt_lines_dict.items():
            # Filter by odds criteria (-450 to +200)
            for alt_line_data in alt_lines:
                odds = alt_line_data.get('odds', 0)
                
                # Check if odds are between +200 and -450
                if -450 <= odds <= 200:
                    filtered_count += 1
                    
                    # Find matching player in standard props to get team info
                    player_props = standard_props_df[
                        (standard_props_df['Player'] == player_name) &
                        (standard_props_df['Stat Type'] == stat_type)
                    ]
                    
                    if not player_props.empty:
                        base_prop = player_props.iloc[0]
                        
                        # Create alternate prop entry
                        alt_prop = {
                            'Player': player_name,
                            'Team': base_prop['Team'],
                            'Opposing Team': base_prop['Opposing Team'],
                            'Stat Type': stat_type,
                            'Line': alt_line_data['line'],
                            'Odds': odds,
                            'Bookmaker': base_prop.get('Bookmaker', 'FanDuel'),
                            'Market': base_prop.get('Market', '').replace('_alternate', '_alt'),
                            'Home Team': base_prop.get('Home Team', ''),
                            'Away Team': base_prop.get('Away Team', ''),
                            'Commence Time': base_prop.get('Commence Time', ''),
                            'is_alternate': True  # Flag to identify alternates
                        }
                        
                        all_alternate_props.append(alt_prop)
        
        print(f"        ✅ Found {filtered_count} alternate lines (odds between -450 and +200)")
    
    print()
    return pd.DataFrame(all_alternate_props)


def save_props_for_week(week_number, props_df, existing_df):
    """
    Save props for a specific week with smart merging:
    - If a player/stat exists in both old and new: REPLACE ALL lines for that player/stat (standard + alternates)
    - If a player/stat exists only in old: KEEP it (don't delete)
    - If a player/stat exists only in new: ADD it (only if game hasn't started)
    
    This handles cases where the line moves (e.g., 196.5 -> 200.5) by replacing the entire player/stat group.
    """
    if props_df.empty:
        print("⚠️ No props to save")
        return existing_df
    
    # Add metadata columns to new data
    props_df = props_df.copy()
    props_df['week'] = week_number
    props_df['saved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Ensure is_alternate column exists (False for standard props)
    if 'is_alternate' not in props_df.columns:
        props_df['is_alternate'] = False
    
    # Filter out props for games that have already started
    now = datetime.now(timezone.utc)
    if 'Commence Time' in props_df.columns:
        # Parse commence times and filter
        props_df['commence_datetime'] = pd.to_datetime(props_df['Commence Time'], errors='coerce')
        future_games_mask = (props_df['commence_datetime'].isna()) | (props_df['commence_datetime'] > now)
        started_games_count = (~future_games_mask).sum()
        
        if started_games_count > 0:
            print(f"🚫 Skipping {started_games_count} props for games that have already started")
        
        props_df = props_df[future_games_mask].copy()
        props_df = props_df.drop('commence_datetime', axis=1)
    
    if props_df.empty:
        print("⚠️ No props remaining after filtering (all games have started)")
        return existing_df
    
    # Create a grouping key for Player + Stat Type (not including Line)
    # This allows us to replace ALL lines for a player/stat when fresh data is available
    props_df['player_stat_key'] = (
        props_df['Player'].astype(str) + '_' +
        props_df['Stat Type'].astype(str)
    )
    
    if not existing_df.empty:
        # Create a copy to avoid modifying the original
        existing_df = existing_df.copy()
        
        # Create player_stat_key for existing data if it doesn't exist
        if 'player_stat_key' not in existing_df.columns:
            existing_df['player_stat_key'] = (
                existing_df['Player'].astype(str) + '_' +
                existing_df['Stat Type'].astype(str)
            )
        
        # Get unique player/stat combos
        existing_player_stats = set(existing_df['player_stat_key'].unique())
        new_player_stats = set(props_df['player_stat_key'].unique())
        
        # Calculate what's being updated vs added vs kept
        updated_player_stats = existing_player_stats & new_player_stats  # In both (replace all lines)
        added_player_stats = new_player_stats - existing_player_stats    # Only in new (add)
        kept_player_stats = existing_player_stats - new_player_stats     # Only in old (keep)
        
        # Count actual prop lines
        updated_old_count = existing_df[existing_df['player_stat_key'].isin(updated_player_stats)].shape[0]
        updated_new_count = props_df[props_df['player_stat_key'].isin(updated_player_stats)].shape[0]
        added_count = props_df[props_df['player_stat_key'].isin(added_player_stats)].shape[0]
        kept_count = existing_df[existing_df['player_stat_key'].isin(kept_player_stats)].shape[0]
        
        print(f"📊 Replacing {updated_old_count} old props with {updated_new_count} new props ({len(updated_player_stats)} player/stat combos)")
        print(f"➕ Adding {added_count} new props ({len(added_player_stats)} new player/stat combos)")
        print(f"✅ Keeping {kept_count} props ({len(kept_player_stats)} player/stat combos not in current fetch)")
        
        # Keep only old props for player/stat combos that aren't in the new data
        old_props_to_keep = existing_df[~existing_df['player_stat_key'].isin(updated_player_stats)]
        
        # Combine: old props (not updated) + all new props (replaces + additions)
        combined_df = pd.concat([old_props_to_keep, props_df], ignore_index=True)
    else:
        print(f"➕ Adding {len(props_df)} new props for Week {week_number}")
        combined_df = props_df
    
    # Sort by player name and stat type
    combined_df = combined_df.sort_values(['Player', 'Stat Type', 'Line'])
    
    return combined_df


def save_to_file(df, week_number):
    """Save the props dataframe to CSV in the week folder"""
    # Ensure the week directory exists
    week_folder = f"2025/WEEK{week_number}"
    os.makedirs(week_folder, exist_ok=True)
    
    # Select columns to save (exclude temporary columns)
    columns_to_save = [
        'week', 'saved_date', 'Player', 'Team', 'Opposing Team', 
        'Stat Type', 'Line', 'Odds', 'Bookmaker', 'Commence Time', 'is_alternate'
    ]
    
    # Only include columns that exist in the dataframe
    columns_to_save = [col for col in columns_to_save if col in df.columns]
    
    # Add any additional columns that exist (exclude temporary keys)
    for col in df.columns:
        if col not in columns_to_save and col not in ['player_stat_key', 'Opposing Team Full']:
            columns_to_save.append(col)
    
    save_df = df[columns_to_save].copy()
    
    # Save to CSV
    props_file = get_props_file_path(week_number)
    save_df.to_csv(props_file, index=False)
    print(f"💾 Saved {len(save_df)} props to {props_file}")
    
    # Print summary
    print(f"\n📈 Week {week_number} props summary:")
    print(f"   - Total props: {len(save_df)}")
    print(f"   - Unique players: {save_df['Player'].nunique()}")
    print(f"   - Stat types: {', '.join(save_df['Stat Type'].unique())}")
    
    # Check for box score
    box_score_file = f"{week_folder}/box_score_debug.csv"
    if os.path.exists(box_score_file):
        print(f"   - ✅ Box score data available")
    else:
        print(f"   - ⏳ Box score data not yet available (games haven't been played)")


def main():
    parser = argparse.ArgumentParser(description='Save weekly player props to historical database')
    parser.add_argument('--week', type=int, help='Week number to save (default: auto-detect current week)')
    parser.add_argument('--dry-run', action='store_true', help='Fetch props but do not save to file')
    parser.add_argument('--no-alternates', action='store_true', help='Skip fetching alternate lines (faster)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📊 NFL Player Props - Weekly Save Script")
    print("=" * 60)
    print()
    
    # Determine week number
    if args.week:
        week_number = args.week
        print(f"📅 Saving props for Week {week_number} (manual override)")
    else:
        week_number = get_current_week_from_schedule()
        print(f"📅 Auto-detected current week: {week_number} (based on NFL schedule)")
    
    print()
    
    # Load existing props for this week (if any)
    existing_df = load_historical_props(week_number)
    print()
    
    # Fetch current props (with or without alternates)
    include_alternates = not args.no_alternates
    if args.no_alternates:
        print("⚡ Fast mode: Skipping alternate lines")
    current_props_df = fetch_current_props(include_alternates=include_alternates)
    print()
    
    if current_props_df.empty:
        print("❌ No props fetched. Exiting.")
        return
    
    # Show sample of fetched props
    print("📋 Sample of fetched props:")
    print(current_props_df[['Player', 'Stat Type', 'Line', 'Odds']].head(10))
    print()
    
    # Prepare data for this week
    updated_df = save_props_for_week(week_number, current_props_df, existing_df)
    print()
    
    # Save to file (unless dry run)
    if args.dry_run:
        print("🔍 DRY RUN MODE - Not saving to file")
        print(f"   Would save {len(updated_df)} props to 2025/WEEK{week_number}/props.csv")
    else:
        save_to_file(updated_df, week_number)
    
    print()
    print("=" * 60)
    print("✅ Script completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

