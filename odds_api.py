"""
Odds API Client for NFL Player Props
Handles interactions with The Odds API for fetching player props and alternate lines
"""

import requests
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


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
        
        # Create reverse mapping (full name to abbreviation)
        self.team_abbrev_mapping = {v: k for k, v in self.team_name_mapping.items()}
        
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
                return []
            
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
                    time.sleep(0.3)
                    
                except Exception as e:
                    continue
            
            return all_games
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds data: {e}")
            return []
    
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
                    
                    # Map market keys to our stat types
                    stat_mapping = {
                        'player_pass_yds': 'Passing Yards',
                        'player_pass_tds': 'Passing TDs',
                        'player_rush_yds': 'Rushing Yards', 
                        'player_rush_tds': 'Rushing TDs',
                        'player_receptions': 'Receptions',
                        'player_reception_yds': 'Receiving Yards',
                        'player_reception_tds': 'Receiving TDs'
                    }
                    
                    stat_type = stat_mapping.get(market_key, market_key)
                    
                    for outcome in market.get('outcomes', []):
                        # Handle the new API format where player names are in description for "Over" outcomes
                        if outcome.get('name') == 'Over' and outcome.get('description'):
                            player_name = outcome.get('description', '').strip()
                            line = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            # Fix reception lines: API returns 2.5 for "3+ receptions", so add 1
                            if stat_type == 'Receptions':
                                line = line + 1
                            
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
                            
                            # Fix reception lines: API returns 2.5 for "3+ receptions", so add 1
                            if stat_type == 'Receptions':
                                line = line + 1
                            
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
            opposing_team_full = "Unknown"  # Keep full name for lookups
            if player_team != "Unknown" and 'Home Team' in row and 'Away Team' in row:
                home_team = row['Home Team']
                away_team = row['Away Team']
                # Determine opposing team based on which team the player is on
                is_home_game = False
                if player_team == home_team:
                    opposing_team_full = away_team
                    is_home_game = True
                elif player_team == away_team:
                    opposing_team_full = home_team
                    is_home_game = False
                
                # Format opposing team as "vs NYG" or "@ NYG" for display
                if opposing_team_full != "Unknown":
                    opp_abbrev = self.team_abbrev_mapping.get(opposing_team_full, opposing_team_full)
                    if is_home_game:
                        opposing_team = f"vs {opp_abbrev}"
                    else:
                        opposing_team = f"@ {opp_abbrev}"
                else:
                    opposing_team = "Unknown"
            
            # Update the row
            updated_row = row.copy()
            updated_row['Team'] = player_team
            updated_row['Opposing Team'] = opposing_team  # Display version
            updated_row['Opposing Team Full'] = opposing_team_full  # Full name for lookups
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
    
    def get_nfl_events(self, sport: str = "americanfootball_nfl") -> List[Dict]:
        """
        Get list of NFL events
        
        Args:
            sport: Sport key (default: americanfootball_nfl)
            
        Returns:
            List of event dictionaries
        """
        url = f"{self.base_url}/sports/{sport}/events"
        params = {
            'apiKey': self.api_key,
            'regions': 'us'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching NFL events: {e}")
            return []
    
    def save_to_json(self, data: Dict, filename: str = None) -> str:
        """
        Save data to JSON file
        
        Args:
            data: Data to save
            filename: Optional filename (will auto-generate if not provided)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"odds_data_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data saved to: {filepath}")
        return filepath
    
    def analyze_alternate_lines(self, data: Dict) -> Dict:
        """
        Analyze alternate lines data and provide insights
        
        Args:
            data: Alternate lines data from fetch
            
        Returns:
            Analysis dictionary with statistics
        """
        analysis = {
            'total_events_attempted': len(data.get('events', [])) + len(data.get('errors', [])),
            'successful_events': len(data.get('events', [])),
            'failed_events': len(data.get('errors', [])),
            'total_outcomes': 0,
            'players_found': set(),
            'market_summary': {}
        }
        
        # Analyze successful events
        for event in data.get('events', []):
            for bookmaker in event.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key')
                    outcomes = market.get('outcomes', [])
                    
                    if market_key not in analysis['market_summary']:
                        analysis['market_summary'][market_key] = 0
                    analysis['market_summary'][market_key] += len(outcomes)
                    analysis['total_outcomes'] += len(outcomes)
                    
                    # Extract player names
                    for outcome in outcomes:
                        description = outcome.get('description', '')
                        if description:
                            analysis['players_found'].add(description)
        
        # Convert set to list for JSON serialization
        analysis['players_found'] = list(analysis['players_found'])
        
        return analysis


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
            'Receiving TDs': 'player_reception_tds_alternate'
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
                                                
                                                line = outcome.get('point', 0)
                                                # Fix reception lines: API returns 2.5 for "3+ receptions", so add 1
                                                if stat_type == 'Receptions':
                                                    line = line + 1
                                                
                                                parsed_lines[player_name].append({
                                                    'line': line,
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

