"""R1-v1 · maker 成交概率 —— 锚级 walk-forward。

v0 判负后的两个改变(#33 记录): ① 标签换成【成交/不成交】二值(基率友好) ② 头号特征
`spread_at_submit_bps` 已落地。第三个改变来自今日实测: 成交比例是【双峰近二值】的
(72.2% 全成 / 14.8% 全不成 / 中间仅 ~13%), 所以二值化不是简化, 是它本来的形状。

★ 判据(写死于跑之前):
  主判 : OOS AUC ≥ 0.60 且 ≥3/4 折 > 0.55
  副判 : 预测最高五分位 vs 最低五分位的【实测不成交率】差 ≥ 15 个百分点
  ★增量: 必须【超过仅用 |notional| 的平凡基线】—— 小单更容易成交是已知的, 不算发现
  ★会红: 若 AUC ≈ 0.5 ⇒ 提交时刻信息不预测成交 ⇒ R2 的 ĉ 维持【确定性】(仅费用),
         那正是 #33 已登记的退路, 不算失败, 算把退路钉死。
  ★有效样本 = 锚不是订单(v0 的头号教训) ⇒ 折按锚切, 绝不打乱订单。
"""
import json, glob, numpy as np, datetime as dt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
rows = []
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("order_type") != "maker" or d.get("terminal_reason") != "partial_expired":
            continue
        it, fn = d.get("intended_notional"), d.get("filled_notional")
        if it is None or fn is None or abs(it) < 1e-9:
            continue
        ff = abs(fn)/abs(it)
        rows.append({
            "rid": d.get("rebalance_id"), "ts": d.get("anchor_ts") or 0,
            "y": 1.0 if ff < 0.01 else 0.0,                       # 1 = 完全没成交(贵的那一侧)
            "notl": abs(float(it)),
            "side": 1.0 if str(d.get("side", "")).lower().startswith("b") else 0.0,
            "attempt": float(d.get("attempt_idx") or 1),
            "spread": d.get("spread_at_submit_bps"),
            "mid": float(d.get("mid_at_anchor") or np.nan),
            "regime": str(d.get("_regime") or ""),
        })
rows.sort(key=lambda r: r["ts"])
anchors = sorted({r["rid"] for r in rows}, key=lambda a: min(r["ts"] for r in rows if r["rid"] == a))
print(f"订单 {len(rows)}  锚 {len(anchors)}  不成交基率 {np.mean([r['y'] for r in rows]):.3f}")

FEAT_BASE = ["log_notl"]
FEAT_FULL = ["log_notl", "side", "attempt", "log_mid", "hour_sin", "hour_cos"]
FEAT_SPR = FEAT_FULL + ["spread"]


def design(rs, cols):
    X = []
    for r in rs:
        h = (dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).hour) if r["ts"] else 0
        d = {"log_notl": np.log1p(r["notl"]), "side": r["side"], "attempt": r["attempt"],
             "log_mid": np.log1p(max(r["mid"], 1e-9)) if np.isfinite(r["mid"]) else 0.0,
             "hour_sin": np.sin(2*np.pi*h/24), "hour_cos": np.cos(2*np.pi*h/24),
             "spread": float(r["spread"]) if r["spread"] is not None else np.nan}
        X.append([d[c] for c in cols])
    return np.array(X, float), np.array([r["y"] for r in rs])


def walkforward(rs, cols, K=4, tag=""):
    an = sorted({r["rid"] for r in rs}, key=lambda a: min(x["ts"] for x in rs if x["rid"] == a))
    if len(an) < K + 2:
        print(f"  [{tag}] 锚数 {len(an)} 不足, 跳过"); return None
    bounds = [int(len(an)*i/(K+1)) for i in range(1, K+2)]
    aucs, spreads = [], []
    for k in range(K):
        tr_a = set(an[:bounds[k]]); te_a = set(an[bounds[k]:bounds[k+1]])
        tr = [r for r in rs if r["rid"] in tr_a]; te = [r for r in rs if r["rid"] in te_a]
        if len(tr) < 50 or len(te) < 20: continue
        Xtr, ytr = design(tr, cols); Xte, yte = design(te, cols)
        if len(set(ytr)) < 2 or len(set(yte)) < 2: continue
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(max_iter=2000, C=1.0).fit(sc.transform(Xtr), ytr)
        p = m.predict_proba(sc.transform(Xte))[:, 1]
        aucs.append(roc_auc_score(yte, p))
        q = np.quantile(p, [0.2, 0.8])
        lo = yte[p <= q[0]].mean() if (p <= q[0]).sum() else np.nan
        hi = yte[p >= q[1]].mean() if (p >= q[1]).sum() else np.nan
        spreads.append(hi - lo)
    if not aucs: return None
    print(f"  [{tag}] 折 AUC {[round(a,3) for a in aucs]}  均值 {np.mean(aucs):.4f}  "
          f"五分位不成交率差 {np.nanmean(spreads)*100:+.1f}pp", flush=True)
    return {"auc_folds": [round(a, 4) for a in aucs], "auc_mean": round(float(np.mean(aucs)), 4),
            "quintile_spread_pp": round(float(np.nanmean(spreads))*100, 2),
            "n_folds_gt_055": int(sum(1 for a in aucs if a > 0.55))}


print("\n=== 全样本(spread 缺失, 用 FEAT_FULL) ===")
r_base = walkforward(rows, FEAT_BASE, tag="平凡基线 |notional|")
r_full = walkforward(rows, FEAT_FULL, tag="提交时特征(无 spread)")

sp_rows = [r for r in rows if r["spread"] is not None]
print(f"\n=== 带 spread 的子样本 n={len(sp_rows)} 锚={len({r['rid'] for r in sp_rows})} ===")
r_sb = walkforward(sp_rows, FEAT_BASE, tag="平凡基线 |notional|")
r_sf = walkforward(sp_rows, FEAT_FULL, tag="无 spread")
r_ss = walkforward(sp_rows, FEAT_SPR, tag="★ 加 spread")

print("\n===== 判据 =====")
for nm, r in [("全样本 提交时特征", r_full), ("子样本 加 spread", r_ss)]:
    if not r: print(f"  {nm}: 无结果"); continue
    g1 = r["auc_mean"] >= 0.60 and r["n_folds_gt_055"] >= 3
    g2 = r["quintile_spread_pp"] >= 15
    print(f"  {nm}: AUC {r['auc_mean']:.4f} ({r['n_folds_gt_055']}/{len(r['auc_folds'])} 折>0.55) "
          f"五分位差 {r['quintile_spread_pp']:+.1f}pp  ⇒ 主判 {'PASS' if g1 else 'FAIL'} / 副判 {'PASS' if g2 else 'FAIL'}")
if r_ss and r_sb:
    print(f"  ★增量 vs 平凡基线(子样本): AUC {r_sb['auc_mean']:.4f} → {r_ss['auc_mean']:.4f} "
          f"(Δ{r_ss['auc_mean']-r_sb['auc_mean']:+.4f})")
if r_ss and r_sf:
    print(f"  ★spread 自身增量: {r_sf['auc_mean']:.4f} → {r_ss['auc_mean']:.4f} "
          f"(Δ{r_ss['auc_mean']-r_sf['auc_mean']:+.4f})")
json.dump({"base": r_base, "full": r_full, "spr_base": r_sb, "spr_nospread": r_sf, "spr_with": r_ss,
           "n_orders": len(rows), "n_anchors": len(anchors)},
          open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/r1v1_fill.json", "w"), indent=1)
print("\nR1V1_DONE")
