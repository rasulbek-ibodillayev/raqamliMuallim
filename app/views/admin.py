"""Admin paneli: faqat adminga tegishli bo'limlar.

- Statistika — sayt ko'rsatkichlari;
- Foydalanuvchilar — ro'yxat va har bir o'qituvchining to'liq ma'lumoti (o'zlashtirgan mavzulari, testlari, faolligi);
- Ekspertlar — qo'shish, huquqlarini berish, faoliyatini nazorat qilish, bloklash;
- Sozlamalar — tizim chegaralari, faol bo'lmagan akkauntlar siyosati.
Kontent (mavzular, darslar, savollar) — ekspert vazifasi: app/views/expert.py.
"""
from flask import Blueprint, abort, render_template, request, url_for
from flask_babel import gettext as _

from .. import mock as m
from ..forms import (check_date, check_email, check_name, check_phone, field, required, respond, validate)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
def stats():
    return render_template("admin/stats.html", s=m.STATS, dau=m.DAU, hard=m.HARD_TOPICS, panel="admin")


@bp.get("/foydalanuvchilar")
def users():
    return render_template("admin/users.html", users=m.USERS, panel="admin")


@bp.get("/foydalanuvchilar/<int:uid>")
def user_detail(uid):
    if not 1 <= uid <= len(m.USERS):
        abort(404)
    name, ini, contact, region, done, last, active, exam = m.USERS[uid - 1]
    u = {"id": uid, "name": name, "ini": ini, "contact": contact, "region": region, "done": done, "last": last,
         "active": active, "exam": exam, **m.USER_DETAIL}
    return render_template("admin/user_detail.html", u=u, sections=m.SECTIONS, status=m.STATUS, results=m.RESULTS,
                           decision=m.DECISION, weak=m.ERRORS_WEAK, objections=m.OBJECTIONS, obj_state=m.OBJ_STATE,
                           trend=m.TREND, panel="admin")


@bp.post("/foydalanuvchilar/<int:uid>/holat")
def user_status(uid):
    """Bloklash / blokdan chiqarish / parolni tiklash havolasi / akkauntni o'chirish. Backendda: audit_log."""
    action = field("action")
    if action not in {"block", "unblock", "reset", "delete"}:
        abort(400)
    msg = {"block": _("Foydalanuvchi bloklandi"), "unblock": _("Foydalanuvchi blokdan chiqarildi"),
           "reset": _("Parolni tiklash havolasi yuborildi"), "delete": _("Akkaunt o‘chirildi")}[action]
    target = url_for("admin.users") if action == "delete" else url_for("admin.user_detail", uid=uid)
    return respond(redirect_to=target, message=msg)


@bp.get("/ekspertlar")
def experts():
    return render_template("admin/experts.html", experts=m.EXPERTS, perms=m.EXPERT_PERMS, areas=m.CONTENT_AREAS, panel="admin")


@bp.post("/ekspertlar")
def expert_add():
    contact = field("contact")
    errors = validate({
        "name": (field("name"), lambda v: check_name(v.split()[0] if v else "", "first") or
                 (None if len(v.split()) >= 2 else _("Ism va familiyani kiriting"))),
        "contact": (contact, required, lambda v: check_email(v) if "@" in v else check_phone(v)),
        "areas": (request.form.getlist("areas"), lambda v: None if v else _("Kamida bitta yo‘nalishni tanlang")),
        "perms": (request.form.getlist("perms"), lambda v: None if v else _("Kamida bitta huquq bering")),
    })
    return respond(errors=errors, template="admin/experts.html", experts=m.EXPERTS, perms=m.EXPERT_PERMS,
                   areas=m.CONTENT_AREAS, panel="admin", add_open=True, redirect_to=url_for("admin.experts"),
                   message=_("%(name)s ekspert sifatida qo‘shildi. Taklifnoma yuborildi", name=field("name")))


@bp.post("/ekspertlar/<int:eid>")
def expert_update(eid):
    action = field("action")
    if action not in {"block", "unblock", "perms"}:
        abort(400)
    msg = {"block": _("Ekspert faoliyati to‘xtatildi"), "unblock": _("Ekspert faollashtirildi"), "perms": _("Huquqlar saqlandi")}[action]
    return respond(redirect_to=url_for("admin.experts"), message=msg)


@bp.get("/sozlamalar")
def settings():
    return render_template("admin/settings.html", panel="admin")


@bp.post("/foydalanuvchilar/sana")
def set_exam_date():
    """Attestatsiya sanasini admin kiritadi (o'qituvchi o'zgartira olmaydi). Backendda: users.exam_date + audit_log."""
    errors = validate({"user": (field("user"), required), "date": (field("date"), check_date)})
    return respond(errors=errors, template="admin/users.html", users=m.USERS, panel="admin",
                   redirect_to=request.referrer or url_for("admin.users"),
                   message=_("%(name)s uchun attestatsiya sanasi saqlandi", name=field("name") or _("Foydalanuvchi")))
