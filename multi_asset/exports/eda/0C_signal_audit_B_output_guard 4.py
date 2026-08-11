#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item B: is there ANY guard on what inference EMITS?

Training has a σ-gate (σŷ/σy >= 0.02) because a collapsing model is the classic silent failure.
This asks the inference-side question: if the checkpoint were corrupt, or `norm_stats` misaligned
with the weights, what is the first thing that would go red, and at which layer?

Four measurements, all on the real anchor with the real frozen models:

  B1  SCALE-INVARIANCE. `inference.composite` z-scores every factor head across the cross-section
      before averaging. Multiply the model's output by any c > 0 and the emitted signal is
      unchanged. ⇒ σŷ is ~1 BY CONSTRUCTION and cannot report collapse. Verified by scaling the
      final layer of every head by 1e-6 and 1e+6.
  B2  THE ONLY THRESHOLD IS `col.std() > 1e-12` (inference.py:108). Where is the boundary, and how
      far is a healthy head from it?
  B3  MISALIGNED NORMALISATION. Give king s2's mu/sd (the shape a stats/checkpoint mix-up takes)
      and ask: does anything notice, and how much money moves?
  B4  A LEG THAT DIES IS SILENTLY ZEROED. legs.z() returns zeros for a non-finite input and
      legs.l1() passes zeros through, so a dead leg contributes 0 and the book is re-normalised to
      FULL gross from the survivors. Measured on the real anchor.

Read-only; all model mutations are on deep copies.
"""
import copy
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
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_B_output_guard.json")
GROSS = 25000.0


def main():
    import torch
    syms = LP.panel_symbols()
    kc, fc = LP.KlineCache(symbols=syms), LP.FundingCache(symbols=syms)
    ts, C, H, L, V, Q = kc.window(PB.WARMUP_RECOMMENDED_H)
    DV = PB.dvol30_from_qvol(np.asarray(Q, np.float64))
    rows = fc.as_rows(until_ms=int(ts[-1]))
    out = PB.build_dl_panel(ts, syms, C, H, L, V, Q, rows, DVOL30=DV, member=None)
    CH = out["CH"]
    member = PB.derive_member(DV, np.asarray(C, np.float64))
    anchor = len(ts) - 1
    mask = member[anchor].astype(np.float32)
    window = CH[anchor - INF.W + 1:anchor + 1].transpose(1, 0, 2)
    models, _ = INF.load()
    FUND_FIX, _, _ = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)

    res = {"anchor_ts_ms": int(ts[-1]), "n_members": int(mask.sum())}

    # ── baseline: the raw per-head scores BEFORE the z-mean (the quantity a σ-gate would need) ──
    base_comp, base_idx = {}, None
    head_stats = {}
    for name in ("king", "s2"):
        sc = models[name].factor_scores(window, mask)
        base = np.where(mask.astype(bool))[0]
        cols = sc[base]
        head_stats[name] = {
            "n_heads": int(cols.shape[1]),
            "raw_head_std": [float(cols[:, k].std()) for k in range(cols.shape[1])],
            "raw_head_std_min": float(min(cols[:, k].std() for k in range(cols.shape[1]))),
            "margin_over_1e-12_threshold_orders_of_magnitude": float(
                np.log10(min(cols[:, k].std() for k in range(cols.shape[1])) / 1e-12))}
        comp, idx = models[name].composite(window, mask)
        base_comp[name] = comp
        base_idx = idx
    res["B0_raw_head_spread_today"] = {
        **head_stats,
        "persisted_anywhere": False,
        "note": "these raw per-head standard deviations are the ONLY quantity in which an "
                "inference-side collapse could show up. They are computed, used for the "
                "drop-test, and thrown away — preds_latest.json records neither them nor any "
                "distributional summary of the emitted signal."}

    base_sym = [syms[j] for j in base_idx]
    base_book = LG.compose_book(base_comp["king"], base_comp["s2"],
                                FUND_FIX[anchor, base_idx], DV[anchor, base_idx])
    base_tgt = LG.to_notional(base_book["target_w"], base_sym, GROSS)

    # ── B1: scale-invariance — a collapsing (or exploding) model emits the SAME signal ─────────
    res["B1_scale_invariance"] = {}
    for c in (1e-6, 1e6):
        m2 = copy.deepcopy(models["king"])
        with torch.no_grad():
            for head in m2.model.factor_heads:
                head[-1].weight.mul_(c)
                head[-1].bias.mul_(c)
        comp2, _ = m2.composite(window, mask)
        res["B1_scale_invariance"][f"final_layer_x{c:g}"] = {
            "emitted_signal_max_abs_change": (None if comp2 is None
                                              else float(np.abs(comp2 - base_comp["king"]).max())),
            "emitted_sigma": None if comp2 is None else float(comp2.std()),
            "baseline_sigma": float(base_comp["king"].std()),
            "verdict": ("IDENTICAL — output scale carries no information"
                        if comp2 is not None and np.abs(comp2 - base_comp["king"]).max() < 1e-6
                        else "changed")}
    # ── B5: TOTAL MODEL DEATH. Every head emits ONE constant value for all 110 coins. The code
    # says this is handled ("Heads that are constant ... are dropped rather than divided by ~0",
    # inference.py:99). It is not. Traced through every layer that could stop it.
    m0 = copy.deepcopy(models["king"])
    with torch.no_grad():
        for head in m0.model.factor_heads:
            head[-1].weight.zero_()          # output = bias => one constant per head
    sc0 = m0.factor_scores(window, mask)
    b0 = np.where(mask.astype(bool))[0]
    heads = []
    for k in range(sc0.shape[1]):
        col = sc0[b0, k]
        heads.append({"n_distinct_values": int(len(np.unique(col))),
                      "value": float(col[0]),
                      "np_std_float32": float(col.std()),
                      "passes_the_1e-12_liveness_test": bool(col.std() > 1e-12)})
    comp0, _ = m0.composite(window, mask)
    leg0 = LG.z(comp0) if comp0 is not None else None
    dead_book0 = (LG.compose_book(comp0, base_comp["s2"], FUND_FIX[anchor, base_idx],
                                  DV[anchor, base_idx]) if comp0 is not None else None)
    tgt0 = (LG.to_notional(dead_book0["target_w"], base_sym, GROSS) if dead_book0 else {})
    d0 = np.array([tgt0.get(s, 0.0) - base_tgt.get(s, 0.0) for s in base_sym])
    res["B5_total_model_death_is_NOT_caught"] = {
        "what_was_done": "every factor head's final weight zeroed -> each head emits ONE constant "
                         "value for all 110 coins (bit-identical, n_distinct=1)",
        "per_head": heads,
        "n_heads_that_should_have_been_dropped": len(heads),
        "n_heads_actually_dropped": sum(1 for h in heads if not h["passes_the_1e-12_liveness_test"]),
        "root_cause": "np.std of 110 BIT-IDENTICAL float32 values is not 0 — it is ~3.7e-09, the "
                      "residue of a float32 mean. 3.7e-09 > 1e-12, so the head passes the "
                      "liveness test, and the very next line divides the ~0 numerator by that "
                      "~0 denominator, amplifying rounding noise to unit variance.",
        "layer1_composite_returns_none": comp0 is None,
        "layer2_emitted_signal": (None if comp0 is None else
                                  {"std": float(comp0.std()), "max_abs": float(np.abs(comp0).max()),
                                   "n_distinct": int(len(np.unique(comp0)))}),
        "layer3_compute_preds_would_raise": False,
        "layer3_note": "compute() raises only on `comp is None` and on members missing a score; "
                       "a constant vector satisfies both, so preds_latest.json IS written with a "
                       "fresh computed_ts and the staleness ladder never engages",
        "layer4_legs_z_output_l1": (None if leg0 is None else float(np.abs(leg0).sum())),
        "layer4_note": "legs.z() has its own sd>1e-12 test, in float64 on a constant input, so it "
                       "DOES return zeros — the dead model becomes a silently dead LEG (B4)",
        "layer5_book_gross_usdt": float(sum(abs(v) for v in tgt0.values())),
        "layer5_gross_reallocated_usdt": float(np.abs(d0).sum() / 2),
        "layer5_n_sign_flips": int(sum(1 for i, s in enumerate(base_sym)
                                       if base_tgt.get(s, 0.0) * tgt0.get(s, 0.0) < 0)),
        "verdict": "NOT CAUGHT AT ANY LAYER. A completely dead king model produces a fresh, "
                   "well-formed preds file; the anchor composes a book from the surviving three "
                   "legs and deploys the FULL gross. Nothing is logged, nothing alarms, and the "
                   "staleness ladder — the mechanism designed for 'no signal' — never sees a "
                   "stale file because a file was written.",
    }

    # ── B2: where the only threshold sits ────────────────────────────────────────────────────
    res["B2_head_drop_threshold"] = {
        "threshold": 1e-12,
        "source": "signal/inference.py:108  `if np.isfinite(col).all() and col.std() > 1e-12`",
        "healthy_head_min_std_today": head_stats["king"]["raw_head_std_min"],
        "orders_of_magnitude_above_threshold": head_stats["king"][
            "margin_over_1e-12_threshold_orders_of_magnitude"],
        "interpretation": "the threshold separates 'exactly constant' from everything else. A head "
                          "that has collapsed to float noise (std 1e-9, ~3 decades above the "
                          "threshold) is ACCEPTED and then re-scaled to unit variance by the same "
                          "line — collapse is converted into a full-strength signal."}

    # ── B3: misaligned normalisation stats ───────────────────────────────────────────────────
    mk = copy.deepcopy(models["king"])
    mk.mu, mk.sd = models["s2"].mu.copy(), models["s2"].sd.copy()
    comp_mis, idx_mis = mk.composite(window, mask)
    mis_sym = [syms[j] for j in idx_mis]
    mis_book = LG.compose_book(comp_mis, base_comp["s2"],
                               FUND_FIX[anchor, idx_mis], DV[anchor, idx_mis])
    mis_tgt = LG.to_notional(mis_book["target_w"], mis_sym, GROSS)
    allsym = sorted(set(base_tgt) | set(mis_tgt))
    d = np.array([mis_tgt.get(s, 0.0) - base_tgt.get(s, 0.0) for s in allsym])
    res["B3_misaligned_norm_stats"] = {
        "what_was_done": "king evaluated with s2's frozen mu/sd (a stats/checkpoint mix-up)",
        "emitted_sigma": float(comp_mis.std()), "baseline_sigma": float(base_comp["king"].std()),
        "looks_healthy": bool(0.5 < comp_mis.std() < 2.0),
        "pearson_vs_correct_king": float(np.corrcoef(comp_mis, base_comp["king"])[0, 1]),
        "spearman_vs_correct_king": float(
            np.corrcoef(np.argsort(np.argsort(comp_mis)),
                        np.argsort(np.argsort(base_comp["king"])))[0, 1]),
        "gross_reallocated_usdt": float(np.abs(d).sum() / 2),
        "largest_single_move_usdt": float(np.abs(d).max()),
        "n_sign_flips": int(sum(1 for s in allsym
                                if base_tgt.get(s, 0.0) * mis_tgt.get(s, 0.0) < 0)),
        "any_guard_that_fires": "none — mu/sd are hashed into preds.models[] and the frozen-input "
                                "census compares the FILE against MANIFEST.json, so a file that is "
                                "intact but paired with the wrong weights passes every check",
    }

    # ── B4: a dead leg is silently zeroed and the book re-normalised to full gross ────────────
    dead = np.full_like(base_comp["king"], np.nan)
    dead_book = LG.compose_book(dead, base_comp["s2"],
                                FUND_FIX[anchor, base_idx], DV[anchor, base_idx])
    dead_tgt = LG.to_notional(dead_book["target_w"], base_sym, GROSS)
    d2 = np.array([dead_tgt.get(s, 0.0) - base_tgt.get(s, 0.0) for s in base_sym])
    res["B4_dead_leg_is_silent"] = {
        "what_was_done": "king leg fed all-NaN (leg dead); s2/funding/size untouched",
        "king_leg_l1_norm_after": float(np.abs(dead_book["legs_unit"]["king"]).sum()),
        "book_gross_usdt_before": float(sum(abs(v) for v in base_tgt.values())),
        "book_gross_usdt_after": float(sum(abs(v) for v in dead_tgt.values())),
        "gross_reallocated_usdt": float(np.abs(d2).sum() / 2),
        "n_sign_flips": int(sum(1 for i, s in enumerate(base_sym)
                                if base_tgt.get(s, 0.0) * dead_tgt.get(s, 0.0) < 0)),
        "verdict": "a leg carrying w=0.30 can vanish and the book still deploys the FULL 25,000 "
                   "USDT gross, re-weighted onto the surviving legs, with no size reduction and "
                   "no alarm. `legs.l1()` returns its input unchanged when the gross is < 1e-9, "
                   "so the dead leg is a silent zero rather than an error.",
    }

    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
