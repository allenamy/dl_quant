# 独立复审请求 · FP3 全链收口第一批(2026-09-17 15:30Z → 17:50Z)

> **创建:** 2026-09-17 17:5xZ | **Session:** b9646a9e(主研究员) | **状态:** 待独立研究员复审 | **作废条件:** 复审推翻任一收据
> **范围:** 复审五轮后的 FP3 纲领(`PROGRAM_FP3_full_chain_closure_2026-09-17.md`)项 J、E、K、C、D、F、G、L(v1)、I(计划)、B(FP2-6b 三段之二 + 设钉部署)。**H(Q6)未动**, 需用户先裁定 R2/R9。研究分支 `research/book-uplift-2026-09-11` 提交链 `1446fe4e..de6e2818`(21 个提交, 逐个 pathspec); 执行器 `origin/main` 58256ed → 81ea654 → **d858c36**(两次电池 161/161)。

## 1. 请逐项复核(每项: 装置 / 收据 / 我的判词 / 反例可否重跑)
| 项 | 提交 | 装置(可重跑) | 收据 | 判词 | 请特别核 |
|---|---|---|---|---|---|
| J run_arm 入装置 + 原表→原决策集成 | b4d08fa1 | `v4_chain_2026-09-09/run_arm.sh`(d81359ae), `run_v4_arms.sh`, `chain_v4_monthly.sh`; `fp2_decision_fixture.py`, `tests_fp2_table_to_decision.py` | `FP2_receipts/suite_J_*.log`(arms 10/10, 集成 6/6, 决策 41/41, pipeline 484/484) | 树内副本永不被执行(W6/W9); 集成正控/负控 5 条 | 装置副本无 RUN_ARM_ROOT 是否真拒(W9); pipeline 计数 26/28→27/29 的理由 |
| E FP2-1 v2 真实重建 | fd61264b | `FX_DATA/devices/fx_fnd_hol_rebuild_v2.py`(8cff0d54) | `FX_DATA/receipts/fndhol_v2_2026-09-17/`, `CLOSURE_FP2-1_v2_rebuild_*` | 7/7 ok; 与 run 24 逐格只差 f_fund_iv 尾部 542 格 | C1 精确口径 +252 格的逐键分解; EMA 分母 40,560 的读法 |
| K NOSLEEP-1 | 435a317e, a836dd08, 执行器 81ea654 | `dl_quant_live/ops/check_nosleep.py` | `FP2_receipts/battery_prod_81ea654_*`, 错题 E-0917-D/E | 根因 = pmset 整存储渲染超时; UNKNOWN≠[]; 本机真实读 1.4 s | A9 真实读格是否会在别的机器上误红; E-0917-E 首次被拒的日志 |
| C 生产整书平价 | d36ea23b, 320b2a6a, 511255ef | `FP3_devices/producer_archive_vs_executor_read.py`; `FP3_devices/combosnap/*`(两个 launchd 代理, 只读) | `FP3_receipts/PRODUCER_ARCHIVE_VS_EXECUTOR_READ_*`, `PARITY_1789646400_*`, `PARITY_1789660800_*` | 154/154 身份; 12Z/16Z PARITY(权重逐名相等) | 快照的时序保证(源 sha 复制前后一致)是否足够; 「PARITY≠代码正确」的限定 |
| D 现金核账 | 9f6ef3ff, 2fe78592, dcd81342 | `FP3_devices/fp3_cash_recon.py` | `FP3_receipts/CASH_RECON_20260801_20260917.json`, `LEDGER_CENSUS_*`, `BNBUSDT_daily_*`; `RESULT_FP3_D_*` | PARTIAL: 缺口全部具名(平仓成交未记 / 单名止损未记 / COMMISSION 少计 283 USDT) | 加权平均成本法与场所 REALIZED_PNL 的可比性; BNB 按收盘换算的误差; 真实成本表(2.99 bps, maker 59%) |
| F K3 细化 | 0d6951b3 | `FX_DATA/devices/fx_k3_nan_legitimacy.py` | `FX_DATA/receipts/fndhol_v2_2026-09-17/RECEIPT_k3_nan_legitimacy.json` | LEGITIMATE_ALL(0 格必须失败); 3 名退市后 elig 仍 True | 判据本身(NaN 合法 ⇔ 窗内无结算行)是否过宽 |
| G F08 经济影响 | ba4c23bf, 82f0e109 | `FP3_devices/fp3_f08_null_test.py`(pod2, 27 s/臂) | `FP3_receipts/F08_NULL_TEST_2026-09-17.json` | NULL(处理 −0.0032 落在随机删格分布中位) | 分数层干预是否回答了 F08(训练层隔离未测, 已限定) |
| L 统一评估表 v1 | 6068f785 | — | `EVAL_FP3_L_unified_table_v1_*`, `FP3_receipts/LIVE_NAV_SERIES_*` | 实盘 21 天 +0.52% / 夏普 0.42 / maxDD −6.08%; 桥四条 | 实盘日收益定义(20Z→20Z, 外部流净额)与回放的可比性 |
| B FP2-6b | 20377486, afbce920, 7eb85635, 执行器 d858c36 | 生产者 3520d363; 读者 58256ed; `set_f10_pin.py`(工作树) | `FP2_receipts/fp2-6b_16Z_producer_evidence_*`, `_reader_acceptance_*`, `_pin_positive_control_realfiles_*`, `battery_prod_d858c36_*` | 三段之二 + 设钉部署; 第三段 = 20Z 锚钉下验收(20:33Z 自动写 `fp2-6b_20Z_pin_acceptance_*`) | 正控 D 格(无 f10_sha 文件在真钉下拒)是否就是「换 DL 腿不改钉 ⇒ HOLD」的证明 |
| I 历史账本 | aa0fefe3 | — | `PLAN_FP3_I_ledger_backfill_*` | 计划; 未取数未改账本 | 回填纪律是否足够(副本过看门狗) |

## 2. 需要用户裁定(H 前置)
- **R2**: `position_break` 改读对账输出 E_s —— E_s 是**不能被成交/请求/更正解释的残差(当前距离)**, 不是「期望仓位」(七轮更正); 让风控消费残差而非原始读数改变了接受域, 需用户字。
- **R9**: 跨窗对账的**部署起点**(从哪个锚/账本状态起算, 41 天账本回放是否作为前置)。

## 3. 今日已知未关(不在本批复审范围)
I 取数与副本回填; H 全部; C 第二段只有两锚(逐锚累积); L 随 C/I 更新; 训练成员集含退市名(F 附带发现, 资格规则后续); 电池 DRY_RUN 写入 `state/`(DRY_RUN 根)污染 `anchor_runs.log` 末行(已知)。

## 4. 当日实盘观察(16Z 深查)
本日 NAV −3.64%(twin −2.90%), 过 −2.68% 告警线, 距 −4.0% 单日止损线 0.36 pp, 看门狗未触发; 其余六项无异常; 已 push 通知。
