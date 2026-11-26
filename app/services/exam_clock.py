"""Attestatsiya testi vaqti: serverda yuritiladi, tugagach test yakunlanadi va berilgan javoblar baholanadi.

- deadline_at — tugash vaqti. «To'xtatish» bosilganda qolgan soniya settings_snapshot["left"] ga yoziladi va deadline_at
  bo'shaydi; davom ettirilganda qaytadan hisoblanadi. Pauza internet bilan: aks holda server vaqtni to'xtatmaydi.
- Vaqt tugagach test GRACE soniyadan keyin yopiladi (oxirgi javob yo'lda bo'lishi mumkin): fon vazifasi (tasks.exam_end),
  u ishlamasa — foydalanuvchi test sahifalarini ochganda.
- Oflayn berilgan javob kech kelsa ham hisobga olinadi: u vaqt tugamasidan belgilangan bo'lsa va natija (kalit) hali
  ko'rilmagan bo'lsa. Faqat javobsiz savol to'ldiriladi, ball faqat oshadi.
- Qurilma soati noto'g'ri bo'lishi mumkin: so'rovda qurilma vaqti ham keladi, farqi (skew) hisobga olinadi.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from ..extensions import db
from ..models import ErrorItem, QuestionStat, TestAttempt
from . import attempts as at
from . import scoring

GRACE = 60
SLACK_MS = 5000             # tugash paytidagi javob uchun


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_paused(a: TestAttempt) -> bool:
    return "left" in a.settings_snapshot


def left(a: TestAttempt) -> int:
    """Qolgan soniya."""
    if is_paused(a):
        return int(a.settings_snapshot["left"])
    return max(0, round((a.deadline_at - _now()).total_seconds())) if a.deadline_at else 0


def overdue(a: TestAttempt) -> bool:
    return (a.kind == "exam" and a.status == "in_progress" and a.deadline_at is not None
            and _now() >= a.deadline_at + timedelta(seconds=GRACE))


def schedule(a: TestAttempt) -> None:
    """Commit qilmaydi."""
    from . import jobs
    jobs.add("exam_end", {"id": a.id}, key=f"exam:{a.id}", delay=left(a) + GRACE + 1)


def pause(a: TestAttempt) -> bool:
    """a — qulflangan qator. Vaqti tugagan test to'xtatilmaydi."""
    if a.kind != "exam" or a.status != "in_progress" or is_paused(a) or not left(a):
        return False
    a.settings_snapshot, a.deadline_at = {**a.settings_snapshot, "left": left(a)}, None
    db.session.commit()
    return True


def resume(a: TestAttempt) -> bool:
    if a.status != "in_progress" or not is_paused(a):
        return False
    snap = dict(a.settings_snapshot)
    a.deadline_at = _now() + timedelta(seconds=snap.pop("left"))
    a.settings_snapshot = snap
    schedule(a)
    db.session.commit()
    return True


def close(a: TestAttempt) -> bool:
    """Vaqti tugagan bo'lsa yakunlaydi (a — qulflangan qator)."""
    if not overdue(a):
        return False
    a.settings_snapshot = {**a.settings_snapshot, "timeout": True}
    at.finish(a, ended=a.deadline_at)
    return True


def close_by_id(attempt_id: int) -> bool:
    a = db.session.scalar(select(TestAttempt).where(TestAttempt.id == attempt_id).with_for_update()
                          .execution_options(populate_existing=True))
    return a is not None and close(a)


def close_all(user_id: int | None = None) -> int:
    """Vaqti tugagan attestatsiya testlari (bitta foydalanuvchiniki yoki hammasi)."""
    q = select(TestAttempt.id).where(TestAttempt.kind == "exam", TestAttempt.status == "in_progress",
                                     TestAttempt.deadline_at <= _now() - timedelta(seconds=GRACE))
    ids = list(db.session.scalars(q.where(TestAttempt.user_id == user_id) if user_id is not None else q))
    return sum(close_by_id(i) for i in ids)


# ---------------- Javob vaqti ----------------

def in_time(a: TestAttempt, answers: list[dict], skew_ms: int) -> list[dict]:
    """Vaqt tugaguncha belgilangan javoblar."""
    if a.kind != "exam" or a.deadline_at is None or _now() <= a.deadline_at:
        return answers
    end = a.deadline_at.timestamp() * 1000 + SLACK_MS
    return [x for x in answers if 0 < x.get("at", 0) + skew_ms <= end]


def accepts_late(a: TestAttempt) -> bool:
    s = a.settings_snapshot
    return a.status == "submitted" and bool(s.get("timeout")) and not s.get("viewed") and a.items_archive is None


def add_late(a: TestAttempt, answers: list[dict]) -> None:
    """Yakunlangandan keyin yetib kelgan oflayn javoblar. Commit qiladi."""
    snaps, by_pos = at._snapshots(a), {i.position: i for i in a.items}
    gone = at.dropped(a)
    for x in answers:
        item = by_pos.get(x["pos"])
        if item is None or item.answer is not None or x.get("v") is None or x["pos"] not in snaps:
            continue
        item.answer, item.time_ms = {"v": x["v"]}, x.get("t") or item.time_ms
        if x["pos"] in gone:
            continue
        snap = snaps[x["pos"]][0]
        item.score = scoring.grade(snap["type"], snap["answer"], x["v"])
        if item.score == 100:
            db.session.execute(delete(ErrorItem).where(
                ErrorItem.user_id == a.user_id, ErrorItem.question_id == item.question_id, ErrorItem.last_attempt_id == a.id)
                .execution_options(synchronize_session=False))
            db.session.execute(update(QuestionStat).where(QuestionStat.question_id == item.question_id)
                               .values(correct=QuestionStat.correct + 1).execution_options(synchronize_session=False))
    scores = [i.score or 0 for i in a.items if i.position not in gone]
    a.score_pct = max(a.score_pct or 0, float(scoring.percent(scores)))
    a.correct = max(a.correct or 0, sum(scores) / 100)
    a.decision = scoring.decision(int(a.score_pct))
    db.session.commit()


def mark_viewed(a: TestAttempt) -> None:
    """Kalit ko'rsatildi: endi kech kelgan javob qabul qilinmaydi."""
    if accepts_late(a):
        a.settings_snapshot = {**a.settings_snapshot, "viewed": True}
        db.session.commit()
