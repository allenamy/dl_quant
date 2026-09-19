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

## AMENDMENT 1(2026-09-19, 写于任何对象 B 数字之前; lead 转达的 R5-02 价格恢复结果, 提交 0c0fd45a0; 原文保留, 冲突处以本节为准)

**A1.1 价格源(对象 B 的 E1 / E2 与对象 A 的纸面收益, 一律如此)**
- 钉住恢复后的原始 5m 价格表(pod2 `/workspace/raw_price_fix_2026-09-19/`):
  - `work/price_logtable_raw.npy` sha256 0b134159a61aa77e33b02696f3702c35e7360862b30ed9b356731017fcad0157;
  - `work/price_meta_raw.npz` c27fdb11af42f374bc1aeabd66641637b1c651010de922983473a2002c2c7f55;
  - 补丁 `r_prices_raw_patch.npz` 984c28923838501758fe52d1ea7d0cd92fc7fc26c4869058b112bb43670343b2。
- **不用**流 R 旧价格表(3b588cb0)及其「等份对数收益」修补。
- 价格表覆盖 2022-06-30 00Z → 2026-09-01; 09-01 之后的价格等流 D 收据。
- E1 的 4h 收益改为从恢复表在锚边界取: y4 = exp(lp(A+4h) − lp(A)) − 1。取点规则与行号映射写进收据。
- meta RAW y4(0e3c09ac)**只作逐格对照**, 不作主口径。它把 BNX 缺数段记为 0、5 格(AERGO 2025-04-16 08Z、ESPORTS 2025-07-29 08Z、2Z 2025-10-02 12Z、RECALL 2025-10-15 12Z、UAI 2025-11-06 08Z)记为 NaN。凡用到 meta y4 的地方, 这些格与恢复路径逐格比较并报差。
- **NaN 与 0 一律不得代替「未知」。**

**A1.2 UNAVAILABLE 规则「UA-FREEZE-EXCLUDE」(具名, 对象 B 的 E1 / E2 与对象 A 同用)**
- 定义: 补丁 `gap_unavail_row / gap_unavail_col` 列出的 3,084 根 bar = 交易所无 K 线(停牌 / 重新上市 / 换币)。
- (A) **定价**: 名 s 在 4h 窗 (A, A+4h] 内含任一 UNAVAILABLE bar, 或窗端点价取不到 ⇒ 该 (s, 窗) 为 UNKNOWN 格。
  - 该格的价格损益与资金费**不进主读数分子**, 另记一栏「UNKNOWN」。
  - 主读数的 gross 分母**照常包含**该格的 |w|: 未知不当零收益、也不白白抬高 g。
  - 收据逐格给出名、窗、|w|、按 2.0× NAV 换算的名义额(notional at risk)。
- (B) **交易**: 名 s 在锚 A 的边界价 UNAVAILABLE ⇒ 该锚不能交易 s: 持仓按上锚冻结(目标层把 s 的权重钉在上锚值)。直到首个边界价可得的锚才按当锚目标调整。冻结期内每锚的冻结名义额逐锚报告。
- (C) **计数**(每个读数、每个窗): 受影响锚数、(s, 窗) 格数、|w| 之和、名义额、UNKNOWN 栏的「可比较但未计入」上下界(无界时写 UNBOUNDED, 不编数)。
- E2 若执行器模拟 v3 自身已有对 UNAVAILABLE 的规则且与本规则不同, 以本规则为对象 B 的主读、模拟器规则为敏感性, 两者都报。
- 本修订不改对象 B 目标链(特征 / 成员来自生产等价的 5m 通道缓存, 与生产者自己抓的裁剪通道同口径); 只改收益记账层。

## AMENDMENT 2(2026-09-19 10:1xZ; 写于门 F 在 12 个锚中**只跑了 1 个锚**(1789660800)之后、其余 11 锚之前; 原文保留, 冲突处以本节为准)

**先披露已看到的读数(1 / 12 锚, 1789660800 = 09-17 16Z):**
- F-1、F-2、正控的权重逐名逐位相等(max|Δw| = 0.0), `weights_sha` 相等, n_f10_scored 相等。
- F-2 的 king `weights/<A>.npz`、prev_rec(members / legz / sm / sm_idx / sel_idx / carry / cost)、LR 尾部逐位相等。
- NC1、NC2 都变红。
- 我写的比较器是「所有键全等」, 因两个字段把该锚判成 FAIL:
  - (i) 注入路径下 target_live 的 `f10_sha` = 恒等模型文件的 sha(80c7c75a…)。这是注入构造本身的结果; 打分器实际用的模型 sha = 351ae26b(已记录)。正控(真管线 + 在役模型)的 f10_sha 与归档相等。
  - (ii) 重跑生产者写出的 king 文件 `gross_norm` 与归档差 1 ulp(0.8188702296482515 vs 0.8188702296482516)。原因已实测: 生产 Mac 的 CPython 3.14 内建 `sum()` 对浮点用 Neumaier 补偿求和(3.12 起), pod2 为 CPython 3.11(逐项相加)。同一组 |w|(按生产者插入顺序 = 面板索引升序)用两种求和恰好得到这两个值。king 文件本不在 F-2 的预注册判据里, 是我多加的比较。

**A2.1 门 F 判据的澄清(权重一律仍须逐位, 不放宽):**
- **F-1 / F-2 的 target_live 必须同时满足**:
  - (a) 名集相同, 每名权重逐位相等;
  - (b) `weights_sha` 相等(float32 权重 npz 的字节);
  - (c) `schema / anchor_ts / n_names / universe / universe_sha / n_universe / booster_sha / producer` 相等;
  - (d) n_f10_scored 与归档 target_combo 相等;
  - (e) 打分器实际使用的模型 sha == 351ae26b;
  - (f) `f10_sha`: 正控必须等于归档; 注入路径按构造为恒等模型 sha, 只记录不比较(16Z 之前写出的归档缺该键, 按原文放行);
  - (g) `gross_norm`: 相等; 否则**只有**当「回放值 == 同一组 |w| 按插入顺序的逐项和」且「归档值 == 其 Neumaier 和」**两者都成立**时, 判为解释器求和差(D13)并通过; 任一不成立 ⇒ FAIL。
- **F-2 追加**(本次新增, 只加严): 重跑生产者写出的 king 文件, 在 weights / n_names / universe / universe_sha / booster_sha / weights_sha 上与归档 king 备份相等, `gross_norm` 按 (g) 判。
- 每锚同时报告「字面全键相等」列(原比较器的读法), 不删除。
- 其余(正控、NC1、NC2、锚集合、停止条款)不变。

## AMENDMENT 3(2026-09-19; **写于第一次门 F 运行之后**, 已知哪 5 个锚的 NC1 未变红; 写于任何门 F 重跑与任何对象 B 历史之前; 原文与第一次判词原样保留)

**A3.0 lead 裁定原文(照录, 用户委托「修复不用等我裁定 / 按最佳建议」):**

> 1. **Parity gate negative control.** AMENDMENT 3 is approved, with one strengthening. It must be committed BEFORE re-running the 12 anchors.
>    - **NC1′:** swap the F10 scores of the top- and bottom-scored members among members that are inside `sel` and not FTRIM-zeroed at that anchor.
>    - **Add NC1r:** at each anchor, 3 swaps between pairs of eligible members (inside `sel`, not FTRIM-zeroed) drawn with `numpy.random.default_rng([20260919, anchor_epoch])`.
>    - **Pass rule:** every NC1′ and NC1r variant must change the target on every anchor (12/12 and 36/36). NC2 stays as is. The exact-parity criterion (max|Δw| = 0, weights_sha equal) is unchanged.
>    - **Disclosure:** The original NC1 verdict (FAIL, 5/12 unchanged; explanation holds on 12/12) stays in the receipts verbatim, and the gate history shows both verdicts. State that the amendment was written after seeing which anchors failed. State that the amendment makes the control stricter and does not touch the parity criterion.
> 2. **Live-equivalent cache.** Adopt **R0**: the holefix2 cache as-is, i.e. what production actually fetched. It is proven cell-for-cell equal to production on the overlap window. The LE-A′ keep-gate FAIL stays recorded. Delisted and dead contracts are handled only through the membership and tradability masks production itself uses. Report the dead-name exposure (the % of gross in names after their last trade, per year) as a named limitation in the object-B results. Do not blank cache cells.
> 3. **Data version.** Use the stream-D corrected variant `x0918r` (official 08-31 archives) if its difference proof passes. That agent is building it now; its addendum lands in `docs/RESULT_data_axis_0919_2026-09-19.md`. Otherwise use x0918 with the 08-31 hole-fill named as a limitation. Pin the choice in your run config before running. The price table for 08-31 → 09-18 will be extended by the raw-price agent after x0918r exists; object A's paper return waits for that.
> 4. **Order after the gate passes:** object-B A0 targets over the full history; then the v4 refit arm (the baseline-tables prereg needs it); then report. A separate baseline-runner agent (folder `multi_asset/exports/research/baseline_tables_2026-09-19/`) will consume your targets once your gate receipt says PASS. Don't run tables yourself.
> 5. **The S2 f10_v4RAW_s42 overwrite:** noted. Lead is investigating it; don't touch those files.

**A3.1 披露**:
- 本修订写于第一次门 F 运行之后。那时已知 NC1 在 5/12 锚(09-17 20Z、09-18 08Z、09-18 12Z、09-19 00Z、09-19 04Z)未改变目标, 且「被换两名的 F10 分被生产逻辑整体丢弃」这一解释在 12/12 锚上成立。
- 第一次运行的判词(FAIL)与逐锚收据原样保留, 另存为 `receipts/gate_f/run1_NC1orig/`; 门的历史两次判词并列。
- 本修订**只把负控改严**(对照必须在「F10 分确实进入书」的成员上起作用), **不触及平价判据**: max|Δw| = 0、weights_sha 相等、AMENDMENT 2 A2.1 其余各款一字不变。

**A3.2 负控(替换 §3 S5 的 NC1, 原 NC1 照跑照报但不进判词)**:
- **合格成员(每锚)** = 生产者成员 pm 中同时满足三条的名:
  - 在 combo 的 `sel` 内: 按 combo_stage L38–42 在该锚缓存上重算, qv4h ≥ params.qv4h_min;
  - 不在基线注入运行(未交换)的 `target_combo.ftrim.names_fc` 中;
  - F10 分有限。
- **NC1′**: 交换合格成员中 F10 分最高与最低的两名。
- **NC1r**: `rng = numpy.random.default_rng([20260919, A])`, 依次抽 3 对 `rng.choice(合格成员, 2, replace=False)`, 每对单独交换、单独运行。
- **判定**: 每锚 NC1′ 与 3 个 NC1r 都必须改变目标(判别 = 平价比较器判不等)。须 12/12 与 36/36; NC2 不变; 其余不变。

**A3.3 缓存与基名单(R0)**:
- 历史链的 5m 缓存 = holefix2 原样(不施加 §1 / §3 S4 的实时等价规则)。LE-A′ FAIL 保留在案(`receipts/LIVE_EQUIV.json`)。
- 死合约只经生产者自己的成员规则与宇宙掩码处理。死名暴露(各年目标 gross 落在「末成交之后」名上的比例)作具名局限报告。
- **基名单**: §1 的「已上市且未死」判据用的正是被 LE-A′ 否决的末成交规则, 故一并撤回。基名单改回 S2 D3 的代理(`P2/work/universe.npz` 的 trading24 = (A−24h, A] 有结算)∩ 非 非COIN, 再 ∪ symbols_live(A), 锚前预置。
  - 依据: 仍在列、只是无成交的合约(如 SCRT / STORJ)照常结算资金费, 这与生产者 exchangeInfo 名单一致。
  - 已知局限: 真正下市后仍有资金费记录的名会留在基名单里(AUDIT_DATA TRD-01 / TRD-02)。

**A3.4 数据版本**:
- 若流 D 的 x0918r 差分证明通过, 用 x0918r; 否则用 x0918 并把 08-31 补洞列为局限。选择与 sha 钉在 RUN_CONFIG 里, 先于运行。
- 锚 ≤ 2026-08-31 00Z 的 40 日尾窗不含 08-31 的 bar, 所以这段在 holefix2 / x0918 / x0918r 上逐位相同(流 D 前缀证明: 对 holefix2 差 0)。
- 延长段(2026-08-31 04Z → 09-18 20Z)还需要延长的宇宙、资金费与可交易输入; 缺哪一项就在 RUN_CONFIG 里具名, 不自建。

## AMENDMENT 4(2026-09-19; 写于门 F 第二次 FAIL 之后、第三次运行之前; 原文、第一次与第二次判词及收据原样保留)

**A4.0 lead 裁定原文(`docs/RULINGS_best_recommendation_2026-09-19.md` 末节, e3e7a8fc3, 照录要点):**「负对照的目的: 证明『错误的 F10 输入会被门发现』。小于中性带的扰动在生产里同样不改变书, 回放与生产在书上一致, 这时『判对』是正确的, 不是门失灵。所以把检验分成两层: 1. **管道敏感性**: NC1r 的判据改为『中性带之前的 DL 腿(fc)状态必须改变』(每次随机互换都要变; 全部 36 次)。 2. **书层敏感性**: 由已通过的 NC1′(sel 内最高 / 最低互换, 12/12 改变最终目标)与 NC2(换 king 模型, 11/11)承担。 3. **主判据同时收紧**: 除最终目标逐位相同外, 中性带之前的 fc 状态也必须与存档生产状态逐位相同(若存档里有)。……09-01 → 09-18 的宇宙: ……用生产当时实际使用的九月宇宙(实盘目标文件记录的 universe_sha 对应的那一份)……若该宇宙文件无法按 sha 取回, 这一段对象 B 不出数并具名。」 lead 另嘱: 本次通过则依序出 A0 全史 → v4 重训臂 → 报告; **本次失败则停止并上报, 不再修订**。

**A4.1 披露(原话照录):** "third run of the same gate after control revisions; the parity criterion was never changed; revisions were written after seeing the failures"。
- 精确说明: 权重层平价判据(逐名逐位、max|Δw| = 0、weights_sha 相等)三次运行从未改变。
- AMENDMENT 2 在第一次运行的第 1 锚之后澄清了两个元数据键(注入路径的 f10_sha、1 ulp 的 gross_norm), 已在该修订内披露。

**A4.2 「中性带之前的 fc 状态」的定义与观测:**
- 定义 = combo_stage 3520d363 中 fc 那次 `chain()` 调用里的 `smv = H + P["alpha"] * (tgt - H)`, 取在 `smv = np.where(np.abs(trade) < P["band"], H, smv)` 之前(L90–92)。fc 调用是文件中第 4 次 `chain()` 调用: ① 自平价 king、② 侧车 f10、③ kc、④ fc。
- 观测用插桩副本 `combo_stage_replay_3520d363_preband.py`, 在回放装置上只加 4 处断言过的插入:
  - 模块级列表;
  - chain 入口占位;
  - smv 行之后记录副本;
  - 状态落盘之后按环境变量 `PREBAND_OUT` 写出 4 个向量。
  - 不改任何计算。
- **中立性检查**(必须通过, 否则判 FAIL): 插桩副本的基线注入运行, 其 target_live 与三个状态文件 == 同锚非插桩 F-1 运行的输出(逐位)。

**A4.3 判据(第三次运行):**
- **主判据** = AMENDMENT 2 A2.1 的全部条款(不变)**加**:
  - F-1 与 F-2 回放写出的 `state_H_fc_<A>.npz`(idx 与 val)与存档生产的同名文件逐位相等, 凡存档里有就查。
- **存档里有什么, 写明**: 生产只存「中性带之后、|v| > 1e-9 的 fc 状态」; **从不存中性带之前的状态** ⇒ 「中性带之前的 fc 状态 vs 存档」在 12 个锚上全部**无存档可比**, 逐锚具名, 不作通过证据。存档可比的是带后 fc 状态, 按上款在每个有存档的锚上必须逐位相等。
- **只报(不进判词)**:
  - kc 与 f10 两个状态文件对存档;
  - 注入路径的带前 fc 状态 vs 插桩真管线(在役模型、need = True)的带前 fc 状态, 逐位。
- **NC1r** = 抽取规则与 rng 不变(`default_rng([20260919, A])`, 3 对)。每次互换后带前 fc 状态 ≠ 插桩基线的带前 fc 状态 ⇒ 变红; 须 36/36。
- **NC1′**(最终目标, 12/12)与 **NC2**(king 权重, 11/11)在本次运行中原样重跑, 判据不变。
- 原 NC1 照报, 不进判词。
- 门的历史三次并列; 第一次、第二次收据原样保留。

**A4.4 09-01 → 09-18 段的宇宙:**
- 以存档 target_live 记录的 `universe_sha` 在 `~/wide_shadow` 只读查找与之 sha 相符的宇宙文件; 取回则按 sha 钉住使用。
- 取不回 ⇒ 该段对象 B 标 UNAVAILABLE 并具名。
- 该段数据版本按 x0918r(差分证明落地后), 估值等原始价格代理的延长收据。
