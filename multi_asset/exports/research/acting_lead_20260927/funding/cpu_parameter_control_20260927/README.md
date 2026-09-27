> **创建:** 2026-09-27 18:49 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** partial；F0严格字节身份未闭合 | **作废条件:** 原执行源码/收据身份改变，或新独立证据定位F0哈希差异

# 双锚 CPU 控制：参数时钟通过，F0字节身份未闭合

预注册 b99ad8632，执行前两次修订14fac14d7/8007d41b3；最终worker SHA31fcb2f3…、guard2972247c…。修改都在数值读数之前：F=0两臂真实carry开关不同，但共同事件rate=0；硬forward仅签给定输入step。部署5项SHA核同，guard只运行一次。

18:46:45Z资源门free14,040,358,912B≥10GiB，同UIDRSS16,943,501,312B+2GiB≤30GiB。guard3526549、worker/PGID3526551；18:47:16Z终态rc0/COMPLETED，31.12秒，RSS/HWM和903,806,976B（0.842GiB），最大采样间隔0.098秒，未触1.75GiB软件线。真实Python3.11.10、Torch2.11.0+cu128，CUDA_VISIBLE_DEVICES为空且cuda_initialized=false，CPU1、纯合成。

root独立scalar oracle逐数复现：共享θ导数−1.46，baseline q=0仍−1.46，早现金对当前target导数0、对前target−.1，反号+1.46，重复结算被真正输入验证拒绝。原110082参数Net的两个合成171维样本（数量接口）在price/fee/carry/A0/A1五项×两个固定epsilon的10项方向FD全部通过，最大绝对误差1.46645e−10。它不包含生产排序/组合/真实数据。

独立Torch硬step对原combo_target.step共8格（2锚×2初始状态×2publication），1发布7HOLD，最大权重误差1.73473e−18；错误phi=.5经同一checker8/8拒绝。这只签给定输入step，不签连续evolve/HOLD执行库存协议，也不宣称硬rank对score可微。

**F=0不能签逐位PASS。** 原工具将torch.equal误标F0_bitwise；该比较给loss/gradient/params/Adam状态数值相同，但全对象哈希为d1260ef2…与8c6bd47b…，不同。signed-zero是可能原因，但当前没有逐字段字节证据；hash还包含未逐项比较的parts_before_NAV_bps。原张量未持久化，因此只读现存收据无法定位。POSTRUN_ACCEPTANCE_AUDIT明确降为PARTIAL_CONTROLS_PASS_F0_BYTE_IDENTITY_UNRESOLVED。原RESULT/ONE_STEP字节保留，不回写假PASS，不据此放行训练。

A0/A1各实际合成AdamW一步的最大参数差0.00059998868只证明不同目标能改变参数，不是收益，也不说明改善方向。另有F0两控制步；所有更新只在进程内，无候选模型保存。stdout/stderr（含float转换warning）全部保留；未重跑，no_reschedule=true。完整120网络链/整fold尚未授权。

时间勘误：预注册追加行手写18:47 UTC不准确；其真实修订时间是CPU_CONTRACT的18:44:58.473Z（commit14fac14d7同秒），逐事件rate修订18:46:05.282Z、commit8007d41b3在18:46:22Z；均先于18:46:45Z唯一数值运行。以这些机器时间为准，不用手写分钟证明冻结时序。
