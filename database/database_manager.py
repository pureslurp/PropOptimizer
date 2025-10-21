from sqlalchemy.orm import Session
from contextlib import contextmanager
from .database_config import SessionLocal, engine
from .database_models import Base, Game, Prop, BoxScore, CacheMetadata
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def init_database(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("✅ Database tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return False
    
    def migrate_database(self):
        """Run database migrations to ensure schema is up to date"""
        try:
            from sqlalchemy import text
            
            with self.get_session() as session:
                # Check if last_historical_check column exists in games table
                result = session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'games' 
                    AND column_name = 'last_historical_check'
                """))
                
                if not result.fetchone():
                    print("🔄 Adding missing last_historical_check column...")
                    session.execute(text("""
                        ALTER TABLE games 
                        ADD COLUMN last_historical_check TIMESTAMP
                    """))
                    session.commit()
                    print("✅ Added last_historical_check column")
                else:
                    print("✅ last_historical_check column already exists")
                    
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")
            # Continue anyway - this might be expected for some database types
    
    def is_data_fresh(self, data_type: str, max_age_hours: int = 2) -> bool:
        """Check if cached data is still fresh with automatic corruption detection"""
        try:
            with self.get_session() as session:
                cache_entry = session.query(CacheMetadata).filter(
                    CacheMetadata.data_type == data_type
                ).first()
                
                if not cache_entry:
                    return False
                
                # Check for corruption: expires_at should be after last_updated
                if cache_entry.expires_at <= cache_entry.last_updated:
                    print(f"⚠️ Detected corrupted cache metadata for {data_type}")
                    print(f"   last_updated: {cache_entry.last_updated}")
                    print(f"   expires_at: {cache_entry.expires_at}")
                    print(f"   Auto-fixing corruption...")
                    
                    # Auto-fix the corruption
                    cache_entry.expires_at = cache_entry.last_updated + timedelta(hours=max_age_hours)
                    session.commit()
                    print(f"✅ Auto-fixed corrupted cache metadata for {data_type}")
                
                return datetime.utcnow() < cache_entry.expires_at
        except Exception as e:
            print(f"Error checking cache freshness: {e}")
            return False
    
    def store_game(self, game_data: dict):
        """Store game data"""
        try:
            with self.get_session() as session:
                game = Game(
                    id=game_data['id'],
                    home_team=game_data['home_team'],
                    away_team=game_data['away_team'],
                    commence_time=game_data['commence_time'],
                    week=game_data['week'],
                    season=game_data['season']
                )
                session.merge(game)  # Use merge to handle duplicates
                session.commit()
                print(f"✅ Stored game: {game_data['away_team']} @ {game_data['home_team']}")
        except Exception as e:
            print(f"❌ Error storing game: {e}")
    
    def store_props(self, game_id: str, props_data: list):
        """Store props data - only replaces props for games that haven't started yet"""
        try:
            with self.get_session() as session:
                # Check if the game has started yet
                game = session.query(Game).filter(Game.id == game_id).first()
                current_time = datetime.utcnow()
                
                # Don't update props if:
                # 1. Game has already started, OR
                # 2. Game has historical props merged (we want to keep the canonical 2-hour historical data)
                if game and game.commence_time and game.commence_time <= current_time:
                    print(f"⚠️ Game {game_id} has already started, preserving existing props")
                    return  # Don't add or modify props
                elif game and game.historical_merged:
                    print(f"⚠️ Game {game_id} has historical props merged, preserving them (not overwriting with live data)")
                    return  # Don't add or modify props - historical data is canonical
                
                # Clear existing props for games that haven't started and don't have historical data yet
                deleted_count = session.query(Prop).filter(Prop.game_id == game_id).delete()
                if deleted_count > 0:
                    print(f"🔄 Cleared {deleted_count} existing props for game {game_id} (game hasn't started, no historical data yet)")
                
                # Add new props
                for prop_data in props_data:
                    prop = Prop(
                        game_id=game_id,
                        player=prop_data['player'],
                        stat_type=prop_data['stat_type'],
                        line=prop_data['line'],
                        odds=prop_data['odds'],
                        bookmaker=prop_data['bookmaker'],
                        is_alternate=prop_data.get('is_alternate', False),
                        # Enhanced columns
                        player_team=prop_data.get('player_team'),
                        opp_team=prop_data.get('opp_team'),
                        opp_team_full=prop_data.get('opp_team_full'),
                        team_pos_rank_stat_type=prop_data.get('team_pos_rank_stat_type'),
                        week=prop_data.get('week'),
                        commence_time=prop_data.get('commence_time'),
                        home_team=prop_data.get('home_team'),
                        away_team=prop_data.get('away_team'),
                        prop_source=prop_data.get('prop_source', 'live_capture')  # Default to live_capture
                    )
                    session.add(prop)
                session.commit()
                print(f"✅ Stored {len(props_data)} props for game {game_id}")
        except Exception as e:
            print(f"❌ Error storing props: {e}")
    
    def get_props(self, game_id: str = None, week: int = None, filters: dict = None):
        """Retrieve props data"""
        try:
            with self.get_session() as session:
                query = session.query(Prop)
                
                if game_id:
                    query = query.filter(Prop.game_id == game_id)
                
                if week:
                    query = query.join(Game).filter(Game.week == week)
                
                if filters:
                    for key, value in filters.items():
                        if hasattr(Prop, key):
                            query = query.filter(getattr(Prop, key) == value)
                
                props = query.all()
                print(f"✅ Retrieved {len(props)} props from database")
                return props
        except Exception as e:
            print(f"❌ Error retrieving props: {e}")
            return []
    
    def update_cache_metadata(self, data_type: str, record_count: int, max_age_hours: int = 2):
        """Update cache metadata with validation to prevent corruption"""
        try:
            with self.get_session() as session:
                now = datetime.utcnow()
                expires_at = now + timedelta(hours=max_age_hours)
                
                # Validate that expires_at is actually in the future
                if expires_at <= now:
                    raise ValueError(f"Invalid expiration time: expires_at ({expires_at}) must be after now ({now})")
                
                cache_entry = CacheMetadata(
                    data_type=data_type,
                    last_updated=now,
                    expires_at=expires_at,
                    record_count=record_count
                )
                session.merge(cache_entry)
                session.commit()
                
                # Verify the data was stored correctly
                stored_entry = session.query(CacheMetadata).filter(
                    CacheMetadata.data_type == data_type
                ).first()
                
                if stored_entry and stored_entry.expires_at <= stored_entry.last_updated:
                    raise ValueError(f"Cache metadata corruption detected: expires_at ({stored_entry.expires_at}) <= last_updated ({stored_entry.last_updated})")
                
                print(f"✅ Updated cache metadata for {data_type} (expires in {max_age_hours} hours)")
        except Exception as e:
            print(f"❌ Error updating cache metadata: {e}")
            raise
    
    def fix_corrupted_cache_metadata(self):
        """Detect and fix corrupted cache metadata entries"""
        try:
            with self.get_session() as session:
                corrupted_entries = []
                
                # Find all cache entries where expires_at <= last_updated
                all_entries = session.query(CacheMetadata).all()
                for entry in all_entries:
                    if entry.expires_at <= entry.last_updated:
                        corrupted_entries.append(entry)
                        print(f"🔧 Found corrupted cache entry: {entry.data_type}")
                        print(f"   last_updated: {entry.last_updated}")
                        print(f"   expires_at: {entry.expires_at}")
                
                if corrupted_entries:
                    print(f"🔧 Fixing {len(corrupted_entries)} corrupted cache entries...")
                    
                    for entry in corrupted_entries:
                        # Set expires_at to 2 hours after last_updated
                        fixed_expires_at = entry.last_updated + timedelta(hours=2)
                        entry.expires_at = fixed_expires_at
                        print(f"   Fixed {entry.data_type}: expires_at = {fixed_expires_at}")
                    
                    session.commit()
                    print(f"✅ Fixed {len(corrupted_entries)} corrupted cache entries")
                    return len(corrupted_entries)
                else:
                    print("✅ No corrupted cache entries found")
                    return 0
                    
        except Exception as e:
            print(f"❌ Error fixing corrupted cache metadata: {e}")
            return -1
    
    def get_fresh_props(self, week: int = None):
        """Get fresh props data, checking cache first"""
        if self.is_data_fresh('props'):
            print("📊 Using cached props data")
            return self.get_props(week=week)
        else:
            print("🔄 Props data is stale, need to refresh")
            return None
    
    def get_available_weeks_from_db(self):
        """Get list of weeks that have props data in the database"""
        try:
            with self.get_session() as session:
                # Get unique weeks from props table via games table
                weeks = session.query(Game.week).distinct().order_by(Game.week).all()
                week_list = [week[0] for week in weeks]
                print(f"✅ Found {len(week_list)} weeks with props data: {week_list}")
                return week_list
        except Exception as e:
            print(f"❌ Error getting available weeks from database: {e}")
            return []
    
    def get_latest_week_with_props(self):
        """Get the latest week that has props data in the database"""
        available_weeks = self.get_available_weeks_from_db()
        if available_weeks:
            latest_week = max(available_weeks)
            print(f"✅ Latest week with props data: {latest_week}")
            return latest_week
        else:
            print("⚠️ No weeks with props data found in database")
            return None
    
    def get_props_as_dataframe(self, week: int = None, upcoming_only: bool = True):
        """Get props data as a pandas DataFrame"""
        try:
            with self.get_session() as session:
                query = session.query(Prop)
                
                if week:
                    query = query.join(Game).filter(Game.week == week)
                
                # Filter out games that have already started (only show upcoming games)
                if upcoming_only:
                    current_time = datetime.utcnow()
                    query = query.filter(Prop.commence_time > current_time)
                
                props = query.all()
                
                if not props:
                    return pd.DataFrame()
                
                # Convert to DataFrame
                data = []
                for prop in props:
                    row = {
                        'Player': prop.player,
                        'Team': prop.player_team,
                        'Opp. Team': prop.opp_team,
                        'Opp. Team Full': prop.opp_team_full,
                        'Stat Type': prop.stat_type,
                        'Line': prop.line,
                        'Odds': prop.odds,
                        'Bookmaker': prop.bookmaker,
                        'Home Team': prop.home_team,
                        'Away Team': prop.away_team,
                        'Commence Time': prop.commence_time,
                        'is_alternate': prop.is_alternate,
                        'team_pos_rank_stat_type': prop.team_pos_rank_stat_type,
                        'week': prop.week
                    }
                    data.append(row)
                
                df = pd.DataFrame(data)
                
                # Ensure all required columns exist (same as CSV loading)
                if not df.empty:
                    # Handle is_alternate column
                    if 'is_alternate' in df.columns:
                        df['is_alternate'] = df['is_alternate'].fillna(False)
                        df['is_alternate'] = df['is_alternate'].apply(lambda x: x == 'True' or x == True)
                    else:
                        df['is_alternate'] = False
                    
                    # Ensure all required columns exist
                    required_cols = ['Player', 'Team', 'Opp. Team', 'Stat Type', 'Line', 'Odds', 
                                   'Bookmaker', 'Home Team', 'Away Team', 'Commence Time']
                    for col in required_cols:
                        if col not in df.columns:
                            df[col] = ''
                        else:
                            # Fill NULL values with defaults
                            if df[col].isnull().any():
                                if col == 'Stat Type':
                                    df[col] = df[col].fillna('Unknown')
                                elif col in ['Team', 'Opp. Team', 'Opp. Team Full', 'Home Team', 'Away Team']:
                                    df[col] = df[col].fillna('Unknown')
                                else:
                                    df[col] = df[col].fillna('')
                    
                    # Also handle Opp. Team Full column specifically
                    if 'Opp. Team Full' in df.columns and df['Opp. Team Full'].isnull().any():
                        df['Opp. Team Full'] = df['Opp. Team Full'].fillna('Unknown')
                
                print(f"✅ Retrieved {len(df)} props as DataFrame")
                return df
        except Exception as e:
            print(f"❌ Error getting props as DataFrame: {e}")
            return pd.DataFrame()
    
    def test_connection(self):
        """Test database connection"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                result = session.execute(text("SELECT 1")).fetchone()
                print("✅ Database connection successful")
                return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def merge_historical_props(self, session, game_id: str, historical_props: list) -> dict:
        """
        Merge historical API props with existing props for a game.
        Historical data overwrites matches (by player, stat_type, bookmaker),
        but preserves props that aren't in the historical API (scratched players).
        
        Args:
            session: SQLAlchemy session to use
            game_id: The game ID
            historical_props: List of prop dictionaries from historical API
            
        Returns:
            Dictionary with merge statistics
        """
        from sqlalchemy.orm.attributes import flag_modified
        
        try:
            # Get existing props for this game
            existing_props = session.query(Prop).filter(
                Prop.game_id == game_id
            ).all()
            
            if not existing_props:
                print(f"  ⚠️ No existing props to merge for game {game_id}")
                
                # Get week from first prop
                prop_week = historical_props[0].get('week', 7) if historical_props else 7
                
                # Calculate defensive rankings efficiently (like update_week_rankings.py)
                rankings_cache = {}
                if prop_week > 1:  # Skip Week 1 (no historical data)
                    print(f"  📊 Calculating defensive rankings for Week {prop_week}...")
                    try:
                        from position_defensive_ranks import PositionDefensiveRankings
                        import tempfile
                        import os
                        import shutil
                        
                        # Create temporary directory for ranking calculation
                        temp_dir = tempfile.mkdtemp()
                        
                        try:
                            # Export weeks 1 through prop_week-1 to temp directory
                            from .database_enhanced_data_processor import DatabaseBoxScoreLoader
                            box_score_loader = DatabaseBoxScoreLoader()
                            weeks_to_export = list(range(1, prop_week))
                            
                            for week in weeks_to_export:
                                week_data = box_score_loader.load_week_data_from_db(week)
                                if not week_data.empty:
                                    week_dir = os.path.join(temp_dir, f'WEEK{week}')
                                    os.makedirs(week_dir, exist_ok=True)
                                    week_data.to_csv(os.path.join(week_dir, 'box_scores.csv'), index=False)
                            
                            # Initialize ranking calculator once
                            rankings_calc = PositionDefensiveRankings(data_dir=temp_dir)
                            rankings_calc.calculate_position_defensive_stats(max_week=prop_week)
                            
                            # Get unique combinations from historical props
                            unique_combinations = set()
                            for hist_prop in historical_props:
                                player = hist_prop.get('player')
                                opp_team = hist_prop.get('opp_team_full', hist_prop.get('opp_team'))
                                stat_type = hist_prop.get('stat_type')
                                if player and opp_team and stat_type:
                                    unique_combinations.add((player, opp_team, stat_type))
                            
                            print(f"  📊 Calculating ranks for {len(unique_combinations)} unique combinations...")
                            
                            # Calculate rankings for each unique combination
                            for player, opp_team, stat_type in unique_combinations:
                                calculated_rank = rankings_calc.get_position_defensive_rank(opp_team, player, stat_type)
                                rankings_cache[(player, opp_team, stat_type)] = calculated_rank
                                print(f"  📊 {player} vs {opp_team} ({stat_type}) → rank {calculated_rank}")
                        
                        finally:
                            # Clean up temporary directory
                            shutil.rmtree(temp_dir)
                    
                    except Exception as e:
                        print(f"  ⚠️ Error calculating defensive rankings: {e}")
                        # Continue without rankings if calculation fails
                
                # Add all historical props with cached rankings
                for hist_prop in historical_props:
                    hist_prop['prop_source'] = 'historical_api'
                    
                    # Use cached ranking if available
                    player = hist_prop.get('player')
                    opp_team = hist_prop.get('opp_team_full', hist_prop.get('opp_team'))
                    stat_type = hist_prop.get('stat_type')
                    
                    if player and opp_team and stat_type and (player, opp_team, stat_type) in rankings_cache:
                        hist_prop['team_pos_rank_stat_type'] = rankings_cache[(player, opp_team, stat_type)]
                    else:
                        hist_prop['team_pos_rank_stat_type'] = None
                    
                    new_prop = Prop(**hist_prop)
                    session.add(new_prop)
                # Don't commit here - let the outer function handle it
                # session.commit()
                return {
                    'deleted': 0,
                    'added': len(historical_props),
                    'replaced_groups': 0,
                    'preserved_groups': 0
                }
            
            # Group existing props by (player, stat_type, bookmaker) - NOT line!
            # Each key maps to a LIST of all props with different lines
            existing_groups = {}
            for p in existing_props:
                key = (p.player, p.stat_type, p.bookmaker)
                if key not in existing_groups:
                    existing_groups[key] = []
                existing_groups[key].append(p)
            
            # Group historical props by (player, stat_type, bookmaker)
            historical_groups = {}
            for hist_prop in historical_props:
                key = (hist_prop['player'], hist_prop['stat_type'], hist_prop['bookmaker'])
                if key not in historical_groups:
                    historical_groups[key] = []
                historical_groups[key].append(hist_prop)
            
            # Track statistics
            deleted_count = 0
            added_count = 0
            preserved_groups = 0
            replaced_groups = 0
            
            # For each player/stat/bookmaker combo in historical API:
            # DELETE all live props, ADD all historical props
            for key, hist_props_list in historical_groups.items():
                player, stat_type, bookmaker = key
                
                # PRESERVE defensive rank from existing props (if available)
                existing_defensive_rank = None
                if key in existing_groups:
                    # Get defensive rank from first existing prop (they should all have same rank)
                    if existing_groups[key] and existing_groups[key][0].team_pos_rank_stat_type:
                        existing_defensive_rank = existing_groups[key][0].team_pos_rank_stat_type
                    
                    # DELETE all existing props for this combo
                    for existing_prop in existing_groups[key]:
                        session.delete(existing_prop)
                        deleted_count += 1
                    replaced_groups += 1
                
                # ADD all historical props for this combo
                for hist_prop in hist_props_list:
                    hist_prop['prop_source'] = 'historical_api'
                    
                    # PRIORITY 1: Use existing defensive rank from live_capture props (if available)
                    if existing_defensive_rank is not None:
                        hist_prop['team_pos_rank_stat_type'] = existing_defensive_rank
                        print(f"✅ Preserved existing rank {existing_defensive_rank} for {player} {stat_type}")
                    else:
                        # PRIORITY 2: Calculate defensive rank if no existing rank
                        try:
                            from position_defensive_ranks import PositionDefensiveRankings
                            import tempfile
                            import os
                            
                            # Get week from the prop
                            prop_week = hist_prop.get('week', 7)  # Default to 7 if not specified
                            
                            # Create temporary directory for ranking calculation
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # Export box score data for ranking calculation
                                from .database_enhanced_data_processor import DatabaseBoxScoreLoader
                                box_score_loader = DatabaseBoxScoreLoader()
                                weeks_to_export = list(range(1, prop_week))  # Export weeks 1 through prop_week-1
                                
                                for week in weeks_to_export:
                                    week_data = box_score_loader.load_week_data_from_db(week)
                                    if not week_data.empty:
                                        week_dir = os.path.join(temp_dir, f'WEEK{week}')
                                        os.makedirs(week_dir, exist_ok=True)
                                        week_data.to_csv(os.path.join(week_dir, 'box_scores.csv'), index=False)
                                
                                # Initialize ranking calculator
                                rankings_calc = PositionDefensiveRankings(data_dir=temp_dir)
                                
                                # Calculate rank for this opponent/stat combination
                                opp_team = hist_prop.get('opp_team_full', hist_prop.get('opp_team'))
                                player = hist_prop.get('player')
                                calculated_rank = rankings_calc.get_position_defensive_rank(
                                    opp_team, player, stat_type
                                )
                                
                                hist_prop['team_pos_rank_stat_type'] = calculated_rank
                                print(f"📊 Calculated rank {calculated_rank} for {player} vs {opp_team} {stat_type}")
                        
                        except Exception as e:
                            print(f"⚠️ Error calculating defensive rank for {player} {stat_type}: {e}")
                            hist_prop['team_pos_rank_stat_type'] = None
                    
                    new_prop = Prop(**hist_prop)
                    session.add(new_prop)
                    added_count += 1
            
            # PRESERVE props for player/stat/bookmaker combos NOT in historical API (scratched players)
            for key, props_list in existing_groups.items():
                if key not in historical_groups:
                    # Mark all as live_capture and preserve
                    for prop in props_list:
                        if not prop.prop_source or prop.prop_source == '':
                            prop.prop_source = 'live_capture'
                            flag_modified(prop, 'prop_source')
                            session.add(prop)
                    preserved_groups += 1
            
            # Print merge summary
            print(f"  📊 Merge complete: {deleted_count} deleted, {added_count} added ({replaced_groups} combos replaced, {preserved_groups} preserved)")
            
            # Don't commit here - let the outer function handle it for atomicity
            # session.commit()
            
            return {
                'deleted': deleted_count,
                'added': added_count,
                'replaced_groups': replaced_groups,
                'preserved_groups': preserved_groups
            }
            
        except Exception as e:
            print(f"❌ Error merging historical props for game {game_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'deleted': 0,
                'added': 0,
                'replaced_groups': 0,
                'preserved_groups': 0,
                'error': str(e)
            }
    
    def check_and_merge_historical_props(self, week: int, odds_api=None, progress_callback=None) -> dict:
        """
        Check for games that have started and need historical prop merge.
        Fetches historical props for all games in parallel for efficiency.
        
        Args:
            week: Week number to check
            odds_api: OddsAPIWithDB instance for fetching historical props
            progress_callback: Optional function to call with progress updates (progress_value, message)
            
        Returns:
            Dictionary with merge statistics
        """
        from sqlalchemy import or_
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            with self.get_session() as session:
                current_time = datetime.utcnow()
                
                # Find games that:
                # 1. Are in the specified week
                # 2. Have already started (commence_time <= current_time) - only completed games
                #    This ensures we only fetch historical props for games that are finished
                # 3. Haven't been merged yet (historical_merged = False)
                # 4. Haven't been checked recently (last_historical_check is None or > 1 hour ago)
                
                one_hour_ago = current_time - timedelta(hours=1)
                games_needing_merge = session.query(Game).filter(
                    Game.week == week,
                    Game.commence_time <= current_time,  # Only completed games
                    Game.historical_merged == False,
                    or_(
                        Game.last_historical_check.is_(None),
                        Game.last_historical_check <= one_hour_ago
                    )
                ).all()
                
                if not games_needing_merge:
                    # Update last check time for all games in this week to avoid repeated checks
                    session.query(Game).filter(
                        Game.week == week,
                        Game.commence_time <= current_time
                    ).update({'last_historical_check': current_time})
                    session.commit()
                    return {'games_merged': 0, 'message': 'No games need merging'}
                
                if progress_callback:
                    progress_callback(5, f"Fetching historical odds for {len(games_needing_merge)} game(s) in parallel...")
                
                print(f"\n🔄 Found {len(games_needing_merge)} game(s) needing historical merge for Week {week}")
                
                if not odds_api:
                    print(f"  ⚠️ No odds_api provided, cannot fetch historical props")
                    return {'games_merged': 0, 'error': 'No odds_api provided'}
                
                # PARALLEL FETCH: Fetch all historical props in parallel (huge speed improvement!)
                print(f"📡 Fetching historical props for all {len(games_needing_merge)} game(s) in parallel...")
                game_props_map = {}  # Map game_id -> historical_props
                
                def fetch_for_game(game):
                    """Helper function to fetch props for a single game"""
                    try:
                        # Convert game object to dictionary to avoid database connection issues
                        game_data = {
                            'id': game.id,
                            'commence_time': game.commence_time,
                            'home_team': game.home_team,
                            'away_team': game.away_team,
                            'week': game.week
                        }
                        props = odds_api.fetch_historical_props_for_game(game_data)
                        return (game.id, props, None)
                    except Exception as e:
                        return (game.id, None, str(e))
                
                # Use ThreadPoolExecutor to fetch all games in parallel
                with ThreadPoolExecutor(max_workers=min(10, len(games_needing_merge))) as executor:
                    future_to_game = {executor.submit(fetch_for_game, game): game for game in games_needing_merge}
                    
                    completed = 0
                    for future in as_completed(future_to_game):
                        game = future_to_game[future]
                        completed += 1
                        
                        if progress_callback:
                            progress = 5 + int((completed / len(games_needing_merge)) * 5)
                            progress_callback(progress, f"Fetched {completed}/{len(games_needing_merge)} games...")
                        
                        game_id, props, error = future.result()
                        if error:
                            print(f"  ❌ Error fetching {game.away_team} @ {game.home_team}: {error}")
                            game_props_map[game_id] = {'error': error}
                        else:
                            game_props_map[game_id] = props
                            if props:
                                print(f"  ✅ Fetched {len(props)} props for {game.away_team} @ {game.home_team}")
                
                print(f"✅ Parallel fetch complete! Processing {len(game_props_map)} game(s)...")
                
                # Now process each game sequentially (database operations must be sequential)
                total_stats = {
                    'games_merged': 0,
                    'total_updated': 0,
                    'total_added': 0,
                    'total_preserved': 0,
                    'errors': []
                }
                
                for idx, game in enumerate(games_needing_merge):
                    if progress_callback:
                        progress = 5 + int((idx / len(games_needing_merge)) * 5)
                        progress_callback(progress, f"Merging {game.away_team} @ {game.home_team}...")
                    
                    print(f"\n📊 Merging: {game.away_team} @ {game.home_team}")
                    
                    # Get pre-fetched props from parallel fetch
                    fetched_data = game_props_map.get(game.id)
                    
                    if not fetched_data:
                        print(f"  ⚠️ No data fetched for game {game.id}")
                        # Update last_historical_check even when no data to prevent repeated attempts
                        game.last_historical_check = current_time
                        continue
                    
                    # Check if there was an error during fetch
                    if isinstance(fetched_data, dict) and 'error' in fetched_data:
                        print(f"  ❌ Error during fetch: {fetched_data['error']}")
                        total_stats['errors'].append(f"Game {game.id}: {fetched_data['error']}")
                        # Update last_historical_check even on error to prevent repeated attempts
                        game.last_historical_check = current_time
                        continue
                    
                    try:
                        historical_props = fetched_data
                        
                        if not historical_props:
                            print(f"  ⚠️ No historical props returned from API for game {game.id}")
                            
                            # Check how long ago the game started
                            time_since_game = (current_time - game.commence_time).total_seconds() / 3600
                            
                            if time_since_game < 48:  # Less than 48 hours ago
                                print(f"  ⏰ Game started {time_since_game:.1f} hours ago - will retry on next app load")
                                print(f"     (Historical API might not be available yet)")
                                # Don't mark as merged - allow retry
                            else:
                                print(f"  ⏰ Game started {time_since_game:.1f} hours ago - marking as merged to stop retrying")
                                # Give up after 48 hours
                                game.historical_merged = True
                            continue
                        
                        # Merge the props (using same session - no nested sessions!)
                        stats = self.merge_historical_props(session, game.id, historical_props)
                        
                        if 'error' not in stats:
                            total_stats['games_merged'] += 1
                            total_stats['total_updated'] += stats.get('deleted', 0)  # Track deletions as "updates"
                            total_stats['total_added'] += stats.get('added', 0)
                            total_stats['total_preserved'] += stats.get('preserved_groups', 0)
                            
                            # Flush the session to ensure all deletes/adds are tracked before querying
                            session.flush()
                            
                            # Check if we still have live_capture props (meaning historical API doesn't have them yet)
                            remaining_live_props = session.query(Prop).filter(
                                Prop.game_id == game.id,
                                Prop.prop_source == 'live_capture'
                            ).count()
                            
                            # Update the last_historical_check timestamp
                            game.last_historical_check = current_time
                            
                            if remaining_live_props > 0:
                                # Check how long ago the game started
                                time_since_game = (current_time - game.commence_time).total_seconds() / 3600
                                
                                if time_since_game < 48:  # Less than 48 hours ago
                                    print(f"  ⏰ {remaining_live_props} live_capture props remain - will retry in 8h (game started {time_since_game:.1f}h ago)")
                                    # Don't mark as merged - keep trying, but update timestamp
                                else:
                                    print(f"  ⏰ {remaining_live_props} live_capture props remain, marking as merged (48h timeout)")
                                    game.historical_merged = True
                            else:
                                print(f"  ✅ All props now from historical API - marking as complete")
                                game.historical_merged = True
                        else:
                            total_stats['errors'].append(f"Game {game.id}: {stats['error']}")
                            
                    except Exception as e:
                        error_msg = f"Game {game.id}: {str(e)}"
                        print(f"  ❌ Error processing game: {e}")
                        total_stats['errors'].append(error_msg)
                        import traceback
                        traceback.print_exc()
                
                # Commit all changes
                session.commit()
                
                if total_stats['games_merged'] > 0:
                    print(f"✅ Historical merge complete: {total_stats['games_merged']} game(s), {total_stats['total_updated']} replaced, {total_stats['total_added']} added")
                    if total_stats['errors']:
                        print(f"   ⚠️ {len(total_stats['errors'])} error(s) occurred")
                
                return total_stats
                
        except Exception as e:
            print(f"❌ Error in check_and_merge_historical_props: {e}")
            import traceback
            traceback.print_exc()
            return {
                'games_merged': 0,
                'error': str(e)
            }