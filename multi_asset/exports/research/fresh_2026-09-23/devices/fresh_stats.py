#!/usr/bin/env python3
"""fresh_stats.py — FRESH decision rule F1–F5 (docs/PREREG_fresh_models_newS_2026-09-23.md b6e682e0a §3).
Loading, segment/day conventions, per-path metrics, d̄ and the block bootstrap are copied VERBATIM from news_stats.py
(which copied them from the Stage 1 device ovn_stats.py 1c35efb5; bt_tables 892ba66b / bt_driver_lib ba3bc261) — the same
operationalisation (full UTC days only, path mean = mean over the 32 per-path metrics, 30-day MBB B=10,000, rng [20260923,1]).
Control = NEW_S SAME SEED (prereg §2). No new control run is made: NEW_S's own path files are read.

Rules (both F10 seeds must satisfy all five, else the verdict is KEEP_NEWS naming the failing rule):
  F1 judge-window (2023-06-30T04Z → 2026-08-31T00Z) mean daily difference (FRESH − NEW_S) point estimate > 0
  F2 of 2023H2 / 2024 / 2025 / 2026(1–8), at least 3 segments with point estimate > 0
  F3 judge-window maxDD (path mean, 5-minute) not worse than NEW_S (FRESH >= NEW_S; both negative)
  F4 R-P (−25 % from the FULL_RECIPE base 2023-06-30T04:00:00Z, permanent halt) halted paths <= NEW_S
  F5 under the three certified cost cells the F1 sign is unchanged
30-day block intervals are REPORTED, NOT gated.

R-P run selection (same contract as news_stats AMENDMENT 2 / review R10-E02): a reading receipt may hold several runs
(scaled + lit). `select_rp_run` picks the ONE run whose `dir` equals the base-cell directory the tables load
(<runs_root>/<prefix>_scaled_rule_raw_UAFE), refuses 0 or >1 matches, and checks the frozen object: threshold −0.25,
FULL_RECIPE base 2023-06-30T04:00:00Z, 32 paths with seeds exactly 0..31, window end 2026-08-31T00:00:00Z.
The module has no side effects on import (the red/green test imports `select_rp_run`); main() runs only as a script.

Precondition P0_same_engine (FRESH-specific, load-bearing): every loaded path file of both arms must carry the same
device_sha256 / calibration_sha256 / price_pin, and each arm's config_sha256 must equal its own run-config file's sha.
A difference there would mean the two arms were not run by the same engine and the paired difference is not interpretable.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B fresh_stats.py PATH,HOME,LC_CTYPE
         <news_runs> <fresh_runs> <P_NEWS_s42.json> <P_NEWS_s2027.json> <P_FRESH_s42.json> <P_FRESH_s2027.json>
         <news_cfg_s42> <news_cfg_s2027> <fresh_cfg_s42> <fresh_cfg_s2027> <out.json>
"""
import os, sys, json, time, math, hashlib, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
H4 = 14400; DAY = 86400; B = 10000; RNG = (20260923, 1); BLOCK_MAIN = 30; BLOCK_SENS = 5; NPATH = 32
PCT97_5 = (1.25, 98.75); PCT95 = (2.5, 97.5)
DEV = {"bt_tables.py": "892ba66b9e8040ff04caede02272556dec5a71eb4632cbe7a2a13f46bd35f389", "bt_driver_lib.py": "ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb"}
BTP_SHA = "a7cb9c4d02dd07751fd298500c8e88d54e884d236429bff2f3567fbb77e1ff48"
# PREREG §2: judge window 2023-06-30T04Z → 2026-08-31T00Z in four segments
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z"),
       "judge": ("2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z"), "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}
JUDGE_SEGMENTS = ("2023H2", "2024", "2025", "2026"); JUDGE_WINDOW = "judge"; F2_MIN_POSITIVE = 3
PAIRS = (("FRESH_s42", "NEWS_s42"), ("FRESH_s2027", "NEWS_s2027"))
CELLS = {"base": "scaled_rule_raw_UAFE", "fee_x1.25": "scaled_rule_raw_UAFE_fee_x1.25", "slip_x1.5": "scaled_rule_raw_UAFE_slip_x1.5",
         "fill_x0.9": "scaled_rule_raw_UAFE_fill_x0.9", "lit": "lit_rule_raw_UAFE"}
PREFIX = {"NEWS_s42": "NEWS_s42", "NEWS_s2027": "NEWS_s2027", "FRESH_s42": "FRESH_s42", "FRESH_s2027": "FRESH_s2027"}
PREREG = {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"}
NEWS_PREREG = {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7",
               "amendment_1": {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}}
SENTENCE = ("30 日块自举区间照报不作门。仪器区间半宽约 3–10 bps/日(E-0923-B),\"下界 > 0\"等于要求效应超过这个量级;"
            "本规则是候选选择规则,不是显著性声明。")
RP_THRESHOLD = -0.25; RP_BASE_LABEL = "FULL_RECIPE window start"; RP_BASE_ANCHOR = "2023-06-30T04:00:00Z"
RP_BASE_KEY = f"{RP_BASE_LABEL} @ {RP_BASE_ANCHOR}"; RP_WINDOW_END = "2026-08-31T00:00:00Z"
BT = DL = None


class RPError(Exception):
    pass


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso_): return calendar.timegm(time.strptime(iso_, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def select_rp_run(receipt_path, expected_dir, check_device_sha=True):
    """→ dict(halted_paths, n_paths, run_key, ...) for the ONE run of the receipt whose dir == expected_dir; RPError otherwise."""
    R = json.load(open(receipt_path))
    if check_device_sha and R.get("self_sha256") != BTP_SHA: raise RPError(f"bt_p_reading sha {str(R.get('self_sha256'))[:16]} != {BTP_SHA[:16]}")
    rule = R.get("rule", {})
    if rule.get("threshold_cum_return") != RP_THRESHOLD: raise RPError(f"threshold {rule.get('threshold_cum_return')} != {RP_THRESHOLD}")
    if not any(b.get("label") == RP_BASE_LABEL and b.get("anchor") == RP_BASE_ANCHOR for b in rule.get("bases", [])): raise RPError("FULL_RECIPE base 2023-06-30T04Z not declared")
    if rule.get("breach_by") != RP_WINDOW_END: raise RPError(f"breach_by {rule.get('breach_by')} != {RP_WINDOW_END}")
    want = os.path.normpath(expected_dir)
    hits = [(k, v) for k, v in R.get("runs", {}).items() if os.path.normpath(str(v.get("dir", ""))) == want]
    if len(hits) != 1: raise RPError(f"{len(hits)} runs match dir {want} (runs: {list(R.get('runs', {}))})")
    key, run = hits[0]
    if run.get("n_paths") != NPATH: raise RPError(f"n_paths {run.get('n_paths')} != {NPATH}")
    if list(run.get("window", []))[-1:] != [RP_WINDOW_END]: raise RPError(f"run window end {run.get('window')} != {RP_WINDOW_END}")
    base = run.get("bases", {}).get(RP_BASE_KEY)
    if base is None: raise RPError(f"no base '{RP_BASE_KEY}' in run {key}")
    pp = base.get("per_path", [])
    seeds = sorted(int(x["seed"]) for x in pp)
    if seeds != list(range(NPATH)): raise RPError(f"per-path seeds are not exactly 0..{NPATH - 1}: {seeds[:5]}… (n={len(seeds)})")
    ends = {x.get("window_last_anchor") for x in pp}
    if ends != {RP_WINDOW_END}: raise RPError(f"per-path window ends {sorted(map(str, ends))} != {{{RP_WINDOW_END}}}")
    return {"receipt": receipt_path, "receipt_sha256": sha(receipt_path), "run_key": key, "run_dir": run["dir"], "halted_paths": int(sum(1 for x in pp if x["fired"])),
            "n_paths": len(pp), "threshold": RP_THRESHOLD, "base": RP_BASE_KEY, "window_end": RP_WINDOW_END}


# ───── verbatim from news_stats.py / ovn_stats.py (load_cell … boot); the only addition is the engine-pin fields ─────
def load_cell(d, tag_dir):
    stems = [os.path.join(d, f"PATH_{tag_dir}_seed_{k:02d}") for k in range(NPATH)]
    miss = [s for s in stems if not (os.path.exists(s + ".npz") and os.path.exists(s + ".json"))]
    if miss: raise FileNotFoundError(f"{tag_dir}: {len(miss)} path files missing, first {os.path.basename(miss[0])}")
    paths, facts = [], []
    for k, s in enumerate(stems):
        J = json.load(open(s + ".json")); h = sha(s + ".npz")
        if J["npz_sha256"] != h: raise ValueError(f"{tag_dir} seed {k}: npz sha != its json")
        if not DL.audits_clean(J["audits"]): raise ValueError(f"{tag_dir} seed {k}: audits not clean")
        if int(J["seed"]) != k: raise ValueError(f"{tag_dir} seed field {J['seed']} != {k}")
        facts.append({"seed": k, "npz_sha256": h, "status_counts": J["status_counts"], "events": J["events_fired_counts"], "target_stats": J["target_stats"],
                      "device_sha256": J["device_sha256"], "calibration_sha256": J["calibration_sha256"], "price_pin": J["price_pin"], "config_sha256": J["config_sha256"]})
        paths.append(BT.series_from_path(np.load(s + ".npz")))
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
    D = np.stack([daily_on(a["A"][m], a["r"][m], days) - daily_on(b["A"][m], b["r"][m], days) for a, b in zip(pn, po)])
    if not np.all(np.isfinite(D)): raise ValueError("non-finite daily difference")
    return D.mean(0), D


def boot(x, block):
    n = len(x); idx = BT.mbb_indices(n, block, B, RNG); mb = x[idx].mean(1)
    return {"block_days": block, "n_days": n, "B": B, "rng": list(RNG), "ci97.5_two_sided_bps": [float(1e4 * np.percentile(mb, PCT97_5[0])), float(1e4 * np.percentile(mb, PCT97_5[1]))],
            "ci95_bps": [float(1e4 * np.percentile(mb, PCT95[0])), float(1e4 * np.percentile(mb, PCT95[1]))], "draws_defined": int(np.isfinite(mb).sum())}


def main():
    global BT, DL
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
    sys.path.insert(0, HERE)
    import bt_tables as _BT
    import bt_driver_lib as _DL
    BT, DL = _BT, _DL
    RUNS_N, RUNS_F, P_N42, P_N2027, P_F42, P_F2027, CFG_N42, CFG_N2027, CFG_F42, CFG_F2027, OUT = sys.argv[2:13]
    for f, s in DEV.items(): assert sha(os.path.join(HERE, f)) == s, f"device sha {f}"
    ARMS = {"NEWS_s42": (RUNS_N, PREFIX["NEWS_s42"]), "NEWS_s2027": (RUNS_N, PREFIX["NEWS_s2027"]),
            "FRESH_s42": (RUNS_F, PREFIX["FRESH_s42"]), "FRESH_s2027": (RUNS_F, PREFIX["FRESH_s2027"])}
    CFG = {"NEWS_s42": CFG_N42, "NEWS_s2027": CFG_N2027, "FRESH_s42": CFG_F42, "FRESH_s2027": CFG_F2027}
    RPR = {"NEWS_s42": P_N42, "NEWS_s2027": P_N2027, "FRESH_s42": P_F42, "FRESH_s2027": P_F2027}
    rec = {"device": "fresh_stats.py", "self_sha256": sha(os.path.abspath(__file__)), "devices": DEV, "utc_start": iso(time.time()),
           "runs_roots": {"news_control": RUNS_N, "fresh": RUNS_F}, "configs": {k: {"path": v, "sha256": sha(v)} for k, v in CFG.items()},
           "rng": list(RNG), "B": B, "blocks": {"main": BLOCK_MAIN, "sensitivity": BLOCK_SENS}, "segments": SEG, "judge_segments": list(JUDGE_SEGMENTS),
           "prereg": PREREG, "newS_prereg": NEWS_PREREG, "operationalisation": "Stage 1 receipts/OVN_OPERATIONALISATION.json via news_stats.py (verbatim)",
           "preconditions": {}, "unavailable": [], "interval_statement_verbatim": SENTENCE}
    S = {}
    for arm, (root, pre) in ARMS.items():
        for cell, suf in CELLS.items():
            tag_dir = f"{pre}_{suf}"; d = os.path.join(root, tag_dir)
            try:
                S[(arm, cell)] = load_cell(d, tag_dir)
            except Exception as e:
                rec["unavailable"].append({"arm": arm, "cell": cell, "why": f"{type(e).__name__}: {e}"}); print("UNAVAILABLE", arm, cell, e, flush=True)
    need = [(a, c) for a in ARMS for c in CELLS]
    missing = [k for k in need if k not in S]
    rec["preconditions"]["P_cells_loaded"] = {"needed": len(need), "loaded": len(S), "missing": [list(k) for k in missing]}
    if missing:
        rec["VERDICT"] = "STOPPED: CELLS_MISSING"; json.dump(rec, open(OUT, "w"), indent=1, default=float)
        print("FRESH_STATS VERDICT=STOPPED missing", missing, flush=True); sys.exit(3)
    # ── P0_same_engine: both arms must carry identical engine / calibration / price pins, and each arm's config pin must be its own config file
    pins = {}
    for (arm, cell), (_, facts) in S.items():
        for what in ("device_sha256", "calibration_sha256", "price_pin", "config_sha256"):
            vals = {json.dumps(f[what], sort_keys=True) for f in facts}
            if len(vals) != 1: raise ValueError(f"{arm}/{cell}: {what} differs across the 32 paths ({len(vals)} distinct)")
            pins.setdefault((arm, cell), {})[what] = json.loads(vals.pop())
    eng = {}
    for what in ("device_sha256", "calibration_sha256", "price_pin"):
        vals = {json.dumps(v[what], sort_keys=True) for v in pins.values()}
        eng[what] = {"n_distinct": len(vals), "identical_across_all_arms_and_cells": len(vals) == 1, "value": json.loads(list(vals)[0]) if len(vals) == 1 else sorted(vals)}
    cfg_ok = {arm: {"config_sha256_in_paths": pins[(arm, "base")]["config_sha256"], "config_file_sha256": sha(CFG[arm]),
                    "match": pins[(arm, "base")]["config_sha256"] == sha(CFG[arm])} for arm in ARMS}
    rec["preconditions"]["P0_same_engine"] = {"engine_pins": eng, "config_pin_matches_config_file": cfg_ok,
                                              "PASS": bool(all(eng[w]["identical_across_all_arms_and_cells"] for w in eng) and all(v["match"] for v in cfg_ok.values()))}
    if not rec["preconditions"]["P0_same_engine"]["PASS"]:
        rec["VERDICT"] = "STOPPED: SAME_ENGINE FAIL"; json.dump(rec, open(OUT, "w"), indent=1, default=float)
        print("FRESH_STATS VERDICT=STOPPED same_engine", json.dumps(rec["preconditions"]["P0_same_engine"])[:400], flush=True); sys.exit(3)
    A = S[("NEWS_s42", "base")][0][0]["A"]
    for k, (paths, _) in S.items():
        if not np.array_equal(paths[0]["A"], A): raise ValueError(f"{k}: window axis differs from the NEWS_s42 base")
    rec["preconditions"]["P1_common_axis"] = {"first": iso(A[0]), "last": iso(A[-1]), "n": int(len(A))}
    rec["control_path_shas"] = {f"{a}/{c}": [f["npz_sha256"] for f in S[(a, c)][1]] for a in ("NEWS_s42", "NEWS_s2027") for c in CELLS}
    masks = {s: seg_mask(A, a, b) for s, (a, b) in SEG.items()}
    days = {s: full_days(A, masks[s]) for s in SEG}
    rec["days"] = {s: {"n_full_days": int(len(days[s])), "first": iso(days[s][0]), "last": iso(days[s][-1]), "n_windows": int(masks[s].sum())} for s in SEG}
    T = {}
    for (arm, cell), (paths, facts) in S.items():
        T.setdefault(arm, {})[cell] = {}
        for s in SEG:
            per = [path_metrics(p, masks[s], days[s]) for p in paths]
            T[arm][cell][s] = {"paths": summarise(per), "mean_path": mean_path_metrics(paths, masks[s], days[s])}
    rec["tables"] = T
    base_dir = {a: os.path.join(ARMS[a][0], f"{ARMS[a][1]}_{CELLS['base']}") for a in ARMS}
    RP = {a: select_rp_run(RPR[a], base_dir[a]) for a in ARMS}
    rec["R_P"] = RP

    def rules(fresh, ctrl):
        out = {}
        pn = S[(fresh, "base")][0]; po = S[(ctrl, "base")][0]
        db, D = dbar(pn, po, masks[JUDGE_WINDOW], days[JUDGE_WINDOW]); est = float(1e4 * db.mean())
        seg = {}
        for s in JUDGE_SEGMENTS:
            x, _ = dbar(pn, po, masks[s], days[s]); seg[s] = {"mean_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
        n_pos = sum(seg[s]["mean_bps_per_day"] > 0 for s in JUDGE_SEGMENTS)
        cells = {}
        for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9"):
            x, _ = dbar(S[(fresh, c)][0], S[(ctrl, c)][0], masks[JUDGE_WINDOW], days[JUDGE_WINDOW]); e = float(1e4 * x.mean())
            cells[c] = {"estimate_bps_per_day": e, "same_strict_sign_as_base": bool(np.sign(e) == np.sign(est) and e != 0.0)}
        ddn = T[fresh]["base"][JUDGE_WINDOW]["paths"]["maxdd_5m"]["path_mean"]; ddc = T[ctrl]["base"][JUDGE_WINDOW]["paths"]["maxdd_5m"]["path_mean"]
        out["F1"] = {"estimate_bps_per_day": est, "n_days": int(len(db)), "n_paths": int(D.shape[0]), "window": SEG[JUDGE_WINDOW], "PASS": bool(est > 0)}
        out["F2"] = {"segment_means": seg, "segments_positive": int(n_pos), "of": len(JUDGE_SEGMENTS), "min_required": F2_MIN_POSITIVE, "PASS": bool(n_pos >= F2_MIN_POSITIVE)}
        out["F3"] = {"maxdd_5m_judge_path_mean": {"FRESH": ddn, "NEWS": ddc}, "PASS": bool(ddn >= ddc), "gate": "FRESH maxDD (negative number) >= NEW_S maxDD"}
        out["F4"] = {"halted_paths": {"FRESH": RP[fresh]["halted_paths"], "NEWS": RP[ctrl]["halted_paths"]}, "PASS": bool(RP[fresh]["halted_paths"] <= RP[ctrl]["halted_paths"])}
        out["F5"] = {"cells": cells, "base_estimate_bps_per_day": est, "PASS": bool(all(v["same_strict_sign_as_base"] for v in cells.values()))}
        out["intervals_report_only"] = {"boot_30d": boot(db, BLOCK_MAIN), "boot_5d": boot(db, BLOCK_SENS),
                                        "per_segment_boot_30d": {s: boot(dbar(pn, po, masks[s], days[s])[0], BLOCK_MAIN) for s in JUDGE_SEGMENTS}}
        out["control"] = ctrl
        out["failing"] = [k for k in ("F1", "F2", "F3", "F4", "F5") if not out[k]["PASS"]]
        out["ALL_PASS"] = not out["failing"]
        return out

    V = {f: rules(f, c) for f, c in PAIRS}
    rec["rules"] = V
    verdict = "FRESH_REPLACES_NEWS" if all(V[f]["ALL_PASS"] for f, _ in PAIRS) else "KEEP_NEWS"
    rec["VERDICT"] = verdict
    rec["verdict_rule"] = "prereg §3: FRESH replaces NEW_S iff BOTH F10 seeds satisfy F1..F5; any seed failing any rule ⇒ keep NEW_S, naming the rule"
    rec["failing_by_seed"] = {f: V[f]["failing"] for f, _ in PAIRS}
    rec["utc_end"] = iso(time.time())
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    for f, c in PAIRS:
        v = V[f]
        print(f"FRESH_STATS {f} vs {c}: F1={'PASS' if v['F1']['PASS'] else 'FAIL'}({v['F1']['estimate_bps_per_day']:+.3f} bps/d) "
              f"F2={'PASS' if v['F2']['PASS'] else 'FAIL'}({v['F2']['segments_positive']}/4, need {F2_MIN_POSITIVE}) "
              f"F3={'PASS' if v['F3']['PASS'] else 'FAIL'}(maxDD {v['F3']['maxdd_5m_judge_path_mean']['FRESH']:.4f} vs {v['F3']['maxdd_5m_judge_path_mean']['NEWS']:.4f}) "
              f"F4={'PASS' if v['F4']['PASS'] else 'FAIL'}(halted {v['F4']['halted_paths']['FRESH']} vs {v['F4']['halted_paths']['NEWS']}) "
              f"F5={'PASS' if v['F5']['PASS'] else 'FAIL'} ALL={'PASS' if v['ALL_PASS'] else 'FAIL'}", flush=True)
    print(f"FRESH_STATS VERDICT={verdict} failing={rec['failing_by_seed']} unavailable={len(rec['unavailable'])} receipt_sha256={sha(OUT)}", flush=True)


if __name__ == "__main__":
    main()
