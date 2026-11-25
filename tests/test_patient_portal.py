"""Patient accounts, diary, reminders and appointments (temporary database), voice segmentation and the patient
welcome. No network: speech synthesis itself is not called."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "portal"))
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    import db as _db
    monkeypatch.setattr(_db, "DB_PATH", tmp_path / "t.db")
    _db.init_db()
    return _db


def test_patient_signup_login_and_isolation(db):
    user, msg = db.register_patient("Meena", "secret1", "Meena R", 41, "F", "9000000000", "kn")
    assert user and user["role"] == "patient" and user["lang"] == "kn" and user["patient_id"]
    assert db.check_login("meena", "secret1")["patient_id"] == user["patient_id"]
    assert db.register_patient("meena", "secret1", "Other", 30, "F")[0] is None          # username taken
    assert db.register_patient("ab", "123", "Short", 30, "F")[0] is None                  # too short
    other = db.add_patient("Someone Else", 50, "M")
    db.add_case(other, "keratitis", "x.png", "FK", 0.6, "FK", 1, 1, "Dr. X")
    mine = db.add_case(user["patient_id"], "keratitis", "y.png", "BK", 0.7, "BK", 0, 1, "Meena R", source="self")
    assert [c["id"] for c in db.cases_for_patient(user["patient_id"])] == [mine]
    assert db.stats()["self_checks"] == 1


def test_doctor_creates_login_for_existing_patient(db):
    pid = db.add_patient("Ravi Kumar", 58, "M")
    ok, _ = db.create_patient_login(pid, "ravi2", "patient123", "hi")
    assert ok and db.login_for_patient(pid)["username"] == "ravi2"
    assert not db.create_patient_login(pid, "ravi2", "patient123")[0]                    # duplicate username


def test_diary_reminders_appointments_profile(db):
    user, _ = db.register_patient("asha", "secret1", "Asha", 30, "F")
    pid = user["patient_id"]
    db.add_symptom(pid, "Right eye", {"pain": 3, "redness": 5, "blur": 1}, "after work")
    db.add_symptom(pid, "Right eye", {"pain": 8, "redness": 6, "blur": 2})
    rows = db.symptoms_for(pid)
    assert [r["pain"] for r in rows] == [3, 8] and rows[0]["note"] == "after work"
    db.add_reminder(pid, "Follow-up visit", "2026-12-01")
    rid = db.reminders_for(pid)[0]["id"]
    db.set_reminder_done(rid)
    assert db.reminders_for(pid, include_done=False) == []
    db.add_appointment(None, "Narayana Nethralaya", "", "Asha", patient_id=pid, preferred_date="2026-12-02")
    assert db.appointments_for_patient(pid)[0]["preferred_date"] == "2026-12-02"
    db.update_profile(user["id"], phone="123", lang="ta", age=31)
    assert db.get_user(user["id"])["lang"] == "ta" and db.get_patient(pid)["age"] == 31
    assert not db.change_password(user["id"], "wrong", "newpass1")[0]
    assert db.change_password(user["id"], "secret1", "newpass1")[0] and db.check_login("asha", "newpass1")


def test_voice_segments_use_a_voice_per_script():
    import tts
    segs = tts._segments("ಇದು ಕಣ್ಣಿನ ತುರ್ತು. Please see a doctor. வணக்கம்.", "kn")
    assert [lg for lg, _ in segs] == ["kn", "en", "ta"]
    assert tts.VOICES["te"][1] == "te-IN-MohanNeural"
    assert tts.clean("- Dr. Rao **today**") == "Doctor Rao today"


def test_patient_welcome_mentions_their_status():
    from oculens.assistant.i18n import welcome_text
    u = {"name": "Ravi Kumar", "role": "patient"}
    txt = welcome_text(u, {"patient_status": "refer"}, "en")
    assert txt.split(", ")[1].startswith("Ravi.") and "eye specialist" in txt
    assert "ಸ್ವಾಗತ" in welcome_text(u, {"patient_status": "none"}, "kn")


def test_booking_a_recommended_doctor_blocks_double_booking(db):
    user, _ = db.register_patient("kiran", "secret1", "Kiran", 35, "M")
    pid = user["patient_id"]
    assert db.add_appointment(None, "Narayana Nethralaya", "Dr. A. Rao (sample)", "Kiran", patient_id=pid,
                              preferred_date="2026-12-03", slot="10:00")
    assert db.booked_slots("Dr. A. Rao (sample)", "2026-12-03") == {"10:00"}
    assert db.add_appointment(None, "Narayana Nethralaya", "Dr. A. Rao (sample)", "Someone", preferred_date="2026-12-03",
                              slot="10:00") is False
    aid = db.appointments_for_patient(pid)[0]["id"]
    db.set_appointment_status(aid, "declined")          # a declined booking frees the slot
    assert db.booked_slots("Dr. A. Rao (sample)", "2026-12-03") == set()
    assert db.all_appointments()[0]["patient_name"] == "Kiran"


def test_nearest_hospitals_are_sorted_by_distance_and_fit():
    import geo
    lat, lon = geo.AREAS["Whitefield"]
    near = geo.nearest(lat, lon)
    assert near[0]["hospital"] == "Sankara Eye Hospital"                   # Kundalahalli is next to Whitefield
    assert [h["km"] for h in near] == sorted(h["km"] for h in near)
    fit = geo.nearest(lat, lon, "ulcer_pattern", only_fit=True)
    assert all("ulcer_pattern" in h["fits"] for h in fit) and "Sankara Eye Hospital" not in [h["hospital"] for h in fit]
    jay = geo.nearest(*geo.AREAS["Jayanagar"])[0]
    assert jay["branch"] == "Jayanagar" and jay["km"] < 0.5 and jay["minutes"] == 5


def test_pincode_and_directions():
    import geo
    assert geo.area_of_pincode(" 560034 ") == "Koramangala" and geo.area_of_pincode("999999") is None
    assert abs(geo.haversine_km(12.9716, 77.5946, 13.0827, 80.2707) - 290) < 10          # Bengaluru -> Chennai
    url = geo.directions_url(geo.HOSPITALS[0], (12.9, 77.6))
    assert url.startswith("https://www.google.com/maps/dir/") and "origin=12.90000,77.60000" in url
    assert geo.nearest_area(*geo.AREAS["Hebbal"]) == "Hebbal"


def test_reschedule_visit_type_and_travel_modes(db):
    import geo
    user, _ = db.register_patient("leela", "secret1", "Leela", 45, "F")
    pid = user["patient_id"]
    aid = db.add_appointment(None, "Minto", "Dr. K. Prasad (sample)", "Leela", patient_id=pid, preferred_date="2026-12-04",
                             slot="09:30", visit_type="Video consultation", needs="Wheelchair access")
    a = db.get_appointment(aid)
    assert a["visit_type"] == "Video consultation" and a["needs"] == "Wheelchair access"
    db.add_appointment(None, "Minto", "Dr. K. Prasad (sample)", "Other", preferred_date="2026-12-05", slot="10:00")
    assert not db.reschedule_appointment(aid, "2026-12-05", "10:00")          # taken
    assert db.reschedule_appointment(aid, "2026-12-05", "11:00")
    assert db.booked_slots("Dr. K. Prasad (sample)", "2026-12-04") == set()   # old slot freed
    assert geo.travel_minutes(10, "Walking") > geo.travel_minutes(10, "Two-wheeler")
    low = geo.nearest(*geo.AREAS["Koramangala"], low_cost=True)
    assert {h["kind"] for h in low} <= {"Government", "Charitable"}
    assert "travelmode=transit" in geo.directions_url(geo.HOSPITALS[0], (12.9, 77.6), "Bus / metro")


def test_calendar_file_and_qr():
    import patient_portal as pp
    a = {"id": 7, "preferred_date": "2026-12-03", "slot": "09:30", "doctor": "Dr. A. Rao (sample)",
         "hospital": "Narayana Nethralaya · Rajajinagar", "visit_type": "In person"}
    ics = pp._ics(a, "Ravi")
    assert "DTSTART:20261203T040000Z" in ics and "TRIGGER:-PT2H" in ics and "OCL-00007" in ics   # 09:30 IST = 04:00 UTC
    assert len(pp._qr_b64("OCL-00007")) > 200 and pp._ampm("14:30") == "2:30 PM"


def test_doctor_calendar_slots_and_leave(db):
    doc = "Dr. Test (sample)"
    assert len(db.slots_for(doc, "2026-12-02")) == 12 and db.slots_for(doc, "2026-12-06") == []   # Wed / Sunday
    sched = {d: ("", 20) for d in range(7)}
    sched[2] = ("10:00-11:00", 20)
    db.save_schedule(doc, sched)
    assert db.slots_for(doc, "2026-12-02") == ["10:00", "10:20", "10:40"]
    assert db.slots_for(doc, "2026-12-01") == []                                                   # Tuesday off
    db.add_leave(doc, "2026-12-02", "conference")
    assert db.slots_for(doc, "2026-12-02") == []
    with pytest.raises(ValueError):
        db.save_schedule(doc, {0: ("11:00-10:00", 30)})


def test_eye_drop_adherence(db):
    import datetime as dt
    user, _ = db.register_patient("raju", "secret1", "Raju", 60, "M")
    mid = db.add_medication(user["patient_id"], None, "Drop A", "Right eye", ["08:00", "20:00"], "2026-12-01",
                            "2026-12-03", "", "Dr. X")
    med = db.medications_for(user["patient_id"])[0]
    db.set_dose(mid, "2026-12-01", "08:00")
    db.set_dose(mid, "2026-12-01", "08:00")                                  # ticking twice counts once
    assert db.adherence(med, upto=dt.datetime(2026, 12, 1, 21, 0)) == (1, 2)
    db.set_dose(mid, "2026-12-01", "20:00")
    assert db.adherence(med, upto=dt.datetime(2026, 12, 5, 9, 0)) == (2, 6)
    db.stop_medication(mid)
    assert db.medications_for(user["patient_id"]) == []


def test_referral_loop_states(db):
    user, _ = db.register_patient("sita", "secret1", "Sita", 50, "F")
    pid = user["patient_id"]
    cid = db.add_case(pid, "keratitis", "z.png", "FK", 0.4, "FK, BK", 1, 1, "Dr. X")
    st = {r["id"]: r for r in db.referral_status()}
    assert st[cid]["state"] == "Not booked" and not st[cid]["overdue"]          # referred today
    db.add_appointment(cid, "Minto", "Dr. K. Prasad (sample)", "Sita", preferred_date="2026-12-01", slot="09:30")
    assert {r["id"]: r for r in db.referral_status()}[cid]["state"] == "Booked"
    db.add_followup(cid, "Visited", "seen at Minto", "Dr. X")
    assert {r["id"]: r for r in db.referral_status()}[cid]["state"] == "Visited"


def test_vision_letter_size():
    import vision_test as vt
    assert abs(vt.letter_mm(0.0, 6) - 8.73) < 0.05            # a 6/6 letter at 6 m is 8.73 mm tall
    assert abs(vt.letter_mm(1.0, 2) / vt.letter_mm(0.0, 2) - 10) < 1e-9
    assert vt.snellen(0.3) == "6/12" and vt.snellen(None) == "worse than 6/60"
