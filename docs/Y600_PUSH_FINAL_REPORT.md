# V4 y_600 12-Hour Push — Final Report

## Headline

| | Pearson | Spearman | DirAcc |
|---|---:|---:|---:|
| Baseline (frozen) | +0.0562 | +0.0744 | 0.538 |
| Final stack | +0.0737 | +0.0867 | 0.538 |
| Δ | +0.0176 | +0.0123 | |

## Per-fold (clean / dense)

| Fold | Clean N | Clean P | Clean S | Clean Dir | Dense N | Dense P | Dense S |
|---|---:|---:|---:|---:|---:|---:|---:|
| fold_0 | 1543 | +0.0834 | +0.1091 | 0.543 | 15399 | +0.0515 | +0.0585 |
| fold_1 | 1651 | +0.0779 | +0.0680 | 0.532 | 16470 | +0.0528 | +0.0556 |
| fold_2 | 1677 | +0.0607 | +0.0860 | 0.541 | 16809 | +0.0605 | +0.0645 |

## Pooled

- **Clean** (stride_every=10): N=4871  P=+0.0737 (95% CI [+0.0459, +0.1031])  S=+0.0867 (95% CI [+0.0570, +0.1143])  Dir=0.538
- **Dense**: N=48678  P=+0.0540  S=+0.0591  Dir=0.524

## Tail (|y| > 2·MAD-σ)

- threshold: 19.37 bps
- N tail: 48458
- DirAcc: 0.524  (gate: ≥ 0.52)
- Pearson: +0.0541
- Spearman: +0.0592

## Regime (vol terciles)

| Bucket | N | Pearson | Spearman | DirAcc | Avg vol bps |
|---|---:|---:|---:|---:|---:|
| low_vol | 16226 | +0.0694 | +0.0716 | 0.525 | 9366.97 |
| mid_vol | 16226 | +0.0677 | +0.0695 | 0.530 | 12583.90 |
| high_vol | 16226 | +0.0422 | +0.0437 | 0.516 | 17584.03 |

## Verdict: **PARTIAL**
