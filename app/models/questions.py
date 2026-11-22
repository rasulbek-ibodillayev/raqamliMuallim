"""Savollar banki (TZ 6.1) va ularning versiyalari."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, QID, Timestamps, created_at, one_of, pk, qid_pk

Q_TYPES = ("single", "multiple", "open", "matching")
Q_DIFFICULTY = ("easy", "medium", "hard")           # 1, 2, 3-bosqich (chegaralar 90/80/70 — settings'da)
Q_STATUS = ("draft", "review", "approved", "paused", "archived")
Q_SOURCE = ("expert", "ai", "import")


class Question(Timestamps, db.Model):
    """Joriy holat. Har bir tahrir `question_versions`ga nusxa sifatida yoziladi."""
    __tablename__ = "questions"
    __table_args__ = (
        one_of("type", Q_TYPES),
        one_of("difficulty", Q_DIFFICULTY),
        one_of("status", Q_STATUS),
        one_of("source", Q_SOURCE),
        # Test yig'ishning asosiy so'rovi: kichik mavzu + qiyinlik + tasdiqlangan
        Index("ix_questions_pick", "subtopic_id", "difficulty", "status"),
    )

    id: Mapped[int] = qid_pk()
    subtopic_id: Mapped[int] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="RESTRICT"))
    type: Mapped[str] = mapped_column(String(10))
    difficulty: Mapped[str] = mapped_column(String(6))
    text: Mapped[str] = mapped_column(Text)
    # Variantlar, kod, rasm, jadval, moslashtirish juftliklari: {"options": [...], "code": "...", "image": "...", ...}
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # To'g'ri javob (indekslar 0 dan): single/multiple {"keys": [1]} | open {"value": "45", "accept": [...]} |
    # matching {"pairs": [r0, r1, ...]} — left[k] ↔ right[pairs[k]]. Tekshiruv: services/content_import.check_question

    answer: Mapped[dict] = mapped_column(JSONB)
    explanation: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(8), default="expert", server_default="expert")
    status: Mapped[str] = mapped_column(String(8), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    time_limit_s: Mapped[int | None] = mapped_column(SmallInteger)
    author_id: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    reviewer_id: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Statistika (fon vazifasi yangilaydi): qiyinlikni kalibrlash va "qiyin mavzular" uchun
    times_answered: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    times_correct: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    subtopic = relationship("Subtopic")
    versions: Mapped[list["QuestionVersion"]] = relationship(back_populates="question",
                                                             order_by="QuestionVersion.version")


class QuestionVersion(db.Model):
    __tablename__ = "question_versions"
    __table_args__ = (UniqueConstraint("question_id", "version"),)

    id: Mapped[int] = pk()
    question_id: Mapped[int] = mapped_column(QID, ForeignKey("questions.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)       # type, difficulty, text, data, answer, explanation
    changed_by: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    change_note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = created_at()

    question: Mapped[Question] = relationship(back_populates="versions")
