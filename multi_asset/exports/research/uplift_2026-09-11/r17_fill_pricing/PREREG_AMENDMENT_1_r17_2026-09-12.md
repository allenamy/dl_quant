> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 r17)| **状态:** 冻结, 先于任何成交比例被看到 | **修订对象:** `PREREG_r17_fill_pricing_2026-09-12.md`(sha256 a7533b922c68e6dc575b1eadd3d19f62d4d271393ec5d58621c31aa65f5ae272)§2.3 最后一句

# AMENDMENT 1 · 账本里有离网锚运行, 「断言 |anchor_ts − E| < 3600」改为「剔除并计数」

**触发**: 装置 `r17_fillmodel.py` 首次运行在 (rebalance_id, symbol) 组 `anchor_ts = 1785565798.85`(2026-08-01 **06:29:58Z**)处断言失败: 最近的正典锚 08:00Z 距它 5402 s。这是账本里的一次**离网运行**(手工/重建锚, 不在 00/04/08/12/16/20Z 网格上), 不是在役锚执行。
**改动**: §2.3 的断言改为 —— `E = round(anchor_ts/14400)·14400; 若 |anchor_ts − E| ≥ 3600 ⇒ 该组标 OFFGRID, 剔除并计数(收据 `counts.offgrid_groups`)`。其余不变。
**为什么这是更严不是更松**: 离网运行的 qv4h 与 mid_next 都无法按 4h 锚对齐; 保留它们要么让 qvk 错位一格, 要么让 adv 的持有区间失真。剔除是唯一不引入错位的处理。计数使读者能看到剔了多少。
**数字标签**: 触发值为本轮实测 VERIFIED; 写本文时仍未看任何成交比例。
