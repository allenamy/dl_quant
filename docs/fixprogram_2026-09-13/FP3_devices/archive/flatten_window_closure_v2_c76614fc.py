#!/usr/bin/env python3
"""FP3 · 平仓桶【逐笔】现金闭合 —— 独立研究员第三轮建议 §8-3「平仓桶逐笔现金闭合」。只读。

为什么要这件装置(而不是再算一张 ±120 s 窗的表):
  CASH_RECON v6 的 09-05 20:43 → 09-06 20:39 日窗残差 +2,229.28 USD、238 个持仓缺口。上一版只做到「残差与缺口【共现】」,
  复审明确指出「共现不是归因」。要把它变成归因, 必须逐笔证明:
    (a) 缺口里的每一个名, 其数量变化 = 场所逐笔成交之和(一个名都不能靠推);
    (b) 残差的每一分钱 = 账本缺失的那些成交的现金 + 手续费(身份到 (symbol, trade id));
    (c) 两个互相独立的场所端点(userTrades 与 income)在同一窗口上给出同一个手续费 / 已实现盈亏。
  三条都过, 才叫「闭合」; 任一条缺数据, 整体 UNAVAILABLE(rc 3), 不出部分数。

窗口规则 —— 与 ±120 s 桶的根本区别:
  这里的窗口是【两行 NAV 之间】(t0, t1], 两端都有与 NAV 同一次账户调用的持仓快照(|Δt| ≤ 60 s, fp3 同规则)。
  它不是「围绕某个事件的归因选择」, 而是一个【会计恒等式成立的区间】: 区间内所有流量都必须被找到, 否则残差不为零。
  日窗在 daily_nav 里其实每 4 小时就有一行 —— 用最细的相邻两行把日窗拆开, 平仓落在哪个 4 小时里就只查那一段。

恒等式(与 fp3_cash_recon.py v5 §3 逐字同义):
  ΔNAV − 外部划转 = Σ_s [q1·mk1 − q0·mk0 − Σ_账本成交 sgn·q·px] + 资金费 − 账本手续费 + 残差
  若账本缺了某些成交, 则  残差 = −Σ_缺失成交 sgn·quoteQty − Σ_缺失成交 手续费(USDT 等值)。
  这是可证伪的: 预测残差与实测残差之差必须落在 fp3 同一容差 max(2 USDT, 0.5 bp·NAV) 内。

已声明的边界(不静默):
  - 09-06 的平仓单【没有我们的 clientOrderId】, 当时也【没记场所 orderId】(执行器 binance_broker.py 的注释自述, 该字段是后来补的)。
    ⇒ 订单身份只能靠「本窗内每个 (symbol, side) 场所只有一个 orderId」+「执行器本窗只有 protective_flatten 单」这两条唯一性来对上。
    装置【测量】这两条唯一性, 不假设。
  - BNB 计价手续费按当日收盘价折 USDT(与 fp3 一致); NAV 若计入 BNB 余额的重估, 那一项不在恒等式里 —— 本窗若闭合, 说明它在本窗可忽略;
    不闭合时它是候选之一, 装置不替它背书。
usage: flatten_window_closure.py <t0_nav_ts> <t1_nav_ts> <out.json> [raw_trades_out.json]"""
import collections, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
import fills_reader as FR                                   # 规范成交读者: (symbol, trade_id) 坍缩, 金额取一次
VERSION = "v2-2026-09-19"   # v2: 订单身份按 (symbol, side, 首/末成交毫秒) 对齐 + 账本已记成交逐笔金额核对
LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
SNAP_TOL_S = 60.0
BNB_P = os.path.join(HERE, "..", "FP3_receipts", "BNBUSDT_daily_20260801_20260918.json")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
DAY = lambda t: time.strftime("%Y%m%d", time.gmtime(float(t)))


def rows(day, name):
    p = f"{LED}/{day}/{name}.jsonl"
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []


def main():
    t0, t1, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    raw_out = sys.argv[4] if len(sys.argv) > 4 else out.replace(".json", "_venue_trades.json")
    assert t1 > t0
    days = sorted({DAY(t0 - 86400), DAY(t0), DAY(t1), DAY(t1 + 86400)})
    days = [d for d in days if os.path.isdir(f"{LED}/{d}")]
    inputs = {f"{d}/{n}": hashlib.sha256(open(f"{LED}/{d}/{n}.jsonl", "rb").read()).hexdigest()[:16]
              for d in days for n in ("fills", "orders", "funding", "position_readback", "daily_nav")
              if os.path.isfile(f"{LED}/{d}/{n}.jsonl")}
    BNB = {d: v["close"] for d, v in json.load(open(BNB_P))["days"].items()}

    def fee_usdt(asset, c, ts):
        if asset == "USDT": return c
        if asset == "BNB": return c * BNB[DAY(ts)]           # KeyError = 不可判, 不猜
        raise ValueError(f"commission asset {asset}")

    # ── A. 本地恒等式(fp3 §3 同义) ──
    nav = {float(r["nav_ts"]): r for d in days for r in rows(d, "daily_nav") if r.get("mode") in (None, "LIVE")}
    r0, r1 = nav.get(t0), nav.get(t1)
    if r0 is None or r1 is None:
        print("REFUSED: t0/t1 必须是 daily_nav 的 nav_ts 原值"); return 2
    between = sorted(t for t in nav if t0 < t < t1)
    if between:
        print(f"REFUSED: (t0,t1) 之间还有 {len(between)} 行 NAV —— 用相邻两行, 否则恒等式区间不是最细的"); return 2
    rb = [r for d in days for r in rows(d, "position_readback")]

    def snap(ts):
        c = collections.defaultdict(list)
        for r in rb:
            if abs(float(r["read_ts"]) - ts) <= SNAP_TOL_S: c[float(r["read_ts"])].append(r)
        if not c: return None, None
        st = min(c, key=lambda k: (abs(k - ts), k)); m = {}
        for r in c[st]:
            q = float(r["venue_position_qty"])
            if r["symbol"] in m and m[r["symbol"]][0] != q: return None, "CONFLICT"
            m[r["symbol"]] = (q, abs(float(r["venue_position_notional"])) / abs(q) if q else 0.0)
        return m, st
    m0, s0 = snap(t0); m1, s1 = snap(t1)
    if m0 is None or m1 is None:
        print("UNAVAILABLE: 端点无同次调用的持仓快照", s0, s1); return 3
    fills = [f for f in FR.read_range(day_list=days) if t0 < float(f["fill_ts"]) <= t1]
    sgn = lambda side: 1.0 if str(side).upper() == "BUY" else -1.0
    cash = collections.defaultdict(float); q_rec = collections.defaultdict(float)
    for f in fills:
        q = float(f["fill_notional"]) / float(f["fill_px"]) * sgn(f["side"])
        cash[f["symbol"]] += q * float(f["fill_px"]); q_rec[f["symbol"]] += q
    names_local = set(m0) | set(m1) | set(q_rec)
    term = sum(m1.get(s, (0, 0))[0] * m1.get(s, (0, 0))[1] - m0.get(s, (0, 0))[0] * m0.get(s, (0, 0))[1] - cash[s] for s in names_local)
    FUND = [x for d in days for x in rows(d, "funding") if t0 < float(x["settlement_ts"]) <= t1]
    fund = sum(float(x.get("funding_paid") or 0.0) for x in FUND)
    fees_led = sum(fee_usdt(f.get("commission_asset"), float(f.get("commission") or 0.0), f["fill_ts"]) for f in fills)
    dnav = float(r1["nav"]) - float(r1.get("external_flow_usdt") or 0.0) - float(r0["nav"])
    resid = dnav - (term + fund - fees_led)
    tol = max(2.0, 0.5e-4 * float(r0["nav"]))
    gaps = {s: (m0.get(s, (0, 0))[0] + q_rec[s]) - m1.get(s, (0, 0))[0] for s in names_local}
    gaps = {s: g for s, g in gaps.items() if abs(g) * (m1.get(s, (0, 0))[1] or m0.get(s, (0, 0))[1] or 1.0) > 1.0}
    A = {"t0": U(t0), "t1": U(t1), "snapshot_minus_nav_s": [round(s0 - t0, 3), round(s1 - t1, 3)],
         "n_pos_t0": sum(1 for v in m0.values() if v[0]), "n_pos_t1": sum(1 for v in m1.values() if v[0]),
         "dnav_ex_flow": round(dnav, 4), "mtm_positions_and_fills": round(term, 4), "funding_local": round(fund, 4),
         "fees_ledger": round(fees_led, 4), "residual": round(resid, 4), "tol": round(tol, 4),
         "n_ledger_fills": len(fills), "n_position_gaps_gt_1usd": len(gaps)}
    print("A 本地恒等式:", json.dumps(A, ensure_ascii=False))

    # 执行器本窗的订单(按 submit_ts 或 first_fill_ts 落在窗内)
    ords = [o for d in days for o in rows(d, "orders")
            if any(o.get(k) is not None and t0 < float(o[k]) <= t1 for k in ("submit_ts", "first_fill_ts"))]
    ord_types = collections.Counter(o.get("order_type") for o in ords)
    print("  执行器本窗订单:", dict(ord_types))

    # ── B. 场所(只读密钥): income 全品种 + 逐名 userTrades ──
    import fetch_trades as FT, fetch_income_paged as FI
    s_ms, e_ms = int(t0 * 1000) + 1, int(t1 * 1000)          # (t0, t1] 的毫秒闭区间近似; 端点各差 <1 ms, 快照与 NAV 同刻(Δ 0.0 s)
    ipages, irows, istatus, iwhy, isub = FI.run(s_ms, e_ms, "closure")
    if istatus != "COMPLETE":
        print("UNAVAILABLE: income 拉取不完整:", iwhy); return 3
    inc_syms = {r["symbol"] for r in irows if r.get("symbol") and r["incomeType"] in ("COMMISSION", "REALIZED_PNL")}
    names = sorted(names_local | inc_syms)
    per, bad, trades = {}, [], []
    for i, s in enumerate(names, 1):
        pages, rs, st, why = FT.fetch_trades(s, s_ms, e_ms)
        if st != "COMPLETE": bad.append((s, why)); continue
        trades += rs
        if i % 40 == 0: print(f"    trades {i}/{len(names)}", flush=True)
    if bad:
        print("UNAVAILABLE: 以下品种 userTrades 不完整:", bad[:10]); return 3
    raw_doc = {"device": f"flatten_window_closure.py {VERSION}", "endpoint": "/fapi/v1/userTrades", "window_ms": [s_ms, e_ms],
               "n_symbols_queried": len(names), "n_rows": len(trades), "completeness": "COMPLETE", "body": trades,
               "income_rows": irows, "income_completeness": istatus}
    tmp = raw_out + ".part"
    with open(tmp, "w") as fh: json.dump(raw_doc, fh)
    os.replace(tmp, raw_out)                                  # 原子写: 读者永远看不到半份拉取

    # ── C. 闭合 ──
    led_ids = {(f["symbol"], str(f["trade_id"])) for f in fills}
    ven_ids = {(t["symbol"], str(t["id"])) for t in trades}
    ledger_only = sorted(led_ids - ven_ids)                  # 账本有、场所无 = 合同违例
    missing = [t for t in trades if (t["symbol"], str(t["id"])) not in led_ids]
    q_miss = collections.defaultdict(float)
    for t in missing: q_miss[t["symbol"]] += (1.0 if t["buyer"] else -1.0) * abs(float(t["qty"]))
    # (a) 逐名数量闭合: q0 + 账本成交 + 缺失成交 == q1
    qfail = []
    for s in sorted(names_local | set(q_miss)):
        q0 = m0.get(s, (0, 0))[0]; q1 = m1.get(s, (0, 0))[0]; mk = m1.get(s, (0, 0))[1] or m0.get(s, (0, 0))[1]
        d = q0 + q_rec[s] + q_miss[s] - q1
        if abs(d) * (mk or 1.0) > 0.01 or (mk == 0 and abs(d) > 1e-9): qfail.append((s, round(d, 10)))
    # (b) 现金闭合
    miss_cash = sum((1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])) for t in missing)
    miss_fee_native = collections.Counter()
    for t in missing: miss_fee_native[t["commissionAsset"]] += float(t["commission"])
    miss_fee = sum(fee_usdt(t["commissionAsset"], float(t["commission"]), int(t["time"]) / 1000) for t in missing)
    predicted = -miss_cash - miss_fee
    gap_cash = resid - predicted
    # (c) 两端点交叉: userTrades vs income (全部场所成交, 不只缺失的)
    inc = collections.defaultdict(float)
    for r in irows: inc[(r["incomeType"], r.get("asset"))] += float(r["income"])
    tr_fee = collections.Counter(); tr_rpnl = 0.0
    for t in trades: tr_fee[t["commissionAsset"]] += float(t["commission"]); tr_rpnl += float(t["realizedPnl"])
    cross = {"commission_by_asset_userTrades": {k: round(v, 8) for k, v in tr_fee.items()},
             "commission_by_asset_income": {a: round(-v, 8) for (ty, a), v in inc.items() if ty == "COMMISSION"},
             "realized_pnl_userTrades": round(tr_rpnl, 6),
             "realized_pnl_income": round(sum(v for (ty, a), v in inc.items() if ty == "REALIZED_PNL"), 6),
             "funding_income": round(sum(v for (ty, a), v in inc.items() if ty == "FUNDING_FEE"), 6), "funding_local": round(fund, 6),
             "income_types": sorted({ty for ty, a in inc})}
    cross_ok = (all(abs(cross["commission_by_asset_userTrades"].get(a, 0.0) - cross["commission_by_asset_income"].get(a, 0.0)) < 1e-6
                    for a in set(cross["commission_by_asset_userTrades"]) | set(cross["commission_by_asset_income"]))
                and abs(cross["realized_pnl_userTrades"] - cross["realized_pnl_income"]) < 1e-4)
    # 账本已记成交 vs 场所: 同一 (symbol, trade id) 的金额与手续费必须一致(正对照: 09-09 / 09-12 平仓成交已入账)
    vt = {(t["symbol"], str(t["id"])): t for t in trades}
    led_amt = [abs(float(f["fill_notional"]) - abs(float(vt[k]["quoteQty"]))) for f in fills
               for k in [(f["symbol"], str(f["trade_id"]))] if k in vt]
    led_fee = [abs(float(f.get("commission") or 0.0) - float(vt[k]["commission"])) for f in fills
               for k in [(f["symbol"], str(f["trade_id"]))] if k in vt and f.get("commission_asset") == vt[k]["commissionAsset"]]
    led_asset_mismatch = sum(1 for f in fills for k in [(f["symbol"], str(f["trade_id"]))]
                             if k in vt and f.get("commission_asset") != vt[k]["commissionAsset"])
    # 订单身份(v2): 执行器每张 protective_flatten 单记着场所的【首/末成交毫秒】(场所时钟)与签名成交额。
    #   场所端按 orderId 分组; 一张执行器单 ⇔ 同 (symbol, side) 且首/末成交毫秒都相同的场所 orderId —— 必须【恰好一个】, 金额再核一次。
    #   这把「按 ±120 s 时间窗归因」换成「按订单身份归因」: 旧窗以本地回读时刻为中心, 平仓开始得更早,
    #   09-06 桶漏了前 23 秒(31 名)、08-26 桶漏了前 26 秒 —— 不是个例而是窗规则的类缺陷, 所以换规则而不是挪窗。
    vo = collections.defaultdict(list)
    for t in trades: vo[t["orderId"]].append(t)
    vkey = collections.defaultdict(list)
    for oid, ts_ in vo.items():
        vkey[(ts_[0]["symbol"], "buy" if ts_[0]["buyer"] else "sell",
              min(int(t["time"]) for t in ts_), max(int(t["time"]) for t in ts_))].append(oid)
    flat = [o for o in ords if o.get("order_type") == "protective_flatten"]
    matched, zero, many, amt = {}, [], [], []
    for o in flat:
        if o.get("first_fill_ts") is None or o.get("last_fill_ts") is None: zero.append(o["symbol"]); continue
        k = (o["symbol"], str(o.get("side")).lower(), int(round(float(o["first_fill_ts"]) * 1000)), int(round(float(o["last_fill_ts"]) * 1000)))
        c = vkey.get(k, [])
        if len(c) == 1:
            matched[c[0]] = o
            v = sum((1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])) for t in vo[c[0]])
            amt.append(abs(v - float(o["filled_notional"])) if o.get("filled_notional") is not None else float("inf"))
        elif not c: zero.append(o["symbol"])
        else: many.append((o["symbol"], c))
    ft = [t for oid in matched for t in vo[oid]]
    ft_fee_native = collections.Counter()
    for t in ft: ft_fee_native[t["commissionAsset"]] += float(t["commission"])
    ft_fee = sum(fee_usdt(t["commissionAsset"], float(t["commission"]), int(t["time"]) / 1000) for t in ft)
    ft_rpnl = sum(float(t["realizedPnl"]) for t in ft)
    groups = sorted({o.get("rebalance_id") for o in flat})
    other_missing = [t for t in missing if t["orderId"] not in matched]
    om_orders = collections.defaultdict(list)
    for t in other_missing: om_orders[t["orderId"]].append(t)
    flatten = {"rebalance_ids": groups, "n_executor_flatten_orders": len(flat), "n_matched_one_to_one": len(matched),
               "n_no_venue_order": len(zero), "no_venue_order": zero[:10], "n_ambiguous": len(many), "ambiguous": many[:10],
               "max_abs_signed_notional_diff_executor_vs_venue": (round(max(amt), 6) if amt else None),
               "n_trades": len(ft), "n_trades_already_in_ledger": sum(1 for t in ft if (t["symbol"], str(t["id"])) in led_ids),
               "time_span": ([U(min(int(t["time"]) for t in ft) / 1000), U(max(int(t["time"]) for t in ft) / 1000)] if ft else None),
               "gross_usdt": round(sum(abs(float(t["quoteQty"])) for t in ft), 4),
               "realized_pnl_venue": round(ft_rpnl, 4), "fee_native": {k: round(v, 8) for k, v in ft_fee_native.items()},
               "fee_usdt_eq": round(ft_fee, 4), "realized_after_fee": round(ft_rpnl - ft_fee, 4),
               "reads": "realized P&L of the flatten ORDERS (identity-joined), measured against each name's average cost basis — "
                        "a cash identity, NOT the counterfactual cost of flattening"}
    other = {"n_trades": len(other_missing), "n_orders": len(om_orders),
             "orders": [{"orderId": oid, "symbol": ts_[0]["symbol"], "side": "buy" if ts_[0]["buyer"] else "sell",
                         "first": U(min(int(t["time"]) for t in ts_) / 1000), "n": len(ts_),
                         "signed_cash": round(sum((1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])) for t in ts_), 4),
                         "realized": round(sum(float(t["realizedPnl"]) for t in ts_), 4)} for oid, ts_ in list(om_orders.items())[:40]],
             "reads": "venue trades in the window that are absent from the ledger AND do not belong to an identity-matched flatten order"}
    tmin = min((int(t["time"]) for t in missing), default=None); tmax = max((int(t["time"]) for t in missing), default=None)
    closed = (not ledger_only and not qfail and abs(gap_cash) <= tol and cross_ok
              and (max(led_amt) if led_amt else 0.0) < 1e-6 and (max(led_fee) if led_fee else 0.0) < 1e-8 and led_asset_mismatch == 0)
    C = {"n_venue_trades": len(trades), "n_symbols_queried": len(names), "n_income_only_symbols": len(inc_syms - names_local),
         "n_ledger_only_trades": len(ledger_only), "ledger_only_sample": ledger_only[:10],
         "ledger_vs_venue_same_trade": {"n": len(led_amt), "max_abs_notional_diff": (round(max(led_amt), 9) if led_amt else None),
                                        "max_abs_commission_diff": (round(max(led_fee), 10) if led_fee else None),
                                        "n_commission_asset_mismatch": led_asset_mismatch},
         "n_missing_trades": len(missing), "n_missing_symbols": len({t['symbol'] for t in missing}),
         "missing_time_span": [U(tmin / 1000) if tmin else None, U(tmax / 1000) if tmax else None],
         "missing_maker_share": round(sum(1 for t in missing if t["maker"]) / len(missing), 4) if missing else None,
         "missing_gross_usdt": round(sum(abs(float(t["quoteQty"])) for t in missing), 4),
         "missing_signed_cash_usdt": round(miss_cash, 4), "missing_fee_native": {k: round(v, 8) for k, v in miss_fee_native.items()},
         "missing_fee_usdt_eq": round(miss_fee, 4), "missing_realized_pnl_venue": round(sum(float(t["realizedPnl"]) for t in missing), 4),
         "quantity_closure_failures": qfail[:20], "n_quantity_closure_failures": len(qfail),
         "predicted_residual": round(predicted, 4), "measured_residual": round(resid, 4), "closure_gap": round(gap_cash, 4), "tol": round(tol, 4),
         "cross_endpoint": cross, "cross_endpoint_ok": cross_ok,
         "flatten_orders": flatten, "other_missing": other,
         "executor_order_types_in_window": dict(ord_types),
         "identity_boundary": "flatten orders carry no clientOrderId of ours and (before the broker fix) no recorded venue orderId; the join is "
                              "(symbol, side, first-fill ms, last-fill ms) with measured one-to-one uniqueness and an amount check, not an id join",
         "VERDICT": "CLOSED" if closed else "OPEN"}
    doc = {"receipt": "FLATTEN_WINDOW_CLOSURE", "device": f"flatten_window_closure.py {VERSION}",
           "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "utc": time.strftime("%FT%TZ", time.gmtime()), "argv": sys.argv[1:], "inputs_sha16": inputs,
           "raw_trades_file": os.path.basename(raw_out), "raw_trades_sha256": hashlib.sha256(open(raw_out, "rb").read()).hexdigest(),
           "A_local_identity": A, "C_closure": C}
    tmp = out + ".part"
    with open(tmp, "w") as fh: json.dump(doc, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, out)
    print("C 闭合:", json.dumps({k: v for k, v in C.items() if k not in ("cross_endpoint", "flatten_orders", "other_missing")}, ensure_ascii=False))
    print("  两端点:", json.dumps(cross, ensure_ascii=False))
    print("  平仓单(身份对齐):", json.dumps(flatten, ensure_ascii=False))
    print("  其它缺失成交:", json.dumps({k: (v if k != "orders" else v[:8]) for k, v in other.items()}, ensure_ascii=False))
    print("VERDICT", C["VERDICT"])
    return 0 if closed else 4


if __name__ == "__main__":
    sys.exit(main())
