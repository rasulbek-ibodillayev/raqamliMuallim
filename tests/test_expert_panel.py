"""7b: mavzular va darslar muharriri, e'tirozlarni ko'rib chiqish, qayta hisoblash, bildirishnomalar, ekspert huquqlari, eksport."""
import copy
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app import models as m
from app.cli import demo_user
from app.extensions import db
from app.models import (AttemptItem, ContentBlock, ErrorItem, ExpertProfile, Notification, Objection, Question, QuestionVersion, Section,
                        Subtopic, TestAttempt, Topic, User, UserTopicProgress)
from app.services import archive, catalog, notify, objections
from app.services import attempts as at
from app.services import content_editor as ce
from app.services import objection_review as rv
from app.services import question_bank as qb
from app.services import test_builder as tb
from app.services import xlsx
from app.services.content_import import load
from tests.conftest import JSON

BLOCK = [{"kind": "text", "data": {"body": "x"}}]


def _uid():
    return demo_user("user").id


def _eid():
    return demo_user("expert").id


def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


def _topic(title="M"):
    return db.session.scalar(select(Topic.id).where(Topic.title == title))


def _q(text, type_="single", **kw):
    base = {"single": ({"options": ["a", "b", "c"]}, {"keys": [0]}), "multiple": ({"options": ["a", "b", "c"]}, {"keys": [0, 1]}),
            "matching": ({"left": ["a", "b"], "right": ["c", "d"]}, {"pairs": [0, 1]}), "open": ({}, {"value": "45"})}[type_]
    return {"type": type_, "difficulty": "easy", "text": text, "data": base[0], "answer": base[1], **kw}


def _load(subs, section="S", topic="M"):
    load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": section, "topics": [{"title": topic, "subtopics": [
        {"title": t, "questions": qs, "blocks": BLOCK} for t, qs in subs.items()]}]}]}, status="approved")


def _by_text(text):
    return db.session.scalar(select(Question).where(Question.text == text))


def _run(kind, values, uid=None, **kw):
    """values: {savol matni: javob}; qolganlari to'g'ri."""
    a, _ = tb.get_or_start(uid or _uid(), kind, **kw)
    while a.status == "in_progress":
        snaps, ans = at._snapshots(a), []
        for p in at.active_positions(a):
            s = snaps[p][0]
            right = {"single": lambda: s["answer"]["keys"][0], "multiple": lambda: s["answer"]["keys"],
                     "matching": lambda: s["answer"]["pairs"], "open": lambda: s["answer"]["value"]}[s["type"]]()
            ans.append({"pos": p, "v": values.get(s["text"], right), "at": 1})
        at.save_answers(a, ans)
        at.finish(a, a.stage)
    return a


def _object(a, text, reason="wrong_key", uid=None, urgent=False):
    pos = next(p for p, (s, *_x) in at._snapshots(a).items() if s["text"] == text)
    return objections.create(uid or _uid(), objections.ref(a, pos), reason, "izoh", urgent)


def _notes():
    return list(db.session.scalars(select(Notification).order_by(Notification.id)))


@pytest.fixture()
def lesson3(app, fresh_content):
    with app.app_context():
        _load({"D": [_q("q1"), _q("q2"), _q("q3", "multiple")]})
        yield


# ---------------- Qaror: to'g'ri javob o'zgaradi ----------------

def test_key_change_recalculates_everyone_upwards_only(lesson3):
    sid, qid = _sub("D"), _by_text("q1").id
    other = User(first_name="B", last_name="C", phone="+998900000001", role="user")
    db.session.add(other)
    db.session.commit()
    mine = _run("lesson", {"q1": 1}, subtopic_id=sid)                       # 67%
    theirs = _run("lesson", {"q1": 1}, uid=other.id, subtopic_id=sid)       # 67%, e'tiroz bildirmagan
    old_right = User(first_name="D", last_name="E", phone="+998900000002", role="user")
    db.session.add(old_right)
    db.session.commit()
    good = _run("lesson", {}, uid=old_right.id, subtopic_id=sid)            # 100% eski kalit bilan
    assert (mine.score_pct, theirs.score_pct, good.score_pct) == (67, 67, 100) and mine.decision == "fail"
    o = _object(mine, "q1")
    assert rv.count() == 1
    d = rv.detail(qid)
    assert [(x["right"], x["pct"]) for x in d["options"]] == [(True, 33), (False, 67), (False, 0)]

    assert rv.decide(qid, _eid(), "key", "Kalit xato edi", [1]) == 2
    assert (mine.score_pct, theirs.score_pct, good.score_pct) == (100, 100, 100)
    assert mine.decision == "pass" and mine.correct == 3
    q = db.session.get(Question, qid)
    assert q.version == 2 and q.answer == {"keys": [1]} and q.status == "approved"
    assert (o.status, o.verdict, o.score_before, o.score_after) == ("accepted", "Kalit xato edi", 67, 100)
    # Ko'rib chiqishda yangi kalit; eski kalit bo'yicha to'g'ri bo'lganida o'z versiyasi qoladi
    assert next(r for r in at.review(mine) if r["q"] == "q1")["right"] == [1]
    assert next(r for r in at.review(good) if r["q"] == "q1")["right"] == [0]
    # Xato yopildi, dars o'tgan hisoblanadi
    assert db.session.scalar(select(func.count()).select_from(ErrorItem).where(ErrorItem.user_id == _uid())) == 0
    assert catalog.lesson_scores(_uid(), _topic()) == {sid: 100}
    assert db.session.get(UserTopicProgress, (_uid(), _topic())).lesson_pct == 100
    assert [(n.user_id, n.kind, n.old_pct, n.new_pct) for n in _notes()] == [
        (_uid(), notify.OBJ_ACCEPTED, 67, 100), (other.id, notify.RECALC, 67, 100)]
    assert rv.count() == 0
    with pytest.raises(qb.FormError):
        rv.decide(qid, _eid(), "reject", "x")


def test_single_question_with_two_right_answers_is_paused(lesson3):
    a = _run("lesson", {"q1": 2}, subtopic_id=_sub("D"))
    _object(a, "q1", "also_correct")
    qid = _by_text("q1").id
    assert rv.decide(qid, _eid(), "key", "Ikkalasi to‘g‘ri", [0, 2]) == 1
    q = db.session.get(Question, qid)
    assert a.score_pct == 100 and q.status == "paused" and q.version == 1 and q.answer == {"keys": [0]}


def test_open_answer_gets_more_accepted_values(app, fresh_content):
    with app.app_context():
        _load({"D": [_q("o", "open"), _q("q2"), _q("q3", "multiple")]})
        a = _run("lesson", {"o": "qirq besh"}, subtopic_id=_sub("D"))
        _object(a, "o")
        qid = _by_text("o").id
        assert rv.detail(qid)["given"] == [("qirq besh", 1)]
        with pytest.raises(qb.FormError):
            rv.decide(qid, _eid(), "key", "x", accept=["45", " "])
        db.session.rollback()
        assert rv.decide(qid, _eid(), "key", "x", accept=[" Qirq besh ", "45"]) == 1
        assert a.score_pct == 100 and db.session.get(Question, qid).answer["accept"] == ["Qirq besh"]


@pytest.mark.parametrize("keys", [[], [0], [9]])
def test_key_must_really_change(lesson3, keys):
    _object(_run("lesson", {"q1": 1}, subtopic_id=_sub("D")), "q1")
    with pytest.raises(qb.FormError):
        rv.decide(_by_text("q1").id, _eid(), "key", "x", keys)


def test_version_with_other_options_is_not_regraded(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    q = _by_text("q1")
    _object(a, "q1")
    qb.save({**qb._snapshot(q), "data": {"options": ["a", "z", "c"]}}, _eid(), q.id)     # variantlar o'zgardi
    assert rv.decide(q.id, _eid(), "key", "x", [1]) == 0 and a.score_pct == 67


def test_unfinished_test_gets_new_version(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    _object(a, "q1")
    other = User(first_name="B", last_name="C", phone="+998900000003", role="user")
    db.session.add(other)
    db.session.commit()
    open_, _ = tb.get_or_start(other.id, "lesson", subtopic_id=_sub("D"))
    rv.decide(_by_text("q1").id, _eid(), "key", "x", [1])
    db.session.expire_all()
    pos = next(p for p, (s, *_x) in at._snapshots(open_).items() if s["text"] == "q1")
    assert at._snapshots(open_)[pos][0]["answer"] == {"keys": [1]}
    b = _run("lesson", {}, uid=other.id, subtopic_id=_sub("D"))
    assert b.id == open_.id and b.score_pct == 100


# ---------------- Qaror: hisobdan chiqarish ----------------

def test_drop_excludes_question_and_pauses_it(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    _object(a, "q1", "unclear")
    assert rv.decide(_by_text("q1").id, _eid(), "drop", "Savol noaniq") == 1
    assert a.score_pct == 100 and a.settings_snapshot["dropped"] and _by_text("q1").status == "paused"
    r = next(r for r in at.review(a) if r["q"] == "q1")
    assert r["dropped"] and r["score"] == 0
    assert at.by_subtopic(a)[0][1:] == (100, "2", 2)
    assert catalog.subtopic_scores(_uid(), _topic()) == {_sub("D"): 100}
    assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == 0


def test_drop_keeps_right_answers_and_last_question(lesson3):
    a = _run("lesson", {"q2": 1}, subtopic_id=_sub("D"))                    # q1 to'g'ri
    _object(a, "q1")
    assert rv.decide(_by_text("q1").id, _eid(), "drop", "x") == 0
    assert a.score_pct == 67 and "dropped" not in a.settings_snapshot
    one = User(first_name="B", last_name="C", phone="+998900000004", role="user")
    db.session.add(one)
    db.session.commit()
    b = _run("lesson", {"q2": 1}, uid=one.id, subtopic_id=_sub("D"))        # q1 to'xtatilgan: 2 savol
    assert b.total == 2


def test_dropped_in_unfinished_test_is_not_graded(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    _object(a, "q1")
    u = User(first_name="B", last_name="C", phone="+998900000005", role="user")
    db.session.add(u)
    db.session.commit()
    open_, _ = tb.get_or_start(u.id, "lesson", subtopic_id=_sub("D"))
    rv.decide(_by_text("q1").id, _eid(), "drop", "x")
    db.session.expire_all()
    b = _run("lesson", {"q1": 1}, uid=u.id, subtopic_id=_sub("D"))
    assert b.id == open_.id and b.score_pct == 100
    assert db.session.scalar(select(func.count()).select_from(ErrorItem).where(ErrorItem.user_id == u.id)) == 0


def test_staged_topic_passes_after_recalc(app, fresh_content):
    """Kalit xatosi sababli o'tmagan mavzu: yuqori bosqich savollari hisobdan chiqadi, mavzu tavsiyadan o'chadi."""
    with app.app_context():
        levels = ("easy", "medium", "hard")
        _load({"a": [_q(f"a-{d}", difficulty=d) for d in levels]}, topic="A")
        _load({"b": [_q(f"b-{d}", difficulty=d) for d in levels]}, topic="B")
        a = _run("diagnostic", {"b-easy": 1})
        assert a.score_pct == 50 and a.settings_snapshot["failed_topics"] == [_topic("B")]
        _object(a, "b-easy")
        assert rv.decide(_by_text("b-easy").id, _eid(), "key", "x", [1]) == 1
        assert a.score_pct == 100 and a.settings_snapshot["failed_topics"] == [] and at.advice(a) == {"relearn": [], "lessons": []}
        p = db.session.get(UserTopicProgress, (_uid(), _topic("B")))
        assert p.status == "solid" and p.flags == ["diagnostic"]


def test_topic_test_status_improves_but_interim_respects_later_failure(app, fresh_content):
    with app.app_context():
        _load({"D": [_q(f"q{i}") for i in range(8)]})
        t = _run("topic", {"q0": 1, "q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 1, "q6": 1, "q7": 1}, topic_id=_topic())
        assert t.score_pct == 0 and db.session.get(UserTopicProgress, (_uid(), _topic())).status == "relearn"
        for text in [s["text"] for s, *_x in at._snapshots(t).values()]:
            _object(t, text)
            rv.decide(_by_text(text).id, _eid(), "key", "x", [1])
        assert t.score_pct == 100
        assert db.session.get(UserTopicProgress, (_uid(), _topic())).status == "solid"


def test_archived_attempt_is_recalculated(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    _object(a, "q1")
    a.finished_at -= timedelta(days=400)
    db.session.commit()
    assert archive.compress_old() == 1
    assert rv.decide(_by_text("q1").id, _eid(), "key", "x", [1]) == 1
    assert a.score_pct == 100 and db.session.scalar(select(func.count()).select_from(AttemptItem)) == 0
    assert {i.score for i in archive.rows(a)} == {100}
    assert next(r for r in at.review(a) if r["q"] == "q1")["right"] == [1]


# ---------------- Rad etish va boshqa qarorlar ----------------

def test_reject_and_fix_do_not_touch_results(lesson3):
    a = _run("lesson", {"q1": 1, "q2": 1}, subtopic_id=_sub("D"))
    o1, o2 = _object(a, "q1"), _object(a, "q2", urgent=True)
    assert [x["id"] for x in rv.queue()] == [_by_text("q2").id, _by_text("q1").id]       # shoshilinchi birinchi
    assert rv.decide(_by_text("q1").id, _eid(), "reject", "Javob to‘g‘ri") == 0
    assert rv.decide(_by_text("q2").id, _eid(), "fix", "Matn tuzatiladi") == 0
    assert (o1.status, o2.status, a.score_pct) == ("rejected", "accepted", 33)
    assert [n.kind for n in _notes()] == [notify.OBJ_REJECTED, notify.OBJ_ACCEPTED]
    assert db.session.scalar(select(func.count()).select_from(m.AuditLog).where(m.AuditLog.action.like("objection_%"))) == 2


@pytest.mark.parametrize("action,verdict", [("key", ""), ("", "x"), ("boshqa", "x")])
def test_decision_is_validated(lesson3, action, verdict):
    _object(_run("lesson", {"q1": 1}, subtopic_id=_sub("D")), "q1")
    with pytest.raises(qb.FormError):
        rv.decide(_by_text("q1").id, _eid(), action, verdict, [1])


def test_objections_page_and_forms(app, as_role, lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    _object(a, "q1")
    qid, uid = _by_text("q1").id, _uid()
    c = as_role("expert")
    html = c.get("/ekspert/etirozlar").get_data(as_text=True)
    assert f"#{qid}" in html and "To‘g‘ri javob noto‘g‘ri ko‘rsatilgan" in html and "Dilnoza K." in html
    assert "Karimova" not in html                                          # ekspert to'liq familiyani ko'rmaydi
    assert c.post(f"/ekspert/etirozlar/{qid}/toxtatish", data={"on": "1"}).status_code == 302
    assert "Testlarda vaqtincha to‘xtatilgan" in c.get("/ekspert/etirozlar").get_data(as_text=True)
    c.post(f"/ekspert/etirozlar/{qid}/toxtatish", data={"on": "0"})
    r = c.post(f"/ekspert/etirozlar/{qid}", data={"action": "key", "keys": "1"}, headers=JSON)
    assert r.status_code == 422 and "verdict" in r.json["errors"]
    r = c.post(f"/ekspert/etirozlar/{qid}", data={"action": "key", "keys": "1", "verdict": "Kalit xato"})
    assert r.status_code == 302
    assert "Ko‘rib chiqiladigan e’tiroz yo‘q" in c.get("/ekspert/etirozlar").get_data(as_text=True)
    u = as_role("user")
    html = u.get("/app/etirozlarim").get_data(as_text=True)
    assert "Kalit xato" in html and "67%" in html and "100%" in html
    home = u.get("/app/").get_data(as_text=True)
    assert "E’tirozingiz qabul qilindi" in home and "bell-dot" in home
    assert u.post("/app/bildirishnomalar/oqildi", headers=JSON).json["ok"]
    assert "bell-dot" not in u.get("/app/").get_data(as_text=True)
    assert u.get(f"/ekspert/etirozlar").status_code == 403 and uid


# ---------------- AI savolini rad etish ----------------

def test_rejected_ai_question_is_dropped_and_users_notified(lesson3):
    a = _run("lesson", {"q1": 1}, subtopic_id=_sub("D"))
    q = _by_text("q1")
    q.source, q.status = "ai", "review"
    db.session.commit()
    assert qb.reject(q.id, _eid())
    assert db.session.get(Question, q.id).status == "archived" and a.score_pct == 100
    n = _notes()
    assert [(x.user_id, x.kind, x.ref_id, x.old_pct, x.new_pct) for x in n] == [(_uid(), notify.DROPPED, a.id, 67, 100)]


def test_unused_ai_question_is_deleted(lesson3):
    q = _by_text("q1")
    q.source, q.status = "ai", "review"
    db.session.commit()
    qid = q.id
    assert qb.reject(qid, _eid()) and db.session.get(Question, qid) is None and _notes() == []


# ---------------- Bildirishnomalar ----------------

def test_notifications_expire_and_show_unfinished_tests(app, lesson3):
    uid = _uid()
    with app.test_request_context():
        notify.add(uid, notify.RECALC, None, 50.4, 60.6)
        db.session.flush()
        db.session.scalar(select(Notification)).created_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.session.commit()
        assert notify.list_for(db.session.get(User, uid)) == []
        tb.get_or_start(uid, "lesson", subtopic_id=_sub("D"))
        a = db.session.scalar(select(TestAttempt))
        notify.add(uid, notify.DROPPED, a.id, 70, 70)
        db.session.commit()
        assert db.session.scalar(select(func.count()).select_from(Notification)) == 1      # eskisi o'chdi
        items = notify.list_for(db.session.get(User, uid))
        assert [x["title"] for x in items] == ["Tugatilmagan testingiz bor", "Savol hisobdan chiqarildi"]
        assert items[0]["unread"] is False and items[1]["unread"] and "Dars testi: D" in items[1]["text"]
        assert "o‘zgarmadi" in items[1]["text"]
        notify.mark_seen(db.session.get(User, uid))
        assert not any(x["unread"] for x in notify.list_for(db.session.get(User, uid)))


# ---------------- Muharrir ----------------

def _api(c, **d):
    return c.post("/ekspert/mavzular/api", json=d)


@pytest.mark.usefixtures("fresh_content")
def test_tree_operations(app, as_role):
    c = as_role("expert")
    r = _api(c, op="section_save", name="  Yangi   mavzu ")
    sid = r.json["id"]
    assert r.json["ok"] and r.json["tree"][0]["name"] == "Yangi mavzu"
    assert _api(c, op="section_save", name="yangi MAVZU").status_code == 422
    assert _api(c, op="section_save", name="").status_code == 422
    two = _api(c, op="section_save", name="Ikkinchi").json["id"]
    assert [t["id"] for t in _api(c, op="move", kind="section", id=two, step=-1).json["tree"]] == [two, sid]
    assert _api(c, op="section_save", id=sid, name="Nomi").json["tree"][1]["name"] == "Nomi"
    l1, l2 = (_api(c, op="lesson_add", section_id=sid, name=n).json["id"] for n in ("Dars 1", "Dars 2"))
    assert _api(c, op="lesson_add", section_id=sid, name="dars 1").status_code == 422
    assert _api(c, op="lesson_add", section_id=9999, name="x").status_code == 422
    t = _api(c, op="move", kind="topic", id=l2, step=-1).json["tree"][1]
    assert [x["id"] for x in t["lessons"]] == [l2, l1] and not any(x["published"] for x in t["lessons"])
    assert _api(c, op="lesson_delete", id=l2).json["ok"]
    for bad in ({"op": "nima"}, {"op": "move", "kind": "user", "id": 1, "step": 1}, {"op": "move", "kind": "topic", "id": l1, "step": 5}, {}):
        assert _api(c, **bad).status_code in (403, 422), bad
    assert _api(c, op="section_delete", id=sid).json["ok"]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Topic)) == 0
        assert db.session.scalar(select(func.count()).select_from(m.AuditLog).where(m.AuditLog.entity.in_(("section", "topic")))) == 7


def test_things_with_questions_are_not_deleted(app, as_role):
    with app.app_context():
        tid = _topic("Sanoq sistemalari")
        sid = db.session.get(Topic, tid).section_id
    c = as_role("expert")
    assert _api(c, op="lesson_delete", id=tid).status_code == 422
    assert _api(c, op="section_delete", id=sid).status_code == 422
    d = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    d["subs"] = d["subs"][:1]
    r = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r.status_code == 422 and "savollari bor" in r.json["error"]
    with app.app_context():
        assert _sub("O‘n oltilik")


def test_unchanged_lesson_keeps_versions(app, as_role):
    """Muharrir → baza → muharrir: o'zgartirilmagan bloklar (hamma turlari) o'zgarmaydi."""
    with app.app_context():
        tid = _topic("Python: shart operatorlari")
        before = {b.id: (b.kind, copy.deepcopy(b.data), b.version, b.content_hash) for b in db.session.scalars(select(ContentBlock))}
    c = as_role("expert")
    d = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    assert len({b["kind"] for s in d["subs"] for b in s["blocks"]}) >= 3
    r = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r.status_code == 200, r.json
    with app.app_context():
        assert {b.id: (b.kind, b.data, b.version, b.content_hash) for b in db.session.scalars(select(ContentBlock))} == before


@pytest.mark.usefixtures("fresh_content")
def test_lesson_editing_full_cycle(app, as_role):
    c = as_role("expert")
    sec = _api(c, op="section_save", name="S").json["id"]
    tid = _api(c, op="lesson_add", section_id=sec, name="Sikllar").json["id"]
    d = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    d.update(minutes=15, published=True)
    assert c.post(f"/ekspert/mavzular/dars/{tid}", json=d).status_code == 422          # bo'sh dars nashr qilinmaydi
    d["subs"][0].update(name="for", weight=3, generators=["py_for", "yoq"], blocks=[
        {"kind": "text", "data": {"title": "Kirish", "body": "Matn <b>\n\nikkinchi"}},
        {"kind": "code", "data": {"code": "\n  x = 1\n", "lang": "Python", "boshqa": "x"}},
        {"kind": "table", "data": {"body": "A | B\n1 | 2\n3", "head": True}},
        {"kind": "links", "data": {"links": [{"title": "Hujjat", "url": "https://docs.python.org"}, {"title": "", "url": ""}]}},
        {"kind": "video", "data": {"title": "", "url": "https://youtu.be/x"}}])
    d["subs"].append({"id": None, "name": "while", "weight": 1, "generators": [], "blocks": []})
    r = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r.status_code == 200, r.json
    assert r.json["tree"][0]["lessons"][0] == {"id": tid, "name": "Sikllar", "published": True, "subs": 2, "blocks": 5, "questions": 0}
    with app.app_context():
        bs = db.session.scalars(select(ContentBlock).order_by(ContentBlock.position)).all()
        assert [b.data for b in bs] == [
            {"title": "Kirish", "body": "Matn <b>\n\nikkinchi"}, {"code": "  x = 1", "lang": "Python"},
            {"head": ["A", "B"], "rows": [["1", "2"], ["3", ""]]},
            {"links": [{"title": "Hujjat", "url": "https://docs.python.org"}]}, {"url": "https://youtu.be/x"}]
        s = db.session.get(Subtopic, _sub("for"))
        assert s.weight == 3 and s.generators == ["py_for"] and bs[0].author_id == _eid()
        assert db.session.get(Topic, tid).est_minutes == 15
        db.session.get(ContentBlock, bs[3].id)
    # O'qituvchi darsni ko'radi (matn ekranlangan)
    html = as_role("user").get(f"/app/dars/{tid}").get_data(as_text=True)
    assert "&lt;b&gt;" in html and "https://docs.python.org" in html

    # Bitta blok o'zgardi: faqat uning versiyasi oshadi; tartib almashadi; biri o'chadi
    d = r.json["lesson"]
    first = d["subs"][0]["blocks"]
    first[0]["data"]["body"] = "Yangi matn"
    first[0], first[1] = first[1], first[0]
    removed = first.pop(2)["id"]
    r = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r.status_code == 200, r.json
    with app.app_context():
        got = {b.kind: (b.version, b.position) for b in db.session.scalars(select(ContentBlock))}
        assert got["text"] == (2, 1) and got["code"] == (1, 0) and removed and "table" not in got

    # Eski nusxa bilan saqlash — 409, hech narsa yozilmaydi
    d["name"] = "Bosib ketadigan nom"
    r2 = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r2.status_code == 409 and "boshqa joyda" in r2.json["error"]
    with app.app_context():
        assert db.session.get(Topic, tid).title == "Sikllar"
    fresh = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    fresh["subs"].pop()                                                                # savolsiz kichik mavzu o'chadi
    assert c.post(f"/ekspert/mavzular/dars/{tid}", json=fresh).status_code == 200
    with app.app_context():
        assert _sub("while") is None


@pytest.mark.parametrize("block,err", [
    ({"kind": "text", "data": {"body": " "}}, "bo‘sh"),
    ({"kind": "video", "data": {"url": "javascript:alert(1)"}}, "https"),
    ({"kind": "video", "data": {"url": "http://x.uz"}}, "https"),
    ({"kind": "links", "data": {"links": [{"title": "x", "url": "javascript:1"}]}}, "https"),
    ({"kind": "links", "data": {"links": []}}, "Havola"),
    ({"kind": "image", "data": {"src": "https://evil/x.png", "alt": "a"}}, "Rasmni"),
    ({"kind": "image", "data": {"src": "uploads/../../x.png", "alt": "a"}}, "Rasmni"),
    ({"kind": "image", "data": {"src": "uploads/q/ab.png", "alt": ""}}, "tavsifini"),
    ({"kind": "table", "data": {"body": "\n \n"}}, "Jadval"),
    ({"kind": "quiz", "data": {}}, "turi"),
    ({"kind": "text", "data": "matn"}, "bo‘sh"),
    ("blok", "noto‘g‘ri"),
])
def test_bad_blocks_are_rejected(app, as_role, block, err):
    with app.app_context():
        tid = _topic("Sanoq sistemalari")
        n = db.session.scalar(select(func.count()).select_from(ContentBlock))
    c = as_role("expert")
    d = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    d["subs"][0]["name"] = "O‘zgargan nom"
    d["subs"][1]["blocks"].append(block)
    r = c.post(f"/ekspert/mavzular/dars/{tid}", json=d)
    assert r.status_code == 422 and err in r.json["error"]
    with app.app_context():                                          # xatoda hech narsa yozilmaydi
        assert db.session.scalar(select(func.count()).select_from(ContentBlock)) == n and _sub("Ikkilik va o‘nlik")


def test_lesson_payload_shape_is_checked(app, as_role):
    with app.app_context():
        tid = _topic("Sanoq sistemalari")
    c = as_role("expert")
    d = c.get(f"/ekspert/mavzular/dars/{tid}").json["lesson"]
    for over in ({"subs": []}, {"subs": "x"}, {"name": " "}, {"subs": [{"name": "a"}, {"name": "A"}]}):
        assert c.post(f"/ekspert/mavzular/dars/{tid}", json={**d, **over}).status_code == 422, over
    assert c.post(f"/ekspert/mavzular/dars/{tid}", json=[1]).status_code == 409
    assert c.get("/ekspert/mavzular/dars/99999").status_code == 404
    assert c.post("/ekspert/mavzular/rasm", data={}).status_code == 422
    assert as_role("user").get(f"/ekspert/mavzular/dars/{tid}").status_code == 403


def test_other_lessons_blocks_cannot_be_stolen(app, as_role):
    with app.app_context():
        a, b = _topic("Python: shart operatorlari"), _topic("Sanoq sistemalari")
        stolen = db.session.scalar(select(ContentBlock.id).join(Subtopic).where(Subtopic.topic_id == a))
    c = as_role("expert")
    d = c.get(f"/ekspert/mavzular/dars/{b}").json["lesson"]
    d["subs"][0]["blocks"].append({"id": stolen, "kind": "text", "data": {"body": "yangi"}})
    assert c.post(f"/ekspert/mavzular/dars/{b}", json=d).status_code == 200
    with app.app_context():
        assert db.session.get(ContentBlock, stolen).subtopic.topic_id == a
        db.session.execute(ContentBlock.__table__.delete().where(ContentBlock.data["body"].as_string() == "yangi"))
        db.session.commit()


# ---------------- Savol muharriri: izoh va kod ----------------

def test_question_editor_notes_and_code(app, as_role):
    with app.app_context():
        q = db.session.scalar(select(Question).where(Question.text.like("DNS%")))
        qid, sub = q.id, db.session.get(Subtopic, q.subtopic_id)
        base = {"id": str(qid), "topic": sub.topic.section_id, "lesson": sub.topic_id, "subtopic": sub.id, "level": "Oson",
                "kind": "yopiq", "format": "matn", "time": "60", "text": q.text, "why": q.explanation}
        old = copy.deepcopy((q.data, q.answer, q.version, q.explanation))
    c = as_role("expert")
    html = c.get(f"/ekspert/savol?id={qid}").get_data(as_text=True)
    assert "TLS (HTTPS)" in html
    r = c.post("/ekspert/savol", headers=JSON, data={**base, "opt": ["a", "", "b"], "opt_note": ["n1", "yo‘q", ""], "right": "2",
                                                     "code": "\r\nif x:\r\n    print(1)\r\n"})
    assert r.json["ok"], r.json
    with app.app_context():
        q = db.session.get(Question, qid)
        assert q.answer == {"keys": [1], "notes": ["n1", ""]} and q.data["code"] == "if x:\n    print(1)"
        q.data, q.answer, q.version, q.explanation = old
        db.session.execute(QuestionVersion.__table__.delete().where(QuestionVersion.question_id == qid, QuestionVersion.version > old[2]))
        db.session.commit()


def test_table_question_keeps_table_in_editor(app, as_role):
    with app.app_context():
        q = db.session.scalar(select(Question).where(Question.text.like("%SUMIF%"), Question.source != "template"))
        qid, head = q.id, q.data["table"]["head"]
    html = as_role("expert").get(f"/ekspert/savol?id={qid}").get_data(as_text=True)
    assert "fmt: &#34;jadval&#34;" in html and 'name="table_head" value="1" checked' in html and head[1] == "A"


# ---------------- Excel ----------------

def test_export_imports_back_without_duplicates(app, as_role):
    c = as_role("expert")
    r = c.get("/ekspert/savollar/eksport.xlsx")
    assert r.status_code == 200 and r.headers["Content-Disposition"].endswith('savollar.xlsx"')
    rows = xlsx.read_rows(r.data)
    with app.app_context():
        n = db.session.scalar(select(func.count()).select_from(Question).where(Question.status != "archived"))
        assert len(rows) == n + 1 and rows[0] == qb.EXCEL_HEAD
        assert any(x[4] == "moslashtirish" and "HTTP = Gipermatn" in x[6] for x in rows)
        assert any(len(x) > 15 and x[15] == "kod" for x in rows) and any(len(x) > 15 and x[15] == "jadval" for x in rows)
        assert qb.import_excel(r.data, _eid()) == (0, [])
        assert db.session.scalar(select(func.count()).select_from(Question).where(Question.status != "archived")) == n
    only = xlsx.read_rows(c.get("/ekspert/savollar/eksport.xlsx?turi=moslash&holat=approved").data)
    assert {x[4] for x in only[1:]} == {"moslashtirish"}


# ---------------- Huquqlar ----------------

@pytest.fixture()
def limited(app):
    """Faqat «questions» huquqi va bitta mavzu (Mantiq asoslari) bilan ekspert."""
    with app.app_context():
        sec = db.session.scalar(select(Section.id).where(Section.title == "Mantiq asoslari"))
        db.session.add(ExpertProfile(user_id=_eid(), perms=["questions"], areas=[sec]))
        db.session.commit()
        own = db.session.scalar(select(Question.id).where(Question.text.like("De Morgan%"), Question.status == "approved"))
        foreign = db.session.scalar(select(Question.id).where(Question.text.like("DNS%")))
        return {"sec": sec, "own": own, "foreign": foreign, "tid": _topic("Mantiqiy amallar"), "other": _topic("Sanoq sistemalari")}


def test_permissions_limit_pages_and_menu(as_role, limited):
    c = as_role("expert")
    html = c.get("/ekspert/").get_data(as_text=True)
    assert "Mavzular va darslar</a>" not in html and "/ekspert/etirozlar" not in html and "/ekspert/navbat" not in html
    for url in ("/ekspert/mavzular", "/ekspert/etirozlar", "/ekspert/navbat"):
        assert c.get(url).status_code == 403, url
    assert c.post("/ekspert/etirozlar/1", data={}).status_code == 403
    assert _api(c, op="section_save", name="x").status_code == 403


def test_areas_limit_questions(app, as_role, limited):
    c = as_role("expert")
    html = c.get("/ekspert/").get_data(as_text=True)
    assert "De Morgan" in html and "DNS serverning" not in html
    assert c.get(f"/ekspert/savol?id={limited['own']}").status_code == 200
    assert c.get(f"/ekspert/savol?id={limited['foreign']}").status_code == 403
    assert c.post(f"/ekspert/savollar/{limited['foreign']}/ochirish").status_code == 403
    assert all("Mantiq asoslari" == x[0] for x in xlsx.read_rows(c.get("/ekspert/savollar/eksport.xlsx").data)[1:])
    with app.app_context():
        assert qb.import_excel(qb.export_excel(qb.Filters()), _eid(), {limited["sec"]})[1]      # boshqa mavzu — xato


def test_areas_limit_lessons_and_objections(app, as_role, limited):
    with app.app_context():
        db.session.get(ExpertProfile, _eid()).perms = ["topics", "objections"]
        db.session.commit()
        a = _run("lesson", {}, subtopic_id=_sub("Amaliy protokollar"))
        _object(a, at._snapshots(a)[0][0]["text"])
    c = as_role("expert")
    assert "Ko‘rib chiqiladigan e’tiroz yo‘q" in c.get("/ekspert/etirozlar").get_data(as_text=True)
    with app.app_context():
        qid = db.session.scalar(select(Objection.question_id))
    assert c.post(f"/ekspert/etirozlar/{qid}", data={"action": "reject", "verdict": "x"}).status_code == 403
    assert c.get(f"/ekspert/mavzular/dars/{limited['tid']}").status_code == 200
    assert c.get(f"/ekspert/mavzular/dars/{limited['other']}").status_code == 403
    assert _api(c, op="section_save", name="Yangi").status_code == 403                  # yangi mavzu — cheklovsiz ekspertga
    assert _api(c, op="lesson_delete", id=limited["other"]).status_code == 403
    assert _api(c, op="move", kind="section", id=limited["sec"] + 1, step=1).status_code == 403


def test_invite_saves_rights(app, guest):
    from app import invites
    with app.app_context():
        sec = db.session.scalar(select(Section.id).where(Section.title == "Dasturlash"))
        token = invites.token(invites.make("Nodira Saidova", "+998935551199", [sec], ["questions", "review", "begona"]))
        db.session.commit()
    r = guest.post(f"/taklif/{token}", data={"pw": "ekspert123", "pw2": "ekspert123", "secret": "metodika", "agree": "1"}, headers=JSON)
    assert r.json["ok"]
    with app.app_context():
        p = db.session.scalar(select(ExpertProfile))
        assert p.perms == ["questions", "review"] and p.areas == [sec]
    assert guest.get("/ekspert/").status_code == 200 and guest.get("/ekspert/mavzular").status_code == 403
