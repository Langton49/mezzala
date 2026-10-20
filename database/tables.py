from sqlalchemy import String, Integer, DateTime, UniqueConstraint, Float, Date, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone, date

class Base(DeclarativeBase):
    pass

class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String)
    home_coach_id: Mapped[int] = mapped_column(Integer, nullable=True)
    away_team_id: Mapped[int] = mapped_column(Integer)
    away_team: Mapped[str] = mapped_column(String)
    away_coach_id: Mapped[int] = mapped_column(Integer, nullable=True)
    referee_id: Mapped[int] = mapped_column(Integer, nullable=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=True)
    round_name: Mapped[str] = mapped_column(String, nullable=True)
    group_name: Mapped[str] = mapped_column(String, nullable=True)
    stage: Mapped[str] = mapped_column(String, nullable=True)
    stage_name: Mapped[str] = mapped_column(String, nullable=True)
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
    
FIXTURE_COLS = {column.name for column in Fixture.__table__.columns}

class CompetitionStages(Base):
    __tablename__ = "comp_stages"
    __table_args__ = (
        UniqueConstraint("league_id", "stage", name="uq_comp_stages_league_id_stage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(Integer, index=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    stage: Mapped[str] = mapped_column(String)
    stage_name: Mapped[str] = mapped_column(String)
    rounds: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (
        UniqueConstraint("league_id", "season_id", "team_id", name="uq_standings_league_season_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season_id: Mapped[int] = mapped_column(Integer, index=True)
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    team_name: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer)
    played: Mapped[int] = mapped_column(Integer)
    won: Mapped[int] = mapped_column(Integer)
    drawn: Mapped[int] = mapped_column(Integer)
    lost: Mapped[int] = mapped_column(Integer)
    gf: Mapped[int] = mapped_column(Integer)
    ga: Mapped[int] = mapped_column(Integer)
    gd: Mapped[int] = mapped_column(Integer)
    pts: Mapped[int] = mapped_column(Integer)
    xgf: Mapped[float | None] = mapped_column(Float, nullable=True)
    xga: Mapped[float | None] = mapped_column(Float, nullable=True)
    xgd: Mapped[float | None] = mapped_column(Float, nullable=True)
    form: Mapped[str | None] = mapped_column(String, nullable=True)
    zone_key: Mapped[str | None] = mapped_column(String, nullable=True)
    zone_label: Mapped[str | None] = mapped_column(String, nullable=True)
    zone_type: Mapped[str | None] = mapped_column(String, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PlayerStat(Base):
    __tablename__ = "player_stats"
    __table_args__ = (
        UniqueConstraint("league_id", "season_id", "stat_type", "player_id",
                          name="uq_player_stats_league_season_stat_player"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season_id: Mapped[int] = mapped_column(Integer, index=True)
    stat_type: Mapped[str] = mapped_column(String, index=True)  # "scorers" | "assists" | "yellowcards" | "redcards" | "fouls"
    rank: Mapped[int] = mapped_column(Integer)
    player_id: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str] = mapped_column(String)
    player_position: Mapped[str | None] = mapped_column(String, nullable=True)
    team_id: Mapped[int] = mapped_column(Integer)
    team_name: Mapped[str] = mapped_column(String)
    value: Mapped[int] = mapped_column(Integer)
    matches: Mapped[int] = mapped_column(Integer)
    
class Player(Base):
    __tablename__ = "players"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    position: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=True)
    number: Mapped[int  | None] = mapped_column(Integer, nullable=True) # Player may be a free agent
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    current_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    national_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    market_value_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_exp: Mapped[date | None] = mapped_column(Date, nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    injury_type: Mapped[str | None] = mapped_column(String, nullable=True)
    injury_return: Mapped[date | None] = mapped_column(Date, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_wages_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        )
       
class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_league: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String)
    short_name: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    venue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_national: Mapped[bool] = mapped_column(Boolean, default=False)

class News(Base):
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String, unique=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)) 