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
        # Pass the base stat type - get_team_defensive_rank will handle the conversion
        team_rank = self.data_processor.get_team_defensive_rank(opposing_team, stat_type)
        
        # Get player's team and determine home/away status
        player_team = self.data_processor.get_player_team(player)
        week = self.data_processor.get_week_from_matchup(player_team, opposing_team)
        is_home = self.data_processor.is_home_game(player_team, week) if week else None
        
        # Get player statistics
        season_over_rate = self.data_processor.get_player_over_rate(player, stat_type, line)
        l5_over_rate = self.data_processor.get_player_last_n_over_rate(player, stat_type, line, n=5)
        home_over_rate = self.data_processor.get_player_home_over_rate(player, stat_type, line)
        away_over_rate = self.data_processor.get_player_away_over_rate(player, stat_type, line)
        
        # Use location-specific over rate based on home/away status
        if is_home:
            loc_over_rate = home_over_rate
        else:
            loc_over_rate = away_over_rate
        
        player_avg = self.data_processor.get_player_average(player, stat_type)
        player_consistency = self.data_processor.get_player_consistency(player, stat_type)
        player_streak = self.data_processor.get_player_streak(player, stat_type, line)
        
        # Calculate different score components
        matchup_score = self._calculate_matchup_score(team_rank, stat_type)
        player_history_score = self._calculate_player_history_score(season_over_rate, loc_over_rate, l5_over_rate, player_streak, line)
        consistency_score = self._calculate_consistency_score(player_consistency, player_avg)
        value_score = self._calculate_value_score(season_over_rate, odds) if odds != 0 else 50
        
        # Weighted combination of scores
        weights = {
            'matchup': 0.33,      # 35% - How good/bad the matchup is
            'player_history': 0.33, # 30% - Player's historical performance
            'value': 0.33, # 30% - Betting value
        }
        
        total_score = (
            weights['matchup'] * matchup_score +
            weights['player_history'] * player_history_score +
            weights['value'] * value_score
        )
        
        # Calculate confidence level
        confidence = self._calculate_confidence(season_over_rate, player_consistency, team_rank)
        
        return {
            'total_score': round(total_score, 2),
            'matchup_score': round(matchup_score, 2),
            'player_history_score': round(player_history_score, 2),
            'consistency_score': round(consistency_score, 2),
            'value_score': round(value_score, 2),
            'confidence': confidence,
            'team_rank': team_rank,
            'over_rate': season_over_rate,
            'player_avg': player_avg,
            'player_consistency': player_consistency,
            'line_vs_avg': line - player_avg,
            'is_home': is_home,
            'week': week,
            'l5_over_rate': l5_over_rate,
            'home_over_rate': home_over_rate,
            'away_over_rate': away_over_rate,
            'streak': player_streak,  # Add streak to return values
            'analysis': self._generate_analysis(player, opposing_team, stat_type, line, total_score, confidence)
        }
    
    def _calculate_matchup_score(self, team_rank: int, stat_type: str) -> float:
        """Calculate score based on defensive matchup"""
        # Higher rank = worse defense = higher score (better matchup for offense)
        # Rank 1 (best defense) = 0 score, Rank 32 (worst defense) = 100 score
        score = ((team_rank - 1) / 31) * 100
        
        return score
    
    def _calculate_player_history_score(self, season_over_rate: float, loc_over_rate: float, l5_over_rate: float, player_streak: int, line: float) -> float:
        """Calculate score based on player's historical performance"""
        # Base score from over rate (0-100)
        season_score = season_over_rate * 100
        loc_score = loc_over_rate * 100
        l5_score = l5_over_rate * 100

        # weight 
        weights = {
            'season': 0.2,
            'loc': 0.3,
            'l5': 0.5
        }

        base_score = (
            weights['season'] * season_score +
            weights['loc'] * loc_score +
            weights['l5'] * l5_score
        )
        
        # Apply streak multiplier (e.g., 5 game streak = 1.05x multiplier = 5% bonus)
        streak_multiplier = (1 + (player_streak / 100))
        total_score = base_score * streak_multiplier

        return max(0, min(100, total_score))
    
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
        """
        Calculate betting value score based on Expected Value (EV)
        Heavy favorites are capped because of limited upside
        """
        if odds == 0:
            return 50  # Default middle score
        
        # Convert American odds to implied probability
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)
        
        # Calculate Expected Value (EV)
        # EV = (win_prob × profit) - (loss_prob × stake)
        expected_value = (over_rate * (1 / implied_prob - 1)) - ((1 - over_rate) * 1)
        
        # Simple EV-based scoring
        # Scale EV to 0-100 score (EV of 0.5 = great value)
        ev_score = 50 + (expected_value * 100)  # Linear scaling
        
        # Cap the maximum score based on odds (heavy favorites get lower ceiling)
        # The heavier the favorite, the lower the max value score
        if odds >= 100:  # Plus odds (underdog)
            max_score = 100  # No cap for underdogs
        elif odds >= -110:  # Close to even
            max_score = 95
        elif odds >= -150:  # Slight favorite
            max_score = 85
        elif odds >= -200:  # Moderate favorite
            max_score = 75
        elif odds >= -250:  # Heavy favorite
            max_score = 65
        elif odds >= -300:  # Very heavy favorite
            max_score = 55
        elif odds >= -400:  # Extreme favorite
            max_score = 50
        elif odds >= -500:  # Ridiculous favorite
            max_score = 45
        else:  # -500 or worse (terrible upside)
            max_score = 40
        
        # Apply the cap
        capped_score = min(ev_score, max_score)
        
        return max(20, min(100, capped_score))
    
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
