"""
Configuration file for the NFL Player Prop Optimizer
"""

# API Configuration
# Replace 'YOUR_API_KEY_HERE' with your actual API key from https://the-odds-api.com/
ODDS_API_KEY = "5fcc5a130a5bf4e22fa51c033d9a7c1a"

# Application Settings
DEFAULT_MIN_SCORE = 50
DEFAULT_STAT_TYPE = "Passing Yards"

# Scoring Weights (can be adjusted)
SCORING_WEIGHTS = {
    'matchup': 0.35,      # Team defensive ranking
    'player_history': 0.30, # Player historical performance
    'consistency': 0.20,   # Player consistency
    'value': 0.15         # Betting value
}

# Available stat types
STAT_TYPES = [
    "Passing Yards",
    "Passing TDs", 
    "Rushing Yards",
    "Rushing TDs",
    "Receptions",
    "Receiving Yards",
    "Receiving TDs"
]

# Confidence levels
CONFIDENCE_LEVELS = ["All", "High", "Medium", "Low"]

# Preferred bookmaker for odds
PREFERRED_BOOKMAKER = "FanDuel"
