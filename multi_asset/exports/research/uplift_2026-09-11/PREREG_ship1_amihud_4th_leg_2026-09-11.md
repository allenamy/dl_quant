> **创建:** 2026-09-11 | **Session:** round-5 SHIP-1 (research/book-uplift-2026-09-11, 未提交) | **状态:** 预注册, 未裁定, 未改任何在役件(`~/dl_quant_live` 与 `~/wide_shadow` 本轮全程只读, 已核无写入) | **作废条件:** (a) 用户裁定 ADMIT/REJECT; (b) v4 口径链被 v5 取代; (c) §B1 或 §B2 所依据的在役代码事实被修改或证伪; (d) 运行树从 d040c74 换代(§0.3)

# PREREG SHIP-1 — a=0.20 正交 Amihud sleeve 作为**第四条固定配额腿**

**上游**: `PREREG_p6_amihud_sleeve_2026-09-11.md`(位级复现前提 + 回放证据 + 生产者侧 diff)。
**本文新增的**: 两个风险侧拦路虎的**代码事实与最小修复**(§B1/§B2), 三把本轮新跑的尺子(§3), 以及裁定要读的冻结门(§4)。
**本文不改任何东西。** 提议的 diff 在 `PROPOSED_DIFF_ship1_executor_risk_scale_2026-09-11.txt`(执行器侧)与 `PROPOSED_DIFF_p6_amihud_producer_2026-09-11.txt`(生产者侧); 测试件在 `ship1_patch/tests_producer_risk.py`。

---

## 0. 口径钉 + 前置门

### 0.1 钉

| 项 | 值 | 标签 |
|---|---|---|
| 立方/面板 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz`, `wide_fea_v4_meta.npz`(轴 10182), `/workspace/dlw_v4raw/data/*`(RAW, 轴 10212) | 钉 |
| 装置 | `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` | VERIFIED (`sha256sum`, 本轮实测) |
| 成本 | `r3k/costb_PWR_G230k.json` sha256 `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`(fitted, K=0.17) | VERIFIED (本轮 `sha256sum`) |
| 零假设装置 | `r3_attack_b9646/null.py` sha256 `91d4c91cb92a64404f8e635a76969b435b86ab7840fc110564d9509a1b0c7fa9` | VERIFIED |
| 尾部尺子 | `r3_gates/rs_conc.py` sha256 `3fd2f76496a593ba5342bbf8dd21d9f52473a52fe55657b7592f30d06143ab11` | VERIFIED |
| 旗标 | CAL=log, CRYPTO m1 掩码, MEMBERS_TOPN=829, LEGS=101, PHI=0.45, LOOK=900, WRULE=msharpe, FTRIM=zero(A0 侧) | 钉 |
| 窗 | FULL post-warm: 丢前 900 个 device 锚, 截至 2026-08-10 20Z, **n=9018**, SE(Sharpe)=0.4928; 冻结窗 n=3168, SE 0.83 | E-0911-A |
| 统计量 | g = net_ex/gross_total, bps/锚/单位 gross; 逐锚配对; UTC-日 block bootstrap 2000, `default_rng([20260905,k])`, k∈{0,9} | 钉 |

**记账定义(逐字从装置读, 不从文档读)**: `w10_sleeve.py` L372-374 ⇒ `net_ex = pnl_ex − carry_ex − cost_ex`。**carry_ex 为正 = 付费率**。

### 0.2 GATE P —— 本轮**重跑**, 不引用上一轮的收据

装置 knobs-off 必须逐位重现归档 A0 四格。**我没有复用 round-4 的 `p6/gateP` 缓存**: 换了新 ROOT(`ship1/gateP`), 四格全部真跑(`rc=0`, 27–29 s), 不是 `cached`。

| 格 | `d30_n2_c42_rec` | `d30_n2_c42_W` |
|---|---|---|
| dyn s42 | bitwise **true**, maxabs 0.0, shape (10039,23) | bitwise **true**, maxabs 0.0, shape (10039,829) |
| dyn s2027 | bitwise **true**, maxabs 0.0 | bitwise **true**, maxabs 0.0 |
| fix s42 | bitwise **true**, maxabs 0.0 | bitwise **true**, maxabs 0.0 |
| fix s2027 | bitwise **true**, maxabs 0.0 | bitwise **true**, maxabs 0.0 |

`PASS: true`。收据 `/workspace/uplift_2026-09-11/ship1/gateP/GATE_P_ship1.json`。
复跑命令**逐字**: `ssh pod2 '/workspace/venv/bin/python /workspace/uplift_2026-09-11/ship1/gateP_ship1.py'`。

### 0.3 ★ env 白名单(E-0826-D: round-3 因漏 `V2=1` 训了另一个对象, 值 −0.219 Sharpe)

装置自身读的 env 全集(`grep environ` 于 `w10_sleeve.py`, 32 个):
`CAL CDAMP COSTB_JSON FEMAT_NPZ FPRED FSEED FTPOS FTRIM FTRIM_TH FUNDSCALE KMOD KMOD_AGREE KMOD_F10 KMOD_L KTAIL LEGS LOOK LTRIM_TH MEMBERS_TOPN OUT_TAG PHI REF_SKIP RNSM SEATF10 SEATNET SLEEVE SLOW_NPY TRADE_TOPN UMASK_NPZ UMASK_SCOPE W3FIX WRULE`

**本轮我的跑所 SET 的 env, 全部列举并断言**:
`CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 UMASK_NPZ=<…/umask_UPIT_CRYPTO.npz> LEGS=101 FTRIM=zero PHI=0.45 SLOW_NPY=<…/SLOW_v3_on_v4axis.npy> FSEED={42,2027} FPRED=f10_A0_s{42,2027}.npy COSTB_JSON=<见上> OUT_TAG=<每跑唯一> OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4`。
未列出的 14 个装置 env **一律未设**, 走装置默认。装置把 `_CFG` 写进产物 `config_json`; 裁定时应读产物自报而不是读本表。

### 0.4 运行树

在役执行器运行树 = `d040c74`(VERIFIED: `git -C ~/dl_quant_live rev-parse --short HEAD`)。`origin/main` = `b681ca5`, **领先 19 提交且未部署**(STATE.md 09-11 04Z/08Z 行)。§B1 的 diff 的每一行上下文都是对着 **d040c74** 取的。**若用户先部署 b681ca5, 本 diff 必须重新取一次上下文再施加** —— 跨树打补丁是已登记的错误形态。

---

## A. 结论先行(给裁定看的三句)

1. **这是全纲领唯一一个逐折配对 CI 下界四格全过零的改进**: A0 **1.4150** → 组合 **1.6608**, 配对 ΔSharpe **+0.2458 / +0.2407**, CI95 下界 **+0.0336 / +0.0319 / +0.0315 / +0.0305**(2 种子 × 2 bootstrap 种子, 4/4 > 0)。
2. **它买的是波动, 不是收益**。八格(a∈{0.20,0.30,0.40,0.50} × 种子{42,2027})的 **Δg 全为负**, a=0.20 上是 **−0.00252 / −0.00581** bps/锚/单位 gross ⇒ 在 gross=2.0×NAV 与 2190 锚/年下 = **−11.0 / −25.5 bps/年 NAV**(NAV 116,220 时 ≈ **−128 ~ −296 USD/年**)。若 gross 永远被政策钉在 2.0, 这笔交易在纯收益口径上是**亏的**。
3. **它不把书送到 3.0**。"显著高于 3.0" 需要点估计 3.966, 距 A0 是 5.18 SE; 本提案只走 0.50 SE。**任何把本案说成"迈向 3.0"的表述都是错的。**

---

## B. 两个风险侧拦路虎 —— 事实、最小修复、失败形态

### B1 — 执行器把生产者写的 gross 除掉了, 所以"降级 = 少跑"根本表达不出来

#### B1.1 gross 的完整流向(逐行读在役码, 全 VERIFIED)

| 位置 | 代码 | 效果 |
|---|---|---|
| `live/external_book.py:483-490` | `gn = float(ext.get("gross_in") or ext["gross_norm"]); return np.array([w.get(s,0.0)/gn for s in symbols])` | **无条件**除掉生产者的 gross; 返回向量 `sum|·| == 1` 恒成立 |
| `scheduler/anchor_loop.py:1490` | `book["target_w"] = EXT.target_vector(external, symbols)` | 书 = 那个单位 gross 向量 |
| `anchor_loop.py:1588-1602` | `_g,_ginfo = sigma_ladder.load()`; `_size_book(target_leverage = external["gross_mult"] * _g)` | 杠杆 = 配置常数 × 阶梯 g |
| `anchor_loop.py:1129-1198` | `gross = nav × target_leverage`(带死区与地板) | 名义额 |
| `anchor_loop.py:1618` | `target = LG.to_notional(book["target_w"], symbols, self.gross)` | 下单目标 |

⇒ **实盘 gross = NAV × gross_mult × g_sigma**。生产者写什么 gross 都会被一次除法抹掉。一个只算出半本书、或 sleeve 静默变 NaN 的生产者, 会被执行器**重新加满杠杆**。**"run me smaller" 在 `wide_target_v1` 里不可表达** —— 这是本轮最重要的操作发现, 已在 round-4 P6 §3.3 首次记下, 本轮逐行复核成立。

#### B1.2 复用 sigma_ladder 通道: 我评估过, 它输在四点(三点是今天实测的)

先说它对的地方: **算术是对的**(`target_leverage = gross_mult × g`, 一次乘法, 说的是杠杆政策自己的单位), 失败方向是对的(任何缺陷 → 1.0, 绝不产生我们没决定的减仓), 模块形状是对的(纯 `evaluate()` + 一个 loader), S4 契约是对的(默认路径与改前逐字节相同)。**这四样我全部复用。只有那个文件我拒绝复用。**

| # | 反对理由 | 证据 |
|---|---|---|
| (a) | **一个文件两个写者**。仪表盘侧写者 `/Users/haosiyu/regime_dash/sigma_ladder.py` 与它的任务 `com.hsy.sigma_ladder.plist` **都在这台机器上**。生产者若也写 `state/live/sigma_ladder.json`, 两个独立作者在一条路径上竞争, 后写者赢, 各自静默抹掉对方的风险决定 | VERIFIED: 两个文件都存在 |
| (b) | **白名单不对**。`sigma_ladder.ALLOWED_G == (0.5, 1.0)`。降级到 0.8 会被**拒绝** ⇒ g=1.0 ⇒ 满仓。改宽它, 等于顺手改掉 σ 阶梯自己的预注册契约 —— 一个补丁两个裁定 | VERIFIED: `live/sigma_ladder.py` L11 |
| (c) | **写入方向被倒置**。生产者今天**不往 `~/dl_quant_live` 写任何东西**(`grep -rn dl_quant_live ~/wide_shadow/*.py` 只命中对 pilot_log 的**读**与一次 `sys.path.insert`)。是执行器伸手去读生产者的树, 不是反过来。`tests_scoped_writes.py` 就是为写作用域越界而存在的 | VERIFIED |
| (d) | **`missing` 是静默的, 而且这条通道的全部历史就是这个形态** | 见 B1.3 |

#### B1.3 ★ σ 阶梯从来没有被打开过 —— 这不是先例, 这是**同一个缺陷的现场**

| 事实 | 收据 |
|---|---|
| 消费者存在且被在役循环调用 | `anchor_loop.py:1590` |
| 消费者的电池存在且在 SUITES 里 | `run_acceptance.sh:55` |
| 写者脚本存在 | `/Users/haosiyu/regime_dash/sigma_ladder.py`(3140 B, 2026-09-04) |
| 写者的 launchd 任务文件存在(6 个锚 :52 触发) | `~/Library/LaunchAgents/com.hsy.sigma_ladder.plist` |
| **写者从未运行过** | `launchctl list \| grep hsy` **不含** `com.hsy.sigma_ladder`; 且 plist 声明的 `StandardOutPath`/`StandardErrorPath`(`sigma_ladder.log` / `.err`)**两个文件都不存在** —— launchd 首次运行就会创建它们 |
| **消费者的状态文件不存在** | `state/live/` 下只有 `sigma_ladder.json.reserve_20260904`, 没有 `sigma_ladder.json` |
| **所以 g 恒等于 1.0, 且一声不吭** | `sigma_ladder.evaluate(None) → (1.0, reason="missing")`, 而 `anchor_loop.py:1595` 的 elif **显式把 `"missing"` 排除在告警之外** |

**读法**: 这个项目已经**造好、接线、写了电池、装了 plist**, 然后让它在"缺文件 ⇒ 满仓 ⇒ 无告警"的状态下运行了 7 天。本案若把降级路径接到同一形状上, 就是第三次重演。**所以 §B1.4 的设计里, "沉默地回到满仓"必须有行为签名。**

#### B1.4 最小修复(建议): 在执行器**已经校验的那个文件**里加一个可选字段

`wide_target_v1` 增加**一个**可选字段 `risk_scale`。它搭在 target 文件里, 因此**零成本继承**该文件已有的全部保护: sha256 sidecar 校验、`anchor_ts == 本锚`、`written_utc` 新鲜度(`max_age_min=10`)、producer 前缀检查、以及既有的陈旧阶梯。**一个陈旧的风险决定 = 一个陈旧的 target**, 而那已经被检测、已经 HIGH 告警、已经驱动预注册的 HOLD 阶梯。这就是它该放这里而不是放第二个文件的全部理由。

五条设计刀口(逐条都有反面教训):

1. **应用点是 `target_leverage`, 不是权重向量。** `target_vector` 一行不改, 向量继续 `sum|·|==1`。若把 scale 藏进向量, `min_notional` 的 `mass_frac`、`reshape.gross_before`、`net_over_gross` 三个口径同时失真, 而 `self.gross` 会变成一句关于实际书的假话 —— 「测量被误解的量」。
2. **白名单是离散的** `{1.0, 0.8, 0.5}`。连续字段会让生产者的一个算术 bug 写出 0.003 或 4.0 并被相信。
3. **畸形值拒掉整个文件, 不强制归一。** 一个试图谈论风险却说错了的生产者, 是我们不信任它来定书大小的生产者; 既有的 `on_unavailable="hold"`(保持现仓 + HIGH 告警)才是诚实答案, 而且它已经写好、已经有电池、已经预注册。**把畸形的风险声明强制成"满仓"正是 `missing` 消失的方式。**
4. **`risk_scale < 1.0` 报 HIGH, 不是 INFO。** 生产者在真钱运行中告诉你它坏了。
5. **schema 回归守卫。** 一旦某个生产者声明过 `risk_scale`, 之后不再声明的文件**不是**"没什么要说的生产者", 而是"丢了那条代码路径的生产者", 它会**沉默地 fail-open 到满仓且没有任何行为签名**。所以在 `loop_state` 里记 `external_risk_scale_seen`, 由声明变不声明 ⇒ HIGH 告警。这一条就是对 B1.3 的直接回答。

**Blast radius**: `external_book.py` 一个纯函数 + `parse_target` 两处(一次校验、返回加三个键)+ 一段 docstring 警告; `anchor_loop.py` 一次读、一次乘法、两条告警、一个 state 键; `config/book.json` 一个白名单 + 说明; 三件套。**`risk_scale` 缺省时全链与今天逐位相同**(与阶梯当年用的同一个 S4 契约形状)。

**FM7(必须写在裁定书上)**: `_size_book` 在 `NAV × target_leverage` 低于曝险地板时返回 `halt=True`, 裁定是「低于地板我们停, 不缩」。`risk_scale=0.5` 把 `target_leverage` 减半, **可以踩到那个地板** ⇒ 降级的 sleeve 会升级成 **HALT** 而不只是变小的书。这是设计内的(半本宽书正是那条款所写的"广度已失的浓缩残渣"), 但它必须被说出来, 也是白名单止步于 0.5 而不往下走的理由。

#### B1.5 失败形态表(B1)

| # | 形态 | 今天的行为 | 打上补丁后的行为 | 谁看得见 |
|---|---|---|---|---|
| FM1 | 生产者算出半本书(sleeve NaN), 照写 target | 执行器除掉 gross, **满仓跑半本书**, 无信号 | 生产者写 `risk_scale=0.8` ⇒ 目标 gross ×0.8, **HIGH 告警**带 `risk_reason` | Telegram(在役已投递) + anchors 行 `producer_risk` |
| FM2 | 生产者写了畸形 `risk_scale`(0.003 / "0.8" / NaN) | — | `parse_target` **拒整个文件** ⇒ 既有 HOLD 路径 + HIGH | 同上 |
| FM3 | 生产者曾声明、本锚不再声明 | — | `external_risk_scale_seen` ⇒ **HIGH 告警**, 本锚按 1.0 满仓 | 同上 |
| FM4 | 生产者根本没升级(老码) | 今天的行为 | **逐位相同**, `reason="absent"`, 无告警 | — |
| FM5 | target 文件本身陈旧/缺失 | 已检测: HIGH + HOLD 阶梯 | **不变**(这正是把字段放进 target 文件的收益) | 已在役 |
| FM6 | 有人篡改 target 文件加 `risk_scale=0.5` | — | sidecar sha 不匹配 ⇒ 文件被拒 ⇒ HOLD + HIGH | 已在役 |
| FM7 | `risk_scale=0.5` 把 gross 压到曝险地板以下 | — | `_size_book` 返回 halt ⇒ **CRITICAL + 停开仓** | 已在役 |
| FM8 | `risk_scale` 写对了但生产者**根本没发现自己坏了** | — | **仍然满仓**。补丁**不覆盖**这一格 | **无人看见** ⇒ 只能由 §C4 降级演练覆盖, 而演练是人工纪律, 电池里没有断言 |

**FM8 是这个补丁的真实边界**, 它已写进 `gate_coverage` 的盲区条目里(见 diff §2 的 `(b)`)。

#### B1.6 三件套(在役电池的硬规矩)

| 件 | 去处 | 状态 |
|---|---|---|
| 测试文件 | `~/dl_quant_live/live/tests_producer_risk.py` | **已写**, 在 `ship1_patch/tests_producer_risk.py` |
| SUITES 条目 | `run_acceptance.sh` L55 之后一行 | 在 diff 里 |
| 盲区条目 | `ops/gate_coverage.py` `SUITE_SCOPE["tests_producer_risk"]`(5 条盲区) | 在 diff 里 |

**测试件已被实测为"对着未打补丁的树是红的, 且红在正确的理由上"**: 逐字命令
`cd <…>/ship1_patch && PYTHONDONTWRITEBYTECODE=1 DL_QUANT_LIVE_LIVE=/Users/haosiyu/dl_quant_live/live /usr/bin/python3 tests_producer_risk.py`
⇒ `EXIT=1`, 9 checks, 第一条失败是 `0a external_book.parse_risk_scale exists — UNPATCHED TREE`。
(该跑**没有向真钱仓写入任何东西**: `sys.dont_write_bytecode=True` + `PYTHONDONTWRITEBYTECODE=1`; 跑后 `find ~/dl_quant_live -newermt "2026-09-11 21:00" -not -path "*/.git/*" -not -path "*/state/*"` 为空。)

---

### B2 — 没有任何东西读生产者的心跳, 所以 fail-safe 告警是一个没人看的标记

#### B2.1 现状(全 VERIFIED)

| 生产者写什么 | 谁读 | 读了以后会发生什么 |
|---|---|---|
| `~/wide_shadow/heartbeat.json`(`{last_anchor, utc, coverage, status}`) | **`~/dl_quant_live` 里没有任何代码读它**(全仓 grep `heartbeat` 只命中 `live/telegram_notify.py:292` 自己的 token 自检 + 它的测试) | 什么也不会发生 |
| `~/wide_shadow/state/combo_live_status.json`(`{anchor, ok, step, n, gross, reader_ok, age_s, …}`) | **唯一消费者 = `ops/anchor_report.py:50`** | `if not (S.get("ok") and S.get("reader_ok")): warn.append(...)` ⇒ 进报告的 ⚠ 行 |
| `~/wide_shadow/shadow_log.jsonl` 的 `e=="signal"` 行 | `ops/anchor_report.py`(`fund_updates`/`coverage`/`forced_exit_n`) | 同上 |
| `state/target_live/<anchor>.json` | `external_book.read_target`(sha + anchor + 新鲜度) | **会改变行为**: 缺/坏 ⇒ HOLD + HIGH + 陈旧阶梯 |

**好消息(比 round-4 记的更好)**: `com.hsy.anchor_report` **是加载着的**(`launchctl list` 有它), 6 个锚的 :55 触发, 结果打 Telegram(`state/anchor_report.log` 末尾 `[sent]`)。所以**存在一条每 4 小时到人的通道**。
**坏消息**: 它是**报告**, 不改变任何行为; 而且它对 sleeve 一无所知 —— 今天 `ami` 变 NaN, `combo_live_status.ok` 仍然是 `true`, `reader_ok` 仍然是 `true`, 报告照样 ✅。

#### B2.2 "sleeve 输入陈旧或缺失"今天会不会被发现? —— 分三种, 两种不会

| 场景 | 今天会被发现吗 | 靠谁 |
|---|---|---|
| 生产者整个死了(不写 target) | **会** | `external_book` 缺文件 ⇒ HIGH + HOLD(`notify_audit.jsonl` 有实例: "external_book_unavailable: missing … 本锚 HOLD") |
| 生产者活着但**慢**(落盘超过 `max_age_min=10`) | **会** | `parse_target` 的 `stale` 分支 |
| **生产者活着、按时落盘, 但 sleeve 那一项静默变 NaN** | **不会** | 谁都不会。`shadow_loop_v3.py:471` 的 `np.nan_to_num` 把该项变成 0 向量, 随后 L482 `w /= g` 把书重新归一到 gross 1 ⇒ **sleeve 静默消失, 其余三腿被放大回满仓, 无任何告警**。这与 σ 阶梯的 `missing` 是同一个形态 |

#### B2.3 最小消费者(把"sleeve 输入陈旧"变成真的会改变行为或被人看见的东西)

**不要新造守望者。** 本项目已登记 [守望者静默死] 与 [handback 静默死] 两种形态; 一个新进程本身就是一个新的静默死点。用**已经在跑、已经有人看、已经会改变行为**的两条通道:

**(i) 行为通道(真正改变风险) = §B1.4 的 `risk_scale`。**
生产者在 sleeve 降级的那一锚写 `risk_scale=0.8` + `risk_reason="ami_prev missing"` + `sleeve_alloc=0.20`。执行器 ⇒ 目标 gross ×0.8 + **HIGH 告警**。这不是标记, 这是仓位。

**(ii) 人眼通道(零新进程) = `ops/anchor_report.py` 加三行。**
它已经在读 `combo_live_status.json` 与 `shadow_log.jsonl`, 已经 6×/天 发 Telegram。加:
```
if S.get("ami_status") not in (None, "OK"): warn.append(f"AMI sleeve {S.get('ami_status')}")
if (m.get("sleeve_alloc") or 0) and eb and eb.get("risk_scale", 1.0) < 1.0:
    warn.append(f"生产者自报降级 risk_scale={eb.get('risk_scale')}")
if (m.get("ami_cov_lt_min") or 0) > 0.02: warn.append(f"AMI 覆盖门 {m.get('ami_cov_lt_min'):.3f} >2%")
```
(`ops/anchor_report.py` 是 `~/dl_quant_live` 的文件 ⇒ 同样只能经 `ops/safe_commit.sh` 改, 同样在本文里只是提议。)

**(iii) 诚实声明 —— 这条不许删。**
即便 (i)+(ii) 都上, **FM8 仍然开着**: 一个"坏了但不自知"的生产者会写 `risk_scale=1.0`, 三条通道全绿。唯一能碰到 FM8 的是 §C4 的**降级演练**, 而演练是人工纪律, 电池里没有断言。**"静默 fail-safe 到满仓"本身就是本项目已经记录两次的缺陷形态**(σ 阶梯造好接线从未打开; 其缺文件 ⇒ g=1.0 且无告警), 本案只把它从"无签名"改成"有签名但仍需人工演练"。**它没有被关闭, 只是被缩小了。**

---

## C. 部署形态与第一锚

### C.1 "第四条腿"是什么意思(必须先说清, 否则会做错)

用户的话是"作为第四条腿"。**按固定配额做, 不要按 msharpe 席位做。** 理由(round-4 P6 §2.1, 本轮复核成立):
生产者 L525-533 的 `w3 = shp/shp.sum()` 由三腿 900 锚的 msharpe 决定, 不足 900 锚时退化成 `[1/3]×3`。加第四条 msharpe 腿 ⇒ 前 900 锚(**150 天**)退化成 `[1/4]×4`, 新 sleeve **一上来就拿 25% 的书且零证据**; 而回放里我们把这 900 锚**丢掉不读**(E-0911-A), 实盘却要真金白银走过去。若改成从回放回灌 `LR` 历史, 那是「回放席位路径 ≠ 实盘席位路径」。

**形态 = z 合成处一行固定配额**:
```
z3 = w3[0]*legz["king"] + w3[1]*legz["rev24"] + w3[2]*legz["fund"]   # 不动
z  = (1 - AMI_ALLOC) * z3 + AMI_ALLOC * xz(ami_orth)                 # 新增, AMI_ALLOC 默认 0.0
```
`AMI_ALLOC=0.0` 时全链逐位不变。裁定通过才改 0.20。

### C.2 信号本体(逐字, 否则不是被检验的那个对象)

```
ZF  = xz_rows(f_fund_ema_v1)                    # scipy.stats.rankdata, AVERAGE ranks
ZA  = xz_rows(amihud_24h)                       # amihud_24h = |Σ288 ch0| / Σ288 expm1(clip(ch3,0,30)) × 1e6
ZAL[t] = ZA[t-1]                                # 一锚滞后, 是信号定义的一部分, 不是保守处理
b   = Σ(ZF·ZAL)/Σ(ZF·ZF)                        # 逐锚无截距 OLS
sig = ZAL − b·ZF
```
两处刀口: (1) RANK **必须** `scipy.stats.rankdata`(AVERAGE), 绝不 `argsort(argsort(·))` —— `f_fund_ema_v1` 在 10039 行里有 9031 行存在并列; (2) 滞后量必须持久化到 `state/ami_prev.json`, 否则重启后首锚没有它。

### C.3 回滚

`ami_alloc` 从 0.20 改回 **0.0** ⇒ 下一锚逐位回到今天的书。不需要回滚 `rolling.npz`, 不需要重启执行器, 不需要碰执行器。执行器侧的 `risk_scale` 补丁在生产者不写该字段时**逐位无操作**, 因此**可以先于生产者改动单独部署**(它是 inert 的), 这也是本案建议的上线顺序。

### C.4 首锚检查(缺一条就回滚)

| # | 检查 | 门 | 不过怎么办 |
|---|---|---|---|
| C0 | `ami_alloc=0.0` 跑一个历史锚, 权重向量与旧码**逐位相等**(`tests_target_live_output.py` 新断言, `np.array_equal` 不是 `allclose`) | bitwise | **不上线** |
| C1 | 当锚生产者的 `ami[m]` vs 用归档立方按 §C.2 recipe 算的值: 报逐锚 Spearman + 位级相等比例 | Spearman ≥ 0.999 | 只告警不回滚(跨数据源差), 进当日日志 |
| C2 | `ami_prev.anchor_ts == anchor − 14400` | 相等 | 该锚 `ami_alloc=0` + 告警 |
| C3 | `frac(cov288 < 0.95)` 于成员集 | 回放基线 0.129%; >2% 告警 | 告警 |
| C4 | **降级演练(硬门)**: 人为把 `ami` 置空跑一次影子(不落 target_live), 确认 (a) `e=ami_degraded` 进日志, (b) `combo_live_status.ami_status=="DEGRADED"`, (c) **`risk_scale` 真的写进了 target 文件**, (d) 执行器**真的**报了 HIGH 且 `_last_sizing.target_leverage` 真的 = `gross_mult × g × 0.8`, (e) 权重向量等于 `ami_alloc=0` 的向量 | 五条全响 | **没响 = 不上线** |
| C5 | `target_live.gross_norm` 与上一锚之比 ∈ [0.9,1.1] | — | 仅生产者侧自检; **提醒: 执行器会把它除掉, 这不是风控** |
| C6 | 当锚换手相对上一锚 ≤ +40% | 回放 sleeve 比 A0 高 **+27.4%**(0.038706 vs 0.030372, 两数同为本轮自算) | 告警 + 当日复看 |

---

## D. 冻结验收门 —— **裁定按这个读, 先于任何新数字**

**对象**: A0(在役形态)与独立 Amihud sleeve 的固定配额组合, **a = 0.20**(不是 0.50; 见 §E.2 —— 这颗钉子在 round-4 就钉死了, 本轮不再搜 a)。
**成本**: `costb_PWR_G230k.json`(fitted, K=0.17)。**不是**部署成本模型, 不是 K=1。
**窗**: FULL post-warm n=9018 **与** 冻结窗 n=3168, 两个都要报。
**种子**: 42 与 2027, 配对必须同种子。
**K 与 Bonferroni**: 本文只提一个对象、一个配额 ⇒ **K=1**, 不做额外校正; round-3 的 repaired-placebo 家族校正 K=12 已在 §3.3 单独报。

| 门 | 判据 | 现状 |
|---|---|---|
| **G0** | **合成书必须真的被跑过一次**: sleeve 接进装置的 z 合成(第四项固定配额), 重跑 GATE P, 得到一条**书**的逐锚序列, 而不是两本书在 g 层的线性组合 | **今天 FAIL**。§E.4 |
| **G1** | FULL post-warm 配对 ΔSharpe **CI95 下界 > 0**, 2 种子 × 2 bootstrap 种子 **4/4** | **PASS** (+0.0336/+0.0319/+0.0315/+0.0305) |
| **G2** | 冻结窗 ΔSharpe 点估计 > 0, 且 4 格中 **≥3 格**下界 > 0 | **边缘 PASS 3/4**(s2027 k0 下界 −0.0046) |
| **G3** | FULL post-warm 的 **Δg 点估计 ≥ −0.010** bps/锚/单位 gross(门必须显式承认它是负的) | **PASS**(−0.00252 / −0.00581) |
| **G4** | 位级不变门 C0 通过 | 未做(需生产者侧改动落地) |
| **G5** | fail-safe 走 §B1.4 + §B2.3, **且 C4 演练五条全响过** | **今天 FAIL**(补丁未施加) |
| **G6** | 尾部集中度: top-20 份额与 ex-top-20 Sharpe 不得呈 RESID_SHARPE 形态(份额 >100% 且 ex-top-20 Sharpe < 0) | **PASS**, §3.1 |
| **G7** | 换手匹配零假设(SHIFT/RELAB/T 族)**逐族 pooled** margin_net CI95 下界 > 0, FULL 窗 | **PASS** FULL; 冻结窗 **只 SURVIVES_NOMINAL**, §3.3 |

**REJECT** 若: G1 任一格下界 ≤ 0, 或 G3 破 −0.010, 或 C0 不逐位相等, 或 G6 呈 RESID_SHARPE 形态。
**今天的整体状态 = NEAR_MISS**: 统计门(G1/G2/G3/G6/G7-FULL)已过, **工程门 G0/G4/G5 未过**。这不是"再跑一个实验"能解决的, 是要先把代码写上去。

---

## E. 它到底买到什么、代价是什么(诚实版)

### E.1 收益

post-warm n=9018, fitted 成本 G=230k:

| | seed 42 | seed 2027 |
|---|---|---|
| A0 Sharpe | **1.4150** | 1.4370 |
| sleeve 独立 Sharpe | 1.4721 | 1.4721 |
| ρ(A0, sleeve) FULL | **+0.1490** | +0.1553 |
| ρ 冻结窗 | −0.0124 | +0.0292 |
| **组合 a=0.20** | **1.6608** | **1.6777** |
| 组合 a=0.20 冻结窗 | 3.2647 | — |
| 组合 a=0.50 | 1.9028 | 1.9122 |

**"1.42 → 约 1.90" 只在 a=0.50 上成立, 而 a=0.50 的配对 ΔSharpe CI 含 0(P(Δ>0)=0.93)。能过门的 a=0.20 买到的是 +0.246 Sharpe。**

### E.2 为什么是 0.20 而不是 0.50(钉子先于数字)

| a | ΔSharpe(s42) | FULL CI95 k0 | 冻结 CI95 k0 | Δg(s42) |
|---|---|---|---|---|
| **0.20** | **+0.2458** | **[+0.0336, +0.4587]** | [+0.0180, +0.6523] | −0.00252 |
| 0.30 | +0.3591 | [+0.0195, +0.7016] | [**−0.0381**, +1.0263] | −0.00377 |
| 0.40 | +0.4456 | [**−0.0356**, +0.9313] | [−0.1961, +1.3918] | −0.00503 |
| 0.50 | +0.4878 | [**−0.1449**, +1.1253] | [−0.4642, +1.6653] | −0.00629 |

a=0.20 过 G1(4/4) 与 G3; a=0.30 过 G1 但冻结窗 0/4; a≥0.40 连 G1 都不过。**配额是 0.20。本轮不再搜 a。**

### E.3 代价 —— 逐笔算给你看

**八格 Δg 全为负**(a∈{0.20,0.30,0.40,0.50} × 种子{42,2027}): −0.00252, −0.00377, −0.00503, −0.00629(s42); −0.00581, −0.00872, −0.01163, −0.01453(s2027)。符号一致性 **8/8**。

a=0.20 的年化让利, 换算链逐字写出(E-0904-G: 换算链必须脚本化/写出, 不许心算):
```
Δ收益/年(bps of NAV) = Δg [bps/锚/单位 gross] × 2190 [锚/年 = 6×365] × 2.0 [gross/NAV]
  s42  : −0.0025163 × 2190 × 2.0 = −11.02 bps/年
  s2027: −0.0058134 × 2190 × 2.0 = −25.46 bps/年
NAV = 116,220 USD(STATE.md 2026-09-11 12Z 锚) ⇒ −128.1 USD/年 ~ −295.9 USD/年
```
**但**: Δg 的 CI95(s42,k0)是 [−0.1194, +0.1204] ⇒ ±523 bps/年。**这笔让利的"符号"是稳的(8/8), "大小"完全测不出来**。正确读法是: sleeve 不是来赚钱的, 是来降波动的; 在 gross 被政策钉死 2.0× 的世界里, 它**用一点点(测不准的)钱换夏普**。若将来能按夏普再加杠杆, 这笔交易划算; 若 gross 永远 2.0, 它在纯收益口径上是亏的, 买的是回撤。

**carry 侧(本轮自算, 定义取自装置 L372)**:

post-warm n=9018, fitted 成本(A0 一侧是**我本轮自己重跑**出来的, 见下方对账):

| | sleeve (s42=s2027) | A0 s42 | A0 s2027 |
|---|---|---|---|
| Sharpe(g) | 1.4721 | **1.4150** | **1.4370** |
| `pnl_ex` bps/锚 | 0.569102 | 0.845319 | 0.856821 |
| `carry_ex` bps/锚(正=付) | **−0.035796(收)** | +0.354918 | +0.351753 |
| `cost_ex` bps/锚 | 0.123202 | 0.094746 | 0.095712 |
| `net_ex` bps/锚 | 0.481696 | 0.395655 | 0.409356 |
| **carry / net** | **−7.43%** | **+89.7%** | **+85.9%** |
| 换手/锚 | 0.038706 | 0.030372 | 0.030705 |
| \|netlong\| 均值 | 0.0513 | 0.037714 | 0.038953 |
| nsel | 251.08 | 251.08 | 251.08 |

**★ 第四个对账点**: 我用**自己的 GATE-P dev 树**、装置未改、只把 `COSTB_JSON` 换成钉住的 fitted 模型重跑 A0 两个种子, 读出 **1.4150 / 1.4370**, n=9018 —— 与钉住的 round-3 值**逐位一致**, 且 `carry_ex` 0.354918 / `cost_ex` 0.094746 / `turnover` 0.030372 与 round-4 P6 §2.4 表**逐位一致**。收据 `/workspace/uplift_2026-09-11/ship1/SHIP1_A0_accounting_PWR.json`; 逐字命令 `ssh pod2 '/workspace/venv/bin/python /workspace/uplift_2026-09-11/ship1/a0pwr.py'`。

**读法**: 这是本案一个被低估的正面证据。在役 A0 的净额里 carry 占 **86–90%**, 而 sleeve **净收** carry(占其净额 **−7.4%**)。这与害死 LOB sleeve 家族的形态(50–102% 来自 carry)完全相反 —— sleeve 加进来是在**稀释**书对 carry 的依赖。

### E.4 逐年(seed 42, fitted 成本)

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| A0 | 0.480 | **−1.936** | 1.088 | 1.187 | 5.433 |
| sleeve 独立 | 0.168 | **+1.861** | 1.197 | 1.379 | 2.407 |
| 组合 a=0.20 | — | **−1.237** | 1.239 | 1.408 | 5.944 |

**sleeve 的全部卖点在 2023(A0 的死年)。** 2022 它自己只有 **0.168** —— "它有 2022"字面为真, 但 0.168 不是证据, 只是不为负; 而且 2022 前 900 锚按 E-0911-A 已被丢掉。**组合在 2026 是被 A0 抬起来的**; 若 2026 的 A0 表现本身是 regime rent(冻结窗付 2.07× 跨 regime 均值), 那么正常 regime 下组合的样子更接近 2023–2025 那三年, 而不是这张表的加权平均。

---

## 3. 本轮新跑的三把尺子(round-3 的门修复, 从第一根臂就用)

### 3.1 尾部集中度尺(`rs_conc.py` 口径, 我自己的移植, 带 port check)

**Port check(必须先过, 否则读数无意义)**: 我的移植对 `LIVE_FUND` 控制臂在 2025on 上读出 **top20_share 0.1109 / ex_top20_sharpe 6.709**, 与归档 `rs_concentration.json` 的 **0.1109 / 6.71** 相同 ⇒ 移植没有漂。

| 臂 | 窗 | n | top-20 份额 | ex-top-20 Sharpe | leg Sharpe |
|---|---|---|---|---|---|
| **AMI_ORTHLAG(本案信号)** | FULL post-warm | 9156 | **−0.0029** | **+3.249** | 2.055 |
| AMI_ORTHLAG | 2025on | 3522 | +0.4433 | **+2.480** | 2.873 |
| AMI_ORTHLAG | pre2025 | 4386 | −0.4996 | **+3.928** | 1.701 |
| 对照 LIVE_FUND | 2025on | 3522 | +0.1109 | +6.709 | 4.781 |
| 对照 LIVE_FUND | pre2025 | 4386 | **+1.0682** | **+0.075** | −0.53 |
| 已死的 RESID_SHARPE | 2025on | 3522 | **+1.2977 / +1.8892** | **−2.40 / −5.60** | — |

**读法**: sleeve 在**三个窗**上都不是 RESID_SHARPE 形态。它最集中的窗(2025on, 44% 来自 top-20)剩下的名字仍然给 **+2.48** Sharpe; 而在役 fund 腿在它自己的坏窗(pre2025)是 **107% 来自 top-20 且 ex-top-20 Sharpe +0.075** —— **在役书本身比这条 sleeve 更依赖尾巴**。
**顺带**: 去掉一锚滞后, 2025on 的 ex-top-20 Sharpe 从 2.48 掉到 **0.881** ⇒ 滞后不是保守处理, 是信号的一部分(与 §C.2 一致)。
收据 `/workspace/uplift_2026-09-11/ship1/SHIP1_concentration.json`, 装置 `ship1/rs_conc_ami.py`。

### 3.2 前后向偏移谱(k = −3..+3, 报七个数不报一个比值)

约定(必须声明): `y4[i]` = 锚 i 的**前向** 4h 收益 ⇒ **k=0 是可交易的那一格**, k<0 是过去。n=9277, FULL post-warm。

| k | −3 | −2 | −1 | **0** | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|
| 秩 IC | 0.01144 | **0.02402** | 0.00941 | **0.01191** | 0.01181 | 0.01081 | 0.00964 |
| t | 6.97 | **14.29** | 7.48 | **9.68** | 9.49 | 8.75 | 7.82 |

**峰在 k=−2(过去), 是前向的 2.02 倍。** 这**不是泄漏**: 分子 `|Σ288 ret5|` 的 24h 窗**本来就包含** k=−2 那根 bar 的收益, 所以它与自己窗内的收益相关是构造使然; 决策时刻能看到的一切严格早于锚, 再加 §C.2 的一锚滞后。
**但它必须被写下来**: 前向 IC 只有 **0.0119**, 而后向相关是它的两倍 —— 这条信号的可交易边缘是小的。**对照**: 被判死的 taker flow 是"后向 IC 122×前向, 且前向 IC = −0.0001"; 本案是 2.02× 且前向 **+0.0119 (t=9.68)**。两者不是同一个东西。
收据 `ship1/SHIP1_offset_spectrum.json`, 装置 `ship1/ic_off.py`。

### 3.3 换手匹配零假设(SHIFT / RELAB / T 族; 归档臂名 `AMI_lag`)

**口径警告**: round-3 的 placebo 电池跑在 `costb_fee_steady.json` 上, **不是**本文钉的 fitted PWR 模型。所以下表的绝对 margin 与 §E 的 Sharpe **不可混读**; 它回答的是"这条信号是不是换手噪声", 不是"它值多少钱"。

| 窗 | 池化 margin_net | CI95 | **CI Bonf(K=12)** | 判词 |
|---|---|---|---|---|
| FULL n=9018 | **+0.9310** | [+0.5489, +1.3348] | **[+0.3667, +1.5249]** | **SURVIVES** |
| F23 n=7908 | +1.0031 | [+0.5386, +1.4500] | [+0.3882, +1.6836] | SURVIVES |
| **冻结 n=3168** | +0.9432 | [+0.1659, +1.7136] | **[−0.1484, +2.1458]** | **SURVIVES_NOMINAL** |

逐族(FULL): R(RELAB)+1.0022 CI95 [+0.5330,+1.4787]; RO +0.8285 [+0.3458,+1.3473]; T(SHIFT)+0.9280 [+0.5077,+1.3702] —— **三族 pooled 下界全 > 0**。
**但逐个零假设不全过**: FULL 上 8 个匹配零假设的 CI95 下界全 > 0, 然而在 **K=12 Bonferroni** 下 **O2(−0.096)与 T1(−0.089)掉到零以下**; **冻结窗上 T1 的 margin 直接是负的(−0.1931)** —— 即那一个换手匹配的零假设在冻结窗上**跑赢了真臂**。
**旧 placebo 的折价, 在本臂上实测**: legacy(逐锚置换)margin 1.8199 vs 匹配后 0.9310 ⇒ 旧读数把优势**夸大了 +95.5%**, 且旧零假设的成本是真臂的 **7.87×**(`legacy_cost_ratio`) —— 正是"读在换手成本上而不是读在缺席 alpha 上"。
收据 `/workspace/uplift_2026-09-11/r3_placebo/JUDGE_r3_placebo.json`(round-3 产物, 本轮逐键重读)。

**★ `AMI_lag` 不是本案 sleeve 的位级同一件**: 它建在 ext 谱系的研究列上(`cells_real = 3,125,890`), 本案钉的是 v4 重建列(3,140,350 有限格)。round-4 P6 §1.4 实测两者在**书层**差 **+1.68e-17 bps/锚**, 且本轮 §3.1 的移植里 `AMI_ORTHLAG`(v4 列)与 `AMI_ORTHLAG_RESEARCHCOL`(研究列)**每一位打印数字相同**。所以该判词可以转移, 但这一句必须留在文件里。

---

## 4. 本文没有证明的(空洞, 按重要性排)

1. **合成书没跑过(G0)**。§E 的 1.6608 是两本书在 g 层的线性组合, **不是一本跑过的书**。装置 `w10_sleeve.py` L219 的 z 合成是硬写的三腿, 加第四项需要改装置 ⇒ 新 sha ⇒ 新 GATE P。**这是 ADMIT 前必须补的一次跑**, 不是文书细节。组合的成本项是**上界**(真书会净掉两腿的对冲交易), 但 alpha 项只在中性带内不互相抵消时才精确。
2. **FTRIM 联合未检验**。sleeve 的全部回放是 `FTRIM=off`; 在役书是 `FTRIM=zero`。合成后 FTRIM 作用在合成 z 上, 是没测过的对象。
3. **跨数据源位级未验**。生产者的立方是自己从 REST klines 现搭的, 与归档立方(monthly zip → holefix2)内容上不是同一份。只能在首锚 C1 验。
4. **min-notional 地板未检验**(回放层不存在)。sleeve 持名 250.8(A0 250.8 附近), 但权重分布更偏尾。
5. **冻结窗的 placebo 没有单独复验**, 而 G2 正好落在冻结窗上; 且冻结窗上 T1 零假设跑赢真臂(§3.3)。
6. **FM8 开着**: 一个"坏了但不自知"的生产者写 `risk_scale=1.0`, 全部三条通道绿。只能靠人工演练。
7. **0.8 这个降级档位是预注册的猜测, 不是测出来的。** 本仓没有任何证据说降级时该跑 0.8 而不是 0.7 或 0.9。
8. **中性度变差**: sleeve 的 |netlong| 均值 0.0513 vs A0 0.0377(**差 36%**); 在役执行器有 1.5% 中性带, 而 09-11 已连续两锚 net/gross 在 −1.2%~−1.45% 带外(STATE.md)。**合成后的中性度必须在 G0 那一跑里单独读出来**, 本文没有这个数。

---

## 5. 建议的裁定顺序(不是动作, 是性质)

1. **先单独裁定执行器补丁(§B1.4)**。它在生产者不写字段时逐位无操作, 与 sleeve 的死活无关, 而它修的是一个**独立于本案已经存在**的缺陷: 今天任何生产者降级都会被重新加满杠杆。
2. **再补 G0 那一跑**(装置加第四项 + 新 GATE P + FTRIM=zero 联合)。
3. **最后才谈 `ami_alloc: 0.0 → 0.20`**, 且以 C4 五条全响为硬前提。
