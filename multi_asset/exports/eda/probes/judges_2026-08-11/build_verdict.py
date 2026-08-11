"""Assemble qim_final_verdict.json from the audit raw + fixed analysis. Run on server."""
import json, numpy as np

RAW = "multi_asset/exports/eda/qim_verdict_audit_raw.json"
OUT = "multi_asset/exports/eda/qim_final_verdict.json"
d = json.load(open(RAW))

years = ["2022", "2023", "2024", "2025", "2026"]
dyn = []
for y in years:
    v = d["multiyear"][y]; dc = v["decomp"]; nc = v["netcost"]
    dyn.append(dict(
        year=int(y), ens_resid_ic=v["ens_resid_ic"], ens_resid_ic_ir=v["ens_resid_ic_ir"],
        ens_raw_ic=v["ens_raw_ic"], member_per_hr=v["member_per_hr"], n_clean_ts=v["n_clean_ts"],
        total=dc["total"], static_shuffle=dc["static_shuffle"], static_mean=dc["static_mean"],
        dynamic=round(dc["total"] - dc["static_shuffle"], 4), dyn_share=round(dc["dyn_share"], 3),
        flag_low_dynamic=bool(dc["dyn_share"] < 0.5)))

nety = []
for y in years:
    nc = d["multiyear"][y]["netcost"]
    nety.append(dict(
        year=int(y), gross_sharpe_0cost=round(nc["gross_sharpe"], 2),
        breakeven_per_side_bps=round(nc["be_fullturn"], 2), turnover_per_period=round(nc["turnover"], 2),
        gross_bps_per_period=round(nc["gross_bps"], 2),
        netSharpe_maker0=round(nc["netSharpe_full_c0.0"], 2),
        netSharpe_taker2p3=round(nc["netSharpe_full_c2.3"], 2),
        netSharpe_taker5p0=round(nc["netSharpe_full_c5.0"], 2),
        netSharpe_taker9p5=round(nc["netSharpe_full_c9.5"], 2),
        decile_monotonicity=round(nc["decile_monotonicity"], 3), avg_breadth=round(nc["avg_breadth"], 0),
        go_maker0="GO", go_taker2p3=("GO" if nc["netSharpe_full_c2.3"] > 0 else "NO"),
        go_taker5p0=("GO" if nc["netSharpe_full_c5.0"] > 0 else "NO"),
        go_taker9p5=("GO" if nc["netSharpe_full_c9.5"] > 0 else "NO")))

mech = d["mechanism"]; seed = d["seed"]
seed_vals = [seed["wideA_qim"]["mean"], seed["wideA_qim_seed43"]["mean"], seed["wideA_qim_seed44"]["mean"]]

verdict = dict(
    title="QIM wide-universe factor — 0C final verdict",
    created="2026-07-12",
    auditor="0C",
    final_verdict="CONDITIONAL_GO",
    one_line=("QIM signal is GENUINE and net-cost-tradeable at maker/cheap-taker cost, but its "
              "headline edge is MIS-ATTRIBUTED: the ~2x lift is removing the orthogonality penalty "
              "(lam_orth=1->0), NOT the pinball head (which is neutral). Deploy the lever, re-label the crown."),
    reproduction=dict(
        method="independent recompute of honest z-mean ensemble resid-IC from fold_i_head_scores.npz + panel_ref.npz",
        my_per_year=[d["multiyear"][y]["ens_resid_ic"] for y in years],
        json_per_year=[0.0443, 0.064, 0.0697, 0.0807, 0.0774],
        bit_match=True, mean=0.0672,
        caliber="ensemble (z-score each of [imean,q50] then mean), NOT per-fold best-head; matches JSON exactly"),
    yearly_dynamic_static=dyn,
    dyn_share_mean=round(float(np.mean([r["dyn_share"] for r in dyn])), 3),
    yearly_netcost=nety,
    netcost_notes=("4h-rebalanced dollar-neutral rank-weighted L/S on RAW forward returns; "
                   "Sharpe annualized at per_yr=2190 (4h periods). High Sharpe magnitude is a "
                   "frequency x breadth x xsec-consistency artifact and assumes FRICTIONLESS fills / "
                   "no impact / no capacity / no short borrow. The honest tradeability gate is the "
                   "break-even per-side (bps). Cost tiers: maker~0, taker {2.3,5.0,9.5}. "
                   "Heavy-EMA (alpha=0.05) raises BE to 15-27bps but collapses Sharpe to ~2-3 because "
                   "dynamic-share ~0.9 signal does not tolerate holding -> report full-turnover as headline."),
    mechanism=dict(
        protocol="3-fold matched panel (md5 39f5cc4e), identical honest ensemble caliber",
        conformer_ref_Khead_orth1=mech["wideA_conformer_ref"],
        lamorth0_Khead_orth0=mech["wideA_lamorth0"],
        qim_pinball=mech["wideA_qim"],
        verdict=("Removing orthogonality penalty (conformer_ref 0.0327 -> lamorth0 0.0672) DOUBLES IC "
                 "in every fold (+105%). QIM head vs K-head-no-penalty (lamorth0 0.0672 -> qim 0.0689) "
                 "is FLAT (+0.0017, within seed noise, fold-by-fold mixed sign). CONCLUSION: the ~2x edge "
                 "is the orthogonality-penalty removal; the pinball head is NEUTRAL, not the alpha source."),
        dilution_factor=round(mech["wideA_lamorth0"]["mean"] / mech["wideA_conformer_ref"]["mean"], 2)),
    seed=dict(
        protocol="SAME-protocol 3-fold ensemble (corrects tasking's cross-protocol triple)",
        seed42=seed["wideA_qim"], seed43=seed["wideA_qim_seed43"], seed44=seed["wideA_qim_seed44"],
        mean=round(float(np.mean(seed_vals)), 4), std=round(float(np.std(seed_vals)), 4),
        min=min(seed_vals), max=max(seed_vals),
        cov=round(float(np.std(seed_vals) / np.mean(seed_vals)), 3),
        G2_gate="PASS (3 seeds all positive 0.065-0.078, sign-consistent per fold, CoV 7.5%, no collapse)"),
    anomaly_audit=dict(
        fold_boundaries=dict(status="CLEAN", detail=d["fold_boundary"],
                             note="expanding walk-forward, 9-day embargo gap val-end->test-start, zero train/test overlap; 4h label << 9d gap"),
        member_point_in_time=dict(status="CLEAN", corr_free="0 coins member-before-first-finite",
                                  distinct_monthly_sets=d["leak_audit"]["n_distinct_monthly_sets"],
                                  n_months=d["leak_audit"]["n_months"],
                                  universe_growth="62->110 (trailing-DVOL30 monthly refresh, no survivorship)"),
        residual_target_leak=dict(status="CLEAN", corr_YR_funding=d["leak_audit"]["corr_YR_funding"],
                                  note="per-ts cross-sectional OLS residual (beta fit only within same-t cross-section); no time leakage; YR orthogonal to funding"),
        ensemble_caliber=dict(status="HONEST", note="z-mean of heads, NOT best-head; reproduced bit-exact"),
        panel_ref_byte_identity=dict(status="VERIFIED",
                                     note="5yr QIM panel_ref md5=185d3b65 == 5yr xattn (identical); 3-fold runs (qim/seed43/seed44/lamorth0/conformer_ref) all md5=39f5cc4e (identical)"),
        too_good_pattern=dict(status="EXPLAINED",
                              note="5yr monotone rise 0.044->0.081 + IC-IR 16-29 explained by (a) expanding train window (2022 fold=1yr train, 2025 fold=4yr) (b) universe breadth 81->110 (c) IC-IR is PER-CROSS-SECTION t-stat over ~2000 ts/yr, NOT a Sharpe. All 6 leak checks pass.")),
    flags=[
        "MIS-ATTRIBUTION (material): headline credits 'QIM pinball head' but matched ablation shows the alpha is 'lam_orth=0'; QIM head is neutral vs plain K-head-no-penalty.",
        "TASKING LABEL ERROR (bookkeeping): lamorth0 described as '5-year protocol' but is a 3-FOLD run (mean 0.0672 is coincidence). Its role is the 3-fold mechanism ablation, valid as such.",
        "TASKING LABEL ERROR (bookkeeping): seed43/seed44 are 3-FOLD runs, quoted against seed42's 5-YEAR 0.0672 = cross-protocol. Same-protocol 3-fold triple = {0.0689,0.0652,0.0781}, mean 0.0707.",
        "NET-COST CAVEAT: paper Sharpe 8-19 assumes frictionless 4h fills; only break-even per-side (4.9-16 bps) is the honest gate; underwater at 9.5bps taker in thin-universe years (2022,2026).",
        "MECHANISM UNCONFIRMED AT 5YR: lam_orth=0 K-head has no 5-year run; mechanism inferred from 3-fold ablation (consistent, but a 5yr lamorth0 would close it)."],
    conditions_for_full_go=[
        "Re-label leaderboard: the lever is 'drop orthogonality penalty (lam_orth=0)', not 'QIM head'. Run a 5-year lamorth0 K-head to confirm mechanism at 5yr scale.",
        "Validate net-cost under realistic execution (maker-fill / impact / capacity) before any sizing; the frictionless 4h Sharpe is not deployable as-is.",
        "Prefer the full-universe regime (>=100 members, i.e. 2024+); thin-universe years (2022 @81 members, 2026 partial) are the weak, high-cost-sensitivity tail."])
json.dump(verdict, open(OUT, "w"), indent=2, default=str)
print("SAVED", OUT)
print(json.dumps({k: verdict[k] for k in ["final_verdict", "dyn_share_mean", "flags"]}, indent=2))
