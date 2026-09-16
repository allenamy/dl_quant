"""R6 EXTEND step 6: the extended replay tree health_check/dev_v4_x0910, mirroring build_dev_v4.py exactly
(same file names, same symlink layout) so w10_sleeve.py can be pointed at it with no device change.

The DL leg is the one thing that CANNOT be carried forward (see RECEIPT + report): the F10/V2MAIN monthly
walk-forward has folds 202501..202608 only; scoring 2026-09 needs a 202609 fold, which is retraining (PREREG §8.1
forbids it this round). The fold checkpoints are bare state_dicts (keys f.0/f.3/f.6 + 'a') with NO mu/sd, so a
stale-fold forward pass also needs the trainer's fold-specific standardisation reconstructed and gated against
preds_fold/*.npz. Neither was done. The A0 FPRED arrays are therefore written with the incumbent rows aligned by
E_ts and NaN on the 60 new anchors — the gap is VISIBLE in the artifact rather than silently interpolated.
"""
import numpy as np, os, json, time, hashlib
R = "/workspace/review_scratch"; OUT6 = "/workspace/uplift_2026-09-11/r6/out"
D = f"{R}/health_check/dev_v4_x0910"
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<24), b""): h.update(c)
    return h.hexdigest()
M4 = np.load(f"{OUT6}/wide_fea_v4_meta_x0910.npz", allow_pickle=True)
TG = np.load(f"{OUT6}/dlw_targets_x0910.npz", allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64)
rt = {int(x): i for i, x in enumerate(tt)}
missing = [U(x) for x in E4 if int(x) not in rt]
assert not missing, f"king anchors with no DL target row: {missing}"
idx = np.array([rt[int(x)] for x in E4])
y4 = TG["y4s"][idx].astype(np.float32)
os.makedirs(f"{D}/pod_backup_2026-08-21", exist_ok=True); os.makedirs(f"{D}/f8_2026-08-22/preds", exist_ok=True)
os.makedirs(f"{D}/probe_artifacts", exist_ok=True); os.makedirs(f"{D}/logs", exist_ok=True)
meta_out = f"{OUT6}/meta_newprod_v4_x0910.npz"
np.savez_compressed(meta_out, E_ts=E4, members=M4["members"], y4=y4, qvk=M4["qvk"], names=M4["names"])
# regression: the incumbent device meta must be reproduced bitwise on its own axis
MI = np.load(f"{R}/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True)
EI = MI["E_ts"].astype(np.int64); nI = len(EI)
chk = {"prefix_E_ts_equal": bool(np.array_equal(EI, E4[:nI])),
       "prefix_y4_bitwise_equal": bool(np.array_equal(MI["y4"], y4[:nI], equal_nan=True)),
       "prefix_qvk_bitwise_equal": bool(np.array_equal(MI["qvk"], M4["qvk"][:nI], equal_nan=True)),
       "prefix_members_equal": bool(all(np.array_equal(MI["members"][i], M4["members"][i]) for i in range(nI))),
       "incumbent_n": int(nI), "extended_n": int(len(E4))}
print("device meta regression vs meta_newprod_v4:", json.dumps(chk), flush=True)
def ln(src, dst):
    if os.path.islink(dst) or os.path.exists(dst): os.remove(dst)
    os.symlink(src, dst)
ln(meta_out, f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz")
ln(f"{OUT6}/SLOW_v4_x0910.npy", f"{D}/pod_backup_2026-08-21/slow_pred_hist_oos.npy")
ln(f"{OUT6}/wide_panel_4h_v2ext_x0910.npz", f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz")
for f in ("nets_histv2_-30_2_42.npy", "nets_histv2_0_0_0.npy"):
    ln(f"{R}/health_check/dev_alt/pod_backup_2026-08-21/{f}", f"{D}/pod_backup_2026-08-21/{f}")
ln(f"{OUT6}/dlw_v4raw_x0910", f"{D}/dlw_2026-08-22")
# FPRED: incumbent DL preds aligned onto the extended DL axis, NaN on the new anchors (the gap, made visible)
fp = {}
for s in ("42", "2027"):
    src = f"{R}/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s{s}.npy"
    if not os.path.exists(src): fp[s] = {"src_missing": src}; continue
    Y = np.load(src); EX = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
    assert Y.shape[0] == len(EX), (Y.shape, len(EX))
    A0 = np.full((len(tt), Y.shape[1]), np.nan, np.float32)
    r = {int(t): i for i, t in enumerate(EX)}
    for k, t in enumerate(tt):
        i = r.get(int(t))
        if i is not None: A0[k] = Y[i]
    p = f"{D}/f8_2026-08-22/preds/f10_A0_s{s}.npy"; np.save(p, A0)
    fin = np.isfinite(A0).any(1)
    fp[s] = {"path": p, "sha256": sha(p), "finite_rows": int(fin.sum()), "total_rows": int(len(tt)),
             "nan_rows": int((~fin).sum()), "last_finite_anchor": U(tt[np.nonzero(fin)[0][-1]]),
             "first_nan_anchor": U(tt[np.nonzero(~fin)[0][0]]) if (~fin).any() else None}
    print(f"FPRED s{s}: finite rows {fp[s]['finite_rows']}/{fp[s]['total_rows']}, last finite {fp[s]['last_finite_anchor']}", flush=True)
rep = {"tree": D, "meta_out": meta_out, "meta_sha256": sha(meta_out), "regression": chk,
       "axis": {"n": int(len(E4)), "start": U(E4[0]), "end": U(E4[-1])},
       "dl_axis": {"n": int(len(tt)), "end": U(tt[-1])},
       "FPRED": fp,
       "DL_LEG_NOT_EXTENDED": "F10/V2MAIN monthly walk-forward folds are 202501..202608 only; 2026-09 needs a 202609 fold = retraining (PREREG §8.1 forbids). Fold .pt files carry no mu/sd, so a stale-202608-fold forward pass needs the trainer's standardisation reconstructed and gated against preds_fold/*.npz. NOT DONE this round.",
       "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open("/workspace/uplift_2026-09-11/r6/RECEIPT_dev_tree.json","w"), indent=1)
assert chk["prefix_E_ts_equal"] and chk["prefix_y4_bitwise_equal"] and chk["prefix_members_equal"], "device meta regression FAIL"
print("R6_DEV_TREE_DONE", D, flush=True)
