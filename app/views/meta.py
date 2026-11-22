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
        ("user.plan", "O‘quv reja — diagnostikasiz (umumiy ish reja)", {"diagnostika": "yoq"}),
        ("user.plan", "O‘quv reja — oylik test vaqti kelgan", {"oylik": 1}),
        ("user.topic", "Mavzu tafsiloti", {"topic_id": 1}),
    ]),
    ("Dars va AI tutor", [
        ("user.lesson", "Dars sahifasi", {}),
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
        ("test.question", "Savol — xatolar ustida ishlash (15 ta)", {"manba": "xatolar", "soni": 15}),
        ("test.question", "Savol — haftalik test (bosqichli)", {"turi": "haftalik"}),
        ("test.stage", "Bosqichlar orasida (oraliq sinov)", {"turi": "oraliq"}),
        ("test.result", "Natija — o‘tdi", {}),
        ("test.result", "Natija — qaytarildi", {"holat": "qaytarildi"}),
        ("user.control", "Nazorat oldidan", {}),
        ("user.optional", "Ixtiyoriy test", {}),
        ("test.exam", "Attestatsiya testi (savollar navigatori bilan)", {"namuna": 1}),
        ("test.exam", "Attestatsiya testi — jadvalli savol", {"savol": 5, "namuna": 1}),
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
        ("expert.queue", "Tekshiruv navbati — 2-sahifa", {"sahifa": 2}),
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


@bp.get("/_rol/<role>")
def as_role(role):
    """Faqat ishlab chiqish uchun: rolni almashtirib, sahifani ochish (/ekranlar havolalari shu orqali o'tadi)."""
    from flask import abort, redirect, request, session, url_for

    from ..roles import HOME, ROLES
    if role not in ROLES:
        abort(404)
    session["role"] = role
    nxt = request.args.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for(HOME[role]))


@bp.get("/ekranlar")
def screens():
    from ..roles import REQUIRED
    return render_template("meta/screens.html", groups=SCREENS, required=REQUIRED)
