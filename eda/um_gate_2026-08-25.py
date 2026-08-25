"""um 新信息源第一轮前置门 @jpline。预注册 DESIGN_um_features_2026-08-25 (ddf9bad) 先于本数字。
BASE=LGBM(171) vs UM=LGBM(171+10), 全宇宙行, walk-forward 2023-26, embargo 60 锚。
判据(与 f11_gate 同构): Δ锚级截面秩IC ≥ +0.005 且 ≥3/4 折同号(raw y4s 主 / YRZ 辅双口径)。
★覆盖注记: um 面板 2023-01 起 ⇒ fold-2023 训练段(2022) um 列全缺(LGBM 原生缺失) ⇒ 该折 Δ 结构性≈0, 判据实际由 2024/25/26 承载。"""
import os, time, hashlib, datetime as dt, json
import numpy as np
from scipy.stats import spearmanr
import lightgbm as lgb

ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
YEARS = (2023, 2024, 2025, 2026); EMB = 60
LGB = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
           colsample_bytree=0.8, random_state=0, n_jobs=20, verbose=-1)
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int)
y4s = TG["y4s"]; YRZ = TG["YRZ"]
SY = [str(x) for x in TG["symbols"]]
nA, NW = y4s.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
X171 = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); del FE, F9

# ---- UM 特征拼装 (nA, NW, 10), +1 bar(5m) 可得性时移 ----
T0S = int(dt.datetime(2023, 1, 1, tzinfo=dt.timezone.utc).timestamp())
k5 = (E - T0S) // 300 - 1          # ★时移: 锚上最新可用 = 锚前一根 5m
NT = 383040
def gat(v, k):                      # k<0 或越界 → nan
    o = np.full(len(k), np.nan, np.float32)
    m = (k >= 0) & (k < len(v))
    o[m] = v[k[m]]
    return o
UM = np.full((nA, NW, 10), np.nan, np.float32)
nsym = 0
for j, s in enumerate(SY):
    p = f"{ROOT}/um_panel/{s}.npz"
    if not os.path.exists(p):
        continue
    X = np.load(p)["X"]
    oiv = np.log(np.clip(X[:, 1], 1e-9, None)); oiv[~np.isfinite(X[:, 1])] = np.nan
    ltp, lta, lg, tk = X[:, 2], X[:, 3], X[:, 4], X[:, 5]
    a0 = gat(oiv, k5); a1 = gat(oiv, k5 - 12); a4 = gat(oiv, k5 - 48)
    f = np.empty((nA, 10), np.float32)
    f[:, 0] = a0 - a1                                     # oiv Δ1h
    f[:, 1] = a0 - a4                                     # oiv Δ4h
    e = np.copy(a0); prev = np.nan
    for i in range(nA):                                   # 锚频 EMA α.1(半衰~26h)
        v = a0[i]
        if np.isfinite(v):
            prev = v if not np.isfinite(prev) else 0.1 * v + 0.9 * prev
        e[i] = prev
    f[:, 2] = a0 - e                                      # oiv EMA 偏离
    f[:, 3] = gat(ltp, k5)                                # 大户仓位比水平
    f[:, 4] = gat(ltp, k5) - gat(ltp, k5 - 288)           # Δ24h
    r = gat(ltp, k5) / np.where(np.abs(gat(lta, k5)) > 1e-9, gat(lta, k5), np.nan)
    f[:, 5] = r                                           # 集中度(仓位比/账户比)
    f[:, 6] = gat(lg, k5)                                 # 全户水平
    f[:, 7] = gat(lg, k5) - gat(lg, k5 - 288)             # Δ24h
    f[:, 8] = gat(tk, k5)                                 # 吃单比水平
    f[:, 9] = gat(tk, k5) - gat(tk, k5 - 12)              # Δ1h
    UM[:, j, :] = f
    nsym += 1
log(f"um features built syms={nsym}")
# 截面 z(逐锚逐列, ≥20 有效)
for c in range(10):
    V = UM[:, :, c]
    m = np.isfinite(V)
    n = m.sum(1)
    mu = np.nanmean(np.where(m, V, np.nan), 1)
    sd = np.nanstd(np.where(m, V, np.nan), 1)
    ok = n >= 20
    Z = (V - mu[:, None]) / np.where(sd[:, None] > 1e-9, sd[:, None], np.nan)
    Z[~ok] = np.nan
    UM[:, :, c] = np.clip(Z, -5, 5)
XU = UM[pa, ps]                                            # (nrows,10)
Yr = y4s[pa, ps]; Yz = YRZ[pa, ps]; YRA = yrs[pa]
fin = np.isfinite(Yz)
log(f"rows {fin.sum()} um_cov {np.isfinite(XU[:,0]).mean():.2f}")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f_:
        for ch in iter(lambda: f_.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()
rep = {"prereg": "ddf9bad", "self_sha256": sha(os.path.abspath(__file__))[:16], "folds": {}}

def xsec_ic(pred, y, anchors):
    ics = []
    for a in np.unique(anchors):
        m = anchors == a
        if m.sum() < 25:
            continue
        p_, y_ = pred[m], y[m]
        ok = np.isfinite(p_) & np.isfinite(y_)
        if ok.sum() < 25:
            continue
        ics.append(spearmanr(p_[ok], y_[ok])[0])
    return float(np.nanmean(ics))

for YV in YEARS:
    te = fin & (YRA == YV)
    tr = fin & (YRA < YV)
    if tr.sum() == 0 or te.sum() == 0:
        continue
    temin = pa[te].min()
    tr = tr & (pa < temin - EMB)
    r = {}
    for tag, XT in (("base", X171), ("um", np.concatenate([X171, XU], 1))):
        mdl = lgb.LGBMRegressor(**LGB)
        mdl.fit(XT[tr], Yz[tr])
        pd_ = mdl.predict(XT[te])
        r[tag + "_raw"] = xsec_ic(pd_, Yr[te], pa[te])
        r[tag + "_rz"] = xsec_ic(pd_, Yz[te], pa[te])
    r["d_raw"] = round(r["um_raw"] - r["base_raw"], 5)
    r["d_rz"] = round(r["um_rz"] - r["base_rz"], 5)
    rep["folds"][str(YV)] = {k: round(v, 5) for k, v in r.items()}
    log(f"[{YV}] base_raw {r['base_raw']:.4f} um_raw {r['um_raw']:.4f} Δraw {r['d_raw']:+.5f} Δrz {r['d_rz']:+.5f}")
json.dump(rep, open(f"{OUT}/results/um_gate_r1.json", "w"), indent=1)
log("UM_GATE_DONE")
