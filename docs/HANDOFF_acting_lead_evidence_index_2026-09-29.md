> **创建:** 2026-09-29 01:28 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final-evidence-index | **作废条件:** 冻结HEAD、索引文件或归档字节变化须重新核验

# 两日交接证据索引

主件：[HANDOFF_acting_lead_2026-09-29.md](HANDOFF_acting_lead_2026-09-29.md)。此索引不重判实验，也没有重新训练或重跑现金；历史测试结果以原收据为准。

冻结范围 `3b4a2815ad4b8d45ee09ed8b69222e04b5885301..f64792d1c2b34bd0e38bdd7eb1c013bcb4be4ff1`：**528提交，2031改变文件，587个Python/shell源码文件，57份结果/发现/审计文档**。下面的SHA来自冻结Git对象；后续仅交接文/台账修改不倒写历史身份。

## 一、完整机器索引

- [COMMITS.tsv](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/COMMITS.tsv) — SHA256 `d95267436fc3567192e71453cea5b4ac56c69a2ae80380be36d058b6a37cfbb1`。
- [CHANGED_FILES.json](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/CHANGED_FILES.json) — SHA256 `acbbcccd6fffdc578dab00b72147aeb32b09b7157a9ed98fa779c9a4be33ecd9`。
- [SOURCE_FILES.json](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/SOURCE_FILES.json) — SHA256 `1ca33329326600043221059978c5c7f33881df1d008533a4db91ef57c982b411`。
- [CHANGED_PATHS.txt](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/CHANGED_PATHS.txt) — SHA256 `2d3ca9386e0ee8c59e929959ed06b4f3ed77f9ae1328c9f859fd921f29cbe720`。
- [DIFF_STAT.txt](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/DIFF_STAT.txt) — SHA256 `d7b749ec0cfbc671098ae26f2235637821ce048a4961e0f61598af8b84f9cd49`。
- [PAUSE_RECEIPT.json](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/PAUSE_RECEIPT.json) — SHA256 `6ad49cca29b20a859836d7ec9325868025d91b227d285109d14e080b08ba3337`。
- [LOCAL_ARCHIVES.json](../multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929/LOCAL_ARCHIVES.json) — SHA256 `0570b9eb2817a0a10873ba84113e47304fcc3edfa237e28735fc3c408bb2e9b8`。

`CHANGED_FILES.json`逐文件给出完整路径、字节数、SHA256、Git blob和最后修改提交。`SOURCE_FILES.json`是代码子集。它们不是仅有文件名的索引。

## 二、所有最终结果入口

表中“最后修改提交”不是初始预注册；各报告正文列完整设计/实现/修订链。哈希按冻结点，旧报告中的事后更正保留。

| 文档 | 最后修改提交 | SHA256 |
|---|---|---|
| [AUDIT_GAP4_OPEN_08Z_failure_2026-09-27.md](AUDIT_GAP4_OPEN_08Z_failure_2026-09-27.md) | `453ed3001` | `117356d475c544997dffd727f310b57e6214a7b43ae17faa51eaae7a5407b5e5` |
| [AUDIT_executor_mirror_dust_bridge_2026-09-28.md](AUDIT_executor_mirror_dust_bridge_2026-09-28.md) | `3623b24d0` | `c35f4a3b6c9b4c724b154bc41844970937e07a2279d07fc63ee4b5ccc1f382ed` |
| [FINDING_F10_capacity_not_correlation_2026-09-27.md](FINDING_F10_capacity_not_correlation_2026-09-27.md) | `8ba8a6178` | `a419f8a27baccc6e66078a13f33eed8e2fe98d3b528ac18f154cd25cf6f92a7d` |
| [FINDING_F10_recent_training_admission_2026-09-28.md](FINDING_F10_recent_training_admission_2026-09-28.md) | `eb23ef1c6` | `026322df8d6404f8cf23d9e9a13d778468204a7391e17d363e3c5b5d468064e8` |
| [RESULT_D10_input_dryrun_2026-09-28.md](RESULT_D10_input_dryrun_2026-09-28.md) | `72bf99de4` | `710b31069026c2acf7e246519c53440f56a0553eae5d8bbcead56399278da914` |
| [RESULT_F0_byte_identity_2026-09-28.md](RESULT_F0_byte_identity_2026-09-28.md) | `823ae153a` | `47d55d5fdd7e9765a1b18e390612181d3447022f3660c0baa7c40325f44779b4` |
| [RESULT_F10_label_evidence_repair_full_book_2026-09-28.md](RESULT_F10_label_evidence_repair_full_book_2026-09-28.md) | `d1a26166e` | `3560af1f018c17553c60950e59b64b1df8125c38f03b4c46d49f6d3de8399d6c` |
| [RESULT_F10_liquid_population_loss_2026-09-28.md](RESULT_F10_liquid_population_loss_2026-09-28.md) | `87bb20917` | `1415a833989d97841daac9c1f064617f9cd2d00f560de1fa5060e9338aa93db4` |
| [RESULT_F10_recent_adaptation_full_book_2026-09-28.md](RESULT_F10_recent_adaptation_full_book_2026-09-28.md) | `5e3bf3e44` | `cedd4f818f3ff7df749f8f22c6a0b686458a79012d56db4c79d4be726c239c0c` |
| [RESULT_F10_signal_to_book_decomposition_2026-09-28.md](RESULT_F10_signal_to_book_decomposition_2026-09-28.md) | `39b811462` | `5e3bd6a84475f2d76c08d739ab6659b2bb9198df5712663ab0b0e72f93a89681` |
| [RESULT_F10_tail_position_split_2026-09-28.md](RESULT_F10_tail_position_split_2026-09-28.md) | `39b811462` | `efcb9c8c8ee6dee0a2c668eaffc5fbe16ea1043f23a5e3b106cd87107a3f1896` |
| [RESULT_KN_label_geometry_2026-09-28.md](RESULT_KN_label_geometry_2026-09-28.md) | `75fe6ce35` | `5e56ed22f07c4768d26bb0fca8dd2a31cb8f16b01bbc2fe8294f9b11ce86540f` |
| [RESULT_KSR_handback_state_2026-09-28.md](RESULT_KSR_handback_state_2026-09-28.md) | `053095ca8` | `a95fba2f1ef1527f3a7c5c2832be5219b465c33a5cd3349ba1e0a173ad85cbc6` |
| [RESULT_NC_liquidity_blend_cash_2026-09-28.md](RESULT_NC_liquidity_blend_cash_2026-09-28.md) | `72eb3c0ac` | `9c98aaea99480e9e56134d8e55930e907ef783cddf472c8a5e3df7a150eb8423` |
| [RESULT_NC_liquidity_blend_support_2026-09-28.md](RESULT_NC_liquidity_blend_support_2026-09-28.md) | `0dc14c6b9` | `38d01bd1ef0d428607446a9814a4b3cd18a59992cdccd464a9731773ad334041` |
| [RESULT_acting_KSR_complete_2026-09-28.md](RESULT_acting_KSR_complete_2026-09-28.md) | `6ef3c9aa6` | `4293aa100db9fd0c26eecfabf078c24acfe5991f6f258685f2ffcf7bd29c7987` |
| [RESULT_acting_funding_mechanism_2026-09-27.md](RESULT_acting_funding_mechanism_2026-09-27.md) | `ddd8ef3b6` | `1c85ad95174415685be7033f62d71b6ff6f7066d3d98cc2df280308e24b66e16` |
| [RESULT_actual_blend_cash_attribution_2026-09-28.md](RESULT_actual_blend_cash_attribution_2026-09-28.md) | `5432299c6` | `9b0275de03c8e881082e3a51d74a0863dd9b6276362428014af75ef88fd346f9` |
| [RESULT_actual_directional_cash_2026-09-28.md](RESULT_actual_directional_cash_2026-09-28.md) | `af48c903c` | `4f58e024cea7a0eb0dec714c13a0f27f5e27f8041aaf7cd7d5476ad24a510a4c` |
| [RESULT_actual_target_cash_bridge_2026-09-28.md](RESULT_actual_target_cash_bridge_2026-09-28.md) | `1ee204621` | `42369f447be33a5b796cfc7f1d9247233e4a063974d470af2df4c54e11ec3980` |
| [RESULT_baseline_sharpe_bridge_2026-09-28.md](RESULT_baseline_sharpe_bridge_2026-09-28.md) | `0e431121d` | `1faa8f55778f37f4c2266f2d4921f0f97b7021e6967c868832f50c73f51053c6` |
| [RESULT_cap50_complete_book_2026-09-28.md](RESULT_cap50_complete_book_2026-09-28.md) | `e244faa87` | `86b7684294d942f7d6b69910b0abfe71b264a84d9d5d7de3f53c0015eafd57bf` |
| [RESULT_clock_paired_update_probe_2026-09-28.md](RESULT_clock_paired_update_probe_2026-09-28.md) | `e1b5b86ca` | `25d0e305886eec7959940f2ca4552eef73eac052a4370f83ac24ccd4f23c68b4` |
| [RESULT_execution_input_closure_2026-09-28.md](RESULT_execution_input_closure_2026-09-28.md) | `ed1456b17` | `26e3e62017cb0cd62644e7d47b70edf0de3430fb8b63b98ea27c7d4b6cef7c6d` |
| [RESULT_executor_dust_bridge_2026-09-28.md](RESULT_executor_dust_bridge_2026-09-28.md) | `befb272be` | `fca00205817dba6746ff131d1afbbee80237c58dde4b9ec526d94968caff287f` |
| [RESULT_fetch_feature_propagation_2026-09-28.md](RESULT_fetch_feature_propagation_2026-09-28.md) | `0266b0717` | `c3540526ee3615f7d7b1f3400a743a24b21c05792866769c24a0ead704cfeac5` |
| [RESULT_fetch_membership_boundary_2026-09-28.md](RESULT_fetch_membership_boundary_2026-09-28.md) | `6571a533e` | `d2227fdc374ceffbd69091605937222264f90a5b6548ef9b4d5c513fe9113d6f` |
| [RESULT_first120_network_clock_2026-09-28.md](RESULT_first120_network_clock_2026-09-28.md) | `7c39c83e7` | `64b2c9498ea8da9407c67c254350da0150ef16ee4f322e1a88bedf154f54851c` |
| [RESULT_first120_rank_action_2026-09-28.md](RESULT_first120_rank_action_2026-09-28.md) | `93f419c36` | `1cb2b99a77e79339e0c7d27e2e61abe2359f1b796fcce60dfb44ff1087c2e2db` |
| [RESULT_gap_history_propagation_2026-09-28.md](RESULT_gap_history_propagation_2026-09-28.md) | `e7d6caac7` | `b322df9ec590690a88836f28d53990222758a54f9b1a233d5330d66094f65615` |
| [RESULT_held_strength_cash_diagnostic_2026-09-28.md](RESULT_held_strength_cash_diagnostic_2026-09-28.md) | `0e694c0cf` | `b1200941ec37c4c11269d0c9c6622bc9bafdad00c027d269e9332624b1196861` |
| [RESULT_holding_horizon_full_book_2026-09-28.md](RESULT_holding_horizon_full_book_2026-09-28.md) | `bdbfecedc` | `d0ec1af41dec827315ec1acc3600b382b76748f419f4fc7fd5741e93378ce288` |
| [RESULT_independent_LR_recurrence_2026-09-28.md](RESULT_independent_LR_recurrence_2026-09-28.md) | `ae2c6dcaa` | `92244d206ee198edd1a9fcd4c897df7f7e487465dab0d0fcbcc91ed2ef2bc41e` |
| [RESULT_inverse_risk_complete_book_2026-09-28.md](RESULT_inverse_risk_complete_book_2026-09-28.md) | `0374ffb66` | `658aa4137cbcb78989d82470a33a0032c1996ab9e9014141984377d619a9dc73` |
| [RESULT_liquidity_cost_probe_2026-09-28.md](RESULT_liquidity_cost_probe_2026-09-28.md) | `0f91ba975` | `b297274c0deff1422854f4b379cc99a572f5192a14366cfd428d15d72a9db7f7` |
| [RESULT_live_replay_layer_alignment_2026-09-28.md](RESULT_live_replay_layer_alignment_2026-09-28.md) | `42293c2a0` | `f6198fb8be445b4b3c05f67e0d75146bdac66fac06df54134c93c73abdbb6458` |
| [RESULT_model_state_handoff_cash_2026-09-29.md](RESULT_model_state_handoff_cash_2026-09-29.md) | `869277383` | `aa0e01c16e3ec66653318964c490b3ab10f5f8a947cd05cac302b68a26668c2f` |
| [RESULT_model_state_handoff_probe_2026-09-29.md](RESULT_model_state_handoff_probe_2026-09-29.md) | `b72fb73ef` | `f87ab5d36b2732930df7c827efc64a86af021c7d2a24ed888c4ad86abb503172` |
| [RESULT_normalized_network_gradient_check_2026-09-28.md](RESULT_normalized_network_gradient_check_2026-09-28.md) | `15a97fb41` | `634543a036b7546d7e0d58c3b83f7f119ed8e1ce6bf5aaef584972f6d59d40e7` |
| [RESULT_own_control_ablation_2026-09-28.md](RESULT_own_control_ablation_2026-09-28.md) | `999fbca68` | `082f3ca64195055ba6ce42e17ad6432914f3b36b345116e18e36696fd342cd60` |
| [RESULT_peer_flow_funding_screen_2026-09-28.md](RESULT_peer_flow_funding_screen_2026-09-28.md) | `d643124a8` | `ad0922982f671c39b3603f916fac2fe8a711276a0f6be920a296f01f967f5ec6` |
| [RESULT_peer_price_incremental_screen_2026-09-28.md](RESULT_peer_price_incremental_screen_2026-09-28.md) | `40097d3d0` | `1796a999ceb3b450393caf2a67760e79fc98ba0607424761c83f1d5aec554888` |
| [RESULT_peer_serving_population_2026-09-28.md](RESULT_peer_serving_population_2026-09-28.md) | `2fbd30e41` | `976f8cb1ea4b9bad795759a8480d619abab83554492439257bdda1553c279010` |
| [RESULT_prediction_axis_bridge_2026-09-28.md](RESULT_prediction_axis_bridge_2026-09-28.md) | `ef7815096` | `66f191170c17963075cd3466b444a7fb1126c21037740775ce8a8758d5af8470` |
| [RESULT_recent_NC_full_book_cash_2026-09-28.md](RESULT_recent_NC_full_book_cash_2026-09-28.md) | `95b08ff5f` | `6369beafc0ab42ba9a4f65965aa387d4cc9c213e9e7260ff7a23bca0b1a5f929` |
| [RESULT_recent_evaluation_priority_2026-09-28.md](RESULT_recent_evaluation_priority_2026-09-28.md) | `8fb4b1c5c` | `117c7acb4bc1be6436ee804b286d767d43d7a6793b69d35a0f4b33702555632e` |
| [RESULT_recent_raw_input_parity_2026-09-28.md](RESULT_recent_raw_input_parity_2026-09-28.md) | `7e21a997d` | `90420245213219d4042b263e58388e7b0551300c5a181c70758820166fca2ca9` |
| [RESULT_reconcile_notice_2026-09-28.md](RESULT_reconcile_notice_2026-09-28.md) | `10bf1d86e` | `0b1f51b2ac5f7dc04835e0cfcc30e00782ba713694a479fa66e121e422f48d64` |
| [RESULT_recovery00_and_live_signal_bridge_2026-09-28.md](RESULT_recovery00_and_live_signal_bridge_2026-09-28.md) | `15a97fb41` | `5e270f314a5665f15e8430d0c2bb323de34b287689f6d0eaafda4f595a0a2de5` |
| [RESULT_residual_model_full_book_2026-09-28.md](RESULT_residual_model_full_book_2026-09-28.md) | `ab2bdf410` | `956b54d1edd59942e77fab79375d48750e0954578459bbbe9d621617ab928659` |
| [RESULT_residual_score_to_book_probe_2026-09-28.md](RESULT_residual_score_to_book_probe_2026-09-28.md) | `8310d4329` | `917d87eba417a7105d4b1ebf6027bfb9459c4258a1fa7c99d731bc55262a5e66` |
| [RESULT_residual_strength_conditional_2026-09-28.md](RESULT_residual_strength_conditional_2026-09-28.md) | `999fbca68` | `b135111b167b6cf12ba3eb5de8dde20be4c0b0492b1391642339f4a84def1f0c` |
| [RESULT_signal_state_trace_2026-09-28.md](RESULT_signal_state_trace_2026-09-28.md) | `526576058` | `9caf05c6747344195bdaa02c3a6e3675079f43255651cb596659f9b48222e367` |
| [RESULT_stable_training_window_sampling_2026-09-28.md](RESULT_stable_training_window_sampling_2026-09-28.md) | `8ffc837ed` | `e30865ce6c146d8a0e58df92f9252fcac55c72d0ea64d52e481cce59bf802a64` |
| [RESULT_tail_risk_held_cash_2026-09-29.md](RESULT_tail_risk_held_cash_2026-09-29.md) | `f64792d1c` | `8fcc07c54c1317019b39778c3db28ca8133cc8d8cc5303192951e047f3610172` |
| [RESULT_twenty_anchor_actual_cash_bridge_2026-09-28.md](RESULT_twenty_anchor_actual_cash_bridge_2026-09-28.md) | `6fb6caf8a` | `741286be5f89efe279f04a32fd5f5e1fdc32e5fe292e219b60401fdc9971f2f0` |
| [RESULT_two_sided_tail_risk_screen_2026-09-28.md](RESULT_two_sided_tail_risk_screen_2026-09-28.md) | `46ec13d45` | `ff62c9cf4b347b7fa62289609f43ae8fc6fa23ba0ddb4be225f9b89fc6dbe960` |

## 三、实际代码入口

均相对本研究工作树。目录内的合同、runner、测试和独立验证器一并保留；完整SHA见SOURCE_FILES，不用HEAD同名文件冒充旧运行版本。

| 任务 | 入口 | 最后修改提交 / SHA256 |
|---|---|---|
| 本地只读巡检 | [light_local_audit.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/light_local_audit.py) | `ff2f4b9c9` / `273fe0863d58f80fd327530bc264dab9c85a39d1ad4d862622ffedfa4fefe7a7` |
| 恢复验收 | [recovery_acceptance.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/recovery_acceptance.py) | `c8cdb12b7` / `0e78dba29aa235fd120c11e12e0212a81648a570d9ab6ad1e3ee9942f007fc82` |
| 对账提示核验 | [reconcile_notice_audit.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/reconcile_notice_audit.py) | `10bf1d86e` / `62ebce78e10e42a1c6dbcfc31de002ad1ce3522df5b8393f29a74438f257a73f` |
| 基线聚合桥 | [baseline_sharpe_bridge_20260928.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/baseline_sharpe_bridge_20260928.py) | `72eb3c0ac` / `5ae6957cd405e9bb7a97ed4b8a853b5dbc2185b4086afdcdc036741d50fbcbdd` |
| D10重现队列 | [d10_rerun6_queue.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/d10_rerun6_queue.py) | `688cb50e7` / `b921c5d8f9da69aeadad0088920b5a6db3a3b15746c81f088f0d978656dfc026` |
| KSR终态核验 | [ksr_terminal_audit.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/ksr_terminal_audit.py) | `f3cf14d2c` / `2f2b9465685ff947209e9627ebf33d5719d3a27f9d985b81cd7c9d5873f6d515` |
| KSR状态重建 | [ksr_handback_rebuild.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/ksr_handback_rebuild.py) | `a401ee88c` / `7760ca0b8f6c5558e9055062b35fc03ec59e3e399f80d6b85648b2501e813189` |
| KN标签诊断 | [kn_label_geometry_20260928/probe.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/kn_label_geometry_20260928/probe.py) | `ac11c6cbe` / `cb11bb84a02ed09d0939500d5faa708ab587b3079a020c534b8895ed742ffddd` |
| cap50 | [book_cap50_20260928/run_batch.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/book_cap50_20260928/run_batch.py) | `e3f402e13` / `fd9fe01214a980f6b473c472c2b5d46df7e8f24b094c643e62501ff6d8039d85` |
| 逆波动 | [book_invvol_20260928/run_batch.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/book_invvol_20260928/run_batch.py) | `b341dd202` / `4d6d641d7b9fb70235e4870bafcf236cc9d76645b4da0cc12eb3dff252b957f2` |
| 残差小模型 | [residual_book_20260928/train_ridge.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/residual_book_20260928/train_ridge.py) | `498e91ad5` / `d7d1963a7a4e3203b403560998e8a0059493f2d2fee6d14aa4099f3acdcba5bf` |
| 长持仓标签 | [horizon_book_20260928/train_ridge.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/horizon_book_20260928/train_ridge.py) | `93250c364` / `d2b363ccab3a6fe570c6a2e0d3f765cef69d14d099efdddb81791c144502e0f1` |
| 流动性融合整书 | [nc_liquidity_blend_cash_20260928/run_batch.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/nc_liquidity_blend_cash_20260928/run_batch.py) | `c4594a4b8` / `5534ffda90f147b57b3050cf675b354589c6e3fe89e46814088a5d3ff4b05775` |
| F10近期训练 | [f10_recent_adapt_20260928/train_adapt.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/f10_recent_adapt_20260928/train_adapt.py) | `526b333be` / `f786f2ad952335403ee5a4daa155998b3ae3245283ca0732793aa5963a95590d` |
| F10流动性人口loss | [f10_liquid_population_20260928/train_adapt.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/f10_liquid_population_20260928/train_adapt.py) | `993acabef` / `b6c29fb6b7edd344bc16d2bb8742bb656d2da42b6d4598a31ab2598321b7cf11` |
| 标签修复训练 | [f10_label_repair_20260928/train_adapt.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/f10_label_repair_20260928/train_adapt.py) | `d0c5de359` / `1fd512a20762ba8f48d5acb1da8333417e47f39b610bd4d84f2cd7b6af702ba2` |
| 标签证据 | [training_exposure_label_repair_20260928.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/training_exposure_label_repair_20260928.py) | `108fde7dc` / `a53b3596ad380a4c668b9446189709153a313c294f31c040b7b1c8b054309072` |
| 同伴特征小模型 | [linkage_20260928/ridge_screen.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/linkage_20260928/ridge_screen.py) | `2cebd2edd` / `54818daadd9d486afdcb2e7ee32cb7cd3aa8890c1e2b9748a6f5ae8679a65bbb` |
| 近期NC现金 | [recent_evaluation_inputs_20260928/recent_cash_run.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/recent_evaluation_inputs_20260928/recent_cash_run.py) | `4929df8e8` / `50397785637435256e41a777301a31e76e6b67c3b9ee4c1286aa4a70e2c78372` |
| d01 pure执行桥 | [executor_bridge_20260928/run_bridge.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/executor_bridge_20260928/run_bridge.py) | `f63ecc5fd` / `2179b0bfa71bdf521b102802b023390361c34af710f8957b52f2f5ed383a6e16` |
| 抓取状态 | [fetch_membership_boundary_20260928/probe.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/fetch_membership_boundary_20260928/probe.py) | `f3f327331` / `716b38a635c58c38b3e0204f55b3878810f448aa906761e8e5ba3e6ac7b962a7` |
| 抓取→完整特征 | [fetch_feature_alignment_20260928/run.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/fetch_feature_alignment_20260928/run.py) | `3c8263264` / `d5198873fe72db77aa615549d6b9e233dceeb4b39b2973379c376a9df2ff88bd` |
| 独立LR递推 | [lr_recurrence_20260928/run_lr.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/lr_recurrence_20260928/run_lr.py) | `0d3a48670` / `8c4f616ed523c2409dd2d7e3070e7c27372f42fe773f730e5e94928e44a214e5` |
| 执行限制闭合 | [conditional_execution_book.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/conditional_execution_book.py) | `8e3d6a1a9` / `5470a486bf9ce03d3e3bcf9f1a839aabd3fc39de37cb2ab100dfe71ac03ed3d2` |
| 实际现金 | [actual_cash_bridge.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/actual_cash_bridge.py) | `9dfe94eff` / `58b56c5141c8798dff1c22bf7dedad87a0b57e1a5aa05c424f61a31bf7656d49` |
| 实际多空 | [actual_directional_cash.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/actual_directional_cash.py) | `affa00ae7` / `ec149ce96952517e38db792beaf52e5b5d4ac15b1825631bdef2af5e2f488be4` |
| 静态目标桥 | [actual_target_cash.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/actual_target_cash.py) | `959856d2e` / `4bf352d6e4764527de13db482cc19e4daf9ef1611996d6b58c840c63caee97f9` |
| 混合子书 | [actual_blend_cash.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/actual_blend_cash.py) | `ab1ac5872` / `67a957344839dc80941a892fdffe551f09800d9c1b107489a8876aae9174f599` |
| 旧H谱系 | [signal_state_trace.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/signal_state_trace.py) | `703b0b56f` / `8eff10f9b12368fd1b04ec66a7647887efbc491eab4ee8109b5264eb1d9e1a88` |
| 状态接入 | [state_handoff.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/state_handoff.py) | `b94112502` / `7aa76aa6913ab61596a05a902f42d7425f9f0268d6bde02f8d7571789aa0e834` |
| 接入现金 | [run_handoff_cash.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/run_handoff_cash.py) | `88ee26cc5` / `cfeee67e464d809ca9df30bc507b4b5bb46b620cf58ddeaf67b797d9ab0998bd` |
| 尾部持仓现金 | [tail_held_cash.py](../multi_asset/exports/research/acting_lead_2026-09-27/devices/tail_held_cash.py) | `3c57770ce` / `e63e3ce025703fcc72701ff12a2c5fb623cf9b59632379e07f9ede9d520abc43` |

## 四、完整本机大包

本次重新读取并计算了下面42个ZIP的SHA256，共6,096,458,378字节。这里只证明本机现存包身份，未再次比对Pod所有成员，也未宣称所有训练输入已永久备份。部分模型/原始输入仍依赖Pod，关机前必须看原COMMAND与manifest。

| 本机绝对路径 | 字节数 | SHA256 |
|---|---:|---|
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/ALLOC_closed_artifacts_20260928.zip` | 814445190 | `9d5bb5d46b68292e69bcde88fa6e433a64f34dfc301daead6fb42fcc52377d56` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_LABEL_PROOFS_20260928.zip` | 2503080 | `652c51630bbcc60878699404d5c38b4fc480118a659ea13cd6379e13fdefb2b0` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_LABEL_REPAIR_CASH_20260928_large.zip` | 604545474 | `553d08822b83a6d632ebf94a4ae10b0efde9ca207603ed2cd24cc871abc41e19` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_LABEL_REPAIR_CASH_20260928_small.zip` | 1170336 | `c2ee99c7cdf1a0765bef4f2b4cc45e6b26ce3e6340dfc4964d2e65c299716a42` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_LIQUID_CASH_20260928_large.zip` | 604294298 | `07e73ad190cf28081b4a9831ab6d60000e42ccaf856181ec12befc577648834b` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_LIQUID_CASH_20260928_small.zip` | 926322 | `64ae859f21168e11b988be4bc068d39f7e5c62c16c0f97708b8ec3ccce8935ec` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_RECENT_ADAPT_CASH_20260928_small.zip` | 1122616 | `64e213694af6b52db7b3cd92be72e69ba1734346abd1f85b63a69d89cef55886` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_RECENT_ADAPT_CASH_DEDUP_20260928_large.zip` | 1079116587 | `6c8eb3116e255e82c4e11528f2dd386cd5342c8a7b98fec2b13b91a15f15aeb9` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_RECENT_ADAPT_CASH_DEDUP_20260928_small.zip` | 1159439 | `caf768a9cca52599b0d1aa1b36d8789fea7b5957a6c94d9ac1f6be2e550d226b` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/F10_RECENT_ADAPT_TRAINED_20260928.zip` | 134970951 | `125041dd61d6e84f3fcc30c01d3d80ecde243525a616f297de29041fab388a23` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/HORIZON_REVIEW_LARGE_ARTIFACTS_20260928.zip` | 531320806 | `36eac94f955740c034273676aa60e50214009902e6d1cc9757860c8e85b2ae0e` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/HORIZON_SEALED_MODELS_20260928.zip` | 45727232 | `370d7c4673a9d453cc11e8b1f2dc0c786f7a06f2f9816bea35044e0b9ff4e8ad` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/NC_LIQUIDITY_BLEND_CASH_PATHS_20260928.zip` | 431133869 | `7112f38edc8152cf5e456f2ca9cfb57bf6af983f0dc1d557cf8f371557c23e6d` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/NC_LIQUIDITY_BLEND_CASH_REVIEW_20260928.zip` | 462050 | `8664245e72a45bf3c5b5ba5f8b0b40dbf6ae99e28a2dd671985be19280dc9a71` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/NC_LIQUIDITY_BLEND_TARGETS_20260928.zip` | 137597596 | `b89c3d3f8055d47b553d96cf3088aa9d26deaadb430e05472f41d577685622b9` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/RECENT_FEATURES_PREDICTIONS_20260928.zip` | 9769740 | `e4a9a5eb60ac1dac5461f69bde987303f249941fefe266d0e171ad1f213495cd` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/RECENT_LEGS_COMBO_20260928.zip` | 1010886 | `acb0d0377b60dbf589d725ba595a9b6978ba3e71c6612bc6458d894949f63554` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/RECENT_PUBLIC_PRICES_20260928.zip` | 91930085 | `b9686fada33ee48dad1c589636d3f793c6584ade67eca2038546883a97d330b8` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/actual_blend_cash.zip` | 1697157 | `fde646849e357c68d53e600beffa6ad7bcdfdd8fb2be2024fafacee815d72c23` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/actual_cash_bridge.zip` | 5344699 | `47de7e01e5d6e472168c7e808bfc53ce1e5b06afb83cd9a492e152e594c31878` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/actual_directional_cash.zip` | 236182 | `20f33b4a6bb12c34ad1d54d3427a99b1938331484f985ebb0c25912c8179d0db` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/actual_target_cash.zip` | 558722 | `4a3a1780bc3e0bf22bbd77aefa812ac8770bd7f1c3750f9c8268e82d437c165f` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/conditional_strength.zip` | 127635875 | `47887faa9209799877614b371d6568a2a44caf8c291e631058e44516c9ee3a60` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/execution_input_census.zip` | 1806343 | `ab7be1f97eca6989b63a61c65c05554a95c77edb93c232ac22d21cd23b2965fb` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/executor_bridge.zip` | 39318867 | `3ddc4e8d03c37ea44fe50269f3528725e45e49f64d442e85389849820e7f53f0` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/fetch_feature_alignment.zip` | 6281233 | `7c4865dee13e0e5e121902537085dfe4827b8c637b3780d1ceef8b9f794c4cf9` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/fetch_membership_boundary.zip` | 135871881 | `d7dc2f5a08aea7b2e44e30f514a89a5ad51056476bc271b4adddc4ca67f3331d` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/gap_history_propagation.zip` | 2054081 | `5d4412ae6283d18853212ef03c934eebd91fa1710ca4688ec20e6526194ef6cd` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/held_strength_cash.zip` | 2313364 | `88fb3136ea997056aae0a286c80618c62e6f39768f87e9976fc7beb99189c01b` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/live_replay_layers.zip` | 63354835 | `750d70e9b1554ab2918cee161adb0bb9ac470f6a71b595eec0447b4b52a8664e` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/lr_recurrence_20260928.zip` | 1919270 | `7778d6685902b73e66d4b0e9c955d3f633f11ee1e3ea66ab5ace8d632facc208` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/own_control_ablation.zip` | 146087397 | `089ca8ab8f382ac0f9ef2fb22fe5995e42117f6900d51786e126b18f950f7669` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/peer_flow_funding_screen.zip` | 267388560 | `b663156a6c4f2997b23a94cc858d872be0cdef7a61212db30cddb289199796b1` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/peer_price_screen.zip` | 215884151 | `b0b23c72523d20a02a22e0502c11e42499a2d44376209adaaf430eae56b4799d` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/recent_nc_cash_complete.zip` | 406803454 | `394d4b858f6d8f01a90298dc26266b552eaf19f301a0a57a773e331d52addc64` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/recovery_order_bridge.zip` | 478899 | `504995df950e50f233c1be14fe10448d3ae895623f10554d549030fe7a2f2d48` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/serving_population.zip` | 145159 | `1b21c25756753cc2b7e1db912010732c904283562a70fb8878c60d3785328008` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/signal_state_trace.zip` | 1987107 | `3f23c469341ebf5ca4d23a1b75877394c07d3f94e45396d82d4d3e8d89abab49` |
| `/Users/haosiyu/.codex/tmp/pod_archive_20260928/tail_risk.zip` | 164154137 | `16b30f78b313f8cd3eb6ce18590b42015b718594d5ed959cb338130f7f5573ad` |
| `/Users/haosiyu/.codex/tmp/state_handoff_cash_20260929/state_handoff_cash_20260929.zip` | 3747462 | `632ed1775fde2029c21e65948a97b6e3163ace68f5c83cfda93a8b410163cf00` |
| `/Users/haosiyu/.codex/tmp/state_handoff_20260929/state_handoff_20260929.zip` | 365069 | `ffdac6c7d3a75d5d2e2d706b7b7107c07b28e16dfd83c81ac66c5b5129d6daf5` |
| `/Users/haosiyu/.codex/tmp/tail_held_cash_20260929/tail_held_cash_20260929_package.zip` | 7817917 | `e812f108d2566a0064a45735fce1020aef28d743afdf50ca8da7310c3126f466` |

## 五、复核边界

- 本次没有重跑历史经济实验；摘要引用冻结收据，历史方法局限沿用。
- 交接验证器另核主件/索引链接、引用提交、当前文件与冻结SHA、暂停状态和任务登记；不能把这些文档验收叫策略通过。
- 本机大包可能含私有账本，路径可交接给账户研究人员，勿直接公开上传。索引不包含密钥。
- 主件、索引及新增交接代码的SHA在 PACKAGE_FILES.json；该清单不包含自身以免循环。最终提交以git为准。
