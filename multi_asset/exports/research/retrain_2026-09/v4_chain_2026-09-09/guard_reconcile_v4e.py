"""Reconcile the replica (1.92) against the published v3 guard (2.28): the 09-01 method — compare leg returns against the bundle's own
leg_returns.npz (rev24 exact => panel rev24 same; fund => f_fund_ema_v1 lineage; king => PRED), under panel v2ext and v3splice."""
import numpy as np, json, sys, time
sys.path.insert(0, "/workspace/review_scratch"); from guard_book_lib import book, T, sharpe
M3 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); P3 = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); P4 = np.load("/workspace/shadow_bundle_v4/slow_pred_pinned.npy")
M4e = np.load("/workspace/data/wide_fea_v4e_meta.npz", allow_pickle=True); P4e = np.load("/workspace/shadow_bundle_v4e/slow_pred_pinned.npy")   # E-0909-F
LB = np.load("/workspace/shadow_bundle_v3/leg_returns.npz"); lts = LB["ts"].astype(np.int64)
out = {}
for pname in ("v2ext", "v3splice"):
    PW = np.load(f"/workspace/data/wide_panel_4h_{pname}.npz", allow_pickle=True)
    for name, (P, MT) in (("v3", (P3, M3)), ("v4", (P4, M4)), ("v4e", (P4e, M4e))):
        rec, W3, LRa, idx = book(P, MT, PW); ts = rec[:, 0].astype(np.int64); net = rec[:, 1]; m24 = ts >= T(2024, 1, 1)
        r = {"guard_sharpe": sharpe(net[m24]), "net_mean": float(net[m24].mean()), "n": int(m24.sum())}
        E = MT["E_ts"].astype(np.int64)[idx]; com = np.intersect1d(E, lts); ia = np.searchsorted(E, com); ib = np.searchsorted(lts, com)
        for leg in ("king", "rev24", "fund"):
            a = LRa[leg][ia]; b = LB[leg][ib]; r[f"leg_{leg}_corr_vs_bundle"] = float(np.corrcoef(a, b)[0, 1]); r[f"leg_{leg}_maxabs_vs_bundle"] = float(np.abs(a - b).max()); r[f"leg_{leg}_exact_share"] = float(np.mean(np.abs(a - b) < 1e-9))
        out[f"{name}|{pname}"] = r; print(f"{name} panel={pname}: guard Sharpe {r['guard_sharpe']:.3f} net {r['net_mean']:+.3f} | vs bundle legs: king corr {r['leg_king_corr_vs_bundle']:.6f} exact {r['leg_king_exact_share']:.3f} | rev24 corr {r['leg_rev24_corr_vs_bundle']:.6f} exact {r['leg_rev24_exact_share']:.3f} | fund corr {r['leg_fund_corr_vs_bundle']:.6f} exact {r['leg_fund_exact_share']:.3f}", flush=True)
band = (2.27, 2.57); s4e = out["v4e|v3splice"]["guard_sharpe"]; out["v4e_guard_in_band"] = bool(band[0] <= s4e <= band[1]); out["band"] = band
json.dump(out, open("/workspace/review_scratch/v4_gates/guard_reconcile_v4e.json", "w"), indent=1); print("GUARD_RECONCILE_V4E_DONE in_band", out["v4e_guard_in_band"], flush=True)
import sys as _s; _s.exit(0 if out["v4e_guard_in_band"] else 3)
