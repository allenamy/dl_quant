# 重训战役 2026-09 · 脚本清单(单一真相源 = 本目录; 机器上只放运行副本)
> PREREG: docs/PREREG_retrain_addendum_v2main_2026-09-01.md(sha c24b8d2f8567) + RUNBOOK_monthly_retrain_2026-09

| 脚本 | 跑在 | 输入 | 输出 | 门 |
|---|---|---|---|---|
| pod_extend_vision.py(镜像原件) | pod | Vision daily zips 08-22..31 | wide_multisrc/{klines5m,premidx}_daily | 404=新币缺日正常 |
| pod_merge_cache_ext.py(派生 de7a0661) | pod | fresh缓存 + 新zips | dlnative..._ext.npz | **重叠窗逐位 exact_eq≥0.999 → 实测 1.000000 PASS** |
| fund_pull_pod.py(新作) | pod(独立IP, ≤3.5req/s) | /fapi/v1/fundingRate 全史 | fund_aug.json.gz(AUG全量形态) | 行数/名覆盖抽查 |
| pod_panel_ext.py(镜像原件) | pod | ext缓存 + fund_aug + zload | wide_panel_4h_v2ext.npz | 回传 jpline 与基线重叠 corr≥0.999(门①) |
| pod_fea_ext.py(镜像原件) | pod | ext缓存/面板 | 特征 ext | 同构校验 |
| king 重训(jpline+pod 双机) | 双机 | 合并面板 | slow booster v3 | 门② \|ΔIC\|≤0.004 + 门V4 双机一致 |
| f10_refit_pod.py(卷上原件) | pod GPU | 171特征ext + 冻结配方 | f10 s42/s2027 .pt + np导出 | 门V1 np≡torch / V2 回放不退化 / V3 泄漏仪器 |

**运行副本位置**: pod:/workspace/(scp 自本目录); jpline:/mnt/storage/private/work_hsy/。机器上文件 = 副本, 修改必须回写本目录并重新分发。
