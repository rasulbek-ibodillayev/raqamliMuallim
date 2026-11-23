"""Test pleyer uchun API: javoblar test_attempts / attempt_items jadvallariga yoziladi (services/attempts.py).

  POST /api/urinish/<uuid>/javoblar   {"kind": "exam", "answers": [{"pos": 0, "v": 1, "t": 4200, "at": 1763300000000}]}
       → 200 {"ok": true, "saved": [0]}       409 — urinish yakunlangan      400/422 — noto'g'ri so'rov
       403 — urinish boshqa foydalanuvchiniki  404 — bunday urinish yo'q
  POST /api/urinish/<uuid>/yakunlash  {"kind": "exam", "stage": 1}
       → 200 {"ok": true, "result_url": "..."}  (takroriy chaqiruv ham 200 — idempotent)

Urinishni server yaratadi (views/test.py), uuid — test_attempts.client_uuid.
Bir xil (uuid, pos) qayta kelsa, `at` vaqti kattarog'i qoladi: oflayn navbat qayta yuborilganda eski javob yangisini bosmaydi.
Bosqichli testda `stage` — yakunlanayotgan bosqich: oflayn navbat uni ikki marta yuborsa ham bosqich bir marta o'tadi.
"""
import uuid as uuidlib

from flask import Blueprint, jsonify, request
from flask_babel import gettext as _
from flask_login import current_user

from ..models.testing import ATTEMPT_KINDS
from ..services import attempts as at

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_POS = 200
MAX_ITEMS = 200


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


def _int(v, low, high) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and low <= v < high


def _attempt(attempt_uuid, kind):
    """Qulflangan urinish yoki xato javobi: (urinish, None) | (None, javob)."""
    a = at.get(uuidlib.UUID(attempt_uuid), lock=True)
    if a is None:
        return None, _err(404, _("Urinish topilmadi"))
    if a.user_id != current_user.id:
        return None, _err(403, _("Bu urinish boshqa foydalanuvchiga tegishli"))
    if a.kind != kind:
        return None, _err(422, _("Urinish turi mos kelmaydi"))
    return a, None


@bp.post("/urinish/<attempt_uuid>/javoblar")
def save_answers(attempt_uuid):
    if not _valid_uuid(attempt_uuid):
        return _err(400, _("Urinish identifikatori noto‘g‘ri"))
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
        return _err(400, _("JSON kutilgan: {kind, answers: [...]}"))
    kind, items = data.get("kind"), data["answers"]
    if kind not in ATTEMPT_KINDS:
        return _err(422, _("Test turi noto‘g‘ri"))
    if not 1 <= len(items) <= MAX_ITEMS:
        return _err(422, _("Javoblar soni noto‘g‘ri"))

    bad = [i for i, a in enumerate(items)
           if not (isinstance(a, dict) and _int(a.get("pos"), 0, MAX_POS) and _valid_value(a.get("v"))
                   and _int(a.get("t", 0), 0, 86_400_000) and _int(a.get("at", 0), 0, 1 << 53))]
    if bad:
        return _err(422, _("Ba’zi javoblar noto‘g‘ri formatda"), invalid=bad)

    a, err = _attempt(attempt_uuid, kind)
    if err:
        return err
    try:
        return jsonify(ok=True, saved=at.save_answers(a, items))
    except at.Closed:
        return _err(409, _("Urinish yakunlangan, javoblarni o‘zgartirib bo‘lmaydi"))


@bp.post("/urinish/<attempt_uuid>/yakunlash")
def finish(attempt_uuid):
    if not _valid_uuid(attempt_uuid):
        return _err(400, _("Urinish identifikatori noto‘g‘ri"))
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    kind, stage = data.get("kind"), data.get("stage")
    if kind not in ATTEMPT_KINDS or not (stage is None or _int(stage, 1, 4)):
        return _err(422, _("Test turi noto‘g‘ri"))
    a, err = _attempt(attempt_uuid, kind)
    if err:
        return err
    if a.status == "abandoned":
        return _err(409, _("Test bekor qilingan"))
    if at.is_staged(a) and stage is None and a.status == "in_progress":
        return _err(422, _("Bosqich ko‘rsatilmagan"))
    a = at.finish(a, stage)
    from .test import attempt_url
    answered = sum(1 for i in a.items if (i.answer or {}).get("v") not in (None, "", []))
    return jsonify(ok=True, answered=answered, result_url=attempt_url(a))
