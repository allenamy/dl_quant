"""E-0909-F: align shadow_bundle_v4e pinned king predictions to the dev_v4 replay axis -> king_v4/SLOW_v4e.npy (same align() as build_dev_v4.py)."""
import numpy as np, json
R = "/workspace/review_scratch"; D = f"{R}/health_check/dev_v4"
M4e = np.load("/workspace/data/wide_fea_v4e_meta.npz", allow_pickle=True); E4e = M4e["E_ts"].astype(np.int64)
P4e = np.load("/workspace/shadow_bundle_v4e/slow_pred_pinned.npy"); assert P4e.shape == (len(E4e), 829), (P4e.shape, len(E4e))
tt = np.load(f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True)["E_ts"].astype(np.int64)
def align(P, src_E, dst_E):
    o = np.full((len(dst_E), P.shape[1]), np.nan, np.float32); r = {int(t): i for i, t in enumerate(src_E)}
    for k, t in enumerate(dst_E):
        i = r.get(int(t))
        if i is not None: o[k] = P[i]
    return o
S = align(P4e, E4e, tt); np.save(f"{R}/king_v4/SLOW_v4e.npy", S)
rep = {"n_src": int(len(E4e)), "n_dev_axis": int(len(tt)), "finite_rows": int(np.isfinite(S).any(1).sum()), "dev_anchors_not_in_v4e": int(len(np.setdiff1d(tt, E4e))), "v4e_anchors_not_in_dev": int(len(np.setdiff1d(E4e, tt)))}
json.dump(rep, open(f"{R}/v4_gates/align_v4e.json", "w"), indent=1); print("ALIGN_V4E_DONE", json.dumps(rep), flush=True)
