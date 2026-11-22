"""Rollar: har bir rol faqat o'z paneliga kiradi."""
import pytest

from tests.conftest import JSON

PAGES = {"user": "/app/", "expert": "/ekspert/", "admin": "/admin/"}


@pytest.mark.parametrize("role", PAGES)
@pytest.mark.parametrize("target", PAGES)
def test_role_matrix(as_role, role, target):
    r = as_role(role).get(PAGES[target])
    assert r.status_code == (200 if role == target else 403)


def test_guest_is_sent_to_login(guest):
    for url in ["/app/", "/app/reja", "/ekspert/", "/admin/"]:
        r = guest.get(url)
        assert r.status_code == 302 and r.headers["Location"].startswith("/kirish?next="), url
    r = guest.post("/api/urinish/00000000-0000-4000-8000-000000000000/javoblar", json={})
    assert r.status_code == 401 and r.json["ok"] is False


def test_public_pages_for_everyone(as_role):
    for role in PAGES:
        c = as_role(role)
        for url in ["/", "/kirish", "/maxfiylik", "/s/INF-2026-000123"]:
            assert c.get(url).status_code == 200, (role, url)


def test_login_role_comes_from_account(app, guest):
    from app.cli import demo_user
    with app.app_context():
        for role in ("user", "expert", "admin"):
            demo_user(role)
    r = guest.post("/kirish", data={"login": "admin@raqamlimuallim.uz", "pw": "parol1234"}, headers=JSON)
    assert r.json["redirect"] == "/admin/"
    r = guest.post("/kirish", data={"login": "ekspert@raqamlimuallim.uz", "pw": "parol1234"}, headers=JSON)
    assert r.json["redirect"] == "/ekspert/"
    assert guest.get("/ekspert/").status_code == 200
    # Login matnidagi "admin" so'zi endi rol bermaydi
    r = guest.post("/kirish", data={"login": "admin@boshqa.uz", "pw": "parol1234"}, headers=JSON)
    assert r.status_code == 422


def test_logout_ends_session(as_role):
    c = as_role("admin")
    c.get("/chiqish")
    assert c.get("/admin/").status_code == 302


def test_panels_have_no_cross_links(as_role):
    admin = as_role("admin").get("/admin/").get_data(as_text=True)
    assert 'href="/ekspert' not in admin
    expert = as_role("expert").get("/ekspert/").get_data(as_text=True)
    assert 'href="/admin' not in expert
