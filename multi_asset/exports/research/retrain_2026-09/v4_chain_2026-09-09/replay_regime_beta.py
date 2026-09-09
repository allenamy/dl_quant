"""DIAGNOSTIC (hypothesis stated before numbers): the in-service book's SHORT half is structurally short-beta to the alt index (live 08-26→09-09: corr −0.93,
β −0.87), and the book's losses concentrate in regimes where positive-funding share is saturated (>0.85) and σ_fund is low (short half = low-positive-funding
alts). Test on the v4 replay (A0 dyn s42, RAW accounting, 2024→2026-08-31): per-anchor short/long-half returns, altEW, rn8 regime stats; rolling causal β
(trailing 180 anchors) of book g on altEW; β-part vs residual by year and by regime bucket; costless β-neutral counterfactual (information only, NOT a candidate)."""
import numpy as np, json, time, calendar
HC = "/workspace/review_scratch/health_check"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]; C = {c: i for i, c in enumerate(COLS)}
A = np.load(f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz", allow_pickle=True); R = A["d30_n2_c42_rec"]; Wb = A["d30_n2_c42_W"]; ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
MT = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True); E = MT["E_ts"].astype(np.int64); Y = MT["y4"]; MEM = MT["members"]; ei = {int(t): i for i, t in enumerate(E)}
PW = np.load(f"{HC}/dev_alt/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz", allow_pickle=True); pts = PW["ts"].astype(np.int64); pi = {int(t): j for j, t in enumerate(pts)}; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"] if "f_fund_iv" in PW.files else np.full_like(FN, 8.0)
UZ = np.load(f"{HC}/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True); um = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
rows = []
for p, t in enumerate(ts):
    i = ei.get(int(t)); j = pi.get(int(t))
    if i is None or j is None: continue
    w = Wb[p].astype(np.float64); y = np.nan_to_num(Y[i].astype(np.float64), nan=0.0); m = MEM[i]
    if int(t) in um: m = m[UM[um[int(t)]][m]]
    if len(m) < 50: continue
    alt = float(np.nanmean(Y[i, m])) * 1e4; rn = FN[j, m] * (8.0 / np.where(np.isfinite(IV[j, m]) & (IV[j, m] > 0), IV[j, m], 8.0)) * 1e4; ok = np.isfinite(rn)
    pos_share = float((rn[ok] > 0).mean()) if ok.sum() else np.nan; deep = float((rn[ok] <= -10).mean()) if ok.sum() else np.nan; sig = float(np.nanstd(rn[ok])) if ok.sum() else np.nan
    sg = np.abs(w[w < 0]).sum(); lg = w[w > 0].sum(); sret = float((w[w < 0] * y[w < 0]).sum() / sg * 1e4) if sg > 0 else np.nan; lret = float((w[w > 0] * y[w > 0]).sum() / lg * 1e4) if lg > 0 else np.nan
    rows.append((int(t), g[p], alt, sret, lret, pos_share, deep, sig, sg / (sg + lg) if sg + lg > 0 else np.nan))
X = np.array(rows); t = X[:, 0].astype(np.int64); gg = X[:, 1]; alt = X[:, 2]; sret = X[:, 3]; lret = X[:, 4]; ps = X[:, 5]; dp = X[:, 6]; sg_ = X[:, 7]
yrs = np.array([time.gmtime(int(x)).tm_year for x in t])
# rolling causal beta of book g on altEW (trailing 180 anchors, min 60)
beta = np.full(len(t), np.nan)
for k in range(60, len(t)):
    a_ = alt[max(0, k - 180):k]; b_ = gg[max(0, k - 180):k]; ok = np.isfinite(a_) & np.isfinite(b_)
    if ok.sum() >= 60: beta[k] = np.cov(a_[ok], b_[ok])[0, 1] / (np.var(a_[ok]) + 1e-12)
bpart = beta * alt; resid = gg - bpart; hedged = gg - bpart
def T(*x): return calendar.timegm(x + (0,) * (6 - len(x)))
def sh(v): v = v[np.isfinite(v)]; return float(v.mean() / (v.std(ddof=1) + 1e-12) * np.sqrt(2190)) if len(v) > 2 else np.nan
out = {}
print("== v4 replay A0 dyn s42 (RAW accounting, CRYPTO m1): short/long halves vs alt index, by year ==")
print("%-6s %5s %8s %8s %8s %8s %7s %7s %7s %8s %8s %8s %8s" % ("year", "n", "g", "altEW", "shortR", "longR", "corrS", "betaS", "beta_g", "b_part", "resid", "g_hedg", "Sh g/h"))
for y in (2024, 2025, 2026):
    m = (yrs == y) & np.isfinite(beta); ok = m & np.isfinite(sret) & np.isfinite(alt)
    cs = np.corrcoef(alt[ok], sret[ok])[0, 1]; bs = np.polyfit(alt[ok], sret[ok], 1)[0]
    out[str(y)] = dict(n=int(m.sum()), g=float(gg[m].mean()), alt=float(alt[m].mean()), shortR=float(np.nanmean(sret[m])), longR=float(np.nanmean(lret[m])), corr_short_alt=float(cs), beta_short=float(bs), beta_book=float(np.nanmean(beta[m])), beta_part=float(np.nanmean(bpart[m])), resid=float(np.nanmean(resid[m])), g_hedged=float(np.nanmean(hedged[m])), sharpe_g=sh(gg[m]), sharpe_hedged=sh(hedged[m]))
    o = out[str(y)]; print("%-6d %5d %+8.3f %+8.2f %+8.2f %+8.2f %+7.2f %+7.2f %+7.3f %+8.3f %+8.3f %+8.3f %5.2f/%5.2f" % (y, o["n"], o["g"], o["alt"], o["shortR"], o["longR"], o["corr_short_alt"], o["beta_short"], o["beta_book"], o["beta_part"], o["resid"], o["g_hedged"], o["sharpe_g"], o["sharpe_hedged"]))
WIN = {"frozen 25-03-01→26-08-10": (T(2025, 3, 1), T(2026, 8, 10, 20) + 1), "aug 26-08-11→08-31": (T(2026, 8, 11), T(2026, 8, 31, 20) + 1), "2024→26-08-31": (T(2024, 1, 1), T(2026, 8, 31, 20) + 1)}
for w, (lo, hi) in WIN.items():
    m = (t >= lo) & (t < hi) & np.isfinite(beta); ok = m & np.isfinite(sret)
    out[w] = dict(n=int(m.sum()), g=float(gg[m].mean()), alt=float(alt[m].mean()), shortR=float(np.nanmean(sret[m])), longR=float(np.nanmean(lret[m])), corr_short_alt=float(np.corrcoef(alt[ok], sret[ok])[0, 1]), beta_book=float(np.nanmean(beta[m])), beta_part=float(np.nanmean(bpart[m])), resid=float(np.nanmean(resid[m])), g_hedged=float(np.nanmean(hedged[m])), sharpe_g=sh(gg[m]), sharpe_hedged=sh(hedged[m]), maxdd_g=float(np.max(np.maximum.accumulate(np.concatenate([[0], np.cumsum(gg[m])])) - np.concatenate([[0], np.cumsum(gg[m])]))), maxdd_h=float(np.max(np.maximum.accumulate(np.concatenate([[0], np.cumsum(hedged[m])])) - np.concatenate([[0], np.cumsum(hedged[m])]))))
    o = out[w]; print("%-24s n %5d g %+7.3f alt %+6.2f shortR %+6.2f longR %+6.2f corrS %+5.2f β_book %+6.3f β_part %+6.3f resid %+6.3f | hedged g %+6.3f Sharpe %5.2f→%5.2f maxDD %6.0f→%6.0f" % (w, o["n"], o["g"], o["alt"], o["shortR"], o["longR"], o["corr_short_alt"], o["beta_book"], o["beta_part"], o["resid"], o["g_hedged"], o["sharpe_g"], o["sharpe_hedged"], o["maxdd_g"], o["maxdd_h"]))
print("\n== regime buckets 2024→2026 (pos_share saturation × σ_fund tercile): mean g, altEW, shortR, longR, β_part, resid ==")
m24 = (yrs >= 2024) & np.isfinite(beta) & np.isfinite(ps) & np.isfinite(dp)
q = np.nanpercentile(X[m24, 7], [33, 67]); out["regime"] = {}
for lab, cond in (("saturated pos>=0.85 & deep<=0.03", (ps >= 0.85) & (dp <= 0.03)), ("mid", ~((ps >= 0.85) & (dp <= 0.03)) & ~(ps < 0.7)), ("unsaturated pos<0.7", ps < 0.7)):
    for sl, sc in (("σ_fund low", X[:, 7] <= q[0]), ("σ_fund mid", (X[:, 7] > q[0]) & (X[:, 7] <= q[1])), ("σ_fund high", X[:, 7] > q[1])):
        m = m24 & cond & sc
        if m.sum() < 30: continue
        out["regime"][f"{lab}|{sl}"] = dict(n=int(m.sum()), g=float(gg[m].mean()), alt=float(alt[m].mean()), shortR=float(np.nanmean(sret[m])), longR=float(np.nanmean(lret[m])), beta_part=float(np.nanmean(bpart[m])), resid=float(np.nanmean(resid[m])), share_neg_anchors=float((gg[m] < 0).mean()))
        o = out["regime"][f"{lab}|{sl}"]; print("  %-34s %-12s n %5d g %+7.3f alt %+6.2f shortR %+6.2f longR %+6.2f β_part %+6.3f resid %+6.3f" % (lab, sl, o["n"], o["g"], o["alt"], o["shortR"], o["longR"], o["beta_part"], o["resid"]))
print("\n== live-window analogue: replay anchors with pos_share>=0.85 & σ_fund<=%.1f (like 09-03→09-09): n=%d, g %+.3f, altEW %+.2f, shortR %+.2f, longR %+.2f" % (q[0], (m24 & (ps >= 0.85) & (X[:, 7] <= q[0])).sum(), gg[m24 & (ps >= 0.85) & (X[:, 7] <= q[0])].mean(), alt[m24 & (ps >= 0.85) & (X[:, 7] <= q[0])].mean(), np.nanmean(sret[m24 & (ps >= 0.85) & (X[:, 7] <= q[0])]), np.nanmean(lret[m24 & (ps >= 0.85) & (X[:, 7] <= q[0])])))
out["sigma_terciles_bp"] = q.tolist(); json.dump(out, open("/workspace/review_scratch/v4_gates/replay_regime_beta.json", "w"), indent=1); print("REPLAY_REGIME_BETA_DONE")
