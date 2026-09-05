"""paired_compare.py — paired comparison of the extended primary arm (EXT: FPRED = new 2026-fold preds covering 2026-01-01→08-30) against the
health_check primary arm (HC: M1_UPIT_prod_s{seed}_ccal, old preds to 08-10) on the overlap 2024-01-01 → 2026-08-10 20:00Z, per-gross g = net_ex/gross_total
[bps/anchor per gross]; Δ = g_EXT − g_HC; UTC-day-block bootstrap (2000 resamples, seed 20260905) CI95 of mean Δ and of Δ anchor-Sharpe; by-year; plus
the 08-11→08-30 stretch (EXT has the F10 leg, HC has not) and 2026-01-01→08-10 alone. Also EXT vs EXT0901 (09-01 ext-run preds, same recipe) if present.
usage: paired_compare.py <seed> <ext.npz> <hc.npz> [ext0901.npz]"""
import numpy as np, json, time, sys, calendar, hashlib
ROOT = "/workspace/review_scratch/v2main_fold2026"; NB = 2000; SEED = 20260905; APY = 2190
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; END = T("2026-08-30") + 20 * 3600
def load(p):
    Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS; R = Z["d30_n2_c42_rec"]; cfg = json.loads(str(Z["config_json"]))
    return R[:, C["ts"]].astype(np.int64), R[:, C["net_ex"]] / R[:, C["gross_total"]], R, cfg
def r4(v): return round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 else float("nan")
def boot_delta(a, b, ts):
    d = a - b; days = ts // 86400; ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float); rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd))
    m = s1[idx].sum(1) / c[idx].sum(1)
    # Sharpe Δ under the same day resample: recompute both Sharpes from resampled days
    A1 = np.bincount(inv, a); A2 = np.bincount(inv, a * a); B1 = np.bincount(inv, b); B2 = np.bincount(inv, b * b)
    def sh(S1, S2, Cn): mu = S1 / Cn; var = np.maximum((S2 - Cn * mu * mu) / (Cn - 1), 1e-18); return mu / np.sqrt(var) * np.sqrt(APY)
    Cn = c[idx].sum(1); dsh = sh(A1[idx].sum(1), A2[idx].sum(1), Cn) - sh(B1[idx].sum(1), B2[idx].sum(1), Cn)
    return {"n_anchors": int(len(d)), "n_days": int(nd), "mean_ext": r4(a.mean()), "mean_hc": r4(b.mean()), "delta_mean": r4(d.mean()), "delta_ci95": [r4(np.percentile(m, 2.5)), r4(np.percentile(m, 97.5))], "p_delta_gt0": r4((m > 0).mean()),
            "sharpe_ext": r4(sharpe(a)), "sharpe_hc": r4(sharpe(b)), "delta_sharpe": r4(sharpe(a) - sharpe(b)), "delta_sharpe_ci95": [r4(np.percentile(dsh, 2.5)), r4(np.percentile(dsh, 97.5))],
            "share_anchors_nonzero_delta": r4((np.abs(d) > 1e-12).mean()), "max_abs_delta": r4(np.abs(d).max()), "nav_pct_yr_at_2x_ext": r4(a.mean() * 2 * APY / 1e4 * 100), "nav_pct_yr_at_2x_hc": r4(b.mean() * 2 * APY / 1e4 * 100)}
seed, pe, ph = sys.argv[1], sys.argv[2], sys.argv[3]; pe01 = sys.argv[4] if len(sys.argv) > 4 else None
te, ge, Re, ce = load(pe); th, gh, Rh, ch = load(ph)
assert np.array_equal(te, th), "anchor grids differ"
out = {"seed": seed, "ext": {"path": pe, "sha16": hashlib.sha256(open(pe, "rb").read()).hexdigest()[:16], "FPRED": ce.get("FPRED")}, "hc": {"path": ph, "sha16": hashlib.sha256(open(ph, "rb").read()).hexdigest()[:16], "FPRED": ch.get("FPRED")},
       "config_equal_minus_FPRED": {k: (ce.get(k), ch.get(k)) for k in set(ce) | set(ch) if k not in ("FPRED", "HEALTH") and ce.get(k) != ch.get(k)} == {}, "windows": {}}
W = {"overlap_2024-01-01->2026-08-10": (T("2024-01-01"), CUT + 1), "2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026-01-01->08-10": (T("2026-01-01"), CUT + 1),
     "2025->26_to_cut": (T("2025-01-01"), CUT + 1), "stretch_2026-08-11->08-30 (EXT has F10 leg, HC has not)": (CUT + 1, END + 1), "2026->0830 (EXT full vs HC with F10 absent after cut)": (T("2026-01-01"), END + 1), "2024->0830": (T("2024-01-01"), END + 1)}
for wn, (lo, hi) in W.items():
    m = (te >= lo) & (te < hi)
    if m.sum() < 12: continue
    out["windows"][wn] = boot_delta(ge[m], gh[m], te[m])
# pre-2026 must be identical (F10P rows unchanged before 2026)
mpre = te < T("2026-01-01"); out["pre2026_identical"] = bool(np.array_equal(Re[mpre], Rh[mpre])); out["pre2026_max_abs_delta_g"] = r4(np.abs(ge[mpre] - gh[mpre]).max())
if pe01:
    t1, g1, R1, c1 = load(pe01); assert np.array_equal(t1, te); out["ext_vs_ext0901"] = {}
    for wn in ("overlap_2024-01-01->2026-08-10", "2026->0830 (EXT full vs HC with F10 absent after cut)", "stretch_2026-08-11->08-30 (EXT has F10 leg, HC has not)"):
        lo, hi = W[wn]; m = (te >= lo) & (te < hi); out["ext_vs_ext0901"][wn.split(" ")[0]] = boot_delta(ge[m], g1[m], te[m])
json.dump(out, open(f"{ROOT}/results/paired_s{seed}.json", "w"), indent=1)
print(f"# paired EXT vs HC s{seed}  config_equal_minus_FPRED={out['config_equal_minus_FPRED']}  pre2026_identical={out['pre2026_identical']}")
print("| window | n | mean EXT | mean HC | Δ [CI95] | P(Δ>0) | Sharpe EXT / HC | ΔSharpe [CI95] | share anchors Δ≠0 |"); print("|---|---|---|---|---|---|---|---|---|")
for wn, w in out["windows"].items():
    print(f"| {wn} | {w['n_anchors']} | {w['mean_ext']} | {w['mean_hc']} | {w['delta_mean']} [{w['delta_ci95'][0]}, {w['delta_ci95'][1]}] | {w['p_delta_gt0']} | {w['sharpe_ext']} / {w['sharpe_hc']} | {w['delta_sharpe']} [{w['delta_sharpe_ci95'][0]}, {w['delta_sharpe_ci95'][1]}] | {w['share_anchors_nonzero_delta']} |")
if pe01:
    print("\n# EXT (this campaign) vs EXT0901 (09-01 ext-run preds, same recipe/data, no saved model)")
    for wn, w in out["ext_vs_ext0901"].items(): print(f"| {wn} | n={w['n_anchors']} | Δ {w['delta_mean']} [{w['delta_ci95'][0]}, {w['delta_ci95'][1]}] | Sharpe {w['sharpe_ext']} vs {w['sharpe_hc']} |")
