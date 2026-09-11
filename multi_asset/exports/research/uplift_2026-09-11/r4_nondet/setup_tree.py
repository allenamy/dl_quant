"""P4 dev tree. Copied VERBATIM from r3_xib/setup_tree.py (the tree that reproduced the archived A0 BITWISE),
with f8x = my own preds dir: archived s42/s2027 symlinked in, plus my newly trained same-seed draws."""
import os
R = "/workspace/uplift_2026-09-11/r4_nondet"; D = R + "/dev"
HC = "/workspace/review_scratch/health_check"
BK = D + "/pod_backup_2026-08-21"
os.makedirs(BK, exist_ok=True)
LINKS = {"nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
         "nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         "slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy",
         "wide_fea_hist_meta.npz": "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
         "wide_panel_4h_hist_v2.npz": "/workspace/data/wide_panel_4h_v2ext.npz"}
for k, v in LINKS.items():
    t = BK + "/" + k
    assert os.path.exists(v), v
    if not os.path.islink(t): os.symlink(v, t)
for k, v in {"dlw_2026-08-22": "/workspace/dlw_v4raw", "f8_2026-08-22": R + "/f8x"}.items():
    if not os.path.islink(D + "/" + k): os.symlink(v, D + "/" + k)
os.makedirs(R + "/f8x/preds", exist_ok=True)
for s in ("42", "2027"):
    p = R + "/f8x/preds/f10_A0_s%s.npy" % s
    if not os.path.islink(p): os.symlink(HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s%s.npy" % s, p)
print("TREE_OK")
