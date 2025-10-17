#!/usr/bin/env python3
"""
Validation script to test position-specific defensive rankings against CBS Sports data.

This script compares our calculated defensive stats with known values from CBS Sports
to ensure our system is working correctly.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from position_defensive_ranks import PositionDefensiveRankings
import time
import random

class PositionRankingsValidator:
    def __init__(self):
        self.position_defensive_ranks = PositionDefensiveRankings()
        self.position_defensive_ranks.calculate_position_defensive_stats(max_week=6)
        
        # CBS Sports team abbreviations mapping
        self.team_abbreviations = {
            'DET': 'Detroit Lions',
            'PIT': 'Pittsburgh Steelers', 
            'CIN': 'Cincinnati Bengals',
            'CLE': 'Cleveland Browns',
            'CHI': 'Chicago Bears',
            'GB': 'Green Bay Packers',
            'BAL': 'Baltimore Ravens',
            'KC': 'Kansas City Chiefs',
            'SF': 'San Francisco 49ers',
            'SEA': 'Seattle Seahawks',
            'PHI': 'Philadelphia Eagles',
            'DAL': 'Dallas Cowboys',
            'NYG': 'New York Giants',
            'NYJ': 'New York Jets',
            'NE': 'New England Patriots',
            'BUF': 'Buffalo Bills',
            'MIA': 'Miami Dolphins',
            'IND': 'Indianapolis Colts',
            'JAX': 'Jacksonville Jaguars',
            'TEN': 'Tennessee Titans',
            'HOU': 'Houston Texans',
            'DEN': 'Denver Broncos',
            'LV': 'Las Vegas Raiders',
            'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams',
            'ARI': 'Arizona Cardinals',
            'ATL': 'Atlanta Falcons',
            'CAR': 'Carolina Panthers',
            'NO': 'New Orleans Saints',
            'TB': 'Tampa Bay Buccaneers',
            'MIN': 'Minnesota Vikings',
            'WAS': 'Washington Commanders'
        }
        
        # Position abbreviations for CBS Sports URLs
        self.position_abbreviations = {
            'RB': 'RB',
            'WR': 'WR', 
            'TE': 'TE',
            'QB': 'QB'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_cbs_sports_data(self, position, team_abbrev):
        """Scrape defensive stats from CBS Sports for a specific position vs team"""
        url = f"https://www.cbssports.com/fantasy/football/stats/posvsdef/{position}/{team_abbrev}/teambreakdown/standard"
        
        try:
            print(f"Fetching CBS Sports data: {position} vs {team_abbrev}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with defensive stats
            table = soup.find('table', class_='data compact')
            if not table:
                print(f"  ❌ No table found for {position} vs {team_abbrev}")
                return None
            
            # Extract season totals from the "Season" row
            season_row = None
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2 and cells[0].get_text().strip() == 'Season':
                    season_row = cells
                    break
            
            if not season_row:
                print(f"  ❌ No season totals found for {position} vs {team_abbrev}")
                return None
            
            # Parse the season totals
            stats = {}
            if len(season_row) >= 13:  # Ensure we have enough columns
                stats = {
                    'rushing_attempts': int(season_row[2].get_text().strip()) if season_row[2].get_text().strip() else 0,
                    'rushing_yards': int(season_row[3].get_text().strip()) if season_row[3].get_text().strip() else 0,
                    'rushing_tds': int(season_row[5].get_text().strip()) if season_row[5].get_text().strip() else 0,
                    'receiving_targets': int(season_row[6].get_text().strip()) if season_row[6].get_text().strip() else 0,
                    'receiving_receptions': int(season_row[7].get_text().strip()) if season_row[7].get_text().strip() else 0,
                    'receiving_yards': int(season_row[8].get_text().strip()) if season_row[8].get_text().strip() else 0,
                    'receiving_tds': int(season_row[10].get_text().strip()) if season_row[10].get_text().strip() else 0
                }
            
            print(f"  ✅ CBS Sports data retrieved: {stats}")
            return stats
            
        except Exception as e:
            print(f"  ❌ Error fetching CBS Sports data: {e}")
            return None

    def get_our_data(self, team_name, position, stat_type):
        """Get our calculated defensive stats"""
        try:
            # Get the defensive rank
            rank = self.position_defensive_ranks.get_position_defensive_rank(team_name, 'Test Player', stat_type)
            
            # Get the raw defensive stats
            team_stats = self.position_defensive_ranks.position_defensive_stats.get(team_name, {})
            
            # Map stat types to our internal keys
            stat_mapping = {
                'Rushing Yards': f'{position}_Rushing_Yards_Allowed',
                'Rushing TDs': f'{position}_Rushing_TDs_Allowed',
                'Receiving Yards': f'{position}_Receiving_Yards_Allowed',
                'Receiving TDs': f'{position}_Receiving_TDs_Allowed',
                'Receptions': f'{position}_Receptions_Allowed'
            }
            
            stat_key = stat_mapping.get(stat_type)
            if stat_key and stat_key in team_stats:
                return {
                    'rank': rank,
                    'total_yards': team_stats[stat_key],
                    'games_played': team_stats.get('Games_Played', 0),
                    'per_game': team_stats[stat_key] / team_stats.get('Games_Played', 1) if team_stats.get('Games_Played', 0) > 0 else 0
                }
            else:
                return None
                
        except Exception as e:
            print(f"  ❌ Error getting our data: {e}")
            return None

    def validate_team_position(self, team_abbrev, position):
        """Validate defensive stats for a specific team and position"""
        team_name = self.team_abbreviations.get(team_abbrev)
        if not team_name:
            print(f"❌ Unknown team abbreviation: {team_abbrev}")
            return False
        
        print(f"\n=== VALIDATING {position} vs {team_name} ({team_abbrev}) ===")
        
        # Get CBS Sports data
        cbs_data = self.get_cbs_sports_data(position, team_abbrev)
        if not cbs_data:
            return False
        
        # Get our data
        our_data = {}
        stat_types = ['Rushing Yards', 'Rushing TDs', 'Receiving Yards', 'Receiving TDs']
        
        for stat_type in stat_types:
            our_data[stat_type] = self.get_our_data(team_name, position, stat_type)
        
        # Compare the data
        results = {}
        
        # Compare rushing yards
        cbs_rushing_yards = cbs_data.get('rushing_yards', 0)
        our_rushing_data = our_data.get('Rushing Yards')
        if our_rushing_data:
            our_rushing_yards = our_rushing_data['total_yards']
            rushing_match = abs(cbs_rushing_yards - our_rushing_yards) <= 1  # Allow 1 yard difference for rounding
            results['rushing_yards'] = {
                'cbs': cbs_rushing_yards,
                'ours': our_rushing_yards,
                'match': rushing_match,
                'our_rank': our_rushing_data['rank'],
                'our_per_game': our_rushing_data['per_game']
            }
            print(f"Rushing Yards: CBS={cbs_rushing_yards}, Ours={our_rushing_yards}, Match={rushing_match}")
        
        # Compare receiving yards  
        cbs_receiving_yards = cbs_data.get('receiving_yards', 0)
        our_receiving_data = our_data.get('Receiving Yards')
        if our_receiving_data:
            our_receiving_yards = our_receiving_data['total_yards']
            receiving_match = abs(cbs_receiving_yards - our_receiving_yards) <= 1
            results['receiving_yards'] = {
                'cbs': cbs_receiving_yards,
                'ours': our_receiving_yards,
                'match': receiving_match,
                'our_rank': our_receiving_data['rank'],
                'our_per_game': our_receiving_data['per_game']
            }
            print(f"Receiving Yards: CBS={cbs_receiving_yards}, Ours={our_receiving_yards}, Match={receiving_match}")
        
        return results

    def run_validation_tests(self):
        """Run validation tests for multiple teams and positions"""
        print("🏈 POSITION-SPECIFIC DEFENSIVE RANKINGS VALIDATION")
        print("=" * 60)
        
        # Test cases: (team_abbrev, position)
        test_cases = [
            ('GB', 'RB'),   # Green Bay Packers vs RBs
            ('BUF', 'WR'),  # Buffalo Bills vs WRs
            ('KC', 'TE'),   # Kansas City Chiefs vs TEs
            ('PHI', 'RB'),  # Philadelphia Eagles vs RBs
            ('LAR', 'WR'),  # Los Angeles Rams vs WRs
        ]
        
        all_results = {}
        
        for team_abbrev, position in test_cases:
            try:
                results = self.validate_team_position(team_abbrev, position)
                all_results[f"{team_abbrev}_{position}"] = results
                
                # Add delay to be respectful to CBS Sports
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"❌ Error validating {team_abbrev} {position}: {e}")
                all_results[f"{team_abbrev}_{position}"] = None
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, results in all_results.items():
            if results:
                print(f"\n{test_name}:")
                for stat_type, data in results.items():
                    if isinstance(data, dict) and 'match' in data:
                        total_tests += 1
                        if data['match']:
                            passed_tests += 1
                            print(f"  ✅ {stat_type}: CBS={data['cbs']}, Ours={data['ours']}, Rank={data['our_rank']}")
                        else:
                            print(f"  ❌ {stat_type}: CBS={data['cbs']}, Ours={data['ours']}, Rank={data['our_rank']}")
            else:
                print(f"\n{test_name}: ❌ FAILED TO VALIDATE")
        
        print(f"\n🎯 VALIDATION RESULTS: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Our system is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the discrepancies above.")
        
        return all_results

def main():
    """Main function to run the validation tests"""
    validator = PositionRankingsValidator()
    results = validator.run_validation_tests()
    
    # Save results to file for further analysis
    with open('validation_results.txt', 'w') as f:
        f.write("Position-Specific Defensive Rankings Validation Results\n")
        f.write("=" * 60 + "\n\n")
        
        for test_name, test_results in results.items():
            f.write(f"{test_name}:\n")
            if test_results:
                for stat_type, data in test_results.items():
                    if isinstance(data, dict):
                        f.write(f"  {stat_type}: CBS={data.get('cbs', 'N/A')}, Ours={data.get('ours', 'N/A')}, Match={data.get('match', False)}\n")
            else:
                f.write("  FAILED TO VALIDATE\n")
            f.write("\n")
    
    print("\n📄 Results saved to validation_results.txt")

if __name__ == "__main__":
    main()
