"""O'quv reja, bosh sahifa, xatolar analitikasi va majburiy testlar jadvali — bazadagi natijalardan (5b)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.cli import demo_user
from app.extensions import db
from app.models import Subtopic, TestAttempt, Topic, User, UserTopicProgress
from app.services import attempts as at
from app.services import catalog
from app.services import plan as pl
from app.services import test_builder as tb
from app.services.content_import import load
from app.services.timefmt import now

pytestmark = pytest.mark.usefixtures("fresh_content")
BLOCK = [{"kind": "text", "data": {"body": "x"}}]


def _q(text, d="easy"):
    return {"type": "single", "difficulty": d, "text": text, "data": {"options": ["a", "b"]}, "answer": {"keys": [0]}}


def content(n=7, lessons=2):
    """n ta mavzu (T1…), har birida lessons ta dars (T1a, T1b), har darsda 4 ta savol."""
    load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [
        {"title": f"T{i}", "est_minutes": 20, "subtopics": [
            {"title": f"T{i}{'abc'[k]}", "blocks": BLOCK, "questions": [_q(f"q{i}{k}{j}", d) for j, d in enumerate(
                ("easy", "easy", "medium", "hard"))]} for k in range(lessons)]} for i in range(1, n + 1)]}]}, status="approved")


@pytest.fixture()
def ctx(app):
    with app.app_context():
        content()
        yield


def me() -> User:
    return demo_user("user")


def topic(i):
    return db.session.scalar(select(Topic.id).where(Topic.title == f"T{i}"))


def sub(name):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == name))


def run(kind, good=True, days=0, **kw):
    a, fresh = tb.get_or_start(me().id, kind, **kw)
    assert fresh
    while a.status == "in_progress":
        at.save_answers(a, [{"pos": p, "v": 0 if good else 1, "at": 1} for p in at.active_positions(a)])
        at.finish(a, a.stage)
    if days:
        a.started_at -= timedelta(days=days)
        a.finished_at -= timedelta(days=days)
        db.session.commit()
    return a


def master(*ids, status="done", pct=80, flags=()):
    for i in ids:
        db.session.merge(UserTopicProgress(user_id=me().id, topic_id=topic(i), status=status, best_pct=pct, flags=list(flags)))
    db.session.commit()


def plan(**kw):
    return pl.build(me(), sunday=kw.pop("sunday", False))


def states(p):
    return [t["state"] for t in p.topics]


# ---------------- Mavzular ----------------

def test_fresh_plan_opens_first_topic_only(ctx):
    p = plan()
    assert states(p) == ["current"] + ["locked"] * 6
    assert p.current["name"] == "T1" and p.current["min"] == 24              # 2 dars × 10 daqiqa + 4 savollik mavzu testi
    assert [t["state"] for t in p.interims] == ["locked", "locked"] and p.final["state"] == "locked"
    assert p.daily["state"] == "due" and p.monthly is None and not p.has_results
    assert p.summary["done"] == 0 and p.summary["total"] == 7 and p.summary["next_control"] == "3 mavzu"
    assert [i.get("type", "t") for i in p.items][:4] == ["t", "daily", "t", "t"]


def test_lessons_then_topic_test_then_next_topic(ctx):
    run("lesson", good=False, subtopic_id=sub("T1a"))
    p = plan()
    assert p.current["passed"] == 0 and pl.next_step(p)["lesson"]["name"] == "T1a" and "0%" in pl.next_step(p)["text"]
    run("lesson", subtopic_id=sub("T1a"))
    p = plan()
    x = p.current["lessons"][0]
    assert x["pct"] == 100 and x["tries"] == 2 and p.current["read"] == 50 and p.has_results
    assert pl.next_step(p)["lesson"]["name"] == "T1b"
    run("lesson", subtopic_id=sub("T1b"))
    assert pl.next_step(plan())["kind"] == "topic_test"
    run("topic", topic_id=topic(1))
    p = plan()
    assert states(p)[:3] == ["done", "current", "locked"] and p.topics[0]["pct"] == 100
    assert pl.next_step(p)["label"] == "Keyingi mavzu" and p.summary["avg"] == 100


def test_failed_topic_test_keeps_topic_current(ctx):
    run("topic", good=False, topic_id=topic(1))
    p = plan()
    assert p.current["name"] == "T1" and p.current["relearn"] and p.current["test"]["pct"] == 0


def test_diagnostic_topics_are_excluded_until_relearn(ctx):
    master(1, 2, status="solid", pct=95, flags=["diagnostic"])
    p = plan()
    assert [x["name"] for x in p.excluded] == ["T1", "T2"] and p.current["name"] == "T3"
    assert p.summary["done"] == 2 and p.summary["total"] == 7
    master(1, status="relearn", pct=95, flags=["diagnostic"])                    # oraliq sinovda yiqildi — rejaga qaytadi
    assert plan().current["name"] == "T1"


# ---------------- Oraliq, oylik, kunlik, haftalik, yakuniy ----------------

def test_interim_blocks_next_topic_until_passed(ctx, app, as_role):
    master(1, 2, 3)
    p = plan()
    assert p.interims[0]["state"] == "due" and p.blocker is p.interims[0]
    assert states(p)[3] == "locked" and "ochiladi" in p.topics[3]["note"]
    assert pl.next_step(p)["kind"] == "control" and p.summary["next_control"] == "Navbati keldi"
    assert pl.today_items(p)[0]["test"] == "interim"
    c = as_role("user")
    html = c.get("/app/nazorat").get_data(as_text=True)
    assert all(f">T{i}<" in html for i in (1, 2, 3)) and ">T4<" not in html
    a = run("interim")
    tops = {db.session.get(Subtopic, s).topic_id for s in db.session.scalars(
        select(Subtopic.id).where(Subtopic.topic_id.in_([topic(i) for i in (1, 2, 3)])))}
    from app.models import Question
    got = {db.session.get(Subtopic, db.session.get(Question, i.question_id).subtopic_id).topic_id for i in a.items}
    assert got == tops                                                            # aynan shu uch mavzudan
    p = plan()
    assert p.interims[0]["state"] == "done" and p.interims[0]["rid"] == a.id and p.blocker is None
    assert p.current["name"] == "T4" and p.current["state"] == "current"
    assert c.get("/app/nazorat").status_code == 302                               # navbat o'tdi


def test_interim_does_not_block_started_topic(ctx):
    master(1, 2, 3)
    run("lesson", subtopic_id=sub("T4a"))
    p = plan()
    assert p.blocker is None and p.current["state"] == "current" and p.interims[0]["state"] == "due"


def test_interim_uses_its_own_group(ctx):
    master(1, 2, 3)
    run("interim")
    master(4, 5, 6)
    db.session.merge(UserTopicProgress(user_id=me().id, topic_id=topic(1), status="solid", best_pct=99))   # eng yangi updated_at
    db.session.commit()
    assert pl.interim_topics(me().id) == [topic(i) for i in (4, 5, 6)]


def test_monthly_due_after_30_days(ctx):
    master(1, 2)
    run("daily", days=29)
    assert plan().monthly["state"] == "locked"
    run("daily", days=30)
    p = plan()
    assert p.monthly["state"] == "due" and p.blocker is p.monthly and p.monthly in p.items
    run("monthly")
    p = plan()
    assert p.monthly["state"] == "locked" and p.blocker is None and p.monthly not in p.items


def test_daily_and_weekly(ctx):
    assert plan(sunday=True).items[1]["type"] == "daily" and not any(i.get("type") == "weekly" for i in plan(sunday=True).items)
    master(1)
    assert any(i.get("type") == "weekly" and i["state"] == "due" for i in plan(sunday=True).items)
    assert not any(i.get("type") == "weekly" for i in plan(sunday=False).items)
    a = run("daily")
    p = plan()
    assert p.daily["state"] == "done" and p.daily["rid"] == a.id and pl.today_items(p)[-1]["done"]
    a.finished_at -= timedelta(days=1)
    db.session.commit()
    assert plan().daily["state"] == "due"


def test_final_opens_when_everything_mastered(ctx):
    master(*range(1, 8))
    for _ in range(2):
        run("interim")
    p = plan()
    assert p.current is None and p.final["state"] == "due" and pl.next_step(p)["kind"] == "final"
    run("final")
    p = plan()
    assert p.final["state"] == "done" and pl.next_step(p)["kind"] == "finished"


# ---------------- Sanalar va prognoz ----------------

def test_dates_follow_exam_date(ctx):
    u, today = me(), now().date()
    p = plan()
    assert [t["start"] for t in p.topics[:3]] == [today + timedelta(days=d) for d in (0, 2, 4)]
    assert p.summary["exam"] is None and p.summary["per_day"] == "2 kunda 1 mavzu"
    u.exam_date = today + timedelta(days=pl.RESERVE_DAYS + 70)                   # 70 kun / 7 mavzu = 10 kunda bitta
    db.session.commit()
    p = plan()
    assert p.topics[1]["start"] == today + timedelta(days=10) and p.summary["days_left"] == 73
    u.exam_date = today + timedelta(days=1)                                      # ulgurmaydi: kuniga 7 ta
    db.session.commit()
    assert plan().summary["per_day"] == "≈ 7 mavzu"


def test_readiness_states(ctx):
    u, today = me(), now().date()
    r = pl.readiness(u, plan())
    assert (r["pct"], r["state"], r["forecast"]) == (0, "none", None)
    for i in (1, 2):
        run("topic", topic_id=topic(i))                                           # 14 kunda 2 mavzu → qolgan 5 taga 35 kun
    assert pl.readiness(u, plan())["state"] == "free"
    for days, state, margin in ((40, "ok", 5), (35, "risk", 0), (30, "late", -5)):
        u.exam_date = today + timedelta(days=days)
        db.session.commit()
        r = pl.readiness(u, plan())
        assert (r["state"], r["margin_days"]) == (state, margin)
    assert r["pct"] == round(200 / 7)


# ---------------- Sahifalar ----------------

def test_home_for_new_user_then_plan(ctx, as_role):
    c = as_role("user")
    html = c.get("/app/").get_data(as_text=True)
    assert "3 qadamda tayyorgarlikni boshlang" in html and "0 / 3" in html
    run("diagnostic", good=False)
    assert "1 / 3" in c.get("/app/").get_data(as_text=True)
    run("lesson", subtopic_id=sub("T1a"))
    html = c.get("/app/").get_data(as_text=True)
    assert "3 qadamda" not in html and "Darsni davom ettirish" in html and "«T1» mavzusi bo‘yicha reja" in html
    assert f'href="/app/dars/{topic(1)}#k{sub("T1b")}"' in html
    assert "Attestatsiya sanasi hali belgilanmagan" in html


def test_plan_page(ctx, as_role):
    run("lesson", subtopic_id=sub("T1a"))
    html = as_role("user").get("/app/reja").get_data(as_text=True)
    assert "T7" in html and "Oraliq sinov testi: 1–3 mavzular" in html and "1 / 2" in html
    rid = db.session.scalar(select(TestAttempt.id))
    assert f"/app/natijalar/{rid}" in html and f"/app/dars/{topic(1)}#k{sub('T1b')}" in html
    assert "turi=dars" not in html                                                # dars testi dars oxiridan boshlanadi
    assert "90000" not in html                                                    # namunaviy natija havolalari yo'q


def test_plan_keeps_test_button_when_lesson_has_no_blocks(app, as_role):
    with app.app_context():
        load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [
            {"title": "T1", "subtopics": [{"title": "T1a", "questions": [_q("a")]}]}]}]}, status="approved")
        sid = sub("T1a")
    html = as_role("user").get("/app/reja").get_data(as_text=True)
    assert f"/test/savol?turi=dars&amp;dars={sid}" in html and "Darsni ochish" not in html


def test_empty_plan(app, as_role):
    c = as_role("user")
    assert "Reja hali tayyor emas" in c.get("/app/reja").get_data(as_text=True)
    for url in ("/app/", "/app/testlar", "/app/xatolar", "/app/diagnostika", "/app/tutor", "/app/eslatmalar"):
        assert c.get(url).status_code == 200, url


def test_tests_page_schedule(ctx, as_role):
    c = as_role("user")
    html = c.get("/app/testlar").get_data(as_text=True)
    assert "Mavzu testi: T1" in html and "Yakuniy diagnostika" in html and "Bugun ochiq" in html
    for s in ("T1a", "T1b"):
        run("lesson", subtopic_id=sub(s))
    assert f"/test/savol?turi=mavzu&amp;mavzu={topic(1)}" in c.get("/app/testlar").get_data(as_text=True)


def test_errors_page(ctx, as_role):
    c = as_role("user")
    assert "Tuzatilmagan xato yo‘q" in c.get("/app/xatolar").get_data(as_text=True)
    a = run("lesson", good=False, subtopic_id=sub("T1a"))
    run("lesson", good=False, subtopic_id=sub("T1a"))
    items, total = catalog.error_items(me().id)
    assert total == len(items) == 4 and {e["section"] for e in items} == {"T1 · T1a"}
    assert [e["wrong"] for e in items] == [2] * 4            # takrorsiz 3 + 1 savol; shu kichik mavzuda 2 ta testda xato
    html = c.get("/app/xatolar").get_data(as_text=True)
    assert "Xato qilingan savollar · 4" in html and "2 marta xato" in html and a.id


def test_lesson_without_questions_does_not_block(app, as_role):
    with app.app_context():
        load({"course": {"slug": "t", "title": "T"}, "sections": [{"title": "S", "topics": [{"title": "T1", "subtopics": [
            {"title": "T1a", "blocks": BLOCK}, {"title": "T1b", "blocks": BLOCK, "questions": [_q("a"), _q("b")]}]}]}]},
             status="approved")
        tid = topic(1)
        html = as_role("user").get(f"/app/dars/{tid}").get_data(as_text=True)
        assert "Dars testi tayyorlanmoqda" in html and "Keyingi darslar yopiq" not in html
        p = plan()
        assert p.current["passed"] == 1 and pl.next_step(p)["lesson"]["name"] == "T1b"
        assert tb.current_lesson(me().id) == sub("T1b")


def test_samples_closed_in_production(ctx, app, as_role):
    c = as_role("user")
    assert "LEARN" not in c.get("/app/reja?namuna=1").get_data(as_text=True)
    assert "Python: sikllar" in c.get("/app/reja?namuna=1").get_data(as_text=True)
    app.config["DEV_TOOLS"] = False
    assert "Python: sikllar" not in c.get("/app/reja?namuna=1").get_data(as_text=True)
    assert c.get("/app/natijalar/900009").status_code == 404
    assert c.get("/app/dars").location.endswith(f"/app/dars/{topic(1)}")
    assert c.get("/app/nazorat?namuna=1").status_code == 302


def test_tutor_chat_is_bound_to_plan_topic(ctx, app, as_role):
    """Suhbat qurilmada saqlanadi; server faqat foydalanuvchi va joriy mavzu id'sini beradi (mavzu o'zgarsa — o'chadi)."""
    import re
    c = as_role("user")

    def meta(url="/app/tutor"):
        m = re.search(r'<meta name="rm-learner" data-uid="(\d+)" data-topic="(\d+)">', c.get(url).get_data(as_text=True))
        return int(m.group(1)), int(m.group(2))

    assert meta() == (me().id, topic(1))
    assert meta(f"/app/dars/{topic(3)}") == (me().id, topic(1))                 # boshqa mavzu darsini ko'rish o'chirmaydi
    master(1)
    assert meta() == (me().id, topic(2))                                          # keyingi mavzuga o'tildi
    master(*range(1, 8))
    assert meta() == (me().id, 0)
    assert "rm-learner" not in as_role("expert").get("/ekspert/navbat").get_data(as_text=True)


def test_tutor_sample_chat_only_in_dev(ctx, app, as_role):
    c = as_role("user")
    assert 'data-role="ai"' in c.get("/app/tutor").get_data(as_text=True)
    app.config["DEV_TOOLS"] = False
    assert 'data-role="ai"' not in c.get("/app/tutor").get_data(as_text=True)
