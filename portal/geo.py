"""Nearby eye care: hospital directory with locations, Bengaluru areas / pincodes, distance and a browser
"use my location" button.

Coordinates are APPROXIMATE area centres (good to about a kilometre), not exact building locations; directions
always open Google Maps, which finds the real address. The hospitals are real Bengaluru eye-care centres; doctor
names are placeholders marked "(sample)". Location is used only in the browser session to sort hospitals by
distance; only the area name the patient chooses is saved to their profile.
"""
from __future__ import annotations

import math
import urllib.parse

import streamlit.components.v2 as _stc2

# kind: govt / private · fits: which screening tasks the centre suits
HOSPITALS = [
    {"id": "nn_rjn", "hospital": "Narayana Nethralaya", "branch": "Rajajinagar", "lat": 12.9910, "lon": 77.5530,
     "kind": "Private", "fits": ["keratitis", "ulcer_pattern", "trachoma_tf"],
     "doctors": [("Dr. A. Rao (sample)", "Cornea & Refractive Surgery"), ("Dr. R. Nair (sample)", "Preventive Ophthalmology")]},
    {"id": "nn_hbl", "hospital": "Narayana Nethralaya", "branch": "Hebbal", "lat": 13.0358, "lon": 77.5970,
     "kind": "Private", "fits": ["keratitis", "ulcer_pattern"],
     "doctors": [("Dr. V. Menon (sample)", "Cornea Services")]},
    {"id": "ndh_jay", "hospital": "Nethradhama Super Speciality Eye Hospital", "branch": "Jayanagar", "lat": 12.9250,
     "lon": 77.5938, "kind": "Private", "fits": ["keratitis", "ulcer_pattern"],
     "doctors": [("Dr. S. Reddy (sample)", "Cornea & Ocular Surface")]},
    {"id": "aga_kor", "hospital": "Dr. Agarwal's Eye Hospital", "branch": "Koramangala", "lat": 12.9352, "lon": 77.6245,
     "kind": "Private", "fits": ["keratitis", "ulcer_pattern"],
     "doctors": [("Dr. N. Iyer (sample)", "Cornea & Refractive Services")]},
    {"id": "minto", "hospital": "Minto Ophthalmic Hospital (Govt.)", "branch": "Chamrajpet", "lat": 12.9575, "lon": 77.5650,
     "kind": "Government", "fits": ["keratitis", "ulcer_pattern", "trachoma_tf"],
     "doctors": [("Dr. K. Prasad (sample)", "General & Community Ophthalmology")]},
    {"id": "sankara", "hospital": "Sankara Eye Hospital", "branch": "Kundalahalli", "lat": 12.9660, "lon": 77.7160,
     "kind": "Charitable", "fits": ["keratitis", "trachoma_tf"],
     "doctors": [("Dr. M. Shetty (sample)", "Community & Pediatric Ophthalmology")]},
]

AREAS = {  # approximate centres
    "Majestic / Gandhinagar": (12.9767, 77.5713), "MG Road": (12.9756, 77.6066), "Rajajinagar": (12.9910, 77.5530),
    "Malleshwaram": (13.0031, 77.5643), "Yeshwanthpur": (13.0285, 77.5410), "Peenya": (13.0285, 77.5197),
    "Hebbal": (13.0358, 77.5970), "RT Nagar": (13.0213, 77.5951), "Yelahanka": (13.1007, 77.5963),
    "Hennur / Kalyan Nagar": (13.0280, 77.6400), "KR Puram": (13.0076, 77.6960), "Whitefield": (12.9698, 77.7500),
    "Marathahalli": (12.9569, 77.7011), "Indiranagar": (12.9784, 77.6408), "Koramangala": (12.9352, 77.6245),
    "HSR Layout": (12.9121, 77.6446), "BTM Layout": (12.9166, 77.6101), "Electronic City": (12.8452, 77.6602),
    "Bannerghatta Road": (12.8890, 77.5970), "JP Nagar": (12.9063, 77.5857), "Jayanagar": (12.9250, 77.5938),
    "Basavanagudi": (12.9406, 77.5738), "Banashankari": (12.9255, 77.5468), "Chamrajpet": (12.9575, 77.5650),
    "Vijayanagar": (12.9719, 77.5374), "Kengeri": (12.9177, 77.4838),
}
PINCODES = {
    "560009": "Majestic / Gandhinagar", "560001": "MG Road", "560010": "Rajajinagar", "560003": "Malleshwaram",
    "560022": "Yeshwanthpur", "560058": "Peenya", "560024": "Hebbal", "560032": "RT Nagar", "560064": "Yelahanka",
    "560043": "Hennur / Kalyan Nagar", "560036": "KR Puram", "560066": "Whitefield", "560037": "Marathahalli",
    "560038": "Indiranagar", "560034": "Koramangala", "560102": "HSR Layout", "560076": "BTM Layout",
    "560100": "Electronic City", "560078": "JP Nagar", "560011": "Jayanagar", "560004": "Basavanagudi",
    "560070": "Banashankari", "560018": "Chamrajpet", "560040": "Vijayanagar", "560060": "Kengeri",
}


def haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# travel mode -> (Google Maps travelmode, typical Bengaluru speed in km/h)
TRAVEL = {"Car / cab": ("driving", 18), "Two-wheeler": ("driving", 22), "Bus / metro": ("transit", 14),
          "Walking": ("walking", 4.5)}


def travel_minutes(km: float, mode: str = "Car / cab") -> int:
    """Rough city estimate: roads are ~1.4x the straight line; speed depends on the travel mode."""
    speed = TRAVEL.get(mode, TRAVEL["Car / cab"])[1]
    return max(5, int(round(km * 1.4 / speed * 60 / 5) * 5))


def nearest(lat, lon, task=None, only_fit=False, mode="Car / cab", low_cost=False):
    """Hospitals sorted by distance from (lat, lon), each with km, minutes and whether it suits the task."""
    out = []
    for h in HOSPITALS:
        fit = task in h["fits"] if task else True
        if (only_fit and not fit) or (low_cost and h["kind"] not in ("Government", "Charitable")):
            continue
        km = haversine_km(lat, lon, h["lat"], h["lon"])
        out.append({**h, "km": km, "minutes": travel_minutes(km, mode), "fit": fit})
    return sorted(out, key=lambda x: x["km"])


def area_of_pincode(pin: str):
    return PINCODES.get((pin or "").strip())


def nearest_area(lat, lon) -> str:
    return min(AREAS, key=lambda a: haversine_km(lat, lon, *AREAS[a]))


def directions_url(h, origin=None, mode="Car / cab") -> str:
    dest = urllib.parse.quote_plus(f"{h['hospital']} {h['branch']} Bengaluru")
    if origin:
        return (f"https://www.google.com/maps/dir/?api=1&origin={origin[0]:.5f},{origin[1]:.5f}"
                f"&destination={dest}&travelmode={TRAVEL.get(mode, TRAVEL['Car / cab'])[0]}")
    return f"https://www.google.com/maps/search/?api=1&query={dest}"


def in_bengaluru(lat, lon) -> bool:
    return 12.6 <= lat <= 13.4 and 77.2 <= lon <= 78.0


# ---------------------------------------------------------------- "use my location" button (browser geolocation)
_HTML = """<div class="gl"></div>"""
_CSS = r"""
.gl { font-family: inherit; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.gl button { font: inherit; font-weight:700; font-size:.92rem; padding:10px 18px; border-radius:14px; cursor:pointer;
  border:0; color:#fff; background:linear-gradient(135deg,#0F7C80,#36B3A8); box-shadow:0 6px 16px rgba(15,124,128,.3);
  display:inline-flex; align-items:center; gap:8px; }
.gl button:disabled { opacity:.6; cursor:wait; }
.gl .msg { font-size:.84rem; color:#41575C; }
.gl .pulse { width:10px; height:10px; border-radius:50%; background:#fff; animation: glp 1s ease-in-out infinite; }
@keyframes glp { 0%,100% { opacity:.3 } 50% { opacity:1 } }
"""
_JS = r"""
export default function (component) {
  const { parentElement, data, setTriggerValue } = component;
  const root = parentElement.querySelector('.gl');
  if (!root) return;
  const cfg = Object.assign({ label: 'Use my current location', busy: 'Finding you...', denied: 'Location permission was denied.' }, data || {});
  const PIN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11Z"/><circle cx="12" cy="10" r="2.2"/></svg>';
  root.innerHTML = `<button>${PIN}<span>${cfg.label}</span></button><span class="msg"></span>`;
  const btn = root.querySelector('button'), msg = root.querySelector('.msg');
  btn.onclick = () => {
    if (!navigator.geolocation) { msg.textContent = 'This browser cannot share location. Choose your area instead.'; return; }
    btn.disabled = true; btn.querySelector('span').textContent = cfg.busy;
    navigator.geolocation.getCurrentPosition((p) => {
      btn.disabled = false; btn.querySelector('span').textContent = cfg.label;
      setTriggerValue('loc', { lat: p.coords.latitude, lon: p.coords.longitude, acc: p.coords.accuracy, t: Date.now() });
    }, (e) => {
      btn.disabled = false; btn.querySelector('span').textContent = cfg.label;
      msg.textContent = e.code === 1 ? cfg.denied + ' Allow it from the address bar, or choose your area below.'
        : 'Could not get your location. Choose your area below.';
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
  };
}
"""
_NAME = "oculens_geolocate"
_mount = None


def _component():
    global _mount
    from streamlit.runtime import Runtime
    registry = Runtime.instance().bidi_component_registry if Runtime.exists() else None
    if _mount is None or (registry is not None and registry.get(_NAME) is None):
        _mount = _stc2.component(_NAME, html=_HTML, css=_CSS, js=_JS)
    return _mount


def locate_button(label="Use my current location", busy="Finding you...", key="geoloc"):
    """Returns {"lat", "lon", "acc"} on the run the browser reports a position, else None."""
    res = _component()(key=key, data={"label": label, "busy": busy}, on_loc_change=lambda: None)
    v = res.get("loc") if hasattr(res, "get") else getattr(res, "loc", None)
    return v or None
