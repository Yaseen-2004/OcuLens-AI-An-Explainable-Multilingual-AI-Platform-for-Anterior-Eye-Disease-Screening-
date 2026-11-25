"""SQLite storage for the OcuLens-AI portal: users, patients, screening cases, recommendations."""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "oculens.db"
STORAGE = ROOT / "storage"
STORAGE.mkdir(exist_ok=True)


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def hash_pw(pw: str) -> str:
    return hashlib.sha256(("oculens$" + pw).encode()).hexdigest()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def init_db():
    c = _conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            name TEXT, role TEXT DEFAULT 'doctor', created_at TEXT);
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mrn TEXT, name TEXT NOT NULL, age INTEGER, sex TEXT, notes TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER, task TEXT, image_path TEXT,
            top_label TEXT, top_prob REAL, pred_set TEXT, referred INTEGER,
            quality_ok INTEGER, status TEXT DEFAULT 'pending',
            created_by TEXT, created_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id));
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, doctor TEXT, diagnosis TEXT, recommendation TEXT, created_at TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id));
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER, hospital TEXT, doctor TEXT, requested_by TEXT, status TEXT DEFAULT 'requested', created_at TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id));
        """
    )
    # migration: add mutual-information column if an older DB predates it
    cols = [r[1] for r in c.execute("PRAGMA table_info(cases)").fetchall()]
    if "mi" not in cols:
        c.execute("ALTER TABLE cases ADD COLUMN mi REAL DEFAULT 0")
    # migration: which eye the image shows ("R", "L" or "" when not recorded)
    if "eye" not in cols:
        c.execute("ALTER TABLE cases ADD COLUMN eye TEXT DEFAULT ''")
    # patient accounts (25 Nov): a login linked to a patient record, a symptom diary and reminders
    ucols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    for col, typ in (("patient_id", "INTEGER"), ("phone", "TEXT DEFAULT ''"), ("lang", "TEXT DEFAULT 'en'"),
                     ("home_area", "TEXT DEFAULT ''")):
        if col not in ucols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
    if "source" not in cols:
        c.execute("ALTER TABLE cases ADD COLUMN source TEXT DEFAULT 'clinic'")
    acols = [r[1] for r in c.execute("PRAGMA table_info(appointments)").fetchall()]
    for col, typ in (("patient_id", "INTEGER"), ("preferred_date", "TEXT DEFAULT ''"), ("note", "TEXT DEFAULT ''"),
                     ("slot", "TEXT DEFAULT ''"), ("visit_type", "TEXT DEFAULT 'In person'"),
                     ("needs", "TEXT DEFAULT ''")):
        if col not in acols:
            c.execute(f"ALTER TABLE appointments ADD COLUMN {col} {typ}")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, eye TEXT, pain INTEGER, redness INTEGER,
            itching INTEGER, watering INTEGER, blur INTEGER, light INTEGER, note TEXT, logged_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id));
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, title TEXT, due TEXT, kind TEXT,
            done INTEGER DEFAULT 0, created_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id));
        """
    )
    _ensure_feature_tables(c)
    # seed demo users once
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed = [
            ("admin", "admin123", "Administrator", "admin"),
            ("dr.yaseen", "doctor123", "Dr. Syed Mohammed Yaseen", "doctor"),
            ("dr.ayaan", "doctor123", "Dr. Mohammed Ayaan", "doctor"),
            ("dr.arfath", "doctor123", "Dr. Arfath Khan", "doctor"),
        ]
        for u, p, n, r in seed:
            c.execute("INSERT INTO users (username, password_hash, name, role, created_at) VALUES (?,?,?,?,?)",
                      (u, hash_pw(p), n, r, now()))
    c.commit()
    c.close()


# ---- auth
def check_login(username: str, password: str):
    c = _conn()
    row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    c.close()
    if row and row["password_hash"] == hash_pw(password):
        return dict(row)
    return None


def list_users():
    c = _conn(); rows = c.execute("SELECT id, username, name, role, created_at FROM users ORDER BY id").fetchall(); c.close()
    return [dict(r) for r in rows]


def add_user(username, password, name, role):
    c = _conn()
    try:
        c.execute("INSERT INTO users (username, password_hash, name, role, created_at) VALUES (?,?,?,?,?)",
                  (username, hash_pw(password), name, role, now()))
        c.commit(); return True
    except sqlite3.IntegrityError:
        return False
    finally:
        c.close()


# ---- patients
def add_patient(name, age, sex, mrn="", notes=""):
    c = _conn()
    cur = c.execute("INSERT INTO patients (mrn, name, age, sex, notes, created_at) VALUES (?,?,?,?,?,?)",
                    (mrn, name, age, sex, notes, now()))
    c.commit(); pid = cur.lastrowid; c.close(); return pid


def list_patients():
    c = _conn(); rows = c.execute("SELECT * FROM patients ORDER BY id DESC").fetchall(); c.close()
    return [dict(r) for r in rows]


def get_patient(pid):
    c = _conn(); row = c.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone(); c.close()
    return dict(row) if row else None


# ---- cases
def add_case(patient_id, task, image_path, top_label, top_prob, pred_set, referred, quality_ok, created_by, mi=0.0,
             eye="", source="clinic"):
    c = _conn()
    cur = c.execute(
        """INSERT INTO cases (patient_id, task, image_path, top_label, top_prob, pred_set, referred,
           quality_ok, mi, eye, status, created_by, created_at, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (patient_id, task, image_path, top_label, float(top_prob), pred_set, int(referred),
         int(quality_ok), float(mi), eye or "", "pending", created_by, now(), source))
    c.commit(); cid = cur.lastrowid; c.close(); return cid


def list_cases(status=None, task=None, referred=None):
    q = ("SELECT c.*, p.name AS patient_name FROM cases c LEFT JOIN patients p ON c.patient_id=p.id WHERE 1=1")
    args = []
    if status and status != "All":
        q += " AND c.status=?"; args.append(status)
    if task and task != "All":
        q += " AND c.task=?"; args.append(task)
    if referred is not None:
        q += " AND c.referred=?"; args.append(int(referred))
    q += " ORDER BY c.id DESC"
    c = _conn(); rows = c.execute(q, args).fetchall(); c.close()
    return [dict(r) for r in rows]


def get_case(cid):
    c = _conn()
    row = c.execute("SELECT c.*, p.name AS patient_name, p.age, p.sex FROM cases c LEFT JOIN patients p ON c.patient_id=p.id WHERE c.id=?", (cid,)).fetchone()
    c.close(); return dict(row) if row else None


def set_case_status(cid, status):
    c = _conn(); c.execute("UPDATE cases SET status=? WHERE id=?", (status, cid)); c.commit(); c.close()


def cases_for_patient(pid):
    c = _conn(); rows = c.execute("SELECT * FROM cases WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall(); c.close()
    return [dict(r) for r in rows]


# ---- recommendations
def add_recommendation(case_id, doctor, diagnosis, recommendation):
    c = _conn()
    c.execute("INSERT INTO recommendations (case_id, doctor, diagnosis, recommendation, created_at) VALUES (?,?,?,?,?)",
              (case_id, doctor, diagnosis, recommendation, now()))
    c.execute("UPDATE cases SET status='reviewed' WHERE id=?", (case_id,))
    c.commit(); c.close()


def recommendations_for(case_id):
    c = _conn(); rows = c.execute("SELECT * FROM recommendations WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]


def add_appointment(case_id, hospital, doctor, requested_by, patient_id=None, preferred_date="", note="", slot="",
                    visit_type="In person", needs=""):
    c = _conn()
    if patient_id is None and case_id:
        row = c.execute("SELECT patient_id FROM cases WHERE id=?", (case_id,)).fetchone()
        patient_id = row["patient_id"] if row else None
    if doctor and preferred_date and slot and slot in booked_slots(doctor, preferred_date):
        c.close()
        return False                       # that doctor's slot was just taken
    cur = c.execute("INSERT INTO appointments (case_id, hospital, doctor, requested_by, status, created_at, patient_id, "
                    "preferred_date, note, slot, visit_type, needs) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (case_id, hospital, doctor, requested_by, "requested", now(), patient_id, preferred_date, note, slot,
                     visit_type, needs))
    c.commit(); aid = cur.lastrowid; c.close()
    return aid


def get_appointment(aid):
    c = _conn(); row = c.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone(); c.close()
    return dict(row) if row else None


def reschedule_appointment(aid, date, slot):
    """Move a booking to a new date and time if that doctor is free then; it goes back to 'requested'."""
    a = get_appointment(aid)
    if not a or (a.get("doctor") and slot in booked_slots(a["doctor"], date)):
        return False
    c = _conn()
    c.execute("UPDATE appointments SET preferred_date=?, slot=?, status='requested' WHERE id=?", (str(date), slot, aid))
    c.commit(); c.close()
    return True


def booked_slots(doctor, date):
    """Time slots already taken with this doctor on this date (declined bookings free the slot)."""
    c = _conn()
    rows = c.execute("SELECT slot FROM appointments WHERE doctor=? AND preferred_date=? AND slot!='' "
                     "AND status NOT IN ('declined', 'cancelled')", (doctor, str(date))).fetchall()
    c.close(); return {r["slot"] for r in rows}


def set_appointment_status(aid, status):
    c = _conn(); c.execute("UPDATE appointments SET status=? WHERE id=?", (status, aid)); c.commit(); c.close()


def appointments_for(case_id):
    c = _conn(); rows = c.execute("SELECT * FROM appointments WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]


def all_appointments():
    c = _conn()
    rows = c.execute("SELECT a.*, p.name AS patient_name, c2.task AS task FROM appointments a "
                     "LEFT JOIN cases c2 ON a.case_id=c2.id "
                     "LEFT JOIN patients p ON p.id = COALESCE(a.patient_id, c2.patient_id) ORDER BY a.id DESC").fetchall()
    c.close(); return [dict(r) for r in rows]


def stats():
    c = _conn()
    s = {
        "patients": c.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "cases": c.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "referred": c.execute("SELECT COUNT(*) FROM cases WHERE referred=1").fetchone()[0],
        "pending": c.execute("SELECT COUNT(*) FROM cases WHERE status='pending'").fetchone()[0],
        "reviewed": c.execute("SELECT COUNT(*) FROM cases WHERE status='reviewed'").fetchone()[0],
        "self_checks": c.execute("SELECT COUNT(*) FROM cases WHERE source='self' AND status='pending'").fetchone()[0],
        "patient_accounts": c.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0],
    }
    by_task = c.execute("SELECT task, COUNT(*) n FROM cases GROUP BY task").fetchall()
    s["by_task"] = {r["task"]: r["n"] for r in by_task}
    c.close(); return s


# ---- patient accounts
def register_patient(username, password, name, age, sex, phone="", lang="en"):
    """Self sign-up: a patient record plus a login linked to it. Returns (user dict or None, message)."""
    username = (username or "").strip().lower()
    if len(username) < 3 or len(password or "") < 6:
        return None, "Choose a username of at least 3 letters and a password of at least 6 characters."
    c = _conn()
    try:
        if c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            return None, "That username is taken. Please choose another."
        cur = c.execute("INSERT INTO patients (mrn, name, age, sex, notes, created_at) VALUES (?,?,?,?,?,?)",
                        ("", name.strip(), int(age), sex, "self-registered", now()))
        pid = cur.lastrowid
        c.execute("INSERT INTO users (username, password_hash, name, role, created_at, patient_id, phone, lang) "
                  "VALUES (?,?,?,?,?,?,?,?)", (username, hash_pw(password), name.strip(), "patient", now(), pid,
                                               phone, lang))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row), "Account created."
    finally:
        c.close()


def create_patient_login(patient_id, username, password, lang="en"):
    """A doctor gives an existing patient record a portal login."""
    p = get_patient(patient_id)
    if not p:
        return False, "Patient not found."
    username = (username or "").strip().lower()
    if len(username) < 3 or len(password or "") < 6:
        return False, "Username needs 3+ letters and password 6+ characters."
    c = _conn()
    try:
        c.execute("INSERT INTO users (username, password_hash, name, role, created_at, patient_id, lang) "
                  "VALUES (?,?,?,?,?,?,?)", (username, hash_pw(password), p["name"], "patient", now(), patient_id, lang))
        c.commit()
        return True, f"Login created for {p['name']}."
    except sqlite3.IntegrityError:
        return False, "That username is taken."
    finally:
        c.close()


def login_for_patient(patient_id):
    c = _conn()
    row = c.execute("SELECT id, username, lang FROM users WHERE role='patient' AND patient_id=?", (patient_id,)).fetchone()
    c.close()
    return dict(row) if row else None


def get_user(uid):
    c = _conn(); row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); c.close()
    return dict(row) if row else None


def update_profile(uid, phone=None, lang=None, age=None, sex=None, home_area=None):
    c = _conn()
    u = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if u:
        if phone is not None:
            c.execute("UPDATE users SET phone=? WHERE id=?", (phone, uid))
        if lang is not None:
            c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
        if home_area is not None:
            c.execute("UPDATE users SET home_area=? WHERE id=?", (home_area, uid))
        if u["patient_id"] and (age is not None or sex is not None):
            if age is not None:
                c.execute("UPDATE patients SET age=? WHERE id=?", (int(age), u["patient_id"]))
            if sex is not None:
                c.execute("UPDATE patients SET sex=? WHERE id=?", (sex, u["patient_id"]))
    c.commit(); c.close()


def change_password(uid, old, new):
    c = _conn()
    try:
        u = c.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()
        if not u or u["password_hash"] != hash_pw(old):
            return False, "The current password is not correct."
        if len(new or "") < 6:
            return False, "The new password needs at least 6 characters."
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(new), uid)); c.commit()
        return True, "Password changed."
    finally:
        c.close()


def add_symptom(patient_id, eye, scores: dict, note=""):
    c = _conn()
    c.execute("INSERT INTO symptoms (patient_id, eye, pain, redness, itching, watering, blur, light, note, logged_at) "
              "VALUES (?,?,?,?,?,?,?,?,?,?)",
              (patient_id, eye, *[int(scores.get(k, 0)) for k in ("pain", "redness", "itching", "watering", "blur", "light")],
               note, now()))
    c.commit(); c.close()


def symptoms_for(patient_id):
    c = _conn(); rows = c.execute("SELECT * FROM symptoms WHERE patient_id=? ORDER BY id", (patient_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]


def add_reminder(patient_id, title, due, kind="custom"):
    c = _conn()
    c.execute("INSERT INTO reminders (patient_id, title, due, kind, done, created_at) VALUES (?,?,?,?,0,?)",
              (patient_id, title, due, kind, now()))
    c.commit(); c.close()


def reminders_for(patient_id, include_done=True):
    q = "SELECT * FROM reminders WHERE patient_id=?" + ("" if include_done else " AND done=0") + " ORDER BY done, due"
    c = _conn(); rows = c.execute(q, (patient_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]


def set_reminder_done(rid, done=True):
    c = _conn(); c.execute("UPDATE reminders SET done=? WHERE id=?", (int(done), rid)); c.commit(); c.close()


def delete_reminder(rid, patient_id):
    c = _conn(); c.execute("DELETE FROM reminders WHERE id=? AND patient_id=?", (rid, patient_id)); c.commit(); c.close()


def appointments_for_patient(patient_id):
    c = _conn()
    rows = c.execute("SELECT a.* FROM appointments a LEFT JOIN cases c2 ON a.case_id=c2.id "
                     "WHERE a.patient_id=? OR c2.patient_id=? ORDER BY a.id DESC", (patient_id, patient_id)).fetchall()
    c.close(); return [dict(r) for r in rows]


def recommendations_for_patient(patient_id):
    c = _conn()
    rows = c.execute("SELECT r.*, c2.task, c2.eye FROM recommendations r JOIN cases c2 ON r.case_id=c2.id "
                     "WHERE c2.patient_id=? ORDER BY r.id DESC", (patient_id,)).fetchall()
    c.close(); return [dict(r) for r in rows]


def seed_patient_demo():
    """Demo patient login for the fictional seeded patient Ravi Kumar (ravi / patient123)."""
    c = _conn()
    try:
        if c.execute("SELECT 1 FROM users WHERE username='ravi'").fetchone():
            return
        p = c.execute("SELECT id FROM patients WHERE name='Ravi Kumar' ORDER BY id LIMIT 1").fetchone()
        if not p:
            return
        c.execute("INSERT INTO users (username, password_hash, name, role, created_at, patient_id, phone, lang) "
                  "VALUES (?,?,?,?,?,?,?,?)", ("ravi", hash_pw("patient123"), "Ravi Kumar", "patient", now(), p["id"],
                                               "", "en"))
        c.commit()
    finally:
        c.close()


# ---- doctor availability (weekly sessions + leave days)
DEFAULT_SESSIONS = "09:30-12:30,14:00-17:00"


def _ensure_feature_tables(c):
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS doctor_schedule (
            doctor TEXT, weekday INTEGER, sessions TEXT, slot_min INTEGER DEFAULT 30,
            PRIMARY KEY (doctor, weekday));
        CREATE TABLE IF NOT EXISTS doctor_leave (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, day TEXT, reason TEXT);
        CREATE TABLE IF NOT EXISTS vision_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, eye TEXT, kind TEXT, logmar REAL,
            snellen TEXT, distance_m REAL, amsler TEXT, taken_at TEXT);
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, case_id INTEGER, name TEXT, eye TEXT,
            times TEXT, start_date TEXT, end_date TEXT, instructions TEXT, prescribed_by TEXT,
            active INTEGER DEFAULT 1, created_at TEXT);
        CREATE TABLE IF NOT EXISTS med_doses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, med_id INTEGER, day TEXT, time TEXT, taken_at TEXT,
            UNIQUE (med_id, day, time));
        CREATE TABLE IF NOT EXISTS referral_followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, outcome TEXT, note TEXT, by_user TEXT, at TEXT);
        """
    )


def _feature_conn():
    c = _conn()
    _ensure_feature_tables(c)
    return c


def get_schedule(doctor):
    """{weekday: (sessions, slot_min)}; doctors without a saved schedule work Mon-Sat, 09:30-12:30 and 14:00-17:00."""
    c = _feature_conn()
    rows = c.execute("SELECT * FROM doctor_schedule WHERE doctor=?", (doctor,)).fetchall()
    c.close()
    if not rows:
        return {d: (DEFAULT_SESSIONS if d < 6 else "", 30) for d in range(7)}
    sched = {d: ("", 30) for d in range(7)}
    for r in rows:
        sched[r["weekday"]] = (r["sessions"] or "", r["slot_min"] or 30)
    return sched


def save_schedule(doctor, sched: dict):
    for d, (sessions, _) in sched.items():
        for part in filter(None, (sessions or "").split(",")):
            a, b = part.strip().split("-")
            if not (len(a) == 5 and len(b) == 5 and a < b):
                raise ValueError(f"Bad session '{part}' (use HH:MM-HH:MM)")
    c = _feature_conn()
    c.execute("DELETE FROM doctor_schedule WHERE doctor=?", (doctor,))
    for d, (sessions, slot_min) in sched.items():
        c.execute("INSERT INTO doctor_schedule (doctor, weekday, sessions, slot_min) VALUES (?,?,?,?)",
                  (doctor, int(d), sessions.replace(" ", ""), int(slot_min)))
    c.commit(); c.close()


def add_leave(doctor, day, reason=""):
    c = _feature_conn()
    c.execute("INSERT INTO doctor_leave (doctor, day, reason) VALUES (?,?,?)", (doctor, str(day), reason))
    c.commit(); c.close()


def leave_for(doctor):
    c = _feature_conn()
    rows = c.execute("SELECT * FROM doctor_leave WHERE doctor=? ORDER BY day", (doctor,)).fetchall()
    c.close(); return [dict(r) for r in rows]


def delete_leave(lid):
    c = _feature_conn(); c.execute("DELETE FROM doctor_leave WHERE id=?", (lid,)); c.commit(); c.close()


def slots_for(doctor, day):
    """All bookable times for a doctor on a date (HH:MM), from the weekly schedule, minus leave days."""
    import datetime as _dt
    d = _dt.date.fromisoformat(str(day))
    if any(lv["day"] == d.isoformat() for lv in leave_for(doctor)):
        return []
    sessions, step = get_schedule(doctor)[d.weekday()]
    out = []
    for part in filter(None, (sessions or "").split(",")):
        a, b = part.split("-")
        t = _dt.datetime.combine(d, _dt.time.fromisoformat(a))
        end = _dt.datetime.combine(d, _dt.time.fromisoformat(b))
        while t + _dt.timedelta(minutes=step) <= end:
            out.append(t.strftime("%H:%M"))
            t += _dt.timedelta(minutes=step)
    return out


# ---- at-home vision tests
def add_vision_test(patient_id, eye, kind, logmar=None, snellen="", distance_m=None, amsler=""):
    c = _feature_conn()
    c.execute("INSERT INTO vision_tests (patient_id, eye, kind, logmar, snellen, distance_m, amsler, taken_at) "
              "VALUES (?,?,?,?,?,?,?,?)", (patient_id, eye, kind, logmar, snellen, distance_m, amsler, now()))
    c.commit(); c.close()


def vision_tests_for(patient_id):
    c = _feature_conn()
    rows = c.execute("SELECT * FROM vision_tests WHERE patient_id=? ORDER BY id", (patient_id,)).fetchall()
    c.close(); return [dict(r) for r in rows]


# ---- eye-drop schedule (entered by the doctor; the AI never suggests medicines)
def add_medication(patient_id, case_id, name, eye, times, start_date, end_date, instructions, prescribed_by):
    c = _feature_conn()
    cur = c.execute("INSERT INTO medications (patient_id, case_id, name, eye, times, start_date, end_date, instructions, "
                    "prescribed_by, active, created_at) VALUES (?,?,?,?,?,?,?,?,?,1,?)",
                    (patient_id, case_id, name.strip(), eye, ",".join(sorted(times)), str(start_date), str(end_date),
                     instructions, prescribed_by, now()))
    c.commit(); mid = cur.lastrowid; c.close(); return mid


def medications_for(patient_id, active_only=True):
    c = _feature_conn()
    q = "SELECT * FROM medications WHERE patient_id=?" + (" AND active=1" if active_only else "") + " ORDER BY id"
    rows = c.execute(q, (patient_id,)).fetchall(); c.close()
    return [dict(r) for r in rows]


def stop_medication(mid):
    c = _feature_conn(); c.execute("UPDATE medications SET active=0 WHERE id=?", (mid,)); c.commit(); c.close()


def set_dose(med_id, day, time, taken=True):
    c = _feature_conn()
    if taken:
        c.execute("INSERT OR IGNORE INTO med_doses (med_id, day, time, taken_at) VALUES (?,?,?,?)",
                  (med_id, str(day), time, now()))
    else:
        c.execute("DELETE FROM med_doses WHERE med_id=? AND day=? AND time=?", (med_id, str(day), time))
    c.commit(); c.close()


def doses_taken(med_id):
    c = _feature_conn()
    rows = c.execute("SELECT day, time FROM med_doses WHERE med_id=?", (med_id,)).fetchall(); c.close()
    return {(r["day"], r["time"]) for r in rows}


def adherence(med, upto=None):
    """(taken, due) doses from the start date up to now (or `upto`), for this medication."""
    import datetime as _dt
    nowdt = upto or _dt.datetime.now()
    start = _dt.date.fromisoformat(med["start_date"])
    end = min(_dt.date.fromisoformat(med["end_date"]), nowdt.date())
    taken = doses_taken(med["id"])
    due = got = 0
    d = start
    while d <= end:
        for t in filter(None, med["times"].split(",")):
            if _dt.datetime.combine(d, _dt.time.fromisoformat(t)) <= nowdt:
                due += 1
                got += (d.isoformat(), t) in taken
        d += _dt.timedelta(days=1)
    return got, due


# ---- referral loop: did the patient reach the specialist?
def add_followup(case_id, outcome, note, by_user):
    c = _feature_conn()
    c.execute("INSERT INTO referral_followups (case_id, outcome, note, by_user, at) VALUES (?,?,?,?,?)",
              (case_id, outcome, note, by_user, now()))
    c.commit(); c.close()


def referral_status():
    """One row per referred case: booking / visit state, days since referral and the latest follow-up."""
    import datetime as _dt
    c = _feature_conn()
    cases = c.execute("SELECT c.*, p.name AS patient_name FROM cases c LEFT JOIN patients p ON c.patient_id=p.id "
                      "WHERE c.referred=1 ORDER BY c.id DESC").fetchall()
    out = []
    for cs in cases:
        cs = dict(cs)
        appts = c.execute("SELECT status FROM appointments WHERE case_id=? OR (patient_id=? AND patient_id IS NOT NULL "
                          "AND created_at>=?)", (cs["id"], cs["patient_id"], cs["created_at"])).fetchall()
        sts = {a["status"] for a in appts}
        fu = c.execute("SELECT * FROM referral_followups WHERE case_id=? ORDER BY id DESC LIMIT 1", (cs["id"],)).fetchone()
        fu = dict(fu) if fu else None
        if (fu and fu["outcome"] == "Visited") or "completed" in sts:
            state = "Visited"
        elif fu and fu["outcome"] in ("Declined", "Not reachable", "Moved away"):
            state = fu["outcome"]
        elif sts & {"requested", "confirmed"}:
            state = "Booked"
        else:
            state = "Not booked"
        days = (_dt.datetime.now() - _dt.datetime.strptime(cs["created_at"], "%Y-%m-%d %H:%M")).days
        overdue = (state == "Not booked" and days >= 3) or (state == "Booked" and days >= 14)
        out.append({**cs, "state": state, "days": days, "overdue": overdue, "followup": fu})
    c.close()
    return out
