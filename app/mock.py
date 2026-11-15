"""Namunaviy (demo) ma'lumotlar.

Backend tayyor bo'lgunga qadar shablonlar shu ma'lumotlar bilan ko'rsatiladi.
Keyin har bir funksiya ma'lumotlar bazasidan o'qiydigan servisga almashtiriladi.
"""

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
        ("user.home", "Bosh sahifa", "home", True),
        ("user.plan", "O‘quv reja", "route", True),
        ("user.knowledge", "Bilim darajasi", "layers", True),
        ("user.results", "Natijalarim", "chart", True),
    ],
    # Chap menyuning qolgan guruhlari
    "user_groups": [
        ("O‘qish", [
            ("user.tutor", "AI tutor", "sparkle"),
            ("user.notes", "Shaxsiy konspekt", "note"),
            ("user.discussions", "Muhokamalar", "message"),
        ]),
        ("Test va natijalar", [
            ("user.tests", "Testlarim", "clipboard"),
            ("test.exam", "Attestatsiya sinovi", "clock"),
            ("user.errors", "Xatolar analitikasi", "target"),
            ("user.objections", "E’tirozlarim", "flag"),
            ("user.certificates", "Sertifikatlarim", "award"),
        ]),
    ],
    "expert": [
        ("expert.queue", "Tekshiruv navbati", "inbox", 12),
        ("expert.editor", "Savol yaratish", "edit", None),
        ("expert.objections", "E’tirozlar", "flag", 3),
    ],
    "admin": [
        ("admin.dashboard", "Boshqaruv paneli", "grid", None),
        ("admin.topics", "Mavzular va darslar", "book", None),
        ("admin.questions", "Savollar banki", "database", None),
        ("admin.users", "Foydalanuvchilar", "users", None),
        ("admin.settings", "Sozlamalar", "settings", None),
    ],
}

# Mavzu holatlari (TZ 7-bo'lim)
STATUS = {
    "none":   ("O‘zlashtirilmagan", "gray"),
    "learn":  ("O‘rganilmoqda", "yellow"),
    "relearn": ("Qayta o‘zlashtirish kerak", "red"),
    "done":   ("O‘zlashtirilgan", "blue"),
    "solid":  ("Mustahkam", "green"),
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
    {"name": "Python: shart operatorlari", "state": "current", "note": "3/4 kichik mavzu · 60% o‘qilgan"},
    {"name": "Python: sikllar (for, while)", "state": "confirm", "note": "Tasdiqlash mumkin — darsni o‘tkazib, testni topshiring"},
    {"name": "Nazorat: oxirgi 3 ta mavzu", "state": "control", "note": "Majburiy oraliq nazorat"},
    {"name": "Funksiyalar va modullar", "state": "locked", "note": "Avvalgi mavzulardan keyin ochiladi"},
    {"name": "Massivlar va ro‘yxatlar", "state": "locked", "note": "Avvalgi mavzulardan keyin ochiladi"},
]

RESULTS = [
    {"id": 1, "name": "Funksiyalar va modullar", "kind": "Mavzu testi", "when": "Bugun, 14:20", "pct": 92, "decision": "pass"},
    {"id": 2, "name": "Oraliq nazorat: 3 ta mavzu", "kind": "Nazorat", "when": "Kecha, 18:45", "pct": 78, "decision": "warn"},
    {"id": 3, "name": "Sanoq sistemalari va mantiq", "kind": "Mavzu testi", "when": "12-noyabr", "pct": 62, "decision": "fail"},
    {"id": 4, "name": "Boshlang‘ich bilim darajasi", "kind": "Diagnostika", "when": "8-noyabr", "pct": 70, "decision": "pass"},
    {"id": 5, "name": "Attestatsiya sinovi", "kind": "Sinov", "when": "5-noyabr", "pct": 84, "decision": "pass"},
    {"id": 6, "name": "Sikllar va takrorlanish", "kind": "Mavzu testi", "when": "1-noyabr", "pct": 65, "decision": "fail"},
]
DECISION = {"pass": ("O‘tdi", "green"), "warn": ("Tavsiya bilan", "yellow"), "fail": ("Qaytarildi", "red")}
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
OBJ_STATE = {"review": ("Ko‘rib chiqilmoqda", "yellow"), "accepted": ("Qabul qilindi", "green"), "rejected": ("Rad etildi", "gray")}

CERT_TOPICS = [
    ("Axborot nazariyasi va sanoq sistemalari", 92), ("Mantiq asoslari va rostlik jadvallari", 88),
    ("Dasturlash asoslari va algoritmlar", 85), ("Ma’lumotlar tuzilmasi", 80), ("Funksiyalar va rekursiya", 78),
    ("Kompyuter tarmoqlari va xavfsizlik", 90), ("Ma’lumotlar bazasi asoslari", 86), ("Ofis dasturlari", 94),
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
Q_STATE = {"approved": ("Tasdiqlangan", "green"), "review": ("Tekshiruvda", "yellow"),
           "draft": ("Qoralama", "gray"), "archived": ("Arxivlangan", "gray"), "paused": ("To‘xtatilgan", "red")}
TOPIC_TREE = [
    ("Dasturlash asoslari", [("Python asoslari", 8), ("Python: shart operatorlari", 14), ("Sikllar", 14), ("Funksiyalar va modullar", 19)]),
    ("Algoritmlar va ma’lumotlar tuzilmasi", [("Saralash algoritmlari", 22), ("Qidiruv algoritmlari", 9)]),
    ("Kompyuter tarmoqlari", [("IP-manzillash", 16), ("Protokollar", 11)]),
    ("Ma’lumotlar bazasi va SQL", [("Relyatsion model", 6)]),
]
