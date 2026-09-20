#!/usr/bin/env python3
"""fcf_tables.py — PREREG_fallback_counterfactual_2026-09-20 result tables, MAIN reading.

It does NOT define a single metric of its own. Every metric, the g convention, the daily aggregation, the moving-block bootstrap and
the paired estimator are IMPORTED from the certified renderer `bt_tables.py` (byte-identical copy, sha recorded), so that a number
here means exactly what the same-named number means in the certified baseline tables (F-prereg §3: "判官 = 认证生产路径 … 不另建判官").
  g        bt_tables.series_from_path L71   s["g"] = 1e4 * s["r"] / gm , r = navm1/navm0 - 1 , gm = 2.0 ; cell g = arithmetic mean
           over EVERY anchor of the cell (holds, halts and day-stop anchors included, none dropped) — bt_g_convention.py
  CAGR     bt_tables.cagr L111-116 on daily compounded returns ; Sharpe bt_tables.sharpe L119-123 (daily, x sqrt(365))
  maxDD    bt_tables.maxdd_4h L132 (4h NAV) and maxdd_5m L150 (5-minute NAV)
  paired   bt_tables.paired L245 — per-anchor paired delta on the same windows and the same fill seeds, 5-day moving-block
           bootstrap, B = 10,000. THE ONLY THING THIS DEVICE CHANGES is the rng seed, to the one the F prereg §3 fixes:
           rng = [20260920, arm_index] with arm_index from the arm's own name (F1 -> 1, F2 -> 2, F4 -> 4).

LEVEL. Every window here is RETROSPECTIVE LEVEL R (F-prereg §3): 2023-06-30 -> 2026-08-31. **Level R can only REFUSE, never promote.**
No result in this device's output may be called 有效 / valid / an improvement; a label is at most "not refuted at level R".
Holm control is NOT applied: the F prereg puts the family-wise control on the PROSPECTIVE level only.

E-0920-C. Every cell prints its anchor count n; cells with n = 0 are printed as null with n = 0 and never averaged into anything.

usage: fcf_tables.py <run_config.json> <out.json>
"""
import calendar, hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT

OUT = "/workspace/fallback_cf_2026-09-20"
ARM_INDEX = {"F1": 1, "F2": 2, "F3": 3, "F4a": 4, "F4b": 4}      # F-prereg §3 rng = [20260920, 臂序号]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(x): return calendar.timegm(time.strptime(x, "%Y-%m-%dT%H:%M:%SZ"))


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def load_arm(run_dir, tag, nseed):
    """every path file, sha-checked against its own json (the writer's own contract)"""
    fs = []
    for s in range(nseed):
        st = os.path.join(run_dir, f"PATH_{tag}_seed_{s:02d}")
        J = json.load(open(st + ".json"))
        got = sha(st + ".npz")
        assert J["npz_sha256"] == got, (st, got[:16], J["npz_sha256"][:16])
        fs.append((BT.series_from_path(dict(np.load(st + ".npz"))), got))
    paths = [f[0] for f in fs]
    return paths, BT.series_mean(paths), [f[1] for f in fs]


def main():
    CFG = json.load(open(sys.argv[1])); OUTP = sys.argv[2]
    nseed = int(CFG["paths_R"]); root = CFG["paths"]["pod_root"]
    frs = ts(CFG["window"]["full_recipe_start"])
    doc = {"device": "fcf_tables.py", "self_sha256": sha(os.path.abspath(__file__)),
           "bt_tables_sha256": sha(f"{HERE}/bt_tables.py"),
           "prereg": "docs/PREREG_fallback_counterfactual_2026-09-20.md (a964c2f9a)",
           "run_config": {"path": os.path.abspath(sys.argv[1]), "sha256": sha(sys.argv[1])},
           "LEVEL": "RETROSPECTIVE R — can only REFUSE, never promote (F-prereg §3). No result here may be written as 有效.",
           "multiplicity": "Holm is NOT applied: the F prereg controls the family at the PROSPECTIVE level only.",
           "reading": "MAIN (assumes the live watchdog §4-4 never fires); readings P and P2 are separate devices",
           "n_seeds": nseed, "utc": iso(time.time()), "arms": {}, "paired_vs_F0": {}}

    ARMS = {}
    for r in CFG["runs"]:
        arm = r["arm"].replace("OBJB_", "")
        d = os.path.join(root, "runs", r["tag"].replace("|", "_"))
        paths, mean, shas = load_arm(d, r["tag"].replace("|", "_"), nseed)
        ARMS[arm] = (paths, mean)
        doc["arms"][arm] = {"tag": r["tag"], "run_dir": d, "path_npz_sha256": shas, "role": r.get("role"), "cells": {}}

    A = ARMS["F0"][1]["A"]
    import bt_objb_targets as OT
    T0 = OT.load_targets(CFG["runs"][0]["targets"]["sources"], reading="scaled", arm="A0", n_sym=829)
    pos = {int(a): i for i, a in enumerate(T0["anchor"])}
    kind0 = np.array([T0["kind"][pos[int(a)]] for a in A], np.int8)
    fb = kind0 == 1
    for a in ARMS: assert np.array_equal(ARMS[a][1]["A"], A), a

    HIST = (A >= frs) & (A <= ts("2025-12-31T20:00:00Z"))
    RLEV = A >= frs
    cells = {"R_level_2023-06-30→2026-08-31": RLEV,
             "HIST_2023-06-30→2025-12-31 (the FINDING's window)": HIST,
             "fallback_subsample_R": fb & RLEV,
             "fallback_subsample_HIST": fb & HIST,
             "combo_subsample_R": (~fb) & RLEV,
             "combo_subsample_HIST": (~fb) & HIST,
             "PARTIAL_RECIPE_before_2023-06-30 (describe only)": A < frs}
    for nm, m in BT.year_cells(A, frs).items():
        cells["year " + nm] = m["mask"]
    doc["cell_definitions"] = {k: {"n_anchors": int(v.sum()),
                                   "first": iso(A[v][0]) if v.any() else None, "last": iso(A[v][-1]) if v.any() else None}
                               for k, v in cells.items()}
    doc["fallback_subsample_definition"] = ("anchors where the ARCHIVED (F0 = in-service) reading wrote the producer's king file, i.e. the "
                                            "preflight failed; identical across arms by construction (fcf_targets.py A3)")

    days_all = np.unique((A // 86400) * 86400)
    PM_CACHE = {}          # (arm, cell) -> [cell_metrics of each path]; computed once, reused by path_distribution and the paired-by-seed block

    def per_path(arm, nm, m):
        k = (arm, nm)
        if k not in PM_CACHE: PM_CACHE[k] = [BT.cell_metrics(p, m) for p in ARMS[arm][0]]
        return PM_CACHE[k]

    PDK = ("cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "worst_30d", "cvar5_daily", "g", "nav_return")
    for arm, (paths, mean) in ARMS.items():
        for nm, m in cells.items():
            o = BT.cell_metrics(mean, m)
            if o["n_anchors"]:
                pp = per_path(arm, nm, m)
                o["per_path"] = {k: {"median": BT.pct([x.get(k) for x in pp], 50), "p05": BT.pct([x.get(k) for x in pp], 5),
                                     "p95": BT.pct([x.get(k) for x in pp], 95), "n_paths": len(pp)} for k in PDK}
                if o["n_days"] >= 2:
                    # single-cell CI on g, the judge's own estimator (bt_tables.mean_ci, 5-day MBB, B = 10,000).
                    # rng = [20260920, 900 + arm index] — fixed here, before any number of this device was seen.
                    sd = (20260920, 900 + ARM_INDEX.get(arm, 0))
                    ci, _ = BT.mean_ci(A, mean["g"], m, days_all, block=5, B=10000, seed=sd)
                    o["g_ci"] = dict(ci, rng=list(sd), block_days=5, B=10000)
                else:
                    o["g_ci"] = {"UNAVAILABLE": "fewer than 2 distinct days in the cell", "n_days": o["n_days"]}
            doc["arms"][arm]["cells"][nm] = o

    for arm in ARMS:
        if arm == "F0": continue
        k = ARM_INDEX[arm]; seed = (20260920, k)
        doc["paired_vs_F0"][arm] = {"rng": list(seed), "block_days": 5, "B": 10000,
                                    "note": "paired per anchor on the same windows and the same fill seeds (F-prereg §3); level R ⇒ can only refuse"}
        for nm, m in cells.items():
            if int(m.sum()) < 2 or len(np.unique((A[m] // 86400))) < 3:
                doc["paired_vs_F0"][arm][nm] = {"n_anchors": int(m.sum()), "UNAVAILABLE": "fewer than 3 distinct days in the cell"}
                continue
            # A cell in which one arm's daily returns are IDENTICALLY ZERO has no defined Sharpe (0/0), and every bootstrap draw of
            # ΔSharpe is NaN, so bt_tables.paired raises. That is a real property of the arm, not a device failure: it happens where
            # an arm holds no book at all. It is recorded with its reason and its measured standard deviations, and the quantities that
            # ARE defined (Δg, ΔCAGR) are still computed with the judge's own estimators — never silently dropped, never coded as 0.
            _, ra_ = BT.daily(A[m], ARMS[arm][1]["r"][m]); _, rb_ = BT.daily(A[m], ARMS["F0"][1]["r"][m])
            sda, sdb = float(np.std(ra_, ddof=1)), float(np.std(rb_, ddof=1))
            if sda > 0 and sdb > 0:
                o = dict(BT.paired(ARMS[arm][1], ARMS["F0"][1], block=5, B=10000, seed=seed, mask=m), n_anchors=int(m.sum()))
            else:
                dg = ARMS[arm][1]["g"][m] - ARMS["F0"][1]["g"][m]
                ci, _ = BT.mean_ci(A, ARMS[arm][1]["g"] - ARMS["F0"][1]["g"], m, days_all, block=5, B=10000, seed=seed)
                o = {"n_anchors": int(m.sum()), "n_days": len(ra_), "block_days": 5, "B": 10000, "rng": list(seed),
                     "DEGENERATE_CELL": {"reason": "one arm's daily returns are identically zero in this cell, so its Sharpe is 0/0 and every "
                                                   "bootstrap draw of ΔSharpe is undefined. This is the arm holding NO book, not a missing "
                                                   "measurement and not a zero return by accident.",
                                         "daily_return_sd": {arm: sda, "F0": sdb},
                                         "which_arm_is_flat": [k for k, v in ((arm, sda), ("F0", sdb)) if v == 0.0]},
                     "d_sharpe": {"estimate": None, "ci95": None, "label": "UNAVAILABLE", "why": "Sharpe undefined for a flat arm"},
                     "d_cagr": {"estimate": float(BT.cagr(ra_) - BT.cagr(rb_)), "ci95": None, "label": "UNAVAILABLE",
                                "why": "reported as a point estimate only; the paired draw set is undefined in this cell"},
                     "d_g": {"estimate": float(dg.mean()), "ci95": ci["ci95"], "label": "point + CI from bt_tables.mean_ci on the paired "
                             "difference series (the judge's own estimator); no p-value in a degenerate cell", "n_draws_defined": ci["n_draws_defined"]}}
            # the prereg says "逐锚配对 Δ(同锚同成交路径)". BT.paired pairs per anchor on the MEAN path (the certified §3.5 estimator);
            # this second block pairs SEED BY SEED as well, so the per-fill-path spread is visible and not hidden by the mean.
            pa = per_path(arm, nm, m); pb = per_path("F0", nm, m)
            o["per_fill_path_delta"] = {"pairing": "paired by fill seed (seed s of this arm vs seed s of F0)", "n_seeds": len(pa)}
            for kk in ("g", "cagr", "sharpe_daily", "maxdd_4h", "maxdd_5m", "nav_return"):
                dd = [(x.get(kk) - y.get(kk)) for x, y in zip(pa, pb) if x.get(kk) is not None and y.get(kk) is not None]
                o["per_fill_path_delta"][kk] = ({"median": float(np.median(dd)), "p05": float(np.percentile(dd, 5)),
                                                 "p95": float(np.percentile(dd, 95)), "n_measured": len(dd), "n_population": len(pa),
                                                 "n_seeds_with_the_same_sign": int(sum(1 for v in dd if v > 0)) if dd else 0}
                                                if dd else {"n_measured": 0, "n_population": len(pa), "note": "no measurement — not 0"})
            doc["paired_vs_F0"][arm][nm] = o

    # ── PREREG §5 falsification checks, computed explicitly rather than left to the reader ──
    F = {}
    combo_H = doc["arms"]["F0"]["cells"]["combo_subsample_HIST"]
    F["naive_counterfactual_reference"] = {
        "what": "the FINDING's whole-window combo bucket g on HIST, recomputed here from F0 (which is bitwise the certified run)",
        "g": combo_H.get("g"), "n_anchors": combo_H.get("n_anchors"), "FINDING_value": 0.490,
        "reproduces_the_FINDING": (abs(combo_H.get("g", 0) - 0.490) < 0.001)}
    if "F1" in doc["arms"]:
        f1 = doc["arms"]["F1"]["cells"]["fallback_subsample_HIST"]
        ref = combo_H.get("g")
        ci = (f1.get("g_ci") or {}).get("ci95")
        F["lead_prior_F1_on_the_fallback_subsample_comes_in_BELOW_the_combo_bucket"] = {
            "prior": "the lead expected F1's g on the fallback subsample to be LOWER than the whole-window combo bucket (+0.490), because "
                     "those anchors are selected by a high model seat; the question was only how much lower",
            "F1_g_on_fallback_HIST": f1.get("g"), "n_anchors": f1.get("n_anchors"), "ci95": ci,
            "combo_bucket_reference": ref,
            "point_estimate_is_below_the_reference": (None if (f1.get("g") is None or ref is None) else bool(f1["g"] < ref)),
            "ci95_excludes_the_reference": (None if (ci is None or ref is None) else bool(ci[1] < ref or ci[0] > ref)),
            "reading_rule": "the reference +0.490 is itself an estimate from the same 32 paths, so 'CI excludes it' is a weaker statement than a "
                            "two-sample test; it is reported as a descriptive comparison, never as a decision"}
    for arm in ARMS:
        if arm == "F0": continue
        p = doc["paired_vs_F0"].get(arm, {}).get("fallback_subsample_HIST")
        if p and "UNAVAILABLE" not in p:
            F[f"mechanism_check_{arm}_vs_F0_on_the_fallback_subsample"] = {
                "d_g": p["d_g"]["estimate"], "ci95": p["d_g"]["ci95"], "label": p["d_g"]["label"], "n_anchors": p["n_anchors"],
                "falsified_shape": "the FINDING's mechanism is falsified if F1 is NOT above F0 here, or if an F4 arm sits at F0 rather than at F1"}
    doc["prereg_s5_falsification"] = F
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1, default=float); os.replace(OUTP + ".tmp", OUTP)
    print("FCF_TABLES written", OUTP, "sha256", sha(OUTP), flush=True)
    for nm in ("R_level_2023-06-30→2026-08-31", "HIST_2023-06-30→2025-12-31 (the FINDING's window)",
               "fallback_subsample_HIST", "combo_subsample_HIST"):
        print(f"  {nm}  n={doc['cell_definitions'][nm]['n_anchors']}")
        for arm in ARMS:
            c = doc["arms"][arm]["cells"][nm]
            if not c["n_anchors"]: print(f"    {arm:4s} n=0"); continue
            print(f"    {arm:4s} g {c['g']:+.4f}  cagr {c['cagr']:+.4f}  sharpe {c['sharpe_daily'] if c['sharpe_daily'] is None else round(c['sharpe_daily'], 3)}"
                  f"  maxdd4h {c['maxdd_4h']:+.4f}  turn/gross {c['turnover_over_gross']:.4f}  fee {c['fee']:+.4f}"
                  f"  daystops {c['day_stop_flattens']:.1f}  pnstops {c['per_name_stops']:.1f}  hold {c['hold_anchors']:.0f}")


if __name__ == "__main__":
    main()
