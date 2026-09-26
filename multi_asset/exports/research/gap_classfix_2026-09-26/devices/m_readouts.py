#!/usr/bin/env python3
"""Lead item (a) readouts on the run-2 M arms (sandboxes written by gap_fix_replay.sh; production not read). A = 1790409600, arm mhdrop =
members_hist[A-24h] deleted. Per code (current / patched): F10 score Spearman mhdrop vs mhbase (finite names), F10 book Sum|dw| (state_H_f10_A,
the F10-only sidecar book) and the F10 half of the combo (state_H_fc_A), King half (state_H_kc_A), combo target Sum|dw| (target_live weights,
unit = the published file's weights) and drank row-A zero share. usage: m_readouts.py <run2 root> <out json>"""
import json, os, sys, hashlib
import numpy as np
from scipy.stats import spearmanr
root, A = sys.argv[1], 1790409600
def sbx(code, arm): return f"{root}/{code}_{arm}/{A}"
def state(code, arm, leg):
    z = np.load(f"{sbx(code, arm)}/wide_shadow/fea171/state_H_{leg}_{A}.npz"); v = np.zeros(829); v[z["idx"].astype(int)] = z["val"]; return v
def tgt(code, arm): return json.load(open(f"{sbx(code, arm)}/wide_shadow/state/target_live_PARITY/{A}.json"))["weights"]
out = {"device": "m_readouts.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "A": A}
for code in ("current", "patched"):
    b, d = dict(np.load(f"{sbx(code, 'mhbase')}/M_DUMP.npz")), dict(np.load(f"{sbx(code, 'mhdrop')}/M_DUMP.npz"))
    ok = np.isfinite(b["f10"]) & np.isfinite(d["f10"])
    r = {"f10_spearman": float(spearmanr(b["f10"][ok], d["f10"][ok]).correlation), "n_scored": int(ok.sum()),
         "drank_zero_share_rowA": [float((b["drank"] == 0).mean()), float((d["drank"] == 0).mean())]}
    for leg in ("f10", "fc", "kc"):
        x, y = state(code, "mhbase", leg), state(code, "mhdrop", leg)
        r[f"sum_abs_dw_state_H_{leg}"] = float(np.abs(x - y).sum()); r[f"gross_state_H_{leg}"] = float(np.abs(x).sum())
    wb, wd = tgt(code, "mhbase"), tgt(code, "mhdrop"); ks = set(wb) | set(wd)
    r["sum_abs_dw_combo_target"] = float(sum(abs(wb.get(k, 0) - wd.get(k, 0)) for k in ks)); r["gross_combo_target"] = float(sum(abs(v) for v in wb.values()))
    r["combo_target_names_changed"] = int(sum(1 for k in ks if wb.get(k, 0) != wd.get(k, 0)))
    out[code] = r
json.dump(out, open(sys.argv[2], "w"), indent=1); print(json.dumps(out, indent=1))
