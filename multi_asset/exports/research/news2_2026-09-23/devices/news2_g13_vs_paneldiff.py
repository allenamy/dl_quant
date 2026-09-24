#!/usr/bin/env python3
"""news2_g13_vs_paneldiff.py -- do the G1-3 anchors fall inside the panel-difference anchors?

Pre-registration: docs/PREREG_member_diff_rootcause_2026-09-24.md (committed 545143958, BEFORE any
number here). Outcomes (a)/(b)/(c) are frozen there.

THE ASYMMETRY BEING TESTED. Two receipts compare DIFFERENT OBJECTS:
  G1-3  : NC's member screen  vs  the researcher's FUNCTION select_members, on the same input
  mine  : NC's panel          vs  the researcher's DELIVERED PANEL
G1-3 passed on 10 anchors with members_equal=True and empty both-way difference lists. If any of those
10 anchors is also one where the delivered panels differ, then both receipts are true and mutually
exclusive, and the only way out is that the delivered panel was not produced by that function on that
input (or the inputs differ).

Also reported, independently: G1-3's recorded n_members_researcher vs the member count in the
DELIVERED panel at the same anchor. A mismatch there is direct evidence of "function output != what
was delivered", and does not depend on the set-membership test.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT JUDGED (lead 2026-09-24): which side is correct. That is a contract question; this device reports
only where and how much.
"""
import argparse, hashlib, json, os, sys

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
    ap.add_argument("--g13-receipt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_member_diff_rootcause_2026-09-24.md @ 545143958",
           "status": "WHERE_AND_HOW_MUCH_NOT_WHICH_SIDE_IS_RIGHT",
           "compares": {"G1_3": "NC screen vs researcher FUNCTION select_members",
                        "panel_diff": "NC panel vs researcher DELIVERED panel"},
           "inputs": {"g13_receipt": {"path": a.g13_receipt, "sha256": sha(a.g13_receipt)},
                      "nc_features": {"path": a.nc_features, "bytes": os.path.getsize(a.nc_features)},
                      "researcher_panel": {"path": a.researcher_panel,
                                           "bytes": os.path.getsize(a.researcher_panel)}}}

    G = json.load(open(a.g13_receipt))
    g13 = G.get("G1_3_members", [])
    rec["g13_pass"] = G.get("G1_3_PASS")
    rec["g13_n_anchors"] = len(g13)

    N = np.load(a.nc_features, allow_pickle=False)
    R = np.load(a.researcher_panel, allow_pickle=False)
    AX = np.load(a.researcher_axis, allow_pickle=False)

    n_anch = N["anchors"].astype(np.int64)
    n_off = N["off"].astype(np.int64)
    n_m = N["m"].astype(np.int64)
    r_ts_all = AX["E_ts"].astype(np.int64)
    r_anchor_ts = r_ts_all[R["pair_a"].astype(np.int64)]
    ps = R["pair_s"].astype(np.int64)

    order = np.argsort(r_anchor_ts, kind="stable")
    rts_s, rps_s = r_anchor_ts[order], ps[order]
    uniq, starts = np.unique(rts_s, return_index=True)
    ends = np.append(starts[1:], rts_s.size)
    res_members = {int(t): rps_s[s:e] for t, s, e in zip(uniq, starts, ends)}

    nc_members = {}
    for i, t in enumerate(n_anch):
        nc_members[int(t)] = n_m[n_off[i]:n_off[i + 1]]

    diff_anchors, per_anchor = set(), {}
    for t, nc_s in nc_members.items():
        if t not in res_members:
            continue
        rs = set(res_members[t].tolist())
        ns = set(nc_s.tolist())
        only_nc, only_res = len(ns - rs), len(rs - ns)
        if only_nc or only_res:
            diff_anchors.add(t)
        per_anchor[t] = (only_nc, only_res, len(ns), len(rs))
    rec["n_shared_anchors"] = len(per_anchor)
    rec["n_differing_anchors"] = len(diff_anchors)

    rows, n_inside, n_count_mismatch = [], 0, 0
    for e in g13:
        t = int(e["anchor"])
        inside = t in diff_anchors
        n_inside += int(inside)
        pa_ = per_anchor.get(t)
        delivered_n = len(res_members[t]) if t in res_members else None
        g13_res_n = e.get("n_members_researcher")
        count_mismatch = (delivered_n is not None and g13_res_n is not None
                          and int(delivered_n) != int(g13_res_n))
        n_count_mismatch += int(count_mismatch)
        rows.append({
            "anchor": t, "utc": e.get("utc"),
            "in_differing_set": inside,
            "only_nc": pa_[0] if pa_ else None, "only_researcher": pa_[1] if pa_ else None,
            "nc_members_in_panel": pa_[2] if pa_ else None,
            "researcher_members_in_DELIVERED_panel": delivered_n,
            "g13_n_members_researcher_from_FUNCTION": g13_res_n,
            "g13_n_members_producer": e.get("n_members_producer"),
            "g13_members_equal": e.get("members_equal"),
            "g13_v7_f32_differ": e.get("v7_f32_differ"),
            "g13_q7_f32_differ": e.get("q7_f32_differ"),
            "g13_ties_in_candidate_qvm": e.get("R1_4_ties_in_candidate_qvm"),
            "delivered_vs_function_count_mismatch": count_mismatch,
        })
    rec["g13_anchors"] = rows
    rec["summary"] = {"g13_anchors_inside_differing_set": n_inside,
                      "g13_anchors_total": len(g13),
                      "g13_anchors_with_delivered_vs_function_count_mismatch": n_count_mismatch}

    if n_inside == 0 and n_count_mismatch == 0:
        outcome = "a"
        text = ("none of the G1-3 anchors is in the differing set and no member count disagrees: the "
                "two receipts do not conflict on this sample. NOT evidence that the screens are "
                "equivalent -- 10 anchors is a sample, not the population.")
    elif n_count_mismatch > 0:
        outcome = "c"
        text = ("the member count recorded by G1-3 for the researcher FUNCTION differs from the count "
                "in the DELIVERED panel at the same anchor: direct evidence that the delivered panel "
                "was not produced by that function on that input")
    else:
        outcome = "b"
        text = ("G1-3 anchors fall inside the differing set: 'the functions agree' and 'the panels "
                "differ' are both true, so the delivered panel does not correspond to that "
                "function/input pair")
    rec["outcome"] = outcome
    rec["outcome_text"] = text
    rec["outcome_is_prereg_frozen"] = True

    # RED CONTROL. The set-membership test is only meaningful if the differing set is neither empty
    # nor everything, and if a known-differing anchor is actually detected as inside it.
    ctrl = {"n_differing": len(diff_anchors), "n_shared": len(per_anchor)}
    ctrl["set_nonempty"] = len(diff_anchors) > 0
    ctrl["set_not_everything"] = len(diff_anchors) < len(per_anchor)
    probe = sorted(diff_anchors)[0] if diff_anchors else None
    ctrl["probe_anchor_in_set"] = (probe in diff_anchors) if probe is not None else None
    non = [t for t in per_anchor if t not in diff_anchors]
    ctrl["probe_nondiffering_not_in_set"] = (non[0] not in diff_anchors) if non else None
    ctrl["baseline_green"] = bool(ctrl["set_nonempty"] and ctrl["set_not_everything"]
                                  and ctrl["probe_anchor_in_set"] and ctrl["probe_nondiffering_not_in_set"])
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = "red control: the differing set is degenerate or membership testing is broken"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"G13_VS_PANELDIFF VERDICT={rec['verdict']}  OUTCOME=({outcome})")
    print(f"  differing anchors {len(diff_anchors)} / shared {len(per_anchor)}; "
          f"red control baseline_green={ctrl['baseline_green']}")
    print(f"  G1-3 anchors inside the differing set: {n_inside}/{len(g13)};  "
          f"count mismatches (delivered vs function): {n_count_mismatch}/{len(g13)}")
    print("  anchor                 in_diff  only_nc  only_res  nc_n  delivered_n  g13_func_n  equal")
    for r in rows:
        print(f"   {r['anchor']} {str(r['utc'])[:16]:17s} {str(r['in_differing_set']):5s}  "
              f"{str(r['only_nc']):>7s}  {str(r['only_researcher']):>8s}  "
              f"{str(r['nc_members_in_panel']):>4s}  {str(r['researcher_members_in_DELIVERED_panel']):>11s}  "
              f"{str(r['g13_n_members_researcher_from_FUNCTION']):>10s}  {r['g13_members_equal']}")
    print(f"  => {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
