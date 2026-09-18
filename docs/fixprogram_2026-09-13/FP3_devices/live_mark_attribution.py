#!/usr/bin/env python3
"""Live book mark-to-market attribution (read-only, 2026-09-17): per anchor, P&L ≈ Σ qty_{t-1}(s) × (mid_t(s) − mid_{t-1}(s)) from the executor's
post-anchor position readback (venue truth) and the anchors row's mid_at_anchor_vector (JSON string). Splits by side, breadth (share of held names
whose mid rose), top-5 concentration, BTC move; day sums; per-name day totals; largest positions. Intra-anchor fills are ignored (fills are ~5% of
gross per anchor), so this is the holding-period price P&L, not the ledger. usage: live_mark_attribution.py <day_from> <day_to> <out.json>"""
import json, os, sys, time, collections, hashlib
L = os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); D0, D1, OUT = sys.argv[1:4]
days = sorted(d for d in os.listdir(L) if d.isdigit() and D0 <= d <= D1)
def rows(d, n):
    p = f"{L}/{d}/{n}.jsonl"; return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []
an = {}; rb = collections.defaultdict(dict); fr = collections.defaultdict(dict); ins = {}
for d in days:
    for n in ("anchors", "position_readback", "funding"):
        p = f"{L}/{d}/{n}.jsonl"
        if os.path.isfile(p): ins[f"{d}/{n}"] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    for r in rows(d, "anchors"):
        A = int(float(r["anchor_ts"]) // 14400 * 14400); mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str) and mv.startswith("{"): an[A] = json.loads(mv)
    for r in rows(d, "position_readback"):
        A = int(float(r["anchor_ts"]) // 14400 * 14400); rb[A][r["symbol"]] = (float(r["venue_position_qty"]), float(r["venue_position_notional"]))
    for r in rows(d, "funding"): fr[int(float(r["settlement_ts"]))][r["symbol"]] = (float(r.get("funding_rate") or 0), int(r.get("funding_interval_h") or 8))
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))
As = sorted(set(an) & set(rb)); per_anchor = []; name_day = collections.defaultdict(float); day = collections.defaultdict(lambda: {"total": 0.0, "long": 0.0, "short": 0.0, "n_anchors": 0})
for i in range(1, len(As)):
    a0, a1 = As[i - 1], As[i]
    if a1 - a0 != 14400: continue
    m0, m1, q = an[a0], an[a1], rb[a0]; pn = {}; up_s = dn_s = up_l = dn_l = 0
    for s, (qty, notl) in q.items():
        if s in m0 and s in m1 and m0[s] and m1[s] and qty:
            ret = float(m1[s]) / float(m0[s]) - 1; pn[s] = qty * (float(m1[s]) - float(m0[s]))
            if qty < 0: up_s += ret > 0; dn_s += ret <= 0
            else: up_l += ret > 0; dn_l += ret <= 0
    tot = sum(pn.values()); lo = sum(v for s, v in pn.items() if q[s][0] > 0); sh = tot - lo; ab = sum(abs(v) for v in pn.values())
    top5 = sorted(pn.items(), key=lambda x: -abs(x[1]))[:5]
    btc = (float(m1["BTCUSDT"]) / float(m0["BTCUSDT"]) - 1) * 100 if m0.get("BTCUSDT") and m1.get("BTCUSDT") else None
    rec = {"from": U(a0), "to": U(a1), "pnl": round(tot), "long": round(lo), "short": round(sh), "btc_pct": None if btc is None else round(btc, 2), "shorts_up_share": round(up_s / max(1, up_s + dn_s), 2), "longs_up_share": round(up_l / max(1, up_l + dn_l), 2), "n_held": len(pn), "top5_share_abs": round(sum(abs(v) for _, v in top5) / ab, 2) if ab else None,
           "top5": [(s, round(v), round(q[s][1]), round((float(m1[s]) / float(m0[s]) - 1) * 100, 1)) for s, v in top5]}
    per_anchor.append(rec); d = time.strftime("%m-%d", time.gmtime(a1)); day[d]["total"] += tot; day[d]["long"] += lo; day[d]["short"] += sh; day[d]["n_anchors"] += 1
    for s, v in pn.items(): name_day[(d, s)] += v
by_name = {}
for d in sorted({k[0] for k in name_day}):
    nd = sorted(((s, v) for (dd, s), v in name_day.items() if dd == d), key=lambda x: x[1]); by_name[d] = {"worst": [(s, round(v)) for s, v in nd[:8]], "best": [(s, round(v)) for s, v in nd[-8:][::-1]]}
Alast = As[-1]; q = rb[Alast]; nav_guess = sum(abs(n) for _, n in q.values()) / 2.0
conc = {"anchor": U(Alast), "positions": len(q), "gross_usdt": round(sum(abs(n) for _, n in q.values())), "n_over_1p5pct_of_half_gross": sum(1 for _, n in q.values() if abs(n) > 0.015 * nav_guess), "max_abs_pct_of_half_gross": round(max(abs(n) for _, n in q.values()) / nav_guess * 100, 2)}
out = {"device": "live_mark_attribution.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "days": days, "inputs_sha16": ins, "per_anchor": per_anchor, "by_day": {d: {k: (round(v) if isinstance(v, float) else v) for k, v in x.items()} for d, x in day.items()}, "by_name_day": by_name, "concentration_last_anchor": conc}
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
for r in per_anchor[-12:]: print(f"{r['from']}→{r['to'][-3:]}: {r['pnl']:+6} (L {r['long']:+6} / S {r['short']:+6}) BTC {r['btc_pct']:+.2f}% | shorts up {r['shorts_up_share']:.0%} longs up {r['longs_up_share']:.0%} | top5 {r['top5_share_abs']:.0%} {r['top5'][:3]}")
print("by_day:", out["by_day"]); print("concentration:", conc)
