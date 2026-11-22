"""O'qituvchi ekranlari bazadan: mavzu sahifasi, dars bloklari, qidiruv, eslatmalar, hudud."""
import json

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Question, Subtopic, Topic, User, UserTopicProgress
from app.services import attempts
from app.services.content_import import load
from tests.conftest import JSON


def _topic_id(app, title="Python: shart operatorlari"):
    with app.app_context():
        return db.session.scalar(select(Topic.id).where(Topic.title == title))


def _me(app):
    with app.app_context():
        return db.session.scalar(select(User.id).where(User.phone == "+998901234567"))


def test_topic_page_from_database(app, client):
    tid = _topic_id(app)
    html = client.get(f"/app/bilim/{tid}").get_data(as_text=True)
    for name in ("if operatori", "if / else", "elif zanjiri", "Ichma-ich shartlar", "Dasturlash"):
        assert name in html
    assert "Mavzu testi hali topshirilmagan" in html
    assert f'href="/app/dars/{tid}"' in html                 # darsi bor mavzu
    assert client.get("/app/bilim/999999").status_code == 404


def test_topic_without_lesson_blocks(app, client):
    html = client.get(f"/app/bilim/{_topic_id(app, 'Sanoq sistemalari')}").get_data(as_text=True)
    assert "Dars tayyorlanmoqda" in html and "/app/dars/" not in html


def test_topic_shows_progress_and_weak_subtopic(app, client):
    tid, uid = _topic_id(app), _me(app)
    with app.app_context():
        db.session.add(UserTopicProgress(user_id=uid, topic_id=tid, status="relearn", best_pct=64.4))
        attempt = attempts.start_attempt(uid, "topic", attempts.plan_for_topic(tid), topic_id=tid)
        subs = {q.id: q.subtopic.title for q in db.session.scalars(select(Question))}
        for item in attempt.items:                               # elif — 40%, qolganlari — 100%
            item.score = 40 if subs[item.question_id] == "elif zanjiri" else 100
        db.session.commit()
    html = client.get(f"/app/bilim/{tid}").get_data(as_text=True)
    assert "Eng yaxshi natija: 64%" in html
    assert "2 / 4 tayyor" in html                             # if operatori, if / else ≥ 70; elif 40; ichma-ich baholanmagan
    assert "«elif zanjiri» bo‘yicha 40%" in html


def test_lesson_renders_blocks(app, client):
    tid = _topic_id(app)
    html = client.get(f"/app/dars/{tid}").get_data(as_text=True)
    assert "Shart operatori mantiqiy ifodaning" in html       # text
    assert "flowchart TD" in html                             # mermaid (SVG yo'q — matni)
    assert "<th>Amal</th>" in html and "<td>teng emas</td>" in html   # table
    assert 'href="#k' in html                                 # mundarija
    assert client.get(f"/app/dars/{_topic_id(app, 'Sanoq sistemalari')}").status_code == 404
    assert client.get("/app/dars/999999").status_code == 404


@pytest.mark.usefixtures("fresh_content")
def test_lesson_blocks_are_escaped_and_unsafe_sources_dropped(app, client):
    with app.app_context():
        load({"course": {"slug": "x", "title": "X"}, "sections": [{"title": "S", "topics": [{"title": "T", "subtopics": [
            {"title": "U", "blocks": [
                {"kind": "text", "data": {"body": "<script>alert(1)</script>"}},
                {"kind": "image", "data": {"src": "https://evil.example/x.png", "alt": "tashqi"}},
                {"kind": "image", "data": {"src": "img/savol-mantiqiy-sxema.svg", "alt": "ichki"}},
                {"kind": "video", "data": {"url": "javascript:alert(1)"}},
                {"kind": "mermaid", "data": {"svg": "<svg xmlns='http://www.w3.org/2000/svg'></svg>", "alt": "sxema"}},
            ]}]}]}]})
    html = client.get(f"/app/dars/{_topic_id(app, 'T')}").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "evil.example" not in html and "javascript:alert" not in html
    assert '/static/img/savol-mantiqiy-sxema.svg' in html
    assert 'src="data:image/svg+xml;base64,' in html


def test_search_index_and_notes_use_database_topics(app, client):
    tid = _topic_id(app, "Relyatsion model")
    html = client.get("/app/").get_data(as_text=True)
    index = json.loads(html.split("window.RM_SEARCH = ", 1)[1].split(";</script>", 1)[0])
    hit = next(i for i in index if i["t"] == "Relyatsion model")
    assert hit["u"] == f"/app/bilim/{tid}" and hit["s"] == "Ma’lumotlar bazasi"
    assert "Relyatsion model" in client.get("/app/eslatmalar").get_data(as_text=True)


def test_unpublished_topic_is_hidden(app, client):
    tid = _topic_id(app, "Relyatsion model")
    with app.app_context():
        db.session.get(Topic, tid).is_published = False
        db.session.commit()
    try:
        assert client.get(f"/app/bilim/{tid}").status_code == 404
        assert "Relyatsion model" not in client.get("/app/").get_data(as_text=True)
    finally:
        with app.app_context():
            db.session.get(Topic, tid).is_published = True
            db.session.commit()


def test_region_is_saved(app, client):
    r = client.post("/app/profil/hudud", data={"region": "Samarqand viloyati"}, headers=JSON)
    assert r.json["ok"]
    with app.app_context():
        assert db.session.get(User, _me(app)).region == "Samarqand viloyati"
