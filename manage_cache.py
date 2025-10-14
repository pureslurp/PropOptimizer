#!/usr/bin/env python3
"""
Cache Management Utility for Player Prop Optimizer

Use this script to check cache status and clear caches when needed.
Especially useful after adding new week data on Tuesdays.

Usage:
    python manage_cache.py status     # Show cache status
    python manage_cache.py clear      # Clear all caches
    python manage_cache.py --help     # Show this help
"""

import sys
from enhanced_data_processor import EnhancedFootballDataProcessor

def show_status():
    """Display cache status"""
    processor = EnhancedFootballDataProcessor()
    status = processor.get_cache_status()
    
    print("=" * 70)
    print("Cache Status Report")
    print("=" * 70)
    print()
    
    # Main caches
    print("Main Caches:")
    print("-" * 70)
    for cache_name in ['player_season', 'team_defensive', 'nfl_defensive_td']:
        if cache_name in status:
            info = status[cache_name]
            if info['exists']:
                valid_icon = "✅" if info['is_valid'] else "⚠️ "
                print(f"{valid_icon} {cache_name:20} | Age: {info['age_days']:5.1f} days | Modified: {info['last_modified']}")
                if not info['is_valid']:
                    print(f"   ⚠️  Cache is INVALID - will be rebuilt on next use")
            else:
                print(f"❌ {cache_name:20} | Not cached")
    
    # Defensive rankings caches
    if 'defensive_rankings' in status:
        print()
        print("Historical Defensive Rankings Caches:")
        print("-" * 70)
        for week_key, info in sorted(status['defensive_rankings'].items()):
            week_num = week_key.replace('week_', '')
            print(f"   Week {week_num:2} | Age: {info['age_hours']:5.1f} hours | Modified: {info['last_modified']}")
    
    print()
    print("=" * 70)
    print()
    
    # Check if any caches are invalid
    has_invalid = any(
        info.get('is_valid') == False 
        for cache_name, info in status.items() 
        if isinstance(info, dict) and 'is_valid' in info
    )
    
    if has_invalid:
        print("⚠️  WARNING: Some caches are invalid and will be rebuilt automatically.")
        print("   This is normal after adding new week data.")
    else:
        print("✅ All caches are valid and up to date.")
    
    print()

def clear_caches():
    """Clear all caches"""
    print()
    response = input("Are you sure you want to clear all caches? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    print()
    processor = EnhancedFootballDataProcessor()
    processor.clear_all_caches()
    print()

def show_help():
    """Show help message"""
    print(__doc__)

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        show_status()
    elif command == 'clear':
        clear_caches()
    elif command in ['--help', '-h', 'help']:
        show_help()
    else:
        print(f"Unknown command: {command}")
        print()
        show_help()
        sys.exit(1)

if __name__ == '__main__':
    main()

