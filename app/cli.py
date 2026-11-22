"""Buyruqlar: `flask namuna-foydalanuvchilar` — ishlab chiqish uchun uchta namunaviy akkaunt.

| Rol       | Login                        | Parol     | Maxfiy so'z |
|-----------|------------------------------|-----------|-------------|
| o'qituvchi| +998901234567                | parol1234 | informatika |
| ekspert   | ekspert@raqamlimuallim.uz    | parol1234 | informatika |
| admin     | admin@raqamlimuallim.uz      | parol1234 | informatika |
"""
import click

DEMO_PASSWORD = "parol1234"
DEMO_SECRET = "informatika"

DEMO_USERS = [
    {"role": "user", "phone": "+998901234567", "email": "dilnoza.k@maktab.uz",
     "first_name": "Dilnoza", "last_name": "Karimova", "region": "Toshkent shahri"},
    {"role": "expert", "phone": "+998931234545", "email": "ekspert@raqamlimuallim.uz",
     "first_name": "Zuhra", "last_name": "Qodirova"},
    {"role": "admin", "phone": "+998971234510", "email": "admin@raqamlimuallim.uz",
     "first_name": "Aziz", "last_name": "Rahimov"},
]


def demo_user(role: str):
    """Shu roldagi namunaviy foydalanuvchi (bo'lmasa yaratiladi)."""
    from datetime import datetime, timezone

    from .extensions import db
    from .models.users import User

    data = next(d for d in DEMO_USERS if d["role"] == role)
    user = db.session.scalar(db.select(User).where(User.phone == data["phone"]))
    if user is None:
        user = User(**data, consent_at=datetime.now(timezone.utc))
        user.set_password(DEMO_PASSWORD)
        user.set_secret(DEMO_SECRET)
        db.session.add(user)
        db.session.commit()
    return user


def init_app(app):
    @app.cli.command("namuna-foydalanuvchilar")
    def seed_demo_users():
        """O'qituvchi, ekspert va admin namunaviy akkauntlarini yaratadi (bor bo'lsa tegmaydi)."""
        for d in DEMO_USERS:
            u = demo_user(d["role"])
            click.echo(f"{u.role:7} {u.email or u.phone}  (parol: {DEMO_PASSWORD})")
