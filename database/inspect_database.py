#!/usr/bin/env python3
"""
Inspect the database structure and data
"""

import os
import sys
import toml

# Load secrets from .streamlit/secrets.toml
try:
    secrets = toml.load('.streamlit/secrets.toml')
    os.environ['DATABASE_URL'] = secrets['DATABASE_URL']
    print("✅ Loaded database URL from secrets.toml")
except Exception as e:
    print(f"❌ Error loading secrets: {e}")
    sys.exit(1)

from .database_manager import DatabaseManager
from .database_models import Game, Prop, BoxScore, CacheMetadata

def inspect_database():
    """Inspect the database structure and data"""
    print("🔍 Inspecting Database Structure and Data")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        
        # Test connection
        print("1. Testing database connection...")
        if not db_manager.test_connection():
            print("❌ Database connection failed!")
            return False
        
        # Check tables
        print("\n2. Checking database tables...")
        with db_manager.get_session() as session:
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db_manager.engine)
            tables = inspector.get_table_names()
            print(f"✅ Found tables: {tables}")
            
            # Check games table
            print("\n3. Checking games table...")
            games = session.query(Game).all()
            print(f"📊 Games count: {len(games)}")
            if games:
                print("Sample game:")
                game = games[0]
                print(f"  ID: {game.id}")
                print(f"  Home: {game.home_team}")
                print(f"  Away: {game.away_team}")
                print(f"  Time: {game.commence_time}")
                print(f"  Week: {game.week}")
                print(f"  Season: {game.season}")
            
            # Check props table
            print("\n4. Checking props table...")
            props = session.query(Prop).all()
            print(f"📊 Props count: {len(props)}")
            if props:
                print("Sample prop:")
                prop = props[0]
                print(f"  Game ID: {prop.game_id}")
                print(f"  Player: {prop.player}")
                print(f"  Stat Type: {prop.stat_type}")
                print(f"  Line: {prop.line}")
                print(f"  Odds: {prop.odds}")
                print(f"  Bookmaker: {prop.bookmaker}")
                print(f"  Is Alternate: {prop.is_alternate}")
            
            # Check cache metadata
            print("\n5. Checking cache metadata...")
            cache_entries = session.query(CacheMetadata).all()
            print(f"📊 Cache entries count: {len(cache_entries)}")
            for entry in cache_entries:
                print(f"  Data Type: {entry.data_type}")
                print(f"  Last Updated: {entry.last_updated}")
                print(f"  Expires At: {entry.expires_at}")
                print(f"  Record Count: {entry.record_count}")
            
            # Check box scores
            print("\n6. Checking box scores table...")
            box_scores = session.query(BoxScore).all()
            print(f"📊 Box scores count: {len(box_scores)}")
        
        print("\n🎉 Database inspection complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error during database inspection: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = inspect_database()
    sys.exit(0 if success else 1)
