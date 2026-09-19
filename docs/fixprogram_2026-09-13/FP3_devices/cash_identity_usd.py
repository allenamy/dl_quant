#!/usr/bin/env python3
"""FP3 · 全期现金恒等式, 用账户【自己的计价单位】重写(2026-09-19)。只读。

为什么: CASH_RECON v6 有 21 个「超容差但没有持仓缺口」的窗, 残差绝对值合计 329.05 USD, 此前「没有机制解释」。
  2026-09-19 实测到的机制(read-only 密钥, 收据在 venue_readonly_2026-09-19/):
   ① 账户 multiAssetsMargin = True, daily_nav.nav 是 USD: USDT 按 USDTUSD 指数×(1−1e-4) 计入, BNB 按 BNBUSD 指数×0.95 计入;
      恒等式的其它各项都是 USDT ⇒ 此前把 USD 与 USDT 直接相减。空仓窗(9 月 7 个)的 NAV 跳动被 USDT 指数解释到 ±0.6 USD。
   ② 08-05..09-06 手续费以 BNB 付, 账户持有 BNB 余额 ⇒ BNB 价格变动本身改变 NAV(打 0.95 折), 恒等式里没有这一项。
   ③ external_flow_usdt 是【自然日累计】(since 00:00Z), 窗口却是 20:4x→20:4x 或 4 小时; 且把 BNB 数量当 USDT 相加
      (08-05 07:23 −200 USDT 与 07:24 +0.33275 BNB 被记成 −199.667)。
  本装置把三项都按场所原始流水重做, 并对【每一个】NAV 窗(最细 4 小时 + v6 的日窗)出残差。

恒等式(单位: 账户自己的):  N = p·W + b·B
   W1 = W0 + Σ_s(q1·mk1 − q0·mk0) − Σ_全部成交 sgn·quoteQty + Σ_USDT 计收入流水(资金费 / 手续费 / 划转 / 其它)
   B1 = B0 + Σ_BNB 计收入流水(手续费为负 / 划转 / 其它)
   残差(USDT) = (N1 − p1·W1 − b1·B1) / p1,      W0 = (N0 − b0·B0) / p0
   REALIZED_PNL 与 DELIVERED_SETTELMENT 流水【不】进恒等式: 它们是钱包对成交的记账(下市结算由场所作为一笔 userTrade 给出),
   已经由成交现金 + 持仓市值变化完整包含, 再加就重复。
全部成交 = 账本成交(规范读者坍缩) ∪ 账本缺失的场所成交(场所 COMMISSION / REALIZED_PNL / DELIVERED_SETTELMENT 流水的 (symbol, tradeId)
   反连接账本得出, 再拉 userTrades)。三类都没有的成交(零手续费且零已实现, 如纯开仓的零费成交)反连接看不见 —— 由逐名数量闭合兜住
   (q0 + Σ成交 = q1), 不静默。
所有输入落盘并带 sha; 指数价格走 usd_valuation 的缓存, --offline 复跑不联网、逐位相同。
★ v2 两件事:
  (1) 精确计价率。kline 插值的 USDTUSD 与账户在那一秒实际用的率有 ±24 ppm(sd)的差, 在 ~116k 上是 ±2.7 USD, 最坏 −120 ppm(09-09 04:43:39)
      ⇒ 4 小时窗出现「相邻两窗符号相反」的锯齿。BNB 余额为 0 的时刻(08-05 07:24 前、09-07 08:25 后), 钱包 USD / 钱包 USDT 就是账户实际用的率:
        钱包 USDT(t) = 快照钱包 USDT − Σ_{t < time ≤ 快照} USDT 计收入流水(全部类型, 含 REALIZED_PNL —— 这里重建的是钱包, 不是恒等式)
      两端都有精确率的窗, 另报 residual_exact_p; 判词优先用它, kline 口径并列。这不是循环论证: 精确率只来自钱包一侧,
      恒等式检验的是「未实现盈亏 + 钱包」与持仓市值、成交现金是否一致。
  (2) 数量缺口定点补拉: 第一遍里逐名数量不闭合的 (名, 窗), 对该名该窗拉完整 userTrades, 把账本没有的成交补进来再算一遍。
usage: cash_identity_usd.py <out.json> --income <INCOME_ALL.json> [--income-delta <INCOME_DELTA.json>] [--account-snapshot <ACCOUNT_SNAPSHOT.json>]
       [--raw <closure_raw.json> ...] [--missing-trades <MISSING_TRADES.json>] [--offline]"""
import bisect, collections, glob, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
import fills_reader as FR
import usd_valuation as UV
VERSION = "v2-2026-09-19"   # v2: 精确计价率列(BNB=0 时由钱包反推) + 数量缺口定点补拉
LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
SNAP_TOL_S = 60.0
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
DAY = lambda t: time.strftime("%Y%m%d", time.gmtime(float(t)))
sha16 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def rows(day, name):
    p = f"{LED}/{day}/{name}.jsonl"
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []


def main():
    av = sys.argv[1:]; out = av[0]; flags = collections.defaultdict(list); i = 1
    while i < len(av):
        if av[i] == "--offline": flags["--offline"].append(True); i += 1
        elif av[i] == "--ablate": flags["--ablate"].append(av[i + 1]); i += 2
        else: flags[av[i]].append(av[i + 1]); i += 2
    offline = bool(flags.get("--offline"))
    # 负对照(红能力): 逐项拿掉恒等式的一个组成部分, 判词必须变差 —— 否则这个验证器在该项上是空转的。
    ABL = set(flags.get("--ablate", []))
    assert ABL <= {"missing_trades", "usd_unit", "bnb_balance", "venue_transfers"}, ABL
    inc = json.load(open(flags["--income"][0]))
    if inc.get("completeness") != "COMPLETE" or inc.get("incomeType") not in (None, "ALL"):
        print("REFUSED: --income 必须是【全类型】且 COMPLETE 的收入拉取"); return 2
    I = inc["body"]; i_lo, i_hi = inc["startTime"], inc["endTime"]
    dlt = None
    if flags.get("--income-delta"):                            # 桥接段: 主拉取末尾 → 账户快照之后; 必须首尾相接且完整
        dlt = json.load(open(flags["--income-delta"][0]))
        if dlt.get("completeness") != "COMPLETE" or dlt["startTime"] != i_hi + 1:
            print("REFUSED: --income-delta 不完整或不与主拉取首尾相接"); return 2
        I = I + dlt["body"]; i_hi = dlt["endTime"]
    days = sorted(d for d in os.listdir(LED) if d.startswith("2026") and os.path.isdir(f"{LED}/{d}"))
    inputs = {f"{d}/{n}": sha16(f"{LED}/{d}/{n}.jsonl") for d in days for n in ("fills", "position_readback", "daily_nav")
              if os.path.isfile(f"{LED}/{d}/{n}.jsonl")}
    inputs["income"] = sha16(flags["--income"][0])

    # ── 成交: 账本(坍缩) + 缺失 ──
    fills = FR.read_range(day_list=days)
    led = {(f["symbol"], str(f["trade_id"])): f for f in fills}
    # 场所成交身份的来源: 任何带 tradeId 的收入行(COMMISSION / REALIZED_PNL / DELIVERED_SETTELMENT)。
    #   只用 COMMISSION 会漏掉零手续费的成交(下市结算就是一例), 所以取并集。
    TRADE_TYPES = ("COMMISSION", "REALIZED_PNL", "DELIVERED_SETTELMENT")
    ven_ids = {}
    for r in I:
        if r["incomeType"] in TRADE_TYPES and r.get("tradeId") not in (None, ""):
            ven_ids.setdefault((r["symbol"], str(r["tradeId"])), r)
    miss_ids = sorted(set(ven_ids) - set(led))
    led_not_in_income = sorted(k for k, f in led.items() if float(f.get("commission") or 0.0) != 0.0
                               and i_lo <= float(f["fill_ts"]) * 1000 <= i_hi and k not in ven_ids)
    have = {}
    for p in flags.get("--raw", []):                          # 先用已完整拉取的平仓窗原始成交
        rd = json.load(open(p)); inputs[os.path.basename(p)] = sha16(p)
        if rd.get("completeness") != "COMPLETE": print("REFUSED: --raw 不完整", p); return 2
        for t in rd["body"]: have[(t["symbol"], str(t["id"]))] = t
    mt_path = flags.get("--missing-trades", [None])[0]
    if mt_path and os.path.isfile(mt_path):
        md = json.load(open(mt_path)); inputs[os.path.basename(mt_path)] = sha16(mt_path)
        for t in md["body"]: have[(t["symbol"], str(t["id"]))] = t
    need = [k for k in miss_ids if k not in have]
    if need:
        if offline: print(f"UNAVAILABLE: {len(need)} 笔缺失成交不在任何输入里(offline)"); return 3
        import fetch_trades as FT
        by_sym = collections.defaultdict(list)
        for s, tid in need: by_sym[s].append(int(ven_ids[(s, tid)]["time"]))
        fetched, bad = [], []
        for s, ts_ in sorted(by_sym.items()):
            ts_.sort(); cl = [[ts_[0], ts_[0]]]
            for t in ts_[1:]:
                if t - cl[-1][1] <= 3_600_000: cl[-1][1] = t
                else: cl.append([t, t])
            for a, b in cl:
                # 收入行的 time 是【截到整秒】的(实测: 成交 time − 收入 time ∈ [0, 997] ms), 窗口两端各放 1 s; 身份仍按 id 精确匹配
                pages, rs, st, why = FT.fetch_trades(s, a - 1000, b + 1000)
                if st != "COMPLETE": bad.append((s, a, b, why)); continue
                fetched += rs
        if bad: print("UNAVAILABLE: userTrades 不完整", bad[:5]); return 3
        for t in fetched: have[(t["symbol"], str(t["id"]))] = t
        mt_path = mt_path or out.replace(".json", "_MISSING_TRADES.json")
        if os.path.isfile(mt_path):                          # 追加而不是覆盖: 上一次已完整拉到的成交保留
            prev = json.load(open(mt_path))["body"]; seen = {(t["symbol"], str(t["id"])) for t in fetched}
            fetched = [t for t in prev if (t["symbol"], str(t["id"])) not in seen] + fetched
        doc = {"device": f"cash_identity_usd.py {VERSION}", "endpoint": "/fapi/v1/userTrades", "completeness": "COMPLETE",
               "rule": "clusters of missing trade times per symbol (gap ≤ 1 h), each pulled complete-by-construction over [first − 1 s, last + 1 s] (income times are floored to the second)", "body": fetched}
        with open(mt_path + ".part", "w") as fh: json.dump(doc, fh)
        os.replace(mt_path + ".part", mt_path); inputs[os.path.basename(mt_path)] = sha16(mt_path)
    still = [k for k in miss_ids if k not in have]
    if still: print(f"UNAVAILABLE: {len(still)} 笔缺失成交拉不到", still[:5]); return 3
    # 缺失成交 = 收入反连接得出的 ∪ 缺失成交收据里账本没有的(后者含零费零已实现、收入里没有行的成交 —— 数量补拉找到的就在这里)。
    #   只取前者会让补拉结果在下一次运行里丢掉(09-19 实测: 第二次运行 sweep 加 0, 数量缺口回来了), 离线复跑也就复现不了。
    from_file = set()
    if mt_path and os.path.isfile(mt_path):
        from_file = {(t["symbol"], str(t["id"])) for t in json.load(open(mt_path))["body"]} - set(led)
    miss_keys = sorted(set(miss_ids) | from_file)
    missing = [have[k] for k in miss_keys]
    # 统一成交表: (ts, symbol, signed qty, signed cash)
    T = [(float(f["fill_ts"]), f["symbol"], (1.0 if str(f["side"]).upper() == "BUY" else -1.0) * float(f["fill_notional"]) / float(f["fill_px"]),
          (1.0 if str(f["side"]).upper() == "BUY" else -1.0) * float(f["fill_notional"]), "L") for f in fills]
    T += [(int(t["time"]) / 1000, t["symbol"], (1.0 if t["buyer"] else -1.0) * abs(float(t["qty"])),
           (1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])), "M") for t in missing]
    T.sort()
    # 账本已记且场所也有的同一笔: 金额必须一致
    amt_diff = [abs(float(led[k]["fill_notional"]) - abs(float(have[k]["quoteQty"]))) for k in led if k in have]

    # ── BNB 余额路径(全类型流水里 asset = BNB 的全部行) ──
    path = UV.BnbPath(I)
    # ── 精确计价率(仅 BNB = 0 的时刻) ──
    p_exact_at = lambda ts, wusd: None
    if flags.get("--account-snapshot") and flags.get("--income-delta"):
        snp = json.load(open(flags["--account-snapshot"][0]))
        inputs["account_snapshot"] = sha16(flags["--account-snapshot"][0]); inputs["income_delta"] = sha16(flags["--income-delta"][0])
        usdt = [x for x in snp["assets"] if x["asset"] == "USDT"][0]; W_snap = float(usdt["walletBalance"]); t_snap = int(usdt["updateTime"])
        if dlt["endTime"] < t_snap: print("REFUSED: 收入流水没有覆盖到快照时刻"); return 2
        Iu = sorted((r for r in I if r.get("asset") == "USDT"), key=lambda r: int(r["time"]))   # I 已含桥接段
        after = [r for r in Iu if int(r["time"]) > t_snap]
        if after: print(f"REFUSED: 快照之后还有 {len(after)} 行 USDT 流水, 快照不是最新钱包"); return 2
        ut = [int(r["time"]) for r in Iu]; uc = [0.0]
        for r in Iu: uc.append(uc[-1] + float(r["income"]))

        def p_exact_at(ts, wusd):
            if wusd is None or abs(path.at(ts)) > 1e-9: return None   # 路径是浮点累加: 09-07 后 = 2.5e-17 而非 0.0, 用容差而不是 ==(第一次跑用 == 把九月全排除了)
            wu = W_snap - (uc[len(ut)] - uc[bisect.bisect_right(ut, int(float(ts) * 1000))])
            return float(wusd) / wu if wu else None
    # ── NAV 行 / 快照 ──
    nav = sorted({float(r["nav_ts"]): r for d in days for r in rows(d, "daily_nav") if r.get("mode") in (None, "LIVE")}.values(),
                 key=lambda r: float(r["nav_ts"]))
    rb = collections.defaultdict(dict)
    for d in days:
        for r in rows(d, "position_readback"): rb[float(r["read_ts"])][r["symbol"]] = r
    snaps = sorted(rb)

    def snap(ts):
        j = bisect.bisect_left(snaps, ts); c = [s for s in snaps[max(0, j - 2):j + 2] if abs(s - ts) <= SNAP_TOL_S]
        if not c: return None
        st = min(c, key=lambda k: (abs(k - ts), k))
        return {s: (float(r["venue_position_qty"]), abs(float(r["venue_position_notional"])) / abs(float(r["venue_position_qty"]))
                    if float(r["venue_position_qty"]) else 0.0) for s, r in rb[st].items()}
    Tt = [x[0] for x in T]
    It = sorted(I, key=lambda r: int(r["time"])); Itt = [int(r["time"]) for r in It]

    def window(r0, r1):
        t0, t1 = float(r0["nav_ts"]), float(r1["nav_ts"])
        if not (i_lo <= t0 * 1000 and t1 * 1000 <= i_hi): return {"from": U(t0), "to": U(t1), "status": "UNAVAILABLE_OUTSIDE_INCOME_PULL"}
        m0, m1 = snap(t0), snap(t1)
        if m0 is None or m1 is None: return {"from": U(t0), "to": U(t1), "status": "UNAVAILABLE_TIMING"}
        a, b = bisect.bisect_right(Tt, t0), bisect.bisect_right(Tt, t1)
        cash = collections.defaultdict(float); qty = collections.defaultdict(float); n_m = 0
        for ts, s, q, c, src in T[a:b]:
            if src == "M" and "missing_trades" in ABL: continue
            cash[s] += c; qty[s] += q; n_m += src == "M"
        names = set(m0) | set(m1) | set(qty); mtm = 0.0; qfail = []
        for s in names:
            q0, k0 = m0.get(s, (0.0, 0.0)); q1, k1 = m1.get(s, (0.0, 0.0))
            mtm += q1 * k1 - q0 * k0 - cash[s]
            if abs(q0 + qty[s] - q1) * (k1 or k0 or 1.0) > 0.01: qfail.append((s, round(q0 + qty[s] - q1, 8)))
        ia, ib = bisect.bisect_right(Itt, int(t0 * 1000)), bisect.bisect_right(Itt, int(t1 * 1000))
        flow = collections.defaultdict(float); other = collections.Counter()
        for r in It[ia:ib]:
            if r["incomeType"] in ("REALIZED_PNL", "DELIVERED_SETTELMENT"): continue   # 钱包对成交的记账; 现金已在成交里
            flow[(r["incomeType"], r.get("asset"))] += float(r["income"])
            if r["incomeType"] not in ("COMMISSION", "FUNDING_FEE", "TRANSFER"): other[r["incomeType"]] += 1
        bad_assets = sorted({a_ for _, a_ in flow} - {"USDT", "BNB"})
        p0, p1 = UV.p_usdt(t0, offline), UV.p_usdt(t1, offline); b0, b1 = UV.b_bnb(t0, offline), UV.b_bnb(t1, offline)
        N0, N1 = float(r0["nav"]), float(r1["nav"]); B0 = path.at(t0)
        if "usd_unit" in ABL: p0 = p1 = 1.0
        if "bnb_balance" in ABL:
            B0 = 0.0; flow = {k: v for k, v in flow.items() if k[1] != "BNB"}
        if "venue_transfers" in ABL:                           # v6 行为: 用 t1 行的自然日累计 external_flow_usdt 代替窗内场所划转
            flow = {k: v for k, v in flow.items() if k[0] != "TRANSFER"}; flow[("TRANSFER", "USDT")] = float(r1.get("external_flow_usdt") or 0.0)
        W0 = (N0 - b0 * B0) / p0
        W1 = W0 + mtm + sum(v for (ty, a_), v in flow.items() if a_ == "USDT")
        B1 = B0 + sum(v for (ty, a_), v in flow.items() if a_ == "BNB")
        res = (N1 - p1 * W1 - b1 * B1) / p1
        tol = max(2.0, 0.5e-4 * N0)
        pe0, pe1 = p_exact_at(t0, r0.get("wallet_balance")), p_exact_at(t1, r1.get("wallet_balance"))
        res_x = None
        if pe0 is not None and pe1 is not None and "usd_unit" not in ABL:   # 两端 B = 0 ⇒ W = N / p 精确
            W0x = N0 / pe0; res_x = (N1 - pe1 * (W0x + mtm + sum(v for (ty, a_), v in flow.items() if a_ == "USDT"))) / pe1
        res_primary = res_x if res_x is not None else res
        # 同一窗的旧口径(v6 同义: USD 当 USDT、自然日累计划转、BNB 手续费按日收盘折算)—— 并列, 用来量化每一项
        old_flow = float(r1.get("external_flow_usdt") or 0.0)
        return {"from": U(t0), "to": U(t1), "hours": round((t1 - t0) / 3600, 2), "n_trades": b - a, "n_missing_trades": n_m,
                "n_quantity_failures": len(qfail), "quantity_failures": qfail[:6],
                "residual_usd_identity": round(res, 4), "residual_exact_p": (None if res_x is None else round(res_x, 4)),
                "p_exact": (None if res_x is None else [round(pe0, 9), round(pe1, 9)]),
                "residual_primary": round(res_primary, 4), "primary_source": ("exact_p" if res_x is not None else "kline_p"),
                "tol": round(tol, 4), "ok": abs(res_primary) <= tol and not qfail and not bad_assets,
                "ok_kline_p": abs(res) <= tol and not qfail and not bad_assets,
                "terms": {"p": [round(p0, 8), round(p1, 8)], "b": [round(b0, 4), round(b1, 4)], "B": [round(B0, 8), round(B1, 8)],
                          "B_path_at_t1": round(path.at(t1), 8), "N": [N0, N1], "mtm_and_trade_cash": round(mtm, 4),
                          "flows": {f"{k[0]}|{k[1]}": round(v, 8) for k, v in flow.items()},
                          "usdt_revaluation_usd": round(W0 * (p1 - p0), 4), "bnb_revaluation_usd": round(B0 * (b1 - b0), 4),
                          "ledger_external_flow_usdt_row_t1": old_flow},
                "other_income_types": dict(other), "non_usdt_bnb_assets": bad_assets}

    W4 = [window(a_, b_) for a_, b_ in zip(nav, nav[1:])]
    # ── 数量缺口定点补拉 ──
    sweep = {"n_pairs": 0, "n_trades_added": 0, "pairs": []}
    qpairs = [(s_, w["from"], w["to"]) for w in W4 if w.get("n_quantity_failures") for s_, _ in w["quantity_failures"]]
    if qpairs and not offline:
        import fetch_trades as FT
        navt = {U(r["nav_ts"]): float(r["nav_ts"]) for r in nav}
        added = []
        for s_, f_, t_ in qpairs:
            pages, rs, st, why = FT.fetch_trades(s_, int(navt[f_] * 1000) + 1, int(navt[t_] * 1000))
            if st != "COMPLETE": print("UNAVAILABLE: 补拉不完整", s_, f_, why); return 3
            mk = {(t["symbol"], str(t["id"])) for t in missing}
            new = [t for t in rs if (t["symbol"], str(t["id"])) not in led and (t["symbol"], str(t["id"])) not in mk]
            for t in new: have[(t["symbol"], str(t["id"]))] = t
            added += new; sweep["pairs"].append({"symbol": s_, "from": f_, "to": t_, "venue_trades": len(rs), "added": len(new)})
        sweep["n_pairs"] = len(qpairs); sweep["n_trades_added"] = len(added)
        if added:
            missing += added
            T.extend((int(t["time"]) / 1000, t["symbol"], (1.0 if t["buyer"] else -1.0) * abs(float(t["qty"])),
                      (1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])), "M") for t in added)
            T.sort(); Tt[:] = [x[0] for x in T]
            mt_path2 = mt_path or out.replace(".json", "_MISSING_TRADES.json")
            prev = json.load(open(mt_path2))["body"] if os.path.isfile(mt_path2) else []
            doc_m = {"device": f"cash_identity_usd.py {VERSION}", "endpoint": "/fapi/v1/userTrades", "completeness": "COMPLETE",
                     "rule": "missing-trade clusters (income-joined) + quantity-failure sweep (name × NAV window, complete pulls)", "body": prev + added}
            with open(mt_path2 + ".part", "w") as fh: json.dump(doc_m, fh)
            os.replace(mt_path2 + ".part", mt_path2); inputs[os.path.basename(mt_path2)] = sha16(mt_path2)
            W4 = [window(a_, b_) for a_, b_ in zip(nav, nav[1:])]
    lastday = {}
    for r in nav: lastday[DAY(r["nav_ts"])] = r                 # v6 的日窗 = 每日最后一行(fp3 nav_rows 同规则)
    dl = [lastday[d] for d in sorted(lastday)]
    WD = [window(a_, b_) for a_, b_ in zip(dl, dl[1:])]
    if not offline: UV.save()

    def summ(W):
        ok = [w for w in W if "ok" in w]
        return {"n": len(W), "n_judged": len(ok), "n_ok": sum(w["ok"] for w in ok), "n_bad": sum(not w["ok"] for w in ok),
                "n_ok_kline_p": sum(w["ok_kline_p"] for w in ok), "n_primary_exact_p": sum(w["primary_source"] == "exact_p" for w in ok),
                "n_unavailable": len(W) - len(ok), "residual_abs_sum": round(sum(abs(w["residual_primary"]) for w in ok), 2),
                "residual_abs_sum_kline_p": round(sum(abs(w["residual_usd_identity"]) for w in ok), 2),
                "n_with_quantity_failures": sum(1 for w in ok if w["n_quantity_failures"]),
                "worst": sorted(((w["from"], w["to"], w["residual_primary"], w["primary_source"], w["n_quantity_failures"]) for w in ok),
                                key=lambda x: -abs(x[2]))[:12]}
    doc = {"receipt": "CASH_IDENTITY_USD", "device": f"cash_identity_usd.py {VERSION}", "ablated": sorted(ABL),
           "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "usd_valuation_sha256": hashlib.sha256(open(os.path.join(HERE, "usd_valuation.py"), "rb").read()).hexdigest(),
           "utc": time.strftime("%FT%TZ", time.gmtime()), "argv": sys.argv[1:], "inputs_sha16": inputs,
           "valuation": {"usdt_bid_buffer": UV.USDT_BID_BUFFER, "bnb_bid_buffer": UV.BNB_BID_BUFFER, "index_cache": os.path.basename(UV.CACHE)},
           "trades": {"n_ledger_collapsed": len(fills), "n_venue_commission_rows_with_tradeId": len(ven_ids),
                      "n_missing_from_ledger": len(missing), "n_missing_income_joined": len(miss_ids), "n_missing_from_receipt_only": len(from_file - set(miss_ids)), "n_ledger_trades_with_nonzero_fee_absent_from_income": len(led_not_in_income),
                      "ledger_absent_from_income_sample": led_not_in_income[:10],
                      "ledger_vs_venue_same_trade_max_abs_notional_diff": (round(max(amt_diff), 9) if amt_diff else None), "n_compared": len(amt_diff)},
           "bnb_path": {"n_rows": path.n, "min_balance": round(path.min_bal, 10), "end_balance": round(path.end, 10),
                        "by_type": {k: round(v, 10) for k, v in path.by_type.items()}},
           "quantity_sweep": sweep, "summary_4h": summ(W4), "summary_daily": summ(WD), "windows_4h": W4, "windows_daily": WD}
    with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1, ensure_ascii=False)
    os.replace(out + ".part", out)
    print("trades:", json.dumps(doc["trades"], ensure_ascii=False)); print("bnb_path:", doc["bnb_path"])
    print("sweep:", {k: v for k, v in sweep.items() if k != "pairs"})
    print("4h:", json.dumps({k: v for k, v in doc["summary_4h"].items() if k != "worst"})); print("  worst:", doc["summary_4h"]["worst"][:8])
    print("daily:", json.dumps({k: v for k, v in doc["summary_daily"].items() if k != "worst"})); print("  worst:", doc["summary_daily"]["worst"][:8])
    return 0


if __name__ == "__main__":
    sys.exit(main())
