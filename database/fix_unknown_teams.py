#!/usr/bin/env python3
"""
Fix props with Unknown team by looking up from player_positions table
"""

from .database_manager import DatabaseManager
from .database_models import Prop, PlayerPosition
from utils import clean_player_name

def fix_unknown_teams(week=None):
    db_manager = DatabaseManager()
    
    # Team abbreviation mapping
    team_name_mapping = {
        'PHI': 'Philadelphia Eagles', 'NYG': 'New York Giants', 'DAL': 'Dallas Cowboys',
        'WAS': 'Washington Commanders', 'SF': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks',
        'LAR': 'Los Angeles Rams', 'ARI': 'Arizona Cardinals', 'GB': 'Green Bay Packers',
        'MIN': 'Minnesota Vikings', 'DET': 'Detroit Lions', 'CHI': 'Chicago Bears',
        'TB': 'Tampa Bay Buccaneers', 'NO': 'New Orleans Saints', 'ATL': 'Atlanta Falcons',
        'CAR': 'Carolina Panthers', 'KC': 'Kansas City Chiefs', 'LV': 'Las Vegas Raiders',
        'LAC': 'Los Angeles Chargers', 'DEN': 'Denver Broncos', 'BUF': 'Buffalo Bills',
        'MIA': 'Miami Dolphins', 'NE': 'New England Patriots', 'NYJ': 'New York Jets',
        'BAL': 'Baltimore Ravens', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns',
        'PIT': 'Pittsburgh Steelers', 'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts',
        'JAX': 'Jacksonville Jaguars', 'TEN': 'Tennessee Titans'
    }
    team_abbrev_mapping = {v: k for k, v in team_name_mapping.items()}
    
    print("=" * 80)
    print("FIXING PROPS WITH UNKNOWN TEAM")
    if week:
        print(f"Week {week}")
    else:
        print("All weeks")
    print("=" * 80)
    print()
    
    with db_manager.get_session() as session:
        # Find props with Unknown team
        query = session.query(Prop).filter(Prop.player_team == 'Unknown')
        if week:
            query = query.filter(Prop.week == week)
        
        unknown_props = query.all()
        
        print(f"Found {len(unknown_props)} props with Unknown team")
        print()
        
        fixed_count = 0
        player_teams = {}  # Cache player teams
        
        for prop in unknown_props:
            player = prop.player
            
            # Check cache first
            if player in player_teams:
                team = player_teams[player]
            else:
                # Look up in player_positions table
                cleaned = clean_player_name(player)
                
                # Try exact match first
                player_pos = session.query(PlayerPosition).filter(
                    PlayerPosition.player == player
                ).first()
                
                # Try cleaned name match if exact fails
                if not player_pos:
                    player_pos = session.query(PlayerPosition).filter(
                        PlayerPosition.cleaned_name == cleaned
                    ).first()
                
                if player_pos and player_pos.team:
                    team = player_pos.team
                    player_teams[player] = team
                else:
                    team = None
                    print(f"  ⚠️ Could not find team for: {player}")
            
            if team:
                # Update the prop
                prop.player_team = team
                
                # Also update opponent info if it's Unknown
                if prop.opp_team_full == 'Unknown' or not prop.opp_team_full:
                    home_team = prop.home_team
                    away_team = prop.away_team
                    
                    if team == home_team:
                        prop.opp_team_full = away_team
                        # Also update abbreviated opponent
                        if prop.opp_team in ['Unknown', None, '']:
                            opp_abbrev = team_abbrev_mapping.get(away_team, away_team)
                            prop.opp_team = f"vs {opp_abbrev}"
                    elif team == away_team:
                        prop.opp_team_full = home_team
                        if prop.opp_team in ['Unknown', None, '']:
                            opp_abbrev = team_abbrev_mapping.get(home_team, home_team)
                            prop.opp_team = f"@ {opp_abbrev}"
                
                fixed_count += 1
        
        session.commit()
        
        print()
        print(f"✅ Fixed {fixed_count} props")
        
        # Show updated player teams
        if player_teams:
            print()
            print("Updated teams:")
            for player, team in player_teams.items():
                print(f"  {player} → {team}")

if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    fix_unknown_teams(week)

