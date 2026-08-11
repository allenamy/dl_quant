"""STEP B — chunked reduce-only exit of the two positions the ladder could not close.

Ordered by team-lead 2026-07-26 after the 12:00Z trip left MEMEUSDT / 1000BONKUSDT short and
`flatten_all` kept hitting [-4005] Quantity greater than max quantity.

★ THE BINDING FILTER IS MARKET_LOT_SIZE.maxQty = 100,000, WHICH SymbolFilters NEVER LOADS.
  LOT_SIZE.maxQty is 10,000,000 (not binding). `submit()` sends type=MARKET whenever no price is
  set, and `flatten_all` sets none — so the market cap applies and a 271,229-contract exit can
  never go as one order.

FENCES (all abort, none advisory):
  - testnet base url, testnet creds only, no BINANCE_KEY, no BINANCE_LIVE_CONFIRM
  - One-way mode (else reduceOnly is unsendable)
  - only the two named symbols; only the REDUCING direction; position must be SHORT
  - every chunk <= CAP and >= min_qty, on the step grid, and <= MAX_CHUNK_NOTIONAL
  - position must strictly shrink after every order, else abort
  - hard cap on total orders
Every request and response is appended to the evidence log before the next order is sent.
"""
import os, sys, json, math, time

assert "BINANCE_LIVE_CONFIRM" not in os.environ, "LIVE_CONFIRM present — abort"
assert not os.environ.get("BINANCE_KEY"), "prod key present — abort"
assert os.environ.get("BINANCE_TESTNET_KEY"), "testnet key missing"

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
import binance_broker as BB

TARGETS = ("MEMEUSDT", "1000BONKUSDT")
CAP = 100000.0            # MARKET_LOT_SIZE.maxQty, read from exchangeInfo at 13:16Z
STEP = 1.0
MIN_QTY = 1.0
MAX_CHUNK_NOTIONAL = 400.0
MAX_ORDERS = 12

TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
EV = os.path.join(REPO, "state/testnet_evidence/exam_1200Z", f"manual_flatten_{TS}.jsonl")
os.makedirs(os.path.dirname(EV), exist_ok=True)


def log(rec):
    rec["ts_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(EV, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    print("  LOG", json.dumps({k: v for k, v in rec.items() if k != "resp"}, default=str)[:220])


b = BB.BinanceBroker(mode="TESTNET")
base = getattr(b, "base", None) or getattr(b, "BASE", None) or getattr(b, "_base", None)
assert base and "testnet" in str(base), f"not testnet: {base}"
dual = b._request("GET", "/fapi/v1/positionSide/dual", signed=True)
assert dual.get("dualSidePosition") is False, f"not One-way mode: {dual}"
b.armed = True                      # readback-verified above; submit() requires it


def snapshot(tag):
    c, n = b.positions(), b.positions_notional()
    s = {"tag": tag, "contracts": c, "notional": n,
         "sigma_abs_notional": round(sum(abs(v) for v in n.values()), 2),
         "net_notional": round(sum(n.values()), 2), "n_nonzero": len(n)}
    log({"event": "readback", **s})
    print(f"  READBACK[{tag}] n={s['n_nonzero']} SIGMA|notional|={s['sigma_abs_notional']} "
          f"net={s['net_notional']} {json.dumps(n)}")
    return s


print(f"evidence -> {EV}")
print("\n=== BEFORE ===")
before = snapshot("before")
log({"event": "context", "base": str(base), "dual": dual, "cap": CAP,
     "cap_source": "MARKET_LOT_SIZE.maxQty from /fapi/v1/exchangeInfo",
     "ordered_by": "team-lead 2026-07-26 urgent single-item order"})

n_orders = 0
for sym in TARGETS:
    for rnd in range(6):
        amt = b.positions().get(sym, 0.0)
        if abs(amt) < MIN_QTY:
            print(f"  {sym}: flat (positionAmt={amt})")
            break
        assert amt < 0, f"{sym} is not SHORT (amt={amt}); this script only buys to reduce"
        q = abs(amt)
        n_chunks = max(1, math.ceil(q / CAP))
        chunk = math.floor(q / n_chunks / STEP) * STEP
        if chunk < MIN_QTY:
            chunk = q
        px = float(b._request("GET", "/fapi/v1/ticker/bookTicker",
                              {"symbol": sym})["askPrice"])
        print(f"\n  {sym} round {rnd}: remaining={q:,.0f} -> {n_chunks} chunk(s) of {chunk:,.0f} "
              f"(ask={px}, chunk notional ~{chunk*px:.2f} USDT)")
        for i in range(n_chunks):
            amt_now = b.positions().get(sym, 0.0)
            rem = abs(amt_now)
            if rem < MIN_QTY:
                break
            qty = min(chunk, math.floor(rem / STEP) * STEP)
            assert MIN_QTY <= qty <= CAP, f"chunk {qty} outside [{MIN_QTY}, {CAP}]"
            assert qty * px <= MAX_CHUNK_NOTIONAL, f"chunk notional {qty*px:.2f} too large"
            assert n_orders < MAX_ORDERS, "order cap reached — abort"
            order = {"symbol": sym, "side": "buy", "quantity": int(qty), "reduce_only": True}
            log({"event": "submit_attempt", "order": order, "remaining_before": rem,
                 "ask": px, "est_notional": round(qty * px, 2)})
            try:
                b.submit(order, "manual chunked exit of ladder-stuck position (lead order)")
                n_orders += 1
                det = b.last_fill_details()
                log({"event": "submit_ok", "order": order, "fill": det,
                     "resp": b.actions[-1].get("resp")})
            except Exception as e:
                log({"event": "submit_failed", "order": order,
                     "err": f"{type(e).__name__}: {e}"})
                print(f"    !! {type(e).__name__}: {e}")
                raise SystemExit("ABORT: submission failed — see evidence log")
            amt_after = b.positions().get(sym, 0.0)
            rem_after = abs(amt_after)
            log({"event": "post_order_readback", "symbol": sym,
                 "remaining_before": rem, "remaining_after": rem_after})
            print(f"    order {n_orders}: qty={int(qty):,} -> remaining {rem:,.0f} => {rem_after:,.0f}")
            if rem_after >= rem:
                log({"event": "ABORT", "why": "position did not shrink",
                     "symbol": sym, "before": rem, "after": rem_after})
                raise SystemExit("ABORT: position did not shrink after a reduce-only order")

print("\n=== AFTER ===")
after = snapshot("after")
log({"event": "summary", "n_orders_sent": n_orders,
     "sigma_before": before["sigma_abs_notional"], "sigma_after": after["sigma_abs_notional"]})
print(f"\norders sent: {n_orders}")
print(f"SIGMA|notional|  before={before['sigma_abs_notional']}  after={after['sigma_abs_notional']}")
print(f"evidence: {EV}")
