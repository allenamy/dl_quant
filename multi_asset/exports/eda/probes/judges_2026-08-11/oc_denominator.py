"""How many symbol-settlements did this account ACTUALLY cross with a live position?
That number is the denominator of the 'zero FUNDING_FEE' observation."""
import json, glob, time, sys
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get

ROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
rows = []
for f in sorted(glob.glob(ROOT + "/*/position_readback.jsonl")):
    for line in open(f):
        rows.append(json.loads(line))

# batches: read_ts -> {sym: notional}
batches = {}
for r in rows:
    t = float(r.get("read_ts") or r.get("anchor_ts"))
    batches.setdefault(round(t, 3), {})[r["symbol"]] = float(r.get("venue_position_notional") or 0.0)
bt = sorted(batches)
print(f"readback batches: {len(bt)}  first={time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(bt[0]))} "
      f"last={time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(bt[-1]))}")

fi = get("/fapi/v1/fundingInfo")
iv = {x["symbol"]: int(float(x["fundingIntervalHours"])) for x in fi if float(x.get("fundingIntervalHours", 0)) > 0}
syms = sorted({r["symbol"] for r in rows})
n4 = sum(1 for s in syms if iv.get(s) == 4)
n8 = sum(1 for s in syms if iv.get(s) == 8)
nUnk = sum(1 for s in syms if s not in iv)
print(f"our {len(syms)} names on TESTNET fundingInfo: 4h={n4}  8h={n8}  absent(=>venue default 8h)={nUnk}")

# window: account's first income row .. now
T0 = 1784991690.0           # 2026-07-25T15:01:30Z, earliest income row in the account
T1 = time.time()
MAX_AGE = 4 * 3600

def positions_at(t_s):
    """same rule as production positions_at: newest readback STRICTLY before, not older than 4h"""
    before = [t for t in bt if t < t_s]
    if not before:
        return None, "no readback before"
    newest = max(before)
    if t_s - newest > MAX_AGE:
        return None, f"stale {(t_s-newest)/3600:.2f}h"
    return batches[newest], f"age {(t_s-newest)/3600:.2f}h"

opps = 0
per_settlement = []
t = int(T0 // 3600) * 3600
while t <= T1:
    tt = time.gmtime(t)
    if tt.tm_hour % 4 == 0 and tt.tm_min == 0:
        snap, why = positions_at(float(t))
        held4 = held8 = 0
        if snap:
            for s in syms:
                h = iv.get(s, 8)
                if abs(snap.get(s, 0.0)) < 1e-9:
                    continue
                if h == 4:
                    held4 += 1
                elif h == 8 and tt.tm_hour % 8 == 0:
                    held8 += 1
        n = held4 + held8
        opps += n
        per_settlement.append((time.strftime('%Y-%m-%dT%H:%MZ', tt), n, why))
    t += 3600

print("\nsettlement instant | our names charged if the venue billed | readback basis")
for s, n, why in per_settlement:
    print(f"  {s}   n={n:4d}   ({why})")
print(f"\n★ TOTAL symbol-settlements actually crossed with a live position = {opps}")
print(f"★ observed FUNDING_FEE rows                                       = 0")
