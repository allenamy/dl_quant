> **创建:** 2026-09-27 17:03 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** D10共同输入/价格/成员或时钟合同改变；本文未授权新增训练，不把六窗夹具视为候选有效

# 完整 fold 的最小同钟现金代理

本计划接在53b61495f的六窗网络夹具后。夹具只验证网络参数可达性；完整fold不需要找回更多历史逐笔实盘成交，也不要求可微代理逐位复现非线性撮合。需要固定一个有明确成本假设的因果执行代理，再由原canonical全书引擎评价。

## 已定位的可复用输入

- `/dev/shm/news2_2026-09-23/engine/bt_hist_sim31.py` 已有 `CfgMap31`：历史无rid时 `t_dec=A+1440`，再按原calibration的first/later-leg pooled offsets逐笔fill。`HistSim31`继承canonical v3.1的事件优先级、费用、持仓现金、止损及订单计划，不另写模拟器。
- 原始价全网格 `/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy`，SHA `23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8`；meta `price_full_raw_x0918r_meta.npz`，SHA `d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90`。已核实际存在，2.8GiB+3.9MiB。用已有`FullPanel`公式，只读mmap每120锚所需5分钟小块；不能用旧y4s替延后成交价窗。
- D10完整ms账 `/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz`，SHA `76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db`。按同symbol、逐原始事件时间和rate保留；没有持仓的事件也不能删，以免后续梯度漏费。
- 已归档D10共同特征 `/workspace/d10_reread_2026-09-27/r6_assemble/NEWS_FEATURES_D10EXT.npz`，SHA `ad80d50d1f8b953a317845a88ff2ae7399ad8cfdd967a49f492cb8094a6314c1`。这是已定位修正输入，不能仅因路径叫D10就宣称最新主线已验收。正式跑之前需等待D10主线冻结当前接受的共同输入SHA；若更新，A0/A1必须一起使用同一新版。NC旧特征3c886a2b…只保留参照，不混成新修复模型。
- canonical calibration SHA `fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6`；成员/交易许可和UNAVAILABLE集从同一run config pins及NEWS2 adapter读取。原config基础universe不是adapter实际扩展universe，不直接沿旧6322b573…：NEWS2 adapter明确用`/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz` SHA `3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f`。新D10组合必须绑定自己的完整adapter收据。

## 只新增一个因果执行代理

复用原Net、合法成员utility和alpha，但明确保留两个状态：producer EMA权重h=(1−alpha)*h+alpha*u，以及实际数量库存q。每120锚起点h=0、q=0，前24锚burn后继续同一双状态，训练起点不再清零。固定benchmark V0=1 USDT、GM=2，决策价P_dec=P(floor5m(t_dec))，目标数量q*=GM*V0*h/P_dec，计划变化Q=q*−q(t_dec)。GM只在这里乘一次；全部price、fee、carry现金统一乘1e4/V0得到NAV bps。固定V0不按模型盈亏重定量，和canonical动态GM*equity(b_dec)的差额是明示近似，不称精确复现。把同一次目标数量变化按既定期望成交核分配：first-leg五个tau用原tw乘r1，later-leg五个tau用原tw乘r2；未成交余量保持旧持仓。producer h不乘r1+r2；只有q按实际发生的partial fill递增，二者不能混成一套“held”。新数量只在各fill时刻生效，结算按funding先于同刻fill规则。先held、后partial fills、再new-held的数量通路必须保留；不允许把new target提前到A整点。

这个代理明确假设：固定十个成交时间atom，r1=(1−p_rej)*(p_full+p_part*fbar_part)，r2=(1−r1)*pi_fill；忽略lot/min-notional门、撤单及保护反馈。first-leg为maker，later-leg费用用maker_share混合；历史fee使用HistSim31的当前USDT费格，slippage分别用原first/later值，不在两臂之间改变。它不是实际订单实现，既不承诺满额成交也不拿代理收益当可交易净收益。由现有calibration直接得到r1=0.581006080491、r2=0.252908573708、总期望执行比例=0.833914654199，没有新参数。它把已存在成本假设施于历史，是固定benchmark执行假设而非该历史时点已知的重新估计。first/later路径不能为了利润从数据中挑选；后续canonical引擎仍按真实计划、拒单/partial、min-notional与保护逻辑执行。

fill价格严格按canonical `P_dec*(1+sign(Q)*slip_first_or_later)`，不能替换为P(fill_time)；原first/later slip都是负数，原符号保留。以同一数量事件流计算三项：价格为持仓在每段标价变化及这个fill现金的账，已经包含slippage；手续费在fill时刻按abs(fill_cash)*fee_rate收取（平滑abs只用于梯度，原引擎账保持实际abs）；资金费为每个事件`−q(t−)*P(floor5m(t))*rate`。所有项使用同一锚边界和归一化名义，GM/NAV单位显式写入收据。旧3.52换手惩罚在两臂都移除，不能与真实fee/slip叠收。A0/A1一起改为此同钟价格及成本，A1仅新增实际carry，不声称对原NC的单变量改动。原NC价格标签/损失保留为独立参照。

输出接口只需每个120锚span的小包：`anchors, members, decision_px, fill_times, fill_px, fee_rates, settlement_times/symbol/rate/px, raw_price_valid, legal_mask`。该span终端固定B=A_last+14400；最长t_dec+tau=A+2638.259s<4h，全部正常十atom在B前；窗口(t0,t1]及fund-before-fill优先级写死，不为末端后续carry延长标签。若原始ms记录的边界归属与现行canonical秒消费者不同，先具名对账并统一合同，不能各用一套时钟。原始数据最大消费时刻、经济有效时刻及训练cutoff都写入首span收据。包是输入系数，不含任一臂收益；现读现用，不落盘整份features或全史展开价格。held在span前24锚burn并贯穿96训练锚，沿原`span_admissible`思路核全部可能held成员。可达时刻涉及的必要价缺失就整span拒绝并具名记因；不能把未知carry/price置0。训练和最终全书分别报告拒绝/UNKNOWN人口，不能把缩样本损失与全人口NC作收益比较。

## 首次实现与门

1. 先只取原202608 admission中的时间上第一条合法120锚span，在同一raw价格、同一费率账、固定目标下，用既有HistSim31的只读tap导出持仓事件和费用。核基准逐事件cash以及代理数量通路；成交假设造成的差额具名拆出，不要求非线性策略反馈的梯度相等。任何未说明的时钟/符号/单位差异都挡住训练。
2. D10 ms adapter在送入按秒查询的canonical消费者前必须明确闭合。先查实际运行适配器是否已按同秒聚合；若尚未闭合，则在独立适配器保留原逐ms现金对照，只对同秒、同结算价、同现金窗口归属，且从秒桶首时刻到最后ms事件的整个压缩区间q不变的事件求和；不能只查两fund之间无fill。反例：.100秒fill、.900秒唯一fund，按秒提前会改q。必须覆盖fill/flatten等全部改q事件，并以同刻fund优先逐事件核验；不满足时保留浮点ms事件时间和每事件专属rate接口，不直接灌入int(t)字典。不能last-write覆盖，也不能由旧类文件推断当前全书已错误。
3. 对第一span做F=0的loss/梯度/参数/optimizer严格恒等、费率反号、new回溯收费红控、fill前梯度0、fill后现金独立有限差分。以原模型参数梯度而非score变量度量carry/price/fee比例。门通过后才扩展原fold所有149条候选训练窗，成员价可观测规则导致的新增拒绝必须先披露，不改窗口步长/参数/学习率。
4. 首轮仍只s42、202608、同初始化、同打乱、同一epoch，A0/A1两臂；用于实现和资源验收，未作为候选有效。下一阶段由主研究员另冻结多fold、两种子的完整训练和严格隔离评价。不能因短夹具梯度大就跳过多regime，也不能因梯度小就否定F10-N。

## 完整书与预算

A0/A1输出用同D10特征训练的King/资金费席位和同一合法成员、raw价格、actual cash ledger进原`continuous_combo.evolve`及NEWS2 adapter，先以同输入F10正控核kc/fc/raw/weights/trade_mask。保留完整King+F10+fund组合、链、GM、32个执行路径、手续费、止损与UNKNOWN；同时给共同D10基线和NC参照。不能仅看独立F10腿或预分片carry增量下收益判词。新输入如需要重建King/轻量T2，按主线资源门排，不复用旧输入预测来命名正确口径候选。

资源建议（未执行、不是本轮自动扩权）：第一120锚CPU1、RSS≤2GiB、≤5分钟、≤10MiB；完整fold同钟小包CPU1、RSS≤6GiB、≤10分钟，逐span消费。两臂一epoch预计45–120 GPU秒（原训练149窗单epoch22.25秒，仅为下界参考），含系数与控制整体≤15分钟、GPU≤8GiB、结果≤10MiB；单窗先实测再外推，超过即停本任务而不减少控制。整套多fold两种子及32路径整书另排预算，不与KSR/D10争资源。真正阻塞条件是输入/时钟/UNKNOWN或资源门失败；现有原始价、事件账和模型输入都已定位，不再以“缺历史实盘逐笔镜像”作为停止理由。

独立静态复核：research_resume_0927于17:12–13Z指出上述聚合压缩区间、decision-reference成交价、EMA/数量双状态、末端边界、GM/fee单位五项；均在首120锚执行前写明。该复核未跑执行器或候选，不构成cash新读数。
