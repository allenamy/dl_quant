"""r14 STEP 1, source-side half: reproduce the dead-leg prefix FROM SOURCE on pod2.

Replicates w10_sleeve.py (sha b88e35a4...) member construction EXACTLY for the archived A0 config
(MEMBERS_TOPN=829 rebuilt from qvk, UMASK_SCOPE=m1 with umask_UPIT_CRYPTO.npz) and reports, per anchor,
how many member-column values of each prediction file are finite.  The device's own gate is xz():
ok.sum() >= 10 else the whole leg becomes NaN and np.nan_to_num turns it into an identically-zero leg.

READ-ONLY.  Touches nothing under ~/dl_quant_live or ~/wide_shadow (not present on this machine anyway).
ENV WHITELIST (E-0826-D) = EMPTY SET, asserted below.
"""
import os, sys, json, hashlib, time
import numpy as np

# ---- E-0826-D: env whitelist = EMPTY SET, asserted ----------------------------------
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
ENV_SEEN = sorted(os.environ.keys())
ENV_WHITELIST = []          # explicitly asserted EMPTY SET
assert ENV_WHITELIST == []

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

PREREG = "/workspace/uplift_2026-09-11/r14_cleanbase/PREREG_r14_clean_baseline_2026-09-12.md"
PREREG_SHA = "89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7"
assert sha(PREREG) == PREREG_SHA, "PREREG sha mismatch -> device refuses to run"

OUT = "/workspace/uplift_2026-09-11/r14_cleanbase"
os.makedirs(OUT, exist_ok=True)
R = {"step": "R14_POD_DEADMASK", "self_sha256": sha(os.path.abspath(__file__)),
     "prereg_sha256": PREREG_SHA, "env_whitelist": ENV_WHITELIST, "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "python": sys.version.split()[0],
     "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

# ---- pinned inputs, exactly as the archived A0 arm names them ------------------------
DEVV4 = "/workspace/review_scratch/health_check/dev_v4"
P_META  = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
P_PANEL = DEVV4 + "/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
P_UMASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
P_SLOW3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
P_SLOW4 = "/workspace/review_scratch/king_v4/SLOW_v4.npy"
P_F10   = DEVV4 + "/f8_2026-08-22/preds/f10_A0_s42.npy"
IN = {"meta_newprod_v4": P_META, "panel_hist_v2": P_PANEL, "umask_UPIT_CRYPTO": P_UMASK,
      "SLOW_v3_on_v4axis": P_SLOW3, "SLOW_v4": P_SLOW4, "f10_A0_s42": P_F10}
R["inputs"] = {k: {"path": os.path.realpath(v), "sha256": sha(v),
                   "bytes": os.path.getsize(v)} for k, v in IN.items()}
for k, v in R["inputs"].items(): print("INPUT %-20s %s  %s" % (k, v["sha256"][:16], v["path"]), flush=True)

MT = np.load(P_META, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); qvk = MT["qvk"]; NW = 829
PW = np.load(P_PANEL, allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pw_ts)}
WSYM = [str(s) for s in PW["symbols"]]

# ---- member reconstruction: w10_sleeve.py L95-101 verbatim ---------------------------
MEMBERS_TOPN = 829
members = np.empty(len(E_ts), dtype=object)
for _i in range(len(E_ts)):
    _q = np.nan_to_num(qvk[_i], nan=-1.0); _ord = np.argsort(-_q); _ord = _ord[_q[_ord] > -0.5]
    members[_i] = np.sort(_ord[:MEMBERS_TOPN]).astype(np.int64)

# ---- umask: w10_sleeve.py L158-170 verbatim, scope m1 --------------------------------
_uz = np.load(P_UMASK, allow_pickle=True)
assert [str(x) for x in _uz["symbols"]] == WSYM, "umask symbols mismatch"
_umap = {int(t): k for k, t in enumerate(_uz["ts"].astype(np.int64))}
_UM = np.asarray(_uz["mask"])
UMASK_ROW = {}
for _j, _t in enumerate(pw_ts):
    _k = _umap.get(int(_t))
    if _k is not None: UMASK_ROW[_j] = _UM[_k]

S3 = np.load(P_SLOW3); S4 = np.load(P_SLOW4); F10raw = np.load(P_F10)
R["shapes"] = {"E_ts": int(len(E_ts)), "SLOW_v3": list(S3.shape), "SLOW_v4": list(S4.shape),
               "f10_A0_s42_raw": list(F10raw.shape), "panel_ts": int(len(pw_ts))}
print("shapes", json.dumps(R["shapes"]), flush=True)

# ---- F10 column alignment: w10_sleeve.py L118-137 verbatim ---------------------------
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
_dts = TG["E_ts"].astype(np.int64); _dsy = [str(x) for x in TG["symbols"]]
_rmap = {int(t): k for k, t in enumerate(_dts)}
_cmap = {s: k for k, s in enumerate(_dsy)}
_cols = np.array([_cmap.get(s, -1) for s in WSYM], np.int64); _okc = _cols >= 0
F10P = np.full((len(E_ts), NW), np.nan, np.float32); _nrow = 0
for _i in range(len(E_ts)):
    _k = _rmap.get(int(E_ts[_i]))
    if _k is None: continue
    F10P[_i, _okc] = F10raw[_k, _cols[_okc]]; _nrow += 1
R["f10_alignment"] = {"rows_aligned": int(_nrow), "of": int(len(E_ts)), "cols": int(_okc.sum()),
                      "finite_frac": float(np.isfinite(F10P).mean())}
print("f10_alignment", json.dumps(R["f10_alignment"]), flush=True)

# ---- per-anchor finite member counts -------------------------------------------------
ts_out = []; nk3 = []; nk4 = []; nf = []; nm = []
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    _mk = UMASK_ROW.get(j)
    if _mk is not None: m = m[_mk[m]]
    ts_out.append(int(E_ts[i])); nm.append(len(m))
    nk3.append(int(np.isfinite(S3[i, m]).sum()))
    nk4.append(int(np.isfinite(S4[i, m]).sum()))
    nf.append(int(np.isfinite(F10P[i, m]).sum()))
ts_out = np.array(ts_out, np.int64)
nk3 = np.array(nk3); nk4 = np.array(nk4); nf = np.array(nf); nm = np.array(nm)
print("anchors with a panel row:", len(ts_out), flush=True)

# ---- row-level coverage of the prediction files (independent of the member set) -------
def firstfin(A):
    fr = np.isfinite(A).any(1)
    return (int(fr.sum()), int(np.argmax(fr)) if fr.any() else -1)
R["row_coverage"] = {}
for nm_, A in (("SLOW_v3_on_v4axis", S3), ("SLOW_v4", S4)):
    n_, i0 = firstfin(A)
    R["row_coverage"][nm_] = {"finite_rows_of_axis": n_, "axis_rows": int(A.shape[0]),
                              "first_finite_row": i0,
                              "first_finite_ts_utc": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(E_ts[i0]))) if i0 >= 0 else None)}
n_, i0 = firstfin(F10P)
R["row_coverage"]["f10_A0_s42_on_axis"] = {"finite_rows_of_axis": n_, "axis_rows": int(F10P.shape[0]),
                                           "first_finite_row": i0,
                                           "first_finite_ts_utc": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(E_ts[i0]))) if i0 >= 0 else None)}
print("row_coverage", json.dumps(R["row_coverage"], indent=1), flush=True)

np.savez_compressed(OUT + "/r14_deadmask.npz", ts=ts_out, n_finite_king_v3=nk3,
                    n_finite_king_v4=nk4, n_finite_f10=nf, n_members=nm)
R["out_npz"] = OUT + "/r14_deadmask.npz"
R["out_npz_sha256"] = sha(R["out_npz"])

# ---- pull the Amihud sleeve arms into a compact file ---------------------------------
AM = {}
for seed in ("42", "2027"):
    p = "/workspace/uplift_2026-09-11/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s%s.npz" % seed
    Z = np.load(p, allow_pickle=True)
    key = "rec" if "rec" in Z.files else "d30_n2_c42_rec"
    rec = np.asarray(Z[key], float)
    AM["AMIHUD_s%s_rec" % seed] = rec
    AM["AMIHUD_s%s_cols" % seed] = np.array([str(c) for c in Z["cols"]])
    AM["AMIHUD_s%s_config" % seed] = np.array(str(Z["config_json"]))
    R.setdefault("amihud_inputs", {})["s" + seed] = {"path": p, "sha256": sha(p), "rec_key": key,
                                                     "rec_shape": list(rec.shape)}
    print("AMIHUD s%s %s %s" % (seed, key, rec.shape), flush=True)
np.savez_compressed(OUT + "/r14_amihud_arms.npz", **AM)
R["out_amihud"] = OUT + "/r14_amihud_arms.npz"
R["out_amihud_sha256"] = sha(R["out_amihud"])

json.dump(R, open(OUT + "/RECEIPT_r14_pod_deadmask.json", "w"), indent=1)
print("POD_DEADMASK_DONE", flush=True)
