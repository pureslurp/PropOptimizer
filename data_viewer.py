"""
Data Viewer for Player Prop Optimizer
Streamlit app to view player and team statistics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from enhanced_data_processor import EnhancedFootballDataProcessor
from datetime import datetime

def main():
    """Main Streamlit app for data viewing"""
    st.title("📊 NFL Data Viewer")
    st.markdown("View player statistics and team defensive rankings")
    
    # Initialize data processor
    with st.spinner("Loading data..."):
        processor = EnhancedFootballDataProcessor()
    
    # Sidebar for data management
    with st.sidebar:
        st.subheader("🔧 Data Management")
        
        # Show data summary
        summary = processor.get_data_summary()
        st.metric("Total Players", summary['total_players'])
        st.metric("Total Games", summary['total_games'])
        st.metric("Current Week", summary['current_week'])
        
        # Cache status
        st.subheader("💾 Cache Status")
        cache_status = summary['cache_status']
        if cache_status['player_season']:
            st.success("✅ Player data cached")
        else:
            st.warning("⚠️ No player data cache")
            
        if cache_status['team_defensive']:
            st.success("✅ Team data cached")
        else:
            st.warning("⚠️ No team data cache")
        
        # Update data section
        st.subheader("🔄 Update Data")
        st.markdown("""
        **To update data:**
        1. Run `python update_data.py` after games
        2. Data is cached for 1 week
        3. Force refresh if needed
        """)
        
        if st.button("🔄 Force Refresh Data", type="secondary"):
            with st.spinner("Updating data..."):
                try:
                    processor.update_season_data(force_refresh=True)
                    st.success("✅ Data updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating data: {e}")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["👥 Player Stats", "🛡️ Team Defense", "📈 Player Analysis"])
    
    with tab1:
        st.subheader("Player Statistics")
        
        # Player selector
        available_players = processor.get_available_players()
        if not available_players:
            st.warning("No player data available. Run data update first.")
            st.stop()
        
        selected_player = st.selectbox("Select Player", available_players)
        
        if selected_player:
            # Get detailed stats
            player_stats = processor.get_player_detailed_stats(selected_player)
            
            if player_stats:
                st.subheader(f"📊 {selected_player} - Season Stats")
                
                # Create metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_games = sum(stats['games'] for stats in player_stats.values())
                    st.metric("Total Games", total_games)
                
                with col2:
                    # Show most relevant stat
                    if 'Passing Yards' in player_stats:
                        avg_passing = player_stats['Passing Yards']['average']
                        st.metric("Avg Passing Yards", f"{avg_passing:.1f}")
                    elif 'Rushing Yards' in player_stats:
                        avg_rushing = player_stats['Rushing Yards']['average']
                        st.metric("Avg Rushing Yards", f"{avg_rushing:.1f}")
                    elif 'Receiving Yards' in player_stats:
                        avg_receiving = player_stats['Receiving Yards']['average']
                        st.metric("Avg Receiving Yards", f"{avg_receiving:.1f}")
                
                with col3:
                    # Show consistency
                    if 'Passing Yards' in player_stats:
                        consistency = player_stats['Passing Yards']['consistency']
                        st.metric("Passing Consistency", f"{consistency:.1f}")
                    elif 'Rushing Yards' in player_stats:
                        consistency = player_stats['Rushing Yards']['consistency']
                        st.metric("Rushing Consistency", f"{consistency:.1f}")
                    elif 'Receiving Yards' in player_stats:
                        consistency = player_stats['Receiving Yards']['consistency']
                        st.metric("Receiving Consistency", f"{consistency:.1f}")
                
                with col4:
                    # Show best game
                    best_performance = 0
                    best_stat = ""
                    for stat_name, stats in player_stats.items():
                        if stats['max'] > best_performance:
                            best_performance = stats['max']
                            best_stat = stat_name
                    
                    st.metric(f"Best {best_stat}", f"{best_performance:.1f}")
                
                # Create charts for each stat
                for stat_name, stats in player_stats.items():
                    st.subheader(f"📈 {stat_name}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Bar chart of game-by-game performance
                        fig = px.bar(
                            x=list(range(1, len(stats['values']) + 1)),
                            y=stats['values'],
                            title=f"{stat_name} by Game",
                            labels={'x': 'Game', 'y': stat_name}
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Stats summary
                        st.markdown(f"""
                        **Summary:**
                        - Games: {stats['games']}
                        - Average: {stats['average']:.1f}
                        - Min: {stats['min']:.1f}
                        - Max: {stats['max']:.1f}
                        - Consistency: {stats['consistency']:.1f}
                        """)
                        
                        # Over rate for different lines
                        st.markdown("**Over Rate for Common Lines:**")
                        common_lines = _get_common_lines(stat_name)
                        for line in common_lines:
                            over_rate = processor.get_player_over_rate(selected_player, stat_name, line)
                            st.write(f"{line}+: {over_rate*100:.1f}%")
            else:
                st.warning(f"No detailed stats available for {selected_player}")
    
    with tab2:
        st.subheader("Team Defensive Rankings")
        
        # Team defensive stats
        if processor.team_defensive_stats:
            for stat_type, team_stats in processor.team_defensive_stats.items():
                st.subheader(f"🛡️ {stat_type}")
                
                # Create DataFrame for display
                df = pd.DataFrame([
                    {'Team': team, 'Yards Allowed': yards, 'Rank': i+1}
                    for i, (team, yards) in enumerate(sorted(team_stats.items(), key=lambda x: x[1]))
                ])
                
                # Display as table
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Create bar chart
                fig = px.bar(
                    df.head(10),  # Top 10 defenses
                    x='Team',
                    y='Yards Allowed',
                    title=f"Top 10 Defenses - {stat_type}",
                    color='Yards Allowed',
                    color_continuous_scale='RdYlGn_r'  # Red to Green (lower is better)
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No team defensive data available. Run data update first.")
    
    with tab3:
        st.subheader("Player Analysis")
        
        # Show players with best consistency
        if available_players:
            st.subheader("🎯 Most Consistent Players")
            
            consistency_data = []
            for player in available_players[:20]:  # Check top 20 players
                player_stats = processor.get_player_detailed_stats(player)
                
                # Get consistency for primary stat
                primary_stat = None
                consistency = None
                
                if 'Passing Yards' in player_stats:
                    primary_stat = 'Passing Yards'
                    consistency = player_stats['Passing Yards']['consistency']
                elif 'Rushing Yards' in player_stats:
                    primary_stat = 'Rushing Yards'
                    consistency = player_stats['Rushing Yards']['consistency']
                elif 'Receiving Yards' in player_stats:
                    primary_stat = 'Receiving Yards'
                    consistency = player_stats['Receiving Yards']['consistency']
                
                if primary_stat and consistency is not None:
                    avg_performance = player_stats[primary_stat]['average']
                    consistency_data.append({
                        'Player': player,
                        'Stat': primary_stat,
                        'Average': avg_performance,
                        'Consistency': consistency,
                        'Games': player_stats[primary_stat]['games']
                    })
            
            if consistency_data:
                # Sort by consistency (lower is better)
                consistency_data.sort(key=lambda x: x['Consistency'])
                
                # Create DataFrame
                df = pd.DataFrame(consistency_data)
                
                # Display table
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Create scatter plot
                fig = px.scatter(
                    df,
                    x='Average',
                    y='Consistency',
                    color='Stat',
                    hover_data=['Player', 'Games'],
                    title="Player Consistency vs Average Performance",
                    labels={'Consistency': 'Standard Deviation (Lower = More Consistent)'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
def _get_common_lines(stat_name: str) -> list:
        """Get common betting lines for a stat type"""
        if 'Passing Yards' in stat_name:
            return [200, 250, 275, 300, 325, 350]
        elif 'Rushing Yards' in stat_name:
            return [50, 75, 100, 125, 150]
        elif 'Receiving Yards' in stat_name:
            return [50, 75, 100, 125, 150]
        elif 'Receptions' in stat_name:
            return [3, 4, 5, 6, 7, 8]
        elif 'TDs' in stat_name:
            return [1, 2, 3]
        else:
            return []

if __name__ == "__main__":
    main()
