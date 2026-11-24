"""Yakunlangan testdan keyin: xatolar ro'yxati (error_items) va mavzu holati (user_topic_progress).

- Xato (ball < 100) — error_items qatori ochiladi. Savol qaytib berilmagani uchun xato shu kichik mavzudagi boshqa savolga
  to'liq to'g'ri javob bilan tuzatiladi: keyingi testlardagi har bir to'g'ri javob bitta (eng eski) xatoni yopadi.
- Ixtiyoriy test o'zlashtirish foiziga ta'sir qilmaydi (xatolar baribir yoziladi).
- Dars testi: mavzu «O'rganilmoqda»ga o'tadi, lesson_pct — ≥ 70% topshirilgan darslar ulushi.
- Mavzu testi: best_pct — eng yaxshi natija; ≥ 90 — mustahkam, ≥ 70 — o'zlashtirilgan, < 70 — qayta o'zlashtirish.
  Bir marta o'zlashtirilgan mavzu mavzu testini qayta yomon topshirgani uchun pasaymaydi.
- Oraliq sinov: < 70% chiqqan mavzular qayta o'zlashtirishga qaytadi.
- Diagnostika: ≥ 90% chiqqan mavzu — mustahkam, "diagnostic" belgisi bilan (rejadan chiqariladi).
"""
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..extensions import db
from ..models import ErrorItem, TestAttempt, UserTopicProgress
from . import scoring


def record(a: TestAttempt, snaps: dict) -> None:
    """snaps — {tartib: (nusxa, kichik mavzu, mavzu)}. Commit qilmaydi."""
    _errors(a, snaps)
    if a.kind == "lesson" and a.topic_id:
        _lesson(a)
    elif a.kind == "topic" and a.topic_id:
        _topic_result(_row(a.user_id, a.topic_id), int(a.score_pct))
    elif a.kind in ("interim", "diagnostic"):
        scores: dict[int, list[int]] = {}
        gone = set(a.settings_snapshot.get("dropped", []))
        for i in a.items:
            if i.position not in gone:
                scores.setdefault(snaps[i.position][2], []).append(i.score or 0)
        for tid, sc in scores.items():
            pct = scoring.percent(sc)
            if a.kind == "interim" and pct < scoring.PASS_MIN:
                _row(a.user_id, tid).status = "relearn"
            elif a.kind == "diagnostic" and pct >= scoring.SOLID_MIN:
                _diagnosed(a.user_id, tid, pct)


def upgrade(a: TestAttempt, items: list, snaps: dict, old_pct: float) -> None:
    """Qayta hisoblashdan keyin (recalc.py): mavzu holati faqat yaxshilanadi. Commit qilmaydi."""
    if a.kind == "lesson" and a.topic_id:
        _lesson(a)
    elif a.kind == "topic" and a.topic_id:
        p, pct = _row(a.user_id, a.topic_id), int(a.score_pct)
        p.best_pct = max(p.best_pct or 0, pct)
        if pct >= scoring.PASS_MIN and (p.status not in ("done", "solid") or (pct >= scoring.SOLID_MIN and p.status == "done")):
            p.status = "solid" if pct >= scoring.SOLID_MIN else "done"
            p.fail_streak = 0
    elif a.kind in ("interim", "diagnostic"):
        gone = set(a.settings_snapshot.get("dropped", []))
        scores: dict[int, list[int]] = {}
        for i in items:
            if i.position not in gone:
                scores.setdefault(snaps[i.position][2], []).append(i.score or 0)
        later = a.kind == "interim" and db.session.scalar(
            select(TestAttempt.id).where(TestAttempt.user_id == a.user_id, TestAttempt.kind == "interim",
                                         TestAttempt.status == "submitted", TestAttempt.finished_at > a.finished_at).limit(1))
        for tid, sc in scores.items():
            pct, p = scoring.percent(sc), db.session.get(UserTopicProgress, (a.user_id, tid))
            if a.kind == "diagnostic" and pct >= scoring.SOLID_MIN:
                _diagnosed(a.user_id, tid, pct)
            elif a.kind == "interim" and not later and pct >= scoring.PASS_MIN and p is not None \
                    and p.status == "relearn" and (p.best_pct or 0) >= scoring.PASS_MIN:
                p.status = "solid" if p.best_pct >= scoring.SOLID_MIN else "done"


def _diagnosed(user_id: int, topic_id: int, pct: int) -> None:
    p = _row(user_id, topic_id)
    p.status, p.best_pct = "solid", max(p.best_pct or 0, pct)
    p.flags = sorted({*(p.flags or []), "diagnostic"})


def _row(user_id: int, topic_id: int) -> UserTopicProgress:
    p = db.session.get(UserTopicProgress, (user_id, topic_id))
    if p is None:
        p = UserTopicProgress(user_id=user_id, topic_id=topic_id, status="none", flags=[], lesson_pct=0, fail_streak=0)
        db.session.add(p)
    return p


def _topic_result(p: UserTopicProgress, pct: int) -> None:
    p.best_pct = max(p.best_pct or 0, pct)
    if pct >= scoring.PASS_MIN:
        p.fail_streak = 0
        # relearn'dan qaytganda eski best_pct emas, shu natija hal qiladi
        p.status = "solid" if pct >= scoring.SOLID_MIN or p.status == "solid" else "done"
    else:
        p.fail_streak = (p.fail_streak or 0) + 1
        if p.status not in ("done", "solid"):
            p.status = "relearn"


def _lesson(a: TestAttempt) -> None:
    from .catalog import lesson_scores, lessons_by_topic
    db.session.flush()                                   # shu urinish natijasi ham hisobga olinsin
    p = _row(a.user_id, a.topic_id)
    if p.status == "none":
        p.status = "learn"
    scores = lesson_scores(a.user_id, a.topic_id)
    lessons = lessons_by_topic(a.topic_id).get(a.topic_id, [])
    ok = sum(1 for x in lessons if not x["testable"] or scores.get(x["id"], 0) >= scoring.PASS_MIN)
    p.lesson_pct = round(100 * ok / len(lessons)) if lessons else 0


def _errors(a: TestAttempt, snaps: dict) -> None:
    now = datetime.now(timezone.utc)
    wrong = [i for i in a.items if i.score is not None and i.score < 100]
    right = Counter(snaps[i.position][1] for i in a.items if i.score == 100)
    if wrong:
        stmt = insert(ErrorItem).values([{"user_id": a.user_id, "subtopic_id": snaps[i.position][1],
                                          "question_id": i.question_id, "last_attempt_id": a.id, "last_wrong_at": now}
                                         for i in wrong])
        db.session.execute(stmt.on_conflict_do_update(
            index_elements=[ErrorItem.user_id, ErrorItem.question_id],
            set_={"last_attempt_id": a.id, "last_wrong_at": now}))
    for sid, n in right.items():
        oldest = (select(ErrorItem.question_id).where(ErrorItem.user_id == a.user_id, ErrorItem.subtopic_id == sid,
                                                      ErrorItem.last_attempt_id.is_distinct_from(a.id))
                  .order_by(ErrorItem.last_wrong_at, ErrorItem.question_id).limit(n))
        db.session.execute(db.delete(ErrorItem).where(ErrorItem.user_id == a.user_id, ErrorItem.question_id.in_(oldest))
                           .execution_options(synchronize_session=False))
