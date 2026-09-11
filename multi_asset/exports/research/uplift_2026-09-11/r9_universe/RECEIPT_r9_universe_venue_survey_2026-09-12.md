> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX (subagent, class = INDEPENDENT UNIVERSE OR VENUE) | **状态:** 调研 + 两条一手量测; 无臂, 无判决, 无换装建议 | **作废条件:** jpline 恢复可达(HL 归档可读) / 买入付费跨场所历史 / 面板换文件
> **口径 PIN:** v4 chain 2026-09-09 (`CALIBER_PIN_v4_2026-09-11.md`)。**本文两条量测都不是书层 PnL, 是相关性与费率量级诊断 —— 不得换算成夏普**(反模式: `score_level_magnitude_is_not_book_level`)。
> **实盘零接触:** `~/dl_quant_live` / `~/wide_shadow` 全程只读, 未写、未重启、未下单。仅公开静态 CDN `data.binance.vision` 与 pod2 本地面板。
> **ENV 白名单 (E-0826-D):** 两个脚本 `r9_cohort_diag.py` / `r9_cm_probe.py` 的环境变量白名单 = **空集**; 均以 `env -i /usr/bin/python3` 运行(命令逐字见下), 脚本不读任何环境变量。
> **GPU:** 未用。pod2 `nvidia-smi` 当时 0 个 compute app / 2 MiB used ⇒ 未排队, 未抢占。

## 逐字复跑命令 (E-0826-D)

```
scp r9_cohort_diag.py pod2:/workspace/r9_cohort_diag.py
ssh pod2 "cd /workspace && env -i /usr/bin/python3 r9_cohort_diag.py"

scp r9_cm_probe.py    pod2:/workspace/r9_cm_probe.py
ssh pod2 "cd /workspace && timeout 900 env -i /usr/bin/python3 r9_cm_probe.py"
```

## 量测 1 — 代币化股票/商品能不能当"独立宇宙" (VERIFIED)

装置 `r9_cohort_diag.py`, 面板 `/workspace/data/wide_panel_4h_v3splice.npz`(v4 PIN 指定的导出面板, 前 1MB sha256 头 `5ad7469ec6c7b8d7`), 收据 `RECEIPT_r9_cohort_independence.json`。

| 读数 | 值 |
|---|---|
| 面板里的代币化股票名 | **23**(AAPL/AMZN/TSLA/NVDA/… USDT) |
| 面板里的商品名 | **3**(XAU/XAG/XPT USDT) |
| 加密名 | 803 |
| 股票组 ≥8 名的锚数 | **1067**, 窗 **2026-02-16 08:00Z → 2026-08-30 20:00Z** |
| **corr(股票组逐锚等权均收益, 加密组逐锚等权均收益)** | **+0.5992** |
| corr(商品组, 加密组) | +0.3392 |
| 资金费横截面 std 中位: 股票组 / 加密组 / 商品组 | **1.88e-4 / 4.95e-4 / 0.0** |
| 组内 fund→Y4 逐锚秩 IC 可算锚数: 股票组 / 加密组 | **1 / 1067** |

**读法(三条, 都指向否定):**
1. **"不同宇宙"不等于"不同下注"** —— 这批合约在加密交易时段、由加密资金交易, 组均收益对加密组均收益相关 **0.60**。市场层就已经不独立。
2. **燃料只有加密组的 38%**(资金费横截面离散度 1.88e-4 vs 4.95e-4), 商品组**恰好为 0**(XAU/XAG/XPT 的费率在横截面上没有分散度)⇒ 资金费动量机制在这里没有可排序的东西。
3. **样本量在算术上就判不了**: 1067 锚 ⇒ SE(年化夏普) = √(2190/1067) = **1.433**。即使真实夏普是 3.7, CI95 也是 [0.9, 6.5]。**这条轴不是"没测", 是"测不出"。**

## 量测 2 — COIN-M(币本位) vs USDT-M 资金费价差 (VERIFIED, 部分样本)

装置 `r9_cm_probe.py`, 源 = `data.binance.vision` 批量档案(静态 CDN, 匿名, 无签名端点, 无凭据), 从 **pod2** 发起(不是任何接触交易 API 的机器), **352 个请求**, 顺序 + 0.3s 间隔(≈3 req/s)。收据 `RECEIPT_r9_cm_um_funding_spread.json`。
归一规则逐字沿用 `multi_asset/exports/eda/PREREG_crossvenue_2026-08-09.md` §1: `per_hour_rate = last_funding_rate / funding_interval_hours`, interval **逐笔从档案第 2 列读**, 不用静态表。

16 个名(ADA APT AVAX BNB BTC DOGE ETH LINK LTC NEAR SOL SUI TRX UNI WLD XRP), 每名 **259–262** 笔**精确对齐**的结算, 窗 **2025-09-01 → 2026-06-27**:

| 读数 | 值 |
|---|---|
| mean(CM − UM) bps/小时 | 中位 **+0.0282**, 区间 +0.0062 … +0.1938, **16/16 名为正** |
| std(CM − UM) bps/小时 | 中位 **0.0962**(= 均值的 3.4 倍) |
| corr(CM 水平, UM 水平) | min 0.058 / **中位 0.484** / max 0.814 |
| **sign(价差) == sign(UM 水平) 的占比** | min 0.259 / **中位 0.340** / max 0.550 |
| 中位价差换算 | **+0.113 bps / 4h 锚**(单腿名义), 即 +0.676 bps/日 |

**读法:**
1. **价差真实存在且逐名同号**(16/16), 但**它的符号与 A0 交易的那个量(UM 资金费水平)只有 34% 的时候一致** ⇒ 这不是 A0 的重新加权。这是本轮调研里唯一一个一手量到的"低相关"证据。
2. **它是静态敞口, 不是预测。** 逐名恒正 + 与水平近乎无关 = 同 `SL_AGE50` 的形态(IC 谱在 k=−3..+3 平)。对本 program 而言这**不自动是死刑** —— 缺口要的正是"一条与现书零相关的独立来源", 风险溢价本来就可以是静态的。**但必须先分清它是溢价还是记账常数**(见下)。
3. **量级要按两腿摊**: 配对占用两条腿的 gross, 所以每单位**总** gross 的 carry ≈ **+0.056 bps/锚**, 是 A0 无条件 +0.6342 的 **8.9%** —— 且这是**毛价差**, 未扣任何成本、未扣反向合约 delta 再对冲的换手。

**档案深度 (VERIFIED, HEAD 请求)**: `futures/cm/monthly/fundingRate/` 下 **49 个 `*USD_PERP`** 符号(S3 列表)。`BTCUSD_PERP` 2023-01 = 200, **2022-01 = 404**; `SUIUSD_PERP` 2024-01 = 404 ⇒ **主流名约 2023-01 起, 新名更晚**, 覆盖不到本 program 要求的 2022-04 起的窗。

**装置自述的两个缺口(必须让裁定者看见):**
- `common` 是按 **calc_time 逐毫秒精确相交**取的, 只命中约 29% 的结算(259–262 / ~900)。两族结算时间戳有 ms 级偏移时该笔被丢弃。**这是无偏抽样但不是全样本**; 正式做要按最近邻(容差 ≤60s)对齐并重测。
- 窗只有 2025-09 → 2026-06(我只拉了 11 个月), **不跨 regime**。

## jpline 不可达 (VERIFIED, 2026-09-12, 两次)

`ssh jpline` 两次 `connect to host 212.50.244.62 port 31999: Operation timed out`。
⇒ `multi_asset/engine/hl_archive/` 从 2026-07-25 起每日 cron 落的 **HL 小时线 / funding / 名册 / L2 盘口**本轮**读不到**。
本机只有 `multi_asset/exports/eda/hl_funding_hourly.npz`(VERIFIED: 16,675 逐小时行 × 81 币, **2024-05-31 11:00Z → 2026-08-05 06:00Z**, 84.79% 有限值, `pulled_utc 2026-08-09`)。
**时间敏感**: HL `candleSnapshot` 是 5000 行 = 滚动 ~210 天硬顶(`hl_archive/README.md`)。若该 cron 已死, **2026-02-14 之前的 HL 小时线是永久性损失**, 且本轮无法核实它是死是活。这是本调研发现的唯一一条会随时间恶化的事项。
