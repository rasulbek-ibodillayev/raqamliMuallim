"""Ekspert huquqlari (expert_profiles): nima qila oladi (perms) va qaysi mavzularda (areas — sections id'lari).

Qator bo'lmasa — hamma huquq; areas bo'sh bo'lsa — hamma mavzu. Huquqlarni admin belgilaydi (8-bosqich).
Savollar bankini ko'rish hamma ekspertga ochiq (o'z mavzulari bo'yicha).
"""
from flask import abort
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import ExpertProfile, Question, Subtopic, Topic, User

PERMS = ("questions", "review", "topics", "objections")


def perms(user: User) -> set[str]:
    p = db.session.get(ExpertProfile, user.id)
    return set(PERMS) if p is None else set(p.perms) & set(PERMS)


def areas(user: User) -> set[int] | None:
    """Ruxsat etilgan mavzular (sections) yoki None — hammasi."""
    p = db.session.get(ExpertProfile, user.id)
    return set(p.areas) if p is not None and p.areas else None


def my_areas() -> set[int] | None:
    return areas(current_user)


def section_of_question(question_id: int) -> int | None:
    return db.session.scalar(select(Topic.section_id).join(Subtopic, Subtopic.topic_id == Topic.id)
                             .join(Question, Question.subtopic_id == Subtopic.id).where(Question.id == question_id))


def require_section(section_id: int | None) -> None:
    """Boshqa mavzu — 403."""
    allowed = my_areas()
    if allowed is not None and section_id not in allowed:
        abort(403)


def save(user_id: int, perm_list, area_ids) -> None:
    """Commit qilmaydi."""
    db.session.merge(ExpertProfile(user_id=user_id, perms=[p for p in PERMS if p in perm_list], areas=sorted(area_ids)))
