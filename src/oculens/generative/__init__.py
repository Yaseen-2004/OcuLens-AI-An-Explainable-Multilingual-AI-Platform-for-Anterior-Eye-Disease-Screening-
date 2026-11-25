"""Generative models (Step 3). Used only at training time - never on a patient's image.

ddpm.py      class-conditional denoising diffusion model for rare-class synthesis
cyclegan.py  CycleGAN-style translator for cross-device / cross-hospital harmonisation
validate.py  FID on backbone features and TSTR (train on synthetic, test on real)
"""
