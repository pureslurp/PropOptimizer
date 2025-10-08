"""
NFL Defensive Statistics Scraper
Combines NFL.com and ESPN data to provide comprehensive defensive rankings
Run this weekly to update defensive stats for the prop optimizer
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import pickle
import time
import os
from typing import Dict, List, Optional
from datetime import datetime

class DefensiveScraper:
    """
    Unified defensive statistics scraper
    - NFL.com: TD statistics (Passing TDs, Rushing TDs allowed)
    - ESPN: Yards and points statistics
    """
    
    def __init__(self):
        self.nfl_urls = {
            'passing': "https://www.nfl.com/stats/team-stats/defense/passing/2025/reg/all",
            'rushing': "https://www.nfl.com/stats/team-stats/defense/rushing/2025/reg/all"
        }
        self.espn_url = "https://www.espn.com/nfl/stats/team/_/view/defense"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Team name normalization mapping
        self.team_mapping = {
            '49ers': 'San Francisco 49ers',
            'Bears': 'Chicago Bears',
            'Bengals': 'Cincinnati Bengals',
            'Bills': 'Buffalo Bills',
            'Broncos': 'Denver Broncos',
            'Browns': 'Cleveland Browns',
            'Buccaneers': 'Tampa Bay Buccaneers',
            'Cardinals': 'Arizona Cardinals',
            'Chargers': 'Los Angeles Chargers',
            'Chiefs': 'Kansas City Chiefs',
            'Colts': 'Indianapolis Colts',
            'Commanders': 'Washington Commanders',
            'Cowboys': 'Dallas Cowboys',
            'Dolphins': 'Miami Dolphins',
            'Eagles': 'Philadelphia Eagles',
            'Falcons': 'Atlanta Falcons',
            'Giants': 'New York Giants',
            'Jaguars': 'Jacksonville Jaguars',
            'Jets': 'New York Jets',
            'Lions': 'Detroit Lions',
            'Packers': 'Green Bay Packers',
            'Panthers': 'Carolina Panthers',
            'Patriots': 'New England Patriots',
            'Raiders': 'Las Vegas Raiders',
            'Rams': 'Los Angeles Rams',
            'Ravens': 'Baltimore Ravens',
            'Saints': 'New Orleans Saints',
            'Seahawks': 'Seattle Seahawks',
            'Steelers': 'Pittsburgh Steelers',
            'Texans': 'Houston Texans',
            'Titans': 'Tennessee Titans',
            'Vikings': 'Minnesota Vikings'
        }
    
    def scrape_nfl_td_stats(self) -> Dict[str, Dict[str, int]]:
        """Scrape TD statistics from NFL.com"""
        print("🔄 Scraping NFL.com TD statistics...")
        
        try:
            defensive_stats = {}
            
            # Scrape passing defense TDs
            passing_tds = self._scrape_nfl_passing_tds()
            if passing_tds:
                defensive_stats.update(passing_tds)
            
            # Scrape rushing defense TDs
            rushing_tds = self._scrape_nfl_rushing_tds()
            if rushing_tds:
                for team, stats in rushing_tds.items():
                    if team in defensive_stats:
                        defensive_stats[team].update(stats)
                    else:
                        defensive_stats[team] = stats
            
            print(f"✅ Scraped NFL.com TD stats for {len(defensive_stats)} teams")
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping NFL.com TD stats: {e}")
            return {}
    
    def _scrape_nfl_passing_tds(self) -> Dict[str, Dict[str, int]]:
        """Scrape passing defense TD statistics from NFL.com"""
        try:
            response = requests.get(self.nfl_urls['passing'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='d3-o-table')
            
            if not table:
                print("⚠️ Could not find passing defense table")
                return {}
            
            defensive_stats = {}
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    team_name = self._extract_nfl_team_name(cells[0])
                    if team_name:
                        try:
                            td_count = int(cells[6].get_text(strip=True))
                            if team_name not in defensive_stats:
                                defensive_stats[team_name] = {}
                            defensive_stats[team_name]['Passing TDs Allowed'] = td_count
                        except (ValueError, IndexError):
                            continue
            
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping passing TDs: {e}")
            return {}
    
    def _scrape_nfl_rushing_tds(self) -> Dict[str, Dict[str, int]]:
        """Scrape rushing defense TD statistics from NFL.com"""
        try:
            response = requests.get(self.nfl_urls['rushing'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='d3-o-table')
            
            if not table:
                print("⚠️ Could not find rushing defense table")
                return {}
            
            defensive_stats = {}
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 5:
                    team_name = self._extract_nfl_team_name(cells[0])
                    if team_name:
                        try:
                            td_count = int(cells[4].get_text(strip=True))
                            if team_name not in defensive_stats:
                                defensive_stats[team_name] = {}
                            defensive_stats[team_name]['Rushing TDs Allowed'] = td_count
                        except (ValueError, IndexError):
                            continue
            
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping rushing TDs: {e}")
            return {}
    
    def _extract_nfl_team_name(self, team_cell) -> Optional[str]:
        """Extract team name from NFL.com table cell"""
        try:
            club_info = team_cell.find('div', class_='d3-o-club-info')
            if club_info:
                fullname_div = club_info.find('div', class_='d3-o-club-fullname')
                if fullname_div:
                    team_name = fullname_div.get_text(strip=True)
                    return self.team_mapping.get(team_name, team_name)
            
            team_text = team_cell.get_text(strip=True)
            if team_text:
                return self.team_mapping.get(team_text, team_text)
                
        except Exception as e:
            print(f"⚠️ Error extracting team name: {e}")
        
        return None
    
    def get_espn_defensive_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get ESPN defensive statistics
        Note: Currently using manual data. Can be updated to scrape live ESPN data.
        """
        print("🔄 Loading ESPN defensive statistics...")
        
        # Using manual ESPN data (accurate as of week data was collected)
        # Update this periodically or implement live scraping
        defensive_stats = {
            'Atlanta Falcons': {'total_yards_per_game': 244.0, 'passing_yards_per_game': 135.0, 'rushing_yards_per_game': 109.0, 'points_allowed_per_game': 21.5},
            'Cleveland Browns': {'total_yards_per_game': 247.8, 'passing_yards_per_game': 172.2, 'rushing_yards_per_game': 75.6, 'points_allowed_per_game': 24.6},
            'Houston Texans': {'total_yards_per_game': 265.8, 'passing_yards_per_game': 175.2, 'rushing_yards_per_game': 90.6, 'points_allowed_per_game': 12.2},
            'Green Bay Packers': {'total_yards_per_game': 283.3, 'passing_yards_per_game': 205.8, 'rushing_yards_per_game': 77.5, 'points_allowed_per_game': 21.0},
            'Denver Broncos': {'total_yards_per_game': 288.6, 'passing_yards_per_game': 200.2, 'rushing_yards_per_game': 88.4, 'points_allowed_per_game': 16.8},
            'Minnesota Vikings': {'total_yards_per_game': 289.8, 'passing_yards_per_game': 157.6, 'rushing_yards_per_game': 132.2, 'points_allowed_per_game': 19.4},
            'Los Angeles Chargers': {'total_yards_per_game': 293.8, 'passing_yards_per_game': 172.2, 'rushing_yards_per_game': 121.6, 'points_allowed_per_game': 19.6},
            'Detroit Lions': {'total_yards_per_game': 298.8, 'passing_yards_per_game': 206.6, 'rushing_yards_per_game': 92.2, 'points_allowed_per_game': 22.4},
            'Buffalo Bills': {'total_yards_per_game': 299.6, 'passing_yards_per_game': 154.0, 'rushing_yards_per_game': 145.6, 'points_allowed_per_game': 22.6},
            'Los Angeles Rams': {'total_yards_per_game': 309.0, 'passing_yards_per_game': 215.4, 'rushing_yards_per_game': 93.6, 'points_allowed_per_game': 21.4},
            'Tampa Bay Buccaneers': {'total_yards_per_game': 310.8, 'passing_yards_per_game': 218.4, 'rushing_yards_per_game': 92.4, 'points_allowed_per_game': 26.4},
            'Carolina Panthers': {'total_yards_per_game': 311.6, 'passing_yards_per_game': 204.4, 'rushing_yards_per_game': 107.2, 'points_allowed_per_game': 23.8},
            'Kansas City Chiefs': {'total_yards_per_game': 314.0, 'passing_yards_per_game': 190.6, 'rushing_yards_per_game': 123.4, 'points_allowed_per_game': 21.4},
            'Indianapolis Colts': {'total_yards_per_game': 315.0, 'passing_yards_per_game': 217.0, 'rushing_yards_per_game': 98.0, 'points_allowed_per_game': 17.8},
            'San Francisco 49ers': {'total_yards_per_game': 315.6, 'passing_yards_per_game': 207.6, 'rushing_yards_per_game': 108.0, 'points_allowed_per_game': 19.6},
            'Seattle Seahawks': {'total_yards_per_game': 322.8, 'passing_yards_per_game': 239.8, 'rushing_yards_per_game': 83.0, 'points_allowed_per_game': 21.0},
            'New Orleans Saints': {'total_yards_per_game': 326.2, 'passing_yards_per_game': 204.0, 'rushing_yards_per_game': 122.2, 'points_allowed_per_game': 27.0},
            'New England Patriots': {'total_yards_per_game': 327.8, 'passing_yards_per_game': 242.2, 'rushing_yards_per_game': 85.6, 'points_allowed_per_game': 20.2},
            'Las Vegas Raiders': {'total_yards_per_game': 328.2, 'passing_yards_per_game': 226.8, 'rushing_yards_per_game': 101.4, 'points_allowed_per_game': 27.8},
            'Philadelphia Eagles': {'total_yards_per_game': 338.2, 'passing_yards_per_game': 211.4, 'rushing_yards_per_game': 126.8, 'points_allowed_per_game': 21.8},
            'Arizona Cardinals': {'total_yards_per_game': 346.6, 'passing_yards_per_game': 254.2, 'rushing_yards_per_game': 92.4, 'points_allowed_per_game': 19.2},
            'New York Jets': {'total_yards_per_game': 347.4, 'passing_yards_per_game': 207.0, 'rushing_yards_per_game': 140.4, 'points_allowed_per_game': 31.4},
            'Jacksonville Jaguars': {'total_yards_per_game': 348.2, 'passing_yards_per_game': 250.4, 'rushing_yards_per_game': 97.8, 'points_allowed_per_game': 20.0},
            'Washington Commanders': {'total_yards_per_game': 352.0, 'passing_yards_per_game': 235.0, 'rushing_yards_per_game': 117.0, 'points_allowed_per_game': 20.2},
            'Tennessee Titans': {'total_yards_per_game': 366.8, 'passing_yards_per_game': 220.0, 'rushing_yards_per_game': 146.8, 'points_allowed_per_game': 28.2},
            'New York Giants': {'total_yards_per_game': 377.2, 'passing_yards_per_game': 237.2, 'rushing_yards_per_game': 140.0, 'points_allowed_per_game': 25.4},
            'Chicago Bears': {'total_yards_per_game': 379.5, 'passing_yards_per_game': 215.0, 'rushing_yards_per_game': 164.5, 'points_allowed_per_game': 29.3},
            'Pittsburgh Steelers': {'total_yards_per_game': 382.5, 'passing_yards_per_game': 260.5, 'rushing_yards_per_game': 122.0, 'points_allowed_per_game': 24.5},
            'Miami Dolphins': {'total_yards_per_game': 386.6, 'passing_yards_per_game': 212.4, 'rushing_yards_per_game': 174.2, 'points_allowed_per_game': 29.0},
            'Cincinnati Bengals': {'total_yards_per_game': 391.2, 'passing_yards_per_game': 259.0, 'rushing_yards_per_game': 132.2, 'points_allowed_per_game': 31.2},
            'Baltimore Ravens': {'total_yards_per_game': 408.8, 'passing_yards_per_game': 262.6, 'rushing_yards_per_game': 146.4, 'points_allowed_per_game': 35.4},
            'Dallas Cowboys': {'total_yards_per_game': 412.0, 'passing_yards_per_game': 284.6, 'rushing_yards_per_game': 127.4, 'points_allowed_per_game': 30.8}
        }
        
        print(f"✅ Loaded ESPN defensive stats for {len(defensive_stats)} teams")
        return defensive_stats
    
    def calculate_rankings(self, espn_stats: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, int]]:
        """Calculate defensive rankings from ESPN stats"""
        rankings = {}
        
        # Categories to rank (lower is better for defense)
        categories = {
            'total_yards_per_game': 'Total Yards Allowed',
            'passing_yards_per_game': 'Passing Yards Allowed',
            'rushing_yards_per_game': 'Rushing Yards Allowed',
            'points_allowed_per_game': 'Points Allowed'
        }
        
        for category, display_name in categories.items():
            # Sort teams by this category (ascending = better defense)
            sorted_teams = sorted(
                espn_stats.items(),
                key=lambda x: x[1].get(category, 999)
            )
            
            # Assign rankings (1 = best defense)
            for rank, (team_name, _) in enumerate(sorted_teams, 1):
                if team_name not in rankings:
                    rankings[team_name] = {}
                rankings[team_name][display_name] = rank
        
        return rankings
    
    def combine_defensive_data(self, nfl_td_stats: Dict, espn_rankings: Dict) -> Dict:
        """Combine NFL.com TD stats and ESPN rankings"""
        combined = {}
        
        # Start with all teams from ESPN rankings
        for team, rankings in espn_rankings.items():
            combined[team] = rankings.copy()
        
        # Add TD stats from NFL.com
        for team, td_stats in nfl_td_stats.items():
            if team not in combined:
                combined[team] = {}
            combined[team].update(td_stats)
        
        return combined
    
    def save_to_cache(self, data: Dict, td_cache_file: str = "data/nfl_defensive_td_cache.pkl", 
                     rankings_cache_file: str = "data/espn_defensive_rankings.json"):
        """Save defensive data to cache files"""
        try:
            os.makedirs("data", exist_ok=True)
            
            # Save TD stats (pickle format for compatibility)
            td_stats = {team: {k: v for k, v in stats.items() if 'TDs Allowed' in k} 
                       for team, stats in data.items()}
            with open(td_cache_file, 'wb') as f:
                pickle.dump(td_stats, f)
            print(f"💾 Saved TD stats to {td_cache_file}")
            
            # Save full rankings (JSON format)
            with open(rankings_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved defensive rankings to {rankings_cache_file}")
            
        except Exception as e:
            print(f"⚠️ Could not save cache: {e}")
    
    def load_from_cache(self, td_cache_file: str = "data/nfl_defensive_td_cache.pkl",
                       rankings_cache_file: str = "data/espn_defensive_rankings.json") -> Optional[Dict]:
        """Load defensive data from cache"""
        try:
            # Try to load from JSON first (has complete data)
            if os.path.exists(rankings_cache_file):
                with open(rankings_cache_file, 'r') as f:
                    data = json.load(f)
                print(f"📁 Loaded defensive data from cache")
                return data
        except Exception as e:
            print(f"⚠️ Could not load from cache: {e}")
        
        return None
    
    def update_defensive_stats(self, force_refresh: bool = False) -> Dict:
        """
        Main method to update all defensive statistics
        Run this weekly to refresh data
        """
        print("=" * 60)
        print("🏈 NFL Defensive Statistics Update")
        print("=" * 60)
        
        if not force_refresh:
            cached_data = self.load_from_cache()
            if cached_data:
                print("✅ Using cached defensive data (use --force to refresh)")
                return cached_data
        
        # Scrape NFL.com TD stats
        nfl_td_stats = self.scrape_nfl_td_stats()
        time.sleep(1)  # Rate limiting
        
        # Get ESPN stats
        espn_stats = self.get_espn_defensive_stats()
        
        # Calculate rankings from ESPN stats
        espn_rankings = self.calculate_rankings(espn_stats)
        
        # Combine all data
        combined_data = self.combine_defensive_data(nfl_td_stats, espn_rankings)
        
        # Save to cache
        self.save_to_cache(combined_data)
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully updated defensive stats for {len(combined_data)} teams")
        print("=" * 60)
        
        return combined_data


def main():
    """Command-line interface for updating defensive stats"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update NFL Defensive Statistics')
    parser.add_argument('--force', action='store_true', help='Force refresh even if cache exists')
    parser.add_argument('--show', action='store_true', help='Display the rankings after update')
    
    args = parser.parse_args()
    
    scraper = DefensiveScraper()
    data = scraper.update_defensive_stats(force_refresh=args.force)
    
    if args.show and data:
        print("\n📊 Defensive Rankings Sample:")
        print("=" * 60)
        
        # Show top 5 teams in each category
        for team in sorted(data.keys())[:5]:
            print(f"\n{team}:")
            for stat, value in data[team].items():
                print(f"  {stat}: {value}")
        
        print(f"\n✅ Complete data for {len(data)} teams")


if __name__ == "__main__":
    main()

