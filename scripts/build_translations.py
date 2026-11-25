"""Pre-translate the assistant's fixed English texts into Hindi, Kannada, Tamil and Telugu.

Run once (needs internet):  python scripts/build_translations.py [--nllb]
(--nllb: translate on this computer with Meta NLLB-200; the model, about 2.5 GB, downloads once.)
Output: src/oculens/assistant/translations.json, used offline at run time.

Only fixed educational text is sent to the translation service (FAQ answers, condition notes, patient-portal
content and interface labels): never patient data. The translations are machine-made (Google Translate via
deep-translator) and should be reviewed by native speakers before real clinical use.
"""
from __future__ import annotations

import json
import ssl
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "src" / "oculens" / "assistant" / "translations.json"
LANGS = ["hi", "kn", "ta", "te"]
KEEP = ["OcuLens-AI", "OcuLens", "REFER", "U-Net", "EfficientNet-B0", "Grad-CAM"]   # names kept in English


def lines_of(texts):
    seen, out = set(), []
    for t in texts:
        for line in t.split("\n"):
            b = line.strip()
            if b.startswith("- "):
                b = b[2:]
            if b and b not in seen:
                seen.add(b)
                out.append(b)
    return out


def protect(s):
    for i, k in enumerate(KEEP):
        s = s.replace(k, f"[[{i}]]")
    return s


def restore(s):
    for i, k in enumerate(KEEP):
        for v in (f"[[{i}]]", f"[[ {i} ]]", f"[ [{i}] ]", f"[[{i}] ]", f"[ [{i}]]"):
            s = s.replace(v, k)
    return s


def translate_all(lines, lang, done):
    from deep_translator import GoogleTranslator
    gt = GoogleTranslator(source="en", target=lang)
    todo = [x for x in lines if x not in done]
    batch, size = [], 0
    def flush(b):
        if not b:
            return
        joined = "\n".join(protect(x) for x in b)
        for attempt in range(3):
            try:
                res = gt.translate(joined).split("\n")
                break
            except Exception as e:  # noqa: BLE001
                print("  retry", attempt, e); time.sleep(3)
        else:
            return
        if len(res) == len(b):
            for en, t in zip(b, res):
                done[en] = restore(t.strip())
        else:   # the service merged or split lines: translate one by one
            for en in b:
                try:
                    done[en] = restore(gt.translate(protect(en)).strip())
                except Exception as e:  # noqa: BLE001
                    print("  skip", en[:40], e)
    for x in todo:
        if size + len(x) > 3500:
            flush(batch); batch, size = [], 0
        batch.append(x); size += len(x) + 1
    flush(batch)


NLLB = {"hi": "hin_Deva", "kn": "kan_Knda", "ta": "tam_Taml", "te": "tel_Telu"}
_NLLB_MODEL = "facebook/nllb-200-distilled-600M"


def translate_nllb(lines, lang, done, batch=16):
    """Offline translation with Meta's NLLB-200 (distilled 600M) on the CPU, used when the online service is
    unavailable. Lines are translated one sentence group at a time; names are restored afterwards."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    global _tok, _mdl
    if "_mdl" not in globals():
        _tok = AutoTokenizer.from_pretrained(_NLLB_MODEL, src_lang="eng_Latn")
        _mdl = AutoModelForSeq2SeqLM.from_pretrained(_NLLB_MODEL).eval()
    import os
    torch.set_num_threads(os.cpu_count() or 4)
    todo = sorted((x for x in lines if x not in done), key=len)      # similar lengths batch with little padding
    tgt = _tok.convert_tokens_to_ids(NLLB[lang])
    t0 = time.time()
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        enc = _tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=300)
        cap = int(enc["input_ids"].shape[1] * 2.2) + 12                 # Indic scripts need more tokens than English
        with torch.inference_mode():
            out = _mdl.generate(**enc, forced_bos_token_id=tgt, max_new_tokens=cap, num_beams=1,
                                no_repeat_ngram_size=4)
        for en, t in zip(chunk, _tok.batch_decode(out, skip_special_tokens=True)):
            for k in KEEP:                      # NLLB sometimes transliterates product names: put them back
                if k in en and k not in t:
                    t = t.replace(k.lower(), k)
            done[en] = t.strip()
        if i % (batch * 4) == 0:
            print(f"  {lang} {i + len(chunk)}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)


def ui_strings():
    """Every literal passed to T(...) in the patient portal (implicit string concatenation included)."""
    import ast
    tree = ast.parse((ROOT / "portal" / "patient_portal.py").read_text(encoding="utf-8"))
    out = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "T" and n.args
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            out.append(n.args[0].value)
    sys.path.insert(0, str(ROOT / "portal"))
    import patient_portal as pp                       # texts kept in lists and passed to T() through a variable
    out += list(pp.VT_LABELS.values()) + pp.BRING + pp.BRING_VIDEO
    return out


def main():
    try:
        import truststore
        truststore.inject_into_ssl()      # use the operating system's certificate store
    except Exception:  # noqa: BLE001
        pass
    from oculens.assistant import chat
    from oculens.assistant.faq import FAQ
    from oculens.assistant import patient_content as pc
    from oculens.assistant import i18n
    texts = chat.static_texts() + pc.all_strings() + ui_strings()
    phrasings = [p for qs, _, _ in FAQ for p in qs[:2]]      # so questions asked in these languages match too
    lines = lines_of(texts + phrasings)
    table = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for lang in LANGS:
        done = table.setdefault(lang, {})
        before = len(done)
        if "--nllb" in sys.argv:
            translate_nllb(lines, lang, done)
        else:
            translate_all(lines, lang, done)
        OUT.write_text(json.dumps(table, ensure_ascii=False, indent=0), encoding="utf-8")   # save as we go
        print(lang, "lines:", len(done), f"(+{len(done) - before})")
    table["_phrasings"] = phrasings
    table["_note"] = ("Machine translation (" + ("Meta NLLB-200 distilled 600M, offline" if "--nllb" in sys.argv
                      else "Google Translate via deep-translator") + "); review by native speakers pending.")
    OUT.write_text(json.dumps(table, ensure_ascii=False, indent=0), encoding="utf-8")
    i18n._TR_CACHE = None
    print("wrote", OUT)


if __name__ == "__main__":
    main()
