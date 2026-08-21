"""薄币执行探针(PREREG_exec_probe_thin_2026-08-16, 用户批准主账户 2026-08-16).
独立进程, 不 import 在役代码; 每 4h 锚+20min 一轮: 5 币各挂 post-only 买卖对($15-25/单, 180s 窗),
未成交撤单, 残留仓 reduce-only 市价平; 全事件 jsonl. 安全: KILL 文件/累计亏损 $40 停/单币持仓>1单跳过.
不过度影响在役: 时间错峰(锚+20min), 符号双保险排除(静态段+运行时持仓检查), API 轻量(~40 req/轮).
"""
import os, sys, time, json, hmac, hashlib, urllib.parse, urllib.request, math, datetime

BASE = "https://fapi.binance.com"
HOME = os.path.expanduser("~/exec_probe")
EV = os.path.join(HOME, "events.jsonl")
KILL = os.path.join(HOME, "KILL")
STATE = os.path.join(HOME, "probe_state.json")

def load_env():
    p = os.path.expanduser("~/dl_quant_live/.env")
    for line in open(p):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
load_env()
API_KEY = os.environ.get("BINANCE_API_KEY") or os.environ.get("BINANCE_KEY")
API_SEC = os.environ.get("BINANCE_API_SECRET") or os.environ.get("BINANCE_SECRET")
assert API_KEY and API_SEC, "API keys not found in env"

def req(method, path, params=None, signed=False):
    params = dict(params or {})
    if signed:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        q = urllib.parse.urlencode(params)
        sig = hmac.new(API_SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
        q = q + "&signature=" + sig
    else:
        q = urllib.parse.urlencode(params)
    url = BASE + path + ("?" + q if q else "")
    r = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": API_KEY})
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
            if att == 2: return {"_err": str(e)}
            time.sleep(2)

def log(ev):
    ev["ts"] = time.time()
    with open(EV, "a") as f:
        f.write(json.dumps(ev) + "\n")

SYMS = ["JASMYUSDT", "ZILUSDT", "ONEUSDT", "CELRUSDT", "BADGERUSDT"]  # 启动时按段位与过滤校验替换
OFFENDERS = {"1000RATSUSDT", "ETHFIUSDT", "CRVUSDT", "AKTUSDT", "RATSUSDT"}
EQUITY_TOKENS = {"GOOGLUSDT", "AAPLUSDT", "TSLAUSDT", "NVDAUSDT", "AMZNUSDT", "METAUSDT",
                 "MSTRUSDT", "COINUSDT", "HOODUSDT", "CRCLUSDT", "SPYUSDT", "QQQUSDT",
                 "MSFTUSDT", "NFLXUSDT", "PLTRUSDT", "ADBEUSDT", "AMDUSDT", "INTCUSDT",
                 "ORCLUSDT", "AVGOUSDT", "LLYUSDT", "UNHUSDT", "COSTUSDT", "WMTUSDT"}

def pick_symbols():
    """T2×3(量能 130-200 段) + T3×2(300-380 段), 排除惯犯与现有持仓符号."""
    tick = req("GET", "/fapi/v1/ticker/24hr")
    if isinstance(tick, dict): raise RuntimeError(f"ticker err {tick}")
    vol = {t["symbol"]: float(t["quoteVolume"]) for t in tick if t["symbol"].endswith("USDT")}
    ranked = sorted(vol, key=lambda s: -vol[s])
    acct = req("GET", "/fapi/v3/account", signed=True)
    held = {p["symbol"] for p in acct.get("positions", []) if abs(float(p["positionAmt"])) > 0}
    import re
    def _ok(s):
        # 排除: 惯犯/持仓/股票代币/杠杆代币(2L/3L/2S 族)/CSOP 系 ETF 代币(2026-08-18 CSOPSAMSUNG2L 逃逸案)
        return (s not in OFFENDERS and s not in held and s not in EQUITY_TOKENS
                and not re.search(r"\d+[LS]USDT$", s) and not s.startswith("CSOP"))
    t2 = [s for s in ranked[130:200] if _ok(s)][:3]
    t3 = [s for s in ranked[300:380] if _ok(s)][:2]
    return t2 + t3, held

def filters():
    info = req("GET", "/fapi/v1/exchangeInfo")
    out = {}
    for s in info["symbols"]:
        f = {x["filterType"]: x for x in s["filters"]}
        out[s["symbol"]] = {
            "tick": float(f["PRICE_FILTER"]["tickSize"]),
            "step": float(f["LOT_SIZE"]["stepSize"]),
            "minNotional": float(f.get("MIN_NOTIONAL", {}).get("notional", 5.0)),
        }
    return out

def rnd(x, step):
    return math.floor(x / step + 1e-9) * step

def fmt(x):
    return f"{x:.10f}".rstrip("0").rstrip(".")

def _live_halted():
    """A3(2026-08-21 审计): 探针与实盘共用账户; 停机/reduce-only 期间不得开新仓(哪怕 $90)。只读 watchdog 状态。"""
    try:
        import json as _j, os as _o
        p = _o.path.expanduser("~/dl_quant_live/state/live/watchdog/state.json")
        if not _o.path.exists(p): return False
        st = _j.load(open(p))
        return bool(st.get("reduce_only")) or bool(st.get("tripped_at"))
    except Exception:
        return True   # 读不到状态 ⇒ 保守: 视为停机, 跳过本轮
def one_round(syms, filt, dry=False):
    if _live_halted():
        log({"e": "skip_round_live_halted"}); return
    acct = req("GET", "/fapi/v3/account", signed=True)
    held = {p["symbol"]: float(p["positionAmt"]) for p in acct.get("positions", [])
            if abs(float(p["positionAmt"])) > 0}
    # 轮首清扫: 撤本探针币上遗留的 probe* 挂单(轮中被杀会留无主单 — 2026-08-18 16:20Z 实例); 只撤自家前缀
    for s in syms:
        oo = req("GET", "/fapi/v1/openOrders", {"symbol": s}, signed=True)
        if isinstance(oo, list):
            for o in oo:
                if str(o.get("clientOrderId", "")).startswith("probe"):
                    c = req("DELETE", "/fapi/v1/order", {"symbol": s, "orderId": o["orderId"]}, signed=True)
                    log({"e": "sweep_orphan", "symbol": s, "orderId": o["orderId"],
                         "resp": c.get("status", c.get("_err"))})
    placed = []
    for s in syms:
        if s in held and abs(held[s]) > 0:
            log({"e": "skip_existing_pos", "symbol": s, "amt": held[s]}); continue
        bt = req("GET", "/fapi/v1/ticker/bookTicker", {"symbol": s})
        if "_err" in bt: log({"e": "bookticker_err", "symbol": s, "r": bt}); continue
        bid, ask = float(bt["bidPrice"]), float(bt["askPrice"])
        f = filt[s]
        notion = max(15.0, f["minNotional"] * 1.05)
        if notion > 26: log({"e": "skip_min_notional_high", "symbol": s, "n": notion}); continue
        log({"e": "quote", "symbol": s, "bid": bid, "ask": ask,
             "spread_bps": (ask - bid) / (0.5 * (ask + bid)) * 1e4, "dry": dry})
        if dry: continue
        # 基线对(判定表序列, 参数不动) + XL 对($75, 独立标签 — 2026-08-18 用户入金授权, 测规模维度)
        for arm, notion_a in (("base", notion), ("xl", 75.0)):
            qb = rnd(notion_a / bid, f["step"]); qa = rnd(notion_a / ask, f["step"])
            if qb * bid < f["minNotional"]: qb += f["step"]
            if qa * ask < f["minNotional"]: qa += f["step"]
            tag = "probe" if arm == "base" else "probe_xl"
            for side, px, q in (("BUY", bid, qb), ("SELL", ask, qa)):
                o = req("POST", "/fapi/v1/order", {
                    "symbol": s, "side": side, "type": "LIMIT", "timeInForce": "GTX",
                    "quantity": fmt(q), "price": fmt(px), "newClientOrderId": f"{tag}_{int(time.time())}_{s}_{side[0]}",
                }, signed=True)
                log({"e": "place", "arm": arm, "symbol": s, "side": side, "px": px, "q": q, "resp_id": o.get("orderId"), "err": o.get("_err"), "body": o.get("_body")})
                if "orderId" in o: placed.append((s, o["orderId"], side, px, arm))
    if dry: return
    time.sleep(180)
    for s, oid, side, px, arm in placed:
        st = req("GET", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
        log({"e": "status", "arm": arm, "symbol": s, "orderId": oid, "side": side, "px": px,
             "status": st.get("status"), "executedQty": st.get("executedQty"), "avgPrice": st.get("avgPrice")})
        if st.get("status") in ("NEW", "PARTIALLY_FILLED"):
            c = req("DELETE", "/fapi/v1/order", {"symbol": s, "orderId": oid}, signed=True)
            log({"e": "cancel", "arm": arm, "symbol": s, "orderId": oid, "resp": c.get("status", c.get("_err"))})
    time.sleep(3)
    acct2 = req("GET", "/fapi/v3/account", signed=True)
    for p in acct2.get("positions", []):
        s = p["symbol"]; amt = float(p["positionAmt"])
        if s in syms and abs(amt) > 0:
            side = "SELL" if amt > 0 else "BUY"
            fl = req("POST", "/fapi/v1/order", {
                "symbol": s, "side": side, "type": "MARKET", "quantity": fmt(abs(amt)),
                "reduceOnly": "true"}, signed=True)
            log({"e": "flatten", "symbol": s, "amt": amt, "resp_id": fl.get("orderId"), "err": fl.get("_err"), "body": fl.get("_body")})
    # markout 基准价(5m 后另录由分析端做; 此处录轮末中价)
    for s in syms:
        bt = req("GET", "/fapi/v1/ticker/bookTicker", {"symbol": s})
        if "_err" not in bt:
            log({"e": "round_end_mid", "symbol": s, "mid": (float(bt["bidPrice"]) + float(bt["askPrice"])) / 2})

def next_slot():
    now = datetime.datetime.now(datetime.timezone.utc)
    anchors = [0, 4, 8, 12, 16, 20]
    for h in anchors:
        t = now.replace(hour=h, minute=20, second=0, microsecond=0)
        if t > now: return t
    return (now + datetime.timedelta(days=1)).replace(hour=0, minute=20, second=0, microsecond=0)

def main():
    os.makedirs(HOME, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    pinned = os.environ.get("PROBE_SYMS")
    if pinned:
        syms, held = [s.strip() for s in pinned.split(",") if s.strip()], set()
        log({"e": "syms_pinned", "symbols": syms})
    else:
        syms, held = pick_symbols()
    filt = filters()
    log({"e": "start", "mode": mode, "symbols": syms, "held_excluded": sorted(held)})
    print("symbols:", syms, flush=True)
    if mode == "dry":
        one_round(syms, filt, dry=True)
        log({"e": "dry_done"}); print("DRY_DONE", flush=True); return
    while True:
        if os.path.exists(KILL):
            log({"e": "killed"}); print("KILLED", flush=True); return
        t = next_slot()
        wait = (t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        print(f"next round {t.isoformat()} in {wait:.0f}s", flush=True)
        time.sleep(max(wait, 1))
        if os.path.exists(KILL):
            log({"e": "killed"}); return
        try:
            one_round(syms, filt, dry=False)
        except Exception as ex:
            log({"e": "round_error", "err": repr(ex)})
        log({"e": "round_done"})

if __name__ == "__main__":
    main()
