"""Sound effects for the OcuLens-AI portal, synthesized in the browser with the Web Audio API
(no audio files, works offline). Browsers only allow sound after the user has interacted with the
page; every sound here follows a click (Run screening, Capture, Use this photo), so that is met.

SFX_FN is plain JavaScript shared with the guided-capture component; play() is the Python helper
used by the screening page.
"""
from __future__ import annotations

import uuid

import streamlit.components.v2 as _stc2

SFX_FN = r"""
function ocSfx(kind, opt) {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = window.__ocAudio || (window.__ocAudio = new AC());
    if (ctx.state === 'suspended') ctx.resume();
    (window.__ocSfxLog = window.__ocSfxLog || []).push(kind);
    const t = ctx.currentTime + 0.01, out = ctx.destination;
    const tone = (f0, f1, at, dur, type, vol) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = type || 'sine';
      o.frequency.setValueAtTime(f0, t + at);
      if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + at + dur);
      g.gain.setValueAtTime(0.0001, t + at);
      g.gain.exponentialRampToValueAtTime(vol || 0.1, t + at + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t + at + dur);
      o.connect(g); g.connect(out); o.start(t + at); o.stop(t + at + dur + 0.03);
    };
    const noise = (at, dur, freq, vol) => {
      const n = Math.floor(ctx.sampleRate * dur), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
      for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3);
      const src = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      src.buffer = b; f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = 0.9; g.gain.value = vol;
      src.connect(f); f.connect(g); g.connect(out); src.start(t + at);
    };
    switch (kind) {
      case 'tick': { const p = Math.max(0, Math.min(1, (opt && opt.p) || 0)); tone(520 + 760 * p, 0, 0, 0.045, 'sine', 0.05); break; }
      case 'shutter': noise(0, 0.07, 3200, 0.55); noise(0.085, 0.06, 1800, 0.35); tone(150, 70, 0, 0.09, 'triangle', 0.12); break;
      case 'confirm': tone(880, 0, 0, 0.13, 'sine', 0.12); tone(1318.5, 0, 0.11, 0.26, 'sine', 0.12); break;
      case 'success': tone(784, 0, 0, 0.16, 'sine', 0.1); tone(988, 0, 0.12, 0.16, 'sine', 0.1); tone(1318.5, 0, 0.24, 0.42, 'sine', 0.11); break;
      case 'retake': tone(420, 300, 0, 0.14, 'sine', 0.07); break;
      case 'scan':
        tone(260, 1500, 0, 0.85, 'sine', 0.045);
        [0, 0.28, 0.56].forEach((d, i) => tone(1250 + i * 180, 0, d, 0.09, 'triangle', 0.05));
        break;
      case 'alert': tone(520, 0, 0, 0.14, 'square', 0.04); tone(390, 0, 0.16, 0.26, 'square', 0.04); break;
    }
  } catch (e) { /* sound is decoration: never break the page */ }
}
"""

_JS = SFX_FN + r"""
export default function (component) {
  const { data } = component;
  if (!data || !data.kind || !data.nonce) return;
  const seen = (window.__ocSfxSeen = window.__ocSfxSeen || new Set());
  if (seen.has(data.nonce)) return;      // a re-render must not replay the sound
  seen.add(data.nonce);
  ocSfx(data.kind);
}
"""

_NAME = "oculens_sfx"
_mount = None


def _component():
    global _mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _mount is None or (registry is not None and registry.get(_NAME) is None):
        _mount = _stc2.component(_NAME, html="<span></span>", js=_JS)
    return _mount


def play(kind: str, enabled: bool = True) -> None:
    """Play one sound in the browser: scan, confirm, success, alert, shutter, retake, tick."""
    if not enabled:
        return
    nonce = uuid.uuid4().hex
    _component()(key=f"sfx_{nonce}", data={"kind": kind, "nonce": nonce})
