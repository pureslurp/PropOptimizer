"""
Advanced scoring model for Player Prop Optimizer
Implements sophisticated algorithms based on matchup data and player history
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from enhanced_data_processor import EnhancedFootballDataProcessor

class AdvancedPropScorer:
    """Advanced scoring model for player props"""
    
    def __init__(self, data_processor: EnhancedFootballDataProcessor):
        self.data_processor = data_processor
        
    def calculate_comprehensive_score(self, 
                                    player: str, 
                                    opposing_team: str, 
                                    stat_type: str, 
                                    line: float,
                                    odds: float = 0) -> Dict:
        """
        Calculate a comprehensive score for a player prop
        
        Args:
            player: Player name
            opposing_team: Opposing team name
            stat_type: Type of stat (e.g., "Passing Yards")
            line: The line to beat
            odds: American odds format
            
        Returns:
            Dictionary with score breakdown and analysis
        """
        # Get team defensive ranking
        # Map receiving yards to passing yards since they're the same defensive stat
        defense_stat_type = f"{stat_type} Allowed"
        if stat_type == "Receiving Yards":
            defense_stat_type = "Passing Yards Allowed"
        
        team_rank = self.data_processor.get_team_defensive_rank(opposing_team, defense_stat_type)
        
        # Get player statistics
        over_rate = self.data_processor.get_player_over_rate(player, stat_type, line)
        player_avg = self.data_processor.get_player_average(player, stat_type)
        player_consistency = self.data_processor.get_player_consistency(player, stat_type)
        
        # Calculate different score components
        matchup_score = self._calculate_matchup_score(team_rank, stat_type)
        player_history_score = self._calculate_player_history_score(over_rate, player_avg, line)
        consistency_score = self._calculate_consistency_score(player_consistency, player_avg)
        value_score = self._calculate_value_score(over_rate, odds) if odds != 0 else 50
        
        # Weighted combination of scores
        weights = {
            'matchup': 0.35,      # 35% - How good/bad the matchup is
            'player_history': 0.30, # 30% - Player's historical performance
            'consistency': 0.20,   # 20% - Player's consistency
            'value': 0.15         # 15% - Betting value
        }
        
        total_score = (
            weights['matchup'] * matchup_score +
            weights['player_history'] * player_history_score +
            weights['consistency'] * consistency_score +
            weights['value'] * value_score
        )
        
        # Calculate confidence level
        confidence = self._calculate_confidence(over_rate, player_consistency, team_rank)
        
        return {
            'total_score': int(total_score),
            'matchup_score': int(matchup_score),
            'player_history_score': int(player_history_score),
            'consistency_score': int(consistency_score),
            'value_score': int(value_score),
            'confidence': confidence,
            'team_rank': team_rank,
            'over_rate': over_rate,
            'player_avg': player_avg,
            'player_consistency': player_consistency,
            'line_vs_avg': line - player_avg,
            'analysis': self._generate_analysis(player, opposing_team, stat_type, line, total_score, confidence)
        }
    
    def _calculate_matchup_score(self, team_rank: int, stat_type: str) -> float:
        """Calculate score based on defensive matchup"""
        # Lower rank = better defense = lower score
        # Scale from 0-100 where 100 is worst defense (best matchup)
        max_rank = 32
        score = ((max_rank - team_rank + 1) / max_rank) * 100
        
        # Adjust based on stat type sensitivity
        if stat_type in ['Passing Yards', 'Receiving Yards']:
            # These stats are more sensitive to defensive rankings
            return score
        elif stat_type in ['Rushing Yards']:
            # Rushing is moderately sensitive
            return score * 0.9
        else:
            # TD stats are less predictable
            return score * 0.8
    
    def _calculate_player_history_score(self, over_rate: float, player_avg: float, line: float) -> float:
        """Calculate score based on player's historical performance"""
        # Base score from over rate (0-100)
        base_score = over_rate * 100
        
        # Adjust based on how the line compares to player average
        if player_avg > 0:
            line_ratio = line / player_avg
            if line_ratio < 0.8:  # Line is much lower than average
                adjustment = 20
            elif line_ratio < 1.0:  # Line is lower than average
                adjustment = 10
            elif line_ratio < 1.2:  # Line is close to average
                adjustment = 0
            else:  # Line is higher than average
                adjustment = -20
        else:
            adjustment = 0
        
        return max(0, min(100, base_score + adjustment))
    
    def _calculate_consistency_score(self, consistency: float, player_avg: float) -> float:
        """Calculate score based on player consistency"""
        if player_avg == 0:
            return 50  # Default middle score
        
        # Lower consistency (standard deviation) = higher score
        # Normalize consistency relative to average
        normalized_consistency = consistency / player_avg if player_avg > 0 else 1.0
        
        # Score decreases as consistency gets worse
        if normalized_consistency < 0.1:  # Very consistent
            return 90
        elif normalized_consistency < 0.2:  # Consistent
            return 80
        elif normalized_consistency < 0.3:  # Moderately consistent
            return 70
        elif normalized_consistency < 0.5:  # Somewhat inconsistent
            return 60
        else:  # Very inconsistent
            return 40
    
    def _calculate_value_score(self, over_rate: float, odds: float) -> float:
        """Calculate betting value score"""
        if odds == 0:
            return 50  # Default middle score
        
        # Convert American odds to implied probability
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)
        
        # Calculate value (positive expected value = good value)
        expected_value = (over_rate * (1 / implied_prob - 1)) - ((1 - over_rate) * 1)
        
        # Convert to 0-100 score
        if expected_value > 0.2:  # Very good value
            return 90
        elif expected_value > 0.1:  # Good value
            return 80
        elif expected_value > 0.05:  # Decent value
            return 70
        elif expected_value > 0:  # Slight value
            return 60
        elif expected_value > -0.05:  # Fair value
            return 50
        else:  # Poor value
            return 30
    
    def _calculate_confidence(self, over_rate: float, consistency: float, team_rank: int) -> str:
        """Calculate confidence level for the prediction"""
        # Factors that increase confidence
        confidence_factors = []
        
        if over_rate >= 0.7 or over_rate <= 0.3:  # Clear trend
            confidence_factors.append(1)
        
        if team_rank <= 5 or team_rank >= 28:  # Clear defensive strength/weakness
            confidence_factors.append(1)
        
        if consistency < 20:  # Player is consistent
            confidence_factors.append(1)
        
        confidence_score = sum(confidence_factors)
        
        if confidence_score >= 3:
            return "High"
        elif confidence_score >= 2:
            return "Medium"
        else:
            return "Low"
    
    def _generate_analysis(self, player: str, opposing_team: str, stat_type: str, 
                          line: float, score: float, confidence: str) -> str:
        """Generate human-readable analysis"""
        analysis_parts = []
        
        # Score interpretation
        if score >= 80:
            analysis_parts.append(f"🔥 Excellent opportunity - Score: {score}")
        elif score >= 70:
            analysis_parts.append(f"✅ Strong play - Score: {score}")
        elif score >= 60:
            analysis_parts.append(f"👍 Good value - Score: {score}")
        elif score >= 50:
            analysis_parts.append(f"⚖️ Neutral - Score: {score}")
        else:
            analysis_parts.append(f"❌ Avoid - Score: {score}")
        
        # Confidence level
        if confidence == "High":
            analysis_parts.append("High confidence prediction")
        elif confidence == "Medium":
            analysis_parts.append("Medium confidence prediction")
        else:
            analysis_parts.append("Low confidence - consider other factors")
        
        return " | ".join(analysis_parts)
    
    def get_recommendations(self, props_data: List[Dict]) -> List[Dict]:
        """Get top recommendations from a list of props"""
        scored_props = []
        
        for prop in props_data:
            score_data = self.calculate_comprehensive_score(
                prop['Player'],
                prop['Opposing Team'],
                prop['Stat Type'],
                prop['Line'],
                prop.get('Odds', 0)
            )
            
            scored_prop = {**prop, **score_data}
            scored_props.append(scored_prop)
        
        # Sort by total score and confidence
        scored_props.sort(key=lambda x: (x['total_score'], x['confidence'] == 'High'), reverse=True)
        
        return scored_props
