#!/usr/bin/env python3
"""
Create player_positions table in database
"""

from .database_config import Base, engine
from .database_models import PlayerPosition

def create_table():
    print("Creating player_positions table...")
    
    # Create only the player_positions table
    PlayerPosition.__table__.create(engine, checkfirst=True)
    
    print("✅ Table created successfully!")
    print()
    print("Next steps:")
    print("1. Run: python3 scrape_player_positions_to_db.py")
    print("   This will scrape player positions from FootballDB.com")
    print()
    print("2. Then run: python3 fix_defensive_rankings.py")
    print("   This will recalculate all defensive rankings with the fix")

if __name__ == "__main__":
    create_table()

