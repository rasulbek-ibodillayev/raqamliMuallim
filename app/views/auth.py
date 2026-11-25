"""Kirish, ro'yxatdan o'tish, parolni tiklash, sertifikatni tekshirish.

Foydalanuvchilar users jadvalida (parol va maxfiy so'z — xesh), sessiya — Flask-Login.
Ro'yxatdan o'tish qadamlari orasidagi ma'lumot (telefon/email, tasdiqlangani) Flask sessiyasida saqlanadi.
Urinishlar hisobi sessiyada emas, bazada (services/limits.py): cookie'ni o'chirish yoki eskisini qayta yuborish yordam bermaydi.
Tasdiqlash kodi — services/codes.py (Telegram bot va email hali ulanmagan).
"""
import secrets
import time
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_babel import gettext as _
from flask_login import login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..forms import (fmt_phone, REGIONS, check_secret, check_email, check_login, check_name, check_otp, check_password, check_phone,
                     field, norm_phone, otp_code, required, respond, validate, wants_json)
from ..models.users import User
from ..roles import HOME, safe_next
from ..services import codes, google_auth, limits

bp = Blueprint("auth", __name__)

# Kirgandan keyin ?next= faqat o'z bo'limiga olib boradi (boshqa rol bo'limi — 403 bo'lardi)
_AREA = {"user": ("/app", "/test"), "expert": ("/ekspert",), "admin": ("/admin",)}


def _now():
    return datetime.now(timezone.utc)


def _sign_in(user: User):
    """Kirish: «eslab qolish» bilan (telefonda PWA har safar parol so'ramasin), oxirgi faollik yangilanadi."""
    login_user(user, remember=True, duration=user.remember_for)
    user.last_seen_at = _now()
    db.session.commit()
    session.pop("motto", None)   # bosh sahifadagi motivatsion so'z har kirishda yangilanadi


def _taken(login: str) -> bool:
    return User.by_login(login) is not None


def _password_changed(user: User, via: str) -> None:
    """Parol tiklandi: jurnalga yoziladi va egasiga bildirishnoma boradi (o'zi qilmagan bo'lsa bilib qoladi). Commit qilmaydi."""
    from ..services import admin_users, notify
    admin_users.log(user.id, "reset_used" if via == "link" else "password_reset", "user", user.id)
    if user.role == "user":
        notify.add(user.id, notify.PASSWORD)


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
        user, errors = _authenticate(login_v, pw)
    if errors:
        return respond(errors=errors, template="auth/login.html", next_url=nxt)
    _sign_in(user)
    _link_google(user)
    to = nxt if nxt and nxt.startswith(_AREA[user.role]) else url_for(HOME[user.role])
    return respond(errors={}, template="auth/login.html", redirect_to=to, message=_("Xush kelibsiz!"))


def _authenticate(login_v: str, pw: str) -> tuple[User | None, dict]:
    who, ip = codes.target(login_v), limits.client_ip()
    by_ip, by_pair, by_login = ("login_ip", ip), ("login", f"{who}|{ip}"), ("login_all", who)
    r = limits.take(by_ip, by_pair, by_login)
    if r.blocked:
        return None, {"pw": limits.message(r.wait)}
    user = User.by_login(login_v)
    if user is None or not user.password_hash:
        User.spend_hash_time(pw)
        user = None
    # Qaysi biri xato ekani aytilmaydi: begona odam ro'yxatdan o'tgan raqamlarni bilib olmasin
    if user is None or not user.check_password(pw):
        if not r.left:
            return None, {"pw": limits.message(limits.RULES["login"][1])}
        wrong = _("Telefon/email yoki parol noto‘g‘ri")
        return None, {"pw": _("%(e)s. Yana %(n)s ta urinish qoldi", e=wrong, n=r.left) if r.left <= 2 else wrong}
    limits.refund(by_ip, by_login)
    limits.clear(by_pair)
    if not user.is_active:
        return None, {"login": _("Akkaunt bloklangan. Yordam xizmatiga yozing")}
    return user, {}


@bp.route("/royxat", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", reg_step=1)
    phone = field("phone")
    errors = validate({"phone": (phone, required, check_phone)})
    if not errors:
        err = codes.lookup() or (_("Bu raqam bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang") if _taken(phone)
                                 else codes.send(phone))
        errors = {"phone": err} if err else {}
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
    errors = validate({"otp": (code, check_otp)})
    if not errors:
        err = (codes.verify(session["reg_phone"], code)[0] if session.get("reg_phone")
               else _("Avval telefon raqamingizni kiriting"))
        errors = {"otp": err} if err else {}
    if not errors:
        session["reg_verified"] = "phone"
    return respond(errors=errors, template="auth/verify_telegram.html", reg_step=2, phone=phone, bot_url=bot,
                   redirect_to=url_for("auth.details"))


@bp.post("/royxat/email/kod")
def send_email_code():
    email = field("email").lower()
    errors = validate({"email": (email, required, check_email)})
    if not errors:
        err = codes.lookup() or (_("Bu email bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang") if _taken(email)
                                 else codes.send(email))
        errors = {"email": err} if err else {}
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
    errors = validate({"email": (email, required, check_email), "otp": (code, check_otp)})
    # Kod aynan shu emailga yuborilgan bo'lishi kerak
    if not errors and email != session.get("reg_email"):
        errors = {"email": _("Kod boshqa emailga yuborilgan. Shu email uchun kodni qayta so‘rang")}
    if not errors:
        err, _dead = codes.verify(email, code)
        errors = {"otp": err} if err else {}
    if not errors:
        session["reg_verified"] = "email"
    return respond(errors=errors, template="auth/verify_email.html", reg_step=2, sent=True, email=email,
                   redirect_to=url_for("auth.details"))


@bp.route("/royxat/malumotlar", methods=["GET", "POST"])
def details():
    via = session.get("reg_verified")
    # Google orqali: parol va maxfiy so'z so'ralmaydi (parol keyin «Parolni tiklash» orqali o'rnatiladi)
    g = session.get("reg_google") if via == "google" else None
    ctx = {"reg_step": 3, "regions": REGIONS, "google": g}
    if request.method == "GET":
        return render_template("auth/details.html", **ctx, **({"form": {"fn": g["first"], "ln": g["last"]}} if g else {}))
    pw = request.form.get("pw", "")
    region = field("region")
    errors = validate({
        "fn": (field("fn"), lambda v: check_name(v, "first")),
        "ln": (field("ln"), lambda v: check_name(v, "last")),
        **({} if g else {
            "pw": (pw, check_password),
            "pw2": (request.form.get("pw2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
            "secret": (request.form.get("secret", ""), lambda v: check_secret(v, pw))}),
        "region": (region, lambda v: None if not v or v in REGIONS else _("Viloyatni ro‘yxatdan tanlang")),
        "consent": (request.form.get("consent"), lambda v: None if v else _("Davom etish uchun rozilik kerak")),
    })
    contact = (g["email"] if g else session.get("reg_phone") if via == "phone" else session.get("reg_email") if via == "email" else None)
    if not errors and not contact:
        errors = {"fn": _("Avval telefon raqam yoki emailni tasdiqlang")}
    if not errors:
        user = User(first_name=field("fn"), last_name=field("ln"), region=region or None, consent_at=_now(), role="user",
                    **({"phone": contact} if via == "phone" else {"email": contact}))
        if g:
            user.google_sub = g["sub"]
        else:
            user.set_password(pw)
            user.set_secret(request.form.get("secret", ""))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:   # shu orada boshqa so'rov xuddi shu raqam/email bilan ro'yxatdan o'tgan
            db.session.rollback()
            errors = {"fn": _("Bu telefon/email bilan ro‘yxatdan o‘tilgan. Kiring yoki parolni tiklang")}
    if not errors:
        for k in ("reg_phone", "reg_email", "reg_verified", "reg_google"):
            session.pop(k, None)
        _sign_in(user)
    return respond(errors=errors, template="auth/details.html", **ctx,
                   redirect_to=url_for("user.home", yangi=1),
                   message=_("Ro‘yxatdan o‘tdingiz. Eslatma: 6 oy kirilmasa akkaunt avtomatik o‘chiriladi"))


# --- Google orqali kirish va ro'yxatdan o'tish ---
# Google → /kirish/google/qaytish: google_sub bo'yicha akkaunt bor — kiradi; yo'q — ism va rozilik so'raladi (details).
# Shu emailli akkaunt avvaldan bo'lsa, avtomatik bog'lanmaydi: egasi parol bilan bir marta kirgach bog'lanadi (aks holda
# birovning emailini oldindan ro'yxatdan o'tkazib qo'ygan odam uning akkauntiga kirib qolardi).

def _google_cfg():
    cfg = current_app.config
    return (cfg["GOOGLE_CLIENT_ID"], cfg["GOOGLE_CLIENT_SECRET"]) if cfg.get("GOOGLE_CLIENT_ID") and cfg.get("GOOGLE_CLIENT_SECRET") else None


def _to_login(message):
    flash(message)
    return redirect(url_for("auth.login"))


@bp.get("/kirish/google")
def google():
    cfg = _google_cfg()
    if cfg:
        url, flow = google_auth.begin(cfg[0], url_for("auth.google_back", _external=True))
        session["google"] = {**flow, "next": safe_next(request.args.get("next"))}
        return redirect(url)
    if not (current_app.debug or current_app.config.get("DEV_TOOLS")):
        return _to_login(_("Google orqali kirish hali ulanmagan. Telefon yoki email bilan kiring"))
    # Ishlab chiqishda, kalitsiz: ro'yxatdan o'tish sahifasidan — yangi akkaunt, kirishdan — namunaviy o'qituvchi
    if request.args.get("yangi"):
        return _google_signup({"sub": "namuna-google", "email": "namuna.google@example.com", "first": "Malika", "last": "Tursunova"})
    from ..cli import demo_user
    _sign_in(demo_user("user"))
    flash(_("Google akkaunti orqali kirdingiz (namuna)"))
    return redirect(url_for("user.home"))


@bp.get("/kirish/google/qaytish")
def google_back():
    cfg, flow = _google_cfg(), session.pop("google", None)
    state, code = request.args.get("state", ""), request.args.get("code", "")
    if not cfg or not flow or not secrets.compare_digest(state.encode(), flow["state"].encode()) or not code:
        return _to_login(_("Google orqali kirish bekor qilindi. Qayta urinib ko‘ring"))
    try:
        who = google_auth.finish(*cfg, url_for("auth.google_back", _external=True), code, flow)
    except google_auth.GoogleError as e:
        current_app.logger.warning("Google: %s", e)
        return _to_login(_("Google bilan bog‘lanib bo‘lmadi. Qayta urinib ko‘ring"))
    return _google_signup(who, flow.get("next"))


def _google_signup(who: dict, nxt: str | None = None):
    user = db.session.scalar(db.select(User).where(User.google_sub == who["sub"]))
    if user is not None:
        if not user.is_active:
            return _to_login(_("Akkaunt bloklangan. Yordam xizmatiga yozing"))
        _sign_in(user)
        return redirect(nxt if nxt and nxt.startswith(_AREA[user.role]) else url_for(HOME[user.role]))
    if _taken(who["email"]):
        session["google_link"] = {"sub": who["sub"], "email": who["email"]}
        return _to_login(_("Bu email bilan akkaunt bor. Bir marta parol bilan kiring, keyin Google orqali ham kira olasiz"))
    for k in ("reg_phone", "reg_email", "google_link"):
        session.pop(k, None)
    session.update(reg_verified="google", reg_google=who)
    return redirect(url_for("auth.details"))


def _link_google(user: User):
    """Parol bilan kirgan foydalanuvchiga shu brauzerda kutayotgan Google akkauntini bog'laydi (email bir xil bo'lsa)."""
    link = session.pop("google_link", None)
    if not link or user.email != link["email"] or user.google_sub or user.role != "user":
        return
    user.google_sub = link["sub"]
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    else:
        flash(_("Google akkauntingiz bog‘landi"))


@bp.get("/chiqish")
def logout():
    # Boshqa sayt shu havolani ochtirib, eslatmalar va yuborilmagan javoblarni (brauzer xotirasi) o'chirtira olmasin
    if request.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
        return redirect(url_for("auth.guest"))
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
    """Ekspert taklifnomasi: admin bergan havola orqali ekspert parolni o'zi o'rnatadi va akkaunt yaratiladi."""
    from .. import invites
    from ..services import admin_stats, admin_users, experts
    state, inv = invites.read(token)
    ctx = {"state": state, "inv": inv, "via": invites.channel(inv.contact) if inv else None,
           "areas": (admin_stats.section_titles(inv.areas) or [_("Barcha mavzular")]) if inv else [],
           "contact": (fmt_phone(inv.contact) if "@" not in inv.contact else inv.contact) if inv else None}
    if request.method == "GET" or state != "valid":
        return render_template("auth/invite.html", **ctx), (200 if state == "valid" else 410 if state in ("expired", "used") else 404)
    pw = request.form.get("pw", "")
    errors = validate({
        "pw": (pw, check_password),
        "pw2": (request.form.get("pw2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
        "secret": (request.form.get("secret", ""), lambda v: check_secret(v, pw)),
        "agree": (request.form.get("agree"), lambda v: None if v else _("Shartlarga rozilik bildiring")),
    })
    if not errors and _taken(inv.contact):
        errors = {"pw": _("Bu telefon/email bilan akkaunt allaqachon bor. Kirish sahifasidan kiring")}
    if not errors:
        first, last = (inv.name.split(maxsplit=1) + [""])[:2]
        user = User(first_name=first[:80], last_name=last[:80], role="expert", consent_at=_now(),
                    **({"email": inv.contact} if "@" in inv.contact else {"phone": inv.contact}))
        user.set_password(pw)
        user.set_secret(request.form.get("secret", ""))
        db.session.add(user)
        try:
            db.session.flush()
            experts.save(user.id, inv.perms, inv.areas)
            inv.used_at = _now()
            admin_users.log(user.id, "create", "expert", user.id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            errors = {"pw": _("Bu telefon/email bilan akkaunt allaqachon bor. Kirish sahifasidan kiring")}
    if not errors:
        _sign_in(user)
    return respond(errors=errors, template="auth/invite.html", **ctx, redirect_to=url_for("expert.questions"),
                   message=None if errors else _("Akkauntingiz yaratildi. Xush kelibsiz, %(name)s!", name=user.first_name))


@bp.route("/parol-tiklash/havola/<token>", methods=["GET", "POST"])
def reset_link(token):
    """Admin bergan bir martalik havola: foydalanuvchi parolni o'zi o'rnatadi (24 soat, parol almashgach ishlamaydi)."""
    from .. import invites
    user = invites.read_reset(token)
    if request.method == "GET" or user is None:
        return render_template("auth/reset_link.html", user=user), 200 if user else 410
    pw = request.form.get("p1", "")
    errors = validate({"p1": (pw, check_password),
                       "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas"))})
    if not errors:
        user.set_password(pw)
        _password_changed(user, "link")
        db.session.commit()
    return respond(errors=errors, template="auth/reset_link.html", user=user, redirect_to=url_for("auth.login"),
                   message=_("Parol yangilandi. Yangi parol bilan kiring"))


@bp.get("/taklif/namuna")
def invite_demo():
    """/ekranlar uchun: namunaviy taklifnoma (yangi token) yoki ?holat=eskirgan|yaroqsiz holatlari."""
    from .. import invites
    if not (current_app.debug or current_app.config.get("DEV_TOOLS")):
        return redirect(url_for("auth.login"))
    holat = request.args.get("holat")
    if holat == "eskirgan":
        return render_template("auth/invite.html", state="expired", inv=None, via=None, contact=None), 410
    if holat == "yaroqsiz":
        return redirect(url_for("auth.invite", token="buzilgan-havola"))
    inv = invites.make("Nodira Saidova", "+998935551122", [], ["questions", "review"])
    db.session.commit()
    return redirect(url_for("auth.invite", token=invites.token(inv)))


@bp.get("/maxfiylik")
def privacy():
    return render_template("auth/privacy.html")


# Parolni tiklash holati sessiyada: reset_who (kod yuborilgan manzil), reset_verified (kod tasdiqlangan vaqt va akkaunt belgisi).
# Yangi parol faqat kod tasdiqlangandan keyin, 15 daqiqa ichida qabul qilinadi. Sessiya — cookie: eskisini qayta yuborish
# mumkin, shuning uchun User.auth_tag saqlanadi — parol bir marta almashgach tasdiq o'z-o'zidan bekor bo'ladi.
STEP_AGE = 15 * 60


def _tag(user: User | None) -> str:
    return user.auth_tag() if user is not None else ""


def _reset_verified() -> bool:
    who, v = session.get("reset_who"), session.get("reset_verified")
    return bool(who and isinstance(v, list) and time.time() - v[0] < STEP_AGE and v[1] == _tag(User.by_login(who)))


def _reset_ctx(**extra):
    who = extra.pop("who", None) or session.get("reset_who", "")
    return {"sent": bool(session.get("reset_who")), "verified": _reset_verified(),
            "who": who, "via": "email" if "@" in who else ("phone" if who else ""),
            "bot_url": current_app.config.get("TELEGRAM_BOT_URL", "https://t.me/raqamliMuallimBot"), **extra}


@bp.route("/parol-tiklash", methods=["GET", "POST"])
def reset():
    """Bitta sahifa: telefon/email → «Kod yuborish» → kod → (kod to'g'ri bo'lsa) yangi parol."""
    if request.method == "GET":
        if not request.args.get("kod"):
            # Sahifaga yangidan kirilganda eski jarayon boshidan boshlanadi
            for k in ("reset_who", "reset_verified"):
                session.pop(k, None)
        return render_template("auth/reset.html", **_reset_ctx())
    # Yakuniy qadam: yangi parol (kod oldinroq tasdiqlangan bo'lishi shart)
    who = session.get("reset_who")
    if not _reset_verified():
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
            _password_changed(user, "code")
            db.session.commit()
        for k in ("reset_who", "reset_verified"):
            session.pop(k, None)
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(),
                   redirect_to=url_for("auth.login"), message=_("Parol yangilandi. Yangi parol bilan kiring"))


@bp.post("/parol-tiklash/kod")
def reset_code():
    """Kod yuborish (va qayta yuborish). Har yangi yuborishda avvalgi tasdiq bekor bo'ladi."""
    who = field("who")
    errors = validate({"who": (who, check_login)})
    # Telegram bot raqamni users.phone bilan solishtiradi: topilmasa kod yuborilmaydi
    if not errors:
        err = codes.lookup() or (_("Bu raqam orqali ro‘yxatdan o‘tilmagan. Raqamni tekshiring yoki email orqali tiklang")
                                 if "@" not in who and not _taken(who) else codes.send(who))
        errors = {"who": err} if err else {}
    if not errors:
        session["reset_who"] = who
        session.pop("reset_verified", None)
    msg = (_("Kod %(c)s manziliga yuborildi", c=who) if "@" in who
           else _("Telegram botni oching va raqamingizni ulashing: bot %(c)s raqamini tekshirib, kod yuboradi", c=fmt_phone(norm_phone(who)))) if not errors else None
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(who=who),
                   redirect_to=url_for("auth.reset", kod=1), message=msg, data={"via": "email" if "@" in who else "phone"})


@bp.post("/parol-tiklash/kod-tekshirish")
def reset_verify():
    """Kodni tekshirish. To'g'ri bo'lsa — yangi parol maydonlari ochiladi. 5 ta xato urinishdan keyin kod bekor qilinadi
    (hisob bazada, raqam/email bo'yicha: yangi sessiya ochish urinishlarni tiklamaydi)."""
    who = session.get("reset_who")
    if not who:
        return respond(errors={"who": _("Avval telefon raqam yoki emailga kod yuboring")}, template="auth/reset.html", **_reset_ctx())
    if field("who") and field("who") != who:
        return respond(errors={"who": _("Telefon/email o‘zgardi. Yangisiga kodni qayta yuboring")},
                       template="auth/reset.html", **_reset_ctx())
    code = otp_code()
    errors = validate({"otp": (code, check_otp)})
    if not errors:
        err, dead = codes.verify(who, code)
        errors = {"otp": err} if err else {}
        if dead:
            session.pop("reset_who", None)
    if not errors:
        session["reset_verified"] = [int(time.time()), _tag(User.by_login(who))]
    return respond(errors=errors, template="auth/reset.html", **_reset_ctx(),
                   redirect_to=url_for("auth.reset", kod=1), message=_("Kod tasdiqlandi. Endi yangi parolni kiriting"))


# --- Maxfiy so'z orqali tiklash (2 bosqich) ---
# 1) eski telefon raqam yoki email + maxfiy so'z (login bazada bo'lsa va maxfiy so'z mos kelsa) →
# 2) yangi parol (2 marta) → parol o'zgaradi va foydalanuvchi akkauntiga kiradi.
# Holat sessiyada: recover = {"uid", "at", "tag"} — 1-bosqich o'tilgan (15 daqiqa, parol almashguncha).
# Maxfiy so'z users.secret_hash bilan solishtiriladi; urinishlar akkaunt va IP bo'yicha bazada sanaladi.

def _recover_user() -> User | None:
    rec = session.get("recover") or {}
    user = db.session.get(User, rec["uid"]) if rec.get("uid") and time.time() - rec.get("at", 0) < STEP_AGE else None
    return user if user is not None and user.is_active and rec.get("tag") == user.auth_tag() else None


def _check_secret_word(who: str, secret: str) -> tuple[User | None, dict]:
    login_id, by_ip = codes.target(who), ("secret_ip", limits.client_ip())
    r = limits.take(by_ip, ("secret", login_id), ("secret_day", login_id))
    if not r.blocked:
        user = User.by_login(who)
        if user is None or not user.secret_hash:
            User.spend_hash_time(secret)
            user = None
        if user is not None and user.check_secret(secret):
            limits.refund(by_ip)
            limits.clear(("secret", login_id), ("secret_day", login_id))
            if not user.is_active:
                return None, {"who": _("Akkaunt bloklangan. Yordam xizmatiga yozing")}
            return user, {}
        if r.left:
            return None, {"secret": _("Telefon/email yoki maxfiy so‘z noto‘g‘ri. Yana %(n)s ta urinish qoldi", n=r.left)}
    wait = limits.wait_text(r.wait or limits.RULES["secret"][1])
    return None, {"secret": _("Urinishlar tugadi. %(t)s keyin qayta urinib ko‘ring yoki yordam xizmatiga yozing", t=wait)}


@bp.route("/parol-tiklash/maxfiy-soz", methods=["GET", "POST"])
def recover():
    if request.method == "GET":
        if request.args.get("qayta"):
            session.pop("recover", None)
        return render_template("auth/recover.html", rstep=2 if _recover_user() else 1)

    # 1-bosqich: eski telefon/email va maxfiy so'z
    session.pop("recover", None)
    who, secret = field("who"), request.form.get("secret", "")
    errors = validate({"who": (who, check_login), "secret": (secret, required)})
    if not errors:
        user, errors = _check_secret_word(who, secret)
        if user:
            session["recover"] = {"uid": user.id, "at": int(time.time()), "tag": user.auth_tag()}
    return respond(errors=errors, template="auth/recover.html", rstep=1,
                   redirect_to=url_for("auth.recover"), data={"step": 2})


def _recover_expired():
    """1-bosqich o'tilmagan yoki 15 daqiqa o'tgan: boshidan (JS'da ham xato o'rniga boshlang'ich sahifa ochiladi)."""
    return redirect(url_for("auth.recover")) if not wants_json() else respond(redirect_to=url_for("auth.recover", qayta=1))


@bp.post("/parol-tiklash/maxfiy-soz/parol")
def recover_confirm():
    """2-bosqich: yangi parol (2 marta) → parol o'zgaradi va foydalanuvchi akkauntiga kiradi."""
    user = _recover_user()
    if user is None:
        session.pop("recover", None)
        return _recover_expired()
    pw = request.form.get("p1", "")
    errors = validate({
        "p1": (pw, check_password),
        "p2": (request.form.get("p2", ""), lambda v: None if v == pw else _("Parollar bir xil emas")),
    })
    if not errors:
        user.set_password(pw)
        _password_changed(user, "secret")
        db.session.commit()
        session.pop("recover", None)
        _sign_in(user)
    return respond(errors=errors, template="auth/recover.html", rstep=2,
                   redirect_to=url_for(HOME[user.role]), message=_("Parol yangilandi, akkauntingizga kirdingiz"))


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
