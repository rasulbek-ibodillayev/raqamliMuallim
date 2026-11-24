"""admin paneli: taklifnomalar, kunlik faollik, savol statistikasi

Revision ID: e6a1f8c4b02d
Revises: d47b0e93a1c8
Create Date: 2026-11-25 15:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e6a1f8c4b02d'
down_revision = 'd47b0e93a1c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('expert_invites',
                    sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
                    sa.Column('created_by', sa.BigInteger(), nullable=True),
                    sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('nonce', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('name', sa.String(length=160), nullable=False),
                    sa.Column('contact', sa.String(length=254), nullable=False),
                    sa.Column('perms', postgresql.JSONB(), server_default='[]', nullable=False),
                    sa.Column('areas', postgresql.JSONB(), server_default='[]', nullable=False),
                    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_expert_invites_created_by_users'),
                                            ondelete='SET NULL'),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_expert_invites')),
                    sa.UniqueConstraint('contact', name=op.f('uq_expert_invites_contact')))
    op.create_table('daily_stats',
                    sa.Column('day', sa.Date(), nullable=False),
                    sa.Column('active', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('phone', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('tablet', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('pwa', sa.Integer(), server_default='0', nullable=False),
                    sa.PrimaryKeyConstraint('day', name=op.f('pk_daily_stats')))
    op.create_table('question_stats',
                    sa.Column('question_id', sa.Integer(), nullable=False),
                    sa.Column('answered', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('correct', sa.Integer(), server_default='0', nullable=False),
                    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_question_stats_question_id_questions'),
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('question_id', name=op.f('pk_question_stats')))
    # Yakunlangan testlardagi javoblar (arxivlanganlari bundan keyingi testlarda to'planadi)
    op.execute("""INSERT INTO question_stats (question_id, answered, correct)
                  SELECT i.question_id, count(*), count(*) FILTER (WHERE i.score = 100) FROM attempt_items i
                  JOIN test_attempts a ON a.id = i.attempt_id WHERE a.status = 'submitted' AND i.score IS NOT NULL
                  GROUP BY i.question_id""")
    op.drop_column('questions', 'times_answered')
    op.drop_column('questions', 'times_correct')


def downgrade():
    op.add_column('questions', sa.Column('times_answered', sa.Integer(), server_default='0', nullable=False))
    op.add_column('questions', sa.Column('times_correct', sa.Integer(), server_default='0', nullable=False))
    op.execute("UPDATE questions q SET times_answered = s.answered, times_correct = s.correct FROM question_stats s WHERE s.question_id = q.id")
    op.drop_table('question_stats')
    op.drop_table('daily_stats')
    op.drop_table('expert_invites')
