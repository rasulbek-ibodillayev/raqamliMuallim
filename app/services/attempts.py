"""Test yig'ish: savollarni tanlash va urinishni boshlash.

Qoidalar:
- Savol bazada bir joyda (questions) turadi; urinish faqat (question_id, version) ga havola qiladi.
- Bitta foydalanuvchiga bitta savol ikki marta berilmaydi: berilgan savollar user_seen_questions'ga yoziladi.
- Kichik mavzudagi yangi savollar tugasa, test to'liq bo'lishi uchun eng oldin ko'rilgan savollar qaytariladi
  (seen_on bo'yicha). Nechtasi takrorlangani test_attempts.settings_snapshot["repeated"] ga yoziladi —
  admin shu bo'yicha qaysi mavzuga yangi savol kerakligini ko'radi.
- Faqat tasdiqlangan (approved) savollar olinadi.

Savollar bitta SQL so'rov bilan tanlanadi: har bir kichik mavzu ichida avval ko'rilmaganlar (tasodifiy tartibda),
keyin ko'rilganlar (eng eskisidan) va har biridan rejadagi sonicha olinadi.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert

from ..extensions import db
from ..models import Question, Subtopic, TestAttempt, AttemptItem, UserSeenQuestion


@dataclass(frozen=True)
class Picked:
    question_id: int
    version: int
    subtopic_id: int
    repeated: bool          # foydalanuvchi bu savolni avval ko'rgan (yangi savollar yetmadi)


def plan_for_topic(topic_id: int) -> dict[int, int]:
    """Mavzu testi rejasi: {kichik mavzu id: savollar soni (Subtopic.weight)}."""
    rows = db.session.execute(select(Subtopic.id, Subtopic.weight).where(Subtopic.topic_id == topic_id)
                              .order_by(Subtopic.position)).all()
    return {sid: w for sid, w in rows if w > 0}


def pick_questions(user_id: int, plan: dict[int, int], difficulty: str | None = None) -> list[Picked]:
    """Reja bo'yicha savollarni tanlaydi (bazaga hech narsa yozmaydi). Natija kichik mavzular tartibida."""
    plan = {sid: n for sid, n in plan.items() if n > 0}
    if not plan:
        return []
    seen = UserSeenQuestion
    is_seen = seen.question_id.is_not(None)
    rank = func.row_number().over(
        partition_by=Question.subtopic_id,
        order_by=(is_seen, seen.seen_on, func.random()),
    ).label("rn")
    q = (select(Question.id, Question.version, Question.subtopic_id, is_seen.label("repeated"), rank)
         .outerjoin(seen, (seen.question_id == Question.id) & (seen.user_id == user_id))
         .where(Question.subtopic_id.in_(plan), Question.status == "approved"))
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    ranked = q.subquery()
    # Har bir kichik mavzu uchun o'z limiti: (subtopic_id, n) jadvali bilan solishtiriladi
    limits = select(func.unnest(list(plan.keys())).label("sid"),
                    func.unnest(list(plan.values())).label("n")).subquery()
    rows = db.session.execute(
        select(ranked.c.id, ranked.c.version, ranked.c.subtopic_id, ranked.c.repeated)
        .join(limits, limits.c.sid == ranked.c.subtopic_id)
        .where(ranked.c.rn <= limits.c.n)
        .order_by(ranked.c.subtopic_id, ranked.c.rn)
    ).all()
    order = {sid: i for i, sid in enumerate(plan)}
    picked = [Picked(r.id, r.version, r.subtopic_id, bool(r.repeated)) for r in rows]
    return sorted(picked, key=lambda p: order[p.subtopic_id])   # sorted barqaror: kichik mavzu ichidagi tartib saqlanadi


def start_attempt(user_id: int, kind: str, plan: dict[int, int], *, difficulty: str | None = None,
                  topic_id: int | None = None, stage: int | None = None, time_limit_s: int | None = None,
                  client_uuid: uuid.UUID | None = None, settings: dict | None = None) -> TestAttempt:
    """Urinishni yaratadi: savollar tanlanadi, attempt_items yoziladi va savollar «ko'rilgan» deb belgilanadi.

    client_uuid berilsa va shunday urinish bor bo'lsa — o'sha qaytariladi (oflayn qayta yuborish takror yaratmaydi).
    Hammasi bitta tranzaksiyada.
    """
    if client_uuid is not None:
        existing = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == client_uuid))
        if existing is not None:
            if existing.user_id != user_id:
                raise PermissionError("Bu urinish boshqa foydalanuvchiga tegishli")
            return existing

    picked = pick_questions(user_id, plan, difficulty)
    now = datetime.now(timezone.utc)
    attempt = TestAttempt(
        user_id=user_id, kind=kind, topic_id=topic_id, stage=stage, total=len(picked),
        client_uuid=client_uuid or uuid.uuid4(),
        deadline_at=now + timedelta(seconds=time_limit_s) if time_limit_s else None,
        settings_snapshot={**(settings or {}), "plan": {str(k): v for k, v in plan.items()},
                           "difficulty": difficulty, "requested": sum(plan.values()),
                           "repeated": sum(p.repeated for p in picked)},
    )
    attempt.items = [AttemptItem(position=i, question_id=p.question_id, question_version=p.version)
                     for i, p in enumerate(picked)]
    db.session.add(attempt)
    if picked:
        # Qayta berilgan savolning sanasi yangilanadi: keyingi safar u navbatning oxiriga o'tadi
        stmt = insert(UserSeenQuestion).values([{"user_id": user_id, "question_id": p.question_id} for p in picked])
        db.session.execute(stmt.on_conflict_do_update(
            index_elements=[UserSeenQuestion.user_id, UserSeenQuestion.question_id],
            set_={"seen_on": literal_column("CURRENT_DATE")}))
    db.session.commit()
    return attempt
