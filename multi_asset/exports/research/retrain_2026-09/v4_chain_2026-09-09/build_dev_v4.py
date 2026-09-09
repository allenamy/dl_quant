"""Replay tree for PREREG_v4 §2.5 (A0..A3): health_check/dev_v4.
 meta_newprod_v4.npz = v4 king meta (E_ts 10182 / members / qvk / names) with y4 <- dlw_v4raw y4s (RAW accounting, holefix2 + raw_patch), aligned by E_ts and symbol.
 Self-check: vs meta_newprod_raw.npz (v3 axis 10176, _ext+patch raw accounting): common anchors outside hole neighbourhoods -> y4 equal within 1e-6, members bitwise.
 SLOW files: SLOW_v4.npy (= shadow_bundle_v4 pinned, canonical shape) and SLOW_v3_on_v4axis.npy (v3 pinned aligned by E_ts, NaN on the 6 new anchors).
 FPRED A0: in-service yearly OOS f8_ext/preds/f10_V2MAIN_s{42,2027}.npy (axis 10206) aligned to the v4 DL axis (10212) by E_ts."""
import numpy as np, os, json, time
R = "/workspace/review_scratch"; HC = f"{R}/health_check"; D = f"{HC}/dev_v4"
M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64); rt = {int(x): i for i, x in enumerate(tt)}; idx = np.array([rt[int(x)] for x in E4])
assert np.array_equal(TG["symbols"], np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")["symbols"]), "symbol order"
y4 = TG["y4s"][idx].astype(np.float32)
out = f"{R}/refute_C6_2/altrun/meta_newprod_v4.npz"; M4mem = M4["members"]; np.savez_compressed(out, E_ts=E4, members=M4mem, y4=y4, qvk=M4["qvk"], names=M4["names"]); print("written", out, y4.shape, flush=True)
# self-check vs meta_newprod_raw (v3 axis)
MR = np.load(f"{R}/refute_C6_2/altrun/meta_newprod_raw.npz", allow_pickle=True); ER = MR["E_ts"].astype(np.int64)
H = np.load(f"{R}/holefix2_cells.npz", allow_pickle=True); NEIGH = H["neigh_rows"]; CTS = np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")["ts"].astype(np.int64)
com = np.intersect1d(E4, ER); i4 = np.searchsorted(E4, com); ir = np.searchsorted(ER, com); rows = np.searchsorted(CTS, com)
inn = np.zeros(len(com), bool)
for lo, hi in NEIGH: inn |= (rows >= lo) & (rows <= hi)
a = y4[i4][~inn]; b = MR["y4"][ir][~inn]; fa, fb = np.isfinite(a), np.isfinite(b); M4m = M4["members"]; MRm = MR["members"]   # materialise once
chk = {"n_common": int(len(com)), "n_outside_neigh": int((~inn).sum()), "finite_pattern_equal_outside": bool(np.array_equal(fa, fb)), "y4_maxabs_outside": float(np.abs(a[fa & fb] - b[fa & fb]).max()),
       "members_equal_outside": bool(all(np.array_equal(M4m[i4[k]], MRm[ir[k]]) for k in np.nonzero(~inn)[0])), "qvk_equal_outside": bool(np.array_equal(M4["qvk"][i4][~inn], MR["qvk"][ir][~inn], equal_nan=True))}
print("selfcheck vs meta_newprod_raw:", json.dumps(chk), flush=True)
assert chk["finite_pattern_equal_outside"] and chk["y4_maxabs_outside"] <= 1e-6 and chk["members_equal_outside"] and chk["qvk_equal_outside"], "meta_newprod_v4 self-check FAIL"
# tree
for d in (f"{D}/logs", f"{D}/probe_artifacts", f"{D}/pod_backup_2026-08-21", f"{D}/f8_2026-08-22/preds", f"{R}/king_v4"): os.makedirs(d, exist_ok=True)
def ln(src, dst):
    if os.path.islink(dst) or os.path.exists(dst): os.remove(dst)
    os.symlink(src, dst)
ln(out, f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz")
P4 = np.load("/workspace/shadow_bundle_v4/slow_pred_pinned.npy"); assert P4.shape == (len(E4), 829); np.save(f"{R}/king_v4/SLOW_v4.npy", P4)
ln(f"{R}/king_v4/SLOW_v4.npy", f"{D}/pod_backup_2026-08-21/slow_pred_hist_oos.npy")
for f in ("wide_panel_4h_hist_v2.npz", "nets_histv2_-30_2_42.npy", "nets_histv2_0_0_0.npy"): ln(f"{HC}/dev_alt/pod_backup_2026-08-21/{f}", f"{D}/pod_backup_2026-08-21/{f}")
ln("/workspace/dlw_v4raw", f"{D}/dlw_2026-08-22")
def align(P, src_E, dst_E):
    o = np.full((len(dst_E), P.shape[1]), np.nan, np.float32); r = {int(t): i for i, t in enumerate(src_E)}
    for k, t in enumerate(dst_E):
        i = r.get(int(t))
        if i is not None: o[k] = P[i]
    return o
M3 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); E3 = M3["E_ts"].astype(np.int64); P3 = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
S3 = align(P3, E3, E4); np.save(f"{R}/king_v4/SLOW_v3_on_v4axis.npy", S3); print("SLOW_v3_on_v4axis finite rows", int(np.isfinite(S3).any(1).sum()), "/", len(E4), flush=True)
EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
for s in ("42", "2027"):
    Y = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{s}.npy"); assert Y.shape[0] == len(EX)
    A0 = align(Y, EX, tt); p = f"{D}/f8_2026-08-22/preds/f10_A0_s{s}.npy"; np.save(p, A0); print(p, "finite rows", int(np.isfinite(A0).any(1).sum()), "/", len(tt), flush=True)
rec = {"meta_newprod_v4": out, "selfcheck": chk, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rec, open(f"{D}/BUILD.json", "w"), indent=1); print("DEV_V4_DONE", flush=True)
