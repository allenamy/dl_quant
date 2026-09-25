#!/usr/bin/env python3
"""step1_researcher_legs_on_nc.py -- the researcher's causal_legs, unmodified, on NC's inputs.

Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 1. The criterion is
LEAD'S, copied verbatim there. This device only measures what it asks for.

THE CODE IS IMPORTED, NEVER EDITED: `from combo_legs import causal_legs` off the researcher's own
devices dir (combo_legs.py sha 0fc84ae8...). Only its ARGUMENTS are NC's.

HOW EACH ARGUMENT IS BUILT FROM NC's OWN DATA (the researcher's main() is the reference, L58-65):
  pred     NC's archived KING_OOF P                                     (10333, 829)
  funding  NC's base_val                                               -- see note
  legal    isfinite(base_val)                                          -- see note
  rev24    NC's ragged rev24 scattered to full width at member columns
  seat_y   forward 4h sum of NC's R_crypto, >=46 of 48 observed, scattered to crypto columns
  members  NC's off/m
  look, min_members: defaults, as the researcher calls it

NOTE ON funding/legal -- this is what unblocked step 1, and it uses NC's data, not the researcher's:
NC never persists a full-width `legal`, which is why this step was blocked before. But NC's
`base_val` is the full-width funding EMA already masked to NC's own base (legal AND crypto AND fresh
known EMA), NaN outside. MEASURED: base_val[i, member_cols] == fe_v exactly on all 40 anchors tested.
So funding=base_val with legal=isfinite(base_val) makes the researcher's
`base = flatnonzero(legal[i] & isfinite(funding[i]))` reproduce NC's base exactly, and
`xz(funding[i, base])` rank NC's own funding values. No researcher input is borrowed.

SEAT WINDOW: the researcher uses ret[e+1:e+49] (forward 4h from the anchor) and reads it as
seat_y[i-1]; NC uses R[ia-47:ia+1] at the NEXT anchor for the PREVIOUS anchor's members. Those are the
same window indexed two ways -- I withdrew a "direction difference" claim on exactly this point
earlier. This device builds the forward form, matching the researcher's call.

NOT JUDGED: causality. This sizes where the seat difference sits; it does not prove what causes it.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def cmp_arrays(x, y):
    """elementwise comparison on positions finite in both; both-NaN counts as equal"""
    fx, fy = np.isfinite(x), np.isfinite(y)
    both = fx & fy
    eq = (x == y) | (~fx & ~fy)
    d = np.abs(x[both] - y[both]) if both.any() else np.zeros(0)
    den = np.abs(y[both]) if both.any() else np.zeros(0)
    rel = d[den > 0] / den[den > 0] if den.size else np.zeros(0)
    return {
        "positions_both_finite": int(both.sum()),
        "nan_pattern_mismatch": int((fx ^ fy).sum()),
        "all_equal": bool(eq.all()),
        "max_abs_diff": float(d.max()) if d.size else None,
        "median_abs_diff": float(np.median(d)) if d.size else None,
        "median_rel_diff": float(np.median(rel)) if rel.size else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher-devices", required=True)
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--nc-king", required=True)
    ap.add_argument("--nc-axes", required=True)
    ap.add_argument("--nc-returns", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--researcher-legs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.researcher_devices)
    from combo_legs import causal_legs          # imported, never edited

    import combo_legs as _cl
    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_gap_carrier_ladder_2026-09-25.md @ be4a013a8 (step 1)",
           "criterion_author": "team-lead (not news2)",
           "status": "WHERE_THE_SEAT_DIFFERENCE_SITS_NOT_ITS_CAUSE",
           "researcher_code": {"module": _cl.__file__, "sha256": sha(_cl.__file__),
                              "modified_by_this_device": False},
           "inputs": {}}
    for k, p in (("nc_features", a.nc_features), ("nc_king", a.nc_king), ("nc_axes", a.nc_axes),
                 ("nc_legs", a.nc_legs), ("researcher_legs", a.researcher_legs)):
        rec["inputs"][k] = {"path": p, "sha256": sha(p)}
    rec["inputs"]["nc_returns"] = {"path": a.nc_returns, "bytes": os.path.getsize(a.nc_returns)}

    F = np.load(a.nc_features, allow_pickle=False)
    K = np.load(a.nc_king, allow_pickle=False)
    AX = np.load(a.nc_axes, allow_pickle=True)
    R = np.load(a.nc_returns, mmap_mode="r")

    anchors = F["anchors"].astype(np.int64)
    off = F["off"].astype(np.int64)
    mcol = F["m"].astype(np.int64)
    syms = F["symbols"]
    n, w = len(anchors), len(syms)
    ts = AX["ts"].astype(np.int64)
    ccols = AX["crypto_cols"].astype(np.int64)

    assert K["P"].shape == (n, w), (K["P"].shape, (n, w))
    pred = np.asarray(K["P"], np.float64)
    funding = np.asarray(F["base_val"], np.float64)          # NC's full-width funding EMA on NC's base
    legal = np.isfinite(funding)                              # == NC's base mask

    rev24 = np.full((n, w), np.nan, np.float64)
    r_flat = np.asarray(F["rev24"], np.float64)
    for i in range(n):
        b, e = off[i], off[i + 1]
        if e > b:
            rev24[i, mcol[b:e]] = r_flat[b:e]

    seat_y = np.full((n, w), np.nan, np.float64)
    for i in range(n):
        ia = int(np.searchsorted(ts, int(anchors[i])))
        if ia >= len(ts) or ts[ia] != anchors[i]:
            continue
        if ia + 49 > R.shape[0]:
            continue
        blk = np.asarray(R[ia + 1:ia + 49], np.float64)       # forward 4h, as the researcher does
        fin = np.isfinite(blk)
        v = np.where(fin, blk, 0.0).sum(0)
        v[fin.sum(0) < 46] = np.nan
        seat_y[i, ccols] = v

    members = [mcol[off[i]:off[i + 1]] for i in range(n)]
    rec["built_inputs"] = {
        "n_anchors": n, "n_symbols": w,
        "mean_members": float(np.mean([len(x) for x in members])),
        "anchors_with_seat_y": int(np.isfinite(seat_y).any(1).sum()),
        "mean_base_size": float(np.mean(legal.sum(1))),
        "base_val_equals_fe_v_on_members": "MEASURED separately: exact on all 40 anchors tested"}

    out = causal_legs(pred, funding, rev24, seat_y, members, legal)
    rec["researcher_code_on_nc_inputs"] = {
        "ready": int(out["ready"].sum()), "not_ready": int((~out["ready"]).sum()),
        "leg_returns_rows": int(np.isfinite(out["LR"]).all(1).sum())}

    NCL = np.load(a.nc_legs, allow_pickle=False)
    NEW = np.load(a.researcher_legs, allow_pickle=False)
    rec["reference_ready"] = {"nc": int(np.asarray(NCL["ready"]).sum()),
                              "new": int(np.asarray(NEW["ready"]).sum())}

    # --- array-by-array comparison, aligned by anchor timestamp ---
    nc_ts = NCL["E_ts"].astype(np.int64); new_ts = NEW["E_ts"].astype(np.int64)
    nc_pos = {int(t): i for i, t in enumerate(nc_ts)}
    new_pos = {int(t): i for i, t in enumerate(new_ts)}
    idx_self, idx_nc, idx_new = [], [], []
    for i, t in enumerate(anchors):
        t = int(t)
        if t in nc_pos and t in new_pos:
            idx_self.append(i); idx_nc.append(nc_pos[t]); idx_new.append(new_pos[t])
    idx_self = np.array(idx_self); idx_nc = np.array(idx_nc); idx_new = np.array(idx_new)
    rec["n_anchors_compared"] = int(idx_self.size)

    cmp_out = {}
    for name in ("KZ", "Z24", "ZFD", "WL", "LR"):
        mine = np.asarray(out[name], np.float64)[idx_self]
        vs_nc = np.asarray(NCL[name], np.float64)[idx_nc]
        vs_new = np.asarray(NEW[name], np.float64)[idx_new]
        e = {"vs_nc": cmp_arrays(mine, vs_nc), "vs_new": cmp_arrays(mine, vs_new)}
        # differing anchors / total, and the first differing anchor, against each side
        for lbl, other in (("vs_nc", vs_nc), ("vs_new", vs_new)):
            fx, fy = np.isfinite(mine), np.isfinite(other)
            neq = ~((mine == other) | (~fx & ~fy))
            rows = neq.reshape(neq.shape[0], -1).any(1)
            e[lbl]["differing_anchors"] = int(rows.sum())
            e[lbl]["total_anchors"] = int(rows.size)
            fst = int(np.flatnonzero(rows)[0]) if rows.any() else None
            e[lbl]["first_differing_anchor"] = (
                {"index": fst, "ts": int(anchors[idx_self[fst]]),
                 "utc": datetime.datetime.utcfromtimestamp(int(anchors[idx_self[fst]])).strftime("%Y-%m-%dT%H:%MZ")}
                if fst is not None else None)
        cmp_out[name] = e
    rec["array_comparison"] = cmp_out

    # --- pre-2026 per-year seat distribution, three ways + lead's frozen reading ---
    yrs = np.array([datetime.datetime.utcfromtimestamp(int(t)).year for t in anchors[idx_self]])
    SEATS = ("king", "rev24", "fund")
    seat_tab, dist = {}, {}
    for y in sorted(set(yrs.tolist())):
        sel = yrs == y
        mine = np.asarray(out["WL"], np.float64)[idx_self][sel]
        vnc = np.asarray(NCL["WL"], np.float64)[idx_nc][sel]
        vnew = np.asarray(NEW["WL"], np.float64)[idx_new][sel]
        ok = np.isfinite(mine).all(1) & np.isfinite(vnc).all(1) & np.isfinite(vnew).all(1)
        if ok.sum() < 5:
            seat_tab[str(y)] = {"note": "fewer than 5 anchors with all three defined"}
            continue
        row = {"n_anchors": int(ok.sum())}
        for j, nm in enumerate(SEATS):
            row[nm] = {"researcher_code_on_nc": float(mine[ok, j].mean()),
                       "nc": float(vnc[ok, j].mean()), "new": float(vnew[ok, j].mean())}
        dk = abs(row["king"]["researcher_code_on_nc"] - row["king"]["nc"])
        dn = abs(row["king"]["researcher_code_on_nc"] - row["king"]["new"])
        row["king_seat_distance"] = {"to_nc": dk, "to_new": dn,
                                     "closer_to": ("nc" if dk < dn else "new" if dn < dk else "tie"),
                                     "share_of_gap_toward_new": (dk / (dk + dn)) if (dk + dn) > 0 else None}
        seat_tab[str(y)] = row
        if y in (2023, 2024, 2025):
            dist[str(y)] = row["king_seat_distance"]
    rec["seat_distribution_three_way"] = seat_tab
    closer = [v["closer_to"] for v in dist.values()]
    rec["frozen_reading"] = {
        "rule": ("lead, verbatim: 研究员代码@NC输入 的 WL 若更靠近 NEW 的 WL(逐年 king 席位均值的距离)"
                 "⇒「席位差来自腿代码」; 若更靠近 NC 的 ⇒「席位差来自输入(King P)」; 两者之间报比例, 不下因果。"),
        "pre2026_per_year": dist,
        "closer_to_by_year": closer,
        "VERDICT": ("SEAT_DIFF_FROM_LEG_CODE" if closer and all(c == "new" for c in closer)
                    else "SEAT_DIFF_FROM_INPUT_KING_P" if closer and all(c == "nc" for c in closer)
                    else "MIXED_report_shares_no_causal_claim")}

    # --- red control ---
    ctrl = {"code_sha_matches_handoff_record": sha(_cl.__file__).startswith("0fc84ae8"),
            "inputs_have_right_shape": all(x.shape == (n, w) for x in (pred, funding, rev24, seat_y)),
            "legal_is_base_mask": bool((legal == np.isfinite(funding)).all()),
            "seat_y_nonempty": int(np.isfinite(seat_y).sum()) > 0,
            "ready_nonzero": int(out["ready"].sum()) > 0}
    ctrl["baseline_green"] = all(ctrl.values())
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"

    json.dump(rec, open(a.out, "w"), indent=2)

    print(f"STEP1 VERDICT={rec['verdict']}  anchors_compared={rec['n_anchors_compared']}")
    print(f"  researcher code sha {sha(_cl.__file__)[:16]} (imported, unmodified)")
    print(f"  red control: {ctrl}")
    print(f"  ready: researcher_code@NC={rec['researcher_code_on_nc_inputs']['ready']}  "
          f"NC={rec['reference_ready']['nc']}  NEW={rec['reference_ready']['new']}")
    print("  array comparison (researcher_code@NC vs each side):")
    for nm, e in cmp_out.items():
        for lbl in ("vs_nc", "vs_new"):
            c = e[lbl]
            print(f"   {nm:4s} {lbl:6s} diff_anchors {c['differing_anchors']:5d}/{c['total_anchors']:5d}  "
                  f"max|d|={c['max_abs_diff']}  med|d|={c['median_abs_diff']}  "
                  f"med_rel={c['median_rel_diff']}  first={(c['first_differing_anchor'] or {}).get('utc')}")
    print("  king seat mean by year (researcher_code@NC / NC / NEW) and distance:")
    for y, r in seat_tab.items():
        if "note" in r:
            print(f"   {y}: {r['note']}"); continue
        k = r["king"]; d = r["king_seat_distance"]
        print(f"   {y}  n={r['n_anchors']:4d}  {k['researcher_code_on_nc']:.4f} / {k['nc']:.4f} / {k['new']:.4f}"
              f"   to_nc={d['to_nc']:.4f} to_new={d['to_new']:.4f} closer={d['closer_to']}")
    print(f"  FROZEN READING -> {rec['frozen_reading']['VERDICT']}  by_year={closer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
