"""Part 2 (read-only): (a) stop-day anchors 09-05 20Z→09-06 08Z detail (side, buckets, worst names); (b) side×bucket split per segment (FTRIM check);
(c) what is in S|pos_lo: name list ranked by cumulative loss with rn8 and sector hint (majors?); (d) market-beta of the short side: short P&L vs altEW/BTC per anchor."""
import json, os, time, collections, glob, numpy as np
L = os.path.expanduser("~/dl_quant_live/state/live"); R = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_root_cause_2026-09-09_receipt.json")))
def utc(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
mid = {}
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/anchors.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); mv = r.get("mid_at_anchor_vector"); mv = json.loads(mv) if isinstance(mv, str) else mv
        if mv: mid[a] = {s: float(v) for s, v in mv.items() if v}
pos = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/position_readback.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); n = r.get("venue_position_notional")
        if n is not None and abs(float(n)) > 0: pos[a][r["symbol"]] = float(n)
fr = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/funding.jsonl")):
    for r in jl(p):
        t = int(float(r["settlement_ts"])) // 14400 * 14400; h = float(r.get("funding_interval_h") or 8); fr[t][r["symbol"]] = float(r["funding_rate"]) * (8.0 / h) * 1e4
def rn8_at(a):
    out = {}
    for t in sorted(t for t in fr if t <= a)[-6:]: out.update(fr[t])
    return out
def T(*x):
    import calendar; return calendar.timegm(x + (0,) * (6 - len(x)))
anchors = sorted(a for a in pos if a >= 1787716800 and a + 14400 in mid and a in mid)
def bucket_of(n, f): return ("L" if n > 0 else "S") + "|" + ("na" if f is None else ("deepneg" if f <= -10 else "neg" if f < 0 else "pos_top" if f >= 10 else "pos_hi" if f >= 5 else "pos_lo"))
# (a) stop-day detail
print("== (a) 09-05 20Z → 09-06 08Z anchors: side split, buckets, worst names (USDT)")
for a in [x for x in anchors if T(2026, 9, 5, 20) <= x <= T(2026, 9, 6, 8)]:
    m0, m1 = mid[a], mid[a + 14400]; rn = rn8_at(a); per = []; bk = collections.defaultdict(float)
    for s, n in pos[a].items():
        if s in m0 and s in m1 and m0[s] > 0: r = m1[s] / m0[s] - 1; u = n * r; per.append((s, u, n, r, rn.get(s))); bk[bucket_of(n, rn.get(s))] += u
    per.sort(key=lambda x: x[1]); tot = sum(x[1] for x in per); lg = sum(x[1] for x in per if x[2] > 0); sh = tot - lg
    btc = (m1.get("BTCUSDT", 0) / m0.get("BTCUSDT", 1) - 1) * 100; alt = np.mean([m1[s] / m0[s] - 1 for s in m0 if s in m1 and m0[s] > 0]) * 100
    print(f"  {utc(a)} total {tot:+7,.0f} long {lg:+7,.0f} short {sh:+7,.0f} | BTC {btc:+.2f}% altEW {alt:+.2f}% | buckets {dict((k, round(v)) for k, v in sorted(bk.items(), key=lambda x: x[1]))}")
    print("     worst:", [(s, round(u), "L" if n > 0 else "S", f"{r*100:+.1f}%", f"rn8 {f:+.1f}" if f is not None else "rn8 ?") for s, u, n, r, f in per[:6]])
# (b) per-segment bucket split
SEG = [("S1 pre-FTRIM", T(2026, 8, 26, 20), T(2026, 9, 2, 8)), ("S2 +FTRIM", T(2026, 9, 2, 12), T(2026, 9, 3, 12)), ("S3-S4 09-03 16Z→09-06 04Z", T(2026, 9, 3, 16), T(2026, 9, 6, 4)), ("S5a stop", T(2026, 9, 6, 8), T(2026, 9, 6, 8)), ("S6-S7 09-07 04Z→09-09 04Z", T(2026, 9, 7, 4), T(2026, 9, 9, 4))]
print("\n== (b) side×bucket per segment (USDT)")
sposlo_names = collections.defaultdict(float); sposlo_n = collections.Counter(); short_pl = []; alt_r = []; btc_r = []
for lab, lo, hi in SEG:
    bk = collections.defaultdict(float)
    for a in [x for x in anchors if lo <= x <= hi]:
        m0, m1 = mid[a], mid[a + 14400]; rn = rn8_at(a)
        for s, n in pos[a].items():
            if s in m0 and s in m1 and m0[s] > 0:
                u = n * (m1[s] / m0[s] - 1); b = bucket_of(n, rn.get(s)); bk[b] += u
                if b == "S|pos_lo": sposlo_names[s] += u; sposlo_n[s] += 1
    print(f"  {lab:28s} " + " ".join(f"{k}:{v:+,.0f}" for k, v in sorted(bk.items(), key=lambda x: x[1])))
print("\n== (c) S|pos_lo: worst 20 names (cum USDT, anchors held)")
print("  ", [(s, round(v), sposlo_n[s]) for s, v in sorted(sposlo_names.items(), key=lambda x: x[1])[:20]])
majors = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LTCUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "TRXUSDT", "BCHUSDT", "XLMUSDT", "SUIUSDT", "TONUSDT"}
print("   majors in S|pos_lo:", {s: round(sposlo_names[s]) for s in majors if s in sposlo_names}, "| majors total", round(sum(sposlo_names[s] for s in majors if s in sposlo_names)))
# (d) short-side beta: regress short P&L (bps of short gross) on altEW return per anchor
for a in anchors:
    m0, m1 = mid[a], mid[a + 14400]; sg = sum(-n for n in pos[a].values() if n < 0); sp = sum(n * (m1[s] / m0[s] - 1) for s, n in pos[a].items() if n < 0 and s in m0 and s in m1 and m0[s] > 0)
    if sg > 0: short_pl.append(sp / sg * 1e4); alt_r.append(np.mean([m1[s] / m0[s] - 1 for s in m0 if s in m1 and m0[s] > 0]) * 1e4); btc_r.append((m1.get("BTCUSDT", 0) / m0.get("BTCUSDT", 1) - 1) * 1e4)
sp, ar, br = map(np.array, (short_pl, alt_r, btc_r)); b_alt = np.polyfit(ar, sp, 1)[0]; b_btc = np.polyfit(br, sp, 1)[0]
print(f"\n== (d) short side (bps of short gross) vs market per anchor: mean {sp.mean():+.1f} | beta vs altEW {b_alt:+.2f} (corr {np.corrcoef(ar, sp)[0,1]:+.2f}) | beta vs BTC {b_btc:+.2f} (corr {np.corrcoef(br, sp)[0,1]:+.2f}) | altEW mean {ar.mean():+.1f} bps/anchor, BTC mean {br.mean():+.1f}")
resid = sp - b_alt * ar; print(f"   short side after removing altEW beta: mean {resid.mean():+.1f} bps/anchor (n={len(sp)}) => {'beta explains the loss' if abs(resid.mean()) < abs(sp.mean())/2 else 'idiosyncratic short losses dominate'}")
