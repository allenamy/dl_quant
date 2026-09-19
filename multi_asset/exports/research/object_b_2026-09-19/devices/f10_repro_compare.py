#!/usr/bin/env python3
"""F-REPRO comparator (PREREG §3 S2; comparison type (3) packaging parity — no returns).
Compares two refit checkpoints: bitwise equality of every state_dict tensor, mu, sd, alpha and the validation curve => PASS.
Otherwise scores the SAME 30,000 real feature rows the in-service export's gate V1 uses (default_rng(0) choice over dlw_fea82 rows) with both
models (torch eval, CPU) and applies the pre-registered numeric rule: Spearman >= 0.99999 and max|d| <= 1e-5 => REPRO_NUMERIC, else NEW_DRAW.
usage: f10_repro_compare.py <ckpt_ref> <ckpt_new> <out.json> [--expect-different]   (--expect-different = negative control: PASS/REPRO_NUMERIC => exit 3)"""
import hashlib, json, os, sys, time
import numpy as np
import torch, torch.nn as nn
from scipy.stats import spearmanr

ref_p, new_p, out_p = sys.argv[1:4]; neg = "--expect-different" in sys.argv
DLW = "/workspace/dlw_ext"; F8 = "/workspace/f8_ext"


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


A = torch.load(ref_p, map_location="cpu", weights_only=False); B = torch.load(new_p, map_location="cpu", weights_only=False)
rec = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "comparison_type": "(3) packaging/prediction parity — not a return",
       "ref": ref_p, "ref_sha256": sha(ref_p), "new": new_p, "new_sha256": sha(new_p), "negative_control": neg, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
keys = sorted(set(A["state_dict"]) | set(B["state_dict"]))
diff = {}
for k in keys:
    a = A["state_dict"].get(k); b = B["state_dict"].get(k)
    diff[k] = None if (a is None or b is None) else (0.0 if torch.equal(a, b) else float((a.double() - b.double()).abs().max()))
diff["mu"] = 0.0 if torch.equal(A["mu"], B["mu"]) else float((A["mu"].double() - B["mu"].double()).abs().max())
diff["sd"] = 0.0 if torch.equal(A["sd"], B["sd"]) else float((A["sd"].double() - B["sd"].double()).abs().max())
rec["tensor_max_abs_diff"] = diff
rec["meta"] = {k: [A.get(k), B.get(k)] for k in ("alpha", "best_va", "trained_through", "seed", "va_curve")}
bitwise = all(v == 0.0 for v in diff.values()) and A.get("va_curve") == B.get("va_curve") and A.get("alpha") == B.get("alpha")
rec["bitwise"] = bool(bitwise)
if bitwise:
    rec["VERDICT"] = "PASS"
else:
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True); F9 = np.load(f"{F8}/data/f8_fea89.npz", allow_pickle=True)
    rng = np.random.default_rng(0); sel = rng.choice(FE["X"].shape[0], 30000, replace=False)
    XL = np.concatenate([FE["X"][sel].astype(np.float32), F9["X"][sel].astype(np.float32)], 1)

    class Net(nn.Module):
        def __init__(s, d=171, h=256, p=0.1):
            super().__init__()
            s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))

    def score(ck):
        n = Net(); n.load_state_dict({k: v for k, v in ck["state_dict"].items() if k.startswith("f.")}); n.eval()
        mu = ck["mu"].numpy().astype(np.float64); sd = ck["sd"].numpy().astype(np.float64)
        xz = np.nan_to_num(np.clip((XL - mu) / sd, -5, 5)).astype(np.float32)
        with torch.no_grad(): return n.f(torch.from_numpy(xz)).squeeze(-1).numpy().astype(np.float64)
    sa, sb = score(A), score(B)
    rho = float(spearmanr(sa, sb).correlation); mx = float(np.abs(sa - sb).max())
    rec["sample"] = {"n_rows": 30000, "spearman": rho, "max_abs": mx, "rows_rule": "default_rng(0).choice(dlw_fea82 rows, 30000) = pod_f10_np_export gate V1 sample"}
    rec["VERDICT"] = "REPRO_NUMERIC" if (rho >= 0.99999 and mx <= 1e-5) else "NEW_DRAW"
json.dump(rec, open(out_p, "w"), indent=1)
print(f"F_REPRO_COMPARE {'NEGCTRL ' if neg else ''}VERDICT {rec['VERDICT']} bitwise={rec['bitwise']} sample={rec.get('sample')}", flush=True)
if neg: sys.exit(3 if rec["VERDICT"] in ("PASS", "REPRO_NUMERIC") else 0)
sys.exit(0)
