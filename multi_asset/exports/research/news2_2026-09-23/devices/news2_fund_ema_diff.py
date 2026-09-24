#!/usr/bin/env python3
"""news2_fund_ema_diff.py -- fund_ema is the ONLY feature column that differs inside the criterion window.

Context that makes this the priority: per-year, every rank column and every value column of X82 is
bitwise identical in 2023 and 2024; only fund_ema differs, and its disagreement GROWS with time
(2023 3.6% of cells, 2024 6.5%, 2025 11.4%, 2026 21.8%). 98% of the NEW<->NC gap lives pre-2026, so
fund_ema is the only feature-side candidate left there.

The researcher's own meta states the funding contract: "official interval priority, EMA(normalized 8h
rate), half life 3d, 12h freshness, unknown interval resets state". Every clause in that sentence is a
STATE machine, so a single disagreement about an interval can persist and compound -- which is the
shape a growing disagreement would have.

WHAT THIS MEASURES: where and how much fund_ema differs, and whether the differing cells coincide with
cells where the two sides disagree about the funding INTERVAL. Interval is available on both sides
(NC: iv_v in NC_FEATURES; researcher: iv in funding_state.npz), so this is a direct test, not a story.

NOT JUDGED (lead 2026-09-24): which side is correct. Contract question.
NOT MEASURED: whether the fund_ema difference explains any part of the King P difference. Coincidence
of two differences is not attribution; that needs the counterfactual.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)
SCALE = 1024


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher-panel", required=True)
    ap.add_argument("--researcher-funding", required=True)
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--col-name", default="fund_ema")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "WHERE_AND_HOW_MUCH_NOT_WHICH_SIDE_IS_RIGHT",
           "researcher_funding_contract": ("official interval priority, EMA(normalized 8h rate), "
                                           "half life 3d, 12h freshness, unknown interval resets state"),
           "inputs": {}}
    for k, p in (("researcher_panel", a.researcher_panel), ("researcher_funding", a.researcher_funding),
                 ("nc_features", a.nc_features)):
        rec["inputs"][k] = {"path": p, "bytes": os.path.getsize(p)}

    R = np.load(a.researcher_panel, allow_pickle=False)
    F = np.load(a.researcher_funding, allow_pickle=False)
    N = np.load(a.nc_features, allow_pickle=False)

    names = [str(x) for x in R["names"]]
    if a.col_name not in names:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"{a.col_name} not in researcher names"
        json.dump(rec, open(a.out, "w"), indent=2); print("FUND_EMA VERDICT=UNAVAILABLE"); return 2
    j = names.index(a.col_name)
    rec["column_index"] = j

    f_ts = F["E_ts"].astype(np.int64)
    r_ts = f_ts[R["pair_a"].astype(np.int64)]
    ps = R["pair_s"].astype(np.int64)
    n_anch = N["anchors"].astype(np.int64); n_off = N["off"].astype(np.int64); n_m = N["m"].astype(np.int64)
    n_rep = np.repeat(n_anch, np.diff(n_off))
    k_r = r_ts * SCALE + ps
    k_n = n_rep * SCALE + n_m
    common, ir, inn = np.intersect1d(k_r, k_n, assume_unique=True, return_indices=True)
    rec["common_pairs"] = int(common.size)

    x = np.asarray(R["X"])[ir, j].astype(np.float64)
    y = np.asarray(N["X82"])[inn, j].astype(np.float64)
    anch = (common // SCALE).astype(np.int64)
    sym = (common % SCALE).astype(np.int64)
    yr = np.array([datetime.datetime.utcfromtimestamp(int(t)).year for t in anch])

    fx, fy = np.isfinite(x), np.isfinite(y)
    eq = (x == y) | (~fx & ~fy)
    both = fx & fy
    diff = (~eq) & both

    # interval channel on both sides, aligned to the same pairs
    iv_res = np.asarray(F["iv"], np.float64)
    f_pos = {int(t): i for i, t in enumerate(f_ts)}
    ivr = np.array([iv_res[f_pos[int(t)], int(s)] if int(t) in f_pos else np.nan
                    for t, s in zip(anch, sym)], np.float64)
    ivn = None
    if "iv_v" in N.files:
        ivn_all = np.asarray(N["iv_v"], np.float64)
        ivn = ivn_all[inn] if ivn_all.ndim == 1 else None
    rec["nc_iv_available"] = ivn is not None

    per_year = {}
    for Y in sorted(set(yr.tolist())):
        s = yr == Y
        d = diff & s
        e = {"n_pairs": int(s.sum()), "n_differing": int(d.sum()),
             "frac_differing": float(d.sum() / max(1, s.sum())),
             "nan_pattern_mismatch": int(((fx ^ fy) & s).sum())}
        if d.any():
            ad = np.abs(x[d] - y[d])
            den = np.abs(y[d])
            e["abs_diff"] = {"median": float(np.median(ad)), "p90": float(np.percentile(ad, 90)),
                             "max": float(ad.max())}
            e["rel_diff_median"] = float(np.median(ad[den > 0] / den[den > 0])) if (den > 0).any() else None
            # interval cross-tab: do differing cells sit on non-8h intervals?
            e["researcher_interval_on_differing"] = {
                "frac_iv_8h": float(np.mean(ivr[d] == 8.0)) if np.isfinite(ivr[d]).any() else None,
                "frac_iv_not_8h": float(np.mean((ivr[d] != 8.0) & np.isfinite(ivr[d]))),
                "frac_iv_nan": float(np.mean(~np.isfinite(ivr[d])))}
            m_ = eq & both & s
            e["researcher_interval_on_matching"] = {
                "frac_iv_8h": float(np.mean(ivr[m_] == 8.0)) if m_.any() else None,
                "frac_iv_not_8h": float(np.mean((ivr[m_] != 8.0) & np.isfinite(ivr[m_]))) if m_.any() else None,
                "frac_iv_nan": float(np.mean(~np.isfinite(ivr[m_]))) if m_.any() else None}
            if ivn is not None:
                e["nc_vs_researcher_interval_differs_on_differing_cells"] = float(
                    np.mean(ivn[d] != ivr[d]))
                e["nc_vs_researcher_interval_differs_on_matching_cells"] = float(
                    np.mean(ivn[m_] != ivr[m_])) if m_.any() else None
            idx = np.flatnonzero(d)[:3]
            syms = N["symbols"]
            e["examples"] = [{"anchor": int(anch[i]),
                              "utc": datetime.datetime.utcfromtimestamp(int(anch[i])).strftime("%Y-%m-%dT%H:%MZ"),
                              "symbol": str(syms[int(sym[i])]),
                              "researcher_fund_ema": float(x[i]), "nc_fund_ema": float(y[i]),
                              "abs_diff": float(abs(x[i] - y[i])),
                              "researcher_iv": (float(ivr[i]) if np.isfinite(ivr[i]) else None),
                              "nc_iv": (float(ivn[i]) if ivn is not None and np.isfinite(ivn[i]) else None)}
                             for i in idx]
        per_year[str(Y)] = e
    rec["per_year"] = per_year

    # RED CONTROL: the equality expression must detect an injected change as exactly one cell, and the
    # interval cross-tab must have resolution (intervals must not be constant, or "concentrates on
    # non-8h" is unmeasurable).
    mut = y.copy()
    k0 = int(np.flatnonzero(fy)[0]) if fy.any() else 0
    mut[k0] += 1.0
    mut_n = int((~((y == mut) | (~fy & ~np.isfinite(mut)))).sum())
    iv_vals = np.unique(ivr[np.isfinite(ivr)])
    ctrl = {"mutation_n_differing": mut_n, "mutation_detected": mut_n == 1,
            "distinct_researcher_intervals": [float(v) for v in iv_vals[:10]],
            "interval_has_resolution": bool(iv_vals.size > 1)}
    ctrl["baseline_green"] = ctrl["mutation_detected"] and ctrl["interval_has_resolution"]
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = "red control: mutation not detected, or intervals are constant (no resolution)"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"FUND_EMA VERDICT={rec['verdict']} col={j} common_pairs={common.size}")
    print(f"  red control: mutation_detected={ctrl['mutation_detected']} "
          f"interval_resolution={ctrl['interval_has_resolution']} intervals={ctrl['distinct_researcher_intervals']}")
    print(f"  nc_iv_available={rec['nc_iv_available']}")
    for Y, e in per_year.items():
        if not e["n_differing"]:
            print(f"   {Y}  n={e['n_pairs']:7d}  differing 0"); continue
        ad = e["abs_diff"]; ri = e["researcher_interval_on_differing"]; rm = e["researcher_interval_on_matching"]
        print(f"   {Y}  n={e['n_pairs']:7d}  differing {e['n_differing']:7d} ({100*e['frac_differing']:5.2f}%)  "
              f"|d| med={ad['median']:.6f} p90={ad['p90']:.6f} max={ad['max']:.4f}")
        print(f"         iv on DIFFERING: 8h={ri['frac_iv_8h']}  not8h={ri['frac_iv_not_8h']:.4f}  nan={ri['frac_iv_nan']:.4f}")
        print(f"         iv on MATCHING : 8h={rm['frac_iv_8h']}  not8h={rm['frac_iv_not_8h']}  nan={rm['frac_iv_nan']}")
        if "nc_vs_researcher_interval_differs_on_differing_cells" in e:
            print(f"         NC vs RES interval differs: on differing {e['nc_vs_researcher_interval_differs_on_differing_cells']:.4f}  "
                  f"on matching {e['nc_vs_researcher_interval_differs_on_matching_cells']}")
        for ex in e["examples"]:
            print(f"         e.g. {ex['utc']} {ex['symbol']:12s} res={ex['researcher_fund_ema']:+.8f} "
                  f"nc={ex['nc_fund_ema']:+.8f} |d|={ex['abs_diff']:.8f} iv_res={ex['researcher_iv']} iv_nc={ex['nc_iv']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
