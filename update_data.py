"""
Weekly Data Update Script for Player Prop Optimizer
Run this script after each week's games to update player and team statistics
"""

import argparse
import sys
from enhanced_data_processor import EnhancedFootballDataProcessor
from datetime import datetime
import streamlit as st

def update_weekly_data(weeks: list = None, force_refresh: bool = False):
    """Update data for specified weeks"""
    print(f"🔄 Starting data update...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize the enhanced data processor
    processor = EnhancedFootballDataProcessor()
    
    if weeks is None:
        # Update up to current week
        weeks = list(range(1, min(processor.current_week + 1, 19)))
    
    print(f"📊 Updating data for weeks: {weeks}")
    
    try:
        # Update the season data
        processor.update_season_data(weeks=weeks, force_refresh=force_refresh)
        
        # Get summary of what was updated
        summary = processor.get_data_summary()
        
        print(f"\n✅ Data update completed!")
        print(f"📈 Total players: {summary['total_players']}")
        print(f"🎮 Total games: {summary['total_games']}")
        print(f"📅 Current week: {summary['current_week']}")
        
        # Show some sample players
        available_players = processor.get_available_players()
        if available_players:
            print(f"\n👥 Sample players with data:")
            for player in available_players[:10]:  # Show first 10
                print(f"  • {player}")
            if len(available_players) > 10:
                print(f"  ... and {len(available_players) - 10} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating data: {e}")
        return False

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='Update NFL player and team data')
    parser.add_argument('--weeks', type=int, nargs='+', 
                       help='Specific weeks to update (e.g., --weeks 1 2 3)')
    parser.add_argument('--force', action='store_true', 
                       help='Force refresh even if cache exists')
    parser.add_argument('--current-week', action='store_true',
                       help='Update up to current week only')
    
    args = parser.parse_args()
    
    if args.current_week:
        weeks = None  # Let the processor determine current week
    elif args.weeks:
        weeks = args.weeks
    else:
        # Default: update current week
        weeks = None
    
    success = update_weekly_data(weeks=weeks, force_refresh=args.force)
    
    if success:
        print("\n🎉 Data update successful! You can now run the Player Prop Optimizer.")
    else:
        print("\n💥 Data update failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
