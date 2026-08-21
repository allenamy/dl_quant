"""第二浪 @5090: 骨干/损失/目标/特征 扫描。基座=xda(xattn+dense+apool, 无film), 单变量。
用法: pod_wave.py [ptst|itr|mtcn|qh|pw|aux|xrk]
判据: Δ vs xda s42(+0.0516) >= +0.003 录取; 同种子42
受据: mtcn=单资产冠军骨干 / qh=EngineA QIM 25分位领先2x / xrk=本栈母语是秩
"""
import sys as _sys
ARM = _sys.argv[1] if len(_sys.argv) > 1 else "qh"
BASE = 0.0516
import time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
DEV = "cuda"
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
ts_ms = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float32)
Y8 = P["Y8"].astype(np.float32); Y24 = P["Y24"].astype(np.float32)
MEM = P["MEMBER110"]; SY = [str(s) for s in P["symbols"]]
Z = zload("/workspace/data/dlnative_5m_k7_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = list(Z["symbols"])
t0c = int(CTS[0]); col_of = np.array([csyms.index(s) if s in csyms else -1 for s in SY])
OD = None
if ARM == "oi":
    OZ = zload("/workspace/data/dlnative_5m_oi4_f16.npz", allow_pickle=True)
    assert list(OZ["symbols"]) == csyms and OZ["data"].shape[0] == CD.shape[0], "OI 网格不齐"
    OD = OZ["data"]
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576
NCH = 8 + (7 if ARM == "xrk" else 0) + (4 if ARM == "oi" else 0)
def rz(v, m):
    out = np.full(v.shape, np.nan, np.float32)
    ok = np.isfinite(v[m])
    if ok.sum() >= 10:
        rr = rankdata(v[m][ok]); out_m = np.full(m.shape, np.nan, np.float32)
        out_m[ok] = (rr-(len(rr)+1)/2)/max(len(rr)-1, 1)
        out[m] = out_m
    return out
MS = []; Yv_ = np.full((len(anchors), N), np.nan, np.float32)
YRZ = np.full((len(anchors), N), np.nan, np.float32)
YRZ8 = np.full((len(anchors), N), np.nan, np.float32)
YRZ24 = np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
    if ARM == "aux":
        YRZ8[i] = rz(Y8[r], m); YRZ24[i] = rz(Y24[r], m)
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
    if ARM == "xrk":
        v = np.where(mk, blk, np.nan)
        order = np.argsort(np.nan_to_num(v, nan=1e9), axis=0)
        rk = np.empty_like(order); n_ = v.shape[0]
        ar = np.arange(n_)[:, None, None]
        np.put_along_axis(rk, order, np.broadcast_to(ar, v.shape).copy(), axis=0)
        rkf = rk.astype(np.float32)/max(n_-1, 1) - 0.5
        out[ok, :, 8:15] = np.where(mk, rkf, 0.0)
    if ARM == "oi":
        ob = OD[s0:e][:, cols[ok], :].astype(np.float32)
        out[ok, :, 8:12] = np.nan_to_num(np.transpose(ob, (1, 0, 2)))
    return out
class Backbone(nn.Module):
    def __init__(s, cin=NCH, ch=128):
        super().__init__()
        s.kind = ARM if ARM in ("ptst", "itr", "mtcn") else "tcn"
        if s.kind == "tcn":
            L = []
            c = cin
            for d in (1, 2, 4, 8, 16, 32, 64, 128):
                L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
                c = ch
            s.net = nn.ModuleList(L)
        elif s.kind == "mtcn":
            s.stem = nn.Conv1d(cin, ch, 1)
            s.blocks = nn.ModuleList()
            for _ in range(6):
                s.blocks.append(nn.ModuleList([nn.Conv1d(ch, ch, 51, groups=ch), nn.GroupNorm(8, ch),
                                               nn.Conv1d(ch, 2*ch, 1), nn.Conv1d(2*ch, ch, 1)]))
        elif s.kind == "ptst":
            s.proj = nn.Linear(16*cin, ch)
            s.pos = nn.Parameter(torch.zeros(36, ch))
            enc = nn.TransformerEncoderLayer(ch, 8, 256, batch_first=True, norm_first=True, activation="gelu")
            s.enc = nn.TransformerEncoder(enc, 4)
        elif s.kind == "itr":
            s.proj = nn.Linear(W, ch)
            enc = nn.TransformerEncoderLayer(ch, 8, 256, batch_first=True, norm_first=True, activation="gelu")
            s.enc = nn.TransformerEncoder(enc, 2)
        s.apq = nn.Linear(ch, 1)
    def forward(s, x):
        if s.kind == "tcn":
            h = x.transpose(1, 2)
            for l in s.net:
                if isinstance(l, nn.Conv1d):
                    h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
                else: h = l(h)
        elif s.kind == "mtcn":
            h = s.stem(x.transpose(1, 2))
            for dw, gn, up, dn in s.blocks:
                r = h
                h = nn.functional.pad(h, (50, 0)); h = dw(h); h = gn(nn.functional.gelu(h))
                h = dn(nn.functional.gelu(up(h))) + r
        elif s.kind == "ptst":
            B = x.shape[0]
            t = s.proj(x.reshape(B, 36, -1)) + s.pos
            t = s.enc(t)
            return torch.cat([t.mean(1), t[:, -1]], -1)
        elif s.kind == "itr":
            t = s.proj(x.transpose(1, 2))
            t = s.enc(t)
            return torch.cat([t.mean(1), t.max(1).values], -1)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        return torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
QN = 25
QS = torch.tensor([(i+0.5)/QN for i in range(QN)])
class Model(nn.Module):
    def __init__(s):
        super().__init__()
        s.bb = Backbone()
        zd = 256
        s.xa = nn.MultiheadAttention(zd, 8, batch_first=True)
        s.xln = nn.LayerNorm(zd)
        odim = QN if ARM == "qh" else (3 if ARM == "aux" else 1)
        s.head = nn.Linear(zd, odim)
    def forward(s, x, sizes):
        z = s.bb(x)
        parts = torch.split(z, sizes)
        zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
        mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
        for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
        q = s.xln(zp)
        a, _ = s.xa(q, q, q, key_padding_mask=mask)
        zp = zp + a
        z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.head(z)
def score_of(o):
    if ARM == "qh": return o.mean(-1)
    if ARM == "aux": return o[:, 0]
    return o.squeeze(-1)
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(42); np.random.seed(42)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    samp = [gather(i, MS[i]) for i in tr1[::25]]
    sampv = [s_ for s_ in samp if s_ is not None]
    S = np.concatenate([s_[:, ::8, :7] for s_ in sampv])
    mu = S.mean((0, 1)); sd = S.std((0, 1)) + 1e-6
    omu = osd = None
    if ARM == "oi":
        SO = np.concatenate([s_[:, ::8, 8:12] for s_ in sampv])
        omu = SO.mean((0, 1)); osd = SO.std((0, 1)) + 1e-6
    def norm(g):
        g = g.copy(); g[:, :, :7] = np.clip((g[:, :, :7]-mu)/sd, -5, 5)
        if ARM == "oi": g[:, :, 8:12] = np.clip((g[:, :, 8:12]-omu)/osd, -5, 5)
        return g
    mdl = Model().to(DEV)
    qs_dev = QS.to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=8)
    best_va, best_state = -9, None
    for ep in range(8):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), 16):
            xs, ys, y8s, y24s, sz = [], [], [], [], []
            for i in order[bi:bi+16]:
                m = MS[i]; ok = np.isfinite(YRZ[i, m])
                g = gather(i, m[ok])
                if g is None: continue
                xs.append(norm(g)); ys.append(YRZ[i, m[ok]]); sz.append(int(ok.sum()))
                if ARM == "aux":
                    y8s.append(YRZ8[i, m[ok]]); y24s.append(YRZ24[i, m[ok]])
            if not xs: continue
            xb = torch.from_numpy(np.concatenate(xs)).to(DEV)
            yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            o = mdl(xb, sz)
            if ARM == "qh":
                d_ = yb.unsqueeze(-1) - o
                loss = torch.maximum(qs_dev*d_, (qs_dev-1)*d_).mean()
            elif ARM == "aux":
                loss = nn.functional.mse_loss(o[:, 0], yb)
                for k_, yt in ((1, y8s), (2, y24s)):
                    t_ = torch.from_numpy(np.concatenate(yt)).to(DEV)
                    fin = torch.isfinite(t_)
                    if fin.any(): loss = loss + 0.3*nn.functional.mse_loss(o[fin, k_], t_[fin])
            elif ARM == "pw":
                s_ = o.squeeze(-1)
                loss = nn.functional.mse_loss(s_, yb)
                off = 0; ph = []
                for n_ in sz:
                    ys_ = yb[off:off+n_]; ss_ = s_[off:off+n_]
                    k_ = max(3, n_//5)
                    idx = torch.argsort(ys_)
                    bot, top = idx[:k_], idx[-k_:]
                    ph.append(torch.relu(0.2 - (ss_[top].unsqueeze(1) - ss_[bot].unsqueeze(0))).mean())
                    off += n_
                loss = loss + 0.5*torch.stack(ph).mean()
            else:
                loss = nn.functional.mse_loss(score_of(o), yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]; g = gather(i, m)
                if g is None: continue
                p = score_of(mdl(torch.from_numpy(norm(g)).to(DEV), [g.shape[0]]))
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
            p = score_of(mdl(torch.from_numpy(norm(g)).to(DEV), [g.shape[0]])).cpu().numpy()
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/wave_{ARM}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV]:+.4f}", flush=True)
solo = float(np.mean(list(res.values())))
d = solo - BASE
print(f"", flush=True)
print(f"浪2[{ARM}] 判: solo 均值 {solo:+.4f} Δ vs xda {d:+.4f} ⇒ " + ("录取(Δ>=+0.003)" if d >= 0.003 else "判负, 记录"), flush=True)
print(f"WAVE_{ARM}_DONE", flush=True)
