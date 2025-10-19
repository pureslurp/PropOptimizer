#!/usr/bin/env python3
"""
Scrape CBS Sports to calculate QB rushing yards defensive rankings
"""

import requests
from bs4 import BeautifulSoup
import time
import sys

# NFL team abbreviations used by CBS Sports
NFL_TEAMS = {
    'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
    'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
    'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
    'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAC': 'Jacksonville Jaguars',
    'KC': 'Kansas City Chiefs', 'LAC': 'Los Angeles Chargers', 'LAR': 'Los Angeles Rams',
    'LV': 'Las Vegas Raiders', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
    'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
    'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
    'SF': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers',
    'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'
}

def scrape_team_qb_rushing_stats(team_abbr, max_week=None):
    """Scrape QB rushing yards allowed for a specific team through a certain week"""
    
    # Note: CBS uses QB instead of QBS for the position
    url = f"https://www.cbssports.com/fantasy/football/stats/posvsdef/QB/{team_abbr}/teambreakdown/standard"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            return None
        
        # Parse the table to get weekly stats
        total_rushing_yards = 0
        games_count = 0
        weeks_found = []
        
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            
            if not cells or len(cells) < 14:
                continue
            
            # First cell is week number or "Average" or "Season"
            week_cell = cells[0].get_text().strip()
            
            # Skip Average and Season rows
            if week_cell in ['Average', 'Season']:
                continue
            
            # Try to parse week number
            try:
                week_num = int(week_cell)
                
                # If max_week specified, only count up to that week
                if max_week and week_num > max_week:
                    continue
                
                weeks_found.append(week_num)
                games_count += 1
                
                # For QB table: 0=Week, 1=Team, 2-7=Passing stats, 8=Rush Att, 9=Rush Yd, 10=Rush Avg, 11=Rush TD, 12=FL, 13=FPTS
                # Rushing yards is in column 9
                rushing_yards_text = cells[9].get_text().strip()
                
                if rushing_yards_text and rushing_yards_text.lstrip('-').isdigit():
                    rushing_yards = int(rushing_yards_text)
                    total_rushing_yards += rushing_yards
                
            except (ValueError, IndexError) as e:
                continue
        
        return {
            'team': NFL_TEAMS.get(team_abbr, team_abbr),
            'team_abbr': team_abbr,
            'total_rushing_yards': total_rushing_yards,
            'games': games_count,
            'per_game': total_rushing_yards / games_count if games_count > 0 else 0,
            'weeks': weeks_found
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def main():
    max_week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    highlight_team = sys.argv[2].upper() if len(sys.argv) > 2 else None
    
    print("=" * 80)
    print("SCRAPING CBS SPORTS: QB Rushing Yards")
    if max_week:
        print(f"Through Week {max_week}")
    print("=" * 80)
    print()
    
    team_stats = []
    
    for team_abbr, team_name in NFL_TEAMS.items():
        print(f"Scraping {team_name} ({team_abbr})...", end=" ")
        
        stats = scrape_team_qb_rushing_stats(team_abbr, max_week)
        
        if stats:
            team_stats.append(stats)
            print(f"✅ {stats['total_rushing_yards']} yards in {stats['games']} games")
        else:
            print("❌ Failed")
        
        time.sleep(0.5)
    
    print()
    print("=" * 80)
    print("RANKINGS")
    print("=" * 80)
    print()
    
    # Sort by per-game yards (ascending = best defense = rank 1)
    team_stats.sort(key=lambda x: x['per_game'])
    
    # Assign ranks
    for rank, team_data in enumerate(team_stats, 1):
        team_data['rank'] = rank
    
    # Display rankings
    print(f"{'Rank':<6} {'Team':<35} {'Total Yds':<12} {'Games':<8} {'Per Game':<10}")
    print("-" * 80)
    
    for team_data in team_stats:
        print(f"{team_data['rank']:<6} {team_data['team']:<35} {team_data['total_rushing_yards']:<12} {team_data['games']:<8} {team_data['per_game']:<10.2f}")
    
    # Highlight specific team
    if highlight_team:
        print()
        print("=" * 80)
        print(f"VERIFICATION FOR {highlight_team}")
        print("=" * 80)
        
        for team_data in team_stats:
            if team_data['team_abbr'] == highlight_team:
                print(f"Team: {team_data['team']}")
                print(f"Rank: {team_data['rank']}")
                print(f"Total QB Rushing Yards Allowed: {team_data['total_rushing_yards']}")
                print(f"Games: {team_data['games']}")
                print(f"Per Game: {team_data['per_game']:.2f}")
                print(f"Weeks: {team_data['weeks']}")
                break

if __name__ == "__main__":
    main()

