"""Legal and credits pages. These are templates written for the prototype: have them reviewed by a lawyer before
real patients use the service. The organisation name and contacts come from the admin's branding settings."""
from __future__ import annotations

LAST_UPDATED = "26 November 2026"


def _contact(org, phone, email):
    parts = [x for x in (phone, email) if x]
    return f"{org} ({', '.join(parts)})" if parts else f"{org} (contact the clinic that gave you access)"


def disclaimer(org):
    return f"""
### Medical disclaimer
{org} is a **screening and decision-support tool**, not a diagnosis and not a substitute for an eye doctor.

- Results show *possible signs* of keratitis, corneal ulcer patterns or trachoma, or that no signs were found. A
  result that says *REFER* means an eye specialist should examine the eye; it is never a diagnosis.
- "No signs of disease found" is shown only when a dedicated check is confident. It does not rule out disease:
  if you have pain, redness, blurred vision, discharge or light sensitivity, see an eye doctor.
- The AI assistant explains results and gives general eye-health information. It never prescribes medicines.
- **Emergencies:** sudden loss of vision, a chemical splash or an eye injury need a hospital now. Call **108** or **112**.
- This software is a research prototype. It has not been clinically validated or registered as a medical device
  with CDSCO, and it must not be used as the sole basis for clinical decisions.
"""


def terms(org, phone, email):
    return f"""
### Terms of use
*Last updated {LAST_UPDATED}.*

1. **Service.** {org} lets clinics screen photos of the front of the eye and lets patients follow their results,
   book visits and receive reminders.
2. **Who may use it.** Clinic staff use accounts issued by their administrator. Patients may create an account
   for themselves, or for a child or dependant with their consent.
3. **Your responsibilities.** Keep your password private, upload only photos you are entitled to share, and do not
   try to access other people's records.
4. **Clinical responsibility.** Treatment decisions are made by qualified clinicians. Screening results and the AI
   assistant are aids, not medical advice (see the medical disclaimer).
5. **Availability.** The service is provided as is. Planned maintenance or network problems can interrupt it.
6. **Changes.** These terms may change; the date above shows the latest version.
7. **Contact.** {_contact(org, phone, email)}.
"""


def privacy(org, phone, email):
    return f"""
### Privacy notice
*Last updated {LAST_UPDATED}. Written with India's Digital Personal Data Protection Act, 2023 in mind.*

**Data fiduciary:** {_contact(org, phone, email)}.

**What we collect**
- Account details: name, age, sex, phone (optional), username, preferred language.
- Health data: eye photos, screening results, doctor recommendations, symptom diary, vision tests, eye-drop
  schedules and doses, appointments and reminders.
- Usage records: sign-ins and important actions (audit log), kept for security.

**Why:** to screen eye photos, let clinicians review them, refer you to a suitable hospital, and remind you about
visits and drops. We do not sell your data or use it for advertising.

**Where it goes**
- Your records stay on the clinic's server and are visible to you and the clinic's doctors and administrators.
- If *natural cloud voice* is switched on, the text being read aloud is sent to Microsoft's speech service.
- If the online AI assistant is enabled, your question and the case summary are sent to Anthropic's Claude API.
- Voice input uses your browser's speech service.

**Consent:** you gave consent when you created your account; the date is recorded. You may withdraw it at any time
by deleting your account.

**Your rights:** you can **download all your data** and **delete your account and data** from *My profile*. To
correct your data or raise a grievance, contact the clinic above.

**Retention:** records are kept while your account is active and for as long as the clinic must keep medical
records by law; deleted accounts are erased with their photos.

**Security:** passwords are stored as salted PBKDF2 hashes; accounts lock after repeated wrong passwords;
sessions end after inactivity; access is logged.
"""


CREDITS = """
### Data and model credits
The screening models were trained on these public datasets. CC BY 4.0 requires credit to the authors:

| Dataset | Source | Licence |
|---|---|---|
| Infectious keratitis (slit-lamp, 4 classes) | Figshare, DOI 10.6084/m9.figshare.28578860.v1 | CC BY 4.0 |
| SUSTech-SYSU corneal ulcer | Figshare, DOI 10.6084/m9.figshare.c.4526675; Scientific Data, DOI 10.1038/s41597-020-0360-7 | CC0 |
| Trachoma (everted eyelid, TF / TI) | Figshare, DOI 10.6084/m9.figshare.7551053.v1 | GPL-3.0 (as listed; confirm before commercial use) |
| Eye disease classification (incl. 649 normal eyes) | Mendeley Data, DOI 10.17632/n9zp473wfw.2 | CC BY 4.0 |
| Nuclear cataract (slit-lamp) | Mendeley Data, DOI 10.17632/6wv33nbcvv.2 | CC BY 4.0 |
| Slit-lamp cataract (temporal series) | PLOS ONE supplement, DOI 10.1371/journal.pone.0201142.s001 | CC BY 4.0 |

**Software:** Streamlit, PyTorch, torchvision, timm (EfficientNet-B0, ImageNet weights), scikit-learn, OpenCV,
Plotly, ReportLab, edge-tts, Meta NLLB-200 (translations), Anthropic Claude API (optional assistant), Leaflet /
OpenStreetMap map tiles via Plotly. Each is used under its own open-source licence.

**Team:** Syed Mohammed Yaseen, Mohammed Ayaan, Arfath Khan.
"""
