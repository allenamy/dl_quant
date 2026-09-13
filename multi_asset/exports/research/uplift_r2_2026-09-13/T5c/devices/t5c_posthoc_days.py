#!/usr/bin/env python3
"""t5c_posthoc_days.py — Mac, POST-HOC descriptive (not in PREREG_T5c): per-anchor correlation and per-UTC-day means of deployed vs replay king-chain
price and net over the T5c window, read only from receipts/pod2/T5c_bridge_components.npz (sha asserted against the bridge receipt)."""
import os, sys, json, hashlib, time
T = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
BR = json.load(open(T + "/receipts/pod2/RECEIPT_T5c_bridge.json")); P = T + "/receipts/pod2/T5c_bridge_components.npz"; assert sha(P) == BR["components_npz_sha256"]
Z = np.load(P); CAL = [int(x) for x in Z["CAL"]]; WIN = set(int(x) for x in Z["WIN"]); kW = [k for k, A in enumerate(CAL) if A in WIN]
out = dict(label="POST-HOC descriptive; not a pre-registered reading", seeds={})
for tag in ("KA_s42", "KA_s2027"):
    o = {}
    for q in ("P", "N"):
        dk = Z["DK_" + q][kW]; rk = Z[f"{tag}_{q}_V"][0][kW]
        days = {}
        for k, a, b in zip(kW, dk, rk): days.setdefault(time.strftime("%m-%d", time.gmtime(CAL[k])), []).append((a, b))
        o[q] = dict(corr_per_anchor=float(np.corrcoef(dk, rk)[0, 1]), same_sign_share=float(np.mean(np.sign(dk) == np.sign(rk))),
                    per_day={d: dict(n=len(v), D_K=float(np.mean([x[0] for x in v])), R_K=float(np.mean([x[1] for x in v]))) for d, v in sorted(days.items())},
                    worst5_D_K_anchors=[dict(anchor=time.strftime("%m-%d %HZ", time.gmtime(CAL[kW[i]])), D_K=float(dk[i]), R_K=float(rk[i])) for i in np.argsort(dk)[:5]])
    out["seeds"][tag] = o
out["self_sha256"] = sha(os.path.abspath(__file__)); out["components_sha256"] = sha(P); out["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(out, open(T + "/receipts/RECEIPT_T5c_posthoc_days.json", "w"), indent=1)
o = out["seeds"]["KA_s42"]["P"]; print("price corr", round(o["corr_per_anchor"], 4), "same-sign", round(o["same_sign_share"], 3)); print({d: (round(v["D_K"], 2), round(v["R_K"], 2)) for d, v in o["per_day"].items()}); print(o["worst5_D_K_anchors"])
print("s2027 price corr", round(out["seeds"]["KA_s2027"]["P"]["corr_per_anchor"], 4))
