"""
Comprehensive utility functions for the Player Prop Optimizer
Includes player name cleaning, team name normalization, week detection, and formatting utilities
"""

import re
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import os


# ============================================================================
# TEAM NAME NORMALIZATION
# ============================================================================

class TeamNameNormalizer:
    """Centralized team name normalization across all data sources"""
    
    # Master team name mapping - all variations point to canonical full name
    TEAM_NAME_MAPPING = {
        # Arizona Cardinals
        'Arizona Cardinals': 'Arizona Cardinals',
        'Cardinals': 'Arizona Cardinals',
        'ARI': 'Arizona Cardinals',
        'ARZ': 'Arizona Cardinals',
        
        # Atlanta Falcons
        'Atlanta Falcons': 'Atlanta Falcons',
        'Falcons': 'Atlanta Falcons',
        'ATL': 'Atlanta Falcons',
        
        # Baltimore Ravens
        'Baltimore Ravens': 'Baltimore Ravens',
        'Ravens': 'Baltimore Ravens',
        'BAL': 'Baltimore Ravens',
        
        # Buffalo Bills
        'Buffalo Bills': 'Buffalo Bills',
        'Bills': 'Buffalo Bills',
        'BUF': 'Buffalo Bills',
        
        # Carolina Panthers
        'Carolina Panthers': 'Carolina Panthers',
        'Panthers': 'Carolina Panthers',
        'CAR': 'Carolina Panthers',
        
        # Chicago Bears
        'Chicago Bears': 'Chicago Bears',
        'Bears': 'Chicago Bears',
        'CHI': 'Chicago Bears',
        
        # Cincinnati Bengals
        'Cincinnati Bengals': 'Cincinnati Bengals',
        'Bengals': 'Cincinnati Bengals',
        'CIN': 'Cincinnati Bengals',
        
        # Cleveland Browns
        'Cleveland Browns': 'Cleveland Browns',
        'Browns': 'Cleveland Browns',
        'CLE': 'Cleveland Browns',
        
        # Dallas Cowboys
        'Dallas Cowboys': 'Dallas Cowboys',
        'Cowboys': 'Dallas Cowboys',
        'DAL': 'Dallas Cowboys',
        
        # Denver Broncos
        'Denver Broncos': 'Denver Broncos',
        'Broncos': 'Denver Broncos',
        'DEN': 'Denver Broncos',
        
        # Detroit Lions
        'Detroit Lions': 'Detroit Lions',
        'Lions': 'Detroit Lions',
        'DET': 'Detroit Lions',
        
        # Green Bay Packers
        'Green Bay Packers': 'Green Bay Packers',
        'Packers': 'Green Bay Packers',
        'GB': 'Green Bay Packers',
        'GNB': 'Green Bay Packers',
        
        # Houston Texans
        'Houston Texans': 'Houston Texans',
        'Texans': 'Houston Texans',
        'HOU': 'Houston Texans',
        
        # Indianapolis Colts
        'Indianapolis Colts': 'Indianapolis Colts',
        'Colts': 'Indianapolis Colts',
        'IND': 'Indianapolis Colts',
        
        # Jacksonville Jaguars
        'Jacksonville Jaguars': 'Jacksonville Jaguars',
        'Jaguars': 'Jacksonville Jaguars',
        'JAX': 'Jacksonville Jaguars',
        'JAC': 'Jacksonville Jaguars',
        
        # Kansas City Chiefs
        'Kansas City Chiefs': 'Kansas City Chiefs',
        'Chiefs': 'Kansas City Chiefs',
        'KC': 'Kansas City Chiefs',
        'KAN': 'Kansas City Chiefs',
        
        # Las Vegas Raiders
        'Las Vegas Raiders': 'Las Vegas Raiders',
        'Raiders': 'Las Vegas Raiders',
        'LV': 'Las Vegas Raiders',
        'LVR': 'Las Vegas Raiders',
        'Oakland Raiders': 'Las Vegas Raiders',  # Legacy
        'OAK': 'Las Vegas Raiders',  # Legacy
        
        # Los Angeles Chargers
        'Los Angeles Chargers': 'Los Angeles Chargers',
        'Chargers': 'Los Angeles Chargers',
        'LAC': 'Los Angeles Chargers',
        'SD': 'Los Angeles Chargers',  # Legacy San Diego
        'San Diego Chargers': 'Los Angeles Chargers',  # Legacy
        
        # Los Angeles Rams
        'Los Angeles Rams': 'Los Angeles Rams',
        'Rams': 'Los Angeles Rams',
        'LAR': 'Los Angeles Rams',
        'LA': 'Los Angeles Rams',
        'St. Louis Rams': 'Los Angeles Rams',  # Legacy
        'STL': 'Los Angeles Rams',  # Legacy
        
        # Miami Dolphins
        'Miami Dolphins': 'Miami Dolphins',
        'Dolphins': 'Miami Dolphins',
        'MIA': 'Miami Dolphins',
        
        # Minnesota Vikings
        'Minnesota Vikings': 'Minnesota Vikings',
        'Vikings': 'Minnesota Vikings',
        'MIN': 'Minnesota Vikings',
        
        # New England Patriots
        'New England Patriots': 'New England Patriots',
        'Patriots': 'New England Patriots',
        'NE': 'New England Patriots',
        'NWE': 'New England Patriots',
        
        # New Orleans Saints
        'New Orleans Saints': 'New Orleans Saints',
        'Saints': 'New Orleans Saints',
        'NO': 'New Orleans Saints',
        'NOR': 'New Orleans Saints',
        
        # New York Giants
        'New York Giants': 'New York Giants',
        'Giants': 'New York Giants',
        'NYG': 'New York Giants',
        
        # New York Jets
        'New York Jets': 'New York Jets',
        'Jets': 'New York Jets',
        'NYJ': 'New York Jets',
        
        # Philadelphia Eagles
        'Philadelphia Eagles': 'Philadelphia Eagles',
        'Eagles': 'Philadelphia Eagles',
        'PHI': 'Philadelphia Eagles',
        
        # Pittsburgh Steelers
        'Pittsburgh Steelers': 'Pittsburgh Steelers',
        'Steelers': 'Pittsburgh Steelers',
        'PIT': 'Pittsburgh Steelers',
        
        # San Francisco 49ers
        'San Francisco 49ers': 'San Francisco 49ers',
        '49ers': 'San Francisco 49ers',
        'SF': 'San Francisco 49ers',
        'SFO': 'San Francisco 49ers',
        
        # Seattle Seahawks
        'Seattle Seahawks': 'Seattle Seahawks',
        'Seahawks': 'Seattle Seahawks',
        'SEA': 'Seattle Seahawks',
        
        # Tampa Bay Buccaneers
        'Tampa Bay Buccaneers': 'Tampa Bay Buccaneers',
        'Buccaneers': 'Tampa Bay Buccaneers',
        'TB': 'Tampa Bay Buccaneers',
        'TAM': 'Tampa Bay Buccaneers',
        
        # Tennessee Titans
        'Tennessee Titans': 'Tennessee Titans',
        'Titans': 'Tennessee Titans',
        'TEN': 'Tennessee Titans',
        
        # Washington Commanders
        'Washington Commanders': 'Washington Commanders',
        'Commanders': 'Washington Commanders',
        'WAS': 'Washington Commanders',
        'WSH': 'Washington Commanders',
        'Washington Football Team': 'Washington Commanders',  # Legacy
        'Washington Redskins': 'Washington Commanders',  # Legacy
    }
    
    # Reverse mapping: Full name to common abbreviation
    TEAM_TO_ABBREV = {
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
        'Washington Commanders': 'WAS',
    }
    
    # 2025 NFL Bye Week Schedule
    # Each team has exactly one bye week during the season (weeks 5-14)
    # Use this to understand gaps in player stats and avoid confusion
    BYE_WEEK_2025 = {
        'Arizona Cardinals': 8,  # TODO: Fill in bye week
        'Atlanta Falcons': 5,
        'Baltimore Ravens': 7,
        'Buffalo Bills': 7,
        'Carolina Panthers': 14,
        'Chicago Bears': 5,
        'Cincinnati Bengals': 10,
        'Cleveland Browns': 9,
        'Dallas Cowboys': 10,
        'Denver Broncos': 12,
        'Detroit Lions': 8,
        'Green Bay Packers': 5,
        'Houston Texans': 6,
        'Indianapolis Colts': 11,
        'Jacksonville Jaguars': 8,
        'Kansas City Chiefs': 10,
        'Las Vegas Raiders': 8,
        'Los Angeles Chargers': 12,
        'Los Angeles Rams': 8,
        'Miami Dolphins': 12,
        'Minnesota Vikings': 6,
        'New England Patriots': 14,
        'New Orleans Saints': 11,
        'New York Giants': 14,
        'New York Jets': 9,
        'Philadelphia Eagles': 9,
        'Pittsburgh Steelers': 5,  # Confirmed: Week 5 bye
        'San Francisco 49ers': 14,
        'Seattle Seahawks': 8,
        'Tampa Bay Buccaneers': 9,
        'Tennessee Titans': 10,
        'Washington Commanders': 12,
    }
    
    @classmethod
    def normalize(cls, team_name: str) -> str:
        """
        Normalize any team name variation to the canonical full name
        
        Args:
            team_name: Any variation of a team name
            
        Returns:
            Canonical full team name, or original if not found
        """
        if not team_name:
            return team_name
        
        # Try exact match first
        if team_name in cls.TEAM_NAME_MAPPING:
            return cls.TEAM_NAME_MAPPING[team_name]
        
        # Try case-insensitive match
        team_name_lower = team_name.lower()
        for key, value in cls.TEAM_NAME_MAPPING.items():
            if key.lower() == team_name_lower:
                return value
        
        # Try partial match (for cases like "SF 49ers" or "49ers SF")
        for key, value in cls.TEAM_NAME_MAPPING.items():
            if key.lower() in team_name_lower or team_name_lower in key.lower():
                return value
        
        # Return original if no match found
        return team_name
    
    @classmethod
    def to_abbreviation(cls, team_name: str) -> str:
        """
        Convert any team name to its common abbreviation
        
        Args:
            team_name: Any variation of a team name
            
        Returns:
            Team abbreviation (e.g., 'SF', 'KC', 'NE')
        """
        normalized = cls.normalize(team_name)
        return cls.TEAM_TO_ABBREV.get(normalized, team_name)
    
    @classmethod
    def get_bye_week(cls, team_name: str) -> Optional[int]:
        """
        Get the bye week for a team in the 2025 season
        
        Args:
            team_name: Any variation of a team name
            
        Returns:
            Bye week number (5-14), or None if not set/unknown
        """
        normalized = cls.normalize(team_name)
        return cls.BYE_WEEK_2025.get(normalized, None)
    
    @classmethod
    def is_bye_week(cls, team_name: str, week: int) -> bool:
        """
        Check if a team is on bye for a specific week
        
        Args:
            team_name: Any variation of a team name
            week: NFL week number (1-18)
            
        Returns:
            True if team is on bye this week, False otherwise
        """
        bye_week = cls.get_bye_week(team_name)
        return bye_week is not None and bye_week == week
    
    @classmethod
    def get_all_variations(cls, team_name: str) -> list:
        """
        Get all known variations of a team name
        
        Args:
            team_name: Any variation of a team name
            
        Returns:
            List of all known variations for this team
        """
        normalized = cls.normalize(team_name)
        return [k for k, v in cls.TEAM_NAME_MAPPING.items() if v == normalized]


def normalize_team_name(team_name: str) -> str:
    """Normalize team name to canonical format"""
    return TeamNameNormalizer.normalize(team_name)


def get_team_abbreviation(team_name: str) -> str:
    """Get team abbreviation from any team name format"""
    return TeamNameNormalizer.to_abbreviation(team_name)


def get_team_variations(team_name: str) -> list:
    """Get all variations of a team name"""
    return TeamNameNormalizer.get_all_variations(team_name)


def get_bye_week(team_name: str) -> Optional[int]:
    """
    Get the bye week for a team in the 2025 season
    
    Args:
        team_name: Any variation of a team name
        
    Returns:
        Bye week number (5-14), or None if not set/unknown
        
    Example:
        >>> get_bye_week('Pittsburgh Steelers')
        5
        >>> get_bye_week('PIT')
        5
    """
    return TeamNameNormalizer.get_bye_week(team_name)


def is_bye_week(team_name: str, week: int) -> bool:
    """
    Check if a team is on bye for a specific week
    
    Args:
        team_name: Any variation of a team name
        week: NFL week number (1-18)
        
    Returns:
        True if team is on bye this week, False otherwise
        
    Example:
        >>> is_bye_week('Pittsburgh Steelers', 5)
        True
        >>> is_bye_week('PIT', 6)
        False
    """
    return TeamNameNormalizer.is_bye_week(team_name, week)


# ============================================================================
# NFL SEASON WEEK DATES
# ============================================================================

# NFL 2025 Season Week Start Dates (Tuesday after previous week's MNF ends)
# These dates represent when we transition to preparing for the next week
# Pattern: Each week transitions on Tuesday after the previous week's Monday Night Football
NFL_2025_WEEK_DATES = {
    1: '2025-09-04',   # Week 1 starts Sep 4 (Thursday - actual NFL season kickoff)
    2: '2025-09-10',   # Week 2 starts Sep 10 (Tuesday after Week 1 MNF on Sep 9)
    3: '2025-09-17',   # Week 3 starts Sep 17 (Tuesday after Week 2 MNF on Sep 16)
    4: '2025-09-24',   # Week 4 starts Sep 24 (Tuesday after Week 3 MNF on Sep 23)
    5: '2025-10-01',   # Week 5 starts Oct 1 (Tuesday after Week 4 MNF on Sep 30)
    6: '2025-10-08',   # Week 6 starts Oct 8 (Tuesday after Week 5 MNF on Oct 7)
    7: '2025-10-14',   # Week 7 starts Oct 14 (Tuesday after Week 6 MNF on Oct 13)
    8: '2025-10-21',   # Week 8 starts Oct 21 (Tuesday after Week 7 MNF on Oct 20)
    9: '2025-10-28',   # Week 9 starts Oct 28 (Tuesday after Week 8 MNF on Oct 27)
    10: '2025-11-04',  # Week 10 starts Nov 4 (Tuesday after Week 9 MNF on Nov 3)
    11: '2025-11-11',  # Week 11 starts Nov 11 (Tuesday after Week 10 MNF on Nov 10)
    12: '2025-11-18',  # Week 12 starts Nov 18 (Tuesday after Week 11 MNF on Nov 17)
    13: '2025-11-25',  # Week 13 starts Nov 25 (Tuesday after Week 12 Thanksgiving/MNF)
    14: '2025-12-02',  # Week 14 starts Dec 2 (Tuesday after Week 13 MNF on Dec 1)
    15: '2025-12-09',  # Week 15 starts Dec 9 (Tuesday after Week 14 MNF on Dec 8)
    16: '2025-12-16',  # Week 16 starts Dec 16 (Tuesday after Week 15 MNF on Dec 15)
    17: '2025-12-23',  # Week 17 starts Dec 23 (Tuesday after Week 16 MNF on Dec 22)
    18: '2025-12-30',  # Week 18 starts Dec 30 (Tuesday after Week 17 MNF on Dec 29)
}


def get_week_start_date(week_number: int, year: str = "2025") -> Optional[str]:
    """
    Get the start date for a given NFL week
    
    Args:
        week_number: NFL week number (1-18)
        year: Season year (default: "2025")
    
    Returns:
        ISO format date string (e.g., '2025-10-02T00:00:00Z') or None if week not found
    """
    # For now, only support 2025
    if year != "2025":
        return None
    
    date_str = NFL_2025_WEEK_DATES.get(week_number)
    if date_str:
        return f"{date_str}T00:00:00Z"
    return None


def get_week_date_range(week_number: int, year: str = "2025") -> tuple[Optional[str], Optional[str]]:
    """
    Get the start and end dates for a given NFL week
    
    Args:
        week_number: NFL week number (1-18)
        year: Season year (default: "2025")
    
    Returns:
        Tuple of (start_date, end_date) in ISO format, or (None, None) if week not found
    """
    from datetime import timedelta
    
    start_date = get_week_start_date(week_number, year)
    if not start_date:
        return None, None
    
    # Calculate end date (6 days after start to include Monday night)
    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_dt = start_dt + timedelta(days=6)
    end_date = end_dt.strftime('%Y-%m-%dT23:59:59Z')
    
    return start_date, end_date


def get_available_weeks(year: str = "2025") -> list[int]:
    """
    Get list of all available NFL weeks
    
    Args:
        year: Season year (default: "2025")
    
    Returns:
        List of week numbers
    """
    # For now, only support 2025
    if year != "2025":
        return []
    
    return sorted(NFL_2025_WEEK_DATES.keys())


def get_current_week_from_dates(year: str = "2025") -> int:
    """
    Determine the current NFL week based on week start dates and today's date
    
    Args:
        year: Season year (default: "2025")
    
    Returns:
        int: Current NFL week number (1-18)
    """
    if year != "2025":
        # Fallback to folder-based detection
        return get_current_week_from_folders()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find which week we're in based on start dates
    weeks = sorted(NFL_2025_WEEK_DATES.keys())
    
    for i, week in enumerate(weeks):
        week_start_str = NFL_2025_WEEK_DATES[week]
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
        
        # Get next week's start date (or add 7 days if it's the last week)
        if i + 1 < len(weeks):
            next_week_start_str = NFL_2025_WEEK_DATES[weeks[i + 1]]
            next_week_start = datetime.strptime(next_week_start_str, '%Y-%m-%d')
        else:
            # Last week - use 7 days as the range
            from datetime import timedelta
            next_week_start = week_start + timedelta(days=7)
        
        # If today is between this week's start and next week's start, it's this week
        if week_start <= today < next_week_start:
            return week
    
    # If we're past all weeks, return the last week + 1
    return weeks[-1] + 1


# ============================================================================
# WEEK DETECTION UTILITIES
# ============================================================================

def get_current_week_from_schedule(schedule_file="2025/nfl_schedule.csv"):
    """
    Determine the current NFL week based on week dates and today's date.
    
    This function now uses the centralized NFL_2025_WEEK_DATES first,
    then falls back to schedule file parsing if needed.
    
    Logic:
    - Primary: Use NFL_2025_WEEK_DATES to determine week based on today's date
    - Fallback 1: Parse schedule file if dates don't match
    - Fallback 2: Use folder-based detection
    
    Returns:
        int: Current NFL week number (1-18)
    """
    # Try date-based detection first (fastest and most reliable for 2025)
    try:
        return get_current_week_from_dates()
    except Exception as e:
        print(f"⚠️ Date-based detection failed: {e}")
    
    # Fallback to schedule file parsing
    if not os.path.exists(schedule_file):
        print(f"⚠️ Schedule file not found: {schedule_file}")
        print("   Falling back to folder-based detection")
        return get_current_week_from_folders()
    
    try:
        # Load schedule
        schedule = pd.read_csv(schedule_file)
        
        # Parse dates - handle "Sep 4 2025" format
        schedule['parsed_date'] = pd.to_datetime(
            schedule['Date'] + ' ' + schedule['Time (ET)'].str.split().str[0],
            format='%b %d %Y %I:%M',
            errors='coerce'
        )
        
        # Get today's date (without time for comparison)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Group by week and get the last game date for each week
        week_end_dates = schedule.groupby('Week')['parsed_date'].max().sort_index()
        
        # Determine current week
        for week in week_end_dates.index:
            week_end = week_end_dates[week].replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Add a day buffer - if we're within 24 hours after last game, still that week
            # (gives time for box scores to be processed)
            week_end_with_buffer = week_end + pd.Timedelta(days=1)
            
            if today <= week_end_with_buffer:
                return int(week)
        
        # If we're past all scheduled weeks, return the last week + 1
        return int(week_end_dates.index[-1]) + 1
    
    except Exception as e:
        print(f"⚠️ Error parsing schedule: {e}")
        print("   Falling back to folder-based detection")
        return get_current_week_from_folders()


def get_current_week_from_folders():
    """
    Fallback method: Determine current week based on which folders have box scores.
    
    Logic:
    - Check which WEEK folders have box_score_debug.csv (completed weeks)
    - Current week = highest completed week + 1
    
    Returns:
        int: Current NFL week number (1-18)
    """
    completed_weeks = []
    year_folder = "2025"
    
    if os.path.exists(year_folder):
        for item in os.listdir(year_folder):
            if item.startswith("WEEK") and os.path.isdir(os.path.join(year_folder, item)):
                try:
                    week_num = int(item.replace("WEEK", ""))
                    # Check if box score exists (indicating week is completed)
                    box_score_path = os.path.join(year_folder, item, "box_score_debug.csv")
                    if os.path.exists(box_score_path):
                        completed_weeks.append(week_num)
                except ValueError:
                    continue
    
    # Current week is the next week after the latest completed week
    if completed_weeks:
        return max(completed_weeks) + 1
    return 1


def get_available_weeks_with_data():
    """
    Get list of weeks that have any data (props or box scores).
    
    Returns:
        dict: {
            'all': [1, 2, 3, 4, 5, 6],  # All weeks with folders
            'with_props': [6],          # Weeks with saved props
            'with_scores': [1, 2, 3, 4, 5],  # Weeks with box scores
            'complete': []              # Weeks with both props and scores
        }
    """
    year_folder = "2025"
    all_weeks = []
    with_props = []
    with_scores = []
    complete = []
    
    if os.path.exists(year_folder):
        for item in os.listdir(year_folder):
            if item.startswith("WEEK") and os.path.isdir(os.path.join(year_folder, item)):
                try:
                    week_num = int(item.replace("WEEK", ""))
                    all_weeks.append(week_num)
                    
                    week_path = os.path.join(year_folder, item)
                    has_props = os.path.exists(os.path.join(week_path, "props.csv"))
                    has_scores = os.path.exists(os.path.join(week_path, "box_score_debug.csv"))
                    
                    if has_props:
                        with_props.append(week_num)
                    if has_scores:
                        with_scores.append(week_num)
                    if has_props and has_scores:
                        complete.append(week_num)
                        
                except ValueError:
                    continue
    
    return {
        'all': sorted(all_weeks),
        'with_props': sorted(with_props),
        'with_scores': sorted(with_scores),
        'complete': sorted(complete)
    }


# ============================================================================
# PLAYER NAME CLEANING
# ============================================================================

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
        "Woody Marks": "Jo'quavious Marks",  # Props use "Woody Marks", box scores have "Jo'quavious Marks"
        "quavious Marks": "Jo'quavious Marks",  # Handle apostrophe stripping issue
        "Joquavious Marks": "Jo'quavious Marks",  # Handle apostrophe removal
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
    name = name.lower()
    
    # Remove dots from initials for consistent matching
    # This ensures "a.j. brown" matches "aj brown" from different sources
    # Pattern matches single letters followed by dots (e.g., "a.", "j.")
    name = re.sub(r'\b([a-z])\.', r'\1', name)
    
    return name


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

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


# ============================================================================
# MAIN EXECUTION (for testing)
# ============================================================================

if __name__ == "__main__":
    """Test the utility functions"""
    print("=" * 70)
    print("TESTING UTILITY FUNCTIONS")
    print("=" * 70)
    
    # Test team name normalization
    print("\n1. Team Name Normalization:")
    print("-" * 70)
    test_teams = ["49ers", "SF", "Pittsburgh Steelers", "Washington Football Team"]
    for team in test_teams:
        normalized = normalize_team_name(team)
        abbrev = get_team_abbreviation(team)
        print(f"  {team:30} → {normalized:30} ({abbrev})")
    
    # Test week detection
    print("\n2. Week Detection:")
    print("-" * 70)
    current_week = get_current_week_from_schedule()
    print(f"  Current week (schedule-based): {current_week}")
    fallback_week = get_current_week_from_folders()
    print(f"  Current week (folder-based): {fallback_week}")
    
    # Test available weeks
    print("\n3. Available Weeks:")
    print("-" * 70)
    weeks_data = get_available_weeks_with_data()
    print(f"  All weeks: {weeks_data['all']}")
    print(f"  With props: {weeks_data['with_props']}")
    print(f"  With scores: {weeks_data['with_scores']}")
    print(f"  Complete: {weeks_data['complete']}")
    
    # Test player name cleaning
    print("\n4. Player Name Cleaning:")
    print("-" * 70)
    test_players = ["A.J. Brown", "Kenneth Walker III", "Amon-Ra St. Brown"]
    for player in test_players:
        cleaned = clean_player_name(player)
        print(f"  {player:30} → {cleaned}")
    
    # Test formatting
    print("\n5. Formatting:")
    print("-" * 70)
    print(f"  Odds +150: {format_odds(150)}")
    print(f"  Odds -200: {format_odds(-200)}")
    print(f"  Line 1.5 (TDs): {format_line(1.5, 'Passing TDs')}")
    print(f"  Line 249.5 (Yards): {format_line(249.5, 'Passing Yards')}")
    
    print("\n" + "=" * 70)
