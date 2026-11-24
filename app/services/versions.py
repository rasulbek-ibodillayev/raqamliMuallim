"""Savol versiyalari: joriy versiyaning nusxasi saqlanmaydi (question_versions.snapshot NULL — questions qatorining o'zi),
faqat tahrirdan oldingi versiyalar to'liq nusxa bilan turadi. Shu bilan savol matni bazada bir marta saqlanadi."""
from sqlalchemy import select

from ..extensions import db
from ..models import Question, QuestionVersion

KEYS = ("type", "difficulty", "text", "data", "answer", "explanation")


def of(q: Question) -> dict:
    return {k: getattr(q, k) for k in KEYS}


def columns() -> list:
    """SELECT ustunlari: nusxa va joriy savol maydonlari — read() uchun (Question bilan JOIN qilingan so'rovda)."""
    return [QuestionVersion.snapshot, *(getattr(Question, k) for k in KEYS)]


def read(values) -> dict:
    """columns() qiymatlari → nusxa."""
    snapshot, *current = values
    return snapshot if snapshot is not None else dict(zip(KEYS, current))


def all_of(question_id: int) -> dict[int, dict]:
    """{versiya: nusxa} — savolning barcha versiyalari."""
    rows = db.session.execute(select(QuestionVersion.version, *columns()).join(Question, Question.id == QuestionVersion.question_id)
                              .where(QuestionVersion.question_id == question_id))
    return {ver: read(values) for ver, *values in rows}
