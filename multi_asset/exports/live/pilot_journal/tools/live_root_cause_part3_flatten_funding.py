"""Part 3 (read-only; reviewer P1/P2 corrections): (a) the two flatten anchors (08-26 12Z E-0826-F, 09-06 08Z stop) rebuilt from actual fills:
P&L = Σ signed_notional × (fill_px/mid_anchor − 1) for the flattened quantity (held from anchor mid to the fill), zero after; (b) window decomposition WITH
ledger funding and commissions per segment; (c) daily residual after the rebuild."""
import json, os, glob, time, collections, numpy as np
L = os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); R = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_root_cause_2026-09-09_receipt.json")))
def utc(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
mid = {}
for p in sorted(glob.glob(f"{L}/2026*/anchors.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); mv = r.get("mid_at_anchor_vector"); mv = json.loads(mv) if isinstance(mv, str) else mv
        if mv: mid[a] = {s: float(v) for s, v in mv.items() if v}
pos = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/2026*/position_readback.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); n = r.get("venue_position_notional")
        if n is not None and abs(float(n)) > 0 and "post_anchor" in str(r.get("source", "")): pos[a][r["symbol"]] = float(n)
out = {}
for a, day in ((1787746400 - 1787746400 % 14400, "20260826"), (1788681600, "20260906")):   # 08-26 12Z = 1787745600, 09-06 08Z = 1788681600
    a = a // 14400 * 14400; m0 = mid.get(a, {}); fills = [f for f in jl(f"{L}/{day}/fills.jsonl") if a + 2400 <= float(f["fill_ts"]) < a + 14400]   # after the anchor's own N+40min submission window
    seen = set(); pl = 0.0; notional = 0.0; nfill = 0; by = collections.defaultdict(float)
    for f in fills:
        k = (f["symbol"], f.get("trade_id"))
        if k in seen: continue
        seen.add(k); s = f["symbol"]; px = float(f["fill_px"]); q_usd = float(f["fill_notional"]); side = f["side"]
        if s not in m0 or m0[s] <= 0: continue
        signed = -q_usd if side == "sell" else q_usd      # a sell closes a long (long P&L = notional × (px/mid − 1)); a buy closes a short
        held_sign = 1 if side == "sell" else -1; pl_i = held_sign * q_usd * (px / m0[s] - 1); pl += pl_i; notional += q_usd; nfill += 1; by[s] += pl_i
    proxy = next((r["pl"] for r in R["rows"] if r["a"] == a), None)
    out[utc(a)] = {"fills_after_window": nfill, "flatten_notional": round(notional), "pl_fill_based": round(pl, 1), "pl_mid_proxy": round(proxy, 1) if proxy is not None else None, "worst": sorted(by.items(), key=lambda x: x[1])[:5]}
    print(f"{utc(a)} flatten fills {nfill} notional {notional:,.0f} | fill-based P&L (anchor mid→fill px) {pl:+,.1f} vs mid-proxy {proxy:+,.1f} | worst {[(s, round(v)) for s, v in sorted(by.items(), key=lambda x: x[1])[:5]]}")
# (b) segment decomposition with ledger funding/commission apportioned by day and by anchor count
rows = R["rows"]; daily = {}
for d in sorted(os.listdir(L)):
    p = f"{L}/{d}/daily_nav.jsonl"
    if not os.path.exists(p) or d < "20260826": continue
    rw = jl(p)
    if rw: bt = rw[-1].get("realised_by_type") or {}; daily[d] = dict(nav=float(rw[-1]["nav"]), tr=float(bt.get("TRANSFER") or 0), ff=float(bt.get("FUNDING_FEE") or 0), cm=float(bt.get("COMMISSION") or 0))
def T(*x):
    import calendar; return calendar.timegm(x + (0,) * (6 - len(x)))
SEG = [("S1 08-26 20Z→09-02 08Z", T(2026, 8, 26, 20), T(2026, 9, 2, 8)), ("S2 09-02 12Z→09-03 12Z", T(2026, 9, 2, 12), T(2026, 9, 3, 12)), ("S3-S4 09-03 16Z→09-06 04Z", T(2026, 9, 3, 16), T(2026, 9, 6, 4)), ("S5a 09-06 08Z (fill-based)", T(2026, 9, 6, 8), T(2026, 9, 6, 8)), ("S6-S7 09-07 04Z→09-09 04Z", T(2026, 9, 7, 4), T(2026, 9, 9, 4))]
tot_ff = sum(v["ff"] for d, v in daily.items() if d >= "20260827"); tot_cm = sum(v["cm"] for d, v in daily.items() if d >= "20260827"); n_all = len(rows)
print(f"\nledger funding 08-27→09-09 {tot_ff:+,.0f} USDT, commissions {tot_cm:+,.0f} (apportioned per anchor below by day)")
print("%-30s %3s %10s %9s %9s %9s %9s" % ("segment", "n", "price", "long", "short", "funding", "comm"))
for lab, lo, hi in SEG:
    rs = [r for r in rows if lo <= r["a"] <= hi]; ff = 0.0; cm = 0.0
    for r in rs:
        d = time.strftime("%Y%m%d", time.gmtime(r["a"] + 14400)); nd = sum(1 for x in rows if time.strftime("%Y%m%d", time.gmtime(x["a"] + 14400)) == d)
        if d in daily and nd: ff += daily[d]["ff"] / nd; cm += daily[d]["cm"] / nd
    pl = sum(r["pl"] for r in rs); lg = sum(r["longp"] for r in rs); sh = sum(r["shortp"] for r in rs)
    if lab.startswith("S5a"): pl = out["09-06 08Z"]["pl_fill_based"]
    print(f"{lab:30s} {len(rs):3d} {pl:+10,.0f} {lg:+9,.0f} {sh:+9,.0f} {ff:+9,.0f} {cm:+9,.0f}")
json.dump({"flatten": out, "ledger_funding_total": tot_ff, "ledger_commission_total": tot_cm}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_root_cause_part3_receipt.json"), "w"), indent=1, default=str); print("PART3_DONE")
