"""Stage 4: sliding windows -> VAE encoder-decoder -> GRU temporal learning -> temporal attention + position awareness -> risk head."""
import math
import numpy as np
import torch
import torch.nn as nn

T = 8  # sliding-window length (current transaction + the 7 before it, in time order)

def _positional_encoding(steps, dim):
    pe, pos = torch.zeros(steps, dim), torch.arange(steps).unsqueeze(1)
    div = torch.exp(torch.arange(0, dim, 2) * (-math.log(10000.0) / dim))
    pe[:, 0::2], pe[:, 1::2] = torch.sin(pos * div), torch.cos(pos * div)
    return pe

class VAEGRU(nn.Module):
    def __init__(self, d=9, latent=6, hidden=16):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d, 16), nn.ReLU())                      # VAE encoder
        self.mu, self.lv = nn.Linear(16, latent), nn.Linear(16, latent)
        self.dec = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, d), nn.Sigmoid())  # VAE decoder
        self.gru = nn.GRU(latent, hidden, batch_first=True)                        # GRU temporal learning
        self.att = nn.Linear(hidden, 1)                                            # temporal attention
        self.head = nn.Sequential(nn.Linear(hidden, 8), nn.ReLU(), nn.Linear(8, 1), nn.Sigmoid())
        self.register_buffer("pe", _positional_encoding(T, hidden))                # position awareness

    def forward(self, x):                                                          # x: (batch, T, features)
        e = self.enc(x)
        mu, lv = self.mu(e), self.lv(e).clamp(-6, 4)
        z = mu + torch.randn_like(mu) * torch.exp(.5 * lv) if self.training else mu
        out, _ = self.gru(z)
        w = torch.softmax(self.att(out + self.pe).squeeze(-1), dim=1)
        ctx = ((out + self.pe) * w.unsqueeze(-1)).sum(1)
        return self.head(ctx).squeeze(-1), self.dec(z), mu, lv, w

def train(X, win, target, epochs=25, seed=7, max_rows=20000, beta=.05):
    """Loss = reconstruction + beta*KL (VAE) + risk-head error against the weak/real labels."""
    torch.manual_seed(seed)
    sel = torch.tensor(np.random.default_rng(seed).permutation(len(X))[:max_rows])
    Xt, Wt, Tt = torch.tensor(X, dtype=torch.float32), torch.tensor(win), torch.tensor(target, dtype=torch.float32)
    model = VAEGRU()
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=.5, patience=2)
    for _ in range(epochs):
        model.train()
        total = 0.0
        for b in sel[torch.randperm(len(sel))].split(256):
            xb = Xt[Wt[b]]
            head, rec, mu, lv, _ = model(xb)
            kl = -.5 * torch.mean(1 + lv - mu ** 2 - lv.exp())
            loss = nn.functional.mse_loss(rec, xb) + beta * kl + nn.functional.mse_loss(head, Tt[b])
            opt.zero_grad(); loss.backward(); opt.step()
            total += loss.item() * len(b)
        sched.step(total / len(sel))
    return model.eval()

def score_windows(model, xb):
    """xb: (m, T, features) numpy -> (risk head output, reconstruction error of the last transaction)."""
    with torch.no_grad():
        x = torch.tensor(xb, dtype=torch.float32)
        head, rec, _, _, w = model(x)
        err = ((rec[:, -1] - x[:, -1]) ** 2).mean(1)
    return head.numpy().astype(float), err.numpy().astype(float), w.numpy()

def predict(model, X, win, batch=4096):
    parts = [score_windows(model, X[win[i:i + batch]]) for i in range(0, len(win), batch)]
    return tuple(np.concatenate(p) for p in zip(*parts))
