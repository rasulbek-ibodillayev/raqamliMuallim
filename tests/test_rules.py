"""Biznes qoidalari: e'tirozni tahrirlash, testni bekor qilish, navbat filtrlari, tarjima yo'nalishi."""
import importlib.util
from pathlib import Path

from tests.conftest import JSON


def test_objection_edit_only_while_in_review(as_role):
    c = as_role("user")
    assert c.post("/app/etirozlarim/3/tahrir", data={"reason": "unclear", "note": "x"}, headers=JSON).json["ok"]
    r = c.post("/app/etirozlarim/3/tahrir", data={"reason": "other", "note": ""}, headers=JSON)
    assert r.status_code == 422 and "note" in r.json["errors"]
    r = c.post("/app/etirozlarim/2/tahrir", data={"reason": "unclear"}, headers=JSON)   # qabul qilingan
    assert r.status_code == 422


def test_only_optional_unfinished_test_can_be_cancelled(as_role):
    c = as_role("user")
    assert c.post("/app/testlar/ixtiyoriy-1/bekor", headers=JSON).json["ok"]
    assert c.post("/app/testlar/oylik-noyabr/bekor", headers=JSON).status_code == 422


def test_unfinished_mandatory_test_blocks(as_role):
    html = as_role("user").get("/app/testlar?oylik=1").get_data(as_text=True)
    assert "Majburiy test yakunlanmagan" in html
    assert "Majburiy test yakunlanmagan" not in as_role("user").get("/app/testlar").get_data(as_text=True)


def test_queue_filters_by_topic_and_lesson(as_role):
    c = as_role("expert")
    html = c.get("/ekspert/navbat?mavzu=Sanoq+sistemalari&dars=O‘n+oltilik").get_data(as_text=True)
    assert html.count("q-review") == 3 and "Kompyuter tarmoqlari</b>" not in html
    assert c.get("/ekspert/navbat?q=yoq-matn").get_data(as_text=True).count("q-review") == 0


def test_translation_routes_through_russian_when_uzbek_unsupported():
    path = Path(__file__).resolve().parent.parent / "scripts" / "translate.py"
    spec = importlib.util.spec_from_file_location("translate_script", path)
    tr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tr)
    tr._SUPPORTED = {"ru": {"en"}, "en": {"ru"}}          # LibreTranslate: uz yo'q
    assert tr.route("en", "Saqlash", {"Saqlash": "Сохранить"}) == ("Сохранить", "ru")
    assert tr.route("en", "Saqlash", {}) == (None, None)


def test_plan_lesson_results_add_up_to_topic_test():
    from app import mock as m
    for t in m.LEARN_PLAN:
        if t.get("test"):
            ok = sum(l["ok"] for l in t["lessons"])
            n = sum(l["n"] for l in t["lessons"])
            assert n == t["test"]["n"] and round(ok / n * 100) == t["test"]["pct"], t["name"]
