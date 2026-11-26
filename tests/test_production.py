"""Production features: password hashing and upgrade, lockout, audit log, settings, patient data rights, backup."""
import json
import sqlite3
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "portal"))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    import db as _db
    monkeypatch.setattr(_db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(_db, "STORAGE", tmp_path / "storage")
    (tmp_path / "storage").mkdir()
    monkeypatch.setenv("OCULENS_DEMO_MODE", "1")
    _db.init_db()
    return _db


def test_passwords_are_salted_pbkdf2_and_legacy_hashes_upgrade(db):
    h1, h2 = db.hash_pw("secret12"), db.hash_pw("secret12")
    assert h1.startswith("pbkdf2_sha256$") and h1 != h2                     # salted
    assert db.verify_pw("secret12", h1) and not db.verify_pw("wrong", h1)
    c = sqlite3.connect(db.DB_PATH)
    c.execute("UPDATE users SET password_hash=? WHERE username='dr.yaseen'", (db._legacy_hash("doctor123"),))
    c.commit()
    user, msg = db.login("dr.yaseen", "doctor123")
    assert msg == "ok" and "password_hash" not in user                    # no secret in the session
    stored = c.execute("SELECT password_hash FROM users WHERE username='dr.yaseen'").fetchone()[0]
    assert stored.startswith("pbkdf2_sha256$")                            # upgraded on login


def test_account_locks_after_repeated_wrong_passwords(db, monkeypatch):
    monkeypatch.setenv("OCULENS_MAX_LOGIN_ATTEMPTS", "3")
    for _ in range(2):
        assert db.login("dr.ayaan", "nope")[1] == "Invalid username or password."
    assert "locked" in db.login("dr.ayaan", "nope")[1]
    user, msg = db.login("dr.ayaan", "doctor123")                          # right password, but locked
    assert user is None and "locked" in msg


def test_production_mode_seeds_one_admin_who_must_change_password(tmp_path, monkeypatch):
    import db as _db
    monkeypatch.setattr(_db, "DB_PATH", tmp_path / "p.db")
    monkeypatch.setenv("OCULENS_DEMO_MODE", "0")
    monkeypatch.setenv("OCULENS_ADMIN_PASSWORD", "Str0ng-admin-pass")
    _db.init_db()
    assert [u["username"] for u in _db.list_users()] == ["admin"]
    user, _ = _db.login("admin", "Str0ng-admin-pass")
    assert user["must_change_password"] == 1
    assert _db.change_password(user["id"], "Str0ng-admin-pass", "another-pass-1")[0]
    assert _db.get_user(user["id"])["must_change_password"] == 0
    _db.seed_patient_demo()
    assert _db.check_login("ravi", "patient123") is None                   # no demo patient in production


def test_audit_log_and_settings(db, monkeypatch):
    db.audit({"username": "dr.yaseen", "role": "doctor"}, "case_viewed", "case 5")
    rows = db.audit_rows(10, "case_viewed")
    assert rows[0]["username"] == "dr.yaseen" and rows[0]["target"] == "case 5"
    monkeypatch.setenv("OCULENS_ORG_NAME", "Env Clinic")
    assert db.setting("org_name") == "Env Clinic"
    db.set_setting("org_name", "Admin Clinic")                            # the admin's branding wins
    assert db.setting("org_name") == "Admin Clinic"


def test_patient_can_export_and_erase_their_data(db):
    user, _ = db.register_patient("meera", "secret12", "Meera", 40, "F")
    pid = user["patient_id"]
    assert user["consent_at"]                                             # consent time recorded
    (db.STORAGE / "m1.png").write_bytes(b"\x89PNG fake")
    cid = db.add_case(pid, "keratitis", "m1.png", "FK", 0.6, "FK", 1, 1, "Meera", source="self")
    db.add_symptom(pid, "Right eye", {"pain": 2})
    z = zipfile.ZipFile(BytesIO(db.export_patient_zip(pid)))
    data = json.loads(z.read("my_oculens_data.json"))
    assert data["cases"][0]["id"] == cid and data["symptom_diary"] and "photos/case_%d.png" % cid in z.namelist()
    assert all("password_hash" not in a for a in data["account"])
    assert db.delete_patient(pid) == 1 and not (db.STORAGE / "m1.png").exists()
    assert db.check_login("meera", "secret12") is None and db.cases_for_patient(pid) == []


def test_backup_is_a_valid_database(db, tmp_path):
    out = tmp_path / "b.db"
    out.write_bytes(db.backup_bytes())
    assert sqlite3.connect(out).execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 1
