> **创建:** 2026-09-27 18:23 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** draft；供 root 审，未启动训练 | **作废条件:** 共同输入、固定映射、时钟/损失、训练人口或预算改变；不得续用过期六窗预算

# 沿真实库存时钟检验 F10 资金费目标：最小两臂设计

首 120 现金接口已经完成，不再以缺镜像阻塞。证据为 ddd8ef3b6/a1dcd597a 及 `RESULT_acting_funding_mechanism_2026-09-27.md` §13：9/120 发布、111 HOLD，5,225 fills、9,104 全资金费事件，独立初始数量/逐事件现金闭合。这里只证明装置；该窗不代表策略全人口，也没有新网络参数梯度或收益证据。本计划先检验参数通路，再决定是否值得独立申请完整学习实验；当前不启 GPU。

## 1. 新假设与已失败试验的关系

| 已有工作 | 实际检验对象和状态 | 本次不能据此偷换的对象 |
|---|---|---|
| DLARCH T3 | 自制权重映射换成可微生产 chain，含 RN8；REJECT。对 T0 2026 −1.418 bps/day、0/3 正；对 NC −2.622。原/修订两判据均 REJECT。 | 本次完整 chain 是两臂共同装置，不能将其效应重新命名为新成功。沿用原失败记录，不重跑 T3 或其 tanh 敏感性。 |
| DLARCH T2 | 原臂将 detach King 的书混入 F10 净效用，仍用 y4s 和3.52；收益单位残差 Ridge/LGBM 是另一条前置证据，并未证明混合损失有效。 | 本次 King/资金费席位和完整书在两臂中完全相同，不加 King 特征、不改残差标签，不以 T2 的 IC 保证本次有效。 |
| F10-N 提议 | 原 T_NET 扣费近似，未因 KN 秩标签 FAIL 自动得到连续目标判词。 | 本次不能把旧 T_NET 或朴素 ms(A,B] 直接乘 new(A) 当成本；必须使用事件时持有的数量。 |

来源：`RESULT_dlarch_G3_why_DL_underdelivers_2026-09-26.md` §1.4、`DECISION_RULE_dl_program_book_gate_2026-09-25.md` §11(a)、`PREREG_dlarch_T2_leg_gate_2026-09-25.md` §1/R3。保留整个 DL 程序家族的试验次数；此设计只因旧目标没有**执行可达的事件现金归属**才有新的可证伪问题，不能重置先验或多重性。

**H_clock**：固定同一网络/特征/完整组合映射与价格成本时，按事件库存承担资金费产生可达的网络参数梯度；这个梯度对前锚库存和当前新成交有不同归属。机制通过不意味着梯度大、OOS 有利或收入可观。即使 H_clock 成立，完整书收益仍可能零或负。

## 2. 两臂定义与单位

原 NC 配方保留为只读参照 R_NC，另保留当前 D10 重打分完整书 R_D10。A0/A1 共用同一执行时钟价格和实际费用代理；A0 不是原 NC 逐位复现，因为两臂共同改了价格时钟、完整组合及费用口径。这些共同变化不能归给资金费。

- 模型仍为 F10 171→256→256→1、GELU/dropout0.1，110,082 参数（含原 a）；不加层、特征或模型参数。生产 chain 的 alpha=0.1 固定，原 a 不进入服务链，须照报其梯度/更新状态；不能靠学习另一个仓位 EMA 增加自由度。
- 完整目标：冻结 D10 King 分数/legs/seats/RN8/合法成员，分别形成 kc、fc，经原 chain、`raw=.55kc+.45fc`、原 exec_reshape 和发布/HOLD规则。King 常量不回传。producer 的 h_kc/h_fc 和执行数量 q 是不同状态；partial fill 只改变 q，不再次乘进 producer EMA。
- 两臂损失均用 `L(u)=-mean(u)+0.25*ES5%(-u)`、原96训练锚（24 burn）、同样的窗口人口/尾部选择规则。A0 的 u 为 `1e4*(price_cash-fee_cash)/V0`；A1 为 `1e4*(price_cash-fee_cash+fund_cash)/V0`。carry 系数固定1，无系数搜索。加 carry 后 ES 尾部集合自然可变，另分解均值项与尾部项，不伪称总差等于线性 cash 梯度。
- numeraire 固定 V0=100000 USDT、GM=2，目标数量 `q*=GM*V0*w/P_dec`；只乘一次 GM，所有现金同除固定 V0，单位 NAV bps。原 canonical 动态 `gm*equity`、lot、min-notional、保护反馈在最终评价保留；此处固定名义是明示训练代理，差额不冒充 cash 真值。
- fill 系数沿前计划已冻结的十 atom 校准，A+1440+tau；`r1=.581006080491,r2=.252908573708`，first/later 各原校准分配；fill px=`P_dec*(1+sign(dq)*原signed slip)`，不能用 P(fill)。价格项已含 slip，fee 按 fill 名义，不能再收旧3.52。每个 atom 更新 q，未完成差额留到后续目标递推。代理不承诺原引擎会形成同样 fills。
- funding 取 checker 返回的唯一精确 ms 事件流；fund-before-same-time-fill；`fund_cash_e=-q(e-)*P(floor5m(e))*rate_e`。不能只枚举非零 fund_log；baseline q=0 的事件也进入导数。末端固定 B=A_last+4h，不能为了收后续 carry 延长标签。

## 3. 当前 fill 之前的现金不能简单删掉

连续120锚使用同一 θ：`q(e-;θ)=stopgrad(q_initial)+Σ_{fills t<e} Δq_t(θ)`。当前锚 k 的决策前事件，`∂cash_e/∂target_k=0`；若旧 q 来自锚 k−1 的网络预测，`∂cash_e/∂θ` 仍可能非零。入窗初始 q、h 从绑定 checkpoint/prefix 取得并 stopgrad；窗口内部的库存不得逐锚 detach。24 burn 不进统计目标，但它形成的库存对96训练锚现金保持计算图。这样既不能让当前目标回避已结算费用，也不能抹去先前可采取行动的责任。

必须单列合成反例：θ0 形成第一锚 q=2θ0，下一锚决策前付 r=.001、P=100；新 θ1 尚无 fill。cash=−.2θ0，正确 `(∂θ0,∂θ1)=(-.2,0)`；把事件删掉会得(0,0)，回溯给新仓会给 θ1 非零，两者都必须红。共享 θ 令 θ0=θ1=θ 时导数仍−.2。入窗 q=2θ 但 stopgrad 后导数0，是另一个正控。已有固定 tape FD 不覆盖这个网络因果反例。

## 4. 梯度代理的边界和检验次序

硬 rank 对连续 score 局部导数几乎处处为0，不能冒称硬生产排序可微。固定使用现有 pairwise sigmoid soft-rank，tau=.3，仅本次一步机制测量；不扫温度。硬模式使用生产1-based rank定义作 forward 平价控制（kc/fc/raw/weights/trade_mask）；软模式只作明示训练代理，有限差分检验软函数，不用 straight-through 的假有限差分。RN8、clip、死区、发布门保留原 piecewise 判定；若扰动跨门，分别标出，不把不光滑处报梯度错误；稳定区内未过门须停。发布门在每次前向由同一函数生成，不能为得到梯度挑发布锚/改阈值。

顺序与硬门：

1. 纯 CPU 合成时钟反例和全书硬 forward 平价。原 canonical tap 作为 cash 校准基准，代理与其差额按成交数量/固定名义/保护差异报告；同一数量 tape 时 cash 必须逐事件≤1e−8 USD，q 独立精确门通过。实际 consumer import 后断言 `__file__` 和 SHA；不沿用原进程缺失遥测。
2. 固定首 supported120，先算 price/fee/carry/总损失相对 θ 的梯度，报告范数、夹角、非零参数/锚人口、mean与ES分解、当前 target 与前锚 held 的偏导。梯度极小则报告量纲/数值可检测下限，不以经验比值门直接否定 F10-N。
3. 固定方向做中心有限差分；网络 eval/dropout固定掩码时验证，避开已标记的门跨越。float64小型控制 atol1e−10、rtol1e−6；真实 float32 directional FD 报 eps=1e−3/1e−4 两个预定尺度的误差与门变化，不挑其中好看的结果，未一致则参数梯度未验收。不能用 score FD 替网络 θ FD。
4. 从同初值、同 batch、同 RNG、同 optimizer空状态各一步 AdamW（lr3e−4,wd1e−4,clip1），不调参数。F=0 两臂 loss/梯度/参数/optimizer状态逐位相同；反号、错归当前 target、漏掉 baseline q=0、重复 cash 负控都要通过；共享 θ 的旧持仓反例必须过。输出一步前后分数/完整书目标差、price/fee/carry 分项；优化状态只存小型证据，不生成 OOS 候选。

## 5. 输入和隔离：先实施验证，再谈真实学习

首步固定当前已认证 Jan2023 窗，不因9次发布稀少改窗。当前共同输入来自 manifest `9a7de4e6…`、修后 checker `5f1ba04e…`、D10 features `ad80d50d…`、legs `37c0b5d3…`、King `6579bc4e…`、现金账 `76b777bf…`、raw price `23af32bd…`、members `3ee838cf…`。按120锚 mmap读取，不能落整份大特征。

最小一步实施验证在现存 D10 s42/202608 checkpoint 附近做，两臂克隆同一份。已只读定位 `/workspace/dlarch_2026-09-24/f10d10_2026-09-27/runs/d10/G1_T0_nomask/f10_s42/202608/model.pt`（445607字节，SHA `e8ed6a3eeed417a97826ac580422e0e57bd2e0c3c6fa4bd50484fd6b0257f97f`）；foldreceipt `11ca8e7d…`、原模型数110082。该模型训练输入是早期 D10 `f1cd3fa2…`，当前 ad80 是延长重建后的重打分来源，**不能把此一步命名“最新输入重新训练的候选”**；沿其既存 mu/sd 只测服务一致参数通路。模型只读，213 pins 不改，输出新根。

若此装置通过，真正单折 A0/A1 学习另从相同 seed42 的原 Net 初始化，mu/sd 仅在相同 D10 ad80 训练人口上流式计算；共同 King/legs/现金/原始价/合法成员与当前基线统一，保留 R_NC。沿202608原 train/admission：149条120锚窗、stride48、24 burn、96目标；原6条拒绝保留，再按共同OOF/状态支持域和执行时钟价可观测性预先排除，逐条列表冻结后训练，不能补别的窗。支持域排除不是信号负判。窗口边界固定，训练可消费的最晚经济时间不得越原 max_train_label_end=1765468800，更不得越 cutoff=1784678400、test_start=1785542400；旧数值由 receipt 钉，不单凭变量名。完整前缀可流式重建，不能无声明对每span清空状态。

首轮单折一 epoch 只验实现、可训练性与资源；不从单折 P/S、loss改善或现金决定 alpha。原始收益 Pearson/Spearman、CS rankIC、beta、σ比、偏置以及 clean/dense 即使报告也属描述，不继承收益判词。是否扩展须 lead 冻结多折/多种子与原完整32执行路径评价；同输入 A0/A1 及 NC/D10 参照均保留、UNKNOWN人口对齐。机制实验不自动获豁免项目既定多折/信号前置门。

## 6. 成本、真实阻塞与后续归因

现在优先级 KSR/D10。旧六窗尝试已 EXPIRED/NO_RESCHEDULE、optimizer=0，不设置新截止或等待器。新 CUDA 形状探针是独立资源工程，只有全零/固定合成张量、原 MLP 一次 forward/backward、无 optimizer；确切源码/预算先交 root 审，再允许执行。它不读 labels/targets，不能证明含 soft-rank/库存图的整轮训练内存上界。

CPU系数/合成控制：1核、2GiB、≤5分钟、预计首窗<60秒（参考目标11秒+cash10秒；梯度部分未实测）。既有原D10单epoch23–24秒；新单步预计数秒、含模型加载/控制≤2分钟；两臂一epoch粗估1–3 GPU分钟，端到端15分钟仅待评估，不是本轮预算延长。当前候选预算仍保守 RSS6GiB、GPU8GiB，启动 cgroup余量≥14GiB、同UIDRSS+6GiB≤30GiB、GPU空闲，严禁因“只差几十MB”绕门。CUDA探针和CPU/GPU分阶段能提供实测低峰值，但不将一次低峰值称硬上界；若无专属kernel限额，只能承诺监控终止并披露采样间隔及可能越限。

实际阻塞仅：完整输入/因果状态不闭合、forward或梯度控制失败、必须价格UNKNOWN、预算/空闲门失败、root未批准新运行。不再要求恢复不可得 old mirror，不需新全史下载。后续若有收益信号，可预注册简单线性动作或无条件缩放控制以拆辨“模型学会避费”与“只是总敞口变小”；当前不跑这些额外臂、不扫参数。

## 7. 独立 CUDA 形状探针：只交源码，待审后运行

源码 `multi_asset/exports/research/acting_lead_20260927/funding/funding_cuda_shape_probe.py`，SHA `2901bfa137448baa65e58e2409a15777381bae733025da3e77859dee38a28a7a`。guard/worker 同一文件，默认只打印提案。guard 创建全新目录，以绝对 `/workspace/venv/bin/python` 调同一文件的 `--worker`；源内没有旧六窗入口、动态 exec、torch.load、模拟器或 optimizer。只有一次固定 synthetic forward/backward；参数前后逐位相同必须断言。12个 stdlib 测试通过，未 import Torch、未启 GPU。

最大显式输入 `[120,829,171]` float32 = 68,044,320 bytes；每个 hidden activation `[120,829,256]` = 101,867,520 bytes，两个 hidden layer；output `[120,829]` = 397,920 bytes；weights/gradient 各440,328 bytes。GELU/dropout保存张量、反向临时workspace、CUDA上下文/allocator另计，**没有静态宣称峰值上界**。合成输入全零，seed42、dropout0.1，网络110082参数；一次 backward，不建 AdamW，不读取历史数据/标签/targets/model。只读取自身源码及本次 guard 命令元数据；`data_files_read=[]` 指没有领域数据。

独立申报 RSS3GiB，软件停止线2.5GiB，公共余量≥8GiB，启动须 cgroup余量≥11GiB、同UID RSS+3GiB≤30GiB，GPU无compute PID、util0、总已用≤64MiB。GPU预算8GiB，PyTorch allocator限7GiB为非allocator留空间；它不是总显存硬限。只监控 guard+本次子PID的RSS/HWM，50ms轮询；nvidia-smi 每500ms、查询超时1秒；他人GPU作业出现或公共余量不足就停本任务PGID。记录实际最大采样间隔，软件停止线可能被瞬时分配越过，不称 Linux RSS硬上限。worker默认 SIGALRM 指向同一60秒 deadline，guard只清理自己 PGID，最多额外2秒有界清理；不改任何cgroup、不清缓存、不干预KSR。

输出新根固定 `/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/cuda_shape_probe_20260927`；目录必须不存在，资源拒绝/失败也写终态且不在此root重试。写64KiB真实fsync quota probe，仅删除该任务自己的probe。源与测试目前仅本地，**没有发出下面的运行命令**：

```sh
/workspace/venv/bin/python -B /workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/funding_cuda_shape_probe.py --run
```

源码经 root 复核并单独授权后才上传/运行。观察成功仅给这个固定 MLP 的实测 CUDA/RSS峰值；不覆盖 soft-rank NxN图、120锚库存链、Adam状态或预处理，不能自动缩小真正两臂训练预算，也不恢复过期六窗实验。
