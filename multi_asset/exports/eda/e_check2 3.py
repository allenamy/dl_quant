"""Prove v2 gate_e is SOUND; the self-test T3c BROKEN is a mis-scaled corruption (pred std ~1.0,
Yraw std ~0.023 => additive alpha=3 injects only ~7% => negligible). Build corruptions inline."""
import os
import sys, json, numpy as np
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/handoff")
import acceptance_battery as ab
M = MA + "/exports/train"
THR = ab.THRESHOLDS
champ3 = ab.load_any(f"{M}/wideA_lamorth0_xattn", THR)
H, T = champ3.horizon, champ3.pred.shape[0]
inj = np.full_like(champ3.pred, np.nan); inj[:T-H] = champ3.Yraw[H:]
ok = np.isfinite(champ3.pred) & np.isfinite(inj)
ps, ys = float(np.nanstd(champ3.pred)), float(np.nanstd(champ3.Yraw))
print(f"pred_std={ps:.4f} yraw_std={ys:.4f} scale_ratio={ps/ys:.1f}x", flush=True)

def mk(alpha, replace=False):
    Q = ab._clone(champ3); Q.pred = champ3.pred.copy()
    if replace:
        Q.pred = np.full_like(champ3.pred, np.nan); Q.pred[ok] = inj[ok]
    else:
        Q.pred[ok] = champ3.pred[ok] + alpha * inj[ok]
    Q.point = Q.pred.copy(); Q.finalize()
    return ab.gate_e_forward(Q, THR)

OUT = dict(pred_std=ps, yraw_std=ys)
for tag, a, rep in [("additive_a3(0B)", 3.0, False), ("additive_a50", 50.0, False), ("replace_purefwd", 0, True)]:
    g = mk(a, rep)
    OUT[tag] = dict(passed=g["passed"], peak0=g["peak_at_lag0"], prof=g["profile_fullH"])
    print(f"{tag:18s} e_pass={g['passed']} peak0={g['peak_at_lag0']} prof={g['profile_fullH']}", flush=True)
json.dump(OUT, open("/tmp/0c_echeck.json", "w"), indent=1, default=str)
print("SAVED", flush=True)
