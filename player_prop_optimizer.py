"""
NFL Player Prop Optimizer
A Streamlit application for analyzing NFL player props using matchup data and player history.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime
import os

# Import our custom modules
from enhanced_data_processor import EnhancedFootballDataProcessor
from scoring_model import AdvancedPropScorer
from odds_api import OddsAPI, AlternateLineManager
from utils import clean_player_name, format_odds, format_line
from config import ODDS_API_KEY, STAT_TYPES, CONFIDENCE_LEVELS, DEFAULT_MIN_SCORE, PREFERRED_BOOKMAKER
from utils import get_current_week_from_schedule, get_available_weeks_with_data

# Set page config
st.set_page_config(
    page_title="NFL Player Prop Optimizer",
    page_icon="🏈",
    layout="wide"
)


# Removed - now using get_available_weeks_with_data() from week_utils


def load_historical_props_for_week(week_num):
    """Load historical props data for a specific week"""
    props_file = f"2025/WEEK{week_num}/props.csv"
    
    if not os.path.exists(props_file):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(props_file)
        return df
    except Exception as e:
        print(f"Error loading historical props: {e}")
        return pd.DataFrame()


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
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown("---")
    
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
    
    # Initialize components
    odds_api = OddsAPI(ODDS_API_KEY)
    data_processor = EnhancedFootballDataProcessor()
    scorer = AdvancedPropScorer(data_processor)
    
    # Control buttons at the top
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Refresh", type="primary"):
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
        export_button = st.button("📥 Export to CSV", type="secondary")
    
    st.caption(f"📊 Odds from {PREFERRED_BOOKMAKER} (prioritized)")
    
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
            info_messages.append(('info', f"ℹ️ Using cached data ({len(all_props)} total props)"))
        else:
            # Fetch fresh data with progress bars
            progress_bar = st.progress(0, text="Fetching player props data...")
            odds_data = odds_api.get_player_props()
            progress_bar.progress(10, text="Processing player props data...")
            
            if not odds_data:
                st.error("No odds data available. Please check your API key and try again.")
                st.stop()
            
            # Parse the data
            props_df = odds_api.parse_player_props(odds_data)
            progress_bar.progress(20, text="Updating team assignments...")
            
            if props_df.empty:
                st.warning("No player props found for the selected criteria.")
                st.stop()
            
            # Update team assignments using actual player data
            props_df = odds_api.update_team_assignments(props_df, data_processor)
            
            # Cache the raw data
            st.session_state.props_df_cache = props_df
            st.session_state.odds_data_cache = odds_data
            
            # Initialize alternate line manager
            alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
            st.session_state.alt_line_manager = alt_line_manager
            
            # Fetch alternate lines for all stat types with progress
            progress_bar.progress(30, text="Fetching alternate lines for all stat types...")
            stat_types_in_data = props_df['Stat Type'].unique()
            for idx, stat_type in enumerate(stat_types_in_data):
                if stat_type in alt_line_manager.stat_market_mapping:
                    progress_text = f"Fetching alternate lines for {stat_type}... ({idx+1}/{len(stat_types_in_data)})"
                    progress_val = 30 + int((idx + 1) / len(stat_types_in_data) * 20)
                    progress_bar.progress(progress_val, text=progress_text)
                    alt_line_manager.alternate_lines[stat_type] = alt_line_manager.fetch_alternate_lines_for_stat(stat_type)
            
            # Process all stat types and calculate scores
            progress_bar.progress(50, text="Calculating scores for all props...")
            all_props = []
            
            for idx, stat_type in enumerate(stat_types_in_data):
                stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
                
                if stat_filtered_df.empty:
                    continue
                
                progress_text = f"Processing {stat_type}... ({idx+1}/{len(stat_types_in_data)})"
                progress_val = 50 + int((idx + 1) / len(stat_types_in_data) * 40)
                progress_bar.progress(progress_val, text=progress_text)
                
                # Calculate scores for main lines
                for _, row in stat_filtered_df.iterrows():
                    score_data = scorer.calculate_comprehensive_score(
                        row['Player'],
                        row.get('Opposing Team Full', row['Opposing Team']),
                        row['Stat Type'],
                        row['Line'],
                        row.get('Odds', 0)
                    )
                    
                    # Calculate L5, Home, Away over rates, and Streak
                    player_name = row['Player']
                    line = row['Line']
                    
                    l5_over_rate = data_processor.get_player_last_n_over_rate(player_name, stat_type, line, n=5)
                    streak = data_processor.get_player_streak(player_name, stat_type, line)
                    home_over_rate = data_processor.get_player_home_over_rate(player_name, stat_type, line)
                    away_over_rate = data_processor.get_player_away_over_rate(player_name, stat_type, line)
                    
                    scored_prop = {
                        **row.to_dict(),
                        **score_data,
                        'l5_over_rate': l5_over_rate,
                        'home_over_rate': home_over_rate,
                        'away_over_rate': away_over_rate,
                        'streak': streak,
                        'is_alternate': False
                    }
                    all_props.append(scored_prop)
                    
                    # Add alternate lines with odds between +200 and -450
                    if stat_type in alt_line_manager.alternate_lines:
                        player_alt_lines = alt_line_manager.alternate_lines[stat_type].get(player_name, [])
                        
                        for alt_line in player_alt_lines:
                            alt_odds = alt_line.get('odds', 0)
                            
                            if -450 <= alt_odds <= 200:
                                alt_score_data = scorer.calculate_comprehensive_score(
                                    player_name,
                                    row.get('Opposing Team Full', row['Opposing Team']),
                                    stat_type,
                                    alt_line['line'],
                                    alt_line['odds']
                                )
                                
                                alt_l5_over_rate = data_processor.get_player_last_n_over_rate(player_name, stat_type, alt_line['line'], n=5)
                                alt_streak = data_processor.get_player_streak(player_name, stat_type, alt_line['line'])
                                alt_home_over_rate = data_processor.get_player_home_over_rate(player_name, stat_type, alt_line['line'])
                                alt_away_over_rate = data_processor.get_player_away_over_rate(player_name, stat_type, alt_line['line'])
                                
                                alt_prop = {
                                    **row.to_dict(),
                                    'Line': alt_line['line'],
                                    'Odds': alt_line['odds'],
                                    **alt_score_data,
                                    'l5_over_rate': alt_l5_over_rate,
                                    'home_over_rate': alt_home_over_rate,
                                    'away_over_rate': alt_away_over_rate,
                                    'streak': alt_streak,
                                    'is_alternate': True
                                }
                                all_props.append(alt_prop)
            
            progress_bar.progress(100, text="Complete!")
            progress_bar.empty()  # Clear the progress bar
            
            # Cache the processed data
            st.session_state.all_scored_props = all_props
            
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
                        'Opposing Team': prop['Opposing Team'],
                        'Line': prop['Line'],
                        'Odds': format_odds(prop.get('Odds', 0)),
                        'Team Rank': prop['team_rank'],
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
        
        # Update sidebar with stats after filtering
        with st.sidebar:
            st.markdown("---")
            
            # Show stats summary
            st.metric("Stat Types Selected", f"{len(selected_stat_types)}/{len(available_stat_types)}")
            st.metric("Games Selected", f"{len(selected_games)}/{len(available_matchups)}")
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
        
        # Format the display
        display_columns = [
            'Stat Type', 'Player', 'Opposing Team', 'team_rank', 'total_score',
            'Line', 'Odds', 'streak', 'l5_over_rate', 'home_over_rate', 'away_over_rate', 'over_rate'
        ]
        
        display_df = results_df[display_columns].copy()
        
        # Rename columns for display
        display_df.columns = [
            'Stat Type', 'Player', 'Opposing Team', 'Team Rank', 'Score',
            'Line', 'Odds', 'Streak', 'L5', 'Home', 'Away', '25/26'
        ]
        
        # Format the line display (need to handle different stat types)
        display_df['Line'] = display_df.apply(
            lambda row: format_line(row['Line'], row['Stat Type']), 
            axis=1
        )
        
        # Format odds
        display_df['Odds'] = display_df['Odds'].apply(format_odds)
        
        # Format Score as decimal with 2 decimal places
        display_df['Score_numeric'] = display_df['Score']  # Store for styling
        display_df['Score'] = display_df['Score'].apply(lambda x: f"{x:.2f}")
        display_df['L5_numeric'] = display_df['L5'] * 100
        display_df['Home_numeric'] = display_df['Home'] * 100
        display_df['Away_numeric'] = display_df['Away'] * 100
        display_df['25/26_numeric'] = display_df['25/26'] * 100
        
        # Format L5 over rate as percentage
        display_df['L5'] = display_df['L5_numeric'].round(1).astype(str) + '%'
        
        # Format Home over rate as percentage
        display_df['Home'] = display_df['Home_numeric'].round(1).astype(str) + '%'
        
        # Format Away over rate as percentage
        display_df['Away'] = display_df['Away_numeric'].round(1).astype(str) + '%'
        
        # Format season over rate as percentage
        display_df['25/26'] = display_df['25/26_numeric'].round(1).astype(str) + '%'
        
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
            if 'Team Rank' in row.index:
                try:
                    val = row['Team Rank']
                    if val <= 10:
                        styles['Team Rank'] = 'background-color: #f8d7da; color: #721c24'
                    elif val >= 21:
                        styles['Team Rank'] = 'background-color: #d4edda; color: #155724'
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
        display_columns_final = ['Stat Type', 'Player', 'Opposing Team', 'Team Rank', 'Line', 'Odds', 'Score', 'Streak', 'L5', 'Home', 'Away', '25/26']
        
        # Display the results with styling
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_order=display_columns_final
        )
        
        # Display info messages below the table
        for msg_type, msg_text in info_messages:
            if msg_type == 'info':
                st.info(msg_text)
            elif msg_type == 'success':
                st.success(msg_text)
        
        # Function to display prop picks based on score threshold
        def display_prop_picks(df, score_min, score_max, odds_min=-400, odds_max=-150):
            """Display top 5 props based on score threshold with parlay odds"""
            # Filter: score in range and odds between odds_min and odds_max
            filtered_df = df[
                (df['total_score'] >= score_min) & 
                (df['total_score'] < score_max) &
                (df['Odds'] >= odds_min) & 
                (df['Odds'] <= odds_max)
            ].copy()
            
            if not filtered_df.empty:
                # Keep only highest score per player+stat type combination
                filtered_df = filtered_df.sort_values('total_score', ascending=False)
                filtered_df = filtered_df.drop_duplicates(subset=['Player', 'Stat Type'], keep='first')
                
                # Get top 5
                top_5 = filtered_df.head(5)
                
                # Display as condensed bullets
                for _, row in top_5.iterrows():
                    # Abbreviate stat type
                    stat_abbrev = row['Stat Type'].replace('Passing Yards', 'PassYds') \
                                                  .replace('Rushing Yards', 'RushYds') \
                                                  .replace('Receiving Yards', 'RecYds') \
                                                  .replace('Passing TDs', 'PassTD') \
                                                  .replace('Rushing TDs', 'RushTD') \
                                                  .replace('Receiving TDs', 'RecTD') \
                                                  .replace('Receptions', 'Rec')
                    
                    st.markdown(f"• **{row['Player']}** {row['Line']}+ {stat_abbrev} {format_odds(row['Odds'])} odds")
                
                # Calculate parlay odds
                parlay_decimal = 1.0
                for _, row in top_5.iterrows():
                    odds = row['Odds']
                    # Convert American odds to decimal
                    if odds < 0:
                        decimal = 1 + (100 / abs(odds))
                    else:
                        decimal = 1 + (odds / 100)
                    parlay_decimal *= decimal
                
                # Convert parlay decimal back to American odds
                if parlay_decimal >= 2.0:
                    parlay_american = int((parlay_decimal - 1) * 100)
                    parlay_odds_str = f"+{parlay_american}"
                else:
                    parlay_american = int(-100 / (parlay_decimal - 1))
                    parlay_odds_str = str(parlay_american)
                
                st.markdown(f"• **If Parlayed:** {parlay_odds_str} odds")
            else:
                st.markdown("*No props meet the criteria*")
        
        # Three prop strategy sections in columns
        col_1, col_2, col_3 = st.columns(3)
        
        with col_1:
            with st.expander("🎯 Optimal", expanded=False):
                display_prop_picks(results_df, score_min=70, score_max=float('inf'))
        
        with col_2:
            with st.expander("🧈 Greasy", expanded=False):
                display_prop_picks(results_df, score_min=50, score_max=70)
        
        with col_3:
            with st.expander("🎲 Degen", expanded=False):
                display_prop_picks(results_df, score_min=0, score_max=50)
        
        # Column Explanations Section
        with st.expander("📖 Column Explanations", expanded=False):
            st.markdown("""
            ### What Each Column Means
            
            **Player** - The NFL player's name for this prop bet
            
            **Opposing Team** - The defense the player is facing this week
            - Format: "vs TEAM" (home game) or "@ TEAM" (away game)
            
            **Team Rank** - Defensive ranking against this stat type (1-32)
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
            - Green Team Rank = weak opposing defense
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
