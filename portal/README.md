# OcuLens-AI demo portal

A Streamlit portal over the trained anterior-eye screening pipeline.

## Run
From the project root (`D:\Capston_Project`):

```
python -m streamlit run portal/app.py
```

or just double-click **run_portal.bat**. A browser tab opens at http://localhost:8501.

## Pages
- **Home** - what the system does.
- **Screening** - upload an eye image (or tick the sample box) and run the full chain:
  quality gate -> cornea segmentation -> classification -> conformal confidence + referral ->
  Grad-CAM++ explanation -> plain-language summary.
- **Evaluation dashboard** - live test-set metrics, calibration and referral curves, subgroup fairness.
- **About** - methodology, datasets, honest scope.

## Needs
Python with `streamlit`, `torch` (CPU is fine), `timm`, `opencv-python`, `pillow` installed,
and the trained weights in `models/checkpoints/` (already present). Runs fully offline on CPU.

Research prototype - not a medical device.
