"""薄币执行探针 v2 (2026-08-22) — 修 E-0821-C 的三条 + 两条防御.

v1 事故(docs/INCIDENT_daily_loss_trip_2026-08-21.md §S, ERROR_LEDGER E-0821-C): 轮末 `if s in syms and |amt|>0: 市价平`
不分仓位归属, 把实盘书的 ATOM/SNX 平掉 ⇒ 看门狗 5b/5e 真触发 ⇒ 整书平仓。v2 三条硬规则:
  1. 只平自己建的仓: 轮末只按本轮自己 orderId 的 executedQty 累计净量平(reduceOnly, 数量=min(|自己净量|,|账户持仓|), 同号才平);
     名字上"账户持仓 ≠ 自己净量"一律记 `foreign_position_detected`, 只记不动。
  2. 排除集合 = 在役书数据宇宙 ∪ 宽书成员宇宙 ∪ 账户当前任何持仓名(每轮重选; team-lead 2026-08-22 更正版):
     在役 = ~/dl_quant_live/config/funding_span_table.json["table"] 键(140 = 面板列集, 月度成员 110 在其内选; = MANIFEST training_member_union)
            ∪ state/live/preds_latest.json["symbols"] ∪ checkpoints/MANIFEST.json union;
     宽书 = ~/wide_shadow/state/weights/<最新 anchor>.npz["members"](400 下标 → shadow_bundle/config.json["symbols_panel"] 829 符号轴)
            ∪ config.json["symbols_live"](450 抓取全集, 成员在其内轮换);
     任一组读不到 ⇒ 跳轮; 候选不足 5 取能取到的, 为空 ⇒ 跳轮记事件。
  3. 对账收据: 每轮 state/receipt_<round>.json(下单集/成交/平仓/轮末持仓/"触碰名 ∩ 宇宙 = ∅"断言/"平仓 ≤ 自己净量"断言); 停机守卫沿用且加固
     (state.json reduce_only/tripped_at/open_orders_halted 或 last_eval.json tripped 或 last_eval 过期 >6h 或读不到 ⇒ 跳轮)。
  防御: (i) 轮必须在名义槽 [锚+20min, 锚+40min] 内开始, 否则跳(机器睡醒不越锚); (ii) 下单前落盘 pending_round.json, 被杀后下次启动只对
     账本里的 orderId 做成交核对+只平自己净量(recovery 收据); (iii) 单日探针估算净损 < −$10 ⇒ 当日余轮跳过(PREREG 安全线, 估算值);
     (iv) 候选名上有非 probe 前缀的挂单 ⇒ 该名跳过; (v) PROBE_SYMS 钉名同样过宇宙过滤; (vi) 没有 `run` 参数不启动; KILL 每 30s 检查。
独立进程, 不 import 在役代码, 不写 ~/dl_quant_live 任何文件(只读 4 个文件)。事件流 ~/exec_probe/v2/events.jsonl(字段与 v1 兼容)。
"""
import os, sys, time, json, hmac, hashlib, urllib.parse, urllib.request, math, datetime, re

BASE = "https://fapi.binance.com"
HOME = os.path.expanduser(os.environ.get("PROBE_HOME", "~/exec_probe/v2"))
LIVE_DIR = os.path.expanduser(os.environ.get("PROBE_LIVE_DIR", "~/dl_quant_live"))
WIDE_DIR = os.path.expanduser(os.environ.get("PROBE_WIDE_DIR", "~/wide_shadow"))
KILL_PATHS = [os.path.expanduser("~/exec_probe/KILL"), os.path.join(HOME, "KILL")]

OFFENDERS = {"1000RATSUSDT", "ETHFIUSDT", "CRVUSDT", "AKTUSDT", "RATSUSDT"}
EQUITY_TOKENS = {"GOOGLUSDT", "AAPLUSDT", "TSLAUSDT", "NVDAUSDT", "AMZNUSDT", "METAUSDT",
                 "MSTRUSDT", "COINUSDT", "HOODUSDT", "CRCLUSDT", "SPYUSDT", "QQQUSDT",
                 "MSFTUSDT", "NFLXUSDT", "PLTRUSDT", "ADBEUSDT", "AMDUSDT", "INTCUSDT",
                 "ORCLUSDT", "AVGOUSDT", "LLYUSDT", "UNHUSDT", "COSTUSDT", "WMTUSDT"}
CLIENT_PREFIX = "probe"          # v1 "probe_"/"probe_xl_" 与 v2 "probe2_"/"probe2xl_" 都以它开头; 书的 client_id = "{rid}-{SYM}-n"


class UniverseUnreadable(Exception):
    pass


class ApiError(Exception):
    pass


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_iso_z(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def rnd(x, step):
    return math.floor(x / step + 1e-9) * step


def fmt(x):
    return f"{x:.10f}".rstrip("0").rstrip(".")


def sign(x):
    return (x > 0) - (x < 0)


def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    os.replace(tmp, path)


def load_env(p=os.path.expanduser("~/dl_quant_live/.env")):
    if not os.path.exists(p):
        return
    for line in open(p):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


class BinanceAPI:
    def __init__(self, key, secret, base=BASE):
        self.key, self.secret, self.base = key, secret, base

    def req(self, method, path, params=None, signed=False):
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            q = urllib.parse.urlencode(params)
            sig = hmac.new(self.secret.encode(), q.encode(), hashlib.sha256).hexdigest()
            q = q + "&signature=" + sig
        else:
            q = urllib.parse.urlencode(params)
        url = self.base + path + ("?" + q if q else "")
        r = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": self.key})
        for att in range(3):
            try:
                with urllib.request.urlopen(r, timeout=15) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                if att == 2 or e.code in (400, 401, 403):
                    return {"_err": e.code, "_body": body}
                time.sleep(2)
            except Exception as e:
                if att == 2:
                    return {"_err": str(e)}
                time.sleep(2)


class Probe:
    SLOT_MINUTE = 20            # 锚+20min 错峰(书 k=900s 窗在锚+0..+16min 内结束)
    SLOT_GRACE_MIN = 20         # 名义槽之后最多晚 20min 开轮; 再晚跳过(不越下一锚)
    K_SECONDS = 180
    T2_BAND, N_T2 = (130, 200), 3
    T3_BAND, N_T3 = (300, 380), 2
    NOTIONAL_BASE_MIN, NOTIONAL_BASE_MAX, NOTIONAL_XL = 15.0, 26.0, 75.0
    WATCHDOG_MAX_AGE_H = 6.0
    DAILY_LOSS_STOP_USDT = 10.0
    UNIVERSE_MIN_SIZE = 100
    FEE_MAKER, FEE_TAKER = 0.0002, 0.0005   # 估算用

    WIDE_MAX_AGE_H = 30.0       # 宽书权重文件比这更旧只记 wide_universe_stale(仍用于排除), 不跳轮

    def __init__(self, api, home=HOME, live_dir=LIVE_DIR, sleep=time.sleep, now=now_utc, kill_paths=None, wide_dir=WIDE_DIR):
        self.api, self.home, self.live_dir, self.sleep, self.now = api, home, live_dir, sleep, now
        self.wide_dir = wide_dir
        self.kill_paths = list(kill_paths) if kill_paths is not None else KILL_PATHS
        self.state_dir = os.path.join(home, "state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.ev_path = os.path.join(home, "events.jsonl")
        self.pending_path = os.path.join(self.state_dir, "pending_round.json")
        self.daily_path = os.path.join(self.state_dir, "daily_pnl.json")
        self.filt = {}

    # ───────────────────────── 基础 ─────────────────────────
    def log(self, ev):
        ev = dict(ev)
        ev["ts"] = time.time()
        with open(self.ev_path, "a") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        return ev

    def killed(self):
        return any(os.path.exists(p) for p in self.kill_paths)

    def _get(self, path, params=None, signed=False):
        r = self.api.req("GET", path, params, signed=signed)
        if isinstance(r, dict) and "_err" in r:
            raise ApiError(f"GET {path} {params}: {r}")
        return r

    # ───────────────────────── 规则 2: 宇宙 ─────────────────────────
    def load_live_universe(self):
        """在役书数据宇宙。权威 = config/funding_span_table.json["table"] 键(140); 并集 preds_latest.json symbols(110) + MANIFEST union(140)。
        权威读不到/太小/非 USDT 名 ⇒ UniverseUnreadable。返回 (set, sources, inconsistencies)。"""
        sources, incons = [], []
        p1 = os.path.join(self.live_dir, "config", "funding_span_table.json")
        try:
            tab = json.load(open(p1))["table"]
            cols = set(tab.keys())
        except Exception as e:
            raise UniverseUnreadable("%s: %r" % (p1, e))
        if len(cols) < self.UNIVERSE_MIN_SIZE or not all(isinstance(x, str) and x.endswith("USDT") for x in cols):
            raise UniverseUnreadable("%s: table has %d keys / non-USDT keys present — refusing" % (p1, len(cols)))
        uni = set(cols)
        sources.append({"path": p1, "key": "table(keys)", "n": len(cols), "sha256": sha256_file(p1), "role": "live_authoritative"})
        extras = [
            (os.path.join(self.live_dir, "state", "live", "preds_latest.json"), "symbols", lambda d: d["symbols"]),
            (os.path.join(self.live_dir, "checkpoints", "MANIFEST.json"), "training_member_union.symbols",
             lambda d: d["training_member_union"]["symbols"]),
        ]
        for p, key, getter in extras:
            try:
                x = set(getter(json.load(open(p))))
                sources.append({"path": p, "key": key, "n": len(x), "sha256": sha256_file(p), "role": "live_union"})
                if not x <= cols:
                    incons.append({"path": p, "not_in_authoritative": sorted(x - cols)})
                uni |= x
            except Exception as e:
                sources.append({"path": p, "key": key, "error": repr(e), "role": "live_union"})
        return uni, sources, incons

    def load_wide_universe(self):
        """宽书成员宇宙(team-lead 2026-08-22 更正)。权威 = ~/wide_shadow/state/weights/<最新 anchor>.npz["members"](400 个 int32 下标)
        → ~/wide_shadow/shadow_bundle/config.json["symbols_panel"](829, 符号轴)映射成符号; 并上 config.json["symbols_live"](450 = 宽书每锚
        抓取/选员的候选全集, 成员在其内轮换 — 2026-08-22 核: 400 ⊂ 450 ⊂ 829, 29 个权重文件成员并集 421)。
        任一读不到/numpy 缺/下标越界/成员 <50 ⇒ UniverseUnreadable(调用方跳轮)。权重文件过旧只记 stale。返回 (set, sources, stale)。"""
        sources = []
        cfgp = os.path.join(self.wide_dir, "shadow_bundle", "config.json")
        try:
            cfg = json.load(open(cfgp))
            panel = list(cfg["symbols_panel"]); live450 = set(cfg["symbols_live"])
        except Exception as e:
            raise UniverseUnreadable("%s: %r" % (cfgp, e))
        wdir = os.path.join(self.wide_dir, "state", "weights")
        try:
            files = sorted(f for f in os.listdir(wdir) if f.endswith(".npz"))
            latest = os.path.join(wdir, files[-1])
            import numpy as np
            z = np.load(latest)
            m = [int(i) for i in z["members"].tolist()]
        except Exception as e:
            raise UniverseUnreadable("%s: %r" % (wdir, e))
        if len(m) < 50 or min(m) < 0 or max(m) >= len(panel):
            raise UniverseUnreadable("%s: members invalid n=%d range=[%d,%d] panel=%d" % (latest, len(m), min(m) if m else -1, max(m) if m else -1, len(panel)))
        members = {panel[i] for i in m}
        try:
            anchor_ts = int(os.path.splitext(os.path.basename(latest))[0])
            age_h = (self.now().timestamp() - anchor_ts) / 3600.0
        except Exception:
            anchor_ts = None; age_h = (time.time() - os.path.getmtime(latest)) / 3600.0
        stale = age_h > self.WIDE_MAX_AGE_H
        sources.append({"path": latest, "key": "members(idx->symbols_panel)", "n": len(members), "sha256": sha256_file(latest),
                        "role": "wide_members", "anchor_ts": anchor_ts, "age_h": round(age_h, 2), "stale": stale})
        sources.append({"path": cfgp, "key": "symbols_live", "n": len(live450), "sha256": sha256_file(cfgp), "role": "wide_fetch_universe"})
        sources.append({"path": cfgp, "key": "symbols_panel", "n": len(panel), "role": "wide_symbol_axis"})
        if not members <= live450:
            sources.append({"note": "members not subset of symbols_live", "n_outside": len(members - live450)})
        return members | live450, sources, stale

    def load_universe(self):
        """排除集合的宇宙部分 = 在役 140 ∪ 宽书 400/450(持仓名由调用方并上)。返回 (set, meta, groups); 任一组读不到 ⇒ UniverseUnreadable。"""
        live, lsrc, incons = self.load_live_universe()
        wide, wsrc, stale = self.load_wide_universe()
        uni = live | wide
        meta = {"sources": lsrc + wsrc, "inconsistencies": incons, "n_live": len(live), "n_wide": len(wide),
                "n_live_and_wide": len(live & wide), "n_total": len(uni), "wide_stale": stale}
        return uni, meta, {"live": live, "wide": wide}

    # ───────────────────────── 规则 3b: 停机守卫 ─────────────────────────
    def live_halted(self):
        """(halted, reason)。只读看门狗两文件; 任何读不到/过期 ⇒ 保守 True。
        state.json 不在 = 看门狗自身语义的"未触发"(resume_from_trip.sh 归档后删除); 但 last_eval.json 必须可读、新鲜且 tripped=False。"""
        wd = os.path.join(self.live_dir, "state", "live", "watchdog")
        sp, lp = os.path.join(wd, "state.json"), os.path.join(wd, "last_eval.json")
        try:
            if os.path.exists(sp):
                st = json.load(open(sp))
                if st.get("reduce_only") or st.get("tripped_at") or st.get("open_orders_halted"):
                    return True, ("state.json: reduce_only=%s tripped_at=%s open_orders_halted=%s"
                                  % (st.get("reduce_only"), st.get("tripped_at"), st.get("open_orders_halted")))
            le = json.load(open(lp))
            if le.get("tripped"):
                return True, "last_eval.json tripped=True: %s" % (le.get("triggers"),)
            age_h = (self.now() - parse_iso_z(le["evaluated_utc"])).total_seconds() / 3600.0
            if age_h > self.WATCHDOG_MAX_AGE_H:
                return True, "last_eval.json stale: evaluated %s (%.1fh > %.1fh)" % (le["evaluated_utc"], age_h, self.WATCHDOG_MAX_AGE_H)
            return False, "state.json %s; last_eval %s tripped=False age %.2fh" % (
                "absent" if not os.path.exists(sp) else "not halted", le["evaluated_utc"], age_h)
        except Exception as e:
            return True, "watchdog state unreadable: %r" % (e,)

    # ───────────────────────── 账户 / 过滤器 ─────────────────────────
    def account_positions(self):
        acct = self._get("/fapi/v3/account", signed=True)
        if not isinstance(acct, dict) or "positions" not in acct:
            raise ApiError("account response without positions: %r" % (str(acct)[:200],))
        out = {}
        for p in acct["positions"]:
            amt = float(p.get("positionAmt") or 0)
            if abs(amt) > 0:
                out[p["symbol"]] = out.get(p["symbol"], 0.0) + amt
        return out

    def ensure_filters(self, syms=None, force=False):
        """exchangeInfo → 过滤器 + 合约元数据(underlyingType/contractType/status; 选币用数据驱动排除股票/商品/指数类 perp —
        2026-08-22 空跑首轮 USARUSDT(EQUITY/TRADIFI_PERPETUAL)穿过了 v1 的静态股票名单, 交易所当时有 173 个非 COIN perp)。"""
        if not force and syms is not None and self.filt and all(s in self.filt for s in syms):
            return
        info = self._get("/fapi/v1/exchangeInfo")
        for s in info["symbols"]:
            f = {x["filterType"]: x for x in s["filters"]}
            self.filt[s["symbol"]] = {
                "tick": float(f["PRICE_FILTER"]["tickSize"]),
                "step": float(f["LOT_SIZE"]["stepSize"]),
                "minNotional": float(f.get("MIN_NOTIONAL", {}).get("notional", 5.0)),
                "underlyingType": s.get("underlyingType", "COIN"),
                "contractType": s.get("contractType", "PERPETUAL"),
                "status": s.get("status", "TRADING"),
            }

    def symbol_meta_reason(self, s):
        """None = 可选; 否则返回排除原因(数据驱动: 非 COIN 标的 / 非永续 / 非 TRADING / 交易所无此合约)。"""
        m = self.filt.get(s)
        if m is None:
            return "not_in_exchangeInfo"
        if m.get("underlyingType") != "COIN":
            return "underlyingType=%s" % m.get("underlyingType")
        if m.get("contractType") != "PERPETUAL":
            return "contractType=%s" % m.get("contractType")
        if m.get("status") != "TRADING":
            return "status=%s" % m.get("status")
        return None

    # ───────────────────────── 规则 2: 选币 ─────────────────────────
    def pick_symbols(self, universe, held, pinned=None, groups=None):
        """T2 段[130,200) 取 3 + T3 段[300,380) 取 2(不足取能取到的, 为空由调用方跳轮), 排除: 宇宙(在役 140 ∪ 宽书 400/450)/账户持仓名/
        惯犯/股票代币/杠杆代币/CSOP/exchangeInfo 非 COIN。pinned(PROBE_SYMS) 同样过滤。返回 (syms, info); info 记每类排除的命中名(收据证据)。"""
        info = {"excluded_universe": [], "excluded_universe_by": {}, "excluded_held": [], "excluded_static": [], "excluded_meta": {},
                "pinned_dropped": [], "ranks": {}, "vol24": {}}
        groups = groups or {}
        self.ensure_filters(None, force=True)                  # 每轮刷新 exchangeInfo(权重 1): 新上市/状态变更/标的类型

        def ok(s):
            if s in universe:
                info["excluded_universe"].append(s)
                info["excluded_universe_by"][s] = "+".join(g for g in ("live", "wide") if s in groups.get(g, ())) or "universe"
                return False
            if s in held:
                info["excluded_held"].append(s); return False
            if (s in OFFENDERS or s in EQUITY_TOKENS or re.search(r"\d+[LS]USDT$", s) or s.startswith("CSOP")
                    or not s.endswith("USDT") or not all(ord(ch) < 128 for ch in s)):     # 非 ASCII 名(如 币安人生USDT): 未测的编码路径, 保守排除
                info["excluded_static"].append(s); return False
            why = self.symbol_meta_reason(s)
            if why:
                info["excluded_meta"][s] = why; return False
            return True

        if pinned:
            syms = [s for s in pinned if ok(s)]
            info["pinned_dropped"] = [s for s in pinned if s not in syms]
            info["mode"] = "pinned"
            return syms, info
        tick = self._get("/fapi/v1/ticker/24hr")
        if not isinstance(tick, list):
            raise ApiError("ticker/24hr not a list")
        vol = {t["symbol"]: float(t["quoteVolume"]) for t in tick if str(t.get("symbol", "")).endswith("USDT")}
        ranked = sorted(vol, key=lambda s: -vol[s])
        t2 = [s for s in ranked[self.T2_BAND[0]:self.T2_BAND[1]] if ok(s)][:self.N_T2]
        t3 = [s for s in ranked[self.T3_BAND[0]:self.T3_BAND[1]] if ok(s)][:self.N_T3]
        syms = t2 + t3
        info["mode"] = "ranked"
        info["n_ranked"] = len(ranked)
        info["ranks"] = {s: ranked.index(s) for s in syms}
        info["vol24"] = {s: vol[s] for s in syms}
        return syms, info

    # ───────────────────────── 下单 / 结算 ─────────────────────────
    def sweep_orders(self, syms, dry):
        """轮首: 撤自家前缀(probe*)的遗留挂单(只撤自家); 名字上有非自家挂单 ⇒ 该名本轮跳过(只记)。返回 (touched_set, foreign_order_syms)."""
        touched, foreign = set(), set()
        for s in syms:
            oo = self.api.req("GET", "/fapi/v1/openOrders", {"symbol": s}, signed=True)
            if not isinstance(oo, list):
                self.log({"e": "open_orders_err", "symbol": s, "r": oo}); foreign.add(s); continue
            for o in oo:
                cid = str(o.get("clientOrderId", ""))
                if cid.startswith(CLIENT_PREFIX):
                    if dry:
                        self.log({"e": "would_sweep_orphan", "symbol": s, "orderId": o.get("orderId"), "clientOrderId": cid}); continue
                    c = self.api.req("DELETE", "/fapi/v1/order", {"symbol": s, "orderId": o["orderId"]}, signed=True)
                    touched.add(s)
                    self.log({"e": "sweep_orphan", "symbol": s, "orderId": o["orderId"], "clientOrderId": cid,
                              "resp": c.get("status", c.get("_err")) if isinstance(c, dict) else c})
                else:
                    foreign.add(s)
                    self.log({"e": "foreign_open_order", "symbol": s, "orderId": o.get("orderId"), "clientOrderId": cid})
        return touched, foreign

    def place_orders(self, s, round_id, dry):
        """一币: 基线对($15-26)+XL 对($75), post-only(GTX)。返回 placed 列表(含 orderId)。"""
        f = self.filt[s]
        bt = self.api.req("GET", "/fapi/v1/ticker/bookTicker", {"symbol": s})
        if not isinstance(bt, dict) or "_err" in bt:
            self.log({"e": "bookticker_err", "symbol": s, "r": bt}); return []
        bid, ask = float(bt["bidPrice"]), float(bt["askPrice"])
        notion = max(self.NOTIONAL_BASE_MIN, f["minNotional"] * 1.05)
        if notion > self.NOTIONAL_BASE_MAX:
            self.log({"e": "skip_min_notional_high", "symbol": s, "n": notion}); return []
        self.log({"e": "quote", "symbol": s, "bid": bid, "ask": ask,
                  "spread_bps": (ask - bid) / (0.5 * (ask + bid)) * 1e4, "dry": dry})
        if dry:
            return []
        placed = []
        for arm, notion_a in (("base", notion), ("xl", self.NOTIONAL_XL)):
            qb = rnd(notion_a / bid, f["step"]); qa = rnd(notion_a / ask, f["step"])
            if qb * bid < f["minNotional"]: qb += f["step"]
            if qa * ask < f["minNotional"]: qa += f["step"]
            tag = "probe2" if arm == "base" else "probe2xl"
            for side, px, q in (("BUY", bid, qb), ("SELL", ask, qa)):
                cid = f"{tag}_{round_id}_{s}_{side[0]}"[:36]
                o = self.api.req("POST", "/fapi/v1/order", {
                    "symbol": s, "side": side, "type": "LIMIT", "timeInForce": "GTX",
                    "quantity": fmt(q), "price": fmt(px), "newClientOrderId": cid}, signed=True)
                if not isinstance(o, dict):
                    o = {"_err": "non-dict", "_body": str(o)[:200]}
                self.log({"e": "place", "arm": arm, "symbol": s, "side": side, "px": px, "q": q,
                          "resp_id": o.get("orderId"), "err": o.get("_err"), "body": o.get("_body"), "clientOrderId": cid})
                if "orderId" in o:
                    placed.append({"symbol": s, "orderId": o["orderId"], "clientOrderId": cid, "side": side,
                                   "px": px, "q": q, "arm": arm})
        return placed

    def finalize_orders(self, placed):
        """查每张自家单 → 未完成的撤 → 取最终 executedQty。返回 fills{orderId: {...}}, unknown_syms(状态拿不到的名)。"""
        fills, unknown = {}, set()
        for o in placed:
            s, oid = o["symbol"], o["orderId"]
            st = self.api.req("GET", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
            if not isinstance(st, dict) or "status" not in st:
                st = self.api.req("GET", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
            if not isinstance(st, dict) or "status" not in st:
                self.log({"e": "status_unknown", "symbol": s, "orderId": oid, "r": st}); unknown.add(s); continue
            self.log({"e": "status", "arm": o["arm"], "symbol": s, "orderId": oid, "side": o["side"], "px": o["px"],
                      "status": st.get("status"), "executedQty": st.get("executedQty"), "avgPrice": st.get("avgPrice")})
            final = st
            if st.get("status") in ("NEW", "PARTIALLY_FILLED"):
                c = self.api.req("DELETE", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
                self.log({"e": "cancel", "arm": o["arm"], "symbol": s, "orderId": oid,
                          "resp": c.get("status", c.get("_err")) if isinstance(c, dict) else c})
                if isinstance(c, dict) and "executedQty" in c:
                    final = c                                   # 撤单回执带最终 executedQty
                else:
                    st2 = self.api.req("GET", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
                    if isinstance(st2, dict) and "status" in st2:
                        final = st2
                    else:
                        self.log({"e": "status_unknown_after_cancel", "symbol": s, "orderId": oid, "r": st2}); unknown.add(s); continue
            fills[str(oid)] = {"symbol": s, "side": o["side"], "arm": o["arm"], "status": final.get("status"),
                               "executedQty": float(final.get("executedQty") or 0), "avgPrice": float(final.get("avgPrice") or 0),
                               "px": o["px"], "q": o["q"]}
        return fills, unknown

    @staticmethod
    def own_net_from_fills(fills):
        net = {}
        for f in fills.values():
            net[f["symbol"]] = net.get(f["symbol"], 0.0) + (f["executedQty"] if f["side"] == "BUY" else -f["executedQty"])
        return net

    # ───────────────────────── 规则 1: 只平自己 ─────────────────────────
    def flatten_own(self, round_syms, own_net, positions, unknown_syms=()):
        """对本轮名字: 账户持仓 ≠ 自己净量 ⇒ foreign_position_detected(只记); 自己净量≠0 且与持仓同号 ⇒ reduceOnly 市价平
        min(|净量|,|持仓|)。绝不对 round_syms 以外的名字发任何单; 绝不平超过自己净量。返回 (flattens, foreign)。"""
        flattens, foreign = [], []
        for s in sorted(round_syms):
            step = self.filt.get(s, {}).get("step", 1e-9)
            tol = max(step * 0.5, 1e-12)
            net = float(own_net.get(s, 0.0)); pos = float(positions.get(s, 0.0))
            if abs(pos - net) > tol:
                rec = {"symbol": s, "acct_pos": pos, "own_net": net, "diff": pos - net}
                foreign.append(rec); self.log(dict(rec, e="foreign_position_detected"))
            if abs(net) < tol:
                continue                                        # 自己净量为 0: 名字上有仓也不是我的
            if s in unknown_syms:
                self.log({"e": "flatten_skipped", "symbol": s, "reason": "unknown_fills", "own_net": net, "acct_pos": pos}); continue
            if pos == 0 or sign(pos) != sign(net):
                self.log({"e": "flatten_skipped", "symbol": s, "reason": "no_position" if pos == 0 else "sign_mismatch",
                          "own_net": net, "acct_pos": pos}); continue
            qty = rnd(min(abs(net), abs(pos)), step)
            if qty < step:
                self.log({"e": "flatten_skipped", "symbol": s, "reason": "dust", "own_net": net, "acct_pos": pos}); continue
            side = "SELL" if net > 0 else "BUY"
            fl = self.api.req("POST", "/fapi/v1/order", {"symbol": s, "side": side, "type": "MARKET",
                                                          "quantity": fmt(qty), "reduceOnly": "true"}, signed=True)
            if not isinstance(fl, dict):
                fl = {"_err": "non-dict", "_body": str(fl)[:200]}
            rec = {"symbol": s, "side": side, "qty": qty, "own_net": net, "acct_pos": pos,
                   "resp_id": fl.get("orderId"), "err": fl.get("_err"), "body": fl.get("_body"), "avgPrice": None}
            if "orderId" in fl:
                st = self.api.req("GET", "/fapi/v1/order", {"symbol": s, "orderId": fl["orderId"]}, signed=True)
                if isinstance(st, dict) and st.get("avgPrice"):
                    rec["avgPrice"] = float(st["avgPrice"]); rec["executedQty"] = float(st.get("executedQty") or 0)
            flattens.append(rec)
            self.log(dict(rec, e="flatten", amt=net))        # v1 兼容字段 amt = 自己净量(不是账户全量)
        return flattens, foreign

    # ───────────────────────── 盈亏估算 / 日停 ─────────────────────────
    def pnl_estimate(self, fills, flattens):
        cash, fee = 0.0, 0.0
        for f in fills.values():
            n = f["executedQty"] * f["avgPrice"]
            cash += n if f["side"] == "SELL" else -n
            fee += n * self.FEE_MAKER
        for fl in flattens:
            if fl.get("avgPrice") and fl.get("executedQty"):
                n = fl["executedQty"] * fl["avgPrice"]
                cash += n if fl["side"] == "SELL" else -n
                fee += n * self.FEE_TAKER
        return {"cash_usdt": cash, "fee_usdt_approx": fee, "net_usdt_approx": cash - fee}

    def _daily(self, today):
        try:
            d = json.load(open(self.daily_path))
            if d.get("date") == today:
                return d
        except Exception:
            pass
        return {"date": today, "net_usdt_approx": 0.0, "rounds": 0}

    def daily_loss_stopped(self, today):
        d = self._daily(today)
        return d["net_usdt_approx"] < -self.DAILY_LOSS_STOP_USDT, d

    def daily_add(self, today, net):
        d = self._daily(today)
        d["net_usdt_approx"] += float(net); d["rounds"] += 1
        atomic_write_json(self.daily_path, d)
        return d

    # ───────────────────────── 账本恢复(被杀后) ─────────────────────────
    def recover_pending(self):
        """pending_round.json 存在(上一轮下单后未收口) ⇒ 只对账本里的 orderId 对账 + 只平自己净量; 写 receipt_recovery_<round>.json。"""
        if not os.path.exists(self.pending_path):
            return None
        try:
            pend = json.load(open(self.pending_path))
        except Exception as e:
            self.log({"e": "recovery_ledger_unreadable", "err": repr(e)}); return None
        placed = pend.get("orders", [])
        syms = sorted({o["symbol"] for o in placed})
        self.log({"e": "recovery_start", "round_id": pend.get("round_id"), "n_orders": len(placed), "symbols": syms})
        self.ensure_filters(syms)
        fills, unknown = self.finalize_orders(placed)
        own_net = self.own_net_from_fills(fills)
        positions = self.account_positions()
        flattens, foreign = self.flatten_own(syms, own_net, positions, unknown)
        pos_end = self.account_positions()
        rec = {"version": "v2", "kind": "recovery", "round_id": pend.get("round_id"), "recovered_utc": self.now().isoformat(),
               "orders_placed": placed, "fills": fills, "own_net": own_net, "flattens": flattens, "foreign_positions": foreign,
               "unknown_syms": sorted(unknown), "positions_round_syms_end": {s: pos_end.get(s, 0.0) for s in syms}}
        rec.update(self._assertions(syms, set(), set(syms), fills, flattens, own_net, positions, foreign))
        p = os.path.join(self.state_dir, "receipt_recovery_%s.json" % pend.get("round_id", "unknown"))
        atomic_write_json(p, rec)
        if unknown:
            self.log({"e": "recovery_partial", "unknown_syms": sorted(unknown), "receipt": p})   # 账本保留, 下次再试
        else:
            os.remove(self.pending_path)
            self.log({"e": "recovery_done", "receipt": p})
        return rec

    # ───────────────────────── 收据断言 ─────────────────────────
    def _assertions(self, round_syms, universe, touched, fills, flattens, own_net, positions_pre_flatten, foreign):
        inter = sorted(set(touched) & set(universe))
        over = []
        for fl in flattens:
            if fl.get("err"):
                continue
            s = fl["symbol"]
            if fl["qty"] > abs(own_net.get(s, 0.0)) + 1e-9 or fl["qty"] > abs(positions_pre_flatten.get(s, 0.0)) + 1e-9:
                over.append(fl)
        return {"assert_touched_disjoint_universe": {"touched": sorted(touched), "intersection": inter, "ok": not inter,
                                                    "set": "live140 ∪ wide400/450 ∪ held", "n_set": len(universe)},
                "assert_flatten_only_own": {"n_flattens": len(flattens), "violations": over, "ok": not over},
                "assert_round_syms_disjoint_universe": {"intersection": sorted(set(round_syms) & set(universe)),
                                                        "ok": not (set(round_syms) & set(universe))}}

    # ───────────────────────── 一轮 ─────────────────────────
    def one_round(self, round_id, dry=False, pinned=None, slot=None):
        t0 = self.now()
        today = t0.strftime("%Y-%m-%d")
        rec = {"version": "v2", "kind": "dry" if dry else "round", "round_id": round_id, "started_utc": t0.isoformat(),
               "dry": dry, "skipped": None}
        touched, flattens, foreign, fills, own_net, positions_end = set(), [], [], {}, {}, {}
        syms, universe, pick_info, positions = [], set(), {}, {}
        try:
            halted, why = self.live_halted()
            rec["halt_guard"] = {"halted": halted, "reason": why}
            if halted:
                self.log({"e": "skip_round_live_halted", "reason": why}); rec["skipped"] = "live_halted:" + why
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            if slot is not None and not dry:
                late_min = (t0 - slot).total_seconds() / 60.0
                rec["slot"] = {"nominal": slot.isoformat(), "late_min": late_min}
                if late_min < -1 or late_min > self.SLOT_GRACE_MIN:
                    self.log({"e": "skip_round_off_slot", "late_min": late_min}); rec["skipped"] = "off_slot"
                    return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            stopped, d = self.daily_loss_stopped(today)
            rec["daily_pnl_before"] = d
            if stopped and not dry:
                self.log({"e": "skip_round_daily_loss_stop", "daily": d}); rec["skipped"] = "daily_loss_stop"
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            try:
                universe, umeta, groups = self.load_universe()
            except UniverseUnreadable as e:
                self.log({"e": "universe_unreadable", "err": str(e)}); rec["skipped"] = "universe_unreadable:" + str(e)
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            rec["universe"] = umeta
            self.log({"e": "universe_loaded", "n_live": umeta["n_live"], "n_wide": umeta["n_wide"], "n_total": umeta["n_total"],
                      "sources": [(x.get("path"), x.get("key"), x.get("n")) for x in umeta["sources"]],
                      "inconsistencies": umeta["inconsistencies"], "wide_stale": umeta["wide_stale"]})
            if umeta["wide_stale"]:
                self.log({"e": "wide_universe_stale", "sources": [x for x in umeta["sources"] if x.get("role") == "wide_members"]})
            if not dry:
                self.recover_pending()
            positions = self.account_positions()
            rec["held_symbols_start"] = sorted(positions)
            held = set(positions)
            uni_lw = universe                                  # 在役 140 ∪ 宽书 400/450(选币归因用)
            universe = uni_lw | held                           # 排除集合 = 在役 ∪ 宽书 ∪ 账户当前任何持仓名(断言/收据用)
            rec["exclusion_set"] = {"n_live": umeta["n_live"], "n_wide": umeta["n_wide"], "n_held": len(held),
                                    "n_held_outside_universe": len(held - uni_lw), "n_total": len(universe)}
            syms, pick_info = self.pick_symbols(uni_lw, held, pinned=pinned, groups=groups)
            rec["pick_info"] = pick_info
            if pick_info.get("pinned_dropped"):
                self.log({"e": "pinned_dropped", "dropped": pick_info["pinned_dropped"]})
            bad = sorted(set(syms) & universe)
            if bad:                                            # 按构造不可能; 仍做独立断言
                self.log({"e": "skip_round_universe_overlap", "overlap": bad}); rec["skipped"] = "universe_overlap"; syms = []
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            if not syms:
                self.log({"e": "skip_round_no_candidates", "pick_info": pick_info}); rec["skipped"] = "no_candidates"
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            self.log({"e": "symbols_picked", "symbols": syms, "ranks": pick_info.get("ranks"), "mode": pick_info.get("mode"),
                      "n_excluded_universe": len(pick_info["excluded_universe"]), "n_excluded_held": len(pick_info["excluded_held"])})
            self.ensure_filters(syms)
            swept, foreign_orders = self.sweep_orders(syms, dry)
            touched |= swept
            rec["foreign_open_order_syms"] = sorted(foreign_orders)
            placed = []
            pend = {"round_id": round_id, "orders": placed, "symbols": syms, "started_utc": t0.isoformat()}
            for s in syms:
                if s in positions and abs(positions[s]) > 0:   # 轮首已持仓(持仓名已在选币排除; 钉名路径可能到这)
                    self.log({"e": "skip_existing_pos", "symbol": s, "amt": positions[s]}); continue
                if s in foreign_orders:
                    self.log({"e": "skip_foreign_open_order", "symbol": s}); continue
                new = self.place_orders(s, round_id, dry)
                if new:
                    placed.extend(new); touched.add(s)
                    atomic_write_json(self.pending_path, pend)  # 下单即落盘(被杀可恢复)
            rec["orders_placed"] = placed
            if dry:
                rec["skipped"] = None
                return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)
            if placed:
                self.sleep(self.K_SECONDS)
            fills, unknown = self.finalize_orders(placed)
            own_net = self.own_net_from_fills(fills)
            rec["unknown_syms"] = sorted(unknown)
            self.sleep(3)
            positions_mid = self.account_positions()
            round_syms = sorted({o["symbol"] for o in placed} | set(syms))
            flattens, foreign = self.flatten_own(round_syms, own_net, positions_mid, unknown)
            touched |= {fl["symbol"] for fl in flattens if not fl.get("err")}
            positions_end = self.account_positions()
            rec["positions_round_syms_pre_flatten"] = {s: positions_mid.get(s, 0.0) for s in round_syms}
            for s in syms:
                bt = self.api.req("GET", "/fapi/v1/ticker/bookTicker", {"symbol": s})
                if isinstance(bt, dict) and "_err" not in bt:
                    self.log({"e": "round_end_mid", "symbol": s, "mid": (float(bt["bidPrice"]) + float(bt["askPrice"])) / 2})
            pnl = self.pnl_estimate(fills, flattens)
            rec["pnl_estimate"] = pnl
            rec["daily_pnl_after"] = self.daily_add(today, pnl["net_usdt_approx"])
            if not unknown and os.path.exists(self.pending_path):
                os.remove(self.pending_path)
            return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net,
                                positions_mid if placed else positions, foreign, positions_end)
        except Exception as ex:
            self.log({"e": "round_error", "err": repr(ex)})
            rec["error"] = repr(ex)
            return self._finish(rec, round_id, syms, universe, touched, fills, flattens, own_net, positions, foreign, positions_end)

    def _finish(self, rec, round_id, syms, universe, touched, fills, flattens, own_net, positions_pre, foreign, positions_end):
        rec["symbols"] = list(syms)
        rec["fills"] = fills; rec["own_net"] = own_net; rec["flattens"] = flattens; rec["foreign_positions"] = foreign
        rec["positions_round_syms_end"] = {s: positions_end.get(s, 0.0) for s in syms} if positions_end else {}
        rec.update(self._assertions(syms, universe, touched, fills, flattens, own_net, positions_pre, foreign))
        rec["ok"] = (rec["assert_touched_disjoint_universe"]["ok"] and rec["assert_flatten_only_own"]["ok"]
                     and rec["assert_round_syms_disjoint_universe"]["ok"] and not foreign and not rec.get("error"))
        rec["finished_utc"] = self.now().isoformat()
        p = os.path.join(self.state_dir, "receipt_%s.json" % round_id)
        atomic_write_json(p, rec)
        rec["receipt_path"] = p
        self.log({"e": "receipt_written", "path": p, "ok": rec["ok"], "skipped": rec.get("skipped")})
        self.log({"e": "dry_done" if rec["dry"] else "round_done", "round_id": round_id})
        return rec

    # ───────────────────────── 调度 ─────────────────────────
    def next_slot(self, now=None):
        now = now or self.now()
        for h in (0, 4, 8, 12, 16, 20):
            t = now.replace(hour=h, minute=self.SLOT_MINUTE, second=0, microsecond=0)
            if t > now:
                return t
        return (now + datetime.timedelta(days=1)).replace(hour=0, minute=self.SLOT_MINUTE, second=0, microsecond=0)

    @staticmethod
    def slot_id(slot):
        return slot.strftime("%Y%m%dT%H%MZ")

    def run_forever(self, pinned=None, out=print):
        while True:
            if self.killed():
                self.log({"e": "killed"}); out("KILLED"); return
            slot = self.next_slot()
            out("next round %s in %.0fs" % (slot.isoformat(), (slot - self.now()).total_seconds()))
            while True:                                        # 30s 粒度等待, KILL 一分钟内生效
                wait = (slot - self.now()).total_seconds()
                if wait <= 0:
                    break
                self.sleep(min(wait, 30))
                if self.killed():
                    self.log({"e": "killed"}); out("KILLED"); return
            rid = self.slot_id(slot)
            try:
                rec = self.one_round(rid, dry=False, pinned=pinned, slot=slot)
                out("round %s ok=%s skipped=%s symbols=%s" % (rid, rec.get("ok"), rec.get("skipped"), rec.get("symbols")))
            except Exception as ex:
                self.log({"e": "round_error", "err": repr(ex)}); out("round %s error %r" % (rid, ex))


def _dry_report(rec, out=print):
    out("=== exec_probe v2 DRY RUN (no orders; read-only API) ===")
    out("utc now      : %s" % rec["started_utc"])
    hg = rec.get("halt_guard", {})
    out("halt guard   : halted=%s  (%s)" % (hg.get("halted"), hg.get("reason")))
    u = rec.get("universe", {})
    for s in u.get("sources", []):
        out("universe src : %s [%s] n=%s role=%s %s" % (s.get("path"), s.get("key"), s.get("n"), s.get("role"),
                                                         ("ERROR " + s["error"]) if s.get("error") else ("sha256=" + s.get("sha256", "")[:12])))
    out("universe     : n_live=%s n_wide=%s overlap=%s n_total=%s wide_stale=%s inconsistencies=%s" % (
        u.get("n_live"), u.get("n_wide"), u.get("n_live_and_wide"), u.get("n_total"), u.get("wide_stale"), u.get("inconsistencies")))
    es = rec.get("exclusion_set", {})
    out("exclusion set: live %s ∪ wide %s ∪ held %s (held outside both: %s) = %s names" % (
        es.get("n_live"), es.get("n_wide"), es.get("n_held"), es.get("n_held_outside_universe"), es.get("n_total")))
    out("held (acct)  : %d names (all excluded)" % len(rec.get("held_symbols_start", [])))
    pi = rec.get("pick_info", {})
    out("pick         : mode=%s ranked=%s  excluded_universe=%d  excluded_held=%d  excluded_static=%d  pinned_dropped=%s" % (
        pi.get("mode"), pi.get("n_ranked"), len(pi.get("excluded_universe", [])), len(pi.get("excluded_held", [])),
        len(pi.get("excluded_static", [])), pi.get("pinned_dropped")))
    out("excluded_universe hits in bands: %d  by-group: %s" % (len(pi.get("excluded_universe", [])),
        dict((g, sum(1 for v in pi.get("excluded_universe_by", {}).values() if v == g)) for g in ("live", "wide", "live+wide", "universe"))))
    out("excluded_universe names: %s" % (pi.get("excluded_universe"),))
    out("excluded_meta (non-COIN/non-perp/non-trading): %s" % (pi.get("excluded_meta"),))
    out("symbols      : %s" % (rec.get("symbols"),))
    for s in rec.get("symbols", []):
        out("   %-14s rank=%s vol24=%.0f" % (s, pi.get("ranks", {}).get(s), pi.get("vol24", {}).get(s, 0.0)))
    out("assert picked ∩ universe = ∅ : %s (intersection=%s)" % (rec["assert_round_syms_disjoint_universe"]["ok"],
                                                                  rec["assert_round_syms_disjoint_universe"]["intersection"]))
    out("skipped      : %s" % rec.get("skipped"))
    out("foreign open orders on picked: %s" % rec.get("foreign_open_order_syms"))
    out("receipt      : %s" % rec.get("receipt_path"))
    out("ok           : %s" % rec.get("ok"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("run", "--dry", "dry"):
        print("usage: python3 exec_probe.py run | --dry      (no default: an explicit verb is required)")
        return 2
    load_env()
    key = os.environ.get("BINANCE_API_KEY") or os.environ.get("BINANCE_KEY")
    sec = os.environ.get("BINANCE_API_SECRET") or os.environ.get("BINANCE_SECRET")
    assert key and sec, "API keys not found in env"
    probe = Probe(BinanceAPI(key, sec))
    pinned = os.environ.get("PROBE_SYMS")
    pinned = [s.strip() for s in pinned.split(",") if s.strip()] if pinned else None
    if argv[0] in ("--dry", "dry"):
        rid = "dry_" + probe.now().strftime("%Y%m%dT%H%M%SZ")
        probe.log({"e": "start", "mode": "dry", "round_id": rid, "pinned": pinned})
        rec = probe.one_round(rid, dry=True, pinned=pinned)
        _dry_report(rec)
        print("DRY_DONE", flush=True)
        return 0
    if probe.killed():
        print("KILL file present (%s) — refusing to start. Remove it deliberately after the README checklist." % probe.kill_paths)
        return 3
    halted, why = probe.live_halted()
    try:
        uni, umeta, _g = probe.load_universe()
        ulog = "%d names (live %d ∪ wide %d) from %d sources" % (len(uni), umeta["n_live"], umeta["n_wide"], len(umeta["sources"]))
    except UniverseUnreadable as e:
        ulog = "UNREADABLE: %s" % e
    probe.log({"e": "start", "mode": "run", "pinned": pinned, "halt_guard": why, "universe": ulog})
    print("exec_probe v2 start | halt_guard: halted=%s (%s) | universe: %s | pinned=%s" % (halted, why, ulog, pinned), flush=True)
    probe.run_forever(pinned=pinned, out=lambda m: print(m, flush=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
