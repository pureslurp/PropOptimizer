#!/usr/bin/env python3
"""
PyClean - Quick cache clearing utility

This is a simple wrapper around the cache management functionality
that can be used as a hotkey or quick command.

Usage:
    python pyclean.py        # Clear all caches (no confirmation)
    python pyclean.py --help # Show help
"""

import sys
import os
import argparse
import glob

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def pyclean():
    """Quick cache clearing without confirmation"""
    
    print("🧹 PyClean - Quick cache clearing...")
    print()
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        print("❌ Data directory not found")
        return
    
    cleared_count = 0
    
    # Clear main caches
    cache_types = ['player_season', 'team_defensive', 'nfl_defensive_td']
    
    for cache_type in cache_types:
        cache_file = os.path.join(data_dir, f"{cache_type}_cache.pkl")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"✅ Cleared {cache_type} cache")
            cleared_count += 1
    
    # Clear historical defensive rankings caches
    ranking_caches = glob.glob(os.path.join(data_dir, "defensive_rankings_week*.pkl"))
    
    for cache_file in ranking_caches:
        week = cache_file.split('week')[1].replace('.pkl', '')
        os.remove(cache_file)
        print(f"✅ Cleared defensive_rankings_week{week} cache")
        cleared_count += 1
    
    # Clear Streamlit cache directory if it exists
    streamlit_cache_dir = os.path.expanduser("~/.streamlit/cache")
    if os.path.exists(streamlit_cache_dir):
        import shutil
        shutil.rmtree(streamlit_cache_dir)
        print("✅ Cleared Streamlit cache directory")
        cleared_count += 1
    
    print()
    if cleared_count > 0:
        print(f"🎯 Cleared {cleared_count} cache files/directories")
        print("✅ All caches cleared! Data will be rebuilt on next access.")
    else:
        print("ℹ️  No caches found to clear")

def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(
        description="PyClean - Quick cache clearing utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python pyclean.py        # Clear all caches (no confirmation)
        """
    )
    
    args = parser.parse_args()
    pyclean()

if __name__ == "__main__":
    main()
