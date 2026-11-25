"""Class-conditional DDPM (Ho et al. 2020) with classifier-free guidance.

Small enough to train at 64-128 px on one GPU slice. Generated images go to data/synthetic/
and may only ever be added to a TRAINING split.
"""
from __future__ import annotations

import math

import torch
from torch import nn
import torch.nn.functional as F


def timestep_embedding(t: torch.Tensor, dim: int) -> torch.Tensor:
    half = dim // 2
    freqs = torch.exp(-math.log(10000) * torch.arange(half, device=t.device) / half)
    args = t.float()[:, None] * freqs[None]
    return torch.cat([args.sin(), args.cos()], dim=1)


class ResBlock(nn.Module):
    def __init__(self, cin: int, cout: int, emb_dim: int):
        super().__init__()
        self.n1, self.c1 = nn.GroupNorm(8, cin), nn.Conv2d(cin, cout, 3, padding=1)
        self.emb = nn.Linear(emb_dim, cout)
        self.n2, self.c2 = nn.GroupNorm(8, cout), nn.Conv2d(cout, cout, 3, padding=1)
        self.skip = nn.Conv2d(cin, cout, 1) if cin != cout else nn.Identity()

    def forward(self, x, emb):
        h = self.c1(F.silu(self.n1(x)))
        h = h + self.emb(emb)[:, :, None, None]
        h = self.c2(F.silu(self.n2(h)))
        return h + self.skip(x)


class CondUNet(nn.Module):
    """Noise predictor eps(x_t, t, y). Class index num_classes means 'unconditional'."""

    def __init__(self, num_classes: int, base: int = 64, mults=(1, 2, 2, 4), img_ch: int = 3):
        super().__init__()
        self.num_classes = num_classes
        emb_dim = base * 4
        self.t_mlp = nn.Sequential(nn.Linear(base, emb_dim), nn.SiLU(), nn.Linear(emb_dim, emb_dim))
        self.y_emb = nn.Embedding(num_classes + 1, emb_dim)
        self.base = base
        self.inp = nn.Conv2d(img_ch, base, 3, padding=1)
        chs = [base * m for m in mults]
        self.downs, self.ups = nn.ModuleList(), nn.ModuleList()
        prev = base
        for c in chs:
            self.downs.append(nn.ModuleList([ResBlock(prev, c, emb_dim), nn.Conv2d(c, c, 3, stride=2, padding=1)]))
            prev = c
        self.mid = ResBlock(prev, prev, emb_dim)
        for c in reversed(chs):
            self.ups.append(nn.ModuleList([nn.ConvTranspose2d(prev, c, 4, stride=2, padding=1), ResBlock(c * 2, c, emb_dim)]))
            prev = c
        self.out = nn.Sequential(nn.GroupNorm(8, prev), nn.SiLU(), nn.Conv2d(prev, img_ch, 3, padding=1))

    def forward(self, x, t, y):
        emb = self.t_mlp(timestep_embedding(t, self.base)) + self.y_emb(y)
        h = self.inp(x)
        skips = []
        for block, down in self.downs:
            h = block(h, emb)
            skips.append(h)
            h = down(h)
        h = self.mid(h, emb)
        for up, block in self.ups:
            h = up(h)
            h = block(torch.cat([h, skips.pop()], 1), emb)
        return self.out(h)


class Diffusion:
    def __init__(self, model: CondUNet, timesteps: int = 1000, device: str = "cpu"):
        self.model, self.T, self.device = model, timesteps, device
        self.betas = torch.linspace(1e-4, 0.02, timesteps, device=device)
        self.alphas = 1 - self.betas
        self.abar = torch.cumprod(self.alphas, 0)

    def loss(self, x0: torch.Tensor, y: torch.Tensor, p_uncond: float = 0.1) -> torch.Tensor:
        """x0 in [-1, 1]. Randomly drops the label so the model also learns unconditional generation."""
        b = x0.shape[0]
        t = torch.randint(0, self.T, (b,), device=x0.device)
        noise = torch.randn_like(x0)
        ab = self.abar[t][:, None, None, None]
        xt = ab.sqrt() * x0 + (1 - ab).sqrt() * noise
        y = torch.where(torch.rand(b, device=x0.device) < p_uncond, torch.full_like(y, self.model.num_classes), y)
        return F.mse_loss(self.model(xt, t, y), noise)

    @torch.no_grad()
    def sample(self, y: torch.Tensor, size: int, guidance: float = 2.0, steps: int | None = None) -> torch.Tensor:
        """Ancestral sampling with classifier-free guidance. Returns images in [-1, 1]."""
        self.model.eval()
        b = y.shape[0]
        x = torch.randn(b, 3, size, size, device=self.device)
        uncond = torch.full_like(y, self.model.num_classes)
        ts = list(range(self.T))[::-1] if steps is None else torch.linspace(self.T - 1, 0, steps).long().tolist()
        for i, t in enumerate(ts):
            tt = torch.full((b,), t, device=self.device, dtype=torch.long)
            e_c, e_u = self.model(x, tt, y), self.model(x, tt, uncond)
            eps = e_u + guidance * (e_c - e_u)
            ab = self.abar[t]
            ab_prev = self.abar[ts[i + 1]] if i + 1 < len(ts) else torch.tensor(1.0, device=self.device)
            x0 = ((x - (1 - ab).sqrt() * eps) / ab.sqrt()).clamp(-1, 1)
            if i + 1 < len(ts):
                # DDIM-style deterministic step when skipping timesteps, plus a little noise (eta=0.5)
                sigma = 0.5 * ((1 - ab_prev) / (1 - ab) * (1 - ab / ab_prev)).clamp(min=0).sqrt()
                dir_xt = (1 - ab_prev - sigma ** 2).clamp(min=0).sqrt() * eps
                x = ab_prev.sqrt() * x0 + dir_xt + sigma * torch.randn_like(x)
            else:
                x = x0
        return x
