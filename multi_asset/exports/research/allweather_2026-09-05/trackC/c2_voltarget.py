#!/usr/bin/env python
"""c2_voltarget.py — Track C · C2 down-only volatility target (insurance form), paper overlay on the baseline per-anchor per-gross net series
(PREREG_allweather_programme_2026-09-05 §3 Track C C2; frozen before numbers). Same method family as the premium-sleeve budget test: no device rerun, overlay on the archived series.
Baseline = health_check main arm M1_UPIT_{cal}_s{seed}_ccal (read-only originals; prod = primary, log = secondary), g_t = net_ex/gross_total [bps/anchor per unit gross].
  σ̂_t = std(ddof=1) of g over the trailing 42 anchors ending at t−1 (causal; NaN ⇒ gate 1)
  σ*_t = quantile q of σ̂ over the prior 500 anchors [t−500, t−1] (causal, excludes t; requires the full 500 finite ⇒ gating starts ≈ anchor 542 = 2022-05; q ∈ {0.50, 0.65, 0.80})
  insurance gate g_t = min(1, σ*_t/σ̂_t);  symmetric control gate = clip(σ*_t/σ̂_t, 0.5, 1.5)  (control: reproduce the known negative direction of symmetric vol-targeting)
  overlay net_t = gate_t·g_t − COST·|gate_t − gate_{t−1}|, COST = 3.92 bps per unit of (full) gross moved (lead's frozen figure; gate_{−1} = 1); a no-cost variant is stored for information only.
UNITS: overlay net is per unit of FULL gross ⇒ NAV return at L=2 = 2×net (the executor would hold gate×2×NAV); NAV %/yr = mean × 6 × 365 × 2 / 1e4 × 100; maxDD at 2× from Π(1+2·net/1e4); Sharpe = mean/std(ddof=1)×√2190.
Windows: 2024 | 2025 | 2026→cut (2026-08-10 20:00Z) | 2024→26 | 2025→26. Worst-year Sharpe = min over {2024, 2025, 2026→cut}.
FROZEN JUDGE (maximin; prod, both seeds): candidate ⇔ worst-year Sharpe rises ≥ +0.3 AND 2024→26 Sharpe falls ≤ 0.1 AND maxDD(2024→26 @2×) falls.
usage: c2_voltarget.py → c2/c2_voltarget.json, c2/c2_tables.md"""
import numpy as np, json, time, os, hashlib, calendar
ROOT = "/workspace/review_scratch/allweather_trackC"; HC = "/workspace/review_scratch/health_check"
NB = 2000; SEED = 20260905; APY = 2190; L = 2.0; NSIG = 42; NQ = 500; COST = 3.92; QS = (0.50, 0.65, 0.80)
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1)}
YEARS = ("2024", "2025", "2026->cut")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(g):
    nav = np.cumprod(1.0 + L * g / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def boot(r, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud); s1 = np.bincount(inv, r); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd)); m = s1[idx].sum(1) / c[idx].sum(1)
    return [r4(np.percentile(m, 2.5)), r4(np.percentile(m, 97.5))], r4((m > 0).mean())
def load(cal, s):
    d = "dev" if cal == "log" else "dev_alt"; p = f"{HC}/{d}/probe_artifacts/w10_ablation_series_M1_UPIT_{cal}_s{s}_ccal.npz"
    Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS; R = Z["d30_n2_c42_rec"]; cfg = json.loads(str(Z["config_json"]))
    assert cfg["UMASK_SCOPE"] == "m1" and cfg["COSTB_JSON"] and cfg["PHI"] == 0.45 and cfg["FSEED"] == s
    return p, hashlib.sha256(open(p, "rb").read()).hexdigest(), R[:, 0].astype(np.int64), R[:, C["net_ex"]] / R[:, C["gross_total"]]
def gates(g, q):
    n = len(g); sig = np.full(n, np.nan); star = np.full(n, np.nan)
    for p in range(NSIG, n): sig[p] = g[p - NSIG:p].std(ddof=1)
    for p in range(NSIG + NQ, n):
        h = sig[p - NQ:p]
        if np.isfinite(h).all(): star[p] = np.quantile(h, q)
    with np.errstate(all="ignore"): ratio = star / sig
    ok = np.isfinite(ratio)
    ins = np.where(ok, np.minimum(1.0, ratio), 1.0); sym = np.where(ok, np.clip(ratio, 0.5, 1.5), 1.0)
    return ins, sym, sig, star
def overlay(g, gate, cost=COST):
    prev = np.concatenate([[1.0], gate[:-1]]); return gate * g - cost * np.abs(gate - prev), cost * np.abs(gate - prev)
def stats(x, ts, days, gate=None, drag=None):
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); xw = x[m]; ci, p = boot(xw, days[m])
        d = {"n": int(m.sum()), "mean": r4(xw.mean()), "mean_ci95": ci, "sharpe": r4(sharpe(xw)), "maxdd_pct_at_2x": r4(maxdd(xw)), "nav_pct_yr_at_2x_arith": r4(xw.mean() * 6 * 365 * 2 / 1e4 * 100), "std": r4(xw.std(ddof=1))}
        if gate is not None: d.update({"share_gate_lt1": r4((gate[m] < 1 - 1e-12).mean()), "share_gate_gt1": r4((gate[m] > 1 + 1e-12).mean()), "mean_gate": r4(gate[m].mean()), "min_gate": r4(gate[m].min()), "cost_drag_bps_anchor": r4(drag[m].mean())})
        out[wn] = d
    out["worst_year_sharpe"] = r4(min(out[y]["sharpe"] for y in YEARS)); out["worst_year"] = min(YEARS, key=lambda y: out[y]["sharpe"])
    return out
def main():
    print("UNITS CHAIN: overlay net per unit FULL gross [bps/anchor]; NAV %/yr at L=2 = mean × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); maxDD at 2× from Π(1+2·net/1e4); Sharpe = mean/std(ddof=1)×√2190", flush=True)
    res = {"prereg": "docs/PREREG_allweather_programme_2026-09-05.md §3 Track C C2 (sha256 8a02895c…, commit 5075b36)", "definition": {"sigma_window": NSIG, "quantile_window": NQ, "quantiles": QS, "cost_bps_per_unit_gross_moved": COST, "gate_ins": "min(1, σ*/σ̂)", "gate_sym": "clip(σ*/σ̂, 0.5, 1.5)"},
           "judge_rule": "candidate ⇔ worst-year Sharpe rises ≥ +0.3 AND 2024→26 Sharpe falls ≤ 0.1 AND maxDD(2024→26 @2×) falls; prod caliber, both seeds", "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "cells": {}, "verdict": {}}
    for cal in ("prod", "log"):
        for s in ("42", "2027"):
            p, sha, ts, g = load(cal, s); days = ts // 86400; base = stats(g, ts, days)
            cell = {"base_artifact": p, "base_sha256": sha, "n_anchors": int(len(ts)), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[0]))), "base": base, "arms": {}}
            for q in QS:
                ins, sym, sig, star = gates(g, q); gate_start = int(np.argmax(np.isfinite(star))) if np.isfinite(star).any() else -1
                for nm, gt in (("ins", ins), ("sym", sym)):
                    x, drag = overlay(g, gt); x0, _ = overlay(g, gt, 0.0); st = stats(x, ts, days, gt, drag); st0 = stats(x0, ts, days)
                    dl = {}
                    for wn, (lo, hi) in WIN.items():
                        m = (ts >= lo) & (ts < hi); dd = x[m] - g[m]; ci, pp = boot(dd, days[m])
                        dl[wn] = {"delta_mean": r4(dd.mean()), "ci95": ci, "p_gt0": pp, "delta_sharpe": r4(st[wn]["sharpe"] - base[wn]["sharpe"]), "delta_maxdd_pp": r4(st[wn]["maxdd_pct_at_2x"] - base[wn]["maxdd_pct_at_2x"]), "net_ratio_pct": r4((x[m].mean() / g[m].mean() - 1) * 100) if abs(g[m].mean()) > 1e-9 else None}
                    cell["arms"][f"{nm}_q{q:.2f}"] = {"form": nm, "q": q, "gate_start": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[gate_start]))) if gate_start >= 0 else None, "levels": st, "levels_no_cost": {w: {"mean": st0[w]["mean"], "sharpe": st0[w]["sharpe"]} for w in WIN}, "delta_vs_base": dl,
                                                     "delta_worst_year_sharpe": r4(st["worst_year_sharpe"] - base["worst_year_sharpe"]), "delta_sharpe_2426": r4(st["2024->26"]["sharpe"] - base["2024->26"]["sharpe"]), "delta_maxdd_2426_pp": r4(st["2024->26"]["maxdd_pct_at_2x"] - base["2024->26"]["maxdd_pct_at_2x"])}
            res["cells"][f"{cal}/s{s}"] = cell
    for q in QS:
        for nm in ("ins", "sym"):
            k = f"{nm}_q{q:.2f}"; per = {}
            for s in ("42", "2027"):
                a = res["cells"][f"prod/s{s}"]["arms"][k]
                per[s] = {"d_worst_year_sharpe": a["delta_worst_year_sharpe"], "d_sharpe_2426": a["delta_sharpe_2426"], "d_maxdd_2426_pp": a["delta_maxdd_2426_pp"], "pass_worst": a["delta_worst_year_sharpe"] >= 0.3, "pass_full": a["delta_sharpe_2426"] >= -0.1, "pass_dd": a["delta_maxdd_2426_pp"] < 0}
            res["verdict"][k] = {"per_seed": per, "verdict": "CANDIDATE" if all(per[s]["pass_worst"] and per[s]["pass_full"] and per[s]["pass_dd"] for s in per) else "NOT CANDIDATE", "role": "insurance arm (judged)" if nm == "ins" else "symmetric control (reported only)"}
    json.dump(res, open(f"{ROOT}/c2/c2_voltarget.json", "w"), indent=1, ensure_ascii=False)
    Lm = []; P = Lm.append
    P("## C2 · down-only vol target (insurance) vs symmetric control — levels (net = bps/anchor per full gross; S = anchor Sharpe; DD = maxDD at 2×; g<1 = share of anchors with gross cut; ḡ = mean gate)")
    P("| cell | arm | 2024 net S DD | 2025 net S DD | 2026→cut net S DD | 2024→26 net [CI] S DD | 2025→26 net S DD | worst-yr S (yr) | g<1 / ḡ / drag (24→26) |")
    P("|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        b = cell["base"]; f = lambda st, w: f"{st[w]['mean']:+.3f} S{st[w]['sharpe']:.2f} DD{st[w]['maxdd_pct_at_2x']:.1f}%"
        P(f"| {cn} | base | {f(b,'2024')} | {f(b,'2025')} | {f(b,'2026->cut')} | {b['2024->26']['mean']:+.3f} [{b['2024->26']['mean_ci95'][0]:+.2f},{b['2024->26']['mean_ci95'][1]:+.2f}] S{b['2024->26']['sharpe']:.2f} DD{b['2024->26']['maxdd_pct_at_2x']:.1f}% | {f(b,'2025->26')} | {b['worst_year_sharpe']:.2f} ({b['worst_year']}) | — |")
        for an, a in cell["arms"].items():
            st = a["levels"]; w = st["2024->26"]
            P(f"| {cn} | {an} | {f(st,'2024')} | {f(st,'2025')} | {f(st,'2026->cut')} | {w['mean']:+.3f} [{w['mean_ci95'][0]:+.2f},{w['mean_ci95'][1]:+.2f}] S{w['sharpe']:.2f} DD{w['maxdd_pct_at_2x']:.1f}% | {f(st,'2025->26')} | {st['worst_year_sharpe']:.2f} ({st['worst_year']}) | {w['share_gate_lt1']:.2f} / {w['mean_gate']:.3f} / {w['cost_drag_bps_anchor']:.3f} |")
    P("\n## C2 · paired Δ vs base (bps/anchor per full gross; UTC-day-block bootstrap CI95) and the three maximin quantities")
    P("| cell | arm | Δ2024 | Δ2025 | Δ2026→cut | Δ2024→26 [CI] | net ratio 24→26 | Δ worst-yr S | Δ S 24→26 | Δ maxDD 24→26 (pp) |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for an, a in cell["arms"].items():
            d = a["delta_vs_base"]; f = lambda w: f"{d[w]['delta_mean']:+.3f}"
            P(f"| {cn} | {an} | {f('2024')} | {f('2025')} | {f('2026->cut')} | {d['2024->26']['delta_mean']:+.3f} [{d['2024->26']['ci95'][0]:+.3f},{d['2024->26']['ci95'][1]:+.3f}] | {d['2024->26']['net_ratio_pct']:+.1f}% | {a['delta_worst_year_sharpe']:+.2f} | {a['delta_sharpe_2426']:+.2f} | {a['delta_maxdd_2426_pp']:+.1f} |")
    P("\n## C2 · frozen verdict (prod, seeds 42/2027): worst-yr S ≥ +0.3 ∧ S(24→26) ≥ −0.1 ∧ maxDD(24→26) falls")
    P("| arm | role | s42 Δworst / ΔS24→26 / ΔDD | s2027 Δworst / ΔS24→26 / ΔDD | verdict |")
    P("|---|---|---|---|---|")
    for k, v in res["verdict"].items():
        f = lambda s: f"{v['per_seed'][s]['d_worst_year_sharpe']:+.2f} / {v['per_seed'][s]['d_sharpe_2426']:+.2f} / {v['per_seed'][s]['d_maxdd_2426_pp']:+.1f}pp"
        P(f"| {k} | {v['role']} | {f('42')} | {f('2027')} | **{v['verdict']}** |")
    open(f"{ROOT}/c2/c2_tables.md", "w").write("\n".join(Lm) + "\n"); print("\n".join(Lm)); print("C2_DONE", flush=True)
if __name__ == "__main__": main()
