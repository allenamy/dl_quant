#!/usr/bin/env python3
"""Diagnostic (not a gate, no history): why did GATE F's NC1 (swap the top- and bottom-scored members' F10 scores) leave the target unchanged
on some anchors? Hypothesis H: the two swapped members are outside the combo stage's liquidity selection `sel` (combo_stage L38–42:
qv4h = expm1(clip(mean log_qv over the last 2016 rows, 0, 30)) × 48 >= params.qv4h_min), so chain() zeroes their z (L79) whatever their score.
Per anchor: recompute the live-model scores with the same scorer as the gate, identify the two swapped members, and report their sel flags and
qv4h. H predicts: NC1 unchanged <=> both swapped members outside sel. Reads the staged gate inputs only; writes receipts/gate_f/DIAG_NC1.json."""
import os, sys, json, shutil
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import gate_f as GF

A = int(sys.argv[1])
fea_src, reader_src, man = BD.stage_sources()
root = f"/dev/shm/object_b_diag/{A}"; shutil.rmtree(root, ignore_errors=True)
ws = BL.make_sandbox(root, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); GF.stage_state(ws, A, f"{BD.STAGE}/snap/{A}")
sc = GF.run_scorer(root, ws, A, f"{BD.STAGE}/model/f10_live_s42_np.npz")
cfg = json.load(open(BD.SRC["bundle_config"][0])); P = cfg["params"]; syms = cfg["symbols_panel"]
R = np.load(f"{BD.STAGE}/snap/{A}/rolling.npz", allow_pickle=True); rts = R["ts"].astype(np.int64); RD = R["data"]
ai = int(np.searchsorted(rts, A, side="right")) - 1
qseg = RD[max(ai + 1 - 2016, 0):ai + 1, :, 3].astype(np.float32); finq = np.isfinite(qseg)
qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
pm = sc["pm"]; qv4h = np.expm1(np.clip(qvm[pm], 0, 30)) * 48; sel = qv4h >= P["qv4h_min"]
f = sc["f10"]; ok = np.where(np.isfinite(f))[0]; i_hi = int(ok[np.argmax(f[ok])]); i_lo = int(ok[np.argmin(f[ok])])
g = json.load(open(f"{GF.OUTD}/GATE_F_{A}.json"))
out = {"anchor": A, "utc": BL.iso(A), "nc1_unchanged": not g["NC1"]["must_differ_ok"],
       "hi": {"name": syms[int(pm[i_hi])], "in_sel": bool(sel[i_hi]), "qv4h": float(qv4h[i_hi])},
       "lo": {"name": syms[int(pm[i_lo])], "in_sel": bool(sel[i_lo]), "qv4h": float(qv4h[i_lo])},
       "n_sel": int(sel.sum()), "n_pm": int(len(pm)), "qv4h_min": P["qv4h_min"]}
out["both_outside_sel"] = (not out["hi"]["in_sel"]) and (not out["lo"]["in_sel"])
out["H_consistent"] = out["nc1_unchanged"] == out["both_outside_sel"]
os.makedirs(GF.OUTD, exist_ok=True); json.dump(out, open(f"{GF.OUTD}/DIAG_NC1_{A}.json", "w"), indent=1)
print(json.dumps(out)); shutil.rmtree(root, ignore_errors=True)
