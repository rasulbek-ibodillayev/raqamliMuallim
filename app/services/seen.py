"""Foydalanuvchiga berilgan savollar bitmapi (user_seen): bir savol bir foydalanuvchiga ikki marta berilmaydi."""
from sqlalchemy import case, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.types import LargeBinary

from ..extensions import db
from ..models import AttemptItem, Question, TestAttempt, UserSeen


def mark(user_id: int, question_ids: list[int]) -> None:
    """Savollarni «berilgan» deb belgilaydi. Commit qilmaydi; qator tranzaksiya oxirigacha qulflanadi."""
    if not question_ids:
        return
    db.session.execute(insert(UserSeen).values(user_id=user_id, bits=b"").on_conflict_do_nothing())
    mine = UserSeen.user_id == user_id
    buf = bytearray(db.session.scalar(select(UserSeen.bits).where(mine).with_for_update()))
    buf.extend(bytes(max(0, max(question_ids) // 8 + 1 - len(buf))))
    for q in question_ids:
        buf[q >> 3] |= 1 << (q & 7)              # PostgreSQL get_bit bilan bir xil tartib
    db.session.execute(update(UserSeen).where(mine).values(bits=bytes(buf)).execution_options(synchronize_session=False))


def is_new(user_id: int):
    """SQL sharti: Question foydalanuvchiga berilmagan va yakunlanmagan testida (keyingi bosqichda) turmagan."""
    # || '' — bitmap bir marta ochiladi: aks holda katta bitmap har savolda qaytadan ochilardi (TOAST)
    bits = (select(UserSeen.bits.op("||", return_type=LargeBinary())(literal(b"", LargeBinary)))
            .where(UserSeen.user_id == user_id).scalar_subquery())
    # CASE: bitmap oxiridan keyingi (yangi) savollar uchun get_bit chaqirilmaydi; bitmap yo'q bo'lsa ham ELSE
    unseen = case((Question.id < func.length(bits) * 8, func.get_bit(bits, Question.id) == 0), else_=True)
    reserved = (select(AttemptItem.question_id).join(TestAttempt, TestAttempt.id == AttemptItem.attempt_id)
                .where(TestAttempt.user_id == user_id, TestAttempt.status.in_(("in_progress", "offline"))))
    return unseen & Question.id.not_in(reserved)


def given_to(question_id: int):
    """Savol berilgan foydalanuvchilar (SELECT). attempt_items'da question_id indeksi yo'q — qidiruv shu bilan torayadi."""
    return select(UserSeen.user_id).where(
        case((func.length(UserSeen.bits) * 8 > question_id, func.get_bit(UserSeen.bits, question_id) == 1), else_=False))


def ever_given(question_id: int) -> bool:
    """Savol birorta foydalanuvchiga berilganmi (arxivlangan urinishlar ham hisobga olinadi)."""
    item = select(AttemptItem.attempt_id).where(AttemptItem.question_id == question_id).limit(1)
    return (db.session.scalar(item) is not None
            or db.session.scalar(given_to(question_id).limit(1)) is not None)
