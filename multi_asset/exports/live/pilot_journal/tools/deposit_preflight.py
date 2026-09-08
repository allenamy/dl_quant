"""READ-ONLY deposit preflight (2026-09-08 +35,000 USDT). Places no orders, writes nothing to live state.
Only broker read methods: account_snapshot / income_since / exchange filters. Mirrors the 09-03 checklist."""
import os, sys, json, time, calendar
REPO=os.path.expanduser("~/dl_quant_live")
for d in ("live","ops"): sys.path.insert(0, os.path.join(REPO,d))
import envfile; envfile.load()
os.environ.setdefault("LIVE_MODE","LIVE")
from binance_broker import BinanceBroker
B=BinanceBroker(mode="LIVE")
snap=B.account_snapshot()
day0=int(calendar.timegm(time.strptime(time.strftime("%Y%m%d",time.gmtime()),"%Y%m%d")))*1000
inc=B.income_since(day0)
print("== ACCOUNT (read %s) =="%time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(snap["read_ts"])))
for k in ("total_wallet_balance","total_unrealized_profit","total_margin_balance","available_balance","equity"):
    print("  %-26s %15.2f"%(k,snap[k]))
pn=snap["positions_notional"]; gross=sum(abs(v) for v in pn.values()); net=sum(pn.values())
print("  %-26s %15d  gross %.2f  net %.2f (%.2f%% of gross)"%("open positions",len(pn),gross,net,100*net/max(gross,1e-9)))
print("== TODAY INCOME (since 00:00Z) ==")
print("  ",json.dumps(inc if not isinstance(inc,dict) else {k:(round(v,4) if isinstance(v,float) else v) for k,v in inc.items()},default=str)[:900])
