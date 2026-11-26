"""Admin: statistika, ekspertlar faoliyati va amallar jurnali — hammasi bazadan (shaxsiy ma'lumotsiz yig'indilar)."""
from datetime import date, datetime, timedelta, timezone

from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from sqlalchemy import Date, cast, func, select

from ..extensions import db
from ..models import (AuditLog, Certificate, DailyStat, ExpertProfile, Job, Objection, Question, QuestionStat, Section, Subtopic, TestAttempt,
                      Topic, User, UserTopicProgress)
from . import admin_users as au
from . import experts as ex
from . import jobs
from .test_builder import MASTERED
from .timefmt import TASHKENT, moment, now, when

PERIODS = {"7": 7, "30": 30, "90": 90}
SLOW_HOURS = 72             # e'tirozga javob me'yori: 3 ish kuni
HARD_MIN = 20               # «qiyin mavzu» uchun kamida shuncha javob
TEACHER = User.role == "user"


def _count(*where) -> int:
    return db.session.scalar(select(func.count()).select_from(User).where(TEACHER, *where))


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _users_with(*where) -> int:
    return db.session.scalar(select(func.count(TestAttempt.user_id.distinct())).where(TestAttempt.status == "submitted", *where))


def _pct(a, b) -> int:
    return round(100 * a / b) if b else 0


def overview(period: int = 30) -> dict:
    today = now().date()
    total = _count()
    days = {d.day: d for d in db.session.scalars(select(DailyStat).where(DailyStat.day > today - timedelta(days=max(period, 14))))}
    at_ = lambda d: days[d].active if d in days else 0                                           # noqa: E731
    week = sum(at_(today - timedelta(days=i)) for i in range(7))
    before = sum(at_(today - timedelta(days=i)) for i in range(7, 14))
    topics = au.total_topics()
    mastered = db.session.scalar(select(func.count()).select_from(UserTopicProgress).join(User, User.id == UserTopicProgress.user_id)
                                 .where(TEACHER, UserTopicProgress.status.in_(MASTERED)))
    diag, certs = _users_with(TestAttempt.kind == "diagnostic"), db.session.scalar(select(func.count()).select_from(Certificate))
    half = db.session.scalar(select(func.count()).select_from(
        select(UserTopicProgress.user_id).where(UserTopicProgress.status.in_(MASTERED)).group_by(UserTopicProgress.user_id)
        .having(func.count() * 2 >= max(topics, 1)).subquery()))
    tests = db.session.scalar(select(func.count()).select_from(TestAttempt).where(
        TestAttempt.status == "submitted", TestAttempt.finished_at >= _since(period)))
    span = [d for d in days.values() if d.day > today - timedelta(days=period)]
    active = sum(d.active for d in span)
    phone, tablet, pwa = (sum(getattr(d, k) for d in span) for k in ("phone", "tablet", "pwa"))
    return {
        "kpi": [(_("O‘qituvchilar"), total, _("+%(n)s bu hafta", n=_count(User.created_at >= _since(7))), "users"),
                (_("Bugun faol"), at_(today), _("7 kunda %(a)s, oldingi 7 kunda %(b)s", a=week, b=before), "zap"),
                (_("O‘rtacha o‘zlashtirish"), f"{_pct(mastered, total * topics)}%", _("%(n)s ta mavzudan", n=topics), "target"),
                (_("Topshirilgan testlar"), tests, _("oxirgi %(n)s kunda", n=period), "clipboard"),
                (_("Diagnostikani tugatgan"), f"{_pct(diag, total)}%", _("Maqsad ≥ 60%"), "check-circle"),
                (_("Sertifikatlar"), certs, "", "award")],
        "dau": [(today - timedelta(days=i), at_(today - timedelta(days=i))) for i in range(min(period, 14) - 1, -1, -1)],
        "signups": _signups(today),
        "funnel": [(_("Ro‘yxatdan o‘tgan"), total), (_("Diagnostikani tugatgan"), diag),
                   (_("Birinchi dars testini topshirgan"), _users_with(TestAttempt.kind == "lesson")),
                   (_("Birinchi mavzu testini topshirgan"), _users_with(TestAttempt.kind == "topic")),
                   (_("Mavzularning yarmini o‘zlashtirgan"), half), (_("Sertifikat olgan"), certs)],
        "hard": hard_topics(), "regions": _regions(),
        "devices": [(_("Telefon"), _pct(phone, active)), (_("Kompyuter"), _pct(active - phone - tablet, active)),
                    (_("Planshet"), _pct(tablet, active))] if active else [],
        "pwa": _pct(pwa, active), "content": _content(), "inactive": _inactive(), "attention": _attention(total)}


def _signups(today: date) -> list[int]:
    """Oxirgi 12 hafta (7 kunlik), eskisidan."""
    local = cast(func.timezone("Asia/Tashkent", User.created_at), Date)
    rows = db.session.execute(select(local, func.count()).where(TEACHER, User.created_at >= _since(85)).group_by(local)).all()
    out = [0] * 12
    for d, n in rows:
        k = (today - d).days // 7
        if 0 <= k < 12:
            out[11 - k] += n
    return out


def hard_topics() -> list[tuple[str, int]]:
    wrong = func.sum(QuestionStat.answered - QuestionStat.correct)
    rows = db.session.execute(
        select(Topic.title, wrong, func.sum(QuestionStat.answered)).join(Subtopic, Subtopic.topic_id == Topic.id)
        .join(Question, Question.subtopic_id == Subtopic.id).join(QuestionStat, QuestionStat.question_id == Question.id)
        .group_by(Topic.id).having(func.sum(QuestionStat.answered) >= HARD_MIN)
        .order_by((wrong * 1.0 / func.sum(QuestionStat.answered)).desc()).limit(5)).all()
    return [(t, _pct(w, n)) for t, w, n in rows]


def _regions() -> list[tuple[str, int]]:
    rows = db.session.execute(select(User.region, func.count()).where(TEACHER).group_by(User.region).order_by(func.count().desc())).all()
    named = [(r, n) for r, n in rows if r]
    rest = sum(n for _r, n in named[8:])
    none = sum(n for r, n in rows if not r)
    return named[:8] + ([(_("Boshqa viloyatlar"), rest)] if rest else []) + ([(_("Ko‘rsatilmagan"), none)] if none else [])


def response_hours(*where) -> float | None:
    s = db.session.scalar(select(func.avg(func.extract("epoch", Objection.decided_at - Objection.created_at)))
                          .where(Objection.decided_at.is_not(None), *where))
    return float(s) / 3600 if s is not None else None


def hours(h: float | None) -> str:
    if h is None:
        return "—"
    return _("1 soatdan kam") if h < 1 else (_("%(n)s soat", n=round(h)) if h < 72 else _("%(n)s kun", n=round(h / 24)))


def _content() -> list[tuple]:
    st = dict(db.session.execute(select(Question.status, func.count()).group_by(Question.status)).all())
    tpl = db.session.scalar(select(func.count()).select_from(Question).where(Question.source == "template"))
    opened = db.session.scalar(select(func.count()).select_from(Objection).where(Objection.status == "review"))
    return [(_("Tasdiqlangan savollar"), st.get("approved", 0)), (_("shundan shablon savollari"), tpl),
            (_("Tekshiruvda"), st.get("review", 0)), (_("To‘xtatilgan"), st.get("paused", 0)),
            (_("Ochiq e’tirozlar"), opened), (_("E’tirozga o‘rtacha javob"), hours(response_hours()))]


def _inactive() -> list[tuple]:
    seen = func.coalesce(User.last_seen_at, User.created_at)
    return [(_("3–6 oy kirmagan"), _count(seen < _since(90), seen >= _since(183))),
            (_("O‘chirishga 2 haftadan kam qolgan"), _count(seen < _since(169), seen >= _since(183))),
            (_("6 oydan beri kirmagan"), _count(seen < _since(183)))]


def _attention(total: int) -> list[dict]:
    out = []
    if not jobs.worker_alive():
        out.append({"url": "admin.jobs", "icon": "alert", "cls": "t-red", "title": _("Fon jarayoni ishlamayapti"),
                    "sub": _("Tozalash, arxiv va xabarlar navbatda turibdi")})
    if n := jobs.failed():
        out.append({"url": "admin.jobs", "icon": "refresh", "cls": "t-red", "title": _("%(n)s ta fon vazifasi xato bilan to‘xtadi", n=n),
                    "sub": _("Sababini ko‘rib, qayta ishga tushiring")})
    late = db.session.scalar(select(func.count()).select_from(Objection).where(
        Objection.status == "review", Objection.created_at < datetime.now(timezone.utc) - timedelta(hours=SLOW_HOURS)))
    if late:
        out.append({"url": "admin.experts", "icon": "shield", "cls": "t-yellow", "title": _("%(n)s ta e’tiroz 3 kundan beri javobsiz", n=late),
                    "sub": _("Ekspertlar faoliyatini tekshiring")})
    queue = db.session.scalar(select(func.count()).select_from(Question).where(Question.status == "review", Question.source == "ai"))
    if queue:
        out.append({"url": "admin.experts", "icon": "sparkle", "cls": "t-blue", "title": _("%(n)s ta AI savoli tekshiruv kutmoqda", n=queue),
                    "sub": _("Tasdiqlanmagan savol hammaga berilmaydi")})
    nodate = _count(User.exam_date.is_(None), User.is_active.is_(True))
    if nodate:
        out.append({"url": "admin.users", "args": {"sana": "yoq"}, "icon": "calendar", "cls": "t-red",
                    "title": _("%(n)s ta foydalanuvchida attestatsiya sanasi kiritilmagan", n=nodate),
                    "sub": _("Reja standart sur’atda tuziladi, prognoz sanasiz hisoblanmaydi")})
    return out


def report(period: int) -> bytes:
    s = overview(period)
    rows = [[_("Ko‘rsatkich"), _("Qiymat"), _("Izoh")], *[[a, b, c] for a, b, c, _ic in s["kpi"]], []]
    for title, data in ((_("Kunlik faol"), [(d.strftime("%d.%m.%Y"), n) for d, n in s["dau"]]), (_("O‘quv voronkasi"), s["funnel"]),
                        (_("Eng qiyin mavzular, xato %"), s["hard"]), (_("Hududlar"), s["regions"]), (_("Qurilmalar, %"), s["devices"]),
                        (_("Kontent holati"), s["content"]), (_("Faol bo‘lmagan akkauntlar"), s["inactive"])):
        rows += [[title], *[[a, b] for a, b in data], []]
    return au.to_csv(rows)


# ---------------- Ekspertlar ----------------

def expert_rows() -> list[dict]:
    users = list(db.session.scalars(select(User).where(User.role == "expert").order_by(User.is_active.desc(), User.id)))
    made = dict(db.session.execute(select(Question.author_id, func.count()).where(Question.author_id.is_not(None)).group_by(Question.author_id)).all())
    seen = dict(db.session.execute(select(Question.reviewer_id, func.count()).where(Question.reviewer_id.is_not(None)).group_by(Question.reviewer_id)).all())
    obj = {e: (n, float(s) / 3600) for e, n, s in db.session.execute(
        select(Objection.expert_id, func.count(), func.avg(func.extract("epoch", Objection.decided_at - Objection.created_at)))
        .where(Objection.expert_id.is_not(None), Objection.decided_at.is_not(None)).group_by(Objection.expert_id))}
    rights = {p.user_id: p for p in db.session.scalars(select(ExpertProfile))}
    titles = dict(au.sections())
    out = []
    for u in users:
        p, (n, h) = rights.get(u.id), obj.get(u.id, (0, None))
        areas = [a for a in (p.areas if p else []) if a in titles]
        out.append({"id": u.id, "name": u.full_name, "ini": au.initials(u), "contact": au.contact(u), "active": u.is_active,
                    "last": when(u.last_seen_at) or "—", "area_ids": areas, "areas": [titles[a] for a in areas],
                    "perms": list(p.perms) if p else list(ex.PERMS), "created": made.get(u.id, 0), "reviewed": seen.get(u.id, 0),
                    "objections": n, "resp": hours(h), "slow": h is not None and h > SLOW_HOURS})
    return out


def expert_summary() -> dict:
    month = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    opened, urgent = db.session.execute(select(func.count(), func.count().filter(Objection.urgent.is_(True)))
                                        .where(Objection.status == "review")).one()
    return {"queue": db.session.scalar(select(func.count()).select_from(Question).where(Question.status == "review")),
            "open": opened, "urgent": urgent, "resp": hours(response_hours(Objection.decided_at >= _since(30))),
            "approved": db.session.scalar(select(func.count()).select_from(Question).where(
                Question.status == "approved", Question.source != "template",
                func.coalesce(Question.reviewed_at, Question.created_at) >= month))}


# ---------------- Fon vazifalari ----------------

def _job_result(r: dict | None) -> str:
    if not r:
        return ""
    parts = [_("%(n)s ta", n=r["n"])] if "n" in r else []
    if r.get("kb"):
        parts.append(f"{r['kb']} KB")
    if "ms" in r:
        parts.append(_("%(n)s soniya", n=f"{r['ms'] / 1000:.1f}"))
    return " · ".join(parts)


def job_rows() -> dict:
    """Jadvaldagi vazifalar, to'xtab qolganlari va navbatdagilar soni."""
    tasks = jobs.load_tasks()
    rows = list(db.session.scalars(select(Job).where(Job.key.like("cron:%") | Job.run_at.is_(None)).order_by(Job.id)))
    view = lambda j: {"id": j.id, "label": tasks[j.kind].label if j.kind in tasks else j.kind, "done": when(j.done_at) or "—",   # noqa: E731
                      "next": moment(j.run_at), "error": j.error, "result": _job_result(j.result), "dead": j.run_at is None}
    cron = [view(j) for j in rows if j.key and j.key.startswith("cron:") and j.run_at is not None]
    dead = [view(j) for j in rows if j.run_at is None]
    waiting = db.session.scalar(select(func.count()).select_from(Job).where(
        Job.run_at.is_not(None), func.coalesce(Job.key, "").not_like("cron:%")))
    return {"cron": cron, "dead": dead, "waiting": waiting, "alive": jobs.worker_alive()}


# ---------------- Jurnal ----------------

JOURNAL_PAGE = 50
ENTITIES = {"question": _l("Savol"), "user": _l("Foydalanuvchi"), "expert": _l("Ekspert"), "invite": _l("Taklifnoma"),
            "setting": _l("Sozlama"), "job": _l("Fon vazifasi"), "section": _l("Mavzu"), "topic": _l("Dars")}
ACTIONS = {"create": _l("yaratildi"), "update": _l("o‘zgartirildi"), "delete": _l("o‘chirildi"), "archive": _l("arxivlandi"),
           "reject": _l("rad etildi"), "pause": _l("to‘xtatildi"), "resume": _l("qaytarildi"), "block": _l("bloklandi"),
           "unblock": _l("blokdan chiqarildi"), "exam_date": _l("attestatsiya sanasi"), "reset_link": _l("parol havolasi berildi"),
           "reset_used": _l("parol havola orqali yangilandi"), "password_reset": _l("parol tiklandi"), "run": _l("qo‘lda ishga tushirildi"), "perms": _l("huquqlari o‘zgardi"), "send": _l("tayyorlandi"), "export": _l("CSV yuklab olindi"),
           "resend": _l("qayta yuborildi"), "cancel": _l("bekor qilindi"), "import_excel": _l("Excel’dan yuklandi"),
           "objection_key": _l("e’tiroz: javob o‘zgardi"), "objection_drop": _l("e’tiroz: hisobdan chiqarildi"),
           "objection_fix": _l("e’tiroz: matn tuzatiladi"), "objection_reject": _l("e’tiroz: rad etildi")}


def journal(entity: str, page: int) -> dict:
    q = select(AuditLog, User.first_name, User.last_name, User.role).outerjoin(User, User.id == AuditLog.actor_id)
    n = select(func.count()).select_from(AuditLog)
    if entity in ENTITIES:
        q, n = q.where(AuditLog.entity == entity), n.where(AuditLog.entity == entity)
    total = db.session.scalar(n)
    pages = max(1, -(-total // JOURNAL_PAGE))
    page = min(max(1, page), pages)
    rows = db.session.execute(q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset((page - 1) * JOURNAL_PAGE).limit(JOURNAL_PAGE))
    return {"total": total, "page": page, "pages": pages, "rows": [
        {"when": x.created_at.astimezone(TASHKENT).strftime("%d.%m.%Y %H:%M"), "who": f"{first} {last}" if first else "—", "role": role,
         "entity": ENTITIES.get(x.entity, x.entity), "id": x.entity_id, "action": ACTIONS.get(x.action, x.action), "note": _note(x)}
        for x, first, last, role in rows]}


def _note(x: AuditLog) -> str:
    d = x.data or {}
    if x.entity == "setting":
        return ", ".join(f"{k}: {a} → {b}" for k, (a, b) in d.items())
    if x.action == "exam_date":
        return f"{d.get('old') or '—'} → {d.get('new') or '—'}"
    if "changed" in d and isinstance(d["changed"], list):
        return ", ".join(d["changed"])
    for k in ("title", "verdict", "count"):
        if d.get(k):
            return str(d[k])[:120]
    return ""


def section_titles(ids) -> list[str]:
    return [t for (t,) in db.session.execute(select(Section.title).where(Section.id.in_(ids)).order_by(Section.position))]
