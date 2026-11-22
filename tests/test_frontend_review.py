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
