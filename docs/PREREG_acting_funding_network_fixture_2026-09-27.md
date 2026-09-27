> **创建:** 2026-09-27 16:52 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** 修改六窗/双臂/时钟/输入；资源门不满足；任何参数通路结果不得升级为候选或OOS收益

# 固定真实路径上的两臂网络实现计划

主审在16:48后续期授权，16:51同意把原202608整fold烟测收窄为已认证Aug26–27六窗网络夹具。原报告§10“旧授权过期不自启”保留为当时事实；本次是新授权。使用writing-plans与executing-plans流程；自行实现，主审复核。没有新增模型/参数/系数搜索。

目标是验证171维F10参数能经过可达fill影响真实cash，并检验F=0的loss、梯度、参数及AdamW状态严格恒等。六窗在NC原OOF区段；在这里优化属于已知数据实现测试，不能生成候选、OOS判词或泛化收益。原认证现金门、原NC 202608模型/预测保持引用；不修改任何D10文件。

## 冻结输入与线性化

固定6f14e4ef6的initial_state/trade_log/fund_log、INPUT_MANIFEST 59875e5a…、原canonical simlib价格panel和FundingBook、seed02前六个windows。同一价格来源已有现金核验。新通路需要枚举原FundingBook的全部未来事件（含基准q=0未进入fund_log者），避免把“基准未持有”误作“无结算”。先验证每窗price/fee/funding再做优化。未知price拒绝，不静默填0。

NC NEWS_FEATURES SHA3c886a2b…，legs9ee5886f…，202608 model SHA9475cdb3…；只按固定六窗实际rebalance fill的anchor取特征。ZIP为stored NPY，直接只读memmap指定rows，不落盘完整特征；合法成员继承NC旧输入，仅服务一致实现测试。mu/sd取原202608训练集的checkpoint；网络用原Net/utility AST、随机种子42初始化，两臂复制同state。原171→256→256→1、alpha、soft-rank tau=.5、AdamW lr3e−4/weight_decay1e−4、clip1、ES5%系数.25保持。每臂一epoch定义为六个区间合成一个完整batch、一次optimizer step；无验证择优。固定dropout RNG使所有对照在相同mask下。

令w(theta)为该anchor utility与alpha递推结果，w0为相同初始参数及mask结果。对每个实际rebalance fill l=(A,s,t,dq,P)，定义

`delta_q_l = NAV0/P_l * share_l * (w_A,s(theta)-w_A,s(theta0))`，其中share为该(A,s)全部实际fill的绝对成交名义占比。不在NC成员中的实际fill、保护flatten与初始held完全冻结；所有实际fill均保留，未覆盖数量和名义单列。这是固定实际成交路径附近的明示线性化，不是新目标将产生同样成交的声明，也不含重规划、保护单反馈或当前完整King+fund重建。

每窗价格增量按该fill真实时刻：窗内fill为delta_q*(P_end-P_fill)，窗前fill为delta_q*(P_end-P_start)，窗后0。费用在实际fill所属窗计算`fee_per_abs_qty*(abs(dq+delta_q)-abs(dq))`。carry增量为每笔严格晚于fill的结算`-delta_q*P_settlement*rate`；同刻funding优先，所以t_fund<=t_fill导数为0。price/fee/carry统一窗口(t0,t1]，加到原认证完整书基准cash，除以固定NAV0乘1e4，单位明确为这个fixture的NAV bps。

A0=-mean(price-fee)+.25 ES5%；A1仅加事件时持有carry现金。两臂共同使用上述实际fill价格窗；A0不是原NC旧y4s损失逐位重现。F=0零费率控制包括held基准carry也归零，故loss、参数和optimizer应逐位相同。实际A1保留无法由new改变的初始held carry常数，它可改变ES尾部选择，但其直接参数导数应0。

## 步骤与判据

1. 先准备真实同钟coefficients；基准六窗price/fee/carry≤1e−8USD。抽已存BONK先fund后fill例：该早期事件关于新fill梯度必须0；错误回溯非零必须红。F反号、F=0以及可达现金有限差分必须通过。所有事件含q=0也按原FundingBook列举，边界严格。
2. 两臂同初始化同batch各一次更新。另做不额外训练的F=0对照复制，两份AdamW一步后参数和完整optimizer状态逐位相同；这是仪器正控，不是第三候选臂。报告网络参数carry/price/fee梯度norm、L0/L1方向、alpha、两臂参数差；不得把局部方向称整书改善。
3. 记录原NC checkpoint、原OOF分数身份和固定输入coverage；原收益P/S/σ在这个极短已用于优化的fixture不作有效性门。输出model仅标IMPLEMENTATION_FIXTURE，不接候选链。归档所有实际读数/失败及代码SHA。

## 资源与运行

仅Pod CPU1、进程RSS≤6GiB、GPU≤8GiB；启动必须cgroup剩余≥14GiB、GPU空闲、同UID RSS+6GiB≤30GiB，输出真实16MiB quota probe后移除probe文件。不满足写QUEUE收据，不降预算绕门。以通过启动门时开始最多15分钟wall，watchdog只停止本任务PGID，RSS/GPU超限即停止并留日志。预计输入哈希/小切片/Panel<90秒，控制与双臂一步<30秒，输出<10MiB；不抢KSR/D10，资源不够等待。

文件：`multi_asset/exports/research/acting_lead_20260927/funding/funding_network_fixture.py`实现；同目录独立run receipt/日志/小型结果；Pod新根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/network_fixture_20260927`。不写共享registry/STATE。
