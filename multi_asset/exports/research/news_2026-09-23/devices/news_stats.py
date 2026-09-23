#!/usr/bin/env python3
"""news_stats.py — NEW_S decision rule S1–S5 (docs/PREREG_new_servable_models_2026-09-23.md db0123df7 §3, unchanged by AMENDMENTS 1–2).
Loading, P0 checks, segment/day conventions, per-path metrics, d̄ and the block bootstrap are copied VERBATIM from the Stage 1
statistics device ovn_stats.py (1c35efb5; bt_tables 892ba66b / bt_driver_lib ba3bc261 functions) — the same operationalisation
(receipts/OVN_OPERATIONALISATION.json: full UTC days only, path mean = mean over the 32 per-path metrics, 30-day MBB B=10,000
rng [20260923,1]). OLD and OLD_HOLD are Stage 1's own path files (their npz sha is re-checked against the Stage 1 receipts and,
for OLD, against the certified runs, i.e. Stage 1 precondition P1 re-run).
Rules (both seeds must satisfy all five, else NO-SWAP naming the failing rule):
  S1 pre-2026 mean daily difference (NEW_S − control) point estimate > 0 vs OLD and vs OLD_HOLD
  S2 of 2023H2 / 2024 / 2025, at least 2 segments with point estimate > 0 (vs both controls)
  S3 pre-2026 maxDD (path mean, 5-minute) not worse than OLD_HOLD (NEW_S >= OLD_HOLD)
  S4 R-P (−25 % from the FULL_RECIPE base 2023-06-30T04Z, permanent halt; Stage 1 reading bt_p_reading a7cb9c4d) halted paths <= OLD_HOLD
  S5 under the three certified cost cells the S1 sign is unchanged (vs both controls)
30-day block intervals are REPORTED, NOT gated.
AMENDMENT 2 (R10-E02): an R-P reading receipt may hold several runs (e.g. scaled + lit). `select_rp_run` picks the ONE run whose `dir`
equals the base-cell directory the S tables load (<runs_root>/<prefix>_scaled_rule_raw_UAFE), refuses 0 or >1 matches, and checks the
frozen object: threshold −0.25, FULL_RECIPE base 2023-06-30T04:00:00Z, 32 paths with seeds exactly 0..31, window end 2026-08-31T00:00:00Z.
The module has no side effects on import (tests import `select_rp_run`); main() runs only as a script.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B news_stats.py PATH,HOME,LC_CTYPE <stage1_runs> <news_runs> <certified_runs>
         <stage1_P_OLD_HOLD.json> <P_NEWS_s42.json> <P_NEWS_s2027.json> <P_OLD.json> <out.json>
"""
import os, sys, json, time, math, hashlib, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
H4 = 14400; DAY = 86400; B = 10000; RNG = (20260923, 1); BLOCK_MAIN = 30; BLOCK_SENS = 5; NPATH = 32
PCT97_5 = (1.25, 98.75); PCT95 = (2.5, 97.5)
DEV = {"bt_tables.py": "892ba66b9e8040ff04caede02272556dec5a71eb4632cbe7a2a13f46bd35f389", "bt_driver_lib.py": "ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb"}
BTP_SHA = "a7cb9c4d02dd07751fd298500c8e88d54e884d236429bff2f3567fbb77e1ff48"
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
JUDGE = ("2023H2", "2024", "2025")
CONTROLS = ("OLD", "OLD_HOLD"); SEEDS = ("NEWS_s42", "NEWS_s2027")
CELLS = {"base": "scaled_rule_raw_UAFE", "fee_x1.25": "scaled_rule_raw_UAFE_fee_x1.25", "slip_x1.5": "scaled_rule_raw_UAFE_slip_x1.5",
         "fill_x0.9": "scaled_rule_raw_UAFE_fill_x0.9", "lit": "lit_rule_raw_UAFE"}
PREFIX = {"OLD": "OBJB_A0", "OLD_HOLD": "OVN_OLD_HOLD", "NEWS_s42": "NEWS_s42", "NEWS_s2027": "NEWS_s2027"}
PREREG = {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7"}
AMD1 = {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}
AMD2 = {"path": "docs/AMENDMENT_2_new_servable_models_2026-09-23.md"}
SENTENCE = ("30 日块自举区间照报,不作门。依据 E-0923-B:这台仪器对此类比较的区间半宽约 10 bps/日,以\"下界 > 0\"为门等于要求效应 ≥ 约 10 bps/日。"
            "本规则是换装决策规则,不是\"统计显著\"的声明。")
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


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
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


# ───── verbatim from ovn_stats.py (load_cell / seg_mask / full_days / daily_on / path_metrics / summarise / mean_path_metrics / dbar / boot) ─────
def load_cell(d, tag_dir, certified_dir=None):
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
    RUNS1, RUNSN, CERT, P_OH, P_S42, P_S2027, P_OLD, OUT = sys.argv[2:10]
    for f, s in DEV.items(): assert sha(os.path.join(HERE, f)) == s, f"device sha {f}"
    ARMS = {"OLD": (RUNS1, PREFIX["OLD"]), "OLD_HOLD": (RUNS1, PREFIX["OLD_HOLD"]), "NEWS_s42": (RUNSN, PREFIX["NEWS_s42"]), "NEWS_s2027": (RUNSN, PREFIX["NEWS_s2027"])}
    rec = {"device": "news_stats.py", "self_sha256": sha(os.path.abspath(__file__)), "devices": DEV, "utc_start": iso(time.time()), "runs_roots": {"stage1": RUNS1, "news": RUNSN},
           "certified_runs_root": CERT, "rng": list(RNG), "B": B, "blocks": {"main": BLOCK_MAIN, "sensitivity": BLOCK_SENS}, "segments": SEG,
           "prereg": PREREG, "amendment_1": AMD1, "amendment_2": AMD2, "operationalisation": "Stage 1 receipts/OVN_OPERATIONALISATION.json (verbatim)",
           "preconditions": {}, "unavailable": [], "interval_statement_verbatim": SENTENCE}
    # ───── load (OLD_HOLD has no lit run by design, as in Stage 1) ─────
    S = {}
    for arm, (root, pre) in ARMS.items():
        for cell, suf in CELLS.items():
            if arm == "OLD_HOLD" and cell == "lit": continue
            tag_dir = f"{pre}_{suf}"; d = os.path.join(root, tag_dir)
            try:
                S[(arm, cell)] = load_cell(d, tag_dir, os.path.join(CERT, tag_dir) if arm == "OLD" else None)
            except Exception as e:
                rec["unavailable"].append({"arm": arm, "cell": cell, "why": f"{type(e).__name__}: {e}"}); print("UNAVAILABLE", arm, cell, e, flush=True)
    repro = {}
    for cell in CELLS:
        if ("OLD", cell) not in S: repro[cell] = "UNAVAILABLE"; continue
        f = S[("OLD", cell)][1]; repro[cell] = {"n_identical": sum(x["byte_identical_to_certified"] for x in f), "n": len(f)}
    rec["preconditions"]["P1_old_reproduction_recheck"] = repro
    if any(v == "UNAVAILABLE" or v["n_identical"] != v["n"] for v in repro.values()):
        rec["VERDICT"] = "STOPPED: OLD_REPRODUCTION FAIL"; json.dump(rec, open(OUT, "w"), indent=1); print("NEWS_STATS VERDICT=STOPPED", repro, flush=True); sys.exit(3)
    A = S[("OLD", "base")][0][0]["A"]
    for k, (paths, _) in S.items():
        if not np.array_equal(paths[0]["A"], A): raise ValueError(f"{k}: window axis differs from OLD base")
    rec["preconditions"]["P2_common_axis"] = {"first": iso(A[0]), "last": iso(A[-1]), "n": int(len(A))}
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
    # ───── R-P halted paths: the ONE main-reading run whose dir is the base-cell directory the S tables loaded (AMENDMENT 2) ─────
    base_dir = {a: os.path.join(ARMS[a][0], f"{ARMS[a][1]}_{CELLS['base']}") for a in ARMS}
    RP = {"OLD": select_rp_run(P_OLD, base_dir["OLD"]), "OLD_HOLD": select_rp_run(P_OH, base_dir["OLD_HOLD"]),
          "NEWS_s42": select_rp_run(P_S42, base_dir["NEWS_s42"]), "NEWS_s2027": select_rp_run(P_S2027, base_dir["NEWS_s2027"])}
    rec["R_P"] = RP

    def rules(seed):
        out = {"S1": {}, "S2": {}, "S5": {}, "intervals_report_only": {}}
        for ctrl in CONTROLS:
            po = S[(ctrl, "base")][0]; pn = S[(seed, "base")][0]
            db, D = dbar(pn, po, masks["pre2026"], days["pre2026"]); est = float(1e4 * db.mean())
            seg = {}
            for s in JUDGE + ("2026",):
                x, _ = dbar(pn, po, masks[s], days[s]); seg[s] = {"mean_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
            n_pos = sum(seg[s]["mean_bps_per_day"] > 0 for s in JUDGE)
            cells = {}
            for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9"):
                x, _ = dbar(S[(seed, c)][0], S[(ctrl, c)][0], masks["pre2026"], days["pre2026"]); e = float(1e4 * x.mean())
                cells[c] = {"estimate_bps_per_day": e, "same_strict_sign_as_base": bool(np.sign(e) == np.sign(est) and e != 0.0)}
            out["S1"][ctrl] = {"estimate_bps_per_day": est, "n_days": int(len(db)), "n_paths": int(D.shape[0]), "PASS": bool(est > 0)}
            out["S2"][ctrl] = {"segment_means": seg, "segments_positive": int(n_pos), "PASS": bool(n_pos >= 2)}
            out["S5"][ctrl] = {"cells": cells, "base_estimate_bps_per_day": est, "PASS": bool(all(v["same_strict_sign_as_base"] for v in cells.values()))}
            out["intervals_report_only"][ctrl] = {"boot_30d": boot(db, BLOCK_MAIN), "boot_5d": boot(db, BLOCK_SENS)}
        ddn = T[seed]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]; ddh = T["OLD_HOLD"]["base"]["pre2026"]["paths"]["maxdd_5m"]["path_mean"]
        out["S3"] = {"maxdd_5m_pre2026_path_mean": {"NEWS": ddn, "OLD_HOLD": ddh}, "PASS": bool(ddn >= ddh), "gate": "NEW_S maxDD (negative number) >= OLD_HOLD maxDD"}
        out["S4"] = {"halted_paths": {"NEWS": RP[seed]["halted_paths"], "OLD_HOLD": RP["OLD_HOLD"]["halted_paths"]}, "PASS": bool(RP[seed]["halted_paths"] <= RP["OLD_HOLD"]["halted_paths"])}
        out["S1"]["PASS"] = all(out["S1"][c]["PASS"] for c in CONTROLS); out["S2"]["PASS"] = all(out["S2"][c]["PASS"] for c in CONTROLS)
        out["S5"]["PASS"] = all(out["S5"][c]["PASS"] for c in CONTROLS)
        out["failing"] = [k for k in ("S1", "S2", "S3", "S4", "S5") if not out[k]["PASS"]]
        out["ALL_PASS"] = not out["failing"]
        return out

    V = {s: rules(s) for s in SEEDS}
    rec["rules"] = V
    verdict = "SWAP" if all(V[s]["ALL_PASS"] for s in SEEDS) else "NO-SWAP"
    rec["VERDICT"] = verdict
    rec["verdict_rule"] = "prereg §3: SWAP iff BOTH F10 seeds satisfy S1..S5; any seed failing any rule ⇒ NO-SWAP naming the rule"
    rec["failing_by_seed"] = {s: V[s]["failing"] for s in SEEDS}
    rec["utc_end"] = iso(time.time())
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    for s in SEEDS:
        v = V[s]
        print(f"NEWS_STATS SEED {s}: S1={'PASS' if v['S1']['PASS'] else 'FAIL'}(vs OLD {v['S1']['OLD']['estimate_bps_per_day']:+.3f}, vs OLD_HOLD {v['S1']['OLD_HOLD']['estimate_bps_per_day']:+.3f} bps/d) "
              f"S2={'PASS' if v['S2']['PASS'] else 'FAIL'}(OLD {v['S2']['OLD']['segments_positive']}/3, OLD_HOLD {v['S2']['OLD_HOLD']['segments_positive']}/3) "
              f"S3={'PASS' if v['S3']['PASS'] else 'FAIL'}(maxDD {v['S3']['maxdd_5m_pre2026_path_mean']['NEWS']:.4f} vs OLD_HOLD {v['S3']['maxdd_5m_pre2026_path_mean']['OLD_HOLD']:.4f}) "
              f"S4={'PASS' if v['S4']['PASS'] else 'FAIL'}(halted {v['S4']['halted_paths']['NEWS']} vs OLD_HOLD {v['S4']['halted_paths']['OLD_HOLD']}) "
              f"S5={'PASS' if v['S5']['PASS'] else 'FAIL'} ALL={'PASS' if v['ALL_PASS'] else 'FAIL'}", flush=True)
    print(f"NEWS_STATS VERDICT={verdict} failing={rec['failing_by_seed']} unavailable={len(rec['unavailable'])} old_reproduction={repro} receipt_sha256={sha(OUT)}", flush=True)


if __name__ == "__main__":
    main()
