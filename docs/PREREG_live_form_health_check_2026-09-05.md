> **创建:** 2026-09-05 04:4xZ(本地 12:4x +08) | **Session:** b9646a9e | **状态:** 预注册(指标与形态冻结, 数字未看) | **用户字:** 09-05 "生成一版和线上策略完全一致的全面历史严格因果评估: 宇宙/费率完全采用线上; 完全线上动态权重(严格样本外); 成本不臆测, 用实盘真实成本与成交; ftrim/sigma fund gross/m1/m2 一致; 分年/季/regime/σ_fund; 2x/2.5x/3x 下夏普、最大回撤、年化 NAV、单日跌幅比例等; 最严谨全面的体检" | **仪器:** pod2 `w10_universe_recheck.py`(口径复审同装置, 默认路径逐位等价 port 基线)+ 实盘日志成本标定 | **作废条件:** 指标或形态在看数字后被改; 任何数字无脚本收据

# PREREG · 在役书全史严格因果体检(线上形态逐项对齐)

## §0 在役形态(逐项, 来源 = 代码/配置, 不凭记忆)
| 项 | 线上 | 回放对齐 |
|---|---|---|
| 宇宙 | `~/wide_shadow/syms450.txt` 449 名, 冻结名单(08-2x 选定); 交易集 = 名单 ∩ (qv4h ≥ 2.5e5) 且 ≥80 名 | 主臂 **U-PIT**: 逐月按过去 30 日成交额在已上市名中取前 449(严格因果); 副臂 **U-FROZEN**: 今日 449 名单回溯(带前视选择偏差, 只作上界) — 两臂都经 `UMASK_NPZ` 注入 |
| 秩基(M1, 09-04 上线) | fund 腿在更宽基(base_n ≈528)内取秩, 只交易宇宙内名 | `MEMBERS_TOPN=829`(秩基)+ UMASK(交易集)= 宇宙机制研究已验证的 M1 形态 |
| M2/M3, σ_fund 阶梯 | 未部署(阶梯 launchd 卸载, state .reserve) | 不加 |
| 腿与席位 | king(78 列 LGBM, 2022–25 训练)与 fund; rev24 掩码(LEGS=101); 席位 = 最近 900 锚样本外腿收益 msharpe, 掩码 king/(king+fund) | `LEGS=101 WRULE=msharpe LOOK=900`, 无 W3FIX; king = `slow_pred_pinned.npy`(逐年折外: 2024 由 <2024 模型, 2025 由 <2025, 2026 由 <2026); 席位由装置自身样本外腿行滚动产生(2024 上半年为暖机, 单列) |
| combo | 0.55 king 书 + 0.45 V2MAIN(F10)书, 各自 EMA 态 | `PHI=0.45`, F10 = 走前折预测 s42 与 s2027(60 锚 embargo, 至 2026-08-10; 若 2026 折模型在 pod 可前推至 08-30 则前推并标注) |
| FTRIM | rn8 ≤ −0.0010 的负费率空头置零 | `FTRIM=zero` |
| 书链 | sel qv4h≥2.5e5 & ≥80; sel 内去均值; L1; cap 2.5/n; EMA α 0.1; 带 2.5e-4; 非 sel 强制出场 | 装置同链(已逐位对齐 port 基线) |
| 止损 | per_name_stop wide: depth −0.30, 连续 2 锚, 冷却 7 天 | 臂 `d30_n2_c42` |
| 杠杆 | 执行器 re-demean + gross = 2.0×NAV(constant_leverage_2.00) | NAV 锚收益 = (net_ex / gross_total) × L, L ∈ {2.0, 2.5, 3.0}; 逐锚复利得 NAV 路径 |
| 成本 | 实盘: maker-only + −5022 拒单 taker 补单; 费(BNB)≈1.8–2.3 bps/成交额; maker 占比 85–96%; 未成交残差 | 由 §1 实盘标定替换装置 COST_B(补丁自报); 另报"装置默认成本"列作对照 |
| 资金费 | 交易所结算 | 面板费率 × 4/interval(口径复审已验: 同书差 −0.12 bps) |
| 收益口径 | 交易所记账 Π(1+r)−1 | 主报 **prod**(记账); 副报 log(Σ简单, 高估 7–10%) |

## §1 成本与成交标定(只读实盘日志 `~/dl_quant_live/state/live/pilot_log/*`, 自 08-26 combo 上线起全部锚; 方法冻结)
按名分三档流动性(装置 COST_B 的三档边界: qv4h 分位)统计: (a) 费 bps/成交额(fills 去重 trade_id, commission_BNB × 记录 px); (b) maker 成交额占比; (c) +60 s markout(有回填者); (d) 成交比 = 成交额/意向额(按边); (e) −5022 拒单率; (f) 单锚换手(成交额/venue gross)。产物 `cost_calib.json`: 每档 {maker_bps, taker_bps, maker_share, fill_ratio} 与全书均值, 附 n 与日期范围。回放成本 = 每单位换手 × [maker_share × maker_bps + (1−maker_share) × taker_bps] 逐档; 未成交残差不改书, 但报 **孪生差**(实盘真实 − 纸面目标, 已有 50 锚 −0.37 bps/锚)作为执行折价带。

## §2 指标(全部由 `health_metrics.py` 打印; 单位链在脚本内)
对每个臂 × 口径 × 种子 × L: 年化收益(算术 mean×2190 与复利 CAGR 两种), Sharpe(锚级 √2190 与日级 √365), Sortino, 最大回撤(NAV 路径)与回撤时长, 最差日/周/月, 日跌幅分布: 日 < −2% / −5% / −10% NAV 的天数与占比, 锚级尾部 p1/p5/最小, 8 锚累计 p5/最小, 日 VaR99/CVaR99, 胜率(锚/日), 换手与成本占毛利比例, carry 占比, **爆仓距离** = min(equity/gross) 相对维持保证金(按 Binance 分层保守取 gross 的 1.5%; 报最小余量与触及次数), 滚动 90 日 Sharpe 分布(p5/中位/p95)。切片: 逐年(2024/2025/2026)、逐季度、σ_fund 三分位(judge.py 定义, 因果扩展分位)、广度 regime(`regime_dash.py` 的宽/窄档定义)、负费率名占比三分位、BTC 30 日实现波动三分位。2024-H1 单列为席位暖机期。

## §3 臂(不多不少)
U-PIT × {prod, log} × {s42, s2027} × {实盘标定成本, 装置默认成本}(8 次)+ U-FROZEN × prod × {s42, s2027} × 标定成本(2 次)= 10 次装置运行; 杠杆是事后映射不另跑。**不做任何录取判决; 只报数字。** 实盘重叠窗(08-26→09-04)另报纸面 vs 真实对账(§1 孪生)作为标定收据。

## §4 报表
`docs/RESULT_live_form_health_check_2026-09-05.md`: 白话, 每表标 [单仪器 pod2], 负年份/负季度显式, 每个数字有 results/*.json 收据。
