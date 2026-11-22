"""Kirish va akkaunt: users jadvali va Flask-Login bilan haqiqiy ishlashi."""
import pytest

from app import create_app
from app.cli import demo_user
from app.extensions import db
from app.models.users import User
from tests.conftest import CONFIG, JSON


def _user(app, login):
    with app.app_context():
        return User.by_login(login)


@pytest.fixture()
def teacher(app):
    with app.app_context():
        demo_user("user")


def test_login_wrong_password_is_rejected(guest, teacher):
    r = guest.post("/kirish", data={"login": "+998901234567", "pw": "notogri123"}, headers=JSON)
    assert r.status_code == 422 and "pw" in r.json["errors"]
    r = guest.post("/kirish", data={"login": "+998909999999", "pw": "parol1234"}, headers=JSON)
    assert r.status_code == 422 and "pw" in r.json["errors"]   # topilmagan raqam ham xuddi shu xato
    assert guest.get("/app/").status_code == 302


def test_login_accepts_phone_in_any_format_and_follows_next(guest, teacher):
    r = guest.post("/kirish?next=/app/reja", data={"login": "90 123-45-67", "pw": "parol1234"}, headers=JSON)
    assert r.json["ok"] and r.json["redirect"] == "/app/reja"


@pytest.mark.parametrize("nxt", ["//evil.example/x", "https://evil.example/", "/admin/"])
def test_login_ignores_foreign_next(guest, teacher, nxt):
    r = guest.post("/kirish", data={"login": "+998901234567", "pw": "parol1234", "next": nxt}, headers=JSON)
    assert r.json["redirect"] == "/app/"


def test_logout_also_drops_remember_cookie(guest, teacher):
    guest.post("/kirish", data={"login": "+998901234567", "pw": "parol1234"}, headers=JSON)
    assert guest.get_cookie("remember_token") is not None
    guest.get("/chiqish")
    assert guest.get_cookie("remember_token") is None
    assert guest.get("/app/").status_code == 302


def test_blocked_account_cannot_log_in(app, guest, teacher):
    with app.app_context():
        User.by_login("+998901234567").is_active = False
        db.session.commit()
    r = guest.post("/kirish", data={"login": "+998901234567", "pw": "parol1234"}, headers=JSON)
    assert r.status_code == 422 and "login" in r.json["errors"]


def test_register_rejects_taken_phone_and_email(guest, teacher):
    r = guest.post("/royxat", data={"phone": "+998901234567"}, headers=JSON)
    assert r.status_code == 422 and "phone" in r.json["errors"]
    r = guest.post("/royxat/email/kod", data={"email": "Dilnoza.K@maktab.uz"}, headers=JSON)
    assert r.status_code == 422 and "email" in r.json["errors"]


def test_register_needs_verified_contact(guest):
    guest.post("/royxat", data={"phone": "90 765 43 21"}, headers=JSON)   # kod tasdiqlanmagan
    r = guest.post("/royxat/malumotlar", headers=JSON, data={
        "fn": "Malika", "ln": "Tursunova", "pw": "parol1234", "pw2": "parol1234", "secret": "olma daraxti", "consent": "1"})
    assert r.status_code == 422


def test_register_by_email_saves_user(app, guest):
    guest.post("/royxat/email/kod", data={"email": "Yangi@Maktab.uz"}, headers=JSON)
    assert guest.post("/royxat/email", data={"email": "yangi@maktab.uz", "otp": list("123456")}, headers=JSON).json["ok"]
    r = guest.post("/royxat/malumotlar", headers=JSON, data={
        "fn": "Malika", "ln": "Tursunova", "pw": "parol1234", "pw2": "parol1234", "secret": "olma daraxti",
        "region": "Samarqand viloyati", "consent": "1"})
    assert r.json["ok"]
    u = _user(app, "yangi@maktab.uz")
    assert u.role == "user" and u.phone is None and u.region == "Samarqand viloyati" and u.consent_at
    assert u.password_hash != "parol1234" and u.check_password("parol1234") and u.check_secret("OLMA  daraxti")


def test_email_code_must_match_requested_email(guest):
    guest.post("/royxat/email/kod", data={"email": "bir@maktab.uz"}, headers=JSON)
    r = guest.post("/royxat/email", data={"email": "boshqa@maktab.uz", "otp": list("123456")}, headers=JSON)
    assert r.status_code == 422 and "email" in r.json["errors"]


def test_profile_password_change_is_saved(app, client):
    r = client.post("/app/profil/parol", data={"old": "notogri123", "new": "yangiparol9", "new2": "yangiparol9"}, headers=JSON)
    assert r.status_code == 422 and "old" in r.json["errors"]
    r = client.post("/app/profil/parol", data={"old": "parol1234", "new": "yangiparol9", "new2": "yangiparol9"}, headers=JSON)
    assert r.json["ok"]
    assert _user(app, "+998901234567").check_password("yangiparol9")


def test_profile_name_and_secret_are_saved(app, client):
    assert client.post("/app/profil/malumotlar", data={"fn": "Dilfuza", "ln": "Karimova"}, headers=JSON).json["ok"]
    assert "Dilfuza" in client.get("/app/profil").get_data(as_text=True)
    r = client.post("/app/profil/maxfiy-soz", data={"pw": "notogri123", "secret": "yangi soz"}, headers=JSON)
    assert r.status_code == 422 and "pw" in r.json["errors"]
    assert client.post("/app/profil/maxfiy-soz", data={"pw": "parol1234", "secret": "yangi soz"}, headers=JSON).json["ok"]
    u = _user(app, "+998901234567")
    assert u.check_secret("Yangi  SOZ") and not u.check_secret("informatika")


def test_profile_contact_change_is_saved(app, client, as_role):
    as_role("expert")   # +998931234545 band
    r = client.post("/app/profil/aloqa/kod", data={"method": "phone", "contact": "93 123 45 45", "pw": "parol1234"}, headers=JSON)
    assert r.status_code == 422 and "contact" in r.json["errors"]
    assert client.post("/app/profil/aloqa/kod", data={"method": "email", "contact": "Yangi@Maktab.uz", "pw": "parol1234"}, headers=JSON).json["ok"]
    assert client.post("/app/profil/aloqa/tasdiq", data={"otp": list("123456")}, headers=JSON).json["ok"]
    assert _user(app, "yangi@maktab.uz").first_name == "Dilnoza"


def test_password_reset_sets_new_password(app, guest, teacher):
    guest.post("/parol-tiklash/kod", data={"who": "+998901234567"}, headers=JSON)
    guest.post("/parol-tiklash/kod-tekshirish", data={"otp": list("123456")}, headers=JSON)
    assert guest.post("/parol-tiklash", data={"p1": "tiklangan1", "p2": "tiklangan1"}, headers=JSON).json["ok"]
    assert _user(app, "+998901234567").check_password("tiklangan1")


def test_recover_replaces_contact_and_password(app, guest, teacher):
    assert guest.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": " INFORMATIKA "}, headers=JSON).json["ok"]
    assert guest.post("/parol-tiklash/maxfiy-soz/aloqa", data={"method": "phone", "contact": "99 111 22 33"}, headers=JSON).json["ok"]
    r = guest.post("/parol-tiklash/maxfiy-soz/tasdiq", data={"otp": list("123456"), "p1": "tiklangan1", "p2": "tiklangan1"}, headers=JSON)
    assert r.json["ok"]
    u = _user(app, "+998991112233")
    assert u.first_name == "Dilnoza" and u.check_password("tiklangan1")
    assert guest.get("/app/").status_code == 200


def test_recover_wrong_secret_for_real_user(guest, teacher):
    r = guest.post("/parol-tiklash/maxfiy-soz", data={"who": "+998901234567", "secret": "boshqa soz"}, headers=JSON)
    assert r.status_code == 422 and "secret" in r.json["errors"]


def test_invite_creates_expert_account(app, guest):
    r = guest.get("/taklif/namuna")
    token_url = r.headers["Location"]
    r = guest.post(token_url, data={"pw": "ekspert123", "pw2": "ekspert123", "secret": "metodika", "agree": "1"}, headers=JSON)
    assert r.json["ok"]
    u = _user(app, "+998935551122")
    assert u.role == "expert" and (u.first_name, u.last_name) == ("Nodira", "Saidova")
    assert guest.get("/ekspert/").status_code == 200


def test_dev_tools_hidden_in_production():
    app = create_app({**CONFIG, "DEV_TOOLS": False})
    c = app.test_client()
    assert c.get("/ekranlar").status_code == 404
    assert c.get("/_rol/admin").status_code == 404
    assert c.get("/kirish/google").status_code == 302
    assert c.get("/app/").status_code == 302
