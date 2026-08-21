"""B批2 @5090 (SURVEY §1-bis 自家栈受据武器): 单一开关=单一假设。
用法: pod_arm2.py [xattn|film|huber|dcnv2|base]
受据: xattn=EngineA xsec注意力+0.031 / film=单资产REG_arch RG-FiLM / huber=v5冠军损失 / dcnv2=用户点名特征交叉
判据: Δ vs base(+0.0320, d0b.log 2026-08-12) >= +0.003 录取
"""
import sys as _sys
ARM = _sys.argv[1] if len(_sys.argv) > 1 else "seed2027"
BASE_SOLO = 0.0320
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
K = zload("/workspace/harness_y4_pred_panel.npz", allow_pickle=True)
KP = K[list(K.keys())[0]].astype(np.float32) if len(K.files) == 1 else K["king_pred"].astype(np.float32)
Z = zload("/workspace/data/dlnative_5m_k7_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = list(Z["symbols"])
t0c = int(CTS[0]); col_of = np.array([csyms.index(s) if s in csyms else -1 for s in SY])
BTC_COL = csyms.index("BTCUSDT")
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576; CW = 2016
MS, Yv_, YRZ, KH = [], np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
    KH[i, m] = KP[r, m] if KP.shape == Y4.shape else np.nan
print(f"anchors {len(anchors)} arm {ARM}", flush=True)
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
    def __init__(s, cin=8, ch=128):
        super().__init__()
        L = []
        c = cin
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            c = ch
        s.net = nn.ModuleList(L); s.head = nn.Linear(ch*3, 1)
        s.xa = nn.MultiheadAttention(ch*3, 8, batch_first=True) if ARM == "xattn" else None
        s.xln = nn.LayerNorm(ch*3) if ARM == "xattn" else None
        s.film = nn.Sequential(nn.Linear(3, 64), nn.GELU(), nn.Linear(64, 2*ch)) if ARM == "film" else None
        s.cross = nn.ModuleList([nn.Linear(ch*3, ch*3) for _ in range(2)]) if ARM == "dcnv2" else None
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
        z = torch.cat([h[:, :, -72:].mean(-1), h[:, :, -288:].mean(-1), h[:, :, -1]], -1)
        if s.cross is not None:
            z0 = z; zz = z
            for cw in s.cross: zz = z0 * cw(zz) + zz
            z = zz
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
    _sd = 2027 if ARM == "seed2027" else 42
    torch.manual_seed(_sd); np.random.seed(_sd)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all if ARM == "dense" else tr_all[::2]; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    samp = [gather(i, MS[i]) for i in tr1[::25]]
    S = np.concatenate([s_[:, ::8, :7] for s_ in samp if s_ is not None])
    mu = S.mean((0, 1)); sd = S.std((0, 1)) + 1e-6
    cmu = csd = None
    if ARM == "film":
        sampc = [gather_ctx(i, MS[i]) for i in tr1[::25]]
        SC = np.concatenate([c_ for c_ in sampc if c_ is not None])
        cmu = SC.mean(0); csd = SC.std(0) + 1e-6
    def norm(g):
        g = g.copy(); g[:, :, :7] = np.clip((g[:, :, :7]-mu)/sd, -5, 5); return g
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
                if ARM == "film":
                    c_ = gather_ctx(i, m[ok])
                    if c_ is None: continue
                    cs.append(c_)
                xs.append(norm(g)); ys.append(YRZ[i, m[ok]]); sz.append(int(ok.sum()))
            if not xs: continue
            xb = torch.from_numpy(np.concatenate(xs)).to(DEV)
            yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            cb = torch.from_numpy(normc(np.concatenate(cs))).to(DEV) if cs else None
            pred = mdl(xb, ctx=cb, sizes=sz if ARM == "xattn" else None)
            loss = nn.functional.huber_loss(pred, yb, delta=0.3) if ARM == "huber" else nn.functional.mse_loss(pred, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]; g = gather(i, m)
                if g is None: continue
                cb = None
                if ARM == "film":
                    c_ = gather_ctx(i, m)
                    if c_ is None: continue
                    cb = torch.from_numpy(normc(c_)).to(DEV)
                p = mdl(torch.from_numpy(norm(g)).to(DEV), ctx=cb, sizes=[g.shape[0]] if ARM == "xattn" else None)
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
            if ARM == "film":
                c_ = gather_ctx(i, m)
                if c_ is None: continue
                cb = torch.from_numpy(normc(c_)).to(DEV)
            p = mdl(torch.from_numpy(norm(g)).to(DEV), ctx=cb, sizes=[g.shape[0]] if ARM == "xattn" else None).cpu().numpy()
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/arm3_{ARM}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV]:+.4f}", flush=True)
solo = float(np.mean(list(res.values())))
d = solo - BASE_SOLO
print(f"", flush=True)
print(f"臂3[{ARM}] 判: solo 均值 {solo:+.4f} Δ vs base {d:+.4f} ⇒ " + ("录取(Δ>=+0.003)" if d >= 0.003 else "判负, 记录"), flush=True)
print(f"ARM3_{ARM}_DONE", flush=True)
