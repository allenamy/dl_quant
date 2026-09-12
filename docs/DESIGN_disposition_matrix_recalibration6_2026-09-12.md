> **创建:** 2026-09-12 07:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 事实表先于代码(用户规则); 修复在克隆分支 `fix/disposition-venue-lock-20260912` 落码, 待 safe_commit 电池全绿后合入运行树; 用户字 09-12「确保无误可以更新」 | **作废条件:** E-0909-E 有限上限截断上线(-2027 类应归零, 分母问题随之消失); `order_disposition.gaps()` 的 names 截断被取消(③ 可撤); 研究员复核推翻任一事实行

# tests_disposition_matrix 尺子第六次重标定 — 事实表

## §0 为什么要改
b681ca5 部署前后两次电池(隔离克隆 05:44Z / 运行目录 06:36Z)与旧树 d040c74 同快照上, `tests_disposition_matrix` 三条**真账本**断言逐字节同样红。红不是代码退化, 是账本长到了断言外。但它挡住 `safe_commit`(电池全绿门), 所以必须把尺子按事实重标, **不是放宽**。

## §1 事实表(全部第一手, 运行目录账本 74,383 行 / 249 锚行, 2026-09-12 07:3xZ)

| # | 事实 | 数 | 来源 |
|---|---|---|---|
| F1 | 红断言 1「EVERY steady anchor's INVOLUNTARY gap is small」的违例锚 | **A1789115039**(09-11 08:24Z), involuntary **4,504U** | 套件 payload |
| F2 | 该锚缺口按行分解(gaps() 同一残差算术, 排除 -5022 / -4164) | -4400 补单 **73 行 4,014U** · -2027 PIEVERSE **1 行 2,202U** · no-chase 弃单 **22 行 490U** = gross 6,706 | 原始 orders 行 |
| F3 | 套件 `_split` 的自愿(deliberate)读数 | **0**(应为 490) | `gaps()["names"]` 只留 |残差| 前 20 名(`order_disposition.py` L227), 该锚 96 名, 22 行 no-chase 不在前 20 |
| F4 | ⇒ 真非自愿 = 6,706 − 490 − 2,202 = **4,014 = -4400 意图, 逐 USDT 相等** | |4,014.0 − 4,014.0| < 1 | F2 |
| F5 | -4400 出现过的锚(全账本) | 08-26 20Z A1787775780(REBUILD, 75 行 6,521U)· 08-27 08Z A1787819040(RESIZE, 24 行 425U)· 09-07 04Z A1788755040(REBUILD, 68 行 52,334U)· 09-10 00Z A1788999840(REBUILD, 71 行 72,813U)· **09-11 08Z A1789115039(稳态, 73 行 4,014U)** | 原始行, note 含 `[-4400]`, terminal_reason 全 `abandoned_max_attempts`, leg 全 `topup_taker` |
| F6 | 稳态锚上的锁**只有一例**; 其余四例已被 REBUILD / RESIZE 类(整书尺度的界)接住 | 4/5 | F5 × 套件类定义 |
| F7 | 锁后首个稳态锚 | 09-11 12:24Z A1789129439 involuntary **0** | 套件 payload |
| F8 | 有主: `scheduler/anchor_loop.py` 按相位分页 `场所账户级锁 [-4400](E-0910-A, … 相)` | L1977(开仓相)/ L2406(补单相) | 源码 grep |
| F9 | 红断言 2「VENUE-CAPPED -2027 < 1% own realized gross」的违例锚 | **A1788999840**(09-10 00:24Z, REBUILD): 残差 2,239 vs 1%×realized **154,910 = 1,549** | 套件 payload |
| F10 | 同锚 target(sizing)gross | **232,259** ⇒ 1% = 2,323 > 2,239 | anchors 行 `target_gross` |
| F11 | 全部 21 个 -2027 锚(09-08 12Z → 09-12 04Z, 全是 PIEVERSEUSDT 一名)对 target 1% 的最小余量 | **3.6%**(09-10 00Z), 其余 3.9–82% | 逐锚计算 |
| F12 | `target_gross` 在 anchors 行的覆盖 | 249/249 锚行, 自 A1785565796(08-01)起全有 | 逐行计数 |
| F13 | 红断言 3「SEPARATION: max steady involuntary < 0.25 × min halted gross」 | 4,504 vs 0.25×4,169 = 1,042; 把 F1 锚归入锁类后 max steady involuntary = **425**(08-27 08Z RESIZE 锚的 -4400, 该断言历来不排除 RESIZE) | 套件 payload 前后 |
| F14 | 行法 vs 表法(F3 缺陷)在 23 个 >20 名锚上 | **9 锚不同**(行法 ≥ 表法, 最大 09-07 04Z 4,836 → 9,785); ≤20 名锚上两法一致 | 逐锚计算 |
| F15 | 行法只**降低** involuntary; 套件全部 involuntary 断言都是上界 | 不可能 pass → fail | 断言形式 |

## §2 改法(三处, 各自带承重断言)
1. **VENUE-LOCKED 类**(E-0910-A): `_locked = {traded − rebuild − resize : Σ|-4400 意图| > 0}`。断言 (a) involuntary − lock < 200U; (b) 其后首个稳态锚 < 200U; (c) 源码有主 `[-4400](E-0910-A`。稳态断言、分离断言、`_next_steady_after` / `_next_traded_after` 排除该类。
2. **-2027 分母 = target_gross**(缺则退回 realized; F12 说明永不缺)。1% 与 ≤3 名不变。
3. **自愿部分从行求和**(对 no-chase 行直接调 `gaps()`, 同一残差算术, `gross_usdt` 不截断)。
4. **[G] 承重断言**: 类空 ⇒ 稳态红(命名 A1789115039); 锁 = 非自愿到 1U; 分母换回 realized ⇒ 09-10 00Z 红且换 target 全过; 行法 vs 表法在 >20 名锚上必不同、≤20 名锚上一致(容差 1e-2 = gross_usdt 四位小数舍入)。

## §3 验证(克隆 `exec_b681_acceptance`, 05:43Z 真 state 快照, HEAD b681ca5 + 本补丁)
- 修后套件: 见 §4 收据行。
- 突变(红能力, 临时副本): `_LOCK_CODE → -9999` / 分母换回 realized / 自愿改回表法 —— 各自必须红, 且红在预期的那条。
- 不触实盘树; 落地经 `ops/safe_commit.sh`(fetch → 电池全绿 → commit → push), 窗 09:36–09:59Z(避锚小时与 HH:20–35)。

## §4 收据(落地时补)
