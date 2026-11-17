"""Kirish, ro'yxatdan o'tish, parolni tiklash, sertifikatni tekshirish.

Hozircha soxta: haqiqiy foydalanuvchi bazasi yo'q, tekshiruvlar esa haqiqiy (formalar.py).
Ro'yxatdan o'tish qadamlari orasidagi ma'lumot (telefon/email) Flask sessiyasida saqlanadi.
Namunada tasdiqlash kodi har doim 123456 (backendda Telegram bot / email yuboradi).
"""
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_babel import gettext as _

from ..forms import (REGIONS, check_email, check_login, check_name, check_otp, check_password, check_phone,
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
        return render_template("auth/register.html", step=1)
    phone = field("phone")
    errors = validate({"phone": (phone, required, check_phone)})
    if not errors:
        session["reg_phone"] = norm_phone(phone)
    return respond(errors=errors, template="auth/register.html", step=1, redirect_to=url_for("auth.verify_telegram"))


@bp.route("/royxat/telegram", methods=["GET", "POST"])
def verify_telegram():
    phone = _fmt_phone(session.get("reg_phone", "+998901234567"))
    bot = current_app.config.get("TELEGRAM_BOT_URL", "https://t.me/raqamliMuallimBot")
    if request.method == "GET":
        return render_template("auth/verify_telegram.html", step=2, phone=phone, bot_url=bot)
    code = otp_code()
    errors = validate({"otp": (code, check_otp, _otp_matches)})
    return respond(errors=errors, template="auth/verify_telegram.html", step=2, phone=phone, bot_url=bot,
                   redirect_to=url_for("auth.details"))


@bp.post("/royxat/email/kod")
def send_email_code():
    email = field("email").lower()
    errors = validate({"email": (email, required, check_email)})
    if not errors:
        session["reg_email"] = email
    return respond(errors=errors, template="auth/verify_email.html", step=2,
                   message=_("Kod %(email)s manziliga yuborildi", email=email), redirect_to=url_for("auth.verify_email", yuborildi=1))


@bp.route("/royxat/email", methods=["GET", "POST"])
def verify_email():
    sent = bool(session.get("reg_email")) and bool(request.args.get("yuborildi") or request.method == "POST")
    if request.method == "GET":
        return render_template("auth/verify_email.html", step=2, sent=sent, email=session.get("reg_email", ""))
    email, code = field("email").lower(), otp_code()
    errors = validate({"email": (email, required, check_email), "otp": (code, check_otp, _otp_matches)})
    return respond(errors=errors, template="auth/verify_email.html", step=2, sent=True, email=email,
                   redirect_to=url_for("auth.details"))


@bp.route("/royxat/malumotlar", methods=["GET", "POST"])
def details():
    if request.method == "GET":
        return render_template("auth/details.html", step=3, regions=REGIONS)
    pw = request.form.get("pw", "")
    region = field("region")
    errors = validate({
        "fn": (field("fn"), lambda v: check_name(v, "first")),
        "ln": (field("ln"), lambda v: check_name(v, "last")),
        "pw": (pw, check_password),
        "pw2": (request.form.get("pw2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
        "region": (region, lambda v: None if not v or v in REGIONS else _("Viloyatni ro‘yxatdan tanlang")),
        "consent": (request.form.get("consent"), lambda v: None if v else _("Davom etish uchun rozilik kerak")),
    })
    if not errors:
        session.pop("reg_phone", None)
        session.pop("reg_email", None)
        session["role"] = "user"
    return respond(errors=errors, template="auth/details.html", step=3, regions=REGIONS,
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


@bp.route("/parol-tiklash", methods=["GET", "POST"])
def reset():
    step = 2 if session.get("reset_who") else 1
    if request.method == "GET":
        if not request.args.get("kod"):
            step = 1
        return render_template("auth/reset.html", step=step)
    pw = request.form.get("p1", "")
    errors = validate({
        "otp": (otp_code(), check_otp, _otp_matches),
        "p1": (pw, check_password),
        "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
    })
    if not errors:
        session.pop("reset_who", None)
    return respond(errors=errors, template="auth/reset.html", step=2, redirect_to=url_for("auth.login"),
                   message=_("Parol yangilandi. Yangi parol bilan kiring"))


@bp.post("/parol-tiklash/kod")
def reset_code():
    who = field("who")
    errors = validate({"who": (who, check_login)})
    if not errors:
        session["reset_who"] = who
    return respond(errors=errors, template="auth/reset.html", step=1,
                   redirect_to=url_for("auth.reset", kod=1), message=_("Tasdiqlash kodi yuborildi"))


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
    return redirect(url_for("auth.verify_certificate", cert_no=request.args.get("raqam", "").strip() or "-"))
