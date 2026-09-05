"""diag_g2a.py — DIAGNOSTIC for classifying a G2(a) mismatch (not a gate, not a G5 arm; the main chain keeps the unmasked rebuilt panel).
Two extra runs of the verbatim-logic stage-6 device (patched/pod_stop_arms_v3.py, output paths only) with the SAME rebuilt meta:
  DIAG-A: panel = rebuilt panel with f_fund_* columns masked to the 08-21 funding coverage (symbols that have any finite f_fund_now in
          /workspace/data/wide_panel_4h_v1.npz = the 450 live names), king = the real 08-21 king (ref/slow_pred_hist_oos.npy re-indexed
          by ts onto the rebuilt meta grid). If this reproduces the 08-21 nets bitwise, the whole G2(a) gap is (funding coverage + king refit).
  DIAG-B: panel = rebuilt (unmasked), king = the real 08-21 king  => isolates the funding-coverage effect alone.
Also reports the funding-column residual mismatch after masking (does the within-symbol funding history agree with v1?).
Writes results/diag_g2a.json; prints per-year means and max|Δ| vs ref nets."""
import os, sys, json, time, hashlib, subprocess
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
PY = "/workspace/venv/bin/python"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
out = {"self_sha256": sha(os.path.abspath(__file__)), "note": "diagnostic only; not a gate, not a G5 arm"}
# 1. masked panel
A = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz", allow_pickle=True); B = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
sa = [str(s) for s in A["symbols"]]; assert sa == [str(s) for s in B["symbols"]]
cov = np.isfinite(B["f_fund_now"]).any(0); out["v1_funding_symbols"] = int(cov.sum()); out["rebuilt_funding_symbols"] = int(np.isfinite(A["f_fund_now"]).any(0).sum())
masked = {k: A[k] for k in A.files}
for k in A.files:
    if k.startswith("f_fund"):
        x = np.array(A[k], copy=True); x[:, ~cov] = np.nan; masked[k] = x
MP = f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt_fund450_DIAG.npz"; np.savez_compressed(MP, **masked); out["masked_panel_sha256"] = sha(MP)
# residual funding mismatch after masking (common ts)
tsa = A["ts"].astype(np.int64); tsb = B["ts"].astype(np.int64); common = np.intersect1d(tsa, tsb); ra = np.searchsorted(tsa, common); rb = np.searchsorted(tsb, common); yrs = np.array([yr(t) for t in common])
resid = {}
for k in ("f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
    a = masked[k][ra].astype(np.float64); b = B[k][rb].astype(np.float64); fa = np.isfinite(a); fb = np.isfinite(b); both = fa & fb; neq = both & (a != b); nanmis = fa ^ fb
    resid[k] = {"n_both": int(both.sum()), "n_neq": int(neq.sum()), "n_nan_mismatch": int(nanmis.sum()), "max_abs_diff": float(np.abs(a - b)[neq].max()) if neq.any() else 0.0,
                "by_year": {str(y): {"n_neq": int(neq[yrs == y].sum()), "n_nan_mismatch": int(nanmis[yrs == y].sum()), "max_abs": float(np.abs(a - b)[neq & (yrs == y)[:, None]].max()) if (neq & (yrs == y)[:, None]).any() else 0.0} for y in sorted(set(yrs.tolist()))}}
    print(f"  masked {k}: neq {resid[k]['n_neq']} nan-mismatch {resid[k]['n_nan_mismatch']} max|Δ| {resid[k]['max_abs_diff']:.2e} | by year: " + " ".join(f"{y}:{v['n_neq']}/{v['n_nan_mismatch']}" for y, v in resid[k]["by_year"].items()), flush=True)
out["residual_funding_mismatch_after_mask"] = resid
# 2. 08-21 king re-indexed onto the rebuilt meta grid
K = np.load(f"{ROOT}/ref/slow_pred_hist_oos.npy"); mref = np.load(f"{ROOT}/ref/wide_fea_hist_meta.npz", allow_pickle=True); tref = mref["E_ts"].astype(np.int64)
mreb = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True); treb = mreb["E_ts"].astype(np.int64)
rowr = {int(t): i for i, t in enumerate(tref)}; K2 = np.full((len(treb), 829), np.nan, np.float32); nmap = 0
for i, t in enumerate(treb):
    j = rowr.get(int(t))
    if j is not None: K2[i] = K[j]; nmap += 1
KP = f"{ROOT}/data/king0821_on_rebuilt_meta_DIAG.npy"; np.save(KP, K2); out["king0821_reindexed"] = {"n_mapped": nmap, "n_rebuilt_anchors": int(len(treb)), "identical_grid": bool(np.array_equal(tref, treb)), "sha256": sha(KP)}
print(f"  08-21 king re-indexed: {nmap}/{len(treb)} anchors mapped (grids identical: {np.array_equal(tref, treb)})", flush=True)
# 3. runs
def run(tag, panel, king):
    cmd = ["env", f"TAG={tag}", f"META_IN={ROOT}/data/wide_fea_hist_meta_rebuilt.npz", f"PANEL_IN={panel}", f"KING_IN={king}", PY, f"{ROOT}/patched/pod_stop_arms_v3.py"]
    with open(f"{ROOT}/logs/commands.txt", "a") as f: f.write(f"CMD[06g_diag] (cwd={ROOT}) {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}: {' '.join(cmd)}\n")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True); open(f"{ROOT}/logs/diag_{tag}.log", "w").write(r.stdout + r.stderr)
    with open(f"{ROOT}/logs/commands.txt", "a") as f: f.write(f"RC[06g_diag] {tag} rc={r.returncode}\n")
    assert r.returncode == 0 and "STOP_ARMS_DONE" in r.stdout, tag
def compare(tag):
    rec = {}
    for f in ("nets_%s_-30_2_42.npy", "nets_%s_0_0_0.npy"):
        a = np.load(f"{ROOT}/data/{f % tag}"); b = np.load(f"{ROOT}/ref/{f % 'histv2'}"); ta = a[:, 0].astype(np.int64); tb = b[:, 0].astype(np.int64)
        c = np.intersect1d(ta, tb); va = a[np.searchsorted(ta, c), 1]; vb = b[np.searchsorted(tb, c), 1]; d = va - vb; yy = np.array([yr(t) for t in c])
        rec[f % tag] = {"ts_equal": bool(np.array_equal(ta, tb)), "n": int(len(ta)), "n_ref": int(len(tb)), "n_common": int(len(c)), "bitwise_share": float((va == vb).mean()), "max_abs_diff_bps": float(np.abs(d).max()), "mean_diff_bps": float(d.mean()), "corr": float(np.corrcoef(va, vb)[0, 1]),
                        "by_year": {str(y): {"diag": round(float(va[yy == y].mean()), 4), "ref0821": round(float(vb[yy == y].mean()), 4), "max_abs": float(np.abs(d[yy == y]).max()), "bitwise_share": float((va[yy == y] == vb[yy == y]).mean()), "n": int((yy == y).sum())} for y in sorted(set(yy.tolist()))},
                        "n_only_diag": int(len(ta) - len(c)), "n_only_ref": int(len(tb) - len(c)), "first_diag": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ta[0]))), "first_ref": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tb[0])))}
        print(f"  {f % tag}: ts_equal {rec[f % tag]['ts_equal']} n {len(ta)}/{len(tb)} (first {rec[f % tag]['first_diag']} vs {rec[f % tag]['first_ref']}) bitwise {rec[f % tag]['bitwise_share']:.4f} max|Δ| {rec[f % tag]['max_abs_diff_bps']:.3e} mean {rec[f % tag]['mean_diff_bps']:+.4f} corr {rec[f % tag]['corr']:.5f} | " + " ".join(f"{y}: {v['diag']:+.3f}/{v['ref0821']:+.3f} bw{v['bitwise_share']:.2f} max{v['max_abs']:.0e}" for y, v in rec[f % tag]["by_year"].items()), flush=True)
    return rec
run("diagA", MP, KP); out["DIAG_A_masked_funding_plus_0821_king"] = compare("diagA")
run("diagB", f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz", KP); out["DIAG_B_rebuilt_panel_plus_0821_king"] = compare("diagB")
json.dump(out, open(f"{ROOT}/results/diag_g2a.json", "w"), indent=1); print("wrote results/diag_g2a.json", flush=True)
