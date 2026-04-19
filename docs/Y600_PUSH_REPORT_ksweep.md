# V4 y_600 — Post-processing Push Report

## Variants — pooled clean metrics

| Variant | N | Pearson | Pearson CI95 | Spearman | Spearman CI95 | DirAcc |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 4871 | +0.0562 | [+0.0276, +0.0844] | +0.0744 | [+0.0452, +0.1023] | 0.538 |
| swa_k5 | 4871 | +0.0656 | [+0.0348, +0.0964] | +0.0786 | [+0.0492, +0.1060] | 0.539 |
| swa_k3 | 4871 | +0.0607 | [+0.0301, +0.0921] | +0.0730 | [+0.0432, +0.1005] | 0.537 |
| swa_k7 | 4871 | +0.0659 | [+0.0358, +0.0964] | +0.0770 | [+0.0478, +0.1048] | 0.538 |

## Per-fold (clean)

| Fold | baseline P | swa_k5 P | swa_k3 P | swa_k7 P | baseline S | swa_k5 S | swa_k3 S | swa_k7 S |
|---|---|---|---|---|---|---|---|---|
| fold_0 | +0.0328 | +0.0473 | +0.0454 | +0.0512 | +0.0671 | +0.0729 | +0.0670 | +0.0717 |
| fold_1 | +0.0780 | +0.0850 | +0.0853 | +0.0862 | +0.0718 | +0.0738 | +0.0703 | +0.0739 |
| fold_2 | +0.0623 | +0.0652 | +0.0600 | +0.0644 | +0.0874 | +0.0913 | +0.0878 | +0.0907 |

## Tail DirAcc (baseline)

- threshold: |z| > 2.0 (19.37 bps equivalent), N tail: 6000
- DirAcc: 0.541  Pearson: +0.0870  Spearman: +0.0895

## Verdict: FAIL

Winning variant: **swa_k5**  (P=+0.0656 S=+0.0786)
