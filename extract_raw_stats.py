#!/usr/bin/env python3
"""
Extract raw stats from the box score scraper before DFS scoring is applied.
This gets the actual yards, receptions, etc. instead of DFS points.
"""

import pandas as pd
import os
import argparse
from collections import defaultdict
import re
from utils import clean_player_name
from dfs_box_scores import FootballDBScraper

def extract_raw_stats_for_week(week):
    """
    Extract raw stats directly from the scraper before DFS processing.
    """
    print(f"📊 Extracting raw stats for Week {week}...")
    
    try:
        scraper = FootballDBScraper(week)
        driver = scraper.setup_driver()
        
        try:
            # Get all game data
            master_df = scraper.process_all_games()
            
            if master_df.empty:
                print(f"⚠️ No data found for Week {week}")
                return {}
            
            print(f"✅ Found {len(master_df)} players with raw stats")
            
            # The master_df should contain the raw stats before DFS scoring
            # Let's examine what columns we have
            print(f"Available columns: {master_df.columns.tolist()}")
            
            # Group by position and collect raw stats
            position_stats = defaultdict(lambda: {
                'passing_yards': [],
                'rushing_yards': [],
                'receiving_yards': [],
                'receptions': [],
                'passing_tds': [],
                'rushing_tds': [],
                'receiving_tds': []
            })
            
            for _, row in master_df.iterrows():
                name = row['Name'].strip()
                
                # Infer position from available stats
                position = infer_position_from_raw_stats(row)
                
                if position:
                    stats = position_stats[position]
                    
                    # Collect raw stats (before DFS conversion)
                    if 'pass_Yds' in row and pd.notna(row['pass_Yds']) and row['pass_Yds'] > 0:
                        stats['passing_yards'].append(row['pass_Yds'])
                    if 'pass_TD' in row and pd.notna(row['pass_TD']) and row['pass_TD'] > 0:
                        stats['passing_tds'].append(row['pass_TD'])
                    
                    if 'rush_Yds' in row and pd.notna(row['rush_Yds']) and row['rush_Yds'] > 0:
                        stats['rushing_yards'].append(row['rush_Yds'])
                    if 'rush_TD' in row and pd.notna(row['rush_TD']) and row['rush_TD'] > 0:
                        stats['rushing_tds'].append(row['rush_TD'])
                    
                    if 'rec_Rec' in row and pd.notna(row['rec_Rec']) and row['rec_Rec'] > 0:
                        stats['receptions'].append(row['rec_Rec'])
                    if 'rec_Yds' in row and pd.notna(row['rec_Yds']) and row['rec_Yds'] > 0:
                        stats['receiving_yards'].append(row['rec_Yds'])
                    if 'rec_TD' in row and pd.notna(row['rec_TD']) and row['rec_TD'] > 0:
                        stats['receiving_tds'].append(row['rec_TD'])
            
            # Calculate averages for each position
            defensive_stats = {}
            
            for position, stats in position_stats.items():
                position_summary = {}
                
                for stat_type, values in stats.items():
                    if values:
                        avg_value = sum(values) / len(values)
                        position_summary[stat_type] = {
                            'average': avg_value,
                            'count': len(values),
                            'values': values
                        }
                
                if position_summary:
                    defensive_stats[position] = position_summary
                    print(f"Position {position}:")
                    for stat_type, summary in position_summary.items():
                        print(f"  {stat_type}: {summary['count']} players, avg {summary['average']:.1f}")
            
            return defensive_stats
            
        finally:
            if driver:
                driver.quit()
                
    except Exception as e:
        print(f"❌ Error extracting raw stats for Week {week}: {e}")
        return {}

def infer_position_from_raw_stats(row):
    """
    Infer player position from raw statistics.
    """
    # Check for passing stats
    if 'pass_Yds' in row and pd.notna(row['pass_Yds']) and row['pass_Yds'] > 0:
        return 'QB'
    
    # Check for rushing stats
    if 'rush_Yds' in row and pd.notna(row['rush_Yds']) and row['rush_Yds'] > 0:
        # Could be RB or QB with rushing stats
        if 'pass_Yds' in row and pd.notna(row['pass_Yds']) and row['pass_Yds'] > 0:
            return 'QB'  # QB with rushing stats
        else:
            return 'RB'
    
    # Check for receiving stats
    if 'rec_Rec' in row and pd.notna(row['rec_Rec']) and row['rec_Rec'] > 0:
        # Could be WR or TE
        if 'rec_Yds' in row and pd.notna(row['rec_Yds']):
            # Simple heuristic: more receiving yards = more likely WR
            if row['rec_Yds'] > 80:  # Arbitrary threshold
                return 'WR'
            else:
                return 'TE'
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Extract raw stats from box score scraper')
    parser.add_argument('week', type=int, help='Week number to extract stats for')
    
    args = parser.parse_args()
    
    raw_stats = extract_raw_stats_for_week(args.week)
    
    if raw_stats:
        print(f"\n✅ Successfully extracted raw stats for Week {args.week}")
        
        # Show summary
        for position, position_stats in raw_stats.items():
            print(f"\n{position}:")
            for stat_type, summary in position_stats.items():
                print(f"  {stat_type}: {summary['count']} players, avg {summary['average']:.1f}")
    else:
        print(f"❌ Failed to extract raw stats for Week {args.week}")

if __name__ == "__main__":
    main()
