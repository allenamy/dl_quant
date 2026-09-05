# MANIFEST — phi_grid_2026-09-05 (PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §B, sha256 05801bb2…, commit dfbe516)

pod2 root: /workspace/review_scratch/phi_grid/ (read-only after 2026-09-05 11:22:39Z JUDGE rc=0; 136 MB on pod incl. 8 .npz). Layout = f10_caliber/dev_alt (label (iii) accounting caliber, meta = refute_C6_2/altrun/meta_newprod.npz = dlw y4s); device w10_health.py / masks/umask_UPIT.npz / calib/costb_fee_steady.json byte-identical to health_check (setup_phi.log). Archived here: results json/md, scripts, logs (SHA256SUMS = local sha256 of the archived copies; each equals the pod-side value below).

## pod-side sha256 of every product (sha256sum on pod2, 2026-09-05 11:23Z)

```
5f19609372c902c2368fd8a1a2695e7f97d736853589735d1083400ac7c31a9c  results/phi_judge.json
f9cfc4cbb886837dbdfef64f96add7a297cfabd2c9edd5a886806c94dfc0662d  results/phi_tables.md
f5b836b626421c2222cef65588f52b44bb669743c8d02420db050daf531306bf  setup_phi.sh
e2e2fd843a2f0cbb004e636bc4079c4864d665359ae838fd824534bcc60a83f2  chain_phi.sh
2b6d093148b205745d5a2e38388b0af8b27ca85a0ca4540ab64a4d53c6c37436  run_arm.sh
371325641eaeaedd6343272d312a69d3d87e7a60da86a9b092c7a6a433e922fd  judge_phi.py
8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d  w10_health.py
ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece  masks/umask_UPIT.npz
9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42  calib/costb_fee_steady.json
0e378c81880cf07d4cce1eb9417683087f0f8ab39e0da82bb86af25f302db5bc  logs/commands.txt
3408a18b27efd689f81e8059902fa40bbcf45e3282e597256bca48ae34d9b6d2  logs/chain_phi.log
a3ce58264f9a02a8342a19731f6f4c5973687f947e0e7b3b26b08288e02691b1  logs/setup_phi.log
97ade05596a795904dab42add4f750a0ebf20c0040c035f542afc91e03effe0b  logs/judge_phi.log
e1fa6a95632055cca71d37f369856b836cdf1241e0e303989c4b24b00a8573ff  dev_alt/probe_artifacts/w10_ablation_series_prod_phi025_s2027.npz
7be038be8a420f0a25f5e86f5a40d4f2af51a21eec2db43a362a5f2aea31ef84  dev_alt/probe_artifacts/w10_ablation_series_prod_phi025_s42.npz
10f21057764758a51ffe90fc86d470e0b954211b73c14a8070bd665c7bfa2977  dev_alt/probe_artifacts/w10_ablation_series_prod_phi035_s2027.npz
cc97d6f2a2668726e460b7431a9a8afafc455cfbe3a306c59a5aa26285cf433b  dev_alt/probe_artifacts/w10_ablation_series_prod_phi035_s42.npz
4c6195ed4c83aa537da609e55cd4d59eaac3fa3f414e0074d9894e8136fa8873  dev_alt/probe_artifacts/w10_ablation_series_prod_phi055_s2027.npz
29c898d74ffe69348560ad2f6624438ae09b38a43bd9c1cad17f77c43332f45e  dev_alt/probe_artifacts/w10_ablation_series_prod_phi055_s42.npz
3b3ee1f5c48db357556c5a63a3ac9ac9d291fa7ba2e0a53f0cf90324e06658de  dev_alt/probe_artifacts/w10_ablation_series_prod_phi065_s2027.npz
45c8ac17efbec64e52cc3f1fa4af927e98fd0a5a3f8198c04f68ff87fbcca15d  dev_alt/probe_artifacts/w10_ablation_series_prod_phi065_s42.npz
```

## grid anchors reused (not rerun; sha256 asserted in judge_phi.py against f10_caliber MANIFEST.md, commit 7ceb754):

```
93b927b71ba9c6a61dba39186b4423d733441aa58ffa3870b7bba26fd13793f9  /workspace/review_scratch/f10_caliber/dev_alt/probe_artifacts/w10_ablation_series_prod_phi0_s42.npz
d7e66b9607ef2412af360dde3ccaf9ef4fd8157a937adb4e1f8b29a905c58152  /workspace/review_scratch/f10_caliber/dev_alt/probe_artifacts/w10_ablation_series_prod_phi0_s2027.npz
53cd2d7fa7be3e00cbca3dffa15dec1d5f64085d4bb375cadd7953792cf2ae24  /workspace/review_scratch/f10_caliber/dev_alt/probe_artifacts/w10_ablation_series_prod_phi045_s42.npz
4710b1bb4d5fb5b763820d9e7d1890ff37d1e1c055b1e2bfaee0d7c4f035e79b  /workspace/review_scratch/f10_caliber/dev_alt/probe_artifacts/w10_ablation_series_prod_phi045_s2027.npz
```

## not archived (npz, left on pod): the 8 new artifacts dev_alt/probe_artifacts/w10_ablation_series_prod_phi{025,035,055,065}_s{42,2027}.npz (sha above) + masks/umask_UPIT.npz (ccb7a080…).

## inputs (read-only): meta_newprod 831857dd…, slow_pred_pinned 158cd4ac…, wide_panel_4h_v2ext 5e67c055…, f10_V2MAIN_s42 baf747ce…, f10_V2MAIN_s2027 c742ffaa…, dlw_targets dd4ed2df… (setup_phi.log)
