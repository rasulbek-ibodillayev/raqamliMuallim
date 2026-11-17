"""Har bir ekran (/ekranlar ro'yxati) o'z roli bilan ochiladi va asosiy qismlari bor."""
import re

import pytest
from flask import url_for

from app.roles import REQUIRED
from app.views.meta import SCREENS

ALL = [(e, title, args) for _, items in SCREENS for e, title, args in items]


def _url(app, endpoint, args):
    with app.test_request_context():
        return url_for(endpoint, **args)


@pytest.mark.parametrize("endpoint,title,args", ALL, ids=[t for _, t, _ in ALL])
def test_screen_renders(app, as_role, endpoint, title, args):
    role = REQUIRED.get(endpoint.split(".")[0], "user")
    r = as_role(role).get(_url(app, endpoint, args))
    # Topilmagan sertifikat sahifasi 404 qaytaradi; /xato/<kod> namunalari esa oddiy sahifa (200)
    missing = endpoint == "auth.verify_certificate" and "topilmadi" in title
    assert r.status_code == (404 if missing else 200)
    html = r.get_data(as_text=True)
    assert "<title>" in html and 'name="csrf-token"' in html
    # Jinja yoki tarjima xatosi sahifaga chiqib qolmasin
    assert "{{" not in html and "{%" not in html
    body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    assert "%%" not in body and "%(" not in body


def test_screen_gallery(client):
    r = client.get("/ekranlar")
    assert r.status_code == 200
    assert r.get_data(as_text=True).count("screens-grid") >= 10


def test_unknown_page_is_404_page(client):
    r = client.get("/yoq-sahifa")
    assert r.status_code == 404
    assert "Sahifa topilmadi" in r.get_data(as_text=True)


def test_favicon(client):
    assert client.get("/favicon.ico").status_code == 200
