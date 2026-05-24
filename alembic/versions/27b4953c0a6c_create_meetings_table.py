"""create_meetings_table

Revision ID: 27b4953c0a6c
Revises: 7154c0b7510b
Create Date: 2026-05-24 22:21:54.422309

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision: str = '27b4953c0a6c'
down_revision: Union[str, Sequence[str], None] = '7154c0b7510b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'meetings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_meetings_user_id', 'meetings', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_meetings_user_id', table_name='meetings')
    op.drop_table('meetings')
