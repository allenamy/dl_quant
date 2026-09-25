#!/usr/bin/env python3
"""pnoise_readout.py -- the final readout of the perturbation-noise experiment (K=8 chains, n=7 samples).

Pre-registration: docs/PREREG_perturbation_noise_run_2026-09-24.md (41e5e8776) + the addendum.
Reads EVERY PNOISE_DBAR_r*.json receipt and re-derives everything from them. SUMMARY.tsv is read only
as a cross-check and is NOT the source of any number (lead 2026-09-24: "先实测核对每次的收据,
不要只抄 SUMMARY.tsv").

WHAT dbar_rs MEANS (lead's framing): dbar is computed against the archived NC cell, and NC *is*
random_state = 0, so dbar_rs = level_rs - level_0. The dispersion of the seven values therefore
estimates the between-model dispersion of this family, and their MEAN says whether the deployed model
(rs = 0) sits above or below its family.

rs = 0 is NOT a sample of the distribution: its dbar is 0 by construction (it is the baseline).
It is reported as a POSITION inside the distribution, never as a draw from it.
"""
import argparse, glob, hashlib, json, math, os, statistics, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def boot_ci(x, n_boot=20000, seed=(20260924, 1), pcts=(2.5, 97.5)):
    rng = np.random.default_rng(seed)
    a = np.asarray(x, float)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    means = a[idx].mean(1)
    return [float(np.percentile(means, p)) for p in pcts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipts-dir", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)),
           "argv": sys.argv[1:], "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_perturbation_noise_run_2026-09-24.md @ 41e5e8776 + addendum",
           "status": "DISPERSION_OF_ONE_PERTURBATION_KIND_NOT_A_SWITCH_RECOMMENDATION",
           "source_rule": "every number re-derived from the per-run receipts; SUMMARY.tsv cross-check only"}

    # ---- read every receipt ----
    runs, problems, caliber = {}, [], set()
    for p in sorted(glob.glob(os.path.join(a.receipts_dir, "PNOISE_DBAR_r*.json"))):
        d = json.load(open(p))
        r = int(str(d["random_state"]))
        if d.get("verdict") not in ("MEASURED",):
            problems.append({"receipt": p, "verdict": d.get("verdict")})
        cs = d.get("caliber_source", {})
        caliber.add((cs.get("news_stats_sha256"), cs.get("bt_tables_sha256"),
                     cs.get("bt_driver_lib_sha256"), cs.get("NPATH")))
        seg = d["dbar_vs_nc"]
        runs[r] = {"receipt": p, "receipt_sha256": sha(p), "verdict": d["verdict"],
                   "n_paths": d.get("n_paths"), "anchor_axis_identical": d.get("anchor_axis_identical"),
                   "pre2026": seg["pre2026"]["mean_bps_per_day"],
                   "y2026": seg["2026"]["mean_bps_per_day"],
                   "pre2026_days": seg["pre2026"]["n_days"], "y2026_days": seg["2026"]["n_days"],
                   "segments": {k: v.get("mean_bps_per_day") for k, v in seg.items() if "n_days" in v}}
        if r == 0:
            runs[r]["red_control"] = d.get("red_control")
    rec["n_receipts"] = len(runs)
    rec["receipts"] = runs
    rec["receipt_problems"] = problems
    rec["caliber_identical_across_runs"] = (len(caliber) == 1)
    rec["caliber_tuple"] = sorted(str(c) for c in caliber)

    # ---- cross-check against SUMMARY.tsv (not a source) ----
    xcheck = []
    if os.path.exists(a.summary):
        for line in open(a.summary):
            f = line.rstrip("\n").split("\t")
            if len(f) >= 4 and f[1] == "OK":
                r = int(f[0])
                ok_pre = abs(float(f[2]) - runs[r]["pre2026"]) < 5e-6
                ok_26 = abs(float(f[3]) - runs[r]["y2026"]) < 5e-6
                xcheck.append({"run": r, "pre2026_matches": ok_pre, "y2026_matches": ok_26})
    rec["summary_cross_check"] = xcheck
    rec["summary_cross_check_all_match"] = all(c["pre2026_matches"] and c["y2026_matches"] for c in xcheck)

    # ---- red control (rs = 0) ----
    r0 = runs.get(0, {})
    rec["red_control_rs0"] = {
        "all_segments": r0.get("segments"),
        "exactly_zero_everywhere": all(v == 0.0 for v in (r0.get("segments") or {}).values()),
        "from_receipt": r0.get("red_control")}

    QUOTED = {"pre2026": {"NEW_minus_NC_s42": 2.835, "NEW_minus_NC_s2027": 0.935},
              "y2026": {"measured_2026_dbar_s42": -0.367}}

    out = {}
    for key, label in (("pre2026", "pre-2026 criterion window"), ("y2026", "2026")):
        vals = [runs[r][key] for r in sorted(runs) if r != 0]
        n = len(vals)
        mean = statistics.fmean(vals)
        sd = statistics.stdev(vals) if n > 1 else float("nan")
        se = sd / math.sqrt(n) if n > 1 else float("nan")
        t = mean / se if se and se == se and se != 0 else float("nan")
        ci = boot_ci(vals)
        # rs = 0 position: its level is 0 by construction
        levels = sorted(vals + [0.0], reverse=True)
        rank0 = levels.index(0.0) + 1
        e = {
            "segment": label, "n_samples": n, "samples": vals,
            "mean": mean, "sd_ddof1": sd, "min": min(vals), "max": max(vals),
            "range": max(vals) - min(vals), "median": statistics.median(vals),
            "sd_relative_standard_error": 1.0 / math.sqrt(2 * (n - 1)),
            "rs0": {
                "level_by_construction": 0.0,
                "z_of_rs0_in_distribution": (0.0 - mean) / sd if sd == sd and sd else None,
                "rank_among_all_8_models_1_is_best": rank0,
                "is_best_of_8": rank0 == 1,
                "prior_prob_rs0_is_best_of_8": 1.0 / 8,
                "note": ("rs=0 is NOT a draw from the distribution -- its dbar is 0 by construction. "
                         "It is reported as a position only."),
                "n_samples_below_rs0": sum(1 for v in vals if v < 0),
                "n_samples_above_rs0": sum(1 for v in vals if v > 0)},
            "family_mean_vs_rs0": {
                "mean_dbar": mean,
                "interpretation": ("negative mean => the family averages BELOW the deployed model "
                                   "(rs=0), i.e. the deployed model's backtest is optimistic relative "
                                   "to its family's expectation"),
                "t_stat_vs_zero": t, "se_of_mean": se,
                "bootstrap_ci95_of_mean": ci,
                "ci_excludes_zero": (ci[0] < 0 and ci[1] < 0) or (ci[0] > 0 and ci[1] > 0)},
        }
        # quoted values placed in the distribution
        placed = {}
        for nm, q in QUOTED[key].items():
            below = sum(1 for v in vals if v < q)
            placed[nm] = {"value": q,
                          "z": (q - mean) / sd if sd == sd and sd else None,
                          "empirical_n_below": below, "empirical_of_n": n,
                          "empirical_quantile": below / n,
                          "quantile_resolution": 1.0 / n,
                          "inside_observed_range": (min(vals) <= q <= max(vals))}
        e["quoted_values_placed"] = placed
        # power: seeds needed to resolve 1 bps/day
        Z_A, Z_B = 1.959963985, 0.841621234      # alpha=0.05 two-sided, power=0.80
        for delta in (1.0, 2.835):
            k = f"n_seeds_to_resolve_{delta}_bps_per_day"
            e[k] = {
                "one_sample_n": math.ceil(((Z_A + Z_B) * sd / delta) ** 2) if sd == sd else None,
                "two_sample_n_per_arm": math.ceil(2 * ((Z_A + Z_B) * sd / delta) ** 2) if sd == sd else None,
                "assumes": "alpha=0.05 two-sided, power=0.80, sd as estimated here"}
        out[key] = e
    rec["readout"] = out

    # ---- addendum 2: the frozen criterion expressed in sigmas ----
    sd_pre = out["pre2026"]["sd_ddof1"]
    rec["criteria_in_sigmas"] = {
        "sigma_pre2026_bps_per_day": sd_pre,
        "B1_threshold_is_point_estimate_ge_0": {
            "threshold_bps_per_day": 0.0,
            "distance_of_threshold_from_family_mean_in_sigma": (0.0 - out["pre2026"]["mean"]) / sd_pre,
            "note": ("B1 asks a single seed's point estimate to clear 0. One perturbation of this family "
                     "moves the point estimate by ~1 sigma, so the criterion is being applied at a "
                     "resolution comparable to the noise it does not model.")},
        "NEW_minus_NC_s42_in_sigma": (2.835 - out["pre2026"]["mean"]) / sd_pre,
        "NEW_minus_NC_s2027_in_sigma": (0.935 - out["pre2026"]["mean"]) / sd_pre,
    }

    json.dump(rec, open(a.out, "w"), indent=2)

    # ---- print ----
    print(f"PNOISE_READOUT receipts={len(runs)} problems={len(problems)} "
          f"caliber_identical={rec['caliber_identical_across_runs']} "
          f"summary_xcheck_all_match={rec['summary_cross_check_all_match']}")
    rc0 = rec["red_control_rs0"]
    print(f"  RED CONTROL rs=0 exactly zero in every segment: {rc0['exactly_zero_everywhere']}")
    for key in ("pre2026", "y2026"):
        e = out[key]
        print(f"\n  === {e['segment']} (n={e['n_samples']}) ===")
        print("   samples: " + "  ".join(f"{v:+.4f}" for v in e["samples"]))
        print(f"   mean {e['mean']:+.4f}  sd {e['sd_ddof1']:.4f}  range {e['range']:.4f} "
              f"[{e['min']:+.4f}, {e['max']:+.4f}]  median {e['median']:+.4f}")
        print(f"   sd relative SE {100*e['sd_relative_standard_error']:.1f}%")
        z = e["rs0"]
        print(f"   rs=0: z={z['z_of_rs0_in_distribution']:+.3f}  rank {z['rank_among_all_8_models_1_is_best']}/8 "
              f"(best={z['is_best_of_8']}, prior 1/8)  below/above: "
              f"{z['n_samples_below_rs0']}/{z['n_samples_above_rs0']}")
        fm = e["family_mean_vs_rs0"]
        print(f"   family mean vs rs=0: {fm['mean_dbar']:+.4f}  t={fm['t_stat_vs_zero']:+.3f}  "
              f"boot95 [{fm['bootstrap_ci95_of_mean'][0]:+.4f}, {fm['bootstrap_ci95_of_mean'][1]:+.4f}]  "
              f"excludes0={fm['ci_excludes_zero']}")
        for nm, q in e["quoted_values_placed"].items():
            print(f"   {nm} = {q['value']:+.3f}: z={q['z']:+.3f}  empirical {q['empirical_n_below']}/{q['empirical_of_n']} "
                  f"below (res {q['quantile_resolution']:.3f})  inside_range={q['inside_observed_range']}")
        for delta in ("1.0", "2.835"):
            k = f"n_seeds_to_resolve_{delta}_bps_per_day"
            print(f"   resolve {delta} bps/day: one-sample n={e[k]['one_sample_n']}, "
                  f"two-sample n/arm={e[k]['two_sample_n_per_arm']}")
    c = rec["criteria_in_sigmas"]
    print(f"\n  sigma(pre2026) = {c['sigma_pre2026_bps_per_day']:.4f} bps/day")
    print(f"  B1 threshold 0 sits {c['B1_threshold_is_point_estimate_ge_0']['distance_of_threshold_from_family_mean_in_sigma']:+.3f} sigma from the family mean")
    print(f"  2.835 = {c['NEW_minus_NC_s42_in_sigma']:+.3f} sigma ; 0.935 = {c['NEW_minus_NC_s2027_in_sigma']:+.3f} sigma")
    return 0


if __name__ == "__main__":
    sys.exit(main())
