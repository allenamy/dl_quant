> **创建:** 2026-09-27 18:36 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** final | **作废条件:** 本次源码或终态身份不一致；仅为固定合成MLP资源观测

# 独立 CUDA 形状探针：一次完成，optimizer 0

root 审 fd045e069 后授权一次，源 SHA2901bfa137448baa65e58e2409a15777381bae733025da3e77859dee38a28a7a 与 Pod 文件核同；12/12 stdlib 测试通过。为不预建输出目录，源码上传独立 `cuda_shape_probe_source_20260927`，guard 调同一精确源的 worker；输出固定 `cuda_shape_probe_20260927`。RUNNER_START/PID/COMMAND 记录命令与身份；没有旧六窗入口或重试。

18:34:23Z 门通过：cgroup free14,112,141,312B≥11GiB，UIDRSS17,868,304,384B+3GiB≤30GiB，GPU2MiB/util0、无compute PID。guard3524608；worker/PGID3524614。18:34:49Z OBSERVATION_COMPLETE，rc0、26.109秒；固定120×829×171全零float32输入、110082参数，一次forward/backward；参数逐位未变、optimizer更新0。

真实运行器 `/workspace/venv/bin/python` Python3.11.10、Torch2.11.0+cu128、CUDA12.8、RTX PRO4500 Blackwell。guard+worker各自HWM之和的观测峰1,388,814,336B（1.293GiB），进程GPU观测峰1,088,421,888B（1.014GiB）；Torch最大allocated702,179,328B、reserved708,837,376B。guard采样中最大间隔0.134915秒；RSS软件停止线2.5GiB、申报3GiB、公共8GiB、GPU8GiB、60秒均未触发。

这不是Linux RSS硬上界；HWM之和是保守观测且GPU进程占用和allocator不同。没有覆盖soft-rank NxN、120锚库存图、Adam、真实数据预处理。**不能自动缩小训练预算，不能重开旧六窗。** 新根终态 no_reschedule=true。本件不读labels/targets/model，不给任何经济或alpha判词。
