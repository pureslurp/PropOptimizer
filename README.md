# Softball Lineup Generator

An intelligent lineup generator for softball teams that optimizes player assignments based on preferences, athleticism, and position importance.

## Features

- **Smart Player Assignment**: Uses global optimization to find the best overall lineup rather than making greedy local decisions
- **Player Preferences**: Respects player position preferences and restrictions
- **Athleticism Scoring**: Considers player athleticism and position importance for optimal assignments
- **Guest Player Support**: Add temporary players with custom preferences and athleticism ratings
- **Real-time Optimization**: Generates optimal lineups instantly using backtracking algorithms
- **Interactive Web Interface**: Built with Streamlit for easy use

## How It Works

The algorithm uses a sophisticated scoring system that considers:

1. **Player Preferences** (highest priority): Players get their preferred positions when possible
2. **Athleticism × Position Importance**: More athletic players get more important positions
3. **Global Optimization**: Finds the best overall team assignment rather than making local decisions

### Position Importance

**Infield Positions:**
- SS: 6 (highest action)
- 3B: 5
- 2B: 4
- 1B: 3
- P: 2
- C: 1 (lowest action)

**Outfield Positions:**
- LCF: 4 (most action)
- RCF: 3
- LF: 2
- RF: 1 (least action)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/softball-lineup-generator.git
cd softball-lineup-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run softball.py
```

## Usage

1. **Player Availability**: Check/uncheck players in the sidebar to mark them as available
2. **Guest Players**: Add up to 5 guest players with custom names, preferences, and athleticism ratings
3. **Generate Lineup**: The app automatically generates the optimal lineup based on available players
4. **View Details**: Use the checkboxes to see detailed scoring information and candidate analysis

## Player Configuration

Players are configured with:
- **Preferences**: Preferred positions (e.g., `["P", "SS"]`)
- **Restrictions**: Positions they cannot play (e.g., `["P", "3B"]`)
- **Athleticism**: Rating from 1-10 indicating overall athletic ability

## Algorithm Details

The generator uses a backtracking algorithm that:
1. Explores all possible player-to-position assignments
2. Calculates total lineup score for each combination
3. Returns the assignment with the highest overall score
4. Applies post-optimization swaps to improve team athleticism

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Uses global optimization techniques for optimal lineup generation 