> **创建:** 2026-09-27 17:43 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** 输入/源码/运行时改变；本文没有新运行授权，原900秒预算及NO_RESCHEDULE永久保留

# 六窗实现夹具的内存工程提案

原尝试已由30e2a9625封账：只启动一次，torch2.4.1不支持当前GPU，成功forward=0、optimizer step=0。本文是独立资源设计，不修订原尝试身份，不建立新deadline，不启动CUDA、模拟器或训练。原现金核验与统计控制不减项。关联研究合同见`PREREG_acting_funding_network_fixture_2026-09-27.md`，完整fold另见`PLAN_acting_funding_fold_clock_2026-09-27.md`。

## 已测量与尚未测量

原guard采样峰1,020,203,008 bytes（0.950GiB），发生于错误torch版本、首个有效CUDA张量之前；它不是正确torch2.11完整训练的内存上界。原子进程源码来自6c1f9e8f3，fixture SHA `97fd21afcd7f06dcacb787ebc1d91cd4558de05b40554dbfbf47d5cc904a9479`，guard SHA `18ca32bf9daafd21a156bd0394c8101dadd3f1d645143d304bc18d1a143fe449`，不能拿后改源码替换原身份。

本提案阅读的当前fixture SHA `5bd1b02486d33a3dd969c7e03c8cdf3b0ab7e6b3ae4742381a843950396187d7`、关闭guard SHA `946b4dbabbd44ab07faf81fc8417393c792b3fbd2b3e4cd9475880fd174fd632`。本次只有17:40:59Z的只读ZIP/NPY头和六对offset读取，没有再执行数组、模型或模拟器。六锚索引10189–10194，每锚恰400行，2400行171维float32恰1,641,600 bytes。完整X82/X89文件成员分别913,727,440与991,728,552 bytes，必须只读映射切片，不解压/复制全表。

| 显式载荷 | 大小或严格形状上界 | 含义 |
|---|---:|---|
| rolling原float16 data | 133,701,120 bytes | NPY头另128 bytes，11520×829×7 |
| 当前Panel显式数组保守和 | 601,661,800 bytes | 原data、六个double网格及finite mask；非所有Python/RSS上界 |
| 六锚特征 | 1,641,600 bytes | 6×400×171×4；实际offset核验 |
| CP、CF、CW | 709,920 bytes | 3×6×4930×8；筛选后不会增大 |
| 六锚成员索引 | 19,200 bytes | 6×400×8 |
| 六锚完整权重 | 19,896 bytes | 6×829×4 |
| Net参数 | 110,082个 | 单份float32参数440,328 bytes |
| 一套参数/梯度/Adam m/v | 1,761,312 bytes | 标量step和容器另计 |
| 单个隐藏层输出 | 2,457,600 bytes | 2400×256×4；不等于autograd全图 |

Torch2.11导入、CUDA宿主驱动、cuBLAS、autograd保存张量、Python对象及allocator碎片仍未测全程峰值。不能把上表相加后宣称3GiB已证明。旧torch失败阶段的实测只能说明6GiB相对已观察载荷有较大余量，不能直接用它降低启动门。

## 可实施的缩峰方式

保留同六窗、同模型、同随机数、同两臂与全部正负控，只改变进程生命周期：

1. 新的CPU预处理子进程不导入torch。复用当前canonical只读Panel/FundingBook和固定tape，输出完整事件现金闭合、CP/CF/CW及六行块特征/成员/legs必要列。所有输入仍按原SHA验证；沿用1819个事件，不能回退fund_log子集。输出字段固定dtype、shape，包上限64MiB，禁止object dtype。现金不闭合即结束，不进入GPU。
2. CPU进程退出并确认回收后，才启动`/workspace/venv/bin/python` GPU子进程。它只打开小包与NC checkpoint、AST Net源码，核SHA及尺寸；不再创建Mirror/Panel，不持有整份legs或任一完整特征数组。用原检查点mu/sd及NC预测作参照，再按原随机初始化做网络控制；禁止把此前参数未运行的控制写作已通过。
3. 控制计算后及时释放已完成的autograd图和F=0副本；保留必要梯度数值、A0/A1权重和optimizer状态供逐位比较。不能以减少比较字段降低开销。CPU与GPU阶段顺序运行，最大RSS取两阶段峰值而非同时叠加；监控进程和其小缓冲也计入总预算。

预计静态小包低于8MiB，64MiB只是拒绝上限。CPU阶段此前实测约2秒、CUDA阶段尚无兼容环境实测；提议新资源验证最多60秒、之后原形状实现夹具仍最多15分钟，均需主审另授权及新根，不能从此文自动发起。原网络实验身份与NO_RESCHEDULE不动。

## 3GiB只是待证明的申报候选

候选预算为整任务RSS≤3GiB、GPU≤8GiB、CPU1；只有验证通过且主审采纳后，启动余量才可由14GiB改为11GiB（3+8），同UID RSS+3GiB仍≤30GiB，GPU仍空闲，真实输出quota仍须probe。没有证明时沿原6GiB/14GiB门等待，不把余量差几十MB当豁免。

当前只读cgroup收据显示namespace根可写、controllers包含memory，但subtree_control为空；没有已证明可用的私有memory controller。可写不代表已获准启用共享父级controller。不得改父级memory.max/high、清page cache、驱逐共享映射或处理KSR/D10进程。

真正的硬限首选已有授权的独立、已委派memory cgroup：仅在其父级memory已启用时建立本任务子组，令worker预算为3GiB减64MiB监控预留，禁swap，仅放本任务worker；CPU退出后同组运行GPU。记录memory.max/current/peak/events，单组OOM只损本任务。若不存在这种已委派接口，返回HARD_CAP_UNAVAILABLE，不能自行启用共享父级、不能把RLIMIT_RSS说成Linux有效硬限，也不能给CUDA用RLIMIT_AS伪装RSS限。

补充用户态保护可以每50ms读取本任务进程树VmRSS及VmHWM，在2.5GiB软阈值停止自己的PGID，并始终记录ru_maxrss。它可快速中止并事后识别超限，但采样存在短暂越界，**单靠它不证明3GiB硬上限**。CUDA的per_process_memory_fraction只约束Torch allocator；NVML进程显存仍需独立8GiB门，不能将两者混同。

批准资源验证后的通过谓词为：同源小包数学控制不变；实际环境是已记录torch2.11/cu128；故意超限的专属无模型子进程被本任务私有限额阻止；共享父级设置前后相同且无共享任务被触及；正确CUDA环境经历forward/backward和AdamW state建立，全程task峰≤3GiB、GPU峰≤8GiB、无OOM且保留8GiB公共余量。若无可委派cgroup，则硬限证明不能完成，维持6GiB申报；不能仅凭一次低峰值替代机械限额。

## 不随资源方案改变的研究门

F=0参数及optimizer逐位相同、fill前carry梯度0、不可达整点费错配给new报红、完整事件carry的独立有限差分、price/fee/carry同钟全部保留。六窗优化仍只证明实现，不输出OOS/候选结论；当前固定fill是局部线性化，不能声称新网络在canonical会形成同成交。未来正确共同D10输入及完整书评价继续另行排期。
