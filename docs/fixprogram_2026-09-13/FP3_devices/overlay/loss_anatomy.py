#!/usr/bin/env python3
"""FP3-R loss anatomy on the baseline replay (A0 s42, W_ALPHA): for the worst anchors and worst UTC days, split the pre-cost loss into long leg vs short leg,
top-3 name share, contemporaneous member breadth quantile (realised over the anchor, NOT causal), and whether the causal trailing-24h breadth trigger
(r1a q=0.90 definition) was on. Identity check first: Σ_n W·y4 vs the record's pnl column. usage: loss_anatomy.py <probe_dir> <meta.npz> <out.json>"""
import sys, json, time, hashlib, numpy as np
PD, META, OUT = sys.argv[1:4]; WA0, UB = 1656547200, 1788120000
z = np.load(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_OVLnone.npz", allow_pickle=True); C = [str(c) for c in z["cols"]]; rec = np.asarray(z["d30_n2_c42_rec"], float); W = np.asarray(z["d30_n2_c42_W"], float)
ts = rec[:, C.index("ts")].astype(np.int64); gross = rec[:, C.index("gross_total")]; pnl = rec[:, C.index("pnl")]; net = rec[:, C.index("net_ex")]
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], float); MEM = M["members"]; pos = {int(t): i for i, t in enumerate(E)}
I = np.array([pos[int(t)] for t in ts]); Y = np.where(np.isfinite(y4[I]), y4[I], 0.0)                     # realised 4h return of every name over each recorded anchor
contrib = W * Y * 1e4; recon = contrib.sum(1) / np.where(gross > 0, gross, np.nan)                        # bps per unit gross, pre-cost
ident = {"corr_recon_vs_pnl": float(np.corrcoef(np.nan_to_num(recon), np.nan_to_num(pnl))[0, 1]), "median_abs_diff": float(np.nanmedian(np.abs(recon - pnl))), "p99_abs_diff": float(np.nanpercentile(np.abs(recon - pnl), 99)), "note": "pnl col may include reshape/lag conventions; use recon only for the split shares"}
# breadth: contemporaneous (realised over the anchor) and causal trailing-24h (overlay definition)
bc = np.array([Y[k][np.asarray(MEM[I[k]]).astype(int)].mean() for k in range(len(ts))])
def breadth(i, m, look=6):
    if i < look: return np.nan
    seg = y4[i - look:i][:, m]; seg = np.where(np.isfinite(seg), seg, 0.0); return float(seg.mean(1).sum())
bt = np.array([breadth(I[k], np.asarray(MEM[I[k]]).astype(int)) for k in range(len(ts))]); trig = np.zeros(len(ts), bool); hist = []
for k in range(len(ts)):
    b = bt[k]
    if np.isfinite(b):
        if len(hist) >= 200 and b >= np.quantile(hist, 0.90): trig[k] = True
        hist.append(b)
WA = (ts >= WA0) & (ts <= UB); ranks_c = np.argsort(np.argsort(bc)) / len(bc)
g = np.nan_to_num(net / np.where(gross > 0, gross, np.nan))   # bps per unit gross (constant-leverage convention, same as overlay_eval)
day = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts])
def anat(idx):
    c = contrib[idx].sum(0) if np.ndim(idx) else contrib[idx]; Wk = W[idx]; lossk = c[c < 0]
    long_loss = float(c[(Wk > 0) if np.ndim(Wk) == 1 else (Wk.sum(0) > 0)].clip(max=0).sum()); short_loss = float(c[(Wk < 0) if np.ndim(Wk) == 1 else (Wk.sum(0) < 0)].clip(max=0).sum())
    tot_loss = long_loss + short_loss; top3 = float(np.sort(c)[:3].sum() / tot_loss) if tot_loss < 0 else np.nan
    return {"long_loss_share": long_loss / tot_loss if tot_loss < 0 else np.nan, "short_loss_share": short_loss / tot_loss if tot_loss < 0 else np.nan, "top3_names_share_of_loss": top3, "n_names_losing": int((c < 0).sum())}
order = np.argsort(np.where(WA, g, np.inf)); worst = order[:91]                                             # worst 1% anchors in W_ALPHA
rows = []
for k in worst:
    a = anat(k); a.update({"utc": time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[k]))), "net_bps": float(g[k]), "breadth_contemp": float(bc[k]), "breadth_contemp_q": float(ranks_c[k]), "trailing_trigger_on": bool(trig[k])}); rows.append(a)
def summ(rs):
    return {"n": len(rs), "mean_long_loss_share": float(np.nanmean([r["long_loss_share"] for r in rs])), "mean_short_loss_share": float(np.nanmean([r["short_loss_share"] for r in rs])), "median_top3_share": float(np.nanmedian([r["top3_names_share_of_loss"] for r in rs])),
            "frac_contemp_breadth_top_decile": float(np.mean([r["breadth_contemp_q"] >= 0.9 for r in rs])), "frac_contemp_breadth_bottom_decile": float(np.mean([r["breadth_contemp_q"] <= 0.1 for r in rs])), "frac_trailing_trigger_on": float(np.mean([r["trailing_trigger_on"] for r in rs]))}
# worst UTC days (L=2 compounding of the 6 anchors)
ud = np.unique(day[WA]); dr = {}
for d in ud:
    m = WA & (day == d); dr[d] = float(np.prod(1 + 2.0 * g[m] * 1e-4) - 1)
wd = sorted(dr.items(), key=lambda kv: kv[1])[:20]; drows = []
for d, r in wd:
    m = np.where(WA & (day == d))[0]; a = anat(m); a.update({"day": d, "ret_L2": r, "anchors": int(len(m)), "breadth_contemp_day": float(bc[m].sum()), "frac_anchors_contemp_top_decile": float(np.mean(ranks_c[m] >= 0.9)), "trailing_trigger_any": bool(trig[m].any()), "worst_anchor_bps": float(g[m].min())}); drows.append(a)
all_share = {"all_anchors_W_ALPHA": summ([dict(anat(k), breadth_contemp_q=float(ranks_c[k]), trailing_trigger_on=bool(trig[k])) for k in np.where(WA)[0][::10]])}
base_rate = {"trailing_trigger_rate": float(trig[WA].mean()), "g_when_trigger_on": float(g[WA & trig].mean()), "g_when_off": float(g[WA & ~trig].mean()), "g_contemp_top_decile": float(g[WA & (ranks_c >= 0.9)].mean()), "g_contemp_bottom_decile": float(g[WA & (ranks_c <= 0.1)].mean())}
# structural exposure: daily book return (L=2, per gross) vs daily member breadth; rally/sell-off asymmetry; breadth volatility by month
dd = np.array(sorted(dr)); rb = np.array([dr[d] for d in dd]); bb = np.array([bc[WA & (day == d)].sum() for d in dd])
def ols(x, y):
    x = x - x.mean(); y = y - y.mean(); b_ = float((x * y).sum() / (x * x).sum()); r2 = float(b_ * b_ * (x * x).sum() / (y * y).sum()); return b_, r2
b_all, r2_all = ols(bb, rb); b_up, _ = ols(bb[bb > 0], rb[bb > 0]); b_dn, _ = ols(bb[bb < 0], rb[bb < 0])
qb = np.quantile(np.abs(bb), 0.9); big = np.abs(bb) >= qb
expo = {"daily_beta_book_vs_breadth": b_all, "r2": r2_all, "beta_on_rally_days": b_up, "beta_on_selloff_days": b_dn, "mean_ret_big_breadth_days_top10pct_abs": float(rb[big].mean()), "mean_ret_other_days": float(rb[~big].mean()), "mean_ret_rally_days_top10pct": float(rb[bb >= np.quantile(bb, 0.9)].mean()), "mean_ret_selloff_days_bottom10pct": float(rb[bb <= np.quantile(bb, 0.1)].mean()), "n_days": int(len(dd))}
mon = np.array([d[:7] for d in dd]); bvol = {m: float(bb[mon == m].std(ddof=1)) for m in sorted(set(mon)) if (mon == m).sum() > 10}
yr = np.array([d[:4] for d in dd]); bvol_year = {y: float(bb[yr == y].std(ddof=1)) for y in sorted(set(yr))}
# what happens after a bad day: mean next-day and next-3-day return after days ≤ −2.68% / ≤ −2% / ≤ −1% (does a daily flatten protect or cost?)
after = {}
for thr in (-0.0268, -0.02, -0.01):
    idx = np.where(rb <= thr)[0]; idx = idx[idx + 3 < len(rb)]
    after[str(thr)] = {"n": int(len(idx)), "mean_next_day": float(rb[idx + 1].mean()) if len(idx) else None, "mean_next_3_days": float(sum(rb[idx + k] for k in (1, 2, 3)).mean()) if len(idx) else None, "frac_next_day_negative": float((rb[idx + 1] < 0).mean()) if len(idx) else None, "unconditional_mean_day": float(rb.mean())}
out = {"device": "loss_anatomy.py", "after_bad_day": after, "structural_exposure": expo, "breadth_daily_sd_by_month_2026": {m: v for m, v in bvol.items() if m.startswith("2026")}, "breadth_daily_sd_by_year": bvol_year, "breadth_daily_sd_2026_08": bvol.get("2026-08"), "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%FT%TZ", time.gmtime()), "identity": ident, "worst_1pct_anchors": {"summary": summ(rows), "rows": rows[:30]}, "worst_20_days": drows, "base_rates": base_rate, "reference": all_share}
json.dump(out, open(OUT, "w"), indent=1, default=float)
print("identity", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ident.items()})
print("structural", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in expo.items()}); print("breadth sd by year", {k: round(v, 4) for k, v in bvol_year.items()}); print("breadth sd 2026 months", {k: round(v, 4) for k, v in bvol.items() if k.startswith("2026")})
print("after bad day", json.dumps(after))
print("base rates", {k: round(v, 3) for k, v in base_rate.items()})
print("worst 1% anchors", {k: round(v, 3) for k, v in summ(rows).items()})
print("reference (all anchors, 1/10 sample)", {k: round(v, 3) for k, v in all_share["all_anchors_W_ALPHA"].items()})
for r in drows[:15]: print(f"{r['day']} L2 {r['ret_L2']:+.4f} anchors {r['anchors']} worst {r['worst_anchor_bps']:+.1f} | long-loss {r['long_loss_share']:.2f} short-loss {r['short_loss_share']:.2f} top3 {r['top3_names_share_of_loss']:.2f} | breadth day {r['breadth_contemp_day']:+.4f} top-dec anchors {r['frac_anchors_contemp_top_decile']:.2f} | trailing trigger {r['trailing_trigger_any']}")
