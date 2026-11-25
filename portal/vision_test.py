"""At-home vision test (Streamlit custom component): a tumbling-E acuity chart sized for the screen and the
viewing distance, and an Amsler grid check. A screening aid only: it does not replace a clinic vision test.

Size: the patient first matches a box to a bank card (85.6 mm wide), which gives pixels per millimetre. A letter
for logMAR L at distance d is 5 arc-minutes x 10^L tall: h = d * tan(5') * 10^L. Levels from logMAR 1.0 (6/60) to
0.0 (6/6); a level is passed with at least 2 of 3 correct answers.
"""
from __future__ import annotations

import math

import streamlit.components.v2 as _stc2

LEVELS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
SNELLEN = {1.0: "6/60", 0.8: "6/38", 0.6: "6/24", 0.5: "6/19", 0.4: "6/15", 0.3: "6/12", 0.2: "6/9.5", 0.1: "6/7.5",
           0.0: "6/6"}


def letter_mm(logmar: float, distance_m: float) -> float:
    return distance_m * 1000 * math.tan(math.radians(5 / 60)) * 10 ** logmar


def snellen(logmar):
    return SNELLEN.get(round(logmar, 1), f"logMAR {logmar:.1f}") if logmar is not None else "worse than 6/60"


_HTML = """<div class="vt"></div>"""
_CSS = r"""
.vt { font-family: inherit; background:#fff; border:1px solid #E2EEEC; border-radius:22px; padding:18px 20px;
      box-shadow:0 8px 24px rgba(10,61,69,.07); }
.vt h4 { margin:0 0 6px; color:#0A2A33; font-size:1.1rem; }
.vt p { margin:.3rem 0; color:#41575C; font-size:.92rem; }
.vt .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-top:10px; }
.vt button { font:inherit; font-weight:700; padding:10px 18px; border-radius:14px; border:0; cursor:pointer; color:#fff;
             background:linear-gradient(135deg,#0F7C80,#36B3A8); }
.vt button.alt { background:#EEF6F5; color:#0F6B6E; border:1.5px solid #BFE3E1; }
.vt button.sel { outline:3px solid #FFB27A; }
.vt .card { height:54px; border-radius:8px; background:linear-gradient(135deg,#3B5BA5,#5A79C4); margin:12px 0;
            display:grid; place-items:center; color:#fff; font-weight:700; font-size:.8rem; }
.vt input[type=range] { width:100%; }
.vt .stage { min-height:260px; display:grid; place-items:center; background:#FBFDFD; border-radius:16px; margin-top:10px;
             border:1px dashed #CFE6E3; }
.vt .arrows { display:grid; grid-template-columns:repeat(3, 64px); gap:8px; justify-content:center; margin-top:12px; }
.vt .arrows button { height:52px; padding:0; font-size:1.3rem; }
.vt .prog { height:8px; background:#E7EEEE; border-radius:4px; overflow:hidden; margin-top:10px; }
.vt .prog i { display:block; height:100%; background:linear-gradient(90deg,#0F7C80,#36B3A8); }
.vt .grid { width:300px; height:300px; position:relative;
  background-image: linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px);
  background-size: 15px 15px; border:1px solid #333; }
.vt .grid .dot { position:absolute; left:50%; top:50%; width:10px; height:10px; margin:-5px; border-radius:50%; background:#000; }
.vt .res { font-family:'Sora','Inter',sans-serif; font-size:2rem; font-weight:800; color:#0F7C80; }
"""
_JS = r"""
export default function (component) {
  const { parentElement, data, setTriggerValue } = component;
  const root = parentElement.querySelector('.vt');
  if (!root) return;
  const L = Object.assign({}, data && data.labels);
  const LEVELS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0];
  const SN = {'1':'6/60','0.8':'6/38','0.6':'6/24','0.5':'6/19','0.4':'6/15','0.3':'6/12','0.2':'6/9.5','0.1':'6/7.5','0':'6/6'};
  const S = { pxmm: parseFloat(localStorage.getItem('oc_pxmm') || '0') || 0, eye: 'Right', dist: 2, level: 0,
              trial: 0, right: 0, dir: 0, passed: null };
  const DIRS = ['right', 'down', 'left', 'up'];        // rotation 0, 90, 180, 270
  const esc = (x) => String(x).replace(/[&<>]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

  function calib() {
    const w0 = S.pxmm ? Math.round(S.pxmm * 85.6) : 320;
    root.innerHTML = `<h4>${esc(L.calTitle)}</h4><p>${esc(L.calText)}</p>
      <div class="card" style="width:${w0}px">ATM / BANK CARD</div>
      <input type="range" min="180" max="700" value="${w0}"><div class="row"><button class="go">${esc(L.next)}</button></div>`;
    const card = root.querySelector('.card'), r = root.querySelector('input');
    r.oninput = () => { card.style.width = r.value + 'px'; };
    root.querySelector('.go').onclick = () => { S.pxmm = r.value / 85.6; localStorage.setItem('oc_pxmm', S.pxmm); setup(); };
  }
  function setup() {
    root.innerHTML = `<h4>${esc(L.setupTitle)}</h4><p>${esc(L.setupText)}</p>
      <div class="row"><b>${esc(L.eye)}:</b><button class="alt e" data-v="Right">${esc(L.right)}</button>
      <button class="alt e" data-v="Left">${esc(L.left)}</button></div>
      <div class="row"><b>${esc(L.distance)}:</b><button class="alt d" data-v="2">2 m</button><button class="alt d" data-v="3">3 m</button></div>
      <div class="row"><button class="go">${esc(L.start)}</button><button class="alt grid-b">${esc(L.amsler)}</button>
      <button class="alt recal">${esc(L.recal)}</button></div>`;
    const mark = () => { root.querySelectorAll('.e').forEach((b) => b.classList.toggle('sel', b.dataset.v === S.eye));
                         root.querySelectorAll('.d').forEach((b) => b.classList.toggle('sel', +b.dataset.v === S.dist)); };
    root.querySelectorAll('.e').forEach((b) => b.onclick = () => { S.eye = b.dataset.v; mark(); });
    root.querySelectorAll('.d').forEach((b) => b.onclick = () => { S.dist = +b.dataset.v; mark(); });
    mark();
    root.querySelector('.go').onclick = () => { S.level = 0; S.trial = 0; S.right = 0; S.passed = null; show(); };
    root.querySelector('.grid-b').onclick = amsler;
    root.querySelector('.recal').onclick = calib;
  }
  function letterPx(lm) { return S.dist * 1000 * Math.tan(5 / 60 * Math.PI / 180) * Math.pow(10, lm) * S.pxmm; }
  function eSvg(px, rot) {   // a 5x5 tumbling E, open side to the right at rotation 0
    return `<svg width="${px}" height="${px}" viewBox="0 0 5 5" style="transform:rotate(${rot}deg)" shape-rendering="crispEdges">
      <rect x="0" y="0" width="5" height="1"/><rect x="0" y="2" width="5" height="1"/><rect x="0" y="4" width="5" height="1"/>
      <rect x="0" y="0" width="1" height="5"/></svg>`;
  }
  function show() {
    const lm = LEVELS[S.level];
    S.dir = Math.floor(Math.random() * 4);
    const px = Math.max(5, letterPx(lm));
    const pct = Math.round(100 * (S.level * 3 + S.trial) / (LEVELS.length * 3));
    root.innerHTML = `<h4>${esc(L.testTitle)} · ${esc(S.eye === 'Right' ? L.right : L.left)}</h4>
      <p>${esc(L.testText)}</p><div class="stage">${eSvg(px, S.dir * 90)}</div>
      <div class="arrows"><span></span><button data-d="3">&#8593;</button><span></span>
      <button data-d="2">&#8592;</button><button class="alt" data-d="-1">?</button><button data-d="0">&#8594;</button>
      <span></span><button data-d="1">&#8595;</button><span></span></div>
      <div class="prog"><i style="width:${pct}%"></i></div>
      <p style="font-size:.8rem">${esc(L.level)} ${S.level + 1}/${LEVELS.length} · ${px < 7 ? esc(L.tooSmall) : ''}</p>`;
    root.querySelectorAll('.arrows button').forEach((b) => b.onclick = () => answer(+b.dataset.d));
  }
  function answer(d) {
    if (d === S.dir) S.right++;
    S.trial++;
    if (S.trial < 3) return show();
    if (S.right >= 2) { S.passed = LEVELS[S.level]; S.level++; S.trial = 0; S.right = 0;
                        if (S.level < LEVELS.length) return show(); }
    finish();
  }
  function finish() {
    const sn = S.passed === null ? L.worse : SN[String(S.passed)];
    root.innerHTML = `<h4>${esc(L.resTitle)} · ${esc(S.eye === 'Right' ? L.right : L.left)}</h4>
      <div class="res">${esc(sn)}</div><p>${esc(L.resText)}</p>
      <div class="row"><button class="again">${esc(L.otherEye)}</button><button class="alt grid-b">${esc(L.amsler)}</button></div>`;
    setTriggerValue('result', { kind: 'acuity', eye: S.eye, logmar: S.passed, distance: S.dist, t: Date.now() });
    root.querySelector('.again').onclick = () => { S.eye = S.eye === 'Right' ? 'Left' : 'Right'; setup(); };
    root.querySelector('.grid-b').onclick = amsler;
  }
  function amsler() {
    root.innerHTML = `<h4>${esc(L.amsTitle)}</h4><p>${esc(L.amsText)}</p>
      <div class="stage"><div class="grid"><span class="dot"></span></div></div>
      <div class="row"><button class="ok">${esc(L.amsOk)}</button><button class="alt bad">${esc(L.amsBad)}</button>
      <button class="alt back">${esc(L.back)}</button></div>`;
    const send = (v) => { setTriggerValue('result', { kind: 'amsler', eye: S.eye, amsler: v, t: Date.now() });
                          root.querySelector('p').textContent = v === 'normal' ? L.amsOkRes : L.amsBadRes; };
    root.querySelector('.ok').onclick = () => send('normal');
    root.querySelector('.bad').onclick = () => send('distorted');
    root.querySelector('.back').onclick = setup;
  }
  // arrow keys work for the acuity test
  if (!window.__vtKeys) { window.__vtKeys = true;
    window.addEventListener('keydown', (e) => { const m = {ArrowRight:0, ArrowDown:1, ArrowLeft:2, ArrowUp:3}[e.key];
      const btn = document.querySelector(`[data-d="${m}"]`) || [...document.querySelectorAll('*')].map((x) => x.shadowRoot)
        .filter(Boolean).map((r) => r.querySelector(`.vt [data-d="${m}"]`)).find(Boolean);
      if (m !== undefined && btn) { e.preventDefault(); btn.click(); } }); }
  S.pxmm ? setup() : calib();
}
"""
_NAME = "oculens_vision_test"
_mount = None


def _component():
    global _mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _mount is None or (registry is not None and registry.get(_NAME) is None):
        _mount = _stc2.component(_NAME, html=_HTML, css=_CSS, js=_JS)
    return _mount


def vision_test(labels: dict, key="vt"):
    """Returns the latest result dict on the run it arrives, else None."""
    res = _component()(key=key, data={"labels": labels}, on_result_change=lambda: None)
    v = res.get("result") if hasattr(res, "get") else getattr(res, "result", None)
    return v or None
