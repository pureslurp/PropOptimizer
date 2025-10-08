#!/usr/bin/env python3
"""
Optimized Workflow for NFL Player Prop Optimizer
Handles the complete data pipeline from scraping to analysis
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from data_manager import NFLDataManager

def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def weekly_data_update(week: int, force_refresh: bool = False):
    """Complete weekly data update workflow"""
    print(f"📅 Weekly Data Update - Week {week}")
    print("=" * 50)
    
    manager = NFLDataManager()
    
    # Step 1: Create directory and scrape box scores
    print(f"\n📊 Step 1: Creating directory and scraping Week {week} box scores...")
    
    # Create the week directory first
    week_dir = f"2025/WEEK{week}"
    os.makedirs(week_dir, exist_ok=True)
    print(f"✅ Created directory: {week_dir}")
    
    scrape_cmd = f"python3 dfs_box_scores.py {week}"
    if not run_command(scrape_cmd, f"Week {week} box score scraping"):
        print("❌ Box score scraping failed. Check your setup.")
        return False
    
    # Step 2: Generate simplified team analysis (no DKSalaries needed)
    print(f"\n🎯 Step 2: Generating simplified team analysis...")
    analysis_cmd = f"python3 simple_box_score_processor.py --week {week}"
    if not run_command(analysis_cmd, f"Week {week} simplified analysis"):
        print("⚠️ Simplified analysis failed, but continuing...")
    
    # Step 3: Update data manager cache
    print(f"\n💾 Step 3: Updating data cache...")
    if not manager.process_week_efficiently(week):
        print("❌ Data processing failed")
        return False
    
    # Step 4: Update optimizer cache
    print(f"\n🔄 Step 4: Updating optimizer cache...")
    if not manager.update_optimizer_cache():
        print("❌ Optimizer cache update failed")
        return False
    
    # Step 5: Verify integration
    print(f"\n🧪 Step 5: Testing integration...")
    if not run_command("python3 test_integration.py", "Integration test"):
        print("⚠️ Integration test failed, but data should still work")
    
    print(f"\n🎉 Week {week} data update completed!")
    return True

def batch_weeks_update(weeks: list, force_refresh: bool = False):
    """Update multiple weeks at once"""
    print(f"📅 Batch Update - Weeks {weeks}")
    print("=" * 50)
    
    success_count = 0
    for week in weeks:
        if weekly_data_update(week, force_refresh):
            success_count += 1
        else:
            print(f"⚠️ Week {week} failed, continuing with remaining weeks...")
    
    print(f"\n📊 Batch update completed: {success_count}/{len(weeks)} weeks successful")
    return success_count == len(weeks)

def quick_refresh():
    """Quick refresh of existing data"""
    print("⚡ Quick Data Refresh")
    print("=" * 30)
    
    manager = NFLDataManager()
    
    # Just update the optimizer cache from existing data
    if manager.update_optimizer_cache():
        print("✅ Quick refresh completed")
        return True
    else:
        print("❌ Quick refresh failed")
        return False

def status_report():
    """Generate comprehensive status report"""
    print("📊 NFL Data Status Report")
    print("=" * 40)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    manager = NFLDataManager()
    summary = manager.get_data_summary()
    
    print(f"\n📁 Data Directory: {summary['data_directory']}")
    print(f"💾 Cache Directory: {summary['cache_directory']}")
    print(f"📅 Last Updated: {summary['last_updated'] or 'Never'}")
    
    print(f"\n📊 Week Status:")
    print(f"  Total weeks available: {summary['total_weeks_available']}")
    print(f"  Complete weeks: {summary['complete_weeks']}")
    print(f"  Weeks with data: {summary['weeks_with_data']}")
    
    print(f"\n🎯 Master Dataset: {'✅ Available' if summary['master_dataset_available'] else '❌ Not available'}")
    
    # Check if optimizer is ready
    print(f"\n🚀 Optimizer Status:")
    if summary['complete_weeks'] > 0 and summary['master_dataset_available']:
        print("  ✅ Ready to run: streamlit run player_prop_optimizer.py")
        print("  ✅ Ready to view: streamlit run data_viewer.py")
    else:
        print("  ❌ Not ready - need to run weekly update first")
        if summary['total_weeks_available'] == 0:
            print("     💡 Start with: python3 optimized_workflow.py --scrape 1")

def main():
    """Main workflow interface"""
    parser = argparse.ArgumentParser(description='Optimized NFL Data Workflow')
    
    # Action selection
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--scrape', type=int, metavar='WEEK', 
                            help='Scrape and process a specific week')
    action_group.add_argument('--batch', type=int, nargs='+', metavar='WEEK',
                            help='Scrape and process multiple weeks')
    action_group.add_argument('--refresh', action='store_true',
                            help='Quick refresh from existing data')
    action_group.add_argument('--status', action='store_true',
                            help='Show data status report')
    
    # Options
    parser.add_argument('--force', action='store_true',
                       help='Force refresh even if data exists')
    
    args = parser.parse_args()
    
    if args.scrape:
        success = weekly_data_update(args.scrape, args.force)
        sys.exit(0 if success else 1)
    
    elif args.batch:
        success = batch_weeks_update(args.batch, args.force)
        sys.exit(0 if success else 1)
    
    elif args.refresh:
        success = quick_refresh()
        sys.exit(0 if success else 1)
    
    elif args.status:
        status_report()
        sys.exit(0)

if __name__ == "__main__":
    main()
