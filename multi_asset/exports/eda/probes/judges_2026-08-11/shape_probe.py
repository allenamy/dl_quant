#!/usr/bin/python3
"""READ-ONLY probe: does a SHAPE criterion separate the doubling from healthy anchors?

Touches no guard, writes nothing into the repo. Reads state/testnet/pilot_log only.

Criterion under test, per anchor, over names whose INTENT is materially non-zero:
    n_double = #{ ratio = actual/intent  in [LO, HI] }        (signed: wrong-side names cannot count)
    n_zero   = #{ |actual| < DUST }                            (intended, and not held at all)
Reported alongside the magnitude reading the lead/0C already have, so the two can be compared on
the same rows.
"""
import collections, glob, json, os, sys, time

D = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
LO, HI = 1.7, 2.3
INTENT_FLOOR = 25.0        # "materially non-zero": ~1/10 of a typical name (~230 USDT)
DUST = 5.0                 # the venue's default MIN_NOTIONAL — below it a name is "not held"

EVENTS = {                 # what each anchor is, established elsewhere (0C + trip_causes.py)
    1785024063: "★ REAL: top-up doubling",
    1785110467: "★ REAL: fill-record collapse (venue holds 21,424, ledger records nothing)",
}


def anchors():
    for day in sorted(os.listdir(D)):
        p = os.path.join(D, day)
        if not os.path.isdir(p) or not os.path.exists(p + "/anchors.jsonl"):
            continue
        orders = [json.loads(l) for l in open(p + "/orders.jsonl")]
        anch = {float(a["anchor_ts"]): a for a in
                (json.loads(l) for l in open(p + "/anchors.jsonl"))}
        rb = collections.defaultdict(dict)
        if os.path.exists(p + "/position_readback.jsonl"):
            for l in open(p + "/position_readback.jsonl"):
                r = json.loads(l)
                rb[float(r["anchor_ts"])][r["symbol"]] = float(r["venue_position_notional"])
        for ats in sorted(anch):
            g = float(anch[ats]["target_gross"])
            o_a = [o for o in orders if abs(float(o["anchor_ts"]) - ats) < 0.6]
            tgt = {o["symbol"]: float(o["target_w"]) * g
                   for o in o_a if o.get("target_w") is not None}
            yield day, ats, g, tgt, dict(rb.get(ats, {})), \
                sum(1 for o in o_a if o.get("submit_ts") is not None)


print(f"criterion: ratio in [{LO},{HI}] over names with |intent| >= {INTENT_FLOOR} USDT; "
      f"'not held' = |actual| < {DUST}\n")
hdr = (f"{'anchor (UTC)':17s} {'nsub':>5s} {'n_sig':>5s} | {'n_dbl':>5s} {'%dbl':>5s} | "
       f"{'n_zero':>6s} {'%zero':>5s} | {'pct_gross':>9s} {'p50':>6s} {'max':>7s} | what")
print(hdr)
print("-" * len(hdr))
rows = []
for day, ats, g, tgt, rb, nsub in anchors():
    sig = {s: v for s, v in tgt.items() if abs(v) >= INTENT_FLOOR}
    n_dbl = n_zero = 0
    for s, v in sig.items():
        a = rb.get(s, 0.0)
        if abs(a) < DUST:
            n_zero += 1
        r = a / v
        if LO <= r <= HI:
            n_dbl += 1
    devs = sorted(abs(rb.get(s, 0.0) - tgt.get(s, 0.0))
                  for s in set(tgt) | set(rb))
    pct = sum(devs) / g if g else 0.0
    lab = EVENTS.get(int(ats), "healthy" if nsub else "(halted: nothing submitted)")
    rows.append((ats, nsub, len(sig), n_dbl, n_zero, pct, lab))
    print(f"{time.strftime('%m-%d %H:%M:%SZ', time.gmtime(ats)):17s} {nsub:5d} {len(sig):5d} | "
          f"{n_dbl:5d} {n_dbl/max(len(sig),1):5.1%} | {n_zero:6d} {n_zero/max(len(sig),1):5.1%} | "
          f"{pct:8.1%} {devs[len(devs)//2]:6.1f} {devs[-1]:7.1f} | {lab}")

print("\n--- separation, over the anchors that actually TRADED (nsub > 0) ---")
traded = [r for r in rows if r[1] > 0]
brk = [r for r in traded if r[6].startswith("★")]
ok = [r for r in traded if not r[6].startswith("★")]
for nm, sel, idx in (("n_double", None, 3), ("n_zero", None, 4), ("pct_gross", None, 5)):
    b = [r[idx] for r in brk]
    h = [r[idx] for r in ok]
    fmt = (lambda x: f"{x:.1%}") if nm == "pct_gross" else (lambda x: f"{x:g}")
    print(f"  {nm:10s} broken={[fmt(x) for x in b]}   healthy(max)={fmt(max(h)) if h else '-'}  "
          f"healthy={[fmt(x) for x in h]}")

print("\n--- would a threshold K fire on the doubling and stay silent on every healthy anchor? ---")
for K in (3, 5, 8, 10, 15, 20, 30):
    fire_b = [time.strftime('%m-%d %H:%MZ', time.gmtime(r[0])) for r in brk if r[3] >= K]
    fire_h = [time.strftime('%m-%d %H:%MZ', time.gmtime(r[0])) for r in ok if r[3] >= K]
    print(f"  n_double >= {K:2d}: fires on broken {fire_b or '[]'}, false on healthy {fire_h or '[]'}")

print("\n--- the second half of the shape (intended but not held at all) ---")
for K in (5, 10, 20, 30, 40, 56):
    fire_b = [time.strftime('%m-%d %H:%MZ', time.gmtime(r[0])) for r in brk if r[4] >= K]
    fire_h = [time.strftime('%m-%d %H:%MZ', time.gmtime(r[0])) for r in ok if r[4] >= K]
    print(f"  n_zero   >= {K:2d}: fires on broken {fire_b or '[]'}, false on healthy {fire_h or '[]'}")

print("\n--- ratio histogram, the doubling vs the worst healthy anchor ---")
for want in (1785024063, 1785225684, 1785110467):
    for day, ats, g, tgt, rb, nsub in anchors():
        if int(ats) != want:
            continue
        sig = {s: v for s, v in tgt.items() if abs(v) >= INTENT_FLOOR}
        h = collections.Counter()
        for s, v in sig.items():
            r = rb.get(s, 0.0) / v
            b = ("<0 (wrong side)" if r < -0.05 else "~0 (not held)" if r < 0.05 else
                 "0.05-0.7" if r < 0.7 else "0.7-1.3 (on target)" if r < 1.3 else
                 "1.3-1.7" if r < 1.7 else "1.7-2.3 (DOUBLE)" if r <= 2.3 else ">2.3")
            h[b] += 1
        print(f"  {time.strftime('%m-%d %H:%M:%SZ', time.gmtime(ats))} nsub={nsub} "
              f"n_sig={len(sig)}: " + " | ".join(f"{k}={v}" for k, v in sorted(h.items())))

print("\n--- a DIFFERENT signature, for the record-collapse event the shape cannot see ---")
print("    'the venue holds a book while our ledger recorded no execution at all'")
for day, ats, g, tgt, rb, nsub in anchors():
    held = sum(abs(v) for v in rb.values())
    orders = [json.loads(l) for l in open(os.path.join(D, day, "orders.jsonl"))]
    o_a = [o for o in orders if abs(float(o["anchor_ts"]) - ats) < 0.6]
    filled = sum(abs(float(o["filled_notional"] or 0.0)) for o in o_a)
    if held > DUST:
        flag = "  <== ledger says NOTHING executed, venue says we hold a book" \
            if filled < 0.01 * held else ""
        print(f"  {time.strftime('%m-%d %H:%M:%SZ', time.gmtime(ats)):17s} nsub={nsub:3d} "
              f"venue_gross={held:9.1f}  ledger_|filled|={filled:9.1f}  "
              f"ratio={filled/held if held else 0:6.3f}{flag}")
