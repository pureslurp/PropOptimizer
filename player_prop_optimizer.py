"""
NFL Player Prop Optimizer
A Streamlit application for analyzing NFL player props using matchup data and player history.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime

# Import our custom modules
from enhanced_data_processor import EnhancedFootballDataProcessor
from scoring_model import AdvancedPropScorer
from odds_api import OddsAPI, AlternateLineManager
from utils import clean_player_name, format_odds, format_line, calculate_last_n_over_rate, calculate_streak
from config import ODDS_API_KEY, STAT_TYPES, CONFIDENCE_LEVELS, DEFAULT_MIN_SCORE, PREFERRED_BOOKMAKER

# Set page config
st.set_page_config(
    page_title="NFL Player Prop Optimizer",
    page_icon="🏈",
    layout="wide"
)


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
    
    # Initialize components
    odds_api = OddsAPI(ODDS_API_KEY)
    data_processor = EnhancedFootballDataProcessor()
    scorer = AdvancedPropScorer(data_processor)
    
    # Stat type selector at the top
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        selected_stat = st.selectbox(
            "Select Stat Type",
            STAT_TYPES,
            index=0
        )
    
    with col2:
        if st.button("🔄 Refresh", type="primary"):
            # Clear all cached data on refresh
            if 'alt_line_manager' in st.session_state:
                del st.session_state.alt_line_manager
            if 'props_df_cache' in st.session_state:
                del st.session_state.props_df_cache
            if 'odds_data_cache' in st.session_state:
                del st.session_state.odds_data_cache
            st.rerun()
        export_button = st.button("📥 Export to CSV", type="secondary")
    
    st.subheader(f"Player Props - {selected_stat}")
    st.caption(f"📊 Odds from {PREFERRED_BOOKMAKER} (prioritized)")
    
    # Fetch and display data
    try:
        # Initialize info messages list
        info_messages = []
        
        # Check if we have cached data
        if 'props_df_cache' in st.session_state and 'odds_data_cache' in st.session_state:
            # Use cached data
            props_df = st.session_state.props_df_cache
            odds_data = st.session_state.odds_data_cache
            info_messages.append(('info', f"ℹ️ Using cached props data ({len(props_df)} props from {len(odds_data)} games)"))
        else:
            # Fetch fresh data
            with st.spinner("Fetching player props data..."):
                odds_data = odds_api.get_player_props()
            
            if not odds_data:
                st.error("No odds data available. Please check your API key and try again.")
                st.stop()
            
            # Parse the data
            with st.spinner("Processing player props data..."):
                props_df = odds_api.parse_player_props(odds_data)
            
            if props_df.empty:
                st.warning("No player props found for the selected criteria.")
                st.stop()
            
            # Update team assignments using actual player data
            with st.spinner("Updating team assignments..."):
                props_df = odds_api.update_team_assignments(props_df, data_processor)
            
            # Cache the data
            st.session_state.props_df_cache = props_df
            st.session_state.odds_data_cache = odds_data
            
            # Store success message
            info_messages.append(('success', f"✅ Loaded {len(props_df)} player props from {len(odds_data)} games"))
        
        # Initialize or retrieve alternate line manager from session state
        if 'alt_line_manager' not in st.session_state:
            st.session_state.alt_line_manager = AlternateLineManager(ODDS_API_KEY, odds_data)
        else:
            # Update odds_data in case events changed
            st.session_state.alt_line_manager.odds_data = odds_data
        
        alt_line_manager = st.session_state.alt_line_manager
        
        # Handle export if button was clicked
        if export_button:
            with st.spinner("Generating export for all stat types..."):
                all_export_data = []
                
                # Fetch alternate lines for all stat types
                for stat_type in STAT_TYPES:
                    if stat_type not in alt_line_manager.alternate_lines:
                        with st.spinner(f"Fetching alternate lines for {stat_type}..."):
                            alt_line_manager.alternate_lines[stat_type] = alt_line_manager.fetch_alternate_lines_for_stat(stat_type)
                
                # Process all stat types
                for stat_type in STAT_TYPES:
                    stat_filtered_df = props_df[props_df['Stat Type'] == stat_type].copy()
                    
                    if stat_filtered_df.empty:
                        continue
                    
                    # Calculate scores for this stat type
                    for _, row in stat_filtered_df.iterrows():
                        score_data = scorer.calculate_comprehensive_score(
                            row['Player'],
                            row.get('Opposing Team Full', row['Opposing Team']),  # Use full name for lookups
                            row['Stat Type'],
                            row['Line'],
                            row.get('Odds', 0)
                        )
                        
                        # Calculate L5 over rate for export
                        l5_over_rate = 0.5  # Default
                        player_name = row['Player']
                        if hasattr(data_processor, 'player_season_stats'):
                            player_stats_dict = data_processor.player_season_stats
                            cleaned_player_name = clean_player_name(player_name)
                            player_stats = None
                            for stored_player, stats in player_stats_dict.items():
                                cleaned_stored = clean_player_name(stored_player)
                                if cleaned_stored.lower() == cleaned_player_name.lower() and stat_type in stats:
                                    player_stats = stats[stat_type]
                                    break
                            if player_stats and len(player_stats) > 0:
                                l5_over_rate = calculate_last_n_over_rate(player_stats, row['Line'], n=5)
                        
                        export_row = {
                            'Stat Type': stat_type,
                            'Player': row['Player'],
                            'Team': row['Team'],
                            'Opposing Team': row['Opposing Team'],
                            'Line': row['Line'],
                            'Odds': row.get('Odds', 0),
                            'Team Rank': score_data['team_rank'],
                            'Score': score_data['total_score'],
                            'L5': f"{l5_over_rate*100:.1f}%",
                            'Over Rate': f"{score_data['over_rate']*100:.1f}%",
                            'Player Avg': f"{score_data['player_avg']:.1f}",
                            'Is Alternate': False
                        }
                        all_export_data.append(export_row)
                        
                        # Add ALL alternate lines with odds between +200 and -450
                        player_name = row['Player']
                        if stat_type in alt_line_manager.alternate_lines:
                            player_alt_lines = alt_line_manager.alternate_lines[stat_type].get(player_name, [])
                            
                            # Filter alternate lines by odds criteria
                            for alt_line in player_alt_lines:
                                alt_odds = alt_line.get('odds', 0)
                                
                                # Check if odds are between +200 and -450
                                if -400 <= alt_odds <= 200:
                                    # Get player stats for L5 calculation
                                    player_stats = None
                                    if hasattr(data_processor, 'player_season_stats'):
                                        player_stats_dict = data_processor.player_season_stats
                                        cleaned_player_name = clean_player_name(player_name)
                                        for stored_player, stats in player_stats_dict.items():
                                            cleaned_stored = clean_player_name(stored_player)
                                            if cleaned_stored.lower() == cleaned_player_name.lower() and stat_type in stats:
                                                player_stats = stats[stat_type]
                                                break
                                    
                                    alt_score_data = scorer.calculate_comprehensive_score(
                                        player_name,
                                        row.get('Opposing Team Full', row['Opposing Team']),  # Use full name for lookups
                                        stat_type,
                                        alt_line['line'],
                                        alt_line['odds']
                                    )
                                    
                                    # Calculate L5 for alternate line
                                    alt_l5_over_rate = 0.5  # Default
                                    if player_stats and len(player_stats) > 0:
                                        alt_l5_over_rate = calculate_last_n_over_rate(player_stats, alt_line['line'], n=5)
                                    
                                    alt_export_row = {
                                        'Stat Type': stat_type,
                                        'Player': player_name,
                                        'Team': row['Team'],
                                        'Opposing Team': row['Opposing Team'],
                                        'Line': alt_line['line'],
                                        'Odds': alt_line['odds'],
                                        'Team Rank': alt_score_data['team_rank'],
                                        'Score': alt_score_data['total_score'],
                                        'L5': f"{alt_l5_over_rate*100:.1f}%",
                                        'Over Rate': f"{alt_score_data['over_rate']*100:.1f}%",
                                        'Player Avg': f"{alt_score_data['player_avg']:.1f}",
                                        'Is Alternate': True
                                    }
                                    all_export_data.append(alt_export_row)
                
                # Create DataFrame and CSV
                export_df = pd.DataFrame(all_export_data)
                export_df = export_df.sort_values(['Stat Type', 'Player', 'Is Alternate'])
                
                # Format odds for export
                export_df['Odds'] = export_df['Odds'].apply(format_odds)
                
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
                
                st.success(f"✅ Export ready! {len(export_df)} total props (including alternates) across {len(STAT_TYPES)} stat types")
        
        # Filter by selected stat type
        filtered_df = props_df[props_df['Stat Type'] == selected_stat].copy()
        
        if filtered_df.empty:
            st.warning(f"No {selected_stat} props found.")
            st.stop()
        
        # Pre-fetch alternate lines for the selected stat type (only if not cached)
        if selected_stat not in alt_line_manager.alternate_lines:
            with st.spinner(f"Fetching alternate lines for {selected_stat}..."):
                # This will populate the cache for this stat type
                if selected_stat in alt_line_manager.stat_market_mapping:
                    alt_line_manager.alternate_lines[selected_stat] = alt_line_manager.fetch_alternate_lines_for_stat(selected_stat)
                    info_messages.append(('success', f"✅ Cached alternate lines for {selected_stat}"))
        else:
            info_messages.append(('info', f"ℹ️ Using cached alternate lines for {selected_stat}"))
        
        # Calculate comprehensive scores
        scored_props = []
        alternate_line_props = []  # Store alternate line props separately
        
        for _, row in filtered_df.iterrows():
            score_data = scorer.calculate_comprehensive_score(
                row['Player'],
                row.get('Opposing Team Full', row['Opposing Team']),  # Use full name for lookups
                row['Stat Type'],
                row['Line'],
                row.get('Odds', 0)
            )
            
            # Calculate L5, Home, Away over rates, and Streak
            l5_over_rate = 0.5  # Default
            home_over_rate = 0.5  # Default
            away_over_rate = 0.5  # Default
            streak = 0  # Default
            player_name = row['Player']
            stat_type = row['Stat Type']
            line = row['Line']
            
            # Get player's stat history from data processor
            if hasattr(data_processor, 'player_season_stats'):
                player_stats_dict = data_processor.player_season_stats
                
                # Try to find player stats (case-insensitive with name cleaning)
                cleaned_player_name = clean_player_name(player_name)
                player_stats = None
                for stored_player, stats in player_stats_dict.items():
                    cleaned_stored = clean_player_name(stored_player)
                    if cleaned_stored.lower() == cleaned_player_name.lower() and stat_type in stats:
                        player_stats = stats[stat_type]
                        break
                
                if player_stats and len(player_stats) > 0:
                    # Calculate L5 over rate
                    l5_over_rate = calculate_last_n_over_rate(player_stats, line, n=5)
                    # Calculate streak
                    streak = calculate_streak(player_stats, line)
            
            # Calculate home/away over rates
            home_over_rate = data_processor.get_player_home_over_rate(player_name, stat_type, line)
            away_over_rate = data_processor.get_player_away_over_rate(player_name, stat_type, line)
            
            scored_prop = {**row.to_dict(), **score_data, 'l5_over_rate': l5_over_rate, 
                          'home_over_rate': home_over_rate, 'away_over_rate': away_over_rate, 'streak': streak}
            scored_props.append(scored_prop)
            
            # Get ALL alternate lines with odds between +200 and -450
            if stat_type in alt_line_manager.alternate_lines:
                player_alt_lines = alt_line_manager.alternate_lines[stat_type].get(player_name, [])
                
                # Filter alternate lines by odds criteria
                for alt_line in player_alt_lines:
                    alt_odds = alt_line.get('odds', 0)
                    
                    # Check if odds are between +200 and -450
                    if -450 <= alt_odds <= 200:
                        # Get player stats for L5 calculation
                        player_stats = None
                        if hasattr(data_processor, 'player_season_stats'):
                            player_stats_dict = data_processor.player_season_stats
                            cleaned_player_name = clean_player_name(player_name)
                            for stored_player, stats in player_stats_dict.items():
                                cleaned_stored = clean_player_name(stored_player)
                                if cleaned_stored.lower() == cleaned_player_name.lower() and stat_type in stats:
                                    player_stats = stats[stat_type]
                                    break
                        
                        # Create alternate line prop row
                        alt_score_data = scorer.calculate_comprehensive_score(
                            player_name,
                            row.get('Opposing Team Full', row['Opposing Team']),  # Use full name for lookups
                            stat_type,
                            alt_line['line'],
                            alt_line['odds']
                        )
                        
                        # Calculate L5 for alternate line
                        alt_l5_over_rate = 0.5  # Default
                        alt_streak = 0  # Default
                        if player_stats and len(player_stats) > 0:
                            alt_l5_over_rate = calculate_last_n_over_rate(player_stats, alt_line['line'], n=5)
                            alt_streak = calculate_streak(player_stats, alt_line['line'])
                        
                        # Calculate home/away over rates for alternate line
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
                            'is_alternate': True  # Flag to identify alternate lines
                        }
                        alternate_line_props.append(alt_prop)
        
        # Combine main props and alternate line props
        all_props = scored_props + alternate_line_props
        
        # Store info about alternate lines added
        if alternate_line_props:
            info_messages.append(('info', f"✨ Added {len(alternate_line_props)} alternate line(s) with odds between +200 and -450"))
        
        # Convert to DataFrame
        results_df = pd.DataFrame(all_props)
        
        # Add is_alternate flag if not present
        if 'is_alternate' not in results_df.columns:
            results_df['is_alternate'] = False
        
        # Sort by Player name, then by is_alternate (False first, then True)
        # This groups each player's main line with their alternate line
        results_df = results_df.sort_values(['Player', 'is_alternate'], ascending=[True, True])
        
        if results_df.empty:
            st.warning(f"No props found matching the selected criteria.")
            st.stop()
        
        # Format the display
        display_columns = [
            'Player', 'Opposing Team', 'team_rank',
            'Line', 'Odds', 'streak', 'l5_over_rate', 'home_over_rate', 'away_over_rate', 'over_rate'
        ]
        
        display_df = results_df[display_columns].copy()
        
        # Rename columns for display
        display_df.columns = [
            'Player', 'Opposing Team', 'Team Rank',
            'Line', 'Odds', 'Streak', 'L5', 'Home', 'Away', '25/26'
        ]
        
        # Format the line display
        display_df['Line'] = display_df['Line'].apply(lambda x: format_line(x, selected_stat))
        
        # Format odds
        display_df['Odds'] = display_df['Odds'].apply(format_odds)
        
        # Store numeric values for styling before converting to strings
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
        display_columns_final = ['Player', 'Opposing Team', 'Team Rank', 'Line', 'Odds', 'Streak', 'L5', 'Home', 'Away', '25/26']
        
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
