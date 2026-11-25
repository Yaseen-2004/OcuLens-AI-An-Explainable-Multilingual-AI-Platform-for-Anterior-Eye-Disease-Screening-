import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, ListFlowable, ListItem, KeepTogether)

OUT = r"D:\Capston_Project\OcuLens-AI_Step_Log_and_Pre-Implementation_Guide.pdf"

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1f3a5f"))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#1f3a5f"))
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=10.5, spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#444444"))
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=10, leading=14, spaceAfter=4)
CELL = ParagraphStyle("CELL", parent=B, fontSize=9, leading=12, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, textColor=colors.white, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("T", parent=ss["Title"], fontSize=22, leading=27, textColor=colors.HexColor("#1f3a5f"))

def p(t, s=B): return Paragraph(t, s)
def bullets(items):
    return ListFlowable([ListItem(p(i), leftIndent=12) for i in items], bulletType="bullet", start="-", leftIndent=14)
def table(rows, widths, header=True):
    data = []
    for r, row in enumerate(rows):
        data.append([p(c, CELLH if (header and r == 0) else CELL) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")))
    t.setStyle(TableStyle(st))
    return t

def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
    c.drawString(2*cm, 1.2*cm, "OcuLens-AI - Step Log and Pre-Implementation Guide")
    c.drawRightString(A4[0]-2*cm, 1.2*cm, "Page %d" % d.page); c.restoreState()

s = []
s += [Spacer(1, 3*cm), p("OcuLens-AI", TITLE),
      p("Step Log and Pre-Implementation Guide", ParagraphStyle("st", parent=TITLE, fontSize=16, leading=20)),
      Spacer(1, 0.5*cm),
      p("Prepared: 17 Nov 2026. Source: the OcuLens-AI project report (17 pages, @Zivora)."),
      p("<b>Revised design (this version):</b> the system is <b>not smartphone-based</b>. It analyses clinical anterior-eye images "
        "(slit-lamp or clinic camera) and runs as a web/desktop application. This replaces the smartphone assumptions in the source report."),
      Spacer(1, 0.5*cm),
      p("This document has twelve parts. <b>Part A</b> records every step I performed while producing this file. "
        "<b>Part B</b> explains the project in plain terms. <b>Part C</b> explains each project step and what must be "
        "prepared <i>before</i> implementing it. <b>Part D</b> gives a recommended build order. "
        "<b>Part E</b> (at the bottom) gives the complete proposed project structure and <b>Part F</b> gives five detailed flow diagrams. <b>Part G</b> records the first dataset downloads and <b>Part H</b> the second round. <b>Part I</b> covers the third round and the image total. <b>Part J</b> records the project build and server setup, <b>Part K</b> the training results, and <b>Part L</b> the run logs."),
      Spacer(1, 0.4*cm),
      p("<i>Note: OcuLens-AI is a screening and decision-support tool. It does not replace an ophthalmologist's diagnosis.</i>"),
      PageBreak()]

# ---------------- PART A
s += [p("Part A - Work log: steps I performed", H1)]
s.append(table([
    ["#", "Step", "What I did", "Result"],
    ["1", "Read the request", "You asked for (a) a PDF noting each step I perform and (b) an explanation of each project step and the process needed before implementing it.", "Two deliverables identified: work log + pre-implementation guide, in one PDF."],
    ["2", "Read the project report", "Went through all 17 pages of the OcuLens-AI report you attached: summary, problem, objectives and RQ1-RQ5, novelty, scope and label taxonomy, architecture, the 12 methodology steps, evaluation, stack/team/timeline, ethics and risks.", "Full understanding of the 5 runtime stages, 12 build steps, and the 8-10 month plan."],
    ["3", "Checked the working folder", "Working folder is c:\\Users\\USER\\OneDrive\\Desktop\\Capston_Project. It is not a git repository. I made no changes to it other than adding this PDF.", "Output location chosen."],
    ["4", "Loaded the PDF skill", "Loaded the PDF-creation guidance (use reportlab for creating PDFs).", "Method chosen: reportlab / Platypus."],
    ["5", "Checked tooling", "Tried to import reportlab; it was not installed.", "Needed to install it."],
    ["6", "Installed reportlab", "Ran pip install reportlab (version 5.1.0 installed).", "Tool available."],
    ["7", "Designed the document", "Split into Part A (log), B (project overview), C (per-step explanation + prerequisites), D (build order). Used plain ASCII text to avoid font glyph problems.", "Outline fixed."],
    ["8", "Wrote the generator script", "Wrote a Python script in my scratch folder (not in your project) that builds the PDF.", "Script ready."],
    ["9", "Generated the PDF", "Ran the script; saved the PDF into your project folder.", "File created (name shown at the end of this document)."],
    ["10", "Verified the output", "Checked that the file exists and counts its pages. (The first build failed because reportlab had been installed under a different Python; I reinstalled it with python -m pip and rebuilt.)", "First version: 10 pages."],
    ["11", "Discussed scope with you", "You said you have 10 months and want 20% of the project in one day. I explained that ethics, hospital partnership and own-data labeling cannot be finished in a day, and proposed a one-day code plan on public data.", "Scope of 'day one' agreed in chat."],
    ["12", "Received the revision request", "You asked for the complete structure in detail plus detailed flow diagrams, added at the bottom of the PDF.", "Parts E and F added; this log updated."],
    ["13", "Designed the project structure", "Defined the folder tree, module interfaces, findings JSON schema, database tables and API endpoints, each mapped to a report step. This is a proposed design only; no folders or code were created.", "Part E."],
    ["14", "Drew the flow diagrams", "Drew five diagrams in code: end-to-end system, on-device runtime decisions, triage decisions, training and data flow, and follow-up/feedback loop.", "Part F."],
    ["15", "Rebuilt the PDF", "Re-ran the generator so the new parts sit at the bottom of the same file.", "19-page version."],
    ["16", "Researched datasets", "Ran three web searches: public anterior-eye datasets, eye-region segmentation datasets, corneal ulcer datasets. Reported findings and flagged what was not verified.", "Dataset advice given in chat; now also in Part E6."],
    ["17", "Scope change", "You said not to make it for smartphone. I asked two questions; you chose: clinical anterior-eye images with a web/desktop app, and rewrite everything consistently.", "Direction fixed."],
    ["18", "Rewrote the content", "Changed every smartphone-specific item: capture, on-device models, MediaPipe, offline mode, mobile app, home monitoring, RQ2 and RQ5, folder tree, all diagrams. Added a table of what changed and the dataset list.", "Revised parts A to F."],
    ["19", "Rebuilt and checked", "Regenerated the PDF, rendered pages to images and inspected the diagrams.", "21-page version."],
    ["20", "Dataset recommendation", "Ran more searches (SLID availability, pterygium/conjunctivitis, cataract slit-lamp sets, CatScreen, EyeHealer, CADMUS) and ranked datasets.", "Recommendation given in chat."],
    ["21", "Moved to D:\Capston_Project", "You gave D:\Capston_Project as the folder. It already contained a copy of the PDF. I created D:\Capston_Project\datasets and write the rebuilt PDF there.", "Output path changed."],
    ["22", "Located download sources", "Read dataset pages and APIs (Figshare, Mendeley, GitHub, paper pages). Found open sources for SUSTech-SYSU and Nuclear Cataract; found no open source for the others.", "2 downloadable, others gated."],
    ["23", "Downloaded, found corruption, fixed", "First downloads were killed and resumed; MD5 and CRC checks failed. Deleted and re-downloaded both from scratch.", "See Part G4."],
    ["24", "Verified and extracted", "SUSTech-SYSU MD5 matches; all 1,436 Nuclear Cataract files match published SHA-256. Extracted each into its own folder with a path-safety check.", "Part G2."],
    ["25", "Wrote dataset register and Part G", "Added DATA_LICENSES.md in the datasets folder and a new Part G in this PDF; updated E6.", "24-page version."],
    ["26", "Suggested free datasets", "Searched for open anterior-eye datasets, then checked licences and file lists through the Figshare, Mendeley and Zenodo APIs. Rejected a confocal-microscopy set and a mostly-fundus set.", "Two candidates recommended in chat."],
    ["27", "Downloaded round 2", "After your approval, downloaded the Infectious Keratitis zips (Figshare) and the Eye Diseases Classification zip (Mendeley) with no resume, to avoid the earlier corruption.", "All three completed."],
    ["28", "Verified and extracted round 2", "Keratitis: MD5 of both zips matches. Eye Diseases Classification: SHA-256 of all 2,300 files matches. Extracted with a path-safety check; did not run the 2 notebooks inside.", "Part H1."],
    ["29", "Compared counts with the description", "Folder counts (ZEH 944 files) did not match the described 475 images, so I flagged it as unresolved instead of assuming.", "Part H3."],
    ["30", "Wrote Part H and rebuilt", "Added Part H, updated DATA_LICENSES.md and E6, regenerated the PDF.", "27-page version."],
    ["31", "Counted images", "Counted 5,703 images across four datasets for you.", "Told in chat."],
    ["32", "Searched for many more free datasets", "Searched Hugging Face, Mendeley, Figshare, Zenodo and the ESCRS public-dataset list. Found that most free sets are confocal or OCT, plus two usable ones.", "Two candidates."],
    ["33", "Downloaded round 3", "Trachoma photos (3.5 GB tar) and a 60-image cataract time series, both from Figshare, no resume.", "Both completed."],
    ["34", "Verified and extracted round 3", "MD5 of both files matches Figshare; extracted with path checks; read the trachoma label CSV.", "Part I1."],
    ["35", "Wrote Part I and rebuilt", "Added Part I with the new total (7,419) and what it would take to go much higher; updated DATA_LICENSES.md.", "29-page version."],
    *json.load(open(__file__.replace("make_pdf.py", "worklog.json"), encoding="utf-8")),
], [0.8*cm, 3.2*cm, 8.0*cm, 5*cm]))
s += [Spacer(1, 6), p("<b>Honesty note:</b> I have not implemented any part of OcuLens-AI yet - no code, models or data. "
      "This document is the planning step that comes before implementation, as you requested.")]
s.append(PageBreak())

# ---------------- PART B
s += [p("Part B - The project in plain terms", H1),
      p("<b>What it is.</b> A web/desktop application that analyses clinical photographs of the front of the eye (slit-lamp or clinic camera), finds which eye layer looks abnormal "
        "(eyelid, conjunctiva, sclera, cornea, iris, pupil, lens), says how sure it is, shows where it looked, and guides the "
        "patient to a doctor and through follow-up. Target users: eye clinics, vision centres and screening programmes where technicians capture images and ophthalmologists are scarce or remote."),
      p("<b>Why it matters.</b> Cataract and corneal infections are treatable if caught early. Existing AI mostly gives one "
        "label on clean clinical images; it does not say which layer, rarely checks its own uncertainty or explanations, and does not support follow-up."),
      p("<b>The five runtime stages</b>", H2)]
s.append(table([
    ["Stage", "What happens", "Where it runs"],
    ["1 Image intake", "A technician uploads or captures a slit-lamp / clinic-camera image; a quality check rejects blurred, glare-heavy, dark or closed-eye images and asks for a retake.", "Clinic workstation or server"],
    ["2 Segment", "Model splits the eye into regions (eyelid ... lens).", "Clinic workstation or server"],
    ["3 Classify", "CNN + ViT per region: condition and severity, plus uncertainty.", "Clinic workstation or server"],
    ["4 Explain", "Grad-CAM++ heatmap, checked against the segmentation mask.", "Clinic workstation or server"],
    ["5 Assist / follow up", "Triage, multilingual LLM assistant, doctor dashboard, change tracking at clinic visits.", "Backend (clinic server or cloud)"],
], [3*cm, 10*cm, 4*cm]))
s += [Spacer(1, 6), p("<b>Training-time only:</b> GANs and diffusion models make synthetic rare-disease images and optionally harmonize "
        "images across different cameras and hospitals. They are never used on a patient's image at runtime."),
      p("<b>Research questions:</b> RQ1 anatomy helps classification; RQ2 (revised) GAN/diffusion synthesis and cross-device harmonization improve rare-class sensitivity and generalization to a new camera or hospital; "
        "RQ3 uncertainty-based referral reduces missed cases; RQ4 anatomy-verified explanations are more faithful; "
        "RQ5 (revised) AI comparison of post-operative clinic images flags complications more consistently than visits alone."),
      p("<b>Primary metric: sensitivity</b> - a missed case costs far more than an extra referral."),
      p("<b>Out of scope (v1):</b> retina, glaucoma pressure, refractive error, any treatment or prescription advice. "
        "Posterior subcapsular cataract is easier to see on slit-lamp images than on phone photos, but still depends on image type and lighting."),
      p("What changed from the original report", H2),
      table([
        ["Aspect", "Original report", "Revised design"],
        ["Image source", "Smartphone photos", "Clinical anterior-eye images: slit-lamp or clinic camera"],
        ["Intake", "Live phone camera, MediaPipe eye tracking", "Technician upload or capture; quality gate with retake prompt"],
        ["Where models run", "On the phone, offline", "Clinic workstation / hospital server, or cloud"],
        ["Application", "Flutter or React Native", "Web app (React, or Streamlit for a quick MVP) + FastAPI"],
        ["RQ2", "Clinic-to-phone domain adaptation", "Rare-class synthesis + cross-device / cross-hospital harmonization"],
        ["RQ5", "Home monitoring after surgery", "Post-operative follow-up at clinic visits (days 1, 7, 30)"],
        ["Data", "Scarce public phone datasets", "Public slit-lamp datasets usable; own hospital data still needed for validation"],
        ["Fairness / efficiency", "Phone model, low-end phone speed", "Camera/device model, speed on clinic hardware"],
      ], [3.2*cm, 6.4*cm, 7.4*cm]),
      Spacer(1, 4),
      p("<b>Trade-off to accept:</b> without a phone, the app no longer reaches patients in villages directly. Screening needs a clinic or vision centre with an imaging device and a trained technician. "
        "In return, image quality is higher, many more public datasets apply, and the tool is simpler to build and validate."),
      PageBreak()]

# ---------------- PART C
s += [p("Part C - Each step and what to do before implementing it", H1),
      p("For every step: <b>Purpose</b> (what it is), <b>Before you implement</b> (the preparation process), "
        "<b>Decisions to make</b>, and <b>Ready when</b> (the exit check). Do not start coding a step until its "
        "'Ready when' checklist is met.")]

def step(title, purpose, before, decisions, ready):
    blk = [p(title, H2), p("<b>Purpose.</b> " + purpose), p("Before you implement", H3), bullets(before),
           p("Decisions to make", H3), bullets(decisions), p("Ready when", H3), bullets(ready)]
    return blk

s += [p("Step 0 - Foundations (not numbered in the report, but required first)", H2),
      p("<b>Purpose.</b> Settle the things every later step depends on."),
      bullets([
        "<b>Literature review</b> (PubMed, IEEE Xplore, Google Scholar, arXiv): confirm which novelty claims are still open and list the closest prior work.",
        "<b>Clinical partner:</b> sign up an eye hospital or medical college and name the clinical advisor (ophthalmologist).",
        "<b>Ethics approval:</b> submit to an institutional ethics committee; prepare consent forms. Image data is personal data under the DPDP Act 2023.",
        "<b>Regulatory check:</b> ask a regulatory expert early whether the software counts as a medical device needing CDSCO approval.",
        "<b>Environment:</b> GPU access (local or cloud), PyTorch/timm/MONAI, experiment tracking (W&amp;B or MLflow), a shared repository with version control, and a data-versioning plan.",
        "<b>Write the label taxonomy and success targets</b> (e.g., target sensitivity) so models are judged against fixed goals."]),
      Spacer(1, 4)]

s += step("Step 1 - Data collection and labeling",
  "Build the datasets everything else learns from: public data for pre-training and clinical anterior-eye images (slit-lamp or clinic camera) from your hospital partner, with labels and masks.",
  ["Shortlist public datasets (ODIR-5K, Kaggle eye sets); record each one's license and image type - many are fundus images, which are not anterior-eye and may not suit this app.",
   "Write the <b>imaging protocol</b>: which slit-lamp / camera models, magnification, diffuse vs. slit illumination, fluorescein or not, both eyes, range of ages, skin tones, iris colors.",
   "Start with the public slit-lamp datasets (see Part E6): they already match the image type, unlike fundus sets.",
   "Write the <b>labeling guideline</b> with the clinical advisor: Region -> Condition -> Severity, LOCS III-style cataract grades, and how to draw masks.",
   "Choose an annotation tool (for example CVAT or Label Studio) and set up de-identified file naming.",
   "Plan labeling: at least two ophthalmologists per image, a third to resolve disagreements, Cohen's kappa to measure agreement.",
   "Define the <b>patient-level split</b> rule now so the same patient never appears in train and test."],
  ["How many images per class are realistic? (rare classes will need Step 3.)", "Which public datasets are usable at all?", "Annotation budget: image-level for all, pixel masks for a subset?"],
  ["Ethics approval and consent in hand.", "Guideline pilot-tested on about 50 images with acceptable kappa.", "Patient-level split script written and tested."])

s += step("Step 2 - Image quality assessment and preprocessing",
  "Reject unusable images at intake and standardize the usable ones. Light reflections on the cornea can look like a cataract, so handling them matters.",
  ["Collect examples of bad images (blur, glare, closed eye, dark) and label them good/bad - these come from Step 1 captures.",
   "Decide the rule thresholds (Laplacian variance for blur, glare area, brightness) and the small CNN that backs them up.",
   "Choose how to find the eye region: slit-lamp images are close-ups, so a simple detector or the segmentation model itself can crop it; test on sample images.",
   "Choose preprocessing: CLAHE, color-constancy, specular-reflection removal, final resize and normalization.",
   "Write the technician prompts (for example 'refocus', 'reduce glare', 'eye closed - retake') in the languages used at the clinic."],
  ["Reject threshold vs. retake burden for busy clinic staff.", "Fixed crop size for all downstream models."],
  ["Quality classifier reaches the rejection accuracy you set.", "Preprocessing pipeline runs identically in training and in the deployed service (same code and library versions)."])

s += step("Step 3 - GAN and diffusion models (augmentation and domain adaptation)",
  "Create synthetic images of rare conditions (StyleGAN2-ADA or conditional diffusion) and, optionally, harmonize images across cameras and hospitals (CycleGAN-style translation) so a model trained at one site works at another. Used only at training time.",
  ["Wait until Step 1 gives a real base set; generative models trained on too little data memorize or invent wrong features.",
   "List which classes are rare (for example corneal ulcer, advanced cataract) and how many images each needs.",
   "Set up the validation plan <b>before</b> generating: FID, a visual Turing test with ophthalmologists, TSTR (train on synthetic, test on real).",
   "Reserve the real-only test set and lock it. <b>Rule: the test set contains only real images.</b>",
   "If you plan cross-device harmonization, collect unpaired images from at least two different cameras or hospitals."],
  ["GAN vs. diffusion - the report treats the comparison as a result, so plan to train both.", "How much synthetic data to mix in (ablate several ratios)."],
  ["Test set frozen and documented.", "Expert-review protocol for synthetic images agreed.", "Baseline classifier without synthetic data already trained (to measure gain)."])

s += step("Step 4 - Segmentation of eye layers",
  "Produce masks for eyelid, conjunctiva/sclera, cornea/iris, pupil, and lesions. This is the anatomy backbone of the project (RQ1, RQ4).",
  ["You need pixel-level masks from Step 1; confirm the mask class list and annotation quality (second reader on a sample).",
   "Pick a baseline (U-Net) and the comparison models (Attention U-Net, nnU-Net, TransUNet, fine-tuned SAM/MedSAM).",
   "Define the loss (Dice + cross-entropy) and metrics (Dice, IoU, HD95) and the evaluation split.",
   "Check model size and speed targets now, so the model runs quickly on a clinic workstation (CPU only if no GPU)."],
  ["Which model gives the best accuracy at the speed clinic hardware allows?"],
  ["Masks reviewed by the clinician.", "Baseline U-Net trained and scored, so other models have a number to beat."])

s += step("Step 5 - Region-aware classification and severity grading",
  "Predict condition, severity and affected region using the image plus segmentation output.",
  ["Segmentation (Step 4) must be usable first.",
   "Plan three variants to compare: A) masks as extra input channels, B) per-region crops, C) multi-task heads (condition, severity, region).",
   "Choose backbones to compare: EfficientNet-B3/B4, ConvNeXt, ViT/Swin, hybrid CNN+ViT.",
   "Plan imbalance handling (focal loss or class weights) and augmentation.",
   "Prepare the <b>image-only baseline</b> - RQ1 needs it for comparison."],
  ["Which option (A/B/C) wins on sensitivity and AUROC?", "Calibration method: temperature scaling on a held-out validation set."],
  ["Baseline sensitivity/AUROC recorded.", "Validation set separate from both train and test."])

s += step("Step 6 - Uncertainty estimation",
  "Know when the model is unsure and refer those cases instead of guessing (RQ3). The app never reports 'normal' for uncertain cases.",
  ["Needs trained, calibrated classifiers from Step 5.",
   "Decide the method: deep ensemble of about five models or MC dropout; plus conformal prediction (for example 95 percent coverage).",
   "Set a calibration set for conformal thresholds, disjoint from train and test.",
   "Agree with clinicians on an acceptable referral rate and the rule for retake vs. see-a-doctor."],
  ["Trade-off: missed-case rate vs. referral load."],
  ["ECE measured before calibration.", "Referral-rate budget agreed."])

s += step("Step 7 - Explainability",
  "Show where the model looked and verify it looked at the correct anatomical layer (RQ4).",
  ["Needs the trained classifier and segmentation masks.",
   "Pick methods to compare: Grad-CAM, Grad-CAM++, Score-CAM, Integrated Gradients, attention rollout (for transformers).",
   "Define the <b>attention-in-region ratio</b> and the threshold below which a result is flagged unreliable.",
   "Plan counterfactuals (using Step 3 generators) and TCAV concepts (lens opacity, redness, corneal haze) - these need concept example sets.",
   "Prepare a doctor-rating form to measure trust."],
  ["Which explanation method is shown by default."],
  ["Metrics defined: pointing game, attention-in-region, deletion/insertion AUC.", "Doctors available for ratings."])

s += step("Step 8 - Clinical decision engine",
  "Combine image findings with a symptom questionnaire to assign Routine, Soon or Urgent triage. Safety rules override the AI.",
  ["Write the questionnaire with the clinical advisor (age, blurred vision, pain, discharge, diabetes, recent eye surgery).",
   "Write the rule table: finding + symptoms -> triage level, and the override rules (for example pain plus sudden vision loss is always urgent).",
   "Decide how a symptom can overturn a 'normal' image result."],
  ["Time windows per level (for example urgent = within 24 hours)."],
  ["Rules signed off in writing by the ophthalmologist.", "Unit tests drafted for every rule."])

s += step("Step 9 - Grounded LLM assistant",
  "Explain results in simple, multilingual language, answer questions, produce a doctor report. It never diagnoses from the image.",
  ["Define the <b>structured findings schema</b> the LLM receives (region, finding, severity, confidence, uncertainty, triage, attention score).",
   "Collect trusted sources for RAG: ophthalmology guidelines, national blindness-control material; check their licenses.",
   "Write guardrails: 'possible signs of' wording, immediate escalation for emergencies, no medication dosing.",
   "Choose model route: API model (fast to build) or open model (Llama/Qwen/Mistral + LoRA) for privacy/offline use.",
   "Pick languages and get translations reviewed by native speakers.",
   "Build a test set of questions, including unsafe ones, for doctor review."],
  ["API vs. open model.", "Which regional languages first."],
  ["Schema frozen.", "Safety test set exists with expected behaviors."])

s += step("Step 10 - Longitudinal follow-up",
  "Track the eye over time: rescan schedule, change detection (progressed, stable, improved), progression risk, and post-cataract-surgery follow-up at clinic visits (RQ5).",
  ["Needs repeat scans from the same patients - plan the data collection and consent for repeat visits.",
   "Define schedules (for example every 3 months for early cataract; days 1, 7 and 30 after surgery).",
   "Plan image alignment and the Siamese change-detection network and its labels.",
   "Define post-surgery warning signs (redness, cloudiness, discharge, pain, vision drop) and the alert path to the surgeon.",
   "Design the pilot study for RQ5, including a comparison against scheduled visits alone."],
  ["Who receives alerts and how fast they must respond."],
  ["Longitudinal consent obtained.", "Pilot protocol approved by the ethics committee."])

s += step("Step 11 - Doctor dashboard and continuous learning",
  "Let doctors review flagged cases and correct the AI; corrections become training data (active learning). Federated learning is a later extension.",
  ["Define dashboard screens and roles (who may see which patient).",
   "Define the correction record format and how corrections are stored and versioned.",
   "Decide the active-learning rule (least-sure images first) and retraining approval process so models are not changed without validation."],
  ["Federated learning now or later (recommended: later)."],
  ["Access control and audit-log design done.", "Retraining policy written."])

s += step("Step 12 - Deployment",
  "Package the models behind a service (PyTorch or ONNX Runtime) with a web application, hosted on a hospital-local server or in the cloud; FastAPI + PostgreSQL for records, LLM assistant, dashboard and follow-up.",
  ["Pick the web front-end (React, or Streamlit for a quick MVP) and decide hospital-local server vs. cloud hosting.",
   "Test inference speed early on the target clinic machine (CPU only vs. GPU); export to ONNX if useful and confirm accuracy is unchanged.",
   "Design the database, API, and encryption in transit and at rest, consent management and audit logs.",
   "Decide whether to link with ABHA; confirm requirements first."],
  ["Latency budget per image; hospital-local vs. cloud hosting."],
  ["Service meets the latency budget with unchanged accuracy.", "Security and privacy checklist complete."])

s += [p("Evaluation and validation (before any claims)", H2),
      bullets([
        "Fix the metrics per module up front (see report Section 8): sensitivity first, plus specificity, AUROC, AUPRC, F1, kappa, ECE, FID/TSTR, fairness by age/sex/skin tone/iris color/imaging device, and efficiency.",
        "Plan the ablation ladder: image-only -> + masks (RQ1) -> + synthetic data -> + CycleGAN (RQ2) -> + quality filter -> + uncertainty referral (RQ3).",
        "Validate in stages: internal test, external hospital with different imaging devices, then a prospective pilot examined by an ophthalmologist. Follow TRIPOD+AI and CLAIM reporting guidelines."]),
      PageBreak()]

# ---------------- PART D
s += [p("Part D - Recommended build order", H1),
      p("The report's timeline is 8-10 months for five people, with a 2-3 month minimum viable version. A sensible order:")]
s.append(table([
    ["When", "Work", "Notes"],
    ["Month 1", "Step 0: literature review, hospital partner, ethics, regulatory check", "Nothing else can legally start without approvals."],
    ["Months 2-3", "Steps 1-2: data, labeling, quality check", "MVP can start here with public data while approvals proceed."],
    ["Months 3-4", "Step 3: GAN / diffusion (+ cross-device harmonization)", "Only after baseline and locked real test set."],
    ["Months 4-5", "Step 4: segmentation", ""],
    ["Months 5-6", "Steps 5-6: classification, uncertainty, ablations", "Answers RQ1-RQ3."],
    ["Months 6-7", "Steps 7 and 9: explainability, LLM assistant", "Answers RQ4."],
    ["Months 7-8", "Steps 8, 10, 11, 12: decision engine, follow-up, dashboard, web app", "RQ5 needs the pilot."],
    ["Months 8-10", "External validation, pilot camp, paper writing", ""],
], [2.6*cm, 8*cm, 6.4*cm]))
s += [Spacer(1, 8),
      p("<b>Minimum viable version (2-3 months):</b> quality check, segmentation, cataract classification, Grad-CAM and a basic LLM explanation. "
        "GAN, uncertainty and follow-up are research extensions."),
      p("<b>Suggested next actions</b>", H2),
      bullets(["Decide whether to start with the MVP on public data or wait for hospital data.",
               "Confirm team size and who owns each role (CV/ML, generative AI, web front-end, backend/LLM, clinical advisor).",
               "Pick the Python/PyTorch environment and repository layout so implementation can begin with Step 1 and Step 2."]),
      PageBreak()]

exec(open(__file__.replace("make_pdf.py", "extra_parts.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_g.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_h.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_i.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_j.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_k2.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_sweep.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_k4.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_k5.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_k6.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_eval.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_ci.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_fail.py"), encoding="utf-8").read())
exec(open(__file__.replace("make_pdf.py", "extra_l.py"), encoding="utf-8").read())

s += [Spacer(1, 10), p("<i>Status on 23 Nov 2026 - capstone prototype complete: six datasets downloaded and verified (Parts G-I); "
      "code for all 12 method steps built and tested (48 tests, dry run passed - Parts J and L); all 11 models trained for 50 epochs "
      "in parallel across the team's GPU accounts (Part K2); a full evaluation - calibration, conformal coverage, referral and "
      "subgroup fairness - in Part M; and a live Streamlit demo portal (portal/app.py, run with run_portal.bat). The results are "
      "first baselines on public data, not clinical claims; clinical validation (ethics, hospital data, prospective study) is the "
      "documented next phase.</i>")]

doc =SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
                        title="OcuLens-AI Step Log and Pre-Implementation Guide")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
print("ok")
