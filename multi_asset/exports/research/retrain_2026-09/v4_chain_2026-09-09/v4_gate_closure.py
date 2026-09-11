"""PREREG_fea89_stable_trend §3 G2: per-column dependency-closure gate between two fea89 builds (same builder, holefix vs holefix2).
closure rows = [fill_start-48, fill_end + 2016 (membership) + L_col + extra]; L_col from the name suffix; extra: H +8640+48, J +288, E +288. NaN-aware: a
NaN<->finite change counts as a diff and is reported separately. usage: v4_gate_closure.py <fea89_A (holefix2)> <fea89_B (holefix)> <targets_A> <targets_B> <out.json>

★ HARDENED 2026-09-09 (review b0a573a1 P1-PIPE / R7): FAIL now EXITS 3 (was rc 0 with PASS=false in the JSON), the receipt carries
  the input SHAs (chains `require` it), and the AXIS is checked, not assumed: E_ts equal, symbols equal and in the same order,
  E_row strictly increasing on the 4h grid (spacing a positive multiple of 48 rows), pair keys unique and in range on both sides,
  the expected column count present. A build whose B side has every E_ts shifted +300 s and the symbol axis reversed used to PASS
  because only E_row was compared. env: HOLE_CELLS (default /workspace/review_scratch/holefix2_cells.npz), EXPECT_NCOLS (89)."""
import numpy as np, json, sys, re, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize
A_, B_, TA, TB, OUT = sys.argv[1:6]
HOLE = os.environ.get("HOLE_CELLS", "/workspace/review_scratch/holefix2_cells.npz")
H = np.load(HOLE, allow_pickle=True); RUNS = H["fill_runs"]
# explicit per-column lookback table derived from pod_f8_build_ext.py (rows): E family = day-phase windows j<=7/30 slots x 288 (+288 phase); J drank = base rank window + 6-anchor lag (288)
EXPLICIT = {"E:spr_7": 7 * 288 + 288, "E:spr_30": 30 * 288 + 288, "E:spr_30_t": 30 * 288 + 288, "E:spq_7": 7 * 288 + 288 + 2016, "E:spq_30": 30 * 288 + 288 + 8640, "E:sprg_7": 7 * 288 + 288, "E:spt_7": 7 * 288 + 288,
            "J:drank_m7_1d": 2016 + 288, "J:drank_v7_1d": 2016 + 288, "J:drank_r24_1d": 288 + 288, "J:r24_lag1": 288 + 288, "J:dqv_4h": 48 + 288, "B:vov_7d": 2016 + 288, "B:dvol_1d": 288 + 288, "B:dvol_4h": 48 + 48, "F:damihud": 2016 + 288}
for k in range(2, 7): EXPLICIT[f"J:r4_lag_{k}"] = 48 + 48 * k
def L_col(name):
    fam, base = name.split(":", 1)
    if name in EXPLICIT: L = EXPLICIT[name]
    else:
        m = re.search(r"_(\d+)$", base); L = int(m.group(1)) if m else 8640
        if fam in ("H", "I"): L = 8640
    extra = {"H": 8640 + 48}.get(fam, 0)
    return 2016 + max(L, 48) + extra
Fa = np.load(A_, allow_pickle=True); Fb = np.load(B_, allow_pickle=True)
Ta = np.load(TA, allow_pickle=True); Tb = np.load(TB, allow_pickle=True)
res = {"PASS": False, "axis": {}, "columns": {}}
# ── AXIS (R7): everything the pair keys are relative to must be identical on both sides ──────────
names = [str(x) for x in Fa["names"]]; names_b = [str(x) for x in Fb["names"]]
Ea = Ta["E_row"].astype(np.int64); Eb = Tb["E_row"].astype(np.int64)
tsa = Ta["E_ts"].astype(np.int64); tsb = Tb["E_ts"].astype(np.int64)
syma = [str(s) for s in Ta["symbols"]]; symb = [str(s) for s in Tb["symbols"]]
NW = len(syma); EXPECT_NCOLS = int(os.environ.get("EXPECT_NCOLS", "89"))
ka = Fa["pair_a"].astype(np.int64) * NW + Fa["pair_s"].astype(np.int64); kb = Fb["pair_a"].astype(np.int64) * NW + Fb["pair_s"].astype(np.int64)
ax = res["axis"]
ax["names_equal"] = names == names_b; ax["n_cols"] = len(names); ax["n_cols_expected"] = EXPECT_NCOLS; ax["n_cols_ok"] = (len(names) == EXPECT_NCOLS)
ax["E_row_equal"] = bool(np.array_equal(Ea, Eb)); ax["E_ts_equal"] = bool(np.array_equal(tsa, tsb))
ax["symbols_equal_same_order"] = (syma == symb)
ax["E_row_strictly_increasing"] = bool(len(Ea) < 2 or (np.diff(Ea) > 0).all())
ax["E_row_grid_spacing_ok"] = bool(len(Ea) < 2 or ((np.diff(Ea) % 48 == 0) & (np.diff(Ea) > 0)).all())
ax["E_ts_row_consistent"] = bool(len(Ea) < 2 or np.array_equal(np.diff(tsa) // 300, np.diff(Ea)))
ax["pairs_unique_A"] = bool(len(np.unique(ka)) == len(ka)); ax["pairs_unique_B"] = bool(len(np.unique(kb)) == len(kb))
ax["pair_a_in_range"] = bool((Fa["pair_a"] >= 0).all() and (Fa["pair_a"] < len(Ea)).all() and (Fb["pair_a"] >= 0).all() and (Fb["pair_a"] < len(Eb)).all())
ax["pair_s_in_range"] = bool((Fa["pair_s"] >= 0).all() and (Fa["pair_s"] < NW).all() and (Fb["pair_s"] >= 0).all() and (Fb["pair_s"] < NW).all())
ax["X_shape_A"] = list(Fa["X"].shape); ax["X_shape_B"] = list(Fb["X"].shape)
ax["X_rows_match_pairs"] = bool(Fa["X"].shape[0] == len(ka) and Fb["X"].shape[0] == len(kb) and Fa["X"].shape[1] == len(names) and Fb["X"].shape[1] == len(names_b))
axis_ok = all(ax[k] for k in ("names_equal", "n_cols_ok", "E_row_equal", "E_ts_equal", "symbols_equal_same_order", "E_row_strictly_increasing",
                             "E_row_grid_spacing_ok", "E_ts_row_consistent", "pairs_unique_A", "pairs_unique_B", "pair_a_in_range", "pair_s_in_range", "X_rows_match_pairs"))
res["axis_ok"] = bool(axis_ok)
if not axis_ok:
    res["failing_axis_checks"] = [k for k, v in ax.items() if v is False]
    finalize("G2_closure", res, OUT, {"fea_A": A_, "fea_B": B_, "targets_A": TA, "targets_B": TB, "hole_cells": HOLE})
oa = np.argsort(ka, kind="stable"); ob = np.argsort(kb, kind="stable"); ka = ka[oa]; kb = kb[ob]; common = np.intersect1d(ka, kb); ia = oa[np.searchsorted(ka, common)]; ib = ob[np.searchsorted(kb, common)]
only_a = np.setdiff1d(ka, kb); only_b = np.setdiff1d(kb, ka)
def in_closure(rows, reach):
    out = np.zeros(len(rows), bool)
    for a, b in RUNS: out |= (rows >= a - 48) & (rows <= b + reach)
    return out
res.update({"n_common": int(len(common)), "pairs_only_A": int(len(only_a)), "pairs_only_B": int(len(only_b)), "pairs_only_A_outside_membership_closure": int((~in_closure(Ea[only_a // NW], 2016)).sum()), "pairs_only_B_outside_membership_closure": int((~in_closure(Eb[only_b // NW], 2016)).sum())})
Xa = Fa["X"]; Xb = Fb["X"]; er = Ea[common // NW]
for j, nm in enumerate(names):
    reach = L_col(nm); a = Xa[ia, j]; b = Xb[ib, j]; na = np.isnan(a); nb = np.isnan(b); d = (na != nb) | (~na & ~nb & (a != b)); inc = in_closure(er, reach)
    out_d = d & ~inc; res["columns"][nm] = {"reach_rows": int(reach), "diff_cells": int(d.sum()), "diff_outside_closure": int(out_d.sum()), "nan_flips_outside": int(((na != nb) & ~inc).sum()), "finite_diff_outside_maxabs": float(np.nanmax(np.abs(a.astype(np.float64) - b.astype(np.float64))[out_d & ~na & ~nb])) if (out_d & ~na & ~nb).any() else 0.0}
bad = {k: v for k, v in res["columns"].items() if v["diff_outside_closure"] > 0}
res["PASS"] = bool(axis_ok and not bad and res["pairs_only_A_outside_membership_closure"] == 0 and res["pairs_only_B_outside_membership_closure"] == 0); res["failing_columns"] = bad
print(f"G2 closure gate {A_.split('/')[-3] if A_.count('/') >= 3 else A_} vs {B_.split('/')[-3] if B_.count('/') >= 3 else B_}: common {len(common)} pairs; only-A {len(only_a)} (outside membership closure {res['pairs_only_A_outside_membership_closure']}); only-B {len(only_b)} (outside {res['pairs_only_B_outside_membership_closure']}); columns with outside-closure diffs {len(bad)}/{len(names)}", flush=True)
for k, v in sorted(bad.items(), key=lambda x: -x[1]['diff_outside_closure']): print("  FAIL", k, v)
finalize("G2_closure", res, OUT, {"fea_A": A_, "fea_B": B_, "targets_A": TA, "targets_B": TB, "hole_cells": HOLE})
