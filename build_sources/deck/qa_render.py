"""Layout QA for a pptx without PowerPoint/LibreOffice: rebuild each slide as HTML from the pptx
(positions, sizes, fonts, colours, insets, images), render it in headless Chrome with the real
Windows fonts, report text boxes whose content overflows, and screenshot every slide.
Charts are drawn as labelled placeholders (their content is checked separately)."""
import asyncio, base64, html, json, os, subprocess, sys, time, urllib.request

import websockets
from pptx import Presentation
from pptx.enum.dml import MSO_COLOR_TYPE
from pptx.util import Emu

from cdp_lib import CDP, CHROME, SP

DECK = sys.argv[1]
OUTD = os.path.join(SP, "qa")
os.makedirs(OUTD, exist_ok=True)
PX = 100 / 914400          # 100 px per inch
THEME = {"dk1": "0E1A2B", "lt1": "FFFFFF", "dk2": "0A1A33", "lt2": "EEF3FC", "accent1": "2F6BFF", "accent2": "C6F23B",
         "accent3": "FF6B57", "accent4": "F0A93B", "accent5": "19C2A9", "accent6": "8A9BB8",
         "tx1": "0E1A2B", "bg1": "FFFFFF", "tx2": "0A1A33", "bg2": "EEF3FC"}
HEAD, BODY = "Century Schoolbook", "Calibri"
BG = {"HERO": "bg_dark.png", "DARK": "bg_dark.png", "LIGHT": "bg_light.png"}
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def b64(path_or_blob, mime="image/png"):
    data = open(path_or_blob, "rb").read() if isinstance(path_or_blob, str) else path_or_blob
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def clr(el):
    """Colour from an <a:solidFill>-like parent element (srgbClr or schemeClr)."""
    if el is None:
        return None
    s = el.find("a:srgbClr", NS)
    if s is not None:
        return "#" + s.get("val")
    s = el.find("a:schemeClr", NS)
    if s is not None:
        return "#" + THEME.get(s.get("val"), "FF00FF")
    return None


def fill_of(sppr):
    if sppr is None:
        return None
    sf = sppr.find("a:solidFill", NS)
    if sf is None:
        return None
    alpha = sf.find(".//a:alpha", NS)
    c = clr(sf)
    if c and alpha is not None and int(alpha.get("val")) < 5000:
        return None
    return c


def geom(sppr):
    g = sppr.find("a:prstGeom", NS) if sppr is not None else None
    return g.get("prst") if g is not None else "rect"


def text_html(txbody, title=False, dark=False):
    bp = txbody.find("a:bodyPr", NS)
    ins = [int(bp.get(k, d)) * PX for k, d in (("tIns", 45720), ("rIns", 91440), ("bIns", 45720), ("lIns", 91440))]
    anchor = {"t": "flex-start", "ctr": "center", "b": "flex-end"}.get(bp.get("anchor", "t"), "flex-start")
    paras = []
    for p in txbody.findall("a:p", NS):
        ppr = p.find("a:pPr", NS)
        algn = {"ctr": "center", "r": "right", "just": "justify"}.get(ppr.get("algn") if ppr is not None else None, "left")
        spc = p.find("a:pPr/a:spcAft/a:spcPts", NS)
        after = int(spc.get("val")) / 100 * 100 / 72 if spc is not None else 0
        bullet = ppr is not None and (ppr.find("a:buChar", NS) is not None or ppr.find("a:buAutoNum", NS) is not None)
        runs = []
        for r in p.findall("a:r", NS) + p.findall("a:fld", NS):
            rpr = r.find("a:rPr", NS)
            t = r.find("a:t", NS)
            if t is None:
                continue
            size = int(rpr.get("sz")) / 100 if rpr is not None and rpr.get("sz") else (36 if title else 18)
            bold = (rpr is not None and rpr.get("b") == "1") or title
            ital = rpr is not None and rpr.get("i") == "1"
            col = clr(rpr.find("a:solidFill", NS)) if rpr is not None else None
            col = col or ("#FFFFFF" if (title and dark) else "#" + THEME["dk2"] if title else "#000000")
            lat = rpr.find("a:latin", NS) if rpr is not None else None
            face = lat.get("typeface") if lat is not None else None
            face = HEAD if (face in (None, "+mj-lt") and title) or face == "+mj-lt" else (BODY if face in (None, "+mn-lt") else face)
            sp = int(rpr.get("spc")) / 100 if rpr is not None and rpr.get("spc") else 0
            runs.append(f'<span style="font-family:\'{face}\';font-size:{size * 100 / 72:.2f}px;font-weight:{700 if bold else 400};'
                        f'font-style:{"italic" if ital else "normal"};color:{col};letter-spacing:{sp * 100 / 72:.2f}px">{html.escape(t.text or "")}</span>')
        pad = "padding-left:22px;text-indent:-14px;" if bullet else ""
        mark = "&#8226;&nbsp;" if bullet else ""
        paras.append(f'<div style="text-align:{algn};margin-bottom:{after:.1f}px;line-height:1.2;{pad}">{mark}{"".join(runs) or "&nbsp;"}</div>')
    return ins, anchor, "".join(paras)


def slide_html(slide, idx, deckdir):
    layout = slide.slide_layout.name
    dark = layout in ("HERO", "DARK")
    bg = BG.get(layout)
    out = [f'<div id="slide" style="position:relative;width:1333px;height:750px;overflow:hidden;'
           f'background:{"#0A1A33" if dark else "#fff"} url({b64(os.path.join(deckdir, "img", bg))}) 0 0/100% 100%">'] if bg else ['<div id="slide">']
    shapes = list(slide.shapes)
    # title placeholder geometry comes from the layout
    for i, sh in enumerate(shapes):
        el = sh._element
        x, y, w, h = (sh.left or 0) * PX, (sh.top or 0) * PX, (sh.width or 0) * PX, (sh.height or 0) * PX
        name = html.escape(sh.name)
        box = f"left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;"
        tag = el.tag.split("}")[1]
        if tag == "pic":
            sppr = el.find("p:spPr", NS)
            rad = "border-radius:50%;" if geom(sppr) == "ellipse" else ""
            out.append(f'<img data-name="{name}" style="position:absolute;{box}{rad}object-fit:cover" src="{b64(sh.image.blob, "image/" + sh.image.ext)}">')
            continue
        if tag == "graphicFrame":
            if sh.has_table:
                rows = []
                for r in sh.table.rows:
                    cells = []
                    for cidx, cell in enumerate(r.cells):
                        tcpr = cell._tc.find("a:tcPr", NS)
                        f = fill_of(tcpr) or "#FFFFFF"
                        _, _, inner = text_html(cell._tc.find("a:txBody", NS))
                        cw = sh.table.columns[cidx].width * PX
                        cells.append(f'<td style="box-sizing:border-box;background:{f};width:{cw:.1f}px;padding:7px 8px;border:1px solid #D3DDEE;vertical-align:middle">{inner}</td>')
                    rows.append(f'<tr style="height:{r.height * PX:.1f}px">{"".join(cells)}</tr>')
                planned = sum(r.height for r in sh.table.rows) * PX
                out.append(f'<table class="tbl" data-name="{name}" data-h="{planned:.1f}" style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;border-collapse:collapse;table-layout:fixed">{"".join(rows)}</table>')
            else:
                out.append(f'<div style="position:absolute;{box}border:2px dashed #9AA8C0;background:rgba(140,160,200,.18);color:#7A88A6;font:600 14px Calibri;display:flex;align-items:center;justify-content:center">chart: {name}</div>')
            continue
        if tag == "cxnSp":
            continue
        sppr = el.find("p:spPr", NS)
        g = geom(sppr)
        fill = fill_of(sppr)
        ln = sppr.find("a:ln", NS) if sppr is not None else None
        lncol = clr(ln.find("a:solidFill", NS)) if ln is not None else None
        lnw = int(ln.get("w", 12700)) * PX if ln is not None else 0
        if g == "line":
            out.append(f'<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{max(w, lnw):.1f}px;height:{max(h, lnw):.1f}px;'
                       f'border-left:{lnw:.1f}px dashed {lncol or "#888"};border-top:{lnw:.1f}px dashed {lncol or "#888"}"></div>')
            continue
        rad = "border-radius:50%;" if g == "ellipse" else ("border-radius:14px;" if g == "roundRect" else "")
        border = f"box-shadow:inset 0 0 0 {lnw:.1f}px {lncol};" if lncol and fill != lncol else ""
        txb = el.find("p:txBody", NS)
        is_title = sh.is_placeholder and "TITLE" in str(sh.placeholder_format.type)
        style = f"position:absolute;{box}{rad}{border}background:{fill or 'transparent'};box-sizing:border-box;"
        if txb is None or not "".join(t.text or "" for t in txb.iter(f"{{{NS['a']}}}t")).strip():
            out.append(f'<div style="{style}"></div>')
            continue
        ins, anchor, inner = text_html(txb, title=is_title, dark=dark)
        out.append(f'<div class="tx" data-name="{name}" style="{style}padding:{ins[0]:.1f}px {ins[1]:.1f}px {ins[2]:.1f}px {ins[3]:.1f}px;'
                   f'display:flex;flex-direction:column;justify-content:{anchor};overflow:visible">'
                   f'<div class="inner" style="overflow-wrap:break-word">{inner}</div></div>')
    out.append("</div>")
    page = "<!doctype html><html><head><meta charset='utf-8'><style>body{margin:0;background:#222}</style></head><body>" + "".join(out) + "</body></html>"
    p = os.path.join(OUTD, f"slide-{idx:02d}.html")
    open(p, "w", encoding="utf-8").write(page)
    return p


CHECK = r"""(() => {
  const res = [];
  document.querySelectorAll('.tx').forEach(b => {
    const inner = b.querySelector('.inner'); const cs = getComputedStyle(b);
    const avail = b.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    const need = inner.scrollHeight, wide = inner.scrollWidth - inner.clientWidth;
    if (need > avail + 2 || wide > 2) res.push({name: b.dataset.name, over_px: Math.round(need - avail), wide_px: Math.round(wide), text: inner.innerText.slice(0, 60)});
  });
  document.querySelectorAll('.tbl').forEach(t => { const h = t.getBoundingClientRect().height, want = parseFloat(t.dataset.h);
    if (h > want + 3) res.push({name: t.dataset.name, table_grows_px: Math.round(h - want)}); });
  const sl = document.getElementById('slide').getBoundingClientRect();
  document.querySelectorAll('.tx, img, .tbl').forEach(e => { const r = e.getBoundingClientRect();
    if (e.classList.contains('tx') && (r.right > sl.right + 1 || r.bottom > sl.bottom + 1)) res.push({name: e.dataset.name, off_slide: true}); });
  return res; })()"""


async def main():
    prs = Presentation(DECK)
    deckdir = os.path.dirname(os.path.abspath(DECK))
    pages = [slide_html(s, i + 1, deckdir) for i, s in enumerate(prs.slides)]
    port = 9341
    prof = os.path.join(SP, "chrome_qa")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={prof}",
                             "--window-size=1333,750", "--hide-scrollbars", "--no-first-run", "about:blank"])
    report = {}
    try:
        for _ in range(60):
            try:
                page = next(p for p in json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list")) if p.get("type") == "page")
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=80_000_000) as ws:
            c = CDP(ws)
            await c.call("Page.enable")
            await c.call("Emulation.setDeviceMetricsOverride", width=1333, height=750, deviceScaleFactor=1, mobile=False)
            for p in pages:
                await c.call("Page.navigate", url="file:///" + p.replace("\\", "/"))
                await asyncio.sleep(1.0)
                await c.js("document.fonts.ready.then(() => true)")
                issues = await c.js(CHECK)
                n = os.path.basename(p).replace(".html", "")
                report[n] = issues
                r = await c.call("Page.captureScreenshot", format="png")
                open(os.path.join(OUTD, n + ".png"), "wb").write(base64.b64decode(r["data"]))
    finally:
        proc.terminate()
    bad = {k: [i for i in v if 'Slide Number' not in i.get('name', '')] for k, v in report.items()}
    bad = {k: v for k, v in bad.items() if v}
    print(json.dumps(bad, indent=1, ensure_ascii=False) if bad else "no text overflow found")


asyncio.run(main())
