"""Profil: shaxsiy ma'lumotlar, telefon/email, parol va maxfiy so'z — uchala rol uchun umumiy.

O'qituvchi (user), ekspert va admin profillari bir xil formalardan foydalanadi; farqi — shablon va
blueprint (url'lar /app/profil, /ekspert/profil, /admin/profil). register(bp, ...) shu yo'nalishlarni
berilgan blueprint'ga qo'shadi. Parolni unutganda — umumiy /parol-tiklash (auth.reset) sahifasi.

Namunada joriy parol "parol1234", tasdiqlash kodi 123456. Backendda: users.password_hash, audit_log.
"""
from flask import jsonify, render_template, request, session, url_for
from flask_babel import gettext as _

from .. import mock as m
from ..forms import (check_email, check_name, check_otp, check_password, check_phone, check_secret, field, fmt_phone,
                     norm_phone, otp_code, required, respond, validate)

DEMO_PASSWORD = "parol1234"
DEMO_OTP = "123456"
PW_MAX_FAILS = 5


def account_of(role: str) -> dict:
    """Profil egasining ma'lumotlari (namuna). Backendda: current_user."""
    return m.ME if role == "user" else m.STAFF[role]


def check_current_password(pw: str):
    """Joriy parolni tekshiradi; 5 ta xato urinishdan keyin 15 daqiqa bloklanadi (namunada — sessiya oxirigacha)."""
    fails = session.get("pw_fails", 0)
    if fails >= PW_MAX_FAILS:
        return _("Parol 5 marta noto‘g‘ri kiritildi. 15 daqiqadan keyin qayta urinib ko‘ring")
    if not pw:
        return _("Joriy parolni kiriting")
    if pw != DEMO_PASSWORD:
        session["pw_fails"] = fails + 1
        left = PW_MAX_FAILS - fails - 1
        return (_("Parol noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=left) if left
                else _("Parol 5 marta noto‘g‘ri kiritildi. 15 daqiqadan keyin qayta urinib ko‘ring"))
    session.pop("pw_fails", None)
    return None


def context(bp_name: str, role: str, **ctx) -> dict:
    """Profil shablonlari uchun umumiy kontekst: kimning profili, qaysi blueprint, aloqani almashtirish holati."""
    cc = session.get("contact_change") or {}
    return {"acct": account_of(role), "acct_bp": bp_name, "cc_pending": bool(cc), "cc_method": cc.get("method"),
            "cc_target": cc.get("target"), **ctx}


# ---------- Formalar: har biri (bp_name, role, template) bilan chaqiriladi ----------

def save_info(bp_name, role, template, **extra):
    errors = validate({
        "fn": (field("fn"), lambda v: check_name(v, "first")),
        "ln": (field("ln"), lambda v: check_name(v, "last")),
    })
    return respond(errors=errors, template=template, **context(bp_name, role, open="info", **extra),
                   redirect_to=url_for(bp_name + ".profile"), message=_("Shaxsiy ma’lumotlar saqlandi"))


def password_check():
    """Telefon/emailni almashtirishdan oldin joriy parolni tekshirish: to'g'ri bo'lsa «Kod yuborish» faollashadi."""
    err = check_current_password(request.form.get("pw", ""))
    if err:
        return jsonify(ok=False, errors={"pw": err}), 422
    return jsonify(ok=True, message=_("Parol to‘g‘ri"))


def contact_code(bp_name, role, template, **extra):
    """Telefon yoki emailni almashtirish, 1-qadam: yangi qiymat + joriy parol → yangi qiymatga kod (telefon — Telegram bot).
    Parol shu yerda ham qayta tekshiriladi: «Kod yuborish» tugmasini chetlab o'tib bo'lmaydi."""
    acct = account_of(role)
    method = field("method") if field("method") in ("phone", "email") else "phone"
    value = field("contact")
    current = {"phone": acct["phone_raw"], "email": acct["email"]}[method]
    errors = validate({"contact": (value, required, check_phone if method == "phone" else (lambda v: check_email(v.lower())))})
    target = norm_phone(value) if method == "phone" else value.lower()
    if not errors and target == current:
        errors = {"contact": _("Bu sizning hozirgi ma’lumotingiz. Boshqasini kiriting")}
    pw_error = check_current_password(request.form.get("pw", ""))
    if pw_error:
        errors = {**errors, "pw": pw_error}
    if not errors:
        session["contact_change"] = {"method": method, "target": target}
    msg = (_("Kod Telegram bot orqali %(c)s raqamiga yuborildi", c=fmt_phone(target)) if method == "phone"
           else _("Kod %(c)s manziliga yuborildi", c=target)) if not errors else None
    return respond(errors=errors, template=template, **context(bp_name, role, open="contact", cc_method=method, **extra),
                   redirect_to=url_for(bp_name + ".profile"), message=msg,
                   data={"target": fmt_phone(target) if method == "phone" else target})


def contact_confirm(bp_name, role, template, **extra):
    """2-qadam: kod to'g'ri bo'lsa yangi telefon/email saqlanadi (eskisi shu paytgacha amalda)."""
    cc = session.get("contact_change")
    if not cc:
        return respond(errors={"otp": _("Avval yangi telefon yoki emailni kiriting")}, template=template,
                       **context(bp_name, role, open="contact", **extra))
    errors = validate({"otp": (otp_code(), check_otp, lambda v: None if v == DEMO_OTP else _("Kod noto‘g‘ri. Namunada kod: 123456"))})
    if not errors:
        session.pop("contact_change", None)
    msg = (_("Telefon raqam yangilandi") if cc["method"] == "phone" else _("Email yangilandi")) if not errors else None
    return respond(errors=errors, template=template, **context(bp_name, role, open="contact", **extra),
                   redirect_to=url_for(bp_name + ".profile"), message=msg)


def save_secret(bp_name, role, template, **extra):
    pw = request.form.get("pw", "")
    errors = validate({"pw": (pw, required), "secret": (request.form.get("secret", ""), lambda v: check_secret(v, pw))})
    return respond(errors=errors, template=template, **context(bp_name, role, open="secret", **extra),
                   redirect_to=url_for(bp_name + ".profile"), message=_("Maxfiy so‘z yangilandi"))


def change_password(bp_name, role, template, **extra):
    new = request.form.get("new", "")
    errors = validate({
        "old": (request.form.get("old", ""), required),
        "new": (new, check_password),
        "new2": (request.form.get("new2", ""), lambda v: None if v == new else _("Parollar bir xil emas")),
    })
    if not errors and request.form.get("old") == new:
        errors = {"new": _("Yangi parol joriy paroldan farq qilsin")}
    return respond(errors=errors, template=template, **context(bp_name, role, open="pw", **extra),
                   redirect_to=url_for(bp_name + ".profile"), message=_("Parol o‘zgartirildi"))


def register(bp, role: str, template: str = "staff/profile.html", **extra):
    """Ekspert va admin blueprint'lariga profil yo'nalishlarini qo'shadi: /profil, /profil/malumotlar, ..."""
    name = bp.name
    ctx = {"panel": role, **extra}
    bp.add_url_rule("/profil", "profile", lambda: render_template(template, **context(name, role, **ctx)))
    bp.add_url_rule("/profil/malumotlar", "profile_info", lambda: save_info(name, role, template, **ctx), methods=["POST"])
    bp.add_url_rule("/profil/parol-tekshirish", "password_check", password_check, methods=["POST"])
    bp.add_url_rule("/profil/aloqa/kod", "contact_code", lambda: contact_code(name, role, template, **ctx), methods=["POST"])
    bp.add_url_rule("/profil/aloqa/tasdiq", "contact_confirm", lambda: contact_confirm(name, role, template, **ctx), methods=["POST"])
    bp.add_url_rule("/profil/maxfiy-soz", "profile_secret", lambda: save_secret(name, role, template, **ctx), methods=["POST"])
    bp.add_url_rule("/profil/parol", "profile_password", lambda: change_password(name, role, template, **ctx), methods=["POST"])
