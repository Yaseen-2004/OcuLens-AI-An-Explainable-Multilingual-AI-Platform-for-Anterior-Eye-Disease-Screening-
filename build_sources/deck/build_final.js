// OcuLens-AI final presentation - "slit-lamp" theme (midnight, cobalt, fluorescein), iris motif.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("C:/Users/USER/.claude/skills/synced/aca801c7-97b4-437c-ab8d-624127824cd5_3f1862fb-3a45-4828-b029-3eff756ef817/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || path.join(__dirname, "OcuLens-AI_Final_Presentation.pptx");
const IMG = (n) => path.join(__dirname, "img", n);
const EV = "D:/Capston_Project/experiments";
const rd = (p) => { try { return JSON.parse(fs.readFileSync(p, "utf8").replace(/\bNaN\b/g, "null")); } catch (e) { return null; } };

// ---------------------------------------------------------------- theme: the colours of a slit-lamp exam
const HEX = {
  dk1: "0E1A2B", lt1: "FFFFFF", dk2: "0A1A33", lt2: "EEF3FC",
  accent1: "2F6BFF",   // cobalt-blue slit-lamp light
  accent2: "C6F23B",   // fluorescein glow
  accent3: "FF6B57",   // coral - referral / alert
  accent4: "F0A93B",   // iris amber
  accent5: "19C2A9",   // aqua - ok
  accent6: "8A9BB8",   // slate - muted
  hlink: "2F6BFF", folHlink: "7E6BFF",
};
const THEME = { name: "OcuLens Slit-lamp", headFontFace: "Century Schoolbook", bodyFontFace: "Calibri", colors: HEX };
const PANEL = "13284A";      // raised panel on dark slides
const SOFT = "C9D8F5";       // secondary text on dark slides
const GRID_DARK = "24385C";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "OcuLens-AI - Capstone Project 2026";
pres.author = "Syed Mohammed Yaseen, Mohammed Ayaan, Arfath Khan";
pres.subject = "Explainable, uncertainty-aware screening of anterior-eye disease";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------------------------------------------------------------- generated artwork
function rng(seed) { let s = seed >>> 0; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }

// every eye is different: one iris colour per section
const IRIS = {
  blue: { stops: ["0A1A33", "123E8C", "1F5FD6", "0B2A66"], fib: [["5B8CFF", 0.6], ["19C2A9", 0.2], ["C6F23B", 0.12], ["F0A93B", 0.08]], rim: "2F6BFF" },
  green: { stops: ["06231F", "0E5A4E", "19A58C", "0A3B34"], fib: [["3FD8B9", 0.55], ["C6F23B", 0.2], ["8FB2FF", 0.15], ["F0A93B", 0.1]], rim: "19C2A9" },
  hazel: { stops: ["2A1506", "6B3A0F", "C77A1E", "4A2A0C"], fib: [["F0A93B", 0.5], ["E8C07A", 0.22], ["C6F23B", 0.18], ["19C2A9", 0.1]], rim: "F0A93B" },
  grey: { stops: ["0F1724", "3B4A63", "8A9BB8", "2A3548"], fib: [["C9D8F5", 0.5], ["8FB2FF", 0.3], ["C6F23B", 0.1], ["F0A93B", 0.1]], rim: "8A9BB8" },
};

function irisSVG(N = 1600, seed = 11, pal = IRIS.blue) {
  const r = rng(seed), c = N / 2, u = N / 1600;
  const P = (rad, deg) => [c + rad * u * Math.cos(deg * Math.PI / 180), c + rad * u * Math.sin(deg * Math.PI / 180)];
  let fib = "";
  const palette = pal.fib;
  for (let i = 0; i < 820; i++) {
    const a = (i / 820) * 360 + r() * 0.6;
    const r1 = 185 + r() * 25, r2 = 300 + r() * 170;
    let p = r(), col = palette[0][0];
    for (const [cc, w] of palette) { if (p < w) { col = cc; break; } p -= w; }
    const [x1, y1] = P(r1, a), [x2, y2] = P(r2, a + (r() - 0.5) * 2.5);
    fib += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#${col}" stroke-opacity="${(0.22 + r() * 0.5).toFixed(2)}" stroke-width="${((1.1 + r() * 1.6) * u).toFixed(2)}" stroke-linecap="round"/>`;
  }
  let coll = "";
  for (let d = 0; d <= 360; d += 2) { const [x, y] = P(255 + 13 * Math.sin(d * 14 * Math.PI / 180), d); coll += `${d ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`; }
  let ticks = "";
  for (let d = 0; d < 360; d += 3) {
    const long = d % 30 === 0, [x1, y1] = P(690, d), [x2, y2] = P(long ? 730 : 712, d);
    ticks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#8A9BB8" stroke-opacity="${long ? 0.75 : 0.4}" stroke-width="${(long ? 3 : 2) * u}"/>`;
  }
  const arc = (rad, a0, a1) => { const [x0, y0] = P(rad, a0), [x1, y1] = P(rad, a1); return `M${x0.toFixed(1)},${y0.toFixed(1)} A${rad * u},${rad * u} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)}`; };
  const [d0x, d0y] = P(770, -35), [d1x, d1y] = P(770, 55);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${N}" height="${N}" viewBox="0 0 ${N} ${N}">
  <defs>
    <radialGradient id="glow"><stop offset="0" stop-color="#${pal.rim}" stop-opacity="0.55"/><stop offset="0.6" stop-color="#${pal.rim}" stop-opacity="0.12"/><stop offset="1" stop-color="#${pal.rim}" stop-opacity="0"/></radialGradient>
    <radialGradient id="iris"><stop offset="0" stop-color="#${pal.stops[0]}"/><stop offset="0.38" stop-color="#${pal.stops[1]}"/><stop offset="0.72" stop-color="#${pal.stops[2]}"/><stop offset="1" stop-color="#${pal.stops[3]}"/></radialGradient>
  </defs>
  <circle cx="${c}" cy="${c}" r="${800 * u}" fill="url(#glow)"/>
  <circle cx="${c}" cy="${c}" r="${470 * u}" fill="url(#iris)"/>
  ${fib}
  <path d="${coll}Z" fill="none" stroke="#F0A93B" stroke-opacity="0.8" stroke-width="${4 * u}"/>
  <circle cx="${c}" cy="${c}" r="${476 * u}" fill="none" stroke="#0A1A33" stroke-opacity="0.9" stroke-width="${22 * u}"/>
  <circle cx="${c}" cy="${c}" r="${492 * u}" fill="none" stroke="#${pal.rim}" stroke-opacity="0.9" stroke-width="${3 * u}"/>
  <circle cx="${c}" cy="${c}" r="${180 * u}" fill="#040A16"/>
  <circle cx="${c}" cy="${c}" r="${180 * u}" fill="none" stroke="#1A2D55" stroke-width="${3 * u}"/>
  <ellipse cx="${c - 65 * u}" cy="${c - 75 * u}" rx="${38 * u}" ry="${30 * u}" fill="#FFFFFF" fill-opacity="0.9"/>
  <circle cx="${c + 60 * u}" cy="${c + 50 * u}" r="${10 * u}" fill="#FFFFFF" fill-opacity="0.55"/>
  <circle cx="${c}" cy="${c}" r="${565 * u}" fill="none" stroke="#C6F23B" stroke-opacity="0.55" stroke-width="${3 * u}" stroke-dasharray="${4 * u} ${14 * u}"/>
  <circle cx="${c}" cy="${c}" r="${635 * u}" fill="none" stroke="#8A9BB8" stroke-opacity="0.35" stroke-width="${2 * u}"/>
  ${ticks}
  <path d="${arc(770, -35, 55)}" fill="none" stroke="#C6F23B" stroke-width="${7 * u}" stroke-linecap="round"/>
  <circle cx="${d0x.toFixed(1)}" cy="${d0y.toFixed(1)}" r="${11 * u}" fill="#C6F23B"/>
  <circle cx="${d1x.toFixed(1)}" cy="${d1y.toFixed(1)}" r="${11 * u}" fill="#C6F23B"/>
</svg>`;
}

function bgDarkSVG() {
  let rings = "";
  for (let rr = 260; rr <= 1700; rr += 110) rings += `<circle cx="2250" cy="1300" r="${rr}" fill="none" stroke="#FFFFFF" stroke-opacity="${(0.055 - rr / 60000).toFixed(3)}" stroke-width="2"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1350" viewBox="0 0 2400 1350">
  <defs>
    <radialGradient id="a" cx="2050" cy="1150" r="1150" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2F6BFF" stop-opacity="0.34"/><stop offset="1" stop-color="#2F6BFF" stop-opacity="0"/></radialGradient>
    <radialGradient id="b" cx="150" cy="0" r="760" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#19C2A9" stop-opacity="0.11"/><stop offset="1" stop-color="#19C2A9" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="2400" height="1350" fill="#0A1A33"/><rect width="2400" height="1350" fill="url(#a)"/><rect width="2400" height="1350" fill="url(#b)"/>${rings}</svg>`;
}

function bgLightSVG() {
  let rings = "";
  for (let rr = 150; rr <= 950; rr += 70) rings += `<circle cx="2400" cy="0" r="${rr}" fill="none" stroke="#2F6BFF" stroke-opacity="0.055" stroke-width="2"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1350" viewBox="0 0 2400 1350"><rect width="2400" height="1350" fill="#FFFFFF"/>${rings}</svg>`;
}

// project-journey layout (inches) shared by the path artwork and the native nodes placed on it
const JOURNEY = { xs: [1.95, 4.85, 7.75, 10.65], lanes: [2.25, 3.95, 5.65], turnR: 11.75, turnL: 1.25, start: 0.85, end: 11.6 };

function journeySVG() {
  const K = 180, J = JOURNEY;
  const [y1, y2, y3] = J.lanes.map((v) => v * K), r = (y2 - y1) / 2;
  const xr = J.turnR * K, xl = J.turnL * K, x0 = J.start * K, xe = J.end * K;
  const segs = [
    [`M${x0},${y1} L${xr},${y1}`, "#19C2A9"],
    [`M${xr},${y1} A${r},${r} 0 0 1 ${xr},${y2}`, "url(#gR)"],
    [`M${xr},${y2} L${xl},${y2}`, "#2F6BFF"],
    [`M${xl},${y2} A${r},${r} 0 0 0 ${xl},${y3}`, "url(#gL)"],
    [`M${xl},${y3} L${xe},${y3}`, "url(#gE)"],
  ];
  const all = segs.map(([d]) => d).join(" ");
  const glow = segs.map(([d, c]) => `<path d="${d}" fill="none" stroke="${c}" stroke-width="24" stroke-opacity="0.35" filter="url(#blur)"/>`).join("");
  const core = segs.map(([d, c]) => `<path d="${d}" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round"/>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1350" viewBox="0 0 2400 1350">
  <defs>
    <filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="9"/></filter>
    <linearGradient id="gR" gradientUnits="userSpaceOnUse" x1="0" y1="${y1}" x2="0" y2="${y2}"><stop offset="0" stop-color="#19C2A9"/><stop offset="1" stop-color="#2F6BFF"/></linearGradient>
    <linearGradient id="gL" gradientUnits="userSpaceOnUse" x1="0" y1="${y2}" x2="0" y2="${y3}"><stop offset="0" stop-color="#2F6BFF"/><stop offset="1" stop-color="#F0A93B"/></linearGradient>
    <linearGradient id="gE" gradientUnits="userSpaceOnUse" x1="${xl}" y1="0" x2="${xe}" y2="0"><stop offset="0" stop-color="#F0A93B"/><stop offset="1" stop-color="#FF6B57"/></linearGradient>
  </defs>
  ${glow}${core}
  <path d="${all}" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="2.5" stroke-dasharray="2 20" stroke-linecap="round"/>
  <circle cx="${x0}" cy="${y1}" r="15" fill="#19C2A9"/><circle cx="${x0}" cy="${y1}" r="26" fill="none" stroke="#19C2A9" stroke-opacity="0.5" stroke-width="3"/>
  <polygon points="${xe},${y3 - 24} ${xe + 44},${y3} ${xe},${y3 + 24}" fill="#FF6B57"/>
</svg>`;
}

async function icon(Comp, color = "FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ---------------------------------------------------------------- helpers
let objN = 0;
const oname = (s) => `${s}_${++objN}`;

function kicker(slide, text, dark) {
  slide.addText(text, { x: 0.7, y: 0.32, w: 10, h: 0.3, fontSize: 12, bold: true, charSpacing: 4,
    color: dark ? C.accent2 : C.accent1, margin: 0, isTextBox: true, objectName: oname("kicker") });
}
function iconDisc(slide, data, x, y, d, fill) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: oname("disc") });
  const pad = d * 0.26;
  slide.addImage({ data, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: oname("icon") });
}
// the motif: a photo in a round "iris" frame with a thin coloured ring around it
function irisFrame(slide, img, x, y, d, ring, alt) {
  slide.addImage({ path: img, x, y, w: d, h: d, rounding: true, altText: alt, objectName: oname("iris_img") });
  const g = Math.max(0.06, d * 0.045);
  slide.addShape(pres.shapes.OVAL, { x: x - g, y: y - g, w: d + 2 * g, h: d + 2 * g, fill: { color: "FFFFFF", transparency: 100 },
    line: { color: ring, width: d > 2 ? 2.5 : 1.75 }, objectName: oname("iris_ring") });
}
function panel(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.14, fill: { color: fill }, line: { color: fill }, objectName: oname("panel") });
}
// screenshot on a soft "device" frame
function screen(slide, img, x, y, w, h, dark, alt) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.1, y: y - 0.1, w: w + 0.2, h: h + 0.2, rectRadius: 0.12,
    fill: { color: dark ? "1B3560" : "DCE5F5" }, line: { color: dark ? "1B3560" : "DCE5F5" },
    shadow: { type: "outer", color: "000000", opacity: dark ? 0.45 : 0.18, blur: 10, offset: 4, angle: 90 }, objectName: oname("frame") });
  slide.addImage({ path: img, x, y, w, h, altText: alt, objectName: oname("shot") });
}
function note(slide, text, x, y, w, h, dark, opts = {}) {
  slide.addText(text, { x, y, w, h, fontSize: 12, italic: true, color: dark ? SOFT : "51617A", margin: 0, valign: "top",
    isTextBox: true, objectName: oname("note"), ...opts });
}
const f3 = (v) => (v === null || v === undefined || Number.isNaN(v)) ? "n/a" : Number(v).toFixed(3);
const chartText = (dark) => ({
  catAxisLabelColor: dark ? SOFT : "33425C", valAxisLabelColor: dark ? SOFT : "33425C",
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  dataLabelColor: dark ? "FFFFFF" : HEX.dk1, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12,
  titleColor: dark ? "FFFFFF" : HEX.dk2, titleFontFace: "+mn-lt", titleFontSize: 14,
  legendFontFace: "+mn-lt", legendFontSize: 12, legendColor: dark ? SOFT : "33425C",
});

(async () => {
  // artwork files
  await sharp(Buffer.from(bgDarkSVG())).png().toFile(IMG("bg_dark.png"));
  await sharp(Buffer.from(bgLightSVG())).png().toFile(IMG("bg_light.png"));
  await sharp(Buffer.from(irisSVG(1600, 11))).png().toFile(IMG("hero_iris.png"));
  for (const [nm, seed] of [["green", 23], ["hazel", 37], ["grey", 41]]) {
    await sharp(Buffer.from(irisSVG(1600, seed, IRIS[nm]))).png().toFile(IMG(`iris_${nm}.png`));
  }
  await sharp(Buffer.from(journeySVG())).png().toFile(IMG("journey_path.png"));

  // ---------------------------------------------------------------- layouts
  pres.defineSlideMaster({ title: "HERO", background: { path: IMG("bg_dark.png") }, objects: [] });
  pres.defineSlideMaster({
    title: "DARK", background: { path: IMG("bg_dark.png") }, margin: [0.5, 0.7, 0.6, 0.7],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.62, w: 11.9, h: 0.85, fontSize: 36, bold: true,
        color: C.background1, valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "OcuLens-AI  ·  Capstone 2026", options: { x: 0.7, y: 7.02, w: 6, h: 0.28, fontSize: 10, color: C.accent6, margin: 0, isTextBox: true } } },
    ],
    slideNumber: { x: 12.1, y: 7.02, w: 0.55, h: 0.28, fontSize: 10, color: C.accent6, align: "right" },
  });
  pres.defineSlideMaster({
    title: "LIGHT", background: { path: IMG("bg_light.png") }, margin: [0.5, 0.7, 0.6, 0.7],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.62, w: 11.9, h: 0.85, fontSize: 36, bold: true,
        color: C.text2, valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "OcuLens-AI  ·  Capstone 2026", options: { x: 0.7, y: 7.02, w: 6, h: 0.28, fontSize: 10, color: C.accent6, margin: 0, isTextBox: true } } },
    ],
    slideNumber: { x: 12.1, y: 7.02, w: 0.55, h: 0.28, fontSize: 10, color: C.accent6, align: "right" },
  });

  const I = {
    eye: await icon(fa.FaEye), camera: await icon(fa.FaCamera), layers: await icon(fa.FaLayerGroup),
    brain: await icon(fa.FaBrain), search: await icon(fa.FaSearchPlus), chart: await icon(fa.FaChartLine),
    shield: await icon(fa.FaShieldAlt), hospital: await icon(fa.FaHospital), exclam: await icon(fa.FaExclamationTriangle),
    question: await icon(fa.FaQuestionCircle), flask: await icon(fa.FaFlask), check: await icon(fa.FaCheckCircle),
    user: await icon(fa.FaUserMd), file: await icon(fa.FaFilePdf), map: await icon(fa.FaMapMarkerAlt),
    images: await icon(fa.FaImages), gauge: await icon(fa.FaTachometerAlt), laptop: await icon(fa.FaLaptopMedical),
    users: await icon(fa.FaUsers), history: await icon(fa.FaHistory), sliders: await icon(fa.FaSlidersH),
    bullseye: await icon(fa.FaBullseye), hand: await icon(fa.FaHandPaper), magic: await icon(fa.FaMagic),
    database: await icon(fa.FaDatabase), clock: await icon(fa.FaClock), ban: await icon(fa.FaBan), idcard: await icon(fa.FaIdCard),
    filter: await icon(fa.FaFilter), crosshairs: await icon(fa.FaCrosshairs), scale: await icon(fa.FaBalanceScale), rocket: await icon(fa.FaRocket),
    comments: await icon(fa.FaComments), mic: await icon(fa.FaMicrophone), robot: await icon(fa.FaRobot),
  };

  // section divider: giant numeral, title, what is inside, and an iris in this section's eye colour
  function divider(num, title, sub, chips, irisImg, notes, section) {
    const d = pres.addSlide({ masterName: "HERO", sectionTitle: section });
    d.addImage({ path: IMG(irisImg), x: 7.15, y: 0.45, w: 6.6, h: 6.6, altText: "Stylised iris", objectName: oname("div_iris") });
    d.addText(num, { x: 0.65, y: 0.3, w: 5.5, h: 2.72, fontFace: THEME.headFontFace, fontSize: 160, bold: true, color: "1F4FBF", margin: 0, isTextBox: true, objectName: oname("div_num") });
    d.addText(title, { x: 0.75, y: 3.05, w: 6.6, h: 0.95, fontFace: THEME.headFontFace, fontSize: 44, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("div_title") });
    d.addText(sub, { x: 0.75, y: 4.1, w: 6.2, h: 0.95, fontSize: 18, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: oname("div_sub") });
    let cx0 = 0.75, cy0 = 5.35;
    chips.forEach((t) => {
      const w = 0.4 + t.length * 0.088;
      if (cx0 + w > 7.0) { cx0 = 0.75; cy0 += 0.55; }
      d.addText(t, { x: cx0, y: cy0, w, h: 0.42, fontSize: 13, bold: true, color: C.background1, fill: { color: PANEL }, line: { color: HEX.accent2, width: 1 },
        align: "center", valign: "middle", margin: 0, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.21, isTextBox: true, objectName: oname("div_chip") });
      cx0 += w + 0.15;
    });
    d.addNotes(notes);
    return d;
  }
  const ci = rd(`${EV}/ci/ci.json`) || {};

  // ================================================================ 1. Title
  pres.addSection({ title: "Introduction" });
  let s = pres.addSlide({ masterName: "HERO", sectionTitle: "Introduction" });
  s.addImage({ path: IMG("hero_iris.png"), x: 6.95, y: 0.2, w: 7.1, h: 7.1, altText: "Stylised iris drawn as a scan, with fibres, pupil and measurement rings", objectName: "hero_iris" });
  s.addText("CAPSTONE PROJECT 2026", { x: 0.75, y: 1.0, w: 6, h: 0.35, fontSize: 14, bold: true, charSpacing: 6, color: C.accent2, margin: 0, isTextBox: true, objectName: "t_kicker" });
  s.addText("OcuLens-AI", { x: 0.75, y: 1.45, w: 6.2, h: 1.2, fontFace: THEME.headFontFace, fontSize: 66, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "t_title" });
  s.addText("Seeing the eye the way a specialist does: explainable, uncertainty-aware screening of anterior-eye disease",
    { x: 0.75, y: 2.8, w: 5.9, h: 1.25, fontSize: 20, color: SOFT, margin: 0, valign: "top", isTextBox: true, objectName: "t_sub" });
  ["Keratitis", "Corneal ulcer", "Trachoma"].forEach((t, i) => {
    const x = 0.75 + i * 1.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.25, w: 1.8, h: 0.5, rectRadius: 0.25, fill: { color: PANEL }, line: { color: HEX.accent2, width: 1.25 }, objectName: oname("chip") });
    s.addText(t, { x, y: 4.25, w: 1.8, h: 0.5, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: oname("chiptxt") });
  });
  s.addText("TEAM", { x: 0.75, y: 5.2, w: 3, h: 0.3, fontSize: 12, bold: true, charSpacing: 6, color: C.accent2, margin: 0, isTextBox: true, objectName: "t_team_l" });
  s.addText([{ text: "Syed Mohammed Yaseen", options: { breakLine: true } }, { text: "Mohammed Ayaan", options: { breakLine: true } }, { text: "Arfath Khan" }],
    { x: 0.75, y: 5.55, w: 5.5, h: 1.15, fontSize: 18, color: C.background1, margin: 0, valign: "top", isTextBox: true, objectName: "t_team" });
  s.addNotes("Introduce the team. OcuLens-AI looks at a photo of the front of the eye and answers four questions a specialist would: what is wrong, where it is, how sure we are, and who the patient should see next. The colours of this deck are the colours of a slit-lamp eye exam: cobalt-blue light and the green-yellow glow of fluorescein dye.");

  divider("01", "Why it matters", "Eye infections, too few specialists, and AI that does not explain itself.",
    ["The problem", "Research questions", "Data"], "hero_iris.png",
    "Section one: why this problem matters, the four questions we set out to answer, and the data we used.", "Introduction");

  // ================================================================ 2. Problem
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Introduction" });
  kicker(s, "THE PROBLEM", false);
  s.addText("Treatable eye disease is found too late", { placeholder: "title" });
  const probs = [
    [I.clock, "Found late", "Corneal infections are treatable, yet many patients reach a specialist only after their sight is affected."],
    [I.hospital, "Few specialists", "Eye doctors cluster in cities; vision centres often have a camera but no ophthalmologist."],
    [I.exclam, "Infections are emergencies", "A corneal ulcer can damage sight within days, and an urgent red eye looks like a minor one."],
    [I.question, "Current AI falls short", "Most models give one label, without saying where the problem is, how sure they are, or what to do."],
  ];
  probs.forEach(([ic, h, b], i) => {
    const x = 0.7 + (i % 2) * 3.95, y = 1.75 + Math.floor(i / 2) * 2.5;
    panel(s, x, y, 3.75, 2.3, HEX.lt2);
    iconDisc(s, ic, x + 0.3, y + 0.3, 0.7, i === 2 ? HEX.accent3 : HEX.accent1);
    s.addText(h, { x: x + 0.3, y: y + 1.08, w: 3.2, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("ph") });
    s.addText(b, { x: x + 0.3, y: y + 1.48, w: 3.2, h: 0.75, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: oname("pb") });
  });
  irisFrame(s, IMG("sq_ker_HSK.jpg"), 8.95, 1.85, 3.75, HEX.accent1, "Cobalt-blue slit-lamp photo; fluorescein dye glows green over a corneal lesion");
  note(s, "Herpes simplex keratitis under the slit lamp's cobalt-blue light: the fluorescein dye glows green where the cornea is damaged. These are the colours of this deck.", 8.75, 5.85, 4.15, 0.9, false);
  s.addNotes("The problem is not that these diseases are untreatable; it is that patients are found late and the tools that exist give one label with no explanation. A screening tool has to say where, how sure, and what next.");

  // ================================================================ 3. Research questions
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Introduction" });
  kicker(s, "OBJECTIVES", true);
  s.addText("Four research questions", { placeholder: "title" });
  s.addText("Goal: say what is wrong, where it is, how sure we are, and who the patient should see next.",
    { x: 0.7, y: 1.55, w: 11.9, h: 0.45, fontSize: 18, color: SOFT, margin: 0, isTextBox: true, objectName: "rq_goal" });
  const rqs = [
    ["RQ1", "Anatomy", "Does telling the model where the cornea is improve the diagnosis?", "Tested: mask as input, cornea crop, multitask head"],
    ["RQ2", "Data", "Do synthetic images help rare classes, and does restyling help with another hospital's images?", "Tested: DDPM diffusion, CycleGAN"],
    ["RQ3", "Uncertainty", "Can the model tell when it is unsure, and refer instead of guessing?", "Tested: calibration, conformal sets, 10-model ensemble"],
    ["RQ4", "Explanation", "Does the heat-map actually point at the cornea and the ulcer?", "Tested: Grad-CAM++, attention-in-region, pointing game"],
  ];
  const rqIcons = [[I.crosshairs, HEX.accent1], [I.magic, HEX.accent4], [I.chart, HEX.accent5], [I.search, HEX.accent3]];
  rqs.forEach(([k, h, q, t], i) => {
    const x = 0.7 + i * 3.03;
    panel(s, x, 2.3, 2.8, 4.35, PANEL);
    iconDisc(s, rqIcons[i][0], x + 1.95, 2.5, 0.6, rqIcons[i][1]);
    s.addText(k, { x: x + 0.25, y: 2.5, w: 1.6, h: 0.6, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: oname("rqk") });
    s.addText(h, { x: x + 0.25, y: 3.15, w: 2.3, h: 0.42, fontSize: 18, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("rqh") });
    s.addText(q, { x: x + 0.25, y: 3.65, w: 2.3, h: 1.85, fontSize: 15, color: SOFT, margin: 0, valign: "top", isTextBox: true, objectName: oname("rqq") });
    s.addText(t, { x: x + 0.25, y: 5.6, w: 2.3, h: 0.85, fontSize: 12, italic: true, color: "8FB2FF", margin: 0, valign: "top", isTextBox: true, objectName: oname("rqt") });
  });
  s.addNotes("Four research questions drive the whole project. RQ1 is about anatomy, RQ2 about data, RQ3 about honest uncertainty, RQ4 about whether the explanations are trustworthy. Each later results slide is labelled with the question it answers.");

  // ================================================================ 4. Datasets
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Introduction" });
  kicker(s, "DATA", false);
  s.addText("Three public datasets, 3,741 images", { placeholder: "title" });
  const th = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 14 } });
  const td = (t, o = {}) => ({ text: t, options: { fontSize: 14, color: HEX.dk1, ...o } });
  s.addTable([
    [th("Dataset"), th("Images"), th("Labels"), th("Test set")],
    [td("Infectious Keratitis (2 hospitals)", { bold: true }), td("1,373"), td("Bacterial, fungal, herpes, other"), td("429 images")],
    [td("SUSTech-SYSU corneal ulcer", { bold: true }), td("712"), td("3 ulcer patterns + cornea masks"), td("102 images")],
    [td("Trachoma conjunctiva photos", { bold: true }), td("1,656"), td("Trachoma sign TF: yes / no"), td("237 images")],
  ], { x: 0.7, y: 1.75, w: 8.2, colW: [2.75, 1.0, 2.95, 1.5], rowH: 0.62, border: { type: "solid", color: "D3DDEE", pt: 0.75 },
    fill: { color: "FFFFFF" }, valign: "middle", margin: 0.08, objectName: "data_table" });
  panel(s, 0.7, 4.55, 8.2, 2.0, HEX.lt2);
  iconDisc(s, I.shield, 0.95, 4.8, 0.75, HEX.accent1);
  s.addText([
    { text: "Kept honest: ", options: { bold: true, color: C.text2 } },
    { text: "splits are by patient, so no patient is in both training and test. Every test image is a real photograph; synthetic images are used for training only. Three more collected datasets (cataract, web images) were not used for the final models." },
  ], { x: 1.95, y: 4.75, w: 6.75, h: 1.6, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "data_rules" });
  [["sq_ker_FK.jpg", "Keratitis", "Fungal keratitis, slit lamp"], ["sq_sus_overlay.jpg", "Corneal ulcer", "Fluorescein-stained cornea with the ulcer outlined"], ["sq_tra_tf.jpg", "Trachoma", "Everted eyelid with trachoma follicles"]].forEach(([f, lab, alt], i) => {
    const y = 1.75 + i * 1.65;
    irisFrame(s, IMG(f), 9.45, y, 1.4, HEX.accent1, alt);
    s.addText(lab, { x: 11.1, y: y + 0.45, w: 1.6, h: 0.5, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("dlab") });
  });
  s.addNotes("Three public datasets, 3,741 images in total. Each is split by patient, and every test image is real. Keratitis has four infection types that look alike, which makes it the hardest task.");

  // ================================================================ Section 02: how we built it
  pres.addSection({ title: "How we built it" });
  divider("02", "How we built it", "Every step and every model, from raw photos to a working clinic portal.",
    ["Project journey", "Model zoo", "Model flow", "Runtime pipeline", "DGX training"], "iris_green.png",
    "Section two: how we built it. First the whole journey on one slide, then every model we used, how the models feed each other, the pipeline that runs for each patient, and the GPU training.", "How we built it");

  // ---------------------------------------------------------------- Project journey: the complete view of every step
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "How we built it" });
  s.addImage({ path: IMG("journey_path.png"), x: 0, y: 0, w: 13.333, h: 7.5, altText: "Glowing three-lane path linking the twelve project steps", objectName: "journey_path" });
  kicker(s, "THE COMPLETE JOURNEY · 12 STEPS", true);
  s.addText("How we built OcuLens-AI", { placeholder: "title" });
  [["Plan & data", HEX.accent5, HEX.dk2], ["Build models", HEX.accent1, "FFFFFF"], ["Trust & ship", HEX.accent4, HEX.dk2]].forEach(([t, bg, fg], i) => {
    s.addText(t, { x: 8.55 + i * 1.38, y: 0.8, w: 1.28, h: 0.36, fontSize: 12, bold: true, color: fg, fill: { color: bg }, align: "center", valign: "middle", margin: 0,
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.18, isTextBox: true, objectName: oname("phase") });
  });
  const J = JOURNEY;
  const jsteps = [
    [I.question, "Define the problem", "4 research questions"],
    [I.database, "Collect data", "6 public datasets, checksums verified"],
    [I.filter, "Clean & split", "manifest, patient-level splits, 512-px cache"],
    [I.check, "Quality & preprocessing", "blur and glare checks, CLAHE contrast"],
    [I.layers, "Segment the cornea", "U-Net cornea + U-Net ulcer"],
    [I.brain, "Train classifiers", "EfficientNet-B0, 3 tasks, DGX GPUs"],
    [I.crosshairs, "Test anatomy (RQ1)", "mask input, cornea crop, multitask"],
    [I.magic, "Synthetic data (RQ2)", "DDPM diffusion and CycleGAN"],
    [I.chart, "Uncertainty (RQ3)", "temperature scaling, conformal sets, 10-seed ensemble"],
    [I.search, "Explanations (RQ4)", "Grad-CAM++, attention in cornea, pointing game"],
    [I.scale, "Evaluate & choose", "bootstrap CIs, fairness, failure cases, model sweep"],
    [I.rocket, "Ship the portal", "Streamlit portal, guided capture, AI assistant, PDF"],
  ];
  jsteps.forEach(([ic, h, d], i) => {
    const row = Math.floor(i / 4), k = i % 4;
    const x = row === 1 ? J.xs[3 - k] : J.xs[k], y = J.lanes[row];
    const col = i === 11 ? HEX.accent3 : [HEX.accent5, HEX.accent1, HEX.accent4][row];
    s.addShape(pres.shapes.OVAL, { x: x - 0.45, y: y - 0.45, w: 0.9, h: 0.9, fill: { color: "0A1A33" }, line: { color: col, width: 2.25 }, objectName: oname("jring") });
    iconDisc(s, ic, x - 0.33, y - 0.33, 0.66, col);
    s.addText(String(i + 1), { x: x + 0.22, y: y - 0.6, w: 0.36, h: 0.36, fontSize: 12, bold: true, color: HEX.dk2, fill: { color: HEX.accent2 }, align: "center", valign: "middle", margin: 0, shape: pres.shapes.OVAL, isTextBox: true, objectName: oname("jnum") });
    s.addText(h, { x: x - 1.35, y: y + 0.5, w: 2.7, h: 0.3, fontSize: 14, bold: true, color: C.background1, align: "center", margin: 0, isTextBox: true, objectName: oname("jh") });
    s.addText(d, { x: x - 1.35, y: y + 0.81, w: 2.7, h: 0.42, fontSize: 11, color: SOFT, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: oname("jd") });
  });
  s.addNotes("The whole project on one slide, in the order we did it. Plan and data: define the four research questions, collect six public datasets and verify them, build patient-level splits, and add quality checks and contrast enhancement. Build models: train the cornea and ulcer U-Nets, train EfficientNet-B0 classifiers for all three tasks on the DGX, test the anatomy variants, and add diffusion and CycleGAN images. Trust and ship: measure uncertainty, check the explanations, evaluate with confidence intervals and pick the best models, then ship them in the clinic portal.");

  // ---------------------------------------------------------------- Model zoo: every model we used
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How we built it" });
  kicker(s, "MODEL ZOO", false);
  s.addText("Every model we used", { placeholder: "title" });
  note(s, "★ runs in the live portal · classifiers are ImageNet-pretrained EfficientNet-B0", 6.45, 0.95, 6.2, 0.3, false, { align: "right" });
  const FAM = { CLASSIFIER: [HEX.accent1, "FFFFFF"], TRIED: ["B5C0D3", HEX.dk2], SEGMENTATION: [HEX.accent5, "FFFFFF"], GENERATIVE: [HEX.accent4, HEX.dk2], TRUST: [HEX.accent2, HEX.dk2], SAFETY: [HEX.accent3, "FFFFFF"] };
  const zoo = [
    ["CLASSIFIER", "CLASSIFIER", "Keratitis model ★", "EfficientNet-B0 trained on real + synthetic rare-class images", "0.488 · best of 4 seeds"],
    ["CLASSIFIER", "CLASSIFIER", "10-seed ensemble ★", "Ten EfficientNet-B0s from different seeds; disagreement = uncertainty", "0.451 · uncertainty score"],
    ["CLASSIFIER", "CLASSIFIER", "Trachoma model ★", "EfficientNet-B0 spotting follicles (TF) on the everted eyelid", "0.814 · AUROC 0.90"],
    ["CLASSIFIER", "CLASSIFIER", "Ulcer-pattern model ★", "EfficientNet-B0 grading three ulcer patterns from the photo", "0.632 balanced accuracy"],
    ["CLASSIFIER", "CLASSIFIER · RQ1", "Anatomy variants", "Cornea mask as extra input, cornea crop, multitask severity head", "best: mask input 0.678"],
    ["TRIED", "TRIED · NOT SHIPPED", "320 px · CycleGAN runs", "Higher resolution and harmonised training for keratitis", "0.409 and 0.422"],
    ["SEGMENTATION", "SEGMENTATION", "U-Net · cornea ★", "Outlines the cornea; drives the anatomy variants and portal layers", "Dice 0.965 · layers view"],
    ["SEGMENTATION", "SEGMENTATION", "U-Net · ulcer", "Outlines the ulcer lesion; labels now read the right way round", "Dice 0.77 after the label fix"],
    ["GENERATIVE", "GENERATIVE", "DDPM diffusion ★", "Class-conditional model that draws 64-px rare-class eye images", "keratitis +0.117"],
    ["GENERATIVE", "GENERATIVE", "CycleGAN", "Makes ZEH-hospital photos look like AGEH ones", "keratitis 0.371 → 0.422"],
    ["TRUST", "TRUST", "Trust layer ★", "Temperature scaling, 95% conformal sets, Grad-CAM++ heat-maps", "ECE 0.047 · coverage 0.91–0.97"],
    ["SAFETY", "SAFETY", "Eye & quality gates ★", "EfficientNet features vs 903 real eyes; blur, light and glare tests", "run before every prediction"],
  ];
  zoo.forEach(([fam, tag, name, role, res], i) => {
    const x = 0.7 + (i % 4) * 3.03, y = 1.7 + Math.floor(i / 4) * 1.72, w = 2.83;
    const [bg, fg] = FAM[fam];
    panel(s, x, y, w, 1.6, HEX.lt2);
    s.addText(tag, { x: x + 0.18, y: y + 0.15, w: 0.34 + tag.length * 0.075, h: 0.27, fontSize: 10, bold: true, charSpacing: 1, color: fg, fill: { color: bg },
      align: "center", valign: "middle", margin: 0, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.13, isTextBox: true, objectName: oname("ztag") });
    s.addText(name, { x: x + 0.18, y: y + 0.5, w: w - 0.3, h: 0.34, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: oname("zname") });
    s.addText(role, { x: x + 0.18, y: y + 0.85, w: w - 0.3, h: 0.44, fontSize: 11, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: oname("zrole") });
    s.addText(res, { x: x + 0.18, y: y + 1.3, w: w - 0.3, h: 0.26, fontSize: 12, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: oname("zres") });
  });
  s.addNotes("Every model in the project on one slide. Four EfficientNet-B0 classifiers run in the portal: the diffusion-augmented keratitis model, the trachoma and ulcer models, and a ten-seed ensemble used only to measure uncertainty. The anatomy variants answered RQ1; the high-resolution and CycleGAN runs were tested and not shipped. Two U-Nets segment the cornea and the ulcer, a DDPM draws synthetic training images, and CycleGAN restyles photos between the two keratitis hospitals. Around them sit the trust layer and the two safety gates.");

  // ---------------------------------------------------------------- Model flow: how the models feed each other
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "How we built it" });
  kicker(s, "MODEL FLOW", true);
  s.addText("How the models feed each other", { placeholder: "title" });
  const lineage = [
    { x: 0.7, w: 1.8, head: "DATA", h: 1.05, items: [["Keratitis", "1,373 photos", "8A9BB8"], ["Corneal ulcer", "712 photos", "8A9BB8"], ["Trachoma", "1,656 photos", "8A9BB8"]] },
    { x: 2.85, w: 2.2, head: "SUPPORT MODELS", h: 0.85, items: [["U-Net · cornea", "cornea masks", HEX.accent5], ["U-Net · ulcer", "ulcer masks", HEX.accent5, true], ["DDPM diffusion", "synthetic rare-class images", HEX.accent4], ["CycleGAN", "restyled hospital photos", HEX.accent4]] },
    { x: 5.4, w: 2.6, head: "CLASSIFIERS", h: 0.72, items: [["EfficientNet-B0 baselines ×3", "keratitis, ulcer, trachoma", HEX.accent1], ["Anatomy variants ×3", "mask input, crop, multitask", HEX.accent1], ["Diffusion-augmented", "the keratitis winner", HEX.accent1], ["10-seed ensemble", "for uncertainty", HEX.accent1], ["320 px · CycleGAN-trained", "tested, not shipped", "8A9BB8", true]] },
    { x: 8.35, w: 2.0, head: "TRUST LAYER", h: 0.85, items: [["Temperature scaling", "honest confidence", HEX.accent2], ["Conformal sets", "95% prediction sets", HEX.accent2], ["Ensemble disagreement", "uncertainty score", HEX.accent2], ["Grad-CAM++", "heat-map explanation", HEX.accent2]] },
    { x: 10.7, w: 1.9, head: "IN THE PORTAL", h: 0.72, items: [["Keratitis ★", "diffusion model", HEX.accent3], ["Ulcer + trachoma ★", "baseline models", HEX.accent3], ["U-Net layers ★", "cornea outline", HEX.accent3], ["Image generator ★", "DDPM samples", HEX.accent3], ["Eye + quality gates ★", "before predicting", HEX.accent3]] },
  ];
  const top = 2.0, span = 4.55;
  lineage.forEach((col) => {
    s.addText(col.head, { x: col.x, y: 1.58, w: col.w + 0.1, h: 0.3, fontSize: 11, bold: true, charSpacing: 2, color: C.accent2, margin: 0, isTextBox: true, objectName: oname("lhead") });
    const n = col.items.length, gap = n > 1 ? (span - n * col.h) / (n - 1) : 0;
    col.items.forEach(([name, sub, lc, dashed], j) => {
      const y = top + j * (col.h + gap);
      s.addText([{ text: name, options: { bold: true, fontSize: 12, color: dashed ? "B5C0D3" : "FFFFFF", breakLine: true } }, { text: sub, options: { fontSize: 10, color: SOFT } }],
        { x: col.x, y, w: col.w, h: col.h, fill: { color: PANEL }, line: { color: lc, width: 1.5, dashType: dashed ? "dash" : "solid" }, valign: "middle", margin: [4, 8, 4, 8],
          shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.1, isTextBox: true, objectName: oname("lbox") });
    });
  });
  [2.5, 5.05, 8.0, 10.35].forEach((gx) => [2.55, 4.25, 5.95].forEach((gy) => {
    s.addShape(pres.shapes.CHEVRON, { x: gx + 0.09, y: gy - 0.2, w: 0.17, h: 0.4, fill: { color: HEX.accent2 }, line: { color: HEX.accent2 }, objectName: oname("chev") });
  }));
  note(s, "Dashed = trained and tested, not shipped. Synthetic and restyled images are used for training only; every test image is real.", 0.7, 6.62, 11.9, 0.32, true);
  s.addNotes("Read left to right. Photos from the three datasets train the support models: two U-Nets that outline the cornea and ulcer, a DDPM that draws synthetic images, and CycleGAN that restyles one hospital's photos. Their outputs feed the EfficientNet-B0 classifiers. The trust layer turns raw scores into calibrated confidence, prediction sets, an uncertainty score and a heat-map. On the right is what actually runs in the portal; dashed boxes were tested but not shipped.");

  // ================================================================ 5. Architecture (runtime)
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "How we built it" });
  kicker(s, "AT RUN TIME · FOR EACH PATIENT", true);
  s.addText("From camera to referral", { placeholder: "title" });
  const stepsA = [
    [I.camera, "Guided capture", "Right eye, then left; live focus meter", HEX.accent1],
    [I.eye, "Eye check", "Refuses images that are not an eye", HEX.accent5],
    [I.check, "Quality check", "Blur, light and glare", HEX.accent5],
    [I.layers, "Cornea U-Net", "Finds the cornea", HEX.accent1],
    [I.brain, "Classifier", "Diffusion-augmented EfficientNet-B0", HEX.accent1],
    [I.chart, "Uncertainty", "Calibration, conformal set, ensemble", HEX.accent1],
    [I.search, "Grad-CAM++", "Shows where the model looked", HEX.accent1],
    [I.hospital, "Referral", "3 Bengaluru specialists, case + PDF", HEX.accent3],
  ];
  const cx = [1.55, 4.75, 7.95, 11.15];
  const node = (i) => (i < 4 ? { x: cx[i], y: 2.25 } : { x: cx[7 - i], y: 4.55 });
  s.addShape(pres.shapes.LINE, { x: cx[0], y: 2.25, w: cx[3] - cx[0], h: 0, line: { color: HEX.accent2, width: 2, dashType: "dash" }, objectName: "flow1" });
  // route the turn around the right of step 4's label instead of through it
  const turnX = 12.2;
  s.addShape(pres.shapes.LINE, { x: cx[3], y: 2.25, w: turnX - cx[3], h: 0, line: { color: HEX.accent2, width: 2, dashType: "dash" }, objectName: "flow2a" });
  s.addShape(pres.shapes.LINE, { x: turnX, y: 2.25, w: 0, h: 2.3, line: { color: HEX.accent2, width: 2, dashType: "dash" }, objectName: "flow2b" });
  s.addShape(pres.shapes.LINE, { x: cx[3], y: 4.55, w: turnX - cx[3], h: 0, line: { color: HEX.accent2, width: 2, dashType: "dash" }, objectName: "flow2c" });
  s.addShape(pres.shapes.LINE, { x: cx[0], y: 4.55, w: cx[3] - cx[0], h: 0, line: { color: HEX.accent2, width: 2, dashType: "dash" }, objectName: "flow3" });
  stepsA.forEach(([ic, h, d, col], i) => {
    const { x, y } = node(i);
    s.addShape(pres.shapes.OVAL, { x: x - 0.62, y: y - 0.62, w: 1.24, h: 1.24, fill: { color: "0A1A33" }, line: { color: col, width: 2.25 }, objectName: oname("ring") });
    iconDisc(s, ic, x - 0.47, y - 0.47, 0.94, col);
    s.addText(String(i + 1), { x: x + 0.36, y: y - 0.7, w: 0.36, h: 0.36, fontSize: 12, bold: true, color: HEX.dk2, fill: { color: HEX.accent2 }, align: "center", valign: "middle", margin: 0, shape: pres.shapes.OVAL, isTextBox: true, objectName: oname("num") });
    s.addText(h, { x: x - 1.4, y: y + 0.7, w: 2.8, h: 0.38, fontSize: 16, bold: true, color: C.background1, align: "center", margin: 0, isTextBox: true, objectName: oname("sh") });
    s.addText(d, { x: x - 1.4, y: y + 1.08, w: 2.8, h: 0.5, fontSize: 13, color: SOFT, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: oname("sd") });
  });
  note(s, "Green rings are safety gates that run before any prediction. Models were trained on the NVIDIA DGX; the portal itself runs fully offline on a laptop CPU.", 0.7, 6.4, 11.9, 0.45, true);
  s.addNotes("The pipeline in eight steps. Capture, then two safety gates: is it an eye, and is the photo usable. Only then the cornea is segmented, the classifier runs, uncertainty is measured, the heat-map is computed, and the patient is referred. Every step is visible in the portal.");

  // ================================================================ 7. Training setup
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "How we built it" });
  kicker(s, "INFRASTRUCTURE", true);
  s.addText("Training on the NVIDIA DGX", { placeholder: "title" });
  [["4", "team GPU accounts in parallel"], ["H200", "GPU slices (18 GB each)"], ["50", "epochs per model"], ["35 min", "final stretch, down from about 2 hours"]].forEach(([n, l], i) => {
    const x = 0.7 + (i % 2) * 2.85, y = 1.75 + Math.floor(i / 2) * 2.45;
    panel(s, x, y, 2.65, 2.25, PANEL);
    s.addText(n, { x: x + 0.2, y: y + 0.25, w: 2.25, h: 0.95, fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: oname("tn") });
    s.addText(l, { x: x + 0.2, y: y + 1.25, w: 2.25, h: 0.85, fontSize: 14, color: C.background1, valign: "top", margin: 0, isTextBox: true, objectName: oname("tl") });
  });
  s.addText("Who trained what", { x: 6.75, y: 1.75, w: 5.9, h: 0.4, fontSize: 18, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "who_h" });
  [["0034", "Baselines for all three tasks, cornea U-Nets, anatomy variants, explanation checks"],
   ["0001", "5-model keratitis ensemble and the multitask ulcer model"],
   ["0063", "Diffusion image synthesis and the diffusion-augmented retrain"],
   ["3007", "CycleGAN harmonisation and extra seeds for the 10-model ensemble"]].forEach(([a, t], i) => {
    const y = 2.35 + i * 1.02;
    s.addText(a, { x: 6.75, y, w: 1.05, h: 0.5, fontSize: 15, bold: true, color: HEX.dk2, fill: { color: HEX.accent2 }, align: "center", valign: "middle", margin: 0, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.1, isTextBox: true, objectName: oname("acct") });
    s.addText(t, { x: 8.0, y: y - 0.12, w: 4.6, h: 0.8, fontSize: 14, color: SOFT, valign: "middle", margin: 0, isTextBox: true, objectName: oname("accttxt") });
  });
  note(s, "Splitting the work across the team's own accounts let jobs run side by side instead of one after another. The finished portal needs no GPU.", 6.75, 6.45, 5.9, 0.45, true);
  s.addNotes("Training ran on the university's NVIDIA DGX, using only the four team members' own accounts. Running jobs in parallel cut the final stretch from about two hours to 35 minutes. Once trained, everything runs offline on a laptop.");

  // ================================================================ 8. Results overview
  pres.addSection({ title: "Results" });
  divider("03", "What we found", "Results with confidence intervals, and honest about what did not work.",
    ["Results", "Anatomy", "Model choice", "Synthetic data", "Uncertainty", "Explanations"], "iris_hazel.png",
    "Section three: what we found, one research question at a time, with confidence intervals and the experiments that did not work.", "Results");
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Results" });
  kicker(s, "RESULTS", false);
  s.addText("Best model for each task", { placeholder: "title" });
  const kd = ci.keratitis_diffusion || {}, ul = ci.ulcer_pattern || {}, tr = ci.trachoma_tf || {};
  s.addChart(pres.charts.BAR, [
    { name: "Best model", labels: ["Trachoma", "Ulcer pattern", "Keratitis"], values: [tr.balanced_accuracy?.point ?? 0.814, ul.balanced_accuracy?.point ?? 0.678, kd.balanced_accuracy?.point ?? 0.488] },
    { name: "Chance level", labels: ["Trachoma", "Ulcer pattern", "Keratitis"], values: [0.5, 0.333, 0.25] },
  ], { x: 0.7, y: 1.7, w: 6.1, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent1, "C3CCDC"], barGapWidthPct: 60,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 1,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: true, legendPos: "b",
    showTitle: true, title: "Balanced accuracy on held-out test images", ...chartText(false), objectName: "results_chart" });
  const ciTxt = (r) => r && r.balanced_accuracy ? `${f3(r.balanced_accuracy.point)}  [${f3(r.balanced_accuracy.ci95[0])}–${f3(r.balanced_accuracy.ci95[1])}]` : "n/a";
  s.addTable([
    [th("Task · model"), th("Balanced acc. [95% CI]"), th("AUROC")],
    [td("Trachoma · baseline", { bold: true }), td(ciTxt(tr)), td(f3(tr.auroc?.point))],
    [td("Ulcer · mask as input", { bold: true }), td(ciTxt(ul)), td(f3(ul.auroc?.point))],
    [td("Keratitis · diffusion", { bold: true }), td(ciTxt(kd)), td(f3(kd.auroc?.point))],
  ], { x: 7.15, y: 1.75, w: 5.45, colW: [2.05, 2.45, 0.95], rowH: 0.62, border: { type: "solid", color: "D3DDEE", pt: 0.75 },
    fill: { color: "FFFFFF" }, valign: "middle", margin: 0.08, objectName: "results_table" });
  panel(s, 7.15, 4.55, 5.45, 2.05, HEX.lt2);
  s.addText([
    { text: "Reading the numbers: ", options: { bold: true, color: C.text2 } },
    { text: "balanced accuracy averages over classes, so chance is 1 ÷ number of classes. Keratitis has four look-alike infections, so 0.49 is about twice chance. Keratitis: best of four training seeds; the average is 0.42." },
  ], { x: 7.4, y: 4.7, w: 5.0, h: 1.75, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "results_read" });
  s.addNotes("Trachoma is strong at 0.81, ulcer pattern 0.68, keratitis 0.49. The grey bars are chance level, so every model is well above chance; keratitis is about twice chance on a four-way problem. The brackets are 95% bootstrap confidence intervals.");

  // ================================================================ 9. RQ1 anatomy
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Results" });
  kicker(s, "RQ1 · ANATOMY", true);
  s.addText("Anatomy helps ulcer grading", { placeholder: "title" });
  const P50 = `${EV}/runs_50ep_parallel`;
  const ba = (f) => { const d = rd(`${P50}/${f}.json`); return d ? (d.overall || d).balanced_accuracy : null; };
  const rq1 = (title, labels, files) => ({ title, labels, values: files.map(ba) });
  const ulc = rq1("Ulcer pattern (102 test images)", ["Image only", "Mask as input", "Cornea crop", "Multitask"],
    ["eval_ulcer_pattern_image", "eval_ulcer_pattern_mask_input", "eval_ulcer_pattern_region_crop", "eval_ulcer_pattern_multitask"]);
  const ker = rq1("Keratitis (429 test images)", ["Image only", "Mask as input", "Cornea crop"],
    ["eval_keratitis_image", "eval_keratitis_mask_input", "eval_keratitis_region_crop"]);
  [[ulc, 0.7], [ker, 6.85]].forEach(([d, x]) => {
    s.addChart(pres.charts.BAR, [{ name: "Balanced accuracy", labels: d.labels, values: d.values }], {
      x, y: 1.75, w: 5.75, h: 3.75, barDir: "col", chartColors: [x < 1 ? HEX.accent2 : "8FB2FF"], barGapWidthPct: 55,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 0.85,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: d.title,
      ...chartText(true), objectName: oname("rq1chart") });
  });
  panel(s, 0.7, 5.7, 11.9, 1.05, PANEL);
  s.addText([
    { text: "Ulcer: ", options: { bold: true, color: C.accent2 } },
    { text: "the cornea mask as an extra input gave the best balanced accuracy (0.678 vs 0.632) and the crop the best AUROC (0.866). " },
    { text: "Keratitis: ", options: { bold: true, color: "8FB2FF" } },
    { text: "no clear gain. With 102 ulcer test images the gaps sit inside the confidence intervals: suggestive, not proven." },
  ], { x: 0.95, y: 5.75, w: 11.4, h: 0.95, fontSize: 14, color: C.background1, valign: "middle", margin: 0, isTextBox: true, objectName: "rq1_take" });
  s.addNotes("RQ1: does knowing where the cornea is help? For ulcer pattern, yes: feeding the cornea mask as a fourth input channel gave the best balanced accuracy, and cropping to the cornea gave the best AUROC. For keratitis there is no clear gain, probably because infection type depends on texture rather than location. The ulcer test set is small, so we call this suggestive.");

  // ================================================================ 10. Keratitis sweep
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Results" });
  kicker(s, "CHOOSING THE KERATITIS MODEL", false);
  s.addText("Diffusion helps, but seeds vary", { placeholder: "title" });
  const sw = rd(`${EV}/runs/final_sweep.json`);
  const swRuns = sw ? sw.runs : [];
  const swLab = { "5-model deep ensemble (prior)": "5-model ensemble", "Higher-resolution 320px (single)": "Higher resolution (320 px)", "10-model deep ensemble": "10-model ensemble", "Diffusion-augmented (single) [SELECTED]": "Diffusion-augmented (single)" };
  const seedSt = rd(`${EV}/runs/seed_study.json`) || { mean: 0.423, ensemble4: { point: 0.474 } };
  const swL = swRuns.map((r) => swLab[r.label] || r.label), swV = swRuns.map((r) => r.d.balanced_accuracy);
  swL[swL.length - 1] = "Diffusion, best of 4 seeds"; swL.push("Diffusion, average of 4 seeds", "Diffusion ensemble (4 seeds)"); swV.push(seedSt.mean, seedSt.ensemble4.point);
  s.addChart(pres.charts.BAR, [{ name: "Balanced accuracy", labels: swL, values: swV }], {
    x: 0.7, y: 1.7, w: 7.1, h: 3.85, barDir: "bar", chartColors: [HEX.accent1], barGapWidthPct: 45, catAxisOrientation: "maxMin",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 0.6,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: "Keratitis balanced accuracy, same 429 test images",
    ...chartText(false), objectName: "sweep_chart" });
  panel(s, 8.25, 1.75, 4.35, 3.8, HEX.dk2);
  s.addText("0.474", { x: 8.55, y: 1.95, w: 3.8, h: 1.1, fontFace: THEME.headFontFace, fontSize: 60, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: "sweep_big" });
  s.addText("four diffusion models averaged beat the 10-model ensemble (0.451) without relying on one lucky run", { x: 8.55, y: 3.1, w: 3.8, h: 1.1, fontSize: 15, color: C.background1, valign: "top", margin: 0, isTextBox: true, objectName: "sweep_lbl" });
  s.addText("Single runs: 0.36–0.49, mean 0.42", { x: 8.55, y: 4.45, w: 3.8, h: 0.45, fontSize: 15, bold: true, color: "8FB2FF", margin: 0, isTextBox: true, objectName: "sweep_ece" });
  panel(s, 0.7, 5.8, 11.9, 0.95, HEX.lt2);
  s.addText([
    { text: "Honest reading: ", options: { bold: true, color: C.text2 } },
    { text: "0.488 is the best of four training seeds (0.488, 0.437, 0.408, 0.361). The ensemble's 95% interval (0.405–0.539) still overlaps the old one, so the gain is promising, not proven. Higher resolution (0.409) and doubling the synthetic images (0.388) did not help." },
  ], { x: 0.95, y: 5.85, w: 11.4, h: 0.85, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "sweep_note" });
  s.addNotes("For keratitis we tried several fixes in parallel on the team's GPUs. Diffusion augmentation gave the best single run, 0.488, but when we retrained the same recipe with three more random seeds we got 0.437, 0.408 and 0.361: the average is about 0.42, so 0.488 was partly a lucky draw. Averaging the four diffusion models into an ensemble gives 0.474, better than the 10-model plain ensemble with fewer than half the models. The intervals still overlap, so we call the gain promising, not proven. Higher resolution and doubling the synthetic images did not help.");

  // ================================================================ 11. Diffusion images
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Results" });
  kicker(s, "RQ2 · SYNTHETIC DATA", true);
  s.addText("Synthetic images help where data is scarce", { placeholder: "title" });
  s.addText("Real", { x: 2.2, y: 1.55, w: 1.05, h: 0.3, fontSize: 12, bold: true, color: SOFT, align: "center", margin: 0, isTextBox: true, objectName: "col_real" });
  s.addText("Synthetic (64 px DDPM samples)", { x: 3.4, y: 1.55, w: 3.45, h: 0.3, fontSize: 12, bold: true, color: C.accent2, align: "center", margin: 0, isTextBox: true, objectName: "col_syn" });
  [["BK", "Bacterial"], ["FK", "Fungal"], ["HSK", "Herpes"], ["other_corneal_abnormalities", "Other"]].forEach(([cls, lab], i) => {
    const y = 1.95 + i * 1.2;
    s.addText(lab, { x: 0.7, y: y + 0.3, w: 1.35, h: 0.4, fontSize: 15, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("cls") });
    irisFrame(s, IMG(`real_${cls}.jpg`), 2.25, y, 0.95, "8FB2FF", `Real ${lab.toLowerCase()} keratitis photo`);
    for (let k = 0; k < 3; k++) irisFrame(s, IMG(`syn_${cls}_${k}.png`), 3.5 + k * 1.15, y, 0.95, HEX.accent2, `Synthetic ${lab.toLowerCase()} keratitis image made by the diffusion model`);
  });
  const res11 = [
    ["Keratitis", "0.371 → 0.488", "best of 4 seeds (mean 0.42); 600 per class fell to 0.388"],
    ["Ulcer pattern", "0.632 → 0.646", "a small gain; the mask-input model (0.678) is still best"],
    ["Trachoma", "0.814 → 0.808", "no gain on a two-class task; the baseline stays"],
  ];
  res11.forEach(([h, n, d], i) => {
    const y = 1.75 + i * 1.6;
    panel(s, 7.3, y, 5.3, 1.42, PANEL);
    s.addText(h, { x: 7.55, y: y + 0.15, w: 2.2, h: 0.4, fontSize: 16, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("r11h") });
    s.addText(n, { x: 9.6, y: y + 0.1, w: 2.85, h: 0.55, fontFace: THEME.headFontFace, fontSize: 26, bold: true, color: i === 2 ? HEX.accent6 : C.accent2, align: "right", margin: 0, isTextBox: true, objectName: oname("r11n") });
    s.addText(d, { x: 7.55, y: y + 0.72, w: 4.9, h: 0.6, fontSize: 14, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: oname("r11d") });
  });
  note(s, "Synthetic images are used for training only; every test image is a real photograph.", 0.7, 6.55, 6.2, 0.35, true);
  s.addNotes("These are real outputs of our diffusion model: 64-pixel, blurry, clearly not photographs. Yet adding them for the rare classes lifted keratitis from 0.371 to 0.488. For ulcer the gain is small and the anatomy model still wins. The trachoma run was cut short when we lost GPU access.");

  // ================================================================ 12. Trust & safety
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Results" });
  kicker(s, "RQ3 · UNCERTAINTY", false);
  s.addText("Knowing when not to answer", { placeholder: "title" });
  [["0.91–0.97", "conformal coverage against a 0.95 target", HEX.accent1],
   ["0.047", "calibration error (ECE) of the deployed keratitis model", HEX.accent1],
   ["REFER", "unsure cases go to a specialist, never reported as normal", HEX.accent3]].forEach(([n, l, col], i) => {
    const y = 1.75 + i * 1.62;
    panel(s, 0.7, y, 3.7, 1.45, HEX.lt2);
    s.addText(n, { x: 0.95, y: y + 0.12, w: 3.3, h: 0.65, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: col, margin: 0, isTextBox: true, objectName: oname("kn") });
    s.addText(l, { x: 0.95, y: y + 0.78, w: 3.3, h: 0.6, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: oname("kl") });
  });
  const cal = rd(`${EV}/curves/keratitis_diffusion.json`) || rd(`${EV}/curves/keratitis_baseline.json`);
  const bins = cal ? cal.calibration : [];
  s.addChart(pres.charts.LINE, [
    { name: "Model accuracy", labels: bins.map((b) => b.conf.toFixed(2)), values: bins.map((b) => b.acc) },
    { name: "Perfect calibration", labels: bins.map((b) => b.conf.toFixed(2)), values: bins.map((b) => b.conf) },
  ], { x: 4.75, y: 1.7, w: 3.95, h: 4.95, chartColors: [HEX.accent1, "B5C0D3"], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 7,
    valAxisMinVal: 0, valAxisMaxVal: 1, valGridLine: { color: "E1E7F2", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "b", showTitle: true, title: "Calibration: keratitis model",
    showCatAxisTitle: true, catAxisTitle: "stated confidence", catAxisTitleColor: "33425C", catAxisTitleFontSize: 11,
    ...chartText(false), objectName: "cal_chart" });
  const refj = rd(`${EV}/curves/ulcer_region_crop.json`);
  // one point per distinct referral rate (several low cut-offs refer nobody and would repeat "0%")
  const seenRate = new Set();
  const ref = (refj ? refj.referral : []).filter((r) => {
    const k = Math.round(r.referral_rate * 100);
    if (r.accuracy_kept === null || r.referral_rate >= 0.96 || seenRate.has(k)) return false;
    seenRate.add(k); return true;
  });
  s.addChart(pres.charts.LINE, [{ name: "Accuracy on kept cases", labels: ref.map((r) => `${Math.round(r.referral_rate * 100)}%`), values: ref.map((r) => r.accuracy_kept) }], {
    x: 8.85, y: 1.7, w: 3.8, h: 4.95, chartColors: [HEX.accent3], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
    valAxisMinVal: 0.5, valAxisMaxVal: 1, valGridLine: { color: "E1E7F2", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: false, showTitle: true, title: "Referring more raises accuracy (ulcer)",
    showCatAxisTitle: true, catAxisTitle: "share of cases referred", catAxisTitleColor: "33425C", catAxisTitleFontSize: 11,
    ...chartText(false), objectName: "ref_chart" });
  s.addNotes("A screening tool must know when it does not know. Conformal sets hit their 95% target, the deployed model's stated confidence matches its real accuracy, and the right chart shows the safety trade-off: the more uncertain cases we refer, the more accurate the remaining calls are. Uncertain cases are referred, never called normal.");

  // ================================================================ 13. Explanations & failures
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Results" });
  kicker(s, "RQ4 · EXPLANATIONS", true);
  s.addText("Does it look at the right place?", { placeholder: "title" });
  screen(s, IMG("shot_explain.png"), 0.8, 1.85, 6.25, 4.2, true, "Portal result: cornea found by the U-Net and the Grad-CAM++ heat-map, with Bengaluru referrals below");
  note(s, "Portal output: the cornea found by the U-Net (left) and the Grad-CAM++ heat-map (right).", 0.7, 6.3, 6.45, 0.45, true);
  [["67%", "of the ulcer model's heat-map lies inside the cornea, against 56% if it were spread at random"],
   ["2%", "of the heat-map falls on the ulcer itself, which fills 4% of the image: it reads the cornea, not the lesion"]].forEach(([n, l], i) => {
    const y = 1.75 + i * 1.2;
    s.addText(n, { x: 7.6, y, w: 1.6, h: 0.8, fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: oname("xn") });
    s.addText(l, { x: 9.25, y: y + 0.02, w: 3.4, h: 1.0, fontSize: 14, color: C.background1, valign: "top", margin: 0, isTextBox: true, objectName: oname("xl") });
  });
  s.addText("Confident mistakes we show, not hide", { x: 7.6, y: 4.3, w: 5.0, h: 0.4, fontSize: 16, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "fail_h" });
  [["fail_keratitis.png", "Herpes read as Other (70%)"], ["fail_ulcer_pattern.png", "Ulcer pattern 1 read as 0 (94%)"], ["fail_trachoma_tf.png", "Trachoma sign missed (98%)"]].forEach(([f, t], i) => {
    const x = 7.75 + i * 1.65;
    irisFrame(s, IMG(f), x, 4.85, 1.1, HEX.accent3, "Misclassified test image with Grad-CAM++ overlay");
    s.addText(t, { x: x - 0.25, y: 6.05, w: 1.6, h: 0.55, fontSize: 11, color: SOFT, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: oname("fcap") });
  });
  s.addNotes("RQ4, stated honestly: two-thirds of the heat-map falls inside the cornea, against 56% expected by chance, so the model reads the right part of the eye. But only 2% falls on the ulcer lesion itself, which fills 4% of the image, so it does not point at the lesion. We found this after fixing an inverted ulcer label file. We also show the most confident mistakes; these are the cases the referral gate is built to catch.");

  // ================================================================ 14. Portal
  pres.addSection({ title: "Portal" });
  divider("04", "Seeing it work", "The clinic portal, guided capture of both eyes, the AI assistant, and a live demo.",
    ["Portal", "Guided capture", "AI assistant", "Live demo"], "iris_grey.png",
    "Section four: seeing it work. The portal, the new guided capture, the AI assistant, and then the live demo.", "Portal");
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Portal" });
  kicker(s, "THE PORTAL", false);
  s.addText("A working clinic portal", { placeholder: "title" });
  screen(s, IMG("shot_dashboard.png"), 0.8, 1.85, 7.4, 3.92, false, "Doctor dashboard with patient, screening, referral and review counts");
  note(s, "Doctor dashboard: screenings, referrals and the review queue at a glance.", 0.7, 6.0, 7.6, 0.4, false);
  [[I.idcard, "Login with doctor and admin roles"], [I.users, "Patients, cases and follow-up timeline"], [I.layers, "Layer-by-layer screening"],
   [I.map, "Bengaluru referral with Maps links"], [I.file, "PDF report for every case"], [I.images, "Diffusion image generator"],
   [I.chart, "Live evaluation dashboard"], [I.comments, "AI assistant with voice"], [I.laptop, "Runs offline on a laptop CPU"]].forEach(([ic, t], i) => {
    const y = 1.78 + i * 0.52;
    iconDisc(s, ic, 8.75, y, 0.44, i % 2 ? HEX.accent4 : HEX.accent1);
    s.addText(t, { x: 9.35, y, w: 3.3, h: 0.44, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: oname("feat") });
  });
  s.addNotes("This is not only a model but a working clinic portal: doctors log in, register patients, run screenings, review cases, download a PDF report and refer patients to real Bengaluru eye hospitals with map links. It all runs offline on a laptop.");

  // ================================================================ 15. Guided capture
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Portal" });
  kicker(s, "NEW · GUIDED CAPTURE", true);
  s.addText("Right eye, then left, like a face check", { placeholder: "title" });
  screen(s, IMG("shot_capture.png"), 0.8, 1.85, 3.75, 4.81, true, "Guided capture: eye in the guide circle, focus bar green, all checks passed");
  [[I.bullseye, "Guide circle and step chips", "right eye, then left; each saved as its own case"],
   [I.hand, "Auto-capture", "fires once the eye is sharp and steady"],
   [I.sliders, "Focus meter", "uses the same test as the quality gate"],
   [I.magic, "Focus peaking", "sharp edges light up green on the preview"]].forEach(([ic, h, d], i) => {
    const x = 5.05 + (i % 2) * 3.85, y = 1.8 + Math.floor(i / 2) * 1.0;
    iconDisc(s, ic, x, y, 0.62, HEX.accent5);
    s.addText(h, { x: x + 0.8, y: y - 0.02, w: 2.9, h: 0.35, fontSize: 15, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("gch") });
    s.addText(d, { x: x + 0.8, y: y + 0.33, w: 2.9, h: 0.5, fontSize: 12, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: oname("gcd") });
  });
  // eye check, rebuilt natively so the message is readable: the real uploaded image + the portal's exact text
  panel(s, 5.05, 3.95, 7.6, 2.8, PANEL);
  s.addShape(pres.shapes.RECTANGLE, { x: 5.33, y: 4.2, w: 1.72, h: 2.24, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" }, objectName: "doc_bg" });
  s.addImage({ path: IMG("not_an_eye.png"), x: 5.35, y: 4.22, w: 1.68, h: 2.2, altText: "Uploaded image: a scanned laboratory report, not an eye", objectName: "doc_img" });
  s.addText("Eye check", { x: 7.35, y: 4.15, w: 5.0, h: 0.4, fontSize: 17, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: "gate_h" });
  s.addText("This does not look like an eye image. Please upload a clear anterior-eye / cornea photograph for prediction.",
    { x: 7.35, y: 4.62, w: 5.05, h: 1.0, fontSize: 14, bold: true, color: "B42318", fill: { color: "FDE8E6" }, valign: "middle", margin: [6, 10, 6, 10],
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, isTextBox: true, objectName: "gate_msg" });
  s.addText("A scanned lab report is refused before any prediction is made: each upload is compared with 903 real eye photos.",
    { x: 7.35, y: 5.75, w: 5.05, h: 0.75, fontSize: 12, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: "gate_note" });
  s.addNotes("New this week: guided capture. Like a face-verification flow, it photographs the right eye, then the left, and captures automatically once the image is sharp and steady. The focus meter uses exactly the same test as the server's quality gate. Below: the eye check refuses anything that is not an eye.");

  // ================================================================ 15b. AI assistant
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Portal" });
  kicker(s, "NEW · AI ASSISTANT", true);
  s.addText("An assistant that explains, by voice", { placeholder: "title" });
  screen(s, IMG("shot_assistant.png"), 0.8, 1.85, 4.37, 4.85, true, "AI assistant page: a patient question about case 5, the answer with the referral hospitals, and the voice bar");
  [[I.comments, "Answers every patient question", "the case's result, next steps and hospitals; 50+ common eye-health questions; anything else with Claude online"],
   [I.mic, "Voice in, voice out", "speak a question, hear the answer: English, Hindi, Kannada, Tamil, Telugu"],
   [I.shield, "Safe by design", "no diagnosis or medicine names; emergencies get first aid; treatment notes stay with clinicians"],
   [I.robot, "Two engines", "Claude Opus 5.5 online with a safety fallback; a grounded offline assistant when there is no internet"]].forEach(([ic, h, d], i) => {
    const y = 1.85 + i * 1.12;
    iconDisc(s, ic, 5.65, y, 0.62, HEX.accent5);
    s.addText(h, { x: 6.45, y: y - 0.02, w: 6.2, h: 0.35, fontSize: 15, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("aih") });
    s.addText(d, { x: 6.45, y: y + 0.33, w: 6.2, h: 0.62, fontSize: 12, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: oname("aid") });
  });
  s.addText("Checked by 88 automated tests, including red flags, never prescribing and the offline fallback.",
    { x: 5.65, y: 6.35, w: 7.0, h: 0.4, fontSize: 12, italic: true, color: SOFT, margin: 0, isTextBox: true, objectName: "ai_note" });
  s.addNotes("New: the AI assistant. A patient or doctor picks a case and asks in plain words, by typing or by voice, in five languages, and hears the answer read aloud. It explains the result, what to do next and which hospital to visit, and answers common eye-health questions. It never diagnoses or names medicines; urgent symptoms such as a chemical splash get first-aid advice and an urgent-care message. Online it uses Claude Opus 5.5; offline a grounded assistant answers from the case facts and a checked question bank.");

  // ================================================================ 16. Live demo
  s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Portal" });
  kicker(s, "LIVE DEMO", false);
  s.addText("Live demo", { placeholder: "title" });
  const demo = ["Log in as a doctor", "Guided capture of both eyes", "Watch the layer-by-layer analysis", "Read confidence, uncertainty and heat-map", "Referral, PDF and the AI assistant"];
  s.addShape(pres.shapes.LINE, { x: 1.1, y: 2.2, w: 10.0, h: 0, line: { color: "B5C0D3", width: 2, dashType: "dash" }, objectName: "demo_line" });
  demo.forEach((t, i) => {
    const x = 0.7 + i * 2.5;
    s.addShape(pres.shapes.OVAL, { x: x + 0.05, y: 1.8, w: 0.8, h: 0.8, fill: { color: HEX.accent1 }, line: { color: "FFFFFF", width: 2 }, objectName: oname("dot") });
    s.addText(String(i + 1), { x: x + 0.05, y: 1.8, w: 0.8, h: 0.8, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: oname("dotn") });
    s.addText(t, { x, y: 2.75, w: 2.25, h: 0.75, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: oname("demot") });
  });
  screen(s, IMG("shot_pred.png"), 0.8, 3.85, 4.95, 2.92, false, "Result screen: low confidence, referral advised, model disagreement and the conformal prediction set");
  panel(s, 6.25, 3.75, 6.35, 3.05, HEX.lt2);
  s.addText("If something goes wrong on stage", { x: 6.55, y: 3.95, w: 5.8, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "fb_h" });
  s.addText([
    { text: "No camera: switch Image source to Sample image", options: { bullet: true, breakLine: true } },
    { text: "No internet or GPU needed: everything runs on this laptop", options: { bullet: true, breakLine: true } },
    { text: "Use http://localhost:8501; browsers block the camera on plain network addresses", options: { bullet: true } },
  ], { x: 6.55, y: 4.45, w: 5.8, h: 2.15, fontSize: 14, color: C.text1, paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true, objectName: "fb_list" });
  s.addNotes("Switch to the portal now. Log in, open New screening, choose Guided camera capture and photograph both eyes, then run the screening and walk through the layers, the result, the heat-map and the referral. The screenshot shows an honest result: low confidence, so the portal refers instead of guessing. If the camera fails, use the sample image.");

  // ================================================================ 17. Limitations
  pres.addSection({ title: "Wrap-up" });
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Wrap-up" });
  kicker(s, "LIMITATIONS", true);
  s.addText("What this prototype is not (yet)", { placeholder: "title" });
  [[I.database, "Single-site public data", "Each test set comes from one hospital, so there is no true cross-site test yet."],
   [I.chart, "Keratitis is still hard", "0.42 on average across seeds (best 0.488); the test sets are small."],
   [I.ban, "Not a medical device", "No clinical validation, ethics approval or prospective study yet."],
   [I.user, "Placeholder doctors", "The referral hospitals are real; the doctor names are clearly marked samples."],
   [I.search, "Heat-maps miss the lesion", "They land on the cornea, but only 2% falls on the ulcer itself."],
   [I.eye, "Eye-check margin", "A scanned report scored 0.61 against a 0.60 limit; it needs more non-eye examples."]].forEach(([ic, h, b], i) => {
    const x = 0.7 + (i % 2) * 6.1, y = 1.75 + Math.floor(i / 2) * 1.65;
    panel(s, x, y, 5.8, 1.45, PANEL);
    iconDisc(s, ic, x + 0.25, y + 0.3, 0.8, i < 3 ? HEX.accent3 : HEX.accent4);
    s.addText(h, { x: x + 1.3, y: y + 0.16, w: 4.3, h: 0.4, fontSize: 17, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: oname("lh") });
    s.addText(b, { x: x + 1.3, y: y + 0.58, w: 4.3, h: 0.75, fontSize: 14, color: SOFT, valign: "top", margin: 0, isTextBox: true, objectName: oname("lb") });
  });
  s.addNotes("We are clear about the limits. The test sets are public and single-site, keratitis is still hard, and this is a research prototype, not a medical device. The referral doctors are placeholders, two experiments were cut short when GPU access ended, and the eye check needs more non-eye training examples.");

  // ================================================================ 18. Next steps & close
  s = pres.addSlide({ masterName: "HERO", sectionTitle: "Wrap-up" });
  s.addText("NEXT STEPS", { x: 0.75, y: 0.55, w: 6, h: 0.32, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, isTextBox: true, objectName: "n_kicker" });
  s.addText("What comes next", { x: 0.75, y: 0.9, w: 6.6, h: 0.85, fontFace: THEME.headFontFace, fontSize: 36, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "n_title" });
  s.addText([
    { text: "Partner hospital and ethics approval", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Hospital data and multi-site validation", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Pilot at a screening camp", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Teach the heat-maps to find the lesion", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Mobile capture app for vision centres", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Clinician review of the referral rules", options: { bullet: { type: "number" } } },
  ], { x: 0.75, y: 1.95, w: 6.3, h: 3.1, fontSize: 17, color: C.background1, paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true, objectName: "n_list" });
  panel(s, 0.75, 5.3, 6.3, 1.45, PANEL);
  s.addText("A complete, evaluated research prototype: it screens three eye diseases, shows where it looked, says how sure it is, and refers patients to a specialist.",
    { x: 1.0, y: 5.4, w: 5.85, h: 1.25, fontSize: 16, color: C.background1, valign: "middle", margin: 0, isTextBox: true, objectName: "n_concl" });
  s.addImage({ path: IMG("hero_iris.png"), x: 7.75, y: 0.45, w: 5.2, h: 5.2, altText: "Stylised iris scan", objectName: "close_iris" });
  s.addText("Thank you · Questions?", { x: 7.3, y: 5.85, w: 5.95, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.accent2, align: "center", margin: 0, isTextBox: true, objectName: "thanks" });
  s.addNotes("Close with the next steps: a hospital partner and ethics approval come first, because everything clinical depends on them. Then summarise in one sentence and invite questions.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);

  // a gentle fade between every slide (pptxgenjs has no transition API, so add it to each slide's XML)
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(OUT));
  const TR = '<p:transition spd="med"><p:fade/></p:transition>';
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n))) {
    let x = await zip.file(name).async("string");
    if (x.includes("<p:transition")) continue;
    if (x.includes("</p:clrMapOvr>")) x = x.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + TR);
    else x = x.replace("</p:cSld>", "</p:cSld>" + TR);
    zip.file(name, x);
  }
  // re-pack with files only: folder entries stop decks opening from OneDrive / SharePoint
  const clean = new JSZip();
  for (const [n, f] of Object.entries(zip.files)) if (!f.dir) clean.file(n, await f.async("nodebuffer"), { createFolders: false });
  fs.writeFileSync(OUT, await clean.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log("wrote", OUT);
})();
