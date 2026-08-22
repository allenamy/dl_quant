"""F-8 有效性复读(POST-HOC, 非预注册, 只读报告): 对 base / +D / +E / +J / +ALL(两模型)用与 judge 同一方法算
 (1) 同年锚内置换目标 shuffle null(3 种子)  (2) 偏移谱 k∈[−6,6]  (3) 增量谱: 臂预测对 base 预测逐锚 OLS 残差 vs YR4s_{i+k}
 (4) 逐名年内持久成分: IC(pred_i, 该名当年 YR4s 均值(剔除锚 i 自身)) — 预测是否载有逐名持久排序
产物 results/f8_validity_reread.json"""
import json, numpy as np
from scipy.stats import spearmanr, rankdata
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); YR4s = TG["YR4s"]; yrs = TG["yrs"].astype(int); MS = list(TG["members"]); nA, NW = YR4s.shape
YEARS = (2023, 2024, 2025, 2026); test = np.isin(yrs, YEARS)
def spear(x, y, nmin=30):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= nmin else np.nan
def nm(a):
    a = np.asarray(a, float); return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")
# 逐名年均(剔自身): 按年累加
ysum = {}; ycnt = {}
for y in YEARS:
    ia = np.where(yrs == y)[0]; Yb = YR4s[ia]; fin = np.isfinite(Yb)
    ysum[y] = np.where(fin, Yb, 0).sum(0); ycnt[y] = fin.sum(0)
out = {}
for model in ("ridge", "lgbm"):
    base = np.load(f"{OUT}/preds/f8_{model}_base.npy")
    for arm in ("base", "pD", "pE", "pJ", "pALL"):
        P = np.load(f"{OUT}/preds/f8_{model}_{arm}.npy")
        icr = np.full(nA, np.nan)
        for i in np.where(test)[0]:
            m = MS[i]; icr[i] = spear(P[i, m], YR4s[i, m])
        A = test & np.isfinite(icr); A_idx = np.where(A)[0]; se = float(np.nanstd(icr[A]) / np.sqrt(A.sum()))
        nulls = []
        for s in range(3):
            rs = np.random.default_rng(s); v = []
            for y in YEARS:
                ia = np.where(A & (yrs == y))[0]; perm = rs.permutation(ia)
                for i, j in zip(ia[::2], perm[::2]):
                    m = MS[i]; v.append(spear(P[i, m], YR4s[j, m]))
            nulls.append(nm(v))
        spec = {}; spec_inc = {}
        for k in range(-6, 7):
            v = []; vi = []
            for i in A_idx[::4]:
                j = i + k
                if 0 <= j < nA:
                    m = MS[i]; v.append(spear(P[i, m], YR4s[j, m]))
                    if arm != "base":
                        p = P[i, m]; b = base[i, m]; ok = np.isfinite(p) & np.isfinite(b)
                        if ok.sum() >= 30:
                            zp = np.full(len(m), np.nan); zb = np.full(len(m), np.nan)
                            zp[ok] = rankdata(p[ok]); zb[ok] = rankdata(b[ok])
                            X = np.stack([np.ones(ok.sum()), zb[ok]], 1); beta = np.linalg.lstsq(X, zp[ok], rcond=None)[0]
                            r = np.full(len(m), np.nan); r[ok] = zp[ok] - X @ beta
                            vi.append(spear(r, YR4s[j, m]))
            spec[str(k)] = nm(v); spec_inc[str(k)] = nm(vi) if vi else None
        # 持久成分: pred_i vs 该名当年均值(剔除自身)
        pers = []
        for i in A_idx[::4]:
            y = yrs[i]; m = MS[i]; yi = YR4s[i, m]; fin = np.isfinite(yi)
            cnt = ycnt[y][m] - fin; s_ = ysum[y][m] - np.where(fin, yi, 0)
            mu = np.where(cnt >= 30, s_ / np.maximum(cnt, 1), np.nan)
            pers.append(spear(P[i, m], mu))
        out[f"{model}:{arm}"] = {"ic_A": nm(icr[A]), "se": se, "null_per_seed": nulls, "null_mean": float(np.mean(nulls)), "null_over_2se": float(np.mean(nulls)) / (2 * se),
                                 "spectrum": spec, "spectrum_increment_vs_base": spec_inc, "persistent_component_ic": nm(pers),
                                 "kpos_monotone_decay": all(spec[str(k)] >= spec[str(k + 1)] - 0.005 for k in range(0, 6))}
        print(model, arm, "IC", round(out[f"{model}:{arm}"]["ic_A"], 4), "null", round(out[f"{model}:{arm}"]["null_mean"], 4), "pers", round(out[f"{model}:{arm}"]["persistent_component_ic"], 4),
              "spec", {k: round(v, 3) for k, v in spec.items()}, flush=True)
json.dump(out, open(f"{OUT}/results/f8_validity_reread.json", "w"), indent=1)
print("VALIDITY_REREAD_DONE")
