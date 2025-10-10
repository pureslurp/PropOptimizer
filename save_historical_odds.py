"""
Save Historical Odds for NFL Week
Fetches and saves historical alternate lines for a given week to the appropriate folder
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class HistoricalOddsSaver:
    """Save historical odds data for NFL weeks"""
    
    def __init__(self, api_key: str, base_year: str = "2025"):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.base_year = base_year
        self.requests_used = None
        self.requests_remaining = None
    
    def _update_usage_from_headers(self, headers):
        """Update and display usage statistics from API response headers"""
        self.requests_used = headers.get('x-requests-used')
        self.requests_remaining = headers.get('x-requests-remaining')
        requests_last = headers.get('x-requests-last')
        
        print(f"   💳 Cost: {requests_last} credits | Remaining: {self.requests_remaining}")
    
    def get_week_folder(self, week_number: int) -> str:
        """Get the folder path for a given week"""
        folder = os.path.join(self.base_year, f"WEEK{week_number}")
        os.makedirs(folder, exist_ok=True)
        return folder
    
    def get_historical_events(self, commence_from: str, commence_to: str) -> List[Dict]:
        """
        Fetch historical events for a date range
        
        Args:
            commence_from: Start date in ISO8601 format (e.g., '2025-10-02T00:00:00Z')
            commence_to: End date in ISO8601 format (e.g., '2025-10-07T23:59:59Z')
        
        Returns:
            List of historical event dictionaries
        """
        url = f"{self.base_url}/historical/sports/americanfootball_nfl/events"
        
        # Use the commence_from date as the snapshot date
        params = {
            'apiKey': self.api_key,
            'date': commence_from,
            'commenceTimeFrom': commence_from,
            'commenceTimeTo': commence_to
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            self._update_usage_from_headers(response.headers)
            
            result = response.json()
            events = result.get('data', [])
            
            return events
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching historical events: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return []
    
    def get_historical_event_odds(self,
                                 event_id: str,
                                 date: str,
                                 markets: List[str],
                                 bookmakers: str = 'fanduel') -> Dict:
        """
        Fetch historical odds for a specific event
        
        Args:
            event_id: Historical event ID
            date: Timestamp in ISO8601 format (e.g., '2024-10-03T12:00:00Z')
            markets: List of market keys
            bookmakers: Specific bookmaker (default: 'fanduel')
        
        Returns:
            Historical odds data
        """
        url = f"{self.base_url}/historical/sports/americanfootball_nfl/events/{event_id}/odds"
        
        markets_str = ','.join(markets) if isinstance(markets, list) else markets
        
        params = {
            'apiKey': self.api_key,
            'date': date,
            'regions': 'us',
            'markets': markets_str,
            'oddsFormat': 'american',
            'bookmakers': bookmakers
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            self._update_usage_from_headers(response.headers)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching historical odds for event {event_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return {}
    
    def save_event_data(self, event_data: Dict, week_number: int, event_id: str, game_info: str = "") -> str:
        """
        Save event data to JSON file
        
        Args:
            event_data: Historical odds data
            week_number: Week number
            event_id: Event ID (used as filename prefix)
            game_info: Optional game info for filename (e.g., "TB_ATL")
        
        Returns:
            Path to saved file
        """
        folder = self.get_week_folder(week_number)
        
        # Create filename with event ID prefix
        if game_info:
            filename = f"{event_id}_{game_info}_historical_odds.json"
        else:
            filename = f"{event_id}_historical_odds.json"
        
        filepath = os.path.join(folder, filename)
        
        with open(filepath, 'w') as f:
            json.dump(event_data, f, indent=2)
        
        return filepath
    
    def fetch_and_save_week(self,
                           week_number: int,
                           week_start_date: str,
                           markets: List[str] = None,
                           max_games: int = None,
                           hours_before_game: int = 2) -> Dict:
        """
        Fetch and save historical odds for all games in a week
        
        Args:
            week_number: NFL week number
            week_start_date: Start date of the week (ISO format, e.g., '2024-10-03T00:00:00Z')
            markets: List of markets to fetch (default: all alternate markets)
            max_games: Maximum number of games to fetch (None = all games, use 1 for testing)
            hours_before_game: Hours before game start to fetch odds (default: 2)
        
        Returns:
            Summary dictionary
        """
        if markets is None:
            markets = [
                'player_pass_yds_alternate',
                'player_rush_yds_alternate',
                'player_reception_yds_alternate',
                'player_receptions_alternate',
                'player_pass_tds_alternate',
                'player_rush_tds_alternate',
                'player_reception_tds_alternate'
            ]
        
        # Calculate week end date (typically 6 days after start, to include Monday night)
        start_dt = datetime.fromisoformat(week_start_date.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(days=6)
        week_end_date = end_dt.strftime('%Y-%m-%dT23:59:59Z')
        
        print("=" * 100)
        print(f"🏈 FETCHING HISTORICAL ODDS - WEEK {week_number}")
        print("=" * 100)
        print(f"\n📅 Week Date Range:")
        print(f"   From: {week_start_date}")
        print(f"   To:   {week_end_date}")
        print(f"📊 Markets: {', '.join(markets)}")
        if max_games:
            print(f"⚠️  TEST MODE: Fetching only {max_games} game(s)")
        print()
        
        # Step 1: Get historical events for the week
        print(f"Step 1: Fetching events for week {week_number}...")
        events = self.get_historical_events(week_start_date, week_end_date)
        
        if not events:
            print("❌ No events found for this date")
            return {'success': False, 'error': 'No events found'}
        
        print(f"✅ Found {len(events)} events")
        
        # Limit games if testing
        if max_games:
            events = events[:max_games]
            print(f"   📌 Limited to {len(events)} game(s) for testing")
        
        # Step 2: Fetch and save odds for each event
        print(f"\nStep 2: Fetching historical odds for {len(events)} event(s)...")
        print("-" * 100)
        
        saved_files = []
        total_cost = 0
        
        for idx, event in enumerate(events, 1):
            event_id = event.get('id')
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            commence_time_str = event.get('commence_time', '')
            
            # Create short team names for filename
            home_abbrev = ''.join([word[0] for word in home_team.split()]).upper()
            away_abbrev = ''.join([word[0] for word in away_team.split()]).upper()
            game_info = f"{away_abbrev}_at_{home_abbrev}"
            
            print(f"\n[{idx}/{len(events)}] {away_team} @ {home_team}")
            print(f"   Event ID: {event_id}")
            print(f"   Game Time: {commence_time_str}")
            
            # Calculate odds fetch time (X hours before game)
            try:
                game_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                odds_time = (game_time - timedelta(hours=hours_before_game)).strftime('%Y-%m-%dT%H:%M:%SZ')
                print(f"   Fetching odds from: {odds_time} ({hours_before_game}h before game)")
            except:
                print(f"   ⚠️  Could not parse game time, using week start date")
                odds_time = week_start_date
            
            # Fetch historical odds
            historical_data = self.get_historical_event_odds(
                event_id=event_id,
                date=odds_time,
                markets=markets
            )
            
            if historical_data and 'data' in historical_data:
                # Save to file
                filepath = self.save_event_data(
                    event_data=historical_data,
                    week_number=week_number,
                    event_id=event_id,
                    game_info=game_info
                )
                
                saved_files.append({
                    'event_id': event_id,
                    'game': f"{away_team} @ {home_team}",
                    'filepath': filepath
                })
                
                print(f"   ✅ Saved: {os.path.basename(filepath)}")
            else:
                print(f"   ⚠️  No data available for this event")
            
            # Rate limiting
            if idx < len(events):
                time.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 100)
        print("✅ COMPLETE")
        print("=" * 100)
        print(f"\n📊 Summary:")
        print(f"   Week: {week_number}")
        print(f"   Events Processed: {len(events)}")
        print(f"   Files Saved: {len(saved_files)}")
        print(f"   Location: {self.get_week_folder(week_number)}")
        
        if self.requests_used and self.requests_remaining:
            try:
                used = int(self.requests_used)
                remaining = int(self.requests_remaining)
                print(f"\n💰 API Usage:")
                print(f"   Requests Remaining: {remaining:,}")
                print(f"   Total Used: {used:,}")
            except:
                pass
        
        print(f"\n📁 Saved Files:")
        for file_info in saved_files:
            print(f"   ✓ {os.path.basename(file_info['filepath'])}")
            print(f"     {file_info['game']}")
        
        return {
            'success': True,
            'week': week_number,
            'events_processed': len(events),
            'files_saved': saved_files,
            'folder': self.get_week_folder(week_number)
        }


def get_api_key():
    """Get API key from environment or config"""
    api_key = os.getenv('ODDS_API_KEY')
    if api_key and api_key != 'YOUR_API_KEY_HERE':
        return api_key
    
    try:
        from config import ODDS_API_KEY
        if ODDS_API_KEY and ODDS_API_KEY != 'YOUR_API_KEY_HERE':
            return ODDS_API_KEY
    except:
        pass
    
    api_key = input("Please enter your Odds API key: ").strip()
    return api_key if api_key else None


def main():
    """Main function"""
    from utils import get_week_start_date, get_available_weeks
    
    api_key = get_api_key()
    if not api_key:
        print("❌ Error: No API key provided")
        return
    
    saver = HistoricalOddsSaver(api_key, base_year="2025")
    
    print("\n" + "=" * 100)
    print("🏈 NFL HISTORICAL ODDS SAVER")
    print("=" * 100)
    
    # Show available weeks
    available_weeks = get_available_weeks()
    print(f"\n📅 Available weeks: {', '.join(map(str, available_weeks))}")
    
    # CONFIGURATION - UPDATE THESE VALUES
    week_number = 5  # ← Change this to the week you want
    max_games = 1    # ← Set to None to fetch ALL games, or 1 for testing
    
    # Get week start date from utils
    week_start_date = get_week_start_date(week_number)
    
    if not week_start_date:
        print(f"❌ Error: Week {week_number} not found")
        print(f"   Available weeks: {', '.join(map(str, available_weeks))}")
        return
    
    print(f"\n📊 Week {week_number} Information:")
    print(f"   Start Date: {week_start_date}")
    print(f"   Note: Game count will be determined by the events API (1 credit)")
    
    if max_games == 1:
        print(f"\n🧪 TEST MODE - Fetching only 1 game")
        print(f"   Estimated Cost: ~51 credits (1 for events + 50 for odds)")
    else:
        print(f"\n🚀 FULL MODE - Fetching all games for the week")
        print(f"   Estimated Cost: ~1 credit for events + 50 per game")
    
    # Confirm if fetching all games
    if max_games is None or max_games > 1:
        if max_games is None:
            print(f"\n⚠️  You are about to fetch ALL games for week {week_number}")
        else:
            print(f"\n⚠️  You are about to fetch {max_games} game(s)")
        confirm = input(f"   Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return
    
    # Fetch and save
    result = saver.fetch_and_save_week(
        week_number=week_number,
        week_start_date=week_start_date,
        max_games=max_games,
        hours_before_game=2
    )
    
    if result['success']:
        print(f"\n✅ Complete! Check the folder: {result['folder']}")
        if max_games == 1:
            print(f"\n💡 To fetch ALL games for this week:")
            print(f"   1. Edit the script and change: max_games = None")
            print(f"   2. Re-run the script")


if __name__ == "__main__":
    main()

