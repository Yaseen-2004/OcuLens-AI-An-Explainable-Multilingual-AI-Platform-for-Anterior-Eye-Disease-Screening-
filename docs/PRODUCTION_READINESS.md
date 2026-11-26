# OcuLens-AI production readiness (v1.0.0)

What is in place in the software, and what a clinic or buyer still needs before OcuLens-AI is used with real
patients or sold. Last reviewed: 26 November 2026.

## Done in the software

| Area | In place |
|---|---|
| Accounts and access | Roles (admin, doctor, patient); patients see only their own records; admin user management with password reset |
| Passwords | Salted PBKDF2-SHA256 (260,000 rounds); old hashes upgraded automatically at sign-in; no password data kept in the session |
| Brute-force protection | Account locks after 5 wrong passwords for 15 minutes (configurable) |
| Sessions | Automatic sign-out after 30 idle minutes (configurable) |
| First admin | Production mode seeds one `admin` with a password from configuration, forced to change it at first sign-in; no demo accounts |
| Audit trail | Sign-ins, failed sign-ins, case views, screenings, recommendations, appointment changes, data exports, account deletions, settings changes, backups and errors, with an admin viewer and CSV export |
| Errors | Users see a reference number; full details go to a rotating server log (`<data dir>/logs/oculens.log`) |
| Privacy (DPDP Act 2023) | Consent recorded with a timestamp at sign-up; privacy notice and terms; patients can download all their data (JSON + photos) and delete their account and photos |
| Clinical safety in the product | Screening aid wording everywhere; uncertain results are referred, never called normal; "no signs of disease" only from a dedicated, strict check; red-flag symptoms trigger emergency advice; the assistant never names medicines |
| Configuration | Environment variables or Streamlit secrets; white-label organisation name and support contacts editable by the admin |
| Operations | System status page (models, data, voice service), one-click database backup, health-check endpoint, Docker image with a persistent data volume, automated tests on every push |
| Credits | Dataset licences and attributions shown in the app (CC BY 4.0 requires credit) |

## Still needed before real clinical use or sale

These cannot be solved in code; plan them with the client.

1. **Clinical validation.** A prospective, multi-site study on the intended patients and cameras, with ethics
   committee approval. Current results come from small, single-site public test sets (see README).
2. **Regulatory approval.** Screening software that influences referral is likely Software as a Medical Device
   under India's Medical Devices Rules, 2017: register with CDSCO in the appropriate risk class, with a quality
   management system (ISO 13485), risk management (ISO 14971) and software life-cycle records (IEC 62304).
3. **Data licences.** Five datasets are CC BY 4.0 or CC0 and allow commercial use with credit. The trachoma
   dataset is listed as GPL-3.0: get legal advice before selling the trachoma model, or retrain it on licensed data.
4. **Legal review.** The terms, privacy notice and disclaimer are templates; a lawyer should adapt them,
   including the grievance officer details the DPDP rules require.
5. **Hosting.** Streamlit Community Cloud is for demos only (public, data resets). For patients use the Docker
   image on a private server or cloud in India, behind HTTPS (needed for the camera and microphone), with
   encrypted disks, daily off-site backups of the data volume, and monitoring of the health-check endpoint.
6. **Database at scale.** SQLite (WAL mode) suits one clinic. For many clinics or concurrent users, move to
   PostgreSQL.
7. **Security review.** An independent penetration test and a vulnerability scan of the image before go-live.
   Consider two-factor sign-in for doctors and admins.
8. **Third-party services.** Natural voices use Microsoft's speech service through an unofficial client: switch to
   the official Azure Speech service (same voices) with a data-processing agreement. The optional online
   assistant needs an Anthropic agreement covering health data.
9. **Translations.** Hindi, Kannada, Tamil and Telugu texts are machine translations plus hand-written labels:
   have native speakers review them.
10. **Support.** Named support contacts, an incident process, and a version-update procedure for the clinic.
