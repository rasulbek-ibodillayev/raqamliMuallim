"""E'tirozlarni ko'rib chiqish (ekspert). Savol bo'yicha guruhlanadi: bitta xulosa shu savolga e'tiroz bildirganlarning
hammasiga boradi.

| Qaror  | Nima bo'ladi                                                                                        |
|--------|-----------------------------------------------------------------------------------------------------|
| key    | To'g'ri javob o'zgaradi: yangi versiya, barcha natijalar qayta hisoblanadi (faqat foydaga)            |
|        | Bitta javobli savolda bir nechta javob belgilansa — hammasi to'g'ri hisoblanadi, savol to'xtatiladi   |
|        | Ochiq savolda — yangi qabul qilinadigan yozilishlar qo'shiladi                                        |
| drop   | Savol natijalardan chiqariladi va testlardan to'xtatiladi (tahrirlab qayta tasdiqlash mumkin)         |
| fix    | E'tiroz o'rinli, lekin natijalar o'zgarmaydi: ekspert matnni tahrirlaydi                               |
| reject | Rad etiladi                                                                                          |
"""
from collections import Counter
from datetime import datetime, timezone

from flask_babel import gettext as _
from sqlalchemy import func, select

from ..extensions import db
from ..models import AttemptItem, Objection, Question, Subtopic, TestAttempt, Topic, User
from . import archive, notify, recalc, seen, versions
from . import question_bank as qb
from .timefmt import when

ACTIONS = ("key", "drop", "fix", "reject")


def _open():
    return (select(Objection).join(Question, Question.id == Objection.question_id)
            .join(Subtopic, Subtopic.id == Question.subtopic_id).join(Topic, Topic.id == Subtopic.topic_id)
            .where(Objection.status == "review"))


def count(areas: set[int] | None = None) -> int:
    """Ko'rib chiqilmagan e'tirozli savollar soni."""
    q = _open().with_only_columns(func.count(Objection.question_id.distinct()))
    return db.session.scalar(q.where(Topic.section_id.in_(areas)) if areas is not None else q)


def queue(areas: set[int] | None = None) -> list[dict]:
    """Savollar: shoshilinchlari birinchi, keyin eng eski e'tiroz."""
    q = (_open().with_only_columns(Question.id, Question.text, Question.difficulty, Topic.title, func.count(),
                                   func.bool_or(Objection.urgent), func.min(Objection.created_at))
         .group_by(Question.id, Topic.title)
         .order_by(func.bool_or(Objection.urgent).desc(), func.min(Objection.created_at)))
    if areas is not None:
        q = q.where(Topic.section_id.in_(areas))
    return [{"id": i, "q": text, "lvl": qb.DIFF_TO_LEVEL[d], "topic": topic, "n": n, "urgent": u, "ago": when(t)}
            for i, text, d, topic, n, u, t in db.session.execute(q)]


def _answers(q: Question) -> Counter:
    """Shu variantli versiyalarga berilgan javoblar: {variant indeksi yoki matn: soni}."""
    same = [v for v, s in versions.all_of(q.id).items() if (s.get("data") or {}).get("options") == (q.data or {}).get("options")]
    v = AttemptItem.answer["v"].label("v")
    rows = db.session.execute(
        select(v, func.count()).join(TestAttempt, TestAttempt.id == AttemptItem.attempt_id)
        .where(AttemptItem.question_id == q.id, AttemptItem.question_version.in_(same),
               TestAttempt.user_id.in_(seen.given_to(q.id)), TestAttempt.status == "submitted", AttemptItem.answer.is_not(None))
        .group_by(v)).all()
    out: Counter = Counter()
    old = [(v, 1) for blob in db.session.scalars(
        select(TestAttempt.items_archive).where(TestAttempt.user_id.in_(seen.given_to(q.id)), archive.may_have(q.id)))
        for qid, ver, _sec, _score, v in archive.scan(blob) if qid == q.id and ver in same and v is not None]
    for value, n in [*rows, *old]:
        for x in (value if isinstance(value, list) else [value]):
            out[x] += n
    return out


def detail(question_id: int) -> dict | None:
    q = db.session.get(Question, question_id)
    if q is None:
        return None
    sub = db.session.get(Subtopic, q.subtopic_id)
    got = _answers(q) if q.type in ("single", "multiple", "open") else Counter()
    total = sum(got.values())
    right = set((q.answer or {}).get("keys", []))
    d = q.data or {}
    rows = db.session.execute(
        select(Objection, User.first_name, User.last_name).join(User, User.id == Objection.user_id)
        .where(Objection.question_id == q.id, Objection.status == "review").order_by(Objection.created_at)).all()
    return {"id": q.id, "type": q.type, "kind": qb.TYPE_TO_KIND[q.type], "text": q.text, "status": q.status, "code": d.get("code"),
            "table": d.get("table"), "image": d.get("image"), "why": q.explanation, "lvl": qb.DIFF_TO_LEVEL[q.difficulty],
            "where": f"{sub.topic.title} · {sub.title}", "section_id": sub.topic.section_id,
            "options": [{"i": i, "text": o, "right": i in right, "pct": round(100 * got[i] / total) if total else 0}
                        for i, o in enumerate(d.get("options", []))],
            "pairs": [f"{left} — {d['right'][r]}" for left, r in zip(d.get("left", []), (q.answer or {}).get("pairs", []))],
            "value": (q.answer or {}).get("value"), "accept": (q.answer or {}).get("accept", []),
            "given": [(str(v), n) for v, n in got.most_common(8)] if q.type == "open" else [],
            "objections": [{"who": f"{first} {last[:1]}.", "ini": (first[:1] + last[:1]).upper(), "reason": o.reason,
                            "note": o.text, "urgent": o.urgent, "when": when(o.created_at)} for o, first, last in rows]}


def pause(question_id: int, actor_id: int, on: bool) -> bool:
    """Testlarga tushishini vaqtincha to'xtatish / davom ettirish."""
    q = db.session.get(Question, question_id)
    if q is None or q.status != ("approved" if on else "paused"):
        return False
    q.status = "paused" if on else "approved"
    qb.audit(actor_id, "pause" if on else "resume", q.id)
    db.session.commit()
    return True


def _new_key(q: Question, keys: list[int], accept: list[str]) -> tuple[dict, dict | None]:
    """(baholash uchun kalit, yangi versiya javobi yoki None — savol to'xtatiladi). Xato — FormError."""
    if q.type in ("single", "multiple"):
        n = len((q.data or {}).get("options", []))
        keys = sorted({k for k in keys if 0 <= k < n})
        if not keys:
            raise qb.FormError({"keys": _("To‘g‘ri javobni belgilang")})
        if keys == sorted(q.answer["keys"]):
            raise qb.FormError({"keys": _("To‘g‘ri javob o‘zgarmadi. Boshqa variantni belgilang yoki boshqa qarorni tanlang")})
        if q.type == "multiple" and len(keys) < 2:
            raise qb.FormError({"keys": _("Ko‘p javobli savolda kamida 2 ta to‘g‘ri javob bo‘lsin")})
        answer = {"keys": keys}
        return answer, (None if q.type == "single" and len(keys) > 1 else answer)
    if q.type == "open":
        old = [q.answer["value"], *q.answer.get("accept", [])]
        new = [x for x in dict.fromkeys(a.strip() for a in accept) if x and x not in old]
        if not new:
            raise qb.FormError({"accept": _("Qabul qilinadigan yangi javobni kiriting")})
        answer = {**q.answer, "accept": [*q.answer.get("accept", []), *new]}
        return answer, answer
    raise qb.FormError({"action": _("Moslashtirish savolida kalitni tahrirlash sahifasida o‘zgartiring")})


def decide(question_id: int, actor_id: int, action: str, verdict: str, keys=(), accept=()) -> int:
    """Ko'rib chiqilmagan barcha e'tirozlarga qaror. Hammasi bitta tranzaksiyada. Natija: qayta hisoblangan natijalar soni."""
    q = db.session.scalar(select(Question).where(Question.id == question_id).with_for_update())
    rows = list(db.session.scalars(select(Objection).where(Objection.question_id == question_id, Objection.status == "review")
                                   .with_for_update()))
    if q is None or not rows:
        raise qb.FormError({"action": _("E’tiroz topilmadi yoki allaqachon ko‘rib chiqilgan")})
    if action not in ACTIONS:
        raise qb.FormError({"action": _("Qarorni tanlang")})
    if not verdict:
        raise qb.FormError({"verdict": _("Xulosani yozing: u e’tiroz bildirganlarga yuboriladi")})
    changes: list[recalc.Change] = []
    if action == "key":
        grade_by, new_answer = _new_key(q, list(keys), list(accept))
        version = None
        if new_answer is None:
            q.status = "paused"
        else:
            q = qb.save({**qb._snapshot(q), "answer": new_answer}, actor_id, q.id, status=q.status, commit=False)
            version = q.version
        db.session.flush()
        changes = recalc.regrade(q.id, grade_by, q.type, q.data, version)
    elif action == "drop":
        q.status = "paused" if q.status == "approved" else q.status
        changes = recalc.drop(q.id)
    _close(rows, changes, actor_id, action != "reject", verdict)
    qb.audit(actor_id, f"objection_{action}", q.id, {"objections": len(rows), "changed": sum(c.new > c.old for c in changes),
                                                     "verdict": verdict})
    db.session.commit()
    return sum(c.new > c.old for c in changes)


def _close(rows: list[Objection], changes: list[recalc.Change], actor_id: int, accepted: bool, verdict: str) -> None:
    by_attempt = {c.attempt_id: c for c in changes}
    now = datetime.now(timezone.utc)
    for o in rows:
        c = by_attempt.get(o.attempt_id)
        o.status, o.verdict, o.expert_id, o.decided_at = ("accepted" if accepted else "rejected"), verdict, actor_id, now
        if c and c.new > c.old:
            o.score_before, o.score_after = c.old, c.new
        notify.add(o.user_id, notify.OBJ_ACCEPTED if accepted else notify.OBJ_REJECTED, o.attempt_id,
                   c.old if c else None, c.new if c else None)
    told = {(o.user_id, o.attempt_id) for o in rows}
    for c in changes:                                # e'tiroz bildirmagan, lekin natijasi o'zgarganlar
        if c.new > c.old and (c.user_id, c.attempt_id) not in told:
            notify.add(c.user_id, notify.RECALC, c.attempt_id, c.old, c.new)
