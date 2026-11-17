"""Kirish, ro'yxatdan o'tish, parolni tiklash, sertifikatni tekshirish.

Hozircha soxta: haqiqiy foydalanuvchi bazasi yo'q, tekshiruvlar esa haqiqiy (formalar.py).
Ro'yxatdan o'tish qadamlari orasidagi ma'lumot (telefon/email) Flask sessiyasida saqlanadi.
Namunada tasdiqlash kodi har doim 123456 (backendda Telegram bot / email yuboradi).
"""
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_babel import gettext as _

from ..forms import (fmt_phone, REGIONS, check_secret, norm_secret, check_email, check_login, check_name, check_otp, check_password, check_phone,
                     field, norm_phone, otp_code, required, respond, validate)

bp = Blueprint("auth", __name__)

DEMO_OTP = "123456"


def _otp_matches(code):
    return None if code == DEMO_OTP else _("Kod noto‘g‘ri. Namunada kod: 123456")


def _fmt_phone(p):
    d = p.lstrip("+")
    return f"+{d[:3]} {d[3:5]} {d[5:8]} {d[8:10]} {d[10:]}" if len(d) == 12 else p


@bp.get("/")
def guest():
    return render_template("auth/guest.html")


@bp.route("/kirish", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html", error=request.args.get("xato"))
    from ..roles import HOME, role_from_login
    login_v, pw = field("login"), request.form.get("pw", "")
    # Namuna: "admin@..." — admin, "ekspert@..." — ekspert sifatida kiradi (rol tekshiruvidan o'tadi)
    role = role_from_login(login_v)
    errors = validate({"login": (login_v, lambda v: None if role != "user" and "@" in v else check_login(v)),
                       "pw": (pw, required)})
    if not errors:
        session["role"] = role
    return respond(errors=errors, template="auth/login.html", redirect_to=url_for(HOME[role]),
                   message=_("Xush kelibsiz!"))


@bp.route("/royxat", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", reg_step=1)
    phone = field("phone")
    errors = validate({"phone": (phone, required, check_phone)})
    if not errors:
        session["reg_phone"] = norm_phone(phone)
    return respond(errors=errors, template="auth/register.html", reg_step=1, redirect_to=url_for("auth.verify_telegram"))


@bp.route("/royxat/telegram", methods=["GET", "POST"])
def verify_telegram():
    phone = _fmt_phone(session.get("reg_phone", "+998901234567"))
    bot = current_app.config.get("TELEGRAM_BOT_URL", "https://t.me/raqamliMuallimBot")
    if request.method == "GET":
        return render_template("auth/verify_telegram.html", reg_step=2, phone=phone, bot_url=bot)
    code = otp_code()
    errors = validate({"otp": (code, check_otp, _otp_matches)})
    return respond(errors=errors, template="auth/verify_telegram.html", reg_step=2, phone=phone, bot_url=bot,
                   redirect_to=url_for("auth.details"))


@bp.post("/royxat/email/kod")
def send_email_code():
    email = field("email").lower()
    errors = validate({"email": (email, required, check_email)})
    if not errors:
        session["reg_email"] = email
    return respond(errors=errors, template="auth/verify_email.html", reg_step=2,
                   message=_("Kod %(email)s manziliga yuborildi", email=email), redirect_to=url_for("auth.verify_email", yuborildi=1))


@bp.route("/royxat/email", methods=["GET", "POST"])
def verify_email():
    sent = bool(session.get("reg_email")) and bool(request.args.get("yuborildi") or request.method == "POST")
    if request.method == "GET":
        return render_template("auth/verify_email.html", reg_step=2, sent=sent, email=session.get("reg_email", ""))
    email, code = field("email").lower(), otp_code()
    errors = validate({"email": (email, required, check_email), "otp": (code, check_otp, _otp_matches)})
    return respond(errors=errors, template="auth/verify_email.html", reg_step=2, sent=True, email=email,
                   redirect_to=url_for("auth.details"))


@bp.route("/royxat/malumotlar", methods=["GET", "POST"])
def details():
    if request.method == "GET":
        return render_template("auth/details.html", reg_step=3, regions=REGIONS)
    pw = request.form.get("pw", "")
    region = field("region")
    errors = validate({
        "fn": (field("fn"), lambda v: check_name(v, "first")),
        "ln": (field("ln"), lambda v: check_name(v, "last")),
        "pw": (pw, check_password),
        "pw2": (request.form.get("pw2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
        "secret": (request.form.get("secret", ""), lambda v: check_secret(v, pw)),
        "region": (region, lambda v: None if not v or v in REGIONS else _("Viloyatni ro‘yxatdan tanlang")),
        "consent": (request.form.get("consent"), lambda v: None if v else _("Davom etish uchun rozilik kerak")),
    })
    if not errors:
        session.pop("reg_phone", None)
        session.pop("reg_email", None)
        session["role"] = "user"
    return respond(errors=errors, template="auth/details.html", reg_step=3, regions=REGIONS,
                   redirect_to=url_for("user.home", yangi=1),
                   message=_("Ro‘yxatdan o‘tdingiz. Eslatma: 6 oy kirilmasa akkaunt avtomatik o‘chiriladi"))


@bp.get("/kirish/google")
def google():
    """Google OAuth 2.0. Namunada darhol kiritadi; backendda Authlib bilan accounts.google.com ga yo'naltiriladi,
    qaytgan email bo'yicha foydalanuvchi topiladi yoki yaratiladi (yangi bo'lsa — ism va rozilik so'raladi)."""
    from flask import flash
    if current_app.config.get("GOOGLE_CLIENT_ID"):
        return redirect(url_for("auth.login"))  # haqiqiy OAuth ulanadigan joy
    session["role"] = "user"
    flash(_("Google akkaunti orqali kirdingiz (namuna)"))
    return redirect(url_for("user.home"))


@bp.get("/chiqish")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.get("/maxfiylik")
def privacy():
    return render_template("auth/privacy.html")


# Parolni tiklash holati sessiyada: reset_who (kod yuborilgan manzil), reset_verified (kod tasdiqlangan),
# reset_fails (noto'g'ri kod urinishlari). Yangi parol faqat kod tasdiqlangandan keyin so'raladi va qabul qilinadi.
RESET_MAX_FAILS = 5


def _reset_ctx(**extra):
    who = session.get("reset_who", "")
    return {"sent": bool(who), "verified": bool(who) and bool(session.get("reset_verified")), "who": who, **extra}


@bp.route("/parol-tiklash", methods=["GET", "POST"])
def reset():
    """Bitta sahifa: telefon/email → «Kod yuborish» → kod → (kod to'g'ri bo'lsa) yangi parol."""
    if request.method == "GET":
        if not request.args.get("kod"):
            # Sahifaga yangidan kirilganda eski jarayon boshidan boshlanadi
            for k in ("reset_who", "reset_verified", "reset_fails"):
                session.pop(k, None)
        return render_template("auth/reset.html", **_reset_ctx())
    # Yakuniy qadam: yangi parol (kod oldinroq tasdiqlangan bo'lishi shart)
    who = session.get("reset_who")
    if not who or not session.get("reset_verified"):
        return respond(errors={"otp": _("Avval tasdiqlash kodini kiriting")}, template="auth/reset.html", **_reset_ctx())
    if field("who") and field("who") != who:
        return respond(errors={"who": _("Telefon/email o‘zgardi. Yangisiga kodni qayta yuboring")},
                       template="auth/reset.html", **_reset_ctx())
    pw = request.form.get("p1", "")
    errors = validate({
        "p1": (pw, check_password),
        "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
    })
    if not errors:
        for k in ("reset_who", "reset_verified", "reset_fails"):
            session.pop(k, None)
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(),
                   redirect_to=url_for("auth.login"), message=_("Parol yangilandi. Yangi parol bilan kiring"))


@bp.post("/parol-tiklash/kod")
def reset_code():
    """Kod yuborish (va qayta yuborish). Har yangi yuborishda avvalgi tasdiq bekor bo'ladi."""
    who = field("who")
    errors = validate({"who": (who, check_login)})
    if not errors:
        session["reset_who"] = who
        session.pop("reset_verified", None)
        session.pop("reset_fails", None)
    msg = (_("Kod %(c)s manziliga yuborildi", c=who) if "@" in who
           else _("Kod Telegram bot orqali %(c)s raqamiga yuborildi", c=fmt_phone(norm_phone(who)))) if not errors else None
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(who=who),
                   redirect_to=url_for("auth.reset", kod=1), message=msg)


@bp.post("/parol-tiklash/kod-tekshirish")
def reset_verify():
    """Kodni tekshirish. To'g'ri bo'lsa — yangi parol maydonlari ochiladi. 5 ta xato urinishdan keyin kod bekor qilinadi."""
    who = session.get("reset_who")
    if not who:
        return respond(errors={"who": _("Avval telefon raqam yoki emailga kod yuboring")}, template="auth/reset.html", **_reset_ctx())
    if field("who") and field("who") != who:
        return respond(errors={"who": _("Telefon/email o‘zgardi. Yangisiga kodni qayta yuboring")},
                       template="auth/reset.html", **_reset_ctx())
    code = otp_code()
    errors = validate({"otp": (code, check_otp)})
    if not errors and code != DEMO_OTP:
        fails = session.get("reset_fails", 0) + 1
        session["reset_fails"] = fails
        if fails >= RESET_MAX_FAILS:
            session.pop("reset_who", None)
            errors = {"otp": _("Kod 5 marta noto‘g‘ri kiritildi. Yangi kod so‘rang")}
        else:
            errors = {"otp": _("Kod noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=RESET_MAX_FAILS - fails)}
    if not errors:
        session["reset_verified"] = True
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(),
                   redirect_to=url_for("auth.reset", kod=1), message=_("Kod tasdiqlandi. Endi yangi parolni kiriting"))


# --- Maxfiy so'z orqali tiklash ---
# Telefon raqam o'zgargan yoki emailga kirib bo'lmaganda: eski login + maxfiy so'z → yangi aloqa (kod bilan) → yangi parol.
# Holat sessiyada: recover = {"step": 1|2|3, "who", "fails", "method", "contact"}.
# Namunada maxfiy so'z: "informatika". Backendda: users.secret_hash bilan solishtiriladi, urinishlar audit_log'ga yoziladi.
DEMO_SECRET = "informatika"
RECOVER_MAX_FAILS = 5


def _recover():
    return session.get("recover") or {"step": 1, "fails": 0}


def _recover_ctx(rec, **extra):
    method = rec.get("method", "phone")
    return {"rstep": rec.get("step", 1), "method": method, "contact": rec.get("contact", ""),
            "locked": rec.get("fails", 0) >= RECOVER_MAX_FAILS, "fails_left": RECOVER_MAX_FAILS - rec.get("fails", 0), **extra}


@bp.route("/parol-tiklash/maxfiy-soz", methods=["GET", "POST"])
def recover():
    rec = _recover()
    if request.method == "GET":
        if request.args.get("qayta"):
            rec = {"step": 1, "fails": rec.get("fails", 0)}
            session["recover"] = rec
        return render_template("auth/recover.html", **_recover_ctx(rec))

    # 1-qadam: eski telefon/email va maxfiy so'z
    if rec.get("fails", 0) >= RECOVER_MAX_FAILS:
        return respond(errors={"secret": _("Urinishlar tugadi. 30 daqiqadan keyin qayta urinib ko‘ring yoki yordam xizmatiga yozing")},
                       template="auth/recover.html", **_recover_ctx(rec))
    who, secret = field("who"), request.form.get("secret", "")
    errors = validate({"who": (who, check_login), "secret": (secret, required)})
    if not errors and norm_secret(secret) != DEMO_SECRET:
        rec["fails"] = rec.get("fails", 0) + 1
        session["recover"] = rec
        left = RECOVER_MAX_FAILS - rec["fails"]
        errors = {"secret": _("Telefon/email yoki maxfiy so‘z noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=left) if left
                  else _("Urinishlar tugadi. 30 daqiqadan keyin qayta urinib ko‘ring yoki yordam xizmatiga yozing")}
    if not errors:
        session["recover"] = {"step": 2, "fails": 0, "who": who}
    return respond(errors=errors, template="auth/recover.html", **_recover_ctx(rec),
                   redirect_to=url_for("auth.recover"), data={"step": 2})


@bp.post("/parol-tiklash/maxfiy-soz/aloqa")
def recover_contact():
    """2-qadam: yangi telefon (kod Telegram bot orqali) yoki yangi email (kod pochtaga)."""
    rec = _recover()
    if rec.get("step", 1) < 2:
        return redirect(url_for("auth.recover"))
    method = field("method") if field("method") in ("phone", "email") else "phone"
    value = field("contact")
    check = (lambda v: check_phone(v)) if method == "phone" else (lambda v: check_email(v.lower()))
    errors = validate({"contact": (value, required, check)})
    if not errors:
        contact = norm_phone(value) if method == "phone" else value.lower()
        session["recover"] = {**rec, "step": 3, "method": method, "contact": contact}
        msg = (_("Kod Telegram bot orqali %(c)s raqamiga yuborildi", c=_fmt_phone(contact)) if method == "phone"
               else _("Kod %(c)s manziliga yuborildi", c=contact))
    else:
        msg = None
    return respond(errors=errors, template="auth/recover.html", **_recover_ctx({**rec, "method": method}),
                   redirect_to=url_for("auth.recover"), message=msg, data={"step": 3})


@bp.post("/parol-tiklash/maxfiy-soz/tasdiq")
def recover_confirm():
    """3-qadam: yangi aloqadagi kod + yangi parol → aloqa yangilanadi va foydalanuvchi akkauntiga kiradi."""
    rec = _recover()
    if rec.get("step", 1) < 3:
        return redirect(url_for("auth.recover"))
    pw = request.form.get("p1", "")
    errors = validate({
        "otp": (otp_code(), check_otp, _otp_matches),
        "p1": (pw, check_password),
        "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
    })
    if not errors:
        session.pop("recover", None)
        session["role"] = "user"
    return respond(errors=errors, template="auth/recover.html", **_recover_ctx(rec),
                   redirect_to=url_for("user.home"),
                   message=_("Akkaunt tiklandi: yangi telefon raqam yoki email saqlandi, endi yangi parol bilan kirasiz"))


# --- Sertifikatni tekshirish (ommaviy, QR-koddan) ---
# Namunada: INF-2026-000123 — haqiqiy, INF-2026-000099 — bekor qilingan, qolgani — topilmadi
_CERT_STATES = {"INF-2026-000123": "valid", "INF-2026-000099": "revoked"}


@bp.get("/s/<cert_no>")
def verify_certificate(cert_no):
    cert_no = cert_no.upper()
    state = _CERT_STATES.get(cert_no, "missing")
    return render_template("auth/verify_certificate.html", cert_no=cert_no, state=state), 200 if state != "missing" else 404


@bp.get("/s")
def verify_certificate_lookup():
    """Raqam kiritish sahifasi (mehmon sahifasidan). Raqam berilsa — natija sahifasiga yo'naltiradi."""
    import re
    raw = request.args.get("raqam", "").strip().upper()
    if not raw:
        return render_template("auth/verify_certificate.html", state="form", cert_no="")
    if not re.fullmatch(r"[A-Z]{3}-\d{4}-\d{6}", raw):
        return render_template("auth/verify_certificate.html", state="form", cert_no=raw,
                               lookup_error=_("Raqam formati: 3 harf, yil va 6 raqam. Masalan: INF-2026-000123")), 422
    return redirect(url_for("auth.verify_certificate", cert_no=raw))
