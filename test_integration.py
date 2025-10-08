#!/usr/bin/env python3
"""
Test script to verify the integration between position_vs_team_analysis and Player Prop Optimizer
"""

import os
import sys
from enhanced_data_processor import EnhancedFootballDataProcessor

def test_data_integration():
    """Test the integration of real data with the Player Prop Optimizer"""
    print("🧪 Testing Player Prop Optimizer Data Integration")
    print("=" * 50)
    
    # Initialize the enhanced data processor
    print("📊 Initializing Enhanced Data Processor...")
    processor = EnhancedFootballDataProcessor()
    
    # Check if we have any existing data
    print("\n📁 Checking for existing data...")
    base_dir = "2025"
    if os.path.exists(base_dir):
        week_dirs = [d for d in os.listdir(base_dir) if d.startswith('WEEK') and os.path.isdir(os.path.join(base_dir, d))]
        print(f"Found {len(week_dirs)} week directories: {sorted(week_dirs)}")
        
        if week_dirs:
            print("\n🔍 Checking data files...")
            for week_dir in sorted(week_dirs)[:3]:  # Check first 3 weeks
                week_path = os.path.join(base_dir, week_dir)
                files = os.listdir(week_path)
                
                has_box_scores = any(f.startswith('box_score') for f in files)
                has_dk_salaries = any(f.startswith('DKSalaries') for f in files)
                
                print(f"  {week_dir}: Box Scores={has_box_scores}, DKSalaries={has_dk_salaries}")
    else:
        print(f"❌ No data directory found at {base_dir}")
        print("💡 You need to run the box score scraper first:")
        print("   python dfs_box_scores.py 1 2 3  # For weeks 1, 2, 3")
        return False
    
    # Test data loading
    print("\n🔄 Testing data loading...")
    try:
        # This will try to load cached data or scrape new data
        summary = processor.get_data_summary()
        print(f"✅ Data loaded successfully!")
        print(f"   Total players: {summary['total_players']}")
        print(f"   Total games: {summary['total_games']}")
        print(f"   Current week: {summary['current_week']}")
        
        # Test some specific functionality
        print("\n🎯 Testing player data retrieval...")
        available_players = processor.get_available_players()
        if available_players:
            test_player = available_players[0]
            print(f"   Testing with player: {test_player}")
            
            # Test over rate calculation
            over_rate = processor.get_player_over_rate(test_player, "Passing Yards", 250)
            print(f"   Over rate for 250+ passing yards: {over_rate*100:.1f}%")
            
            # Test team defensive rank
            team_rank = processor.get_team_defensive_rank("San Francisco 49ers", "Passing Yards Allowed")
            print(f"   SF 49ers defensive rank vs passing: {team_rank}")
            
            # Test detailed stats
            detailed_stats = processor.get_player_detailed_stats(test_player)
            if detailed_stats:
                print(f"   Detailed stats available for {len(detailed_stats)} stat categories")
            else:
                print("   ⚠️ No detailed stats available")
        else:
            print("   ⚠️ No players available - data may need updating")
        
        print("\n✅ Integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        print("\n💡 This might be expected if no data has been scraped yet.")
        print("   Try running: python update_data.py")
        return False

def main():
    """Main function"""
    success = test_data_integration()
    
    if success:
        print("\n🎉 Integration test passed! You can now:")
        print("   1. Run the Player Prop Optimizer: streamlit run player_prop_optimizer.py")
        print("   2. View data: streamlit run data_viewer.py")
        print("   3. Update data weekly: python update_data.py")
    else:
        print("\n💥 Integration test failed. Please:")
        print("   1. Run the box score scraper first: python dfs_box_scores.py 1")
        print("   2. Then run this test again: python test_integration.py")

if __name__ == "__main__":
    main()
