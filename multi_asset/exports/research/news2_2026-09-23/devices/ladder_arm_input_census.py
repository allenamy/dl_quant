#!/usr/bin/env python3
"""ladder_arm_input_census.py -- the check that closes my detector's blind spot, for EVERY arm.

WHY THIS EXISTS. My artifact detector was "compare each arm's refusal-reason vocabulary with the two
ends; a novel reason means the swap manufactured a defect". It caught KZ_res / KZWL_res / F10_res /
MEM_res. It passed FUND_res as clean -- no novel reason, and zero NaN/inf in its combo weights. But
ZFD, which FUND_res swaps in, is non-finite on 43,233 MEMBER cells over 1,715 anchors -- MORE anchors
than the KZ footprint. combo tolerates a non-finite funding rank silently: it neither refuses the
anchor nor emits NaN. So no reason vocabulary could ever have shown it.

  The reason-vocabulary detector is NECESSARY but NOT SUFFICIENT: it only sees degradation the
  consumer complains about. Using it to certify silence is using an instrument that only rings when
  something rings.

So this device does not take a list of arrays I remembered to worry about. It reads each arm's OWN
receipt, takes the arrays that arm actually substituted, and censuses every one of them. A new arm
added tomorrow is covered without editing this file -- which is the point: my fixes have been
instance-shaped before, and the acceptance line for this one is "does it catch the arm I have not
written yet".

Per-symbol arrays are censused on MEMBER cells in the use window (what combo reads). Arrays that are
not per-symbol (WL is (n,3) seats, ready is (n,)) are censused as non-finite entries inside vs outside
the use window, because combo RAISES on non-finite seats rather than refusing an anchor
(combo_target.py:24).
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


USE_FROM = 1672531200

# where each substitutable array comes from on NEW's side, read off continuous_combo.py:49/:61/:69/:78
SRC = {"KZ": ("legs", "KZ"), "ZFD": ("legs", "ZFD"), "WL": ("legs", "WL"), "ready": ("legs", "ready"),
       "P": ("f10", "P"), "RN8": ("funding", "rn8"), "QV": ("targets", "qvk"),
       "members": ("targets", "members"), "legal": ("funding", "legal")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipts", required=True)
    ap.add_argument("--arms", required=True, help="comma-separated arm names")
    ap.add_argument("--features", required=True)
    ap.add_argument("--new-legs", required=True)
    ap.add_argument("--new-f10", required=True)
    ap.add_argument("--new-funding", required=True)
    ap.add_argument("--new-targets", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": ("docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f "
                      "(sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03), revision 1"),
           "why": ("closes the blind spot in the reason-vocabulary detector: combo tolerates a non-finite "
                   "funding rank silently, so a silently degraded arm passes that detector. Arrays are "
                   "taken from each arm's OWN receipt so a future arm is covered without editing this file."),
           "coverage_rule": "per-symbol arrays -> member cells in the use window; others -> in/out of window entries"}

    F = np.load(a.features, allow_pickle=False)
    anchors = F["anchors"].astype(np.int64); syms = F["symbols"]; off = F["off"]; mm = F["m"]
    Z = {"legs": np.load(a.new_legs, allow_pickle=False),
         "f10": np.load(a.new_f10, allow_pickle=False),
         "funding": np.load(a.new_funding, allow_pickle=False),
         "targets": np.load(a.new_targets, allow_pickle=True)}
    pos = {int(t): i for i, t in enumerate(Z["legs"]["E_ts"].astype(np.int64))}
    rows = np.array([pos.get(int(t), -1) for t in anchors])
    members_nc = [mm[off[i]:off[i + 1]].astype(np.int64) for i in range(len(anchors))]
    # NEW's member set on NC's anchor axis, for arms that substitute members
    _nm_new = list(Z["targets"]["members"])
    members_new = [(np.asarray(_nm_new[rows[i]], np.int64) if rows[i] >= 0 else members_nc[i])
                   for i in range(len(anchors))]
    yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in anchors])

    def census(name, members, member_source, repaired):
        where, key = SRC[name]
        A = Z[where][key]
        if key == "members":
            return {"array": f"{where}[{key}]", "shape": "ragged object array",
                    "census": "not applicable -- member lists are index sets, not values; see the "
                              "member-set comparison in the MEM_res reporting instead"}
        A = np.asarray(A, np.float64)
        per_symbol = A.ndim == 2 and A.shape[1] == len(syms)
        d = {"array": f"{where}[{key}]", "shape": str(A.shape), "per_symbol": bool(per_symbol),
             "member_set_used": member_source,
             "repaired_by_ncfill": bool(repaired)}
        if per_symbol:
            cells = anch = 0
            per_year = {}
            for i in range(len(anchors)):
                if anchors[i] < USE_FROM or rows[i] < 0:
                    continue
                nb = int((~np.isfinite(A[rows[i]][members[i]])).sum())
                cells += nb
                if nb:
                    anch += 1
                    per_year[str(int(yr[i]))] = per_year.get(str(int(yr[i])), 0) + 1
            d.update({"non_finite_member_cells_in_use_window": cells,
                      "anchors_affected": anch, "anchors_affected_per_year": per_year})
            d["silent"] = bool(cells > 0 and not repaired)
            if repaired:
                d["repair_note"] = ("lead's path-2 fill replaced these cells with NC values; "
                                    "the count above describes the INPUT before repair")
        else:
            nf = ~np.isfinite(A)
            inw = np.zeros(A.shape[0], bool)
            for i in range(len(anchors)):
                if rows[i] >= 0 and anchors[i] >= USE_FROM:
                    inw[rows[i]] = True
            d.update({"non_finite_entries_inside_use_window": int(nf[inw].sum()),
                      "non_finite_entries_outside_use_window": int(nf[~inw].sum())})
            d["silent"] = bool(int(nf[inw].sum()) > 0 and not repaired)
        return d

    out = {}
    for arm in a.arms.split(","):
        arm = arm.strip()
        p = os.path.join(a.receipts, f"LADDER_{arm}.json")
        if not os.path.exists(p):
            out[arm] = {"status": "NO_RECEIPT", "path": p}
            continue
        r = json.load(open(p))
        # the arm's OWN record of what it substituted -- not a list I maintain here
        subs = [x.replace("(ncfill)", "").replace("(negated)", "").replace("(funding_state)", "")
                for x in r.get("substituted", [])]
        subs = [x for x in subs if x in SRC]
        ends = set()
        for e in ("none", "all_new"):
            pe = os.path.join(a.receipts, f"LADDER_{e}.json")
            if os.path.exists(pe):
                re_ = json.load(open(pe))
                for pol in re_["policies"]:
                    ends |= set(re_["policies"][pol]["reasons"])
        novel = {}
        for pol in r["policies"]:
            nv = {k: v for k, v in r["policies"][pol]["reasons"].items() if k not in ends}
            if nv:
                novel[pol] = nv
        swaps_members = any(x == "members" for x in subs)
        mem = members_new if swaps_members else members_nc
        msrc = ("NEW (this arm substitutes members, so it reads NEW's member set)" if swaps_members
                else "NC (this arm keeps NC's members)")
        filled = r.get("cells_filled_with_nc_because_new_had_no_score", {}) or {}
        arrays = {nm: census(nm, mem, msrc, nm in filled) for nm in subs}
        silent = [nm for nm, d in arrays.items() if d.get("silent")]
        out[arm] = {"substituted": r.get("substituted", []), "arrays_censused": arrays,
                    "novel_refusal_reasons": novel or None,
                    "loud_degradation": bool(novel),
                    "silent_degradation_arrays": silent,
                    "member_set_used": msrc,
                    "arrays_repaired_by_ncfill": sorted(filled.keys()),
                    "verdict": ("CLEAN" if not novel and not silent else
                                "LOUD_AND_SILENT" if novel and silent else
                                "LOUD_ONLY" if novel else "SILENT_ONLY")}
    rec["arms"] = out
    rec["headline"] = {arm: d.get("verdict", d.get("status")) for arm, d in out.items()}
    rec["limits"] = ["a CLEAN verdict here means no non-finite input on member cells and no novel refusal "
                     "reason; it does not certify the arm is a deployable combination -- no arm is",
                     "arms are NOT additive"]
    json.dump(rec, open(a.out, "w"), indent=2)

    print("LADDER ARM INPUT CENSUS")
    for arm, d in out.items():
        if "verdict" not in d:
            print(f"  {arm:20s} {d['status']}"); continue
        print(f"  {arm:20s} {d['verdict']:16s} loud={d['loud_degradation']} silent={d['silent_degradation_arrays']}"
              f"  members={'NEW' if 'NEW' in d['member_set_used'] else 'NC'}")
        for nm, c in d["arrays_censused"].items():
            if c.get("per_symbol"):
                tag = " [REPAIRED by ncfill]" if c.get("repaired_by_ncfill") else ""
                print(f"      {nm:8s} {c['shape']:14s} non-finite member cells={c['non_finite_member_cells_in_use_window']:7d}"
                      f"  anchors={c['anchors_affected']:5d}  per_year={c.get('anchors_affected_per_year')}{tag}")
            elif "non_finite_entries_inside_use_window" in c:
                print(f"      {nm:8s} {c['shape']:14s} non-finite entries in-window="
                      f"{c['non_finite_entries_inside_use_window']:7d}  out-of-window="
                      f"{c['non_finite_entries_outside_use_window']:7d}")
            else:
                print(f"      {nm:8s} {c.get('census')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
