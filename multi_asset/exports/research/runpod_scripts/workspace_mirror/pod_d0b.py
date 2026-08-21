"""D0b @5090 (CAMPAIGN e099415e): 放大版 5m-solo — 128ch TCN 双尺度池化 8 轮。
pod 原生: 直读 pm32_hz 面板 + k7_f16 缓存(7通道+mask=8入); king 参照读 harness_y4_pred_panel。
门: solo ≥0.04 = 融合上限算术进入 +16% 区; ≥0.02 维持强先验。"""
import time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
DEV = "cuda"
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
ts_ms = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float32)
MEM = P["MEMBER110"]; SY = [str(s) for s in P["symbols"]]
assert int(ts_ms[0]) == 1609459200000, f"面板起点非2021-01-01: {ts_ms[0]}"
K = zload("/workspace/harness_y4_pred_panel.npz", allow_pickle=True)
KP = K[list(K.keys())[0]].astype(np.float32) if len(K.files) == 1 else K["king_pred"].astype(np.float32)
Z = zload("/workspace/data/dlnative_5m_k7_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = list(Z["symbols"])
t0c = int(CTS[0]); col_of = np.array([csyms.index(s) if s in csyms else -1 for s in SY])
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576
MS, Yv_, YRZ, KH = [], np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
    KH[i, m] = KP[r, m] if KP.shape == Y4.shape else np.nan
print(f"anchors {len(anchors)} years {sorted(set(yrs))}", flush=True)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
def gather(i, names):
    e = int(row_end[i]); s0 = e - W
    if s0 < 0 or e > CD.shape[0]: return None
    cols = col_of[names]; ok = cols >= 0
    out = np.zeros((len(names), W, 8), np.float32)
    blk = CD[s0:e][:, cols[ok], :].astype(np.float32)
    blk = np.transpose(blk, (1, 0, 2))
    mk = np.isfinite(blk)
    out[ok, :, :7] = np.where(mk, blk, 0.0); out[ok, :, 7] = mk.all(-1)
    return out
class TCN(nn.Module):
    def __init__(s, cin=8, ch=128):
        super().__init__()
        L = []
        c = cin
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            c = ch
        s.net = nn.ModuleList(L); s.head = nn.Linear(ch*3, 1)
    def forward(s, x):
        h = x.transpose(1, 2)
        for l in s.net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
            else: h = l(h)
        z = torch.cat([h[:, :, -72:].mean(-1), h[:, :, -288:].mean(-1), h[:, :, -1]], -1)
        return s.head(z).squeeze(-1)
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(42); np.random.seed(42)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all[::2]; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    samp = [gather(i, MS[i]) for i in tr1[::25]]
    S = np.concatenate([s_[:, ::8, :7] for s_ in samp if s_ is not None])
    mu = S.mean((0, 1)); sd = S.std((0, 1)) + 1e-6
    def norm(g):
        g = g.copy(); g[:, :, :7] = np.clip((g[:, :, :7]-mu)/sd, -5, 5); return g
    mdl = TCN().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=8)
    best_va, best_state = -9, None
    for ep in range(8):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), 16):
            xs, ys = [], []
            for i in order[bi:bi+16]:
                m = MS[i]; ok = np.isfinite(YRZ[i, m])
                g = gather(i, m[ok])
                if g is None: continue
                xs.append(norm(g)); ys.append(YRZ[i, m[ok]])
            if not xs: continue
            xb = torch.from_numpy(np.concatenate(xs)).to(DEV)
            yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            loss = nn.functional.mse_loss(mdl(xb), yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]; g = gather(i, m)
                if g is None: continue
                v.append(spear(mdl(torch.from_numpy(norm(g)).to(DEV)).cpu().numpy(), Yv_[i, m]))
        va = float(np.nanmean(v))
        print(f"[{YV}] ep{ep} va {va:+.4f} ({time.time()-t00:.0f}s)", flush=True)
        if va > best_va: best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics = []; kics = []
    SOLOP = np.full((len(anchors), N), np.nan, np.float32)
    with torch.no_grad():
        for i in te:
            m = MS[i]; g = gather(i, m)
            if g is None: continue
            p = mdl(torch.from_numpy(norm(g)).to(DEV)).cpu().numpy()
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m])); kics.append(spear(KH[i, m], Yv_[i, m]))
    res[YV] = (float(np.nanmean(tics)), float(np.nanmean(kics)))
    np.save(f"/workspace/exports_train/d0b_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV][0]:+.4f} king {res[YV][1]:+.4f}", flush=True)
solo = np.mean([v[0] for v in res.values()])
print(f"\nD0b 判: solo 均值 {solo:+.4f} ⇒ " + ("★≥0.04 融合上限入+16%区" if solo >= 0.04 else "≥0.02 强先验维持" if solo >= 0.02 else "回落, 记录"), flush=True)
print("D0B_DONE", flush=True)
