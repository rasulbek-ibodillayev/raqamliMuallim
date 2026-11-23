from flask import Blueprint, redirect, render_template, request, url_for

from .. import mock as m

# Test turi URL'da (?turi=…) → mock.TEST_TYPES kaliti. «Bosqichlar orasi» ekrani faqat mock.STAGED_TYPES uchun.
TYPE_SLUGS = {"diagnostika": "diagnostic", "mavzu": "topic", "kunlik": "daily", "oraliq": "interim", "haftalik": "weekly",
              "ixtiyoriy": "optional", "oylik": "monthly", "yakuniy": "final", "xatolar": "errors",
              "dars": "lesson"}


def _test_type():
    t = request.args.get("turi") or ("xatolar" if request.args.get("manba") == "xatolar" else "mavzu")
    return TYPE_SLUGS.get(t, "topic"), (t if t in TYPE_SLUGS else "mavzu")

bp = Blueprint("test", __name__, url_prefix="/test")

QUESTIONS = {
    "yopiq": {"n": 4, "topic": "Shart operatorlari", "type": "Bitta javob",
              "text": "Quyidagi kod natijasini aniqlang:",
              "code": "x = 5\nif x > 3:\n    print(x * 2)",
              "options": ["5", "10", "15", "Xato beradi"]},
    "kop": {"n": 5, "topic": "Kompyuter qurilmalari", "type": "Bir nechta javob",
            "text": "Quyidagilardan qaysilari kiritish qurilmalari?",
            "options": ["Klaviatura", "Monitor", "Sichqoncha", "Printer", "Skaner"]},
    "moslash": {"n": 6, "topic": "Tarmoq texnologiyalari", "type": "Moslashtirish",
                "text": "Atamalarni ta’riflari bilan moslashtiring.",
                "pairs": ["HTTP", "DNS", "IP", "FTP"],
                "answers": ["Gipermatn uzatish protokoli", "Domen nomini IP-manzilga o‘giradi",
                            "Qurilmaning tarmoqdagi manzili", "Fayl uzatish protokoli"]},
    # Jadvalli savol (masalan, elektron jadval yoki rostlik jadvali bilan)
    "jadval": {"n": 8, "topic": "Elektron jadvallar", "type": "Bitta javob", "mode": "yopiq",
               "text": "Jadvalda C4 katakka =SUMIF(A1:A3;\">1\";B1:B3) formulasi yozildi. C4 qiymati nechaga teng?",
               "table": {"head": ["", "A", "B", "C"],
                         "rows": [["1", "1", "10", ""], ["2", "2", "20", ""], ["3", "3", "30", ""], ["4", "", "", "?"]]},
               "options": ["60", "50", "30", "20"]},
    # Rasmli savol (sxema, diagramma, ekran tasviri va h.k.)
    "rasm": {"n": 9, "topic": "Mantiq asoslari", "type": "Bitta javob", "mode": "yopiq",
             "text": "Rasmdagi mantiqiy sxema qaysi ifodaga mos keladi?",
             "image": {"src": "img/savol-mantiqiy-sxema.svg",
                       "alt": "Mantiqiy sxema: A va B kirishlari OR elementiga va AND elementiga ulangan; AND chiqishi NOT orqali o‘tadi; ikkala natija oxirgi AND elementiga beriladi, chiqish F.",
                       "caption": "1-rasm. Mantiqiy sxema"},
             "options": ["F = (A ∨ B) ∧ ¬(A ∧ B)", "F = (A ∧ B) ∨ ¬(A ∨ B)", "F = ¬(A ∨ B)", "F = A ∧ B"]},
    "ochiq": {"n": 7, "topic": "Sanoq sistemalari", "type": "Ochiq javob",
              "text": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
              "hint": "Faqat sonni kiriting"},
}


@bp.get("/savol")
def question():
    kind = request.args.get("tur", "yopiq")
    q = QUESTIONS.get(kind, QUESTIONS["yopiq"])
    ttype, slug = _test_type()
    staged = ttype in m.STAGED_TYPES
    try:
        total = max(1, min(50, int(request.args.get("soni", 10))))
    except ValueError:
        total = 10
    # mode — javob berish usuli (yopiq/kop/moslash/ochiq); rasm va jadval istalgan turga qo'shilishi mumkin.
    # Bosqichli test (diagnostika, oraliq, haftalik, ixtiyoriy, oylik, yakuniy) — keyin «Bosqichlar orasi»;
    # boshqalari (mavzu testi, kunlik, xatolar ustida ishlash) — to'g'ridan-to'g'ri natijaga.
    # Forma GET bilan yuboriladi: action manzilidagi ?turi=… brauzer tomonidan tashlab yuboriladi,
    # shuning uchun test turi formaning yashirin maydoni (turi) orqali uzatiladi.
    next_url = url_for("test.stage") if staged else url_for("test.result")
    return render_template("test/question.html", q=q, kind=q.get("mode", kind), total=total,
                           offline=bool(request.args.get("oflayn")), staged=staged, ttype=ttype,
                           tname=m.TEST_TYPES[ttype][0], next_url=next_url, slug=slug)


@bp.get("/bosqich")
def stage():
    """Bosqichlar orasi: faqat diagnostika, oraliq sinov, haftalik, ixtiyoriy, oylik test va yakuniy diagnostikada."""
    ttype, slug = _test_type()
    if request.args.get("turi") and ttype not in m.STAGED_TYPES:
        return redirect(url_for("test.result", turi=slug))
    if ttype not in m.STAGED_TYPES:
        ttype, slug = "interim", "oraliq"
    return render_template("test/stage.html", slug=slug, tname=m.TEST_TYPES[ttype][0])


@bp.get("/natija")
def result():
    failed = request.args.get("holat") == "qaytarildi"
    return render_template("test/result.html", failed=failed, questions=m.RESULT_QUESTIONS)


EXAM_POOL = [
    {"topic": "Mantiq asoslari", "text": "(A ∨ B) ∧ ¬(A ∧ B) mantiqiy ifodasi qachon 1 ga teng bo‘ladi?",
     "options": ["Faqat A va B bir vaqtda rost bo‘lganda", "A va B turli qiymatga ega bo‘lganda",
                 "A va B ikkalasi yolg‘on bo‘lganda", "Har doim"], "right": 1},
    {"topic": "Sanoq sistemalari", "text": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
     "options": ["43", "45", "47", "53"], "right": 1},
    {"topic": "Dasturlash", "text": "Quyidagi Python kodi natijasini aniqlang:",
     "code": "s = 0\nfor i in range(1, 5):\n    s += i\nprint(s)", "options": ["10", "15", "4", "5"], "right": 0},
    {"topic": "Tarmoq texnologiyalari", "text": "DNS serverning asosiy vazifasi qaysi?",
     "options": ["Fayllarni uzatish", "Domen nomini IP-manzilga o‘girish", "Elektron xat yuborish", "Sahifani shifrlash"], "right": 1},
    {"topic": "Elektron jadvallar", "text": "C4 katakka =SUMIF(A1:A3;\">1\";B1:B3) formulasi yozildi. C4 qiymati nechaga teng?",
     "table": {"head": ["", "A", "B", "C"], "rows": [["1", "1", "10", ""], ["2", "2", "20", ""], ["3", "3", "30", ""], ["4", "", "", "?"]]},
     "options": ["60", "50", "30", "20"], "right": 1},
    {"topic": "Mantiq asoslari", "text": "Rasmdagi mantiqiy sxema qaysi ifodaga mos keladi?",
     "image": {"src": "img/savol-mantiqiy-sxema.svg", "alt": "Mantiqiy sxema: OR va NAND elementlari natijasi AND orqali F chiqishiga beriladi"},
     "options": ["F = (A ∨ B) ∧ ¬(A ∧ B)", "F = (A ∧ B) ∨ ¬(A ∨ B)", "F = ¬(A ∨ B)", "F = A ∧ B"], "right": 0},
    {"topic": "Axborot hajmi", "text": "256 xil belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
     "options": ["6", "7", "8", "16"], "right": 2},
    # Rasmli savollar (attestatsiyada sxema, tarmoq chizmasi, blok-sxema va h.k. bo'ladi)
    {"topic": "Tarmoq texnologiyalari", "text": "Rasmda kompyuter tarmog‘ining qaysi topologiyasi tasvirlangan?",
     "image": {"src": "img/savol-tarmoq-topologiya.svg", "alt": "Oltita kompyuter markazdagi bitta hub qurilmasiga alohida kabel bilan ulangan"},
     "options": ["Shina", "Halqa", "Yulduz", "To‘liq bog‘langan"], "right": 2},
    {"topic": "Algoritmlash", "text": "Blok-sxemada tasvirlangan algoritm bajarilgach, qanday qiymat chiqariladi?",
     "image": {"src": "img/savol-blok-sxema.svg", "alt": "Blok-sxema: s = 0, i = 1; i ≤ 4 bo‘lsa s = s + i va i = i + 1, aks holda s chiqariladi"},
     "options": ["4", "6", "10", "15"], "right": 2},
]


@bp.get("/sinov")
def exam():
    from flask import url_for
    qs = []
    for i in range(35):
        q = dict(EXAM_POOL[i % len(EXAM_POOL)])
        if "image" in q:
            q["image"] = {**q["image"], "src": url_for("static", filename=q["image"]["src"])}
        qs.append(q)
    start_given = "savol" in request.args
    try:
        start = max(1, min(35, int(request.args.get("savol", 1)))) - 1
    except ValueError:
        start = 0
    # namuna=1 — /ekranlar uchun: oldindan javob berilgan, serverga yuborilmaydigan alohida sessiya
    sample = bool(request.args.get("namuna"))
    answered = {i: (i * 3) % 4 for i in range(1, 11) if i != start} if sample else {}
    return render_template("test/exam.html", questions=qs, start=start, start_given=start_given, answered=answered,
                           sample=sample, confirm=bool(request.args.get("yakun")))


@bp.get("/sinov/natija")
def exam_result():
    """Attestatsiya testi yakuni: to'plangan ball, har bir savol (xato javob — qizil, to'g'ri javob — yashil),
    mavzular bo'yicha o'zlashtirish foizi va qayta o'zlashtirish tavsiyasi.
    Namunada javoblar soxta; backendda urinish (attempt) javoblaridan hisoblanadi."""
    qs = []
    for i in range(35):
        q = EXAM_POOL[i % len(EXAM_POOL)]
        right = q["right"]
        # namuna: har 4-savol xato, 33–35 javobsiz; «Mantiq asoslari»da xato ko'proq
        if i >= 32:
            mine = None
        elif i % 4 == 3 or (q["topic"] == "Mantiq asoslari" and i % 3 == 0):
            mine = (right + 1) % len(q["options"])
        else:
            mine = right
        image = {**q["image"], "src": url_for("static", filename=q["image"]["src"])} if q.get("image") else None
        qs.append({"n": i + 1, "topic": q["topic"], "q": q["text"], "code": q.get("code"), "image": image,
                   "table": q.get("table"), "options": q["options"], "mine": mine, "right": right})
    correct = sum(1 for q in qs if q["mine"] == q["right"])
    topics = {}
    for q in qs:
        t = topics.setdefault(q["topic"], [0, 0])
        t[1] += 1
        t[0] += q["mine"] == q["right"]
    by_topic = sorted(((name, round(c / n * 100), c, n) for name, (c, n) in topics.items()), key=lambda x: x[1])
    return render_template("test/exam_result.html", questions=qs, correct=correct, total=len(qs),
                           pct=round(correct / len(qs) * 100), by_topic=by_topic,
                           pass_min=m.PASS_MIN, solid_min=m.SOLID_MIN)
