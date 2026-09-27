> **创建:** 2026-09-27 15:55:36 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** 读数后改抽样/损失/单位；输入SHA不符；同轴与价格/费率覆盖失败

# F10 漏计 carry 的 CPU 局部梯度探针（见数前冻结）

现役 news2_train_f10.py 原始 utility、WL 和损失逐字提取（不使用后来 mask-WL 的 T0），模型输入171维/OOF s42不变。经济量为训练utility归一化名义基准的bps（不含整书GM=2，不是NAV bps）：price=1e4 Σnew*y4s，turnover=3.52 Σsqrt((new-held)^2+1e-12)，carry=1e4 Σnew*F（正值是付款）。只比较 L0=−mean(price−turnover)+.25 ES5%(−price+turnover) 与 L1=相同但逐锚再减carry。F取现有T_NET里的(A,A+4h]实际settled rate和，不是RN8，不把未覆盖补0。F是旧P2秒级producer口径，非D10真值；结果只对此输入成立。

输入固定：NC s42 F10_OOF 2af48f7c84bfd5de2df83fa1266455ca718558a80ae68017de444b510a592d51；NC legs 9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65；T_NET 929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c；y4s ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62；existing combo diagnostic f4630a20f796bce26590aedeadfc28791be7eeecee8c14789f418b5a08de4388。绝对时间和symbol对齐，禁止行号假对齐。检查Tnet+F=y4s在有限标签上误差<=2e-15。

两个年代pre2026和2026各取4个120锚连续span：候选起点按全OOF行号每48锚网格；必须同OOF fold、全部ready且至少50个有限score、全部F covered、全span出现过的held名称逐锚price/F可测。只在eligible starts排序上用linspace到4个索引，不按收益挑选。与训练一样held从0开始、前24锚burn、后96锚计损失，tau=.3（原固定epoch7），alpha读该fold已有FOLD_RECEIPT末epoch值，score为现有eval-mode OOF。使用float32原utility，保留held递推计算图，单线程CPU。每spanΣn²>64million则RESOURCE_UNAVAILABLE，不改span长度或人口。无GPU，无训练，无新回测。预计RSS<2GB；本地stdout结果KB级，远端零写。

测量逐span的price/turn/carry、loss0/loss1、score梯度norm与cosine：carry相对price、相对turnover、L1−L0相对L0；并给alpha偏导。冻结同一span上直接权重目标梯度1e4F与−1e4y的demean norm比；正负carry方向分别列出。结果是已有分数附近完整120锚效用计算图的score/alpha导数，不是171维网络参数梯度、不证明可泛化、不作P/S有效性或部署判定。8个span仅描述离散分布；不伪造独立样本MDE或OOS置信区间。若需要参数空间可优化性，最小下一步是同初始化/同batch的两臂短训练。

控制：F=0时L与所有score/alpha梯度逐位同；F反号时线性carry与其梯度精确反号；常数同率F=1e-4因中性目标/held令carry及score梯度近0（float32误差限1e-5bps）；沿−carry score梯度作L2长度1e-4的有限差分，carry下降且导数相符（相对误差<=5%，若分段拐点不符只记不成立，不改步长）。同一既有combo权重按全部covered可测锚报告carry/price/换手描述，保持既有book与所有参数固定；不比较新候选收益。

解释门：数学漏项≠实质收益。若carry/price score梯度中位>=1%或carry/turnover中位>=10%，且控制通过，称“存在值得两臂验证的局部方向”，不是收益有效；若小于此门只说本次八span局部影响小，不否定F10-N尾部/新regime贡献。任何预期GPU成本按既有receipt实测外推，资源授权仍由主任务安排。

## 读数前修订（2026-09-27 16:00:32 UTC；原装置尚未启动、未见梯度数字）

按主审纠正上述绝对单位。旧T_NET仅作旧账恒等正控，不再用旧P2的经济结果判定训练推进。已找到D10延长毫秒账 `/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz` SHA `76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db`。现有构建收据明确对e179071d前缀逐事件/费率bitwise，末事件09-27 07Z，87962行新事件；九月API来源不是月归档双源。此次仍保留原T_NET covered和原抽样窗，不扩九月人口。以该账ft_ms严格 `A*1000 < ft_ms <= (A+14400)*1000` 对symbol逐一求和生成F_D10，不做interval归一化（实际现金费率不需要间隔推断），用它替代损失carry。原P2 F仅报告与真值同轴差异。额外冻结边界红控：落在A、A+1ms、A+4h、A+4h+1ms的已知事件必须只包含中间两笔；真实求和以独立逐事件逻辑抽查。任一来源SHA/事件排序/轴/边界门不闭合，则真实carry经济判断UNAVAILABLE，不退回旧P2。

## 读数后解释限定（2026-09-27 16:06:26 UTC）

首个D10梯度读数16:00:45–52Z已产生。主审指出执行钟漏洞：真实决策A+24m、5m价格网格填单A+25m，而朴素new(A)*F_ms(A,A+4h]会让新目标承担A+毫秒、它来不及避免的资金费。随后独立边界拆分证实差异几乎全是该边界归属；因此原JSON的LOCAL_DIRECTION_WORTH_TWO_ARM_TEST只保存为抽象utility图数学判词，经济判词明确UNAVAILABLE_TIMING_NOT_CLOSED，不据它启动训练。常量费率、F=0、反号、有限差分控制不能检验执行可达性。原16:00:32修订标时为撰写时间；工具读取clock实际为16:00:30，真实计算开始16:00:45，前后次序无歧义。
