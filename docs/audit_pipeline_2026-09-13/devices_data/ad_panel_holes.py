#!/usr/bin/env python3
"""ad_panel_holes.py -- AUDIT_DATA 2026-09-13, device D (pod2, CPU, READ-ONLY): do the 4h panels still carry the cache holes?

The hole fixes (E-0908-D 2026-08-13..24, 348 names zeroed; E-0909-B 2022-02-26..03-01 / 04-01..03, 49 names) were applied to the 5m
CACHE (holefix2). The panels every research replay and the v4 chain read -- wide_panel_4h_v2ext.npz (built 09-01 by pod_panel_ext.py on
the pre-fix `_ext` cache) and wide_panel_4h_v3splice.npz (v1 canonical prefix + v2ext tail) -- were not rebuilt; the x0910 panels copy
their prefixes verbatim (r6 BW-2). Reference = wide_panel_4h_rawbuild_x0910.npz: the SAME builder (pod_panel_ext.py, unmodified per
RESULT_r6 S4) run on the hole-fixed, extended cache holefix2_x0910.
Readings per panel key on common anchors: cells whose finite pattern or value (|d| > 1e-6 * max(1,|ref|)) differ, split by whether the
anchor's longest window (8,640 rows back, 288 rows forward) touches a holefix2 fill run (holefix2_cells.npz fill_runs) -- differences
OUTSIDE every hole neighbourhood are unexplained and listed. Funding keys are compared too (they do not depend on the 5m cache).
Positive control: on anchors whose windows touch no fill run, every kline key of v2ext must equal the reference (else the comparison
is not a hole measurement and is declared INVALID).
Usage: python3 ad_panel_holes.py <out_receipt.json>
"""
import os, sys, json, time, hashlib
import numpy as np

ENV_WHITELIST = set()
os.nice(19)
OUT = sys.argv[1]
W = "/workspace"
REF = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_rawbuild_x0910.npz"
PANELS = {"v2ext": f"{W}/data/wide_panel_4h_v2ext.npz", "v3splice": f"{W}/data/wide_panel_4h_v3splice.npz", "v2holefix": f"{W}/data/wide_panel_4h_v2holefix.npz"}
HOLES = f"{W}/review_scratch/holefix2_cells.npz"; CACHE_X = f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
KLINE = ["f_rev_4h", "f_rev_24h", "f_rev_3d", "f_mom_7d", "f_mom_30d", "f_mom_7d_x24", "f_vol_7d", "f_volq_ratio", "f_amihud_24h", "f_range_24h",
         "f_cpos_24h", "f_tbf_24h", "f_asz_24h", "Y4", "Y24", "elig"]
FUND = ["f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"]
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
assert not (ENV_WHITELIST - set(os.environ))
T0 = time.time()
rec = {"device": "ad_panel_holes.py", "self_sha256": sha(os.path.abspath(__file__)), "reference": {"path": REF, "sha256": sha(REF)},
       "panels": {k: {"path": v, "sha256": sha(v)} for k, v in PANELS.items()}, "holes": {"path": HOLES, "sha256": sha(HOLES)}}
H = np.load(HOLES, allow_pickle=True); runs = H["fill_runs"].astype(np.int64)
cts = np.load(CACHE_X, allow_pickle=True)["ts"].astype(np.int64)
run_ts = [(int(cts[a]), int(cts[b])) for a, b in runs]
rec["holes"]["fill_runs_utc"] = [(utc(a), utc(b)) for a, b in run_ts]
REFZ = np.load(REF, allow_pickle=True); rts = REFZ["ts"].astype(np.int64); rsy = [str(s) for s in REFZ["symbols"]]; rpos = {int(t): i for i, t in enumerate(rts)}
def near_hole(t):   # any fill run inside [t - 8640*300, t + 288*300]
    lo, hi = t - 8640 * 300, t + 288 * 300
    return any(not (b < lo or a > hi) for a, b in run_ts)
out = {}
for pk, pth in PANELS.items():
    Z = np.load(pth, allow_pickle=True); ts = Z["ts"].astype(np.int64); assert [str(s) for s in Z["symbols"]] == rsy
    common = [(i, rpos[int(t)]) for i, t in enumerate(ts) if int(t) in rpos]
    ia = np.array([c[0] for c in common]); ib = np.array([c[1] for c in common]); cts_ = ts[ia]
    nh = np.array([near_hole(int(t)) for t in cts_])
    keys = {}
    for k in KLINE + FUND:
        if k not in Z.files or k not in REFZ.files: keys[k] = "absent"; continue
        a = np.asarray(Z[k])[ia].astype(np.float64); b = np.asarray(REFZ[k])[ib].astype(np.float64)
        fa, fb = np.isfinite(a), np.isfinite(b); pat = fa != fb
        both = fa & fb; val = both & (np.abs(a - b) > 1e-6 * np.maximum(1.0, np.abs(b)))
        diff = pat | val; rows_any = diff.any(1)
        r = {"cells_compared": int(diff.size), "pattern_diff_cells": int(pat.sum()), "value_diff_cells": int(val.sum()),
             "diff_cells_near_hole": int(diff[nh].sum()), "diff_cells_away_from_hole": int(diff[~nh].sum()),
             "anchors_with_diff": int(rows_any.sum()), "anchors_with_diff_away_from_hole": int((rows_any & ~nh).sum()),
             "max_abs_value_diff": (float(np.abs(a - b)[both].max()) if both.any() else None)}
        if (rows_any & ~nh).any():
            aw = np.where(rows_any & ~nh)[0]
            r["away_anchor_examples"] = [utc(cts_[x]) for x in aw[:12]]; r["away_anchor_last"] = utc(cts_[aw[-1]])
        keys[k] = r
    kl = [keys[k] for k in KLINE if isinstance(keys.get(k), dict)]
    pc = sum(r["diff_cells_away_from_hole"] for r in kl)
    out[pk] = {"n_anchors": int(len(ts)), "first": utc(ts[0]), "last": utc(ts[-1]), "common_anchors": int(len(ia)), "anchors_near_hole": int(nh.sum()),
               "kline_diff_cells_away_from_hole_total": int(pc), "kline_diff_cells_near_hole_total": int(sum(r["diff_cells_near_hole"] for r in kl)),
               "positive_control_kline_equal_away_from_holes": bool(pc == 0), "keys": keys}
    print(pk, "PC", pc == 0, "near-hole kline diff cells", out[pk]["kline_diff_cells_near_hole_total"], flush=True)
rec["comparisons"] = out; rec["elapsed_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_PANEL_HOLES_DONE", OUT, flush=True)
