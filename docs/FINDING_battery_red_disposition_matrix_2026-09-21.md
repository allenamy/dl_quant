> **创建:** 2026-09-21 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb | **状态:** 取证完成, 根因已定位到**单行**, 修法已拟(类形状), **尚未落码** —— 本文先发, 供独立研究员并行排查 | **作废条件:** `_DELIBERATE` 改为从矩阵派生后本文 §7 的修法段作废(结论与取证段仍有效); 或 `skipped_stop_maker_only` 的矩阵判词被改写而本文未同步

# 电池红: `tests_disposition_matrix` —— 全链取证报告

> 一句话: **161 套里 1 套红, 红的根因是整个生产账本里的 1 行**; 书的行为**完全正确**; 红的是**尺子**。
> §4-4 的部署被这个红挡着, **我没有绕过 `safe_commit.sh`** —— 实盘至今仍是 `409ea16`, 代码区零改动。

---

## §0 一页结论(白话)

1. **电池确实是红的, 部署确实被挡住了, 我没有绕过。** 实盘运行树 = 本地 main = origin/main = `409ea16`; `git status` 代码区 0 处改动(只有 `state/` 的运行时文件在动)。§4-4 的改动**一行都没上线**。
2. **红的是 161 套里的 1 套**(`tests_disposition_matrix`), 它里面 80 格中的 **2 格**。这 2 格都是承重的账本断言, 不是装饰。
3. **根因是一行。** 整个生产账本里, 终态 `skipped_stop_maker_only` **历史上总共只出现过 2 行**, 就是让这 2 格变红的那 2 个锚各一行:
   - 2026-09-18 16Z, **GUSDT**, 309.53 USDT
   - 2026-09-19 12Z, **STARUSDT**, 2,536.33 USDT
4. **这个终态按矩阵自己的判词就是「故意不发」的。** 它 2026-09-13 按裁定 R2′ 入矩阵, 原文写着 "sendable, **deliberately not sent**, carried to the next anchor's maker exit"。但尺子里那个"故意"的名单是**手写的常量** `_DELIBERATE = {"skipped_no_chase_arm"}` —— 只有追单实验那一个。于是**按设计故意保留的残差, 被当成了非自愿缺口**。
5. **书的经济行为没有问题, 已逐行核实**: 两个被止损的名字都在**下一个锚由 maker 成交平掉**了 —— GUSDT 09-18 20Z 成交 278.40(意图 278.2, 残 −0.1 尘埃), STARUSDT 09-19 16Z 成交 −2,445.35(意图 −2,445.0, 残 0.4 尘埃)。裁定 R2′ 要的就是这个: maker-only 退出、不追单、下一锚补上, **省掉 2,536 USDT 的吃单穿越**。它做到了。
6. **所以这是一次真红, 但红的对象是尺子。** 缺陷类型是这个库反复付学费的那一类: **矩阵在散文里声明了性质, 而消费者持有自己的硬编码集合 —— 声明不约束消费者**(参见 `declaration_that_does_not_bind_the_conclusion`)。
7. **第三个发现(独立于本案, 但更值得看)**: 这套电池**只在提交时跑**。`run_acceptance.sh` 没有任何 launchd/cron 调用者(唯一的生产调用者是 `ops/safe_commit.sh`)。而这套断言的输入是**每天在长的实盘账本**。⇒ 一个账本事实的回归, 只会在**下一次有人部署时**被发现。本案就是实例: 首个触发锚 09-18 16Z, 上一次绿 09-18 02:30Z, 而下一次运行是**三天后的今天**。

---

## §1 电池基线(先测再改, 未绕过)

按"改动只经 `ops/safe_commit.sh` + 电池全绿"的纪律, 在打任何补丁**之前**先在**真实实盘树**上跑基线:

```
BASELINE_REAL_EXIT=1
ACCEPTANCE: NOT GREEN
树状态: .env=true, notify_audit_newest_age_hours=2.1, 代码区 0 处改动
HEAD: 409ea16
红: 161 套中恰好 1 套 —— tests_disposition_matrix
```

| 项 | 值 | 收据 |
|---|---|---|
| 本次运行 | `FAILURES: [...]` (80 checks) | `docs/receipts/battery_red_2026-09-21/20260921T104851Z_tests_disposition_matrix.log` |
| 上一次绿 | `ALL PASS (80 checks)` | `docs/receipts/battery_red_2026-09-21/20260918T023037Z_tests_disposition_matrix.log` |
| 更早 | 20260917 六次、20260913、20260912 两次 **全 ALL PASS** | `~/dl_quant_live/state/acceptance/` |

⚠ **按纪律引原文判词整行, 不引"N/M"**(电池的 "N checks" 印在 ALL PASS 与 FAILURES 两行上, 计数不证明通过 —— `battery_count_printed_on_both_verdict_lines_2026_09_18`)。

---

## §2 红的是哪两格(判词原文)

```
FAILURES: [
 "★★★ ...and EVERY steady trading anchor's INVOLUNTARY gap is small — the deliberate
   no-chase-arm abstention is excluded (alpha we chose to forgo); REBUILD anchors ...,
   RESIZE anchors and VENUE-LOCKED anchors (E-0910-A) are their own classes asserted below",
 "★★★ ...and the halted/trading SEPARATION holds on the INVOLUNTARY total — a halted anchor
   declares its whole book, a trading anchor involuntarily misses a small fraction. The
   deliberate part (no-chase, resize abstentions) is chosen, measured, and excluded"
]
max steady traded involuntary 2536 vs min halted 4169
```

两格的含义:
- **格 1(稳态尺)**: 每个稳态交易锚的**非自愿**缺口必须 < **200 USDT**。
- **格 2(分离性)**: 停机锚申报整本书, 交易锚只非自愿地差一小块 ⇒ `max(稳态非自愿) < 0.25 × min(停机锚整书)` = `0.25 × 4,169 = 1,042 USDT`。

两格红于**同一行**: 2,536.3 > 200, 且 2,536.3 > 1,042。

---

## §3 尺子的算术(装置自己的, 不是我重写的)

`live/tests_disposition_matrix.py`:

```python
_DELIBERATE = {"skipped_no_chase_arm"}          # ← 手写常量, 本案的缺陷就在这里

def _split(rid):
    g   = _by[rid]                               # OD.gaps(重判后的全部行, rid)
    d   = _deliberate_usdt(rid)                  # 只数 _DELIBERATE 里的终态
    cap = float(g.get("venue_cap_usdt") or 0.0)  # -2027 场所仓位上限, 单独成类
    return d, g["gross_usdt"] - d - cap          # (自愿, 非自愿)
```

而 `OD.gaps()`(`live/order_disposition.py` L178)做的事:
- 只收矩阵里判为 **GAP** 的终态;
- `residual = intended_notional − filled_notional`, **逐行**;
- **剔除 `venue_reject` 带 `-5022`**(自 2026-08-02 起由 taker 补单收回, 不是缺口);
- **剔除 `abandoned_max_attempts` 带 `-4164`**(低于场所最小名义的尘埃);
- `-2027` 留在 `gross_usdt` 里但**另打标签** `venue_cap_usdt`, 供尺子拆出。

> ★ **我第一次查错了方向**: 我按 `venue_reject` 行粗加 `intended − filled`, 得到 09-18 16Z = 7,535.4 / 09-19 12Z = 4,510.4 / 对照锚 09-20 16Z = 5,558.1 —— **复现不出 310 / 2,536**, 而且对照锚比红锚还大。原因就是上面这三条剔除规则。**改用装置自己的 `OD.gaps` 函数后逐位复现**: 309.5 / 2,536.3, 与判词里的 310 / 2,536 一致。
> 教训写进 §6。

---

## §4 取证: 非自愿 > 200U 的**全部**锚, 逐行拆到终态

装置: `docs/receipts/battery_red_2026-09-21/forensic_disposition_split.py`(= 该电池前 345 行原样 + 我的拆解段; `_HERE` 改为绝对路径以便在仓外跑)
输出: `docs/receipts/battery_red_2026-09-21/forensic_output.txt`

全史 26 个锚非自愿 > 200U。**其中 24 个是已归类的合法形态**:

| 形态 | 锚 | 终态构成 |
|---|---|---|
| **停机锚**(申报整书, 本就该大) | 08-01 06Z … 09-13 08Z 共 14 个 | 全部 `blocked_by_halt` |
| **REBUILD / RESIZE / VENUE-LOCKED**(各自成类, 另有断言) | 08-26 20Z, 08-27 08Z, 09-07 04Z, 09-10 00Z, 09-11 08Z 等 | `abandoned_max_attempts -4400`(账户级量化规则锁) + `venue_reject -2027`(场所仓位上限) |

**剩下 2 个就是红格**, 且两个的非自愿部分**各自只由 1 行构成**:

```
### 2026-09-18 16Z A1789748640  inv=309.5
    skipped_no_chase_arm           n=10  gross=  374.6   ← 已按自愿剔除, 正确
    skipped_stop_maker_only        n= 1  gross=  309.5   ← 全部的非自愿缺口

### 2026-09-19 12Z A1789820640  inv=2536.3
    skipped_stop_maker_only        n= 1  gross= 2536.3   ← 全部的非自愿缺口
    skipped_no_chase_arm           n=15  gross=  881.7   ← 已按自愿剔除, 正确
```

**该终态的全史(整个生产账本)**:

```
09-18 16Z A1789748640 GUSDT      topup_taker  intended=  309.5  residual=309.53104934
09-19 12Z A1789820640 STARUSDT   topup_taker  intended=-2536.3  residual=2536.32678
总行数 2
```

**它在矩阵里的判词(原文)**:

```
skipped_stop_maker_only → GAP, recoverable=False
"a stopped name's from_partial residual (per-name stop cf40ea21: maker-only exit, never
 chased — ruling R2'): sendable, DELIBERATELY NOT SENT, carried to the next anchor's maker
 exit. Intended, recorded, paged while it lasts, and still a gap"
```

⇒ **矩阵说它是故意的; 尺子的"故意"名单里没有它。** 这就是全部根因。

**时间线自洽**: 该格 2026-09-13 按裁定 R2′ 入矩阵 ⇒ **09-18 16Z 之前从未触发** ⇒ 电池一直绿; **头两次触发就把它打红**。不是"三天前的回归", 是**一个潜伏了五天的错分类, 在这个终态第一次真实发生时暴露**。

---

## §5 经济核对: 书有没有真的漏掉 2,536 USDT?(**没有**)

这是本案唯一在钱上要紧的问题。逐行追两个名字的后续锚:

```
--- GUSDT ---
  09-18 16Z maker        partial_expired          intended= 309.5  filled=0.0
  09-18 16Z topup_taker  skipped_stop_maker_only  intended= 309.5  filled=0.0   ← 故意不追
  09-18 20Z maker        partial_expired          intended= 278.2  filled=278.39541  ← 下一锚 maker 平掉
  09-18 20Z topup_taker  skipped_min_notional     intended=  -0.1              ← 只剩尘埃

--- STARUSDT ---
  09-19 12Z maker        partial_expired          intended=-2555.1 filled=-18.81282
  09-19 12Z topup_taker  skipped_stop_maker_only  intended=-2536.3 filled=0.0   ← 故意不追
  09-19 16Z maker        partial_expired          intended=-2445.0 filled=-2445.34608  ← 下一锚 maker 平掉
  09-19 16Z topup_taker  skipped_min_notional     intended=   0.4              ← 只剩尘埃
```

**结论: 裁定 R2′ 按设计工作。** 止损名的退出是 maker-only、不追单、带到下一锚, 并在下一锚**以 maker 价成交完毕**。代价是多持有一个锚(4 小时)的敞口, 收益是省掉 2,536 USDT 的吃单穿越成本。**没有任何敞口被遗留**。

> ⚠ 独立研究员请复核这一段: 我只核了这两个名字的**订单行**, 没有独立从**持仓快照**核对下一锚后 GUSDT/STARUSDT 的仓位确为 0。这是 §9 里给你的具名问题 Q2。

---

## §6 我在这一轮里差点报错的两件事(自陈)

1. **元组顺序读反**。`_split()` 返回 `(deliberate, involuntary)`, 我第一次读成了 `(involuntary, deliberate)`。按错的读法, 会得出"**自 08-04 起 272 个锚里有 100 个超尺**"这样一个耸人听闻且完全错误的结论。正确读法: 272 个稳态交易锚, 32 个非自愿缺口 > 0, **只有 2 个超过 200U 的尺**。**在报告出口前抓住**。
2. **猜字段名三次**。`reject_code|code|err_code`(都不存在)、`notional|target_notional|delta_notional`(实际是 `intended_notional`/`filled_notional`)、`terminal`(实际是 `terminal_reason`)。**修法**: 先 dump 真实 key 列表再写查询。
3. **用自己的粗加法代替装置的算术**(§3 里那段)。这是同一天里第二次踩"**现写脚本 = 主动放弃全部已有补丁**"(`run_the_canonical_inspector_before_ad_hoc_scripts`)。**修法已执行**: 本报告的所有数字都出自**装置自己的 `OD.gaps()`**, 取证脚本是该电池前 345 行**原样**加载, 不是我的复现。

---

## §7 拟议修法(**类形状**, 尚未落码)

**不采用**的修法(实例形状, 明天再加一个终态会原样复发):
```python
_DELIBERATE = {"skipped_no_chase_arm", "skipped_stop_maker_only"}   # ✗ 拒绝
```
理由: 我自己的受据规则 —— **我的修法是实例形状的, 缺陷是类形状的**(`my_fixes_are_instance_shaped_defects_are_class_shaped_2026_09_18`)。验收线要问的是"**明天新加一个终态, 还会不会被抓住**"。

**采用**的修法:
1. 在 `order_disposition.DISPOSITION` 的**每一个 GAP 格**上加**必填**字段 `deliberate: bool`(把现在只写在散文 `why` 里的性质, 变成机器可读的合同项)。
2. 暴露 `OD.deliberate_reasons()`; 尺子的 `_DELIBERATE` **从矩阵派生**, 删掉手写常量 —— **一份共享实现**。
3. **缺失即拒绝**: 断言"每个 GAP 格都声明了 `deliberate`"; 少一个就红, **不是跳过**(`absent_key_means_skip_defect_family`)。
4. **两条负控**(按 E-0921-F 收紧后的验收线):
   - **先断言基线为绿**, 再注入一个不带 `deliberate` 的合成 GAP 格 ⇒ 必须变红(避免"基线已红时红能力检查恒真", `red_capability_check_is_vacuous_when_baseline_is_red`);
   - 把某个格的 `deliberate` 翻转 ⇒ 尺子量到的人口必须**随之改变**(证明它承重, 不是装饰)。
5. 判词里**同时给出**基线值与变异后值。

**修完后尺子会读到什么(预测, 待实测)**: 两个红锚的非自愿缺口变为 **0**; `max(稳态非自愿)` 回到 **< 200U**; 两格转绿。⇒ 这条预测本身就是修法的验收判据之一, **先写在这里, 数字后到**。

---

## §8 第三个发现: 这套电池只在提交时跑

```
run_acceptance 的生产调用者: ops/safe_commit.sh   (其余命中全是测试自指)
launchd / cron 调用者:       无
```

运行历史(最近 12 次)按**提交活动**分布, 不按日历:
```
09-12 ×2 | 09-13 | 09-17 ×6 | 09-18 02:30Z | 09-21 10:48Z(本次, 红)
```

**问题**: `tests_disposition_matrix` 的输入是**每天在长的实盘账本**。一个账本事实的回归, 只会在**下一次有人部署时**被发现。本案的潜伏期是 **3 天**(09-18 16Z 首次触发 → 09-21 10:48Z 首次被看见), 而这 3 天没人提交纯属偶然 —— 若下次提交在两周后, 潜伏期就是两周。

**拟议**(待裁定, 未落码): 账本事实类套件(不发任何交易所请求的那些)**每日定时跑一次**, 落收据; 时段避开静默窗 [N+1:00, N+3:40](E-0919-V: 研究侧 fapi 请求与实盘共用每 IP 权重)。
⚠ 需要先普查哪些套件**真的不碰交易所** —— 这是给复审的具名问题 Q3。

---

## §9 给独立研究员的具名问题(请并行排查)

| # | 问题 | 为什么问 |
|---|---|---|
| **Q1** | `deliberate` 应该是**矩阵格的属性**, 还是**尺子的策略**? 我按前者修。反方观点: "故意"是**尺子**关心的事(哪些缺口不该计入执行质量), 矩阵只该陈述事实态。若你认同反方, 修法就要改成"尺子声明它的口径并断言口径覆盖了全部 GAP 格"。 | 这决定修法落在哪一侧, 且**两种修法都能让电池转绿** —— 转绿不构成选择依据 |
| **Q2** | 请**从持仓快照**(不是订单行)独立核对: 09-18 20Z 之后 GUSDT、09-19 16Z 之后 STARUSDT 的仓位是否确为 0? | §5 我只核了订单行。两仪器矛盾先对账 |
| **Q3** | 161 套里哪些**真的不发交易所请求**? 我打算据此提"每日跑账本事实类套件"。 | 按文件名/目录名推断语义是在册错误形态(E-0825-H/G) |
| **Q4** | `0.25 × min(停机锚整书)` 这个分母跨越了 **50 倍的 NAV 量级**(8 月 4,169 vs 9 月 235,320)。即使本案修好, 这条界仍以**全史最小的那本书**为标尺。这是不是下一个会咬人的"钉在瞬时状态上"? | 这个文件自己的注释记录了尺子已被重标定 **5 次**, 每次都是同一族 |
| **Q5** | `skipped_stop_maker_only` 只发生过 **2 次**就出现了一个 2,536 USDT 的残差(占该锚整书缺口的 74%)。样本 2 不足以说"R2′ 一直会在下一锚补上"。需要多少次观测、什么条件下该重开这条裁定? | 单日/单折结论是在册反模式 |

---

## §10 状态与下一步

| 项 | 状态 |
|---|---|
| 实盘代码 | **未改动**, HEAD `409ea16`, 代码区 0 处 diff |
| §4-4 恢复语义(已实现、已过自测) | **待部署, 被本红挡住** —— 不绕过 `safe_commit.sh` |
| 本案修法 | 已拟(§7), **未落码**; 落码后走 `safe_commit.sh`, 电池须全绿 |
| 错题 | 拟登记 **E-0921-G**(矩阵声明性质, 消费者持手写集合 ⇒ 声明不约束消费者)与 **E-0921-H**(账本事实套件只在提交时跑) |

**给复审的并行建议**: Q1 是**先于落码**要定的 —— 它决定修法落在矩阵侧还是尺子侧, 而两种修法都会让电池转绿, 所以**不能用"绿了"来选**。
