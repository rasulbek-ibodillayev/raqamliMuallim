"""Yakunlangan testdan keyin: xatolar ro'yxati (error_items) va mavzu holati (user_topic_progress).

- Xato (ball < 100) — error_items qatori ochiladi yoki wrong_count oshadi; keyin to'liq to'g'ri javob — resolved_at.
- Ixtiyoriy test o'zlashtirish foiziga ta'sir qilmaydi (xatolar baribir yoziladi).
- Dars testi: mavzu «O'rganilmoqda»ga o'tadi, lesson_pct — ≥ 70% topshirilgan darslar ulushi.
- Mavzu testi: best_pct — eng yaxshi natija; ≥ 90 — mustahkam, ≥ 70 — o'zlashtirilgan, < 70 — qayta o'zlashtirish.
  Bir marta o'zlashtirilgan mavzu mavzu testini qayta yomon topshirgani uchun pasaymaydi.
- Oraliq sinov: < 70% chiqqan mavzular qayta o'zlashtirishga qaytadi.
- Diagnostika: ≥ 90% chiqqan mavzu — mustahkam, "diagnostic" belgisi bilan (rejadan chiqariladi).
"""
from datetime import datetime, timezone

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert

from ..extensions import db
from ..models import ErrorItem, Subtopic, TestAttempt, UserTopicProgress
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
        for i in a.items:
            scores.setdefault(snaps[i.position][2], []).append(i.score or 0)
        for tid, sc in scores.items():
            pct = scoring.percent(sc)
            if a.kind == "interim" and pct < scoring.PASS_MIN:
                _row(a.user_id, tid).status = "relearn"
            elif a.kind == "diagnostic" and pct >= scoring.SOLID_MIN:
                p = _row(a.user_id, tid)
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
    from .catalog import lesson_scores
    db.session.flush()                                   # shu urinish natijasi ham hisobga olinsin
    p = _row(a.user_id, a.topic_id)
    if p.status == "none":
        p.status = "learn"
    scores = lesson_scores(a.user_id, a.topic_id)
    total = db.session.scalar(select(func.count()).select_from(Subtopic).where(Subtopic.topic_id == a.topic_id))
    p.lesson_pct = round(100 * sum(1 for s in scores.values() if s >= scoring.PASS_MIN) / total) if total else 0


def _errors(a: TestAttempt, snaps: dict) -> None:
    now = datetime.now(timezone.utc)
    wrong = [i for i in a.items if i.score is not None and i.score < 100]
    right = [i.question_id for i in a.items if i.score == 100]
    if wrong:
        stmt = insert(ErrorItem).values([{"user_id": a.user_id, "subtopic_id": snaps[i.position][1],
                                          "question_id": i.question_id, "last_attempt_id": a.id, "last_wrong_at": now}
                                         for i in wrong])
        db.session.execute(stmt.on_conflict_do_update(
            index_elements=[ErrorItem.user_id, ErrorItem.question_id],
            set_={"wrong_count": literal_column("error_items.wrong_count + 1"), "last_attempt_id": a.id,
                  "last_wrong_at": now, "resolved_at": None}))
    if right:
        db.session.execute(db.update(ErrorItem).where(ErrorItem.user_id == a.user_id, ErrorItem.question_id.in_(right),
                                                      ErrorItem.resolved_at.is_(None)).values(resolved_at=now))
