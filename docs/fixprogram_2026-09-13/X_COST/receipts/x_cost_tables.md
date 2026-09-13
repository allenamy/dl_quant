## T1 Maker share (CHK-03 caliber) by period
| period | anchors | halted | rebuild | D (USDT) | maker share | median anchor | min–max anchor | maker share ex-rebuild |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| P1 | 34 | 0 | 0 | 69,895 | 92.6% | 94.5% | 73.5–100.0% | 92.6% |
| P2 | 30 | 4 | 2 | 438,111 | 83.8% | 83.1% | 56.1–100.0% | 80.4% |
| P3 | 34 | 6 | 2 | 770,057 | 77.6% | 77.2% | 55.9–100.0% | 73.9% |
| S1a | 27 | 0 | 0 | 54,969 | 93.1% | 95.0% | 74.8–100.0% | 93.1% |
| S1b | 7 | 0 | 0 | 14,926 | 90.4% | 93.1% | 73.5–96.7% | 90.4% |
| S2a | 15 | 0 | 1 | 198,808 | 80.7% | 87.6% | 76.0–95.9% | 87.9% |
| S2b | 15 | 4 | 1 | 239,303 | 86.3% | 73.1% | 56.1–100.0% | 76.1% |
| S3 | 34 | 6 | 2 | 770,057 | 77.6% | 77.2% | 55.9–100.0% | 73.9% |

## T2 Taker components as % of D (non-halted, excluding rebuild anchors); Δ vs S1a in pp
| component | S1a | S1b | S2a | S2b | S3 | Δ S3−S1a |
|---|---:|---:|---:|---:|---:|---:|
| K2d | 0.00 | 0.00 | 0.00 | 9.88 | 15.56 | +15.56 |
| K2q | 0.00 | 0.00 | 0.00 | 3.12 | 3.17 | +3.17 |
| K2e | 0.00 | 0.00 | 0.00 | 0.00 | 0.57 | +0.57 |
| K2n | 6.87 | 6.73 | 6.45 | 0.00 | 0.00 | -6.87 |
| K3ci | 0.00 | 2.83 | 4.00 | 6.63 | 4.35 | +4.35 |
| K3f | 0.00 | 0.00 | 1.67 | 4.22 | 2.44 | +2.44 |
| **taker total** | 6.87 | 9.56 | 12.12 | 23.85 | 26.10 | **+19.22** |

## T3 Driver indicators (A1: non-halted anchors, excluding rebuild anchors)
| indicator | S1a | S1b | S2a | S2b | S3 |
|---|---:|---:|---:|---:|---:|
| first-attempt −5022 plans / plans | 11.6 | 9.0 | 14.3 | 19.6 | 23.0 |
| rejected intent / maker intent (RI/MI) | 0.221 | 0.218 | 0.231 | 0.213 | 0.282 |
| from_reject IOC notional / rejected intent | 0.248 | 0.258 | 0.262 | 0.576 | 0.597 |
| maker intent / D | 1.255 | 1.195 | 1.068 | 1.061 | 1.145 |
| maker-flag maker fills / maker intent | 0.742 | 0.757 | 0.823 | 0.718 | 0.645 |
| no-chase gap: skipped_no_chase_arm residual / MI | 0.0810 | 0.0548 | 0.0283 | 0.0460 | 0.0428 |
| residual below floor / MI | 0.0035 | 0.0027 | 0.0024 | 0.0016 | 0.0013 |
| from_partial residual sent / MI | — | 0.0237 | 0.0534 | 0.1022 | 0.0635 |
| median target notional per name (USDT) | 170.53 | 175.79 | 706.46 | 674.11 | 906.98 |
| gross_mult values | [2.0] | [2.0] | [2.0] | [2.0] | [2.0] |

## T4 from_reject IOC share: factorisation S2a → S3 (non-halted, ex-rebuild; log-share allocation)
share_FR 6.45% → 19.30% (Δ +12.85 pp)
| factor | ratio S3/S2a | allocated pp |
|---|---:|---:|
| reject_pool RI/MI | 1.222 | +2.35 |
| IOC conversion IOC/RI | 2.282 | +9.68 |
| intent per fill MI/D | 1.072 | +0.82 |

## T5 Requote direct arm: counterfactual (A1, INFERRED)
| slice | K2d share | RI_direct/D | attributable (c0 from S2a) | attributable (c0 from S1a) | bounds |
|---|---:|---:|---:|---:|---|
| S3:ex_rebuild | 15.56% | 15.98% | 11.38% | 11.61% | [-0.42, 15.56]% |
| S3:all | 11.86% | 16.36% | 7.58% | 7.81% | [-4.49, 11.86]% |
| S2b:ex_rebuild | 9.88% | 9.88% | 7.29% | 7.43% | [-0.00, 9.88]% |
c0 (S2a ex-rebuild) = 0.2616; c0' (S1a) = 0.2476

## T6 Attribution of the maker-share drop S1a → S3 (non-halted, ex-rebuild)
Maker share 93.1% → 73.9%; taker share Δ +19.22 pp; D per trading anchor in S3 = 14,862 USDT
| item | pp of D | extra fee vs maker, USDT/anchor | USDT/day |
|---|---:|---:|---:|
| requote direct arm (counterfactual c0 S2a) | +11.38 | 0.51 | 3.05 |
| other from_reject growth (reject pool, requote-arm and exempt IOC, net of pre-experiment K2n) | +1.04 | 0.05 | 0.28 |
| chase arm, in-sample anchors (K3ci) | +4.35 | 0.19 | 1.16 |
| chase_forced neutrality fills (K3f) | +2.44 | 0.11 | 0.65 |
| all other components | +0.00 | 0.00 | 0.00 |

