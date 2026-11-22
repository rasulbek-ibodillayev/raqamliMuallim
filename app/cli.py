"""Buyruqlar: `flask namuna-foydalanuvchilar` — ishlab chiqish uchun uchta namunaviy akkaunt.

| Rol       | Login                        | Parol     | Maxfiy so'z |
|-----------|------------------------------|-----------|-------------|
| o'qituvchi| +998901234567                | parol1234 | informatika |
| ekspert   | ekspert@raqamlimuallim.uz    | parol1234 | informatika |
| admin     | admin@raqamlimuallim.uz      | parol1234 | informatika |
"""
import json
from pathlib import Path

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


SEED_CONTENT = Path(__file__).parent / "seed" / "namuna_kontent.json"


def init_app(app):
    @app.cli.command("kontent-yuklash")
    @click.argument("fayl", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--holat", default=None, type=click.Choice(["draft", "review", "approved"]),
                  help="Yangi savollar holati. Standart: o'z faylingiz uchun review, namunaviy kontent uchun approved.")
    def load_content(fayl, holat):
        """JSON fayldan kurs, mavzular, dars bloklari va savollarni yuklaydi (fayl berilmasa — namunaviy kontent).

        Avval butun fayl tekshiriladi: xato bo'lsa hech narsa yozilmaydi. Qayta yuklash takrorlamaydi."""
        from .services.content_import import ContentError, load
        path = fayl or SEED_CONTENT
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))   # -sig: Windows muharrirlari qo'shadigan BOM
        except json.JSONDecodeError as e:
            raise click.ClickException(f"{path.name}: JSON xatosi, {e.lineno}-qator: {e.msg}")
        try:
            r = load(doc, status=holat or ("approved" if fayl is None else "review"))
        except ContentError as e:
            for err in e.errors[:50]:
                click.echo(f"  - {err}", err=True)
            raise click.ClickException(f"{path.name}: {len(e.errors)} ta xato, bazaga hech narsa yozilmadi")
        c = r.created
        click.echo(f"Yangi: {c['sections']} bo'lim, {c['topics']} mavzu, {c['subtopics']} kichik mavzu, "
                   f"{c['blocks']} blok, {c['questions']} savol. Avval bor bo'lgani uchun o'tkazilgan savollar: "
                   f"{r.skipped_questions}.")

    @app.cli.command("namuna-foydalanuvchilar")
    def seed_demo_users():
        """O'qituvchi, ekspert va admin namunaviy akkauntlarini yaratadi (bor bo'lsa tegmaydi)."""
        for d in DEMO_USERS:
            u = demo_user(d["role"])
            click.echo(f"{u.role:7} {u.email or u.phone}  (parol: {DEMO_PASSWORD})")
