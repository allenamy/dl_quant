> **创建:** 2026-09-28 00:20 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** frozen-before-normalized-probe | **作废条件:** 公式、输入、变换、窗口或容差改变

# 修正自己代理遗漏的分数标准化

PREREG_first120_rank_action_diagnostic_2026-09-28.md 的原形测量完成：硬路径正仿射全不变；soft raw ×0.1/×1/×10 发布113/90/41锚。**这个尺度缺陷是root新代理的缺陷，不能借它解释已有T3失败或现役亏损。** 交叉读 `dlarch_train_f10.py:110–113` 发现原训练函数先做 `(score-mean)/(score.std()+1e-8)`；新clock core漏了这一步。

仅在新的独立副本补这一标准化，std沿原训练sample std；有限打分少于2个拒绝。温度仍0.3，1-based average rank仍向生产对齐，不改为原训练的0-based约定，不改alpha/band/FTRIM/gross门，不改原失败或成功收据。

原训练标准化有1e−8分母常数，因此尺度不变只能近似；预先要求四个固定正仿射变换的normalized-soft书误差≤1e−6且发布/原因相同。不满足就INVARIANCE_FAILED，不再换容差。硬路径仍逐项精确不变，观测器有/无输出精确，原continuous ≤1e−12。

测试先让旧proxy在“与原训练标准化后的soft rank值一致”及正尺度近似一致的受控输入上变红，再补公式；一次300秒追加资源预算（原6GiB RSS/8GiB GPU/14GiB启动/8GiB公共门不变），复用同120锚、同checkpoint、同四变换和crossed states。无optimizer、无收益读数；本件不把梯度原UNRESOLVED变PASS。新归档目录normalized_rank_action_20260928，与旧原形分开。
