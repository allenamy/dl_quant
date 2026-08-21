"""第三浪快装置 @5090: 数据驻显存(GPU切窗) + 期货止损 + 贪心基座(xattn+dense+apool+qh25分位).
用法: pod_fast.py [base|oi2|oix]
base=快装置重标定(无止损, 写fast_base.json) / oi2=OI独立编码器双流融合(dual-book同构) / oix=OI交互通道形式(d_oi×sign(ret))
判据: Δ vs fast_base ≥ +0.003; 期货止损: 前两折均值 < base前两折均值−0.004 即砍
设计依据: 用户令 2026-08-13 不要生硬拼接 — 同一信息三种形式对照(粗拼wave_oi/交互oix/双流oi2)
"""
import sys as _sys, os as _os, json
ARM = _sys.argv[1] if len(_sys.argv) > 1 else "base"
SEED = int(_os.environ.get("SEED", "42"))
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
assert col_of.min() >= 0, "面板币不在缓存里"
CDT = torch.from_numpy(np.ascontiguousarray(CD)).to(DEV)
ODT = None
if ARM in ("oi2", "oix"):
    OZ = zload("/workspace/data/dlnative_5m_oi4_f16.npz", allow_pickle=True)
    assert list(OZ["symbols"]) == csyms and OZ["data"].shape[0] == CD.shape[0]
    ODT = torch.from_numpy(np.ascontiguousarray(OZ["data"])).to(DEV)
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576
MS, Yv_, YRZ = [], np.full((len(anchors), N), np.nan, np.float32), np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
MS_T = [torch.from_numpy(col_of[m]).to(DEV) for m in MS]
print(f"anchors {len(anchors)} arm {ARM} seed {SEED}", flush=True)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
BTC_T = csyms.index("BTCUSDT")
def regime_ctx(i, cols_t):
    e = int(row_end[i]); s0 = e - 2016
    if s0 < 0: s0 = 0
    blk = CDT[s0:e].index_select(1, cols_t).float()
    r = torch.nan_to_num(blk[:, :, 0])
    vol7 = r.std(0)
    btcv = torch.nan_to_num(CDT[s0:e, BTC_T, 0].float()).std()
    disp = torch.nan_to_num(blk[-576:, :, 0]).sum(0).std()
    breadth = (torch.nan_to_num(blk[-288:, :, 0]).sum(0) > 0).float().mean()
    absr = r.abs().mean()
    volpct = vol7.argsort().argsort().float()/max(len(vol7)-1, 1) - 0.5
    qz = torch.nan_to_num(blk[-288:, :, 3]).mean(0)
    qz = (qz - qz.mean())/(qz.std()+1e-6)
    tbf = torch.nan_to_num(blk[-288:, :, 6]).mean(0) - 0.5
    n = blk.shape[1]
    mkt = torch.stack([btcv.expand(n), disp.expand(n), breadth.expand(n), absr.expand(n)], -1)
    own = torch.stack([torch.log1p(100*vol7), volpct, qz, tbf], -1)
    return torch.cat([mkt*100, own], -1)
def gather_t(i, cols_t):
    e = int(row_end[i]); s0 = e - W
    if s0 < 0 or e > CDT.shape[0]: return None, None
    blk = CDT[s0:e].index_select(1, cols_t).float()
    mk = torch.isfinite(blk)
    xp = torch.where(mk, blk, torch.zeros((), device=DEV))
    x = torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)
    xo = None
    if ARM == "sgn":
        r = xp[:, :, 0:1]
        sf = (2*xp[:, :, 6:7]-1)*xp[:, :, 3:4]
        xo = torch.cat([torch.clamp(r, min=0), torch.clamp(r, max=0), sf], -1).transpose(0, 1)
    if ODT is not None:
        ob = ODT[s0:e].index_select(1, cols_t).float()
        ob = torch.nan_to_num(ob)
        if ARM == "oix":
            inter = ob[:, :, 0:1] * torch.sign(xp[:, :, 0:1])
            xo = torch.cat([ob, inter], -1).transpose(0, 1)
        else:
            xo = ob.transpose(0, 1)
    return x, xo
QN = 25
class Model(nn.Module):
    def __init__(s, ch=128):
        super().__init__()
        L = []
        c = 8 + (5 if ARM == "oix" else 0) + (3 if ARM == "sgn" else 0)
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            c = ch
        s.net = nn.ModuleList(L)
        s.apq = nn.Linear(ch, 1)
        zd = ch*2
        if ARM == "oi2":
            Lo = []
            c = 4
            for d in (1, 4, 16, 64):
                Lo += [nn.Conv1d(c, 64, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, 64)]
                c = 64
            s.onet = nn.ModuleList(Lo)
            s.oproj = nn.Linear(zd + 64, zd)
        s.films = nn.ModuleList([nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2*ch)) for _ in range(8)]) if ARM == "film2" else None
        s.xa = nn.MultiheadAttention(zd, 8, batch_first=True)
        s.xln = nn.LayerNorm(zd)
        s.head = nn.Linear(zd, QN)
    def enc(s, x, net, ctx=None):
        h = x.transpose(1, 2); nb = 0
        for l in net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
            else:
                h = l(h)
                if s.films is not None and ctx is not None and isinstance(l, nn.GroupNorm):
                    fb = s.films[nb](ctx); nb += 1
                    h = h*(1 + 0.1*fb[:, :h.shape[1]].unsqueeze(-1)) + 0.1*fb[:, h.shape[1]:].unsqueeze(-1)
        return h
    def forward(s, x, xo, sizes, ctx=None):
        h = s.enc(x, s.net, ctx)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        if ARM == "oi2" and xo is not None:
            ho = s.enc(xo, s.onet)
            z = s.oproj(torch.cat([z, ho[:, :, -288:].mean(-1)], -1))
        parts = torch.split(z, sizes)
        zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
        mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
        for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
        q = s.xln(zp)
        a, _ = s.xa(q, q, q, key_padding_mask=mask)
        zp = zp + a
        z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.head(z)
QS = torch.tensor([(i+0.5)/QN for i in range(QN)], device=DEV)
FUT = None
if ARM != "base":
    try: FUT = json.load(open("/workspace/fast_base.json"))
    except Exception: FUT = None
res = {}
QDUMP = []
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    sidx = [i for i in tr1[::25] if int(row_end[i]) >= W]
    SS = torch.cat([gather_t(i, MS_T[i])[0][:, ::8, :7].reshape(-1, 7) for i in sidx])
    mu = SS.mean(0); sd = SS.std(0) + 1e-6
    omu = osd = None
    if ODT is not None or ARM == "sgn":
        SO = torch.cat([gather_t(i, MS_T[i])[1][:, ::8, :].reshape(-1, 5 if ARM == "oix" else (3 if ARM == "sgn" else 4)) for i in sidx])
        omu = SO.mean(0); osd = SO.std(0) + 1e-6
    def norm(x, xo):
        x = x.clone(); x[:, :, :7] = torch.clamp((x[:, :, :7]-mu)/sd, -5, 5)
        if xo is not None: xo = torch.clamp((xo-omu)/osd, -5, 5)
        if ARM in ("oix", "sgn") and xo is not None:
            x = torch.cat([x, xo], -1); xo = None
        return x, xo
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=8)
    best_va, best_state = -9, None
    for ep in range(8):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), 16):
            xs, xos, ys, sz, cxs = [], [], [], [], []
            for i in order[bi:bi+16]:
                m = MS[i]; okf = np.isfinite(YRZ[i, m])
                if int(row_end[i]) < W: continue
                x, xo = gather_t(i, MS_T[i])
                if x is None: continue
                okt = torch.from_numpy(okf).to(DEV)
                x, xo = norm(x, xo)
                xs.append(x[okt]); ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
                if xo is not None: xos.append(xo[okt])
                if ARM == "film2": cxs.append(regime_ctx(i, MS_T[i])[okt])
            if not xs: continue
            xb = torch.cat(xs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            xob = torch.cat(xos) if xos else None
            cb = torch.cat(cxs) if cxs else None
            o = mdl(xb, xob, sz, ctx=cb)
            d_ = yb.unsqueeze(-1) - o
            loss = torch.maximum(QS*d_, (QS-1)*d_).mean()
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                if int(row_end[i]) < W: continue
                x, xo = gather_t(i, MS_T[i])
                if x is None: continue
                x, xo = norm(x, xo)
                cb = regime_ctx(i, MS_T[i]) if ARM == 'film2' else None
                p = mdl(x, xo, [x.shape[0]], ctx=cb).mean(-1)
                v.append(spear(p.cpu().numpy(), Yv_[i, m]))
        va = float(np.nanmean(v))
        print(f"[{YV}] ep{ep} va {va:+.4f} ({time.time()-t00:.0f}s)", flush=True)
        if va > best_va: best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics = []
    SOLOP = np.full((len(anchors), N), np.nan, np.float32)
    with torch.no_grad():
        for i in te:
            m = MS[i]
            if int(row_end[i]) < W: continue
            x, xo = gather_t(i, MS_T[i])
            if x is None: continue
            x, xo = norm(x, xo)
            cb = regime_ctx(i, MS_T[i]) if ARM == 'film2' else None
            oq = mdl(x, xo, [x.shape[0]], ctx=cb).cpu().numpy()
            p = oq.mean(-1)
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
            if ARM == "base": QDUMP.append((i, m, oq))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/fast_{ARM}_s{SEED}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV]:+.4f}", flush=True)
    if ARM != "base" and FUT and YV == 2024:
        two = (res[2023] + res[2024]) / 2
        ref = (FUT["2023"] + FUT["2024"]) / 2
        if two < ref - 0.004:
            print(f"FUTILITY_STOP 前两折 {two:+.4f} vs base {ref:+.4f}", flush=True)
            print(f"快3[{ARM} s{SEED}] 判: 期货止损判负", flush=True)
            print(f"FAST_{ARM}_DONE", flush=True); _sys.exit(0)
solo = float(np.mean(list(res.values())))
if ARM == "base":
    import pickle
    pickle.dump(QDUMP, open("/workspace/exports_train/fast_base_qdump.pkl", "wb"))
    json.dump({str(k): v for k, v in res.items()} | {"mean": solo}, open("/workspace/fast_base.json", "w"))
    print(f"快3[base s{SEED}] 重标定: solo 均值 {solo:+.4f}(旧装置 qh=0.0557 对照)", flush=True)
else:
    b = FUT["mean"] if FUT else 0.0557
    d = solo - b
    print(f"快3[{ARM} s{SEED}] 判: solo 均值 {solo:+.4f} Δ vs base {d:+.4f} ⇒ " + ("录取(Δ>=+0.003)" if d >= 0.003 else "判负, 记录"), flush=True)
print(f"FAST_{ARM}_DONE", flush=True)
