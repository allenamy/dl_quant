#!/usr/bin/env python
"""judge_t3c.py — T3c re-validation judge (team-lead round 3, 2026-09-06; frozen rule = PREREG_deploy_modulation_2026-09-04 §2/§3 checks as restated by the lead; numbers after rule).
Arms (verbatim health_check device, main-arm form U-PIT·m1·FTRIM·dynamic seat·live fee tiers): T3c KMOD_F10=0.5 (z×(1+0.5·xz(F10)), both chains) | T3 KMOD=0.5,KMOD_L=0.5 (z×(1+0.5·xz(king))) | T3b KMOD_AGREE=0.5 | T2 KTAIL=1; base B0 = knobs off (bitwise = health_check M1_UPIT_{cal}_s{seed}_ccal, logs/check_equiv.log).
UNITS (E-0904-G): g = net_ex/gross_total [bps/anchor per unit gross]; NAV %/yr at L=2 = mean g × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); Sharpe = mean/std(ddof=1)×√2190; maxDD at 2× from Π(1+2g/1e4); ES5 = mean of the anchors below the 5th percentile of g.
Windows: 2023→cut (main; cut 2026-08-10 20:00Z) | 2024→cut | 2025→cut | 2022 | 2023 | 2024 | 2025 | 2026→cut. Paired Δ = g_arm − g_base per anchor; UTC-day-block bootstrap 2000, seed 20260905.
Checks: V1 = per-anchor contribution of the |ret| top-5% names (Σ w·y4·1e4 over the top 5% |y4| names, per gross), arm ≥ base over 2023→cut (2025→cut reported); V2 = six regime cells (σ_fund causal terciles from health_check masks/regime_series.npz + breadth = nsel causal terciles), 2023→cut and 2025→cut: no cell Δ < −0.10;
V4 = fixed seat W3FIX=0.21,0,0.79 Δ (recorded only); V7 = Σ|Δw|/gross_total vs base, median over the last 30 anchors ≤ 35%.
FROZEN JUDGE (prod, both seeds): Δ(2023→cut) CI95 lower > 0 AND yearly Δ(2023, 2024, 2025, 2026→cut) ≥ −0.017 AND Δturnover ≤ +5% AND V1 AND V2 AND V7 ⇒ "re-validated candidate" else "NOT re-validated". Secondary (PREREG_fusion §3): CI lower>0 ∧ yearly ≥ −0.3 ∧ |ES5| not worse by >10% ∧ turnover ≤ +25% ∧ both seeds same sign.
usage: judge_t3c.py → results/judge.json, results/tables.md"""
import numpy as np, json, time, os, hashlib, calendar
ROOT = "/workspace/review_scratch/allweather_trackC/t3c"; HC = "/workspace/review_scratch/health_check"; NB = 2000; SEED = 20260905; APY = 2190; L = 2.0
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600
WIN = {"2023->cut": (T("2023-01-01"), CUT + 1), "2024->cut": (T("2024-01-01"), CUT + 1), "2025->cut": (T("2025-01-01"), CUT + 1), "2022": (T("2022-01-01"), T("2023-01-01")), "2023": (T("2023-01-01"), T("2024-01-01")), "2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1)}
YEARS = ("2023", "2024", "2025", "2026->cut")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
ARMS = [("T3c", "T3c z×(1+0.5·xz(F10))", {"KMOD_F10": 0.5}), ("T3", "T3 z×(1+0.5·xz(king))", {"KMOD": 0.5, "KMOD_L": 0.5}), ("T3b", "T3b z+0.5·|z|·xz(king)", {"KMOD_AGREE": 0.5}), ("T2", "T2 king tail veto", {"KTAIL": 1})]
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(g): nav = np.cumprod(1.0 + L * g / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def es5(g): q = np.percentile(g, 5); return float(g[g <= q].mean())
def boot(r, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 5: return [None, None], None
    s1 = np.bincount(inv, r); c = np.bincount(inv).astype(float); rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); mm = s1[ii].sum(1) / c[ii].sum(1)
    return [r4(np.percentile(mm, 2.5)), r4(np.percentile(mm, 97.5))], r4((mm > 0).mean())
def causal_ter(x, min_hist=300):
    x = np.asarray(x, float); out = np.full(len(x), -1, np.int8)
    for p in range(len(x)):
        h = x[:p]; h = h[np.isfinite(h)]
        if len(h) >= min_hist and np.isfinite(x[p]): q1, q2 = np.percentile(h, [100 / 3, 200 / 3]); out[p] = 0 if x[p] <= q1 else (1 if x[p] <= q2 else 2)
    return out
def load(tag, cal):
    d = "dev" if cal == "log" else "dev_alt"; p = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz"; Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS
    return {"path": p, "sha": hashlib.sha256(open(p, "rb").read()).hexdigest(), "cfg": json.loads(str(Z["config_json"])), "R": Z["d30_n2_c42_rec"], "W": Z["d30_n2_c42_W"].astype(np.float64)}
def levels(g, ts, days, R, turn):
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); gw = g[m]; ci, p = boot(gw, days[m])
        out[wn] = {"n": int(m.sum()), "mean": r4(gw.mean()), "mean_ci95": ci, "sharpe": r4(sharpe(gw)), "maxdd_pct_at_2x": r4(maxdd(gw)), "es5": r4(es5(gw)), "turnover_per_gross": r4(turn[m].mean()), "nav_pct_yr_at_2x": r4(gw.mean() * 6 * 365 * 2 / 1e4 * 100), "negative": bool(gw.mean() < 0)}
    return out
def main():
    print("UNITS CHAIN: g = net_ex/gross_total [bps/anchor per gross]; NAV %/yr at L=2 = mean g × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); maxDD at 2× from Π(1+2g/1e4); Sharpe = mean/std(ddof=1)×√2190; ES5 = mean of anchors ≤ 5th pct", flush=True)
    RS = np.load(f"{HC}/masks/regime_series.npz"); rts = RS["ts"].astype(np.int64); rmap = {int(t): i for i, t in enumerate(rts)}; sig_ter_all = RS["sig_ter"]
    res = {"prereg": "docs/PREREG_deploy_modulation_2026-09-04.md (sha256 674ade3f…, commit c763361) §2/§3 + docs/PREREG_fusion_2026-09-04.md §判据; frozen rule restated by team-lead 2026-09-06", "judge_rule": "prod both seeds: Δ(2023→cut) CI95 lower > 0 AND yearly Δ(2023,2024,2025,2026→cut) ≥ −0.017 AND Δturnover ≤ +5% AND V1 (top-5% |ret| contribution arm ≥ base, 2023→cut) AND V2 (six regime cells, 2023→cut & 2025→cut, no Δ < −0.10) AND V7 (median Σ|Δw|/gross over last 30 anchors ≤ 35%) ⇒ re-validated candidate; else NOT re-validated",
           "secondary_rule_prereg_fusion": "CI lower>0 ∧ yearly ≥ −0.3 ∧ |ES5| not worse >10% ∧ turnover ≤ +25% ∧ seeds same sign", "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "regime_source": f"{HC}/masks/regime_series.npz (σ_fund causal terciles, health_metrics.py definition); breadth = nsel causal terciles over the rec sequence", "cells": {}, "verdict": {}, "v4": {}}
    for cal in ("prod", "log"):
        MT = np.load(f"{ROOT}/{'dev' if cal == 'log' else 'dev_alt'}/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True); mE = MT["E_ts"].astype(np.int64); mrow = {int(t): i for i, t in enumerate(mE)}; Y4 = MT["y4"]
        for s in ("42", "2027"):
            b = load(f"B0_{cal}_s{s}", cal); assert all(b["cfg"].get(k) in (0, 0.0) for k in ("KMOD_F10", "KMOD", "KMOD_AGREE", "KTAIL")) and b["cfg"]["W3FIX"] is None
            R = b["R"]; ts = R[:, 0].astype(np.int64); days = ts // 86400; gt = R[:, C["gross_total"]]; gb = R[:, C["net_ex"]] / gt; tb = R[:, C["turnover"]] / gt
            rows = np.array([mrow[int(t)] for t in ts]); YV = Y4[rows]; YV0 = np.nan_to_num(YV, nan=0.0)
            top = np.zeros_like(YV0, bool)
            for n in range(len(ts)):
                fin = np.isfinite(YV[n]);
                if fin.sum() >= 20: thr = np.percentile(np.abs(YV[n][fin]), 95); top[n] = fin & (np.abs(YV0[n]) >= thr)
            v1b = (np.where(top, b["W"], 0.0) * YV0).sum(1) * 1e4 / gt
            pos = np.array([rmap.get(int(t), -1) for t in ts]); sig_ter = np.where(pos >= 0, sig_ter_all[np.maximum(pos, 0)], -1); br_ter = causal_ter(R[:, C["nsel"]].astype(float))
            Lb = levels(gb, ts, days, R, tb); cell = {"base": {"artifact": b["path"], "sha256": b["sha"], "levels": Lb}, "arms": {}}
            for tag, label, expect in ARMS:
                a = load(f"{tag}_{cal}_s{s}", cal); assert all(a["cfg"].get(k) == v for k, v in expect.items()) and a["cfg"]["FSEED"] == s and a["cfg"]["UMASK_SCOPE"] == "m1" and a["cfg"]["COSTB_JSON"], (tag, a["cfg"])
                Ra = a["R"]; tsa = Ra[:, 0].astype(np.int64); assert np.array_equal(tsa, ts), "anchor sets differ"; gta = Ra[:, C["gross_total"]]; ga = Ra[:, C["net_ex"]] / gta; ta = Ra[:, C["turnover"]] / gta
                La = levels(ga, ts, days, Ra, ta); dl = {}
                for wn, (lo, hi) in WIN.items():
                    m = (ts >= lo) & (ts < hi); dd = ga[m] - gb[m]; ci, p = boot(dd, days[m])
                    dl[wn] = {"delta_mean": r4(dd.mean()), "ci95": ci, "p_gt0": p, "delta_sharpe": r4(La[wn]["sharpe"] - Lb[wn]["sharpe"]), "delta_maxdd_pp": r4(La[wn]["maxdd_pct_at_2x"] - Lb[wn]["maxdd_pct_at_2x"]), "es5_ratio": r4(La[wn]["es5"] / Lb[wn]["es5"]) if Lb[wn]["es5"] else None,
                              "turnover_ratio_pct": r4((ta[m].mean() / tb[m].mean() - 1) * 100), "delta_unit_book_net_ex": r4((Ra[m, C["net_ex"]] - R[m, C["net_ex"]]).mean()), "delta_pnl_per_gross": r4(((Ra[m, C["pnl_ex"]] / gta[m]) - (R[m, C["pnl_ex"]] / gt[m])).mean()), "delta_carry_per_gross": r4(((Ra[m, C["carry_ex"]] / gta[m]) - (R[m, C["carry_ex"]] / gt[m])).mean()), "delta_cost_per_gross": r4(((Ra[m, C["cost_ex"]] / gta[m]) - (R[m, C["cost_ex"]] / gt[m])).mean())}
                v1a = (np.where(top, a["W"], 0.0) * YV0).sum(1) * 1e4 / gta; v1 = {}
                for wn in ("2023->cut", "2025->cut"):
                    m = (ts >= WIN[wn][0]) & (ts < WIN[wn][1]); v1[wn] = {"base": r4(v1b[m].mean()), "arm": r4(v1a[m].mean()), "delta": r4((v1a[m] - v1b[m]).mean())}
                v2 = {}
                for wn in ("2023->cut", "2025->cut"):
                    m = (ts >= WIN[wn][0]) & (ts < WIN[wn][1]); cells = {}
                    for nm, ter in (("sigma_fund", sig_ter), ("breadth", br_ter)):
                        for t_, lab in ((0, "low"), (1, "mid"), (2, "high")):
                            mm = m & (ter == t_); dd = ga[mm] - gb[mm]; ci, p = boot(dd, days[mm]) if mm.sum() >= 12 else ([None, None], None)
                            cells[f"{nm}/{lab}"] = {"n": int(mm.sum()), "delta": r4(dd.mean()) if mm.sum() else None, "ci95": ci, "base_mean": r4(gb[mm].mean()) if mm.sum() else None}
                    v2[wn] = cells
                dw = np.abs(a["W"] - b["W"]).sum(1) / gt; v7 = {"median_last30": r4(np.median(dw[-30:])), "median_2023cut": r4(np.median(dw[(ts >= WIN['2023->cut'][0]) & (ts < CUT)])), "p95_last30": r4(np.percentile(dw[-30:], 95))}
                cell["arms"][tag] = {"label": label, "artifact": a["path"], "sha256": a["sha"], "levels": La, "delta_vs_base": dl, "V1": v1, "V2": v2, "V7": v7}
            res["cells"][f"{cal}/s{s}"] = cell
    for s in ("42", "2027"):   # V4 fixed seat
        b = load(f"V4B0_prod_s{s}", "prod"); a = load(f"V4T3c_prod_s{s}", "prod"); assert b["cfg"]["W3FIX"] == "0.21,0,0.79" and a["cfg"]["W3FIX"] == "0.21,0,0.79" and a["cfg"]["KMOD_F10"] == 0.5
        ts = b["R"][:, 0].astype(np.int64); assert np.array_equal(ts, a["R"][:, 0].astype(np.int64)); days = ts // 86400; gb = b["R"][:, C["net_ex"]] / b["R"][:, C["gross_total"]]; ga = a["R"][:, C["net_ex"]] / a["R"][:, C["gross_total"]]
        res["v4"][f"prod/s{s}"] = {}
        for wn in ("2023->cut", "2024->cut", "2025->cut"):
            m = (ts >= WIN[wn][0]) & (ts < WIN[wn][1]); dd = ga[m] - gb[m]; ci, p = boot(dd, days[m]); res["v4"][f"prod/s{s}"][wn] = {"delta_mean": r4(dd.mean()), "ci95": ci, "base_mean": r4(gb[m].mean()), "arm_mean": r4(ga[m].mean())}
    for tag, label, _ in ARMS:
        per = {}
        for s in ("42", "2027"):
            e = res["cells"][f"prod/s{s}"]["arms"][tag]; dl = e["delta_vs_base"]
            v2min = min(c["delta"] for wn in e["V2"] for c in e["V2"][wn].values() if c["delta"] is not None)
            per[s] = {"d_main": dl["2023->cut"]["delta_mean"], "ci_lo": dl["2023->cut"]["ci95"][0], "ci_hi": dl["2023->cut"]["ci95"][1], "years": {y: dl[y]["delta_mean"] for y in YEARS}, "min_year": min(dl[y]["delta_mean"] for y in YEARS), "turn_pct": dl["2023->cut"]["turnover_ratio_pct"], "es5_ratio": dl["2023->cut"]["es5_ratio"],
                      "V1_delta": e["V1"]["2023->cut"]["delta"], "V2_min_cell_delta": r4(v2min), "V7_median_last30": e["V7"]["median_last30"],
                      "pass_ci": dl["2023->cut"]["ci95"][0] > 0, "pass_years": all(dl[y]["delta_mean"] >= -0.017 for y in YEARS), "pass_turn": dl["2023->cut"]["turnover_ratio_pct"] <= 5.0, "pass_V1": e["V1"]["2023->cut"]["delta"] >= 0, "pass_V2": v2min >= -0.10, "pass_V7": e["V7"]["median_last30"] <= 0.35,
                      "fusion_pass_years03": all(dl[y]["delta_mean"] >= -0.3 for y in YEARS), "fusion_pass_es5": (dl["2023->cut"]["es5_ratio"] is not None and dl["2023->cut"]["es5_ratio"] <= 1.10), "fusion_pass_turn25": dl["2023->cut"]["turnover_ratio_pct"] <= 25.0}
        allp = all(per[s]["pass_ci"] and per[s]["pass_years"] and per[s]["pass_turn"] and per[s]["pass_V1"] and per[s]["pass_V2"] and per[s]["pass_V7"] for s in per)
        same = np.sign(per["42"]["d_main"]) == np.sign(per["2027"]["d_main"])
        fus = all(per[s]["pass_ci"] and per[s]["fusion_pass_years03"] and per[s]["fusion_pass_es5"] and per[s]["fusion_pass_turn25"] for s in per) and bool(same)
        fails = sorted(set(k for s in per for k in ("ci", "years", "turn", "V1", "V2", "V7") if not per[s][f"pass_{k}"]))
        res["verdict"][tag] = {"label": label, "per_seed": per, "seeds_same_sign": bool(same), "verdict": "re-validated candidate" if allp else "NOT re-validated", "failed_checks": fails, "secondary_prereg_fusion_rule": "pass" if fus else "fail"}
    json.dump(res, open(f"{ROOT}/results/judge.json", "w"), indent=1, ensure_ascii=False)
    Lm = []; P = Lm.append
    P("## t3c_revalidation · levels (g = bps/anchor per gross; S = Sharpe; DD = 2× maxDD; ES5 per gross; turn = turnover/gross)")
    P("| cell | arm | 2022 g S | 2023 g S | 2024 g S | 2025 g S | 2026→cut g S | **2023→cut g [CI] S DD ES5 turn** | 2024→cut g S | 2025→cut g S |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        f = lambda Lx, w: f"{Lx[w]['mean']:+.3f} S{Lx[w]['sharpe']:.2f}"; M = lambda Lx: f"**{Lx['2023->cut']['mean']:+.3f} [{Lx['2023->cut']['mean_ci95'][0]:+.2f},{Lx['2023->cut']['mean_ci95'][1]:+.2f}] S{Lx['2023->cut']['sharpe']:.2f} DD{Lx['2023->cut']['maxdd_pct_at_2x']:.1f}% ES5 {Lx['2023->cut']['es5']:.1f} turn {Lx['2023->cut']['turnover_per_gross']:.4f}**"
        Lb = cell["base"]["levels"]; P(f"| {cn} | B0 base | {f(Lb,'2022')} | {f(Lb,'2023')} | {f(Lb,'2024')} | {f(Lb,'2025')} | {f(Lb,'2026->cut')} | {M(Lb)} | {f(Lb,'2024->cut')} | {f(Lb,'2025->cut')} |")
        for tag, label, _ in ARMS:
            La = cell["arms"][tag]["levels"]; P(f"| {cn} | {label} | {f(La,'2022')} | {f(La,'2023')} | {f(La,'2024')} | {f(La,'2025')} | {f(La,'2026->cut')} | {M(La)} | {f(La,'2024->cut')} | {f(La,'2025->cut')} |")
    P("\n## paired Δ vs B0 (bps/anchor per gross; UTC-day-block bootstrap CI95; Δturn% / ES5 ratio / ΔDD over 2023→cut; Δpnl/Δcarry/Δcost per gross 2023→cut)")
    P("| cell | arm | Δ2022 | Δ2023 | Δ2024 | Δ2025 | Δ2026→cut | **Δ2023→cut [CI]** | Δ2024→cut [CI] | Δ2025→cut [CI] | Δturn | ES5 ratio | ΔDD pp | Δpnl / Δcarry / Δcost |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for tag, label, _ in ARMS:
            d = cell["arms"][tag]["delta_vs_base"]; f = lambda w: f"{d[w]['delta_mean']:+.3f}"; g_ = lambda w: f"{d[w]['delta_mean']:+.3f} [{d[w]['ci95'][0]:+.3f},{d[w]['ci95'][1]:+.3f}]"
            P(f"| {cn} | {label} | {f('2022')} | {f('2023')} | {f('2024')} | {f('2025')} | {f('2026->cut')} | **{g_('2023->cut')}** (unit-book {d['2023->cut']['delta_unit_book_net_ex']:+.3f}) | {g_('2024->cut')} | {g_('2025->cut')} | {d['2023->cut']['turnover_ratio_pct']:+.1f}% | {d['2023->cut']['es5_ratio']:.3f} | {d['2023->cut']['delta_maxdd_pp']:+.1f} | {d['2023->cut']['delta_pnl_per_gross']:+.3f} / {d['2023->cut']['delta_carry_per_gross']:+.3f} / {d['2023->cut']['delta_cost_per_gross']:+.3f} |")
    P("\n## V1 (top-5% |ret| names' contribution per gross, base → arm, Δ) · V7 (Σ|Δw|/gross: median last 30 anchors / median 2023→cut / p95 last 30) · V2 (six regime cells Δ, 2023→cut | 2025→cut)")
    P("| cell | arm | V1 2023→cut | V1 2025→cut | V7 | V2 2023→cut σ_fund L/M/H · breadth L/M/H | V2 2025→cut σ_fund L/M/H · breadth L/M/H |")
    P("|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for tag, label, _ in ARMS:
            e = cell["arms"][tag]; v1 = e["V1"]; v7 = e["V7"]
            c2 = lambda wn: " · ".join(f"{e['V2'][wn][k]['delta']:+.3f}" if e['V2'][wn][k]['delta'] is not None else "—" for k in ("sigma_fund/low", "sigma_fund/mid", "sigma_fund/high")) + " · " + " · ".join(f"{e['V2'][wn][k]['delta']:+.3f}" if e['V2'][wn][k]['delta'] is not None else "—" for k in ("breadth/low", "breadth/mid", "breadth/high"))
            P(f"| {cn} | {label} | {v1['2023->cut']['base']:+.3f} → {v1['2023->cut']['arm']:+.3f} ({v1['2023->cut']['delta']:+.3f}) | {v1['2025->cut']['base']:+.3f} → {v1['2025->cut']['arm']:+.3f} ({v1['2025->cut']['delta']:+.3f}) | {v7['median_last30']:.3f} / {v7['median_2023cut']:.3f} / {v7['p95_last30']:.3f} | {c2('2023->cut')} | {c2('2025->cut')} |")
    P("\n## V4 fixed seat 0.21 (W3FIX) · T3c vs base, prod (recorded only; expected negative = F10 counted linearly and multiplicatively)")
    P("| cell | 2023→cut Δ [CI] (base → arm) | 2024→cut Δ [CI] | 2025→cut Δ [CI] |"); P("|---|---|---|---|")
    for cn, v in res["v4"].items():
        f = lambda w: f"{v[w]['delta_mean']:+.3f} [{v[w]['ci95'][0]:+.3f},{v[w]['ci95'][1]:+.3f}] ({v[w]['base_mean']:+.3f} → {v[w]['arm_mean']:+.3f})"
        P(f"| {cn} | {f('2023->cut')} | {f('2024->cut')} | {f('2025->cut')} |")
    P("\n## frozen verdict (prod, both seeds): Δ23→cut CI lo > 0 ∧ years ≥ −0.017 ∧ Δturn ≤ +5% ∧ V1 ∧ V2 (no cell < −0.10) ∧ V7 (≤ 35%)")
    P("| arm | s42: Δ [CI] / min-year / Δturn / V1 Δ / V2 min / V7 | s2027 | failed checks | verdict | PREREG_fusion rule |"); P("|---|---|---|---|---|---|")
    for tag, v in res["verdict"].items():
        f = lambda s: f"{v['per_seed'][s]['d_main']:+.3f} [{v['per_seed'][s]['ci_lo']:+.3f},{v['per_seed'][s]['ci_hi']:+.3f}] / {v['per_seed'][s]['min_year']:+.3f} / {v['per_seed'][s]['turn_pct']:+.1f}% / {v['per_seed'][s]['V1_delta']:+.3f} / {v['per_seed'][s]['V2_min_cell_delta']:+.3f} / {v['per_seed'][s]['V7_median_last30']:.3f}"
        P(f"| {v['label']} | {f('42')} | {f('2027')} | {', '.join(v['failed_checks']) or '—'} | **{v['verdict']}** | {v['secondary_prereg_fusion_rule']} |")
    open(f"{ROOT}/results/tables.md", "w").write("\n".join(Lm) + "\n"); print("\n".join(Lm)); print("JUDGE_T3C_DONE", flush=True)
if __name__ == "__main__": main()
