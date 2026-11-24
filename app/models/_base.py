"""Modellar uchun umumiy yordamchilar."""
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["JSONB", "PK", "QID", "Timestamps", "created_at", "one_of", "pk", "qid_pk"]


def pk() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(), primary_key=True)


PK = BigInteger  # tashqi kalitlar uchun ham shu tur

# Savollar 2 milliarddan oshmaydi: questions.id va unga havola qiluvchi ustunlar 4 baytli. Eng katta jadvallar
# (attempt_items, error_items) har qatorda 4 bayt tejaydi.
QID = Integer


def qid_pk() -> Mapped[int]:
    return mapped_column(Integer, Identity(), primary_key=True)


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now(), nullable=False)


def one_of(column: str, values, name: str | None = None) -> CheckConstraint:
    """`column IN (...)` cheklovi. Holat va tur maydonlari ENUM o'rniga shu bilan himoyalanadi."""
    vals = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({vals})", name=name or column)
