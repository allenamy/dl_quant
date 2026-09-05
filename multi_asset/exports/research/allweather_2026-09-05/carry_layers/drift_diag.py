"""drift_diag.py — carry_layers diagnostic for the D-layer drift term (not part of the frozen judge; mechanism reading only).
(a) dodged events of D10_prev s42 (2023→cut): mean price move over the used window [S−10m, S+25m) vs placebo windows of the same length shifted −3h…+3h (non-settlement times for 4h/8h names) and the 4h anchor return of those names;
(b) ALL settlement events 2023→cut (no position conditioning) bucketed by the settled rate: mean/median window move — the sign pattern of the settlement-window move by funding sign.
Note: dodge_events col 0 = the ANCHOR ts E_i (device stores the anchor, not S); S is recovered as E_i + (q+1)h by matching (r_S, drift) to the settlement table slot q. Read-only on inputs; writes results/drift_diag.json."""
import numpy as np, json, time, zipfile, io, calendar
ROOT = "/workspace/review_scratch/allweather_trackC/carry_layers"; F5 = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; LO = T("2023-01-01")
z = zipfile.ZipFile(F5); ts5 = np.load(io.BytesIO(z.read("ts.npy"))).astype(np.int64); row5 = {int(t): r for r, t in enumerate(ts5)}
ret5 = np.load(F5)["data"][:, :, 0].astype(np.float32)
def win(S, k, shift_s=0):
    r = row5.get(int(S + shift_s))
    if r is None or r - 2 < 0 or r + 5 > len(ts5): return np.nan
    w = ret5[r - 2:r + 5, k]; ok = np.isfinite(w)
    return float(np.prod(1 + w[ok]) - 1) if ok.any() else np.nan
Z = np.load(f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_D10_prev_prod_s42.npz", allow_pickle=True); E = Z["d30_n2_c42_dodge_events"]
m = (E[:, 0] >= LO) & (E[:, 0] < CUT); E = E[m]; out = {"arm": "D10_prev_prod_s42", "window": "2023->cut", "n_events": int(len(E))}
A_ = E[:, 0].astype(np.int64); K = E[:, 1].astype(int); W = E[:, 2]; R = E[:, 3]; D = E[:, 5]; sg = np.sign(W)
ST0 = np.load(f"{ROOT}/data/sett_tables.npz"); R0 = ST0["R"]; D0 = ST0["DR"]; E0 = ST0["E_ts"].astype(np.int64); arow = {int(t): i for i, t in enumerate(E0)}
S = np.full(len(E), -1, np.int64); amb = 0
for n in range(len(E)):
    i = arow[int(A_[n])]; q = np.where(np.isfinite(R0[i, K[n]]) & (np.abs(R0[i, K[n]].astype(np.float64) - R[n]) < 1e-12) & (np.abs(D0[i, K[n]].astype(np.float64) - D[n]) < 1e-9))[0]
    if len(q) != 1: amb += 1
    if len(q) >= 1: S[n] = A_[n] + (int(q[0]) + 1) * 3600
out["settlement_time_recovered"] = int((S > 0).sum()); out["ambiguous_or_missing_slot"] = amb
okS = S > 0
for nm, sh in (("used [S-10,S+25)", 0), ("placebo -3h", -10800), ("placebo -2h", -7200), ("placebo -1h", -3600), ("placebo +1h", 3600), ("placebo +2h", 7200), ("placebo +3h", 10800)):
    d = np.array([win(S[i], K[i], sh) if okS[i] else np.nan for i in range(len(E))]); ok = np.isfinite(d)
    out[nm] = {"n_finite": int(ok.sum()), "mean_move_bps_rpos": float(np.nanmean(d[(R > 0) & ok]) * 1e4), "mean_move_bps_rneg": float(np.nanmean(d[(R < 0) & ok]) * 1e4), "mean_forgone_pnl_bps": float(np.nanmean((sg * d)[ok]) * 1e4), "median_forgone_pnl_bps": float(np.nanmedian((sg * d)[ok]) * 1e4)}
d0 = np.array([win(S[i], K[i], 0) if okS[i] else np.nan for i in range(len(E))]); out["recomputed_window_equals_saved_drift_max_abs"] = float(np.nanmax(np.abs(d0 - D)))
MT = np.load(f"{ROOT}/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True); mE = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; mrow = {int(t): i for i, t in enumerate(mE)}
Y = np.array([y4[mrow[int(A_[i])], K[i]] if int(A_[i]) in mrow else np.nan for i in range(len(E))])
out["anchor_4h_return_bps_of_dodged_names"] = {"rpos": float(np.nanmean(Y[R > 0]) * 1e4), "rneg": float(np.nanmean(Y[R < 0]) * 1e4), "forgone_pnl_4h_if_flat_whole_anchor": float(np.nanmean(sg * Y) * 1e4)}
Rt = ST0["R"]; DRt = ST0["DR"]; Et = E0
mm = (Et >= LO) & (Et < CUT); Rw = Rt[mm].ravel(); Dw = DRt[mm].ravel(); ok = np.isfinite(Rw) & np.isfinite(Dw); Rw = Rw[ok] * 1e4; Dw = Dw[ok] * 1e4
edges = [-1e9, -15, -10, -6, -2, 0, 2, 6, 10, 15, 1e9]; tab = []
for a, b in zip(edges[:-1], edges[1:]):
    s = (Rw >= a) & (Rw < b); tab.append({"rate_bps_range": [a if a > -1e8 else None, b if b < 1e8 else None], "n": int(s.sum()), "mean_move_bps": float(Dw[s].mean()) if s.any() else None, "median_move_bps": float(np.median(Dw[s])) if s.any() else None})
out["all_events_by_rate_bucket"] = tab
json.dump(out, open(f"{ROOT}/results/drift_diag.json", "w"), indent=1); print(json.dumps(out, indent=1)); print("DIAG_DONE")
