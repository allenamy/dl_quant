# V4 y_600 — Post-processing Push Report

## Variants — pooled clean metrics

| Variant | N | Pearson | Pearson CI95 | Spearman | Spearman CI95 | DirAcc |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 4871 | +0.0562 | [+0.0276, +0.0844] | +0.0744 | [+0.0452, +0.1023] | 0.538 |
| baseline_swa5 | 4871 | +0.0656 | [+0.0348, +0.0964] | +0.0786 | [+0.0492, +0.1060] | 0.539 |
| block_b_best | 4871 | +0.0560 | [+0.0278, +0.0843] | +0.0734 | [+0.0471, +0.0998] | 0.536 |
| block_b_ema | 4871 | +0.0597 | [+0.0301, +0.0897] | +0.0773 | [+0.0477, +0.1060] | 0.538 |
| **rank_blend** | 4871 | +0.0766 | [+0.0488, +0.1047] | +0.0856 | [+0.0558, +0.1124] | 0.493 |

## Per-fold (clean)

| Fold | baseline P | baseline_swa5 P | block_b_best P | block_b_ema P | baseline S | baseline_swa5 S | block_b_best S | block_b_ema S |
|---|---|---|---|---|---|---|---|---|
| fold_0 | +0.0328 | +0.0473 | +0.0934 | +0.0899 | +0.0671 | +0.0729 | +0.1081 | +0.1052 |
| fold_1 | +0.0780 | +0.0850 | +0.0418 | +0.0659 | +0.0718 | +0.0738 | +0.0592 | +0.0696 |
| fold_2 | +0.0623 | +0.0652 | +0.0453 | +0.0543 | +0.0874 | +0.0913 | +0.0774 | +0.0800 |

## Tail DirAcc (baseline)

- threshold: |z| > 2.0 (19.37 bps equivalent), N tail: 6000
- DirAcc: 0.541  Pearson: +0.0870  Spearman: +0.0895

## Verdict: PARTIAL

Winning variant: **rank_blend**  (P=+0.0766 S=+0.0856)
