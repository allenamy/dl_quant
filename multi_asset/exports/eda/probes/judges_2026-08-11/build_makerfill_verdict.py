import json, numpy as np
EDA = "multi_asset/exports/eda/"
calib = json.load(open(EDA + "makerfill_calib_raw.json"))
app = json.load(open(EDA + "makerfill_apply_raw.json"))
pc = calib["per_coin"]

spectrum = {s: dict(hourly_notl_M=round(pc[s]["hourly_notl_usd"] / 1e6, 1), spread_bps=pc[s]["spread_bps"],
                    markout_bps=pc[s]["markout_mean_bps"],
                    eff_if_fill_bps=round(-pc[s]["markout_mean_bps"] - pc[s]["half_spread_bps"], 3))
            for s in sorted(pc, key=lambda x: -pc[x]["hourly_notl_usd"])}


def yrs(tag):
    r = app["scenarios"][tag]
    return {y: dict(net=r[y]["net_sh"], cost=r[y]["eff_cost_bps_side"], fill=r[y]["mean_fill_rate"])
            for y in ["2022", "2023", "2024", "2025", "2026"]}


verdict = dict(
    title="Track-1 maker-fill conservative replay calibration — pilot verdict", created="2026-07-12",
    auditor="0C",
    one_line=("PILOT WORTH IT. Under a CONSERVATIVE maker-fill lower bound (join-at-back queue, trade-driven "
              "depletion only, NO spread-capture profit credited, small-tier haircuts), the xattn book's "
              "effective cost is ~1.5-1.9 bps/side (full) / ~1.0-1.6 (calib-grounded @k300) / ~0.4-1.0 "
              "(calib-grounded @k900) — FAR below the 5 bps taker floor — and net Sharpe stays +9 to +22 "
              "EVERY year incl weak 2022/2026. The calibration-GROUNDED book (>=$4M/h, ZERO extrapolation) is "
              "already net-positive, so the verdict does NOT depend on the small-coin extrapolation."),
    calibration=dict(
        ground="14 mega-cap bar_1s (5-lvl LOB + trade-flow), 12 days across 2022-2025",
        method=("post passive at touch; queue-ahead = full L1 notional (join-at-back, CONSERVATIVE); deplete by "
                "opposite-side taker NOTIONAL only, cancels excluded (CONSERVATIVE); our full order O must clear "
                "on top of L1; fill within working window k; adverse-selection markout D=60s at fill."),
        liquidity_spectrum_M=[spectrum[s]["hourly_notl_M"] for s in spectrum],
        spectrum=spectrum,
        finding=("fill-rate curve is LIQUIDITY-INVARIANT in f=order/hourly-notl (BTC≈TRX): >0.95 for f<=0.5%, "
                 "collapses past f~2%; adverse markout tiny (-0.03..-0.38 bps); half-spread capture 0.01 (BTC) to "
                 "1.1 bps (small) — so a FILLED maker order is cheap-to-profitable, but we conservatively floor "
                 "its cost at 0 (no MM profit booked).")),
    extrapolation_caveat=dict(
        calib_floor_usd=4.0e6, wide_median_notl_M=1.25, n_coins_below_floor="109/140",
        note=("★ 109/140 wide coins sit BELOW the $4M/h calibration floor (median wide coin $1.25M/h). The SMALL "
              "tier is EXTRAPOLATED with explicit conservative haircuts: fill-rate x0.7, adverse markout = p25 "
              "(worse tail), spread-capture credit x0.5. DECISIVE: the calib-GROUNDED book (>=$4M/h, ~31 coins, "
              "NO extrapolation) is independently net-positive (net Sharpe 9-16), so the extrapolated tail is a "
              "marginal drag, NOT load-bearing — the pilot verdict is robust to the extrapolation.")),
    conservative_net_sharpe=dict(
        full_book_AUM10M_k300=yrs("AUM10M_k300_full"),
        megamid_AUM10M_k300=yrs("AUM10M_k300_megamid"),
        calib_grounded_AUM10M_k300=yrs("AUM10M_k300_calib"),
        calib_grounded_AUM10M_k900=yrs("AUM10M_k900_calib"),
        all_scenarios=app["scenarios"]),
    reads=[
        "Effective cost ~1.5-1.9 bps/side (full, conservative floor) vs 5 bps taker used in the coronation — "
        "maker execution roughly HALVES-to-THIRDS the cost; net Sharpe recovers to near-gross.",
        "megamid >= full and calib-grounded is HIGHER than full in 2026 (weak year) — dropping the illiquid "
        "small tail helps net (it is capacity-suppressed + expensive-to-fill, as the 0C capacity table found).",
        "k=900 (15-min working) vs k=300: fill-rate 0.5-0.84 vs 0.3-0.5, cost 0.4-1.0 vs 1.0-1.6 bps for the "
        "calib book — working orders longer is the operational cost lever.",
        "Higher AUM ($5M->$25M) lowers fill-rate (bigger orders vs volume) and raises cost modestly; net Sharpe "
        "drifts down slowly (calib $5M 9.6-19.5 -> $25M 9.0-18.7 @k300). No cliff in the tested range."],
    pilot_proposal=dict(
        recommendation="OPEN a $2-5M live maker-fill pilot on the calib-grounded / mega+mid core.",
        book="calib-grounded core (>=$4M/h, ~31 coins, fully validated) or mega+mid (>=$0.89M/h); the <$0.89M "
             "small tail is OPTIONAL (marginal, extrapolated-uncertain) — start WITHOUT it.",
        size="$2-5M gross to start (net Sharpe ~flat across $5-25M; cost rises slowly). Scale to $10-25M as the "
             "realized fill-rate/cost confirm the calibration.",
        working="post passive at touch, work k=300-900s (5-15 min), taker-complete the residual.",
        success_criteria=["realized fill-rate >= calibration (>=0.40 @k300 / >=0.65 @k900 on the core book)",
                          "realized effective cost <= 2.0 bps/side",
                          "realized adverse-selection markout (D=60s) within ~2x the measured -0.05..-0.4 bps",
                          "realized net edge >= this conservative bound"],
        stop_loss=["effective cost > 3.5 bps/side (approaching taker) sustained",
                   "fill-rate << calibration (< half) at the working window",
                   "adverse markout > 1 bp/side (informed-flow pickoff worse than measured)"]),
    honesty_caveats=[
        "CONSERVATIVE FLOOR credits NO spread capture (real book likely earns some -> upside).",
        "1s bar aggregation ignores within-second trade/cancel ordering (mildly optimistic on adverse ordering); "
        "offset by join-at-back + cancels-excluded (conservative on fills). Net: order-of-magnitude, bracketed.",
        "adverse selection measured at D=60s markout; longer-horizon informed pickoff could be worse, but the "
        "measured markout is small (<0.4 bps) so even 2x is minor.",
        "2026 has NO bar_1s data (ends 2025-11) -> 2026 uses the extrapolated law; flag as model, not observed.",
        "net-Sharpe MAGNITUDE (9-22) retains the frequency x breadth x participation-model caveat from the "
        "coronation/capacity docs; the DEPLOYABLE conclusion is the effective COST (~1.5 bps conservative) << "
        "gross edge, i.e. the book survives realistic maker execution — not the Sharpe number itself."])
json.dump(verdict, open(EDA + "makerfill_calibration.json", "w"), indent=2, default=str)
print("SAVED", EDA + "makerfill_calibration.json")
print("calib-grounded @k300 $10M net:", [yrs("AUM10M_k300_calib")[y]["net"] for y in ["2022", "2023", "2024", "2025", "2026"]])
