> **创建:** 2026-09-28 00:08 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** frozen-before-new-measurements | **作废条件:** 下述输入、源码、变换、窗口或判据改变须留原件另行登记

# 首120锚硬排序与软代理动作差异：机制诊断

承接 RESULT_first120_network_clock_2026-09-28.md：相同 checkpoint 的硬映射发布30/120，固定温度0.3软代理发布90/120。这个数已经见过；本件是机制实验，不是假装未见数的收益检验。既有T3、F10_FULL及去band判负均保留。

## 冻结对象与问题

沿原Jan2023全120锚、202608 checkpoint、原μ/σ和20份输入SHA；固定scaled_diagnostic历史人口门，所有零初态和连续推进规则不变。仍是样本内工程检查；不计算收益、不新训练、不改现役代码，不使用本窗选择最赚钱温度。

假设：硬rank不随分数正仿射变换而变，固定温度软rank却受尺度影响；与资金费混合、FTRIM、cap、EMA/band和gross门随后使训练代理与实际动作不同。

1. 原样硬/软两条连续路径，逐锚捕获模型秩、与fund混合前后、FTRIM掩码、目标、band和发布；原数值函数以只读Python frame tracing观测，输出须与未装trace的原函数逐项精确相同。原硬路径另与已钉住continuous实现核≤1e−12，布尔/原因精确。
2. 固定四种变换：identity、分数×0.1、×10、+7；先验证float64有序关系与tie未变。硬路径应逐项相同；soft的+7允许1e−12浮点误差且发布应相同，乘法路径只描述动作变化。不是温度搜索、不能根据结果选一个因子训练。
3. 对每个锚固定相同当锚输入，交叉hard/soft × hard/soft上一锚状态四格。以soft沿hard历史为中间对象，把raw权重差精确拆成当锚映射差和继承状态差，必须逐格闭合≤1e−12；同时报另一排序的交叉格，不把此路径分解当唯一因果份额。
4. 记录float64分数std与rank幅度；报告全120锚，不只报发布锚。差异只解释本代理，不能归因已有T3全部失败。

## 工程验收与预算

新观测器先跑受控输入：trace有真实数值、移除trace应红；同输入有/无trace输出精确相同；原硬秩对同值ties正确，正尺度不变；soft平移不变、尺度会改变；源hash漂移拒绝。只读对象无写入。

一次最多300秒、CPU1、RSS预算6GiB/软件止5.5GiB、GPU8GiB；启动需cgroup余量14GiB、其它UID RSS+预算≤30GiB、GPU空闲；运行保留8GiB公共余量。沿既有guard，独立私有输出目录，registry登记；不覆盖旧实验。只做一次网络推理，其余无梯度；参数hash前后相同、optimizer=0。测试用Pod CPU，非本地锚窗重活。

判词仅 MECHANISM_MEASURED / UNAVAILABLE / INVARIANCE_FAILED。原双eps梯度门仍UNRESOLVED，无收益/候选/上线判词。若机制成立，下一步另立“硬动作一致、梯度为代理”的设计及多折整书门；不得据此直接用直通梯度宣称真导数已验。
