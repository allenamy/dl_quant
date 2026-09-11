#!/usr/bin/env python3
"""Realized live P&L per anchor from the executor ledgers. READ-ONLY."""
import json, glob, os, time
import numpy as np
PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"

anchors = []
for d in sorted(glob.glob(f"{PL}/2026*")):
    p = f"{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        try: r = json.loads(l)
        except Exception: continue
        mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except Exception: mv = {}
        anchors.append({"ts": float(r["anchor_ts"]), "mid": mv or {},
                        "realized_gross": r.get("realized_gross"), "target_gross": r.get("target_gross"),
                        "regime": r.get("regime_at_anchor"), "hash": r.get("target_vector_hash")})
anchors.sort(key=lambda x: x["ts"])
print("anchors rows:", len(anchors), "with mid:", sum(1 for a in anchors if a["mid"]))

pos = {}   # anchor_ts -> {sym: (qty, notional)}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p = f"{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        try: r = json.loads(l)
        except Exception: continue
        pos.setdefault(float(r["anchor_ts"]), {})[r["symbol"]] = (
            float(r.get("venue_position_qty") or 0.0), float(r.get("venue_position_notional") or 0.0))

fund = []
seen = set()
for d in sorted(glob.glob(f"{PL}/2026*")):
    p = f"{d}/funding.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        try: r = json.loads(l)
        except Exception: continue
        k = (r["symbol"], float(r["settlement_ts"]))
        if k in seen: continue
        seen.add(k)
        fund.append((float(r["settlement_ts"]), float(r.get("funding_paid") or 0.0),
                     float(r.get("funding_interval_h") or 0), float(r.get("funding_rate") or 0.0),
                     float(r.get("position_notional_at_settlement") or 0.0)))
fund.sort()
print("funding rows (deduped):", len(fund), "total paid:", round(sum(f[1] for f in fund), 2))
from collections import Counter
print("funding_interval_h histogram:", Counter(f[2] for f in fund))

comm = []
for d in sorted(glob.glob(f"{PL}/2026*")):
    p = f"{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        try: r = json.loads(l)
        except Exception: continue
        comm.append((float(r.get("anchor_ts") or 0), float(r.get("commission") or 0.0),
                     float(r.get("fill_notional") or 0.0), bool(r.get("venue_maker_flag"))))

rows = []
for i in range(len(anchors) - 1):
    a, b = anchors[i], anchors[i + 1]
    pa = pos.get(a["ts"])
    if not pa or not a["mid"] or not b["mid"]: continue
    pnl = 0.0; gross = 0.0; covered = 0.0; uncov = 0.0
    for s, (q, nt) in pa.items():
        if q == 0: continue
        gross += abs(nt)
        m0 = a["mid"].get(s); m1 = b["mid"].get(s)
        if m0 is None or m1 is None or not m0: uncov += abs(nt); continue
        covered += abs(nt)
        pnl += q * (m1 - m0)
    fw = sum(f[1] for f in fund if a["ts"] <= f[0] < b["ts"])
    cw = sum(c[1] for c in comm if a["ts"] <= c[0] < b["ts"])
    cn = sum(c[2] for c in comm if a["ts"] <= c[0] < b["ts"])
    A = int(a["ts"] // 14400 * 14400)
    rows.append({"exec_ts": a["ts"], "grid_anchor": A,
                 "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(a["ts"])),
                 "gross": gross, "covered_gross": covered, "uncovered_gross": uncov,
                 "price_pnl": pnl, "funding": fw, "commission": cw, "fill_notional": cn,
                 "dt_h": (b["ts"] - a["ts"]) / 3600.0,
                 "price_bps_of_gross": pnl / gross * 1e4 if gross else None,
                 "funding_bps_of_gross": fw / gross * 1e4 if gross else None,
                 "comm_bps_of_gross": cw / gross * 1e4 if gross else None})
json.dump(rows, open(f"{OUT}/live_anchor_table.json", "w"), indent=1)
print("\nper-anchor rows:", len(rows), rows[0]["utc"], "->", rows[-1]["utc"])

def s(tag, sub):
    if not sub: print(tag, "empty"); return
    for k in ("price_bps_of_gross", "funding_bps_of_gross", "comm_bps_of_gross"):
        v = [r[k] for r in sub if r[k] is not None]
        print(f"  {tag:12s} {k:22s} mean {np.mean(v):8.4f} sd {np.std(v,ddof=1):7.3f} sum {np.sum(v):9.2f} n {len(v)}")
    print(f"  {tag:12s} {'usd price_pnl sum':22s} {sum(r['price_pnl'] for r in sub):9.1f}   funding {sum(r['funding'] for r in sub):8.1f}  comm {sum(r['commission'] for r in sub):8.3f}")
    print(f"  {tag:12s} {'mean gross usdt':22s} {np.mean([r['gross'] for r in sub]):9.0f}  mean uncov frac {np.mean([r['uncovered_gross']/max(r['gross'],1) for r in sub]):.4f}  mean dt_h {np.mean([r['dt_h'] for r in sub]):.3f}")

COMBO0 = 1787716800
s("ALL", rows)
s("COMBO", [r for r in rows if r["grid_anchor"] >= COMBO0])
s("POST-DEP", [r for r in rows if r["grid_anchor"] >= 1788134400])
