#!/usr/bin/env python3
"""news2_feature_panel_diff.py -- did NC reproduce the researcher's King input panel, column by column?

Pre-registration: docs/PREREG_feature_panel_diff_2026-09-24.md (committed 3f02ab0f0, BEFORE any number
here). This is a DEPLOYMENT-CORRECTNESS check, not gap attribution -- lead: "和缺口大小无关".

PANEL CHOICE. Lead wrote "the X78 item"; the pod manifest has no X78 panel, and the researcher's own
KING_TRAIN_RECEIPT.json records King's inputs as dlw_targets.npz + dlw_fea82.npz. King eats X82. This
device compares X82 (and X89 if asked). NC's NC_FEATURES.npz does carry an X78 key, but the researcher
delivered no X78 panel, so X78 is a NAMED NON-MEASUREMENT, not covered by the X82 result.

ALIGNMENT. Row counts differ (2,785,890 vs 2,785,754), so rows are NOT comparable by position. The unit
is the (anchor timestamp, symbol index) PAIR, encoded as one int64 key. Pairs present on only one side
are counted and reported separately, never averaged into an agreement rate.

NaN POLICY (pre-registered): NaN is not turned into 0. "Both NaN" counts as equal; a position where the
two sides disagree about NaN-ness is counted in its own column and never silently compared.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.
"""
import argparse, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)
EPS = 1e-12


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher-panel", required=True)
    ap.add_argument("--researcher-axis", required=True, help="npz carrying the researcher E_ts axis")
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--nc-key", default="X82")
    ap.add_argument("--label", default="X82")
    ap.add_argument("--hash-inputs", action="store_true", help="sha the (multi-GB) inputs too")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "label": a.label, "nc_key": a.nc_key,
           "prereg": "docs/PREREG_feature_panel_diff_2026-09-24.md @ 3f02ab0f0",
           "status": "DEPLOYMENT_CORRECTNESS_NOT_GAP_ATTRIBUTION",
           "panel_choice_note": ("lead said 'X78'; the researcher's KING_TRAIN_RECEIPT.json records "
                                 "King's input as dlw_fea82.npz, so X82 is the panel King eats. "
                                 "X78 is undelivered by the researcher => named non-measurement."),
           "inputs": {}}
    for k, p in (("researcher_panel", a.researcher_panel), ("researcher_axis", a.researcher_axis),
                 ("nc_features", a.nc_features)):
        rec["inputs"][k] = {"path": p, "bytes": os.path.getsize(p)}
        if a.hash_inputs:
            rec["inputs"][k]["sha256"] = sha(p)

    R = np.load(a.researcher_panel, allow_pickle=False)
    AX = np.load(a.researcher_axis, allow_pickle=False)
    N = np.load(a.nc_features, allow_pickle=False)

    if a.nc_key not in N.files:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"NC panel has no key {a.nc_key}"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE"); return 2

    r_sym, n_sym = AX["symbols"], N["symbols"]
    same_axis = r_sym.shape == n_sym.shape and bool((r_sym == n_sym).all())
    rec["symbol_axis_identical"] = same_axis
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "symbol axes differ; a by-index pairing would compare different names"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE axes"); return 2

    r_ts = AX["E_ts"].astype(np.int64)
    pa, ps = R["pair_a"].astype(np.int64), R["pair_s"].astype(np.int64)
    if int(pa.max()) >= r_ts.size:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = f"pair_a max {int(pa.max())} exceeds the supplied axis length {r_ts.size}"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE axis len"); return 2

    n_anch, n_off, n_m = N["anchors"].astype(np.int64), N["off"].astype(np.int64), N["m"].astype(np.int64)
    counts = np.diff(n_off)
    n_ts_rep = np.repeat(n_anch, counts)
    if n_ts_rep.size != n_m.size:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = f"NC off/m inconsistent: repeat gives {n_ts_rep.size}, m has {n_m.size}"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE off/m"); return 2

    SCALE = 1024  # symbol index < 829 < 1024
    k_r = r_ts[pa] * SCALE + ps
    k_n = n_ts_rep * SCALE + n_m
    # np.intersect1d(return_indices=True) returns only the FIRST occurrence of a duplicated key, so a
    # duplicated (anchor, symbol) pair would silently drop rows and pair the wrong ones. Assert it.
    dup_r = int(k_r.size - np.unique(k_r).size)
    dup_n = int(k_n.size - np.unique(k_n).size)
    rec["duplicate_pairs"] = {"researcher": dup_r, "nc": dup_n}
    if dup_r or dup_n:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = (f"duplicate (anchor, symbol) pairs: researcher {dup_r}, nc {dup_n}; the pairing "
                      f"would be ambiguous and intersect1d would keep only the first")
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE dup"); return 2
    common, ir, inn = np.intersect1d(k_r, k_n, assume_unique=True, return_indices=True)
    rec["pairs"] = {"researcher_rows": int(k_r.size), "nc_rows": int(k_n.size),
                    "common_pairs": int(common.size),
                    "only_researcher": int(k_r.size - common.size),
                    "only_nc": int(k_n.size - common.size),
                    "row_count_difference": int(k_r.size) - int(k_n.size),
                    "note": "pairs present on one side only are reported, never averaged into agreement"}

    if common.size == 0:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "no common (anchor, symbol) pair"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE"); return 2

    XR, XN = np.asarray(R["X"]), np.asarray(N[a.nc_key])
    names = [str(x) for x in R["names"]] if "names" in R.files else None
    rec["column_names_source"] = ("researcher 'names' array; NC panel carries no column names, so NC "
                                  "columns are aligned BY POSITION -- that is an assumption, stated")
    if XR.shape[1] != XN.shape[1]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = f"column counts differ: researcher {XR.shape[1]} vs NC {XN.shape[1]}"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label} VERDICT=UNAVAILABLE ncol"); return 2

    A_ = XR[ir]
    B_ = XN[inn]
    del XR, XN

    cols, identical_cols, differing = [], 0, []
    for j in range(A_.shape[1]):
        x, y = A_[:, j].astype(np.float64), B_[:, j].astype(np.float64)
        fx, fy = np.isfinite(x), np.isfinite(y)
        both = fx & fy
        nan_mismatch = int((fx ^ fy).sum())
        eq = (x == y) | (~fx & ~fy)          # both-NaN counts as equal; NaN != NaN otherwise
        frac_eq = float(eq.mean())
        d = np.abs(x[both] - y[both]) if both.any() else np.zeros(0)
        den = np.abs(y[both]) if both.any() else np.zeros(0)
        zero_den = int((den == 0).sum())
        rel = d[den > 0] / (den[den > 0] + EPS) if den.size else np.zeros(0)
        e = {"col": j, "name": names[j] if names else None,
             "frac_bitwise_identical": frac_eq,
             "n_positions": int(x.size), "nan_pattern_mismatch": nan_mismatch,
             "max_abs_diff": float(d.max()) if d.size else None,
             "median_rel_diff": float(np.median(rel)) if rel.size else None,
             "zero_denominator_positions": zero_den,
             "zero_denominator_note": "counted, not dropped"}
        cols.append(e)
        if frac_eq == 1.0 and nan_mismatch == 0:
            identical_cols += 1
        else:
            differing.append({"col": j, "name": e["name"], "frac_bitwise_identical": frac_eq,
                              "max_abs_diff": e["max_abs_diff"],
                              "median_rel_diff": e["median_rel_diff"],
                              "nan_pattern_mismatch": nan_mismatch})
    rec["n_columns"] = A_.shape[1]
    rec["n_columns_bitwise_identical"] = identical_cols
    rec["differing_columns"] = differing
    rec["per_column"] = cols

    # RED CONTROL.
    # Cell 1 (baseline green) is the ALIGNMENT IDENTITY, not "a column equals itself" -- the latter is
    # true by construction (x == x, or both-NaN) and could never fail, which is not a control. This one
    # can fail: it asserts the two index vectors really select the same (anchor, symbol) keys.
    align_ok = bool(np.array_equal(k_r[ir], k_n[inn])) and bool(np.array_equal(k_r[ir], common))
    # Cell 2 (mutation): injecting exactly one changed position must be detected as exactly one.
    b0 = B_[:, 0].astype(np.float64)
    mut = b0.copy()
    k = int(np.flatnonzero(np.isfinite(mut))[0]) if np.isfinite(mut).any() else 0
    mut[k] += 1.0
    mut_ne = int((~((b0 == mut) | (~np.isfinite(b0) & ~np.isfinite(mut)))).sum())
    ctrl = {"alignment_identity_holds": align_ok,
            "mutation_n_differing_positions": mut_ne,
            "baseline_green": align_ok, "mutation_detected": mut_ne == 1,
            "why_not_self_comparison": ("a column compared with itself is equal by construction and "
                                        "cannot fail, so it is not a control")}
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: the alignment identity failed"
    elif not ctrl["mutation_detected"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"red control: injected 1 diff, detected {mut_ne}"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    p = rec["pairs"]
    print(f"{a.label} VERDICT={rec['verdict']}  columns identical {identical_cols}/{rec['n_columns']}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} (alignment identity) "
          f"mutation_detected={ctrl['mutation_detected']} (n={mut_ne})")
    print(f"  pairs: researcher {p['researcher_rows']}  nc {p['nc_rows']}  common {p['common_pairs']}  "
          f"only_res {p['only_researcher']}  only_nc {p['only_nc']}  rowdiff {p['row_count_difference']}")
    if differing:
        print(f"  DIFFERING COLUMNS ({len(differing)}):")
        for d in differing[:40]:
            print(f"   col {d['col']:3d} {str(d['name'])[:26]:26s} identical={d['frac_bitwise_identical']:.6f} "
                  f"max|d|={d['max_abs_diff']}  med_rel={d['median_rel_diff']}  nan_mm={d['nan_pattern_mismatch']}")
    else:
        print("  all columns bitwise identical on the common pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
