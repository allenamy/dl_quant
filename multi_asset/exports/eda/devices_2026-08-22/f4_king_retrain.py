"""F-4 · king 管线重训(原目标 = 原始收益成员内秩)吃 F-8 89 新列 @jpline(2026-08-22, Session 6737834a 主线)。
预注册 `PREREG_F4_king_retrain_raw_target_2026-08-22.md`(SHA b119f4fa…4aa5e, commit c635653) — 先于任何数字。
唯一变量 vs f8_higher_order_features.run(): 标签 Y = 原始秩(y4s 成员内 rank/(n−1)−0.5, = king 配方
`pod_export_shadow_bundle.py:34`), 而非残差秩 YRZ。折/embargo/LGBM 参数/列构造全部逐字复用 F-8 装置。
臂: K82raw(对照 = king 管线在本网格的复制品) / K171raw(处理 = 82+89)。
产物: preds/f4_lgbm_{arm}.npy(锚×829) + results/f4_king_retrain.json(逐年双口径 IC)。
用法 @jpline: python -u f4_king_retrain.py
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
sys.path.insert(0, OUT)
PREREG_SHA = "b119f4fab8b1bfe52857bf412c87434f7be1a0c34c70ad31c67d91f3f0b4aa5e"; PREREG_COMMIT = "c635653"
YEARS = (2023, 2024, 2025, 2026); EMBARGO = 60
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
                  colsample_bytree=0.8, random_state=0, n_jobs=12, verbose=-1)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y, nmin=30):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < nmin:
        return np.nan
    r = spearmanr(x[ok], y[ok])
    return float(r.correlation if hasattr(r, "correlation") else r[0])


def nanmean(a):
    a = np.asarray(a, float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")


def main():
    import lightgbm as lgb
    TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
    yrs = TG["yrs"].astype(int); YRZ = TG["YRZ"]; YR4s = TG["YR4s"]; y4s = TG["y4s"]
    MS = list(TG["members"]); nA, NW = YRZ.shape
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
    X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
    X89 = F9["X"]
    assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.array_equal(F9["pair_s"].astype(np.int64), ps)
    rep = {"prereg": {"sha": PREREG_SHA, "commit": PREREG_COMMIT}, "self_sha256": sha(os.path.abspath(__file__)),
           "targets_sha256": sha(f"{DLW}/data/dlw_targets.npz"), "fea82_sha256": sha(f"{DLW}/data/dlw_fea82.npz"),
           "fea89_sha256": sha(f"{OUT}/data/f8_fea89.npz"), "lgb_params": LGB_PARAMS, "embargo_anchors": EMBARGO,
           "label": "raw in-member rank of y4s (king recipe), NOT residual", "arms": {}}

    # ── 标签: 原始秩(king 配方). 逐锚在成员内排, 与残差秩同一 (pa, ps) 行序 ──
    YRAW = np.full((nA, NW), np.nan, np.float32)
    for i in range(nA):
        m = np.asarray(MS[i], dtype=np.int64)
        if m.size == 0:
            continue
        v = y4s[i, m]; ok = np.isfinite(v)
        if ok.sum() < 50:
            continue
        rr = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
        YRAW[i, m[ok]] = rr.astype(np.float32)
    Yraw = YRAW[pa, ps]
    Yres = YRZ[pa, ps]
    okrow = np.isfinite(Yraw) & np.isfinite(Yres)      # ★ 与 F-8 同一行集合(可比性), 两标签都有限
    X82 = X82[okrow].astype(np.float32); X89 = X89[okrow]
    Y = Yraw[okrow].astype(np.float32); A = pa[okrow]; S = ps[okrow]; YRA = yrs[A]
    rep["n_rows"] = int(len(Y)); rep["n_rows_dropped_vs_resid_rowset"] = int((~okrow).sum())
    log(f"rows {len(Y)} X82 {X82.shape} X89 {X89.shape} | 标签相关 ρ(raw,resid)={spear(Yraw[okrow], Yres[okrow]):+.4f}")
    rep["label_rho_raw_vs_resid"] = round(spear(Yraw[okrow], Yres[okrow]), 4)

    folds = []
    for YV in YEARS:
        te_anchor = np.where(yrs == YV)[0]
        if te_anchor.size == 0:
            continue
        first_te = int(te_anchor[0])
        tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
        folds.append((YV, te_anchor, tr_ok[A], YRA == YV))

    for arm, X in (("K82raw", X82), ("K171raw", None)):
        if X is None:
            X = np.concatenate([X82, X89], 1)
        t_arm = time.time()
        P = np.full((nA, NW), np.nan, np.float32)
        icr = np.full(nA, np.nan); icy = np.full(nA, np.nan); byy = {}
        for YV, te_anchor, tr, te in folds:
            t1 = time.time()
            gbm = lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr], Y[tr])
            pv = gbm.predict(X[te]).astype(np.float32)
            P[A[te], S[te]] = pv
            for i in te_anchor:
                icr[i] = spear(P[i], YR4s[i]); icy[i] = spear(P[i], y4s[i])
            byy[str(YV)] = {"ic_resid": nanmean(icr[te_anchor]), "ic_raw": nanmean(icy[te_anchor]),
                            "n_train": int(tr.sum()), "sec": round(time.time() - t1, 1)}
            log(f"[{arm}] {YV} resid {byy[str(YV)]['ic_resid']:+.4f} raw {byy[str(YV)]['ic_raw']:+.4f} ({time.time()-t1:.0f}s)")
        np.save(f"{OUT}/preds/f4_lgbm_{arm}.npy", P)
        rep["arms"][arm] = {"by_year": byy, "n_cols": int(X.shape[1]),
                            "ic_resid_mean": nanmean([v["ic_resid"] for v in byy.values()]),
                            "ic_raw_mean": nanmean([v["ic_raw"] for v in byy.values()]),
                            "pred_sha256": sha(f"{OUT}/preds/f4_lgbm_{arm}.npy"), "sec": round(time.time() - t_arm, 1)}
        log(f"[{arm}] DONE 年均 raw {rep['arms'][arm]['ic_raw_mean']:+.4f} resid {rep['arms'][arm]['ic_resid_mean']:+.4f} ({time.time()-t_arm:.0f}s)")
        del X, P
        json.dump(rep, open(f"{OUT}/results/f4_king_retrain.json", "w"), indent=1, default=float)
    # 同判官参照行: F-8 残差臂 pALL 的双口径(若在)
    for nm, pth in (("f8_lgbm_pALL", f"{OUT}/preds/f8_lgbm_pALL.npy"), ("f8_lgbm_base", f"{OUT}/preds/f8_lgbm_base.npy")):
        if os.path.exists(pth):
            Q = np.load(pth); r = np.full(nA, np.nan); q = np.full(nA, np.nan)
            for i in range(nA):
                r[i] = spear(Q[i], YR4s[i]); q[i] = spear(Q[i], y4s[i])
            rep.setdefault("reference_rows", {})[nm] = {"ic_resid_mean": nanmean(r), "ic_raw_mean": nanmean(q)}
    json.dump(rep, open(f"{OUT}/results/f4_king_retrain.json", "w"), indent=1, default=float)
    log("F4_TRAIN_DONE", {k: (v["ic_raw_mean"], v["ic_resid_mean"]) for k, v in rep["arms"].items()})


if __name__ == "__main__":
    main()
