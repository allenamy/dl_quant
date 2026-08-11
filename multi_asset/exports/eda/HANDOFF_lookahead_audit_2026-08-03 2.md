> **创建:** 2026-08-03 12:48 UTC | **Session:** 0C (上下文接近上限, 主动交接) | **状态:** final — 接手清单 | **性质:** 全部为只读诊断; 未改动任何生产代码/面板/配置, 未 commit | **作废条件:** `build_wide_dl.py:124` 或 `signal/panel_build.py:187` 被修改 ⇒ 全链结论须重验。

# 接手清单 — 前视审计线 (2026-08-03)

**这条线从"对平一个 IC(+0.111 vs +0.0048)"开始, 追到"部署模型的训练血统"。下面是接手所需的一切。**
**★ 全部 SHA 于交接前逐一重算, 不是从记忆引用。**

---

## (a) 已闭合的结论

| 结论 | 文档 | SHA-256 |
|---|---|---|
| **`Y4` 全历史无偏差** = `log(close[t+4h]/close[t])`, 48,909 锚 2021-01→2026-08, 最大偏差 0.0011 bps(float32 精度) | `RESULT_Y4_vs_market_diagnostic_2026-08-03.md` | `8eef7a57c1a89e8a313cd6dfe9887e445f9eebe361951632f2f9424f3b53acf2` |
| **部署对齐缝 ≈ 1 分钟不是 1 小时** —— 面板行 T 携带 T+1h 的价 × 实盘取锚前 1 小时那行, 两步恰好抵消; IC 缝 +0.0005 | `RESULT_deployment_alignment_seam_2026-08-03.md` | `f74092008d4401bce0df87be6c1fb28140712aa3289f4ea2ac9e29ab7af0ad19` |
| **实盘 IC 对平**: +0.111 与 +0.0048 差的 95% 是 Pearson vs Spearman; **同期 Pearson +0.003**; 与面板基准是「不矛盾」非「一致」(CI 宽 0.172) | `RESULT_live_IC_reconciliation_2026-08-03.md` | `0a66fd18f22889dd9e27d737ac23c7178b7f2fb10a2e40e6b2c8c2483f2ddc9d` |
| **★ `betaadj_ret24` 含 11 小时前视**(`np.convolve(...,"same")` 居中, `out[t]←input[t−12…t+11]`); 通道 IC −0.0697 vs 因果 −0.0342; 三口径冻结模型 king **0.135/0.079/0.041**; 横截面 R²=1.0000(是 ch23/ch12 的恒等式); `fundfix` 面板同病已实测 | `RESULT_channel_cutoff_audit_2026-08-03.md` | `eedab22a5e10f0c30310b3d51868d6c3c37745d81e38703898dc4ef72c9842d5` |
| **★ 污染面判据 + 血统链**: 影子期 41–44% 纸面盈亏来自前视; `king_fold4.pt` ← `wideA_lamorth0_xattn_5yr/fold_4`(逐位), `s2_fold4.pt` ← `wideA_s2_y24_5yr/fold_4`; 部署模型利用度 +0.2518 / +0.2611 | `RESULT_contamination_surface_2026-08-03.md` | `8d3bef7a01de7648cfbecab4f1edb90201f7f014e48933a15940d061fbca01f1` |
| 探针 1: 实盘 beta 路径(总 3.97 bps, 离散项 4.20 bps 9/11 同号) | `RESULT_probe1_book_beta_2026-08-03.md` | `8ea37aa35f874253eb0a0ebca2e2fb560ad74a39fcd22af4b927ba99e2294f28` |
| 探针 2: 翻向 −0.73 bps/锚, p=0.61, **不立项** | `RESULT_probe2_flip_economics_2026-08-03.md` | `563105d3c0b6681cca20b25dd7e478a53918ab1357ac632cb8b8535e9ad3cefd` |
| 探针 1b: 影子期"被支付"**已撤回**(93% 是前视时机成分) | `RESULT_probe1b_dispersion_paid_2026-08-03.md` | `d576eaffb4180becaf9422f243f3e98b65d700012837d09536be02cbaff4e81e` |
| 追价机会成本预注册(裁定版-A) | `PREREG_chase_opportunity_cost_2026-08-03.md` | `3a0f3d4f8dceae0affb15c9a36c5595c92d08a2113ee302b218a6dafe43fed6d` |
| R1 离线信号预注册(裁定版) | `PREREG_R1_offline_execution_signal_2026-08-03.md` | `aaee55891c859c79f6ee5f9856900e781940a7ff4c71cbcf8d2be96d42f7c2b0` |

---

## (b) 未完成项 + **确切**阻塞点

| # | 未完成项 | **阻塞在哪(具体)** |
|---|---|---|
| **1** | **vol-scaling ΔNet 三口径对照**(20:00Z 时限) | **不缺信息, 缺机时。** 装配口径 team-lead 已给(见下); 前提(fundfix 同病)已确证。**唯一障碍: 全量 9,821 锚 × 3 口径 = 25.6 CPU 小时**(实测每锚 9.4 秒)。**⇒ 必须抽样。每 20 抽 1 = 491 锚 ≈ 1.3 小时。抽样对配对差安全, 但结果【不得与全量算的 +1.81 并列】。** |
| **2** | **SERVE 口径 champion vs 亚军对照**(决定"实盘拿得到的信号上 champion 是否仍胜") | **缺训练时的归一化统计 mu/sd。** `wideA_lamorth0_xattn_5yr/` 与 `wideA_s2_y24_5yr/` 目录里只有 `fold_*_model.pt` + `fold_*_head_scores.npz` + `panel_ref.npz`(含 CL/YR/Yraw/ch_names/day/funding/member/symbols, **无 ts, 无 mu/sd**)。**`checkpoints/norm_stats.npz` 里有部署那一对的 mu/sd, 但用它去跑【别的候选】是口径错。** ⇒ 要么找到各 run 的 norm 统计, 要么放弃跨模型的 SERVE 对照。 |
| 3 | king/s2 训练标签是 `Y4` 还是 `YR4` | 未读。链条: `train/train_v2arch.py` 的 `target_key` ← 服务器上 `exports/train/wide_harness_*.json`。**读一份即得。** 若是 `Y4`(已证干净)⇒ 污染只在输入侧。 |
| 4 | Ridge/GBDT 基线特征集是否含第 32 通道 | 未读。位置: `multi_asset/baselines/` 与 `multi_asset/eda/_clean_feat_ridge.py`。决定它们是 C 类还是 A 类。 |
| 5 | 其余面板同病核实 | `wide_dl_full.npz` / `_12h` / `_39ch` / `_s3_y168` **仍是推定**。`_fundfix` 与 `_live` 已实测同病。用 (c) 的 `fundfix_check.py` 换路径即可。 |
| 6 | king 权重暴露度 / 验收 net-Sharpe 4.61 折减 | 未开始。方法同血统那套(用 head_scores)。 |

**装配口径出处(team-lead 已给, 不要自创):** `exports/eda/REPRO_vol_scaling_lambda1_2026-08-02.md` **§2.1 六步** + **§3 三个陷阱**(顺序不可换 / `Y4` NaN 时 gross 限 finite 而 turn 在全 N 空间是故意的 / 面板是 `wide_dl_full_fundfix.npz` 9,821 锚)。

---

## (c) 服务器脚本与复算命令

**全部只读。** 服务器 python: `/root/miniconda3/envs/hsy_v5push/bin/python`(系统 python3 无 numpy)。

| 脚本(在 jpline `/tmp/`) | 作用 |
|---|---|
| `leakprobe2.py` | 前视幅度: 存盘 vs 重建 same vs 重建 causal 的逐锚 rank-IC |
| `skewprobe.py` | 训练/服务口径偏斜 |
| `corrfix.py` | **池化 vs 逐锚横截面**相关(§8 那处更正的来源) |
| `deployed_leak.py` | 部署模型的前视利用度(用 head_scores) |
| `leakuse.py` | 全候选的前视利用度 |
| `fundfix_check.py` | 面板同病确证(换 `P=` 路径即可查其它面板) |

```
# 血统链复算(逐位, 不需推断)
KSZ=1055835; K=$(shasum -a 256 ~/dl_quant_live/checkpoints/king_fold4.pt|awk '{print $1}')
ssh jpline "cd /mnt/storage/private/work_hsy/quant_research_multi_asset
  find . -name '*.pt' -size ${KSZ}c | while read f; do
    [ \"\$(sha256sum \$f|awk '{print \$1}')\" = \"$K\" ] && echo \"KING = \$f\"; done"

# 关键面板(注意网格必须匹配, 见 (d))
exports/live/wide_dl_live.npz        T=48,913  <-> exports/live/wide_panel_live.npz
exports/wide_dl_full_fundfix.npz     T=48,168  <-> exports/wide_panel_full.npz
exports/wide_dl.npz / wide_panel.npz T=13,176  <-> 早期候选 run 的网格
```

---

## (d) ★★ 不要重复走的弯路(每一条我都走过, 每一条都花了时间)

1. **影子期 `mid_at_anchor_vector` 是合成的**(每个名字都在 100 附近, BTC 记作 99.93), **不是价格**。影子期一切价格必须用 kline。**实盘同名字段是真价格**(与 kline 中位差 0.056%)。**同一个字段名, 仿真树与实盘树是两种东西。**
2. **kline 的开盘价 vs 收盘价差一小时**: 面板/`Y4` 用 **bar 的 close**(= 墙钟 t+1h 的价)。用 open 对齐会得到 corr≈0.74 的"另一条序列", 并让整簿盈亏**翻号**(−$1,158 vs +$1,595)。
3. **兄弟 run 冒充部署件**: 部署的是 `wideA_lamorth0_xattn_**5yr**`, 不是 `wideA_lamorth0_xattn`。**两者只差一个后缀, 且网格不同(48,168 vs 13,176)。网格不匹配表现为"可用锚 0" —— 一个看起来像"没数据"的正常状态, 而不是像"指错了"。** 任何跨 run 比较前先对 `head_scores.shape[0]` 与基础面板行数。
4. **`panel_source.py` 的默认面板不是运行时用的那个**: 默认 `wide_dl_full.npz`(止 2026-06-30), 而 `shadow_pilot_log.py:37` 用环境变量覆盖成 `exports/live/wide_dl_live.npz`。**读默认值推断运行时行为 ⇒ 我差点上报"影子期在重放 6 月数据"这种级别的假警报。核实成本: 一行 grep 调用方。**
5. **池化相关 ≠ 逐锚横截面相关**: 训练/服务偏斜, 池化 corr 0.8416 / 相对差 52.8%, 而逐锚横截面 Pearson 中位 0.9903、Spearman 0.9802、水平相对差中位 45.7%。**两个都对, 回答的是两个问题。凡报相关/比值必须声明聚合维度。**
6. **`np.convolve(x,w,"same")` 的支撑区间要按【卷积矩阵的行】读**: `M[:,i]=convolve(e_i,...)` 后 `M[t]` 的非零列才是 `out[t]` 用到的输入。用"一个脉冲影响哪些输出"读会得到**镜像**(我因此把 11 项未来写成了 12 项)。**实验没错, 解读错了 —— 这类错只会被"换一种读法"发现, 不会被"重跑一遍"发现。**
7. **推理成本按锚数线性外推时不要漏乘倍数**: 160 锚 ≈ 25 分钟 ⇒ 每锚 9.4 秒 ⇒ 9,821 锚 × 3 口径 = **25.6 小时**, 不是 45 分钟。
8. **`alpha/ops.py::decay_linear` 是【正确的】因果形式**(`"full"[:len(A)]` + 降序权重 + 预热裁掉)。**不要因为"同作者同期"就假定它同病 —— 实测它干净。** 通则(team-lead): **错误跟着 API 默认值走, 不跟着作者走。**

---

## (e) 两条已登记但未做的缺陷(会自己恶化, 优先级由 team-lead 定)

1. **`checkpoints/MANIFEST.json` 只记权重/norm 哈希, 无任何字段指向产出它的训练 run。** 哈希链能证明"没被换过", 不能证明"是哪来的"。**本次靠全盘逐位搜索才闭合。**
2. **⇒ jpline 上 `exports/train/wideA_lamorth0_xattn_5yr/` 与 `wideA_s2_y24_5yr/` 两个目录一旦被清理, 部署模型将【永久】失去可追溯来源。** 这条随时间自己恶化。
