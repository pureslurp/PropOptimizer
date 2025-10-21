"""
Database-enhanced version of Enhanced Data Processor that loads box score data from database
instead of CSV files
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
import json
from datetime import datetime, timedelta
import pickle
import warnings
warnings.filterwarnings('ignore')

from utils import clean_player_name

# Import the original processor and our database loader
from enhanced_data_processor import EnhancedFootballDataProcessor
from .database_manager import DatabaseManager
from .database_models import BoxScore

class DatabaseBoxScoreLoader:
    """Load box score data from database instead of CSV files"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def load_week_data_from_db(self, week: int) -> pd.DataFrame:
        """Load box score data for a specific week from the database"""
        print(f"📊 Loading Week {week} box score data from database...")
        
        try:
            with self.db_manager.get_session() as session:
                # Query all box score records for the week
                box_scores = session.query(BoxScore).filter(BoxScore.week == week).all()
                
                if not box_scores:
                    print(f"⚠️ No box score data found for Week {week} in database")
                    return pd.DataFrame()
                
                print(f"✅ Found {len(box_scores)} box score records for Week {week}")
                
                # Convert to DataFrame format similar to CSV structure
                data = []
                for record in box_scores:
                    # Create a row similar to the CSV format
                    row = {
                        'Name': record.player,
                        'stat_type': record.stat_type,
                        'actual_result': record.actual_result,
                        'week': record.week,
                        'team': record.team if hasattr(record, 'team') else 'Unknown'
                    }
                    data.append(row)
                
                df = pd.DataFrame(data)
                
                # Pivot the data to match CSV format (one row per player, columns for each stat)
                if not df.empty:
                    # Get team information for each player (should be consistent across stat types)
                    team_info = df.groupby('Name')['team'].first().reset_index()
                    
                    # Create a pivot table with players as index and stat types as columns
                    pivot_df = df.pivot_table(
                        index='Name', 
                        columns='stat_type', 
                        values='actual_result', 
                        fill_value=0
                    ).reset_index()
                    
                    # Add team information back to the pivot table
                    pivot_df = pivot_df.merge(team_info, on='Name', how='left')
                    
                    # Rename columns to match CSV format
                    column_mapping = {
                        'Passing Yards': 'pass_Yds',
                        'Passing TDs': 'pass_TD',
                        'Rushing Yards': 'rush_Yds',
                        'Rushing TDs': 'rush_TD',
                        'Receiving Yards': 'rec_Yds',
                        'Receiving TDs': 'rec_TD',
                        'Receptions': 'rec_Rec'
                    }
                    
                    pivot_df = pivot_df.rename(columns=column_mapping)
                    
                    # Add missing columns with default values to match CSV format
                    required_columns = [
                        'Name', 'team', 'pass_Yds', 'pass_TD', 'pass_INT', 'pass_Att', 'pass_Cmp',
                        'rush_Yds', 'rush_TD', 'rush_Att', 'rec_Rec', 'rec_Yds', 'rec_TD', 'rec_Tar'
                    ]
                    
                    for col in required_columns:
                        if col not in pivot_df.columns:
                            if col == 'team':
                                # Team info should already be in the dataframe from database
                                if 'team' not in pivot_df.columns:
                                    pivot_df[col] = 'Unknown'
                            elif col in ['pass_INT', 'pass_Att', 'pass_Cmp', 'rec_Tar']:
                                pivot_df[col] = 0  # Default to 0 for missing columns
                            else:
                                pivot_df[col] = 0
                    
                    # Reorder columns to match CSV format
                    pivot_df = pivot_df[required_columns]
                    
                    # Add Name_clean column for matching (required by get_actual_stat function)
                    from utils import clean_player_name
                    pivot_df['Name_clean'] = pivot_df['Name'].apply(clean_player_name)
                    
                    print(f"✅ Converted to DataFrame with {len(pivot_df)} players")
                    return pivot_df
                
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error loading Week {week} data from database: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_available_weeks(self) -> List[int]:
        """Get list of weeks that have box score data in the database"""
        try:
            with self.db_manager.get_session() as session:
                weeks = session.query(BoxScore.week).distinct().order_by(BoxScore.week).all()
                return [week[0] for week in weeks]
        except Exception as e:
            print(f"❌ Error getting available weeks: {e}")
            return []
    
    def _get_team_info_from_csv_fallback(self, week: int, player_names: List[str]) -> List[str]:
        """Get team information from CSV fallback to populate missing team data"""
        try:
            week_path = f"2025/WEEK{week}"
            box_score_file = f"{week_path}/box_score_debug.csv"
            
            if os.path.exists(box_score_file):
                # Load CSV to get team information
                csv_df = pd.read_csv(box_score_file)
                
                # Create a mapping from cleaned player name to team
                team_mapping = {}
                for _, row in csv_df.iterrows():
                    player_name = row['Name']
                    cleaned_name = clean_player_name(player_name)
                    team = row['team']
                    team_mapping[cleaned_name] = team
                
                # Map each player to their team using cleaned names
                teams = []
                for player_name in player_names:
                    cleaned_player_name = clean_player_name(player_name)
                    team = team_mapping.get(cleaned_player_name, 'Unknown')
                    teams.append(team)
                
                return teams
            else:
                print(f"⚠️ No CSV file found for Week {week}, using Unknown for all teams")
                return ['Unknown'] * len(player_names)
                
        except Exception as e:
            print(f"⚠️ Error getting team info from CSV for Week {week}: {e}")
            return ['Unknown'] * len(player_names)
    
    def close(self):
        """Close database connection"""
        # DatabaseManager uses context managers, no explicit close needed
        pass

class DatabaseEnhancedFootballDataProcessor(EnhancedFootballDataProcessor):
    """
    Enhanced Data Processor that loads box score data from database instead of CSV files
    Inherits all functionality from the original processor but overrides data loading methods
    """
    
    def __init__(self, data_dir: str = "data", max_week: int = None, skip_calculations: bool = False):
        self.use_database = True  # Always use database now
        self.skip_calculations = skip_calculations
        self.db_loader = DatabaseBoxScoreLoader()  # Always use database loader
        
        if skip_calculations:
            # Custom initialization that skips expensive calculations
            self.data_dir = data_dir
            self.team_defensive_stats = {}
            self.historical_defensive_stats = {}
            self.player_season_stats = {}
            self.player_name_index = {}
            self.current_week = self._get_current_week()
            self.max_week = max_week
            self.schedule_data = self._load_schedule()
            self.opponent_mapping = self._build_opponent_mapping_from_game_data()
            
            # Create data directory if it doesn't exist
            import os
            os.makedirs(data_dir, exist_ok=True)
            
            # Load cached data if available
            self._load_cached_data()
            
            # Skip the expensive position_defensive_rankings calculation
            self.position_defensive_rankings = None
        else:
            # Initialize parent class normally (this will load cached data and other initialization)
            super().__init__(data_dir, max_week)
        
        print("🗄️ Using database for box score data loading")
    
    def get_position_defensive_rank(self, team: str, player_name: str, stat_type: str) -> int:
        """Get position-specific defensive ranking from existing database data"""
        if self.skip_calculations:
            # Use existing data from database instead of calculating
            try:
                from .database_manager import DatabaseManager
                db_manager = DatabaseManager()
                
                with db_manager.get_session() as session:
                    from .database_models import Prop
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
        else:
            # Use parent class method for calculations
            return super().get_position_defensive_rank(team, player_name, stat_type)
    
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
        print(f"📁 Loading Week {week} data from CSV files (fallback)...")
        
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
            for week in range(1, 8):  # Check weeks 1-7
                box_score_file = f"2025/WEEK{week}/box_score_debug.csv"
                if os.path.exists(box_score_file):
                    available_weeks.append(week)
            return available_weeks
    
    def close(self):
        """Close database connections"""
        if self.db_loader:
            self.db_loader.close()
