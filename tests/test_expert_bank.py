"""Ekspert paneli bazada: savollar banki, muharrir (versiyalar), arxivlash, AI navbati, audit, rasm yuklash."""
import io

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import AttemptItem, AuditLog, Question, QuestionVersion, Section, Subtopic, Topic, User
from app.services import attempts
from tests.conftest import JSON

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64


def _ids(app, sub="Rekursiya"):
    with app.app_context():
        s = db.session.scalar(select(Subtopic).where(Subtopic.title == sub))
        t = db.session.get(Topic, s.topic_id)
        return {"topic": str(t.section_id), "lesson": str(t.id), "subtopic": str(s.id)}


def _form(app, **kw):
    f = {**_ids(app), "level": "O‘rta", "kind": "yopiq", "format": "matn", "time": "60", "text": "Yangi savol?",
         "opt": ["A javob", "B javob", "", "C javob"], "right": ["3"], "why": "Izoh"}
    f.update(kw)
    return f


def _q(app, text):
    with app.app_context():
        q = db.session.scalar(select(Question).where(Question.text == text))
        db.session.expunge_all()
        return q


@pytest.fixture()
def expert(as_role):
    return as_role("expert")


def test_bank_lists_database_questions_with_filters(app, expert):
    html = expert.get("/ekspert/").get_data(as_text=True)
    assert "DNS serverning asosiy vazifasi qaysi?" in html
    assert "3A₁₆ sonini" in html                                  # AI savoli ham bankda (tekshiruvda)
    html = expert.get("/ekspert/?turi=moslash").get_data(as_text=True)
    assert "Atamalarni ta’riflari bilan moslashtiring." in html and "DNS serverning" not in html
    html = expert.get("/ekspert/?holat=review").get_data(as_text=True)
    assert "3A₁₆ sonini" in html and "DNS serverning" not in html
    assert "Savol topilmadi" in expert.get("/ekspert/?q=yo%27q+savol").get_data(as_text=True)
    assert "kichik mavzuda savollar yetarli emas" in html          # namunada har darajada 4×weight yo'q


def test_create_question_saves_version_and_audit(app, expert):
    r = expert.post("/ekspert/savol", data=_form(app), headers=JSON)
    assert r.json["ok"], r.json
    q = _q(app, "Yangi savol?")
    assert (q.type, q.difficulty, q.status, q.source) == ("single", "medium", "approved", "expert")
    assert q.data["options"] == ["A javob", "B javob", "C javob"] and q.answer == {"keys": [2]}   # bo'sh variant tashlandi
    assert q.time_limit_s == 60 and q.explanation == "Izoh"
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(QuestionVersion).where(QuestionVersion.question_id == q.id)) == 1
        log = db.session.scalar(select(AuditLog).where(AuditLog.entity_id == str(q.id)))
        assert log.action == "create" and log.actor_id == db.session.scalar(select(User.id).where(User.role == "expert"))


@pytest.mark.parametrize("kw, field", [
    ({"subtopic": ""}, "subtopic"),
    ({"opt": ["faqat bitta", ""]}, "opt"),
    ({"right": []}, "opt"),
    ({"kind": "kop", "right": ["0"]}, "opt"),
    ({"kind": "ochiq"}, "answer"),
    ({"kind": "moslash", "left": ["a", ""], "right_txt": ["b", "c"]}, "pairs"),
    ({"time": "5"}, "time"),
    ({"level": "Juda qiyin"}, "level"),
])
def test_editor_validation(app, expert, kw, field):
    r = expert.post("/ekspert/savol", data=_form(app, **kw), headers=JSON)
    assert r.status_code == 422 and field in r.json["errors"]


def test_matching_and_open_questions(app, expert):
    r = expert.post("/ekspert/savol", headers=JSON, data=_form(
        app, kind="moslash", text="Moslang:", left=["HTTP", "FTP", ""], right_txt=["Veb", "Fayl", ""]))
    assert r.json["ok"]
    q = _q(app, "Moslang:")
    assert q.data["left"] == ["HTTP", "FTP"] and q.answer == {"pairs": [0, 1]}
    expert.post("/ekspert/savol", headers=JSON, data=_form(app, kind="ochiq", text="2+2?", answer="4", answer_alt="to‘rt, 4.0"))
    assert _q(app, "2+2?").answer == {"value": "4", "accept": ["to‘rt", "4.0"]}


def test_table_and_diagram_formats(app, expert):
    expert.post("/ekspert/savol", headers=JSON, data=_form(
        app, format="jadval", text="Jadval?", rows="2", cols="2", cell_1_1="x", cell_1_2="y", cell_2_1="", cell_2_2=""))
    assert _q(app, "Jadval?").data["table"] == {"rows": [["x", "y"]]}
    expert.post("/ekspert/savol", headers=JSON, data=_form(app, format="chizma", text="Sxema?", diagram="flowchart TD; A-->B"))
    assert _q(app, "Sxema?").data["diagram"] == "flowchart TD; A-->B"


def test_image_upload_checks_content(app, expert, tmp_path, monkeypatch):
    monkeypatch.setattr(app, "static_folder", str(tmp_path))
    bad = expert.post("/ekspert/savol", headers=JSON, content_type="multipart/form-data", data={
        **_form(app, format="rasm", text="Rasm?"), "image": (io.BytesIO(b"<svg onload=alert(1)>"), "x.png")})
    assert bad.status_code == 422 and "PNG" in bad.json["errors"]["text"]
    ok = expert.post("/ekspert/savol", headers=JSON, content_type="multipart/form-data", data={
        **_form(app, format="rasm", text="Rasm?", image_alt="Sxema"), "image": (io.BytesIO(PNG), "../../evil.svg")})
    assert ok.json["ok"]
    src = _q(app, "Rasm?").data["image"]["src"]
    assert src.startswith("uploads/q/") and src.endswith(".png") and ".." not in src
    assert (tmp_path / src).read_bytes() == PNG


def test_edit_bumps_version_and_keeps_history(app, expert):
    expert.post("/ekspert/savol", data=_form(app), headers=JSON)
    q = _q(app, "Yangi savol?")
    html = expert.get(f"/ekspert/savol?id={q.id}").get_data(as_text=True)
    assert "Savolni tahrirlash" in html and f'name="id" value="{q.id}"' in html
    r = expert.post("/ekspert/savol", headers=JSON, data=_form(app, id=str(q.id), text="Tahrirlangan savol?"))
    assert r.json["ok"]
    with app.app_context():
        q2 = db.session.get(Question, q.id)
        assert q2.version == 2 and q2.text == "Tahrirlangan savol?"
        snaps = db.session.scalars(select(QuestionVersion.snapshot).where(QuestionVersion.question_id == q.id)
                                   .order_by(QuestionVersion.version)).all()
        assert [s["text"] for s in snaps] == ["Yangi savol?", "Tahrirlangan savol?"]
    # O'zgarishsiz saqlash versiyani oshirmaydi
    expert.post("/ekspert/savol", headers=JSON, data=_form(app, id=str(q.id), text="Tahrirlangan savol?"))
    with app.app_context():
        assert db.session.get(Question, q.id).version == 2
    assert expert.get("/ekspert/savol?id=999999").status_code == 404


def test_delete_archives_and_hides_from_tests(app, expert, client):
    q = _q(app, "DNS serverning asosiy vazifasi qaysi?")
    assert expert.post(f"/ekspert/savollar/{q.id}/ochirish", headers=JSON).json["ok"]
    assert "DNS serverning" not in expert.get("/ekspert/").get_data(as_text=True)
    assert "DNS serverning" in expert.get("/ekspert/?holat=archived").get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Question, q.id).status == "archived"
        uid = db.session.scalar(select(User.id).where(User.role == "user"))
        picked = attempts.pick_questions(uid, {q.subtopic_id: 10})
        assert q.id not in [p.question_id for p in picked]
        # Holatni qaytarish (umumiy namunaviy kontent boshqa testlar uchun)
        db.session.get(Question, q.id).status = "approved"
        db.session.commit()


def test_queue_approve_with_edits(app, expert):
    q = _q(app, "FF₁₆ soni o‘nlik sanoq sistemasida nechaga teng?")
    r = expert.post(f"/ekspert/navbat/{q.id}", headers=JSON, data={
        "action": "approve", "text": "FF₁₆ soni o‘nlikda nechaga teng?", "opt": ["255", "256", "", "240"], "right": ["0"]})
    assert r.json["ok"], r.json
    with app.app_context():
        q2 = db.session.get(Question, q.id)
        assert q2.status == "approved" and q2.version == 2 and q2.data["options"] == ["255", "256", "240"]
        q2.status, q2.text, q2.version, q2.data = "review", q.text, 1, q.data      # namunani tiklash
        db.session.execute(QuestionVersion.__table__.delete().where(QuestionVersion.question_id == q.id,
                                                                     QuestionVersion.version == 2))
        db.session.commit()
    # Tasdiqlangan yoki AI'dan bo'lmagan savol navbat orqali o'zgarmaydi
    other = _q(app, "DNS serverning asosiy vazifasi qaysi?")
    assert expert.post(f"/ekspert/navbat/{other.id}", data={"action": "reject"}, headers=JSON).status_code == 422


@pytest.mark.usefixtures("fresh_content")
def test_queue_reject_deletes_unused_and_archives_used(app, expert):
    from app.services.content_import import load
    with app.app_context():
        load({"course": {"slug": "x", "title": "X"}, "sections": [{"title": "S", "topics": [{"title": "T", "subtopics": [
            {"title": "U", "weight": 2, "questions": [
                {"source": "ai", "type": "single", "difficulty": "easy", "text": f"AI {i}", "data": {"options": ["a", "b"]},
                 "answer": {"keys": [0]}} for i in (1, 2)]}]}]}]})
        a1, a2 = (db.session.scalar(select(Question.id).where(Question.text == t)) for t in ("AI 1", "AI 2"))
    assert expert.post(f"/ekspert/navbat/{a1}", data={"action": "reject"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.get(Question, a1) is None
        # Berilgan savol (attempt_items'da bor) o'chirilmaydi, arxivlanadi
        q = db.session.get(Question, a2)
        q.status = "approved"
        db.session.commit()
        uid = db.session.scalar(select(User.id).where(User.role == "expert"))
        attempts.start_attempt(uid, "topic", {q.subtopic_id: 1})
        q = db.session.get(Question, a2)
        q.status = "review"
        db.session.commit()
    assert expert.post(f"/ekspert/navbat/{a2}", data={"action": "reject"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.get(Question, a2).status == "archived"
        assert db.session.scalar(select(func.count()).select_from(AttemptItem)) == 1


def test_user_cannot_use_expert_bank(client):
    assert client.get("/ekspert/").status_code == 403
    assert client.post("/ekspert/savol", data={}).status_code == 403
