"""bildirishnomalar, ekspert huquqlari, darsda havolalar bloki

Revision ID: c92e7a1d5f34
Revises: b81d4f60c2e7
Create Date: 2026-11-25 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c92e7a1d5f34'
down_revision = 'b81d4f60c2e7'
branch_labels = None
depends_on = None

OLD = ("text", "code", "image", "table", "mermaid", "formula", "video", "callout", "example", "quiz")
NEW = (*OLD, "links")


def _in(col, vals):
    return f"{col} IN ({', '.join(repr(v) for v in vals)})"


def upgrade():
    op.create_table('notifications',
                    sa.Column('user_id', sa.BigInteger(), nullable=False),
                    sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
                    sa.Column('ref_id', sa.BigInteger(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('kind', sa.SmallInteger(), nullable=False),
                    sa.Column('old_pct', sa.SmallInteger(), nullable=True),
                    sa.Column('new_pct', sa.SmallInteger(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('user_id', 'id', name=op.f('pk_notifications')))
    op.add_column('users', sa.Column('notif_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('expert_profiles',
                    sa.Column('user_id', sa.BigInteger(), nullable=False),
                    sa.Column('perms', postgresql.JSONB(), server_default='[]', nullable=False),
                    sa.Column('areas', postgresql.JSONB(), server_default='[]', nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_expert_profiles_user_id_users'),
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_expert_profiles')))
    op.drop_constraint(op.f('ck_content_blocks_kind'), 'content_blocks', type_='check')
    op.create_check_constraint(op.f('ck_content_blocks_kind'), 'content_blocks', _in("kind", NEW))


def downgrade():
    op.execute("DELETE FROM content_blocks WHERE kind = 'links'")
    op.drop_constraint(op.f('ck_content_blocks_kind'), 'content_blocks', type_='check')
    op.create_check_constraint(op.f('ck_content_blocks_kind'), 'content_blocks', _in("kind", OLD))
    op.drop_table('expert_profiles')
    op.drop_column('users', 'notif_seen_at')
    op.drop_table('notifications')
