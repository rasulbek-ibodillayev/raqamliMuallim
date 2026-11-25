"""7c: takrorlanmaslik (bitmap, shablon generator), javoblarni ixchamlash va 12 oylik arxiv."""
import contextlib
import io
import random
from collections import Counter
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app import models as m
from app.cli import demo_user
from app.extensions import db
from app.models import AttemptItem, ErrorItem, Question, QuestionVersion, Subtopic, TestAttempt
from app.services import archive, catalog, generator, objections, seen
from app.services import attempts as at
from app.services import test_builder as tb
from app.services.content_import import ContentError, check_question, load
from app.services.question_templates import TEMPLATES


def _uid():
    return demo_user("user").id


def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


def _right(snap):
    t, a = snap["type"], snap["answer"]
    return {"single": lambda: a["keys"][0], "multiple": lambda: a["keys"], "matching": lambda: a["pairs"],
            "open": lambda: a["value"]}[t]()


def _run(kind, good=True, **kw):
    a, fresh = tb.get_or_start(_uid(), kind, **kw)
    assert fresh
    while a.status == "in_progress":
        snaps = at._snapshots(a)
        at.save_answers(a, [{"pos": p, "v": _right(snaps[p][0]) if good else None, "at": 7, "t": 1500}
                            for p in at.active_positions(a)])
        at.finish(a, a.stage)
    return a


def _bits(uid):
    return db.session.scalar(select(m.UserSeen.bits).where(m.UserSeen.user_id == uid))


def _load(subs):
    load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [{"title": "M", "subtopics": [
        {"title": t, **u} for t, u in subs.items()]}]}]}, status="approved")


def _q(text, difficulty="easy"):
    return {"type": "single", "difficulty": difficulty, "text": text, "data": {"options": ["a", "b"]}, "answer": {"keys": [0]}}


# ---------------- Bitmap ----------------

def test_bitmap_marks_and_grows(app):
    with app.app_context():
        uid = _uid()
        for ids in ([1], [8, 9], [2047], [3, 1]):
            seen.mark(uid, ids)
        db.session.commit()
        bits = _bits(uid)
        assert len(bits) == 256 and {n for n in range(2048) if bits[n >> 3] >> (n & 7) & 1} == {1, 3, 8, 9, 2047}
        # PostgreSQL ham shu tartibda o'qiydi
        assert db.session.scalar(select(func.get_bit(m.UserSeen.bits, 2047))) == 1
        seen.mark(uid, [])
        assert _bits(uid) == bits


def test_is_new_is_per_user_and_handles_ids_beyond_bitmap(app):
    with app.app_context():
        uid, other = _uid(), demo_user("expert").id
        ids = sorted(db.session.scalars(select(Question.id)))
        seen.mark(uid, ids[:1])
        fresh = lambda u: set(db.session.scalars(select(Question.id).where(seen.is_new(u))))      # noqa: E731
        assert fresh(uid) == set(ids[1:]) and fresh(other) == set(ids)
        assert seen.ever_given(ids[0]) and not seen.ever_given(ids[-1])


@pytest.mark.usefixtures("fresh_content")
def test_later_stage_questions_are_reserved(app):
    """Bosqichli testning hali ko'rsatilmagan savoli boshqa testga tushmaydi (aks holda ikki marta berilardi)."""
    with app.app_context():
        _load({"D": {"questions": [_q("oson"), _q("orta", "medium"), _q("qiyin", "hard")]}})
        a, _ = tb.get_or_start(_uid(), "optional", n=10)
        assert a.total == 3 and a.stage == 1
        with pytest.raises(tb.Unavailable):
            tb.build(_uid(), "daily")
        at.cancel(a)                                                # ko'rsatilmaganlari bankka qaytadi
        assert len(tb.build(_uid(), "daily").parts[0]) == 2


@pytest.mark.usefixtures("fresh_content")
def test_no_new_questions_explains_and_mentions_nothing_repeated(app, as_role):
    with app.app_context():
        _load({"D": {"questions": [_q("bitta")]}})
        _run("lesson", subtopic_id=_sub("D"))
        sid = _sub("D")
    html = as_role("user").get(f"/test/savol?turi=dars&dars={sid}", follow_redirects=True).get_data(as_text=True)
    assert "yangi savollar qolmagan" in html
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(TestAttempt)) == 1


# ---------------- Shablonlar ----------------

def _output(code):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(code, {})
    return out.getvalue().strip()


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_template_is_valid_and_key_is_correct(name):
    t = TEMPLATES[name]
    for level in t.levels:
        keys: dict[str, tuple] = {}
        for seed in range(150):
            try:
                q = t.fn(random.Random(seed), level)
            except ValueError:
                continue
            assert check_question({"type": t.type, "difficulty": level, "text": q.text, "data": q.data, "answer": q.answer}) == []
            assert len(f"{name}:{q.key}") <= Question.sig.type.length
            opts, code = q.data.get("options", []), q.data.get("code")
            assert len(set(opts)) == len(opts)
            if t.type == "single":
                assert len(opts) == 4
            if t.type == "multiple":
                assert 2 <= len(q.answer["keys"]) < len(opts)
            if t.type == "matching":
                assert len(set(q.data["right"])) == len(q.data["right"]) >= 3
            # Bir xil kalit — bir xil savol
            same = (q.text, code, *(str(q.data.get(k)) for k in ("table", "sheet", "scratch", "logo", "ui")))
            assert keys.setdefault(q.key, same) == same
            if not code or q.data.get("lang", "python") != "python":
                continue
            # Kodli savol: javob kodni ishga tushirib tekshiriladi
            if t.type == "single":
                assert _output(code) == opts[q.answer["keys"][0]]
            elif t.type == "open":
                assert _output(code) == q.answer["value"]
            elif t.type == "matching":
                for left, r in zip(q.data["left"], q.answer["pairs"]):
                    src = f"{code}\nprint({left})" if left.startswith("f(") else f"{left}\n{code}"
                    assert _output(src) == q.data["right"][r]
        assert len(keys) >= 6, (name, level, len(keys))


@pytest.mark.parametrize("name,expected", [
    ("bin_dec_open", lambda q: str(int(q.text.split("₂")[0], 2))),
    ("hex_dec_open", lambda q: str(int(q.text.split("₁₆")[0], 16))),
])
def test_number_templates_match_text(name, expected):
    for seed in range(100):
        q = TEMPLATES[name].fn(random.Random(seed), "hard")
        assert q.answer["value"] == expected(q)


def test_python_true_template_matches_eval():
    for level in ("easy", "medium", "hard"):
        for seed in range(100):
            q = TEMPLATES["py_true"].fn(random.Random(seed), level)
            x = int(q.text.split("x = ")[1].split(" ")[0])
            assert q.answer["keys"] == [i for i, o in enumerate(q.data["options"]) if eval(o, {"x": x})]


# ---------------- Generator ----------------

@pytest.mark.usefixtures("fresh_content")
def test_generator_fills_when_bank_is_exhausted(app):
    with app.app_context():
        _load({"D": {"generators": ["bin_dec", "bin_match"], "questions": [_q("a"), _q("b")]}})
        uid, sid = _uid(), _sub("D")
        given = Counter()
        for _ in range(8):
            a = _run("lesson", subtopic_id=sid)
            types = [s[0]["type"] for s in at._snapshots(a).values()]
            assert a.total == 3 and "matching" in types            # B1: kamida bittasi qisman balli
            given.update(i.question_id for i in a.items)
        assert max(given.values()) == 1 and len(given) == 24
        made = db.session.scalars(select(Question).where(Question.source == "template")).all()
        assert len(made) == 22 and all(q.status == "approved" and q.sig and q.version == 1 for q in made)
        assert len({q.sig for q in made}) == 22
        assert db.session.scalar(select(func.count()).select_from(QuestionVersion)) == 24

        # Boshqa foydalanuvchiga avval shu tuzilganlar beriladi: yangisi tuzilmaydi
        other = demo_user("expert").id
        for _ in range(4):
            spec = tb.build(other, "topic", topic_id=db.session.scalar(select(Subtopic.topic_id)))
            at.create(other, spec)
        assert db.session.scalar(select(func.count()).select_from(Question)) == 24


@pytest.mark.usefixtures("fresh_content")
def test_generator_alternates_templates(app):
    with app.app_context():
        _load({"D": {"generators": ["bin_dec", "dec_bin", "bin_add"], "questions": [_q("a")]}})
        made = generator.make(_sub("D"), 6, "hard")
        assert Counter(q.sig.split(":")[0] for q in made) == {"bin_dec": 2, "dec_bin": 2, "bin_add": 2}


@pytest.mark.usefixtures("fresh_content")
def test_generator_respects_level_type_and_finite_space(app):
    with app.app_context():
        _load({"D": {"generators": ["de_morgan", "bin_dec", "bin_match"], "questions": [_q("a")]}})
        sid = _sub("D")
        made = generator.make(sid, 5, "hard", ("single",))
        assert len(made) == 5 and {(q.type, q.difficulty) for q in made} == {("single", "hard")}
        assert generator.make(sid, 3, types=("open",)) == []
        db.session.get(Subtopic, sid).generators = ["de_morgan"]
        db.session.flush()
        got = [q for _ in range(12) for q in generator.make(sid, 6, "easy")]
        assert 0 < len(got) <= 8 and len({q.sig for q in got}) == len(got)      # shablon tugadi — takror tuzilmaydi
        assert generator.make(sid, 6, "hard") == []


@pytest.mark.usefixtures("fresh_content")
def test_archived_generated_question_is_not_remade(app):
    with app.app_context():
        _load({"D": {"generators": ["de_morgan"], "questions": [_q("a")]}})
        sid = _sub("D")
        for _ in range(30):
            generator.make(sid, 8, "easy")
        sigs = set(db.session.scalars(select(Question.sig).where(Question.sig.is_not(None))))
        assert len(sigs) == 8
        for q in db.session.scalars(select(Question).where(Question.sig.is_not(None))):
            q.status = "archived"
        db.session.flush()
        assert generator.make(sid, 8, "easy") == []


@pytest.mark.usefixtures("fresh_content")
def test_content_generators_are_validated_and_kept(app):
    with app.app_context():
        for bad in (["yoq_shablon"], "bin_dec", [1]):
            with pytest.raises(ContentError):
                _load({"D": {"generators": bad, "questions": [_q("a")]}})
        _load({"D": {"generators": ["bin_dec"], "questions": [_q("a")]}})
        _load({"D": {"questions": [_q("b")]}})                       # ko'rsatilmagan bo'lsa o'zgarmaydi
        assert db.session.scalar(select(Subtopic.generators)) == ["bin_dec"]


def test_exam_is_full_with_generators(app):
    with app.app_context():
        seen_ids = set()
        for _ in range(2):
            a = at.create(_uid(), tb.build(_uid(), "exam"))
            ids = {i.question_id for i in a.items}
            assert a.total == 35 and not ids & seen_ids
            seen_ids |= ids
            at.finish(a)
        assert set(db.session.scalars(select(Question.type).where(Question.id.in_(seen_ids)))) == {"single"}


# ---------------- Xatolar (savol qaytmaydi) ----------------

@pytest.mark.usefixtures("fresh_content")
def test_error_is_resolved_by_other_question_of_same_subtopic(app):
    with app.app_context():
        _load({"A": {"questions": [_q(f"a{i}") for i in range(9)]}, "B": {"questions": [_q(f"b{i}") for i in range(9)]}})
        opened = lambda t: db.session.scalar(select(func.count()).select_from(ErrorItem).where(      # noqa: E731
            ErrorItem.subtopic_id == _sub(t)))
        _run("lesson", good=False, subtopic_id=_sub("A"))
        _run("lesson", good=False, subtopic_id=_sub("A"))
        _run("lesson", good=False, subtopic_id=_sub("B"))
        assert (opened("A"), opened("B")) == (6, 3)
        oldest = db.session.scalars(select(ErrorItem.question_id).order_by(ErrorItem.last_wrong_at, ErrorItem.question_id).limit(3)).all()
        _run("lesson", subtopic_id=_sub("A"))                        # 3 ta to'g'ri javob — 3 ta eng eski xato
        assert (opened("A"), opened("B")) == (3, 3)
        assert not set(oldest) & set(db.session.scalars(select(ErrorItem.question_id)))


# ---------------- Javobni ixchamlash va arxiv ----------------

def test_answer_keeps_only_value_after_finish(app):
    with app.app_context():
        a, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=_sub("if operatori"))
        at.save_answers(a, [{"pos": 0, "v": 0, "at": 5}, {"pos": 1, "v": None, "at": 6}])
        assert a.items[0].answer == {"v": 0, "at": 5}
        at.finish(a)
        assert a.items[0].answer == {"v": 0}
        null_rows = select(func.count()).select_from(AttemptItem).where(AttemptItem.answer.is_(None))
        assert db.session.scalar(null_rows) == 2                     # SQL NULL (JSON null emas)
        assert "repeated" not in a.settings_snapshot


def test_old_attempts_are_compressed_and_still_readable(app, as_role):
    with app.app_context():
        uid, sid = _uid(), _sub("if operatori")
        tid = db.session.get(Subtopic, sid).topic_id
        old, mid = _run("lesson", subtopic_id=sid), _run("diagnostic", good=False)
        fresh = _run("lesson", good=False, subtopic_id=sid)
        before = {a.id: (at.review(a), at.by_subtopic(a), catalog.attempt_by_section(a)) for a in (old, mid, fresh)}
        scores = catalog.subtopic_scores(uid, tid)
        for a in (old, mid):
            a.finished_at -= timedelta(days=8)
        db.session.commit()
        left = fresh.total

        assert archive.compress_old() == 2 and archive.compress_old() == 0
        assert db.session.scalar(select(func.count()).select_from(AttemptItem)) == left
        assert old.items == [] and len(old.items_archive) < 30 and fresh.items_archive is None
        for a in (old, mid, fresh):
            assert (at.review(a), at.by_subtopic(a), catalog.attempt_by_section(a)) == before[a.id]
        assert catalog.subtopic_scores(uid, tid) == scores
        assert archive.rows(old)[0].time_ms == 2000                  # 1500 ms: arxivda soniyagacha yaxlitlanadi
        given = archive.rows(old)[0].question_id
        assert seen.ever_given(given)                                # arxivlangach ham savol «berilgan»
        assert given not in {p.question_id for p in at.pick_from_bank(uid, {sid: 99})}
        u, kind = old.client_uuid, old.kind
    c = as_role("user")
    html = c.get(f"/test/urinish/{u}/natija").get_data(as_text=True)
    assert "100%" in html and "E’tiroz" in html
    assert c.post(f"/api/urinish/{u}/yakunlash", json={"kind": kind}).json["answered"] == 3
    assert c.get("/app/natijalar").status_code == 200
    r = c.post("/app/etiroz", data={"question": f"{u}:0", "reason": "unclear", "note": "x"},
               headers={"Accept": "application/json"})
    assert r.status_code == 200 and r.json["ok"]
    with app.app_context():
        a = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == u))
        assert objections.sent_positions(a) == {0}


def test_archive_format_round_trip():
    from types import SimpleNamespace as N
    answers = [None, 0, 25, 99, [], [0, None, 3], "qirq besh “x”", "", list(range(300)), 100, -1, 1.5, True, {"a": 1}]
    items = [N(position=n, question_id=q, question_version=v, time_ms=ms, score=sc, answer=None if a is None else {"v": a})
             for n, (a, q, v, ms, sc) in enumerate(zip(answers, [1, 127, 128, 20000, 2**31 - 1] * 3, [1, 2, 300] * 5,
                                                       [None, 0, 999, 61400, 86_400_000] * 3, [None, 0, 100] * 5))]
    back = archive.unpack(archive.pack(items))
    assert [(i.position, i.question_id, i.question_version, i.score, (i.answer or {}).get("v")) for i in back] ==         [(i.position, i.question_id, i.question_version, i.score, (i.answer or {}).get("v")) for i in items]
    assert [i.time_ms for i in back][:5] == [None, 0, 1000, 61000, 86_400_000]          # soniyagacha yaxlitlanadi
    assert archive.unpack(b"") == []
    with pytest.raises(ValueError):
        archive.pack([N(position=1, question_id=1, question_version=1, time_ms=None, score=0, answer=None)])


def test_next_test_compresses_users_old_attempts(app):
    with app.app_context():
        sid = _sub("if operatori")
        old = _run("lesson", subtopic_id=sid)
        old.finished_at -= timedelta(days=8)
        db.session.commit()
        new, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=sid)
        assert old.items_archive is not None and old.items == [] and len(new.items) == 3
        # Arxivdagi savolni qidirish sharti
        qid = archive.rows(old)[0].question_id
        found = select(TestAttempt.id).where(archive.may_have(qid))
        assert list(db.session.scalars(found)) == [old.id]
        assert list(db.session.scalars(select(TestAttempt.id).where(archive.may_have(2_000_000_000)))) == []


def test_compress_command_and_unfinished_attempts(app):
    with app.app_context():
        a, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=_sub("if operatori"))
        a.started_at -= timedelta(days=800)                          # yakunlanmagani siqilmaydi
        db.session.commit()
    out = app.test_cli_runner().invoke(args=["eski-testlarni-siqish"]).output
    assert "Siqilgan urinishlar: 0" in out
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(AttemptItem)) == 3
