#!/usr/bin/env python3
"""Light pre-check for nc_parity_gate.py (no producer, no combo, no window needed): loads the parity pack with the gate's own Pack class and
prints, per reference anchor, the exchangeInfo list size and the coverage at A that the producer's coverage gate will see under each
--exinfo mode ('all' = every crypto name, the lead's spec; 'w24h' = crypto names with a bar in the legal_live window). The producer SKIPs
an anchor below 0.80 — choose the mode before the window. The listing below restates run_one's lines (nc_parity_gate.py, 'exchangeInfo
TRADING list' block); the gate's receipt records its own listing per anchor (runs.<A>.exinfo), which is authoritative.
usage: ~/wide_shadow/venv/bin/python nc_parity_precheck.py <parity pack npz>"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_sandbox_lib as L
from nc_parity_gate import Pack

cfg = json.load(open(f"{L.WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
pk = Pack(sys.argv[1], syms, np.array(L.crypto_axis_json(syms)["crypto"], bool), need_ref=True)
for A in sorted(int(x) for x in pk.z["ref_anchors"]):
    ia_ = int(np.searchsorted(pk.rts, A)); seg = pk.rows[max(ia_ - 290, 0):ia_ + 1]
    w24 = np.isfinite(seg[:, :, 3].astype(np.float32)).any(0) | np.isfinite(seg[:, :, 4].astype(np.float32)).any(0)
    at_A = np.isfinite(pk.rows[ia_, :, 3].astype(np.float32))
    row = {}
    for mode, sel in (("all", np.ones(len(pk.cols), bool)), ("w24h", w24)):
        cov = round(float((at_A & sel).sum()) / max(int(sel.sum()), 1), 4); row[mode] = {"listed": int(sel.sum()), "coverage_at_A": cov, "producer_skips": cov < 0.80}
    print("NC_PARITY_PRECHECK", A, json.dumps(row), flush=True)
