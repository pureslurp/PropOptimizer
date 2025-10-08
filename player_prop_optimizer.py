"""
NFL Player Prop Optimizer
A Streamlit application for analyzing NFL player props using matchup data and player history.
"""

import streamlit as st
import pandas as pd
import requests
import os
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime, timedelta
import time

# Import our custom modules
from enhanced_data_processor import EnhancedFootballDataProcessor
from scoring_model import AdvancedPropScorer
from utils import clean_player_name, format_odds, format_line
from config import ODDS_API_KEY, STAT_TYPES, CONFIDENCE_LEVELS, DEFAULT_MIN_SCORE, PREFERRED_BOOKMAKER

# Set page config
st.set_page_config(
    page_title="NFL Player Prop Optimizer",
    page_icon="🏈",
    layout="wide"
)

# API Configuration is now in config.py

class OddsAPI:
    """Handle interactions with The Odds API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.player_teams = {}  # Cache for player team assignments
        
        # Map team abbreviations to full names (as used by Odds API)
        self.team_name_mapping = {
            'PHI': 'Philadelphia Eagles',
            'NYG': 'New York Giants',
            'DAL': 'Dallas Cowboys',
            'WAS': 'Washington Commanders',
            'SF': 'San Francisco 49ers',
            'SEA': 'Seattle Seahawks',
            'LAR': 'Los Angeles Rams',
            'ARI': 'Arizona Cardinals',
            'GB': 'Green Bay Packers',
            'MIN': 'Minnesota Vikings',
            'DET': 'Detroit Lions',
            'CHI': 'Chicago Bears',
            'TB': 'Tampa Bay Buccaneers',
            'NO': 'New Orleans Saints',
            'ATL': 'Atlanta Falcons',
            'CAR': 'Carolina Panthers',
            'KC': 'Kansas City Chiefs',
            'LV': 'Las Vegas Raiders',
            'LAC': 'Los Angeles Chargers',
            'DEN': 'Denver Broncos',
            'BUF': 'Buffalo Bills',
            'MIA': 'Miami Dolphins',
            'NE': 'New England Patriots',
            'NYJ': 'New York Jets',
            'BAL': 'Baltimore Ravens',
            'CIN': 'Cincinnati Bengals',
            'CLE': 'Cleveland Browns',
            'PIT': 'Pittsburgh Steelers',
            'HOU': 'Houston Texans',
            'IND': 'Indianapolis Colts',
            'JAX': 'Jacksonville Jaguars',
            'TEN': 'Tennessee Titans'
        }
        
    def get_player_props(self, sport: str = "americanfootball_nfl") -> List[Dict]:
        """Fetch player props from The Odds API using the event-based approach"""
        try:
            # Step 1: Get events first
            events_url = f"{self.base_url}/sports/{sport}/events"
            events_params = {
                'apiKey': self.api_key,
                'regions': 'us'
            }
            
            events_response = requests.get(events_url, params=events_params, timeout=30)
            events_response.raise_for_status()
            events = events_response.json()
            
            if not events:
                st.warning("No NFL events found. Using demonstration data.")
                return self._get_mock_player_props()
            
            # Step 2: Get odds for each event with player props (only games with player props)
            all_games = []
            # Request all available player prop markets
            player_markets = [
                'player_pass_yds', 
                'player_pass_tds',
                'player_rush_yds',
                'player_rush_tds',
                'player_receptions',
                'player_reception_yds',
                'player_reception_tds'
            ]
            games_with_props = 0
            
            for i, event in enumerate(events[:15]):  # Check more events to find ones with player props
                try:
                    event_id = event.get('id')
                    if not event_id:
                        continue
                    
                    odds_url = f"{self.base_url}/sports/{sport}/events/{event_id}/odds"
                    odds_params = {
                        'apiKey': self.api_key,
                        'regions': 'us',
                        'bookmakers': 'fanduel',
                        'markets': ','.join(player_markets),
                        'oddsFormat': 'american'
                    }
                    
                    odds_response = requests.get(odds_url, params=odds_params, timeout=30)
                    
                    if odds_response.status_code == 200:
                        event_data = odds_response.json()
                        # Check if this game actually has player props
                        has_player_props = False
                        for bookmaker in event_data.get('bookmakers', []):
                            if bookmaker.get('key') == 'fanduel':
                                for market in bookmaker.get('markets', []):
                                    if market.get('key') in player_markets and market.get('outcomes'):
                                        has_player_props = True
                                        break
                                break
                        
                        if has_player_props:
                            all_games.append(event_data)
                            games_with_props += 1
                            
                            # Stop after finding enough games with player props
                            if games_with_props >= 5:
                                break
                    
                    # Rate limiting
                    import time
                    time.sleep(0.3)
                    
                except Exception as e:
                    continue
            
            if not all_games:
                st.warning("No player props data found. Using demonstration data.")
                return self._get_mock_player_props()
            
            return all_games
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching odds data: {e}")
            st.info("Using demonstration data instead.")
            return self._get_mock_player_props()
    
    def _get_mock_player_props(self) -> List[Dict]:
        """Return mock player props data for demonstration"""
        return [
            {
                'id': 'mock_game_1',
                'sport_key': 'americanfootball_nfl',
                'commence_time': '2024-01-15T20:00:00Z',
                'home_team': 'Buffalo Bills',
                'away_team': 'Kansas City Chiefs',
                'bookmakers': [
                    {
                        'key': 'fanduel',
                        'title': 'FanDuel',
                        'last_update': '2024-01-15T18:00:00Z',
                        'markets': [
                            {
                                'key': 'player_pass_yds',
                                'outcomes': [
                                    {'name': 'Josh Allen', 'point': 275.5, 'price': -110},
                                    {'name': 'Josh Allen', 'point': 300.5, 'price': -120},
                                    {'name': 'Patrick Mahomes', 'point': 280.5, 'price': -105},
                                    {'name': 'Patrick Mahomes', 'point': 305.5, 'price': -115}
                                ]
                            },
                            {
                                'key': 'player_rush_yds',
                                'outcomes': [
                                    {'name': 'Josh Allen', 'point': 45.5, 'price': -110},
                                    {'name': 'Josh Allen', 'point': 55.5, 'price': -120},
                                    {'name': 'Isiah Pacheco', 'point': 65.5, 'price': -105},
                                    {'name': 'Isiah Pacheco', 'point': 75.5, 'price': -115}
                                ]
                            },
                            {
                                'key': 'player_rec',
                                'outcomes': [
                                    {'name': 'Stefon Diggs', 'point': 6.5, 'price': -110},
                                    {'name': 'Stefon Diggs', 'point': 7.5, 'price': -120},
                                    {'name': 'Travis Kelce', 'point': 6.5, 'price': -105},
                                    {'name': 'Travis Kelce', 'point': 7.5, 'price': -115}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'id': 'mock_game_2',
                'sport_key': 'americanfootball_nfl',
                'commence_time': '2024-01-15T17:00:00Z',
                'home_team': 'San Francisco 49ers',
                'away_team': 'Dallas Cowboys',
                'bookmakers': [
                    {
                        'key': 'fanduel',
                        'title': 'FanDuel',
                        'last_update': '2024-01-15T18:00:00Z',
                        'markets': [
                            {
                                'key': 'player_rush_yds',
                                'outcomes': [
                                    {'name': 'Christian McCaffrey', 'point': 95.5, 'price': -110},
                                    {'name': 'Christian McCaffrey', 'point': 110.5, 'price': -120},
                                    {'name': 'Tony Pollard', 'point': 75.5, 'price': -105},
                                    {'name': 'Tony Pollard', 'point': 85.5, 'price': -115}
                                ]
                            },
                            {
                                'key': 'player_rec_yds',
                                'outcomes': [
                                    {'name': 'Deebo Samuel', 'point': 65.5, 'price': -110},
                                    {'name': 'Deebo Samuel', 'point': 75.5, 'price': -120},
                                    {'name': 'CeeDee Lamb', 'point': 85.5, 'price': -105},
                                    {'name': 'CeeDee Lamb', 'point': 95.5, 'price': -115}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    
    def parse_player_props(self, odds_data: List[Dict]) -> pd.DataFrame:
        """Parse odds data into a structured DataFrame, prioritizing FanDuel"""
        props = []
        
        for game in odds_data:
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            # Prioritize FanDuel bookmaker
            fanduel_bookmaker = None
            other_bookmakers = []
            
            for bookmaker in game.get('bookmakers', []):
                if bookmaker.get('key', '').lower() == 'fanduel':
                    fanduel_bookmaker = bookmaker
                else:
                    other_bookmakers.append(bookmaker)
            
            # Use FanDuel first, then fall back to others
            bookmakers_to_process = [fanduel_bookmaker] if fanduel_bookmaker else other_bookmakers
            
            for bookmaker in bookmakers_to_process:
                if not bookmaker:
                    continue
                    
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key', '')
                    
                    # Map market keys to our stat types (updated for correct API format)
                    stat_mapping = {
                        'player_pass_yds': 'Passing Yards',
                        'player_pass_tds': 'Passing TDs',
                        'player_rush_yds': 'Rushing Yards', 
                        'player_rush_tds': 'Rushing TDs',
                        'player_receptions': 'Receptions',
                        'player_reception_yds': 'Receiving Yards',
                        'player_reception_tds': 'Receiving TDs'  # Fixed: was player_rec_tds
                    }
                    
                    stat_type = stat_mapping.get(market_key, market_key)
                    
                    for outcome in market.get('outcomes', []):
                        # Handle the new API format where player names are in description for "Over" outcomes
                        if outcome.get('name') == 'Over' and outcome.get('description'):
                            player_name = outcome.get('description', '').strip()
                            line = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            # Determine team using actual data (will be updated later with data processor)
                            team = "Unknown"  # Will be determined by data processor
                            opposing_team = "Unknown"  # Will be determined by data processor
                            
                            props.append({
                                'Player': player_name,
                                'Team': team,
                                'Opposing Team': opposing_team,
                                'Stat Type': stat_type,
                                'Line': line,
                                'Odds': odds,
                                'Bookmaker': bookmaker.get('title', ''),
                                'Market': market_key,
                                'Home Team': home_team,
                                'Away Team': away_team
                            })
                        elif outcome.get('name') and outcome.get('name') not in ['Over', 'Under']:
                            # Handle other outcome types if needed (but skip Over/Under)
                            player_name = outcome.get('name', '')
                            line = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            # Determine team using actual data (will be updated later with data processor)
                            team = "Unknown"  # Will be determined by data processor
                            opposing_team = "Unknown"  # Will be determined by data processor
                            
                            props.append({
                                'Player': player_name,
                                'Team': team,
                                'Opposing Team': opposing_team,
                                'Stat Type': stat_type,
                                'Line': line,
                                'Odds': odds,
                                'Bookmaker': bookmaker.get('title', ''),
                                'Market': market_key,
                                'Home Team': home_team,
                                'Away Team': away_team
                            })
        
        return pd.DataFrame(props)
    
    def update_team_assignments(self, props_df: pd.DataFrame, data_processor) -> pd.DataFrame:
        """Update team assignments using actual player data"""
        if props_df.empty:
            return props_df
        
        updated_props = []
        for _, row in props_df.iterrows():
            player_name = row['Player']
            
            # Get player's actual team from our data
            player_team = self.get_player_team_from_data(player_name, data_processor)
            
            # Get opposing team from odds API game context
            opposing_team = "Unknown"
            if player_team != "Unknown" and 'Home Team' in row and 'Away Team' in row:
                home_team = row['Home Team']
                away_team = row['Away Team']
                # Determine opposing team based on which team the player is on
                if player_team == home_team:
                    opposing_team = away_team
                elif player_team == away_team:
                    opposing_team = home_team
            
            # Update the row
            updated_row = row.copy()
            updated_row['Team'] = player_team
            updated_row['Opposing Team'] = opposing_team
            updated_props.append(updated_row)
        
        return pd.DataFrame(updated_props)
    
    def get_player_team_from_data(self, player_name: str, data_processor) -> str:
        """Get player's actual team from our data"""
        try:
            # Clean the player name to match our data format
            from utils import clean_player_name
            cleaned_name = clean_player_name(player_name)
            
            team = "Unknown"
            
            # Try to get team from data processor
            if hasattr(data_processor, 'get_player_team'):
                team = data_processor.get_player_team(cleaned_name)
                if team == "Unknown":
                    # Try case-insensitive matching with name cleaning on both sides
                    if hasattr(data_processor, 'player_season_stats'):
                        for stored_player, stats in data_processor.player_season_stats.items():
                            # Clean both names for comparison
                            cleaned_stored = clean_player_name(stored_player)
                            if cleaned_stored.lower() == cleaned_name.lower():
                                team = stats.get('team', 'Unknown')
                                break
            
            # Normalize team name from abbreviation to full name
            if team != "Unknown" and team in self.team_name_mapping:
                team = self.team_name_mapping[team]
            
            return team
        except Exception as e:
            print(f"ERROR in get_player_team_from_data for {player_name}: {e}")
            return "Unknown"

class DataProcessor:
    """Process matchup and player history data"""
    
    def __init__(self):
        self.team_stats = {}
        self.player_stats = {}
    
    def load_team_defensive_stats(self) -> Dict:
        """Load team defensive statistics (mock data for now)"""
        # This would typically load from your data source
        # For now, using mock data based on common NFL defensive rankings
        return {
            'Passing Yards Allowed': {
                'Arizona Cardinals': 250,
                'Atlanta Falcons': 240,
                'Baltimore Ravens': 220,
                'Buffalo Bills': 210,
                'Carolina Panthers': 230,
                'Chicago Bears': 245,
                'Cincinnati Bengals': 235,
                'Cleveland Browns': 225,
                'Dallas Cowboys': 215,
                'Denver Broncos': 255,
                'Detroit Lions': 245,
                'Green Bay Packers': 230,
                'Houston Texans': 250,
                'Indianapolis Colts': 240,
                'Jacksonville Jaguars': 245,
                'Kansas City Chiefs': 235,
                'Las Vegas Raiders': 250,
                'Los Angeles Chargers': 245,
                'Los Angeles Rams': 230,
                'Miami Dolphins': 240,
                'Minnesota Vikings': 235,
                'New England Patriots': 220,
                'New Orleans Saints': 225,
                'New York Giants': 250,
                'New York Jets': 215,
                'Philadelphia Eagles': 230,
                'Pittsburgh Steelers': 220,
                'San Francisco 49ers': 210,
                'Seattle Seahawks': 245,
                'Tampa Bay Buccaneers': 235,
                'Tennessee Titans': 240,
                'Washington Commanders': 250
            },
            'Rushing Yards Allowed': {
                'Arizona Cardinals': 120,
                'Atlanta Falcons': 115,
                'Baltimore Ravens': 100,
                'Buffalo Bills': 95,
                'Carolina Panthers': 110,
                'Chicago Bears': 125,
                'Cincinnati Bengals': 105,
                'Cleveland Browns': 100,
                'Dallas Cowboys': 110,
                'Denver Broncos': 130,
                'Detroit Lions': 120,
                'Green Bay Packers': 115,
                'Houston Texans': 125,
                'Indianapolis Colts': 110,
                'Jacksonville Jaguars': 120,
                'Kansas City Chiefs': 115,
                'Las Vegas Raiders': 125,
                'Los Angeles Chargers': 120,
                'Los Angeles Rams': 110,
                'Miami Dolphins': 115,
                'Minnesota Vikings': 120,
                'New England Patriots': 105,
                'New Orleans Saints': 110,
                'New York Giants': 130,
                'New York Jets': 100,
                'Philadelphia Eagles': 115,
                'Pittsburgh Steelers': 105,
                'San Francisco 49ers': 95,
                'Seattle Seahawks': 125,
                'Tampa Bay Buccaneers': 115,
                'Tennessee Titans': 120,
                'Washington Commanders': 130
            },
            'Receiving Yards Allowed': {
                'Arizona Cardinals': 250,
                'Atlanta Falcons': 240,
                'Baltimore Ravens': 220,
                'Buffalo Bills': 210,
                'Carolina Panthers': 230,
                'Chicago Bears': 245,
                'Cincinnati Bengals': 235,
                'Cleveland Browns': 225,
                'Dallas Cowboys': 215,
                'Denver Broncos': 255,
                'Detroit Lions': 245,
                'Green Bay Packers': 230,
                'Houston Texans': 250,
                'Indianapolis Colts': 240,
                'Jacksonville Jaguars': 245,
                'Kansas City Chiefs': 235,
                'Las Vegas Raiders': 250,
                'Los Angeles Chargers': 245,
                'Los Angeles Rams': 230,
                'Miami Dolphins': 240,
                'Minnesota Vikings': 235,
                'New England Patriots': 220,
                'New Orleans Saints': 225,
                'New York Giants': 250,
                'New York Jets': 215,
                'Philadelphia Eagles': 230,
                'Pittsburgh Steelers': 220,
                'San Francisco 49ers': 210,
                'Seattle Seahawks': 245,
                'Tampa Bay Buccaneers': 235,
                'Tennessee Titans': 240,
                'Washington Commanders': 250
            }
        }
    
    def load_player_season_stats(self) -> Dict:
        """Load player season statistics (mock data for now)"""
        # This would typically load from your data source
        return {
            'Josh Allen': {
                'Passing Yards': [280, 320, 250, 310, 290],
                'Passing TDs': [2, 3, 1, 4, 2],
                'Rushing Yards': [45, 60, 35, 55, 40],
                'Rushing TDs': [1, 1, 0, 2, 1]
            },
            'Lamar Jackson': {
                'Passing Yards': [250, 280, 220, 300, 260],
                'Passing TDs': [2, 2, 1, 3, 2],
                'Rushing Yards': [80, 95, 70, 85, 75],
                'Rushing TDs': [1, 2, 1, 1, 1]
            },
            'Christian McCaffrey': {
                'Rushing Yards': [120, 95, 110, 85, 100],
                'Rushing TDs': [1, 1, 2, 0, 1],
                'Receptions': [5, 3, 6, 4, 5],
                'Receiving Yards': [45, 25, 60, 35, 50]
            },
            'Cooper Kupp': {
                'Receptions': [8, 6, 9, 7, 8],
                'Receiving Yards': [120, 85, 140, 95, 110],
                'Receiving TDs': [1, 0, 2, 1, 1]
            }
        }
    
    def get_team_rank(self, team: str, stat_type: str) -> int:
        """Get team defensive ranking for a specific stat"""
        team_stats = self.load_team_defensive_stats()
        
        if stat_type not in team_stats:
            return 16  # Default middle ranking
        
        # Get all teams and their stats for this category
        all_teams = [(team_name, stats) for team_name, stats in team_stats[stat_type].items()]
        all_teams.sort(key=lambda x: x[1])  # Sort by yards allowed (ascending = better defense)
        
        # Find the rank of the specified team
        for i, (team_name, _) in enumerate(all_teams, 1):
            if team_name == team:
                return i
        
        return 16  # Default middle ranking if team not found
    
    def get_player_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line this season"""
        player_stats = self.load_player_season_stats()
        
        if player not in player_stats or stat_type not in player_stats[player]:
            return 0.5  # Default 50% if no data
        
        games = player_stats[player][stat_type]
        over_count = sum(1 for game_stat in games if game_stat > line)
        
        return over_count / len(games) if games else 0.5


class PropScorer:
    """Calculate scores for player props based on matchup and player history"""
    
    def __init__(self, data_processor: DataProcessor):
        self.data_processor = data_processor
    
    def calculate_score(self, player: str, opposing_team: str, stat_type: str, line: float) -> int:
        """Calculate a score for a player prop"""
        # Get team defensive ranking (lower is better defense)
        # Map stat types to defensive rankings
        defense_stat_type = f"{stat_type} Allowed"
        if stat_type == "Receiving Yards":
            defense_stat_type = "Passing Yards Allowed"
        elif stat_type == "Receiving TDs":
            defense_stat_type = "Passing TDs Allowed"
        
        team_rank = self.data_processor.get_team_rank(opposing_team, defense_stat_type)
        
        # Get player's over rate for this line
        over_rate = self.data_processor.get_player_over_rate(player, stat_type, line)
        
        # Calculate base score from team ranking (inverted - better defense = lower score)
        team_score = max(0, 32 - team_rank) * 2  # Scale to 0-64
        
        # Calculate player score from over rate
        player_score = over_rate * 40  # Scale to 0-40
        
        # Combine scores (team defense + player history)
        total_score = int(team_score + player_score)
        
        return min(100, max(0, total_score))  # Clamp between 0-100


class AlternateLineManager:
    """Manage alternate lines from The Odds API - fetches in real-time"""
    
    def __init__(self, api_key: str, odds_data: List[Dict] = None):
        """
        Initialize AlternateLineManager
        
        Args:
            api_key: The Odds API key
            odds_data: Optional pre-fetched odds data (list of events from main odds fetch)
        """
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.alternate_lines = {}
        self.odds_data = odds_data or []
        
        # Map stat types to alternate market names
        self.stat_market_mapping = {
            'Passing Yards': 'player_pass_yds_alternate',
            'Rushing Yards': 'player_rush_yds_alternate',
            'Receiving Yards': 'player_reception_yds_alternate',
            'Receptions': 'player_receptions_alternate',
            'Passing TDs': 'player_pass_tds_alternate',
            'Rushing TDs': 'player_rush_tds_alternate',
            'Receiving TDs': 'player_reception_tds_alternate'  # Fixed: was player_rec_tds_alternate
        }
    
    def fetch_alternate_lines_for_stat(self, stat_type: str, bookmaker: str = 'fanduel', progress_callback=None) -> Dict:
        """
        Fetch alternate lines for a specific stat type in real-time
        
        Args:
            stat_type: The stat type (e.g., 'Passing Yards')
            bookmaker: The bookmaker to use (default: 'fanduel')
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dict mapping player names to their alternate lines
        """
        market_key = self.stat_market_mapping.get(stat_type)
        if not market_key:
            return {}
        
        # Get event IDs from the odds data
        event_ids = [event.get('id') for event in self.odds_data if event.get('id')]
        if not event_ids:
            return {}
        
        parsed_lines = {}
        total_events = len(event_ids)
        
        # Fetch alternate lines for each event
        for idx, event_id in enumerate(event_ids, 1):
            if progress_callback:
                progress_callback(f"Fetching alternate lines for {stat_type}... ({idx}/{total_events})")
            
            try:
                odds_url = f"{self.base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
                odds_params = {
                    'apiKey': self.api_key,
                    'regions': 'us',
                    'bookmakers': bookmaker,
                    'markets': market_key,
                    'oddsFormat': 'american',
                    'includeAltLines': 'true'
                }
                
                response = requests.get(odds_url, params=odds_params, timeout=30)
                
                if response.status_code == 200:
                    event_data = response.json()
                    
                    # Parse the alternate lines from this event
                    for bookmaker_data in event_data.get('bookmakers', []):
                        if bookmaker_data.get('key') == bookmaker:
                            for market in bookmaker_data.get('markets', []):
                                if market.get('key') == market_key:
                                    for outcome in market.get('outcomes', []):
                                        if outcome.get('name') == 'Over':
                                            player_name = outcome.get('description', '')
                                            if player_name:
                                                if player_name not in parsed_lines:
                                                    parsed_lines[player_name] = []
                                                
                                                parsed_lines[player_name].append({
                                                    'line': outcome.get('point', 0),
                                                    'odds': outcome.get('price', 0)
                                                })
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                # Continue to next event on error
                continue
        
        # Sort lines by point value for each player
        for player in parsed_lines:
            parsed_lines[player] = sorted(parsed_lines[player], key=lambda x: x['line'])
        
        return parsed_lines
    
    def get_closest_alternate_line(self, player: str, stat_type: str, target_line: float) -> Optional[Dict]:
        """
        Find the closest alternate line to a target threshold
        
        Args:
            player: Player name
            stat_type: Stat type (e.g., 'Passing Yards')
            target_line: Target line to find closest match to
            
        Returns:
            Dict with 'line' and 'odds' or None if not found
        """
        # Get alternate lines for this stat type (should already be cached)
        if stat_type not in self.alternate_lines:
            return None
        
        player_lines = self.alternate_lines[stat_type].get(player, [])
        if not player_lines:
            return None
        
        # Find the closest line
        closest_line = min(player_lines, key=lambda x: abs(x['line'] - target_line))
        return closest_line


def calculate_70_percent_threshold(player_stats: List[float]) -> Tuple[float, float]:
    """
    Calculate the threshold at which a player's over rate is closest to 70%
    
    Args:
        player_stats: List of player's game stats
        
    Returns:
        Tuple of (threshold, actual_over_rate)
    """
    if not player_stats or len(player_stats) == 0:
        return (0.0, 0.0)
    
    # Sort the stats
    sorted_stats = sorted(player_stats)
    n = len(sorted_stats)
    
    # Target is 70% over rate
    target_rate = 0.70
    
    best_threshold = 0.0
    best_rate = 0.0
    best_diff = float('inf')
    
    # Check thresholds between consecutive games (e.g., 226.5 is between 226 and 280)
    # This is more realistic for betting lines
    for i in range(n):
        # Set threshold at mid-point between consecutive values
        if i < n - 1:
            threshold = (sorted_stats[i] + sorted_stats[i + 1]) / 2
        else:
            # For the highest value, add 0.5
            threshold = sorted_stats[i] + 0.5
        
        over_count = sum(1 for stat in player_stats if stat > threshold)
        over_rate = over_count / n
        diff = abs(over_rate - target_rate)
        
        # If there's a tie in difference, prefer the higher threshold (lower over rate)
        if diff < best_diff or (diff == best_diff and over_rate < best_rate):
            best_diff = diff
            best_threshold = threshold
            best_rate = over_rate
    
    # Also check a threshold just below the lowest value
    threshold = sorted_stats[0] - 0.5
    over_count = sum(1 for stat in player_stats if stat > threshold)
    over_rate = over_count / n
    diff = abs(over_rate - target_rate)
    
    if diff < best_diff or (diff == best_diff and over_rate < best_rate):
        best_diff = diff
        best_threshold = threshold
        best_rate = over_rate
    
    # Round to .5 for cleaner display
    int_part = int(best_threshold)
    decimal_part = best_threshold - int_part
    
    if decimal_part < 0.25:
        best_threshold = int_part + 0.5
    elif decimal_part < 0.75:
        best_threshold = int_part + 0.5
    else:
        best_threshold = int_part + 1.5
    
    # Recalculate the over rate with the rounded threshold
    over_count = sum(1 for stat in player_stats if stat > best_threshold)
    best_rate = over_count / n
    
    return (best_threshold, best_rate)

def main():
    """Main Streamlit application"""
    st.title("🏈 NFL Player Prop Optimizer")
    st.markdown("Analyze NFL player props using matchup data and player history")
    
    # Check if API key is configured
    if ODDS_API_KEY == "YOUR_API_KEY_HERE":
        st.error("⚠️ API Key not configured!")
        st.markdown("""
        **To use this application:**
        1. Get your free API key from [The Odds API](https://the-odds-api.com/)
        2. Replace `YOUR_API_KEY_HERE` in the code with your actual API key
        3. Restart the application
        """)
        st.stop()
    
    # Initialize components
    odds_api = OddsAPI(ODDS_API_KEY)
    data_processor = EnhancedFootballDataProcessor()
    scorer = AdvancedPropScorer(data_processor)
    
    # Stat type selector at the top
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_stat = st.selectbox(
            "Select Stat Type",
            STAT_TYPES,
            index=0
        )
    
    with col2:
        if st.button("🔄 Refresh", type="primary"):
            # Clear all cached data on refresh
            if 'alt_line_manager' in st.session_state:
                del st.session_state.alt_line_manager
            if 'props_df_cache' in st.session_state:
                del st.session_state.props_df_cache
            if 'odds_data_cache' in st.session_state:
                del st.session_state.odds_data_cache
            st.rerun()
    
    st.subheader(f"Player Props - {selected_stat}")
    st.caption(f"📊 Odds from {PREFERRED_BOOKMAKER} (prioritized)")
    
    # Fetch and display data
    try:
        # Check if we have cached data
        if 'props_df_cache' in st.session_state and 'odds_data_cache' in st.session_state:
            # Use cached data
            props_df = st.session_state.props_df_cache
            odds_data = st.session_state.odds_data_cache
            st.info(f"ℹ️ Using cached props data ({len(props_df)} props from {len(odds_data)} games)")
        else:
            # Fetch fresh data
            with st.spinner("Fetching player props data..."):
                odds_data = odds_api.get_player_props()
            
            if not odds_data:
                st.error("No odds data available. Please check your API key and try again.")
                st.stop()
            
            # Check if we're using mock data
            if any('mock_game' in str(game.get('id', '')) for game in odds_data):
                st.info("📊 Using demonstration data")
                with st.expander("ℹ️ About Player Props API Access"):
                    st.markdown("""
                    **Player props require a paid API plan:**
                    - Free plan: 500 requests/month, basic markets only
                    - Paid plans: Player props, historical data, and more
                    
                    **To get real player props data:**
                    1. Upgrade your plan at [The Odds API](https://the-odds-api.com/)
                    2. Player props are available on 20K+ plans
                    3. Your current API key works for demonstration purposes
                    
                    **Current features:**
                    - ✅ Advanced scoring model
                    - ✅ Matchup analysis  
                    - ✅ Player history tracking
                    - ✅ Interactive dashboard
                    """)
            
            # Parse the data
            with st.spinner("Processing player props data..."):
                props_df = odds_api.parse_player_props(odds_data)
            
            if props_df.empty:
                st.warning("No player props found for the selected criteria.")
                st.stop()
            
            # Update team assignments using actual player data
            with st.spinner("Updating team assignments..."):
                props_df = odds_api.update_team_assignments(props_df, data_processor)
            
            # Cache the data
            st.session_state.props_df_cache = props_df
            st.session_state.odds_data_cache = odds_data
            
            # Show success message once
            st.success(f"✅ Loaded {len(props_df)} player props from {len(odds_data)} games")
        
        # Initialize or retrieve alternate line manager from session state
        if 'alt_line_manager' not in st.session_state:
            st.session_state.alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
        else:
            # Update odds_data in case events changed
            st.session_state.alt_line_manager.odds_data = odds_data
        
        alt_line_manager = st.session_state.alt_line_manager
        
        # Filter by selected stat type
        filtered_df = props_df[props_df['Stat Type'] == selected_stat].copy()
        
        if filtered_df.empty:
            st.warning(f"No {selected_stat} props found.")
            st.stop()
        
        # Pre-fetch alternate lines for the selected stat type (only if not cached)
        if selected_stat not in alt_line_manager.alternate_lines:
            with st.spinner(f"Fetching alternate lines for {selected_stat}..."):
                # This will populate the cache for this stat type
                if selected_stat in alt_line_manager.stat_market_mapping:
                    alt_line_manager.alternate_lines[selected_stat] = alt_line_manager.fetch_alternate_lines_for_stat(selected_stat)
                    st.success(f"✅ Cached alternate lines for {selected_stat}")
        else:
            st.info(f"ℹ️ Using cached alternate lines for {selected_stat}")
        
        # Calculate comprehensive scores
        scored_props = []
        alternate_line_props = []  # Store alternate line props separately
        
        for _, row in filtered_df.iterrows():
            score_data = scorer.calculate_comprehensive_score(
                row['Player'],
                row['Opposing Team'], 
                row['Stat Type'],
                row['Line'],
                row.get('Odds', 0)
            )
            scored_prop = {**row.to_dict(), **score_data}
            scored_props.append(scored_prop)
            
            # Calculate 70% threshold and find alternate line
            player_name = row['Player']
            stat_type = row['Stat Type']
            
            # Get player's stat history from data processor
            if hasattr(data_processor, 'player_season_stats'):
                player_stats_dict = data_processor.player_season_stats
                
                # Try to find player stats (case-insensitive with name cleaning)
                from utils import clean_player_name
                cleaned_player_name = clean_player_name(player_name)
                player_stats = None
                for stored_player, stats in player_stats_dict.items():
                    cleaned_stored = clean_player_name(stored_player)
                    if cleaned_stored.lower() == cleaned_player_name.lower() and stat_type in stats:
                        player_stats = stats[stat_type]
                        break
                
                if player_stats and len(player_stats) > 0:
                    # Calculate 70% threshold
                    threshold, actual_rate = calculate_70_percent_threshold(player_stats)
                    
                    # Find closest alternate line
                    alt_line = alt_line_manager.get_closest_alternate_line(
                        player_name, stat_type, threshold
                    )
                    
                    if alt_line:
                        # Create alternate line prop row
                        alt_score_data = scorer.calculate_comprehensive_score(
                            player_name,
                            row['Opposing Team'],
                            stat_type,
                            alt_line['line'],
                            alt_line['odds']
                        )
                        
                        alt_prop = {
                            **row.to_dict(),
                            'Line': alt_line['line'],
                            'Odds': alt_line['odds'],
                            **alt_score_data,
                            'is_alternate': True,  # Flag to identify alternate lines
                            'calculated_threshold': threshold,
                            'threshold_over_rate': actual_rate
                        }
                        alternate_line_props.append(alt_prop)
        
        # Combine main props and alternate line props
        all_props = scored_props + alternate_line_props
        
        # Show info about alternate lines added
        if alternate_line_props:
            st.info(f"✨ Added {len(alternate_line_props)} alternate line recommendation(s) based on 70% threshold analysis")
        
        # Convert to DataFrame
        results_df = pd.DataFrame(all_props)
        
        # No additional filtering needed
        
        # Add is_alternate flag if not present
        if 'is_alternate' not in results_df.columns:
            results_df['is_alternate'] = False
        
        # Sort by Player name, then by is_alternate (False first, then True)
        # This groups each player's main line with their alternate line
        results_df = results_df.sort_values(['Player', 'is_alternate'], ascending=[True, True])
        
        if results_df.empty:
            st.warning(f"No props found matching the selected criteria.")
            st.stop()
        
        # Format the display
        display_columns = [
            'Player', 'Opposing Team', 'team_rank', 'total_score', 
            'Line', 'Odds', 'over_rate'
        ]
        
        display_df = results_df[display_columns].copy()
        
        # Rename columns for display
        display_df.columns = [
            'Player', 'Opposing Team', 'Team Rank', 'Score', 
            'Line', 'Odds', 'Over Rate'
        ]
        
        # Format the line display
        display_df['Line'] = display_df['Line'].apply(lambda x: format_line(x, selected_stat))
        
        # Format odds
        display_df['Odds'] = display_df['Odds'].apply(format_odds)
        
        # Format over rate as percentage
        display_df['Over Rate'] = (display_df['Over Rate'] * 100).round(1).astype(str) + '%'
        
        # Color code the scores
        def color_score(val):
            if val >= 80:
                return 'background-color: #d4edda'  # Green
            elif val >= 70:
                return 'background-color: #fff3cd'  # Yellow
            elif val >= 60:
                return 'background-color: #f8d7da'  # Light red
            else:
                return 'background-color: #f5c6cb'  # Red
        
        styled_df = display_df.style.applymap(color_score, subset=['Score'])
        
        # Display the results
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        
    
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.stop()

if __name__ == "__main__":
    main()
