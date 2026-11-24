"""Urinish: savollarni tanlash, boshlash, javoblarni saqlash, baholash (scoring) va tahlil.
Qaysi testga nechta savol tushishi — test_builder.py; natijaning progressga ta'siri — progress.py.

Qoidalar:
- Savol bazada bir joyda (questions) turadi; urinish faqat (question_id, version) ga havola qiladi.
- Bitta foydalanuvchiga bitta savol ikki marta berilmaydi (seen.py). Yangi savol yetmasa — shablon generator (generator.py),
  u ham yetmasa test qisqaroq bo'ladi.
- Faqat tasdiqlangan (approved) savollar olinadi.
- Test (bosqich) tugagach javobdan faqat qiymati qoladi; 12 oydan eski urinish siqiladi (archive.py), shuning uchun
  yakunlangan urinish qatorlari archive.rows(a) orqali o'qiladi.

Bankdagi savollar bitta SQL so'rov bilan tanlanadi: har bir kichik mavzudan rejadagi sonicha, tasodifiy tartibda.
"""
import random
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from flask_babel import lazy_gettext as _l
from sqlalchemy import func, select, tuple_

from ..extensions import db
from ..models import AttemptItem, Question, QuestionVersion, Subtopic, TestAttempt, Topic
from . import generator, progress, scoring, seen
from .archive import rows as rows_of

PARTIAL_TYPES = ("multiple", "matching")      # qisman ball beriladigan turlar
DEFAULT_SECONDS = 60                          # savolda time_limit_s bo'lmasa
TYPE_TO_KIND = {"single": "yopiq", "multiple": "kop", "matching": "moslash", "open": "ochiq"}


@dataclass(frozen=True)
class Picked:
    question_id: int
    version: int
    subtopic_id: int
    type: str = "single"
    seconds: int = DEFAULT_SECONDS


def plan_for_topic(topic_id: int) -> dict[int, int]:
    """Mavzu testi rejasi: {kichik mavzu id: savollar soni (Subtopic.weight)}."""
    rows = db.session.execute(select(Subtopic.id, Subtopic.weight).where(Subtopic.topic_id == topic_id)
                              .order_by(Subtopic.position)).all()
    return {sid: w for sid, w in rows if w > 0}


def pick_questions(user_id: int, plan: dict[int, int], difficulty: str | None = None,
                   types: tuple[str, ...] | None = None) -> list[Picked]:
    """Reja bo'yicha savollar, kichik mavzular tartibida: avval bankdagi yangi savollar, yetmaganiga shablon generator.

    Generator tuzgan savollar sessiyaga qo'shiladi (commit urinish bilan birga)."""
    picked = pick_from_bank(user_id, plan, difficulty, types)
    have = Counter(p.subtopic_id for p in picked)
    out = []
    for sid, n in plan.items():
        out += [p for p in picked if p.subtopic_id == sid]
        out += make_new(sid, n - have[sid], difficulty, types)
    return out


def make_new(subtopic_id: int, n: int, difficulty=None, types=None) -> list[Picked]:
    return [Picked(q.id, q.version, q.subtopic_id, q.type, q.time_limit_s or DEFAULT_SECONDS)
            for q in generator.make(subtopic_id, n, difficulty, types)]


def pick_from_bank(user_id: int, plan: dict[int, int], difficulty: str | None = None,
                   types: tuple[str, ...] | None = None) -> list[Picked]:
    """Bankdagi foydalanuvchiga berilmagan savollar (bazaga hech narsa yozmaydi)."""
    plan = {sid: n for sid, n in plan.items() if n > 0}
    if not plan:
        return []
    rank = func.row_number().over(partition_by=Question.subtopic_id, order_by=func.random()).label("rn")
    q = (select(Question.id, Question.version, Question.subtopic_id, Question.type, Question.time_limit_s, rank)
         .where(Question.subtopic_id.in_(plan), Question.status == "approved", seen.is_new(user_id)))
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    if types:
        q = q.where(Question.type.in_(types))
    ranked = q.subquery()
    # Har bir kichik mavzu uchun o'z limiti: (subtopic_id, n) jadvali bilan solishtiriladi
    limits = select(func.unnest(list(plan.keys())).label("sid"),
                    func.unnest(list(plan.values())).label("n")).subquery()
    rows = db.session.execute(
        select(ranked.c.id, ranked.c.version, ranked.c.subtopic_id, ranked.c.type, ranked.c.time_limit_s)
        .join(limits, limits.c.sid == ranked.c.subtopic_id)
        .where(ranked.c.rn <= limits.c.n)
        .order_by(ranked.c.subtopic_id, ranked.c.rn)
    ).all()
    order = {sid: i for i, sid in enumerate(plan)}
    picked = [Picked(r.id, r.version, r.subtopic_id, r.type, r.time_limit_s or DEFAULT_SECONDS) for r in rows]
    return sorted(picked, key=lambda p: order[p.subtopic_id])   # sorted barqaror: kichik mavzu ichidagi tartib saqlanadi


def _insert(user_id: int, kind: str, parts: list[list[Picked]], *, levels=None, topic_id=None, subtopic_id=None,
            seconds=None, client_uuid=None, stage=None, settings=None) -> TestAttempt:
    """Urinish va savollarini yozadi. Bosqichli testda faqat birinchi bosqich savollari «berilgan» deb belgilanadi:
    keyingilari test yakunlanmaguncha band turadi (seen.is_new), bosqichga yetib borilmasa — bankka qaytadi."""
    now = datetime.now(timezone.utc)
    flat = [p for part in parts for p in part]
    snap = dict(settings or {})
    if levels and levels != [None]:
        stages, start = [], 0
        for level, part in zip(levels, parts):
            stages.append({"level": level, "from": start, "to": start + len(part), "seconds": _seconds(part)})
            start += len(part)
        snap.update(stages=stages, skipped=[], failed_topics=[], recommended={})
        stage, seconds = 1, stages[0]["seconds"]
    if seconds:
        snap["seconds"] = seconds
    attempt = TestAttempt(
        user_id=user_id, kind=kind, topic_id=topic_id, subtopic_id=subtopic_id, stage=stage, total=len(flat),
        client_uuid=client_uuid or uuid.uuid4(), settings_snapshot=snap,
        deadline_at=now + timedelta(seconds=seconds) if seconds else None)
    attempt.items = [AttemptItem(position=i, question_id=p.question_id, question_version=p.version)
                     for i, p in enumerate(flat)]
    db.session.add(attempt)
    seen.mark(user_id, [p.question_id for p in (parts[0] if "stages" in snap else flat)])
    db.session.commit()
    return attempt


def _seconds(part: list[Picked]) -> int:
    return sum(p.seconds for p in part)


def create(user_id: int, spec) -> TestAttempt:
    """test_builder.Spec bo'yicha urinish."""
    return _insert(user_id, spec.kind, spec.parts, levels=spec.levels, topic_id=spec.topic_id,
                   subtopic_id=spec.subtopic_id, settings=spec.settings,
                   seconds=spec.seconds or sum(_seconds(p) for p in spec.parts))


def start_attempt(user_id: int, kind: str, plan: dict[int, int], *, difficulty: str | None = None,
                  topic_id: int | None = None, stage: int | None = None, time_limit_s: int | None = None,
                  client_uuid: uuid.UUID | None = None, settings: dict | None = None) -> TestAttempt:
    """Urinishni reja ({kichik mavzu: son}) bo'yicha yaratadi. Hammasi bitta tranzaksiyada.

    client_uuid berilsa va shunday urinish bor bo'lsa — o'sha qaytariladi (oflayn qayta yuborish takror yaratmaydi).
    """
    if client_uuid is not None:
        existing = db.session.scalar(select(TestAttempt).where(TestAttempt.client_uuid == client_uuid))
        if existing is not None:
            if existing.user_id != user_id:
                raise PermissionError("Bu urinish boshqa foydalanuvchiga tegishli")
            return existing
    picked = pick_questions(user_id, plan, difficulty)
    return _insert(user_id, kind, [picked], topic_id=topic_id, stage=stage, client_uuid=client_uuid, seconds=time_limit_s,
                   settings={**(settings or {}), "plan": {str(k): v for k, v in plan.items()},
                             "difficulty": difficulty, "requested": sum(plan.values())})


# ---------------- Javoblar va yakunlash ----------------

class Closed(Exception):
    """Urinish yakunlangan yoki bekor qilingan."""


def get(client_uuid: uuid.UUID, *, lock: bool = False) -> TestAttempt | None:
    q = select(TestAttempt).where(TestAttempt.client_uuid == client_uuid)
    return db.session.scalar(q.with_for_update().execution_options(populate_existing=True) if lock else q)


def stages(a: TestAttempt) -> list[dict]:
    return a.settings_snapshot.get("stages", [])


def is_staged(a: TestAttempt) -> bool:
    return bool(stages(a))


def stage_range(a: TestAttempt, stage: int | None = None) -> tuple[int, int]:
    """Joriy (yoki berilgan) bosqich savollari: [boshi, oxiri)."""
    if not is_staged(a):
        return 0, a.total
    s = stages(a)[(stage or a.stage) - 1]
    return s["from"], s["to"]


def active_positions(a: TestAttempt) -> list[int]:
    start, end = stage_range(a)
    skipped = set(a.settings_snapshot.get("skipped", []))
    return [p for p in range(start, end) if p not in skipped]


def save_answers(a: TestAttempt, answers: list[dict]) -> list[int]:
    """Javoblarni yozadi (a — qulflangan qator). Bir savolga ikki marta kelsa, `at` kattarog'i qoladi.

    Faqat joriy bosqich savollari yoziladi: tugagan bosqich javobi keyin o'zgarmaydi."""
    if a.status != "in_progress":
        raise Closed
    items = {i.position: i for i in a.items}
    allowed = set(active_positions(a))
    saved = []
    for x in answers:
        saved.append(x["pos"])
        item = items.get(x["pos"])
        if item is None or x["pos"] not in allowed:
            continue
        prev = item.answer or {}
        if x.get("at", 0) >= prev.get("at", 0):
            item.answer = {"v": x.get("v"), "at": x.get("at", 0)}
            item.time_ms = x.get("t") or item.time_ms
    db.session.commit()
    return saved


def _snapshots(a: TestAttempt) -> dict[int, tuple[dict, int, int]]:
    """{tartib: (savol nusxasi, kichik mavzu, mavzu)} — urinishdagi aniq versiyalar."""
    items = rows_of(a)
    if not items:
        return {}
    rows = db.session.execute(
        select(QuestionVersion.question_id, QuestionVersion.version, QuestionVersion.snapshot, Subtopic.id, Subtopic.topic_id)
        .join(Question, Question.id == QuestionVersion.question_id).join(Subtopic, Subtopic.id == Question.subtopic_id)
        .where(tuple_(QuestionVersion.question_id, QuestionVersion.version)
               .in_([(i.question_id, i.question_version) for i in items]))).all()
    info = {(qid, ver): (snap, sid, tid) for qid, ver, snap, sid, tid in rows}
    return {i.position: info[i.question_id, i.question_version] for i in items if (i.question_id, i.question_version) in info}


def _stage_verdict(a: TestAttempt, snaps, positions) -> tuple[set[int], dict[str, int]]:
    """Bosqich natijasi: (o'tmagan mavzular, tavsiya etilgan darslar {kichik mavzu: foiz}).

    Mavzu bo'yicha: < 70 — keyingi bosqichga o'tmaydi; 70–89 — o'tadi, ≥ 90 ga yetmagan darslarini qayta o'zlashtirish
    tavsiya etiladi; ≥ 90 — tavsiyasiz o'tadi."""
    by_pos = {i.position: i for i in a.items}
    topics: dict[int, dict[int, list[int]]] = {}
    for p in positions:
        _snap, sid, tid = snaps[p]
        topics.setdefault(tid, {}).setdefault(sid, []).append(by_pos[p].score or 0)
    failed, advise = set(), {}
    for tid, lessons in topics.items():
        verdict = scoring.decision(scoring.percent([x for sc in lessons.values() for x in sc]))
        if verdict == "fail":
            failed.add(tid)
        elif verdict == "warn":
            advise |= {str(sid): pct for sid, sc in lessons.items() if (pct := scoring.percent(sc)) < scoring.SOLID_MIN}
    return failed, advise


def finish(a: TestAttempt, stage: int | None = None) -> TestAttempt:
    """Testni (yoki bosqichli testning joriy bosqichini) yakunlaydi: baholaydi, natija va progressni yozadi.

    a — qulflangan qator. Takroriy chaqiruv xavfsiz: yakunlangan test yoki o'tib bo'lingan bosqich (stage) qayta
    ishlanmaydi. Bosqich tugaganda savollari qolgan keyingi bosqich bo'lsa — unga o'tadi, aks holda test yakunlanadi.
    """
    if a.status != "in_progress":
        return a
    if is_staged(a) and stage is not None and stage != a.stage:
        return a
    snaps = _snapshots(a)
    by_pos = {i.position: i for i in a.items}
    now_positions = active_positions(a)
    for p in now_positions:
        snap, item = snaps[p][0], by_pos[p]
        v = (item.answer or {}).get("v")
        item.score = scoring.grade(snap["type"], snap["answer"], v)
        item.answer = None if v is None else {"v": v}          # `at` faqat sinxronlash paytida kerak edi

    if is_staged(a):
        _apply_verdict(a, snaps, now_positions)
    if is_staged(a) and _next_stage(a, snaps):
        db.session.commit()
        return a

    # So'ralmagan (yuqori bosqichdagi, mavzusi o'tmagan) savollar 0 ball: test to'liq rejaga nisbatan baholanadi
    scores = [i.score or 0 for i in a.items]
    a.score_pct = scoring.percent(scores)
    a.correct = sum(scores) / 100
    a.decision = scoring.decision(int(a.score_pct))
    a.status, a.finished_at = "submitted", datetime.now(timezone.utc)
    progress.record(a, snaps)
    db.session.commit()
    return a


def _apply_verdict(a: TestAttempt, snaps, positions) -> None:
    cfg = a.settings_snapshot
    failed, advise = _stage_verdict(a, snaps, positions)
    failed |= set(cfg["failed_topics"])
    advise = {**cfg["recommended"], **advise}
    # O'tmagan mavzuning darslari alohida tavsiya qilinmaydi: mavzu butunlay qayta o'zlashtiriladi
    topic_of = {str(sid): tid for _s, sid, tid in snaps.values()}
    advise = {sid: pct for sid, pct in advise.items() if topic_of[sid] not in failed}
    a.settings_snapshot = {**cfg, "failed_topics": sorted(failed), "recommended": advise}


def _next_stage(a: TestAttempt, snaps) -> bool:
    """Keyingi bosqichga o'tkazadi (o'tmagan mavzularsiz); savol qolmagan bo'lsa False."""
    cfg = a.settings_snapshot
    failed, skipped = set(cfg["failed_topics"]), set(cfg["skipped"])
    n = a.stage
    while n < len(cfg["stages"]):
        s = cfg["stages"][n]
        rng = range(s["from"], s["to"])
        skipped |= {p for p in rng if snaps[p][2] in failed}
        left = [p for p in rng if p not in skipped]
        n += 1
        if left:
            seconds = round(s["seconds"] * len(left) / len(rng))
            a.settings_snapshot = {**cfg, "skipped": sorted(skipped), "seconds": seconds}
            a.stage = n
            a.deadline_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            seen.mark(a.user_id, [i.question_id for i in a.items if i.position in left])
            return True
    a.settings_snapshot = {**cfg, "skipped": sorted(skipped)}
    return False


def advice(a: TestAttempt) -> dict:
    """Bosqichli test xulosasi: {"relearn": [mavzu nomi], "lessons": [{"name", "topic", "pct"}]}."""
    cfg = a.settings_snapshot
    failed, rec = cfg.get("failed_topics", []), cfg.get("recommended", {})
    relearn = list(db.session.scalars(select(Topic.title).where(Topic.id.in_(failed)).order_by(Topic.id))) if failed else []
    rows = db.session.execute(select(Subtopic.id, Subtopic.title, Topic.title).join(Topic, Topic.id == Subtopic.topic_id)
                              .where(Subtopic.id.in_([int(s) for s in rec]))
                              .order_by(Topic.id, Subtopic.position)).all() if rec else []
    return {"relearn": relearn, "lessons": [{"name": n, "topic": t, "pct": rec[str(i)]} for i, n, t in rows]}


def cancel(a: TestAttempt) -> None:
    """Bekor qilish (faqat ixtiyoriy testlar — ko'rinish tekshiradi): qatorlari o'chadi, natijaga kirmaydi.
    Ko'rsatilgan savollari «berilgan» bo'lib qoladi (bitmap)."""
    a.status, a.finished_at = "abandoned", datetime.now(timezone.utc)
    a.items.clear()
    db.session.commit()


# ---------------- Ko'rsatish ----------------

def play_view(a: TestAttempt) -> list[dict]:
    """Joriy bosqich savollari pleyer uchun. To'g'ri javob (answer, explanation) sahifaga chiqmaydi."""
    snaps, titles = _snapshots(a), _titles(a)
    out = []
    for p in active_positions(a):
        snap = snaps[p][0]
        data = snap.get("data") or {}
        q = {"pos": p, "kind": TYPE_TO_KIND[snap["type"]], "text": snap["text"], "topic": titles[p],
             "code": data.get("code"), "image": data.get("image"), "table": data.get("table")}
        if snap["type"] in ("single", "multiple"):
            q["options"] = data["options"]
        elif snap["type"] == "matching":
            q["pairs"] = data["left"]
            # O'ng ustun aralash tartibda (har urinishda bir xil); qiymat — asl indeks
            order = list(range(len(data["right"])))
            random.Random(f"{a.client_uuid}:{p}").shuffle(order)
            q["answers"] = [(i, data["right"][i]) for i in order]
        else:
            q["numeric"] = str(snap["answer"].get("value", "")).isdigit()      # raqamli klaviatura uchun
        out.append(q)
    return out


def saved_answers(a: TestAttempt) -> dict[int, dict]:
    active = set(active_positions(a))
    return {i.position: i.answer for i in a.items if i.answer and i.position in active}


def _titles(a: TestAttempt) -> dict[int, str]:
    items = rows_of(a)
    by_q = dict(db.session.execute(
        select(Question.id, Subtopic.title).join(Subtopic, Subtopic.id == Question.subtopic_id)
        .where(Question.id.in_([i.question_id for i in items]))).all())
    return {i.position: by_q[i.question_id] for i in items if i.question_id in by_q}


LEVELS = {"easy": _l("Oson"), "medium": _l("O‘rta"), "hard": _l("Qiyin")}


def review(a: TestAttempt) -> list[dict]:
    """Yakunlangan urinish tahlili (partials/answer_review.html). So'ralmagan savollar ko'rsatilmaydi."""
    snaps, titles = _snapshots(a), _titles(a)
    skipped = set(a.settings_snapshot.get("skipped", []))
    out = []
    for item in rows_of(a):
        if item.position in skipped or item.position not in snaps:
            continue
        snap = snaps[item.position][0]
        data, ans, v = snap.get("data") or {}, snap["answer"], (item.answer or {}).get("v")
        r = {"n": len(out) + 1, "pos": item.position, "kind": TYPE_TO_KIND[snap["type"]], "topic": titles[item.position],
             "level": LEVELS.get(snap["difficulty"]), "q": snap["text"], "code": data.get("code"),
             "table": data.get("table"), "image": data.get("image"), "score": item.score or 0,
             "answered": v not in (None, "", []), "why": snap.get("explanation"), "notes": ans.get("notes"),
             "computed": bool(data.get("code") or data.get("table")) or snap["type"] == "open"}
        if snap["type"] in ("single", "multiple"):
            r["options"], r["right"] = data["options"], ans["keys"]
            r["mine"] = v if isinstance(v, list) else ([] if v is None else [v])
        elif snap["type"] == "matching":
            mine = v if isinstance(v, list) else []
            mine = [m if isinstance(m, int) and 0 <= m < len(data["right"]) else None for m in mine]
            mine += [None] * (len(data["left"]) - len(mine))
            r["pairs"] = [{"left": left, "right": data["right"][ans["pairs"][k]], "ok": mine[k] == ans["pairs"][k],
                           "mine": data["right"][mine[k]] if mine[k] is not None else None}
                          for k, left in enumerate(data["left"])]
        else:
            r["mine_text"], r["right_text"] = v, ans["value"]
        out.append(r)
    return out


def by_subtopic(a: TestAttempt) -> list[tuple[str, int, str, int]]:
    """[(kichik mavzu, foiz, to'plangan ball, savollar soni)], eng pastidan."""
    titles, acc = _titles(a), {}
    for i in rows_of(a):
        acc.setdefault(titles.get(i.position, "—"), []).append(i.score or 0)
    rows = [(name, scoring.percent(s), f"{round(sum(s) / 100, 1):g}", len(s)) for name, s in acc.items()]
    return sorted(rows, key=lambda r: r[1])


def names(attempts: list[TestAttempt], type_names: dict) -> dict[int, str]:
    """{urinish id: nomi}: dars testi — kichik mavzu, mavzu testi — mavzu nomi, qolganlari — tur nomi."""
    subs = {a.subtopic_id for a in attempts if a.subtopic_id}
    tops = {a.topic_id for a in attempts if a.topic_id}
    sub = dict(db.session.execute(select(Subtopic.id, Subtopic.title).where(Subtopic.id.in_(subs))).all()) if subs else {}
    top = dict(db.session.execute(select(Topic.id, Topic.title).where(Topic.id.in_(tops))).all()) if tops else {}
    out = {}
    for a in attempts:
        base = str(type_names[a.kind])
        detail = sub.get(a.subtopic_id) if a.kind == "lesson" else (top.get(a.topic_id) if a.kind == "topic" else None)
        out[a.id] = f"{base}: {detail}" if detail else base
    return out


def finished(user_id: int, kind: str | None = None, limit: int | None = None) -> list[TestAttempt]:
    q = (select(TestAttempt).where(TestAttempt.user_id == user_id, TestAttempt.status == "submitted")
         .order_by(TestAttempt.finished_at.desc(), TestAttempt.id.desc()))
    return list(db.session.scalars((q.where(TestAttempt.kind == kind) if kind else q).limit(limit)))
