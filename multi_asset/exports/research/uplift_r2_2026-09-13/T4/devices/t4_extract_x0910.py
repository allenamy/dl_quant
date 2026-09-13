#!/usr/bin/env python3
"""t4_extract_x0910.py — pod2, READ-ONLY input extraction for the live-window gates (PREREG_T4 §6). No statistic computed.
Copies, for anchors >= 2026-09-05 12Z, the funding columns of the r6 extension panel (training recipe, September funding
from an independent REST pull) and the accounting y4s rows of the r6 extension meta, with their symbol axes and file sha.
Output: /workspace/uplift_r2_2026-09-13/T4/private_inputs/x0910_live_window.npz + receipt."""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
T4 = "/workspace/uplift_r2_2026-09-13/T4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"
assert sha(T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md") == PREREG_SHA
PAN = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"; MET = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"
TGT = "/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz"
INPUTS = {p: sha(p) for p in (PAN, MET, TGT)}
assert INPUTS[PAN] == "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549", INPUTS[PAN]
LO = 1788609600
P = np.load(PAN, allow_pickle=True); pts = P["ts"].astype(np.int64); sel = pts >= LO
M = np.load(MET, allow_pickle=True); mts = M["E_ts"].astype(np.int64); ms = mts >= LO + 14400
T = np.load(TGT, allow_pickle=True)
out = dict(panel_ts=pts[sel], panel_symbols=np.array([str(s) for s in P["symbols"]]), f_fund_ema=P["f_fund_ema"][sel], f_fund_ema_v1=P["f_fund_ema_v1"][sel],
           f_fund_now=P["f_fund_now"][sel], f_fund_iv=P["f_fund_iv"][sel], meta_ts=mts[ms], meta_y4s=M["y4"][ms].astype(np.float32),
           targets_symbols=np.array([str(s) for s in T["symbols"]]), targets_ts_last=np.int64(T["E_ts"].astype(np.int64)[-1]))
os.makedirs(T4 + "/private_inputs", exist_ok=True); op = T4 + "/private_inputs/x0910_live_window.npz"; np.savez_compressed(op, **out)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, output=op, output_sha256=sha(op),
          panel_rows=int(sel.sum()), panel_first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(pts[sel][0]))), panel_last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(pts[sel][-1]))),
          meta_rows=int(ms.sum()), meta_first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(mts[ms][0]))), meta_last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(mts[ms][-1]))),
          symbols_equal_panel_targets=bool(list(out["panel_symbols"]) == list(out["targets_symbols"])), meta_keys=list(M.files),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_extract_x0910.json", "w"), indent=1, default=str); print(json.dumps(RC, indent=1, default=str))
