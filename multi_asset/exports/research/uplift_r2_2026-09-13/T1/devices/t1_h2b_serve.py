#!/usr/bin/env python3
"""t1_h2b_serve.py — Mac, read-only copies (PREREG_T1 AMENDMENT 3 item 4).
Served V2MAIN panel value f_fund_ema (last row of the producer's xfer_panel_live.npz, = aux ema acc per combo_stage.py L139-146) versus EMAs
recomputed from the producer ledger copy with (v0) the raw per-settlement rate and (v1) rate*8/iv, same wall-clock HL 3d recursion
(shadow_loop_v3.py L344-349). Median served/v1 and served/v0 over names whose latest recorded iv == 4 and |v0| > 1e-6.
"""
import os, sys, json, time, hashlib
T1 = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
SH = {"PREREG_T1_edge_diagnosis_2026-09-13.md": "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6", "PREREG_AMENDMENT_3_T1_2026-09-13.md": "e6afc13879c6332520d7f3876f2adc212468e98594c312baf5fab035483685e8"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
for f, h in SH.items(): assert sha(T1 + "/" + f) == h, f
XP = T1 + "/private/xfer_panel_live_copy.npz"; XR = T1 + "/private/xfer_ref_copy.npz"; AUX = T1 + "/private/aux_20260913.json"
X = np.load(XP, allow_pickle=True); syms = [str(s) for s in np.load(XR, allow_pickle=True)["symbols"]]
served = X["f_fund_ema"][-1].astype(np.float64); served_now = X["f_fund_now"][-1].astype(np.float64); last_ts = int(X["ts"][-1])
aux = json.load(open(AUX)); LED = aux["ledger_tail"]; EMA = aux["ema"]
def ema(rows, use_iv):
    acc = None; last = None
    for r in rows:
        ft, rate = float(r[0]), float(r[1]); iv = float(r[2]) if (len(r) > 2 and r[2]) else 8.0
        v = rate * (8.0 / iv) if use_iv else rate
        if acc is None: acc = v; last = ft
        else:
            a = 1 - 0.5 ** (max(ft - last, 1) / (3 * 86400.0)); acc = acc + a * (v - acc); last = ft
    return acc
r1, r0, r_aux, names4 = [], [], [], []
for j, s in enumerate(syms):
    rows = LED.get(s)
    if not rows or len(rows) < 50: continue
    if float(rows[-1][2]) != 4.0: continue
    if served[j] == 0.0: continue
    e1 = ema(rows, True); e0 = ema(rows, False)
    if abs(e0) <= 1e-6: continue
    r1.append(served[j] / e1); r0.append(served[j] / e0); names4.append(s)
    if s in EMA: r_aux.append(served[j] / float(EMA[s]["acc"]))
res = dict(xfer_last_row_utc=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(last_ts)), n_names_iv4=len(names4), median_served_over_v1=float(np.median(r1)) if r1 else None,
           median_served_over_v0=float(np.median(r0)) if r0 else None, median_served_over_aux_acc=float(np.median(r_aux)) if r_aux else None,
           p10_p90_served_over_v0=[float(np.percentile(r0, 10)), float(np.percentile(r0, 90))] if r0 else None)
res["serving_caliber"] = ("v1" if (res["median_served_over_v1"] is not None and 0.99 <= res["median_served_over_v1"] <= 1.01 and 1.9 <= res["median_served_over_v0"] <= 2.1) else "NOT v1 by the registered rule")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg=SH, inputs={XP: sha(XP), XR: sha(XR), AUX: sha(AUX)}, result=res,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T1 + "/receipts/RECEIPT_T1_h2b_serve.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1))
