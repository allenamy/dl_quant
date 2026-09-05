#!/usr/bin/env python
"""judge_c1.py — Track C · C1 listing-age tilt judge (PREREG_allweather_programme_2026-09-05 §3 Track C, C1; frozen before numbers).
Reads only Track C artifacts (AGEW=0 base = bitwise identical to health_check M1_UPIT_{cal}_s{seed}_ccal, receipt logs/check_equiv.log) + the dose arms.
UNITS CHAIN (E-0904-G, printed at run time): rec net_ex = bps/anchor earned by the unit replay book of gross gross_total ⇒ g = net_ex/gross_total [bps/anchor per unit gross]
  ⇒ NAV %/yr at L=2 (arithmetic) = mean g × 6 × 365 × 2 / 1e4 × 100 = mean g × 43.8; maxDD at 2× from NAV = Π(1 + 2g/1e4); anchor Sharpe = mean/std(ddof=1) × √2190 (L-invariant).
Windows: 2024 | 2025 | 2026→cut (cut = 2026-08-10 20:00Z, last finite F10 row) | 2024→26 | 2025→26. Paired Δ = g_arm − g_base per anchor (anchor sets asserted equal);
UTC-day-block bootstrap of the window mean, 2000 resamples, seed 20260905 (same as health_metrics.py). Turnover = rec turnover / gross_total (per gross); Δturnover% over 2024→26.
Young-name shares from the saved d30_n2_c42_W weight rows + the device's own listing receipts (trackc_age_first / trackc_meta_ts) — the YOUNG matrix is rebuilt from those, not re-derived.
FROZEN JUDGE (prod caliber, both seeds): candidate ⇔ Δ(2024→26) CI95 lower > 0 AND Δ(2025) ≥ 0 AND Δturnover ≤ +15% AND sign(Δ 2024→26) equal across seeds.
usage: judge_c1.py  → results/c1_judge.json, results/c1_tables.md (paths under ROOT)."""
import numpy as np, json, time, os, sys, hashlib, calendar
ROOT = "/workspace/review_scratch/allweather_trackC"
NB = 2000; SEED = 20260905; APY = 2190; L = 2.0; AGE_DAYS = 90
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(CUT)) == "2026-08-10 20:00"
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1)}
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
DOSES = ["0", "05", "10", "20"]; DOSE_VAL = {"0": 0.0, "05": 0.5, "10": 1.0, "20": 2.0}
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(g):
    nav = np.cumprod(1.0 + L * g / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def boot(r, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, r); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd))
    m = s1[idx].sum(1) / c[idx].sum(1)
    return [r4(np.percentile(m, 2.5)), r4(np.percentile(m, 97.5))], r4((m > 0).mean())
def load(tag, cal):
    d = "dev" if cal == "log" else "dev_alt"; p = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz"
    Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS
    cfg = json.loads(str(Z["config_json"])); R = Z["d30_n2_c42_rec"]; W = Z["d30_n2_c42_W"]
    return {"path": p, "sha": hashlib.sha256(open(p, "rb").read()).hexdigest(), "cfg": cfg, "R": R, "W": W, "age_first": Z["trackc_age_first"].astype(np.int64), "meta_ts": Z["trackc_meta_ts"].astype(np.int64), "young_count": Z["trackc_young_count"]}
def young_matrix(age_first, meta_ts):
    Y = np.zeros((len(meta_ts), len(age_first)), bool)
    for k, f in enumerate(age_first):
        if f > 0: Y[f:, k] = (meta_ts[f:] - meta_ts[f]) < AGE_DAYS * 86400
    return Y
def qv24_matrix(cal):
    d = "dev" if cal == "log" else "dev_alt"; M = np.load(f"{ROOT}/{d}/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True)
    return M["E_ts"].astype(np.int64), np.expm1(np.clip(np.nan_to_num(M["qvk"], nan=0.0), 0, 30)) * 288.0   # device: qv4h = expm1(qvk)*48 ⇒ expm1(qvk) = 5-min quote volume ⇒ ×288 = 24h USDT
def metrics(R, YM, qv24, meta_row):
    ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]; days = ts // 86400; tpg = R[:, C["turnover"]] / R[:, C["gross_total"]]
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); gw = g[m]; ci, p = boot(gw, days[m])
        out[wn] = {"n": int(m.sum()), "mean_bps_anchor_per_gross": r4(gw.mean()), "mean_ci95": ci, "sharpe_anchor": r4(sharpe(gw)), "maxdd_pct_at_2x": r4(maxdd(gw)), "nav_pct_yr_at_2x_arith": r4(gw.mean() * 6 * 365 * 2 / 1e4 * 100),
                   "turnover_per_gross": r4(tpg[m].mean()), "gross_total": r4(R[m, C["gross_total"]].mean()), "nsel": r4(R[m, C["nsel"]].mean()), "w3_king": r4(R[m, C["w3_king"]].mean()), "cost_per_gross": r4((R[m, C["cost_ex"]] / R[m, C["gross_total"]]).mean()), "carry_per_gross": r4((R[m, C["carry_ex"]] / R[m, C["gross_total"]]).mean())}
    return out, g, ts, days, tpg
def young_shares(R, W, YM, qv24, meta_row):
    ts = R[:, 0].astype(np.int64); rows = np.array([meta_row[int(t)] for t in ts]); out = {}
    absW = np.abs(W.astype(np.float64)); Y = YM[rows]; Q = qv24[rows]
    held = absW > 1e-12
    gs = (absW * Y).sum(1) / np.maximum(absW.sum(1), 1e-12)                       # young share of gross
    vs = (Q * (held & Y)).sum(1) / np.maximum((Q * held).sum(1), 1e-12)          # young share of 24h quote volume among held names
    with np.errstate(all="ignore"):
        part = np.where(Q > 0, absW / np.maximum(Q, 1.0) * 1e6 * 100, np.nan)   # % of the name's 24h quote volume traded-through per $1M of unit gross (position size, not turnover)
    py = np.array([np.nanmean(np.where(held[i] & Y[i], part[i], np.nan)) if (held[i] & Y[i]).any() else np.nan for i in range(len(ts))])
    po = np.array([np.nanmean(np.where(held[i] & ~Y[i], part[i], np.nan)) if (held[i] & ~Y[i]).any() else np.nan for i in range(len(ts))])
    ny = (held & Y).sum(1); nh = held.sum(1)
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        out[wn] = {"young_share_of_gross": r4(gs[m].mean()), "young_share_of_24h_quote_volume_held": r4(vs[m].mean()), "young_names_held": r4(ny[m].mean()), "names_held": r4(nh[m].mean()),
                   "position_pct_of_24h_vol_per_1M_gross_young": r4(np.nanmean(py[m])), "position_pct_of_24h_vol_per_1M_gross_old": r4(np.nanmean(po[m]))}
    return out
def main():
    print("UNITS CHAIN: g = net_ex/gross_total [bps/anchor per gross]; NAV %/yr at L=2 = mean g × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); maxDD at 2× from Π(1+2g/1e4); Sharpe = mean/std(ddof=1)×√2190", flush=True)
    res = {"prereg": "docs/PREREG_allweather_programme_2026-09-05.md §3 Track C C1 (sha256 8a02895c…, commit 5075b36)", "judge_rule": "candidate ⇔ Δ(2024→26) CI95 lower > 0 AND Δ(2025) ≥ 0 AND Δturnover(2024→26) ≤ +15% AND sign(Δ 2024→26) equal across seeds 42/2027; prod caliber primary, log secondary (reported, not judged)",
           "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "age_days": AGE_DAYS, "cells": {}, "verdict": {}}
    devsha = set()
    for cal in ("prod", "log"):
        mts, qv24 = qv24_matrix(cal); meta_row = {int(t): i for i, t in enumerate(mts)}
        base = load(f"A0_{cal}_s42", cal); YM = young_matrix(base["age_first"], base["meta_ts"]); assert np.array_equal(YM.sum(1).astype(np.int32), base["young_count"]), "young receipt mismatch"
        assert np.array_equal(base["meta_ts"], mts)
        for s in ("42", "2027"):
            arms = {d: load(f"A{d}_{cal}_s{s}", cal) for d in DOSES}
            for d, a in arms.items():
                assert a["cfg"]["AGEW"] == DOSE_VAL[d] and a["cfg"]["FSEED"] == s and a["cfg"]["UMASK_SCOPE"] == "m1" and a["cfg"]["COSTB_JSON"] and a["cfg"]["PHI"] == 0.45 and a["cfg"]["FTRIM"] == "zero" and a["cfg"]["LEGS"] == "101", (d, a["cfg"])
                assert np.array_equal(a["age_first"], base["age_first"]), "listing receipts differ across arms"; devsha.add(a["cfg"]["TRACKC"]["device_sha256"])
            b = arms["0"]; mb, gb, tsb, daysb, tpb = metrics(b["R"], YM, qv24, meta_row)
            cell = {"base_artifact": b["path"], "base_sha256": b["sha"], "arms": {}}
            for d in DOSES:
                a = arms[d]; ma, ga, tsa, daysa, tpa = metrics(a["R"], YM, qv24, meta_row); assert np.array_equal(tsa, tsb), "anchor sets differ"
                ys = young_shares(a["R"], a["W"], YM, qv24, meta_row)
                dl = {}
                for wn, (lo, hi) in WIN.items():
                    m = (tsa >= lo) & (tsa < hi); dd = ga[m] - gb[m]; ci, p = boot(dd, daysa[m])
                    dl[wn] = {"delta_mean": r4(dd.mean()), "ci95": ci, "p_gt0": p, "delta_sharpe": r4(sharpe(ga[m]) - sharpe(gb[m])), "delta_maxdd_pct_at_2x": r4(maxdd(ga[m]) - maxdd(gb[m])),
                              "turnover_ratio_pct": r4((tpa[m].mean() / tpb[m].mean() - 1) * 100)}
                cell["arms"][f"AGEW={DOSE_VAL[d]}"] = {"artifact": a["path"], "sha256": a["sha"], "levels": ma, "delta_vs_base": dl, "young": ys}
            res["cells"][f"{cal}/s{s}"] = cell
    res["device_sha256_set"] = sorted(devsha); assert len(devsha) == 1, devsha
    for d in DOSES[1:]:
        k = f"AGEW={DOSE_VAL[d]}"; per = {}
        for s in ("42", "2027"):
            dl = res["cells"][f"prod/s{s}"]["arms"][k]["delta_vs_base"]
            per[s] = {"d2426": dl["2024->26"]["delta_mean"], "ci_lo_2426": dl["2024->26"]["ci95"][0], "d2025": dl["2025"]["delta_mean"], "turn_pct": dl["2024->26"]["turnover_ratio_pct"],
                      "pass_ci": dl["2024->26"]["ci95"][0] > 0, "pass_2025": dl["2025"]["delta_mean"] >= 0, "pass_turn": dl["2024->26"]["turnover_ratio_pct"] <= 15.0}
        same_sign = np.sign(per["42"]["d2426"]) == np.sign(per["2027"]["d2426"])
        cand = all(per[s]["pass_ci"] and per[s]["pass_2025"] and per[s]["pass_turn"] for s in per) and bool(same_sign)
        rej = any(res["cells"][f"prod/s{s}"]["arms"][k]["delta_vs_base"]["2024->26"]["ci95"][1] < 0 for s in per)
        res["verdict"][k] = {"per_seed": per, "same_sign_2426": bool(same_sign), "verdict": "CANDIDATE" if cand else ("REJECT (2024→26 CI95 upper < 0 in ≥1 seed; informational — the frozen rule only defines candidate)" if rej else "NOT CANDIDATE")}
    json.dump(res, open(f"{ROOT}/results/c1_judge.json", "w"), indent=1, ensure_ascii=False)
    # tables
    Lm = []; P = Lm.append
    P("## C1 · listing-age tilt (AGEW) — levels per cell (g = bps/anchor per gross; NAV%/yr@2× = g×43.8; maxDD at 2×; turnover per gross)")
    P("| cell | arm | 2024 g [CI] S DD | 2025 g [CI] S DD | 2026→cut g [CI] S DD | 2024→26 g [CI] S DD turn | 2025→26 g [CI] S DD |")
    P("|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for an, a in cell["arms"].items():
            f = lambda w: f"{a['levels'][w]['mean_bps_anchor_per_gross']:+.3f} [{a['levels'][w]['mean_ci95'][0]:+.2f},{a['levels'][w]['mean_ci95'][1]:+.2f}] S{a['levels'][w]['sharpe_anchor']:.2f} DD{a['levels'][w]['maxdd_pct_at_2x']:.1f}%"
            P(f"| {cn} | {an} | {f('2024')} | {f('2025')} | {f('2026->cut')} | {f('2024->26')} turn {a['levels']['2024->26']['turnover_per_gross']:.4f} | {f('2025->26')} |")
    P("\n## C1 · paired Δ vs AGEW=0 (bps/anchor per gross; UTC-day-block bootstrap CI95; Δturnover% over 2024→26)")
    P("| cell | arm | Δ2024 | Δ2025 | Δ2026→cut | **Δ2024→26** | Δ2025→26 | Δturn% | ΔSharpe 24→26 | ΔmaxDD@2× 24→26 |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for an, a in cell["arms"].items():
            if an == "AGEW=0.0": continue
            d = a["delta_vs_base"]; f = lambda w: f"{d[w]['delta_mean']:+.3f} [{d[w]['ci95'][0]:+.3f},{d[w]['ci95'][1]:+.3f}]"
            P(f"| {cn} | {an} | {f('2024')} | {f('2025')} | {f('2026->cut')} | **{f('2024->26')}** | {f('2025->26')} | {d['2024->26']['turnover_ratio_pct']:+.1f}% | {d['2024->26']['delta_sharpe']:+.2f} | {d['2024->26']['delta_maxdd_pct_at_2x']:+.1f}pp |")
    P("\n## C1 · young-name share (age < 90 d) of gross and of 24h quote volume among held names; position size as % of a name's 24h quote volume per $1M unit gross")
    P("| cell | arm | window | young share of gross | young share of 24h vol (held) | young held / held | pos %24h-vol per $1M: young / old |")
    P("|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for an, a in cell["arms"].items():
            for w in ("2024", "2025", "2026->cut", "2024->26"):
                y = a["young"][w]; P(f"| {cn} | {an} | {w} | {y['young_share_of_gross']:.3f} | {y['young_share_of_24h_quote_volume_held']:.3f} | {y['young_names_held']:.0f} / {y['names_held']:.0f} | {y['position_pct_of_24h_vol_per_1M_gross_young']:.3f} / {y['position_pct_of_24h_vol_per_1M_gross_old']:.3f} |")
    P("\n## C1 · frozen verdict (prod, seeds 42/2027)")
    P("| arm | s42 Δ24→26 [CI lo] / Δ2025 / Δturn | s2027 Δ24→26 [CI lo] / Δ2025 / Δturn | same sign | verdict |")
    P("|---|---|---|---|---|")
    for k, v in res["verdict"].items():
        f = lambda s: f"{v['per_seed'][s]['d2426']:+.3f} [{v['per_seed'][s]['ci_lo_2426']:+.3f}] / {v['per_seed'][s]['d2025']:+.3f} / {v['per_seed'][s]['turn_pct']:+.1f}%"
        P(f"| {k} | {f('42')} | {f('2027')} | {v['same_sign_2426']} | **{v['verdict']}** |")
    open(f"{ROOT}/results/c1_tables.md", "w").write("\n".join(Lm) + "\n"); print("\n".join(Lm)); print("JUDGE_C1_DONE", flush=True)
if __name__ == "__main__": main()
