from flask import Blueprint, render_template, request

from .. import mock as m

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
    # mode — javob berish usuli (yopiq/kop/moslash/ochiq); rasm va jadval istalgan turga qo'shilishi mumkin
    return render_template("test/question.html", q=q, kind=q.get("mode", kind),
                           offline=bool(request.args.get("oflayn")))


@bp.get("/bosqich")
def stage():
    return render_template("test/stage.html")


@bp.get("/natija")
def result():
    failed = request.args.get("holat") == "qaytarildi"
    return render_template("test/result.html", failed=failed, review=m.REVIEW)


EXAM_POOL = [
    {"topic": "Mantiq asoslari", "text": "(A ∨ B) ∧ ¬(A ∧ B) mantiqiy ifodasi qachon 1 ga teng bo‘ladi?",
     "options": ["Faqat A va B bir vaqtda rost bo‘lganda", "A va B turli qiymatga ega bo‘lganda",
                 "A va B ikkalasi yolg‘on bo‘lganda", "Har doim"]},
    {"topic": "Sanoq sistemalari", "text": "101101₂ sonini o‘nlik sanoq sistemasiga o‘tkazing.",
     "options": ["43", "45", "47", "53"]},
    {"topic": "Dasturlash", "text": "Quyidagi Python kodi natijasini aniqlang:",
     "code": "s = 0\nfor i in range(1, 5):\n    s += i\nprint(s)", "options": ["10", "15", "4", "5"]},
    {"topic": "Tarmoq texnologiyalari", "text": "DNS serverning asosiy vazifasi qaysi?",
     "options": ["Fayllarni uzatish", "Domen nomini IP-manzilga o‘girish", "Elektron xat yuborish", "Sahifani shifrlash"]},
    {"topic": "Elektron jadvallar", "text": "C4 katakka =SUMIF(A1:A3;\">1\";B1:B3) formulasi yozildi. C4 qiymati nechaga teng?",
     "table": {"head": ["", "A", "B", "C"], "rows": [["1", "1", "10", ""], ["2", "2", "20", ""], ["3", "3", "30", ""], ["4", "", "", "?"]]},
     "options": ["60", "50", "30", "20"]},
    {"topic": "Mantiq asoslari", "text": "Rasmdagi mantiqiy sxema qaysi ifodaga mos keladi?",
     "image": {"src": "img/savol-mantiqiy-sxema.svg", "alt": "Mantiqiy sxema: OR va NAND elementlari natijasi AND orqali F chiqishiga beriladi"},
     "options": ["F = (A ∨ B) ∧ ¬(A ∧ B)", "F = (A ∧ B) ∨ ¬(A ∨ B)", "F = ¬(A ∨ B)", "F = A ∧ B"]},
    {"topic": "Axborot hajmi", "text": "256 xil belgidan iborat alifbodagi bitta belgi necha bit axborot olib keladi?",
     "options": ["6", "7", "8", "16"]},
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
    start = max(1, min(35, int(request.args.get("savol", 1)))) - 1
    answered = {i: (i * 3) % 4 for i in range(1, 11) if i != start}  # namunaviy javoblar
    return render_template("test/exam.html", questions=qs, start=start, answered=answered,
                           flagged=[8, 13], confirm=bool(request.args.get("yakun")))
