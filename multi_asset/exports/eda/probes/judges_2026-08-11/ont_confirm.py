"""READ-ONLY: explicit confirmation that ONTUSDT is flat at the venue.
It is invisible to the guards (no readback row since 12:00Z), so the record cannot answer this."""
import os, sys, json
assert "BINANCE_LIVE_CONFIRM" not in os.environ and not os.environ.get("BINANCE_KEY")
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import binance_broker as BB
b = BB.BinanceBroker(mode="TESTNET")
acct = b._request("GET", "/fapi/v3/account", signed=True)
rows = [p for p in acct.get("positions", []) if p["symbol"] in ("ONTUSDT", "QTUMUSDT")]
print("targeted rows from /fapi/v3/account:")
for p in rows:
    print("  ", p["symbol"], "positionAmt=", p.get("positionAmt"), " notional=", p.get("notional"),
          " entryPrice=", p.get("entryPrice"), " unrealized=", p.get("unrealizedProfit"))
print("  (absent from the response entirely means never held):",
      [s for s in ("ONTUSDT", "QTUMUSDT") if s not in {p["symbol"] for p in rows}])
nz = {p["symbol"]: float(p["notional"]) for p in acct.get("positions", [])
      if abs(float(p.get("notional", 0) or 0)) > 0}
print("\nWHOLE BOOK nonzero:", len(nz), nz)
print("wallet:", acct.get("totalWalletBalance"), " unrealized:", acct.get("totalUnrealizedProfit"))
oo = b._request("GET", "/fapi/v1/openOrders", {}, signed=True)
print("open orders:", len(oo))
