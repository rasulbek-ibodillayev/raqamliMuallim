"""Namunaviy (demo) ma'lumotlar.

Backend tayyor bo'lgunga qadar shablonlar shu ma'lumotlar bilan ko'rsatiladi.
Keyin har bir funksiya ma'lumotlar bazasidan o'qiydigan servisga almashtiriladi.
"""
from flask_babel import lazy_gettext as _l

ME = {
    "first": "Dilnoza",
    "last": "Karimova",
    "initials": "DK",
    "role": "Informatika fani o‘qituvchisi",
    "phone": "+998 90 *** ** 67",
    "days_left": 38,
    "exam_date": "23-dekabr",
}

# Foydalanuvchi paneli navigatsiyasi: (endpoint, nom, ikonka, mobil pastki panelda)
NAV = {
    "user": [
        ("user.home", _l("Bosh sahifa"), "home", True),
        ("user.plan", _l("O‘quv reja"), "route", True),
        ("user.knowledge", _l("Bilim darajasi"), "layers", True),
        ("user.results", _l("Natijalarim"), "chart", True),
    ],
    # Chap menyuning qolgan guruhlari
    "user_groups": [
        (_l("O‘qish"), [
            ("user.tutor", _l("AI tutor"), "sparkle"),
            ("user.notes", _l("Eslatmalar"), "note"),
            ("user.discussions", _l("Muhokamalar"), "message"),
        ]),
        (_l("Test va natijalar"), [
            ("user.tests", _l("Testlarim"), "clipboard"),
            ("test.exam", _l("Attestatsiya sinovi"), "clock"),
            ("user.errors", _l("Xatolar analitikasi"), "target"),
            ("user.objections", _l("E’tirozlarim"), "flag"),
            ("user.certificates", _l("Sertifikatlarim"), "award"),
        ]),
    ],
    # Ekspert: kontent (mavzular, darslar, savollar) va sifat nazorati
    "expert": [
        ("expert.queue", _l("Tekshiruv navbati"), "inbox", 12),
        ("expert.questions", _l("Savollar banki"), "database", None),
        ("expert.editor", _l("Savol yaratish"), "edit", None),
        ("expert.topics", _l("Mavzular va darslar"), "book", None),
        ("expert.objections", _l("E’tirozlar"), "flag", 3),
    ],
    # Admin: foydalanuvchilar, ekspertlar, statistika va tizim sozlamalari (kontent bilan ishlamaydi)
    "admin": [
        ("admin.stats", _l("Statistika"), "chart", None),
        ("admin.users", _l("Foydalanuvchilar"), "users", None),
        ("admin.experts", _l("Ekspertlar"), "shield", None),
        ("admin.settings", _l("Sozlamalar"), "settings", None),
    ],
}

# Mavzu holatlari (TZ 7-bo'lim)
STATUS = {
    "none":   (_l("O‘zlashtirilmagan"), "gray"),
    "learn":  (_l("O‘rganilmoqda"), "yellow"),
    "relearn": (_l("Qayta o‘zlashtirish kerak"), "red"),
    "done":   (_l("O‘zlashtirilgan"), "blue"),
    "solid":  (_l("Mustahkam"), "green"),
}

SECTIONS = [
    {"name": "Dasturlash", "pct": 72, "topics": [
        {"id": 1, "name": "Python: shart operatorlari", "pct": 92, "status": "done"},
        {"id": 2, "name": "Sikllar (for, while)", "pct": 68, "status": "learn"},
        {"id": 3, "name": "Funksiyalar", "pct": 45, "status": "relearn", "flag": "Takrorlash tavsiya etiladi"},
        {"id": 4, "name": "Massivlar va ro‘yxatlar", "pct": 85, "status": "done"},
        {"id": 5, "name": "Obyektga yo‘naltirilgan dasturlash", "pct": None, "status": "none"},
    ]},
    {"name": "Axborot va kodlash", "pct": 74, "topics": [
        {"id": 6, "name": "Sanoq sistemalari", "pct": 96, "status": "solid"},
        {"id": 7, "name": "Matnli axborotni kodlash", "pct": 60, "status": "learn"},
        {"id": 8, "name": "Axborot hajmi", "pct": None, "status": "none"},
    ]},
    {"name": "Tarmoq texnologiyalari", "pct": 80, "topics": [
        {"id": 9, "name": "IP-manzillash va maskalar", "pct": 95, "status": "solid"},
        {"id": 10, "name": "Tarmoq protokollari", "pct": 64, "status": "learn"},
    ]},
    {"name": "Ofis dasturlari", "pct": 95, "topics": [
        {"id": 11, "name": "Elektron jadvallar: formulalar", "pct": 98, "status": "solid"},
    ]},
]

DISTRIBUTION = [("none", 15), ("learn", 25), ("relearn", 10), ("done", 30), ("solid", 20)]

TOPIC = {
    "name": "Python: shart operatorlari",
    "section": "Dasturlash",
    "status": "done",
    "last": "85% · 12-noyabr",
    "subtopics": [("if operatori", 100), ("if / else", 100), ("elif zanjiri", 40), ("Ichma-ich shartlar", 100)],
}

PLAN = [
    {"name": "Kompyuter arxitekturasi va mantiqiy asoslar", "state": "done", "note": "100%"},
    {"name": "Algoritmlash asoslari va blok-sxemalar", "state": "done", "note": "95%"},
    {"name": "Python: shart operatorlari", "state": "current", "note": "3/4 kichik mavzu · 60% o‘qilgan", "min": 12},
    {"name": "Python: sikllar (for, while)", "state": "confirm", "note": "Tasdiqlash mumkin — darsni o‘tkazib, testni topshiring", "min": 15},
    {"name": "Nazorat: oxirgi 3 ta mavzu", "state": "control", "note": "Majburiy oraliq nazorat", "min": 35},
    {"name": "Funksiyalar va modullar", "state": "locked", "note": "Avvalgi mavzulardan keyin ochiladi", "min": 45},
    {"name": "Massivlar va ro‘yxatlar", "state": "locked", "note": "Avvalgi mavzulardan keyin ochiladi", "min": 40},
]

RESULTS = [
    {"id": 1, "name": "Funksiyalar va modullar", "kind": "Mavzu testi", "when": "Bugun, 14:20", "pct": 92, "decision": "pass"},
    {"id": 2, "name": "Oraliq nazorat: 3 ta mavzu", "kind": "Nazorat", "when": "Kecha, 18:45", "pct": 78, "decision": "warn"},
    {"id": 3, "name": "Sanoq sistemalari va mantiq", "kind": "Mavzu testi", "when": "12-noyabr", "pct": 62, "decision": "fail"},
    {"id": 4, "name": "Boshlang‘ich bilim darajasi", "kind": "Diagnostika", "when": "8-noyabr", "pct": 70, "decision": "pass"},
    {"id": 5, "name": "Attestatsiya sinovi", "kind": "Sinov", "when": "5-noyabr", "pct": 84, "decision": "pass"},
    {"id": 6, "name": "Sikllar va takrorlanish", "kind": "Mavzu testi", "when": "1-noyabr", "pct": 65, "decision": "fail"},
]
DECISION = {"pass": (_l("O‘tdi"), "green"), "warn": (_l("Tavsiya bilan"), "yellow"), "fail": (_l("Qaytarildi"), "red")}
TREND = [62, 70, 65, 78, 84, 92]

REVIEW = [
    {"n": 1, "ok": True, "q": "101101 ikkilik sonini o‘nlik sanoq sistemasiga o‘tkazing.",
     "mine": "45", "topic": "Sanoq sistemalari"},
    {"n": 2, "ok": False, "q": "Quyidagi kod natijasini aniqlang:",
     "code": "x = 5\nif x > 3:\n    print(x * 2)\nelse:\n    print(x + 10)",
     "mine": "15", "right": "10",
     "why": "x > 3 sharti rost (5 > 3), shuning uchun 5 * 2 = 10 chop etiladi.", "topic": "Shart operatorlari"},
    {"n": 3, "ok": True, "q": "Tarmoq texnologiyalarida DNS vazifasi nima?",
     "mine": "Domen nomlarini IP-manzilga o‘girish", "topic": "Tarmoq texnologiyalari"},
]

ERRORS_WEAK = [
    ("Rekursiv funksiyalar va stek", "Funksiyalar", 7),
    ("Mantiqiy amallar va rostlik jadvallari", "Mantiq asoslari", 5),
    ("Ko‘p o‘lchovli ro‘yxatlar", "Ma’lumotlar tuzilmasi", 4),
    ("Murakkab shartli o‘tishlar", "Algoritmlash", 3),
    ("Sanoq sistemalarida arifmetika", "Axborot nazariyasi", 2),
]
ERRORS_LIST = [
    ("(A ∨ B) ∧ ¬(A ∧ B) ifodasining rostlik jadvali…", "Mantiq asoslari", "2 marta xato", True),
    ("Rekursiyaning bazaviy sharti to‘g‘ri ko‘rsatilgan qator…", "Funksiyalar", "Kecha", False),
    ("Ikkilik sanoq sistemasida 101101 + 11011 yig‘indisi…", "Axborot nazariyasi", "12-noyabr", False),
    ("Ikki o‘lchovli massiv diagonali elementlarini topish…", "Ma’lumotlar tuzilmasi", "3 marta xato", True),
]

NOTES = [
    ("Shart operatorlari", "elif sharti faqat oldingi if sharti yolg‘on (False) bo‘lganda tekshiriladi. Barcha shartlar qanoatlanmasa else bloki ishlaydi.", None, "12-noyabr"),
    ("Shart operatorlari", "if/else qisqa sintaksisi:", 'holat = "Iliq" if harorat > 20 else "Salqin"', "10-noyabr"),
    ("Sanoq sistemalari", "O‘nlikdan ikkilikka o‘tishda son 2 ga bo‘linadi va qoldiqlar teskari tartibda yoziladi.", None, "5-noyabr"),
    ("Sanoq sistemalari", "16 lik sanoq sistemasida A=10, B=11, C=12, D=13, E=14, F=15.", None, "3-noyabr"),
]

OBJECTIONS = [
    {"when": "Bugun, 11:20", "q": "(A ∨ B) ∧ ¬(A ∧ B) ifodasi qachon 1 ga teng bo‘ladi?", "state": "review"},
    {"when": "12-noyabr", "q": "Rekursiyaning bazaviy sharti to‘g‘ri ko‘rsatilgan javobni aniqlang",
     "state": "accepted", "verdict": "Savol matnidagi 2-shartda noaniqlik borligi tasdiqlandi. Siz ko‘rsatgan javob to‘g‘ri deb hisoblandi.",
     "recalc": ("78%", "82%")},
    {"when": "5-noyabr", "q": "Ikkilik sanoq sistemasida 101101 + 11011 yig‘indisi nechaga teng?", "state": "rejected",
     "verdict": "Savol va javob to‘g‘ri. 101101₂ + 11011₂ = 1001000₂ (72)."},
]
OBJ_STATE = {"review": (_l("Ko‘rib chiqilmoqda"), "yellow"), "accepted": (_l("Qabul qilindi"), "green"), "rejected": (_l("Rad etildi"), "gray")}

CERT_TOPICS = [
    ("Axborot nazariyasi va sanoq sistemalari", 92), ("Mantiq asoslari va rostlik jadvallari", 88),
    ("Dasturlash asoslari va algoritmlar", 85), ("Ma’lumotlar tuzilmasi", 80), ("Funksiyalar va rekursiya", 78),
    ("Kompyuter tarmoqlari va xavfsizlik", 90), ("Ma’lumotlar bazasi asoslari", 86), ("Ofis dasturlari", 94),
]

# Yagona tayyorlik ko'rsatkichi va prognoz.
# Backendda: tayyorlik = mavzular og'irligi bo'yicha o'zlashtirish; prognoz = so'nggi 14 kundagi sur'atdan.
READINESS = {
    "pct": 68,
    "forecast": "19-dekabr",
    "exam": "23-dekabr",
    "days_left": 38,
    "margin_days": 4,          # attestatsiyadan necha kun oldin tayyor bo'ladi (manfiy — kechikadi)
    "pace": "Kuniga ≈ 1 mavzu",
    "state": "ok",             # ok | risk | late
}
READINESS_STATE = {
    "ok":   (_l("Reja bo‘yicha"), "green", _l("Hozirgi sur’atda attestatsiyadan {m} kun oldin tayyor bo‘lasiz.")),
    "risk": (_l("Biroz ortda"), "yellow", _l("Sur’at sekinlashdi: attestatsiyaga zo‘rg‘a ulgurasiz. Kuniga 15 daqiqa qo‘shing.")),
    "late": (_l("Ortda qolmoqda"), "red", _l("Hozirgi sur’atda attestatsiyaga ulgurmaysiz. Rejani tezlashtiring.")),
}

# «Bugun» rejasi: har vazifa uchun taxminiy vaqt (daqiqa)
TODAY = [
    {"title": "Darsni davom ettirish", "sub": "Shart operatorlari · elif zanjiri", "min": 12, "done": False, "endpoint": "user.lesson", "icon": "book"},
    {"title": "Mavzu testi", "sub": "1-bosqich · 10 savol", "min": 8, "done": False, "endpoint": "test.question", "icon": "clipboard"},
    {"title": "Kunlik 5 ta savol", "sub": "Takrorlash", "min": 3, "done": True, "endpoint": "test.question", "icon": "zap"},
]

# Yangi foydalanuvchi uchun 3 qadam (TZ 1.3: diagnostikani yakunlaganlar ≥ 60%)
ONBOARDING = [
    {"title": "Diagnostikadan o‘ting", "sub": "≈ 40 daqiqa · bilgan mavzularingizni aniqlaymiz", "endpoint": "user.diagnostic"},
    {"title": "Birinchi darsni o‘qing", "sub": "≈ 12 daqiqa · rejangizdagi birinchi mavzu", "endpoint": "user.lesson"},
    {"title": "Birinchi mavzu testini topshiring", "sub": "≈ 8 daqiqa · 3 bosqich", "endpoint": "test.question"},
]

NOTIFICATIONS = [
    {"icon": "flag", "title": "Oraliq nazorat sizni kutmoqda", "text": "Oxirgi 3 ta mavzu bo‘yicha majburiy nazorat", "when": "10 daqiqa oldin", "endpoint": "user.control", "unread": True},
    {"icon": "shield", "title": "E’tirozingizga javob keldi", "text": "Natijangiz 78% → 82% ga qayta hisoblandi", "when": "2 soat oldin", "endpoint": "user.objections", "unread": True},
    {"icon": "zap", "title": "Kunlik 5 ta savol tayyor", "text": "3 daqiqa · takrorlash vaqti kelgan mavzular", "when": "Bugun, 08:00", "endpoint": "test.question", "unread": False},
    {"icon": "calendar", "title": "Attestatsiya sanasi belgilandi", "text": "23-dekabr, 2026 · administrator tomonidan", "when": "Kecha", "endpoint": "user.profile", "unread": False},
]

DISCUSSIONS = [
    {"n": 14, "topic": "Sanoq sistemalari", "q": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazganda qanday natija hosil bo‘ladi?", "count": 4, "last": "Bugun, 10:45", "expert": True, "mine": True},
    {"n": 18, "topic": "Mantiq asoslari", "q": "(A ∨ B) ∧ ¬(A ∧ B) ifodasi qachon 1 ga teng bo‘ladi?", "count": 7, "last": "Kecha, 19:02", "expert": False, "mine": True},
    {"n": 7, "topic": "Shart operatorlari", "q": "Quyidagi kod natijasini aniqlang: x = 5; if x > 3: print(x * 2)", "count": 2, "last": "12-noyabr", "expert": True, "mine": False},
    {"n": 22, "topic": "Tarmoq texnologiyalari", "q": "DNS serverning asosiy vazifasi nima?", "count": 3, "last": "10-noyabr", "expert": False, "mine": False},
]

DISCUSSION = [
    ("Dilshod Karimov", "Bugun, 10:45", "Savol shartidagi so‘z biroz chalg‘ituvchi edi, lekin hisob-kitob qoidasi to‘g‘ri."),
    ("Nodira Aliyeva", "Kecha, 16:20", "Mening variantimda javoblar tartibi boshqacha edi, 45 javobi B variantda edi."),
    ("Javohir Toshmatov", "14-noyabr", "Ekspert tushuntirishi aniq bo‘ldi, rahmat."),
]

OPTIONAL_TOPICS = [
    ("Python asoslari: sintaksis va o‘zgaruvchilar", 45, "done", True),
    ("Shart operatorlari: if, elif, else", 32, "done", True),
    ("Takrorlanish operatorlari: for va while", 38, "done", True),
    ("Funksiyalar va modullar", 28, "done", True),
    ("Ikkilik va o‘nlik sanoq sistemalari", 20, "solid", True),
    ("Ma’lumotlar bazasi: relyatsion model", 15, "relearn", False),
]

# --- Ekspert ---
QUEUE = [
    ("101101 ikkilik sonini o‘nlik sanoq sistemasiga…", "Sanoq sistemalari", "O‘rta", "Yopiq test", "AI generator", "ai"),
    ("De Morgan qonunlariga ko‘ra ¬(A ∧ B) ifodasi…", "Mantiq asoslari", "Oson", "Yopiq test", "Alisher Rustamov", "expert"),
    ("Ikkilik qidiruv algoritmining vaqt murakkabligi…", "Algoritmlar", "Qiyin", "Bir nechta javob", "AI generator", "ai"),
    ("Mantiqiy darvozalarni rostlik jadvali bilan moslang", "Mantiq asoslari", "O‘rta", "Moslashtirish", "Zuhra Qodirova", "expert"),
    ("Rekursiv funksiyada bazaviy shart bo‘lmasa…", "Funksiyalar", "O‘rta", "Yopiq test", "AI generator", "ai"),
]
EXPERT_OBJ = [
    {"id": "#Q-84920", "q": "101101 ikkilik sonini o‘nlik sanoq sistemasiga o‘tkazganda qanday natija hosil bo‘ladi?", "topic": "Sanoq sistemalari", "lvl": "O‘rta", "n": 5, "urgent": True, "ago": "15 daqiqa oldin"},
    {"id": "#Q-84812", "q": "De Morgan qonunlariga ko‘ra ¬(A ∧ B) ifodasining ekvivalenti qaysi?", "topic": "Mantiq asoslari", "lvl": "Oson", "n": 3, "urgent": False, "ago": "2 soat oldin"},
    {"id": "#Q-84590", "q": "Ikkilik qidiruv algoritmining vaqt murakkabligi qanday?", "topic": "Algoritmlar", "lvl": "Qiyin", "n": 2, "urgent": False, "ago": "kecha"},
]

# --- Admin ---
KPI = [
    ("Foydalanuvchilar", "1 248", "+34 ta bu hafta"),
    ("Bugun faol", "312", "25% foydalanuvchilardan"),
    ("Diagnostikani tugatgan", "61%", "Maqsad ≥ 60%"),
    ("AI xarajati (oy)", "$210", "$500 limitning 42%"),
]
DAU = [240, 268, 255, 290, 301, 276, 312]
HARD_TOPICS = [("Ikkilik va o‘nlik sanoq sistemalari", 68), ("De Morgan qonunlari", 59),
               ("Ikkilik qidiruv algoritmi", 54), ("Funksiyalar va rekursiya", 47), ("Graf va daraxtlar", 41)]
USERS = [
    # (ism, initsial, aloqa, viloyat, o'tilgan mavzu, oxirgi faollik, faol, attestatsiya sanasi YYYY-MM-DD yoki None)
    # Ro'yxatdagi tartib raqami (1 dan) — namunada foydalanuvchi ID'si: /admin/foydalanuvchilar/<id>
    ("Dilnoza Karimova", "DK", "+998 90 123 45 67", "Toshkent sh.", 14, "Bugun 11:42", True, "2026-12-23"),
    ("Javlon Toshmatov", "JT", "+998 93 456 78 90", "Samarqand vil.", 38, "Kecha 18:20", True, "2026-12-05"),
    ("Nigora Mirzayeva", "NM", "+998 97 712 34 56", "Farg‘ona vil.", 21, "3 kun oldin", True, None),
    ("Sardor Aliyev", "SA", "sardor@maktab.uz", "Buxoro vil.", 4, "12 kun oldin", False, None),
    ("Malika Yusupova", "MY", "+998 91 222 33 44", "Andijon vil.", 30, "Bugun 09:10", True, "2027-01-14"),
]
QUESTIONS = [
    ("Rekursiv funksiyaning maksimal chaqiruv chuqurligi qanday oshiriladi?", "Funksiyalar", "Oson", "Yopiq", "approved", 42, True),
    ("1101101₂ sonini o‘n oltilik sanoq sistemasiga o‘tkazing.", "Sanoq sistemalari", "O‘rta", "Ochiq", "approved", 71, False),
    ("HTTP, DNS, FTP protokollarini vazifasi bilan moslang.", "Tarmoqlar", "Oson", "Moslashtirish", "review", None, False),
    ("Qaysilari kiritish qurilmalari?", "Kompyuter qurilmalari", "Oson", "Ko‘p javobli", "draft", None, False),
    ("for sikli necha marta bajariladi?", "Sikllar", "Qiyin", "Yopiq", "archived", 88, True),
]
Q_STATE = {"approved": (_l("Tasdiqlangan"), "green"), "review": (_l("Tekshiruvda"), "yellow"),
           "draft": (_l("Qoralama"), "gray"), "archived": (_l("Arxivlangan"), "gray"), "paused": (_l("To‘xtatilgan"), "red")}
TOPIC_TREE = [
    ("Dasturlash asoslari", [("Python asoslari", 8), ("Python: shart operatorlari", 14), ("Sikllar", 14), ("Funksiyalar va modullar", 19)]),
    ("Algoritmlar va ma’lumotlar tuzilmasi", [("Saralash algoritmlari", 22), ("Qidiruv algoritmlari", 9)]),
    ("Kompyuter tarmoqlari", [("IP-manzillash", 16), ("Protokollar", 11)]),
    ("Ma’lumotlar bazasi va SQL", [("Relyatsion model", 6)]),
]


# --- Admin: foydalanuvchi tafsiloti (namunada hamma uchun bir xil tarix, ism/aloqa USERS'dan) ---
USER_DETAIL = {
    "registered": "8-noyabr, 2026", "auth": ["Telegram", "Google"], "email": "dilnoza.k@maktab.uz",
    "school": "Toshkent sh., 110-maktab", "experience": "12 yil", "category": "Birinchi toifa",
    "readiness": 68, "study_hours": 21.5, "streak": 6, "tests": 18, "avg": 79, "ai_requests": 64,
    "devices": [("Android · Chrome (PWA o‘rnatilgan)", "Bugun 11:42"), ("Windows · Edge", "3 kun oldin")],
    "activity": [
        ("Bugun 11:42", "Mavzu testi topshirildi", "Funksiyalar va modullar · 92% · o‘tdi"),
        ("Bugun 11:05", "Dars o‘qildi", "Funksiyalar va modullar · 100%"),
        ("Kecha 18:45", "Oraliq nazorat", "3 ta mavzu · 78% · tavsiya bilan"),
        ("Kecha 18:02", "E’tiroz yuborildi", "#Q-84920 · ko‘rib chiqilmoqda"),
        ("12-noyabr", "Mavzu testi", "Sanoq sistemalari va mantiq · 62% · qaytarildi"),
        ("8-noyabr", "Diagnostika yakunlandi", "Boshlang‘ich daraja 70%"),
        ("8-noyabr", "Ro‘yxatdan o‘tdi", "Telegram orqali"),
    ],
}

# --- Admin: ekspertlar ---
EXPERTS = [
    # id, ism, initsial, aloqa, yo'nalishlar, yaratgan, tekshirgan, e'tiroz hal qilgan, o'rtacha javob vaqti, faol, oxirgi faollik, huquqlar
    {"id": 1, "name": "Zuhra Qodirova", "ini": "ZQ", "contact": "zuhra.q@raqamlimuallim.uz", "areas": ["Mantiq asoslari", "Dasturlash"],
     "created": 142, "reviewed": 388, "objections": 41, "resp": "3 soat", "active": True, "last": "Bugun 10:20",
     "perms": ["questions", "review", "topics", "objections"]},
    {"id": 2, "name": "Alisher Rustamov", "ini": "AR", "contact": "+998 90 777 12 34", "areas": ["Algoritmlar", "Ma’lumotlar bazasi"],
     "created": 96, "reviewed": 210, "objections": 18, "resp": "7 soat", "active": True, "last": "Kecha 21:05",
     "perms": ["questions", "review", "objections"]},
    {"id": 3, "name": "Kamola Ergasheva", "ini": "KE", "contact": "kamola.e@raqamlimuallim.uz", "areas": ["Kompyuter tarmoqlari"],
     "created": 37, "reviewed": 64, "objections": 5, "resp": "26 soat", "active": True, "last": "4 kun oldin",
     "perms": ["questions", "review"]},
    {"id": 4, "name": "Bobur Nazarov", "ini": "BN", "contact": "+998 93 101 20 30", "areas": ["Ofis dasturlari"],
     "created": 12, "reviewed": 8, "objections": 0, "resp": "—", "active": False, "last": "2 oy oldin",
     "perms": ["questions"]},
]
EXPERT_PERMS = [("questions", _l("Savol yaratish va tahrirlash")), ("review", _l("Savollarni tekshirish va tasdiqlash")),
                ("topics", _l("Mavzular va darslarni tahrirlash")), ("objections", _l("E’tirozlarni ko‘rib chiqish"))]
CONTENT_AREAS = ["Dasturlash", "Algoritmlar", "Mantiq asoslari", "Axborot va kodlash", "Kompyuter tarmoqlari",
                 "Ma’lumotlar bazasi", "Ofis dasturlari"]

# --- Admin: statistika ---
STATS = {
    "kpi": [("Foydalanuvchilar", "1 248", "+34 bu hafta", "users"), ("Kunlik faol", "312", "25% · o‘tgan haftadan +8%", "zap"),
            ("O‘rtacha tayyorlik", "64%", "+3 p.p. bu oy", "target"), ("Sertifikatlar", "87", "+12 bu oy", "award"),
            ("Diagnostikani tugatgan", "61%", "Maqsad ≥ 60%", "check-circle"), ("AI xarajati", "$210", "$500 limitning 42%", "sparkle")],
    "signups": [18, 24, 31, 22, 40, 36, 34, 29, 45, 38, 41, 52],
    "funnel": [("Ro‘yxatdan o‘tgan", 1248), ("Diagnostikani tugatgan", 761), ("Birinchi darsni o‘qigan", 702),
               ("Birinchi mavzu testini topshirgan", 655), ("Yarim kursdan o‘tgan", 388), ("Sertifikat olgan", 87)],
    "regions": [("Toshkent shahri", 248), ("Samarqand viloyati", 156), ("Farg‘ona viloyati", 141), ("Andijon viloyati", 128),
                ("Toshkent viloyati", 117), ("Qashqadaryo viloyati", 102), ("Boshqa viloyatlar", 356)],
    "devices": [("Telefon", 71), ("Kompyuter", 24), ("Planshet", 5)],
    "pwa": 38,
    "content": [("Tasdiqlangan savollar", "2 140"), ("Tekshiruvda", "86"), ("Ochiq e’tirozlar", "3"), ("O‘rtacha tekshiruv vaqti", "9 soat")],
    "inactive": [("3–6 oy kirmagan", 42), ("O‘chirishga 2 haftadan kam qolgan", 7), ("Shu oy avtomatik o‘chirilgan", 11)],
}
