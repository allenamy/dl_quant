> **创建:** 2026-08-22 03:4xZ | **Session:** 6737834a-WA | **状态:** WIP — 装置已落盘(`devices_2026-08-22/wide_full_caliber_audit.py`), jpline 数据层(1h 网格 829 名 / 资金费 828 名逐结算)已建成, 5m 对照臂构建中, `run` 阶段(全史记账/腿归因/在役同口径/触线)与本机 `shadow` 阶段(fapi 1h+fundingRate 独立重算 29 锚)在跑; 数字一律以结果 JSON 为准, 本文待填 | **作废条件:** 主线对宽书口径作出裁定后由新日期文件取代并互链; STATE.md §3 永远优先

# 宽书最深入独立口径审计(WA)· 原始 K 线 + 交易所资金费 + 影子真实权重 ⇒ 简单持有收益口径的宽书全史 / 影子前向 / 与在役同口径对比

**一句话(待填):** —

## 0. 白话三句(待填)

## 1. 装置、独立性、输入与收据

| 件 | 路径 | 说明 |
|---|---|---|
| 装置 | `devices_2026-08-22/wide_full_caliber_audit.py`(自 SHA 与输入 SHA 写入结果 JSON) | 阶段: `build1h`(829 名 1h 收盘网格 2021-01→2026-08-21, 原始月度 zip + 8 月逐日 zip)/ `build5m`(450 名 5m 收盘-收盘 与 Σ简单 5m 两个对照量)/ `funding`(829 名 fundingRate 月度 zip 逐币逐结算, s30 缓存 450 + 本装置补拉 379 名)/ `run`(全史记账 + 腿归因 + 情景 + 在役同口径 + 触线)/ `shadow`(本机, fapi 公共端点 1h K 线 + fundingRate, 影子存档权重 29 锚对账) |
| 补拉器 | `devices_2026-08-22/wa/jp_pull_funding_829.py` | data.binance.vision 月度 fundingRate zip, 仅 s30 缓存未覆盖名; 404 标记可续 |
| 附件 | `devices_2026-08-22/wa/wa_followup_capacity.py` | 最小名义额地板 / 退市名权重份额 / 参与率读数 |
| 结果 | `devices_2026-08-22/results/wide_full_caliber_audit_2026-08-22.json`(run + shadow 合并)| 本文所有数字出处 |

**独立路径声明**: 不 import/调用 `w2_wide_replay.py` / `w2b_common.py` / `wide_return_source_audit.py` / `pod_stop_arms*.py` / `engine.replay_fullhist` / `legs.py` 的任何函数; 收益/资金费/成本全部自算; 权重两路: (W-a) 读现有装置权重输出 `w2_wide_series.npz::{S0_W,d30_n2_c42_W}` 作输入; (W-b) 按 PREREG_wide_book_assembly §1 规格自建整条权重链(腿收益与止损价格路径用本装置 1h 简单收益), 与 W-a 的一致性只作收据。

**冻结定义/判读**: 见脚本头(持仓窗 (T,T+4h]; 价格 pnl = Σw·(C(T+4h)/C(T)−1); 资金费按真实结算时刻 f∈(T,T+4h] 作用于 w(T), 不 ×4/iv 平摊; 成本 c×Σ|Δw| 主臂 3.52, 敏感 {0.32, 4.137, 6.64, 1.75, 2.49}; 净@2 = 恒定 gross 2; 夏普 锚级 √2190 主 + 日聚合并报, CI 42 锚块自助; 触线 = 历史滚动 1 年窗 + 180 锚块自助; 三选一规则 = W-b d30 vs 在役 S1 同口径 配对块自助 ΔSharpe CI)。

## 2. A · 全史(待填)
## 3. B · 影子前向(待填)
## 4. C · 与在役同口径(待填)
## 5. D · 未闭合假设清单(待填)
## 6. E · 四问与三选一(待填)
## 7. 受据与关联(待填)
