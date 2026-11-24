"""Ekspert taklifnomasi (admin → havola → ekspert parol o'rnatadi) va ekspert/admin profillari."""
import re

import pytest

from app.cli import demo_user
from tests.conftest import JSON

NEW = {"name": "Nodira Saidova", "contact": "93 555 11 22", "perms": ["questions"]}


def _invite_link(admin, **form):
    r = admin.post("/admin/ekspertlar", data={**NEW, **form}, headers=JSON)
    assert r.status_code == 200, r.json
    html = admin.get("/admin/ekspertlar").get_data(as_text=True)
    return r.json["message"], re.findall(r'data-copy-text="http://localhost(/taklif/[^"]+)"', html)


def test_admin_invites_expert_by_phone_and_email(as_role):
    admin = as_role("admin")
    msg, links = _invite_link(admin)
    assert "72 soat" in msg and len(links) == 1
    msg, links = _invite_link(admin, name="Ali Valiyev", contact="Ali.V@Maktab.uz")
    assert len(links) == 2


def test_invite_validation(app, as_role):
    admin = as_role("admin")
    with app.app_context():
        demo_user("expert")
    r = admin.post("/admin/ekspertlar", data={**NEW, "contact": "Ekspert@raqamlimuallim.uz"}, headers=JSON)
    assert r.status_code == 422 and "allaqachon" in r.json["errors"]["contact"]
    r = admin.post("/admin/ekspertlar", data={**NEW, "name": "Nodira", "contact": "123"}, headers=JSON)
    assert set(r.json["errors"]) == {"name", "contact"}


def test_expert_sets_password_via_link(app, as_role):
    _, (link,) = _invite_link(as_role("admin"))
    expert = app.test_client()                     # boshqa qurilma: sessiya yo'q
    page = expert.get(link)
    assert page.status_code == 200 and "Nodira Saidova" in page.get_data(as_text=True)
    r = expert.post(link, data={"pw": "qisqa", "pw2": "", "secret": "", "agree": ""}, headers=JSON)
    assert r.status_code == 422 and set(r.json["errors"]) == {"pw", "pw2", "secret", "agree"}
    r = expert.post(link, data={"pw": "yangi1234", "pw2": "yangi1234", "secret": "maktab", "agree": "1"}, headers=JSON)
    assert r.json["ok"] and r.json["redirect"] == "/ekspert/"
    assert expert.get("/ekspert/").status_code == 200          # endi ekspert sifatida kirgan
    assert expert.get(link).status_code == 410                 # havola bir martalik


def test_resend_and_cancel_revoke_old_link(app, as_role):
    admin = as_role("admin")
    _, (old,) = _invite_link(admin)
    iid = old.split("/")[-1].split("-")[0]
    admin.post("/admin/ekspertlar/taklif", data={"action": "resend", "id": iid}, headers=JSON)
    html = admin.get("/admin/ekspertlar").get_data(as_text=True)
    (new,) = re.findall(r'data-copy-text="http://localhost(/taklif/[^"]+)"', html)
    assert new != old and app.test_client().get(old).status_code == 404
    admin.post("/admin/ekspertlar/taklif", data={"action": "cancel", "id": iid}, headers=JSON)
    assert app.test_client().get(new).status_code == 404
    assert "Javob kutayotgan" not in admin.get("/admin/ekspertlar").get_data(as_text=True)


def test_link_has_no_personal_data(as_role):
    """Havolada ism yoki telefon bo'lmasin (URL loglarda va Referer'da ko'rinadi)."""
    _, (link,) = _invite_link(as_role("admin"))
    assert "Nodira" not in link and "935551122" not in link and "eyJ" not in link


def test_tampered_link_is_rejected(client):
    assert client.get("/taklif/soxta-token").status_code == 404


@pytest.mark.parametrize("role,base", [("expert", "/ekspert"), ("admin", "/admin")])
def test_staff_profile(as_role, role, base):
    c = as_role(role)
    html = c.get(base + "/profil").get_data(as_text=True)
    assert f'action="{base}/profil/parol"' in html and f'action="{base}/profil/aloqa/kod"' in html
    assert 'href="/parol-tiklash"' in html                     # parolni unutganda tiklash
    r = c.post(base + "/profil/malumotlar", data={"fn": "Zuhra", "ln": "Qodirova"}, headers=JSON)
    assert r.json["ok"] and r.json["redirect"] == base + "/profil"
    r = c.post(base + "/profil/parol", data={"old": "parol1234", "new": "yangi1234", "new2": "boshqa12"}, headers=JSON)
    assert r.status_code == 422 and "new2" in r.json["errors"]
    r = c.post(base + "/profil/aloqa/kod", data={"method": "email", "contact": "yangi@maktab.uz", "pw": "parol1234"}, headers=JSON)
    assert r.json["ok"]
    r = c.post(base + "/profil/aloqa/tasdiq", data={"otp": list("123456")}, headers=JSON)
    assert r.json["ok"] and r.json["message"] == "Email yangilandi"


def test_staff_profile_is_role_only(as_role):
    assert as_role("user").get("/ekspert/profil").status_code == 403
    assert as_role("expert").get("/admin/profil").status_code == 403
    assert 'href="/ekspert/profil"' in as_role("expert").get("/ekspert/").get_data(as_text=True)
