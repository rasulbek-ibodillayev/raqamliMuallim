"""Attestatsiya vaqti: serverda yuritiladi, tugagach test yakunlanadi va javob berilgan savollar baholanadi."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from app.cli import demo_user
from app.extensions import db
from app.models import ErrorItem, Job, Question, QuestionStat, TestAttempt
from app.services import attempts as at
from app.services import exam_clock as ec
from app.services import jobs, tasks
from app.services import test_builder as tb
from tests.conftest import JSON


@pytest.fixture()
def exam(app, client):
    """Boshlangan attestatsiya testi: (uuid, urinish id)."""
    url = client.get("/test/sinov").location
    with app.app_context():
        a = db.session.scalar(select(TestAttempt))
        assert a.kind == "exam" and a.total >= 3
        return url.rsplit("/", 1)[1], a.id


def get(aid) -> TestAttempt:
    db.session.rollback()
    return db.session.get(TestAttempt, aid, populate_existing=True)


def shift(aid, seconds):
    """Tugash vaqti hozirdan shuncha soniya keyin (manfiy — o'tib ketgan)."""
    db.session.execute(text("UPDATE test_attempts SET deadline_at = now() + make_interval(secs => :s) WHERE id = :i"), {"s": seconds, "i": aid})
    db.session.commit()


def right(aid, pos):
    a = get(aid)
    i = next(x for x in a.items if x.position == pos)
    return db.session.get(Question, i.question_id).answer["keys"][0]


def send(client, uuid, answers, **extra):
    return client.post(f"/api/urinish/{uuid}/javoblar", json={"kind": "exam", "answers": answers, **extra})


def ms(delta=0):
    return round((time.time() + delta) * 1000)


def test_start_schedules_finish(app, exam):
    with app.app_context():
        j = db.session.scalar(select(Job).where(Job.kind == "exam_end"))
        a = get(exam[1])
        assert j.key == f"exam:{a.id}" and abs((j.run_at - a.deadline_at).total_seconds() - ec.GRACE) < 5


def test_background_job_finishes_and_grades_answered(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        k = right(aid, 0)
    assert send(client, uuid, [{"pos": 0, "v": k, "at": ms()}]).json["ok"]
    with app.app_context():
        total = get(aid).total
        shift(aid, -ec.GRACE - 1)
        db.session.execute(text("UPDATE jobs SET run_at = now() WHERE kind = 'exam_end'"))
        db.session.commit()
        assert jobs.run_due(jobs.FAST) == 1
        a = get(aid)
        assert a.status == "submitted" and a.correct == 1 and abs(a.score_pct - 100 / total) < 1
        assert a.finished_at == a.deadline_at and a.settings_snapshot["timeout"] is True
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == total - 1     # javobsizlari — xato
        assert not jobs.TASKS["exam_end"].run({"id": aid})["n"]                                # qayta chaqirish xavfsiz


def test_nothing_happens_before_time(app, exam):
    with app.app_context():
        assert tasks.exam_end({"id": exam[1]}) == {"n": 0}
        shift(exam[1], -ec.GRACE + 20)                                # tugagan, lekin oxirgi javob hali yo'lda bo'lishi mumkin
        assert tasks.exam_end({"id": exam[1]}) == {"n": 0} and get(exam[1]).status == "in_progress"
        assert tasks.exam_end({"id": 999_999}) == {"n": 0}


@pytest.mark.parametrize("url", ["/app/testlar", "/test/sinov", "/test/urinish/{}"])
def test_pages_finish_overdue_test_without_worker(app, client, exam, url):
    uuid, aid = exam
    with app.app_context():
        shift(aid, -ec.GRACE - 1)
    html = client.get(url.format(uuid), follow_redirects=True).text
    assert "vaqti tugadi" in html
    with app.app_context():
        assert get(aid).status == "submitted"
        assert db.session.scalar(select(func.count()).select_from(TestAttempt)) == (2 if url == "/test/sinov" else 1)


def test_nightly_cleanup_finishes_lost_ones(app, exam):
    with app.app_context():
        shift(exam[1], -ec.GRACE - 1)
        assert tasks.cleanup({})["n"] >= 1 and get(exam[1]).status == "submitted"


def test_other_kinds_are_not_timed(app, client):
    with app.app_context():
        a, _ = tb.get_or_start(demo_user("user").id, "optional")
        shift(a.id, -9999)
        assert ec.close_all() == 0 and get(a.id).status == "in_progress"
        u = a.client_uuid
    assert client.get(f"/api/urinish/{u}/vaqt").status_code == 422


# ---------------- Pauza ----------------

def test_pause_stops_time_on_server(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        shift(aid, 100)
    r = client.post(f"/api/urinish/{uuid}/pauza").json
    assert r["paused"] and 97 <= r["left"] <= 100
    with app.app_context():
        assert get(aid).deadline_at is None and tasks.exam_end({"id": aid}) == {"n": 0} and ec.close_all() == 0
    assert client.get(f"/api/urinish/{uuid}/vaqt").json == {"ok": True, "left": r["left"], "paused": True}
    assert client.post(f"/api/urinish/{uuid}/pauza").json["left"] == r["left"]          # takror bosish xavfsiz
    html = client.get(f"/test/urinish/{uuid}").text
    assert f'"duration": {r["left"]}' in html
    r2 = client.post(f"/api/urinish/{uuid}/davom").json
    assert not r2["paused"] and r2["left"] == r["left"]
    with app.app_context():
        a, j = get(aid), db.session.scalar(select(Job).where(Job.kind == "exam_end"))
        assert "left" not in a.settings_snapshot and abs((j.run_at - a.deadline_at).total_seconds() - ec.GRACE) < 5
        assert db.session.scalar(select(func.count()).select_from(Job)) == 1


def test_pause_is_refused_after_time(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        shift(aid, -5)
    r = client.post(f"/api/urinish/{uuid}/pauza").json
    assert not r["paused"] and r["left"] == 0
    with app.app_context():
        shift(aid, -ec.GRACE - 1)
    r = client.post(f"/api/urinish/{uuid}/davom").json
    assert r["closed"] and r["result_url"].endswith("/natija")


def test_clock_is_private(app, exam, as_role):
    uuid, _aid = exam
    assert as_role("expert").get(f"/api/urinish/{uuid}/vaqt").status_code == 403
    with app.app_context():
        from app.models import User
        u = User(first_name="A", last_name="B", email="b@b.uz", role="user")
        db.session.add(u)
        db.session.commit()
        sid = u.get_id()
    c = app.test_client()
    with c.session_transaction() as s:
        s["_user_id"], s["_fresh"] = sid, True
    for m, p in (("get", "vaqt"), ("post", "pauza"), ("post", "davom")):
        assert getattr(c, m)(f"/api/urinish/{uuid}/{p}").status_code == 403
    assert c.get("/api/urinish/xato/vaqt").status_code == 400


def test_second_device_gets_remaining_time_not_full(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        shift(aid, 300)
    html = client.get(f"/test/urinish/{uuid}").text
    assert '"duration": 7200' not in html and ('"duration": 300' in html or '"duration": 299' in html)


# ---------------- Vaqtdan keyingi javoblar ----------------

def test_answer_marked_after_time_is_ignored(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        shift(aid, -20)
    r = send(client, uuid, [{"pos": 0, "v": 0, "at": ms()}, {"pos": 1, "v": 0, "at": ms(-60)}], now=ms())
    assert r.json["saved"] == [0, 1]                                   # navbatdan o'chadi, lekin kechikkani yozilmaydi
    with app.app_context():
        assert {i.position for i in get(aid).items if i.answer} == {1}


def test_wrong_device_clock_is_corrected(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        shift(aid, -20)
    ahead = 3 * 3600                                                   # qurilma soati 3 soat oldinda
    send(client, uuid, [{"pos": 0, "v": 0, "at": ms(ahead - 60)}, {"pos": 1, "v": 0, "at": ms(ahead)}], now=ms(ahead))
    with app.app_context():
        assert {i.position for i in get(aid).items if i.answer} == {0}


def _timeout(app, aid):
    with app.app_context():
        shift(aid, -ec.GRACE - 1)
        assert ec.close_all() == 1


def test_offline_answers_count_after_automatic_finish(app, client, exam):
    uuid, aid = exam
    with app.app_context():
        keys = [right(aid, p) for p in range(3)]
        qid = get(aid).items[0].question_id
    send(client, uuid, [{"pos": 2, "v": keys[2], "at": ms()}])
    _timeout(app, aid)
    with app.app_context():
        a = get(aid)
        before, errors = a.score_pct, db.session.scalar(select(func.count()).select_from(ErrorItem))
    late = [{"pos": 0, "v": keys[0], "at": ms(-600)}, {"pos": 1, "v": keys[1], "at": ms()},            # 1 — vaqtdan keyin
            {"pos": 2, "v": (keys[2] + 1) % 2, "at": ms(-500)}]                                        # 2 — javobi bor
    for _n in range(2):                                                # navbat takrori
        assert send(client, uuid, late, now=ms()).status_code == 200
    r = client.post(f"/api/urinish/{uuid}/yakunlash", json={"kind": "exam", "stage": None}).json
    assert r["ok"] and r["answered"] == 2 and r["result_url"].endswith("/natija")
    with app.app_context():
        a = get(aid)
        assert a.correct == 2 and a.score_pct > before
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == errors - 1
        s = db.session.get(QuestionStat, qid)
        assert (s.answered, s.correct) == (1, 1)


def test_no_late_answers_after_key_was_shown(app, client, exam):
    uuid, aid = exam
    _timeout(app, aid)
    html = client.get(f"/test/urinish/{uuid}/natija").text
    assert "Vaqt tugadi" in html
    assert send(client, uuid, [{"pos": 0, "v": 0, "at": ms(-600)}], now=ms()).status_code == 409
    with app.app_context():
        assert get(aid).settings_snapshot["viewed"] is True


def test_manual_finish_takes_no_late_answers(app, client, exam):
    uuid, _aid = exam
    client.post(f"/api/urinish/{uuid}/yakunlash", json={"kind": "exam", "stage": None})
    assert send(client, uuid, [{"pos": 0, "v": 0, "at": ms(-600)}], now=ms()).status_code == 409


def test_archived_exam_takes_no_late_answers(app, client, exam):
    from app.services import archive
    uuid, aid = exam
    _timeout(app, aid)
    with app.app_context():
        assert archive.compress_old(datetime.now(timezone.utc) + timedelta(days=8)) == 1
    assert send(client, uuid, [{"pos": 0, "v": 0, "at": ms(-600)}], now=ms()).status_code == 409


def test_bad_device_time_is_harmless(client, exam):
    for now in ("x", -5, 0, None, True, 1 << 60):
        assert send(client, exam[0], [{"pos": 0, "v": 0, "at": ms()}], now=now).status_code == 200


def test_csrf_still_protects_pause():
    from app import create_app
    from tests.conftest import CONFIG
    c = create_app({**CONFIG, "WTF_CSRF_ENABLED": True}).test_client()
    c.get("/_rol/user")
    assert c.post("/api/urinish/00000000-0000-4000-8000-000000000000/pauza", headers=JSON).status_code == 400
