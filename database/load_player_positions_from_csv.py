#!/usr/bin/env python3
"""
Load player positions from existing CSV into database
"""

import pandas as pd
from .database_manager import DatabaseManager
from .database_models import PlayerPosition
from datetime import datetime

def load_positions_from_csv():
    """Load player positions from CSV file into database"""
    
    csv_path = "2025/player_positions.csv"
    
    print(f"📥 Loading player positions from {csv_path}...")
    print()
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Found {len(df)} players in CSV")
        print()
        
        # Filter to only NFL offensive positions (QB, WR, RB, TE)
        nfl_offensive_positions = ['QB', 'WR', 'RB', 'TE']
        df_filtered = df[df['position'].isin(nfl_offensive_positions)].copy()
        
        print(f"🏈 Filtered to {len(df_filtered)} NFL offensive players (QB, WR, RB, TE)")
        print(f"   QB: {len(df_filtered[df_filtered['position'] == 'QB'])}")
        print(f"   WR: {len(df_filtered[df_filtered['position'] == 'WR'])}")
        print(f"   RB: {len(df_filtered[df_filtered['position'] == 'RB'])}")
        print(f"   TE: {len(df_filtered[df_filtered['position'] == 'TE'])}")
        print()
        
        # Use filtered dataframe
        df = df_filtered
        
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            added = 0
            updated = 0
            skipped = 0
            
            for idx, row in df.iterrows():
                try:
                    # Get fields from CSV
                    player_name = row.get('formatted_name') or row.get('player', '')
                    cleaned_name = row.get('cleaned_name', '')
                    position = row.get('position', '')
                    team = row.get('team', '')
                    
                    if not player_name or not cleaned_name or not position:
                        skipped += 1
                        continue
                    
                    # Check if player already exists
                    existing = session.query(PlayerPosition).filter(
                        PlayerPosition.player == player_name
                    ).first()
                    
                    if existing:
                        # Update
                        existing.position = position
                        existing.team = team if team else None
                        existing.cleaned_name = cleaned_name
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        # Insert
                        new_player = PlayerPosition(
                            player=player_name,
                            cleaned_name=cleaned_name,
                            position=position,
                            team=team if team else None
                        )
                        session.add(new_player)
                        added += 1
                    
                    # Commit each player individually to avoid batch conflicts
                    session.commit()
                    
                    # Progress updates
                    if (added + updated) % 100 == 0:
                        print(f"   Processed {added + updated} players...")
                
                except Exception as e:
                    session.rollback()
                    print(f"   ⚠️  Error with player {player_name}: {e}")
                    skipped += 1
                    continue
        
        print()
        print(f"✅ Complete!")
        print(f"   Added: {added} players")
        print(f"   Updated: {updated} players")
        print(f"   Skipped: {skipped} players")
        print(f"   Total: {added + updated} players")
        print()
        
        # Show position breakdown
        with db_manager.get_session() as session:
            from sqlalchemy import func
            
            position_counts = session.query(
                PlayerPosition.position,
                func.count(PlayerPosition.id)
            ).group_by(PlayerPosition.position).all()
            
            print("Position breakdown:")
            for position, count in sorted(position_counts, key=lambda x: x[1], reverse=True):
                print(f"  {position}: {count}")
        
        print()
        print("🎉 Player positions successfully loaded into database!")
        
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_path}")
        print("   Please run: python3 scrape_player_positions.py first")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_positions_from_csv()

