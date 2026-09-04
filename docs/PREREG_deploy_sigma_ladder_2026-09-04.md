# PREREG · 部署 σ_fund 条件化 gross 阶梯(2026-09-04)
> **创建:** 2026-09-04T07:2xZ | **Session:** 主线 | **状态:** 判据冻结, 未部署 | **作废条件:** 首锚验收入档 | **用户字:** 09-04 "都做"(杠杆保持 2×)| **受据:** `docs/RESULT_allweather_2026-09-04.md` H1(臂 C: 2021+ 夏普 0.07→0.33, 2023+ DD −37%→−29%, 2024 −8%→+3%, 2025-26 不变; 四判据全过)

## 1. 规则(与回放逐字同)
- 触发量: 锚 t 的 σ_fund(成员 8h 当量费率横截面 std, 仪表盘 `sig_fund_bp` 口径; 与面板成员口径实测比值 1.000/corr 1.000)的 **30 锚滚动均**, 在**滚动 2 年(4380 锚)分布中的分位 p_t**(因果, 只用 ≤t; 历史由面板 2023-01→2026-08-15 序列种子 + 实盘仪表盘序列续接)。
- 状态 g ∈ {1.0, 0.5}: g=1.0 且 p_t < 0.33 连续 ≥84 锚 ⇒ g=0.5; g=0.5 且 p_t > 0.50 连续 ≥84 锚 ⇒ g=1.0。初始 g=1.0(2025 年起从未进低档)。
- 作用: 执行器目标 gross = NAV × gross_mult(config, 2.0) × g。**g 只在锚间由仪表盘作业写入状态文件, 执行器锚内只读**; 状态文件校验: g ∈ {0.5, 1.0}, 写入时间 ≤ 6h, schema/sha 合法; 校验失败或缺失 ⇒ g=1.0 并 INFO 告警(故障安全 = 不减仓)。
- 换档 = 书行为事件: 触发时 INFO 推送(含 p_t 序列与 streak), 记 anchors.jsonl `gross_ladder` 字段; 换档后首锚按建仓/减仓锚模板验收(换手可达 50%)。

## 2. 实施面
- 仪表盘(研究仓 regime_dash + 运行目录): `sigma_ladder.py` 每锚 N+50 运行: 读 `sigma_seed.json`(面板种子)+ 仪表盘 jsonl 历史 → p_t, streak, g → 原子写 `~/dl_quant_live/state/live/sigma_ladder.json`(执行器只读该文件; 写入不经 git)。
- 执行器(live 仓, safe_commit + 电池): `live/sigma_ladder.py` 读取/校验; `external_book.py` 目标名义 × g; anchors 行记录; 新套件 `tests_sigma_ladder.py`(校验/陈旧/越界/缺失=1.0/算术)+ SUITES 注册 + gate_coverage 盲区条目。
- 部署顺序: 执行器改动先上(g 恒 1.0, 行为零变化)→ 仪表盘作业上线(当前 regime 下 g=1.0)。

## 3. 验收(冻结)
- 执行器换装首锚: anchors 行含 gross_ladder{g:1.0, pct, streak, src}; realized_gross/目标 ≥97%; rc=0; 电池全绿含新套件。
- 仪表盘作业: 逐锚写入; 种子序列与面板逐位同(sha); 当前 p_t 与 2023+ 分位表一致(±0.02)。
- 首次真实换档(若发生): INFO 推送 ≤1 锚延迟; 目标 gross 变为 NAV×2.0×0.5 ±3%; 30 锚后按 RESULT_allweather 口径复核(低档期间书净额 vs 反事实全仓)。
## 4. 回滚
删除/置 g=1.0 状态文件即刻恢复; 执行器代码回滚经 safe_commit。

## 5. 执行器侧换装收据(2026-09-04 09:34Z)
- live 仓 **4b8ca20**(safe_commit, 电池 **ALL GREEN 124/124**, 含新套件 tests_sigma_ladder 13 项; 已推送)。三次红后修正: ① 印记文案破 L2 → g=1.0 时印记不变; ② `from live import` 破 tests_external_book(live/ 走 sys.path 直导入)→ `import sigma_ladder`; ③ S4 合约(size_book 调用字面量)与 tests_imports 生产模块名册 → 默认路径逐字不变 + 低档单独分支 + PRODUCTION_MODULES 登记。
- 改动面: `live/sigma_ladder.py`(evaluate/load, 故障安全 g=1.0), `scheduler/anchor_loop.py`(g<1 时 target_leverage=gross_mult×g 并印记; anchors 行 weights.gross_ladder), `run_acceptance.sh` SUITES, `ops/gate_coverage.py` 盲区条目, `live/tests_imports.py` 名册。快照入研究仓 `dl_quant_live_snapshot_2026-09-04/`。
- 仪表盘侧: launchd `com.hsy.sigma_ladder`(N+52)已装; 首次写入 `state/live/sigma_ladder.json`(g=1.0, p≈0.65); 执行器读取端复核见下条。
