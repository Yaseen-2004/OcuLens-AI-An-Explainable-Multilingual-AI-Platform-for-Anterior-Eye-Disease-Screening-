"""CycleGAN-style translator between two image domains (e.g. camera A <-> camera B, hospital A <-> B).

Used for cross-device harmonisation (revised RQ2). Generators are ResNet-style; discriminators
are 70x70 PatchGANs; losses are least-squares GAN + cycle consistency + identity.
"""
from __future__ import annotations

import itertools

import torch
from torch import nn
import torch.nn.functional as F


class _Res(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.b = nn.Sequential(nn.ReflectionPad2d(1), nn.Conv2d(c, c, 3), nn.InstanceNorm2d(c), nn.ReLU(True),
                               nn.ReflectionPad2d(1), nn.Conv2d(c, c, 3), nn.InstanceNorm2d(c))

    def forward(self, x):
        return x + self.b(x)


class Generator(nn.Module):
    def __init__(self, base: int = 64, n_res: int = 6):
        super().__init__()
        layers = [nn.ReflectionPad2d(3), nn.Conv2d(3, base, 7), nn.InstanceNorm2d(base), nn.ReLU(True)]
        c = base
        for _ in range(2):
            layers += [nn.Conv2d(c, c * 2, 3, stride=2, padding=1), nn.InstanceNorm2d(c * 2), nn.ReLU(True)]
            c *= 2
        layers += [_Res(c) for _ in range(n_res)]
        for _ in range(2):
            layers += [nn.ConvTranspose2d(c, c // 2, 3, stride=2, padding=1, output_padding=1),
                       nn.InstanceNorm2d(c // 2), nn.ReLU(True)]
            c //= 2
        layers += [nn.ReflectionPad2d(3), nn.Conv2d(c, 3, 7), nn.Tanh()]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class PatchDiscriminator(nn.Module):
    def __init__(self, base: int = 64):
        super().__init__()
        def blk(cin, cout, norm=True, stride=2):
            return [nn.Conv2d(cin, cout, 4, stride, 1)] + ([nn.InstanceNorm2d(cout)] if norm else []) + [nn.LeakyReLU(0.2, True)]
        self.net = nn.Sequential(*blk(3, base, norm=False), *blk(base, base * 2), *blk(base * 2, base * 4),
                                 *blk(base * 4, base * 8, stride=1), nn.Conv2d(base * 8, 1, 4, 1, 1))

    def forward(self, x):
        return self.net(x)


class CycleGAN:
    def __init__(self, device: str = "cpu", lr: float = 2e-4, lambda_cyc: float = 10.0, lambda_id: float = 5.0, base: int = 64):
        self.G_ab, self.G_ba = Generator(base).to(device), Generator(base).to(device)
        self.D_a, self.D_b = PatchDiscriminator(base).to(device), PatchDiscriminator(base).to(device)
        self.opt_g = torch.optim.Adam(itertools.chain(self.G_ab.parameters(), self.G_ba.parameters()), lr, betas=(0.5, 0.999))
        self.opt_d = torch.optim.Adam(itertools.chain(self.D_a.parameters(), self.D_b.parameters()), lr, betas=(0.5, 0.999))
        self.lc, self.li = lambda_cyc, lambda_id

    @staticmethod
    def _gan(pred, real: bool):
        return F.mse_loss(pred, torch.ones_like(pred) if real else torch.zeros_like(pred))

    def train_step(self, a: torch.Tensor, b: torch.Tensor) -> dict:
        """a, b: unpaired batches in [-1, 1] from domain A and domain B."""
        fake_b, fake_a = self.G_ab(a), self.G_ba(b)
        loss_g = (self._gan(self.D_b(fake_b), True) + self._gan(self.D_a(fake_a), True)
                  + self.lc * (F.l1_loss(self.G_ba(fake_b), a) + F.l1_loss(self.G_ab(fake_a), b))
                  + self.li * (F.l1_loss(self.G_ab(b), b) + F.l1_loss(self.G_ba(a), a)))
        self.opt_g.zero_grad()
        loss_g.backward()
        self.opt_g.step()
        loss_d = 0.5 * (self._gan(self.D_b(b), True) + self._gan(self.D_b(fake_b.detach()), False)
                        + self._gan(self.D_a(a), True) + self._gan(self.D_a(fake_a.detach()), False))
        self.opt_d.zero_grad()
        loss_d.backward()
        self.opt_d.step()
        return {"loss_g": loss_g.item(), "loss_d": loss_d.item()}
