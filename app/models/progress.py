"""O'quv jarayoni: mavzu holati, xatolar, takrorlash jadvali, tushuntirish usullari samaradorligi."""
from datetime import datetime

from sqlalchemy import (Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, SmallInteger,
                        String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._base import JSONB, PK, Timestamps, one_of, pk

TOPIC_STATUS = ("none", "learn", "relearn", "done", "solid")   # TZ 7-bo'lim


class UserTopicProgress(db.Model):
    __tablename__ = "user_topic_progress"
    __table_args__ = (
        one_of("status", TOPIC_STATUS),
        CheckConstraint("lesson_pct BETWEEN 0 AND 100", name="lesson_pct_range"),
    )

    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(8), default="none", server_default="none")
    flags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")  # belgilar: ["review_suggested", ...]
    lesson_pct: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    last_block_id: Mapped[int | None] = mapped_column(PK, ForeignKey("content_blocks.id", ondelete="SET NULL"))
    stage: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")  # keyingi test bosqichi
    best_pct: Mapped[float | None] = mapped_column(Float)
    fail_streak: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class ErrorItem(db.Model):
    """Xatolar ro'yxati: foydalanuvchi + savol bo'yicha bitta qator, analitika kichik mavzu darajasida."""
    __tablename__ = "error_items"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id"),
        Index("ix_error_items_user_subtopic", "user_id", "subtopic_id"),
    )

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"))
    subtopic_id: Mapped[int] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(PK, ForeignKey("questions.id", ondelete="CASCADE"))
    last_attempt_id: Mapped[int | None] = mapped_column(PK, ForeignKey("test_attempts.id", ondelete="SET NULL"))
    wrong_count: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # keyin to'g'ri javob berilgan


class ReviewSchedule(db.Model):
    """Spaced repetition (SM-2 uslubida) kichik mavzu darajasida: «Kunlik 5 ta savol» shu yerdan olinadi."""
    __tablename__ = "review_schedule"
    __table_args__ = (Index("ix_review_schedule_user_due", "user_id", "due_at"),)

    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subtopic_id: Mapped[int] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="CASCADE"), primary_key=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_days: Mapped[float] = mapped_column(Float, default=1, server_default="1")
    ease: Mapped[float] = mapped_column(Float, default=2.5, server_default="2.5")
    repetitions: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MethodStat(Timestamps, db.Model):
    """Tushuntirish usuli samaradorligi (10.3): usul ko'rsatilgandan keyin test natijasi."""
    __tablename__ = "method_stats"
    __table_args__ = (UniqueConstraint("subtopic_id", "method"),)

    id: Mapped[int] = pk()
    subtopic_id: Mapped[int] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(40))          # analogy, example, visual, step_by_step, ...
    shown: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    succeeded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    score_sum: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
