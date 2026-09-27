> **创建:** 2026-09-27 19:01 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** frozen-before-pack；NETWORK_RUN_NOT_STARTED | **作废条件:** 固定窗、输入SHA/轴、归一化来源、读取合同或预算变化

# 首120真实D10输入小包

root授权准备与只读包构建，网络前向/反向/optimizer未授权。固定已核窗 A=1672531200、B=1674259200；features rows2190:2310、sparse rows299280:316800、17520×171 float32=11,983,680B。原始价固定行53327:59089、5762×829 float64=38,213,584B。输出Pod独立 first120_input_pack_20260927，禁止变窗口/用收益或发布率挑样本。

源在 funding/first120_input_pack_sources_20260927；PACK_CONTRACT钉worker/guard SHA。source-only现在无网络运行。特征 ad80、legs37c0、King/F10 OOF、ledger76b7、raw价23af、universe3ee8及原targets均沿此前完整identity/config闭包；原213文件只读。所有直接读取的文件先用1MiB流式SHA验证，再通过同一fd读指定slice，前后验证device/inode/size/mtime/ctime与路径仍同一文件。严格NPY magic/version/header/shape/dtype/布局/载荷大小；特征六成员必须ZIP_STORED且非加密，按local header边界读短slice；小型legs/mask原本DEFLATED，只允许其明确流式解压前缀+短slice，不将其伪称mmap。不把np.load(...,mmap_mode)当ZIP可映射。

所有轴/成员顺序独立断言：anchors、off int64与固定边界、每锚成员去重/范围、symbols、legs/F10/掩码/universe源同轴；保留合法成员与raw价NaN，不置0。复用修后checker唯一ms事件数据，保存包括q=0的事件，额外EVENT_INPUT_RECEIPT。状态：producer从原Jan1原点kc/fc=0，canonical q初始sealed为空；两状态分开。原9发布/111HOLD与targets/literal/scaled都保留，不生成新目标。

归一化沿冻结D10 s42/202608 model e8ed6a3e…，训练feature f1cd…、当前读取ad80，**不是重训**。仅CPU weights_only读取mu/sd/参数SHA，不执行网络。原训练μσ人口为tr1首85% ready pre-cutoff锚中tr1[::7]成员拼接再[::3]，mu=mean，sd=sample_std+1e−6；既定标准化是float32拼X82/X89、assert finite、clamp((X−mu)/sd,−5,5)。本包不重估、不将当前窗均值充当训练均值，不输出真实收益标签。

6个读取器控制先跑：stored/deflated短slice对原数组、两种负索引拒绝、Fortran拒绝、打开后源变异拒绝。域输入若不匹配立即失败，不换输入。每次加载block≤64MiB，预估整体包<64MiB；GPU0，CPU1、RSS申报2GiB/软件1.75GiB、共享余量8GiB、UID+预算≤30GiB，300秒原截止，资源拒绝/失败保留不重试。实际包和normalization只作后续网络装置输入。完整120网络新预算仍需root审，不能从先前MLP低峰自动缩6GiB训练预算；F0字节身份仍UNRESOLVED。

机械入口：把本sources目录复制到Pod funding根；核PACK_CONTRACT列明SHA后，用/workspace/venv/bin/python -B funding_first120_input_pack_guard.py。guard仅调用输入pack worker，不调用旧六窗、F0或任一网络训练入口。下一次网络前向/反向准备基于实际包byte形状、observability、mu/sd和初始状态清单重新审，不在本入口串接。
