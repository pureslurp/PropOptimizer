"""
Data processing module for Player Prop Optimizer
Integrates with existing football data scraping functionality
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
import json
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

class FootballDataProcessor:
    """Enhanced data processor that can integrate with existing football data sources"""
    
    def __init__(self):
        self.team_defensive_stats = {}
        self.player_season_stats = {}
        self.current_week = self._get_current_week()
        
    def _get_current_week(self) -> int:
        """Get current NFL week"""
        # This is a simplified approach - in practice you'd want to check NFL schedule
        current_date = datetime.now()
        # NFL season typically starts first week of September
        season_start = datetime(current_date.year, 9, 1)
        weeks_elapsed = (current_date - season_start).days // 7
        return min(max(1, weeks_elapsed), 18)  # NFL regular season is 18 weeks max
    
    def load_team_defensive_stats_from_footballdb(self, weeks: List[int] = None) -> Dict:
        """
        Load team defensive statistics from FootballDB
        This integrates with the existing scraping functionality
        """
        if weeks is None:
            weeks = list(range(1, self.current_week + 1))
        
        team_stats = {
            'Passing Yards Allowed': {},
            'Rushing Yards Allowed': {},
            'Receiving Yards Allowed': {}
        }
        
        # This would integrate with your existing FootballDBScraper
        # For now, we'll use enhanced mock data based on realistic NFL stats
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
        
        return team_defensive_rankings
    
    def load_player_season_stats_from_footballdb(self, weeks: List[int] = None) -> Dict:
        """
        Load player season statistics from FootballDB
        This integrates with the existing scraping functionality
        """
        if weeks is None:
            weeks = list(range(1, self.current_week + 1))
        
        # Enhanced mock data with more realistic player performance
        player_stats = {
            # Quarterbacks
            'Josh Allen': {
                'Passing Yards': [285, 315, 265, 295, 275],
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
            'Patrick Mahomes': {
                'Passing Yards': [320, 290, 350, 280, 310],
                'Passing TDs': [3, 2, 4, 2, 3],
                'Rushing Yards': [25, 35, 20, 30, 25],
                'Rushing TDs': [0, 1, 0, 1, 0]
            },
            'Dak Prescott': {
                'Passing Yards': [275, 310, 240, 290, 265],
                'Passing TDs': [2, 3, 1, 2, 2],
                'Rushing Yards': [15, 25, 10, 20, 15],
                'Rushing TDs': [0, 1, 0, 0, 0]
            },
            
            # Running Backs
            'Christian McCaffrey': {
                'Rushing Yards': [120, 95, 110, 85, 100],
                'Rushing TDs': [1, 1, 2, 0, 1],
                'Receptions': [5, 3, 6, 4, 5],
                'Receiving Yards': [45, 25, 60, 35, 50]
            },
            'Derrick Henry': {
                'Rushing Yards': [95, 110, 85, 120, 100],
                'Rushing TDs': [1, 2, 1, 1, 1],
                'Receptions': [2, 1, 3, 2, 2],
                'Receiving Yards': [15, 8, 25, 18, 20]
            },
            'Saquon Barkley': {
                'Rushing Yards': [85, 105, 75, 95, 80],
                'Rushing TDs': [1, 1, 0, 2, 1],
                'Receptions': [4, 6, 3, 5, 4],
                'Receiving Yards': [35, 55, 25, 45, 30]
            },
            'Nick Chubb': {
                'Rushing Yards': [110, 85, 95, 105, 90],
                'Rushing TDs': [1, 1, 1, 1, 1],
                'Receptions': [2, 3, 2, 2, 3],
                'Receiving Yards': [20, 35, 25, 30, 40]
            },
            
            # Wide Receivers
            'Cooper Kupp': {
                'Receptions': [8, 6, 9, 7, 8],
                'Receiving Yards': [120, 85, 140, 95, 110],
                'Receiving TDs': [1, 0, 2, 1, 1]
            },
            'Davante Adams': {
                'Receptions': [7, 9, 6, 8, 7],
                'Receiving Yards': [105, 135, 90, 120, 100],
                'Receiving TDs': [1, 2, 0, 1, 1]
            },
            'Tyreek Hill': {
                'Receptions': [6, 8, 5, 7, 6],
                'Receiving Yards': [95, 125, 80, 110, 90],
                'Receiving TDs': [1, 1, 0, 2, 1]
            },
            'Stefon Diggs': {
                'Receptions': [8, 7, 9, 6, 8],
                'Receiving Yards': [115, 95, 130, 85, 105],
                'Receiving TDs': [1, 1, 2, 0, 1]
            },
            'Justin Jefferson': {
                'Receptions': [9, 7, 8, 6, 9],
                'Receiving Yards': [135, 105, 120, 90, 125],
                'Receiving TDs': [1, 1, 1, 0, 2]
            },
            
            # Tight Ends
            'Travis Kelce': {
                'Receptions': [6, 8, 5, 7, 6],
                'Receiving Yards': [85, 115, 70, 95, 80],
                'Receiving TDs': [1, 1, 0, 1, 1]
            },
            'Mark Andrews': {
                'Receptions': [5, 7, 4, 6, 5],
                'Receiving Yards': [70, 95, 60, 85, 75],
                'Receiving TDs': [1, 1, 0, 1, 0]
            },
            'George Kittle': {
                'Receptions': [4, 6, 3, 5, 4],
                'Receiving Yards': [55, 85, 45, 70, 60],
                'Receiving TDs': [0, 1, 0, 1, 0]
            }
        }
        
        return player_stats
    
    def get_team_defensive_rank(self, team: str, stat_type: str) -> int:
        """Get team defensive ranking for a specific stat"""
        if not self.team_defensive_stats:
            self.team_defensive_stats = self.load_team_defensive_stats_from_footballdb()
        
        if stat_type not in self.team_defensive_stats:
            return 16  # Default middle ranking
        
        # Get all teams and their stats for this category
        all_teams = [(team_name, stats) for team_name, stats in self.team_defensive_stats[stat_type].items()]
        all_teams.sort(key=lambda x: x[1])  # Sort by yards allowed (ascending = better defense)
        
        # Find the rank of the specified team
        for i, (team_name, _) in enumerate(all_teams, 1):
            if team_name == team:
                return i
        
        return 16  # Default middle ranking if team not found
    
    def get_player_over_rate(self, player: str, stat_type: str, line: float) -> float:
        """Calculate how often a player has gone over a specific line this season"""
        if not self.player_season_stats:
            self.player_season_stats = self.load_player_season_stats_from_footballdb()
        
        if player not in self.player_season_stats or stat_type not in self.player_season_stats[player]:
            return 0.5  # Default 50% if no data
        
        games = self.player_season_stats[player][stat_type]
        over_count = sum(1 for game_stat in games if game_stat > line)
        
        return over_count / len(games) if games else 0.5
    
    def get_player_average(self, player: str, stat_type: str) -> float:
        """Get player's average for a specific stat this season"""
        if not self.player_season_stats:
            self.player_season_stats = self.load_player_season_stats_from_footballdb()
        
        if player not in self.player_season_stats or stat_type not in self.player_season_stats[player]:
            return 0.0
        
        games = self.player_season_stats[player][stat_type]
        return sum(games) / len(games) if games else 0.0
    
    def get_player_consistency(self, player: str, stat_type: str) -> float:
        """Calculate player consistency (lower standard deviation = more consistent)"""
        if not self.player_season_stats:
            self.player_season_stats = self.load_player_season_stats_from_footballdb()
        
        if player not in self.player_season_stats or stat_type not in self.player_season_stats[player]:
            return 1.0  # Default high variance
        
        games = self.player_season_stats[player][stat_type]
        if len(games) < 2:
            return 1.0
        
        mean_val = sum(games) / len(games)
        variance = sum((x - mean_val) ** 2 for x in games) / len(games)
        return variance ** 0.5  # Standard deviation
