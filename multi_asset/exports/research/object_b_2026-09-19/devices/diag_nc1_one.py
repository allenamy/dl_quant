#!/usr/bin/env python3
"""Diagnostic for the one anchor where hypothesis H (both swapped members outside sel) does not hold (2026-09-18 08Z, ONEUSDT in sel):
run the combo replay device twice with injection (baseline scores, swapped scores), keep both fc states and target_combo records, and report
for every name whose zf changed: in sel, FTRIM-zeroed in fc (target_combo ftrim.names_fc), H_fc before, H_fc after in both runs. No history."""
import os, sys, json, shutil
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import gate_f as GF

A = int(sys.argv[1]); cfg = json.load(open(BD.SRC["bundle_config"][0])); syms = cfg["symbols_panel"]
fea_src, reader_src, man = BD.stage_sources(); snap = f"{BD.STAGE}/snap/{A}"
res = {}
for tag in ("base", "swap"):
    root = f"/dev/shm/object_b_diag1/{A}_{tag}"; shutil.rmtree(root, ignore_errors=True)
    ws = BL.make_sandbox(root, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); GF.stage_state(ws, A, snap)
    sc = GF.run_scorer(root, ws, A, f"{BD.STAGE}/model/f10_live_s42_np.npz")
    f = sc["f10"].copy(); ok = np.where(np.isfinite(f))[0]; i_hi = int(ok[np.argmax(f[ok])]); i_lo = int(ok[np.argmin(f[ok])])
    if tag == "swap": f[i_hi], f[i_lo] = f[i_lo], f[i_hi]
    r = GF.run_combo(root, ws, A, "inject", scores={"pm": sc["pm"], "f10": f})
    z = np.load(f"{ws}/fea171/state_H_fc_{A}.npz"); fc = np.zeros(829); fc[z["idx"].astype(int)] = z["val"]
    zp = np.load(f"{ws}/fea171/state_H_fc_{A - BL.H4}.npz"); fcp = np.zeros(829); fcp[zp["idx"].astype(int)] = zp["val"]
    tc = json.load(open(f"{ws}/state/target_combo/{A}.json"))
    res[tag] = {"fc": fc, "fc_prev": fcp, "ftrim_fc": tc["ftrim"]["names_fc"], "w3m": tc["w3_masked"], "compare_max_abs_dw": r["compare"].get("max_abs_dw"),
                "names": (syms[int(sc["pm"][i_hi])], syms[int(sc["pm"][i_lo])])}
    shutil.rmtree(root, ignore_errors=True)
col = {s: j for j, s in enumerate(syms)}
out = {"anchor": A, "utc": BL.iso(A), "swapped": res["swap"]["names"], "w3_masked": res["base"]["w3m"], "fc_state_max_abs_diff": float(np.abs(res["base"]["fc"] - res["swap"]["fc"]).max()),
       "per_name": {n: {"H_fc_prev": float(res["base"]["fc_prev"][col[n]]), "H_fc_base": float(res["base"]["fc"][col[n]]), "H_fc_swap": float(res["swap"]["fc"][col[n]]),
                        "ftrim_fc_base": n in res["base"]["ftrim_fc"], "ftrim_fc_swap": n in res["swap"]["ftrim_fc"]} for n in res["swap"]["names"]},
       "band": cfg["params"]["band"], "alpha": cfg["params"]["alpha"]}
json.dump(out, open(f"{GF.OUTD}/DIAG_NC1_one_{A}.json", "w"), indent=1); print(json.dumps(out, indent=1))
