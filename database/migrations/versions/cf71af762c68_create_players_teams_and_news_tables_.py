"""Create players, teams, and news tables empty

Revision ID: cf71af762c68
Revises: 28ad80a82bde
Create Date: 2026-10-12 16:50:47.633112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cf71af762c68'
down_revision: Union[str, Sequence[str], None] = '28ad80a82bde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_table('news')
    op.drop_table('teams')          # drops ix_teams_league_id along with it

    op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('current_league', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short_name', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('venue_id', sa.Integer(), nullable=True),
        sa.Column('is_national', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('news',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('headline', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', name='uq_news_url'),
    )
    # players last: its foreign keys need teams.id to exist and be a primary key
    op.create_table('players',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('position', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('number', sa.Integer(), nullable=True),
        sa.Column('dob', sa.Date(), nullable=True),
        sa.Column('height_cm', sa.Integer(), nullable=True),
        sa.Column('preferred_foot', sa.String(), nullable=True),
        sa.Column('nationality', sa.String(), nullable=True),
        sa.Column('current_team_id', sa.Integer(), nullable=True),
        sa.Column('national_team_id', sa.Integer(), nullable=True),
        sa.Column('market_value_eur', sa.Integer(), nullable=True),
        sa.Column('contract_exp', sa.Date(), nullable=True),
        sa.Column('availability', sa.String(), nullable=True),
        sa.Column('injury_type', sa.String(), nullable=True),
        sa.Column('injury_return', sa.Date(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('annual_wages_eur', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['current_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['national_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
    op.create_index(op.f('ix_players_current_team_id'), 'players', ['current_team_id'], unique=False)
    op.create_index(op.f('ix_players_national_team_id'), 'players', ['national_team_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_players_national_team_id'), table_name='players')
    op.drop_index(op.f('ix_players_current_team_id'), table_name='players')
    op.drop_table('players')
    op.drop_table('news')
    op.drop_table('teams')

    op.create_table('teams',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        sa.Column('team_name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('team_id'),
    )
    op.create_index(op.f('ix_teams_league_id'), 'teams', ['league_id'], unique=False)
    op.create_table('news',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('link', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('image', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
