#!/usr/bin/env python3
"""ad_batch2.py -- AUDIT_DATA 2026-09-13, device F (pod2, CPU, READ-ONLY). Follow-ups opened by devices B-D.

F1  Funding COVERAGE of the splice panel the DL chain reads (wide_panel_4h_v3splice.npz: v1 canonical prefix <= 2026-08-15 00Z + v2ext tail;
    consumers pod_dlw_features_ext.py F171_PANEL (fund_ema/fund_now columns), pod_legs_v4b.py LEGS_PANEL (fund leg f_fund_ema_v1),
    pod_export_bundle_v4.py EXPORT_PANEL, pod_dlw_targets_raw.py DLWT_PANEL) vs the 829-name panel the research replay reads
    (wide_panel_4h_v2ext.npz): cells finite in one and NaN in the other, per year and per key, and the symbols involved.
F2  What the DL training rows actually saw: dlw_v4raw/dlw_fea82.npz fund_ema / fund_now columns (nan_to_num => 0.0 when the panel has
    no value) over every (anchor, member) training pair, split by whether v2ext has a finite value for that pair; per year.
F3  Same question for the legs the F10 V2 trainer reads (f8_v4/f10v2_legs.npz ZFD) : member pairs with non-finite ZFD while v2ext has funding.
F4  Raw-return patch bars per month (raw_patch.npz, raw_patch_x0910.npz) -- how often new +-0.30 clip bars appear (October-chain risk).
Usage: python3 ad_batch2.py <out_receipt.json>
"""
import os, sys, json, time, hashlib
import numpy as np

ENV_WHITELIST = set()
os.nice(19)
OUT = sys.argv[1]
W = "/workspace"
V2 = f"{W}/data/wide_panel_4h_v2ext.npz"; V3 = f"{W}/data/wide_panel_4h_v3splice.npz"; V1 = f"{W}/data/wide_panel_4h_v1.npz"
TG = f"{W}/dlw_v4raw/data/dlw_targets.npz"; FEA82 = f"{W}/dlw_v4raw/data/dlw_fea82.npz"; LEGS = f"{W}/f8_v4/data/f10v2_legs.npz"
PATCH = f"{W}/review_scratch/raw_patch.npz"; PATCH_X = f"{W}/uplift_2026-09-11/r6/out/raw_patch_x0910.npz"
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
assert not (ENV_WHITELIST - set(os.environ))
T0 = time.time()
rec = {"device": "ad_batch2.py", "self_sha256": sha(os.path.abspath(__file__)), "inputs": {p: sha(p) for p in (V2, V3, V1, TG, FEA82, LEGS, PATCH, PATCH_X)}, "numpy": np.__version__}

# ---------------- F1 ----------------
P2 = np.load(V2, allow_pickle=True); P3 = np.load(V3, allow_pickle=True); P1 = np.load(V1, allow_pickle=True)
syms = [str(s) for s in P2["symbols"]]; assert [str(s) for s in P3["symbols"]] == syms == [str(s) for s in P1["symbols"]]
t2 = P2["ts"].astype(np.int64); t3 = P3["ts"].astype(np.int64); t1 = P1["ts"].astype(np.int64); pos3 = {int(t): i for i, t in enumerate(t3)}
i2 = np.array([k for k, t in enumerate(t2) if int(t) in pos3]); i3 = np.array([pos3[int(t2[k])] for k in i2])
f1 = {"v1_last_anchor": utc(t1[-1]), "v3splice_first": utc(t3[0]), "common_anchors": int(len(i2)),
      "v1_symbols_with_any_finite_f_fund_ema": int(np.isfinite(P1["f_fund_ema"]).any(0).sum()),
      "v2ext_symbols_with_any_finite_f_fund_ema": int(np.isfinite(P2["f_fund_ema"]).any(0).sum()), "keys": {}}
yrs = np.array([yr(t) for t in t2[i2]])
for k in ("f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1"):
    a = np.asarray(P2[k])[i2]; b = np.asarray(P3[k])[i3]
    only2 = np.isfinite(a) & ~np.isfinite(b); only3 = ~np.isfinite(a) & np.isfinite(b)
    by = {str(y): {"finite_v2ext_nan_v3splice": int(only2[yrs == y].sum()), "nan_v2ext_finite_v3splice": int(only3[yrs == y].sum()),
                   "finite_v2ext_cells": int(np.isfinite(a[yrs == y]).sum())} for y in sorted(set(yrs.tolist()))}
    sy = only2.sum(0); top = np.argsort(-sy)[:25]
    f1["keys"][k] = {"by_year": by, "symbols_with_finite_v2ext_nan_v3splice": int((sy > 0).sum()),
                     "top_symbols": [(syms[j], int(sy[j])) for j in top if sy[j] > 0]}
rec["F1_splice_vs_v2ext_funding_coverage"] = f1
print("F1 done", time.time() - T0, flush=True)

# ---------------- F2 ----------------
T = np.load(TG, allow_pickle=True); E = T["E_ts"].astype(np.int64)
F = np.load(FEA82, allow_pickle=True); names = [str(x) for x in F["names"]]; X = F["X"]; pa = F["pair_a"].astype(np.int64); ps = F["pair_s"].astype(np.int64)
ce, cn = names.index("fund_ema"), names.index("fund_now")
pos2 = {int(t): i for i, t in enumerate(t2)}
row2 = np.array([pos2.get(int(t), -1) for t in E]); pr = row2[pa]; okr = pr >= 0
v2fin = np.zeros(len(pa), bool); v2fin[okr] = np.isfinite(np.asarray(P2["f_fund_ema"])[pr[okr], ps[okr]])
fe = X[:, ce].astype(np.float32); fn = X[:, cn].astype(np.float32)
pyr = np.array([yr(t) for t in E])[pa]
f2 = {"pairs": int(len(pa)), "names": [names[ce], names[cn]], "by_year": {}}
for y in sorted(set(pyr.tolist())):
    s = pyr == y
    f2["by_year"][str(y)] = {"pairs": int(s.sum()), "pairs_with_v2ext_row": int((s & okr).sum()),
                             "fund_ema_zero": int((s & (fe == 0)).sum()), "fund_ema_zero_while_v2ext_finite": int((s & (fe == 0) & v2fin).sum()),
                             "fund_now_zero_while_v2ext_finite": int((s & (fn == 0) & v2fin).sum()),
                             "share_fund_ema_zero_while_v2ext_finite": round(float((s & (fe == 0) & v2fin).sum()) / max(int((s & v2fin).sum()), 1), 6)}
rec["F2_fea82_fund_columns"] = f2
del X, F
print("F2 done", time.time() - T0, flush=True)

# ---------------- F3 ----------------
L = np.load(LEGS, allow_pickle=True); LE = L["E_ts"].astype(np.int64); assert np.array_equal(LE, E), "legs axis != dlw axis"
ZFD = L["ZFD"]; MEM = T["members"]
P2_FE1 = np.asarray(P2["f_fund_ema_v1"])
f3 = {}
for i, t in enumerate(E):
    y = str(yr(t)); b = f3.setdefault(y, {"member_pairs": 0, "zfd_nonfinite": 0, "zfd_nonfinite_while_v2ext_finite": 0})
    m = np.asarray(MEM[i], np.int64); b["member_pairs"] += int(len(m)); nf = ~np.isfinite(ZFD[i, m]); b["zfd_nonfinite"] += int(nf.sum())
    j = pos2.get(int(t))
    if j is not None: b["zfd_nonfinite_while_v2ext_finite"] += int((nf & np.isfinite(P2_FE1[j, m])).sum())
rec["F3_legs_ZFD"] = f3
print("F3 done", time.time() - T0, flush=True)

# ---------------- F4 ----------------
f4 = {}
for nm, p in (("raw_patch", PATCH), ("raw_patch_x0910", PATCH_X)):
    Z = np.load(p, allow_pickle=True); ts = Z["ts"].astype(np.int64); by = {}
    for t in ts:
        mth = time.strftime("%Y-%m", time.gmtime(int(t))); by[mth] = by.get(mth, 0) + 1
    f4[nm] = {"bars": int(len(ts)), "by_month": dict(sorted(by.items())), "months_with_bars_2026": sum(1 for k in by if k.startswith("2026"))}
rec["F4_patch_bars_by_month"] = f4
rec["elapsed_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_BATCH2_DONE", OUT, flush=True)
