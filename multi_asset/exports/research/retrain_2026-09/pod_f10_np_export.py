"""f10 np 导出 + 门V1(np≡torch)@pod(2026-09-01, PREREG addendum §A V1):
ckpt(f.0/f.3/f.6)→ npz{w0,b0,w1,b1,w2,b2,mu,sd_,alpha,n_cols,trained_through}(= 生产 f10_live_s42_np.npz 形态);
门V1: 真实特征行 30,000 条, torch(eval) vs np(gelu=erf 精确, 服务同式)打分 — 中位 Spearman ≥0.99999 且 maxabs ≤1e-5。
用法: SEED=42 python3 pod_f10_np_export.py(对 models/f10_live_s{SEED}.pt)
"""
import os, sys, time
import numpy as np
import torch, torch.nn as nn
from scipy.stats import spearmanr
from scipy.special import erf

SEED = int(os.environ.get("SEED", "42"))
OUT = os.environ.get("F10_OUT", "/workspace/f8_ext")
DLW = os.environ.get("F10_DLW", "/workspace/dlw_ext")
CK = f"{OUT}/models/f10_live_s{SEED}.pt"
ck = torch.load(CK, map_location="cpu", weights_only=False)
sd = ck["state_dict"]
mu = ck["mu"].numpy().astype(np.float64); sdv = ck["sd"].numpy().astype(np.float64)
alpha = float(ck["alpha"])
W = {"w0": sd["f.0.weight"].numpy(), "b0": sd["f.0.bias"].numpy(),
     "w1": sd["f.3.weight"].numpy(), "b1": sd["f.3.bias"].numpy(),
     "w2": sd["f.6.weight"].numpy(), "b2": sd["f.6.bias"].numpy()}
assert W["w0"].shape == (256, 171) and W["w2"].shape == (1, 256), {k: v.shape for k, v in W.items()}

TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
trained_through = int(TG["E_ts"].astype(np.int64).max())

# ---- 门V1: 真实行双实现打分 ----
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
rng = np.random.default_rng(0)
sel = rng.choice(FE["X"].shape[0], 30000, replace=False)
XL = np.concatenate([FE["X"][sel].astype(np.float32), F9["X"][sel].astype(np.float32)], 1)
xz = np.nan_to_num(np.clip((XL - mu) / sdv, -5, 5)).astype(np.float64)

def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
h = gelu(xz @ W["w0"].T.astype(np.float64) + W["b0"].astype(np.float64))
h = gelu(h @ W["w1"].T.astype(np.float64) + W["b1"].astype(np.float64))
s_np = (h @ W["w2"].T.astype(np.float64) + W["b2"].astype(np.float64)).squeeze(-1)

class Net(nn.Module):
    def __init__(s, d=171, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
    def forward(s, x): return s.f(x).squeeze(-1)
net = Net()
net.load_state_dict({k: v for k, v in sd.items() if k.startswith("f.")}, strict=False)
net.eval()
with torch.no_grad():
    s_t = net(torch.from_numpy(xz.astype(np.float32))).numpy().astype(np.float64)
rho = spearmanr(s_np, s_t).correlation
mx = float(np.abs(s_np - s_t).max())
print(f"V1 s{SEED}: spearman {rho:.7f} maxabs {mx:.2e} (判据 >=0.99999, <=1e-5)", flush=True)
ok = rho >= 0.99999 and mx <= 1e-5
np.savez(f"{OUT}/models/f10_live_s{SEED}_np.npz", **W, mu=mu.astype(np.float32), sd_=sdv.astype(np.float32),
         alpha=np.float32(alpha), n_cols=np.int64(171), trained_through=np.int64(trained_through))
print(f"V1_{'PASS' if ok else 'FAIL'} s{SEED} -> f10_live_s{SEED}_np.npz trained_through {trained_through}", flush=True)
sys.exit(0 if ok else 3)
