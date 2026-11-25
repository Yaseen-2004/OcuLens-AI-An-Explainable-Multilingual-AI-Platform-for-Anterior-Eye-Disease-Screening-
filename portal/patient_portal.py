"""Patient side of the OcuLens portal: a personal eye-health space.

Pages: My eye health (home), Self-check, My results, Symptom diary, Appointments & reminders, AI assistant, Learn,
Emergency help and My profile. A patient sees only their own records. Every label goes through T(), which shows the
patient's language when a translation exists (translations.json) and English otherwise.

The app passes its helpers in `ctx` (models, referral directory, PDF, camera), so this module has no Streamlit
script of its own and nothing here runs on import.
"""
from __future__ import annotations

import datetime as dt
import html
import io
import uuid

import numpy as np
import streamlit as st
from PIL import Image

import db
import geo
from oculens.assistant import patient_content as pc
from oculens.assistant.i18n import tr_or_en, tr_static

# ---------------------------------------------------------------- small helpers
def _lang():
    return st.session_state.get("ai_lang", "en")


def T(text: str) -> str:
    """Interface text in the patient's language (English when no translation is available)."""
    return tr_or_en(text, _lang())


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


ICONS = {   # simple line icons (24x24), stroke = currentColor
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3.2"/>',
    "camera": '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "chart": '<path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6"/>',
    "calendar": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    "chat": '<path d="M5 5h14v10H9l-4 4z"/><path d="M9 10h6"/>',
    "book": '<path d="M4 5h6a3 3 0 0 1 3 3v11a3 3 0 0 0-3-3H4zM20 5h-6a3 3 0 0 0-3 3"/><path d="M20 5v11h-6"/>',
    "alert": '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "heart": '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10Z"/>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    "map": '<path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11Z"/><circle cx="12" cy="10" r="2.2"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
}


def icon(name, size=22, color="currentColor"):
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' stroke='{color}' stroke-width='1.8' "
            f"stroke-linecap='round' stroke-linejoin='round'>{ICONS[name]}</svg>")


PATIENT_CSS = """
<style>
.pp-hero { position:relative; overflow:hidden; border-radius:24px; padding:26px 30px; margin:4px 0 18px;
  background:radial-gradient(circle at 85% 20%, rgba(255,214,153,.35), transparent 40%),
             linear-gradient(125deg,#0A3D45 0%,#0F7C80 50%,#36B3A8 100%); color:#fff;
  box-shadow:0 14px 36px rgba(10,61,69,.28); display:flex; align-items:center; gap:24px; }
.pp-hero h1 { color:#fff !important; margin:0; font-size:1.8rem; }
.pp-hero p { color:#D6F2EF; margin:.35rem 0 0; font-size:1rem; }
.pp-hero .kick { font-size:.78rem; letter-spacing:.18em; font-weight:700; color:#FFD699; text-transform:uppercase; }
.pp-iris { width:118px; height:118px; flex:none; margin-left:auto; position:relative; }
.pp-iris .r { position:absolute; inset:0; border-radius:50%; border:2px dashed rgba(255,255,255,.35); animation:ppspin 18s linear infinite; }
.pp-iris .r2 { inset:12px; border-style:solid; border-color:rgba(255,214,153,.55); animation-duration:9s; animation-direction:reverse; }
.pp-iris .core { position:absolute; inset:26px; border-radius:50%;
  background:radial-gradient(circle at 50% 50%, #0A2A33 0 22%, #3B5BA5 23% 40%, #5FC9C0 41% 62%, #E8FFFB 63% 66%, transparent 67%);
  box-shadow:0 0 30px rgba(95,201,192,.6); animation:ppbreathe 4s ease-in-out infinite; }
.pp-iris .glint { position:absolute; width:12px; height:12px; border-radius:50%; background:#fff; top:40px; left:44px; opacity:.85; }
@keyframes ppspin { to { transform:rotate(360deg) } }
@keyframes ppbreathe { 0%,100% { transform:scale(1) } 50% { transform:scale(1.06) } }
.pp-card { background:#fff; border:1px solid #E2EEEC; border-radius:20px; padding:16px 18px;
  box-shadow:0 6px 20px rgba(10,61,69,.06); height:100%; }
.pp-stat { display:flex; gap:12px; align-items:flex-start; }
.pp-stat .ic { width:42px; height:42px; border-radius:14px; display:grid; place-items:center; flex:none; color:#fff; }
.pp-stat .t { font-size:.74rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:#5B7177; }
.pp-stat .v { font-family:'Sora','Inter',sans-serif; font-weight:700; font-size:1.05rem; color:#0A2A33; line-height:1.3; margin-top:2px; }
.pp-stat .s { font-size:.82rem; color:#5B7177; margin-top:2px; }
.pp-light { display:inline-flex; align-items:center; gap:8px; font-weight:700; }
.pp-light i { width:12px; height:12px; border-radius:50%; display:inline-block; box-shadow:0 0 0 4px rgba(0,0,0,.05); }
.pp-result { border-radius:22px; padding:20px 22px; color:#0A2A33; position:relative; overflow:hidden; }
.pp-result.refer { background:linear-gradient(135deg,#FFF1EC,#FFE2D8); border:1.5px solid #F4B6A3; }
.pp-result.routine { background:linear-gradient(135deg,#ECFAF3,#DDF5E9); border:1.5px solid #A8DCC0; }
.pp-result h3 { margin:0 0 6px; font-size:1.3rem; }
.pp-result .big { display:flex; align-items:center; gap:16px; }
.pp-result .dot { width:58px; height:58px; border-radius:50%; flex:none; position:relative; }
.pp-result.refer .dot { background:#E2664F; } .pp-result.routine .dot { background:#2E9E5B; }
.pp-result .dot:after { content:""; position:absolute; inset:-8px; border-radius:50%; border:3px solid currentColor; opacity:.25;
  animation:pppulse 1.8s ease-out infinite; }
.pp-result.refer .dot { color:#E2664F; } .pp-result.routine .dot { color:#2E9E5B; }
@keyframes pppulse { from { transform:scale(.9); opacity:.5 } to { transform:scale(1.35); opacity:0 } }
.pp-tl { position:relative; padding-left:26px; }
.pp-tl:before { content:""; position:absolute; left:9px; top:6px; bottom:6px; width:2px; background:linear-gradient(#0F7C80,#BFE3E1); }
.pp-tl .it { position:relative; margin:0 0 14px; }
.pp-tl .it:before { content:""; position:absolute; left:-22px; top:5px; width:12px; height:12px; border-radius:50%;
  background:#fff; border:3px solid var(--c,#0F7C80); }
.pp-tl .d { font-size:.75rem; color:#5B7177; font-weight:600; }
.pp-tl .x { font-size:.92rem; color:#0A2A33; }
.pp-tip { border-radius:20px; padding:18px 20px; background:linear-gradient(135deg,#FFF8EC,#FFEFD6); border:1px solid #F5DDB0; }
.pp-tip .k { font-size:.74rem; letter-spacing:.14em; font-weight:800; color:#B57413; }
.pp-tip p { margin:.4rem 0 0; font-size:1rem; color:#5A3D0C; }
.pp-learn { border-radius:18px; padding:16px; background:#fff; border:1px solid #E2EEEC; height:100%;
  box-shadow:0 4px 14px rgba(10,61,69,.05); transition:transform .15s; }
.pp-learn:hover { transform:translateY(-3px); }
.pp-learn .ic { width:40px; height:40px; border-radius:12px; display:grid; place-items:center; color:#fff;
  background:linear-gradient(135deg,#0F7C80,#36B3A8); margin-bottom:8px; }
.pp-learn b { font-family:'Sora','Inter',sans-serif; color:#0A2A33; }
.pp-learn p { font-size:.88rem; color:#41575C; margin:.35rem 0 0; }
.pp-flip { perspective:900px; height:170px; outline:none; cursor:pointer; }
.pp-flip .in { position:relative; width:100%; height:100%; transition:transform .6s; transform-style:preserve-3d; }
.pp-flip:hover .in, .pp-flip:focus .in { transform:rotateY(180deg); }
.pp-flip .f, .pp-flip .b { position:absolute; inset:0; border-radius:18px; padding:16px; backface-visibility:hidden;
  display:flex; flex-direction:column; justify-content:center; }
.pp-flip .f { background:linear-gradient(135deg,#3B5BA5,#5A79C4); color:#fff; }
.pp-flip .b { background:linear-gradient(135deg,#0F7C80,#36B3A8); color:#fff; transform:rotateY(180deg); }
.pp-flip .tag { font-size:.7rem; font-weight:800; letter-spacing:.16em; opacity:.85; }
.pp-flip .q { font-weight:700; margin-top:6px; font-size:.98rem; }
.pp-sos { border-radius:24px; padding:22px 24px; color:#fff; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#B42318,#E2664F); box-shadow:0 14px 34px rgba(180,35,24,.3); }
.pp-sos h2 { color:#fff !important; margin:0 0 8px; }
.pp-sos li { margin:4px 0; }
.pp-sos:after { content:""; position:absolute; right:-30px; top:-30px; width:160px; height:160px; border-radius:50%;
  border:3px solid rgba(255,255,255,.25); animation:pppulse 2.2s ease-out infinite; }
.pp-call { display:inline-flex; align-items:center; gap:10px; padding:12px 20px; border-radius:16px; background:#fff;
  color:#B42318 !important; font-weight:800; text-decoration:none; margin:6px 10px 0 0; font-size:1.05rem; }
.pp-steps { display:flex; gap:8px; flex-wrap:wrap; margin:4px 0 14px; }
.pp-steps span { padding:7px 14px; border-radius:999px; font-weight:700; font-size:.82rem; background:#EAF6F5; color:#0F7C80; }
.pp-steps span.on { background:#0F7C80; color:#fff; }
.pp-chip { display:inline-block; padding:3px 11px; border-radius:999px; font-size:.75rem; font-weight:700; }
.pp-chip.wait { background:#FBEFD8; color:#B57413; } .pp-chip.done { background:#E4F4E9; color:#2E7D43; }
.pp-chip.red { background:#FCE7E1; color:#C0392B; } .pp-chip.mut { background:#EAF1F1; color:#5B7177; }
.st-key-pp_actions button { height:92px; border-radius:20px !important; font-size:1rem !important; font-weight:700 !important;
  background:linear-gradient(135deg,#FFFFFF,#F1FAF9) !important; color:#0A3D45 !important;
  border:1.5px solid #CDE8E5 !important; box-shadow:0 6px 18px rgba(10,61,69,.07); }
.st-key-pp_actions button:hover { border-color:#0F7C80 !important; transform:translateY(-2px); }
.st-key-pp_sos_btn button { background:linear-gradient(135deg,#B42318,#E2664F) !important; color:#fff !important; border:0 !important; }
</style>
"""


def hero(kicker, title, subtitle):
    st.markdown(f"<div class='pp-hero'><div><div class='kick'>{esc(kicker)}</div><h1>{esc(title)}</h1>"
                f"<p>{esc(subtitle)}</p></div><div class='pp-iris'><span class='r'></span><span class='r r2'></span>"
                f"<span class='core'></span><span class='glint'></span></div></div>", unsafe_allow_html=True)


def stat(col, ic, color, title, value, sub=""):
    col.markdown(f"<div class='pp-card pp-stat'><div class='ic' style='background:{color}'>{icon(ic, 22, '#fff')}</div>"
                 f"<div><div class='t'>{esc(title)}</div><div class='v'>{value}</div>"
                 f"<div class='s'>{sub}</div></div></div>", unsafe_allow_html=True)


def chip(text, kind):
    return f"<span class='pp-chip {kind}'>{esc(text)}</span>"


def light(refer):
    c, t = ("#E2664F", T("See an eye specialist soon")) if refer else ("#2E9E5B", T("No urgent signs found"))
    return f"<span class='pp-light'><i style='background:{c}'></i>{esc(t)}</span>"


def go(page_key):
    st.session_state["nav"] = page_label(page_key)


def _greeting():
    h = dt.datetime.now().hour
    return T("Good morning") if h < 12 else (T("Good afternoon") if h < 17 else T("Good evening"))


def _me():
    u = st.session_state["user"]
    pid = u.get("patient_id")
    return u, pid, (db.get_patient(pid) if pid else None)


def _thumb(path, size=220):
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((size, size))
        return im
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- pages
def page_home(ctx):
    u, pid, p = _me()
    first = (u.get("name") or "").split(" ")[0]
    hero(T("Your eye-health space"), f"{_greeting()}, {first}",
         T("Check your eyes, follow your results and get help, in your own language."))
    cases = db.cases_for_patient(pid) if pid else []
    latest = cases[0] if cases else None
    recs = db.recommendations_for_patient(pid) if pid else []
    appts = db.appointments_for_patient(pid) if pid else []
    rem = db.reminders_for(pid, include_done=False) if pid else []
    c = st.columns(4)
    if latest:
        stat(c[0], "eye", "#0F7C80", T("Latest check"), light(latest["referred"]),
             f"{esc(latest['created_at'][:10])} · {esc(ctx.TASK_PLAIN.get(latest['task'], latest['task']))}")
        rv = (chip(T("Doctor reviewed"), "done") if latest["status"] == "reviewed" else chip(T("Awaiting review"), "wait"))
        stat(c[1], "user", "#3B5BA5", T("Doctor review"), rv, esc(recs[0]["doctor"]) if recs else "")
    else:
        stat(c[0], "eye", "#0F7C80", T("Latest check"), esc(T("No checks yet")), esc(T("Start your first self-check")))
        stat(c[1], "user", "#3B5BA5", T("Doctor review"), "-", "")
    if appts:
        a = appts[0]
        stat(c[2], "calendar", "#E8A33D", T("Appointment"), esc(a["hospital"]),
             chip(T(a["status"].capitalize()), "wait") + (f" {esc(a.get('preferred_date') or '')}"))
    else:
        stat(c[2], "calendar", "#E8A33D", T("Appointment"), esc(T("None booked")), "")
    stat(c[3], "bell", "#6C5B9E", T("Reminders"), str(len(rem)),
         esc(rem[0]["title"]) + " · " + esc(rem[0]["due"]) if rem else esc(T("Nothing due")))
    if latest and latest["referred"] and pid:
        open_appts = [a for a in appts if a["status"] in ("requested", "confirmed", "completed")]
        days = (dt.datetime.now() - dt.datetime.strptime(latest["created_at"], "%Y-%m-%d %H:%M")).days
        if not open_appts and days >= 1:
            st.markdown(f"<div class='pp-result refer' style='margin-top:14px'><b>{esc(T('You were advised to see an eye specialist'))}"
                        f" {days} {esc(T('day(s) ago'))}.</b> {esc(T('Booking takes a minute, and early treatment protects your sight.'))}"
                        "</div>", unsafe_allow_html=True)
            st.button(T("Book now"), key="pp_nudge_book", on_click=go, args=("appointments",), type="primary")
    nxt = _next_dose(db.medications_for(pid)) if pid else None
    if nxt:
        st.markdown(f"<div class='pp-tip' style='margin-top:12px'><div class='k'>{esc(T('NEXT DOSE'))}</div><p>"
                    f"{esc(nxt[1]['name'])} · {esc(T(nxt[1]['eye']))} · {nxt[0].strftime('%I:%M %p')}</p></div>",
                    unsafe_allow_html=True)
    st.write("")
    with st.container(key="pp_actions"):
        a = st.columns(4)
        a[0].button(T("Start a self-check"), use_container_width=True, on_click=go, args=("selfcheck",))
        a[1].button(T("Log today's symptoms"), use_container_width=True, on_click=go, args=("diary",))
        a[2].button(T("Ask the assistant"), use_container_width=True, on_click=go, args=("assistant",))
        a[3].button(T("Emergency help"), use_container_width=True, on_click=go, args=("emergency",))
    st.write("")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.markdown(f"### {T('Your eye journey')}")
        events = []
        for cs in cases:
            events.append((cs["created_at"], "#E2664F" if cs["referred"] else "#2E9E5B",
                           f"{T('Eye check')}: {ctx.TASK_PLAIN.get(cs['task'], cs['task'])}"
                           + (f" · {ctx.EYE_NAME[cs['eye']]}" if cs.get("eye") else "") + " · "
                           + (T("See an eye specialist soon") if cs["referred"] else T("No urgent signs found"))))
        for r in recs:
            events.append((r["created_at"], "#3B5BA5", f"{T('Doctor reviewed your check')} · {r['doctor']}"))
        for a_ in appts:
            events.append((a_["created_at"], "#E8A33D", f"{T('Appointment requested')} · {a_['hospital']}"))
        for s_ in (db.symptoms_for(pid) if pid else [])[-5:]:
            events.append((s_["logged_at"], "#6C5B9E", f"{T('Symptoms logged')} · {T('Pain')} {s_['pain']}/10"))
        events.sort(key=lambda e: e[0], reverse=True)
        if events:
            st.markdown("<div class='pp-tl'>" + "".join(
                f"<div class='it' style='--c:{c_}'><div class='d'>{esc(d)}</div><div class='x'>{esc(x)}</div></div>"
                for d, c_, x in events[:8]) + "</div>", unsafe_allow_html=True)
        else:
            st.info(T("Your journey starts with your first self-check."))
    with right:
        tip = pc.TIPS[dt.date.today().toordinal() % len(pc.TIPS)]
        st.markdown(f"<div class='pp-tip'><div class='k'>{esc(T('TIP OF THE DAY'))}</div><p>{esc(T(tip))}</p></div>",
                    unsafe_allow_html=True)
        st.write("")
        sy = db.symptoms_for(pid) if pid else []
        if len(sy) >= 2:
            st.markdown(f"**{T('How your eyes felt recently')}**")
            st.plotly_chart(_trend_fig(sy[-10:], compact=True), use_container_width=True, config={"displayModeBar": False},
                            key="home_trend")
        st.caption(T("OcuLens is a screening aid, not a diagnosis. Your eye doctor decides your treatment."))


def _trend_fig(rows, compact=False):
    import plotly.graph_objects as go_
    fig = go_.Figure()
    colors = ["#E2664F", "#0F7C80", "#E8A33D", "#3B5BA5", "#6C5B9E", "#2E9E5B"]
    keys = pc.SYMPTOMS[:2] if compact else pc.SYMPTOMS
    for (k, lab, _), col in zip(keys, colors):
        fig.add_trace(go_.Scatter(x=[r["logged_at"] for r in rows], y=[r[k] for r in rows], name=T(lab),
                                  mode="lines+markers", line=dict(color=col, width=3, shape="spline"), marker=dict(size=7)))
    fig.update_layout(height=200 if compact else 330, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 10.5]),
                      legend=dict(orientation="h", y=-0.25), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F7FBFB")
    return fig


def page_selfcheck(ctx):
    u, pid, p = _me()
    hero(T("Self-check"), T("Check your eyes at home"),
         T("Take a clear photo of your eye. The AI looks for warning signs and a doctor reviews every check."))
    step = 1 if not st.session_state.get("pp_shots") else 2
    st.markdown("<div class='pp-steps'>" + "".join(
        f"<span class='{'on' if i <= step else ''}'>{i}. {esc(T(t))}</span>"
        for i, t in enumerate(["Choose a check", "Take the photo", "See your result"], 1)) + "</div>", unsafe_allow_html=True)
    checks = {T("Cornea check (red, painful or watery eye)"): "keratitis",
              T("Eyelid check for trachoma"): "trachoma_tf"}
    left, right = st.columns([1, 1.1], gap="large")
    with left:
        task = checks[st.radio(T("What would you like to check?"), list(checks), key="pp_task")]
        st.caption(T("The cornea check is made for eyes that are already red, painful or watery; it cannot confirm "
                     "that an eye is healthy. Ulcer staining photos are taken only in clinics."))
        mode = st.radio(T("Photo"), [T("Use the camera"), T("Upload a photo")], horizontal=True, key="pp_mode")
        shots = []
        if mode == T("Use the camera"):
            shots = ctx.camera_capture(task)
        else:
            up = st.file_uploader(T("Eye photo"), type=ctx.IMG_TYPES, key="pp_up")
            eye = {T("Right eye"): "R", T("Left eye"): "L", T("Not sure"): ""}[
                st.radio(T("Which eye?"), [T("Right eye"), T("Left eye"), T("Not sure")], horizontal=True, key="pp_eye")]
            img = ctx.open_rgb(up) if up is not None else None
            shots = [(eye, img)] if img is not None else []
        run = st.button(T("Check my eyes"), type="primary", disabled=not shots, use_container_width=True)
    with right:
        if shots:
            cols = st.columns(len(shots))
            for col, (eye, im) in zip(cols, shots):
                col.image(im, caption=ctx.EYE_NAME[eye] if eye else T("Your photo"), use_container_width=True)
        else:
            st.markdown(f"<div class='pp-card'><b>{esc(T('Tips for a good photo'))}</b><ul>"
                        f"<li>{esc(T('Sit near a window or a lamp, with light from the side.'))}</li>"
                        f"<li>{esc(T('Open the eye wide and look straight at the camera.'))}</li>"
                        f"<li>{esc(T('Hold steady until the focus bar turns green.'))}</li></ul></div>",
                        unsafe_allow_html=True)
    if not run or not shots:
        return
    for i, (eye, img) in enumerate(shots):
        st.divider()
        if len(shots) > 1:
            st.markdown(f"### {ctx.EYE_NAME[eye]}")
        _check_one(ctx, u, pid, img, task, eye, i)


def _check_one(ctx, u, pid, img, task, eye, idx):
    import time as _t
    holder = st.empty()
    for msg in ("CHECKING THE PHOTO", "FINDING THE CORNEA", "LOOKING FOR WARNING SIGNS"):
        holder.markdown(f"<div style='max-width:460px;margin:auto'>{ctx.scanning_html(img, msg)}</div>",
                        unsafe_allow_html=True)
        ctx.play_sound("scan")
        _t.sleep(0.8)
    res = ctx.analyse_image(img, task)
    holder.empty()
    if not res["eye_ok"]:
        st.error(T("This does not look like a close-up photo of an eye. Please take the photo again, with one eye "
                   "filling most of the picture."))
        ctx.play_sound("alert")
        return
    refer = bool(res["refer"])
    kind = "refer" if refer else "routine"
    head, body = pc.RESULT_PLAIN[kind]
    label = ctx.label_of(task, res["top"])
    detail = (f"{T('Closest pattern the model found')}: <b>{esc(label)}</b> ({res['topp'] * 100:.0f}%)"
              if not (task == "trachoma_tf" and res["top"] == "0") else "")
    st.markdown(f"<div class='pp-result {kind}'><div class='big'><div class='dot'></div><div><h3>{esc(T(head))}</h3>"
                f"<div>{esc(T(body))}</div><div style='margin-top:8px;font-size:.9rem'>{detail}</div></div></div></div>",
                unsafe_allow_html=True)
    if not res["q"].ok:
        st.warning(T("The photo was not very clear, so the doctor may ask you for a new one."))
    fn = f"self_{uuid.uuid4().hex[:10]}.png"
    Image.fromarray(img).save(db.STORAGE / fn)
    cid = db.add_case(pid, task, fn, res["top"], res["topp"], ", ".join(res["pset"]), refer, res["q"].ok,
                      u["name"], mi=res["mi"], eye=eye, source="self")
    if refer and pid:
        due = (dt.date.today() + dt.timedelta(days=2)).isoformat()
        db.add_reminder(pid, T("Visit an eye specialist"), due, "referral")
    ctx.play_sound("confirm")
    st.success(f"{T('Saved to My results')} (#{cid}). {T(pc.RESULT_PLAIN['pending'][1])}")
    _hospital_cards(ctx, task, cid, pid, u, key=f"sc{cid}_{idx}")


def _hospital_cards(ctx, task, cid, pid, u, key):
    import urllib.parse
    loc = _my_coords(u)
    if loc:
        near = geo.nearest(loc[0], loc[1], task, only_fit=True)[:3]
        st.markdown(f"#### {T('Nearest suitable eye hospitals')} · {esc(loc[2])}")
        cols = st.columns(len(near))
        for i, (col, h) in enumerate(zip(cols, near)):
            col.markdown(f"<div class='pp-card'><div style='display:flex;gap:8px;align-items:center;color:#0F7C80'>"
                         f"{icon('map', 20)}<b>{esc(h['hospital'])}</b></div><div style='font-size:.85rem;color:#5B7177;"
                         f"margin-top:4px'>{esc(h['branch'])} · {h['km']:.1f} km · {T('about')} {h['minutes']} {T('min')}</div>"
                         f"<a href='{geo.directions_url(h, loc[:2])}' target='_blank' style='font-size:.85rem;"
                         f"font-weight:700;color:#0F7C80'>{esc(T('Directions'))}</a></div>", unsafe_allow_html=True)
            if col.button(T("Book here"), key=f"{key}_nb{i}", use_container_width=True):
                st.session_state["pp_book_h"] = h["id"]
                go("appointments")
                st.rerun()
        return
    st.markdown(f"#### {T('Where to go in Bengaluru')}")
    st.caption(T("Tip: set your home area in Appointments to see the nearest hospitals first."))
    hs = ctx.BLR_REFERRALS.get(task, ctx.CORNEA_PANEL)
    cols = st.columns(len(hs))
    for i, (col, d) in enumerate(zip(cols, hs)):
        q = urllib.parse.quote_plus(f"{d['hospital']} {d['area']} Bengaluru")
        col.markdown(f"<div class='pp-card'><div style='display:flex;gap:8px;align-items:center;color:#0F7C80'>"
                     f"{icon('map', 20)}<b>{esc(d['hospital'])}</b></div><div style='font-size:.85rem;color:#5B7177;"
                     f"margin-top:4px'>{esc(d['area'])}, Bengaluru</div><div style='font-size:.82rem;margin-top:6px'>"
                     f"{esc(d['focus'])}</div><a href='https://www.google.com/maps/search/?api=1&query={q}' "
                     f"target='_blank' style='font-size:.85rem;font-weight:700;color:#0F7C80'>{esc(T('Open in Maps'))}</a>"
                     f"</div>", unsafe_allow_html=True)
        if col.button(T("Request appointment"), key=f"{key}_ap{i}", use_container_width=True):
            db.add_appointment(cid, d["hospital"], "", u["name"], patient_id=pid)
            st.success(f"{T('Appointment requested')}: {d['hospital']}")
    st.caption(T("The hospitals are real Bengaluru eye-care centres. Please call the hospital to confirm the time."))


def page_results(ctx):
    u, pid, p = _me()
    hero(T("My results"), T("Your eye checks"), T("Every check you or your doctor made, with the doctor's advice."))
    cases = db.cases_for_patient(pid) if pid else []
    if not cases:
        st.info(T("No results yet. Start your first self-check."))
        st.button(T("Start a self-check"), on_click=go, args=("selfcheck",))
        return
    sel = st.session_state.get("pp_view")
    if sel:
        return _result_detail(ctx, u, pid, sel)
    for cs in cases:
        with st.container(border=True):
            c = st.columns([0.9, 2.4, 1.6, 1])
            th = _thumb(db.STORAGE / cs["image_path"], 160)
            if th is not None:
                c[0].image(th, use_container_width=True)
            c[1].markdown(f"**{ctx.TASK_PLAIN.get(cs['task'], cs['task'])}**"
                          + (f" · {ctx.EYE_NAME[cs['eye']]}" if cs.get("eye") else "")
                          + f"  \n{cs['created_at']} · " + (T("Self-check") if cs.get("source") == "self" else T("Clinic")))
            c[2].markdown(light(cs["referred"]) + "<br>" + (chip(T("Doctor reviewed"), "done") if cs["status"] == "reviewed"
                                                             else chip(T("Awaiting review"), "wait")), unsafe_allow_html=True)
            if c[3].button(T("Open"), key=f"pp_open_{cs['id']}", use_container_width=True):
                st.session_state["pp_view"] = cs["id"]
                st.rerun()


def _result_detail(ctx, u, pid, cid):
    cs = db.get_case(cid)
    if st.button(T("Back to my results")):
        st.session_state["pp_view"] = None
        st.rerun()
    if not cs or cs.get("patient_id") != pid:       # a patient sees only their own records
        st.error(T("This result is not available."))
        return
    left, right = st.columns([1, 1.25], gap="large")
    ip = db.STORAGE / cs["image_path"]
    img = np.array(Image.open(ip).convert("RGB")) if ip.exists() else None
    with left:
        if img is not None:
            st.image(img, use_container_width=True, caption=cs["created_at"])
    with right:
        kind = "refer" if cs["referred"] else "routine"
        head, body = pc.RESULT_PLAIN[kind]
        st.markdown(f"<div class='pp-result {kind}'><div class='big'><div class='dot'></div><div><h3>{esc(T(head))}</h3>"
                    f"<div>{esc(T(body))}</div></div></div></div>", unsafe_allow_html=True)
        st.write("")
        recs = db.recommendations_for(cid)
        st.markdown(f"#### {T('Your doctor’s advice')}")
        if recs:
            for r in recs:
                st.markdown(f"<div class='pp-card'><b>{esc(r['doctor'])}</b> · {esc(r['created_at'])}<br>"
                            f"{esc(r['diagnosis'] or '')}<br>{esc(r['recommendation'] or '')}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='pp-card'>{chip(T('Awaiting review'), 'wait')} "
                        f"{esc(T('A doctor will review your photo and add advice here.'))}</div>", unsafe_allow_html=True)
        st.write("")
        b = st.columns(2)
        try:
            b[0].download_button(T("Download report (PDF)"), data=ctx.case_pdf_bytes(cs, img, None, recs),
                                 file_name=f"OcuLens_result_{cid}.pdf", mime="application/pdf", use_container_width=True)
        except Exception:  # noqa: BLE001
            pass
        if b[1].button(T("Ask the assistant about this"), use_container_width=True):
            st.session_state["assistant_case"] = cid
            go("assistant")
            st.rerun()
    _hospital_cards(ctx, cs["task"], cid, pid, u, key=f"rd{cid}")


def page_diary(ctx):
    u, pid, p = _me()
    hero(T("Symptom diary"), T("How do your eyes feel today?"),
         T("A quick daily note helps your doctor see whether your eyes are getting better."))
    left, right = st.columns([1, 1.3], gap="large")
    with left:
        with st.form("pp_diary", border=True):
            eye = st.radio(T("Which eye?"), [T("Right eye"), T("Left eye"), T("Both eyes")], horizontal=True)
            scores = {k: st.slider(T(lab), 0, 10, 0, help=T(hlp)) for k, lab, hlp in pc.SYMPTOMS}
            note = st.text_input(T("Anything else? (optional)"))
            saved = st.form_submit_button(T("Save today's entry"), type="primary", use_container_width=True)
        if saved and pid:
            prev = db.symptoms_for(pid)
            db.add_symptom(pid, eye, scores, note)
            if scores["pain"] >= 8 or scores["blur"] >= 8:
                st.markdown(f"<div class='pp-result refer'><b>{esc(T(pc.DIARY_ALERT))}</b></div>", unsafe_allow_html=True)
                ctx.play_sound("alert")
                st.button(T("Emergency help"), key="pp_diary_sos", on_click=go, args=("emergency",))
            else:
                ctx.play_sound("confirm")
                if prev:
                    last = sum(prev[-1][k] for k, _, _ in pc.SYMPTOMS)
                    now_ = sum(scores.values())
                    msg = pc.DIARY_WORSE if now_ > last + 2 else (pc.DIARY_BETTER if now_ < last - 2 else "")
                    st.success(T("Saved.") + (" " + T(msg) if msg else ""))
                else:
                    st.success(T("Saved."))
    with right:
        rows = db.symptoms_for(pid) if pid else []
        if rows:
            st.markdown(f"**{T('Your symptoms over time')}**")
            st.plotly_chart(_trend_fig(rows[-30:]), use_container_width=True, config={"displayModeBar": False},
                            key="diary_trend")
            last = rows[-1]
            st.caption(f"{T('Last entry')}: {last['logged_at']} · {last['eye']}"
                       + (f" · {last['note']}" if last.get("note") else ""))
        else:
            st.info(T("Your chart appears here after your first entry."))


SLOTS = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]


def _my_coords(u):
    """The patient's position for sorting hospitals: shared GPS (this session), else their saved home area."""
    loc = st.session_state.get("pp_loc")
    if loc:
        return loc
    home = (db.get_user(u["id"]) or {}).get("home_area")
    if home in geo.AREAS:
        return (*geo.AREAS[home], home)
    return None


def _where_am_i(u):
    """Location picker: current location (browser), an area, or a pincode. Returns (lat, lon, label) or None."""
    ss = st.session_state
    modes = [T("My current location"), T("My area"), T("Pincode")]
    home = (db.get_user(u["id"]) or {}).get("home_area") or ""
    mode = st.radio(T("Find eye hospitals near"), modes, horizontal=True, key="pp_loc_mode",
                    index=1 if home and not ss.get("pp_loc") else 0)
    if mode == modes[0]:
        got = geo.locate_button(T("Use my current location"), T("Finding you..."), key="pp_geo")
        if got:
            ss["pp_loc"] = (float(got["lat"]), float(got["lon"]), T("Your current location"))
        loc = ss.get("pp_loc")
        if loc:
            near = geo.nearest_area(loc[0], loc[1])
            st.caption(f"{T('Located near')} {near}" + ("" if geo.in_bengaluru(loc[0], loc[1]) else
                       " · " + T("You seem to be outside Bengaluru; distances are to Bengaluru hospitals.")))
        return loc
    if mode == modes[1]:
        areas = list(geo.AREAS)
        area = st.selectbox(T("Your area"), areas, index=areas.index(home) if home in areas else 0, key="pp_area")
        if area != home and st.checkbox(T("Save as my home area"), key="pp_save_area"):
            db.update_profile(u["id"], home_area=area)
            st.toast(T("Saved."))
        return (*geo.AREAS[area], area)
    pin = st.text_input(T("Your 6-digit pincode"), max_chars=6, key="pp_pin")
    if pin:
        area = geo.area_of_pincode(pin)
        if not area:
            st.warning(T("We don't know this pincode yet. Please choose your area instead."))
            return None
        st.caption(f"{pin} · {area}")
        return (*geo.AREAS[area], area)
    return None


def _map(loc, hs):
    import plotly.graph_objects as go_
    fig = go_.Figure()
    fig.add_trace(go_.Scattermap(lat=[h["lat"] for h in hs], lon=[h["lon"] for h in hs], mode="markers+text",
                                 marker=dict(size=16, color=["#0F7C80" if h["fit"] else "#8A9BB8" for h in hs]),
                                 text=[f"{i + 1}" for i in range(len(hs))], textfont=dict(color="#fff", size=11),
                                 hovertext=[f"{h['hospital']} · {h['branch']} · {h['km']:.1f} km" for h in hs],
                                 hoverinfo="text", name=T("Eye hospitals")))
    fig.add_trace(go_.Scattermap(lat=[loc[0]], lon=[loc[1]], mode="markers", name=T("You"),
                                 marker=dict(size=18, color="#E2664F"), hovertext=[loc[2]], hoverinfo="text"))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=loc[0], lon=loc[1]), zoom=10.6),
                      height=380, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    return fig


BOOK_CSS = """<style>
.pp-earliest { border-radius:22px; padding:18px 22px; color:#fff; display:flex; gap:18px; align-items:center;
  background:linear-gradient(120deg,#3B5BA5,#0F7C80 70%,#36B3A8); box-shadow:0 12px 30px rgba(59,91,165,.28); margin:6px 0 4px; }
.pp-earliest .big { font-family:'Sora','Inter',sans-serif; font-size:1.45rem; font-weight:800; line-height:1.1; }
.pp-earliest .k { font-size:.72rem; letter-spacing:.16em; font-weight:800; color:#FFD699; }
.pp-earliest .cal { width:66px; height:72px; border-radius:16px; background:#fff; color:#0A3D45; flex:none; text-align:center;
  box-shadow:0 6px 14px rgba(0,0,0,.18); overflow:hidden; }
.pp-earliest .cal b { display:block; background:#E2664F; color:#fff; font-size:.72rem; padding:3px 0; letter-spacing:.1em; }
.pp-earliest .cal span { display:block; font-family:'Sora','Inter',sans-serif; font-size:1.7rem; font-weight:800; margin-top:4px; }
.pp-busy { display:inline-flex; align-items:center; gap:6px; font-size:.8rem; font-weight:700; }
.pp-busy i { display:inline-block; width:34px; height:8px; border-radius:4px; background:#E7EEEE; position:relative; overflow:hidden; }
.pp-busy i:after { content:""; position:absolute; inset:0; width:var(--w); background:var(--c); }
.pp-pass { position:relative; border-radius:24px; overflow:hidden; display:flex; color:#0A2A33; background:#fff;
  border:1px solid #DCEBE9; box-shadow:0 16px 40px rgba(10,61,69,.16); }
.pp-pass .l { flex:1; padding:20px 24px; }
.pp-pass .r { width:210px; padding:18px; background:linear-gradient(160deg,#0A3D45,#0F7C80); color:#fff; text-align:center;
  border-left:2px dashed rgba(255,255,255,.5); }
.pp-pass .r img { width:150px; height:150px; border-radius:12px; background:#fff; padding:6px; }
.pp-pass .id { font-family:'Sora','Inter',sans-serif; font-weight:800; letter-spacing:.08em; margin-top:8px; }
.pp-pass .kick { font-size:.72rem; letter-spacing:.18em; font-weight:800; color:#0F7C80; }
.pp-pass h3 { margin:.2rem 0 .6rem; }
.pp-pass .row { display:flex; gap:26px; flex-wrap:wrap; margin-top:6px; }
.pp-pass .row div { font-size:.78rem; color:#5B7177; text-transform:uppercase; letter-spacing:.06em; font-weight:700; }
.pp-pass .row div b { display:block; font-size:1rem; color:#0A2A33; text-transform:none; letter-spacing:0; margin-top:2px; }
.pp-bring li { margin:4px 0; }
.pp-share { display:inline-flex; align-items:center; gap:8px; padding:9px 16px; border-radius:12px; font-weight:700;
  background:#25A244; color:#fff !important; text-decoration:none; }
</style>"""

NEEDS = ["Wheelchair access", "Interpreter (my language)", "Companion / attendant", "Large print or reading help"]
BRING = ["Your OcuLens report (download it from My results)", "Your glasses, or your contact lens case",
         "All eye drops and medicines you are using", "Earlier prescriptions and test reports",
         "An ID card or your ABHA health card",
         "Someone to go with you: drops used at the visit can blur your vision for a few hours, so do not drive back"]
BRING_VIDEO = ["A phone with a working camera, good light and internet", "Your OcuLens report",
               "All eye drops and medicines you are using", "A quiet place for the call"]


def _ampm(s):
    h, m = map(int, s.split(":"))
    return f"{(h - 1) % 12 + 1}:{m:02d} {'AM' if h < 12 else 'PM'}"


def _busy(taken_n, total=None):
    """How full a doctor's day is, from the portal's own bookings."""
    frac = taken_n / max(1, total or len(SLOTS))
    label, color = ((T("Quiet day"), "#2E9E5B") if frac < 0.25 else (T("Moderately busy"), "#E8A33D") if frac < 0.6
                    else (T("Busy day"), "#E2664F"))
    return f"<span class='pp-busy'><i style='--w:{max(8, int(frac * 100))}%;--c:{color}'></i>{esc(label)}</span>"


def _free_slots(doctor, day):
    """Free times from the doctor's own calendar (weekly sessions, leave days) minus existing bookings."""
    taken = db.booked_slots(doctor, day.isoformat())
    now = dt.datetime.now()
    return [x for x in db.slots_for(doctor, day.isoformat())
            if x not in taken and not (day == now.date() and x <= now.strftime("%H:%M"))]


def _earliest(hs, days=10):
    """The soonest free slot among the nearest hospitals' doctors."""
    best = None
    for d0 in range(days):
        day = dt.date.today() + dt.timedelta(days=d0)
        for h in hs[:4]:
            for doc, spec in h["doctors"]:
                free = _free_slots(doc, day)
                if free:
                    cand = (day, free[0], h, doc)
                    if best is None or (cand[0], cand[1], h["km"]) < (best[0], best[1], best[2]["km"]):
                        best = cand
        if best:
            return best
    return None


def _book(ctx, u, pid, case_id, place, doctor, day, slot, visit, needs, reason):
    aid = db.add_appointment(case_id, place, doctor, u["name"], patient_id=pid, preferred_date=day.isoformat(),
                             note=reason, slot=slot, visit_type=visit, needs=", ".join(needs))
    if aid is False:
        st.error(T("Sorry, that time was just booked. Please pick another time."))
        return
    db.add_reminder(pid, f"{T('Appointment')}: {doctor} · {place} · {_ampm(slot)}", day.isoformat(), "appointment")
    ctx.play_sound("success")
    st.session_state["pp_book_h"] = None
    st.session_state["pp_pass"] = aid
    st.rerun()


def _nearby_booking(ctx, u, pid):
    ss = st.session_state
    st.markdown(BOOK_CSS, unsafe_allow_html=True)
    cases = db.cases_for_patient(pid) if pid else []
    task = cases[0]["task"] if cases else None
    case_id = cases[0]["id"] if cases else None
    st.markdown(f"### {T('Book an eye hospital near you')}")
    loc = _where_am_i(u)
    if not loc:
        st.info(T("Share your location, or choose your area or pincode, to see the nearest eye hospitals."))
        return
    f = st.columns([1.1, 1.2, 1.2, 1.3])
    mode = f[0].selectbox(T("Getting there"), list(geo.TRAVEL), format_func=T, key="pp_travel")
    visit = f[1].radio(T("Visit type"), ["In person", "Video consultation"], format_func=T, key="pp_visit")
    low_cost = f[2].toggle(T("Low-cost only"), key="pp_lowcost",
                           help=T("Government and charitable hospitals usually cost less."))
    only_fit = f[3].toggle(T("Only hospitals suited to my last check"), key="pp_only_fit") if task else False
    hs = geo.nearest(loc[0], loc[1], task, only_fit, mode, low_cost)
    if not hs:
        st.warning(T("No hospital matches these filters. Switch a filter off."))
        return
    ss["pp_visit_type"] = visit
    best = _earliest(hs)
    if best:
        day, slot, h, doc = best
        when = T("Today") if day == dt.date.today() else (T("Tomorrow") if day == dt.date.today() + dt.timedelta(days=1)
                                                          else day.strftime("%a %d %b"))
        e = st.columns([3.2, 1])
        e[0].markdown(f"<div class='pp-earliest'><div class='cal'><b>{day.strftime('%b').upper()}</b>"
                      f"<span>{day.day}</span></div><div><div class='k'>{esc(T('EARLIEST AVAILABLE NEAR YOU'))}</div>"
                      f"<div class='big'>{esc(when)}, {_ampm(slot)}</div><div style='margin-top:4px'>{esc(doc)} · "
                      f"{esc(h['hospital'])}, {esc(h['branch'])} · {h['km']:.1f} km · {T('about')} {h['minutes']} "
                      f"{T('min')}</div></div></div>", unsafe_allow_html=True)
        e[1].write("")
        e[1].write("")
        if e[1].button(T("Book this slot"), type="primary", use_container_width=True, key="pp_book_earliest"):
            _book(ctx, u, pid, case_id, f"{h['hospital']} · {h['branch']}", doc, day, slot, visit, [], "")
    left, right = st.columns([1.25, 1], gap="large")
    with right:
        try:
            st.plotly_chart(_map(loc, hs), use_container_width=True, config={"displayModeBar": False}, key="pp_map")
        except Exception:  # noqa: BLE001  (no map tiles offline: the list still works)
            st.caption(T("The map needs internet; the list works offline."))
        st.caption(T("Distances are straight-line estimates from area centres; travel time assumes city traffic. "
                     "Directions open Google Maps."))
    with left:
        for i, h in enumerate(hs):
            sel = ss.get("pp_book_h") == h["id"]
            day_load = sum(len(db.booked_slots(d, dt.date.today().isoformat())) for d, _ in h["doctors"])
            badges = (chip(T(h["kind"]), "mut") + " " + (chip(T("Suits your last check"), "done") if (task and h["fit"]) else "")
                      + " " + _busy(day_load / max(1, len(h["doctors"]))))
            st.markdown(
                f"<div class='pp-card' style='margin-bottom:6px;{'border:2px solid #0F7C80' if sel else ''}'>"
                f"<div style='display:flex;gap:12px;align-items:center'><div style='width:34px;height:34px;border-radius:50%;"
                f"background:{'#0F7C80' if i == 0 else '#5FA8A6'};color:#fff;display:grid;place-items:center;font-weight:800'>"
                f"{i + 1}</div><div style='flex:1'><b>{esc(h['hospital'])}</b> · {esc(h['branch'])}<br>"
                f"<span style='font-size:.85rem;color:#5B7177'>{h['km']:.1f} km · {T('about')} {h['minutes']} {T('min')} "
                f"({esc(T(mode))})</span></div><a href='{geo.directions_url(h, loc[:2], mode)}' target='_blank' "
                f"style='font-weight:700;color:#0F7C80;font-size:.85rem'>{esc(T('Directions'))}</a></div>"
                f"<div style='margin-top:6px'>{badges}</div></div>", unsafe_allow_html=True)
            if st.button(T("Selected") if sel else T("Book here"), key=f"pp_bh_{h['id']}", use_container_width=True,
                         type="primary" if sel else "secondary"):
                ss["pp_book_h"] = h["id"]
                st.rerun()
        revs = []
        for r in (db.recommendations_for_patient(pid) if pid else []):
            if r["doctor"] not in revs:
                revs.append(r["doctor"])
        if revs and st.button(f"{T('Or book a follow-up with your reviewing doctor')} ({revs[0]})", key="pp_bh_rev",
                              use_container_width=True):
            ss["pp_book_h"] = "review"
            st.rerun()
    sel = ss.get("pp_book_h")
    if not sel:
        return
    if sel == "review" and revs:
        place, docs = "OcuLens partner clinic", [(revs[0], T("Reviewed your eye check"))]
    else:
        h = next((x for x in geo.HOSPITALS if x["id"] == sel), None)
        if not h:
            return
        place, docs = f"{h['hospital']} · {h['branch']}", h["doctors"]
    _slot_picker(ctx, u, pid, case_id, place, docs, visit)


def _slot_picker(ctx, u, pid, case_id, place, docs, visit="In person"):
    with st.container(border=True):
        st.markdown(f"**{T('Book a time at')} {esc(place)}** · {esc(T(visit))}")
        c = st.columns([1.3, 1, 2.2])
        names = [d for d, _ in docs]
        doctor = c[0].selectbox(T("Doctor"), names, format_func=lambda n: f"{n} · {dict(docs)[n]}", key="pp_bk_doc")
        day = c[1].date_input(T("Date"), min_value=dt.date.today(), value=dt.date.today() + dt.timedelta(days=1),
                              key="pp_bk_date")
        grid = db.slots_for(doctor, day.isoformat())
        if not grid:
            c[2].warning(T("The doctor does not work on this day. Please choose another day."))
            return
        taken = db.booked_slots(doctor, day.isoformat())
        free = _free_slots(doctor, day)
        c[2].markdown(_busy(len(taken), len(grid)), unsafe_allow_html=True)
        if not free:
            c[2].warning(T("No free times on this day. Please choose another day."))
            return
        morning = [x for x in free if x < "13:00"]
        afternoon = [x for x in free if x >= "13:00"]
        part = c[2].radio(T("When suits you?"), [T("Morning"), T("Afternoon")] if morning and afternoon else
                          ([T("Morning")] if morning else [T("Afternoon")]), horizontal=True, key="pp_bk_part")
        opts = morning if part == T("Morning") else afternoon
        slot = c[2].pills(T("Available times"), opts, format_func=_ampm, key=f"pp_bk_slot_{part}", default=opts[0])
        needs = st.multiselect(T("Help needed at the visit"), NEEDS, format_func=T, key="pp_bk_needs")
        reason = st.text_input(T("Reason for the visit (optional)"), key="pp_bk_reason")
        st.caption(T("Doctor names are samples for this prototype; the hospitals are real. The hospital confirms "
                     "every booking."))
        if st.button(T("Confirm booking"), type="primary", key="pp_bk_go", disabled=not slot):
            _book(ctx, u, pid, case_id, place, doctor, day, slot, visit, needs, reason)


def _ics(a, patient):
    """Calendar file for the booking (times in IST, written as UTC), with a reminder two hours before."""
    start = dt.datetime.fromisoformat(f"{a['preferred_date']}T{a['slot']}") - dt.timedelta(hours=5, minutes=30)
    end = start + dt.timedelta(minutes=30)
    f = "%Y%m%dT%H%M%SZ"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//OcuLens-AI//Appointments//EN", "BEGIN:VEVENT",
             f"UID:oculens-{a['id']}@oculens.local", f"DTSTAMP:{dt.datetime.now(dt.timezone.utc).strftime(f)}",
             f"DTSTART:{start.strftime(f)}", f"DTEND:{end.strftime(f)}",
             f"SUMMARY:Eye appointment - {a['doctor']}", f"LOCATION:{a['hospital']}, Bengaluru",
             f"DESCRIPTION:OcuLens booking OCL-{a['id']:05d} for {patient}. {a.get('visit_type') or 'In person'}. "
             "Please bring your OcuLens report.",
             "BEGIN:VALARM", "TRIGGER:-PT2H", "ACTION:DISPLAY", "DESCRIPTION:Eye appointment in 2 hours", "END:VALARM",
             "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines)


def _qr_b64(text):
    import base64
    import qrcode
    img = qrcode.make(text, box_size=6, border=1)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return base64.b64encode(b.getvalue()).decode()


def appointment_pass(ctx, u, a):
    """Ticket-style pass: booking ID, QR code for the reception desk, calendar file, WhatsApp share, what to bring."""
    import urllib.parse
    code = f"OCL-{a['id']:05d}"
    day = dt.date.fromisoformat(a["preferred_date"]) if a.get("preferred_date") else None
    when = f"{day.strftime('%a %d %b %Y')}, {_ampm(a['slot'])}" if day and a.get("slot") else T("To be confirmed")
    qr = _qr_b64(f"OcuLens booking {code} | {a['hospital']} | {a['doctor']} | {a.get('preferred_date')} {a.get('slot')}")
    status = T(a["status"].capitalize())
    st.markdown(
        f"<div class='pp-pass'><div class='l'><div class='kick'>{esc(T('APPOINTMENT PASS'))}</div>"
        f"<h3>{esc(a['hospital'])}</h3><div class='row'><div>{esc(T('Doctor'))}<b>{esc(a['doctor'] or '-')}</b></div>"
        f"<div>{esc(T('When'))}<b>{esc(when)}</b></div><div>{esc(T('Visit type'))}<b>{esc(T(a.get('visit_type') or 'In person'))}</b>"
        f"</div><div>{esc(T('Status'))}<b>{esc(status)}</b></div></div>"
        + (f"<div class='row'><div>{esc(T('Help needed at the visit'))}<b>{esc(a['needs'])}</b></div></div>" if a.get("needs") else "")
        + f"<div style='margin-top:12px;font-size:.84rem;color:#5B7177'>{esc(T('Show this pass at the reception desk.'))}</div>"
        f"</div><div class='r'><img src='data:image/png;base64,{qr}'><div class='id'>{code}</div></div></div>",
        unsafe_allow_html=True)
    msg = (f"My eye appointment ({code}): {a['doctor']}, {a['hospital']}, Bengaluru - {when}. "
           f"Booked with OcuLens.")
    b = st.columns([1, 1, 2])
    if a.get("preferred_date") and a.get("slot"):
        b[0].download_button(T("Add to calendar"), _ics(a, u.get("name") or ""), file_name=f"{code}.ics",
                             mime="text/calendar", use_container_width=True, key=f"ics_{a['id']}")
    b[1].markdown(f"<a class='pp-share' href='https://wa.me/?text={urllib.parse.quote(msg)}' target='_blank'>"
                  f"{icon('chat', 18, '#fff')} {esc(T('Share on WhatsApp'))}</a>", unsafe_allow_html=True)
    items = BRING_VIDEO if (a.get("visit_type") == "Video consultation") else BRING
    st.markdown(f"<div class='pp-card pp-bring' style='margin-top:10px'><b>{esc(T('What to bring'))}</b><ul>"
                + "".join(f"<li>{esc(T(x))}</li>" for x in items) + "</ul></div>", unsafe_allow_html=True)


def page_appointments(ctx):
    u, pid, p = _me()
    hero(T("Appointments & reminders"), T("Stay on track"), T("Your hospital visits and reminders in one place."))
    if st.session_state.get("pp_booked_msg"):
        st.success(st.session_state.pop("pp_booked_msg"))
    new = st.session_state.get("pp_pass")
    if new:
        a = db.get_appointment(new)
        if a and a.get("patient_id") == pid:
            st.markdown(BOOK_CSS, unsafe_allow_html=True)
            st.success(T("Booking requested. The hospital will confirm the time; we added a reminder."))
            appointment_pass(ctx, u, a)
            if st.button(T("Done"), key="pp_pass_done"):
                st.session_state["pp_pass"] = None
                st.rerun()
            st.divider()
    _nearby_booking(ctx, u, pid)
    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"### {T('My appointments')}")
        kinds = {"requested": "wait", "confirmed": "done", "completed": "mut", "declined": "red", "cancelled": "red"}
        for a in (db.appointments_for_patient(pid) if pid else []):
            when = " ".join(x for x in (a.get("preferred_date") or "", a.get("slot") or "") if x)
            st.markdown(f"<div class='pp-card' style='margin-bottom:6px'><div style='display:flex;gap:10px;"
                        f"align-items:center'>{icon('calendar', 20, '#E8A33D')}<b>{esc(a['hospital'])}</b></div>"
                        + (f"<div style='font-size:.9rem;margin-top:4px'>{esc(a['doctor'])}</div>" if a.get("doctor") else "")
                        + f"<div style='font-size:.85rem;color:#5B7177;margin-top:2px'>"
                        + (f"{esc(when)}" if when else f"{esc(T('Requested'))} {esc(a['created_at'])}")
                        + f"</div><div style='margin-top:6px'>{chip(T(a['status'].capitalize()), kinds.get(a['status'], 'wait'))}"
                        f"</div></div>", unsafe_allow_html=True)
            if a["status"] in ("requested", "confirmed"):
                b = st.columns(3)
                if b[0].button(T("Show pass"), key=f"pp_show_{a['id']}", use_container_width=True):
                    st.session_state["pp_pass"] = a["id"]
                    st.rerun()
                if a.get("slot") and b[1].button(T("Reschedule"), key=f"pp_res_{a['id']}", use_container_width=True):
                    st.session_state["pp_resched"] = a["id"]
                if b[2].button(T("Cancel"), key=f"pp_cancel_{a['id']}", use_container_width=True):
                    db.set_appointment_status(a["id"], "cancelled")
                    st.rerun()
                if st.session_state.get("pp_resched") == a["id"]:
                    with st.container(border=True):
                        nd = st.date_input(T("New date"), min_value=dt.date.today(), key=f"pp_rd_{a['id']}",
                                           value=dt.date.today() + dt.timedelta(days=1))
                        free = _free_slots(a["doctor"], nd) if a.get("doctor") else db.slots_for("", nd.isoformat())
                        if not free:
                            st.warning(T("No free times on this day. Please choose another day."))
                        else:
                            ns = st.pills(T("Available times"), free, format_func=_ampm, default=free[0],
                                          key=f"pp_rs_{a['id']}")
                            if st.button(T("Move my appointment"), type="primary", key=f"pp_rgo_{a['id']}", disabled=not ns):
                                if db.reschedule_appointment(a["id"], nd.isoformat(), ns):
                                    db.add_reminder(pid, f"{T('Appointment')}: {a['doctor']} · {a['hospital']} · "
                                                         f"{_ampm(ns)}", nd.isoformat(), "appointment")
                                    st.session_state["pp_resched"] = None
                                    st.session_state["pp_booked_msg"] = T("Your appointment was moved. The hospital will confirm the new time.")
                                    ctx.play_sound("confirm")
                                    st.rerun()
                                else:
                                    st.error(T("Sorry, that time was just booked. Please pick another time."))
        hospitals = sorted({d["hospital"] for v in ctx.BLR_REFERRALS.values() for d in v})
        with st.form("pp_appt", border=True):
            st.markdown(f"**{T('Or request any hospital')}**")
            h = st.selectbox(T("Hospital"), hospitals)
            d = st.date_input(T("Preferred date"), min_value=dt.date.today(),
                              value=dt.date.today() + dt.timedelta(days=1))
            note = st.text_input(T("Reason (optional)"))
            if st.form_submit_button(T("Send request"), type="primary", use_container_width=True) and pid:
                db.add_appointment(None, h, "", u["name"], patient_id=pid, preferred_date=d.isoformat(), note=note)
                ctx.play_sound("confirm")
                st.success(f"{T('Appointment requested')}: {h}")
                st.rerun()
        st.caption(T("The hospital confirms the time. Please call them if you do not hear back."))
    with right:
        st.markdown(f"### {T('Reminders')}")
        for r in (db.reminders_for(pid) if pid else []):
            c = st.columns([0.12, 0.7, 0.18])
            done = c[0].checkbox(" ", value=bool(r["done"]), key=f"rem_{r['id']}", label_visibility="collapsed")
            if done != bool(r["done"]):
                db.set_reminder_done(r["id"], done)
                st.rerun()
            style = "text-decoration:line-through;opacity:.55" if r["done"] else ""
            c[1].markdown(f"<div style='{style}'><b>{esc(r['title'])}</b><br><span style='font-size:.82rem;"
                          f"color:#5B7177'>{esc(r['due'])}</span></div>", unsafe_allow_html=True)
            if c[2].button(T("Delete"), key=f"remdel_{r['id']}"):
                db.delete_reminder(r["id"], pid)
                st.rerun()
        with st.form("pp_rem", border=True):
            st.markdown(f"**{T('Add a reminder')}**")
            t = st.text_input(T("What should we remind you about?"), placeholder=T("Follow-up visit"))
            d = st.date_input(T("When"), min_value=dt.date.today(), key="pp_rem_date")
            if st.form_submit_button(T("Add reminder"), use_container_width=True) and t.strip() and pid:
                db.add_reminder(pid, t.strip(), d.isoformat())
                st.rerun()


VT_LABELS = {
    "calTitle": "Step 1: match your screen", "next": "Next",
    "calText": "Hold any bank or ATM card flat against the screen and move the slider until the blue box is "
               "exactly as wide as the card. We remember this for next time.",
    "setupTitle": "Step 2: get ready",
    "setupText": "Cover one eye with your palm (keep your glasses on if you use them). Stand at the chosen distance "
                 "from the screen. A helper can press the buttons, or use the arrow keys.",
    "eye": "Eye being tested", "right": "Right eye", "left": "Left eye", "distance": "Distance from the screen",
    "start": "Start the test", "amsler": "Grid test", "recal": "Match the screen again",
    "testTitle": "Which way do the arms of the E point?",
    "testText": "Answer with the arrows. If you cannot see it, press ?.", "level": "Level",
    "tooSmall": "This screen is too coarse for the smallest letters; step further back if you can.",
    "resTitle": "Your result", "otherEye": "Test the other eye", "worse": "Below 6/60",
    "resText": "6/6 is normal vision. If this is worse than your last test, or below 6/12, please see an eye doctor.",
    "amsTitle": "Grid test (Amsler)",
    "amsText": "Cover one eye, hold the screen at reading distance and look only at the black dot. Do all the "
               "lines look straight and complete?",
    "amsOk": "All lines look straight", "amsBad": "Some lines are wavy, blurred or missing", "back": "Back",
    "amsOkRes": "Good: the grid looks normal.",
    "amsBadRes": "Wavy or missing lines can be a sign of a problem in the retina. Please see an eye doctor soon.",
}


def page_vision(ctx):
    from vision_test import snellen, vision_test
    u, pid, p = _me()
    hero(T("Vision test"), T("Check your eyesight at home"),
         T("A quick eye-chart test on this screen. Use it to notice changes between doctor visits."))
    labels = {k: T(v) for k, v in VT_LABELS.items()}
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        res = vision_test(labels, key="pp_vt")
        if res and pid and st.session_state.get("pp_vt_last") != res.get("t"):
            st.session_state["pp_vt_last"] = res.get("t")
            if res["kind"] == "acuity":
                lm = res.get("logmar")
                db.add_vision_test(pid, res["eye"], "acuity", lm, snellen(lm), res.get("distance"))
                ctx.play_sound("success")
            else:
                db.add_vision_test(pid, res["eye"], "amsler", amsler=res.get("amsler"))
                ctx.play_sound("alert" if res.get("amsler") == "distorted" else "confirm")
            st.toast(T("Saved to your vision history."))
        st.caption(T("A screening aid only: lighting, screen and distance affect the result. It does not replace a "
                     "vision test at the clinic."))
    with right:
        rows = db.vision_tests_for(pid) if pid else []
        acu = [r for r in rows if r["kind"] == "acuity"]
        st.markdown(f"#### {T('Your vision history')}")
        if acu:
            import plotly.graph_objects as go_
            fig = go_.Figure()
            for eye, col in (("Right", "#0F7C80"), ("Left", "#3B5BA5")):
                pts = [r for r in acu if r["eye"] == eye]
                if pts:
                    fig.add_trace(go_.Scatter(x=[r["taken_at"] for r in pts],
                                              y=[1.1 if r["logmar"] is None else r["logmar"] for r in pts],
                                              mode="lines+markers", name=T(f"{eye} eye"), line=dict(color=col, width=3)))
            fig.update_yaxes(autorange="reversed", tickvals=[1.0, 0.6, 0.3, 0.0], ticktext=["6/60", "6/24", "6/12", "6/6"])
            fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.3),
                              plot_bgcolor="#F7FBFB")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="vt_hist")
            last = {e: next((r for r in reversed(acu) if r["eye"] == e), None) for e in ("Right", "Left")}
            c = st.columns(2)
            for col, e in zip(c, ("Right", "Left")):
                r = last[e]
                col.markdown(f"<div class='pp-card'><div class='t' style='font-size:.74rem;font-weight:700;color:#5B7177'>"
                             f"{esc(T(e + ' eye')).upper()}</div><div style='font-size:1.5rem;font-weight:800;color:#0F7C80'>"
                             f"{esc(r['snellen'] if r else '-')}</div><div style='font-size:.78rem;color:#5B7177'>"
                             f"{esc(r['taken_at'][:10] if r else '')}</div></div>", unsafe_allow_html=True)
            worse = [e for e in ("Right", "Left")
                     if len([r for r in acu if r["eye"] == e]) >= 2
                     and ([r for r in acu if r["eye"] == e][-1]["logmar"] or 1.1) - ([r for r in acu if r["eye"] == e][-2]["logmar"] or 1.1) >= 0.2]
            if worse:
                st.warning(T("Your vision is lower than at your last test. Please see an eye doctor."))
        else:
            st.info(T("Your results will appear here after your first test."))
        ams = [r for r in rows if r["kind"] == "amsler"]
        if ams:
            r = ams[-1]
            st.markdown(f"{T('Last grid test')}: " + (chip(T("Normal"), "done") if r["amsler"] == "normal"
                                                       else chip(T("Wavy lines reported"), "red"))
                        + f" · {esc(r['taken_at'])}", unsafe_allow_html=True)


def _next_dose(meds):
    now = dt.datetime.now()
    best = None
    for m in meds:
        for dd in range(0, 2):
            day = now.date() + dt.timedelta(days=dd)
            if day > dt.date.fromisoformat(m["end_date"]):
                continue
            for t in filter(None, m["times"].split(",")):
                when = dt.datetime.combine(day, dt.time.fromisoformat(t))
                if when >= now - dt.timedelta(minutes=30) and (day.isoformat(), t) not in db.doses_taken(m["id"]):
                    if best is None or when < best[0]:
                        best = (when, m)
    return best


def page_drops(ctx):
    u, pid, p = _me()
    hero(T("My eye drops"), T("Your drops, on time"),
         T("The schedule your doctor set. Tick each dose when you put it in."))
    st.markdown(BOOK_CSS, unsafe_allow_html=True)
    meds = db.medications_for(pid) if pid else []
    if not meds:
        st.info(T("Your doctor has not added an eye-drop schedule yet. It will appear here after your visit."))
        return
    nxt = _next_dose(meds)
    if nxt:
        when, m = nxt
        mins = int((when - dt.datetime.now()).total_seconds() // 60)
        due = T("now") if mins <= 0 else (f"{T('in')} {mins} {T('min')}" if mins < 120 else when.strftime("%I:%M %p"))
        st.markdown(f"<div class='pp-earliest' style='background:linear-gradient(120deg,#6C5B9E,#0F7C80)'><div class='cal'>"
                    f"<b>{when.strftime('%b').upper()}</b><span>{when.day}</span></div><div><div class='k'>"
                    f"{esc(T('NEXT DOSE'))}</div><div class='big'>{esc(m['name'])} · {esc(due)}</div><div>"
                    f"{esc(T(m['eye']))} · {esc(m['instructions'] or '')}</div></div></div>", unsafe_allow_html=True)
    today = dt.date.today()
    for m in meds:
        got, due_n = db.adherence(m)
        pct = int(100 * got / due_n) if due_n else 100
        with st.container(border=True):
            c = st.columns([2.2, 1])
            c[0].markdown(f"**{m['name']}** · {T(m['eye'])}  \n{m['instructions'] or ''}  \n"
                          f"<span style='font-size:.8rem;color:#5B7177'>{T('Prescribed by')} {esc(m['prescribed_by'])} · "
                          f"{m['start_date']} → {m['end_date']}</span>", unsafe_allow_html=True)
            ring = ("#2E9E5B" if pct >= 80 else "#E8A33D" if pct >= 50 else "#E2664F")
            c[1].markdown(f"<div style='display:flex;gap:10px;align-items:center'><div style='width:58px;height:58px;"
                          f"border-radius:50%;background:conic-gradient({ring} {pct * 3.6}deg,#E7EEEE 0);display:grid;"
                          f"place-items:center'><div style='width:44px;height:44px;border-radius:50%;background:#fff;"
                          f"display:grid;place-items:center;font-weight:800;font-size:.85rem'>{pct}%</div></div>"
                          f"<div style='font-size:.8rem;color:#5B7177'>{esc(T('doses taken on time'))}<br>{got}/{due_n}</div>"
                          f"</div>", unsafe_allow_html=True)
            if today <= dt.date.fromisoformat(m["end_date"]):
                taken = db.doses_taken(m["id"])
                tc = st.columns(max(1, len(m["times"].split(","))))
                for col, t in zip(tc, filter(None, m["times"].split(","))):
                    done = (today.isoformat(), t) in taken
                    new = col.checkbox(f"{T('Today')} {_ampm(t)}", value=done, key=f"dose_{m['id']}_{t}")
                    if new != done:
                        db.set_dose(m["id"], today.isoformat(), t, new)
                        if new:
                            ctx.play_sound("confirm")
                        st.rerun()
    st.caption(T("Only your doctor sets or changes this schedule. If your eye gets worse while using the drops, "
                 "see your doctor; do not change the drops yourself."))


def page_learn(ctx):
    hero(T("Learn"), T("Know your eyes"), T("Short, simple answers to common questions about eye health."))
    icons = ["eye", "spark", "alert", "heart", "eye", "spark", "chart", "heart"]
    for row in range(0, len(pc.LEARN), 4):
        cols = st.columns(4)
        for col, (t, d), ic in zip(cols, pc.LEARN[row:row + 4], icons[row:row + 4]):
            col.markdown(f"<div class='pp-learn'><div class='ic'>{icon(ic, 22, '#fff')}</div><b>{esc(T(t))}</b>"
                         f"<p>{esc(T(d))}</p></div>", unsafe_allow_html=True)
        st.write("")
    st.markdown(f"### {T('Myth or fact?')}")
    st.caption(T("Hover over or tap a card to see the answer."))
    for row in range(0, len(pc.MYTHS), 3):
        cols = st.columns(3)
        for col, (m, f) in zip(cols, pc.MYTHS[row:row + 3]):
            col.markdown(f"<div class='pp-flip' tabindex='0'><div class='in'><div class='f'><div class='tag'>"
                         f"{esc(T('MYTH?'))}</div><div class='q'>{esc(T(m))}</div></div><div class='b'><div class='tag'>"
                         f"{esc(T('FACT'))}</div><div class='q'>{esc(T(f))}</div></div></div></div>",
                         unsafe_allow_html=True)
        st.write("")
    st.markdown(f"### {T('Everyday tips')}")
    st.markdown("<div class='pp-card'><ul>" + "".join(f"<li>{esc(T(t))}</li>" for t in pc.TIPS) + "</ul></div>",
                unsafe_allow_html=True)


def page_emergency(ctx):
    import urllib.parse
    hero(T("Emergency help"), T("If it is urgent, act now"), T("Some eye problems need a hospital the same day."))
    st.markdown(f"<div class='pp-sos'><h2>{esc(T('Go to a hospital now if you have:'))}</h2><ul>"
                + "".join(f"<li>{esc(T(x))}</li>" for x in pc.EMERGENCY)
                + f"</ul><a class='pp-call' href='tel:108'>{icon('phone', 22, '#B42318')} {esc(T('Call 108 (ambulance)'))}"
                f"</a><a class='pp-call' href='tel:112'>{icon('phone', 22, '#B42318')} {esc(T('Call 112 (emergency)'))}</a>"
                "</div>", unsafe_allow_html=True)
    st.write("")
    c = st.columns(2, gap="large")
    c[0].markdown(f"<div class='pp-card'><h4>{esc(T('Chemical in the eye'))}</h4><ol>"
                  + "".join(f"<li>{esc(T(x))}</li>" for x in pc.FIRSTAID_CHEM) + "</ol></div>", unsafe_allow_html=True)
    c[1].markdown(f"<div class='pp-card'><h4>{esc(T('Injury to the eye'))}</h4><ol>"
                  + "".join(f"<li>{esc(T(x))}</li>" for x in pc.FIRSTAID_INJURY) + "</ol></div>", unsafe_allow_html=True)
    st.write("")
    u, pid, p = _me()
    loc = _my_coords(u)
    if loc:
        st.markdown(f"#### {T('Nearest eye hospitals')} · {esc(loc[2])}")
        cols = st.columns(3)
        for i, h in enumerate(geo.nearest(loc[0], loc[1])[:6]):
            cols[i % 3].markdown(f"<div class='pp-card' style='margin-bottom:10px'><b>{i + 1}. {esc(h['hospital'])}</b><br>"
                                 f"<span style='font-size:.85rem;color:#5B7177'>{esc(h['branch'])} · {h['km']:.1f} km · "
                                 f"{T('about')} {h['minutes']} {T('min')}</span><br><a href='{geo.directions_url(h, loc[:2])}' "
                                 f"target='_blank' style='font-weight:700;color:#0F7C80;font-size:.85rem'>"
                                 f"{esc(T('Directions'))}</a></div>", unsafe_allow_html=True)
        st.caption(T("Call the hospital on the way to confirm that its emergency service is open."))
        return
    st.markdown(f"#### {T('Eye hospitals in Bengaluru')}")
    hs = {d["hospital"]: d for v in ctx.BLR_REFERRALS.values() for d in v}
    cols = st.columns(3)
    for i, d in enumerate(hs.values()):
        q = urllib.parse.quote_plus(f"{d['hospital']} {d['area']} Bengaluru")
        cols[i % 3].markdown(f"<div class='pp-card' style='margin-bottom:10px'><b>{esc(d['hospital'])}</b><br>"
                             f"<span style='font-size:.85rem;color:#5B7177'>{esc(d['area'])}</span><br>"
                             f"<a href='https://www.google.com/maps/search/?api=1&query={q}' target='_blank' "
                             f"style='font-weight:700;color:#0F7C80;font-size:.85rem'>{esc(T('Open in Maps'))}</a></div>",
                             unsafe_allow_html=True)
    st.caption(T("Call the hospital on the way to confirm that its emergency service is open."))


def page_profile(ctx):
    u, pid, p = _me()
    hero(T("My profile"), u.get("name") or "", T("Your details, language and voice."))
    fresh = db.get_user(u["id"]) or u
    left, right = st.columns(2, gap="large")
    with left:
        with st.form("pp_prof", border=True):
            st.markdown(f"**{T('Your details')}**")
            st.text_input(T("Name"), value=fresh.get("name") or "", disabled=True)
            age = st.number_input(T("Age"), 0, 120, int((p or {}).get("age") or 30))
            sexes = ["", "M", "F", "Other"]
            sex = st.selectbox(T("Sex"), sexes, index=sexes.index((p or {}).get("sex") or "") if (p or {}).get("sex") in sexes else 0)
            phone = st.text_input(T("Phone"), value=fresh.get("phone") or "")
            langs = list(ctx.LANGUAGES)
            lang = st.selectbox(T("Language"), langs, index=langs.index(fresh.get("lang") or "en")
                                if (fresh.get("lang") or "en") in langs else 0,
                                format_func=lambda k: ctx.LANGUAGES[k][0])
            if st.form_submit_button(T("Save"), type="primary", use_container_width=True):
                db.update_profile(u["id"], phone=phone, lang=lang, age=age, sex=sex)
                st.session_state["pending_lang"] = lang
                st.success(T("Saved."))
                st.rerun()
    with right:
        with st.form("pp_pw", border=True):
            st.markdown(f"**{T('Change password')}**")
            old = st.text_input(T("Current password"), type="password")
            new = st.text_input(T("New password"), type="password")
            if st.form_submit_button(T("Change password"), use_container_width=True):
                ok, msg = db.change_password(u["id"], old, new)
                (st.success if ok else st.error)(T(msg))
        st.markdown(f"<div class='pp-card'>{icon('heart', 20, '#E2664F')} <b>{esc(T('Your privacy'))}</b><br>"
                    f"<span style='font-size:.88rem'>{esc(T('Only you and the clinic doctors can see your photos and results.'))}"
                    "</span></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- menu
PAGE_KEYS = [("home", "My eye health"), ("selfcheck", "Self-check"), ("results", "My results"),
             ("drops", "My eye drops"), ("vision", "Vision test"),
             ("diary", "Symptom diary"), ("appointments", "Appointments & reminders"), ("assistant", "AI assistant"),
             ("learn", "Learn"), ("emergency", "Emergency help"), ("profile", "My profile")]


def page_label(key):
    return T(dict(PAGE_KEYS)[key])


def pages(ctx):
    """Menu label (in the patient's language) -> page function."""
    funcs = {"home": page_home, "selfcheck": page_selfcheck, "results": page_results, "diary": page_diary,
             "drops": page_drops, "vision": page_vision,
             "appointments": page_appointments, "assistant": lambda c: c.page_assistant(), "learn": page_learn,
             "emergency": page_emergency, "profile": page_profile}
    return {T(lab): (lambda f=funcs[k]: f(ctx)) for k, lab in PAGE_KEYS}
