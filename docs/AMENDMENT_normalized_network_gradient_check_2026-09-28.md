> **创建:** 2026-09-28 01:08 UTC | **Session:** codex-acting-lead-20260927 | **状态:** in-progress | **作废条件:** 固定输入/方向/双eps/资源门或源码改变

接续 `RESULT_first120_rank_action_2026-09-28.md`。新图修回旧训练器原有的分数标准化后，必须重新验证参数梯度；原raw图双eps未决不会自动升级。

本次明确分配一个300秒、CPU1/RSS6GiB/GPU8GiB、启动余量14GiB、运行公共余量8GiB的无optimizer尝试。输入仍是Jan2023首120锚与固定202608 checkpoint；24锚烧入不detach。属于样本内工程，不报告投资收益，不是修后重训。只改原数值core为已独立红绿验证的normalized版本及worker/guard配对输出路径。原随机Rademacher方向20260927、eps1e-3与1e-4、全部9分项、分支稳定门与误差容差保持不变；任何分支越界照报UNRESOLVED，不选eps、不改阈值。

依赖price控制/硬动作平价是这次图验收的前置，原已完成F0定位不重跑。原失败和原未决保留。私有路径 `.../funding/normalized_network_fd_20260928`，只在GPU空闲和既有资源门全部满足时运行，不起等待器，不隐式续期。
