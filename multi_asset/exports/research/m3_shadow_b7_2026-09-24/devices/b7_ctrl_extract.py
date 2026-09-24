#!/usr/bin/env python3
"""b7_ctrl_extract.py (pod2, read-only inputs) — positive-control reference for B7: the CERTIFIED research β at 2026-09-18T20Z (the last anchor
of the certified price table x0918r), i.e. the row of M3's β matrix BETA_M3_full.npz (sha 6dcf9782…, built by m3_build_beta.py with m2_lib
from price_full_raw_x0918r), plus, per symbol, whether ANY UNAVAILABLE 5-minute bar of the certified table closes inside the closed interval
[A − 180×4h, A] (those names are excluded from the control's bitwise-level comparison: the certified formula drops their UA bars, a kline
pull cannot see UA marks). Writes one small npz + receipt.
usage: /workspace/venv/bin/python -B b7_ctrl_extract.py <beta_npz> <out_npz>
"""
import sys, json, hashlib, time
import numpy as np

A = 1789761600; H4 = 14400; ROW = 300
BETA_SHA = "6dcf97824f4ba3765e5f902c9a9edbf051f3354f28d2899724998e1c2584de4d"
META = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"; META_SHA = "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


bp, outp = sys.argv[1:3]
assert sha(bp) == BETA_SHA and sha(META) == META_SHA, "pinned inputs"
Z = np.load(bp); i = int(np.nonzero(Z["anchor"].astype(np.int64) == A)[0][0])
PM = np.load(META, allow_pickle=True); g0 = int(PM["grid"][0])
syms = [str(s) for s in Z["symbols"]]; assert syms == [str(s) for s in PM["symbols"]]
ur = PM["unavail_grid_row"].astype(np.int64); uc = PM["unavail_col"].astype(np.int64); tc = g0 + ur * ROW
inwin = (tc >= A - 180 * H4) & (tc <= A)
ua = np.zeros(len(syms), bool); ua[np.unique(uc[inwin])] = True
np.savez(outp, anchor=np.array(A), symbols=np.array(syms), beta=Z["beta"][i], nobs=Z["nobs"][i], est=Z["est"][i], ua_in_window=ua,
         first_fin=PM["first_fin"].astype(np.int64), last_fin=PM["last_fin"].astype(np.int64))
rec = {"device": "b7_ctrl_extract.py", "self_sha256": sha(sys.argv[0]), "beta_npz": [bp, BETA_SHA], "meta": [META, META_SHA], "anchor": A,
       "n_symbols": len(syms), "n_est": int(Z["est"][i].sum()), "n_ua_in_window": int(ua.sum()), "out": [outp, sha(outp)],
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rec, open(outp[:-4] + ".json", "w"), indent=1)
print("B7_CTRL_EXTRACT DONE", json.dumps(rec))
