"""
Utility functions for the Player Prop Optimizer
"""

import re

def clean_player_name(name: str) -> str:
    """
    Clean and standardize player names
    
    Args:
        name: Raw player name from data source
        
    Returns:
        Cleaned player name
    """
    if not name:
        return ""
    
    # Remove extra whitespace
    name = name.strip()
    
    # Remove periods from initials (A.J. -> AJ, D.J. -> DJ, etc.)
    name = name.replace('.', '')
    
    # Remove common suffixes and prefixes
    name = re.sub(r'\s+(Jr|Sr|III|II|IV)$', '', name)
    
    # Remove position indicators that might be in the name
    name = re.sub(r'\s+(QB|RB|WR|TE|K|DST)$', '', name)
    
    # Remove team abbreviations that might be appended
    name = re.sub(r'\s+\([A-Z]{2,4}\)$', '', name)
    
    # Clean up any remaining HTML entities or special characters
    name = name.replace('&nbsp;', ' ')
    name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with single space
    
    return name.strip()

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
