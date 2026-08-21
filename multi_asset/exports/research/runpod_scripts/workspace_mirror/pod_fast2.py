"""第三浪快装置 @5090: 数据驻显存(GPU切窗) + 期货止损 + 贪心基座(xattn+dense+apool+qh25分位).
用法: pod_fast.py [base|oi2|oix]
base=快装置重标定(无止损, 写fast_base.json) / oi2=OI独立编码器双流融合(dual-book同构) / oix=OI交互通道形式(d_oi×sign(ret))
判据: Δ vs fast_base ≥ +0.003; 期货止损: 前两折均值 < base前两折均值−0.004 即砍
设计依据: 用户令 2026-08-13 不要生硬拼接 — 同一信息三种形式对照(粗拼wave_oi/交互oix/双流oi2)
"""
import sys as _sys, os as _os, json
ARM = _sys.argv[1] if len(_sys.argv) > 1 else "base"
SEED = int(_os.environ.get("SEED", "42"))
EPOCHS = int(_os.environ.get("EPOCHS", "8"))
LR = float(_os.environ.get("LR", "1e-3"))
DROP = float(_os.environ.get("DROP", "0"))
BATCH = int(_os.environ.get("BATCH", "16"))
CHW = int(_os.environ.get("CHW", "128"))
RESD = int(_os.environ.get("RESD", "0"))
MIDX = int(_os.environ.get("MIDX", "0"))
IST = int(_os.environ.get("IST", "0"))
import time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
DEV = "cuda"
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
CHX = P["CH"].astype(np.float32) if "CH" in P.files else None
CHN = [str(c) for c in P["ch_names"]] if "ch_names" in P.files else []
SLOW_IDX = [CHN.index(c) for c in ("funding_ema", "mom_72h", "mom_168h", "rev_3h") if c in CHN]
ts_ms = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float32)
MEM = P["MEMBER110"]; SY = [str(s) for s in P["symbols"]]
Y1 = P["Y1"].astype(np.float32)
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
YRZ1 = np.full((len(anchors), N), np.nan, np.float32)
for i, r in enumerate(anchors):
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    MS.append(m); Yv_[i, m] = Y4[r, m]
    rr = rankdata(Y4[r, m]); YRZ[i, m] = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
    if ARM == "nullck":
        _rs = np.random.RandomState(777 + i)
        YRZ[i, m] = _rs.permutation(YRZ[i, m])
    if ARM == "ty1":
        ok1 = np.isfinite(Y1[r, m])
        if ok1.sum() >= 10:
            rr1 = rankdata(Y1[r, m][ok1])
            v1 = np.full(len(m), np.nan, np.float32); v1[ok1] = (rr1-(len(rr1)+1)/2)/max(len(rr1)-1, 1)
            YRZ1[i, m] = v1
MS_T = [torch.from_numpy(col_of[m]).to(DEV) for m in MS]
if ARM in ("tvol", "tmed"):
    from scipy.stats import rankdata as _rk2
    for i, r in enumerate(anchors):
        m = MS[i]
        e = int(row_end[i])
        if e < 576 or e + 48 > CD.shape[0]: 
            YRZ[i, :] = np.nan
            continue
        cols = col_of[m]
        if ARM == "tvol":
            hist = np.nan_to_num(CD[e-576:e][:, cols, 0].astype(np.float32))
            vol = hist.std(0) + 1e-4
            yv = Y4[r, m] / vol
        else:
            fut = np.nan_to_num(CD[e:e+48][:, cols, 0].astype(np.float32))
            segs = fut.reshape(4, 12, -1).sum(1)
            yv = np.median(segs, 0)
        ok = np.isfinite(yv)
        out = np.full(len(m), np.nan, np.float32)
        if ok.sum() >= 10:
            rr2 = _rk2(yv[ok]); out[ok] = (rr2-(len(rr2)+1)/2)/max(len(rr2)-1, 1)
        YRZ[i, m] = out
print(f"anchors {len(anchors)} arm {ARM} seed {SEED}", flush=True)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
BTC_T = csyms.index("BTCUSDT")
FEAT = None
if ARM == "femb":
    FEAT = zload("/workspace/data/feat51.npz", allow_pickle=True)["feat"].astype(np.float32)
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
    out8 = torch.cat([mkt*100, own], -1)
    if ARM == "relf":
        e2 = int(row_end[i]); s2 = max(0, e2 - 288)
        rw = torch.nan_to_num(CDT[s2:e2].index_select(1, cols_t)[:, :, 0].float())
        mk2 = rw.mean(1, keepdim=True)
        rc = rw - rw.mean(0, keepdim=True); mc = mk2 - mk2.mean(0, keepdim=True)
        sd_r = rc.std(0) + 1e-6; sd_m = mc.std(0) + 1e-6
        corr = (rc*mc).mean(0)/(sd_r*sd_m.squeeze())
        beta = (rc*mc).mean(0)/(sd_m.squeeze()**2)
        ll = (rc[1:]*mc[:-1]).mean(0)/(sd_r*sd_m.squeeze()) - (rc[:-1]*mc[1:]).mean(0)/(sd_r*sd_m.squeeze())
        h1 = rw[:144]; h2 = rw[144:]
        c1 = ((h1-h1.mean(0))* (h1.mean(1, keepdim=True)-h1.mean())).mean(0)/((h1.std(0)+1e-6)*(h1.mean(1).std()+1e-6))
        c2 = ((h2-h2.mean(0))* (h2.mean(1, keepdim=True)-h2.mean())).mean(0)/((h2.std(0)+1e-6)*(h2.mean(1).std()+1e-6))
        inst = (c1 - c2).abs()
        rel = torch.stack([corr, torch.clamp(beta, -3, 3), ll*10, inst, corr.argsort().argsort().float()/max(len(corr)-1, 1) - 0.5], -1)
        return torch.cat([out8, torch.nan_to_num(rel)], -1)
    if ARM == "ctxk" and CHX is not None and SLOW_IDX:
        import numpy as _np
        slow = torch.from_numpy(_np.nan_to_num(_np.clip(CHX[anchors[i]][MS[i]][:, SLOW_IDX], -5, 5))).float().to(out8.device)
        if slow.shape[1] < 4:
            slow = torch.cat([slow, torch.zeros(slow.shape[0], 4-slow.shape[1], device=out8.device)], -1)
        return torch.cat([out8, slow], -1)
    return out8
def gather_t(i, cols_t):
    e = int(row_end[i]); s0 = e - W
    if s0 < 0 or e > CDT.shape[0]: return None, None
    blk = CDT[s0:e].index_select(1, cols_t).float()
    mk = torch.isfinite(blk)
    xp = torch.where(mk, blk, torch.zeros((), device=DEV))
    x = torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)
    xo = None
    if ARM in ("sgn", "sf"):
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
    def __init__(s, ch=CHW):
        super().__init__()
        L = []
        c = 8 + (5 if ARM == "oix" else 0) + (3 if ARM in ("sgn", "sf") else 0)
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            if DROP > 0: L += [nn.Dropout(DROP)]
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
        s.films = nn.ModuleList([nn.Sequential(nn.Linear(12 if ARM == "ctxk" else (13 if ARM == "relf" else 8), 32), nn.GELU(), nn.Linear(32, 2*ch)) for _ in range(8)]) if ARM in ("film2", "sf", "ctxk", "nullck", "tvol", "tmed", "relf", "femb") else None
        s.tattn = nn.MultiheadAttention(ch, 4, batch_first=True) if ARM == "hyb" else None
        s.protW = nn.Parameter(torch.randn(zd, 4)*0.02) if ARM == "proto" else None
        s.pattn = nn.MultiheadAttention(zd, 4, batch_first=True) if ARM == "proto" else None
        s.gate = nn.Linear(8, 3) if ARM == "moe" else None
        s.experts = nn.ModuleList([nn.Sequential(nn.Linear(zd, zd), nn.GELU(), nn.Linear(zd, zd)) for _ in range(3)]) if ARM == "moe" else None
        s.femb_emb = nn.Embedding(51*16, 32) if ARM == "femb" else None
        s.f_attn1 = nn.MultiheadAttention(32, 4, batch_first=True) if ARM == "femb" else None
        s.f_attn2 = nn.MultiheadAttention(32, 4, batch_first=True) if ARM == "femb" else None
        s.f_ln1 = nn.LayerNorm(32) if ARM == "femb" else None
        s.f_ln2 = nn.LayerNorm(32) if ARM == "femb" else None
        s.f_proj = nn.Linear(64, zd) if ARM == "femb" else None
        s.mxa = nn.MultiheadAttention(ch, 4, batch_first=True) if (MIDX or IST) else None
        s.mxln = nn.LayerNorm(ch) if (MIDX or IST) else None
        s.xa = nn.MultiheadAttention(zd, 8, batch_first=True)
        s.xln = nn.LayerNorm(zd)
        s.head = nn.Linear(zd, QN)
    def enc(s, x, net, ctx=None, sizes=None):
        h = x.transpose(1, 2); nb = 0; ng = 0
        for l in net:
            if isinstance(l, nn.Conv1d):
                h_in = h
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
            else:
                h = l(h)
                if isinstance(l, nn.GroupNorm):
                    ng += 1
                    if RESD and h.shape == h_in.shape: h = h + h_in
                    if s.films is not None and ctx is not None:
                        fb = s.films[nb](ctx); nb += 1
                        h = h*(1 + 0.1*fb[:, :h.shape[1]].unsqueeze(-1)) + 0.1*fb[:, h.shape[1]:].unsqueeze(-1)
                    if s.tattn is not None and ng == 5:
                        t = h[:, :, ::8].transpose(1, 2)
                        L = t.shape[1]
                        am = torch.triu(torch.ones(L, L, dtype=torch.bool, device=h.device), 1)
                        at, _ = s.tattn(t, t, t, attn_mask=am)
                        up = torch.repeat_interleave(at.transpose(1, 2), 8, dim=2)[:, :, :h.shape[2]]
                        h = h + 0.3*up
                    if s.mxa is not None and (IST or ng == 4) and sizes is not None:
                        hv = h.mean(-1)
                        parts = torch.split(hv, sizes)
                        hp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
                        km = torch.ones(hp.shape[:2], dtype=torch.bool, device=h.device)
                        for gi, n_ in enumerate(sizes): km[gi, :n_] = False
                        qm = s.mxln(hp)
                        am2, _ = s.mxa(qm, qm, qm, key_padding_mask=km)
                        av = torch.cat([am2[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
                        h = h + 0.2*av.unsqueeze(-1)
        return h
    def forward(s, x, xo, sizes, ctx=None, fids=None):
        h = s.enc(x, s.net, ctx, sizes)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        if ARM == "oi2" and xo is not None:
            ho = s.enc(xo, s.onet)
            z = s.oproj(torch.cat([z, ho[:, :, -288:].mean(-1)], -1))
        if getattr(s, 'femb_emb', None) is not None and fids is not None:
            t = s.femb_emb(fids)
            a1, _ = s.f_attn1(s.f_ln1(t), s.f_ln1(t), s.f_ln1(t)); t = t + a1
            a2, _ = s.f_attn2(s.f_ln2(t), s.f_ln2(t), s.f_ln2(t)); t = t + a2
            fr = torch.cat([t.mean(1), t.max(1).values], -1)
            z = z + 0.3*s.f_proj(fr)
        if s.protW is not None:
            outs = []
            for zg in torch.split(z, sizes):
                A = torch.softmax((zg @ s.protW)/16.0, dim=0)
                Pk = (A.transpose(0, 1) @ zg).unsqueeze(0)
                at, _ = s.pattn(s.xln(zg).unsqueeze(0), Pk, Pk)
                outs.append(zg + at.squeeze(0))
            z = torch.cat(outs, 0)
        else:
            parts = torch.split(z, sizes)
            zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
            mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
            for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
            q = s.xln(zp)
            a, _ = s.xa(q, q, q, key_padding_mask=mask)
            zp = zp + a
            z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        if s.gate is not None and ctx is not None:
            g = torch.softmax(s.gate(ctx), -1)
            z = z + sum(g[:, e:e+1]*s.experts[e](z) for e in range(3))
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
    EDGES = None
    if ARM == "femb":
        samp_f = np.concatenate([FEAT[i][MS[i]] for i in tr1[::10]])
        EDGES = np.stack([np.nanquantile(samp_f[:, j], np.linspace(0, 1, 17)[1:-1]) for j in range(51)])
    def fid_of(i, mm):
        fv = np.nan_to_num(FEAT[i][mm])
        ids = np.stack([np.searchsorted(EDGES[j], fv[:, j]) for j in range(51)], -1)
        return torch.from_numpy((ids + np.arange(51)*16).astype(np.int64)).to(DEV)
    omu = osd = None
    if ODT is not None or ARM in ("sgn", "sf"):
        SO = torch.cat([gather_t(i, MS_T[i])[1][:, ::8, :].reshape(-1, 5 if ARM == "oix" else (3 if ARM in ("sgn", "sf") else 4)) for i in sidx])
        omu = SO.mean(0); osd = SO.std(0) + 1e-6
    def norm(x, xo):
        x = x.clone(); x[:, :, :7] = torch.clamp((x[:, :, :7]-mu)/sd, -5, 5)
        if xo is not None: xo = torch.clamp((xo-omu)/osd, -5, 5)
        if ARM in ("oix", "sgn", "sf") and xo is not None:
            x = torch.cat([x, xo], -1); xo = None
        return x, xo
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    best_va, best_state = -9, None
    for ep in range(EPOCHS):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), BATCH):
            xs, xos, ys, sz, cxs, fidl = [], [], [], [], [], []
            for i in order[bi:bi+BATCH]:
                m = MS[i]; okf = np.isfinite(YRZ1[i, m]) if ARM == "ty1" else np.isfinite(YRZ[i, m])
                if int(row_end[i]) < W: continue
                x, xo = gather_t(i, MS_T[i])
                if x is None: continue
                okt = torch.from_numpy(okf).to(DEV)
                x, xo = norm(x, xo)
                xs.append(x[okt]); ys.append((YRZ1 if ARM == "ty1" else YRZ)[i, m[okf]]); sz.append(int(okf.sum()))
                if ARM == "femb": fidl.append(fid_of(i, m[okf]))
                if xo is not None: xos.append(xo[okt])
                if ARM in ("film2", "moe", "sf", "ctxk", "nullck", "tvol", "tmed", "relf", "femb"): cxs.append(regime_ctx(i, MS_T[i])[okt])
            if not xs: continue
            xb = torch.cat(xs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            xob = torch.cat(xos) if xos else None
            cb = torch.cat(cxs) if cxs else None
            fb = torch.cat(fidl) if fidl else None
            o = mdl(xb, xob, sz, ctx=cb, fids=fb)
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
                cb = regime_ctx(i, MS_T[i]) if ARM in ('film2', 'moe', 'sf', 'ctxk', 'nullck', 'tvol', 'tmed', 'relf', 'femb') else None
                p = mdl(x, xo, [x.shape[0]], ctx=cb, fids=fid_of(i, m) if ARM == 'femb' else None).mean(-1)
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
            cb = regime_ctx(i, MS_T[i]) if ARM in ('film2', 'moe', 'sf', 'ctxk') else None
            oq = mdl(x, xo, [x.shape[0]], ctx=cb, fids=fid_of(i, m) if ARM == 'femb' else None).cpu().numpy()
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
