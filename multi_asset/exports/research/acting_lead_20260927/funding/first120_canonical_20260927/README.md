> **创建:** 2026-09-27 18:18 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** final | **作废条件:** 原 tape/source/config SHA 改变，或发现未披露事件/初始状态；本件只签现金接口

# D10 首 120 锚：现金接口 PASS，9/120 发布、111 HOLD

固定 2023-01-01T00Z 至 2023-01-21T00Z、s42 模型来源、执行 seed0、NAV100000、GM2。窗口由原 admission 中完整 OOF/状态支持域的时间上首条决定，先于任何现金读数冻结（docs/PREREG_acting_funding_first120_2026-09-27.md）。原 2022-07 窗因 F10 未开始支持而 UNAVAILABLE 的收据保留。完整 King+F10+fund 原 combo、OVN adapter/loader 120 锚逐位回读通过；scaled 只发布 9 次，111 次 HOLD；literal 0 次发布。**现金 PASS 不签策略代表性或收益。**

原 HistSim31 加独立 exact-ms active-event 视图运行一次：5,225 笔 fill、659 条原 fund_log、9,104 个全部 ms 事件，其中 656 次非零库存的可达结算。原逐事件现金差 0，逐窗差最大 1.16e-14 USD；价格/费用/权益恒等误差分别 1.19e-11 / 3.81e-13 / 4.51e-10 USD。初始数量从 sim.sealed 导出为空，SHA 83c32f281cbbd950fb3e4a09ed14493535842e19d6baf76d27deb92509c9b714。

现金 tap 原源计算了 max quantity error=0，但没有独立 assert；原 `plus_one_cent_control_red` 只是算术式，不能作为红能力证据。保留原 RESULT.json 字节。随后纯读取 TAPE.json 的 funding_cash_tape_verify.py 从 sealed 数量和严格早于结算的实际成交重建 q，独立精确数量门、逐事件/逐窗现金门全通过，最大差均 0；把真实 fund_log 的 cash+0.01、quantity+1、初始库存变异喂同一 verify 均拒绝，额外零费率也不能掩盖数量差。没有重跑模拟器。Root 又用零 engine import 的独立读器复核并增加重复现金红控（收据由 root 另存）。

消费者 source SHA 与输入 contract 钉值一致。原进程未记录导入 module.__file__；18:17:28Z 按相同 sys.path 的只读 find_spec 解析到该精确文件/同 SHA，见 POSTRUN_IMPORT_RESOLUTION.json。这是事后解析证据，不补称原进程遥测。下次新装置必须在实际 import 后断言 resolved __file__/SHA。

一个固定 fill 的局部现金 FD：1000SHIBUSDT、1674145458.759 秒，fill 前 1674144000012ms 的现金由旧 q=-155871 承担，新 fill 偏导 0；之后三结算导数 -3.4402539366e-6 USD/qty，FD -3.4402541926e-6。**固定 tape FD 不代表共享网络 θ 的端到端梯度。** 在连续网络递推中，当前 fill 前 held 若来自前锚 θ，仍应对 θ 保留梯度。

目标构建 11.00 秒/RSS337.30MiB，现金 tap 10.25 秒/RSS100.64MiB，CPU1、RLIMIT_AS2GiB、CPU240/250秒、外层 wall300秒，均过 cgroup≥预算+8GiB、同 UID RSS+预算≤30GiB 和真实 quota probe；无 GPU。原 raw 价格块 float64 实际 38,213,584 字节（36.44MiB）。执行命令及三个精确源码副本在 EXECUTION_ARCHIVE.json / executed_sources；原 stdout/stderr 在上级目录。新 D10 毫秒账消费成功不证明旧 seconds 引擎有现金损坏。
