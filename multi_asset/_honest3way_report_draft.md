# Honest leak-free 3-way perp-y_600 measurement (fold-0, 2026-01)

> Created: 2026-06-19 | Session: honest3way | Status: in-progress | Supersedes: n/a
> Caliber: LEAK-FREE re-anchored perp y_600; uniform trainer (multi_asset/train/train_dual_lob.py)
> with FIXED sigma-gate fallback checkpoint. Single fold-0: test = 2026-01-01..2026-01-31,
> train_days=400, val_days=60, embargo=1, epochs=16, patience=6, ema_decay=0.995, seed=42.

## STATUS
TBD (filled at end)

## Commit
6cd84be (branch multi-asset): fix(dual): train_dual_lob fallback checkpoint
(sigma-gate no-save trap) + uniform 3-arm tdl configs. Files: train_dual_lob.py,
perp_base_tdl_roll.json, perp_dualsrc_tdl_roll.json.

## Note on sigma-gate trap (confirmed live on this run)
base Epoch 1/16: raw sigR (sigma_yhat/sigma_y) = 0.001 (<< 0.02) -> the hardcoded
sigma-gate would have saved NOTHING. This is EXACTLY the bug; the fallback handles it.

## Fallback-fix smoke (the bug this fixes)
Bug: on the leak-free perp target sigma_yhat/sigma_y stays < 0.02 for all epochs, so the
hardcoded sigma>=0.02 best-checkpoint gate (trainer_v2 + the replica in train_dual_lob)
saves NO checkpoint -> eval crashes FileNotFoundError: best_model.pt.

Fix (train_dual_lob.py): keep the sigma>=0.02 best-checkpoint logic, but ALSO track the
best-composite (0.5*Pearson+0.5*Spearman on val) state over ALL epochs regardless of sigma;
if no sigma>=0.02 epoch fired, persist that fallback as best_model.pt / ema_best.pt so eval
always runs. Record provenance + the saved checkpoint's sigma_yhat/sigma_y in metrics.json.

Smoke result (CPU, tiny BASE-arm fold, spot-64 LOBDatasetV2 path), CONFIRMED:
- best_model.pt + ema_best.pt SAVED despite sigma_yhat/sigma_y = 0.0006 (best) / 0.0002 (ema),
  both << 0.02.
- ckpt_provenance = {best_source: "fallback_low_sigma", ema_source: "fallback_low_sigma"}.
- best_ckpt_sigma_ratio = 0.0006 recorded in metrics.json.
- test_preds.npz + ema_test_preds.npz written -> eval RAN, no FileNotFoundError (exit 0).
- Log: "sigma-gate never fired (best raw sigma_yhat/sigma_y=0.0006 < 0.02); saved FALLBACK
  best_model.pt @ epoch 3."

Also confirms train_dual_lob handles use_perp_residual=false: routed to plain LOBDatasetV2
(no perp deep-book cache required), 64 feats + d_prior 6, model byte-identical to REG_arch parent.

## Data build (npz_dualsrclob for the fold-0 span)
Built 2024-09-26..2026-01-31 via build_dualsrclob_npz.py (8-proc parallel). Final cache =
490 days. 3 days SKIPPED by the builder's own offset-guard (constant perp-vs-spot timestamp
offset > 10s tolerance -> refuses to emit a possibly-misaligned day):
  2024-10-22 (offset 12s), 2024-11-23 (23s)  -> in the LOB train window
  2025-11-25                                  -> in the LOB val window
CAVEAT (measurement asymmetry): base/dualsrc read their own caches (no such skip), so the
LOB arm's fold-0 train/val window is shifted by ~3 days vs base/dualsrc (the fold builder
indexes the npz_dualsrclob day list). The TEST window (2026-01-01..01-31) is IDENTICAL for
all 3 arms -> the headline test-month comparison is clean; only LOB's training data differs
by ~3 boundary days (0.75%).

## THE 3-WAY TABLE (2026-01, EMA checkpoint)
(headline; CLEAN is the honest caliber, DENSE shown too)

TBD

## Per-arm fallback provenance + val sigma (from metrics.json)
- base: ckpt_provenance = {best: fallback_low_sigma, ema: fallback_low_sigma};
  best_ckpt_sigma_ratio=0.0085, ema_ckpt_sigma_ratio=0.00025; 6 epochs (early-stop);
  ARM base DONE rc=0, ema_test_preds.npz OK (eval RAN — the old chain crashed HERE).
  val (selection only): raw P=0.013 S=0.0145; EMA P=0.010 S=0.0079.
- dualsrc: TBD
- lob: TBD

NOTE: every arm's sigma_yhat/sigma_y is FAR below 0.02 on the leak-free perp target
(EMA especially: ~0.0003 -> EMA q50 is nearly constant). The fallback fix is what lets
eval run at all; but the EMA test IC must be read WITH this caveat (near-degenerate
spread => IC may be unreliable / latency-fragile, see single-asset record-caliber note).

## OBSERVATION
TBD

## CONCERNS
TBD
