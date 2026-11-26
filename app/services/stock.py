"""Savol zaxirasi: qaysi darslarda faol o'qituvchilarga yangi savol tugayapti (har kecha, services/tasks.py).

Shabloni bor kichik mavzu kirmaydi: unga savol so'ralganda darhol tuziladi (generator.py). Qolganida yangi savol 2 ta testga
yetmasa — ekspertga ko'rsatiladi (13b da shu ro'yxat bo'yicha AI savol tayyorlaydi). Natija jadval qatorining o'zida (jobs.result).
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ..extensions import db
from ..models import Job, Question, Subtopic, Topic, User, UserSeen
from .question_templates import TEMPLATES
from .test_builder import LESSON_N

ACTIVE_DAYS, KEEP = 30, 100


def _masks() -> dict[int, tuple[int, int, int]]:
    """{kichik mavzu: (birinchi bayt, oxirgi bayt + 1, savollar bitlari)} — bitmapning faqat kerakli qismi o'qiladi."""
    ids = defaultdict(list)
    for sid, names, qid in db.session.execute(
            select(Subtopic.id, Subtopic.generators, Question.id).join(Question, Question.subtopic_id == Subtopic.id)
            .join(Topic, Topic.id == Subtopic.topic_id).where(Question.status == "approved", Topic.is_published.is_(True))):
        if not any(n in TEMPLATES for n in names or []):
            ids[sid].append(qid)
    out = {}
    for sid, qs in ids.items():
        lo, hi = min(qs) // 8, max(qs) // 8 + 1
        out[sid] = (lo, hi, sum(1 << (q - lo * 8) for q in qs))
    return out


def compute() -> dict:
    """{"low": [[kichik mavzu, kam qolganlar soni, tugaganlar soni], …], "n": kichik mavzular soni}."""
    masks = _masks()
    low, empty = defaultdict(int), defaultdict(int)
    rows = db.session.execute(
        select(UserSeen.bits).join(User, User.id == UserSeen.user_id)
        .where(User.role == "user", User.is_active.is_(True), User.last_seen_at >= datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS))
        .execution_options(yield_per=200))
    for (bits,) in rows:
        for sid, (lo, hi, mask) in masks.items():
            mine = int.from_bytes(bits[lo:hi], "little") & mask
            if not mine:
                continue                                # bu darsga hali kirmagan
            left = mask.bit_count() - mine.bit_count()
            if left < 2 * LESSON_N:
                low[sid] += 1
                empty[sid] += left < LESSON_N
    top = sorted(low, key=lambda s: (-empty[s], -low[s], s))[:KEEP]
    return {"n": len(low), "low": [[s, low[s], empty[s]] for s in top]}


def current(areas: set[int] | None = None) -> list[dict]:
    """Oxirgi hisob: [{"name", "topic", "low", "empty"}], eng muhimi birinchi. areas — ekspertning mavzulari."""
    result = db.session.scalar(select(Job.result).where(Job.key == "cron:stock")) or {}
    rows = {s: (lo, em) for s, lo, em in result.get("low", [])}
    if not rows:
        return []
    q = select(Subtopic.id, Subtopic.title, Topic.title).join(Topic, Topic.id == Subtopic.topic_id).where(Subtopic.id.in_(rows))
    if areas is not None:
        q = q.where(Topic.section_id.in_(areas))
    names = {s: (a, b) for s, a, b in db.session.execute(q)}
    return [{"id": s, "name": names[s][0], "topic": names[s][1], "low": lo, "empty": em} for s, (lo, em) in rows.items() if s in names]
