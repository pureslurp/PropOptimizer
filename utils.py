"""
Utility functions for the Player Prop Optimizer
"""

import re
import pandas as pd


# Team Mapping Dictionaries
TEAM_DICT = {
    'TB': 'Buccaneers',
    'SEA': 'Seahawks',
    'SF': '49ers',
    'LAC': 'Chargers',
    'PIT': 'Steelers',
    'ARI': 'Cardinals',
    'PHI': 'Eagles',
    'NYJ': 'Jets',
    'NYG': 'Giants',
    'NO': 'Saints',
    'NE': 'Patriots',
    'MIN': 'Vikings',
    'MIA': 'Dolphins',
    'LV': 'Raiders',
    'LAR': 'Rams',
    'KC': 'Chiefs',
    'JAX': 'Jaguars',
    'IND': 'Colts',
    'TEN': 'Titans',
    'GB': 'Packers',
    'DET': 'Lions',
    'DEN': 'Broncos',
    'DAL': 'Cowboys',
    'CLE': 'Browns',
    'CIN': 'Bengals',
    'CHI': 'Bears',
    'CAR': 'Panthers',
    'BUF': 'Bills',
    'BAL': 'Ravens',
    'ATL': 'Falcons',
    'WAS': 'Commanders',
    'HOU': 'Texans'
}

CITY_TO_TEAM = {
    'Tampa Bay': 'Buccaneers',
    'Seattle': 'Seahawks',
    'San Francisco': '49ers',
    'LA Chargers': 'Chargers',
    'Pittsburgh': 'Steelers',
    'Arizona': 'Cardinals',
    'Philadelphia': 'Eagles',
    'NY Jets': 'Jets',
    'NY Giants': 'Giants',
    'New Orleans': 'Saints',
    'New England': 'Patriots',
    'Minnesota': 'Vikings',
    'Miami': 'Dolphins',
    'Las Vegas': 'Raiders',
    'LA Rams': 'Rams',
    'Kansas City': 'Chiefs',
    'Jacksonville': 'Jaguars',
    'Indianapolis': 'Colts',
    'Tennessee': 'Titans',
    'Green Bay': 'Packers',
    'Detroit': 'Lions',
    'Denver': 'Broncos',
    'Dallas': 'Cowboys',
    'Cleveland': 'Browns',
    'Cincinnati': 'Bengals',
    'Chicago': 'Bears',
    'Carolina': 'Panthers',
    'Buffalo': 'Bills',
    'Baltimore': 'Ravens',
    'Atlanta': 'Falcons',
    'Washington': 'Commanders',
    'Houston': 'Texans'
}


def get_team_abbreviation_mapping():
    """
    Create a mapping from full team names to abbreviations.
    """
    return {
        'Arizona Cardinals': 'ARI',
        'Atlanta Falcons': 'ATL',
        'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET',
        'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU',
        'Indianapolis Colts': 'IND',
        'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV',
        'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR',
        'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE',
        'New Orleans Saints': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI',
        'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN',
        'Washington Commanders': 'WAS'
    }


def normalize_team_name(team_name: str) -> str:
    """
    Normalize team names to consistent format
    
    Args:
        team_name (str): Raw team name
        
    Returns:
        str: Normalized team name
    """
    if pd.isna(team_name) or not team_name:
        return ""
    
    team_name = str(team_name).strip()
    
    # Use existing mappings
    if team_name in TEAM_DICT:
        return TEAM_DICT[team_name]
    elif team_name in CITY_TO_TEAM:
        return CITY_TO_TEAM[team_name]
    
    return team_name


def clean_player_name(name: str) -> str:
    """
    Comprehensive player name cleaning function that handles:
    1. Basic text cleaning and normalization
    2. Regex-based pattern matching for abbreviated names
    3. Specific player name mappings from various sources
    
    Args:
        name (str): Raw player name
        
    Returns:
        str: Cleaned and standardized player name
    """
    if pd.isna(name) or not name:
        return ""
    
    name = str(name).strip()
    
    # Remove ID numbers in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', name)
    
    # Handle abbreviated names where the full name is followed by abbreviation
    # Examples: 
    # "A.J. BrownA.  Brow" -> "A.J. Brown"
    # "Amon-Ra St. BrownA. St.  Brow" -> "Amon-Ra St. Brown"
    
    # Look for pattern where a name is followed by abbreviated version with dots and spaces
    abbreviated_pattern = r'([A-Za-z\-\.\s]+?)([A-Z]\.\s+[A-Za-z]+)$'
    match = re.search(abbreviated_pattern, name)
    if match:
        full_part = match.group(1).strip()
        # Check if the full part looks like a complete name (has space or hyphen)
        if ' ' in full_part or '-' in full_part:
            name = full_part
    
    # Alternative pattern: Look for cases where name ends with single letters and spaces
    if not match:
        single_letter_pattern = r'([A-Za-z\-\.\s]+?)([A-Z]\.?\s+[A-Za-z]+)$'
        alt_match = re.search(single_letter_pattern, name)
        if alt_match:
            full_part = alt_match.group(1).strip()
            if ' ' in full_part or '-' in full_part:
                name = full_part
    
    # Remove extra spaces and normalize
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Handle HTML entities and special characters
    name = name.replace('\xa0', ' ')  # Replace non-breaking spaces
    
    # Remove all suffixes (Jr., Sr., II, III, IV, etc.) for consistent matching
    # This ensures "Kenneth Walker III" and "kenneth walker iii" both become "kenneth walker"
    name = re.sub(r'\s+(Jr\.?|Sr\.?|III|II|IV|V|VI)$', '', name, flags=re.IGNORECASE)
    
    # Apply specific player name mappings
    name_mappings = {
        "Amon-Ra St.": "Amon-Ra St. Brown",
        "Amon-Ra St.BrownA. S": "Amon-Ra St. Brown",
        "Amon-Ra St. BrownA. St. Brow": "Amon-Ra St. Brown",
        "D.K. Metcalf": "DK Metcalf",
        "D.J. Moore": "DJ Moore",
        "Nathaniel Dell": "Tank Dell",
        "Josh Palmer": "Joshua Palmer",
        "Cartavious Bigsby": "Tank Bigsby",
        "Damario Douglas": "DeMario Douglas",
        "Re'Mahn Davis": "Ray Davis",
        "Gabriel Davis": "Gabe Davis",
        "Chigoziem Okonkwo": "Chig Okonkwo",
        "John Mundt": "Johnny Mundt",
        "Mar'Keise Irving": "Bucky Irving",
        "Jaxon Smith-NjigbaJ. Smith-Njigba": "Jaxon Smith-Njigba",
        "Cam Ward": "Cameron Ward",
        # Specific name variations
        "A.J. BrownA.  Brow": "A.J. Brown",
        "J.J. McCarthyJ.  McCarth": "J.J. McCarthy",
        "Marquez Valdes-ScantlingM. Valdes-Scantling": "Marquez Valdes-Scantling",
        "e Thornton": "Dont'e Thornton",
        # Truncated names from box scores
        "Amon-Ra St. BrownA. St. Brown": "Amon-Ra St. Brown",
        "JuJu Smith-SchusterJ. Smith-Schuster": "JuJu Smith-Schuster",
        "Mo Alie-CoxM. Alie-Cox": "Mo Alie-Cox",
        "Brevyn Spann-FordB. Spann-Ford": "Brevyn Spann-Ford",
        # Missing first names
        "Marr Chase": "Ja'Marr Chase",
        "Von Achane": "De'Von Achane",
        # Additional name mappings
        "Marquise Brown": "Hollywood Brown",
        "Dale Robinson": "Wan'Dale Robinson",
        "Andre Swift": "D'Andre Swift",
        "Ray Ray McCloud": "Ray-Ray McCloud",
        "Keise Irving": "Bucky Irving",
        "Cameron Skattebo": "Cam Skattebo",
        "Kenny Gainwell": "Kenneth Gainwell",
        "AJ Dillon": "A.J. Dillon",
        "Jacory Merritt": "Jacory Croskey-Merritt",
        "Christopher Rodriguez": "Chris Rodriguez",
        "Tavion Sanders": "Ja'Tavion Sanders",
        "quavious Marks": "Woody Marks",
        "Tre Harris": "Tre' Harris",
        "Christopher Brooks": "Chris Brooks",
        "Nick Westbrook": "Nick Westbrook-Ikhine",
        "Mahn Davis": "Ray Davis",
        "Wayne Eskridge": "Dee Eskridge",
        "Chatarius Atwell": "Tutu Atwell"
    }
    
    # Apply name mapping if exists
    if name in name_mappings:
        name = name_mappings[name]
    
    # Handle defense/special teams name formatting
    # ESPN: "Packers D/ST" -> DKSalaries: "Packers"
    if name.endswith(" D/ST"):
        name = name.replace(" D/ST", "")
    
    # Normalize to lowercase for consistent matching
    return name.lower()


def format_odds(odds: float) -> str:
    """
    Format odds for display
    
    Args:
        odds: American odds format
        
    Returns:
        Formatted odds string
    """
    if odds == 0:
        return "0"
    elif odds > 0:
        return f"+{int(odds)}"
    else:
        return str(int(odds))


def format_line(line: float, stat_type: str) -> str:
    """
    Format line for display based on stat type
    
    Args:
        line: The line value
        stat_type: Type of stat (e.g., "Passing Yards", "Receptions")
        
    Returns:
        Formatted line string
    """
    if stat_type in ["Receptions", "Passing TDs", "Rushing TDs", "Receiving TDs"]:
        # For counting stats, show as whole numbers
        return f"{int(line)}"
    else:
        # For yardage stats, show with decimal if needed
        if line == int(line):
            return f"{int(line)}"
        else:
            return f"{line}"


def calculate_last_n_over_rate(player_stats: list, line: float, n: int = 5) -> float:
    """
    Calculate the over rate for the last N games
    
    Args:
        player_stats: List of player's game stats (should be in chronological order)
        line: The line to compare against
        n: Number of recent games to consider (default: 5)
        
    Returns:
        Over rate as a decimal (0.0 to 1.0), or 0.5 if insufficient data
    """
    if not player_stats or len(player_stats) == 0:
        return 0.5
    
    # Get the last N games
    last_n_games = player_stats[-n:] if len(player_stats) >= n else player_stats
    
    # Calculate over rate
    over_count = sum(1 for stat in last_n_games if stat > line)
    return over_count / len(last_n_games)


def calculate_streak(player_stats: list, line: float) -> int:
    """
    Calculate how many consecutive games (from most recent) the player has gone over the line
    
    Args:
        player_stats: List of player's game stats (should be in chronological order)
        line: The line to compare against
        
    Returns:
        Number of consecutive games over the line (0 if last game was under)
    """
    if not player_stats or len(player_stats) == 0:
        return 0
    
    streak = 0
    # Count backwards from most recent game
    for stat in reversed(player_stats):
        if stat > line:
            streak += 1
        else:
            break  # Stop at first game that didn't go over
    
    return streak
