"""
Strategy definitions and display functions for NFL player prop analysis.
Centralizes all strategy configurations to avoid duplication.
"""

import streamlit as st
import pandas as pd
from utils import format_odds

# Centralized strategy configurations
# These are used for both ROI calculation and display
STRATEGIES = {
    # V1 Strategies
    'v1_Optimal': {
        'name': 'Optimal',
        'emoji': '🎯',
        'version': 'v1',
        'score_min': 70, 
        'score_max': float('inf'),
        'odds_min': -400,
        'odds_max': -150,
        'max_players': 5,
        'streak_min': None,
        'position_filter': False
    },
    'v1_Greasy': {
        'name': 'Greasy',
        'emoji': '🧈',
        'version': 'v1',
        'score_min': 50, 
        'score_max': 70,
        'odds_min': -400,
        'odds_max': -150,
        'max_players': 5,
        'streak_min': None,
        'position_filter': False
    },
    'v1_Degen': {
        'name': 'Degen',
        'emoji': '🎲',
        'version': 'v1',
        'score_min': 0, 
        'score_max': 50,
        'odds_min': -400,
        'odds_max': -150,
        'max_players': 5,
        'streak_min': None,
        'position_filter': False
    },
    # V2 Strategies
    'v2_Optimal': {
        'name': 'Optimal v2',
        'emoji': '🎯',
        'version': 'v2',
        'score_min': 75,
        'score_max': float('inf'),
        'odds_min': -300,
        'odds_max': -150,
        'streak_min': 3,
        'max_players': 4,
        'position_filter': True
    },
    'v2_Greasy': {
        'name': 'Greasy v2',
        'emoji': '🧈',
        'version': 'v2',
        'score_min': 65,
        'score_max': 80,
        'odds_min': -300,
        'odds_max': -150,
        'streak_min': 2,
        'max_players': 6,
        'position_filter': True
    },
    'v2_Degen': {
        'name': 'Degen v2',
        'emoji': '🎲',
        'version': 'v2',
        'score_min': 70,
        'score_max': 100,
        'odds_min': 0,
        'odds_max': 200,
        'streak_min': None,
        'max_players': 3,
        'position_filter': False
    }
}


def get_strategies_for_roi():
    """
    Get strategy configurations formatted for ROI calculation.
    Returns dict with only the parameters needed for calculation.
    """
    roi_strategies = {}
    for key, config in STRATEGIES.items():
        roi_strategies[key] = {
            'score_min': config['score_min'],
            'score_max': config['score_max'],
            'odds_min': config['odds_min'],
            'odds_max': config['odds_max'],
            'streak_min': config.get('streak_min'),
            'max_players': config['max_players'],
            'position_filter': config.get('position_filter', False)
        }
    return roi_strategies


def display_prop_picks(df, filter_props_func, data_processor, is_historical, 
                       score_min, score_max, odds_min=-400, odds_max=-150, 
                       streak_min=None, max_players=5, position_filter=False):
    """
    Display props based on strategy criteria with parlay odds.
    
    Args:
        df: DataFrame of props to filter
        filter_props_func: Function to filter props by strategy
        data_processor: Data processor for player stats
        is_historical: Whether viewing historical week
        score_min: Minimum score threshold
        score_max: Maximum score threshold
        odds_min: Minimum odds (e.g., -400)
        odds_max: Maximum odds (e.g., -150)
        streak_min: Minimum streak value (optional)
        max_players: Maximum number of players to select
        position_filter: If True, apply position-appropriate filtering
    """
    try:
        # Use the reusable filter function
        top_props = filter_props_func(
            df, 
            data_processor=data_processor,
            score_min=score_min,
            score_max=score_max,
            odds_min=odds_min,
            odds_max=odds_max,
            streak_min=streak_min,
            max_players=max_players,
            position_filter=position_filter
        )
        
        if not top_props.empty:
            # Display each prop
            for idx, row in top_props.iterrows():
                player = row['Player']
                stat_type = row['Stat Type']
                line = row['Line']
                odds = row['Odds']
                score = row['total_score']
                
                # Build the display string
                prop_str = f"**{player}** - {stat_type} O{line} ({format_odds(odds)}) - Score: {score:.1f}"
                
                # Add actual result if historical
                if is_historical and 'actual_result' in row and pd.notna(row['actual_result']):
                    actual = row['actual_result']
                    if actual > line:
                        prop_str += f' ✅ ({actual:.1f})'
                    else:
                        prop_str += f' ❌ ({actual:.1f})'
                
                st.markdown(prop_str)
            
            # Calculate and display parlay odds
            parlay_decimal = 1.0
            all_props_hit = True
            
            for _, row in top_props.iterrows():
                odds = row['Odds']
                # Convert American odds to decimal
                if odds < 0:
                    decimal = 1 + (100 / abs(odds))
                else:
                    decimal = 1 + (odds / 100)
                parlay_decimal *= decimal
                
                # Check if prop hit (for historical weeks)
                if is_historical and 'actual_result' in row and pd.notna(row['actual_result']):
                    if row['actual_result'] <= row['Line']:
                        all_props_hit = False
            
            # Convert parlay decimal back to American odds
            if parlay_decimal >= 2.0:
                parlay_american = int((parlay_decimal - 1) * 100)
                parlay_odds_str = f"+{parlay_american}"
            else:
                parlay_american = int(-100 / (parlay_decimal - 1))
                parlay_odds_str = str(parlay_american)
            
            # Add parlay result indicator if historical
            parlay_result = ""
            if is_historical:
                if all_props_hit:
                    parlay_result = ' <span style="color: #28a745; font-weight: bold; font-size: 1.2em;">✓</span>'
                else:
                    parlay_result = ' <span style="color: #dc3545; font-weight: bold; font-size: 1.2em;">✗</span>'
            
            st.markdown(f"• **If Parlayed:** {parlay_odds_str} odds{parlay_result}", unsafe_allow_html=True)
        else:
            # Build informative message about why no props were found
            criteria_parts = []
            criteria_parts.append(f"Score {score_min}+")
            if score_max != float('inf'):
                criteria_parts.append(f"(max {score_max})")
            criteria_parts.append(f"Odds {format_odds(odds_min)} to {format_odds(odds_max)}")
            if streak_min is not None:
                criteria_parts.append(f"Streak {streak_min}+")
            if position_filter:
                criteria_parts.append("Position-appropriate only")
            
            criteria_str = " | ".join(criteria_parts)
            st.markdown(f"*No props meet the criteria: {criteria_str}*")
            st.caption("💡 Try adjusting filters or check back when more games are available")
    except Exception as e:
        st.error(f"Error displaying props: {e}")


def display_strategy_section(df, filter_props_func, data_processor, is_historical, 
                             strategy_key, expanded=False):
    """
    Display a single strategy section with expander.
    
    Args:
        df: DataFrame of props
        filter_props_func: Function to filter props
        data_processor: Data processor
        is_historical: Whether viewing historical week
        strategy_key: Key to look up strategy in STRATEGIES dict (e.g., 'v1_Optimal')
        expanded: Whether to expand the section by default
    """
    if strategy_key not in STRATEGIES:
        st.error(f"Unknown strategy: {strategy_key}")
        return
    
    config = STRATEGIES[strategy_key]
    
    with st.expander(f"{config['emoji']} {config['name']}", expanded=expanded):
        display_prop_picks(
            df,
            filter_props_func,
            data_processor,
            is_historical,
            score_min=config['score_min'],
            score_max=config['score_max'],
            odds_min=config['odds_min'],
            odds_max=config['odds_max'],
            streak_min=config.get('streak_min'),
            max_players=config['max_players'],
            position_filter=config.get('position_filter', False)
        )


def display_all_strategies(df, filter_props_func, data_processor, is_historical):
    """
    Display all v1 and v2 strategies in organized sections.
    
    Args:
        df: DataFrame of props
        filter_props_func: Function to filter props
        data_processor: Data processor
        is_historical: Whether viewing historical week
    """
    # V1 Strategies
    st.subheader("Plum Props")
    col_1, col_2, col_3 = st.columns(3)
    
    with col_1:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v1_Optimal')
    
    with col_2:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v1_Greasy')
    
    with col_3:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v1_Degen')
    
    # V2 Strategies
    st.subheader("Plum Props v2")
    col_1_v2, col_2_v2, col_3_v2 = st.columns(3)
    
    with col_1_v2:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v2_Optimal')
    
    with col_2_v2:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v2_Greasy')
    
    with col_3_v2:
        display_strategy_section(df, filter_props_func, data_processor, is_historical, 'v2_Degen')


def display_time_window_strategies(window_df, filter_props_func, data_processor, is_historical):
    """
    Display strategies for a specific time window.
    
    Args:
        window_df: DataFrame filtered to a specific time window
        filter_props_func: Function to filter props
        data_processor: Data processor
        is_historical: Whether viewing historical week
    """
    def display_strategy_compact(column, strategy_key):
        """Helper to display a strategy in a column without expander."""
        config = STRATEGIES[strategy_key]
        with column:
            st.markdown(f"**{config['emoji']} {config['name']}**")
            display_prop_picks(
                window_df, filter_props_func, data_processor, is_historical,
                score_min=config['score_min'], score_max=config['score_max'],
                odds_min=config['odds_min'], odds_max=config['odds_max'],
                streak_min=config.get('streak_min'), max_players=config['max_players'],
                position_filter=config.get('position_filter', False)
            )
    
    # Display v1 strategies
    cols = st.columns(3)
    for col, strategy in zip(cols, ['v1_Optimal', 'v1_Greasy', 'v1_Degen']):
        display_strategy_compact(col, strategy)
    
    st.markdown("---")
    
    # Display v2 strategies
    st.markdown("**v2 Strategies**")
    cols_v2 = st.columns(3)
    for col, strategy in zip(cols_v2, ['v2_Optimal', 'v2_Greasy', 'v2_Degen']):
        display_strategy_compact(col, strategy)

