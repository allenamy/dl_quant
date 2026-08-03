#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item A: what a DATA GAP becomes by the time it reaches an order.

Question posed: "a symbol's price series breaks for 30 minutes / some hours — what are its
DVOL30 / momentum / vol factors then? Does it get a number that LOOKS normal?"

Method: take the real live panel cache, run the real build (live_panel -> panel_build ->
frozen king/s2 -> legs.compose_book), then re-run it with hourly bars DELETED for one member
symbol, and measure what changed — in the raw channels, in the model's own prediction, in OTHER
symbols' predictions, and in the final USDT target vector.

Scenarios: a 1h hole, a 6h hole and a 30h hole ending one hour BEFORE the anchor (so the symbol
keeps a fresh last bar and stays a member), plus a hole ON the anchor row as a control.

Read-only w.r.t. ~/dl_quant_live; all arrays are copies.
"""
import json
import os
import sys

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
for p in (os.path.join(LIVE, "signal"), os.path.join(LIVE, "vendor"), os.path.join(LIVE, "live")):
    sys.path.insert(0, p)

import funding_panel as FP          # noqa: E402
import inference as INF             # noqa: E402
import legs as LG                   # noqa: E402
import live_panel as LP             # noqa: E402
import panel_build as PB            # noqa: E402

OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_A_gap_propagation.json")
GROSS = 25000.0
FIELDS = ("close", "high", "low", "volume", "quote_vol")


def build(ts, syms, C, H, L, V, Q, rows, models, span_table=None):
    """The live chain, verbatim: DVOL30 -> 32ch panel -> member -> king/s2 -> 4-leg book."""
    DV = PB.dvol30_from_qvol(np.asarray(Q, np.float64))
    err = None
    try:
        out = PB.build_dl_panel(ts, syms, C, H, L, V, Q, rows, DVOL30=DV, member=None)
    except Exception as e:
        return {"blocked": f"{type(e).__name__}: {str(e)[:200]}"}
    CH = out["CH"]
    member = PB.derive_member(DV, np.asarray(C, np.float64))
    anchor = len(ts) - 1
    mask = member[anchor].astype(np.float32)
    window = CH[anchor - INF.W + 1: anchor + 1].transpose(1, 0, 2)
    comps = {}
    for name in ("king", "s2"):
        comp, base = models[name].composite(window, mask)
        comps[name] = {"idx": base, "val": comp}
    FUND_FIX, _, _ = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)
    base = comps["king"]["idx"]
    king = comps["king"]["val"]
    s2 = comps["s2"]["val"]
    fund = FUND_FIX[anchor, base]
    dvol = DV[anchor, base]
    bk = LG.compose_book(king, s2, fund, dvol)
    tgt = LG.to_notional(bk["target_w"], [syms[j] for j in base], GROSS)
    return {"blocked": err, "anchor": anchor, "member_idx": base, "CH": CH, "DV": DV,
            "king": king, "s2": s2, "fund": fund, "target": tgt,
            "ch_names": out["ch_names"], "n_members": int(mask.sum()),
            "caliber_gate": out["provenance"].get("caliber_gate")}


def main():
    syms = LP.panel_symbols()
    kc, fc = LP.KlineCache(symbols=syms), LP.FundingCache(symbols=syms)
    ts, C, H, L, V, Q = kc.window(PB.WARMUP_RECOMMENDED_H)
    rows = fc.as_rows(until_ms=int(ts[-1]))
    models, _ = INF.load()

    base = build(ts, syms, C, H, L, V, Q, rows, models)
    anchor = base["anchor"]
    base_sym = [syms[j] for j in base["member_idx"]]
    res = {"panel_hours": int(len(ts)), "anchor_ts_ms": int(ts[-1]),
           "n_members_baseline": base["n_members"],
           "baseline_target_gross_usdt": float(sum(abs(v) for v in base["target"].values())),
           "scenarios": {}}

    # ── how the cache already looks: are there gaps TODAY? ──────────────────────────────────
    nan_close = np.isnan(C)
    per_sym = nan_close.sum(0)
    res["cache_state_today"] = {
        "hourly_index_gaps": int((np.diff(ts) != 3_600_000).sum()),
        "symbols_with_any_missing_bar": int((per_sym > 0).sum()),
        "symbols_fully_absent": [syms[j] for j in np.where(per_sym == len(ts))[0]],
        "symbols_partially_missing": [(syms[j], int(per_sym[j]))
                                      for j in np.where((per_sym > 0) & (per_sym < len(ts)))[0]],
        "note": "the window() guard raises only on gaps in the SHARED hourly index; a per-symbol "
                "hole leaves the index intact and is not checked anywhere."}

    # pick liquid members to hole out (worst case = a name carrying real weight)
    order = sorted(base["target"], key=lambda s: -abs(base["target"][s]))
    victims = [s for s in ("BTCUSDT", "ETHUSDT", order[0]) if s in base_sym]
    victims = list(dict.fromkeys(victims))

    for victim in victims:
        jv = syms.index(victim)
        for hole_h, end_off in ((1, 1), (6, 1), (30, 1), (1, 0)):
            tag = f"{victim}:{hole_h}h_hole_ending_t-{end_off}"
            C2, H2, L2, V2, Q2 = (x.copy() for x in (C, H, L, V, Q))
            hi = anchor - end_off + 1
            lo = max(0, hi - hole_h)
            for arr in (C2, H2, L2, V2, Q2):
                arr[lo:hi, jv] = np.nan
            got = build(ts, syms, C2, H2, L2, V2, Q2, rows, models)
            if got.get("blocked"):
                res["scenarios"][tag] = {"outcome": "BLOCKED", "detail": got["blocked"]}
                continue
            new_sym = [syms[j] for j in got["member_idx"]]
            still_member = victim in new_sym
            entry = {"outcome": "BUILT_AND_SHIPPED",
                     "victim_still_a_member": still_member,
                     "n_members": got["n_members"],
                     "any_nan_in_model_input": bool(
                         not np.isfinite(got["CH"][anchor - INF.W + 1:anchor + 1]).all()),
                     "caliber_gate_verdict": (got["caliber_gate"] or {}).get(
                         "structural", {}).get("verdict")}
            # raw channel values for the victim at the anchor row: do they look plausible?
            chn = got["ch_names"]
            watch = ["ret_24h", "rvol_6h", "logqvol", "xsr_rvol", "xsr_ret24", "xsr_mom72",
                     "mom_72h" if "mom_72h" in chn else chn[1]]
            entry["victim_channels_at_anchor"] = {
                c: {"baseline": float(base["CH"][anchor, jv, chn.index(c)]),
                    "with_gap": float(got["CH"][anchor, jv, chn.index(c)])}
                for c in watch if c in chn}
            entry["victim_dvol30_at_anchor"] = {
                "baseline": float(base["DV"][anchor, jv]),
                "with_gap": float(got["DV"][anchor, jv]),
                "pct_change": float(100 * (got["DV"][anchor, jv] / base["DV"][anchor, jv] - 1))}
            # prediction deltas — victim's own, and the CONTAGION onto everyone else
            common = [s for s in base_sym if s in new_sym]
            bi = {s: i for i, s in enumerate(base_sym)}
            ni = {s: i for i, s in enumerate(new_sym)}
            dk = np.array([got["king"][ni[s]] - base["king"][bi[s]] for s in common])
            ds = np.array([got["s2"][ni[s]] - base["s2"][bi[s]] for s in common])
            if still_member:
                entry["victim_pred_delta"] = {
                    "king": float(got["king"][ni[victim]] - base["king"][bi[victim]]),
                    "s2": float(got["s2"][ni[victim]] - base["s2"][bi[victim]])}
            others = [i for i, s in enumerate(common) if s != victim]
            entry["contagion_to_other_symbols"] = {
                "n_others": len(others),
                "max_abs_king_delta": float(np.abs(dk[others]).max()) if others else None,
                "mean_abs_king_delta": float(np.abs(dk[others]).mean()) if others else None,
                "max_abs_s2_delta": float(np.abs(ds[others]).max()) if others else None,
                "note": "king/s2 are z-scored across the cross-section, so 1.0 = one sd of the "
                        "signal itself."}
            # final money
            allsym = sorted(set(base["target"]) | set(got["target"]))
            d = np.array([got["target"].get(s, 0.0) - base["target"].get(s, 0.0) for s in allsym])
            worst = allsym[int(np.abs(d).argmax())]
            entry["target_notional_change_usdt"] = {
                "gross_reallocated": float(np.abs(d).sum() / 2),
                "victim_leg": float(got["target"].get(victim, 0.0) - base["target"].get(victim, 0.0)),
                "largest_single_move": {"symbol": worst, "usdt": float(d[np.abs(d).argmax()])},
                "n_symbols_moved_gt_50usdt": int((np.abs(d) > 50).sum())}
            res["scenarios"][tag] = entry

    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
