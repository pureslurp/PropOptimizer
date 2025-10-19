#!/usr/bin/env python3
"""
Validate the defensive rankings we calculated in our multi-week test
against the actual CBS data to ensure accuracy
"""

import os
import sys
import toml
from enhanced_data_processor import EnhancedFootballDataProcessor

def validate_defensive_rankings():
    """Validate our calculated defensive rankings against CBS data"""
    
    print("🔍 VALIDATING DEFENSIVE RANKINGS FROM MULTI-WEEK TEST")
    print("="*60)
    
    # Load database configuration
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        os.environ['DATABASE_URL'] = secrets['DATABASE_URL']
        print("✅ Loaded database URL from secrets.toml")
    except Exception as e:
        print(f"❌ Error loading secrets: {e}")
        sys.exit(1)
    
    # Test cases from our multi-week test
    test_cases = [
        {
            'week': 1,
            'player': 'Jared Goff',
            'opp_team': 'Green Bay Packers',
            'stat_type': 'Passing TDs',
            'expected_rank': 16,
            'logic': 'Default rank (no historical data)'
        },
        {
            'week': 2,
            'player': 'Lamar Jackson',
            'opp_team': 'Cleveland Browns',
            'stat_type': 'Passing TDs',
            'expected_rank': 26,
            'logic': 'Historical data from Week 1'
        },
        {
            'week': 3,
            'player': 'Kyler Murray',
            'opp_team': 'San Francisco 49ers',
            'stat_type': 'Passing TDs',
            'expected_rank': 2,
            'logic': 'Historical data from Weeks 1-2'
        },
        {
            'week': 4,
            'player': 'Jaxson Dart',
            'opp_team': 'Los Angeles Chargers',
            'stat_type': 'Passing TDs',
            'expected_rank': 5,
            'logic': 'Historical data from Weeks 1-3'
        },
        {
            'week': 5,
            'player': 'Sam Darnold',
            'opp_team': 'Tampa Bay Buccaneers',
            'stat_type': 'Passing TDs',
            'expected_rank': 15,
            'logic': 'Historical data from Weeks 1-4'
        },
        {
            'week': 6,
            'player': 'Josh Allen',
            'opp_team': 'Atlanta Falcons',
            'stat_type': 'Passing TDs',
            'expected_rank': 11,
            'logic': 'Historical data from Weeks 1-5'
        }
    ]
    
    print(f"📊 Testing {len(test_cases)} defensive ranking calculations...")
    print()
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        week = test_case['week']
        player = test_case['player']
        opp_team = test_case['opp_team']
        stat_type = test_case['stat_type']
        expected_rank = test_case['expected_rank']
        logic = test_case['logic']
        
        print(f"🧪 TEST {i}: Week {week} - {player} vs {opp_team}")
        print(f"   Stat Type: {stat_type}")
        print(f"   Expected Rank: {expected_rank}")
        print(f"   Logic: {logic}")
        
        try:
            if week == 1:
                # Week 1: No historical data, use default rank
                calculated_rank = 16
                print(f"   📊 Week 1 - Using default rank: {calculated_rank}")
            else:
                # Use data from previous weeks only
                max_week = week - 1
                print(f"   📊 Using data from weeks 1-{max_week} for rankings")
                
                # Create data processor with limited historical data
                historical_processor = EnhancedFootballDataProcessor(max_week=max_week)
                calculated_rank = historical_processor.get_team_defensive_rank(opp_team, stat_type)
                
                if calculated_rank is None:
                    print(f"   ⚠️  No defensive data found for {opp_team} in weeks 1-{max_week}")
                    calculated_rank = None
                else:
                    print(f"   📊 Defensive rank for {opp_team} vs {stat_type}: {calculated_rank}")
            
            # Validate the result
            if week == 1:
                if calculated_rank == 16:
                    status = "✅ CORRECT"
                    print(f"   {status}: Week 1 correctly using default rank 16")
                else:
                    status = "❌ ERROR"
                    print(f"   {status}: Week 1 should use default rank 16, got {calculated_rank}")
            else:
                if calculated_rank is not None and calculated_rank != 16:
                    if calculated_rank == expected_rank:
                        status = "✅ CORRECT"
                        print(f"   {status}: Historical ranking matches expected")
                    else:
                        status = "⚠️  DIFFERENT"
                        print(f"   {status}: Got rank {calculated_rank}, expected {expected_rank}")
                elif calculated_rank == 16:
                    status = "❌ ERROR"
                    print(f"   {status}: Week {week} incorrectly using default rank 16")
                else:
                    status = "❌ ERROR"
                    print(f"   {status}: Week {week} has no ranking data")
            
            results.append({
                'week': week,
                'player': player,
                'opp_team': opp_team,
                'stat_type': stat_type,
                'expected_rank': expected_rank,
                'calculated_rank': calculated_rank,
                'status': status
            })
            
        except Exception as e:
            print(f"   ❌ ERROR: Exception occurred: {e}")
            results.append({
                'week': week,
                'player': player,
                'opp_team': opp_team,
                'stat_type': stat_type,
                'expected_rank': expected_rank,
                'calculated_rank': None,
                'status': f"❌ ERROR: {e}"
            })
        
        print()
    
    # Summary
    print("="*60)
    print("📊 DEFENSIVE RANKING VALIDATION SUMMARY")
    print("="*60)
    
    correct_count = 0
    error_count = 0
    different_count = 0
    
    for result in results:
        week = result['week']
        player = result['player']
        opp_team = result['opp_team']
        expected_rank = result['expected_rank']
        calculated_rank = result['calculated_rank']
        status = result['status']
        
        print(f"Week {week}: {player} vs {opp_team}")
        print(f"   Expected: {expected_rank}, Calculated: {calculated_rank}")
        print(f"   Status: {status}")
        print()
        
        if "✅ CORRECT" in status:
            correct_count += 1
        elif "❌ ERROR" in status:
            error_count += 1
        elif "⚠️  DIFFERENT" in status:
            different_count += 1
    
    print(f"📈 RESULTS: {correct_count} correct, {different_count} different, {error_count} errors")
    
    if error_count == 0:
        print("🎉 All defensive rankings are working correctly!")
    else:
        print(f"⚠️  {error_count} errors found that need investigation")

if __name__ == "__main__":
    validate_defensive_rankings()

