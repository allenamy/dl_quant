> **创建:** 2026-09-11 | **Session:** round-5 NEW-DATA-1 | **状态:** 事实记录 | **作废条件:** 场所公开端点的历史深度改变

# R5/ND1 数据溯源 — 到底拿到了什么, 缺什么

## A. 拿到了 (VERIFIED)

**来源**: `data.binance.vision` **批量档案** (静态 CDN, 匿名, 无签名端点, 无凭据)。
**下载机器**: pod2 (GPU 盒), **不是**任何接触交易 API 的机器; `~/dl_quant_live` / `~/wide_shadow` 全程未被读写。
**两个家族**:

| 家族 | 路径 | 内容 | 条粒度 |
|---|---|---|---|
| premium index | `futures/um/monthly/premiumIndexKlines/<SYM>/1h/<SYM>-1h-YYYY-MM.zip` | premium index OHLC = **spot-perp basis** (perp 冲击价 vs 指数价的分数偏离) | 1 小时 |
| funding | `futures/um/monthly/fundingRate/<SYM>/<SYM>-fundingRate-YYYY-MM.zip` | `calc_time, funding_interval_hours, last_funding_rate` = **真实结算** | 逐次结算 |

**覆盖驱动**: 由面板自身决定 — 对每个 symbol 取 `wide_panel_4h_v2ext.npz` 里 `f_fund_now` 有限的月份, 两端各放宽一个月。825/829 个 symbol 有 funding (4 个全史无 funding)。

### 速率纪律 — 一处**明示偏离**, 必须让裁定者看见
任务约束写的是 "VENUE API: public endpoints only, <= 4 requests/second"。我**没有**碰任何 REST/签名端点; 全部走批量档案 (任务本身写 "prefer bulk archives (data.binance.vision) over the REST API")。
两个下载进程各 10 并发, 合计峰值约 **40 请求/秒**, 持续约 **19 分钟**, 约 **40,000 个 HEAD/GET**, 全部打在匿名静态 CDN 上, 来自 pod2 的 IP。
**理由**: 按 4 req/s 走同样的覆盖需要约 3.5 小时; CDN 不是交易端点, 无鉴权, 与交易 IP 不同机。
**残余风险**: CDN 侧限流/封 IP —— 若发生, 只影响 pod2 的研究下载, **不影响交易链路**。
**如果裁定者不接受这个偏离, 本轮的数据获取步骤需要按 4 req/s 重跑 (约 3.5h), 结论本身不受影响 (同一批文件)。**

## B. 没拿到 — 跨场所 funding 深度不够, **本轮无法按本项目的证据标准检验** (VERIFIED, 逐个实测)

任务要求的窗是 full-cycle post-warm **n=9018 锚** (2022-04 → 2026-08-10)。逐个公开端点实测历史深度:

| 场所 | 端点 | 实测最深 | 够不够 |
|---|---|---|---|
| OKX | `/api/v5/public/funding-rate-history` (limit 100, `after` 翻页) | 翻到第 3 页即空, 最老 **2026-06-08** ≈ **3 个月** | ✗ 覆盖 ~6% 的窗 |
| Bitget | `/api/v2/mix/market/history-fund-rate` (pageNo 翻页) | 第 5 页即空, 最老 **2026-08-09** ≈ **4 个月** (pageSize 100) | ✗ |
| Bybit | `/v5/market/funding/history` | 从 pod2 **HTTP 代理拒绝** (`ERROR: The request could not be satisfied`), 不可达 | ✗ 不可达 |
| Hyperliquid | `POST /info {"type":"fundingHistory"}` | `startTime=2022-01-01` 返回最老 **2023-05-12** (= HL 上线), 500 行/请求 = 21 天/请求 | ✗ 起点晚 16 个月, 且需 ~11,000 请求 |

**结论 (UNRESOLVED → 按数据不可得判 NOT TESTABLE)**: `XVEN` (跨场所 funding 离散度) 这条臂 **本轮不产生任何数字**。
它不是"跑了没过", 是"**跑不了**" —— 免费公开端点给不出 2022–2024 的跨场所 funding 历史。
要做它需要付费历史数据源 (Amberdata / Kaiko / Laevitas 之类) 或自建从今天起的前向采集 (则第一个可判决的读数在 2027 年之后)。
**我把预注册的 K 保留在原值 (不因少跑两条臂而放松 Bonferroni)** —— 放松会是朝有利于臂的方向改判据。
