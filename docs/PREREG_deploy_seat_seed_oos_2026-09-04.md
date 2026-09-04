# PREREG · 修复 E-0904-C: 实盘席位种子改为样本外腿收益(2026-09-04)
> **创建:** 2026-09-04T08:1xZ | **状态:** 判据冻结, **待用户字**(书行为改动: 席位将由 0.21/0.79 变为 ≈0.00/1.00) | **受据:** ERROR_LEDGER E-0904-C; 回放 FTRIM+M1 msharpe(诚实席位)vs 固定 0.21: 2023+ 夏普 3.56 vs 2.60, 2025-26 6.05 vs 5.24, DD −14% vs −32%, 2022-24 逐年 +22/+11/+12% vs −22/−1/−8%

## 1. 改动(生产者输入, 不改代码)
- 新种子 = 回放装置 canonpred_s42 的三腿 OOS 腿收益(2022-01→2026-08-15, 年折外 king; 三腿同源内部一致)+ 生产者自 08-16 起的 live 追加行(OOS)。文件: `leg_returns_oos_seed_2026-09-04.npz`(研究仓 wide_shadow_snapshot), schema 同 bundle。
- 静默窗: 备份 `state/leg_returns_live.json` 与 `shadow_bundle/leg_returns.npz`(MANIFEST 同步更新 sha)→ 写入新种子(live 追加行拼接)→ `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop` → 首锚 signal 行 w3 应 ≈ [0.0x, 0.1x, 0.9x](掩码后 king ≈0.0, fund ≈1.0)。
- RUNBOOK 月度重训: `leg_returns.npz` 导出改为 OOS 源, 加断言"king 腿 900 窗夏普 ≤ 2×年折 OOS"。

## 2. 验收(冻结)
首锚: w3_masked king ≤ 0.05; 目标权重差 Σ|Δw|/gross ≤ 25%(EMA 吸收); rc=0; 拒单分散; net/gross ±1.5%(换档锚放宽); 影子三书继续。30 锚: 书 net 与影子(旧席位反事实)差分记录, 判据 = 不劣于反事实 −20 bps of gross 累计。
## 3. 回滚
恢复两文件 + kickstart; 一步可逆。
## 4. 不做
不改席位规则本身(回看窗 900 / msharpe 形式); 席位口径改造(过链净贡献)另立预注册。
