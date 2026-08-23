"""L3 快模型 v1 @jpline。规格冻结 DESIGN_lob_shallow_campaign §6: GRU+多视界头+截面软IC损失+171条件。
门(冻结): 30m/1h 头 te 年截面秩IC ≥ 0.03; 4h 头(锚点) vs f11 base-LGBM Δ ≥ +0.005。
产物: results/f12_l3_{SEED}.json + preds/f12_heads_{SEED}.npz(锚点四头分数)。"""
import os, json, time, hashlib
import numpy as np
import torch, torch.nn as nn
from scipy.stats import spearmanr
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
SEED = int(os.environ.get("SEED", "42")); EPOCHS = int(os.environ.get("EPOCHS", "8"))
CHUNK = 288; EMB = 288
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
torch.manual_seed(SEED); np.random.seed(SEED)
Z = np.load(f"{OUT}/data/f12_l3.npz", allow_pickle=True)
ts5 = Z["ts5"].astype(np.int64); XL = Z["X_lob"].astype(np.float32); XK = Z["X_kl"].astype(np.float32)
Y = Z["Y"].astype(np.float32); amap = Z["amap"].astype(np.int64); yr5 = Z["yr5"].astype(int)
syms60 = [str(s) for s in Z["syms60"]]; scol60 = Z["scol60"].astype(np.int64)
T, NS, _ = XL.shape
# 171 条件: 长格 → (nA,59,171) 稠密
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
X171 = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32)
TGn = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); nA = len(TGn["E_ts"])
colmap = {int(c): j for j, c in enumerate(scol60)}
sel = np.isin(ps, scol60)
C = np.full((nA, NS, 171), np.nan, np.float32)
C[pa[sel], [colmap[int(x)] for x in ps[sel]]] = X171[sel]
del X171, FE, F9
log(f"grid T={T} NS={NS} cond dense {C.shape}")
XKz = XK.copy(); XKz[~np.isfinite(XKz)] = 0.0
rep = {"seed": SEED, "self_sha256": hashlib.sha256(open(os.path.abspath(__file__),'rb').read()).hexdigest()[:16],
       "folds": {}}


class L3(nn.Module):
    def __init__(s, d, h=128):
        super().__init__()
        s.inp = nn.Sequential(nn.Linear(d, h), nn.GELU())
        s.gru = nn.GRU(h, h, num_layers=2, batch_first=False)
        s.heads = nn.ModuleList([nn.Linear(h, 1) for _ in range(4)])
        for hd in s.heads:
            nn.init.normal_(hd.weight, 0, 1e-3); nn.init.zeros_(hd.bias)


def icloss(p, y, fin):
    ok = fin & torch.isfinite(y)
    n = ok.sum(-1)
    m = n >= 20
    if not m.any():
        return None
    p0 = torch.where(ok, p, torch.zeros_like(p)); y0 = torch.where(ok, y, torch.zeros_like(y))
    cnt = n.clamp(min=1).float().unsqueeze(-1)
    pc = torch.where(ok, p - p0.sum(-1, keepdim=True) / cnt, torch.zeros_like(p))
    yc = torch.where(ok, y - y0.sum(-1, keepdim=True) / cnt, torch.zeros_like(y))
    num = (pc * yc).sum(-1)
    den = torch.sqrt(((pc ** 2).sum(-1) * (yc ** 2).sum(-1)).clamp(min=1e-8))
    return (1 - num / den)[m].mean()


HW = [0.15, 0.35, 0.35, 0.15]
for YV in (2024, 2025, 2026):
    te = yr5 == YV
    if te.sum() < 5000:
        continue
    first_te = int(np.argmax(te))
    tr_end = first_te - EMB
    tr_idx = np.arange(0, tr_end)
    torch.manual_seed(SEED + YV)
    # 标定
    sl = tr_idx[:: max(1, len(tr_idx) // 3000)]
    def zs(Ms):
        flat = Ms.reshape(-1, Ms.shape[-1])
        return np.nanmean(flat, 0), np.nanstd(flat, 0) + 1e-6
    muL, sdL = zs(XL[sl]); muC, sdC = zs(C[np.clip(amap[sl], 0, nA - 1)])
    ysd = np.nanstd(Y[sl], (0, 1)) + 1e-9
    D = 21 + 8 + 171
    mdl = L3(D).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=1e-3, weight_decay=1e-4)
    starts = list(range(0, tr_end - CHUNK, CHUNK))
    best_va, best_state = -9, None
    va_cut = int(len(starts) * 0.9)
    for ep in range(EPOCHS):
        mdl.train(); h0 = None; t1 = time.time()
        for s0 in starts[:va_cut]:
            j = slice(s0, s0 + CHUNK)
            xb = np.concatenate([
                np.nan_to_num((XL[j] - muL) / sdL), XKz[j],
                np.nan_to_num((C[np.clip(amap[j], 0, nA - 1)] - muC) / sdC) * (amap[j] >= 0)[:, None, None]], -1)
            xb = torch.from_numpy(np.clip(xb, -8, 8)).to(DEV)
            yb = torch.from_numpy(Y[j] / ysd).to(DEV)
            fin = torch.isfinite(torch.from_numpy(XL[j, :, 0])).to(DEV)
            z, h1 = mdl.gru(mdl.inp(xb), h0)
            h0 = h1.detach()
            loss = 0; nl = 0
            for hi in range(4):
                p = mdl.heads[hi](z).squeeze(-1)
                li = icloss(p, yb[:, :, hi], fin)
                if li is not None:
                    loss = loss + HW[hi] * li; nl += 1
            if nl == 0:
                continue
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        # 验证: 训练尾段 10%
        mdl.eval(); vas = []
        with torch.no_grad():
            h0v = None
            for s0 in starts[va_cut:]:
                j = slice(s0, s0 + CHUNK)
                xb = np.concatenate([
                    np.nan_to_num((XL[j] - muL) / sdL), XKz[j],
                    np.nan_to_num((C[np.clip(amap[j], 0, nA - 1)] - muC) / sdC) * (amap[j] >= 0)[:, None, None]], -1)
                xb = torch.from_numpy(np.clip(xb, -8, 8)).to(DEV)
                z, h0v = mdl.gru(mdl.inp(xb), h0v)
                p = mdl.heads[2](z).squeeze(-1).cpu().numpy()      # 1h 头作检查点标尺
                for k in range(0, CHUNK, 12):
                    yy = Y[s0 + k, :, 2]
                    okv = np.isfinite(yy) & np.isfinite(p[k])
                    if okv.sum() >= 20:
                        r = spearmanr(p[k][okv], yy[okv])
                        vas.append(float(r.correlation if hasattr(r, "correlation") else r[0]))
        va = float(np.nanmean(vas)) if vas else -9
        if va > best_va:
            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log(f"[{YV}] ep{ep} va1h {va:+.4f} ({time.time()-t1:.0f}s)")
    mdl.load_state_dict(best_state); mdl.eval()
    # 测试: 时序整段, 每 30m 记 IC; 锚点四头分数导出
    ics = {h: [] for h in range(4)}
    anchor_pred = {}
    with torch.no_grad():
        h0t = None
        for s0 in range(max(0, first_te - CHUNK * 2), T - 1, CHUNK):
            j = slice(s0, min(s0 + CHUNK, T))
            xb = np.concatenate([
                np.nan_to_num((XL[j] - muL) / sdL), XKz[j],
                np.nan_to_num((C[np.clip(amap[j], 0, nA - 1)] - muC) / sdC) * (amap[j] >= 0)[:, None, None]], -1)
            xb = torch.from_numpy(np.clip(xb, -8, 8)).to(DEV)
            z, h0t = mdl.gru(mdl.inp(xb), h0t)
            P4 = torch.stack([mdl.heads[hi](z).squeeze(-1) for hi in range(4)], -1).cpu().numpy()
            for k in range(z.shape[0]):
                t_ = s0 + k
                if not te[t_]:
                    continue
                for hi in range(4):
                    yy = Y[t_, :, hi]
                    okv = np.isfinite(yy) & np.isfinite(P4[k, :, hi])
                    if t_ % 6 == 0 and okv.sum() >= 20:
                        r = spearmanr(P4[k][okv, hi], yy[okv])
                        ics[hi].append(float(r.correlation if hasattr(r, "correlation") else r[0]))
                if t_ + 1 < T and amap[t_ + 1] != amap[t_] and amap[t_ + 1] >= 0:
                    anchor_pred[int(amap[t_ + 1])] = P4[k]         # 锚前最后一个 5m 步
    rep["folds"][str(YV)] = {"ic_5m": round(float(np.nanmean(ics[0])), 4), "ic_30m": round(float(np.nanmean(ics[1])), 4),
                             "ic_1h": round(float(np.nanmean(ics[2])), 4), "ic_4h": round(float(np.nanmean(ics[3])), 4),
                             "best_va": round(best_va, 4), "n_anchor_pred": len(anchor_pred)}
    log(f"== {YV}: 5m {rep['folds'][str(YV)]['ic_5m']:+.4f} 30m {rep['folds'][str(YV)]['ic_30m']:+.4f} 1h {rep['folds'][str(YV)]['ic_1h']:+.4f} 4h {rep['folds'][str(YV)]['ic_4h']:+.4f}")
    if "AP" not in dir():
        AP = np.full((nA, NS, 4), np.nan, np.float32)
    for a_, v in anchor_pred.items():
        AP[a_] = v
    np.savez(f"{OUT}/preds/f12_heads_s{SEED}.npz", AP=AP, syms60=np.array(syms60), scol60=scol60)
    json.dump(rep, open(f"{OUT}/results/f12_l3_s{SEED}.json", "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
log("F12_TRAIN_DONE", json.dumps({k: v for k, v in rep["folds"].items()}, ensure_ascii=False)[:300])
