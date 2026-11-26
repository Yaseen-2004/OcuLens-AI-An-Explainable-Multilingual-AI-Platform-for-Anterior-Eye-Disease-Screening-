"""Deployment settings for the OcuLens portal.

Every value can be set without touching code, in this order of precedence:
1. an environment variable  OCULENS_<NAME>        (Docker, servers)
2. a Streamlit secret        <name> in .streamlit/secrets.toml or the Streamlit Cloud "Secrets" box
3. the default below
Branding (organisation name, support contacts) can also be changed by an admin in the portal; that value,
stored in the database, wins over 1-3.
"""
from __future__ import annotations

import os
from pathlib import Path

VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip() \
    if (Path(__file__).resolve().parents[1] / "VERSION").exists() else "1.0.0"

DEFAULTS = {
    "demo_mode": "1",                 # 1: seed demo doctors, patients and cases, and show the demo logins
    "admin_password": "",             # production (demo_mode 0): password of the first 'admin' account
    "org_name": "OcuLens-AI",
    "org_tagline": "Anterior-eye screening and referral",
    "support_phone": "",
    "support_email": "",
    "session_timeout_min": "30",      # sign out after this many idle minutes
    "max_login_attempts": "5",        # wrong passwords before the account is locked
    "lockout_min": "15",
    "data_dir": "",                   # where the database, photos and caches live (default: the portal folder)
}


def get(name: str, default: str | None = None) -> str:
    v = os.environ.get("OCULENS_" + name.upper())
    if v not in (None, ""):
        return v
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # noqa: BLE001  (no secrets file, or not running under Streamlit)
        pass
    return DEFAULTS.get(name, "") if default is None else default


def flag(name: str) -> bool:
    return str(get(name)).strip().lower() in ("1", "true", "yes", "on")


def number(name: str) -> int:
    try:
        return int(get(name))
    except ValueError:
        return int(DEFAULTS[name])


def data_dir() -> Path:
    d = get("data_dir")
    p = Path(d) if d else Path(__file__).resolve().parent
    p.mkdir(parents=True, exist_ok=True)
    return p
