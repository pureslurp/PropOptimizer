#!/usr/bin/env python3
"""
Scrape CBS Sports to calculate actual defensive rankings for verification
"""

import requests
from bs4 import BeautifulSoup
import time
import sys

# NFL team abbreviations used by CBS Sports
NFL_TEAMS = {
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
    'JAC': 'Jacksonville Jaguars',  # CBS uses JAC, not JAX
    'KC': 'Kansas City Chiefs',
    'LAC': 'Los Angeles Chargers',
    'LAR': 'Los Angeles Rams',
    'LV': 'Las Vegas Raiders',
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

def scrape_team_rb_receiving_stats(team_abbr, max_week=None):
    """Scrape RB receiving yards allowed for a specific team through a certain week"""
    
    url = f"https://www.cbssports.com/fantasy/football/stats/posvsdef/RB/{team_abbr}/teambreakdown/standard"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            print(f"  ⚠️  No table found for {team_abbr}")
            return None
        
        # Parse the table to get weekly stats
        total_receiving_yards = 0
        games_count = 0
        weeks_found = []
        
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            
            if not cells or len(cells) < 11:
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
                
                # Receiving yards is in column 8 (0-indexed: 0=Week, 1=Team, 2=Att, 3=Yd, 4=Avg, 5=TD, 6=Targt, 7=Recpt, 8=Yd, 9=Avg, 10=TD)
                receiving_yards_text = cells[8].get_text().strip()
                
                if receiving_yards_text and receiving_yards_text.isdigit():
                    receiving_yards = int(receiving_yards_text)
                    total_receiving_yards += receiving_yards
                
            except (ValueError, IndexError):
                continue
        
        return {
            'team': NFL_TEAMS.get(team_abbr, team_abbr),
            'team_abbr': team_abbr,
            'total_receiving_yards': total_receiving_yards,
            'games': games_count,
            'per_game': total_receiving_yards / games_count if games_count > 0 else 0,
            'weeks': weeks_found
        }
        
    except Exception as e:
        print(f"  ❌ Error scraping {team_abbr}: {e}")
        return None

def calculate_cbs_rankings(position='RB', stat='receiving_yards', max_week=None):
    """Calculate defensive rankings from CBS Sports data"""
    
    print("=" * 80)
    print(f"SCRAPING CBS SPORTS: {position} {stat.replace('_', ' ').title()}")
    if max_week:
        print(f"Through Week {max_week}")
    else:
        print("All available weeks")
    print("=" * 80)
    print()
    
    team_stats = []
    
    for team_abbr, team_name in NFL_TEAMS.items():
        print(f"Scraping {team_name} ({team_abbr})...", end=" ")
        
        stats = scrape_team_rb_receiving_stats(team_abbr, max_week)
        
        if stats:
            team_stats.append(stats)
            print(f"✅ {stats['total_receiving_yards']} yards in {stats['games']} games")
        else:
            print("❌ Failed")
        
        # Be respectful - delay between requests
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
        print(f"{team_data['rank']:<6} {team_data['team']:<35} {team_data['total_receiving_yards']:<12} {team_data['games']:<8} {team_data['per_game']:<10.2f}")
    
    return team_stats

def main():
    max_week = None
    
    if len(sys.argv) > 1:
        max_week = int(sys.argv[1])
        print(f"Calculating rankings through Week {max_week}")
        print()
    
    # Calculate RB receiving yards rankings
    rankings = calculate_cbs_rankings('RB', 'receiving_yards', max_week)
    
    # Highlight specific teams if requested
    if len(sys.argv) > 2:
        highlight_team = sys.argv[2].upper()
        
        print()
        print("=" * 80)
        print(f"VERIFICATION FOR {highlight_team}")
        print("=" * 80)
        
        for team_data in rankings:
            if team_data['team_abbr'] == highlight_team:
                print(f"Team: {team_data['team']}")
                print(f"Rank: {team_data['rank']}")
                print(f"Total RB Receiving Yards Allowed: {team_data['total_receiving_yards']}")
                print(f"Games: {team_data['games']}")
                print(f"Per Game: {team_data['per_game']:.2f}")
                print(f"Weeks: {team_data['weeks']}")
                break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python3 scrape_cbs_rankings.py [max_week] [team_abbr]")
        print()
        print("Examples:")
        print("  python3 scrape_cbs_rankings.py 4 JAC")
        print("  python3 scrape_cbs_rankings.py 5 TB")
        print("  python3 scrape_cbs_rankings.py")
        sys.exit(0)
    
    main()

