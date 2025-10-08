"""
Final Working Odds API Alternate Player Props Fetcher

This script successfully fetches alternate NFL player props using the correct approach
discovered from player_prop_optimizer.py.
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import time

class WorkingAlternatePropsAPI:
    def __init__(self, api_key: str):
        """Initialize the Odds API client"""
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.headers = {
            'User-Agent': 'PropOptimizer/1.0'
        }
    
    def get_nfl_events(self) -> List[Dict]:
        """Get NFL events"""
        url = f"{self.base_url}/sports/americanfootball_nfl/events"
        params = {
            'apiKey': self.api_key,
            'regions': 'us'
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching NFL events: {e}")
            return []
    
    def get_alternate_passing_yards(self, event_ids: List[str] = None, bookmaker: str = 'fanduel') -> Dict:
        """
        Get alternate passing yards props for specific events
        
        Args:
            event_ids (List[str]): List of event IDs to fetch. If None, will get all events.
            bookmaker (str): Bookmaker to use (default: 'fanduel')
            
        Returns:
            Dict: Combined data with events and their alternate passing yards odds
        """
        if event_ids is None:
            events = self.get_nfl_events()
            if not events:
                return {'error': 'No NFL events found'}
            event_ids = [event['id'] for event in events]
        
        print(f"Fetching alternate passing yards for {len(event_ids)} events...")
        
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'market': 'player_pass_yds_alternate',
            'bookmaker': bookmaker,
            'events': [],
            'errors': []
        }
        
        for event_id in event_ids:
            print(f"Fetching odds for event: {event_id}")
            
            # Use the working endpoint structure
            odds_url = f"{self.base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
            odds_params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'bookmakers': bookmaker,
                'markets': 'player_pass_yds_alternate',
                'oddsFormat': 'american',
                'includeAltLines': 'true'
            }
            
            try:
                response = requests.get(odds_url, params=odds_params, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    event_data = response.json()
                    
                    # Check if this event has alternate passing yards props
                    has_alternate_props = False
                    for bookmaker_data in event_data.get('bookmakers', []):
                        if bookmaker_data.get('key') == bookmaker:
                            for market in bookmaker_data.get('markets', []):
                                if market.get('key') == 'player_pass_yds_alternate' and market.get('outcomes'):
                                    has_alternate_props = True
                                    break
                            break
                    
                    if has_alternate_props:
                        all_data['events'].append(event_data)
                        print(f"✅ Successfully fetched data")
                    else:
                        print(f"⚠️ No alternate props found for this event")
                else:
                    error_info = {
                        'event_id': event_id,
                        'status_code': response.status_code,
                        'error': response.text[:200]
                    }
                    all_data['errors'].append(error_info)
                    print(f"❌ Failed: {response.status_code}")
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                error_info = {
                    'event_id': event_id,
                    'error': str(e)
                }
                all_data['errors'].append(error_info)
                print(f"❌ Exception: {e}")
        
        return all_data
    
    def get_multiple_alternate_props(self, markets: List[str], event_ids: List[str] = None, bookmaker: str = 'fanduel') -> Dict:
        """
        Get multiple alternate player props for specific events
        
        Args:
            markets (List[str]): List of market keys to fetch
            event_ids (List[str]): List of event IDs to fetch. If None, will get all events.
            bookmaker (str): Bookmaker to use (default: 'fanduel')
            
        Returns:
            Dict: Combined data with events and their alternate props
        """
        if event_ids is None:
            events = self.get_nfl_events()
            if not events:
                return {'error': 'No NFL events found'}
            event_ids = [event['id'] for event in events]
        
        print(f"Fetching alternate props for {len(event_ids)} events...")
        print(f"Markets: {markets}")
        
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'markets': markets,
            'bookmaker': bookmaker,
            'events': [],
            'errors': []
        }
        
        for event_id in event_ids:
            print(f"Fetching odds for event: {event_id}")
            
            # Use the working endpoint structure
            odds_url = f"{self.base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
            odds_params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'bookmakers': bookmaker,
                'markets': ','.join(markets),
                'oddsFormat': 'american',
                'includeAltLines': 'true'
            }
            
            try:
                response = requests.get(odds_url, params=odds_params, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    event_data = response.json()
                    
                    # Check if this event has any of the requested markets
                    has_alternate_props = False
                    for bookmaker_data in event_data.get('bookmakers', []):
                        if bookmaker_data.get('key') == bookmaker:
                            for market in bookmaker_data.get('markets', []):
                                if market.get('key') in markets and market.get('outcomes'):
                                    has_alternate_props = True
                                    break
                            break
                    
                    if has_alternate_props:
                        all_data['events'].append(event_data)
                        print(f"✅ Successfully fetched data")
                    else:
                        print(f"⚠️ No alternate props found for this event")
                else:
                    error_info = {
                        'event_id': event_id,
                        'status_code': response.status_code,
                        'error': response.text[:200]
                    }
                    all_data['errors'].append(error_info)
                    print(f"❌ Failed: {response.status_code}")
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                error_info = {
                    'event_id': event_id,
                    'error': str(e)
                }
                all_data['errors'].append(error_info)
                print(f"❌ Exception: {e}")
        
        return all_data
    
    def save_to_json(self, data: Dict, filename: str = None) -> str:
        """Save data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alternate_props_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data saved to: {filepath}")
        return filepath
    
    def analyze_results(self, data: Dict) -> Dict:
        """Analyze the results and provide insights"""
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

def main():
    """Main function demonstrating the working approach"""
    from config import ODDS_API_KEY
    
    if ODDS_API_KEY == "YOUR_API_KEY_HERE":
        print("Please set your Odds API key in config.py or as an environment variable")
        return
    
    api_client = WorkingAlternatePropsAPI(ODDS_API_KEY)
    
    print("Working Odds API Alternate Player Props Fetcher")
    print("=" * 60)
    print("✅ Uses the correct endpoint structure from player_prop_optimizer.py")
    print("✅ Successfully fetches alternate player props")
    print("✅ Includes proper error handling and analysis")
    print()
    
    # Example 1: Fetch alternate passing yards for all events
    print("Example 1: Fetching alternate passing yards...")
    passing_data = api_client.get_alternate_passing_yards()
    
    if passing_data and not passing_data.get('error'):
        filepath = api_client.save_to_json(passing_data, "alternate_passing_yards.json")
        analysis = api_client.analyze_results(passing_data)
        
        print(f"\nResults Analysis:")
        print(f"  Events attempted: {analysis['total_events_attempted']}")
        print(f"  Successful: {analysis['successful_events']}")
        print(f"  Failed: {analysis['failed_events']}")
        print(f"  Total outcomes: {analysis['total_outcomes']}")
        print(f"  Players found: {len(analysis['players_found'])}")
        print(f"  Market summary: {analysis['market_summary']}")
        
        if analysis['players_found']:
            print(f"\nSample players:")
            for player in list(analysis['players_found'])[:5]:
                print(f"  - {player}")
    else:
        print("❌ No alternate passing yards data found")
    
    # Example 2: Fetch multiple alternate props (commented out to avoid too many API calls)
    # print("\nExample 2: Fetching multiple alternate props...")
    # markets = ['player_pass_yds_alternate', 'player_rush_yds_alternate', 'player_receptions_alternate']
    # combined_data = api_client.get_multiple_alternate_props(markets)
    # if combined_data and not combined_data.get('error'):
    #     filepath = api_client.save_to_json(combined_data, "multiple_alternate_props.json")
    #     analysis = api_client.analyze_results(combined_data)
    #     print(f"Multiple props analysis: {analysis}")
    
    print(f"\nScript completed. Check the saved JSON files for detailed results.")

if __name__ == "__main__":
    main()
