from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class LiveFixture(Base):
    __tablename__ = "live_fixtures"
    
    match_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String)
    away_team_id: Mapped[int] = mapped_column(Integer)
    away_team: Mapped[str] = mapped_column(String)
    event_date: Mapped[datetime] = mapped_column(DateTime)
    current_minute: Mapped[int] = mapped_column(Integer)
    home_score: Mapped[int] = mapped_column(Integer)
    away_score: Mapped[int] = mapped_column(Integer)
    home_score_ht: Mapped[int] = mapped_column(Integer)
    away_score_ht: Mapped[int] = mapped_column(Integer)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Fixture(Base):
    __tablename__ = "fixtures"
    
    match_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer)
    away_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String)
    away_team: Mapped[str] = mapped_column(String)
    venue_id: Mapped[int] = mapped_column(Integer)
    home_score: Mapped[int] = mapped_column(Integer)
    away_score: Mapped[int] = mapped_column(Integer)
    event_date: Mapped[datetime] = mapped_column(DateTime)

class News(Base):
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(String)
    image: Mapped[str] = mapped_column(String)
    
class Team(Base):
    __tablename__ = "teams"
    
    team_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    team_name: Mapped[str] = mapped_column(String)
    