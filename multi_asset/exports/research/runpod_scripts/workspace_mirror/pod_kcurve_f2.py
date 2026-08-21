"""F2 森林×film2 宽版: F1 融合架构 + 可微森林枝(64树×深4, 吃82特征)投影入头 — 110录取冠军形态的宽书版.
判据 DESIGN §7: 固定锚 vs LGBM82 0.0690 门+0.003 双种子 + 层书贡献为正.
判据 DESIGN §7: 固定锚 vs LGBM82 0.0690 门+0.003 双种子; 且层书回放贡献为正(总策略底线).
上一场 pod_wide 回答的是训练侧加宽(NTOP300 不抬 mem110, 判负); 本装置回答不同问题:
    一个宽训练的 king 在 serve-K∈{110,200,250,300,400} 嵌套子集(逐锚量能 top-K)上的 rank-IC 曲线.
判据冻结: DESIGN_wide_book_v1_2026-08-15 §3.4 (IC 曲线 + IC×√K + Q4 最坏五分位 + 成本后净额另判).
臂: ① NTOP=400 SEED=42(主) ② NTOP=110 SEED=42(训练宽度对照) ③ NTOP=400 SEED=2027(种子2).
产物: kcurveF2_pred_K{NTOP}_s{SEED}_{YV}.npy + kcurveF2_meta_K{NTOP}_s{SEED}.npz(锚ts/成员/量能) + json.
幸存者约束沿袭 pod_wide(成员要求 y4 有数), 与代理 K 曲线同限制, DESIGN §1.1 已声明.
用法: pod_kcurve.py  (env: SEED/EPOCHS=8/LR/DROP/BATCH=4/CHW=128/NTOP=400/RESD=0/MIDX=0)
"""
import sys as _sys, os as _os, json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
ARM = "film2"
SEED = int(_os.environ.get("SEED", "42"))
EPOCHS = int(_os.environ.get("EPOCHS", "8"))
LR = float(_os.environ.get("LR", "1e-3"))
DROP = float(_os.environ.get("DROP", "0"))
BATCH = int(_os.environ.get("BATCH", "4"))
CHW = int(_os.environ.get("CHW", "128"))
NTOP = int(_os.environ.get("NTOP", "400"))
RESD = int(_os.environ.get("RESD", "0"))
MIDX = int(_os.environ.get("MIDX", "0"))
SERVE_KS = (110, 200, 250, 300, 400)
DEV = "cuda"
W = 576; FWD = 48; TRAIL = 2016
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = [str(s) for s in Z["symbols"]]
NW = len(csyms); TT = CD.shape[0]
BTC_T = csyms.index("BTCUSDT")
# ---- 滚动统计: 前置零行 cumsum, CS[b]-CS[a] = 行[a,b)之和 ----
r5 = CD[:, :, 0].astype(np.float32)
fin = np.isfinite(r5)
r5z = np.where(fin, r5, 0).astype(np.float32)
qvz = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], 0).astype(np.float32)
z1 = np.zeros((1, NW))
CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
CS_r = np.concatenate([z1, np.cumsum(r5z, 0, dtype=np.float64)])
CS_r2 = np.concatenate([z1, np.cumsum(r5z * r5z, 0, dtype=np.float64)])
CS_q = np.concatenate([z1, np.cumsum(qvz, 0, dtype=np.float64)])
del r5, r5z, qvz, fin
grid = np.where(CTS % 14400 == 0)[0]
grid = grid[(grid >= W) & (grid + FWD <= TT)]
E = grid
S = np.maximum(E - TRAIL, 0)
nfin = np.maximum(CS_f[E] - CS_f[S], 1)
covr = (CS_f[E] - CS_f[S]) / np.maximum(E - S, 1)[:, None]
qvm = (CS_q[E] - CS_q[S]) / nfin
rs_ = CS_r[E] - CS_r[S]
vstd = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S]) / nfin - (rs_ / nfin) ** 2, 0))
y4n = CS_f[E + FWD] - CS_f[E]
y4full = (CS_r[E + FWD] - CS_r[E]).astype(np.float32)
y4full[y4n < FWD - 2] = np.nan
del CS_f, CS_r, CS_r2, CS_q, rs_
MS, keep = [], []
for i in range(len(E)):
    ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4full[i])
    m = np.where(ok)[0]
    if len(m) > NTOP:
        m = np.sort(m[np.argsort(-qvm[i, m])[:NTOP]])
    if len(m) >= 50:
        MS.append(m); keep.append(i)
keep = np.array(keep)
E = E[keep]; y4full = y4full[keep]
qvk = qvm[keep].astype(np.float32)   # K曲线新增: 逐锚量能, serve-K 嵌套子集的排序键
yrs = np.array([time.gmtime(int(t)).tm_year for t in CTS[E]])
Yv_ = np.full((len(E), NW), np.nan, np.float32)
YRZ = np.full((len(E), NW), np.nan, np.float32)
for i in range(len(E)):
    m = MS[i]
    Yv_[i, m] = y4full[i, m]
    rr = rankdata(y4full[i, m])
    YRZ[i, m] = (rr - (len(m) + 1) / 2) / max(len(m) - 1, 1)
FEA82 = np.load("/workspace/data/wide_fea_v1.npy")
FM = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
f_ts = FM["E_ts"].astype(np.int64)
frow_map = {int(t): j for j, t in enumerate(f_ts)}
FROW = np.array([frow_map.get(int(CTS[e]), -1) for e in E])
NF82 = FEA82.shape[2]
MS_T = [torch.from_numpy(m).to(DEV) for m in MS]
CDT = torch.from_numpy(np.ascontiguousarray(CD)).to(DEV)
print(f"anchors {len(E)} kcurve film2 seed {SEED} NTOP {NTOP} 平均成员 {np.mean([len(m) for m in MS]):.0f}", flush=True)
# ---- 面板桥: 对齐自检(沿袭 pod_wide, mem110 口径保留作参照) ----
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
pts = P["ts"].astype(np.int64); PY4 = P["Y4"].astype(np.float32)
PMEM = P["MEMBER110"]; PSY = [str(s) for s in P["symbols"]]
pwall = pts // 1000 + 3600
wall2prow = {int(w): j for j, w in enumerate(pwall)}
pcol = np.array([csyms.index(s) if s in csyms else -1 for s in PSY])
del P
M110 = []
n_hit = 0
for i in range(len(E)):
    j = wall2prow.get(int(CTS[E[i]]))
    if j is None:
        M110.append(np.array([], dtype=np.int64)); continue
    sel = np.where(PMEM[j] & np.isfinite(PY4[j]) & (pcol >= 0))[0]
    cols = pcol[sel]
    pos = np.searchsorted(MS[i], cols)
    okp = (pos < len(MS[i])) & (MS[i][np.minimum(pos, len(MS[i]) - 1)] == cols)
    M110.append(pos[okp]); n_hit += 1
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
chk = {-1: [], 0: [], 1: []}
for i in range(60, len(E) - 60, max(len(E) // 200, 1)):
    j = wall2prow.get(int(CTS[E[i]]))
    if j is None: continue
    sel = np.where(PMEM[j] & np.isfinite(PY4[j]) & (pcol >= 0))[0]
    if len(sel) < 30: continue
    for off in (-1, 0, 1):
        chk[off].append(spear(y4full[i + off][pcol[sel]], PY4[j, sel]))
c0, cm, cp = (float(np.nanmedian(chk[o])) for o in (0, -1, 1))
print(f"对齐自检 corr@0 {c0:+.3f} vs @-1 {cm:+.3f} @+1 {cp:+.3f} (n={len(chk[0])}, mem110可评锚 {n_hit}/{len(E)})", flush=True)
assert c0 > cm and c0 > cp and c0 > 0.8, "对齐自检 FAIL: 自算y4 与面板 Y4 未在 0 偏移对齐"
# ---- 以下 regime/gather/模型/训练 逐字复制自 pod_wide.py(其又逐字复制自 pod_fast2.py) ----
def regime_ctx(i, cols_t):
    e = int(E[i]); s0 = e - TRAIL
    if s0 < 0: s0 = 0
    blk = CDT[s0:e].index_select(1, cols_t).float()
    r = torch.nan_to_num(blk[:, :, 0])
    vol7 = r.std(0)
    btcv = torch.nan_to_num(CDT[s0:e, BTC_T, 0].float()).std()
    disp = torch.nan_to_num(blk[-576:, :, 0]).sum(0).std()
    breadth = (torch.nan_to_num(blk[-288:, :, 0]).sum(0) > 0).float().mean()
    absr = r.abs().mean()
    volpct = vol7.argsort().argsort().float() / max(len(vol7) - 1, 1) - 0.5
    qz = torch.nan_to_num(blk[-288:, :, 3]).mean(0)
    qz = (qz - qz.mean()) / (qz.std() + 1e-6)
    tbf = torch.nan_to_num(blk[-288:, :, 6]).mean(0) - 0.5
    n = blk.shape[1]
    mkt = torch.stack([btcv.expand(n), disp.expand(n), breadth.expand(n), absr.expand(n)], -1)
    own = torch.stack([torch.log1p(100 * vol7), volpct, qz, tbf], -1)
    return torch.cat([mkt * 100, own], -1)
def gather_t(i, cols_t):
    e = int(E[i]); s0 = e - W
    if s0 < 0 or e > CDT.shape[0]: return None
    blk = CDT[s0:e].index_select(1, cols_t).float()
    mk = torch.isfinite(blk)
    xp = torch.where(mk, blk, torch.zeros((), device=DEV))
    return torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)
QN = 25
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
        zd = ch * 2
        s.films = nn.ModuleList([nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2 * ch)) for _ in range(8)])
        s.mxa = nn.MultiheadAttention(ch, 4, batch_first=True) if MIDX else None
        s.mxln = nn.LayerNorm(ch) if MIDX else None
        s.xa = nn.MultiheadAttention(zd, 8, batch_first=True)
        s.xln = nn.LayerNorm(zd)
        s.fnorm82 = nn.LayerNorm(82)
        NTREE, TDEPTH = 64, 4
        s.tsel = nn.Parameter(torch.randn(NTREE, TDEPTH, 82) * 0.01)
        s.tthr = nn.Parameter(torch.randn(NTREE, TDEPTH) * 0.5)
        s.tleaf = nn.Parameter(torch.randn(NTREE, 2 ** TDEPTH) * 0.1)
        bits = torch.tensor([[(l >> d) & 1 for d in range(TDEPTH)] for l in range(2 ** TDEPTH)], dtype=torch.float32)
        s.register_buffer("tbits", bits)
        s.fproj = nn.Linear(NTREE, 64)
        s.head = nn.Sequential(nn.Linear(zd + 82 + 64, 256), nn.GELU(), nn.Linear(256, QN))
    def enc(s, x, net, ctx=None, sizes=None):
        h = x.transpose(1, 2); nb = 0; ng = 0
        for l in net:
            if isinstance(l, nn.Conv1d):
                h_in = h
                h = nn.functional.pad(h, (l.dilation[0] * 2, 0)); h = l(h)
            else:
                h = l(h)
                if isinstance(l, nn.GroupNorm):
                    ng += 1
                    if RESD and h.shape == h_in.shape: h = h + h_in
                    if s.films is not None and ctx is not None:
                        fb = s.films[nb](ctx); nb += 1
                        h = h * (1 + 0.1 * fb[:, :h.shape[1]].unsqueeze(-1)) + 0.1 * fb[:, h.shape[1]:].unsqueeze(-1)
                    if s.mxa is not None and ng == 4 and sizes is not None:
                        hv = h.mean(-1)
                        parts = torch.split(hv, sizes)
                        hp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
                        km = torch.ones(hp.shape[:2], dtype=torch.bool, device=h.device)
                        for gi, n_ in enumerate(sizes): km[gi, :n_] = False
                        qm = s.mxln(hp)
                        am2, _ = s.mxa(qm, qm, qm, key_padding_mask=km)
                        av = torch.cat([am2[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
                        h = h + 0.2 * av.unsqueeze(-1)
        return h
    def forward(s, x, sizes, ctx=None, fea=None):
        h = s.enc(x, s.net, ctx, sizes)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        parts = torch.split(z, sizes)
        zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
        mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
        for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
        q = s.xln(zp)
        a, _ = s.xa(q, q, q, key_padding_mask=mask)
        zp = zp + a
        z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        fn = s.fnorm82(fea)
        fx = torch.einsum("nf,tdf->ntd", fn, torch.softmax(s.tsel, -1))
        g = torch.sigmoid((fx - s.tthr) / 0.1)
        pl = g.unsqueeze(2) * s.tbits.unsqueeze(0).unsqueeze(0) + (1 - g.unsqueeze(2)) * (1 - s.tbits.unsqueeze(0).unsqueeze(0))
        fo = (pl.prod(-1) * s.tleaf.unsqueeze(0)).sum(-1)
        z = torch.cat([z, fn, s.fproj(fo)], -1)
        return s.head(z)
QS = torch.tensor([(i + 0.5) / QN for i in range(QN)], device=DEV)
res, res110 = {}, {}
resK = {K: {} for K in SERVE_KS}
for YV in (2023, 2024, 2025, 2026):
    if (yrs == YV).sum() == 0:
        print(f"[{YV}] 无测试锚, 跳过", flush=True); continue
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(E)) if yrs[i] < YV and i < first_te - 60])
    tr = tr_all; cut = int(len(tr) * 0.85); tr1, va1 = tr[:cut], tr[cut:]
    te = np.where(yrs == YV)[0]
    sidx = [i for i in tr1[::25]]
    SS = torch.cat([gather_t(i, MS_T[i])[:, ::8, :7].reshape(-1, 7) for i in sidx])
    mu = SS.mean(0); sd = SS.std(0) + 1e-6
    def norm(x):
        x = x.clone(); x[:, :, :7] = torch.clamp((x[:, :, :7] - mu) / sd, -5, 5)
        return x
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    best_va, best_state = -9, None
    for ep in range(EPOCHS):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), BATCH):
            xs, ys, sz, cxs, fes = [], [], [], [], []
            for i in order[bi:bi + BATCH]:
                m = MS[i]; okf = np.isfinite(YRZ[i, m])
                x = gather_t(i, MS_T[i])
                if x is None: continue
                okt = torch.from_numpy(okf).to(DEV)
                x = norm(x)
                fr = FROW[i]
                if fr < 0: continue
                fea_i = torch.from_numpy(np.nan_to_num(FEA82[fr, m[okf]]).astype(np.float32)).to(DEV)
                xs.append(x[okt]); ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
                cxs.append(regime_ctx(i, MS_T[i])[okt]); fes.append(fea_i)
            if not xs: continue
            xb = torch.cat(xs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            cb = torch.cat(cxs)
            fb = torch.cat(fes)
            o = mdl(xb, sz, ctx=cb, fea=fb)
            d_ = yb.unsqueeze(-1) - o
            loss = torch.maximum(QS * d_, (QS - 1) * d_).mean()
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                x = gather_t(i, MS_T[i])
                if x is None: continue
                x = norm(x)
                fr = FROW[i]
                if fr < 0: continue
                fea_i = torch.from_numpy(np.nan_to_num(FEA82[fr, m]).astype(np.float32)).to(DEV)
                p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i]), fea=fea_i).mean(-1)
                v.append(spear(p.cpu().numpy(), Yv_[i, m]))
        va = float(np.nanmean(v))
        print(f"[{YV}] ep{ep} va {va:+.4f} ({time.time() - t00:.0f}s)", flush=True)
        if va > best_va: best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics, tics110 = [], []
    ticsK = {K: [] for K in SERVE_KS}
    SOLOP = np.full((len(E), NW), np.nan, np.float32)
    with torch.no_grad():
        for i in te:
            m = MS[i]
            x = gather_t(i, MS_T[i])
            if x is None: continue
            x = norm(x)
            fr = FROW[i]
            if fr < 0: continue
            fea_i = torch.from_numpy(np.nan_to_num(FEA82[fr, m]).astype(np.float32)).to(DEV)
            p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i]), fea=fea_i).cpu().numpy().mean(-1)
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
            if len(M110[i]) >= 30:
                tics110.append(spear(p[M110[i]], Yv_[i, m[M110[i]]]))
            # K曲线新增: serve-K 嵌套子集(成员内按逐锚尾随量能 top-K)
            ordm = np.argsort(-qvk[i, m])
            for K in SERVE_KS:
                if len(m) >= int(K * 0.9):
                    sub = ordm[:K]
                    ticsK[K].append(spear(p[sub], Yv_[i, m[sub]]))
    res[YV] = float(np.nanmean(tics)); res110[YV] = float(np.nanmean(tics110))
    for K in SERVE_KS:
        resK[K][YV] = float(np.nanmean(ticsK[K])) if ticsK[K] else float("nan")
    np.save(f"/workspace/exports_train/kcurveF2_pred_K{NTOP}_s{SEED}_{YV}.npy", SOLOP)
    kline_ = " ".join(f"K{K} {resK[K][YV]:+.4f}(n{len(ticsK[K])})" for K in SERVE_KS)
    print(f"== {YV}: all {res[YV]:+.4f} | mem110 {res110[YV]:+.4f} | {kline_}", flush=True)
np.savez_compressed(f"/workspace/exports_train/kcurveF2_meta_K{NTOP}_s{SEED}.npz",
                    E_ts=CTS[E], members=np.array(MS, dtype=object), qvk=qvk,
                    yrs=yrs, symbols=np.array(csyms))
solo = float(np.mean(list(res.values())))
summ = {"NTOP": NTOP, "SEED": SEED, "all": res, "mem110": res110,
        "serveK": {str(K): resK[K] for K in SERVE_KS},
        "serveK_mean": {str(K): float(np.nanmean(list(resK[K].values()))) for K in SERVE_KS}}
json.dump(summ, open(f"/workspace/kcurveF2_K{NTOP}_s{SEED}.json", "w"), indent=1)
print("K曲线均值: " + " ".join(f"K{K} {summ['serveK_mean'][str(K)]:+.4f}" for K in SERVE_KS), flush=True)
print("IC×√K:   " + " ".join(f"K{K} {summ['serveK_mean'][str(K)]*np.sqrt(K):+.3f}" for K in SERVE_KS), flush=True)
print("KCURVE_F2_DONE", flush=True)
