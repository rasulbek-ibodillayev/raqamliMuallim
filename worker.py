"""Fon vazifalari alohida jarayonda (odatda kerak emas: RM_WORKER=1 bilan veb-jarayon ichida ishlaydi — app/worker.py).

    python worker.py               doimiy ishlaydi (SECRET_KEY shart)
    python worker.py --dev         ishlab chiqishda (SECRET_KEY shart emas)
    python worker.py --bir-marta   vaqti kelgan vazifalarni bajarib, chiqadi
"""
import logging
import os
import signal
import sys

from app.envfile import load_env


def main(argv: list[str]) -> int:
    asked = {"-h", "--help"} & set(argv)
    if asked or set(argv) - {"--dev", "--bir-marta"}:
        print(__doc__)
        return 0 if asked else 2
    load_env()
    if "--dev" in argv:
        os.environ.setdefault("FLASK_DEBUG", "1")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from app import create_worker_app
    from app.services import jobs
    from app.worker import Worker
    app = create_worker_app()
    if "--bir-marta" in argv:
        with app.app_context():
            jobs.ensure_schedule()
            print(f"Bajarildi: {jobs.run_due()}")
        return 0
    w = Worker(app)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: w.stop.set())
    w.run()
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
