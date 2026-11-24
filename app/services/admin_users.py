"""Admin: o'qituvchilar ro'yxati, to'liq kartasi, amallar, CSV eksport va attestatsiya sanalarini Excel'dan yuklash.

Faqat role = "user": ekspert va adminlar bu yerdan boshqarilmaydi. Har bir amal audit_log'da (shaxsiy ma'lumotsiz).
"""
import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from flask_babel import gettext as _
from sqlalchemy import func, or_, select, update

from ..extensions import db
from ..forms import fmt_phone, norm_phone
from ..models import (AuditLog, Certificate, ErrorItem, Objection, Question, Section, Subtopic, TestAttempt, Topic, User,
                      UserTopicProgress)
from . import notify
from .test_builder import MASTERED
from .timefmt import TASHKENT, now, when

PAGE = 25
EXPORT_MAX = 20_000


def log(actor_id: int, action: str, entity: str, entity_id, data: dict | None = None) -> None:
    from flask import has_request_context, request
    db.session.add(AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=str(entity_id), data=data or {},
                            ip=request.remote_addr if has_request_context() else None))


# ---------------- Ro'yxat ----------------

@dataclass
class Filters:
    q: str = ""
    viloyat: str = ""
    sana: str = ""       # yoq / oy / otgan
    holat: str = ""      # faol / blok

    @classmethod
    def from_args(cls, args):
        return cls(**{k: (args.get(k) or "").strip()[:100] for k in cls.__dataclass_fields__})


def _query(f: Filters):
    q = select(User).where(User.role == "user")
    if f.q:
        like = "%" + f.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        digits = "".join(c for c in f.q if c.isdigit())
        q = q.where(or_((User.first_name + " " + User.last_name).ilike(like, escape="\\"),
                        (User.last_name + " " + User.first_name).ilike(like, escape="\\"), User.email.ilike(like, escape="\\"),
                        *([User.phone.like(f"%{digits}%")] if len(digits) >= 3 else [])))
    if f.viloyat:
        q = q.where(User.region == f.viloyat)
    today = now().date()
    if f.sana == "yoq":
        q = q.where(User.exam_date.is_(None))
    elif f.sana == "oy":
        q = q.where(User.exam_date.between(today, today + timedelta(days=30)))
    elif f.sana == "otgan":
        q = q.where(User.exam_date < today)
    if f.holat in ("faol", "blok"):
        q = q.where(User.is_active.is_(f.holat == "faol"))
    return q


def total_topics() -> int:
    from .plan import all_topics
    return len(all_topics())


def _mastered(user_ids) -> dict[int, int]:
    return dict(db.session.execute(select(UserTopicProgress.user_id, func.count()).where(
        UserTopicProgress.user_id.in_(user_ids), UserTopicProgress.status.in_(MASTERED)).group_by(UserTopicProgress.user_id)).all())


def contact(u: User) -> str:
    return fmt_phone(u.phone) if u.phone else (u.email or "—")


def initials(u: User) -> str:
    return (u.first_name[:1] + u.last_name[:1]).upper()


def listing(f: Filters, page: int) -> dict:
    base = _query(f)
    total = db.session.scalar(select(func.count()).select_from(base.subquery()))
    pages = max(1, -(-total // PAGE))
    page = min(max(1, page), pages)
    rows = list(db.session.scalars(base.order_by(User.last_seen_at.desc().nulls_last(), User.id).offset((page - 1) * PAGE).limit(PAGE)))
    done = _mastered([u.id for u in rows])
    return {"total": total, "page": page, "pages": pages, "first": (page - 1) * PAGE + 1 if total else 0,
            "last": min(page * PAGE, total),
            "rows": [{"id": u.id, "name": u.full_name, "ini": initials(u), "contact": contact(u), "region": u.region or "—",
                      "done": done.get(u.id, 0), "last": when(u.last_seen_at) or "—", "active": u.is_active, "exam": u.exam_date}
                     for u in rows]}


def counts() -> dict:
    n, active = db.session.execute(select(func.count(), func.count().filter(User.is_active.is_(True))).where(User.role == "user")).one()
    return {"all": n, "active": active, "blocked": n - active}


def teacher(user_id: int) -> User | None:
    u = db.session.get(User, user_id)
    return u if u is not None and u.role == "user" else None


# ---------------- Karta ----------------

def card(u: User) -> dict:
    """O'qituvchining to'liq ma'lumoti: tayyorlik, mavzular, testlar, xatolar, e'tirozlar, so'nggi harakatlar."""
    from ..views.test import type_names
    from . import attempts as at
    from . import plan as pl
    p = pl.build(u)
    progress = {t.topic_id: t for t in db.session.scalars(select(UserTopicProgress).where(UserTopicProgress.user_id == u.id))}
    sections: dict[str, list] = {}
    for t in pl.all_topics():
        pr = progress.get(t["id"])
        sections.setdefault(t["section"], []).append({"name": t["name"], "status": pr.status if pr else "none",
                                                      "pct": round(pr.best_pct) if pr and pr.best_pct is not None else None})
    n, avg = db.session.execute(select(func.count(), func.avg(TestAttempt.score_pct)).where(
        TestAttempt.user_id == u.id, TestAttempt.status == "submitted")).one()
    results = at.finished(u.id, limit=10)
    names = at.names(results, type_names())
    weak = db.session.execute(
        select(Subtopic.title, Topic.title, func.count()).join(Topic, Topic.id == Subtopic.topic_id)
        .join(ErrorItem, ErrorItem.subtopic_id == Subtopic.id).where(ErrorItem.user_id == u.id)
        .group_by(Subtopic.id, Topic.title).order_by(func.count().desc()).limit(5)).all()
    objections = db.session.execute(
        select(Question.text, Objection.status, Objection.created_at).join(Question, Question.id == Objection.question_id)
        .where(Objection.user_id == u.id).order_by(Objection.created_at.desc()).limit(5)).all()
    events = [(a.finished_at, _("Test topshirildi"), f"{names[a.id]} · {int(a.score_pct)}%") for a in results]
    events += [(t, _("E’tiroz yuborildi"), text[:80]) for text, _st, t in objections]
    events.append((u.created_at, _("Ro‘yxatdan o‘tdi"), ""))
    mastered = sum(1 for s in progress.values() if s.status in MASTERED)
    return {"id": u.id, "name": u.full_name, "ini": initials(u), "contact": contact(u), "phone": fmt_phone(u.phone) if u.phone else None,
            "email": u.email, "region": u.region, "active": u.is_active, "exam": u.exam_date,
            "auth": [k for k, v in (("Parol", u.password_hash), ("Telegram", u.telegram_id), ("Google", u.google_sub)) if v],
            "registered": when(u.created_at), "last": when(u.last_seen_at) or "—",
            "readiness": pl.readiness(u, p)["pct"], "done": mastered, "topics": sum(len(x) for x in sections.values()),
            "tests": n, "avg": round(avg) if avg is not None else None,
            "sections": [{"name": s, "topics": ts, "pct": round(100 * sum(t["status"] in MASTERED for t in ts) / len(ts))}
                         for s, ts in sections.items()],
            "weak": [(sub, top, k) for sub, top, k in weak],
            "results": [{"name": names[a.id], "when": when(a.finished_at), "pct": int(a.score_pct), "decision": a.decision} for a in results],
            "objections": [{"q": text, "state": st, "when": when(t)} for text, st, t in objections],
            "activity": [(when(t), what, sub) for t, what, sub in sorted(events, key=lambda e: e[0], reverse=True)[:8]]}


# ---------------- Amallar ----------------

def set_active(u: User, active: bool, actor_id: int) -> None:
    u.is_active = active
    log(actor_id, "unblock" if active else "block", "user", u.id)
    db.session.commit()


def set_exam_date(u: User, day: date | None, actor_id: int, tell: bool) -> None:
    """Commit qilmaydi."""
    if u.exam_date == day:
        return
    log(actor_id, "exam_date", "user", u.id, {"old": str(u.exam_date) if u.exam_date else None, "new": str(day) if day else None})
    u.exam_date = day
    if tell and day:
        notify.add(u.id, notify.EXAM_DATE, day.toordinal())


def delete_account(u: User, actor_id: int) -> int:
    """Akkauntni butunlay o'chiradi (bog'liq ma'lumotlar CASCADE). Faqat sertifikatlari qoladi: ular akkauntdan uziladi
    (SET NULL). Natija — saqlangan sertifikatlar soni."""
    uid = u.id
    kept = db.session.scalar(select(func.count()).select_from(Certificate).where(Certificate.user_id == uid))
    db.session.execute(update(AuditLog).where(AuditLog.actor_id == uid).values(ip=None).execution_options(synchronize_session=False))
    log(actor_id, "delete", "user", uid)
    db.session.flush()
    db.session.execute(User.__table__.delete().where(User.id == uid))
    db.session.expunge(u)
    db.session.commit()
    return kept


# ---------------- CSV va Excel ----------------

def _safe(v) -> str:
    """Excel formulasi bo'lib ishlab ketmasin (CSV injection)."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def to_csv(rows) -> bytes:
    """Excel uchun: UTF-8 BOM, «;» ajratuvchi."""
    out = io.StringIO()
    csv.writer(out, delimiter=";", lineterminator="\r\n").writerows([_safe(c) for c in r] for r in rows)
    return ("﻿" + out.getvalue()).encode()


def export(f: Filters) -> bytes:
    users = list(db.session.scalars(_query(f).order_by(User.id).limit(EXPORT_MAX)))
    done, total = _mastered([u.id for u in users]), total_topics()
    local = lambda t: t.astimezone(TASHKENT).strftime("%d.%m.%Y") if t else ""                   # noqa: E731
    rows = [[_("Familiya"), _("Ism"), _("Telefon"), _("Email"), _("Viloyat"), _("O‘zlashtirgan mavzular"), _("Jami mavzular"),
             _("Attestatsiya sanasi"), _("Ro‘yxatdan o‘tgan"), _("Oxirgi kirish"), _("Holat")]]
    for u in users:
        rows.append([u.last_name, u.first_name, (u.phone or "").lstrip("+"), u.email, u.region, done.get(u.id, 0), total,
                     u.exam_date.strftime("%d.%m.%Y") if u.exam_date else "", local(u.created_at), local(u.last_seen_at),
                     _("Faol") if u.is_active else _("Bloklangan")])
    return to_csv(rows)


DATES_HEAD = ["Telefon yoki email", "Attestatsiya sanasi"]


def dates_sample() -> bytes:
    from . import xlsx
    return xlsx.write([DATES_HEAD, ["998901234567", (now().date() + timedelta(days=60)).strftime("%d.%m.%Y")],
                       ["ism@maktab.uz", (now().date() + timedelta(days=75)).strftime("%d.%m.%Y")]], widths=[28, 22])


def parse_date(v: str) -> date | None:
    """25.12.2026, 2026-12-25 yoki Excel'ning kun raqami (46381)."""
    v = v.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    head = v.split(".")[0]
    if head.isdigit() and 40_000 < int(head) < 80_000:
        return date(1899, 12, 30) + timedelta(days=int(head))
    return None


def import_dates(data: bytes, actor_id: int, tell: bool = True) -> tuple[int, list[str]]:
    """(yangilanganlar soni, xatolar). Bitta xato bo'lsa ham hech narsa yozilmaydi."""
    from . import xlsx
    try:
        rows = xlsx.read_rows(data)
    except xlsx.XlsxError as e:
        return 0, [str(e)]
    if rows and not any(c.isdigit() for c in "".join(rows[0])):
        rows = rows[1:]
        start = 2
    else:
        start = 1
    todo, errors, seen_ids = [], [], set()
    for n, r in enumerate(rows, start=start):
        r = [c.strip() for c in (r + ["", ""])[:2]]
        if not any(r):
            continue
        login = r[0].split(".")[0] if r[0].replace(".", "").isdigit() else r[0]
        u = User.by_login(login if "@" in login else norm_phone(login)) if login else None
        day = parse_date(r[1])
        if u is None or u.role != "user":
            errors.append(_("%(n)s-qator: foydalanuvchi topilmadi", n=n))
        elif day is None or day < now().date():
            errors.append(_("%(n)s-qator: sana noto‘g‘ri yoki o‘tib ketgan", n=n))
        elif u.id in seen_ids:
            errors.append(_("%(n)s-qator: foydalanuvchi faylda ikki marta", n=n))
        else:
            seen_ids.add(u.id)
            todo.append((u, day))
    if not todo and not errors:
        errors = [_("Faylda ma’lumot topilmadi")]
    if errors:
        return 0, errors[:20] + ([_("… yana %(n)s ta xato", n=len(errors) - 20)] if len(errors) > 20 else [])
    for u, day in todo:
        set_exam_date(u, day, actor_id, tell)
    db.session.commit()
    return len(todo), []


def sections() -> list[tuple[int, str]]:
    return [tuple(r) for r in db.session.execute(select(Section.id, Section.title).order_by(Section.position, Section.id))]
