"""R1 成交概率首拟合 · 执行既有预写门(MAP_paradigm_headroom §2-W2, 冻结先于数字):
过门 = 全特征模型 OOS AUC − 基线(rvol+换手) ≥ +0.02(逐日 walk-forward, pooled)。
标签: 已提交 maker 单的成交结局(full≥99.9% 名义 =1); 特征全部为提交时点可得(≤submit)。
读出(不改判): 逐 spread 桶 / 逐流动性档的 p(fill) —— 赌博机设计的原料。"""
import json, glob, os
import numpy as np
rows = []
for f in sorted(glob.glob(os.path.expanduser("~/dl_quant_live/state/live/pilot_log/*/orders.jsonl"))):
    day = os.path.basename(os.path.dirname(f))
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        r["_day"] = day; rows.append(r)
sub = [r for r in rows if r.get("submit_ts") and r.get("order_type") == "maker"
       and r.get("intended_notional") not in (None, 0)]
print(f"总行 {len(rows)}, 已提交 maker {len(sub)}")
from collections import Counter
print("终态分布:", dict(Counter(r.get("terminal_reason") for r in sub).most_common(8)))
# 逐 symbol 逐锚 mid 序列 → 因果 trailing rvol(过去 6 锚 mid 变化 std)
mids = {}
for r in rows:
    if r.get("mid_at_anchor"):
        mids.setdefault(r["symbol"], []).append((r["anchor_ts"], r["mid_at_anchor"]))
rvol_map = {}
for s, xs in mids.items():
    xs = sorted(set(xs))
    ts = [t for t, _ in xs]; m = np.array([v for _, v in xs], float)
    rets = np.abs(np.diff(np.log(m)))
    for i, t in enumerate(ts):
        lo = max(0, i-6)
        rvol_map[(s, t)] = float(np.mean(rets[lo:i])) if i > lo else np.nan
anchor_turn = {}
for r in sub:
    anchor_turn[r["anchor_ts"]] = anchor_turn.get(r["anchor_ts"], 0.0) + abs(r["intended_notional"])
# 逐 symbol 历史成交率(严格用【之前的日】— walk-forward 安全)
days = sorted(set(r["_day"] for r in sub))
hist_fill = {}
per_day_sym = {}
for r in sub:
    filled = abs(r.get("filled_notional") or 0) >= 0.999*abs(r["intended_notional"])
    per_day_sym.setdefault((r["_day"], r["symbol"]), []).append(filled)
X, y, meta = [], [], []
for r in sub:
    d, s = r["_day"], r["symbol"]
    prior = [f for (dd, ss), fl in per_day_sym.items() if ss == s and dd < d for f in fl]
    histf = np.mean(prior) if len(prior) >= 5 else np.nan
    spr = r.get("spread_at_submit_bps")
    ps, mid = r.get("price_submit"), r.get("mid_at_submit")
    dist_bps = abs(ps/mid - 1)*1e4 if (ps and mid) else np.nan
    rv = rvol_map.get((s, r["anchor_ts"]), np.nan)
    feats = [abs(r["intended_notional"]), np.sign(r["intended_notional"]),
             spr if spr is not None else np.nan, dist_bps, rv,
             anchor_turn.get(r["anchor_ts"], np.nan), histf,
             float(r.get("attempt_idx") or 1)]
    X.append(feats)
    y.append(1.0 if abs(r.get("filled_notional") or 0) >= 0.999*abs(r["intended_notional"]) else 0.0)
    meta.append((d, s, spr))
X = np.array(X, float); y = np.array(y); days_arr = np.array([m[0] for m in meta])
print(f"样本 {len(y)}, 全成率 {y.mean():.3f}, spread 特征覆盖 {np.isfinite(X[:,2]).mean():.1%}")
def auc(scores, labels):
    ok = np.isfinite(scores)
    s, t = scores[ok], labels[ok]
    if len(set(t)) < 2: return np.nan
    r = s.argsort().argsort().astype(float)
    n1 = t.sum(); n0 = len(t)-n1
    return (r[t == 1].mean() - (n1-1)/2) / n0
def fit_predict(Xtr, ytr, Xte, cols):
    # 中位数填充 + 标准化 + 岭正则逻辑回归(纯 numpy, 无依赖风险)
    med = np.nanmedian(Xtr[:, cols], axis=0)
    def prep(A):
        B = A[:, cols].copy()
        for j in range(B.shape[1]):
            B[np.isnan(B[:, j]), j] = med[j]
        return B
    A = prep(Xtr); mu, sd = A.mean(0), A.std(0)+1e-9
    A = (A-mu)/sd; A = np.c_[A, np.ones(len(A))]
    w = np.zeros(A.shape[1])
    for _ in range(300):
        p = 1/(1+np.exp(-A@w))
        g = A.T@(p-ytr)/len(ytr) + 0.01*np.r_[w[:-1], 0]
        h_diag = (p*(1-p))@ (A**2) /len(ytr) + 0.01
        w -= g/h_diag
    B = prep(Xte); B = np.c_[(B-mu)/sd, np.ones(len(B))]
    return 1/(1+np.exp(-B@w))
BASE = [4, 5]           # rvol + 锚换手(预写基线)
FULL = list(range(X.shape[1]))
aucs = {"base": [], "full": []}
for i in range(3, len(days)):
    tr = np.isin(days_arr, days[:i]); te = days_arr == days[i]
    if te.sum() < 30 or len(set(y[tr])) < 2: continue
    for tag, cols in (("base", BASE), ("full", FULL)):
        p = fit_predict(X[tr], y[tr], X[te], cols)
        aucs[tag].append((days[i], auc(p, y[te]), int(te.sum())))
for tag in ("base", "full"):
    v = [a for _, a, _ in aucs[tag] if np.isfinite(a)]
    print(f"  {tag}: 逐日 {[(d, round(a,3), n) for d, a, n in aucs[tag]]}")
pb = np.nanmean([a for _, a, _ in aucs["base"]]); pf = np.nanmean([a for _, a, _ in aucs["full"]])
print(f"\n基线 AUC {pb:.4f} | 全特征 {pf:.4f} | Δ {pf-pb:+.4f} ⇒ "
      + ("★过门(≥+0.02), 进赌博机设计" if pf-pb >= 0.02 else "不过门, 记录关闭或等更多标签"))
# 读出: spread 桶 p(fill)
spr_all = X[:, 2]; ok = np.isfinite(spr_all)
if ok.sum() > 200:
    qs = np.nanquantile(spr_all[ok], [0, .25, .5, .75, 1])
    print("\nspread 桶 p(fill):", end=" ")
    for a_, b_ in zip(qs[:-1], qs[1:]):
        m_ = ok & (spr_all >= a_) & (spr_all <= b_)
        print(f"[{a_:.1f},{b_:.1f}]bps:{y[m_].mean():.2f}(n={m_.sum()})", end="  ")
    print()
hf = X[:, 6]; okh = np.isfinite(hf)
if okh.sum() > 200:
    print(f"逐名历史成交率特征: corr(histf, y) = {np.corrcoef(hf[okh], y[okh])[0,1]:+.3f}")
print("R1_DONE")
