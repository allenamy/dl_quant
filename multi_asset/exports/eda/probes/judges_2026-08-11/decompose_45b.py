#!/usr/bin/env python3
"""0C: decompose every historical §4-5b residual into PRICE term vs QUANTITY term.

Independent re-implementation of reconcile()'s arithmetic (deliberately NOT importing it, so a
defect in it cannot hide inside my own check).  Adds, per anomaly:

    residual        = observed(T2) - [ readback(T1) + signed fills in (T1,T2] ]
    price_est       = N1*(M2/M1 - 1) + sum_i F_i*(M2 - p_i)/p_i
    qty_share       = 1 - price_est/residual

M1/M2 come from `mid_at_anchor_vector` of the two bracketing anchors (readbacks sit ~900 s after
each anchor, so BOTH ends carry the same lag; the interval return survives it).  p_i = avg_fill_px.

Mark-free corroborator, reported alongside: |residual| / max(|N1|,|F|).  A missing flatten or a
double-count is ~1.0 of a whole position; a price artefact is a few percent.
"""
import json
import os
import sys
import datetime
from collections import defaultdict

ROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
DAYS = ["20260725", "20260726", "20260727", "20260728"]
TOL = 0.10
DUST = 5.0


def rd(day, name):
    p = os.path.join(ROOT, day, name + ".jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for ln in open(p):
        ln = ln.strip()
        if ln:
            out.append(json.loads(ln))
    return out


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%m-%dT%H:%M:%SZ")


# ── executions, by their own time (reconcile's interval rule) ──────────────────────────────────
execs = []           # (t, sym, signed_notional, avg_px)
for d in DAYS:
    for o in rd(d, "orders"):
        f = o.get("filled_notional")
        if f is None or not float(f):
            continue
        t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
        if t is None:
            continue
        execs.append((float(t), o["symbol"], float(f), o.get("avg_fill_px")))
execs.sort()

# ── mids at each anchor ────────────────────────────────────────────────────────────────────────
mid = {}             # anchor_ts -> {sym: mid}
for d in DAYS:
    for a in rd(d, "anchors"):
        v = a.get("mid_at_anchor_vector")
        if isinstance(v, str):
            v = json.loads(v)
        if v:
            mid[float(a["anchor_ts"])] = v


def mid_for(ats, sym):
    """mid of `sym` at the anchor whose ts is nearest at-or-before `ats`."""
    cands = [t for t in mid if t <= ats + 1e-6 and sym in mid[t]]
    if not cands:
        return None
    return float(mid[max(cands)][sym])


# ── walk readbacks exactly as reconcile does ───────────────────────────────────────────────────
prev_rb = prev_t = prev_ats = None
rows = []
for d in DAYS:
    by_anchor = defaultdict(dict)
    rb_time = {}
    for r in rd(d, "position_readback"):
        by_anchor[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
    for ats in sorted(by_anchor):
        cur = by_anchor[ats]
        t_cur = rb_time.get(ats, ats)
        if prev_rb is not None:
            win = defaultdict(list)
            for t, sym, f, px in execs:
                if (prev_t is None or t > prev_t) and t <= t_cur:
                    win[sym].append((f, px))
            for sym, v in cur.items():
                n1 = prev_rb.get(sym, 0.0)
                fills = win.get(sym, [])
                F = sum(f for f, _ in fills)
                expected = n1 + F
                resid = v - expected
                scale = max(abs(expected), abs(v), 1.0)
                if abs(resid) <= max(TOL * scale, DUST):
                    continue
                m1 = mid_for(prev_ats, sym)
                m2 = mid_for(ats, sym)
                price_est = None
                if m1 and m2:
                    price_est = n1 * (m2 / m1 - 1.0)
                    for f, px in fills:
                        if px:
                            price_est += f * (m2 - float(px)) / float(px)
                rows.append({
                    "T2_anchor": ats, "sym": sym, "N1": n1, "F": F, "N2": v,
                    "resid": resid, "frac": abs(resid) / scale, "price_est": price_est,
                    "scale_ref": max(abs(n1), abs(F)),
                })
        prev_rb, prev_t, prev_ats = cur, t_cur, ats

# ── report, grouped by anchor ─────────────────────────────────────────────────────────────────
by_anchor = defaultdict(list)
for r in rows:
    by_anchor[r["T2_anchor"]].append(r)

print(f"# decomposition run {datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
print(f"# {len(rows)} anomalies over {len(by_anchor)} anchors "
      f"(tol={TOL}, dust={DUST} global — the caliber the historical trips ran under)\n")
hdr = ("anchor(T2)      n   Σ|resid|      Σ|N1|   price-expl%   med |resid|/max(|N1|,|F|)   "
       "n_qtylike(>0.5)")
print(hdr)
print("-" * len(hdr))
for ats in sorted(by_anchor):
    rs = by_anchor[ats]
    sr = sum(abs(r["resid"]) for r in rs)
    sn = sum(abs(r["N1"]) for r in rs)
    have = [r for r in rs if r["price_est"] is not None]
    expl = (sum(abs(r["price_est"]) for r in have) / sr * 100) if sr and have else float("nan")
    ratios = sorted(abs(r["resid"]) / r["scale_ref"] if r["scale_ref"] else float("inf")
                    for r in rs)
    med = ratios[len(ratios) // 2] if ratios else float("nan")
    nq = sum(1 for x in ratios if x > 0.5)
    print(f"{utc(ats)}  {len(rs):3d}  {sr:9.2f}  {sn:9.2f}      {expl:6.1f}%"
          f"              {med:6.3f}            {nq:3d}")

if len(sys.argv) > 1 and sys.argv[1] == "--detail":
    want = float(sys.argv[2])
    print(f"\n# detail for anchor {utc(want)}")
    for r in sorted(by_anchor[want], key=lambda r: -abs(r["resid"]))[:200]:
        pe = "n/a" if r["price_est"] is None else f"{r['price_est']:9.2f}"
        print(f"  {r['sym']:16s} N1={r['N1']:10.2f} F={r['F']:10.2f} N2={r['N2']:10.2f} "
              f"resid={r['resid']:9.2f} price_est={pe} frac={r['frac']:.4f}")
