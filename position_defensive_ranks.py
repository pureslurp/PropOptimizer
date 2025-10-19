"""
Position-specific defensive rankings system
This module handles mapping player positions to specific defensive stats
and provides position-aware defensive rankings.
"""

import pandas as pd
import os
import json
from typing import Dict, Optional, Tuple, List
from utils import clean_player_name, get_team_abbreviation

class PositionDefensiveRankings:
    def __init__(self, data_dir: str = "2025"):
        self.data_dir = data_dir
        self.player_positions = {}
        self.position_stat_mapping = {
            # Quarterback stats
            'QB': {
                'Passing Yards': 'Passing Yards Allowed',
                'Passing TDs': 'Passing TDs Allowed',
                'Rushing Yards': 'QB Rushing Yards Allowed',  # Position-specific
                'Rushing TDs': 'QB Rushing TDs Allowed',     # Position-specific
            },
            
            # Running Back stats
            'RB': {
                'Rushing Yards': 'Rushing Yards Allowed',
                'Rushing TDs': 'Rushing TDs Allowed',
                'Receiving Yards': 'RB Receiving Yards Allowed',  # Position-specific
                'Receptions': 'RB Receiving Yards Allowed',       # Use receiving yards as proxy
                'Receiving TDs': 'RB Receiving TDs Allowed',      # Position-specific
            },
            
            # Wide Receiver stats
            'WR': {
                'Receiving Yards': 'WR Receiving Yards Allowed',  # Position-specific
                'Receptions': 'WR Receiving Yards Allowed',       # Use receiving yards as proxy
                'Receiving TDs': 'WR Receiving TDs Allowed',      # Position-specific
            },
            
            # Tight End stats
            'TE': {
                'Receiving Yards': 'TE Receiving Yards Allowed',  # Position-specific
                'Receptions': 'TE Receiving Yards Allowed',       # Use receiving yards as proxy
                'Receiving TDs': 'TE Receiving TDs Allowed',      # Position-specific
            },
            
            # Default fallback (for positions not explicitly mapped)
            'DEFAULT': {
                'Passing Yards': 'Passing Yards Allowed',
                'Passing TDs': 'Passing TDs Allowed',
                'Rushing Yards': 'Rushing Yards Allowed',
                'Rushing TDs': 'Rushing TDs Allowed',
                'Receiving Yards': 'Passing Yards Allowed',      # Use passing defense as proxy
                'Receptions': 'Passing Yards Allowed',           # Use passing defense as proxy
                'Receiving TDs': 'Passing TDs Allowed'           # Use passing TDs as proxy
            }
        }
        
        # Load player position data
        self._load_player_positions()
        
        # Position-specific defensive stats (calculated from box scores)
        self.position_defensive_stats = {}  # {team: {position_stat: value}}
        self.position_defensive_rankings = {}  # {position_stat: {team: rank}}
        
        # Game data abbreviation to full team name mapping
        # Note: CB is used for both Cleveland Browns and Cincinnati Bengals - need special handling
        self.game_abbrev_to_full_name = {
            'CB': None,  # Special case - will be handled separately
            'GBP': 'Green Bay Packers', 
            'BB': 'Buffalo Bills',
            'AF': 'Atlanta Falcons',
            'TBB': 'Tampa Bay Buccaneers',
            'SF4': 'San Francisco 49ers',
            'MD': 'Miami Dolphins',
            'LAC': 'Los Angeles Chargers',
            'DL': 'Detroit Lions',
            'LAR': 'Los Angeles Rams',
            'HT': 'Houston Texans',
            'MV': 'Minnesota Vikings',
            'BR': 'Baltimore Ravens',
            'JJ': 'Jacksonville Jaguars',
            'KCC': 'Kansas City Chiefs',
            'PE': 'Philadelphia Eagles',
            'SS': 'Seattle Seahawks',
            'NYJ': 'New York Jets',
            'DC': 'Dallas Cowboys',
            'DB': 'Denver Broncos',
            'NYG': 'New York Giants',
            'CP': 'Carolina Panthers',
            'AC': 'Arizona Cardinals',
            'IC': 'Indianapolis Colts',
            'NOS': 'New Orleans Saints',
            'PS': 'Pittsburgh Steelers',
            'LVR': 'Las Vegas Raiders',
            'TT': 'Tennessee Titans',
            'WC': 'Washington Commanders',
            'NEP': 'New England Patriots',
            'CIN': 'Cincinnati Bengals'
        }
    
    def _load_player_positions(self):
        """Load player position data from database"""
        try:
            from database.database_manager import DatabaseManager
            from database.database_models import PlayerPosition
            
            db_manager = DatabaseManager()
            
            with db_manager.get_session() as session:
                # Get all player positions from database
                positions = session.query(PlayerPosition).all()
                
                if positions:
                    for player_pos in positions:
                        self.player_positions[player_pos.cleaned_name] = player_pos.position
                    
                    print(f"✅ Loaded {len(self.player_positions)} player positions from database")
                else:
                    print(f"⚠️ No player positions found in database")
                    print(f"   Run: python3 scrape_player_positions_to_db.py")
                
        except Exception as e:
            print(f"⚠️ Could not load player positions from database: {e}")
            print(f"   Player positions may not be available")
    
    def get_player_position(self, player_name: str) -> Optional[str]:
        """
        Get the position for a given player name
        
        Args:
            player_name: Player name (will be cleaned before lookup)
            
        Returns:
            Position string (e.g., 'QB', 'RB', 'WR', 'TE') or None if not found
        """
        # Import here to avoid circular imports
        from utils import clean_player_name
        
        cleaned_name = clean_player_name(player_name)
        return self.player_positions.get(cleaned_name)
    
    def get_position_specific_stat(self, player_name: str, stat_type: str) -> Tuple[str, str]:
        """
        Get the position-specific defensive stat for a player and stat type
        
        Args:
            player_name: Player name
            stat_type: Stat type (e.g., 'Passing Yards', 'Receiving Yards')
            
        Returns:
            Tuple of (position, defensive_stat_type)
        """
        position = self.get_player_position(player_name)
        
        if position is None:
            # Use default mapping if position not found
            position = 'DEFAULT'
        
        # Get the position-specific stat mapping
        position_mapping = self.position_stat_mapping.get(position, self.position_stat_mapping['DEFAULT'])
        
        # Get the defensive stat type
        defensive_stat = position_mapping.get(stat_type)
        
        if defensive_stat is None:
            # Fallback to default mapping
            defensive_stat = self.position_stat_mapping['DEFAULT'].get(stat_type, f"{stat_type} Allowed")
        
        return position, defensive_stat
    
    def calculate_position_defensive_stats(self, max_week: int = None):
        """
        Calculate position-specific defensive stats from box score data
        
        Args:
            max_week: Maximum week to include in calculations (None = all weeks)
        """
        print("Calculating position-specific defensive stats from box score data...")
        
        # Reset stats
        self.position_defensive_stats = {}
        
        # Process each week's box score data
        for week_folder in os.listdir(self.data_dir):
            if not week_folder.startswith("WEEK"):
                continue
            
            # Extract week number
            try:
                week_num = int(week_folder.replace("WEEK", ""))
                if max_week is not None and week_num >= max_week:
                    continue
            except:
                continue
            
            box_score_path = os.path.join(self.data_dir, week_folder, "box_score_debug.csv")
            if not os.path.exists(box_score_path):
                print(f"No box score data for {week_folder}")
                continue
            
            print(f"Processing {week_folder}...")
            self._process_week_box_score(box_score_path)
        
        # Calculate rankings from the accumulated stats
        self._calculate_position_rankings()
        print(f"✅ Calculated position-specific defensive stats for {len(self.position_defensive_stats)} teams")
    
    def _process_week_box_score(self, box_score_path: str):
        """Process a single week's box score data"""
        try:
            # Get the week folder to find game data
            week_folder = os.path.dirname(box_score_path)
            game_data_dir = os.path.join(week_folder, "game_data")
            
            # Load game data to get team matchups
            team_matchups = self._load_week_game_data(game_data_dir)
            if not team_matchups:
                print(f"No game data found for {week_folder}")
                return
            
            print(f"  Found {len(team_matchups)} game matchups: {list(team_matchups.items())[:3]}")
            
            # Initialize games played counter for this week
            teams_in_this_week = set()
            for home_team, away_team in team_matchups.items():
                teams_in_this_week.add(home_team)
                teams_in_this_week.add(away_team)
            
            # Increment games played for each team in this week
            for team in teams_in_this_week:
                if team not in self.position_defensive_stats:
                    self.position_defensive_stats[team] = {'Games_Played': 0}
                self.position_defensive_stats[team]['Games_Played'] += 1
            
            df = pd.read_csv(box_score_path)
            print(f"  Processing {len(df)} players from box score")
            
            players_processed = 0
            players_with_position = 0
            
            for _, row in df.iterrows():
                player_name = row.get('Name', '')
                player_team = row.get('team', '')
                
                if not all([player_name, player_team]):
                    continue
                
                players_processed += 1
                
                # Get player position
                position = self.get_player_position(player_name)
                if position is None:
                    continue
                
                players_with_position += 1
                
                # Find opposing team
                # Normalize team names for comparison (game data uses underscores, box scores use spaces)
                player_team_normalized = player_team.replace(' ', '_')
                
                opposing_team = None
                for home_team, away_team in team_matchups.items():
                    if player_team_normalized == home_team:
                        opposing_team = away_team
                    elif player_team_normalized == away_team:
                        opposing_team = home_team
                
                # If multiple matches found, we need to be more specific
                # For now, we'll use the last match found (this may need refinement)
                
                if opposing_team is None:
                    # Debug: show first few unmatched teams
                    if players_with_position <= 5:
                        print(f"    No opposing team found for {player_name} ({player_team})")
                    continue
                
                # Initialize defensive stats for the opposing team (they are the defense)
                if opposing_team not in self.position_defensive_stats:
                    self.position_defensive_stats[opposing_team] = {'Games_Played': 0}
                
                # Process each stat type for this player
                stat_mappings = {
                    'pass_Yds': 'Passing Yards',
                    'pass_TD': 'Passing TDs',
                    'rush_Yds': 'Rushing Yards',
                    'rush_TD': 'Rushing TDs',
                    'rec_Rec': 'Receptions',
                    'rec_Yds': 'Receiving Yards',
                    'rec_TD': 'Receiving TDs'
                }
                
                for stat_column, stat_type in stat_mappings.items():
                    value = row.get(stat_column, 0)
                    if pd.isna(value):
                        value = 0
                    
                    # Create position-specific stat key
                    position_stat = f"{position}_{stat_type.replace(' ', '_')}_Allowed"
                    
                    # Add to team's defensive stats (include negative values for accurate totals)
                    if position_stat not in self.position_defensive_stats[opposing_team]:
                        self.position_defensive_stats[opposing_team][position_stat] = 0
                    
                    self.position_defensive_stats[opposing_team][position_stat] += value
            
            print(f"  Processed {players_processed} players, {players_with_position} with positions")
                
        except Exception as e:
            print(f"Error processing box score {box_score_path}: {e}")
    
    def _load_week_game_data(self, game_data_dir: str) -> Dict[str, str]:
        """Load game data to get team matchups for a week"""
        team_matchups = {}  # {home_team: away_team}
        
        if not os.path.exists(game_data_dir):
            return team_matchups
        
        try:
            for filename in os.listdir(game_data_dir):
                if not filename.endswith('_historical_odds.json'):
                    continue
                
                # Parse filename: {hash}_{AWAY_TEAM}_at_{HOME_TEAM}_historical_odds.json
                # Remove the hash prefix and _historical_odds.json suffix
                name_without_suffix = filename.replace('_historical_odds.json', '')
                parts = name_without_suffix.split('_at_')
                if len(parts) == 2:
                    # Remove the hash prefix from the first part
                    away_team_abbrev = parts[0].split('_', 1)[-1]  # Take everything after the first underscore
                    home_team_abbrev = parts[1]
                    
                    # Convert abbreviations to full team names
                    away_team = self._resolve_team_abbreviation(away_team_abbrev, game_data_dir, filename)
                    home_team = self._resolve_team_abbreviation(home_team_abbrev, game_data_dir, filename)
                    
                    if away_team and home_team:
                        team_matchups[home_team] = away_team
                    
        except Exception as e:
            print(f"Error loading game data from {game_data_dir}: {e}")
        
        return team_matchups
    
    def _resolve_team_abbreviation(self, abbrev, game_data_dir, filename=None):
        """Resolve team abbreviation to full team name, handling conflicts like CB"""
        # Handle normal mappings first
        if abbrev != 'CB':
            return self.game_abbrev_to_full_name.get(abbrev, abbrev)
        
        # Special handling for CB conflict (Chicago Bears, Cleveland Browns, Cincinnati Bengals)
        # Use game context to determine which specific CB team is playing
        try:
            if not filename:
                return None
                
            # Get the week folder from game_data_dir
            week_folder = os.path.dirname(game_data_dir)
            box_score_path = os.path.join(week_folder, "box_score_debug.csv")
            
            if not os.path.exists(box_score_path):
                return None
            
            # Parse the filename to understand the specific game context
            # Format: {hash}_{AWAY_TEAM}_at_{HOME_TEAM}_historical_odds.json
            name_without_suffix = filename.replace('_historical_odds.json', '')
            parts = name_without_suffix.split('_at_')
            if len(parts) != 2:
                return None
                
            away_team_abbrev = parts[0].split('_', 1)[-1]
            home_team_abbrev = parts[1]
            
            # Determine which team is CB and which is the opponent
            cb_is_away = (away_team_abbrev == 'CB')
            cb_is_home = (home_team_abbrev == 'CB')
            
            if not (cb_is_away or cb_is_home):
                return None
                
            # Get the opponent team name to help identify the correct CB team
            opponent_abbrev = home_team_abbrev if cb_is_away else away_team_abbrev
            opponent_name = self.game_abbrev_to_full_name.get(opponent_abbrev, opponent_abbrev)
            
            # Read the JSON file directly to get the exact team names
            json_file_path = os.path.join(game_data_dir, filename)
            if not os.path.exists(json_file_path):
                print(f"Warning: JSON file not found: {json_file_path}")
                return None
            
            try:
                import json
                with open(json_file_path, 'r') as f:
                    game_data = json.load(f)
                
                # Get the team names from the JSON
                home_team = game_data.get('data', {}).get('home_team', '')
                away_team = game_data.get('data', {}).get('away_team', '')
                
                # Determine which team is CB based on the filename
                if cb_is_away:
                    # CB is the away team, so return away_team
                    return away_team
                elif cb_is_home:
                    # CB is the home team, so return home_team
                    return home_team
                else:
                    return None
                    
            except Exception as e:
                print(f"Error reading JSON file {filename}: {e}")
                return None
                
        except Exception as e:
            print(f"Error resolving CB abbreviation: {e}")
            return None
    
    def _calculate_position_rankings(self):
        """Calculate rankings for each position-specific stat"""
        self.position_defensive_rankings = {}
        
        # Get all unique position stats across all teams
        all_position_stats = set()
        for team_stats in self.position_defensive_stats.values():
            all_position_stats.update(team_stats.keys())
        
        # Calculate rankings for each position stat (per-game basis)
        for position_stat in all_position_stats:
            team_values = {}
            
            for team, stats in self.position_defensive_stats.items():
                if position_stat in stats:
                    total_yards = stats[position_stat]
                    games_played = stats.get('Games_Played', 1)  # Default to 1 to avoid division by zero
                    per_game_yards = total_yards / games_played
                    team_values[team] = per_game_yards
            
            if not team_values:
                continue
            
            # Sort teams by value (lower values = better defense = lower rank)
            # For yards allowed: lower is better (rank 1 = best defense)
            # For TDs allowed: lower is better (rank 1 = best defense)
            sorted_teams = sorted(team_values.items(), key=lambda x: x[1], reverse=False)
            
            # Create ranking (1 = best defense, higher number = worse defense)
            rankings = {}
            for rank, (team, value) in enumerate(sorted_teams, 1):
                rankings[team] = rank
            
            self.position_defensive_rankings[position_stat] = rankings
    
    def get_position_defensive_rank(self, team: str, player_name: str, stat_type: str) -> Optional[int]:
        """
        Get position-specific defensive ranking for a team against a player's stat type
        
        Args:
            team: Opposing team name
            player_name: Player name
            stat_type: Stat type (e.g., 'Receiving Yards')
            
        Returns:
            Defensive ranking (1 = best defense, higher = worse defense) or None
        """
        # Get player position
        position = self.get_player_position(player_name)
        if position is None:
            return None
        
        # Create position-specific stat key
        position_stat = f"{position}_{stat_type.replace(' ', '_')}_Allowed"
        
        # Normalize team name (rankings use underscores, inputs may have spaces)
        team_normalized = team.replace(' ', '_')
        
        # Get ranking
        if position_stat in self.position_defensive_rankings:
            return self.position_defensive_rankings[position_stat].get(team_normalized)
        
        return None
    
    def get_position_stat_mapping_info(self) -> Dict:
        """Get information about the position-stat mapping for debugging"""
        return {
            'player_count': len(self.player_positions),
            'position_mapping': self.position_stat_mapping,
            'sample_players': dict(list(self.player_positions.items())[:10])
        }

def test_position_rankings():
    """Test function to verify the position rankings system"""
    pos_ranks = PositionDefensiveRankings()
    
    print("=== Position Defensive Rankings Test ===")
    
    # Test basic position lookup
    test_players = [
        "Josh Allen",
        "Christian McCaffrey", 
        "Davante Adams",
        "Travis Kelce",
        "Unknown Player"
    ]
    
    for player in test_players:
        position = pos_ranks.get_player_position(player)
        print(f"Player: {player}")
        print(f"  Position: {position}")
        
        if position:
            # Test a few stat types
            for stat_type in ['Passing Yards', 'Rushing Yards', 'Receiving Yards']:
                pos, def_stat = pos_ranks.get_position_specific_stat(player, stat_type)
                print(f"  {stat_type} → {pos}: {def_stat}")
        print()
    
    # Test position-specific defensive stats calculation
    print("=== Calculating Position-Specific Defensive Stats ===")
    pos_ranks.calculate_position_defensive_stats(max_week=6)  # Use first 6 weeks
    
    # Show some sample rankings
    print("\n=== Sample Position-Specific Rankings ===")
    for position_stat, rankings in pos_ranks.position_defensive_rankings.items():
        print(f"\n{position_stat}:")
        # Show top 5 (worst defenses)
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])[:5]
        for team, rank in sorted_rankings:
            print(f"  {team}: {rank}")
        if len(sorted_rankings) == 0:
            print("  No data available")
    
    # Test getting position-specific defensive rank
    print("\n=== Testing Position-Specific Defensive Rank Lookup ===")
    test_cases = [
        ("Josh Allen", "Passing Yards", "Miami Dolphins"),
        ("Christian McCaffrey", "Receiving Yards", "Seattle Seahawks"),
        ("Davante Adams", "Receiving Yards", "Arizona Cardinals"),
    ]
    
    for player, stat_type, opposing_team in test_cases:
        rank = pos_ranks.get_position_defensive_rank(opposing_team, player, stat_type)
        print(f"{player} ({pos_ranks.get_player_position(player)}) {stat_type} vs {opposing_team}: Rank {rank}")

if __name__ == "__main__":
    test_position_rankings()
