# Changelog

## 1.0.0 (26 November 2026): first production-ready release

**Security and operations**
- Salted PBKDF2 password hashing with automatic upgrade of old hashes; account lockout after repeated wrong
  passwords; idle sign-out; forced password change for a temporary admin password.
- Production mode (`OCULENS_DEMO_MODE=0`): no demo accounts or demo data; the first admin comes from configuration.
- Audit log with admin viewer and CSV export; rotating server log; friendly error pages with a reference number.
- Admin "System & branding" page: health checks, white-label organisation name and contacts, database backup.
- Settings from environment variables or Streamlit secrets; configurable data folder.
- Docker image (CPU-only PyTorch, non-root user, health check, persistent `/data` volume) and docker-compose file.
- Automated tests on GitHub for every push.

**Privacy**
- Consent recorded at sign-up; privacy notice, terms of use, medical disclaimer, and data and software credits.
- Patients can download all their data and delete their account and photos.

**Screening**
- Normal-eye check: "No signs of disease found" only when a strict healthy-vs-diseased check is confident
  (test: 89.9% of healthy eyes and 0.24% of diseased eyes called normal).

## 0.9 (November 2026): capstone prototype
Screening models, explainability, doctor and patient portals, multilingual voice assistant, nearby-hospital
booking, doctor calendars, eye-drop schedules, vision test, referral follow-up.
