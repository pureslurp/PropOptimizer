#!/usr/bin/env python3
"""
Cache Health Check Script
Run this script to check and fix any cache metadata corruption issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from datetime import datetime

def check_cache_health():
    """Check and fix cache metadata health"""
    print("🔍 NFL Prop Optimizer - Cache Health Check")
    print("=" * 50)
    
    db_manager = DatabaseManager()
    
    # Check for corrupted entries
    print("\n📊 Checking for corrupted cache metadata...")
    fixed_count = db_manager.fix_corrupted_cache_metadata()
    
    if fixed_count > 0:
        print(f"\n✅ Fixed {fixed_count} corrupted cache entries")
    else:
        print("\n✅ No corrupted cache entries found")
    
    # Check current cache status
    print("\n📊 Current cache status:")
    with db_manager.get_session() as session:
        from database.database_models import CacheMetadata
        cache_entries = session.query(CacheMetadata).all()
        
        if not cache_entries:
            print("  No cache entries found")
        else:
            now = datetime.utcnow()
            for entry in cache_entries:
                is_fresh = now < entry.expires_at
                hours_until_expiry = (entry.expires_at - now).total_seconds() / 3600 if is_fresh else 0
                
                print(f"  - {entry.data_type}:")
                print(f"    Last updated: {entry.last_updated}")
                print(f"    Expires at: {entry.expires_at}")
                print(f"    Record count: {entry.record_count}")
                print(f"    Status: {'🟢 Fresh' if is_fresh else '🔴 Expired'}")
                if is_fresh:
                    print(f"    Hours until expiry: {hours_until_expiry:.1f}")
                print()
    
    print("✅ Cache health check complete!")

if __name__ == "__main__":
    check_cache_health()
