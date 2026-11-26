"""oflayn paket: test_attempts.status = offline

Revision ID: c5e90b7d3f18
Revises: b3d8f1a6c240
Create Date: 2026-11-26 10:00:00

"""
from alembic import op

revision = 'c5e90b7d3f18'
down_revision = 'b3d8f1a6c240'
branch_labels = None
depends_on = None

NAME = 'ck_test_attempts_status'


def _set(values: str):
    op.drop_constraint(op.f(NAME), 'test_attempts', type_='check')
    op.create_check_constraint(op.f(NAME), 'test_attempts', f"status IN ({values})")


def upgrade():
    _set("'in_progress', 'submitted', 'expired', 'abandoned', 'offline'")


def downgrade():
    # Boshlanmagan tayyor testlar eski sxemaga sig'maydi; natijasi yo'q, savollari bankka qaytadi
    op.execute("DELETE FROM test_attempts WHERE status = 'offline'")
    _set("'in_progress', 'submitted', 'expired', 'abandoned'")
