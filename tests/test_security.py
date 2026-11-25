"""9: urinishlarni cheklash, so'rov hajmi, sessiya, cookie, sarlavhalar va kiritilgan ma'lumotdan himoya."""
import io
import threading
import zipfile

import pytest
from flask import request
from sqlalchemy import select, text

from app import create_app, security
from app.cli import demo_user
from app.extensions import db
from app.models import AuditLog, Notification, RateLimit
from app.models.users import User
from app.roles import safe_next
from app.services import codes, limits, xlsx
from tests.conftest import CONFIG, JSON

PHONE = "+998901234567"
EMAIL = "dilnoza.k@maktab.uz"


@pytest.fixture()
def teacher(app):
    with app.app_context():
        return demo_user("user").id


def login(c, pw, who=PHONE, ip="10.0.0.1"):
    return c.post("/kirish", data={"login": who, "pw": pw}, headers=JSON, environ_base={"REMOTE_ADDR": ip})


def expire(app):
    """Hamma davr tugadi."""
    with app.app_context(), db.engine.begin() as conn:
        conn.execute(text("UPDATE rate_limits SET until = now() - interval '1 second'"))


def user(app, who=PHONE):
    with app.app_context():
        return User.by_login(who)


# ---------------- Hisob ----------------

def test_take_counts_blocks_and_expires(app):
    with app.test_request_context():
        assert [limits.take(("pw", 1)).left for _ in range(5)] == [4, 3, 2, 1, 0]
        r = limits.take(("pw", 1))
        assert r.blocked and 890 < r.wait <= 900
        assert not limits.take(("pw", 2)).blocked                     # boshqa foydalanuvchiga ta'sir qilmaydi
    expire(app)
    with app.test_request_context():
        assert limits.take(("pw", 1)).left == 4


def test_blocked_attempt_neither_extends_nor_spends_later_rules(app):
    with app.test_request_context():
        for _ in range(5):
            limits.take(("login", "a|ip"), ("login_all", "a"))
        before = db.session.execute(select(RateLimit.key, RateLimit.n, RateLimit.until)).all()
        for _ in range(10):
            assert limits.take(("login", "a|ip"), ("login_all", "a")).blocked
        db.session.rollback()
        assert sorted(db.session.execute(select(RateLimit.key, RateLimit.n, RateLimit.until)).all()) == sorted(before)


def test_refund_and_clear(app):
    with app.test_request_context():
        limits.take(("pw", 1))
        limits.refund(("pw", 1))
        assert limits.take(("pw", 1)).left == 4
        limits.refund(("pw", 1), ("pw", 1), ("pw", 1))                # noldan pastga tushmaydi
        assert limits.take(("pw", 1)).left == 4
        limits.clear(("pw", 1))
        assert limits.take(("pw", 1)).left == 4


def test_parallel_attempts_cannot_exceed_limit(app):
    got = []

    def run():
        with app.test_request_context():
            got.append(limits.take(("pw", 7)).blocked)

    threads = [threading.Thread(target=run) for _ in range(14)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert got.count(False) == 5 and got.count(True) == 9


def test_count_survives_rollback_and_old_rows_are_purged(app, monkeypatch):
    with app.test_request_context():
        limits.take(("pw", 1))
        db.session.rollback()
        assert limits.take(("pw", 1)).left == 3
    expire(app)
    monkeypatch.setattr(limits.random, "random", lambda: 0.0)
    with app.test_request_context():
        limits.take(("pw", 2))
        assert db.session.scalar(select(db.func.count()).select_from(RateLimit)) == 1


def test_table_has_no_personal_data_and_is_unlogged(app, guest, teacher):
    login(guest, "xato12345")
    with app.app_context():
        rows = db.session.scalars(select(RateLimit)).all()
        assert len(rows) == 3 and all(isinstance(r.key, int) for r in rows)
        assert set(RateLimit.__table__.columns.keys()) == {"key", "until", "n"}
        assert db.session.scalar(text("SELECT relpersistence FROM pg_class WHERE relname = 'rate_limits'")) == "u"


@pytest.mark.parametrize("raw, same", [("2001:db8:1:2::1", "2001:db8:1:2:ffff::9"), ("::ffff:10.0.0.5", "10.0.0.5")])
def test_ip_groups(app, raw, same):
    def ip(v):
        with app.test_request_context(environ_base={"REMOTE_ADDR": v}):
            return limits.client_ip()
    assert ip(raw) == ip(same) != ip("2001:db8:1:3::1")


# ---------------- Kirish ----------------

def test_login_locks_account_for_ip_even_with_new_cookies(app, teacher):
    for n in range(5):
        r = login(app.test_client(), "xato12345")                     # har safar yangi brauzer
        assert r.status_code == 422, n
    assert "15 daqiqadan" in r.json["errors"]["pw"]
    r = login(app.test_client(), "parol1234")                         # to'g'ri parol ham kutadi
    assert r.status_code == 429 and 0 < int(r.headers["Retry-After"]) <= 900 and "Juda ko‘p urinish" in r.json["errors"]["pw"]
    assert login(app.test_client(), "parol1234", ip="10.0.0.2").json["ok"]      # egasi boshqa tarmoqdan kira oladi
    expire(app)
    assert login(app.test_client(), "parol1234").json["ok"]


def test_login_formats_share_one_counter(app, teacher):
    for who in ("90 123-45-67", "+998901234567", "998 90 123 45 67", "(90) 1234567", "901234567"):
        login(app.test_client(), "xato12345", who=who)
    assert login(app.test_client(), "parol1234").status_code == 429
    for who in (EMAIL, EMAIL.upper(), EMAIL, EMAIL, f" {EMAIL} "):
        login(app.test_client(), "xato12345", who=who)
    assert login(app.test_client(), "parol1234", who=EMAIL).status_code == 429


def test_login_warns_when_few_attempts_left(app, teacher):
    msgs = [login(app.test_client(), "xato12345").json["errors"]["pw"] for _ in range(4)]
    assert "qoldi" not in msgs[1] and "Yana 2 ta urinish qoldi" in msgs[2] and "Yana 1 ta" in msgs[3]


def test_successful_logins_are_not_counted(app, teacher):
    for _ in range(12):
        assert login(app.test_client(), "parol1234").json["ok"]
    with app.app_context():
        assert {r.n for r in db.session.scalars(select(RateLimit))} <= {0}


def test_one_ip_cannot_try_many_accounts(app, teacher, monkeypatch):
    monkeypatch.setitem(limits.RULES, "login_ip", (6, 900))
    for n in range(6):
        login(app.test_client(), "xato12345", who=f"+99890111222{n}")
    assert login(app.test_client(), "parol1234").status_code == 429
    assert login(app.test_client(), "parol1234", ip="10.0.0.9").json["ok"]


def test_many_ips_cannot_try_one_account(app, teacher):
    for n in range(30):
        login(app.test_client(), "xato12345", ip=f"10.1.0.{n}")
    assert login(app.test_client(), "parol1234", ip="10.2.0.1").status_code == 429


def test_unknown_and_known_login_look_the_same(app, guest, teacher, monkeypatch):
    spent = []
    monkeypatch.setattr(User, "spend_hash_time", staticmethod(lambda v: spent.append(v)))
    a = login(guest, "xato12345")
    assert not spent
    b = login(guest, "xato12345", who="+998909999999")
    assert spent == ["xato12345"] and (a.status_code, a.json) == (b.status_code, b.json)


def test_without_js_limit_page_is_rendered(app, guest, teacher):
    for _ in range(5):
        login(guest, "xato12345")
    r = guest.post("/kirish", data={"login": PHONE, "pw": "x"}, environ_base={"REMOTE_ADDR": "10.0.0.1"})
    assert r.status_code == 429 and "Juda ko‘p urinish" in r.get_data(as_text=True)


# ---------------- Kodlar ----------------

@pytest.mark.parametrize("url, name, value", [("/royxat", "phone", "90 765 43 21"), ("/royxat/email/kod", "email", "yangi@maktab.uz"),
                                              ("/parol-tiklash/kod", "who", PHONE)])
def test_code_sending_is_limited_per_contact(app, teacher, url, name, value):
    for _ in range(5):
        assert app.test_client().post(url, data={name: value}, headers=JSON).json["ok"]
    r = app.test_client().post(url, data={name: value}, headers=JSON)
    assert r.status_code == 429 and name in r.json["errors"] and r.headers["Retry-After"]


def test_code_limit_is_shared_between_pages_and_daily(app, guest, teacher):
    with app.test_request_context():
        assert [codes.send(PHONE) for _ in range(5)] == [None] * 5
    assert guest.post("/parol-tiklash/kod", data={"who": "90 123 45 67"}, headers=JSON).status_code == 429
    for _ in range(2):
        with app.test_request_context():
            limits.clear(("code", PHONE))
            assert [codes.send(PHONE) for _ in range(5)] == [None] * 5
    with app.test_request_context():
        limits.clear(("code", PHONE))
        assert "soatdan" in codes.send(PHONE)                         # kuniga 15 ta


def test_account_lookup_is_limited_by_ip(app, guest, monkeypatch):
    """Ro'yxatdan o'tgan raqamlarni terib chiqish: «bor» va «yo'q» javoblari ham sanaladi."""
    monkeypatch.setitem(limits.RULES, "code_ip", (4, 3600))
    for n in range(4):
        assert guest.post("/parol-tiklash/kod", data={"who": f"+99890555000{n}"}, headers=JSON).status_code == 422
    r = guest.post("/parol-tiklash/kod", data={"who": "+998905550009"}, headers=JSON)
    assert r.status_code == 429 and "Juda ko‘p" in r.json["errors"]["who"]


def test_code_guesses_are_counted_per_contact_not_per_session(app, teacher):
    for n in range(5):
        c = app.test_client()
        with c.session_transaction() as s:                            # eski cookie qayta yuborilgandek: urinishlar soni yo'q
            s["reset_who"] = PHONE
        r = c.post("/parol-tiklash/kod-tekshirish", data={"otp": list("000000")}, headers=JSON)
    assert "Yangi kod" in r.json["errors"]["otp"]
    c = app.test_client()
    with c.session_transaction() as s:
        s["reset_who"] = PHONE
    assert c.post("/parol-tiklash/kod-tekshirish", data={"otp": list("123456")}, headers=JSON).status_code == 429
    # Yangi kod so'ralsa qaytadan 5 ta urinish
    c = app.test_client()
    c.post("/parol-tiklash/kod", data={"who": PHONE}, headers=JSON)
    assert c.post("/parol-tiklash/kod-tekshirish", data={"otp": list("123456")}, headers=JSON).json["ok"]


def test_registration_code_is_limited(guest):
    guest.post("/royxat", data={"phone": "90 765 43 21"}, headers=JSON)
    left = [guest.post("/royxat/telegram", data={"otp": list("000000")}, headers=JSON).json["errors"]["otp"] for _ in range(5)]
    assert "4 ta urinish" in left[0] and "Yangi kod" in left[4]
    assert guest.post("/royxat/telegram", data={"otp": list("123456")}, headers=JSON).status_code == 429


def test_demo_code_never_works_on_server(teacher):
    """Yetkazish ulanmaguncha serverda kod bilan hech kimning akkaunti ochilmaydi."""
    app = create_app({**CONFIG, "DEV_TOOLS": False})
    c = app.test_client()
    r = c.post("/parol-tiklash/kod", data={"who": PHONE}, headers=JSON)
    assert r.status_code == 422 and "hali ulanmagan" in r.json["errors"]["who"]
    with c.session_transaction() as s:
        s["reset_who"], s["reg_phone"], s["reg_email"] = PHONE, "+998907654321", "a@b.uz"
    for url, data in (("/parol-tiklash/kod-tekshirish", {}), ("/royxat/telegram", {}), ("/royxat/email", {"email": "a@b.uz"})):
        assert c.post(url, data={**data, "otp": list("123456")}, headers=JSON).status_code == 422, url
    for url in ("/parol-tiklash?kod=1", "/royxat/telegram", "/parol-tiklash/maxfiy-soz", "/royxat/email"):
        assert "Namunada" not in c.get(url).get_data(as_text=True), url


def test_contact_change_does_not_reveal_accounts_without_password(client, as_role):
    as_role("expert")
    r = client.post("/app/profil/aloqa/kod", data={"method": "phone", "contact": "93 123 45 45", "pw": "xato"}, headers=JSON)
    assert set(r.json["errors"]) == {"pw"}


# ---------------- Tiklash qadamlari ----------------

def test_secret_word_is_limited_per_account(app, teacher):
    for n in range(5):
        r = app.test_client().post("/parol-tiklash/maxfiy-soz", data={"who": PHONE, "secret": "xato"}, headers=JSON,
                                   environ_base={"REMOTE_ADDR": f"10.3.0.{n}"})
    assert "Urinishlar tugadi. 30 daqiqadan" in r.json["errors"]["secret"]
    r = app.test_client().post("/parol-tiklash/maxfiy-soz", data={"who": PHONE, "secret": "informatika"}, headers=JSON)
    assert r.status_code == 429


def test_secret_word_respects_blocked_account(app, guest, teacher):
    with app.app_context():
        User.by_login(PHONE).is_active = False
        db.session.commit()
    r = guest.post("/parol-tiklash/maxfiy-soz", data={"who": PHONE, "secret": "informatika"}, headers=JSON)
    assert r.status_code == 422 and "bloklangan" in r.json["errors"]["who"]


def test_recover_step_cookie_cannot_be_replayed(app, guest, teacher):
    guest.post("/parol-tiklash/maxfiy-soz", data={"who": PHONE, "secret": "informatika"}, headers=JSON)
    saved = guest.get_cookie("session").value
    pw = {"p1": "yangiparol1", "p2": "yangiparol1"}
    assert guest.post("/parol-tiklash/maxfiy-soz/parol", data=pw, headers=JSON).json["ok"]
    c = app.test_client()
    c.set_cookie("session", saved)
    r = c.post("/parol-tiklash/maxfiy-soz/parol", data={"p1": "ogirlangan1", "p2": "ogirlangan1"}, headers=JSON)
    assert r.json["redirect"].startswith("/parol-tiklash/maxfiy-soz")
    assert user(app).check_password("yangiparol1")


def test_reset_cookie_cannot_be_replayed_and_expires(app, guest, teacher):
    guest.post("/parol-tiklash/kod", data={"who": PHONE}, headers=JSON)
    guest.post("/parol-tiklash/kod-tekshirish", data={"otp": list("123456")}, headers=JSON)
    saved = guest.get_cookie("session").value
    with guest.session_transaction() as s:
        s["reset_verified"] = [s["reset_verified"][0] - 16 * 60, s["reset_verified"][1]]
    new = {"p1": "yangiparol1", "p2": "yangiparol1"}
    assert set(guest.post("/parol-tiklash", data=new, headers=JSON).json["errors"]) == {"otp"}
    for expected in (True, False):                                    # bir marta ishlaydi, qayta yuborilsa — yo'q
        c = app.test_client()
        c.set_cookie("session", saved)
        assert c.post("/parol-tiklash", data=new, headers=JSON).json["ok"] is expected


def test_password_reset_notifies_owner_and_is_logged(app, guest, teacher):
    guest.post("/parol-tiklash/maxfiy-soz", data={"who": PHONE, "secret": "informatika"}, headers=JSON)
    guest.post("/parol-tiklash/maxfiy-soz/parol", data={"p1": "yangiparol1", "p2": "yangiparol1"}, headers=JSON)
    with app.app_context():
        assert db.session.scalar(select(AuditLog.action).where(AuditLog.entity == "user")) == "password_reset"
        assert db.session.scalar(select(db.func.count()).select_from(Notification)) == 1


def test_staff_recover_goes_to_own_panel(app, guest, as_role):
    as_role("expert")
    guest.post("/parol-tiklash/maxfiy-soz", data={"who": "ekspert@raqamlimuallim.uz", "secret": "informatika"}, headers=JSON)
    r = guest.post("/parol-tiklash/maxfiy-soz/parol", data={"p1": "yangiparol1", "p2": "yangiparol1"}, headers=JSON)
    assert r.json["redirect"].startswith("/ekspert") and guest.get(r.json["redirect"]).status_code == 200


# ---------------- Sessiya ----------------

def test_password_change_signs_out_other_devices(app, teacher):
    phone, pc, thief = app.test_client(), app.test_client(), app.test_client()
    login(phone, "parol1234")
    login(pc, "parol1234")
    thief.set_cookie("remember_token", pc.get_cookie("remember_token").value)
    assert thief.get("/app/profil").status_code == 200
    r = phone.post("/app/profil/parol", data={"old": "parol1234", "new": "yangiparol9", "new2": "yangiparol9"}, headers=JSON)
    assert r.json["ok"]
    assert phone.get("/app/profil").status_code == 200                # o'zi kirgan holda qoladi
    phone.delete_cookie("session")
    assert phone.get("/app/profil").status_code == 200                # «eslab qolish» cookie'si ham yangilangan
    thief.delete_cookie("session")
    assert pc.get("/app/profil").status_code == 302 and thief.get("/app/profil").status_code == 302


def test_old_style_and_forged_session_is_rejected(app, teacher):
    for value in (str(teacher), f"{teacher}.", f"{teacher}.{'0' * 20}", "x.y", "", "²." + "0" * 20):
        c = app.test_client()
        with c.session_transaction() as s:
            s["_user_id"], s["_fresh"] = value, True
        assert c.get("/app/profil").status_code == 302, value


def test_staff_is_remembered_for_a_week(app, as_role):
    as_role("admin")
    c = app.test_client()
    r = login(c, "parol1234", who="admin@raqamlimuallim.uz")
    age = c.get_cookie("remember_token").expires
    from datetime import datetime, timedelta, timezone
    assert r.json["ok"] and abs(age - datetime.now(timezone.utc) - timedelta(days=7)) < timedelta(minutes=1)


def test_cross_site_link_cannot_sign_out(app, teacher, guest):
    login(guest, "parol1234")
    r = guest.get("/chiqish", headers={"Sec-Fetch-Site": "cross-site"})
    assert "Clear-Site-Data" not in r.headers and guest.get("/app/profil").status_code == 200
    assert "Clear-Site-Data" in guest.get("/chiqish", headers={"Sec-Fetch-Site": "same-origin"}).headers
    assert guest.get("/app/profil").status_code == 302


@pytest.mark.parametrize("url", ["//evil.uz", "/\\evil.uz", "/\t/evil.uz", "/\n/evil.uz", "https://evil.uz", "evil", "", None])
def test_safe_next_rejects(url):
    assert safe_next(url) is None


# ---------------- Sozlama ----------------

@pytest.fixture()
def prod_env(monkeypatch):
    for k in ("FLASK_DEBUG", "SECRET_KEY", "RM_DEV_TOOLS", "FLASK_RUN_FROM_CLI", "RM_HOSTS", "RM_PROXY_HOPS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DATABASE_URL", CONFIG["SQLALCHEMY_DATABASE_URI"])
    return monkeypatch


def test_server_does_not_start_without_secret_key(prod_env):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()
    prod_env.setenv("SECRET_KEY", "qisqa")
    with pytest.raises(RuntimeError, match="32"):
        create_app()
    prod_env.setenv("SECRET_KEY", "x" * 40)
    cfg = create_app().config
    assert cfg["SESSION_COOKIE_SECURE"] and cfg["REMEMBER_COOKIE_SECURE"] and cfg["REMEMBER_COOKIE_HTTPONLY"]
    assert cfg["WTF_CSRF_TIME_LIMIT"] is None


def test_cli_gets_random_key_and_debug_gets_dev_key(prod_env):
    prod_env.setenv("FLASK_RUN_FROM_CLI", "true")
    assert create_app().config["SECRET_KEY"] != create_app().config["SECRET_KEY"]
    prod_env.setenv("FLASK_DEBUG", "1")
    app = create_app()
    assert app.config["SECRET_KEY"] == "dev-only-change-me" and not app.config["SESSION_COOKIE_SECURE"]


def test_proxy_headers_only_when_configured(prod_env):
    def seen(hops):
        prod_env.setenv("RM_PROXY_HOPS", hops)
        app = create_app(CONFIG)
        app.add_url_rule("/_ip", "ip", lambda: f"{request.remote_addr} {request.scheme}")
        return app.test_client().get("/_ip", headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2", "X-Forwarded-Proto": "https"}).text
    assert seen("") == "127.0.0.1 http"
    assert seen("1") == "2.2.2.2 https"                               # mijoz o'zi qo'shgan 1.1.1.1 ga ishonilmaydi


def test_foreign_host_is_rejected(prod_env):
    prod_env.setenv("RM_HOSTS", "raqamlimuallim.uz, .raqamlimuallim.uz")
    c = create_app(CONFIG).test_client()
    assert c.get("/kirish", base_url="https://raqamlimuallim.uz").status_code == 200
    assert c.get("/kirish", base_url="https://www.raqamlimuallim.uz").status_code == 200
    assert c.get("/kirish", base_url="https://evil.uz").status_code == 400


def test_env_file_is_read(tmp_path, monkeypatch):
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "run.py").read_text(encoding="utf-8").split("load_env(Path(")[0]
    ns = {}
    exec(src.replace("from app import create_app", ""), ns)
    monkeypatch.setenv("RM_T1", "muhit")
    monkeypatch.delenv("RM_T2", raising=False)
    f = tmp_path / ".env"
    f.write_text("# izoh\n\nRM_T1=fayl\nRM_T2 = \"a=b\"\n", encoding="utf-8")
    ns["load_env"](f)
    import os
    assert os.environ["RM_T1"] == "muhit" and os.environ.pop("RM_T2") == "a=b"
    ns["load_env"](tmp_path / "yoq")


# ---------------- So'rov hajmi ----------------

def test_body_limits(app, guest, client, as_role):
    big = b"a" * (security.BODY_MAX + 1)
    r = guest.post("/kirish", data=big, content_type="application/x-www-form-urlencoded", headers=JSON)
    assert r.status_code == 413 and "512 KB" in r.json["error"]
    r = guest.post("/kirish", data=big, content_type="application/x-www-form-urlencoded")
    assert r.status_code == 413 and "Fayl juda katta" in r.get_data(as_text=True)
    u = "/api/urinish/00000000-0000-4000-8000-000000000000/javoblar"
    assert client.post(u, data=b'{"a":"' + big + b'"}', content_type="application/json").status_code == 413
    assert guest.post("/yoq-sahifa", data=big).status_code == 404
    e = as_role("expert")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024)
    r = e.post("/ekspert/mavzular/rasm", data={"image": (io.BytesIO(png * 7), "a.png")}, headers=JSON)
    assert r.status_code == 413 and "6 MB" in r.json["error"]
    r = e.post("/ekspert/mavzular/rasm", data={"image": (io.BytesIO(png * 3), "a.png")}, headers=JSON)
    assert r.status_code == 422 and "2 MB" in r.json["error"]


def test_body_limit_names_are_real_endpoints(app):
    assert set(security.BODY_LIMITS) <= set(app.view_functions)
    from app.services import uploads
    assert max(uploads.MAX_BYTES, xlsx.MAX_BYTES) < security.UPLOAD_MAX == app.config["MAX_CONTENT_LENGTH"]


# ---------------- Sarlavhalar ----------------

def test_headers(client, guest, as_role):
    r = client.get("/app/profil", base_url="https://localhost")
    assert r.headers["Strict-Transport-Security"] and "Cookie" in r.headers["Vary"]
    assert "camera=()" in r.headers["Permissions-Policy"] and r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "no-store" not in r.headers.get("Cache-Control", "")       # oflayn rejim shu sahifalarni keshlaydi
    for c, url in ((guest, "/kirish"), (as_role("admin"), "/admin/"), (as_role("expert"), "/ekspert/")):
        r = c.get(url)
        assert r.headers["Cache-Control"] == "no-store" and "Strict-Transport-Security" not in r.headers, url
        assert "frame-ancestors 'self'" in r.headers["Content-Security-Policy"]


def test_csrf_token_outlives_exam(app):
    """Attestatsiya testi 120 daqiqa: sahifa ochilganda olingan token shu vaqt ichida eskirmasligi kerak."""
    from unittest import mock
    import itsdangerous.timed as timed
    import re
    import time
    a = create_app({**CONFIG, "WTF_CSRF_ENABLED": True})
    c = a.test_client()
    c.get("/_rol/user")
    token = re.search(r'csrf-token" content="([^"]+)"', c.get("/app/profil").text).group(1)
    url = "/api/urinish/00000000-0000-4000-8000-000000000000/javoblar"
    body = {"kind": "exam", "answers": [{"pos": 0, "v": 1}]}
    with mock.patch.object(timed.TimestampSigner, "get_timestamp", lambda self: int(time.time()) + 3 * 3600):
        assert c.post(url, json=body, headers={"X-CSRFToken": token}).status_code == 404      # 400 emas
    assert c.post(url, json=body).status_code == 400


# ---------------- Kiritilgan ma'lumot ----------------

@pytest.mark.parametrize("bad", ["a'b@c.uz", "a\"@b.uz", "a<b>@c.uz", "a@b", "a b@c.uz", "a@b..uz", "a@b.uz\n", "a@" + "b" * 250 + ".uz", "@b.uz"])
def test_bad_emails(guest, bad):
    assert "email" in guest.post("/royxat/email/kod", data={"email": bad.replace("\n", "\nx")}, headers=JSON).json["errors"]


def test_contact_target_is_not_injected_into_alpine(client):
    with client.session_transaction() as s:
        s["contact_change"] = {"method": "email", "target": "x'+alert(1)+'@b.uz"}
    html = client.get("/app/profil").text
    q = chr(92) + "u0027"                                             # JSON qochirishi: apostrof satrdan chiqarmaydi
    assert f"target: &#34;x{q}+alert(1)+{q}@b.uz&#34;" in html and "target: &#39;" not in html


def test_null_bytes_are_not_server_errors(client, guest):
    assert guest.post("/kirish", data={"login": "a\x00@b.uz", "pw": "x\x00y"}, headers=JSON).status_code == 422
    assert client.post("/app/profil/malumotlar", data={"fn": "Di\x00lnoza", "ln": "Karimova"}, headers=JSON).json["ok"]
    r = client.post("/api/urinish/00000000-0000-4000-8000-000000000000/javoblar",
                    json={"kind": "exam", "answers": [{"pos": 0, "v": "a\x00b"}]})
    assert r.status_code == 422


def test_too_long_password_is_rejected(client):
    long = "a1" * 65
    r = client.post("/app/profil/parol", data={"old": "parol1234", "new": long, "new2": long}, headers=JSON)
    assert r.status_code == 422 and "128" in r.json["errors"]["new"]


def _sheet(xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", xml)
    return buf.getvalue()


def test_excel_column_bomb_is_ignored():
    ns = xlsx.NS["m"]
    row = '<row><c r="A1" t="inlineStr"><is><t>a</t></is></c><c r="{}1"><v>1</v></c></row>'
    wrap = f'<worksheet xmlns="{ns}"><sheetData>{{}}</sheetData></worksheet>'
    assert xlsx.read_rows(_sheet(wrap.format(row.format("XFD")))) == [["a"]]
    for ref in ("ZZZZZZZ", "a", "1"):
        with pytest.raises(xlsx.XlsxError):
            xlsx.read_rows(_sheet(wrap.format(row.format(ref))))


def test_excel_bombs_and_broken_files():
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(_sheet("<a>" + " " * (xlsx.MAX_UNZIPPED + 1) + "</a>"))
    entities = "".join(f'<!ENTITY e{n} "{f"&e{n - 1};" * 10}">' for n in range(1, 10))
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(_sheet(f'<!DOCTYPE x [<!ENTITY e0 "aaaaaaaaaa">{entities}]><x>&e9;</x>'))
    good = bytearray(_sheet("<a/>"))
    good[60] ^= 0xFF
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(bytes(good))
