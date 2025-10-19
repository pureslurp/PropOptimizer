#!/usr/bin/env python3
"""
Generate player_positions.csv from database props
Infer positions based on what stat types each player has
"""

from database.database_manager import DatabaseManager
from database.database_models import Prop
from utils import clean_player_name
import pandas as pd
import os

def generate_player_positions():
    """Generate player positions CSV from database"""
    
    print("🏈 Generating player positions from database...")
    print()
    
    db_manager = DatabaseManager()
    
    with db_manager.get_session() as session:
        # Get all unique players and their stat types
        players = session.query(Prop.player).distinct().all()
        
        print(f"Found {len(players)} unique players in database")
        print()
        
        player_positions = []
        
        for (player_name,) in players:
            if not player_name:
                continue
            
            # Get all stat types for this player
            stats = session.query(Prop.stat_type).filter(
                Prop.player == player_name
            ).distinct().all()
            
            stat_types = [s[0] for s in stats if s[0]]
            
            # Infer position from stat types
            position = infer_position(stat_types)
            
            cleaned_name = clean_player_name(player_name)
            
            player_positions.append({
                'player': player_name,
                'cleaned_name': cleaned_name,
                'position': position,
                'stat_types': ', '.join(stat_types)
            })
        
        # Create DataFrame
        df = pd.DataFrame(player_positions)
        
        # Sort by position and player name
        df = df.sort_values(['position', 'player'])
        
        # Save to CSV
        output_file = "2025/player_positions.csv"
        os.makedirs("2025", exist_ok=True)
        
        df.to_csv(output_file, index=False)
        
        print(f"✅ Saved {len(df)} players to {output_file}")
        print()
        
        # Show summary
        position_counts = df['position'].value_counts()
        print("Position breakdown:")
        for position, count in position_counts.items():
            print(f"  {position}: {count} players")
        
        print()
        print("Sample players:")
        print(df[['player', 'position', 'stat_types']].head(10).to_string(index=False))
        
        return df

def infer_position(stat_types):
    """Infer player position from their stat types"""
    
    has_passing = any('Passing' in st for st in stat_types)
    has_rushing = any('Rushing' in st for st in stat_types)
    has_receiving = any('Receiving' in st or 'Receptions' in st for st in stat_types)
    
    # QB: Has passing yards
    if has_passing:
        return 'QB'
    
    # RB: Has rushing AND receiving (but not passing)
    if has_rushing and has_receiving:
        return 'RB'
    
    # RB (rushing only): Has rushing but not receiving
    if has_rushing and not has_receiving:
        return 'RB'
    
    # WR/TE: Has receiving but not rushing or passing
    if has_receiving:
        # We can't distinguish WR vs TE from stat types alone
        # Default to WR (more common)
        return 'WR'
    
    # Unknown
    return 'UNKNOWN'

if __name__ == "__main__":
    generate_player_positions()

