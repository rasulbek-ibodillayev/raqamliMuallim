"""Ko'p tillilik: standart o'zbekcha, ?til=ru ruscha, sessiyada eslab qolinadi."""
from tests.conftest import JSON


def test_default_uzbek(client):
    html = client.get("/kirish").get_data(as_text=True)
    assert '<html lang="uz"' in html and "Qaytganingizdan xursandmiz" in html


def test_russian_and_remembered(client):
    html = client.get("/kirish?til=ru").get_data(as_text=True)
    assert '<html lang="ru"' in html and "Рады вас видеть снова" in html
    html = client.get("/app/").get_data(as_text=True)
    assert "Главная" in html and "Учебный план" in html
    client.get("/kirish?til=uz")
    assert "Bosh sahifa" in client.get("/app/").get_data(as_text=True)


def test_unknown_language_ignored(client):
    assert '<html lang="uz"' in client.get("/kirish?til=fr").get_data(as_text=True)


def test_english(client):
    html = client.get("/app/?til=en").get_data(as_text=True)
    assert '<html lang="en"' in html and "Study plan" in html and "My results" in html


def test_karakalpak_removed(client):
    assert '<html lang="uz"' in client.get("/app/?til=kaa").get_data(as_text=True)


def test_language_select(client):
    html = client.get("/kirish?til=ru").get_data(as_text=True)
    assert '<select class="select select-sm" name="til"' in html
    assert '<option value="ru" lang="ru" selected>' in html and 'value="kaa"' not in html


def test_form_errors_translated(client):
    client.get("/kirish?til=ru")
    r = client.post("/kirish", data={"login": "", "pw": ""}, headers=JSON)
    assert r.json["errors"]["login"] == "Введите номер телефона или email"


def test_percent_signs_render(client):
    # Jinja newstyle gettext: "%%" → "%" bo'lishi kerak
    html = client.get("/test/natija?holat=qaytarildi").get_data(as_text=True)
    assert "70%" in html and "70%%" not in html
