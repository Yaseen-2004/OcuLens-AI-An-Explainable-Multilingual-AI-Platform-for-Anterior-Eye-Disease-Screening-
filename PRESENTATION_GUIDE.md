# OcuLens-AI — Presentation guide (for the team)

**Team:** Syed Mohammed Yaseen · Mohammed Ayaan · Arfath Khan
**Deck:** `Downloads/OcuLens-AI_Capstone_Presentation.pptx` (14 slides)
**Report:** `D:\Capston_Project\OcuLens-AI_Step_Log_and_Pre-Implementation_Guide.pdf` (52 pages)
**Live portal:** double-click `D:\Capston_Project\run_portal.bat` → browser opens.

Target: a confident 10–12 minute talk + live demo + Q&A. One-line framing to repeat:
**"A complete, working, evaluated research prototype for anterior-eye disease screening — with honest uncertainty and explanations checked against anatomy."**

---

## The 30-second pitch (memorise this)
Eye specialists are scarce, especially rural; many anterior-eye diseases (corneal infection, ulcers, trachoma) are
treatable if caught early. OcuLens-AI screens a single clinic/slit-lamp photo and does three things most tools don't:
it says **where** it's looking (cornea), **how sure** it is (calibrated confidence + a referral gate), and **what next**
(triage + follow-up). It's built, trained, evaluated, and runs live in a portal.

---

## Slide-by-slide talking points

1. **Title** — Names, project title, one sentence: "anatomy-aware, explainable anterior-eye screening."
2. **Agenda** — 10 seconds, just signpost.
3. **Introduction** — The problem: specialist shortage, late diagnosis, avoidable blindness. Screening at the point of care helps.
4. **Main idea** — The three pillars: localisation, honest uncertainty with referral, explanations verified against anatomy. "This is our novelty."
5. **Proposed plan** — The research pipeline (data → quality → segment → classify → uncertainty → explain → triage → follow-up).
6. **Datasets** — 6 public datasets, 7,419 images, **split by patient** (no leakage), all hashes verified. Say "test set is real images only."
7. **Methodologies** — Name the techniques (EfficientNet, U-Net, conformal prediction, Grad-CAM++, diffusion/CycleGAN, ensemble). Don't over-explain each.
8. **System architecture** — Three layers: training → inference service → clinic backend with the doctor-in-the-loop feedback that becomes new training data.
9. **Dataset gallery** — Quick visual; "these are the real image types we work with."
10. **Triage & safety** — Guardrails: the assistant only repeats verified findings; uncertain cases are referred, never guessed.
11. **What we delivered** — The money slide. "Complete prototype + evaluation, 48 tests, 11 models trained 50 epochs, a live portal." The chart shows the research pipeline is built end-to-end; clinical steps are deliberately future work.
12. **Evaluation** — Walk the table: trachoma strong (0.81), ulcer ~0.63–0.68 (anatomy helps), keratitis hard. Then: "conformal coverage near the 0.95 target, keratitis well-calibrated, and the referral curve is our safety argument."
12b. **Model-selection sweep (key result)** — "For the hard keratitis task we tried several fixes in parallel. **Diffusion augmentation gave our best single run, 0.488 — but retraining the same recipe with three more seeds gave 0.437, 0.408 and 0.361, so the honest average is 0.42 ± 0.05.** Averaging the four diffusion models gives **0.474**, better than the 10-model plain ensemble (0.451) with fewer than half the models. The intervals still overlap, so it is promising, not proven. Higher resolution and doubling the synthetic images did not help." (In the 24-slide v2 deck this is slide 15, "Diffusion helps, but seeds vary"; every slide carries its own speaker notes.)
13. **Live demo** — **Switch to the portal now** (see runbook below).
14. **Follow-up & next steps + Thank you** — Change-detection across visits; next phase is ethics + hospital data + prospective validation. Invite questions.

---

## Demo runbook (practise this twice before the day)
1. **Before the talk:** double-click `run_portal.bat`. Wait for the browser tab (http://localhost:8501). Leave it open on the **Home** page.
2. On slide 13, Alt-Tab to the browser.
3. Click **Screening** in the sidebar. Pick a task (e.g. "Infectious keratitis"). Tick **"Use a sample for this task"** (or upload a real image). Click **Run screening**.
4. Narrate the 5 outputs as they appear: quality → prediction bar chart → conformal set + **REFER** badge → Grad-CAM heatmap + cornea outline → plain-language summary.
5. Click **Evaluation dashboard** to show the metrics table + calibration/referral charts.
6. **Fallback if the portal won't start:** the deck slide 12 (Evaluation) and slide 13 (demo steps) contain the same content — present from the slides and say "the portal shows this interactively."

Tips: it runs offline on CPU, so no Wi-Fi needed. First prediction takes a few seconds (model load); click once and wait.

---

## Likely examiner questions + strong answers

**Q: Keratitis accuracy is low (~0.49). Isn't that a failure?**
A: Keratitis is a hard 4-class problem on a small public dataset, and we report it honestly. The point of our work
isn't a single accuracy number — it's the *safety design*: the model is well-calibrated (ECE 0.047) and our conformal
referral gate sends uncertain cases to a specialist instead of guessing. We actively improved it — diffusion
augmentation gave our best run (0.488), and an ensemble of four diffusion models reaches 0.474 without relying on one lucky seed — and real
hospital data is the clear path to more.

**Q: Why is the test set single-site? Isn't cross-site important?**
A: Completely agree it's important — that's why we flag it explicitly. The public keratitis split is single-site
(AGEH), so a true held-out-site test wasn't possible. We approximated domain-shift robustness with CycleGAN
harmonisation (balanced accuracy 0.37 → 0.42), and a proper multi-site study is the first item in our next phase.

**Q: What's actually novel here?**
A: Three things working together: (1) explanations *verified* against the cornea mask, not just shown; (2) honest
uncertainty via conformal prediction with an explicit referral gate; (3) an assistant constrained to only repeat
verified findings. Most student projects stop at a classifier; we built the trust layer around it.

**Q: Is this usable in a clinic?**
A: Not yet, and we don't claim it is — it's a research prototype on public data. It needs ethics approval, a hospital
partner, prospective validation and regulatory review. We've built the engineering so that clinical validation is the
next step, not a rebuild.

**Q: How do you prevent the model from "cheating" (looking outside the eye)?**
A: The Grad-CAM++ attention-in-region metric measures how much heat-map mass falls inside the cornea mask; we report
it, so a model that looked at the wrong place would score poorly and we'd catch it.

**Q: How did you train it / what compute?**
A: EfficientNet-B0 and U-Net, trained 50 epochs. We ran the plan in parallel across our team's GPU accounts on the
university DGX to finish quickly. Everything is reproducible — the whole run is logged in the report.

**Q: Data privacy / ethics?**
A: All data is public, de-identified and used under its licence (documented in DATA_LICENSES.md). Any future hospital
data would go through ethics approval and consent.

**Q: What would you do with more time?**
A: Multi-site validation, the requested larger datasets (CatScreen, SLID, EyeHealer), the diffusion work for rare
classes, deploy the backend, and a small prospective screening pilot.

---

## 2-day plan
- **Day 1:** Rehearse the talk twice end-to-end. Run the demo 3× until it's muscle memory. Decide who speaks on which
  slides (suggest: intro/problem = one person, methods/results = one, demo = one). Skim the report Parts K2 and M so
  you can answer number questions. Charge the laptop; test the projector/HDMI.
- **Day 2:** Arrive early, start `run_portal.bat` before you're called, keep the browser tab ready. Present. Breathe.

You have a complete, honest, well-evaluated project with a working demo. That's a strong capstone — present it with confidence.


## AI assistant (new): how to demo it
1. Open a saved case and press **Ask the AI assistant about this case** (or use **AI assistant** in the menu).
2. Tap a quick question such as *What does this result mean?* or *Which hospital should they visit?*; the answer
   uses only that case's facts and is read aloud.
3. Tap the **mic** and ask by voice (Chrome/Edge, needs internet), or type. Under **Voice assistant** in the
   sidebar, switch **Language** to Hindi, Kannada, Tamil or Telugu and **Voice** to Female or Male; set **Answer
   style** to *Clinician* to show the range. Offline, case results, next steps, hospitals and emergencies are in the
   chosen language; longer health answers stay in English (fully translated answers need Claude online).
4. Type *a chemical splashed in my eye* to show the emergency banner and first-aid advice.
5. Patient-style questions that work offline: *I have eye allergy for 15 years, what should I follow?*, *Can I eat
   non-veg with an eye infection?*, *My baby's eye is watering*, *My eyes burn in AC*.
- **Use Microsoft Edge for the demo** (with internet): it has natural Indian voices (English India, Hindi, Kannada,
  Tamil, Telugu). Chrome and offline fall back to the voices installed on the laptop (US English only on this PC).
- **Spoken welcome:** after signing in, a voice assistant greets the doctor by name with the live review and referral
  counts. If the browser blocks autoplay, press *Play greeting*. Replay it from the sidebar (*Play the welcome again*).
- Without an API key the badge says **Offline assistant**: answers come from the case and a built-in knowledge base.
  To use Claude, set `ANTHROPIC_API_KEY` (or run `ant auth login`) and restart the portal.
- If asked: it never diagnoses or names medicines; uncertain results are always referred to a specialist.

## Patient portal (new): how to demo it
Sign in as **ravi / patient123** (the fictional demo patient Ravi Kumar), or create a new account under
*New patient? Create an account* on the login page.
1. **Spoken welcome** in the patient's language, mentioning their latest result ("your last check suggests seeing an
   eye specialist...").
2. **My eye health**: latest check (traffic light), doctor review, appointment, reminders, the eye journey timeline
   and a tip of the day.
3. **Self-check**: cornea or eyelid (trachoma) check by camera or upload; plain-language result; saved for the
   doctor as a *patient self-check*; a reminder is added automatically when referral is advised.
4. **Appointments & reminders**: *Book an eye hospital near you*: tap *Use my current location* (or choose an area or pincode); the nearest hospitals are listed by distance and travel time, on a map, with Google Maps directions; *Book here* opens the doctor, date and time-slot picker (a follow-up with the reviewing doctor is also offered).
   Double booking is blocked. The doctor confirms or declines it on the doctor's **Appointments** page, and the
   patient sees the status. Self-check results and the Emergency page also show the nearest hospitals first.
5. **Symptom diary** (sliders, trend chart, urgent warning at 8/10), **Learn** (cards and myth-or-fact flip cards),
   **Emergency help** (red flags, first aid, call 108 / 112), **My profile** (language, password).
6. Switch **Language** to Kannada, Tamil or Telugu under *Voice assistant*: menus, education and answers change, and
   the answer is spoken with a natural voice in **any browser** (server voice; needs internet).
- Doctor side: Dashboard shows patient self-checks awaiting review; Patients shows each patient's portal login and
  symptom diary; doctors can create a portal login for an existing patient.
- Specialist names are marked samples; the hospitals are real. Translations are machine-made (review pending).

## New: four care-loop features (how to demo)
1. **Doctor calendar** (doctor menu *My schedule*): set working days, sessions (e.g. `09:30-12:30,14:00-17:00`),
   appointment length and leave days. Patient booking then offers only those times ("the doctor does not work on
   this day" otherwise). The admin can edit any doctor's calendar.
2. **At-home vision test** (patient menu *Vision test*): match a bank card to calibrate the screen, cover one eye,
   stand 2 or 3 m away and answer which way the E points (buttons or arrow keys). Result in Snellen (6/6 ... 6/60),
   saved to a history chart; a drop of two lines is flagged. Includes an Amsler grid check. Screening aid only.
3. **Eye-drop schedule** (doctor: open a case, *Eye-drop schedule for the patient*; patient: *My eye drops*): the
   doctor enters the drops and how often; the patient sees the next dose, ticks each dose, and the doctor sees the
   adherence percentage. The AI never suggests medicines.
4. **Referral follow-up** (doctor menu): did referred patients book and reach the specialist? Booked/visited rates,
   overdue cases (not booked in 3 days, or not seen in 14), log calls and outcomes, and send a booking reminder to
   the patient's app. Patients also see a "please book" nudge on their home page a day after a referral.
