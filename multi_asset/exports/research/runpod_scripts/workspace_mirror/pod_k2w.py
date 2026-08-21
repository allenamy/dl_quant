"""K2W: B梯队臂② 表格DL宽版 — 架构逐字(森林64x4+双残差塔+xattn+25分位+0.2辅助头), 数据层换 wide_fea_v1(82特征, 829币含退市).
判据 DESIGN_wide_book_v1 §6: 与 LGBM 臂(bracketB)与 film2(0.0645固定锚)三方同表; 无期货止损(宽树bar同日在产).
弹药完全同树: 31面板通道(剔betaadj)×滞后{0,24,96,168}×{值,横截面秩} = 248 特征/名/锚.
架构 = 全录取件合成: 可微森林枝(NTREE64×深4, 含树结构=下界保证) + 深特征塔(MLP 3层残差)
    + 跨资产注意力 + 25分位 pinball 头 + 森林辅助头0.2(梯度保险). 无序列枝(纯"同桌吃饭"对照).
判据(冻结): raw 排序口径(用户点名), bar=树 0.0763(逐折 0.0830/0.0704/0.0718/0.0798), 门 +0.003;
    期货止损: 前两折均值 < 树前两折(0.0767)−0.004 即砍. 过线→双种子.
用法: pod_k2.py [tag]  env: SEED/EPOCHS=10/LR=1e-3/BATCH=64/HID=256/NTREE=64/TDEPTH=4
"""
import sys as _sys, os as _os, time
TAG = _sys.argv[1] if len(_sys.argv) > 1 else "k2"
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
FEA = np.load("/workspace/data/wide_fea_v1.npy")
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); MS = list(MT["members"]); y4w = MT["y4"]
N = 829; NF = FEA.shape[2]
anchors = list(range(len(E_ts)))
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
YRZ = np.full((len(anchors), N), np.nan, np.float32)
Yv_ = np.full((len(anchors), N), np.nan, np.float32)
for i in range(len(anchors)):
    m = MS[i]
    yv = y4w[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50:
        MS[i] = m[ok]; continue
    MS[i] = m[ok]
    Yv_[i, MS[i]] = yv[ok]
    rr = rankdata(yv[ok]); YRZ[i, MS[i]] = (rr-(ok.sum()+1)/2)/max(ok.sum()-1, 1)
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
class Model(nn.Module):
    def __init__(s):
        super().__init__()
        s.inp = nn.Sequential(nn.Linear(NF, HID), nn.GELU(), nn.LayerNorm(HID))
        s.b1 = nn.Sequential(nn.Linear(HID, HID), nn.GELU(), nn.LayerNorm(HID))
        s.b2 = nn.Sequential(nn.Linear(HID, HID), nn.GELU(), nn.LayerNorm(HID))
        s.forest = Forest()
        s.fproj = nn.Linear(NTREE, HID)
        s.faux = nn.Linear(NTREE, QN)
        s.xa = nn.MultiheadAttention(HID, 8, batch_first=True)
        s.xln = nn.LayerNorm(HID)
        s.head = nn.Linear(HID, QN)
    def forward(s, f, sizes):
        z = s.inp(f)
        z = z + s.b1(z)
        z = z + s.b2(z)
        fo = s.forest(f)
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
TREE_FOLD = None
res = {}
for YV in (2023, 2024, 2025, 2026):
    torch.manual_seed(SEED); np.random.seed(SEED)
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60])
    cut = int(len(tr_all)*0.85); tr1, va1 = tr_all[:cut], tr_all[cut:]
    te = np.where(yrs == YV)[0]
    FS = np.concatenate([FEA[i][MS[i]] for i in tr1[::10] if np.isfinite(FEA[i][MS[i]]).any()])
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
            fs, ys, sz = [], [], []
            for i in order[bi:bi+BATCH]:
                m = MS[i]
                if not np.isfinite(FEA[i][m]).any(): continue
                okf = np.isfinite(YRZ[i, m])
                fs.append(fnorm(i, m[okf])); ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
            if not fs: continue
            fb = torch.cat(fs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV)
            o, oaux = mdl(fb, sz)
            loss = pinball(o, yb) + 0.2 * pinball(oaux, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                if not np.isfinite(FEA[i][m]).any(): continue
                p = mdl(fnorm(i, m), [len(m)])[0].mean(-1)
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
            p = mdl(fnorm(i, m), [len(m)])[0].cpu().numpy().mean(-1)
            SOLOP[i, m] = p; tics.append(spear(p, Yv_[i, m]))
    res[YV] = float(np.nanmean(tics))
    np.save(f"/workspace/exports_train/k2w_s{SEED}_pred_{YV}.npy", SOLOP)
    print(f"== {YV}: k2w {res[YV]:+.4f}", flush=True)
mean = float(np.mean(list(res.values())))
fx = [i for i in range(len(anchors)) if yrs[i] >= 2025 and len(MS[i]) >= 360]
print(f"K2W[s{SEED}] 均值 {mean:+.4f}(判读到 bracketB 判官统一做, 对照 LGBM 臂与 film2 0.0645)", flush=True)
print("K2W_DONE", flush=True)
