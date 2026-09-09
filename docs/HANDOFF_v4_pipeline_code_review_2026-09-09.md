# HANDOFF · v4 口径正典重训链: 代码落实现状 + 提交清单 + 复审点(给独立研究员)

> **创建:** 2026-09-09 15:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 交付复审 | **作废条件:** v4 链换装或 RUNBOOK §v4 被下一代配方取代时, 本文只作历史

## §0 一句话结论(先说清「落实到代码」指什么)

- **落实了的**: 修正后的重训链是**可执行、sha 钉住、有收据的脚本**, 全部入库在研究仓 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`(55 个脚本: 50 与 pod2 sha256 逐位一致 + 5 个首轮快照, 差异 0; 清单 `receipts/v4_scripts_sha_full.json`, 与 pod2 `/workspace/review_scratch/` 逐位对账), 配方写在 `docs/RUNBOOK_monthly_retrain_2026-10.md §v4` 八步, 每步有门、门有收据, 审计链 PREREG → 7 个 AMENDMENT → RESULT → 复审接受 全在 docs/。
- **没落实的(明写, 不藏)**: ① 没有单一「一键跑通」的 v4 驱动脚本, 现在是五段 `chain_*.sh` + 判官手工串联; RUNBOOK §1–§4 旧步骤(v3 链: `pod_f10_inputs_chain.sh` / `pod_legs_ext.py` / `pod_f10_refit_ext.py`)仍留在文中, §v4 只是声明「按本节不按上文」; ② **线上生产者 `~/wide_shadow` 仍在跑 v3 旧链训练的 bundle**(09-01 换装), v4 bundle 在 pod2 `/workspace/shadow_bundle_v4`(sha16 16194c70)未换装, 其 `provenance.generation` 仍写 "v3_2026-09"; ③ 三个候选未入正典, 均待用户字: 稳定 trend 构建器(G3 四格 (C))、FIX7 epoch 规则(CONST2027 干净参照研究员 09-07 已完成 20/20 — 本文首版误写「欠」, 复审 b0a573a1 更正; 仍欠 14 天影子 + 用户字)、bundle 代际标签。
- **换装与否不是本文的问题**: 十四格对照全 (C), 措辞只能是「在本合同与窗内未检出差异」; 换装 = 口径纠正, 不是收益主张。

## §1 提交清单(研究仓 `multi-asset-v2`, 2026-09-09, 按主题; 实盘仓另列)

| 主题 | 提交 | 内容 |
|---|---|---|
| 预注册(判据冻结先于数字) | `61af466b` | PREREG v4 链冻结: 全量重训 + 量化 + 临时换装规则 |
| AMENDMENT 1–7 | `ac2d8e6a` `f99ca64e` `59a4860d` `05dd5464` `3f058a7c` `9da34ebf` `b7d49eac` | 1 轴+6 锚/20 折/原始记账免校正 · 2 守卫红=导出漏 env(受据复跑 2.30) · 3 fea89 门读法(后被复审撤回) · 4 扩展窗次级 · 5 legs 文件缺陷(全行重算)⇒ legs v4b 重跑 · 6 V3′ 条款② 同配方参照 · 7 接受复审 c8e2fc13 六项(AMD3 撤回=FAIL 受据; 四处超证据定论撤回) |
| RESULT(进行中→收口) | `7421ea29` `a28a9e10` `32060a3f` `a7d497d3` `e586cbed` `9da34ebf` `92c1a9dd` `f281a44f` `662b2b90` | 链定义/门读数/守卫对账/A0 逐年表 → refit V1 PASS → 首种子 → 谱塌缩假说与撤回 → legs v4b 后谱恢复 → 主判双种子 (C) → 十格全 (C) |
| 装置入库 | `5749a821` `a8b1ef4c` | 门 1/2/守卫/对账/判官/队列脚本 + receipts/; RUNBOOK §v4 八步配方 |
| 口径纠正三轨(前置) | `54a244fc` `69450e9d` `493e9ef4` `ed2c3ea9` `6b4d87e2` `4b41e4f4` | king clamp 消融 (C) / 原始目标正典 / E-0909-B 2022 月档缺口修复→holefix2 / CALIBER_STATUS 账本 / 补洞链第二轮四层逐位门 / E-0909-A 范围闭环 / 接受研究员 9954c158 五项 |
| fea89 稳定 trend(研究员 P1) | `3a90d8cf` `32934194` `878e8836` `98640431` `84bf1003` `aef1213c` | PREREG(闭合门代码推导)→ G1 四条过 → G2 稳定版闭包外差异 0 → G3 首种子 → G3 关闭四格 (C) → 双种子收据分文件 |
| 本次交付 | (本文所在提交, `git log -1 -- docs/HANDOFF_v4_pipeline_code_review_2026-09-09.md`) | 归档补齐 10 个脚本(pod2 逐位) + 判官/泄漏门/臂/收据脚本首轮快照 5 个保留 + 全量 sha 清单 + 本文 |
| 实盘仓 `~/dl_quant_live`(独立复审点, 与重训链无关) | `d040c74` | E-0909-D 执行器传输韧性 + E-0909-E 有限上限拒单具名(电池 129/129); 后续截断补丁排 20Z |

## §2 八步配方 ↔ 脚本 ↔ 门 ↔ 收据(路径相对 `v4_chain_2026-09-09/`; 上一级 `retrain_2026-09/` 的基础脚本以 `../` 标)

| 步 | 逻辑 | 执行脚本 | 门 / 判官 | 收据 |
|---|---|---|---|---|
| 1 | 5m 缓存 = holefix2 正典(2022 官方月档缺口 49 名用日档修复)+ 原始收益补丁 952 bar | `../caliber_program_2026-09-09/holefix2_daily.py`, `v4_hole_cells.py`, `run_raw32.sh` + `patch_targets_raw_inplace.py` | `cache_coverage_gate_v2.py`(首末日排除, 洞 0/宽缺口 0) | `receipts/holefix2_cells.json`, `cov2_holefix2_rerun.log`, `PROVENANCE_v4_chain.json` |
| 2 | king 特征 E−w clamp ≥ 0(E-0909-A 回绕缺陷) | `pod_fea_ext_clamp.py`(由 `chain_v4_data.sh` 调) | `v4_gate_step2.py`(+`_diag`): 与上代差异只在缓存改动邻域 | `step2.json`, `step2_diag.json` |
| 2′ | 候选: fea89 trend_288/2016 稳定局部算法(全局累积和对死名 NaN 翻转) | `pod_f8_build_stable.py`(= 构建器逐字, 只换 trend 块), `stable_trend.py`, `make_f8_stable.py`, `chain_fea89_stable.sh` | G1 `stable_trend.py` 合成; G2 `v4_gate_closure.py`(代码推导逐列闭包表); `trend_nanflip_check.py`, `trend288_receipt.py` | `stable_trend_G1_synthetic.json`, `G2_closure_stable.json`, `G2_closure_global.json`, `trend288_receipt*.json`, `F10_GATE_RAW_v4s.json` |
| 3 | DL 目标 = 记账 y4s 原始收益(RET_CH=0 + 补丁); fea82/fea89 同法 | `pod_dlw_targets_raw.py`, `../pod_dlw_features_ext.py`, `../pod_f8_build_ext.py`(`chain_v4_data.sh`) | `v4_gate_step1.py`(+`_diag`,`_diag2`): RAW vs CLIP 差异恰为补丁窗 | `step1.json`, `STEP1_VERDICT.json`, `STEP1_PASS`, `step1_diag*.json` |
| 4 | legs = 在役训练行逐位原样 + 新锚同公式(禁全行重算) | `pod_legs_v4b.py`(正典); `pod_legs_v4.py` = 错误版留作证据(AMENDMENT 5) | 单折干预 D2/D3: `pod_f10_train_monthly_diag.py`, `diag_legs_setup.py`, `diag_compare.py`, `diag_launch.sh` | `legs_v4.log`, `diag_202507.json`, `diag_quickstats.log` |
| 5 | king 导出, env 逐字 `EXPORT_PANEL=<splice> EMA_STATE_JSON=<canoncont> BUNDLE_BASE=<上代 own fold IC>`; 守卫带 2.27–2.57 | `pod_export_bundle_v4.py`(命令原文 `receipts/v4_commands.txt` L1/L3) | `guard_book_lib.py`(逐字基线书) + `guard_reconcile.py` + `guard_decompose.py`: 先复现上代 2.284/1.024 再报 | `export_v4.log`, `export_v4_run1_v2extpanel.log`(漏 env 那次 1.96 红, 留作证据), `guard_reconcile.json`, `guard_decompose.json`, `bundle_v4_MANIFEST.json`, `bundle_v4_config.json` |
| 6 | F10 月折 FIX7(BEST_EP_FIX=7, EMBARGO=1, 20 折)+ refit FIX7; V1 np≡torch; V3′ 条款② 同配方参照 | `pod_f10_train_monthly_v4.py` / `launch_mwf_v4b.sh` / `chain_v4_gpu3.sh` / `merge_mwf_v4b.py`; refit `pod_f10_refit_v4.py`; 稳定变体 `pod_f10_train_monthly_v4s.py` / `launch_mwf_v4s.sh` / `chain_v4s_gpu.sh` / `merge_mwf_v4s.py`; 首轮(坏 legs)`launch_mwf_v4.sh`/`merge_mwf_v4.py`/`chain_v4_gpu2.sh` 留作证据 | V1 在 merge 收据; V3′ `v4_leakcheck.py`(首轮快照 `v4_leakcheck.r1_*.py`) | `merge_v4b_*_s{42,2027}.json`, `merge_v4s_RAW_s{42,2027}.*`, `V3P_*_amd6*.json`, `F10_GATE_{RAW,CLIP}.json` |
| 7 | 书层量化: dev 树 meta y4 用原始收益; 判官先复现已发表数字(A0p 同代输入逐位); 冻结窗主判 + 扩展窗次级; 双种子双席位; 逐年表负年显式 | `build_dev_v4.py`, `build_a0p.py`, `run_v4_arms.sh`(A0/A0p/A1/A1s/A2/A3 × dyn/fix × s42/s2027; 首轮快照 `.r1_*`), `judge_v4.py`(冻结 §4; 首轮快照 `.r1_*`) | `judge_v4.py` 内置 REPRO(#20)+ 每对照 RNG 子流 | `a0p_vintage.json`, `build_dev_v4.log`, `JUDGE_v4.json`(首轮), `JUDGE_v4_g3_s2027.json`(终), `g3_*.log`, `replay_regime_beta.json`(实盘诊断用) |
| 8 | 易错清单 | RUNBOOK §v4 第 8 条 | — | `v4_commands.txt`(全部命令原文与时间戳) |

`make_v4_scripts.py` = 从 v3 基底生成 v4 变体脚本的生成器(Δ 记档在各脚本头部); `../base_*.py` 为 v3 基底。

## §3 冻结窗对照终表(2025-03-01→2026-08-10 20Z, bps/锚/gross; 判官 `judge_v4.py`, 每对照 RNG 子流 `[20260905, k]`, UTC 日块 bootstrap 2000)

| 对照 | 席位 | s42 Δ [CI95] | s2027 Δ [CI95] | 判决 |
|---|---|---|---|---|
| A1−A0 全量重训(king v4 + F10 v4 RAW/FIX7) vs 在役形态 | 动态 | +0.061 [-0.168, +0.287] | +0.048 [-0.171, +0.270] | (C) UNDECIDED |
| A1−A0 全量重训(king v4 + F10 v4 RAW/FIX7) vs 在役形态 | 固定 0.21 | +0.005 [-0.076, +0.087] | -0.010 [-0.102, +0.088] | (C) UNDECIDED |
| A2−A0(F10 CLIP 标签) | 动态 | +0.083 [-0.140, +0.308] | +0.014 [-0.205, +0.241] | (C) UNDECIDED |
| A2−A0(F10 CLIP 标签) | 固定 0.21 | +0.007 [-0.078, +0.096] | -0.006 [-0.093, +0.082] | (C) UNDECIDED |
| A3−A0(king v4 + 在役 F10) | 动态 | +0.015 [-0.169, +0.204] | +0.081 [-0.105, +0.276] | (C) UNDECIDED |
| A3−A0(king v4 + 在役 F10) | 固定 0.21 | -0.019 [-0.089, +0.050] | +0.001 [-0.078, +0.084] | (C) UNDECIDED |
| A1−A2(RAW vs CLIP 标签) | 动态 | -0.022 [-0.077, +0.041] | +0.034 [-0.013, +0.082] | (C) UNDECIDED |
| A1−A2(RAW vs CLIP 标签) | 固定 0.21 | -0.002 [-0.062, +0.046] | -0.005 [-0.033, +0.021] | (C) UNDECIDED |
| A1−A3(F10 重训 vs 在役 F10, king 同) | 动态 | +0.045 [-0.100, +0.190] | -0.033 [-0.179, +0.110] | (C) UNDECIDED |
| A1−A3(F10 重训 vs 在役 F10, king 同) | 固定 0.21 | +0.023 [-0.031, +0.072] | -0.011 [-0.066, +0.040] | (C) UNDECIDED |
| A1s−A0(稳定 fea89 + v4 链) vs 在役 | 动态 | +0.095 [-0.138, +0.320] | +0.056 [-0.161, +0.259] | (C) UNDECIDED |
| A1s−A0(稳定 fea89 + v4 链) vs 在役 | 固定 0.21 | +0.016 [-0.075, +0.107] | -0.017 [-0.110, +0.072] | (C) UNDECIDED |
| A1s−A1(稳定 vs 全局 trend, 其余同) | 动态 | +0.035 [-0.013, +0.085] | +0.009 [-0.032, +0.049] | (C) UNDECIDED |
| A1s−A1(稳定 vs 全局 trend, 其余同) | 固定 0.21 | +0.012 [-0.023, +0.056] | -0.007 [-0.033, +0.019] | (C) UNDECIDED |

读法: (A)=两种子点估计>0 且 CI 下界>0; (B)=两种子 CI 上界<0; 其余 (C) UNDECIDED, **不得写「不劣」**。全形态 2023 年为负(逐年表在 `g3_judge_s2027.log`)。

## §4 请重点复审的点

- **R1 legs 策略等价性**: `pod_legs_v4b.py`「在役行逐位 + 新锚同公式」与生产者 `shadow_loop_v3.py` 运行时 legs 是否同公式; 分年 WL 自检(2023 king ≈0.59)是否足以证明 2023 席位未被清零。
- **R2 clamp 同定义**: `pod_fea_ext_clamp.py` 的 E−w clamp 与生产者运行时 clamp(`shadow_loop_v3.py` L357–363/L390 + 40 天缓冲)逐算子同序。
- **R3 目标口径**: `pod_dlw_targets_raw.py` y4s = Π(1+r)−1 记账口径, 与 `pod_dlw_targets_ext.py` L93 定义逐位; RAW/CLIP 训练标签「书层无差」(A1−A2)的证据是否够(双种子反号, 装置分辨率内)。
- **R4 判官**: `judge_v4.py` 的冻结 §4 与 `PREREG_king_clip_label_ablation §4` 逐字; A0p 复现 #20 的 paired max|Δ|; 首轮快照 `.r1_*` 与终版差异只在 A1s 臂 + AMD6 env(请 diff)。
- **R5 归档一致性**: 复算 `receipts/v4_scripts_sha_full.json`: 研究仓脚本 sha 与 pod2 逐位; 我方声明「归档 = 产出收据的版本」。
- **R6 可复跑性**: 仅凭 RUNBOOK §v4 + 本归档能否在新机器复跑八步(缺哪些 env/路径/数据件); 是否需要 `chain_v4_all.sh` 单驱动 + 旧步骤作废横幅(我方建议做, 未做)。
- **R7 闭包门**: `v4_gate_closure.py` 的 EXPLICIT 逐列回看表(E/J/B/F 族, H 8688, membership 2016)是否与列定义一致; AMD3 首版「trend_288 残差」读法错在哪, 现版是否封死同类错。
- **R8 因果声明**: AMENDMENT 5 用 D2(换 legs)/D3(重训)单折干预支撑「legs 文件是谱塌缩之因」, 单折证据是否够。

## §5 明写的限制

数字全部 VERIFIED 于收据文件; 2023 负年在所有形态; 尾部一律下界; 扩展窗(→08-31 20Z)只是次级读数; jpline 不可达, V4 跨机 np 门未做; 换装决定与本文无关, 归用户。
