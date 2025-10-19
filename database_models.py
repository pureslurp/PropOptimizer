from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database_config import Base
from datetime import datetime

class Game(Base):
    __tablename__ = "games"
    
    id = Column(String, primary_key=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    commence_time = Column(DateTime, nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    historical_merged = Column(Boolean, default=False)  # Track if historical props have been merged
    
    # Relationship
    props = relationship("Prop", back_populates="game")

class Prop(Base):
    __tablename__ = "props"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    player = Column(String, nullable=False)
    stat_type = Column(String, nullable=False)
    line = Column(Float, nullable=False)
    odds = Column(Integer, nullable=False)
    bookmaker = Column(String, nullable=False)
    is_alternate = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Enhanced columns for analysis
    player_team = Column(String, nullable=True)  # Player's team
    opp_team = Column(String, nullable=True)     # Opposing team
    opp_team_full = Column(String, nullable=True)  # Full opposing team name
    team_pos_rank_stat_type = Column(Integer, nullable=True)   # Opponent position rank for this stat type
    week = Column(Integer, nullable=True)                       # Week number for easy reference
    commence_time = Column(DateTime, nullable=True)  # Game start time
    home_team = Column(String, nullable=True)    # Home team
    away_team = Column(String, nullable=True)    # Away team
    prop_source = Column(String, nullable=True)  # Source: 'live_capture' or 'historical_api'
    
    # Relationship
    game = relationship("Game", back_populates="props")

class BoxScore(Base):
    __tablename__ = "box_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    player = Column(String, nullable=False)
    stat_type = Column(String, nullable=False)
    actual_result = Column(Float)
    week = Column(Integer, nullable=False)
    team = Column(String, nullable=True)  # Player's team
    created_at = Column(DateTime, default=datetime.utcnow)

class CacheMetadata(Base):
    __tablename__ = "cache_metadata"
    
    data_type = Column(String, primary_key=True)
    last_updated = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    record_count = Column(Integer, default=0)
