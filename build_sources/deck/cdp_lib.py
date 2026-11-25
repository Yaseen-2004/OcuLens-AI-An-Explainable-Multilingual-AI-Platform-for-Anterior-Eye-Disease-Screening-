"""Drive the live portal in headless Chrome (fake camera = a real eye photo) and screenshot
each stage of the guided right/left capture, then run the two-eye screening."""
import asyncio, base64, json, os, subprocess, sys, time, urllib.request

import websockets

SP = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SP, "deck_shots")
os.makedirs(OUT, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333

HELPERS = r"""
window.__ec = () => { for (const e of document.querySelectorAll('*'))
    if (e.shadowRoot && e.shadowRoot.querySelector('.ec')) return e.shadowRoot.querySelector('.ec'); return null; };
window.__clickText = (txt, sel) => { const b = [...document.querySelectorAll(sel || 'button, label')]
    .find(e => e.innerText && e.innerText.trim() === txt); if (!b) return false; b.scrollIntoView({block:'center'}); b.click(); return true; };
window.__ecState = () => { const r = window.__ec(); if (!r) return null; const q = (s) => r.querySelector(s);
    const vid = q('.ec-video');
    return { title: q('.ec-title') && q('.ec-title').innerText, hint: q('.ec-hint') && q('.ec-hint').innerText,
      meter: q('.ec-meter .val') && q('.ec-meter .val').innerText, lapEst: q('.ec-fill') ? Math.round(parseFloat(q('.ec-fill').style.width) * 1.2) : null,
      checks: [...r.querySelectorAll('.ec-ck')].map(e => e.innerText),
      chips: [...r.querySelectorAll('.ec-chip')].map(e => e.className.replace('ec-chip','').trim() + ':' + e.innerText.replace(/\s+/g,' ')),
      reviewing: !q('.ec-review').classList.contains('hide'), reviewQ: q('.ec-review-q') && q('.ec-review-q').innerText,
      done: q('.ec-done') && q('.ec-done').style.display === 'block',
      video: vid ? vid.videoWidth + 'x' + vid.videoHeight : null,
      msg: q('.ec-msg') && q('.ec-msg').style.display === 'flex' ? q('.ec-msg').innerText : '' }; };
true;
"""


class CDP:
    def __init__(self, ws):
        self.ws, self.i = ws, 0

    async def call(self, method, **params):
        self.i += 1
        mid = self.i
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            m = json.loads(await self.ws.recv())
            if m.get("id") == mid:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    async def js(self, expr):
        r = await self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))
        return r["result"].get("value")

    async def shot(self, name):
        r = await self.call("Page.captureScreenshot", format="png")
        p = os.path.join(OUT, name)
        open(p, "wb").write(base64.b64decode(r["data"]))
        print("  screenshot ->", name, flush=True)

    async def wait(self, expr, timeout, what):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                await self.js(HELPERS)
                v = await self.js(expr)
                if v:
                    return v
            except Exception:  # noqa: BLE001 - page may be mid-rerender
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"timed out waiting for: {what}")


