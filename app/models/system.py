"""Sozlamalar (barcha chegaralar) va admin harakatlari jurnali."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._base import JSONB, PK, created_at, pk


class Setting(db.Model):
    """Kalit → JSON qiymat. Faqat standartdan farqli sozlamalar (services/settings.py)."""
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


class DailyStat(db.Model):
    """Kuniga bitta qator: nechta o'qituvchi kirgani va qurilma turi (kim ekani yozilmaydi)."""
    __tablename__ = "daily_stats"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    active: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    phone: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tablet: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pwa: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ExpertInvite(db.Model):
    """Ekspert taklifnomasi. Token saqlanmaydi — imzodan hosil bo'ladi (app/invites.py). Bitta manzilga bitta taklif."""
    __tablename__ = "expert_invites"

    id: Mapped[int] = pk()
    created_by: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nonce: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    name: Mapped[str] = mapped_column(String(160))
    contact: Mapped[str] = mapped_column(String(254), unique=True)
    perms: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    areas: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")      # sections.id; bo'sh — hammasi
