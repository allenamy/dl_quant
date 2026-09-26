#!/usr/bin/env python3
"""alloc_judge.py — the verdict device for docs/DECISION_RULE_combination_layer_2026-09-26.md (lead, 9d645e2dd / 8a3a1e208).
Committed BEFORE any reading it produces. Three modes, one measurement:

  measurement  d_k,seg = dbar(arm, seed k) - dbar(NC reference, seed k)  with the FROZEN news_stats.py (7141ba42) load_cell / seg_mask /
               full_days / dbar (bt_tables 892ba66b, bt_driver_lib ba3bc261 asserted by news_stats.DEV). Segments: pre2026 (frozen SEG),
               2026 extended to 2026-09-18T20Z (lead revision 3), 2026_frozen_truncated alongside, and FULL = the pre2026 and 2026 daily
               series concatenated (1,176 days). D_seg = mean over the seeds present; the seed-averaged daily series x_seg is the MBB input.
               SE_seg = max( MBB30_SE(x_seg), sd_k(d_k,seg)/sqrt(n_seeds) )  [rule §1]; with one seed the second term is undefined and SE
               is the MBB term alone. MBB = bt_tables.mbb_indices(n, 30, 10000, (20260923, 1)); MBB_SE = sd(ddof=1) of the B resampled
               means; the 95% interval = its 2.5/97.5 percentiles.
  --mode IDENTITY  zero-point control of THIS judge (TEAM_PROTOCOL §10-d): the in-service arm through the alloc chain vs its reference,
                 s42. PASS iff D == 0.0 exactly in every segment (the engine identity already proved the PATH arrays equal).
  --mode R       red control (fundflip, s42).  PASS iff pre2026 D < 0 AND 2026 D < 0 AND both MBB 95% upper bounds < 0 (rule §2-0).
  --mode O       ceiling control (oracle, s42). RUN_SEAT_ARMS = NOT( pre2026 D < 3.84*SE AND 2026 D < 3.84*SE ), SE from O's own
                 paired series (rule §2-1). O is never admissible.
  --mode FAMILY  one candidate arm, seeds {42, 2027, 7} (rule §3). Return track for A1/A2/A3; non-inferiority track for A3 only
                 (--noninf-mech-corr <2026 median F10/King weight corr from the footprint receipt>); A4 = descriptive (never PASS).
Required reports (rule §5) that are computed here: four channels (pnl/car/cst/unk bps/anchor), turnover, hold/halt counts, per-year
dbar table, every seed listed, maxDD 5m path means. BTC daily beta is NOT computed here (no BTC series in the engine output): reported by
a separate named step before the family verdict is sent; its absence is written into every output as PENDING.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B alloc_judge.py PATH,HOME,LC_CTYPE --mode IDENTITY|R|O|FAMILY
         --arm <rule>_<mix> --seeds 42[,2027,7] [--arm-class A1|A2|A3|A4] [--noninf-mech-corr X] --out <json>
"""
import os, sys, json, math, hashlib, time
import numpy as np
ENG = "/dev/shm/news2_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
CELLS = "/workspace/alloc_2026-09-26/cells"
REF = "/workspace/dlarch_2026-09-24/chain/ref_nc_s{s}X/runs/DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE"
REF_TAG = "DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE"
B = 10000; RNG = (20260923, 1); BLOCK = 30; MDE_K = 3.84
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def arg(args, k, d=None): return args[args.index(k) + 1] if k in args else d


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
    args = sys.argv[2:]; mode = arg(args, "--mode"); armname = arg(args, "--arm"); out = arg(args, "--out")
    seeds = [int(x) for x in arg(args, "--seeds").split(",")]; aclass = arg(args, "--arm-class")
    assert mode in ("IDENTITY", "R", "O", "FAMILY")
    if mode == "IDENTITY": assert armname == "inservice_shared" and seeds == [42]
    if mode == "R": assert armname == "inservice_fundflip" and seeds == [42]
    if mode == "O": assert armname == "oracle_shared" and seeds == [42]
    if mode == "FAMILY": assert sorted(seeds) == [7, 42, 2027] and aclass in ("A1", "A2", "A3", "A4")
    assert sha(f"{ENG}/news_stats.py") == NS_SHA, "frozen judge drifted"
    import news_stats as S, bt_tables as BT, bt_driver_lib as DL
    for f, s in S.DEV.items(): assert sha(os.path.join(ENG, f)) == s, f"device sha {f}"
    S.BT, S.DL = BT, DL
    seg = {"pre2026": S.SEG["pre2026"], "2026": ("2026-01-01T00:00:00Z", "2026-09-18T20:00:00Z"), "2026_frozen_truncated": S.SEG["2026"],
           "2023H2": S.SEG["2023H2"], "2024": S.SEG["2024"], "2025": S.SEG["2025"]}
    cells = {}; A = None
    for s in seeds:
        tag = f"ALLOC_{armname}_s{s}X_scaled_rule_raw_UAFE"; d = f"{CELLS}/{armname}_s{s}/runs/{tag}"
        pa, fa = S.load_cell(d, tag); pr, fr = S.load_cell(REF.format(s=s), REF_TAG.format(s=s))
        assert np.array_equal(pa[0]["A"], pr[0]["A"]); A = pa[0]["A"] if A is None else A; assert np.array_equal(A, pa[0]["A"])
        cells[s] = {"arm": pa, "ref": pr, "arm_dir": d, "ref_dir": REF.format(s=s),
                    "arm_npz_sha256": [f["npz_sha256"] for f in fa], "ref_npz_sha256": [f["npz_sha256"] for f in fr]}
    masks = {k: S.seg_mask(A, a, b) for k, (a, b) in seg.items()}; days = {k: S.full_days(A, masks[k]) for k in seg}
    per = {}; xs = {}
    for k in seg:
        per[k] = {}; xl = []
        for s in seeds:
            x, _ = S.dbar(cells[s]["arm"], cells[s]["ref"], masks[k], days[k]); xl.append(x)
            ma, mr = S.BT.series_mean(cells[s]["arm"]), S.BT.series_mean(cells[s]["ref"]); m = masks[k]
            per[k][s] = {"d_bps_per_day": float(1e4 * x.mean()),
                         "maxdd_5m_path_mean": {"arm": float(np.mean([BT.maxdd_5m(p, m) for p in cells[s]["arm"]])),
                                                "ref": float(np.mean([BT.maxdd_5m(p, m) for p in cells[s]["ref"]]))},
                         "channels_bps_per_anchor": {c: {"arm": float(ma[c][m].mean()), "ref": float(mr[c][m].mean())} for c in ("g", "pnl", "car", "cst", "unk")},
                         "turnover_over_gross": {"arm": float(ma["tau"][m].mean()), "ref": float(mr["tau"][m].mean())},
                         "hold_anchors": {"arm": float(ma["hold"][m].sum()), "ref": float(mr["hold"][m].sum())},
                         "halt_anchors": {"arm": float(ma["halt"][m].sum()), "ref": float(mr["halt"][m].sum())}}
        xs[k] = np.stack(xl).mean(0)
    xs["FULL"] = np.concatenate([xs["pre2026"], xs["2026"]])
    per["FULL"] = {s: {"d_bps_per_day": float(1e4 * np.concatenate([S.dbar(cells[s]["arm"], cells[s]["ref"], masks[k], days[k])[0] for k in ("pre2026", "2026")]).mean())} for s in seeds}
    stat = {}
    for k, x in xs.items():
        idx = BT.mbb_indices(len(x), BLOCK, B, RNG); mb = x[idx].mean(1)
        mbb_se = float(1e4 * mb.std(ddof=1)); dk = np.array([per[k][s]["d_bps_per_day"] for s in seeds])
        seed_se = float(dk.std(ddof=1) / math.sqrt(len(dk))) if len(dk) > 1 else None
        se = max(mbb_se, seed_se) if seed_se is not None else mbb_se
        stat[k] = {"n_days": int(len(x)), "D_bps_per_day": float(1e4 * x.mean()), "mbb30_se": mbb_se, "seed_se": seed_se, "SE": se,
                   "mbb30_ci95": [float(1e4 * np.percentile(mb, 2.5)), float(1e4 * np.percentile(mb, 97.5))],
                   "d_k": {str(s): float(v) for s, v in zip(seeds, dk)}, "n_seeds_positive": int((dk > 0).sum())}
    V = {"mode": mode}
    P, T = stat["pre2026"], stat["2026"]
    if mode == "IDENTITY":
        ok = all(v["D_bps_per_day"] == 0.0 for v in stat.values())
        V.update(VERDICT="PASS" if ok else "FAIL", rule="D == 0.0 exactly in every segment")
    elif mode == "R":
        ok = P["D_bps_per_day"] < 0 and T["D_bps_per_day"] < 0 and P["mbb30_ci95"][1] < 0 and T["mbb30_ci95"][1] < 0
        V.update(VERDICT="PASS" if ok else "FAIL_FAMILY_STOPS", rule="pre2026 D<0 & 2026 D<0 & both MBB95 upper<0")
    elif mode == "O":
        mde = {k: MDE_K * stat[k]["SE"] for k in ("pre2026", "2026")}
        below = {k: stat[k]["D_bps_per_day"] < mde[k] for k in mde}
        run = not (below["pre2026"] and below["2026"])
        V.update(MDE80=mde, O_below_MDE80=below, RUN_SEAT_ARMS=bool(run),
                 VERDICT=("RUN_A1_A2_A3_A4" if run else "RUN_A3_A4_ONLY"), rule="O-NC < 3.84*SE in BOTH segments => seat arms A1, A2 not run")
    else:
        F = stat["FULL"]
        dd_ok = all(np.mean([per[k][s]["maxdd_5m_path_mean"]["arm"] for s in seeds]) >= np.mean([per[k][s]["maxdd_5m_path_mean"]["ref"] for s in seeds]) - 0.03
                    for k in ("pre2026", "2026"))
        main = F["D_bps_per_day"] >= 3 * F["SE"] and sum(per["FULL"][s]["d_bps_per_day"] > 0 for s in seeds) >= 2
        both = P["D_bps_per_day"] >= 0 and T["D_bps_per_day"] >= 0
        reject = any(stat[k]["D_bps_per_day"] < 0 and stat[k]["mbb30_ci95"][1] < 0 for k in ("pre2026", "2026"))
        ret = {"main_full_ge_3SE_and_2of3": bool(main), "both_segments_ge_0": bool(both), "dd_guard": bool(dd_ok)}
        if aclass == "A4":
            verdict = "DESCRIPTIVE_NOT_ADMISSIBLE"
        elif main and both and dd_ok:
            verdict = "RECOMMEND_TO_USER (return track; F10 not retrained for the new seats/structure -- full-pipeline confirmation required)"
        elif reject:
            verdict = "REJECT"
        elif F["D_bps_per_day"] > 0:
            verdict = "UNDECIDED"
        else:
            verdict = "NOT_RECOMMENDED (no segment rejects; full-window point estimate <= 0)"
        V.update(return_track=ret, VERDICT_return_track=verdict)
        if aclass == "A3":
            mc = arg(args, "--noninf-mech-corr"); assert mc is not None, "A3 needs the footprint's 2026 F10/King weight corr"
            ni = all(stat[k]["D_bps_per_day"] >= -max(0.5, 3.5 * stat[k]["SE"]) for k in ("pre2026", "2026"))
            mech = float(mc) <= 0.80
            V.update(noninferiority_track={"both_segments_noninferior": bool(ni), "mechanism_corr_2026_median": float(mc), "mechanism_le_0.80": bool(mech),
                                           "dd_guard": bool(dd_ok)},
                     VERDICT_noninferiority_track=("DIAGNOSABILITY_IMPROVEMENT_AND_NONINFERIOR" if (ni and mech and dd_ok) else "NOT_MET"))
    rec = {"device": "alloc_judge.py", "self_sha256": sha(os.path.abspath(__file__)), "decision_rule": "docs/DECISION_RULE_combination_layer_2026-09-26.md @ 9d645e2dd/8a3a1e208",
           "frozen_judge_sha256": NS_SHA, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arm": armname, "arm_class": aclass, "seeds": seeds,
           "segments": seg, "stat": stat, "per_seed": {k: {str(s): v for s, v in d.items()} for k, d in per.items()},
           "cells": {str(s): {k: v for k, v in c.items() if k not in ("arm", "ref")} for s, c in cells.items()},
           "btc_daily_beta": "PENDING (separate named step before the family verdict is sent)", "verdict": V}
    json.dump(rec, open(out + ".tmp", "w"), indent=1, default=float); os.replace(out + ".tmp", out)
    assert json.load(open(out))["self_sha256"] == rec["self_sha256"]
    print(f"ALLOC_JUDGE mode={mode} arm={armname} " + json.dumps({k: round(v["D_bps_per_day"], 3) for k, v in stat.items()}) + " VERDICT=" +
          str(V.get("VERDICT", V.get("VERDICT_return_track"))), flush=True)


if __name__ == "__main__":
    main()
