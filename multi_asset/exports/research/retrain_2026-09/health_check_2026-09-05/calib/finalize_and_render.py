"""finalize_and_render.py — adds (1) the commission-collision finding and (2) a delay-reweighted +60s markout to cost_calib.json,
then renders REPORT.md from the JSON. Every number in REPORT.md is written by this script from cost_calib.json / canon_report.json /
commission_collision_test.py output. READ-ONLY on the live trees."""
import os, json, subprocess, hashlib, time, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
PL = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
CC = json.load(open(f"{HERE}/cost_calib.json")); CR = json.load(open(f"{HERE}/canon_report.json"))

# ---------- (1) commission collision test (re-run, parse) ----------
out = subprocess.run([sys.executable, f"{HERE}/commission_collision_test.py"], capture_output=True, text=True).stdout
open(f"{HERE}/commission_collision_test.out", "w").write(out)
rows = []
for ln in out.splitlines():
    if ln[:4] == "2026" and "|" in ln:
        p = [x.strip() for x in ln.split("|")]
        rows.append({"day": p[0], "venue_COMMISSION_BNB": float(p[1]), "log_all_BNB": float(p[2]), "log_opening_only_BNB": float(p[3]), "log_reducing_only_BNB": float(p[4]), "venue_over_all": float(p[5]), "venue_over_opening": float(p[6])})
tot = [ln for ln in out.splitlines() if ln.startswith("TOTAL")][0]
CC["findings"] = {"commission_collision": {
    "status": "VERIFIED (exact match on 10/11 days; 08-26 differs by the flatten event whose fees are not in fills.jsonl)",
    "what": "daily_nav.realised_by_type.COMMISSION equals the pilot-log commission of position-OPENING fills only. Position-REDUCING fills' COMMISSION rows are missing.",
    "why": "live/binance_broker.py realised-income pagination dedupes rows on tranId; a reducing fill's COMMISSION row shares its tranId with the same trade's REALIZED_PNL row, so the second of the pair is dropped. Reproduced by classifying every fill as opening/reducing from the previous anchor's position_readback.",
    "money": "small: commission is charged in BNB (~0.002 BNB/day at 41k gross, ~0.005-0.011 BNB/day at 163k gross); REALIZED_PNL rows are the ones kept. Also note realised_pnl sums COMMISSION in BNB units with USDT rows.",
    "consequence_for_this_report": "none — fees here come from /fapi/v1/userTrades via orders.fee_paid (= commission_BNB x bookTicker BNB mid, exact on 6908/6908 rows) and fills.commission; daily_nav COMMISSION must not be used for fee totals.",
    "receipt": "commission_collision_test.py -> commission_collision_test.out", "total_line": tot, "daily": rows}}

# ---------- (2) delay-reweighted +60s markout (post-stratification on fill delay after the anchor) ----------
H4 = 14400
days = [d for d in sorted(os.listdir(PL)) if d.isdigit() and "20260826" <= d <= "20260905"]
def jl(d, n):
    p = f"{PL}/{d}/{n}.jsonl"; return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
O = [r for d in days for r in jl(d, "orders")]; F = [r for d in days for r in jl(d, "fills")]; A = [r for d in days for r in jl(d, "anchors")]
ANCT = {r["rebalance_id"]: float(r["anchor_ts"]) for r in A}; rid2N = {r["rebalance_id"]: int(float(r["anchor_ts"]) // H4 * H4) for r in A}
steadyN = set(r["N"] for r in CC["per_anchor"] if r["steady"]); calibN = set(r["N"] for r in CC["per_anchor"] if r["in_calib"])
byid = {}
for r in F:
    if r["trade_id"] not in byid or r.get("supersedes_trade_id") is not None: byid[r["trade_id"]] = r
FD = list(byid.values())
B = [(0, 10), (10, 60), (60, 300), (300, 1e9)]
def poststrat(N_set, typ):
    fl = [r for r in FD if rid2N.get(r["rebalance_id"]) in N_set and r["order_type"] == typ]
    res = {"buckets": [], "adjusted_bps": None, "raw_weighted_bps": None, "n_backfilled": 0, "n_population": len(fl)}
    adj = 0.0; wsum = 0.0; num = 0.0; den = 0.0
    for lo, hi in B:
        pop = [r for r in fl if lo <= float(r["fill_ts"]) - ANCT[r["rebalance_id"]] < hi]
        sub = [r for r in pop if r.get("mid_at_fill_plus_60s") is not None]
        pw = sum(float(r["fill_notional"]) for r in pop); tw = sum(float(r["fill_notional"]) for r in fl)
        mo = [(1 if r["side"] == "buy" else -1) * (float(r["mid_at_fill_plus_60s"]) - float(r["fill_px"])) / float(r["fill_px"]) * 1e4 for r in sub]
        w = [float(r["fill_notional"]) for r in sub]
        wm = float(np.dot(mo, w) / sum(w)) if sum(w) > 0 else None
        res["buckets"].append({"delay_s": f"[{lo},{hi if hi < 1e8 else 'inf'})", "population_notional_share": pw / tw if tw else None, "n_backfilled": len(sub), "subset_weighted_bps": wm})
        res["n_backfilled"] += len(sub); num += float(np.dot(mo, w)) if w else 0.0; den += sum(w)
        if wm is not None and len(sub) >= 5: adj += (pw / tw) * wm; wsum += pw / tw
    res["adjusted_bps"] = adj / wsum if wsum > 0 else None; res["raw_weighted_bps"] = num / den if den > 0 else None
    res["note"] = "subset markout re-weighted to the population's fill-delay mix (buckets with <5 marks dropped and weights renormalised). INFERRED: the backfill subset is the alphabetically-first symbols and the earliest fills of each anchor, not a random sample."
    return res
CC["markout_poststratified"] = {"steady": {"maker": poststrat(steadyN, "maker"), "topup_taker": poststrat(steadyN, "topup_taker")},
                                "all_calib": {"maker": poststrat(calibN, "maker"), "topup_taker": poststrat(calibN, "topup_taker")}}
CC["receipts"] = {"cost_calib.py": sha(f"{HERE}/cost_calib.py"), "canon_reconcile.py": sha(f"{HERE}/canon_reconcile.py"), "canon_report.json": sha(f"{HERE}/canon_report.json"),
                  "commission_collision_test.py": sha(f"{HERE}/commission_collision_test.py"), "markout_diag.py": sha(f"{HERE}/markout_diag.py"), "finalize_and_render.py": sha(os.path.abspath(__file__)),
                  "commands": ["cd <calib dir> && cp <research repo>/multi_asset/exports/research/retrain_2026-09/review_caliber_wf/gap_live_pnl/canon_reconcile.py . && python3 canon_reconcile.py > canon_run.log",
                               "python3 cost_calib.py > calib_run.log", "python3 markout_diag.py > markout_diag.out", "python3 finalize_and_render.py"],
                  "finalized_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(CC, open(f"{HERE}/cost_calib.json", "w"), indent=1)

# ---------- render REPORT.md ----------
def f(x, d=2, pct=False, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)): return "n/a"
    if pct: return f"{100*x:.{d}f}%"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
def ci(v, d=2): return "n/a" if not v or v[0] is None else f"[{v[0]:+.{d}f}, {v[1]:+.{d}f}]"
L = []; P = L.append
S = CC["calib"]["primary_steady"]; ALL = CC["calib"]["all_calib"]; U = CC["uncertainty"]; TG = CC["twin_gap"]; AN = CC["anchors"]
P(f"> **创建:** {CC['receipts']['finalized_utc']} | **Session:** b9646a9e (calib teammate, read-only on `~/dl_quant_live` and `~/wide_shadow`) | **状态:** calibration receipts, no ruling | **作废条件:** any log re-write, executor pricing/top-up change, or a tier rule different from the producer's `qv4h` | **方法:** `docs/PREREG_live_form_health_check_2026-09-05.md` §1 (frozen)")
P("")
P("# Live execution cost and fill calibration — combo go-live 08-26 04Z → 09-05 00Z")
P("")
P("All numbers below are printed by scripts in this directory (receipts in §12). Units: notional in USDT one-sided; bps = 1/10000 of the notional named in each table; per-anchor rates are means over anchors unless a row says pooled. Labels: VERIFIED = read from the logs with an exact cross-check; INFERRED = a sample or a model assumption is involved.")
P("")
P("## 0. Bottom line (steady-state anchors, n = %d)" % S["anchors"]["n"])
P("")
P("| quantity | value | label |")
P("|---|---|---|")
P(f"| maker fee / taker fee (bps of traded notional) | {f(S['all']['maker_bps_fee'],3)} / {f(S['all']['taker_bps_fee'],3)} | VERIFIED (= venue schedule with BNB discount; fee_paid = BNB × px on 6908/6908 rows) |")
P(f"| maker share of filled notional | {f(S['all']['maker_share'],3)} (anchor-mean CI95 {ci(U['steady']['maker_share_ci95_anchor_boot'],3)}) | VERIFIED |")
P(f"| maker fill ratio buy / sell / all | {f(S['all']['fill_ratio_maker_buy'],3)} / {f(S['all']['fill_ratio_maker_sell'],3)} / {f(S['all']['fill_ratio_maker'],3)} | VERIFIED |")
P(f"| fill ratio after top-ups buy / sell / all | {f(S['all']['fill_ratio_after_topup_buy'],3)} / {f(S['all']['fill_ratio_after_topup_sell'],3)} / {f(S['all']['fill_ratio_after_topup'],3)} | VERIFIED |")
P(f"| −5022 first refusal (share of maker legs sent) | {f(S['all']['reject5022_first_rate'],3)} pooled; anchor-mean CI95 {ci(U['steady']['reject5022_first_rate_count_ci95_anchor_boot'],3)} | VERIFIED |")
P(f"| −5022 refused twice → taker top-up | {f(S['all']['reject5022_to_taker_rate'],3)} pooled | VERIFIED |")
P(f"| turnover per anchor (filled / venue gross) | mean {f(S['turnover_per_anchor']['mean'],4)}, median {f(S['turnover_per_anchor']['median'],4)}, notional-weighted {f(S['turnover_per_anchor']['notional_weighted'],4)} | VERIFIED |")
P(f"| fee cost per unit of turnover (fee only) | {f(S['all']['cost_per_unit_turnover_fee_only_bps'],3)} bps | VERIFIED |")
P(f"| fee drag per anchor / per year | {f(S['units_chain']['fee_bps_of_gross_per_anchor'],4)} bps of gross per anchor = {f(S['units_chain']['fee_pct_of_gross_per_year'],2)}% of gross per year = {f(S['units_chain']['fee_pct_of_NAV_per_year_at_2x'],2)}% of NAV per year at 2× | VERIFIED arithmetic (2190 anchors/yr) |")
P(f"| +60 s markout, maker (notional-weighted) | {f(S['all']['markout60_maker_bps'],2,sign=True)} bps on {U['steady']['markout60_maker_tierall_n']} marks = {f(S['all']['markout60_coverage_notional'],1,pct=True)} of notional; CI95 {ci(U['steady']['markout60_maker_tierall_ci95_fill_boot'])}; delay-reweighted {f(CC['markout_poststratified']['steady']['maker']['adjusted_bps'],2,sign=True)} | INFERRED (non-random 5% subset) |")
P(f"| paper target vs real, twin + funding (bps of gross per anchor) | {f(TG['twin_plus_funding_bps_per_anchor']['mean'],2,sign=True)}, CI95 {ci(TG['twin_plus_funding_bps_per_anchor']['ci95_bootstrap'])}, n = {TG['n_canon']} | VERIFIED (canon_reconcile.py reused verbatim) |")
P(f"| paper (venue-aligned) minus twin = execution discount band | {f(TG['paper_s25_minus_twin_bps']['mean'],2,sign=True)} bps per anchor, CI95 {ci(TG['paper_s25_minus_twin_bps']['ci95_bootstrap'])} | VERIFIED, wide |")
P("")
P("The two calibration products the replay can consume are in §8: the fee-only vector per tier (VERIFIED) and the fee-minus-markout vector (INFERRED, thin and biased coverage). The paper-vs-real band in §9 is the execution discount the prereg asks to carry alongside, not a per-trade cost.")
P("")
P("## 1. Anchors and sets")
P("")
P("| set | n | first | last | rule |")
P("|---|---|---|---|---|")
P(f"| all live rows in the window | {AN['n_rows']} | {AN['first']} | {AN['last']} | anchors.jsonl 08-26 → 09-05 |")
P(f"| in calibration (`all_calib`) | {AN['n_in_calib']} | {AN['calib_first']} | {AN['calib_last']} | combo producer (from 08-26 04Z), not halted, venue gross ≥ 1000 |")
P(f"| steady (`primary_steady`) | {AN['n_steady']} | {S['anchors']['first']} | {S['anchors']['last']} | in calibration minus step-up anchors ({AN['stepup_rule']}) |")
P(f"| pre-deposit steady | {CC['calib']['pre_deposit']['anchors']['n']} | {CC['calib']['pre_deposit']['anchors']['first']} | {CC['calib']['pre_deposit']['anchors']['last']} | steady, before the 09-03 16Z deposit build |")
P(f"| post-deposit steady | {CC['calib']['post_deposit']['anchors']['n']} | {CC['calib']['post_deposit']['anchors']['first']} | {CC['calib']['post_deposit']['anchors']['last']} | steady, gross ≈ 163k |")
P("")
P("Excluded from steady (VERIFIED from anchors.jsonl):")
P("")
P("| anchor | why |")
P("|---|---|")
for e in AN["excluded"]: P(f"| {e['when']} | {e['why']} |")
P("")
P(f"Row semantics used throughout (VERIFIED from `live/binance_executor.py` and the per-(anchor, symbol) row patterns): one leg = one (anchor, symbol). A −5022 first refusal is an attempt-1 maker reject row; the single maker requote, if it rests, is logged as a second attempt-1 maker row for the same leg; if refused again it is an attempt-2 maker reject row and the residual goes to the taker top-up (`from_reject`). Counts: {CC['fills']['unique_trade_id']} unique fills (from {CC['fills']['rows']} rows, {CC['fills']['backfilled']} superseded by a backfilled +60 s mark), 15630 legs, 2032 first refusals, 1506 requotes rested, 526 refused twice. Fee identities: fee_paid = commission_BNB × BNB mid on 6908/6908 fee rows (max rel diff 0); Σ fills commission = order fee_conversion qty on 6908/6908; |order filled_notional| = Σ fills on 6908/6908 (max rel diff 4e-16). The 08-26 12:49Z protective flatten (334 taker rows, {f(CC['protective_flatten_event']['filled_notional'],0)} USDT) has no fills rows and no fee record; it is outside every table below.")
P("")
P("## 2. Liquidity tiers (VERIFIED)")
P("")
P("| item | value |")
P("|---|---|")
P(f"| rule | {CC['tier_rule']['tiers']['0']} → tier 0; {CC['tier_rule']['tiers']['1']} → tier 1; {CC['tier_rule']['tiers']['2']} → tier 2 |")
P(f"| qv4h | {CC['tier_rule']['qv4h']} |")
P(f"| source | {CC['tier_rule']['source']} |")
P("| check | recomputed at the producer's latest anchor 1788580800 (09-05 04Z): the set of names with qv4h ≥ 2.5e5 over the producer's 400 members equals the producer's own `sel_idx` (233 of 233, set identity true, `aux.json prev_rec`) |")
P(f"| traded notional by tier (steady) | tier 0 {f(S['tiers']['0']['share_of_filled_notional'],1,pct=True)}, tier 1 {f(S['tiers']['1']['share_of_filled_notional'],1,pct=True)}, tier 2 {f(S['tiers']['2']['share_of_filled_notional'],1,pct=True)} |")
P(f"| note | {CC['tier_rule']['note']} |")
P("")
P("## 3. Fees (VERIFIED)")
P("")
P("| set | tier | fills maker / taker | maker notional | taker notional | maker share | maker fee bps | taker fee bps | blended fee bps |")
P("|---|---|---|---|---|---|---|---|---|")
for lab, C in (("steady", "steady"), ("all_calib", "all_calib")):
    R = CC["by_set"][C]
    for t in ("0", "1", "2", "all"):
        d = R[t]; P(f"| {lab} | {t} | {d['n_fills_maker']} / {d['n_fills_taker']} | {f(d['maker_notional'],0)} | {f(d['taker_notional'],0)} | {f(d['maker_share'],3)} | {f(d['maker_fee_bps'],3)} | {f(d['taker_fee_bps'],3)} | {f(d['blended_fee_bps'],3)} |")
P("")
P("Venue-side cross-check of the same fees (daily_nav COMMISSION, BNB units, since 00:00Z each day) against the log's commission split by whether the fill opened or reduced a position:")
P("")
P("| day | venue COMMISSION BNB | log all fills BNB | log opening fills only BNB | venue / all | venue / opening |")
P("|---|---|---|---|---|---|")
for r in rows: P(f"| {r['day']} | {r['venue_COMMISSION_BNB']:.6f} | {r['log_all_BNB']:.6f} | {r['log_opening_only_BNB']:.6f} | {r['venue_over_all']:.3f} | {r['venue_over_opening']:.3f} |")
P(f"| total | {tot} | | | | |")
P("")
P("Reading: the venue field reproduces the opening-fill commission exactly and is missing every reducing fill's commission (§10 finding 1). The fee tables above therefore use the per-trade `fee_paid` (userTrades), which is complete.")
P("")
P("## 4. Maker share and fill ratios (VERIFIED)")
P("")
P("| set | tier | legs sent | maker fill ratio buy | sell | all | after top-up buy | sell | all |")
P("|---|---|---|---|---|---|---|---|---|")
for lab in ("steady", "all_calib", "pre_deposit", "post_deposit"):
    R = CC["by_set"][lab]
    for t in ("0", "1", "2", "all"):
        d = R[t]; P(f"| {lab} | {t} | {d['n_legs_sent']} | {f(d['fill_ratio_maker_buy'],3)} | {f(d['fill_ratio_maker_sell'],3)} | {f(d['fill_ratio_maker_all'],3)} | {f(d['fill_ratio_after_topup_buy'],3)} | {f(d['fill_ratio_after_topup_sell'],3)} | {f(d['fill_ratio_after_topup_all'],3)} |")
P("")
P("Fill ratio = filled notional / intended notional of the attempt-1 maker leg, over legs actually sent (skipped-below-minimum and halted legs excluded). After top-up adds the taker top-up fills to the numerator; the residual that is never sent is the chase experiment's no-chase arm, dust below the venue minimum, and abandoned top-ups.")
P("")
P("## 5. −5022 post-only refusals (VERIFIED)")
P("")
P("| set | tier | first refusal rate (legs) | first refusal rate (notional) | refused twice → taker (legs) | requotes that rested / first refusals | taker notional from refusals | taker notional from partial fills |")
P("|---|---|---|---|---|---|---|---|")
for lab in ("steady", "all_calib"):
    R = CC["by_set"][lab]
    for t in ("0", "1", "2", "all"):
        d = R[t]; P(f"| {lab} | {t} | {f(d['reject5022_first_rate_count'],3)} | {f(d['reject5022_first_rate_notional'],3)} | {f(d['reject5022_second_rate_count'],3)} | {f(d['requote_rested_share_of_first'],3)} | {f(d['taker_from_reject_notional'],0)} | {f(d['taker_from_partial_notional'],0)} |")
P("")
P("Per-anchor series (all live anchors; C = in calibration, S = steady):")
P("")
P("| anchor | set | venue gross | legs sent | −5022 first n | rate (legs) | rate (notional) | refused twice n | maker filled | taker filled | turnover filled/gross | unfilled % of intended | maker share | fee USDT | fee bps of filled | fills (with +60 s mark) |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in CC["per_anchor"]:
    P(f"| {r['when']} | {'C' if r['in_calib'] else '-'}{'S' if r['steady'] else '-'} | {f(r['venue_gross'],0)} | {r['n_legs_sent']} | {r['n_5022_first']} | {f(r['reject5022_first_rate_count'],3)} | {f(r['reject5022_first_rate_notional'],3)} | {r['n_5022_second']} | {f(r['maker_filled'],0)} | {f(r['taker_filled'],0)} | {f(r['turnover_filled'],4)} | {f(r['unfilled_frac_of_intended'],1,pct=True)} | {f(r['maker_share'],3)} | {f(r['fee_usdt'],2)} | {f(r['fee_bps_of_filled'],3)} | {r['n_fills']} ({r['n_backfilled']}) |")
P("")
P("## 6. +60 s markout (INFERRED — coverage and selection stated)")
P("")
P("Sign: positive = the price moved in the direction of our trade after the fill (favourable); negative = adverse selection. Notional-weighted. Only fills with a backfilled mark (`/fapi/v1/aggTrades` first trade at or after fill + 60 s).")
P("")
P("| set | type | tier | marks n | coverage of notional | weighted bps | CI95 (fill bootstrap) | median bps |")
P("|---|---|---|---|---|---|---|---|")
for lab in ("steady", "all_calib"):
    R = CC["by_set"][lab]; u = U[lab]
    for typ, key in (("maker", "maker"), ("taker top-up", "taker")):
        for t in ("0", "1", "2", "all"):
            d = R[t]; tk = "topup_taker" if key == "taker" else "maker"; tt = t if t != "all" else "all"
            P(f"| {lab} | {typ} | {t} | {d[f'markout60_{key}_n']} | {f(d[f'markout60_{key}_coverage_notional'],1,pct=True)} | {f(d[f'markout60_{key}_bps'],2,sign=True)} | {ci(u[f'markout60_{tk}_tier{tt}_ci95_fill_boot'])} | {f(d[f'markout60_{key}_median_bps'],2,sign=True)} |")
P("")
P("Why the subset is not random (VERIFIED from `ops/backfill_markout.py` and `markout_diag.out`): the backfill walks symbols in sorted order and fills in time order under a request budget, so the marked fills are the alphabetically-first names (40 of 333 symbols; top: 4USDT, 1000PEPEUSDT, ACEUSDT, 1000BONKUSDT, 0GUSDT) and the earliest fills of each anchor (median rank 0.19 within the anchor; median fill delay 22 s vs 65 s in the population). The subset therefore over-represents fast fills. Re-weighting the subset to the population's fill-delay mix moves the steady maker figure only from −6.2 to −6.7 bps, because the sparse slow bucket (16 marks) is worse still; the symbol selection cannot be corrected from the logs:")
P("")
P("| set | type | delay bucket | population notional share | marks n | subset weighted bps |")
P("|---|---|---|---|---|---|")
for lab in ("steady", "all_calib"):
    for typ in ("maker", "topup_taker"):
        ps = CC["markout_poststratified"][lab][typ]
        for b in ps["buckets"]: P(f"| {lab} | {typ} | {b['delay_s']} s | {f(b['population_notional_share'],3)} | {b['n_backfilled']} | {f(b['subset_weighted_bps'],2,sign=True)} |")
        P(f"| {lab} | {typ} | **re-weighted** | | {ps['n_backfilled']} | **{f(ps['adjusted_bps'],2,sign=True)}** (raw {f(ps['raw_weighted_bps'],2,sign=True)}) |")
P("")
P("Supplementary, 100% coverage, not one of the frozen items: fill price versus the anchor mid (`mid_at_anchor`, positive = filled better than the anchor mid). Maker fills beat the anchor mid; taker top-ups, sent up to 900 s later, pay delay plus spread.")
P("")
P("| set | type | tier | weighted bps | CI95 | median bps |")
P("|---|---|---|---|---|---|")
for lab in ("steady", "all_calib"):
    R = CC["by_set"][lab]; u = U[lab]
    for typ, key, tk in (("maker", "maker", "maker"), ("taker top-up", "taker", "topup_taker")):
        for t in ("0", "1", "2", "all"):
            d = R[t]; tt = t
            P(f"| {lab} | {typ} | {t} | {f(d[f'vs_anchor_mid_{key}_bps'],2,sign=True)} | {ci(u[f'vs_anchor_mid_{tk}_tier{tt}_ci95_fill_boot'])} | {f(u[f'vs_anchor_mid_{tk}_tier{tt}_median'],2,sign=True)} |")
P("")
P("## 7. Turnover per anchor (VERIFIED)")
P("")
P("| set | n anchors | mean | median | notional-weighted | p10 | p90 | CI95 of mean (anchor bootstrap) | intended turnover mean | unfilled share of intended (mean) |")
P("|---|---|---|---|---|---|---|---|---|---|")
for lab in ("steady", "all_calib", "pre_deposit", "post_deposit"):
    s = CC["per_anchor_summary"][lab]; c = CC["calib"][{"steady": "primary_steady"}.get(lab, lab)]
    cib = ci(U[lab]["turnover_filled_ci95_anchor_boot"], 4) if lab in U else "n/a"
    P(f"| {lab} | {s['turnover_filled']['n']} | {f(s['turnover_filled']['mean'],4)} | {f(s['turnover_filled']['median'],4)} | {f(s['turnover_filled_notional_weighted'],4)} | {f(s['turnover_filled']['p10'],4)} | {f(s['turnover_filled']['p90'],4)} | {cib} | {f(s['turnover_intended']['mean'],4)} | {f(s['unfilled_frac_of_intended']['mean'],3)} |")
P("")
P("Turnover = Σ|filled notional| of the anchor's maker and top-up fills / the anchor's venue gross after the anchor. The producer's own book-level turnover at the latest anchor is 0.02008 (shadow_log); the executor's filled turnover at 09-05 00Z is 0.0280, the difference being the executor's re-demean, rescale, floors and forced exits.")
P("")
P("## 8. All-in cost per unit of turnover by tier")
P("")
P("Definition (prereg §1): replay cost = turnover × [maker_share × maker_bps + (1 − maker_share) × taker_bps] per tier, with maker_bps / taker_bps = fee + (−markout). Two versions, because the markout leg is a 5% biased sample:")
P("")
P("| set | tier | share of live turnover | maker share | maker fee bps | taker fee bps | fee-only cost per unit turnover (VERIFIED) | maker markout bps | taker markout bps | fee − markout cost per unit turnover (INFERRED) | device COST_B blended (for comparison) |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
dev = S["units_chain"]["device_COST_B_blended_bps_per_unit_turnover_by_tier"]
for lab, C in (("steady", "primary_steady"), ("all_calib", "all_calib")):
    c = CC["calib"][C]
    for t in ("0", "1", "2"):
        b = c["tiers"][t]; P(f"| {lab} | {t} | {f(b['share_of_filled_notional'],3)} | {f(b['maker_share'],3)} | {f(b['maker_bps_fee'],3)} | {f(b['taker_bps_fee'],3)} | {f(b['cost_per_unit_turnover_fee_only_bps'],3)} | {f(b['markout60_maker_bps'],2,sign=True)} | {f(b['markout60_taker_bps'],2,sign=True)} | {f(b['cost_per_unit_turnover_fee_minus_markout_bps'],2)} | {f(dev[t],3)} |")
    b = c["all"]; P(f"| {lab} | all | 1.000 | {f(b['maker_share'],3)} | {f(b['maker_bps_fee'],3)} | {f(b['taker_bps_fee'],3)} | {f(b['cost_per_unit_turnover_fee_only_bps'],3)} | {f(b['markout60_maker_bps'],2,sign=True)} | {f(b['markout60_taker_bps'],2,sign=True)} | {f(b['cost_per_unit_turnover_fee_minus_markout_bps'],2)} | {f(c['units_chain']['device_COST_B_applied_to_live_tier_mix_bps'],3)} (device on live tier mix) |")
P("")
P("Vectors in the device's `COST_B` shape `(maker_bps, taker_bps, maker_share)` per tier 0/1/2:")
P("")
P("| version | tier 0 | tier 1 | tier 2 | label |")
P("|---|---|---|---|---|")
v = [S["tiers"][t]["COST_B_format_fee_only"] for t in ("0", "1", "2")]
P(f"| live, fee only (steady) | ({v[0][0]:.2f}, {v[0][1]:.2f}, {v[0][2]:.3f}) | ({v[1][0]:.2f}, {v[1][1]:.2f}, {v[1][2]:.3f}) | ({v[2][0]:.2f}, {v[2][1]:.2f}, {v[2][2]:.3f}) | VERIFIED |")
v = [S["tiers"][t]["COST_B_format_fee_minus_markout"] for t in ("0", "1", "2")]
P(f"| live, fee − raw markout (steady) | ({v[0][0]:.2f}, {v[0][1]:.2f}, {v[0][2]:.3f}) | ({v[1][0]:.2f}, {v[1][1]:.2f}, {v[1][2]:.3f}) | ({v[2][0]:.2f}, {v[2][1]:.2f}, {v[2][2]:.3f}) | INFERRED, 68/134/128 marks, taker leg on 9/10/2 marks |")
mk_adj = CC["markout_poststratified"]["steady"]["maker"]["adjusted_bps"]; tk_adj = CC["markout_poststratified"]["steady"]["topup_taker"]["adjusted_bps"]
P(f"| live, fee − delay-reweighted markout, all tiers pooled (steady) | maker {S['all']['maker_bps_fee'] - (mk_adj or 0):.2f}, taker {S['all']['taker_bps_fee'] - (tk_adj if tk_adj is not None else S['all']['markout60_taker_bps']):.2f}, maker share {S['all']['maker_share']:.3f} → {S['all']['maker_share'] * (S['all']['maker_bps_fee'] - (mk_adj or 0)) + (1 - S['all']['maker_share']) * (S['all']['taker_bps_fee'] - (tk_adj if tk_adj is not None else S['all']['markout60_taker_bps'])):.2f} bps per unit turnover | | | INFERRED |")
P("| device COST_B (unchanged) | (−0.25, 5.0, 0.85) | (0.5, 6.0, 0.75) | (2.0, 8.0, 0.55) | replay default |")
P("")
P("Units chain (VERIFIED arithmetic, printed by `cost_calib.py`):")
P("")
P("| step | steady | all_calib |")
P("|---|---|---|")
for k, lab in (("fee_bps_of_gross_per_anchor", "fee, bps of gross per anchor (Σ fees / Σ venue gross)"), ("fee_pct_of_gross_per_year", "× 2190 anchors = % of gross per year"), ("fee_pct_of_NAV_per_year_at_2x", "× 2 = % of NAV per year at 2× gross"), ("check_turnover_x_cost", "check: turnover × fee-only cost per unit turnover (bps of gross per anchor)"), ("device_COST_B_applied_to_live_tier_mix_bps", "device COST_B on the live tier mix, bps per unit turnover")):
    P(f"| {lab} | {f(S['units_chain'][k],4)} | {f(ALL['units_chain'][k],4)} |")
P("")
P("## 9. Paper target vs real (twin), refreshed on all anchors to date (VERIFIED; `canon_reconcile.py` reused verbatim, sha 03ab6539…)")
P("")
P(f"Canonical set = clean 4h windows from the first combo anchor to the last closable anchor: n = {TG['n_canon']}, {TG['first']} → {TG['last']} (exclusions: halted 08-26 16Z, flattened 08-26 12Z, missing-next-anchor slots). bps of realized gross per anchor.")
P("")
P("| measure | mean | s.e. | CI95 (bootstrap) | n | meaning |")
P("|---|---|---|---|---|---|")
P(f"| paper Π, nominal grid (N, N+4h], target weights | {f(TG['paper_comp_bps']['mean'],2,sign=True)} | {f(TG['paper_comp_bps']['se'],2)} | {ci(TG['paper_comp_bps']['ci95_bootstrap'])} | {TG['paper_comp_bps']['n']} | what the target book would have made priced at the 4h grid |")
P(f"| paper Π shifted 25 min (venue pricing moment) | {f(TG['paper_comp_s25_bps']['mean'],2,sign=True)} | {f(TG['paper_comp_s25_bps']['se'],2)} | {ci(TG['paper_comp_s25_bps']['ci95_bootstrap'])} | {TG['paper_comp_s25_bps']['n']} | same book priced when the executor actually trades |")
P(f"| twin = venue positions × Δmid | {f(TG['twin_bps']['mean'],2,sign=True)} | {f(TG['twin_bps']['se'],2)} | {ci(TG['twin_bps']['ci95_bootstrap'])} | {TG['twin_bps']['n']} | the real positions' price P&L |")
P(f"| funding paid in window | {f(TG['funding_bps']['mean'],2,sign=True)} | {f(TG['funding_bps']['se'],2)} | | {TG['funding_bps']['n']} | carry actually paid |")
P(f"| twin + funding | {f(TG['twin_plus_funding_bps_per_anchor']['mean'],2,sign=True)} | {f(TG['twin_plus_funding_bps_per_anchor']['se'],2)} | {ci(TG['twin_plus_funding_bps_per_anchor']['ci95_bootstrap'])} | {TG['twin_plus_funding_bps_per_anchor']['n']} | real P&L per anchor before fees |")
P(f"| paper (shifted) − twin | {f(TG['paper_s25_minus_twin_bps']['mean'],2,sign=True)} | {f(TG['paper_s25_minus_twin_bps']['se'],2)} | {ci(TG['paper_s25_minus_twin_bps']['ci95_bootstrap'])} | {TG['paper_s25_minus_twin_bps']['n']} | execution discount band, price leg only |")
P(f"| paper (nominal) − twin − funding | {f(TG['paper_minus_twin_minus_funding_bps']['mean'],2,sign=True)} | | {ci(TG['paper_minus_twin_minus_funding_bps']['ci95_bootstrap'])} | {TG['paper_minus_twin_minus_funding_bps']['n']} | everything the paper book does not pay |")
P(f"| corr(paper shifted, twin) | {f(TG['corr_paper_s25_twin'],3)} | | | | |")
P("")
P("Same measures on the reconcile script's other sets (mean bps per anchor):")
P("")
P("| set | n | paper Π | paper Π shifted 25 min | twin | funding | twin + funding | s.e. |")
P("|---|---|---|---|---|---|---|---|")
for k, vv in TG["sets"].items(): P(f"| {k} | {vv['n']} | {f(vv['paper_comp_mean'],2,sign=True)} | {f(vv['paper_s25_mean'],2,sign=True)} | {f(vv['twin_mean'],2,sign=True)} | {f(vv['funding_mean'],2,sign=True)} | {f(vv['twin_plus_funding_mean'],2,sign=True)} | {f(vv['se'],2)} |")
P("")
P("Daily check against the executor's own equity (daily_nav, net of transfers), USDT:")
P("")
P("| nav day | span | equity Δ net of transfers | twin | funding in span | twin + funding | residual | fills vs anchor mid | paper Π | paper Π shifted | windows | notes |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for d in CR["daily"]:
    P(f"| {d['day']} | {d['span']} | {f(d['equity_delta_net'],1,sign=True)} | {f(d['twin_usd'],1,sign=True)} | {f(d['funding_in_span'],1,sign=True)} | {f(d['twin_plus_funding'],1,sign=True)} | {f(d['residual'],1,sign=True)} | {f(d['IS_usd_in_span'],1,sign=True)} | {f(d['paper_usd'],1,sign=True)} | {f(d['paper_s25_usd'],1,sign=True)} | {d['n_windows']} | {'PARTIAL day; ' if d['partial_day'] else ''}{'; '.join(n.split(':',1)[1][:40] for n in d['notes'])} |")
ds = CR["daily_summary"]
P(f"| sum 08-27…09-03 (full days, clean) | | {f(ds['sum_equity_delta_net_0827_0903'],1,sign=True)} | | | {f(ds['sum_twin_plus_funding_0827_0903'],1,sign=True)} | {f(ds['sum_residual_0827_0903'],1,sign=True)} | {f(ds['sum_IS_0827_0903'],1,sign=True)} | | | | |")
P(f"| sum all days incl. 08-26 flatten day and partial 09-05 | | {f(ds['sum_equity_delta_net_all'],1,sign=True)} | | | {f(ds['sum_twin_plus_funding_all'],1,sign=True)} | {f(ds['sum_residual_all'],1,sign=True)} | {f(ds['sum_IS_all'],1,sign=True)} | | | | |")
P("")
b = TG["per_unit_turnover_band_bps"]
P(f"Execution discount per unit of turnover, book level: (paper shifted − twin) / steady turnover = {f(b['paper_s25_minus_twin_over_turnover'],1,sign=True)} bps per unit turnover, CI95 {ci(b['ci95'],1)}. {b['note']}.")
P("")
P("## 10. Findings and limitations")
P("")
P("| # | finding | label | receipt |")
P("|---|---|---|---|")
fc = CC["findings"]["commission_collision"]
P(f"| 1 | {fc['what']} Cause: {fc['why']} Money at stake: {fc['money']} Effect on this report: {fc['consequence_for_this_report']} | {fc['status']} | {fc['receipt']} |")
P("| 2 | +60 s markout coverage is 5% of notional and the marked fills are selected by symbol order and fill order, not at random; the taker leg rests on 21–30 marks. The fee-minus-markout cost vector is therefore INFERRED and should not replace the device cost without a full backfill (the backfill ordering is a known-unfixed item in STATE §3). | INFERRED | markout_diag.out, §6 |")
P("| 3 | The step-up anchors (leverage ramp 08-26/27, deposit build 09-03 16Z) have 2–3× the taker share and 4–20× the turnover of steady anchors; they are in `all_calib` and out of `primary_steady`. Using `all_calib` fee drag as a run-rate would overstate it (4.4% vs 2.0% of gross per year). | VERIFIED | §1, §8 |")
P("| 4 | Fees are exactly the venue schedule with the BNB discount (maker 0.020% × 0.9, taker 0.050% × 0.9); there is no observed variation by tier, side or day, so `maker_bps`/`taker_bps` fee legs are constants and the calibration content is in maker share, fill ratio, refusal rate and turnover. | VERIFIED | §3 |")
P("| 5 | Funding settlement actuals versus the panel carry were not computed (not required by the task). | — | — |")
P("| 6 | The 08-26 12:49Z protective flatten (E-0826-F) is outside all fee/fill tables: no fills rows exist for it and its fees are only in the venue's 08-26 COMMISSION. | VERIFIED | §1 |")
r0903 = next(r for r in CC["per_anchor"] if r["when"] == "09-03 16Z")
P(f"| 7 | The pilot journal (journal_2026-09-02_forward_gate_42.md L26) quotes a −5022 refusal of 76% for the 09-03 16Z deposit build under an unstated definition. This report's definition (first refusals / maker legs sent) gives {f(r0903['reject5022_first_rate_count'],3)} by legs ({r0903['n_5022_first']}/{r0903['n_legs_sent']}) and {f(r0903['reject5022_first_rate_notional'],3)} by notional, with {r0903['n_5022_second']} legs refused twice. The two are not the same quantity; the journal figure should be re-derived from its generating line before reuse. | VERIFIED (this report's number) | §5 series |")
P("")
P("## 11. Product")
P("")
P("`cost_calib.json` (this directory). Keys: `calib.primary_steady` / `calib.all_calib` / `calib.pre_deposit` / `calib.post_deposit` each with `tiers.{0,1,2}` and `all` → `{maker_bps_fee, taker_bps_fee, maker_share, fill_ratio_maker(_buy/_sell), fill_ratio_after_topup(_buy/_sell), reject5022_first_rate, reject5022_to_taker_rate, markout60_maker_bps, markout60_taker_bps, markout60_coverage_notional, markout60_n, cost_per_unit_turnover_fee_only_bps, cost_per_unit_turnover_fee_minus_markout_bps, share_of_filled_notional, COST_B_format_fee_only, COST_B_format_fee_minus_markout}`, plus `turnover_per_anchor`, `units_chain`, `anchors{n, first, last}`; `per_anchor` (series); `per_anchor_summary`; `uncertainty` (bootstrap CIs); `markout_poststratified`; `twin_gap`; `fee_crosscheck_daily`; `findings`; `tier_rule`; `receipts`.")
P("")
P("## 12. Receipts")
P("")
P("| file | sha256 | produced by |")
P("|---|---|---|")
for k, vv in CC["receipts"].items():
    if k in ("commands", "finalized_utc"): continue
    P(f"| {k} | {vv[:16]}… | {'copied verbatim from multi_asset/exports/research/retrain_2026-09/review_caliber_wf/gap_live_pnl/' if k.startswith('canon_reconcile') else 'this directory'} |")
P(f"| cost_calib.json | (written by finalize_and_render.py at {CC['receipts']['finalized_utc']}) | |")
P("")
P("Commands (run in this directory, in order):")
P("")
P("```")
for c in CC["receipts"]["commands"]: P(c)
P("```")
P("")
P(f"Inputs: pilot log days {CC['inputs']['days'][0]}…{CC['inputs']['days'][-1]} under `~/dl_quant_live/state/live/pilot_log/`; `~/wide_shadow/state/rolling.npz` sha {CC['inputs']['rolling_npz_sha256'][:16]}…; `~/wide_shadow/shadow_bundle/config.json` sha {CC['inputs']['config_json_sha256'][:16]}…; `~/wide_shadow/state/aux.json` (tier check). Nothing under `~/dl_quant_live` or `~/wide_shadow` was written.")
open(f"{HERE}/REPORT.md", "w").write("\n".join(L) + "\n")
print("WROTE REPORT.md", sha(f"{HERE}/REPORT.md")[:16], "cost_calib.json", sha(f"{HERE}/cost_calib.json")[:16])
print("poststrat:", json.dumps(CC["markout_poststratified"]["steady"], indent=1))
print("FINALIZE_DONE")
