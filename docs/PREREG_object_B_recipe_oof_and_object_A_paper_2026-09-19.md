> **创建:** 2026-09-19 | **Session:** https://claude.ai/code/session_01KW6frfphbFmFzx7wUtGhLb(R5-05 实施子代理) | **状态:** 预注册 —— 写于任何对象 B 数字、任何复现门与平价门读数之前; 装置在本文提交之后才写入与运行 | **作废条件:** 用户撤回 `docs/RULINGS_best_recommendation_2026-09-19.md` 末节 6 项裁定之任一; 生产者 e9c98374 或 combo_stage 3520d363 换代; 本文列出的任一输入 sha 被撤回; 以 AMENDMENT 修订的条目以修订为准(原字节保留)

# 预注册: 对象 B(配方匹配折外历史)与对象 A(生产重叠期)目标层纸面收益

**上游:** 设计 `docs/DESIGN_certified_production_path_2026-09-19.md`(6da9cb466); 裁定 `docs/RULINGS_best_recommendation_2026-09-19.md` 末节(b2b90bebb); 复审 R5-05(第五轮)与 R5B-09(`REVIEW_round5b_codex_2026-09-19.md` L128–140)。
**装置根:** 本地 `multi_asset/exports/research/object_b_2026-09-19/`; pod2 `/workspace/object_b_2026-09-19/`(只写此根与 `/dev/shm/object_b_*`)。

## §0 比较类型(R5B-09; 每份收据都必须写明属于哪一类)

| 类型 | 含义 | 本文里的实例 |
|---|---|---|
| **(1) 历史配方比较** | 各腿都用自己的因果折外预测; 每个被评估的标签都晚于产生该预测的折的训练 / 选模边界 | **对象 B 全部读数** |
| (2) 两个具体 bundle 的未来比较 | 每个被评估标签都晚于两个 bundle 各自的训练 / 选模可见边界 | 本文**不做** |
| **(3) 最新 refit 的打包 / 预测平价** | 部署工艺检查, **不是**任何收益 | **门 F(平价门)、K-REPRO、F-REPRO、B-REPRO** |
| (A-lit) 生产字面记录 | 实盘真实交易的目标文件, 不是比较 | **对象 A 纸面收益** |

- 在役 F10(351ae26b, 训练标签止于 2026-08-30 24:00Z 前)与在役 king(8d79186b, 标签年 < 2026)**只**在门 F 与对象 A 中出现, **永不**给对象 B 的任何历史锚打分(那是样本内)。
- **配方选择的可见边界(写明, 不修)**: 对象 B 固定的是 2026-08 选定的配方(φ = 0.45、去 rev24、FTRIM −10 bp、band 2.5e-4、msharpe 900、cap 2.5 等)。这些超参是用截至 2026-08 的全史选出来的, 所以对象 B 是「这套配方放到历史上」的**条件读数**, 不是前向检验。唯一前向证据是对象 A。

## §1 对象 B 的定义(按 6 项裁定)

- **代码(逐字节, 只换输入):**
  - 生产者 `shadow_loop_v3.py` e9c98374 → 回放装置 `shadow_loop_v3_replay.py` 4d3bc157(2 处替换: 取数改为读缓存、TAIL_SCORE 关)。
  - combo_stage 3520d363 → 由 `mk_combo_replay_device.py` 同法生成的回放装置(3 处替换: WS 取自环境、页报抑制、缓存截到 A)。其 sha 在生成收据里, 运行前断言。
- **king(裁定 2 = v3):**
  - 折 Y ∈ {2023, 2024, 2025, 2026}, 按 `pod_export_bundle_v3.py`(c210bac6)L26–60 的配方在 `wide_fea_v2ext.npy` f88b0720 / `_meta.npz` 4b1b6047 上拟合「锚年份 < Y」。
  - 2023、2024、2025 三折重训并存盘; **折 2026 = 在役 `slow2026.txt` 8d79186b 本身**(它按构造就是 year < 2026 的那一折)。
  - 服务规则: 锚 E 用满足 `label_end(Y) < E − 30 天` 的最新折。label_end(Y) = 该轴上 Y−1 年最后一个「成员中有限标签 ≥ 50」的锚 + 4h。
  - 打分在**生产者自己的服务特征 X 上**进行(生产者 e9c98374 L421–422 `X = FE_ANCH[:, keep]; pred = booster.predict(X)`), 覆盖全部生产成员。
- **F10(裁定 1 = 在役配方, 仅 s42):**
  - 在役训练器 `pod_f10_refit_ext.py` ea3675b8, 在其原输入上运行: `dlw_ext/data/dlw_targets.npz` 31d043e8、`dlw_fea82.npz` 9bc111a4、`f8_ext/data/f8_fea89.npz` bebf2720、`f10v2_legs.npz` facf53f7(mtime 均早于 09-01 在役 refit)。
  - 逐年折 Y ∈ {2023, 2024, 2025, 2026}: 只保留标签止点(E + 4h)< Y-01-01 00Z 的锚。
  - 派生训练器只有两处文本改动, 且都有断言: (i) 截断块, 由环境变量 `F10_CUTOFF` 控制, 不设则为空操作; (ii) 存盘路径取自环境变量 `F10_SAVE`, 永不写 `f8_ext/models`。
  - 每折按 `pod_f10_np_export.py`(3e304c27)同式导出 np 权重, 并过 V1(np ≡ torch)。
  - 服务规则: 锚 E 用满足 `label_end < E 所在月首` 的最新折(= G2-D 的 F10 规则)。
  - 打分走 combo_stage **真 171 管线**(L111–176 原文), 覆盖全部生产成员; 历史上按 §3 S6 的「预计算 → 注入」执行。
- **成员(裁定 3)**: 生产者成员规则原样(生产者 e9c98374 L365–380: 7 日有限 ret5 占比 ≥ 0.95、v7 ≥ 1e-4、top-400、< 50 跳锚)。训练集沿用在役构建(判活门之前)。
- **宇宙**: PIT = umask_UPIT_CRYPTO, 经 `P2/work/universe.npz` 6322b573(同 S2)。
- **回放缓存 = 实时抓取等价(§3 S4)**: holefix2 1d7f459d。凡场所当时不存在该合约的格一律置 NaN, 依据 tradability_v1 54d409d0 的首 / 末成交时刻。再按当锚 symbols_live 把宇宙外名置 NaN(同 S2 I3)。
- **基名单(§3 S4)**: 当锚「已上市且未死」的加密名(非 COIN 的名排除, 与生产 exchangeInfo 的 `contractType == PERPETUAL` 过滤同向)∪ 当锚 symbols_live。锚前预置 `st.base`(同 S2 D3 的做法)。
- **资金费**: `P2/work/ledger_full.npz` bea6f575(同 S2)。
- **冷启动**: 2022-01-31 00Z, H = 0, LR = [](同 S2)。
- **COMBO_LIVE 两读(裁定 4)**:
  - **B-scaled(主读)**: L333 / L335 / L381 三个计数下限按当锚成员数 n 等比缩放 = ⌈380·n/400⌉、⌈150·n/400⌉、⌈150·n/400⌉。L334 gross ∈ [0.4, 1.2]、`gross_in > 0.4`、宇宙外权重 = 0 不变。
  - **B-lit(同报)**: 常数原样(即回放装置自己跑出的判定)。
  - 敏感性: 只缩放 L333(只报)。
  - 两读都只是在同一条链的状态上**选择交易哪个文件**: 通过 ⇒ combo 目标; 失败或已知崩溃 ⇒ 该锚 king 文件; 生产者跳锚 ⇒ 持有。
- **不改生产代码(裁定 6)。**

## §2 缺成员 / 缺预测 / 停机规则(写死)

| 情形 | 规则 |
|---|---|
| 无合规 king 折(2022 全年; 2023-01-01 → 2023-01-31 00Z) | king 分全 NaN ⇒ king 腿中性(生产 `xz` → NaN → nan_to_num 0), 逐锚记录 |
| 有折时的单名 king 分 | LightGBM 对每行都给分, 不会缺; 若出现 NaN 仍中性并计数 |
| 无合规 F10 折(2022 全年) | f10 全 NaN ⇒ fc = 纯 fund; 飞前断言 okf = 0 ⇒ 两读均交易 king 文件 |
| 单名缺 F10 分(管线无该行) | NaN ⇒ fc 腿中性; 计入 okf 缺口, 逐锚计数; **不补值** |
| 生产者跳锚(coverage < 0.80 / 成员 < 50 / sel < 80) | 无新目标 ⇒ 持有(执行器 on_unavailable = hold) |
| combo 已知崩溃(`chain()` 返回 None → TypeError) | 字面语义: 交易 king 文件(不取 S2 CMB 的「持有」) |
| 死合约 | 由实时等价缓存让成员规则自然剔除; 残留目标毛额逐年报(不强删) |
| 执行层停机 / 日止损 / 逐名止损 | 目标层不建模, 归执行器模拟 v3 |

## §3 步骤(每步: 命令 · 输入 / 输出 sha · 训练标签末 / 评估起止 · 正负控)

所有 pod2 命令形如 `env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 [变量…] nice -n 10 /workspace/venv/bin/python -B <装置> [参数]`, 在 `/workspace/object_b_2026-09-19/devices` 下执行。逐字复跑行写进各收据。内存峰值 < 20 GB(先读 `free -g` 与 cgroup `memory.current`)。只按自己记录的 PID / PGID 停进程。

**S1 · king v3 折(CPU)** —— 装置 `king_v3_folds.py`
- 输入: `wide_fea_v2ext.npy` f88b0720、`_meta.npz` 4b1b6047、`live_pins.json` fd27fe48(keep_names)、导出器源 c210bac6(逐行断言所抄代码段)、`shadow_bundle_v3/slow_pred_pinned.npy` 158cd4ac、`slow2026.txt` 8d79186b。
- 输出: `models/king_v3_fold{2023,2024,2025}.txt`、`receipts/K_REPRO.json`。
- 训练标签末: 每折写入收据。评估 = 各折自身测试年。
- **K-REPRO**(类型 3): 重训的 fold 2024、2025 在其测试格上的 float32 预测 == pinned 对应行(逐位); 重训的 fold 2026 模型文本 sha == 8d79186b, 且其预测 == pinned 2026 行。
  - 全等 ⇒ PASS;
  - 否则 max|Δ| ≤ 1e-6 且逐锚秩全同 ⇒ REPRO_NUMERIC;
  - 否则 ⇒ NEW_DRAW。
  - 三种结果下 2023–2025 折都可用, 但必须带标签写进对象 B 的每份收据; fold 2023 无参照, 继承本门结论。
- 负控: 比较器作用于(pinned 2024 行, 重训 fold 2025 模型在 2024 行上的预测)必须判不等。

**S2 · F10 在役配方逐年折(GPU)** —— 装置 `f10_refit_fold.py`(派生)+ `f10_np_export_fold.py`
- 启动前 `nvidia-smi` 显存 < 500 MiB 且利用率 0%; 记录 PGID; 他人开始使用即不再启动新折。
- 输出: `models/f10_ins_fold{Y}_s42.pt` / `_np.npz`、`receipts/F_REPRO.json`、`receipts/F10_FOLDS.json`。
- **F-REPRO**(类型 3): 不设 `F10_CUTOFF` 跑一次, 与在役 `f10_live_s42.pt` c983b3e3 的 state_dict / mu / sd 比较。
  - 逐位 ⇒ PASS;
  - 否则在导出器 V1 同一 30,000 行样本上: Spearman ≥ 0.99999 且 max|Δ| ≤ 1e-5 ⇒ REPRO_NUMERIC;
  - 否则 ⇒ NEW_DRAW(同样带标签可用)。
  - 负控: 同一比较器作用于(f10_live_s42.pt, f10_live_s2027.pt)必须判不等。
- 训练标签末 = Y-01-01 00Z(严格小于)。

**S3 · 月折 mu/sd 重建(CPU; 不进对象 B, 附带交付)** —— 装置 `f10_monthly_musd.py`
- 按训练器 2147a7dd 的 mu/sd 规则(先读码, 无随机数才做), 为 mE1cX7 RAW s42 的 20 折重建 mu/sd。
- **B-REPRO**: 用存盘 state_dict 与重建的 mu/sd, 在原测试 pair 上推理, 必须 == `f10_v4RAW_s42.npy` 58d64a6f(max|Δ| ≤ 1e-6, 全部测试格)。
- 不过 ⇒ 该路径报 **UNAVAILABLE**; **不得**用新数据上重算的 mu/sd 代替。

**S4 · 实时等价缓存与基名单(CPU)** —— 装置 `live_equiv.py`
- 输出: 掩码规格 `receipts/LIVE_EQUIV.json`(逐名存活区间、改动格数、按年)。不写多 GB 缓存副本, 掩码在内存里施加。
- 规则:
  - dead(s) ⇔ `last_traded_ts[s] < data_end − 3 天`。
  - 格 (t, s) 置 NaN ⇔ `t < first_traded_ts[s]`, 或 `dead(s) 且 t > last_traded_ts[s]`。
  - 基名单(A) = {s: 非 COIN 否, 且 first_traded_ts ≤ A, 且 ¬(dead ∧ A > last_traded_ts)} ∪ symbols_live(A)。
  - 非 COIN(s) ⇔ 存在 t 使 UPIT[t, s] ∧ ¬UPIT_CRYPTO[t, s]; 从未进 UPIT 的名按「未知 → 保留」(与 crypto_mask_note 同约定)。
- **保持门 LE-A′**: 在 08-03 08:05Z → 09-01 00:00Z 重叠窗、live450 名上, 施加掩码后的缓存与生产者快照 `P2/work/snapshots/1789200000/rolling.npz` 的 NaN 支持差必须仍 = 0(holefix2 在 G2-A′ 下为 0)。不为 0 ⇒ 列出格与名, 规则判为偏离生产, **停**。
- 负控: 把某个 live 名在窗内人为判「已死」, 门必须变红。

**S5 · 平价门 F(类型 3, 无收益)** —— 装置 `gate_f.py`
- 在役模型(king 8d79186b、F10 351ae26b)。归档: 对象 A tar sha **33910c01**; combosnap 快照 `~/wide_shadow/state/snap/<A>/`(拷到 pod2, 逐文件 sha 入收据); `weights/<A−4h>.npz`、`fea171/state_H_{f10,kc,fc}_<A−4h>.npz` 的只读副本。
- 被测锚: 快照完整且 king 备份存在的全部锚(截至本文 12 个: 1789646400 … 1789804800)。
- **F-1(combo 段)**: 快照 A 的输入 + 本路径的 F10 打分器(combo_stage L1–176 原文前缀)打出分数 + 注入 ⇒ 回放 target_live。要求:
  - 与归档 target_live **逐名逐位相等**(max|Δw| = 0.0, 名集相同, n_names / gross_norm / universe_sha / weights_sha 相等; f10_sha 缺失仅在 16Z 之前写出的归档上按版本差放行);
  - n_f10_scored 与生产 `target_combo` 相等。
- **F-2(端到端)**: 由快照 A−4h 的状态重跑生产者到 A(FoldBooster 在役模式), 再走 F-1 ⇒ king `weights/<A>.npz` 逐位 = 归档, prev_rec(members / legz / sm)逐位 = 快照 A, target_live 逐位 = 归档。被测锚 = 同时有 A−4h 快照的锚。
- **正控**: 同一回放装置走真管线(`need = True`, 在役模型)⇒ 与归档逐位相等。
- **负控**(每锚都要变红): (i) 交换两个秩不同成员的 F10 分; (ii) king 用 fold 2025 代替在役。
- **判定**: 全部被测锚 F-1、F-2 通过, 且正负控表现如上 ⇒ PASS; 其余 ⇒ FAIL ⇒ **停止, 不跑任何历史, 上报**。
- 另报: 对象 A 144 锚中无快照(不可测)的锚数; pod2 与 Mac 两机 F10 分数的逐名差(D13 测量, 不作门)。

**S6 · 对象 B 链(CPU, 只在 S5 PASS 之后)** —— 装置 `b_driver.py` / `b_scorer.py` / `b_launch.py`
- 三趟:
  - **P1** 生产者单链(不跑 combo), 逐锚记录打分所需输入: 成员名单、ema acc、各名末行费率、prev_rec。
  - **P2** 按锚并行跑 F10 打分器(父进程载入缓存后 fork; 每锚在 `/dev/shm` 的独立沙箱里, 先清空 mini, 保证 need = True)。
  - **P3** 生产者 + combo 串行全链, 注入 P2 分数(秩 / 128 + 恒等模型, G2-C′ 已证逐位)。
- P1 与 P3 的生产者链必须逐锚全同(king H、成员、w3), 否则停。
- 输出: `RUN_B.json`(逐锚记录, 含成员名单 idx)+ `RUN_B.vec.npz`(king / kc / fc / F10 分)+ 两读目标 `TARGETS_B_{scaled,lit}.vec.npz` + 清单。
- 锚轴: 2022-01-31 00Z → 2026-08-31 00Z(= S2 轴, 10,039 锚)。延长到 2026-09-18 20Z 须等流 D 收据, 另行标注。
- **审计 G2-D′**(阻断): 由折表独立重推每锚应送入的 king / F10 折, 与记录逐锚一致, 且「送入却不合规」= 0。红能力: 伪造折表(label_end 移入评估期)⇒ 审计必须变红。
- **覆盖**: 每锚记录 okf 与 |pm|。king 与 F10 已送入时, 缺分名单逐锚列出。

**S7 · 对象 A 纸面收益(A-lit)** —— 装置 `a_paper.py`
- 目标: tar 33910c01 中执行器实际交易的文件(TRADE 锚)。HOLD / 缺文件 / 无执行行 ⇒ 沿用上锚。
- 价格: 流 D 的 RAW 5m 延长(`/workspace/axis_0919/`)**收据落地之后**才读, 不自建。RAW y4 = Π(1 + r5) − 1 over (A, A+4h]。
- 记账同 S2 A6.4(pnl / carry / cost, costb_PWR_G230k, NOSTOP 去均值重标)。资金费用流 D 账本。
- 逐锚标出在役 king / F10 版本及其训练末: 全部标签都在其后, 即全前向。
- 只报描述量(总额、逐日、2.0× 复利 NAV), 24 天不下 CI 判词。

## §4 对象 B 评估(窗口、统计、K; 只在目标产出且执行器 v3 与原始价格补丁的收据都存在之后运行)

- **层**:
  - **E2(主)** = 执行器模拟 v3(原样, 按其自身收据)× 原始 5m 价格补丁;
  - **E1(副、诊断)** = 目标层 S2 A6.4 记账 × meta RAW y4 0e3c09ac。
- **窗口**:
  - **B_CORE** = [首个「席位窗 900 条 king 收益全部来自 king 已送入的锚」的锚, 2026-08-30 20Z]。起点由链记录按此规则算出, 不按日期。
  - **PRE** = [2022-06-30 00Z, B_CORE 起点), 标签 **「PARTIAL_RECIPE —— 席位暖机 / 模型腿缺席, 不是生产策略」**。
  - 两窗内按 UTC 自然年分格。
  - **EXT** = [2026-08-31 00Z, 2026-09-18 20Z](仅在流 D 收据后, 标「与对象 A 重叠」)。
- **统计**:
  - g = bps / 锚 / 单位 gross; 2.0× 固定杠杆复利 NAV; 日 Sharpe; maxDD(E1 按 UTC 日; E2 按模拟器口径)。
  - CI = UTC 日块自举 2000 次, `default_rng([20260905, k])`, k = 0 主读、k = 9 复核。
  - † = CI95 不含 0。†† = Bonferroni K = 16 不含 0(8 格: B_CORE、PRE、2022–2026 五年、EXT × 2 读)。
  - G0 的 21 个 regime 格另成一族, 只描述。
- **不下 (A) / (B) / (C) 判词**(本文没有预注册任何对照)。与 A0 / S2 / 流 R 的任何并列都只描述, 且必须写明比较类型。
- **两读不同向时**如实写出, 主读仍是 B-scaled。

## §5 不主张

- 不主张对象 B 是在役 booster 或在役 F10 本身的历史表现(折外抽样, 且是逐年而非月度节奏)。
- 不主张 PIT = pins; 不主张下市结算已建模。
- 不做任何实盘改动。
- 门 F 只认证「本路径在有归档输入的锚上等于生产」, 不认证无快照的 132 个对象 A 锚。
