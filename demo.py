"""
Demo script for the NFL Player Prop Optimizer
This script demonstrates the core functionality without requiring an API key
"""

import pandas as pd
from data_processor import FootballDataProcessor
from scoring_model import AdvancedPropScorer

def demo_scoring():
    """Demonstrate the scoring system with sample data"""
    print("🏈 NFL Player Prop Optimizer - Demo")
    print("=" * 50)
    
    # Initialize components
    data_processor = FootballDataProcessor()
    scorer = AdvancedPropScorer(data_processor)
    
    # Sample player props for demonstration
    sample_props = [
        {
            'Player': 'Josh Allen',
            'Opposing Team': 'New York Jets',
            'Stat Type': 'Passing Yards',
            'Line': 275.5,
            'Odds': -110
        },
        {
            'Player': 'Christian McCaffrey',
            'Opposing Team': 'Arizona Cardinals',
            'Stat Type': 'Rushing Yards',
            'Line': 95.5,
            'Odds': -105
        },
        {
            'Player': 'Cooper Kupp',
            'Opposing Team': 'San Francisco 49ers',
            'Stat Type': 'Receiving Yards',
            'Line': 85.5,
            'Odds': -115
        },
        {
            'Player': 'Lamar Jackson',
            'Opposing Team': 'Denver Broncos',
            'Stat Type': 'Rushing Yards',
            'Line': 65.5,
            'Odds': -110
        },
        {
            'Player': 'Travis Kelce',
            'Opposing Team': 'Buffalo Bills',
            'Stat Type': 'Receptions',
            'Line': 6.5,
            'Odds': -120
        }
    ]
    
    print("Analyzing sample player props...")
    print()
    
    # Calculate scores for each prop
    results = []
    for prop in sample_props:
        score_data = scorer.calculate_comprehensive_score(
            prop['Player'],
            prop['Opposing Team'],
            prop['Stat Type'],
            prop['Line'],
            prop['Odds']
        )
        
        results.append({
            'Player': prop['Player'],
            'Opposing Team': prop['Opposing Team'],
            'Stat Type': prop['Stat Type'],
            'Line': prop['Line'],
            'Odds': prop['Odds'],
            'Score': score_data['total_score'],
            'Confidence': score_data['confidence'],
            'Over Rate': f"{score_data['over_rate']*100:.1f}%",
            'Team Rank': score_data['team_rank'],
            'Analysis': score_data['analysis']
        })
    
    # Create DataFrame and display results
    df = pd.DataFrame(results)
    df = df.sort_values('Score', ascending=False)
    
    print("📊 Results Summary:")
    print("-" * 50)
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        print(f"{i}. {row['Player']} vs {row['Opposing Team']}")
        print(f"   {row['Stat Type']}: {row['Line']} (Odds: {row['Odds']})")
        print(f"   Score: {row['Score']} | Confidence: {row['Confidence']}")
        print(f"   Over Rate: {row['Over Rate']} | Team Rank: {row['Team Rank']}")
        print(f"   Analysis: {row['Analysis']}")
        print()
    
    # Summary statistics
    print("📈 Summary Statistics:")
    print(f"Average Score: {df['Score'].mean():.1f}")
    print(f"High Score Props (70+): {len(df[df['Score'] >= 70])}")
    print(f"High Confidence Props: {len(df[df['Confidence'] == 'High'])}")
    
    print("\n🎯 Top Recommendation:")
    top_prop = df.iloc[0]
    print(f"Best Play: {top_prop['Player']} {top_prop['Stat Type']} {top_prop['Line']}")
    print(f"Score: {top_prop['Score']} | Confidence: {top_prop['Confidence']}")
    print(f"Analysis: {top_prop['Analysis']}")

if __name__ == "__main__":
    demo_scoring()
