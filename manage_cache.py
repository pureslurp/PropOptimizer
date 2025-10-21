#!/usr/bin/env python3
"""
Cache Management Script for Player Prop Optimizer

This script provides easy cache management functionality that was referenced
in the documentation but was missing from the codebase.

Usage:
    python manage_cache.py status    # Check cache status
    python manage_cache.py clear     # Clear all caches
    python manage_cache.py --help    # Show help
"""

import sys
import os
import argparse
from datetime import datetime
import glob

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_cache_status():
    """Get detailed cache status information"""
    
    print("=" * 70)
    print("Cache Status Report")
    print("=" * 70)
    print()
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        print("❌ Data directory not found")
        return
    
    # Check main caches
    cache_types = ['player_season', 'team_defensive', 'nfl_defensive_td']
    
    print("Main Caches:")
    print("-" * 70)
    
    for cache_type in cache_types:
        cache_file = os.path.join(data_dir, f"{cache_type}_cache.pkl")
        
        if os.path.exists(cache_file):
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            age_days = age_hours / 24
            
            # Simple validity check (age-based)
            is_valid = age_hours < 168  # 7 days
            
            status_icon = "✅" if is_valid else "⚠️ "
            print(f"{status_icon} {cache_type:<20} | Age: {age_days:5.1f} days | Modified: {cache_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if not is_valid:
                print(f"   ⚠️  Cache is INVALID - will be rebuilt on next use")
        else:
            print(f"❌ {cache_type:<20} | Not found")
    
    print()
    
    # Check historical defensive rankings caches
    ranking_caches = glob.glob(os.path.join(data_dir, "defensive_rankings_week*.pkl"))
    
    if ranking_caches:
        print("Historical Defensive Rankings Caches:")
        print("-" * 70)
        
        for cache_file in sorted(ranking_caches):
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            # Extract week number from filename
            week = cache_file.split('week')[1].replace('.pkl', '')
            
            print(f"   Week {week:<2} | Age: {age_hours:5.1f} hours | Modified: {cache_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Historical Defensive Rankings Caches:")
        print("-" * 70)
        print("   No historical ranking caches found")
    
    print()
    print("=" * 70)

def clear_all_caches():
    """Clear all cache files"""
    
    print("🧹 Clearing all caches...")
    print()
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        print("❌ Data directory not found")
        return
    
    # Clear main caches
    cache_types = ['player_season', 'team_defensive', 'nfl_defensive_td']
    
    for cache_type in cache_types:
        cache_file = os.path.join(data_dir, f"{cache_type}_cache.pkl")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"✅ Removed {cache_type} cache")
        else:
            print(f"ℹ️  {cache_type} cache not found")
    
    # Clear historical defensive rankings caches
    ranking_caches = glob.glob(os.path.join(data_dir, "defensive_rankings_week*.pkl"))
    
    for cache_file in ranking_caches:
        week = cache_file.split('week')[1].replace('.pkl', '')
        os.remove(cache_file)
        print(f"✅ Removed defensive_rankings_week{week} cache")
    
    if not ranking_caches:
        print("ℹ️  No historical ranking caches found")
    
    print()
    print("✅ All caches cleared. Data will be rebuilt on next access.")

def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(
        description="Cache Management Script for Player Prop Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python manage_cache.py status    # Check cache status
    python manage_cache.py clear     # Clear all caches
        """
    )
    
    parser.add_argument(
        'action',
        choices=['status', 'clear'],
        help='Action to perform'
    )
    
    args = parser.parse_args()
    
    if args.action == 'status':
        get_cache_status()
    elif args.action == 'clear':
        # Ask for confirmation
        response = input("Are you sure you want to clear all caches? (y/N): ")
        if response.lower() in ['y', 'yes']:
            clear_all_caches()
        else:
            print("Cache clearing cancelled.")

if __name__ == "__main__":
    main()
