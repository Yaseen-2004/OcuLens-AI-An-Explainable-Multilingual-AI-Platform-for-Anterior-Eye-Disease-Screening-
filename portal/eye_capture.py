"""Guided eye capture for the OcuLens-AI portal (Streamlit custom component, components v2).

A live camera view walks the user through photographing each eye in turn (right, then left),
in the style of an identity-verification flow: an on-screen guide circle, step chips, live
feedback, and a "hold still" ring that fills before an automatic capture.

Focus help works on every camera:
  * a live focus meter that uses the same measure as the portal's image-quality gate
    (variance of the Laplacian on a grayscale copy scaled to 512 px), so a green bar means
    the photo will pass the gate;
  * focus peaking - sharp edges are painted green on the preview;
  * camera controls when the device exposes them: auto / manual focus with a distance slider,
    a refocus button, zoom (digital zoom otherwise) and the torch.

Python receives JPEG data URLs and turns them into RGB arrays.
"""
from __future__ import annotations

import base64
import io

import numpy as np
import streamlit.components.v2 as _stc2
from PIL import Image

from sfx import SFX_FN

HTML = """<div class="ec"></div>"""

CSS = r"""
.ec { --tl:#0F7C80; --ok:#1E9E6A; --am:#E0A230; --bad:#E2664F; --ink:#123A40; --mut:#5B7177;
      font-family: inherit; color: var(--ink); }
.ec * { box-sizing: border-box; }
.ec-chips { display:flex; gap:8px; margin:0 0 8px; flex-wrap:wrap; }
.ec-chip { display:flex; align-items:center; gap:6px; padding:5px 11px; border-radius:999px; font-size:.82rem;
           font-weight:600; border:1.5px solid #C9DCDA; color:var(--mut); background:#fff; }
.ec-chip .n { width:20px; height:20px; border-radius:50%; display:grid; place-items:center; font-size:.72rem;
              background:#E7F1F0; color:var(--tl); }
.ec-chip.on { border-color:var(--tl); color:var(--tl); box-shadow:0 0 0 3px rgba(15,124,128,.12); }
.ec-chip.on .n { background:var(--tl); color:#fff; }
.ec-chip.ok { border-color:var(--ok); color:var(--ok); }
.ec-chip.ok .n { background:var(--ok); color:#fff; }
.ec-chip.skip { opacity:.55; text-decoration:line-through; }
.ec-title { font-weight:700; font-size:1.02rem; margin:2px 0 8px; }
.ec-stage { position:relative; width:100%; background:#0B1F22; border-radius:18px; overflow:hidden; min-height:220px; }
.ec-video { display:block; width:100%; height:auto; transform-origin:50% 50%; }
.ec-peak, .ec-still { position:absolute; pointer-events:none; }
.ec-still { display:none; object-fit:cover; border-radius:50%; box-shadow:0 0 0 4px var(--ok); }
.ec-mask { position:absolute; inset:0; pointer-events:none;
           background: radial-gradient(circle at 50% 50%, transparent 0, transparent var(--r,100px),
                       rgba(6,30,34,.62) calc(var(--r,100px) + 1px)); }
.ec-ring { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%) rotate(-90deg); pointer-events:none; }
.ec-ring circle { fill:none; stroke-width:2.6; }
.ec-ring .bg { stroke:rgba(255,255,255,.35); }
.ec-ring .fg { stroke:var(--bad); stroke-linecap:round; transition:stroke .25s; }
.ec-hint { position:absolute; left:50%; bottom:12px; transform:translateX(-50%); max-width:92%; text-align:center;
           background:rgba(6,30,34,.78); color:#fff; padding:6px 14px; border-radius:999px; font-size:.86rem; font-weight:600; }
.ec-arrow { position:absolute; top:50%; transform:translateY(-50%); color:#8FE0DF; font-size:2.2rem; font-weight:800;
            pointer-events:none; animation:ecnudge 1s ease-in-out infinite; text-shadow:0 2px 8px rgba(0,0,0,.4); }
@keyframes ecnudge { 0%,100% { opacity:.25 } 50% { opacity:1 } }
.ec-flash { position:absolute; inset:0; background:#fff; opacity:0; pointer-events:none; transition:opacity .35s; }
.ec-msg { position:absolute; inset:0; display:none; align-items:center; justify-content:center; text-align:center;
          padding:24px; color:#fff; font-size:.92rem; line-height:1.45; }
.ec-meter { display:flex; align-items:center; gap:10px; margin:10px 0 4px; font-size:.84rem; }
.ec-meter .lbl { font-weight:700; width:44px; }
.ec-bar { position:relative; flex:1; height:10px; border-radius:6px; background:#E3ECEB; overflow:hidden; }
.ec-fill { position:absolute; left:0; top:0; bottom:0; width:0; background:var(--bad); border-radius:6px; transition:width .15s, background .2s; }
.ec-mark { position:absolute; left:50%; top:-2px; bottom:-2px; width:2px; background:var(--ink); opacity:.45; }
.ec-meter .val { width:64px; text-align:right; color:var(--mut); font-variant-numeric:tabular-nums; }
.ec-checks { display:flex; gap:6px; flex-wrap:wrap; margin:4px 0 8px; }
.ec-ck { font-size:.76rem; padding:2px 9px; border-radius:999px; background:#FBEDEA; color:var(--bad); font-weight:600; }
.ec-ck.ok { background:#E5F4EC; color:var(--ok); }
.ec-controls, .ec-review, .ec-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:6px 0; }
.ec button { font:inherit; font-size:.86rem; font-weight:600; border-radius:10px; padding:7px 14px; cursor:pointer;
             border:1.5px solid #C9DCDA; background:#fff; color:var(--ink); }
.ec button:hover { border-color:var(--tl); color:var(--tl); }
.ec button.pri { background:var(--tl); border-color:var(--tl); color:#fff; }
.ec button.pri:hover { filter:brightness(1.08); color:#fff; }
.ec button:disabled { opacity:.45; cursor:not-allowed; }
.ec label { display:flex; align-items:center; gap:6px; font-size:.86rem; cursor:pointer; }
.ec details { margin:6px 0 2px; border:1px solid #DCE8E6; border-radius:12px; padding:6px 12px; background:#FAFCFC; }
.ec summary { cursor:pointer; font-weight:700; font-size:.88rem; color:var(--tl); }
.ec .row-l { width:96px; font-size:.84rem; font-weight:600; color:var(--mut); }
.ec input[type=range] { flex:1; min-width:120px; accent-color:var(--tl); }
.ec select { font:inherit; font-size:.86rem; padding:4px 8px; border-radius:8px; border:1.5px solid #C9DCDA; }
.ec-note { font-size:.8rem; color:var(--mut); margin:4px 0; }
.ec-done { display:none; }
.ec-done .thumbs { display:flex; gap:12px; flex-wrap:wrap; margin:8px 0; }
.ec-done figure { margin:0; text-align:center; font-size:.82rem; font-weight:600; color:var(--ink); }
.ec-done img { width:150px; height:150px; object-fit:cover; border-radius:50%; box-shadow:0 0 0 3px var(--ok); display:block; margin-bottom:6px; }
.hide { display:none !important; }
"""

JS = r"""
export default function (component) {
  const { parentElement, data, setStateValue } = component;
  const root = parentElement.querySelector('.ec');
  if (!root) return;
  if (root.__ecCleanup) { try { root.__ecCleanup(); } catch (e) { /* previous instance already gone */ } }

  const cfg = Object.assign({ instance: 'eyecap', eyes: ['R', 'L'], blur_min: 60, bmin: 40, bmax: 225,
                              glare_max: 0.08, contrast_min: 18, sound: true }, data || {});
  const STORE = (window.__oculensEyeCap = window.__oculensEyeCap || {});
  const S = (STORE[cfg.instance] = STORE[cfg.instance] ||
             { caps: {}, qual: {}, skipped: {}, step: 0, auto: true, peak: true, done: false, sent: false, sound: cfg.sound });
  const snd = (k, o) => { if (S.sound) ocSfx(k, o); };
  const EYES = cfg.eyes.filter((e) => e === 'R' || e === 'L');
  const NAME = { R: 'RIGHT eye', L: 'LEFT eye' };
  const LONG = { R: 'Right eye (OD)', L: 'Left eye (OS)' };
  const GUIDE = 0.62;           // guide-circle diameter as a share of the shorter frame side
  const MARGIN = 1.35;          // captured square = circle diameter x MARGIN (keeps lids and lashes in frame)
  const AUTO_LAP = cfg.blur_min * 1.25;   // auto-capture asks for a little headroom over the quality gate
  const HOLD_MS = 1200;         // how long everything must stay good before the automatic capture
  const STEADY = 7;             // mean frame-to-frame change (0-255) below which the view counts as steady

  root.innerHTML = `
    <div class="ec-live">
      <div class="ec-chips"></div>
      <div class="ec-title"></div>
      <div class="ec-stage">
        <video class="ec-video" playsinline muted autoplay></video>
        <canvas class="ec-peak"></canvas>
        <img class="ec-still" alt="captured eye">
        <div class="ec-mask"></div>
        <svg class="ec-ring"><circle class="bg"></circle><circle class="fg"></circle></svg>
        <div class="ec-arrow hide"></div>
        <div class="ec-hint">Starting camera...</div>
        <div class="ec-flash"></div>
        <div class="ec-msg"></div>
      </div>
      <div class="ec-meter"><span class="lbl">Focus</span><div class="ec-bar"><div class="ec-fill"></div><div class="ec-mark"></div></div><span class="val">-</span></div>
      <div class="ec-checks"></div>
      <div class="ec-controls">
        <button class="pri ec-shutter">Capture now</button>
        <label><input type="checkbox" class="ec-auto"> Auto-capture when sharp</label>
        <label><input type="checkbox" class="ec-snd"> Sound</label>
        <button class="ec-skip">Skip this eye</button>
        <button class="ec-switch hide">Switch camera</button>
        <button class="ec-retry hide">Retry camera</button>
      </div>
      <div class="ec-review hide">
        <button class="ec-retake">Retake</button>
        <button class="pri ec-use">Use this photo</button>
        <span class="ec-note ec-review-q"></span>
      </div>
      <details class="ec-adv" open>
        <summary>Focus &amp; camera options</summary>
        <div class="ec-row"><span class="row-l">Focus assist</span>
          <label><input type="checkbox" class="ec-peakon"> Highlight sharp edges (focus peaking)</label></div>
        <div class="ec-row ec-frow"><span class="row-l">Camera focus</span>
          <select class="ec-fmode"></select><input type="range" class="ec-fdist hide">
          <button class="ec-refocus hide">Refocus</button></div>
        <div class="ec-row"><span class="row-l">Zoom</span><input type="range" class="ec-zoom"><span class="ec-note ec-zoomv"></span></div>
        <div class="ec-row ec-torchrow hide"><span class="row-l">Light</span><label><input type="checkbox" class="ec-torch"> Torch / flash</label></div>
        <div class="ec-note ec-fnote"></div>
      </details>
    </div>
    <div class="ec-done"><div class="ec-title">Photos captured</div><div class="thumbs"></div>
      <div class="ec-note">Review them on the right, then press <b>Run screening</b>.</div></div>`;

  const $ = (s) => root.querySelector(s);
  const video = $('.ec-video'), stage = $('.ec-stage'), peak = $('.ec-peak'), still = $('.ec-still');
  const mask = $('.ec-mask'), ring = $('.ec-ring'), fg = $('.ec-ring .fg'), bg = $('.ec-ring .bg');
  const hint = $('.ec-hint'), flash = $('.ec-flash'), msg = $('.ec-msg'), arrow = $('.ec-arrow');
  const fill = $('.ec-fill'), fval = $('.ec-meter .val'), checks = $('.ec-checks');
  const shutter = $('.ec-shutter'), autoBox = $('.ec-auto'), skipBtn = $('.ec-skip'), switchBtn = $('.ec-switch');
  const retryBtn = $('.ec-retry'), review = $('.ec-review'), controls = $('.ec-controls');
  const fmode = $('.ec-fmode'), fdist = $('.ec-fdist'), refocus = $('.ec-refocus'), fnote = $('.ec-fnote');
  const zoom = $('.ec-zoom'), zoomv = $('.ec-zoomv'), torchRow = $('.ec-torchrow'), torch = $('.ec-torch');
  const peakOn = $('.ec-peakon'), sndBox = $('.ec-snd');

  let alive = true, stream = null, track = null, mirrored = true, hwZoom = false, dzoom = 1;
  let devices = [], devIdx = -1, raf = 0, lastTick = 0, hold = 0, armedAt = 0, prevTiny = null;
  let lastQ = null, pending = null, reviewing = false, lastTickT = 0;
  const work = document.createElement('canvas'), wctx = work.getContext('2d', { willReadFrequently: true });
  const tiny = document.createElement('canvas'); tiny.width = tiny.height = 64;
  const tctx = tiny.getContext('2d', { willReadFrequently: true });
  const pk = document.createElement('canvas'), pkctx = pk.getContext('2d');
  const shot = document.createElement('canvas'), sctx = shot.getContext('2d');
  autoBox.checked = S.auto; peakOn.checked = S.peak; sndBox.checked = S.sound;

  const curEye = () => EYES[S.step];

  function chipsHtml() {
    return EYES.map((e, i) => {
      const cls = S.caps[e] ? 'ok' : S.skipped[e] ? 'skip' : (i === S.step && !S.done ? 'on' : '');
      const mark = S.caps[e] ? '&#10003;' : String(i + 1);
      return `<span class="ec-chip ${cls}"><span class="n">${mark}</span>${LONG[e]}</span>`;
    }).join('');
  }

  function renderStep() {
    $('.ec-chips').innerHTML = chipsHtml();
    const e = curEye();
    if (!e) return;
    $('.ec-title').textContent = `Step ${S.step + 1} of ${EYES.length} · Bring the ${NAME[e]} into the circle`;
    // Arrow on the side of the screen where that eye shows up in the preview.
    // Mirrored preview (selfie view): the right eye appears on the right of the screen.
    const onRight = (e === 'R') === mirrored;
    arrow.textContent = onRight ? '››' : '‹‹';
    arrow.style.left = onRight ? '' : '14px';
    arrow.style.right = onRight ? '14px' : '';
    arrow.classList.toggle('hide', EYES.length < 2);
    const left = EYES.slice(S.step).filter((x) => !S.caps[x] && !S.skipped[x]).length;
    const any = EYES.some((x) => S.caps[x]);
    skipBtn.disabled = left <= 1 && !any;   // cannot skip the only remaining eye with nothing captured
  }

  function layout() {
    const w = stage.clientWidth, h = stage.clientHeight || video.clientHeight;
    const r = Math.max(40, (GUIDE * Math.min(w, h)) / 2);
    mask.style.setProperty('--r', r + 'px');
    const d = 2 * r + 10;
    ring.setAttribute('width', d); ring.setAttribute('height', d);
    ring.setAttribute('viewBox', `0 0 ${d} ${d}`);
    for (const c of [bg, fg]) { c.setAttribute('cx', d / 2); c.setAttribute('cy', d / 2); c.setAttribute('r', r + 2); }
    const circ = 2 * Math.PI * (r + 2);
    fg.style.strokeDasharray = circ; fg.dataset.circ = circ;
    const sq = 2 * r * MARGIN;
    Object.assign(still.style, { width: sq + 'px', height: sq + 'px', left: (w - sq) / 2 + 'px', top: (h - sq) / 2 + 'px',
                                 transform: mirrored ? 'scaleX(-1)' : 'none' });
    Object.assign(peak.style, { width: sq + 'px', height: sq + 'px', left: (w - sq) / 2 + 'px', top: (h - sq) / 2 + 'px',
                                transform: mirrored ? 'scaleX(-1)' : 'none' });
  }

  function applyTransform() {
    const parts = [];
    if (!hwZoom && dzoom !== 1) parts.push(`scale(${dzoom})`);
    if (mirrored) parts.push('scaleX(-1)');
    video.style.transform = parts.join(' ');
    zoomv.textContent = (hwZoom ? (+zoom.value).toFixed(1) : dzoom.toFixed(1)) + 'x' + (hwZoom ? '' : ' (digital)');
  }

  function cropRect() {
    // Whole-pixel rectangle: a fractional source rect makes the canvas interpolate every pixel,
    // which softens the photo and pulls the focus measure well below the server's value.
    const vw = video.videoWidth, vh = video.videoHeight;
    const side = Math.floor(Math.min(vw, vh, (Math.min(vw, vh) * GUIDE * MARGIN) / (hwZoom ? 1 : dzoom)));
    return { x: Math.floor((vw - side) / 2), y: Math.floor((vh - side) / 2), s: side };
  }

  function showMsg(text, retry) {
    msg.innerHTML = text; msg.style.display = 'flex';
    hint.classList.add('hide'); arrow.classList.add('hide');
    retryBtn.classList.toggle('hide', !retry);
  }

  async function start() {
    stop();
    msg.style.display = 'none'; hint.classList.remove('hide'); retryBtn.classList.add('hide');
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showMsg('The browser only allows the camera on a secure page.<br>Open the portal at <b>http://localhost:8501</b> on this computer, or use <b>Upload file</b>.', false);
      return;
    }
    const base = { width: { ideal: 1920 }, height: { ideal: 1080 } };
    const dev = devIdx >= 0 && devices[devIdx] ? devices[devIdx].deviceId : null;
    const video_c = dev ? Object.assign({ deviceId: { exact: dev } }, base) : Object.assign({ facingMode: { ideal: 'environment' } }, base);
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: video_c });
    } catch (e) {
      const blocked = e && (e.name === 'NotAllowedError' || e.name === 'SecurityError');
      showMsg(blocked ? 'Camera access was blocked.<br>Allow the camera from the icon in the browser address bar, then press <b>Retry camera</b>.'
                      : `No camera could be opened (${e && e.name ? e.name : 'error'}).<br>Connect a camera and press <b>Retry camera</b>, or use <b>Upload file</b>.`, true);
      return;
    }
    if (!alive) { stream.getTracks().forEach((t) => t.stop()); return; }
    video.srcObject = stream;
    try { await video.play(); } catch (e) { /* autoplay is muted, so play() normally succeeds */ }
    track = stream.getVideoTracks()[0];
    const st = track.getSettings ? track.getSettings() : {};
    mirrored = st.facingMode ? st.facingMode === 'user' : true;   // laptop webcams face the user
    try {
      devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput');
      if (devIdx < 0) devIdx = Math.max(0, devices.findIndex((d) => d.deviceId === st.deviceId));
    } catch (e) { devices = []; }
    switchBtn.classList.toggle('hide', devices.length < 2);
    setupCaps(st);
    await new Promise((res) => (video.readyState >= 2 ? res() : video.addEventListener('loadeddata', res, { once: true })));
    layout(); applyTransform(); renderStep();
    armedAt = performance.now() + 900;
    raf = requestAnimationFrame(loop);
  }

  function stop() {
    cancelAnimationFrame(raf); raf = 0;
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null; track = null; prevTiny = null;
  }

  async function constrain(c) {
    if (!track || !track.applyConstraints) return false;
    try { await track.applyConstraints({ advanced: [c] }); return true; } catch (e) { return false; }
  }

  function setupCaps(st) {
    const caps = track && track.getCapabilities ? track.getCapabilities() : {};
    // zoom: hardware when the camera has it, otherwise a digital crop
    if (caps.zoom && caps.zoom.max > caps.zoom.min) {
      hwZoom = true; zoom.min = caps.zoom.min; zoom.max = caps.zoom.max; zoom.step = caps.zoom.step || 0.1;
      zoom.value = st.zoom || caps.zoom.min;
    } else {
      hwZoom = false; zoom.min = 1; zoom.max = 3; zoom.step = 0.1; zoom.value = dzoom;
    }
    // focus
    const modes = caps.focusMode || [];
    fmode.innerHTML = '';
    const opt = (v, t) => { const o = document.createElement('option'); o.value = v; o.textContent = t; fmode.appendChild(o); };
    if (modes.includes('continuous')) opt('continuous', 'Auto (continuous)');
    if (modes.includes('single-shot')) opt('single-shot', 'Auto (single shot)');
    const manual = modes.includes('manual') && caps.focusDistance;
    if (manual) {
      opt('manual', 'Manual');
      fdist.min = caps.focusDistance.min; fdist.max = caps.focusDistance.max; fdist.step = caps.focusDistance.step || 0.01;
      fdist.value = st.focusDistance != null ? st.focusDistance : caps.focusDistance.min;
    }
    if (fmode.options.length) {
      fmode.disabled = false;
      fmode.value = modes.includes('continuous') ? 'continuous' : fmode.options[0].value;
      constrain({ focusMode: fmode.value });
      refocus.classList.toggle('hide', !(modes.includes('single-shot') || modes.includes('continuous')));
      fnote.textContent = manual ? 'Choose Manual to set the focus distance yourself; use the focus bar and the green edges to judge sharpness.'
                                 : 'This camera focuses automatically; press Refocus if the eye looks soft.';
    } else {
      opt('fixed', 'Fixed (not adjustable)'); fmode.disabled = true; refocus.classList.add('hide');
      fnote.textContent = 'This camera has fixed focus. Move slowly closer or farther until the focus bar turns green and the eyelashes light up green, then hold still.';
    }
    fdist.classList.toggle('hide', fmode.value !== 'manual');
    torchRow.classList.toggle('hide', !caps.torch);
  }

  // ---- per-frame analysis (mirrors oculens.quality.checks.assess_quality) ----
  function analyze() {
    const { x, y, s } = cropRect();
    const n = Math.max(32, Math.min(512, s));   // 1:1 copy when the crop is 512 px or smaller
    work.width = n; work.height = n;
    wctx.imageSmoothingQuality = 'high';
    wctx.drawImage(video, x, y, s, s, 0, 0, n, n);
    const d = wctx.getImageData(0, 0, n, n).data;
    const N = n * n, g = new Float32Array(N);
    let sum = 0, sum2 = 0, glare = 0;
    for (let i = 0, j = 0; i < d.length; i += 4, j++) {
      const v = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
      g[j] = v; sum += v; sum2 += v * v; if (v >= 250) glare++;
    }
    const mean = sum / N, std = Math.sqrt(Math.max(0, sum2 / N - mean * mean));
    const L = new Float32Array(N);
    let ls = 0, ls2 = 0, m = 0;
    for (let yy = 1; yy < n - 1; yy++) {
      const r = yy * n;
      for (let xx = 1; xx < n - 1; xx++) {
        const k = r + xx, v = g[k - 1] + g[k + 1] + g[k - n] + g[k + n] - 4 * g[k];
        L[k] = v; ls += v; ls2 += v * v; m++;
      }
    }
    const lm = ls / m, lap = ls2 / m - lm * lm;
    tctx.drawImage(video, x, y, s, s, 0, 0, 64, 64);
    const t = tctx.getImageData(0, 0, 64, 64).data;
    let motion = 99;
    if (prevTiny) {
      let acc = 0;
      for (let i = 0; i < t.length; i += 4) acc += Math.abs(t[i] - prevTiny[i]) + Math.abs(t[i + 1] - prevTiny[i + 1]) + Math.abs(t[i + 2] - prevTiny[i + 2]);
      motion = acc / (64 * 64 * 3);
    }
    prevTiny = new Uint8ClampedArray(t);
    return { lap, bright: mean, contrast: std, glare: glare / N, motion, L, n };
  }

  function drawPeaking(q) {
    if (!S.peak) { peak.style.display = 'none'; return; }
    peak.style.display = 'block';
    const n = q.n, thr = Math.max(18, 2.6 * Math.sqrt(Math.max(q.lap, 1)));
    pk.width = n; pk.height = n;
    const im = pkctx.createImageData(n, n), px = im.data;
    for (let k = 0; k < n * n; k++) {
      if (Math.abs(q.L[k]) > thr) { const o = k * 4; px[o] = 60; px[o + 1] = 255; px[o + 2] = 140; px[o + 3] = 230; }
    }
    pkctx.putImageData(im, 0, 0);
    const disp = parseFloat(peak.style.width) || 300;
    peak.width = Math.round(disp); peak.height = Math.round(disp);
    const c = peak.getContext('2d');
    c.clearRect(0, 0, peak.width, peak.height);
    c.drawImage(pk, 0, 0, peak.width, peak.height);
  }

  function setChecks(ok) {
    const items = [['focus', 'Focus'], ['light', 'Lighting'], ['glare', 'No glare'], ['contrast', 'Eye fills circle'], ['steady', 'Steady']];
    checks.innerHTML = items.map(([k, t]) => `<span class="ec-ck ${ok[k] ? 'ok' : ''}">${ok[k] ? '&#10003;' : '&#10007;'} ${t}</span>`).join('');
  }

  function loop(now) {
    if (!alive || !stream) return;
    raf = requestAnimationFrame(loop);
    if (reviewing || video.readyState < 2 || now - lastTick < 160) return;
    const dt = lastTick ? Math.min(400, now - lastTick) : 160;
    lastTick = now;
    let q;
    try { q = analyze(); } catch (e) { return; }
    lastQ = q;
    const ok = { focus: q.lap >= cfg.blur_min, light: q.bright >= cfg.bmin && q.bright <= cfg.bmax,
                 glare: q.glare <= cfg.glare_max, contrast: q.contrast >= cfg.contrast_min, steady: q.motion < STEADY };
    setChecks(ok);
    drawPeaking(q);
    const pct = Math.min(1, q.lap / (cfg.blur_min * 2));
    fill.style.width = (pct * 100).toFixed(1) + '%';
    fill.style.background = q.lap >= AUTO_LAP ? 'var(--ok)' : q.lap >= cfg.blur_min ? 'var(--am)' : 'var(--bad)';
    fval.textContent = q.lap >= AUTO_LAP ? 'Sharp' : q.lap >= cfg.blur_min ? 'OK' : 'Blurry';
    let h;
    if (!ok.light) h = q.bright < cfg.bmin ? 'Too dark - add light' : 'Too bright - reduce the light';
    else if (!ok.glare) h = 'Reflection on the eye - tilt the light or the camera';
    else if (!ok.contrast) h = 'Bring the eye closer so it fills the circle';
    else if (!ok.focus) h = 'Blurry - move slowly closer or farther, then hold still';
    else if (!ok.steady) h = 'Hold still...';
    else h = S.auto ? (q.lap >= AUTO_LAP ? 'Perfect - hold still' : 'Almost sharp - hold still') : 'Looks good - press Capture now';
    const allOk = ok.focus && ok.light && ok.glare && ok.contrast && ok.steady;
    const good = allOk && q.lap >= AUTO_LAP;
    if (now < armedAt) h = `Now the ${NAME[curEye()]}`;
    hint.textContent = h;
    if (S.auto && good && now >= armedAt) hold += dt; else hold = Math.max(0, hold - dt * 2);
    const circ = +fg.dataset.circ || 600, prog = Math.min(1, hold / HOLD_MS);
    fg.style.strokeDashoffset = circ * (1 - (S.auto ? prog : (allOk ? 1 : 0.15)));
    fg.style.stroke = good ? 'var(--ok)' : allOk ? 'var(--am)' : 'var(--bad)';
    // scanning ticks: rise in pitch as the hold-still ring fills
    if (S.auto && good && now >= armedAt && hold > 0 && now - lastTickT > 190) { snd('tick', { p: prog }); lastTickT = now; }
    if (S.auto && hold >= HOLD_MS) { hold = 0; capture(); }
  }

  function capture() {
    if (!stream || video.readyState < 2) return;
    const { x, y, s } = cropRect();
    const out = Math.max(64, Math.min(1024, s));  // full detail; only very large crops are scaled down
    shot.width = out; shot.height = out;
    sctx.imageSmoothingQuality = 'high';
    sctx.drawImage(video, x, y, s, s, 0, 0, out, out);
    const q = lastQ || analyze();
    pending = { url: shot.toDataURL('image/jpeg', 0.92),
                q: { focus: Math.round(q.lap), brightness: Math.round(q.bright), glare: +(q.glare * 100).toFixed(1) } };
    snd('shutter');
    flash.style.opacity = 0.85; setTimeout(() => (flash.style.opacity = 0), 120);
    still.src = pending.url; still.style.display = 'block'; peak.style.display = 'none';
    reviewing = true; hold = 0;
    controls.classList.add('hide'); review.classList.remove('hide');
    $('.ec-review-q').textContent = `Focus ${pending.q.focus} (gate needs ${cfg.blur_min}) · brightness ${pending.q.brightness}`;
    hint.textContent = `${LONG[curEye()]} captured - keep it or retake`;
  }

  function leaveReview() {
    reviewing = false; pending = null; still.style.display = 'none';
    review.classList.add('hide'); controls.classList.remove('hide');
    armedAt = performance.now() + 1500; prevTiny = null;
  }

  function advance() {
    while (S.step < EYES.length && (S.caps[EYES[S.step]] || S.skipped[EYES[S.step]])) S.step++;
    if (S.step >= EYES.length) return finish();
    renderStep();
  }

  function finish() {
    S.done = true; stop();
    $('.ec-live').classList.add('hide');
    const done = $('.ec-done'); done.style.display = 'block';
    done.querySelector('.thumbs').innerHTML = EYES.filter((e) => S.caps[e])
      .map((e) => `<figure><img src="${S.caps[e]}">${LONG[e]}</figure>`).join('');
    if (!S.sent) {
      S.sent = true;
      setTimeout(() => snd('success'), 320);
      setStateValue('captures', { R: S.caps.R || null, L: S.caps.L || null, quality: S.qual, t: Date.now() });
    }
  }

  // ---- events ----
  shutter.onclick = () => capture();
  autoBox.onchange = () => { S.auto = autoBox.checked; hold = 0; };
  peakOn.onchange = () => { S.peak = peakOn.checked; };
  sndBox.onchange = () => { S.sound = sndBox.checked; if (S.sound) ocSfx('confirm'); };
  skipBtn.onclick = () => { const e = curEye(); if (!e) return; S.skipped[e] = true; hold = 0; armedAt = performance.now() + 1200; advance(); };
  $('.ec-retake').onclick = () => { snd('retake'); leaveReview(); };
  $('.ec-use').onclick = () => {
    const e = curEye();
    if (e && pending) { S.caps[e] = pending.url; S.qual[e] = pending.q; snd('confirm'); }
    leaveReview(); advance();
  };
  switchBtn.onclick = () => { if (devices.length > 1) { devIdx = (devIdx + 1) % devices.length; start(); } };
  retryBtn.onclick = () => start();
  zoom.oninput = () => {
    if (hwZoom) constrain({ zoom: +zoom.value }); else dzoom = +zoom.value;
    applyTransform();
  };
  fmode.onchange = () => {
    fdist.classList.toggle('hide', fmode.value !== 'manual');
    constrain(fmode.value === 'manual' ? { focusMode: 'manual', focusDistance: +fdist.value } : { focusMode: fmode.value });
  };
  fdist.oninput = () => constrain({ focusMode: 'manual', focusDistance: +fdist.value });
  refocus.onclick = async () => {
    const back = fmode.value;
    await constrain({ focusMode: 'single-shot' });
    setTimeout(() => { if (back !== 'single-shot' && back !== 'manual') constrain({ focusMode: back }); }, 900);
  };
  torch.onchange = () => constrain({ torch: torch.checked });
  const ro = new ResizeObserver(() => layout());
  ro.observe(stage);

  if (S.done) { finish(); } else { renderStep(); start(); }

  const cleanup = () => { alive = false; stop(); ro.disconnect(); root.__ecCleanup = null; };
  root.__ecCleanup = cleanup;
  return cleanup;
}
"""

JS = SFX_FN + JS

_NAME = "oculens_eye_capture"
_mount = None


def _component():
    """Register on first use, and again if the running Streamlit runtime does not know the
    component (registration at import time can land in a different registry than the one used
    to mount, e.g. when the module was imported before the runtime started)."""
    global _mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _mount is None or (registry is not None and registry.get(_NAME) is None):
        _mount = _stc2.component(_NAME, html=HTML, css=CSS, js=JS)
    return _mount


def _decode(data_url: str) -> np.ndarray | None:
    try:
        b64 = data_url.split(",", 1)[1]
        return np.array(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))
    except Exception:  # noqa: BLE001
        return None


def eye_capture(instance: str, eyes=("R", "L"), quality: dict | None = None, key: str | None = None, sound: bool = True):
    """Show the guided capture. Returns {"R": rgb_array, "L": rgb_array} (only the eyes captured)
    once the user has finished, otherwise None. `quality` is the portal's quality config, so the
    live focus meter uses the same thresholds as the image-quality gate."""
    q = quality or {}
    data = {"instance": instance, "eyes": list(eyes),
            "blur_min": float(q.get("blur_min_laplacian_var", 60.0)),
            "bmin": float(q.get("brightness_min", 40.0)), "bmax": float(q.get("brightness_max", 225.0)),
            "glare_max": float(q.get("glare_max_fraction", 0.08)),
            "contrast_min": float(q.get("contrast_min_std", 18.0)), "sound": bool(sound)}
    res = _component()(key=key or f"eyecap_{instance}", data=data, on_captures_change=lambda: None)
    caps = res.get("captures") if hasattr(res, "get") else getattr(res, "captures", None)
    if not caps:
        return None
    out = {}
    for e in ("R", "L"):
        u = caps.get(e)
        arr = _decode(u) if u else None
        if arr is not None:
            out[e] = arr
    return out or None
