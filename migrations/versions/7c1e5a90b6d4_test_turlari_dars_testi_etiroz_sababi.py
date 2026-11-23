"""test turlari, dars testi (subtopic_id), e'tiroz sababi

Revision ID: 7c1e5a90b6d4
Revises: 14d1231782d2
Create Date: 2026-11-23 18:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '7c1e5a90b6d4'
down_revision = '14d1231782d2'
branch_labels = None
depends_on = None

OLD = ("diagnostic", "topic", "control", "final", "optional", "daily", "exam")
NEW = ("diagnostic", "lesson", "topic", "daily", "interim", "weekly", "monthly", "optional", "final", "errors", "exam")
REASONS = ("wrong_key", "also_correct", "unclear", "media", "other")


def _in(col, vals):
    return f"{col} IN ({', '.join(repr(v) for v in vals)})"


def upgrade():
    op.drop_constraint(op.f('ck_test_attempts_kind'), 'test_attempts', type_='check')
    op.execute("UPDATE test_attempts SET kind = 'interim' WHERE kind = 'control'")
    op.create_check_constraint(op.f('ck_test_attempts_kind'), 'test_attempts', _in("kind", NEW))
    op.add_column('test_attempts', sa.Column('subtopic_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_test_attempts_subtopic_id_subtopics'), 'test_attempts', 'subtopics',
                          ['subtopic_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_test_attempts_subtopic_id'), 'test_attempts', ['subtopic_id'])

    op.add_column('objections', sa.Column('reason', sa.String(length=12), server_default='other', nullable=False))
    op.add_column('objections', sa.Column('urgent', sa.Boolean(), server_default='false', nullable=False))
    op.create_check_constraint(op.f('ck_objections_reason'), 'objections', _in("reason", REASONS))


def downgrade():
    op.drop_constraint(op.f('ck_objections_reason'), 'objections', type_='check')
    op.drop_column('objections', 'urgent')
    op.drop_column('objections', 'reason')

    op.drop_index(op.f('ix_test_attempts_subtopic_id'), table_name='test_attempts')
    op.drop_constraint(op.f('fk_test_attempts_subtopic_id_subtopics'), 'test_attempts', type_='foreignkey')
    op.drop_column('test_attempts', 'subtopic_id')
    op.drop_constraint(op.f('ck_test_attempts_kind'), 'test_attempts', type_='check')
    op.execute("UPDATE test_attempts SET kind = 'control' WHERE kind = 'interim'")
    # Eski sxemada yo'q turlar: urinishlar saqlanadi, eng yaqin turga o'tadi
    op.execute("UPDATE test_attempts SET kind = 'topic' WHERE kind = 'lesson'")
    op.execute("UPDATE test_attempts SET kind = 'optional' WHERE kind IN ('weekly', 'monthly', 'errors')")
    op.create_check_constraint(op.f('ck_test_attempts_kind'), 'test_attempts', _in("kind", OLD))
