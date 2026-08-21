"""批3 @5090: 基座=xattn(录取臂, +0.0384), 贪心叠加。
用法: pod_arm4.py [xf|prem|apool]
xf=xattn+film叠加性 / prem=+premium3通道(L1-a信息层) / apool=注意力池化
判据: Δ vs xf(+0.0384) >= +0.003 录取
"""
import sys as _sys
ARM = _sys.argv[1] if len(_sys.argv) > 1 else "xfd"
import os as _os
SEED = int(_os.environ.get("SEED", "42"))
BASE_X = 0.0448
FILM_ON = "f" in ARM; PREM_ON = "p" in ARM; APOOL_ON = "a" in ARM; XATTN_ON = "x" in ARM
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
Z = zload("/workspace/data/dlnative_5m_k7_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = list(Z["symbols"])
t0c = int(CTS[0]); col_of = np.array([csyms.index(s) if s in csyms else -1 for s in SY])
BTC_COL = csyms.index("BTCUSDT")
PD = None
if PREM_ON:
    PZ = zload("/workspace/data/dlnative_5m_prem3_f16.npz", allow_pickle=True)
    assert int(PZ["ts"][0]) == int(CTS[0]) and PZ["data"].shape[0] == CD.shape[0], "prem 网格与 klines 不齐"
    assert list(PZ["symbols"]) == csyms, "prem 符号序不齐"
    PD = PZ["data"]
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576; CW = 2016
NCH = 8 + (3 if PREM_ON else 0)
MS, Yv_, YRZ = [], np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
print(f"anchors {len(anchors)} arm {ARM} nch {NCH}", flush=True)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
def gather(i, names):
    e = int(row_end[i]); s0 = e - W
    if s0 < 0 or e > CD.shape[0]: return None
    cols = col_of[names]; ok = cols >= 0
    out = np.zeros((len(names), W, NCH), np.float32)
    blk = CD[s0:e][:, cols[ok], :].astype(np.float32)
    blk = np.transpose(blk, (1, 0, 2))
    mk = np.isfinite(blk)
    out[ok, :, :7] = np.where(mk, blk, 0.0); out[ok, :, 7] = mk.all(-1)
    if PREM_ON:
        pb = PD[s0:e][:, cols[ok], :].astype(np.float32)
        pb = np.transpose(pb, (1, 0, 2))
        out[ok, :, 8:11] = np.nan_to_num(pb)
    return out
def gather_ctx(i, names):
    e = int(row_end[i]); s0 = e - CW
    if s0 < 0 or e > CD.shape[0]: return None
    cols = col_of[names]; ok = cols >= 0
    blk = CD[s0:e][:, cols[ok], :].astype(np.float32)
    vol7 = np.nanstd(blk[:, :, 0], axis=0)
    qv7 = np.nanmean(blk[:, :, 3], axis=0)
    btc = np.nanstd(CD[s0:e, BTC_COL, 0].astype(np.float32))
    out = np.zeros((len(names), 3), np.float32)
    out[ok, 0] = np.log1p(100*np.nan_to_num(vol7))
    out[ok, 1] = np.nan_to_num(qv7)
    out[:, 2] = np.log1p(100*np.nan_to_num(btc))
    return out
class TCN(nn.Module):
    def __init__(s, cin=NCH, ch=128):
        super().__init__()
        L = []
        c = cin
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            c = ch
        zdim = ch*2 if APOOL_ON else ch*3
        s.net = nn.ModuleList(L); s.head = nn.Linear(zdim, 1)
        s.xa = nn.MultiheadAttention(zdim, 8, batch_first=True) if XATTN_ON else None
        s.xln = nn.LayerNorm(zdim) if XATTN_ON else None
        s.film = nn.Sequential(nn.Linear(3, 64), nn.GELU(), nn.Linear(64, 2*ch)) if FILM_ON else None
        s.apq = nn.Linear(ch, 1) if APOOL_ON else None
    def forward(s, x, ctx=None, sizes=None):
        h = x.transpose(1, 2); nconv = 0
        for l in s.net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h); nconv += 1
            else:
                h = l(h)
                if s.film is not None and ctx is not None and nconv == 4 and isinstance(l, nn.GroupNorm):
                    fb = s.film(ctx); g_, b_ = fb[:, :128], fb[:, 128:]
                    h = h*(1 + g_.unsqueeze(-1)) + b_.unsqueeze(-1)
        if APOOL_ON:
            hs = h[:, :, -288:]
            w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
            zp_ = (hs * w_.unsqueeze(1)).sum(-1)
            z = torch.cat([zp_, h[:, :, -1]], -1)
        else:
            z = torch.cat([h[:, :, -72:].mean(-1), h[:, :, -288:].mean(-1), h[:, :, -1]], -1)
        if s.xa is not None and sizes is not None:
            parts = torch.split(z, sizes)
            zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
            mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
            for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
            q = s.xln(zp)
            a, _ = s.xa(q, q, q, key_padding_mask=mask)
            zp = zp + a
            z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.head(z).squeeze(-1)
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    samp = [gather(i, MS[i]) for i in tr1[::25]]
    sampv = [s_ for s_ in samp if s_ is not None]
    S = np.concatenate([s_[:, ::8, :7] for s_ in sampv])
    mu = S.mean((0, 1)); sd = S.std((0, 1)) + 1e-6
    pmu = psd = None
    if PREM_ON:
        SP = np.concatenate([s_[:, ::8, 8:11] for s_ in sampv])
        pmu = SP.mean((0, 1)); psd = SP.std((0, 1)) + 1e-6
    cmu = csd = None
    if FILM_ON:
        sampc = [gather_ctx(i, MS[i]) for i in tr1[::25]]
        SC = np.concatenate([c_ for c_ in sampc if c_ is not None])
        cmu = SC.mean(0); csd = SC.std(0) + 1e-6
    def norm(g):
        g = g.copy(); g[:, :, :7] = np.clip((g[:, :, :7]-mu)/sd, -5, 5)
        if PREM_ON: g[:, :, 8:11] = np.clip((g[:, :, 8:11]-pmu)/psd, -5, 5)
        return g
    def normc(c): return np.clip((c-cmu)/csd, -5, 5).astype(np.float32)
    mdl = TCN().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=8)
    best_va, best_state = -9, None
    for ep in range(8):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), 16):
            xs, ys, cs, sz = [], [], [], []
            for i in order[bi:bi+16]:
                m = MS[i]; ok = np.isfinite(YRZ[i, m])
                g = gather(i, m[ok])
                if g is None: continue
                if FILM_ON:
                    c_ = gather_ctx(i, m[ok])
                    if c_ is None: continue
                    cs.append(c_)
                xs.append(norm(g)); ys.append(YRZ[i, m[ok]]); sz.append(int(ok.sum()))
            if not xs: continue
            xb = torch.from_numpy(np.concatenate(xs)).to(DEV)
            yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            cb = torch.from_numpy(normc(np.concatenate(cs))).to(DEV) if cs else None
            pred = mdl(xb, ctx=cb, sizes=sz if XATTN_ON else None)
            loss = nn.functional.mse_loss(pred, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]; g = gather(i, m)
                if g is None: continue
                cb = None
                if FILM_ON:
                    c_ = gather_ctx(i, m)
                    if c_ is None: continue
                    cb = torch.from_numpy(normc(c_)).to(DEV)
                p = mdl(torch.from_numpy(norm(g)).to(DEV), ctx=cb, sizes=[g.shape[0]])
                v.append(spear(p.cpu().numpy(), Yv_[i, m]))
        va = float(np.nanmean(v))
        print(f"[{YV}] ep{ep} va {va:+.4f} ({time.time()-t00:.0f}s)", flush=True)
        if va > best_va: best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics = []
    SOLOP = np.full((len(anchors), N), np.nan, np.float32)
    with torch.no_grad():
        for i in te:
            m = MS[i]; g = gather(i, m)
            if g is None: continue
            cb = None
            if FILM_ON:
                c_ = gather_ctx(i, m)
                if c_ is None: continue
                cb = torch.from_numpy(normc(c_)).to(DEV)
            p = mdl(torch.from_numpy(norm(g)).to(DEV), ctx=cb, sizes=[g.shape[0]]).cpu().numpy()
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/arm5_{ARM}_s{SEED}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV]:+.4f}", flush=True)
solo = float(np.mean(list(res.values())))
d = solo - BASE_X
print(f"", flush=True)
print(f"臂5[{ARM} s{SEED}] 判: solo 均值 {solo:+.4f} Δ vs xf {d:+.4f} ⇒ " + ("录取(Δ>=+0.003)" if d >= 0.003 else "判负, 记录"), flush=True)
print(f"ARM5_{ARM}_DONE", flush=True)
