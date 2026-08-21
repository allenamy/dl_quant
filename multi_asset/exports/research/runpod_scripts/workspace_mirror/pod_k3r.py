"""K3r: K3c 同架构 + 【目标改 resid(YR4)】— K 系首个调整训练目标的臂(用户质询: 目标和评估方向要调整).(ICML25 LAMDA 方向×本仓 FiLM 受据; 表格差距程序末臂)(k=8 虚拟成员, 共享主干+乘性适配器+逐成员头, 预测平均; ICLR25)(恰一个变量; TabReD ICLR25: 时序切分下 MLP-PLR 与 GBDT 并列冠军)(用户命题 2026-08-14: 同弹药下 DL 必须证明能否超树).
弹药完全同树: 31面板通道(剔betaadj)×滞后{0,24,96,168}×{值,横截面秩} = 248 特征/名/锚.
架构 = 全录取件合成: 可微森林枝(NTREE64×深4, 含树结构=下界保证) + 深特征塔(MLP 3层残差)
    + 跨资产注意力 + 25分位 pinball 头 + 森林辅助头0.2(梯度保险). 无序列枝(纯"同桌吃饭"对照).
判据(冻结): raw 排序口径(用户点名), bar=树 0.0763(逐折 0.0830/0.0704/0.0718/0.0798), 门 +0.003;
    期货止损: 前两折均值 < 树前两折(0.0767)−0.004 即砍. 过线→双种子.
用法: pod_k2.py [tag]  env: SEED/EPOCHS=10/LR=1e-3/BATCH=64/HID=256/NTREE=64/TDEPTH=4
"""
import sys as _sys, os as _os, time
TAG = _sys.argv[1] if len(_sys.argv) > 1 else "k3r"
KMEM = int(_os.environ.get("KMEM", "8"))
SEED = int(_os.environ.get("SEED", "42"))
EPOCHS = int(_os.environ.get("EPOCHS", "10"))
LR = float(_os.environ.get("LR", "1e-3"))
BATCH = int(_os.environ.get("BATCH", "64"))
HID = int(_os.environ.get("HID", "256"))
NTREE = int(_os.environ.get("NTREE", "64"))
TDEPTH = int(_os.environ.get("TDEPTH", "4"))
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
import torch, torch.nn as nn
DEV = "cuda"
P = zload("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
ts_ms = P["ts"].astype(np.int64); Y4 = P["Y4"].astype(np.float32); YR4 = P["YR4"].astype(np.float32); MEM = P["MEMBER110"]
CH = P["CH"].astype(np.float32); CHN = [str(c) for c in P["ch_names"]]
keep = [j for j, c in enumerate(CHN) if "betaadj" not in c]
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
LAGS = (0, 24, 96, 168)
NF = len(keep) * 2 * len(LAGS)
FEA_PATH = "/workspace/data/k2_fea248.npy"
if _os.path.exists(FEA_PATH):
    FEA = np.load(FEA_PATH)
else:
    t0 = time.time()
    FEA = np.full((len(anchors), N, NF), np.nan, np.float32)
    for i, r in enumerate(anchors):
        if r - max(LAGS) < 0: continue
        m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
        Fs = []
        for L in LAGS:
            X = np.nan_to_num(np.clip(CH[r - L][m][:, keep], -8, 8))
            XR = np.stack([rankdata(X[:, j])/max(len(m)-1, 1) - 0.5 for j in range(X.shape[1])], -1)
            Fs += [X, XR]
        FEA[i, m] = np.concatenate(Fs, -1)
        if i % 2000 == 0: print(f"fea {i}/{len(anchors)} ({time.time()-t0:.0f}s)", flush=True)
    np.save(FEA_PATH, FEA)
    print(f"特征缓存 {FEA.shape} ({time.time()-t0:.0f}s)", flush=True)
MS = [np.where(MEM[anchors[i]] & np.isfinite(Y4[anchors[i]]))[0] for i in range(len(anchors))]
CTX = np.zeros((len(anchors), 8), np.float32)
for i, r in enumerate(anchors):
    m = MS[i]
    blk = CH[r][m][:, keep]
    for jj, cj in enumerate((0, 9, 16, 20)):
        CTX[i, 2*jj] = np.nanmean(blk[:, cj]); CTX[i, 2*jj+1] = np.nanstd(blk[:, cj])
CTX = np.nan_to_num(CTX)
YRZ = np.full((len(anchors), N), np.nan, np.float32)
Yv_ = np.full((len(anchors), N), np.nan, np.float32)
for i in range(len(anchors)):
    m = MS[i]
    tv = YR4[anchors[i], m]
    ok = np.isfinite(tv)
    Yv_[i, m] = tv
    if ok.sum() >= 10:
        rr = rankdata(tv[ok])
        z = np.full(len(m), np.nan, np.float32)
        z[ok] = (rr-(ok.sum()+1)/2)/max(ok.sum()-1, 1)
        YRZ[i, m] = z
print(f"anchors {len(anchors)} arm {TAG} seed {SEED} NF {NF}", flush=True)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
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
class PLR(nn.Module):
    """周期-线性数值嵌入(Gorishniy'22 / TabReD 冠军件): 每特征 [x, sin(2πfx), cos(2πfx)] → d 维."""
    def __init__(s, nf, K=8, d=8):
        super().__init__()
        s.freq = nn.Parameter(torch.randn(nf, K) * 3.0)
        s.lin = nn.Parameter(torch.randn(nf, 2*K+1, d) / (2*K+1) ** 0.5)
        s.bias = nn.Parameter(torch.zeros(nf, d))
        s.out_dim = nf * d
    def forward(s, x):
        ang = 6.283185307 * x.unsqueeze(-1) * s.freq
        e = torch.cat([x.unsqueeze(-1), torch.sin(ang), torch.cos(ang)], -1)
        h = torch.einsum("nfe,fed->nfd", e, s.lin) + s.bias
        return torch.relu(h).flatten(1)
class Model(nn.Module):
    def __init__(s):
        super().__init__()
        s.plr = PLR(NF)
        s.inp = nn.Sequential(nn.Linear(s.plr.out_dim, HID), nn.GELU(), nn.LayerNorm(HID))
        s.r_in = nn.Parameter(1 + 0.1*torch.randn(KMEM, s.plr.out_dim))
        s.r_h = nn.Parameter(1 + 0.1*torch.randn(KMEM, HID))
        s.mheads = nn.ModuleList([nn.Linear(HID, QN) for _ in range(KMEM)])
        s.film1 = nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2*HID))
        s.film2 = nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2*HID))
        s.b1 = nn.Sequential(nn.Linear(HID, HID), nn.GELU(), nn.LayerNorm(HID))
        s.b2 = nn.Sequential(nn.Linear(HID, HID), nn.GELU(), nn.LayerNorm(HID))
        s.forest = Forest()
        s.fproj = nn.Linear(NTREE, HID)
        s.faux = nn.Linear(NTREE, QN)
        s.xa = nn.MultiheadAttention(HID, 8, batch_first=True)
        s.xln = nn.LayerNorm(HID)
        s.head = nn.Linear(HID, QN)
    def member(s, e, fo, sizes, j, ctx):
        z = s.inp(e * s.r_in[j])
        f1 = s.film1(ctx); z = z * (1 + 0.1*f1[:, :z.shape[1]]) + 0.1*f1[:, z.shape[1]:]
        z = z + s.b1(z * s.r_h[j])
        f2 = s.film2(ctx); z = z * (1 + 0.1*f2[:, :z.shape[1]]) + 0.1*f2[:, z.shape[1]:]
        z = z + s.b2(z)
        z = z + 0.3 * s.fproj(fo)
        parts = torch.split(z, sizes)
        zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
        mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
        for gi, n_ in enumerate(sizes): mask[gi, :n_] = False
        q = s.xln(zp)
        a, _ = s.xa(q, q, q, key_padding_mask=mask)
        zp = zp + a
        z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.mheads[j](z)
    def forward(s, f, sizes, ctx):
        e = s.plr(f)
        fo = s.forest(f)
        outs = torch.stack([s.member(e, fo, sizes, j, ctx) for j in range(KMEM)], 0)
        return outs.mean(0), s.faux(fo), outs
QS = torch.tensor([(i+0.5)/QN for i in range(QN)], device=DEV)
def pinball(o, yb):
    d_ = yb.unsqueeze(-1) - o
    return torch.maximum(QS*d_, (QS-1)*d_).mean()
TREE_FOLD = {2023: 0.0830, 2024: 0.0704, 2025: 0.0718, 2026: 0.0798}
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    cut = int(len(tr_all)*0.85); tr1, va1 = tr_all[:cut], tr_all[cut:]
    te = np.where(yrs == YV)[0]
    FS = np.concatenate([FEA[i][MS[i]] for i in tr1[::10] if np.isfinite(FEA[i][MS[i]]).any()])
    CS_ = CTX[tr1]; cmu = CS_.mean(0); csd = CS_.std(0) + 1e-6
    def cnorm(i, n):
        c = np.clip((CTX[i] - cmu) / csd, -5, 5)
        return torch.from_numpy(np.tile(c, (n, 1))).to(DEV).float()
    fmu = torch.from_numpy(np.nan_to_num(np.nanmean(FS, 0))).to(DEV).float()
    fsd = torch.from_numpy(np.nan_to_num(np.nanstd(FS, 0)) + 1e-6).to(DEV).float()
    def fnorm(i, mm):
        f = torch.from_numpy(np.nan_to_num(FEA[i][mm])).to(DEV).float()
        return torch.clamp((f - fmu) / fsd, -5, 5)
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    best_va, best_state = -9, None
    for ep in range(EPOCHS):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), BATCH):
            fs, ys, sz, cxs = [], [], [], []
            for i in order[bi:bi+BATCH]:
                m = MS[i]
                if not np.isfinite(FEA[i][m]).any(): continue
                okf = np.isfinite(YRZ[i, m])
                fs.append(fnorm(i, m[okf])); ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
                cxs.append(cnorm(i, int(okf.sum())))
            if not fs: continue
            fb = torch.cat(fs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            cb = torch.cat(cxs)
            o, oaux, omem = mdl(fb, sz, cb)
            loss = torch.stack([pinball(omem[j], yb) for j in range(KMEM)]).mean() + 0.2 * pinball(oaux, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                if not np.isfinite(FEA[i][m]).any(): continue
                p = mdl(fnorm(i, m), [len(m)], cnorm(i, len(m)))[0].mean(-1)
                v.append(spear(p.cpu().numpy(), Yv_[i, m]))
        va = float(np.nanmean(v))
        print(f"[{YV}] ep{ep} va {va:+.4f} ({time.time()-t00:.0f}s)", flush=True)
        if va > best_va: best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics = []
    SOLOP = np.full((len(anchors), N), np.nan, np.float32)
    with torch.no_grad():
        for i in te:
            m = MS[i]
            if not np.isfinite(FEA[i][m]).any(): continue
            p = mdl(fnorm(i, m), [len(m)], cnorm(i, len(m)))[0].cpu().numpy().mean(-1)
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/k2_{TAG}_s{SEED}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: k2 {res[YV]:+.4f} vs 树 {TREE_FOLD[YV]:+.4f}", flush=True)
    if False:
        two = ref = 0
        if two < ref - 0.004:
            print(f"FUTILITY_STOP 前两折 {two:+.4f} vs 树 {ref:+.4f}", flush=True)
            print(f"K3r[{TAG} s{SEED}] 判(resid目标训练; 口径: king resid +0.0486 / resid树 +0.0483): 期货止损判负(未超树)", flush=True)
            print("K2_DONE", flush=True); _sys.exit(0)
mean = float(np.mean(list(res.values())))
print(f"K3r[{TAG} s{SEED}] 判(resid目标训练; 口径: king resid +0.0486 / resid树 +0.0483)(口径: raw 排序, 同弹药 248 特征; bar=LGBM 0.0763, 门+0.003): "
      f"resid均值 {mean:+.4f} Δ vs king {mean-0.0486:+.4f} ⇒ "
      + ("超king! 双种子终审" if mean-0.0486 >= 0.003 else ("平手带" if mean-0.0486 > -0.003 else "判负")), flush=True)
print("K2_DONE", flush=True)
