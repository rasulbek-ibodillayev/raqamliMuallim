"""xotirani tejash: xatolar jadvali, joriy versiya nusxasi, jurnal, halfvec, ortiqcha indekslar

Revision ID: d47b0e93a1c8
Revises: c92e7a1d5f34
Create Date: 2026-11-25 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'd47b0e93a1c8'
down_revision = 'c92e7a1d5f34'
branch_labels = None
depends_on = None


def upgrade():
    # 1) error_items: faqat tuzatilmagan xatolar, kalit (user_id, question_id)
    op.execute("DELETE FROM error_items WHERE resolved_at IS NOT NULL")
    op.drop_constraint(op.f('pk_error_items'), 'error_items', type_='primary')
    op.drop_constraint(op.f('uq_error_items_user_id_question_id'), 'error_items', type_='unique')
    op.drop_index('ix_error_items_user_subtopic', table_name='error_items')
    for col in ('id', 'wrong_count', 'resolved_at'):
        op.drop_column('error_items', col)
    op.create_primary_key(op.f('pk_error_items'), 'error_items', ['user_id', 'question_id'])

    # 2) Joriy versiyaning nusxasi questions'da: question_versions'da takrorlanmaydi
    op.alter_column('question_versions', 'snapshot', nullable=True)
    op.execute("""UPDATE question_versions v SET snapshot = NULL FROM questions q
                  WHERE q.id = v.question_id AND q.version = v.version AND v.snapshot->>'text' = q.text
                    AND v.snapshot->>'type' = q.type AND v.snapshot->>'difficulty' = q.difficulty
                    AND v.snapshot->'data' = q.data AND v.snapshot->'answer' = q.answer
                    AND v.snapshot->>'explanation' IS NOT DISTINCT FROM q.explanation""")

    # 3) Jurnalda savolning to'liq nusxalari (before/after) — versiyalarda bor
    op.execute("""UPDATE audit_log SET data = jsonb_strip_nulls(jsonb_build_object('status', data->'status'))
                  WHERE entity = 'question' AND action IN ('create', 'update')""")

    # 4) Embedding: 2 bayt/o'lcham
    op.drop_index('ix_rag_chunks_embedding', table_name='rag_chunks')
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE halfvec(768) USING embedding::halfvec(768)")
    op.execute("CREATE INDEX ix_rag_chunks_embedding ON rag_chunks USING hnsw (embedding halfvec_cosine_ops) "
               "WITH (m = 16, ef_construction = 64)")

    # 5) So'rovlar ishlatmaydigan indekslar (mavzu o'chirilganda kerak bo'lardi, savoli bor mavzu esa o'chmaydi)
    op.drop_index(op.f('ix_test_attempts_topic_id'), table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_subtopic_id'), table_name='test_attempts')


def downgrade():
    op.create_index(op.f('ix_test_attempts_subtopic_id'), 'test_attempts', ['subtopic_id'])
    op.create_index(op.f('ix_test_attempts_topic_id'), 'test_attempts', ['topic_id'])
    op.drop_index('ix_rag_chunks_embedding', table_name='rag_chunks')
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768)")
    op.execute("CREATE INDEX ix_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops) "
               "WITH (m = 16, ef_construction = 64)")
    op.execute("""UPDATE question_versions v SET snapshot = jsonb_build_object('type', q.type, 'difficulty', q.difficulty,
                  'text', q.text, 'data', q.data, 'answer', q.answer, 'explanation', q.explanation)
                  FROM questions q WHERE q.id = v.question_id AND v.snapshot IS NULL""")
    op.alter_column('question_versions', 'snapshot', nullable=False)
    op.drop_constraint(op.f('pk_error_items'), 'error_items', type_='primary')
    op.add_column('error_items', sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False))
    op.add_column('error_items', sa.Column('wrong_count', sa.SmallInteger(), server_default='1', nullable=False))
    op.add_column('error_items', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_primary_key(op.f('pk_error_items'), 'error_items', ['id'])
    op.create_unique_constraint(op.f('uq_error_items_user_id_question_id'), 'error_items', ['user_id', 'question_id'])
    op.create_index('ix_error_items_user_subtopic', 'error_items', ['user_id', 'subtopic_id'])
