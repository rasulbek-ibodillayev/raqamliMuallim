"""Formalar: server tekshiruvi, JSON (JS bilan) va oddiy POST (JS'siz), CSRF."""
import pytest

from app import create_app
from tests.conftest import JSON

CASES = [
    ("user", "/kirish", {"login": "abc", "pw": ""}, {"login", "pw"}),
    ("user", "/royxat", {"phone": "123"}, {"phone"}),
    ("user", "/royxat/telegram", {"otp": ["1", "2"]}, {"otp"}),
    ("user", "/royxat/malumotlar", {"fn": "", "ln": "1", "pw": "abc", "pw2": "x"}, {"fn", "ln", "pw", "pw2", "consent"}),
    ("user", "/parol-tiklash", {"otp": "000000", "p1": "abcdefgh1", "p2": "abcdefgh1"}, {"otp"}),
    ("user", "/app/profil/parol", {"old": "", "new": "short", "new2": "x"}, {"old", "new", "new2"}),
    ("user", "/app/etiroz", {"question": "Q-1", "reason": "other"}, {"note"}),
    ("user", "/app/muhokama", {"body": ""}, {"body"}),
    ("user", "/app/eslatmalar", {"topic": "X", "text": ""}, {"text"}),
    ("admin", "/admin/foydalanuvchilar/sana", {"user": "A", "date": "2000-01-01"}, {"date"}),
    ("admin", "/admin/ekspertlar", {"name": "Ali"}, {"name", "contact", "areas", "perms"}),
]


@pytest.mark.parametrize("role,url,data,fields", CASES, ids=[c[1] for c in CASES])
def test_validation_json(as_role, role, url, data, fields):
    r = as_role(role).post(url, data=data, headers=JSON)
    assert r.status_code == 422
    assert set(r.json["errors"]) == fields
    assert r.json["ok"] is False


@pytest.mark.parametrize("role,url,data,fields", CASES, ids=[c[1] for c in CASES])
def test_validation_without_js(as_role, role, url, data, fields):
    r = as_role(role).post(url, data=data)
    assert r.status_code == 422
    assert 'class="field-error"' in r.get_data(as_text=True)


def test_success_json_and_prg(as_role):
    c = as_role("user")
    r = c.post("/app/profil/hudud", data={"region": "Andijon viloyati"}, headers=JSON)
    assert r.json == {"ok": True, "message": "Hudud saqlandi", "redirect": "/app/profil", "data": {}}
    r = c.post("/app/profil/hudud", data={"region": "Andijon viloyati"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/app/profil")


def test_registration_flow(client):
    assert client.post("/royxat", data={"phone": "90 123 45 67"}, headers=JSON).json["ok"]
    assert client.post("/royxat/telegram", data={"otp": list("123456")}, headers=JSON).json["ok"]
    r = client.post("/royxat/malumotlar", headers=JSON, data={
        "fn": "Dilnoza", "ln": "Karimova", "pw": "parol1234", "pw2": "parol1234", "consent": "1"})
    assert r.json["ok"] and "6 oy" in r.json["message"]


def test_csrf_required():
    app = create_app()
    app.config.update(TESTING=True)
    c = app.test_client()
    assert c.post("/kirish", data={"login": "x"}).status_code == 400
    r = c.post("/api/urinish/00000000-0000-4000-8000-000000000000/javoblar", json={})
    assert r.status_code == 400 and r.json["ok"] is False
