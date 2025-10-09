"""
Utility functions for determining the current NFL week based on schedule dates.
"""

import pandas as pd
from datetime import datetime
import os


def get_current_week_from_schedule(schedule_file="2025/nfl_schedule.csv"):
    """
    Determine the current NFL week based on the schedule and today's date.
    
    Logic:
    - If today is between week X-1's last game and week X's last game, it's week X
    - This works regardless of whether folders exist or not
    
    Returns:
        int: Current NFL week number (1-18)
    """
    if not os.path.exists(schedule_file):
        print(f"⚠️ Schedule file not found: {schedule_file}")
        print("   Falling back to folder-based detection")
        return get_current_week_from_folders()
    
    try:
        # Load schedule
        schedule = pd.read_csv(schedule_file)
        
        # Parse dates - handle "Sep 4 2025" format
        schedule['parsed_date'] = pd.to_datetime(
            schedule['Date'] + ' ' + schedule['Time (ET)'].str.split().str[0],
            format='%b %d %Y %I:%M',
            errors='coerce'
        )
        
        # Get today's date (without time for comparison)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Group by week and get the last game date for each week
        week_end_dates = schedule.groupby('Week')['parsed_date'].max().sort_index()
        
        # Determine current week
        for week in week_end_dates.index:
            week_end = week_end_dates[week].replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Add a day buffer - if we're within 24 hours after last game, still that week
            # (gives time for box scores to be processed)
            week_end_with_buffer = week_end + pd.Timedelta(days=1)
            
            if today <= week_end_with_buffer:
                return int(week)
        
        # If we're past all scheduled weeks, return the last week + 1
        return int(week_end_dates.index[-1]) + 1
    
    except Exception as e:
        print(f"⚠️ Error parsing schedule: {e}")
        print("   Falling back to folder-based detection")
        return get_current_week_from_folders()


def get_current_week_from_folders():
    """
    Fallback method: Determine current week based on which folders have box scores.
    
    Logic:
    - Check which WEEK folders have box_score_debug.csv (completed weeks)
    - Current week = highest completed week + 1
    
    Returns:
        int: Current NFL week number (1-18)
    """
    completed_weeks = []
    year_folder = "2025"
    
    if os.path.exists(year_folder):
        for item in os.listdir(year_folder):
            if item.startswith("WEEK") and os.path.isdir(os.path.join(year_folder, item)):
                try:
                    week_num = int(item.replace("WEEK", ""))
                    # Check if box score exists (indicating week is completed)
                    box_score_path = os.path.join(year_folder, item, "box_score_debug.csv")
                    if os.path.exists(box_score_path):
                        completed_weeks.append(week_num)
                except ValueError:
                    continue
    
    # Current week is the next week after the latest completed week
    if completed_weeks:
        return max(completed_weeks) + 1
    return 1


def get_available_weeks_with_data():
    """
    Get list of weeks that have any data (props or box scores).
    
    Returns:
        dict: {
            'all': [1, 2, 3, 4, 5, 6],  # All weeks with folders
            'with_props': [6],          # Weeks with saved props
            'with_scores': [1, 2, 3, 4, 5],  # Weeks with box scores
            'complete': []              # Weeks with both props and scores
        }
    """
    year_folder = "2025"
    all_weeks = []
    with_props = []
    with_scores = []
    complete = []
    
    if os.path.exists(year_folder):
        for item in os.listdir(year_folder):
            if item.startswith("WEEK") and os.path.isdir(os.path.join(year_folder, item)):
                try:
                    week_num = int(item.replace("WEEK", ""))
                    all_weeks.append(week_num)
                    
                    week_path = os.path.join(year_folder, item)
                    has_props = os.path.exists(os.path.join(week_path, "props.csv"))
                    has_scores = os.path.exists(os.path.join(week_path, "box_score_debug.csv"))
                    
                    if has_props:
                        with_props.append(week_num)
                    if has_scores:
                        with_scores.append(week_num)
                    if has_props and has_scores:
                        complete.append(week_num)
                        
                except ValueError:
                    continue
    
    return {
        'all': sorted(all_weeks),
        'with_props': sorted(with_props),
        'with_scores': sorted(with_scores),
        'complete': sorted(complete)
    }


if __name__ == "__main__":
    """Test the week detection functions"""
    print("Testing Week Detection Functions")
    print("=" * 60)
    
    print("\n1. Schedule-based detection:")
    current_week = get_current_week_from_schedule()
    print(f"   Current week: {current_week}")
    
    print("\n2. Folder-based detection (fallback):")
    fallback_week = get_current_week_from_folders()
    print(f"   Current week: {fallback_week}")
    
    print("\n3. Available weeks:")
    weeks_data = get_available_weeks_with_data()
    print(f"   All weeks: {weeks_data['all']}")
    print(f"   With props: {weeks_data['with_props']}")
    print(f"   With scores: {weeks_data['with_scores']}")
    print(f"   Complete (both): {weeks_data['complete']}")
    
    print("\n" + "=" * 60)

