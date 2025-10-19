"""
Enhanced Data Processor that integrates with the existing FootballDB scraper
Provides real player and team data for the Player Prop Optimizer
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
import json
from datetime import datetime, timedelta
import pickle
# from dfs_box_scores import FootballDBScraper  # Not needed for production
from defensive_scraper import DefensiveScraper
from position_defensive_ranks import PositionDefensiveRankings
import warnings
warnings.filterwarnings('ignore')

class EnhancedFootballDataProcessor:
    """Enhanced data processor that uses real FootballDB data with database support"""
    
    def __init__(self, data_dir: str = "data", max_week: int = None, use_database: bool = True, skip_calculations: bool = False):
        """
        Initialize the data processor
        
        Args:
            data_dir: Directory for cache files
            max_week: Maximum week to include in calculations (None = all weeks)
            use_database: If True, use database for box score data. If False, use CSV files.
            skip_calculations: If True, skip expensive calculations like position defensive rankings
        """
        self.data_dir = data_dir
        self.team_defensive_stats = {}
        self.historical_defensive_stats = {}  # Store historical defensive rankings
        self.player_season_stats = {}
        self.player_name_index = {}  # Index: cleaned_name -> actual_player_key
        self.current_week = self._get_current_week()
        self.max_week = max_week  # Used for filtering historical data (None = use all weeks)
        self.use_database = use_database
        self.skip_calculations = skip_calculations
        
        # Initialize database loader if using database
        if use_database:
            from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
            self.db_loader = DatabaseBoxScoreLoader()
            print("🗄️ Using database for box score data loading")
        else:
            self.db_loader = None
            print("📁 Using CSV files for box score data loading (fallback mode)")
        
        self.schedule_data = self._load_schedule()
        self.opponent_mapping = self._build_opponent_mapping_from_game_data()  # Build from game data
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load cached data if available
        self._load_cached_data()
        
        # If max_week is set, load or calculate historical defensive rankings
        if self.max_week is not None:
            self._load_historical_defensive_rankings()
        
        # Initialize position-specific defensive rankings (skip if requested)
        # Note: In production, defensive ranks come from database, not calculated here
        if skip_calculations:
            self.position_defensive_rankings = None
        else:
            # This is only used for initial database population or testing
            # In normal app usage, ranks are retrieved from database
            self.position_defensive_rankings = None
        
    def _get_current_week(self) -> int:
        """Get current NFL week"""
        current_date = datetime.now()
        # NFL season typically starts first week of September
        season_start = datetime(current_date.year, 9, 1)
        weeks_elapsed = (current_date - season_start).days // 7
        return min(max(1, weeks_elapsed), 18)  # NFL regular season is 18 weeks max
    
    def _load_schedule(self) -> pd.DataFrame:
        """Load the NFL schedule from CSV (optional - only used as fallback)"""
        try:
            schedule_path = "2025/nfl_schedule.csv"
            if os.path.exists(schedule_path):
                df = pd.read_csv(schedule_path)
                print(f"✅ Loaded NFL schedule with {len(df)} games")
                return df
            else:
                # Schedule is optional - home/away detection uses API data
                return pd.DataFrame()
        except Exception as e:
            # Schedule is optional, silently return empty DataFrame
            return pd.DataFrame()
    
    def _build_opponent_mapping_from_game_data(self):
        """Build a mapping of week -> team -> opponent from game_data JSON files"""
        opponent_map = {}  # {week: {team: opponent}}
        
        # Scan for week directories
        year_dir = "2025"
        if not os.path.exists(year_dir):
            return opponent_map
        
        for week_folder in os.listdir(year_dir):
            if not week_folder.startswith("WEEK"):
                continue
            
            # Extract week number
            try:
                week_num = int(week_folder.replace("WEEK", ""))
            except:
                continue
            
            game_data_dir = os.path.join(year_dir, week_folder, "game_data")
            if not os.path.exists(game_data_dir):
                continue
            
            week_opponents = {}
            
            # Load all JSON files in the game_data directory
            for json_file in os.listdir(game_data_dir):
                if not json_file.endswith("_historical_odds.json"):
                    continue
                
                json_path = os.path.join(game_data_dir, json_file)
                try:
                    with open(json_path, 'r') as f:
                        game_data = json.load(f)
                    
                    # Extract home and away teams
                    if 'data' in game_data:
                        data = game_data['data']
                        home_team = data.get('home_team', '')
                        away_team = data.get('away_team', '')
                        commence_time = data.get('commence_time', '')
                        
                        if home_team and away_team:
                            week_opponents[home_team] = {
                                'opponent': away_team,
                                'is_home': True,
                                'game_time': commence_time
                            }
                            week_opponents[away_team] = {
                                'opponent': home_team,
                                'is_home': False,
                                'game_time': commence_time
                            }
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
                    continue
            
            if week_opponents:
                opponent_map[week_num] = week_opponents
        
        return opponent_map
    
    def is_home_game(self, team: str, week: int) -> Optional[bool]:
        """
        Determine if a team was home for a specific week
        
        Args:
            team: Full team name (e.g., "Kansas City Chiefs")
            week: NFL week number
            
        Returns:
            True for home, False for away, None if unknown/bye week
        """
        # Use opponent mapping from game data
        if week in self.opponent_mapping and team in self.opponent_mapping[week]:
            return self.opponent_mapping[week][team]['is_home']
        
        return None  # Team not found in schedule for this week (bye week or not found)
    
    def _get_cache_file(self, data_type: str) -> str:
        """Get cache file path for a data type"""
        return os.path.join(self.data_dir, f"{data_type}_cache.pkl")
    
    def _is_cache_valid(self, cache_file: str, max_age_hours: int = 24) -> bool:
        """
        Check if cache file is still valid
        
        Validates cache by checking:
        1. File exists
        2. Age is within max_age_hours
        3. Source CSV files haven't been updated since cache was created
        
        This prevents stale cache issues when new week data is added on Tuesdays.
        """
        if not os.path.exists(cache_file):
            return False
        
        # Check if cache is older than max_age_hours
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        
        if age_hours >= max_age_hours:
            return False
        
        # For player_season and team_defensive cache, check if any CSV files are newer
        # This is critical for detecting when new weeks are added (typically Tuesdays)
        if 'player_season' in cache_file or 'team_defensive' in cache_file:
            base_path = "2025"
            if os.path.exists(base_path):
                for week in range(1, 19):  # Check weeks 1-18
                    csv_file = f"{base_path}/WEEK{week}/box_score_debug.csv"
                    if os.path.exists(csv_file):
                        csv_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
                        if csv_time > cache_time:
                            cache_type = "player_season" if "player_season" in cache_file else "team_defensive"
                            print(f"⚠️ {cache_type} cache invalid: WEEK{week} CSV is newer than cache")
                            return False
        
        return True
    
    def _rebuild_player_name_index(self):
        """Rebuild the player name index for fast lookups"""
        from utils import clean_player_name
        self.player_name_index = {}
        for player_key in self.player_season_stats.keys():
            cleaned = clean_player_name(player_key)
            self.player_name_index[cleaned] = player_key
    
    def _load_cached_data(self):
        """Load cached data if available and valid"""
        # Load team defensive stats
        team_cache_file = self._get_cache_file("team_defensive")
        if self._is_cache_valid(team_cache_file, max_age_hours=168):  # 1 week
            try:
                with open(team_cache_file, 'rb') as f:
                    self.team_defensive_stats = pickle.load(f)
                print(f"✅ Loaded cached team defensive stats")
            except Exception as e:
                print(f"⚠️ Could not load team defensive cache: {e}")
        
        # Load player season stats
        player_cache_file = self._get_cache_file("player_season")
        if self._is_cache_valid(player_cache_file, max_age_hours=168):  # 1 week
            try:
                with open(player_cache_file, 'rb') as f:
                    self.player_season_stats = pickle.load(f)
                
                # Validate cache has week data (needed for historical filtering)
                cache_has_weeks = False
                if self.player_season_stats:
                    # Check first player's data for week information
                    first_player = next(iter(self.player_season_stats.values()))
                    cache_has_weeks = any(key.endswith('_weeks') for key in first_player.keys())
                
                if not cache_has_weeks:
                    print(f"⚠️ Cache is outdated (missing week tracking). Clearing cache...")
                    self.player_season_stats = {}
                    os.remove(player_cache_file)
                else:
                    self._rebuild_player_name_index()
                    print(f"✅ Loaded cached player season stats")
            except Exception as e:
                print(f"⚠️ Could not load player season cache: {e}")
    
    def _save_cache(self, data: dict, data_type: str):
        """Save data to cache"""
        cache_file = self._get_cache_file(data_type)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            print(f"💾 Cached {data_type} data")
        except Exception as e:
            print(f"⚠️ Could not save cache for {data_type}: {e}")
    
    def clear_all_caches(self):
        """
        Clear all cache files to force fresh data load
        
        Use this when:
        - You suspect stale cache issues
        - New week data has been added
        - You want to ensure fresh calculations
        """
        import glob
        
        print("🗑️  Clearing all caches...")
        
        # Clear main caches
        cache_types = ['player_season', 'team_defensive', 'nfl_defensive_td']
        for cache_type in cache_types:
            cache_file = self._get_cache_file(cache_type)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"   ✓ Removed {cache_type} cache")
        
        # Clear historical defensive rankings caches
        ranking_caches = glob.glob(os.path.join(self.data_dir, 'defensive_rankings_week*.pkl'))
        for cache_file in ranking_caches:
            os.remove(cache_file)
            week = cache_file.split('week')[1].replace('.pkl', '')
            print(f"   ✓ Removed defensive_rankings_week{week} cache")
        
        # Reset in-memory data
        self.player_season_stats = {}
        self.team_defensive_stats = {}
        self.historical_defensive_stats = {}
        self.player_name_index = {}
        
        print("✅ All caches cleared. Data will be rebuilt on next access.")
    
    def get_cache_status(self):
        """
        Get status of all cache files
        
        Returns dict with cache info including age and validity
        """
        import glob
        
        status = {}
        
        # Check main caches
        cache_types = ['player_season', 'team_defensive', 'nfl_defensive_td']
        for cache_type in cache_types:
            cache_file = self._get_cache_file(cache_type)
            if os.path.exists(cache_file):
                cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                is_valid = self._is_cache_valid(cache_file, max_age_hours=168)
                
                status[cache_type] = {
                    'exists': True,
                    'age_hours': round(age_hours, 1),
                    'age_days': round(age_hours / 24, 1),
                    'last_modified': cache_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_valid': is_valid
                }
            else:
                status[cache_type] = {'exists': False}
        
        # Check historical defensive ranking caches
        ranking_caches = glob.glob(os.path.join(self.data_dir, 'defensive_rankings_week*.pkl'))
        if ranking_caches:
            status['defensive_rankings'] = {}
            for cache_file in ranking_caches:
                week = cache_file.split('week')[1].replace('.pkl', '')
                cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                status['defensive_rankings'][f'week_{week}'] = {
                    'age_hours': round(age_hours, 1),
                    'last_modified': cache_time.strftime('%Y-%m-%d %H:%M:%S')
                }
        
        return status
    
    def _load_historical_defensive_rankings(self):
        """Load or calculate defensive rankings through max_week"""
        if self.max_week is None:
            return
        
        # Check cache first
        cache_file = os.path.join(self.data_dir, f'defensive_rankings_week{self.max_week}.pkl')
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    self.historical_defensive_stats = pickle.load(f)
                print(f"✅ Loaded historical defensive rankings for Week {self.max_week} from cache")
                return
            except Exception as e:
                print(f"⚠️ Could not load historical defensive cache: {e}")
        
        # Calculate from box scores
        print(f"📊 Calculating defensive rankings through Week {self.max_week-1}...")
        self.historical_defensive_stats = self._calculate_defensive_rankings_through_week(self.max_week)
        
        # Save to cache
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.historical_defensive_stats, f)
            print(f"💾 Cached historical defensive rankings for Week {self.max_week}")
        except Exception as e:
            print(f"⚠️ Could not save historical defensive cache: {e}")
    
    def _calculate_defensive_rankings_through_week(self, target_week: int) -> Dict:
        """
        Calculate defensive rankings based on stats allowed through week N-1
        
        Args:
            target_week: Calculate rankings through week N-1 (for predicting week N)
        
        Returns:
            Dictionary of {team: {stat_type: rank}}
        """
        # Initialize defensive stats tracking
        defensive_stats = {}
        
        # Process weeks 1 through target_week-1
        for week in range(1, target_week):
            box_score_path = f"2025/WEEK{week}/box_score_debug.csv"
            
            if not os.path.exists(box_score_path):
                print(f"⚠️ Box score not found for Week {week}: {box_score_path}")
                continue
            
            try:
                df = pd.read_csv(box_score_path)
                
                # Get opponent mapping for this week from schedule
                opponent_map = self._get_opponent_map_for_week(week)
                
                # For each player's stats, attribute them to the opposing defense
                for _, row in df.iterrows():
                    player_team = row.get('team', '')
                    
                    if not player_team or pd.isna(player_team):
                        continue
                    
                    # Get opponent from mapping
                    opponent = opponent_map.get(player_team)
                    
                    if not opponent or opponent == 'BYE':
                        continue
                    
                    # Initialize opponent in defensive stats if not exists
                    if opponent not in defensive_stats:
                        defensive_stats[opponent] = {
                            'Passing Yards Allowed': 0,
                            'Passing TDs Allowed': 0,
                            'Rushing Yards Allowed': 0,
                            'Rushing TDs Allowed': 0,
                            'games': 0
                        }
                    
                    # Aggregate offensive stats as defensive stats allowed
                    # Passing
                    if pd.notna(row.get('pass_Yds')):
                        defensive_stats[opponent]['Passing Yards Allowed'] += float(row['pass_Yds'])
                    if pd.notna(row.get('pass_TD')):
                        defensive_stats[opponent]['Passing TDs Allowed'] += float(row['pass_TD'])
                    
                    # Rushing
                    if pd.notna(row.get('rush_Yds')):
                        defensive_stats[opponent]['Rushing Yards Allowed'] += float(row['rush_Yds'])
                    if pd.notna(row.get('rush_TD')):
                        defensive_stats[opponent]['Rushing TDs Allowed'] += float(row['rush_TD'])
                
                # Count games per team (number of unique opponents they faced)
                for team in opponent_map.keys():
                    opponent = opponent_map.get(team)
                    if opponent and opponent != 'BYE' and opponent in defensive_stats:
                        defensive_stats[opponent]['games'] += 1
                        
            except Exception as e:
                print(f"⚠️ Error processing Week {week} box score: {e}")
                continue
        
        # Calculate rankings for each stat type
        rankings = {}
        
        stat_types = ['Passing Yards Allowed', 'Passing TDs Allowed', 
                     'Rushing Yards Allowed', 'Rushing TDs Allowed']
        
        for stat_type in stat_types:
            # Create list of (team, average_stat) tuples
            team_stats = []
            for team, stats in defensive_stats.items():
                if stats['games'] > 0:
                    avg_stat = stats[stat_type] / stats['games']
                    team_stats.append((team, avg_stat))
            
            # Sort by stat (ascending - lower is better for defense)
            team_stats.sort(key=lambda x: x[1])
            
            # Assign ranks
            for rank, (team, _) in enumerate(team_stats, 1):
                if team not in rankings:
                    rankings[team] = {}
                rankings[team][stat_type] = rank
        
        print(f"✅ Calculated defensive rankings for {len(rankings)} teams through Week {target_week-1}")
        return rankings
    
    def _get_opponent_map_for_week(self, week: int) -> Dict[str, str]:
        """
        Get mapping of team -> opponent for a specific week
        First tries schedule data, then falls back to historical odds JSON files
        
        Args:
            week: Week number
            
        Returns:
            Dictionary mapping team name to opponent name
        """
        opponent_map = {}
        
        # Try schedule data first
        if self.schedule_data is not None and not self.schedule_data.empty:
            week_games = self.schedule_data[self.schedule_data['week'] == week]
            
            for _, game in week_games.iterrows():
                home_team = game.get('home_team', '')
                away_team = game.get('away_team', '')
                
                if home_team and away_team:
                    opponent_map[home_team] = away_team
                    opponent_map[away_team] = home_team
            
            if opponent_map:
                return opponent_map
        
        # Fallback: Load from historical odds JSON files in game_data folder
        game_data_path = f"2025/WEEK{week}/game_data"
        if os.path.exists(game_data_path):
            json_files = [f for f in os.listdir(game_data_path) if f.endswith('_historical_odds.json')]
            
            for json_file in json_files:
                try:
                    with open(os.path.join(game_data_path, json_file), 'r') as f:
                        data = json.load(f)
                    
                    event_data = data.get('data', {})
                    home_team = event_data.get('home_team', '')
                    away_team = event_data.get('away_team', '')
                    
                    if home_team and away_team:
                        opponent_map[home_team] = away_team
                        opponent_map[away_team] = home_team
                except Exception as e:
                    continue
        
        return opponent_map
    
    def scrape_week_data(self, week: int, force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """Load data for a specific week from database or CSV files"""
        
        if self.use_database and self.db_loader:
            print(f"🗄️ Loading Week {week} data from database...")
            
            try:
                # Load from database
                df = self.db_loader.load_week_data_from_db(week)
                
                if df.empty:
                    print(f"⚠️ No data found for Week {week} in database, falling back to CSV")
                    return self._load_from_csv_fallback(week)
                
                print(f"✅ Loaded {len(df)} players from database")
                # Process the data into our format (same as original)
                return self._process_scraped_data(df, week)
                
            except Exception as e:
                print(f"❌ Error loading Week {week} from database: {e}")
                print("📁 Falling back to CSV files...")
                return self._load_from_csv_fallback(week)
        else:
            # Use original CSV-based loading
            return self._load_from_csv_fallback(week)
    
    def _load_from_csv_fallback(self, week: int) -> Dict[str, pd.DataFrame]:
        """Fallback method to load data from CSV files (original behavior)"""
        print(f"📁 Loading Week {week} data from CSV files...")
        
        try:
            week_path = f"2025/WEEK{week}"
            box_score_file = f"{week_path}/box_score_debug.csv"
            
            if os.path.exists(box_score_file):
                print(f"📊 Loading existing box score data from {box_score_file}")
                # Load the existing CSV data
                master_df = pd.read_csv(box_score_file)
                
                if master_df.empty:
                    print(f"⚠️ No data found in {box_score_file}")
                    return {}
                
                print(f"✅ Loaded {len(master_df)} players from CSV")
                # Process the data into our format
                return self._process_scraped_data(master_df, week)
            else:
                print(f"❌ No box score file found at {box_score_file}")
                print(f"💡 Run the box score scraper first: python3 dfs_box_scores.py {week}")
                return {}
                    
        except Exception as e:
            print(f"❌ Error loading Week {week} from CSV: {e}")
            return {}
    
    def _process_scraped_data(self, master_df: pd.DataFrame, week: int) -> Dict[str, pd.DataFrame]:
        """Process scraped data into our internal format"""
        processed_data = {}
        
        # Convert column names to match our expected format
        column_mapping = {
            'Name': 'player',
            'team': 'team',  # Preserve team information
            'pass_Yds': 'Passing Yards',
            'pass_TD': 'Passing TDs',
            'rush_Yds': 'Rushing Yards', 
            'rush_TD': 'Rushing TDs',
            'rec_Rec': 'Receptions',
            'rec_Yds': 'Receiving Yards',
            'rec_TD': 'Receiving TDs'
        }
        
        # Rename columns
        df = master_df.copy()
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Add week information
        df['week'] = week
        
        # Store the processed data
        processed_data[f'week_{week}'] = df
        
        return processed_data
    
    def update_season_data(self, weeks: List[int] = None, force_refresh: bool = False):
        """Update season data by scraping specified weeks"""
        if weeks is None:
            weeks = list(range(1, min(self.current_week + 1, 19)))  # Up to current week
        
        print(f"🔄 Updating season data for weeks: {weeks}")
        
        all_week_data = {}
        
        for week in weeks:
            # Check if we already have this week's data
            week_key = f'week_{week}'
            if not force_refresh and week_key in self.player_season_stats:
                print(f"⏭️ Week {week} data already available, skipping...")
                continue
            
            # Scrape the week's data
            week_data = self.scrape_week_data(week, force_refresh)
            if week_data:
                all_week_data.update(week_data)
        
        if all_week_data:
            # Combine all weeks into season stats
            self._build_season_stats(all_week_data)
            
            # Calculate team defensive stats
            self._build_team_defensive_stats(all_week_data)
            
            # Save to cache
            self._save_cache(self.player_season_stats, "player_season")
            self._save_cache(self.team_defensive_stats, "team_defensive")
            
            print(f"✅ Updated season data with {len(all_week_data)} weeks")
        else:
            print("⚠️ No new data to update")
    
    def _build_season_stats(self, all_week_data: Dict[str, pd.DataFrame]):
        """Build player season stats from weekly data including home/away splits"""
        print("📊 Building player season stats with home/away splits...")
        
        # Combine all weeks with week numbers
        all_games = []
        for week_key, week_df in all_week_data.items():
            if not week_df.empty:
                # Extract week number from key (e.g., 'week_1' -> 1)
                week_num = int(week_key.split('_')[1]) if '_' in week_key else 0
                week_df_copy = week_df.copy()
                week_df_copy['week'] = week_num
                all_games.append(week_df_copy)
        
        if not all_games:
            return
        
        combined_df = pd.concat(all_games, ignore_index=True)
        
        # Group by player and build season stats
        player_stats = {}
        
        for player in combined_df['player'].unique():
            player_data = combined_df[combined_df['player'] == player]
            
            player_stats[player] = {}
            
            # Store team information (use most recent team if player changed teams)
            if 'team' in player_data.columns:
                team_values = player_data['team'].dropna()
                if len(team_values) > 0:
                    # Use the most recent team (last value)
                    player_stats[player]['team'] = team_values.iloc[-1]
            
            # Calculate stats for each category
            stat_categories = ['Passing Yards', 'Passing TDs', 'Rushing Yards', 'Rushing TDs', 
                             'Receptions', 'Receiving Yards', 'Receiving TDs']
            
            for stat in stat_categories:
                if stat in player_data.columns:
                    # Get non-null values for this stat with team and week info
                    stat_data = player_data[['team', 'week', stat]].dropna(subset=[stat])
                    
                    if len(stat_data) > 0:
                        # Convert to numeric and get actual values
                        stat_data[stat] = pd.to_numeric(stat_data[stat], errors='coerce')
                        stat_data = stat_data.dropna(subset=[stat])
                        
                        if len(stat_data) > 0:
                            # All games - store both values and week numbers
                            player_stats[player][stat] = stat_data[stat].tolist()
                            player_stats[player][f"{stat}_weeks"] = stat_data['week'].tolist()
                            
                            # Split by home/away
                            home_values = []
                            home_weeks = []
                            away_values = []
                            away_weeks = []
                            
                            for _, row in stat_data.iterrows():
                                team = row['team']
                                week = row['week']
                                value = row[stat]
                                
                                is_home = self.is_home_game(team, week)
                                if is_home == True:
                                    home_values.append(value)
                                    home_weeks.append(week)
                                elif is_home == False:
                                    away_values.append(value)
                                    away_weeks.append(week)
                                # If None (bye week or not found), we skip it
                            
                            # Store home/away splits with week numbers
                            if home_values:
                                player_stats[player][f"{stat}_home"] = home_values
                                player_stats[player][f"{stat}_home_weeks"] = home_weeks
                            if away_values:
                                player_stats[player][f"{stat}_away"] = away_values
                                player_stats[player][f"{stat}_away_weeks"] = away_weeks
        
        self.player_season_stats = player_stats
        self._rebuild_player_name_index()
        print(f"✅ Built season stats for {len(player_stats)} players with home/away splits")
    
    def _build_team_defensive_stats(self, all_week_data: Dict[str, pd.DataFrame]):
        """Build team defensive stats using ESPN data and NFL.com TD data"""
        print("🛡️ Building team defensive stats using ESPN and NFL.com data...")
        
        try:
            # Use unified defensive scraper to get all defensive stats
            defensive_scraper = DefensiveScraper()
            defensive_data = defensive_scraper.update_defensive_stats()
            
            # Extract yards rankings and TD data from combined defensive data
            yards_rankings = {team: {k: v for k, v in stats.items() if 'Allowed' in k and 'TDs' not in k}
                            for team, stats in defensive_data.items()}
            td_data = {team: {k: v for k, v in stats.items() if 'TDs Allowed' in k}
                      for team, stats in defensive_data.items()}
            
            if yards_rankings and td_data:
                # Combine yards and TD data
                combined_rankings = self._combine_defensive_data(yards_rankings, td_data)
                print(f"✅ Loaded combined defensive rankings for {len(combined_rankings)} teams")
                self.team_defensive_stats = combined_rankings
                return
            elif yards_rankings:
                print(f"✅ Loaded ESPN defensive rankings for {len(yards_rankings)} teams (no TD data)")
                self.team_defensive_stats = yards_rankings
                return
            
            print("⚠️ No defensive data available, using fallback")
            self._use_fallback_defensive_stats()
            return
            
        except Exception as e:
            print(f"⚠️ Error building team defensive stats: {e}")
            print("Using fallback defensive stats")
            self._use_fallback_defensive_stats()
    
    def _combine_defensive_data(self, yards_rankings: Dict, td_data: Dict) -> Dict:
        """Combine ESPN yards rankings with NFL.com TD data"""
        print("🔄 Combining yards and TD defensive data...")
        
        combined_rankings = {}
        
        # Start with yards data
        for team, stats in yards_rankings.items():
            combined_rankings[team] = stats.copy()
        
        # Add TD rankings (already calculated by defensive_scraper)
        for team, td_stats in td_data.items():
            if team in combined_rankings:
                combined_rankings[team].update(td_stats)
            else:
                # If team not in yards data, create entry with just TD data
                combined_rankings[team] = td_stats
        
        # Note: TD data is already in ranking format from defensive_scraper,
        # no need to convert again
        
        return combined_rankings
    
    def _convert_td_counts_to_rankings(self, defensive_stats: Dict):
        """Convert TD counts to rankings (lower TDs = better defense = lower rank)"""
        # Extract TD counts for ranking
        passing_tds = {}
        rushing_tds = {}
        
        for team, stats in defensive_stats.items():
            if 'Passing TDs Allowed' in stats:
                passing_tds[team] = stats['Passing TDs Allowed']
            if 'Rushing TDs Allowed' in stats:
                rushing_tds[team] = stats['Rushing TDs Allowed']
        
        # Convert to rankings (lower TDs = better rank)
        if passing_tds:
            sorted_passing = sorted(passing_tds.items(), key=lambda x: x[1])
            for rank, (team, _) in enumerate(sorted_passing, 1):
                if team in defensive_stats:
                    defensive_stats[team]['Passing TDs Allowed'] = rank
        
        if rushing_tds:
            sorted_rushing = sorted(rushing_tds.items(), key=lambda x: x[1])
            for rank, (team, _) in enumerate(sorted_rushing, 1):
                if team in defensive_stats:
                    defensive_stats[team]['Rushing TDs Allowed'] = rank
    
    def _convert_position_analysis_to_defensive_stats(self, position_results: Dict):
        """Convert position vs team analysis results to defensive stats format"""
        print("🔄 Converting position analysis to defensive stats...")
        
        # Team abbreviation to full name mapping
        team_mapping = {
            'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs', 'LV': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
            'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
            'SF': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'
        }
        
        # Convert DFS points to approximate yards allowed
        # These are rough conversions based on typical DFS scoring
        defensive_stats = {
            'Passing Yards Allowed': {},
            'Rushing Yards Allowed': {},
            'Receiving Yards Allowed': {}
        }
        
        for team_abbrev, position_data in position_results.items():
            full_team_name = team_mapping.get(team_abbrev, team_abbrev)
            
            # Convert QB DFS points to approximate passing yards allowed
            if 'QB' in position_data:
                # Rough conversion: QB DFS points to passing yards
                # QB gets 0.04 points per yard + 4 per TD + bonuses
                qb_points = position_data['QB']
                # Estimate passing yards (this is approximate)
                passing_yards = max(150, min(400, (qb_points - 10) * 25))  # Rough estimate
                defensive_stats['Passing Yards Allowed'][full_team_name] = int(passing_yards)
            
            # Convert RB DFS points to approximate rushing yards allowed
            if 'RB' in position_data:
                # RB gets 0.1 points per yard + 6 per TD + 1 per reception
                rb_points = position_data['RB']
                # Estimate rushing yards (this is approximate)
                rushing_yards = max(50, min(200, rb_points * 8))  # Rough estimate
                defensive_stats['Rushing Yards Allowed'][full_team_name] = int(rushing_yards)
            
            # Convert WR DFS points to approximate receiving yards allowed
            if 'WR' in position_data:
                # WR gets 0.1 points per yard + 6 per TD + 1 per reception
                wr_points = position_data['WR']
                # Estimate receiving yards (this is approximate)
                receiving_yards = max(100, min(350, wr_points * 6))  # Rough estimate
                defensive_stats['Receiving Yards Allowed'][full_team_name] = int(receiving_yards)
        
        # Fill in missing teams with default values
        all_teams = list(team_mapping.values())
        for stat_type in defensive_stats:
            for team in all_teams:
                if team not in defensive_stats[stat_type]:
                    # Default values based on stat type
                    if 'Passing' in stat_type:
                        defensive_stats[stat_type][team] = 250
                    elif 'Rushing' in stat_type:
                        defensive_stats[stat_type][team] = 120
                    elif 'Receiving' in stat_type:
                        defensive_stats[stat_type][team] = 250
        
        self.team_defensive_stats = defensive_stats
        print(f"✅ Converted defensive stats for {len(defensive_stats['Passing Yards Allowed'])} teams")
    
    def _use_fallback_defensive_stats(self):
        """Use fallback defensive stats when real data is not available"""
        team_defensive_rankings = {
            'Passing Yards Allowed': {
                'San Francisco 49ers': 195, 'Buffalo Bills': 205, 'New York Jets': 210,
                'Pittsburgh Steelers': 215, 'New England Patriots': 220, 'Baltimore Ravens': 220,
                'Cleveland Browns': 225, 'New Orleans Saints': 225, 'Cincinnati Bengals': 235,
                'Kansas City Chiefs': 235, 'Minnesota Vikings': 235, 'Tampa Bay Buccaneers': 235,
                'Philadelphia Eagles': 230, 'Los Angeles Rams': 230, 'Green Bay Packers': 230,
                'Indianapolis Colts': 240, 'Miami Dolphins': 240, 'Tennessee Titans': 240,
                'Atlanta Falcons': 240, 'Carolina Panthers': 230, 'Chicago Bears': 245,
                'Detroit Lions': 245, 'Jacksonville Jaguars': 245, 'Los Angeles Chargers': 245,
                'Seattle Seahawks': 245, 'Arizona Cardinals': 250, 'Dallas Cowboys': 250,
                'Houston Texans': 250, 'Las Vegas Raiders': 250, 'Denver Broncos': 255,
                'New York Giants': 250, 'Washington Commanders': 250
            },
            'Rushing Yards Allowed': {
                'San Francisco 49ers': 85, 'Buffalo Bills': 90, 'New York Jets': 95,
                'Pittsburgh Steelers': 95, 'New England Patriots': 100, 'Baltimore Ravens': 100,
                'Cleveland Browns': 100, 'New Orleans Saints': 105, 'Cincinnati Bengals': 105,
                'Kansas City Chiefs': 110, 'Minnesota Vikings': 110, 'Tampa Bay Buccaneers': 110,
                'Philadelphia Eagles': 110, 'Los Angeles Rams': 110, 'Green Bay Packers': 115,
                'Indianapolis Colts': 115, 'Miami Dolphins': 115, 'Tennessee Titans': 115,
                'Atlanta Falcons': 115, 'Carolina Panthers': 110, 'Chicago Bears': 120,
                'Detroit Lions': 120, 'Jacksonville Jaguars': 120, 'Los Angeles Chargers': 120,
                'Seattle Seahawks': 120, 'Arizona Cardinals': 125, 'Dallas Cowboys': 125,
                'Houston Texans': 125, 'Las Vegas Raiders': 125, 'Denver Broncos': 130,
                'New York Giants': 130, 'Washington Commanders': 130
            },
            'Receiving Yards Allowed': {
                'San Francisco 49ers': 195, 'Buffalo Bills': 205, 'New York Jets': 210,
                'Pittsburgh Steelers': 215, 'New England Patriots': 220, 'Baltimore Ravens': 220,
                'Cleveland Browns': 225, 'New Orleans Saints': 225, 'Cincinnati Bengals': 235,
                'Kansas City Chiefs': 235, 'Minnesota Vikings': 235, 'Tampa Bay Buccaneers': 235,
                'Philadelphia Eagles': 230, 'Los Angeles Rams': 230, 'Green Bay Packers': 230,
                'Indianapolis Colts': 240, 'Miami Dolphins': 240, 'Tennessee Titans': 240,
                'Atlanta Falcons': 240, 'Carolina Panthers': 230, 'Chicago Bears': 245,
                'Detroit Lions': 245, 'Jacksonville Jaguars': 245, 'Los Angeles Chargers': 245,
                'Seattle Seahawks': 245, 'Arizona Cardinals': 250, 'Dallas Cowboys': 250,
                'Houston Texans': 250, 'Las Vegas Raiders': 250, 'Denver Broncos': 255,
                'New York Giants': 250, 'Washington Commanders': 250
            }
        }
        
        self.team_defensive_stats = team_defensive_rankings
    
    # Interface methods that match the original data processor
    def get_team_defensive_rank(self, team: str, stat_type: str) -> int:
        """Get team defensive ranking for a specific stat"""
        # Use historical rankings if max_week is set and we have the data
        if self.max_week is not None and self.historical_defensive_stats:
            return self._get_historical_team_defensive_rank(team, stat_type)
        
        # Otherwise use season-long rankings
        if not self.team_defensive_stats:
            self.update_season_data()
        
        # Convert stat type to defensive stat format (e.g., "Passing Yards" -> "Passing Yards Allowed")
        # Map stat types to their defensive equivalents
        # Note: ESPN doesn't have separate receiving stats, so we use passing stats as proxy
        stat_mapping = {
            'Passing Yards': 'Passing Yards Allowed',
            'Passing TDs': 'Passing TDs Allowed',
            'Rushing Yards': 'Rushing Yards Allowed',
            'Rushing TDs': 'Rushing TDs Allowed',
            'Receptions': 'Passing Yards Allowed',      # Use passing defense as proxy
            'Receiving Yards': 'Passing Yards Allowed',  # Use passing defense as proxy
            'Receiving TDs': 'Passing TDs Allowed'       # Use passing TDs as proxy
        }
        
        defensive_stat = stat_mapping.get(stat_type, stat_type + ' Allowed')
        
        # The ESPN data is organized by team first, then by stat type
        if team in self.team_defensive_stats and defensive_stat in self.team_defensive_stats[team]:
            return self.team_defensive_stats[team][defensive_stat]
        
        # Try case-insensitive matching
        for team_name, stats in self.team_defensive_stats.items():
            if team_name.lower() == team.lower() and defensive_stat in stats:
                return stats[defensive_stat]
        
        return None  # Return None if team not found (will display as N/A)
    
    def get_position_defensive_rank(self, team: str, player_name: str, stat_type: str) -> int:
        """
        Get position-specific defensive ranking for a team against a player's stat type
        
        Args:
            team: Opposing team name
            player_name: Player name
            stat_type: Stat type (e.g., 'Passing Yards', 'Receiving Yards')
            
        Returns:
            Defensive ranking (1 = worst defense, higher = better defense) or None
        """
        if self.skip_calculations:
            # Load from database instead of calculating
            try:
                from database.database_manager import DatabaseManager
                db_manager = DatabaseManager()
                
                with db_manager.get_session() as session:
                    from database.database_models import Prop
                    # Get the most recent prop for this team/stat combination
                    prop = session.query(Prop).filter(
                        Prop.opp_team == team,
                        Prop.stat_type == stat_type,
                        Prop.team_pos_rank_stat_type.isnot(None)
                    ).first()
                    
                    if prop and prop.team_pos_rank_stat_type:
                        return prop.team_pos_rank_stat_type
                    
                return None
            except Exception as e:
                print(f"⚠️ Error getting defensive rank from database: {e}")
                return None
        elif hasattr(self, 'position_defensive_rankings') and self.position_defensive_rankings:
            return self.position_defensive_rankings.get_position_defensive_rank(team, player_name, stat_type)
        return None
    
    def _get_historical_team_defensive_rank(self, team: str, stat_type: str) -> int:
        """Get historical defensive ranking for a team (used when max_week is set)"""
        # Map stat types to defensive stat format
        stat_mapping = {
            'Passing Yards': 'Passing Yards Allowed',
            'Passing TDs': 'Passing TDs Allowed',
            'Rushing Yards': 'Rushing Yards Allowed',
            'Rushing TDs': 'Rushing TDs Allowed',
            'Receptions': 'Passing Yards Allowed',
            'Receiving Yards': 'Passing Yards Allowed',
            'Receiving TDs': 'Passing TDs Allowed'
        }
        
        defensive_stat = stat_mapping.get(stat_type, stat_type + ' Allowed')
        
        # Look up in historical rankings
        if team in self.historical_defensive_stats and defensive_stat in self.historical_defensive_stats[team]:
            return self.historical_defensive_stats[team][defensive_stat]
        
        # Try case-insensitive matching
        for team_name, stats in self.historical_defensive_stats.items():
            if team_name.lower() == team.lower() and defensive_stat in stats:
                return stats[defensive_stat]
        
        return None  # Return None if team not found (will display as N/A)
    
    def _filter_games_by_week(self, games: list, weeks: list) -> list:
        """
        Filter games to include only those before max_week
        
        Args:
            games: List of game stats
            weeks: List of week numbers (same length as games)
            
        Returns:
            Filtered list of games
        """
        if self.max_week is None or not weeks:
            return games
        
        # Filter to only include games before max_week
        filtered_games = [game for game, week in zip(games, weeks) if week < self.max_week]
        return filtered_games if filtered_games else games  # Return all if filtered is empty
    
    def _filter_games_by_week_with_weeks(self, games: list, weeks: list) -> list:
        """
        Filter games to include only those before max_week, returning both games and weeks
        
        Args:
            games: List of game stats
            weeks: List of week numbers (same length as games)
            
        Returns:
            List of tuples [(game, week), ...] with filtered data
        """
        if self.max_week is None or not weeks:
            return list(zip(games, weeks))
        
        # Filter to only include games before max_week
        filtered_data = [(game, week) for game, week in zip(games, weeks) if week < self.max_week]
        return filtered_data if filtered_data else list(zip(games, weeks))  # Return all if filtered is empty
    
    def get_player_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line this season
        Returns None if no data is available"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and stat_type in self.player_season_stats[player_key]:
            games = self.player_season_stats[player_key][stat_type]
            weeks = self.player_season_stats[player_key].get(f"{stat_type}_weeks", [])
            
            # Filter by max_week if set
            games = self._filter_games_by_week(games, weeks)
            
            if games:
                over_count = sum(1 for game_stat in games if game_stat > line)
                return over_count / len(games)
        
        return None  # Return None if no data available
    
    def get_player_home_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line in home games
        Returns None if no home game data is available"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        home_stat_key = f"{stat_type}_home"
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and home_stat_key in self.player_season_stats[player_key]:
            games = self.player_season_stats[player_key][home_stat_key]
            weeks = self.player_season_stats[player_key].get(f"{home_stat_key}_weeks", [])
            
            # Filter by max_week if set
            games = self._filter_games_by_week(games, weeks)
            
            if games:
                over_count = sum(1 for game_stat in games if game_stat > line)
                return over_count / len(games)
        
        return None  # Return None if no home game data available
    
    def get_player_away_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line in away games
        Returns None if no away game data is available"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        away_stat_key = f"{stat_type}_away"
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and away_stat_key in self.player_season_stats[player_key]:
            games = self.player_season_stats[player_key][away_stat_key]
            weeks = self.player_season_stats[player_key].get(f"{away_stat_key}_weeks", [])
            
            # Filter by max_week if set
            games = self._filter_games_by_week(games, weeks)
            
            if games:
                over_count = sum(1 for game_stat in games if game_stat > line)
                return over_count / len(games)
        
        return None  # Return None if no away game data available
    
    def get_player_average(self, player: str, stat_type: str) -> float:
        """Get player's average for a specific stat this season
        Returns None if no data is available"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and stat_type in self.player_season_stats[player_key]:
            games = self.player_season_stats[player_key][stat_type]
            if games:
                return sum(games) / len(games)
        
        return None  # Return None if no data available
    
    def get_player_consistency(self, player: str, stat_type: str) -> float:
        """Calculate player consistency (lower standard deviation = more consistent)"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and stat_type in self.player_season_stats[player_key]:
            games = self.player_season_stats[player_key][stat_type]
            if len(games) < 2:
                return 1.0
            mean_val = sum(games) / len(games)
            variance = sum((x - mean_val) ** 2 for x in games) / len(games)
            return variance ** 0.5
        
        return 1.0  # Default high variance
    
    def get_player_team(self, player: str) -> str:
        """Get the player's current team"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Import clean function
        from utils import clean_player_name
        
        # Use index for fast lookup
        cleaned_input = clean_player_name(player)
        player_key = self.player_name_index.get(cleaned_input)
        
        if player_key and 'team' in self.player_season_stats[player_key]:
            return self.player_season_stats[player_key]['team']
        
        # Fallback: Check player_positions table for players without box score history
        # (rookies, injured reserve, new signings, etc.)
        try:
            from database.database_manager import DatabaseManager
            from database.database_models import PlayerPosition
            
            db_manager = DatabaseManager()
            with db_manager.get_session() as session:
                # Try exact match first
                player_pos = session.query(PlayerPosition).filter(
                    PlayerPosition.player == player
                ).first()
                
                # Try cleaned name match if exact fails
                if not player_pos:
                    player_pos = session.query(PlayerPosition).filter(
                        PlayerPosition.cleaned_name == cleaned_input
                    ).first()
                
                if player_pos and player_pos.team:
                    return player_pos.team
        except Exception as e:
            print(f"⚠️ Error looking up player team from database: {e}")
        
        return "Unknown"
    
    def get_player_last_n_over_rate(self, player: str, stat_type: str, line: float, n: int = 5) -> float:
        """
        Calculate the over rate for the last N games
        
        Args:
            player: Player name
            stat_type: Type of stat (e.g., "Passing Yards")
            line: The line to compare against
            n: Number of recent games to consider (default: 5)
            
        Returns:
            Over rate as a decimal (0.0 to 1.0), or None if no data available
        """
        from utils import clean_player_name
        cleaned_name = clean_player_name(player)
        
        # Use index for fast lookup
        player_key = self.player_name_index.get(cleaned_name)
        
        if not player_key or stat_type not in self.player_season_stats[player_key]:
            return None
        
        player_stats = self.player_season_stats[player_key][stat_type]
        weeks = self.player_season_stats[player_key].get(f"{stat_type}_weeks", [])
        
        # Filter by max_week if set
        player_stats = self._filter_games_by_week(player_stats, weeks)
        
        if not player_stats or len(player_stats) == 0:
            return None
        
        # Get the last N games (from filtered data)
        last_n_games = player_stats[-n:] if len(player_stats) >= n else player_stats
        
        # Calculate over rate
        over_count = sum(1 for stat in last_n_games if stat > line)
        return over_count / len(last_n_games)
    
    def get_player_streak(self, player: str, stat_type: str, line: float) -> int:
        """
        Calculate how many consecutive games (from most recent) the player has gone over the line
        Streak resets to 0 if player misses 2 or more consecutive games
        
        Args:
            player: Player name
            stat_type: Type of stat (e.g., "Passing Yards")
            line: The line to compare against
            
        Returns:
            Number of consecutive games over the line (0 if last game was under or if 2+ games missed)
        """
        from utils import clean_player_name
        cleaned_name = clean_player_name(player)
        
        # Use index for fast lookup
        player_key = self.player_name_index.get(cleaned_name)
        
        if not player_key or stat_type not in self.player_season_stats[player_key]:
            return 0
        
        player_stats = self.player_season_stats[player_key][stat_type]
        weeks = self.player_season_stats[player_key].get(f"{stat_type}_weeks", [])
        
        # Filter by max_week if set
        filtered_data = self._filter_games_by_week_with_weeks(player_stats, weeks)
        
        if not filtered_data or len(filtered_data) == 0:
            return 0
        
        # Extract filtered stats and weeks
        filtered_stats = [item[0] for item in filtered_data]
        filtered_weeks = [item[1] for item in filtered_data]
        
        streak = 0
        previous_week = None
        
        # Count backwards from most recent game
        for i in range(len(filtered_stats) - 1, -1, -1):
            stat_value = filtered_stats[i]
            current_week = filtered_weeks[i]
            
            # Check if player went over the line
            if stat_value > line:
                # Check for gap in weeks (if not the first game in streak)
                if previous_week is not None:
                    week_gap = previous_week - current_week
                    # If gap is 2 or more weeks, reset streak
                    if week_gap >= 3:  # Gap of 3 means 2 weeks missed (e.g., played week 6, then week 3 = missed weeks 4 and 5)
                        break
                
                streak += 1
                previous_week = current_week
            else:
                break  # Stop at first game that didn't go over
        
        return streak
    
    def get_player_last_n_games(self, player: str, stat_type: str, n: int = 5) -> list:
        """
        Get the actual stat values for the last N games
        
        Args:
            player: Player name
            stat_type: Type of stat (e.g., "Passing Yards")
            n: Number of recent games to get (default: 5)
            
        Returns:
            List of stat values for the last N games (most recent last)
        """
        from utils import clean_player_name
        cleaned_name = clean_player_name(player)
        
        # Find player's stats
        player_stats = None
        for stored_player, stats in self.player_season_stats.items():
            cleaned_stored = clean_player_name(stored_player)
            if cleaned_stored == cleaned_name and stat_type in stats:
                player_stats = stats[stat_type]
                break
        
        if not player_stats or len(player_stats) == 0:
            return []
        
        # Get the last N games
        last_n_games = player_stats[-n:] if len(player_stats) >= n else player_stats
        
        return last_n_games
    
    def _load_all_week_data(self) -> Dict[str, pd.DataFrame]:
        """Load all available week data from files"""
        all_week_data = {}
        
        # Look for all WEEK folders
        base_path = "2025"
        if not os.path.exists(base_path):
            return {}
        
        for week in range(1, 19):  # Check weeks 1-18
            week_path = f"{base_path}/WEEK{week}"
            box_score_file = f"{week_path}/box_score_debug.csv"
            
            if os.path.exists(box_score_file):
                try:
                    week_data = self.scrape_week_data(week, force_refresh=False)
                    if week_data:
                        all_week_data.update(week_data)
                except Exception as e:
                    # Skip weeks that can't be loaded
                    continue
        
        return all_week_data
    
    def get_player_last_n_games_detailed(self, player: str, stat_type: str, n: int = 5) -> list:
        """
        Get detailed game information for the last N games including opponents and ranks
        
        Args:
            player: Player name
            stat_type: Type of stat (e.g., "Passing Yards")
            n: Number of recent games to get (default: 5)
            
        Returns:
            List of dicts with 'value', 'opponent', 'is_home', 'defensive_rank' for last N games
        """
        from utils import clean_player_name, get_team_abbreviation
        cleaned_name = clean_player_name(player)
        
        # Load all week data to get game context
        all_week_data = self._load_all_week_data()
        if not all_week_data:
            return []
        
        combined_df = pd.concat(all_week_data.values(), ignore_index=True)
        
        # Find player's games
        player_games = combined_df[combined_df['player'].apply(lambda x: clean_player_name(x) == cleaned_name)].copy()
        
        if player_games.empty:
            return []
        
        # Get games with the specific stat
        if stat_type not in player_games.columns:
            return []
        
        player_games = player_games.dropna(subset=[stat_type])
        player_games[stat_type] = pd.to_numeric(player_games[stat_type], errors='coerce')
        player_games = player_games.dropna(subset=[stat_type])
        
        # Sort by week to get chronological order
        if 'week' in player_games.columns:
            player_games = player_games.sort_values('week')
        
        # Get last N games
        last_n_games = player_games.tail(n)
        
        game_details = []
        for _, game in last_n_games.iterrows():
            team = game.get('team', 'Unknown')
            week = game.get('week', 0)
            value = game[stat_type]
            
            # Determine if home or away
            is_home = self.is_home_game(team, week)
            
            # Get opponent (returns full name from schedule)
            opponent_full = self.get_opposing_team(team, week)
            
            # Convert full name to abbreviation for display
            opponent_abbrev = get_team_abbreviation(opponent_full)
            
            # Get defensive rank for opponent against this stat (using full name)
            defensive_rank = self.get_team_defensive_rank(opponent_full, stat_type)
            
            # Get game date in MM/DD format
            game_date = self.get_game_date(team, week)
            
            game_details.append({
                'value': value,
                'opponent': opponent_abbrev,  # Abbreviation for display
                'is_home': is_home,
                'defensive_rank': defensive_rank,
                'game_date': game_date
            })
        
        return game_details
    
    def get_opposing_team(self, player_team: str, week: int = None) -> str:
        """Get the opposing team for a given team and week"""
        if week is None:
            week = self.current_week
        
        try:
            # Use opponent mapping from game data
            if week in self.opponent_mapping and player_team in self.opponent_mapping[week]:
                return self.opponent_mapping[week][player_team]['opponent']
            
            return "Unknown"
        except Exception as e:
            print(f"Error getting opposing team for {player_team}: {e}")
            return "Unknown"
    
    def get_game_date(self, team: str, week: int = None) -> str:
        """Get the game date for a team and week in MM/DD format"""
        if week is None:
            week = self.current_week
        
        try:
            # Use opponent mapping from game data
            if week in self.opponent_mapping and team in self.opponent_mapping[week]:
                game_time = self.opponent_mapping[week][team]['game_time']
                if game_time:
                    # Parse ISO format datetime (e.g., "2025-10-07T00:16:00Z")
                    try:
                        date_obj = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                        # Return in MM/DD format
                        return date_obj.strftime("%m/%d")
                    except:
                        pass
            
            return ""
        except Exception as e:
            print(f"Error getting game date for {team}: {e}")
            return ""
    
    def get_week_from_matchup(self, team1: str, team2: str) -> Optional[int]:
        """
        Determine the week number based on a team matchup
        
        Args:
            team1: First team name (full name like "Kansas City Chiefs")
            team2: Second team name (full name like "Buffalo Bills")
            
        Returns:
            Week number if matchup found, None otherwise
        """
        try:
            if self.schedule_data is None or self.schedule_data.empty:
                return None
            
            # Search for matchup in either direction (home vs away or away vs home)
            for _, game in self.schedule_data.iterrows():
                home_team = game['Home'].strip()
                away_team = game['Away'].strip()
                
                # Check if teams match in either direction
                if (home_team == team1 and away_team == team2) or \
                   (home_team == team2 and away_team == team1):
                    return int(game['Week'])
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error finding week from matchup: {e}")
            return None
    
    def get_matchup_details(self, team1: str, team2: str) -> Optional[Dict]:
        """
        Get comprehensive matchup details for two teams
        
        Args:
            team1: First team name
            team2: Second team name
            
        Returns:
            Dict with week, home_team, away_team, date, time, or None if not found
        """
        try:
            if self.schedule_data is None or self.schedule_data.empty:
                return None
            
            # Search for matchup
            for _, game in self.schedule_data.iterrows():
                home_team = game['Home'].strip()
                away_team = game['Away'].strip()
                
                # Check if teams match in either direction
                if (home_team == team1 and away_team == team2) or \
                   (home_team == team2 and away_team == team1):
                    return {
                        'week': int(game['Week']),
                        'home_team': home_team,
                        'away_team': away_team,
                        'date': game.get('Date', 'Unknown'),
                        'time': game.get('Time (ET)', 'Unknown'),
                        'is_team1_home': (home_team == team1)
                    }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error getting matchup details: {e}")
            return None
    
    def get_player_detailed_stats(self, player: str) -> Dict:
        """Get detailed stats for a player (for dashboard display)"""
        if not self.player_season_stats:
            self.update_season_data()
        
        if player not in self.player_season_stats:
            return {}
        
        player_data = self.player_season_stats[player]
        detailed_stats = {}
        
        for stat_type, values in player_data.items():
            if values:
                detailed_stats[stat_type] = {
                    'games': len(values),
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'values': values,
                    'consistency': np.std(values) if len(values) > 1 else 0
                }
        
        return detailed_stats
    
    def get_available_players(self) -> List[str]:
        """Get list of all available players"""
        if not self.player_season_stats:
            self.update_season_data()
        
        return list(self.player_season_stats.keys())
    
    def get_data_summary(self) -> Dict:
        """Get summary of available data"""
        if not self.player_season_stats:
            self.update_season_data()
        
        total_players = len(self.player_season_stats)
        total_games = sum(len(values) for player_data in self.player_season_stats.values() 
                         for values in player_data.values())
        
        return {
            'total_players': total_players,
            'total_games': total_games,
            'current_week': self.current_week,
            'cache_status': {
                'team_defensive': os.path.exists(self._get_cache_file("team_defensive")),
                'player_season': os.path.exists(self._get_cache_file("player_season"))
            }
        }
    
    def get_available_weeks_from_db(self) -> List[int]:
        """Get list of weeks available in the database"""
        if self.use_database and self.db_loader:
            try:
                return self.db_loader.get_available_weeks()
            except Exception as e:
                print(f"❌ Error getting available weeks from database: {e}")
                return []
        else:
            # Fallback to file system check
            available_weeks = []
            for week in range(1, 19):  # Check weeks 1-18
                box_score_file = f"2025/WEEK{week}/box_score_debug.csv"
                if os.path.exists(box_score_file):
                    available_weeks.append(week)
            return available_weeks
    
    def close(self):
        """Close database connections"""
        if hasattr(self, 'db_loader') and self.db_loader:
            self.db_loader.close()
