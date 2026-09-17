#!/usr/bin/env python3
"""F08 measurement device (independent review 2026-09-17): how much of the TRAINING member set sits inside a feature window that straddles a
contract-generation OPEN boundary. Read-only. It MEASURES exposure counts; it does not (cannot) price the economic impact, which stays UNAVAILABLE.

For each OPEN transition (symbol s, time o) in the lifecycle calendar and each horizon H in HORIZONS (seconds): the anchors E with o ≤ E < o+H are
those whose look-back window of length H reaches back across the boundary (features computed on those windows mix the old and the new generation —
or, for the first bars, are built on frozen/NaN rows). We count, per event and per member source (king meta, DL targets), the anchors at which s IS a
member, the first member anchor after o (hours), and the totals as a share of all member cells. Inputs are sha-bound in the receipt.
env: CALENDAR KING_META DL_TARGETS OUT_JSON [HORIZONS="172800,604800,2592000"]"""
import hashlib, json, os, sys, time
import numpy as np
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def load_members(p, axis_from=None):
    """members are integer indices into the CACHE symbol axis. The king meta carries NO symbol axis (its `names` are the 82 FEATURE names — a
    first version of this device used them and reported every OPEN symbol as 'not on the axis'); the axis is taken from `axis_from` (the DL targets
    file, whose `symbols` build_dev_v4 asserts equal to the cache's). The provenance is returned and the member index range is checked against it."""
    z = np.load(p, allow_pickle=True); E = z["E_ts"].astype(np.int64); M = z["members"]
    if "symbols" in z.files: syms, prov = [str(s) for s in z["symbols"]], p
    elif axis_from: za = np.load(axis_from, allow_pickle=True); syms, prov = [str(s) for s in za["symbols"]], axis_from
    else: raise SystemExit(f"UNAVAILABLE: {p} has no symbol axis and no axis_from given")
    mx = max((int(np.asarray(m).max()) for m in M if len(np.asarray(m))), default=-1)
    if mx >= len(syms): raise SystemExit(f"UNAVAILABLE: member index {mx} exceeds symbol axis of {len(syms)} from {prov}")
    return E, M, syms, prov
def measure(E, M, syms, opens, horizons):
    pos = {s: i for i, s in enumerate(syms)}; idx = {}
    total_cells = int(sum(len(np.asarray(m)) for m in M)); ev = []
    for o, s in sorted(opens):
        j = pos.get(s); row = {"symbol": s, "open_utc": time.strftime("%FT%TZ", time.gmtime(o)), "open_ts": int(o), "in_symbol_axis": j is not None}
        if j is None: ev.append(row); continue
        first = None
        for H in horizons:
            lo, hi = np.searchsorted(E, o), np.searchsorted(E, o + H); n = 0
            for k in range(lo, hi):
                if j in idx.setdefault(k, set(int(x) for x in np.asarray(M[k]).tolist())):
                    n += 1
                    if first is None: first = int(E[k])
            row[f"member_anchors_within_{H//3600}h"] = int(n); row[f"anchors_on_axis_within_{H//3600}h"] = int(hi - lo)
        row["first_member_anchor_after_open_h"] = None if first is None else round((first - o) / 3600.0, 2)
        ev.append(row)
    tot = {f"member_anchors_within_{H//3600}h": int(sum(r.get(f"member_anchors_within_{H//3600}h", 0) for r in ev)) for H in horizons}
    tot["total_member_cells"] = total_cells; tot["share_of_member_cells"] = {k: (v / total_cells if total_cells else None) for k, v in tot.items() if k.startswith("member_anchors")}
    tot["events"] = len(ev); tot["events_with_any_member_anchor"] = {f"{H//3600}h": int(sum(1 for r in ev if r.get(f"member_anchors_within_{H//3600}h", 0) > 0)) for H in horizons}
    return ev, tot
def main():
    E = {k: os.environ.get(k, "") for k in ("CALENDAR", "KING_META", "DL_TARGETS", "OUT_JSON", "HORIZONS")}
    horizons = [int(x) for x in (E["HORIZONS"] or "172800,604800,2592000").split(",")]
    rec = {"gate": "FP2_OPEN_WINDOW_EXPOSURE", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "horizons_s": horizons, "inputs": {}, "UNAVAILABLE": [],
           "meaning": "counts of TRAINING member anchors inside post-OPEN windows of length H (features on those windows straddle the generation boundary); economic impact NOT measured (UNAVAILABLE)"}
    for k in ("CALENDAR", "KING_META", "DL_TARGETS"):
        if not E[k] or not os.path.isfile(E[k]): rec["UNAVAILABLE"].append(f"{k} missing: {E[k]!r}")
        else: rec["inputs"][k] = {"path": E[k], "sha256": sha(E[k])}
    if rec["UNAVAILABLE"]:
        rec["VERDICT"] = "UNAVAILABLE"; json.dump(rec, open(E["OUT_JSON"] or "OPEN_WINDOW_EXPOSURE.json", "w"), indent=1); print("UNAVAILABLE", rec["UNAVAILABLE"]); return 3
    cal = json.load(open(E["CALENDAR"])); opens = [(int(t["effective_ms"]) // 1000, s) for s, v in cal["symbols"].items() for t in v.get("transitions", []) if t["kind"] == "OPEN"]
    rec["n_open_events"] = len(opens); rec["sources"] = {}
    for name, p in (("king", E["KING_META"]), ("dl", E["DL_TARGETS"])):
        Ea, M, syms, prov = load_members(p, axis_from=E["DL_TARGETS"]); ev, tot = measure(Ea, M, syms, opens, horizons)
        rec["sources"][name] = {"n_anchors": int(len(Ea)), "n_symbols": len(syms), "symbol_axis_from": prov, "events": ev, "totals": tot}
        if not all(e["in_symbol_axis"] for e in ev): rec["UNAVAILABLE"].append(f"{name}: {sum(1 for e in ev if not e['in_symbol_axis'])} OPEN symbols not on the symbol axis {prov}")
    rec["VERDICT"] = "MEASURED" if not rec["UNAVAILABLE"] else "PARTIAL"
    json.dump(rec, open(E["OUT_JSON"] or "OPEN_WINDOW_EXPOSURE.json", "w"), indent=1)
    for name, s in rec["sources"].items(): print(name, json.dumps({k: v for k, v in s["totals"].items() if k != "share_of_member_cells"}), "share", {k: (None if v is None else round(v, 6)) for k, v in s["totals"]["share_of_member_cells"].items()})
    print("OPEN_WINDOW_EXPOSURE MEASURED events", len(opens)); return 0
if __name__ == "__main__": sys.exit(main())
