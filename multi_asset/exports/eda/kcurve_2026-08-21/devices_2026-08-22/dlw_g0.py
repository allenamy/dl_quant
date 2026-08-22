"""DLW · G0 预门基准: Ridge82 / LGBM82 同弹药同目标同折 @jpline CPU(2026-08-22, Session 6737834a-DLW)。
预注册 §P.2/§P.3(冻结段 SHA256 33f066c9…64577, commit 7acda02)。
折: 测试年 YV ∈ {2023,2024,2025,2026}; 训练 = 年 < YV 且锚序号 < 测试首锚 − 60; 标签 YRZ(成员内残差秩 [−0.5,0.5])。
R82: Ridge α=1.0, 训练折均值/标准差标准化 clip ±5, 截距不惩罚。
L82: LGBMRegressor(400, 0.05, 63, 0.8, 0.8, random_state=0, n_jobs=8)(参数沿 B 梯队不搜; n_jobs=8 不抢 F-1 的 CPU)。
产物: preds/dlw_R82_s0.npy, preds/dlw_L82_s0.npy(锚 × 829, 测试年有值), results/dlw_g0.json(逐年 IC 残差/原始口径, 用时, SHA)。
用法 @jpline: python dlw_g0.py [--only R82|L82]
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr

ROOT = "/mnt/storage/private/work_hsy"; OUT = f"{ROOT}/dlw_2026-08-22"
EMBARGO = 60; ALPHA = 1.0; NJOBS = 8
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=NJOBS, verbose=-1)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 30 else np.nan


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
    yrs = TG["yrs"]; YRZ = TG["YRZ"]; YR4s = TG["YR4s"]; y4s = TG["y4s"]; nA, NW = YRZ.shape
    FE = np.load(f"{OUT}/data/dlw_fea82.npz", allow_pickle=True)
    X16 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64); names = [str(n) for n in FE["names"]]
    Y = YRZ[pa, ps]; okrow = np.isfinite(Y)
    X = X16[okrow].astype(np.float32); Y = Y[okrow].astype(np.float32); A = pa[okrow]; S = ps[okrow]; YRA = yrs[A]
    del X16
    log(f"样本 {X.shape} (有标签行 {okrow.sum()}/{len(okrow)})")
    res = {"self_sha256": sha(os.path.abspath(__file__)), "targets_sha256": sha(f"{OUT}/data/dlw_targets.npz"), "fea_sha256": sha(f"{OUT}/data/dlw_fea82.npz"),
           "n_rows": int(len(Y)), "embargo_anchors": EMBARGO, "ridge_alpha": ALPHA, "lgb_params": LGB_PARAMS, "arms": {}}
    arms = ["R82", "L82"] if only is None else [only]
    PRED = {a: np.full((nA, NW), np.nan, np.float32) for a in arms}
    for YV in (2023, 2024, 2025, 2026):
        te_anchor = np.where(yrs == YV)[0]
        if len(te_anchor) == 0:
            continue
        first_te = int(te_anchor[0])
        tr_anchor_ok = np.zeros(nA, bool); tr_anchor_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
        tr = tr_anchor_ok[A]; te = YRA == YV
        assert A[tr].max() < first_te - EMBARGO
        log(f"[{YV}] train rows {tr.sum()} (anchors < {first_te-EMBARGO}) test rows {te.sum()}")
        for arm in arms:
            t1 = time.time()
            if arm == "R82":
                mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
                Xs = np.clip((X[tr] - mu) / sd, -5, 5).astype(np.float64); ones = np.ones((Xs.shape[0], 1))
                Xa = np.concatenate([Xs, ones], 1)
                G = Xa.T @ Xa; G[:-1, :-1] += ALPHA * np.eye(Xs.shape[1])
                beta = np.linalg.solve(G, Xa.T @ Y[tr].astype(np.float64))
                Xt = np.clip((X[te] - mu) / sd, -5, 5).astype(np.float64)
                pv = (np.concatenate([Xt, np.ones((Xt.shape[0], 1))], 1) @ beta).astype(np.float32)
            else:
                import lightgbm as lgb
                gbm = lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr], Y[tr])
                pv = gbm.predict(X[te]).astype(np.float32)
            PRED[arm][A[te], S[te]] = pv
            ics_r = [spear(PRED[arm][i], YR4s[i]) for i in te_anchor]; ics_y = [spear(PRED[arm][i], y4s[i]) for i in te_anchor]
            res["arms"].setdefault(arm, {"ic_resid_by_year": {}, "ic_raw_by_year": {}, "sec_by_year": {}})
            res["arms"][arm]["ic_resid_by_year"][str(YV)] = float(np.nanmean(ics_r)); res["arms"][arm]["ic_raw_by_year"][str(YV)] = float(np.nanmean(ics_y))
            res["arms"][arm]["sec_by_year"][str(YV)] = round(time.time() - t1, 1)
            log(f"[{YV}] {arm} IC resid {np.nanmean(ics_r):+.4f} raw {np.nanmean(ics_y):+.4f} ({time.time()-t1:.0f}s)")
            np.save(f"{OUT}/preds/dlw_{arm}_s0.npy", PRED[arm])
            json.dump(res, open(f"{OUT}/results/dlw_g0{'' if only is None else '_' + only}.json", "w"), indent=1)
    for arm in arms:
        r = res["arms"][arm]; r["ic_resid_mean"] = float(np.mean(list(r["ic_resid_by_year"].values()))); r["ic_raw_mean"] = float(np.mean(list(r["ic_raw_by_year"].values())))
        log(arm, "年均 resid", f"{r['ic_resid_mean']:+.4f}", "raw", f"{r['ic_raw_mean']:+.4f}")
    json.dump(res, open(f"{OUT}/results/dlw_g0{'' if only is None else '_' + only}.json", "w"), indent=1)
    log("G0_DONE")


if __name__ == "__main__":
    main()
