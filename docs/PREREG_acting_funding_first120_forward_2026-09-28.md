> **创建:** 2026-09-27 19:22 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** draft；REVIEW_READY_RUN_NOT_STARTED | **作废条件:** 窗口、来源、模型、映射、时钟、预算或数值门改变；旧六窗/F0额度不得复活

# 固定120真实输入：无 optimizer 的端到端通路装置

依据 `PLAN_acting_funding_learning_clock_2026-09-27.md`，本次仅交源码，未上传或执行网络入口。输入包已于19:02:42–19:03:08Z完成并经独立后验验收（93fd499d0）；root另核完整22件输出字节。旧F0严格字节身份仍UNRESOLVED，旧六窗和F0截止终态不变。本装置不改变train_frac、epoch或既有F10_FULL/R1.4失败判词。

## 冻结入口与依赖

源码和机读合同在 `multi_asset/exports/research/acting_lead_20260927/funding/first120_forward_sources_20260928/`；`FORWARD_CONTRACT.json`包含每份完整SHA。entry是 `funding_first120_forward_guard.py --run`，只调用同目录 `funding_first120_forward.py --worker <new_root>`。两个入口默认均只显示RUN_NOT_STARTED。完整命令在合同；Pod源码拟放同名独立目录，输出固定 `/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/first120_network_clock_20260928`，目录必须不存在。当前未运行此命令。

实际运行时先消费封存RESULT/TERMINAL/POSTVERIFY，强制COMPLETED/rc0与已批worker、guard、COMMAND源pin相符。所有包中已登记数组和JSON复哈希；acceptance/core实际import的`__file__.resolve()`必须为批准文件并复哈希，ACTUAL_IMPORTS写实物。包中INITIAL_STATE必须为Jan1起点、producer prefix0、q={}、n_positions0、cash/NAV100000、原sealed SHA83c32。不能只凭约定初始化。

领域依赖均只读：包 RESULT 2bc7bef5、TERMINAL93556a6e、POSTVERIFY b4dc7806；原first120 config3a482d58；model e8ed6a3e；原Net源码66bc7c3e（只AST提取Net定义）；原continuous1501c9f6、combo d7577e82、stage fb5a9407（只AST定义）；bundle3a8422f3、calibration fda34243。μ/σ与checkpoint逐数组相等。当前ad80输入、f1cd训练的checkpoint仅作跨时段实现检验，绝非重训模型/OOS。训练源码副本仅供身份阅读，绝不执行训练顶层。

## 固定通路与控制

- 120锚、Jan1–Jan21 2023、829全轴、17520×171稀疏X。Net110082参数不变、eval禁用dropout，原checkpoint载入。保留原a，但生产alpha=.1，a不进入书且如实报告unused。soft-rank温度.3，采用生产1-based平均秩的平滑延拓 `sum(sigmoid)+.5`。无参数/温度/窗口搜索。
- 旧OOF分数分别送原evolve，逐项精确核literal/scaled封存kc/fc/raw/weights/trade_mask/reason；9发布/111HOLD只属于这个正控。新的单checkpoint分数同时送原evolve与独立硬实现，逐锚kc/fc/raw/weights最大误差≤1e−12、发布/原因相同。producer在HOLD仍提交自己的稀疏kc/fc；执行HOLD保留实际数量。新评分无发布数预期，0发布不换窗。
- 软模式保留全部120锚的共享θ库存图；仅初始q stopgrad。前24锚排除目标但库存不detach。随后96锚，A0 price−fee，A1 price−fee+carry，`-mean+.25*ES5%`；分别报告price/fee/carry、A0/A1均值、ES和总损失梯度及carry对各锚score的梯度。
- 固定NAV100000、GM2一次；原十atom的expected partial fill，决策A+1440，原signed slip和USDT maker/taker池，quantity按P_dec定量。每事件fund优先于同刻fill，`-q(e-)*P_floor5m*rate`；当前fill前导数归旧库存。末端B固定，无跨界补label。价格现金按A/B持仓mark加fill现金，费用同fill名义，不重复收3.52。
- 先独立逐事件固定合成数量核同窗price/fee/carry系数，1e−8 USD门；实际给核对函数cash+0.01必须红。9104全部事件保留：q=0不删除。未知价格仅可在由固定合法/流动性集合证明永远无法持仓处标结构零；可能持仓的价缺失立即UNAVAILABLE，不零填原始价。此控制与原canonical现金证据不同；expected atoms没有lot/min-notional、stop或动态NAV反馈，不能称真实引擎fills平价。
- 参数方向固定Rademacher seed20260927除sqrt110082，两eps1e−3/1e−4；不挑方向/eps。记录RN8、cap、band、稀疏状态、发布、reshape、fill符号和ES尾部跨门。数值门`5e−4+.02|AD|`仅稳定分段可验；任一eps跨门或超差则梯度验收UNRESOLVED。另报|AD|/5e−4和低于绝对分辨率标记；即使误差门通过，也不签非零信号/赚钱证据。全部参数扰动后从基准copy_精确恢复并核hash，不创建optimizer。

## 资源与终态

保持RSS声明6GiB、软停止5.5GiB、公共余量8GiB（启动≥14GiB），同UID RSS+6≤30GiB；GPU空闲、util0、compute PID空且已用≤64MiB，GPU预算8GiB、Torch allocator限7GiB。CPU1，单次wall300s，64KiB真实fsync quota probe。先完成资源门再进入worker；拒绝只落RESOURCE_REFUSED，不排队、不重试、不创建新截止。

guard每50ms采样本task worker+guard RSS/HWM，GPU每500ms查询、1s超时；记录实际最大间隔，超过软线/GPU/300s/公共余量就仅终止本worker PGID。其它GPU工作出现即自停，为KSR/D10让路；无cgroup设置、共享cache处理或他人进程动作。worker同deadline SIGALRM。软件采样不是内核硬上限；结束后以worker真实高水位再检查，未观测到不等于绝不会越限。

显式规模：X float32约11.43MiB、两个hidden各17.11MiB，model/grad各0.42MiB；完整书每120×829 float64数组约0.76MiB，原始价mmap约36.44MiB，9项参数梯度约3.78MiB；pairwise矩阵只在每锚成员内构建，`sum(n_i²)≤829×17520`给单个double pairwise总≤110.82MiB，非每个全轴829²。autograd保存张量、allocator、框架context和临时内存另计，不能用这些静态量或旧1.293GiB合成峰冒称硬上界。只有一个反向图，FD前删除obj引用；四次FD前向在no_grad中串行。预计分钟级；不因超过预期另开预算。

准备阶段已运行6个stdlib source/gate/scalar test（含内部多个红控），未import Torch/NumPy、未运行网络/optimizer。这不能代替真实硬平价、现金控制或参数FD；都须在root审核授权后的单次装置里照实出终态。即使全部控制过，结果仍仅实现通路；完整单折训练与多折完整书评价需另立授权，旧F0字节门继续保留。
