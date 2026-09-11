# RESULT · r9 独立性筛选 · OPTIONS_IV_SURFACE — **DEAD**

> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **分支:** research/book-uplift-2026-09-11 | **状态:** 判决已下 = DEAD, 两条独立死因, 均本轮一手实测 | **作废条件:** `data/option/daily/EOHSummary/` 出现 100+ 新标的前缀 **且** 该前缀恢复更新(今日已停更 1054 天)
> **口径锁:** `CALIBER_PIN_v4_2026-09-11.md`(v4 链 2026-09-09)。本轮**未跑任何装置**, 故口径锁只用于"若要建臂需落在哪个窗"的判定。
> **E-0826-D env 白名单: 空集 (EMPTY SET)。** 本轮全部命令为只读 `curl` 前缀列举 / `cat` / `grep` / `find` / 无环境变量的 `python3` 算术。未设任何环境变量, 未跑 `w10_universe.py` / `w10_sleeve.py` / `judge_v4.py`, 未启 GPU 作业, `~/dl_quant_live` 与 `~/wide_shadow` 只读(仅 `cat syms450.txt`)。未调用任何交易所 API(见 §7 对 Deribit 的处理)。

---

## 0. 一句话

候选**如其定义**(IV 曲面: 隐含波动率 + 偏斜 + 期限结构)所依赖的唯一数据集 `EOHSummary` **不是"从 2023-05-18 至今"**, 它**停在 2023-10-23**, 与判官的**六个窗口全部零重叠**;
唯一有实盘长度覆盖的期权派生序列是 **2 条标量指数**(BVOLIndex), 它没有截面维度、不在 450 名可交易集合内, 只能作为 gross 乘子进入书, 而 gross 乘子对 A0 的 rho **按代数恒等式 ≥ 0.89**(可部署档位 0.970), 比 XIB_LAG50 的 0.889 还差 —— **是再加权, 不是第二个赌注**。

**判决: DEAD。** 两条死因彼此独立, 任一条单独成立即可杀。

---

## 1. STEP 1 · 可行性 —— 调研员的数据主张有一半是错的

调研员(`r9_indep_source/RECEIPT_r9_independent_source_survey_2026-09-12.json` V1)只列了**首个 key**, 没查**末个 key**, 于是写成 "starting 2023-05-18, missing the first 16 months of the full-cycle window" —— 这句话读起来是"从 2023-05-18 跑到今天, 只缺开头"。**不是。**

### 1.1 本轮一手复核(全部 VERIFIED, 原始 XML 见 `raw_listings/`)

| # | 事实 | 值 | 标签 |
|---|---|---|---|
| M1 | `data/option/` 的子前缀 | **只有 `daily/`**; `data/option/monthly/` 返回空 `ListBucketResult`(无 key 无 CommonPrefix) | VERIFIED |
| M2 | `data/option/daily/` 的子前缀 | 恰好 2 个: `BVOLIndex/`, `EOHSummary/`; `IsTruncated=false` | VERIFIED |
| M3 | `EOHSummary/` 标的 | 恰好 5 个: BNBUSDT BTCUSDT DOGEUSDT ETHUSDT XRPUSDT; `IsTruncated=false` ⇒ 列举完整 | VERIFIED |
| M4 | `BVOLIndex/` 标的 | 恰好 2 个: BTCBVOLUSDT ETHBVOLUSDT | VERIFIED |
| **M5** | **`EOHSummary` 的末个 key(调研员未查)** | **停在 2023-10-23**。逐标的 zip 天数 / 首末: BTC **147** (05-18..10-23) · ETH **147** (05-18..10-23) · BNB **121** (05-18..10-23) · XRP **99** (05-19..10-20) · DOGE **31** (08-30..10-20) | **VERIFIED** |
| M6 | `BVOLIndex` 的覆盖 | 2023-06-20 .. **2026-09-10**, 两个标的各 **1153** zip 天 / 1179 日历天(缺 26 天) | VERIFIED |
| M7 | 450 名可交易集合内是否有波动率指数 | `~/wide_shadow/syms450.txt` 共 **450** 名, 匹配 `BVOL|OPT` 的 **0 个** | VERIFIED |
| M8 | 5 个期权标的是否在 450 名内 | 5/5 全在 ⇒ 截面覆盖率**恰好 5/450 = 1.11%** | VERIFIED |
| M9 | **E-0825-H 陷阱规避** | 本仓确实出现过 token `BVOL`(`runpod_scripts/workspace_mirror/pod_kingslot.py:12`), 但它是 `PW["f_vol_7d"][:, BTC_P]` = **已实现 7 日波动率**, **不是隐含波动率**。不得据文件内的这个名字推断"书已经用了 IV" | VERIFIED |

### 1.2 决定性的那张表 —— EOHSummary 与判官六窗的重叠

判官窗口逐字取自 `CALIBER_PIN_v4_2026-09-11.md` §3。锚轴 = `meta_newprod_v4.npz` E_ts, 2022-01-08 00:00Z .. 2026-08-31 20:00Z, 6 锚/日;
自洽校验: (2026-08-31 − 2022-01-08) 含端点 = **1697 日 × 6 = 10182**, 与口径锁登记的轴长 **10182 逐位相符**(VERIFIED 算术, 轴长本身为 INFERRED, 未本机读 npz)。

| 判官窗 | EOHSummary 重叠(日) | BVOLIndex 重叠(日) |
|---|---|---|
| frozen 2025-03-01 .. 2026-08-10 20Z | **0** | 528 |
| 2024-01-01 .. 2026-08-10 20Z | **0** | 953 |
| ext 2026-08-11 .. 2026-08-30 20Z | **0** | 20 |
| 2026-01-01 .. 2026-08-31 20Z | **0** | 243 |
| EXTENDED 2025-03-01 .. 2026-08-31 20Z | **0** | 549 |
| 2024-01-01 .. 2026-08-31 20Z | **0** | 974 |

**六个窗全部为 0。** 不存在任何一个判官能评它的窗口。后热身轴(丢前 900 锚 ⇒ 起点 2022-06-07, 余 **9282** 锚)里, EOHSummary 最好的标的只覆盖 147 日 × 6 = **882 锚 = 9.50%**, 且全部落在 2023-05..10 —— 即**全部落在冻结窗之前**。

⇒ **截面形态(IV / skew / term structure 逐名)在 STEP 1 即死。** 两重: 覆盖 5/450, 且在任何可判窗内**无数据**。
⇒ 附带纠正一条: 该数据集**已停更 1054 天(2.89 年)**。哪怕明天上市 100 个山寨期权, 判官窗内仍将多年无历史。

### 1.3 泄漏检查(为完整性做, 虽然已死)

调研员称 "end-of-hour snapshots embargo cleanly to 4h anchors" —— 这一条**技术上成立**(整点快照 ≤ 锚时刻, 无前视), 但**无关紧要**, 因为没有可用样本。本轮**未**触碰 `panel_source.py` 默认脏面板, **未**施 expm1 于 pod 5m 谱系, **未**用任何 `_ext` 谱系 —— 因为**未建任何特征**。stride<horizon 不适用。

---

## 2. STEP 2 · 主筛选 rho-to-A0 —— 唯一有数据的形态按代数恒等式就是再加权

截面形态无法建序列 ⇒ **rho = NOT_REACHED(不可建, 非未测)**。
剩下的只有聚合形态: BVOLIndex 的 2 条标量指数。对它必须诚实地走完筛选, 因为它**没有**被覆盖率杀死(75.57% 后热身轴, 冻结窗内 528 天)。

**它只能以一种方式进书。** 每锚一个标量 ⇒ 截面方差为零 ⇒ 无法给 450 名排序(M8 说 5 名有逐名 IV, 但那 5 名的数据已死);
且该指数**不在 450 名可交易集合内**(M7) ⇒ 不能作为持仓腿。
于是唯一形态是 **gross / 暴露乘子**: `g_cand,t = w_t · g_A0,t`, `w_t ≥ 0` 且 t 时可测。

**恒等式。** A0 逐锚 mean 0.6342 bps 对 sd 22.986 bps(由 mean 与年化 Sharpe 1.2912、2190 锚/年反解, VERIFIED 算术), 零均值近似很紧。于是对与 g 近似独立的 w:

```
rho(w·g, g) = E[w]/sqrt(E[w²]) = 1 / sqrt(1 + CV(w)²)
```

数值复核(n=9138, `numpy.default_rng([20260905, 9])`, lognormal w, 均值 1):

| CV(w) | rho 模拟 | rho 理论 |
|---|---|---|
| 0.10 | 0.9951 | 0.9950 |
| **0.25**(可部署档) | **0.9709** | 0.9701 |
| 0.50(激进) | 0.8985 | 0.8944 |
| 1.00 | 0.7187 | 0.7071 |
| 2.00 | 0.4635 | 0.4472 |
| **3.18**(筛线所需) | **0.2899** | 0.3000 |

**要把 rho 压到筛线 0.30 以下, 需要 CV(w) > 3.18** —— 即 gross 乘子的标准差是其均值的 3.18 倍。在 gross 封顶 2.0×NAV、w ≥ 0 的约束下**不可部署**(那意味着书几乎永远空仓、偶尔巨额)。现实档位 CV ≈ 0.25 给出 **rho = 0.970**。

⇒ **rho to A0 ≥ 0.89, 可部署档 0.970。比 XIB_LAG50 的 0.889 更差。按本纲领的主筛选, DEAD, 与其 Sharpe 无关。**

### 2.1 A0 亏损格内的条件 rho —— 这里**不需要**测, 它是代数

AMI 的教训是"无条件独立、在 A0 亏损格里 rho 反升到 +0.343/+0.438"。对本候选, 同一个陷阱**不可能被漏掉**, 因为 `rho = 1/sqrt(1+CV²)` 是**逐观测恒等式**, 在**任意条件子集**内同样成立(只要该子集内 w 的 CV 不爆炸)。所以:

**A0 亏损格内的条件 rho 同样 ≥ 0.89 —— 独立性不是"在坏状态蒸发", 而是**从来不存在**。** 标签: VERIFIED(代数 + 模拟), 非 INFERRED。

### 2.2 更糟: 已测的样本外符号是**反的**

`DOCKET_r7_ship_2026-09-12.md` **L354**(本轮逐行打开核对, VERIFIED 行号与原文): 任何择时 / 暴露控制 / de-risk 家族**已被 396 个 walk-forward 变体否决**, 样本内选择在样本外**反预测**(corr **−0.171** de-risk / **−0.275** up-lever; 300 变体 de-risk 家族 OOS 均 dSharpe −0.0502, 单边 95% 上界 −0.0398)。
把这个实测的 −0.171 代进上面的模拟, 该 overlay 臂的**独立 Sharpe 为负**: CV=0.25 ⇒ **−0.7669**; CV=0.50 ⇒ **−2.0662**(VERIFIED 模拟, 同一 rng)。

⇒ 聚合形态是**已关闭轴**上的又一个变体。收据: DOCKET L354。

---

## 3. STEP 3 · 独立边际 —— **NOT_REACHED**

主筛选未过(rho 0.89–0.97 ≫ 0.30), 按纲领在此停手。未跑 turnover-matched nulls(`r3_attack_RESID_SHARPE/null.py`), 未计成本, 未跑自举 —— 因为**没有可评的臂**。

---

## 4. STEP 4 · 算术: 这东西能把桌子推多远(不向自己方向取整)

`S_comb = sqrt((S1² + S2² − 2ρ·S1·S2)/(1 − ρ²))`。post-warm 口径 A0 S1 = **1.4150**(见 §5 口径纠正)。

| 配置 | rho | S2 | 合成 Sharpe | 增量 | 距 3.966 还差 |
|---|---|---|---|---|---|
| BVOL overlay, 可部署 CV=0.25 | 0.970 | 1.4150 | 1.4257 | **+0.0107** | **2.5403** |
| BVOL overlay, 激进 CV=0.50 | 0.894 | 1.4150 | 1.4539 | **+0.0389** | **2.5121** |
| 假想: 刚好过筛线, A0 质量 | 0.300 | 1.4150 | 1.7551 | +0.3401 | 2.2109 |
| **桌子真正需要的** | 0.000 | **3.7050** | 3.9660 | +2.5510 | 0.000 |

**最慷慨的配置下, 本候选填掉缺口的 1.5%**(0.0389 / 2.5510), 而产生这 1.5% 的那个配置正是**被 396 变体否决、且实测符号为负**的择时 overlay。可部署档只填 **0.4%**。

另: 以 A0 质量的**互不相关**书计, 补齐缺口需 **6.86 本**(post-warm 口径)。

---

## 5. 顺手查出的三处口径/路径问题(交回上游, 本轮未依赖)

1. **任务简报混了三个 A0 口径。** 本机读 `r5_newdata3/A0_headline_check.json`(VERIFIED): `FULL_all` s42 = **1.2947** (n=9139) / s2027 = **1.3332**; `FULL_pw`(= 丢前 900, 即约束 4 指定的口径) s42 = **1.4150** (n=9018) / s2027 = **1.4370**。
   简报的 **"3.705"** 只能由 **1.4150** 反解(sqrt(3.966²−1.4150²)=3.7050); 简报的 **"~7.9 本书"** 只能由 **1.3332** 反解((3.7352/1.3332)²=7.85); 而简报表头写的是 **1.2912**。三个不同的 A0。
   **按约束 4(post-warm), 正确的一对是 S2 = 3.7050 与 6.86 本。** 建议上游统一。
2. **约束 4 的成本模型路径是坏的。** `.../uplift_2026-09-11/r3k/costb_PWR_G230k.json` **不存在**; 实际在 `.../uplift_2026-09-11/r3k_impact/costb_PWR_G230k.json`(VERIFIED `find`)。该 JSON 内**没有** `K=0.17` 或 `alpha=0.87` 字段, 它装的是分层 maker/taker bps、`impact_bps_by_tier`、`book_avg_bps_per_unit_turnover = 2.9537`, model = "POWER-shape book-walk impact, excess of half-spread, G=$230000", 标定源 `r3k_fitK3.py`。简报里的 K/alpha 属 **INFERRED**(本轮未打开 `r3k_fitK3.py` 核实)。本轮未用到成本模型(无臂可计)。
3. **约束 5 的 nulls 路径是坏的。** `.../r3_attack_b9646/` **不存在**(VERIFIED `ls`); `null.py` 在 `.../r3_attack_RESID_SHARPE/null.py`。本轮未用到。

---

## 6. 重开条件(一分钟复查, 不是一个项目)

两条**同时**满足才值得重开截面形态:
1. `data/option/daily/EOHSummary/` 下出现 **100+ 新标的前缀**;
2. 该前缀**恢复更新**(今日末个 key = 2023-10-23, 已停 1054 天), 且新历史累积到能落进某个判官窗。

复查命令(逐字, 只读前缀列举, 零下载):
```
curl -s "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/option/daily/EOHSummary/" \
  | grep -o '<Prefix>data/option/daily/EOHSummary/[^<]*</Prefix>'
curl -s "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/option/daily/EOHSummary/BTCUSDT/&marker=data/option/daily/EOHSummary/BTCUSDT/BTCUSDT-EOHSummary-2026-01-01" \
  | grep -o '<Key>[^<]*</Key>' | tail -3
```
聚合形态**不因任何新上市重开** —— 它死在代数上(§2), 不是死在数据上。

---

## 7. 未验证项(诚实边界)

| 项 | 为什么没验 | 验证路径 |
|---|---|---|
| Deribit 的标的数 | **硬约束 1: 不调用交易所 API。** 调研员的 "adds a handful more underlyings and does not change the order of magnitude" 本轮**未复核** ⇒ **INFERRED** | 匿名 GET `https://www.deribit.com/api/v2/public/get_currencies`, 再 `get_instruments?kind=option&currency=<c>` 数标的。需先解除约束 1 或改走静态归档 |
| `EOHSummary` zip 的列语义(是否含 IV/skew) | 本轮**只做前缀列举, 零市场数据下载**(与 r9 调研同一克制) ⇒ 未打开文件 | 若重开: 下 1 个 zip 读表头。**注意 E-0825-H**: 不得由列名推断语义, 需对 Binance 公开文档 |
| 锚轴长 10182 / A0 逐锚序列 | 本机无 `f10_A0_*.npy`(只有汇总 JSON), npz 在 pod2 | 若需: pod2 读 `meta_newprod_v4.npz` 的 `E_ts` |
| `K=0.17 / alpha=0.87` | 见 §5.2 | 打开 `r3k_fitK3.py` |

**本文所有数字**: §1 M1–M9、§1.2 重叠表、§2 模拟表、§4 算术表 = **VERIFIED**(本轮亲跑, 原始输出见 `raw_listings/` 与 `RECEIPT_*.json`)。§2.2 的 396 变体/−0.171/−0.275 = **VERIFIED 为引文**(本轮打开 DOCKET L354 逐字核对), 其底层实验**未本轮复跑** ⇒ 对结论为 INFERRED。§1.2 轴长 10182 = INFERRED(承口径锁), 但与本轮日历算术逐位自洽。
