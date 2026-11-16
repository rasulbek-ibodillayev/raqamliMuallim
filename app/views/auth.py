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


# --- Sertifikatni tekshirish (ommaviy, QR-koddan) ---
# Namunada: INF-2026-000123 — haqiqiy, INF-2026-000099 — bekor qilingan, qolgani — topilmadi
_CERT_STATES = {"INF-2026-000123": "valid", "INF-2026-000099": "revoked"}


@bp.get("/s/<cert_no>")
def verify_certificate(cert_no):
    cert_no = cert_no.upper()
    state = _CERT_STATES.get(cert_no, "missing")
    return render_template("auth/verify_certificate.html", cert_no=cert_no, state=state), 200 if state != "missing" else 404


@bp.get("/s")
def verify_certificate_lookup():
    from flask import redirect, url_for
    return redirect(url_for("auth.verify_certificate", cert_no=request.args.get("raqam", "").strip() or "-"))
