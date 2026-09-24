#!/usr/bin/env python3
"""news2_member_diff_shape.py -- is the 1.54% member difference SHAPED like the D5 member screen?

Pre-registration: docs/PREREG_member_diff_attribution_2026-09-24.md (committed 547f16825, BEFORE any
number here). The three predictions P1/P2/P3 and the judging rules are frozen there.

This does NOT ask "is there a difference" -- that is already measured and, more importantly, it was
DECLARED IN ADVANCE and adjudicated: AMENDMENT_1 L65 and DESIGN_producer_new_contract L485 both state
that implementing D5 over the member screen (L497-L505) means "the member set may change", with the
mechanism "v7 near the 1e-4 gate, qvm ordering near rank 400", and lead ruled on 2026-09-23 that the
member screen is inside D5. So the open question is whether the difference has the SHAPE that story
predicts -- a boundary effect -- or some other shape, which would mean the declared mechanism does not
account for it.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT MEASURED (named, per the pre-registration):
  - the qvm rank of the 43,025 researcher-only pairs: NC has no qvm for a non-member, so that half
    cannot be judged by P1. Counts only.
  - D5's SHARE of the difference: that needs D5 switched off and re-run. Shape is not share.
  - why fund_ema / fund_now differ: unrelated to membership, separate case.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--researcher-panel", required=True)
    ap.add_argument("--researcher-axis", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_member_diff_attribution_2026-09-24.md @ 547f16825",
           "status": "SHAPE_OF_THE_DIFFERENCE_NOT_ITS_SHARE",
           "declared_in_advance": {
               "AMENDMENT_1_L65": "D5/D6 covering the member screen L497-L505 => the member set may change",
               "DESIGN_producer_new_contract_L485": "mechanism: v7 near the 1e-4 gate, qvm order near rank 400",
               "DESIGN_producer_new_contract_L491": "lead 2026-09-23: the member screen is inside D5 (B8)"},
           "inputs": {k: {"path": p, "bytes": os.path.getsize(p)} for k, p in
                      (("nc_features", a.nc_features), ("researcher_panel", a.researcher_panel),
                       ("researcher_axis", a.researcher_axis))}}

    N = np.load(a.nc_features, allow_pickle=False)
    R = np.load(a.researcher_panel, allow_pickle=False)
    AX = np.load(a.researcher_axis, allow_pickle=False)

    n_anch = N["anchors"].astype(np.int64)
    n_off = N["off"].astype(np.int64)
    n_m = N["m"].astype(np.int64)
    qvm = np.asarray(N["qvm"]).astype(np.float64)
    r_ts = AX["E_ts"].astype(np.int64)
    pa, ps = R["pair_a"].astype(np.int64), R["pair_s"].astype(np.int64)
    r_anchor_ts = r_ts[pa]

    # researcher member set per anchor
    order = np.argsort(r_anchor_ts, kind="stable")
    rts_s, rps_s = r_anchor_ts[order], ps[order]
    uniq, starts = np.unique(rts_s, return_index=True)
    ends = np.append(starts[1:], rts_s.size)
    res_members = {int(t): rps_s[s:e] for t, s, e in zip(uniq, starts, ends)}

    per_anchor, only_nc_norm_ranks, both_norm_ranks = [], [], []
    n_anchors_with_diff = 0
    dn_list = []
    for i, t in enumerate(n_anch):
        t = int(t)
        if t not in res_members:
            continue
        s, e = n_off[i], n_off[i + 1]
        nc_syms = n_m[s:e]
        nc_qvm = qvm[s:e]
        rs = res_members[t]
        n_nc, n_rs = nc_syms.size, rs.size
        dn_list.append(n_nc - n_rs)
        rset = set(rs.tolist())
        in_res = np.array([int(x) in rset for x in nc_syms], bool)
        only_nc = ~in_res
        k_only = int(only_nc.sum())
        k_only_res = n_rs - int(in_res.sum())
        if k_only or k_only_res:
            n_anchors_with_diff += 1
        # rank by qvm DESCENDING within NC's members: rank 1 = most liquid; normalise to (0, 1]
        if n_nc >= 5:
            ordq = np.argsort(-nc_qvm, kind="stable")
            rank = np.empty(n_nc, np.float64)
            rank[ordq] = np.arange(1, n_nc + 1, dtype=np.float64)
            nr = rank / n_nc
            if k_only:
                only_nc_norm_ranks.append(nr[only_nc])
            if in_res.any():
                both_norm_ranks.append(nr[in_res])
        per_anchor.append({"anchor": t, "n_nc": n_nc, "n_res": n_rs,
                           "only_nc": k_only, "only_res": k_only_res})

    if not per_anchor:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "no shared anchor"
        json.dump(rec, open(a.out, "w"), indent=2); print("MEMBER_DIFF VERDICT=UNAVAILABLE"); return 2

    onr = np.concatenate(only_nc_norm_ranks) if only_nc_norm_ranks else np.zeros(0)
    bnr = np.concatenate(both_norm_ranks) if both_norm_ranks else np.zeros(0)
    dn = np.array(dn_list, np.float64)
    n_shared = len(per_anchor)

    # ---- RED CONTROL (must run before P1 is reported) ----
    # baseline: symbols present on BOTH sides must NOT concentrate in the last 10% -- otherwise
    # "concentrated in the last 10%" is a property of every symbol and P1 has no resolution.
    base_median = float(np.median(bnr)) if bnr.size else None
    base_not_concentrated = base_median is not None and base_median < 0.9
    # mutation: reversing the rank axis must flip the verdict of the same criterion.
    mut_median = float(np.median(1.0 - onr)) if onr.size else None
    obs_median = float(np.median(onr)) if onr.size else None
    mut_flips = (obs_median is not None and mut_median is not None
                 and (obs_median >= 0.9) != (mut_median >= 0.9))
    ctrl = {"baseline_both_sides_median_norm_rank": base_median,
            "baseline_not_concentrated": base_not_concentrated,
            "mutation_reversed_median": mut_median, "mutation_flips_verdict": mut_flips,
            "n_only_nc_positions": int(onr.size), "n_both_positions": int(bnr.size)}
    ctrl["baseline_green"] = bool(base_not_concentrated)
    rec["red_control"] = ctrl

    p1_ok = obs_median is not None and obs_median >= 0.9
    p2_med = float(np.median(np.abs(dn))) if dn.size else None
    p2_ok = p2_med is not None and p2_med <= 1
    p3_frac = n_anchors_with_diff / n_shared
    p3_ok = p3_frac >= 0.5
    rec["predictions"] = {
        "P1_only_nc_ranks_concentrate_near_the_cut": {
            "criterion": "median normalised qvm rank of NC-only symbols >= 0.9",
            "median_norm_rank": obs_median,
            "p10": float(np.percentile(onr, 10)) if onr.size else None,
            "p25": float(np.percentile(onr, 25)) if onr.size else None,
            "p75": float(np.percentile(onr, 75)) if onr.size else None,
            "frac_in_last_10pct": float((onr >= 0.9).mean()) if onr.size else None,
            "frac_in_last_25pct": float((onr >= 0.75).mean()) if onr.size else None,
            "holds": bool(p1_ok)},
        "P2_member_counts_almost_equal": {
            "criterion": "median |n_NC - n_RES| <= 1", "median_abs_dn": p2_med,
            "mean_dn": float(dn.mean()) if dn.size else None,
            "max_abs_dn": float(np.abs(dn).max()) if dn.size else None,
            "frac_equal_counts": float((dn == 0).mean()) if dn.size else None,
            "holds": bool(p2_ok)},
        "P3_difference_is_widespread": {
            "criterion": "fraction of shared anchors with any difference >= 0.5",
            "n_shared_anchors": n_shared, "n_anchors_with_diff": n_anchors_with_diff,
            "frac": p3_frac, "holds": bool(p3_ok)},
    }
    rec["named_non_measurement"] = {
        "researcher_only_pairs_rank": "NC has no qvm for a non-member; counts only, no rank judgement",
        "share_not_measured": "shape is not share; D5's share needs D5 switched off and re-run"}
    rec["totals"] = {"only_nc_pairs": int(sum(p["only_nc"] for p in per_anchor)),
                     "only_res_pairs": int(sum(p["only_res"] for p in per_anchor))}

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = ("red control: symbols present on both sides ALSO concentrate in the last 10%, "
                      "so P1 has no resolution on this population")
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    P = rec["predictions"]
    print(f"MEMBER_DIFF VERDICT={rec['verdict']}  shared_anchors={n_shared}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} "
          f"(both-sides median norm rank {base_median}) mutation_flips={mut_flips}")
    print(f"  totals: only_nc pairs {rec['totals']['only_nc_pairs']}  "
          f"only_res pairs {rec['totals']['only_res_pairs']}")
    q = P["P1_only_nc_ranks_concentrate_near_the_cut"]
    print(f"  P1 {'HOLDS' if q['holds'] else 'FAILS':6s} median_norm_rank={q['median_norm_rank']} "
          f"p25={q['p25']} p75={q['p75']} in_last_10%={q['frac_in_last_10pct']} "
          f"in_last_25%={q['frac_in_last_25pct']}")
    q = P["P2_member_counts_almost_equal"]
    print(f"  P2 {'HOLDS' if q['holds'] else 'FAILS':6s} median|dn|={q['median_abs_dn']} "
          f"mean_dn={q['mean_dn']} max|dn|={q['max_abs_dn']} frac_equal={q['frac_equal_counts']}")
    q = P["P3_difference_is_widespread"]
    print(f"  P3 {'HOLDS' if q['holds'] else 'FAILS':6s} anchors_with_diff={q['n_anchors_with_diff']}"
          f"/{q['n_shared_anchors']} = {q['frac']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
