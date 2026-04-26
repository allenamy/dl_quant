# y_1800 End-to-End Calibration + Backbone A/B/C — Overview

**Branch:** `siyu_y1800_e2e_calib` (off `siyu_v4_y600_push`)

## Two Goals

**G1 — End-to-end β-calibration:** Train-time loss term forces `β → 1` (i.e. `σ_ŷ ≈ ρ·σ_y`). Live trading consumes ŷ directly without post-hoc calibration. Validated first on V4 y_600 (controlled, architecture frozen — only loss changes).

**G2 — y_1800 (30-min horizon) exploration:** Establish whether DL's non-linear edge over Ridge (which on y_600 was 1.5-3.7×) is even larger at longer horizons, and whether cost-economics turn positive (10-20 bps per trade vs 4-8 bps cost). Backbone A/B/C compares EMA pool, GRU, and isolated Mamba-2 against the V4 baseline (last-timestep slice).

## Detailed Plan

`docs/superpowers/plans/2026-04-25-y1800-e2e-calib.md` — 23 tasks, 8 phases, with explicit gates between phases.

## Key Constraints

- **No post-hoc tricks.** Seed ensemble, val-fit reweighting, SWA blending excluded per project policy. Calibration via training loss, not via post-fit β scaling (post-hoc still available as safety net but not the primary mechanism).
- **No simultaneous-multi-component changes.** V5-LH failed because Mamba + decorr + focal + side-aware + cross-path were all changed at once. This plan changes ONE thing at a time, with gates.
- **Strict pre-declared gates.** Any feature/architecture must pass +0.005 ΔP on Ridge walk-forward (or DL gate) before consuming pod time at the next phase.
- **Cross-sectional IC interface stubbed.** Single-asset doesn't activate it, but the loss module is wired now so multi-asset extension later is plug-and-play.

## Status

See task list in repo (TaskList tool) and gate-decision files written under `experiments/y600_calib/` and `experiments/y1800_calib/` for live progress.
