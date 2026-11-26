"""Fon vazifalari navbati (services/jobs.py)."""
from datetime import datetime

from sqlalchemy import DateTime, Index, SmallInteger, String, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._base import JSONB, pk


class Job(db.Model):
    """Navbat va jadval bitta joyda. Bajarilgan bir martalik vazifa qatori o'chadi, jadvaldagisi keyingi vaqtiga suriladi.

    run_at: qachon bajariladi; bajarilayotganda — ijara muddati (worker qulasa, shu vaqtda qaytadan olinadi);
    NULL — urinishlar tugagan, admin qarori kutiladi. data'da shaxsiy ma'lumot emas, id saqlanadi.
    """
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_due", "run_at", postgresql_where=sql_text("run_at IS NOT NULL")),
        Index("uq_jobs_key", "key", unique=True, postgresql_where=sql_text("key IS NOT NULL")),
    )

    id: Mapped[int] = pk()
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))      # jadvaldagi vazifa: oxirgi muvaffaqiyat
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    kind: Mapped[str] = mapped_column(String(24))
    key: Mapped[str | None] = mapped_column(String(80))                            # takrorlanmasin; "cron:…" — jadvaldagi
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    result: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    error: Mapped[str | None] = mapped_column(String(200))
