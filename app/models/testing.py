"""Test urinishlari va berilgan savollar."""
import uuid
from datetime import datetime

from sqlalchemy import (CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer,
                        LargeBinary, SmallInteger, String, Uuid)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, created_at, one_of, pk

ATTEMPT_KINDS = ("diagnostic", "topic", "control", "final", "optional", "daily", "exam")
ATTEMPT_STATUS = ("in_progress", "submitted", "expired", "abandoned")
DECISIONS = ("pass", "warn", "fail")


class TestAttempt(db.Model):
    __tablename__ = "test_attempts"
    __table_args__ = (
        one_of("kind", ATTEMPT_KINDS),
        one_of("status", ATTEMPT_STATUS),
        one_of("decision", DECISIONS),
        CheckConstraint("stage IS NULL OR stage BETWEEN 1 AND 3", name="stage_range"),
        Index("ix_test_attempts_user_started", "user_id", "started_at"),
    )

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"))
    # Oflayn (IndexedDB) qayta yuborishda takror yozilmasligi uchun mijoz yaratgan UUID
    client_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(11), default="in_progress", server_default="in_progress")
    topic_id: Mapped[int | None] = mapped_column(PK, ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    stage: Mapped[int | None] = mapped_column(SmallInteger)              # 1 oson / 2 o'rta / 3 qiyin
    total: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    correct: Mapped[float | None] = mapped_column(Float)                 # qisman ball bo'lishi mumkin
    score_pct: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str | None] = mapped_column(String(4))
    # Boshlangan paytdagi chegaralar, vaqt, savollar soni — keyin sozlama o'zgarsa ham natija buzilmaydi
    settings_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    started_at: Mapped[datetime] = created_at()
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 1 yildan eski urinishlar: attempt_items o'chiriladi, bu yerda zlib(JSON) ko'rinishida qoladi
    items_archive: Mapped[bytes | None] = mapped_column(LargeBinary)

    items: Mapped[list["AttemptItem"]] = relationship(back_populates="attempt", order_by="AttemptItem.position",
                                                      cascade="all, delete-orphan")


class AttemptItem(db.Model):
    """Ixcham: (urinish, tartib) → savol versiyasi, javob, ball, vaqt."""
    __tablename__ = "attempt_items"
    __table_args__ = (
        ForeignKeyConstraint(["question_id", "question_version"],
                             ["question_versions.question_id", "question_versions.version"],
                             name="fk_attempt_items_question_version"),
    )

    attempt_id: Mapped[int] = mapped_column(PK, ForeignKey("test_attempts.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    question_id: Mapped[int] = mapped_column(PK, index=True)
    question_version: Mapped[int] = mapped_column(Integer)
    answer: Mapped[dict | None] = mapped_column(JSONB)                  # null — javob berilmagan
    score: Mapped[float | None] = mapped_column(Float)                  # 0..1
    time_ms: Mapped[int | None] = mapped_column(Integer)

    attempt: Mapped[TestAttempt] = relationship(back_populates="items")
