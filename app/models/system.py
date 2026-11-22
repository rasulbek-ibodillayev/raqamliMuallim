"""Sozlamalar (barcha chegaralar) va admin harakatlari jurnali."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._base import JSONB, PK, created_at, pk


class Setting(db.Model):
    """Kalit → JSON qiymat: test chegaralari (90/80/70), savollar soni, vaqt, AI limitlari va h.k."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)    # masalan: test.thresholds
    value: Mapped[dict | list | int | float | str | bool] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(String(300))
    updated_by: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity", "entity_id"),)

    id: Mapped[int] = pk()
    actor_id: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(40))                   # create, update, delete, approve, ...
    entity: Mapped[str] = mapped_column(String(40))                   # question, user, setting, ...
    entity_id: Mapped[str | None] = mapped_column(String(80))
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")   # {"before": ..., "after": ...}
    ip: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
