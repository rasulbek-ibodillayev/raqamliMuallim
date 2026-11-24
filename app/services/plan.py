"""Shaxsiy o'quv reja, tayyorlik prognozi va bosh sahifadagi keyingi qadam — bazadagi natijalardan.

Rejaga tasdiqlangan savollari bor, nashr qilingan mavzular kontent tartibida kiradi. Diagnostikada ≥ 90% chiqqan mavzular
(user_topic_progress.flags: "diagnostic", status hali ham o'zlashtirilgan) rejadan chiqariladi.

- Joriy mavzu — hali o'zlashtirilmagan birinchi mavzu; undan keyingilari yopiq (taxminiy sana bilan).
- Har 3 mavzudan keyin — oraliq sinov (majburiy). Uchala mavzu o'zlashtirilgach navbati keladi.
- Oylik test — oxirgi oylik testdan (yoki birinchi testdan) 30 kun o'tgach (majburiy).
- Oraliq yoki oylik test navbati kelgan bo'lsa, hali boshlanmagan keyingi mavzu ochilmaydi (boshlangani tugatiladi).
- Kunlik test — har kuni (majburiy); haftalik — yakshanba, o'zlashtirilgan mavzu bo'lsa (ixtiyoriy).
- Yakuniy diagnostika — barcha mavzular o'zlashtirilgach.

Sanalar: attestatsiya sanasi bo'lsa, qolgan mavzular unga reserve_days kun qolguncha teng taqsimlanadi; bo'lmasa — har
pace_days kunda bitta mavzu (admin sozlamalari: services/settings.py).
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from flask_babel import gettext as _
from sqlalchemy import func, select

from ..extensions import db
from ..models import Section, TestAttempt, Topic, User, UserTopicProgress
from . import catalog
from . import settings as conf
from . import test_builder as tb
from .scoring import PASS_MIN
from .timefmt import TASHKENT, day_month, when
from .timefmt import now as tk_now

INTERIM_EVERY = 3
LESSON_MIN = 10             # topics.est_minutes bo'lmasa, bitta darsga daqiqa
FORECAST_DAYS = 14


@dataclass
class Plan:
    items: list[dict] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)          # rejadagi mavzular (items ichidagilar bilan bir xil dict)
    excluded: list[dict] = field(default_factory=list)
    current: dict | None = None
    blocker: dict | None = None                               # navbati kelgan oraliq/oylik test keyingi mavzuni to'sib turibdi
    daily: dict | None = None
    monthly: dict | None = None
    final: dict | None = None
    interims: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    has_results: bool = False                                  # dars yoki mavzu testi topshirilgan


def _attempts(user_id: int):
    """Foydalanuvchining barcha yakunlangan va boshlangan urinishlari (eskisidan)."""
    return db.session.execute(
        select(TestAttempt.id, TestAttempt.kind, TestAttempt.status, TestAttempt.topic_id, TestAttempt.subtopic_id,
               TestAttempt.score_pct, TestAttempt.total, TestAttempt.started_at, TestAttempt.finished_at)
        .where(TestAttempt.user_id == user_id, TestAttempt.status.in_(("submitted", "in_progress")))
        .order_by(TestAttempt.started_at, TestAttempt.id)).all()


def _result(rows) -> dict | None:
    """Shu dars/mavzu bo'yicha urinishlardan eng yaxshisi."""
    if not rows:
        return None
    best = max(rows, key=lambda r: (r.score_pct, r.id))
    return {"pct": int(best.score_pct), "rid": best.id, "when": when(best.finished_at), "n": best.total,
            "tries": len(rows) if len(rows) > 1 else None}


def all_topics() -> list[dict]:
    """Rejaga kirishi mumkin bo'lgan mavzular, tartib bilan: {"id", "name", "section", "est", "lessons"}."""
    lessons = catalog.lessons_by_topic()
    rows = db.session.execute(
        select(Topic.id, Topic.title, Section.title, Topic.est_minutes).join(Section, Section.id == Topic.section_id)
        .where(Topic.is_published.is_(True))
        .order_by(Section.position, Section.id, Topic.position, Topic.id)).all()
    return [{"id": t, "name": n, "section": s, "est": e, "lessons": lessons[t]} for t, n, s, e in rows
            if any(x["testable"] for x in lessons.get(t, []))]


def pace(user: User, remaining: int, today: date) -> float:
    """Bitta mavzuga necha kun."""
    if user.exam_date and remaining:
        days = (user.exam_date - today).days - conf.get("reserve_days")
        return max(days, 1) / remaining
    return float(conf.get("pace_days"))


def build(user: User, *, sunday: bool | None = None) -> Plan:
    today = tk_now().date()
    sunday = today.weekday() == 6 if sunday is None else sunday
    rows = _attempts(user.id)
    done_rows = [r for r in rows if r.status == "submitted"]
    open_kinds = {r.kind for r in rows if r.status == "in_progress"}
    by_lesson, by_topic, by_kind = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in done_rows:
        by_kind[r.kind].append(r)
        if r.kind == "lesson":
            by_lesson[r.subtopic_id].append(r)
        elif r.kind == "topic":
            by_topic[r.topic_id].append(r)
    started = {r.topic_id for r in rows if r.kind in ("lesson", "topic") and r.topic_id}
    progress = {p.topic_id: p for p in db.session.scalars(select(UserTopicProgress).where(UserTopicProgress.user_id == user.id))}

    p = Plan(has_results=bool(by_kind["lesson"] or by_kind["topic"]))
    for t in all_topics():
        pr = progress.get(t["id"])
        mastered = pr is not None and pr.status in tb.MASTERED
        if mastered and "diagnostic" in (pr.flags or []):
            p.excluded.append({"id": t["id"], "name": t["name"], "pct": int(pr.best_pct or 0)})
            continue
        p.topics.append(_topic(t, pr, mastered, by_lesson, by_topic))

    remaining = [t for t in p.topics if t["state"] != "done"]
    step = pace(user, len(remaining), today)
    for k, t in enumerate(remaining):
        t["start"] = today + timedelta(days=math.ceil(k * step))
        t["date"] = day_month(t["start"])
    p.current = remaining[0] if remaining else None
    if p.current:
        p.current["state"] = "current"

    # --- Majburiy va davriy testlar ---
    def test(kind, name, state, **kw):
        return {"kind": "test", "type": kind, "name": name, "state": state, "min": kw.pop("min", 10), **kw}

    def last(kind):
        r = by_kind[kind][-1] if by_kind[kind] else None
        return {"pct": int(r.score_pct), "rid": r.id} if r else {}

    def due_state(kind):
        return "started" if kind in open_kinds else "due"

    groups = [p.topics[i:i + INTERIM_EVERY] for i in range(0, len(p.topics) - INTERIM_EVERY + 1, INTERIM_EVERY)]
    for g, group in enumerate(groups):
        name = _("Oraliq sinov testi: %(a)s–%(b)s mavzular", a=g * INTERIM_EVERY + 1, b=(g + 1) * INTERIM_EVERY)
        n = sum(len(t["lessons"]) for t in group)
        done = by_kind["interim"][g] if g < len(by_kind["interim"]) else None
        ready = all(t["state"] == "done" for t in group)
        if done is not None:
            it = test("interim", name, "done", pct=int(done.score_pct), rid=done.id, min=n)
        elif ready and g == len(by_kind["interim"]):
            it = test("interim", name, due_state("interim"), min=n, note=_("Topshirilmaguncha keyingi mavzu ochilmaydi"))
        else:
            end = max((t["start"] for t in group if t.get("start")), default=today)
            it = test("interim", name, "locked", min=n, date=day_month(end + timedelta(days=math.ceil(step))),
                      note=_("%(n)s-mavzudan keyin", n=(g + 1) * INTERIM_EVERY))
        it["topics"] = group
        p.interims.append(it)

    any_mastered = bool(p.excluded) or any(t["state"] == "done" for t in p.topics)
    anchor = by_kind["monthly"][-1].finished_at if by_kind["monthly"] else (rows[0].started_at if rows else None)
    if anchor is not None and any_mastered:
        next_monthly = anchor.astimezone(TASHKENT).date() + timedelta(days=conf.get("monthly_days"))
        state = due_state("monthly") if next_monthly <= today or "monthly" in open_kinds else "locked"
        p.monthly = test("monthly", _("Oylik test"), state, min=conf.get("monthly_n"), date=day_month(next_monthly),
                         note=_("Har %(n)s kunda · topshirilmaguncha keyingi mavzular ochilmaydi", n=conf.get("monthly_days")))

    last_daily = by_kind["daily"][-1] if by_kind["daily"] else None
    daily_done = last_daily is not None and last_daily.finished_at.astimezone(TASHKENT).date() == today
    p.daily = test("daily", _("Kunlik test"), "done" if daily_done else due_state("daily"), min=conf.get("daily_n"),
                   note=_("Ko‘p xato qilayotgan mavzulardan"), **(last("daily") if daily_done else {}))

    weekly = None
    last_weekly = by_kind["weekly"][-1] if by_kind["weekly"] else None
    weekly_done = last_weekly is not None and last_weekly.finished_at.astimezone(TASHKENT).date() == today
    if any_mastered and (sunday or "weekly" in open_kinds or weekly_done):
        weekly = test("weekly", _("Haftalik test"), "done" if weekly_done else due_state("weekly"), min=conf.get("weekly_n"),
                      note=_("O‘zlashtirilgan mavzulardan"), **(last("weekly") if weekly_done else {}))

    if p.topics or p.excluded:
        everything = not remaining
        fin_date = today + timedelta(days=math.ceil(len(remaining) * step))
        if by_kind["final"]:
            p.final = test("final", _("Yakuniy diagnostika"), "done", min=90, **last("final"))
        else:
            p.final = test("final", _("Yakuniy diagnostika"), due_state("final") if everything else "locked", min=90,
                           date=day_month(fin_date), note=_("Barcha mavzular o‘zlashtirilgach. Natijasi bo‘yicha sertifikat beriladi"))

    # --- Keyingi mavzuni to'sadigan test ---
    waiting = [t for t in [*p.interims, p.monthly] if t and t["state"] in ("due", "started")]
    if p.current and waiting and p.current["id"] not in started:
        p.blocker = waiting[0]
        p.current["state"] = "locked"
        p.current["note"] = _("«%(t)s» topshirilgach ochiladi", t=p.blocker["name"])
    elif not p.current and waiting:
        p.blocker = waiting[0]

    _assemble(p, weekly)
    _summary(p, user, today, step, remaining)
    return p


def _topic(t, pr, mastered, by_lesson, by_topic) -> dict:
    est = t["est"] or LESSON_MIN * len(t["lessons"])
    each = max(2, round(est / len(t["lessons"])))
    lessons = []
    for x in t["lessons"]:
        r = _result(by_lesson.get(x["id"])) or {"pct": None, "rid": None, "when": None, "n": tb.LESSON_N, "tries": None}
        lessons.append({**x, **r, "min": each, "ok": not x["testable"] or (r["pct"] is not None and r["pct"] >= PASS_MIN)})
    ok = sum(1 for x in lessons if x["ok"])
    left = len(lessons) - ok
    return {"kind": "topic", "id": t["id"], "name": t["name"], "section": t["section"], "lessons": lessons,
            "state": "done" if mastered else "locked", "relearn": pr is not None and pr.status == "relearn",
            "pct": int(pr.best_pct) if pr and pr.best_pct is not None else (0 if mastered else None),
            "passed": ok, "read": round(100 * ok / len(lessons)), "min": each * left + 2 * len(lessons) if left else 2 * len(lessons),
            "total_min": est, "test": _result(by_topic.get(t["id"])), "has_lesson": any(x["has_blocks"] for x in lessons)}


def _assemble(p: Plan, weekly) -> None:
    extra = [t for t in (p.daily if p.topics else None, weekly) if t]
    if p.monthly and p.monthly["state"] != "locked":
        extra.append(p.monthly)
    placed = False
    for i, t in enumerate(p.topics):
        p.items.append(t)
        if t is p.current:
            p.items += extra
            placed = True
        if (i + 1) % INTERIM_EVERY == 0:
            p.items.append(p.interims[i // INTERIM_EVERY])
    if not placed:
        p.items += extra
    if p.final:
        p.items.append(p.final)


def _summary(p: Plan, user: User, today: date, step: float, remaining: list[dict]) -> None:
    done = [t for t in p.topics if t["state"] == "done"]
    pcts = [t["pct"] for t in done] + [x["pct"] for x in p.excluded]
    total = len(p.topics) + len(p.excluded)
    nxt = next((t for t in p.interims if t["state"] != "done"), None)
    if nxt is None:
        control = "—"
    elif nxt["state"] in ("due", "started"):
        control = _("Navbati keldi")
    else:
        control = _("%(n)s mavzu", n=sum(1 for t in nxt["topics"] if t["state"] != "done"))
    if not remaining:
        per_day = "—"
    elif step <= 1:
        per_day = _("≈ %(n)s mavzu", n=f"{round(1 / step, 1):g}")
    else:
        per_day = _("%(n)s kunda 1 mavzu", n=f"{round(step, 1):g}")
    p.summary = {"done": len(done) + len(p.excluded), "total": total, "avg": round(sum(pcts) / len(pcts)) if pcts else 0,
                 "days_left": max(0, (user.exam_date - today).days) if user.exam_date else None,
                 "exam": day_month(user.exam_date) if user.exam_date else None, "per_day": per_day, "next_control": control}


def interim_topics(user_id: int) -> list[int] | None:
    """Navbati kelgan oraliq sinov mavzulari (test_builder uchun); navbat kelmagan bo'lsa None."""
    p = build(db.session.get(User, user_id))
    it = next((t for t in p.interims if t["state"] in ("due", "started")), None)
    return [t["id"] for t in it["topics"]] if it else None


# ---------------- Tayyorlik va prognoz ----------------

def readiness(user: User, p: Plan) -> dict:
    """Tayyorlik: mavzular bo'yicha o'rtacha (o'zlashtirilgani — eng yaxshi foizi, boshqasi — o'tilgan darslarining yarmi).
    Prognoz: so'nggi 14 kunda mavzu testidan o'tilgan mavzular sur'ati bo'yicha."""
    today = tk_now().date()
    scores = [x["pct"] for x in p.excluded] + [t["pct"] if t["state"] == "done" else t["read"] / 2 for t in p.topics]
    pct = round(sum(scores) / len(scores)) if scores else 0
    left = sum(1 for t in p.topics if t["state"] != "done")
    passed = db.session.scalar(
        select(func.count(func.distinct(TestAttempt.topic_id)))
        .where(TestAttempt.user_id == user.id, TestAttempt.kind == "topic", TestAttempt.status == "submitted",
               TestAttempt.score_pct >= PASS_MIN, TestAttempt.finished_at >= tk_now() - timedelta(days=FORECAST_DAYS)))
    exam, days_left = user.exam_date, p.summary["days_left"]
    ready = today + timedelta(days=math.ceil(left / (passed / FORECAST_DAYS))) if left and passed else (today if not left else None)
    margin = (exam - ready).days if exam and ready else None
    if ready is None or not p.topics and not p.excluded:
        state = "none"
    elif margin is None:
        state = "free"
    else:
        state = "ok" if margin >= 2 else ("risk" if margin >= 0 else "late")
    pos = min(100, round(100 * (ready - today).days / days_left)) if ready and days_left else None
    return {"pct": pct, "state": state, "margin_days": margin, "forecast": day_month(ready) if ready else None,
            "exam": day_month(exam) if exam else None, "days_left": days_left, "pos": pos}


# ---------------- Bosh sahifa ----------------

def next_step(p: Plan) -> dict:
    """Keyingi qadam: {"kind", "label", "title", "sub", "pct", "text", "min", "alert", + havola uchun "topic"/"lesson"/"test"}."""
    if p.blocker:
        b = p.blocker
        return {"kind": "control", "label": _("Majburiy nazorat testini boshlash"), "title": b["name"], "pct": 0, "alert": True,
                "sub": _("3 bosqich: oson → o‘rta → qiyin"), "min": b["min"], "test": b["type"],
                "text": _("Navbatdagi mavzuga o‘tishdan oldin shu test topshiriladi.")}
    t = p.current
    if t is None:
        f = p.final
        if f and f["state"] in ("due", "started"):
            return {"kind": "final", "label": _("Yakuniy diagnostikani boshlash"), "title": f["name"], "pct": 0, "alert": True,
                    "sub": _("Barcha mavzular o‘zlashtirildi"), "min": f["min"], "test": "final",
                    "text": _("Natijasi bo‘yicha sertifikat beriladi.")}
        return {"kind": "finished", "label": _("Natijalarni ko‘rish"), "title": _("Reja bajarildi"), "pct": 100, "alert": False,
                "sub": "", "min": 5, "text": _("Barcha mavzular o‘zlashtirilgan. Bilimingizni haftalik va ixtiyoriy testlar bilan mustahkamlang.")}
    sub = _("%(s)s · %(a)s / %(b)s dars", s=t["section"], a=t["passed"], b=len(t["lessons"]))
    lesson = next((x for x in t["lessons"] if not x["ok"]), None)
    if lesson is None:
        return {"kind": "topic_test", "label": _("Mavzu testini boshlash"), "title": t["name"], "sub": sub, "pct": 100, "alert": False,
                "min": 2 * len(t["lessons"]), "topic": t, "text": _("Barcha darslar o‘tildi. Mavzuni yakunlash uchun mavzu testini topshiring.")}
    tried = lesson["pct"] is not None
    if t["passed"] or tried or t["relearn"]:
        text = (_("«%(n)s» dars testida natija %(p)s%%. Darsni takrorlab, testni qayta topshiring.", n=lesson["name"], p=lesson["pct"])
                if tried else _("Navbatdagi dars — «%(n)s». O‘qib bo‘lgach, dars testini topshiring.", n=lesson["name"]))
        return {"kind": "lesson", "label": _("Darsni davom ettirish"), "title": t["name"], "sub": sub, "pct": t["read"], "alert": False,
                "min": t["min"], "topic": t, "lesson": lesson, "text": text}
    return {"kind": "lesson", "label": _("Keyingi mavzu"), "title": t["name"], "sub": sub, "pct": 0, "alert": False,
            "min": t["min"], "topic": t, "lesson": lesson, "text": _("Yangi mavzu. Birinchi dars — «%(n)s».", n=lesson["name"])}


def today_items(p: Plan) -> list[dict]:
    """Bugungi reja: to'sib turgan test → joriy mavzuning qolgan darslari (4 tagacha) → mavzu testi → kunlik test."""
    out = []
    if p.blocker:
        out.append({"title": p.blocker["name"], "sub": _("Majburiy"), "min": p.blocker["min"], "done": False, "icon": "flag",
                    "test": p.blocker["type"]})
    t = p.current
    if t and t["state"] == "current":
        left = [(i, x) for i, x in enumerate(t["lessons"], 1) if not x["ok"]]
        for i, x in left[:4]:
            out.append({"title": x["name"], "sub": f"{t['name']} · {_('%(n)s-dars', n=i)}", "min": x["min"], "done": False,
                        "icon": "book", "topic": t, "lesson": x})
        if len(left) <= 4:
            out.append({"title": _("Mavzu testi"), "sub": _("Majburiy · %(n)s savol", n=2 * len(t["lessons"])),
                        "min": 2 * len(t["lessons"]), "done": False, "icon": "clipboard", "topic_test": t})
    if p.daily and p.topics:
        out.append({"title": p.daily["name"], "sub": _("Majburiy · ko‘p xato qilayotgan mavzulardan"), "min": p.daily["min"],
                    "done": p.daily["state"] == "done", "icon": "zap", "test": "daily", "rid": p.daily.get("rid")})
    return out


def schedule(p: Plan) -> list[dict]:
    """«Testlar»: majburiy testlar jadvali — navbati kelgani ochiq, qolgani taxminiy sana bilan yopiq."""
    out = []
    if p.daily and p.topics:
        d = p.daily
        out.append({**d, "note": _("Bugungisi topshirildi · ertaga yangisi") if d["state"] == "done" else _("Bugun ochiq")})
    if p.current:
        t = p.current
        ready = t["state"] == "current" and all(x["ok"] for x in t["lessons"])
        out.append({"type": "topic", "name": _("Mavzu testi: %(n)s", n=t["name"]), "state": "due" if ready else "locked",
                    "date": t["date"], "note": "" if ready else _("Mavzu darslari tugagach ochiladi"), "topic_id": t["id"]})
    nxt = next((t for t in p.interims if t["state"] != "done"), None)
    out += [t for t in (nxt, p.monthly, p.final if p.final and p.final["state"] != "done" else None) if t]
    return out
