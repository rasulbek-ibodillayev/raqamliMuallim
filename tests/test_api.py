"""Test pleyer API: javoblarni saqlash (idempotent), yakunlash, egalik, validatsiya."""
import uuid

import pytest
from sqlalchemy import select

from app.cli import demo_user
from app.extensions import db
from app.models import Subtopic, TestAttempt
from app.services import test_builder as tb


def url(u, what="javoblar"):
    return f"/api/urinish/{u}/{what}"


@pytest.fixture()
def attempt(app, client):
    """«if operatori» dars testi (3 savol) — namunaviy o'qituvchiniki."""
    with app.app_context():
        sid = db.session.scalar(select(Subtopic.id).where(Subtopic.title == "if operatori"))
        a, fresh = tb.get_or_start(demo_user("user").id, "lesson", subtopic_id=sid)
        assert fresh and a.total == 3
        return str(a.client_uuid)


def _answers(app, u):
    with app.app_context():
        a = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == uuid.UUID(u)))
        return {i.position: i.answer for i in a.items}


def test_save_and_finish(app, client, attempt):
    r = client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 0, "v": 1, "t": 1200, "at": 1}]})
    assert r.status_code == 200 and r.json["saved"] == [0]
    assert _answers(app, attempt)[0] == {"v": 1, "at": 1}
    r = client.post(url(attempt, "yakunlash"), json={"kind": "lesson"})
    assert r.status_code == 200 and r.json["answered"] == 1
    assert r.json["result_url"] == f"/test/urinish/{attempt}/natija"
    # Yakunlangandan keyin javob qabul qilinmaydi
    assert client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 1, "v": 0}]}).status_code == 409
    # Yakunlash idempotent
    assert client.post(url(attempt, "yakunlash"), json={"kind": "lesson"}).status_code == 200


def test_older_answer_does_not_overwrite_newer(app, client, attempt):
    client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 2, "v": 2, "at": 200}]})
    client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 2, "v": 0, "at": 100}]})
    assert _answers(app, attempt)[2]["v"] == 2
    client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 2, "v": None, "at": 300}]})   # javob olib tashlandi
    assert _answers(app, attempt)[2]["v"] is None


@pytest.mark.parametrize("value", [1, [0, 2], "45", None, [None, 1]])
def test_valid_answer_types(client, attempt, value):
    r = client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 0, "v": value}]})
    assert r.status_code == 200


def test_position_outside_attempt_is_ignored(app, client, attempt):
    r = client.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 150, "v": 1}]})
    assert r.status_code == 200 and all(v is None for v in _answers(app, attempt).values())


@pytest.mark.parametrize("payload,status", [
    ({"kind": "exam"}, 400),
    ({"kind": "nope", "answers": [{"pos": 0, "v": 1}]}, 422),
    ({"kind": "exam", "answers": []}, 422),
    ({"kind": "exam", "answers": [{"pos": -1, "v": 1}]}, 422),
    ({"kind": "exam", "answers": [{"pos": True, "v": 1}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": True}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": "x" * 501}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": {"a": 1}}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": 1, "at": "x"}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": 1}]}, 422),        # urinish turi boshqa (lesson)
])
def test_invalid_payloads(client, attempt, payload, status):
    assert client.post(url(attempt), json=payload).status_code == status


def test_bad_or_unknown_uuid(client):
    body = {"kind": "exam", "answers": [{"pos": 0, "v": 1}]}
    assert client.post("/api/urinish/123/javoblar", json=body).status_code == 400
    assert client.post(url(uuid.uuid4()), json=body).status_code == 404
    assert client.post(url(uuid.uuid4(), "yakunlash"), json={"kind": "exam"}).status_code == 404


def test_other_users_attempt_is_forbidden(app, as_role, attempt):
    with app.app_context():
        a = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == uuid.UUID(attempt)))
        a.user_id = demo_user("expert").id
        db.session.commit()
    c = as_role("user")
    assert c.post(url(attempt), json={"kind": "lesson", "answers": [{"pos": 0, "v": 1}]}).status_code == 403
    assert c.post(url(attempt, "yakunlash"), json={"kind": "lesson"}).status_code == 403
    assert c.get(f"/test/urinish/{attempt}").status_code == 404


def test_api_requires_user_role(as_role):
    r = as_role("admin").post(url(uuid.uuid4()), json={"kind": "exam", "answers": [{"pos": 0, "v": 1}]})
    assert r.status_code == 403 and r.json["ok"] is False
