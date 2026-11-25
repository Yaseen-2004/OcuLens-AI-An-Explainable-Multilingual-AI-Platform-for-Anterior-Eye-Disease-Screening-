const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("C:/Users/USER/.claude/skills/synced/aca801c7-97b4-437c-ab8d-624127824cd5_3f1862fb-3a45-4828-b029-3eff756ef817/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || "OcuLens-AI_Capstone.pptx";
const IMG = (n) => path.join(__dirname, "img", n);

// ---------------------------------------------------------------- theme
const HEX = {
  dk1: "1B2A30", lt1: "FFFFFF", dk2: "0B2E3A", lt2: "E8F3F2",
  accent1: "0F7C80", accent2: "E8A33D", accent3: "C8553D", accent4: "5B8C5A", accent5: "6C5B9E", accent6: "8AA6A3",
  hlink: "0F7C80", folHlink: "6C5B9E",
};
const THEME = { name: "OcuLens Iris", headFontFace: "Cambria", bodyFontFace: "Calibri", colors: HEX };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "OcuLens-AI - Capstone Project";
pres.author = "Syed Mohammed Yaseen, Mohammed Ayaan, Arfath Khan";
pres.subject = "Anatomy-aware, explainable anterior eye disease screening";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------------------------------------------------------------- icons
async function icon(Comp, color = "FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.dk2 },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontFace: "Cambria",
      fontSize: 32, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "OcuLens-AI  |  Capstone Project 2026", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10,
      color: C.accent6, fontFace: "Calibri", margin: 0, isTextBox: true } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, fontFace: "Calibri", align: "right" },
});

let objN = 0;
const oname = (s) => `${s}_${++objN}`;

function circleIcon(slide, data, x, y, d, fill) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: oname("iconbg") });
  const pad = d * 0.25;
  slide.addImage({ data, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: oname("icon") });
}

function card(slide, x, y, w, h, fill = HEX.lt2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { color: fill }, objectName: oname("card") });
}

function caption(slide, text, x, y, w, opts = {}) {
  slide.addText(text, { x, y, w, h: 0.3, fontSize: 11, color: "5B6B70", italic: true, margin: 0, isTextBox: true,
    objectName: oname("caption"), ...opts });
}

(async () => {
  const I = {
    eye: await icon(fa.FaEye), camera: await icon(fa.FaCameraRetro), layers: await icon(fa.FaLayerGroup),
    brain: await icon(fa.FaBrain), search: await icon(fa.FaSearchPlus), chat: await icon(fa.FaComments),
    db: await icon(fa.FaDatabase), chart: await icon(fa.FaChartLine), shield: await icon(fa.FaShieldAlt),
    doctor: await icon(fa.FaUserMd), calendar: await icon(fa.FaCalendarCheck), flask: await icon(fa.FaFlask),
    robot: await icon(fa.FaRobot), bullseye: await icon(fa.FaBullseye), clinic: await icon(fa.FaClinicMedical),
    hospital: await icon(fa.FaHospital), users: await icon(fa.FaUsers), exclam: await icon(fa.FaExclamationTriangle),
    history: await icon(fa.FaHistory), server: await icon(fa.FaServer), code: await icon(fa.FaCode),
    check: await icon(fa.FaCheckCircle), question: await icon(fa.FaQuestionCircle), lang: await icon(fa.FaLanguage),
  };

  // ================================================================ 1. Title
  pres.addSection({ title: "Overview" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Overview" });
  s.addText("CAPSTONE PROJECT 2026", { x: 0.7, y: 0.9, w: 6.5, h: 0.4, fontSize: 14, bold: true, color: HEX.accent2,
    charSpacing: 4, margin: 0, isTextBox: true, objectName: "kicker" });
  s.addText("OcuLens-AI", { x: 0.7, y: 1.4, w: 7, h: 1.2, fontFace: "Cambria", fontSize: 60, bold: true, color: "FFFFFF",
    margin: 0, isTextBox: true, objectName: "title" });
  s.addText("Anatomy-aware, explainable screening of anterior eye disease from clinical images, with a grounded AI assistant and follow-up",
    { x: 0.7, y: 2.7, w: 6.6, h: 1.1, fontSize: 18, color: "CFE3E1", margin: 0, isTextBox: true, objectName: "subtitle" });
  s.addText("TEAM", { x: 0.7, y: 4.35, w: 3, h: 0.35, fontSize: 13, bold: true, color: HEX.accent2, charSpacing: 4,
    margin: 0, isTextBox: true, objectName: "teamlabel" });
  s.addText([
    { text: "Syed Mohammed Yaseen", options: { breakLine: true } },
    { text: "Mohammed Ayaan", options: { breakLine: true } },
    { text: "Arfath Khan" },
  ], { x: 0.7, y: 4.75, w: 6, h: 1.4, fontSize: 20, color: "FFFFFF", paraSpaceAfter: 6, margin: 0, isTextBox: true, objectName: "team" });
  // iris motif: three circular eye images
  s.addImage({ path: IMG("sq_ker_FK.jpg"), x: 8.3, y: 0.8, w: 3.6, h: 3.6, rounding: true, objectName: "img_eye_large",
    altText: "Slit-lamp photograph of an eye with a corneal infection" });
  s.addImage({ path: IMG("sq_sus_overlay.jpg"), x: 7.6, y: 4.1, w: 2.2, h: 2.2, rounding: true, objectName: "img_eye_ulcer",
    altText: "Fluorescein-stained cornea with the ulcer outlined" });
  s.addImage({ path: IMG("sq_ker_BK.jpg"), x: 10.3, y: 4.5, w: 2.0, h: 2.0, rounding: true, objectName: "img_eye_small",
    altText: "Slit-lamp photograph of an eye" });
  s.addNotes("Introduce the team: Syed Mohammed Yaseen, Mohammed Ayaan and Arfath Khan. OcuLens-AI screens clinical photographs of the front of the eye, shows which eye layer looks abnormal, says how sure it is, and guides the patient to a doctor. It is a screening and decision-support tool, not a diagnosis.");

  // ================================================================ 2. Agenda
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  s.addText("Agenda", { placeholder: "title" });
  const agenda = ["Introduction", "Main idea", "Proposed plan", "Datasets", "Upcoming methodologies", "System architecture",
    "Dataset gallery", "Triage and patient safety", "Results & evaluation", "Live demo & next steps"];
  agenda.forEach((t, i) => {
    const col = i < 5 ? 0 : 1, row = i % 5;
    const x = 0.8 + col * 6.2, y = 1.55 + row * 1.0;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.65, h: 0.65, fill: { color: col ? HEX.accent2 : HEX.accent1 },
      line: { color: col ? HEX.accent2 : HEX.accent1 }, objectName: oname("num") });
    s.addText(String(i + 1).padStart(2, "0"), { x, y, w: 0.65, h: 0.65, fontSize: 16, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: oname("numtxt") });
    s.addText(t, { x: x + 0.9, y, w: 4.8, h: 0.65, fontSize: 20, color: C.text1, valign: "middle", margin: 0,
      isTextBox: true, objectName: oname("agenda") });
  });
  s.addNotes("Walk through the ten topics. Slides 3 to 7 cover the problem, idea, plan, data and methods; slides 8 to 12 add architecture, sample images, safety design, progress and next steps.");

  // ================================================================ 3. Introduction
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  s.addText("Introduction: why eye screening needs help", { placeholder: "title" });
  const probs = [
    [I.eye, "Treatable blindness found late", "Cataract and corneal infection are treatable, but many patients reach a specialist only after vision is badly affected."],
    [I.hospital, "Specialists are scarce", "Eye doctors are concentrated in cities; vision centres often have imaging but no ophthalmologist on site."],
    [I.exclam, "Infections are emergencies", "A corneal ulcer can damage sight within days, and an urgent red eye is hard to tell from a minor one."],
    [I.question, "Today's AI falls short", "Most models give one label on one image, without saying where, how sure, or what to do next."],
  ];
  probs.forEach(([ic, h, b], i) => {
    const y = 1.45 + i * 1.32;
    circleIcon(s, ic, 0.7, y + 0.05, 0.75, i === 2 ? HEX.accent3 : HEX.accent1);
    s.addText(h, { x: 1.7, y, w: 6.3, h: 0.42, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("h") });
    s.addText(b, { x: 1.7, y: y + 0.42, w: 6.3, h: 0.75, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: oname("b") });
  });
  s.addImage({ path: IMG("sq_ker_HSK.jpg"), x: 8.75, y: 1.45, w: 3.9, h: 3.9, rounding: true, objectName: "img_intro",
    altText: "Cobalt-blue slit-lamp image with fluorescein staining of a corneal lesion" });
  caption(s, "Herpes simplex keratitis under cobalt-blue light (Infectious Keratitis dataset, CC BY 4.0)", 8.5, 5.55, 4.4, { h: 0.6 });
  s.addNotes("The problem is not that these diseases are untreatable; it is that patients are identified late and followed up poorly. Existing AI work mostly answers 'is a disease present?' on clean images. We want to answer where it is, how sure we are, and what happens next.");

  // ================================================================ 4. Main idea
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  s.addText("Main idea: where is it, how sure are we, what next?", { placeholder: "title" });
  const stages = [
    [I.camera, "Capture + quality", "Technician uploads a slit-lamp or clinic image; blur, glare and exposure checks ask for a retake"],
    [I.layers, "Segment layers", "Separate eyelid, conjunctiva, sclera, cornea, iris, pupil and lens"],
    [I.brain, "Classify + uncertainty", "Condition and severity per layer, calibrated, with a conformal prediction set"],
    [I.search, "Explain", "Grad-CAM++ heatmap checked against the anatomy mask"],
    [I.chat, "Triage + assist", "Safety rules, routine / soon / urgent, multilingual explanation"],
  ];
  stages.forEach(([ic, h, b], i) => {
    const x = 0.6 + i * 2.5;
    card(s, x, 1.6, 2.25, 3.35);
    circleIcon(s, ic, x + 0.73, 1.85, 0.8, i % 2 ? HEX.accent2 : HEX.accent1);
    s.addText(`${i + 1}. ${h}`, { x: x + 0.15, y: 2.8, w: 1.95, h: 0.75, fontSize: 16, bold: true, color: C.text2,
      align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: oname("stage") });
    s.addText(b, { x: x + 0.15, y: 3.6, w: 1.95, h: 1.8, fontSize: 13, color: C.text1, align: "center", valign: "top",
      margin: 0, isTextBox: true, objectName: oname("stagebody") });
    if (i < 4) s.addShape(pres.shapes.CHEVRON, { x: x + 2.29, y: 3.38, w: 0.17, h: 0.36,
      fill: { color: HEX.accent6 }, line: { color: HEX.accent6 }, objectName: oname("arrow") });
  });
  s.addText("Novelty: layer-wise diagnosis, honest uncertainty with referral, explanations verified against anatomy, and an assistant that only explains verified findings.",
    { x: 0.6, y: 5.3, w: 12.1, h: 0.8, fontSize: 17, italic: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "novelty" });
  s.addNotes("Five runtime stages. The key design choice is that every step can say 'I am not sure' and refer the patient instead of guessing, and the explanation is checked against the eye layer the model claims to be looking at.");

  // ================================================================ 5. Proposed plan
  pres.addSection({ title: "Plan and data" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Plan and data" });
  s.addText("Proposed plan: 10 months", { placeholder: "title" });
  const phases = [
    ["M1", "Literature review, hospital partner, ethics"],
    ["M2-3", "Data, labeling protocol, quality check"],
    ["M3-4", "GAN / diffusion synthesis"],
    ["M4-5", "Segmentation of eye layers"],
    ["M5-6", "Classification, uncertainty, ablations"],
    ["M6-7", "Explainability and AI assistant"],
    ["M7-8", "Follow-up, web app, doctor dashboard"],
    ["M8-10", "External validation, pilot, paper"],
  ];
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 2.55, w: 11.5, h: 0, line: { color: HEX.accent6, width: 3 }, objectName: "timeline" });
  phases.forEach(([m, t], i) => {
    const x = 0.6 + i * 1.5;
    const done = i < 2;
    s.addShape(pres.shapes.OVAL, { x: x + 0.38, y: 2.33, w: 0.45, h: 0.45, fill: { color: done ? HEX.accent2 : HEX.accent1 },
      line: { color: "FFFFFF", width: 2 }, objectName: oname("dot") });
    s.addText(m, { x, y: 1.7, w: 1.25, h: 0.45, fontSize: 16, bold: true, color: C.text2, align: "center", margin: 0,
      isTextBox: true, objectName: oname("month") });
    s.addText(t, { x: x - 0.05, y: 2.95, w: 1.35, h: 1.3, fontSize: 13, color: C.text1, align: "center", valign: "top",
      margin: 0, isTextBox: true, objectName: oname("phase") });
  });
  card(s, 0.6, 4.65, 12.1, 1.75);
  circleIcon(s, I.bullseye, 0.85, 5.08, 0.9, HEX.accent2);
  s.addText([
    { text: "Where we are: ", options: { bold: true, color: C.accent3 } },
    { text: "code for all 12 method steps is written and tested (37 tests), 6 public datasets are collected, and GPU training is set up; model training is next. " },
    { text: "Minimum viable version (months 1-3): ", options: { bold: true, color: C.text2 } },
    { text: "quality check, segmentation, classification, Grad-CAM and a basic assistant." },
  ], { x: 2.0, y: 4.85, w: 10.5, h: 1.35, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "status" });
  s.addNotes("Eight phases over ten months, team of three plus a clinical advisor. Amber dots mark phases where work has started. The biggest schedule risk is ethics approval and the hospital partnership in month 1, because own-data collection depends on them.");

  // ================================================================ 6. Datasets
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Plan and data" });
  s.addText("Datasets collected", { placeholder: "title" });
  const hdr = { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 13 };
  const rows = [
    ["Dataset", "Images", "Labels", "Used for", "Licence"],
    ["Infectious Keratitis (2 hospitals)", "1,373", "Bacterial, fungal, herpes, other", "Cornea infection classifier", "CC BY 4.0"],
    ["SUSTech-SYSU corneal ulcer", "712", "Ulcer pattern, grade; cornea + ulcer masks", "Segmentation, grading", "CC0"],
    ["Nuclear Cataract Database", "1,320", "None in download (grades missing)", "Lens images, pre-training", "CC BY 4.0"],
    ["Trachoma conjunctival photos", "1,656", "TF / TI trachoma signs", "Conjunctiva / eyelid", "GPL 3.0+ (check)"],
    ["Eye Diseases Classification (web)", "2,298", "Cataract, conjunctivitis, uveitis, eyelid, normal", "Prototype only", "CC BY 4.0"],
    ["Slit-lamp cataract time series", "60", "10 patients x 6 visits", "Follow-up module", "CC BY 4.0"],
  ].map((r, i) => r.map((c) => (i === 0 ? { text: c, options: hdr } : { text: c, options: { fontSize: 13, color: HEX.dk1 } })));
  s.addTable(rows, { x: 0.6, y: 1.45, w: 9.0, colW: [2.6, 0.9, 2.4, 1.85, 1.25], border: { type: "solid", color: "D5E3E2", pt: 0.75 },
    fill: { color: "FFFFFF" }, rowH: 0.52, valign: "middle", margin: 0.06, objectName: "datasets_table" });
  card(s, 0.6, 5.4, 9.0, 1.2);
  circleIcon(s, I.shield, 0.85, 5.6, 0.8, HEX.accent1);
  s.addText("Data rules: split by patient, so no patient is in both training and test; the test set holds real images only; the web-sourced set is never used for testing.",
    { x: 1.9, y: 5.45, w: 7.5, h: 1.1, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "data_rules" });
  card(s, 9.95, 1.45, 2.75, 2.15, HEX.dk2);
  s.addText("7,419", { x: 9.95, y: 1.6, w: 2.75, h: 1.0, fontSize: 50, bold: true, color: HEX.accent2, align: "center",
    margin: 0, isTextBox: true, objectName: "stat_images" });
  s.addText("images, 6 datasets, all hashes verified", { x: 10.1, y: 2.6, w: 2.45, h: 0.85, fontSize: 14, color: "FFFFFF",
    align: "center", margin: 0, isTextBox: true, objectName: "stat_label" });
  ["sq_ker_FK.jpg", "sq_nuc.jpg", "sq_tra_tf.jpg"].forEach((f, i) => {
    s.addImage({ path: IMG(f), x: 10.0 + (i % 3) * 0.92, y: 3.95, w: 0.82, h: 0.82, rounding: true, objectName: oname("thumb"),
      altText: "Sample dataset image" });
  });
  caption(s, "Keratitis, nuclear cataract, trachoma", 9.95, 4.85, 2.75, { align: "center" });
  card(s, 9.95, 5.3, 2.75, 1.3);
  s.addText("Requested next: CatScreen (18,640 slit-lamp images, India), SLID, EyeHealer, own hospital data",
    { x: 10.1, y: 5.35, w: 2.45, h: 1.2, fontSize: 12, color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: "next_data" });
  s.addNotes("All six sets are public and were checked with MD5 or SHA-256 hashes after download. Two cautions: the Nuclear Cataract download has no grade labels, and the web-sourced set is used only for prototyping, never for testing. Splits are by patient, so no patient appears in both training and test.");

  // ================================================================ 7. Upcoming methodologies
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Plan and data" });
  s.addText("Upcoming methodologies", { placeholder: "title" });
  const meth = [
    [I.flask, "GAN and diffusion synthesis", "StyleGAN2-ADA / conditional diffusion for rare classes; validated with FID, TSTR and expert review; test set stays real-only"],
    [I.layers, "Layer segmentation", "U-Net baseline, then nnU-Net, TransUNet and MedSAM; Dice + cross-entropy; Dice, IoU, HD95"],
    [I.brain, "Region-aware classifier", "EfficientNet, ConvNeXt, ViT / Swin; masks as input, region crops or multi-task heads"],
    [I.chart, "Calibrated uncertainty", "Temperature scaling, deep ensembles, conformal sets at 95 % coverage; refer instead of guessing"],
    [I.search, "Verified explanations", "Grad-CAM++, Score-CAM, Integrated Gradients; attention-in-region, pointing game, deletion AUC"],
    [I.robot, "Grounded LLM assistant", "Explains only verified findings, in Indian languages, with guardrails and a doctor report"],
  ];
  meth.forEach(([ic, h, b], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.6 + col * 4.1, y = 1.5 + row * 2.65;
    card(s, x, y, 3.85, 2.4);
    circleIcon(s, ic, x + 0.25, y + 0.25, 0.75, row ? HEX.accent2 : HEX.accent1);
    s.addText(h, { x: x + 1.15, y: y + 0.25, w: 2.55, h: 0.75, fontSize: 16, bold: true, color: C.text2, valign: "middle",
      margin: 0, isTextBox: true, objectName: oname("mh") });
    s.addText(b, { x: x + 0.25, y: y + 1.1, w: 3.4, h: 1.2, fontSize: 13, color: C.text1, valign: "top", margin: 0,
      isTextBox: true, objectName: oname("mb") });
  });
  s.addNotes("These are the research-core methods for the coming months. Each maps to a research question: segmentation helps classification (RQ1), synthesis and harmonisation help rare classes and new devices (RQ2), uncertainty-based referral reduces missed cases (RQ3), anatomy-verified explanations are more faithful (RQ4).");

  // ================================================================ 8. Architecture
  pres.addSection({ title: "Details" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("System architecture", { placeholder: "title" });
  const lanes = [
    ["Training (research)", HEX.accent5, ["Public + hospital data", "GAN / diffusion data", "Train, calibrate, lock test set"]],
    ["Inference service", HEX.accent1, ["Quality + preprocess", "Segment layers", "Classify + uncertainty", "Grad-CAM++ check"]],
    ["Backend and users", HEX.accent2, ["Triage engine", "AI assistant", "Follow-up", "Doctor dashboard"]],
  ];
  lanes.forEach(([name, color, boxes], li) => {
    const y = 1.45 + li * 1.65;
    card(s, 0.6, y, 12.1, 1.45, li === 1 ? "E3EFEF" : HEX.lt2);
    s.addText(name, { x: 0.8, y, w: 2.2, h: 1.45, fontSize: 16, bold: true, color, valign: "middle", margin: 0,
      isTextBox: true, objectName: oname("lane") });
    const bw = (9.3 - (boxes.length - 1) * 0.35) / boxes.length;
    boxes.forEach((b, bi) => {
      const x = 3.15 + bi * (bw + 0.35);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y + 0.25, w: bw, h: 0.95, rectRadius: 0.1, fill: { color: "FFFFFF" },
        line: { color, width: 1.5 }, objectName: oname("box") });
      s.addText(b, { x: x + 0.1, y: y + 0.25, w: bw - 0.2, h: 0.95, fontSize: 14, color: C.text1, align: "center",
        valign: "middle", margin: 0, isTextBox: true, objectName: oname("boxtxt") });
      if (bi < boxes.length - 1) s.addShape(pres.shapes.CHEVRON, { x: x + bw + 0.09, y: y + 0.55, w: 0.17, h: 0.35,
        fill: { color }, line: { color }, objectName: oname("arr") });
    });
  });
  caption(s, "Generative models are used only at training time. Doctor corrections flow back into retraining (active learning).", 0.6, 6.5, 12.1, { h: 0.35, fontSize: 12 });
  s.addNotes("Three layers. Research-time training produces calibrated models that run in an inference service at the clinic or on a server. The backend applies safety rules, explains results, schedules follow-up and feeds flagged cases to doctors, whose corrections become new training data.");

  // ================================================================ 9. Dataset gallery
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("Dataset gallery", { placeholder: "title" });
  const gal = [
    ["ker_BK.jpg", "Bacterial keratitis"], ["ker_FK.jpg", "Fungal keratitis"], ["ker_HSK.jpg", "Herpes keratitis (cobalt light)"],
    ["sus_overlay.jpg", "Corneal ulcer, mask outline"], ["nuc.jpg", "Nuclear cataract (slit beam)"], ["tra_tf.jpg", "Trachoma (everted eyelid)"],
  ];
  gal.forEach(([f, cap], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.6 + col * 4.1, y = 1.4 + row * 2.6;
    s.addImage({ path: IMG(f), x, y, w: 3.85, h: 2.05, sizing: { type: "cover", w: 3.85, h: 2.05 }, objectName: oname("gal"),
      altText: cap });
    s.addText(cap, { x, y: y + 2.1, w: 3.85, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true,
      objectName: oname("galcap") });
  });
  caption(s, "Sources: Infectious Keratitis Dataset (Figshare, CC BY 4.0); SUSTech-SYSU (CC0); Nuclear Cataract Database (Mendeley, CC BY 4.0); Trachoma images (Figshare).",
    0.6, 6.55, 12.1, { h: 0.35, fontSize: 10 });
  s.addNotes("Real examples from the downloaded datasets. Note the different imaging modes: white light, cobalt-blue with fluorescein, slit beam, and field photographs of the everted eyelid. The model must handle all of them, which is why image quality checks and preprocessing come first.");

  // ================================================================ 10. Triage and safety
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("Triage and patient safety", { placeholder: "title" });
  const levels = [
    ["URGENT", HEX.accent3, "Within 24 hours", "Suspected infection or ulcer; pain with sudden vision loss; pain or redness after surgery"],
    ["REFER", HEX.accent5, "Retake or see a doctor", "Model unsure (several labels plausible) or heatmap not on the expected layer - never reported as normal"],
    ["SOON", HEX.accent2, "Within weeks", "Early or moderate cataract, conjunctivitis, any symptom with no image finding"],
    ["ROUTINE", HEX.accent4, "Rescan in 6-12 months", "No significant finding and no symptoms"],
  ];
  levels.forEach(([lvl, col, when, why], i) => {
    const y = 1.45 + i * 1.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 2.0, h: 1.1, rectRadius: 0.12, fill: { color: col },
      line: { color: col }, objectName: oname("lvl") });
    s.addText([{ text: lvl, options: { bold: true, fontSize: 17, breakLine: true } }, { text: when, options: { fontSize: 12 } }],
      { x: 0.65, y, w: 1.9, h: 1.1, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: oname("lvltxt") });
    s.addText(why, { x: 2.85, y, w: 4.6, h: 1.1, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true,
      objectName: oname("why") });
  });
  card(s, 7.85, 1.45, 4.85, 5.0);
  circleIcon(s, I.shield, 8.1, 1.7, 0.8, HEX.accent1);
  s.addText("Guardrails", { x: 9.1, y: 1.7, w: 3.4, h: 0.8, fontSize: 20, bold: true, color: C.text2, valign: "middle",
    margin: 0, isTextBox: true, objectName: "guard_h" });
  s.addText([
    { text: "Safety rules from symptoms always override the AI", options: { bullet: true, breakLine: true } },
    { text: "The assistant never sees the image; it explains structured findings only", options: { bullet: true, breakLine: true } },
    { text: "Wording is \"possible signs of\", never \"you have\"", options: { bullet: true, breakLine: true } },
    { text: "No medicine names or doses", options: { bullet: true, breakLine: true } },
    { text: "Works offline with a fixed template when the AI service is unavailable", options: { bullet: true } },
  ], { x: 8.1, y: 2.7, w: 4.35, h: 3.6, fontSize: 14, color: C.text1, paraSpaceAfter: 8, valign: "top", margin: 0,
    isTextBox: true, objectName: "guard_list" });
  s.addNotes("Sensitivity matters more than specificity in screening: a missed case costs more than an extra referral. That is why uncertainty and unreliable explanations both route to REFER, and symptom-based safety rules can raise any result to URGENT. These rules are implemented and unit-tested, and still need clinician sign-off.");

  // ================================================================ 11. Work completed
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("What we delivered", { placeholder: "title" });
  const stats = [["Complete", "prototype + evaluation"], ["48", "unit tests passing"], ["11", "models trained (50 ep)"], ["Live", "demo portal"]];
  stats.forEach(([n, l], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 2.6, y = 1.5 + row * 2.0;
    card(s, x, y, 2.4, 1.8, row === 0 && col === 0 ? HEX.dk2 : HEX.lt2);
    const dark = row === 0 && col === 0;
    s.addText(n, { x, y: y + 0.2, w: 2.4, h: 0.9, fontSize: 36, bold: true, color: dark ? HEX.accent2 : HEX.accent1,
      align: "center", margin: 0, isTextBox: true, objectName: oname("statn") });
    s.addText(l, { x: x + 0.1, y: y + 1.1, w: 2.2, h: 0.55, fontSize: 14, color: dark ? "FFFFFF" : C.text1, align: "center",
      margin: 0, isTextBox: true, objectName: oname("statl") });
  });
  s.addText([
    { text: "Trained (50 epochs, 4 team GPUs in parallel): ", options: { bold: true, color: C.text2 } },
    { text: "baselines (keratitis, ulcer, trachoma), RQ1 anatomy variants, diffusion + CycleGAN augmentation, 5-model ensemble, Grad-CAM++ checks, ONNX export. " },
    { text: "Best so far: ", options: { bold: true, color: C.text2 } },
    { text: "ulcer region-crop 0.74 acc; keratitis AUROC 0.75." },
  ], { x: 0.6, y: 5.55, w: 5.0, h: 1.2, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "built" });
  s.addChart(pres.charts.BAR, [{
    name: "Estimated completion",
    labels: ["Planning + design", "Data (public)", "Quality + preprocessing", "GAN / diffusion", "Segmentation", "Classification",
             "Uncertainty + explain", "Triage + assistant", "Follow-up", "Doctor dashboard", "Web app", "Validation + pilot"],
    values: [100, 40, 75, 55, 60, 60, 65, 50, 60, 50, 35, 0],
  }], {
    x: 5.9, y: 1.4, w: 6.8, h: 5.4, barDir: "bar", chartColors: [HEX.accent1],
    showTitle: true, title: "Pipeline maturity by step (research prototype vs. clinical future work)", titleFontSize: 12, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    catAxisLabelFontSize: 11, catAxisLabelColor: HEX.dk1, catAxisLabelFontFace: "+mn-lt", catAxisOrientation: "maxMin",
    valAxisHidden: true, valAxisMaxVal: 115, valAxisMinVal: 0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 45, objectName: "progress_chart",
  });
  s.addNotes("We delivered a complete, working, evaluated research prototype: every method step coded and tested (48 tests), 6 datasets verified, 11 models trained for 50 epochs across the team's GPU accounts, a full evaluation (calibration, uncertainty, referral, fairness), and a live Streamlit demo portal. The chart shows pipeline maturity per step - the research pipeline is built end-to-end; the clinical steps (ethics, hospital data, prospective validation) are deliberately scoped as future work. All results are first baselines on public data, not clinical claims.");

  // ================================================================ 12. Evaluation
  {
    const fs = require("fs");
    const EV = "D:/Capston_Project/experiments";
    const rd = (p) => { try { return JSON.parse(fs.readFileSync(p, "utf8").replace(/\bNaN\b/g, "null")); } catch (e) { return null; } };
    const f3 = (v) => (v === null || v === undefined || Number.isNaN(v)) ? "n/a" : Number(v).toFixed(3);

    s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
    s.addText("Evaluation: calibration, referral & fairness", { placeholder: "title" });

    // headline stat cards
    const estats = [["0.91\u20130.97", "conformal coverage (target 0.95)"], ["0.047", "keratitis ECE (diffusion model)"],
                    ["0.488", "keratitis bal-acc (diffusion)"], ["+0.05", "over the 5-model ensemble"]];
    estats.forEach(([n, l], i) => {
      const x = 0.6 + (i % 2) * 3.05, y = 1.45 + Math.floor(i / 2) * 1.35;
      const dark = i === 0;
      card(s, x, y, 2.9, 1.2, dark ? HEX.dk2 : HEX.lt2);
      s.addText(n, { x, y: y + 0.12, w: 2.9, h: 0.55, fontSize: 26, bold: true, color: dark ? HEX.accent2 : HEX.accent1,
        align: "center", margin: 0, isTextBox: true, objectName: oname("estatn") });
      s.addText(l, { x: x + 0.12, y: y + 0.72, w: 2.66, h: 0.42, fontSize: 11, color: dark ? "FFFFFF" : C.text1,
        align: "center", margin: 0, isTextBox: true, objectName: oname("estatl") });
    });

    // results table (read from eval_final)
    const models = [["trachoma_image", "Trachoma"], ["ulcer_mask_input", "Ulcer mask_input"],
      ["ulcer_region_crop", "Ulcer region_crop"], ["keratitis_ensemble", "Keratitis ens.(5)"],
      ["keratitis_harmonized", "Keratitis +CycleGAN"], ["keratitis_image", "Keratitis base"]];
    const hdr = ["Model", "Bal.acc", "AUROC", "ECE"].map((t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 11 } }));
    const trows = [hdr];
    models.forEach(([fn, lab]) => {
      const d = rd(`${EV}/eval_final/eval_${fn}.json`); const o = d ? d.overall : {}; const c = d ? d.conformal : {};
      trows.push([{ text: lab, options: { fontSize: 11 } }, { text: f3(o.balanced_accuracy), options: { fontSize: 11, align: "center" } },
        { text: f3(o.auroc_macro_ovr), options: { fontSize: 11, align: "center" } }, { text: f3(o.ece), options: { fontSize: 11, align: "center" } }]);
    });
    s.addText("Test-set results (50 epochs)", { x: 0.6, y: 4.25, w: 5.9, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("evtt") });
    s.addTable(trows, { x: 0.6, y: 4.65, w: 5.9, colW: [2.6, 1.1, 1.1, 1.1], border: { type: "solid", color: "D5E3E1", pt: 0.5 },
      fill: { color: "FFFFFF" }, color: C.text1, valign: "middle", rowH: 0.3, objectName: "ev_table" });

    // calibration reliability line chart (keratitis diffusion model = deployed)
    const cal = rd(`${EV}/curves/keratitis_diffusion.json`) || rd(`${EV}/curves/keratitis_baseline.json`);
    const bins = cal ? cal.calibration : [];
    const labels = bins.map((b) => b.conf.toFixed(2));
    s.addChart(pres.charts.LINE, [
      { name: "Model (acc)", labels, values: bins.map((b) => b.acc) },
      { name: "Perfect", labels, values: bins.map((b) => b.conf) },
    ], { x: 6.8, y: 1.35, w: 6.0, h: 2.55, chartColors: [HEX.accent1, HEX.accent6], lineDataSymbol: "circle", lineSize: 2,
      showTitle: true, title: "Calibration: keratitis diffusion model (deployed)", titleFontSize: 12, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
      showLegend: true, legendPos: "b", legendFontSize: 9, catAxisLabelFontSize: 8, valAxisLabelFontSize: 8,
      valAxisMinVal: 0, valAxisMaxVal: 1, catAxisTitle: "confidence", showCatAxisTitle: true, catAxisTitleFontSize: 9, objectName: "ev_cal" });

    // referral trade-off line chart (ulcer region_crop)
    const refj = rd(`${EV}/curves/ulcer_region_crop.json`);
    const ref = refj ? refj.referral.filter((r) => r.accuracy_kept !== null) : [];
    s.addChart(pres.charts.LINE, [
      { name: "Accuracy on kept cases", labels: ref.map((r) => r.referral_rate.toFixed(2)), values: ref.map((r) => r.accuracy_kept) },
    ], { x: 6.8, y: 4.1, w: 6.0, h: 2.55, chartColors: [HEX.accent4], lineSize: 2, lineDataSymbol: "circle",
      showTitle: true, title: "Referral trade-off: ulcer region_crop", titleFontSize: 12, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
      showLegend: false, catAxisLabelFontSize: 8, valAxisLabelFontSize: 8, valAxisMinVal: 0, valAxisMaxVal: 1,
      catAxisTitle: "referral rate", showCatAxisTitle: true, catAxisTitleFontSize: 9, objectName: "ev_ref" });

    caption(s, "Fairness gaps flagged: keratitis eye L 0.39 vs R 0.35; illumination mode 1 0.44 vs mode 2 0.36. Test sets are single-site (keratitis AGEH, ulcer ZOC) - a true cross-site test needs the hospital data in next steps.", 0.6, 6.55, 12.1, { fontSize: 9 });
    s.addNotes("Evaluation beyond accuracy. Conformal prediction gives near-target 95% coverage; the deployed keratitis diffusion model is well-calibrated (ECE 0.047). The referral curve shows accuracy on kept cases rising as low-confidence cases are referred - the safety argument. Subgroup checks flag eye and illumination gaps to watch. Test sets are single-site, so cross-site validation is future work.");
  }

  // ================================================================ 12b. Final model-selection sweep
  {
    const fs = require("fs");
    const f3 = (v) => (v === null || v === undefined || Number.isNaN(v)) ? "n/a" : Number(v).toFixed(3);
    const sw = (() => { try { return JSON.parse(fs.readFileSync("D:/Capston_Project/experiments/runs/final_sweep.json", "utf8")); } catch (e) { return null; } })();

    s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
    s.addText("Choosing the keratitis model: better data beat more models", { placeholder: "title" });
    s.addText("Keratitis is the hardest task. We tried three fixes head-to-head on the same held-out test set (n=429), run in parallel on the team's own DGX GPUs.",
      { x: 0.6, y: 1.25, w: 12.1, h: 0.5, fontSize: 13, color: C.text2, margin: 0, isTextBox: true, objectName: oname("swsub") });

    const hdr = ["Configuration", "Bal.acc", "Macro F1", "AUROC", "ECE"].map((t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 12 } }));
    const trows = [hdr];
    const runs = sw ? sw.runs : [];
    runs.forEach((r) => {
      const win = /SELECTED/.test(r.label);
      const nm = r.label.replace(" [SELECTED]", "");
      const opt = { fontSize: 12, bold: win, fill: win ? { color: HEX.lt2 } : { color: "FFFFFF" }, color: win ? HEX.accent1 : C.text1 };
      trows.push([{ text: nm + (win ? "  \u2605" : ""), options: opt },
        { text: f3(r.d.balanced_accuracy), options: { ...opt, align: "center" } },
        { text: f3(r.d.macro_f1), options: { ...opt, align: "center" } },
        { text: f3(r.d.auroc), options: { ...opt, align: "center" } },
        { text: f3(r.d.ece), options: { ...opt, align: "center" } }]);
    });
    s.addTable(trows, { x: 0.6, y: 2.0, w: 8.3, colW: [3.9, 1.1, 1.1, 1.1, 1.1], border: { type: "solid", color: "D5E3E1", pt: 0.5 },
      fill: { color: "FFFFFF" }, color: C.text1, valign: "middle", rowH: 0.42, objectName: "sweep_table" });

    // takeaway cards
    const cards = [
      ["Diffusion augmentation wins", "DDPM-synthesised rare-class images lifted balanced accuracy to 0.488 and gave the best calibration (ECE 0.047)."],
      ["Beats a 10-model ensemble", "A single diffusion-trained model (0.488) beat a 10-model deep ensemble (0.451): smarter data > more models."],
      ["Higher resolution did not help", "320px input scored 0.409 - no gain over 224px on this data. An honest negative result."],
    ];
    cards.forEach(([h, b], i) => {
      const y = 4.55 + i * 0.0; const x = 0.6 + i * 4.1;
      card(s, x, 4.55, 3.9, 1.9, HEX.lt2);
      s.addText(h, { x: x + 0.15, y: 4.7, w: 3.6, h: 0.5, fontSize: 13, bold: true, color: HEX.accent1, margin: 0, isTextBox: true, objectName: oname("swch") });
      s.addText(b, { x: x + 0.15, y: 5.2, w: 3.6, h: 1.15, fontSize: 11, color: C.text1, margin: 0, isTextBox: true, objectName: oname("swcb") });
    });

    caption(s, "The portal uses the diffusion-augmented model for the prediction; the deep ensemble is kept only to measure disagreement (mutual information) as an uncertainty signal beside each call. First baselines on public, single-site data - not clinical claims.", 0.6, 6.6, 12.1, { fontSize: 9 });
    s.addNotes("This is the key result slide. After the main run we tried three ways to improve keratitis in parallel on the team GPUs. Diffusion augmentation won clearly - 0.488 balanced accuracy vs 0.438 for the old ensemble, and best calibration. It even beat a 10-model ensemble, so the story is 'better training data beat more models'. Higher resolution gave nothing. The winning model is what the live portal now runs.");
  }

  // ================================================================ 13. Evaluation rigor
  {
    const fs = require("fs");
    const EV = "D:/Capston_Project/experiments";
    const rd = (p) => { try { return JSON.parse(fs.readFileSync(p, "utf8").replace(/\bNaN\b/g, "null")); } catch (e) { return null; } };
    const fci = (d) => { if (!d || d.point == null) return "n/a"; const c = d.ci95 || []; return c.length === 2 ? `${d.point.toFixed(3)} [${c[0].toFixed(3)}, ${c[1].toFixed(3)}]` : d.point.toFixed(3); };
    s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
    s.addText("Evaluation rigor: confidence intervals & failure cases", { placeholder: "title" });
    const ci = rd(`${EV}/ci/ci.json`) || {};
    const hdr = ["Model", "Test n", "Balanced acc [95% CI]", "AUROC [95% CI]"].map((t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 11 } }));
    const trows = [hdr];
    Object.keys(ci).forEach((k) => { const r = ci[k]; trows.push([{ text: r.label || k, options: { fontSize: 11 } }, { text: String(r.n), options: { fontSize: 11, align: "center" } }, { text: fci(r.balanced_accuracy), options: { fontSize: 11 } }, { text: fci(r.auroc), options: { fontSize: 11 } }]); });
    s.addText("95% confidence intervals (1,000-sample bootstrap)", { x: 0.6, y: 1.35, w: 8, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("cih") });
    if (trows.length > 1) s.addTable(trows, { x: 0.6, y: 1.8, w: 7.4, colW: [2.6, 1.0, 2.4, 1.4], border: { type: "solid", color: "D5E3E1", pt: 0.5 }, fill: { color: "FFFFFF" }, color: C.text1, valign: "middle", rowH: 0.34, objectName: "ci_table" });
    s.addText("Overlapping intervals = difference not yet significant; wider bounds come from smaller test sets.", { x: 0.6, y: 3.7, w: 7.4, h: 0.6, fontSize: 11, italic: true, color: "5B6B70", margin: 0, isTextBox: true, objectName: oname("cin") });
    const fidx = rd(`${EV}/failures/index.json`) || [];
    const pick = {}; fidx.forEach((it) => { if (!pick[it.task]) pick[it.task] = it; });
    s.addText("Failure cases (confident mistakes · Grad-CAM++)", { x: 8.4, y: 1.35, w: 4.3, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("fh") });
    let fy = 1.8;
    ["keratitis", "ulcer_pattern", "trachoma_tf"].forEach((tk) => {
      const it = pick[tk]; if (!it) return;
      try { s.addImage({ path: `${EV}/failures/${it.file}`, x: 8.4, y: fy, w: 1.5, h: 1.15, sizing: { type: "contain", w: 1.5, h: 1.15 }, rounding: true, objectName: oname("fimg") }); } catch (e) {}
      s.addText(`${it.true} → ${it.pred}\n(${Math.round(it.conf * 100)}% conf)`, { x: 10.0, y: fy + 0.18, w: 2.7, h: 0.9, fontSize: 10, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: oname("fcap") });
      fy += 1.35;
    });
    s.addText("First baselines on public data — not clinical claims. Confident errors are exactly what the referral gate is built to catch.", { x: 0.6, y: 6.7, w: 12.1, h: 0.3, fontSize: 10, italic: true, color: "5B6B70", margin: 0, isTextBox: true, objectName: oname("rign") });
    s.addNotes("Rigour slide: we report 95% bootstrap confidence intervals, not just point metrics, and show the models' confident mistakes with Grad-CAM. Keratitis confuses visually similar infection types; trachoma has a few high-confidence flips — exactly what the referral gate catches. Overlapping CIs mean a difference is not yet significant.");
  }

  // ================================================================ 14. Live demo portal
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("Live demo: the OcuLens-AI portal", { placeholder: "title" });
  s.addText([
    { text: "A working Streamlit web portal runs the whole pipeline on a single uploaded eye image, entirely offline on CPU:", options: { breakLine: true, color: C.text1 } },
  ], { x: 0.6, y: 1.35, w: 12.1, h: 0.6, fontSize: 16, color: C.text1, margin: 0, isTextBox: true, objectName: "demo_intro" });
  const steps = [
    ["1  Quality gate", "Rejects blurred / dark / glare images and asks for a retake."],
    ["2  Cornea segmentation", "U-Net finds the cornea; explanations are checked to look there."],
    ["3  Classification", "EfficientNet-B0 predicts the condition with calibrated probabilities."],
    ["4  Confidence + referral", "Conformal prediction set; uncertain cases are flagged for review."],
    ["5  Grad-CAM++ explanation", "Shows where the model looked, overlaid on the eye."],
    ["6  Plain-language summary", "A grounded summary that only repeats verified findings."],
  ];
  steps.forEach(([h, d], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 2.1 + row * 1.5;
    card(s, x, y, 5.9, 1.35);
    s.addText(h, { x: x + 0.25, y: y + 0.12, w: 5.5, h: 0.4, fontSize: 15, bold: true, color: HEX.accent1, margin: 0, isTextBox: true, objectName: oname("dsh") });
    s.addText(d, { x: x + 0.25, y: y + 0.55, w: 5.5, h: 0.72, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, objectName: oname("dsd") });
  });
  s.addText("Also in the portal: a live evaluation dashboard (metrics, calibration & referral curves, fairness) and an About page.  Run:  python -m streamlit run portal/app.py",
    { x: 0.6, y: 6.75, w: 12.1, h: 0.3, fontSize: 11, italic: true, color: "5B6B70", margin: 0, isTextBox: true, objectName: "demo_run" });
  s.addNotes("Switch to the live portal here. Open Screening, tick the sample box (or upload an image), and walk through the six steps on screen. Then show the Evaluation dashboard tab. This is the centrepiece - a reviewer can click through the whole system.");

  // ================================================================ 14. Follow-up and next steps
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Details" });
  s.addText("Follow-up monitoring and next steps", { placeholder: "title" });
  ["tmp_0.jpg", "tmp_1.jpg", "tmp_2.jpg", "tmp_3.jpg"].forEach((f, i) => {
    const x = 0.6 + i * 1.6;
    s.addImage({ path: IMG(f), x, y: 1.5, w: 1.45, h: 1.09, objectName: oname("ts"), altText: `Visit ${i + 1} slit-lamp image` });
    s.addText(`Visit ${i + 1}`, { x, y: 2.62, w: 1.45, h: 0.3, fontSize: 12, color: C.text2, align: "center", margin: 0,
      isTextBox: true, objectName: oname("tscap") });
  });
  s.addText([
    { text: "Align each new scan to the last one, then classify the change: ", options: { breakLine: false } },
    { text: "progressed, stable or improved", options: { bold: true } },
    { text: ". Rescan dates follow the triage level; after cataract surgery the clinic reviews days 1, 7 and 30 and alerts the surgeon on warning signs." },
  ], { x: 0.6, y: 3.45, w: 6.3, h: 1.45, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "fu_text" });
  caption(s, "Same eye over six visits (slit-lamp time series, PLOS ONE 2018, CC BY 4.0)", 0.6, 3.0, 6.3);
  card(s, 7.3, 1.45, 5.4, 5.2);
  s.addText("Next steps", { x: 7.6, y: 1.65, w: 4.8, h: 0.5, fontSize: 20, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "next_h" });
  s.addText([
    { text: "Finish GPU training: keratitis, ulcer pattern, trachoma", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Train the U-Net and measure explanation quality", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Request CatScreen, SLID and EyeHealer", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Ethics approval and hospital partner", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Start GAN / diffusion experiments", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "External validation and pilot screening camp", options: { bullet: { type: "number" } } },
  ], { x: 7.6, y: 2.35, w: 4.9, h: 4.1, fontSize: 16, color: C.text1, paraSpaceAfter: 14, valign: "top", margin: 0,
    isTextBox: true, objectName: "next_list" });
  card(s, 0.6, 5.1, 6.3, 1.55, HEX.dk2);
  s.addText("Thank you - questions?", { x: 0.9, y: 5.1, w: 5.8, h: 1.55, fontFace: "Cambria", fontSize: 28, bold: true,
    color: "FFFFFF", valign: "middle", margin: 0, isTextBox: true, objectName: "thanks" });
  s.addNotes("Follow-up turns one-off screening into continuous care. Close with the next steps and invite questions.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
