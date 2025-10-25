"""
NFL Player Prop Optimizer
A Streamlit application for analyzing NFL player props using matchup data and player history.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime
from dateutil import parser
import pytz
import os
import plotly.graph_objects as go
import sys
import json
import glob

# Import our custom modules
from enhanced_data_processor import EnhancedFootballDataProcessor
from scoring_model import AdvancedPropScorer
from odds_api import OddsAPI, AlternateLineManager
from odds_api_with_db import OddsAPIWithDB
from utils import clean_player_name, format_odds, format_line
from config import ODDS_API_KEY, STAT_TYPES, CONFIDENCE_LEVELS, DEFAULT_MIN_SCORE, PREFERRED_BOOKMAKER
from utils import get_current_week_from_schedule, get_available_weeks_with_data
from prop_strategies import (
    STRATEGIES, 
    get_strategies_for_roi, 
    display_all_strategies,
    display_time_window_strategies
)
from database.database_models import Prop, Game
import warnings

# Set page config
st.set_page_config(
    page_title="NFL Player Prop Optimizer",
    page_icon="🏈",
    layout="wide"
)

# Database-only mode - no more CSV fallbacks needed


# Removed - now using get_available_weeks_with_data() from week_utils


# Removed deprecated CSV functions - now using database-only approach


# Removed deprecated CSV/JSON functions - now using database-only approach


def classify_game_time_window(commence_time_str):
    """
    Classify a game into a time window based on its commence time.
    
    Args:
        commence_time_str: ISO format timestamp string (e.g., "2025-09-07T17:00:00Z")
    
    Returns:
        str: One of 'TNF', 'SunAM', 'SunPM', 'SNF', 'MNF', or 'Other'
    """
    if not commence_time_str:
        return 'Other'
    
    try:
        # Handle both string and datetime/Timestamp objects
        if isinstance(commence_time_str, str):
            # Parse the UTC time string
            utc_time = parser.parse(commence_time_str)
        else:
            # Already a datetime/Timestamp object
            utc_time = commence_time_str
        
        # Ensure the datetime is timezone-aware (localize to UTC if tz-naive)
        if utc_time.tzinfo is None or utc_time.tzinfo.utcoffset(utc_time) is None:
            # Timestamp is tz-naive, assume it's in UTC and localize it
            if hasattr(utc_time, 'tz_localize'):
                # Pandas Timestamp
                utc_time = utc_time.tz_localize('UTC')
            else:
                # Python datetime
                utc_time = pytz.utc.localize(utc_time)
        
        # Convert to Eastern Time
        eastern = pytz.timezone('US/Eastern')
        et_time = utc_time.astimezone(eastern)
        
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = et_time.weekday()
        hour = et_time.hour
        
        # Thursday Night Football (Thursday games)
        if day_of_week == 3:  # Thursday
            return 'TNF'
        
        # Sunday games
        elif day_of_week == 6:  # Sunday
            # Sunday AM: Games starting between 12pm-2:30pm ET
            if 12 <= hour < 15:
                return 'SunAM'
            # Sunday PM: Games starting between 3pm-6pm ET
            elif 15 <= hour < 18:
                return 'SunPM'
            # Sunday Night Football: Games starting at 6pm ET or later
            elif hour >= 18:
                return 'SNF'
        
        # Monday Night Football (Monday games)
        elif day_of_week == 0:  # Monday
            return 'MNF'
        
        # Saturday or other days (rare but can happen late season)
        return 'Other'
        
    except Exception as e:
        # Silently return 'Other' on parsing errors
        return 'Other'


def get_available_historical_weeks():
    """
    Get list of available historical weeks from database.
    This function is now deprecated - use DatabaseManager.get_available_weeks_from_db() instead.
    """
    from database.database_manager import DatabaseManager
    db_manager = DatabaseManager()
    # Ensure database schema is up to date
    db_manager.migrate_database()
    return db_manager.get_available_weeks_from_db()


# Removed fetch_props_with_fallback - no longer needed since everything is in database


def process_props_and_score(props_df, stat_types_in_data, scorer, data_processor, 
                            alt_line_manager, fallback_used, progress_bar):
    """
    Process props and calculate scores (database mode).
    
    Returns:
        list: All scored props including alternates
    """
    all_props = []
    
    # Check if props_df is empty
    if props_df.empty:
        return all_props
    
    if fallback_used:
        # Database mode: process all rows (already includes alternates)
        for idx, stat_type in enumerate(stat_types_in_data):
            stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
            
            if stat_filtered_df.empty:
                continue
            
            if progress_bar:
                progress_text = f"Processing {stat_type}... ({idx+1}/{len(stat_types_in_data)})"
                progress_val = 50 + int((idx + 1) / len(stat_types_in_data) * 40)
                progress_bar.progress(progress_val, text=progress_text)
            
            # Process all rows from database (both main and alternate lines)
            for _, row in stat_filtered_df.iterrows():
                try:
                    import pandas as pd
                    if pd.isna(row.get('Player')) or row.get('Player') is None:
                        continue
                    if pd.isna(row.get('Stat Type')) or row.get('Stat Type') is None:
                        continue
                    
                    score_data = scorer.calculate_comprehensive_score(
                        row['Player'],
                        row.get('Opp. Team Full', row['Opp. Team']),
                        row['Stat Type'],
                        row['Line'],
                        row.get('Odds', 0),
                        home_team=row.get('Home Team'),
                        away_team=row.get('Away Team'),
                        player_team=row.get('Team'),  # Use pre-calculated from database
                        team_rank=row.get('team_pos_rank_stat_type')  # Use pre-calculated from database
                    )
                    
                    # score_data already includes l5_over_rate, home_over_rate, away_over_rate, and streak
                    scored_prop = {
                        **row.to_dict(),
                        **score_data,
                        'is_alternate': row.get('is_alternate', False)
                    }
                    all_props.append(scored_prop)
                except Exception as e:
                    continue
    else:
        # API mode (OPTIMIZED): All props come from alternate lines
        # No main props are fetched to save API calls
        for idx, stat_type in enumerate(stat_types_in_data):
            stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
            
            if stat_filtered_df.empty:
                continue
            
            progress_text = f"Processing {stat_type}... ({idx+1}/{len(stat_types_in_data)})"
            progress_val = 50 + int((idx + 1) / len(stat_types_in_data) * 40)
            progress_bar.progress(progress_val, text=progress_text)
            
            # Process all props (which are all alternates with odds filter)
            for _, row in stat_filtered_df.iterrows():
                # Filter odds between +200 and -450
                odds = row.get('Odds', 0)
                if -450 <= odds <= 200:
                    score_data = scorer.calculate_comprehensive_score(
                        row['Player'],
                        row.get('Opp. Team Full', row['Opp. Team']),
                        row['Stat Type'],
                        row['Line'],
                        odds,
                        home_team=row.get('Home Team'),
                        away_team=row.get('Away Team'),
                        player_team=row.get('Team'),  # Use pre-calculated from database/API
                        team_rank=row.get('team_pos_rank_stat_type')  # Use pre-calculated from database/API
                    )
                    
                    scored_prop = {
                        **row.to_dict(),
                        **score_data,
                        'is_alternate': row.get('is_alternate', True)
                    }
                    all_props.append(scored_prop)
    
    return all_props


# Removed deprecated CSV box score function - now using database-only approach


def get_stat_column_mapping():
    """Map stat types to box score column names"""
    return {
        "Passing Yards": "pass_Yds",
        "Passing TDs": "pass_TD",
        "Rushing Yards": "rush_Yds",
        "Rushing TDs": "rush_TD",
        "Receptions": "rec_Rec",
        "Receiving Yards": "rec_Yds",
        "Receiving TDs": "rec_TD"
    }


def get_actual_stat(player_name, stat_type, box_score_df):
    """Get the actual stat value for a player from box score data"""
    if box_score_df.empty:
        return None
    
    stat_mapping = get_stat_column_mapping()
    stat_column = stat_mapping.get(stat_type)
    
    if not stat_column:
        return None
    
    # Clean the player name for matching
    player_clean = clean_player_name(player_name)
    
    # Find the player in the box score
    player_row = box_score_df[box_score_df['Name_clean'] == player_clean]
    
    if player_row.empty:
        return None
    
    # Get the stat value
    stat_value = player_row.iloc[0].get(stat_column)
    
    if pd.isna(stat_value):
        return 0  # Return 0 if stat is NaN (player didn't have this stat)
    
    return stat_value


def get_team_abbreviation(full_name):
    """Convert full team name to abbreviation"""
    team_abbrev_map = {
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
    return team_abbrev_map.get(full_name, full_name)


def get_matchup_string(row):
    """Create matchup string from row data (e.g., 'PHI @ NYG')"""
    if 'Home Team' in row and 'Away Team' in row and pd.notna(row['Home Team']) and pd.notna(row['Away Team']):
        away_abbrev = get_team_abbreviation(row['Away Team'])
        home_abbrev = get_team_abbreviation(row['Home Team'])
        return f"{away_abbrev} @ {home_abbrev}"
    return None


def calculate_profit_from_odds(odds, stake=1.0):
    """Calculate profit from American odds for a winning bet"""
    if odds < 0:
        # Negative odds: bet abs(odds) to win 100
        return stake * (100 / abs(odds))
    else:
        # Positive odds: bet 100 to win odds
        return stake * (odds / 100)


def calculate_strategy_roi_for_week_with_data(props_df, data_processor, score_min, score_max, odds_min=-400, odds_max=-150, streak_min=None, max_players=5, position_filter=False):
    """
    Calculate ROI for a specific strategy using pre-loaded data.
    
    Args:
        props_df: Pre-loaded and scored props DataFrame
        score_min: Minimum score threshold
        score_max: Maximum score threshold  
        odds_min: Minimum odds threshold
        odds_max: Maximum odds threshold
        streak_min: Minimum streak requirement
        max_players: Maximum number of players to select
        position_filter: If True, apply position-appropriate filtering
    
    Returns:
        dict: ROI data by time window, e.g., {'TNF': {'roi': 0.0, 'results': []}, ...}
    """
    if props_df.empty:
        return {}
    
    # Group props by time window FIRST, then apply strategy filters to each window
    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
    roi_by_window = {}
    
    for window in time_windows:
        # Filter to this time window first
        window_props = props_df[props_df['time_window'] == window]
        
        if window_props.empty:
            continue
        
        # Apply strategy filter to this time window's props
        filtered_window_props = filter_props_by_strategy(
            window_props,
            data_processor=data_processor,  # Pass the data processor for position filtering
            score_min=score_min,
            score_max=score_max,
            odds_min=odds_min,
            odds_max=odds_max,
            streak_min=streak_min,
            max_players=max_players,
            position_filter=position_filter
        )
        
        if filtered_window_props.empty:
            continue
        
        # filtered_window_props is already limited to max_players by filter_props_by_strategy
        window_props = filtered_window_props
        
        # Calculate ROI as PARLAY (1 unit bet per time window)
        bet_results = []
        all_props_hit = True
        parlay_decimal_odds = 1.0
        
        for _, row in window_props.iterrows():
            actual = row.get('actual_result')
            line = row['Line']
            odds = row['Odds']
            score = row['total_score']
            
            # Convert American odds to decimal for parlay calculation
            if odds < 0:
                decimal_odds = 1 + (100 / abs(odds))
            else:
                decimal_odds = 1 + (odds / 100)
            
            if pd.notna(actual) and actual is not None:
                if actual > line:
                    # Prop hit
                    parlay_decimal_odds *= decimal_odds
                    bet_results.append({
                        'player': row['Player'],
                        'stat_type': row['Stat Type'],
                        'line': line,
                        'actual': actual,
                        'odds': odds,
                        'score': score,
                        'result': 'HIT',
                        'roi': 0  # Individual prop ROI is 0 for parlays
                    })
                else:
                    # Prop missed - parlay loses
                    all_props_hit = False
                    bet_results.append({
                        'player': row['Player'],
                        'stat_type': row['Stat Type'],
                        'line': line,
                        'actual': actual,
                        'odds': odds,
                        'score': score,
                        'result': 'MISS',
                        'roi': 0  # Individual prop ROI is 0 for parlays
                    })
            else:
                # No result available - treat as incomplete parlay
                all_props_hit = False
                bet_results.append({
                    'player': row['Player'],
                    'stat_type': row['Stat Type'],
                    'line': line,
                    'actual': None,
                    'odds': odds,
                    'score': score,
                    'result': 'N/A',
                    'roi': 0  # Individual prop ROI is 0 for parlays
                })
        
        # Calculate ROI for this time window
        if all_props_hit:
            # Parlay wins - profit is (decimal odds - 1) * stake
            window_roi = parlay_decimal_odds - 1.0
        else:
            # Parlay loses - lose 1 unit stake
            window_roi = -1.0
        
        roi_by_window[window] = {
            'roi': window_roi,
            'results': bet_results
        }
    
    return roi_by_window


def calculate_strategy_roi_for_week(week_num, score_min, score_max, odds_min=-400, odds_max=-150, 
                                    streak_min=None, max_players=5, position_filter=False):
    """
    Calculate ROI for a strategy in a specific historical week, broken down by time window.
    Returns dictionary of ROI by time window.
    
    Args:
        week_num: Week number to calculate ROI for
        score_min: Minimum score threshold
        score_max: Maximum score threshold
        odds_min: Minimum odds (e.g., -400)
        odds_max: Maximum odds (e.g., -150)
        streak_min: Minimum streak value (optional)
        max_players: Maximum number of players to select
        position_filter: If True, apply position-appropriate filtering
    
    Returns:
        dict: ROI data by time window, e.g., {'TNF': {'roi': 0.0, 'results': []}, ...}
    """
    # Load historical data from database
    from database.database_manager import DatabaseManager
    db_manager = DatabaseManager()
    props_df = db_manager.get_props_as_dataframe(week=week_num, upcoming_only=False)
    
    
    if props_df.empty:
        return None
    
    # Add time window classification to each prop
    props_df['time_window'] = props_df['Commence Time'].apply(classify_game_time_window)
    
    # Create a data processor limited to data before this week
    from database.database_enhanced_data_processor import DatabaseEnhancedFootballDataProcessor
    data_processor_historical = DatabaseEnhancedFootballDataProcessor(max_week=week_num)
    scorer_historical = AdvancedPropScorer(data_processor_historical)
    
    # Score the props (this adds the total_score column that's missing from database)
    # Add total_score column by calculating comprehensive score for each prop
    total_scores = []
    for _, row in props_df.iterrows():
        if pd.isna(row.get('Stat Type')) or row.get('Stat Type') is None:
            total_scores.append(0.0)
            continue
        
        score_data = scorer_historical.calculate_comprehensive_score(
            row['Player'],
            row.get('Opp. Team Full', row['Opp. Team']),
            row['Stat Type'],
            row['Line'],
            row.get('Odds', 0),
            row.get('Home Team'),
            row.get('Away Team'),
            row.get('Team'),
            row.get('team_pos_rank_stat_type')
        )
        total_scores.append(score_data['total_score'])
    
    props_df['total_score'] = total_scores
    
    # Update team assignments
    odds_api_temp = OddsAPI(ODDS_API_KEY)
    props_df = odds_api_temp.update_team_assignments(props_df, data_processor_historical)
    
    # Load box score for actual results from database
    from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
    box_score_loader = DatabaseBoxScoreLoader()
    box_score_df = box_score_loader.load_week_data_from_db(week_num)
    
    if box_score_df.empty:
        return None
    
    # Add actual results to the already-scored props_df
    for idx, row in props_df.iterrows():
        actual_stat = get_actual_stat(
            row['Player'],
            row['Stat Type'],
            box_score_df
        )
        props_df.at[idx, 'actual_result'] = actual_stat
    
    # Use props_df directly (already has total_score from first scoring pass)
    results_df = props_df
    
    if results_df.empty:
        return {}
    
    # Group props by time window FIRST, then apply strategy filters to each window
    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
    roi_by_window = {}
    
    
    for window in time_windows:
        # Filter to this time window first
        window_props = results_df[results_df['time_window'] == window]
        
        if window_props.empty:
            continue
        
        
        # Apply strategy filter to this time window's props
        filtered_window_props = filter_props_by_strategy(
            window_props,
            data_processor=data_processor_historical,
            score_min=score_min,
            score_max=score_max,
            odds_min=odds_min,
            odds_max=odds_max,
            streak_min=streak_min,
            max_players=max_players,
            position_filter=position_filter
        )
        
        
        if filtered_window_props.empty:
            continue
        
        # filtered_window_props is already limited to max_players by filter_props_by_strategy
        window_props = filtered_window_props
        
        # Calculate ROI as PARLAY (1 unit bet per time window)
        bet_results = []
        all_props_hit = True
        parlay_decimal_odds = 1.0
        
        
        for _, row in window_props.iterrows():
            actual = row.get('actual_result')
            line = row['Line']
            odds = row['Odds']
            score = row['total_score']
            
            
            # Convert American odds to decimal for parlay calculation
            if odds < 0:
                decimal_odds = 1 + (100 / abs(odds))
            else:
                decimal_odds = 1 + (odds / 100)
            
            if pd.notna(actual) and actual is not None:
                if actual > line:
                    # Prop hit
                    parlay_decimal_odds *= decimal_odds
                    bet_results.append({
                        'player': row['Player'],
                        'stat_type': row['Stat Type'],
                        'line': line,
                        'actual': actual,
                        'odds': odds,
                        'score': score,
                        'result': 'HIT',
                        'roi': 0.0
                    })
                else:
                    # Prop missed - parlay loses
                    all_props_hit = False
                    bet_results.append({
                        'player': row['Player'],
                        'stat_type': row['Stat Type'],
                        'line': line,
                        'actual': actual,
                        'odds': odds,
                        'score': score,
                        'result': 'MISS',
                        'roi': 0.0
                    })
            else:
                # No result available - treat as incomplete parlay
                all_props_hit = False
                bet_results.append({
                    'player': row['Player'],
                    'stat_type': row['Stat Type'],
                    'line': line,
                    'actual': None,
                    'odds': odds,
                    'score': score,
                    'result': 'N/A',
                    'roi': 0.0
                })
        
        # Calculate ROI for this time window
        if all_props_hit:
            # Parlay wins - profit is (decimal odds - 1) * stake
            window_roi = parlay_decimal_odds - 1.0
        else:
            # Parlay loses - lose 1 unit stake
            window_roi = -1.0
        
        
        roi_by_window[window] = {
            'roi': window_roi,
            'results': bet_results
        }
    
    return roi_by_window


def is_position_appropriate_stat(player_name, stat_type, data_processor):
    """
    Determine if a stat type is appropriate for a player's position.
    
    Rules:
    - QB: Allow Passing stats, NO Rushing stats
    - RB: Allow Rushing stats, NO Receiving stats
    - WR/TE: Allow Receiving stats
    
    Args:
        player_name: Player name
        stat_type: Stat type to check
        data_processor: Data processor instance
        
    Returns:
        bool: True if the stat is position-appropriate
    """
    try:
        from utils import clean_player_name
        
        # Validate inputs
        if not player_name or not stat_type or not data_processor:
            return True  # Allow if missing data
        
        cleaned_name = clean_player_name(player_name)
        
        # Check if data processor has required attributes
        if not hasattr(data_processor, 'player_name_index') or not hasattr(data_processor, 'player_season_stats'):
            return True  # Allow if data structure is incomplete
        
        player_key = data_processor.player_name_index.get(cleaned_name)
        
        if not player_key or player_key not in data_processor.player_season_stats:
            return True  # If we can't determine, allow it
        
        player_stats = data_processor.player_season_stats[player_key]
        
        # Determine position based on what stats they have
        has_passing = 'Passing Yards' in player_stats or 'Passing TDs' in player_stats
        has_rushing = 'Rushing Yards' in player_stats or 'Rushing TDs' in player_stats
        has_receiving = 'Receiving Yards' in player_stats or 'Receptions' in player_stats or 'Receiving TDs' in player_stats
        
        # QB position detection (has passing stats)
        if has_passing:
            # No QB rushing allowed
            if stat_type in ['Rushing Yards', 'Rushing TDs']:
                return False
            return True
        
        # RB position detection (has rushing but no passing)
        if has_rushing and not has_passing:
            # No RB receiving allowed
            if stat_type in ['Receiving Yards', 'Receptions', 'Receiving TDs']:
                return False
            return True
        
        # WR/TE (has receiving stats)
        if has_receiving:
            return True
        
        return True  # Default to allowing the stat
        
    except Exception as e:
        # Log error but don't crash - default to allowing the stat
        print(f"Warning: Error in position filtering for {player_name} - {stat_type}: {e}")
        return True


def filter_props_by_strategy(df, data_processor=None, score_min=70, score_max=float('inf'), 
                              odds_min=-400, odds_max=-150, streak_min=None, 
                              max_players=5, position_filter=False):
    """
    Reusable function to filter props based on strategy criteria.
    
    Args:
        df: DataFrame of props with scores
        data_processor: Data processor instance (required for position filtering)
        score_min: Minimum score threshold
        score_max: Maximum score threshold
        odds_min: Minimum odds (e.g., -400)
        odds_max: Maximum odds (e.g., -150)
        streak_min: Minimum streak value (optional)
        max_players: Maximum number of players to return
        position_filter: If True, apply position-appropriate filtering
        
    Returns:
        DataFrame: Filtered props (empty DataFrame if no props match or error occurs)
    """
    try:
        # Validate input DataFrame
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Validate required columns exist
        required_columns = ['total_score', 'Odds', 'Player', 'Stat Type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Warning: Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Filter by score range
        filtered_df = df[
            (df['total_score'] >= score_min) & 
            (df['total_score'] < score_max) &
            (df['Odds'] >= odds_min) & 
            (df['Odds'] <= odds_max)
        ].copy()
        
        # Apply streak filter if specified
        if streak_min is not None:
            if 'streak' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['streak'] >= streak_min]
            else:
                print(f"Warning: Streak filter requested but 'streak' column not found")
        
        # Apply position filter if specified
        if position_filter:
            if data_processor is None:
                print("Warning: Position filter requested but no data_processor provided")
            else:
                try:
                    filtered_df = filtered_df[
                        filtered_df.apply(
                            lambda row: is_position_appropriate_stat(row['Player'], row['Stat Type'], data_processor),
                            axis=1
                        )
                    ]
                except Exception as e:
                    print(f"Warning: Error applying position filter: {e}")
                    # Continue without position filtering
        
        if not filtered_df.empty:
            # Keep only highest score per player+stat type combination
            filtered_df = filtered_df.sort_values('total_score', ascending=False)
            filtered_df = filtered_df.drop_duplicates(subset=['Player', 'Stat Type'], keep='first')
            
            # Return top N players
            return filtered_df.head(max_players)
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error in filter_props_by_strategy: {e}")
        return pd.DataFrame()


def calculate_high_score_straight_bets_roi():
    """
    Calculate ROI for all players with Score > 80 AND Streak >= 3 as straight bets (1 unit each).
    This is separate from parlay strategies and treats each prop as an independent bet.
    Only the highest-scoring prop per player/stat type combination is counted.
    Returns a dictionary with ROI data by time window for display.
    """
    current_week = get_current_week_from_schedule()
    
    # Calculate for all weeks from 4 up to (but not including) current week
    historical_weeks = list(range(4, current_week))
    
    if not historical_weeks:
        return None
    
    # Time windows we're tracking
    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF', 'All']
    
    # Initialize ROI tracking by time window
    roi_by_window = {window: {'roi': 0.0, 'total_bets': 0, 'wins': 0, 'losses': 0, 'results': []} for window in time_windows}
    
    for week in historical_weeks:
        try:
            # Load historical data from database
            from database.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            props_df = db_manager.get_props_as_dataframe(week=week, upcoming_only=False)
            
            if props_df.empty:
                continue
            
            # Add time window classification to each prop
            props_df['time_window'] = props_df['Commence Time'].apply(classify_game_time_window)
            
            # Create a data processor limited to data before this week
            from database.database_enhanced_data_processor import DatabaseEnhancedFootballDataProcessor
            data_processor_historical = DatabaseEnhancedFootballDataProcessor(max_week=week)
            scorer_historical = AdvancedPropScorer(data_processor_historical)
            
            # Update team assignments
            odds_api_temp = OddsAPI(ODDS_API_KEY)
            props_df = odds_api_temp.update_team_assignments(props_df, data_processor_historical)
            
            # Score all props
            all_props = []
            stat_types_in_data = props_df['Stat Type'].unique()
            
            for stat_type in stat_types_in_data:
                stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
                
                if stat_filtered_df.empty:
                    continue
                
                for _, row in stat_filtered_df.iterrows():
                    score_data = scorer_historical.calculate_comprehensive_score(
                        row['Player'],
                        row.get('Opp. Team Full', row['Opp. Team']),
                        row['Stat Type'],
                        row['Line'],
                        row.get('Odds', 0),
                        home_team=row.get('Home Team'),
                        away_team=row.get('Away Team')
                    )
                    
                    scored_prop = {
                        **row.to_dict(),
                        **score_data,
                        'is_alternate': row.get('is_alternate', True),
                        'time_window': row.get('time_window', 'Other')
                    }
                    all_props.append(scored_prop)
            
            # Load box score for actual results from database
            from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
            box_score_loader = DatabaseBoxScoreLoader()
            box_score_df = box_score_loader.load_week_data_from_db(week)
            
            if box_score_df.empty:
                continue
            
            # Add actual results
            for prop in all_props:
                actual_stat = get_actual_stat(
                    prop['Player'],
                    prop['Stat Type'],
                    box_score_df
                )
                prop['actual_result'] = actual_stat
            
            # Convert to DataFrame
            results_df = pd.DataFrame(all_props)
            
            if results_df.empty:
                continue
            
            # Filter to props with Score > 80 and Streak >= 3
            high_score_props = results_df[
                (results_df['total_score'] > 80) & 
                (results_df['streak'] >= 3)
            ]
            
            # Remove redundant props: keep only the highest score for each player+stat type combination
            if not high_score_props.empty:
                high_score_props = high_score_props.sort_values('total_score', ascending=False)
                high_score_props = high_score_props.drop_duplicates(subset=['Player', 'Stat Type'], keep='first')
            
            # Calculate ROI for each bet by time window
            for _, row in high_score_props.iterrows():
                actual = row.get('actual_result')
                line = row['Line']
                odds = row['Odds']
                score = row['total_score']
                window = row.get('time_window', 'Other')
                
                # Skip if no actual result available
                if pd.isna(actual) or actual is None:
                    continue
                
                # Calculate payout for this bet (1 unit)
                if odds < 0:
                    # Negative odds: bet abs(odds) to win 100
                    payout = 100 / abs(odds)  # Profit per $1 bet
                else:
                    # Positive odds: bet 100 to win odds
                    payout = odds / 100  # Profit per $1 bet
                
                # Determine if bet hit
                if actual > line:
                    # Prop hit - win the bet
                    bet_roi = payout  # Profit
                    result = 'WIN'
                    if window in roi_by_window:
                        roi_by_window[window]['wins'] += 1
                    roi_by_window['All']['wins'] += 1
                else:
                    # Prop missed - lose the stake
                    bet_roi = -1.0  # Lose 1 unit
                    result = 'LOSS'
                    if window in roi_by_window:
                        roi_by_window[window]['losses'] += 1
                    roi_by_window['All']['losses'] += 1
                
                # Track ROI
                if window in roi_by_window:
                    roi_by_window[window]['roi'] += bet_roi
                    roi_by_window[window]['total_bets'] += 1
                    roi_by_window[window]['results'].append({
                        'week': week,
                        'player': row['Player'],
                        'stat_type': row['Stat Type'],
                        'line': line,
                        'actual': actual,
                        'odds': odds,
                        'score': score,
                        'result': result,
                        'roi': bet_roi
                    })
                
                # Always track in "All" window
                roi_by_window['All']['roi'] += bet_roi
                roi_by_window['All']['total_bets'] += 1
                roi_by_window['All']['results'].append({
                    'week': week,
                    'player': row['Player'],
                    'stat_type': row['Stat Type'],
                    'line': line,
                    'actual': actual,
                    'odds': odds,
                    'score': score,
                    'result': result,
                    'roi': bet_roi
                })
                
        except Exception as e:
            print(f"Warning: Error calculating high score ROI for week {week}: {e}")
            continue
    
    return roi_by_window


def calculate_all_strategies_roi():
    """
    Calculate ROI for all strategies (v1 and v2: Optimal, Greasy, Degen) 
    across all historical weeks (starting from week 4), broken down by time window.
    Returns a dictionary with ROI data by strategy and time window for display.
    """
    current_week = get_current_week_from_schedule()
    
    # Calculate for all weeks from 4 up to (but not including) current week
    historical_weeks = list(range(4, current_week))
    
    if not historical_weeks:
        return None
    
    # Get centralized strategy definitions
    strategies = get_strategies_for_roi()
    
    # Time windows we're tracking
    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
    
    # Initialize ROI tracking for all strategies
    roi_data = {}
    for strategy_name in strategies.keys():
        roi_data[strategy_name] = {window: {'roi': 0.0, 'results': []} for window in time_windows}
    
    # Calculate ROI for all strategies and weeks efficiently
    for week_num in historical_weeks:
        # Load data once per week
        from database.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        props_df = db_manager.get_props_as_dataframe(week=week_num, upcoming_only=False)
        
        if props_df.empty:
            continue
            
        # Add time window classification
        props_df['time_window'] = props_df['Commence Time'].apply(classify_game_time_window)
        
        # Score props once per week
        from database.database_enhanced_data_processor import DatabaseEnhancedFootballDataProcessor
        data_processor_historical = DatabaseEnhancedFootballDataProcessor(max_week=week_num)
        scorer_historical = AdvancedPropScorer(data_processor_historical)
        
        # Add total_score column by calculating comprehensive score for each prop
        total_scores = []
        for _, row in props_df.iterrows():
            if pd.isna(row.get('Stat Type')) or row.get('Stat Type') is None:
                total_scores.append(0.0)
                continue
            
            score_data = scorer_historical.calculate_comprehensive_score(
                row['Player'],
                row.get('Opp. Team Full', row['Opp. Team']),
                row['Stat Type'],
                row['Line'],
                row.get('Odds', 0),
                row.get('Home Team'),
                row.get('Away Team'),
                row.get('Team'),
                row.get('team_pos_rank_stat_type')
            )
            total_scores.append(score_data['total_score'])
        
        props_df['total_score'] = total_scores
        
        # Update team assignments
        odds_api_temp = OddsAPI(ODDS_API_KEY)
        props_df = odds_api_temp.update_team_assignments(props_df, data_processor_historical)
        
        # Load box score for actual results
        from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
        box_score_loader = DatabaseBoxScoreLoader()
        box_score_df = box_score_loader.load_week_data_from_db(week_num)
        
        if box_score_df.empty:
            continue
            
        # Add actual results
        for idx, row in props_df.iterrows():
            actual_stat = get_actual_stat(
                row['Player'],
                row['Stat Type'],
                box_score_df
            )
            props_df.at[idx, 'actual_result'] = actual_stat
        
        # Add streak calculation for each prop
        streak_values = []
        for _, row in props_df.iterrows():
            try:
                streak = data_processor_historical.get_player_streak(
                    row['Player'],
                    row['Stat Type'],
                    row['Line']
                )
                streak_values.append(streak)
            except Exception as e:
                streak_values.append(0)
        
        props_df['streak'] = streak_values
        
        # Now calculate ROI for all strategies using the same data
        for strategy_name, strategy_params in strategies.items():
            try:
                week_roi = calculate_strategy_roi_for_week_with_data(
                    props_df,
                    data_processor_historical,  # Pass the data processor for position filtering
                    strategy_params['score_min'],
                    strategy_params['score_max'],
                    odds_min=strategy_params.get('odds_min', -400),
                    odds_max=strategy_params.get('odds_max', -150),
                    streak_min=strategy_params.get('streak_min'),
                    max_players=strategy_params.get('max_players', 5),
                    position_filter=strategy_params.get('position_filter', False)
                )
                
                if week_roi:
                    # Add this data to our results
                    for window, window_data in week_roi.items():
                        roi_data[strategy_name][window]['roi'] += window_data['roi']
                        roi_data[strategy_name][window]['results'].extend(window_data['results'])
                
            except Exception as e:
                continue
    
    return roi_data


def is_player_in_matchup(row, matchup_string):
    """Check if a player's team is in the specified matchup"""
    if not matchup_string or pd.isna(row.get('Team')):
        return False
    
    # Extract teams from matchup string (e.g., "PHI @ NYG" -> ["PHI", "NYG"])
    teams_in_matchup = matchup_string.replace(' @ ', ' ').split()
    
    # Get player's team abbreviation
    player_team_abbrev = get_team_abbreviation(row['Team'])
    
    return player_team_abbrev in teams_in_matchup


def main():
    """Main Streamlit application"""
    st.title("🏈 NFL Player Prop Optimizer")
    st.markdown("Analyze NFL player props using matchup data and player history")
    
    # Check if API key is configured
    if ODDS_API_KEY == "YOUR_API_KEY_HERE":
        st.error("⚠️ API Key not configured!")
        st.markdown("""
        **To use this application:**
        1. Get your free API key from [The Odds API](https://the-odds-api.com/)
        2. Replace `YOUR_API_KEY_HERE` in the code with your actual API key
        3. Restart the application
        """)
        st.stop()
    
    # Get current week and available historical weeks first
    from utils import get_current_week_from_dates
    current_week_temp = get_current_week_from_dates()
    
    # Get available weeks from database
    from database.database_manager import DatabaseManager
    db_manager = DatabaseManager()
    
    # Test database connection
    try:
        with db_manager.get_session() as session:
            pass  # Connection successful
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()
    
    historical_weeks = db_manager.get_available_weeks_from_db()
    
    # Create week selector options
    week_options = [f"Week {current_week_temp} (Current)"]
    for week in sorted(historical_weeks, reverse=True):
        if week != current_week_temp:
            week_options.append(f"Week {week}")
    
    # Week selector dropdown at the top
    selected_week_display = st.selectbox(
        "📅 Select Week",
        options=week_options,
        index=0,
        help="View current week props or historical data from previous weeks"
    )
    
    # Extract week number from selection
    selected_week = int(selected_week_display.split()[1])
    is_historical = selected_week != current_week_temp
    
    # OPTIMIZATION: Cache data processor with Streamlit caching
    @st.cache_resource
    def get_cached_data_processor(max_week, cache_version="v1.0"):
        from database.database_enhanced_data_processor import DatabaseEnhancedFootballDataProcessor
        return DatabaseEnhancedFootballDataProcessor(data_dir="data", max_week=max_week, skip_calculations=True)
    
    # Initialize components with max_week for historical filtering (cache in session state)
    # Only create once per week selection to avoid repeated expensive initialization
    if ('data_processor' not in st.session_state or 
        'data_processor_week' not in st.session_state or 
        st.session_state.data_processor_week != selected_week):
        
        data_processor = get_cached_data_processor(selected_week, "v2.0")  # Updated for defensive rankings fix
        st.session_state.data_processor = data_processor
        st.session_state.data_processor_week = selected_week
    else:
        data_processor = st.session_state.data_processor
    
    if ('scorer' not in st.session_state or 
        'scorer_week' not in st.session_state or 
        st.session_state.scorer_week != selected_week):
        
        scorer = AdvancedPropScorer(data_processor)
        st.session_state.scorer = scorer
        st.session_state.scorer_week = selected_week
    else:
        scorer = st.session_state.scorer
    
    # Initialize odds_api (lightweight, doesn't need caching)
    odds_api = OddsAPIWithDB(ODDS_API_KEY)
    st.session_state.odds_api = odds_api
    
    # Check and merge historical props for games that have started
    # ONLY check current week, not historical weeks the user is browsing
    if not is_historical:
        # Create progress bar for historical merge check
        hist_progress_bar = st.progress(0, text="Checking for historical odds updates...")
        
        def update_progress(progress, message):
            hist_progress_bar.progress(progress, text=message)
        
        # Check historical merge for current week and previous weeks within 48-hour window
        from datetime import datetime, timedelta
        current_time = datetime.utcnow()
        forty_eight_hours_ago = current_time - timedelta(hours=48)
        
        # Find all weeks that have games within the 48-hour window
        with db_manager.get_session() as session:
            recent_games = session.query(Game).filter(
                Game.commence_time >= forty_eight_hours_ago,
                Game.commence_time <= current_time,
                Game.historical_merged == False
            ).all()
            
            weeks_to_check = set()
            for game in recent_games:
                weeks_to_check.add(game.week)
        
        # Check each week that needs historical merge
        total_weeks = len(weeks_to_check)
        if total_weeks > 0:
            for i, week in enumerate(sorted(weeks_to_check)):
                progress = int((i / total_weeks) * 100)
                update_progress(progress, f"Checking Week {week} for historical merge...")
                db_manager.check_and_merge_historical_props(week, odds_api=odds_api, progress_callback=update_progress)
            
            update_progress(100, "Historical merge check complete!")
        else:
            update_progress(100, "No weeks need historical merge")
        
        hist_progress_bar.empty()  # Clear the progress bar
    
    # Initialize per-week cache dictionary if not exists
    if 'week_cache' not in st.session_state:
        st.session_state.week_cache = {}
    
    # Cache management when week changes
    if 'selected_week' not in st.session_state or st.session_state.selected_week != selected_week:
        old_week = st.session_state.get('selected_week')
        
        # Save current week data to cache before switching
        if old_week is not None:
            st.session_state.week_cache[old_week] = {
                'alt_line_manager': st.session_state.get('alt_line_manager'),
                'all_scored_props': st.session_state.get('all_scored_props'),
                'props_df_cache': st.session_state.get('props_df_cache'),
                'odds_data_cache': st.session_state.get('odds_data_cache')
            }
        
        # Update selected week
        st.session_state.selected_week = selected_week
        
        # Restore cached data for new week if available
        if selected_week in st.session_state.week_cache:
            cache = st.session_state.week_cache[selected_week]
            st.session_state.alt_line_manager = cache.get('alt_line_manager')
            st.session_state.all_scored_props = cache.get('all_scored_props')
            st.session_state.props_df_cache = cache.get('props_df_cache')
            st.session_state.odds_data_cache = cache.get('odds_data_cache')
        else:
            # Clear cache for new week (will be loaded fresh)
            for key in ['alt_line_manager', 'all_scored_props', 'props_df_cache', 'odds_data_cache']:
                if key in st.session_state:
                    del st.session_state[key]
    
    # Sidebar configuration with control buttons
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown("---")
        
        # Export button
        export_button = st.button("📥 Export to CSV", type="secondary", use_container_width=True)
    
    # Fetch and display data
    try:
        # Initialize info messages list
        info_messages = []
        
        # Check if we have all scored props cached
        if 'all_scored_props' in st.session_state:
            # Use cached scored props
            all_props = st.session_state.all_scored_props
            odds_data = st.session_state.odds_data_cache
            alt_line_manager = st.session_state.alt_line_manager
            
            if is_historical:
                info_messages.append(('info', f"ℹ️ Using cached Week {selected_week} historical data ({len(all_props)} total props)"))
            else:
                info_messages.append(('info', f"ℹ️ Using cached data ({len(all_props)} total props)"))
        else:
            # Fetch fresh data with progress bars
            progress_bar = st.progress(0, text="Loading player props data from database...")
            
            # Always load from database (both current and historical data)
            from database.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            
            if is_historical:
                progress_bar.progress(10, text=f"Loading Week {selected_week} historical data from database...")
                # For historical data, show all games (including completed ones)
                props_df = db_manager.get_props_as_dataframe(week=selected_week, upcoming_only=False)
                
                
                if props_df.empty:
                    st.error(f"❌ No historical data found for Week {selected_week} in database.")
                    st.stop()
                
                progress_bar.progress(20, text=f"Loaded {len(props_df)} historical props from database...")
                
                # For historical weeks, skip all API calls and use database data only                
                # Skip all API processing for historical weeks
                odds_data = []  # Empty for compatibility
                fallback_used = True  # Always use database mode
                
                # Cache the raw data
                st.session_state.props_df_cache = props_df
                st.session_state.odds_data_cache = odds_data
                
                # Initialize alternate line manager (for compatibility)
                alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
                st.session_state.alt_line_manager = alt_line_manager
                
                # Database mode: all data is already loaded with alternates
                progress_bar.progress(40, text="Using database data (includes alternates)...")
                
                # For historical weeks, we can skip the rest of the API processing
                # and go directly to scoring the props
                progress_bar.progress(50, text="Calculating scores for historical props...")
                
                stat_types_in_data = props_df['Stat Type'].unique() if not props_df.empty else []
                
                # Process and score all props for historical weeks
                all_props = process_props_and_score(
                    props_df, stat_types_in_data, scorer, data_processor, 
                    alt_line_manager, fallback_used, progress_bar
                )
                
                # Cache the scored props
                st.session_state.all_scored_props = all_props
                
                progress_bar.progress(100, text="Historical data loaded successfully!")
                progress_bar.empty()  # Clear the progress bar
                
                # Info messages are collected but not displayed to keep UI clean
                # (Messages are still logged to console for debugging)
                
                # Continue to table display (don't return early)
            elif not is_historical:
                # For current week, use the actual current week (not just the latest in database)
                current_week = get_current_week_from_dates()
                
                # First, check database for upcoming games with fresh data
                progress_bar.progress(10, text=f"Checking database for Week {current_week} upcoming games...")
                from datetime import datetime
                all_props_df = db_manager.get_props_as_dataframe(week=current_week, upcoming_only=False)
                
                # Filter to upcoming games only
                if not all_props_df.empty:
                    # Convert Commence Time to datetime if it's a string
                    if 'Commence Time' in all_props_df.columns:
                        if all_props_df['Commence Time'].dtype == 'object':
                            all_props_df['Commence Time'] = pd.to_datetime(all_props_df['Commence Time'], utc=True)
                        elif str(all_props_df['Commence Time'].dtype).startswith('datetime64'):
                            # Already datetime64, make sure it's timezone-aware
                            if all_props_df['Commence Time'].dt.tz is None:
                                all_props_df['Commence Time'] = all_props_df['Commence Time'].dt.tz_localize('UTC')
                    
                    # Filter to upcoming games (use pd.Timestamp for comparison with datetime64)
                    from datetime import timezone
                    current_time = pd.Timestamp.now(tz='UTC')
                    upcoming_props_df = all_props_df[all_props_df['Commence Time'] > current_time].copy()
                else:
                    upcoming_props_df = pd.DataFrame()
                
                # Determine if we need to fetch from API
                need_api_fetch = False
                fetch_reason = ""
                
                if upcoming_props_df.empty:
                    # No upcoming games in database - need fresh data from API
                    need_api_fetch = True
                    fetch_reason = "No upcoming games found in database"
                elif not db_manager.is_data_fresh('props', max_age_hours=2):
                    # Data exists but is stale - but only refresh if there are upcoming games
                    if len(upcoming_props_df) > 0:
                        need_api_fetch = True
                        fetch_reason = "Database props are stale (> 2 hours old) for upcoming games"
                    else:
                        # No upcoming games, just use existing data (completed games)
                        props_df = all_props_df  # Use all props including completed games
                        progress_bar.progress(20, text=f"Using database props (no upcoming games to refresh)...")
                        info_messages.append(('info', f"ℹ️ Loaded {len(props_df)} props from database (no upcoming games)"))
                else:
                    # Fresh upcoming games found in database - use them!
                    props_df = upcoming_props_df
                    progress_bar.progress(20, text=f"Using fresh database props (< 2 hours old)...")
                    info_messages.append(('success', f"✅ Loaded {len(props_df)} upcoming game props from database (fresh data)"))
                
                # Fetch from API if needed
                if need_api_fetch:
                    progress_bar.progress(30, text="Fetching fresh odds from API...")
                    
                    try:
                        # Fetch fresh odds data
                        progress_bar.progress(35, text="Fetching events from API...")
                        events_data = odds_api.get_player_props()
                        
                        if not events_data:
                            if not all_props_df.empty:
                                st.warning("⚠️ No events found from API. Using database data as fallback.")
                                props_df = all_props_df.copy()
                            else:
                                st.error("❌ No events found from API and no data in database.")
                                st.stop()
                        else:
                            # Now fetch alternate lines
                            progress_bar.progress(40, text="Fetching alternate lines from API (this may take 30-60 seconds)...")
                            odds_data = odds_api.fetch_all_alternate_lines_optimized()
                            
                            if odds_data:
                                progress_bar.progress(50, text="Processing fresh odds data...")
                                
                                # Convert API data to DataFrame format
                                props_df = odds_api.convert_alternate_lines_to_props_df(odds_data)
                                
                                if not props_df.empty:
                                    # Update team assignments
                                    progress_bar.progress(55, text="Updating team assignments...")
                                    props_df = odds_api.update_team_assignments(props_df, data_processor)
                                    
                                    # Look up defensive rankings from database (don't recalculate)
                                    progress_bar.progress(60, text="Looking up defensive rankings from database...")
                                    
                                    # BYPASS: Skip defensive ranking calculation entirely to prevent infinite loop
                                    print("⚠️ BYPASSING defensive ranking calculation to prevent infinite loop")
                                    print("   All defensive ranks will be set to None (no ranking data)")
                                    
                                    # Set all ranks to None for all props
                                    for idx in props_df.index:
                                        props_df.at[idx, 'team_pos_rank_stat_type'] = None
                                    
                                    progress_bar.progress(70, text="Bypassed defensive ranking calculation...")
                                    # Continue to the next section without any defensive ranking logic
                                    
                                    # Get all unique opponent/stat combinations
                                    unique_combos = props_df[['Opp. Team Full', 'Stat Type']].drop_duplicates()
                                    
                                    # Check if we have cached rankings for this week
                                    cache_key = f"defensive_ranks_week_{current_week}"
                                    if cache_key in st.session_state:
                                        rank_cache = st.session_state[cache_key]
                                        print(f"📊 Using cached defensive rankings for Week {current_week}")
                                    else:
                                        # Initialize with empty cache to prevent infinite loop
                                        rank_cache = {}
                                        print(f"📊 Initializing empty defensive rankings cache for Week {current_week}")
                                    
                                    # First, try to get all existing ranks from database in one query
                                    with db_manager.get_session() as session:
                                        # Get all existing ranks for these combinations
                                        existing_ranks = session.query(Prop.opp_team_full, Prop.stat_type, Prop.team_pos_rank_stat_type).filter(
                                            Prop.opp_team_full.in_(unique_combos['Opp. Team Full'].dropna().tolist()),
                                            Prop.stat_type.in_(unique_combos['Stat Type'].dropna().tolist()),
                                            Prop.team_pos_rank_stat_type.isnot(None)
                                        ).distinct().all()
                                        
                                        # Build cache from existing ranks
                                        for opp_team, stat_type, rank in existing_ranks:
                                            if opp_team and stat_type:
                                                rank_cache[(opp_team, stat_type)] = rank
                                        
                                        # Only calculate missing ranks if we have any
                                        missing_combos = []
                                        for _, row in unique_combos.iterrows():
                                            opp_team = row['Opp. Team Full']
                                            stat_type = row['Stat Type']
                                            
                                            if pd.isna(opp_team) or opp_team == 'Unknown' or not opp_team:
                                                continue
                                            
                                            if (opp_team, stat_type) not in rank_cache:
                                                missing_combos.append((opp_team, stat_type))
                                        
                                        # If we have missing ranks, skip calculation for now to prevent infinite loop
                                        if missing_combos:
                                            print(f"⚠️ Skipping defensive rank calculation for {len(missing_combos)} combinations to prevent infinite loop")
                                            print(f"   Missing combinations: {missing_combos[:5]}{'...' if len(missing_combos) > 5 else ''}")
                                            
                                            # Set missing ranks to None to prevent infinite loop
                                            for opp_team, stat_type in missing_combos:
                                                if (opp_team, stat_type) not in rank_cache:
                                                    rank_cache[(opp_team, stat_type)] = None
                                    
                                    # Cache the rankings for this week
                                    st.session_state[cache_key] = rank_cache
                                    print(f"📊 Cached defensive rankings for Week {current_week}")
                                    
                                    # Apply ranks to props
                                    for idx in props_df.index:
                                        opp_team = props_df.at[idx, 'Opp. Team Full']
                                        stat_type = props_df.at[idx, 'Stat Type']
                                        
                                        if pd.isna(opp_team) or opp_team == 'Unknown' or not opp_team:
                                            props_df.at[idx, 'team_pos_rank_stat_type'] = None
                                        else:
                                            rank = rank_cache.get((opp_team, stat_type))
                                            props_df.at[idx, 'team_pos_rank_stat_type'] = rank
                                    
                                    # Add week number
                                    props_df['week'] = current_week
                                    
                                    # Filter to only complete props (with all required fields)
                                    # Note: team_pos_rank_stat_type can be None (not yet calculated)
                                    complete_props = props_df[
                                        props_df['week'].notna() &
                                        (props_df['Team'] != 'Unknown') &
                                        props_df['Team'].notna()
                                    ].copy()
                                    
                                    # Calculate how many were incomplete
                                    incomplete_count = len(props_df) - len(complete_props)
                                    
                                    # Store ONLY complete props to database
                                    if not complete_props.empty:
                                        progress_bar.progress(65, text="Storing to database...")
                                        # Convert to database format
                                        props_list = []
                                        for _, row in complete_props.iterrows():
                                            prop_dict = {
                                                'player': row['Player'],
                                                'stat_type': row['Stat Type'],
                                                'line': row['Line'],
                                                'odds': row['Odds'],
                                                'bookmaker': row.get('Bookmaker', 'FanDuel'),
                                                'is_alternate': row.get('is_alternate', True),
                                                'player_team': row['Team'],
                                                'opp_team': row.get('Opp. Team', ''),
                                                'opp_team_full': row['Opp. Team Full'],
                                                'team_pos_rank_stat_type': row['team_pos_rank_stat_type'],
                                                'week': row['week'],
                                                'home_team': row['Home Team'],
                                                'away_team': row['Away Team'],
                                                'commence_time': row['Commence Time'],
                                                'game_id': row.get('event_id', f"{row['Away Team']}_at_{row['Home Team']}")
                                            }
                                            props_list.append(prop_dict)
                                        
                                        games_data = odds_api._extract_games_data(odds_data)
                                        odds_api.store_props_to_db(props_list, games_data)
                                        
                                        # After storing new games, check if any need historical merge
                                        # (e.g., games starting soon that just got added)
                                        # Check if there are games that need historical merge
                                        def update_merge_progress(prog, msg):
                                            # Map 0-10 progress to 66-69 range
                                            actual_progress = 66 + int((prog / 10) * 3)
                                            progress_bar.progress(actual_progress, text=msg)
                                        
                                        merge_result = db_manager.check_and_merge_historical_props(current_week, odds_api=odds_api, progress_callback=update_merge_progress)
                                        if merge_result.get('games_merged', 0) == 0:
                                            progress_bar.progress(66, text="No games need historical merge...")
                                            info_messages.append(('info', f"ℹ️ No games need historical merge"))
                                        else:
                                            # Add transparency note about historical odds timing
                                            info_messages.append(('info', f"ℹ️ Historical odds are based on 2 hours before game time for consistency"))
                                        
                                        # Use complete_props for display
                                        props_df = complete_props
                                        
                                        progress_bar.progress(70, text=f"Loaded {len(props_df)} fresh props from API...")
                                        info_messages.append(('success', f"✅ Successfully fetched and stored {len(props_df)} complete props from API"))
                                        if incomplete_count > 0:
                                            info_messages.append(('warning', f"⚠️ Skipped {incomplete_count} props with incomplete data"))
                                    else:
                                        st.error("❌ No complete props to store after processing")
                                        st.stop()
                                else:
                                    # API returned data but no props could be processed - use database
                                    if not all_props_df.empty:
                                        props_df = all_props_df.copy()
                                        info_messages.append(('info', f"ℹ️ API returned no processable props, using database data ({len(props_df)} props)"))
                                    else:
                                        st.error("❌ No props found in API response and no data in database.")
                                        st.stop()
                            else:
                                # API call failed - use database
                                if not all_props_df.empty:
                                    props_df = all_props_df.copy()
                                    info_messages.append(('info', f"ℹ️ API fetch failed, using database data ({len(props_df)} props)"))
                                else:
                                    st.error("❌ Failed to fetch odds from API and no data in database.")
                                    st.stop()
                                
                    except Exception as e:
                        # API error - use database
                        if not all_props_df.empty:
                            props_df = all_props_df.copy()
                            info_messages.append(('info', f"ℹ️ API error: {str(e)[:50]}..., using database data ({len(props_df)} props)"))
                        else:
                            st.error(f"❌ Error fetching fresh odds from API: {e}")
                            st.error("No data in database to fall back to.")
                            st.stop()
                
                # Merge in completed games from this week (so user can see historical recommendations)
                if not all_props_df.empty:
                    current_time = pd.Timestamp.now(tz='UTC')
                    
                    # Ensure datetime is timezone-aware
                    if 'Commence Time' in all_props_df.columns:
                        if all_props_df['Commence Time'].dtype == 'object':
                            all_props_df['Commence Time'] = pd.to_datetime(all_props_df['Commence Time'], utc=True)
                        elif str(all_props_df['Commence Time'].dtype).startswith('datetime64'):
                            if all_props_df['Commence Time'].dt.tz is None:
                                all_props_df['Commence Time'] = all_props_df['Commence Time'].dt.tz_localize('UTC')
                    
                    # Get completed games from this week
                    completed_props_df = all_props_df[all_props_df['Commence Time'] <= current_time].copy()
                    
                    if not completed_props_df.empty:
                        # Merge completed games with upcoming games
                        props_df = pd.concat([props_df, completed_props_df], ignore_index=True)
                        # Remove duplicates (in case of overlap)
                        props_df = props_df.drop_duplicates(subset=['Player', 'Stat Type', 'Line', 'Bookmaker', 'Commence Time'], keep='first')
                        print(f"📊 Included {len(completed_props_df)} props from {completed_props_df['Commence Time'].nunique()} completed game(s) this week")
                
                # Show user what games are being displayed
                if not props_df.empty:
                    # Ensure datetime comparison is timezone-aware
                    if 'Commence Time' in props_df.columns:
                        if props_df['Commence Time'].dtype == 'object':
                            props_df['Commence Time'] = pd.to_datetime(props_df['Commence Time'], utc=True)
                        elif str(props_df['Commence Time'].dtype).startswith('datetime64'):
                            if props_df['Commence Time'].dt.tz is None:
                                props_df['Commence Time'] = props_df['Commence Time'].dt.tz_localize('UTC')
                    
                    game_times = props_df['Commence Time'].unique()
                    current_time = pd.Timestamp.now(tz='UTC')
                    upcoming_games = [gt for gt in game_times if pd.notna(gt) and gt > current_time]
                    if upcoming_games:
                        next_game = min(upcoming_games)
                        # Convert to datetime for formatting
                        if hasattr(next_game, 'to_pydatetime'):
                            next_game = next_game.to_pydatetime()
                    else:
                        st.warning("⚠️ No upcoming games found - all games may have already started")
                
                # Update team assignments using data processor
                props_df = odds_api.update_team_assignments(props_df, data_processor)
                
                # Set compatibility variables
                odds_data = []  # Empty for compatibility
                fallback_used = True  # Always use database mode
                
                # Cache the raw data
                st.session_state.props_df_cache = props_df
                st.session_state.odds_data_cache = odds_data
                
                # Initialize alternate line manager (for compatibility)
                alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
                st.session_state.alt_line_manager = alt_line_manager
                
                # Database mode: all data is already loaded with alternates
                progress_bar.progress(40, text="Using database data (includes alternates)...")
            
            # Process and score all props
            progress_bar.progress(50, text="Calculating scores for all props...")
            
            stat_types_in_data = props_df['Stat Type'].unique() if not props_df.empty else []
            all_props = process_props_and_score(
                props_df, stat_types_in_data, scorer, data_processor, 
                alt_line_manager, fallback_used, progress_bar
            )
            
            # If viewing historical data, add actual results from box score
            if is_historical:
                progress_bar.progress(90, text="Loading actual results from database...")
                
                # Load box score data from database instead of CSV files
                from database.database_enhanced_data_processor import DatabaseBoxScoreLoader
                box_score_loader = DatabaseBoxScoreLoader()
                box_score_df = box_score_loader.load_week_data_from_db(selected_week)
                
                if not box_score_df.empty:
                    for prop in all_props:
                        actual_stat = get_actual_stat(
                            prop['Player'],
                            prop['Stat Type'],
                            box_score_df
                        )
                        prop['actual_result'] = actual_stat
                else:
                    # No box score data available
                    for prop in all_props:
                        prop['actual_result'] = None
            else:
                # Current week - no results yet
                for prop in all_props:
                    prop['actual_result'] = None
            
            progress_bar.progress(100, text="Complete!")
            progress_bar.empty()
            
            # Cache the processed data
            st.session_state.all_scored_props = all_props
            
            # Add appropriate success message based on data source
            if is_historical:
                info_messages.append(('info', f"📜 Loaded {len(all_props)} historical props from Week {selected_week}"))
            else:
                info_messages.append(('success', f"✅ Loaded {len(all_props)} total props from database"))
        
        # Handle export if button was clicked
        if export_button:
            with st.spinner("Generating export..."):
                all_export_data = []
                
                # Convert all_props to export format
                for prop in all_props:
                    export_row = {
                        'Stat Type': prop['Stat Type'],
                        'Player': prop['Player'],
                        'Team': prop['Team'],
                        'Opp. Team': prop['Opp. Team'],
                        'Line': prop['Line'],
                        'Odds': format_odds(prop.get('Odds', 0)),
                        'Opp. Pos. Rank': prop['team_rank'],
                        'Score': prop['total_score'],
                        'L5': f"{prop['l5_over_rate']*100:.1f}%",
                        'Over Rate': f"{prop['over_rate']*100:.1f}%",
                        'Player Avg': f"{prop['player_avg']:.1f}",
                        'Is Alternate': prop.get('is_alternate', False)
                    }
                    all_export_data.append(export_row)
                
                # Create DataFrame and export
                export_df = pd.DataFrame(all_export_data)
                export_df = export_df.sort_values(['Stat Type', 'Player', 'Is Alternate'])
                
                # Export as CSV for download
                csv_data = export_df.to_csv(index=False)
                
                # Show download button
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download Data",
                    data=csv_data,
                    file_name=f"nfl_props_export_{timestamp}.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                stat_types_count = len(export_df['Stat Type'].unique())
                st.success(f"✅ Export ready! {len(export_df)} total props (including alternates) across {stat_types_count} stat types")
        
        # Prepare results dataframe
        results_df = pd.DataFrame(all_props)
        
        # Format 'Opp. Team' column to show abbreviations (e.g., "@ NYJ" or "vs LV")
        # instead of full team names for cleaner display
        team_abbrev_mapping = {
            'Philadelphia Eagles': 'PHI', 'New York Giants': 'NYG', 'Dallas Cowboys': 'DAL',
            'Washington Commanders': 'WAS', 'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA',
            'Los Angeles Rams': 'LAR', 'Arizona Cardinals': 'ARI', 'Green Bay Packers': 'GB',
            'Minnesota Vikings': 'MIN', 'Detroit Lions': 'DET', 'Chicago Bears': 'CHI',
            'Tampa Bay Buccaneers': 'TB', 'New Orleans Saints': 'NO', 'Atlanta Falcons': 'ATL',
            'Carolina Panthers': 'CAR', 'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV',
            'Los Angeles Chargers': 'LAC', 'Denver Broncos': 'DEN', 'Buffalo Bills': 'BUF',
            'Miami Dolphins': 'MIA', 'New England Patriots': 'NE', 'New York Jets': 'NYJ',
            'Baltimore Ravens': 'BAL', 'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE',
            'Pittsburgh Steelers': 'PIT', 'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND',
            'Jacksonville Jaguars': 'JAX', 'Tennessee Titans': 'TEN'
        }
        
        def format_opp_team_display(row):
            """Format opponent team as '@ NYJ' or 'vs LV'"""
            opp_team = row.get('Opp. Team', '')
            player_team = row.get('Team', '')
            home_team = row.get('Home Team', '')
            
            # If already formatted (starts with @ or vs), return as is
            if isinstance(opp_team, str) and (opp_team.startswith('@') or opp_team.startswith('vs')):
                return opp_team
            
            # Get abbreviation
            opp_abbrev = team_abbrev_mapping.get(opp_team, opp_team)
            
            # Determine if home or away
            if player_team == home_team:
                return f"vs {opp_abbrev}"
            else:
                return f"@ {opp_abbrev}"
        
        if 'Opp. Team' in results_df.columns:
            results_df['Opp. Team'] = results_df.apply(format_opp_team_display, axis=1)
        
        # Get available stat types
        available_stat_types = sorted(results_df['Stat Type'].unique())
        
        # Get available matchups
        results_df['Matchup'] = results_df.apply(get_matchup_string, axis=1)
        available_matchups = sorted([m for m in results_df['Matchup'].unique() if m is not None])
        
        # Determine which games are upcoming (not started yet) - only for current week
        matchup_to_upcoming = {}
        if not is_historical:
            # Only filter past games when viewing current week
            current_time = pd.Timestamp.now(tz='UTC')
            
            # Create a map of matchup -> is_upcoming
            for matchup in available_matchups:
                # Get all props for this matchup to find its commence time
                matchup_props = results_df[results_df['Matchup'] == matchup]
                if not matchup_props.empty:
                    # Get the first commence time for this matchup (they should all be the same)
                    commence_time = matchup_props.iloc[0]['Commence Time']
                    
                    # Ensure datetime comparison is timezone-aware
                    if pd.notna(commence_time):
                        if isinstance(commence_time, str):
                            commence_time = pd.to_datetime(commence_time, utc=True)
                        elif hasattr(commence_time, 'tz_localize') and commence_time.tz is None:
                            commence_time = commence_time.tz_localize('UTC')
                        elif not hasattr(commence_time, 'tz') or commence_time.tz is None:
                            # Python datetime without timezone
                            commence_time = pd.Timestamp(commence_time).tz_localize('UTC')
                        
                        # Check if game is upcoming
                        matchup_to_upcoming[matchup] = commence_time > current_time
                    else:
                        # If no commence time, assume it's upcoming
                        matchup_to_upcoming[matchup] = True
                else:
                    matchup_to_upcoming[matchup] = True
        
        # Initialize session state for checkbox selections if not exists
        if 'selected_stat_types' not in st.session_state:
            st.session_state.selected_stat_types = {stat: True for stat in available_stat_types}
        
        if 'selected_games' not in st.session_state:
            if is_historical:
                # Historical weeks: all games selected by default
                st.session_state.selected_games = {game: True for game in available_matchups}
            else:
                # Current week: only upcoming games selected by default
                st.session_state.selected_games = {
                    game: matchup_to_upcoming.get(game, True) for game in available_matchups
                }
        
        # Update session state with any new stat types or games
        for stat in available_stat_types:
            if stat not in st.session_state.selected_stat_types:
                st.session_state.selected_stat_types[stat] = True
        
        for game in available_matchups:
            if game not in st.session_state.selected_games:
                if is_historical:
                    # Historical weeks: new games default to selected
                    st.session_state.selected_games[game] = True
                else:
                    # Current week: new games default to selected only if they're upcoming
                    st.session_state.selected_games[game] = matchup_to_upcoming.get(game, True)
        
        # Remove stat types and games that are no longer in the current week's data
        # (Important when switching between weeks)
        stats_to_remove = [stat for stat in st.session_state.selected_stat_types if stat not in available_stat_types]
        for stat in stats_to_remove:
            del st.session_state.selected_stat_types[stat]
        
        games_to_remove = [game for game in st.session_state.selected_games if game not in available_matchups]
        for game in games_to_remove:
            del st.session_state.selected_games[game]
        
        # Sidebar filters
        with st.sidebar:
            st.subheader("📊 Filters")
            
            # Stat Type filter with expander
            with st.expander("🏈 Stat Types", expanded=False):
                # Select All / Clear All buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All", key="select_all_stats", use_container_width=True):
                        for stat in available_stat_types:
                            st.session_state.selected_stat_types[stat] = True
                        st.rerun()
                with col2:
                    if st.button("Clear All", key="clear_all_stats", use_container_width=True):
                        for stat in available_stat_types:
                            st.session_state.selected_stat_types[stat] = False
                        st.rerun()
                
                st.markdown("---")
                
                # Individual checkboxes for stat types
                for stat_type in available_stat_types:
                    st.session_state.selected_stat_types[stat_type] = st.checkbox(
                        stat_type,
                        value=st.session_state.selected_stat_types.get(stat_type, True),
                        key=f"stat_{stat_type}"
                    )
            
            # Game filter with expander
            with st.expander("🎮 Games", expanded=False):
                # Select All / Clear All buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All", key="select_all_games", use_container_width=True):
                        for game in available_matchups:
                            st.session_state.selected_games[game] = True
                        st.rerun()
                with col2:
                    if st.button("Clear All", key="clear_all_games", use_container_width=True):
                        for game in available_matchups:
                            st.session_state.selected_games[game] = False
                        st.rerun()
                
                st.markdown("---")
                
                # Individual checkboxes for games
                for game in available_matchups:
                    st.session_state.selected_games[game] = st.checkbox(
                        game,
                        value=st.session_state.selected_games.get(game, True),
                        key=f"game_{game}"
                    )
            
            # Odds filter with expander
            with st.expander("💰 Odds Range", expanded=False):
                st.markdown("Filter props by American odds range")
                
                col1, col2 = st.columns(2)
                with col1:
                    odds_min = st.number_input(
                        "Min Odds",
                        min_value=-1000,
                        max_value=1000,
                        value=-450,
                        step=10,
                        key="odds_min",
                        help="Minimum odds (e.g., -450)"
                    )
                with col2:
                    odds_max = st.number_input(
                        "Max Odds",
                        min_value=-1000,
                        max_value=1000,
                        value=200,
                        step=10,
                        key="odds_max",
                        help="Maximum odds (e.g., +200)"
                    )
                
                if odds_min > odds_max:
                    st.warning("⚠️ Min odds should be less than max odds")
        
        # Get selected items from session state
        selected_stat_types = [stat for stat, selected in st.session_state.selected_stat_types.items() if selected]
        selected_games = [game for game, selected in st.session_state.selected_games.items() if selected]
        
        # Filter by selected stat types
        if selected_stat_types:
            filtered_results_df = results_df[results_df['Stat Type'].isin(selected_stat_types)].copy()
        else:
            filtered_results_df = pd.DataFrame()
        
        # Filter by selected games
        if selected_games and not filtered_results_df.empty:
            # Filter to only include players from selected matchups
            filtered_results_df = filtered_results_df[
                filtered_results_df['Matchup'].isin(selected_games)
            ].copy()
        
        # Filter by odds range
        if not filtered_results_df.empty:
            filtered_results_df = filtered_results_df[
                (filtered_results_df['Odds'] >= odds_min) & 
                (filtered_results_df['Odds'] <= odds_max)
            ].copy()
        
        # Update sidebar with stats after filtering
        with st.sidebar:
            st.markdown("---")
            
            # Show stats summary
            st.metric("Stat Types Selected", f"{len(selected_stat_types)}/{len(available_stat_types)}")
            st.metric("Games Selected", f"{len(selected_games)}/{len(available_matchups)}")
            st.metric("Odds Range", f"{format_odds(odds_min)} to {format_odds(odds_max)}")
            st.metric("Props Displayed", len(filtered_results_df))
        
        if filtered_results_df.empty:
            st.warning("No props found matching the selected criteria.")
            st.stop()
        
        results_df = filtered_results_df
        
        # Drop the temporary Matchup column before displaying
        if 'Matchup' in results_df.columns:
            results_df = results_df.drop('Matchup', axis=1)
        
        # Sort by Score (descending), then by Stat Type and Player name
        results_df = results_df.sort_values(['total_score'], ascending=[False])
        
        # Format the display - include Result column if viewing historical data
        if is_historical:
            display_columns = [
                'Stat Type', 'Player', 'Opp. Team', 'team_rank', 'total_score',
                'Line', 'Odds', 'actual_result', 'streak', 'l5_over_rate', 'home_over_rate', 'away_over_rate', 'over_rate'
            ]
        else:
            display_columns = [
                'Stat Type', 'Player', 'Opp. Team', 'team_rank', 'total_score',
                'Line', 'Odds', 'streak', 'l5_over_rate', 'home_over_rate', 'away_over_rate', 'over_rate'
            ]
        
        display_df = results_df[display_columns].copy()
        
        # Format Opp. Pos. Rank as integer (show "N/A" if None)
        display_df['team_rank'] = display_df['team_rank'].apply(
            lambda x: int(x) if pd.notna(x) and x is not None else "N/A"
        )
        
        # Rename columns for display
        if is_historical:
            display_df.columns = [
                'Stat Type', 'Player', 'Opp. Team', 'Opp. Pos. Rank', 'Score',
                'Line', 'Odds', 'Result', 'Streak', 'L5', 'Home', 'Away', '25/26'
            ]
        else:
            display_df.columns = [
                'Stat Type', 'Player', 'Opp. Team', 'Opp. Pos. Rank', 'Score',
                'Line', 'Odds', 'Streak', 'L5', 'Home', 'Away', '25/26'
            ]
        
        # Store numeric Line value BEFORE formatting (needed for Result comparison)
        if is_historical and 'Result' in display_df.columns:
            display_df['Line_numeric'] = display_df['Line'].copy()
            display_df['Result_numeric'] = display_df['Result'].copy()
        
        # Format the line display (need to handle different stat types)
        display_df['Line'] = display_df.apply(
            lambda row: format_line(row['Line'], row['Stat Type']), 
            axis=1
        )
        
        # Format odds
        display_df['Odds'] = display_df['Odds'].apply(format_odds)
        
        # Format Result column if viewing historical data
        if is_historical and 'Result' in display_df.columns:
            # Format Result display - show as number or "-" if None
            display_df['Result'] = display_df['Result'].apply(
                lambda x: f"{x:.1f}" if pd.notna(x) and x is not None else "-"
            )
        
        # Format Score as decimal with 2 decimal places
        display_df['Score_numeric'] = display_df['Score']  # Store for styling
        display_df['Score'] = display_df['Score'].apply(lambda x: f"{x:.2f}")
        
        # Handle None values for all over rates (when no data available)
        display_df['L5_numeric'] = display_df['L5'].apply(lambda x: x * 100 if x is not None and pd.notna(x) else None)
        display_df['Home_numeric'] = display_df['Home'].apply(lambda x: x * 100 if x is not None and pd.notna(x) else None)
        display_df['Away_numeric'] = display_df['Away'].apply(lambda x: x * 100 if x is not None and pd.notna(x) else None)
        display_df['25/26_numeric'] = display_df['25/26'].apply(lambda x: x * 100 if x is not None and pd.notna(x) else None)
        
        # Format L5 over rate as percentage (N/A if no data)
        display_df['L5'] = display_df['L5_numeric'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        
        # Format Home over rate as percentage (N/A if no home games)
        display_df['Home'] = display_df['Home_numeric'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        
        # Format Away over rate as percentage (N/A if no away games)
        display_df['Away'] = display_df['Away_numeric'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        
        # Format season over rate as percentage (N/A if no data)
        display_df['25/26'] = display_df['25/26_numeric'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        
        # Define styling functions
        def style_team_rank(val):
            """Red if 10 or less (good matchup), green if 21 or higher (bad matchup)"""
            try:
                if val <= 10:
                    return 'background-color: #f8d7da; color: #721c24'  # Subtle red bg with dark red text
                elif val >= 21:
                    return 'background-color: #d4edda; color: #155724'  # Subtle green bg with dark green text
                else:
                    return ''
            except:
                return ''
        
        def style_percentage(val):
            """Green if above 60%"""
            try:
                if val > 60:
                    return 'background-color: #d4edda; color: #155724'  # Subtle green bg with dark green text
                else:
                    return ''
            except:
                return ''
        
        # Create a custom styling function that handles all columns
        def apply_all_styles(row):
            styles = pd.Series([''] * len(row), index=row.index)
            
            # Style Team Rank
            if 'Opp. Pos. Rank' in row.index:
                try:
                    val = row['Opp. Pos. Rank']
                    if val <= 10:
                        styles['Opp. Pos. Rank'] = 'background-color: #f8d7da; color: #721c24'
                    elif val >= 21:
                        styles['Opp. Pos. Rank'] = 'background-color: #d4edda; color: #155724'
                except:
                    pass
            
            # Style Score (green=high, orange=medium, red=low)
            if 'Score_numeric' in row.index:
                try:
                    val = row['Score_numeric']
                    if val >= 70:  # High score
                        styles['Score'] = 'background-color: #d4edda; color: #155724'  # Green
                    elif val >= 50:  # Medium score
                        styles['Score'] = 'background-color: #fff3cd; color: #856404'  # Orange/yellow
                    else:  # Low score
                        styles['Score'] = 'background-color: #f8d7da; color: #721c24'  # Red
                except:
                    pass
            
            # Style Result (green if over, red if under)
            if 'Result_numeric' in row.index and 'Line_numeric' in row.index:
                try:
                    result = row['Result_numeric']
                    line = row['Line_numeric']
                    if pd.notna(result) and result is not None and pd.notna(line):
                        if result > line:
                            styles['Result'] = 'background-color: #d4edda; color: #155724'  # Green - hit over
                        else:
                            styles['Result'] = 'background-color: #f8d7da; color: #721c24'  # Red - missed
                except:
                    pass
            
            # Style Streak (green if 3 or more consecutive overs)
            if 'Streak' in row.index:
                try:
                    val = row['Streak']
                    if val >= 3:
                        styles['Streak'] = 'background-color: #d4edda; color: #155724'
                except:
                    pass
            
            # Style L5 based on numeric value
            if 'L5_numeric' in row.index and row['L5_numeric'] > 60:
                styles['L5'] = 'background-color: #d4edda; color: #155724'
            
            # Style Home based on numeric value
            if 'Home_numeric' in row.index and row['Home_numeric'] > 60:
                styles['Home'] = 'background-color: #d4edda; color: #155724'
            
            # Style Away based on numeric value
            if 'Away_numeric' in row.index and row['Away_numeric'] > 60:
                styles['Away'] = 'background-color: #d4edda; color: #155724'
            
            # Style 25/26 based on numeric value
            if '25/26_numeric' in row.index and row['25/26_numeric'] > 60:
                styles['25/26'] = 'background-color: #d4edda; color: #155724'
            
            return styles
        
        # Apply all styling
        styled_df = display_df.style.apply(apply_all_styles, axis=1)
        
        # Drop the numeric columns from display
        if is_historical:
            display_columns_final = ['Stat Type', 'Player', 'Opp. Team', 'Opp. Pos. Rank', 'Line', 'Odds', 'Result', 'Score', 'Streak', 'L5', 'Home', 'Away', '25/26']
        else:
            display_columns_final = ['Stat Type', 'Player', 'Opp. Team', 'Opp. Pos. Rank', 'Line', 'Odds', 'Score', 'Streak', 'L5', 'Home', 'Away', '25/26']
        
        # Display API usage info above the table
        usage_caption = f"📊 Odds from {PREFERRED_BOOKMAKER} (prioritized)"
        
        # Get usage info from odds_api or alt_line_manager
        if 'all_scored_props' in st.session_state and 'alt_line_manager' in st.session_state:
            alt_line_manager = st.session_state.alt_line_manager
            usage_info = alt_line_manager.get_usage_info()
            
            if usage_info.get('requests_used') and usage_info.get('requests_remaining'):
                used = usage_info['requests_used']
                remaining = usage_info['requests_remaining']
                total = usage_info.get('total_quota', int(used) + int(remaining))
                percentage = usage_info.get('percentage_used', 0)
                
                # Add usage to caption with color coding
                if percentage > 80:
                    usage_caption += f" • 🔴 API Usage: {used}/{total} ({percentage:.1f}%) - {remaining} remaining"
                elif percentage > 50:
                    usage_caption += f" • 🟡 API Usage: {used}/{total} ({percentage:.1f}%) - {remaining} remaining"
                else:
                    usage_caption += f" • 🟢 API Usage: {used}/{total} ({percentage:.1f}%) - {remaining} remaining"
        
        st.caption(usage_caption)
        
        # Display the results with styling and selection (disable selection for historical weeks)
        if is_historical:
            # Historical view - no row selection
            event = st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                column_order=display_columns_final
            )
        else:
            # Current week - enable row selection for detailed player analysis
            event = st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                column_order=display_columns_final,
                on_select="rerun",
                selection_mode="single-row"
            )
        
        # Display info messages below the table
        for msg_type, msg_text in info_messages:
            if msg_type == 'info':
                st.info(msg_text)
            elif msg_type == 'success':
                st.success(msg_text)
            elif msg_type == 'warning':
                st.warning(msg_text)
        
        # Display selected player details (only for current week)
        if not is_historical and event.selection and event.selection.get("rows"):
            selected_row_idx = event.selection["rows"][0]
            
            # Get the selected row from the original results_df (before display formatting)
            selected_row = results_df.iloc[selected_row_idx]
            # Last 5 Games Performance Chart
            st.markdown("---")
            st.subheader("📊 Last 5 Games Performance")
            
            # Get last 5 games data with opponent details
            player_name = selected_row['Player']
            stat_type = selected_row['Stat Type']
            line = selected_row['Line']
            
            # OPTIMIZATION: Cache the player history lookup
            @st.cache_data(ttl=300)  # Cache for 5 minutes
            def get_cached_player_history(player_name, stat_type, _data_processor):
                return _data_processor.get_player_last_n_games_detailed(player_name, stat_type, n=5)
            
            game_details = get_cached_player_history(player_name, stat_type, data_processor)
            
            if game_details and len(game_details) > 0:
                # Extract values and create labels with opponents and defensive ranks
                game_values = [game['value'] for game in game_details]
                game_labels = []
                
                for game in game_details:
                    opponent = game['opponent']
                    is_home = game['is_home']
                    def_rank = game['defensive_rank']
                    game_date = game.get('game_date', '')
                    
                    # Format label: "@ NYG (10)<br>on 10/12" or "vs DAL (23)<br>on 09/04"
                    location = "vs" if is_home else "@"
                    rank_str = f"({def_rank})" if def_rank > 0 else ""
                    
                    # Build label with line break for date
                    if game_date:
                        label = f"{location} {opponent} {rank_str}<br>on {game_date}"
                    else:
                        label = f"{location} {opponent} {rank_str}"
                    
                    game_labels.append(label.strip())
                
                # Determine bar colors based on whether they hit the line
                bar_colors = ['#2ecc71' if val > line else '#e74c3c' for val in game_values]
                
                fig = go.Figure()
                
                # Add bars for game values
                fig.add_trace(go.Bar(
                    x=game_labels,
                    y=game_values,
                    marker=dict(color=bar_colors),
                    text=[f"{val:.1f}" for val in game_values],
                    textposition='outside'
                ))
                
                # Add horizontal line for the betting line
                fig.add_hline(
                    y=line, 
                    line_dash="dash", 
                    line_color="#3498db",
                    annotation_text=f"Line: {line}",
                    annotation_position="right"
                )
                
                # Calculate Y-axis range with padding
                max_value = max(game_values) if game_values else 0
                min_value = min(game_values) if game_values else 0
                y_range = max_value - min_value
                padding = max(y_range * 0.2, 20)  # 20% padding or minimum 20 units
                
                y_max = max_value + padding
                y_min = max(0, min_value - padding)  # Don't go below 0 for stats
                
                # Update layout
                fig.update_layout(
                    title=f"{player_name} - {stat_type} (Last {len(game_values)} Games)",
                    xaxis_title="",  # Removed - now obvious from labels
                    yaxis_title=stat_type,
                    showlegend=False,
                    height=400,
                    hovermode='x unified',
                    yaxis=dict(range=[y_min, y_max])
                )
                
                # Add hover template
                fig.update_traces(
                    hovertemplate='<b>%{x}</b><br>' + 
                                  f'{stat_type}: ' + '%{y:.1f}<br>' +
                                  '<extra></extra>'
                )
                
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{player_name}_{stat_type}")
                
                # Add context info
                over_count = sum(1 for val in game_values if val > line)
                st.caption(f"🟢 Hit Over: {over_count}/{len(game_values)} games • 🔴 Hit Under: {len(game_values) - over_count}/{len(game_values)} games • Defensive ranks in parentheses • Dates shown as MM/DD")
            else:
                st.info(f"No game history available for {player_name} - {stat_type}")
            
            # Show all row data in an expander for debugging/detailed view
            with st.expander("🔍 View All Row Data"):
                st.json(selected_row.to_dict())
        
        # OPTIMIZATION: Cache strategies to avoid recalculating on every interaction
        @st.cache_data(ttl=300)  # Cache for 5 minutes
        def get_cached_strategies(_results_df, _filter_props_by_strategy, _data_processor, _is_historical):
            # This will be handled by the display_all_strategies function
            return _results_df, _is_historical
        
        # Display all v1 and v2 strategies using centralized configurations
        cached_results_df, cached_is_historical = get_cached_strategies(results_df, filter_props_by_strategy, data_processor, is_historical)
        display_all_strategies(cached_results_df, filter_props_by_strategy, data_processor, cached_is_historical)

        # Time Window Sections
        st.markdown("---")
        st.subheader("Plum Props by Game Time")
        st.caption("Props organized by when games are played (TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night)")
        
        # OPTIMIZATION: Cache the time window data to avoid recalculating on every interaction
        @st.cache_data(ttl=600)  # Cache for 10 minutes
        def get_cached_time_window_data(_data_processor, _scorer, _odds_api, _alt_line_manager, _is_historical):
            if _is_historical:
                return None
            
            try:
                current_week = get_current_week_from_schedule()
                
                # Load ALL props for the current week from database
                from database.database_manager import DatabaseManager
                db_manager = DatabaseManager()
                all_week_props_df = db_manager.get_props_as_dataframe(week=current_week, upcoming_only=False)
                
                if not all_week_props_df.empty:
                    # Update team assignments
                    all_week_props_df = _odds_api.update_team_assignments(all_week_props_df, _data_processor)
                    
                    # Process and score ALL week props through the same pipeline
                    all_week_stat_types = all_week_props_df['Stat Type'].unique()
                    
                    all_week_all_props = process_props_and_score(
                        all_week_props_df, all_week_stat_types, _scorer, _data_processor, 
                        _alt_line_manager, True, None  # fallback_used=True, no progress bar
                    )
                    
                    if all_week_all_props:
                        # Convert to DataFrame and add time window classification
                        all_week_props_df = pd.DataFrame(all_week_all_props)
                        all_week_props_df['time_window'] = all_week_props_df['Commence Time'].apply(classify_game_time_window)
                        return all_week_props_df
                        
            except Exception as e:
                # Silently fail - historical data is optional
                pass
            
            return None
        
        with st.spinner("Loading props by game time..."):
            # Get cached time window data
            all_week_props_df = get_cached_time_window_data(data_processor, scorer, odds_api, alt_line_manager, is_historical)
            
            # Add time window classification to results_df if not already present
            if 'time_window' not in results_df.columns:
                results_df['time_window'] = results_df['Commence Time'].apply(classify_game_time_window)
            
            # Time windows to display
            time_window_configs = [
                ('TNF', 'Thursday Night Football', '🏈'),
                ('SunAM', 'Sunday 1:00 PM ET', '🌅'),
                ('SunPM', 'Sunday 4:00 PM ET', '☀️'),
                ('SNF', 'Sunday Night Football', '🌙'),
                ('MNF', 'Monday Night Football', '⭐')
            ]
            
            for window_key, window_name, window_emoji in time_window_configs:
                # Filter props for this time window from current data
                window_df = results_df[results_df['time_window'] == window_key]
                
                # If we have all week data, merge it for this time window to show past games
                if all_week_props_df is not None and not all_week_props_df.empty:
                    all_week_window_df = all_week_props_df[all_week_props_df['time_window'] == window_key]
                    
                    if not all_week_window_df.empty:
                        # Combine current and all week data for this time window
                        window_df = pd.concat([window_df, all_week_window_df], ignore_index=True)
                        # Remove duplicates based on player, stat type, and line
                        window_df = window_df.drop_duplicates(subset=['Player', 'Stat Type', 'Line'], keep='first')
                
                if not window_df.empty:
                    with st.expander(f"{window_emoji} {window_name} ({len(window_df)} props)", expanded=False):
                        st.markdown(f"**{window_name}**")
                        display_time_window_strategies(window_df, filter_props_by_strategy, data_processor, is_historical)

        # # ROI Performance Table (only for current week)
        # if not is_historical:
        #     st.subheader("Plum Props Performance (ROI)")
            
        #     # Cache ROI data to avoid recalculating when switching between weeks
        #     current_week = get_current_week_from_schedule()
            
        #     # Check if we have cached ROI data for this week
        #     if ('roi_data_cache' in st.session_state and 
        #         'roi_cache_week' in st.session_state and 
        #         st.session_state.roi_cache_week == current_week):
        #         # Use cached data
        #         roi_data = st.session_state.roi_data_cache
        #     else:
        #         # Calculate fresh ROI data
        #         with st.spinner("Calculating historical ROI for strategies..."):
        #             roi_data = calculate_all_strategies_roi()
                
        #         # Cache the results
        #         st.session_state.roi_data_cache = roi_data
        #         st.session_state.roi_cache_week = current_week
            
            
        # if roi_data:
        #     try:
        #         # Calculate the week range for display
        #         current_week = get_current_week_from_schedule()
        #         historical_weeks = list(range(4, current_week))
        #         if len(historical_weeks) == 1:
        #             week_range_str = f"Week {historical_weeks[0]}"
        #         elif len(historical_weeks) == 2:
        #             week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
        #         else:
        #             week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    
        #         # Create ROI table with Version+TimeWindow as rows and strategies as columns
        #         def format_roi(roi):
        #             try:
        #                 if roi > 0:
        #                     return f"+{roi:.2f}u"
        #                 elif roi < 0:
        #                     return f"{roi:.2f}u"
        #                 else:
        #                     return "0.00u"
        #             except:
        #                 return "N/A"
                    
        #         # Time windows to display
        #         time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
                    
        #         # Build table data with rows for each version+time window combination
        #         roi_table_data = []
                    
        #         for version in ['v1', 'v2']:
        #             for window in time_windows:
        #                 # Extract ROI values for this version and time window
        #                 optimal_key = f'{version}_Optimal'
        #                 greasy_key = f'{version}_Greasy'
        #                 degen_key = f'{version}_Degen'
                                
        #                 optimal_roi = roi_data.get(optimal_key, {}).get(window, {}).get('roi', 0) or 0
        #                 greasy_roi = roi_data.get(greasy_key, {}).get(window, {}).get('roi', 0) or 0
        #                 degen_roi = roi_data.get(degen_key, {}).get(window, {}).get('roi', 0) or 0
                                
        #                 roi_table_data.append({
        #                     'Strategy': f'{version}_{window}',
        #                     'Optimal': format_roi(optimal_roi),
        #                     'Greasy': format_roi(greasy_roi),
        #                     'Degen': format_roi(degen_roi),
        #                     'Optimal_numeric': optimal_roi,
        #                     'Greasy_numeric': greasy_roi,
        #                     'Degen_numeric': degen_roi
        #                 })
                    
        #         roi_df = pd.DataFrame(roi_table_data)
                    
        #         # Style the columns directly based on numeric values
        #         def color_roi(val, numeric_val):
        #             """Apply color based on numeric value"""
        #             if val == '-' or val == 'N/A':
        #                 return ''  # No styling for placeholder
        #             if numeric_val > 0:
        #                 return 'background-color: #d4edda; color: #155724'  # Green
        #             elif numeric_val < 0:
        #                 return 'background-color: #f8d7da; color: #721c24'  # Red
        #             return ''
                        
        #         # Create display DataFrame (without numeric columns)
        #         display_roi_df = roi_df[['Strategy', 'Optimal', 'Greasy', 'Degen']].copy()
                        
        #         # Apply styling using .applymap on each column with its numeric counterpart
        #         styled_roi_df = display_roi_df.style.apply(
        #             lambda x: [color_roi(x['Optimal'], roi_df.loc[x.name, 'Optimal_numeric']) if col == 'Optimal'
        #                        else color_roi(x['Greasy'], roi_df.loc[x.name, 'Greasy_numeric']) if col == 'Greasy'
        #                        else color_roi(x['Degen'], roi_df.loc[x.name, 'Degen_numeric']) if col == 'Degen'
        #                        else '' for col in x.index],
        #             axis=1
        #         )
                    
        #         st.caption(f"ROI calculated from {week_range_str} (1 unit parlay bet per time window per strategy)")
        #         st.dataframe(
        #             styled_roi_df,
        #             use_container_width=False,
        #             hide_index=True
        #         )
        #         st.caption("Note: Each strategy is evaluated separately for each time window (TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night). v1 strategies pick top 5 props. v2 Optimal (4 props, score 75+), v2 Greasy (6 props, score 65-80), v2 Degen (3 props, score 70-100, wide odds). All strategies parlay props - all must hit to win. ROI shows total return across all historical weeks.")
        #     except Exception as e:
        #         st.error(f"Error displaying ROI table: {e}")
        #         st.info("ℹ️ ROI data could not be displayed. Please check console for details.")
        # else:
        #     st.info("ℹ️ Not enough historical data to calculate ROI (requires weeks 4+)")
                
        #     # High Score Straight Bets ROI Section (Score > 80 & Streak >= 3)
        #     st.markdown("---")
        #     st.subheader("High Score Props ROI (Score > 80 & Streak ≥ 3 - Straight Bets)")
            
        #     # Cache high score ROI data
        #     if ('high_score_roi_cache' in st.session_state and 
        #         'high_score_roi_cache_week' in st.session_state and 
        #         st.session_state.high_score_roi_cache_week == current_week):
        #         # Use cached data
        #         high_score_roi = st.session_state.high_score_roi_cache
        #     else:
        #         # Calculate fresh high score ROI data
        #         with st.spinner("Calculating ROI for high-scoring props (Score > 80)..."):
        #             high_score_roi = calculate_high_score_straight_bets_roi()
                
        #         # Cache the results
        #         st.session_state.high_score_roi_cache = high_score_roi
        #         st.session_state.high_score_roi_cache_week = current_week
            
        #     if high_score_roi:
        #         try:
        #             # Calculate the week range for display
        #             current_week = get_current_week_from_schedule()
        #             historical_weeks = list(range(4, current_week))
        #             if len(historical_weeks) == 1:
        #                 week_range_str = f"Week {historical_weeks[0]}"
        #             elif len(historical_weeks) == 2:
        #                 week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
        #             else:
        #                 week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    
        #             # Format ROI function
        #             def format_roi(roi):
        #                 try:
        #                     if roi > 0:
        #                         return f"+{roi:.2f}u"
        #                     elif roi < 0:
        #                         return f"{roi:.2f}u"
        #                     else:
        #                         return "0.00u"
        #                 except:
        #                     return "N/A"
                    
        #             def format_win_rate(wins, losses):
        #                 total = wins + losses
        #                 if total == 0:
        #                     return "0.0%"
        #                 return f"{(wins / total * 100):.1f}%"
                    
        #             # Time windows to display
        #             time_windows_display = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF', 'All']
                    
        #             # Build table data
        #             high_score_table_data = []
                    
        #             for window in time_windows_display:
        #                 window_data = high_score_roi.get(window, {})
        #                 roi_value = window_data.get('roi', 0) or 0
        #                 total_bets = window_data.get('total_bets', 0)
        #                 wins = window_data.get('wins', 0)
        #                 losses = window_data.get('losses', 0)
                        
        #                 high_score_table_data.append({
        #                     'Time Window': window,
        #                     'Total Bets': total_bets,
        #                     'Wins': wins,
        #                     'Losses': losses,
        #                     'Win Rate': format_win_rate(wins, losses),
        #                     'ROI': format_roi(roi_value),
        #                     'ROI_numeric': roi_value
        #                 })
                    
        #             high_score_df = pd.DataFrame(high_score_table_data)
                    
        #             # Style the ROI column
        #             def color_roi(val, numeric_val):
        #                 """Apply color based on numeric value"""
        #                 if val == '-' or val == 'N/A':
        #                     return ''  # No styling for placeholder
        #                 if numeric_val > 0:
        #                     return 'background-color: #d4edda; color: #155724'  # Green
        #                 elif numeric_val < 0:
        #                     return 'background-color: #f8d7da; color: #721c24'  # Red
        #                 return ''
                    
        #             # Create display DataFrame (without numeric column)
        #             display_high_score_df = high_score_df[['Time Window', 'Total Bets', 'Wins', 'Losses', 'Win Rate', 'ROI']].copy()
                    
        #             # Apply styling
        #             styled_high_score_df = display_high_score_df.style.apply(
        #                 lambda x: [color_roi(x['ROI'], high_score_df.loc[x.name, 'ROI_numeric']) if col == 'ROI'
        #                            else '' for col in x.index],
        #                 axis=1
        #             )
                    
        #             st.caption(f"ROI calculated from {week_range_str} (1 unit straight bet per prop with Score > 80 & Streak ≥ 3)")
        #             st.dataframe(
        #                 styled_high_score_df,
        #                 use_container_width=False,
        #                 hide_index=True
        #             )
        #             st.caption("Note: This table shows ROI for ALL props with Score > 80 AND Streak ≥ 3, regardless of whether they were included in Optimal, Greasy, or Degen parlays. Each bet is treated as an independent straight bet (not parlayed). Only the highest-scoring prop per player/stat type is counted. TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night, All=combined across all time windows.")
        #         except Exception as e:
        #             st.error(f"Error displaying high score ROI table: {e}")
        #             st.info("ℹ️ High score ROI data could not be displayed. Please check console for details.")
        #     else:
        #         st.info("ℹ️ Not enough historical data to calculate high score ROI (requires weeks 4+)")
        
        st.markdown("---")
        # Column Explanations Section
        with st.expander("📖 Column Explanations", expanded=False):
            st.markdown("""
            ### What Each Column Means
            
            **Player** - The NFL player's name for this prop bet
            
            **Opp. Team** - The defense the player is facing this week
            - Format: "vs TEAM" (home game) or "@ TEAM" (away game)
            
            **Opp. Pos. Rank** - Position-specific defensive ranking against this stat type (1-32)
            - Lower rank = tougher defense (e.g., rank 1 is hardest to score against)
            - Higher rank = easier defense (e.g., rank 32 is easiest to score against)
            - 🔴 Red highlight (≤10): Favorable matchup - defense is weak against this stat
            - 🟢 Green highlight (≥21): Difficult matchup - defense is strong against this stat
            
            **Score** - Overall prop quality score (0-100)
            - Combines matchup quality, player history, consistency, and betting value
            - 🟢 Green (70+): High quality prop - strong recommendation
            - 🟠 Orange (50-69): Medium quality prop - decent option
            - 🔴 Red (<50): Low quality prop - proceed with caution
            - Higher scores indicate better overall betting opportunities
            
            **Line** - The betting line (over/under threshold)
            - This is the number you're betting the player will go over or under
            
            **Odds** - The American odds for the OVER bet
            - Negative odds (e.g., -110): You bet this amount to win $100
            - Positive odds (e.g., +120): You win this amount on a $100 bet
            
            **Streak** - Number of consecutive games the player has gone OVER this line
            - 🟢 Green highlight (≥3): Player is hot, hit the over 3+ games in a row
            - Example: "3" means the player went over this line in their last 3 straight games
            - **Note**: Streak resets to 0 if player misses 2 or more consecutive games (to avoid inflated streaks from injuries)
            
            **L5** - Over rate for the Last 5 games
            - Percentage of the last 5 games where the player exceeded this line
            - 🟢 Green highlight (>60%): Strong recent performance
            - Example: "80.0%" means player went over in 4 of last 5 games
            
            **Home** - Over rate in home games this season
            - Percentage of home games where the player exceeded this line
            - 🟢 Green highlight (>60%): Player performs well at home
            
            **Away** - Over rate in away games this season
            - Percentage of away games where the player exceeded this line
            - 🟢 Green highlight (>60%): Player performs well on the road
            
            **25/26** - Overall season over rate for 2025/2026
            - Percentage of ALL games this season where the player exceeded this line
            - 🟢 Green highlight (>60%): Consistently strong performance all season
            - This is the most comprehensive stat showing overall consistency
            
            ---
            
            ### How to Use This Information
            
            **Look for green highlights** - These indicate favorable conditions:
            - Green Opp. Pos. Rank = weak opposing defense
            - Green Streak = player is on a hot streak
            - Green percentages = player frequently hits this line
            
            **Multiple green indicators = stronger bet**
            - Best bets typically have 3+ green highlights
            
            **Compare Home vs Away**
            - If the game is at home, prioritize the "Home" percentage
            - If the game is away, prioritize the "Away" percentage
            
            **Alternate Lines**
            - Some players will have multiple rows with different lines and odds
            - These are alternate betting options for the same player
            - Compare the over rates to find the best value
            """)
        
        
    
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.stop()

if __name__ == "__main__":
    main()
