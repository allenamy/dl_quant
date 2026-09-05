"""compare_meta.py — INFORMATIONAL (not a prereg gate): rebuilt wide_fea_hist_meta vs the real 08-21 meta (ref/wide_fea_hist_meta.npz,
sha 0ca2e235…, Mac backup of the 08-21 pod). Checks E_ts, names, members (per anchor), y4 and qvk bitwise on common anchors."""
import os, sys, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
PA = f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz"; PB = f"{ROOT}/ref/wide_fea_hist_meta.npz"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
A = np.load(PA, allow_pickle=True); B = np.load(PB, allow_pickle=True)
out = {"self_sha256": sha(os.path.abspath(__file__)), "rebuilt_sha256": sha(PA), "ref_sha256": sha(PB)}
ta = A["E_ts"].astype(np.int64); tb = B["E_ts"].astype(np.int64)
out["E_ts"] = {"n_rebuilt": int(len(ta)), "n_ref": int(len(tb)), "equal": bool(np.array_equal(ta, tb)),
               "first_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ta[0]))), "first_ref": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tb[0]))),
               "last_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ta[-1]))), "last_ref": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tb[-1])))}
out["names_equal"] = [str(x) for x in A["names"]] == [str(x) for x in B["names"]]
common = np.intersect1d(ta, tb); ia = {int(t): i for i, t in enumerate(ta)}; ib = {int(t): i for i, t in enumerate(tb)}
ra = np.array([ia[int(t)] for t in common]); rb = np.array([ib[int(t)] for t in common]); yrs = np.array([yr(t) for t in common])
ma = A["members"]; mb = B["members"]
mem_eq = np.array([np.array_equal(np.asarray(ma[i]), np.asarray(mb[j])) for i, j in zip(ra, rb)])
out["members"] = {"n_common_anchors": int(len(common)), "n_equal": int(mem_eq.sum()), "by_year_unequal": {str(y): int((~mem_eq)[yrs == y].sum()) for y in sorted(set(yrs.tolist()))}}
if (~mem_eq).any():
    i0 = int(np.argmax(~mem_eq)); sa_ = set(np.asarray(ma[ra[i0]]).tolist()); sb_ = set(np.asarray(mb[rb[i0]]).tolist())
    out["members"]["first_unequal"] = {"anchor": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(common[i0]))), "n_rebuilt": len(sa_), "n_ref": len(sb_), "only_rebuilt": sorted(sa_ - sb_)[:10], "only_ref": sorted(sb_ - sa_)[:10]}
for k in ("y4", "qvk"):
    a = A[k][ra].astype(np.float64); b = B[k][rb].astype(np.float64); fa = np.isfinite(a); fb = np.isfinite(b); both = fa & fb; neq = both & (a != b); nanmis = fa ^ fb
    out[k] = {"n_both": int(both.sum()), "n_neq": int(neq.sum()), "n_nan_mismatch": int(nanmis.sum()), "max_abs_diff": float(np.abs(a - b)[neq].max()) if neq.any() else 0.0,
              "by_year": {str(y): {"n_neq": int(neq[yrs == y].sum()), "n_nan_mismatch": int(nanmis[yrs == y].sum())} for y in sorted(set(yrs.tolist()))}}
out["bitwise_all"] = bool(out["E_ts"]["equal"] and out["names_equal"] and mem_eq.all() and out["y4"]["n_neq"] == 0 and out["y4"]["n_nan_mismatch"] == 0 and out["qvk"]["n_neq"] == 0 and out["qvk"]["n_nan_mismatch"] == 0)
print(f"META vs 08-21: E_ts equal {out['E_ts']['equal']} ({out['E_ts']['n_rebuilt']} vs {out['E_ts']['n_ref']}, {out['E_ts']['first_rebuilt']}..{out['E_ts']['last_rebuilt']} vs {out['E_ts']['first_ref']}..{out['E_ts']['last_ref']}); names equal {out['names_equal']}; "
      f"members equal {out['members']['n_equal']}/{out['members']['n_common_anchors']}; y4 neq {out['y4']['n_neq']} nan-mismatch {out['y4']['n_nan_mismatch']} max|Δ| {out['y4']['max_abs_diff']:.2e}; "
      f"qvk neq {out['qvk']['n_neq']} nan-mismatch {out['qvk']['n_nan_mismatch']}; BITWISE_ALL {out['bitwise_all']}", flush=True)
if not mem_eq.all(): print("  members unequal by year:", out["members"]["by_year_unequal"], "first:", out["members"].get("first_unequal"), flush=True)
json.dump(out, open(f"{ROOT}/results/compare_meta.json", "w"), indent=1); print("wrote results/compare_meta.json")
