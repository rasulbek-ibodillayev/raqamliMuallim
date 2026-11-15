from flask import Blueprint, render_template, request

from .. import mock as m

bp = Blueprint("user", __name__, url_prefix="/app")


@bp.get("/")
def home():
    new_user = bool(request.args.get("yangi"))
    done_steps = int(request.args.get("qadam", 0))  # namunada: nechta qadam bajarilgan
    return render_template("user/home.html", sections=m.SECTIONS, r=m.READINESS, rstate=m.READINESS_STATE,
                           today=m.TODAY, onboarding=m.ONBOARDING, new_user=new_user, done_steps=done_steps)


@bp.get("/diagnostika")
def diagnostic():
    return render_template("user/diagnostic.html")


@bp.get("/bilim")
def knowledge():
    return render_template("user/knowledge.html", sections=m.SECTIONS, dist=m.DISTRIBUTION,
                           status=m.STATUS, view=request.args.get("view", "royxat"))


@bp.get("/bilim/<int:topic_id>")
def topic(topic_id):
    return render_template("user/topic.html", t=m.TOPIC, status=m.STATUS)


@bp.get("/reja")
def plan():
    return render_template("user/plan.html", plan=m.PLAN)


@bp.get("/dars")
def lesson():
    return render_template("user/lesson.html", retry=request.args.get("holat") == "qayta",
                           audio=bool(request.args.get("audio")))


@bp.get("/tutor")
def tutor():
    return render_template("user/tutor.html")


@bp.get("/testlarim")
def tests():
    return render_template("user/tests.html")


@bp.get("/nazorat")
def control():
    return render_template("user/control.html")


@bp.get("/ixtiyoriy-test")
def optional():
    return render_template("user/optional.html", topics=m.OPTIONAL_TOPICS, status=m.STATUS)


@bp.get("/natijalar")
def results():
    empty = bool(request.args.get("bosh"))
    return render_template("user/results.html", results=[] if empty else m.RESULTS,
                           decision=m.DECISION, trend=m.TREND)


@bp.get("/xatolar")
def errors():
    return render_template("user/errors.html", weak=m.ERRORS_WEAK, items=m.ERRORS_LIST)


@bp.get("/konspekt")
def notes():
    seed = [{"id": i + 1, "topic": t, "title": "", "text": text, "code": src or "", "when": when}
            for i, (t, text, src, when) in enumerate(m.NOTES)]
    topics = list(dict.fromkeys([n["topic"] for n in seed] +
                                [t["name"] for s in m.SECTIONS for t in s["topics"]]))
    return render_template("user/notes.html", notes=seed, topics=topics)


@bp.get("/muhokamalar")
def discussions():
    return render_template("user/discussions.html", items=m.DISCUSSIONS)


@bp.get("/muhokama")
def discussion():
    return render_template("user/discussion.html", msgs=m.DISCUSSION)


@bp.get("/etirozlarim")
def objections():
    return render_template("user/objections.html", items=m.OBJECTIONS, state=m.OBJ_STATE)


@bp.get("/sertifikatlar")
def certificates():
    return render_template("user/certificates.html", topics=m.CERT_TOPICS)


@bp.get("/sertifikat/INF-2026-000123")
def certificate_print():
    return render_template("user/certificate_print.html", topics=m.CERT_TOPICS)


@bp.get("/profil")
def profile():
    return render_template("user/profile.html")


@bp.get("/yana")
def more():
    return render_template("user/more.html")


@bp.get("/oflayn")
def offline():
    return render_template("user/offline.html")
