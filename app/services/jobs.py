"""Fon vazifalari navbati: PostgreSQL (SKIP LOCKED + NOTIFY), Redis'siz. Bajaruvchi — app/worker.py, vazifalar — tasks.py.

- add() chaqirgan tranzaksiya bilan birga yoziladi: rollback bo'lsa vazifa ham yo'q, commit bo'lsa yo'qolmaydi.
- Olingan vazifaning run_at'i ijara muddatiga suriladi. Worker qulasa, muddat o'tgach boshqa worker qaytadan oladi; shuning
  uchun vazifa ikki marta bajarilsa ham zarar bo'lmasin (idempotent). Faqat bazaga yozadigan vazifa commit qilmasin: ishi va
  navbatdan o'chishi bitta tranzaksiyada bo'ladi.
- Xato: 30 s, 2 daq, 8 daq, 32 daq, 2 soat dan keyin qayta. Urinishlar tugasa run_at = NULL: admin panelida ko'rinadi.
  Jadvaldagi vazifa («cron:…») to'xtab qolmaydi — keyingi vaqtiga o'tadi.
- Ikki yo'lak: tez (kod, xabar) va sekin (tungi ishlar, AI) — tungi arxiv xatni kutdirmaydi.
"""
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from ..extensions import db
from ..models import Job
from .timefmt import TASHKENT

CHANNEL = "jobs"
FAST, SLOW = "fast", "slow"
BACKOFF, BACKOFF_MAX = 30, 2 * 3600
log = logging.getLogger("jobs")


class Retry(Exception):
    """Vazifa hozir bajarilmaydi (masalan, provayder limiti): shuncha soniyadan keyin, urinish sanalmaydi."""

    def __init__(self, seconds: int, reason: str = ""):
        super().__init__(reason)
        self.seconds = seconds


class Fatal(Exception):
    """Qayta urinishdan foyda yo'q (masalan, manzil noto'g'ri): darhol to'xtatiladi."""


@dataclass(frozen=True)
class Daily:
    """Har kuni (weekday berilsa — haftada bir) Toshkent vaqti bilan."""
    hour: int
    minute: int = 0
    weekday: int | None = None          # 0 — dushanba … 6 — yakshanba

    def next(self, now: datetime) -> datetime:
        at = now.astimezone(TASHKENT).replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        while at <= now or (self.weekday is not None and at.weekday() != self.weekday):
            at += timedelta(days=1)
        return at


@dataclass(frozen=True)
class Task:
    kind: str
    run: Callable[[dict], dict | None]
    label: object
    lane: str = FAST
    lease: int = 600                    # soniya: shundan uzoq ishlamaydi
    tries: int = 6
    every: Daily | None = None


TASKS: dict[str, Task] = {}


def task(kind: str, label, **kw):
    def wrap(fn):
        TASKS[kind] = Task(kind, fn, label, **kw)
        return fn
    return wrap


def load_tasks() -> dict[str, Task]:
    from . import tasks  # noqa: F401 — vazifalar ro'yxatga olinadi
    return TASKS


def _now() -> datetime:
    return datetime.now(timezone.utc)


def wake() -> None:
    db.session.execute(select(func.pg_notify(CHANNEL, "")))      # commit paytida yetib boradi


# ---------------- Navbatga qo'yish ----------------

def add(kind: str, data: dict | None = None, *, key: str | None = None, delay: int = 0) -> None:
    """Commit qilmaydi. key bir xil bo'lsa vazifa bitta qoladi (yangi data bilan); u shu payt bajarilayotgan bo'lsa, yana bir
    marta bajariladi — bajarilish boshlanganidan keyingi o'zgarish yo'qolmaydi."""
    if kind not in load_tasks():
        raise ValueError(f"noma'lum vazifa: {kind}")
    stmt = insert(Job).values(kind=kind, data=data or {}, key=key, run_at=func.now() + timedelta(seconds=delay))
    if key:
        stmt = stmt.on_conflict_do_update(
            index_elements=[Job.key], index_where=Job.key.is_not(None),
            set_={"kind": stmt.excluded.kind, "data": stmt.excluded.data, "run_at": stmt.excluded.run_at, "attempts": 0, "error": None})
    db.session.execute(stmt)
    wake()


def ensure_schedule(now: datetime | None = None) -> None:
    """Jadvaldagi vazifalar qatorlari: yo'qlari qo'shiladi, koddan olib tashlanganlari o'chadi. Commit qiladi."""
    now = now or _now()
    cron = {f"cron:{t.kind}": t for t in load_tasks().values() if t.every}
    for key, t in cron.items():
        db.session.execute(insert(Job).values(kind=t.kind, key=key, run_at=t.every.next(now)).on_conflict_do_nothing())
    db.session.execute(text("DELETE FROM jobs WHERE key LIKE 'cron:%' AND key <> ALL(:keep)"), {"keep": list(cron)})
    db.session.commit()


def run_now(job: Job) -> None:
    """Admin: hozir bajarish yoki to'xtab qolganini qayta boshlash. Commit qilmaydi."""
    job.run_at, job.attempts = func.now(), 0
    db.session.flush()
    wake()


# ---------------- Bajarish ----------------

@dataclass(frozen=True)
class Claim:
    id: int
    kind: str
    key: str | None
    data: dict
    attempts: int
    until: datetime                     # ijara belgisi: shu o'zgargan bo'lsa, vazifa endi bizniki emas


def claim(lane: str | None = None) -> Claim | None:
    """Vaqti kelgan bitta vazifani oladi (commit qiladi)."""
    tasks = load_tasks()
    q = select(Job).where(Job.run_at <= func.now()).order_by(Job.run_at, Job.id).limit(1).with_for_update(skip_locked=True)
    if lane:
        kinds = [k for k, t in tasks.items() if t.lane == lane]
        # Noma'lum tur (eski worker, yangi kod) sekin yo'lakda qoladi
        q = q.where(Job.kind.in_(kinds) if lane == FAST else Job.kind.not_in([k for k in tasks if k not in kinds]))
    job = db.session.scalar(q.execution_options(populate_existing=True))
    if job is None:
        db.session.rollback()
        return None
    t = tasks.get(job.kind)
    until = _now() + timedelta(seconds=t.lease if t else 600)
    job.run_at, job.attempts = until, job.attempts + 1
    c = Claim(job.id, job.kind, job.key, dict(job.data), job.attempts, until)
    db.session.commit()
    return c


def _finish(c: Claim, **values) -> bool:
    """Faqat ijara hali bizniki bo'lsa yozadi."""
    return bool(db.session.execute(update(Job).where(Job.id == c.id, Job.run_at == c.until).values(**values)
                                   .execution_options(synchronize_session=False)).rowcount)


def _short(e: BaseException) -> str:
    """Xato matni: birinchi qator. SQL parametrlari kirmaydi (hide_parameters)."""
    lines = str(e).strip().splitlines()
    return f"{type(e).__name__}: {lines[0] if lines else ''}"[:200]


def execute(c: Claim) -> bool:
    """Vazifani bajaradi. Natija: muvaffaqiyatlimi."""
    t = load_tasks().get(c.kind)
    cron = bool(t and t.every and c.key == f"cron:{c.kind}")
    started = time.perf_counter()
    try:
        if t is None:
            raise Fatal(f"noma'lum vazifa: {c.kind}")
        if c.attempts > t.tries:                      # worker shu vazifada qayta-qayta qulagan
            raise Fatal("urinishlar tugadi")
        out = dict(t.run(c.data) or {})
        if cron:
            out["ms"] = round((time.perf_counter() - started) * 1000)
            _finish(c, run_at=t.every.next(_now()), attempts=0, done_at=func.now(), error=None, result=out)
        else:
            db.session.execute(text("DELETE FROM jobs WHERE id = :id AND run_at = :until"), {"id": c.id, "until": c.until})
        db.session.commit()
        return True
    except Retry as e:
        db.session.rollback()
        _finish(c, run_at=_now() + timedelta(seconds=max(1, e.seconds)), attempts=c.attempts - 1, error=_short(e) if str(e) else None)
    except Exception as e:                            # noqa: BLE001 — bitta vazifa worker'ni to'xtatmasin
        db.session.rollback()
        log.exception("vazifa %s #%s", c.kind, c.id)
        dead = isinstance(e, Fatal) or t is None or c.attempts >= t.tries
        if not dead:
            _finish(c, run_at=_now() + timedelta(seconds=min(BACKOFF * 4 ** (c.attempts - 1), BACKOFF_MAX)), error=_short(e))
        elif cron:
            _finish(c, run_at=t.every.next(_now()), attempts=0, error=_short(e))
        else:
            _finish(c, run_at=None, error=_short(e))
    db.session.commit()
    return False


def run_due(lane: str | None = None, limit: int | None = None) -> int:
    """Vaqti kelgan hamma vazifani bajaradi. Natija: bajarishga uringanlar soni."""
    n = 0
    while (limit is None or n < limit) and (c := claim(lane)) is not None:
        execute(c)
        db.session.remove()
        n += 1
    return n


def next_in(lane: str | None = None) -> float | None:
    """Keyingi vazifagacha soniya (navbat bo'sh — None)."""
    q = select(func.extract("epoch", func.min(Job.run_at) - func.now())).where(Job.run_at.is_not(None))
    if lane:
        mine = [k for k, t in load_tasks().items() if t.lane == lane]
        q = q.where(Job.kind.in_(mine))
    s = db.session.scalar(q)
    db.session.rollback()
    return None if s is None else max(0.0, float(s))


# ---------------- Holat (admin paneli) ----------------

APP_NAME = "raqamli_worker"


def worker_alive() -> bool:
    """Ishlab turgan worker'ning tinglovchi ulanishi bor-yo'qligi (alohida «yurak urishi» yozuvi kerak emas)."""
    return bool(db.session.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE application_name = :n "
                                       "AND datname = current_database())"), {"n": APP_NAME}))


def failed() -> int:
    """To'xtab qolgan vazifalar va oxirgi marta xato bergan jadval vazifalari."""
    return db.session.scalar(select(func.count()).select_from(Job).where(
        Job.run_at.is_(None) | (Job.key.like("cron:%") & Job.error.is_not(None))))
