"""Admin paneli: faqat adminga tegishli bo'limlar.

- Statistika — sayt ko'rsatkichlari;
- Foydalanuvchilar — ro'yxat va har bir o'qituvchining to'liq ma'lumoti (o'zlashtirgan mavzulari, testlari, faolligi);
- Ekspertlar — qo'shish, huquqlarini berish, faoliyatini nazorat qilish, bloklash;
- Sozlamalar — tizim chegaralari, faol bo'lmagan akkauntlar siyosati.
Kontent (mavzular, darslar, savollar) — ekspert vazifasi: app/views/expert.py.
"""
from datetime import datetime

from flask import Blueprint, abort, render_template, request, session, url_for
from flask_babel import gettext as _

from .. import invites
from .. import mock as m
from . import account
from ..forms import (check_date, check_email, check_name, check_phone, field, fmt_phone, norm_phone, required, respond,
                     validate)

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Profil: shaxsiy ma'lumotlar, telefon/email, parol, maxfiy so'z (app/views/account.py)
account.register(bp, "admin")


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


def _experts_ctx(**extra):
    """Ekspertlar sahifasi: ro'yxat + javob kutayotgan taklifnomalar (namunada sessiyada; backendda expert_invites)."""
    return {"experts": m.EXPERTS, "perms": m.EXPERT_PERMS, "areas": m.CONTENT_AREAS, "panel": "admin",
            "invites": session.get("invites", []), **extra}


@bp.get("/ekspertlar")
def experts():
    if request.args.get("namuna") and not session.get("invites"):   # /ekranlar: javob kutayotgan taklifnoma namunasi
        _send_invite("Nodira Saidova", "+998935551122", ["Dasturlash"], ["questions", "review"])
    return render_template("admin/experts.html", **_experts_ctx())


def _send_invite(name, contact, areas, perms):
    """Taklif havolasini yaratadi va «yuboradi» (namunada — faqat ro'yxatga yoziladi). → yuborilgan taklifnoma."""
    for old in session.get("invites", []):          # qayta yuborilsa — eski havola ishlamaydi
        if old["contact"] == contact:
            invites.revoke(old["token"])
    token = invites.make(name, contact, areas, perms)
    inv = {"token": token, "name": name, "contact": contact, "via": invites.channel(contact),
           "shown": contact if "@" in contact else fmt_phone(contact),
           "link": url_for("auth.invite", token=token, _external=True), "sent": datetime.now().strftime("%d.%m.%Y %H:%M")}
    # Backendda: email — xat; telefon — Telegram bot (ekspert botga /start qilgan bo'lsa), aks holda admin havolani o'zi yuboradi
    session["invites"] = [i for i in session.get("invites", []) if i["contact"] != contact] + [inv]
    return inv


def _sent_message(inv):
    return (_("Taklif havolasi Telegram orqali %(c)s raqamiga yuborildi. Havola 72 soat amal qiladi", c=fmt_phone(inv["contact"]))
            if inv["via"] == "telegram" else
            _("Taklif havolasi %(c)s manziliga yuborildi. Havola 72 soat amal qiladi", c=inv["contact"]))


@bp.post("/ekspertlar")
def expert_add():
    """Yangi ekspert: ism-familiya + telefon yoki email (login) → shu manzilga taklif havolasi.
    Ekspert havolani ochib, parolni o'zi o'rnatadi (auth.invite) — admin parolni bilmaydi."""
    raw = field("contact")
    contact = raw.lower() if "@" in raw else norm_phone(raw)
    known = {e["contact"].replace(" ", "").lower() for e in m.EXPERTS}
    errors = validate({
        "name": (field("name"), lambda v: check_name(v.split()[0] if v else "", "first") or
                 (None if len(v.split()) >= 2 else _("Ism va familiyani kiriting"))),
        "contact": (raw, required, lambda v: check_email(v) if "@" in v else check_phone(v),
                    lambda v: _("Bu telefon yoki email bilan ekspert allaqachon bor") if contact in known else None),
        "areas": (request.form.getlist("areas"), lambda v: None if v else _("Kamida bitta yo‘nalishni tanlang")),
        "perms": (request.form.getlist("perms"), lambda v: None if v else _("Kamida bitta huquq bering")),
    })
    inv = None if errors else _send_invite(" ".join(field("name").split()), contact,
                                           request.form.getlist("areas"), request.form.getlist("perms"))
    return respond(errors=errors, template="admin/experts.html", **_experts_ctx(add_open=True),
                   redirect_to=url_for("admin.experts"), message=inv and _sent_message(inv))


@bp.post("/ekspertlar/taklif")
def invite_action():
    """Taklifnomani qayta yuborish (yangi havola, 72 soat qaytadan) yoki bekor qilish."""
    action, contact = field("action"), field("contact")
    inv = next((i for i in session.get("invites", []) if i["contact"] == contact), None)
    if action not in {"resend", "cancel"} or not inv:
        abort(400)
    if action == "cancel":
        invites.revoke(inv["token"])
        session["invites"] = [i for i in session["invites"] if i["contact"] != contact]
        return respond(redirect_to=url_for("admin.experts"), message=_("Taklifnoma bekor qilindi. Eski havola endi ishlamaydi"))
    data = invites.read(inv["token"])[1] or {}
    inv = _send_invite(inv["name"], contact, data.get("a", []), data.get("p", []))
    return respond(redirect_to=url_for("admin.experts"), message=_sent_message(inv))


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
