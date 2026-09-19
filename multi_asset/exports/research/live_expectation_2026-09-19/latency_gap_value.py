#!/usr/bin/env python3
"""锚 → 成交之间约 24 分钟延迟的价格代价(只读; 价格路径 = 生产者 5m 面板, 与 P-C2 同一引擎 pnl_path.Panel)。

问题: 实盘每锚 A 的新目标在 A+~23 分钟才由执行器下单(t_d = 该次再平衡最早的 submit_ts)。这段时间里账户拿着的是【旧书】。
      若新书早一点上(exec_n6 Phase 2 沙箱: combo 落盘 N+2.2–2.5 分钟), 会差多少?
定义(逐锚, USDT, 只价格, 不含费用/资金费/冲击成本):
  旧书 Old = A 之前最近一次持仓回读的逐名数量 q(回读时刻的标记价 → 面板指数外推), 在 [b1, b2] 上的价值变化 Σ q·(P(b2) − P(b1))
  新书 New = 生产者意图 L0(target_live/{A}.json 权重 / gross_norm × sizing.gross, 与 pnl_path.window_pnl 同式)按锚时名义持有,
             在 [b1, b2] 上的价值变化 Σ L0n·(idx(b2) − idx(b1)) / idx(b_A)
  上界  = Σ_A [New − Old] 在 [ceil(A), ceil(t_d)] (目标在 A 时刻并不存在 —— 这是不可达的上界)
  可达  = Σ_A [New − Old] 在 [ceil(A + 180 s), ceil(t_d)] (Phase 2 的时点)
  交叉校验: Old 在 [ceil(A), ceil(t_d)] 与 P-C2 的缺口段 L3(同一面板、同一区间)逐锚比较; 差异大 ⇒ 本装置的旧书近似不可信, 结论作废。
面板缺行/非有限 ⇒ 该名删失(记名义), 不当 0。缺口内的成交(罕见)不进旧书, 计数报出。
usage: latency_gap_value.py <pc2_dir> <out.json>"""
import collections, glob, hashlib, json, math, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "docs", "fixprogram_2026-09-13", "FP3_devices", "pc"))
import pnl_path as PP

PH2_S = 180.0


def main():
    pc2_dir, out = sys.argv[1], sys.argv[2]
    panel = PP.Panel(); rows = []; cens = collections.Counter()
    for p in sorted(glob.glob(os.path.join(pc2_dir, "PC2_v6_2026*.json"))):
        d = json.load(open(p)); day = d["day"]; L = PP.LedgerDay(day)
        gaps = {int(g["gap_for_anchor"]): g for g in d["gaps"]}
        for a in d["anchors"]:
            A = int(a["anchor"]); g = gaps.get(A)
            if a.get("status") != "OK" or not g or g.get("status") != "GAP_OK": continue
            t_d = float(a["t_decision"]); bA = PP.ceil_b(A); bS = PP.ceil_b(A + PH2_S); bD = PP.ceil_b(t_d)
            pa = L.pa.get(A); rid = pa["rebalance_id"]; G = float(pa["sizing"]["gross"])
            anr = [r for r in L.an if r.get("rebalance_id") == rid][-1]; gn = float(anr["external_book"]["gross_norm"])
            tf = f"{PP.WS}/state/target_live/{A}.json"
            if not os.path.exists(tf): cens["no_target_file"] += 1; continue
            L0n = {s: float(w) / gn * G for s, w in json.load(open(tf))["weights"].items()}
            new_full = new_ph2 = 0.0; c_new = 0.0
            for s, n in L0n.items():
                ix = panel.index(s, bA, bA, bD)
                if ix is None or any(not math.isfinite(v) for v in ix.values()): c_new += abs(n); continue
                new_full += n * (ix[bD] - ix[bA]); new_ph2 += n * (ix[bD] - ix[bS])
            prev = L.latest_read_before(A)
            old_full = old_ph2 = 0.0; c_old = 0.0
            for s, r in prev.items():
                q = float(r["venue_position_qty"])
                if q == 0: continue
                mk = abs(float(r["venue_position_notional"])) / abs(q); bR = PP.ceil_b(float(r["read_ts"]))
                lo = min(bR, bA)
                ix = panel.index(s, bR, lo, bD)
                if ix is None or any(not math.isfinite(v) for v in ix.values()): c_old += abs(q) * mk; continue
                P = lambda b: mk * ix[b]
                old_full += q * (P(bD) - P(bA)); old_ph2 += q * (P(bD) - P(bS))
            n_fills_gap = sum(1 for f in L.fills if A < float(f["fill_ts"]) < t_d)
            rows.append({"anchor": A, "utc": a["utc"], "window_class": a.get("window_class"), "gap_s": round(t_d - A, 1), "G": G,
                         "new_full": new_full, "old_full": old_full, "new_ph2": new_ph2, "old_ph2": old_ph2,
                         "pc2_gap_L3": g["pnl_usdt"], "check_old_minus_pc2": old_full - g["pnl_usdt"],
                         "censored_new_notional": c_new, "censored_old_notional": c_old, "n_fills_in_gap": n_fills_gap})
    S = lambda k: sum(r[k] for r in rows)
    Gsum = S("G")
    # UTC 日块自举(判官同规则: 2000 次, 基种子 20260905), 统计量 = Σ(New−Old) / ΣG × 1e4
    import numpy as np
    day = np.array([time.strftime("%Y-%m-%d", time.gmtime(r["anchor"])) for r in rows]); days = sorted(set(day))
    cis = {}
    for lab, kn, ko in (("upper_bound", "new_full", "old_full"), ("phase2", "new_ph2", "old_ph2")):
        num = np.array([r[kn] - r[ko] for r in rows]); den = np.array([r["G"] for r in rows])
        byd = {d_: (num[day == d_].sum(), den[day == d_].sum()) for d_ in days}
        rng = np.random.default_rng([20260905, 7]); bs = []
        for _ in range(2000):
            pick = rng.integers(0, len(days), len(days)); n_ = sum(byd[days[i]][0] for i in pick); d_ = sum(byd[days[i]][1] for i in pick)
            bs.append(n_ / d_ * 1e4)
        cis[lab] = [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]
    doc = {"receipt": "LATENCY_GAP_VALUE", "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "engine_sha256": hashlib.sha256(open(PP.__file__, "rb").read()).hexdigest(), "panel_sha": panel.sha,
           "utc": time.strftime("%FT%TZ", time.gmtime()), "n_anchors": len(rows), "skipped": dict(cens),
           "median_gap_s": sorted(r["gap_s"] for r in rows)[len(rows) // 2] if rows else None,
           "totals_usdt": {"new_minus_old_upper_bound": round(S("new_full") - S("old_full"), 2), "new_minus_old_phase2": round(S("new_ph2") - S("old_ph2"), 2),
                           "new_full": round(S("new_full"), 2), "old_full": round(S("old_full"), 2), "pc2_gap_L3": round(S("pc2_gap_L3"), 2)},
           "per_anchor_per_gross_bps": {"upper_bound": round((S("new_full") - S("old_full")) / Gsum * 1e4, 4),
                                        "phase2": round((S("new_ph2") - S("old_ph2")) / Gsum * 1e4, 4),
                                        "ci95_day_block": cis, "n_days": len(days),
                                        "note": "Σ over anchors / Σ sizing gross — comparable in unit to g (ratio of sums); CI = UTC-day block bootstrap 2000, rng([20260905,7])"},
           "cross_check_old_vs_pc2": {"sum_abs_diff": round(sum(abs(r["check_old_minus_pc2"]) for r in rows), 2),
                                      "max_abs_diff": round(max((abs(r["check_old_minus_pc2"]) for r in rows), default=0.0), 2),
                                      "sum_abs_pc2": round(sum(abs(r["pc2_gap_L3"]) for r in rows), 2)},
           "censored_notional_sum": {"new": round(S("censored_new_notional"), 2), "old": round(S("censored_old_notional"), 2)},
           "n_anchors_with_fills_in_gap": sum(1 for r in rows if r["n_fills_in_gap"]),
           "boundary": "price only; no fees, funding or impact; the upper bound assumes the target exists at the anchor instant (it does not); in-gap fills are not applied to the old book",
           "rows": rows}
    with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(out + ".part", out)
    print(json.dumps({k: v for k, v in doc.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
