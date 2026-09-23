> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(执行代理,lead 派出) | **状态:** RESULT · 预注册 `docs/PREREG_f10_seed_ensemble_book_2026-09-23.md`(45aba1f3f,sha 56acd832)的判决已出 = **FAIL**;执行口径 `ENS_OPERATIONALISATION.json` 写于任何 NAV 读取之前并先入库(d50eb890f);**不含换装建议** | **作废条件:** 预注册 45aba1f3f 或 Stage 1 预注册/修订 1(8530d2b7f / 70adc6cac)的设置改动;Stage 1 的 NEW_s42 / NEW_s2027 主读数路径文件被重算;NEW_ENS 目标(TARGETS_NEW_ENS ea6d20f6 / combo_ENS scaled 22d527b7)或装置 `ens_*.py` 被证伪

# 结果:F10 双种子等权排名平均的整书检验

相关:动机 `docs/ANALYSIS_multi_seed_ensemble_2026-09-23.md`;依赖 `docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md` + `docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md`;Stage 1 装置 `multi_asset/exports/research/old_vs_new_2026-09-23/`(e6d8f6680)。本检验的装置与收据:`multi_asset/exports/research/f10_ens_2026-09-23/{devices,receipts,logs,configs,targets}`。

## §0 判词

判词行原文(`ens_stats.py`,退出码 0,日志 `logs/ens_stats.log`):

```
ENS_STATS E1 vs NEW_s42: FAIL est -0.629 bps/d 97.5%CI30 [-4.329, +2.102] n_days 915
ENS_STATS E1 vs NEW_s2027: FAIL est +0.735 bps/d 97.5%CI30 [-2.648, +3.586] n_days 915
ENS_STATS E2 PASS 2023H2:ENS -0.571/floor -0.938 2024:ENS 1.879/floor 1.681 2025:ENS 1.643/floor 1.597
ENS_STATS E3 PASS ENS 0.05557 limit 0.05651
ENS_STATS E4 PASS ENS -0.1799 floor -0.1911
ENS_STATS VERDICT=FAIL receipt_sha256=806b008af49d3080f67a4109daf2dfbf7aff9884f8705dde4d0c4c27b07bac46
```

**白话**:
- 四条判据里只有 E1(非劣)没过,对两个单种子都没过。E2(不制造新的最差段)、E3(换手)、E4(回撤)都过了。
- E1 没过的方式要看清:相对 s42 的点估计是 −0.63 bps/日,相对 s2027 是 +0.74 bps/日,方向相反;两个区间都跨过 0。但两个 97.5% 区间的半宽约 **3.2 / 3.1 bps/日**,是非劣门(−0.5 bps/日)的 6 倍多。所以这里的 FAIL 意思是"**在这段样本上没能证明不变差**",**不是**"证明了变差"。这是对结果的读法,判词本身不改。
- 按预注册 §3,FAIL ⇒ 维持单种子,记录。本文不做换装建议,由 lead 与用户裁定。

## §1 判据与同报(由 `ens_render.py` 从 `receipts/ENS_STATS.json` sha 806b008a 渲染,数字未手抄)

### E1–E4(判据, pre-2026)

| # | 实测 | 门 | 判 |
|---|---|---|---|
| E1 vs s42 | d̄ = -0.629 bps/日, 97.5% 区间(30 日块) [-4.329, +2.102], n = 915 日 × 32 路径 | 下界 > −0.5 | FAIL |
| E1 vs s2027 | d̄ = +0.735 bps/日, 97.5% 区间(30 日块) [-2.648, +3.586], n = 915 日 × 32 路径 | 下界 > −0.5 | FAIL |
| E2 2023H2 | Sharpe ENS -0.571(s42 -0.783 / s2027 -0.888) | ≥ -0.938 | PASS |
| E2 2024 | Sharpe ENS 1.879(s42 1.851 / s2027 1.731) | ≥ 1.681 | PASS |
| E2 2025 | Sharpe ENS 1.643(s42 1.888 / s2027 1.647) | ≥ 1.597 | PASS |
| E3 | 换手/gross ENS 0.05557(s42 0.05720 / s2027 0.05043) | ≤ 0.05651 | PASS |
| E4 | 5m 最大回撤 ENS -17.99%(s42 -18.11% / s2027 -17.61%) | ≥ -19.11% | PASS |

**判词: FAIL**

E1 旁报(非判据):

| 对照 | 95% 区间(30 日块) | 97.5% 区间(5 日块) | 含 2023-06-30 半日 | 逐段 d̄ bps/日 2023H2 / 2024 / 2025 / 2026 |
|---|---|---|---|---|
| ENS − s42 | [-3.827, +1.834] | [-3.570, +2.095] | -0.568 [-4.351, +2.128],改判 E1: False | +0.962 / +0.128 / -2.190 / -0.408 |
| ENS − s2027 | [-2.161, +3.265] | [-2.237, +3.602] | +0.697 [-2.659, +3.584],改判 E1: False | +1.168 / +0.855 / +0.397 / +0.254 |

### §4.1 逐段三方对照(32 路径均值;[2.5%, 97.5%] 路径分位)

| 段 | 臂 | Sharpe | 总收益 | CAGR | 5m 最大回撤 | 最差日 | 价格+成交 | 资金费(付) | 手续费 | 未知剔除 | g | 换手/gross | §4-2 平仓 | 逐名止损 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023H2 | ENS | -0.571 [-0.79, -0.36] | -2.75% | -5.35% | -15.27% [-16.3, -14.2] | -4.45% | +0.023 | -0.016 | 0.137 | 0.000 | -0.099 | 0.0541 | 1.0 | 76.6 |
| 2023H2 | s42 | -0.783 [-0.99, -0.49] | -4.96% | -9.55% | -14.76% [-16.1, -13.1] | -3.08% | -0.053 | +0.014 | 0.135 | 0.000 | -0.202 | 0.0538 | 0.3 | 74.6 |
| 2023H2 | s2027 | -0.888 [-1.12, -0.59] | -4.41% | -8.51% | -15.02% [-16.0, -14.0] | -4.09% | +0.017 | +0.059 | 0.138 | 0.000 | -0.179 | 0.0545 | 1.0 | 87.1 |
| 2024 | ENS | 1.879 [1.77, 2.06] | +41.68% | +41.55% | -13.14% [-13.9, -12.2] | -3.83% | +1.152 | +0.159 | 0.154 | 0.000 | +0.838 | 0.0618 | 0.5 | 367.0 |
| 2024 | s42 | 1.851 [1.67, 2.00] | +41.01% | +40.88% | -13.73% [-14.9, -12.4] | -3.75% | +1.146 | +0.155 | 0.162 | 0.000 | +0.829 | 0.0649 | 0.2 | 357.1 |
| 2024 | s2027 | 1.731 [1.57, 1.91] | +37.37% | +37.25% | -12.94% [-14.2, -11.7] | -3.71% | +1.059 | +0.158 | 0.134 | 0.000 | +0.768 | 0.0537 | 0.4 | 471.0 |
| 2025 | ENS | 1.643 [1.49, 1.79] | +53.10% | +53.10% | -12.05% [-13.0, -11.4] | -4.48% | +1.593 | +0.412 | 0.128 | -0.000 | +1.052 | 0.0500 | 3.5 | 645.4 |
| 2025 | s42 | 1.888 [1.69, 2.05] | +65.58% | +65.58% | -12.40% [-13.2, -11.8] | -4.78% | +1.784 | +0.420 | 0.131 | 0.000 | +1.232 | 0.0512 | 3.3 | 643.6 |
| 2025 | s2027 | 1.647 [1.47, 1.86] | +51.32% | +51.32% | -12.06% [-12.9, -11.5] | -4.46% | +1.531 | +0.393 | 0.116 | -0.000 | +1.022 | 0.0451 | 3.2 | 524.8 |
| pre2026 | ENS | 1.364 [1.28, 1.47] | +110.92% | +34.63% | -17.99% [-19.5, -16.4] | -4.52% | +1.100 | +0.225 | 0.141 | -0.000 | +0.734 | 0.0556 | 4.9 | 1089.1 |
| pre2026 | s42 | 1.445 [1.35, 1.55] | +121.91% | +37.37% | -18.11% [-20.3, -15.8] | -4.78% | +1.158 | +0.232 | 0.144 | 0.000 | +0.782 | 0.0572 | 3.9 | 1075.3 |
| pre2026 | s2027 | 1.285 [1.21, 1.39] | +98.65% | +31.44% | -17.61% [-19.5, -15.8] | -4.49% | +1.037 | +0.232 | 0.128 | -0.000 | +0.678 | 0.0504 | 4.6 | 1082.8 |
| 2026 | ENS | 4.254 [3.95, 4.59] | +136.06% | +265.11% | -19.66% [-20.7, -18.4] | -4.65% | +4.290 | +1.099 | 0.123 | 0.000 | +3.068 | 0.0479 | 2.2 | 320.9 |
| 2026 | s42 | 4.249 [4.00, 4.54] | +138.27% | +270.25% | -19.73% [-20.9, -18.2] | -4.81% | +4.326 | +1.099 | 0.125 | 0.000 | +3.101 | 0.0485 | 2.6 | 319.6 |
| 2026 | s2027 | 4.251 [3.95, 4.60] | +134.66% | +261.81% | -19.43% [-20.4, -18.2] | -4.58% | +4.269 | +1.099 | 0.123 | 0.000 | +3.047 | 0.0479 | 2.1 | 322.3 |

(价格+成交 / 资金费 / 手续费 / 未知剔除 / g 单位: bps 每锚每单位目标 gross;g = 价格 − 资金费 − 手续费 − 未知,逐窗断言 ≤ 1e-9)

### §4.2 分数层平均(ENS)vs 资金层平均(50/50 分仓,逐 UTC 日再平衡)

| 段 | 臂 | Sharpe(完整日) | 完整日总收益 | 最差日 | 日频 NAV 最大回撤 | d̄(ENS − 50/50) bps/日 |
|---|---|---|---|---|---|---|
| 2023H2 | ENS | -0.571 | -5.30% | -4.45% | -14.28% | +1.065 |
| 2023H2 | 50/50 | -0.856 | -7.07% | -3.57% | -13.58% |  |
| 2024 | ENS | 1.879 | +41.68% | -3.83% | -12.36% | +0.491 |
| 2024 | 50/50 | 1.816 | +39.24% | -3.69% | -12.02% |  |
| 2025 | ENS | 1.643 | +53.10% | -4.48% | -10.32% | -0.897 |
| 2025 | 50/50 | 1.815 | +58.57% | -4.46% | -10.19% |  |
| pre2026 | ENS | 1.364 | +105.38% | -4.52% | -17.12% | +0.053,97.5% [-3.271, +2.267],95% [-2.698, +2.074] |
| pre2026 | 50/50 | 1.396 | +105.17% | -4.46% | -16.16% |  |
| 2026 | ENS | 4.254 | +134.76% | -4.65% | -18.67% | -0.077 |
| 2026 | 50/50 | 4.259 | +135.16% | -4.61% | -18.61% |  |

### §4.3 目标距离(scaled_diagnostic 组合目标;L1 = Σ|w_X − w_Y|)

| 对 | 年/段 | raw L1 逐锚均值 | 两者平均 gross | L1/gross | n_eff 锚 | 同时发布锚上权重 L1 | n_eff |
|---|---|---|---|---|---|---|---|
| ENS|s42 | 2023 | 0.0813 | 0.4889 | 0.166 | 2190 | 0.0780 | 1532 |
| ENS|s42 | 2024 | 0.0476 | 0.5629 | 0.085 | 2196 | 0.0457 | 1801 |
| ENS|s42 | 2025 | 0.0480 | 0.5277 | 0.091 | 2190 | 0.0418 | 1616 |
| ENS|s42 | 2026 | 0.0236 | 0.6976 | 0.034 | 1566 | 0.0236 | 1566 |
| ENS|s42 | pre2026 | 0.0536 | 0.5317 | 0.101 | 5495 | 0.0486 | 4147 |
| ENS|s2027 | 2023 | 0.0792 | 0.4922 | 0.161 | 2190 | 0.0759 | 1545 |
| ENS|s2027 | 2024 | 0.0486 | 0.5521 | 0.088 | 2196 | 0.0446 | 1576 |
| ENS|s2027 | 2025 | 0.0494 | 0.5227 | 0.094 | 2190 | 0.0402 | 1508 |
| ENS|s2027 | 2026 | 0.0231 | 0.6979 | 0.033 | 1566 | 0.0231 | 1566 |
| ENS|s2027 | pre2026 | 0.0541 | 0.5252 | 0.103 | 5495 | 0.0472 | 3796 |
| s42|s2027 | 2023 | 0.1534 | 0.4909 | 0.313 | 2190 | 0.1457 | 1482 |
| s42|s2027 | 2024 | 0.0901 | 0.5567 | 0.162 | 2196 | 0.0828 | 1576 |
| s42|s2027 | 2025 | 0.0889 | 0.5249 | 0.169 | 2190 | 0.0703 | 1487 |
| s42|s2027 | 2026 | 0.0391 | 0.6978 | 0.056 | 1566 | 0.0391 | 1566 |
| s42|s2027 | pre2026 | 0.1004 | 0.5281 | 0.190 | 5495 | 0.0864 | 3751 |

### §4.4 发布资格(scaled_diagnostic trade_mask)

| 段 | 锚 | 发布 ENS | 发布 s42 | 发布 s2027 | ENS≠s42 | ENS≠s2027 | s42≠s2027 | ENS 未发布原因 |
|---|---|---|---|---|---|---|---|---|
| 2023H1_pre_window | 1081 | 843 | 805 | 901 | 44 | 78 | 118 | gross 238 |
| 2023H2 | 1109 | 757 | 753 | 757 | 50 | 90 | 134 | gross 352 |
| 2024 | 2196 | 1803 | 1931 | 1576 | 132 | 227 | 355 | gross 393 |
| 2025 | 2190 | 1640 | 1668 | 1508 | 76 | 132 | 202 | gross 550 |
| 2026_to_0831 | 1453 | 1453 | 1453 | 1453 | 0 | 0 | 0 | — |
| 2026-08-31T04Z_to_axis_end | 113 | 113 | 113 | 113 | 0 | 0 | 0 | — |

仅一个种子有限的名字: 全文件轴 10321 锚合计 **0** 名,出现于 0 锚。


### 读这些表(白话,只描述)

- **逐段**:ENS 的 Sharpe 在 2023H2(−0.571)和 2024(1.879)都高于两个单种子;2025(1.643)落在两者之间,低于 s42(1.888),和 s2027(1.647)相当。pre-2026 合并 Sharpe 1.364、总收益 +110.9%,都落在 s42(1.445 / +121.9%)与 s2027(1.285 / +98.7%)之间。
- **派生算术(非自举)**:两个 E1 点估计之差 = pre-2026 的 d̄(s42 − s2027) = +0.735 − (−0.629) = **+1.364 bps/日**(同 32 条路径、同 915 日,均值恒等式成立)。也就是说,这段历史里两个单种子本身的差比 ENS 与任一方的差都大,ENS 大致落在中间。
- **2026(只报告,与选型样本重合)**:三本书几乎一样(Sharpe 4.254 / 4.249 / 4.251)。原因可以从 §4.3/§4.4 直接读到:2026 三者每锚都发布(1,453/1,453,零分歧),目标距离也最小(L1/gross 约 0.03–0.06)。
- **分数层平均 vs 资金层平均**:pre-2026 的 d̄(ENS − 50/50 分仓) = **+0.053 bps/日**,97.5% 区间 [−3.271, +2.267];分段一正一负(2023H2 +1.065、2024 +0.491、2025 −0.897、2026 −0.077)。在这段数据上,把两个种子的分数先平均,与把资金一分为二各跑一本书,**分不出差别**。
- **目标距离**:pre-2026 的逐锚 raw L1,ENS−s42 0.0536、ENS−s2027 0.0541、s42−s2027 0.1004(相对平均 gross 分别约 10% / 10% / 19%)。ENS 落在两种子中间,和"排名平均"的构造一致。种子分歧在 2023 年最大(s42−s2027 为 gross 的 31%)。
- **发布资格**:pre-2026 发布资格不同的锚数,ENS≠s42 共 258(50+132+76),ENS≠s2027 共 449,s42≠s2027 共 691;2026 为 0。ENS 未发布的原因全部是 gross 门(scaled_diagnostic),没有一锚因 F10 覆盖不发布(两个单种子的原因本文没有逐项列)。
- **其它同报量**:pre-2026 的 §4-2 日止损平仓,路径均值 ENS 4.9、s42 3.9、s2027 4.6;逐名止损 1,089 / 1,075 / 1,083。这些不是本预注册的判据,照报。

## §2 做了什么(装置链,每步都有收据)

| 步 | 做法 | 结果 / 收据 |
|---|---|---|
| 1 读懂 F10 的消费方式 | `ens_dump.py`:先 dump 真实键名与形状,再从钉住 sha 的源码逐字引出消费行(`combo_target.step()` 对**成员内**有限 F10 做 `rankdata`,发布门数的是成员内有限个数) | F10_OOF 键 = `P float32 (10321,829)` / `E_ts int64` / `symbols <U15`;组合轴 8,142 锚上两种子的有限集**都等于成员集**;仅一方有限 = **0**。`receipts/ENS_DUMP.json` |
| 2 造 F10_ENS | `ens_build.py`:每锚两种子都有限的名字各自 `rankdata`(average,与组合同一排名器),ENS = (r42 + r2027 − 2)/(2·max(nb−1,1)),一次除法,相同秩和逐位相同;float32;断言 float32 截断不改变秩结构 | `F10_ENS.npz` d66a092a;全文件轴 10,321 锚 **仅一方有限的名字 = 0**;往返逐位。`receipts/ENS_BUILD.json` |
| 2′ 红绿测试 | `ens_build_test.py`,真实输入:基线先绿(①同种子时按组合的消费算术 zf 逐位相同,8,142 锚;②人造一名只在一个种子有限 ⇒ 该名 NaN、计数 1、其它锚逐位不变;③往返),再 4 个变异按名变红 | `VERDICT=PASS baseline=GREEN(3/3) mutations_red_as_named=4/4`。`receipts/ENS_BUILD_TEST.json` |
| 3 生成 NEW_ENS 组合目标 | `ens_combo.py` = 研究员 `continuous_combo.main()`(1501c9f6)逐句转录,只换两处:F10 分数文件、输出目录;研究员的 `evolve` / `verify_training` / `combo_target.step` / `combo_stage` 内核只读导入(`python -B`);ENS 模式对两个种子的训练链都做 main() 原样的校验 | NEW_ENS:scaled_diagnostic **22d527b7**(发布 6,609)、literal 65113808(发布 3,086)。`receipts/NEW_ENS_TARGET_RECEIPT.json` |
| 3′ 装置正控 | 同一装置 `--f10 s42` 重新生成 | 产物**文件 sha** 与研究员 combo_s42 完全相同(scaled 4dec6b38、literal cae52acf);`ens_combo_compare.py` 逐数组逐位相等,且 +1 ulp 红检能检出:`ENS_COMBO_COMPARE VERDICT=PASS scaled_equal=True literal_equal=True red_capability_one_ulp_detected=True`。`receipts/ENS_POSCTL_COMPARE_s42.json` |
| 4 转认证格式 | Stage 1 的 `ovn_adapter.py`(17555e56,原样复制并校验 sha),不另写 | `OVN_ADAPTER VERDICT=PASS arm=NEW_ENS npz_sha256=ea6d20f6… roundtrip=bitwise scaled_published=6609 lit_published=3086 pad=1110`(补前置空持 1,110 锚,与 s42 相同);Stage 1 的 `ovn_adapter_test.py` 于 NEW_ENS:`VERDICT=PASS baseline=GREEN mutations_red_as_named=5/5`。`receipts/TARGETS_NEW_ENS.json`、`receipts/OVN_ADAPTER_TEST_NEW_ENS.json` |
| 5 冻结配置并运行 | `ens_make_config.py`:以 Stage 1 的 `RUN_CONFIG_OVN_NEW_s42_2026-09-23.json`(162239b6)为模板复制;叶级 diff 先断言后写 | `RUN_CONFIG_F10ENS_NEW_ENS` **6bbfb181**;diff 63 个叶,全部属于:标签、运行命名、目标 arm/来源、谱系、`paths.pod_root`(见 §3 D1)。`receipts/ENS_CONFIG_DIFF.json`。认证运行器 `bt_launch.py`(393a8dc8)主读数 32 条路径 `rc 0`;`AGG` 收据记录 config_sha256 = 6bbfb181、32 个路径文件 |
| 5′ 复用 Stage 1 的单种子 NAV | 不另跑;统计时断言身份 | Stage 1 两个配置 sha = 162239b6 / 54afef27(= e6d8f6680 入库版);Stage 1 启动收据 `BT_LAUNCH_full_ovn_new_s{42,2027}_r2.json` 的配置 sha 与之相等;3×32 条路径的 `run` 字典都等于各自配置的主运行;NEW_ENS 与 NEW_s42 的运行字典只差 arm/tag/role/targets.arm/targets.sources;`calibration_params_used` 96 条路径全同。`receipts/ENS_STATS.json` preconditions |
| 6 统计 | `ens_stats.py`:逐路径指标函数逐字取自 Stage 1 的 `ovn_stats.py`(1208eb43),底层 `bt_tables.py` 892ba66b;E1 自举 30 日块,B = 10,000,rng [20260923, 2],每个对照各自新建 | `receipts/ENS_STATS.json` 806b008a;表格由 `ens_render.py` 从该收据渲染 |

提交:运行前落盘 d50eb890f(装置 + 执行口径 + ENS 构造 + 测试 + 正控);目标/配置 e5cc88ba3;本文与统计收据见本次提交。

## §3 偏离与运维事件(判据、窗口、读数、权重、种子集合:**无任何改动**)

- **D1 输出根**:配置里 `paths.pod_root` 从 `/dev/shm/ovn_2026-09-23` 改为 `/dev/shm/f10_ens_2026-09-23`。这是输出位置,不是设置;保留原值会把本臂的路径文件写进 Stage 1 的目录(本任务禁止)。已写进 diff 收据,并在统计时断言"配置除标签/目标/命名/谱系/pod_root 外完全相同"。
- **D2 /workspace 配额满(08:25Z,`Disk quota exceeded`)**:第一次生成 NEW_ENS 组合(PGID 2229566)在写 scaled 文件时死掉,留下 0 字节临时文件,日志也写不进(空日志、无 EXIT 行)。之后工作根移到 `/dev/shm/f10_ens_2026-09-23`(装置逐个 sha 相同),第二次(PGID 2231024)`EXIT 0`。/dev/shm 不持久,所以所有产物都有 sha 相同的本地副本(`targets/`),其中 `F10_ENS.npz` 与 `TARGETS_NEW_ENS.npz` 已入库。
- **D3 静默没写成的上传**:配额满时一次 scp 报 `close remote: Failure`,回读 sha 一度显示新值,后来读到的是旧内容。此后每次上传都按 sha 回读核对。
- **D4 执行口径时间戳**:`ENS_OPERATIONALISATION.json` 初稿把 written_utc 写成 08:35Z,实际文件时间 08:21Z;在读任何 NAV 之前已改正,并在文件里注明。
- **D5 停掉非判据运行**:冻结配置沿用模板的 5 个运行(主读数 + lit + 3 个成本格),目的是让设置逐字节相同;本预注册只用主读数。主读数完成后,我按自己记录的 PGID 2232812 停掉了其余运行(lit 已写 8/32 条路径,未使用;成本格未开始)。后果:运行器只在结束时写的启动收据 `BT_LAUNCH_full_f10ens_new_ens.json` 不存在,启动日志也没有 EXIT 行。主读数的证据 = 启动日志(钉子全 OK + 主运行 32 行 `rc 0`)、AGG 收据(config 6bbfb181、32 个路径文件)、`NEW_ENS_main_PATH_SHA256SUMS.txt`,以及统计装置的 P0/P1 校验。
- **D6 Stage 1 的启动收据带 `_r2` 后缀**:说明 Stage 1 的 NEW 臂用 `--resume` 重新启动过。其配置 sha 与入库版相同,路径文件在读取时逐个按其 json 的 sha 核对。原因我没去查(不在本任务范围)。

## §4 局限

1. 只有两个种子:**无法估计集成对种子方差的削减量**(预注册 §4.5)。本检验只能检"不变差",而且没能证明。
2. **E1 的分辨率**:915 个完整日上,d̄ 的 97.5% 区间半宽约 3.1–3.2 bps/日,非劣门是 0.5 bps/日。本次区间下界在点估计之下 3.70(对 s42)/ 3.38(对 s2027)bps/日;按这个距离推算(派生,非判据),点估计大约要 ≥ +2.9 至 +3.2 bps/日 才能让下界高于 −0.5。也就是说,在这个样本量和噪声下,E1 能认证的只有"明显更好",认证不了"差不多"。这是读结果时必须知道的事实,**不是**改门的理由。
3. 发布门是 scaled_diagnostic(历史诊断口径),不是现役 literal 门;2026 与选型样本重合,只报告;R-P / R-P2、成本格、08-31→09-18 延长窗都不在本预注册里,没有计算。
4. 本检验只在 NEW 模型家族内部比较,与 OLD / OLD_HOLD 无关,不回答 Stage 1 的问题。

## §5 本文不下的结论

- 不说"集成更好"或"集成更差";不引用任何"收益更高"的数字作宣传(预注册 §3 明文禁止)。
- 不提换装或改重训配方的建议。预注册写的后果是"FAIL ⇒ 维持单种子,记录";是否以及如何再检验,由 lead 与用户决定,且必须另立预注册。

## §6 复跑命令(逐字)

pod2;前 5 条(dump、build、test、正控、比较器)在 `/workspace/f10_ens_2026-09-23/devices` 运行,之后(D2)在 `/dev/shm/f10_ens_2026-09-23/devices` 运行。变量:
`V1D=/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d`、`CT=/workspace/codex_research/QNT-2026-0907/combo_20260923/devices/combo_target.py`、`U=/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz`、`PY="env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B"`、`R=/workspace/f10_ens_2026-09-23`、`D=/dev/shm/f10_ens_2026-09-23`。

```
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ens_dump.py PATH,HOME,LC_CTYPE ../receipts/ENS_DUMP.json
./ens_detach.sh ens_build -- $PY ens_build.py PATH,HOME,LC_CTYPE $V1D/f10_s42/F10_OOF.npz bbc077d93669f249967980377dfe4b4fad438447773cf1f9a971712a5d7ac125 $V1D/f10_s2027/F10_OOF.npz b7327184b2a44c4ab2846f2d00f2f49fde8f0c330e8740d7a765b9951f307a57 $V1D/data/dlw_targets.npz ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62 $R/work/F10_ENS.npz $R/receipts/ENS_BUILD.json
./ens_detach.sh ens_build_test -- $PY ens_build_test.py PATH,HOME,LC_CTYPE $V1D/f10_s42/F10_OOF.npz bbc077d93669f249967980377dfe4b4fad438447773cf1f9a971712a5d7ac125 $V1D/f10_s2027/F10_OOF.npz b7327184b2a44c4ab2846f2d00f2f49fde8f0c330e8740d7a765b9951f307a57 $V1D/data/dlw_targets.npz ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62 $CT d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544 $U 3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f $R/work/test_scratch $R/receipts/ENS_BUILD_TEST.json
./ens_detach.sh ens_combo_posctl_s42 -- $PY ens_combo.py PATH,HOME,LC_CTYPE --f10 s42 --out $R/work/combo_s42_posctl
./ens_detach.sh ens_combo_compare_posctl -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ens_combo_compare.py PATH,HOME,LC_CTYPE /workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/combo_s42 4dec6b38b08f8cc857c8f58659e846fea686c02c2959c622ea248c7ef5b22afa cae52acf3bc2e82dbbe1cca351c1f3d40d21c91ba48c132241e797990de0f747 $R/work/combo_s42_posctl $R/receipts/ENS_POSCTL_COMPARE_s42.json
bash ens_detach.sh ens_combo_ENS_try2 -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ens_combo.py PATH,HOME,LC_CTYPE --f10 ens --ens-npz $D/work/F10_ENS.npz --ens-receipt $D/receipts/ENS_BUILD.json --out $D/work/combo_ENS
bash ens_detach.sh ens_chain -- sh ens_chain.sh
bash ens_detach.sh launch_f10ens_new_ens -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $D/RUN_CONFIG_F10ENS_NEW_ENS_2026-09-23.json --resume f10ens_new_ens
bash ens_detach.sh ens_stats -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ens_stats.py PATH,HOME,LC_CTYPE $D/receipts/ENS_STATS.json
python3 ens_render.py receipts/ENS_STATS.json <out.md>        # 本机,渲染上面的表
```

(`ens_build` / `ens_build_test` / 正控 / 比较器那几行的 `ens_detach.sh` 当时是 `/workspace` 版本,R=/workspace/f10_ens_2026-09-23;D2 之后改为 /dev/shm 根并以 `bash` 调用,因为 /dev/shm 挂载为 noexec。)
