# NFL Player Prop Optimizer

A comprehensive Streamlit application for analyzing NFL player props using matchup data and player history. This tool helps identify the best player prop opportunities based on defensive matchups and player performance trends.

## Features

- **Real-time Odds Integration**: Fetches player prop odds from The Odds API (FanDuel prioritized)
- **Advanced Scoring Model**: Combines matchup data, player history, and betting value
- **Interactive Dashboard**: Filter by stat type, score threshold, and confidence level
- **Comprehensive Analysis**: Provides detailed breakdowns of scoring factors
- **Top Recommendations**: Highlights the best opportunities with detailed metrics
- **FanDuel Focus**: Prioritizes FanDuel odds for consistent data and better player prop coverage

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. **Get an API Key**: Sign up at [The Odds API](https://the-odds-api.com/) to get your free API key
2. **Configure API Key**: Edit `config.py` and replace `YOUR_API_KEY_HERE` with your actual API key
3. **Run the Application**: 
   ```bash
   streamlit run player_prop_optimizer.py
   ```

## Usage

### Main Interface

1. **Select Stat Type**: Choose from:
   - Passing Yards
   - Passing TDs
   - Rushing Yards
   - Rushing TDs
   - Receptions
   - Receiving Yards
   - Receiving TDs

2. **Apply Filters**:
   - **Minimum Score**: Filter results by score threshold (0-100)
   - **Confidence Level**: Filter by High/Medium/Low confidence predictions

3. **View Results**: The dashboard displays:
   - Player name and opposing team
   - Team defensive ranking
   - Overall score (0-100)
   - Line and odds
   - Confidence level
   - Historical over rate
   - Analysis summary

### Understanding the Scores

The scoring system combines four key factors:

1. **Matchup Score (35%)**: Based on opposing team's defensive ranking
2. **Player History Score (30%)**: Based on player's historical performance vs. the line
3. **Consistency Score (20%)**: Based on player's performance consistency
4. **Value Score (15%)**: Based on betting value (odds vs. probability)

**Score Interpretation**:
- 80-100: 🔥 Excellent opportunity
- 70-79: ✅ Strong play
- 60-69: 👍 Good value
- 50-59: ⚖️ Neutral
- 0-49: ❌ Avoid

### Top Recommendations

The app highlights the top 5 recommendations with detailed breakdowns including:
- Individual score components
- Team defensive ranking
- Player's historical over rate
- Confidence level
- Betting odds

## Data Sources

- **Odds Data**: The Odds API for real-time player prop odds
- **Matchup Data**: Real ESPN defensive statistics
- **Player History**: Actual player performance data from box scores

## File Structure

```
PropOptimizer/
├── player_prop_optimizer.py    # Main Streamlit application
├── enhanced_data_processor.py  # Real data processing
├── scoring_model.py           # Advanced scoring algorithms
├── espn_defensive_scraper.py  # ESPN defensive data scraping
├── dfs_box_scores.py          # Box score scraping
├── optimized_workflow.py      # Data workflow orchestrator
├── utils.py                   # Utility functions
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Customization

### Adding New Stat Types

To add new stat types, update the `stat_types` list in the main application and add corresponding mappings in the `OddsAPI.parse_player_props()` method.

### Modifying Scoring Weights

Adjust the scoring weights in `scoring_model.py`:
```python
weights = {
    'matchup': 0.35,      # Team defensive ranking
    'player_history': 0.30, # Player historical performance
    'consistency': 0.20,   # Player consistency
    'value': 0.15         # Betting value
}
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your API key is valid and has sufficient credits
2. **No Data**: Check your internet connection and API key validity
3. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

### Performance Tips

- The app caches data between refreshes to improve performance
- Use filters to narrow down results for faster processing
- Consider running during off-peak hours for better API response times

## Future Enhancements

- **Real-time Data Integration**: Connect to live NFL data feeds
- **Machine Learning Models**: Implement ML-based predictions
- **Historical Analysis**: Add multi-season trend analysis
- **Export Functionality**: Export recommendations to CSV/Excel
- **Mobile Optimization**: Improve mobile device compatibility

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your API key and internet connection
3. Ensure all dependencies are properly installed

## License

This project is for educational and personal use. Please ensure compliance with The Odds API terms of service and any applicable gambling regulations in your jurisdiction.
