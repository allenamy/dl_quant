# MANIFEST · allweather_2026-09-05/carry_sleeve_diag(纸面 delta-neutral 资金费 carry sleeve 上界 + 与在役书的分散算术; 诊断, 无臂无判决)
> **创建:** 2026-09-05 17:3xZ | **Session:** b9646a9e / Track C agent | **立项:** 组长 09-06 round 4(定义先于数字)| **结果文档:** docs/RESULT_carry_sleeve_diagnostic_2026-09-05.md | **pod 源目录:** pod2 /workspace/review_scratch/allweather_trackC/carry_sleeve/ | **输入(只读):** carry_layers/data/sett_tables.npz(f1c33629…)、/workspace/data/wide_panel_4h_v2ext.npz(f_fund_now 预测量)、carry_layers/dev_alt B0_prod_s42/s2027(书基线, 数组逐位 = health_check M1); 零次新 API 请求

| 文件 | 内容 |
|---|---|
| carry_sleeve.py | sleeve 定义(K∈{10,20,40} × h∈{5,10} bps/次, 等权 1/K, 进出 top-K 即换仓, 成本 3.92+10 bps/单位换手, 忽略基差/借币/现货可得性)+ 书对齐 + 混合(1:0/.8:.2/.7:.3/.5:.5)+ 分析行(等波动与实测波动的 S2 needed, 杠杆倍数, vol-matched 混合) |
| results/sleeve.json | 每臂逐窗水平(净/只算收入)、成本、间隔构成、重叠、每种子 ρ/混合 Sharpe/分析行、breakeven_table |
| results/sleeve_tables.md | 上述表格(水平 30 行、成本与重叠、分散、分析行、只算收入混合、break-even) |
| logs/carry_sleeve.log | 脚本 stdout(表格 + SLEEVE_DONE) |
| SHA256SUMS | 本目录全文件 sha(不含本文件与自身) |
