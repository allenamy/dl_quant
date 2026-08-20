> **创建:** 2026-08-20 | **状态:** 装置入库(补齐"判决装置与结论同寿命") | **作废条件:** 不作废

# 2026-08-20 装置库 — 装置 ↔ 结论 ↔ 文档 对照

**入库理由**: 本日大量判决在 jpline/RunPod 上跑, 违反了项目规则"判官脚本当日入库"。此目录是补齐, 并从此改为**先写入仓库路径再 scp 到服务器**。

| 装置 | 产出结论 | 归档文档 |
|---|---|---|
| jp_depth_cond.py / jp_depth_cond2.py | 深水空头条件路径曲线(中位+3.0%回弹/均值−1.4%/p10−27pp) | PREREG_graduated_squeeze_response §1 |
| ope_gsqueeze_v1.py(**含1天前视, 留档自证**) / v2.py | 渐进止损嵌套CV: 盲测 −71/−105 bps/事件判负 | 同上 §5 |
| oi_quadrant_v3 / _4h(结果JSON在 results/) | OI象限双口径判负(日线2/5年, 4h在2024反向) | 同上 §6 |
| ext2020_judge.py | 2020-21前伸: 七年块结构(2020 −654/2021 −901 … 2025 +554/2026 +463) | 同上 §7 |
| adaptive_regime.py / adaptive_diag.py | 自适应regime: 代理级 +91 vs 静态−201/−2; 窗长稳健; 仅2次切换 | 同上 §7 |
| book_adaptive_stop.py(**v1深度记账错, 留档**) / book_adaptive_v2.py | 书级四臂: 在役止损 −2.8%净额/夏普+0.02; 自适应判负 | 同上 §8 |
| stop_conditional.py | 侧×资金费条件结构(空×极正资金费 −10.5bps) | 同上 §9 |
| cond_stop_book.py / _book2.py / _tail.py | 九臂+尾部电池+块自助 ⇒ 在役规则最优, 该轴封卷 | 同上 §9 |
| p1b_replay.py / p1b_ext.py | 簇断路器八档全不过闸 ⇒ 不部署, 改只报警绊线 | PREREG_cluster_breaker RESULT |
| tail_forecast_v2.py | 风险预测重做: AUC 0.63(旧0.51题目设错), 但vol-targeting −22%净额 | RESULT_tail_forecast_redo |
| wide_risk_replay.py / _replay2.py(**两版均未过自校验, 留档**) | — | RESULT_wide_book_risk_layer §1 |
| wide_faithful_stage1b.py + wide_stage2.py / _stage2b.py | 宽书四臂: 止损降maxDD 31-36%(在役书13.5%) ⇒ 换装前必须移植 | RESULT_wide_book_risk_layer |
| intraanchor_depth_watch.py | 锚间巡检器(launchd com.hsy.depthwatch, 20min) | ERROR_LEDGER §E-5 |
| cluster_risk_daily.py / detector_v2_daily.py | P1a 簇风险仪 / 探测器 v2 | ERROR_LEDGER §E |

**留档失败装置**: ope_gsqueeze_v1(1天前视)、book_adaptive_stop v1(深度记账无成本基重置)、wide_risk_replay v1/v2(自校验未过)—— 保留是为了让"结论为何被推翻"可复核, 不是垃圾。
