#!/usr/bin/env python3
"""m2_readout.py — Stage 2 (M2) criteria H2.1–H2.4 of docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md (8530d2b7f / 1217d786) on ONE
base, from simulator path files. Operational definitions WRITTEN BEFORE ANY M2 NAV NUMBER (they operationalise the prereg; none is tuned):

Series        bt_tables.series_from_path per path (main reading, UA-FREEZE-EXCLUDE), bt_tables.series_mean over the 32 paths = the MEAN PATH
              (the certified tables' main object). Criteria are evaluated on the mean path; the 32-path distribution is reported alongside.
Windows       PRE2026 = [2023-06-30T04Z, 2025-12-31T20Z] (criterion window); segments 2023H2 = [2023-06-30T04Z, 2023-12-31T20Z],
              2024 = [2024-01-01T00Z, 2024-12-31T20Z], 2025 = [2025-01-01T00Z, 2025-12-31T20Z]; 2026 = [2026-01-01T00Z, 2026-08-31T00Z] REPORT ONLY.
Daily         complete UTC days only (all six anchors 00Z … 20Z of the day inside the window): r_d = Π(1 + r_w) − 1 over the day's six windows.
Sharpe        bt_tables.sharpe on those days (mean / std(ddof 1) · √365). Total return = Π(1 + r_d) − 1; CAGR = bt_tables.cagr.
maxDD         bt_tables.maxdd_5m on bt_tables.restrict(series, a0, a1) (5-minute NAV, re-based at a0). Worst day = min r_d.
BTC daily     r_BTC,d = exp(LP[d + 1 day] − LP[d]) − 1, BTCUSDT column of the certified price_full_raw_x0918r table (same day boundaries as
              r_d: the day's windows span [d 00:00Z, d+1 00:00Z]).
H2.1          realised daily beta = OLS slope WITH intercept of r_d(book) on r_BTC,d over PRE2026 complete days; PASS iff the M2 arm's beta ∈
              [−0.10, +0.10]. The base arm's beta is reported alongside (and per segment, and per path).
H2.2          ΔS = Sharpe(M2) − Sharpe(base): PASS iff ΔS(PRE2026) > 0 AND ΔS > 0 in at least 2 of {2023H2, 2024, 2025}.
H2.3          "not worse" = M2 ≥ base (no tolerance) for BOTH the PRE2026 maxDD (5m) and the PRE2026 worst day, each on the mean path AND on
              the 32-path average of the per-path values (the prereg's Stage-1 "路径均值" reading); PASS iff all four hold.
H2.4          for each certified cost cell c ∈ {fee_x1.25, slip_x1.5, fill_x0.9}: ΔS_c(PRE2026) = Sharpe(M2_c) − Sharpe(base_c), both on the
              same cell; PASS iff sign(ΔS_c) == sign(ΔS_main) for all three (a zero on either side = not the same sign).
Decomposition (PRE2026, mean paths, complete days): μ, σ (ddof 1) of r_d for both arms; Δμ = μ_M2 − μ_base; DRIFT TERM = −gm · β̄_book ·
              μ_BTC with β̄_book = mean over the window's PUBLISHED anchors of β_book/Σ|w| (the formula's hedge in gross units; gm = 2.0 NAV
              per unit gross) and μ_BTC = mean r_BTC,d; also the Sharpe split: mean-only (μ_M2/σ_base − μ_base/σ_base)·√365 and variance-only
              (μ_base/σ_M2 − μ_base/σ_base)·√365.
DRIFT-DEPENDENT  iff H2.2 PASSES and σ_M2 ≥ σ_base and Δμ > 0 and DRIFT TERM ≥ Δμ (the variance did not fall and the drift accounts for all
              of the return increment).
VERDICT       PASS iff H2.1–H2.4 all PASS and not DRIFT-DEPENDENT; DRIFT-DEPENDENT iff the rule above holds; UNDECIDED iff any criterion is
              not computable (undefined Sharpe / empty window / missing paths); otherwise FAIL (the failing criteria are listed).
Empty inputs raise; counts (n_days, n_anchors, n_paths) are printed next to every aggregate.
usage: python m2_readout.py <label> <base_dir> <m2_dir> <cost_pairs: cell=base_dir:m2_dir,…> <diag_npz> <out.json>
"""
import os, sys, json, time, math, hashlib, calendar
import numpy as np

DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_tables as BTT

GM = 2.0; DAY = 86400; H4 = 14400; BTC = "BTCUSDT"
PRICE = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PRICE_SHA = "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"
META = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"; META_SHA = "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


WIN = {"PRE2026": (ts("2023-06-30T04:00:00Z"), ts("2025-12-31T20:00:00Z")), "2023H2": (ts("2023-06-30T04:00:00Z"), ts("2023-12-31T20:00:00Z")),
       "2024": (ts("2024-01-01T00:00:00Z"), ts("2024-12-31T20:00:00Z")), "2025": (ts("2025-01-01T00:00:00Z"), ts("2025-12-31T20:00:00Z")),
       "2026_report_only": (ts("2026-01-01T00:00:00Z"), ts("2026-08-31T00:00:00Z"))}
SEGS = ("2023H2", "2024", "2025")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


class Empty(Exception):
    pass


def load_dir(d):
    paths, files = BTT.load_run_dir(d, 32)
    return {"paths": paths, "mean": BTT.series_mean(paths), "files": files, "dir": d}


def complete_days(s, a0, a1):
    m = (s["A"] >= a0) & (s["A"] <= a1)
    A = s["A"][m]; r = s["r"][m]
    if len(A) == 0: raise Empty(f"no anchors in [{a0}, {a1}]")
    d = (A // DAY) * DAY
    ud, inv, cnt = np.unique(d, return_inverse=True, return_counts=True)
    out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + r)
    keep = cnt == 6
    if not keep.any(): raise Empty("no complete day")
    return ud[keep], out[keep] - 1.0, int(len(ud) - keep.sum())


def ols(y, x):
    y = np.asarray(y, float); x = np.asarray(x, float)
    if len(y) < 3: raise Empty("fewer than 3 points")
    dx = x - x.mean(); return float((dx * (y - y.mean())).sum() / (dx * dx).sum())


def btc_daily(days):
    PM = np.load(META, allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; j = SY.index(BTC); g0 = int(PM["grid"][0])
    LP = np.load(PRICE, mmap_mode="r")
    r0 = (days - g0) // 300; r1 = (days + DAY - g0) // 300
    if np.any((days - g0) % 300 != 0) or r1.max() >= LP.shape[0]: raise Empty("BTC day boundary off the price grid")
    return np.expm1(np.asarray(LP[r1, j], float) - np.asarray(LP[r0, j], float))


def metrics(s, a0, a1, bmap):
    days, rd, n_partial = complete_days(s, a0, a1)
    rb = np.array([bmap[int(d)] for d in days])
    sub = BTT.restrict(s, a0, a1)
    return {"n_days": int(len(days)), "n_partial_days_excluded": n_partial, "n_anchors": int(len(sub["A"])), "sharpe": BTT.sharpe(rd),
            "total_return": float(np.prod(1.0 + rd) - 1.0), "cagr": BTT.cagr(rd), "maxdd_5m": BTT.maxdd_5m(sub, np.ones(len(sub["A"]), bool)),
            "worst_day": float(rd.min()), "mu_daily": float(rd.mean()), "sd_daily": float(rd.std(ddof=1)), "beta_daily_vs_btc": ols(rd, rb),
            "corr_daily_vs_btc": float(np.corrcoef(rd, rb)[0, 1]),
            "g_bps_per_anchor": float(sub["g"].mean()), "price_bps": float(sub["pnl"].mean()), "funding_paid_bps": float(sub["car"].mean()),
            "fee_bps": float(sub["cst"].mean()), "unknown_excluded_bps": float(sub["unk"].mean()), "turnover_over_gross": float(sub["tau"].mean()),
            "day_stop_flattens": float(sub["dstop"].sum()), "per_name_stops": float(sub["nstop"].sum()), "halt_anchors": float(sub["halt"].sum())}


def path_dist(paths, a0, a1, bmap):
    per = [metrics(p, a0, a1, bmap) for p in paths]
    out = {}
    for k in ("sharpe", "maxdd_5m", "worst_day", "total_return", "beta_daily_vs_btc", "day_stop_flattens", "per_name_stops"):
        v = np.array([m[k] for m in per], float)
        if not np.all(np.isfinite(v)): raise Empty(f"non-finite per-path {k}")
        out[k] = {"n_paths": len(v), "path_mean": float(v.mean()), "p2.5": float(np.percentile(v, 2.5)), "p50": float(np.percentile(v, 50)), "p97.5": float(np.percentile(v, 97.5))}
    return out


def main():
    label, base_d, m2_d, cost_s, diag_p, outp = sys.argv[1:7]
    assert sha(PRICE) == PRICE_SHA and sha(META) == META_SHA, "price pins"
    out = {"device": "m2_readout.py", "self_sha256": sha(os.path.abspath(__file__)), "bt_tables_sha256": sha(os.path.join(DEV, "bt_tables.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "label": label, "inputs": {"base": base_d, "m2": m2_d, "diag": {"path": diag_p, "sha256": sha(diag_p)}},
           "windows": {k: [time.strftime("%Y-%m-%dT%HZ", time.gmtime(a)), time.strftime("%Y-%m-%dT%HZ", time.gmtime(b))] for k, (a, b) in WIN.items()}}
    B = load_dir(base_d); M2 = load_dir(m2_d)
    assert np.array_equal(B["mean"]["A"], M2["mean"]["A"]), "axis"
    out["inputs"]["base_files"] = B["files"]; out["inputs"]["m2_files"] = M2["files"]
    alld = np.unique((B["mean"]["A"] // DAY) * DAY); bd = btc_daily(alld); bmap = {int(d): float(v) for d, v in zip(alld, bd)}
    tab = {}
    for w, (a0, a1) in WIN.items():
        tab[w] = {"base": {"mean_path": metrics(B["mean"], a0, a1, bmap), "paths": path_dist(B["paths"], a0, a1, bmap)},
                  "m2": {"mean_path": metrics(M2["mean"], a0, a1, bmap), "paths": path_dist(M2["paths"], a0, a1, bmap)}}
        db, dm = tab[w]["base"]["mean_path"], tab[w]["m2"]["mean_path"]
        tab[w]["delta"] = {k: (dm[k] - db[k]) if (dm[k] is not None and db[k] is not None) else None
                           for k in ("sharpe", "total_return", "cagr", "maxdd_5m", "worst_day", "mu_daily", "sd_daily", "beta_daily_vs_btc", "g_bps_per_anchor")}
    out["table"] = tab
    # ---- beta_book distribution ----
    D = np.load(diag_p); A = D["anchor"].astype(np.int64); pub = D["kind"] > 0; hb = np.where(pub, D["beta_book"] / np.where(D["L1_base"] > 0, D["L1_base"], 1), np.nan)
    bbd = {}
    for w, (a0, a1) in WIN.items():
        m = pub & (A >= a0) & (A <= a1)
        if not m.any(): raise Empty(f"no published anchor in {w}")
        x = hb[m]; bbd[w] = {"n_published_anchors": int(m.sum()), "mean": float(x.mean()), **{f"p{q}": float(np.percentile(x, q)) for q in (5, 25, 50, 75, 95)},
                             "share_negative": float((x < 0).mean()), "raw_file_units_mean": float(D["beta_book"][m].mean())}
    out["beta_book_gross_units"] = bbd
    # ---- criteria ----
    P = tab["PRE2026"]; mb, mm = P["base"]["mean_path"], P["m2"]["mean_path"]
    crit = {}
    crit["H2.1"] = {"beta_m2": mm["beta_daily_vs_btc"], "beta_base": mb["beta_daily_vs_btc"], "gate": [-0.10, 0.10],
                    "pass": -0.10 <= mm["beta_daily_vs_btc"] <= 0.10}
    und = []
    dS = P["delta"]["sharpe"]; segd = {s: tab[s]["delta"]["sharpe"] for s in SEGS}
    if dS is None or any(v is None for v in segd.values()): und.append("H2.2")
    crit["H2.2"] = {"dS_pre2026": dS, "dS_segments": segd, "n_segments_positive": sum(1 for v in segd.values() if v is not None and v > 0),
                    "pass": (dS is not None and dS > 0 and sum(1 for v in segd.values() if v is not None and v > 0) >= 2)}
    pb, pm = P["base"]["paths"], P["m2"]["paths"]
    h3 = {"maxdd_mean_path": [mm["maxdd_5m"], mb["maxdd_5m"], mm["maxdd_5m"] >= mb["maxdd_5m"]],
          "worst_day_mean_path": [mm["worst_day"], mb["worst_day"], mm["worst_day"] >= mb["worst_day"]],
          "maxdd_path_average": [pm["maxdd_5m"]["path_mean"], pb["maxdd_5m"]["path_mean"], pm["maxdd_5m"]["path_mean"] >= pb["maxdd_5m"]["path_mean"]],
          "worst_day_path_average": [pm["worst_day"]["path_mean"], pb["worst_day"]["path_mean"], pm["worst_day"]["path_mean"] >= pb["worst_day"]["path_mean"]]}
    crit["H2.3"] = {"[m2, base, m2>=base]": h3, "pass": all(v[2] for v in h3.values())}
    cc = {}
    for item in [x for x in cost_s.split(",") if x]:
        cell, dirs = item.split("="); bdir, mdir = dirs.split(":")
        Bc, Mc = load_dir(bdir), load_dir(mdir); a0, a1 = WIN["PRE2026"]
        sb = metrics(Bc["mean"], a0, a1, bmap)["sharpe"]; sm = metrics(Mc["mean"], a0, a1, bmap)["sharpe"]
        d = (sm - sb) if (sm is not None and sb is not None) else None
        cc[cell] = {"sharpe_base": sb, "sharpe_m2": sm, "dS": d, "same_sign_as_main": (d is not None and dS is not None and np.sign(d) == np.sign(dS) and d != 0 and dS != 0),
                    "base_dir": bdir, "m2_dir": mdir}
    if len(cc) != 3: und.append("H2.4 (cells run: %d of 3)" % len(cc))
    crit["H2.4"] = {"cells": cc, "pass": len(cc) == 3 and all(v["same_sign_as_main"] for v in cc.values())}
    mu_b, mu_m, sd_b, sd_m = mb["mu_daily"], mm["mu_daily"], mb["sd_daily"], mm["sd_daily"]
    days, _, _ = complete_days(B["mean"], *WIN["PRE2026"]); mu_btc = float(np.mean([bmap[int(d)] for d in days]))
    drift = -GM * bbd["PRE2026"]["mean"] * mu_btc
    dec = {"mu_base": mu_b, "mu_m2": mu_m, "d_mu": mu_m - mu_b, "sd_base": sd_b, "sd_m2": sd_m, "d_sd": sd_m - sd_b, "mu_btc_daily": mu_btc,
           "beta_book_gross_units_mean": bbd["PRE2026"]["mean"], "drift_term_daily": drift, "drift_share_of_d_mu": (drift / (mu_m - mu_b)) if mu_m != mu_b else None,
           "sharpe_split_mean_only": (mu_m / sd_b - mu_b / sd_b) * math.sqrt(365), "sharpe_split_variance_only": (mu_b / sd_m - mu_b / sd_b) * math.sqrt(365),
           "n_days": len(days)}
    drift_dep = bool(crit["H2.2"]["pass"] and sd_m >= sd_b and (mu_m - mu_b) > 0 and drift >= (mu_m - mu_b))
    dec["drift_dependent_rule"] = {"h22_pass": crit["H2.2"]["pass"], "sd_m2_ge_sd_base": sd_m >= sd_b, "d_mu_pos": (mu_m - mu_b) > 0, "drift_ge_d_mu": drift >= (mu_m - mu_b), "fires": drift_dep}
    out["criteria"] = crit; out["decomposition_PRE2026"] = dec
    allpass = all(crit[k]["pass"] for k in ("H2.1", "H2.2", "H2.3", "H2.4"))
    if und: verdict = "UNDECIDED"
    elif drift_dep: verdict = "DRIFT-DEPENDENT"
    elif allpass: verdict = "PASS"
    else: verdict = "FAIL"
    out["undecided_because"] = und; out["failing"] = [k for k in ("H2.1", "H2.2", "H2.3", "H2.4") if not crit[k]["pass"]]
    out["VERDICT"] = verdict
    json.dump(out, open(outp + ".tmp", "w"), indent=1, default=float); os.replace(outp + ".tmp", outp)
    print(f"M2_READOUT {label} VERDICT={verdict} failing={out['failing']} undecided={und} out_sha256={sha(outp)}", flush=True)


if __name__ == "__main__":
    main()
