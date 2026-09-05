#!/usr/bin/env python
"""carry_sleeve.py — DIAGNOSTIC (team-lead round 4, 2026-09-06): paper delta-neutral funding-carry sleeve, UPPER BOUND, and its diversification arithmetic with the live book. No arm, no judge.
Sleeve (per 4h anchor E, causal): predicted rate = last settled rate known at E (panel f_fund_now, bps per settlement; == prev settlement's rate, verified 100% in carry_layers/data/sett_receipt.json);
  eligible = finite & predicted ≥ h; hold long-spot/short-perp on the top-K eligible names by predicted rate, equal weight 1/K (deployed gross = n_sel/K ≤ 1; flat when none eligible);
  income over (E, E+4h] = Σ_{settlements in window} w_k · r_S,k (short perp receives positive funding; realised rates from carry_layers/data/sett_tables.npz R);
  costs = 3.92 bps × Σ|Δw| (perp, all-in per unit perp turnover) + 10 bps × Σ|Δw| (spot, per unit spot turnover, as specified); basis P&L, borrow, spot availability, fee tiers on spot: IGNORED ⇒ upper bound.
Units: bps per anchor per unit target sleeve gross (perp notional 1 when fully deployed; the spot leg needs an equal notional of spot capital on top). Sharpe = mean/std(ddof=1)·√2190; maxDD from Π(1+r/1e4) at 1× sleeve gross.
Book = health_check main arm B0_prod_s{42,2027} (bitwise; carry_layers/dev_alt) per-gross net g = net_ex/gross_total on the same anchors. Mixes r = a·g + (1−a)·s (gross split a : 1−a, per unit total gross).
Analytic line: equal-vol 50:50 ⇒ S_mix = (S1+S2)/√(2+2ρ) ⇒ S2 needed for S_mix = 3: S2 = 3√(2+2ρ) − S1; general (measured σ, split a): S_mix = (aσ1S1 + bσ2S2)/√(a²σ1² + b²σ2² + 2abρσ1σ2).
Output: results/sleeve.json, results/sleeve_tables.md. Read-only on inputs; writes under carry_sleeve/."""
import numpy as np, json, time, calendar, hashlib, os
ROOT = "/workspace/review_scratch/allweather_trackC/carry_sleeve"; CL = "/workspace/review_scratch/allweather_trackC/carry_layers"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
APY = 2190; PERP_C = 3.92; SPOT_C = 10.0; KS = (10, 20, 40); HS = (5.0, 10.0)
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; LO = T("2023-01-01")
WIN = {"2023": (T("2023-01-01"), T("2024-01-01")), "2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2023->cut": (LO, CUT + 1), "2024->cut": (T("2024-01-01"), CUT + 1)}
YEARS = ("2023", "2024", "2025", "2026->cut")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x, L=1.0): nav = np.cumprod(1.0 + L * x / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
print("UNITS CHAIN: sleeve bps/anchor per unit target sleeve gross (perp notional; spot leg = equal extra capital); book g = net_ex/gross_total; mix per unit total gross; NAV %/yr at 1x = mean × 6 × 365 / 1e4 × 100, at 2x total gross = mean × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 21.9 %/yr at 1x, 43.8 %/yr at 2x); Sharpe = mean/std(ddof=1)×√2190", flush=True)
ST = np.load(f"{CL}/data/sett_tables.npz"); SR = ST["R"].astype(np.float64); E0 = ST["E_ts"].astype(np.int64); SY = [str(s) for s in ST["symbols"]]; NW = len(SY); arow = {int(t): i for i, t in enumerate(E0)}
PW = np.load(PANEL, allow_pickle=True); assert [str(s) for s in PW["symbols"]] == SY; pts = PW["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pts)}; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
books = {}
for s in ("42", "2027"):
    p = f"{CL}/dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s{s}.npz"; Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS; R = Z["d30_n2_c42_rec"]
    books[s] = {"path": p, "sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "ts": R[:, 0].astype(np.int64), "g": R[:, C["net_ex"]] / R[:, C["gross_total"]], "W": Z["d30_n2_c42_W"].astype(np.float64), "gt": R[:, C["gross_total"]]}
ts = books["42"]["ts"]; assert np.array_equal(ts, books["2027"]["ts"]); m = (ts >= LO) & (ts < CUT); idx = np.where(m)[0]; tsw = ts[m]; yrs = np.array([time.gmtime(int(t)).tm_year for t in tsw])
out = {"definition": {"K": KS, "h_bps_per_settlement": HS, "perp_cost_bps_per_unit_turnover": PERP_C, "spot_cost_bps_per_unit_turnover": SPOT_C, "window": "2023-01-01 → 2026-08-10 20:00Z", "n_anchors": int(m.sum()), "upper_bound_omits": ["basis P&L (spot−perp)", "borrow", "spot availability", "spot fee tiers", "funding-interval hetero­geneity in ranking (ranked per settlement as specified)"]},
       "book": {s: {"artifact": books[s]["path"], "sha16": books[s]["sha16"]} for s in books}, "arms": {}, "diversification": {}}
WB = {s: books[s]["W"][m] for s in books}; gB = {s: books[s]["g"][m] for s in books}
def stats(x, turn, nsel, dep):
    o = {}
    for wn, (lo, hi) in WIN.items():
        mm = (tsw >= lo) & (tsw < hi); xw = x[mm]
        o[wn] = {"n": int(mm.sum()), "mean_bps": r4(xw.mean()), "sharpe": r4(sharpe(xw)), "std_bps": r4(xw.std(ddof=1)), "maxdd_pct_1x": r4(maxdd(xw)), "maxdd_pct_2x": r4(maxdd(xw, 2.0)), "turnover_per_gross": r4(turn[mm].mean()), "n_selected_mean": r4(nsel[mm].mean()), "deployed_gross_mean": r4(dep[mm].mean()), "share_anchors_no_eligible": r4((nsel[mm] == 0).mean()), "nav_pct_yr_at_1x": r4(xw.mean() * 6 * 365 / 1e4 * 100)}
    return o
for K in KS:
    for h in HS:
        w_prev = np.zeros(NW); inc = np.zeros(len(idx)); cost = np.zeros(len(idx)); turn = np.zeros(len(idx)); nsel = np.zeros(len(idx)); dep = np.zeros(len(idx)); ov_n = np.zeros(len(idx)); ov_g = {s: np.zeros(len(idx)) for s in books}; sel_int = {"1h": 0, "4h": 0, "8h": 0, "other": 0}
        for n, r in enumerate(idx):
            i = arow[int(ts[r])]; j = prow[int(ts[r])]; pr = FN[j] * 1e4; el = np.isfinite(pr) & (pr >= h)
            w = np.zeros(NW)
            if el.any():
                ks = np.where(el)[0]; ks = ks[np.argsort(-pr[ks])][:K]; w[ks] = 1.0 / K
                for k in ks: iv = IV[j, k]; sel_int["1h" if iv == 1 else "4h" if iv == 4 else "8h" if iv == 8 else "other"] += 1
            Rk = SR[i]; inc[n] = float(np.nansum(np.where(np.isfinite(Rk), Rk, 0.0) * w[:, None]) * 1e4)
            dw = float(np.abs(w - w_prev).sum()); turn[n] = dw; cost[n] = (PERP_C + SPOT_C) * dw; nsel[n] = int((w > 0).sum()); dep[n] = float(w.sum())
            held = w > 0
            if held.any():
                for s in books: wb = WB[s][n]; ov_g[s][n] = float(np.abs(wb[held & (wb > 0)]).sum() / max(np.abs(wb).sum(), 1e-12))
                ov_n[n] = float((held & (WB["42"][n] > 0)).mean() if False else ((WB["42"][n][held] > 0).mean()))
            w_prev = w
        net = inc - cost; tag = f"K{K}_h{int(h)}"
        st = stats(net, turn, nsel, dep); st_gross = stats(inc, turn, nsel, dep)
        arm = {"K": K, "h": h, "levels_net": st, "levels_income_only": {wn: {"mean_bps": st_gross[wn]["mean_bps"], "sharpe": st_gross[wn]["sharpe"]} for wn in WIN}, "cost_mean_bps_2023cut": r4(cost.mean()), "perp_cost_mean": r4(PERP_C * turn.mean()), "spot_cost_mean": r4(SPOT_C * turn.mean()),
               "selected_interval_mix": {k: r4(v / max(sum(sel_int.values()), 1)) for k, v in sel_int.items()}, "overlap": {"share_of_sleeve_names_that_are_book_longs_s42": r4(ov_n[nsel > 0].mean()) if (nsel > 0).any() else None, "book_long_gross_in_sleeve_names_share_of_book_gross": {s: r4(ov_g[s][nsel > 0].mean()) for s in books}}, "series": {}}
        # diversification
        div = {}
        for s in books:
            g = gB[s]; rho = {wn: r4(np.corrcoef(g[(tsw >= lo) & (tsw < hi)], net[(tsw >= lo) & (tsw < hi)])[0, 1]) for wn, (lo, hi) in WIN.items()}
            mixes = {}
            for a in (1.0, 0.8, 0.7, 0.5):
                rmix = a * g + (1 - a) * net; sh = {wn: r4(sharpe(rmix[(tsw >= lo) & (tsw < hi)])) for wn, (lo, hi) in WIN.items()}
                mixes[f"{a:.1f}:{1-a:.1f}"] = {"sharpe": sh, "worst_year_sharpe": r4(min(sh[y] for y in YEARS)), "worst_year": min(YEARS, key=lambda y: sh[y]), "mean_bps_2023cut": r4(rmix.mean()), "nav_pct_yr_at_2x_total_gross": r4(rmix.mean() * 6 * 365 * 2 / 1e4 * 100)}
            wy = mixes["1.0:0.0"]["worst_year"]; mm = (tsw >= WIN[wy][0]) & (tsw < WIN[wy][1]); S1 = sharpe(g[mm]); s1 = g[mm].std(ddof=1); s2 = net[mm].std(ddof=1); S2m = sharpe(net[mm]); rho_w = float(np.corrcoef(g[mm], net[mm])[0, 1])
            analytic = {"book_worst_year": wy, "S1": r4(S1), "sigma_book_bps": r4(s1), "sigma_sleeve_bps": r4(s2), "S2_measured": r4(S2m), "rho_measured": r4(rho_w),
                        "equal_vol_50_50_S2_needed_for_3": {f"rho={r}": r4(3 * np.sqrt(2 + 2 * r) - S1) for r in (0.0, 0.3, rho_w)},
                        "measured_vol_S2_needed_for_3": {}}
            for a in (0.5, 0.7):
                b = 1 - a
                for r in (0.0, 0.3, rho_w):   # solve (aσ1S1 + bσ2S2)/sqrt(a²σ1²+b²σ2²+2abρσ1σ2) = 3
                    den = np.sqrt(a * a * s1 * s1 + b * b * s2 * s2 + 2 * a * b * r * s1 * s2); S2n = (3 * den - a * s1 * S1) / (b * s2) if s2 > 0 else float("nan")
                    analytic["measured_vol_S2_needed_for_3"][f"split={a:.1f}:{b:.1f},rho={r4(r)}"] = r4(S2n)
            mixes_io = {}
            for a in (1.0, 0.8, 0.7, 0.5):
                rmix = a * g + (1 - a) * inc; sh = {wn: r4(sharpe(rmix[(tsw >= lo) & (tsw < hi)])) for wn, (lo, hi) in WIN.items()}
                mixes_io[f"{a:.1f}:{1-a:.1f}"] = {"sharpe": sh, "worst_year_sharpe": r4(min(sh[y] for y in YEARS))}
            lines = {}
            for wy2 in (wy, "2025", "2024"):
                mm2 = (tsw >= WIN[wy2][0]) & (tsw < WIN[wy2][1]); S1b = sharpe(g[mm2]); sb = g[mm2].std(ddof=1); ss = net[mm2].std(ddof=1); si = inc[mm2].std(ddof=1)
                S2n = sharpe(net[mm2]); S2i = sharpe(inc[mm2]); rn = float(np.corrcoef(g[mm2], net[mm2])[0, 1]); ri = float(np.corrcoef(g[mm2], inc[mm2])[0, 1])
                lines[wy2] = {"S1": r4(S1b), "sigma_book": r4(sb), "sigma_sleeve_net": r4(ss), "sigma_sleeve_income": r4(si), "S2_net": r4(S2n), "S2_income_only": r4(S2i), "rho_net": r4(rn), "rho_income": r4(ri),
                              "S2_needed_equal_vol_50_50": {f"rho={r}": r4(3 * np.sqrt(2 + 2 * r) - S1b) for r in (0.0, 0.3)},
                              "leverage_to_match_book_vol_net": r4(sb / ss) if ss > 0 else None, "leverage_to_match_book_vol_income": r4(sb / si) if si > 0 else None,
                              "vol_matched_50_50_mix_sharpe_net": r4((S1b + S2n) / np.sqrt(2 + 2 * rn)), "vol_matched_50_50_mix_sharpe_income_only": r4((S1b + S2i) / np.sqrt(2 + 2 * ri))}
            div[s] = {"rho": rho, "mixes": mixes, "mixes_income_only": mixes_io, "analytic": analytic, "lines_by_year": lines}
        arm["diversification"] = div; out["arms"][tag] = arm
rows = []
for tag, a in out["arms"].items():
    inc_ = a["levels_income_only"]["2023->cut"]["mean_bps"]; tu_ = a["levels_net"]["2023->cut"]["turnover_per_gross"]; be = inc_ / tu_ if tu_ else float("nan")
    rows.append({"arm": tag, "income_mean_bps": inc_, "turnover_per_gross": tu_, "breakeven_allin_cost_bps_per_unit_turnover": r4(be), "assumed_cost": PERP_C + SPOT_C, "turnover_cut_needed_pct_at_assumed_cost": r4((1 - be / (PERP_C + SPOT_C)) * 100)}); a["breakeven"] = rows[-1]
out["breakeven_table"] = rows
os.makedirs(f"{ROOT}/results", exist_ok=True); json.dump(out, open(f"{ROOT}/results/sleeve.json", "w"), indent=1)
L = []; P = L.append
P(f"## Paper carry sleeve (UPPER BOUND; diagnostic): long-spot/short-perp on top-K names by predicted (last settled) funding ≥ h, equal weight 1/K; income = realised funding on perp notional; costs 3.92 (perp) + 10 (spot) bps per unit turnover; basis/borrow/spot availability ignored. Units: bps/anchor per unit target sleeve gross (perp notional; spot leg needs equal extra capital). 2023-01→2026-08-10, {int(m.sum())} anchors.")
P("| arm | window | net mean bps/anchor | Sharpe | σ bps | maxDD 1× | turnover/gross | n sel | deployed | no-eligible share | income-only mean / Sharpe | NAV %/yr at 1× |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for tag, a in out["arms"].items():
    for wn in ("2023", "2024", "2025", "2026->cut", "2023->cut"):
        s_ = a["levels_net"][wn]; io = a["levels_income_only"][wn]
        P(f"| {tag} | {wn} | {s_['mean_bps']:+.3f} | {s_['sharpe']:.2f} | {s_['std_bps']:.2f} | {s_['maxdd_pct_1x']:.1f}% | {s_['turnover_per_gross']:.4f} | {s_['n_selected_mean']:.1f} | {s_['deployed_gross_mean']:.3f} | {s_['share_anchors_no_eligible']:.3f} | {io['mean_bps']:+.3f} / {io['sharpe']:.2f} | {s_['nav_pct_yr_at_1x']:+.1f}% |")
P("\n## Costs and overlap (2023→cut)")
P("| arm | cost mean bps/anchor (perp / spot) | selected interval mix 1h/4h/8h | sleeve names that are book longs (share, s42) | book long gross sitting in sleeve names (share of book gross) s42 / s2027 |")
P("|---|---|---|---|---|")
for tag, a in out["arms"].items():
    im = a["selected_interval_mix"]; ov = a["overlap"]["book_long_gross_in_sleeve_names_share_of_book_gross"]
    P(f"| {tag} | {a['cost_mean_bps_2023cut']:.3f} ({a['perp_cost_mean']:.3f} / {a['spot_cost_mean']:.3f}) | {im['1h']:.2f}/{im['4h']:.2f}/{im['8h']:.2f} | {a['overlap']['share_of_sleeve_names_that_are_book_longs_s42']} | {ov['42']} / {ov['2027']} |")
P("\n## Diversification with the live book (per unit total gross; mix = a·book + (1−a)·sleeve): ρ by window; Sharpe by year for the mixes; worst-year and 2024→26 Sharpe")
P("| arm | seed | ρ 2023 / 2024 / 2025 / 2026 / 2023→cut | mix 1:0 S 23/24/25/26 (worst) | 0.8:0.2 | 0.7:0.3 | 0.5:0.5 | 2024→cut S 1:0 / .8 / .7 / .5 |")
P("|---|---|---|---|---|---|---|---|")
for tag, a in out["arms"].items():
    for s in ("42", "2027"):
        d = a["diversification"][s]; rh = d["rho"]; f = lambda k: f"{d['mixes'][k]['sharpe']['2023']:.2f}/{d['mixes'][k]['sharpe']['2024']:.2f}/{d['mixes'][k]['sharpe']['2025']:.2f}/{d['mixes'][k]['sharpe']['2026->cut']:.2f} (**{d['mixes'][k]['worst_year_sharpe']:.2f}**)"
        P(f"| {tag} | s{s} | {rh['2023']:+.2f} / {rh['2024']:+.2f} / {rh['2025']:+.2f} / {rh['2026->cut']:+.2f} / {rh['2023->cut']:+.2f} | {f('1.0:0.0')} | {f('0.8:0.2')} | {f('0.7:0.3')} | {f('0.5:0.5')} | {d['mixes']['1.0:0.0']['sharpe']['2024->cut']:.2f} / {d['mixes']['0.8:0.2']['sharpe']['2024->cut']:.2f} / {d['mixes']['0.7:0.3']['sharpe']['2024->cut']:.2f} / {d['mixes']['0.5:0.5']['sharpe']['2024->cut']:.2f} |")
P("\n## Analytic line (book's worst year per seed): S2 the sleeve would need for the mix to reach Sharpe 3")
P("| arm | seed | worst yr | S1 book | σ book / σ sleeve bps | S2 measured | ρ measured | equal-vol 50:50 S2 needed @ρ=0 / 0.3 / measured | measured-vol S2 needed 50:50 @ρ=0 / 0.3 / meas · 70:30 @ρ=0 / 0.3 / meas |")
P("|---|---|---|---|---|---|---|---|---|")
for tag, a in out["arms"].items():
    for s in ("42", "2027"):
        an = a["diversification"][s]["analytic"]; ev = an["equal_vol_50_50_S2_needed_for_3"]; mv = an["measured_vol_S2_needed_for_3"]; ks = list(mv.keys())
        P(f"| {tag} | s{s} | {an['book_worst_year']} | {an['S1']:.2f} | {an['sigma_book_bps']:.1f} / {an['sigma_sleeve_bps']:.1f} | {an['S2_measured']:.2f} | {an['rho_measured']:+.2f} | {ev['rho=0.0']:.1f} / {ev['rho=0.3']:.1f} / {list(ev.values())[2]:.1f} | {mv[ks[0]]:.1f} / {mv[ks[1]]:.1f} / {mv[ks[2]]:.1f} · {mv[ks[3]]:.1f} / {mv[ks[4]]:.1f} / {mv[ks[5]]:.1f} |")
P("\n## Income-only (zero-cost ceiling) mixes — Sharpe by year (23/24/25/26) and worst year; and per-year lines: S2 needed (equal-vol 50:50) vs measured S2 (net / income-only), leverage needed for the sleeve to match the book's vol, and the vol-matched 50:50 mix Sharpe")
P("| arm | seed | income-only mix 0.8:0.2 | 0.7:0.3 | 0.5:0.5 | year | S1 | S2 net / income | ρ net / income | S2 needed @ρ=0 / 0.3 | lev to match vol net / income | vol-matched 50:50 S net / income |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for tag, a in out["arms"].items():
    for s in ("42", "2027"):
        d = a["diversification"][s]; mi = d["mixes_income_only"]; f = lambda k: f"{mi[k]['sharpe']['2023']:.2f}/{mi[k]['sharpe']['2024']:.2f}/{mi[k]['sharpe']['2025']:.2f}/{mi[k]['sharpe']['2026->cut']:.2f} ({mi[k]['worst_year_sharpe']:.2f})"
        for yy, ln in d["lines_by_year"].items():
            P(f"| {tag} | s{s} | {f('0.8:0.2')} | {f('0.7:0.3')} | {f('0.5:0.5')} | {yy} | {ln['S1']:.2f} | {ln['S2_net']:.1f} / {ln['S2_income_only']:.1f} | {ln['rho_net']:+.2f} / {ln['rho_income']:+.2f} | {ln['S2_needed_equal_vol_50_50']['rho=0.0']:.1f} / {ln['S2_needed_equal_vol_50_50']['rho=0.3']:.1f} | {ln['leverage_to_match_book_vol_net']} / {ln['leverage_to_match_book_vol_income']} | {ln['vol_matched_50_50_mix_sharpe_net']:.1f} / {ln['vol_matched_50_50_mix_sharpe_income_only']:.1f} |")
P("\n## Break-even (derived from the 2023→cut means): income_mean / turnover_mean = all-in cost per unit turnover at which the sleeve nets zero under the frozen churn rule (assumed 13.92 = 3.92 perp + 10 spot)")
P("| arm | income mean bps/anchor | turnover/gross | break-even cost bps/unit turnover | turnover cut needed at 13.92 |"); P("|---|---|---|---|---|")
for r_ in out["breakeven_table"]: P(f"| {r_['arm']} | {r_['income_mean_bps']:+.3f} | {r_['turnover_per_gross']:.4f} | {r_['breakeven_allin_cost_bps_per_unit_turnover']:.2f} | {r_['turnover_cut_needed_pct_at_assumed_cost']:.0f}% |")
open(f"{ROOT}/results/sleeve_tables.md", "w").write("\n".join(L) + "\n"); print("\n".join(L)); print("SLEEVE_DONE")
