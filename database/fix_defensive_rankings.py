#!/usr/bin/env python3
"""
Fix defensive rankings in database
1. Verify Tampa Bay's RB receiving yards rank should be ~30
2. Test updating Christian McCaffrey's records
3. Scale to fix all rankings in database
"""

from .database_manager import DatabaseManager
from .database_models import BoxScore, Prop
from collections import defaultdict
import tempfile
import os
import shutil

def export_database_to_csv(weeks, temp_dir):
    """Export database box scores to CSV format for position rankings calculation"""
    print(f"📥 Exporting weeks {weeks} from database to temporary CSV files...")
    
    from .database_enhanced_data_processor import DatabaseBoxScoreLoader
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
            from .database_manager import DatabaseManager
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
                        # Format expected by position_defensive_ranks.py
                        game_file = os.path.join(game_data_folder, f"hash_{away_team.replace(' ', '_')}_at_{home_team.replace(' ', '_')}_historical_odds.json")
                        
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
    
    # Player positions are now loaded from database - no CSV needed!
    print()
    print("📋 Player positions will be loaded from database")
    print()

def calculate_correct_rank_for_week(week, player, opp_team_full, stat_type, temp_dir):
    """Calculate what the rank SHOULD be for a specific week/player/opponent/stat"""
    
    from position_defensive_ranks import PositionDefensiveRankings
    
    print(f"🧮 Calculating correct rank for {player} vs {opp_team_full} ({stat_type}, Week {week})")
    print(f"   Using data from weeks 1-{week-1}")
    print()
    
    # Initialize position defensive rankings with max_week=week (will use weeks 1 through week-1)
    pos_ranks = PositionDefensiveRankings(data_dir=temp_dir)
    pos_ranks.calculate_position_defensive_stats(max_week=week)
    
    # Get the rank
    rank = pos_ranks.get_position_defensive_rank(opp_team_full, player, stat_type)
    
    # Debug: Show what we're looking for
    print(f"🔍 Debug info:")
    print(f"   Player: {player}")
    print(f"   Opponent: {opp_team_full}")
    print(f"   Stat type: {stat_type}")
    
    # Check player position
    player_position = pos_ranks.get_player_position(player)
    print(f"   Player position: {player_position}")
    
    if player_position:
        # Expected stat key
        position_stat_key = f"{player_position}_{stat_type.replace(' ', '_')}_Allowed"
        print(f"   Looking for stat key: {position_stat_key}")
        
        # Check if this key exists
        if position_stat_key in pos_ranks.position_defensive_rankings:
            rankings = pos_ranks.position_defensive_rankings[position_stat_key]
            print(f"   Found rankings for this stat (teams: {len(rankings)})")
            
            # Check if Tampa Bay is in the rankings
            if opp_team_full in rankings:
                print(f"   ✅ {opp_team_full} found in rankings: rank {rankings[opp_team_full]}")
            else:
                print(f"   ❌ {opp_team_full} NOT found in rankings")
                print(f"   Available teams: {list(rankings.keys())[:5]}...")
        else:
            print(f"   ❌ Stat key '{position_stat_key}' not found in rankings")
            print(f"   Available stat keys: {list(pos_ranks.position_defensive_rankings.keys())[:5]}...")
    
    print()
    
    return rank

def verify_tampa_bay_rank():
    """Step 1: Verify Tampa Bay's RB receiving yards rank should be ~30"""
    
    print("=" * 80)
    print("STEP 1: VERIFY TAMPA BAY RANK")
    print("=" * 80)
    print()
    
    # Create temporary directory and export weeks 1-5
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    print()
    
    try:
        export_database_to_csv([1, 2, 3, 4, 5], temp_dir)
        
        # Calculate rank for Week 6
        rank = calculate_correct_rank_for_week(
            week=6,
            player="Christian McCaffrey",
            opp_team_full="Tampa Bay Buccaneers",
            stat_type="Receiving Yards",
            temp_dir=temp_dir
        )
        
        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print(f"Current rank in database: 10")
        print(f"Calculated rank (weeks 1-5): {rank}")
        print(f"CBS Sports reported: ~30")
        print()
        
        if rank is None:
            print("❌ ERROR: Could not calculate rank")
            return None
        elif rank >= 28 and rank <= 32:
            print("✅ SUCCESS! Calculated rank matches CBS Sports expectation (~30)")
            print()
            print("The fix is working correctly!")
            return rank
        elif rank == 10:
            print("❌ STILL WRONG: Calculated rank is 10")
            print("   The fix may not have taken effect")
            return None
        else:
            print(f"⚠️  DIFFERENT: Calculated rank {rank} differs from CBS (~30)")
            print("   May need investigation, but could be due to:")
            print("   - Different methodology")
            print("   - Different data sources")
            return rank
    
    finally:
        # Clean up temp directory
        print()
        print(f"🧹 Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)

def test_update_mccaffrey(correct_rank):
    """Step 2: Test updating Christian McCaffrey's records"""
    
    print()
    print("=" * 80)
    print("STEP 2: TEST UPDATE - CHRISTIAN MCCAFFREY")
    print("=" * 80)
    print()
    
    if correct_rank is None:
        print("❌ Cannot proceed - no correct rank calculated")
        return False
    
    db_manager = DatabaseManager()
    
    with db_manager.get_session() as session:
        # Find McCaffrey's receiving yards props in Week 6 vs Tampa Bay
        props = session.query(Prop).filter(
            Prop.player.ilike('%McCaffrey%'),
            Prop.stat_type == 'Receiving Yards',
            Prop.week == 6,
            Prop.opp_team_full == 'Tampa Bay Buccaneers'
        ).all()
        
        print(f"Found {len(props)} props for McCaffrey receiving yards vs TB in Week 6")
        print()
        
        if not props:
            print("❌ No props found to update")
            return False
        
        # Show before
        print("BEFORE UPDATE:")
        for i, prop in enumerate(props[:3], 1):
            print(f"  {i}. Line: {prop.line}, Odds: {prop.odds}, Rank: {prop.team_pos_rank_stat_type}")
        if len(props) > 3:
            print(f"  ... and {len(props) - 3} more")
        print()
        
        # Update all McCaffrey props
        print(f"Updating {len(props)} props from rank 10 to rank {correct_rank}...")
        
        for prop in props:
            prop.team_pos_rank_stat_type = correct_rank
        
        session.commit()
        print("✅ Update committed")
        print()
        
        # Verify after
        print("AFTER UPDATE:")
        updated_props = session.query(Prop).filter(
            Prop.player.ilike('%McCaffrey%'),
            Prop.stat_type == 'Receiving Yards',
            Prop.week == 6,
            Prop.opp_team_full == 'Tampa Bay Buccaneers'
        ).all()
        
        for i, prop in enumerate(updated_props[:3], 1):
            print(f"  {i}. Line: {prop.line}, Odds: {prop.odds}, Rank: {prop.team_pos_rank_stat_type}")
        if len(updated_props) > 3:
            print(f"  ... and {len(updated_props) - 3} more")
        
        print()
        print("✅ Test update successful!")
        return True

def recalculate_all_rankings():
    """Step 3: Recalculate and update ALL rankings in database"""
    
    print()
    print("=" * 80)
    print("STEP 3: RECALCULATE ALL RANKINGS")
    print("=" * 80)
    print()
    
    response = input("⚠️  This will recalculate ALL defensive rankings in the database.\n   This is a heavy operation. Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    print()
    print("🚀 Starting full recalculation...")
    print()
    
    db_manager = DatabaseManager()
    
    # Get all distinct weeks in the database
    with db_manager.get_session() as session:
        weeks = session.query(Prop.week).distinct().order_by(Prop.week).all()
        weeks = [w[0] for w in weeks if w[0] is not None]
    
    print(f"Found props for weeks: {weeks}")
    print()
    
    # For each week, recalculate all ranks
    for week in weeks:
        print(f"=" * 80)
        print(f"PROCESSING WEEK {week}")
        print(f"=" * 80)
        print()
        
        if week == 1:
            print("Week 1: Setting to NULL (no historical data)")
            
            with db_manager.get_session() as session:
                week1_props = session.query(Prop).filter(Prop.week == 1).all()
                print(f"   Updating {len(week1_props)} props...")
                
                for prop in week1_props:
                    prop.team_pos_rank_stat_type = None  # No historical data for Week 1
                
                session.commit()
                print("   ✅ Week 1 updated")
            
            print()
            continue
        
        # Export weeks 1 through week-1 to temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            export_database_to_csv(list(range(1, week)), temp_dir)
            
            # Initialize position defensive rankings
            from position_defensive_ranks import PositionDefensiveRankings
            pos_ranks = PositionDefensiveRankings(data_dir=temp_dir)
            pos_ranks.calculate_position_defensive_stats(max_week=week)
            
            # Get all unique player/opponent/stat combinations for this week
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
                            prop.team_pos_rank_stat_type = new_rank
                            updated_count += 1
                
                session.commit()
                print(f"   ✅ Updated {updated_count} props")
                print()
        
        finally:
            shutil.rmtree(temp_dir)
    
    print()
    print("=" * 80)
    print("✅ ALL RANKINGS RECALCULATED")
    print("=" * 80)

def main():
    print("🏈 NFL DEFENSIVE RANKINGS FIX SCRIPT")
    print("=" * 80)
    print()
    
    # Step 1: Verify
    correct_rank = verify_tampa_bay_rank()
    
    if correct_rank is None:
        print()
        print("❌ Cannot proceed - verification failed")
        return
    
    # Step 2: Test update
    success = test_update_mccaffrey(correct_rank)
    
    if not success:
        print()
        print("❌ Cannot proceed - test update failed")
        return
    
    # Step 3: Full recalculation (with confirmation)
    recalculate_all_rankings()

if __name__ == "__main__":
    main()

