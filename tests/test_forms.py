"""Formalar: server tekshiruvi, JSON (JS bilan) va oddiy POST (JS'siz), CSRF."""
import pytest

from app import create_app
from tests.conftest import JSON

CASES = [
    ("user", "/kirish", {"login": "abc", "pw": ""}, {"login", "pw"}),
    ("user", "/royxat", {"phone": "123"}, {"phone"}),
    ("user", "/royxat/telegram", {"otp": ["1", "2"]}, {"otp"}),
    ("user", "/royxat/malumotlar", {"fn": "", "ln": "1", "pw": "abc", "pw2": "x"}, {"fn", "ln", "pw", "pw2", "secret", "consent"}),
    ("user", "/parol-tiklash/maxfiy-soz", {"who": "x", "secret": ""}, {"who", "secret"}),
    ("user", "/app/profil/aloqa/kod", {"method": "email", "contact": "yo'q"}, {"contact"}),
    ("user", "/app/profil/maxfiy-soz", {"pw": "", "secret": "ab"}, {"pw", "secret"}),
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
        "fn": "Dilnoza", "ln": "Karimova", "pw": "parol1234", "pw2": "parol1234",
        "secret": "Birinchi maktabim", "consent": "1"})
    assert r.json["ok"] and "6 oy" in r.json["message"]


def test_csrf_required():
    app = create_app()
    app.config.update(TESTING=True)
    c = app.test_client()
    assert c.post("/kirish", data={"login": "x"}).status_code == 400
    r = c.post("/api/urinish/00000000-0000-4000-8000-000000000000/javoblar", json={})
    assert r.status_code == 400 and r.json["ok"] is False


def test_secret_must_differ_from_password(client):
    r = client.post("/royxat/malumotlar", headers=JSON, data={
        "fn": "Ali", "ln": "Valiyev", "pw": "parol1234", "pw2": "parol1234", "secret": " PAROL1234 ", "consent": "1"})
    assert set(r.json["errors"]) == {"secret"}


def test_recover_by_secret_word(client):
    # 1) eski login + maxfiy so'z (katta-kichik harf va bo'sh joy farqlanmaydi)
    r = client.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": " Informatika "}, headers=JSON)
    assert r.json["ok"] and r.json["data"]["step"] == 2
    # 2) yangi email → kod
    r = client.post("/parol-tiklash/maxfiy-soz/aloqa", data={"method": "email", "contact": "Yangi@Maktab.uz"}, headers=JSON)
    assert r.json["ok"] and "yangi@maktab.uz" in r.json["message"]
    # 3) kod + yangi parol → akkauntga kiradi
    r = client.post("/parol-tiklash/maxfiy-soz/tasdiq", headers=JSON,
                    data={"otp": list("123456"), "p1": "yangiparol1", "p2": "yangiparol1"})
    assert r.json["ok"] and r.json["redirect"] == "/app/"


def test_recover_steps_cannot_be_skipped(client):
    assert client.post("/parol-tiklash/maxfiy-soz/aloqa", data={"contact": "a@b.uz"}).status_code == 302
    assert client.post("/parol-tiklash/maxfiy-soz/tasdiq", data={"otp": "123456"}).status_code == 302


def test_recover_locks_after_5_wrong_secrets(client):
    for _ in range(5):
        client.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": "xato"}, headers=JSON)
    r = client.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": "informatika"}, headers=JSON)
    assert r.status_code == 422 and "Urinishlar tugadi" in r.json["errors"]["secret"]
    # "Boshqa telefon kiritish" (qayta=1) urinishlar sonini nolga tushirmaydi
    client.get("/parol-tiklash/maxfiy-soz?qayta=1")
    r = client.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": "informatika"}, headers=JSON)
    assert r.status_code == 422


def test_change_phone_requires_code(client):
    r = client.post("/app/profil/aloqa/kod", data={"method": "phone", "contact": "90 123 45 67"}, headers=JSON)
    assert "hozirgi" in r.json["errors"]["contact"]
    r = client.post("/app/profil/aloqa/kod", data={"method": "phone", "contact": "93 111 22 33"}, headers=JSON)
    assert r.json["ok"] and r.json["data"]["target"] == "+998 93 111 22 33"
    assert client.post("/app/profil/aloqa/tasdiq", data={"otp": list("000000")}, headers=JSON).status_code == 422
    r = client.post("/app/profil/aloqa/tasdiq", data={"otp": list("123456")}, headers=JSON)
    assert r.json["message"] == "Telefon raqam yangilandi"
    # Kod ikkinchi marta ishlamaydi
    assert client.post("/app/profil/aloqa/tasdiq", data={"otp": list("123456")}, headers=JSON).status_code == 422


def test_certificate_lookup_page(client):
    assert "Sertifikatni tekshirish" in client.get("/").get_data(as_text=True)
    assert client.get("/s").status_code == 200
    assert client.get("/s?raqam=abc").status_code == 422
    assert client.get("/s?raqam=inf-2026-000123").headers["Location"].endswith("/s/INF-2026-000123")
