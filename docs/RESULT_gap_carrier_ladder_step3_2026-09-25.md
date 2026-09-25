# 第 3 步 组合层替换阶梯: 两端已钉住, 两个臂判「不承载」, 三个臂被覆盖缺陷挡住

> **创建:** 2026-09-25 | **Session:** news2 / b9646a9e | **状态:** 四个控制全过(引擎层红控制恰好为 0, 正控制命中预注册期待值); WL/FUND 两臂判「不承载」; KZ/F10 三臂被覆盖缺陷挡住, 待 lead 裁定 | **作废条件:** lead 改写臂定义, 或 `continuous_combo`/`combo_target` 代码 sha 变化, 或 NC/NEW 任一方在案产物被重建

**预注册**: `docs/PREREG_gap_carrier_ladder_2026-09-25.md` @ `be4a013a8` 第 3 步。**判据由 team-lead 书写, 我逐字抄录未改一字**(我是 NC 补丁作者, 对「它准入什么」有利害, 判据不得由我书写)。

**贯穿全文的局限**(每个数字旁都成立): 各臂**不可相加**, 本文不作任何加和推断; 每个臂都是**管线产不出的组合, 只是测量仪器, 从不是可部署版本**。

---

## 一句话结论

阶梯的两端被钉死了(红控制恰好 0, 正控制 2.834577 命中预注册的 2.835), 但**它现在还认不出缺口的承载者**: 能干净测的两个臂(`WL_res`、`FUND_res`)双双落在 lead 的「**不承载**」带里, 而能测 King / F10 通道的三个臂恰好是被覆盖缺陷挡住的那三个。**已排除两条通道, 未定承载者。**

---

## 1. 装置为什么是一个新驱动, 而这仍然算「combo 代码未改」

`news2_combo.py` 是**驱动**; combo **代码**是 `continuous_combo.evolve` + `combo_target`(sha `1501c9f6` / `d7577e82`)。驱动会断言 F10 的 `TRAIN_RECEIPT` 里记的输入 sha 仍与磁盘相符, 而 F10 记的输入**包含 `legs.npz`** —— 经由那个驱动替换任何腿数组都会撞上 `('training input drift', p)`。改写那份收据去迁就替换等于**伪造收据**, 不在选项内。

所以装置 `pnoise_ladder_combo.py` 是一个**新驱动**, 调用**未改动的** `evolve`。许可它的是红控制, 不是我的声明。

---

## 2. 四个控制(lead: 不过任一 ⇒ 整个阶梯 UNAVAILABLE, 不跑引擎)

| 控制 | 判据(lead 原话) | 结果 | 收据 |
|---|---|---|---|
| 红 `arm none` | 不替换任何数组 ⇒ 须复现 NC | **PASS**: 两个策略 max\|Δw\| = 0, **逐位相同** | `LADDER_REDCONTROL.json` |
| 正 `arm all_new` | 全部数组换成 NEW ⇒ 须复现 NEW 在案目标, max\|Δw\| ≤ 1e-6 | **PASS**: max\|Δw\| = **0.000000e+00**(不是 ≤1e-6, 是逐位); publish 3072/6723 两侧相同; trade_mask 与 reason **0 个锚**不一致; 轴 8142/8142 相同 | `LADDER_POSCONTROL.json` |
| 变异 `arm kz_neg` | KZ 取负 ⇒ 发书决策必须改变 | **PASS**: trade_mask 翻转 330(literal)/2059(scaled)个锚; publish 2946→2740, 6520→6289 | `LADDER_MUTATION_vs_none.json` |
| **引擎层红控制**(我加的) | staged combo 与在案 NC combo 逐位相同 ⇒ dbar 须恰好为 0 | **PASS**: 五个段全部 `exactly_zero=True`, `max_abs_daily_bps=0.0`, 32/32 路径, 锚轴相同 | `STEP3_DBAR_none.json` |
| **引擎层正控制**(我加的) | staged combo 与 NEW 在案逐位相同 ⇒ dbar 须复现已知缺口 | **PASS**: pre-2026 **2.834577** vs 预注册期待 2.835; 2026 **−0.366667** vs 期待 −0.367 | `STEP3_DBAR_all_new.json` |

两条引擎层控制是承重的。没有它们, 任何臂的 dbar 都可能是我「把 combo 塞进 `work/combo_s42` 再走 adapter/引擎」这条搬运路线自己造出来的。红控制恰好为 0、正控制命中已知缺口 ⇒ **搬运路线逐位忠实, 阶梯两端确实就是 NC 与 NEW**。

**期待值写在看到数字之前**: `STEP3_POSCONTROL_ENGINE_EXPECTATION.json`, 落盘于 05:14:30Z, 引擎正控制 05:23:4xZ 才出数。

**先断言基线为绿**: 加装「源接线」补丁后我**重跑了组合层红控制**, 仍是同两个 sha(`210270198350cdce` / `f4630a20f796bce2`)—— 不是只跑变异就收工。

---

## 3. 正控制的拒绝暴露的事: `evolve` 有四个实参不在 legs 文件里

第一次跑正控制死在 `KeyError: 'RN8' is not a file in the archive`。**这个拒绝本身是发现, 不是 bug。**

NEW 的 `data/f10v2_legs.npz` 只有 `E_ts / symbols / KZ / Z24 / ZFD / WL / ready / LR / seat_priced_fraction`。按**消费它的那一行**读(研究员自己的 `continuous_combo.py`: `:49` paths / `:61` handles / `:69` book_legal / `:78` evolve 调用):

| `evolve` 实参 | NEW 侧来源 |
|---|---|
| `KZ` `ZFD` `WL` `ready` | `data/f10v2_legs.npz` |
| `P` | `f10_s42/F10_OOF.npz` |
| **`rn8`** | `data/funding_state.npz[rn8]` |
| **`legal`** | `data/funding_state.npz[legal]` → `book_legal = align_universe(...) & fund['legal'][use]` |
| **`qv`** | `data/dlw_targets.npz[qvk]` |
| **`members`** | `data/dlw_targets.npz[members]` |

**覆盖缺口(待 lead 裁定)**: `legal` 与 `members` 是 NEW↔NC 的真实输入差异, 而 lead 的五个单换臂**一个都没换它们**(lead 的 `FUND_res` 逐字是 ZFD+ready+QV+RN8)。实测 `legal`: NC 的 `book_legal = align_universe ∧ tradable_mask ∧ crypto` 有 2,822,237 个 True 格, NEW 的 = `align_universe ∧ funding_state[legal]` 有 2,916,291 格, **94,054 格不一致, 涉及 1,628/8,143 个锚**。我没有自行改 lead 的臂表。

**两条实测确认不是混淆项**:
- config `params` 两侧**逐字节相同**(config sha `3a8422f3…647c94e`)⇒ params 不是阶梯输入。
- NEW 轴 = NC 轴限制到 `[1641168000, 1789776000]` **逐位相同**; NEW 缺的 12 个 NC 锚是 2022-01-01/02, 在 `use ≥ 1672531200` **之前** ⇒ `evolve` 的状态路径完全相同, 不存在序列差。

---

## 4. 引擎层读数(dbar, bps/day, 在役 `scaled` 读数)

在役 dbar 读的是 `scaled` 读数(运行标签 `NEWS2_s42_scaled_rule_raw_UAFE`; `ovn_adapter.py:31` `READING_OF = {"scaled": "scaled_diagnostic", "lit": "literal"}`)。

| 臂 | pre-2026 (915 天) | in σ | 2026 (242 天) | in σ₂₀₂₆ | lead 判据下的读法(pre-2026) |
|---|---|---|---|---|---|
| `none` 红控制 | **0.000000** | — | **0.000000** | — | 恰好为 0, 五段全 `exactly_zero` |
| `all_new` 正控制 | **+2.834577** | +2.716 | **−0.366667** | −0.608 | = 缺口本身(命中预注册 2.835 / −0.367) |
| `WL_res` | **+0.338361** | +0.324 | +1.131417 | +1.878 | **不承载**(\|d\| ≤ 1σ) |
| `FUND_res` | **−0.004739** | −0.005 | −0.840929 | −1.395 | **不承载**(\|d\| ≤ 1σ) |
| `KZ_res` | 未跑 | | 未跑 | | 被覆盖缺陷挡住, 待裁定 |
| `F10_res` | 未跑 | | 未跑 | | 同上 |
| `KZWL_res` | 未跑 | | 未跑 | | 同上 |

**lead 的门槛**(逐字): 承载大部分 ⇒ `d ≥ max(2.835/2, 2σ)` = `max(1.4175, 2.08739)` = **2.08739**; 不承载 ⇒ `|d| ≤ 1σ` = **1.04370**; 之间 ⇒ 分辨不出。σ 来自扰动噪声族 `sd_ddof1 = 1.0436952`(pre-2026, n=7), 2026 段 σ₂₀₂₆ = `0.6026030`。

### 怎么读这两个「不承载」

- `FUND_res` 的 pre-2026 是 **−0.004739 = −0.005σ** —— 把 NEW 的 ZFD+ready+QV+RN8 全换过来, 对 pre-2026 的书**几乎恰好没有影响**。这不是「效应小」, 是「在这个口径下测不出效应」。
- `WL_res` 的 pre-2026 是 **+0.324σ**, 同样落在不承载带内。
- 但两个臂在组合层都**大幅推动了书**(见 §5): `FUND_res` 在 scaled 下动了 6,319 个锚、max\|Δw\| 9.9e-03。**「书被推动了」与「pre-2026 净额被推动了」是两件事**, 这里正好是一个实例。
- **2026 段两个臂都超过了缺口本身**: 缺口 2026 是 −0.367, 而 `WL_res` 是 **+1.131**(反号且更大), `FUND_res` 是 **−0.841**(同号但 2.3 倍)。这就是 lead 预先写下的「各臂不可相加」, 现在有实测。**不要把它们加起来。**

---

## 5. 各臂在组合层把书推动了多少

对 NC 端(`arm none`)的 max\|Δw\| 与 >1e-6 的锚数, scaled 读数:

| 臂 | max\|Δw\| | >1e-6 的锚 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| `all_new` | 1.1142e-02 | 6848/8142 | 1584 | 2005 | 1693 | 1566 |
| `KZ_res` | 1.0884e-02 | 6737/8142 | 1554 | 2043 | 1574 | 1566 |
| `WL_res` | 1.0547e-02 | 6320/8142 | 1521 | 1946 | 1287 | 1566 |
| `F10_res` | 1.2242e-02 | 6706/8142 | 1575 | 1938 | 1627 | 1566 |
| `FUND_res` | 9.9227e-03 | 6319/8142 | 1508 | 1921 | 1324 | 1566 |
| `KZWL_res` | 1.0832e-02 | 6764/8142 | 1550 | 2040 | 1608 | 1566 |

三点否则这张表会被读错:

1. **publish 计数是很差的判别器。** `FUND_res` 的 publish 几乎没变(2946/6516 vs NC 的 2946/6520), 但它动了 6,319 个锚、max\|Δw\| 9.9e-03 —— 与换掉全部输入的 `all_new` 同量级。**「发书决策没变」不等于「书没变」。**
2. **`literal` 策略在 2023/2024 对所有臂恰好 max\|Δw\| = 0**(包括 `all_new`): 那两年 literal publish = 0, 整段是「持仓不动」, 权重就是结转的同一状态。⇒ **literal 在 2025 之前不承载任何 pre-2026 信息**, 读 pre-2026 只能用 scaled。
3. `KZ_res` / `F10_res` / `KZWL_res` 在 2026 的 literal max\|Δw\| **同为 9.148577e-03(七位全同)** —— 三个臂一个数, 指向同一个共同成因(覆盖缺陷把锚整个否掉、状态同样结转), 不是三个独立效应。

---

## 6. 三个臂被换入动作自己造出来的缺陷挡住

### 症状: 两端都吐不出的拒绝理由

| 臂 | literal publish | scaled publish | 两端没有的新理由 |
|---|---|---|---|
| `none`(= NC) | 2946 | 6520 | — |
| `all_new`(= NEW) | 3072 | 6723 | — |
| `KZ_res` | 1496 | 5213 | **King scores incomplete: 1486 锚** |
| `WL_res` | 2975 | 6482 | 无 |
| `F10_res` | 2260 | 5843 | **F10 coverage: 744 锚(scaled)** |
| `FUND_res` | 2946 | 6516 | 无 |
| `KZWL_res` | 1532 | 5207 | **King scores incomplete: 1486 锚** |

### 机制: 读发出它的那一行

`combo_target.py:26`

```
if not np.isfinite(king_rank).all(): return {'accepted':False,'reason':'King scores incomplete',...}
```

`king_rank` 是该锚 KZ 在**该锚 members 上**的切片 —— 一个非有限格否掉整个锚。

实测(`STEP3_COVERAGE_ARTIFACT.json`, verdict `COVERAGE_ARTIFACT_CONFIRMED`):

- NEW 的 KZ 在 NC 的 member 集上有 **42,889 个非有限格**(占 1.7249%), 涉及 **1,487 个锚**。
- 这些非有限格里 **100%** 是 NEW 自己 member 集里**没有的名字**。
- **NEW 的 King 不给 NEW 从不准入的名字打分。** 把 NEW 的 KZ 换到 NC 更大的 member 集上, 缺的正好是 NEW 筛掉的那些名字。
- F10 的 `P` 覆盖足迹**逐格相同**(同 1,487 锚 / 42,889 格), 但 combo 对 F10 是覆盖率门(`combo_target.py:28` `okf=np.isfinite(f10_score)` 容忍 NaN)而非硬 NaN 检查, 所以只掉 744 锚而不是 1,463。

**绿控制**(不是我说它对, 是它得先答对一个已知数): 同一问题问 NC 自己的 KZ 在 NC members 上 ⇒ **0 个锚**。PASS。没有这一行就分不清「是换入造成的」还是「装置一直在数错」。

### 逐年损伤, 以及为什么上界要按「天」报

| 年 | 受影响锚 / 该年锚 |
|---|---|
| 2023 | **0 / 2190** |
| 2024 | **0 / 2196** |
| 2025 | 24 / 2190 (1.10%) |
| 2026 | **1463 / 1567 (93.4%)** |

那 24 个 pre-2026 锚**恰好是 2025 年最后四天**(12-28 / 29 / 30 / 31, 每天 6 个锚全中)—— 缺陷从 NEW 的 member 筛开始分叉那一刻起烧到窗口末尾, 不是散落的。

**dbar 的分母是「天」不是「锚」**, 所以锚份额不构成上界: pre-2026 分母 915 个完整日(冻结口径 `news_stats.full_days`, 数字引自引擎红控制收据), 被污染 **4/915 = 0.437% 的天**。我先前按锚报的 0.36% 是错的那一层 —— 换成消费这个量的那一层重报。

⇒ **pre-2026 基本干净, 2026 段对这三个臂判 UNAVAILABLE**: 2026 的书 93% 是被换入动作抹掉的, 不是 KZ 承不承载缺口。lead 的门槛本来按 pre-2026 写, 所以阶梯仍能答问题。

因为受污染的四天是**连续的、贴在窗口末端**, 还有一个不改口径的干净读法: 在冻结的 `pre2026` 段(915 天)之外**另报**一个去掉 2025-12-28..31 的 911 天读数, 标注清楚是附加读数而非改口径。

---

## 7. 待 lead 裁定的两件事

1. **三个被污染的臂怎么改**(我不自选): (a) 只报 pre-2026、2026 段判 UNAVAILABLE, 并带上 0.437% 的天污染上界; (b) 另加一个敏感性臂, 在那 1,487 个锚上保留 NC 的 KZ, 代价是多一次引擎跑(约 12 分钟), 换来「0.437% 要不要紧」有实测而非上界; (c) 把 KZ 与 members 一起换 —— 但那就不再隔离 KZ, 臂的语义变了, 要 lead 重写判据。
2. **`legal` / `members` 覆盖缺口**: 是否加 `LEGAL_res` 与 `MEM_res` 两个臂(判据请 lead 书写), 还是明确接受这个缺口、只在五臂范围内下判词。

**为什么这不能由我裁定**: 判据不得由对「它准入什么」有利害的人书写, 而 KZ 正是 NC 与 NEW 唯一实质不同的那条腿(见 `new_vs_nc_gap_is_not_score_layer_skill_2026_09_24` 记忆), 我是 NC 侧补丁的作者。

---

## 8. 收据

- 预注册: `docs/PREREG_gap_carrier_ladder_2026-09-25.md` @ `be4a013a8`
- 控制汇总: `receipts/pnoise_2026-09-24/STEP3_CONTROLS.json`
- 逐臂 combo: `LADDER_{none,all_new,kz_neg,KZ_res,WL_res,F10_res,FUND_res,KZWL_res}.json` + `STEP3_ARMS_COMBO.tsv`
- 控制检验: `LADDER_REDCONTROL.json`, `LADDER_POSCONTROL.json`, `LADDER_MUTATION_vs_none.json`
- 逐臂 Δw: `LADDER_DELTA_*_vs_none.json`
- 覆盖缺陷: `STEP3_COVERAGE_ARTIFACT.json`
- 引擎层: `STEP3_DBAR_{none,all_new,WL_res,FUND_res}.json`, `STEP3_DBAR_SUMMARY.tsv`, `STEP3_POSCONTROL_ENGINE_EXPECTATION.json`
- 装置: `devices/{pnoise_ladder_combo.py, ladder_poscontrol_check.py, ladder_coverage_artifact.py, ladder_arm.sh, ladder_five_arms_combo.sh, ladder_engine_arm.sh, ladder_engine_batch.sh, patch_ladder_sources.py}`
- 前序: 第 0 步 `01f5b5183`(TIER_2_STANDS), 第 1 步 `ea79fe670`(SEAT_DIFF_FROM_INPUT_KING_P), 第 2 步 `ad6c8023f`
- 本步提交: `bdf9c45d3`(控制三件), `c896c84b4`(五臂 + 覆盖缺陷), `c3d83ecd5`(引擎红控制 + Δw + 按天上界)
