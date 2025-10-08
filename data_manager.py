#!/usr/bin/env python3
"""
Data Manager for NFL Player Prop Optimizer
Handles efficient data processing and caching for optimal performance
"""

import os
import pandas as pd
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
from enhanced_data_processor import EnhancedFootballDataProcessor
from position_vs_team_analysis import load_week_data, calculate_totals

class NFLDataManager:
    """Manages NFL data processing and caching for optimal performance"""
    
    def __init__(self, data_dir: str = "2025", cache_dir: str = "cache"):
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_available_weeks(self) -> List[int]:
        """Get list of available weeks from data directory"""
        if not os.path.exists(self.data_dir):
            return []
        
        weeks = []
        for item in os.listdir(self.data_dir):
            if item.startswith('WEEK') and os.path.isdir(os.path.join(self.data_dir, item)):
                week_num = int(item.replace('WEEK', ''))
                weeks.append(week_num)
        
        return sorted(weeks)
    
    def is_week_data_complete(self, week: int) -> bool:
        """Check if a week has all required data files for raw stats analysis"""
        week_path = f"{self.data_dir}/WEEK{week}"
        
        if not os.path.exists(week_path):
            return False
        
        files = os.listdir(week_path)
        
        # For raw stats analysis, we only need box score files
        # DKSalaries files are not required for raw stats processing
        has_box_scores = any(f.startswith('box_score') for f in files)
        
        return has_box_scores
    
    def get_week_data_status(self) -> Dict[int, Dict]:
        """Get status of all weeks"""
        weeks = self.get_available_weeks()
        status = {}
        
        for week in weeks:
            week_path = f"{self.data_dir}/WEEK{week}"
            files = os.listdir(week_path) if os.path.exists(week_path) else []
            
            status[week] = {
                'path': week_path,
                'has_box_scores': any(f.startswith('box_score') for f in files),
                'has_dk_salaries': any(f.startswith('DKSalaries') for f in files),
                'files': files,
                'complete': self.is_week_data_complete(week)
            }
        
        return status
    
    def process_week_efficiently(self, week: int) -> bool:
        """Process a single week's data efficiently for raw stats analysis"""
        print(f"📊 Processing Week {week} data...")
        
        try:
            week_path = f"{self.data_dir}/WEEK{week}"
            
            if not self.is_week_data_complete(week):
                print(f"❌ Week {week} data incomplete")
                return False
            
            # For raw stats analysis, we just need to verify the box score file exists
            # and is readable - no need for complex data loading
            box_score_file = f"{week_path}/box_score_debug.csv"
            if not os.path.exists(box_score_file):
                print(f"❌ Box score file not found: {box_score_file}")
                return False
            
            # Verify the file is readable and has data
            try:
                import pandas as pd
                df = pd.read_csv(box_score_file)
                if df.empty:
                    print(f"❌ Box score file is empty: {box_score_file}")
                    return False
                print(f"✅ Week {week} raw stats verified: {len(df)} players")
                return True
            except Exception as e:
                print(f"❌ Error reading box score file: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Error processing Week {week}: {e}")
            return False
    
    def build_master_dataset(self, force_refresh: bool = False) -> bool:
        """Build master dataset from all available weeks for raw stats analysis"""
        print("🏗️ Building master dataset...")
        
        # Check if master dataset is recent
        master_cache_file = f"{self.cache_dir}/master_dataset.pkl"
        if not force_refresh and os.path.exists(master_cache_file):
            cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(master_cache_file))
            if cache_age.days < 1:  # Less than 1 day old
                print("✅ Master dataset is recent, skipping rebuild")
                return True
        
        # Get all available weeks
        weeks = self.get_available_weeks()
        if not weeks:
            print("❌ No weeks available")
            return False
        
        # For raw stats analysis, we just verify all weeks have box score files
        # and create a simple summary
        valid_weeks = []
        for week in weeks:
            if self.is_week_data_complete(week):
                week_path = f"{self.data_dir}/WEEK{week}"
                box_score_file = f"{week_path}/box_score_debug.csv"
                if os.path.exists(box_score_file):
                    try:
                        import pandas as pd
                        df = pd.read_csv(box_score_file)
                        if not df.empty:
                            valid_weeks.append({
                                'week': week,
                                'player_count': len(df),
                                'path': week_path
                            })
                    except Exception as e:
                        print(f"⚠️ Error reading week {week}: {e}")
        
        if not valid_weeks:
            print("❌ No valid week data found")
            return False
        
        # Create a simple summary for raw stats
        summary = {
            'total_weeks': len(valid_weeks),
            'weeks': valid_weeks,
            'total_players': sum(w['player_count'] for w in valid_weeks),
            'created_at': datetime.now().isoformat()
        }
        
        # Save master dataset
        with open(master_cache_file, 'wb') as f:
            pickle.dump(summary, f)
        
        print(f"✅ Master dataset built from {len(valid_weeks)} weeks ({summary['total_players']} total players)")
        return True
    
    def get_master_dataset(self) -> Optional[Dict]:
        """Get the master dataset"""
        master_cache_file = f"{self.cache_dir}/master_dataset.pkl"
        
        if os.path.exists(master_cache_file):
            try:
                with open(master_cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"⚠️ Error loading master dataset: {e}")
        
        return None
    
    def update_optimizer_cache(self) -> bool:
        """Update the Player Prop Optimizer cache"""
        print("🔄 Updating optimizer cache...")
        
        try:
            # Build master dataset if needed
            if not self.build_master_dataset():
                return False
            
            # Initialize the enhanced data processor
            processor = EnhancedFootballDataProcessor()
            
            # Force update with fresh data
            processor.update_season_data(force_refresh=True)
            
            print("✅ Optimizer cache updated")
            return True
            
        except Exception as e:
            print(f"❌ Error updating optimizer cache: {e}")
            return False
    
    def get_data_summary(self) -> Dict:
        """Get comprehensive data summary"""
        weeks = self.get_available_weeks()
        status = self.get_week_data_status()
        master_data = self.get_master_dataset()
        
        complete_weeks = [w for w, s in status.items() if s['complete']]
        
        return {
            'total_weeks_available': len(weeks),
            'complete_weeks': len(complete_weeks),
            'weeks_with_data': complete_weeks,
            'master_dataset_available': master_data is not None,
            'cache_directory': self.cache_dir,
            'data_directory': self.data_dir,
            'last_updated': datetime.fromtimestamp(os.path.getmtime(f"{self.cache_dir}/master_dataset.pkl")).isoformat() if master_data else None
        }

def main():
    """Command line interface for data management"""
    parser = argparse.ArgumentParser(description='NFL Data Manager')
    parser.add_argument('--action', choices=['status', 'process', 'update', 'summary'], 
                       default='status', help='Action to perform')
    parser.add_argument('--week', type=int, help='Specific week to process')
    parser.add_argument('--force', action='store_true', help='Force refresh')
    
    args = parser.parse_args()
    
    manager = NFLDataManager()
    
    if args.action == 'status':
        print("📊 Data Status Report")
        print("=" * 40)
        
        weeks = manager.get_available_weeks()
        status = manager.get_week_data_status()
        
        print(f"Available weeks: {weeks}")
        print(f"Complete weeks: {[w for w, s in status.items() if s['complete']]}")
        
        for week, info in status.items():
            status_icon = "✅" if info['complete'] else "❌"
            print(f"{status_icon} Week {week}: {len(info['files'])} files")
    
    elif args.action == 'process':
        if args.week:
            success = manager.process_week_efficiently(args.week)
            print(f"Processing result: {'✅ Success' if success else '❌ Failed'}")
        else:
            print("Please specify --week for processing")
    
    elif args.action == 'update':
        success = manager.update_optimizer_cache()
        print(f"Update result: {'✅ Success' if success else '❌ Failed'}")
    
    elif args.action == 'summary':
        summary = manager.get_data_summary()
        print("📈 Data Summary")
        print("=" * 40)
        for key, value in summary.items():
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()
