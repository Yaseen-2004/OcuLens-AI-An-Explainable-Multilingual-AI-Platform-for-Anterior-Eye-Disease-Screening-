from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.platypus import Preformatted, Flowable

NAVY = colors.HexColor("#1f3a5f")
FILLS = {"blue": "#dbe7f5", "green": "#d9f0dc", "amber": "#fdebc8", "red": "#f8d4d4",
         "grey": "#eeeeee", "white": "#ffffff", "purple": "#e6dcf3"}

def _lines(d, cx, cy, txt, fs, bold=False):
    ls = txt.split("\n")
    n = len(ls)
    for i, t in enumerate(ls):
        y = cy + ((n - 1) / 2.0 - i) * (fs + 1.8) - fs * 0.35
        d.add(String(cx, y, t, fontSize=fs, fontName="Helvetica-Bold" if bold else "Helvetica",
                     textAnchor="middle", fillColor=colors.black))

def box(d, cx, cy, w, h, txt, fill="blue", fs=7.2, bold=False):
    d.add(Rect(cx - w / 2.0, cy - h / 2.0, w, h, rx=4, ry=4, fillColor=colors.HexColor(FILLS[fill]),
               strokeColor=NAVY, strokeWidth=0.8))
    _lines(d, cx, cy, txt, fs, bold)

def diamond(d, cx, cy, w, h, txt, fs=7.0):
    d.add(Polygon([cx - w / 2.0, cy, cx, cy + h / 2.0, cx + w / 2.0, cy, cx, cy - h / 2.0],
                  fillColor=colors.HexColor(FILLS["amber"]), strokeColor=NAVY, strokeWidth=0.8))
    _lines(d, cx, cy, txt, fs)

def container(d, x, y, w, h, title, dashed=False):
    r = Rect(x, y, w, h, rx=6, ry=6, fillColor=colors.HexColor("#f7f7f7"), strokeColor=colors.HexColor("#888888"),
             strokeWidth=0.8)
    if dashed:
        r.strokeDashArray = [4, 3]
    d.add(r)
    d.add(String(x + 8, y + h - 12, title, fontSize=7.5, fontName="Helvetica-Bold", fillColor=colors.HexColor("#555555")))

def arrow(d, pts, label=None, lpos=None):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#333333"), strokeWidth=0.9))
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / L, dy / L
    sz = 4.5
    bx, by = x2 - ux * sz, y2 - uy * sz
    d.add(Polygon([x2, y2, bx - uy * sz * 0.5, by + ux * sz * 0.5, bx + uy * sz * 0.5, by - ux * sz * 0.5],
                  fillColor=colors.HexColor("#333333"), strokeColor=colors.HexColor("#333333")))
    if label:
        lx, ly = lpos if lpos else ((x1 + x2) / 2.0 + 3, (y1 + y2) / 2.0 + 3)
        d.add(String(lx, ly, label, fontSize=6.5, fontName="Helvetica-Oblique", fillColor=colors.HexColor("#8a1f1f")))

def note(d, x, y, t, anchor="start", fs=6.8):
    d.add(String(x, y, t, fontSize=fs, fontName="Helvetica-Oblique", fillColor=colors.HexColor("#555555"), textAnchor=anchor))

class Fit(Flowable):
    """Scale a Drawing down to the available width."""
    def __init__(self, d, maxw=482):
        Flowable.__init__(self)
        self.d = d
        self.k = min(1.0, maxw / float(d.width))
        self.width = d.width * self.k
        self.height = d.height * self.k
    def wrap(self, aw, ah):
        return self.width, self.height
    def draw(self):
        self.canv.saveState()
        self.canv.scale(self.k, self.k)
        from reportlab.graphics import renderPDF
        renderPDF.draw(self.d, self.canv, 0, 0)
        self.canv.restoreState()

# =============================================================== PART E
s += [p("Part E - Complete proposed project structure", H1),
      p("<b>Status: design only.</b> Nothing below has been created yet. It is the structure I recommend building, with each part "
        "tied to the report step it implements. Names can be changed; the separation of responsibilities is what matters.")]

s += [p("E1. Layers of the system", H2)]
s.append(table([
    ["Layer", "Contains", "Runs where", "Report steps"],
    ["Research / training", "Data, labeling, GAN/diffusion, segmentation, classifier, uncertainty, explainability, evaluation", "GPU machine / cloud", "1, 3, 4, 5, 6, 7"],
    ["Inference service", "Quality check, eye crop, segmenter, classifier, uncertainty, heatmap", "Clinic workstation or server", "2, 4, 5, 6, 7, 12"],
    ["Web / desktop app", "Image upload or capture, quality prompts, results, heatmaps, history, language choice", "Browser at the clinic", "2, 12"],
    ["Cloud backend", "API, database, triage engine, LLM + RAG, follow-up, consent, audit logs", "Server", "8, 9, 10, 12"],
    ["Doctor dashboard", "Review queue, corrections, patient history, alerts", "Web", "11"],
    ["Evaluation and governance", "Metrics, fairness, ablations, ethics docs, model card, reporting checklists", "Anywhere", "Section 8 and 10"],
], [3.2*cm, 7.2*cm, 3.2*cm, 3.4*cm]))

s += [p("E2. Folder tree", H2)]
TREE = r"""oculens-ai/
|-- README.md, requirements.txt (or pyproject.toml), .gitignore
|-- configs/                      one YAML per module (paths, thresholds, hyper-parameters)
|   |-- data.yaml  quality.yaml  segmentation.yaml  classifier.yaml
|   `-- uncertainty.yaml  triage_rules.yaml  llm.yaml
|-- docs/
|   |-- literature_review/        notes and citations (Step 0)
|   |-- ethics/                   committee application, consent form, DPDP notes
|   |-- labeling_guideline.md     Region -> Condition -> Severity rules, LOCS III-style grades
|   |-- regulatory_notes.md       CDSCO device-classification advice
|   `-- model_card.md             intended use, limits, subgroup results
|-- data/                         NEVER committed to git; versioned with DVC or similar
|   |-- raw/public/  raw/hospital/          original images, untouched
|   |-- annotations/ labels.csv  masks/     image labels and pixel masks
|   |-- processed/                          cropped and normalized images
|   |-- splits/  train.csv val.csv test.csv patient-level split, test is real-only and locked
|   |-- synthetic/                          generated images (train only)
|   `-- DATA_LICENSES.md                    license and image type for every dataset
|-- src/oculens/
|   |-- data/            datasets.py  splits.py  transforms.py  agreement_kappa.py
|   |-- quality/         rules.py (blur, glare, dark, eye open)  quality_cnn.py  guidance.py
|   |-- preprocessing/   eye_crop.py (detector / segmentation)  clahe.py  glare_removal.py  normalize.py
|   |-- generative/      stylegan2_ada/  diffusion/  harmonize/ (CycleGAN-style)  validate_synthetic.py
|   |-- segmentation/    models/ (unet, attn_unet, nnunet, transunet, medsam)  losses.py
|   |                    train.py  evaluate.py (Dice, IoU, HD95)
|   |-- classification/  backbones.py  heads.py (condition, severity, region)  train.py
|   |                    calibrate.py (temperature scaling)  evaluate.py
|   |-- uncertainty/     ensemble.py  mc_dropout.py  conformal.py  referral.py
|   |-- explain/         gradcam.py  scorecam.py  integrated_gradients.py  attention_rollout.py
|   |                    region_check.py (attention-in-region)  counterfactual.py  tcav.py  metrics.py
|   |-- triage/          questionnaire.py  rules.py (safety overrides)  fusion.py
|   |-- assistant/       findings_schema.py  prompts/  rag/ (index, retriever)  guardrails.py
|   |                    translate.py  report_pdf.py
|   |-- followup/        align.py  siamese_change.py  progression.py  schedule.py  postop_monitor.py
|   |-- export/          to_onnx.py  benchmark_latency.py
|   `-- utils/           logging.py  seed.py  io.py
|-- scripts/             download_public_data.py  make_splits.py  train_all.sh  run_ablation.py
|-- experiments/         runs/ (tracked by W&B or MLflow)  ablation_results/
|-- models/              checkpoints/  exported/ (.onnx)
|-- web/                 React front-end (or Streamlit for the MVP)
|   |-- upload/          image upload, quality prompts
|   |-- screens/         result, heatmap, triage, history, language, consent
|   `-- api_client/      calls the backend service
|-- backend/             FastAPI service
|   |-- app/main.py
|   |-- api/             auth.py  scans.py  triage.py  assistant.py  followup.py  doctors.py
|   |-- db/              models.py  migrations/   (PostgreSQL)
|   |-- services/        inference_service  triage_service  llm_service  followup_service  notification_service
|   |-- security/        consent.py  encryption.py  audit_log.py
|   `-- tests/
|-- dashboard/           doctor web UI (review queue, corrections, patient timeline)
|-- evaluation/          metrics.py  fairness.py  calibration_plots.py  tripod_ai_checklist.md
|-- tests/               unit tests per module (quality, splits, triage rules, guardrails)
`-- deploy/              Dockerfile  docker-compose.yml  ci/
"""
s.append(Preformatted(TREE, ParagraphStyle("tree", fontName="Courier", fontSize=6.6, leading=8.1)))

s += [p("E3. Module interfaces (what goes in, what comes out)", H2)]
s.append(table([
    ["Module", "Input", "Output", "Success check"],
    ["quality", "Uploaded image", "ok / reason code + user prompt", "Rejection accuracy"],
    ["preprocessing", "Accepted image", "Cropped, enhanced, normalized eye image", "Same output in training and in the deployed service"],
    ["segmentation", "Eye image", "Masks: eyelid, conj/sclera, cornea/iris, pupil, lesions", "Dice, IoU, HD95"],
    ["classification", "Image + masks", "Per region: condition, severity, probabilities", "Sensitivity, AUROC, kappa"],
    ["uncertainty", "Probabilities (ensemble)", "Prediction set + refer flag", "Missed-case rate, referral rate"],
    ["explain", "Image, model, masks", "Heatmap + attention-in-region ratio + reliable flag", "Pointing game, deletion/insertion AUC"],
    ["triage", "Findings + questionnaire", "Routine / Soon / Urgent", "Rules signed off by clinician"],
    ["assistant", "Structured findings only", "Patient text, doctor report", "Factual accuracy, safety review"],
    ["followup", "Scan history", "Progressed / stable / improved, risk, schedule, alerts", "Agreement with clinician"],
], [2.6*cm, 3.8*cm, 6.4*cm, 4.2*cm]))

s += [p("E4. Findings schema (the only thing the LLM sees)", H2),
      Preformatted("""{
  "scan_id": "...", "patient_id": "...", "eye": "left | right", "captured_at": "...",
  "image_source": "slit_lamp | clinic_camera", "device_model": "...",
  "quality": {"ok": true},
  "findings": [
    {"region": "lens", "condition": "cataract", "severity": "moderate",
     "probability": 0.86, "prediction_set": ["moderate", "early"],
     "uncertainty": "low | high", "attention_in_region": 0.0 to 1.0, "explanation_reliable": true}
  ],
  "symptoms": {"pain": false, "blurred_vision": true, "discharge": false,
               "diabetes": false, "recent_eye_surgery": false},
  "triage": "routine | soon | urgent | refer",
  "language": "hi | ta | te | ..."
}""", ParagraphStyle("js", fontName="Courier", fontSize=7, leading=8.6)),
      p("Values shown are placeholders, not results. Freeze this schema before building the assistant (Step 9).")]

s += [p("E5. Database tables and API endpoints (cloud)", H2)]
s.append(table([
    ["Table", "Key fields"],
    ["patients", "id, pseudonymous code, age band, language, consent status (no free-text identity in image tables)"],
    ["scans", "id, patient_id, eye, captured_at, device model, image URI, quality result"],
    ["findings", "scan_id, region, condition, severity, probability, uncertainty, attention ratio, reliable flag"],
    ["symptoms", "scan_id, questionnaire answers"],
    ["triage_results", "scan_id, level, rule fired, timestamp"],
    ["followups", "patient_id, schedule, change label, progression risk, post-surgery day"],
    ["corrections", "scan_id, doctor_id, original label, corrected label, used_for_retraining flag"],
    ["audit_log", "who, what, when (every access to patient data)"],
], [3.5*cm, 13.5*cm]))
s += [Spacer(1, 5)]
s.append(table([
    ["Endpoint", "Purpose"],
    ["POST /scans", "Upload scan metadata + findings (+ image if consented)"],
    ["POST /triage", "Fuse findings and symptoms, return level"],
    ["POST /assistant/explain, /assistant/ask", "Grounded explanation and Q&amp;A in chosen language"],
    ["GET /patients/{id}/followup", "Timeline, trend, next scan date"],
    ["POST /followup/postop-alert", "Warning signs reported, notify surgeon"],
    ["GET /doctor/queue, POST /doctor/correction", "Review flagged cases, submit corrections"],
    ["DELETE /patients/{id}", "Deletion on request (DPDP Act)"],
], [6.5*cm, 10.5*cm]))

s += [p("E6. Candidate public datasets (clinical anterior-eye images)", H2),
      p("From the web searches in this session. Licence and download status were <b>not</b> verified for any of them; check each before use.")]
s.append(table([
    ["Dataset", "Image type and labels", "Use in this project", "Caution"],
    ["SLID (slit-lamp)", "Anterior-segment slit-lamp images; cataract, intraocular lens and about 11 other lesion classes; boxes and segmentation", "Steps 4 and 5: segmentation and lesion/cataract classification", "Release said to be on GitHub 'upon publication': confirm it is available"],
    ["SUSTech-SYSU", "712 fluorescein-stained slit-lamp images; corneal ulcer segmentation and 5 severity grades", "Cornea region: ulcer segmentation and grading", "CC0 on Figshare (downloaded, see Part G); single hospital"],
    ["Nuclear Cataract Database", "1,320 slit-lamp images, 115 patients (Topcon); grades NOT included in the download", "Unlabeled: pre-training or once grades are obtained", "CC BY 4.0; downloaded (Part G); single hospital, nuclear type only"],
    ["Infectious Keratitis (Figshare)", "1,373 slit-lamp images, two hospitals; HSK, bacterial, fungal, other keratitis", "Steps 5, 8: cornea infection classification", "CC BY 4.0; downloaded (Part H); counts differ from description"],
    ["Eye Diseases Classification (Mendeley)", "About 2,300 web-sourced images: cataract, conjunctivitis, uveitis, eyelid, normal", "Step 5: prototyping only", "CC BY 4.0; downloaded (Part H); not clinical-grade, never for testing"],
    ["SBVPI", "2,399 high-quality eye images with sclera masks; iris and pupil masks for only about 100 images", "Sclera segmentation; small subset for iris and pupil", "Request form; few subjects (55); check capture device"],
    ["OpenEDS", "About 12.8k VR-headset eye images with iris, sclera and pupil masks", "Optional pre-training for iris/pupil segmentation", "Different image type; download on request"],
    ["ESCRS-linked review of 26 public anterior-segment datasets", "Survey of public datasets", "Master list for the literature review", "Most listed datasets are small or poorly described"],
], [3.0*cm, 5.2*cm, 4.4*cm, 4.4*cm]))
s += [Spacer(1, 4),
      p("<b>Not suitable:</b> fundus sets (ODIR-5K, most Kaggle eye-disease sets) show the retina, not the front of the eye. "
        "Smartphone sets such as MOBIUS no longer fit. Your own hospital images are still needed for labeled severity and validation."),
      PageBreak()]

# =============================================================== PART F
s += [p("Part F - Detailed flow diagrams", H1),
      p("Five diagrams. Boxes are processes, amber diamonds are decisions, red italics are branch labels. "
        "Thresholds (blur limit, attention ratio, referral rate) are set during implementation with the clinical advisor, not fixed here.")]

# ---------- Diagram 1
d = Drawing(500, 600)
container(d, 5, 450, 470, 145, "TRAINING TIME (offline, research) - generative models are never used on the patient", dashed=True)
box(d, 80, 548, 130, 42, "Data\npublic + hospital clinical images\nlabels, masks, patient split", "grey")
box(d, 240, 548, 130, 42, "GAN / diffusion\nrare-class synthetic images", "purple")
box(d, 400, 548, 130, 42, "Cross-device harmonization\nCycleGAN-style (optional)", "purple")
box(d, 240, 478, 440, 42, "Train: segmenter, classifier ensemble, temperature scaling, conformal calibration\nevaluate on LOCKED real-only test set", "blue")
for x in (80, 240, 400):
    arrow(d, [(x, 527), (x, 499)])
arrow(d, [(240, 457), (240, 425)], "deploy to inference service", (248, 436))
container(d, 5, 250, 470, 175, "INFERENCE SERVICE (clinic workstation or server)")
box(d, 80, 375, 130, 42, "1 Image intake + quality\nupload, retake prompts", "blue")
box(d, 240, 375, 130, 42, "2 Preprocessing\neye crop, CLAHE, glare", "blue")
box(d, 400, 375, 130, 42, "3 Segmentation\neyelid ... lens masks", "blue")
arrow(d, [(145, 375), (175, 375)]); arrow(d, [(305, 375), (335, 375)])
box(d, 400, 290, 130, 42, "4 Region classifier\ncondition + severity", "blue")
box(d, 240, 290, 130, 42, "5 Uncertainty\nensemble, conformal", "blue")
box(d, 80, 290, 130, 42, "6 Explainability\nGrad-CAM++ + mask check", "blue")
arrow(d, [(400, 354), (400, 311)]); arrow(d, [(335, 290), (305, 290)]); arrow(d, [(175, 290), (145, 290)])
container(d, 5, 95, 470, 130, "BACKEND (clinic server or cloud)")
box(d, 80, 150, 130, 42, "7 Decision engine\nfindings + symptoms", "green")
box(d, 240, 150, 130, 42, "8 LLM assistant\ngrounded, multilingual", "green")
box(d, 400, 150, 130, 42, "9 Follow-up\nchange detection", "green")
arrow(d, [(80, 250), (80, 171)], "findings", (86, 232))
arrow(d, [(145, 150), (175, 150)]); arrow(d, [(305, 150), (335, 150)])
box(d, 240, 45, 300, 40, "Doctor dashboard: review, confirm or correct each flagged result", "amber")
arrow(d, [(240, 95), (240, 65)], "flagged cases", (248, 78))
arrow(d, [(390, 45), (490, 45), (490, 520), (475, 520)])
note(d, 395, 30, "corrections -> active learning", anchor="start")
note(d, 395, 20, "-> retrain -> validate -> release", anchor="start")
s += [p("Diagram 1 - End-to-end system", H2), Fit(d), Spacer(1, 6)]
s.append(PageBreak())

# ---------- Diagram 2
d = Drawing(500, 650)
box(d, 170, 625, 170, 30, "Technician uploads or captures image", "grey")
box(d, 170, 580, 170, 30, "Receive image + patient and eye ID", "blue")
arrow(d, [(170, 610), (170, 595)])
diamond(d, 170, 520, 190, 66, "Quality OK?\nfocus, glare, exposure, eye open")
arrow(d, [(170, 565), (170, 553)])
box(d, 400, 520, 130, 48, "Prompt technician:\n'refocus' or\n'reduce glare' - recapture", "amber")
arrow(d, [(265, 520), (335, 520)], "no", (290, 525))
arrow(d, [(400, 544), (400, 580), (255, 580)], "retake", (405, 560))
box(d, 170, 450, 220, 40, "Eye crop (detector / segmentation)\nCLAHE + reflection removal + resize", "blue")
arrow(d, [(170, 487), (170, 470)], "yes", (176, 476))
box(d, 170, 395, 220, 40, "Segmentation masks\neyelid, conjunctiva, sclera, cornea, iris, pupil, lens", "blue")
arrow(d, [(170, 430), (170, 415)])
box(d, 170, 340, 220, 40, "Region classifier (CNN + ViT, multi-task)\ncondition, severity, region, calibrated probability", "blue")
arrow(d, [(170, 375), (170, 360)])
diamond(d, 170, 275, 200, 66, "Uncertainty high?\nensemble spread, conformal set")
arrow(d, [(170, 320), (170, 308)])
box(d, 400, 275, 130, 56, "REFER\nretake image or see doctor\nnever report 'normal'", "red")
arrow(d, [(270, 275), (335, 275)], "yes", (295, 280))
box(d, 170, 205, 220, 40, "Explanation: Grad-CAM++ heatmap\n+ attention-in-region ratio", "blue")
arrow(d, [(170, 242), (170, 225)], "no", (176, 230))
diamond(d, 170, 140, 200, 66, "Attention on the predicted\nregion above threshold?")
arrow(d, [(170, 185), (170, 173)])
box(d, 400, 140, 130, 48, "Flag explanation\n'unreliable'\n-> doctor review", "red")
arrow(d, [(270, 140), (335, 140)], "no", (295, 145))
box(d, 170, 65, 250, 48, "Structured findings (JSON)\nregion, finding, severity, confidence,\nuncertainty, attention score, flags", "green")
arrow(d, [(170, 107), (170, 89)], "yes", (176, 95))
arrow(d, [(400, 116), (400, 65), (295, 65)])
box(d, 170, 15, 250, 24, "Show result in the web app; store in the patient record", "grey")
arrow(d, [(170, 41), (170, 27)])
note(d, 400, 240, "REFER goes straight to", "start")
note(d, 400, 231, "the result as a referral", "start")
s += [p("Diagram 2 - Runtime analysis flow with decisions (Steps 2 to 7)", H2), Fit(d), Spacer(1, 6)]
s.append(PageBreak())

# ---------- Diagram 3
d = Drawing(500, 560)
box(d, 125, 535, 210, 40, "Image findings\nregion, severity, uncertainty", "blue")
box(d, 375, 535, 210, 40, "Symptom questionnaire\nage, pain, discharge, vision, diabetes, surgery", "blue")
box(d, 250, 480, 200, 30, "Multimodal fusion", "blue")
arrow(d, [(125, 515), (125, 480), (150, 480)]); arrow(d, [(375, 515), (375, 480), (350, 480)])
diamond(d, 250, 420, 240, 70, "Safety rule hit?\ne.g. pain + sudden vision loss")
arrow(d, [(250, 465), (250, 455)])
box(d, 430, 420, 110, 40, "URGENT\nsee doctor < 24 h", "red", bold=True)
arrow(d, [(370, 420), (375, 420)], "yes", (376, 428))
diamond(d, 250, 350, 230, 60, "Image finding grade?")
arrow(d, [(250, 385), (250, 380)], "no", (256, 383))
box(d, 80, 270, 130, 44, "Urgent-grade finding\nsuspected ulcer, post-op\npain + redness", "grey")
box(d, 250, 270, 130, 44, "Early or moderate\ncataract, mild/moderate\nconjunctivitis", "grey")
box(d, 420, 270, 130, 44, "No significant finding", "grey")
arrow(d, [(135, 350), (80, 350), (80, 292)]); arrow(d, [(250, 320), (250, 292)]); arrow(d, [(365, 350), (420, 350), (420, 292)])
box(d, 80, 195, 130, 44, "URGENT\nsee doctor within 24 h", "red", bold=True)
box(d, 250, 195, 130, 44, "SOON\nsee eye doctor within weeks", "amber", bold=True)
arrow(d, [(80, 248), (80, 217)]); arrow(d, [(250, 248), (250, 217)])
diamond(d, 420, 205, 130, 64, "Uncertain image\nor any symptom?")
arrow(d, [(420, 248), (420, 237)])
arrow(d, [(355, 205), (315, 205)], "yes -> SOON / REFER", (318, 212))
box(d, 420, 130, 130, 44, "ROUTINE\nrescan in 6-12 months", "green", bold=True)
arrow(d, [(420, 173), (420, 152)], "no", (426, 160))
box(d, 250, 60, 460, 50, "Grounded LLM assistant: explains verified findings in the patient's language\nguardrails: 'possible signs of', escalate emergencies, no medication dosing\n+ doctor-ready report with images and heatmaps", "green")
arrow(d, [(80, 173), (80, 85)]); arrow(d, [(250, 173), (250, 85)]); arrow(d, [(420, 108), (420, 85)])
note(d, 250, 20, "A safety rule always overrides the AI result; an uncertain result is never reported as normal.", anchor="middle")
s += [p("Diagram 3 - Triage decision flow (Step 8) and hand-off to the assistant (Step 9)", H2), Fit(d), Spacer(1, 6)]
s.append(PageBreak())

# ---------- Diagram 4
d = Drawing(500, 540)
box(d, 125, 510, 210, 40, "Public datasets\nODIR-5K, Kaggle (check license, image type)", "grey")
box(d, 375, 510, 210, 40, "Hospital clinical images (slit-lamp / camera)\nconsent + ethics approval + imaging protocol", "grey")
box(d, 250, 445, 280, 48, "Labeling: two ophthalmologists per image\nregion -> condition -> severity + pixel masks\nCohen's kappa; third expert resolves disagreements", "blue")
arrow(d, [(125, 490), (125, 445), (110, 445)]); arrow(d, [(375, 490), (375, 445), (390, 445)])
box(d, 250, 380, 280, 36, "Quality filter + preprocessing (same code as in the deployed service)", "blue")
arrow(d, [(250, 421), (250, 398)])
box(d, 250, 325, 200, 34, "Patient-level split (by patient, not image)", "amber")
arrow(d, [(250, 362), (250, 342)])
box(d, 75, 250, 120, 40, "TRAIN\nreal images", "green")
box(d, 250, 250, 130, 40, "VALIDATION /\nCALIBRATION", "green")
box(d, 425, 250, 120, 40, "TEST: real only\nLOCKED", "red", bold=True)
arrow(d, [(150, 325), (75, 325), (75, 270)]); arrow(d, [(250, 308), (250, 270)]); arrow(d, [(350, 325), (425, 325), (425, 270)])
box(d, 90, 170, 160, 56, "GAN / diffusion / CycleGAN\ntrained on TRAIN images only\nchecks: FID, TSTR, expert review", "purple")
arrow(d, [(75, 230), (75, 198)], "synthetic + harmonized", (80, 208))
box(d, 170, 95, 260, 44, "Train segmenter + classifier ensemble\ntemperature scaling, conformal threshold", "blue")
arrow(d, [(90, 142), (90, 117)])
arrow(d, [(250, 230), (250, 117)], "tune + calibrate", (256, 175))
box(d, 250, 30, 340, 44, "Evaluate on locked TEST (real only): sensitivity, AUROC, ECE,\nfairness by age / sex / skin tone / iris / device; then external hospital + pilot", "amber")
arrow(d, [(170, 73), (170, 52)])
arrow(d, [(425, 230), (425, 30), (420, 30)])
note(d, 300, 130, "Synthetic images never", "start")
note(d, 300, 121, "enter validation or test.", "start")
s += [p("Diagram 4 - Data and training flow (Steps 1, 3, 4, 5, 6)", H2), Fit(d), Spacer(1, 6)]
s.append(PageBreak())

# ---------- Diagram 5
d = Drawing(500, 540)
box(d, 250, 515, 260, 30, "New clinic image + symptom check", "blue")
box(d, 250, 468, 300, 36, "Quality check, segmentation, classification\n(same analysis pipeline)", "blue")
arrow(d, [(250, 500), (250, 486)])
box(d, 250, 418, 300, 30, "Store in patient history (cloud, encrypted, consent)", "green")
arrow(d, [(250, 450), (250, 433)])
diamond(d, 250, 355, 190, 60, "Previous scan exists?")
arrow(d, [(250, 403), (250, 385)])
box(d, 420, 355, 120, 44, "Set baseline\nschedule first rescan", "grey")
arrow(d, [(345, 355), (360, 355)], "no", (347, 361))
box(d, 250, 285, 260, 40, "Align previous + current image\nSiamese change network", "blue")
arrow(d, [(250, 325), (250, 305)], "yes", (256, 312))
diamond(d, 250, 225, 130, 60, "Change?")
arrow(d, [(250, 265), (250, 255)])
box(d, 90, 150, 110, 40, "PROGRESSED", "red", bold=True)
box(d, 250, 150, 110, 40, "STABLE", "grey", bold=True)
box(d, 410, 150, 110, 40, "IMPROVED", "green", bold=True)
arrow(d, [(185, 225), (90, 225), (90, 170)]); arrow(d, [(250, 195), (250, 170)]); arrow(d, [(315, 225), (410, 225), (410, 170)])
box(d, 250, 80, 300, 44, "Trend chart + progression risk (6-12 months)\nupdate rescan schedule + send reminders", "blue")
arrow(d, [(90, 130), (90, 80), (100, 80)]); arrow(d, [(250, 130), (250, 102)]); arrow(d, [(410, 130), (410, 80), (400, 80)])
box(d, 250, 22, 480, 36, "Post-surgery clinic follow-up (days 1, 7, 30): compare images, check warning signs (redness, cloudiness, discharge)\n+ symptoms (pain, vision drop) -> alert surgeon. Doctor correction of any result -> active learning -> retrain -> validate -> release", "amber", fs=6.5)
arrow(d, [(250, 58), (250, 40)])
s += [p("Diagram 5 - Longitudinal follow-up, post-surgery monitoring and feedback loop (Steps 10 and 11)", H2), Fit(d), Spacer(1, 6)]
