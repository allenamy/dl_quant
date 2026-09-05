"""ic_monthly.py — dl_monthly_wf: score-level diagnostics on the ext grid (dlw_ext targets: y4s = Π(1+r5)−1 over [E+1,E+48], the trainer's own frame
= the replay's prod caliber). Per-anchor rank IC = Spearman over the anchor's members with finite score and finite y4s (≥30).
  (1) IC by window for yearly (0822 grid, padded), mE60, mE1: 2025 | 2026≤cut(08-10 20Z) | 2025→26≤cut (PRIMARY) | 2026-08-11→30 (monthly only)
      paired ΔIC vs yearly on common anchors: mean, anchor s.e., UTC-day-block bootstrap CI95 (2000, seed 20260905)
  (2) overlap agreement: per-anchor Spearman(monthly score, yearly score) over common finite members, 2026-01→08-10 and 2025
  (3) IC-by-model-age (axis A D1 analogue): fold model of month M scores months M..M+5 (age 1..6); paired on anchors where all 6 ages exist (2025-06→2026-08)
  (4) F10 score-leg return by year: z = rank position of the score among members (rankdata/(n−1) − 0.5, zeros where y4s is NaN, demeaned over finite y),
      leg = Σ(z/Σ|z| · y4s)·1e4 bps per unit gross per anchor; paired Δ vs yearly with the same bootstrap
  (5) monthly IC table (each test month, three files)
usage: ic_monthly.py <TAG> [<TAG>...]  → logs/ic_<tags>.json + stdout"""
import sys, os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr, rankdata
R = "/workspace/review_scratch/dl_monthly_wf"; YEARLY = "/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"; NB = 2000; SEED = 20260905
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E)
B = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); nB = len(B["E_ts"]); assert np.array_equal(E[:nB], B["E_ts"].astype(np.int64))
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E]); days = E // 86400
WIN = {"2025": (E >= T25) & (E < T26), "2026<=cut": (E >= T26) & (E <= CUT), "2025->26<=cut": (E >= T25) & (E <= CUT), "2026-08-11->30": E > CUT}
TAGS = sys.argv[1:]; assert TAGS
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def ic_series(P):
    ic = np.full(nA, np.nan)
    for i in range(nA):
        m = MEM[i]; a = P[i, m]; b = Y4[i, m]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], b[ok]).correlation
    return ic
def leg_series(P):
    lg = np.full(nA, np.nan)
    for i in range(nA):
        m = MEM[i]; s = P[i, m]; y = Y4[i, m]; oks = np.isfinite(s); oky = np.isfinite(y)
        if oks.sum() < 10 or oky.sum() < 10: continue
        z = np.full(len(m), np.nan); z[oks] = rankdata(s[oks]) / max(oks.sum() - 1, 1) - 0.5; z = np.nan_to_num(z); z = np.where(oky, z, 0.0); z -= z[oky].mean()
        g = np.abs(z).sum()
        if g > 1e-9: lg[i] = float((z / g * np.nan_to_num(y)).sum() * 1e4)
    return lg
def agree_series(P, Q):
    ag = np.full(nA, np.nan)
    for i in range(nA):
        m = MEM[i]; a = P[i, m]; b = Q[i, m]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ag[i] = spearmanr(a[ok], b[ok]).correlation
    return ag
rng = np.random.default_rng(SEED)
def boot(x, mask):
    m = mask & np.isfinite(x); v = x[m]; d = days[m]
    if m.sum() < 10: return {"n": int(m.sum())}
    ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "se_anchor": float(v.std(ddof=1) / np.sqrt(len(v))), "ci95_dayblock": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))], "p_gt0": float((means > 0).mean())}
def r5(o):
    if isinstance(o, dict): return {k: r5(v) for k, v in o.items()}
    if isinstance(o, list): return [r5(v) for v in o]
    if isinstance(o, float): return round(o, 5)
    return o
PY = np.full((nA, 829), np.nan, np.float32); PY[:nB] = np.load(YEARLY)
FILES = {"yearly": PY}; SHAS = {"yearly": sha(YEARLY)}
for T in TAGS:
    p = f"{R}/preds/f10_V2MAIN_{T}_s42.npy"; FILES[T] = np.load(p); SHAS[T] = sha(p)
IC = {k: ic_series(v) for k, v in FILES.items()}; LEG = {k: leg_series(v) for k, v in FILES.items()}
OUT = {"inputs": SHAS, "targets": "/workspace/dlw_ext/data/dlw_targets.npz (y4s = Π(1+r5)−1 over [E+1,E+48])", "cut": iso(CUT), "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "ic_levels": {}, "ic_delta_vs_yearly": {}, "agreement": {}, "age_curve": {}, "leg_levels": {}, "leg_delta_vs_yearly": {}, "monthly_ic": {}}
print(f"files: " + ", ".join(f"{k} {v[:12]}" for k, v in SHAS.items()))
for w, mk in WIN.items():
    for k in FILES:
        x = IC[k]; m = mk & np.isfinite(x)
        if m.sum() < 10: continue
        OUT["ic_levels"][f"{w}/{k}"] = {"n": int(m.sum()), "mean": float(x[m].mean()), "se_anchor": float(x[m].std(ddof=1) / np.sqrt(m.sum())), "share_pos": float((x[m] > 0).mean())}
        y = LEG[k]; ml = mk & np.isfinite(y)
        OUT["leg_levels"][f"{w}/{k}"] = {"n": int(ml.sum()), "mean_bps": float(y[ml].mean()), "sharpe_anchor": float(y[ml].mean() / y[ml].std(ddof=1) * np.sqrt(2190)), "pct_gross_yr": float(y[ml].mean() * 2190 / 100)}
    for T in TAGS:
        common = mk & np.isfinite(IC[T]) & np.isfinite(IC["yearly"])
        if common.sum() >= 10: OUT["ic_delta_vs_yearly"][f"{w}/{T}"] = boot(IC[T] - IC["yearly"], common)
        commonl = mk & np.isfinite(LEG[T]) & np.isfinite(LEG["yearly"])
        if commonl.sum() >= 10: OUT["leg_delta_vs_yearly"][f"{w}/{T}"] = boot(LEG[T] - LEG["yearly"], commonl)
    if len(TAGS) == 2:
        common = mk & np.isfinite(IC[TAGS[0]]) & np.isfinite(IC[TAGS[1]])
        if common.sum() >= 10: OUT["ic_delta_vs_yearly"][f"{w}/{TAGS[1]}-{TAGS[0]}"] = boot(IC[TAGS[1]] - IC[TAGS[0]], common)
print("\n== IC levels (rank IC per anchor, mean ± anchor s.e.) ==")
for k, v in OUT["ic_levels"].items(): print(f"  {k:28s} n={v['n']:5d} IC {v['mean']:+.4f} ± {v['se_anchor']:.4f}  share>0 {v['share_pos']:.3f}")
print("== paired ΔIC vs yearly (day-block bootstrap CI95) ==")
for k, v in OUT["ic_delta_vs_yearly"].items(): print(f"  {k:28s} n={v.get('n')} Δ {v.get('mean', float('nan')):+.4f} ± {v.get('se_anchor', float('nan')):.4f} CI95 [{v.get('ci95_dayblock', [np.nan, np.nan])[0]:+.4f},{v.get('ci95_dayblock', [np.nan, np.nan])[1]:+.4f}] P>0 {v.get('p_gt0', float('nan')):.3f}")
# (2) agreement
for T in TAGS:
    ag = agree_series(FILES[T], PY)
    for w in ("2026<=cut", "2025", "2025->26<=cut"):
        m = WIN[w] & np.isfinite(ag)
        if m.sum() < 10: OUT["agreement"][f"{w}/{T}"] = {"n": int(m.sum()), "mean": float("nan"), "median": float("nan"), "p5": float("nan"), "p95": float("nan"), "min": float("nan")}; continue
        OUT["agreement"][f"{w}/{T}"] = {"n": int(m.sum()), "mean": float(ag[m].mean()), "median": float(np.median(ag[m])), "p5": float(np.percentile(ag[m], 5)), "p95": float(np.percentile(ag[m], 95)), "min": float(ag[m].min())}
print("== overlap agreement: per-anchor Spearman(monthly, yearly) ==")
for k, v in OUT["agreement"].items(): print(f"  {k:28s} n={v['n']} mean {v['mean']:.4f} median {v['median']:.4f} p5 {v['p5']:.4f} p95 {v['p95']:.4f} min {v['min']:.4f}")
# (3) age curve
MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]; midx = {m: k for k, m in enumerate(MONTHS)}
for T in TAGS:
    PF = {}
    for m in MONTHS:
        p = f"{R}/preds_fold/{T}_{m}.npz"
        if os.path.exists(p): z = np.load(p); PF[m] = (int(z["first_te"]), z["P"])
    ICA = np.full((nA, 6), np.nan)
    for i in range(nA):
        if ym[i] < 202501 or ym[i] > 202608: continue
        for a in range(1, 7):
            k = midx[int(ym[i])] - (a - 1)
            if k < 0: continue
            mm = MONTHS[k]
            if mm not in PF: continue
            f0, P = PF[mm]
            if i < f0: continue
            m = MEM[i]; s = P[i - f0, m]; y = Y4[i, m]; ok = np.isfinite(s) & np.isfinite(y)
            if ok.sum() >= 30: ICA[i, a - 1] = spearmanr(s[ok], y[ok]).correlation
    full = np.isfinite(ICA).all(1)
    cur = {"n_folds_loaded": len(PF), "n_anchors_all6": int(full.sum()), "first": iso(E[np.where(full)[0][0]]) if full.any() else None, "last": iso(E[np.where(full)[0][-1]]) if full.any() else None, "ic_by_age": {}, "delta_age1_minus": {}}
    if full.sum() >= 30:
        for a in range(6):
            cur["ic_by_age"][str(a + 1)] = float(ICA[full, a].mean())
            if a > 0: cur["delta_age1_minus"][str(a + 1)] = boot(ICA[:, 0] - ICA[:, a], full)
        # own-month (age 1) consistency with the stitched file
        chk = np.isfinite(ICA[:, 0]) & np.isfinite(IC[T]); cur["age1_equals_stitched_maxabs"] = float(np.max(np.abs(ICA[chk, 0] - IC[T][chk]))) if chk.any() else None
    OUT["age_curve"][T] = cur
    print(f"== IC by model age [{T}] n={cur['n_anchors_all6']} anchors {cur.get('first')}→{cur.get('last')}: " + " ".join(f"age{a}={v:+.4f}" for a, v in cur["ic_by_age"].items())
          + " | Δ(1−a): " + " ".join(f"a{a} {v['mean']:+.4f}[{v['ci95_dayblock'][0]:+.4f},{v['ci95_dayblock'][1]:+.4f}]" for a, v in cur["delta_age1_minus"].items()) + f" | age1==stitched maxabs {cur.get('age1_equals_stitched_maxabs')}")
# (4) leg tables
print("== F10 score-leg return by window (bps/anchor per unit gross; dlw y4s caliber) ==")
for k, v in OUT["leg_levels"].items(): print(f"  {k:28s} n={v['n']:5d} {v['mean_bps']:+.3f} bps S {v['sharpe_anchor']:+.2f} ({v['pct_gross_yr']:+.1f} %/gross/yr)")
for k, v in OUT["leg_delta_vs_yearly"].items(): print(f"  Δ {k:26s} n={v.get('n')} {v.get('mean', float('nan')):+.3f} CI95 [{v.get('ci95_dayblock', [np.nan, np.nan])[0]:+.3f},{v.get('ci95_dayblock', [np.nan, np.nan])[1]:+.3f}] P>0 {v.get('p_gt0', float('nan')):.3f}")
# (5) monthly table
for m in MONTHS:
    mk = ym == m; row = {}
    for k in FILES:
        x = IC[k]; mm = mk & np.isfinite(x)
        row[k] = {"n": int(mm.sum()), "ic": float(x[mm].mean()) if mm.sum() else None}
    OUT["monthly_ic"][str(m)] = row
print("== monthly IC (test month × file) ==")
print("  month   | " + " | ".join(f"{k:>8s}" for k in FILES))
for m, row in OUT["monthly_ic"].items(): print(f"  {m} | " + " | ".join((f"{row[k]['ic']:+.4f}" if row[k]['ic'] is not None else "     nan") for k in FILES))
json.dump(r5(OUT), open(f"{R}/logs/ic_{'_'.join(TAGS)}.json", "w"), indent=1)
print("IC_DONE", flush=True)
