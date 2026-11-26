"""Natural Indian voices generated on the server, so every browser (not only Microsoft Edge) can speak Kannada,
Tamil, Telugu, Hindi and Indian English.

Uses Microsoft's neural voices through the open-source `edge-tts` client (needs internet). The spoken text is sent
to Microsoft's speech service; switch "Natural cloud voice" off in the sidebar to keep everything on this computer
(the browser's own voices are then used). For a production system, use the official Azure Speech service, which
offers the same voices with a service agreement. Audio is cached on disk, so a repeated sentence costs nothing.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import ssl
from pathlib import Path

import settings  # noqa: E402

CACHE = settings.data_dir() / "storage" / "tts_cache"

VOICES = {  # (female, male)
    "en": ("en-IN-NeerjaNeural", "en-IN-PrabhatNeural"),
    "hi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
    "kn": ("kn-IN-SapnaNeural", "kn-IN-GaganNeural"),
    "ta": ("ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"),
    "te": ("te-IN-ShrutiNeural", "te-IN-MohanNeural"),
}
_SCRIPTS = [("hi", r"[ऀ-ॿ]"), ("kn", r"[ಀ-೿]"), ("ta", r"[஀-௿]"), ("te", r"[ఀ-౿]")]


def script_lang(text: str, fallback: str = "en") -> str:
    for lang, rx in _SCRIPTS:
        if re.search(rx, text):
            return lang
    return "en" if re.search(r"[A-Za-z]", text) else fallback


def clean(text: str) -> str:
    t = re.sub(r"https?://\S+", "", text or "")
    t = re.sub(r"[*_#>`|]", " ", t)
    t = re.sub(r"^\s*[-•]\s*", "", t, flags=re.M)
    t = re.sub(r"\bDr\.", "Doctor", t)
    return re.sub(r"\s+", " ", t).strip()


def _segments(text: str, lang: str) -> list[tuple[str, str]]:
    """Consecutive sentences grouped by script, so each part gets a voice that can read it."""
    parts = re.findall(r"[^.!?।]+[.!?।]?", text) or [text]
    segs: list[tuple[str, str]] = []
    for p in (x.strip() for x in parts):
        if not p:
            continue
        lg = script_lang(p, lang)
        if segs and segs[-1][0] == lg:
            segs[-1] = (lg, segs[-1][1] + " " + p)
        else:
            segs.append((lg, p))
    return segs


def _ssl_context():
    try:  # the Windows / macOS certificate store (works behind campus networks that re-sign TLS)
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


async def _speak(text: str, voice: str) -> bytes:
    import edge_tts
    import edge_tts.communicate as ec
    ec._SSL_CTX = _ssl_context()
    out = b""
    async for ch in edge_tts.Communicate(text, voice, rate="-4%").stream():
        if ch["type"] == "audio":
            out += ch["data"]
    return out


def synthesize(text: str, lang: str = "en", gender: str = "female", timeout: float = 20.0) -> bytes | None:
    """MP3 bytes for the text (None when offline or the service fails)."""
    t = clean(text)
    if not t:
        return None
    g = 1 if (gender or "").lower().startswith("m") else 0
    key = hashlib.sha256(f"{g}|{lang}|{t}".encode()).hexdigest()[:32]
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{key}.mp3"
    if f.exists() and f.stat().st_size > 0:
        return f.read_bytes()
    try:
        async def run():
            audio = b""
            for lg, seg in _segments(t, lang):
                audio += await _speak(seg, VOICES.get(lg, VOICES["en"])[g])
            return audio
        audio = asyncio.run(asyncio.wait_for(run(), timeout))
    except Exception:  # noqa: BLE001  (offline, blocked or timed out: the browser voice takes over)
        return None
    if audio:
        f.write_bytes(audio)
    return audio or None


def data_url(text: str, lang: str = "en", gender: str = "female") -> str:
    a = synthesize(text, lang, gender)
    return ("data:audio/mpeg;base64," + base64.b64encode(a).decode()) if a else ""
