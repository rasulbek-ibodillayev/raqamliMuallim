"""Test urinishlari va berilgan savollar."""
import uuid
from datetime import date, datetime

from sqlalchemy import (CheckConstraint, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer,
                        LargeBinary, SmallInteger, String, Uuid, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, QID, created_at, one_of, pk

# Nomlari mock.TEST_TYPES kalitlari bilan bir xil. control (eski nom) = interim
ATTEMPT_KINDS = ("diagnostic", "lesson", "topic", "daily", "interim", "weekly", "monthly", "optional", "final", "errors",
                 "exam")
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
    # Dars testi (kind=lesson) qaysi kichik mavzudan
    subtopic_id: Mapped[int | None] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="SET NULL"), index=True)
    # Bosqichli testda joriy bosqich (settings_snapshot["stages"] ro'yxatidagi tartib, 1 dan)
    stage: Mapped[int | None] = mapped_column(SmallInteger)
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
    """Eng katta jadval, shuning uchun ixcham: (urinish, tartib) → savol versiyasi, javob, ball, vaqt.

    Savol matni nusxalanmaydi — (question_id, question_version) orqali bitta joydagi savolga havola.
    Ustunlar tartibi PostgreSQL tekislashiga mos (8 → 4 → 2 bayt, keyin JSONB): qatorda bo'sh to'ldiruvchi yo'q.
    question_id bo'yicha alohida indeks yo'q: «foydalanuvchi bu savolni ko'rganmi» — user_seen_questions'da.
    """
    __tablename__ = "attempt_items"
    __table_args__ = (
        ForeignKeyConstraint(["question_id", "question_version"],
                             ["question_versions.question_id", "question_versions.version"],
                             name="fk_attempt_items_question_version"),
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 100", name="score_range"),
    )

    attempt_id: Mapped[int] = mapped_column(PK, ForeignKey("test_attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(QID)
    question_version: Mapped[int] = mapped_column(Integer)
    time_ms: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    score: Mapped[int | None] = mapped_column(SmallInteger)              # 0..100 (qisman ball ham butun foizda)
    answer: Mapped[dict | None] = mapped_column(JSONB)                  # {"v": javob, "at": mijoz vaqti}; null — berilmagan

    attempt: Mapped[TestAttempt] = relationship(back_populates="items")


class UserSeenQuestion(db.Model):
    """Foydalanuvchiga qaysi savollar berilgan — «bitta savol ikki marta berilmasin» qoidasi uchun.

    attempt_items arxivlansa ham (items_archive) bu jadval qoladi, shuning uchun qoida buzilmaydi.
    Qator ~36 bayt + asosiy kalit indeksi; boshqa ustun yo'q. seen_on — kichik mavzudagi barcha savollar
    ko'rib bo'linganda eng eskisini qaytarish uchun (services/attempts.py).
    """
    __tablename__ = "user_seen_questions"

    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(QID, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    seen_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
