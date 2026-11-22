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
            ("user.tests", _l("Testlar"), "clipboard"),
            ("user.errors", _l("Xatolar analitikasi"), "target"),
            ("user.objections", _l("E’tirozlarim"), "flag"),
            ("user.certificates", _l("Sertifikatlarim"), "award"),
        ]),
    ],
    # Ekspert: kontent (mavzular, darslar, savollar) va sifat nazorati
    "expert": [
        ("expert.questions", _l("Savollar banki"), "database", 23),
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

# Foydalanuvchi hozir o'rganayotgan mavzu (yangi eslatmalar shu mavzuga saqlanadi)
CURRENT_TOPIC = "Shart operatorlari"

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

# --- Shaxsiy o'quv reja (TZ: o'quv reja foydalanuvchining dastlabki diagnostikasidan tuziladi) ---
# Umumiy ish rejadan diagnostikada ≥ 90% o'zlashtirilgan mavzular chiqarib yuboriladi.
# Diagnostika rad etilgan bo'lsa — umumiy ish reja to'liq ishlatiladi.
# O'zlashtirish chegaralari: < 70% — keyingi mavzu yopiq; 70–89% — qayta o'zlashtirish tavsiya etiladi;
# ≥ 90% — tavsiya yo'q, lekin mavzuni qayta o'zlashtirish mumkin.
# Rejaga mavzu testlari, oraliq sinov (har 3 mavzudan keyin) va yakuniy diagnostika reja tuzilganda qo'shiladi;
# kunlik 5 ta test, haftalik va oylik testlar — faqat vaqti kelganda.
PASS_MIN, SOLID_MIN = 70, 90
# Mavzu → darslar. Har bir dars: o'zlashtirish foizi va mavzu testidagi shu darsga oid savollar natijasi
# (dars, n — savollar soni, ok — to'g'ri javoblar). Mavzu testi: rid — «Natijalarim»dagi natija (tafsilotga havola).
def _L(name, pct, ok=None, n=None, mn=None):
    return {"name": name, "pct": pct, "ok": ok, "n": n, "min": mn}


LEARN_PLAN = [
    {"kind": "topic", "id": 1, "name": "Kompyuter arxitekturasi va mantiqiy asoslar", "state": "done", "pct": 96, "min": 40,
     "lessons": [_L("Kompyuter qurilmalari", 100, 9, 9), _L("Protsessor va xotira", 95, 8, 8), _L("Mantiqiy amallar", 92, 7, 8)],
     "test": {"pct": 96, "rid": 11, "when": "10-noyabr", "n": 25}},
    {"kind": "topic", "id": 2, "name": "Algoritmlash asoslari va blok-sxemalar", "state": "done", "pct": 84, "min": 35,
     "lessons": [_L("Algoritm tushunchasi", 95, 8, 8), _L("Blok-sxemalar", 78, 7, 9), _L("Chiziqli algoritmlar", 80, 6, 8)],
     "test": {"pct": 84, "rid": 12, "when": "13-noyabr", "n": 25, "tries": 2}},
    {"kind": "topic", "id": 3, "name": "Sanoq sistemalari", "state": "done", "pct": 92, "min": 30,
     "lessons": [_L("Ikkilik sanoq sistemasi", 96, 13, 13), _L("O‘n oltilik sanoq sistemasi", 88, 10, 12)],
     "test": {"pct": 92, "rid": 1, "when": "Bugun", "n": 25, "tries": 2}},
    {"kind": "test", "type": "interim", "name": "Oraliq sinov testi: 1–3 mavzular", "state": "done", "pct": 78, "min": 35, "rid": 2},
    {"kind": "topic", "id": 4, "name": "Python: shart operatorlari", "state": "current", "pct": None, "read": 60, "min": 12,
     "lessons": [_L("if operatori", 100, mn=4), _L("if / else", 100, mn=4), _L("elif zanjiri", 40, mn=6), _L("Ichma-ich shartlar", None, mn=6)],
     "test": None},
    {"kind": "test", "type": "daily", "name": "Kunlik 5 ta test", "state": "done", "pct": 80, "min": 3, "rid": 9,
     "note": "Ko‘p xato qilayotgan mavzulardan"},
    {"kind": "test", "type": "weekly", "name": "Haftalik test", "state": "due", "min": 20,
     "note": "Bugun yakshanba · o‘zlashtirilgan mavzulardan"},
    {"kind": "topic", "id": 5, "name": "Python: sikllar (for, while)", "state": "locked", "date": "24-noyabr", "min": 45,
     "lessons": [_L("for sikli", None), _L("while sikli", None), _L("break va continue", None)]},
    {"kind": "topic", "id": 6, "name": "Funksiyalar va modullar", "state": "locked", "date": "26-noyabr", "min": 45,
     "lessons": [_L("Funksiya e’lon qilish", None), _L("Parametrlar", None), _L("Rekursiya", None)]},
    {"kind": "topic", "id": 7, "name": "Massivlar va ro‘yxatlar", "state": "locked", "date": "28-noyabr", "min": 40,
     "lessons": [_L("Ro‘yxat amallari", None), _L("Ko‘p o‘lchovli ro‘yxatlar", None)]},
    {"kind": "test", "type": "interim", "name": "Oraliq sinov testi: 4–6 mavzular", "state": "locked", "date": "29-noyabr", "min": 35},
    {"kind": "topic", "id": 8, "name": "Ma’lumotlar bazasi: relyatsion model", "state": "locked", "date": "2-dekabr", "min": 40,
     "lessons": [_L("Jadval va kalitlar", None), _L("SQL so‘rovlari", None)]},
    {"kind": "topic", "id": 9, "name": "Kompyuter tarmoqlari va protokollar", "state": "locked", "date": "5-dekabr", "min": 40,
     "lessons": [_L("Tarmoq turlari", None), _L("Protokollar", None)]},
    {"kind": "test", "type": "final", "name": "Yakuniy diagnostika", "state": "locked", "date": "19-dekabr", "min": 90,
     "note": "Barcha mavzular o‘zlashtirilgach. Natijasi bo‘yicha sertifikat beriladi"},
]
# Oylik test (majburiy, har 30 kunda): vaqti kelganda rejaga qo'shiladi. Joriy mavzu tugallanmagan bo'lsa —
# mavzu tugagach olinadi; yakunlanmaguncha keyingi mavzular ochilmaydi. Namunada ?oylik=1.
MONTHLY_DUE = {"kind": "test", "type": "monthly", "name": "Oylik test: noyabr", "state": "started", "min": 45,
               "note": "Boshlangan · 12 / 30 savol saqlangan. Yakunlanmaguncha keyingi mavzu ochilmaydi"}

# Diagnostikada ≥ 90% chiqqani uchun rejadan chiqarilgan mavzular
PLAN_EXCLUDED = [("Ofis dasturlari: elektron jadvallar", 98), ("IP-manzillash va maskalar", 95), ("Axborot hajmi va o‘lchov birliklari", 92)]
PLAN_SUMMARY = {"done": 14, "total": 42, "avg": 88, "days_left": 38, "per_day": "≈ 1 mavzu", "exam": "23-dekabr",
                "next_control": "2 mavzu"}
TEST_TYPES = {
    "diagnostic": ("Diagnostika testi", "target"), "topic": ("Mavzu testi", "clipboard"), "daily": ("Kunlik 5 ta test", "zap"),
    "exam": ("Attestatsiya testi", "clock"), "interim": ("Oraliq sinov testi", "flag"), "weekly": ("Haftalik test", "calendar"),
    "optional": ("Ixtiyoriy test", "settings"), "monthly": ("Oylik test", "calendar"), "final": ("Yakuniy diagnostika", "award"),
    "errors": ("Xatolar ustida ishlash", "target"),
}

# «Natijalarim»: dastlabki diagnostikadan boshlab barcha turdagi yakunlangan testlar (type — TEST_TYPES kaliti).
# Qayta topshirilganda shu turdagi YANGI savollar beriladi va natija ro'yxatga yangi qator bo'lib qo'shiladi.
RESULTS = [
    {"id": 9, "type": "daily", "name": "Kunlik 5 ta test", "when": "Bugun, 08:10", "pct": 80, "decision": "warn", "n": 5, "min": 3},
    {"id": 1, "type": "topic", "name": "Sanoq sistemalari (2-urinish)", "when": "Bugun, 14:20", "pct": 92, "decision": "pass", "n": 25, "min": 20},
    {"id": 8, "type": "errors", "name": "Xatolar ustida ishlash", "when": "Kecha, 20:05", "pct": 70, "decision": "warn", "n": 10, "min": 8},
    {"id": 2, "type": "interim", "name": "Oraliq sinov testi: 1–3 mavzular", "when": "Kecha, 18:45", "pct": 78, "decision": "warn", "n": 30, "min": 35},
    {"id": 7, "type": "weekly", "name": "Haftalik test", "when": "16-noyabr", "pct": 86, "decision": "pass", "n": 20, "min": 20},
    {"id": 10, "type": "optional", "name": "Ixtiyoriy test: Sanoq sistemalari", "when": "14-noyabr", "pct": 90, "decision": "pass", "n": 10, "min": 10},
    {"id": 12, "type": "topic", "name": "Algoritmlash asoslari va blok-sxemalar (2-urinish)", "when": "13-noyabr", "pct": 84, "decision": "warn", "n": 25, "min": 20},
    {"id": 3, "type": "topic", "name": "Sanoq sistemalari", "when": "12-noyabr", "pct": 62, "decision": "fail", "n": 25, "min": 20},
    {"id": 11, "type": "topic", "name": "Kompyuter arxitekturasi va mantiqiy asoslar", "when": "10-noyabr", "pct": 96, "decision": "pass", "n": 25, "min": 20},
    {"id": 4, "type": "diagnostic", "name": "Dastlabki diagnostika", "when": "8-noyabr", "pct": 70, "decision": "pass", "n": 60, "min": 70},
    {"id": 5, "type": "exam", "name": "Attestatsiya testi", "when": "5-noyabr", "pct": 84, "decision": "pass", "n": 35, "min": 120},
    {"id": 6, "type": "topic", "name": "Algoritmlash asoslari va blok-sxemalar", "when": "11-noyabr", "pct": 65, "decision": "fail", "n": 25, "min": 20},
]
# Natija tafsiloti: har bir savol, foydalanuvchi javobi (mine) va to'g'ri javob (right) — variantlar indeksi
RESULT_QUESTIONS = [
    {"n": 1, "topic": "Sanoq sistemalari", "level": "Oson", "q": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
     "options": ["43", "45", "47", "53"], "mine": 1, "right": 1},
    {"n": 2, "topic": "Shart operatorlari", "level": "Oson", "q": "Quyidagi kod natijasini aniqlang:",
     "code": "x = 5\nif x > 3:\n    print(x * 2)\nelse:\n    print(x + 10)", "options": ["5", "10", "15", "Xato beradi"], "mine": 2, "right": 1,
     "why": "x > 3 sharti rost (5 > 3), shuning uchun 5 * 2 = 10 chop etiladi."},
    {"n": 3, "topic": "Tarmoq texnologiyalari", "level": "O‘rta", "q": "DNS serverning asosiy vazifasi qaysi?",
     "options": ["Fayllarni uzatish", "Domen nomini IP-manzilga o‘girish", "Elektron xat yuborish", "Sahifani shifrlash"], "mine": 1, "right": 1},
    {"n": 4, "topic": "Mantiq asoslari", "level": "O‘rta", "q": "(A ∨ B) ∧ ¬(A ∧ B) ifodasi qachon 1 ga teng bo‘ladi?",
     "options": ["Faqat A va B rost bo‘lganda", "A va B turli qiymatga ega bo‘lganda", "Ikkalasi yolg‘on bo‘lganda", "Har doim"], "mine": 0, "right": 1,
     "why": "Ifoda XOR (istisno qiluvchi YOKI) ga teng: faqat bittasi rost bo‘lganda 1."},
    {"n": 5, "topic": "Funksiyalar", "level": "Qiyin", "q": "Rekursiv funksiyada bazaviy shart bo‘lmasa nima bo‘ladi?",
     "options": ["Funksiya bir marta ishlaydi", "RecursionError (stek to‘lib qoladi)", "None qaytaradi", "Sintaksis xatosi"], "mine": 1, "right": 1},
    {"n": 6, "topic": "Axborot hajmi", "level": "Qiyin", "q": "256 xil belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
     "options": ["6", "7", "8", "16"], "mine": 3, "right": 2, "why": "2⁸ = 256, demak har bir belgi 8 bit."},
]

# «Testlar» bo'limi: yakunlanmagan (to'xtatilgan) testlar — istalgan turdagi
# Majburiy turlar (yakunlanmagan bo'lsa — keyingi mavzu va keyingi majburiy test yopiq), qolganlari ixtiyoriy
MANDATORY_TYPES = {"topic", "daily", "interim", "monthly", "final"}
# Majburiy testlar jadvali: navbati kelguncha qulflangan (taxminiy sana), kelganda ochiladi va o'quv rejaga qo'shiladi
MANDATORY_SCHEDULE = [
    {"type": "daily", "name": "Kunlik 5 ta test", "state": "done", "date": "Bugun", "note": "Bugungisi topshirildi · ertaga 08:00 da yangisi"},
    {"type": "topic", "name": "Mavzu testi: Python: shart operatorlari", "state": "locked", "date": "23-noyabr", "note": "Mavzu darslari tugagach ochiladi"},
    {"type": "interim", "name": "Oraliq sinov testi: 4–6 mavzular", "state": "locked", "date": "29-noyabr", "note": "6-mavzudan keyin"},
    {"type": "monthly", "name": "Oylik test: dekabr", "state": "locked", "date": "8-dekabr", "note": "Har 30 kunda"},
    {"type": "final", "name": "Yakuniy diagnostika", "state": "locked", "date": "19-dekabr", "note": "Barcha mavzular o‘zlashtirilgach"},
]
# Namunada ?oylik=1: oylik test vaqti kelgan va boshlab qo'yilgan (yakunlanmagan majburiy test)
UNFINISHED_MONTHLY = {"key": "oylik-noyabr", "type": "monthly", "name": "Oylik test: noyabr", "note": "12 / 30 savol · javoblar saqlangan", "pct": 40}

UNFINISHED_TESTS = [
    {"key": "xatolar-1", "type": "errors", "name": "Xatolar ustida ishlash", "note": "6 / 15 savol · javoblar saqlangan", "pct": 40},
    {"key": "ixtiyoriy-1", "type": "optional", "name": "Ixtiyoriy test: Shart operatorlari", "note": "4 / 10 savol · javoblar saqlangan", "pct": 40},
]
DECISION = {"pass": (_l("O‘tdi"), "green"), "warn": (_l("Tavsiya bilan"), "yellow"), "fail": (_l("Qaytarildi"), "red")}
# Test turlari haqida qisqa ma'lumot (Natijalarim va Testlar sahifalarida)
TEST_TYPE_INFO = [
    ("diagnostic", _l("Tizimga birinchi kirganda (ixtiyoriy). O‘quv reja shu natijadan tuziladi.")),
    ("topic", _l("Har mavzu so‘ngida (majburiy). Mavzuni qay darajada o‘zlashtirganingizni aniqlaydi.")),
    ("daily", _l("Har kuni 5 ta savol (majburiy): ko‘p xato qilayotgan mavzulardan.")),
    ("interim", _l("Har 3 ta o‘zlashtirilgan mavzudan keyin (majburiy).")),
    ("weekly", _l("Har yakshanba (ixtiyoriy): shu paytgacha o‘zlashtirilgan mavzulardan.")),
    ("monthly", _l("Har 30 kunda (majburiy). Topshirilmaguncha keyingi mavzular ochilmaydi.")),
    ("optional", _l("O‘zlashtirgan mavzularingizdan, savollar sonini o‘zingiz tanlaysiz. O‘zlashtirish foiziga ta’sir qilmaydi.")),
    ("exam", _l("35 ta savol, 120 daqiqa, real attestatsiya interfeysida (ixtiyoriy, istalgan paytda).")),
    ("final", _l("Barcha mavzular o‘zlashtirilgach. Natijasi bo‘yicha sertifikat beriladi.")),
]
# Bosqichli testlar: oson → (to'g'ri javob berilgan mavzulardan) o'rta → qiyin. Noto'g'ri javob berilgan mavzu
# o'zlashtirilmagan deb hisoblanadi. Faqat shu turlarga «Bosqichlar orasi» ekrani qo'llanadi.
STAGED_TYPES = {"diagnostic", "interim", "weekly", "optional", "monthly", "final"}
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
    {"id": 3, "when": "Bugun, 11:20", "q": "(A ∨ B) ∧ ¬(A ∧ B) ifodasi qachon 1 ga teng bo‘ladi?", "state": "review",
     "reason": "also_correct", "note": "Rostlik jadvali bo‘yicha B variant ham to‘g‘ri chiqadi."},
    {"id": 2, "when": "12-noyabr", "q": "Rekursiyaning bazaviy sharti to‘g‘ri ko‘rsatilgan javobni aniqlang",
     "state": "accepted", "verdict": "Savol matnidagi 2-shartda noaniqlik borligi tasdiqlandi. Siz ko‘rsatgan javob to‘g‘ri deb hisoblandi.",
     "recalc": ("78%", "82%")},
    {"id": 1, "when": "5-noyabr", "q": "Ikkilik sanoq sistemasida 101101 + 11011 yig‘indisi nechaga teng?", "state": "rejected",
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

# Bosh sahifa: har kirishda tasodifiy tanlanadigan qisqa motivatsion so'zlar
MOTTOS = [
    _l("Bugun kichik qadam — ertaga katta natija."),
    _l("Har bir to‘g‘ri javob sizni maqsadga yaqinlashtiradi."),
    _l("Bilim — eng ishonchli sarmoya."),
    _l("Xato qilish — o‘rganishning bir qismi."),
    _l("Izchillik iqtidordan kuchliroq."),
    _l("Bugun o‘rgangan narsangiz ertangi darsingizni boyitadi."),
    _l("Oz-ozdan, lekin har kuni."),
    _l("Siz uddalaysiz — attestatsiya yaqin!"),
]

# «Bugun» rejasi: hozirgi (tugallanmagan) mavzu bo'yicha qolgan ishlar va taxminiy vaqt (daqiqa).
# Mavzu ichidagi bo'limlar → mavzu testi → kunlik majburiy test → (mavzudan keyin bo'lsa) majburiy nazorat testi.
TODAY = [
    {"title": "elif zanjiri", "sub": "Python: shart operatorlari · 3-bo‘lim", "min": 6, "done": False, "endpoint": "user.lesson", "icon": "book"},
    {"title": "Ichma-ich shartlar", "sub": "Python: shart operatorlari · 4-bo‘lim", "min": 6, "done": False, "endpoint": "user.lesson", "icon": "book"},
    {"title": "Mavzu testi", "sub": "Majburiy · 10 savol", "min": 8, "done": False, "endpoint": "test.question", "icon": "clipboard"},
    {"title": "Kunlik 5 ta test", "sub": "Majburiy · ko‘p xato qilayotgan mavzulardan", "min": 3, "done": True, "endpoint": "test.question", "args": {"turi": "kunlik"}, "icon": "zap"},
]
TODAY_CONTROL = {"title": "Oraliq sinov testi", "sub": "Majburiy · oxirgi 3 ta mavzu", "min": 35, "done": False, "endpoint": "user.control", "icon": "flag"}

# Bosh sahifa: oldingi testlarda xato qilinayotgan mavzular (xatolik foizi)
HOME_ERRORS = [
    ("Rekursiv funksiyalar va stek", "Funksiyalar", 64),
    ("Mantiqiy amallar va rostlik jadvallari", "Mantiq asoslari", 48),
    ("Ko‘p o‘lchovli ro‘yxatlar", "Ma’lumotlar tuzilmasi", 35),
    ("Murakkab shartli o‘tishlar", "Algoritmlash", 22),
    ("Sanoq sistemalarida arifmetika", "Axborot nazariyasi", 12),
]

# Yangi foydalanuvchi uchun 3 qadam (TZ 1.3: diagnostikani yakunlaganlar ≥ 60%)
ONBOARDING = [
    {"title": "Diagnostikadan o‘ting", "sub": "≈ 40 daqiqa · bilgan mavzularingizni aniqlaymiz", "endpoint": "user.diagnostic"},
    {"title": "Birinchi darsni o‘qing", "sub": "≈ 12 daqiqa · rejangizdagi birinchi mavzu", "endpoint": "user.lesson"},
    {"title": "Birinchi mavzu testini topshiring", "sub": "≈ 8 daqiqa · 10 savol", "endpoint": "test.question"},
]

NOTIFICATIONS = [
    {"icon": "clipboard", "title": "Tugatilmagan testingiz bor", "text": "«Xatolar ustida ishlash» · 6 / 15 savol saqlangan", "when": "10 daqiqa oldin", "endpoint": "user.tests", "unread": True},
    {"icon": "shield", "title": "E’tirozingizga javob keldi", "text": "Natijangiz 78% → 82% ga qayta hisoblandi", "when": "2 soat oldin", "endpoint": "user.objections", "unread": True},
    {"icon": "zap", "title": "Kunlik 5 ta test tayyor", "text": "3 daqiqa · ko‘p xato qilayotgan mavzulardan", "when": "Bugun, 08:00", "endpoint": "test.question", "unread": False},
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

# Ekspert: AI har bir mavzu va dars bo'yicha tuzgan, tekshiruvni kutayotgan savollar.
# Tasdiqlangani «Savollar banki»ga qo'shiladi, rad etilgani avtomatik o'chiriladi.
_AI_SEED = [
    ("Sanoq sistemalari", "Ikkilik va o‘nlik", "O‘rta", "yopiq", "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.", ["43", "45", "47", "53"], [1]),
    ("Mantiq asoslari", "De Morgan qonunlari", "Oson", "yopiq", "De Morgan qonuniga ko‘ra ¬(A ∧ B) nimaga teng?", ["¬A ∧ ¬B", "¬A ∨ ¬B", "A ∨ B", "A ∧ ¬B"], [1]),
    ("Algoritmlar va ma’lumotlar tuzilmasi", "Qidiruv algoritmlari", "Qiyin", "kop", "Qaysilari ikkilik qidiruv uchun to‘g‘ri?", ["Massiv saralangan bo‘lishi kerak", "Murakkabligi O(log n)", "Murakkabligi O(n²)", "Har qadamda oraliq ikkiga bo‘linadi"], [0, 1, 3]),
    ("Dasturlash asoslari", "Funksiyalar va modullar", "O‘rta", "yopiq", "Rekursiv funksiyada bazaviy shart bo‘lmasa nima bo‘ladi?", ["Bir marta ishlaydi", "RecursionError", "None qaytaradi", "Sintaksis xatosi"], [1]),
    ("Kompyuter tarmoqlari", "Protokollar", "Oson", "moslash", "Protokollarni vazifasi bilan moslang.", ["HTTP — gipermatn uzatish", "DNS — domen nomini IP ga o‘girish", "FTP — fayl uzatish"], [0, 1, 2]),
    ("Dasturlash asoslari", "Python: shart operatorlari", "O‘rta", "yopiq", "x = 7 bo‘lsa, «if x > 10: … elif x > 5: … else: …» qaysi tarmoq bajariladi?", ["if", "elif", "else", "Hech biri"], [1]),
    ("Sanoq sistemalari", "O‘n oltilik", "Qiyin", "ochiq", "2F₁₆ sonini o‘nlik sanoq sistemasida yozing.", ["47"], [0]),
    ("Ma’lumotlar bazasi va SQL", "Relyatsion model", "Oson", "yopiq", "Jadvaldagi har bir yozuvni yagona aniqlovchi maydon qanday ataladi?", ["Tashqi kalit", "Birlamchi kalit", "Indeks", "Atribut"], [1]),
]
AI_QUEUE = [
    {"id": 1000 + i, "topic": t, "lesson": l, "level": lvl, "type": k, "text": q, "options": o, "right": r,
     "created": ["Bugun", "Kecha", "2 kun oldin"][i % 3]}
    for i, (t, l, lvl, k, q, o, r) in enumerate(_AI_SEED * 3)
][:23]
Q_KINDS = {"yopiq": _l("Yopiq (bitta javob)"), "kop": _l("Ko‘p javobli"), "moslash": _l("Moslashtirish"), "ochiq": _l("Ochiq javob")}
Q_FORMATS = {"matn": _l("Matnli"), "chizma": _l("Chizmali"), "jadval": _l("Jadvalli"), "rasm": _l("Rasmli")}
Q_LEVELS = ["Oson", "O‘rta", "Qiyin"]

# Ekspert: mavzular → darslar → bloklar (matn, rasm, jadval, video, chizma) va qo'shimcha havolalar
EXPERT_CONTENT = [
    {"id": 1, "name": "Dasturlash asoslari", "lessons": [
        {"id": 11, "name": "Python asoslari", "questions": 8, "blocks": [
            {"kind": "matn", "title": "Kirish", "body": "Python — o‘qish oson, keng tarqalgan dasturlash tili."}], "links": []},
        {"id": 12, "name": "Python: shart operatorlari", "questions": 14, "blocks": [
            {"kind": "matn", "title": "if operatori", "body": "Shart operatori mantiqiy ifodaning rost yoki yolg‘on ekaniga qarab dasturni turli yo‘nalishga buradi."},
            {"kind": "chizma", "title": "Blok-sxema", "body": "flowchart TD; A[Boshlash] --> B{yosh ≥ 18?}"},
            {"kind": "jadval", "title": "Taqqoslash amallari", "body": "Amal | Ma’nosi\n== | teng\n!= | teng emas\n> | katta"},
            {"kind": "video", "title": "Video dars", "body": "https://www.youtube.com/watch?v=namuna"}],
         "links": [{"title": "Python hujjatlari: if", "url": "https://docs.python.org/3/tutorial/controlflow.html"}]},
        {"id": 13, "name": "Sikllar", "questions": 14, "blocks": [], "links": []},
        {"id": 14, "name": "Funksiyalar va modullar", "questions": 19, "blocks": [], "links": []}]},
    {"id": 2, "name": "Algoritmlar va ma’lumotlar tuzilmasi", "lessons": [
        {"id": 21, "name": "Saralash algoritmlari", "questions": 22, "blocks": [], "links": []},
        {"id": 22, "name": "Qidiruv algoritmlari", "questions": 9, "blocks": [], "links": []}]},
    {"id": 3, "name": "Kompyuter tarmoqlari", "lessons": [
        {"id": 31, "name": "IP-manzillash", "questions": 16, "blocks": [], "links": []},
        {"id": 32, "name": "Protokollar", "questions": 11, "blocks": [], "links": []}]},
    {"id": 4, "name": "Ma’lumotlar bazasi va SQL", "lessons": [
        {"id": 41, "name": "Relyatsion model", "questions": 6, "blocks": [], "links": []}]},
    {"id": 5, "name": "Sanoq sistemalari", "lessons": [
        {"id": 51, "name": "Ikkilik va o‘nlik", "questions": 18, "blocks": [], "links": []},
        {"id": 52, "name": "O‘n oltilik", "questions": 9, "blocks": [], "links": []}]},
    {"id": 6, "name": "Mantiq asoslari", "lessons": [
        {"id": 61, "name": "Mantiqiy amallar", "questions": 12, "blocks": [], "links": []},
        {"id": 62, "name": "De Morgan qonunlari", "questions": 7, "blocks": [], "links": []}]},
]
BLOCK_KINDS = [("matn", "note", _l("Matn")), ("rasm", "image", _l("Rasm")), ("jadval", "table", _l("Jadval")),
               ("video", "play", _l("Video")), ("chizma", "graph", _l("Chizma"))]

# --- Admin ---
KPI = [
    ("Foydalanuvchilar", "1 248", "+34 ta bu hafta"),
    ("Bugun faol", "312", "25% foydalanuvchilardan"),
    ("Diagnostikani tugatgan", "61%", "Maqsad ≥ 60%"),
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
            ("Diagnostikani tugatgan", "61%", "Maqsad ≥ 60%", "check-circle")],
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
