"""fon vazifalari: jobs

Revision ID: b3d8f1a6c240
Revises: a9c4e2d7b153
Create Date: 2026-11-25 23:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b3d8f1a6c240'
down_revision = 'a9c4e2d7b153'
branch_labels = None
depends_on = None


def upgrade():
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table('jobs',
                    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
                    sa.Column('run_at', sa.DateTime(timezone=True)),
                    sa.Column('done_at', sa.DateTime(timezone=True)),
                    sa.Column('attempts', sa.SmallInteger(), server_default='0', nullable=False),
                    sa.Column('kind', sa.String(24), nullable=False),
                    sa.Column('key', sa.String(80)),
                    sa.Column('data', jsonb, server_default='{}', nullable=False),
                    sa.Column('result', jsonb),
                    sa.Column('error', sa.String(200)),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs')))
    op.create_index('ix_jobs_due', 'jobs', ['run_at'], postgresql_where=sa.text('run_at IS NOT NULL'))
    op.create_index('uq_jobs_key', 'jobs', ['key'], unique=True, postgresql_where=sa.text('key IS NOT NULL'))


def downgrade():
    op.drop_table('jobs')
