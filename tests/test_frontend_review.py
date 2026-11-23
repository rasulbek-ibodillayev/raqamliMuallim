"""Frontend tekshiruvida topilgan xatolar qaytmasligi uchun."""
import collections
import json
import re


def _ids(html):
    return [i for i, n in collections.Counter(re.findall(r'\sid="([^"]+)"', html)).items() if n > 1]


def test_no_duplicate_ids(as_role):
    for role, url in [("user", "/app/profil"), ("expert", "/ekspert/navbat")]:
        html = as_role(role).get(url).get_data(as_text=True)
        assert _ids(html) == [], url


def test_profile_logout_clears_session_and_device_data(as_role):
    c = as_role("user")
    assert 'href="/chiqish"' in c.get("/app/profil").get_data(as_text=True)
    r = c.get("/chiqish")
    assert r.status_code == 302 and "storage" in r.headers["Clear-Site-Data"]
    with c.session_transaction() as s:
        assert "role" not in s


def test_bad_query_param_is_not_server_error(as_role):
    assert as_role("user").get("/app/?qadam=abc").status_code == 200


def test_js_strings_are_translated(client):
    html = client.get("/kirish?til=ru").get_data(as_text=True)
    raw = re.search(r'<script type="application/json" id="rm-i18n">(.*?)</script>', html, re.S).group(1)
    t = json.loads(raw)
    assert t["breakOver"] == "Перерыв окончен. Продолжаем!" and "{q}" in t["tutorDemo"]


def test_alpine_translations_are_json_quoted(client):
    # Tarjimada apostrof bo'lsa ham JS buzilmasin: matn JSON (&#34;…&#34;) ko'rinishida beriladi
    html = client.get("/parol-tiklash").get_data(as_text=True)
    assert 'x-text="sent ? &#34;Qayta yuborish&#34; : &#34;Kod yuborish&#34;"' in html


def _css():
    from pathlib import Path
    return (Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "app.css").read_text(encoding="utf8")


def test_ai_background_in_app_and_panels(as_role):
    # Tuzatish 4.1: nuqtalar foni kirish sahifalaridan tashqari ilova va panellarda ham bor
    for role, url in [("user", "/app/"), ("expert", "/ekspert/navbat"), ("admin", "/admin/")]:
        html = as_role(role).get(url, follow_redirects=True).get_data(as_text=True)
        assert 'class="ai-bg"' in html and "js/particles.js" in html, url
    # Test va dars (fokus rejimi) chalg'itmasligi uchun fonsiz
    html = as_role("user").get("/test/savol?tur=yopiq").get_data(as_text=True)
    assert 'class="ai-bg"' not in html


def test_ai_background_follows_rest_strain():
    # Dam olish rad etilganda (html[data-strain]) nuqtalar rangi fonga mos iliq tusga o'tadi
    css = _css()
    assert ':root[data-strain="1"] { --pt-1:' in css and ':root[data-strain="2"] { --pt-1:' in css
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "particles.js").read_text(encoding="utf8")
    assert '"data-strain"' in js and "--pt-1" in js


def test_plan_test_card_wraps_on_phone(as_role):
    # Tuzatish 4.2: navbati kelgan oylik test kartasida matn tor ustunga siqilmaydi
    html = as_role("user").get("/app/reja?oylik=1").get_data(as_text=True)
    assert "Oylik test" in html and "plan-test-card" in html
    assert ".plan-test-card > .row > .grow { flex: 1 1 220px; }" in _css()
