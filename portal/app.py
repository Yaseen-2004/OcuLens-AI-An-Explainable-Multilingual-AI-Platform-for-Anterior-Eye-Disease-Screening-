"""OcuLens-AI portal - an eye-themed, interactive clinical screening CRM (demo).

Login -> dashboard -> screening/prediction -> case storage -> doctor recommendations,
+ synthetic image generation and an evaluation dashboard. Runs offline on CPU.

Run:  python -m streamlit run portal/app.py
Demo logins: admin/admin123 | dr.yaseen/doctor123 | dr.ayaan/doctor123 | dr.arfath/doctor123
"""
from __future__ import annotations

import base64
import re
import io
import json
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings  # noqa: E402
import db  # noqa: E402
import legal  # noqa: E402
import logging  # noqa: E402
from logging.handlers import RotatingFileHandler  # noqa: E402


def _setup_logging():
    """Application log in <data dir>/logs/oculens.log (rotated, 5 x 2 MB); errors never reach users' screens."""
    log = logging.getLogger("oculens")
    if not log.handlers:
        d = settings.data_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        h = RotatingFileHandler(d / "oculens.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


LOG = _setup_logging()
from eye_capture import eye_capture  # noqa: E402
from sfx import play as play_sound  # noqa: E402
import tts  # noqa: E402
import geo  # noqa: E402
import patient_portal as pp  # noqa: E402

st.set_page_config(page_title="OcuLens-AI Portal", layout="wide", initial_sidebar_state="expanded")
db.init_db()

CKPT = ROOT / "models" / "checkpoints"
EVAL = ROOT / "experiments" / "eval_final"
CURV = ROOT / "experiments" / "curves"
SAMPLES = ROOT / "portal" / "samples"
TEAM = "Syed Mohammed Yaseen · Mohammed Ayaan · Arfath Khan"

# ---- design palette (iris / clinical) -------------------------------------------------
PAL = {"ink": "#0A2A33", "teal": "#0F7C80", "teal2": "#0B6468", "iris": "#3B5BA5",
       "amber": "#E8A33D", "coral": "#E4572E", "green": "#2E9E5B", "mint": "#EAF6F5",
       "line": "#DCEBEA", "muted": "#5B7177"}
# per-class colours for charts
CLS_COLORS = ["#0F7C80", "#E8A33D", "#3B5BA5", "#E4572E", "#6C5B9E", "#2E9E5B"]
MI_FLAG = 0.12  # mutual-information above this = flag "high model disagreement"

LABELS = {"BK": "Bacterial keratitis", "FK": "Fungal keratitis", "HSK": "Herpes simplex keratitis",
          "other_corneal_abnormalities": "Other corneal abnormality", "0": "Grade 0", "1": "Grade 1", "2": "Grade 2"}
TF_LABELS = {"0": "No TF", "1": "Trachomatous inflammation (TF)"}
TASKS = {"Infectious keratitis": "keratitis", "Corneal ulcer pattern": "ulcer_pattern", "Trachoma (TF)": "trachoma_tf"}
TASK_NAME = {v: k for k, v in TASKS.items()}
SAMPLE_FILE = {"keratitis": "keratitis_sample.jpg", "ulcer_pattern": "ulcer_sample.jpg", "trachoma_tf": "trachoma_sample.jpg"}


NORMAL = "NORMAL"
NORMAL_TEXT = "No signs of disease (healthy-looking eye)"


def label_of(task, c):
    if c == NORMAL:
        return NORMAL_TEXT
    return TF_LABELS.get(c, c) if task == "trachoma_tf" else LABELS.get(c, c)


# ============================================================= styling
def inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family:'Inter',system-ui,sans-serif; }
h1,h2,h3 { font-family:'Sora','Inter',sans-serif; color:#0A2A33; letter-spacing:-.01em; }
.block-container { padding-top:3.4rem; max-width:1280px; }
#MainMenu, footer { visibility:hidden; }

/* hero */
.ocu-hero { position:relative; overflow:hidden; border-radius:20px; padding:22px 28px; margin-bottom:20px;
  background:linear-gradient(120deg,#072B33 0%,#0F7C80 55%,#2BA6AA 100%); background-size:180% 180%;
  animation:shift 14s ease infinite; box-shadow:0 10px 32px rgba(11,46,58,.28); }
@keyframes shift { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
.ocu-hero:after { content:""; position:absolute; right:-40px; top:-60px; width:220px; height:220px; border-radius:50%;
  background:radial-gradient(circle at 50% 50%, rgba(255,255,255,.18) 0 30%, rgba(59,91,165,.18) 31% 48%, transparent 60%); }
.ocu-hero h1 { color:#fff !important; margin:0; font-size:1.65rem; }
.ocu-hero p { color:#CDEDEC; margin:.3rem 0 0; font-size:.96rem; max-width:80%; }

/* KPI cards */
.kpi { background:#fff; border:1px solid #E3EFEE; border-left:5px solid var(--a,#0F7C80); border-radius:16px;
  padding:14px 16px; box-shadow:0 3px 14px rgba(11,46,58,.06); height:100%; }
.kpi .v { font-family:'Sora'; font-size:1.7rem; font-weight:700; color:#0A2A33; line-height:1.1; }
.kpi .l { color:#5B7177; font-size:.82rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
.kpi .ic { font-size:1.1rem; }

/* pills */
.pill { display:inline-block; padding:3px 12px; border-radius:999px; font-size:.76rem; font-weight:700; }
.pill-refer { background:#FCE7E1; color:#C0392B; } .pill-ok { background:#E4F4E9; color:#2E7D43; }
.pill-mut { background:#EAF1F1; color:#5B7177; } .pill-amber { background:#FBEFD8; color:#B57413; }

/* card */
.soft { background:#fff; border:1px solid #E3EFEE; border-radius:16px; padding:16px 18px;
  box-shadow:0 3px 14px rgba(11,46,58,.05); }

/* buttons */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button { border-radius:11px; font-weight:600; border:0;
  background:linear-gradient(90deg,#0F7C80,#12A3A8); color:#fff; transition:transform .06s ease, box-shadow .2s ease; }
.stButton>button:hover, .stFormSubmitButton>button:hover { transform:translateY(-1px); box-shadow:0 6px 16px rgba(15,124,128,.35); color:#fff; }

/* sidebar */
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#072B33,#0B3A44); }
section[data-testid="stSidebar"] * { color:#DCEBEA !important; }
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label { padding:7px 10px; border-radius:10px; margin:1px 0; }
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover { background:rgba(255,255,255,.07); }

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap:6px; }
.stTabs [data-baseweb="tab"] { border-radius:10px 10px 0 0; padding:8px 16px; font-weight:600; }
.stTabs [aria-selected="true"] { background:#EAF6F5; color:#0F7C80; }

/* stepper */
.step { display:inline-block; padding:6px 13px; margin:3px 4px 3px 0; border-radius:999px; font-size:.8rem; font-weight:600;
  background:#EAF6F5; color:#0F7C80; border:1px solid #CfE7E6; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #E3EFEE; border-radius:14px; padding:12px 14px; }
div[data-testid="stMetricValue"] { color:#0F7C80; }

/* ---- biometric scan animation ---- */
.scanbox { position:relative; border-radius:16px; overflow:hidden; box-shadow:0 10px 30px rgba(11,46,58,.3);
  max-width:520px; margin:6px auto; }
.scanbox img { display:block; width:100%; filter:saturate(1.05) contrast(1.03); }
.scanbox .tint { position:absolute; inset:0; background:linear-gradient(180deg,rgba(7,43,51,.15),rgba(7,43,51,.4)); }
.scanbox .grid { position:absolute; inset:0; background:
  repeating-linear-gradient(0deg,rgba(25,227,227,.10) 0 1px,transparent 1px 24px),
  repeating-linear-gradient(90deg,rgba(25,227,227,.10) 0 1px,transparent 1px 24px); }
.scanbox .line { position:absolute; left:0; right:0; height:3px;
  background:linear-gradient(90deg,transparent,#19E3E3,transparent);
  box-shadow:0 0 16px 5px rgba(25,227,227,.75); animation:scanmove 1.7s ease-in-out infinite; }
@keyframes scanmove { 0%{top:3%} 50%{top:95%} 100%{top:3%} }
.scanbox .ring { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; }
.scanbox .ring i { width:48%; padding-bottom:48%; border:2px solid rgba(25,227,227,.6); border-radius:50%;
  box-shadow:0 0 22px rgba(25,227,227,.4) inset; animation:ringpulse 1.7s ease-in-out infinite; }
@keyframes ringpulse { 0%,100%{transform:scale(.88);opacity:.45} 50%{transform:scale(1.04);opacity:1} }
.scanbox .corner { position:absolute; width:26px; height:26px; border:3px solid #19E3E3; }
.scanbox .c1{top:10px;left:10px;border-right:0;border-bottom:0}
.scanbox .c2{top:10px;right:10px;border-left:0;border-bottom:0}
.scanbox .c3{bottom:10px;left:10px;border-right:0;border-top:0}
.scanbox .c4{bottom:10px;right:10px;border-left:0;border-top:0}
.scanbox .tag { position:absolute; bottom:12px; left:0; right:0; text-align:center; color:#DBFFFF;
  font-weight:700; letter-spacing:.16em; font-size:.8rem; text-shadow:0 1px 6px rgba(0,0,0,.65);
  animation:blink 1s step-start infinite; }
@keyframes blink { 50%{opacity:.45} }
</style>
        """,
        unsafe_allow_html=True,
    )


EYE_SVG = """
<svg width="{s}" height="{s}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4 32C11 19 21 13 32 13s21 6 28 19c-7 13-17 19-28 19S11 45 4 32Z" fill="#0F7C80" opacity=".15"/>
<path d="M4 32C11 19 21 13 32 13s21 6 28 19c-7 13-17 19-28 19S11 45 4 32Z" stroke="{c}" stroke-width="3"/>
<circle cx="32" cy="32" r="11" fill="#3B5BA5"/><circle cx="32" cy="32" r="11" stroke="{c}" stroke-width="2"/>
<circle cx="32" cy="32" r="4.5" fill="#072B33"/><circle cx="28.5" cy="28.5" r="2" fill="#fff"/>
</svg>
"""


def hero(title, subtitle):
    st.markdown(f"<div class='ocu-hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def kpi(col, value, label, icon, accent):
    col.markdown(f"<div class='kpi' style='--a:{accent}'>"
                 f"<div class='v'>{value}</div><div class='l'>{label}</div></div>", unsafe_allow_html=True)


def pill(text, kind):
    return f"<span class='pill pill-{kind}'>{text}</span>"


def stepper(active):
    steps = ["1 Quality", "2 Cornea", "3 Classify", "4 Confidence", "5 Explain"]
    html = "".join(f"<span class='step' style='{'opacity:1' if i<=active else 'opacity:.4'}'>{s}</span>" for i, s in enumerate(steps))
    st.markdown(html, unsafe_allow_html=True)


def scanning_html(img, msg="ANALYSING CORNEA"):
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f"<div class='scanbox'><img src='data:image/png;base64,{b64}'/>"
            "<div class='tint'></div><div class='grid'></div>"
            "<span class='corner c1'></span><span class='corner c2'></span><span class='corner c3'></span><span class='corner c4'></span>"
            "<div class='ring'><i></i></div><div class='line'></div>"
            f"<div class='tag'>{msg} &hellip;</div></div>")


# ============================================================= models + inference
@st.cache_resource(show_spinner=False)
def get_cfg():
    from oculens.config import load_config
    return load_config()


@st.cache_resource(show_spinner=True)
def load_classifier(task):
    from oculens.models.classifier import load_checkpoint
    return load_checkpoint(CKPT / f"{task}_efficientnet_b0.pt")


@st.cache_resource(show_spinner=True)
def load_ensemble(task):
    """The deep-ensemble members for a task: files {task}_efficientnet_b0_s<N>.pt (keratitis has 5)."""
    import re
    from oculens.models.classifier import load_checkpoint
    pre = f"{task}_efficientnet_b0_"
    members = sorted(p for p in CKPT.glob(f"{task}_efficientnet_b0_s*.pt")
                     if re.fullmatch(r"s\d+\.pt", p.name[len(pre):]))
    return [load_checkpoint(p) for p in members]


# Lead classifier per task. Keratitis uses the diffusion-augmented model: in our
# evaluation it reached the best balanced accuracy (0.488) and calibration (ECE 0.047),
# beating both the baseline and a 10-model deep ensemble.
PRIMARY_CKPT = {"keratitis": "keratitis_efficientnet_b0_syn.pt"}


@st.cache_resource(show_spinner=True)
def load_primary(task):
    """(model, meta), is_diffusion. Falls back to the baseline checkpoint if the
    task has no dedicated primary model or the file is missing."""
    from oculens.models.classifier import load_checkpoint
    name = PRIMARY_CKPT.get(task)
    if name and (CKPT / name).exists():
        return load_checkpoint(CKPT / name), True
    return load_checkpoint(CKPT / f"{task}_efficientnet_b0.pt"), False


@st.cache_resource(show_spinner=False)
def load_segmenter():
    from oculens.models.segmenter import Segmenter
    p = CKPT / "unet_cornea.pt"
    return Segmenter(str(p)) if p.exists() else None


def run_inference(img_rgb, task, use_ensemble=True):
    """Returns (probs, classes, meta, x, gradcam_model, n_members, mi).
    The lead prediction comes from the task's primary model (keratitis: the
    diffusion-augmented EfficientNet-B0, our best model). Where a seed ensemble
    exists, its members' disagreement gives the mutual-information uncertainty;
    n_members is how many models that estimate used. Grad-CAM uses the lead model."""
    import torch
    from oculens.preprocessing.transforms import build_transforms
    cfg = get_cfg()
    (pmodel, pmeta), is_diff = load_primary(task)
    meta = dict(pmeta)
    meta["diffusion_primary"] = is_diff
    size = meta.get("image_size", 224)
    classes = meta["classes"]
    tf = build_transforms(train=False, image_size=size, cfg=cfg["preprocessing"])
    x = tf(img_rgb).unsqueeze(0)
    with torch.no_grad():                  # lead prediction
        pmodel.eval()
        probs = torch.softmax(pmodel(x) / pmeta.get("temperature", 1.0), 1).numpy()[0]  # (C,)
    # Epistemic uncertainty from the deep ensemble's disagreement (if present).
    mi, n_unc = 0.0, 1
    members = load_ensemble(task) if use_ensemble else []
    if len(members) > 1:
        ps = []
        with torch.no_grad():
            for m, mt in members:
                m.eval()
                ps.append(torch.softmax(m(x) / mt.get("temperature", 1.0), 1).numpy())
        P = np.concatenate(ps, axis=0)     # (M, C)
        mean = P.mean(0)
        eps = 1e-12                        # mutual information = total entropy - mean member entropy
        total = -np.sum(mean * np.log(mean + eps))
        expected = float(np.mean([-np.sum(p * np.log(p + eps)) for p in P]))
        mi = float(total - expected)
        n_unc = len(members)
    return probs, classes, meta, x, pmodel, n_unc, mi


@st.cache_resource(show_spinner=False)
def load_eye_gate():
    """Reference-embedding bank + fixed embedder for the 'is this an eye image?' gate.
    The bank holds normalised EfficientNet features of real anterior-eye images across all
    three tasks; an upload far from every reference (in cosine distance) is out-of-distribution."""
    from oculens.models.classifier import load_checkpoint
    p = CKPT / "eye_reference.npz"
    if not p.exists():
        return None
    z = np.load(p)
    model, meta = load_checkpoint(CKPT / "keratitis_efficientnet_b0_syn.pt")
    model.eval()
    return {"ref": z["ref"].astype("float32"), "threshold": float(z["threshold"]),
            "image_size": int(z["image_size"]), "model": model}


def eye_distance(img_rgb):
    """Nearest-reference cosine distance to the eye-image manifold (lower = more eye-like).
    Returns (distance, threshold), or (None, None) if the gate file is unavailable."""
    import torch
    g = load_eye_gate()
    if g is None:
        return None, None
    from oculens.preprocessing.transforms import build_transforms
    tf = build_transforms(train=False, image_size=g["image_size"], cfg=get_cfg()["preprocessing"])
    x = tf(img_rgb).unsqueeze(0)
    with torch.no_grad():
        f = g["model"].forward_features(x)
        v = torch.nn.functional.adaptive_avg_pool2d(f, 1).flatten(1)
        v = torch.nn.functional.normalize(v, dim=1).numpy()[0]
    return float(1.0 - (g["ref"] @ v).max()), g["threshold"]


@st.cache_resource(show_spinner=False)
def load_normal_gate():
    p = CKPT / "normal_gate.npz"
    g = load_eye_gate()
    if not p.exists() or g is None:
        return None
    z = np.load(p)
    return {"coef": z["coef"], "intercept": z["intercept"], "threshold": float(z["threshold"]),
            "image_size": int(z["image_size"]), "model": g["model"]}


def normal_check(img_rgb):
    """Probability that the photo shows a healthy eye, and the threshold above which it is reported as normal.
    The photo is shrunk to the same thumbnail size as in training (see oculens.quality.normal_gate).
    Returns (None, None) when the check is unavailable."""
    from oculens.quality.normal_gate import features, p_normal, thumbnail
    g = load_normal_gate()
    if g is None:
        return None, None
    f = features(g["model"], [thumbnail(img_rgb)], get_cfg()["preprocessing"], g["image_size"])
    return float(p_normal(g, f)[0]), g["threshold"]


def gradcam_overlay(model, x, disp):
    import cv2
    from oculens.explain.gradcam import GradCAM
    eng = GradCAM(model, plus_plus=True)
    try:
        cam, _ = eng(x)
    finally:
        eng.remove()
    h, w = disp.shape[:2]
    cam = cv2.resize(cam.astype(np.float32), (w, h))
    cam = (cam - cam.min()) / (np.ptp(cam) + 1e-8)
    heat = cv2.cvtColor(cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    return (0.55 * disp + 0.45 * heat).astype(np.uint8)


def cornea_overlay(img):
    try:
        seg = load_segmenter()
        if seg is None:
            return None
        import cv2
        mask = seg.predict(img)
        edges = cv2.dilate(mask, np.ones((3, 3), np.uint8)) - mask
        ov = img.copy()
        ov[mask.astype(bool)] = (0.7 * ov[mask.astype(bool)] + np.array([0, 90, 0])).clip(0, 255)
        ov[edges.astype(bool)] = [0, 255, 0]
        return ov
    except Exception:  # noqa: BLE001
        return None


@st.cache_resource(show_spinner=False)
def load_diffusion():
    p = CKPT / "ddpm_keratitis_64.pt"
    if not p.exists():
        return None
    import torch
    from oculens.generative.ddpm import CondUNet, Diffusion
    ck = torch.load(p, map_location="cpu", weights_only=False)
    classes, size = ck["classes"], ck["size"]
    model = CondUNet(len(classes))
    model.load_state_dict(ck["state_dict"])
    model.eval()
    return Diffusion(model, timesteps=1000, device="cpu"), classes, size


def generate_images(class_idx, n, steps, guidance):
    import torch
    diff, classes, size = load_diffusion()
    y = torch.full((n,), class_idx, dtype=torch.long)
    imgs = diff.sample(y, size, guidance=guidance, steps=steps)
    return ((imgs.clamp(-1, 1) + 1) / 2 * 255).byte().permute(0, 2, 3, 1).numpy()


def augment_samples(cls, n):
    import random
    from oculens.preprocessing.transforms import build_transforms, denormalize
    cfg = get_cfg()
    base = ROOT / "data" / "cache" / "infectious_keratitis_figshare"
    files = []
    if base.exists():
        for d in base.rglob(cls):
            if d.is_dir():
                files += list(d.rglob("*.jpg"))
    if not files:
        return [], 0
    tf = build_transforms(train=True, image_size=224, cfg=cfg["preprocessing"])
    return [denormalize(tf(np.array(Image.open(random.choice(files)).convert("RGB")))) for _ in range(n)], len(files)


# ---- interactive charts (plotly)
def gauge_fig(pct, refer):
    import plotly.graph_objects as go
    color = PAL["coral"] if refer else PAL["green"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=pct, number={"suffix": "%", "font": {"size": 34, "color": PAL["ink"]}},
        gauge={"axis": {"range": [0, 100], "tickcolor": PAL["muted"]},
               "bar": {"color": color, "thickness": 0.28},
               "bgcolor": "white", "borderwidth": 0,
               "steps": [{"range": [0, 50], "color": "#F4F8F8"}, {"range": [50, 80], "color": "#EAF6F5"}, {"range": [80, 100], "color": "#DCEFEE"}]}))
    fig.update_layout(height=230, margin=dict(l=40, r=40, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")  # room for the "100" tick
    return fig


def probbar_fig(labels, probs):
    import plotly.graph_objects as go
    order = np.argsort(probs)
    labs = [labels[i] for i in order]
    vals = [float(probs[i]) * 100 for i in order]
    cols = [CLS_COLORS[i % len(CLS_COLORS)] for i in order]
    fig = go.Figure(go.Bar(x=vals, y=labs, orientation="h", marker_color=cols,
                           text=[f"{v:.1f}%" for v in vals], textposition="outside"))
    fig.update_layout(height=max(180, 55 * len(labs)), margin=dict(l=10, r=30, t=8, b=8),
                      xaxis=dict(range=[0, 108], showgrid=False, visible=False),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=PAL["ink"]))
    return fig


def donut_fig(d):
    import plotly.graph_objects as go
    fig = go.Figure(go.Pie(labels=list(d.keys()), values=list(d.values()), hole=0.58,
                           marker=dict(colors=CLS_COLORS)))
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.1), font=dict(color=PAL["ink"]))
    return fig


def _load_json(p):
    try:
        return json.loads(Path(p).read_text().replace("NaN", "null")) if Path(p).exists() else None
    except Exception:  # noqa: BLE001
        return None


def _r(v):
    try:
        return round(float(v), 3)
    except Exception:  # noqa: BLE001
        return None


PLOT_CFG = {"displayModeBar": False}


# ============================================================= login
LOGIN_CSS = """
<style>
.lg-art { position:relative; border-radius:28px; overflow:hidden; min-height:640px; padding:38px 36px 84px; color:#fff;
  background:radial-gradient(circle at 75% 30%, rgba(255,214,153,.28), transparent 38%),
             linear-gradient(150deg,#061F26 0%,#0A3D45 40%,#0F7C80 85%); box-shadow:0 18px 44px rgba(6,31,38,.35); }
.lg-art h1 { color:#fff !important; font-size:2.6rem; margin:0; }
.lg-art .tag { font-size:1.15rem; color:#BFF5EE; margin-top:6px; font-weight:600; }
.lg-art .kick { letter-spacing:.24em; font-size:.75rem; font-weight:800; color:#FFD699; }
.lg-eye { position:absolute; right:-40px; bottom:-40px; width:380px; height:380px; }
.lg-eye .ring { position:absolute; inset:0; border-radius:50%; border:2px dashed rgba(191,245,238,.35); animation:lgspin 30s linear infinite; }
.lg-eye .ring.b { inset:30px; border:2px solid rgba(255,214,153,.45); animation-duration:16s; animation-direction:reverse; }
.lg-eye .ring.c { inset:62px; border:1px solid rgba(191,245,238,.3); }
.lg-eye .iris { position:absolute; inset:92px; border-radius:50%;
  background:conic-gradient(from 0deg,#3B5BA5,#5FC9C0,#2B8C8E,#3B5BA5,#7FD8CF,#3B5BA5);
  box-shadow:0 0 60px rgba(95,201,192,.55), inset 0 0 30px rgba(0,0,0,.35); animation:lgspin 24s linear infinite; }
.lg-eye .pupil { position:absolute; inset:150px; border-radius:50%; background:#04161B; box-shadow:0 0 0 6px rgba(4,22,27,.4);
  animation:lgpupil 5s ease-in-out infinite; }
.lg-eye .glint { position:absolute; width:22px; height:22px; border-radius:50%; background:#fff; top:150px; left:150px; opacity:.9; }
.lg-eye .scan { position:absolute; left:40px; right:40px; height:3px; top:50%;
  background:linear-gradient(90deg,transparent,#19E3E3,transparent); box-shadow:0 0 18px 6px rgba(25,227,227,.55);
  animation:lgscan 3.2s ease-in-out infinite; }
@keyframes lgspin { to { transform:rotate(360deg) } }
@keyframes lgpupil { 0%,100% { transform:scale(1) } 50% { transform:scale(.82) } }
@keyframes lgscan { 0%,100% { top:22% } 50% { top:78% } }
.lg-feat { display:flex; flex-direction:column; gap:12px; margin-top:28px; max-width:330px; position:relative; z-index:2; }
.lg-feat div { background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.16); border-radius:16px; padding:12px 14px;
  backdrop-filter:blur(6px); }
.lg-feat b { color:#FFD699; } .lg-feat span { color:#D6F2EF; font-size:.88rem; }
.lg-foot { position:absolute; left:36px; right:36px; bottom:22px; font-size:.78rem; color:#9CCFCB; z-index:2; }
.st-key-lg_panel { background:#fff; border-radius:26px; padding:22px 24px 10px; border:1px solid #E2EEEC;
  box-shadow:0 14px 40px rgba(10,61,69,.10); }
</style>
"""


def _start_session(user):
    import datetime as _dt
    db.audit(user, "login")
    LOG.info("login %s (%s)", user.get("username"), user.get("role"))
    st.session_state["last_active"] = _dt.datetime.now().timestamp()
    st.session_state["user"] = user
    st.session_state["welcome_nonce"] = uuid.uuid4().hex   # greet once per sign-in
    if user.get("role") == "patient" and user.get("lang"):
        st.session_state["ai_lang"] = user["lang"]
    st.rerun()


def _legal_expander():
    org, ph, em = db.setting("org_name"), db.setting("support_phone"), db.setting("support_email")
    with st.expander("Terms of use · Privacy notice · Medical disclaimer"):
        st.markdown(legal.disclaimer(org) + legal.privacy(org, ph, em) + legal.terms(org, ph, em))


def login_page():
    inject_css()
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown("<div style='height:2vh'></div>", unsafe_allow_html=True)
    art, panel = st.columns([1.15, 1], gap="large")
    with art:
        st.markdown(
            "<div class='lg-art'><div class='kick'>ANTERIOR-EYE SCREENING</div><h1>OcuLens-AI</h1>"
            "<div class='tag'>See early. Act early. In your language.</div>"
            "<div class='lg-feat'><div><b>For doctors</b><br><span>Layer-by-layer AI screening, honest uncertainty, "
            "review queue and Bengaluru referrals.</span></div>"
            "<div><b>For patients</b><br><span>Self-checks at home, results in plain words, a symptom diary, reminders "
            "and a voice assistant.</span></div>"
            "<div><b>Five languages</b><br><span>English, Hindi, Kannada, Tamil and Telugu, by voice.</span></div></div>"
            "<div class='lg-eye'><span class='ring'></span><span class='ring b'></span><span class='ring c'></span>"
            "<span class='iris'></span><span class='pupil'></span><span class='glint'></span><span class='scan'></span></div>"
            f"<div class='lg-foot'>{TEAM} · v{settings.VERSION} · screening aid, not a medical device</div></div>",
            unsafe_allow_html=True)
    with panel:
        with st.container(key="lg_panel"):
            st.markdown(f"<div style='display:flex;align-items:center;gap:10px'>{EYE_SVG.format(s=44, c='#0F7C80')}"
                        "<h2 style='margin:0'>Welcome</h2></div>", unsafe_allow_html=True)
            t_in, t_new = st.tabs(["Sign in", "New patient? Create an account"])
            with t_in:
                with st.form("login"):
                    u = st.text_input("Username", placeholder="e.g. dr.yaseen")
                    pw = st.text_input("Password", type="password", placeholder="••••••••")
                    ok = st.form_submit_button("Sign in", type="primary", use_container_width=True)
                if ok:
                    name = u.strip()
                    user, msg = db.login(name.lower(), pw)
                    if not user and name != name.lower():
                        user, msg = db.login(name, pw)
                    if user:
                        _start_session(user)
                    else:
                        db.audit({"username": name, "role": "-"}, "login_failed", detail=msg)
                        st.error(msg)
                _legal_expander()
                if settings.flag("demo_mode"):
                    st.caption("Demo: doctor **dr.yaseen / doctor123** · patient **ravi / patient123** · admin **admin / admin123**")
                sup = " · ".join(x for x in (db.setting("support_phone"), db.setting("support_email")) if x)
                st.caption("Forgot your password? Ask your clinic administrator" + (f" ({sup})." if sup else "."))
            with t_new:
                with st.form("signup"):
                    name = st.text_input("Full name")
                    c = st.columns(3)
                    age = c[0].number_input("Age", 1, 110, 30)
                    sex = c[1].selectbox("Sex", ["", "M", "F", "Other"])
                    langs = {"English": "en", "हिन्दी Hindi": "hi", "ಕನ್ನಡ Kannada": "kn", "தமிழ் Tamil": "ta",
                             "తెలుగు Telugu": "te"}
                    lang = langs[c[2].selectbox("Language", list(langs))]
                    phone = st.text_input("Mobile number (optional)")
                    c2 = st.columns(2)
                    un = c2[0].text_input("Choose a username")
                    p1 = c2[1].text_input("Choose a password (6+ characters)", type="password")
                    agree = st.checkbox("I have read the privacy notice and terms below. I understand OcuLens is a "
                                        "screening aid, not a diagnosis, and I agree that my eye photos and health "
                                        "details are stored for the clinic's doctors to review.")
                    go = st.form_submit_button("Create my account", type="primary", use_container_width=True)
                if go:
                    if not name.strip():
                        st.error("Please enter your name.")
                    elif not agree:
                        st.error("Please tick the consent box to continue.")
                    else:
                        user, msg = db.register_patient(un, p1, name, age, sex, phone, lang)  # noqa: E501
                        if user:
                            db.audit(user, "patient_signup", target=f"patient {user.get('patient_id')}",
                                     detail="consent recorded")
                            _start_session(user)
                        else:
                            st.error(msg)


# ============================================================= pages
def _nav_to(page):
    st.session_state["nav"] = page


def page_dashboard():
    u = st.session_state["user"]
    hero(f"Welcome, {u['name']}", "Screening activity, referrals and the review queue at a glance.")
    s = db.stats()
    cols = st.columns(5)
    kpi(cols[0], s["patients"], "Patients", "", PAL["iris"])
    kpi(cols[1], s["cases"], "Screenings", "", PAL["teal"])
    kpi(cols[2], s["referred"], "Referred", "", PAL["coral"])
    kpi(cols[3], s["pending"], "Pending review", "", PAL["amber"])
    kpi(cols[4], s["reviewed"], "Reviewed", "", PAL["green"])
    st.write("")
    if s.get("self_checks"):
        st.markdown(f"<div class='soft' style='border-left:5px solid {PAL['amber']}'><b>{s['self_checks']} patient "
                    f"self-check(s)</b> are waiting for your review. They are marked <i>patient self-check</i> in Cases."
                    "</div>", unsafe_allow_html=True)
        st.write("")
    with st.container(key="doc_actions"):
        a = st.columns(4)
        for col, (lab, dest) in zip(a, [("New screening", "New screening"), ("Review queue", "Cases"),
                                        ("AI assistant", "AI assistant"), ("Follow-up", "Follow-up")]):
            col.button(lab, use_container_width=True, key=f"dq_{dest}", on_click=_nav_to, args=(dest,))
    st.write("")
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Recent screenings")
        rows = db.list_cases()[:12]
        if rows:
            for r in rows[:8]:
                with st.container(border=True):
                    cc = st.columns([0.6, 2, 2.2, 1.2, 1])
                    cc[0].markdown(f"**#{r['id']}**")
                    cc[1].write(r["patient_name"] or "walk-in")
                    cc[2].write(f"{TASK_NAME.get(r['task'], r['task'])}: {label_of(r['task'], r['top_label'])}")
                    cc[3].write(f"{r['top_prob']*100:.0f}%")
                    cc[4].markdown(pill("REFER", "refer") if r["referred"] else pill("routine", "ok"), unsafe_allow_html=True)
                    if (r.get("mi") or 0) > MI_FLAG:
                        cc[4].markdown(pill("uncertain", "amber"), unsafe_allow_html=True)
        else:
            st.info("No screenings yet. Open **New screening** to add one.")
    with right:
        st.subheader("By task")
        if s["by_task"]:
            st.plotly_chart(donut_fig({TASK_NAME.get(k, k): v for k, v in s["by_task"].items()}), use_container_width=True, config=PLOT_CFG)
        else:
            st.caption("No data yet.")
        pend = db.list_cases(status="pending")
        if pend and st.button(f"Review oldest pending (#{pend[-1]['id']})", use_container_width=True):
            st.session_state["view_case"] = pend[-1]["id"]
            st.session_state["nav"] = "Cases"
            st.rerun()


IMG_TYPES = ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "gif", "jfif", "ppm"]


def _open_rgb(f):
    try:
        return np.array(Image.open(f).convert("RGB"))
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read image: {e}")
        return None


EYE_NAME = {"R": "Right eye (OD)", "L": "Left eye (OS)", "": "Eye not recorded"}
_EYE_PICK = {"Not recorded": "", "Right (OD)": "R", "Left (OS)": "L"}
_CAPTURE_SETS = {"Both eyes (right, then left)": ["R", "L"], "Right eye only": ["R"], "Left eye only": ["L"]}


def _sound_on():
    return bool(st.session_state.get("sfx_on", True))


def _eye_picker(key):
    return _EYE_PICK[st.radio("Which eye is this?", list(_EYE_PICK), horizontal=True, key=key)]


def _bump_capture(task):
    """Start a fresh guided capture (new component instance, previous photos dropped)."""
    st.session_state[f"camgen_{task}"] = st.session_state.get(f"camgen_{task}", 0) + 1


def _camera_capture(task):
    """Guided right/left capture. Returns [(eye, rgb)] once photos are taken, else []."""
    gen = st.session_state.get(f"camgen_{task}", 0)
    which = st.radio("Eyes to capture", list(_CAPTURE_SETS), horizontal=True, key=f"camwhich_{task}_{gen}")
    eyes = _CAPTURE_SETS[which]
    inst = f"{task}_{gen}_{''.join(eyes)}"
    store = f"camcaps_{inst}"
    if store not in st.session_state:
        st.caption("Allow camera access when the browser asks. Each eye is photographed in turn: centre it in the "
                   "circle and hold still - it captures automatically once the focus bar is green.")
        got = eye_capture(inst, eyes, quality=get_cfg().get("quality"), sound=_sound_on())
        if not got:
            return []
        st.session_state[store] = got
        st.rerun()  # drop the camera view and show the photos in the preview column straight away
    caps = st.session_state[store]
    st.button("Retake photos", key=f"camretake_{inst}", on_click=_bump_capture, args=(task,))
    return [(e, caps[e]) for e in ("R", "L") if e in caps]


def _image_source(task):
    """Returns a list of (eye, rgb_image) pairs; eye is "R", "L" or "" when not recorded."""
    mode = st.radio("Image source", ["Upload file", "Guided camera capture", "Sample image"], horizontal=True,
                    key=f"src_{task}")
    if mode == "Upload file":
        up = st.file_uploader("Eye image (JPG, PNG, WEBP, BMP, TIFF, GIF…)", type=IMG_TYPES, key=f"up_{task}")
        eye = _eye_picker(f"eye_up_{task}")
        img = _open_rgb(up) if up is not None else None
        return [(eye, img)] if img is not None else []
    if mode == "Guided camera capture":
        return _camera_capture(task)
    sp = SAMPLES / SAMPLE_FILE.get(task, "")
    if not sp.exists():
        st.caption("No sample available for this task.")
        return []
    if st.checkbox("Use the sample image for this task", key=f"smp_{task}"):
        return [("", np.array(Image.open(sp).convert("RGB")))]
    return []


CORNEA_PANEL = [
    {"hospital": "Narayana Nethralaya", "doctor": "Dr. A. Rao (sample)", "specialty": "Cornea & Refractive Surgery",
     "area": "Rajajinagar / Hebbal", "focus": "Microbial keratitis, corneal ulcers, keratoplasty"},
    {"hospital": "Nethradhama Super Speciality Eye Hospital", "doctor": "Dr. S. Reddy (sample)", "specialty": "Cornea & Ocular Surface",
     "area": "Jayanagar", "focus": "Infective keratitis, ocular-surface disease"},
    {"hospital": "Dr. Agarwal's Eye Hospital", "doctor": "Dr. N. Iyer (sample)", "specialty": "Cornea & Refractive Services",
     "area": "Koramangala", "focus": "Corneal infections, corneal transplant"},
]
BLR_REFERRALS = {
    "keratitis": CORNEA_PANEL,
    "ulcer_pattern": CORNEA_PANEL,
    "trachoma_tf": [
        {"hospital": "Minto Ophthalmic Hospital (Govt.)", "doctor": "Dr. K. Prasad (sample)", "specialty": "General & Community Ophthalmology",
         "area": "Chamrajpet", "focus": "Trachoma, lid disease, public eye health"},
        {"hospital": "Sankara Eye Hospital", "doctor": "Dr. M. Shetty (sample)", "specialty": "Community & Pediatric Ophthalmology",
         "area": "Varthur / Kundalahalli", "focus": "Outreach screening, trachoma, pediatric lids"},
        {"hospital": "Narayana Nethralaya", "doctor": "Dr. R. Nair (sample)", "specialty": "Preventive Ophthalmology",
         "area": "Rajajinagar", "focus": "Community screening & follow-up"},
    ],
}
REFERRAL_NOTE = ("Illustrative demo directory for this capstone. The hospitals are real Bengaluru eye-care centres; the "
                 "doctor names are placeholders. Verify current specialists and availability and book through each "
                 "hospital's official channels. This is a screening aid, not a medical endorsement.")


def referral_panel(task, refer):
    import urllib.parse
    st.markdown("### Suggested specialists · Bengaluru")
    st.markdown((pill("Referral advised — share these with the patient", "refer") if refer
                 else pill("Routine — share if symptoms persist", "ok")), unsafe_allow_html=True)
    st.write("")
    cols = st.columns(3)
    for col, d in zip(cols, BLR_REFERRALS.get(task, CORNEA_PANEL)):
        query = urllib.parse.quote_plus(f"{d['hospital']} {d['area']} Bengaluru")
        maps = f"https://www.google.com/maps/search/?api=1&query={query}"
        col.markdown(
            f"<div class='soft' style='height:100%'>"
            f"<div style='font-weight:700;color:#0F7C80;font-size:1.02rem'>{d['hospital']}</div>"
            f"<div style='margin-top:4px;font-weight:600'>{d['doctor']}</div>"
            f"<div style='color:#5B7177;font-size:.85rem'>{d['specialty']}</div>"
            f"<div style='margin-top:8px;font-size:.85rem'>Location: {d['area']}, Bengaluru</div>"
            f"<div style='margin-top:4px;font-size:.82rem;color:#5B7177'>{d['focus']}</div>"
            f"<div style='margin-top:10px'><a href='{maps}' target='_blank' "
            f"style='color:#0F7C80;font-weight:600;font-size:.84rem;text-decoration:none'>Open in Google Maps &#8599;</a></div>"
            f"</div>", unsafe_allow_html=True)
    st.caption(REFERRAL_NOTE)


def build_layers(img):
    """Return [(title, desc, image)] of the pipeline's intermediate 'layers' for a step-by-step reveal."""
    import cv2
    cfg = get_cfg()
    layers = [("Input capture", "The raw anterior-eye photograph as received.", img)]
    try:
        from oculens.preprocessing.enhance import enhance
        enh = np.clip(enhance(img, cfg["preprocessing"]), 0, 255).astype(np.uint8)
        layers.append(("Pre-processing (CLAHE)", "Contrast + illumination normalisation so camera/lighting differences do not bias the model.", enh))
    except Exception:  # noqa: BLE001
        pass
    mask = None
    seg = load_segmenter()
    if seg is not None:
        try:
            mask = seg.predict(img)
            ov = img.copy().astype(np.float32)
            ov[mask.astype(bool)] = 0.6 * ov[mask.astype(bool)] + np.array([0, 110, 60])
            edges = cv2.dilate(mask, np.ones((3, 3), np.uint8)) - mask
            ov = np.clip(ov, 0, 255).astype(np.uint8)
            ov[edges.astype(bool)] = [0, 255, 120]
            layers.append(("Cornea segmentation (U-Net)", "A U-Net outlines the cornea so the classifier attends to the right anatomy, not the background.", ov))
            ys, xs = np.where(mask > 0)
            if len(xs) > 0:
                pad = 12
                crop = img[max(0, ys.min() - pad):ys.max() + pad, max(0, xs.min() - pad):xs.max() + pad]
                if crop.size:
                    layers.append(("Region of interest", "The frame cropped to the cornea — the region these diseases actually affect.", crop))
        except Exception:  # noqa: BLE001
            pass
    return layers, mask


def page_new_screening():
    hero("New screening", "Watch the model work through the image layer by layer, then see the prediction and Bengaluru referral.")
    patients = db.list_patients()
    pmap = {f"#{p['id']} · {p['name']} ({p.get('age','?')}{p.get('sex','')})": p["id"] for p in patients}
    left, right = st.columns([1, 1])
    with left:
        choice = st.selectbox("Patient", ["(walk-in / no record)"] + list(pmap.keys()))
        patient_id = pmap.get(choice)
        task = TASKS[st.selectbox("Screen for", list(TASKS.keys()))]
        shots = _image_source(task)
        label = "Run screening on both eyes" if len(shots) > 1 else "Run screening"
        run = st.button(label, type="primary", disabled=not shots, use_container_width=True)
    with right:
        if shots:
            pcols = st.columns(len(shots))
            for pc, (eye, im) in zip(pcols, shots):
                pc.image(im, caption=EYE_NAME[eye] if eye else "Input image", use_container_width=True)
    if not shots or not run:
        return
    for i, (eye, img) in enumerate(shots):
        if len(shots) > 1:
            st.divider()
            st.markdown(f"## {EYE_NAME[eye]}")
        _screen_one(img, task, patient_id, eye, i)


def _open_case(cid):
    st.session_state["view_case"] = cid
    st.session_state["nav"] = "Cases"


def _screen_one(img, task, patient_id, eye, idx):
    """Gate, layer-by-layer analysis, result, save and referral for one eye image."""
    where = f" ({EYE_NAME[eye]})" if eye else ""
    # Gate: only run the model on an actual anterior-eye image.
    dist, thr = eye_distance(img)
    if dist is not None and dist > thr:
        st.error(f"{EYE_NAME[eye] + ': t' if eye else 'T'}his does not look like an eye image. Please upload a clear "
                 "anterior-eye / cornea photograph for prediction.")
        st.caption(f"Out-of-distribution score {dist:.2f} — real eye images score below {thr:.2f}. "
                   "Tip: use a close-up of a single eye that fills most of the frame, in focus and well lit.")
        play_sound("alert", _sound_on())
        return

    from oculens.quality.checks import assess_quality
    from oculens.uncertainty.conformal import prediction_set, should_refer
    cfg = get_cfg()
    st.divider()
    st.markdown(f"#### Live analysis — the model works through the image layer by layer"
                + (f" · {EYE_NAME[eye]}" if eye else ""))
    stepbar, holder = st.empty(), st.empty()

    def reveal(step, title, desc, image, scan_msg=None, hold=0.9):
        with stepbar.container():
            stepper(step)
        with holder.container():
            st.markdown(f"**{title}**")
            st.caption(desc)
            cc = st.columns([1, 2.2, 1])
            if scan_msg:
                cc[1].markdown(scanning_html(image, scan_msg), unsafe_allow_html=True)
                play_sound("scan", _sound_on())
            else:
                cc[1].image(image, use_container_width=True)
        time.sleep(hold)

    layers, _mask = build_layers(img)
    q = assess_quality(img, cfg.get("quality"))
    reveal(0, "Step 1 · Input capture", layers[0][1], img)
    reveal(0, "Step 2 · Image-quality gate",
           "Checking focus, brightness and glare. " + ("Passed — usable image." if q.ok else "Flagged: " + "; ".join(q.prompts)), img)
    for (t, d, im) in layers[1:]:
        step = 2 if ("segmentation" in t.lower() or "interest" in t.lower()) else 1
        reveal(step, t, d, im)
    nens = len(load_ensemble(task))
    _, _is_diff = load_primary(task)
    if _is_diff:
        cls_desc = (f"A diffusion-augmented EfficientNet-B0 reads the cornea and scores every condition, "
                    f"with a {nens}-model ensemble running alongside to measure how uncertain the call is.")
    elif nens > 1:
        cls_desc = f"A deep ensemble of {nens} EfficientNet-B0 models reads the cornea and votes on each condition."
    else:
        cls_desc = "EfficientNet-B0 reads the cornea and scores every possible condition."
    if task == "keratitis":
        pn, pthr = normal_check(img)
        if pn is not None:
            reveal(2, "Step · Normal-eye check",
                   f"A healthy-vs-diseased model (trained on 649 healthy eyes) scores this photo {pn * 100:.0f}% "
                   f"healthy; it reports 'normal' only above {pthr * 100:.0f}% and only for a usable photo.",
                   img, scan_msg="CHECKING FOR A HEALTHY EYE")
            if pn >= pthr and q.ok:
                stepbar.empty()
                holder.empty()
                _normal_result(img, task, patient_id, eye, idx, pn, pthr)
                return
    reveal(3, "Step · Classification", cls_desc, img, scan_msg="CLASSIFYING")
    probs, classes, meta, x, model, nmembers, mi = run_inference(img, task)
    reveal(4, "Step · Explanation", "Computing the Grad-CAM++ heat-map and checking it lands on the cornea.", img, scan_msg="GENERATING EXPLANATION")
    try:
        gcam = gradcam_overlay(model, x, img)
    except Exception:  # noqa: BLE001
        gcam = None
    if gcam is not None:
        with holder.container():
            st.markdown("**Step · Attention heat-map (Grad-CAM++)**")
            st.caption("Warm colours = the pixels that most influenced the prediction.")
            cc = st.columns([1, 2.2, 1])
            cc[1].image(gcam, use_container_width=True)
        time.sleep(0.9)
    stepbar.empty()
    holder.empty()

    order = np.argsort(-probs)
    top = classes[order[0]]
    topp = float(probs[order[0]])
    pset = prediction_set(probs, meta.get("conformal_qhat", 1.0), classes)
    refer = should_refer(pset, top_prob=topp, min_top_prob=0.5)
    seg_ov = next((im for (t, d, im) in layers if "segmentation" in t.lower()), None)

    st.divider()
    st.markdown("## Final result")
    tabs = st.tabs(["Prediction", "Process layers", "Explanation", "Clinical note"])
    with tabs[0]:
        c = st.columns([1, 1.25])
        with c[0]:
            st.markdown("**Confidence**")
            st.plotly_chart(gauge_fig(topp * 100, refer), use_container_width=True, config=PLOT_CFG, key=f"gauge_{idx}")
            st.markdown(pill("REFER for specialist review", "refer") if refer else pill("Confident single label", "ok"), unsafe_allow_html=True)
            st.markdown((pill("image quality OK", "ok") if q.ok else pill("retake advised", "amber")), unsafe_allow_html=True)
            if meta.get("diffusion_primary"):
                st.markdown(pill("Diffusion-augmented EfficientNet-B0", "mut"), unsafe_allow_html=True)
            if nmembers > 1:
                lead = "diffusion-augmented model" if meta.get("diffusion_primary") else "ensemble"
                st.markdown(pill(f"Uncertainty · {nmembers}-model ensemble", "mut"), unsafe_allow_html=True)
                mic = PAL["coral"] if mi > 0.15 else PAL["teal"]
                st.markdown(
                    f"<div style='margin-top:8px;font-size:.85rem'><b>Model disagreement (mutual information):</b> "
                    f"<span style='color:{mic};font-weight:700'>{mi:.3f}</span><br>"
                    f"<span style='color:#5B7177;font-size:.8rem'>Higher = the {nmembers} models disagree more "
                    f"(epistemic uncertainty) — supports the referral decision beside the {lead}'s call.</span></div>",
                    unsafe_allow_html=True)
        with c[1]:
            st.markdown(f"**Most likely: {label_of(task, top)}**")
            st.plotly_chart(probbar_fig([label_of(task, c_) for c_ in classes], probs), use_container_width=True,
                            config=PLOT_CFG, key=f"probs_{idx}")
        st.markdown("**Conformal prediction set (95%):** " + "  ".join(pill(label_of(task, c_), "mut") for c_ in pset), unsafe_allow_html=True)
    with tabs[1]:
        alllayers = list(layers) + ([("Attention heat-map (Grad-CAM++)", "Where the model looked.", gcam)] if gcam is not None else [])
        cols = st.columns(len(alllayers))
        for col, (t, d, im) in zip(cols, alllayers):
            col.image(im, use_container_width=True)
            col.caption(f"**{t}** — {d}")
    with tabs[2]:
        ec = st.columns(2)
        ec[0].image(seg_ov if seg_ov is not None else img, caption="Cornea found by the U-Net (green)", use_container_width=True)
        if gcam is not None:
            ec[1].image(gcam, caption="Grad-CAM++ — where the model looked", use_container_width=True)
        else:
            ec[1].caption("(Grad-CAM unavailable)")
    with tabs[3]:
        st.write(_summary(task, top, topp, refer))
        st.caption("Offline template summary. The full system can call a grounded LLM assistant that only repeats verified findings.")

    fn = f"case_{uuid.uuid4().hex[:10]}.png"
    Image.fromarray(img).save(db.STORAGE / fn)
    cid = db.add_case(patient_id, task, fn, top, topp, ", ".join(pset), refer, q.ok, st.session_state["user"]["name"],
                      mi=mi, eye=eye)
    db.audit(st.session_state["user"], "screening_saved", f"case {cid}", f"{task}: {top} {topp:.2f} refer={bool(refer)}")

    st.divider()
    referral_panel(task, refer)

    st.success(f"Saved as case #{cid}{where}.")
    play_sound("confirm", _sound_on())
    # on_click runs before the next script run, so the click survives the page returning early
    st.button("Open this case", key=f"open_case_{cid}_{idx}", on_click=_open_case, args=(cid,))


def _normal_result(img, task, patient_id, eye, idx, pn, pthr):
    """Result screen when the normal-eye check is confident the eye looks healthy."""
    where = f" ({EYE_NAME[eye]})" if eye else ""
    st.divider()
    st.markdown("## Final result")
    c = st.columns([1, 1.25])
    with c[0]:
        st.markdown("**Normal-eye check**")
        st.plotly_chart(gauge_fig(pn * 100, False), use_container_width=True, config=PLOT_CFG, key=f"ngauge_{idx}")
    with c[1]:
        st.markdown(f"<div class='soft' style='border-left:6px solid {PAL['green']}'><h3 style='margin:0'>No signs of "
                    f"disease found</h3><p style='margin:.4rem 0 0'>The photo looks like a healthy eye: normal-eye score "
                    f"{pn * 100:.1f}% (reported as normal only above {pthr * 100:.1f}%). On held-out test photos this "
                    f"check called 0.24% of diseased eyes normal.</p><p style='margin:.4rem 0 0;color:#5B7177'>Screening "
                    f"aid, not a diagnosis: if the patient has pain, redness, blurred vision or light sensitivity, an eye "
                    f"doctor should still examine them.</p></div>", unsafe_allow_html=True)
        st.markdown(pill("routine", "ok") + " " + pill("image quality OK", "ok"), unsafe_allow_html=True)
    fn = f"case_{uuid.uuid4().hex[:10]}.png"
    Image.fromarray(img).save(db.STORAGE / fn)
    cid = db.add_case(patient_id, task, fn, NORMAL, pn, NORMAL, False, True, st.session_state["user"]["name"],
                      mi=0.0, eye=eye)
    db.audit(st.session_state["user"], "screening_saved", f"case {cid}", f"{task}: normal-eye check {pn:.3f}")
    st.success(f"Saved as case #{cid}{where}.")
    play_sound("confirm", _sound_on())
    st.button("Open this case", key=f"open_case_{cid}_{idx}", on_click=_open_case, args=(cid,))


def _rl_image(arr, max_w):
    from reportlab.platypus import Image as RLImage
    b = io.BytesIO(); Image.fromarray(arr).save(b, format="PNG"); b.seek(0)
    h, w = arr.shape[:2]
    return RLImage(b, width=max_w, height=max_w * h / w)


def case_pdf_bytes(case, img, gcam, recs):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=f"OcuLens-AI case {case['id']}")
    ss = getSampleStyleSheet()
    teal = colors.HexColor("#0F7C80"); ink = colors.HexColor("#0A2A33"); mut = colors.HexColor("#5B7177")
    H = ParagraphStyle("H", parent=ss["Title"], fontSize=18, textColor=ink, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=9, textColor=mut)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, textColor=teal, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, textColor=ink, leading=14)
    s = [Paragraph("OcuLens-AI — Screening Report", H),
         Paragraph(f"Case #{case['id']} &nbsp;·&nbsp; {TASK_NAME.get(case['task'], case['task'])} &nbsp;·&nbsp; {case['created_at']} &nbsp;·&nbsp; screened by {case['created_by']}", sub),
         Spacer(1, 8)]
    s += [Paragraph("Patient", h2),
          Paragraph(f"<b>{case.get('patient_name') or 'walk-in / no record'}</b>"
                    + (f" &nbsp; Age {case.get('age')}" if case.get("age") else "")
                    + (f" &nbsp; {case.get('sex')}" if case.get("sex") else ""), body)]
    imgs = []
    if img is not None:
        imgs.append(_rl_image(img, 7.2 * cm))
    if gcam is not None:
        imgs.append(_rl_image(gcam, 7.2 * cm))
    if imgs:
        s += [Paragraph("Captured image &amp; explanation (Grad-CAM++)", h2),
              Table([imgs], hAlign="LEFT")]
    mi = case.get("mi") or 0.0
    rows = [["Eye", EYE_NAME.get(case.get("eye") or "", "Eye not recorded")],
            ["Prediction", label_of(case["task"], case["top_label"])],
            ["Confidence", f"{case['top_prob']*100:.1f}%"],
            ["Conformal set (95%)", case.get("pred_set") or "-"]]
    if mi:
        rows.append(["Model disagreement (MI)", f"{mi:.3f}"])
    rows += [["Image quality", "OK" if case.get("quality_ok") else "retake advised"],
             ["Decision", "REFER for specialist review" if case["referred"] else "Routine"],
             ["Status", case["status"]]]
    t = Table(rows, colWidths=[5.2 * cm, 10.2 * cm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 10), ("TEXTCOLOR", (0, 0), (0, -1), mut),
                           ("TEXTCOLOR", (1, 0), (1, -1), ink), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCEBEA"))]))
    s += [Paragraph("AI screening result", h2), t]
    s += [Paragraph("Doctor recommendations", h2)]
    if recs:
        for r in recs:
            s.append(Paragraph(f"<b>{r['doctor']}</b> · {r['created_at']}<br/><b>Diagnosis:</b> {r['diagnosis'] or '-'}"
                               f"<br/><b>Plan:</b> {r['recommendation'] or '-'}", body))
            s.append(Spacer(1, 4))
    else:
        s.append(Paragraph("No recommendation recorded yet.", body))
    import urllib.parse
    link = ParagraphStyle("link", parent=body, textColor=teal, fontSize=9)
    s += [Paragraph("Suggested specialists · Bengaluru", h2)]
    for d in BLR_REFERRALS.get(case["task"], CORNEA_PANEL):
        q = urllib.parse.quote_plus(f"{d['hospital']} {d['area']} Bengaluru")
        maps = f"https://www.google.com/maps/search/?api=1&amp;query={q}"
        s.append(Paragraph(f"<b>{d['hospital']}</b> — {d['doctor']}<br/>{d['specialty']} · {d['area']}, Bengaluru<br/>{d['focus']}", body))
        s.append(Paragraph(f'<a href="{maps}">Open in Google Maps</a>', link))
        s.append(Spacer(1, 5))
    s.append(Paragraph(REFERRAL_NOTE, sub))
    s += [Spacer(1, 14),
          Paragraph("OcuLens-AI is a research prototype trained on public data — a screening aid, not a medical device, "
                    "and not a diagnosis. All findings must be confirmed by a qualified eye-care professional.", sub)]
    doc.build(s)
    buf.seek(0)
    return buf.getvalue()


def _summary(task, top, p, refer):
    name = label_of(task, top)
    base = {"keratitis": f"The image most resembles **{name}** ({p*100:.0f}% confidence).",
            "ulcer_pattern": f"The corneal ulcer pattern is graded **{name}** ({p*100:.0f}% confidence).",
            "trachoma_tf": f"Screening result: **{name}** ({p*100:.0f}% confidence)."}[task]
    tail = (" Confidence is below threshold, so this case is flagged for an eye-care professional to review."
            if refer else " This is a screening aid and does not replace a clinician's diagnosis.")
    return base + tail


TASK_PLAIN = {"keratitis": "Cornea check", "ulcer_pattern": "Ulcer pattern (clinic)", "trachoma_tf": "Eyelid check (trachoma)"}


def analyse_image(img, task):
    """Eye check, quality, prediction, prediction set and referral for one image, without any display."""
    from oculens.quality.checks import assess_quality
    from oculens.uncertainty.conformal import prediction_set, should_refer
    dist, thr = eye_distance(img)
    if dist is not None and dist > thr:
        return {"eye_ok": False, "dist": dist, "thr": thr}
    q = assess_quality(img, get_cfg().get("quality"))
    pn, pthr = normal_check(img) if task == "keratitis" else (None, None)
    if pn is not None and q.ok and pn >= pthr:      # confident healthy eye (only for usable cornea photos)
        return {"eye_ok": True, "q": q, "top": NORMAL, "topp": pn, "pset": [NORMAL], "refer": False, "mi": 0.0,
                "normal": True, "p_normal": pn}
    probs, classes, meta, x, model, nmem, mi = run_inference(img, task)
    o = int(np.argmax(probs))
    top, topp = classes[o], float(probs[o])
    pset = prediction_set(probs, meta.get("conformal_qhat", 1.0), classes)
    refer = should_refer(pset, top_prob=topp, min_top_prob=0.5)
    return {"eye_ok": True, "q": q, "top": top, "topp": topp, "pset": pset, "refer": refer, "mi": mi,
            "normal": False, "p_normal": pn}


def page_cases():
    if st.session_state.get("view_case"):
        return _case_detail(st.session_state["view_case"])
    hero("Cases", "Every screening, filterable — open one to review the AI result and add your recommendation.")
    f = st.columns(4)
    status = f[0].selectbox("Status", ["All", "pending", "reviewed"])
    task = f[1].selectbox("Task", ["All"] + list(TASKS.values()), format_func=lambda t: TASK_NAME.get(t, t))
    refflag = f[2].selectbox("Referral", ["All", "Referred only", "Not referred"])
    referred = {"All": None, "Referred only": True, "Not referred": False}[refflag]
    rows = db.list_cases(status=status, task=task, referred=referred)
    f[3].metric("Matching", len(rows))
    if not rows:
        st.info("No cases match these filters.")
        return
    for r in rows:
        with st.container(border=True):
            cols = st.columns([0.6, 2, 2.3, 1.2, 1.1, 0.9])
            cols[0].markdown(f"**#{r['id']}**")
            cols[1].write((r["patient_name"] or "walk-in") + (f" · {EYE_NAME[r['eye']]}" if r.get("eye") else ""))
            cols[2].write(f"{TASK_NAME.get(r['task'], r['task'])}: {label_of(r['task'], r['top_label'])}")
            cols[3].write(f"{r['top_prob']*100:.0f}%")
            cols[4].markdown(pill("REFER", "refer") if r["referred"] else pill("routine", "ok"), unsafe_allow_html=True)
            cols[4].markdown(pill(r["status"], "mut" if r["status"] == "pending" else "ok"), unsafe_allow_html=True)
            if r.get("source") == "self":
                cols[4].markdown(pill("patient self-check", "amber"), unsafe_allow_html=True)
            if (r.get("mi") or 0) > MI_FLAG:
                cols[4].markdown(pill("uncertain", "amber"), unsafe_allow_html=True)
            if cols[5].button("Open", key=f"o{r['id']}"):
                st.session_state["view_case"] = r["id"]
                st.rerun()


def _case_detail(cid):
    case = db.get_case(cid)
    if st.button("← Back to cases"):
        st.session_state["view_case"] = None
        st.rerun()
    if not case:
        st.error("Case not found.")
        return
    if st.session_state.get("_audited_view") != cid:          # one entry per opening, not per rerun
        db.audit(st.session_state["user"], "case_viewed", f"case {cid}")
        st.session_state["_audited_view"] = cid
    eye_txt = f" · {EYE_NAME[case['eye']]}" if case.get("eye") else ""
    hero(f"Case #{cid}", f"{case['patient_name'] or 'walk-in'}{eye_txt} · {TASK_NAME.get(case['task'], case['task'])} · screened {case['created_at']} by {case['created_by']}")
    st.button("Ask the AI assistant about this case", key=f"askai_{cid}", on_click=_ask_ai, args=(cid,))
    img_path = db.STORAGE / case["image_path"]
    img = np.array(Image.open(img_path).convert("RGB")) if img_path.exists() else None
    left, right = st.columns([1, 1.1])
    with left:
        if img is not None:
            st.image(img, caption="Captured image", use_container_width=True)
        _mi = case.get("mi") or 0.0
        mi_line = (f"<br><b>Model disagreement (MI):</b> {_mi:.3f}" if _mi else "")
        st.markdown(f"<div class='soft'><b>AI result:</b> {label_of(case['task'], case['top_label'])} "
                    f"({case['top_prob']*100:.0f}%)<br><b>Set:</b> {case['pred_set'] or '-'}{mi_line}<br><b>Referral:</b> "
                    f"{pill('REFER','refer') if case['referred'] else pill('routine','ok')} &nbsp; "
                    f"{pill(case['status'], 'mut' if case['status']=='pending' else 'ok')}</div>", unsafe_allow_html=True)
    gcam_img = None
    with right:
        if img is not None:
            try:
                _, _, _, x, model, _n, _mi = run_inference(img, case["task"])
                gcam_img = gradcam_overlay(model, x, img)
                st.image(gcam_img, caption="Grad-CAM++", use_container_width=True)
            except Exception as e:  # noqa: BLE001
                st.caption(f"(explanation unavailable: {e})")
    recs = db.recommendations_for(cid)
    try:
        st.download_button("Download PDF report", data=case_pdf_bytes(case, img, gcam_img, recs),
                           file_name=f"OcuLens_case_{cid}.pdf", mime="application/pdf")
    except Exception as e:  # noqa: BLE001
        st.caption(f"(PDF export unavailable: {e})")
    st.divider()
    st.subheader("Doctor recommendations")
    for rec in recs:
        st.markdown(f"<div class='soft'><b>{rec['doctor']}</b> · {rec['created_at']}<br>"
                    f"<b>Diagnosis:</b> {rec['diagnosis'] or '-'}<br><b>Plan:</b> {rec['recommendation'] or '-'}</div>", unsafe_allow_html=True)
        st.write("")
    if st.session_state["user"]["role"] in ("doctor", "admin"):
        with st.form(f"rec{cid}"):
            dx = st.text_input("Confirmed / working diagnosis")
            txt = st.text_area("Recommendation / plan (treatment, follow-up, referral)")
            if st.form_submit_button("Save recommendation", type="primary"):
                db.add_recommendation(cid, st.session_state["user"]["name"], dx, txt)
                db.audit(st.session_state["user"], "recommendation_saved", f"case {cid}", dx)
                st.success("Saved; case marked reviewed.")
                st.rerun()

    st.divider()
    if case.get("patient_id") and st.session_state["user"]["role"] in ("doctor", "admin"):
        _drop_schedule_panel(case)
        st.divider()
    st.subheader("Referral appointments · Bengaluru")
    for a in db.appointments_for(cid):
        st.markdown(f"<div class='soft'>{a['hospital']} — {a['doctor']} &nbsp; {pill(a['status'], 'amber')} "
                    f"&nbsp; requested by {a['requested_by']} · {a['created_at']}</div>", unsafe_allow_html=True)
        st.write("")
    refs = BLR_REFERRALS.get(case["task"], CORNEA_PANEL)
    st.caption("Request an appointment at a suggested centre:")
    acols = st.columns(len(refs))
    for i, (col, d) in enumerate(zip(acols, refs)):
        if col.button(f"Request · {d['hospital']}", key=f"appt{cid}_{i}", use_container_width=True):
            db.add_appointment(cid, d["hospital"], d["doctor"], st.session_state["user"]["name"])
            st.success(f"Appointment requested at {d['hospital']}.")
            st.rerun()


def page_patients():
    hero("Patients", "Manage patient records and see each person's screening history.")
    with st.expander("Add a patient"):
        with st.form("addp"):
            c = st.columns(4)
            name = c[0].text_input("Name")
            age = c[1].number_input("Age", 0, 120, 40)
            sex = c[2].selectbox("Sex", ["", "M", "F", "Other"])
            mrn = c[3].text_input("MRN / ID")
            if st.form_submit_button("Add patient", type="primary") and name.strip():
                db.add_patient(name.strip(), int(age), sex, mrn)
                st.success(f"Added {name}.")
                st.rerun()
    for p in db.list_patients():
        with st.container(border=True):
            top = st.columns([3, 1, 1, 1])
            top[0].markdown(f"**#{p['id']} · {p['name']}**  \nMRN {p.get('mrn') or '-'}")
            top[1].write(f"Age {p.get('age','?')}")
            top[2].write(p.get("sex") or "-")
            cs = db.cases_for_patient(p["id"])
            top[3].write(f"{len(cs)} screening(s)")
            acct = db.login_for_patient(p["id"])
            sy = db.symptoms_for(p["id"])
            info = (pill(f"portal login: {acct['username']}", "ok") if acct else pill("no portal login", "mut"))
            if sy:
                last = sy[-1]
                info += " " + pill(f"diary {last['logged_at'][:10]} · pain {last['pain']}/10 · blur {last['blur']}/10",
                                   "refer" if max(last["pain"], last["blur"]) >= 8 else "mut")
            vt = [v for v in db.vision_tests_for(p["id"]) if v["kind"] == "acuity"]
            if vt:
                last = {e: next((v for v in reversed(vt) if v["eye"] == e), None) for e in ("Right", "Left")}
                info += " " + pill("vision " + " · ".join(f"{e[0]} {last[e]['snellen']}" for e in last if last[e]), "mut")
            st.markdown(info, unsafe_allow_html=True)
            if sy and len(sy) >= 2:
                with st.expander(f"Symptom diary ({len(sy)} entries)"):
                    st.plotly_chart(pp._trend_fig(sy[-30:]), use_container_width=True, config=PLOT_CFG,
                                    key=f"diary_{p['id']}")
            if not acct:
                with st.expander("Create a portal login for this patient"):
                    with st.form(f"plog_{p['id']}"):
                        c = st.columns(3)
                        un = c[0].text_input("Username", key=f"plu_{p['id']}")
                        pw = c[1].text_input("Temporary password", type="password", key=f"plp_{p['id']}")
                        lg = c[2].selectbox("Language", list(ai.LANGUAGES), format_func=lambda k: ai.LANGUAGES[k][0],
                                            key=f"pll_{p['id']}")
                        if st.form_submit_button("Create login"):
                            ok, msg = db.create_patient_login(p["id"], un, pw, lg)
                            (st.success if ok else st.error)(msg)
            for c_ in cs:
                st.markdown(f"&nbsp;&nbsp;↳ case #{c_['id']} · {label_of(c_['task'], c_['top_label'])} "
                            f"({c_['top_prob']*100:.0f}%) · " + (pill("REFER", "refer") if c_["referred"] else pill(c_["status"], "mut")), unsafe_allow_html=True)


def page_imagegen():
    hero("Image generation studio", "Synthesise rare-class training images to rebalance the dataset — runs locally.")
    dif = load_diffusion()
    modes = ["Augmentation synthesis (CPU, runs now)"]
    if dif is not None:
        modes.append("Diffusion — DDPM (GPU-trained)")
    mode = st.radio("Method", modes, horizontal=True)
    if mode.startswith("Diffusion"):
        _, classes, size = dif
        c = st.columns(4)
        cls = c[0].selectbox("Class", classes, format_func=lambda x: LABELS.get(x, x))
        n = c[1].slider("How many", 1, 6, 3)
        steps = c[2].slider("Steps", 10, 100, 30, step=10)
        g = c[3].slider("Guidance", 0.0, 5.0, 2.0, step=0.5)
        if st.button("Generate with diffusion", type="primary"):
            with st.spinner("Sampling on CPU..."):
                imgs = generate_images(classes.index(cls), n, steps, g)
            cols = st.columns(len(imgs))
            for i, im in enumerate(imgs):
                cols[i].image(im, use_container_width=True, caption=f"synthetic #{i+1}")
    else:
        c = st.columns([2, 2, 1])
        cls = c[0].selectbox("Keratitis class", ["BK", "FK", "HSK", "other_corneal_abnormalities"], format_func=lambda x: LABELS.get(x, x))
        n = c[1].slider("How many", 1, 8, 4)
        c[2].write(""); c[2].write("")
        if c[2].button("Generate", type="primary", use_container_width=True):
            with st.spinner("Synthesising..."):
                imgs, nf = augment_samples(cls, n)
            if not imgs:
                st.warning("No local seed images for this class.")
            else:
                st.success(f"Generated {len(imgs)} synthetic '{LABELS.get(cls, cls)}' images from {nf} real seeds.")
                cols = st.columns(len(imgs))
                for i, im in enumerate(imgs):
                    cols[i].image(im, use_container_width=True, caption=f"synthetic #{i+1}")
        st.caption("Augmentation synthesis applies the training-time transforms (crop, flip, rotation, colour, blur) to real "
                   "seed images — the step used to balance rare classes. The diffusion generator (RQ2a) creates fully novel "
                   "images and appears here once its GPU-trained weight is on disk.")


def page_eval():
    hero("Model evaluation", "Test-set results of the 50-epoch models: accuracy, calibration, conformal coverage, referral and fairness.")
    rows = [("eval_trachoma_image", "Trachoma (TF)"), ("eval_ulcer_mask_input", "Ulcer mask_input"),
            ("eval_ulcer_region_crop", "Ulcer region_crop"), ("eval_ulcer_multitask", "Ulcer multitask"),
            ("eval_ulcer_image", "Ulcer baseline"), ("eval_keratitis_ensemble", "Keratitis ensemble (5)"),
            ("eval_keratitis_harmonized", "Keratitis +CycleGAN"), ("eval_keratitis_synthetic", "Keratitis +diffusion"),
            ("eval_keratitis_image", "Keratitis baseline")]
    table = []
    for fn, lab in rows:
        d = _load_json(EVAL / f"{fn}.json")
        if not d:
            continue
        o, cf = d.get("overall", {}), d.get("conformal", {})
        table.append({"Model": lab, "Balanced acc": _r(o.get("balanced_accuracy")), "AUROC": _r(o.get("auroc_macro_ovr")),
                      "ECE": _r(o.get("ece")), "Conf. coverage": _r(cf.get("coverage")), "Mean set size": _r(cf.get("mean_set_size"))})
    if table:
        st.dataframe(table, use_container_width=True, hide_index=True)
    ci = _load_json(ROOT / "experiments" / "ci" / "ci.json")
    if ci:
        st.markdown("#### 95% confidence intervals (1,000-sample bootstrap)")
        def _f(d):
            if not d or d.get("point") is None:
                return "n/a"
            c = d.get("ci95") or []
            return f"{d['point']:.3f} [{c[0]:.3f}, {c[1]:.3f}]" if len(c) == 2 else f"{d['point']:.3f}"
        st.dataframe([{"Model": r.get("label", k), "Test n": r.get("n"),
                       "Balanced acc [95% CI]": _f(r.get("balanced_accuracy")),
                       "Macro F1 [95% CI]": _f(r.get("macro_f1")),
                       "AUROC [95% CI]": _f(r.get("auroc"))} for k, r in ci.items()],
                     use_container_width=True, hide_index=True)
        st.caption("Overlapping intervals mean a difference is not yet statistically meaningful; wider intervals come from smaller test sets.")
    cc = st.columns(2)
    cal = _load_json(CURV / "keratitis_baseline.json")
    if cal:
        cc[0].markdown("**Calibration — keratitis baseline** (ECE %.3f)" % cal.get("ece", float("nan")))
        cc[0].line_chart({"confidence": [b["conf"] for b in cal["calibration"]],
                          "accuracy": [b["acc"] for b in cal["calibration"]],
                          "perfect": [b["conf"] for b in cal["calibration"]]}, x="confidence", y=["accuracy", "perfect"])
    ref = _load_json(CURV / "ulcer_region_crop.json")
    if ref:
        cc[1].markdown("**Referral trade-off — ulcer region_crop**")
        r = [x for x in ref["referral"] if x["accuracy_kept"] == x["accuracy_kept"]]
        cc[1].line_chart({"referral rate": [x["referral_rate"] for x in r], "accuracy on kept": [x["accuracy_kept"] for x in r]},
                         x="referral rate", y="accuracy on kept")
    st.caption("Test splits are single-site (keratitis AGEH, ulcer ZOC); cross-site validation is future work.")
    fdir = ROOT / "experiments" / "failures"
    fidx = _load_json(fdir / "index.json")
    if fidx:
        st.divider()
        st.markdown("#### Failure cases (most-confident mistakes, with Grad-CAM++)")
        tnames = {"keratitis": "Keratitis", "ulcer_pattern": "Ulcer", "trachoma_tf": "Trachoma"}
        by = {}
        for it in fidx:
            by.setdefault(it["task"], []).append(it)
        for task, lst in by.items():
            st.markdown(f"**{tnames.get(task, task)}**")
            cols = st.columns(min(6, len(lst)))
            for col, it in zip(cols, lst[:6]):
                fp = fdir / it["file"]
                if fp.exists():
                    col.image(str(fp), use_container_width=True)
                    col.caption(f"true: {it['true']}\npred: {it['pred']} ({it['conf']*100:.0f}%)")
        st.caption("Confident errors are exactly what the referral gate is designed to catch.")


def page_followup():
    hero("Follow-up & monitoring", "Track a patient's screenings over time and flag changes between visits.")
    patients = db.list_patients()
    if not patients:
        st.info("No patients yet. Add one under Patients.")
        return
    pmap = {f"#{p['id']} · {p['name']}": p["id"] for p in patients}
    pid = pmap[st.selectbox("Patient", list(pmap.keys()))]
    cs = sorted(db.cases_for_patient(pid), key=lambda r: r["id"])
    if not cs:
        st.info("No screenings recorded for this patient yet.")
        return
    st.write("")
    prev_by_task = {}
    for c_ in cs:
        with st.container(border=True):
            cols = st.columns([1.3, 2.2, 1, 1.2, 2.3])
            cols[0].write(c_["created_at"])
            cols[1].write(f"{TASK_NAME.get(c_['task'], c_['task'])}: {label_of(c_['task'], c_['top_label'])}")
            cols[2].write(f"{c_['top_prob']*100:.0f}%")
            flags = pill("REFER", "refer") if c_["referred"] else pill(c_["status"], "mut")
            if (c_.get("mi") or 0) > MI_FLAG:
                flags += " " + pill("uncertain", "amber")
            cols[3].markdown(flags, unsafe_allow_html=True)
            prev = prev_by_task.get(c_["task"])
            if prev:
                if c_["top_label"] != prev["top_label"]:
                    note = f"label changed: {label_of(c_['task'], prev['top_label'])} → {label_of(c_['task'], c_['top_label'])}"
                else:
                    d = (c_["top_prob"] - prev["top_prob"]) * 100
                    trend = "stable" if abs(d) < 5 else ("higher confidence" if d > 0 else "lower confidence")
                    note = f"vs previous: {trend} ({d:+.0f}%)"
            else:
                note = "baseline visit"
            cols[4].write(note)
            prev_by_task[c_["task"]] = c_
    st.caption("Change detection here is illustrative (confidence / label deltas between visits of the same task). The full "
               "system aligns each new image to the previous one and classifies progression as progressed / stable / improved.")


_EYES = ["Right eye", "Left eye", "Both eyes"]
_TIME_PRESETS = {"Once a day": ["08:00"], "Twice a day": ["08:00", "20:00"], "3 times a day": ["08:00", "14:00", "20:00"],
                 "4 times a day": ["07:00", "11:00", "15:00", "19:00"], "Every 2 hours (daytime)":
                 ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]}


def _drop_schedule_panel(case):
    """The doctor writes the drop schedule; the patient sees reminders and ticks doses. The AI never suggests drops."""
    import datetime as _dt
    pid = case["patient_id"]
    st.subheader("Eye-drop schedule for the patient")
    meds = db.medications_for(pid, active_only=False)
    for m in meds:
        got, due = db.adherence(m)
        pct = int(100 * got / due) if due else 100
        c = st.columns([3, 1.3, 1])
        c[0].markdown(f"**{m['name']}** · {m['eye']} · {m['times'].replace(',', ', ')}  \n{m['instructions'] or ''}  \n"
                      f"<span style='font-size:.8rem;color:#5B7177'>{m['start_date']} → {m['end_date']} · by {m['prescribed_by']}</span>",
                      unsafe_allow_html=True)
        c[1].markdown(pill(f"adherence {pct}% ({got}/{due})", "ok" if pct >= 80 else "amber" if pct >= 50 else "refer")
                      + ("" if m["active"] else " " + pill("stopped", "mut")), unsafe_allow_html=True)
        if m["active"] and c[2].button("Stop", key=f"stopmed_{m['id']}"):
            db.stop_medication(m["id"])
            st.rerun()
    with st.expander("Add drops to the patient's schedule", expanded=not meds):
        with st.form(f"med_{case['id']}"):
            c = st.columns([2, 1, 1.4])
            name = c[0].text_input("Drop name and strength (as prescribed)")
            eye = c[1].selectbox("Eye", _EYES)
            preset = c[2].selectbox("How often", list(_TIME_PRESETS))
            c2 = st.columns([1, 1, 2])
            start = c2[0].date_input("Start", value=_dt.date.today(), key=f"ms_{case['id']}")
            days = c2[1].number_input("For how many days", 1, 120, 7)
            instr = c2[2].text_input("Instructions for the patient", placeholder="e.g. wait 5 minutes between drops")
            if st.form_submit_button("Add to schedule", type="primary"):
                if name.strip():
                    db.add_medication(pid, case["id"], name, eye, _TIME_PRESETS[preset], start.isoformat(),
                                      (start + _dt.timedelta(days=int(days) - 1)).isoformat(), instr,
                                      st.session_state["user"]["name"])
                    st.success("Added. The patient sees reminders under My eye drops.")
                    st.rerun()
                else:
                    st.error("Please enter the drop name.")
    st.caption("Entered by the doctor only; the AI assistant never suggests medicines.")


def _all_doctors():
    docs = [u["name"] for u in db.list_users() if u["role"] == "doctor"]
    for h in geo.HOSPITALS:
        for d, _ in h["doctors"]:
            if d not in docs:
                docs.append(d)
    return docs


def page_schedule():
    import datetime as _dt
    hero("My schedule", "Working days, clinic hours and leave: patients can book only the times you are available.")
    me = st.session_state["user"]
    if me["role"] == "admin":
        doctor = st.selectbox("Doctor", _all_doctors())
    else:
        doctor = me["name"]
        st.caption(f"Editing the calendar of **{doctor}**.")
    sched = db.get_schedule(doctor)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        with st.form(f"sched_{doctor}"):
            st.markdown("**Weekly clinic hours** (sessions as HH:MM-HH:MM, comma separated)")
            step = st.select_slider("Appointment length (minutes)", [10, 15, 20, 30, 45, 60],
                                    value=next(iter(sched.values()))[1])
            new = {}
            for i, d in enumerate(days):
                c = st.columns([1.1, 0.7, 2.6])
                c[0].markdown(f"<div style='padding-top:8px;font-weight:600'>{d}</div>", unsafe_allow_html=True)
                on = c[1].checkbox("Works", value=bool(sched[i][0]), key=f"on_{doctor}_{i}")
                sess = c[2].text_input("Sessions", value=sched[i][0] or db.DEFAULT_SESSIONS, key=f"ss_{doctor}_{i}",
                                       label_visibility="collapsed", disabled=False)
                new[i] = (sess if on else "", step)
            if st.form_submit_button("Save schedule", type="primary"):
                try:
                    db.save_schedule(doctor, new)
                    st.success("Schedule saved. Booking now offers only these times.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
    with right:
        st.markdown("**Leave days**")
        with st.form(f"leave_{doctor}"):
            ld = st.date_input("Day off", min_value=_dt.date.today())
            why = st.text_input("Reason (optional)")
            if st.form_submit_button("Add leave"):
                db.add_leave(doctor, ld.isoformat(), why)
                st.rerun()
        for lv in db.leave_for(doctor):
            c = st.columns([3, 1])
            c[0].write(f"{lv['day']} · {lv['reason'] or 'leave'}")
            if c[1].button("Remove", key=f"lv_{lv['id']}"):
                db.delete_leave(lv["id"])
                st.rerun()
        st.markdown("**Next 7 days**")
        rows = []
        for k in range(7):
            d = _dt.date.today() + _dt.timedelta(days=k)
            grid = db.slots_for(doctor, d.isoformat())
            booked = db.booked_slots(doctor, d.isoformat())
            rows.append({"Day": d.strftime("%a %d %b"), "Slots": len(grid), "Booked": len(booked & set(grid)),
                         "Free": len([x for x in grid if x not in booked])})
        st.dataframe(rows, hide_index=True, use_container_width=True)


def page_referrals():
    hero("Referral follow-up", "Did the referred patients reach the specialist? Close the loop on every referral.")
    rows = db.referral_status()
    n = len(rows)
    visited = sum(r["state"] == "Visited" for r in rows)
    booked = sum(r["state"] == "Booked" for r in rows)
    overdue = [r for r in rows if r["overdue"]]
    k = st.columns(4)
    kpi(k[0], n, "Referred", "", PAL["coral"])
    kpi(k[1], f"{(booked + visited) * 100 // max(1, n)}%", "Booked or visited", "", PAL["amber"])
    kpi(k[2], f"{visited * 100 // max(1, n)}%", "Reached the specialist", "", PAL["green"])
    kpi(k[3], len(overdue), "Overdue follow-ups", "", PAL["iris"])
    st.write("")
    show = st.radio("Show", ["Overdue first", "All referrals"], horizontal=True)
    lst = sorted(rows, key=lambda r: (not r["overdue"], -r["days"])) if show == "Overdue first" else rows
    colors = {"Visited": "ok", "Booked": "amber", "Not booked": "refer", "Declined": "mut", "Not reachable": "mut",
              "Moved away": "mut"}
    for r in lst[:60]:
        with st.container(border=True):
            c = st.columns([0.6, 1.8, 1.6, 1.2, 2.6])
            c[0].markdown(f"**#{r['id']}**")
            c[1].markdown(f"{r['patient_name'] or 'walk-in'}  \n{TASK_NAME.get(r['task'], r['task'])}")
            c[2].markdown(f"referred {r['days']} day(s) ago  \n" + (f"last: {r['followup']['outcome']} · {r['followup']['at']}"
                                                                    if r["followup"] else "no follow-up yet"))
            c[3].markdown(pill(r["state"], colors.get(r["state"], "mut")) + (" " + pill("overdue", "refer") if r["overdue"] else ""),
                          unsafe_allow_html=True)
            with c[4].popover("Log follow-up"):
                out = st.selectbox("Outcome", ["Called - will book", "Visited", "Not reachable", "Declined", "Moved away"],
                                   key=f"fo_{r['id']}")
                note = st.text_input("Note", key=f"fn_{r['id']}")
                if st.button("Save", key=f"fs_{r['id']}"):
                    db.add_followup(r["id"], out, note, st.session_state["user"]["name"])
                    st.rerun()
                if r.get("patient_id") and db.login_for_patient(r["patient_id"]):
                    if st.button("Send a booking reminder to the patient's app", key=f"fr_{r['id']}"):
                        import datetime as _dt
                        db.add_reminder(r["patient_id"], "Please book your eye specialist visit (advised by your doctor)",
                                        _dt.date.today().isoformat(), "referral")
                        db.add_followup(r["id"], "Reminder sent", "", st.session_state["user"]["name"])
                        st.rerun()
    st.caption("A referral counts as visited when the appointment is marked done or a follow-up records a visit. Overdue: "
               "not booked within 3 days, or booked but not visited within 14 days.")


def page_appointments_doc():
    hero("Appointments", "Bookings from patients and referrals: confirm, decline or mark them done.")
    me = st.session_state["user"]["name"]
    rows = db.all_appointments()
    f = st.columns(3)
    who = f[0].radio("Show", ["All bookings", "Booked with me"], horizontal=True)
    stt = f[1].selectbox("Status", ["All", "requested", "confirmed", "completed", "declined", "cancelled"])
    if who == "Booked with me":
        rows = [r for r in rows if r.get("doctor") == me]
    if stt != "All":
        rows = [r for r in rows if r["status"] == stt]
    f[2].metric("Bookings", len(rows))
    if not rows:
        st.info("No appointments match.")
        return
    kinds = {"requested": "amber", "confirmed": "ok", "completed": "mut", "declined": "refer", "cancelled": "refer"}
    for r in rows:
        with st.container(border=True):
            c = st.columns([1.7, 2, 1.4, 1, 3.2])
            c[0].markdown(f"**{r.get('patient_name') or r['requested_by']}**  \nrequested {r['created_at']}")
            c[1].markdown(f"{r['hospital']}  \n{r.get('doctor') or '-'}")
            c[2].markdown(f"{r.get('preferred_date') or '-'} {r.get('slot') or ''}  \n{r.get('visit_type') or 'In person'}"
                          + (f"  \nNeeds: {r['needs']}" if r.get("needs") else "")
                          + (f"  \n{r['note']}" if r.get("note") else ""))
            c[3].markdown(pill(r["status"], kinds.get(r["status"], "mut")), unsafe_allow_html=True)
            b = c[4].columns(3)
            if r["status"] == "requested" and b[0].button("Confirm", key=f"apc_{r['id']}"):
                db.set_appointment_status(r["id"], "confirmed")
                db.audit(st.session_state["user"], "appointment_confirmed", f"appointment {r['id']}")
                st.rerun()
            if r["status"] in ("requested", "confirmed") and b[1].button("Decline", key=f"apd_{r['id']}"):
                db.set_appointment_status(r["id"], "declined"); st.rerun()
            if r["status"] == "confirmed" and b[2].button("Done", key=f"apx_{r['id']}"):
                db.set_appointment_status(r["id"], "completed"); st.rerun()


def page_users():
    hero("Users", "Manage portal accounts (admin only).")
    st.dataframe(db.list_users(), use_container_width=True, hide_index=True)
    with st.expander("Reset a user's password"):
        with st.form("resetpw"):
            us = {f"{u['username']} ({u['role']})": u["id"] for u in db.list_users()}
            who = st.selectbox("User", list(us))
            npw = st.text_input("New temporary password (8+ characters)", type="password")
            if st.form_submit_button("Reset password") and len(npw) >= 8:
                db.set_user_active_password(us[who], npw)
                db.audit(st.session_state["user"], "password_reset", who)
                st.success("Password reset; the account is unlocked.")
    with st.form("adduser"):
        c = st.columns(4)
        un = c[0].text_input("Username")
        pw = c[1].text_input("Password", type="password")
        nm = c[2].text_input("Full name")
        role = c[3].selectbox("Role", ["doctor", "admin"])
        if st.form_submit_button("Add user", type="primary") and un.strip():
            (st.success("User added.") if db.add_user(un.strip(), pw, nm, role) else st.error("Username exists."))
            st.rerun()


def page_audit():
    hero("Audit log", "Who signed in, viewed or changed what, and when (admin only).")
    c = st.columns(3)
    actions = ["All", "login", "login_failed", "case_viewed", "screening_saved", "recommendation_saved",
               "appointment_confirmed", "patient_signup", "data_export", "account_deleted", "password_reset",
               "settings_changed", "backup_downloaded", "error"]
    act = c[0].selectbox("Action", actions)
    who = c[1].text_input("Username")
    lim = c[2].number_input("Rows", 50, 5000, 500, step=50)
    rows = db.audit_rows(int(lim), None if act == "All" else act, who.strip() or None)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if rows:
        import csv
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
        st.download_button("Download as CSV", buf.getvalue(), file_name="oculens_audit_log.csv", mime="text/csv")


def _backup_clicked():
    db.audit(st.session_state["user"], "backup_downloaded")


def page_system():
    hero("System & branding", "Health of the installation, white-label branding and backups (admin only).")
    c = st.columns(4)
    stt = db.db_stats()
    kpi(c[0], f"v{settings.VERSION}", "Version", "", PAL["teal"])
    kpi(c[1], stt["users"], "Accounts", "", PAL["iris"])
    kpi(c[2], stt["cases"], "Cases", "", PAL["amber"])
    kpi(c[3], f"{stt['db_mb']} MB", "Database", "", PAL["green"])
    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Health checks")
        need = ["keratitis_efficientnet_b0_syn.pt", "ulcer_pattern_efficientnet_b0.pt", "trachoma_tf_efficientnet_b0.pt",
                "unet_cornea.pt", "eye_reference.npz", "normal_gate.npz"]
        miss = [n for n in need if not (CKPT / n).exists()]
        st.markdown((pill("models: all present", "ok") if not miss else pill(f"models missing: {', '.join(miss)}", "refer"))
                    + " " + pill(f"ensemble members: {len(load_ensemble('keratitis'))}", "mut")
                    + " " + pill("demo mode ON" if settings.flag("demo_mode") else "production mode", "amber"
                                 if settings.flag("demo_mode") else "ok")
                    + " " + pill("Claude online" if ai.has_credentials() else "assistant offline", "mut"),
                    unsafe_allow_html=True)
        st.caption(f"Data folder: {settings.data_dir()} · photos: {stt['photos']} · audit entries: {stt['audit_log']}")
        if st.button("Test the natural cloud voice"):
            ok = bool(tts.synthesize("OcuLens voice check.", "en", "female", timeout=12))
            (st.success if ok else st.warning)("Cloud voice reachable." if ok else
                                               "Cloud voice not reachable: the browser's own voices will be used.")
        st.download_button("Download a database backup", db.backup_bytes(), on_click=_backup_clicked,
                           file_name=f"oculens_backup_{time.strftime('%Y%m%d_%H%M')}.db",
                           mime="application/octet-stream")
        st.caption("Photos live in the data folder's storage/ directory; back it up together with the database.")
    with right:
        st.markdown("#### Branding (white-label)")
        with st.form("branding"):
            org = st.text_input("Organisation name", db.setting("org_name"))
            tag = st.text_input("Tagline", db.setting("org_tagline"))
            ph = st.text_input("Support phone", db.setting("support_phone"))
            em = st.text_input("Support email", db.setting("support_email"))
            if st.form_submit_button("Save branding", type="primary"):
                for k, v in (("org_name", org), ("org_tagline", tag), ("support_phone", ph), ("support_email", em)):
                    db.set_setting(k, v.strip())
                db.audit(st.session_state["user"], "settings_changed", "branding", org)
                st.success("Saved. The name appears in the sidebar, the sign-in page and the legal pages.")
                st.rerun()
        st.caption("Security settings (session timeout, login attempts, lockout, demo mode, admin password) are set "
                   "with environment variables or Streamlit secrets: see the README.")


def page_legal():
    org, ph, em = db.setting("org_name"), db.setting("support_phone"), db.setting("support_email")
    hero("Legal & credits", "Terms of use, privacy notice, medical disclaimer, and data and software credits.")
    t = st.tabs(["Medical disclaimer", "Privacy notice", "Terms of use", "Credits"])
    t[0].markdown(legal.disclaimer(org))
    t[1].markdown(legal.privacy(org, ph, em))
    t[2].markdown(legal.terms(org, ph, em))
    t[3].markdown(legal.CREDITS)
    st.caption(f"{org} v{settings.VERSION}. Templates for the prototype: have them reviewed by a lawyer before real use.")


def page_about():
    hero("About OcuLens-AI", "Anatomy-aware, explainable anterior-eye disease screening.")
    st.markdown(f"""
Three trust pillars: **localisation** (cornea segmentation + anatomy-checked Grad-CAM++), **honest uncertainty**
(temperature scaling + conformal prediction + a referral gate + deep ensemble), and **actionability** (triage,
grounded summaries, doctor-in-the-loop recommendations, follow-up).

**This portal** — login & roles, patient records, screening with saved cases, a doctor review/recommendation
workflow, a synthetic-image generator, and an evaluation dashboard. Local SQLite storage (`portal/oculens.db`),
images under `portal/storage/`, fully offline on CPU.

**Models:** EfficientNet-B0 classifiers, U-Net segmentation, DDPM + CycleGAN augmentation, 5-model ensemble (50 epochs).
**Data:** 6 public, de-identified datasets (7,419 images), split by patient.

**Scope:** research prototype on public data — **not** a medical device. Clinical validation is future work.

**Team:** {TEAM}
""")


def seed_demo():
    """Populate a few demo patients + real screenings on first run so the portal isn't empty."""
    try:
        if db.stats()["patients"] > 0:
            return
        from oculens.quality.checks import assess_quality
        from oculens.uncertainty.conformal import prediction_set, should_refer
        cfg = get_cfg()
        plan = [
            ("Ravi Kumar", 58, "M", "keratitis", "keratitis_sample.jpg",
             "Dr. Syed Mohammed Yaseen", "Suspected microbial keratitis",
             "Start empirical fortified topical antibiotics; corneal scraping for smear/culture; review in 48 hours."),
            ("Anita Sharma", 34, "F", "ulcer_pattern", "ulcer_sample.jpg", None, None, None),
            ("Imran Pasha", 47, "M", "trachoma_tf", "trachoma_sample.jpg",
             "Dr. Mohammed Ayaan", "Trachomatous inflammation — follicular",
             "Azithromycin per WHO SAFE protocol; lid hygiene; community screening referral."),
            ("Lakshmi Devi", 62, "F", "keratitis", "keratitis_sample.jpg", None, None, None),
        ]
        for name, age, sex, task, sample, doc, dx, plan_txt in plan:
            sp = SAMPLES / sample
            if not sp.exists():
                continue
            pid = db.add_patient(name, age, sex)
            img = np.array(Image.open(sp).convert("RGB"))
            probs, classes, meta, x, model, _n, _mi = run_inference(img, task)
            o = int(np.argmax(probs))
            top, topp = classes[o], float(probs[o])
            pset = prediction_set(probs, meta.get("conformal_qhat", 1.0), classes)
            q = assess_quality(img, cfg.get("quality"))
            refer = should_refer(pset, top_prob=topp, min_top_prob=0.5)
            fn = f"seed_{uuid.uuid4().hex[:8]}.png"
            Image.fromarray(img).save(db.STORAGE / fn)
            cid = db.add_case(pid, task, fn, top, topp, ", ".join(pset), refer, q.ok, "Dr. Syed Mohammed Yaseen", mi=_mi)
            if doc:
                db.add_recommendation(cid, doc, dx, plan_txt)
    except Exception:  # noqa: BLE001
        pass


# ============================================================= shell
st.markdown("<style>[data-testid='stToolbar'],[data-testid='stDecoration'],#MainMenu,footer{visibility:hidden;}</style>",
            unsafe_allow_html=True)
inject_css()
if "user" not in st.session_state:
    if st.session_state.pop("timed_out", False):
        st.info("You were signed out after a period of inactivity. Please sign in again.")
    login_page()
    st.stop()

# idle timeout
_now = time.time()
if _now - st.session_state.get("last_active", _now) > settings.number("session_timeout_min") * 60:
    db.audit(st.session_state["user"], "session_timeout")
    st.session_state.clear()
    st.session_state["timed_out"] = True
    st.rerun()
st.session_state["last_active"] = _now

user = st.session_state["user"]
if user.get("must_change_password"):            # first sign-in with a temporary password
    hero("Choose a new password", "Your account uses a temporary password. Please set your own to continue.")
    with st.form("forcepw"):
        old = st.text_input("Temporary password", type="password")
        n1 = st.text_input("New password (8+ characters)", type="password")
        n2 = st.text_input("Repeat the new password", type="password")
        if st.form_submit_button("Save and continue", type="primary"):
            if len(n1) < 8 or n1 != n2:
                st.error("The new passwords must match and have at least 8 characters.")
            else:
                ok, msg = db.change_password(user["id"], old, n1)
                if ok:
                    db.audit(user, "password_changed")
                    st.session_state["user"] = db.get_user(user["id"])
                    st.rerun()
                st.error(msg)
    st.stop()
if settings.flag("demo_mode"):
    seed_demo()
    db.seed_patient_demo()
if st.session_state.get("pending_lang"):          # language saved on the profile page
    st.session_state["ai_lang"] = st.session_state.pop("pending_lang")
_initials = "".join(w[0] for w in (user.get("name") or "?").replace("Dr. ", "").split()[:2]).upper()
_role_col = {"doctor": "#19A6A2", "admin": "#E8A33D", "patient": "#FFB27A"}.get(user["role"], "#19A6A2")
st.sidebar.markdown(f"<div style='text-align:center;padding:6px 0'>{EYE_SVG.format(s=50, c='#8FE0DF')}</div>", unsafe_allow_html=True)
st.sidebar.markdown("<h2 style='text-align:center;color:#fff;margin:0'>OcuLens-AI</h2>", unsafe_allow_html=True)
st.sidebar.markdown(
    f"<div style='display:flex;align-items:center;gap:10px;margin:12px 4px 0;padding:10px;border-radius:14px;"
    f"background:rgba(255,255,255,.07)'><div style='width:40px;height:40px;border-radius:50%;display:grid;"
    f"place-items:center;font-weight:800;background:{_role_col};color:#072B33 !important'>{_initials}</div>"
    f"<div style='line-height:1.25'><div style='font-weight:700;font-size:.88rem'>{user['name']}</div>"
    f"<div style='font-size:.72rem;opacity:.75;text-transform:uppercase;letter-spacing:.08em'>{user['role']}</div></div></div>",
    unsafe_allow_html=True)
st.sidebar.divider()


# ---------------------------------------------------------------- AI assistant (text + voice)
from oculens.assistant import chat as ai  # noqa: E402
from voice import voice_bar, welcome_agent  # noqa: E402
from oculens.assistant.i18n import welcome_text  # noqa: E402

QUICK_QS = {
    "case": ["What does this result mean?", "How sure is the model?", "What should the patient do next?",
             "Which hospital should they visit?"],
    "general": ["What is keratitis?", "What is trachoma?", "How does OcuLens work?", "How do I take a good eye photo?"],
}


def case_facts(case):
    """The grounded facts the assistant may use about one saved case."""
    task = case["task"]
    pset = [label_of(task, c.strip()) for c in (case.get("pred_set") or "").split(",") if c.strip()]
    recs = db.recommendations_for(case["id"])
    mi = case.get("mi") or 0.0
    return {
        "case_id": case["id"], "patient": case.get("patient_name") or "walk-in",
        "screening": TASK_NAME.get(task, task), "eye": EYE_NAME.get(case.get("eye") or "", "") if case.get("eye") else "",
        "most_likely": label_of(task, case["top_label"]), "confidence": round(float(case["top_prob"]), 3),
        "prediction_set": pset, "referral_advised": bool(case["referred"]),
        "uncertainty_mi": round(float(mi), 3) if mi else None, "uncertainty_flagged": bool(mi and mi > MI_FLAG),
        "image_quality_ok": bool(case.get("quality_ok")), "review_status": case.get("status"),
        "doctor_notes": "; ".join(f"{r.get('doctor', 'doctor')}: {r.get('recommendation', '')}" for r in recs) if recs else "",
        "referral_hospitals": [{"hospital": h["hospital"], "area": h["area"], "focus": h["focus"], "doctor": h["doctor"]}
                               for h in BLR_REFERRALS.get(task, CORNEA_PANEL)],
    }


def _ask_ai(cid):
    st.session_state["assistant_case"] = cid
    st.session_state["nav"] = "AI assistant"


ASSISTANT_CSS = """
<style>
.ob-hero { display:flex; align-items:center; gap:18px; padding:18px 22px; border-radius:20px; margin:0 0 14px;
  background:linear-gradient(120deg,#0B3B40 0%,#0F7C80 58%,#19A6A2 100%); color:#fff;
  box-shadow:0 12px 30px rgba(15,124,128,.25); }
.ob-orb { width:62px; height:62px; flex:none; border-radius:50%; position:relative;
  background:radial-gradient(circle at 50% 50%,#06191C 0 21%,#3FD8B9 22% 27%,#1B8C91 28% 52%,#0E5D61 53% 68%,rgba(255,255,255,.22) 69% 100%); }
.ob-orb::before { content:""; position:absolute; left:34%; top:30%; width:13%; height:13%; border-radius:50%; background:#fff; opacity:.9; }
.ob-orb::after { content:""; position:absolute; inset:-7px; border-radius:50%; border:2px solid rgba(143,224,223,.75);
  animation:obpulse 2.4s ease-out infinite; }
@keyframes obpulse { from { transform:scale(.92); opacity:.9 } to { transform:scale(1.28); opacity:0 } }
.ob-hero h2 { margin:0; font-size:1.5rem; color:#fff; line-height:1.2; }
.ob-hero p { margin:3px 0 0; color:#CFEDEC; font-size:.92rem; }
.ob-chips { margin-left:auto; display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.ob-chip { background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.3); padding:5px 12px;
  border-radius:999px; font-size:.78rem; font-weight:700; white-space:nowrap; }
.ob-chip.on::before, .ob-chip.off::before { content:""; display:inline-block; width:8px; height:8px; border-radius:50%;
  margin-right:7px; vertical-align:1px; }
.ob-chip.on::before { background:#6EF2B4; box-shadow:0 0 0 3px rgba(110,242,180,.25); }
.ob-chip.off::before { background:#F5C26B; box-shadow:0 0 0 3px rgba(245,194,107,.25); }
.ob-row { display:flex; gap:10px; margin:14px 0; align-items:flex-end; }
.ob-row.ob-user { flex-direction:row-reverse; }
.ob-av { width:36px; height:36px; border-radius:50%; flex:none; display:grid; place-items:center; }
.ob-bot .ob-av { background:linear-gradient(135deg,#0F7C80,#19A6A2); box-shadow:0 4px 10px rgba(15,124,128,.3); }
.ob-user .ob-av { background:#E6EEF0; }
.ob-msg { max-width:80%; }
.ob-text { padding:12px 16px; border-radius:18px; line-height:1.55; font-size:.95rem; }
.ob-bot .ob-text { background:#fff; border:1px solid #DCE8E6; border-bottom-left-radius:6px;
  box-shadow:0 3px 12px rgba(18,58,64,.07); color:#123A40; }
.ob-user .ob-text { background:linear-gradient(135deg,#0F7C80,#14929A); color:#fff; border-bottom-right-radius:6px; }
.ob-text ul { margin:6px 0 2px 18px; padding:0; } .ob-text li { margin:2px 0; }
.ob-meta { font-size:.72rem; color:#7A8E93; margin:5px 10px 0; }
.ob-user .ob-meta { text-align:right; }
.ob-tag { display:inline-block; padding:1px 8px; border-radius:999px; background:#EEF5F5; color:#0F6B6E; font-weight:700; margin-left:6px; }
.ob-alert { display:flex; gap:10px; align-items:flex-start; margin:-4px 46px 14px auto; max-width:80%;
  background:#FDE8E6; color:#B42318; border:1.5px solid #F4B4A8; border-radius:14px; padding:10px 14px;
  font-weight:700; font-size:.88rem; line-height:1.45; }
.ob-alert svg { flex:none; margin-top:1px; }
.ob-typing { display:inline-flex; gap:5px; padding:4px 2px; }
.ob-typing span { width:8px; height:8px; border-radius:50%; background:#0F7C80; animation:obdot 1.2s infinite; }
.ob-typing span:nth-child(2) { animation-delay:.2s } .ob-typing span:nth-child(3) { animation-delay:.4s }
@keyframes obdot { 0%,80%,100% { opacity:.25; transform:translateY(0) } 40% { opacity:1; transform:translateY(-4px) } }
.ob-welcome b { color:#0F6B6E; }
.ob-panel-title { font-weight:800; color:#123A40; font-size:.82rem; letter-spacing:.06em; text-transform:uppercase; margin:4px 0 8px; }
.ob-case { display:flex; gap:12px; align-items:center; margin:2px 0 10px; }
.ob-case img { width:78px; height:78px; object-fit:cover; border-radius:50%; flex:none;
  box-shadow:0 0 0 3px #fff, 0 0 0 5px #0F7C80; }
.ob-case .t { font-size:.88rem; color:#123A40; line-height:1.45; }
.st-key-ai_quick .stButton>button { border-radius:999px !important; background:#F2FAF9 !important; color:#0F6B6E !important;
  border:1.5px solid #BFE3E1 !important; font-weight:600 !important; box-shadow:none !important; justify-content:flex-start !important; }
.st-key-ai_quick .stButton>button:hover { border-color:#0F7C80 !important; background:#E3F4F3 !important; transform:none !important; }
.st-key-ai_quick .stButton>button p { text-align:left; }
</style>
"""

_USER_SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="#5B7177"><circle cx="12" cy="8" r="4"/>'
             '<path d="M4 20c0-4 4-6 8-6s8 2 8 6z"/></svg>')


def _md_lite(text):
    """Escape, then a little markdown: **bold**, '- ' bullet lists, line breaks."""
    import html as _h
    out, items = [], []
    for line in _h.escape(text or "").split("\n"):
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line.strip())
        if s.startswith("- ") or s.startswith("* "):
            items.append(f"<li>{s[2:]}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        out.append(s)
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    return "<br>".join(x for x in out).replace("<br><ul>", "<ul>").replace("</ul><br>", "</ul>")


def _bubble(role, text, meta="", urgent=False, typing=False):
    bot = role == "assistant"
    av = EYE_SVG.format(s=26, c="#FFFFFF") if bot else _USER_SVG
    body = ('<div class="ob-typing"><span></span><span></span><span></span></div>' if typing else _md_lite(text))
    warn = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="#B42318"><path d="M12 2 1 21h22L12 2zm1 15h-2v-2h2v2zm0-4h-2V9h2v4z"/></svg>')
    alert = f'<div class="ob-alert">{warn}<span>{ai.URGENT}</span></div>' if urgent and not bot else ""
    cls = f"ob-row {'ob-bot' if bot else 'ob-user'}"
    return (f'<div class="{cls}"><div class="ob-av">{av}</div><div class="ob-msg">'
            f'<div class="ob-text">{body}</div>'
            f'{f"<div class=ob-meta>{meta}</div>" if meta else ""}</div></div>{alert}')


def _thumb_b64(path, size=160):
    im = Image.open(path).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((size, size))
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=85)
    return base64.b64encode(b.getvalue()).decode()


def page_assistant():
    import datetime as _dt
    ss = st.session_state
    st.markdown(ASSISTANT_CSS, unsafe_allow_html=True)
    online = ai.has_credentials()
    lang = ss.get("ai_lang", "en")
    st.markdown(
        f"<div class='ob-hero'><div class='ob-orb'></div><div><h2>OcuLens Assistant</h2>"
        f"<p>Ask about a screening result, an eye condition or how OcuLens works, by typing or by voice.</p></div>"
        f"<div class='ob-chips'><span class='ob-chip {'on' if online else 'off'}'>"
        f"{'Claude Opus 5.5 · online' if online else 'Offline · grounded answers'}</span>"
        f"<span class='ob-chip'>{ai.LANGUAGES.get(lang, ai.LANGUAGES['en'])[0]}</span></div></div>",
        unsafe_allow_html=True)

    chat_col, side = st.columns([2.35, 1], gap="large")

    # ---------------- context panel
    with side:
        with st.container(border=True):
            st.markdown("<div class='ob-panel-title'>Conversation</div>", unsafe_allow_html=True)
            is_patient = st.session_state["user"].get("role") == "patient"
            if is_patient:
                opts = {pp.T("General eye questions"): None}
                for r in db.cases_for_patient(st.session_state["user"].get("patient_id")):
                    eye = f" · {EYE_NAME[r['eye']]}" if r.get("eye") else ""
                    opts[f"{pp.T('My check')} #{r['id']} · {r['created_at'][:10]}{eye}"] = r["id"]
                if ss.get("assistant_case") not in opts.values():
                    ss["assistant_case"] = None
            else:
                opts = {"General questions (no case)": None}
                for r in db.list_cases():
                    eye = f" · {EYE_NAME[r['eye']]}" if r.get("eye") else ""
                    opts[f"#{r['id']} · {r['patient_name'] or 'walk-in'} · {label_of(r['task'], r['top_label'])}{eye}"] = r["id"]
            keys = list(opts)
            idx = next((i for i, k in enumerate(keys) if opts[k] == ss.get("assistant_case")), 0)
            ss["assistant_case"] = opts[st.selectbox("Talk about", keys, index=idx)]
            case = db.get_case(ss["assistant_case"]) if ss["assistant_case"] else None
            facts = case_facts(case) if case else None
            if case:
                ip = db.STORAGE / case["image_path"]
                img_html = f"<img src='data:image/jpeg;base64,{_thumb_b64(ip)}'>" if ip.exists() else ""
                st.markdown(
                    f"<div class='ob-case'>{img_html}<div class='t'><b>Case #{case['id']}</b> · {facts['patient']}<br>"
                    f"{facts['most_likely']} · {facts['confidence'] * 100:.0f}%<br>"
                    f"{pill('REFER', 'refer') if facts['referral_advised'] else pill('routine', 'ok')}"
                    f"{' ' + pill('uncertain', 'amber') if facts['uncertainty_flagged'] else ''}</div></div>",
                    unsafe_allow_html=True)
            st.caption(f"Language: **{ai.LANGUAGES[lang][0]}** · voice: **{ss.get('voice_gender', 'Female')}** "
                       "(change under Voice assistant in the sidebar)")
            audience = ("Patient-friendly" if is_patient else
                        st.selectbox("Answer style", ["Patient-friendly", "Clinician"], key="ai_aud"))
            speak_on = st.toggle("Read answers aloud", value=True, key="ai_speak")
        ck = f"chat_{ss['assistant_case'] or 'general'}"
        hist = ss.setdefault(ck, [])
        st.markdown("<div class='ob-panel-title'>Quick questions</div>", unsafe_allow_html=True)
        with st.container(key="ai_quick"):
            from oculens.assistant.patient_content import PATIENT_QS
            for q in (PATIENT_QS if is_patient else QUICK_QS["case" if case else "general"]):
                if st.button(pp.T(q) if is_patient else q, key=f"qq_{ck}_{q}", use_container_width=True):
                    ss["ai_pending"] = q
        b = st.columns(2)
        if b[0].button("Clear chat", key=f"clr_{ck}", use_container_width=True):
            ss[ck] = []
            ss.pop("ai_speak_payload", None)
            st.rerun()
        if hist:
            lines = [f"OcuLens AI assistant - {'case #' + str(case['id']) if case else 'general questions'}", ""]
            lines += [f"[{m.get('t', '')}] {'You' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in hist]
            lines += ["", "Screening aid, not a diagnosis. Please see an eye doctor to confirm any result."]
            b[1].download_button("Save chat", "\n".join(lines), use_container_width=True,
                                 file_name=f"oculens_chat_{ss['assistant_case'] or 'general'}.txt", key=f"dl_{ck}")
        if not online:
            st.caption("Offline answers come from the case data and a built-in eye-health knowledge base (about 90 "
                       "topics); case results, emergencies and next steps are also in Hindi, Kannada, Tamil and Telugu. "
                       "To switch on Claude, set ANTHROPIC_API_KEY (or run `ant auth login`) and restart the portal.")

    # ---------------- chat
    with chat_col:
        last = next((m["content"] for m in reversed(hist) if m["role"] == "assistant"), "")
        sp = ss.get("ai_speak_payload", {})
        heard = voice_bar(lang=ai.LANGUAGES[lang][1], speak=sp.get("text", ""), nonce=sp.get("nonce", ""), last=last,
                          auto_speak=speak_on, sound=_sound_on(), gender=ss.get("voice_gender", "Female").lower(),
                          audio=sp.get("audio", ""), key="ai_voice")
        thread = st.container()  # new messages go here, so the input box stays below them
        with thread:
            if not hist:
                topic = (f"case #{case['id']} ({facts['most_likely']}, {facts['confidence'] * 100:.0f}%)" if case
                         else "eye health and how OcuLens works")
                st.markdown(_bubble("assistant",
                                    f"Hello! I'm the **OcuLens Assistant**. Ask me about {topic}.\n"
                                    "- **What a result means** and how sure the model is\n"
                                    "- **What to do next** and which Bengaluru hospital to visit\n"
                                    "- **Keratitis, corneal ulcers and trachoma**, in plain words\n"
                                    "Tap the mic to ask by voice. I explain results; I don't diagnose or prescribe.",
                                    meta="OcuLens Assistant"), unsafe_allow_html=True)
            for m in hist:
                meta = m.get("t", "")
                if m["role"] == "assistant" and m.get("note"):
                    src = "Claude" if m.get("source") == "claude" else "Offline knowledge base"
                    meta += f"<span class='ob-tag'>{src}</span>"
                st.markdown(_bubble(m["role"], m["content"], meta=meta, urgent=m.get("urgent", False)), unsafe_allow_html=True)

        typed = st.chat_input("Type your question, or tap the mic")
        q = typed or heard or ss.pop("ai_pending", None)
        if q:
            now = _dt.datetime.now().strftime("%H:%M")
            urgent = ai.red_flag(q)
            hist.append({"role": "user", "content": q, "urgent": urgent, "t": now})
            with thread:
                st.markdown(_bubble("user", q, meta=now, urgent=urgent), unsafe_allow_html=True)
                box = st.empty()
            box.markdown(_bubble("assistant", "", typing=True), unsafe_allow_html=True)
            reply = ai.Reply(q, [{"role": m["role"], "content": m["content"]} for m in hist[:-1]], facts, lang, audience)
            acc = ""
            for i, chunk in enumerate(reply):
                acc += chunk
                if i % 4 == 0:
                    box.markdown(_bubble("assistant", acc + " ▍"), unsafe_allow_html=True)
            hist.append({"role": "assistant", "content": reply.text, "note": reply.note, "source": reply.source,
                         "t": _dt.datetime.now().strftime("%H:%M")})
            audio = ""
            if speak_on and ss.get("cloud_voice", True):
                with st.spinner("Preparing the voice..."):
                    audio = tts.data_url(reply.text, lang, ss.get("voice_gender", "Female"))
            ss["ai_speak_payload"] = {"text": reply.text, "nonce": uuid.uuid4().hex, "audio": audio}
            st.rerun()
        st.caption("The assistant explains screening results; it does not diagnose or prescribe. In an emergency, go to "
                   "an eye hospital. Voice input uses the browser's speech service. Natural voices come from Microsoft's "
                   "speech service when 'Natural cloud voice' is on (internet); otherwise the browser's voices are used.")

DOC_ACTIONS_CSS = """<style>
.st-key-doc_actions button { height:78px; border-radius:18px !important; font-size:1rem !important; font-weight:700 !important;
  background:linear-gradient(135deg,#FFFFFF,#EEF8F7) !important; color:#0A3D45 !important; border:1.5px solid #CDE8E5 !important;
  box-shadow:0 6px 18px rgba(10,61,69,.07); }
.st-key-doc_actions button:hover { border-color:#0F7C80 !important; transform:translateY(-2px); }
</style>"""
st.markdown(DOC_ACTIONS_CSS + pp.PATIENT_CSS, unsafe_allow_html=True)

if user["role"] == "patient":
    from types import SimpleNamespace
    _ctx = SimpleNamespace(TASK_PLAIN={k: pp.T(v) for k, v in TASK_PLAIN.items()}, EYE_NAME=EYE_NAME, IMG_TYPES=IMG_TYPES,
                           BLR_REFERRALS=BLR_REFERRALS, CORNEA_PANEL=CORNEA_PANEL, LANGUAGES=ai.LANGUAGES,
                           camera_capture=_camera_capture, open_rgb=_open_rgb, scanning_html=scanning_html,
                           play_sound=lambda k: play_sound(k, _sound_on()), analyse_image=analyse_image,
                           label_of=label_of, case_pdf_bytes=case_pdf_bytes, page_assistant=page_assistant)
    PAGES = pp.pages(_ctx)
else:
    PAGES = {"Dashboard": page_dashboard, "New screening": page_new_screening, "Cases": page_cases,
             "Patients": page_patients, "Appointments": page_appointments_doc, "Referral follow-up": page_referrals,
             "My schedule": page_schedule, "Follow-up": page_followup,
             "AI assistant": page_assistant, "Image generation": page_imagegen, "Evaluation": page_eval, "About": page_about}
    if user["role"] == "admin":
        PAGES["Users"] = page_users
        PAGES["Audit log"] = page_audit
        PAGES["System & branding"] = page_system
PAGES[pp.T("Legal & credits") if user["role"] == "patient" else "Legal & credits"] = page_legal

names = list(PAGES.keys())
default = st.session_state.pop("nav", None)
if default in names:          # programmatic jump (e.g. "Open this case"): set the menu before it renders
    st.session_state["menu"] = default
if st.session_state.get("menu") not in names:      # e.g. the patient changed language: keep the same page
    st.session_state["menu"] = names[min(st.session_state.get("menu_idx", 0), len(names) - 1)]
# A fixed key keeps the menu's own state; changing `index` each run would reset it to Dashboard.
choice = st.sidebar.radio("Menu", names, key="menu", label_visibility="collapsed")
st.session_state["menu_idx"] = names.index(choice)
st.sidebar.toggle("Sound effects", value=True, key="sfx_on", help="Scan, capture and confirmation sounds")
with st.sidebar.expander("Voice assistant", expanded=False):
    st.selectbox("Language", list(ai.LANGUAGES), format_func=lambda k: ai.LANGUAGES[k][0], key="ai_lang",
                 help="Language of the assistant and the spoken welcome")
    st.radio("Voice", ["Female", "Male"], horizontal=True, key="voice_gender")
    st.toggle("Natural cloud voice", value=True, key="cloud_voice",
              help="Natural Indian voices for all five languages in any browser. Needs internet; the spoken text is "
                   "sent to Microsoft's speech service. Off: the browser's own voices are used.")
    st.toggle("Spoken welcome after sign-in", value=True, key="welcome_on")
    if st.button("Play the welcome again", use_container_width=True):
        st.session_state["welcome_nonce"] = uuid.uuid4().hex
        st.session_state.pop("welcome_page", None)
if choice != "Cases":
    st.session_state["view_case"] = None
st.sidebar.divider()
if st.sidebar.button("Sign out", use_container_width=True):
    db.audit(user, "logout")
    st.session_state.clear()
    st.rerun()
st.sidebar.caption(f"{db.setting('org_name')} · v{settings.VERSION}\nScreening aid, not a medical device.")

# spoken welcome: shown on the first page after sign-in, read aloud once
if st.session_state.get("welcome_nonce") and st.session_state.get("welcome_on", True):
    wp = st.session_state.setdefault("welcome_page", choice)
    if wp == choice:
        _lang = st.session_state.get("ai_lang", "en")
        _role = "Doctor" if user["role"] == "doctor" else user["role"].title()
        _stats = db.stats()
        if user["role"] == "patient":
            _cs = db.cases_for_patient(user.get("patient_id")) if user.get("patient_id") else []
            _ap = db.appointments_for_patient(user.get("patient_id")) if user.get("patient_id") else []
            _stats["patient_status"] = ("none" if not _cs else "refer" if (_cs[0]["referred"] and not _ap)
                                        else "reviewed" if _cs[0]["status"] == "reviewed" else "pending")
        _wtext = welcome_text(user, _stats, _lang)
        _gender = st.session_state.get("voice_gender", "Female")
        _wkey = (st.session_state["welcome_nonce"], _lang, _gender)
        if st.session_state.get("cloud_voice", True) and st.session_state.get("welcome_audio_key") != _wkey:
            st.session_state["welcome_audio"] = tts.data_url(_wtext, _lang, _gender)
            st.session_state["welcome_audio_key"] = _wkey
        _waudio = st.session_state.get("welcome_audio", "") if st.session_state.get("cloud_voice", True) else ""
        if welcome_agent(_wtext, lang=ai.LANGUAGES[_lang][1], gender=_gender.lower(),
                         nonce=st.session_state["welcome_nonce"], sound=_sound_on(), audio=_waudio,
                         tag=f"{_role} · {ai.LANGUAGES[_lang][0]}", key="welcome_card"):
            st.session_state["welcome_nonce"] = None
    else:
        st.session_state["welcome_nonce"] = None   # greet only on the first page
try:
    PAGES[choice]()
except Exception as _e:  # noqa: BLE001
    if type(_e).__name__ in ("RerunException", "StopException", "RerunData"):
        raise                                   # Streamlit's own control flow
    _ref = uuid.uuid4().hex[:8].upper()
    LOG.exception("page %s failed (ref %s) for %s", choice, _ref, user.get("username"))
    db.audit(user, "error", choice, f"ref {_ref}: {type(_e).__name__}")
    st.error(f"Sorry, something went wrong on this page. Please try again; if it keeps happening, give the "
             f"administrator this reference: {_ref}.")
