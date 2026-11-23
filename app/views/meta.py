"""Barcha ekranlar ro'yxati (ishlab chiqish va dizaynni ko'rib chiqish uchun)."""
from flask import Blueprint, render_template

bp = Blueprint("meta", __name__)

SCREENS = [
    ("Kirish va ro‘yxatdan o‘tish", [
        ("auth.guest", "Mehmon sahifasi", {}),
        ("auth.login", "Kirish", {}),
        ("auth.login", "Kirish — xato holati", {"xato": 1}),
        ("auth.register", "Ro‘yxatdan o‘tish · 1-qadam", {}),
        ("auth.verify_telegram", "Telegram orqali tasdiqlash · 2-qadam", {}),
        ("auth.verify_email", "Email orqali tasdiqlash · 2-qadam", {}),
        ("auth.details", "Ma’lumotlaringiz · 3-qadam", {}),
        ("auth.reset", "Parolni tiklash", {}),
        ("auth.recover", "Maxfiy so‘z orqali tiklash", {"qayta": 1}),
        ("auth.privacy", "Maxfiylik siyosati", {}),
        ("auth.invite_demo", "Ekspert taklifnomasi — parol o‘rnatish", {}),
        ("auth.invite_demo", "Ekspert taklifnomasi — muddati o‘tgan", {"holat": "eskirgan"}),
        ("auth.invite_demo", "Ekspert taklifnomasi — yaroqsiz havola", {"holat": "yaroqsiz"}),
        ("auth.verify_certificate_lookup", "Sertifikatni tekshirish — raqam kiritish", {}),
        ("auth.verify_certificate", "Sertifikatni tekshirish — haqiqiy", {"cert_no": "INF-2026-000123"}),
        ("auth.verify_certificate", "Sertifikatni tekshirish — muddati o‘tgan", {"cert_no": "INF-2023-000099"}),
        ("auth.verify_certificate", "Sertifikatni tekshirish — topilmadi", {"cert_no": "INF-2026-999999"}),
    ]),
    ("Yuklanish holatlari", [
        ("user.plan", "O‘quv reja — yuklanmoqda", {"yuklanmoqda": 1}),
        ("user.notes", "Eslatmalar — yuklanmoqda", {"yuklanmoqda": 1}),
        ("expert.queue", "Ekspert: tekshiruv navbati — yuklanmoqda", {"yuklanmoqda": 1}),
        ("admin.users", "Admin: foydalanuvchilar — yuklanmoqda", {"yuklanmoqda": 1}),
    ]),
    ("Xato sahifalari", [
        ("meta.error_preview", "404 — sahifa topilmadi", {"code": 404}),
        ("meta.error_preview", "403 — ruxsat yo‘q", {"code": 403}),
        ("meta.error_preview", "500 — server xatosi", {"code": 500}),
    ]),
    ("Asosiy", [
        ("user.home", "Bosh sahifa (dars tugallanmagan)", {}),
        ("user.home", "Bosh sahifa — mavzu yakunlangan (keyingi mavzu)", {"holat": "tugadi"}),
        ("user.home", "Bosh sahifa — majburiy nazorat navbati", {"holat": "nazorat"}),
        ("user.home", "Dam olish tavsiyasi (45 daqiqa)", {"dam": 1}),
        ("user.home", "Majburiy tanaffus (5-rad etish)", {"dam": "majburiy"}),
        ("user.home", "Bosh sahifa — yangi foydalanuvchi", {"yangi": 1, "qadam": 1}),
        ("user.home", "Bosh sahifa — ilovani o‘rnatish (Android)", {"pwa": 1}),
        ("user.home", "Bosh sahifa — ilovani o‘rnatish (iPhone)", {"pwa": "ios"}),
        ("user.diagnostic", "Diagnostika taklifi", {}),
        ("user.diagnostic_result", "Diagnostika natijasi", {}),
        ("user.offline", "Oflayn holat", {}),
    ]),
    ("O‘quv reja", [
        ("user.plan", "O‘quv reja (diagnostika asosida)", {}),
        ("user.plan", "O‘quv reja — oylik test vaqti kelgan", {"oylik": 1}),
        ("meta.sample_topic", "Mavzu tafsiloti (bazadan; avval `flask kontent-yuklash`)", {"kind": "mavzu"}),
    ]),
    ("Dars va AI tutor", [
        ("meta.sample_topic", "Dars — bazadagi bloklardan", {"kind": "dars"}),
        ("user.lesson", "Dars sahifasi (namuna)", {}),
        ("user.lesson", "Dars — qayta o‘qitish", {"holat": "qayta"}),
        ("user.lesson", "Dars — audio pleyer", {"audio": 1}),
        ("user.tutor", "AI tutor", {}),
        ("user.notes", "Eslatmalar", {}),
    ]),
    ("Testlar", [
        ("user.tests", "Testlar", {}),
        ("user.tests", "Testlar — yakunlanmagan majburiy test (oylik)", {"oylik": 1}),
        ("user.tests", "Testlar — yakshanba emas (haftalik yopiq)", {"kun": "boshqa"}),
        ("test.question", "Savol — yopiq test", {"tur": "yopiq"}),
        ("test.question", "Savol — bir nechta javob", {"tur": "kop"}),
        ("test.question", "Savol — moslashtirish", {"tur": "moslash"}),
        ("test.question", "Savol — ochiq javob", {"tur": "ochiq"}),
        ("test.question", "Savol — jadvalli", {"tur": "jadval"}),
        ("test.question", "Savol — rasmli", {"tur": "rasm"}),
        ("test.question", "Savol — oflayn rejimda", {"tur": "yopiq", "oflayn": 1}),
        ("test.question", "Savol — dars testi (3 ta)", {"turi": "dars", "soni": 3}),
        ("test.stage", "Bosqichlar orasida (oraliq sinov)", {"turi": "oraliq"}),
        ("test.result", "Natija — o‘tdi", {}),
        ("test.result", "Natija — qaytarildi", {"holat": "qaytarildi"}),
        ("user.control", "Nazorat oldidan", {}),
        ("user.optional", "Ixtiyoriy test", {}),
        ("test.exam", "Attestatsiya testi (savollar navigatori bilan)", {"namuna": 1}),
        ("test.exam", "Attestatsiya testi — jadvalli savol", {"savol": 5, "namuna": 1}),
        ("test.exam", "Attestatsiya testi — rasmli savol", {"savol": 8, "namuna": 1}),
        ("test.exam", "Attestatsiya testi — yakunlashni tasdiqlash", {"yakun": 1, "namuna": 1}),
        ("test.exam_result", "Attestatsiya testi — natija va tahlil", {}),
    ]),
    ("Natijalar va tahlil", [
        ("user.results", "Natijalarim", {}),
        ("user.results", "Natijalarim — bo‘sh holat", {"bosh": 1}),
        ("user.result_detail", "Natija tafsiloti: savollar va javoblar", {"rid": 3}),
        ("user.errors", "Xatolar analitikasi", {}),
    ]),
    ("Muhokama, e’tiroz, sertifikat", [
        ("user.discussions", "Muhokamalar", {}),
        ("user.discussion", "Muhokama (savol bo‘yicha)", {}),
        ("user.objections", "E’tirozlarim", {}),
        ("user.certificates", "Sertifikatlarim", {}),
        ("user.certificate_print", "Sertifikat — bosma ko‘rinish", {}),
        ("user.profile", "Profil", {}),
        ("user.help", "Yordam", {}),
    ]),
    ("Ekspert paneli", [
        ("expert.questions", "Savollar banki (kartalar bilan)", {}),
        ("expert.queue", "Tekshiruv navbati — AI savollari", {}),
        ("expert.editor", "Savol qo‘shish", {}),
        ("expert.topics", "Mavzular va dars muharriri", {}),
        ("expert.objections", "E’tirozlar", {}),
        ("expert.profile", "Ekspert profili", {}),
    ]),
    ("Admin paneli", [
        ("admin.stats", "Statistika", {}),
        ("admin.users", "Foydalanuvchilar", {}),
        ("admin.user_detail", "Foydalanuvchi — to‘liq ma’lumot", {"uid": 1}),
        ("admin.experts", "Ekspertlar", {}),
        ("admin.experts", "Ekspertlar — javob kutayotgan taklifnoma", {"namuna": 1}),
        ("admin.settings", "Sozlamalar", {}),
        ("admin.profile", "Admin profili", {}),
    ]),
]


@bp.get("/sw.js")
def service_worker():
    # Service Worker butun saytni boshqarishi uchun ildiz manzildan beriladi
    from flask import current_app, send_from_directory
    resp = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.get("/favicon.ico")
def favicon():
    # Ba'zi brauzerlar <link rel="icon"> ga qaramay /favicon.ico ni so'raydi
    from flask import current_app, send_from_directory
    return send_from_directory(current_app.static_folder, "icons/favicon-32.png", mimetype="image/png", max_age=86400)


@bp.get("/xato/<int:code>")
def error_preview(code):
    """Xato sahifalarini /ekranlar ro'yxatidan ko'rish uchun."""
    return render_template("errors/error.html", code=code)


def _dev_tools_only():
    """/ekranlar va /_rol faqat ishlab chiqishda ochiladi (debug yoki DEV_TOOLS); aks holda 404."""
    from flask import abort, current_app
    if not (current_app.debug or current_app.config.get("DEV_TOOLS")):
        abort(404)


@bp.get("/_rol/<role>")
def as_role(role):
    """Faqat ishlab chiqish uchun: shu roldagi namunaviy akkauntga kirib, sahifani ochish
    (/ekranlar havolalari shu orqali o'tadi). Akkaunt bo'lmasa yaratiladi (app/cli.py)."""
    from flask import abort, redirect, request, url_for
    from flask_login import login_user

    from ..cli import demo_user
    from ..roles import HOME, ROLES, safe_next
    _dev_tools_only()
    if role not in ROLES:
        abort(404)
    login_user(demo_user(role))
    return redirect(safe_next(request.args.get("next")) or url_for(HOME[role]))


@bp.get("/_namuna/<kind>")
def sample_topic(kind):
    """Faqat ishlab chiqish uchun: bazadagi darsi bor birinchi mavzuning sahifasi yoki darsi (/ekranlar havolalari).
    Mavzu ID'lari kontent qayta yuklanganda o'zgaradi, shuning uchun ro'yxatda qattiq raqam yozilmaydi."""
    from flask import abort, redirect, url_for
    from sqlalchemy import select

    from ..extensions import db
    from ..models import ContentBlock, Subtopic, Topic
    _dev_tools_only()
    if kind not in ("mavzu", "dars"):
        abort(404)
    tid = db.session.scalar(select(Topic.id).join(Subtopic).join(ContentBlock)
                            .where(Topic.is_published.is_(True)).order_by(Topic.id).limit(1))
    if tid is None:
        abort(404)
    return redirect(url_for("user.topic" if kind == "mavzu" else "user.lesson_topic", topic_id=tid))


@bp.get("/ekranlar")
def screens():
    from ..roles import REQUIRED
    _dev_tools_only()
    return render_template("meta/screens.html", groups=SCREENS, required=REQUIRED)
