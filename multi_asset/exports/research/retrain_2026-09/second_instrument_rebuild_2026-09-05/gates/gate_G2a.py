"""gate_G2a.py — PREREG §2 G2(a): stage-6 nets_histv2_-30_2_42.npy / nets_histv2_0_0_0.npy vs the real 08-21 files.
The pod copies /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_*.npy are 144-byte stubs (prereg: '若为真件而非 144 字节桩'), so the
comparison uses the full-size 08-21 files from the Mac backup of the 08-21 pod (ref/, sha 77375782… and 9a165939…, 12,279 anchors
2021-01-06 16:00 -> 2026-08-15 00:00). PASS iff ts identical and values bitwise. Otherwise: max|Δ|, per-year means of both, corr, and the
same for the two other arms. Also compares the stop_arms summary json. Writes results/G2a.json; exit 0 always."""
import os, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
out = {"self_sha256": sha(os.path.abspath(__file__)), "pod_port_stub_sizes": {f: os.path.getsize(f"/workspace/port_w10/pod_backup_2026-08-21/{f}") for f in ("nets_histv2_-30_2_42.npy", "nets_histv2_0_0_0.npy")}, "arms": {}}
allp = True
for f in ("nets_histv2_-30_2_42.npy", "nets_histv2_0_0_0.npy", "nets_histv2_-25_2_42.npy", "nets_histv2_-25_1_42.npy"):
    a = np.load(f"{ROOT}/data/{f}"); b = np.load(f"{ROOT}/ref/{f}")
    ta = a[:, 0].astype(np.int64); tb = b[:, 0].astype(np.int64)
    rec = {"sha_rebuilt": sha(f"{ROOT}/data/{f}"), "sha_ref": sha(f"{ROOT}/ref/{f}"), "n_rebuilt": int(len(ta)), "n_ref": int(len(tb)), "ts_equal": bool(np.array_equal(ta, tb)),
           "first_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ta[0]))), "first_ref": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tb[0]))),
           "last_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ta[-1]))), "last_ref": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tb[-1])))}
    common = np.intersect1d(ta, tb); ia = {int(t): i for i, t in enumerate(ta)}; ib = {int(t): i for i, t in enumerate(tb)}
    va = np.array([a[ia[int(t)], 1] for t in common]); vb = np.array([b[ib[int(t)], 1] for t in common]); yy = np.array([yr(t) for t in common])
    d = va - vb
    rec.update({"n_common": int(len(common)), "n_only_rebuilt": int(len(ta) - len(common)), "n_only_ref": int(len(tb) - len(common)),
                "bitwise_equal_share": float((va == vb).mean()), "max_abs_diff_bps": float(np.abs(d).max()), "mean_diff_bps": float(d.mean()), "corr": float(np.corrcoef(va, vb)[0, 1]),
                "by_year": {str(y): {"n": int((yy == y).sum()), "rebuilt_mean": round(float(va[yy == y].mean()), 4), "ref_mean": round(float(vb[yy == y].mean()), 4), "max_abs_diff": float(np.abs(d[yy == y]).max()), "corr": float(np.corrcoef(va[yy == y], vb[yy == y])[0, 1]) if (yy == y).sum() > 2 else float("nan")} for y in sorted(set(yy.tolist()))},
                "pass": bool(rec["ts_equal"] and np.array_equal(va, vb))})
    if f in ("nets_histv2_-30_2_42.npy", "nets_histv2_0_0_0.npy"): allp &= rec["pass"]
    out["arms"][f] = rec
    print(f"  {f}: ts_equal {rec['ts_equal']} (n {rec['n_rebuilt']} vs {rec['n_ref']}; common {rec['n_common']}) bitwise_share {rec['bitwise_equal_share']:.4f} max|Δ| {rec['max_abs_diff_bps']:.3e} bps mean Δ {rec['mean_diff_bps']:+.4f} corr {rec['corr']:.5f} -> {'PASS' if rec['pass'] else 'FAIL'}", flush=True)
    print("     by year (rebuilt / ref / max|Δ| / corr): " + " | ".join(f"{y}: {v['rebuilt_mean']:+.3f}/{v['ref_mean']:+.3f}/{v['max_abs_diff']:.1e}/{v['corr']:.3f}" for y, v in rec["by_year"].items()), flush=True)
try:
    ja = json.load(open(f"{ROOT}/data/stop_arms_pod_v3_histv2.json"))["hist_oos"]; jb = json.load(open(f"{ROOT}/ref/stop_arms_pod_v3_histv2.json"))["hist_oos"]
    out["summary_json"] = {arm: {"rebuilt": {k: ja[arm][k] for k in ("net_all", "net_2024on", "sharpe_2024on", "maxDD", "turnover", "fires", "by_year")}, "ref": {k: jb[arm][k] for k in ("net_all", "net_2024on", "sharpe_2024on", "maxDD", "turnover", "fires", "by_year")}} for arm in ja}
    for arm in ja: print(f"  json {arm}: rebuilt net_all {ja[arm]['net_all']} 2024on {ja[arm]['net_2024on']} S {ja[arm]['sharpe_2024on']} maxDD {ja[arm]['maxDD']} fires {ja[arm]['fires']} | ref {jb[arm]['net_all']} {jb[arm]['net_2024on']} S {jb[arm]['sharpe_2024on']} maxDD {jb[arm]['maxDD']} fires {jb[arm]['fires']}", flush=True)
except Exception as e:
    out["summary_json"] = {"error": repr(e)}
out["G2a_PASS"] = bool(allp)
print(f"G2a {'PASS' if allp else 'FAIL'} (d30 + S0 bitwise vs real 08-21 files; pod port stubs {out['pod_port_stub_sizes']})", flush=True)
json.dump(out, open(f"{ROOT}/results/G2a.json", "w"), indent=1); print("wrote results/G2a.json")
