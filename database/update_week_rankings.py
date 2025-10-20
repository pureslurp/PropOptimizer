#!/usr/bin/env python3
"""
Update defensive rankings for a specific week
"""

import sys
import os
import tempfile
import shutil
import json

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from database.database_models import Prop

def export_database_to_csv(weeks, temp_dir):
    """Export database box scores to CSV format for position rankings calculation"""
    print(f"📥 Exporting weeks {weeks} from database...")
    
    from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
    db_loader = DatabaseBoxScoreLoader()
    
    for week in weeks:
        print(f"   Week {week}...", end=" ")
        week_df = db_loader.load_week_data_from_db(week)
        
        if not week_df.empty:
            week_folder = os.path.join(temp_dir, f"WEEK{week}")
            os.makedirs(week_folder, exist_ok=True)
            
            # Need to also create game_data folder for team matchups
            game_data_folder = os.path.join(week_folder, "game_data")
            os.makedirs(game_data_folder, exist_ok=True)
            
            # Save box score CSV
            csv_path = os.path.join(week_folder, "box_score_debug.csv")
            week_df.to_csv(csv_path, index=False)
            
            # Create game data JSON files for team matchups
            db_manager = DatabaseManager()
            
            with db_manager.get_session() as session:
                games = session.query(
                    Prop.home_team,
                    Prop.away_team
                ).filter(
                    Prop.week == week
                ).distinct().all()
                
                for home_team, away_team in games:
                    if home_team and away_team:
                        # Create a minimal JSON file for the game
                        game_file = os.path.join(game_data_folder, f"hash_{away_team.replace(' ', '_')}_at_{home_team.replace(' ', '_')}_historical_odds.json")
                        
                        game_data = {
                            "data": {
                                "home_team": home_team,
                                "away_team": away_team
                            }
                        }
                        
                        with open(game_file, 'w') as f:
                            json.dump(game_data, f)
            
            print(f"✅ {len(week_df)} players")
        else:
            print("⚠️  No data")
    
    print()

def update_week_rankings(week):
    """Update defensive rankings for a specific week"""
    
    print("=" * 80)
    print(f"UPDATING DEFENSIVE RANKINGS FOR WEEK {week}")
    print("=" * 80)
    print()
    
    if week == 1:
        print("Week 1: Using default rank 16 (no historical data)")
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            week1_props = session.query(Prop).filter(Prop.week == 1).all()
            print(f"   Updating {len(week1_props)} props...")
            
            for prop in week1_props:
                prop.team_pos_rank_stat_type = None  # No historical data for Week 1
            
            session.commit()
            print("   ✅ Week 1 updated")
        
        print()
        return
    
    # Export weeks 1 through week-1 to temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        export_database_to_csv(list(range(1, week)), temp_dir)
        
        # Initialize position defensive rankings
        from position_defensive_ranks import PositionDefensiveRankings
        pos_ranks = PositionDefensiveRankings(data_dir=temp_dir)
        pos_ranks.calculate_position_defensive_stats(max_week=week)
        
        # Get all unique player/opponent/stat combinations for this week
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            combos = session.query(
                Prop.player,
                Prop.opp_team_full,
                Prop.stat_type
            ).filter(
                Prop.week == week
            ).distinct().all()
            
            print(f"   Calculating ranks for {len(combos)} unique player/opponent/stat combinations...")
            print()
            
            # Calculate rank for each combination
            rank_cache = {}
            for player, opp_team_full, stat_type in combos:
                if not opp_team_full or not stat_type or not player:
                    continue
                
                cache_key = (player, opp_team_full, stat_type)
                
                if cache_key not in rank_cache:
                    rank = pos_ranks.get_position_defensive_rank(opp_team_full, player, stat_type)
                    rank_cache[cache_key] = rank
                    
                    # Debug: Show a sample
                    if player == "Chuba Hubbard" and stat_type == "Receptions":
                        print(f"   DEBUG: {player} vs {opp_team_full} ({stat_type}) → rank {rank}")
            
            print(f"   Calculated {len(rank_cache)} ranks")
            print()
            
            # Update all props for this week
            print(f"   Updating props in database...")
            
            week_props = session.query(Prop).filter(Prop.week == week).all()
            updated_count = 0
            
            for prop in week_props:
                cache_key = (prop.player, prop.opp_team_full, prop.stat_type)
                
                if cache_key in rank_cache:
                    new_rank = rank_cache[cache_key]
                    if new_rank is not None:
                        # Debug: Show Chuba Hubbard updates
                        if prop.player == "Chuba Hubbard" and prop.stat_type == "Receptions":
                            print(f"   DEBUG: Updating {prop.player} line {prop.line}: {prop.team_pos_rank_stat_type} → {new_rank}")
                        prop.team_pos_rank_stat_type = new_rank
                        updated_count += 1
            
            session.commit()
            print(f"   ✅ Updated {updated_count} props for Week {week}")
            print()
    
    finally:
        print(f"🧹 Cleaning up temporary directory...")
        shutil.rmtree(temp_dir)
    
    print()
    print("=" * 80)
    print(f"✅ WEEK {week} RANKINGS UPDATED")
    print("=" * 80)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 update_week_rankings.py <week_number>")
        print("Example: python3 update_week_rankings.py 7")
        sys.exit(1)
    
    try:
        week = int(sys.argv[1])
    except ValueError:
        print("Error: Week number must be an integer")
        sys.exit(1)
    
    if week < 1 or week > 18:
        print("Error: Week number must be between 1 and 18")
        sys.exit(1)
    
    update_week_rankings(week)

if __name__ == "__main__":
    main()

