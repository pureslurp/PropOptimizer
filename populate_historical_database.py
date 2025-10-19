#!/usr/bin/env python3
"""
Populate database with historical odds from JSON files using validated logic
"""

import os
import sys
import json
import glob
import toml
import pandas as pd
from datetime import datetime
from database_manager import DatabaseManager
from database_models import Prop
from enhanced_data_processor import EnhancedFootballDataProcessor
from odds_api_with_db import OddsAPIWithDB

def populate_historical_database():
    """Process all historical JSON files and populate the database"""
    
    print("🚀 POPULATING DATABASE WITH HISTORICAL ODDS")
    print("="*60)
    
    # Load database configuration
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        os.environ['DATABASE_URL'] = secrets['DATABASE_URL']
        print("✅ Loaded database URL from secrets.toml")
    except Exception as e:
        print(f"❌ Error loading secrets: {e}")
        sys.exit(1)
    
    db_manager = DatabaseManager()
    api = OddsAPIWithDB(os.environ.get('ODDS_API_KEY', 'dummy_key'))
    data_processor = EnhancedFootballDataProcessor()
    
    # Market key mapping to stat types
    market_to_stat_type = {
        'player_pass_yds_alternate': 'Passing Yards',
        'player_rush_yds_alternate': 'Rushing Yards',
        'player_reception_yds_alternate': 'Receiving Yards',
        'player_receptions_alternate': 'Receptions',
        'player_pass_tds_alternate': 'Passing TDs',
        'player_rush_tds_alternate': 'Rushing TDs',
        'player_reception_tds_alternate': 'Receiving TDs'
    }
    
    # Process all weeks
    weeks_to_process = [1, 2, 3, 4, 5, 6, 7]
    total_props_processed = 0
    total_props_saved = 0
    
    for week_num in weeks_to_process:
        print(f"\n{'='*50}")
        print(f"📅 PROCESSING WEEK {week_num}")
        print(f"{'='*50}")
        
        week_folder = f"2025/WEEK{week_num}/game_data"
        
        if not os.path.exists(week_folder):
            print(f"📁 Week {week_num}: No game_data folder found")
            continue
        
        # Find all JSON files for this week
        json_files = glob.glob(os.path.join(week_folder, "*_historical_odds.json"))
        
        if not json_files:
            print(f"   No JSON files found in {week_folder}")
            continue
        
        print(f"📁 Found {len(json_files)} JSON files for Week {week_num}")
        
        week_props_processed = 0
        week_props_saved = 0
        
        for json_file in json_files:
            print(f"\n📄 Processing: {os.path.basename(json_file)}")
            
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                event_data = data.get('data', {})
                event_id = event_data.get('id', '')
                home_team = event_data.get('home_team', '')
                away_team = event_data.get('away_team', '')
                commence_time_str = event_data.get('commence_time', '')
                
                print(f"   🏈 Game: {away_team} @ {home_team}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📅 Game time: {commence_time_str}")
                
                # Parse commence time
                try:
                    commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                except:
                    commence_time = None
                
                # Calculate week from game date
                game_week = week_num  # Use the folder week as expected
                if commence_time:
                    try:
                        season_start = datetime(2025, 9, 4, tzinfo=commence_time.tzinfo)
                        days_diff = (commence_time - season_start).days
                        calculated_week = max(1, min(18, (days_diff // 7) + 1))
                        if calculated_week != week_num:
                            print(f"   ⚠️  Week mismatch: folder={week_num}, calculated={calculated_week}")
                    except:
                        print(f"   ⚠️  Could not calculate week from date")
                
                # Process all props from this game using actual API event ID
                game_props = []
                
                for bookmaker_data in event_data.get('bookmakers', []):
                    bookmaker_name = bookmaker_data.get('title', 'Unknown')
                    
                    for market_data in bookmaker_data.get('markets', []):
                        market_key = market_data.get('key', '')
                        stat_type = market_to_stat_type.get(market_key, 'Unknown')
                        
                        if stat_type == 'Unknown':
                            continue
                        
                        for outcome in market_data.get('outcomes', []):
                            player_name = outcome.get('description', '')
                            line = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            if not player_name or player_name == 'Unknown' or player_name == 'Over' or player_name == 'Under' or player_name == '':
                                continue
                            
                            # Create prop data
                            prop_data = {
                                'Player': player_name,
                                'Team': '',  # Will be filled by API processing
                                'Opp. Team': '',  # Will be filled by API processing
                                'Opp. Team Full': '',  # Will be filled by API processing
                                'Stat Type': stat_type,
                                'Line': line,
                                'Odds': odds,
                                'Bookmaker': bookmaker_name,
                                'Home Team': home_team,
                                'Away Team': away_team,
                                'Commence Time': commence_time.isoformat() if commence_time else '',
                                'game_id': event_id,  # Use actual API event ID
                                'is_alternate': True
                            }
                            
                            game_props.append(prop_data)
                            week_props_processed += 1
                
                if game_props:
                    print(f"   📊 Found {len(game_props)} props for this game")
                    
                    # Convert to DataFrame and process through API pipeline
                    props_df = pd.DataFrame(game_props)
                    processed_df = api.update_team_assignments(props_df, data_processor)
                    
                    # Process each prop with defensive ranking logic
                    processed_props = []
                    for _, row in processed_df.iterrows():
                        try:
                            # Get defensive ranking for this stat type
                            team_pos_rank = None
                            opp_team = row.get('Opp. Team', '')
                            stat_type = row.get('Stat Type', '')
                            
                            if opp_team and stat_type:
                                # Validate week calculation
                                if game_week < 1 or game_week > 18:
                                    print(f"   ⚠️  Invalid week calculated: {game_week}, defaulting to Week 1")
                                    game_week = 1
                                
                                if game_week == 1:
                                    # Week 1: No historical data, use default rank
                                    team_pos_rank = 16
                                else:
                                    # Use data from previous weeks only
                                    max_week = game_week - 1
                                    
                                    # Create data processor with limited historical data
                                    historical_processor = EnhancedFootballDataProcessor(max_week=max_week)
                                    team_pos_rank = historical_processor.get_team_defensive_rank(opp_team, stat_type)
                                    
                                    if team_pos_rank is None:
                                        # Don't use default 16 for non-Week 1 games
                                        team_pos_rank = None
                            else:
                                team_pos_rank = None
                            
                            # Create prop data with all columns populated
                            # Convert numpy types to Python native types
                            prop_data = {
                                'game_id': event_id,  # Use actual API event ID
                                'player': str(row.get('Player', '')),
                                'stat_type': str(row.get('Stat Type', '')),
                                'line': float(row.get('Line', 0)),
                                'odds': int(row.get('Odds', 0)),
                                'bookmaker': str(row.get('Bookmaker', '')),
                                'is_alternate': bool(row.get('is_alternate', True)),
                                'timestamp': datetime.utcnow(),
                                'player_team': str(row.get('Team', '')),
                                'opp_team': str(row.get('Opp. Team', '')),
                                'opp_team_full': str(row.get('Opp. Team Full', '')),
                                'team_pos_rank_stat_type': int(team_pos_rank) if team_pos_rank is not None else None,
                                'week': game_week,
                                'commence_time': commence_time,
                                'home_team': str(row.get('Home Team', '')),
                                'away_team': str(row.get('Away Team', ''))
                            }
                            
                            processed_props.append(prop_data)
                            week_props_saved += 1
                            
                        except Exception as e:
                            print(f"   ❌ Error processing prop for {row.get('Player', 'Unknown')}: {e}")
                            continue
                    
                    # Save props for this game
                    if processed_props:
                        try:
                            # Create game data using actual API event ID
                            game_data = {
                                'id': event_id,  # Use actual API event ID for traceability
                                'home_team': home_team,
                                'away_team': away_team,
                                'commence_time': commence_time,
                                'week': game_week,
                                'season': 2025
                            }
                            
                            # Use the API's store_props_to_db method
                            api.store_props_to_db(processed_props, [game_data])
                            print(f"   ✅ Saved {len(processed_props)} props for this game")
                        except Exception as e:
                            print(f"   ❌ Error saving props for this game: {e}")
                else:
                    print(f"   📊 No valid props found for this game")
            
            except Exception as e:
                print(f"   ❌ Error processing {os.path.basename(json_file)}: {e}")
                continue
        
        print(f"\n📊 Week {week_num} Summary:")
        print(f"   📈 Props processed: {week_props_processed}")
        print(f"   💾 Props saved: {week_props_saved}")
        
        total_props_processed += week_props_processed
        total_props_saved += week_props_saved
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"🎉 HISTORICAL DATABASE POPULATION COMPLETE")
    print(f"{'='*60}")
    print(f"📈 Total props processed: {total_props_processed}")
    print(f"💾 Total props saved: {total_props_saved}")
    print(f"📊 Success rate: {(total_props_saved/total_props_processed*100):.1f}%" if total_props_processed > 0 else "N/A")
    
    # Verify database population
    print(f"\n🔍 VERIFYING DATABASE POPULATION...")
    try:
        total_props_in_db = db_manager.session.query(Prop).count()
        print(f"📊 Total props in database: {total_props_in_db}")
        
        # Check for any NULL values in critical columns
        null_checks = [
            ('player_team', 'Player Team'),
            ('opp_team', 'Opposing Team'),
            ('opp_team_full', 'Opposing Team Full'),
            ('team_pos_rank_stat_type', 'Team Position Rank')
        ]
        
        for column, name in null_checks:
            null_count = db_manager.session.query(Prop).filter(getattr(Prop, column).is_(None)).count()
            if null_count > 0:
                print(f"⚠️  {name}: {null_count} NULL values found")
            else:
                print(f"✅ {name}: No NULL values")
        
        # Check for "Unknown" values
        unknown_checks = [
            ('player_team', 'Player Team'),
            ('opp_team', 'Opposing Team'),
            ('opp_team_full', 'Opposing Team Full')
        ]
        
        for column, name in unknown_checks:
            unknown_count = db_manager.session.query(Prop).filter(getattr(Prop, column) == 'Unknown').count()
            if unknown_count > 0:
                print(f"⚠️  {name}: {unknown_count} 'Unknown' values found")
            else:
                print(f"✅ {name}: No 'Unknown' values")
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
    
    print(f"\n🎯 Database population complete! Ready to test the application.")

if __name__ == "__main__":
    populate_historical_database()
