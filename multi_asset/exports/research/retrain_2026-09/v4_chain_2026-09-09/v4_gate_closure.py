"""PREREG_fea89_stable_trend §3 G2: per-column dependency-closure gate between two fea89 builds (same builder, holefix vs holefix2).
closure rows = [fill_start-48, fill_end + 2016 (membership) + L_col + extra]; L_col from the name suffix; extra: H +8640+48, J +288, E +288. NaN-aware: a
NaN<->finite change counts as a diff and is reported separately. usage: v4_gate_closure.py <fea89_A (holefix2)> <fea89_B (holefix)> <targets_A> <targets_B> <out.json>"""
import numpy as np, json, sys, re, time
A_, B_, TA, TB, OUT = sys.argv[1:6]
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); RUNS = H["fill_runs"]
def L_col(name):
    fam, base = name.split(":", 1); m = re.search(r"_(\d+)$", base); L = int(m.group(1)) if m else None
    if L is None:
        if base.endswith("7d") or "_7" in base or base in ("vov_7d", "spr_7", "spq_7", "sprg_7", "spt_7"): L = 2016
        elif "30" in base: L = 8640
        elif base.endswith("1d") or "lag" in base or base == "dvol_1d": L = 288
        elif base.endswith("4h") or base == "dqv_4h": L = 48
        else: L = 8640
    L = max(L, 48); extra = {"H": 8640 + 48, "J": 288, "E": 288}.get(fam, 0)
    if fam == "H": L = 8640      # products of ranks with the 180-anchor causal z
    if fam == "I": L = 8640
    return 2016 + L + extra
NW = 829
Fa = np.load(A_, allow_pickle=True); Fb = np.load(B_, allow_pickle=True); names = [str(x) for x in Fa["names"]]; assert names == [str(x) for x in Fb["names"]]
Ea = np.load(TA, allow_pickle=True)["E_row"].astype(np.int64); Eb = np.load(TB, allow_pickle=True)["E_row"].astype(np.int64); assert np.array_equal(Ea, Eb)
ka = Fa["pair_a"].astype(np.int64) * NW + Fa["pair_s"].astype(np.int64); kb = Fb["pair_a"].astype(np.int64) * NW + Fb["pair_s"].astype(np.int64)
oa = np.argsort(ka, kind="stable"); ob = np.argsort(kb, kind="stable"); ka = ka[oa]; kb = kb[ob]; common = np.intersect1d(ka, kb); ia = oa[np.searchsorted(ka, common)]; ib = ob[np.searchsorted(kb, common)]
only_a = np.setdiff1d(ka, kb); only_b = np.setdiff1d(kb, ka)
def in_closure(rows, reach):
    out = np.zeros(len(rows), bool)
    for a, b in RUNS: out |= (rows >= a - 48) & (rows <= b + reach)
    return out
res = {"n_common": int(len(common)), "pairs_only_A": int(len(only_a)), "pairs_only_B": int(len(only_b)), "pairs_only_A_outside_membership_closure": int((~in_closure(Ea[only_a // NW], 2016)).sum()), "pairs_only_B_outside_membership_closure": int((~in_closure(Eb[only_b // NW], 2016)).sum()), "columns": {}}
Xa = Fa["X"]; Xb = Fb["X"]; er = Ea[common // NW]
for j, nm in enumerate(names):
    reach = L_col(nm); a = Xa[ia, j]; b = Xb[ib, j]; na = np.isnan(a); nb = np.isnan(b); d = (na != nb) | (~na & ~nb & (a != b)); inc = in_closure(er, reach)
    out_d = d & ~inc; res["columns"][nm] = {"reach_rows": int(reach), "diff_cells": int(d.sum()), "diff_outside_closure": int(out_d.sum()), "nan_flips_outside": int(((na != nb) & ~inc).sum()), "finite_diff_outside_maxabs": float(np.nanmax(np.abs(a - b)[out_d & ~na & ~nb])) if (out_d & ~na & ~nb).any() else 0.0, "anchors_outside": int(len(np.unique(common[out_d] // NW)))}
bad = {k: v for k, v in res["columns"].items() if v["diff_outside_closure"] > 0}
res["PASS"] = bool(not bad and res["pairs_only_A_outside_membership_closure"] == 0 and res["pairs_only_B_outside_membership_closure"] == 0); res["failing_columns"] = bad; res["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(res, open(OUT, "w"), indent=1)
print(f"G2 closure gate {A_.split('/')[-3]} vs {B_.split('/')[-3]}: common {len(common)} pairs; only-A {len(only_a)} (outside membership closure {res['pairs_only_A_outside_membership_closure']}); columns with outside-closure diffs: {len(bad)}")
for k, v in sorted(bad.items(), key=lambda x: -x[1]['diff_outside_closure']): print("  FAIL", k, v)
print("G2", "PASS" if res["PASS"] else "FAIL")
