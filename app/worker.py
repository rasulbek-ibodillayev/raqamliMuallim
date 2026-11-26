"""Fon vazifalarini bajaruvchi: navbatni tinglaydi va ikki yo'lakda bajaradi (services/jobs.py).

Ikki xil ishga tushadi:
- RM_WORKER=1 — veb-jarayonning ichida (birinchi so'rovda). Qo'shimcha RAM deyarli yo'q; alohida jarayon ≈ 90 MB olardi
  (Flask, SQLAlchemy va psycopg'ning o'zi 85 MB). Bir nechta gunicorn worker bo'lsa ham faqat bittasi faol (advisory lock),
  u to'xtasa 30 soniyada boshqasi davom ettiradi;
- `python worker.py` — alohida jarayon (yuklama oshganda, RM_WORKER'siz).

Navbat bo'sh turganda baza qayta-qayta so'ralmaydi: yangi vazifa haqida NOTIFY keladi. To'xtaganda ulgurmagan vazifa ijara
muddati o'tgach qaytadan bajariladi.
"""
import logging
import os
import threading

POLL = 30            # soniya: NOTIFY yetib kelmasa ham shundan kech qolmaydi
LOCK = (8, 1)        # pg advisory lock: faol bajaruvchi bitta
log = logging.getLogger("jobs")


class Worker:
    def __init__(self, app):
        from .services import jobs
        self.app, self.stop = app, threading.Event()
        self.bells = {name: threading.Event() for name in (jobs.FAST, jobs.SLOW)}
        self.threads: list[threading.Thread] = []

    def _lane(self, name: str) -> None:
        from .services import jobs
        bell = self.bells[name]
        while not self.stop.is_set():
            wait = POLL
            try:
                with self.app.app_context():
                    bell.clear()
                    while not self.stop.is_set() and jobs.run_due(name, limit=1):
                        pass
                    left = jobs.next_in(name)
                    wait = POLL if left is None else min(POLL, max(0.2, left))
            except Exception:                          # noqa: BLE001 — baza uzildi: kutib, qayta ulanadi
                log.exception("yo'lak %s", name)
                wait = 5
            bell.wait(wait)

    def ring(self) -> None:
        for bell in self.bells.values():
            bell.set()

    def _start_lanes(self) -> None:
        from .services import jobs
        with self.app.app_context():
            jobs.ensure_schedule()
        if not self.threads:
            self.threads = [threading.Thread(target=self._lane, args=(n,), name=f"jobs-{n}", daemon=True) for n in self.bells]
            for t in self.threads:
                t.start()
            log.info("fon vazifalari: ishga tushdi")

    def run(self) -> None:
        """Tinglovchi. Ulanish nomi bo'yicha admin paneli bajaruvchi borligini biladi (jobs.worker_alive)."""
        import psycopg
        from sqlalchemy import make_url

        from .services import jobs
        url = make_url(self.app.config["SQLALCHEMY_DATABASE_URI"]).set(drivername="postgresql").render_as_string(hide_password=False)
        while not self.stop.is_set():
            try:
                with psycopg.connect(url, autocommit=True) as conn:
                    if not conn.execute("SELECT pg_try_advisory_lock(%s, %s)", LOCK).fetchone()[0]:
                        self.stop.wait(POLL)           # boshqa jarayon faol
                        continue
                    conn.execute(f"SET application_name = '{jobs.APP_NAME}'")
                    conn.execute(f"LISTEN {jobs.CHANNEL}")
                    self._start_lanes()
                    self.ring()                        # uzilib turganda kelganlari bo'lishi mumkin
                    while not self.stop.is_set():
                        for _n in conn.notifies(timeout=1, stop_after=1):
                            self.ring()
            except Exception as e:                     # noqa: BLE001 — baza uzildi yoki hali tayyor emas
                log.warning("fon vazifalari: baza bilan aloqa yo'q: %s", type(e).__name__)
                self.stop.wait(5)

    def close(self, seconds: float = 25) -> None:
        """To'xtatadi: boshlangan vazifa tugashi shuncha soniyagacha kutiladi."""
        self.stop.set()
        self.ring()
        for t in self.threads:
            t.join(seconds)


def embed(app) -> None:
    """RM_WORKER=1 bo'lsa, birinchi so'rovda shu jarayon ichida ishga tushadi (gunicorn fork qilgandan keyin)."""
    if os.environ.get("RM_WORKER") != "1" or app.testing:
        return
    guard = threading.Lock()

    @app.before_request
    def start_worker():
        if "worker" in app.extensions:
            return
        with guard:
            if "worker" not in app.extensions:
                import atexit
                w = app.extensions["worker"] = Worker(app)
                threading.Thread(target=w.run, name="jobs-listen", daemon=True).start()
                atexit.register(w.close, 5)
