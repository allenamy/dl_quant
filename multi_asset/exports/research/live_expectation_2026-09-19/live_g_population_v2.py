#!/usr/bin/env python3
"""实盘 g 的完整人口版(复审 R5-03 修复)。只读。

v1(live_g_decomposition.py af3d0ba1)L69–77 把「窗首空仓」的窗(gross0 = 0)从两个 g 比率里删掉, 但美元合计里保留 ——
被删的 11 窗合池净额 −594.93 USDT(合池现金损失的 23.5%), 另有两个 ≈8h 窗按一个名义 4h 窗计。窗首空仓不代表窗内没有
风险或损益(平仓后重建、手续费、重建期价格)。本版:

  人口  = 恒等式收据里的**全部** 4h NAV 窗(缺 terms 的窗 ⇒ 报错退出, 不静默跳过); 不删任何窗, 不填零。
  时长  = u_w = (t1 − t0) / 14400(4h 单位); 长窗按实际时长进分母, 不伪装成 4h。
  分母(三个, 都对全部窗有定义, 同报):
    I  意图敞口 = 该窗所属锚的 target_gross(执行器 anchors.jsonl, USDT)× u_w —— 与回放判官逐锚 gross_total(意图 gross)同构;
       平仓 / 停机后空仓的时间按意图敞口计入分母, 因为实盘确实按这个意图承担了「没持仓」的机会成本。**与回放对照用这一个。**
    H  持仓敞口 = (窗首 gross + 窗末 gross)/ 2 × u_w(梯形, 场所读回快照)—— 执行质量读法; 两端都为 0 的窗单列其现金。
    N  NAV      = 窗首 NAV(USDT 计)× u_w —— 不依赖任何 gross 假设。
  统计量(每个分母各两个):
    ratio_of_sums   = Σ_w x_w / Σ_w D_w × 1e4                        (bps / 4h / 单位分母)
    time_wtd_mean   = Σ_w u_w·(x_w / D_w) / Σ_w u_w × 1e4            (回放判官「逐锚比值的均值」的实盘对应, 长窗按时长加权)
  v1 的读数(窗首有持仓的条件 g)保留作回归对照, **改名** g_conditional_on_invested_start, 并断言逐位复现 v1 收据。
usage: live_g_population_v2.py <CASH_IDENTITY_USD.json> <v1 LIVE_G_DECOMPOSITION.json> <out.json> [from_utc=2026-08-26T00:00:00Z]"""
import bisect, calendar, collections, hashlib, json, math, os, sys, time

LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
H4 = 14400.0
ANCHOR_TOL_S = 120.0          # 锚记录 anchor_ts(≈A+24)早于 NAV 行(≈A+40); 取 anchor_ts ≤ t0 + 120 s 的最后一条


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def jl(p):
    with open(p) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main():
    rec_p, v1_p, out = sys.argv[1], sys.argv[2], sys.argv[3]
    t_from = calendar.timegm(time.strptime(sys.argv[4] if len(sys.argv) > 4 else "2026-08-26T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
    rec, v1 = json.load(open(rec_p)), json.load(open(v1_p))
    days = sorted(d for d in os.listdir(LED) if d.startswith("2026"))
    nav, rb, anc = {}, collections.defaultdict(dict), []
    for d in days:
        for r in (jl(f"{LED}/{d}/daily_nav.jsonl") if os.path.isfile(f"{LED}/{d}/daily_nav.jsonl") else []):
            if r.get("mode") in (None, "LIVE"): nav[U(r["nav_ts"])] = float(r["nav_ts"])
        for r in (jl(f"{LED}/{d}/position_readback.jsonl") if os.path.isfile(f"{LED}/{d}/position_readback.jsonl") else []):
            rb[float(r["read_ts"])][r["symbol"]] = abs(float(r["venue_position_notional"]))
        for r in (jl(f"{LED}/{d}/anchors.jsonl") if os.path.isfile(f"{LED}/{d}/anchors.jsonl") else []):
            if r.get("target_gross") is None or not math.isfinite(float(r["target_gross"])):
                raise SystemExit(f"anchor {U(r['anchor_ts'])} has no finite target_gross")
            anc.append((float(r["anchor_ts"]), float(r["target_gross"])))
    anc.sort(); at = [a for a, _ in anc]
    snaps = sorted(rb)

    def gross_at(ts):
        j = bisect.bisect_left(snaps, ts); c = [s for s in snaps[max(0, j - 2):j + 2] if abs(s - ts) <= 60]
        if not c: return None
        return sum(rb[min(c, key=lambda k: (abs(k - ts), k))].values())

    def target_at(ts):
        j = bisect.bisect_right(at, ts + ANCHOR_TOL_S) - 1
        if j < 0: raise SystemExit(f"no anchor record at or before {U(ts)}")
        return anc[j][1], at[j]

    rows = []
    for w in rec["windows_4h"]:
        if "terms" not in w: raise SystemExit(f"window {w['from']} has no terms — population not complete")
        t0, t1 = nav.get(w["from"]), nav.get(w["to"])
        if t0 is None or t1 is None: raise SystemExit(f"window {w['from']} not mapped to a NAV row")
        if t0 < t_from: continue
        g0, g1 = gross_at(t0), gross_at(t1)
        if g0 is None or g1 is None: raise SystemExit(f"no snapshot at {w['from']} / {w['to']}")
        T = w["terms"]; fl = T["flows"]
        for v in [T["mtm_and_trade_cash"], *fl.values(), *T["N"], *T["p"], *T["b"]]:
            if not math.isfinite(float(v)): raise SystemExit(f"non-finite input in window {w['from']}")
        bnb_px = T["b"][1] / 0.95
        fund = fl.get("FUNDING_FEE|USDT", 0.0)
        fee = -(fl.get("COMMISSION|USDT", 0.0) + fl.get("COMMISSION|BNB", 0.0) * bnb_px)
        xfer_usdt = fl.get("TRANSFER|USDT", 0.0) + fl.get("TRANSFER|BNB", 0.0) * bnb_px
        N0u, N1u = T["N"][0] / T["p"][0], T["N"][1] / T["p"][1]
        tg, ta = target_at(t0)
        u = (t1 - t0) / H4
        rows.append({"from": w["from"], "to": w["to"], "t0": t0, "t1": t1, "u": u, "gross0": g0, "gross1": g1,
                     "target_gross": tg, "target_anchor": U(ta), "nav0_usdt": N0u,
                     "price_trade": T["mtm_and_trade_cash"], "funding": fund, "fee": fee, "net": T["mtm_and_trade_cash"] + fund - fee,
                     "transfer_usdt": xfer_usdt, "r_nav": (N1u - xfer_usdt - N0u) / N0u})
    if not rows: raise SystemExit("empty population")
    for a, b in zip(rows, rows[1:]):
        if abs(a["t1"] - b["t0"]) > 1e-6: raise SystemExit(f"windows not contiguous at {a['to']}")

    D = {"I_intended": lambda r: r["target_gross"] * r["u"], "H_held_trapezoid": lambda r: 0.5 * (r["gross0"] + r["gross1"]) * r["u"],
         "N_nav": lambda r: r["nav0_usdt"] * r["u"]}
    comps = ("net", "price_trade", "funding", "fee")
    out_stats = {}
    for name, f in D.items():
        pop = [r for r in rows if f(r) > 0]
        zero = [r for r in rows if not f(r) > 0]
        den = sum(f(r) for r in pop); U_ = sum(r["u"] for r in pop)
        out_stats[name] = {
            "n_windows_with_positive_denominator": len(pop), "n_windows_zero_denominator": len(zero),
            "zero_denominator_cash_usdt": {k: round(sum(r[k] for r in zero), 6) for k in comps},
            "ratio_of_sums_bps_per_4h": {k: round(sum(r[k] for r in pop) / den * 1e4, 4) for k in comps},
            "time_weighted_mean_bps_per_4h": {k: round(sum(r["u"] * r[k] / f(r) for r in pop) / U_ * 1e4, 4) for k in comps},
        }
    # v1 读数(窗首有持仓的条件 g)—— 回归对照, 必须逐位复现 v1 收据
    inv = [r for r in rows if r["gross0"] > 0]
    G = sum(r["gross0"] for r in inv)
    v1_ros = {"price_and_trading": round(sum(r["price_trade"] for r in inv) / G * 1e4, 4), "funding": round(sum(r["funding"] for r in inv) / G * 1e4, 4),
              "fee": round(sum(r["fee"] for r in inv) / G * 1e4, 4)}
    per = [(r["net"] / r["gross0"] * 1e4) for r in inv]
    v1_mean = round(sum(per) / len(per), 4)
    ok_ros = all(v1_ros[k] == v1["g_bps_per_anchor_per_gross"][k] for k in v1_ros)
    ok_mean = v1_mean == v1["g_mean_of_anchor_ratios"]["g_net"]
    ok_n = (len(rows), len(inv)) == (v1["n_windows"], v1["n_windows_invested"])
    if not (ok_ros and ok_mean and ok_n):
        raise SystemExit(f"regression control FAILED: v1 reading not reproduced ({v1_ros} / {v1_mean} / {len(rows)},{len(inv)})")
    flat_start = [r for r in rows if not r["gross0"] > 0]
    long_w = [r for r in rows if r["u"] > 1.05 or r["u"] < 0.95]
    doc = {"receipt": "LIVE_G_POPULATION_v2", "device_sha256": sha(os.path.abspath(__file__)),
           "inputs": {"cash_identity": {"file": os.path.basename(rec_p), "sha256": sha(rec_p)},
                      "v1_receipt": {"file": os.path.basename(v1_p), "sha256": sha(v1_p)},
                      "live_ledger": LED + " (daily_nav / position_readback / anchors.jsonl, read-only)"},
           "utc": time.strftime("%FT%TZ", time.gmtime()), "from": rows[0]["from"], "to": rows[-1]["to"],
           "population": {"n_windows": len(rows), "total_4h_units": round(sum(r["u"] for r in rows), 4),
                          "n_flat_start_windows": len(flat_start), "n_windows_not_4h": len(long_w),
                          "cash_total_usdt": {k: round(sum(r[k] for r in rows), 6) for k in comps},
                          "flat_start_cash_usdt": {k: round(sum(r[k] for r in flat_start), 6) for k in comps},
                          "flat_start_windows": [{k: r[k] for k in ("from", "to", "u", "gross0", "gross1", "target_gross", "price_trade", "funding", "fee", "net")} for r in flat_start],
                          "non_4h_windows": [{k: r[k] for k in ("from", "to", "u", "gross0", "gross1", "net")} for r in long_w]},
           "g_by_denominator": out_stats,
           "g_conditional_on_invested_start": {"ratio_of_sums": v1_ros, "mean_of_window_ratios_net": v1_mean, "n_windows": len(inv),
                                                "note": "= v1 reading, renamed (R5-03); reproduced exactly from v1 receipt: " + str(ok_ros and ok_mean and ok_n),
                                                "not_for": "live-vs-replay comparison (drops flat-start windows' cash; treats long windows as 4h)"},
           "nav_level_unchanged": "NAV compounding in v1 already covered all windows; not recomputed here",
           "windows": rows}
    with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(out + ".part", out)
    print(json.dumps({k: doc[k] for k in ("from", "to", "g_by_denominator", "g_conditional_on_invested_start")}, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in doc["population"].items() if k not in ("flat_start_windows", "non_4h_windows")}, indent=1))
    for r in flat_start: print("flat-start", r["from"], "→", r["to"], f"u={r['u']:.2f} g0={r['gross0']:.0f} g1={r['gross1']:.0f} tg={r['target_gross']:.0f} net={r['net']:.2f}")
    for r in long_w: print("non-4h", r["from"], "→", r["to"], f"u={r['u']:.3f} net={r['net']:.2f}")


if __name__ == "__main__":
    main()
