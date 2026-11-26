"""10: fon vazifalari — navbat, jadval, worker, tozalash, rasm fayllari, savol zaxirasi, admin sahifasi."""
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from flask import has_app_context
from sqlalchemy import func, select, text

import worker
from app import create_app, create_worker_app
from app import worker as loop
from app.cli import demo_user
from app.extensions import db
from app.models import AuditLog, ExpertInvite, Job, Notification, Question, Subtopic, Topic, User, UserSeen
from app.services import jobs, notify, seen, stock, tasks, uploads
from app.services.timefmt import TASHKENT
from tests.conftest import CONFIG

NOW = datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc)      # Toshkentda 26-noyabr 01:00, payshanba


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield app


@pytest.fixture()
def ran():
    return []


@pytest.fixture()
def toy(ran, monkeypatch):
    """Sinov vazifalari: tez, sekin, jadvaldagi."""
    jobs.load_tasks()
    reg = dict(jobs.TASKS)
    monkeypatch.setattr(jobs, "TASKS", reg)
    reg.clear()

    def run(data):
        ran.append(data)
        if data.get("raise"):
            raise data["raise"] if isinstance(data["raise"], Exception) else {
                "retry": jobs.Retry(90, "limit"), "fatal": jobs.Fatal("manzil yo'q")}.get(data["raise"], ValueError("xato\nikkinchi qator"))
        return {"n": len(ran)}
    for t in (jobs.Task("tez", run, "Tez", tries=3), jobs.Task("sekin", run, "Sekin", lane=jobs.SLOW),
              jobs.Task("tungi", run, "Tungi", lane=jobs.SLOW, tries=2, every=jobs.Daily(2, 30))):
        reg[t.kind] = t
    return reg


def add(kind="tez", data=None, **kw):
    jobs.add(kind, data, **kw)
    db.session.commit()


def only() -> Job:
    db.session.rollback()
    return db.session.scalars(select(Job).execution_options(populate_existing=True)).one()


def count() -> int:
    db.session.rollback()
    return db.session.scalar(select(func.count()).select_from(Job))


def in_seconds(j: Job) -> float:
    return (j.run_at - datetime.now(timezone.utc)).total_seconds()


def due(j: Job):
    db.session.execute(text("UPDATE jobs SET run_at = now() WHERE id = :i"), {"i": j.id})
    db.session.commit()


# ---------------- Navbat ----------------

def test_done_job_is_removed(ctx, toy, ran):
    add(data={"user": 5})
    assert jobs.run_due() == 1 and ran == [{"user": 5}] and count() == 0 and jobs.run_due() == 0


def test_job_belongs_to_transaction(ctx, toy, ran):
    jobs.add("tez")
    db.session.rollback()
    assert jobs.run_due() == 0
    with pytest.raises(ValueError):
        jobs.add("yoq-tur")


def test_delay_and_order(ctx, toy, ran):
    add(data={"n": 1}, delay=60)
    add(data={"n": 2})
    add(data={"n": 3})
    assert jobs.run_due() == 2 and ran == [{"n": 2}, {"n": 3}]
    assert 50 < jobs.next_in() <= 60 and jobs.next_in(jobs.SLOW) is None


def test_key_keeps_one_job_with_last_data(ctx, toy, ran):
    for n in range(3):
        add(data={"n": n}, key="x")
    assert jobs.run_due() == 1 and ran == [{"n": 2}]


def test_key_added_while_running_runs_again(ctx, toy, ran):
    add(data={"n": 1}, key="x")
    c = jobs.claim()
    add(data={"n": 2}, key="x")
    assert jobs.execute(c) and count() == 1                          # eski bajarilish yangi so'rovni o'chirib yubormadi
    assert jobs.run_due() == 1 and ran == [{"n": 1}, {"n": 2}] and count() == 0


def test_retry_backoff_then_dead(ctx, toy, ran):
    add(data={"raise": "xato"})
    for n, wait in ((1, 30), (2, 120)):
        assert jobs.run_due() == 1
        j = only()
        assert j.attempts == n and wait - 5 < in_seconds(j) <= wait and j.error == "ValueError: xato"
        due(j)
    jobs.run_due()
    j = only()
    assert j.run_at is None and len(ran) == 3 and jobs.failed() == 1 and jobs.run_due() == 0
    jobs.run_now(j)
    db.session.commit()
    assert jobs.run_due() == 1 and only().attempts == 1


def test_retry_later_is_not_counted_and_fatal_stops(ctx, toy):
    add(data={"raise": "retry"})
    jobs.run_due()
    j = only()
    assert j.attempts == 0 and 80 < in_seconds(j) <= 90 and "limit" in j.error
    db.session.delete(j)
    add(data={"raise": "fatal"})
    jobs.run_due()
    assert only().run_at is None and "manzil" in only().error


def test_failed_job_rolls_back_its_writes(ctx, toy, monkeypatch):
    def run(_data):
        db.session.add(User(first_name="A", last_name="B", email="a@b.uz"))
        db.session.flush()
        raise RuntimeError("yarmida")
    toy["tez"] = jobs.Task("tez", run, "Tez")
    add()
    jobs.run_due()
    assert User.by_login("a@b.uz") is None and only().attempts == 1


def test_error_text_has_no_personal_data(ctx, toy):
    def run(_data):
        for _n in (1, 2):
            db.session.add(User(first_name="A", last_name="B", email="maxfiy@b.uz"))
        db.session.flush()
    toy["tez"] = jobs.Task("tez", run, "Tez")
    add()
    jobs.run_due()
    assert "IntegrityError" in only().error and "maxfiy" not in only().error


def test_crashed_worker_job_is_taken_again_after_lease(ctx, toy, ran):
    add()
    assert jobs.claim() and jobs.claim() is None                     # worker shu yerda qulab tushdi
    assert 590 < in_seconds(only()) <= 600
    due(only())
    assert jobs.run_due() == 1 and len(ran) == 1 and count() == 0


def test_poison_job_stops_after_tries(ctx, toy, ran):
    add()
    for _n in range(3):
        jobs.claim()
        due(only())
    assert jobs.run_due() == 1 and not ran and only().run_at is None


def test_late_finish_does_not_touch_other_workers_job(ctx, toy):
    add(data={"raise": "xato"})
    old = jobs.claim()
    due(only())
    new = jobs.claim()
    jobs.execute(old)
    j = only()
    assert j.run_at == new.until and j.error is None


def test_parallel_workers_never_take_same_job(app, toy, ran):
    with app.app_context():
        for n in range(30):
            jobs.add("tez", {"n": n})
        db.session.commit()

    def run():
        with app.app_context():
            jobs.run_due()
    threads = [threading.Thread(target=run) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(d["n"] for d in ran) == list(range(30))


def test_lanes(ctx, toy, ran):
    add("sekin", {"n": "sekin"})
    add("tez", {"n": "tez"})
    assert jobs.run_due(jobs.FAST) == 1 and ran == [{"n": "tez"}]
    db.session.execute(text("INSERT INTO jobs (kind, run_at) VALUES ('kelajak', now())"))
    db.session.commit()
    assert jobs.run_due(jobs.FAST) == 0 and jobs.run_due(jobs.SLOW) == 2
    assert "kelajak" in only().error and only().run_at is None


# ---------------- Jadval ----------------

@pytest.mark.parametrize("every, expected", [
    (jobs.Daily(2, 30), (26, 2, 30)), (jobs.Daily(0, 30), (27, 0, 30)), (jobs.Daily(1, 0), (27, 1, 0)),
    (jobs.Daily(3, 30, weekday=6), (29, 3, 30)), (jobs.Daily(2, 0, weekday=3), (26, 2, 0)), (jobs.Daily(0, 0, weekday=3), (33, 0, 0))])
def test_next_time_is_in_tashkent(every, expected):
    at = every.next(NOW)
    day, h, m = expected
    assert at == datetime(2026, 11, 1, h, m, tzinfo=TASHKENT) + timedelta(days=day - 1)


def test_schedule_is_created_once_and_old_removed(ctx, toy):
    db.session.execute(text("INSERT INTO jobs (kind, key, run_at) VALUES ('eski', 'cron:eski', now())"))
    jobs.ensure_schedule(NOW)
    first = only()
    assert first.key == "cron:tungi" and first.run_at == datetime(2026, 11, 26, 2, 30, tzinfo=TASHKENT)
    jobs.ensure_schedule(NOW + timedelta(days=3))
    assert only().run_at == first.run_at                              # o'tib ketgan vaqt surilmaydi: ishga tushganda bajariladi


def test_schedule_moves_to_next_slot(ctx, toy, ran):
    jobs.ensure_schedule(NOW)
    due(only())
    assert jobs.run_due() == 1 and jobs.run_due() == 0
    j = only()
    assert j.run_at > datetime.now(timezone.utc) and j.done_at and j.attempts == 0 and j.result["n"] == 1 and "ms" in j.result


def test_failing_schedule_never_stops(ctx, toy):
    def run(_data):
        raise ValueError("tunda")
    toy["tungi"] = jobs.Task("tungi", run, "Tungi", lane=jobs.SLOW, tries=2, every=jobs.Daily(2, 30))
    jobs.ensure_schedule()
    for _n in range(2):
        due(only())
        jobs.run_due()
    j = only()
    assert j.run_at is not None and j.attempts == 0 and "tunda" in j.error and jobs.failed() == 1


def test_real_tasks_are_registered_and_slow(ctx):
    reg = jobs.load_tasks()
    assert {"archive", "cleanup", "files", "stock"} <= set(reg)
    assert all(t.lane == jobs.SLOW and t.every for t in (reg[k] for k in ("archive", "cleanup", "files", "stock")))
    jobs.ensure_schedule()
    assert count() == len([t for t in reg.values() if t.every])


# ---------------- Worker ----------------

def test_worker_wakes_on_notify_and_stops(app, toy, ran, monkeypatch):
    monkeypatch.setattr(loop, "POLL", 60)                             # so'rov bilan emas, NOTIFY bilan uyg'onsin
    w = loop.Worker(create_worker_app(CONFIG))
    main = threading.Thread(target=w.run)
    main.start()
    try:
        with app.app_context():
            _until(lambda: jobs.worker_alive())
            time.sleep(0.5)
            add(data={"n": 1})
            t = time.perf_counter()
            _until(lambda: ran)
            assert time.perf_counter() - t < 5
            _until(lambda: count() == 1)                              # faqat jadvaldagi qator qoldi
    finally:
        w.close(10)
        main.join(15)
    assert not main.is_alive() and not any(t.is_alive() for t in w.threads)
    with app.app_context():
        _until(lambda: not jobs.worker_alive())


def test_second_worker_stands_by_then_takes_over(app, toy, ran, monkeypatch):
    monkeypatch.setattr(loop, "POLL", 1)
    a, b = (loop.Worker(create_worker_app(CONFIG)) for _n in range(2))
    ta, tb = (threading.Thread(target=w.run) for w in (a, b))
    try:
        ta.start()
        with app.app_context():
            _until(lambda: a.threads)
            tb.start()
            time.sleep(2)
            assert not b.threads                                      # ikkinchisi kutib turadi
            a.close(10)
            _until(lambda: b.threads)
            add(data={"n": 1})
            _until(lambda: ran)
    finally:
        for w in (a, b):
            w.close(10)
        ta.join(15)
        tb.join(15)


def test_worker_embeds_once_on_first_request(app, toy, monkeypatch):
    monkeypatch.setenv("RM_WORKER", "1")
    started = []
    monkeypatch.setattr(loop.Worker, "run", lambda self: started.append(self))
    web = create_app({**CONFIG, "TESTING": False})
    assert not started
    c = web.test_client()
    for _n in range(3):
        c.get("/kirish")
    _until(lambda: started, 5)
    assert len(started) == 1 and web.extensions["worker"] is started[0]
    assert "worker" not in app.extensions                             # testlarda va RM_WORKER'siz ishga tushmaydi


def _until(check, seconds=15):
    end = time.perf_counter() + seconds
    while not check():
        assert time.perf_counter() < end, "kutilgan holat kelmadi"
        if has_app_context():
            db.session.rollback()
        time.sleep(0.1)


def test_worker_once(app, toy, ran, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", CONFIG["SQLALCHEMY_DATABASE_URI"])
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setattr(worker, "load_env", lambda: None)
    with app.app_context():
        add(data={"n": 1})
    assert worker.main(["--bir-marta"]) == 0 and "Bajarildi: 1" in capsys.readouterr().out and ran == [{"n": 1}]
    assert worker.main(["--yoq"]) == 2


def test_worker_app_is_light(app):
    w = create_worker_app(CONFIG)
    assert not w.blueprints and "csrf" not in w.extensions and "sqlalchemy" in w.extensions


# ---------------- Vazifalar ----------------

def test_cleanup(ctx):
    uid = demo_user("user").id
    now = datetime.now(timezone.utc)
    notify.add(uid, notify.PASSWORD)
    notify.add(uid, notify.PASSWORD)
    db.session.flush()
    first = db.session.scalar(select(func.min(Notification.id)))
    db.session.execute(text("UPDATE notifications SET created_at = now() - interval '31 days' WHERE id = :i"), {"i": first})
    db.session.execute(text("INSERT INTO rate_limits VALUES (1, now() - interval '1 second', 1), (2, now() + interval '1 hour', 1)"))
    for n, used in ((1, 31), (2, 5), (3, None)):
        db.session.add(ExpertInvite(name="A B", contact=f"{n}@b.uz", used_at=now - timedelta(days=used) if used else None))
    db.session.execute(text("INSERT INTO jobs (kind, error) VALUES ('tez', 'yangi')"))
    db.session.execute(text("INSERT INTO jobs (kind, error, done_at) VALUES ('tez', 'eski', now() - interval '31 days')"))
    db.session.commit()
    tasks.cleanup({})
    db.session.commit()
    left = lambda t: db.session.scalar(text(f"SELECT count(*) FROM {t}"))                        # noqa: E731
    assert (left("notifications"), left("rate_limits"), left("expert_invites"), left("jobs")) == (1, 1, 2, 1)
    assert only().error == "yangi" and only().done_at is not None and only().run_at is None


def test_archive_task(ctx):
    assert tasks.archive_old({}) == {"n": 0}


def test_dev_server_never_deletes_files(ctx, monkeypatch):
    monkeypatch.setattr(ctx, "debug", True)
    monkeypatch.setattr(tasks.os, "remove", lambda *_a: pytest.fail("o'chirildi"))
    assert tasks.orphan_files({}) == {"n": 0, "kb": 0}


def test_orphan_files(ctx, tmp_path):
    ctx.static_folder = str(tmp_path)
    folder = tmp_path / "uploads" / "q"
    assert tasks.orphan_files({}) == {"n": 0, "kb": 0}
    folder.mkdir(parents=True)
    names = {k: f"{k * 24}.png" for k in "abcdef"}
    for n in names.values():
        (folder / n).write_bytes(b"x" * 2048)
    (folder / "boshqa.png").write_bytes(b"x")
    old = time.time() - 8 * 86400
    for k in "abcde":
        os.utime(folder / names[k], (old, old))
    os.utime(folder / "boshqa.png", (old, old))
    # a — savolda, b — eski versiyada, c — dars blokida; d, e — hech qayerda; f — hali yangi
    q = db.session.scalar(select(Question).where(Question.status == "approved").limit(1))
    db.session.execute(text("UPDATE questions SET data = data || jsonb_build_object('image', jsonb_build_object('src', cast(:s as text))) WHERE id = :i"),
                       {"s": f"uploads/q/{names['a']}", "i": q.id})
    db.session.execute(text("UPDATE question_versions SET snapshot = jsonb_build_object('data', cast(:s as text)) WHERE id = "
                            "(SELECT min(id) FROM question_versions)"), {"s": f"uploads/q/{names['b']}"})
    db.session.execute(text("UPDATE content_blocks SET data = data || jsonb_build_object('src', cast(:s as text)) WHERE id = "
                            "(SELECT min(id) FROM content_blocks)"), {"s": f"uploads/q/{names['c']}"})
    assert tasks.orphan_files({}) == {"n": 2, "kb": 4}
    db.session.rollback()
    assert sorted(f.name for f in folder.iterdir()) == sorted([names[k] for k in "abcf"] + ["boshqa.png"])


def test_reupload_refreshes_file_age(ctx, tmp_path):
    import io

    from werkzeug.datastructures import FileStorage
    ctx.static_folder = str(tmp_path)
    img = lambda: FileStorage(io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 10), "a.png")            # noqa: E731
    path = tmp_path / uploads.save_image(img())
    os.utime(path, (1, 1))
    uploads.save_image(img())
    assert time.time() - path.stat().st_mtime < 60 and tasks.orphan_files({})["n"] == 0


def _bank_subtopic() -> tuple[int, list[int]]:
    """Shabloni yo'q, savoli eng ko'p kichik mavzu."""
    rows = {}
    for sid, gens, qid in db.session.execute(
            select(Subtopic.id, Subtopic.generators, Question.id).join(Question, Question.subtopic_id == Subtopic.id)
            .join(Topic, Topic.id == Subtopic.topic_id).where(Question.status == "approved", Topic.is_published.is_(True))):
        if not gens:
            rows.setdefault(sid, []).append(qid)
    return max(rows.items(), key=lambda kv: len(kv[1]))


def test_stock_counts_active_teachers_running_out(ctx):
    sid, qids = _bank_subtopic()
    assert stock.compute() == {"n": 0, "low": []}
    u = demo_user("user")
    u.last_seen_at = datetime.now(timezone.utc)
    seen.mark(u.id, qids)
    for n, days in ((1, 1), (2, 40)):                                 # ikkinchisi 40 kundan beri kirmagan
        x = User(first_name="A", last_name="B", email=f"{n}@b.uz", role="user", last_seen_at=datetime.now(timezone.utc) - timedelta(days=days))
        db.session.add(x)
        db.session.flush()
        seen.mark(x.id, qids[:max(1, len(qids) - 4)])
    db.session.commit()
    left = len(qids) - max(1, len(qids) - 4)
    assert stock.compute() == {"n": 1, "low": [[sid, 2, 2 if left < 3 else 1]]}


def test_stock_matches_sql_bitmap(ctx):
    """Python'dagi bit hisobi PostgreSQL get_bit bilan bir xil."""
    u = demo_user("user")
    for sid, (lo, hi, mask) in stock._masks().items():
        qids = list(db.session.scalars(select(Question.id).where(Question.subtopic_id == sid, Question.status == "approved")))
        seen.mark(u.id, qids[::2])
        bits = db.session.scalar(select(UserSeen.bits).where(UserSeen.user_id == u.id))
        new = db.session.scalar(select(func.count(Question.id)).where(Question.id.in_(qids), seen.is_new(u.id)))
        assert mask.bit_count() - (int.from_bytes(bits[lo:hi], "little") & mask).bit_count() == new


def test_stock_skips_subtopics_with_templates(ctx):
    with_gen = set(db.session.scalars(select(Subtopic.id).where(func.jsonb_array_length(Subtopic.generators) > 0)))
    assert with_gen and not with_gen & set(stock._masks())


def test_expert_sees_running_out_lessons(app, as_role):
    e = as_role("expert")
    assert "yangi savol tugayapti" not in e.get("/ekspert/").text
    with app.app_context():
        sid, _q = _bank_subtopic()
        name = db.session.get(Subtopic, sid).title
        db.session.add(Job(kind="stock", key="cron:stock", run_at=datetime.now(timezone.utc) + timedelta(days=1),
                           result={"n": 1, "low": [[sid, 7, 3], [999_999, 1, 0]]}))
        db.session.commit()
        assert [r["id"] for r in stock.current()] == [sid] and stock.current(set()) == []
    html = e.get("/ekspert/").text
    assert "1 ta kichik mavzuda o‘qituvchilarga yangi savol tugayapti" in html and name in html and "7 ta o‘qituvchida kam qoldi" in html


# ---------------- Admin ----------------

def test_admin_page_empty_and_worker_warning(app, as_role):
    c = as_role("admin")
    html = c.get("/admin/vazifalar").text
    assert "Fon jarayoni ishlamayapti" in html and "hali biror marta ishga tushmagan" in html
    assert "Fon jarayoni ishlamayapti" in c.get("/admin/").text


def test_admin_runs_and_deletes(app, as_role):
    c = as_role("admin")
    with app.app_context():
        jobs.ensure_schedule()
        db.session.add(Job(kind="stock", error="ValueError: <b>x</b>"))
        db.session.add(Job(kind="yoq", run_at=datetime.now(timezone.utc) + timedelta(days=1)))
        db.session.commit()
        cron = db.session.scalar(select(Job.id).where(Job.key == "cron:archive"))
        dead = db.session.scalar(select(Job.id).where(Job.run_at.is_(None)))
    html = c.get("/admin/vazifalar").text
    assert "Eski testlarni siqish" in html and "&lt;b&gt;x" in html and "Navbatda 1 ta vazifa" in html
    assert "1 ta fon vazifasi xato bilan" in c.get("/admin/").text
    assert c.post("/admin/vazifalar", data={"id": cron, "action": "run"}).status_code == 302
    assert c.post("/admin/vazifalar", data={"id": cron, "action": "delete"}).status_code == 400       # jadval o'chirilmaydi
    for bad in ({"id": "0", "action": "run"}, {"id": "x", "action": "run"}, {"id": cron, "action": "boshqa"}):
        assert c.post("/admin/vazifalar", data=bad).status_code == 400
    assert c.post("/admin/vazifalar", data={"id": dead, "action": "delete"}).status_code == 302
    with app.app_context():
        assert db.session.get(Job, dead) is None and db.session.get(Job, cron).run_at <= datetime.now(timezone.utc)
        assert {a for a in db.session.scalars(select(AuditLog.action).where(AuditLog.entity == "job"))} == {"run", "delete"}
        assert jobs.run_due() == 1
        assert db.session.get(Job, cron).result["n"] == 0
    html = c.get("/admin/vazifalar").text
    assert "Bugun," in html and "0 ta · 0." in html
    assert "qo‘lda ishga tushirildi" in c.get("/admin/jurnal?tur=job").text


@pytest.mark.parametrize("role", ["user", "expert"])
def test_only_admin(as_role, role):
    assert as_role(role).get("/admin/vazifalar").status_code == 403
