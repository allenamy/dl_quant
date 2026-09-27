> **创建:** 2026-09-27 15:45 UTC | **Session:** Codex acting-lead / research_resume_0927 | **状态:** final | **作废条件:** KSR 冻结判据 §3 或读数器/测试 SHA 改变；本说明不构成候选臂判词

# KSR 逐年回撤护栏转录修复

冻结基线 HEAD `3b4a2815ad4b8d45ee09ed8b69222e04b5885301`。`docs/DECISION_RULE_king_serving_refresh_2026-09-27.md` §3 原文是「H1 各年的 maxDD 均值不得比 S0 差 3 个百分点以上」。该文件只有原判据、红控移至 IC 层的修订 1、中间 IC 判词三次提交；没有把该护栏改为三年平均的修订。判据 SHA-256 `6cab2ac6cb420a7fcabf1e57896743285d0df52d9e2cca65e2a0fdb6281895d0`，本次不改判据。

原读数器先求每年路径×成员×种子的 maxDD 均值，再把三年平均后判 `> 3pp`。这允许单一年明显恶化被另外两年摊薄或抵消。原 source SHA-256 `3e1af1d4c10c2fa67884c77bc37aba7303a7dd00ca1a3f131c35a6bddec62bca`，2026-09-27 15:39Z 在 pod2 上核得同一 SHA。

修复只改变护栏的量词：各年独立计算差与 FAIL，`any(year.FAIL)` 触发总 FAIL 并沿原判词代码触发 BOOK.REJECT。三年均值继续报告，标为 `DESCRIPTIVE_ONLY_NOT_A_GATE`。缺任一 H1 年份时非零退出，打印 `KSR_BOOK UNAVAILABLE missing_H1_years=...`，不生成候选判词。净额统计、阈值、种子、输入、回撤复利 `cumprod(1+r)` 均保留。新 source SHA-256 `816d373458906f397f8b8e564feb67250f86a981d74e99b168162a9c20232118`。

专属测试 `test_ksr_book_drawdown.py` 执行实际读数器的回撤与判词代码，唯一替换是 `ser` 的数据边界，使用内存中 32 路径收益。没有读取 KSR 候选、真实收益序列或引擎。测试 SHA-256 `6450547137a44dfacfd753ac1214d7b12351c34daddb2aba61fc30332785d6b5`。

## 修前红 / 修后绿

- 单个 H1 年份基线 maxDD 10%、候选 14%，其他两年相同：逐年旋转三次，旧门均漏报，修复后全部 REJECT。
- 候选三年 maxDD 为 14% / 0% / 0%，基线都是 10%：旧门被其他年改善抵消，修复后 REJECT。
- 恒等、每年均低于 3pp、`r` 已是 NAV 收益而不额外乘 GM：绿控通过。
- 缺 2023、2024 或 2025 任一年：旧代码抛无语义的空数组 reduction 错误，新代码均为 UNAVAILABLE。
- 修前 6 个测试方法：4 个断言失败（含单年轮转的 3 个子测）、3 个缺年错误；修后 6/6 通过。原有拼接合成自测 7/7 通过；两文件 AST 解析与 `git diff --check` 通过。

复验：在本 worktree 执行 `python3 -B multi_asset/exports/research/dlarch_2026-09-24/devices/ksr_2026-09-27/test_ksr_book_drawdown.py`。设置 `KSR_BOOK_READER` 为原研究仓的同名文件，可复现旧门红控；测试不会写该文件。原红/绿运行日志保存在 `/Users/haosiyu/.codex/tmp/acting_lead_20260927/ksr_drawdown_{red,green}.log`。

## 验证范围与接续

未运行全仓训练/回放测试：本次变更仅是冻结判据的逐年量词转录，验证使用合成数据及相邻拼接装置自测；pod2 正在运行的 36 格未改、未重跑。没有读取未到停止点的候选结局，未做服务器部署。36 格全部 `KSR_DONE` 后，由 root 独立复核本修复，在新目录部署读数器，再运行终态 CPU 读数。BOOK 判词最高仍是整份 KSR 最终判词的一半，IC 及必报项须另行合并。
