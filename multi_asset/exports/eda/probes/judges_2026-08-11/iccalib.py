"""#55 监视器阈值标定: α=0.05+带.002 书的逐锚 corr(w_held, y) 分布 → 滚动24/48锚均值的分位。
输出 = 监视器预注册阈值的标定依据(离线全史, 非实盘窗口自标 —— 避免"判据从被判对象里取")。"""
import sys, json, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
from scipy.stats import spearmanr
state = None; prev = np.zeros(N); ics = []
for i in range(n):
    m = MSK[i]; syms = [SYMS[j] for j in m]
    out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
    state = out["state"]
    tgt = np.asarray(out["target_w"], float)
    w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
    delta = tgt - w[m]
    T = np.abs(delta) > BW
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum()/T.sum()
    w[m] = wm; prev = w
    y = RET[i]; ok = np.isfinite(y) & (np.abs(w[m]) > 0)
    if ok.sum() >= 30:
        ics.append(float(spearmanr(w[m][ok], y[ok]).statistic))
ics = np.array(ics)
def roll(x, k):
    return np.array([x[j-k:j].mean() for j in range(k, len(x)+1)])
r24, r48 = roll(ics, 24), roll(ics, 48)
out = dict(n=len(ics), mean=round(float(ics.mean()), 5), sd=round(float(ics.std(ddof=1)), 5),
           p_neg=round(float((ics < 0).mean()), 4),
           r24=dict(p1=round(float(np.percentile(r24, 1)), 5), p5=round(float(np.percentile(r24, 5)), 5),
                    p10=round(float(np.percentile(r24, 10)), 5), mean=round(float(r24.mean()), 5)),
           r48=dict(p1=round(float(np.percentile(r48, 1)), 5), p5=round(float(np.percentile(r48, 5)), 5),
                    p10=round(float(np.percentile(r48, 10)), 5), mean=round(float(r48.mean()), 5)))
print(json.dumps(out, indent=1))
json.dump(out, open(f"{PD}/ic_calib_a005.json", "w"), indent=1)
print("ICCALIB_DONE")
