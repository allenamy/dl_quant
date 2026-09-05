> **创建:** 2026-09-05 07:1xZ(本地 15:1x +08) | **Session:** b9646a9e | **状态:** 预注册(臂与判据冻结, 数字未看) | **用户字:** 09-05 "dl 的权重应该合理确定, dl 和 king tree 是完全不同的两个策略, 没道理共享权重. 充分严谨回测, 并确定最佳设置和方案" + "各个腿确定权重的时候是基于夏普还是每锚净额, 成本项按什么考虑" | **前置:** PREREG/RESULT_retrain_cadence_and_seat_rule(轴 B R1–R5 全 UNDECIDED), RESULT_live_form_health_check(在役形态、实盘费用标定) | **作废条件:** 判据/臂在看数字后被改; 装置默认路径与 axisB R0 基线不逐位等价

# PREREG · 席位二轮: V2MAIN 自有席位 / 净额口径席位 / 两书动态混合

## §0 现状(代码事实)
在役席位 = 最近 900 锚**价格毛收益**(秩书 × 下 4h 收益, 不扣手续费、不扣/不计资金费)的 mean/std 按比例分配, 掩掉 rev24; V2MAIN 书**共用**同一个席位(它的分数只替换 king 的位置), 两本书按常数 φ=0.45 混合(PREREG_leg_ablation_2026-08-26 §T5 定)。装置已有开关: `SEATF10`(F10 书用自身四腿腿收益算席位, 结果放 W3FC)、`SEATNET`(席位输入扣 4h carry)。

## §1 臂(形态 = 体检主臂: U-PIT 因果宇宙, UMASK_SCOPE=m1, LEGS=101, msharpe LOOK 900, PHI 0.45, FTRIM, d30_n2_c42, 实盘费用三档; 口径 prod 主 / log 副; F10 种子 42/2027)
| 臂 | 定义 | 装置 |
|---|---|---|
| B0 | 在役: 价格毛收益席位, 共用, φ 0.45 | 基线(= health_check M1_UPIT_prod_s{seed}_ccal 逐位) |
| B1 | V2MAIN 自有席位: F10 书的 fund/F10 分配由 F10 自己的 OOS 腿收益经同一 msharpe 规则产生 | `SEATF10=1` |
| B2 | 净额口径席位(扣 carry): 腿收益 − 该腿单位 gross 书的 4h carry | `SEATNET=1` |
| B3 | 净额口径席位(扣 carry 与换手费): B2 再减 腿换手 × 2.035 bps(实盘标定的每单位换手费用) | 新增 `SEATCOST_BPS=2.035`(自报; 默认 0 = 不变) |
| B4 | 两书动态混合: φ_t = shp(F10 书)/(shp(king 书)+shp(F10 书)), shp = 前 900 锚两本书各自 OOS 净额(价格 − carry − 费)的 mean/std, 负归零; φ 限幅 [0.2, 0.8]; 首 900 锚用 0.45 | 新增 `PHIDYN=1`(自报; 默认 0) |
| B5 | B1 + B4 | `SEATF10=1 PHIDYN=1` |
| B6 | B3 + B5 | 全开 |
共 6 臂 × 2 口径 × 2 种子 = 24 次运行(+B0 复用)。不加臂。

## §2 判据(冻结)
配对 Δ = B_k − B0(net_ex 每 gross bps/锚), UTC 日块 bootstrap 2000, 种子 20260905; 主判窗 2025→26, 辅判 2024→26 与 2024-H2→26(去暖机); 四格 = {prod, log} × {42, 2027}。
- **ADMIT 候选**: 四格 CI95 下界 > 0 且换手 ≤ +15%。
- **不变差**(用户 09-05 规则, 用于"合理确定"而非录取): 四格 CI95 上界 > 0 且点估计 ≥ 0 的格 ≥ 3/4 且 maxDD 不劣于 B0 +10%。
- **REJECT**: 任一格 CI95 上界 < 0 或换手 > +25%。
- 报每臂席位轨迹(king/F10/fund 逐年均值、φ_t 逐年均值与切换次数)、σ_fund 分档 Δ、逐年表(负年显式)、2× 下回撤。
- 最佳方案 = ADMIT 候选中 2025→26 点估计最高者; 若无 ADMIT, 在"不变差"臂中按机理排序报告但**不推荐上线**。

## §3 产物
pod `/workspace/review_scratch/seat_round2/`, 装置 diff 与等价收据, judge.json, REPORT.md; 结果入 `docs/RESULT_seat_round2_2026-09-05.md`。
