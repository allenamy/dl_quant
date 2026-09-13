#!/usr/bin/env python3
"""t1_add_posthoc_split.py — Mac. ADDENDUM 1 X3 supplement (POST-HOC DESCRIPTIVE; not in the spec's reading rule):
ledger price split at the D2 frontier so that the late segment is comparable with D2 (08-31 00Z..09-10 00Z) and the 09-10 04Z..09-11 20Z tail separately."""
import os, sys, json, time, hashlib, calendar
import numpy as np
T1 = os.path.abspath(sys.argv[1])
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
Rz = np.load(T1 + "/receipts/T1_real_names.npz", allow_pickle=True); A = Rz["anchors"]; c = [str(x) for x in Rz["anchor_cols"]]; i = {k: j for j, k in enumerate(c)}
D = np.load(T1 + "/receipts/pod2/T1_d2.npz", allow_pickle=True); DC = [str(x) for x in D["cols"]]; DD = D["D"]; di = {k: j for j, k in enumerate(DC)}
ts = A[:, i["A"]].astype(np.int64); price = A[:, i["price"]] / A[:, i["gross"]] * 1e4; carry = -A[:, i["fund"]] / A[:, i["gross"]] * 1e4
dts = DD[:, di["A"]].astype(np.int64); dprice = DD[:, di["price"]]; dcarry = DD[:, di["carry"]]
T = lambda *a: calendar.timegm(a + (0, 0))
segs = dict(E1_0826_04Z_0830_20Z=(T(2026, 8, 26, 4), T(2026, 8, 30, 20)), E2a_0831_00Z_0910_00Z=(T(2026, 8, 31, 0), T(2026, 9, 10, 0)), E2b_0910_04Z_0911_20Z=(T(2026, 9, 10, 4), T(2026, 9, 11, 20)),
            ALL_0826_04Z_0911_20Z=(T(2026, 8, 26, 4), T(2026, 9, 11, 20)), ALL_to_0910_00Z=(T(2026, 8, 26, 4), T(2026, 9, 10, 0)), P1like_to_0911_00Z=(T(2026, 8, 26, 4), T(2026, 9, 11, 0)))
out = {}
for k, (lo, hi) in segs.items():
    m = (ts >= lo) & (ts <= hi); md = (dts >= lo) & (dts <= hi)
    out[k] = dict(REAL_n=int(m.sum()), REAL_price=float(price[m].mean()) if m.any() else None, REAL_carry=float(carry[m].mean()) if m.any() else None,
                  D2_n=int(md.sum()), D2_price=float(dprice[md].mean()) if md.any() else None, D2_carry=float(dcarry[md].mean()) if md.any() else None)
json.dump(dict(self_sha256=sha(os.path.abspath(__file__)), label="ADDENDUM 1 X3 supplement, POST-HOC DESCRIPTIVE", result=out, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), open(T1 + "/receipts/RECEIPT_T1_addendum1_posthoc_split.json", "w"), indent=1)
print(json.dumps(out, indent=1))
