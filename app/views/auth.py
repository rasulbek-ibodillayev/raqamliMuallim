from flask import Blueprint, render_template, request

bp = Blueprint("auth", __name__)


@bp.get("/")
def guest():
    return render_template("auth/guest.html")


@bp.get("/kirish")
def login():
    return render_template("auth/login.html", error=request.args.get("xato"))


@bp.get("/royxat")
def register():
    return render_template("auth/register.html", step=1)


@bp.get("/royxat/telegram")
def verify_telegram():
    return render_template("auth/verify_telegram.html", step=2)


@bp.get("/royxat/email")
def verify_email():
    return render_template("auth/verify_email.html", step=2)


@bp.get("/royxat/malumotlar")
def details():
    return render_template("auth/details.html", step=3)


@bp.get("/maxfiylik")
def privacy():
    return render_template("auth/privacy.html")


@bp.get("/parol-tiklash")
def reset():
    return render_template("auth/reset.html")
