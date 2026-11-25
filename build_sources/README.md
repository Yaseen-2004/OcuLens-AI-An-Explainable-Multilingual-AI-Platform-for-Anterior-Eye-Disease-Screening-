# Build sources (copied out of the temporary session folder)

- `report/` builds `OcuLens-AI_Step_Log_and_Pre-Implementation_Guide.pdf`: `python report/make_pdf.py`
  (make_pdf.py loads the extra_*.py parts and worklog.json from its own folder).
- `deck/build_final.js` builds the final presentation (v2, 24 slides); `deck/build.js` the older 16-slide deck.
  Needs Node with pptxgenjs, react, react-dom, react-icons, sharp and jszip: `NODE_PATH=<node_modules> node deck/build_final.js out.pptx`.
- `deck/qa_render.py` is the Chrome-based layout check (`python deck/qa_render.py deck.pptx`).
