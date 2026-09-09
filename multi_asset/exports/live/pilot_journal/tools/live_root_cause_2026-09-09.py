#!/usr/bin/env python3
"""Read-only root-cause decomposition of the live book since 08-26 04Z (combo era): where did the money go, by period / side / funding bucket /
name recurrence / leg, reconciled to the ledger. Positions = post-anchor venue readback; returns = next-anchor mid; funding = actual settlement rates.
No API calls. Usage: live_root_cause_2026-09-09.py [start_anchor_ts]"""
import json, glob, os, sys, time, collections
import numpy as np
L = os.path.expanduser("~/dl_quant_live/state/live"); W = os.path.expanduser("~/wide_shadow/state"); START = int(sys.argv[1]) if len(sys.argv) > 1 else 1787716800
def utc(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
# mids per anchor
mid = {}
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/anchors.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); mv = r.get("mid_at_anchor_vector"); mv = json.loads(mv) if isinstance(mv, str) else mv
        if mv: mid[a] = {s: float(v) for s, v in mv.items() if v}
# positions per anchor (post-anchor readback)
pos = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/position_readback.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); n = r.get("venue_position_notional")
        if n is not None and abs(float(n)) > 0: pos[a][r["symbol"]] = float(n)
# funding: latest settlement rate per symbol (8h-normalised bp) at each anchor
fr = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/funding.jsonl")):
    for r in jl(p):
        t = int(float(r["settlement_ts"])) // 14400 * 14400; h = float(r.get("funding_interval_h") or 8); fr[t][r["symbol"]] = float(r["funding_rate"]) * (8.0 / h) * 1e4
anchors = sorted(a for a in pos if a >= START and a + 14400 in mid and a in mid)
def rn8_at(a):
    ts = [t for t in fr if t <= a]; out = {}
    for t in sorted(ts)[-6:]:
        out.update(fr[t])
    return out
rows = []; name_pnl = collections.defaultdict(float); name_hits = collections.Counter(); bucket = collections.defaultdict(float); bucket_n = collections.Counter(); side_pnl = collections.defaultdict(float)
for a in anchors:
    m0, m1 = mid[a], mid[a + 14400]; rn = rn8_at(a); gross = sum(abs(v) for v in pos[a].values()); pl = 0.0; longp = shortp = 0.0; per = []
    for s, n in pos[a].items():
        if s in m0 and s in m1 and m0[s] > 0:
            r = m1[s] / m0[s] - 1; u = n * r; pl += u; per.append((s, u, n, r)); name_pnl[s] += u
            (longp if n > 0 else shortp)
            if n > 0: longp += u
            else: shortp += u
            f = rn.get(s); b = ("L" if n > 0 else "S") + "|" + ("na" if f is None else ("deepneg" if f <= -10 else "neg" if f < 0 else "pos_top" if f >= 10 else "pos_hi" if f >= 5 else "pos_lo"))
            bucket[b] += u; bucket_n[b] += 1
    per.sort(key=lambda x: x[1]); worst = per[:3]
    for s, u, n, r in per[:5]: name_hits[s] += 1
    rows.append(dict(a=a, gross=gross, pl=pl, longp=longp, shortp=shortp, bps=pl / gross * 1e4 if gross else 0.0, worst=[(s, round(u), "L" if n > 0 else "S", round(r * 100, 1)) for s, u, n, r in worst], n=len(per)))
def T(*x):
    import calendar; return calendar.timegm(x + (0,) * (6 - len(x)))
SEG = [("S1 08-26 20Z→09-02 08Z (pre-FTRIM, NAV≈20k)", T(2026, 8, 26, 20), T(2026, 9, 2, 8)), ("S2 09-02 12Z→09-03 12Z (+FTRIM)", T(2026, 9, 2, 12), T(2026, 9, 3, 12)), ("S3 09-03 16Z→09-04 00Z (+deposit×4)", T(2026, 9, 3, 16), T(2026, 9, 4, 0)),
       ("S4 09-04 04Z→09-06 04Z (+M1)", T(2026, 9, 4, 4), T(2026, 9, 6, 4)), ("S5a 09-06 08Z stop anchor", T(2026, 9, 6, 8), T(2026, 9, 6, 8)), ("S6 09-07 04Z→09-08 08Z rebuilt", T(2026, 9, 7, 4), T(2026, 9, 8, 8)), ("S7 09-08 12Z→09-09 04Z (+deposit 35k)", T(2026, 9, 8, 12), T(2026, 9, 9, 4))]
print(f"== live positions × next mid, {utc(anchors[0])}→{utc(anchors[-1])}, n={len(anchors)} anchors (price P&L only; funding/commission from ledger below)")
tot = sum(r["pl"] for r in rows); print(f"TOTAL price P&L {tot:+,.0f} USDT | long {sum(r['longp'] for r in rows):+,.0f} | short {sum(r['shortp'] for r in rows):+,.0f}")
print("%-44s %3s %10s %9s %9s %8s" % ("segment", "n", "P&L USDT", "long", "short", "bps/anch"))
for lab, lo, hi in SEG:
    rs = [r for r in rows if lo <= r["a"] <= hi]
    if rs: print(f"{lab:44s} {len(rs):3d} {sum(r['pl'] for r in rs):+10,.0f} {sum(r['longp'] for r in rs):+9,.0f} {sum(r['shortp'] for r in rs):+9,.0f} {np.mean([r['bps'] for r in rs]):+8.2f}")
post = [r for r in rows if r["a"] >= T(2026, 9, 3, 16)]
print(f"\n== post-deposit (09-03 16Z→): P&L {sum(r['pl'] for r in post):+,.0f} USDT over {len(post)} anchors; anchors with P&L < −1000: {[(utc(r['a']), round(r['pl'])) for r in post if r['pl'] < -1000]}")
print("\n== by side × funding bucket (rn8 bp at anchor; whole window, USDT and share of gross-loss):")
neg_total = sum(v for v in bucket.values() if v < 0)
for b, v in sorted(bucket.items(), key=lambda x: x[1]): print(f"  {b:14s} {v:+9,.0f}  n={bucket_n[b]:5d}  " + (f"{v/neg_total*100:5.1f}% of losses" if v < 0 else ""))
print("\n== name recurrence: names in the worst-5 of ≥3 anchors (cumulative USDT over window):")
for s, k in name_hits.most_common(25):
    if k >= 3: print(f"  {s:14s} worst5 hits {k:2d}  cum {name_pnl[s]:+8,.0f}")
print(f"\n== concentration: top-15 losing names = {sum(sorted(name_pnl.values())[:15]):+,.0f} USDT ({sum(sorted(name_pnl.values())[:15]) / neg_total * 100:.0f}% of gross losses); top-15 winners {sum(sorted(name_pnl.values())[-15:]):+,.0f}")
print("  worst 15:", [(s, round(v)) for s, v in sorted(name_pnl.items(), key=lambda x: x[1])[:15]])
# ledger reconciliation per day
print("\n== ledger (daily_nav last row per day): ΔNAV net of TRANSFER vs positions×mid same UTC day")
prev = None
for d in sorted(os.listdir(f"{L}/pilot_log")):
    p = f"{L}/pilot_log/{d}/daily_nav.jsonl"
    if not os.path.exists(p) or d < "20260826": continue
    rws = jl(p)
    if not rws: continue
    nav = float(rws[-1]["nav"]); bt = rws[-1].get("realised_by_type") or {}; tr = float(bt.get("TRANSFER") or 0); ff = float(bt.get("FUNDING_FEE") or 0); cm = float(bt.get("COMMISSION") or 0)
    day0 = int(time.mktime(time.strptime(d, "%Y%m%d"))) - time.timezone; pm = sum(r["pl"] for r in rows if day0 <= r["a"] < day0 + 86400)
    if prev is not None: print(f"  {d} ΔNAV净 {nav - prev - tr:+8,.0f} | funding {ff:+7,.0f} comm {cm:+6,.0f} | pos×mid {pm:+8,.0f}")
    prev = nav
# leg returns: producer's own leg return history (seeded OOS rows + live rows)
lr = json.load(open(f"{W}/leg_returns_live.json")); n = len(lr["fund"])
print(f"\n== producer leg returns (bps/anchor per leg gross; file rows {n}: first 917 = v3 OOS seed ≤ 08-30 20Z, rest = live since 08-31)")
for leg in ("king", "fund", "rev24"):
    v = np.array(lr[leg]); seed = v[:917]; live = v[917:]
    print("  %-5s seed(917) mean %+6.2f sd %5.1f | last-450 seed mean %+6.2f | live(%d) mean %+6.2f sd %5.1f | live sum %+7.0f" % (leg, seed.mean(), seed.std(), seed[-450:].mean(), len(live), live.mean(), live.std(), live.sum()))
# regime dash fund IC
rd = jl(os.path.expanduser("~/regime_dash/regime_dash.jsonl")); icf = [r["ic_fund_realized"] for r in rd if r.get("ic_fund_realized") is not None]; ict = [r["ic_transient_realized"] for r in rd if r.get("ic_transient_realized") is not None]
print(f"\n== regime dash 09-02→09-09: fund-leg realised IC mean {np.mean(icf):+.4f} (n={len(icf)}, share<0 {np.mean(np.array(icf)<0):.2f}); transient IC mean {np.mean(ict):+.4f}; σ_fund mean {np.mean([r['sig_fund_bp'] for r in rd]):.1f} bp; pos_share mean {np.mean([r['pos_share'] for r in rd]):.3f}; deepneg mean {np.mean([r['deepneg_share'] for r in rd]):.3f}")
json.dump({"rows": [{k: (v if k != 'worst' else v) for k, v in r.items()} for r in rows], "bucket": bucket, "bucket_n": bucket_n, "name_pnl": name_pnl, "name_hits": name_hits}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_root_cause_2026-09-09_receipt.json"), "w"), indent=0, default=float)
print("ROOT_CAUSE_DONE")
