"""8-bosqich: admin paneli — foydalanuvchilar, taklifnomalar, sozlamalar, statistika, jurnal, kunlik faollik."""
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app import invites
from app.cli import demo_user
from app.extensions import db
from app.models import (AuditLog, Certificate, DailyStat, ErrorItem, ExpertInvite, ExpertProfile, Notification, Question, QuestionStat, Section,
                        Setting, Subtopic, TestAttempt, User)
from app.services import activity, admin_stats, notify, xlsx
from app.services import admin_users as au
from app.services import attempts as at
from app.services import plan as pl
from app.services import question_bank as qb
from app.services import settings as conf
from app.services import test_builder as tb
from app.services.timefmt import TASHKENT, now
from tests.conftest import JSON


def _user(n=1, **kw):
    u = User(**{"first_name": f"Ism{n}", "last_name": f"Familiya{n}", "phone": f"+99890000{n:04d}", "role": "user", **kw})
    db.session.add(u)
    db.session.commit()
    return u


def _sub(title):
    return db.session.scalar(select(Subtopic.id).where(Subtopic.title == title))


def _log(action):
    return list(db.session.scalars(select(AuditLog).where(AuditLog.action == action)))


# ---------------- Foydalanuvchilar ----------------

def test_users_list_filters_and_pages(app, as_role):
    with app.app_context():
        today = now().date()
        demo_user("user")
        _user(1, first_name="Zulfiya", last_name="Oripova", region="Buxoro viloyati", exam_date=today + timedelta(days=5))
        _user(2, email="sardor@maktab.uz", is_active=False)
        for n in range(3, 33):
            _user(n)
    c = as_role("admin")
    html = c.get("/admin/foydalanuvchilar").get_data(as_text=True)
    assert "33 nafar · faol 32 · bloklangan 1" in html and "1–25 / 33" in html                 # 32 + namunaviy o'qituvchi
    assert "Zuhra Qodirova</a>" not in html                                                     # ekspertlar bu ro'yxatda yo'q
    assert "26–33 / 33" in c.get("/admin/foydalanuvchilar?sahifa=2").get_data(as_text=True)
    assert c.get("/admin/foydalanuvchilar?sahifa=abc").status_code == 200
    for query, n in (("q=zulfiya", 1), ("q=Oripova+Zul", 1), ("q=0000+0002", 1), ("q=SARDOR@", 1), ("q=%25", 0), ("viloyat=Buxoro+viloyati", 1),
                     ("sana=oy", 1), ("sana=yoq", 32), ("holat=blok", 1), ("q=yoqodam", 0)):
        page = c.get("/admin/foydalanuvchilar?" + query).get_data(as_text=True)
        assert (f"/ {n}</span>" in page) if n else ("Foydalanuvchi topilmadi" in page), query


def test_user_card_shows_real_data(app, as_role):
    with app.app_context():
        uid = demo_user("user").id
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=_sub("if operatori"))
        at.finish(a)
        other = demo_user("expert").id
    c = as_role("admin")
    html = c.get(f"/admin/foydalanuvchilar/{uid}").get_data(as_text=True)
    assert "Dilnoza Karimova" in html and "Dars testi: if operatori" in html and "3 ta xato" in html and "Python: shart operatorlari" in html
    assert c.get(f"/admin/foydalanuvchilar/{other}").status_code == 404                        # ekspert kartasi yo'q
    assert c.get("/admin/foydalanuvchilar/999999").status_code == 404
    assert c.post(f"/admin/foydalanuvchilar/{other}/holat", data={"action": "delete"}).status_code == 404


def test_block_ends_open_session_and_unblock(app, as_role, client):
    with app.app_context():
        uid = demo_user("user").id
    admin = as_role("admin")
    assert client.get("/app/").status_code == 200
    admin.post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "block"})
    assert client.get("/app/").status_code == 302                                              # ochiq sessiya ham yopildi
    assert client.post("/kirish", data={"login": "+998901234567", "pw": "parol1234"}, headers=JSON).status_code == 422
    admin.post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "unblock"})
    assert client.post("/kirish", data={"login": "+998901234567", "pw": "parol1234"}, headers=JSON).json["ok"]
    assert admin.post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "nima"}).status_code == 400
    with app.app_context():
        assert [x.entity_id for x in _log("block") + _log("unblock")] == [str(uid)] * 2


def test_delete_removes_everything(app, as_role):
    with app.app_context():
        u = _user(7)
        uid = u.id
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=_sub("if operatori"))
        at.finish(a)
        db.session.add(AuditLog(actor_id=uid, action="create", entity="user", ip="10.0.0.1"))
        db.session.commit()
    c = as_role("admin")
    r = c.post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "delete"})
    assert r.status_code == 302 and r.location.endswith("/admin/foydalanuvchilar")
    with app.app_context():
        assert db.session.get(User, uid) is None
        assert db.session.scalar(select(func.count()).select_from(TestAttempt)) == 0
        assert db.session.scalar(select(func.count()).select_from(ErrorItem)) == 0
        row = db.session.scalar(select(AuditLog).where(AuditLog.action == "create"))
        assert row.actor_id is None and row.ip is None
        assert _log("delete")[0].data == {}                                                    # jurnalda shaxsiy ma'lumot yo'q


def test_deleted_account_leaves_only_certificates(app, as_role):
    from sqlalchemy import inspect
    with app.app_context():
        u = _user(8, email="sert@maktab.uz", google_sub="g-8")
        uid = u.id
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=_sub("if operatori"))
        at.finish(a)
        db.session.add(Certificate(user_id=uid, attempt_id=a.id, number="INF-2026-1", verify_token="t", full_name="Ism8 Familiya8",
                                   score_pct=90, topic_scores=[{"n": "Mantiq", "p": 90}]))
        notify.add(uid, notify.PASSWORD)
        db.session.commit()
        day = db.session.scalar(select(Certificate.issued_at))
    r = as_role("admin").post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "delete"}, headers=JSON)
    assert r.json["ok"] and "1 ta sertifikati saqlandi" in r.json["message"]
    with app.app_context():
        c = db.session.scalar(select(Certificate))
        assert (c.user_id, c.attempt_id, c.number, c.full_name, c.score_pct, c.issued_at) == (None, None, "INF-2026-1", "Ism8 Familiya8", 90, day)
        assert c.topic_scores == [{"n": "Mantiq", "p": 90}] and c.verify_token == "t"
        # Boshqa hech bir jadvalda foydalanuvchi qatori qolmagan
        for table in db.metadata.sorted_tables:
            for col in table.columns:
                if any(fk.column.table.name == "users" for fk in col.foreign_keys):
                    assert db.session.scalar(select(func.count()).select_from(table).where(col == uid)) == 0, f"{table.name}.{col.name}"
        assert db.session.get(User, uid) is None and inspect(db.engine).has_table("certificates")


def test_reset_link_is_one_time_and_shown_once(app, as_role, guest):
    with app.app_context():
        uid = demo_user("user").id
    c = as_role("admin")
    c.post(f"/admin/foydalanuvchilar/{uid}/holat", data={"action": "reset"})
    html = c.get(f"/admin/foydalanuvchilar/{uid}").get_data(as_text=True)
    (link,) = set(re.findall(r'value="http://localhost(/parol-tiklash/havola/[^"]+)"', html))
    assert "parol-tiklash/havola" not in c.get(f"/admin/foydalanuvchilar/{uid}").get_data(as_text=True)
    assert guest.get(link).status_code == 200
    assert guest.post(link, data={"p1": "qisqa", "p2": "x"}, headers=JSON).status_code == 422
    assert guest.post(link, data={"p1": "yangiparol1", "p2": "yangiparol1"}, headers=JSON).json["ok"]
    assert guest.get(link).status_code == 410 and guest.post(link, data={"p1": "boshqa123", "p2": "boshqa123"}).status_code == 410
    assert guest.post("/kirish", data={"login": "+998901234567", "pw": "yangiparol1"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.scalar(select(Notification.kind)) == notify.PASSWORD
        assert link.split("/")[-1] not in str([x.data for x in db.session.scalars(select(AuditLog))])
        assert len(_log("reset_link")) == len(_log("reset_used")) == 1


@pytest.mark.parametrize("bad", ["", "abc", "1-2-3", "99999999999999999999-1-x", "1--", "-1-5"])
def test_bad_reset_links(guest, bad):
    assert guest.get(f"/parol-tiklash/havola/{bad}").status_code in (404, 410)


def test_reset_link_expires_and_is_bound_to_user(app, monkeypatch):
    with app.app_context(), app.test_request_context():
        u, other = demo_user("user"), _user(9)
        t = invites.reset_token(u)
        assert invites.read_reset(t).id == u.id
        assert invites.read_reset(t.replace(f"{u.id}-", f"{other.id}-", 1)) is None
        u.is_active = False
        assert invites.read_reset(t) is None
        u.is_active = True
        real = invites.time.time
        monkeypatch.setattr(invites.time, "time", lambda: real() + invites.RESET_AGE + 5)
        assert invites.read_reset(t) is None


# ---------------- Attestatsiya sanasi ----------------

def test_exam_date_saved_logged_and_notified(app, as_role):
    with app.app_context():
        uid = demo_user("user").id
        eid = demo_user("expert").id
    c, day = as_role("admin"), (now().date() + timedelta(days=40))
    assert c.post("/admin/foydalanuvchilar/sana", data={"user": uid, "date": day.isoformat(), "notify": "1"}, headers=JSON).json["ok"]
    with app.app_context():
        assert db.session.get(User, uid).exam_date == day
        assert _log("exam_date")[0].data == {"old": None, "new": str(day)}
    home = as_role("user").get("/app/").get_data(as_text=True)
    assert "Attestatsiya sanasi belgilandi" in home and str(day.year) in home
    for bad in ({"user": eid, "date": day.isoformat()}, {"user": "x", "date": day.isoformat()}, {"user": uid, "date": "2000-01-01"}):
        assert c.post("/admin/foydalanuvchilar/sana", data=bad, headers=JSON).status_code == 422


def _xlsx(rows):
    return xlsx.write([au.DATES_HEAD, *rows])


def test_exam_dates_from_excel(app):
    with app.app_context():
        u1, u2, aid = _user(1), _user(2, email="b@maktab.uz"), demo_user("admin").id
        d1, d2 = now().date() + timedelta(days=30), now().date() + timedelta(days=31)
        serial = str((d2 - date(1899, 12, 30)).days)
        assert au.import_dates(_xlsx([["90 000 00 01", d1.strftime("%d.%m.%Y")], ["B@maktab.uz", serial], ["", ""]]), aid) == (2, [])
        assert (u1.exam_date, u2.exam_date) == (d1, d2)
        assert len(_log("exam_date")) == 2 and db.session.scalar(select(func.count()).select_from(Notification)) == 2
        # Xato bo'lsa hech narsa yozilmaydi
        n, errs = au.import_dates(_xlsx([["900000001", d2.isoformat()], ["yoq@maktab.uz", d2.isoformat()], ["b@maktab.uz", "kecha"],
                                         ["b@maktab.uz", "01.01.2020"], ["998900000001", d2.isoformat()]]), aid)
        assert n == 0 and len(errs) == 4 and errs[0].startswith("3-qator") and u1.exam_date == d1
        assert au.import_dates(_xlsx([]), aid)[1] and au.import_dates(b"x", aid)[1]


def test_dates_upload_form(app, as_role):
    import io
    c = as_role("admin")
    sample = c.get("/admin/foydalanuvchilar/sanalar-namuna.xlsx")
    assert xlsx.read_rows(sample.data)[0] == au.DATES_HEAD
    with app.app_context():
        demo_user("user")
        _user(2, email="ism@maktab.uz")
    r = c.post("/admin/foydalanuvchilar/sanalar", data={"file": (io.BytesIO(sample.data), "a.xlsx")}, headers=JSON)
    assert r.status_code == 200 and "2 ta" in r.json["message"]
    for f in ({}, {"file": (io.BytesIO(b"x"), "a.csv")}, {"file": (io.BytesIO(b"x"), "a.xlsx")}):
        assert c.post("/admin/foydalanuvchilar/sanalar", data=f, headers=JSON).status_code == 422


def test_csv_export_is_safe(app, as_role):
    with app.app_context():
        _user(1, first_name="=HYPERLINK(1)", last_name="+cmd", email="a@b.uz")
    r = as_role("admin").get("/admin/foydalanuvchilar.csv?q=a@b.uz")
    text = r.data.decode("utf-8-sig")
    assert r.data.startswith(b"\xef\xbb\xbf") and "'=HYPERLINK(1)" in text and "'+cmd" in text and ";998900000001;" in text
    assert len(text.strip().split("\r\n")) == 2


# ---------------- Ekspertlar va taklifnomalar ----------------

def test_expert_rights_and_block(app, as_role):
    with app.app_context():
        eid = demo_user("expert").id
        uid = demo_user("user").id
        sec = db.session.scalar(select(Section.id).where(Section.title == "Dasturlash"))
    admin, expert = as_role("admin"), as_role("expert")
    r = admin.post(f"/admin/ekspertlar/{eid}", data={"action": "perms", "perms": ["questions", "soxta"], "areas": [sec]})
    assert r.status_code == 302
    with app.app_context():
        p = db.session.get(ExpertProfile, eid)
        assert p.perms == ["questions"] and p.areas == [sec]
    assert expert.get("/ekspert/etirozlar").status_code == 403
    html = admin.get("/admin/ekspertlar").get_data(as_text=True)
    assert "Zuhra Qodirova" in html and '<span class="chip xs">Dasturlash</span>' in html
    assert admin.post(f"/admin/ekspertlar/{eid}", data={"action": "perms", "areas": ["99999"]}).status_code == 400
    assert admin.post(f"/admin/ekspertlar/{uid}", data={"action": "block"}).status_code == 404      # o'qituvchi bu yerdan emas
    admin.post(f"/admin/ekspertlar/{eid}", data={"action": "block"})
    assert expert.get("/ekspert/").status_code == 302
    admin.post(f"/admin/ekspertlar/{eid}", data={"action": "unblock"})
    assert as_role("expert").get("/ekspert/").status_code == 200


def test_invite_token_is_not_stored(app):
    with app.app_context():
        inv = invites.make("Ali Valiyev", "ali@maktab.uz", [], ["questions"])
        t = invites.token(inv)
        sig = t.split("-", 1)[1]
        assert sig not in str([getattr(inv, c.name) for c in ExpertInvite.__table__.columns])
        assert invites.read(t) == ("valid", inv)
        assert invites.read(f"{inv.id + 1}-{sig}")[0] == "invalid" and invites.read(t + "x")[0] == "invalid"
        for bad in ("", "-", "abc", f"{inv.id}", "9" * 30 + "-x"):
            assert invites.read(bad)[0] == "invalid"
        inv.sent_at = datetime.now(timezone.utc) - timedelta(hours=73)
        assert invites.read(t)[0] == "expired"
        invites.resend(inv)
        assert invites.read(t)[0] == "invalid" and invites.read(invites.token(inv))[0] == "valid"
        again = invites.make("Ali Valiyev", "ali@maktab.uz", [], ["review"])
        assert again.id == inv.id and again.perms == ["review"]
        inv.used_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.session.flush()
        invites.make("B C", "b@maktab.uz", [], [])
        assert db.session.scalar(select(func.count()).select_from(ExpertInvite)) == 1             # ishlatilgani 30 kundan keyin o'chadi
        db.session.rollback()


def test_expert_activity_counts(app, as_role):
    from app.models import Objection
    with app.app_context():
        eid, uid = demo_user("expert").id, demo_user("user").id
        sid = _sub("Kalitlar")
        q = qb.save({"subtopic_id": sid, "type": "open", "difficulty": "easy", "text": "yangi?", "data": {}, "answer": {"value": "1"}}, eid)
        q.status, q.source = "review", "ai"
        db.session.commit()
        qb.save({**qb._snapshot(q)}, eid, q.id)
        assert q.reviewer_id == eid and q.status == "approved"
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=sid)
        t0 = datetime.now(timezone.utc) - timedelta(hours=80)
        db.session.add(Objection(user_id=uid, question_id=q.id, question_version=1, attempt_id=a.id, text="", status="accepted",
                                 expert_id=eid, created_at=t0, decided_at=t0 + timedelta(hours=79)))
        db.session.commit()
        (row,) = [r for r in admin_stats.expert_rows() if r["id"] == eid]
        assert (row["created"], row["reviewed"], row["objections"], row["slow"]) == (1, 1, 1, True)
        db.session.delete(a)
        db.session.flush()
        db.session.delete(q)
        db.session.commit()


# ---------------- Sozlamalar ----------------

def _all(**kw):
    return {**{k: i.default for k, i in conf.ITEMS.items()}, **kw}


def test_settings_change_new_tests(app, as_role):
    c = as_role("admin")
    assert c.post("/admin/sozlamalar", data=_all(daily_n=7, exam_n=12, exam_minutes=45), headers=JSON).json["ok"]
    with app.app_context():
        assert {s.key: s.value for s in db.session.scalars(select(Setting))} == {"daily_n": 7, "exam_n": 12, "exam_minutes": 45}
        uid = demo_user("user").id
        assert len(tb.build(uid, "daily").parts[0]) == 7
        spec = tb.build(uid, "exam")
        assert len(spec.parts[0]) == 12 and spec.seconds == 45 * 60
        assert _log("update")[0].data == {"daily_n": [5, 7], "exam_n": [35, 12], "exam_minutes": [120, 45]}
        db.session.rollback()
    assert "12 ta savol · 45 daqiqa" in as_role("user").get("/app/testlar").get_data(as_text=True)
    assert "daily_n: 5 → 7" in c.get("/admin/jurnal?tur=setting").get_data(as_text=True)
    c.post("/admin/sozlamalar", data=_all(), headers=JSON)
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Setting)) == 0                  # standart qiymat saqlanmaydi


@pytest.mark.parametrize("over", [{"daily_n": ""}, {"daily_n": "2"}, {"daily_n": "21"}, {"exam_n": "abc"}, {"pace_days": "-1"}, {"pace_days": "1.5"}])
def test_settings_validation(app, as_role, over):
    r = as_role("admin").post("/admin/sozlamalar", data=_all(**over), headers=JSON)
    assert r.status_code == 422 and set(r.json["errors"]) == set(over)
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Setting)) == 0


def test_corrupt_setting_falls_back_to_default(app):
    with app.app_context():
        db.session.add_all([Setting(key="daily_n", value="buzuq"), Setting(key="exam_n", value=9999), Setting(key="pace_days", value=True)])
        db.session.commit()
        assert (conf.get("daily_n"), conf.get("exam_n"), conf.get("pace_days")) == (5, 35, 2)


def test_plan_uses_settings(app):
    with app.app_context():
        u = demo_user("user")
        conf.save({"pace_days": 4, "reserve_days": 10}, u.id)
        assert pl.pace(u, 5, now().date()) == 4.0
        u.exam_date = now().date() + timedelta(days=60)
        assert pl.pace(u, 5, now().date()) == 10.0
        db.session.rollback()


# ---------------- Faollik va statistika ----------------

PHONE = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"


@pytest.mark.parametrize("ua,kind", [(PHONE, "phone"), ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)", "phone"), ("Mozilla/5.0 (iPad; CPU OS 17)", "tablet"),
                                     ("Mozilla/5.0 (Linux; Android 14; SM-X200) Safari", "tablet"), ("Mozilla/5.0 (Windows NT 10.0)", "desktop"), ("", "desktop")])
def test_device_kind(ua, kind):
    assert activity.device(ua) == kind


def test_activity_is_counted_once_a_day(app, client):
    with app.app_context():
        u = demo_user("user")
        u.last_seen_at = datetime.now(timezone.utc) - timedelta(days=200)
        stamp = u.updated_at
        db.session.commit()
    for _ in range(3):
        client.get("/app/", headers={"User-Agent": PHONE})
    with app.app_context():
        u = demo_user("user")
        assert u.last_seen_at.astimezone(TASHKENT).date() == now().date() and u.updated_at is not None and stamp
        (d,) = db.session.scalars(select(DailyStat))
        assert (d.day, d.active, d.phone, d.tablet, d.pwa) == (now().date(), 1, 1, 0, 0)
        assert activity.touch(u, PHONE) is False


def test_staff_visits_are_not_in_daily_stats(app, as_role):
    as_role("admin").get("/admin/")
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(DailyStat)) == 0
        assert demo_user("admin").last_seen_at is not None


def test_question_stats_grow_on_finish(app):
    with app.app_context():
        uid = demo_user("user").id
        a, _ = tb.get_or_start(uid, "lesson", subtopic_id=_sub("Amaliy protokollar"))
        qid = next(i.question_id for i in a.items if db.session.get(Question, i.question_id).text.startswith("DNS"))
        pos = next(i.position for i in a.items if i.question_id == qid)
        at.save_answers(a, [{"pos": pos, "v": 1, "at": 1}])
        at.finish(a)
        st = db.session.get(QuestionStat, qid)
        assert (st.answered, st.correct) == (1, 1)
        items, *_x = qb.list_questions(qb.Filters(q="DNS server"))
        assert items[0]["pct"] == 100


def test_statistics_numbers(app, as_role):
    with app.app_context():
        for n in range(1, 4):
            _user(n, region="Buxoro viloyati" if n < 3 else None, last_seen_at=datetime.now(timezone.utc) - timedelta(days=100 * n))
        q = db.session.scalar(select(Question).where(Question.text.like("DNS%")))
        db.session.add_all([QuestionStat(question_id=q.id, answered=40, correct=10),
                            DailyStat(day=now().date(), active=4, phone=3, tablet=0, pwa=1)])
        db.session.commit()
        s = admin_stats.overview(30)
        assert s["hard"] == [("Tarmoq protokollari", 75)]
        assert dict(s["regions"]) == {"Buxoro viloyati": 2, "Ko‘rsatilmagan": 1}
        assert s["devices"] == [("Telefon", 75), ("Kompyuter", 25), ("Planshet", 0)] and s["pwa"] == 25
        assert [n for _l, n in s["inactive"]] == [1, 0, 2] and sum(s["signups"]) == 3 and s["signups"][-1] == 3
        assert s["funnel"][0][1] == 3 and s["dau"][-1] == (now().date(), 4) and len(s["dau"]) == 14
    c = as_role("admin")
    for period in ("7", "30", "90", "xato"):
        assert c.get(f"/admin/?davr={period}").status_code == 200
    text = c.get("/admin/hisobot.csv?davr=7").data.decode("utf-8-sig")
    assert "Tarmoq protokollari;75" in text and "Buxoro viloyati;2" in text


def test_statistics_without_data(app, as_role):
    with app.app_context():
        s = admin_stats.overview(7)
        assert s["hard"] == [] and s["devices"] == [] and s["regions"] == []
    assert as_role("admin").get("/admin/").status_code == 200


# ---------------- Jurnal ----------------

def test_journal_pages_and_filter(app, as_role):
    with app.app_context():
        aid = demo_user("admin").id
        db.session.add_all([AuditLog(actor_id=aid, action="block", entity="user", entity_id=str(n), data={}) for n in range(60)])
        db.session.add(AuditLog(actor_id=None, action="yangi_amal", entity="boshqa", entity_id="<b>", data={"title": "<script>"}))
        db.session.commit()
    c = as_role("admin")
    html = c.get("/admin/jurnal").get_data(as_text=True)
    assert "1 / 2" in html and "yangi_amal" in html and "<script>1" not in html and "&lt;script&gt;" in html
    assert "bloklandi" in c.get("/admin/jurnal?sahifa=2").get_data(as_text=True)
    assert "Hali yozuv yo‘q" in c.get("/admin/jurnal?tur=setting").get_data(as_text=True)
    for role in ("user", "expert"):
        assert as_role(role).get("/admin/jurnal").status_code == 403
