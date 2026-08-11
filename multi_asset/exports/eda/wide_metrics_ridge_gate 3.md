# Wide-metrics Ridge pre-gate (YR4 residual, xsec rank-IC, walk-forward)

- alpha=100.0  folds=6  null_perms=20
- baseline(32ch) IC mean = 0.0234
- +7 metrics family IC mean = 0.0242  dIC = +0.0007
- family per-fold dIC = [-0.0004, 0.0015, 0.0009, 0.0015, -0.0009, 0.0016]  sign_consistent=False
- shuffle-future null dIC = -0.0005 +/- 0.0004  z=3.42
- **GATE (family): FAIL**  (need dIC>=+0.003 & sign-consistent & z>2)

## Per-channel incremental dIC (baseline + single channel)

| channel | dIC_mean | sign_consistent | per_fold |
|---|---|---|---|
| oi_level_norm | +0.0005 | False | [0.0013, 0.0008, 0.0002, 0.0003, 0.0002, -0.0001] |
| d_oi_1h | +0.0007 | True | [0.0015, 0.0005, 0.0008, 0.0001, 0.0001, 0.0011] |
| d_oi_24h | +0.0004 | False | [0.0001, 0.0002, 0.0004, 0.0015, 0.0002, -0.0002] |
| doi_x_ret | +0.0000 | False | [-0.0, -0.0, 0.0005, -0.0, -0.0, -0.0003] |
| top_ls_ratio_z | +0.0006 | False | [0.0007, 0.0004, 0.0008, 0.0013, -0.0001, 0.0006] |
| top_vs_global_divergence | -0.0012 | False | [-0.0021, -0.0003, -0.0021, -0.0022, -0.0007, 0.0] |
| taker_ratio_ema | -0.0000 | False | [0.0002, -0.0001, -0.0001, -0.0001, 0.0001, -0.0] |
