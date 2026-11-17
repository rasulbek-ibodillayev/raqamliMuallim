"""Test pleyer API: javoblarni saqlash (idempotent), yakunlash, validatsiya."""
import uuid

import pytest

from app.views import api


@pytest.fixture(autouse=True)
def clean():
    api.ATTEMPTS.clear()
    yield
    api.ATTEMPTS.clear()


def url(u, what="javoblar"):
    return f"/api/urinish/{u}/{what}"


def test_save_and_finish(client):
    u = str(uuid.uuid4())
    r = client.post(url(u), json={"kind": "exam", "answers": [{"pos": 0, "v": 1, "t": 1200, "at": 1}]})
    assert r.status_code == 200 and r.json["saved"] == [0]
    r = client.post(url(u, "yakunlash"), json={"kind": "exam"})
    assert r.status_code == 200 and r.json["answered"] == 1 and r.json["result_url"]
    # Yakunlangandan keyin javob qabul qilinmaydi
    assert client.post(url(u), json={"kind": "exam", "answers": [{"pos": 1, "v": 0}]}).status_code == 409
    # Yakunlash idempotent
    assert client.post(url(u, "yakunlash"), json={"kind": "exam"}).status_code == 200


def test_older_answer_does_not_overwrite_newer(client):
    u = str(uuid.uuid4())
    client.post(url(u), json={"kind": "topic", "answers": [{"pos": 3, "v": 2, "at": 200}]})
    client.post(url(u), json={"kind": "topic", "answers": [{"pos": 3, "v": 0, "at": 100}]})
    assert api.ATTEMPTS[u]["answers"][3]["v"] == 2


@pytest.mark.parametrize("value", [1, [0, 2], "45", None, [None, 1]])
def test_valid_answer_types(client, value):
    r = client.post(url(uuid.uuid4()), json={"kind": "topic", "answers": [{"pos": 0, "v": value}]})
    assert r.status_code == 200


@pytest.mark.parametrize("payload,status", [
    ({"kind": "exam"}, 400),
    ({"kind": "nope", "answers": [{"pos": 0, "v": 1}]}, 422),
    ({"kind": "exam", "answers": []}, 422),
    ({"kind": "exam", "answers": [{"pos": -1, "v": 1}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": True}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": "x" * 501}]}, 422),
    ({"kind": "exam", "answers": [{"pos": 0, "v": {"a": 1}}]}, 422),
])
def test_invalid_payloads(client, payload, status):
    assert client.post(url(uuid.uuid4()), json=payload).status_code == status


def test_bad_uuid(client):
    r = client.post("/api/urinish/123/javoblar", json={"kind": "exam", "answers": [{"pos": 0, "v": 1}]})
    assert r.status_code == 400


def test_api_requires_user_role(as_role):
    r = as_role("admin").post(url(uuid.uuid4()), json={"kind": "exam", "answers": [{"pos": 0, "v": 1}]})
    assert r.status_code == 403 and r.json["ok"] is False
