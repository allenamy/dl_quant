"""diff_quant.py — quantify two replay-vs-live gaps the rec does not carry (for the REPORT differences section). Read-only; prints JSON to results/diff_quant.json.
(1) Executor re-lever turnover: the executor sizes gross = L×NAV every anchor, so the live weight vector is W_t/g_t (g_t = Σ|W_t| of the blended unit book). Its turnover
    T_live = Σ|W_t/g_t − W_{t−1}/g_{t−1}| exceeds the rec's T_rec = Σ|W_t − W_{t−1}|/g_t whenever g drifts; extra cost = (T_live − T_rec) × cost per unit turnover
    (fee-only 2.035 bps live steady; device default 3.44 on the live tier mix). W = d30_n2_c42_W (blended book sm before the executor re-demean; smr is not saved).
(2) Effective fund rank base in the replay: names with finite f_fund_ema_v1 on the panel row (MEMBERS_TOPN=829 ⇒ xz ranks over all finite scores), yearly mean, vs live base_n 528."""
import numpy as np, json, time
ROOT = "/workspace/review_scratch/health_check"; out = {}
for tag, d in (("UPIT_prod_s42_ccal", "dev_alt"), ("UPIT_prod_s2027_ccal", "dev_alt"), ("eq_patched_pinned_log_s42", "dev")):
    Z = np.load(f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz", allow_pickle=True); R = Z["d30_n2_c42_rec"]; W = Z["d30_n2_c42_W"].astype(np.float64)
    ts = R[:, 0].astype(np.int64); g = np.abs(W).sum(1); assert np.abs(g - R[:, 5]).max() < 1e-3, "W gross != rec gross_total"
    Wn = W / np.where(g > 1e-9, g, 1.0)[:, None]
    T_live = np.abs(np.diff(Wn, axis=0)).sum(1); T_rec = R[1:, 17] / g[1:]; yrs = np.array([time.gmtime(int(t)).tm_year for t in ts[1:]])
    rel = np.abs(np.diff(g)) / g[1:]
    o = {}
    for y in (2024, 2025, 2026):
        m = yrs == y; dT = float((T_live[m] - T_rec[m]).mean())
        o[str(y)] = {"T_rec_mean": round(float(T_rec[m].mean()), 5), "T_live_mean": round(float(T_live[m].mean()), 5), "ratio": round(float(T_live[m].mean() / T_rec[m].mean()), 4), "mean_abs_rel_dgross": round(float(rel[m].mean()), 5),
                     "extra_cost_bps_anchor_per_gross_feeonly_2.035": round(dT * 2.035, 4), "extra_cost_bps_anchor_per_gross_default_3.44": round(dT * 3.44, 4)}
    out[tag] = o; print(tag, json.dumps(o), flush=True)
P = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pts = P["ts"].astype(np.int64); FE = P["f_fund_ema_v1"]; FN = P["f_fund_now"]
py = np.array([time.gmtime(int(t)).tm_year for t in pts]); base = {}
for y in (2024, 2025, 2026):
    m = py == y; base[str(y)] = {"finite_fund_ema_mean": round(float(np.isfinite(FE[m]).sum(1).mean()), 1), "finite_fund_now_mean": round(float(np.isfinite(FN[m]).sum(1).mean()), 1), "live_base_n_20260904": 528}
out["effective_fund_rank_base"] = base; print("rank base", json.dumps(base), flush=True)
json.dump(out, open(f"{ROOT}/results/diff_quant.json", "w"), indent=1); print("DIFF_QUANT_DONE")
