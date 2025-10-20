#!/usr/bin/env python3
"""
Verify defensive ranking for any player/week combination
"""

import sys
import tempfile
import os
import shutil
from .database_manager import DatabaseManager
from .database_models import Prop
from position_defensive_ranks import PositionDefensiveRankings
from .database_enhanced_data_processor import DatabaseBoxScoreLoader

def export_weeks_to_temp(weeks):
    """Export database weeks to temporary directory"""
    temp_dir = tempfile.mkdtemp()
    print(f"📥 Exporting weeks {weeks} from database...")
    print()
    
    db_loader = DatabaseBoxScoreLoader()
    
    for week in weeks:
        print(f"   Week {week}...", end=" ")
        week_df = db_loader.load_week_data_from_db(week)
        
        if not week_df.empty:
            week_folder = os.path.join(temp_dir, f"WEEK{week}")
            os.makedirs(week_folder, exist_ok=True)
            
            # Create game_data folder for team matchups
            game_data_folder = os.path.join(week_folder, "game_data")
            os.makedirs(game_data_folder, exist_ok=True)
            
            # Save box score CSV
            csv_path = os.path.join(week_folder, "box_score_debug.csv")
            week_df.to_csv(csv_path, index=False)
            
            # Create game data JSON files
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
                        game_file = os.path.join(
                            game_data_folder,
                            f"hash_{away_team.replace(' ', '_')}_at_{home_team.replace(' ', '_')}_historical_odds.json"
                        )
                        
                        import json
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
    return temp_dir

def verify_player(player_name, week, opp_team_full, stat_type, expected_rank=None):
    """Verify a specific player's defensive ranking"""
    
    print("=" * 80)
    print(f"VERIFYING: {player_name} vs {opp_team_full}")
    print(f"Week {week} - {stat_type}")
    print("=" * 80)
    print()
    
    # Check what's currently in the database
    db_manager = DatabaseManager()
    
    with db_manager.get_session() as session:
        props = session.query(Prop).filter(
            Prop.player.ilike(f'%{player_name}%'),
            Prop.stat_type == stat_type,
            Prop.week == week,
            Prop.opp_team_full.ilike(f'%{opp_team_full}%')
        ).all()
        
        if not props:
            print(f"❌ No props found in database for {player_name} vs {opp_team_full} Week {week}")
            print(f"   Trying without opponent filter...")
            
            props = session.query(Prop).filter(
                Prop.player.ilike(f'%{player_name}%'),
                Prop.stat_type == stat_type,
                Prop.week == week
            ).all()
            
            if props:
                print(f"   Found {len(props)} props, showing opponents:")
                for prop in props[:5]:
                    print(f"     - vs {prop.opp_team_full} (rank: {prop.team_pos_rank_stat_type})")
            return
        
        current_rank = props[0].team_pos_rank_stat_type
        print(f"📊 Current rank in database: {current_rank}")
        print(f"   Found {len(props)} props for this player/opponent/stat")
        print()
    
    # Calculate what it should be
    print(f"🧮 Calculating correct rank using weeks 1-{week-1}...")
    print()
    
    # Export necessary weeks
    weeks_to_export = list(range(1, week))
    temp_dir = export_weeks_to_temp(weeks_to_export)
    
    try:
        # Initialize position defensive rankings
        pos_ranks = PositionDefensiveRankings(data_dir=temp_dir)
        pos_ranks.calculate_position_defensive_stats(max_week=week)
        
        # Get the rank
        calculated_rank = pos_ranks.get_position_defensive_rank(opp_team_full, player_name, stat_type)
        
        # Get player position for context
        player_position = pos_ranks.get_player_position(player_name)
        
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Player: {player_name}")
        print(f"Position: {player_position}")
        print(f"Opponent: {opp_team_full}")
        print(f"Stat: {stat_type}")
        print(f"Week: {week}")
        print()
        print(f"Current rank in database: {current_rank}")
        print(f"Calculated rank (weeks 1-{week-1}): {calculated_rank}")
        
        if expected_rank:
            print(f"CBS Sports reported: {expected_rank}")
            print()
            
            if calculated_rank == expected_rank:
                print("✅ MATCH! Calculated rank matches CBS Sports")
            elif abs(calculated_rank - expected_rank) <= 2:
                print(f"⚠️  CLOSE: Calculated rank is within 2 of CBS Sports (acceptable variance)")
            else:
                print(f"❌ MISMATCH: Calculated rank differs from CBS Sports by {abs(calculated_rank - expected_rank)}")
        else:
            print()
            print("ℹ️  No CBS Sports comparison provided")
        
        print("=" * 80)
        
        return calculated_rank
        
    finally:
        print()
        print(f"🧹 Cleaning up: {temp_dir}")
        shutil.rmtree(temp_dir)

def main():
    if len(sys.argv) < 5:
        print("Usage: python3 verify_single_player.py <player_name> <week> <opponent> <stat_type> [expected_rank]")
        print()
        print("Examples:")
        print("  python3 verify_single_player.py 'Christian McCaffrey' 6 'Tampa Bay Buccaneers' 'Receiving Yards' 30")
        print("  python3 verify_single_player.py 'Josh Allen' 4 'Baltimore Ravens' 'Passing Yards' 15")
        print("  python3 verify_single_player.py 'Derrick Henry' 5 'Buffalo Bills' 'Rushing Yards' 8")
        print()
        print("Stat types: 'Passing Yards', 'Passing TDs', 'Rushing Yards', 'Rushing TDs',")
        print("           'Receiving Yards', 'Receiving TDs', 'Receptions'")
        sys.exit(1)
    
    player_name = sys.argv[1]
    week = int(sys.argv[2])
    opponent = sys.argv[3]
    stat_type = sys.argv[4]
    expected_rank = int(sys.argv[5]) if len(sys.argv) > 5 else None
    
    verify_player(player_name, week, opponent, stat_type, expected_rank)

if __name__ == "__main__":
    main()

