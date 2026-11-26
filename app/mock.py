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
    "phone_raw": "+998901234567",
    "email": "dilnoza.k@maktab.uz",
    "days_left": 38,
    "exam_date": "23-dekabr",
}

# Foydalanuvchi paneli navigatsiyasi: (endpoint, nom, ikonka, mobil pastki panelda)
# Ekspert va admin profillari (namuna). Backendda: current_user
STAFF = {
    "expert": {"first": "Zuhra", "last": "Qodirova", "initials": "ZQ", "role": _l("Ekspert (metodist)"),
               "phone": "+998 93 *** ** 45", "phone_raw": "+998931234545", "email": "zuhra.q@raqamlimuallim.uz"},
    "admin": {"first": "Aziz", "last": "Rahimov", "initials": "AR", "role": _l("Administrator"),
              "phone": "+998 97 *** ** 10", "phone_raw": "+998971234510", "email": "aziz.r@raqamlimuallim.uz"},
}

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
            ("user.offline", _l("Oflayn darslar"), "download"),
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
        ("expert.questions", _l("Savollar banki"), "database", None),
        ("expert.topics", _l("Mavzular va darslar"), "book", None),
        ("expert.objections", _l("E’tirozlar"), "flag", None),
    ],
    # Admin: foydalanuvchilar, ekspertlar, statistika va tizim sozlamalari (kontent bilan ishlamaydi)
    "admin": [
        ("admin.stats", _l("Statistika"), "chart", None),
        ("admin.users", _l("Foydalanuvchilar"), "users", None),
        ("admin.experts", _l("Ekspertlar"), "shield", None),
        ("admin.settings", _l("Sozlamalar"), "settings", None),
        ("admin.journal", _l("Jurnal"), "list", None),
        ("admin.jobs", _l("Fon vazifalari"), "refresh", None),
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
# Mavzu → darslar. Har dars so'ngida 3 savollik «dars testi» olinadi:
#   < 70% — darsni qayta o'zlashtirishga yuboriladi (keyingi dars yopiq);
#   70–89% — qayta o'zlashtirish tavsiya etiladi, lekin keyingi darsga o'tkaziladi («Xatolar analitikasi»da saqlanadi);
#   ≥ 90% — tavsiyasiz keyingi darsga o'tkaziladi.
# Darslar tugagach — mavzu testi: savollar soni = 2 × darslar soni, imkon qadar dars testlarida xato qilingan savol
# turlaridan tuziladi. Chegaralar xuddi shunday, lekin mavzu bo'yicha. Barcha natijalar «Natijalarim»ga tushadi.
# Dars testi: ok — to'plangan ball (qisman ball bilan kasr bo'lishi mumkin), rid — natija (tafsilotga havola).
LESSON_TEST_N = 3


def _L(name, pct=None, rid=None, when=None, mn=None, tries=None):
    return {"name": name, "pct": pct, "rid": rid, "when": when, "min": mn, "tries": tries, "n": LESSON_TEST_N,
            "ok": None if pct is None else round(pct * LESSON_TEST_N / 100, 1)}


def _T(pct, rid, when, lessons, tries=None):
    return {"pct": pct, "rid": rid, "when": when, "n": 2 * lessons, "tries": tries}


LEARN_PLAN = [
    {"kind": "topic", "id": 1, "name": "Kompyuter arxitekturasi va mantiqiy asoslar", "state": "done", "pct": 92, "min": 40,
     "lessons": [_L("Kompyuter qurilmalari", 100, 21, "8-noyabr"), _L("Protsessor va xotira", 100, 22, "9-noyabr"),
                 _L("Mantiqiy amallar", 83, 23, "9-noyabr")],
     "test": _T(92, 11, "10-noyabr", 3)},
    {"kind": "topic", "id": 2, "name": "Algoritmlash asoslari va blok-sxemalar", "state": "done", "pct": 83, "min": 35,
     "lessons": [_L("Algoritm tushunchasi", 100, 24, "11-noyabr"), _L("Blok-sxemalar", 78, 25, "11-noyabr", tries=2),
                 _L("Chiziqli algoritmlar", 92, 26, "12-noyabr")],
     "test": _T(83, 12, "13-noyabr", 3, tries=2)},
    {"kind": "topic", "id": 3, "name": "Sanoq sistemalari", "state": "done", "pct": 92, "min": 30,
     "lessons": [_L("Ikkilik sanoq sistemasi", 100, 27, "14-noyabr"), _L("O‘n oltilik sanoq sistemasi", 92, 28, "15-noyabr")],
     "test": _T(92, 1, "Bugun", 2, tries=2)},
    {"kind": "test", "type": "interim", "name": "Oraliq sinov testi: 1–3 mavzular", "state": "done", "pct": 78, "min": 35, "rid": 2},
    {"kind": "topic", "id": 4, "name": "Python: shart operatorlari", "state": "current", "pct": None, "read": 60, "min": 12,
     "lessons": [_L("if operatori", 100, 29, "Kecha", mn=4), _L("if / else", 86, 30, "Bugun", mn=4),
                 _L("elif zanjiri", mn=6), _L("Ichma-ich shartlar", mn=6)],
     "test": None},
    {"kind": "test", "type": "daily", "name": "Kunlik test", "state": "done", "pct": 80, "min": 3, "rid": 9,
     "note": "Ko‘p xato qilayotgan mavzulardan"},
    {"kind": "test", "type": "weekly", "name": "Haftalik test", "state": "due", "min": 20,
     "note": "Bugun yakshanba · o‘zlashtirilgan mavzulardan"},
    {"kind": "topic", "id": 5, "name": "Python: sikllar (for, while)", "state": "locked", "date": "24-noyabr", "min": 45,
     "lessons": [_L("for sikli"), _L("while sikli"), _L("break va continue")]},
    {"kind": "topic", "id": 6, "name": "Funksiyalar va modullar", "state": "locked", "date": "26-noyabr", "min": 45,
     "lessons": [_L("Funksiya e’lon qilish"), _L("Parametrlar"), _L("Rekursiya")]},
    {"kind": "topic", "id": 7, "name": "Massivlar va ro‘yxatlar", "state": "locked", "date": "28-noyabr", "min": 40,
     "lessons": [_L("Ro‘yxat amallari"), _L("Ko‘p o‘lchovli ro‘yxatlar")]},
    {"kind": "test", "type": "interim", "name": "Oraliq sinov testi: 4–6 mavzular", "state": "locked", "date": "29-noyabr", "min": 35},
    {"kind": "topic", "id": 8, "name": "Ma’lumotlar bazasi: relyatsion model", "state": "locked", "date": "2-dekabr", "min": 40,
     "lessons": [_L("Jadval va kalitlar"), _L("SQL so‘rovlari")]},
    {"kind": "test", "type": "monthly", "name": "Oylik test: dekabr", "state": "locked", "date": "8-dekabr", "min": 45,
     "note": "Har 30 kunda · topshirilmaguncha keyingi mavzular ochilmaydi"},
    {"kind": "topic", "id": 9, "name": "Kompyuter tarmoqlari va protokollar", "state": "locked", "date": "10-dekabr", "min": 40,
     "lessons": [_L("Tarmoq turlari"), _L("Protokollar")]},
    {"kind": "test", "type": "final", "name": "Yakuniy diagnostika", "state": "locked", "date": "19-dekabr", "min": 90,
     "note": "Barcha mavzular o‘zlashtirilgach. Natijasi bo‘yicha sertifikat beriladi"},
]


def lesson_decision(pct):
    """Dars yoki mavzu testi natijasi bo'yicha qaror: relearn (< 70%), recommend (70–89%), pass (≥ 90%)."""
    if pct is None:
        return None
    return "relearn" if pct < PASS_MIN else ("recommend" if pct < SOLID_MIN else "pass")

# Oylik test (majburiy, har 30 kunda): vaqti kelganda rejaga qo'shiladi. Joriy mavzu tugallanmagan bo'lsa —
# mavzu tugagach olinadi; yakunlanmaguncha keyingi mavzular ochilmaydi. Namunada ?oylik=1.
MONTHLY_DUE = {"kind": "test", "type": "monthly", "name": "Oylik test: noyabr", "state": "started", "min": 45,
               "note": "Boshlangan · 12 / 30 savol saqlangan. Yakunlanmaguncha keyingi mavzu ochilmaydi"}

# Diagnostikada ≥ 90% chiqqani uchun rejadan chiqarilgan mavzular
PLAN_EXCLUDED = [("Ofis dasturlari: elektron jadvallar", 98), ("IP-manzillash va maskalar", 95), ("Axborot hajmi va o‘lchov birliklari", 92)]
# Chiqarilgan mavzulardagi darslar soni (to'liq ish reja = shaxsiy reja + chiqarilganlar)
PLAN_EXCLUDED_LESSONS = {"Ofis dasturlari: elektron jadvallar": 3, "IP-manzillash va maskalar": 2,
                         "Axborot hajmi va o‘lchov birliklari": 2}
# Diagnostikada har bir dars bo'yicha savol(lar)ga ajratilgan vaqt, soniya (backendda: savollarning time_limit_s yig'indisi)
DIAG_SEC_PER_LESSON = 60


def diagnostic_estimate(plan=None):
    """Diagnostika vaqti = to'liq o'quv rejadagi har bir dars savollari uchun ajratilgan vaqtlar yig'indisi.
    Natija: (darslar soni, daqiqa)."""
    lessons = sum(len(t.get("lessons", [])) for t in (plan or LEARN_PLAN)) + sum(PLAN_EXCLUDED_LESSONS.values())
    return lessons, -(-lessons * DIAG_SEC_PER_LESSON // 60)
PLAN_SUMMARY = {"done": 14, "total": 42, "avg": 88, "days_left": 38, "per_day": "≈ 1 mavzu", "exam": "23-dekabr",
                "next_control": "2 mavzu"}
TEST_TYPES = {
    "diagnostic": ("Diagnostika testi", "target"), "topic": ("Mavzu testi", "clipboard"), "daily": ("Kunlik test", "zap"),
    "exam": ("Attestatsiya testi", "clock"), "interim": ("Oraliq sinov testi", "flag"), "weekly": ("Haftalik test", "calendar"),
    "optional": ("Ixtiyoriy test", "settings"), "monthly": ("Oylik test", "calendar"), "final": ("Yakuniy diagnostika", "award"),
    "errors": ("Xatolar ustida ishlash", "target"), "lesson": ("Dars testi", "note"),
}

# «Natijalarim»: dastlabki diagnostikadan boshlab barcha turdagi yakunlangan testlar (type — TEST_TYPES kaliti).
# Qayta topshirilganda shu turdagi YANGI savollar beriladi va natija ro'yxatga yangi qator bo'lib qo'shiladi.
RESULTS = [
    {"id": 30, "type": "lesson", "name": "Dars testi: if / else", "when": "Bugun, 15:05", "pct": 86, "decision": "warn", "n": 3, "min": 3},
    {"id": 29, "type": "lesson", "name": "Dars testi: if operatori", "when": "Kecha, 19:30", "pct": 100, "decision": "pass", "n": 3, "min": 3},
    {"id": 9, "type": "daily", "name": "Kunlik test", "when": "Bugun, 08:10", "pct": 80, "decision": "warn", "n": 5, "min": 3},
    {"id": 1, "type": "topic", "name": "Sanoq sistemalari (2-urinish)", "when": "Bugun, 14:20", "pct": 92, "decision": "pass", "n": 4, "min": 4},
    {"id": 8, "type": "errors", "name": "Xatolar ustida ishlash", "when": "Kecha, 20:05", "pct": 70, "decision": "warn", "n": 10, "min": 8},
    {"id": 2, "type": "interim", "name": "Oraliq sinov testi: 1–3 mavzular", "when": "Kecha, 18:45", "pct": 78, "decision": "warn", "n": 30, "min": 35},
    {"id": 7, "type": "weekly", "name": "Haftalik test", "when": "16-noyabr", "pct": 86, "decision": "pass", "n": 20, "min": 20},
    {"id": 10, "type": "optional", "name": "Ixtiyoriy test: Sanoq sistemalari", "when": "14-noyabr", "pct": 90, "decision": "pass", "n": 10, "min": 10},
    {"id": 12, "type": "topic", "name": "Algoritmlash asoslari va blok-sxemalar (2-urinish)", "when": "13-noyabr", "pct": 83, "decision": "warn", "n": 6, "min": 6},
    {"id": 3, "type": "topic", "name": "Sanoq sistemalari", "when": "12-noyabr", "pct": 62, "decision": "fail", "n": 4, "min": 4},
    {"id": 11, "type": "topic", "name": "Kompyuter arxitekturasi va mantiqiy asoslar", "when": "10-noyabr", "pct": 92, "decision": "pass", "n": 6, "min": 6},
    {"id": 4, "type": "diagnostic", "name": "Dastlabki diagnostika", "when": "8-noyabr", "pct": 70, "decision": "pass", "n": 60, "min": 70},
    {"id": 5, "type": "exam", "name": "Attestatsiya testi", "when": "5-noyabr", "pct": 84, "decision": "pass", "n": 35, "min": 120},
    {"id": 6, "type": "topic", "name": "Algoritmlash asoslari va blok-sxemalar", "when": "11-noyabr", "pct": 65, "decision": "fail", "n": 6, "min": 6},
]
# O'quv rejadagi qolgan dars testlari ham «Natijalarim»da (rid — LEARN_PLAN dagi dars natijasi)
RESULTS += [{"id": l["rid"], "type": "lesson", "name": f"Dars testi: {l['name']}", "when": l["when"], "pct": l["pct"],
             "decision": {"pass": "pass", "recommend": "warn", "relearn": "fail"}[lesson_decision(l["pct"])],
             "n": l["n"], "min": 3}
            for t in LEARN_PLAN if t["kind"] == "topic" and t["state"] == "done" for l in t["lessons"]]
# Namunaviy natija id'lari haqiqiy test_attempts.id bilan to'qnashmasin (reja va bosh sahifa bazaga o'tguncha, 5b)
MOCK_RID = 900_000
for _r in RESULTS:
    _r["id"] += MOCK_RID
for _t in LEARN_PLAN:
    for _x in [_t, _t.get("test") or {}, *_t.get("lessons", [])]:
        if _x.get("rid"):
            _x["rid"] += MOCK_RID
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
     "why": "Ifoda XOR (istisno qiluvchi YOKI) ga teng: faqat bittasi rost bo‘lganda 1.",
     "notes": ["A = B = 1 bo‘lsa, A ∧ B = 1, uning inkori 0, demak butun ifoda 0.",
               "Biri 1, ikkinchisi 0: A ∨ B = 1, ¬(A ∧ B) = 1, ko‘paytmasi 1.",
               "A = B = 0 bo‘lsa, A ∨ B = 0, demak butun ifoda 0.",
               "Qiymatlar bir xil bo‘lganda (0 0 va 1 1) ifoda 0, shuning uchun har doim emas."]},
    {"n": 5, "topic": "Funksiyalar", "level": "Qiyin", "q": "Rekursiv funksiyada bazaviy shart bo‘lmasa nima bo‘ladi?",
     "options": ["Funksiya bir marta ishlaydi", "RecursionError (stek to‘lib qoladi)", "None qaytaradi", "Sintaksis xatosi"], "mine": 1, "right": 1},
    {"n": 6, "topic": "Axborot hajmi", "level": "Qiyin", "q": "256 xil belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
     "options": ["6", "7", "8", "16"], "mine": 3, "right": 2, "why": "2⁸ = 256, demak har bir belgi 8 bit."},
]

# «Testlar» bo'limi: yakunlanmagan (to'xtatilgan) testlar — istalgan turdagi
# Majburiy turlar (yakunlanmagan bo'lsa — keyingi mavzu va keyingi majburiy test yopiq), qolganlari ixtiyoriy
MANDATORY_TYPES = {"lesson", "topic", "daily", "interim", "monthly", "final"}
# Majburiy testlar jadvali: navbati kelguncha qulflangan (taxminiy sana), kelganda ochiladi va o'quv rejaga qo'shiladi
# Namunada ?oylik=1: oylik test vaqti kelgan va boshlab qo'yilgan (yakunlanmagan majburiy test)
UNFINISHED_MONTHLY = {"key": "oylik-noyabr", "type": "monthly", "name": "Oylik test: noyabr", "note": "12 / 30 savol · javoblar saqlangan", "pct": 40}

DECISION = {"pass": (_l("O‘tdi"), "green"), "warn": (_l("Tavsiya bilan"), "yellow"), "fail": (_l("Qaytarildi"), "red")}
# Test turlari haqida qisqa ma'lumot (Natijalarim va Testlar sahifalarida)
TEST_TYPE_INFO = [
    ("diagnostic", _l("Tizimga birinchi kirganda (ixtiyoriy). O‘quv reja shu natijadan tuziladi.")),
    ("lesson", _l("Har dars so‘ngida 3 ta savol (majburiy). 70% dan past — dars qayta o‘zlashtiriladi, 70–89% — tavsiya bilan keyingi darsga o‘tasiz.")),
    ("topic", _l("Mavzu darslari tugagach (majburiy). Savollar soni darslar sonidan 2 barobar, dars testlaridagi xatolaringiz turidan.")),
    ("daily", _l("Har kuni (majburiy): ko‘p xato qilayotgan mavzulardan.")),
    ("interim", _l("Har 3 ta o‘zlashtirilgan mavzudan keyin (majburiy).")),
    ("weekly", _l("Har yakshanba (ixtiyoriy): shu paytgacha o‘zlashtirilgan mavzulardan.")),
    ("monthly", _l("Muntazam oraliqda (majburiy). Topshirilmaguncha keyingi mavzular ochilmaydi.")),
    ("optional", _l("O‘zlashtirgan mavzularingizdan, savollar sonini o‘zingiz tanlaysiz. O‘zlashtirish foiziga ta’sir qilmaydi.")),
    ("exam", _l("Real attestatsiya interfeysida, vaqt bilan (ixtiyoriy, istalgan paytda).")),
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
    "free": (_l("O‘rganilmoqda"), "blue", _l("Attestatsiya sanasi belgilangach, ulgurish prognozi chiqadi.")),
    "none": (_l("Ma’lumot yig‘ilmoqda"), "gray", _l("Prognoz uchun so‘nggi 14 kunda kamida bitta mavzu testidan o‘ting.")),
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
    {"title": "Mavzu testi", "sub": "Majburiy · 8 savol", "min": 8, "done": False, "endpoint": "test.question", "args": {"turi": "mavzu", "soni": 8}, "icon": "clipboard"},
    {"title": "Kunlik test", "sub": "Majburiy · ko‘p xato qilayotgan mavzulardan", "min": 3, "done": True, "endpoint": "test.question", "args": {"turi": "kunlik"}, "icon": "zap"},
]
TODAY_CONTROL = {"title": "Oraliq sinov testi", "sub": "Majburiy · oxirgi 3 ta mavzu", "min": 35, "done": False, "endpoint": "user.control", "icon": "flag"}

# Yangi foydalanuvchi uchun 3 qadam (TZ 1.3: diagnostikani yakunlaganlar ≥ 60%)
ONBOARDING = [
    {"title": "Diagnostikadan o‘ting", "sub": f"≈ {diagnostic_estimate()[1]} daqiqa · bilgan mavzularingizni aniqlaymiz", "endpoint": "user.diagnostic"},
    {"title": "Birinchi darsni o‘qing", "sub": "≈ 12 daqiqa · rejangizdagi birinchi mavzu", "endpoint": "user.lesson"},
    {"title": "Birinchi dars testini topshiring", "sub": "≈ 3 daqiqa · 3 savol", "endpoint": "test.question", "args": {"turi": "dars", "soni": 3}},
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

# --- Ekspert ---
QUEUE = [
    ("101101 ikkilik sonini o‘nlik sanoq sistemasiga…", "Sanoq sistemalari", "O‘rta", "Yopiq test", "AI generator", "ai"),
    ("De Morgan qonunlariga ko‘ra ¬(A ∧ B) ifodasi…", "Mantiq asoslari", "Oson", "Yopiq test", "Alisher Rustamov", "expert"),
    ("Ikkilik qidiruv algoritmining vaqt murakkabligi…", "Algoritmlar", "Qiyin", "Bir nechta javob", "AI generator", "ai"),
    ("Mantiqiy darvozalarni rostlik jadvali bilan moslang", "Mantiq asoslari", "O‘rta", "Moslashtirish", "Zuhra Qodirova", "expert"),
    ("Rekursiv funksiyada bazaviy shart bo‘lmasa…", "Funksiyalar", "O‘rta", "Yopiq test", "AI generator", "ai"),
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
Q_FORMATS = {"matn": _l("Matnli"), "kod": _l("Kodli"), "excel": _l("Excel oynasi"), "scratch": _l("Scratch"), "logo": _l("LOGO"),
             "tugma": _l("Dastur tugmalari"), "jadval": _l("Jadvalli"), "chizma": _l("Chizmali"), "rasm": _l("Rasmli")}
Q_LEVELS = ["Oson", "O‘rta", "Qiyin"]

# --- Admin ---
Q_STATE = {"approved": (_l("Tasdiqlangan"), "green"), "review": (_l("Tekshiruvda"), "yellow"),
           "draft": (_l("Qoralama"), "gray"), "archived": (_l("Arxivlangan"), "gray"), "paused": (_l("To‘xtatilgan"), "red")}
EXPERT_PERMS = [("questions", _l("Savol yaratish va tahrirlash")), ("review", _l("Savollarni tekshirish va tasdiqlash")),
                ("topics", _l("Mavzular va darslarni tahrirlash")), ("objections", _l("E’tirozlarni ko‘rib chiqish"))]
