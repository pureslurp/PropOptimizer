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
from dfs_box_scores import FootballDBScraper
from simple_box_score_processor import process_box_score_simple, create_simplified_defensive_rankings, convert_to_defensive_yards
from espn_defensive_scraper import ESPNDefensiveScraper
import warnings
warnings.filterwarnings('ignore')

class EnhancedFootballDataProcessor:
    """Enhanced data processor that uses real FootballDB data"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.team_defensive_stats = {}
        self.player_season_stats = {}
        self.current_week = self._get_current_week()
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load cached data if available
        self._load_cached_data()
        
    def _get_current_week(self) -> int:
        """Get current NFL week"""
        current_date = datetime.now()
        # NFL season typically starts first week of September
        season_start = datetime(current_date.year, 9, 1)
        weeks_elapsed = (current_date - season_start).days // 7
        return min(max(1, weeks_elapsed), 18)  # NFL regular season is 18 weeks max
    
    def _get_cache_file(self, data_type: str) -> str:
        """Get cache file path for a data type"""
        return os.path.join(self.data_dir, f"{data_type}_cache.pkl")
    
    def _is_cache_valid(self, cache_file: str, max_age_hours: int = 24) -> bool:
        """Check if cache file is still valid"""
        if not os.path.exists(cache_file):
            return False
        
        # Check if cache is older than max_age_hours
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        return age_hours < max_age_hours
    
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
    
    def scrape_week_data(self, week: int, force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """Load data for a specific week from existing files (no re-scraping)"""
        print(f"📁 Loading Week {week} data from existing files...")
        
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
                
                print(f"✅ Loaded {len(master_df)} players from existing data")
                # Process the data into our format
                return self._process_scraped_data(master_df, week)
            else:
                print(f"❌ No box score file found at {box_score_file}")
                print(f"💡 Run the box score scraper first: python3 dfs_box_scores.py {week}")
                return {}
                    
        except Exception as e:
            print(f"❌ Error loading Week {week} data: {e}")
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
        """Build player season stats from weekly data"""
        print("📊 Building player season stats...")
        
        # Combine all weeks
        all_games = []
        for week_key, week_df in all_week_data.items():
            if not week_df.empty:
                all_games.append(week_df)
        
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
                    # Get non-null values for this stat
                    values = player_data[stat].dropna()
                    if len(values) > 0:
                        # Convert to numeric and get actual values
                        numeric_values = pd.to_numeric(values, errors='coerce').dropna()
                        if len(numeric_values) > 0:
                            player_stats[player][stat] = numeric_values.tolist()
        
        self.player_season_stats = player_stats
        print(f"✅ Built season stats for {len(player_stats)} players")
    
    def _build_team_defensive_stats(self, all_week_data: Dict[str, pd.DataFrame]):
        """Build team defensive stats using ESPN data"""
        print("🛡️ Building team defensive stats using ESPN data...")
        
        try:
            # Use ESPN defensive scraper to get real rankings
            espn_scraper = ESPNDefensiveScraper()
            defensive_rankings = espn_scraper.get_defensive_rankings()
            
            if defensive_rankings:
                print(f"✅ Loaded ESPN defensive rankings for {len(defensive_rankings)} teams")
                self.team_defensive_stats = defensive_rankings
                return
            
            print("⚠️ No ESPN defensive data available, using fallback")
            self._use_fallback_defensive_stats()
            return
            
        except Exception as e:
            print(f"⚠️ Error building team defensive stats: {e}")
            print("Using fallback defensive stats")
            self._use_fallback_defensive_stats()
    
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
        if not self.team_defensive_stats:
            self.update_season_data()
        
        # The ESPN data is organized by team first, then by stat type
        if team in self.team_defensive_stats and stat_type in self.team_defensive_stats[team]:
            return self.team_defensive_stats[team][stat_type]
        
        # Try case-insensitive matching
        for team_name, stats in self.team_defensive_stats.items():
            if team_name.lower() == team.lower() and stat_type in stats:
                return stats[stat_type]
        
        return 16  # Default middle ranking if team not found
    
    def get_player_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line this season"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Try exact match first
        if player in self.player_season_stats and stat_type in self.player_season_stats[player]:
            games = self.player_season_stats[player][stat_type]
            over_count = sum(1 for game_stat in games if game_stat > line)
            return over_count / len(games) if games else 0.5
        
        # Try case-insensitive matching
        for stored_player, stats in self.player_season_stats.items():
            if stored_player.lower() == player.lower() and stat_type in stats:
                games = stats[stat_type]
                over_count = sum(1 for game_stat in games if game_stat > line)
                return over_count / len(games) if games else 0.5
        
        return 0.5  # Default 50% if no data
    
    def get_player_average(self, player: str, stat_type: str) -> float:
        """Get player's average for a specific stat this season"""
        if not self.player_season_stats:
            self.update_season_data()
        
        if player not in self.player_season_stats or stat_type not in self.player_season_stats[player]:
            return 0.0
        
        games = self.player_season_stats[player][stat_type]
        return sum(games) / len(games) if games else 0.0
    
    def get_player_consistency(self, player: str, stat_type: str) -> float:
        """Calculate player consistency (lower standard deviation = more consistent)"""
        if not self.player_season_stats:
            self.update_season_data()
        
        if player not in self.player_season_stats or stat_type not in self.player_season_stats[player]:
            return 1.0  # Default high variance
        
        games = self.player_season_stats[player][stat_type]
        if len(games) < 2:
            return 1.0
        
        mean_val = sum(games) / len(games)
        variance = sum((x - mean_val) ** 2 for x in games) / len(games)
        return variance ** 0.5
    
    def get_player_team(self, player: str) -> str:
        """Get the player's current team"""
        if not self.player_season_stats:
            self.update_season_data()
        
        # Try exact match first
        if player in self.player_season_stats and 'team' in self.player_season_stats[player]:
            return self.player_season_stats[player]['team']
        
        # Try case-insensitive matching
        for stored_player, stats in self.player_season_stats.items():
            if stored_player.lower() == player.lower() and 'team' in stats:
                return stats['team']
        
        return "Unknown"
    
    def get_opposing_team(self, player_team: str, week: int = None) -> str:
        """Get the opposing team for a given team and week"""
        if week is None:
            week = self.current_week
        
        try:
            # Load schedule data
            schedule_file = "2025/nfl_schedule.csv"
            if not os.path.exists(schedule_file):
                return "Unknown"
            
            import pandas as pd
            schedule_df = pd.read_csv(schedule_file)
            
            # Find the game for this team in the specified week
            week_games = schedule_df[schedule_df['Week'] == week]
            
            for _, game in week_games.iterrows():
                home_team = game['Home'].strip()
                away_team = game['Away'].strip()
                
                if player_team == home_team:
                    return away_team
                elif player_team == away_team:
                    return home_team
            
            return "Unknown"
        except Exception as e:
            print(f"Error getting opposing team for {player_team}: {e}")
            return "Unknown"
    
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
