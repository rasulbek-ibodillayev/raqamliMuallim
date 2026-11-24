"""Tuzatish 24.11.2: «Yechimini ko'rish» (AI tutor), rejadagi dars testi tugmasi, Google orqali kirish."""
import base64
import json
import time
import urllib.parse
import uuid

import pytest
from sqlalchemy import select

from app.cli import demo_user
from app.extensions import db
from app.models import Question, Subtopic, TestAttempt, User
from app.services import attempts as at
from app.services import google_auth
from app.services import question_bank as qb
from app.services import test_builder as tb
from app.services.content_import import check_question
from tests.conftest import JSON


def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


def _finished(title="Amaliy protokollar", wrong=True):
    a, _ = tb.get_or_start(demo_user("user").id, "lesson", subtopic_id=_sub(title))
    if not wrong:
        snaps = at._snapshots(a)
        ans = {"single": lambda x: x["keys"][0], "multiple": lambda x: x["keys"], "matching": lambda x: x["pairs"],
               "open": lambda x: x["value"]}
        at.save_answers(a, [{"pos": p, "v": ans[s["type"]](s["answer"]), "at": 1} for p, (s, *_x) in snaps.items()])
    return at.finish(a)


# ---------------- 1. Yechim ----------------

def test_solution_button_only_on_wrong_answers(app, client):
    with app.app_context():
        bad = _finished().client_uuid
    html = client.get(f"/test/urinish/{bad}/natija").get_data(as_text=True)
    assert "Yechimini ko‘rish" in html and f"/app/tutor?savol={bad}:0" in html
    with app.app_context():
        good = _finished("if operatori", wrong=False).client_uuid
    assert "Yechimini ko‘rish" not in client.get(f"/test/urinish/{good}/natija").get_data(as_text=True)


def test_solution_explains_every_option_of_theory_question(app, client):
    with app.app_context():
        a = _finished()
        snaps = at._snapshots(a)
        pos = next(p for p, (s, *_x) in snaps.items() if s["text"].startswith("DNS"))
        notes = snaps[pos][0]["answer"]["notes"]
        u = a.client_uuid
    r = client.get(f"/app/tutor/yechim/{u}:{pos}", headers=JSON)
    assert r.json["ok"] and "DNS serverning asosiy vazifasi" in r.json["ask"]
    html = r.json["html"]
    assert "B) Domen nomini IP-manzilga o‘girish" in html and "IP-manzil orqali topadi" in html
    assert len(notes) == 4 and all(n in html for n in notes)
    assert html.count("noto‘g‘ri") == 3 and "Manba: savollar banki" in html


@pytest.mark.parametrize("title", ["if operatori", "Ikkilik va o‘nlik", "Shartli yig‘indi", "Qidiruv algoritmlari", "elif zanjiri"])
def test_solution_for_every_question_type(app, client, title):
    with app.app_context():
        a = _finished(title)
        u, n = a.client_uuid, a.total
        links = [s[0]["answer"] for s in at._snapshots(a).values()]
    assert n == 3 and links
    for pos in range(n):
        r = client.get(f"/app/tutor/yechim/{u}:{pos}", headers=JSON)
        assert r.status_code == 200 and "<li" in r.json["html"] or "javobsiz" in r.json["html"]
    if title == "if operatori":                                 # darsi bor kichik mavzu: darsga havola
        assert "/app/dars/" in r.json["html"]


def test_template_solution_shows_calculation(app, client):
    with app.app_context():
        a = _finished("Ikkilik va o‘nlik")
        items = {i.position: i.question_id for i in a.items}
        pos = next(p for p, q in items.items() if db.session.get(Question, q).source == "template")
        why = db.session.get(Question, items[pos]).explanation
        u = a.client_uuid
    from markupsafe import escape
    assert str(escape(why)) in client.get(f"/app/tutor/yechim/{u}:{pos}", headers=JSON).json["html"]


def test_solution_is_private_and_only_after_finish(app, client, as_role):
    with app.app_context():
        a, _ = tb.get_or_start(demo_user("user").id, "lesson", subtopic_id=_sub("Amaliy protokollar"))
        u = a.client_uuid
    assert client.get(f"/app/tutor/yechim/{u}:0", headers=JSON).status_code == 404      # test davomida kalit oshkor bo'lmaydi
    with app.app_context():
        at.finish(db.session.scalar(select(TestAttempt)))
        other = User(first_name="B", last_name="C", phone="+998900000001", role="user")
        db.session.add(other)
        db.session.commit()
        oid = other.id
    assert client.get(f"/app/tutor/yechim/{u}:0", headers=JSON).status_code == 200
    for ref in (f"{u}:99", f"{u}:-1", f"{u}:x", f"{uuid.uuid4()}:0", "abc", "natija:99", "sinov:99"):
        assert client.get(f"/app/tutor/yechim/{ref}", headers=JSON).status_code == 404, ref
    with app.test_client() as c2:
        with c2.session_transaction() as s:
            s["_user_id"], s["_fresh"] = str(oid), True
        assert c2.get(f"/app/tutor/yechim/{u}:0", headers=JSON).status_code == 404


def test_solution_text_is_escaped(app, client):
    with app.app_context():
        a = _finished()
        q = db.session.get(Question, a.items[0].question_id)
        v = next(x for x in q.versions if x.version == q.version)
        old = v.snapshot
        v.snapshot = {**old, "explanation": "<img src=x onerror=alert(1)>", "text": "<script>1</script>"}
        db.session.commit()
        u = a.client_uuid
        vid = v.id
    r = client.get(f"/app/tutor/yechim/{u}:0", headers=JSON).json
    assert "<img src=x" not in r["html"] and "<script>" not in r["ask"] and "&lt;script&gt;" in r["ask"]
    with app.app_context():
        from app.models import QuestionVersion
        db.session.get(QuestionVersion, vid).snapshot = old
        db.session.commit()


def test_sample_screens_have_solutions(client):
    html = client.get("/test/natija").get_data(as_text=True)
    assert "savol=natija:4" in html
    assert "Qiymatlar bir xil bo‘lganda" in client.get("/app/tutor/yechim/natija:4", headers=JSON).json["html"]
    assert "savol=sinov:" in client.get("/test/sinov/natija").get_data(as_text=True)
    assert client.get("/app/tutor/yechim/sinov:3", headers=JSON).json["ok"]


def test_option_notes_are_validated_and_kept_on_edit(app):
    base = {"type": "single", "difficulty": "easy", "text": "t", "data": {"options": ["a", "b"]}}
    assert check_question({**base, "answer": {"keys": [0], "notes": ["x", ""]}}) == []
    for bad in (["x"], "x", [1, 2]):
        assert check_question({**base, "answer": {"keys": [0], "notes": bad}})
    with app.app_context():
        uid = demo_user("expert").id
        sid = _sub("Kalitlar")
        q = qb.save({**base, "subtopic_id": sid, "answer": {"keys": [0], "notes": ["x", "y"]}}, uid)
        qb.save({**base, "subtopic_id": sid, "text": "t2", "answer": {"keys": [0]}}, uid, q.id)
        assert q.answer == {"keys": [0], "notes": ["x", "y"]}
        qb.save({**base, "subtopic_id": sid, "data": {"options": ["a", "c"]}, "answer": {"keys": [0]}}, uid, q.id)
        assert q.answer == {"keys": [0]}                            # variantlar o'zgardi — eski izohlar mos emas
        db.session.delete(q)
        db.session.commit()


# ---------------- 2. Reja ----------------

def test_plan_has_no_lesson_test_button_for_lessons(client):
    html = client.get("/app/reja").get_data(as_text=True)
    assert "Darsni ochish" in html and "Dars testini boshlash" not in html


# ---------------- 3. Google ----------------

CLIENT = {"GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "sec"}


@pytest.fixture()
def google(app, monkeypatch):
    """Google javobi soxta: claims'ni o'zgartirish mumkin. Qaytgan funksiya to'liq aylanishni bajaradi."""
    app.config.update(CLIENT)
    sent = {}

    def run(client, nxt="", state=None, email="yangi.oqituvchi@gmail.com", sub="1001", **over):
        r = client.get("/kirish/google" + (f"?next={nxt}" if nxt else ""))
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(r.location).query))
        sent["auth"] = q
        claims = {"iss": "https://accounts.google.com", "aud": "cid", "exp": time.time() + 600, "nonce": q["nonce"], "sub": sub,
                  "email": email, "email_verified": True, "given_name": "Malika", "family_name": "Tursunova", **over}

        def post(data):
            sent["token"] = data
            body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
            return {"id_token": f"h.{body}.s"}
        monkeypatch.setattr(google_auth, "_post", post)
        return client.get(f"/kirish/google/qaytish?state={state or q['state']}&code=abc")
    run.sent = sent
    return run


def test_google_signup_asks_only_name_and_consent(app, guest, google):
    r = google(guest)
    assert r.status_code == 302 and r.location.endswith("/royxat/malumotlar")
    auth, token = google.sent["auth"], google.sent["token"]
    assert auth["client_id"] == "cid" and auth["scope"] == "openid email profile" and auth["code_challenge_method"] == "S256"
    assert auth["redirect_uri"].endswith("/kirish/google/qaytish") == token["redirect_uri"].endswith("/kirish/google/qaytish")
    assert token["code"] == "abc" and len(token["code_verifier"]) >= 43
    html = guest.get("/royxat/malumotlar").get_data(as_text=True)
    assert 'value="Malika"' in html and "yangi.oqituvchi@gmail.com" in html and 'name="pw"' not in html and 'name="secret"' not in html
    assert guest.post("/royxat/malumotlar", headers=JSON, data={"fn": "Malika", "ln": "Tursunova"}).status_code == 422   # rozilik
    assert guest.post("/royxat/malumotlar", headers=JSON, data={"fn": "Malika", "ln": "Tursunova", "consent": "1"}).json["ok"]
    with app.app_context():
        u = User.by_login("yangi.oqituvchi@gmail.com")
        assert u.google_sub == "1001" and u.password_hash is None and u.consent_at and u.role == "user"
    assert guest.get("/app/").status_code == 200
    # Parolsiz akkauntga parol bilan kirib bo'lmaydi
    guest.get("/chiqish")
    assert guest.post("/kirish", data={"login": "yangi.oqituvchi@gmail.com", "pw": "parol1234"}, headers=JSON).status_code == 422
    # Keyingi safar Google darhol kiritadi (email o'zgargan bo'lsa ham — sub bo'yicha)
    r = google(guest, nxt="/app/reja", email="boshqa@gmail.com")
    assert r.location == "/app/reja" and guest.get("/app/").status_code == 200
    r = guest.post("/app/profil/parol", headers=JSON, data={"old": "x", "new": "yangi1234", "new2": "yangi1234"})
    assert r.status_code == 422 and "Parolni tiklash" in r.json["errors"]["old"]


@pytest.mark.parametrize("over", [{"iss": "https://evil.example"}, {"aud": "boshqa"}, {"exp": 1}, {"nonce": "x"},
                                  {"email_verified": False}, {"email": ""}, {"sub": ""}])
def test_google_rejects_bad_tokens(app, guest, google, over):
    r = google(guest, **over)
    assert r.location.endswith("/kirish") and guest.get("/app/").status_code == 302
    with app.app_context():
        assert db.session.scalar(select(User).where(User.google_sub.is_not(None))) is None


def test_google_state_is_required_and_one_time(guest, google):
    assert google(guest, state="notogri").location.endswith("/kirish")
    assert guest.get("/kirish/google/qaytish?state=x&code=abc").location.endswith("/kirish")      # sessiyada oqim yo'q
    assert guest.get("/kirish/google/qaytish?error=access_denied").location.endswith("/kirish")


def test_google_existing_email_links_only_after_password(app, guest, google):
    with app.app_context():
        email = demo_user("user").email
    assert google(guest, email=email, sub="77").location.endswith("/kirish")
    assert guest.get("/app/").status_code == 302
    with app.app_context():
        assert User.by_login(email).google_sub is None
    assert guest.post("/kirish", data={"login": email, "pw": "parol1234"}, headers=JSON).json["ok"]
    with app.app_context():
        assert User.by_login(email).google_sub == "77"
    guest.get("/chiqish")
    assert google(guest, email=email, sub="77").location == "/app/"


def test_google_pending_link_does_not_attach_to_other_account(app, guest, google):
    with app.app_context():
        email = demo_user("user").email
        u = User(first_name="B", last_name="C", email="b@maktab.uz", role="user")
        u.set_password("parol1234")
        db.session.add(u)
        db.session.commit()
    google(guest, email=email, sub="88")
    assert guest.post("/kirish", data={"login": "b@maktab.uz", "pw": "parol1234"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.scalar(select(User).where(User.google_sub.is_not(None))) is None


def test_google_blocked_account(app, guest, google):
    with app.app_context():
        u = demo_user("user")
        u.google_sub, u.is_active = "99", False
        db.session.commit()
    assert google(guest, sub="99").location.endswith("/kirish") and guest.get("/app/").status_code == 302


def test_google_dev_signup_without_keys(app, guest):
    assert guest.get("/kirish/google?yangi=1").location.endswith("/royxat/malumotlar")
    assert "/kirish/google?yangi=1" in guest.get("/royxat").get_data(as_text=True)
    assert "yangi=1" not in guest.get("/kirish").get_data(as_text=True)
