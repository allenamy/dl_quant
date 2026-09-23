#!/usr/bin/env python3
"""s3_compare_local.py — R10 A.4-5 stage 3, LOCAL Mac, numpy only: PRODUCTION beta (S1, producer cache) vs EVALUATION beta (S2, certified
raw table), name by name, on the same 33 anchors and the same 180-bar windows. No return / PnL / Sharpe quantity is computed.

Definitions (fixed before reading any number):
  estimated (prod) = n_obs_prod >= 120 and name != BTCUSDT and the name has a cache column (compute's rule); (eval) = m2_lib EST.
  dbeta = beta_prod - beta_eval on names estimated on BOTH sides (BTCUSDT excluded: 1 by definition on both).
  a name missing from a side's symbol axis is reported as MISSING, never as a beta.
  beta_exec(side) = sum_i w_i * beta_side_i, w = the published target_live weights / sum|w| (gross units), every weight name, fallback
  names at the side's own formula value (1.0).
  reshape approximation (NOT the executor): w' = w - mean(w over the non-zero names) on the non-zero names, then w'' = w' / sum|w'|;
  no held positions, no untradable pops, no clamp, no venue cap.
  hedge = -beta_exec; delta_hedge (gross units) = -(beta_exec_prod - beta_exec_eval); lots = hedge * G / P_BTC(A) / 0.001 with P_BTC from
  the certified table; the rounded order uses round_qty's convention (floor toward zero, executor patch L391) as primary and nearest as a
  second reading, both from a zero BTC position.
usage: /usr/bin/python3 -B s3_compare_local.py <out_root>
"""
import csv
import hashlib
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
OUT = os.path.abspath(sys.argv[1])
W = OUT + "/work"
S1N, S1J, S2N, S2J = W + "/S1_prod_local.npz", W + "/S1_prod_local.json", W + "/S2_eval_pod2.npz", W + "/S2_eval_pod2.json"
LOT, GS = 0.001, (10000.0, 20000.0)
BTC = "BTCUSDT"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def utc(t):
    return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


FAILS = []
checks = []


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    print("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:200] if detail is not None else "", flush=True)
    if not ok:
        FAILS.append(name)


s1j, s2j = json.load(open(S1J)), json.load(open(S2J))
check("s1_npz_sha_matches_s1_receipt", sha(S1N) == s1j["outputs"]["npz_sha256"])
check("s2_npz_sha_matches_s2_receipt", sha(S2N) == s2j["outputs"]["npz_sha256"])
check("s1_s2_no_failures", not s1j["failed"] and not s2j["failed"])
P, E = np.load(S1N, allow_pickle=False), np.load(S2N, allow_pickle=False)
print("S1 keys", P.files)
print("S2 keys", E.files)
AN = P["anchors"].astype(np.int64)
check("same_anchor_axis", np.array_equal(AN, E["anchors"].astype(np.int64)), len(AN))
NM = [str(s) for s in P["names"]]
CS = [str(s) for s in P["cache_syms"]]
SY = [str(s) for s in E["symbols"]]
ccol = {s: j for j, s in enumerate(CS)}
ecol = {s: j for j, s in enumerate(SY)}
UNI = json.loads(str(P["universe_json"]))
WTS = json.loads(str(P["weights_json"]))
check("same_bar_axis", np.array_equal(P["Tb"], E["Tb"]))

# ── symbol mapping ──
uni_union = sorted(set(n for A in AN for n in UNI[str(A)]) | {BTC})
mapping = {"cache_axis_len": len(CS), "cert_axis_len": len(SY), "cache_axis_eq_cert_axis_same_order": CS == SY,
           "cache_minus_cert": sorted(set(CS) - set(SY)), "cert_minus_cache": sorted(set(SY) - set(CS)),
           "universe_union_size": len(uni_union),
           "universe_in_both_exact": sum(1 for n in uni_union if n in ccol and n in ecol),
           "universe_absent_from_cert": [n for n in uni_union if n not in ecol],
           "universe_absent_from_cache": [n for n in uni_union if n not in ccol],
           "universe_identical_across_anchors": len(set(json.dumps(UNI[str(A)]) for A in AN)) == 1}
unmatched = mapping["universe_absent_from_cert"] + mapping["universe_absent_from_cache"]
near = {}
for n in unmatched:
    base = n.replace("1000000", "").replace("1000", "").replace("USDT", "")
    near[n] = [s for s in SY + CS if base and base in s and s != n][:6]
mapping["near_matches_for_unmatched"] = near

bp, npr, inf = P["beta_prod"], P["nobs_prod"], P["in_field"]
WT = P["weight"]
be, ne, ee, re_ = E["beta_eval"], E["nobs_eval"], E["est_eval"], E["raw_eval"]
Tb = P["Tb"]; R4c, Vc = P["R4_cache"], P["V_cache"]; R4e, Ve = E["R4_cert"], E["V_cert"]
ff, lf = E["first_fin"], E["last_fin"]
px = E["btc_px"].astype(np.float64)
clip_ts, clip_col = P["clip_ts"], P["clip_col"]


def stats(d, names, anchors_of=None):
    d = np.asarray(d, np.float64)
    if len(d) == 0:
        return {"n": 0}
    a = np.abs(d)
    k = int(np.argmax(a))
    out = {"n": int(len(d)), "median": float(np.median(d)), "p5": float(np.percentile(d, 5)), "p95": float(np.percentile(d, 95)),
           "mean": float(d.mean()), "median_abs": float(np.median(a)), "p95_abs": float(np.percentile(a, 95)),
           "max_abs": float(a[k]), "max_abs_signed": float(d[k]), "max_abs_name": names[k],
           "n_abs_gt_0.05": int((a > 0.05).sum()), "n_abs_gt_0.1": int((a > 0.1).sum()), "n_abs_gt_0.5": int((a > 0.5).sum()),
           "n_abs_gt_1e-9": int((a > 1e-9).sum()), "max_abs_among_le_1e-9": float(a[a <= 1e-9].max()) if (a <= 1e-9).any() else None,
           "names_abs_gt_1e-9": sorted(set(names[i] for i in np.nonzero(a > 1e-9)[0]))}
    if anchors_of is not None:
        out["max_abs_anchor"] = anchors_of[k]
    return out


def bar_diag(n, A):
    """why a name's two betas differ at A: bar-level validity / value disagreement over A's 180-bar window."""
    jc, je = ccol.get(n), ecol.get(n)
    hi = int(np.nonzero(Tb == A)[0][0]); lo = hi - 179
    out = {}
    if jc is None or je is None:
        return {"missing_side": "cache" if jc is None else "cert"}
    vc, ve = Vc[lo:hi + 1, jc], Ve[lo:hi + 1, je]
    vbc, vbe = Vc[lo:hi + 1, ccol[BTC]], Ve[lo:hi + 1, ecol[BTC]]
    both = vc & ve
    dr = np.abs(R4c[lo:hi + 1, jc] - R4e[lo:hi + 1, je])
    out.update({"bars_valid_cache": int(vc.sum()), "bars_valid_cert": int(ve.sum()), "cache_only_valid": int((vc & ~ve).sum()),
                "cert_only_valid": int((~vc & ve).sum()), "btc_bars_valid_cache": int(vbc.sum()), "btc_bars_valid_cert": int(vbe.sum()),
                "bars_both_valid": int(both.sum()),
                "bars_abs_r4_diff_gt_1e-3": int((dr[both] > 1e-3).sum()), "max_abs_r4_diff": float(dr[both].max()) if both.any() else None,
                "first_fin_cert": utc(ff[je]) if ff[je] >= 0 else int(ff[je]), "last_fin_cert": utc(lf[je]),
                "window_first_bar_start": utc(Tb[lo] - 14400),
                "clip_cells_in_window": int(sum(1 for t, c in zip(clip_ts, clip_col) if CS[int(c)] == n and Tb[lo] - 14400 <= t <= A))})
    return out


rows_csv = []
per_anchor = {}
pool_d, pool_n, pool_a, pool_dw, pool_nw, pool_aw = [], [], [], [], [], []
fb_mismatch = {"prod_fallback_eval_estimated": [], "prod_estimated_eval_fallback": []}
missing_report = {}
bound_hits = {"prod_at_clip_bound": [], "eval_at_clip_bound": []}
lots_tab = []
for a_i, A in enumerate(AN.tolist()):
    names = [n for n_i, n in enumerate(NM) if inf[a_i, n_i]]
    uni = UNI[str(A)]
    check(f"field_names_eq_BTC_plus_universe.{utc(A)}", set(names) == set(uni) | {BTC}, len(names))
    w_raw = {n: float(v) for n, v in WTS[str(A)].items()}
    g = sum(abs(v) for v in w_raw.values())
    w = {n: v / g for n, v in w_raw.items()}
    d_all, n_all, d_w, n_w = [], [], [], []
    miss = {"weight_names_missing_cert": [n for n in w if n not in ecol], "weight_names_missing_cache": [n for n in w if n not in ccol],
            "universe_missing_cert": [n for n in uni if n not in ecol], "universe_missing_cache": [n for n in uni if n not in ccol]}
    bprod, beval = {}, {}
    n_fbm = 0
    for n in names:
        n_i = NM.index(n)
        b1, o1 = float(bp[a_i, n_i]), int(npr[a_i, n_i])
        est1 = (n != BTC) and (n in ccol) and o1 >= 120
        bprod[n] = b1
        je = ecol.get(n)
        if je is None:
            rows_csv.append([utc(A), n, 1, w.get(n, 0.0), b1, o1, int(est1), "", "", "", "", "", "MISSING_CERT"])
            continue
        b2, o2, est2, r2 = float(be[a_i, je]), int(ne[a_i, je]), bool(ee[a_i, je]), float(re_[a_i, je])
        beval[n] = b2
        if n == BTC:
            check(f"btc_beta_one_both.{utc(A)}", b1 == 1.0 and b2 == 1.0)
            rows_csv.append([utc(A), n, 1, w.get(n, 0.0), b1, o1, 0, b2, o2, 0, "", "", "BTC"])
            continue
        if b1 in (-1.0, 4.0) and est1:
            bound_hits["prod_at_clip_bound"].append([utc(A), n, b1])
        if b2 in (-1.0, 4.0) and est2:
            bound_hits["eval_at_clip_bound"].append([utc(A), n, b2, r2])
        tag = ""
        if est1 and est2:
            d = b1 - b2
            d_all.append(d); n_all.append(n)
            pool_d.append(d); pool_n.append(n); pool_a.append(utc(A))
            if w.get(n, 0.0) != 0.0:
                d_w.append(d); n_w.append(n); pool_dw.append(d); pool_nw.append(n); pool_aw.append(utc(A))
            dd = d
        else:
            dd = ""
            if est1 != est2:
                n_fbm += 1
                tag = "FALLBACK_MISMATCH"
                key = "prod_fallback_eval_estimated" if est2 else "prod_estimated_eval_fallback"
                fb_mismatch[key].append({"anchor": utc(A), "name": n, "weight": w.get(n, 0.0), "beta_prod": b1, "nobs_prod": o1,
                                         "beta_eval": b2, "nobs_eval": o2, "raw_eval": r2, "why": bar_diag(n, A)})
            else:
                tag = "FALLBACK_BOTH"
        rows_csv.append([utc(A), n, 1, w.get(n, 0.0), b1, o1, int(est1), b2, o2, int(est2), r2 if np.isfinite(r2) else "", dd, tag])
    missing_report[utc(A)] = miss
    # beta_exec — every weight name must have a beta on the side; a missing one is reported and the side's beta_exec is None
    def bexec(ww, bb):
        if any(n not in bb for n in ww):
            return None
        return float(sum(v * bb[n] for n, v in ww.items()))
    nz = {n: v for n, v in w.items() if v != 0.0}
    mu = float(np.mean(list(nz.values())))
    w1 = {n: v - mu for n, v in nz.items()}
    g1 = sum(abs(v) for v in w1.values())
    w2 = {n: v / g1 for n, v in w1.items()}
    rec_a = {}
    for lab, ww in (("published", w), ("reshape_approx", w2)):
        xp, xe = bexec(ww, bprod), bexec(ww, beval)
        dx = (xp - xe) if (xp is not None and xe is not None) else None
        r = {"beta_exec_prod": xp, "beta_exec_eval": xe, "delta_beta_exec": dx,
             "rel_diff": (dx / abs(xe)) if (dx is not None and xe) else None,
             "delta_hedge_gross_units": (-dx if dx is not None else None)}
        for G in GS:
            if dx is None:
                continue
            hp, he = -xp * G / px[a_i] / LOT, -xe * G / px[a_i] / LOT
            r[f"G{int(G)}"] = {"delta_hedge_usdt": -dx * G, "delta_lots_unrounded": hp - he,
                               "lots_prod_trunc": int(np.trunc(hp)), "lots_eval_trunc": int(np.trunc(he)),
                               "lots_prod_nearest": int(np.round(hp)), "lots_eval_nearest": int(np.round(he)),
                               "order_differs_ge1lot_trunc": int(np.trunc(hp)) != int(np.trunc(he)),
                               "order_differs_ge1lot_nearest": int(np.round(hp)) != int(np.round(he))}
        rec_a[lab] = r
    net_pub = sum(w.values())
    per_anchor[utc(A)] = {"n_names_field": len(names), "n_weights": len(w), "gross_file": g, "net_published_gross_units": net_pub,
                          "n_compared": len(d_all), "dbeta": stats(d_all, n_all), "n_compared_weighted": len(d_w),
                          "dbeta_weighted": stats(d_w, n_w), "n_fallback_mismatch": n_fbm,
                          "n_prod_estimated": int(sum(1 for n in names if n != BTC and n in ccol and int(npr[a_i, NM.index(n)]) >= 120)),
                          "n_eval_estimated_in_universe": int(sum(1 for n in names if n != BTC and n in ecol and bool(ee[a_i, ecol[n]]))),
                          "btc_px_cert": float(px[a_i]), "beta_exec": rec_a, "missing": miss}
check("no_universe_name_missing_either_side", all(not any(v.values()) for v in missing_report.values()))

pooled = {"dbeta_all_compared": stats(pool_d, pool_n, pool_a), "dbeta_weight_nonzero": stats(pool_dw, pool_nw, pool_aw),
          "note": "pooled over 33 anchors whose 180-bar windows overlap by up to 179 bars: the pairs are NOT independent draws"}
nonw = {}
for lab in ("published", "reshape_approx"):
    dd = np.array([per_anchor[k]["beta_exec"][lab]["delta_beta_exec"] for k in per_anchor], np.float64)
    xp = np.array([per_anchor[k]["beta_exec"][lab]["beta_exec_prod"] for k in per_anchor], np.float64)
    xe = np.array([per_anchor[k]["beta_exec"][lab]["beta_exec_eval"] for k in per_anchor], np.float64)
    nonw[lab] = {"beta_exec_prod_range": [float(xp.min()), float(xp.max())], "beta_exec_eval_range": [float(xe.min()), float(xe.max())],
                 "delta_beta_exec": {"median": float(np.median(dd)), "min": float(dd.min()), "max": float(dd.max()),
                                     "max_abs": float(np.abs(dd).max()), "mean": float(dd.mean())},
                 "rel_diff_max_abs": float(np.max(np.abs(dd / np.abs(xe))))}
    for G in GS:
        k = f"G{int(G)}"
        dl = np.array([per_anchor[a]["beta_exec"][lab][k]["delta_lots_unrounded"] for a in per_anchor])
        nonw[lab][k] = {"delta_lots_unrounded_max_abs": float(np.abs(dl).max()), "delta_lots_unrounded_median_abs": float(np.median(np.abs(dl))),
                        "frac_anchors_order_differs_ge1lot_trunc": float(np.mean([per_anchor[a]["beta_exec"][lab][k]["order_differs_ge1lot_trunc"] for a in per_anchor])),
                        "n_anchors_order_differs_trunc": int(sum(per_anchor[a]["beta_exec"][lab][k]["order_differs_ge1lot_trunc"] for a in per_anchor)),
                        "frac_anchors_order_differs_ge1lot_nearest": float(np.mean([per_anchor[a]["beta_exec"][lab][k]["order_differs_ge1lot_nearest"] for a in per_anchor])),
                        "n_anchors_order_differs_nearest": int(sum(per_anchor[a]["beta_exec"][lab][k]["order_differs_ge1lot_nearest"] for a in per_anchor))}
pooled["beta_exec"] = nonw

# ── bar-level agreement over the union window (universe names, both axes) ──
uc = [n for n in uni_union if n in ccol and n in ecol]
jc = np.array([ccol[n] for n in uc]); je_ = np.array([ecol[n] for n in uc])
vc, ve = Vc[:, jc], Ve[:, je_]
both = vc & ve
drr = np.abs(R4c[:, jc] - R4e[:, je_])
dvals = drr[both]
bars = {"n_bar_cells": int(vc.size), "both_valid": int(both.sum()), "cache_only_valid": int((vc & ~ve).sum()), "cert_only_valid": int((~vc & ve).sum()),
        "neither_valid": int((~vc & ~ve).sum()),
        "abs_r4_diff_both_valid": {"median": float(np.median(dvals)), "p99": float(np.percentile(dvals, 99)), "max": float(dvals.max()),
                                   "n_gt_1e-4": int((dvals > 1e-4).sum()), "n_gt_1e-3": int((dvals > 1e-3).sum()), "n_gt_1e-2": int((dvals > 1e-2).sum())}}
bi = np.argwhere(both & (drr > 1e-3))
bars["cells_abs_r4_diff_gt_1e-3"] = [[utc(Tb[i]), uc[k], float(R4c[i, jc[k]]), float(R4e[i, je_[k]])] for i, k in bi.tolist()][:200]
co = np.argwhere(vc & ~ve); eo = np.argwhere(~vc & ve)
bars["cache_only_valid_cells"] = [[utc(Tb[i]), uc[k]] for i, k in co.tolist()][:200]
bars["cert_only_valid_cells"] = [[utc(Tb[i]), uc[k]] for i, k in eo.tolist()][:200]
bars["cert_only_valid_by_name"] = {}
for i, k in eo.tolist():
    bars["cert_only_valid_by_name"][uc[k]] = bars["cert_only_valid_by_name"].get(uc[k], 0) + 1
bars["cache_only_valid_by_name"] = {}
for i, k in co.tolist():
    bars["cache_only_valid_by_name"][uc[k]] = bars["cache_only_valid_by_name"].get(uc[k], 0) + 1

# ── clip mechanism ──
cc = s2j["clip_cells_cert"]
big = set((int(t), SY[int(c)]) for t, c in zip(E["big_ts"], E["big_col"]))
cset = set((int(t), CS[int(c)]) for t, c in zip(clip_ts, clip_col))
clip = {"union_window_rows": [utc(Tb[0] - 14400), utc(AN.max())],
        "cache_cells_at_clip": len(cset), "cert_cells_abs_r5_gt_0.30": len(big),
        "cache_clip_cells_eq_cert_big_cells": cset == big,
        "cells": [{"utc": c["utc"], "sym": c["sym"], "cache_ret5_f16": float(P["clip_val"][i]), "cert_r5": c["cert_r5"],
                   "in_universe": c["sym"] in set(uni_union), "weight_nonzero_anchors": int(sum(1 for A in AN if WTS[str(A)].get(c["sym"], 0.0) != 0.0))}
                  for i, c in enumerate(cc)],
        "per_anchor_window_counts": {k: {"all_cols": s1j["per_anchor"][k]["n_clip_cells_all_cols"], "universe": s1j["per_anchor"][k]["n_clip_cells_universe"]}
                                     for k in s1j["per_anchor"]},
        "names": sorted(set(c["sym"] for c in cc))}
# beta effect of the clip for clip names (names estimated on both sides)
clip_eff = {}
for n in clip["names"]:
    if n not in NM:
        clip_eff[n] = "not in universe (no production beta written)"
        continue
    n_i = NM.index(n)
    ds = [float(bp[a_i, n_i] - be[a_i, ecol[n]]) for a_i in range(len(AN)) if inf[a_i, n_i] and npr[a_i, n_i] >= 120 and ee[a_i, ecol[n]]]
    clip_eff[n] = {"n_anchors": len(ds), "dbeta_min": min(ds) if ds else None, "dbeta_max": max(ds) if ds else None}
clip["dbeta_of_clip_names"] = clip_eff

# top |dbeta| names with diagnostics
top = sorted(zip(pool_d, pool_n, pool_a), key=lambda x: -abs(x[0]))
seen, top_diag = set(), []
for d, n, a in top:
    if n in seen:
        continue
    seen.add(n)
    A = int([x for x in AN if utc(x) == a][0])
    a_i = int(np.nonzero(AN == A)[0][0]); n_i = NM.index(n)
    top_diag.append({"name": n, "anchor": a, "dbeta": d, "beta_prod": float(bp[a_i, n_i]), "beta_eval": float(be[a_i, ecol[n]]),
                     "raw_eval": float(re_[a_i, ecol[n]]), "nobs_prod": int(npr[a_i, n_i]), "nobs_eval": int(ne[a_i, ecol[n]]),
                     "weight": WTS[a].get(n, 0.0) if a in WTS else WTS[str(A)].get(n, 0.0), "why": bar_diag(n, A)})
    if len(top_diag) >= 12:
        break

# ── write ──
os.makedirs(OUT + "/receipts", exist_ok=True)
cp = OUT + "/receipts/BETA_PARITY_per_anchor_name.csv"
with open(cp, "w", newline="") as f:
    cw = csv.writer(f)
    cw.writerow(["anchor_utc", "name", "in_universe_or_btc", "weight_gross_units", "beta_prod", "nobs_prod", "est_prod", "beta_eval", "nobs_eval",
                 "est_eval", "raw_eval_unclipped", "dbeta_prod_minus_eval", "tag"])
    cw.writerows(rows_csv)
# per-anchor per-name arrays (names = the union field axis)
ne_al = np.full(bp.shape, -1, np.int32); be_al = np.full(bp.shape, np.nan); ee_al = np.zeros(bp.shape, bool); re_al = np.full(bp.shape, np.nan)
for n_i, n in enumerate(NM):
    if n in ecol:
        ne_al[:, n_i] = ne[:, ecol[n]]; be_al[:, n_i] = be[:, ecol[n]]; ee_al[:, n_i] = ee[:, ecol[n]]; re_al[:, n_i] = re_[:, ecol[n]]
sp = OUT + "/receipts/BETA_PARITY_per_anchor_summary.csv"
with open(sp, "w", newline="") as f:
    cw = csv.writer(f)
    cw.writerow(["anchor_utc", "n_compared", "median_abs_dbeta", "p95_abs_dbeta", "max_abs_dbeta", "max_abs_name", "n_abs_dbeta_gt_1e-9",
                 "n_fallback_mismatch", "beta_exec_prod_pub", "beta_exec_eval_pub", "delta_hedge_gross_pub", "delta_lots_G10k_pub",
                 "order_diff_trunc_G10k_pub", "beta_exec_prod_rsh", "beta_exec_eval_rsh", "delta_hedge_gross_rsh", "delta_lots_G10k_rsh",
                 "order_diff_trunc_G10k_rsh", "btc_px_cert"])
    for k, v in per_anchor.items():
        d, bp_, br_ = v["dbeta"], v["beta_exec"]["published"], v["beta_exec"]["reshape_approx"]
        cw.writerow([k, d["n"], d["median_abs"], d["p95_abs"], d["max_abs"], d["max_abs_name"], d["n_abs_gt_1e-9"], v["n_fallback_mismatch"],
                     bp_["beta_exec_prod"], bp_["beta_exec_eval"], bp_["delta_hedge_gross_units"], bp_["G10000"]["delta_lots_unrounded"],
                     int(bp_["G10000"]["order_differs_ge1lot_trunc"]), br_["beta_exec_prod"], br_["beta_exec_eval"], br_["delta_hedge_gross_units"],
                     br_["G10000"]["delta_lots_unrounded"], int(br_["G10000"]["order_differs_ge1lot_trunc"]), v["btc_px_cert"]])
npz = OUT + "/receipts/BETA_PARITY_per_anchor_name.npz"
np.savez_compressed(npz, anchors=AN, names=np.array(NM), in_field=inf, weight_gross_units=WT / np.abs(WT).sum(1, keepdims=True),
                    beta_prod=bp, nobs_prod=npr, beta_eval=be_al, nobs_eval=ne_al, est_eval=ee_al, raw_eval=re_al, btc_px_cert=px)
out = {"item": "R10 A.4-5 β 原始价 vs f16 裁剪 — UNAVAILABLE 数值验证 (production beta device vs evaluation beta device)",
       "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": "s3_compare_local.py",
       "self_sha256": sha(os.path.abspath(__file__)), "python": sys.version, "numpy": np.__version__, "argv": sys.argv,
       "inputs": {"S1_npz": {"path": S1N, "sha256": sha(S1N)}, "S1_receipt": {"path": S1J, "sha256": sha(S1J)},
                  "S2_npz": {"path": S2N, "sha256": sha(S2N)}, "S2_receipt": {"path": S2J, "sha256": sha(S2J)}},
       "upstream_inputs": {"S1": s1j["inputs"], "S2": s2j["inputs"]},
       "upstream_devices": {"S1": {"self_sha256": s1j["self_sha256"], "python": s1j["python"], "numpy": s1j["numpy"], "argv": s1j["argv"]},
                            "S2": {"self_sha256": s2j["self_sha256"], "python": s2j["python"], "numpy": s2j["numpy"], "argv": s2j["argv"],
                                   "env": s2j["env"]}},
       "upstream_checks_failed": {"S1": s1j["failed"], "S2": s2j["failed"]},
       "definitions": __doc__, "anchors": [utc(a) for a in AN], "coverage_census": s1j["coverage_census"],
       "revision_check_snapshot_vs_copy": s1j["revision_check"], "symbol_mapping": mapping, "pooled": pooled,
       "per_anchor": per_anchor, "fallback_mismatch": fb_mismatch, "clip_bound_hits": bound_hits, "bar_level": bars, "clip_mechanism": clip,
       "top_abs_dbeta_names": top_diag, "checks": checks, "failed": FAILS,
       "commands": ({"path": OUT + "/RUN_COMMANDS.sh", "sha256": sha(OUT + "/RUN_COMMANDS.sh"), "text": open(OUT + "/RUN_COMMANDS.sh").read()}
                    if os.path.isfile(OUT + "/RUN_COMMANDS.sh") else "RUN_COMMANDS.sh ABSENT"),
       "pod2_log": open(W + "/S2_eval_pod2.log").read() if os.path.isfile(W + "/S2_eval_pod2.log") else "ABSENT",
       "outputs": {"csv": cp, "csv_sha256": sha(cp), "summary_csv": sp, "summary_csv_sha256": sha(sp), "npz": npz, "npz_sha256": sha(npz)}}
jp = OUT + "/receipts/BETA_PARITY_R10_A45.json"
json.dump(out, open(jp + ".tmp", "w"), indent=1, default=str)
os.replace(jp + ".tmp", jp)
print(("S3 ALL CHECKS OK" if not FAILS else f"S3 FAILURES {FAILS}"), "receipt_sha256=" + sha(jp), flush=True)
sys.exit(0 if not FAILS else 1)
