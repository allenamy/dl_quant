"""exec_probe v2 tests — mock 账户/mock 下单接口, 不联网. 运行: python3 tests_exec_probe_v2.py
"会红"证据(把旧逻辑装回去): PROBE_V2_MUTANT=legacy_flatten|no_universe|no_halt python3 tests_exec_probe_v2.py  ⇒ 对应测试必须 FAIL.
场景 (a) 账户里有非本轮仓位(书的 ATOM/SNX) ⇒ 不平、记 foreign 事件  (b) 候选名 ∩ 书宇宙 ⇒ 排除  (c) 停机状态 ⇒ 跳轮
     (d) 收据字段齐全 + 断言  (e) 08-21 形态的自家净量记账(买成卖拒 ⇒ 平自己净量)  (f) 同名自家+他人混合: 只平自己、封顶、反号不动
     (g) 宇宙读不到 ⇒ 跳轮  (h) 被杀后账本恢复只平自己  (i) 候选为空 ⇒ 跳轮  (j) 越槽跳  (k) 日亏停  (l) 他人挂单名跳/自家孤儿单撤
     (m) 无 run 动词不启动/KILL  (n) --dry 零写操作  (o) 槽计算
"""
import os, sys, json, tempfile, datetime, shutil, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exec_probe as EP

MUTANT = os.environ.get("PROBE_V2_MUTANT", "")
FIXED_NOW = datetime.datetime(2026, 8, 22, 4, 20, 30, tzinfo=datetime.timezone.utc)
SLOT = FIXED_NOW.replace(minute=20, second=0, microsecond=0)
UNIVERSE = ["ATOMUSDT", "SNXUSDT"] + ["U%03dUSDT" % i for i in range(138)]      # 140, 形如在役面板列集
MEMBERS = UNIVERSE[:110]                                                         # 当月 110 在役(含 ATOM/SNX)

RESULTS = []


def check(cond, label, detail=""):
    RESULTS.append((bool(cond), label, detail))
    print(("PASS " if cond else "FAIL ") + label + (("  -- " + str(detail)[:300]) if (detail and not cond) else ""))
    return bool(cond)


# ───────────────────────── fixtures ─────────────────────────
def make_live_dir(root, tripped=False, eval_age_min=10, state_json=None, no_span=False, small_span=False, no_last_eval=False):
    live = os.path.join(root, "dl_quant_live")
    for d in ("config", "state/live/watchdog", "checkpoints"):
        os.makedirs(os.path.join(live, d), exist_ok=True)
    if not no_span:
        tab = {s: {"span": 2, "median_interval_h": 8.0} for s in (UNIVERSE[:10] if small_span else UNIVERSE)}
        json.dump({"n_symbols": len(tab), "table": tab}, open(os.path.join(live, "config", "funding_span_table.json"), "w"))
    json.dump({"symbols": MEMBERS, "king": {s: 0.0 for s in MEMBERS}}, open(os.path.join(live, "state", "live", "preds_latest.json"), "w"))
    json.dump({"training_member_union": {"symbols": UNIVERSE}}, open(os.path.join(live, "checkpoints", "MANIFEST.json"), "w"))
    if not no_last_eval:
        ev_ts = (FIXED_NOW - datetime.timedelta(minutes=eval_age_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
        json.dump({"tripped": tripped, "triggers": (["§4-5e position break"] if tripped else []), "evaluated_utc": ev_ts, "_mode": "LIVE"},
                  open(os.path.join(live, "state", "live", "watchdog", "last_eval.json"), "w"))
    if state_json is not None:
        json.dump(state_json, open(os.path.join(live, "state", "live", "watchdog", "state.json"), "w"))
    return live


def make_ticker():
    """400 名按量能降序. 0-129: 宇宙名; T2 段[130,200): BANK/ATOM/BERA/SNX/DODOX + 宇宙名 + 惯犯/股票/杠杆/CSOP + 填充;
    T3 段[300,380): PARTI/JASMY + 惯犯 + 填充."""
    top = [s for s in UNIVERSE if s not in ("ATOMUSDT", "SNXUSDT")][:130]
    t2 = ["BANKUSDT", "ATOMUSDT", "USARUSDT", "BERAUSDT", "SNXUSDT", "OLDCOINUSDT", "DODOXUSDT", "U130USDT", "U131USDT", "CRVUSDT",
          "TSLAUSDT", "BTC3LUSDT", "CSOPSAMSUNG2LUSDT", "U132USDT", "ZROUSDT"]
    t2 += ["T2F%02dUSDT" % i for i in range(70 - len(t2))]
    mid = ["M%03dUSDT" % i for i in range(100)]
    t3 = ["PARTIUSDT", "1000RATSUSDT", "JASMYUSDT", "U133USDT"] + ["T3F%02dUSDT" % i for i in range(76)]
    tail = ["Z%02dUSDT" % i for i in range(20)]
    ranked = top + t2 + mid + t3 + tail
    assert len(ranked) == 400 and len(set(ranked)) == 400, (len(ranked), len(set(ranked)))
    return [{"symbol": s, "quoteVolume": str(1e9 - i * 1e6)} for i, s in enumerate(ranked)], ranked


EQUITY_MOCK = {"TSLAUSDT", "USARUSDT"}          # USAR 不在 v1 静态名单: 只能靠 exchangeInfo underlyingType 排除
SETTLING_MOCK = {"OLDCOINUSDT"}
BOOK = {"BANKUSDT": (0.03809, 0.0381), "BERAUSDT": (0.1967, 0.1968), "DODOXUSDT": (0.021149, 0.021161),
        "PARTIUSDT": (0.25, 0.2501), "JASMYUSDT": (0.0145, 0.01451), "ATOMUSDT": (1.569, 1.570), "SNXUSDT": (0.234, 0.2341),
        "ZROUSDT": (2.0, 2.001), "XXXUSDT": (1.0, 1.001)}
STEP = {"BANKUSDT": 1.0, "BERAUSDT": 0.1, "DODOXUSDT": 1.0, "PARTIUSDT": 0.1, "JASMYUSDT": 1.0, "ATOMUSDT": 0.01,
        "SNXUSDT": 0.1, "ZROUSDT": 0.01, "XXXUSDT": 1.0}


def fill_all(symbol, side, arm, qty):
    return qty


def plan_incident_shape(symbol, side, arm, qty):
    """08-21 16:20Z 形态: BANK 买成卖拒(-5022) ⇒ 净多; BERA 卖单少 0.2/0.1 ⇒ 净 0.2; DODOX 净 3; 其余全成."""
    if symbol == "BANKUSDT":
        return qty if side == "BUY" else "REJECT"
    if symbol == "BERAUSDT" and side == "SELL":
        return qty - (0.1 if arm == "xl" else 0.1)          # 76.2→76.1, 381.2→381.1 ⇒ 净 +0.2
    if symbol == "DODOXUSDT" and side == "SELL":
        return qty - (1.0 if arm == "base" else 2.0)        # 净 +3
    return qty


class MockAPI:
    """模拟 Binance USDT-M: 持仓/挂单/下单/撤单/查单; 记录所有写操作. fill_plan(symbol, side, arm, qty) → 成交量 或 'REJECT'."""

    def __init__(self, positions=None, ticker=None, open_orders=None, fill_plan=fill_all, extra_syms=()):
        self.positions = dict(positions or {})
        self.ticker, self.ranked = ticker if ticker is not None else make_ticker()
        self.open_orders = {k: list(v) for k, v in (open_orders or {}).items()}
        self.fill_plan = fill_plan
        self.orders, self.calls, self.posts, self.deletes, self.market_orders = {}, [], [], [], []
        self._next = 1000
        self.all_syms = sorted(set(self.ranked) | set(BOOK) | set(extra_syms) | set(UNIVERSE))

    def _order_id(self):
        self._next += 1
        return self._next

    def req(self, method, path, params=None, signed=False):
        params = dict(params or {})
        self.calls.append((method, path, params, signed))
        if method == "GET" and path == "/fapi/v1/ticker/24hr":
            return self.ticker
        if method == "GET" and path == "/fapi/v1/exchangeInfo":
            return {"symbols": [{"symbol": s, "underlyingType": ("EQUITY" if s in EQUITY_MOCK else "COIN"),
                                 "contractType": ("TRADIFI_PERPETUAL" if s in EQUITY_MOCK else "PERPETUAL"),
                                 "status": ("SETTLING" if s in SETTLING_MOCK else "TRADING"), "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.00001"},
                {"filterType": "LOT_SIZE", "stepSize": str(STEP.get(s, 1.0))},
                {"filterType": "MIN_NOTIONAL", "notional": "5"}]} for s in self.all_syms]}
        if method == "GET" and path == "/fapi/v3/account":
            return {"positions": [{"symbol": s, "positionAmt": repr(a)} for s, a in self.positions.items() if abs(a) > 0]}
        if method == "GET" and path == "/fapi/v1/ticker/bookTicker":
            s = params["symbol"]
            if s not in BOOK:
                return {"_err": 400, "_body": "no book"}
            return {"symbol": s, "bidPrice": repr(BOOK[s][0]), "askPrice": repr(BOOK[s][1])}
        if method == "GET" and path == "/fapi/v1/openOrders":
            return list(self.open_orders.get(params["symbol"], []))
        if path == "/fapi/v1/order":
            if method == "POST":
                return self._post(params)
            if method == "GET":
                o = self.orders.get(int(params["orderId"]))
                return dict(o) if o else {"_err": 400, "_body": '{"code":-2013,"msg":"Order does not exist."}'}
            if method == "DELETE":
                self.deletes.append(params)
                o = self.orders.get(int(params["orderId"]))
                if o is None:
                    for s, lst in self.open_orders.items():
                        for x in lst:
                            if x.get("orderId") == params["orderId"]:
                                lst.remove(x); return {"orderId": x["orderId"], "status": "CANCELED", "executedQty": "0"}
                    return {"_err": 400, "_body": '{"code":-2011,"msg":"Unknown order sent."}'}
                if o["status"] in ("NEW", "PARTIALLY_FILLED"):
                    o["status"] = "CANCELED"
                    return dict(o)
                return {"_err": 400, "_body": '{"code":-2011,"msg":"Unknown order sent."}'}
        return {"_err": 404, "_body": "mock: unhandled %s %s" % (method, path)}

    def _post(self, p):
        self.posts.append(p)
        s, side = p["symbol"], p["side"]
        if p.get("type") == "MARKET":
            if p.get("reduceOnly") != "true":
                return {"_err": 400, "_body": "mock: non-reduceOnly MARKET not allowed in probe"}
            pos = self.positions.get(s, 0.0)
            q = float(p["quantity"])
            if pos == 0 or (side == "SELL" and pos < 0) or (side == "BUY" and pos > 0):
                return {"_err": 400, "_body": '{"code":-2022,"msg":"ReduceOnly Order is rejected."}'}
            q = min(q, abs(pos))
            self.positions[s] = pos - math.copysign(q, pos)
            if abs(self.positions[s]) < 1e-9:
                self.positions[s] = 0.0
            mid = sum(BOOK.get(s, (1, 1))) / 2
            oid = self._order_id()
            self.orders[oid] = {"orderId": oid, "symbol": s, "side": side, "status": "FILLED", "executedQty": repr(q),
                                "avgPrice": repr(mid), "origQty": repr(q), "reduceOnly": True}
            self.market_orders.append(self.orders[oid])
            return dict(self.orders[oid])
        # LIMIT GTX
        q = float(p["quantity"]); px = float(p["price"]); cid = p.get("newClientOrderId", "")
        arm = "xl" if "probe2xl" in cid or "probe_xl" in cid else "base"
        ex = self.fill_plan(s, side, arm, q)
        if ex == "REJECT":
            return {"_err": 400, "_body": '{"code":-5022,"msg":"Due to the order could not be executed as maker, the Post Only order will be rejected."}'}
        ex = float(ex)
        self.positions[s] = self.positions.get(s, 0.0) + (ex if side == "BUY" else -ex)
        st = "FILLED" if ex >= q - 1e-12 else ("PARTIALLY_FILLED" if ex > 0 else "NEW")
        oid = self._order_id()
        self.orders[oid] = {"orderId": oid, "clientOrderId": cid, "symbol": s, "side": side, "status": st,
                            "executedQty": repr(ex), "avgPrice": repr(px if ex > 0 else 0.0), "origQty": repr(q), "price": repr(px)}
        return dict(self.orders[oid])


def mk_probe(api, live, root, now=None):
    home = os.path.join(root, "probe_home")
    return EP.Probe(api, home=home, live_dir=live, sleep=lambda s: None, now=(now or (lambda: FIXED_NOW)),
                    kill_paths=[os.path.join(home, "KILL")])


def events(probe, kind=None):
    out = []
    if not os.path.exists(probe.ev_path):
        return out
    for line in open(probe.ev_path):
        d = json.loads(line)
        if kind is None or d.get("e") == kind:
            out.append(d)
    return out


def market_posts(api):
    return [p for p in api.posts if p.get("type") == "MARKET"]


# ───────────────────────── mutants(旧逻辑装回去) ─────────────────────────
def apply_mutant():
    if MUTANT == "legacy_flatten":
        def legacy(self, round_syms, own_net, positions, unknown_syms=()):
            """v1 语义: 本轮名字上有仓就全平, 不分归属."""
            fl = []
            for s in sorted(round_syms):
                amt = positions.get(s, 0.0)
                if abs(amt) > 0:
                    side = "SELL" if amt > 0 else "BUY"
                    r = self.api.req("POST", "/fapi/v1/order", {"symbol": s, "side": side, "type": "MARKET",
                                                                 "quantity": EP.fmt(abs(amt)), "reduceOnly": "true"}, signed=True)
                    fl.append({"symbol": s, "side": side, "qty": abs(amt), "own_net": own_net.get(s, 0.0), "acct_pos": amt,
                               "resp_id": r.get("orderId"), "err": r.get("_err"), "body": r.get("_body"), "avgPrice": None})
                    self.log(dict(fl[-1], e="flatten", amt=amt))
            return fl, []
        EP.Probe.flatten_own = legacy
    elif MUTANT == "no_universe":
        orig = EP.Probe.pick_symbols
        def pick(self, universe, held, pinned=None):
            return orig(self, set(), held, pinned=pinned)            # v1 语义: 只排除当前持仓名
        EP.Probe.pick_symbols = pick
    elif MUTANT == "no_halt":
        EP.Probe.live_halted = lambda self: (False, "mutant: guard removed")
    elif MUTANT:
        raise SystemExit("unknown mutant %r" % MUTANT)


# ───────────────────────── tests ─────────────────────────
def test_a_foreign_position_untouched():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    # (a1) 单元: 书持有 ATOM/SNX, 自家只在 BANK 有净量 ⇒ 只平 BANK 2362, ATOM/SNX 不动, 记两条 foreign
    api = MockAPI(positions={"ATOMUSDT": 237.72, "SNXUSDT": -806.5, "BANKUSDT": 2362.0, "BTCUSDT": 0.5})
    p = mk_probe(api, live, root); p.ensure_filters(["ATOMUSDT", "SNXUSDT", "BANKUSDT"])
    fl, foreign = p.flatten_own(["ATOMUSDT", "SNXUSDT", "BANKUSDT"], {"BANKUSDT": 2362.0},
                                {"ATOMUSDT": 237.72, "SNXUSDT": -806.5, "BANKUSDT": 2362.0})
    mp = market_posts(api)
    check(len(mp) == 1 and mp[0]["symbol"] == "BANKUSDT" and mp[0]["side"] == "SELL" and float(mp[0]["quantity"]) == 2362
          and mp[0]["reduceOnly"] == "true", "(a1) only own BANK net 2362 flattened (reduceOnly SELL)", mp)
    check(api.positions["ATOMUSDT"] == 237.72 and api.positions["SNXUSDT"] == -806.5, "(a1) book's ATOM/SNX positions untouched",
          {k: api.positions[k] for k in ("ATOMUSDT", "SNXUSDT")})
    check(sorted(f["symbol"] for f in foreign) == ["ATOMUSDT", "SNXUSDT"], "(a1) foreign_position_detected for ATOM & SNX (recorded only)", foreign)
    check(len(events(p, "foreign_position_detected")) == 2, "(a1) two foreign events in events.jsonl")
    # (a2) 集成: 08-21 重放 — 宇宙文件"漏掉" ATOM/SNX(模拟规则 2 失效), 钉名含 ATOM/SNX/BANK, 书持有 ATOM/SNX
    root2 = tempfile.mkdtemp(); live2 = make_live_dir(root2)
    tab = {s: {"span": 2} for s in UNIVERSE if s not in ("ATOMUSDT", "SNXUSDT")}
    tab.update({"EXTRA%03dUSDT" % i: {"span": 2} for i in range(2)})
    json.dump({"table": tab}, open(os.path.join(live2, "config", "funding_span_table.json"), "w"))
    json.dump({"symbols": [s for s in MEMBERS if s not in ("ATOMUSDT", "SNXUSDT")]}, open(os.path.join(live2, "state", "live", "preds_latest.json"), "w"))
    json.dump({"training_member_union": {"symbols": list(tab.keys())}}, open(os.path.join(live2, "checkpoints", "MANIFEST.json"), "w"))
    api2 = MockAPI(positions={"ATOMUSDT": 237.72, "SNXUSDT": -806.5}, fill_plan=plan_incident_shape)
    p2 = mk_probe(api2, live2, root2)
    rec = p2.one_round("T0821", dry=False, pinned=["BANKUSDT", "ATOMUSDT", "SNXUSDT"], slot=SLOT)
    mp2 = market_posts(api2)
    check([m["symbol"] for m in mp2] == ["BANKUSDT"], "(a2) incident replay: flatten set == {BANK} (own net), not ATOM/SNX", mp2)
    check(api2.positions["ATOMUSDT"] == 237.72 and api2.positions["SNXUSDT"] == -806.5, "(a2) incident replay: ATOM/SNX positions unchanged after round",
          {k: api2.positions[k] for k in ("ATOMUSDT", "SNXUSDT")})
    check(sorted(rec["pick_info"]["excluded_held"]) == ["ATOMUSDT", "SNXUSDT"] and rec["symbols"] == ["BANKUSDT"],
          "(a2) held ATOM/SNX excluded at pick time (never become round symbols)", (rec["pick_info"]["excluded_held"], rec["symbols"]))
    check(rec["assert_flatten_only_own"]["ok"] and rec["ok"] is True, "(a2) receipt ok: flatten-only-own, no foreign on round symbols",
          (rec["assert_flatten_only_own"], rec["ok"]))
    check(not any(o["symbol"] in ("ATOMUSDT", "SNXUSDT") for o in rec["orders_placed"]), "(a2) zero probe orders on ATOM/SNX")
    # (a3) 集成: 轮中"书"在本轮名字上建仓(180s 窗口内 BANK +237.72 出现) ⇒ 轮末只平自己净量, 记 foreign, 书的 237.72 留下
    root3 = tempfile.mkdtemp(); live3 = make_live_dir(root3)
    api3 = MockAPI(positions={}, fill_plan=plan_incident_shape)
    def sleep_inject(sec):
        if sec == EP.Probe.K_SECONDS:
            api3.positions["BANKUSDT"] = api3.positions.get("BANKUSDT", 0.0) + 237.72    # 他人仓位在窗口内出现
    home3 = os.path.join(root3, "probe_home")
    p3 = EP.Probe(api3, home=home3, live_dir=live3, sleep=sleep_inject, now=lambda: FIXED_NOW, kill_paths=[os.path.join(home3, "KILL")])
    rec3 = p3.one_round("TA3", dry=False, slot=SLOT)
    fl3 = {f["symbol"]: f for f in rec3["flattens"]}
    check("BANKUSDT" in fl3 and fl3["BANKUSDT"]["qty"] == 2362.0 and abs(api3.positions["BANKUSDT"] - 237.72) < 1e-9,
          "(a3) mid-round foreign BANK +237.72: flatten own 2362 only, 237.72 left on the book", (fl3.get("BANKUSDT"), api3.positions.get("BANKUSDT")))
    check([f["symbol"] for f in rec3["foreign_positions"]] == ["BANKUSDT"] and abs(rec3["foreign_positions"][0]["diff"] - 237.72) < 1e-9,
          "(a3) foreign_position_detected BANK diff=+237.72 in receipt", rec3["foreign_positions"])
    check(rec3["assert_flatten_only_own"]["ok"] and rec3["ok"] is False, "(a3) flatten-only-own ok, round ok=False because foreign present",
          (rec3["assert_flatten_only_own"], rec3["ok"]))
    shutil.rmtree(root); shutil.rmtree(root2); shutil.rmtree(root3)


def test_b_universe_exclusion():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={})                                   # 书空仓 = 08-21 15:15Z 的前提
    p = mk_probe(api, live, root)
    rec = p.one_round("TB", dry=True)
    syms = rec["symbols"]
    check(syms == ["BANKUSDT", "BERAUSDT", "DODOXUSDT", "PARTIUSDT", "JASMYUSDT"], "(b) picked T2x3+T3x2 skipping universe names", syms)
    check(not (set(syms) & set(UNIVERSE)), "(b) picked ∩ universe = ∅", set(syms) & set(UNIVERSE))
    ex = rec["pick_info"]["excluded_universe"]
    check("ATOMUSDT" in ex and "SNXUSDT" in ex and "U130USDT" in ex and "U133USDT" in ex, "(b) ATOM/SNX/U130/U133 excluded as universe hits", ex)
    check(rec["assert_round_syms_disjoint_universe"]["ok"], "(b) receipt assertion round_syms ∩ universe = ∅ ok")
    check(set(rec["pick_info"]["excluded_static"]) >= {"CRVUSDT", "TSLAUSDT", "BTC3LUSDT", "CSOPSAMSUNG2LUSDT", "1000RATSUSDT"},
          "(b) static exclusions still applied", rec["pick_info"]["excluded_static"])
    em = rec["pick_info"]["excluded_meta"]
    check(em.get("USARUSDT") == "underlyingType=EQUITY" and em.get("OLDCOINUSDT") == "status=SETTLING" and "USARUSDT" not in EP.EQUITY_TOKENS,
          "(b) data-driven exclusion: USAR (EQUITY, not in static list) and OLDCOIN (SETTLING) excluded via exchangeInfo", em)
    check(rec["universe"]["n_total"] == 140 and rec["universe"]["sources"][0]["path"].endswith("config/funding_span_table.json"),
          "(b) universe 140 from authoritative span table (+preds +MANIFEST union)", rec["universe"])
    # pinned names also filtered
    rec2 = p.one_round("TB2", dry=True, pinned=["ATOMUSDT", "BANKUSDT", "U005USDT"])
    check(rec2["symbols"] == ["BANKUSDT"] and sorted(rec2["pick_info"]["pinned_dropped"]) == ["ATOMUSDT", "U005USDT"],
          "(b) PROBE_SYMS pinned names in universe are dropped", (rec2["symbols"], rec2["pick_info"]["pinned_dropped"]))
    # preds-only name (not in span table) still excluded via union + inconsistency recorded
    json.dump({"symbols": MEMBERS + ["BANKUSDT"]}, open(os.path.join(live, "state", "live", "preds_latest.json"), "w"))
    rec3 = p.one_round("TB3", dry=True)
    check("BANKUSDT" not in rec3["symbols"] and rec3["universe"]["inconsistencies"] and
          rec3["universe"]["inconsistencies"][0]["not_in_authoritative"] == ["BANKUSDT"],
          "(b) name only in preds_latest is excluded too (union) and inconsistency recorded", (rec3["symbols"], rec3["universe"]["inconsistencies"]))
    shutil.rmtree(root)


def test_c_halt_guard():
    cases = [
        ("state.json reduce_only", dict(state_json={"reduce_only": True, "tripped_at": None}), True),
        ("state.json tripped_at", dict(state_json={"reduce_only": False, "tripped_at": "2026-08-21T20:16:00Z"}), True),
        ("state.json open_orders_halted", dict(state_json={"open_orders_halted": True}), True),
        ("no state.json, last_eval tripped", dict(tripped=True), True),
        ("no state.json, last_eval stale 7h", dict(eval_age_min=7 * 60), True),
        ("last_eval missing", dict(no_last_eval=True), True),
        ("healthy: no state.json, last_eval fresh not tripped", dict(), False),
        ("healthy: state.json present but cleared", dict(state_json={"reduce_only": False, "tripped_at": None}), False),
    ]
    for label, kw, expect in cases:
        root = tempfile.mkdtemp(); live = make_live_dir(root, **kw)
        api = MockAPI(positions={})
        p = mk_probe(api, live, root)
        halted, why = p.live_halted()
        check(halted == expect, "(c) live_halted [%s] -> %s" % (label, expect), why)
        rec = p.one_round("TC", dry=False, slot=SLOT)
        if expect:
            check(rec["skipped"] and rec["skipped"].startswith("live_halted") and not api.posts and not api.deletes,
                  "(c) round skipped, zero writes [%s]" % label, (rec["skipped"], len(api.posts)))
        else:
            check(rec["skipped"] is None and len(api.posts) > 0, "(c) round ran when not halted [%s]" % label, rec["skipped"])
        shutil.rmtree(root)


REQUIRED_RECEIPT_KEYS = ["version", "kind", "round_id", "started_utc", "finished_utc", "dry", "skipped", "halt_guard", "universe",
                         "held_symbols_start", "pick_info", "symbols", "orders_placed", "fills", "own_net", "flattens", "foreign_positions",
                         "positions_round_syms_pre_flatten", "positions_round_syms_end", "assert_touched_disjoint_universe",
                         "assert_flatten_only_own", "assert_round_syms_disjoint_universe", "pnl_estimate", "daily_pnl_after", "ok"]


def test_d_receipt():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={"U001USDT": 100.0, "U002USDT": -50.0})   # 书有仓
    p = mk_probe(api, live, root)
    rec = p.one_round("20260822T0420Z", dry=False, slot=SLOT)
    missing = [k for k in REQUIRED_RECEIPT_KEYS if k not in rec]
    check(not missing, "(d) receipt has all required keys", missing)
    path = os.path.join(p.state_dir, "receipt_20260822T0420Z.json")
    check(os.path.exists(path), "(d) receipt file written at state/receipt_<round>.json", path)
    disk = json.load(open(path))
    check(disk["assert_touched_disjoint_universe"]["ok"] and disk["assert_touched_disjoint_universe"]["intersection"] == [],
          "(d) receipt assertion touched ∩ universe = ∅", disk["assert_touched_disjoint_universe"])
    check(sorted(disk["assert_touched_disjoint_universe"]["touched"]) == sorted(rec["symbols"]), "(d) touched == placed symbols",
          disk["assert_touched_disjoint_universe"]["touched"])
    check(len(disk["orders_placed"]) == 20 and len(disk["fills"]) == 20, "(d) 5 names x 2 arms x 2 sides = 20 orders, 20 final states",
          (len(disk["orders_placed"]), len(disk["fills"])))
    exp_net = {}
    for o in api.orders.values():
        if o.get("clientOrderId", "").startswith("probe2"):
            exp_net[o["symbol"]] = exp_net.get(o["symbol"], 0.0) + (float(o["executedQty"]) if o["side"] == "BUY" else -float(o["executedQty"]))
    check(all(abs(disk["own_net"].get(s, 0.0) - v) < 1e-9 for s, v in exp_net.items()), "(d) own_net == sum of own fills (qb-qa residual per arm, v1 sizing)",
          (disk["own_net"], exp_net))
    fq = {f["symbol"]: f["qty"] for f in disk["flattens"]}
    check(all(abs(fq.get(s, 0.0) - EP.rnd(abs(v), STEP[s])) < 1e-9 for s, v in exp_net.items()), "(d) each flatten qty == own residual (floored to step)", (fq, exp_net))
    check(disk["ok"] is True and disk["foreign_positions"] == [], "(d) ok=True, no foreign", (disk["ok"], disk["foreign_positions"]))
    check(set(disk["universe"]["sources"][0].keys()) >= {"path", "n", "sha256", "role"}, "(d) universe provenance (path/n/sha256) in receipt")
    check(disk["held_symbols_start"] == ["U001USDT", "U002USDT"], "(d) held symbols at start recorded (names only)", disk["held_symbols_start"])
    check(all(v == 0.0 for v in disk["positions_round_syms_end"].values()), "(d) end positions on round names all 0", disk["positions_round_syms_end"])
    check(not os.path.exists(p.pending_path), "(d) pending ledger cleared after clean round")
    shutil.rmtree(root)


def test_e_incident_shape_accounting():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={}, fill_plan=plan_incident_shape)
    p = mk_probe(api, live, root)
    rec = p.one_round("TE", dry=False, slot=SLOT)
    fl = {f["symbol"]: f for f in rec["flattens"]}
    check(abs(rec["own_net"]["BANKUSDT"] - 2362.0) < 1e-9, "(e) BANK own net = 393+1969 (sells -5022 rejected)", rec["own_net"])
    check("BANKUSDT" in fl and fl["BANKUSDT"]["qty"] == 2362.0 and fl["BANKUSDT"]["side"] == "SELL", "(e) BANK flattened by own net 2362", fl.get("BANKUSDT"))
    exp_net = {}
    for o in api.orders.values():
        if o.get("clientOrderId", "").startswith("probe2"):
            exp_net[o["symbol"]] = exp_net.get(o["symbol"], 0.0) + (float(o["executedQty"]) if o["side"] == "BUY" else -float(o["executedQty"]))
    check("BERAUSDT" in fl and abs(fl["BERAUSDT"]["qty"] - EP.rnd(exp_net["BERAUSDT"], 0.1)) < 1e-9 and abs(exp_net["BERAUSDT"] - 0.4) < 1e-9,
          "(e) BERA flattened by own net 0.4 (= 0.2 sizing residual + 0.2 short-fill), step 0.1", (fl.get("BERAUSDT"), exp_net.get("BERAUSDT")))
    check("DODOXUSDT" in fl and fl["DODOXUSDT"]["qty"] == EP.rnd(exp_net["DODOXUSDT"], 1.0) == 6.0, "(e) DODOX flattened by own net 6 (= 3 residual + 3 short-fill)",
          (fl.get("DODOXUSDT"), exp_net.get("DODOXUSDT")))
    check(all(abs(api.positions.get(s, 0.0)) < 1e-9 for s in ("BANKUSDT", "BERAUSDT", "DODOXUSDT")), "(e) positions 0 after flatten", api.positions)
    check(rec["ok"] and rec["assert_flatten_only_own"]["ok"] and rec["foreign_positions"] == [], "(e) receipt ok, no foreign", rec["foreign_positions"])
    check(set(f["symbol"] for f in rec["flattens"]) <= set(rec["symbols"]), "(e) flatten symbols ⊆ round symbols")
    check(rec["pnl_estimate"]["net_usdt_approx"] < 0 and rec["daily_pnl_after"]["rounds"] == 1, "(e) pnl estimate computed (negative: taker flatten+fees)", rec["pnl_estimate"])
    shutil.rmtree(root)


def test_f_mixed_own_and_foreign():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={"BANKUSDT": 247.0, "SNXUSDT": -796.0, "XXXUSDT": 40.0})
    p = mk_probe(api, live, root); p.ensure_filters(["BANKUSDT", "SNXUSDT", "XXXUSDT"])
    fl, foreign = p.flatten_own(["BANKUSDT", "SNXUSDT", "XXXUSDT"], {"BANKUSDT": 10.0, "SNXUSDT": 10.0, "XXXUSDT": 100.0},
                                dict(api.positions))
    byq = {m["symbol"]: float(m["quantity"]) for m in market_posts(api)}
    check(byq.get("BANKUSDT") == 10.0 and api.positions["BANKUSDT"] == 237.0, "(f) same-name own 10 + foreign 237: flatten 10, leave 237", (byq, api.positions))
    check("SNXUSDT" not in byq and api.positions["SNXUSDT"] == -796.0, "(f) sign mismatch (own +10 on a -796 book short): no order", (byq, api.positions))
    check(byq.get("XXXUSDT") == 40.0, "(f) own 100 but account 40: capped at 40 (never more than position)", byq)
    check(sorted(f["symbol"] for f in foreign) == ["BANKUSDT", "SNXUSDT", "XXXUSDT"], "(f) all three recorded as foreign (acct != own)", foreign)
    sk = [e for e in events(p, "flatten_skipped") if e["symbol"] == "SNXUSDT"]
    check(sk and sk[0]["reason"] == "sign_mismatch", "(f) flatten_skipped sign_mismatch logged for SNX", sk)
    shutil.rmtree(root)


def test_g_universe_unreadable():
    for label, kw in (("span table missing", dict(no_span=True)), ("span table too small", dict(small_span=True))):
        root = tempfile.mkdtemp(); live = make_live_dir(root, **kw)
        api = MockAPI(positions={})
        p = mk_probe(api, live, root)
        rec = p.one_round("TG", dry=False, slot=SLOT)
        check(rec["skipped"] and rec["skipped"].startswith("universe_unreadable") and not api.posts and not api.deletes,
              "(g) %s => round skipped, zero writes" % label, (rec["skipped"], len(api.posts)))
        shutil.rmtree(root)


def test_h_recovery():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={"ATOMUSDT": 237.72})
    p = mk_probe(api, live, root)
    # 模拟上一轮: BANK 买 393 成交(进程随后被杀), ATOM 是书的
    o = api._post({"symbol": "BANKUSDT", "side": "BUY", "type": "LIMIT", "timeInForce": "GTX", "quantity": "393", "price": "0.03809",
                   "newClientOrderId": "probe2_X_BANKUSDT_B"})
    o2 = api._post({"symbol": "BANKUSDT", "side": "SELL", "type": "LIMIT", "timeInForce": "GTX", "quantity": "393", "price": "0.0381",
                    "newClientOrderId": "probe2_X_BANKUSDT_S"})
    api.orders[o2["orderId"]]["status"] = "NEW"; api.orders[o2["orderId"]]["executedQty"] = "0"; api.positions["BANKUSDT"] = 393.0
    api.posts.clear()
    EP.atomic_write_json(p.pending_path, {"round_id": "KILLED", "symbols": ["BANKUSDT", "ATOMUSDT"], "orders": [
        {"symbol": "BANKUSDT", "orderId": o["orderId"], "clientOrderId": "probe2_X_BANKUSDT_B", "side": "BUY", "px": 0.03809, "q": 393.0, "arm": "base"},
        {"symbol": "BANKUSDT", "orderId": o2["orderId"], "clientOrderId": "probe2_X_BANKUSDT_S", "side": "SELL", "px": 0.0381, "q": 393.0, "arm": "base"}]})
    rec = p.recover_pending()
    mp = market_posts(api)
    check(len(mp) == 1 and mp[0]["symbol"] == "BANKUSDT" and float(mp[0]["quantity"]) == 393.0, "(h) recovery flattens own BANK 393 only", mp)
    check(any(d.get("orderId") == o2["orderId"] for d in api.deletes), "(h) recovery cancels the still-open own SELL", api.deletes)
    check(api.positions["ATOMUSDT"] == 237.72, "(h) recovery never touches ATOM (not in ledger)")
    check(not os.path.exists(p.pending_path) and os.path.exists(os.path.join(p.state_dir, "receipt_recovery_KILLED.json")),
          "(h) ledger cleared + recovery receipt written")
    shutil.rmtree(root)


def test_i_no_candidates():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    tick, ranked = make_ticker()
    new = list(ranked)
    left = ["ATOMUSDT", "SNXUSDT"] + ["U%03dUSDT" % i for i in range(130, 138)]     # 未进前 130 的宇宙名
    k = 0
    for i in list(range(130, 200)) + list(range(300, 380)):
        new[i] = left[k] if k < len(left) else "LEV%03d3LUSDT" % i                 # 其余 = 杠杆代币(正则排除)
        k += 1
    assert len(set(new)) == 400
    tick2 = [{"symbol": s, "quoteVolume": str(1e9 - i * 1e6)} for i, s in enumerate(new)]
    api = MockAPI(positions={}, ticker=(tick2, new))
    p = mk_probe(api, live, root)
    rec = p.one_round("TI", dry=False, slot=SLOT)
    check(rec["skipped"] == "no_candidates" and not api.posts, "(i) empty candidates => skip_round_no_candidates, zero writes", (rec["skipped"], rec["symbols"]))
    check(bool(events(p, "skip_round_no_candidates")), "(i) event logged")
    check(len(rec["pick_info"]["excluded_universe"]) == 10 and len(rec["pick_info"]["excluded_static"]) == 140, "(i) exclusions itemised: 10 universe + 140 static",
          (len(rec["pick_info"]["excluded_universe"]), len(rec["pick_info"]["excluded_static"])))
    shutil.rmtree(root)


def test_j_off_slot():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={})
    late = SLOT + datetime.timedelta(minutes=25)
    p = mk_probe(api, live, root, now=lambda: late)
    rec = p.one_round("TJ", dry=False, slot=SLOT)
    check(rec["skipped"] == "off_slot" and not api.posts, "(j) 25 min late => skip_round_off_slot, zero writes", rec["skipped"])
    ok_t = SLOT + datetime.timedelta(minutes=5)
    p2 = mk_probe(MockAPI(positions={}), live, root, now=lambda: ok_t)
    rec2 = p2.one_round("TJ2", dry=False, slot=SLOT)
    check(rec2["skipped"] is None, "(j) 5 min late => runs", rec2["skipped"])
    shutil.rmtree(root)


def test_k_daily_loss_stop():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={})
    p = mk_probe(api, live, root)
    EP.atomic_write_json(p.daily_path, {"date": FIXED_NOW.strftime("%Y-%m-%d"), "net_usdt_approx": -12.5, "rounds": 3})
    rec = p.one_round("TK", dry=False, slot=SLOT)
    check(rec["skipped"] == "daily_loss_stop" and not api.posts, "(k) daily approx loss -12.5 < -10 => skip rounds, zero writes", rec["skipped"])
    EP.atomic_write_json(p.daily_path, {"date": "2026-08-21", "net_usdt_approx": -12.5, "rounds": 3})
    rec2 = p.one_round("TK2", dry=False, slot=SLOT)
    check(rec2["skipped"] is None, "(k) yesterday's loss does not stop today", rec2["skipped"])
    shutil.rmtree(root)


def test_l_open_orders():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={}, open_orders={"BANKUSDT": [{"orderId": 1, "clientOrderId": "20260822T0400Z-BANKUSDT-1"}],
                                             "BERAUSDT": [{"orderId": 7, "clientOrderId": "probe_1787329201_BERAUSDT_B"}]})
    p = mk_probe(api, live, root)
    rec = p.one_round("TL", dry=False, slot=SLOT)
    placed_syms = {o["symbol"] for o in rec["orders_placed"]}
    check("BANKUSDT" not in placed_syms and "BANKUSDT" in rec["foreign_open_order_syms"], "(l) name with someone else's open order is skipped", (placed_syms, rec["foreign_open_order_syms"]))
    check(any(d.get("orderId") == 7 for d in api.deletes) and "BERAUSDT" in placed_syms, "(l) own orphan probe* order swept, name still traded", api.deletes)
    check(bool(events(p, "foreign_open_order")) and bool(events(p, "sweep_orphan")), "(l) both events logged")
    shutil.rmtree(root)


def test_m_verbs_and_kill():
    rc = EP.main([])
    check(rc == 2, "(m) no verb => usage, rc=2 (no API touched)", rc)
    rc2 = EP.main(["--help"])
    check(rc2 == 2, "(m) unknown verb => usage", rc2)
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    p = mk_probe(MockAPI(), live, root)
    check(not p.killed(), "(m) no KILL => not killed")
    open(p.kill_paths[0], "w").close()
    check(p.killed(), "(m) KILL present => killed()")
    # run_forever must exit before any round when KILL present
    out = []
    p.run_forever(out=out.append)
    check(out == ["KILLED"] and not p.api.posts, "(m) run_forever exits immediately on KILL, zero writes", out)
    shutil.rmtree(root)


def test_n_dry_zero_writes():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    api = MockAPI(positions={"U001USDT": 5.0}, open_orders={"BERAUSDT": [{"orderId": 7, "clientOrderId": "probe_old_BERAUSDT_B"}]})
    p = mk_probe(api, live, root)
    rec = p.one_round("TN", dry=True)
    writes = [c for c in api.calls if c[0] in ("POST", "DELETE")]
    check(not writes, "(n) --dry issues zero POST/DELETE", writes)
    check(rec["kind"] == "dry" and rec["dry"] is True and rec["symbols"] and rec["orders_placed"] == [], "(n) dry receipt: symbols picked, no orders", rec["symbols"])
    check(bool(events(p, "would_sweep_orphan")) and not events(p, "sweep_orphan"), "(n) dry logs would_sweep_orphan, does not cancel")
    check(len(events(p, "quote")) == 5, "(n) 5 quotes logged", len(events(p, "quote")))
    shutil.rmtree(root)


def test_o_slots():
    root = tempfile.mkdtemp(); live = make_live_dir(root)
    p = mk_probe(MockAPI(), live, root)
    n1 = p.next_slot(datetime.datetime(2026, 8, 22, 4, 20, 30, tzinfo=datetime.timezone.utc))
    n2 = p.next_slot(datetime.datetime(2026, 8, 22, 23, 50, 0, tzinfo=datetime.timezone.utc))
    n3 = p.next_slot(datetime.datetime(2026, 8, 22, 4, 19, 59, tzinfo=datetime.timezone.utc))
    check(n1.hour == 8 and n1.minute == 20 and n2.day == 23 and n2.hour == 0 and n3.hour == 4, "(o) next_slot arithmetic", (n1, n2, n3))
    check(EP.Probe.slot_id(n1) == "20260822T0820Z", "(o) slot id format", EP.Probe.slot_id(n1))
    shutil.rmtree(root)


def main():
    apply_mutant()
    if MUTANT:
        print("### MUTANT ACTIVE: %s (expect RED below)" % MUTANT)
    for t in (test_a_foreign_position_untouched, test_b_universe_exclusion, test_c_halt_guard, test_d_receipt, test_e_incident_shape_accounting,
              test_f_mixed_own_and_foreign, test_g_universe_unreadable, test_h_recovery, test_i_no_candidates, test_j_off_slot,
              test_k_daily_loss_stop, test_l_open_orders, test_m_verbs_and_kill, test_n_dry_zero_writes, test_o_slots):
        try:
            t()
        except Exception as ex:
            import traceback
            check(False, "%s raised" % t.__name__, traceback.format_exc()[-600:])
    n_ok = sum(1 for r in RESULTS if r[0]); n = len(RESULTS)
    print("\n%s: %d/%d checks passed%s" % ("MUTANT[%s]" % MUTANT if MUTANT else "exec_probe v2 tests", n_ok, n,
                                          "" if n_ok == n else "  FAILED=%d" % (n - n_ok)))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
