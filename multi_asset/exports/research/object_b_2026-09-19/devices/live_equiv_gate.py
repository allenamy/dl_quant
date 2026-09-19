#!/usr/bin/env python3
"""Object B · S4 keep-gate LE-A′ (PREREG §3 S4): the live-equivalent cache rule (b_lib.LiveEquiv) must not change the NaN support of any live-450
cell in the production overlap window. Compare the transformed holefix2 cache with the producer's own rolling snapshot
P2/work/snapshots/1789200000/rolling.npz (G2-A′ source) on rows ts <= 2026-09-01 00:00Z, live-450 names, all 7 channels:
  violations = cells where the transformed cache is NaN and production is finite, or vice versa. PASS <=> 0.
Negative control: the same rule with one live-450 name forced "dead" mid-window must produce violations > 0.
Also reports the per-year count of cells the rule changes over the whole cache (the chain's input). No history; writes receipts/LIVE_EQUIV.json."""
import os, sys, json, time, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD

SNAP = ("/workspace/uplift_r2_2026-09-13/P2/work/snapshots/1789200000/rolling.npz", None)
T0 = time.time()
G = BD.Globals(load_cache=True)                       # applies the rule in place and records the changed-cell counts
cfg = json.load(open(BD.SRC["bundle_config"][0])); live = [G.col[s] for s in cfg["symbols_live"]]
Z = np.load(SNAP[0], allow_pickle=True); pts = Z["ts"].astype(np.int64); pd = Z["data"]
assert [str(s) for s in Z["symbols"]] == G.SYMS if "symbols" in Z.files else True
common = np.intersect1d(pts, G.TS); common = common[common <= 1788220800]
ia = np.searchsorted(G.TS, common); ib = np.searchsorted(pts, common)
A = G.DATA[ia][:, live, :].astype(np.float32); B = pd[ib][:, live, :].astype(np.float32)
fa = np.isfinite(A); fb = np.isfinite(B)
v_nan_here = int((~fa & fb).sum()); v_nan_prod = int((fa & ~fb).sum())
val_diff = int((fa & fb & (A != B)).sum())
# negative control: force one live name dead at the middle of the window (rule applied to a copy of the overlap slice only)
j = live[0]; mid = int(common[len(common) // 2])
LE2 = copy.copy(G.LE); LE2.last = G.LE.last.copy(); LE2.dead = G.LE.dead.copy(); LE2.last[j] = mid; LE2.dead[j] = True
sl = G.DATA[ia].copy(); LE2.apply_inplace(sl, G.TS[ia]); A2 = sl[:, live, :].astype(np.float32)
neg = int((~np.isfinite(A2) & fb).sum())
doc = {"device": os.path.abspath(__file__), "self_sha256": BL.sha(os.path.abspath(__file__)), "lib_sha256": BL.sha(f"{HERE}/b_lib.py"),
       "inputs_sha256": G.shas, "snapshot": SNAP[0], "snapshot_sha256": BL.sha(SNAP[0]),
       "window": [BL.iso(common[0]), BL.iso(common[-1]), int(len(common))], "n_live": len(live),
       "violations_nan_here_finite_prod": v_nan_here, "violations_finite_here_nan_prod": v_nan_prod, "finite_value_diffs": val_diff,
       "LE_A_prime": "PASS" if (v_nan_here == 0 and v_nan_prod == 0) else "FAIL",
       "negative_control": {"forced_dead_name": G.SYMS[j], "at": BL.iso(mid), "violations": neg, "ok": neg > 0},
       "rule_changed_cells_by_year_whole_cache": G.le_changed, "n_dead_names": int(G.LE.dead.sum()), "n_never_traded": int(G.LE.never.sum()),
       "n_noncoin_names": int(G.LE.noncoin.sum()), "runtime_s": round(time.time() - T0, 1), "utc": BL.iso(time.time())}
json.dump(doc, open(f"{BD.R}/receipts/LIVE_EQUIV.json", "w"), indent=1)
print(json.dumps({k: doc[k] for k in ("window", "LE_A_prime", "violations_nan_here_finite_prod", "violations_finite_here_nan_prod", "finite_value_diffs", "negative_control", "rule_changed_cells_by_year_whole_cache", "n_dead_names", "n_noncoin_names")}))
