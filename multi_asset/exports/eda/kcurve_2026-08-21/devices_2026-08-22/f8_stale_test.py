"""F-8 判别性泄漏检验(POST-HOC, 非预注册, 先写预期再跑): 新 89 列整体"陈化" —— 锚 i 用同名在锚 i−L 的新列(L=1 即 4h 陈旧, L=6 即 24h 陈旧; 同名非成员 ⇒ 0 中性),
82 列基线保持新鲜。预期(写于运行前): 若增量来自 ≤E 的真实信息, 陈化 4h 后 Δ 只部分衰减(E 族季节性几乎不衰, D/J 部分衰), 24h 后进一步衰减但 E 仍正;
若增量来自目标窗泄漏(E+1..E+48), 陈化 4h 会把"泄漏窗"移到上一锚的目标窗 ⇒ Δ 断崖塌到 ≈0 或负(反转)。两模型同跑, 同折同锚。产物 results/f8_stale_test.json"""
import json, time, numpy as np
from scipy.stats import spearmanr
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
YEARS = (2023, 2024, 2025, 2026); EMBARGO = 60
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=8, verbose=-1)
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
def spear(x, y, nmin=30):
    ok = np.isfinite(x) & np.isfinite(y); return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= nmin else np.nan
def nm(a): a = np.asarray(a, float); return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); YRZ = TG["YRZ"]; YR4s = TG["YR4s"]; yrs = TG["yrs"].astype(int); E_ts = TG["E_ts"].astype(np.int64); nA, NW = YRZ.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True); X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True); X89 = F9["X"]
# 稠密化新列 (nA, NW, 89) 太大(2.5GB f32 可接受)
D = np.zeros((nA, NW, 89), np.float32); D[pa, ps] = X89
def lagged(L):
    Xl = np.zeros_like(X89)
    ok = np.zeros(nA, bool); ok[L:] = (E_ts[L:] - E_ts[:-L]) == 14400 * L
    src = pa - L; good = ok[pa] & (src >= 0)
    Xl[good] = D[src[good], ps[good]]
    return Xl
Y = YRZ[pa, ps]; okrow = np.isfinite(Y)
X82f = X82[okrow].astype(np.float32); Y = Y[okrow].astype(np.float32); A = pa[okrow]; S = ps[okrow]; YRA = yrs[A]
arms = {"fresh": X89[okrow], "lag1_4h": lagged(1)[okrow], "lag6_24h": lagged(6)[okrow]}
del D
res = {}
for model in ("ridge", "lgbm"):
    for arm, Xn in [("base", None)] + list(arms.items()):
        X = X82f if Xn is None else np.concatenate([X82f, Xn], 1)
        P = np.full((nA, NW), np.nan, np.float32); byy = {}
        for YV in YEARS:
            te_anchor = np.where(yrs == YV)[0]; first_te = int(te_anchor[0])
            tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
            tr = tr_ok[A]; te = YRA == YV
            if model == "ridge":
                mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
                Xs = np.clip((X[tr] - mu) / sd, -5, 5).astype(np.float64); Xa = np.concatenate([Xs, np.ones((Xs.shape[0], 1))], 1)
                G = Xa.T @ Xa; G[:-1, :-1] += np.eye(Xs.shape[1]); beta = np.linalg.solve(G, Xa.T @ Y[tr].astype(np.float64)); del Xs, Xa, G
                Xt = np.clip((X[te] - mu) / sd, -5, 5).astype(np.float64); pv = (np.concatenate([Xt, np.ones((Xt.shape[0], 1))], 1) @ beta).astype(np.float32); del Xt
            else:
                import lightgbm as lgb
                pv = lgb.LGBMRegressor(**LGB_PARAMS).fit(X[tr], Y[tr]).predict(X[te]).astype(np.float32)
            P[A[te], S[te]] = pv
            byy[str(YV)] = nm([spear(P[i], YR4s[i]) for i in te_anchor])
            log(model, arm, YV, f"{byy[str(YV)]:+.4f}")
        icr = np.full(nA, np.nan)
        for i in np.where(np.isin(yrs, YEARS))[0]:
            icr[i] = spear(P[i], YR4s[i])
        res[f"{model}:{arm}"] = {"by_year": byy, "icr": icr}
    base = res[f"{model}:base"]["icr"]
    for arm in arms:
        d = res[f"{model}:{arm}"]["icr"] - base; ok = np.isfinite(d)
        res[f"{model}:{arm}"]["delta_vs_base"] = {"mean": float(d[ok].mean()), "t": float(d[ok].mean() / (d[ok].std(ddof=1) / np.sqrt(ok.sum()))), "by_year": {str(y): nm(d[yrs == y]) for y in YEARS}}
        log(model, arm, "Δ vs base", res[f"{model}:{arm}"]["delta_vs_base"])
out = {k: {kk: vv for kk, vv in v.items() if kk != "icr"} for k, v in res.items()}
json.dump(out, open(f"{OUT}/results/f8_stale_test.json", "w"), indent=1)
print("STALE_TEST_DONE", json.dumps({k: v.get("delta_vs_base", {}).get("mean") for k, v in out.items()}))
