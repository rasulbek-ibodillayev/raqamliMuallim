"""7d: savol formatlari — kod tillari, HTML/CSS natijasi, Excel oynasi, Scratch, LOGO, dastur tugmalari va ularning shablonlari."""
import html as htmllib
import math
import random
import re
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import select

from app.cli import demo_user
from app.extensions import db
from app.models import Question, Subtopic, TestAttempt
from app.services import attempts as at
from app.services import media, ui_icons, xlsx
from app.services import question_bank as qb
from app.services import test_builder as tb
from app.services.content_import import check_question
from app.services.highlight import LANGS, highlight, norm_lang
from app.services.question_templates import TEMPLATES, OPS
from tests.conftest import JSON

EVIL = "<script>alert(1)</script>\" onload=x '"


@pytest.fixture()
def ctx(app):
    with app.test_request_context():
        yield


# ---------------- Kod ----------------

@pytest.mark.parametrize("lang", list(LANGS))
def test_highlight_keeps_text_and_escapes(lang):
    src = EVIL + "\nif x > 3: # izoh\n  for (let i = 0; i < 5; i++) { s += 'a<b' } /* c */ p { color: #fff; } repeat 4 [fd 50]"
    out = str(highlight(src, lang))
    assert "<script" not in out and re.sub(r"</?span[^>]*>", "", out) == str(htmllib.escape(src)).replace("&quot;", "&#34;").replace("&#x27;", "&#39;")


@pytest.mark.parametrize("src,lang,parts", [
    ("x = 'if' # for", "python", ['<span class="tok-s">', '<span class="tok-c"># for</span>']),
    ("let a = 5;", "js", ['<span class="tok-k">let</span>', '<span class="tok-n">5</span>']),
    ('<p class="a">', "html", ['<span class="tok-k">&lt;p</span>', '<span class="tok-f">class</span>', "tok-s"]),
    ("p { color: red; }", "CSS", ['<span class="tok-k">p</span>', '<span class="tok-f">color</span>']),
    ("SELECT * FROM t", "sql", ['<span class="tok-k">SELECT</span>', '<span class="tok-k">FROM</span>']),
    ("Repeat 4 [FD 50]", "logo", ['<span class="tok-k">Repeat</span>', '<span class="tok-k">FD</span>']),
])
def test_highlight_tokens(src, lang, parts):
    out = str(highlight(src, lang))
    assert all(p in out for p in parts), out


def test_language_names():
    assert [norm_lang(x) for x in ("JS", "C++", "Python", None, "", "Mermaid", "LOGO", "JavaScript")] == \
        ["javascript", "cpp", "python", "python", "python", "plain", "logo", "javascript"]


def test_code_language_is_shown(ctx):
    out = media.render({"code": "let x", "lang": "javascript"})
    assert "<span>JavaScript</span>" in out and "Python" not in out
    assert "<span>Python</span>" in media.render({"code": "x = 1"})                       # eski savollar


# ---------------- HTML / CSS natijasi ----------------

def test_web_preview_is_sandboxed_and_escaped(ctx):
    out = str(media.render({"code": EVIL + "<p>a</p>", "lang": "html", "show": "both"}))
    assert 'sandbox=""' in out and "<script" not in out and out.count("<iframe") == 1 and "&lt;script&gt;" in out
    assert "<iframe" not in media.render({"code": "<p>", "lang": "html"})
    only = media.render({"code": "<p>a</p>", "lang": "html", "show": "result"})
    assert "<pre" not in only and "<iframe" in only
    css = str(media.render({"code": "p{color:red}</style><b>", "lang": "css", "show": "result", "html": "<p>x</p>"}))
    doc = htmllib.unescape(re.search(r'srcdoc="([^"]*)"', css).group(1))
    assert doc.count("</style>") == 2 and "<p>x</p>" in doc                                # kod uslubdan chiqib ketmaydi
    assert "<iframe" not in media.render({"code": "x", "lang": "python", "show": "both"})


# ---------------- Excel oynasi ----------------

def test_sheet_render(ctx):
    out = str(media.render({"sheet": {"rows": [["10", "<b>", "?"], ["5"]], "active": "C1", "formula": "=A1+B1"}}))
    ET.fromstring(out.replace("&nbsp;", " "))
    assert ">A</th>" in out and ">C</th>" in out and "D</th>" not in out and "&lt;b&gt;" in out
    assert '<td class="sel ask">?</td>' in out and "=A1+B1" in out and '<th scope="row" class="on">1</th>' in out and '<td class="num">10</td>' in out


# ---------------- Scratch ----------------

SC = ("voqea: bayroq bosilganda\nboshqaruv: [2] marta takrorla\n  boshqaruv: agar <x > 5> bo'lsa\n    ko'rinish: [Salom <b>] de\n"
      "  boshqaruv: aks holda\n    ovoz: miyov\n  harakat: (x) ga bur\nharakat: [10] qadam yur")


def test_scratch_render(ctx):
    out = str(media.render({"scratch": SC}))
    ET.fromstring(out)
    assert '<span class="sb-bool">x &gt; 5</span>' in out and "[2]" not in out and "&lt;b&gt;" in out and "aks holda" in out
    tree = media._scratch_tree(SC)
    assert [b["text"] for b in tree] == ["bayroq bosilganda", "[2] marta takrorla", "[10] qadam yur"]
    cond, turn = tree[1]["items"]
    assert [b["text"] for b in cond["items"]] == ["[Salom <b>] de"] and [b["text"] for b in cond["else"]] == ["miyov"] and turn["cat"] == "mo"


@pytest.mark.parametrize("bad", ["", "  ", "harakat 10 qadam", "nima: x", "harakat:", "  harakat: x", "harakat: a\n    harakat: b", "harakat: a\n harakat: b",
                                 "boshqaruv: aks holda", "harakat: a\nboshqaruv: aks holda", 5, "harakat: a\n" * 70])
def test_bad_scratch(bad):
    assert media.check({"scratch": bad})


# ---------------- LOGO ----------------

def test_logo_runs_like_a_turtle(ctx):
    path = media._logo_run("repeat 4 [fd 50 rt 90]")
    assert [(round(x), round(y)) for x, y, _p in path] == [(0, 0), (0, 50), (50, 50), (50, 0), (0, 0)]
    assert [p for *_xy, p in media._logo_run("FD 10 pu fd 10 pd BK 5 home")] == [False, True, False, True, True]
    assert media._logo_run("fd 50 cs lt 90 fd 10")[-1][:2] == pytest.approx((-10, 0))
    assert media._logo_run("oldinga 10 o'ngga 90 takrorla 2 [orqaga 5]")[-1][:2] == pytest.approx((-10, 10))
    out = str(media.render({"logo": {"src": "repeat 3 [repeat 2 [fd 10 rt 60]]", "show": "both"}}))
    assert "<svg" in out and "LOGO</span>" in out
    ET.fromstring(re.search(r"<svg.*?</svg>", out, re.S).group())
    assert "<svg" not in media.render({"logo": {"src": "fd 5", "show": "code"}}) and "<pre" not in media.render({"logo": {"src": "fd 5", "show": "drawing"}})


@pytest.mark.parametrize("bad", ["", "fd", "fd x", "uch 5", "repeat 3 fd 5", "repeat 3 [fd 5", "repeat 0 [fd 5]", "repeat 400 [fd 5]", "rt 90",
                                 "repeat 360 [repeat 360 [fd 1]]", "fd 99999", "fd 5 ] fd 5", 5, None])
def test_bad_logo(bad):
    assert media.check({"logo": {"src": bad}})


# ---------------- Tugmalar ----------------

def test_icons_are_valid_svg_and_unique(ctx):
    seen = set()
    for c in ui_icons.codes():
        svg = str(ui_icons.svg(c))
        ET.fromstring(svg)
        assert ui_icons.valid(c) and ui_icons.name(c) and ui_icons.purpose(c)
    for key, (progs, name, _purpose, body) in ui_icons.ICONS.items():
        assert body not in seen and set(progs.split()) <= set(ui_icons.PROGRAMS), key
        seen.add(body)
    assert len({v[1] for v in ui_icons.ICONS.values()}) == len(ui_icons.ICONS)
    for bad in ("word", "word.", "word.pencil", "x.bold", "", None, 5, "word.bold.x"):
        assert not ui_icons.valid(bad)


def test_icon_name_is_not_revealed_in_question(ctx):
    out = str(media.render({"ui": ["word.bold", "word.italic"]})) + str(media.option("word.bold", "ui"))
    assert "Qalin" not in out and "bold" not in out and "Word" in out
    assert media.option_text("word.bold", "ui") == "Qalin"


# ---------------- Tekshiruv ----------------

@pytest.mark.parametrize("data", [
    {"code": 5}, {"code": "x" * 5001}, {"lang": "klingon"}, {"show": "hammasi"}, {"code": "x", "lang": "python", "show": "both"}, {"html": 1},
    {"sheet": []}, {"sheet": {"rows": []}}, {"sheet": {"rows": [[1]]}}, {"sheet": {"rows": [["1"] * 13]}}, {"sheet": {"rows": [["1"]], "active": "Z9"}},
    {"sheet": {"rows": [["1"]], "formula": 5}}, {"logo": "fd 5"}, {"logo": {"src": "fd 5", "show": "x"}}, {"ui": []}, {"ui": ["word.zz"]}, {"ui": "word.bold"},
    {"option_view": "x", "options": ["a", "b"]}, {"option_view": "ui", "options": ["word.bold", "b"]}, {"option_view": "logo", "options": ["fd 5", "x"]}])
def test_bad_formats_are_rejected(data):
    q = {"type": "single", "difficulty": "easy", "text": "t", "data": {"options": ["a", "b"], **data}, "answer": {"keys": [0]}}
    assert check_question(q)


def test_option_view_only_for_choice_questions():
    assert media.check({"option_view": "code"}, "open") and media.check({"option_view": "code", "options": ["a"]}, "multiple") == []


# ---------------- Shablonlar: javobni mustaqil tekshirish ----------------

NEW = [n for n in TEMPLATES if n.startswith(("js_", "html_", "css_", "logo_", "scratch_", "word_", "excel_", "ppt_", "paint_")) or n in ("xl_ref", "xl_abs", "xl_if")]


def _each(name, n=60):
    t = TEMPLATES[name]
    for level in t.levels:
        for seed in range(n):
            try:
                q = t.fn(random.Random(seed), level)
            except ValueError:
                continue
            yield q, (q.data["options"][q.answer["keys"][0]] if t.type == "single" else q.answer.get("value")), level


@pytest.mark.parametrize("name", NEW)
def test_new_templates_pass_media_check(ctx, name):
    for q, _right, _level in _each(name, 25):
        assert media.check(q.data, TEMPLATES[name].type) == []
        out = str(media.render(q.data))
        assert all(str(media.option(o, q.data.get("option_view"))) for o in q.data.get("options", [])) and "<script" not in out


def test_scratch_templates_match_interpreter():
    def run(items, st):
        for b in items:
            t = b["text"]
            nums = [int(x) for x in re.findall(r"\[(-?\d+)\]", t)]
            if "marta takrorla" in t:
                for _ in range(nums[0]):
                    run(b["items"], st)
            elif "ga o‘rnat" in t:
                st["x"] = nums[0]
            elif "ga o‘zgartir" in t:
                st["x"] += nums[0]
            elif "qadam yur" in t:
                st["steps"] += nums[0]
            elif t.startswith("agar"):
                a, op, k = re.search(r"<(x) ([<>]) (\d+)>", t).groups()
                run(b["items"] if OPS[op](st[a], int(k)) else b["else"], st)
            elif t == "(x) de":
                st["said"] = str(st["x"])
            elif t.endswith(" de"):
                st["said"] = re.search(r"\[(.+)\]", t).group(1)
        return st
    for name, key in (("scratch_sum", "said"), ("scratch_if", "said"), ("scratch_steps", "steps")):
        for q, right, _level in _each(name):
            assert str(run(media._scratch_tree(q.data["scratch"]), {"x": 0, "steps": 0, "said": ""})[key]) == right, q


def test_logo_templates_match_turtle():
    from app.services.question_templates import POLYGONS
    for q, right, _level in _each("logo_figure"):
        path = media._logo_run(q.data["logo"]["src"])
        assert POLYGONS[len(path) - 1] == right and math.hypot(*path[-1][:2]) < 1e-6            # yopiq shakl, tomonlar soni
    for q, right, _level in _each("logo_pick"):
        assert f"«{right}»" in q.text
    for q, right, _level in _each("logo_perimeter"):
        path = media._logo_run(q.data["logo"]["src"])
        assert str(round(sum(math.dist(a[:2], b[:2]) for a, b in zip(path, path[1:])))) == right


def test_excel_templates_match_formula():
    def calc(f, row):
        cells = dict(zip("ABC", map(int, row)))
        f = f[1:].replace("^", "**").replace("SUM(A1:C1)", str(sum(cells.values()))).replace("MAX(A1:C1)", str(max(cells.values()))).replace(
            "MIN(A1:C1)", str(min(cells.values())))
        return eval(re.sub(r"([ABC])1", lambda m: str(cells[m.group(1)]), f))
    for q, right, _level in _each("xl_ref"):
        s = q.data["sheet"]
        assert str(calc(s["formula"], s["rows"][0][:3])) == right
    for q, right, _level in _each("xl_if"):
        s = q.data["sheet"]
        a = int(s["rows"][0][0])
        op, k, yes, no = re.fullmatch(r"=IF\(A1(>=|<=|>|<)(\d+);(.+);(.+)\)", s["formula"]).groups()
        branch = yes if OPS[op](a, int(k)) else no
        assert right == (branch.strip('"') if '"' in branch else str(eval(branch.replace("A1", str(a)))))
    for q, right, _level in _each("xl_abs"):
        frm, src, to = re.match(r"[CD](\d) katakdagi (=\S+) formulasi [CD](\d) katakka", q.text).groups()
        d = int(to) - int(frm)
        moved = re.sub(r"(\$?[AB])(\$?)(\d+)", lambda m: m.group(1) + m.group(2) + (m.group(3) if m.group(2) else str(int(m.group(3)) + d)), src)
        assert moved == right, q


def test_icon_templates_answer_matches_icon():
    for prog in ui_icons.PROGRAMS:
        for q, right, _level in _each(prog + "_icon"):
            (code,) = q.data["ui"]
            assert right in (ui_icons.name(code), ui_icons.purpose(code)) and q.data["options"].count(right) == 1
        for q, right, level in _each(prog + "_pick"):
            assert (ui_icons.name(right) if level == "easy" else ui_icons.purpose(right)[1:]) in q.text
            assert len({ui_icons.name(o) for o in q.data["options"]}) == 4


# ---------------- Sahifalar ----------------

def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


@pytest.mark.parametrize("title,mark", [("CSS xossalari", "web-preview"), ("Scratch bloklari", 'class="scratch"'), ("LOGO buyruqlari", "logo-draw"),
                                        ("Word oynasi", "ui-btn"), ("Excel oynasi", "xl-grid"), ("JavaScript asoslari", "JavaScript</span>")])
def test_formats_in_player_result_and_solution(app, client, title, mark):
    with app.app_context():
        sid = _sub(title)
    html = client.get(f"/test/savol?turi=dars&dars={sid}", follow_redirects=True).get_data(as_text=True)
    assert mark in html and html.count('data-q="') == 3 and "&lt;div class=" not in html
    with app.app_context():
        a = at.finish(db.session.scalar(select(TestAttempt)))
        u, n = a.client_uuid, a.total
    assert mark in client.get(f"/test/urinish/{u}/natija").get_data(as_text=True)
    asks = [client.get(f"/app/tutor/yechim/{u}:{p}", headers=JSON).json for p in range(n)]
    assert any(mark in x["ask"] or mark in x["html"] for x in asks)


def test_exam_gets_rendered_media_without_names(app, client):
    with app.app_context():
        from app.services import settings as conf
        conf.save({"exam_n": 100}, demo_user("admin").id)
        db.session.commit()
    html = client.get("/test/sinov", follow_redirects=True).get_data(as_text=True)
    assert "web-preview" in html and "xl-grid" in html and "ui-btn" in html and "word.align" not in html and '"right"' not in html


def test_editor_saves_and_previews_formats(app, as_role):
    with app.app_context():
        sid = _sub("Scratch bloklari")
        sub = db.session.get(Subtopic, sid)
        base = {"topic": sub.topic.section_id, "lesson": sub.topic_id, "subtopic": sid, "level": "Oson", "kind": "yopiq", "time": "60", "opt": ["a", "b"], "right": "0"}
    c = as_role("expert")
    cases = [
        ({"format": "kod", "code": "\r\n  let x = 1;\r\n", "lang": "javascript", "show": "both"}, {"code": "  let x = 1;", "lang": "javascript"}),
        ({"format": "kod", "code": "p{}", "lang": "css", "show": "both", "html": "<p>a</p>"}, {"code": "p{}", "lang": "css", "show": "both", "html": "<p>a</p>"}),
        ({"format": "excel", "sheet": "1 | 2\r\n\r\n3 | ?", "sheet_active": "b2", "sheet_formula": "=A1"}, {"sheet": {"rows": [["1", "2"], ["3", "?"]], "active": "B2", "formula": "=A1"}}),
        ({"format": "scratch", "scratch": "boshqaruv: [2] marta\r\n  harakat: [1] qadam"}, {"scratch": "boshqaruv: [2] marta\n  harakat: [1] qadam"}),
        ({"format": "logo", "logo": " repeat 4\n[fd 5 rt 90] ", "logo_show": "drawing"}, {"logo": {"src": "repeat 4 [fd 5 rt 90]", "show": "drawing"}}),
        ({"format": "tugma", "ui": ["word.bold", "word.copy"]}, {"ui": ["word.bold", "word.copy"]}),
        ({"format": "matn", "view": "ui", "opt": ["word.bold", "word.copy"]}, {"option_view": "ui"}),
    ]
    made = []
    for n, (form, want) in enumerate(cases):
        r = c.post("/ekspert/savol", data={**base, "text": f"7d-{n}", **form}, headers=JSON)
        assert r.status_code == 200, r.json
        with app.app_context():
            q = db.session.scalar(select(Question).where(Question.text == f"7d-{n}"))
            made.append(q.id)
            assert {k: v for k, v in q.data.items() if k not in ("format", "options")} == want
        html = c.get(f"/ekspert/savol?id={made[-1]}").get_data(as_text=True)                   # muharrirga qaytganda saqlanadi
        assert f"fmt: &#34;{form['format']}&#34;" in html
        pv = c.post("/ekspert/savol/korinish", data={**base, **form}).json
        assert pv["ok"] and len(pv["options"]) == 2 and (pv["html"] or form["format"] == "matn")
    for bad in ({"format": "kod"}, {"format": "excel"}, {"format": "scratch", "scratch": "xato"}, {"format": "logo", "logo": "uch"}, {"format": "tugma"},
                {"format": "kod", "code": "x", "lang": "zz"}, {"format": "matn", "view": "ui"}, {"format": "matn", "view": "zz"}):
        assert c.post("/ekspert/savol", data={**base, "text": "7d-x", **bad}, headers=JSON).status_code == 422, bad
    assert not c.post("/ekspert/savol/korinish", data={"format": "logo", "logo": "uch"}).json["ok"]
    assert as_role("user").post("/ekspert/savol/korinish", data={}).status_code == 403
    with app.app_context():
        rows = xlsx.read_rows(qb.export_excel(qb.Filters(q="7d-")))
        assert [x[15] for x in rows[1:]] == ["kod", "kod", "Excel oynasi", "Scratch", "LOGO", "tugmalar", "variant ko‘rinishi"]
        for qid in made:
            db.session.delete(db.session.get(Question, qid))
        db.session.commit()


def test_every_subtopic_lesson_test_has_partial_question(app):
    """Yangi bo'limdagi har bir darsda 3 savol, kamida bittasi qisman balli (B1) — va 5 marta ketma-ket takrorsiz."""
    with app.app_context():
        uid, seen = demo_user("user").id, set()
        for title in ("HTML teglari", "CSS xossalari", "JavaScript asoslari", "Scratch bloklari", "LOGO buyruqlari", "Word oynasi",
                      "PowerPoint oynasi", "Excel oynasi", "Paint oynasi"):
            for _ in range(3):
                a, _f = tb.get_or_start(uid, "lesson", subtopic_id=_sub(title))
                types = [s[0]["type"] for s in at._snapshots(a).values()]
                ids = {i.question_id for i in a.items}
                assert len(ids) == 3 and not ids & seen and any(t in at.PARTIAL_TYPES for t in types), (title, types)
                seen |= ids
                at.finish(a)
