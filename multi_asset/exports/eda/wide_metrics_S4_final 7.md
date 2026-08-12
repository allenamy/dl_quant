# 轨 2 — 宽宇宙衍生品数据面 (OI/持仓) S4 终报

> **创建:** 2026-07-13 04:30 JST | **Session:** fable multi-asset-v3 autonomous (0B build/batch) | **状态:** final | **作废条件:** 换 horizon / 8h-刷新 / regime-gate 用法重开时由后续实验取代
> 交叉引用: 判决文件 `exports/eda/wide_metrics_{ridge_gate,gbdt_probe}.{json,md}`; 里程碑 `docs/2026-07-12_ENGINE_A_FINAL_MILESTONE.md` §六; funding 式先验来源 `memory/ma_v2_funding_ema_GO.md` + `ma_v2_wide_universe_revival.md`

## 判决 (一句话)

**OI/持仓在 1h 尺度对 YR4 残差目标无增量 —— 线性 (Ridge) + 浅非线性 (LightGBM) 双门 FAIL，干净关闭。** "funding 式" 先验 (线性 null 但 DL 可学非线性交互) 被实测否定：交互 (reversal×crowding) 未救活信号。数据资产全绿保留备用。

---

## 一、S1 覆盖 (data.binance.vision futures/um/daily/metrics)

| 项 | 值 |
|---|---|
| 宇宙 | 140 USDT-perp (wide_dl_full.npz symbols, 含历史成员) |
| 日档总数 | **188,358** |
| 空币 | **0** |
| 覆盖到 2026-06-25+ | 126 币 |
| 真退市 (metrics 覆盖满 membership) | 13 币 |
| MATIC→POL 迁移 | 1 币 (2024-10-02, 真数据终点, 尾 9 天 NaN 掩码不补) |
| metrics 可用起点 | 多数 2021-12-01；最早 2020-09-01 (老币)；面板从 2021-01-01 → 2021 上半年多币无 OI (掩码处理) |
| 每档 | 288 行 5min 快照 × 8 列 |

**8 原始列:** sum_open_interest, sum_open_interest_value, count_toptrader_long_short_ratio (账户), sum_toptrader_long_short_ratio (仓位), count_long_short_ratio (全局账户), sum_taker_long_short_vol_ratio。create_time = 窗口末端 (首行 00:05, 日档覆盖 D 00:05→D+1 00:00)。

**13 真退市币** (metrics 终点 = 该币离开 USDT-perp 宇宙, 非截断):
AGIX 2025-10-11 · BAL 2025-06-05 · EOS 2026-05-05 · FLM 2026-02-25 · LISTA 2025-12-05 · MASK 2026-06-03 · MKR 2025-10-06 · OCEAN 2026-01-22 · OMG 2025-06-05 · OMNI 2026-01-23 · RNDR 2025-06-29 · WAVES 2024-07-13 · YFI 2026-04-04。

## 二、S2 通道 (wide_metrics_ch.npz, CH[48168,140,7] + 显式 MASK, 97MB)

**泄漏口径:** 小时格 t 只用 create_time ≤ **t − 5min** 的最后快照 (滞后一格, 比"≤t"更保守 —— 实盘 12:00 快照往往几秒~几分钟后才可查)。spot-check 验证: 面板 12:00 用 11:55 快照, 12:00 快照被正确排除。MASK ⊆ MEMBER110 (无非成员泄漏)。

| 通道 | 机制 | member 覆盖 |
|---|---|---|
| oi_level_norm | log(OI / 30d 滚动均) —— 拥挤度 (均值回复) | 0.884 |
| d_oi_1h | 1h OI log 变化 —— 建仓动量 | 0.886 |
| d_oi_24h | 24h OI log 变化 | 0.886 |
| doi_x_ret | d_oi_1h × sign(1h 收益) —— 新钱 vs 回补 | 0.886 |
| top_ls_ratio_z | 大户仓位 L/S 截面 z —— 聪明钱定位 | 0.747 |
| top_vs_global_divergence | 大户仓位 − 全局账户 L/S 截面 z —— 聪明钱 vs 散户背离 | 0.747 |
| taker_ratio_ema | taker 买卖量比 EMA(6h) 截面 z —— 主动买压 | 0.888 |

(top-trader/divergence 覆盖较低 = 截面 z 需 ≥10 成员 + 正比率。逐资产稳健归一 + 截面可比。)

**funding_mom 本轮不做** (面板已有 funding_ema=ch0 基线；funding 不在 metrics 文件, 需另拉 fundingRate；现 funding_factor_cache 只覆盖 14 mega-cap)。

## 三、S3 双门判决 (YR4 残差, 截面 rank-IC, 6-fold 扩张 walk-forward, CL4 非重叠 clean)

### 门 A — Ridge 线性 (厂规前置门)

| | 值 |
|---|---|
| baseline (32 通道) IC | 0.0234 |
| +7 metrics 全家 IC | 0.0242 |
| **dIC** | **+0.0007** (fold 符号不一致 [−0.0004,+0.0015,+0.0009,+0.0015,−0.0009,+0.0016]) |
| shuffle-null z | 3.42 (量级 tiny) |
| **判决** | **FAIL** (需 dIC≥+0.003 & 符号一致) |

逐通道 dIC: d_oi_1h +0.0007 (**唯一 fold 符号一致**, 但 <门槛) · oi_level_norm +0.0005 · top_ls_ratio_z +0.0006 · d_oi_24h +0.0004 · **doi_x_ret +0.0000 (线性下交互扁平)** · **top_vs_global_divergence −0.0012 (反伤)** · taker_ratio_ema −0.0000。

### 门 B — LightGBM 非线性探针 (复用 0C gbdt_probe 设计: 重正则/目标标准化/无早停/泄漏守卫)

| | 值 |
|---|---|
| baseline (32 通道) GBDT IC | **0.0310** (> Ridge 0.0234 → GBDT 确能从旧书挖非线性, **探针有检测力**) |
| +7 metrics 全家 GBDT IC | 0.0306 |
| **dIC** | **−0.0004** (fold 符号不一致) |
| metrics-block 时移 shuffle-null z | **0.34** (real dIC 与 null 无异) |
| 泄漏守卫 (打乱目标) IC | −0.0045 (CLEAN) |
| **判决** | **FAIL** |

**关键:** baseline GBDT (0.031) 显著高于 baseline Ridge (0.0234) —— 证明探针**有**捕捉非线性的能力；但把 7 通道加上去无增益 (dIC≈0, z 0.34)。两门一致 = 结论稳健。

**判决质量:** 泄漏守卫 clean + 经验 null 校准 (z 而非 IR-vs-0, 避 14-asset 偏差) + fold 符号 + clean 非重叠口径全套齐。

## 四、数据资产清单 (保留备用 —— 谁重开谁复用, 勿重采)

| 产物 | 路径 ($M/multi_asset/) | 说明 |
|---|---|---|
| 原始日档 (压缩, 有迹可循) | `exports/wide_metrics_raw/` | 188,358 档 + `_coverage_final.json` / `_repair_coverage.json` |
| 对齐通道 npz | `exports/wide_metrics_ch.npz` | CH[48168,140,7] + MASK, t−5min 口径 |
| 判决文件 | `exports/eda/wide_metrics_{ridge_gate,gbdt_probe}.{json,md}` | |
| 脚本 | `data/{download_wide_metrics,repair_cdn_enum,build_wide_metrics_channels,ridge_gate_wide_metrics,gbdt_probe_wide_metrics}.py` | 全部可复跑 |

**未测用法 (本轮只测 1h/YR4-残差/线性+浅非线性):**
- **换 horizon** —— OI 类是慢变量, 更长 horizon (4h/24h=YR24) 或短 (1h=YR1) 可能不同 (本轮只 YR4)。
- **8h funding 刷新** —— OI 在 funding settle 附近 (00/08/16 UTC) 或有事件驱动结构, 未做条件化。
- **regime-gate 用法** —— 高波动/挤仓 regime 下 OI 通道条件价值未测 (本轮无条件全样本)。
- **raw 序列 DL** —— 本轮是"工程通道 → 门"; 若某 horizon 有边际, 原始 5min OI 序列喂 DL 可能挖到工程通道抹掉的时序结构 (但当前 1h/YR4 双门 null → 优先级低)。

## 五、下载工程双地雷 (防重犯)

大规模档案拉取 (140 币 × ~1670 天 = 188K 档) 暴露两个**静默**失败模式：

1. **限流假 NO-DATA:** 主 pass 32 路并发打满 S3 后, 同线程的 listing 调用间歇超时/被拒 → 旧代码把失败**吞成空列表** → 24 币误报"无数据" (含 BNB/LINK/LTC/MATIC/TRX/XRP 等核心), 每个还空转 ~200s (退避×超时叠加)。**根因: 未区分 "HTTP 错误/超时" 与 "真 0 keys"。**
2. **分页静默截断:** listing 分页第 2 页失败 → 只拿到第 1 页 → 下载数 == listed 数, 看起来"完整"实则截断。UNIUSDT 只到 2023-04 (500 档, 应 1673 到 2026); BOME 同。**`files==listed` 检查抓不到 (两边都是截断值)。**

**对策 (CDN 枚举, 已固化):**
- S3 listing (s3.ap-northeast-1) 重负载后对本机**间歇不可达** (http=000 / 慢); 但 **CDN 下载主机 (data.binance.vision) 稳定** (404≈0.7s / 200≈0.9s)。→ **放弃 S3 listing 依赖**。
- 用面板 **MEMBER110 point-in-time 掩码**界定每币日期区间 (紧, 基本全 200 少 404), CDN GET-with-skip 补齐 + 显式 retry。
- 覆盖校验必须**重列/重扫全部 140 币** (不只补 0-档币), 才能抓分页截断; 判据用 `last_date vs member_end` (退市=覆盖满 membership, 截断=last < member_end)。

**方法论教训:** (a) 静默吞异常成空值 = 数据完整性头号杀手, 空结果必须区分 error vs 真空; (b) `files==listed` 不是完整性证明 (listing 本身可能截断); (c) 重负载后同源不同主机可用性可分叉 (CDN 活 / S3-listing 死), 备用路径要跨主机。

## 六、结论

轨 2 干净收官。OI/持仓数据面从零到 188K 档全绿覆盖, 7 通道 t−5min 泄漏安全, 线性+非线性双门一致 FAIL —— 在 1h/YR4-残差尺度对已加冕 DL 书 (Engine A xattn+lam_orth=0, 5yr +0.0835) **无正交增量**。数据资产保留供未来 horizon/8h/regime 用法复用。**不建议为本轮口径上 DL 臂。**
