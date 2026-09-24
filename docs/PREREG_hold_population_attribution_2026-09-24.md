> **创建:** 2026-09-24 03:5xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(news2) | **状态:** **预注册, 写于任何数字之前; 其中"替代 A/B"待 lead 裁定后才跑** | **作废条件:** lead 否决; 或 `news_stats.py`(`7141ba42`)的 `dbar` / `full_days` 定义改变; 或 `TARGETS_NEWS2_s42.npz` / 研究员 `scaled_diagnostic.npz` 的 sha 改变

# 预注册:把 NEW↔NC 缺口按"NC 发书 / NC 持旧书"切开

## 0. 这份文件先说一件事:lead 要的那个量,按字面**跑不了**

lead 的原话是"NEW 在那些锚上的收益贡献,**用同一 `dbar` 口径**报 bps/日"。我打开了判词装置的定义,按字面执行不了,按纪律停下报告,不自行变通。

**依据**(`/dev/shm/news2_2026-09-23/engine/news_stats.py`,冻结件 B1 用的就是它):

```
L118  def full_days(A, m):
          d = (A[m] // DAY) * DAY; ud, c = np.unique(d, return_counts=True); return ud[c == 6]
L122  def daily_on(A, r, days):
          ud, rd = BT.daily(A, r); pos = np.searchsorted(ud, days); assert np.all(ud[pos] == days); return rd[pos]
L156  def dbar(pn, po, m, days):
          D = np.stack([daily_on(a["A"][m], a["r"][m], days) - daily_on(b["A"][m], b["r"][m], days) ...])
```

- `full_days` 只承认**一天 6 个锚全在掩码里**的日子(`c == 6`)。
- `daily_on` 对每个请求的日子断言它存在,缺一天就 `AssertionError`。

所以 `dbar` 是**定义在完整 6 锚日上**的量。把掩码换成"203 个 hold 锚"这种**锚子集**,几乎没有哪一天还能凑齐 6 个锚 ⇒ `full_days` 返回近乎空,`daily_on` 直接断言失败。**`dbar` 不是一个可以按任意锚子集求值的量。**

这不是装置缺陷,是口径的定义域。**我不改这个装置,也不放宽 `c == 6`** —— 那会把一个被冻结件引用的量偷偷换掉。

## 1. 两个替代量(都要 lead 点头;A 不动口径,B 换口径并明确标注)

### 替代 A —— **不动口径**:按"日"切,不按"锚"切

把**完整日**分成两组,每组仍然是完整 6 锚日,`dbar` 原样可用:

- `D_hold` = 含 ≥1 个"NC 持旧书而 NEW 发书"锚的完整日;
- `D_pub` = 一个这样的锚都不含的完整日。

对每组各报 `1e4 * dbar(...).mean()`(bps/日)、日数、以及 30 日块 97.5% 区间(用装置里的 `boot`,`block` 与冻结件一致)。

**A 能回答**:缺口是不是集中在"NC 有 hold 的日子"。
**A 不能回答**:那 203 个锚**各自**贡献多少 —— 一天里还有另外 5 个锚,归不到锚头上。

### 替代 B —— **换口径, 必须另起名字**:逐锚,单位是 **bps/锚**,不是 bps/日

直接用引擎路径的逐锚量(`PATH_*.npz` 的 `A` / `nav0` / `nav1`,配对同 seed):

- `r_i = nav1_i / nav0_i − 1`;
- 报人口与补集上的 `mean(r_i^NEW − r_i^NC)`,单位 **bps/锚**,并报锚数;
- 同时报通道拆分(`price_trade` / `funding` / `fee`)的配对差,口径同上。

**B 明确不是 `dbar`,报表里一律写 "bps/锚(非 dbar)"**,不得与冻结件的 bps/日 并排比较,也不得相加成"占缺口的份额"——因为 `BT.daily` 在日内如何聚合(求和还是复利)决定了锚级分解是否可加,我**没有**验证它可加。**要写"份额"就必须先验可加性,本预注册不预先授权这一步。**

## 2. 人口定义(先于任何数字)

- **NC 持旧书**:`TARGETS_NEWS2_s42.npz` 的 `scaled_kind == 0`,且 `pad_before_new_axis == False`。已实测:新轴 1622 个,**理由全部是 `gross`**(`TARGETS_NEWS2_s42.json` `adapter.readings.scaled.reasons`)。
- **NEW 发书**:研究员 `scaled_diagnostic.npz` 的 `trade_mask == True`(逐年 publish 数已核:1558 / 1931 / 1668 / 1566)。
- **人口 P** = 两者的交:NC hold ∧ NEW publish。逐年 hold 差已实测为 2023 +50 / 2024 −2 / 2025 +155 / 2026 0,合计 **NC 多 hold 203** —— 但 **P 的大小不等于 203**(203 是净差,P 是交集,交集只会更大)。**P 的实际大小要测出来报,不许用 203 代替。**

## 3. 判读规则(冻结于数字之前)

1. `d > 0` 表示 NEW 在该组上更好。
2. **不设门**。本项是诊断,不产生录取/否决。
3. 区间跨零 ⇒ 写"在这台仪器上分辨不出",**不写"作用为零"**。
4. **不得**把 A 与 B 的数字相加、相除或换算成彼此。
5. 即使 A 显示缺口集中在 hold 日,也**只**是关联:hold 与那一天的其它 5 个锚同处一天,且 hold 本身是 `gross` 预检的结果,而 `gross` 由腿决定。**要因果必须反事实重链,本预注册不含那一步。**
6. 预先声明一个我预计会出现、且**不**构成解释的情形:hold 的锚上 NC 仍在吃旧仓位的收益,所以 NC 在这些锚上**不是零收益**。"NC 没交易"不等于"NC 没赚钱",报表必须把 NC 在 P 上的实测收益单列。

## 4. 已经实测、写在这里免得日后当成新发现

- 流动性门 `sel<sel_min` 在 NC 全史 **0 次**触发(非空转:统计量 138–400,判据窗内离门限最近也高 104 名)。
- NC 的 not_ready 人口 1086 个锚**全在 2022-H1**,判据窗内 0 个。
- 两边共用同一份 `combo_target.py`(d7577e82),**同一道 `0.4≤gross≤1.2` 预检**。
- 唯一实质不同的输入是 king 腿(pearson 0.764–0.903,逐位相同锚 0),但两边 rank-IC 只差 0.001–0.002 ⇒ **不是技能差**。

## 5. 不在范围内

- 反事实重链(换 KZ 重跑):要引擎,另行预注册。
- `sel_min` / `c == 6` / `gross` 预检任何一个的**改动**:本文件只测,不改。
- s2027:不跑。
