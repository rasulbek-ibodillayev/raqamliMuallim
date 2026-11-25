"""urinishlarni cheklash: rate_limits (UNLOGGED)

Revision ID: a9c4e2d7b153
Revises: f2b7d5a9e310
Create Date: 2026-11-25 20:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'a9c4e2d7b153'
down_revision = 'f2b7d5a9e310'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rate_limits',
                    sa.Column('key', sa.BigInteger(), autoincrement=False, nullable=False),
                    sa.Column('until', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('n', sa.SmallInteger(), nullable=False),
                    sa.PrimaryKeyConstraint('key', name=op.f('pk_rate_limits')),
                    prefixes=['UNLOGGED'])


def downgrade():
    op.drop_table('rate_limits')
