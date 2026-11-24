"""O'qituvchining e'tirozlari: savolning aniq versiyasi va urinishga bog'lanadi (objections jadvali).

Savol havolasi (formadagi `question`) — "<urinish uuid>:<tartib>": foydalanuvchi faqat o'ziga berilgan savolga
e'tiroz bildira oladi. Bitta urinishdagi bitta savolga bitta e'tiroz. Ko'rib chiqilmagani tahrirlanadi va o'chiriladi.
"""
import uuid as uuidlib

from flask_babel import gettext as _
from sqlalchemy import func, select

from ..extensions import db
from ..models import Objection, Question, QuestionVersion, TestAttempt
from . import attempts as at
from .archive import rows as rows_of
from .timefmt import when


class ObjectionError(ValueError):
    pass


def ref(a: TestAttempt, pos: int) -> str:
    return f"{a.client_uuid}:{pos}"


def _parse(user_id: int, value: str):
    head, _sep, tail = (value or "").rpartition(":")
    try:
        a = at.get(uuidlib.UUID(head))
        pos = int(tail)
    except ValueError:
        a = None
    if a is None or a.user_id != user_id:
        return None, None
    return a, next((i for i in rows_of(a) if i.position == pos), None)


def create(user_id: int, question_ref: str, reason: str, note: str, urgent: bool) -> Objection:
    a, item = _parse(user_id, question_ref)
    if item is None:
        raise ObjectionError(_("Savol topilmadi"))
    if item.position in sent_positions(a):
        raise ObjectionError(_("Bu savolga e’tiroz allaqachon yuborilgan"))
    o = Objection(user_id=user_id, question_id=item.question_id, question_version=item.question_version,
                  attempt_id=a.id, reason=reason, text=note, urgent=urgent)
    db.session.add(o)
    db.session.commit()
    return o


def sent_positions(a: TestAttempt) -> set[int]:
    """Shu urinishda e'tiroz yuborilgan savollar tartibi."""
    qids = set(db.session.scalars(select(Objection.question_id).where(Objection.attempt_id == a.id)))
    return {i.position for i in rows_of(a) if i.question_id in qids} if qids else set()


def mine(user_id: int) -> list[dict]:
    rows = db.session.execute(
        select(Objection, func.coalesce(QuestionVersion.snapshot["text"].as_string(), Question.text))
        .join(Question, Question.id == Objection.question_id)
        .outerjoin(QuestionVersion, (QuestionVersion.question_id == Objection.question_id)
                   & (QuestionVersion.version == Objection.question_version))
        .where(Objection.user_id == user_id).order_by(Objection.created_at.desc(), Objection.id.desc())).all()
    out = []
    for o, text in rows:
        recalc = None
        if o.score_before is not None and o.score_after is not None:
            recalc = (f"{round(o.score_before)}%", f"{round(o.score_after)}%")
        out.append({"id": o.id, "when": when(o.created_at), "q": text or "", "state": o.status, "reason": o.reason,
                    "note": o.text, "verdict": o.verdict, "recalc": recalc})
    return out


def own(user_id: int, oid: int) -> Objection | None:
    o = db.session.get(Objection, oid)
    return o if o is not None and o.user_id == user_id else None
