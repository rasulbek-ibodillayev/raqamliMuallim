"""Kirish, ro'yxatdan o'tish, parolni tiklash, sertifikatni tekshirish.

Foydalanuvchilar users jadvalida (parol va maxfiy so'z — xesh), sessiya — Flask-Login.
Ro'yxatdan o'tish qadamlari orasidagi ma'lumot (telefon/email, tasdiqlangani) Flask sessiyasida saqlanadi.
Tasdiqlash kodi hozircha har doim 123456: Telegram bot va email yuborish hali ulanmagan.
"""
from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_babel import gettext as _
from flask_login import login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..forms import (fmt_phone, REGIONS, check_secret, check_email, check_login, check_name, check_otp, check_password, check_phone,
                     field, norm_phone, otp_code, required, respond, validate)
from ..models.users import User
from ..roles import HOME, safe_next

bp = Blueprint("auth", __name__)

DEMO_OTP = "123456"

# Kirgandan keyin ?next= faqat o'z bo'limiga olib boradi (boshqa rol bo'limi — 403 bo'lardi)
_AREA = {"user": ("/app", "/test"), "expert": ("/ekspert",), "admin": ("/admin",)}


def _now():
    return datetime.now(timezone.utc)


def _sign_in(user: User):
    """Kirish: «eslab qolish» bilan (telefonda PWA har safar parol so'ramasin), oxirgi faollik yangilanadi."""
    login_user(user, remember=True)
    user.last_seen_at = _now()
    db.session.commit()
    session.pop("motto", None)   # bosh sahifadagi motivatsion so'z har kirishda yangilanadi


def _taken(login: str) -> bool:
    return User.by_login(login) is not None


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
    nxt = safe_next(request.values.get("next"))
    if request.method == "GET":
        return render_template("auth/login.html", error=request.args.get("xato"), next_url=nxt)
    login_v, pw = field("login"), request.form.get("pw", "")
    errors = validate({"login": (login_v, check_login), "pw": (pw, required)})
    user = None
    if not errors:
        user = User.by_login(login_v)
        # Qaysi biri xato ekani aytilmaydi: begona odam ro'yxatdan o'tgan raqamlarni bilib olmasin
        if user is None or not user.check_password(pw):
            errors = {"pw": _("Telefon/email yoki parol noto‘g‘ri")}
        elif not user.is_active:
            errors = {"login": _("Akkaunt bloklangan. Yordam xizmatiga yozing")}
    if errors:
        return respond(errors=errors, template="auth/login.html", next_url=nxt)
    _sign_in(user)
    to = nxt if nxt and nxt.startswith(_AREA[user.role]) else url_for(HOME[user.role])
    return respond(errors={}, template="auth/login.html", redirect_to=to, message=_("Xush kelibsiz!"))


@bp.route("/royxat", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", reg_step=1)
    phone = field("phone")
    errors = validate({"phone": (phone, required, check_phone)})
    if not errors and _taken(phone):
        errors = {"phone": _("Bu raqam bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang")}
    if not errors:
        session["reg_phone"] = norm_phone(phone)
        session.pop("reg_email", None)
        session.pop("reg_verified", None)
    return respond(errors=errors, template="auth/register.html", reg_step=1, redirect_to=url_for("auth.verify_telegram"))


@bp.route("/royxat/telegram", methods=["GET", "POST"])
def verify_telegram():
    phone = _fmt_phone(session.get("reg_phone", "+998901234567"))
    bot = current_app.config.get("TELEGRAM_BOT_URL", "https://t.me/raqamliMuallimBot")
    if request.method == "GET":
        return render_template("auth/verify_telegram.html", reg_step=2, phone=phone, bot_url=bot)
    code = otp_code()
    errors = validate({"otp": (code, check_otp, _otp_matches)})
    if not errors and not session.get("reg_phone"):
        errors = {"otp": _("Avval telefon raqamingizni kiriting")}
    if not errors:
        session["reg_verified"] = "phone"
    return respond(errors=errors, template="auth/verify_telegram.html", reg_step=2, phone=phone, bot_url=bot,
                   redirect_to=url_for("auth.details"))


@bp.post("/royxat/email/kod")
def send_email_code():
    email = field("email").lower()
    errors = validate({"email": (email, required, check_email)})
    if not errors and _taken(email):
        errors = {"email": _("Bu email bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang")}
    if not errors:
        session["reg_email"] = email
        session.pop("reg_phone", None)
        session.pop("reg_verified", None)
    return respond(errors=errors, template="auth/verify_email.html", reg_step=2,
                   message=_("Kod %(email)s manziliga yuborildi", email=email), redirect_to=url_for("auth.verify_email", yuborildi=1))


@bp.route("/royxat/email", methods=["GET", "POST"])
def verify_email():
    sent = bool(session.get("reg_email")) and bool(request.args.get("yuborildi") or request.method == "POST")
    if request.method == "GET":
        return render_template("auth/verify_email.html", reg_step=2, sent=sent, email=session.get("reg_email", ""))
    email, code = field("email").lower(), otp_code()
    errors = validate({"email": (email, required, check_email), "otp": (code, check_otp, _otp_matches)})
    # Kod aynan shu emailga yuborilgan bo'lishi kerak
    if not errors and email != session.get("reg_email"):
        errors = {"email": _("Kod boshqa emailga yuborilgan. Shu email uchun kodni qayta so‘rang")}
    if not errors:
        session["reg_verified"] = "email"
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
    via = session.get("reg_verified")
    contact = session.get("reg_phone") if via == "phone" else session.get("reg_email") if via == "email" else None
    if not errors and not contact:
        errors = {"fn": _("Avval telefon raqam yoki emailni tasdiqlang")}
    if not errors:
        user = User(first_name=field("fn"), last_name=field("ln"), region=region or None, consent_at=_now(), role="user",
                    **({"phone": contact} if via == "phone" else {"email": contact}))
        user.set_password(pw)
        user.set_secret(request.form.get("secret", ""))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:   # shu orada boshqa so'rov xuddi shu raqam/email bilan ro'yxatdan o'tgan
            db.session.rollback()
            errors = {"fn": _("Bu telefon/email bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang")}
    if not errors:
        for k in ("reg_phone", "reg_email", "reg_verified"):
            session.pop(k, None)
        _sign_in(user)
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
    if not (current_app.debug or current_app.config.get("DEV_TOOLS")):
        flash(_("Google orqali kirish hali ulanmagan. Telefon yoki email bilan kiring"))
        return redirect(url_for("auth.login"))
    from ..cli import demo_user
    _sign_in(demo_user("user"))
    flash(_("Google akkaunti orqali kirdingiz (namuna)"))
    return redirect(url_for("user.home"))


@bp.get("/chiqish")
def logout():
    # Tartib muhim: logout_user() «eslab qolish» cookie'sini o'chirish belgisini sessiyaga yozadi,
    # undan oldin session.clear() qilinmasa bu belgi o'chib ketadi va cookie foydalanuvchini qayta kiritadi
    session.clear()
    logout_user()
    resp = redirect(url_for("auth.login"))
    # Umumiy (maktab) kompyuterlarida keyingi foydalanuvchi oldingisining keshlangan sahifalari, AI suhbati
    # va eslatmalarini ko'rmasin: brauzer kesh va saytning lokal xotirasini (Service Worker ham) tozalaydi
    resp.headers["Clear-Site-Data"] = '"cache", "storage"'
    return resp


@bp.route("/taklif/<token>", methods=["GET", "POST"])
def invite(token):
    """Ekspert taklifnomasi: admin yuborgan havola orqali ekspert parolni o'zi o'rnatadi va akkaunt yaratiladi.
    Havola faqat taklif qilingan telefon (Telegram) yoki emailga yuborilgani uchun egalik shu bilan tasdiqlanadi."""
    from .. import invites
    state, data = invites.read(token)
    ctx = {"state": state, "inv": data, "via": invites.channel(data["c"]) if data else None,
           "contact": (fmt_phone(data["c"]) if data and "@" not in data["c"] else (data or {}).get("c"))}
    if request.method == "GET" or state != "valid":
        return render_template("auth/invite.html", **ctx), (200 if state == "valid" else 410 if state in ("expired", "used") else 404)
    pw = request.form.get("pw", "")
    errors = validate({
        "pw": (pw, check_password),
        "pw2": (request.form.get("pw2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
        "secret": (request.form.get("secret", ""), lambda v: check_secret(v, pw)),
        "agree": (request.form.get("agree"), lambda v: None if v else _("Shartlarga rozilik bildiring")),
    })
    if not errors and _taken(data["c"]):
        errors = {"pw": _("Bu telefon/email bilan akkaunt allaqachon bor. Kirish sahifasidan kiring")}
    if not errors:
        # Yo'nalishlar (areas) va huquqlar (perms) uchun users'da hali ustun yo'q: expert_invites bilan qo'shiladi
        first, last = (data["n"].split(maxsplit=1) + [""])[:2]
        contact = data["c"].lower() if "@" in data["c"] else norm_phone(data["c"])
        user = User(first_name=first, last_name=last, role="expert", consent_at=_now(),
                    **({"email": contact} if "@" in contact else {"phone": contact}))
        user.set_password(pw)
        user.set_secret(request.form.get("secret", ""))
        db.session.add(user)
        db.session.commit()
        invites.mark_used(token)
        _sign_in(user)
    return respond(errors=errors, template="auth/invite.html", **ctx, redirect_to=url_for("expert.questions"),
                   message=_("Akkauntingiz yaratildi. Xush kelibsiz, %(name)s!", name=data["n"].split()[0]))


@bp.get("/taklif/namuna")
def invite_demo():
    """/ekranlar uchun: namunaviy taklifnoma (yangi token) yoki ?holat=eskirgan|yaroqsiz holatlari."""
    from .. import invites
    holat = request.args.get("holat")
    if holat == "eskirgan":
        return render_template("auth/invite.html", state="expired", inv=None, via=None, contact=None), 410
    if holat == "yaroqsiz":
        return redirect(url_for("auth.invite", token="buzilgan-havola"))
    token = invites.make("Nodira Saidova", "+998935551122", ["Dasturlash", "Algoritmlar"], ["questions", "review"])
    return redirect(url_for("auth.invite", token=token))


@bp.get("/maxfiylik")
def privacy():
    return render_template("auth/privacy.html")


# Parolni tiklash holati sessiyada: reset_who (kod yuborilgan manzil), reset_verified (kod tasdiqlangan),
# reset_fails (noto'g'ri kod urinishlari). Yangi parol faqat kod tasdiqlangandan keyin so'raladi va qabul qilinadi.
RESET_MAX_FAILS = 5



def _reset_ctx(**extra):
    who = extra.pop("who", None) or session.get("reset_who", "")
    return {"sent": bool(session.get("reset_who")), "verified": bool(session.get("reset_who")) and bool(session.get("reset_verified")),
            "who": who, "via": "email" if "@" in who else ("phone" if who else ""),
            "bot_url": current_app.config.get("TELEGRAM_BOT_URL", "https://t.me/raqamliMuallimBot"), **extra}


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
        # Email ro'yxatda bo'lmasa ham jarayon bir xil ko'rinadi (kimning emaili borligi oshkor bo'lmasin)
        user = User.by_login(who)
        if user is not None:
            user.set_password(pw)
            db.session.commit()
        for k in ("reset_who", "reset_verified", "reset_fails"):
            session.pop(k, None)
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(),
                   redirect_to=url_for("auth.login"), message=_("Parol yangilandi. Yangi parol bilan kiring"))


@bp.post("/parol-tiklash/kod")
def reset_code():
    """Kod yuborish (va qayta yuborish). Har yangi yuborishda avvalgi tasdiq bekor bo'ladi."""
    who = field("who")
    errors = validate({"who": (who, check_login)})
    # Telegram bot raqamni users.phone bilan solishtiradi: topilmasa kod yuborilmaydi
    if not errors and "@" not in who and not _taken(who):
        errors = {"who": _("Bu raqam orqali ro‘yxatdan o‘tilmagan. Raqamni tekshiring yoki email orqali tiklang")}
    if not errors:
        session["reset_who"] = who
        session.pop("reset_verified", None)
        session.pop("reset_fails", None)
    msg = (_("Kod %(c)s manziliga yuborildi", c=who) if "@" in who
           else _("Telegram botni oching va raqamingizni ulashing: bot %(c)s raqamini tekshirib, kod yuboradi", c=fmt_phone(norm_phone(who)))) if not errors else None
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(who=who),
                   redirect_to=url_for("auth.reset", kod=1), message=msg, data={"via": "email" if "@" in who else "phone"})


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


# --- Maxfiy so'z orqali tiklash (2 bosqich) ---
# 1) eski telefon raqam yoki email + maxfiy so'z (login bazada bo'lsa va maxfiy so'z mos kelsa) →
# 2) yangi parol (2 marta) → parol o'zgaradi va foydalanuvchi akkauntiga kiradi.
# Holat sessiyada: recover = {"step": 1|2, "uid", "fails"}. Maxfiy so'z users.secret_hash bilan solishtiriladi.
# Urinishlar hisobi hozircha sessiyada (keyin audit_log va IP bo'yicha cheklov).
RECOVER_MAX_FAILS = 5


def _recover():
    return session.get("recover") or {"step": 1, "fails": 0}


def _recover_ctx(rec, **extra):
    return {"rstep": rec.get("step", 1), "locked": rec.get("fails", 0) >= RECOVER_MAX_FAILS,
            "fails_left": RECOVER_MAX_FAILS - rec.get("fails", 0), **extra}


@bp.route("/parol-tiklash/maxfiy-soz", methods=["GET", "POST"])
def recover():
    rec = _recover()
    if request.method == "GET":
        if request.args.get("qayta"):
            rec = {"step": 1, "fails": rec.get("fails", 0)}
            session["recover"] = rec
        return render_template("auth/recover.html", **_recover_ctx(rec))

    # 1-bosqich: eski telefon/email va maxfiy so'z
    if rec.get("fails", 0) >= RECOVER_MAX_FAILS:
        return respond(errors={"secret": _("Urinishlar tugadi. 30 daqiqadan keyin qayta urinib ko‘ring yoki yordam xizmatiga yozing")},
                       template="auth/recover.html", **_recover_ctx(rec))
    who, secret = field("who"), request.form.get("secret", "")
    errors = validate({"who": (who, check_login), "secret": (secret, required)})
    user = User.by_login(who) if not errors else None
    if not errors and (user is None or not user.check_secret(secret)):
        rec["fails"] = rec.get("fails", 0) + 1
        session["recover"] = rec
        left = RECOVER_MAX_FAILS - rec["fails"]
        errors = {"secret": _("Telefon/email yoki maxfiy so‘z noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=left) if left
                  else _("Urinishlar tugadi. 30 daqiqadan keyin qayta urinib ko‘ring yoki yordam xizmatiga yozing")}
    if not errors:
        session["recover"] = {"step": 2, "fails": 0, "uid": user.id}
    return respond(errors=errors, template="auth/recover.html", **_recover_ctx(rec),
                   redirect_to=url_for("auth.recover"), data={"step": 2})


@bp.post("/parol-tiklash/maxfiy-soz/parol")
def recover_confirm():
    """2-bosqich: yangi parol (2 marta) → parol o'zgaradi va foydalanuvchi akkauntiga kiradi."""
    rec = _recover()
    if rec.get("step", 1) < 2:
        return redirect(url_for("auth.recover"))
    pw = request.form.get("p1", "")
    errors = validate({
        "p1": (pw, check_password),
        "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
    })
    user = db.session.get(User, rec["uid"]) if rec.get("uid") else None
    if not errors and user is None:
        session.pop("recover", None)
        return redirect(url_for("auth.recover"))
    if not errors:
        user.set_password(pw)
        db.session.commit()
        session.pop("recover", None)
        _sign_in(user)
    return respond(errors=errors, template="auth/recover.html", **_recover_ctx(rec),
                   redirect_to=url_for("user.home"), message=_("Parol yangilandi, akkauntingizga kirdingiz"))


# --- Sertifikatni tekshirish (ommaviy, QR-koddan) ---
# Namunada: INF-2026-000123 — haqiqiy, INF-2023-000099 — muddati o‘tgan (sertifikat 3 yil amal qiladi), qolgani — topilmadi
_CERT_STATES = {"INF-2026-000123": "valid", "INF-2023-000099": "expired"}


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
