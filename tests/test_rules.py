"""Biznes qoidalari: navbat filtrlari, tarjima yo'nalishi, dars va mavzu testi o'lchamlari."""
import importlib.util
from pathlib import Path


def test_queue_filters_by_topic_and_lesson(app, as_role):
    # Namunaviy kontentda 5 ta AI savoli: 3 tasi «Axborot va kodlash» → «Sanoq sistemalari» darsida
    from sqlalchemy import select

    from app.extensions import db
    from app.models import Section, Topic
    with app.app_context():
        sec = db.session.scalar(select(Section.id).where(Section.title == "Axborot va kodlash"))
        top = db.session.scalar(select(Topic.id).where(Topic.title == "Sanoq sistemalari"))
    c = as_role("expert")
    assert c.get("/ekspert/navbat").get_data(as_text=True).count("q-review") == 5
    html = c.get(f"/ekspert/navbat?mavzu={sec}&dars={top}").get_data(as_text=True)
    assert html.count("q-review") == 3 and "Tarmoq texnologiyalari</b>" not in html
    assert c.get("/ekspert/navbat?q=yoq-matn").get_data(as_text=True).count("q-review") == 0
    assert c.get("/ekspert/navbat?daraja=Qiyin").get_data(as_text=True).count("q-review") == 1


def test_translation_routes_through_russian_when_uzbek_unsupported():
    path = Path(__file__).resolve().parent.parent / "scripts" / "translate.py"
    spec = importlib.util.spec_from_file_location("translate_script", path)
    tr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tr)
    tr._SUPPORTED = {"ru": {"en"}, "en": {"ru"}}          # LibreTranslate: uz yo'q
    assert tr.route("en", "Saqlash", {"Saqlash": "Сохранить"}) == ("Сохранить", "ru")
    assert tr.route("en", "Saqlash", {}) == (None, None)


def test_plan_lesson_and_topic_test_sizes():
    """Har dars testi — 3 savol; mavzu testi — 2 × darslar soni."""
    from app import mock as m
    for t in m.LEARN_PLAN:
        if t["kind"] != "topic":
            continue
        assert all(l["n"] == 3 for l in t["lessons"]), t["name"]
        if t.get("test"):
            assert t["test"]["n"] == 2 * len(t["lessons"]), t["name"]
    assert [m.lesson_decision(p) for p in (69, 70, 89, 90)] == ["relearn", "recommend", "recommend", "pass"]
    lessons, minutes = m.diagnostic_estimate()
    assert lessons == sum(len(t.get("lessons", [])) for t in m.LEARN_PLAN) + sum(m.PLAN_EXCLUDED_LESSONS.values())
    assert minutes == lessons * m.DIAG_SEC_PER_LESSON // 60


def test_next_lessons_hidden_until_lesson_test_passed(client):
    from app.views.user import open_lessons
    assert open_lessons([100, 86, None, None]) == 3       # joriy — 3-dars, 4-dars yopiq
    assert open_lessons([100, 40, None]) == 2              # 2-dars testi < 70% — keyingisi ko'rinmaydi
    assert open_lessons([100, 90]) == 2
    html = client.get("/app/dars").get_data(as_text=True)
    assert 'id="elif"' in html and 'id="nested"' not in html and "Keyingi darslar yopiq" in html
    assert "data-end-gate" not in html                     # mavzu testi — barcha dars testlaridan keyin
    html = client.get("/app/dars?holat=qayta").get_data(as_text=True)
    assert 'id="nested"' in html and "data-end-gate" in html and "Keyingi darslar yopiq" not in html
