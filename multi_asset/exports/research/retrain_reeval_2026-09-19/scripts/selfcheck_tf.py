#!/usr/bin/env python3
"""selfcheck_tf.py — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (9b403aad) §2 自检门.
TRAIN_FRAC = 0.85 on folds 202501 and 202608 must reproduce the baseline (A1 = FP2-8 chain, /workspace/fp2_2026-09/f8_v4/mwf_v4b/RAW_s<seed>)
fold out-of-sample predictions BITWISE; otherwise stop. Compared per (seed, fold): the preds_fold P array (every anchor >= first test anchor,
which is what the merge stitches), first_te/last_te, the saved model state_dict tensors, and the va_curve. The gate folds are 202501 and 202608
(both seeds); any other fold present (202601 = the T2 2026 fold) is compared and reported as INFORMATION, it does not enter the verdict.
usage: selfcheck_tf.py <arm dir, e.g. /workspace/retrain_reeval_2026-09-19/mwf/SELFCHK> <out.json>   (reads <arm dir>_s<seed>/shard*/)
rc 0 = GATE PASS, rc 1 = GATE FAIL, rc 3 = missing input."""
import glob, hashlib, json, os, sys, time
import numpy as np, torch
ARMDIR, OUT = sys.argv[1], sys.argv[2]
BASE = "/workspace/fp2_2026-09/f8_v4/mwf_v4b"; TAG = "mE1cX7"; GATE = [(42, 202501), (42, 202608), (2027, 202501), (2027, 202608)]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def one(path_glob):
    L = sorted(glob.glob(path_glob)); assert len(L) <= 1, L; return L[0] if L else None
rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "arm_dir": ARMDIR, "baseline_dir": BASE,
       "rule": "bitwise: P arrays equal with equal NaN pattern (maxabs == 0), first_te/last_te equal, every state_dict tensor torch.equal, va_curve equal", "cells": {}, "GATE_CELLS": [f"s{s}/{m}" for s, m in GATE]}
rc = 0
for s in (42, 2027):
    for p in sorted(glob.glob(f"{ARMDIR}_s{s}/shard*/preds_fold/{TAG}_*.npz")):
        m = int(os.path.basename(p).split("_")[-1].split(".")[0]); key = f"s{s}/{m}"
        b = one(f"{BASE}/RAW_s{s}/shard*/preds_fold/{TAG}_{m}.npz")
        if b is None: rec["cells"][key] = {"error": "baseline fold missing"}; continue
        za, zb = np.load(p), np.load(b); Pa, Pb = za["P"], zb["P"]
        same_shape = Pa.shape == Pb.shape; fa, fb = np.isfinite(Pa), np.isfinite(Pb)
        nan_eq = bool(same_shape and np.array_equal(fa, fb)); mx = float(np.max(np.abs(Pa[fa & fb] - Pb[fa & fb]))) if nan_eq and fa.any() else float("nan")
        idx_eq = int(za["first_te"]) == int(zb["first_te"]) and int(za["last_te"]) == int(zb["last_te"])
        pa, pb = p.replace("/preds_fold/", "/models/").replace(".npz", ".pt"), b.replace("/preds_fold/", "/models/").replace(".npz", ".pt")
        Sa, Sb = torch.load(pa, map_location="cpu"), torch.load(pb, map_location="cpu")
        st_eq = sorted(Sa) == sorted(Sb) and all(torch.equal(Sa[k], Sb[k]) for k in Sa)
        ca = json.load(open(pa.replace(".pt", "_config.json"))); cb = json.load(open(pb.replace(".pt", "_config.json")))
        va_eq = ca["va_curve"] == cb["va_curve"]
        bit = bool(same_shape and nan_eq and mx == 0.0 and idx_eq and st_eq and va_eq)
        rec["cells"][key] = {"arm_preds_fold": p, "arm_sha256": sha(p), "baseline_preds_fold": b, "baseline_sha256": sha(b), "P_shape": list(Pa.shape), "nan_pattern_equal": nan_eq,
                             "P_maxabs": mx, "first_last_te_equal": idx_eq, "state_dict_equal": bool(st_eq), "va_curve_equal": bool(va_eq), "BITWISE": bit, "in_gate": (s, m) in GATE,
                             "arm_train_frac": ca.get("train_frac"), "arm_self_sha256": ca.get("self_sha256"), "baseline_self_sha256": cb.get("self_sha256"),
                             "arm_grad_last_ts": ca.get("grad_last_ts"), "arm_grad_loss_last_ts": ca.get("grad_loss_last_ts"), "arm_n_grad_anchors": ca.get("n_grad_anchors")}
        print(key, "BITWISE" if bit else "DIFFERS", {k: rec["cells"][key][k] for k in ("P_maxabs", "nan_pattern_equal", "state_dict_equal", "va_curve_equal", "in_gate")}, flush=True)
missing = [f"s{s}/{m}" for s, m in GATE if f"s{s}/{m}" not in rec["cells"] or "error" in rec["cells"][f"s{s}/{m}"]]
ok = not missing and all(rec["cells"][f"s{s}/{m}"]["BITWISE"] and rec["cells"][f"s{s}/{m}"]["arm_train_frac"] == 0.85 for s, m in GATE)
rec["missing_gate_cells"] = missing; rec["GATE"] = "PASS" if ok else ("MISSING" if missing else "FAIL")
json.dump(rec, open(OUT, "w"), indent=1); print("SELFCHECK_GATE", rec["GATE"], "missing", missing, flush=True)
sys.exit(0 if ok else (3 if missing else 1))
