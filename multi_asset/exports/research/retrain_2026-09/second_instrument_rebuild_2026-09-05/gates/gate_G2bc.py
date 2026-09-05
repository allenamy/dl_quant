"""gate_G2bc.py — PREREG §2 G2(b) and G2(c).
(b) step-8 three-leg arm (LEGS=111 PHI=0 WRULE=msharpe LOOK=900 CAL=log SLOW_NPY=rebuilt hist king; artifact
    dev/probe_artifacts/w10_ablation_series_F1_hist_log.npz, arm d30_n2_c42) column net/gross_total vs the repo reference
    ref/nets_histv2_d30_pergross_ts_0821.npy (9,941 rows, 2022-01-31 08:00 -> 2026-08-15 00:00; = 08-21 d30 net per gross):
    PASS iff the ts sets are identical AND max|Δ| <= 1e-6 bps. Otherwise both clauses are reported separately, plus per-year means,
    corr, and an attribution: (1) stage-6 rebuilt nets (pod_stop_arms_v3 book, same inputs) vs step-8 net => device-form effect
    (w10 DEMEAN-FIX L205 + W6 forced exit L219-220 vs pod_stop_arms_v3 L62); (2) real 08-21 nets vs stage-6 rebuilt nets (= G2(a));
    (3) 08-21 per-gross reference vs step-8 per-gross.
(c) parity gate inside the device (L325-337, maxabs_diff_vs_pod_backup against the stage-6 nets files linked into dev/pod_backup_2026-08-21/):
    must be <= 1e-6 under CAL=log (PASS) and > 1e-6 under CAL=simple (FAIL expected). Both summaries are read and reported.
Writes results/G2bc.json; exit 0 always."""
import os, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def load_series(tag, d="dev"):
    p = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz"; z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]
    R = z["d30_n2_c42_rec"]; cfg = json.loads(str(z["config_json"]))
    return {c: R[:, i] for i, c in enumerate(cols)}, cfg, sha(p)
def align(ta, va, tb, vb):
    common = np.intersect1d(ta, tb); ia = {int(t): i for i, t in enumerate(ta)}; ib = {int(t): i for i, t in enumerate(tb)}
    return common, np.array([va[ia[int(t)]] for t in common]), np.array([vb[ib[int(t)]] for t in common])
def yearly(common, x):
    yy = np.array([yr(t) for t in common]); return {str(y): round(float(x[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))}
out = {"self_sha256": sha(os.path.abspath(__file__))}
S, cfg, s_sha = load_series("F1_hist_log"); out["step8_config"] = cfg; out["step8_artifact_sha256"] = s_sha
assert cfg["LEGS"] == "111" and cfg["PHI"] == 0 and cfg["WRULE"] == "msharpe" and cfg["LOOK"] == 900 and cfg["CAL"] == "log" and cfg["REF_SKIP"] == 0, cfg
ts8 = S["ts"].astype(np.int64); net8 = S["net"]; g8 = S["gross_total"]; pg8 = net8 / g8
ref = np.load(f"{ROOT}/ref/nets_histv2_d30_pergross_ts_0821.npy"); tr = ref[:, 0].astype(np.int64); vr = ref[:, 1]
common, a, b = align(ts8, pg8, tr, vr); d = a - b
b_rec = {"ref_sha256": sha(f"{ROOT}/ref/nets_histv2_d30_pergross_ts_0821.npy"), "n_step8": int(len(ts8)), "step8_first": iso(ts8[0]), "step8_last": iso(ts8[-1]), "n_ref": int(len(tr)), "ref_first": iso(tr[0]), "ref_last": iso(tr[-1]),
         "ts_set_identical": bool(np.array_equal(np.unique(ts8), np.unique(tr))), "ref_ts_subset_of_step8": bool(np.isin(tr, ts8).all()), "n_common": int(len(common)),
         "max_abs_diff_bps_per_gross": float(np.abs(d).max()), "mean_diff": float(d.mean()), "corr": float(np.corrcoef(a, b)[0, 1]), "bitwise_share": float((a == b).mean()),
         "by_year_step8": yearly(common, a), "by_year_ref": yearly(common, b), "by_year_diff": yearly(common, d)}
b_rec["pass"] = bool(b_rec["ts_set_identical"] and b_rec["max_abs_diff_bps_per_gross"] <= 1e-6)
b_rec["value_clause_on_common_ts"] = bool(b_rec["max_abs_diff_bps_per_gross"] <= 1e-6)
print(f"G2(b) step8 F1_hist_log net/gross vs 08-21 per-gross ref: ts_set_identical {b_rec['ts_set_identical']} (step8 n {b_rec['n_step8']} {b_rec['step8_first']}..{b_rec['step8_last']}; ref n {b_rec['n_ref']}; ref⊂step8 {b_rec['ref_ts_subset_of_step8']}); "
      f"common {b_rec['n_common']} max|Δ| {b_rec['max_abs_diff_bps_per_gross']:.3e} corr {b_rec['corr']:.4f} bitwise {b_rec['bitwise_share']:.4f} -> {'PASS' if b_rec['pass'] else 'FAIL'}", flush=True)
print("   by year step8/ref/Δ: " + " | ".join(f"{y}: {b_rec['by_year_step8'][y]:+.3f}/{b_rec['by_year_ref'][y]:+.3f}/{b_rec['by_year_diff'][y]:+.3f}" for y in b_rec["by_year_step8"]), flush=True)
# attribution (1): stage-6 rebuilt nets (same inputs, pod_stop_arms_v3 book) vs step-8 net (w10 book form)
n6 = np.load(f"{ROOT}/data/nets_histv2_-30_2_42.npy"); t6 = n6[:, 0].astype(np.int64); v6 = n6[:, 1]
c1, a1, b1 = align(ts8, net8, t6, v6); d1 = a1 - b1
attr1 = {"n_common": int(len(c1)), "n_step8": int(len(ts8)), "n_stage6": int(len(t6)), "max_abs_diff_bps": float(np.abs(d1).max()), "mean_diff_bps": float(d1.mean()), "corr": float(np.corrcoef(a1, b1)[0, 1]), "bitwise_share": float((a1 == b1).mean()),
         "by_year_step8_net": yearly(c1, a1), "by_year_stage6_net": yearly(c1, b1), "by_year_diff": yearly(c1, d1),
         "note": "same meta/panel/king; differences come only from the device form: w10_universe_recheck.py L205 (demean inside sel only), L219-220 (forced exit of non-sel names) vs pod_stop_arms_v3.py L62"}
print(f"ATTR(1) device form: step8 net vs stage-6 nets (same inputs): common {attr1['n_common']} max|Δ| {attr1['max_abs_diff_bps']:.3e} bps mean {attr1['mean_diff_bps']:+.4f} corr {attr1['corr']:.4f}; by year Δ: " + " | ".join(f"{y}: {v:+.3f}" for y, v in attr1["by_year_diff"].items()), flush=True)
# attribution (2): real 08-21 nets vs stage-6 rebuilt nets (net, bps)
r6 = np.load(f"{ROOT}/ref/nets_histv2_-30_2_42.npy"); tr6 = r6[:, 0].astype(np.int64); vr6 = r6[:, 1]
c2, a2, b2 = align(t6, v6, tr6, vr6); d2 = a2 - b2
attr2 = {"n_common": int(len(c2)), "max_abs_diff_bps": float(np.abs(d2).max()), "mean_diff_bps": float(d2.mean()), "corr": float(np.corrcoef(a2, b2)[0, 1]), "by_year_stage6": yearly(c2, a2), "by_year_0821": yearly(c2, b2), "by_year_diff": yearly(c2, d2)}
print(f"ATTR(2) inputs (G2a): stage-6 rebuilt nets vs real 08-21 nets: common {attr2['n_common']} max|Δ| {attr2['max_abs_diff_bps']:.3e} mean {attr2['mean_diff_bps']:+.4f} corr {attr2['corr']:.4f}; by year Δ: " + " | ".join(f"{y}: {v:+.3f}" for y, v in attr2["by_year_diff"].items()), flush=True)
# attribution (3): 08-21 per-gross ref vs step-8 gross: what gross did 08-21 use? (ref = net/gross; 08-21 net known from ref nets) -> implied gross
c3, n21, pg21 = align(tr6, vr6, tr, vr); implied_g = np.where(np.abs(pg21) > 1e-12, n21 / pg21, np.nan)
c4, g8c, gi = align(ts8, g8, c3, implied_g)
attr3 = {"n_common": int(len(c4)), "mean_gross_step8": float(np.nanmean(g8c)), "mean_gross_implied_0821": float(np.nanmean(gi)), "by_year_gross_step8": yearly(c4, np.nan_to_num(g8c)), "by_year_gross_implied_0821": yearly(c4, np.nan_to_num(gi))}
print(f"ATTR(3) gross: step8 gross_total mean {attr3['mean_gross_step8']:.4f} vs 08-21 implied (net/pergross) {attr3['mean_gross_implied_0821']:.4f}", flush=True)
out["G2b"] = b_rec; out["attribution"] = {"1_device_form": attr1, "2_inputs_vs_0821": attr2, "3_gross": attr3}
# (c)
c_rec = {}
for tag, cal in (("F1_hist_log", "log"), ("F1_hist_simple", "simple")):
    p = f"{ROOT}/dev/probe_artifacts/w10_ablation_summary_{tag}.json"
    if not os.path.exists(p): c_rec[cal] = {"missing": p}; continue
    js = json.load(open(p)); c_rec[cal] = {arm: {"maxabs_diff_vs_pod_backup": js[arm]["maxabs_diff_vs_pod_backup"], "n": js[arm]["n"], "net_all": js[arm]["net_all"], "by_year": js[arm]["by_year"]} for arm in ("S0", "d30_n2_c42")}
    c_rec[cal]["parity_pass"] = bool(all(np.isfinite(js[arm]["maxabs_diff_vs_pod_backup"]) and js[arm]["maxabs_diff_vs_pod_backup"] <= 1e-6 for arm in ("S0", "d30_n2_c42")))
    print(f"G2(c) CAL={cal}: maxabs_diff_vs_pod_backup S0 {js['S0']['maxabs_diff_vs_pod_backup']:.3e} d30 {js['d30_n2_c42']['maxabs_diff_vs_pod_backup']:.3e} (n {js['d30_n2_c42']['n']}) -> parity {'PASS' if c_rec[cal]['parity_pass'] else 'FAIL'}", flush=True)
c_pass = bool(c_rec.get("log", {}).get("parity_pass") is True and c_rec.get("simple", {}).get("parity_pass") is False)
out["G2c"] = {"per_caliber": c_rec, "pass": c_pass, "rule": "log parity PASS (<=1e-6) AND simple parity FAIL"}
print(f"G2(c) => {'PASS' if c_pass else 'FAIL'} (log parity {c_rec.get('log', {}).get('parity_pass')}, simple parity {c_rec.get('simple', {}).get('parity_pass')})", flush=True)
json.dump(out, open(f"{ROOT}/results/G2bc.json", "w"), indent=1); print("wrote results/G2bc.json")
