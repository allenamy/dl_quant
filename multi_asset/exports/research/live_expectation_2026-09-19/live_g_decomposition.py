#!/usr/bin/env python3
"""实盘书的 g 分解 —— 与真实成本回放(PER_YEAR_TABLE_REALCOST)逐项同口径对照。只读。

回放的分解(fp2_per_year_table.py): g = pnl − carry − cost, 单位 bps / 锚 / 单位 gross;
  pnl = 价格收益(RAW), carry = 付出的资金费(正数 = 付出), cost = 手续费(按成本档)。
本装置对实盘做同一件事, 每个 4 小时 NAV 窗(相邻两行 daily_nav, 两端有同次调用的持仓快照):
  价格与成交 = Σ_s(q1·mk1 − q0·mk0) − Σ_成交 sgn·quoteQty     (USDT; 含执行滑点与平仓, 来自现金恒等式收据)
  资金费     = 窗内场所 FUNDING_FEE 流水(USDT, 负 = 付出)
  手续费     = 窗内场所 COMMISSION 流水(USDT + BNB × BNBUSD 指数; BNB 按市价, 不打保证金折)
  gross0     = 窗首快照 Σ|名义|(USDT)
  g_x = Σ_窗 x / Σ_窗 gross0 × 1e4      (比值的和, 与回放 net_ex / gross_total 同构)
这些量全部来自已闭合的现金恒等式收据(49/49 日窗; 见 docs/RESULT_cash_closure_per_trade_2026-09-19.md 及其复审限定),
所以实盘这一侧的数字是【场所现金】, 不是回放, 也不是目标权重。

另出 NAV 层实现收益(USDT 计, 去掉划转与 USD 重估): r = (N1/p1 − 外部划转 − N0/p0) / (N0/p0), p = USDTUSD 指数 × 0.9999。
usage: live_g_decomposition.py <CASH_IDENTITY_USD.json> <out.json> [from_utc=2026-08-26T00:00:00Z]"""
import bisect, calendar, collections, hashlib, json, math, os, sys, time

LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))


def main():
    rec_p, out = sys.argv[1], sys.argv[2]
    t_from = calendar.timegm(time.strptime(sys.argv[3] if len(sys.argv) > 3 else "2026-08-26T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
    rec = json.load(open(rec_p))
    days = sorted(d for d in os.listdir(LED) if d.startswith("2026"))
    nav = {}
    for d in days:
        p = f"{LED}/{d}/daily_nav.jsonl"
        if os.path.isfile(p):
            for l in open(p):
                if l.strip():
                    r = json.loads(l)
                    if r.get("mode") in (None, "LIVE"): nav[U(r["nav_ts"])] = float(r["nav_ts"])
    rb = collections.defaultdict(dict)
    for d in days:
        p = f"{LED}/{d}/position_readback.jsonl"
        if os.path.isfile(p):
            for l in open(p):
                if l.strip():
                    r = json.loads(l); rb[float(r["read_ts"])][r["symbol"]] = abs(float(r["venue_position_notional"]))
    snaps = sorted(rb)

    def gross_at(ts):
        j = bisect.bisect_left(snaps, ts); c = [s for s in snaps[max(0, j - 2):j + 2] if abs(s - ts) <= 60]
        if not c: return None
        return sum(rb[min(c, key=lambda k: (abs(k - ts), k))].values())
    rows = []
    for w in rec["windows_4h"]:
        if "terms" not in w: continue
        t0, t1 = nav.get(w["from"]), nav.get(w["to"])
        if t0 is None or t1 is None: raise SystemExit(f"window {w['from']} not mapped to a NAV row")
        if t0 < t_from: continue
        g0 = gross_at(t0)
        if g0 is None: raise SystemExit(f"no snapshot at {w['from']}")
        T = w["terms"]; fl = T["flows"]
        for v in [T["mtm_and_trade_cash"], *fl.values(), *T["N"], *T["p"], *T["b"]]:
            if not math.isfinite(float(v)): raise SystemExit(f"non-finite input in window {w['from']}")
        bnb_px = T["b"][1] / 0.95                               # 市价(不打折)计手续费成本
        fund = fl.get("FUNDING_FEE|USDT", 0.0)
        fee = -(fl.get("COMMISSION|USDT", 0.0) + fl.get("COMMISSION|BNB", 0.0) * bnb_px)
        xfer_usdt = fl.get("TRANSFER|USDT", 0.0) + fl.get("TRANSFER|BNB", 0.0) * bnb_px
        N0u, N1u = T["N"][0] / T["p"][0], T["N"][1] / T["p"][1]
        r_nav = (N1u - xfer_usdt - N0u) / N0u if N0u else None
        rows.append({"from": w["from"], "to": w["to"], "t0": t0, "gross0": g0, "nav0_usdt": N0u, "price_trade": T["mtm_and_trade_cash"],
                     "funding": fund, "fee": fee, "transfer_usdt": xfer_usdt, "r_nav": r_nav, "residual_primary": w.get("residual_primary"),
                     "cash_ok": w.get("ok")})
    G = sum(r["gross0"] for r in rows if r["gross0"] > 0)
    inv = [r for r in rows if r["gross0"] > 0]
    agg = lambda k: sum(r[k] for r in inv) / G * 1e4
    g_price, g_fund, g_fee = agg("price_trade"), agg("funding"), agg("fee")
    g = g_price + g_fund - g_fee
    # 回放判官 fp2_per_year_table.py L33/L72 的定义: g = mean_anchor(net_ex / gross_total) —— 逐锚比值的均值(不是比值的和)。
    #   两个定义都报, 与回放对照只用这一个。空仓窗(gross0 = 0)的逐锚比值无定义, 不进均值(回放没有整书平仓; 实盘的空仓时间在 NAV 层体现)。
    per = [((r["price_trade"] + r["funding"] - r["fee"]) / r["gross0"] * 1e4, r["price_trade"] / r["gross0"] * 1e4,
            r["funding"] / r["gross0"] * 1e4, r["fee"] / r["gross0"] * 1e4) for r in inv]
    mg = [sum(x[i] for x in per) / len(per) for i in range(4)]
    # 按日(UTC, 窗首所在日)的 NAV 收益, 复利
    byday = collections.defaultdict(list)
    for r in rows: byday[time.strftime("%Y-%m-%d", time.gmtime(r["t0"]))].append(r["r_nav"])
    dret = {d: math.prod(1 + x for x in v) - 1 for d, v in sorted(byday.items())}
    dv = list(dret.values()); n = len(dv)
    mu = sum(dv) / n; sd = (sum((x - mu) ** 2 for x in dv) / (n - 1)) ** 0.5
    nav_path = [1.0]
    for r in rows: nav_path.append(nav_path[-1] * (1 + r["r_nav"]))
    peak, mdd = 1.0, 0.0
    for v in nav_path: peak = max(peak, v); mdd = min(mdd, v / peak - 1)
    doc = {"receipt": "LIVE_G_DECOMPOSITION", "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "cash_identity_receipt": os.path.basename(rec_p), "cash_identity_sha256": hashlib.sha256(open(rec_p, "rb").read()).hexdigest(),
           "utc": time.strftime("%FT%TZ", time.gmtime()), "from": U(rows[0]["t0"]), "to": rows[-1]["to"],
           "n_windows": len(rows), "n_windows_invested": len(inv), "n_windows_flat": len(rows) - len(inv),
           "g_bps_per_anchor_per_gross": {"price_and_trading": round(g_price, 4), "funding": round(g_fund, 4), "fee": round(g_fee, 4),
                                          "g_net": round(g, 4), "mean_gross0_usdt": round(G / len(inv), 2),
                                          "definition": "ratio of sums Σx/Σgross0"},
           "g_mean_of_anchor_ratios": {"g_net": round(mg[0], 4), "price_and_trading": round(mg[1], 4), "funding": round(mg[2], 4), "fee": round(mg[3], 4),
                                       "definition": "mean over invested windows of x/gross0 — the replay judge's definition (fp2_per_year_table.py L33, L72)",
                                       "per_window_g": [round(x[0], 4) for x in per]},
           "replay_field_mapping": "replay pnl ≈ price_and_trading; replay carry ≈ −funding; replay cost ≈ fee",
           "nav_level": {"n_days": n, "cum_return": round(nav_path[-1] - 1, 6), "mean_daily": round(mu, 6), "sd_daily": round(sd, 6),
                         "sharpe_daily_ann": round(mu / sd * math.sqrt(365), 3) if sd else None,
                         "sharpe_se_iid": round(math.sqrt((365 + (mu / sd * math.sqrt(365)) ** 2 / 2) / n), 3) if sd else None,
                         "maxdd_4h_path": round(mdd, 6), "worst_day": round(min(dv), 6)},
           "daily_returns": {k: round(v, 6) for k, v in dret.items()}, "windows": rows}
    with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(out + ".part", out)
    print(json.dumps({k: (doc[k] if k != "g_mean_of_anchor_ratios" else {kk: vv for kk, vv in doc[k].items() if kk != "per_window_g"})
                      for k in ("from", "to", "n_windows", "n_windows_invested", "n_windows_flat", "g_bps_per_anchor_per_gross", "g_mean_of_anchor_ratios", "nav_level")}, indent=1))


if __name__ == "__main__":
    main()
