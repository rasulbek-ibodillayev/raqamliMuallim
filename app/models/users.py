"""Foydalanuvchilar."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, text, true
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ._base import JSONB, PK, Timestamps, one_of, pk

ROLES = ("user", "expert", "admin")


def _hash(value: str) -> str:
    """Werkzeug xeshi (standart: scrypt). Testlarda PASSWORD_HASH_METHOD bilan tezroq usul beriladi."""
    from flask import current_app
    method = current_app.config.get("PASSWORD_HASH_METHOD", "scrypt")
    return generate_password_hash(value, method=method)


class User(Timestamps, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        one_of("role", ROLES),
        Index("uq_users_google_sub", "google_sub", unique=True, postgresql_where=text("google_sub IS NOT NULL")),
        # Kamida bitta kirish usuli bo'lishi shart
        CheckConstraint("phone IS NOT NULL OR email IS NOT NULL OR telegram_id IS NOT NULL", name="has_login"),
    )

    id: Mapped[int] = pk()
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)          # +998901234567
    email: Mapped[str | None] = mapped_column(String(254), unique=True)         # kichik harflarda saqlanadi
    password_hash: Mapped[str | None] = mapped_column(String(255))             # Telegram yoki Google orqali kirganda bo'sh
    secret_hash: Mapped[str | None] = mapped_column(String(255))               # maxfiy so'z (parolni tiklash uchun)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    google_sub: Mapped[str | None] = mapped_column(String(64))                 # Google akkaunti id'si (email o'zgarsa ham shu)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(10), default="user", server_default="user")
    region: Mapped[str | None] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(80))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # maxfiylik siyosatiga rozilik
    exam_date: Mapped[date | None] = mapped_column(Date)                          # attestatsiya sanasi (admin kiritadi)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notif_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # bildirishnomalar shu vaqtgacha o'qilgan

    # Flask-Login: sessiyada id saqlanadi; is_active=False bo'lsa kira olmaydi
    def get_id(self) -> str:
        return str(self.id)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def set_password(self, pw: str) -> None:
        self.password_hash = _hash(pw)

    def check_password(self, pw: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, pw)

    def set_secret(self, secret: str) -> None:
        """Maxfiy so'z normallashtirilgan holda (forms.norm_secret) xeshlanadi."""
        from ..forms import norm_secret
        self.secret_hash = _hash(norm_secret(secret))

    def check_secret(self, secret: str) -> bool:
        from ..forms import norm_secret
        return bool(self.secret_hash) and check_password_hash(self.secret_hash, norm_secret(secret))

    @classmethod
    def by_login(cls, login: str) -> "User | None":
        """Telefon (+998...) yoki email bo'yicha topadi."""
        from ..forms import norm_phone
        v = (login or "").strip()
        if not v:
            return None
        q = cls.email == v.lower() if "@" in v else cls.phone == norm_phone(v)
        return db.session.scalar(db.select(cls).where(q))

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User {self.id} {self.role}>"


class ExpertProfile(db.Model):
    """Ekspert huquqlari. Qator yo'q — hamma huquq; areas bo'sh — hamma mavzu (services/experts.py)."""
    __tablename__ = "expert_profiles"

    user_id: Mapped[int] = mapped_column(PK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    perms: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    areas: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")      # sections.id
