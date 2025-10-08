# Using the Alternate Lines Feature

## Quick Start

The alternate lines feature is now automatically integrated into your Streamlit dashboard. When you run the app and view any stat type, you'll see additional rows marked with a "+" that represent alternate betting lines based on 70% threshold analysis.

## How to Use

### 1. Run the Dashboard
```bash
streamlit run player_prop_optimizer.py
```

### 2. Select a Stat Type
Choose from the dropdown at the top:
- Passing Yards ✅
- Rushing Yards ✅
- Receiving Yards ✅
- Receptions ✅
- Passing TDs ✅
- Rushing TDs ✅
- Receiving TDs ✅

**Note**: The system will fetch alternate lines in real-time when you select a stat type. You'll see a spinner: "Fetching alternate lines for {Stat Type}..."

### 3. View the Results
The table will show both standard and alternate lines:

```
Player           | Opp Team      | Team Rank | Score | Line    | Odds | Over Rate
──────────────────────────────────────────────────────────────────────────────────
Jalen Hurts      | NY Giants     | 24        | 72    | 199.5   | -106 | 80.0%
Jalen Hurts      | NY Giants     | 24        | 36    | 224.5+  | +178 | 40.0%
──────────────────────────────────────────────────────────────────────────────────
```

**Row 1** (Standard Line): Main betting line from FanDuel
- Line: 199.5 yards
- Odds: -106 (need to bet $106 to win $100)
- Over Rate: 80% (player went over this line in 4 of 5 recent games)

**Row 2** (Alternate Line - marked with "+"): Calculated 70% threshold line
- Line: 224.5+ yards (the "+" indicates this is an alternate line)
- Odds: +178 (bet $100 to win $178)
- Over Rate: 40% (player went over this line in 2 of 5 recent games)

### 4. Look for the Info Message
When alternate lines are added, you'll see:
```
✨ Added 3 alternate line recommendation(s) based on 70% threshold analysis
```

## Understanding the Alternate Lines

### What is the 70% Threshold?
The system analyzes each player's recent game history and calculates a line where they would go "over" approximately 70% of the time based on past performance.

**Example Calculation for Jalen Hurts:**
- Recent passing yards: 152, 101, 226, 130, 280
- System tests different thresholds:
  - At 101.5 yards: 80% over rate (4/5 games)
  - At 130.5 yards: 60% over rate (3/5 games)
  - At 152.5 yards: 40% over rate (2/5 games)
  - At 226.5 yards: 20% over rate (1/5 games)
- Best match for 70% target: 130.5 yards (60% is closest)
- System then finds the closest actual alternate line from FanDuel

### Why Use Alternate Lines?

1. **Value Hunting**: Alternate lines often offer better odds for slightly different targets
2. **Risk Management**: Choose lines based on your risk tolerance
3. **Data-Driven**: Uses actual player performance history, not gut feeling
4. **Consistency**: Applies the same 70% logic across all players

### Reading the Odds

- **Negative odds (e.g., -106)**: How much you bet to win $100
  - -106 means bet $106 to win $100
  - Lower risk, lower reward

- **Positive odds (e.g., +178)**: How much you win on a $100 bet
  - +178 means bet $100 to win $178
  - Higher risk, higher reward

## Real-Time Fetching

The system now **automatically fetches alternate lines in real-time** from The Odds API!

### How It Works

1. **Select Any Stat Type**: Just choose a stat type from the dropdown
2. **Automatic API Calls**: The system automatically makes API calls to fetch alternate lines
3. **Session Caching**: Results are cached during your session to avoid repeated API calls
4. **All Stats Supported**: Works for Passing Yards, Rushing Yards, Receiving Yards, Receptions, and all TD categories

### API Requirements

- **Requires**: Odds API plan with alternate player props access
- **Free Plans**: May not have access to alternate markets
- **Paid Plans**: Full access to all alternate markets

### Performance

- **First Load**: Takes ~2-5 seconds per stat type (fetches from API)
- **Subsequent Views**: Instant (uses cached data)
- **Rate Limiting**: Built-in 0.3 second delay between API calls

## Tips for Using Alternate Lines

### 1. Compare Over Rates
Look at both the standard line and alternate line over rates:
- **Standard: 80% over rate** = Player consistently beats this line (safer bet, lower odds)
- **Alternate: 40% over rate** = Riskier bet (higher odds, bigger payout)

### 2. Consider Matchups
The Team Rank column shows how good/bad the opponent's defense is:
- Lower rank (1-10) = tough defense
- Higher rank (20-32) = weak defense

Combine this with over rates for better decisions.

### 3. Look at the Score
The Score column factors in:
- Defensive matchup
- Player consistency
- Historical performance
- Line value

Higher scores = better overall opportunity

### 4. Grouped Display
Players are listed with their alternate line directly below the main line for easy comparison.

## Troubleshooting

### No Alternate Lines Showing
**Possible reasons:**
1. Your API plan doesn't include alternate markets
2. No alternate lines available for that stat type from FanDuel
3. Player not found in the alternate lines data (not featured this week)
4. Player doesn't have enough game history (need at least 1 game)
5. Network/API error during fetching

**Solution**: 
- Check your Odds API plan supports alternate player props
- Look for any error messages in the Streamlit interface
- Try refreshing the page (click the 🔄 Refresh button)

### Alternate Line Seems Off
**Possible reasons:**
1. Limited game sample size (early in season)
2. Player's performance is very inconsistent
3. Available alternate lines don't match calculated threshold well

**Note**: The system shows the CLOSEST alternate line, which may not perfectly match the calculated 70% threshold

### Wrong Over Rate Displayed
The over rate shown is based on the actual alternate line, not the calculated threshold:
- Calculated threshold: 141.5 yards (60% over rate)
- Closest alternate line: 149.5 yards (might have 40% over rate)
- Display shows: 40% (the rate for the actual 149.5 line)

This is intentional - it shows you the realistic over rate for the bet you'd actually make.

## Example Workflow

1. **Open Dashboard** → Select "Passing Yards"
2. **Review Table** → Look for players with both main and alternate lines
3. **Compare Lines** → Check over rates and odds
4. **Analyze Matchup** → Consider Team Rank and Score
5. **Make Decision** → Choose based on your risk tolerance

### Sample Analysis: Jalen Hurts vs Giants

```
Standard Line: 199.5 yards @ -106 odds (80% over rate)
- Safe bet, player beats this often
- Need to risk $106 to win $100
- Expected value: Good, but low payout

Alternate Line: 224.5 yards @ +178 odds (40% over rate)
- Riskier bet, player beats this less often
- Risk $100 to win $178
- Expected value: Higher reward, but only hits 40% of time

Decision: Depends on your strategy!
```

## Questions?

For technical details about implementation, see `ALTERNATE_LINES_FEATURE.md`

