# V4 Results (updated with no_attention win)

## Headline

**Disabling the patch attention block lifts V4 from 0.061 → 0.101 Pearson on y_180 fold 0 — above Ridge baseline for the first time.**

| Metric | V4 full | V4 no_attention | V3+RevIN | Ridge | Target |
|---|---:|---:|---:|---:|---:|
| Test Pearson (h=180) | 0.061 | **0.101** | 0.082 | 0.099 | 0.12 |
| Test Spearman | 0.089 | **0.107** | — | — | — |
| val_corr peak | 0.038 | **0.066** | — | — | — |

## How we got here — methodology

Running an 8-variant 100-day smoke sweep (1 min/variant) revealed that **patch attention was the single largest NEGATIVE contributor** — removing it 3× the test Pearson on smoke (0.029 → 0.084). Every other V4 module (PPNet gate, Path B raw LOB, RevIN, utility_rank loss) was net-positive.

Promoted to 700-day validation:
- val_corr peak 0.0662 at epoch 5 (vs 0.0383 for V4 full)
- Early stop epoch 13 (patience=8 from peak)
- **Test Pearson 0.1009**, Spearman 0.1072

## Why patch attention hurt

At 66K params with SNR < 1% on y_180, the 3K-param patch attention block (2-head MHA over 120 time patches) was learning train-set-specific attention patterns that didn't generalize. Disabling it leaves:

```
TCN output (B, 600, 32) → last timestep → PPNet gate → quantile head
```

Simpler pipeline, less overfit, better generalization. Matches CLAUDE.md principle: model capacity must match signal strength.

## Architecture still active in the winning config

Retained (all net-positive):
- RevIN per-instance normalization
- MaskNet **disabled** (was already V4 default)
- GDCN gated cross in 64-dim space (Path A)
- RawLOBEncoder with 1×1 channel mix + **level attention pool** (over 20 orderbook depths, Path B)
- TCN: 3 dilated causal convs (d=32, k=3, dil={1,2,4})
- PPNet regime gate (d_prior=6)
- Monotonic quantile head (q10 ≤ q50 ≤ q90)
- DUL loss: pinball + utility-rank (λ=0.3)

Removed (from V4 full):
- PatchEmbedding (time-slicing into 5-step patches)
- CausalPatchAttention (2-head, d_ff=64)
- AttentionPoolTokens (softmax pool over patches)

## Status

- Fold 0 at 700d: **test Pearson 0.1009** — confirmed
- Round 2 smoke sweep running (8 more variants on top of no_attention baseline) to search for +0.02 lift to hit 0.12 target
- Pending: 4-fold run of no_attention to get pooled IC

## Next actions

1. Wait for Round 2 smoke results (~10 min total): test smaller model, no GDCN, higher dropout, no level pool, no conv, etc.
2. If any variant beats 0.10 on smoke Pearson, promote to 700d validation
3. If no further improvement, run no_attention on all 4 folds for pooled IC
4. Decide whether to accept pooled ~0.10 (beats Ridge) or invest in more iteration toward 0.12
