#!/usr/bin/env python3
"""ovn_stats.py — prereg §1.4–§1.6 statistics and verdict for OVN Stage 1 (docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md, 8530d2b7f /
1217d786), exactly as operationalised in receipts/OVN_OPERATIONALISATION.json (written before any number). Reads the per-path files the certified
launcher wrote; uses the certified table device's series / 5-minute drawdown / block-bootstrap functions (bt_tables.py 892ba66b) — no new simulator.
Preconditions (each failure raises; nothing is filled):
  P0  every arm-cell has exactly the 32 seed files; each PATH json's npz_sha256 equals the file; bt_driver_lib.audits_clean on every path.
  P1  OLD reproduction: every OVN OLD path npz (all five cells) is byte-identical (sha256) to the certified /workspace/baseline_tables_2026-09-19 run's
      path npz of the same seed (recorded in the certified PATH json); else OLD_REPRODUCTION = FAIL and the device stops.
  P2  all arms share one window axis; the day axis of every comparison is identical; no NaN in any series; no empty segment.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_stats.py PATH,HOME,LC_CTYPE <runs_root> <certified_runs_root> <out.json>
"""
import os, sys, json, time, math, hashlib, calendar

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT
import bt_driver_lib as DL

RUNS, CERT, OUT = sys.argv[2:5]
H4 = 14400; DAY = 86400; B = 10000; RNG = (20260923, 1); BLOCK_MAIN = 30; BLOCK_SENS = 5; NPATH = 32
PCT97_5 = (1.25, 98.75); PCT95 = (2.5, 97.5)
DEV = {"bt_tables.py": "892ba66b9e8040ff04caede02272556dec5a71eb4632cbe7a2a13f46bd35f389", "bt_driver_lib.py": "ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


for f, s in DEV.items(): assert sha(os.path.join(HERE, f)) == s, f"device sha {f}"
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
JUDGE = ("2023H2", "2024", "2025")
EXTSEG = ("2026-08-31T04:00:00Z", "2026-09-18T20:00:00Z")
ARMS = {"OLD": "OBJB_A0", "NEW_s42": "OVN_NEW_s42", "NEW_s2027": "OVN_NEW_s2027"}
CELLS = {"base": "scaled_rule_raw_UAFE", "fee_x1.25": "scaled_rule_raw_UAFE_fee_x1.25", "slip_x1.5": "scaled_rule_raw_UAFE_slip_x1.5",
         "fill_x0.9": "scaled_rule_raw_UAFE_fill_x0.9", "lit": "lit_rule_raw_UAFE"}
rec = {"device": "ovn_stats.py", "self_sha256": sha(os.path.abspath(__file__)), "devices": DEV, "utc_start": iso(time.time()), "runs_root": RUNS,
       "certified_runs_root": CERT, "rng": list(RNG), "B": B, "blocks": {"main": BLOCK_MAIN, "sensitivity": BLOCK_SENS}, "segments": SEG,
       "operationalisation": "receipts/OVN_OPERATIONALISATION.json", "preconditions": {}, "unavailable": []}


def load_cell(d, tag_dir, certified_dir=None):
    """→ list of 32 series (bt_tables.series_from_path) + file facts; P0 (+ P1 when certified_dir is given)"""
    stems = [os.path.join(d, f"PATH_{tag_dir}_seed_{k:02d}") for k in range(NPATH)]
    miss = [s for s in stems if not (os.path.exists(s + ".npz") and os.path.exists(s + ".json"))]
    if miss: raise FileNotFoundError(f"{tag_dir}: {len(miss)} path files missing, first {os.path.basename(miss[0])}")
    paths, facts = [], []
    for k, s in enumerate(stems):
        J = json.load(open(s + ".json")); h = sha(s + ".npz")
        if J["npz_sha256"] != h: raise ValueError(f"{tag_dir} seed {k}: npz sha != its json")
        if not DL.audits_clean(J["audits"]): raise ValueError(f"{tag_dir} seed {k}: audits not clean")
        if int(J["seed"]) != k: raise ValueError(f"{tag_dir} seed field {J['seed']} != {k}")
        f = {"seed": k, "npz_sha256": h, "status_counts": J["status_counts"], "events": J["events_fired_counts"], "target_stats": J["target_stats"]}
        if certified_dir is not None:
            CJ = json.load(open(os.path.join(certified_dir, os.path.basename(s) + ".json")))
            f["certified_npz_sha256"] = CJ["npz_sha256"]; f["byte_identical_to_certified"] = (CJ["npz_sha256"] == h)
        facts.append(f); paths.append(BT.series_from_path(np.load(s + ".npz")))
    A = paths[0]["A"]
    for p in paths:
        if not np.array_equal(p["A"], A): raise ValueError(f"{tag_dir}: window axes differ across seeds")
        for key in ("r", "pnl", "car", "cst", "unk", "g"):
            if not np.all(np.isfinite(p[key])): raise ValueError(f"{tag_dir}: non-finite {key}")
    return paths, facts


def seg_mask(A, a, b):
    m = (A >= ts(a)) & (A <= ts(b))
    if not m.any(): raise ValueError(f"empty segment {a}..{b}")
    return m


def full_days(A, m):
    """days whose 6 anchors (00..20Z) all lie in the mask"""
    d = (A[m] // DAY) * DAY; ud, c = np.unique(d, return_counts=True); return ud[c == 6]


def daily_on(A, r, days):
    ud, rd = BT.daily(A, r); pos = np.searchsorted(ud, days); assert np.all(ud[pos] == days); return rd[pos]


def path_metrics(p, m, days):
    A = p["A"]; r = p["r"][m]; rd = daily_on(A[m], r, days)
    tr = float(np.prod(1.0 + r) - 1.0); nw = int(m.sum())
    return {"n_windows": nw, "n_full_days": int(len(days)), "total_return": tr, "cagr": float((1.0 + tr) ** (2190.0 / nw) - 1.0) if tr > -1 else -1.0,
            "sharpe": BT.sharpe(rd), "worst_day": float(rd.min()), "maxdd_5m": BT.maxdd_5m(p, m),
            "g": float(p["g"][m].mean()), "price": float(p["pnl"][m].mean()), "funding_paid": float(p["car"][m].mean()), "fee": float(p["cst"][m].mean()),
            "unknown_excluded": float(p["unk"][m].mean()), "turnover_over_gross": float(p["tau"][m].mean()),
            "day_stop_flattens": float(p["dstop"][m].sum()), "per_name_stops": float(p["nstop"][m].sum()), "halt_anchors": float(p["halt"][m].sum()),
            "hold_anchors": float(p["hold"][m].sum()), "g_identity_max_err": float(np.max(np.abs(p["g"][m] - (p["pnl"][m] - p["car"][m] - p["cst"][m] - p["unk"][m]))))}


KEYS = ("total_return", "cagr", "sharpe", "worst_day", "maxdd_5m", "g", "price", "funding_paid", "fee", "unknown_excluded", "turnover_over_gross",
        "day_stop_flattens", "per_name_stops", "halt_anchors", "hold_anchors")


def summarise(per):
    out = {"n_paths": len(per), "n_windows": per[0]["n_windows"], "n_full_days": per[0]["n_full_days"]}
    for k in KEYS:
        v = [x[k] for x in per]
        if any(x is None for x in v): out[k] = {"UNAVAILABLE": f"{sum(x is None for x in v)} paths undefined"}; continue
        v = np.array(v, float); out[k] = {"path_mean": float(v.mean()), "p2.5": float(np.percentile(v, 2.5)), "p97.5": float(np.percentile(v, 97.5)), "n_eff": int(len(v))}
    out["g_identity_max_err"] = max(x["g_identity_max_err"] for x in per); assert out["g_identity_max_err"] <= 1e-9, "g identity"
    return out


def mean_path_metrics(paths, m, days):
    mp = BT.series_mean(paths); rd = daily_on(mp["A"][m], mp["r"][m], days); tr = float(np.prod(1.0 + mp["r"][m]) - 1.0)
    return {"total_return": tr, "sharpe": BT.sharpe(rd), "maxdd_5m": BT.maxdd_5m(mp, m), "worst_day": float(rd.min()), "note": "certified MEAN PATH (descriptive only)"}


def dbar(pn, po, m, days):
    """d̄(t) over the given full days: mean over seeds k of r_NEW,k(t) − r_OLD,k(t)"""
    D = np.stack([daily_on(a["A"][m], a["r"][m], days) - daily_on(b["A"][m], b["r"][m], days) for a, b in zip(pn, po)])
    if not np.all(np.isfinite(D)): raise ValueError("non-finite daily difference")
    return D.mean(0), D


def boot(x, block):
    n = len(x); idx = BT.mbb_indices(n, block, B, RNG); mb = x[idx].mean(1)
    return {"block_days": block, "n_days": n, "B": B, "rng": list(RNG), "ci97.5_two_sided_bps": [float(1e4 * np.percentile(mb, PCT97_5[0])), float(1e4 * np.percentile(mb, PCT97_5[1]))],
            "ci95_bps": [float(1e4 * np.percentile(mb, PCT95[0])), float(1e4 * np.percentile(mb, PCT95[1]))], "draws_defined": int(np.isfinite(mb).sum())}


# ─────────── load ───────────
S = {}
for arm, pre in ARMS.items():
    for cell, suf in CELLS.items():
        tag_dir = f"{pre}_{suf}"; d = os.path.join(RUNS, tag_dir)
        try:
            S[(arm, cell)] = load_cell(d, tag_dir, os.path.join(CERT, tag_dir) if arm == "OLD" else None)
        except Exception as e:
            rec["unavailable"].append({"arm": arm, "cell": cell, "why": f"{type(e).__name__}: {e}"}); print("UNAVAILABLE", arm, cell, e, flush=True)
# P1 OLD reproduction
repro = {}
for cell in CELLS:
    if ("OLD", cell) not in S: repro[cell] = "UNAVAILABLE"; continue
    f = S[("OLD", cell)][1]; repro[cell] = {"n_identical": sum(x["byte_identical_to_certified"] for x in f), "n": len(f)}
rec["preconditions"]["P1_old_reproduction"] = repro
if any(v == "UNAVAILABLE" or v["n_identical"] != v["n"] for v in repro.values()):
    rec["VERDICT"] = "STOPPED: OLD_REPRODUCTION FAIL"; json.dump(rec, open(OUT, "w"), indent=1)
    print("OVN_STATS VERDICT=STOPPED OLD_REPRODUCTION", repro, flush=True); sys.exit(3)
A = S[("OLD", "base")][0][0]["A"]
for k, (paths, _) in S.items():
    if not np.array_equal(paths[0]["A"], A): raise ValueError(f"{k}: window axis differs from OLD base")
rec["preconditions"]["P2_common_axis"] = {"first": iso(A[0]), "last": iso(A[-1]), "n": int(len(A))}
masks = {s: seg_mask(A, a, b) for s, (a, b) in SEG.items()}
days = {s: full_days(A, masks[s]) for s in SEG}
rec["days"] = {s: {"n_full_days": int(len(days[s])), "first": iso(days[s][0]), "last": iso(days[s][-1]), "n_windows": int(masks[s].sum())} for s in SEG}

# ─────────── §1.4 per arm, per cell, per segment ───────────
T = {}
for (arm, cell), (paths, facts) in S.items():
    T.setdefault(arm, {})[cell] = {}
    for s in SEG:
        per = [path_metrics(p, masks[s], days[s]) for p in paths]
        T[arm][cell][s] = {"paths": summarise(per), "mean_path": mean_path_metrics(paths, masks[s], days[s])}
        if cell == "base": T[arm][cell][s]["per_path"] = [{k: x[k] for k in ("sharpe", "total_return", "maxdd_5m", "day_stop_flattens")} for x in per]
rec["tables"] = T

# ─────────── §1.5 pairing, §1.6 criteria ───────────
V = {}
for seed in ("NEW_s42", "NEW_s2027"):
    v = {}
    if ("OLD", "base") not in S or (seed, "base") not in S:
        V[seed] = {"VERDICT_SEED": "UNAVAILABLE"}; continue
    po = S[("OLD", "base")][0]; pn = S[(seed, "base")][0]
    db, D = dbar(pn, po, masks["pre2026"], days["pre2026"])
    est = float(1e4 * db.mean())
    b30 = boot(db, BLOCK_MAIN); b5 = boot(db, BLOCK_SENS)
    # sensitivity: the partial first day (2023-06-30, 5 windows) included as a daily observation
    dp = np.concatenate([[ts("2023-06-30T00:00:00Z")], days["pre2026"]])
    ud_all = lambda p: BT.daily(p["A"][masks["pre2026"]], p["r"][masks["pre2026"]])
    Dp = np.stack([ud_all(a)[1] - ud_all(b)[1] for a, b in zip(pn, po)]); assert np.array_equal(ud_all(pn[0])[0], dp)
    dbp = Dp.mean(0); b30p = boot(dbp, BLOCK_MAIN)
    seg_means = {}
    for s in JUDGE + ("2026",):
        x, _ = dbar(pn, po, masks[s], days[s]); seg_means[s] = {"mean_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
    G1 = est > 0 and b30["ci97.5_two_sided_bps"][0] > 0
    G1_upper_below_0 = b30["ci97.5_two_sided_bps"][1] < 0
    G2n = sum(seg_means[s]["mean_bps_per_day"] > 0 for s in JUDGE); G2 = G2n >= 2
    sh = lambda arm: {s: T[arm]["base"][s]["paths"]["sharpe"]["path_mean"] for s in JUDGE}
    shn, sho = sh(seed), sh("OLD"); worst_n, worst_o = min(shn.values()), min(sho.values())
    ddn = T[seed]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]; ddo = T["OLD"]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]
    G3a = worst_n >= worst_o - 0.10; G3b = ddn >= ddo - 0.02; G3 = G3a and G3b
    g4 = {}
    for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9"):
        if ("OLD", c) not in S or (seed, c) not in S: g4[c] = {"UNAVAILABLE": True}; continue
        x, _ = dbar(S[(seed, c)][0], S[("OLD", c)][0], masks["pre2026"], days["pre2026"]); e = float(1e4 * x.mean())
        g4[c] = {"estimate_bps_per_day": e, "same_strict_sign_as_base": bool(np.sign(e) == np.sign(est) and e != 0.0)}
    G4 = all(isinstance(v_, dict) and v_.get("same_strict_sign_as_base") for v_ in g4.values())
    evn = T[seed]["base"]["pre2026"]["paths"]["day_stop_flattens"]["path_mean"]; evo = T["OLD"]["base"]["pre2026"]["paths"]["day_stop_flattens"]["path_mean"]
    G5 = evn <= 1.25 * evo
    v = {"G1": {"PASS": bool(G1), "estimate_bps_per_day": est, "boot_30d": b30, "boot_5d_sensitivity": b5, "n_days": int(len(db)), "n_paths": int(D.shape[0]),
                "gate": "estimate > 0 AND lower bound of the 97.5% two-sided interval (30-day blocks) > 0", "upper_below_0": bool(G1_upper_below_0),
                "sensitivity_partial_first_day_included": {"estimate_bps_per_day": float(1e4 * dbp.mean()), "boot_30d": b30p,
                                                            "changes_G1": bool((float(dbp.mean()) > 0 and b30p["ci97.5_two_sided_bps"][0] > 0) != G1)}},
         "G2": {"PASS": bool(G2), "segments_positive": int(G2n), "segment_means": seg_means, "gate": ">= 2 of 2023H2 / 2024 / 2025 with segment mean d̄ > 0"},
         "G3": {"PASS": bool(G3), "sharpe_path_mean_by_segment": {"NEW": shn, "OLD": sho}, "worst_segment_sharpe": {"NEW": worst_n, "OLD": worst_o},
                "sharpe_part_PASS": bool(G3a), "maxdd_5m_pre2026_path_mean": {"NEW": ddn, "OLD": ddo}, "maxdd_part_PASS": bool(G3b),
                "gate": "NEW worst-segment Sharpe >= OLD worst-segment Sharpe − 0.10 AND NEW pre-2026 maxDD >= OLD − 0.02"},
         "G4": {"PASS": bool(G4), "cells": g4, "base_estimate_bps_per_day": est, "gate": "G1 point estimate keeps its strict sign under each certified cost cell"},
         "G5": {"PASS": bool(G5), "day_stop_flattens_pre2026_path_mean": {"NEW": evn, "OLD": evo, "limit_1.25x_OLD": 1.25 * evo}, "gate": "NEW <= 1.25 x OLD"}}
    v["ALL_G_PASS"] = bool(G1 and G2 and G3 and G4 and G5)
    V[seed] = v
rec["criteria"] = V
if all(V[s].get("ALL_G_PASS") for s in V): verdict = "PASS"
elif all(isinstance(V[s].get("G1"), dict) and V[s]["G1"]["upper_below_0"] for s in V): verdict = "REVERSE"
else: verdict = "UNDECIDED"
rec["VERDICT"] = verdict
rec["verdict_rule"] = "PASS iff both seeds pass G1..G5; REVERSE iff both seeds' 97.5% interval (30-day blocks) upper bound < 0; else UNDECIDED"
rec["utc_end"] = iso(time.time())
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
for s in ("NEW_s42", "NEW_s2027"):
    v = V[s]
    if "G1" not in v: print(f"OVN_STATS SEED {s}: UNAVAILABLE", flush=True); continue
    print(f"OVN_STATS SEED {s}: G1={'PASS' if v['G1']['PASS'] else 'FAIL'}({v['G1']['estimate_bps_per_day']:+.3f} bps/d, 97.5%CI30 [{v['G1']['boot_30d']['ci97.5_two_sided_bps'][0]:+.3f}, {v['G1']['boot_30d']['ci97.5_two_sided_bps'][1]:+.3f}]) "
          f"G2={'PASS' if v['G2']['PASS'] else 'FAIL'}({v['G2']['segments_positive']}/3) G3={'PASS' if v['G3']['PASS'] else 'FAIL'} G4={'PASS' if v['G4']['PASS'] else 'FAIL'} "
          f"G5={'PASS' if v['G5']['PASS'] else 'FAIL'} ALL={'PASS' if v['ALL_G_PASS'] else 'FAIL'}", flush=True)
print(f"OVN_STATS VERDICT={verdict} unavailable={len(rec['unavailable'])} old_reproduction={repro} receipt_sha256={sha(OUT)}", flush=True)
