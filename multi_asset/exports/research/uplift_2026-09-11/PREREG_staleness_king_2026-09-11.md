> **创建:** 2026-09-11 | **Session:** b9646a9e (subagent: staleness/regime axis) | **状态:** 预注册, 判据冻结先于任何数字 | **作废条件:** 任一事实前提被反证

# PREREG · king LGBM 陈旧性直测(分数层)

## 事实前提(本轮已 VERIFIED)
1. 在役 king booster `slow2026.txt` 由 `pod_export_bundle_v3.py` L49 `tr = YRA < 2026` 训练 ⇒ 梯度止于 2025-12-31。
2. 在役 F10 DL `f10_live_s42_np.npz`(sha256 351ae26b…= pod2 `/workspace/f8_ext/models/f10_live_s42_np.npz`)
   由 `pod_f10_refit_ext.py` L89-90 的时序 85% 切分训练 ⇒ 梯度末锚 2025-12-18 16:00Z, 2026 全部只进验证片(选 epoch)。
3. 2026-09-09 的 v4 全量重训 (`RESULT_v4_chain_retrain_quantify_2026-09-09.md`) 逐字保留上述两条切分
   (§4: "梯度窗末端 2025-12-19 12Z, 验证切片 …→08-31 20Z … 预注册如此"), 因此其十格 (C) UNDECIDED
   **没有测过**「把 2026 喂进梯度」这一自由度。

## 问题
把 2026 上半年喂进 king 的梯度, 是否提高 2026-07..08 的 OOS 分数层 IC?

## 装置
数据 = pod2 `/workspace/data/wide_fea_v4.npy` + `wide_fea_v4_meta.npz`(holefix2+clamp 正典链);
行构造/keep 列/超参逐字抄 `pod_export_bundle_v4.py` L38-L52(rank 目标, n_estimators=400, lr=0.05, leaves=63, sub/col 0.8)。

- **臂 S(stale, 在役配方)**: 训练集 = 年份 < 2026。
- **臂 F(fresh)**: 训练集 = E_ts < 2026-07-01(= S ∪ 2026-01..06)。
- **臂 R(rolling 24m)**: 训练集 = 2024-07-01 ≤ E_ts < 2026-07-01(等量近期, 测「近因 vs 样本量」)。
- 持出 H = 2026-07-01 ≤ E_ts < 2026-09-01(两月, 真持出, 三臂皆未见)。
- 次级持出 H2 = 2026-08-01..08-31(实盘月)。

## 指标与判据(冻结)
- 主指标 = H 上逐锚 Spearman(pred, y4) 的均值(= 在役 bundle 门③ 同口径)。
- 差 Δ = IC(F) − IC(S), CI 由 **按 UTC 日分块自举 2000 次**给出。
- **(A) 录取**: Δ 的 95% CI 下界 > 0 且 H2 同号 ⇒ 「陈旧性可修, 值得做书层复验」。
- **(B) 判负**: Δ 的 95% CI 上界 < 0 ⇒ 「加 2026 有害」。
- **(C) UNDECIDED**: CI 含 0 ⇒ 「陈旧性在分数层测不出」。
- 分数层录取是**必要非充分**(项目铁律「排序≠净额」): 任何 (A) 都必须再过书层净额 CI 才谈换装。本轮不做书层。
- 三臂皆用同一行集/同一 keep 列/同一超参/同一随机种子(lgb 默认), 唯一变量 = 训练行的时间范围。
