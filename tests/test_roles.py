"""Rollar: har bir rol faqat o'z paneliga kiradi."""
import pytest

from tests.conftest import JSON

PAGES = {"user": "/app/", "expert": "/ekspert/", "admin": "/admin/"}


@pytest.mark.parametrize("role", PAGES)
@pytest.mark.parametrize("target", PAGES)
def test_role_matrix(as_role, role, target):
    r = as_role(role).get(PAGES[target])
    assert r.status_code == (200 if role == target else 403)


def test_default_role_is_user(client):
    assert client.get("/app/").status_code == 200
    assert client.get("/admin/").status_code == 403


def test_public_pages_for_everyone(as_role):
    for role in PAGES:
        c = as_role(role)
        for url in ["/", "/kirish", "/maxfiylik", "/s/INF-2026-000123"]:
            assert c.get(url).status_code == 200, (role, url)


def test_login_picks_role(client):
    r = client.post("/kirish", data={"login": "admin@raqamlimuallim.uz", "pw": "x"}, headers=JSON)
    assert r.json["redirect"] == "/admin/"
    r = client.post("/kirish", data={"login": "ekspert@raqamlimuallim.uz", "pw": "x"}, headers=JSON)
    assert r.json["redirect"] == "/ekspert/"
    assert client.get("/ekspert/").status_code == 200


def test_logout_clears_role(as_role):
    c = as_role("admin")
    c.get("/chiqish")
    assert c.get("/admin/").status_code == 403


def test_panels_have_no_cross_links(as_role):
    admin = as_role("admin").get("/admin/").get_data(as_text=True)
    assert 'href="/ekspert' not in admin
    expert = as_role("expert").get("/ekspert/").get_data(as_text=True)
    assert 'href="/admin' not in expert
