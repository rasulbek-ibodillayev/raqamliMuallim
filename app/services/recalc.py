"""Natijalarni qayta hisoblash: e'tiroz qabul qilinganda yoki AI savoli ekspertizadan o'tmaganda.

- Natija faqat foydalanuvchi foydasiga o'zgaradi: ball ham, foiz ham pasaymaydi.
- regrade — to'g'ri javob o'zgardi: variantlari bir xil bo'lgan barcha versiyalardagi javoblar yangi kalit bilan baholanadi.
- drop — savol hisobdan chiqariladi: foiz qolgan savollardan hisoblanadi (settings_snapshot["dropped"], ball NULL).
  Shu savolga to'liq to'g'ri javob berganlarda savol qoladi. Testdagi yagona savol chiqarilmaydi.
- Bosqichli testda mavzu endi o'tgan bo'lsa, unga berilmagan yuqori bosqich savollari ham hisobdan chiqariladi (aybi yo'q
  foydalanuvchi ular uchun 0 ball olmasin).
- Yakunlanmagan testlarda hali baholanmagan savol yangi versiyaga o'tadi yoki chiqarib qo'yiladi.
- Arxivlangan urinishlar ham qayta hisoblanadi.
"""
from dataclasses import dataclass

from sqlalchemy import delete, or_, select

from ..extensions import db
from ..models import AttemptItem, ErrorItem, TestAttempt
from . import archive, progress, scoring, seen, versions
from . import attempts as at


@dataclass(frozen=True)
class Change:
    attempt_id: int
    user_id: int
    old: float
    new: float


def _attempts(question_id: int) -> list[TestAttempt]:
    """Savol tushgan urinishlar (qulflangan). Yakunlanmaganlarda savol keyingi bosqichda turgan bo'lishi ham mumkin."""
    has = TestAttempt.items.any(AttemptItem.question_id == question_id)
    return list(db.session.scalars(
        select(TestAttempt).where(or_(
            (TestAttempt.status == "in_progress") & has,
            (TestAttempt.status == "submitted") & TestAttempt.user_id.in_(seen.given_to(question_id))
            & or_(archive.may_have(question_id), has)))
        .order_by(TestAttempt.id).with_for_update().execution_options(populate_existing=True)))


def _walk(question_id: int):
    """(urinish, hamma qatorlari, shu savol qatori)."""
    for a in _attempts(question_id):
        items = archive.rows(a)
        item = next((i for i in items if i.question_id == question_id), None)
        if item is not None:
            yield a, items, item


def regrade(question_id: int, answer: dict, qtype: str, data: dict, version: int | None = None) -> list[Change]:
    """answer — yangi kalit; data — variantlar (boshqa variantli versiyalarga tegilmaydi); version — yangi versiya raqami.
    Commit qilmaydi."""
    old = versions.all_of(question_id)
    keys = ("options", "left", "right")
    same = {v for v, s in old.items() if s.get("type") == qtype
            and all((s.get("data") or {}).get(k) == (data or {}).get(k) for k in keys)}
    out = []
    for a, items, item in _walk(question_id):
        if item.question_version not in same:
            continue
        if item.score is None:
            if version and a.status == "in_progress":
                item.question_version = version
            continue
        new = scoring.grade(qtype, answer, (item.answer or {}).get("v"))
        if new < item.score:
            continue                                     # eski kalit bo'yicha to'g'ri edi: natijasi va versiyasi qoladi
        item.question_version = version or item.question_version
        if new > item.score:
            item.score = new
            _apply(a, items, out, resolved=question_id if new == 100 else None)
        elif a.items_archive is not None:
            a.items_archive = archive.pack(items)
    db.session.flush()
    return out


def drop(question_id: int) -> list[Change]:
    """Savolni barcha natijalardan chiqaradi. Commit qilmaydi. Natija: yakunlangan urinishlar (o'zgarmaganlari ham)."""
    out = []
    for a, items, item in _walk(question_id):
        dropped = set(a.settings_snapshot.get("dropped", []))
        if item.position in dropped or len(items) - len(dropped) < 2:
            continue
        if item.score == 100:
            if a.status == "submitted":
                out.append(Change(a.id, a.user_id, a.score_pct, a.score_pct))
            continue
        item.score = None
        a.settings_snapshot = {**a.settings_snapshot, "dropped": sorted({*dropped, item.position})}
        _apply(a, items, out, resolved=question_id)
    db.session.flush()
    return out


def _apply(a: TestAttempt, items: list, out: list[Change], resolved: int | None) -> None:
    if a.status != "submitted":
        return
    snaps = at._snapshots(a, items)
    if at.is_staged(a):
        _restage(a, items, snaps)
    dropped = set(a.settings_snapshot.get("dropped", []))
    scores = [i.score or 0 for i in items if i.position not in dropped]
    old = a.score_pct
    a.score_pct = max(old, float(scoring.percent(scores)))
    a.correct = max(a.correct or 0, sum(scores) / 100)
    a.decision = scoring.decision(int(a.score_pct))
    if a.items_archive is not None:
        a.items_archive = archive.pack(items)
    if resolved:
        db.session.execute(delete(ErrorItem).where(ErrorItem.user_id == a.user_id, ErrorItem.question_id == resolved)
                           .execution_options(synchronize_session=False))
    db.session.flush()
    progress.upgrade(a, items, snaps, old)
    out.append(Change(a.id, a.user_id, old, a.score_pct))


def _restage(a: TestAttempt, items: list, snaps: dict) -> None:
    """Bosqichlar xulosasi yangi ballar bilan: o'tgan mavzular failed_topics'dan chiqadi."""
    cfg = a.settings_snapshot
    skipped, dropped = set(cfg.get("skipped", [])), set(cfg.get("dropped", []))
    by_pos = {i.position: i for i in items}
    failed, advise = set(), {}
    for s in cfg["stages"]:
        positions = [p for p in range(s["from"], s["to"]) if p not in skipped and p not in dropped]
        f, adv = at._stage_verdict(a, snaps, positions, by_pos)
        failed |= f
        advise |= adv
    failed &= set(cfg["failed_topics"])
    passed = set(cfg["failed_topics"]) - failed
    dropped |= {p for p in skipped if p in snaps and snaps[p][2] in passed}
    topic_of = {str(sid): tid for _s, sid, tid in snaps.values()}
    a.settings_snapshot = {**cfg, "failed_topics": sorted(failed), "dropped": sorted(dropped),
                           "recommended": {s: p for s, p in advise.items() if topic_of[s] not in failed}}
