"""Reconstruct the position path from the VENUE's own trade record (userTrades),
independent of our position_readback log. Answers exactly one question:
at each real settlement instant, how many of our names had a non-zero position?"""
import json, time, sys
from collections import defaultdict
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get

now = int(time.time() * 1000)
syms = sorted({json.loads(l)["symbol"]
               for l in open("/Users/haosiyu/dl_quant_live/state/testnet/pilot_log/20260727/position_readback.jsonl")})
print(f"symbols: {len(syms)}")

trades = defaultdict(list)
start = now - 5 * 86400_000
err = 0
for i, s in enumerate(syms):
    time.sleep(0.35)
    r = get("/fapi/v1/userTrades", {"symbol": s, "startTime": start, "endTime": now, "limit": 1000}, signed=True)
    if isinstance(r, dict):
        err += 1
        if err < 3: print(f"  {s}: {r}")
        continue
    for x in r:
        q = float(x["qty"]) * (1 if x["side"] == "BUY" else -1)
        trades[s].append((int(x["time"]), q, float(x["price"])))
    if len(r) >= 1000:
        print(f"  !! {s} hit 1000-trade limit — path may be truncated")
n_tr = sum(len(v) for v in trades.values())
print(f"trades fetched: {n_tr} across {len(trades)} symbols (errors={err})")
allt = [t for v in trades.values() for t, _, _ in v]
if allt:
    print(f"first trade {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(min(allt)/1000))}  "
          f"last {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(max(allt)/1000))}")

# 8h settlements (every one of our names is 8h on testnet: 00:00 / 08:00 / 16:00 UTC)
setts = []
t = (min(allt) // (8 * 3600_000)) * (8 * 3600_000)
while t <= now:
    if t >= min(allt):
        setts.append(t)
    t += 8 * 3600_000

print("\nsettlement (8h, the ONLY interval our 110 names use on testnet) | names with |pos|>0 "
      "reconstructed from venue trades")
for st in setts:
    held = 0
    names = []
    for s, v in trades.items():
        pos = sum(q for tt, q, _ in v if tt <= st)
        if abs(pos) > 1e-12:
            held += 1
            names.append(s)
    print(f"  {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st/1000))}   held={held:4d}"
          + (f"   e.g. {names[:3]}" if names else "   <<< FLAT BOOK — no charge possible"))
print("\n★ 'crossed a settlement with a live book' is TRUE only for the rows above with held>0")
