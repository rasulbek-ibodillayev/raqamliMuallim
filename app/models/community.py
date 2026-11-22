"""E'tirozlar, muhokamalar, konspekt, sertifikatlar."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, QID, Timestamps, created_at, one_of, pk

OBJ_STATUS = ("review", "accepted", "rejected")


class Objection(Timestamps, db.Model):
    __tablename__ = "objections"
    __table_args__ = (
        one_of("status", OBJ_STATUS),
        Index("ix_objections_status_created", "status", "created_at"),   # ekspert navbati
    )

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(QID, ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    question_version: Mapped[int] = mapped_column(Integer)
    attempt_id: Mapped[int | None] = mapped_column(PK, ForeignKey("test_attempts.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8), default="review", server_default="review")
    expert_id: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    verdict: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score_before: Mapped[float | None] = mapped_column(Float)        # qayta hisoblash: 78% → 82%
    score_after: Mapped[float | None] = mapped_column(Float)


class Discussion(db.Model):
    """Savol bo'yicha muhokama xabarlari (e'tirozga bog'langan bo'lishi mumkin)."""
    __tablename__ = "discussions"
    __table_args__ = (Index("ix_discussions_question_created", "question_id", "created_at"),)

    id: Mapped[int] = pk()
    question_id: Mapped[int] = mapped_column(QID, ForeignKey("questions.id", ondelete="CASCADE"))
    objection_id: Mapped[int | None] = mapped_column(PK, ForeignKey("objections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(PK, ForeignKey("discussions.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    is_expert: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # moderatsiya
    created_at: Mapped[datetime] = created_at()

    author = relationship("User")


class Note(Timestamps, db.Model):
    """Shaxsiy konspekt: dars matnidan belgilangan parcha va/yoki o'z izohi."""
    __tablename__ = "notes"
    __table_args__ = (Index("ix_notes_user_topic", "user_id", "topic_id"),)

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"))
    topic_id: Mapped[int] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"))
    block_id: Mapped[int | None] = mapped_column(PK, ForeignKey("content_blocks.id", ondelete="SET NULL"))
    quote: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text)


class Certificate(db.Model):
    __tablename__ = "certificates"

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[int | None] = mapped_column(PK, ForeignKey("test_attempts.id", ondelete="SET NULL"))
    number: Mapped[str] = mapped_column(String(20), unique=True)          # RM-2026-000123
    verify_token: Mapped[str] = mapped_column(String(43), unique=True)    # secrets.token_urlsafe(32), QR'da
    full_name: Mapped[str] = mapped_column(String(170))                   # berilgan paytdagi ism (keyin o'zgarmaydi)
    score_pct: Mapped[float] = mapped_column(Float)
    topic_scores: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    pdf_path: Mapped[str | None] = mapped_column(String(300))
    issued_at: Mapped[datetime] = created_at()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(300))
