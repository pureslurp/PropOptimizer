"""
Enhanced Odds API Client with Database Caching
Handles interactions with The Odds API and integrates with PostgreSQL database
"""

import requests
import time
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import pandas as pd
from database_manager import DatabaseManager
from database_models import Game
import streamlit as st


class OddsAPIWithDB:
    """Enhanced Odds API client with database caching"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.player_teams = {}  # Cache for player team assignments
        self.requests_used = None
        self.requests_remaining = None
        self.last_request_time = None
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Map team abbreviations to full names (as used by Odds API)
        self.team_name_mapping = {
            'ARI': 'Arizona Cardinals',
            'ATL': 'Atlanta Falcons', 
            'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills',
            'CAR': 'Carolina Panthers',
            'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals',
            'CLE': 'Cleveland Browns',
            'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos',
            'DET': 'Detroit Lions',
            'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans',
            'IND': 'Indianapolis Colts',
            'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs',
            'LV': 'Las Vegas Raiders',
            'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams',
            'MIA': 'Miami Dolphins',
            'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots',
            'NO': 'New Orleans Saints',
            'NYG': 'New York Giants',
            'NYJ': 'New York Jets',
            'PHI': 'Philadelphia Eagles',
            'PIT': 'Pittsburgh Steelers',
            'SF': 'San Francisco 49ers',
            'SEA': 'Seattle Seahawks',
            'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans',
            'WAS': 'Washington Commanders'
        }
        
        # Create reverse mapping (full name to abbreviation)
        self.team_abbrev_mapping = {v: k for k, v in self.team_name_mapping.items()}
        
        # Stat type to market mapping for alternate lines
        self.stat_market_mapping = {
            'Passing Yards': 'player_pass_yds_alternate',
            'Rushing Yards': 'player_rush_yds_alternate', 
            'Receiving Yards': 'player_reception_yds_alternate',
            'Receptions': 'player_receptions_alternate',
            'Receiving Touchdowns': 'player_reception_tds_alternate'
            # TDs removed to save API credits (same as original)
            # 'Passing Touchdowns': 'player_pass_tds_alternate',
            # 'Rushing Touchdowns': 'player_rush_tds_alternate',
        }
        
        self.odds_data = []  # Store events data
    
    def _update_usage_from_headers(self, headers: Dict):
        """Update API usage info from response headers"""
        self.requests_used = headers.get('x-requests-used')
        self.requests_remaining = headers.get('x-requests-remaining')
        self.last_request_time = datetime.now()
    
    def get_cached_props(self, week: int = None, max_age_hours: int = 2) -> Optional[List[Dict]]:
        """
        Get cached props from database if they're fresh
        
        Args:
            week: Week number to filter by
            max_age_hours: Maximum age of cached data in hours
            
        Returns:
            List of events if cache is fresh, None if stale/missing
        """
        try:
            if self.db_manager.is_data_fresh('props', max_age_hours):
                print("📊 Using cached props data from database")
                
                # Convert database props to API format
                props_df = self.db_manager.get_props_as_dataframe(week=week)
                if props_df.empty:
                    print("⚠️ No props data found in database")
                    return None
                
                # Convert DataFrame to API format (group by game)
                api_events = self._convert_df_to_api_format(props_df)
                print(f"✅ Converted {len(props_df)} props to {len(api_events)} API events")
                return api_events
            else:
                print("🔄 Cached props data is stale, need to refresh")
                return None
        except Exception as e:
            print(f"❌ Error getting cached props: {e}")
            return None
    
    def _convert_df_to_api_format(self, props_df) -> List[Dict]:
        """
        Convert database DataFrame back to API format (grouped by game)
        
        Args:
            props_df: DataFrame with props data from database
            
        Returns:
            List of events in API format
        """
        if props_df.empty:
            return []
        
        # Group props by game (using Home Team + Away Team as game identifier)
        events = []
        
        for (home_team, away_team), game_props in props_df.groupby(['Home Team', 'Away Team']):
            if pd.isna(home_team) or pd.isna(away_team):
                continue
                
            # Create event structure matching API format
            event = {
                'id': f"{away_team}_at_{home_team}",  # Simple ID format
                'sport_key': 'americanfootball_nfl',
                'sport_title': 'NFL',
                'commence_time': game_props['Commence Time'].iloc[0] if 'Commence Time' in game_props.columns else None,
                'home_team': home_team,
                'away_team': away_team,
                'bookmakers': []
            }
            
            # Group props by bookmaker
            for bookmaker, bookmaker_props in game_props.groupby('Bookmaker'):
                if pd.isna(bookmaker):
                    continue
                    
                bookmaker_data = {
                    'key': bookmaker.lower().replace(' ', '_'),
                    'title': bookmaker,
                    'markets': []
                }
                
                # Group props by stat type
                for stat_type, stat_props in bookmaker_props.groupby('Stat Type'):
                    if pd.isna(stat_type):
                        continue
                        
                    market_data = {
                        'key': stat_type.lower().replace(' ', '_'),
                        'outcomes': []
                    }
                    
                    # Add each prop as an outcome
                    for _, prop in stat_props.iterrows():
                        if pd.isna(prop['Player']) or pd.isna(prop['Line']) or pd.isna(prop['Odds']):
                            continue
                            
                        outcome = {
                            'name': prop['Player'],
                            'price': prop['Odds'],
                            'point': prop['Line']
                        }
                        market_data['outcomes'].append(outcome)
                    
                    if market_data['outcomes']:
                        bookmaker_data['markets'].append(market_data)
                
                if bookmaker_data['markets']:
                    event['bookmakers'].append(bookmaker_data)
            
            if event['bookmakers']:
                events.append(event)
        
        return events
    
    def _should_refresh_props(self, week: int = None) -> bool:
        """
        Check if we should refresh props data based on game start times
        
        Args:
            week: Week number to check
            
        Returns:
            True if we need to fetch fresh props for upcoming games, False otherwise
        """
        try:
            from database_models import Game
            from datetime import datetime
            
            with self.db_manager.get_session() as session:
                current_time = datetime.utcnow()
                
                if week:
                    # Check specific week
                    games = session.query(Game).filter(Game.week == week).all()
                else:
                    # Check current week
                    from utils import get_current_week_from_dates
                    current_week = get_current_week_from_dates()
                    games = session.query(Game).filter(Game.week == current_week).all()
                
                if not games:
                    print("⚠️ No games found in database for this week")
                    return True  # Fetch fresh data if no games exist
                
                # Check if any games haven't started yet
                unstarted_games = [game for game in games if game.commence_time and game.commence_time > current_time]
                
                if unstarted_games:
                    print(f"🔄 {len(unstarted_games)} upcoming games found, will fetch fresh odds for upcoming games only")
                    return True
                else:
                    print(f"📊 All {len(games)} games have started, using existing historical data")
                    return False
                    
        except Exception as e:
            print(f"❌ Error checking game start times: {e}")
            return True  # Default to refreshing if we can't determine
            
    def store_props_to_db(self, props_data: List[Dict], games_data: List[Dict]):
        """
        Store props and games data to database with enhanced team information
        
        Args:
            props_data: List of props dictionaries
            games_data: List of games dictionaries
        """
        try:
            # Store games first
            for game in games_data:
                self.db_manager.store_game(game)
            
            # Store props grouped by game
            props_by_game = {}
            for prop in props_data:
                game_id = prop.get('game_id')
                if game_id not in props_by_game:
                    props_by_game[game_id] = []
                props_by_game[game_id].append(prop)
            
            # Store props for each game
            for game_id, game_props in props_by_game.items():
                self.db_manager.store_props(game_id, game_props)
            
            # Update cache metadata (2 hours for production)
            self.db_manager.update_cache_metadata('props', len(props_data), max_age_hours=2)
            print(f"✅ Stored {len(props_data)} props to database")
            
        except Exception as e:
            print(f"❌ Error storing props to database: {e}")
    
    def get_player_props_with_cache(self, sport: str = "americanfootball_nfl", num_events: int = 5, week: int = None) -> List[Dict]:
        """
        Fetch NFL events for player props with database caching
        
        Args:
            sport: Sport key (default: americanfootball_nfl)
            num_events: Optional limit on number of events to return
            week: Week number for caching
            
        Returns:
            List of event dictionaries
        """
        # First, try to get cached data
        cached_props = self.get_cached_props(week=week)
        if cached_props is not None:
            return cached_props
        
        # If no cache or stale, check if we need to fetch fresh data
        if self._should_refresh_props(week):
            print("🔄 Fetching fresh data from API...")
            return self.get_player_props(sport, num_events)
        else:
            print("📊 Using existing database data (no games need refreshing)")
            # Return cached data even if stale, since no games need updating
            props_df = self.db_manager.get_props_as_dataframe(week=week)
            if not props_df.empty:
                return self._convert_df_to_api_format(props_df)
            return []
    
    def get_player_props(self, sport: str = "americanfootball_nfl", num_events: int = 5) -> List[Dict]:
        """
        Fetch NFL events for player props (OPTIMIZED: only gets event IDs, not main props)
        Main props are fetched via alternate lines endpoint to save API calls
        
        Args:
            sport: Sport key (default: americanfootball_nfl)
            num_events: Optional limit on number of events to return (default: None = all events)
        
        Returns:
            List of event dictionaries
        """
        try:
            # Get events
            events_url = f"{self.base_url}/sports/{sport}/events"
            events_params = {
                'apiKey': self.api_key,
                'regions': 'us'
            }
            
            events_response = requests.get(events_url, params=events_params, timeout=30)
            events_response.raise_for_status()
            
            # Update usage info from response headers
            self._update_usage_from_headers(events_response.headers)
            
            events = events_response.json()
            
            if not events:
                return []
            
            # Limit events if specified
            if num_events and len(events) > num_events:
                events = events[:num_events]
            
            # Store events data for later use
            self.odds_data = events
            
            return events
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching events: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []
    
    def fetch_all_alternate_lines_optimized_with_cache(self, bookmaker: str = 'fanduel', progress_callback=None, week: int = None) -> Dict[str, Dict]:
        """
        OPTIMIZED: Fetch ALL alternate lines with database caching
        
        Args:
            bookmaker: The bookmaker to use (default: 'fanduel')
            progress_callback: Optional callback function to report progress
            week: Week number for caching
            
        Returns:
            Dict mapping stat types to player alternate lines
        """
        # For now, always fetch from API to avoid format conversion issues
        # TODO: Implement proper database caching for alternate lines
        print("🔄 Fetching fresh alternate lines from API...")
        return self.fetch_all_alternate_lines_optimized(bookmaker, progress_callback)
    
    def _convert_cached_props_to_alternate_format(self, cached_props: List[Dict]) -> Dict[str, Dict]:
        """
        Convert cached props back to the alternate lines format expected by the app
        
        Args:
            cached_props: List of cached props from database
            
        Returns:
            Dict in the format expected by the application
        """
        result = {}
        
        # Group props by stat type
        for stat_type in self.stat_market_mapping.keys():
            result[stat_type] = {}
        
        # Process cached props
        for prop in cached_props:
            stat_type = prop['stat_type']
            if stat_type in result:
                player = prop['player']
                if player not in result[stat_type]:
                    result[stat_type][player] = []
                
                result[stat_type][player].append({
                    'line': prop['line'],
                    'odds': prop['odds'],
                    'bookmaker': prop['bookmaker'],
                    'is_alternate': prop['is_alternate']
                })
        
        return result
    
    def fetch_all_alternate_lines_optimized(self, bookmaker: str = 'fanduel', progress_callback=None) -> Dict[str, Dict]:
        """
        OPTIMIZED: Fetch ALL alternate lines for ALL stat types in one pass
        
        This makes 1 API call per game instead of 1 call per stat type per game
        Reduces API calls from ~35 to ~5 per refresh!
        
        Args:
            bookmaker: The bookmaker to use (default: 'fanduel')
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dict mapping stat types to player alternate lines
        """
        # Filter out events that have already started or finished
        current_time = datetime.now(timezone.utc)
        active_events = []
        for event in self.odds_data:
            if event.get('id'):
                commence_time_str = event.get('commence_time')
                if commence_time_str:
                    try:
                        commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                        if commence_time > current_time:
                            active_events.append(event)
                    except (ValueError, AttributeError):
                        continue
        
        event_ids = [event.get('id') for event in active_events]
        if not event_ids:
            return {}
        
        # Initialize result structure for all stat types
        all_alternate_lines = {stat_type: {} for stat_type in self.stat_market_mapping.keys()}
        
        # Get all alternate market keys
        all_alternate_markets = ','.join(self.stat_market_mapping.values())
        total_events = len(event_ids)
        
        # Initialize ONE data processor for team lookups (reuse for all props)
        from enhanced_data_processor import EnhancedFootballDataProcessor
        shared_data_processor = EnhancedFootballDataProcessor(use_database=True, skip_calculations=True)
        print("✅ Initialized shared data processor for team lookups")
        
        # Store games data for database
        games_data = []
        all_props_data = []
        
        # Fetch alternate lines for each event (ONE CALL PER GAME instead of 7!)
        for idx, event_id in enumerate(event_ids, 1):
            if progress_callback:
                progress_callback(f"Fetching all alternate lines... ({idx}/{total_events})")
            
            try:
                odds_url = f"{self.base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
                odds_params = {
                    'apiKey': self.api_key,
                    'regions': 'us',
                    'bookmakers': bookmaker,
                    'markets': all_alternate_markets,
                    'oddsFormat': 'american',
                    'includeAltLines': 'true'
                }
                
                odds_response = requests.get(odds_url, params=odds_params, timeout=30)
                odds_response.raise_for_status()
                
                # Update usage info
                self._update_usage_from_headers(odds_response.headers)
                
                if odds_response.status_code == 200:
                    event_data = odds_response.json()
                    
                    print(f"DEBUG: API response for event {event_id}: {type(event_data)}")
                    if isinstance(event_data, dict):
                        print(f"DEBUG: Event data keys: {list(event_data.keys())}")
                    
                    if not event_data:
                        print(f"DEBUG: Empty response for event {event_id}")
                        continue
                    
                    # Extract event context
                    commence_time = event_data.get('commence_time')
                    
                    # Store game data for database
                    if commence_time:
                        try:
                            commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                            # Extract week from commence time (simplified - you might want to improve this)
                            week_num = self._extract_week_from_date(commence_dt)
                            
                            game_data = {
                                'id': event_id,
                                'home_team': event_data.get('home_team', ''),
                                'away_team': event_data.get('away_team', ''),
                                'commence_time': commence_dt,
                                'week': week_num,
                                'season': 2025
                            }
                            games_data.append(game_data)
                        except Exception as e:
                            print(f"Error processing game data: {e}")
                    
                    # Process all markets for this event
                    for market in event_data.get('bookmakers', []):
                        if market.get('key') == bookmaker:
                            for outcome in market.get('markets', []):
                                market_key = outcome.get('key')
                                
                                # Find matching stat type
                                stat_type = None
                                for st, mk in self.stat_market_mapping.items():
                                    if mk == market_key:
                                        stat_type = st
                                        break
                                
                                if stat_type:
                                    # Process outcomes for this market
                                    for outcome_data in outcome.get('outcomes', []):
                                        player = outcome_data.get('description', '')
                                        line = outcome_data.get('point', 0)
                                        odds = outcome_data.get('price', 0)
                                        
                                        if player and line is not None:
                                            # Add to results
                                            if player not in all_alternate_lines[stat_type]:
                                                all_alternate_lines[stat_type][player] = []
                                            
                                            all_alternate_lines[stat_type][player].append({
                                                'line': line,
                                                'odds': odds,
                                                'bookmaker': bookmaker,
                                                'is_alternate': True,
                                                'home_team': event_data.get('home_team', ''),
                                                'away_team': event_data.get('away_team', ''),
                                                'commence_time': event_data.get('commence_time', ''),
                                                'event_id': event_id  # Add event_id for game tracking
                                            })
                                            
                                            # Store prop data for database with enhanced columns
                                            # Get team information using SHARED data processor (no new instance!)
                                            player_team = shared_data_processor.get_player_team(player) or "Unknown"
                                            opp_team_full = self._get_opposing_team_from_game_context(
                                                player_team, 
                                                event_data.get('home_team', ''), 
                                                event_data.get('away_team', '')
                                            )
                                            
                                            prop_data = {
                                                'game_id': event_id,
                                                'player': player,
                                                'stat_type': stat_type,
                                                'line': line,
                                                'odds': odds,
                                                'bookmaker': bookmaker,
                                                'is_alternate': True,
                                                # Enhanced columns with actual team data
                                                'player_team': player_team,
                                                'opp_team': self._format_opp_team_display(opp_team_full, player_team, event_data.get('home_team', '')),
                                                'opp_team_full': opp_team_full,
                                                'team_rank': None,  # Could be calculated later
                                                'commence_time': commence_time,
                                                'home_team': event_data.get('home_team', ''),
                                                'away_team': event_data.get('away_team', '')
                                            }
                                            all_props_data.append(prop_data)
                
                # Rate limiting
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching odds for event {event_id}: {e}")
                continue
            except Exception as e:
                print(f"❌ Unexpected error for event {event_id}: {e}")
                import traceback
                print(f"DEBUG: Full traceback: {traceback.format_exc()}")
                continue
        
        # DON'T store to database here - let the caller do it after calculations
        # (The caller needs to add team_pos_rank_stat_type and week first)
        
        return all_alternate_lines
    
    def _extract_week_from_date(self, date: datetime) -> int:
        """
        Extract week number from date (simplified implementation)
        You might want to improve this based on your NFL schedule logic
        """
        # This is a simplified implementation
        # You might want to use your existing week detection logic
        from datetime import datetime, timezone
        season_start = datetime(2025, 9, 4, tzinfo=timezone.utc)  # Week 1 start with timezone
        days_diff = (date - season_start).days
        week = (days_diff // 7) + 1
        return max(1, min(18, week))  # Clamp between 1 and 18
    
    def update_team_assignments(self, props_df: pd.DataFrame, data_processor) -> pd.DataFrame:
        """Update team assignments using actual player data"""
        if props_df.empty:
            return props_df
        
        updated_props = []
        
        for _, row in props_df.iterrows():
            player = row['Player']
            stat_type = row['Stat Type']
            home_team = row.get('Home Team', '')
            away_team = row.get('Away Team', '')
            
            # Only update team assignments if they're missing, None, empty, or Unknown
            if pd.isna(row.get('Team')) or row.get('Team') is None or row.get('Team') == '' or row.get('Team') == 'Unknown':
                try:
                    # Get player's team
                    player_team = data_processor.get_player_team(player)
                    if player_team:
                        row['Team'] = player_team
                        
                        # Determine opposing team from game context
                        if player_team == home_team:
                            row['Opp. Team'] = away_team
                            row['Opp. Team Full'] = away_team
                        elif player_team == away_team:
                            row['Opp. Team'] = home_team
                            row['Opp. Team Full'] = home_team
                        else:
                            # Player team doesn't match home/away, use home team as default
                            row['Opp. Team'] = home_team
                            row['Opp. Team Full'] = home_team
                    else:
                        # Set default values to prevent None errors
                        row['Team'] = 'Unknown'
                        row['Opp. Team'] = 'Unknown'
                        row['Opp. Team Full'] = 'Unknown'
                        
                except Exception as e:
                    print(f"Error getting team info for {player}: {e}")
                    # Set default values to prevent None errors
                    row['Team'] = 'Unknown'
                    row['Opp. Team'] = 'Unknown'
                    row['Opp. Team Full'] = 'Unknown'
            else:
                # Team info already exists, determine opposing team if missing
                player_team = row.get('Team', '')
                if pd.isna(row.get('Opp. Team')) or row.get('Opp. Team') is None or row.get('Opp. Team') == '':
                    if player_team == home_team:
                        row['Opp. Team'] = away_team
                        row['Opp. Team Full'] = away_team
                    elif player_team == away_team:
                        row['Opp. Team'] = home_team
                        row['Opp. Team Full'] = home_team
                    else:
                        row['Opp. Team'] = home_team
                        row['Opp. Team Full'] = home_team
                if pd.isna(row.get('Opp. Team Full')) or row.get('Opp. Team Full') is None or row.get('Opp. Team Full') == '':
                    if player_team == home_team:
                        row['Opp. Team Full'] = away_team
                    elif player_team == away_team:
                        row['Opp. Team Full'] = home_team
                    else:
                        row['Opp. Team Full'] = home_team
            
            updated_props.append(row)
        
        return pd.DataFrame(updated_props)
    
    def _get_player_team_from_data(self, player_name: str) -> str:
        """Get player's team from data processor"""
        try:
            # Use the data processor to get player team
            from enhanced_data_processor import EnhancedFootballDataProcessor
            data_processor = EnhancedFootballDataProcessor(use_database=True, skip_calculations=True)
            player_team = data_processor.get_player_team(player_name)
            return player_team if player_team else "Unknown"
        except Exception as e:
            print(f"Error getting team for {player_name}: {e}")
            return "Unknown"
    
    def _get_opposing_team_from_game_context(self, player_team: str, home_team: str, away_team: str) -> str:
        """Get opposing team from game context"""
        if player_team == home_team:
            return away_team
        elif player_team == away_team:
            return home_team
        else:
            return "Unknown"
    
    def _format_opp_team_display(self, opp_team_full: str, player_team: str, home_team: str) -> str:
        """Format opposing team for display (vs/@ format)"""
        if opp_team_full == "Unknown":
            return "Unknown"
        
        # Convert full team name to abbreviation
        opp_abbrev = self.team_abbrev_mapping.get(opp_team_full, opp_team_full)
        
        # Determine if player is home or away
        if player_team == home_team:
            return f"vs {opp_abbrev}"
        else:
            return f"@ {opp_abbrev}"
    
    def parse_player_props(self, odds_data: List[Dict]) -> pd.DataFrame:
        """
        Parse odds data into a structured DataFrame
        OPTIMIZED: Now expects just event data (home/away teams, commence time)
        Returns empty DataFrame - actual props come from alternate lines to save API calls
        """
        # Return empty DataFrame with correct structure
        # Alternate lines will be the primary data source
        return pd.DataFrame(columns=[
            'Player', 'Team', 'Opp. Team', 'Stat Type', 'Line', 'Odds',
            'Bookmaker', 'Market', 'Home Team', 'Away Team', 'Commence Time', 
            'Opp. Team Full'
        ])
    
    def get_usage_info(self) -> Dict:
        """Get current API usage information (alias for get_api_usage_info)"""
        return self.get_api_usage_info()
    
    def get_api_usage_info(self) -> Dict:
        """Get current API usage information"""
        return {
            'requests_used': self.requests_used,
            'requests_remaining': self.requests_remaining,
            'last_request_time': self.last_request_time
        }
    
    def print_usage_warning(self):
        """Print API usage warning if needed"""
        if self.requests_remaining is not None and int(self.requests_remaining) < 100:
            print(f"⚠️ API calls remaining: {self.requests_remaining}")
    
    def get_player_team_from_data(self, player_name: str, data_processor) -> str:
        """Get player team from data processor"""
        try:
            # This is a simplified implementation
            # You might want to enhance this based on your data processor
            return ""
        except Exception as e:
            print(f"Error getting team for {player_name}: {e}")
            return ""
    
    def get_nfl_events(self, sport: str = "americanfootball_nfl") -> List[Dict]:
        """Get NFL events (alias for get_player_props)"""
        return self.get_player_props(sport)
    
    def save_to_json(self, data: Dict, filename: str = None) -> str:
        """Save data to JSON file"""
        if filename is None:
            filename = f"odds_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return filename
        except Exception as e:
            print(f"Error saving to JSON: {e}")
            return ""
    
    def analyze_alternate_lines(self, data: Dict) -> Dict:
        """Analyze alternate lines data"""
        # This is a placeholder implementation
        return data
    
    def convert_alternate_lines_to_props_df(self, alternate_lines_data: Dict) -> pd.DataFrame:
        """
        Convert alternate lines dictionary to props DataFrame format
        
        Args:
            alternate_lines_data: Dict mapping stat types to player alternate lines
            
        Returns:
            DataFrame in props format with all alternate lines
        """
        props = []
        
        for stat_type, players_dict in alternate_lines_data.items():
            for player_name, lines in players_dict.items():
                for line_data in lines:
                    # Event context is stored in each line_data
                    props.append({
                        'Player': player_name,
                        'Team': 'Unknown',  # Will be updated later
                        'Opp. Team': 'Unknown',  # Will be updated later
                        'Stat Type': stat_type,
                        'Line': line_data['line'],
                        'Odds': line_data['odds'],
                        'Bookmaker': line_data.get('bookmaker', 'FanDuel'),
                        'Market': self.stat_market_mapping.get(stat_type, ''),
                        'Home Team': line_data.get('home_team', ''),
                        'Away Team': line_data.get('away_team', ''),
                        'Commence Time': line_data.get('commence_time', ''),
                        'Opp. Team Full': 'Unknown',
                        'is_alternate': True,
                        'event_id': line_data.get('event_id', '')  # Add event_id for game tracking
                    })
        
        return pd.DataFrame(props)
    
    def _extract_games_data(self, alternate_lines_data: Dict) -> List[Dict]:
        """
        Extract games data from alternate lines data for database storage
        
        Args:
            alternate_lines_data: Dict mapping stat types to player alternate lines
            
        Returns:
            List of game dictionaries for database storage
        """
        games_data = []
        processed_games = set()
        
        for stat_type, players_dict in alternate_lines_data.items():
            for player_name, lines in players_dict.items():
                for line_data in lines:
                    # Get game info from line data
                    home_team = line_data.get('home_team', '')
                    away_team = line_data.get('away_team', '')
                    commence_time_str = line_data.get('commence_time', '')
                    event_id = line_data.get('event_id', '')
                    
                    # Create unique game identifier
                    game_key = f"{away_team}_at_{home_team}"
                    
                    if game_key not in processed_games and home_team and away_team:
                        # Parse commence_time for week extraction
                        week = None
                        if commence_time_str:
                            try:
                                from dateutil.parser import parse
                                commence_time_dt = parse(commence_time_str)
                                week = self._extract_week_from_date(commence_time_dt)
                            except:
                                pass
                        
                        games_data.append({
                            'id': event_id or game_key,  # Use 'id' to match store_game expectation
                            'home_team': home_team,
                            'away_team': away_team,
                            'commence_time': commence_time_str,
                            'week': week,
                            'season': 2025
                        })
                        processed_games.add(game_key)
        
        return games_data
    
    def fetch_historical_props_for_game(self, game_id: str) -> List[Dict]:
        """
        Fetch historical props for a specific game (2 hours before game time).
        
        Args:
            game_id: The game ID
            
        Returns:
            List of prop dictionaries in database format
        """
        try:
            # Get game from database to find commence time
            with self.db_manager.get_session() as session:
                game = session.query(Game).filter(Game.id == game_id).first()
                
                if not game:
                    print(f"  ❌ Game {game_id} not found in database")
                    return []
                
                if not game.commence_time:
                    print(f"  ❌ Game {game_id} has no commence_time")
                    return []
                
                # Calculate 2 hours before game time
                two_hours_before = game.commence_time - timedelta(hours=2)
                
                # Format date for API (ISO 8601 format)
                date_str = two_hours_before.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                print(f"  📅 Fetching historical odds at: {date_str} (2 hours before {game.commence_time})")
                
                # Define markets to fetch (same as alternate lines)
                markets = list(self.stat_market_mapping.values())
                markets_str = ','.join(markets)
                
                # Call historical API
                url = f"{self.base_url}/historical/sports/americanfootball_nfl/events/{game_id}/odds"
                
                params = {
                    'apiKey': self.api_key,
                    'date': date_str,
                    'regions': 'us',
                    'markets': markets_str,
                    'oddsFormat': 'american',
                    'bookmakers': 'fanduel'
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # Update usage info
                self._update_usage_from_headers(response.headers)
                
                response_data = response.json()
                
                if not response_data:
                    print(f"  ⚠️ No historical data returned for game {game_id}")
                    return []
                
                # Historical API wraps event data in a 'data' key
                event_data = response_data.get('data', {})
                
                if not event_data:
                    print(f"  ⚠️ No event data in response for game {game_id}")
                    return []
                
                # Parse response into prop format
                props_list = []
                
                # Initialize shared data processor for team lookups
                from enhanced_data_processor import EnhancedFootballDataProcessor
                data_processor = EnhancedFootballDataProcessor(use_database=True, skip_calculations=True)
                
                for bookmaker in event_data.get('bookmakers', []):
                    if bookmaker.get('key') != 'fanduel':
                        continue
                    
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key')
                        
                        # Find matching stat type
                        stat_type = None
                        for st, mk in self.stat_market_mapping.items():
                            if mk == market_key:
                                stat_type = st
                                break
                        
                        if not stat_type:
                            continue
                        
                        # Process outcomes
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') != 'Over':
                                continue
                            
                            player = outcome.get('description', '')
                            line = outcome.get('point', 0)
                            odds = outcome.get('price', 0)
                            
                            if not player or line is None:
                                continue
                            
                            # Get team information
                            player_team = data_processor.get_player_team(player) or "Unknown"
                            opp_team_full = self._get_opposing_team_from_game_context(
                                player_team,
                                event_data.get('home_team', ''),
                                event_data.get('away_team', '')
                            )
                            
                            # Get defensive rank
                            team_rank = None
                            try:
                                team_rank = data_processor.get_position_defensive_rank(opp_team_full, player, stat_type)
                            except:
                                pass
                            
                            prop_dict = {
                                'game_id': game_id,
                                'player': player,
                                'stat_type': stat_type,
                                'line': line,
                                'odds': odds,
                                'bookmaker': 'fanduel',
                                'is_alternate': True,
                                'timestamp': two_hours_before,
                                'player_team': player_team,
                                'opp_team': self._format_opp_team_display(opp_team_full, player_team, game.home_team),
                                'opp_team_full': opp_team_full,
                                'team_pos_rank_stat_type': team_rank,
                                'week': game.week,
                                'commence_time': game.commence_time,
                                'home_team': game.home_team,
                                'away_team': game.away_team,
                                'prop_source': 'historical_api'  # Mark as historical
                            }
                            props_list.append(prop_dict)
                
                print(f"  ✅ Parsed {len(props_list)} historical props")
                return props_list
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ API error fetching historical props for game {game_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"     Response: {e.response.text}")
            return []
        except Exception as e:
            print(f"  ❌ Error fetching historical props for game {game_id}: {e}")
            import traceback
            traceback.print_exc()
            return []