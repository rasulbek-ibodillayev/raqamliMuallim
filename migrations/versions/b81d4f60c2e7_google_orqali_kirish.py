"""users.google_sub — Google orqali kirish

Revision ID: b81d4f60c2e7
Revises: a3f09c27d815
Create Date: 2026-11-24 22:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'b81d4f60c2e7'
down_revision = 'a3f09c27d815'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('google_sub', sa.String(length=64), nullable=True))
    op.create_index('uq_users_google_sub', 'users', ['google_sub'], unique=True,
                    postgresql_where=sa.text('google_sub IS NOT NULL'))


def downgrade():
    op.drop_index('uq_users_google_sub', table_name='users', postgresql_where=sa.text('google_sub IS NOT NULL'))
    op.drop_column('users', 'google_sub')
