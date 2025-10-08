"""
NFL.com Defensive Statistics Scraper
Scrapes team defensive TD statistics from NFL.com stats pages
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import os
from typing import Dict, List, Optional
import re

class NFLDefensiveScraper:
    """Scrape team defensive TD statistics from NFL.com"""
    
    def __init__(self):
        self.base_urls = {
            'passing': "https://www.nfl.com/stats/team-stats/defense/passing/2025/reg/all",
            'rushing': "https://www.nfl.com/stats/team-stats/defense/rushing/2025/reg/all"
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def scrape_defensive_td_stats(self) -> Dict[str, Dict[str, int]]:
        """Scrape defensive TD statistics from NFL.com"""
        try:
            print("🔄 Scraping NFL.com defensive TD statistics...")
            
            defensive_stats = {}
            
            # Scrape passing defense TDs
            passing_tds = self._scrape_passing_defense_tds()
            if passing_tds:
                defensive_stats.update(passing_tds)
            
            # Scrape rushing defense TDs  
            rushing_tds = self._scrape_rushing_defense_tds()
            if rushing_tds:
                # Merge rushing TDs with existing data
                for team, stats in rushing_tds.items():
                    if team in defensive_stats:
                        defensive_stats[team].update(stats)
                    else:
                        defensive_stats[team] = stats
            
            print(f"✅ Successfully scraped defensive TD stats for {len(defensive_stats)} teams")
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping NFL.com defensive TD stats: {e}")
            return {}
    
    def _scrape_passing_defense_tds(self) -> Dict[str, Dict[str, int]]:
        """Scrape passing defense TD statistics"""
        try:
            response = requests.get(self.base_urls['passing'], headers=self.headers)
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
                if len(cells) >= 6:  # Ensure we have enough columns
                    # Extract team name from the first cell
                    team_cell = cells[0]
                    team_name = self._extract_team_name(team_cell)
                    
                    if team_name:
                        # TD column is the 7th column (index 6) for passing defense
                        if len(cells) > 6:
                            td_cell = cells[6]
                            td_text = td_cell.get_text(strip=True)
                        else:
                            continue
                        
                        try:
                            td_count = int(td_text)
                            if team_name not in defensive_stats:
                                defensive_stats[team_name] = {}
                            defensive_stats[team_name]['Passing TDs Allowed'] = td_count
                        except ValueError:
                            print(f"⚠️ Could not parse TD count for {team_name}: {td_text}")
            
            print(f"✅ Scraped passing defense TDs for {len(defensive_stats)} teams")
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping passing defense TDs: {e}")
            return {}
    
    def _scrape_rushing_defense_tds(self) -> Dict[str, Dict[str, int]]:
        """Scrape rushing defense TD statistics"""
        try:
            response = requests.get(self.base_urls['rushing'], headers=self.headers)
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
                if len(cells) >= 5:  # Ensure we have enough columns
                    # Extract team name from the first cell
                    team_cell = cells[0]
                    team_name = self._extract_team_name(team_cell)
                    
                    if team_name:
                        # TD column is the 5th column (index 4) for rushing defense
                        if len(cells) > 4:
                            td_cell = cells[4]
                            td_text = td_cell.get_text(strip=True)
                        else:
                            continue
                        
                        try:
                            td_count = int(td_text)
                            if team_name not in defensive_stats:
                                defensive_stats[team_name] = {}
                            defensive_stats[team_name]['Rushing TDs Allowed'] = td_count
                        except ValueError:
                            print(f"⚠️ Could not parse TD count for {team_name}: {td_text}")
            
            print(f"✅ Scraped rushing defense TDs for {len(defensive_stats)} teams")
            return defensive_stats
            
        except Exception as e:
            print(f"❌ Error scraping rushing defense TDs: {e}")
            return {}
    
    def _extract_team_name(self, team_cell) -> Optional[str]:
        """Extract team name from the team cell"""
        try:
            # Look for the team name in the club info div
            club_info = team_cell.find('div', class_='d3-o-club-info')
            if club_info:
                fullname_div = club_info.find('div', class_='d3-o-club-fullname')
                if fullname_div:
                    team_name = fullname_div.get_text(strip=True)
                    # Map to standard team names used in the system
                    return self._normalize_team_name(team_name)
            
            # Fallback: try to get text directly
            team_text = team_cell.get_text(strip=True)
            if team_text:
                return self._normalize_team_name(team_text)
                
        except Exception as e:
            print(f"⚠️ Error extracting team name: {e}")
        
        return None
    
    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team names to match the system's naming convention"""
        team_mapping = {
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
        
        return team_mapping.get(team_name, team_name)
    
    def get_defensive_td_rankings(self, force_refresh: bool = False) -> Dict[str, Dict[str, int]]:
        """Get defensive TD rankings with caching"""
        cache_file = "data/nfl_defensive_td_cache.pkl"
        
        if not force_refresh:
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    print("📁 Loaded cached NFL defensive TD data")
                    return cached_data
            except:
                pass
        
        # Scrape fresh data
        defensive_stats = self.scrape_defensive_td_stats()
        
        if defensive_stats:
            # Cache the data
            try:
                import pickle
                os.makedirs("data", exist_ok=True)
                with open(cache_file, 'wb') as f:
                    pickle.dump(defensive_stats, f)
                print(f"💾 Cached NFL defensive TD data to {cache_file}")
            except Exception as e:
                print(f"⚠️ Could not cache data: {e}")
        
        return defensive_stats

if __name__ == "__main__":
    scraper = NFLDefensiveScraper()
    rankings = scraper.get_defensive_td_rankings(force_refresh=True)
    print(json.dumps(rankings, indent=2))
