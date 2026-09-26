#!/usr/bin/env python3
"""d10_reseed_combo_impact.py -- combo/target-layer impact of the new seats. NO ENGINE RUN.

lead 2026-09-26: feed the new seats into combo and report sum|dw|, the top 20 names, the gross change and how
many names flip direction. Read-only.

THE TARGET BUILD IS THE PRODUCER'S, copied line for line from shadow_loop_v3.py:800-822 and fed the SAME inputs
from each anchor's own snapshot, so the ONLY thing that varies between the two runs is the seat vector w3:
  z    = w3[0]*nan_to_num(legz["king"]) + w3[1]*nan_to_num(legz["rev24"]) + w3[2]*nan_to_num(legz["fund"])
  sel  = qv4h >= P["qv4h_min"]                      <- reconstructed from prev_rec["sel_idx"]
  w    = where(sel, z, 0.0); w[sel] -= w[sel].mean()   <- the E-0825-B form: demean over sel ONLY
  g    = |w|.sum(); w /= g
  capw = P["cap_mult"] / max(sel.sum(), 1); w = clip(w, -capw, capw)
  g2   = |w|.sum(); w /= g2
  tgt  = zeros(NW); tgt[m] = w

WHY tgt AND NOT sm: the smoothed book sm = H + alpha*(tgt - H) depends on H, the PREVIOUS holdings, which would
itself have diverged over the whole history under a different seat series. Comparing tgt isolates the seat
effect at each anchor; comparing sm would silently mix in a path difference this device cannot reconstruct.

WHY THERE IS NO "GROSS CHANGE" TO REPORT: after `w /= g2` the target satisfies sum|tgt| == 1 by construction, so
the target-layer gross is IDENTICAL for any seat vector. Reporting a gross delta here would be reporting a
rounding residue as if it were an effect. The book's gross comes from gross_mult applied later, outside this
layer. The device asserts sum|tgt| == 1 on both sides instead.
"""
import datetime
import hashlib
import json
import os
import statistics as st
import sys

import numpy as np

SNAP = os.path.expanduser("~/wide_shadow/state/snap")
CFG = os.path.expanduser("~/wide_shadow/shadow_bundle/config.json")
DASH = os.path.expanduser("~/regime_dash/regime_dash.jsonl")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def build_target(legz, members, sel_idx, w3, P, NW):
    """shadow_loop_v3.py:800-822, verbatim in form."""
    m = np.asarray(members, np.int64)
    z = (w3[0] * np.nan_to_num(np.asarray(legz["king"], float))
         + w3[1] * np.nan_to_num(np.asarray(legz["rev24"], float))
         + w3[2] * np.nan_to_num(np.asarray(legz["fund"], float)))
    sel = np.zeros(len(m), bool)
    sel[np.asarray(sel_idx, np.int64)] = True
    if sel.sum() < P["sel_min"]:
        return None, sel
    w = np.where(sel, z, 0.0)
    w[sel] -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9:
        return None, sel
    w = w / g
    capw = P["cap_mult"] / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9:
        w = w / g2
    tgt = np.zeros(NW)
    tgt[m] = w
    return tgt, sel


def main():
    new_seats_json, out = sys.argv[1], sys.argv[2]
    P = json.load(open(CFG))["params"]
    panel = json.load(open(CFG))["symbols_panel"]
    NW = len(panel)
    NEW = {r["anchor"]: r for r in json.load(open(new_seats_json))["seat_impact_from_2026_09_24"]["rows"]
           if "new_w3" in r}

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "read_only": True, "engine_run": False,
           "target_build": "shadow_loop_v3.py:800-822, same inputs, only w3 varies",
           "why_tgt_not_sm": "sm depends on the previous holdings H, which would itself have diverged under a "
                             "different seat history; tgt isolates the seat effect at the anchor",
           "gross_note": "sum|tgt| == 1 by construction after w /= g2, so the target-layer gross is identical "
                         "for any seat vector; asserted on both sides rather than reported as a delta",
           "inputs": {"config": {"path": CFG, "sha256": sha(CFG)},
                      "new_seats": {"path": new_seats_json, "sha256": sha(new_seats_json)}},
           "anchors": []}

    for a_utc in sorted(NEW):
        A = int(datetime.datetime.strptime(a_utc, "%Y-%m-%dT%H:%MZ")
                .replace(tzinfo=datetime.timezone.utc).timestamp())
        p = os.path.join(SNAP, str(A), "aux.json")
        if not os.path.exists(p):
            rec["anchors"].append({"anchor": a_utc, "skipped": "no snapshot for this anchor"})
            continue
        pr = json.load(open(p)).get("prev_rec") or {}
        if int(pr.get("anchor_ts", -1)) != A:
            rec["anchors"].append({"anchor": a_utc, "skipped": "prev_rec anchor_ts mismatch"})
            continue
        lw = NEW[a_utc]["live_w3_raw"]
        nw = NEW[a_utc]["new_w3"]
        t_live, sel = build_target(pr["legz"], pr["members"], pr["sel_idx"], lw, P, NW)
        t_new, _ = build_target(pr["legz"], pr["members"], pr["sel_idx"], nw, P, NW)
        if t_live is None or t_new is None:
            rec["anchors"].append({"anchor": a_utc, "skipped": "target build returned None (sel/g gate)"})
            continue
        for nm, t in (("live", t_live), ("new", t_new)):
            assert abs(np.abs(t).sum() - 1.0) < 1e-9, (nm, "target gross is not 1", float(np.abs(t).sum()))
        d = t_new - t_live
        nz = (np.abs(t_live) > 1e-12) | (np.abs(t_new) > 1e-12)
        flips = int(((np.sign(t_live) * np.sign(t_new)) < 0).sum())
        order = np.argsort(-np.abs(d))
        top = [{"symbol": panel[int(j)], "live": float(t_live[j]), "new": float(t_new[j]),
                "d": float(d[j])} for j in order[:20] if abs(float(d[j])) > 0]
        rec["anchors"].append({
            "anchor": a_utc, "live_w3": lw, "new_w3": nw,
            "members": len(pr["members"]), "sel": int(sel.sum()),
            "names_with_a_position": int(nz.sum()),
            "sum_abs_dw": float(np.abs(d).sum()),
            "sum_abs_dw_pct_of_gross": float(np.abs(d).sum() / 1.0 * 100.0),
            "max_abs_dw": float(np.abs(d).max()),
            "direction_flips": flips,
            "gross_live": float(np.abs(t_live).sum()), "gross_new": float(np.abs(t_new).sum()),
            "top20_by_abs_dw": top})

    ok = [a for a in rec["anchors"] if "sum_abs_dw" in a]
    if ok:
        rec["summary"] = {
            "anchors": len(ok),
            "sum_abs_dw": {"mean": st.mean([a["sum_abs_dw"] for a in ok]),
                           "median": st.median([a["sum_abs_dw"] for a in ok]),
                           "min": min(a["sum_abs_dw"] for a in ok),
                           "max": max(a["sum_abs_dw"] for a in ok)},
            "direction_flips": {"mean": st.mean([a["direction_flips"] for a in ok]),
                                "min": min(a["direction_flips"] for a in ok),
                                "max": max(a["direction_flips"] for a in ok)},
            "max_abs_dw": max(a["max_abs_dw"] for a in ok),
            "gross_identical_every_anchor": all(abs(a["gross_live"] - a["gross_new"]) < 1e-9 for a in ok)}

    print(f"{'anchor':18s} {'sum|dw|':>9s} {'%gross':>8s} {'max|dw|':>9s} {'flips':>6s} {'names':>6s} {'sel':>5s}")
    for a in rec["anchors"]:
        if "sum_abs_dw" not in a:
            print(f"{a['anchor']:18s} {a['skipped']}")
            continue
        print(f"{a['anchor']:18s} {a['sum_abs_dw']:>9.5f} {a['sum_abs_dw_pct_of_gross']:>7.2f}% "
              f"{a['max_abs_dw']:>9.6f} {a['direction_flips']:>6d} {a['names_with_a_position']:>6d} {a['sel']:>5d}")
    if ok:
        s = rec["summary"]
        print()
        print(f"  sum|dw|  mean {s['sum_abs_dw']['mean']:.5f}  median {s['sum_abs_dw']['median']:.5f}  "
              f"min {s['sum_abs_dw']['min']:.5f}  max {s['sum_abs_dw']['max']:.5f}   (target gross = 1.0)")
        print(f"  flips    mean {s['direction_flips']['mean']:.1f}  min {s['direction_flips']['min']}  "
              f"max {s['direction_flips']['max']}")
        print(f"  gross identical at every anchor: {s['gross_identical_every_anchor']}")
        print()
        a0 = ok[-1]
        print(f"  top 10 by |dw| at {a0['anchor']}:")
        for t in a0["top20_by_abs_dw"][:10]:
            print(f"     {t['symbol']:14s} live {t['live']:+.6f} -> new {t['new']:+.6f}  d {t['d']:+.6f}")

    def _no_numpy(o):
        raise TypeError(f"refusing to serialise {type(o).__name__}; convert to a plain float first")
    json.dump(rec, open(out, "w"), indent=1, default=_no_numpy)
    print(f"\nreceipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
