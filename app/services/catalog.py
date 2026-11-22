"""Kontent katalogi: bo'limlar, mavzular, kichik mavzular va dars bloklari — foydalanuvchi progressi bilan.

Ko'rinishlar shablonlarga oddiy dict'lar beradi (ORM obyektlari emas): shablon bazaga qo'shimcha so'rov yubormaydi.
"""
from sqlalchemy import func, select

from ..extensions import db
from ..models import (AttemptItem, ContentBlock, Question, Section, Subtopic, TestAttempt, Topic, UserTopicProgress)

PASS_PCT = 70   # kichik mavzu «tayyor» chegarasi (mavzu ochilish chegarasi bilan bir xil, TZ 7)


def topic_titles() -> list[dict]:
    """Barcha nashr qilingan mavzular, bo'lim tartibida: [{"id", "name", "section"}]. Qidiruv va eslatmalar uchun."""
    rows = db.session.execute(
        select(Topic.id, Topic.title, Section.title)
        .join(Section, Topic.section_id == Section.id)
        .where(Topic.is_published.is_(True))
        .order_by(Section.position, Section.id, Topic.position, Topic.id)
    ).all()
    return [{"id": tid, "name": name, "section": sec} for tid, name, sec in rows]


def subtopic_scores(user_id: int, topic_id: int) -> dict[int, int]:
    """Foydalanuvchining shu mavzu kichik mavzularidagi o'rtacha bali (0–100), faqat baholangan javoblar bo'yicha."""
    rows = db.session.execute(
        select(Question.subtopic_id, func.avg(AttemptItem.score))
        .join(AttemptItem, AttemptItem.question_id == Question.id)
        .join(TestAttempt, TestAttempt.id == AttemptItem.attempt_id)
        .join(Subtopic, Subtopic.id == Question.subtopic_id)
        .where(TestAttempt.user_id == user_id, Subtopic.topic_id == topic_id, AttemptItem.score.is_not(None))
        .group_by(Question.subtopic_id)
    ).all()
    return {sid: round(avg) for sid, avg in rows}


def topic_view(topic_id: int, user_id: int) -> dict | None:
    """Mavzu sahifasi uchun: nomi, bo'limi, holati, eng yaxshi natija, kichik mavzular (foizi bilan) va eng zaif qism."""
    row = db.session.execute(
        select(Topic, Section.title).join(Section, Topic.section_id == Section.id)
        .where(Topic.id == topic_id, Topic.is_published.is_(True))
    ).first()
    if row is None:
        return None
    topic, section = row
    progress = db.session.get(UserTopicProgress, (user_id, topic_id))
    scores = subtopic_scores(user_id, topic_id)
    subs = db.session.execute(select(Subtopic.id, Subtopic.title).where(Subtopic.topic_id == topic_id)
                              .order_by(Subtopic.position, Subtopic.id)).all()
    subtopics = [{"id": sid, "name": title, "pct": scores.get(sid)} for sid, title in subs]
    scored = [s for s in subtopics if s["pct"] is not None]
    weak = min((s for s in scored if s["pct"] < PASS_PCT), key=lambda s: s["pct"], default=None)
    return {
        "id": topic.id, "name": topic.title, "section": section,
        "status": progress.status if progress else "none",
        "best_pct": round(progress.best_pct) if progress and progress.best_pct is not None else None,
        "lesson_pct": progress.lesson_pct if progress else 0,
        "subtopics": subtopics, "scored": len(scored),
        "ready": sum(1 for s in scored if s["pct"] >= PASS_PCT), "weak": weak,
        "has_blocks": db.session.scalar(select(func.count()).select_from(ContentBlock).join(Subtopic)
                                        .where(Subtopic.topic_id == topic_id, ContentBlock.is_active.is_(True))) > 0,
    }


def lesson_view(topic_id: int) -> dict | None:
    """Dars: mavzu va kichik mavzular, har birida faol bloklar tartib bo'yicha. Bloklarsiz kichik mavzu ko'rsatilmaydi."""
    row = db.session.execute(
        select(Topic.id, Topic.title, Section.title).join(Section, Topic.section_id == Section.id)
        .where(Topic.id == topic_id, Topic.is_published.is_(True))
    ).first()
    if row is None:
        return None
    blocks = db.session.execute(
        select(Subtopic.id, Subtopic.title, ContentBlock.id, ContentBlock.kind, ContentBlock.data, ContentBlock.audio_text)
        .join(ContentBlock, ContentBlock.subtopic_id == Subtopic.id)
        .where(Subtopic.topic_id == topic_id, ContentBlock.is_active.is_(True))
        .order_by(Subtopic.position, Subtopic.id, ContentBlock.position, ContentBlock.id)
    ).all()
    parts: dict[int, dict] = {}
    for sid, stitle, bid, kind, data, audio in blocks:
        part = parts.setdefault(sid, {"id": sid, "anchor": f"k{sid}", "name": stitle, "blocks": []})
        part["blocks"].append({"id": bid, "kind": kind, "data": data or {}, "audio_text": audio})
    return {"id": row[0], "name": row[1], "section": row[2], "parts": list(parts.values())}
