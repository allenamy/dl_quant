"""R9 reconnaissance (READ-ONLY). No env is consulted: ENV whitelist = EMPTY SET."""
import os, json, time, hashlib, numpy as np
READ_ENV = []          # E-0826-D: analysis script -> empty whitelist
assert READ_ENV == []
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
R = {}
# --- axes ---
for k, p in [("targets_inc", "/workspace/dlw_v4raw/data/dlw_targets.npz"),
             ("targets_ext", "/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz")]:
    z = np.load(p, allow_pickle=True); E = z["E_ts"].astype(np.int64)
    R[k] = {"path": p, "sha16": sha(p)[:16], "n": int(len(E)), "first": iso(E[0]), "last": iso(E[-1]),
            "grid_ok": bool(np.all(np.diff(E) == 14400)), "nsym": int(z["y4s"].shape[1])}
# --- fea shapes/shas ---
for k, p in [("fea82_inc", "/workspace/dlw_v4raw/data/dlw_fea82.npz"),
             ("fea82_hf3", "/workspace/dlw_hf3/data/dlw_fea82.npz"),
             ("fea82_ext", "/workspace/uplift_2026-09-11/r6/out/dlw_hf3_x0910/data/dlw_fea82.npz"),
             ("fea89_inc", "/workspace/f8_v4/data/f8_fea89.npz"),
             ("fea89_ext", "/workspace/uplift_2026-09-11/r6/out/f8_v4_x0910/data/f8_fea89.npz")]:
    z = np.load(p, allow_pickle=True)
    R[k] = {"path": p, "sha16": sha(p)[:16], "keys": sorted(z.files), "X_shape": list(z["X"].shape)}
# --- fold artifact ---
pf = "/workspace/f8_v4/mwf/RAW_s42/shard3/preds_fold/mE1cX7_202608.npz"
z = np.load(pf)
R["preds_fold_202608_s42"] = {"path": pf, "sha16": sha(pf)[:16], "keys": sorted(z.files),
    "first_te": int(z["first_te"]), "last_te": int(z["last_te"]), "E_first": int(z["E_first"]),
    "E_first_iso": iso(int(z["E_first"])), "P_shape": list(z["P"].shape), "P_dtype": str(z["P"].dtype),
    "P_finite_rows": int(np.isfinite(z["P"]).any(1).sum()), "P_finite_frac": float(np.isfinite(z["P"]).mean())}
ck = "/workspace/f8_v4/mwf/RAW_s42/shard3/models/mE1cX7_202608.pt"
R["ckpt_202608_s42"] = {"path": ck, "sha16": sha(ck)[:16]}
# --- f10_A0 vs f10_v4RAW lineage (the arm the live book A0 uses) ---
D = "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"
Einc = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
for s in ("42", "2027"):
    for tag in ("f10_A0_s%s" % s, "f10_v4RAW_s%s" % s):
        p = "%s/%s.npy" % (D, tag); A = np.load(p, mmap_mode="r")
        fin = np.isfinite(np.asarray(A)).any(1)
        idx = np.nonzero(fin)[0]
        R[tag] = {"path": p, "sha16": sha(p)[:16], "shape": list(A.shape),
                  "n_finite_rows": int(fin.sum()), "first_finite": iso(Einc[idx[0]]), "last_finite": iso(Einc[idx[-1]]),
                  "last5_finite_anchors": [iso(Einc[i]) for i in idx[-5:]]}
# overlap difference A0 vs v4RAW on 2026 rows
A0 = np.asarray(np.load("%s/f10_A0_s42.npy" % D)); V4 = np.asarray(np.load("%s/f10_v4RAW_s42.npy" % D))
m26 = Einc >= 1767225600  # 2026-01-01
ok = np.isfinite(A0) & np.isfinite(V4) & m26[:, None]
R["A0_vs_v4RAW_s42_2026"] = {"n_cells_both_finite": int(ok.sum()),
    "maxabs": float(np.abs(A0[ok] - V4[ok]).max()) if ok.any() else None,
    "identical": bool(ok.any() and np.array_equal(A0[ok], V4[ok])),
    "corr": float(np.corrcoef(A0[ok], V4[ok])[0, 1]) if ok.sum() > 10 else None}
# --- is there any saved model for the A0 (yearly) lineage? ---
R["f8_ext_models"] = sorted(os.listdir("/workspace/f8_ext/models"))
R["f8_v4_models_dir"] = sorted(os.listdir("/workspace/f8_v4/models"))
print(json.dumps(R, indent=1))
