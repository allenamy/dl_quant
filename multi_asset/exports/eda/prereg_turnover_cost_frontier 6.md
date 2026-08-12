> **创建:** 2026-07-26 13:3xZ | **Session:** ma-v2 0C | **状态:** draft — **预注册, 待 team-lead 批准后才跑第一次扫描** | **作废条件:** 若 §2 的"已知答案控制"不能逐位复现 canonical, 本设计作废重写

# 换手-成本前沿 · 研究预注册 (0C)

**用户提案 / team-lead 判"方向对、先测后优"。本文在**任何一次扫描之前**写定网格、判据与口径。**

```
目标   max[ Gross − Turnover × EffCost ]   s.t. 净敞口偏置 ≈ 0; 逐年报告(2026 单列)
约束   信号与冻结模型零触碰; 全部在执行层/目标向量层实现; 不碰生产
```

---

## §1 先说清楚: 三个手段族**不在同一个 harness 上**

我读了引擎与已有的成本设施后, 这一条必须写在网格前面 —— 否则会把一个**做不到**的族当成"待跑"。

| 族 | 能否在 `engine/replay_fullhist.py` 上测 | 依据 |
|---|---|---|
| **1. band 族** (no-trade band × 逐名成本阈 × 持仓惯性) | **能** | 它们全部作用在 `CrossLegNetting.run()` 里 `shaped → net` 那一步, 即目标向量层 |
| **2. 中性优先补单政策** | **不能, 直接不能** | **引擎重放没有成交模型** —— 它由目标仓位差算换手 (`net_turn += \|net − prev_net\|`), **没有 maker/taker 腿、没有部分成交、没有欠配**。"容忍欠配"在这个 harness 上**没有可作用的对象** |
| **3. 逐名成本降权** | **能** (作为 band 族的一个轴) | 逐名成本可由 `a7_cost_tiers.json` 提供, 作用在同一步 |

**⇒ 族 2 需要另一套 harness**: 仓里已有 maker-fill 定律 (`apply_makerfill.py` / `makerfill_calibration.md`), **但它跑在 xattn king 面板上, 不是引擎的 4 腿 netted 书**。把两者接起来是一次**集成工作**, 不是一次参数扫描。
**⇒ 建议 (未经裁定): 族 2 从本轮剥离, 单列为后续研究, 并在交付里明写"本前沿不含补单政策维度" —— 否则读者会以为前沿已经涵盖了那 +27pp/年 的单项最大杠杆。**

---

## §2 ★★ 已知答案控制 —— 先过它, 否则任何前沿读数无效

**`band=0, thresh=0, inertia=0` 必须逐位复现 canonical `engine_fullhist_replay.json`:**

| 必须逐位相同 | |
|---|---|
| `per_year[y].gross_sharpe` · `net_of_cost_sharpe` · `mean_rank_ic` · `trading_days` | 全部 5 年 |
| `netting.{hedge_rate, gross_turn_ann, net_turn_ann, savings_bps_yr}` | |
| `avg_net_of_cost_sharpe` | |

**⇒ 这是本研究的"检索式先在已知答案上跑一遍"。⇒ 不过 ⇒ harness 有缺陷 ⇒ 前沿的每一个点都不可信, 停下修 harness。**
**⇒ 实现方式保证它可能成立: 扫描器**不修改** `engine/`, 而是 import 它并对 `CrossLegNetting` 做**子类**覆盖那一步; canonical 路径字节不变。**

---

## §3 网格 (两阶段, 限制多重比较)

**轴的定义 (全部尺度无关 —— 仓位是 L1 归一的, 绝对阈值会随 gross 漂移而变义):**

| 轴 | 定义 | 阶段 1 取值 |
|---|---|---|
| **b** no-trade band | 仅当 `\|w_target − w_held\| > b · mean\|w_target\|` 才动该名字 | 0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50 |
| **c** 逐名成本阈 | 仅当 `\|Δw\| · E[ret\|Δ] > c · cost_name` 才动 (`cost_name` 取 `a7_cost_tiers`) | 0, 0.5, 1, 2, 4 |
| **λ** 持仓惯性 | `w_target' = λ·w_held + (1−λ)·w_target` | 0, 0.25, 0.5, 0.75 |

- **阶段 1 = 逐轴单变量** (7 + 5 + 4 = **16 次**, 含共用的 band=0 基线) —— 先看每根杠杆自己的形状;
- **阶段 2 = 围绕阶段 1 最优的 2 维细网** (≤ 25 次), **轴的选择由阶段 1 的结果决定, 但"选两根最陡的轴"这条规则现在就写死。**

**⇒ 总预算 ≤ 41 次全史重放。**

## §4 口径 (硬要求, 全部来自既有裁定)

1. **换手绝对口径**: 引擎的 `net_turn_ann` 是**漂移毛值单位** (mean gross 0.5167) ⇒ **绝对读数 = ×1.94**。前沿表**只报绝对值**, 并在表头写明换算与出处;
2. **成本 = fee×fill 档位敏感形式**, 用用户真实档位 (**无返佣**), 不用引擎里那个 `COST_BPS = 1.9` 平值 —— 该常数在扫描器里必须**参数化**, 且**记录所用档位**;
3. **raw-y 净成本, 不是 IC**: 沿用 `pnl = net_pos · Y4`, `pnl_net = pnl − turn·cost`; `mean_rank_ic` 仅作诊断**并列**报告, **不进目标函数**;
4. **逐年 + 2026 单列**; **`net_turn` 需按年拆** —— canonical 只给全期年化, **这是本研究要新增的量**, 且新增不得改变 canonical 数;
5. **净敞口偏置 ≈ 0 是约束不是目标**: 每个工作点必须报 `mean|Σw|`, 超过基线 2× 即该点作废。

## §5 选点规则 (现在写死, 防事后挑)

- **推荐工作点 = 2022–2025 平均 net Sharpe 最大**; 并列时**取换手更低者**;
- **2026 不参与选点**, 只作**事后确认**并单列。若 2026 与选点结论相反, **如实报"前沿在 2026 不复现"**, 不换规则;
- **若前沿是平的** (最优与 band=0 的差 < 各年 net Sharpe 的年际标准差), 结论就是"**无甜点**", 照报。**"350–550× 是甜点"是待检验的假设, 不是待确认的结论。**

## §6 先验有利事实 (入档, 但必须被重放证实)

**alpha 近线性 (f1 = 0.297, pilot 加固期实测) ⇒ band 的代价**预期**小。⇒ 但它是**先验**, 不是证据: 若重放显示 band 代价大, 以重放为准, 并把这条先验记为被证否。**

## §7 交付

1. **逐年 frontier 表**: `gross_sharpe / turnover(绝对) / net_sharpe @用户真实档位`, 每个工作点一行, 2026 单列;
2. **推荐工作点** + 它相对 band=0 的三个 Δ;
3. **未经单独检验清单**;
4. **§2 控制的逐位比对输出** (作为附件, 不是一句"已通过")。

## §8 执行位置

**引擎重放的路径是硬编码的 `/mnt/storage/...` ⇒ 只能在 jpline 上跑。** 本地只写代码与验证语法。**⇒ 且按既有纪律: 不与训练任务抢 GPU —— 本研究是纯 CPU 重放, 但仍须错开队列, 由 team-lead 安排窗口。**

---

## 未经单独检验 (设计阶段)

1. **我未实际运行过 `run_replay`** —— §2 的"逐位复现"是**设计要求**, 我尚未验证 canonical 在当前代码上仍能复现它自己 (若 engine 自 2026-07-15 起有改动, 基线本身可能已漂);
2. **`a7_cost_tiers.json` 的档位定义 (`2× one-way 100k cost`) 与用户真实档位的对应关系我未核** —— 两者口径可能不同;
3. **`mean|w_target|` 作为 band 的尺度基准是我的选择**, 未与任何既有口径对齐; 换成 per-name 自身权重会得到不同的前沿形状;
4. **族 2 的"不能测"是我读 `CrossLegNetting.run()` 与 `apply_makerfill.py` 得出的**, 未与 0B 或 lead 确认是否另有我不知道的 harness。


---

# ★★ §2 已知答案硬门 —— **通过 (逐字节)**, 0C 2026-07-26 13:3xZ

## 第一步: 先问"我读的代码是不是产出 canonical 的那份代码"

**canonical 产物 `engine_fullhist_replay.json` 只存在于服务器, 不在 git 里** (本仓无该文件, 无 git 历史)。⇒ 所以"engine 有没有漂"不能只看 git 历史 —— **git 只能证明它自己那份没变, 不能证明服务器那份与它相同。**

**⇒ 逐文件哈希对比 (本地 git vs jpline), 8/8 全同:**
```
replay_fullhist e426dfe5d834fcca   signal_chain 3c3f414aa4218ce2   netting     1744d1f719a26b9f
panel_source    583b48cf156852ab   funding_risk 4ad4be1ee543b903   vol_gate    77c9170b4e3eb261
isotonic_calib  4e3d1559b0d90197   ic_monitor   43fab7da6717d6b9
```
**⇒ 产出 canonical 的代码 = 我能读到的代码。前提成立。**

## 第二步: 复现

```
命令   python engine/replay_fullhist.py --funding_mode rank --shaping cap --out <scratch>
       (canonical 配置即 CLI 默认值; --out 指向 scratch, canonical 文件全程未被写)
结果   sha256(复现) = sha256(canonical) = 5f61188ba89ec4bb463eb22d9d5b89fd793de890437b973f8f71ce951835401a
       JSON 规范化后 diff 无差异
```

**⇒ 硬门 PASS —— 且是**逐字节相同**, 不只是数值相等。⇒ 网格预算可以开花。**

## canonical 参考值 (已 pin 进本仓: `engine_fullhist_replay_CANONICAL_pinned.json`)

| | 2022 | 2023 | 2024 | 2025 | 2026 | avg |
|---|---|---|---|---|---|---|
| gross Sharpe | 11.82 | 14.18 | 14.44 | 18.70 | 13.74 | — |
| **net Sharpe** | 9.64 | 11.77 | 12.55 | 16.04 | 11.05 | **12.21** |
| rank-IC | .0616 | .0859 | .0805 | .0764 | .0622 | — |

`netting`: hedge 12.4% · gross_turn_ann **857.25** · net_turn_ann **750.775** · savings 202.3 bps/yr · years 4.492 · anchors 9821 · `cost_bps 1.9`

**⇒ 绝对口径 (×1.94): gross ≈ 1663 · net ≈ 1457。前沿表按绝对值报, 换算在表头写明。**

> **★ 顺带一条该单独说的: 整个研究校准所依据的那份 canonical 产物, 此前**不在版本控制里** —— 它只是服务器上一个 Jul 15 的文件。⇒ 我已把它 pin 进本仓并附哈希。**否则"前沿相对 canonical 改善了多少"这句话, 其基准随时可能被一次重跑悄悄换掉, 而没有任何东西会响。**(未经裁定: 服务器侧是否也该锁定/只读, 交 team-lead。)**
