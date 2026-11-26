"""10c: oflayn paket — tayyor testlar, band savollar, sinxronlash, o'chirish, sahifalar va Service Worker."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.cli import demo_user
from app.extensions import db
from app.models import ContentBlock, Question, Subtopic, TestAttempt, Topic, UserSeen
from app.services import catalog, offline, progress, tasks
from app.services import attempts as at
from app.services import test_builder as tb
from tests.conftest import JSON

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
PACK = {"X-RM-Pack": "1"}


@pytest.fixture()
def topic(app) -> int:
    """Darsi va dars testlari bor mavzu (testlilari eng ko'pi)."""
    with app.app_context():
        best = None
        for tid in db.session.scalars(select(Topic.id).where(Topic.is_published.is_(True))):
            view = catalog.lesson_view(tid)
            if view and view["parts"]:
                n = sum(x["testable"] for x in catalog.lessons_by_topic(tid)[tid])
                best = max(best or (0, 0), (n, tid))
        assert best[0] >= 1
        return best[1]


def build(client, topic):
    return client.post(f"/api/oflayn/{topic}", headers=JSON)


def attempts(status="offline"):
    db.session.rollback()
    return list(db.session.scalars(select(TestAttempt).where(TestAttempt.status == status).order_by(TestAttempt.id)))


def uid(app):
    return demo_user("user").id


# ---------------- Paket ----------------

def test_pack_lists_pages_and_reserves_tests(app, client, topic):
    r = build(client, topic)
    j = r.json
    assert r.status_code == 200 and j["page"] == f"/app/dars/{topic}" and j["urls"][0] == j["page"]
    assert j["tests"] >= 1 and j["limit"] == 30 * 1024 * 1024 and j["days"] == 30
    with app.app_context():
        rows = attempts()
        assert len(rows) == j["tests"] and {f"/test/urinish/{a.client_uuid}" for a in rows} <= set(j["urls"])
        assert all(a.kind == "lesson" and a.topic_id == topic and len(a.items) == a.total for a in rows)
        assert tb.unfinished(uid(app)) == []                          # «yakunlanmagan test» emas
        assert db.session.scalar(select(func.count()).select_from(UserSeen)) == 0      # hali berilgan emas
    assert "Majburiy test yakunlanmagan" not in client.get("/app/testlar").text


def test_every_url_of_pack_opens_without_redirect(client, topic):
    for u in build(client, topic).json["urls"]:
        r = client.get(u, headers=PACK)
        assert r.status_code == 200, u
        r.close()


def test_second_download_reuses_tests(app, client, topic):
    a, b = build(client, topic).json, build(client, topic).json
    assert a["urls"] == b["urls"]
    with app.app_context():
        assert len(attempts()) == a["tests"]


def test_pack_has_no_answer_key(app, client, topic):
    urls = build(client, topic).json["urls"]
    with app.app_context():
        secrets = {str(q.explanation) for a in attempts() for q in db.session.scalars(
            select(Question).where(Question.id.in_([i.question_id for i in a.items]))) if q.explanation}
    from markupsafe import escape
    for u in urls:
        if u.startswith("/test/"):
            html = client.get(u, headers=PACK).text
            assert "&#34;keys&#34;" not in html and not any(s in html or str(escape(s)) in html for s in secrets)


def test_reserved_questions_are_not_given_elsewhere(app, client, topic):
    build(client, topic)
    with app.app_context():
        held = {i.question_id for a in attempts() for i in a.items}
        for kind, kw in (("topic", {"topic_id": topic}), ("daily", {}), ("optional", {"topic_ids": [topic]})):
            try:
                spec = tb.build(uid(app), kind, **kw)
            except tb.Unavailable:
                continue
            assert not held & {p.question_id for part in spec.parts for p in part}, kind
        db.session.rollback()


def test_online_start_uses_prepared_test(app, client, topic):
    build(client, topic)
    with app.app_context():
        a = attempts()[0]
        sid, u, ids = a.subtopic_id, str(a.client_uuid), [i.question_id for i in a.items]
    assert client.get(f"/test/savol?turi=dars&dars={sid}").location.endswith(u)
    with app.app_context():
        a = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == uuid.UUID(u)))
        assert a.status == "in_progress" and a.deadline_at and not any(
            db.session.scalar(select(offline.seen.is_new(uid(app))).where(Question.id == q)) for q in ids)
    assert f"/test/urinish/{u}" in build(client, topic).json["urls"]    # boshlangani ham paketda qoladi


def test_question_withdrawn_from_bank_replaces_prepared_test(app, client, topic):
    old = build(client, topic).json["urls"]
    with app.app_context():
        qid = attempts()[0].items[0].question_id
        db.session.execute(text("UPDATE questions SET status = 'paused' WHERE id = :i"), {"i": qid})
        db.session.commit()
    try:
        new = build(client, topic).json["urls"]
        assert old != new
        with app.app_context():
            assert qid not in {i.question_id for a in attempts() for i in a.items}
    finally:
        with app.app_context():
            db.session.execute(text("UPDATE questions SET status = 'approved' WHERE id = :i"), {"i": qid})
            db.session.commit()


def test_mastered_lessons_need_no_test(app, client, topic):
    n = build(client, topic).json["tests"]
    with app.app_context():
        a = attempts()[0]
        offline.activate(a)
        for i in a.items:
            q = db.session.get(Question, i.question_id)
            ans = q.answer
            v = ans.get("value") if q.type == "open" else ans.get("pairs") if q.type == "matching" else (
                ans["keys"][0] if q.type == "single" else ans["keys"])
            i.answer = {"v": v}
        at.finish(a)
        assert a.score_pct == 100
    assert build(client, topic).json["tests"] == n - 1


# ---------------- Sinxronlash ----------------

def test_offline_result_is_graded_after_sync(app, client, topic):
    build(client, topic)
    with app.app_context():
        a = attempts()[0]
        u, total = a.client_uuid, a.total
    body = {"kind": "lesson", "answers": [{"pos": p, "v": None if p else 0, "t": 1000, "at": 5} for p in range(total)]}
    assert client.post(f"/api/urinish/{u}/javoblar", json=body).json["ok"]
    with app.app_context():
        assert attempts("in_progress")[0].client_uuid == u
    r = client.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson", "stage": None}).json
    assert r["ok"] and r["result_url"] == f"/test/urinish/{u}/natija"
    assert client.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson", "stage": None}).json["ok"]
    assert client.get(r["result_url"]).status_code == 200
    with app.app_context():
        a = attempts("submitted")[0]
        assert a.score_pct is not None and len(a.items) == total


def test_finish_alone_also_starts_it(app, client, topic):
    build(client, topic)
    with app.app_context():
        u = attempts()[0].client_uuid
    assert client.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson", "stage": None}).json["ok"]
    with app.app_context():
        assert attempts("submitted")[0].score_pct == 0


def test_sync_works_while_other_mandatory_test_is_open(app, client, topic):
    build(client, topic)
    with app.app_context():
        u = attempts()[0].client_uuid
    client.get("/test/savol?turi=kunlik")
    assert client.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson", "stage": None}).json["ok"]


def test_other_user_cannot_touch_prepared_test(app, client, topic):
    build(client, topic)
    with app.app_context():
        from app.models import User
        u = attempts()[0].client_uuid
        x = User(first_name="A", last_name="B", email="b@b.uz")
        db.session.add(x)
        db.session.commit()
        sid = x.get_id()
    c = app.test_client()
    with c.session_transaction() as s:
        s["_user_id"], s["_fresh"] = sid, True
    assert c.get(f"/test/urinish/{u}").status_code == 404
    assert c.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson"}).status_code == 403
    assert c.post(f"/api/oflayn/{topic}/ochirish").json["n"] == 0
    with app.app_context():
        assert attempts()


def test_fixed_key_reaches_prepared_tests(app, client, topic):
    """E'tirozdan keyin savol chiqarilsa, tayyor testdan ham chiqadi."""
    from app.services import recalc
    build(client, topic)
    with app.app_context():
        a = attempts()[0]
        pos, qid = a.items[0].position, a.items[0].question_id
        recalc.drop(qid)
        db.session.commit()
        assert attempts()[0].settings_snapshot["dropped"] == [pos]


# ---------------- O'chirish va cheklar ----------------

def test_release_returns_questions_to_bank(app, client, topic):
    n = build(client, topic).json["tests"]
    assert client.post(f"/api/oflayn/{topic}/ochirish").json["n"] == n
    with app.app_context():
        assert not attempts() and db.session.scalar(select(func.count()).select_from(TestAttempt)) == 0


def test_old_prepared_tests_are_purged(app, client, topic):
    build(client, topic)
    with app.app_context():
        tasks.cleanup({})
        db.session.commit()
        assert attempts()
        db.session.execute(text("UPDATE test_attempts SET started_at = now() - interval '31 days'"))
        tasks.cleanup({})
        db.session.commit()
        assert not attempts()


def test_errors(app, client, topic, monkeypatch):
    assert build(client, 999_999).status_code == 422
    with app.app_context():
        no_lesson = db.session.scalar(select(Topic.id).where(~select(ContentBlock.id).join(Subtopic).where(
            Subtopic.topic_id == Topic.id).exists()))
    if no_lesson:
        assert "tayyor emas" in build(client, no_lesson).json["error"]
    monkeypatch.setattr(offline, "MAX_TOPICS", 0)
    r = build(client, topic)
    assert r.status_code == 422 and "Ko‘pi bilan 0 ta" in r.json["error"]
    with app.app_context():
        assert not attempts()


def test_image_limit_and_list(app, client, topic, monkeypatch, tmp_path):
    with app.app_context():
        block = db.session.scalar(select(ContentBlock).join(Subtopic).where(Subtopic.topic_id == topic))
        old = dict(block.data)
        block.data = {**old, "src": "img/savol-blok-sxema.svg"}
        db.session.commit()
        bid = block.id
    try:
        j = build(client, topic).json
        assert "/static/img/savol-blok-sxema.svg" in j["urls"] and j["bytes"] > 0
        monkeypatch.setattr(offline, "MAX_BYTES", 10)
        r = build(client, topic)
        assert r.status_code == 422 and "30 MB" in r.json["error"]
        with app.app_context():
            for bad in ("../../.env", "https://x.uz/a.png", "img/yoq.png", 5, None):
                b = db.session.get(ContentBlock, bid)
                b.data = {**old, "src": bad}
                assert not any("savol" in p or "env" in p for p, _s in offline._images(catalog.lesson_view(topic), []))
                db.session.rollback()
    finally:
        with app.app_context():
            db.session.get(ContentBlock, bid).data = old
            db.session.commit()


@pytest.mark.parametrize("role", ["expert", "admin"])
def test_only_teachers(as_role, role):
    assert as_role(role).post("/api/oflayn/1", headers=JSON).status_code == 403


def test_guest_is_rejected(guest):
    assert guest.post("/api/oflayn/1", headers=JSON).status_code == 401 and guest.get("/api/token").status_code == 401


# ---------------- Sahifalar ----------------

def test_lesson_page_gates_online_but_not_in_pack(app, client, topic):
    build(client, topic)
    with app.app_context():
        parts = catalog.lesson_view(topic)["parts"]
    online, pack = client.get(f"/app/dars/{topic}").text, client.get(f"/app/dars/{topic}", headers=PACK).text
    assert pack.count("data-off-part=") == len(parts) and "data-off-part" not in online
    assert "data-off-start" in pack and "data-off-locked" in pack
    assert "rmPack(" in online and "rmPack(" not in pack
    for u in re.findall(r'data-off-test="([^"]*)"', pack):
        assert u == "" or uuid.UUID(u)


def test_topic_page_offers_download(client, topic):
    html = client.get(f"/app/bilim/{topic}").text
    assert f"rmPack({topic})" in html and "js/offline.js" in html


def test_offline_shell_is_public_and_has_no_personal_data(client, guest):
    assert guest.get("/oflayn").status_code == 200
    html = client.get("/oflayn").text
    assert "Dilnoza" not in html and "Karimova" not in html and "rmPackList()" in html
    assert "Oflayn darslar" in client.get("/app/oflayn").text


def test_player_of_lesson_returns_to_lesson(app, client, topic):
    build(client, topic)
    with app.app_context():
        a = attempts()[0]
        u, sid = a.client_uuid, a.subtopic_id
    html = client.get(f"/test/urinish/{u}").text
    assert f"/app/dars/{topic}#k{sid}" in html and "Darsga qaytish" in html


def test_token_endpoint_gives_working_token():
    from app import create_app
    from tests.conftest import CONFIG
    c = create_app({**CONFIG, "WTF_CSRF_ENABLED": True}).test_client()
    c.get("/_rol/user")
    r = c.get("/api/token")
    assert r.headers["Cache-Control"] == "no-store"
    u = "/api/urinish/00000000-0000-4000-8000-000000000000/javoblar"
    body = {"kind": "exam", "answers": [{"pos": 0, "v": 1}]}
    assert c.post(u, json=body).status_code == 400
    assert c.post(u, json=body, headers={"X-CSRFToken": r.json["token"]}).status_code == 404


def test_service_worker_files_exist():
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    core = re.findall(r'"/static/([^"]+)"', sw)
    assert "js/offline.js" in core and all((STATIC / f).is_file() for f in core)
    assert 'OFFLINE = "/oflayn"' in sw and "k !== PACK" in sw
    js = (STATIC / "js" / "offline.js").read_text(encoding="utf-8")
    assert 'CACHE = "rm-pack"' in js and 'PACK = "rm-pack"' in sw


def test_js_texts_are_translated_on_page(client):
    html = client.get("/app/oflayn").text
    for key in ("packReady", "packInfo", "packRemove", "packNoSpace", "logoutPending", "pauseOffline"):
        assert f'"{key}"' in html
    assert "{size}" in html and "{n} ta javob hali" in html


def test_progress_module_still_records_lesson(app, client, topic):
    """Oflayn test natijasi mavzu holatiga odatdagidek ta'sir qiladi."""
    build(client, topic)
    with app.app_context():
        u = attempts()[0].client_uuid
    client.post(f"/api/urinish/{u}/yakunlash", json={"kind": "lesson", "stage": None})
    with app.app_context():
        assert db.session.get(progress.UserTopicProgress, (uid(app), topic)).status == "learn"
        assert datetime.now(timezone.utc) - attempts("submitted")[0].finished_at < timedelta(minutes=1)
