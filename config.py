"""
Configuration file for the NFL Player Prop Optimizer
"""

# API Configuration
# Use environment variable for security, fallback to Streamlit secrets for local dev
import os
import streamlit as st

def get_api_key():
    """Get API key from environment variable or Streamlit secrets"""
    # Try environment variable first (for production)
    api_key = os.getenv("ODDS_API_KEY")
    if api_key and api_key != "YOUR_API_KEY_HERE":
        return api_key
    
    # Try Streamlit secrets (for local development)
    try:
        if hasattr(st, 'secrets') and 'ODDS_API_KEY' in st.secrets:
            return st.secrets['ODDS_API_KEY']
    except:
        pass
    
    return "YOUR_API_KEY_HERE"

ODDS_API_KEY = get_api_key()

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
PREFERRED_BOOKMAKER = "fanduel"
