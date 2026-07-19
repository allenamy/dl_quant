"""Diagnose self-test T3c BROKEN: is v2 gate_e sound, or is the corruption mis-scaled?
Compare 0B's additive corruption (alpha*Yraw, Yraw~0.01 << pred~0.18) vs a rank-replacement
corruption (forward window genuinely dominates). Only calls gate_e (fast)."""
import sys, json, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/handoff")
import acceptance_battery as ab
from scipy.stats import rankdata
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
THR = ab.THRESHOLDS
champ3 = ab.load_any(f"{M}/wideA_lamorth0_xattn", THR)

print("pred std ~", round(float(np.nanstd(champ3.pred)), 4), " Yraw std ~", round(float(np.nanstd(champ3.Yraw)), 4), flush=True)

# 0B additive (alpha=3): reproduce
addv = ab.corrupt_inject_lookahead(champ3, THR["seed"], alpha=3.0)
ge_add = ab.gate_e_forward(addv, THR)
print("ADDITIVE alpha=3   e_pass=", ge_add["passed"], "peak0=", ge_add["peak_at_lag0"], "prof=", ge_add["profile_fullH"], flush=True)

# additive but scaled to pred dispersion (alpha huge)
addv2 = ab.corrupt_inject_lookahead(champ3, THR["seed"], alpha=60.0)
ge_add2 = ab.gate_e_forward(addv2, THR)
print("ADDITIVE alpha=60  e_pass=", ge_add2["passed"], "peak0=", ge_add2["peak_at_lag0"], "prof=", ge_add2["profile_fullH"], flush=True)

# rank-replacement: pred := Yraw_{t+H} (pure forward window) — my v1 caliber
H, T = champ3.horizon, champ3.pred.shape[0]
rep = ab._clone(champ3); rep.name = "rep_lookahead"
inj = np.full_like(champ3.pred, np.nan); inj[:T-H] = champ3.Yraw[H:]
ok = np.isfinite(champ3.pred) & np.isfinite(inj)
rep.pred = np.full_like(champ3.pred, np.nan); rep.pred[ok] = inj[ok]; rep.point = rep.pred.copy()
rep.finalize()
ge_rep = ab.gate_e_forward(rep, THR)
print("REPLACE (pure fwd) e_pass=", ge_rep["passed"], "peak0=", ge_rep["peak_at_lag0"], "prof=", ge_rep["profile_fullH"], flush=True)

json.dump(dict(pred_std=float(np.nanstd(champ3.pred)), yraw_std=float(np.nanstd(champ3.Yraw)),
               additive_a3=dict(passed=ge_add["passed"], prof=ge_add["profile_fullH"]),
               additive_a60=dict(passed=ge_add2["passed"], prof=ge_add2["profile_fullH"]),
               replace=dict(passed=ge_rep["passed"], prof=ge_rep["profile_fullH"])),
          open("/tmp/0c_echeck.json", "w"), indent=1, default=str)
print("SAVED /tmp/0c_echeck.json", flush=True)
