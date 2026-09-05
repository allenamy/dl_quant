#!/usr/bin/env python
"""judge_cl.py — carry_layers judge (PREREG_carry_layers_2026-09-05 §3, frozen before numbers). Reads only carry_layers artifacts (B0 = layers off, bitwise = health_check main arm; receipt logs/check_equiv.log).
UNITS (E-0904-G, printed at run time): rec net_ex = bps/anchor of the unit replay book of gross gross_total; dodge layer adds dodge_delta (same unit-book bps: credit − COST·Σ|w| − drift) ⇒ net_adj = net_ex + dodge_delta;
  g = net_adj / gross_total [bps/anchor per unit gross]; NAV %/yr at L=2 (arithmetic) = mean g × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); Sharpe = mean/std(ddof=1)×√2190; maxDD at 2× from Π(1+2g/1e4).
  DODGE_COST 15.8 is re-priced from the saved cost column (cost = 7.84·Σ|w| ⇒ delta_15.8 = delta − (15.8 − 7.84)·cost/7.84). Turnover = (rec turnover + dodge_turn) / gross_total.
Windows: 2023→cut (main; cut = 2026-08-10 20:00Z) | 2023 | 2024 | 2025 | 2026→cut | 2025-05→cut (H primary). Paired Δ = g_arm − g_base per anchor (anchor sets asserted equal); UTC-day-block bootstrap 2000, seed 20260905.
FROZEN JUDGE (both seeds): candidate ⇔ Δ(2023→cut) CI95 lower > 0 AND every year Δ ≥ −0.05 AND Δ(2026→cut) ≥ 0 AND turnover increase (priced at COST) ≤ +30%.
usage: judge_cl.py → results/judge.json, results/tables.md"""
import numpy as np, json, time, os, hashlib, calendar
ROOT = "/workspace/review_scratch/allweather_trackC/carry_layers"; NB = 2000; SEED = 20260905; APY = 2190; L = 2.0
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600
WIN = {"2023->cut": (T("2023-01-01"), CUT + 1), "2023": (T("2023-01-01"), T("2024-01-01")), "2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2025-05->cut": (T("2025-05-01"), CUT + 1), "2024->cut": (T("2024-01-01"), CUT + 1)}
YEARS = ("2023", "2024", "2025", "2026->cut")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
ARMS = [("D6_prev", "D THR 6 prev"), ("D10_prev", "D THR 10 prev"), ("D15_prev", "D THR 15 prev"), ("D6_oracle", "D THR 6 oracle"), ("D10_oracle", "D THR 10 oracle"), ("D15_oracle", "D THR 15 oracle"), ("H05", "H κ 0.5"), ("H10", "H κ 1.0"), ("L10", "L HI +10"), ("L20", "L HI +20"), ("X", "combo D(10,prev)+H(1)+L(10)")]
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(g):
    nav = np.cumprod(1.0 + L * g / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def boot(r, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 5: return [None, None], None
    s1 = np.bincount(inv, r); c = np.bincount(inv).astype(float); rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd)); m = s1[idx].sum(1) / c[idx].sum(1)
    return [r4(np.percentile(m, 2.5)), r4(np.percentile(m, 97.5))], r4((m > 0).mean())
def load(tag):
    p = f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_{tag}.npz"; Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS
    cfg = json.loads(str(Z["config_json"]))
    return {"path": p, "sha": hashlib.sha256(open(p, "rb").read()).hexdigest(), "cfg": cfg, "R": Z["d30_n2_c42_rec"], "W": Z["d30_n2_c42_W"], "dodge": Z["d30_n2_c42_dodge"], "ev": Z["d30_n2_c42_dodge_events"], "hl": Z["d30_n2_c42_hl"]}
def series(a, cost=7.84):
    R = a["R"]; ts = R[:, 0].astype(np.int64); gt = R[:, C["gross_total"]]; dg = a["dodge"]; assert dg.shape[0] == R.shape[0]
    delta = dg[:, 0] - (cost - 7.84) * dg[:, 2] / 7.84 if dg[:, 4].sum() > 0 else dg[:, 0]
    g = (R[:, C["net_ex"]] + delta) / gt; turn = (R[:, C["turnover"]] + dg[:, 5]) / gt
    return ts, g, turn, gt, delta
def levels(ts, g, turn, gt, R, days):
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); gw = g[m]; ci, p = boot(gw, days[m])
        out[wn] = {"n": int(m.sum()), "mean": r4(gw.mean()), "mean_ci95": ci, "sharpe": r4(sharpe(gw)), "maxdd_pct_at_2x": r4(maxdd(gw)), "nav_pct_yr_at_2x": r4(gw.mean() * 6 * 365 * 2 / 1e4 * 100), "turnover_per_gross": r4(turn[m].mean()), "gross_total": r4(gt[m].mean()),
                   "carry_ex_per_gross": r4((R[m, C["carry_ex"]] / gt[m]).mean()), "cost_ex_per_gross": r4((R[m, C["cost_ex"]] / gt[m]).mean()), "pnl_ex_per_gross": r4((R[m, C["pnl_ex"]] / gt[m]).mean()), "negative": bool(gw.mean() < 0)}
    return out
def main():
    print("UNITS CHAIN: g = (net_ex + dodge_delta)/gross_total [bps/anchor per gross]; NAV %/yr at L=2 = mean g × 6 × 365 × 2 / 1e4 × 100 (1 bps ⇒ 43.8 %/yr); maxDD at 2× from Π(1+2g/1e4); Sharpe = mean/std(ddof=1)×√2190; DODGE_COST 15.8 re-priced: delta − (15.8−7.84)·cost/7.84", flush=True)
    res = {"prereg": "docs/PREREG_carry_layers_2026-09-05.md §3 (sha256 f882c72c…, commit 2ec1934)", "judge_rule": "candidate ⇔ Δ(2023→cut) CI95 lower > 0 both seeds AND every year Δ ≥ −0.05 AND Δ(2026→cut) ≥ 0 AND priced turnover increase ≤ +30%; H arm primary window 2025-05→cut also reported",
           "family": "11 cells (D 3 THR × 2 rules, H 2, L 2, combo 1) × 2 seeds; DODGE_COST 15.8 = re-pricing of the same D cells (sensitivity, not new cells)", "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "cells": {}, "verdict": {}, "d_extras": {}, "hl_extras": {}}
    devsha = set()
    for s in ("42", "2027"):
        b = load(f"B0_prod_s{s}"); assert b["cfg"]["CARRY"]["DODGE_ON"] is False and b["cfg"]["CARRY"]["HL_ON"] is False
        tsb, gb, tb, gtb, _ = series(b); daysb = tsb // 86400; Lb = levels(tsb, gb, tb, gtb, b["R"], daysb)
        # prod meta y4 for forgone-alpha decomposition (H/L)
        MT = np.load(f"{ROOT}/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True); mE = MT["E_ts"].astype(np.int64); mrow = {int(t): i for i, t in enumerate(mE)}; Y4 = MT["y4"]
        rows = np.array([mrow[int(t)] for t in tsb]); YV = np.nan_to_num(Y4[rows], nan=0.0)
        cell = {"base": {"artifact": b["path"], "sha256": b["sha"], "levels": Lb}, "arms": {}}
        for tag, label in ARMS:
            a = load(f"{tag}_prod_s{s}"); devsha.add(a["cfg"]["CARRY"]["device_sha256"]); cc = a["cfg"]["CARRY"]
            assert a["cfg"]["FSEED"] == s and a["cfg"]["UMASK_SCOPE"] == "m1" and a["cfg"]["COSTB_JSON"] and a["cfg"]["PHI"] == 0.45 and a["cfg"]["FTRIM"] == "zero", a["cfg"]
            entry = {"artifact": a["path"], "sha256": a["sha"], "carry_cfg": {k: cc[k] for k in ("DODGE_THR", "DODGE_COST", "DODGE_RULE", "HOUR_K", "LONG_HI")}, "by_cost": {}}
            costs = (7.84, 15.8) if cc["DODGE_ON"] else (7.84,)
            for cost in costs:
                tsa, ga, ta, gta, da = series(a, cost); assert np.array_equal(tsa, tsb), "anchor sets differ"; days = tsa // 86400
                La = levels(tsa, ga, ta, gta, a["R"], days); dl = {}
                for wn, (lo, hi) in WIN.items():
                    m = (tsa >= lo) & (tsa < hi); dd = ga[m] - gb[m]; ci, p = boot(dd, days[m])
                    dl[wn] = {"delta_mean": r4(dd.mean()), "ci95": ci, "p_gt0": p, "delta_sharpe": r4(La[wn]["sharpe"] - Lb[wn]["sharpe"]), "delta_maxdd_pp": r4(La[wn]["maxdd_pct_at_2x"] - Lb[wn]["maxdd_pct_at_2x"]),
                              "turnover_ratio_pct": r4((ta[m].mean() / tb[m].mean() - 1) * 100), "delta_carry_per_gross": r4(La[wn]["carry_ex_per_gross"] - Lb[wn]["carry_ex_per_gross"]), "delta_cost_per_gross": r4(La[wn]["cost_ex_per_gross"] - Lb[wn]["cost_ex_per_gross"]), "delta_pnl_per_gross": r4(La[wn]["pnl_ex_per_gross"] - Lb[wn]["pnl_ex_per_gross"])}
                entry["by_cost"][str(cost)] = {"levels": La, "delta_vs_base": dl}
            # D extras (2023→cut): events/anchor, missing share, credit/cost/drift per gross, drift by funding sign with CI
            if cc["DODGE_ON"]:
                dg = a["dodge"]; m = (tsa >= WIN["2023->cut"][0]) & (tsa < WIN["2023->cut"][1]); ev = a["ev"]; me = (ev[:, 0] >= WIN["2023->cut"][0]) & (ev[:, 0] < WIN["2023->cut"][1]) if len(ev) else np.zeros(0, bool)
                E = ev[me]; ed = (E[:, 0] // 86400).astype(np.int64) if len(E) else np.zeros(0, np.int64)
                def drift_stats(mask):
                    if mask.sum() < 20: return {"n": int(mask.sum())}
                    dpos = np.sign(E[mask, 2]) * E[mask, 5] * 1e4   # P&L the position would have earned in the flat window (bps of the name), + = dodge forgoes gain
                    dprice = E[mask, 5] * 1e4; ci_p, _ = boot(dpos, ed[mask]); ci_r, _ = boot(dprice, ed[mask])
                    return {"n": int(mask.sum()), "mean_price_move_bps": r4(dprice.mean()), "price_move_ci95": ci_r, "mean_forgone_pnl_bps": r4(dpos.mean()), "forgone_pnl_ci95": ci_p, "share_missing_bar": r4((E[mask, 6] > 0).mean())}
                entry["d_extras"] = {"events_per_anchor": r4(dg[m, 4].mean()), "events_total": int(dg[m, 4].sum()), "paying_settlements_per_anchor": r4(dg[m, 7].mean()), "share_paying_dodged": r4(dg[m, 4].sum() / max(dg[m, 7].sum(), 1)), "missing_bar_event_share": r4(dg[m, 6].sum() / max(dg[m, 4].sum(), 1)),
                                    "credit_per_gross": r4((dg[m, 1] / gtb[m]).mean()), "cost784_per_gross": r4((dg[m, 2] / gtb[m]).mean()), "drift_per_gross": r4((dg[m, 3] / gtb[m]).mean()), "dodge_turn_per_gross": r4((dg[m, 5] / gtb[m]).mean()), "dodged_notional_share_of_gross": r4((dg[m, 5] / 2.0 / gtb[m]).mean()),
                                    "drift_rate_pos (longs paying)": drift_stats(E[:, 3] > 0) if len(E) else {}, "drift_rate_neg (shorts paying)": drift_stats(E[:, 3] < 0) if len(E) else {},
                                    "realised_rate_vs_predicted_bps": {"mean_|r_S|": r4(np.abs(E[:, 3]).mean() * 1e4) if len(E) else None, "mean_|r_prev|": r4(np.nanmean(np.abs(E[:, 4])) * 1e4) if len(E) else None, "share_sign_flip": r4((E[:, 3] * np.where(np.isfinite(E[:, 4]), E[:, 4], E[:, 3]) < 0).mean()) if len(E) else None}}
            if cc["HL_ON"]:
                hl = a["hl"]; m = (tsa >= WIN["2023->cut"][0]) & (tsa < WIN["2023->cut"][1]); m25 = (tsa >= WIN["2025-05->cut"][0]) & (tsa < WIN["2025-05->cut"][1])
                Wb = b["W"].astype(np.float64); Wa = a["W"].astype(np.float64); red = np.abs(Wa) < np.abs(Wb) - 1e-9; dw = Wb - Wa
                forg = (np.where(red, dw, 0.0) * YV).sum(1) * 1e4; spill = (np.where(~red, dw, 0.0) * YV).sum(1) * 1e4
                entry["hl_extras"] = {"hour_hits_king_per_anchor_2023": r4(hl[m, 0].mean()), "long_hits_king_per_anchor_2023": r4(hl[m, 1].mean()), "hour_hits_king_per_anchor_2025-05": r4(hl[m25, 0].mean()), "long_hits_king_per_anchor_2025-05": r4(hl[m25, 1].mean()), "hour_hits_f10_per_anchor_2025-05": r4(hl[m25, 2].mean()), "long_hits_f10_per_anchor_2023": r4(hl[m25, 3].mean()),
                                     "names_reduced_per_anchor_2023": r4(red[m].sum(1).mean()), "forgone_price_alpha_reduced_names_per_gross_2023": r4((forg[m] / gtb[m]).mean()), "spillover_price_pnl_other_names_per_gross_2023": r4((spill[m] / gtb[m]).mean()),
                                     "forgone_price_alpha_reduced_names_per_gross_2025-05": r4((forg[m25] / gtb[m25]).mean()), "spillover_price_pnl_other_names_per_gross_2025-05": r4((spill[m25] / gtb[m25]).mean())}
            cell["arms"][tag] = entry
        res["cells"][f"prod/s{s}"] = cell
    res["device_sha256_set"] = sorted(devsha); assert len(devsha) == 1, devsha
    for tag, label in ARMS:
        for cost in (("7.84", "15.8") if tag.startswith("D") or tag == "X" else ("7.84",)):
            if tag == "X" and cost == "15.8": continue
            per = {}
            for s in ("42", "2027"):
                e = res["cells"][f"prod/s{s}"]["arms"][tag]["by_cost"].get(cost)
                if e is None: continue
                dl = e["delta_vs_base"]; per[s] = {"d_main": dl["2023->cut"]["delta_mean"], "ci_lo": dl["2023->cut"]["ci95"][0], "ci_hi": dl["2023->cut"]["ci95"][1], "years": {y: dl[y]["delta_mean"] for y in YEARS}, "turn_pct": dl["2023->cut"]["turnover_ratio_pct"], "d_h": dl["2025-05->cut"]["delta_mean"], "ci_lo_h": dl["2025-05->cut"]["ci95"][0],
                          "pass_ci": dl["2023->cut"]["ci95"][0] > 0, "pass_years": all(dl[y]["delta_mean"] >= -0.05 for y in YEARS), "pass_2026": dl["2026->cut"]["delta_mean"] >= 0, "pass_turn": dl["2023->cut"]["turnover_ratio_pct"] <= 30.0}
            cand = all(per[s]["pass_ci"] and per[s]["pass_years"] and per[s]["pass_2026"] and per[s]["pass_turn"] for s in per)
            rej = any(per[s]["ci_hi"] < 0 for s in per)
            res["verdict"][f"{tag}@{cost}"] = {"label": label, "cost": cost, "per_seed": per, "verdict": "CANDIDATE" if cand else ("NOT CANDIDATE (2023→cut CI95 upper < 0 in ≥1 seed)" if rej else "NOT CANDIDATE")}
    # prev vs oracle gap
    res["d_gap"] = {}
    for thr in ("6", "10", "15"):
        for s in ("42", "2027"):
            for cost in ("7.84", "15.8"):
                dp = res["cells"][f"prod/s{s}"]["arms"][f"D{thr}_prev"]["by_cost"][cost]["delta_vs_base"]["2023->cut"]["delta_mean"]; do = res["cells"][f"prod/s{s}"]["arms"][f"D{thr}_oracle"]["by_cost"][cost]["delta_vs_base"]["2023->cut"]["delta_mean"]
                res["d_gap"][f"THR{thr}/s{s}/@{cost}"] = {"prev": dp, "oracle": do, "gap_oracle_minus_prev": r4(do - dp)}
    json.dump(res, open(f"{ROOT}/results/judge.json", "w"), indent=1, ensure_ascii=False)
    Lm = []; P = Lm.append
    P("## carry_layers · levels (prod, g = bps/anchor per gross; S = Sharpe; DD = 2× maxDD; turn = turnover/gross incl. dodge trades) — base and all arms @COST 7.84")
    P("| cell | arm | 2023 g S | 2024 g S | 2025 g S | 2026→cut g S | **2023→cut g [CI] S DD turn** | 2025-05→cut g S |")
    P("|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        Lb = cell["base"]["levels"]; f = lambda Lx, w: f"{Lx[w]['mean']:+.3f} S{Lx[w]['sharpe']:.2f}"
        P(f"| {cn} | B0 base | {f(Lb,'2023')} | {f(Lb,'2024')} | {f(Lb,'2025')} | {f(Lb,'2026->cut')} | **{Lb['2023->cut']['mean']:+.3f} [{Lb['2023->cut']['mean_ci95'][0]:+.2f},{Lb['2023->cut']['mean_ci95'][1]:+.2f}] S{Lb['2023->cut']['sharpe']:.2f} DD{Lb['2023->cut']['maxdd_pct_at_2x']:.1f}% turn {Lb['2023->cut']['turnover_per_gross']:.4f}** | {f(Lb,'2025-05->cut')} |")
        for tag, label in ARMS:
            La = cell["arms"][tag]["by_cost"]["7.84"]["levels"]
            P(f"| {cn} | {label} | {f(La,'2023')} | {f(La,'2024')} | {f(La,'2025')} | {f(La,'2026->cut')} | **{La['2023->cut']['mean']:+.3f} [{La['2023->cut']['mean_ci95'][0]:+.2f},{La['2023->cut']['mean_ci95'][1]:+.2f}] S{La['2023->cut']['sharpe']:.2f} DD{La['2023->cut']['maxdd_pct_at_2x']:.1f}% turn {La['2023->cut']['turnover_per_gross']:.4f}** | {f(La,'2025-05->cut')} |")
    P("\n## carry_layers · paired Δ vs B0 (bps/anchor per gross; UTC-day-block bootstrap CI95; Δturn% over 2023→cut; Δcarry/Δcost/Δpnl per gross 2023→cut)")
    P("| cell | arm | COST | Δ2023 | Δ2024 | Δ2025 | Δ2026→cut | **Δ2023→cut [CI]** | Δ2025-05→cut [CI] | Δturn% | Δcarry | Δcost | Δpnl |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for tag, label in ARMS:
            for cost, e in cell["arms"][tag]["by_cost"].items():
                d = e["delta_vs_base"]; f = lambda w: f"{d[w]['delta_mean']:+.3f}"
                P(f"| {cn} | {label} | {cost} | {f('2023')} | {f('2024')} | {f('2025')} | {f('2026->cut')} | **{d['2023->cut']['delta_mean']:+.3f} [{d['2023->cut']['ci95'][0]:+.3f},{d['2023->cut']['ci95'][1]:+.3f}]** | {d['2025-05->cut']['delta_mean']:+.3f} [{d['2025-05->cut']['ci95'][0]:+.3f},{d['2025-05->cut']['ci95'][1]:+.3f}] | {d['2023->cut']['turnover_ratio_pct']:+.1f}% | {d['2023->cut']['delta_carry_per_gross']:+.3f} | {d['2023->cut']['delta_cost_per_gross']:+.3f} | {d['2023->cut']['delta_pnl_per_gross']:+.3f} |")
    P("\n## D extras (2023→cut): events/anchor, share of paying settlements dodged, missing-bar share, credit/cost/drift per gross, dodged notional share of gross, flat-window drift by funding sign (bps of the name; forgone P&L = sign(w)·move, + = dodge forgoes a gain), prev→oracle rate stats")
    P("| cell | arm | events/anchor | paying/anchor | dodged share | miss share | credit | cost@7.84 | drift | notional/gross | r_S>0: n, price move [CI], forgone P&L [CI] | r_S<0: n, price move [CI], forgone P&L [CI] | mean|r_S| / mean|r_prev| bps, sign-flip share |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for tag, label in ARMS:
            x = cell["arms"][tag].get("d_extras")
            if not x: continue
            dp = x["drift_rate_pos (longs paying)"]; dn = x["drift_rate_neg (shorts paying)"]; rv = x["realised_rate_vs_predicted_bps"]
            fd = lambda z: f"{z.get('n')}, {z.get('mean_price_move_bps')} {z.get('price_move_ci95')}, {z.get('mean_forgone_pnl_bps')} {z.get('forgone_pnl_ci95')}"
            P(f"| {cn} | {label} | {x['events_per_anchor']} | {x['paying_settlements_per_anchor']} | {x['share_paying_dodged']} | {x['missing_bar_event_share']} | {x['credit_per_gross']:+.3f} | {x['cost784_per_gross']:.3f} | {x['drift_per_gross']:+.3f} | {x['dodged_notional_share_of_gross']:.4f} | {fd(dp)} | {fd(dn)} | {rv['mean_|r_S|']} / {rv['mean_|r_prev|']}, {rv['share_sign_flip']} |")
    P("\n## H/L extras: names hit per anchor (king book / F10 book), names reduced per anchor, forgone price alpha of reduced names and spillover (bps/anchor per gross)")
    P("| cell | arm | hour hits king 2023 / 2025-05 | long hits king 2023 / 2025-05 | hour hits f10 2025-05 | reduced names/anchor 2023 | forgone alpha 2023 / 2025-05 | spillover 2023 / 2025-05 |")
    P("|---|---|---|---|---|---|---|---|")
    for cn, cell in res["cells"].items():
        for tag, label in ARMS:
            x = cell["arms"][tag].get("hl_extras")
            if not x: continue
            P(f"| {cn} | {label} | {x['hour_hits_king_per_anchor_2023']} / {x['hour_hits_king_per_anchor_2025-05']} | {x['long_hits_king_per_anchor_2023']} / {x['long_hits_king_per_anchor_2025-05']} | {x['hour_hits_f10_per_anchor_2025-05']} | {x['names_reduced_per_anchor_2023']} | {x['forgone_price_alpha_reduced_names_per_gross_2023']:+.3f} / {x['forgone_price_alpha_reduced_names_per_gross_2025-05']:+.3f} | {x['spillover_price_pnl_other_names_per_gross_2023']:+.3f} / {x['spillover_price_pnl_other_names_per_gross_2025-05']:+.3f} |")
    P("\n## prev vs oracle gap (Δ2023→cut, bps/anchor per gross) = value of a premium-TWAP nowcast")
    P("| THR | seed | COST | Δ prev | Δ oracle | gap |")
    P("|---|---|---|---|---|---|")
    for k, v in res["d_gap"].items(): P(f"| {k.split('/')[0][3:]} | {k.split('/')[1]} | {k.split('@')[1]} | {v['prev']:+.3f} | {v['oracle']:+.3f} | {v['gap_oracle_minus_prev']:+.3f} |")
    P("\n## frozen verdict (both seeds): Δ23→cut CI lo > 0 ∧ years ≥ −0.05 ∧ Δ2026 ≥ 0 ∧ Δturn ≤ +30%")
    P("| arm | COST | s42 Δ [CI] / min-year Δ / Δ2026 / Δturn | s2027 | verdict |")
    P("|---|---|---|---|---|")
    for k, v in res["verdict"].items():
        f = lambda s: f"{v['per_seed'][s]['d_main']:+.3f} [{v['per_seed'][s]['ci_lo']:+.3f},{v['per_seed'][s]['ci_hi']:+.3f}] / {min(v['per_seed'][s]['years'].values()):+.3f} / {v['per_seed'][s]['years']['2026->cut']:+.3f} / {v['per_seed'][s]['turn_pct']:+.1f}%"
        P(f"| {v['label']} | {v['cost']} | {f('42')} | {f('2027')} | **{v['verdict']}** |")
    open(f"{ROOT}/results/tables.md", "w").write("\n".join(Lm) + "\n"); print("\n".join(Lm)); print("JUDGE_CL_DONE", flush=True)
if __name__ == "__main__": main()
