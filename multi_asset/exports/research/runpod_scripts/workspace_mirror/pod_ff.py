"""终装 @5090: film2 全配(八维regime逐层FiLM) × 可微森林枝 — 第六浪首件(RESULT §4-ter 立项).
组装: 序列侧=pod_fast2 film2 本尊(TCN8块+FiLM+xattn+apool+q25); 森林侧=jp_hybrid 录取件
    (48棵×深4 oblivious 软树, 吃 feat51.npz 51特征[47实+4零垫], 残差注入+0.2辅助头).
判据: 双种子 Δ vs film2 双种子 0.0627 ≥ +0.003(s42 先行, 参照 film2 s42 0.0617); 期货止损 vs fast_base.
若 film Δ 与 forest Δ 近似正交可加, 期望落点 ~0.068 = 混合水位单模型化.
用法: pod_ff.py  env: SEED/EPOCHS=8/LR/DROP/BATCH=16/CHW=128/NTREE=48/TDEPTH=4
"""
import sys as _sys, os as _os, json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
SEED = int(_os.environ.get("SEED", "42"))
EPOCHS = int(_os.environ.get("EPOCHS", "8"))
LR = float(_os.environ.get("LR", "1e-3"))
DROP = float(_os.environ.get("DROP", "0"))
BATCH = int(_os.environ.get("BATCH", "16"))
CHW = int(_os.environ.get("CHW", "128"))
NTREE = int(_os.environ.get("NTREE", "48"))
TDEPTH = int(_os.environ.get("TDEPTH", "4"))
DEV = "cuda"
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
ts_ms = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float32)
MEM = P["MEMBER110"]; SY = [str(s) for s in P["symbols"]]
Z = zload("/workspace/data/dlnative_5m_k7_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = list(Z["symbols"])
t0c = int(CTS[0]); col_of = np.array([csyms.index(s) if s in csyms else -1 for s in SY])
assert col_of.min() >= 0
CDT = torch.from_numpy(np.ascontiguousarray(CD)).to(DEV)
FEAT = zload("/workspace/data/feat51.npz", allow_pickle=True)["feat"].astype(np.float32)
NF = FEAT.shape[-1]
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
assert FEAT.shape[0] == len(anchors), f"feat51 行数 {FEAT.shape[0]} != anchors {len(anchors)}"
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
print(f"anchors {len(anchors)} arm ff seed {SEED} NF {NF} NTREE {NTREE}", flush=True)
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
    if s0 < 0 or e > CDT.shape[0]: return None
    blk = CDT[s0:e].index_select(1, cols_t).float()
    mk = torch.isfinite(blk)
    xp = torch.where(mk, blk, torch.zeros((), device=DEV))
    return torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)
QN = 25
NLEAF = 2 ** TDEPTH
class Forest(nn.Module):
    def __init__(s):
        super().__init__()
        s.sel = nn.Parameter(torch.randn(NTREE, TDEPTH, NF) * 0.01)
        s.thr = nn.Parameter(torch.randn(NTREE, TDEPTH) * 0.5)
        s.leaf = nn.Parameter(torch.randn(NTREE, NLEAF) * 0.1)
        bits = torch.tensor([[(l >> d) & 1 for d in range(TDEPTH)] for l in range(NLEAF)], dtype=torch.float32)
        s.register_buffer("bits", bits)
    def forward(s, f):
        fx = torch.einsum("nf,tdf->ntd", f, torch.softmax(s.sel, -1))
        g = torch.sigmoid((fx - s.thr) / 0.1)
        pl = g.unsqueeze(2) * s.bits.unsqueeze(0).unsqueeze(0) + (1 - g.unsqueeze(2)) * (1 - s.bits.unsqueeze(0).unsqueeze(0))
        return (pl.prod(-1) * s.leaf.unsqueeze(0)).sum(-1)
class Model(nn.Module):
    def __init__(s, ch=CHW):
        super().__init__()
        L = []
        c = 8
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            if DROP > 0: L += [nn.Dropout(DROP)]
            c = ch
        s.net = nn.ModuleList(L)
        s.apq = nn.Linear(ch, 1)
        zd = ch*2
        s.films = nn.ModuleList([nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2*ch)) for _ in range(8)])
        s.forest = Forest()
        s.fproj = nn.Linear(NTREE, zd)
        s.faux = nn.Linear(NTREE, QN)
        s.xa = nn.MultiheadAttention(zd, 8, batch_first=True)
        s.xln = nn.LayerNorm(zd)
        s.head = nn.Linear(zd, QN)
    def enc(s, x, ctx):
        h = x.transpose(1, 2); nb = 0
        for l in s.net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
            else:
                h = l(h)
                if isinstance(l, nn.GroupNorm):
                    fb = s.films[nb](ctx); nb += 1
                    h = h*(1 + 0.1*fb[:, :h.shape[1]].unsqueeze(-1)) + 0.1*fb[:, h.shape[1]:].unsqueeze(-1)
        return h
    def forward(s, x, fz, sizes, ctx):
        h = s.enc(x, ctx)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        fo = s.forest(fz)
        z = z + 0.3 * s.fproj(fo)
        parts = torch.split(z, sizes)
        zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
        mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
        for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
        q = s.xln(zp)
        a, _ = s.xa(q, q, q, key_padding_mask=mask)
        zp = zp + a
        z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.head(z), s.faux(fo)
QS = torch.tensor([(i+0.5)/QN for i in range(QN)], device=DEV)
def pinball(o, yb):
    d_ = yb.unsqueeze(-1) - o
    return torch.maximum(QS*d_, (QS-1)*d_).mean()
try: FUT = json.load(open("/workspace/fast_base.json"))
except Exception: FUT = None
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all; cut = int(len(tr)*0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    sidx = [i for i in tr1[::25] if int(row_end[i]) >= W]
    SS = torch.cat([gather_t(i, MS_T[i])[:, ::8, :7].reshape(-1, 7) for i in sidx])
    mu = SS.mean(0); sd = SS.std(0) + 1e-6
    FS = np.concatenate([FEAT[i][MS[i]] for i in sidx])
    fmu = torch.from_numpy(np.nan_to_num(np.nanmean(FS, 0))).to(DEV).float()
    fsd = torch.from_numpy(np.nan_to_num(np.nanstd(FS, 0)) + 1e-6).to(DEV).float()
    def norm(x):
        x = x.clone(); x[:, :, :7] = torch.clamp((x[:, :, :7]-mu)/sd, -5, 5)
        return x
    def fnorm(i, mm):
        f = torch.from_numpy(np.nan_to_num(FEAT[i][mm])).to(DEV).float()
        return torch.clamp((f - fmu) / fsd, -5, 5)
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    best_va, best_state = -9, None
    for ep in range(EPOCHS):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), BATCH):
            xs, fs, ys, sz, cxs = [], [], [], [], []
            for i in order[bi:bi+BATCH]:
                m = MS[i]; okf = np.isfinite(YRZ[i, m])
                if int(row_end[i]) < W: continue
                x = gather_t(i, MS_T[i])
                if x is None: continue
                okt = torch.from_numpy(okf).to(DEV)
                xs.append(norm(x)[okt]); fs.append(fnorm(i, m[okf]))
                ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
                cxs.append(regime_ctx(i, MS_T[i])[okt])
            if not xs: continue
            xb = torch.cat(xs); fb = torch.cat(fs)
            yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            cb = torch.cat(cxs)
            o, oaux = mdl(xb, fb, sz, ctx=cb)
            loss = pinball(o, yb) + 0.2 * pinball(oaux, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                if int(row_end[i]) < W: continue
                x = gather_t(i, MS_T[i])
                if x is None: continue
                p = mdl(norm(x), fnorm(i, m), [x.shape[0]], ctx=regime_ctx(i, MS_T[i]))[0].mean(-1)
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
            x = gather_t(i, MS_T[i])
            if x is None: continue
            p = mdl(norm(x), fnorm(i, m), [x.shape[0]], ctx=regime_ctx(i, MS_T[i]))[0].cpu().numpy().mean(-1)
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/ff_s{SEED}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: solo {res[YV]:+.4f}", flush=True)
    if FUT and YV == 2024:
        two = (res[2023] + res[2024]) / 2
        ref = (FUT["2023"] + FUT["2024"]) / 2
        if two < ref - 0.004:
            print(f"FUTILITY_STOP 前两折 {two:+.4f} vs base {ref:+.4f}", flush=True)
            print(f"终装[ff s{SEED}] 判: 期货止损判负", flush=True)
            print(f"FF_DONE", flush=True); _sys.exit(0)
solo = float(np.mean(list(res.values())))
print(f"终装[ff s{SEED}] 判(口径: film2 s42 +0.0617 / film2 双种子 +0.0627; 混合水位 0.0684): "
      f"solo 均值 {solo:+.4f} Δ vs film2双种子 {solo-0.0627:+.4f} ⇒ "
      + ("过线(需双种子终审)" if solo-0.0627 >= 0.003 else "判负/待双种子"), flush=True)
print("FF_DONE", flush=True)
