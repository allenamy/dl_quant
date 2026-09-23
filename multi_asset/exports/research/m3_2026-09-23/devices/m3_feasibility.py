#!/usr/bin/env python3
"""m3_feasibility.py — the three feasibility rows of prereg §1 (E-0923-C acceptance line), measured BEFORE any M3 NAV:
  (a) resolution: the daily-beta standard error on the BASE mean path over MAIN (classical OLS and Newey–West lag 5; m3_rules.ols), next to
      the prereg's rough 0.03 = (σ_book/σ_BTC)/√n recomputed with the measured σ's; resolution = band half-width 0.10 / SE;
  (b) delivery: R3 on the flat book (m3_exec_path.py output; m3_rules.r3), MAIN (gate) and AUX (report);
  (c) the phenomenon in the window: the base's ex-ante EXECUTED-book beta in MAIN — flat book (m3_exec_path) and in-path from the zero-hedge
      control's sidecar (seed 0: bitwise the base path), with the published / pre-reshape beta and the executed net alongside; plus the
      base's realised daily beta (= the slope in (a)).
Inputs are base paths (Stage 1 / certified), the flat-book npz and the control sidecar — no M3 overlay path is read.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_feasibility.py PATH,HOME,LC_CTYPE <out.json>
         <label>=<base_dir>,<exec_path_npz>,<control_sidecar_seed0_npz> [...]
"""
import os, sys, json, time, math
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m3_rules as RU
import m3_common as CM
import m3_hook as H

outp = sys.argv[2]
OUT = {"device": "m3_feasibility.py", "self_sha256": CM.sha(os.path.abspath(__file__)), "rules_sha256": CM.sha(os.path.join(HERE, "m3_rules.py")),
       "common_sha256": CM.sha(os.path.join(HERE, "m3_common.py")), "pins": CM.pins_ok(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bases": {}}
cn = None
for arg in sys.argv[3:]:
    label, rest = arg.split("=", 1); bdir, ep, sc0 = rest.split(",")
    o = {"inputs": {"base_dir": bdir, "exec_path_npz": [ep, CM.sha(ep)], "control_sidecar_seed0": [sc0, CM.sha(sc0)]}}
    B = CM.load_dir(bdir); o["inputs"]["base_files_sha256"] = B["file_sha256"]
    bmap = CM.bmap_for(B["mean"])
    a0, a1 = RU.MAIN
    days, rd, rb = CM.daily_series(B["mean"], a0, a1, bmap)
    ol = RU.ols(rd, rb)
    rough = (rd.std(ddof=1) / rb.std(ddof=1)) / math.sqrt(len(rd))
    per_path = np.array([RU.ols(RU.complete_days(p["A"], p["r"], a0, a1)[1], rb)["slope"] for p in B["paths"]])
    o["a_resolution"] = {"n_days": int(len(rd)), "first_day": time.strftime("%Y-%m-%d", time.gmtime(int(days[0]))), "last_day": time.strftime("%Y-%m-%d", time.gmtime(int(days[-1]))),
                         "base_realised_daily_beta": ol["slope"], "se_classical": ol["se_classical"], "se_newey_west_lag5": ol["se_newey_west_lag5"],
                         "prereg_rough_formula_with_measured_sigmas": float(rough), "sd_book_daily": float(rd.std(ddof=1)), "sd_btc_daily": float(rb.std(ddof=1)),
                         "band_half_width_over_se_nw": 0.10 / ol["se_newey_west_lag5"], "band_half_width_over_se_classical": 0.10 / ol["se_classical"],
                         "per_path_slope_sd (fill noise, not sampling error)": float(per_path.std(ddof=1)), "per_path_slope_range": [float(per_path.min()), float(per_path.max())]}
    Z = np.load(ep); w = Z["window"]; r = Z["reached"].astype(bool)
    cause_names = {v: k for k, v in H.CAUSE.items()}
    ob = {}
    for k, nm in enumerate(RU.WINDOWS):
        m = (w == k) & r
        ob[nm] = {"R3": RU.r3(Z["intended_gross_units"][m], Z["move_plan"][m]), "R3_on_target_before_plan": RU.r3(Z["intended_gross_units"][m], Z["move_target"][m]),
                  "published_anchors": int(np.sum(w == k)), "reached": int(m.sum()),
                  "cause_counts": {cause_names[int(c)]: int(np.sum(Z["cause_c"][m] == c)) for c in np.unique(Z["cause_c"][m])}}
    o["b_delivery_flat_book"] = ob
    mm = (w == 0) & r
    S = np.load(sc0); A = S["A"].astype(np.int64); inm = (A >= a0) & (A <= a1)
    fin = inm & np.isfinite(S["beta_exec"])
    if str(S["mode"]) != "control": raise RU.Empty("sidecar is not the control arm")
    o["c_phenomenon"] = {"flat_book_MAIN": {"beta_exec": RU.dist(Z["beta_exec_c"][mm]), "beta_pre_published": RU.dist(Z["beta_pre_c"][mm]),
                                            "net_exec": RU.dist(Z["net_exec_c"][mm]), "beta_exec_minus_beta_pre": RU.dist(Z["beta_exec_c"][mm] - Z["beta_pre_c"][mm])},
                         "in_path_control_seed0_MAIN": {"trading_anchors": int(inm.sum()), "empty_target_anchors": int(np.sum(inm & ~np.isfinite(S["beta_exec"]))),
                                                        "beta_exec": RU.dist(S["beta_exec"][fin]), "beta_pre_published": RU.dist(S["beta_pre"][fin]),
                                                        "net_exec": RU.dist(S["net_exec"][fin]), "gross_exec": RU.dist(S["gross_exec"][fin]),
                                                        "intended_hedge_over_gs": RU.dist(S["add_intended"][fin] / S["gs"][fin]),
                                                        "cause_counts_if_overlay": {cause_names[int(c)]: int(np.sum(S["cause"][inm] == c)) for c in np.unique(S["cause"][inm])}},
                         "base_realised_daily_beta_MAIN": ol["slope"]}
    OUT["bases"][label] = o
    print("FEAS", label, json.dumps({"se_nw": ol["se_newey_west_lag5"], "se_cl": ol["se_classical"], "beta_real": ol["slope"],
                                     "R3_MAIN": ob[list(RU.WINDOWS)[0]]["R3"]["pass"], "D": ob[list(RU.WINDOWS)[0]]["R3"]["D_delivered_share"],
                                     "beta_exec_flat_mean": o["c_phenomenon"]["flat_book_MAIN"]["beta_exec"]["mean"],
                                     "beta_exec_path_mean": o["c_phenomenon"]["in_path_control_seed0_MAIN"]["beta_exec"]["mean"]}), flush=True)
OUT["VERDICT"] = "DONE"
json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=float); os.replace(outp + ".tmp", outp)
print("M3_FEASIBILITY VERDICT=DONE out_sha256=" + CM.sha(outp), flush=True)
