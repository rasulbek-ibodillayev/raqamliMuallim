"""Test pleyer uchun API (hozircha xotirada saqlaydigan soxta versiya).

Shartnoma backendda ham shunday qoladi, faqat saqlash `test_attempts` / `attempt_items` jadvallariga o'tadi:

  POST /api/urinish/<uuid>/javoblar   {"kind": "exam", "answers": [{"pos": 0, "v": 1, "t": 4200, "at": 1763300000000}]}
       → 200 {"ok": true, "saved": [0]}       409 — urinish yakunlangan      400/422 — noto'g'ri so'rov
  POST /api/urinish/<uuid>/yakunlash  {"kind": "exam"}
       → 200 {"ok": true, "result_url": "..."}  (takroriy chaqiruv ham 200 — idempotent)

Bir xil (uuid, pos) qayta kelsa, `at` vaqti kattarog'i qoladi: oflayn navbat qayta yuborilganda eski javob yangisini bosmaydi.
"""
import threading
import uuid as uuidlib

from flask import Blueprint, jsonify, request, url_for
from flask_babel import gettext as _

bp = Blueprint("api", __name__, url_prefix="/api")

KINDS = {"diagnostic", "topic", "control", "final", "optional", "daily", "exam"}
MAX_POS = 200
MAX_ITEMS = 200

_lock = threading.Lock()
ATTEMPTS: dict[str, dict] = {}   # uuid → {"kind", "answers": {pos: {...}}, "finished": bool}


def _err(status, msg, **extra):
    return jsonify(ok=False, error=msg, **extra), status


def _valid_uuid(value: str) -> bool:
    try:
        return str(uuidlib.UUID(value)) == value.lower()
    except ValueError:
        return False


def _valid_value(v) -> bool:
    """Javob turlari: indeks (yopiq), indekslar ro'yxati (ko'p javobli / moslashtirish), matn (ochiq), null (bekor qilingan)."""
    if v is None:
        return True
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return 0 <= v < 26
    if isinstance(v, str):
        return len(v) <= 500
    if isinstance(v, list):
        return len(v) <= 26 and all(x is None or (isinstance(x, int) and not isinstance(x, bool) and 0 <= x < 26) for x in v)
    return False


@bp.post("/urinish/<attempt_uuid>/javoblar")
def save_answers(attempt_uuid):
    if not _valid_uuid(attempt_uuid):
        return _err(400, _("Urinish identifikatori noto‘g‘ri"))
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
        return _err(400, _("JSON kutilgan: {kind, answers: [...]}"))
    kind, items = data.get("kind"), data["answers"]
    if kind not in KINDS:
        return _err(422, _("Test turi noto‘g‘ri"))
    if not 1 <= len(items) <= MAX_ITEMS:
        return _err(422, _("Javoblar soni noto‘g‘ri"))

    bad = []
    for i, a in enumerate(items):
        ok = (isinstance(a, dict) and isinstance(a.get("pos"), int) and 0 <= a["pos"] < MAX_POS
              and _valid_value(a.get("v")) and isinstance(a.get("t", 0), int) and 0 <= a.get("t", 0) < 86_400_000
              and isinstance(a.get("at", 0), int))
        if not ok:
            bad.append(i)
    if bad:
        return _err(422, _("Ba’zi javoblar noto‘g‘ri formatda"), invalid=bad)

    with _lock:
        att = ATTEMPTS.setdefault(attempt_uuid, {"kind": kind, "answers": {}, "finished": False})
        if att["kind"] != kind:
            return _err(422, _("Urinish turi mos kelmaydi"))
        if att["finished"]:
            return _err(409, _("Urinish yakunlangan, javoblarni o‘zgartirib bo‘lmaydi"))
        saved = []
        for a in items:
            prev = att["answers"].get(a["pos"])
            if prev is None or a.get("at", 0) >= prev.get("at", 0):
                att["answers"][a["pos"]] = {"v": a.get("v"), "t": a.get("t", 0), "at": a.get("at", 0)}
            saved.append(a["pos"])
    return jsonify(ok=True, saved=saved)


@bp.post("/urinish/<attempt_uuid>/yakunlash")
def finish(attempt_uuid):
    if not _valid_uuid(attempt_uuid):
        return _err(400, _("Urinish identifikatori noto‘g‘ri"))
    data = request.get_json(silent=True) or {}
    kind = data.get("kind")
    if kind not in KINDS:
        return _err(422, _("Test turi noto‘g‘ri"))
    with _lock:
        att = ATTEMPTS.setdefault(attempt_uuid, {"kind": kind, "answers": {}, "finished": False})
        att["finished"] = True
        answered = sum(1 for a in att["answers"].values() if a["v"] is not None)
    return jsonify(ok=True, answered=answered,
                   result_url=url_for("test.exam_result") if kind == "exam" else url_for("test.result"))
