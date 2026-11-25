"""Voice for the OcuLens assistant (Streamlit custom component, components v2).

* Speech to text: the browser's Web Speech API (Chrome / Edge). The browser sends the audio to its own speech
  service, so voice input needs internet; typing always works.
* Text to speech: the browser's speechSynthesis with the computer's installed voices (works offline). Long
  answers are read sentence by sentence so the browser does not cut them off.
"""
from __future__ import annotations

import streamlit.components.v2 as _stc2

from sfx import SFX_FN

# Text to speech shared by the assistant bar and the welcome greeting. Each sentence is read by a voice for its own
# script (an English sentence inside a Hindi answer gets an Indian English voice), and natural Indian voices are
# preferred: Microsoft Edge offers "Online (Natural)" voices for en-IN, hi-IN, kn-IN, ta-IN and te-IN.
TTS_FN = r"""
const OC_FEMALE = /Neerja|Heera|Kalpana|Swara|स्वरा|ಸಪ್ನಾ|Sapna|பல்லவி|Pallavi|శ్రుతి|Shruti|Female|Zira/i;
const OC_MALE = /Prabhat|Ravi|Hemant|Madhur|मधुर|ಗಗನ್|Gagan|வள்ளுவர்|Valluvar|మోహన్|Mohan|Male|David|Mark/i;
function ocScriptLang(t, fallback) {
  if (/[\u0900-\u097F]/.test(t)) return 'hi-IN';
  if (/[\u0C80-\u0CFF]/.test(t)) return 'kn-IN';
  if (/[\u0B80-\u0BFF]/.test(t)) return 'ta-IN';
  if (/[\u0C00-\u0C7F]/.test(t)) return 'te-IN';
  return /[A-Za-z]/.test(t) ? 'en-IN' : fallback;
}
function ocPickVoice(lang, gender) {
  const vs = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  const norm = (x) => (x || '').replace('_', '-').toLowerCase();
  const want = norm(lang), pre = want.split('-')[0];
  let pool = vs.filter((v) => norm(v.lang) === want);
  if (!pool.length && pre === 'en') pool = vs.filter((v) => /^en-(gb|au|us)/.test(norm(v.lang)));
  if (!pool.length) pool = vs.filter((v) => norm(v.lang).startsWith(pre));
  const like = gender === 'male' ? OC_MALE : OC_FEMALE;
  const score = (v) => (/Natural|Neural/i.test(v.name) ? 8 : 0) + (/Online|Google/i.test(v.name) ? 3 : 0)
    + (like.test(v.name) ? 4 : 0) + (norm(v.lang) === want ? 2 : 0) + (norm(v.lang) === 'en-gb' ? 1 : 0);
  pool.sort((a, b) => score(b) - score(a));
  return pool[0] || null;
}
function ocStopAll() {
  try { if (window.__ocPlayer) { window.__ocPlayer.pause(); window.__ocPlayer = null; } } catch (e) { /* gone */ }
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* none */ }
}
// Plays server-made audio (natural Indian voice in any browser); falls back to the browser's voices.
function ocSay(text, audio, opts) {
  const o = Object.assign({ onstart: null, onend: null, ontime: null, onerror: null }, opts || {});
  const log = (window.__ocVoiceLog = window.__ocVoiceLog || []);
  ocStopAll();
  if (!audio) return ocSpeak(text, o);
  return new Promise((resolve) => {
    const a = new Audio(audio);
    window.__ocPlayer = a;
    let fell = false;
    const fallback = (why) => { if (fell) return; fell = true; log.push('audio-fallback:' + why); ocSpeak(text, o).then(resolve); };
    a.onplay = () => { if (o.onstart) o.onstart(); };
    a.ontimeupdate = () => { if (o.ontime && a.duration) o.ontime(a.currentTime / a.duration); };
    a.onended = () => { if (o.onend) o.onend(); };
    a.onerror = () => fallback('error');
    a.play().then(() => { log.push('audio:server'); resolve({ voices: ['server'] }); })
      .catch((e) => { if (e && e.name === 'NotAllowedError') { if (o.onerror) o.onerror({ error: 'not-allowed' }); resolve({}); }
                      else fallback(e && e.name); });
  });
}
function ocCleanSpeech(t) {
  return (t || '').replace(/https?:\/\/\S+/g, '').replace(/[*_#>`|]/g, ' ').replace(/^\s*[-•]\s*/gm, '')
    .replace(/\bDr\./g, 'Doctor').replace(/\s+/g, ' ').trim();
}
function ocSpeak(text, opts) {
  const synth = window.speechSynthesis;
  const o = Object.assign({ lang: 'en-IN', gender: 'female', onstart: null, onend: null, onchunk: null, onerror: null }, opts || {});
  const log = (window.__ocVoiceLog = window.__ocVoiceLog || []);
  if (!synth) return Promise.resolve({ hint: 'This browser cannot read answers aloud.' });
  synth.cancel();
  const t = ocCleanSpeech(text);
  if (!t) return Promise.resolve({});
  const parts = t.match(/[^.!?।]+[.!?।]?/g) || [t];
  const chunks = [];
  parts.forEach((p) => { let x = p.trim(); while (x.length > 220) { const cut = x.lastIndexOf(' ', 220) > 80 ? x.lastIndexOf(' ', 220) : 220;
    chunks.push(x.slice(0, cut)); x = x.slice(cut).trim(); } if (x) chunks.push(x); });
  return new Promise((resolve) => {
    const go = () => {
      const used = [];
      let hint = '';
      chunks.forEach((c, i) => {
        const lang = ocScriptLang(c, o.lang);
        const v = ocPickVoice(lang, o.gender);
        const u = new SpeechSynthesisUtterance(c);
        u.lang = lang; if (v) u.voice = v;
        u.rate = v && /Natural|Neural|Google/i.test(v.name) ? 1.0 : 0.95; u.pitch = 1.0;
        u.onstart = () => { if (i === 0 && o.onstart) o.onstart(); if (o.onchunk) o.onchunk(i, c); };
        u.onerror = (e) => { if (o.onerror) o.onerror(e, i); else if (i === chunks.length - 1 && o.onend) o.onend(); };
        if (i === chunks.length - 1 && o.onend) u.onend = o.onend;
        synth.speak(u);
        const name = v ? v.name : 'default';
        if (!used.includes(name)) used.push(name);
        if (!v || !(v.lang || '').toLowerCase().replace('_', '-').startsWith(lang.toLowerCase())) {
          hint = lang.startsWith('en') ? 'For a natural Indian English voice, open the portal in Microsoft Edge (with internet).'
            : `No ${lang} voice on this browser: open the portal in Microsoft Edge (with internet) for natural Indian voices.`;
        }
      });
      log.push(`speak:${chunks.length}:${used.join(' + ')}`);
      resolve({ hint, voices: used, chunks });
    };
    if (synth.getVoices().length) go();
    else { let done = false; const once = () => { if (!done) { done = true; go(); } };
           synth.addEventListener('voiceschanged', once, { once: true }); setTimeout(once, 900); }
  });
}
"""

_HTML = """<div class="vb"></div>"""

_CSS = r"""
.vb { font-family: inherit; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 12px 16px;
      background: #fff; border: 1px solid #DCE8E6; border-radius: 18px; box-shadow: 0 3px 12px rgba(18,58,64,.06); }
.vb-mic { width: 52px; height: 52px; border-radius: 50%; border: none; cursor: pointer; position: relative; flex: none;
          background: linear-gradient(135deg,#0F7C80,#19A6A2); color: #fff; display: grid; place-items: center;
          box-shadow: 0 6px 16px rgba(15,124,128,.35); transition: transform .15s; }
.vb-mic:hover { transform: scale(1.05); }
.vb-mic svg { width: 24px; height: 24px; }
.vb-mic:disabled { background: #9DB3B5; cursor: not-allowed; box-shadow: none; }
.vb.listening .vb-mic { background: linear-gradient(135deg,#E2664F,#F08A6E); }
.vb.listening .vb-mic::after { content: ""; position: absolute; inset: -6px; border-radius: 50%; border: 3px solid #E2664F;
                               animation: vbpulse 1.1s ease-out infinite; }
@keyframes vbpulse { from { transform: scale(.9); opacity: .9 } to { transform: scale(1.35); opacity: 0 } }
.vb-wave { display: flex; align-items: center; gap: 3px; height: 30px; flex: none; }
.vb-wave i { display: block; width: 4px; height: 6px; border-radius: 3px; background: #C9DCDA; }
.vb.listening .vb-wave i, .vb.speaking .vb-wave i { animation: vbwave .9s ease-in-out infinite; }
.vb.listening .vb-wave i { background: #E2664F; } .vb.speaking .vb-wave i { background: #0F7C80; }
.vb-wave i:nth-child(2) { animation-delay: .1s } .vb-wave i:nth-child(3) { animation-delay: .2s }
.vb-wave i:nth-child(4) { animation-delay: .3s } .vb-wave i:nth-child(5) { animation-delay: .4s }
.vb-wave i:nth-child(6) { animation-delay: .5s } .vb-wave i:nth-child(7) { animation-delay: .6s }
@keyframes vbwave { 0%,100% { height: 6px } 50% { height: 28px } }
.vb-col { display: flex; flex-direction: column; gap: 2px; min-width: 180px; flex: 1; }
.vb-status { font-size: .92rem; font-weight: 700; color: #123A40; }
.vb-hint { font-size: .78rem; color: #5B7177; }
.vb button.vb-btn { font: inherit; font-size: .8rem; font-weight: 700; padding: 6px 12px; border-radius: 999px;
                    border: 1.5px solid #BFE3E1; background: #F2FAF9; color: #0F6B6E; cursor: pointer; }
.vb button.vb-btn:hover { border-color: #0F7C80; }
.vb button.vb-btn:disabled { opacity: .45; cursor: not-allowed; }
"""

_JS = SFX_FN + TTS_FN + r"""
export default function (component) {
  const { parentElement, data, setTriggerValue } = component;
  const root = parentElement.querySelector('.vb');
  if (!root) return;
  if (root.__vbCleanup) { try { root.__vbCleanup(); } catch (e) { /* already gone */ } }
  const cfg = Object.assign({ lang: 'en-IN', gender: 'female', speak: '', nonce: '', last: '', audio: '', autoSpeak: true, sound: true }, data || {});
  const log = (window.__ocVoiceLog = window.__ocVoiceLog || []);
  const MIC = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-2.08A7 7 0 0 0 19 12h-2z"/></svg>';
  root.innerHTML = `<button class="vb-mic" title="Ask by voice">${MIC}</button>
    <div class="vb-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
    <div class="vb-col"><span class="vb-status">Tap the mic and ask your question</span>
      <span class="vb-hint"></span></div>
    <button class="vb-btn vb-stop" disabled>Stop reading</button>
    <button class="vb-btn vb-replay">Read last answer</button>`;
  const $ = (s) => root.querySelector(s);
  const mic = $('.vb-mic'), status = $('.vb-status'), hint = $('.vb-hint'), stopBtn = $('.vb-stop'), replay = $('.vb-replay');
  const snd = (k) => { if (cfg.sound) ocSfx(k); };
  replay.disabled = !cfg.last;

  // ---------------- text to speech (shared helpers in TTS_FN)
  function speak(text, lang) {
    const info = ocSay(text, cfg.audio, { lang, gender: cfg.gender,
      onstart: () => { root.classList.add('speaking'); status.textContent = 'Reading the answer aloud...'; stopBtn.disabled = false; },
      onend: () => { root.classList.remove('speaking'); status.textContent = 'Tap the mic and ask your question'; stopBtn.disabled = true; },
      onerror: (e) => { if (e.error === 'not-allowed') hint.textContent = 'Tap "Read last answer" to hear it (the browser blocked autoplay).'; } });
    info.then((r) => { if (r && r.hint) hint.textContent = r.hint; });
  }
  const synth = window.speechSynthesis;
  stopBtn.onclick = () => { ocStopAll(); root.classList.remove('speaking'); stopBtn.disabled = true; status.textContent = 'Stopped.'; };
  replay.onclick = () => speak(cfg.last, cfg.lang);

  const spoken = (window.__ocSpoken = window.__ocSpoken || new Set());
  if (cfg.speak && cfg.nonce && !spoken.has(cfg.nonce)) {
    spoken.add(cfg.nonce);
    snd('confirm');
    if (cfg.autoSpeak) setTimeout(() => speak(cfg.speak, cfg.lang), 250);
  }

  // ---------------- speech to text
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let rec = null, listening = false, finalText = '';
  if (!SR) {
    mic.disabled = true;
    status.textContent = 'Voice input needs Chrome or Edge';
    hint.textContent = 'You can still type your question below.';
  }
  mic.onclick = () => {
    if (!SR) return;
    if (listening && rec) { rec.stop(); return; }
    ocStopAll();
    finalText = '';
    rec = new SR();
    rec.lang = cfg.lang; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
    rec.onstart = () => { listening = true; root.classList.remove('speaking'); root.classList.add('listening'); status.textContent = 'Listening... speak now';
                          hint.textContent = `Language: ${cfg.lang}. Tap again to stop.`; snd('tick'); log.push('listen'); };
    rec.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript; else interim += r[0].transcript;
      }
      status.textContent = (finalText + interim).trim() || 'Listening... speak now';
    };
    rec.onerror = (e) => {
      const why = { 'not-allowed': 'Microphone blocked: allow it from the icon in the address bar.',
                    'service-not-allowed': 'Microphone blocked: allow it from the icon in the address bar.',
                    'no-speech': "I didn't hear anything. Tap the mic and try again.",
                    'audio-capture': 'No microphone was found.',
                    'network': 'Voice input needs internet (the browser uses its speech service). Typing still works.' };
      hint.textContent = why[e.error] || `Voice input error: ${e.error}`;
      log.push(`error:${e.error}`);
    };
    rec.onend = () => {
      listening = false; root.classList.remove('listening');
      const t = finalText.trim();
      if (t) { status.textContent = `Heard: "${t}"`; snd('confirm'); log.push('heard'); setTriggerValue('transcript', t); }
      else if (status.textContent.startsWith('Listening')) status.textContent = 'Tap the mic and ask your question';
    };
    try { rec.start(); } catch (e) { hint.textContent = 'Could not start the microphone.'; }
  };

  const cleanup = () => { try { if (rec) rec.abort(); } catch (e) { /* ignore */ } root.__vbCleanup = null; };
  root.__vbCleanup = cleanup;
  return cleanup;
}
"""

_NAME = "oculens_voice"
_mount = None


def _component():
    global _mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _mount is None or (registry is not None and registry.get(_NAME) is None):
        _mount = _stc2.component(_NAME, html=_HTML, css=_CSS, js=_JS)
    return _mount


def voice_bar(lang: str = "en-IN", speak: str = "", nonce: str = "", last: str = "", auto_speak: bool = True,
              sound: bool = True, gender: str = "female", audio: str = "", key: str = "voicebar") -> str | None:
    """Mic button + reader. Returns the spoken question once, on the run it arrives; otherwise None."""
    res = _component()(key=key, data={"lang": lang, "gender": gender, "audio": audio, "speak": speak, "nonce": nonce, "last": last,
                                      "autoSpeak": bool(auto_speak), "sound": bool(sound)},
                       on_transcript_change=lambda: None)
    return res.get("transcript") if hasattr(res, "get") else getattr(res, "transcript", None)

# ---------------------------------------------------------------- welcome greeting after login
_W_HTML = """<div class="wa"></div>"""
_W_CSS = r"""
.wa { font-family: inherit; display: flex; gap: 18px; align-items: center; padding: 16px 20px; margin: 4px 0 6px;
      background: linear-gradient(120deg,#0B3B40 0%,#0F6B6E 55%,#17918C 100%); color: #fff; border-radius: 20px;
      box-shadow: 0 10px 28px rgba(11,59,64,.28); position: relative; overflow: hidden; }
.wa.gone { display: none; }
.wa-orb { position: relative; width: 74px; height: 74px; flex: none; }
.wa-orb .core { position: absolute; inset: 14px; border-radius: 50%;
                background: radial-gradient(circle at 35% 30%,#E9FFFC,#7FE3D8 40%,#19A6A2 75%,#0F6B6E);
                box-shadow: 0 0 22px rgba(127,227,216,.7); }
.wa-orb .ring { position: absolute; inset: 6px; border-radius: 50%; border: 2px solid rgba(201,255,248,.55); opacity: 0; }
.wa.speaking .wa-orb .ring { animation: waring 1.6s ease-out infinite; }
.wa.speaking .wa-orb .ring.r2 { animation-delay: .55s } .wa.speaking .wa-orb .ring.r3 { animation-delay: 1.1s }
.wa.speaking .wa-orb .core { animation: wabreathe 1.2s ease-in-out infinite; }
@keyframes waring { from { transform: scale(.85); opacity: .9 } to { transform: scale(1.45); opacity: 0 } }
@keyframes wabreathe { 0%,100% { transform: scale(1) } 50% { transform: scale(1.08) } }
.wa-body { flex: 1; min-width: 0; }
.wa-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.wa-name { font-weight: 800; font-size: 1rem; letter-spacing: .2px; }
.wa-tag { font-size: .72rem; font-weight: 700; padding: 3px 9px; border-radius: 999px; background: rgba(255,255,255,.16); }
.wa-bars { display: inline-flex; gap: 3px; align-items: center; height: 18px; }
.wa-bars i { width: 3px; height: 4px; border-radius: 2px; background: #BFF5EE; display: block; }
.wa.speaking .wa-bars i { animation: wabar .8s ease-in-out infinite; }
.wa-bars i:nth-child(2) { animation-delay: .12s } .wa-bars i:nth-child(3) { animation-delay: .24s }
.wa-bars i:nth-child(4) { animation-delay: .36s } .wa-bars i:nth-child(5) { animation-delay: .48s }
@keyframes wabar { 0%,100% { height: 4px } 50% { height: 18px } }
.wa-text { margin-top: 6px; font-size: .98rem; line-height: 1.5; color: rgba(255,255,255,.8); }
.wa-text span { transition: color .25s, background .25s; border-radius: 4px; }
.wa-text span.now { color: #fff; background: rgba(255,255,255,.14); }
.wa-hint { font-size: .76rem; color: #BFF5EE; margin-top: 4px; min-height: 1em; }
.wa-btns { display: flex; flex-direction: column; gap: 6px; flex: none; }
.wa button { font: inherit; font-size: .8rem; font-weight: 700; padding: 6px 14px; border-radius: 999px; cursor: pointer;
             border: 1.5px solid rgba(255,255,255,.45); background: rgba(255,255,255,.1); color: #fff; }
.wa button:hover { background: rgba(255,255,255,.22); }
.wa button.primary { background: #fff; color: #0F6B6E; border-color: #fff; }
"""
_W_JS = SFX_FN + TTS_FN + r"""
export default function (component) {
  const { parentElement, data, setTriggerValue } = component;
  const root = parentElement.querySelector('.wa');
  if (!root) return;
  const cfg = Object.assign({ text: '', audio: '', lang: 'en-IN', gender: 'female', nonce: '', sound: true,
                              title: 'OcuLens voice assistant', tag: '' }, data || {});
  const esc = (x) => x.replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
  const sentences = (cfg.text.match(/[^.!?।]+[.!?।]?/g) || [cfg.text]).map((x) => x.trim()).filter(Boolean);
  root.innerHTML = `<div class="wa-orb"><span class="ring"></span><span class="ring r2"></span><span class="ring r3"></span><span class="core"></span></div>
    <div class="wa-body"><div class="wa-top"><span class="wa-name">${esc(cfg.title)}</span>
      <span class="wa-bars"><i></i><i></i><i></i><i></i><i></i></span>${cfg.tag ? `<span class="wa-tag">${esc(cfg.tag)}</span>` : ''}</div>
      <div class="wa-text">${sentences.map((x, i) => `<span data-i="${i}">${esc(x)}</span>`).join(' ')}</div>
      <div class="wa-hint"></div></div>
    <div class="wa-btns"><button class="primary wa-play">Play greeting</button><button class="wa-stop">Stop</button><button class="wa-close">Close</button></div>`;
  const $ = (q) => root.querySelector(q);
  const spans = [...root.querySelectorAll('.wa-text span')];
  const hint = $('.wa-hint'), play = $('.wa-play');
  const mark = (txt) => {   // highlight the sentence being spoken
    const head = (txt || '').slice(0, 24).trim();
    const k = spans.findIndex((sp) => !sp.dataset.done && head && sp.textContent.replace(/\s+/g, ' ').includes(head));
    spans.forEach((sp) => sp.classList.remove('now'));
    if (k >= 0) { spans[k].classList.add('now'); spans[k].dataset.done = '1'; }
  };
  const done = () => { root.classList.remove('speaking'); spans.forEach((sp) => { sp.classList.remove('now'); delete sp.dataset.done; });
                       play.textContent = 'Play again'; };
  function say() {
    spans.forEach((sp) => delete sp.dataset.done);
    ocSay(cfg.text, cfg.audio, { lang: cfg.lang, gender: cfg.gender,
      ontime: (f) => {   // server audio: highlight the sentence in proportion to the time played
        const tot = sentences.reduce((n, x) => n + x.length, 0); let acc = 0, k = 0;
        for (; k < sentences.length; k++) { acc += sentences[k].length; if (acc / tot >= f) break; }
        spans.forEach((sp, i) => sp.classList.toggle('now', i === Math.min(k, spans.length - 1)));
      },
      onstart: () => { root.classList.add('speaking'); hint.textContent = ''; play.textContent = 'Speaking...'; },
      onchunk: (i, c) => mark(c), onend: done,
      onerror: (e) => { if (e.error === 'not-allowed') { done(); play.textContent = 'Play greeting';
                          hint.textContent = 'Tap "Play greeting" to hear the welcome (the browser blocked autoplay).'; }
                        else if (e.error !== 'interrupted' && e.error !== 'canceled') done(); } })
      .then((r) => { if (r && r.hint) hint.textContent = r.hint; });
  }
  play.onclick = () => say();
  $('.wa-stop').onclick = () => { ocStopAll(); done(); };
  $('.wa-close').onclick = () => { ocStopAll(); root.classList.add('gone');
                                   setTriggerValue('closed', true); };
  const spoken = (window.__ocSpoken = window.__ocSpoken || new Set());
  if (cfg.nonce && !spoken.has(cfg.nonce)) {
    spoken.add(cfg.nonce);
    if (cfg.sound) ocSfx('success');
    setTimeout(say, 700);
  } else { play.textContent = 'Play again'; }
}
"""

_W_NAME = "oculens_welcome"
_w_mount = None


def _welcome_component():
    global _w_mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _w_mount is None or (registry is not None and registry.get(_W_NAME) is None):
        _w_mount = _stc2.component(_W_NAME, html=_W_HTML, css=_W_CSS, js=_W_JS)
    return _w_mount


def welcome_agent(text: str, lang: str = "en-IN", gender: str = "female", nonce: str = "", sound: bool = True,
                  title: str = "OcuLens voice assistant", tag: str = "", audio: str = "", key: str = "welcome") -> bool:
    """Spoken welcome card. Speaks once per nonce; returns True on the run the user closes it."""
    res = _welcome_component()(key=key, data={"text": text, "audio": audio, "lang": lang, "gender": gender, "nonce": nonce,
                                              "sound": bool(sound), "title": title, "tag": tag},
                               on_closed_change=lambda: None)
    v = res.get("closed") if hasattr(res, "get") else getattr(res, "closed", None)
    return bool(v)
