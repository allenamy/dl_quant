# Wide-metrics GBDT non-linear probe (YR4 residual, xsec rank-IC, walk-forward)

- rows=1129124  folds=6  LightGBM(leaves=15,depth=4,l2=5.0,n_est=500)
- baseline(32ch) GBDT IC = 0.0310  folds=[0.0387, 0.0237, 0.0328, 0.0253, 0.0357, 0.0296]
- +7 metrics family GBDT IC = 0.0306  folds=[0.035, 0.0256, 0.032, 0.0262, 0.0319, 0.0329]
- **dIC = -0.0004**  per-fold=[-0.0037, 0.0018, -0.0007, 0.001, -0.0038, 0.0033]  sign_consistent=False
- metrics-block shuffle null dIC = -0.0006 +/- 0.0006  z=0.34
- leak-guard (shuffled target) IC = -0.0045  (CLEAN)
- **GATE: FAIL**  (need dIC>=+0.003 & sign-consistent & z>2 & leak-clean)
