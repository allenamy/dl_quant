"""READ-ONLY: current venue positions + equity. No order endpoint is touched."""
import os, sys, json
assert "BINANCE_LIVE_CONFIRM" not in os.environ, "live confirm present - abort"
assert not os.environ.get("BINANCE_KEY"), "prod key present - abort"
REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
import binance_broker as BB
b = BB.BinanceBroker(mode="TESTNET") if hasattr(BB, "BinanceBroker") else None
pn = b.positions_notional()
nz = {k: v for k, v in pn.items() if abs(v) > 1e-9}
print("nonzero positions:", len(nz))
print(json.dumps(nz, indent=1, sort_keys=True))
print("gross = %.2f  net = %.2f" % (sum(abs(v) for v in nz.values()), sum(nz.values())))
snap = b.account_snapshot()
if snap:
    print("equity:", {k: snap.get(k) for k in ("totalWalletBalance", "totalMarginBalance",
                                               "totalUnrealizedProfit", "availableBalance")
                      if k in snap})
