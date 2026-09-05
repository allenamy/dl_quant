# MANIFEST · allweather_2026-09-05/carry_layers(资金费结算时点层三臂: D 躲避 / H 小时名 / L 多头门槛)
> **创建:** 2026-09-05 15:4xZ | **Session:** b9646a9e / Track C agent | **预注册:** docs/PREREG_carry_layers_2026-09-05.md(f882c72c… @2ec1934; 当前 23c87065… @d74f93b 仅表头时间戳)| **结果文档:** docs/RESULT_carry_layers_2026-09-05.md | **pod 源目录:** pod2 /workspace/review_scratch/allweather_trackC/carry_layers/(dev/ dev_alt/ 的 26 个 npz 产物与 data/sett_tables.npz 26 MB 留 pod, sha 见 logs/chain_*.log 与 data/sett_receipt.json)

| 文件 | 内容 |
|---|---|
| w10_health_orig.py / w10_carry.py / device.diff | 体检装置逐字节副本(8684d9a9…)/ 补丁装置(28e9b5e9…: DODGE_THR·DODGE_COST·DODGE_RULE·HOUR_K·LONG_HI; 全关逐位同)/ 62 行 diff |
| setup_cl.sh / run_arm.sh / chain_identity.sh / chain_arms.sh | 布局(14 SAME)/ 单跑包装 / 恒等 4 格 / 22 臂(D 6×2, H 2×2, L 2×2, 组合 ×2) |
| check_equiv_cl.py | 恒等收据脚本(四数组 array_equal + max|Δ| + config 去 CARRY/HEALTH 相等) |
| build_settlement_tables.py / data/sett_receipt.json | 逐 (锚, 名, 槽) 结算表构建(fund_aug 全史 + 5m ret5 漂移窗 [S−10m,S+25m))与收据(2,455,415 事件; 缺 bar 0.90%; 面板 iv 一致 99.4%; prev == f_fund_now 100%; ret5 约定 y4 == Σ ret5[E..E+47]) |
| judge_cl.py / results/judge.json / results/tables.md | 冻结判官(§3)与全部数字(水平/配对 Δ/D 分解与漂移/H-L 放弃 alpha/prev-oracle 差/判决) |
| drift_diag.py / results/drift_diag.json | 机制诊断: 所用窗 vs 安慰剂窗(±1/2/3h)、整锚收益、全事件按费率分档 |
| bucket_diag.py / results/bucket_diag.{json,md} / logs/bucket_diag.log | 附录 §9 诊断表(组长追加): 基线持仓 × 窗内全部结算事件 1,572,105, 按结算费率分档 × 持仓侧: 缴费/价格移动 [CI]/加仓 EV/名义占比; 无臂无判决 |
| diag_ret5.py / logs/diag_ret5.log | ret5 bar 约定探针(其 0.8 GB 缓存已删) |
| ledger/ledger_table.py / ledger/ledger_table.{json,md,log} | 实盘账本 08-16→09-05 只读: 可避免缴费/躲避名义/净 by THR×间隔×COST; 符号约定核验 100% |
| logs/setup_cl.log / check_equiv.log / chain_identity.log / chain_arms.log / commands.txt | 布局与输入 sha / 恒等 4/4 PASS max|Δ| 0 / 产物 sha / 26 条逐字命令 rc=0 |
| logs/*_prod_s*.out, logs/B0_*.out | 每跑 CONFIG·SETT injected·RECEIPT_CARRY·RECEIPT_EX |
| logs/build_sett.log / judge_cl.log / drift_diag.log | 三个脚本 stdout(judge 首行单位链) |
| logs/chain_identity_attempt1_quota.log / commands_attempt1_quota.txt | 15:10Z /workspace 配额事故的首次尝试日志(截断产物已删并重跑) |
| SHA256SUMS | 本目录全文件 sha(不含本文件与自身) |
