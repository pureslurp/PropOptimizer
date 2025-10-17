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
from utils import clean_player_name, format_odds, format_line
from config import ODDS_API_KEY, STAT_TYPES, CONFIDENCE_LEVELS, DEFAULT_MIN_SCORE, PREFERRED_BOOKMAKER
from utils import get_current_week_from_schedule, get_available_weeks_with_data
from prop_strategies import (
    STRATEGIES, 
    get_strategies_for_roi, 
    display_all_strategies,
    display_time_window_strategies
)
import warnings

# Set page config
st.set_page_config(
    page_title="NFL Player Prop Optimizer",
    page_icon="🏈",
    layout="wide"
)

# Parse command-line arguments for CSV mode
USE_CSV_MODE = '--use-csv' in sys.argv or '--csv' in sys.argv


# Removed - now using get_available_weeks_with_data() from week_utils


def load_props_from_csv(week_num):
    """
    Load props data from CSV file for a specific week
    Returns DataFrame in the same format as API props_df
    """
    props_file = f"2025/WEEK{week_num}/props.csv"
    
    if not os.path.exists(props_file):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(props_file)
        
        # Convert CSV format to match API props format
        # CSV has: week,saved_date,Player,Team,Opp. Team,Stat Type,Line,Odds,Bookmaker,Commence Time,is_alternate,Market,Home Team,Away Team
        # We need the same structure as parse_player_props returns
        
        # Rename/select columns to match expected format
        if not df.empty:
            # Handle is_alternate column - CSV may have empty strings
            if 'is_alternate' in df.columns:
                df['is_alternate'] = df['is_alternate'].fillna(False)
                df['is_alternate'] = df['is_alternate'].apply(lambda x: x == 'True' or x == True)
            else:
                df['is_alternate'] = False
            
            # Ensure all required columns exist
            required_cols = ['Player', 'Team', 'Opp. Team', 'Stat Type', 'Line', 'Odds', 
                           'Bookmaker', 'Home Team', 'Away Team', 'Commence Time']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ''
            
            # Add Opp. Team Full if not present (for lookups)
            if 'Opp. Team Full' not in df.columns:
                # Extract full team name from "vs TEAM" or "@ TEAM" format
                def extract_full_team(opposing_str, home_team, away_team, player_team):
                    if pd.isna(opposing_str) or opposing_str == '':
                        return ''
                    # If format is "vs X" player is home, opponent is away
                    # If format is "@ X" player is away, opponent is home  
                    if 'vs' in str(opposing_str):
                        return away_team if pd.notna(away_team) else ''
                    elif '@' in str(opposing_str):
                        return home_team if pd.notna(home_team) else ''
                    return ''
                
                df['Opp. Team Full'] = df.apply(
                    lambda row: extract_full_team(
                        row.get('Opp. Team', ''),
                        row.get('Home Team', ''),
                        row.get('Away Team', ''),
                        row.get('Team', '')
                    ), axis=1
                )
        
        return df
        
    except Exception as e:
        print(f"Error loading props from CSV: {e}")
        return pd.DataFrame()


def load_historical_props_for_week(week_num):
    """Load historical props data for a specific week (legacy function)"""
    return load_props_from_csv(week_num)


def load_historical_props_from_game_data(week_num):
    """
    Load historical props from game_data folder JSON files
    Returns DataFrame in the same format as API props_df
    """
    game_data_folder = f"2025/WEEK{week_num}/game_data"
    
    if not os.path.exists(game_data_folder):
        return pd.DataFrame()
    
    # Market key mapping to stat types
    market_to_stat_type = {
        'player_pass_yds_alternate': 'Passing Yards',
        'player_rush_yds_alternate': 'Rushing Yards',
        'player_reception_yds_alternate': 'Receiving Yards',
        'player_receptions_alternate': 'Receptions',
        'player_pass_tds_alternate': 'Passing TDs',
        'player_rush_tds_alternate': 'Rushing TDs',
        'player_reception_tds_alternate': 'Receiving TDs'
    }
    
    all_props = []
    
    # Load all JSON files from the game_data folder
    json_files = glob.glob(os.path.join(game_data_folder, "*_historical_odds.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            event_data = data.get('data', {})
            home_team = event_data.get('home_team', '')
            away_team = event_data.get('away_team', '')
            commence_time = event_data.get('commence_time', '')
            
            # Process each bookmaker
            for bookmaker in event_data.get('bookmakers', []):
                bookmaker_key = bookmaker.get('key', '')
                
                # Process each market
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key', '')
                    stat_type = market_to_stat_type.get(market_key)
                    
                    if not stat_type:
                        continue
                    
                    # Process each outcome (player prop)
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') != 'Over':
                            continue
                        
                        player_name = outcome.get('description', '')
                        line = outcome.get('point', 0)
                        odds = outcome.get('price', 0)
                        
                        # Determine player's team and opposing team
                        # We don't have this info directly, so we'll need to look it up
                        # For now, we'll leave it blank and let the team assignment logic handle it
                        
                        prop_row = {
                            'Player': player_name,
                            'Team': '',  # Will be filled in later
                            'Opp. Team': '',
                            'Opp. Team Full': '',
                            'Stat Type': stat_type,
                            'Line': line,
                            'Odds': odds,
                            'Bookmaker': bookmaker_key,
                            'Home Team': home_team,
                            'Away Team': away_team,
                            'Commence Time': commence_time,
                            'is_alternate': True
                        }
                        
                        all_props.append(prop_row)
        
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue
    
    if not all_props:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_props)
    
    # Filter odds between -450 and +200 (same as API mode)
    df = df[(df['Odds'] >= -450) & (df['Odds'] <= 200)]
    
    return df


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
        # Parse the UTC time
        utc_time = parser.parse(commence_time_str)
        
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
        print(f"Error parsing commence time '{commence_time_str}': {e}")
        return 'Other'


def get_available_historical_weeks():
    """
    Get list of weeks that have historical game_data available
    Returns list of week numbers
    """
    available_weeks = []
    
    for week in range(1, 19):  # NFL has 18 weeks
        game_data_folder = f"2025/WEEK{week}/game_data"
        if os.path.exists(game_data_folder):
            json_files = glob.glob(os.path.join(game_data_folder, "*_historical_odds.json"))
            if json_files:
                available_weeks.append(week)
    
    return available_weeks


def fetch_props_with_fallback(odds_api, progress_bar):
    """
    Fetch props from API with automatic CSV fallback if API fails.
    Can be forced to use CSV mode with --use-csv or --csv flag.
    
    Returns:
        tuple: (props_df, odds_data, fallback_used)
    """
    api_failed = False
    fallback_used = False
    
    # Check if CSV mode is forced via command line
    if USE_CSV_MODE:
        api_failed = True
        st.info("🔧 CSV Mode: Using saved props (--use-csv flag detected)")
    else:
        try:
            odds_data = odds_api.get_player_props()
            progress_bar.progress(10, text="Processing player props data...")
            
            if not odds_data:
                api_failed = True
        except Exception as api_error:
            api_failed = True
            st.warning(f"⚠️ API Error: {str(api_error)}")
    
    # Fallback to CSV if API failed or CSV mode is forced
    if api_failed:
        current_week = get_current_week_from_schedule()
        if not USE_CSV_MODE:
            st.info(f"📁 API limit reached or unavailable. Loading from saved Week {current_week} props...")
        progress_bar.progress(10, text=f"Loading props from Week {current_week} CSV...")
        
        props_df = load_props_from_csv(current_week)
        
        if props_df.empty:
            st.error(f"❌ No saved props found for Week {current_week}. Please try again when API quota resets.")
            st.stop()
        
        fallback_used = True
        odds_data = []  # Empty for compatibility
        progress_bar.progress(20, text="Processing saved props data...")
    else:
        # OPTIMIZED: Parse returns empty DataFrame
        # Actual props come from alternate lines (populated later)
        props_df = odds_api.parse_player_props(odds_data)
        progress_bar.progress(20, text="Events loaded, will fetch alternate lines...")
        
        # Note: props_df is intentionally empty here
        # It will be populated from alternate lines in the main flow
    
    return props_df, odds_data, fallback_used


def process_props_and_score(props_df, stat_types_in_data, scorer, data_processor, 
                            alt_line_manager, fallback_used, progress_bar):
    """
    Process props and calculate scores (handles both API and CSV data).
    
    Returns:
        list: All scored props including alternates
    """
    all_props = []
    
    if fallback_used:
        # CSV fallback: process all rows (already includes alternates)
        for idx, stat_type in enumerate(stat_types_in_data):
            stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
            
            if stat_filtered_df.empty:
                continue
            
            progress_text = f"Processing {stat_type}... ({idx+1}/{len(stat_types_in_data)})"
            progress_val = 50 + int((idx + 1) / len(stat_types_in_data) * 40)
            progress_bar.progress(progress_val, text=progress_text)
            
            # Process all rows from CSV (both main and alternate lines)
            for _, row in stat_filtered_df.iterrows():
                score_data = scorer.calculate_comprehensive_score(
                    row['Player'],
                    row.get('Opp. Team Full', row['Opp. Team']),
                    row['Stat Type'],
                    row['Line'],
                    row.get('Odds', 0),
                    home_team=row.get('Home Team'),
                    away_team=row.get('Away Team')
                )
                
                # score_data already includes l5_over_rate, home_over_rate, away_over_rate, and streak
                scored_prop = {
                    **row.to_dict(),
                    **score_data,
                    'is_alternate': row.get('is_alternate', False)
                }
                all_props.append(scored_prop)
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
                        away_team=row.get('Away Team')
                    )
                    
                    scored_prop = {
                        **row.to_dict(),
                        **score_data,
                        'is_alternate': row.get('is_alternate', True)
                    }
                    all_props.append(scored_prop)
    
    return all_props


def load_box_score_for_week(week_num):
    """Load box score data for a specific week"""
    box_score_path = f"2025/WEEK{week_num}/box_score_debug.csv"
    
    if not os.path.exists(box_score_path):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(box_score_path)
        # Clean player names to match the format used in props
        df['Name_clean'] = df['Name'].apply(clean_player_name)
        return df
    except Exception as e:
        print(f"Error loading box score: {e}")
        return pd.DataFrame()


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
    # Load historical data and box scores for the week
    props_df = load_historical_props_from_game_data(week_num)
    
    if props_df.empty:
        return None
    
    # Add time window classification to each prop
    props_df['time_window'] = props_df['Commence Time'].apply(classify_game_time_window)
    
    # Create a data processor limited to data before this week
    data_processor_historical = EnhancedFootballDataProcessor(max_week=week_num)
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
    
    # Load box score for actual results
    box_score_df = load_box_score_for_week(week_num)
    
    if box_score_df.empty:
        return None
    
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
            # Load historical data and box scores for the week
            props_df = load_historical_props_from_game_data(week)
            
            if props_df.empty:
                continue
            
            # Add time window classification to each prop
            props_df['time_window'] = props_df['Commence Time'].apply(classify_game_time_window)
            
            # Create a data processor limited to data before this week
            data_processor_historical = EnhancedFootballDataProcessor(max_week=week)
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
            
            # Load box score for actual results
            box_score_df = load_box_score_for_week(week)
            
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
    # Week 4 is the first valid week (needs 3 weeks of history for meaningful props)
    historical_weeks = list(range(4, current_week))
    
    if not historical_weeks:
        return None
    
    # Get centralized strategy definitions
    strategies = get_strategies_for_roi()
    
    # Time windows we're tracking
    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
    
    # Calculate ROI for each strategy, broken down by time window
    roi_data = {}
    
    for strategy_name, params in strategies.items():
        try:
            # Initialize ROI tracking by time window
            roi_by_window = {window: {'roi': 0.0, 'results': []} for window in time_windows}
            
            for week in historical_weeks:
                try:
                    week_roi_by_window = calculate_strategy_roi_for_week(
                        week, 
                        params['score_min'], 
                        params['score_max'],
                        odds_min=params.get('odds_min', -400),
                        odds_max=params.get('odds_max', -150),
                        streak_min=params.get('streak_min'),
                        max_players=params.get('max_players', 5),
                        position_filter=params.get('position_filter', False)
                    )
                    
                    if week_roi_by_window is not None:
                        # Aggregate ROI by time window
                        for window, window_data in week_roi_by_window.items():
                            roi_by_window[window]['roi'] += window_data['roi']
                            roi_by_window[window]['results'].extend(window_data['results'])
                            
                except Exception as e:
                    print(f"Warning: Error calculating ROI for {strategy_name} week {week}: {e}")
                    continue
            
            roi_data[strategy_name] = roi_by_window
            
        except Exception as e:
            print(f"Warning: Error calculating ROI for {strategy_name}: {e}")
            roi_data[strategy_name] = {window: {'roi': 0.0, 'results': []} for window in time_windows}
    
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
    current_week_temp = get_current_week_from_schedule()
    historical_weeks = get_available_historical_weeks()
    
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
    
    # Initialize components with max_week for historical filtering
    odds_api = OddsAPI(ODDS_API_KEY)
    # For historical weeks, set max_week to the selected week so stats only include games before it
    max_week_for_processor = selected_week if is_historical else None
    data_processor = EnhancedFootballDataProcessor(max_week=max_week_for_processor)
    scorer = AdvancedPropScorer(data_processor)
    
    # Store odds_api in session state for accessing usage info
    st.session_state.odds_api = odds_api
    
    # Clear cache if week changes
    if 'selected_week' not in st.session_state or st.session_state.selected_week != selected_week:
        old_week = st.session_state.get('selected_week')
        st.session_state.selected_week = selected_week
        
        # If switching FROM current week TO historical week, preserve current week data
        if old_week == current_week_temp and is_historical:
            # Save current week data before clearing
            st.session_state.current_week_cache = {
                'alt_line_manager': st.session_state.get('alt_line_manager'),
                'all_scored_props': st.session_state.get('all_scored_props'),
                'props_df_cache': st.session_state.get('props_df_cache'),
                'odds_data_cache': st.session_state.get('odds_data_cache')
            }
            # Now clear the regular cache so historical data can be loaded fresh
            for key in ['alt_line_manager', 'all_scored_props', 'props_df_cache', 'odds_data_cache']:
                if key in st.session_state:
                    del st.session_state[key]
        
        # If switching TO current week FROM historical week, restore cached data
        elif selected_week == current_week_temp and 'current_week_cache' in st.session_state:
            # Restore current week data from cache
            cache = st.session_state.current_week_cache
            if cache.get('alt_line_manager') is not None:
                st.session_state.alt_line_manager = cache['alt_line_manager']
            if cache.get('all_scored_props') is not None:
                st.session_state.all_scored_props = cache['all_scored_props']
            if cache.get('props_df_cache') is not None:
                st.session_state.props_df_cache = cache['props_df_cache']
            if cache.get('odds_data_cache') is not None:
                st.session_state.odds_data_cache = cache['odds_data_cache']
        else:
            # Clear all cached data when switching between different weeks
            for key in ['alt_line_manager', 'all_scored_props', 'props_df_cache', 'odds_data_cache']:
                if key in st.session_state:
                    del st.session_state[key]
    
    # Sidebar configuration with control buttons
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown("---")
        
        # Control buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 Refresh", type="primary", use_container_width=True):
                # Clear all cached data on refresh
                if 'alt_line_manager' in st.session_state:
                    del st.session_state.alt_line_manager
                if 'all_scored_props' in st.session_state:
                    del st.session_state.all_scored_props
                if 'props_df_cache' in st.session_state:
                    del st.session_state.props_df_cache
                if 'odds_data_cache' in st.session_state:
                    del st.session_state.odds_data_cache
                # Clear filter selections
                if 'selected_stat_types' in st.session_state:
                    del st.session_state.selected_stat_types
                if 'selected_games' in st.session_state:
                    del st.session_state.selected_games
                st.rerun()
        
        with col2:
            export_button = st.button("Export to CSV", type="secondary", use_container_width=True)
        
        st.markdown("---")
    
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
            progress_bar = st.progress(0, text="Fetching player props data...")
            
            # Check if we're loading historical data
            if is_historical:
                progress_bar.progress(10, text=f"Loading Week {selected_week} historical data...")
                props_df = load_historical_props_from_game_data(selected_week)
                
                if props_df.empty:
                    st.error(f"❌ No historical data found for Week {selected_week}. Please check the game_data folder.")
                    st.stop()
                
                # Update team assignments using data processor
                props_df = odds_api.update_team_assignments(props_df, data_processor)
                
                fallback_used = True  # Treat as fallback mode
                odds_data = []  # Empty for compatibility
                progress_bar.progress(30, text=f"Loaded {len(props_df)} props from Week {selected_week} historical data...")
            else:
                # Fetch props with automatic CSV fallback
                props_df, odds_data, fallback_used = fetch_props_with_fallback(odds_api, progress_bar)
            
            # Cache the raw data
            st.session_state.props_df_cache = props_df
            st.session_state.odds_data_cache = odds_data
            
            # Initialize alternate line manager
            alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
            st.session_state.alt_line_manager = alt_line_manager
            
            # Handle alternate lines based on data source
            if is_historical:
                # Historical data already loaded, skip alternate line fetching
                progress_bar.progress(40, text="Using historical alternate lines...")
            elif fallback_used:
                # CSV already has alternate lines, no need to fetch
                progress_bar.progress(30, text="Using saved alternate lines from CSV...")
            else:
                # OPTIMIZED: Fetch ONLY alternate lines (no main props call)
                # This saves ~5 API calls per launch!
                progress_bar.progress(30, text="Fetching alternate lines...")
                all_alternate_lines = alt_line_manager.fetch_all_alternate_lines_optimized()
                alt_line_manager.alternate_lines = all_alternate_lines
                
                # Convert alternate lines to props_df format
                progress_bar.progress(40, text="Converting alternate lines to props...")
                props_df = alt_line_manager.convert_alternates_to_props_df(odds_data)
                
                # Update team assignments
                if not props_df.empty:
                    props_df = odds_api.update_team_assignments(props_df, data_processor)
                
                # Update cache with new props_df
                st.session_state.props_df_cache = props_df
            
            # Process and score all props
            progress_bar.progress(50, text="Calculating scores for all props...")
            stat_types_in_data = props_df['Stat Type'].unique() if not props_df.empty else []
            all_props = process_props_and_score(
                props_df, stat_types_in_data, scorer, data_processor, 
                alt_line_manager, fallback_used, progress_bar
            )
            
            # If viewing historical data, add actual results from box score
            if is_historical:
                progress_bar.progress(90, text="Loading actual results from box score...")
                box_score_df = load_box_score_for_week(selected_week)
                
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
            elif fallback_used:
                current_week = get_current_week_from_schedule()
                info_messages.append(('warning', f"📁 Loaded {len(all_props)} props from saved Week {current_week} CSV (API unavailable)"))
            else:
                info_messages.append(('success', f"✅ Loaded {len(all_props)} total props from {len(odds_data)} games"))
        
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
                
                # Create DataFrame and CSV
                export_df = pd.DataFrame(all_export_data)
                export_df = export_df.sort_values(['Stat Type', 'Player', 'Is Alternate'])
                
                csv = export_df.to_csv(index=False)
                
                # Show download button
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"nfl_props_export_{timestamp}.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                stat_types_count = len(export_df['Stat Type'].unique())
                st.success(f"✅ Export ready! {len(export_df)} total props (including alternates) across {stat_types_count} stat types")
        
        # Prepare results dataframe
        results_df = pd.DataFrame(all_props)
        
        # Get available stat types
        available_stat_types = sorted(results_df['Stat Type'].unique())
        
        # Get available matchups
        results_df['Matchup'] = results_df.apply(get_matchup_string, axis=1)
        available_matchups = sorted([m for m in results_df['Matchup'].unique() if m is not None])
        
        # Initialize session state for checkbox selections if not exists
        if 'selected_stat_types' not in st.session_state:
            st.session_state.selected_stat_types = {stat: True for stat in available_stat_types}
        
        if 'selected_games' not in st.session_state:
            st.session_state.selected_games = {game: True for game in available_matchups}
        
        # Update session state with any new stat types or games
        for stat in available_stat_types:
            if stat not in st.session_state.selected_stat_types:
                st.session_state.selected_stat_types[stat] = True
        
        for game in available_matchups:
            if game not in st.session_state.selected_games:
                st.session_state.selected_games[game] = True
        
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
            
            game_details = data_processor.get_player_last_n_games_detailed(player_name, stat_type, n=5)
            
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
        
        # Display all v1 and v2 strategies using centralized configurations
        display_all_strategies(results_df, filter_props_by_strategy, data_processor, is_historical)

        # Time Window Sections
        st.markdown("---")
        st.subheader("Plum Props by Game Time")
        st.caption("Props organized by when games are played (TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night)")
        
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
            # Filter props for this time window
            window_df = results_df[results_df['time_window'] == window_key]
            
            if not window_df.empty:
                with st.expander(f"{window_emoji} {window_name} ({len(window_df)} props)", expanded=False):
                    st.markdown(f"**{window_name}**")
                    display_time_window_strategies(window_df, filter_props_by_strategy, data_processor, is_historical)

        # ROI Performance Table (only for current week)
        if not is_historical:
            st.subheader("Plum Props Performance (ROI)")
            
            # Cache ROI data to avoid recalculating when switching between weeks
            current_week = get_current_week_from_schedule()
            
            # Check if we have cached ROI data for this week
            if ('roi_data_cache' in st.session_state and 
                'roi_cache_week' in st.session_state and 
                st.session_state.roi_cache_week == current_week):
                # Use cached data
                roi_data = st.session_state.roi_data_cache
            else:
                # Calculate fresh ROI data
                with st.spinner("Calculating historical ROI for strategies..."):
                    roi_data = calculate_all_strategies_roi()
                
                # Cache the results
                st.session_state.roi_data_cache = roi_data
                st.session_state.roi_cache_week = current_week
            
            if roi_data:
                try:
                    # Calculate the week range for display
                    current_week = get_current_week_from_schedule()
                    historical_weeks = list(range(4, current_week))
                    if len(historical_weeks) == 1:
                        week_range_str = f"Week {historical_weeks[0]}"
                    elif len(historical_weeks) == 2:
                        week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    else:
                        week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    
                    # Create ROI table with Version+TimeWindow as rows and strategies as columns
                    def format_roi(roi):
                        try:
                            if roi > 0:
                                return f"+{roi:.2f}u"
                            elif roi < 0:
                                return f"{roi:.2f}u"
                            else:
                                return "0.00u"
                        except:
                            return "N/A"
                    
                    # Time windows to display
                    time_windows = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF']
                    
                    # Build table data with rows for each version+time window combination
                    roi_table_data = []
                    
                    for version in ['v1', 'v2']:
                        for window in time_windows:
                            # Extract ROI values for this version and time window
                            optimal_key = f'{version}_Optimal'
                            greasy_key = f'{version}_Greasy'
                            degen_key = f'{version}_Degen'
                            
                            optimal_roi = roi_data.get(optimal_key, {}).get(window, {}).get('roi', 0) or 0
                            greasy_roi = roi_data.get(greasy_key, {}).get(window, {}).get('roi', 0) or 0
                            degen_roi = roi_data.get(degen_key, {}).get(window, {}).get('roi', 0) or 0
                            
                            roi_table_data.append({
                                'Strategy': f'{version}_{window}',
                                'Optimal': format_roi(optimal_roi),
                                'Greasy': format_roi(greasy_roi),
                                'Degen': format_roi(degen_roi),
                                'Optimal_numeric': optimal_roi,
                                'Greasy_numeric': greasy_roi,
                                'Degen_numeric': degen_roi
                            })
                    
                    roi_df = pd.DataFrame(roi_table_data)
                    
                    # Style the columns directly based on numeric values
                    def color_roi(val, numeric_val):
                        """Apply color based on numeric value"""
                        if val == '-' or val == 'N/A':
                            return ''  # No styling for placeholder
                        if numeric_val > 0:
                            return 'background-color: #d4edda; color: #155724'  # Green
                        elif numeric_val < 0:
                            return 'background-color: #f8d7da; color: #721c24'  # Red
                        return ''
                    
                    # Create display DataFrame (without numeric columns)
                    display_roi_df = roi_df[['Strategy', 'Optimal', 'Greasy', 'Degen']].copy()
                    
                    # Apply styling using .applymap on each column with its numeric counterpart
                    styled_roi_df = display_roi_df.style.apply(
                        lambda x: [color_roi(x['Optimal'], roi_df.loc[x.name, 'Optimal_numeric']) if col == 'Optimal'
                                   else color_roi(x['Greasy'], roi_df.loc[x.name, 'Greasy_numeric']) if col == 'Greasy'
                                   else color_roi(x['Degen'], roi_df.loc[x.name, 'Degen_numeric']) if col == 'Degen'
                                   else '' for col in x.index],
                        axis=1
                    )
                
                    st.caption(f"ROI calculated from {week_range_str} (1 unit parlay bet per time window per strategy)")
                    st.dataframe(
                        styled_roi_df,
                        use_container_width=False,
                        hide_index=True
                    )
                    st.caption("Note: Each strategy is evaluated separately for each time window (TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night). v1 strategies pick top 5 props. v2 Optimal (4 props, score 75+), v2 Greasy (6 props, score 65-80), v2 Degen (3 props, score 70-100, wide odds). All strategies parlay props - all must hit to win. ROI shows total return across all historical weeks.")
                except Exception as e:
                    st.error(f"Error displaying ROI table: {e}")
                    st.info("ℹ️ ROI data could not be displayed. Please check console for details.")
            else:
                st.info("ℹ️ Not enough historical data to calculate ROI (requires weeks 4+)")
            
            # High Score Straight Bets ROI Section (Score > 80 & Streak >= 3)
            st.markdown("---")
            st.subheader("High Score Props ROI (Score > 80 & Streak ≥ 3 - Straight Bets)")
            
            # Cache high score ROI data
            if ('high_score_roi_cache' in st.session_state and 
                'high_score_roi_cache_week' in st.session_state and 
                st.session_state.high_score_roi_cache_week == current_week):
                # Use cached data
                high_score_roi = st.session_state.high_score_roi_cache
            else:
                # Calculate fresh high score ROI data
                with st.spinner("Calculating ROI for high-scoring props (Score > 80)..."):
                    high_score_roi = calculate_high_score_straight_bets_roi()
                
                # Cache the results
                st.session_state.high_score_roi_cache = high_score_roi
                st.session_state.high_score_roi_cache_week = current_week
            
            if high_score_roi:
                try:
                    # Calculate the week range for display
                    current_week = get_current_week_from_schedule()
                    historical_weeks = list(range(4, current_week))
                    if len(historical_weeks) == 1:
                        week_range_str = f"Week {historical_weeks[0]}"
                    elif len(historical_weeks) == 2:
                        week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    else:
                        week_range_str = f"Weeks {historical_weeks[0]}-{historical_weeks[-1]}"
                    
                    # Format ROI function
                    def format_roi(roi):
                        try:
                            if roi > 0:
                                return f"+{roi:.2f}u"
                            elif roi < 0:
                                return f"{roi:.2f}u"
                            else:
                                return "0.00u"
                        except:
                            return "N/A"
                    
                    def format_win_rate(wins, losses):
                        total = wins + losses
                        if total == 0:
                            return "0.0%"
                        return f"{(wins / total * 100):.1f}%"
                    
                    # Time windows to display
                    time_windows_display = ['TNF', 'SunAM', 'SunPM', 'SNF', 'MNF', 'All']
                    
                    # Build table data
                    high_score_table_data = []
                    
                    for window in time_windows_display:
                        window_data = high_score_roi.get(window, {})
                        roi_value = window_data.get('roi', 0) or 0
                        total_bets = window_data.get('total_bets', 0)
                        wins = window_data.get('wins', 0)
                        losses = window_data.get('losses', 0)
                        
                        high_score_table_data.append({
                            'Time Window': window,
                            'Total Bets': total_bets,
                            'Wins': wins,
                            'Losses': losses,
                            'Win Rate': format_win_rate(wins, losses),
                            'ROI': format_roi(roi_value),
                            'ROI_numeric': roi_value
                        })
                    
                    high_score_df = pd.DataFrame(high_score_table_data)
                    
                    # Style the ROI column
                    def color_roi(val, numeric_val):
                        """Apply color based on numeric value"""
                        if val == '-' or val == 'N/A':
                            return ''  # No styling for placeholder
                        if numeric_val > 0:
                            return 'background-color: #d4edda; color: #155724'  # Green
                        elif numeric_val < 0:
                            return 'background-color: #f8d7da; color: #721c24'  # Red
                        return ''
                    
                    # Create display DataFrame (without numeric column)
                    display_high_score_df = high_score_df[['Time Window', 'Total Bets', 'Wins', 'Losses', 'Win Rate', 'ROI']].copy()
                    
                    # Apply styling
                    styled_high_score_df = display_high_score_df.style.apply(
                        lambda x: [color_roi(x['ROI'], high_score_df.loc[x.name, 'ROI_numeric']) if col == 'ROI'
                                   else '' for col in x.index],
                        axis=1
                    )
                    
                    st.caption(f"ROI calculated from {week_range_str} (1 unit straight bet per prop with Score > 80 & Streak ≥ 3)")
                    st.dataframe(
                        styled_high_score_df,
                        use_container_width=False,
                        hide_index=True
                    )
                    st.caption("Note: This table shows ROI for ALL props with Score > 80 AND Streak ≥ 3, regardless of whether they were included in Optimal, Greasy, or Degen parlays. Each bet is treated as an independent straight bet (not parlayed). Only the highest-scoring prop per player/stat type is counted. TNF=Thursday Night, SunAM=1pm ET, SunPM=4pm ET, SNF=Sunday Night, MNF=Monday Night, All=combined across all time windows.")
                except Exception as e:
                    st.error(f"Error displaying high score ROI table: {e}")
                    st.info("ℹ️ High score ROI data could not be displayed. Please check console for details.")
            else:
                st.info("ℹ️ Not enough historical data to calculate high score ROI (requires weeks 4+)")
        
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
