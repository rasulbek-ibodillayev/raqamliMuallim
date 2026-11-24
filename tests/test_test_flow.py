"""Testlar boshidan oxirigacha: boshlash, pleyer, bosqichlar, baholash, natija, progress, e'tiroz, bekor qilish."""
import json
import re
import uuid

import pytest
from sqlalchemy import func, select

from app import models as m
from app.cli import demo_user
from app.extensions import db
from app.models import ErrorItem, Objection, Question, Subtopic, TestAttempt, Topic, UserTopicProgress
from app.services import attempts as at
from app.services import catalog
from app.services import test_builder as tb
from app.services.content_import import load
from app.views.test import TYPE_SLUGS
from tests.conftest import JSON


def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


def _topic(title="Python: shart operatorlari"):
    return db.session.scalar(select(Topic.id).where(Topic.title == title))


def _uid():
    return demo_user("user").id


def _right(snap):
    t, a = snap["type"], snap["answer"]
    return {"single": lambda: a["keys"][0], "multiple": lambda: a["keys"], "matching": lambda: a["pairs"],
            "open": lambda: a["value"]}[t]()


def _given(a) -> set[int]:
    """Urinishdagi bitmapda belgilangan (foydalanuvchiga ko'rsatilgan) savollar tartibi."""
    bits = db.session.scalar(select(m.UserSeen.bits).where(m.UserSeen.user_id == a.user_id))
    return {i.position for i in a.items if i.question_id < len(bits) * 8 and bits[i.question_id >> 3] >> (i.question_id & 7) & 1}


def _answer(a, good=lambda snap: True):
    """Joriy bosqich savollariga javob: good(snap) bo'lsa — to'g'ri, aks holda javobsiz."""
    snaps = at._snapshots(a)
    at.save_answers(a, [{"pos": p, "v": _right(snaps[p][0]) if good(snaps[p][0]) else None, "at": 1}
                        for p in at.active_positions(a)])


def _master(titles=None):
    """Mavzularni o'zlashtirilgan deb belgilaydi."""
    uid = _uid()
    for t in db.session.scalars(select(Topic)):
        if titles is None or t.title in titles:
            db.session.add(UserTopicProgress(user_id=uid, topic_id=t.id, status="done", best_pct=80))
    db.session.commit()


# ---------------- Boshlash va pleyer ----------------

def test_start_creates_one_attempt_and_resumes(app, client):
    with app.app_context():
        sid = _sub("if operatori")
    r1 = client.get(f"/test/savol?turi=dars&dars={sid}")
    r2 = client.get(f"/test/savol?turi=dars&dars={sid}")
    assert r1.status_code == 302 and r1.location == r2.location
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(TestAttempt)) == 1


def test_player_shows_all_questions_without_answers(app, client):
    with app.app_context():
        sid = _sub("if operatori")
    html = client.get(f"/test/savol?turi=dars&dars={sid}", follow_redirects=True).get_data(as_text=True)
    assert html.count('data-q="') == 3 and "Dars testi: if operatori" in html
    with app.app_context():
        for q in db.session.scalars(select(Question).where(Question.subtopic_id == sid)):
            if q.explanation:
                assert q.explanation not in html                # izoh va kalit test davomida chiqmaydi
    assert '"keys"' not in html and "&#34;keys&#34;" not in html
    assert html.count("objection-sent.window") == 3 and "variantlar orasida yo‘q" in html


def test_exam_page_has_no_answer_key(app, client):
    html = client.get("/test/sinov", follow_redirects=True).get_data(as_text=True)
    qs = json.loads(re.search(r"window\.RM_EXAM = (\[.*?\]);\n", html).group(1))
    assert qs and all("right" not in q and "answer" not in q and q["options"] for q in qs)
    with app.app_context():
        a = db.session.scalar(select(TestAttempt))
        assert a.kind == "exam" and a.settings_snapshot["seconds"] == 7200
        types = set(db.session.scalars(select(Question.type).where(Question.id.in_([i.question_id for i in a.items]))))
        assert types == {"single"}


@pytest.mark.parametrize("slug", sorted(TYPE_SLUGS))
def test_every_kind_starts_or_explains(app, client, slug):
    """Har bir tur: yo test ochiladi, yo «Testlar»da sabab ko'rsatiladi (namunaviy foydalanuvchida progress yo'q)."""
    r = client.get(f"/test/savol?turi={slug}", follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    if slug in ("dars", "mavzu", "kunlik", "ixtiyoriy", "diagnostika"):
        assert 'data-q="0"' in html
    else:
        assert "data-flash" in html and 'data-q="0"' not in html


@pytest.mark.parametrize("slug", ["diagnostika", "oraliq", "oylik", "yakuniy", "ixtiyoriy"])
def test_staged_kinds_open_when_topics_mastered(app, client, slug):
    with app.app_context():
        _master()
    html = client.get(f"/test/savol?turi={slug}", follow_redirects=True).get_data(as_text=True)
    assert "1-bosqich · Oson" in html


def test_weekly_only_on_sunday(app, client, monkeypatch):
    from app.views import test as vt
    with app.app_context():
        _master()
    monkeypatch.setattr(vt, "weekly_open", lambda: False)
    assert "yakshanba" in client.get("/test/savol?turi=haftalik", follow_redirects=True).get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(TestAttempt)) == 0
    monkeypatch.setattr(vt, "weekly_open", lambda: True)
    assert 'data-q="0"' in client.get("/test/savol?turi=haftalik", follow_redirects=True).get_data(as_text=True)


def test_mandatory_test_blocks_other_mandatory(app, client):
    with app.app_context():
        sid = _sub("if operatori")
    client.get(f"/test/savol?turi=dars&dars={sid}")
    html = client.get("/test/savol?turi=kunlik", follow_redirects=True).get_data(as_text=True)
    assert "Avval boshlangan majburiy testni yakunlang" in html and "Majburiy test yakunlanmagan" in html
    # Ixtiyoriy test esa boshlanadi
    assert 'data-q="0"' in client.get("/test/savol?turi=ixtiyoriy", follow_redirects=True).get_data(as_text=True)


def test_optional_uses_only_selected_topics(app, client):
    with app.app_context():
        tid = _topic("Sanoq sistemalari")
    client.get(f"/test/savol?turi=ixtiyoriy&soni=10&mavzu={tid}")
    with app.app_context():
        a = db.session.scalar(select(TestAttempt))
        tops = set(db.session.scalars(select(Subtopic.topic_id).join(Question).where(
            Question.id.in_([i.question_id for i in a.items]))))
        assert tops == {tid}


# ---------------- Savollar tanlash ----------------

def test_allocate():
    assert tb.allocate(5, ["a", "b"], {"a": 10, "b": 1}) == {"a": 4, "b": 1}
    assert tb.allocate(3, ["a", "b", "c"], {"a": 9, "b": 9, "c": 9}) == {"a": 1, "b": 1, "c": 1}
    assert tb.allocate(9, ["a"], {"a": 2}) == {"a": 2}
    assert tb.allocate(4, [], {}) == {}


def _q(text, type_="single", **kw):
    base = {"single": ({"options": ["a", "b"]}, {"keys": [0]}), "multiple": ({"options": ["a", "b", "c"]}, {"keys": [0, 1]}),
            "matching": ({"left": ["a", "b"], "right": ["c", "d"]}, {"pairs": [0, 1]})}[type_]
    return {"type": type_, "difficulty": "easy", "text": text, "data": base[0], "answer": base[1], **kw}


def _load(topics):
    load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [
        {"title": t, "subtopics": [{"title": u, "questions": qs, "blocks": [{"kind": "text", "data": {"body": "x"}}]}
                                   for u, qs in subs.items()]} for t, subs in topics.items()]}]}, status="approved")


@pytest.mark.usefixtures("fresh_content")
def test_lesson_test_always_has_partial_credit_question(app):
    with app.app_context():
        _load({"M": {"D": [_q(f"s{i}") for i in range(20)] + [_q("ko'p", "multiple")]}})
        uid, sid = _uid(), _sub("D")
        for _ in range(6):                          # tasodifiy tanlov: har safar ko'p javobli savol bo'lishi shart
            spec = tb.build(uid, "lesson", subtopic_id=sid)
            assert len(spec.parts[0]) == 3 and len({p.question_id for p in spec.parts[0]}) == 3
            assert any(p.type == "multiple" for p in spec.parts[0])


@pytest.mark.usefixtures("fresh_content")
def test_topic_test_size_and_weak_lessons_first(app):
    with app.app_context():
        _load({"M": {"A": [_q(f"a{i}") for i in range(9)], "B": [_q(f"b{i}") for i in range(9)],
                     "C": [_q("c0")]}})
        uid, tid = _uid(), _topic("M")
        spec = tb.build(uid, "topic", topic_id=tid)
        assert len(spec.parts[0]) == 6                    # 2 × 3 dars; C da 1 ta savol bor — qolgani A va B dan
        bad = db.session.scalar(select(Question).where(Question.text == "b0"))
        db.session.add(ErrorItem(user_id=uid, subtopic_id=bad.subtopic_id, question_id=bad.id))
        db.session.commit()
        per = [p.subtopic_id for p in tb.build(uid, "topic", topic_id=tid).parts[0]]
        assert per.count(_sub("B")) == 3 and per.count(_sub("A")) == 2


@pytest.mark.usefixtures("fresh_content")
def test_daily_prefers_errors(app):
    with app.app_context():
        _load({"M": {"A": [_q(f"a{i}") for i in range(9)], "B": [_q(f"b{i}") for i in range(3)]}})
        uid = _uid()
        bad = db.session.scalar(select(Question).where(Question.text == "b0"))
        db.session.add(ErrorItem(user_id=uid, subtopic_id=bad.subtopic_id, question_id=bad.id))
        db.session.commit()
        per = [p.subtopic_id for p in tb.build(uid, "daily").parts[0]]
        assert len(per) == 5 and per.count(_sub("B")) == 3


# ---------------- Baholash va progress ----------------

def test_lesson_result_partial_credit_and_progress(app, client):
    with app.app_context():
        uid, sid, tid = _uid(), _sub("if operatori"), _topic()
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=sid)
        snaps = at._snapshots(a)
        # Ko'p javoblida 3 tadan 2 tasi belgilandi → 67; qolganlari to'g'ri → (100 + 100 + 67) / 3 = 89
        at.save_answers(a, [{"pos": p, "at": 1, "v": _right(s)[:2] if s["type"] == "multiple" else _right(s)}
                            for p, (s, *_x) in snaps.items()])
        at.finish(at.get(a.client_uuid, lock=True))
        assert (a.score_pct, a.decision, a.status) == (89, "warn", "submitted")
        assert catalog.lesson_scores(uid, tid) == {sid: 89}
        p = db.session.get(UserTopicProgress, (uid, tid))
        assert p.status == "learn" and p.lesson_pct == 100                  # bloklari bor yagona dars
        err = db.session.scalars(select(ErrorItem)).all()
        assert len(err) == 1 and err[0].subtopic_id == sid
        u, rid = a.client_uuid, a.id
    html = client.get(f"/test/urinish/{u}/natija").get_data(as_text=True)
    assert "89%" in html and "Keyingi darsga o‘tishingiz mumkin" in html and "Qisman: 67%" in html
    assert html.count("objection-sent.window") == 3 and "Mening javobim ham to‘g‘ri" in html
    assert client.get(f"/test/urinish/{u}").location.endswith("/natija")     # yakunlangan test qayta ochilmaydi
    assert "Dars testi: if operatori" in client.get("/app/natijalar").get_data(as_text=True)
    assert "Qisman: 67%" in client.get(f"/app/natijalar/{rid}").get_data(as_text=True)
    assert "89%" in client.get(f"/app/dars/{tid}").get_data(as_text=True)


def test_error_is_resolved_and_best_lesson_result_kept(app):
    with app.app_context():
        uid, sid, tid = _uid(), _sub("if operatori"), _topic()
        for good, pct in ((True, 100), (False, 0)):
            a, fresh = tb.get_or_start(uid, "lesson", subtopic_id=sid)
            assert fresh
            _answer(a, lambda s: good)
            at.finish(a)
            assert a.score_pct == pct
        assert catalog.lesson_scores(uid, tid) == {sid: 100}             # eng yaxshisi: ochilgan dars qayta yopilmaydi
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == 3
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=sid)
        _answer(a)
        at.finish(a)
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == 0


@pytest.mark.parametrize("good,button", [(False, "Darsni qayta o‘zlashtirish"), (True, "Keyingi dars")])
def test_lesson_result_button_and_link_from_lesson(app, client, good, button):
    """Tuzatish 24.11: < 70% — «Darsni qayta o‘zlashtirish»; topshirilgan dars testi kartasi natijani ochadi."""
    with app.app_context():
        sid, tid = _sub("if operatori"), _topic()
        a, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=sid)
        _answer(a, lambda s: good)
        at.finish(a)
        u, rid = a.client_uuid, a.id
    foot = client.get(f"/test/urinish/{u}/natija").get_data(as_text=True).split('class="focus-foot"', 1)[1]
    other = "Keyingi dars" if not good else "Darsni qayta o‘zlashtirish"
    assert button in foot and other not in foot and f"/app/dars/{tid}#k{sid}" in foot
    html = client.get(f"/app/dars/{tid}").get_data(as_text=True)
    assert f'href="/app/natijalar/{rid}"' in html and (('<a class="lesson-test is-done' in html) is good)


def test_failed_topic_result_button(app, client):
    with app.app_context():
        a, _ = tb.get_or_start(_uid(), "topic", topic_id=_topic())
        at.finish(a)
        u = a.client_uuid
    foot = client.get(f"/test/urinish/{u}/natija").get_data(as_text=True).split('class="focus-foot"', 1)[1]
    assert "Mavzuni qayta o‘zlashtirish" in foot and "Keyingi mavzu" not in foot


@pytest.mark.parametrize("pct,before,after", [(95, "learn", "solid"), (75, "learn", "done"), (50, "learn", "relearn"),
                                              (50, "done", "done"), (75, "solid", "solid"), (75, "relearn", "done")])
def test_topic_test_sets_status(app, pct, before, after):
    from app.services import progress
    with app.app_context():
        p = UserTopicProgress(user_id=_uid(), topic_id=_topic(), status=before, best_pct=None, fail_streak=0)
        progress._topic_result(p, pct)
        assert p.status == after and p.best_pct == pct


def test_optional_test_does_not_change_mastery(app):
    with app.app_context():
        uid = _uid()
        a, _ = tb.get_or_start(uid, "optional", n=30)
        while a.status == "in_progress":
            _answer(a, lambda s: False)
            at.finish(a, a.stage)
        assert a.score_pct == 0
        assert db.session.scalar(select(func.count()).select_from(UserTopicProgress)) == 0
        assert catalog.subtopic_scores(uid, _topic()) == {}
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) > 0      # xatolar ro'yxatiga tushadi


def test_objection_free_user_sees_empty_lists(client):
    assert "Hali e’tiroz yo‘q" in client.get("/app/etirozlarim").get_data(as_text=True)
    assert "Hali natijalar yo‘q" in client.get("/app/natijalar").get_data(as_text=True)


# ---------------- Bosqichlar ----------------

@pytest.fixture()
def staged(app, fresh_content):
    """Ikki mavzu, har birida oson/o'rta/qiyin bittadan savol; ixtiyoriy test: 6 savol, 3 bosqich."""
    with app.app_context():
        levels = ("easy", "medium", "hard")
        _load({"A": {"a": [_q(f"a-{d}", difficulty=d) for d in levels]},
               "B": {"b": [_q(f"b-{d}", difficulty=d) for d in levels]}})
        a, _ = tb.get_or_start(_uid(), "optional", n=10)
        yield a


def test_failed_topic_does_not_reach_next_stage(app, staged):
    a = staged
    assert a.total == 6 and a.stage == 1 and at.active_positions(a) == [0, 1]
    assert _given(a) == {0, 1}                                                             # faqat 1-bosqich berilgan
    _answer(a, lambda s: s["text"].startswith("a-"))                                       # B mavzu o'tmadi
    at.finish(a, 1)
    assert a.status == "in_progress" and a.stage == 2 and at.active_positions(a) == [2]
    at.finish(a, 1)                                                                        # oflayn navbat takrori
    assert a.stage == 2
    at.save_answers(a, [{"pos": 0, "v": 1, "at": 99}])                                     # tugagan bosqich javobi o'zgarmaydi
    assert a.items[0].answer["v"] == 0
    _answer(a)
    at.finish(a, 2)
    assert a.stage == 3 and at.active_positions(a) == [4]
    _answer(a)
    at.finish(a, 3)
    assert a.status == "submitted" and a.score_pct == 50                                   # 3 / 6: berilmaganlar 0 ball
    assert [r["q"] for r in at.review(a)] == ["a-easy", "b-easy", "a-medium", "a-hard"]
    assert _given(a) == {0, 1, 2, 4}                    # B mavzuning o'rta va qiyin savollari bankka qaytdi


def test_all_topics_failed_ends_test(app, staged):
    at.finish(staged, 1)
    assert staged.status == "submitted" and staged.score_pct == 0 and len(at.review(staged)) == 2


def test_stage_pages(app, staged, as_role):
    u = staged.client_uuid
    _answer(staged)
    c = as_role("user")
    api = f"/api/urinish/{u}/yakunlash"
    assert c.post(api, json={"kind": "optional"}).status_code == 422                       # bosqich ko'rsatilishi shart
    r = c.post(api, json={"kind": "optional", "stage": 1})
    assert r.json["result_url"] == f"/test/urinish/{u}/bosqich"
    html = c.get(r.json["result_url"]).get_data(as_text=True)
    assert "1-bosqich yakunlandi" in html and "100%" in html and "2-bosqichni boshlash" in html
    assert "2-bosqich · O‘rta" in c.get(f"/test/urinish/{u}").get_data(as_text=True)
    assert c.get(f"/test/urinish/{u}/natija").status_code == 302                           # hali yakunlanmagan


def _staged_lessons(n, kind="diagnostic"):
    """Bitta mavzu, n ta dars, har birida oson va o'rta bittadan savol; boshlangan bosqichli test."""
    _load({"M": {f"d{i}": [_q(f"e{i}"), _q(f"m{i}", difficulty="medium")] for i in range(n)}})
    return tb.get_or_start(_uid(), kind)[0]


@pytest.mark.usefixtures("fresh_content")
@pytest.mark.parametrize("n,wrong,passes,advised", [
    (10, 4, False, 0),      # 60% — o'tmaydi, alohida dars tavsiyasi yo'q (mavzu butunlay qayta o'zlashtiriladi)
    (10, 3, True, 3),       # 70% — o'tadi, xato qilingan 3 dars tavsiya etiladi
    (10, 2, True, 2),       # 80%
    (10, 1, True, 0),       # 90% — tavsiyasiz o'tadi
    (10, 0, True, 0),
])
def test_stage_pass_with_and_without_recommendation(app, as_role, n, wrong, passes, advised):
    with app.app_context():
        a = _staged_lessons(n)
        bad = {f"e{i}" for i in range(wrong)}
        _answer(a, lambda s: s["text"] not in bad)
        at.finish(a, 1)
        assert (a.status == "in_progress") is passes
        adv = at.advice(a)
        assert adv["relearn"] == ([] if passes else ["M"])
        assert [x["name"] for x in adv["lessons"]] == [f"d{i}" for i in range(advised)]
        u = a.client_uuid
    if passes:
        html = as_role("user").get(f"/test/urinish/{u}/bosqich").get_data(as_text=True)
        assert html.count("darsni qayta o‘zlashtirish tavsiya etiladi") == advised


@pytest.mark.usefixtures("fresh_content")
def test_recommended_lesson_listed_until_lesson_test_90(app, as_role):
    with app.app_context():
        uid = _uid()
        a = _staged_lessons(10)
        _answer(a, lambda s: s["text"] not in {"e0", "e1"})
        at.finish(a, 1)
        _answer(a)
        at.finish(a, 2)                                              # 2-bosqich 100%: 1-bosqich tavsiyasi saqlanadi
        assert a.status == "submitted"
        assert sorted(r["lesson"] for r in catalog.recommended_lessons(uid)) == ["d0", "d1"]
        _load({"M": {"d0": [_q(f"x{i}") for i in range(6)]}})        # savol takrorlanmaydi: ikkita dars testiga yangilari
        sid = _sub("d0")
    c = as_role("user")
    for url in ("/app/", "/app/xatolar"):
        html = c.get(url).get_data(as_text=True)
        assert "Qayta o‘zlashtirish tavsiya etilgan darslar" in html and ">d0<" in html, url
    with app.app_context():
        for good, left in ((False, ["d0", "d1"]), (True, ["d1"])):  # yomon natija chiqarmaydi, ≥ 90% — chiqaradi
            x, _ = tb.get_or_start(uid, "lesson", subtopic_id=sid)
            _answer(x, lambda s: good)
            at.finish(x)
            assert sorted(r["lesson"] for r in catalog.recommended_lessons(uid)) == left


def test_lesson_test_70_89_is_recommended(app):
    with app.app_context():
        uid, sid = _uid(), _sub("if operatori")
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=sid)
        snaps = at._snapshots(a)
        at.save_answers(a, [{"pos": p, "at": 1, "v": _right(s)[:2] if s["type"] == "multiple" else _right(s)}
                            for p, (s, *_x) in snaps.items()])
        at.finish(a)
        assert [(r["lesson"], r["pct"], r["rid"]) for r in catalog.recommended_lessons(uid)] == [("if operatori", 89, a.id)]


@pytest.mark.usefixtures("fresh_content")
def test_optional_test_recommendation_is_not_listed(app):
    with app.app_context():
        _load({"M": {f"d{i}": [_q(f"e{i}")] for i in range(10)}})
        a, _ = tb.get_or_start(_uid(), "optional", n=10)
        _answer(a, lambda s: s["text"] not in {"e0", "e1"})
        at.finish(a, 1)
        assert len(at.advice(a)["lessons"]) == 2                    # natija sahifasida ko'rinadi
        assert catalog.recommended_lessons(_uid()) == []            # lekin o'quv rejaga ta'sir qilmaydi


def test_diagnostic_marks_known_topics(app, client):
    with app.app_context():
        uid = _uid()
        a, _ = tb.get_or_start(uid, "diagnostic")
        while a.status == "in_progress":
            _answer(a)
            at.finish(a, a.stage)
        assert a.score_pct == 100
        rows = db.session.scalars(select(UserTopicProgress)).all()
        assert rows and all(p.status == "solid" and p.flags == ["diagnostic"] for p in rows)
        u = a.client_uuid
    r = client.get(f"/test/urinish/{u}/natija", follow_redirects=True)
    html = r.get_data(as_text=True)
    assert r.request.path == "/app/diagnostika/natija" and "Reja qolgan 0 ta mavzudan" in html


def test_interim_failure_returns_topics_to_relearn(app):
    with app.app_context():
        _master(["Sanoq sistemalari"])
        a, _ = tb.get_or_start(_uid(), "interim")
        at.finish(a, 1)
        assert a.status == "submitted"
        assert db.session.get(UserTopicProgress, (_uid(), _topic("Sanoq sistemalari"))).status == "relearn"


# ---------------- Bekor qilish ----------------

def test_cancel_only_optional(app, client):
    with app.app_context():
        opt, _ = tb.get_or_start(_uid(), "optional", n=10)
        les, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=_sub("if operatori"))
        o, x = opt.client_uuid, les.client_uuid
    html = client.get("/app/testlar").get_data(as_text=True)
    assert "Ixtiyoriy test" in html and "Dars testi: if operatori" in html and f"/test/urinish/{x}" in html
    assert client.post(f"/app/testlar/{o}/bekor", headers=JSON).json["ok"]
    assert client.post(f"/app/testlar/{x}/bekor", headers=JSON).status_code == 422
    assert client.post(f"/app/testlar/{uuid.uuid4()}/bekor", headers=JSON).status_code == 422
    assert client.get(f"/test/urinish/{o}").status_code == 404
    assert client.post(f"/api/urinish/{o}/yakunlash", json={"kind": "optional", "stage": 1}).status_code == 409


# ---------------- E'tirozlar ----------------

@pytest.fixture()
def ref(app, client):
    with app.app_context():
        a, _ = tb.get_or_start(_uid(), "lesson", subtopic_id=_sub("if operatori"))
        return f"{a.client_uuid}:0"


def test_objection_saved_with_question_version(app, client, ref):
    body = {"question": ref, "reason": "unclear", "note": "Aniq emas", "urgent": "1"}
    assert client.post("/app/etiroz", data=body, headers=JSON).json["ok"]
    with app.app_context():
        o = db.session.scalar(select(Objection))
        item = at.get(uuid.UUID(ref[:36])).items[0]
        assert (o.question_id, o.question_version, o.attempt_id) == (item.question_id, item.question_version, item.attempt_id)
        assert (o.reason, o.text, o.urgent, o.status) == ("unclear", "Aniq emas", True, "review")
        text = db.session.get(Question, o.question_id).text
    from markupsafe import escape
    assert str(escape(text)) in client.get("/app/etirozlarim").get_data(as_text=True)
    # Takror yuborilmaydi va tugma pleyerda o'chiq turadi
    r = client.post("/app/etiroz", data=body, headers=JSON)
    assert r.status_code == 422 and "allaqachon" in r.json["errors"]["reason"]
    assert "sent: true" in client.get(f"/test/urinish/{ref[:36]}").get_data(as_text=True)


@pytest.mark.parametrize("question", ["Q-1", "", "x:0", f"{uuid.uuid4()}:0"])
def test_objection_needs_own_question(app, client, question):
    r = client.post("/app/etiroz", data={"question": question, "reason": "unclear"}, headers=JSON)
    assert r.status_code == 422
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Objection)) == 0


def test_objection_other_position_or_user(app, as_role, client, ref):
    assert client.post("/app/etiroz", data={"question": ref[:37] + "99", "reason": "unclear"}, headers=JSON).status_code == 422
    with app.app_context():
        at.get(uuid.UUID(ref[:36])).user_id = demo_user("expert").id
        db.session.commit()
    assert client.post("/app/etiroz", data={"question": ref, "reason": "unclear"}, headers=JSON).status_code == 422


def test_sample_objection_is_not_saved(app, client):
    assert client.post("/app/etiroz", data={"question": "namuna:0", "reason": "unclear"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Objection)) == 0


def test_objection_edit_and_delete_only_while_in_review(app, client, ref):
    client.post("/app/etiroz", data={"question": ref, "reason": "unclear"}, headers=JSON)
    with app.app_context():
        oid = db.session.scalar(select(Objection.id))
    assert client.post(f"/app/etirozlarim/{oid}/tahrir", data={"reason": "media", "note": "x"}, headers=JSON).json["ok"]
    r = client.post(f"/app/etirozlarim/{oid}/tahrir", data={"reason": "other", "note": ""}, headers=JSON)
    assert r.status_code == 422 and "note" in r.json["errors"]
    with app.app_context():
        o = db.session.get(Objection, oid)
        assert (o.reason, o.text) == ("media", "x")
        o.status = "accepted"
        db.session.commit()
    assert client.post(f"/app/etirozlarim/{oid}/tahrir", data={"reason": "unclear"}, headers=JSON).status_code == 422
    assert client.post(f"/app/etirozlarim/{oid}/ochirish", headers=JSON).status_code == 422
    with app.app_context():
        db.session.get(Objection, oid).status = "review"
        db.session.commit()
    assert client.post(f"/app/etirozlarim/{oid}/ochirish", headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(m.Objection)) == 0


# ---------------- Namunaviy ekranlar ----------------

@pytest.mark.parametrize("kind", ["yopiq", "kop", "moslash", "ochiq", "jadval", "rasm"])
def test_sample_player_has_objection(client, kind):
    html = client.get(f"/test/savol?tur={kind}").get_data(as_text=True)
    assert "objection-sent.window" in html and 'action="/app/etiroz"' in html


@pytest.mark.parametrize("url,n", [("/test/natija", 6), ("/test/sinov/natija", 35), ("/app/natijalar/900009", 6),
                                   ("/app/diagnostika/natija", 6)])
def test_sample_objection_button_on_every_question(client, url, n):
    html = client.get(url).get_data(as_text=True)
    assert html.count("objection-sent.window") == n and html.count('action="/app/etiroz"') == 1


def test_samples_closed_in_production(app, client):
    app.config["DEV_TOOLS"] = False
    for url in ("/test/savol?tur=yopiq", "/test/natija", "/test/bosqich", "/test/sinov/natija"):
        assert client.get(url).location.endswith("/app/testlar"), url
    assert client.get("/app/diagnostika/natija").location.endswith("/app/diagnostika")
    r = client.post("/app/etiroz", data={"question": "namuna:0", "reason": "unclear"}, headers=JSON)
    assert r.status_code == 422
