#!/usr/bin/env python3
"""t1_posthoc_live_reconcile.py — Mac. POST-HOC DESCRIPTIVE (not registered; written after the judge showed REAL g +0.05 vs D2 g_pre -3.07).
Reconcile the two live instruments on their COMMON anchors and show which anchors move the window means."""
import os, sys, json, time, hashlib
import numpy as np
T1 = os.path.abspath(sys.argv[1])
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
D = np.load(T1 + "/receipts/pod2/T1_d2.npz", allow_pickle=True); DC = [str(c) for c in D["cols"]]; DD = D["D"]; dci = {c: i for i, c in enumerate(DC)}
Rz = np.load(T1 + "/receipts/T1_real_names.npz", allow_pickle=True); RA = Rz["anchors"]; RAC = [str(c) for c in Rz["anchor_cols"]]; rai = {c: i for i, c in enumerate(RAC)}
L0, L1 = 1787716800, 1789156800
ra = RA[(RA[:, rai["A"]] >= L0) & (RA[:, rai["A"]] <= L1)]
real = {int(r[rai["A"]]): dict(price=r[rai["price"]] / r[rai["gross"]] * 1e4, carry=-r[rai["fund"]] / r[rai["gross"]] * 1e4, cost=-(r[rai["fee"]] + r[rai["timing"]]) / r[rai["gross"]] * 1e4) for r in ra}
d2 = {int(r[dci["A"]]): dict(price=r[dci["price"]], carry=r[dci["carry"]]) for r in DD}
common = sorted(set(real) & set(d2)); only_real = sorted(set(real) - set(d2)); only_d2 = sorted(set(d2) - set(real))
def m(dct, keys, f): return float(np.mean([f(dct[k]) for k in keys])) if keys else None
out = dict(label="POST-HOC DESCRIPTIVE", n_common=len(common), n_only_real=len(only_real), n_only_d2=len(only_d2),
           only_real_utc=[time.strftime("%m-%d %H:%MZ", time.gmtime(a)) for a in only_real], only_d2_utc=[time.strftime("%m-%d %H:%MZ", time.gmtime(a)) for a in only_d2],
           common=dict(real_price=m(real, common, lambda x: x["price"]), real_carry=m(real, common, lambda x: x["carry"]), real_cost=m(real, common, lambda x: x["cost"]),
                       real_g=m(real, common, lambda x: x["price"] - x["carry"] - x["cost"]), d2_price=m(d2, common, lambda x: x["price"]), d2_carry=m(d2, common, lambda x: x["carry"]),
                       d2_g_pre=m(d2, common, lambda x: x["price"] - x["carry"])),
           only_real=dict(real_price=m(real, only_real, lambda x: x["price"]), real_g=m(real, only_real, lambda x: x["price"] - x["carry"] - x["cost"])),
           only_d2=dict(d2_price=m(d2, only_d2, lambda x: x["price"]), d2_g_pre=m(d2, only_d2, lambda x: x["price"] - x["carry"])))
x = np.array([d2[a]["price"] for a in common]); y = np.array([real[a]["price"] for a in common])
b = np.polyfit(x, y, 1); out["common_price_regression_real_on_d2"] = dict(slope=float(b[0]), intercept=float(b[1]), rho=float(np.corrcoef(x, y)[0, 1]))
big = sorted(real, key=lambda a: -abs(real[a]["price"]))[:8]
out["largest_abs_real_price_anchors"] = [dict(utc=time.strftime("%m-%d %H:%MZ", time.gmtime(a)), real_price=float(real[a]["price"]), d2_price=(float(d2[a]["price"]) if a in d2 else None)) for a in big]
json.dump(dict(self_sha256=sha(os.path.abspath(__file__)), result=out), open(T1 + "/receipts/RECEIPT_T1_posthoc_live_reconcile.json", "w"), indent=1)
print(json.dumps(out, indent=1))
