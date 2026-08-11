"""R1-S1 v0: 执行滑点的可预测性 — 订单级 walk-forward (本地 CPU, 只读 LIVE 账本).

★ 判读规则先于数字 (2026-08-06 10:5xZ 写, 未看任何模型输出):
  · 标签   = 已成交订单的净滑点 bps/side = sign(side)·(avg_fill_px − mid_at_submit)/mid_at_submit·1e4
             (正 = 付出成本; 与 pilot_metrics v2 的 slip_net 同号约定; mid_at_submit 为执行相关基准)
  · 特征   = 【提交时刻或更早】可知: side / leg类型 / attempt_idx / intended_notional /
             regime / 时段(hour) / 逐名 trailing 4h 波动(由历史锚点 mid 向量算, 严格用过去) /
             逐名 trailing 平均滑点(expanding, 只用【更早锚】; 首锚该特征=全局均值)
             ⇒ 禁止一切成交后信息 (avg_fill_px / filled_notional / fee 不入特征)。
  · 切分   = 按锚点时间排序, 4 折 walk-forward (前 i 折训, 第 i+1 折测), 折边界=锚, 不切开同锚订单。
  · 主判量 = OOS Spearman(ĉ, 真实滑点), 4 折逐折。
  · 读法   = DIRECTIONAL: 全体 OOS Spearman ≥ 0.10 且 ≥3/4 折同号正。
             DECISIVE-for-S2a: 按 ĉ 分五档, 最贵档 − 最便宜档 的真实滑点差 ≥ 2 bps
             (这是 skip/downsize 规则能吃到的肉的下界)。
             两条都不到 ⇒ 报 CANNOT USE, 不硬拗。
  · 模型   = Ridge(标准化) 为主判; GBM 只作参考不进判据 (n≈1.4k, 树模型方差大)。
  · 诚实项 = n 小; 费用不入标签(费用是算术); maker 未成交(机会成本)不在本判 — S1 只判滑点排序。
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

R = os.path.expanduser("~/dl_quant_live")
LOG = os.path.join(R, "state", "live", "pilot_log")

orders, anchors = [], []
for f in sorted(glob.glob(os.path.join(LOG, "2026*", "orders.jsonl"))):
    for l in open(f):
        orders.append(json.loads(l))
for f in sorted(glob.glob(os.path.join(LOG, "2026*", "anchors.jsonl"))):
    for l in open(f):
        anchors.append(json.loads(l))
anchors.sort(key=lambda a: a["anchor_ts"])
print(f"orders={len(orders)}  anchors={len(anchors)}")

# ── 逐名 trailing 4h 波动: 由锚点 mid 向量, 只用【更早】的锚 ─────────────────────────────
mid_hist = defaultdict(list)          # sym -> [(ts, mid)]
vol_at = {}                           # (anchor_ts, sym) -> trailing vol bps (strictly prior)
for a in anchors:
    ts = a["anchor_ts"]
    mv = a.get("mid_at_anchor_vector") or {}
    if isinstance(mv, str):
        import json as _j
        try: mv = _j.loads(mv)
        except Exception: mv = {}
    for s, m in mv.items():
        h = mid_hist[s]
        if len(h) >= 3:
            rets = [abs(np.log(h[i + 1][1] / h[i][1])) for i in range(len(h) - 1)
                    if h[i][1] and h[i + 1][1]]
            if rets:
                vol_at[(ts, s)] = float(np.mean(rets[-6:]) * 1e4)
        if m:
            h.append((ts, m))

REG = {"calm": 0.0, "normal": 1.0, "storm": 2.0}
rows = []
for o in orders:
    fn = o.get("filled_notional") or 0.0
    px, mid = o.get("avg_fill_px"), o.get("mid_at_submit")
    side = str(o.get("side") or "").upper()
    if fn <= 0 or not px or not mid or side not in ("BUY", "SELL", "LONG", "SHORT"):
        continue
    sgn = 1.0 if side in ("BUY", "LONG") else -1.0
    slip = sgn * (float(px) - float(mid)) / float(mid) * 1e4
    if abs(slip) > 100:               # 显性坏行(错基准/坏中价), 记数不入样
        continue
    rows.append({"ts": o["anchor_ts"], "sym": o["symbol"], "slip": slip,
                 "side": sgn, "attempt": float(o.get("attempt_idx") or 1),
                 "taker": 1.0 if "topup" in str(o.get("order_type") or "").lower()
                                 or "taker" in str(o.get("order_type") or "").lower() else 0.0,
                 "notional": abs(float(o.get("intended_notional") or 0.0)),
                 "hour": (o["anchor_ts"] / 3600.0) % 24,
                 "regime": REG.get(str(o.get("_regime") or ""), np.nan)})

# regime 从锚点表补(订单行不带): 按同 anchor_ts 最近锚
ats = np.array([a["anchor_ts"] for a in anchors])
regs = [REG.get(str(a.get("regime_at_anchor") or ""), 1.0) for a in anchors]
for r in rows:
    j = int(np.searchsorted(ats, r["ts"], side="right")) - 1
    r["regime"] = regs[max(j, 0)]
    r["vol"] = vol_at.get((ats[max(j, 0)], r["sym"]), np.nan)

rows.sort(key=lambda r: r["ts"])
# 逐名 trailing 平均滑点: expanding, 只用更早的锚(同锚不入, 防同期泄漏)
sym_hist = defaultdict(list)
glob_hist = []
cur_ts = None
pend = []
for r in rows:
    if cur_ts is not None and r["ts"] != cur_ts:
        for p in pend:
            sym_hist[p["sym"]].append(p["slip"]); glob_hist.append(p["slip"])
        pend = []
    cur_ts = r["ts"]
    h = sym_hist.get(r["sym"]) or []
    r["sym_prior"] = float(np.mean(h)) if h else (float(np.mean(glob_hist)) if glob_hist else 0.0)
    pend.append(r)

n = len(rows)
y = np.array([r["slip"] for r in rows])
FEATS = ["side", "attempt", "taker", "notional", "hour", "regime", "vol", "sym_prior"]
X = np.array([[r.get(k, np.nan) for k in FEATS] for r in rows])
X = np.where(np.isfinite(X), X, np.nanmedian(X, axis=0))
print(f"样本 n={n}  滑点: mean={y.mean():+.2f} bps  sd={y.std():.2f}  "
      f"p10/p50/p90={np.percentile(y,10):+.1f}/{np.percentile(y,50):+.1f}/{np.percentile(y,90):+.1f}")

def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else np.nan

uts = sorted({r["ts"] for r in rows})
edges = [uts[int(len(uts) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
folds = []
for i, e in enumerate(edges):
    hi = edges[i + 1] if i + 1 < len(edges) else np.inf
    tr = np.array([r["ts"] < e for r in rows]); te = np.array([(r["ts"] >= e) and (r["ts"] < hi) for r in rows])
    if tr.sum() > 100 and te.sum() > 50:
        folds.append((tr, te))

oos_pred = np.full(n, np.nan)
per_fold = []
for tr, te in folds:
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
    Xtr, Xte = (X[tr] - mu) / sd, (X[te] - mu) / sd
    lam = 10.0
    A = Xtr.T @ Xtr + lam * np.eye(X.shape[1])
    w = np.linalg.solve(A, Xtr.T @ (y[tr] - y[tr].mean()))
    p = Xte @ w + y[tr].mean()
    oos_pred[te] = p
    per_fold.append((int(te.sum()), spearman(p, y[te])))

m = np.isfinite(oos_pred)
sp_all = spearman(oos_pred[m], y[m])
print(f"\n4 折 walk-forward OOS:")
for i, (nt, sp) in enumerate(per_fold):
    print(f"  折{i+1}: n={nt:4d}  Spearman={sp:+.3f}")
n_pos = sum(1 for _, sp in per_fold if sp == sp and sp > 0)
print(f"  全体 OOS Spearman = {sp_all:+.3f}   同号正折数 {n_pos}/{len(per_fold)}")

q = np.quantile(oos_pred[m], [0.2, 0.4, 0.6, 0.8])
bins = np.digitize(oos_pred[m], q)
tab = [(b, int((bins == b).sum()), float(y[m][bins == b].mean())) for b in range(5)]
print("\n按 ĉ 五档的真实滑点 (bps):")
for b, cnt, mv in tab:
    print(f"  档{b+1}(ĉ {'最低' if b==0 else '最高' if b==4 else ''}): n={cnt:4d}  真实={mv:+.2f}")
gap = tab[4][2] - tab[0][2]
print(f"  最贵档 − 最便宜档 = {gap:+.2f} bps")

directional = sp_all >= 0.10 and n_pos >= 3
decisive = gap >= 2.0
print(f"\n预注册判读: DIRECTIONAL={'PASS' if directional else 'FAIL'} "
      f"(需 ≥0.10 且 ≥3/4 折正; 得 {sp_all:+.3f}, {n_pos}/{len(per_fold)})")
print(f"            DECISIVE-for-S2a={'PASS' if decisive else 'FAIL'} (需档差 ≥2 bps; 得 {gap:+.2f})")
if not directional and not decisive:
    print("            ⇒ CANNOT USE (如实)")
json.dump({"n": n, "sp_all": sp_all, "per_fold": per_fold, "quintiles": tab, "gap": gap,
           "directional": bool(directional), "decisive": bool(decisive), "feats": FEATS},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r1_s1_result.json"), "w"),
          indent=1)
