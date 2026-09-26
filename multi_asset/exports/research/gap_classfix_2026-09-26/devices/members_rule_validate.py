#!/usr/bin/env python3
"""V1 / V2 of ACCEPTANCE AMENDMENT 2 (read-only on ~/wide_shadow/state/snap; writes only --out).
V1: members_at(S) from snapshot S's own inputs == members_hist[S] (every complete snapshot).
V2: for T = S-4h..S-24h: members_at(T) from S's inputs vs members_hist[T]; and carry-forward members_hist[T-4h] vs members_hist[T].
usage: ~/wide_shadow/venv/bin/python members_rule_validate.py <tree>/fea171 --out RECEIPT.json"""
import argparse, hashlib, json, os, sys, time
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("fea"); ap.add_argument("--out", required=True); a = ap.parse_args()
WS = os.path.expanduser("~/wide_shadow")
sys.path.insert(0, f"{WS}/fea171")                         # production nc_contract / tradability (read-only imports)
import nc_contract as NC, tradability as TR
sys.path.insert(0, a.fea)
import importlib; MR = importlib.import_module("members_rule")
assert os.path.dirname(os.path.abspath(MR.__file__)) == os.path.abspath(a.fea)
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); P = cfg["params"]; syms = cfg["symbols_panel"]
cr = json.load(open(f"{WS}/shadow_bundle/crypto_axis.json")); assert list(cr["symbols"]) == list(syms)
crypto = np.array([bool(x) for x in cr["crypto"]], bool)
snaps = sorted(int(d) for d in os.listdir(f"{WS}/state/snap") if d.isdigit() and os.path.exists(f"{WS}/state/snap/{d}/COMPLETE")
               and os.path.exists(f"{WS}/state/snap/{d}/rolling.npz") and os.path.exists(f"{WS}/state/snap/{d}/members_hist.npz"))
def jac(x, y):
    x, y = set(map(int, x)), set(map(int, y)); return len(x & y) / max(len(x | y), 1)
V1, V2 = [], []
for S in snaps:
    d = f"{WS}/state/snap/{S}"
    with np.load(f"{d}/rolling.npz") as z: cts = z["ts"].astype(np.int64); cd = z["data"]
    assert cd.dtype == np.float16
    aux = json.load(open(f"{d}/aux.json")); assert aux["last_anchor"] == S
    with np.load(f"{d}/members_hist.npz") as m:
        MH = {int(m["anchors"][k]): m["idx"][m["off"][k]:m["off"][k + 1]].astype(np.int64) for k in range(len(m["anchors"]))}
    fm = MR.fetch_mask_from_aux(aux, syms)
    got = MR.members_at(cts, cd, S, crypto, fm, P, TR, NC)
    V1.append({"S": S, "equal": bool(np.array_equal(got, MH[S])), "n": [int(len(got)), int(len(MH[S]))], "jaccard": round(jac(got, MH[S]), 6)})
    for lag in range(1, 7):
        T = S - lag * 14400
        if T not in MH or (T - 14400) not in MH: continue
        r = MR.members_at(cts, cd, T, crypto, fm, P, TR, NC)
        V2.append({"S": S, "T": T, "lag": lag, "recompute_equal": bool(np.array_equal(r, MH[T])), "recompute_jaccard": round(jac(r, MH[T]), 6),
                   "recompute_diff": [sorted(syms[i] for i in set(map(int, r)) - set(map(int, MH[T]))), sorted(syms[i] for i in set(map(int, MH[T])) - set(map(int, r)))],
                   "carry_equal": bool(np.array_equal(MH[T - 14400], MH[T])), "carry_jaccard": round(jac(MH[T - 14400], MH[T]), 6)})
v1_ok = len(V1) >= 8 and all(r["equal"] for r in V1)
mr = float(np.mean([r["recompute_jaccard"] for r in V2])); mc = float(np.mean([r["carry_jaccard"] for r in V2]))
by_lag = {lag: {"n": sum(1 for r in V2 if r["lag"] == lag), "recompute_equal": sum(r["recompute_equal"] for r in V2 if r["lag"] == lag),
                "carry_equal": sum(r["carry_equal"] for r in V2 if r["lag"] == lag)} for lag in range(1, 7)}
choice = "recompute" if mr >= mc else "carry_forward"
rec = {"device": "members_rule_validate.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
       "members_rule_sha256": hashlib.sha256(open(MR.__file__, "rb").read()).hexdigest(), "producer_shadow_loop_sha256": hashlib.sha256(open(f"{WS}/shadow_loop_v3.py", "rb").read()).hexdigest(),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "snapshots": snaps,
       "V1": {"PASS": v1_ok, "rows": V1}, "V2": {"n": len(V2), "recompute_mean_jaccard": mr, "carry_mean_jaccard": mc,
       "recompute_all_equal": sum(r["recompute_equal"] for r in V2), "carry_all_equal": sum(r["carry_equal"] for r in V2), "by_lag": by_lag, "choice": choice, "rows": V2}}
with open(a.out, "w") as f: json.dump(rec, f, indent=1)
print(f"V1 {'PASS' if v1_ok else 'FAIL'} {sum(r['equal'] for r in V1)}/{len(V1)}")
print(f"V2 n={len(V2)} recompute: all-equal {rec['V2']['recompute_all_equal']} mean J {mr:.6f} | carry: all-equal {rec['V2']['carry_all_equal']} mean J {mc:.6f} | by_lag {json.dumps(by_lag)} ⇒ choice={choice}")
sys.exit(0 if v1_ok else 1)
