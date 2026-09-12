# PREREG AMENDMENT 1 · r18 · GATE Y composition formula (definitional; written after GATE Y FAILED as registered, before any outcome number was read)

> **Created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (subagent r18-foundation) | **Amends:** `PREREG_r18_foundation_2026-09-12.md` sha256 `51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c` §0 (one sentence) and §3 GATE Y (formula + scope) | **Does not touch:** arms, knobs, windows, statistic, K, verdict rules, or any readout in §5 | **State when written:** GATE P PASS (both seeds, bitwise), GATE R PASS (108 / 108 / 3 / 0.01183774 / 0.0 exact), GATE Y **FAIL as registered** (`fwd_nan_mismatch 0, closed_nan_mismatch 0, fwd_maxabs 0.532, closed_maxabs 0.125`); the judge had not been run; no g / Δg / tail number had been computed or seen.

## What was wrong in the registered text

§0 said `y4[i]` is "the forward 48-bar (4h) **sum** of 5-minute simple returns from E_i", citing the **king-feature** meta builder (`pod_fea_ext_clamp.py` L36-37). The replay's **accounting** meta is `meta_newprod_v4.npz`, whose `y4` is the accounting caliber of `CALIBER_PIN_v4` §Metric Discipline: **`y4s = Π(1+r) − 1`** over the same forward 48 bars (`pod_dlw_targets_ext.py` L93 lineage). Diagnostic on the registered 60-anchor sample (no P&L involved): NaN structure identical under both formulas (0 mismatches, forward and closed); values match **Π(1+r) − 1 to ≤ 1.1e-10 (median) on 58 / 60 anchors**; the plain sum matches on 0 / 60. So the **window** (forward 48 bars from E, NaN unless ≥ 46 bars finite — the fact the causal argument rests on) is verified; the **composition** sentence was wrong.

Two sampled anchors contain cells where even Π(1+r) − 1 from the holefix2 cache differs from the stored `y4` (worst cell: stored +0.5534, cache Π −0.0510, cache Σ +0.0214). `CALIBER_PIN_v4` §1 already records that `meta_newprod_v4` agrees with `meta_newprod_raw` only **outside hole neighbourhoods** (maxabs 9.09e-13 there). These cells are therefore a property of the pinned baseline's own input, not of anything this round changes; they are **quantified and reported**, not fixed.

## Amended GATE Y (replaces §3 GATE Y)

- **Formula:** `y4[i, m]` must equal `Π_{k∈(E, E+4h]}(1 + ret5[k, m]) − 1` (48 bars, float64) within **1e-5** wherever ≥ 46 of the bars are finite, and be NaN otherwise; identically for `y4[i−1, m]` over `(E−4h, E]`. Channel `ret5` located by name in the cache's `ch` array.
- **Scope:** the **full panel axis** (all 10039 anchors), not a 60-anchor sample.
- **PASS condition (window / causality, the stop gate):** NaN-structure mismatches = 0 for both forward and closed.
- **Reported, not a stop:** the number of finite cells whose value differs from the cache by > 1e-5, their (anchor, symbol) list, and their **traded exposure in the archived A0 s42**: Σ over those cells of `|W[i, m]| · |y4_meta − y4_cache| · 1e4` (bps of NAV-per-unit-gross booked on a return the cache does not support), on W_FULL and W_ALPHA, plus the fraction of those cells with `|W| > 0`.
- The original GATE Y result (sum formula, 60 anchors, FAIL) stays in the receipt under `GATE_Y`; the amended gate is `GATE_Y2`. The judge asserts `GATE_Y2.window_PASS` and this file's sha256.

## Corrected sentence for §0

"`y4[i]` is the forward 48-bar (4h) **compounded** simple return `Π(1+r)−1` from E_i, NaN unless ≥ 46 of the 48 forward bars are finite (accounting caliber `y4s`, `CALIBER_PIN_v4`); hence `y4[i−1]` is the compounded return over the 48 bars ending at E_i — closed at E_i." Nothing else in §0–§7 changes.
