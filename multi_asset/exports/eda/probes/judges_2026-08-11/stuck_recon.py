"""STEP A — READ-ONLY. Confirm the two stuck positions at the venue and read the maxQty filters
the current SymbolFilters never loads. No order endpoint is touched."""
import os, sys, json, math

assert "BINANCE_LIVE_CONFIRM" not in os.environ, "LIVE_CONFIRM present — abort"
assert not os.environ.get("BINANCE_KEY"), "prod key present — abort"

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
import binance_broker as BB

b = BB.BinanceBroker(mode="TESTNET")
base = getattr(b, "base", None) or getattr(b, "BASE", None) or getattr(b, "_base", None)
print("base url        :", base)
assert base and "testnet" in str(base), f"not testnet: {base}"

dual = b._request("GET", "/fapi/v1/positionSide/dual", signed=True)
print("dualSidePosition:", dual, " (must be False for reduceOnly to be sendable)")

print("\n=== POSITIONS (venue, direct read) ===")
contracts = b.positions()
notional = b.positions_notional()
syms = sorted(set(contracts) | set(notional))
for s in syms:
    print(f"  {s:16s} positionAmt={contracts.get(s)!s:>16s}  notional={notional.get(s)!s:>16s}")
print(f"  n_nonzero = {len(syms)}   SIGMA|notional| = {sum(abs(v) for v in notional.values()):.2f}"
      f"   net = {sum(notional.values()):.2f}")

TARGETS = ["MEMEUSDT", "1000BONKUSDT"]
print("\n=== FILTERS (from /fapi/v1/exchangeInfo) — full, incl. the maxQty nobody loads ===")
info = b._request("GET", "/fapi/v1/exchangeInfo")
for s in info.get("symbols", []):
    if s["symbol"] not in TARGETS:
        continue
    print(f"  -- {s['symbol']}  status={s.get('status')}  contractType={s.get('contractType')}")
    for flt in s.get("filters", []):
        if flt["filterType"] in ("LOT_SIZE", "MARKET_LOT_SIZE", "MIN_NOTIONAL", "PRICE_FILTER"):
            print("     ", json.dumps(flt))

print("\n=== WHAT THE LADDER TRIED vs WHAT THE FILTER ALLOWS ===")
lot = {}
for s in info.get("symbols", []):
    if s["symbol"] in TARGETS:
        d = {}
        for flt in s.get("filters", []):
            if flt["filterType"] == "LOT_SIZE":
                d["lot_max"] = float(flt["maxQty"]); d["step"] = float(flt["stepSize"])
                d["min_qty"] = float(flt["minQty"])
            elif flt["filterType"] == "MARKET_LOT_SIZE":
                d["mkt_max"] = float(flt["maxQty"]); d["mkt_step"] = float(flt["stepSize"])
                d["mkt_min"] = float(flt["minQty"])
            elif flt["filterType"] == "MIN_NOTIONAL":
                d["min_notional"] = float(flt.get("notional", 5.0))
        lot[s["symbol"]] = d
for s in TARGETS:
    q = abs(contracts.get(s, 0.0))
    d = lot.get(s, {})
    cap = min([x for x in (d.get("lot_max"), d.get("mkt_max")) if x is not None] or [float("inf")])
    print(f"  {s:16s} need={q:>14,.0f}  LOT_SIZE.maxQty={d.get('lot_max')}  "
          f"MARKET_LOT_SIZE.maxQty={d.get('mkt_max')}  binding_cap={cap}  "
          f"=> min chunks = {math.ceil(q / cap) if cap and cap != float('inf') else 'n/a'}")
print("\nfilters dict:", json.dumps(lot, indent=1))

bt = b._request("GET", "/fapi/v1/ticker/bookTicker", {"symbol": "MEMEUSDT"})
print("\nMEMEUSDT bookTicker:", json.dumps(bt))
bt2 = b._request("GET", "/fapi/v1/ticker/bookTicker", {"symbol": "1000BONKUSDT"})
print("1000BONKUSDT bookTicker:", json.dumps(bt2))
