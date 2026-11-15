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
        ("auth.privacy", "Maxfiylik siyosati", {}),
    ]),
    ("Asosiy", [
        ("user.home", "Bosh sahifa", {}),
        ("user.home", "Bosh sahifa — yangi foydalanuvchi", {"yangi": 1, "qadam": 1}),
        ("user.diagnostic", "Diagnostika taklifi", {}),
        ("user.offline", "Oflayn holat", {}),
    ]),
    ("Bilim va reja", [
        ("user.knowledge", "Bilim darajasi — ro‘yxat", {}),
        ("user.knowledge", "Bilim darajasi — xarita", {"view": "xarita"}),
        ("user.topic", "Mavzu tafsiloti", {"topic_id": 1}),
        ("user.plan", "O‘quv reja", {}),
    ]),
    ("Dars va AI tutor", [
        ("user.lesson", "Dars sahifasi", {}),
        ("user.lesson", "Dars — qayta o‘qitish", {"holat": "qayta"}),
        ("user.lesson", "Dars — audio pleyer", {"audio": 1}),
        ("user.tutor", "AI tutor", {}),
        ("user.notes", "Shaxsiy konspekt", {}),
    ]),
    ("Testlar", [
        ("user.tests", "Testlarim", {}),
        ("test.question", "Savol — yopiq test", {"tur": "yopiq"}),
        ("test.question", "Savol — bir nechta javob", {"tur": "kop"}),
        ("test.question", "Savol — moslashtirish", {"tur": "moslash"}),
        ("test.question", "Savol — ochiq javob", {"tur": "ochiq"}),
        ("test.question", "Savol — jadvalli", {"tur": "jadval"}),
        ("test.question", "Savol — rasmli", {"tur": "rasm"}),
        ("test.question", "Savol — oflayn rejimda", {"tur": "yopiq", "oflayn": 1}),
        ("test.stage", "Bosqichlar orasida", {}),
        ("test.result", "Natija — o‘tdi", {}),
        ("test.result", "Natija — qaytarildi", {"holat": "qaytarildi"}),
        ("user.control", "Nazorat oldidan", {}),
        ("user.optional", "Ixtiyoriy test", {}),
        ("test.exam", "Attestatsiya sinovi (savollar navigatori bilan)", {}),
        ("test.exam", "Attestatsiya sinovi — jadvalli savol", {"savol": 5}),
        ("test.exam", "Attestatsiya sinovi — yakunlashni tasdiqlash", {"yakun": 1}),
    ]),
    ("Natijalar va tahlil", [
        ("user.results", "Natijalarim", {}),
        ("user.results", "Natijalarim — bo‘sh holat", {"bosh": 1}),
        ("user.errors", "Xatolar analitikasi", {}),
    ]),
    ("Muhokama, e’tiroz, sertifikat", [
        ("user.discussions", "Muhokamalar", {}),
        ("user.discussion", "Muhokama (savol bo‘yicha)", {}),
        ("user.objections", "E’tirozlarim", {}),
        ("user.certificates", "Sertifikatlarim", {}),
        ("user.certificate_print", "Sertifikat — bosma ko‘rinish", {}),
        ("user.profile", "Profil", {}),
    ]),
    ("Ekspert paneli", [
        ("expert.queue", "Tekshiruv navbati", {}),
        ("expert.editor", "Savol muharriri", {}),
        ("expert.objections", "E’tirozlar", {}),
    ]),
    ("Admin paneli", [
        ("admin.dashboard", "Boshqaruv paneli", {}),
        ("admin.users", "Foydalanuvchilar", {}),
        ("admin.topics", "Mavzular va dars muharriri", {}),
        ("admin.questions", "Savollar banki", {}),
        ("admin.settings", "Sozlamalar", {}),
    ]),
]


@bp.get("/sw.js")
def service_worker():
    # Service Worker butun saytni boshqarishi uchun ildiz manzildan beriladi
    from flask import current_app, send_from_directory
    resp = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.get("/ekranlar")
def screens():
    return render_template("meta/screens.html", groups=SCREENS)
