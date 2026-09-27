#!/usr/bin/env python3
"""l2n_judge.py — S1 verdict device (lead DECISION_RULE_nonfunding_sources_2026-09-27 §1 via AMENDMENT_L2_NC_population_2026-09-27 §3).
Committed before it is run. Two stages, run in this order by the executor:

  RESOLUTION  reads ONLY the resolution arm (within-anchor-permuted target + planted column): per seed x model, the mean within-anchor
              Spearman IC of the PLANT scores vs y_perm in pre-2026 (test years 2023-2025) and 2026, with its 95% block-bootstrap interval.
              A model is ELIGIBLE iff its PLANT lower bound > 0 in BOTH segments for BOTH seeds. No eligible model => RESOLUTION_FAIL (stop).
              The NULL arm (no planted column) is reported (expected: not detected).
  MAIN        (requires a RESOLUTION receipt with >= 1 eligible model)
              VOID gates (any failure => VOID, no verdict):
                * offset spectrum: mean within-anchor Spearman(score_A, y4[k + h]) for h in -3..3; the FORWARD peak (argmax |.| over h in 0..3,
                  L2 C6 convention inherited) must be at h = 0, for every seed x model;
                * shuffle-future: IC(score_A, SF_A) <= the p97.5 of its own null (200 within-anchor permutations of SF_A,
                  default_rng([20260927, 5, r])), every seed x model;
                * label regime: the build receipt's element-wise assertion (the build stops otherwise) is recorded.
              MAIN (target A_res): PASS iff some ELIGIBLE model m has, for BOTH seeds and BOTH segments, IC >= 0.015 and 95% lower > 0, and the
              pre-2026 and 2026 ICs have the same sign. Collapse guard sd(score)/sd(target) >= 0.02 for the passing model (both seeds).
              Descriptive only: target B_res ICs, per-year ICs, P_neg ICs, the L2 §7 decile statistics G / H / TB / G_med on the raw
              short P&L s = -1e4 r_A.
IC = mean over anchors (>= 10 finite rows) of Spearman(score, target); 95% interval by the L2 §7 block bootstrap (blocks = UTC day for
A, 3 days for B; B = 2,000 draws, default_rng([20260905, b])), computed on per-block IC sums and anchor counts.
usage: /workspace/venv/bin/python -B l2n_judge.py <whitelist> RESOLUTION|MAIN
"""
import os, sys, time, json
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

STAGE = sys.argv[2]; assert STAGE in ("RESOLUTION", "MAIN")
envrep = C.check_env(sys.argv[:2])
L2 = C.L2; OUT = f"{L2}/out"; REC = f"{L2}/receipts"; SEEDS = ("42", "2027"); MODELS = ("R", "L"); TH = 0.015
SEG = {"pre2026": (2023, 2024, 2025), "2026": (2026,)}
BR = json.load(open(f"{REC}/RECEIPT_L2N_build.json")); FR = json.load(open(f"{REC}/RECEIPT_L2N_fit.json"))


def anchor_ic(x, y, i, day):
    ok = np.isfinite(x) & np.isfinite(y); o = np.argsort(i[ok], kind="stable"); xi, yi, ii, di = x[ok][o], y[ok][o], i[ok][o], day[ok][o]
    b = np.flatnonzero(np.diff(ii)) + 1; st = np.concatenate([[0], b]); en = np.concatenate([b, [ii.size]])
    ic, dd, aa = [], [], []
    for a, e in zip(st, en):
        if e - a >= 10:
            v = spearmanr(xi[a:e], yi[a:e])[0]
            if np.isfinite(v): ic.append(v); dd.append(di[a]); aa.append(ii[a])
    return np.array(ic), np.array(dd, np.int64), np.array(aa, np.int64)


def summarise(ic, dd, T, years_of_anchor, seg_years):
    m = np.isin(years_of_anchor, seg_years)
    if m.sum() == 0: return None
    v, d = ic[m], dd[m]; ub, inv = B.block_ids(d, T); nd = ub.size
    s_ = np.bincount(inv, v, nd); c_ = np.bincount(inv, None, nd); Cm = B.draw_counts(nd)
    return {"IC": float(v.mean()), "ci95": B.boot_ci(Cm, s_, c_), "anchors": int(m.sum())}


def year_of_day(dd): return np.array([time.gmtime(int(x) * 86400).tm_year for x in dd], np.int64)


rec = {"device": "l2n_judge.py", "stage": STAGE, "self_sha256": C.sha256(os.path.abspath(__file__)), "env": envrep, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "build_receipt_sha256": C.sha256(f"{REC}/RECEIPT_L2N_build.json"), "fit_receipt_sha256": C.sha256(f"{REC}/RECEIPT_L2N_fit.json"), "cells": {}}
DATA = {}
for s in SEEDS:
    info = BR["per_seed"][s]; assert C.sha256(info["out"]) == info["out_sha256"]; DATA[s] = dict(np.load(info["out"]))

if STAGE == "RESOLUTION":
    elig = {m: True for m in MODELS}
    for s in SEEDS:
        r = FR["resolution"][s]; assert C.sha256(r["path"]) == r["sha256"]; Z = np.load(r["path"]); D = DATA[s]
        i = D["i"].astype(np.int64); day = D["day"].astype(np.int64)
        for m in MODELS:
            for arm in ("PLANT", "NULL"):
                ic, dd, _ = anchor_ic(Z[f"p_{m}_{arm}"], Z["y_perm"], i, day); ya = year_of_day(dd)
                cell = {k: summarise(ic, dd, "A", ya, v) for k, v in SEG.items()}
                rec["cells"][f"s{s}|{m}|{arm}"] = cell
                if arm == "PLANT":
                    det = all(cell[k] is not None and cell[k]["ci95"][0] > 0 for k in SEG); cell["detected"] = det; elig[m] &= det
                print(f"RESOLUTION s{s} {m} {arm}: " + json.dumps({k: (None if v is None else {"IC": round(v['IC'], 4), "ci95": [round(x, 4) for x in v['ci95']]}) for k, v in cell.items() if k in SEG}), flush=True)
    rec["eligible_models"] = [m for m in MODELS if elig[m]]
    rec["VERDICT"] = "RESOLUTION_OK" if rec["eligible_models"] else "RESOLUTION_FAIL"
else:
    RJ = json.load(open(f"{REC}/RECEIPT_L2N_judge_RESOLUTION.json")); assert RJ["VERDICT"] == "RESOLUTION_OK"; rec["resolution_receipt_sha256"] = C.sha256(f"{REC}/RECEIPT_L2N_judge_RESOLUTION.json")
    elig = RJ["eligible_models"]; void = []
    for s in SEEDS:
        D = DATA[s]; O = np.load(FR["out"][s]["path"]); assert C.sha256(FR["out"][s]["path"]) == FR["out"][s]["sha256"]
        i = D["i"].astype(np.int64); day = D["day"].astype(np.int64); shifts = list(D["shiftA"])
        for m in MODELS:
            p = O[f"p_{m}_A"]
            spec = {}
            for c, h in enumerate(shifts):
                ic, _, _ = anchor_ic(p, D["SA"][:, c], i, day); spec[int(h)] = float(ic.mean())
            fwd = [h for h in (0, 1, 2, 3) if h in spec]; peak = max(fwd, key=lambda h: abs(spec[h]))
            ic_sf, _, _ = anchor_ic(p, D["SF_A"], i, day); sf = float(ic_sf.mean())
            nulls = []
            ok = np.isfinite(D["SF_A"]); idx = np.flatnonzero(ok); o = idx[np.argsort(i[idx], kind="stable")]; b = np.flatnonzero(np.diff(i[o])) + 1; segs = np.split(o, b)
            for r in range(200):
                y2 = np.full(i.size, np.nan)
                for sg in segs:
                    if sg.size: y2[sg] = D["SF_A"][sg][np.random.default_rng([20260927, 5, r, int(i[sg[0]])]).permutation(sg.size)]
                v, _, _ = anchor_ic(p, y2, i, day); nulls.append(float(v.mean()))
            p975 = float(np.percentile(nulls, 97.5))
            leak = {"spectrum": spec, "forward_peak_h": int(peak), "spectrum_ok": peak == 0, "shuffle_future_IC": sf, "shuffle_future_null_p97.5": p975,
                    "shuffle_future_ok": sf <= p975}
            if not (leak["spectrum_ok"] and leak["shuffle_future_ok"]): void.append(f"s{s}|{m}")
            cell = {"leakage": leak}
            for T in ("A", "B"):
                ic, dd, _ = anchor_ic(O[f"p_{m}_{T}"], D[f"u{T}_res"], i, day); ya = year_of_day(dd)
                cell[T] = {k: summarise(ic, dd, T, ya, v) for k, v in SEG.items()}
                cell[T]["by_year"] = {str(y): summarise(ic, dd, T, ya, (y,)) for y in B.TEST_YEARS}
            pn = D["pneg"].astype(bool); icn, ddn, _ = anchor_ic(np.where(pn, p, np.nan), D["uA_res"], i, day); yan = year_of_day(ddn)
            cell["A_Pneg"] = {k: summarise(icn, ddn, "A", yan, v) for k, v in SEG.items()}
            okr = np.isfinite(p) & np.isfinite(D["uA_res"]); cell["sd_ratio"] = float(np.std(p[okr]) / np.std(D["uA_res"][okr]))
            # L2 §7 decile statistics (descriptive), raw short P&L
            sA = -1e4 * D["rA"]; okd = np.isfinite(p) & np.isfinite(sA)
            idx, a, sizes, uniq = B.anchor_index(i, okd & (np.bincount(i[okd], minlength=i.max() + 1)[i] >= B.MIN_ANCHOR))
            if idx.size:
                top, bot, _ = B.decile_sets(p[idx], a, sizes, D["n"][idx].astype(np.int64)); Dd, Hh = B.anchor_stats(sA[idx], a, sizes, top, bot)
                cell["L2_decile_descriptive"] = {"G": float(np.nanmean(Dd)), "H": float(np.nanmean(Hh)), "TB": float(np.nanmean(Dd - Hh)),
                                                 "G_med": float(np.nanmean(B.anchor_median_stat(sA[idx], a, sizes, top)))}
            rec["cells"][f"s{s}|{m}"] = cell
            print(f"MAIN s{s} {m}: leak {json.dumps({k: leak[k] for k in ('forward_peak_h', 'spectrum_ok', 'shuffle_future_ok')})} A " +
                  json.dumps({k: (None if v is None else {'IC': round(v['IC'], 4), 'ci95': [round(x, 4) for x in v['ci95']]}) for k, v in cell['A'].items() if k in SEG}) +
                  f" sd_ratio {cell['sd_ratio']:.4f}", flush=True)
    rec["label_regime_assertion"] = "element-wise in l2n_build (build would have stopped otherwise); build receipt sha recorded"
    if void:
        rec["VERDICT"] = "VOID"; rec["void_cells"] = void
    else:
        passing = []
        for m in elig:
            ok = True
            for s in SEEDS:
                A = rec["cells"][f"s{s}|{m}"]["A"]
                for k in SEG:
                    ok &= A[k] is not None and A[k]["IC"] >= TH and A[k]["ci95"][0] > 0
                ok &= A["pre2026"] is not None and A["2026"] is not None and np.sign(A["pre2026"]["IC"]) == np.sign(A["2026"]["IC"])
                ok &= rec["cells"][f"s{s}|{m}"]["sd_ratio"] >= 0.02
            if ok: passing.append(m)
        rec["passing_models"] = passing
        rec["VERDICT"] = ("PASS (S1 IC gate; next = a book-layer prereg written by the lead, replacement action, risk endpoints)" if passing else "FAIL")
p = f"{REC}/RECEIPT_L2N_judge_{STAGE}.json"; C.jdump(rec, p); assert json.load(open(p))["self_sha256"] == rec["self_sha256"]
print(f"L2N_JUDGE_{STAGE} VERDICT={rec['VERDICT']} {C.sha256(p)[:16]}", flush=True)
