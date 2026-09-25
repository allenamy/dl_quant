> **Created:** 2026-09-25 18:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** feasibility check only (lead ruling: check, do not run) — verdict **SEGMENT 0 CANNOT BE REBUILT** | **Invalidated by:** a retained copy of ~/wide_shadow/state/aux.json (prev_rec) for any anchor 09-16 12Z … 09-17 08Z turning up

# Segment 0 (09-16 12Z … 09-17 08Z, 6 anchors, layered L2 −3,079.7 USDT): feasibility
Criterion (lead): the base arm must reproduce that anchor's production target_live bitwise; no approximation.

## What the combo stage that ran then reads
- Code: combo_stage b5c698f9 (in place from 09-02 12Z to the fp2-6b swap-in at 09-17 12:59Z; PRODUCTION_INTERVENTION_LEDGER L8/L16).
- Per anchor A, from tree_old_prefp26b/fea171/combo_stage.py:
  - L13–16: `aux.json` → `prev_rec` (anchor_ts, members, **legz king/rev24/fund**, **sm, sm_idx**, fund_z_old, sel_idx, …);
  - L18: `rolling.npz` (5m buffer);
  - L26–27: `weights/{A−4h}.npz`;
  - L29: `leg_returns_live.json` (msharpe_look 900);
  - L45: `target_live/{A}.json` universe;
  - the King file; state_H.

## Inventory (each checked by path)
| input | 09-16 08Z … 09-17 08Z | source |
|---|---|---|
| production target_live/{A}.json (baseline target) | present, 7/7 | ~/wide_shadow/state/target_live |
| producer King file target_live_king/{A}.json | present, 7/7 | ~/wide_shadow/state/target_live_king |
| combo EMA state state_H_{kc,fc,f10}_{A}.npz | present, 7/7 (incl. the anchor before) | ~/wide_shadow/fea171 |
| weights/{A}.npz, weights_combo, target_combo, target_blend | present | ~/wide_shadow/state (outputs, not inputs) |
| code tree b5c698f9 | retrievable by sha | ~/cc_tmp/nc_20260923/tree_old_prefp26b (+ backup `.pre_fp2-6b_20260917T1259Z_b5c698f9`) |
| **state/snap/{A}** (aux.json, rolling.npz, leg_returns_live.json) | **absent, 0/6** | the first snapshot is 09-17 12Z (49 snaps, 09-17 12Z … 09-25 16Z) |
| **aux.json prev_rec as of A** | **no retained copy** | searched ~/cc_tmp, ~/wide_shadow, ~/dl_quant_live and the research repo for aux*.json: 7 copies, mtimes 08-25, 08-25, 09-14 12:01Z, 09-17 16:16Z (snap 12Z), 09-23 ×2, 09-25. None in [09-16 08Z, 09-17 08Z]. Time Machine: no destination configured. |

## Could the missing inputs be rebuilt from later state?
- rolling.npz: the 09-17 12Z buffer covers 08-08 12:05Z … 09-17 12:00Z (11,520 rows). Truncating it to A leaves a buffer up to 288 rows shorter at the start than the one production held. Rows could also have been refetched since. Unverified either way.
- leg_returns_live.json: capped at 950 entries (still 950 today), no timestamps. Truncation needs an unverified "one append per anchor, no rewrites".
- **prev_rec (legz, sm, sm_idx): decisive.** Written by the upstream shadow loop at each anchor and overwritten at the next; no per-anchor archive exists (members_hist.npz has members only; regime_dash has w3 only). Rebuilding it means replaying the upstream producer stage, whose own state (aux.ema, prev_close, H) is also not archived for those anchors — an unbounded chain back in time. The one recorded producer replay (Phase 1, b9c1f3c41) was not bitwise even with its inputs: King ≤ 9.3e-10, combo 0/41 at ≤ 1e-6.

## Verdict
**Segment 0 cannot be rebuilt.** Base-arm bitwise reproduction of target_live is not reachable for 09-16 12Z … 09-17 08Z: aux.json prev_rec for those anchors was never retained, and the only way to regenerate it is not bitwise. No approximation is offered. Denominator of the counterfactual over the 46-anchor main drawdown: 40 anchors covered (segment 1: 25, segment 2: 15), 6 not covered (−3,079.7 of −9,278.3 layered L2, 33%).
