"""akkaunt o'chganda sertifikat qoladi: certificates.user_id SET NULL

Revision ID: f2b7d5a9e310
Revises: e6a1f8c4b02d
Create Date: 2026-11-25 18:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'f2b7d5a9e310'
down_revision = 'e6a1f8c4b02d'
branch_labels = None
depends_on = None

FK = 'fk_certificates_user_id_users'


def upgrade():
    op.alter_column('certificates', 'user_id', existing_type=sa.BigInteger(), nullable=True)
    op.drop_constraint(op.f(FK), 'certificates', type_='foreignkey')
    op.create_foreign_key(op.f(FK), 'certificates', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Egasi o'chgan sertifikatlar eski sxemaga sig'maydi: ularni jimgina o'chirmaymiz
    if op.get_bind().execute(sa.text("SELECT 1 FROM certificates WHERE user_id IS NULL LIMIT 1")).first():
        raise RuntimeError("Akkaunti o'chirilgan sertifikatlar bor: avval ularni ko'rib chiqing")
    op.drop_constraint(op.f(FK), 'certificates', type_='foreignkey')
    op.create_foreign_key(op.f(FK), 'certificates', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('certificates', 'user_id', existing_type=sa.BigInteger(), nullable=False)
