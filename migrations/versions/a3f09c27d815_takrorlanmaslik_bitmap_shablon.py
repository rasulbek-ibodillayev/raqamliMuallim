"""ko'rilgan savollar bitmapi, shablon savollar, javoblarni ixchamlash

Revision ID: a3f09c27d815
Revises: 7c1e5a90b6d4
Create Date: 2026-11-24 18:00:00

"""
from itertools import groupby

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a3f09c27d815'
down_revision = '7c1e5a90b6d4'
branch_labels = None
depends_on = None

OLD = ("expert", "ai", "import")
NEW = (*OLD, "template")


def _in(col, vals):
    return f"{col} IN ({', '.join(repr(v) for v in vals)})"


def upgrade():
    # 1) user_seen_questions → user_seen: har foydalanuvchiga bitta bitmap (bit = savol id)
    op.create_table('user_seen',
                    sa.Column('user_id', sa.BigInteger(), nullable=False),
                    sa.Column('bits', sa.LargeBinary(), nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_seen_user_id_users'),
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_user_seen')))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT user_id, question_id FROM user_seen_questions ORDER BY user_id, question_id")).all()
    for uid, group in groupby(rows, key=lambda r: r[0]):
        ids = [q for _u, q in group]
        buf = bytearray(ids[-1] // 8 + 1)
        for q in ids:
            buf[q >> 3] |= 1 << (q & 7)
        conn.execute(sa.text("INSERT INTO user_seen (user_id, bits) VALUES (:u, :b)"), {"u": uid, "b": bytes(buf)})
    op.drop_table('user_seen_questions')

    # 2) Shablon generator
    op.add_column('subtopics', sa.Column('generators', postgresql.JSONB(), server_default='[]', nullable=False))
    op.add_column('questions', sa.Column('sig', sa.String(length=120), nullable=True))
    op.create_index('uq_questions_sig', 'questions', ['sig'], unique=True, postgresql_where=sa.text('sig IS NOT NULL'))
    op.drop_constraint(op.f('ck_questions_source'), 'questions', type_='check')
    op.create_check_constraint(op.f('ck_questions_source'), 'questions', _in("source", NEW))

    # 3) Yakunlangan javoblarda `at` (faqat sinxronlash uchun) kerak emas; bekor qilingan testlar qatorlari ham
    op.execute("DELETE FROM attempt_items i USING test_attempts a WHERE a.id = i.attempt_id AND a.status = 'abandoned'")
    op.execute("""UPDATE attempt_items i SET answer = CASE WHEN jsonb_typeof(i.answer) = 'object' AND i.answer->'v' <> 'null'
                  THEN jsonb_build_object('v', i.answer->'v') END
                  FROM test_attempts a WHERE a.id = i.attempt_id AND a.status <> 'in_progress' AND i.answer IS NOT NULL""")
    op.execute("UPDATE test_attempts SET settings_snapshot = settings_snapshot - 'repeated' "
               "WHERE jsonb_exists(settings_snapshot, 'repeated')")


def downgrade():
    # Shablon savollari bankda qoladi, faqat manbasi «import» bo'ladi
    op.execute("UPDATE questions SET source = 'import' WHERE source = 'template'")
    op.drop_constraint(op.f('ck_questions_source'), 'questions', type_='check')
    op.create_check_constraint(op.f('ck_questions_source'), 'questions', _in("source", OLD))
    op.drop_index('uq_questions_sig', table_name='questions', postgresql_where=sa.text('sig IS NOT NULL'))
    op.drop_column('questions', 'sig')
    op.drop_column('subtopics', 'generators')

    op.create_table('user_seen_questions',
                    sa.Column('user_id', sa.BigInteger(), nullable=False),
                    sa.Column('question_id', sa.Integer(), nullable=False),
                    sa.Column('seen_on', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
                    sa.ForeignKeyConstraint(['question_id'], ['questions.id'],
                                            name=op.f('fk_user_seen_questions_question_id_questions'), ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_seen_questions_user_id_users'),
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('user_id', 'question_id', name=op.f('pk_user_seen_questions')))
    op.execute("""INSERT INTO user_seen_questions (user_id, question_id)
                  SELECT s.user_id, q.id FROM user_seen s CROSS JOIN questions q
                  WHERE CASE WHEN q.id < length(s.bits) * 8 THEN get_bit(s.bits, q.id) = 1 ELSE false END""")
    op.drop_table('user_seen')
