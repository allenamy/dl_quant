"""Seat quantification (lead 2026-09-24, read-only). One anchor (the replay's last ready anchor). Formulas copied from combo_stage.py
treeNC5 363dd8c8: w3m masking L282-283, z_kc / z_fc L284-285, FTRIM L290-305 (z<0 & rn8<=-0.001 -> 0), chain target L121-132
(sel = qv4h >= qv4h_min; demean over sel; L1; clip cap_mult/n_sel; L1), zf L229 (rank/(n-1) - 0.5), combo_raw = 0.55 kc + 0.45 fc L322.
Inputs: news2 legs.npz (KZ, ZFD, QV, RN8, WL, E_ts) and f10_s42 F10_OOF.npz (P). No EMA / band / exec_reshape (state-dependent)."""
import json, hashlib, sys
import numpy as np
from scipy.stats import rankdata
Wd = "/dev/shm/news2_2026-09-23"; LP = f"{Wd}/work/legs.npz"; FP = f"{Wd}/work/f10_s42/F10_OOF.npz"; CP = f"{Wd}/inputs/bundle_config.json"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
L = np.load(LP); F = np.load(FP); P = json.load(open(CP))["params"]
assert np.array_equal(L["E_ts"], F["E_ts"])
i = int(np.flatnonzero(L["ready"])[-1]); A = int(L["E_ts"][i])
KZ = L["KZ"][i].astype(np.float64); m = np.flatnonzero(np.isfinite(KZ)); assert len(m) >= 50
kz = KZ[m]; zfd = L["ZFD"][i, m].astype(np.float64); qv = L["QV"][i, m].astype(np.float64); rn8 = L["RN8"][i, m].astype(np.float64)
p = F["P"][i, m].astype(np.float64); okf = np.isfinite(p); zf = np.full(len(m), np.nan); zf[okf] = rankdata(p[okf]) / max(okf.sum() - 1, 1) - 0.5
sel = qv >= P["qv4h_min"]
def tgt(z):
    w = np.where(sel, z, 0.0); w = np.where(sel, w - w[sel].mean(), w); w = w / np.abs(w).sum()
    capw = P["cap_mult"] / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); return w / np.abs(w).sum()
def book(wk, wf):
    zk = wk * np.nan_to_num(kz) + wf * np.nan_to_num(zfd); zc = wk * np.nan_to_num(zf) + wf * np.nan_to_num(zfd)
    ft = lambda z: np.where((z < 0) & np.isfinite(rn8) & (rn8 <= -0.0010), 0.0, z)
    zk, zc = ft(zk), ft(zc); tk, tc = tgt(zk), tgt(zc)
    s = lambda a, b: float(a * np.abs(np.nan_to_num(b)[sel]).sum())
    return {"tgt_kc": tk, "tgt_fc": tc, "combo_raw": 0.55 * tk + 0.45 * tc,
            "kc_share_king": s(wk, kz) / (s(wk, kz) + s(wf, zfd)), "fc_share_f10": s(wk, zf) / (s(wk, zf) + s(wf, zfd))}
wl = L["WL"][i].astype(np.float64); rep = [wl[0] / (wl[0] + wl[2]), wl[2] / (wl[0] + wl[2])]
seats = {"live_2026-09-19T00Z(target_combo/1789776000.json)": [0.383352, 0.616648], "replay_NC_s42_legs.WL_2026-09-19T00Z": rep,
         "live_2026-09-24T00Z(target_combo/1790208000.json)": [0.400266, 0.599734]}
B = {k: book(*v) for k, v in seats.items()}
ks = list(B); out = {"anchor": A, "anchor_row": i, "n_members": int(len(m)), "n_sel": int(sel.sum()), "n_f10_finite": int(okf.sum()),
                     "legs_npz_sha256": sha(LP), "f10_oof_sha256": sha(FP), "bundle_config_sha256": sha(CP), "replay_WL_raw": [float(x) for x in wl],
                     "seats_masked": {k: [round(float(x), 6) for x in v] for k, v in seats.items()},
                     "leg_shares": {k: {"kc_share_king": round(B[k]["kc_share_king"], 4), "fc_share_f10": round(B[k]["fc_share_f10"], 4)} for k in ks}}
def d(a, b):
    x, y = B[a], B[b]
    return {"L1_combo_raw_diff": round(float(np.abs(x["combo_raw"] - y["combo_raw"]).sum()), 5),
            "L1_tgt_kc_diff": round(float(np.abs(x["tgt_kc"] - y["tgt_kc"]).sum()), 5), "L1_tgt_fc_diff": round(float(np.abs(x["tgt_fc"] - y["tgt_fc"]).sum()), 5),
            "first_anchor_alpha_times_L1": round(float(P["alpha"] * np.abs(x["combo_raw"] - y["combo_raw"]).sum()), 5),
            "sign_flips": int((np.sign(x["combo_raw"]) != np.sign(y["combo_raw"])).sum())}
out["diff_live0919_vs_replay0919"] = d(ks[0], ks[1]); out["diff_live0924_vs_replay0919"] = d(ks[2], ks[1]); out["diff_live0924_vs_live0919"] = d(ks[2], ks[0])
out["params"] = {k: P[k] for k in ("alpha", "cap_mult", "qv4h_min", "msharpe_look")}
print(json.dumps(out, indent=1))
