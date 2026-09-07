from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Fixture(Base):
    __tablename__ = "fixtures"

    match_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String)
    away_team_id: Mapped[int] = mapped_column(Integer)
    away_team: Mapped[str] = mapped_column(String)
    venue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, index=True, default="upcoming")

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

class News(Base):
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(String)
    image: Mapped[str] = mapped_column(String)
    
class Team(Base):
    __tablename__ = "teams"
    
    team_id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    team_name: Mapped[str] = mapped_column(String)
    