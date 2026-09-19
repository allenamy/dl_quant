#!/usr/bin/env python3
"""Diagnostic (not a gate, no history): the NC1r draws that did not change the target under AMENDMENT 3 (09-17 12Z PHA/BANK, 09-18 20Z IO/PAXG).
Hypothesis B: the combo stage's neutral band (combo_stage L90–92: smv = H + α(tgt − H); |smv − H| < params.band ⇒ keep H) absorbs the swap.
Test: in a sandbox copy of the bundle config with band = 0 (everything else identical), run the injected combo with the baseline scores and with
the swapped scores; B predicts the two targets DIFFER with band 0 while they are identical with the production band. Also reports the fc state
diff under the production band. Reads the staged gate inputs only; writes receipts/gate_f/DIAG_NC1r_band_<A>.json."""
import os, sys, json, shutil
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import gate_f as GF

A = int(sys.argv[1]); tag = sys.argv[2]
g = json.load(open(f"{GF.OUTD}/GATE_F_{A}.json")); nc = [x for x in g["NC1r"] if x["tag"] == tag][0]
fea_src, reader_src, man = BD.stage_sources(); snap = f"{BD.STAGE}/snap/{A}"
out = {"anchor": A, "utc": BL.iso(A), "draw": tag, "swapped": nc["swapped"]}
for band_mode in ("production", "zero"):
    runs = {}
    for which in ("base", "swap"):
        root = f"/dev/shm/object_b_diag_band/{A}_{band_mode}_{which}"; shutil.rmtree(root, ignore_errors=True)
        ws = BL.make_sandbox(root, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); GF.stage_state(ws, A, snap)
        if band_mode == "zero":
            c = json.load(open(f"{ws}/shadow_bundle/config.json")); c["params"]["band"] = 0.0; json.dump(c, open(f"{ws}/shadow_bundle/config.json", "w"))
        sc = GF.run_scorer(root, ws, A, f"{BD.STAGE}/model/f10_live_s42_np.npz")
        f = sc["f10"].copy()
        if which == "swap":
            names = [GF.COLN[int(j)] for j in sc["pm"]]; i = names.index(nc["swapped"][0]["name"]); j = names.index(nc["swapped"][1]["name"])
            f[i], f[j] = f[j], f[i]
        GF.run_combo(root, ws, A, "inject", scores={"pm": sc["pm"], "f10": f})
        z = np.load(f"{ws}/fea171/state_H_fc_{A}.npz"); fc = np.zeros(829); fc[z["idx"].astype(int)] = z["val"]
        runs[which] = {"fc": fc, "target": BL.target_weights(f"{ws}/state/target_live_combo/{A}.json")[1] if os.path.exists(f"{ws}/state/target_live_combo/{A}.json") else None}
        shutil.rmtree(root, ignore_errors=True)
    ta, tb = runs["base"]["target"], runs["swap"]["target"]
    nd = None if (ta is None or tb is None) else sum(1 for k in set(ta) | set(tb) if ta.get(k) != tb.get(k))
    out[band_mode] = {"fc_state_max_abs_diff": float(np.abs(runs["base"]["fc"] - runs["swap"]["fc"]).max()), "target_names_differing": nd}
out["B_supported"] = bool(out["production"]["target_names_differing"] == 0 and (out["zero"]["target_names_differing"] or 0) > 0)
json.dump(out, open(f"{GF.OUTD}/DIAG_NC1r_band_{A}.json", "w"), indent=1); print(json.dumps(out))
