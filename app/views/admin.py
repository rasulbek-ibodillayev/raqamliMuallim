"""Admin paneli: faqat adminga tegishli bo'limlar.

- Statistika — sayt ko'rsatkichlari va CSV hisobot (services/admin_stats.py);
- Foydalanuvchilar — o'qituvchilar ro'yxati, to'liq kartasi, attestatsiya sanasi, bloklash, parol havolasi, o'chirish
  (services/admin_users.py);
- Ekspertlar — taklif qilish (app/invites.py), huquq va mavzularini berish, to'xtatish;
- Sozlamalar — test va reja sonlari (services/settings.py);
- Jurnal — barcha amallar (audit_log).
Kontent (mavzular, darslar, savollar) — ekspert vazifasi: app/views/expert.py.
"""
from flask import Blueprint, Response, abort, redirect, render_template, request, session, url_for
from flask_babel import gettext as _
from flask_login import current_user

from .. import invites
from .. import mock as m
from ..extensions import db
from ..models import ExpertInvite, User
from . import account
from ..forms import (REGIONS, check_date, check_email, check_name, check_phone, field, fmt_phone, norm_phone, required, respond,
                     validate)
from ..services import admin_stats as st
from ..services import admin_users as au
from ..services import experts as ex
from ..services import settings as conf
from ..services.timefmt import when

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Profil: shaxsiy ma'lumotlar, telefon/email, parol, maxfiy so'z (app/views/account.py)
account.register(bp, "admin")


def _download(data: bytes, name: str, mime: str):
    return Response(data, mimetype=mime, headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


def _page() -> int:
    return max(1, min(request.args.get("sahifa", 1, type=int) or 1, 100_000))


# ---------------- Statistika ----------------

def _period() -> int:
    return st.PERIODS.get(request.args.get("davr", ""), 30)


@bp.get("/")
def stats():
    return render_template("admin/stats.html", s=st.overview(_period()), period=str(_period()), panel="admin")


@bp.get("/hisobot.csv")
def stats_csv():
    return _download(st.report(_period()), "hisobot.csv", "text/csv")


# ---------------- Foydalanuvchilar ----------------

def _users_ctx(**extra):
    f = au.Filters.from_args(request.args)
    return {"list": au.listing(f, _page()), "f": vars(f), "counts": au.counts(), "topics": au.total_topics(), "regions": REGIONS,
            "panel": "admin", **extra}


@bp.get("/foydalanuvchilar")
def users():
    return render_template("admin/users.html", **_users_ctx())


@bp.get("/foydalanuvchilar.csv")
def users_csv():
    au.log(current_user.id, "export", "user", "csv")
    db.session.commit()
    return _download(au.export(au.Filters.from_args(request.args)), "foydalanuvchilar.csv", "text/csv")


def _teacher(uid) -> User:
    return au.teacher(uid) or abort(404)


@bp.get("/foydalanuvchilar/<int:uid>")
def user_detail(uid):
    u = _teacher(uid)
    link = session.pop("reset_link", None)
    return render_template("admin/user_detail.html", u=au.card(u), status=m.STATUS, decision=m.DECISION, obj_state=m.OBJ_STATE,
                           reset_link=link["url"] if link and link["uid"] == uid else None, panel="admin")


@bp.get("/_namuna")
def sample_user():
    """Faqat ishlab chiqish uchun: namunaviy o'qituvchining kartasi (/ekranlar havolasi)."""
    from ..cli import demo_user
    from .test import is_dev
    if not is_dev():
        abort(404)
    return redirect(url_for("admin.user_detail", uid=demo_user("user").id))


@bp.post("/foydalanuvchilar/<int:uid>/holat")
def user_status(uid):
    """Bloklash / blokdan chiqarish / parolni tiklash havolasi / akkauntni butunlay o'chirish."""
    u, action = _teacher(uid), field("action")
    here = url_for("admin.user_detail", uid=uid)
    if action in ("block", "unblock"):
        au.set_active(u, action == "unblock", current_user.id)
        return respond(redirect_to=here, message=_("Foydalanuvchi bloklandi") if action == "block" else _("Foydalanuvchi blokdan chiqarildi"))
    if action == "reset":
        if not u.is_active:
            return respond(redirect_to=here, message=_("Bloklangan akkauntga havola berilmaydi"))
        # Havola faqat bir marta, shu sahifada ko'rsatiladi (logga va jurnalga yozilmaydi)
        session["reset_link"] = {"uid": uid, "url": url_for("auth.reset_link", token=invites.reset_token(u), _external=True)}
        au.log(current_user.id, "reset_link", "user", uid)
        db.session.commit()
        return respond(redirect_to=here, message=_("Havola tayyor: nusxalab, o‘qituvchiga yuboring"))
    if action == "delete":
        kept = au.delete_account(u, current_user.id)
        return respond(redirect_to=url_for("admin.users"),
                       message=_("Akkaunt o‘chirildi, %(n)s ta sertifikati saqlandi", n=kept) if kept else _("Akkaunt o‘chirildi"))
    abort(400)


@bp.post("/foydalanuvchilar/sana")
def set_exam_date():
    """Attestatsiya sanasini admin kiritadi (o'qituvchi o'zgartira olmaydi)."""
    from datetime import date
    uid = field("user")
    u = au.teacher(int(uid)) if uid.isdigit() else None
    errors = validate({"user": (uid, required), "date": (field("date"), check_date)})
    if not errors and u is None:
        errors = {"user": _("Foydalanuvchi topilmadi")}
    if not errors:
        au.set_exam_date(u, date.fromisoformat(field("date")), current_user.id, bool(field("notify")))
        db.session.commit()
    back = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else None
    return respond(errors=errors, template="admin/users.html", **(_users_ctx() if errors else {}), redirect_to=back or url_for("admin.users"),
                   message=u and _("%(name)s uchun attestatsiya sanasi saqlandi", name=u.full_name))


@bp.get("/foydalanuvchilar/sanalar-namuna.xlsx")
def dates_sample():
    return _download(au.dates_sample(), "sanalar-namuna.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.post("/foydalanuvchilar/sanalar")
def dates_import():
    """Attestatsiya sanalarini Excel'dan: bitta qatorda xato bo'lsa ham hech narsa yozilmaydi."""
    f, n = request.files.get("file"), 0
    if not f or not f.filename:
        errors = {"file": _("Excel faylni tanlang")}
    elif not f.filename.lower().endswith(".xlsx"):
        errors = {"file": _("Fayl .xlsx formatida bo‘lsin")}
    else:
        n, errs = au.import_dates(f.read(), current_user.id, bool(field("notify")))
        errors = {"file": "; ".join(errs)} if errs else {}
    return respond(errors=errors, template="admin/users.html", **(_users_ctx(dates_open=True) if errors else {}),
                   redirect_to=url_for("admin.users"), message=_("%(n)s ta foydalanuvchining sanasi saqlandi", n=n))


# ---------------- Ekspertlar ----------------

def _invite_view(i: ExpertInvite) -> dict:
    return {"id": i.id, "name": i.name, "contact": i.contact, "via": invites.channel(i.contact),
            "shown": i.contact if "@" in i.contact else fmt_phone(i.contact), "sent": when(i.sent_at), "expired": invites.expired(i),
            "link": url_for("auth.invite", token=invites.token(i), _external=True)}


def _experts_ctx(**extra):
    return {"experts": st.expert_rows(), "summary": st.expert_summary(), "perms": m.EXPERT_PERMS, "areas": au.sections(),
            "panel": "admin", "invites": [_invite_view(i) for i in invites.pending()], **extra}


@bp.get("/ekspertlar")
def experts():
    return render_template("admin/experts.html", **_experts_ctx())


def _area_ids(values) -> list[int] | None:
    """Tanlangan mavzular (bo'sh ro'yxat — hammasi); noma'lum id bo'lsa None."""
    known = {i for i, _t in au.sections()}
    ids = {int(v) for v in values if v.isdigit()}
    return sorted(ids) if len(ids) == len(set(values)) and ids <= known else None


def _perm_list(values) -> list[str]:
    return [p for p in ex.PERMS if p in values]


def _ready_message():
    return _("Taklifnoma tayyor. Havolani nusxalab ekspertga yuboring: u 72 soat amal qiladi")


@bp.post("/ekspertlar")
def expert_add():
    """Yangi ekspert: ism-familiya + telefon yoki email (login) → taklif havolasi.
    Ekspert havolani ochib, parolni o'zi o'rnatadi (auth.invite) — admin parolni bilmaydi."""
    raw = field("contact")
    contact = raw.lower() if "@" in raw else norm_phone(raw)
    areas, perms = _area_ids(request.form.getlist("areas")), _perm_list(request.form.getlist("perms"))
    errors = validate({
        "name": (field("name"), lambda v: check_name(v.split()[0] if v else "", "first") or
                 (None if len(v.split()) >= 2 and len(v) <= 160 else _("Ism va familiyani kiriting"))),
        "contact": (raw, required, lambda v: check_email(v) if "@" in v else check_phone(v),
                    lambda v: _("Bu telefon yoki email bilan akkaunt allaqachon bor") if User.by_login(contact) else None),
        "areas": (areas, lambda v: None if v is not None else _("Mavzular ro‘yxatdan tanlansin")),
        "perms": (perms, lambda v: None if v else _("Kamida bitta huquq bering")),
    })
    if not errors:
        inv = invites.make(" ".join(field("name").split()), contact, areas, perms, current_user.id)
        au.log(current_user.id, "send", "invite", inv.id)
        db.session.commit()
    return respond(errors=errors, template="admin/experts.html", **(_experts_ctx(add_open=True) if errors else {}),
                   redirect_to=url_for("admin.experts"), message=_ready_message())


@bp.post("/ekspertlar/taklif")
def invite_action():
    """Taklifnomani yangilash (yangi havola, 72 soat qaytadan) yoki bekor qilish."""
    action, iid = field("action"), field("id")
    inv = db.session.get(ExpertInvite, int(iid)) if iid.isdigit() and len(iid) < 19 else None
    if action not in {"resend", "cancel"} or inv is None or inv.used_at is not None:
        abort(400)
    au.log(current_user.id, action, "invite", inv.id)
    if action == "cancel":
        db.session.delete(inv)
    else:
        invites.resend(inv)
    db.session.commit()
    return respond(redirect_to=url_for("admin.experts"),
                   message=_ready_message() if action == "resend" else _("Taklifnoma bekor qilindi. Eski havola endi ishlamaydi"))


@bp.post("/ekspertlar/<int:eid>")
def expert_update(eid):
    u, action = db.session.get(User, eid), field("action")
    if u is None or u.role != "expert":
        abort(404)
    if action in ("block", "unblock"):
        u.is_active = action == "unblock"
        au.log(current_user.id, action, "expert", eid)
        msg = _("Ekspert faoliyati to‘xtatildi") if action == "block" else _("Ekspert faollashtirildi")
    elif action == "perms":
        perms, areas = _perm_list(request.form.getlist("perms")), _area_ids(request.form.getlist("areas"))
        if areas is None:
            abort(400)
        ex.save(eid, perms, areas)
        au.log(current_user.id, "perms", "expert", eid, {"perms": perms, "areas": areas})
        msg = _("Huquqlar saqlandi")
    else:
        abort(400)
    db.session.commit()
    return respond(redirect_to=url_for("admin.experts"), message=msg)


# ---------------- Sozlamalar ----------------

def _settings_ctx(**extra):
    return {"items": [(k, i, conf.get(k)) for k, i in conf.ITEMS.items()], "groups": {k: i.group for k, i in conf.ITEMS.items()},
            "panel": "admin", **extra}


@bp.route("/sozlamalar", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        return render_template("admin/settings.html", **_settings_ctx())
    values, errors = {}, {}
    for key, item in conf.ITEMS.items():
        v = field(key)
        if v.isdigit() and item.low <= int(v) <= item.high:
            values[key] = int(v)
        else:
            errors[key] = _("%(a)s dan %(b)s gacha butun son", a=item.low, b=item.high)
    if not errors:
        changed = conf.save(values, current_user.id)
        if changed:
            au.log(current_user.id, "update", "setting", "tests", changed)
        db.session.commit()
    return respond(errors=errors, template="admin/settings.html", **(_settings_ctx() if errors else {}),
                   redirect_to=url_for("admin.settings"), message=_("Sozlamalar saqlandi"))


# ---------------- Jurnal ----------------

@bp.get("/jurnal")
def journal():
    entity = request.args.get("tur", "")
    return render_template("admin/journal.html", j=st.journal(entity, _page()), entity=entity, entities=st.ENTITIES, panel="admin")


@bp.get("/jurnal/")
def journal_slash():
    return redirect(url_for("admin.journal"), 301)
