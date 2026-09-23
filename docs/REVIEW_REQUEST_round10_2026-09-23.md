> **创建:** 2026-09-23 11:2xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(lead) | **状态:** 第十轮复审指令(11:40Z 追加 §E;12:2xZ 更新 §A 至 M3 终版 `80ae104`、§E.2-6 部署状态改动)—— **紧急**(用户要求尽快换装,复审与实现并行,避免返工) | **作废条件:** 被引用的提交或文件改变;复审回应件出具后由其取代

# 第十轮复审:五处即将上线 / 已上线实现的核心代码逻辑

## 0. 目的与优先级

实盘账户按看门狗 cond4 口径(剔除划转的时间加权, 自首个 LIVE 计价日起 53 天, `state/live/watchdog/last_eval.json` 评估于 2026-09-23T08:48:05Z)累计 **−5.64%**, 峰值回撤 −10.24%。我方分析(`docs/ANALYSIS_independent_researcher_takeover_2026-09-23.md`)认定两个问题:**① 在役模型训练在有缺陷的输入上**(Stage 1:同引擎 2023H2–2025,在役 OLD +1.8% / 回撤 −38%,修复输入重训 NEW +99%–122% / 回撤 −18%);**② 书对 BTC 的实际 beta 约 −0.35**(近期亏损的直接机制,新旧模型在 08-31→09-18 亏得一样)。对应两条上线线正在推进,请**先审代码**(结果之后陆续到):

| 优先 | 对象 | 状态 | 上线时间点 |
|---|---|---|---|
| **P0** | **A. M3 BTC 对冲 —— 生产实现**(执行器 + 生产者) | 代码完成于执行器克隆分支 `m3-beta-overlay`,终版 `80ae104`(未推送,开关缺省 off);评估 M3b 排队中 | 用户对 M3b 结果裁定后 |
| **P0** | **B. NEW_S —— 既有策略在正确口径下重训**(历史特征回放、成员规则) | 代码已定,历史特征重算在 pod2 跑(预计 12:35Z 完);判词预计 16:30–17:00Z | 若判 SWAP,最早 21:00–23:40Z 静默窗 |
| P1 | C. M3 评估钩子(决定 A 能否上线的证据装置) | M3 已出(R3 投递未过),M3b 排队(等 NEW_S 特征重算完) | — |
| P2 | D. 离线电池账本门 | **已部署** `b66257b`(09-23 09:19Z) | 事后复审 |
| **P0** | **E. NEW_S 训练 / 组装 / 评估 / 上线导出**(11:40Z 追加) | 代码已写好,在 pod2 排在特征重建之后自动运行;**训练尚未开始** | 同 B |

---

## A. M3 BTC 对冲 —— 生产实现(P0)

**做什么**:生产者在 target_live 里新增字段 `beta_overlay`(每名 β_i);执行器在 **POP → RESHAPE → CLAMP 之后**,用执行目标算 `β_exec = Σ w_i β_i`,把 BTCUSDT 目标设为"书内 BTC 分量 + (−β_exec)",作为不再经过去均值的独立叠加腿。开关 `config/book.json → beta_overlay.mode ∈ {off, shadow, on}`,缺省 off。

**预注册**:`docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md`(24c3f803f)+ `AMENDMENT_1_m3_beta_overlay_2026-09-23.md`(912788743,碎单判定作用于合计)。

**完整 diff**:`multi_asset/exports/research/review_round10_2026-09-23/EXECUTOR_m3_b66257b_to_4dd7d53.diff`(2,603 行,18 个文件);提交链 `EXECUTOR_m3_commits.txt`(8725e7d → 11aa8d1 → c71ca7a → 4dd7d53)。克隆位置 `~/cc_tmp/m3_impl_20260923/exec`(只读)。

**12:1xZ 更新**:实现代理已交付。终版 = **`80ae104`**,相对 `4dd7d53` 只改 `live/beta_overlay.py` 两处 `#` 注释(lead 核 `git diff`:1 文件 3+/3−,全是注释行),上面的 diff 仍有效。全电池在 `4dd7d53` 上 `ACCEPTANCE: ALL GREEN (163/163 suites exit 0)`;`80ae104` 本身没跑全电池,部署时 `safe_commit` 会在确切的树上跑。设计、逐行改动表、与现有机制的逐项交互、部署与回滚手册见 **`docs/IMPL_m3_beta_overlay_2026-09-23.md`**(研究仓 `9564851c4`);补丁 `multi_asset/exports/research/m3_impl_2026-09-23/executor_m3_b66257b.patch`。

### A.1 接入点(`scheduler/anchor_loop.py`,节选)

```python
# 锚开始:每锚读配置,缺省/无效 ⇒ off(无效还发 HIGH);非外部书 ⇒ off
self._m3 = {"mode": "off", "record": None}
_m3c = BO.config(BC.load())
...
# mode on:BTC 永远进入本锚 symbols(与书的名字一起取价、过场所门、止损与元检查)
if self._m3["mode"] == "on":
    symbols = sorted(set(symbols) | {BO.BTC})
...
# ★ 在书的阶段【之前】对 BTC 的不可交易原因分类:名字级原因(止损/冷却/不可交易…)= hard ⇒ 暂停对冲腿;
#   只有 external_dust 一个原因 ⇒ 允许按"合计值"改判(M3b)
_m3_hard = BO.hard_block(self._untradable, self._untradable_sources)
_m3_dust_only = BO.dust_only(self._untradable, self._untradable_sources)
_clamp, _rs = apply_withhold_and_reshape(target, _held_book, self._untradable, self.gross, ...)   # POP→RESHAPE→CLAMP(现状不变)
# ★ 对冲腿在这里,AFTER reshape+clamp
if self._m3["mode"] != "off":
    _m3o = BO.stage(self._m3["mode"], target, _held_book, external, self.gross, _m3_hard,
                    prev_status=..., btc_floor=_fl.get(BTC), dust_mult=external.get("min_notional_mult"),
                    btc_dust_only=_m3_dust_only)
    if _m3o["release_btc"]:        # 合计值推翻了书内碎单判定 ⇒ BTC 移出 clamp 的只减/禁加/只平/弹出名单
        for k in ("reduced", "add_blocked", "flatten_only", "popped"):
            _clamp[k] = [s for s in _clamp[k] if s != BO.BTC]
...
# 场所上限截断作用于【合计】BTC 目标;被截断的对冲缺口页报并记账
BO.after_cap(self._m3["record"], target, _capd, self._m3.get("betas"))
plans = self.executor.plan(target, ...)
BO.after_plan(self._m3["record"], plans, lot_step=..., min_notional=...)     # 计划层投递,只记录
...
# anchors 行:m3_beta_overlay 记录;中性读数改为"剔除对冲腿后"判(原始 net_over_gross 仍在行上)
_m3_nrow = BO.neutrality_view(row, ctx.get("m3_beta_overlay"))
```

### A.2 对冲计算(`live/beta_overlay.py`,节选)

```python
def beta_exec(target, betas):
    """Σ target_i·β_i,只对执行目标非零的名字;任一非零目标名缺 β ⇒ 整体拒绝(绝不默认 β)"""
    ...
def stage(mode, target, held_true, ext, sizing_gross, hard, prev_status=None, btc_floor=None, dust_mult=None, btc_dust_only=False):
    b = target.get(BTC, 0.0)                         # 书内 BTC 执行分量
    v = validate_field(ext.get(FIELD), ext["anchor_ts"], present=(FIELD in ext))
        # 校验:版本 m3_beta_v1;字段锚 == 文件锚;data_cutoff_ts == 锚(早=陈旧,晚=未来);
        #       n_win=180/n_min=120/clip=[-1,4]/fallback=1.0 逐项等于预注册;n_obs<120 的必须等于 fallback;β_BTC == 1.0
    be = beta_exec(target, v["betas"]) if v["ok"] else None
    if hard:                                         # BTC 名字级不可交易 ⇒ 暂停,对冲缺口 = 意图,记账;首锚 HIGH、持续期 INFO
        ...; return
    if not usable:                                   # 字段缺失/畸形/有名缺 β ⇒ 不下对冲单
        if mode == "on" and held_btc != 0.0:
            target[BTC] = held_btc                   # ★ 冻结在现持:delta 0,不当 0 对冲平掉,也不按 β=1 重算
        ...; HIGH; return
    hedge = -be["beta_exec_usdt"]; combined = b + hedge
    thr = dust_mult * btc_floor
    if btc_dust_only:                                # M3b:BTC 只因书内碎单不可交易 ⇒ 用合计值改判
        if abs(combined) < thr: status="combined_dust"(不动,缺口记账); return
        status = "applied_via_combined"
    else:
        status = "applied"                           # 可交易的 BTC:无论合计多小都对冲(只记录 combined_below_threshold)
    if mode == "shadow": 只记录 would_be,不改 target; return
    target[BTC] = combined                           # ★ 唯一改书的地方
    diag(...)                                        # 平书诊断:执行书 β 的移动 / 意图,容差 1e-9 相对
```

### A.3 生产者 β(`ops/producer_release/20260923_m3/beta_overlay_producer.py`,节选)

```python
# β_i = 名 i 的 4h 对数收益对 BTCUSDT 4h 对数收益的 OLS 斜率(含截距),锚 A 已完成的最近 180 根 4h bar,
#       成对有效 ≥120 否则 1.0,截断 [-1,4],BTC=1;BTC 方差为 0 ⇒ 抛异常
# 数据 = 生产者自己的滚动缓存(state/rolling.npz):4h 收益 = 48 行 log1p(ret5) 之和;
#       一根 bar 有效 ⇔ [T-4h, T] 闭区间的 49 行全有限(起点行缺失会让下一行跨缺口);缺行绝不填 0
# ★ 与评估的具名差异:ret5 在生产缓存里是 float16、每 5 分钟裁剪 ±0.30;评估用的是认证原始价格表
# 因果:只读 close_time <= A 的行;测试扰动 A 之后每一行 ⇒ β 逐位不变,扰动 A 那一行 ⇒ 必变
```
另:`ops/producer_release/20260923_m3/combo_stage.py`(476 行,生产者 combo_stage 的改版 —— 把字段写进 target_live);生产者 diff `multi_asset/exports/research/m3_impl_2026-09-23/producer_m3_fb5a9407.diff`。

### A.4 我最担心、请重点查的(按严重度)

1. **净敞口的全部读者(普查)**:对冲腿本身是 β×gross 量级的 BTC 净多头(M3 结果: 主窗执行书事前 β 平均约 −0.09 gross 单位, 被跳过的大锚平均 |意图| 0.14–0.15 ⇒ 净敞口约为 gross 的 9%–15%, 即 NAV 的 18%–30%)。实现已把"中性读数"改成剔除对冲腿判(`neutrality_view`)。**请逐个找出所有读净敞口/净/gross 比的地方**:执行器 1.5% 中性带(`book_net`)、看门狗各条件(cond4b 杠杆、cond6 权重保真等)、guard_twin、"撤名残差"与 position reconcile 告警、reshape 残差告警、比例响应、逐名止损、账本类电池断言(`tests_disposition_matrix` 等)。**任何一个漏改,都可能在开关打开的第一个锚上误报、误判,甚至触发全书响应。**
2. **BTC 被逐名止损当成 alpha 仓位**:BTC 目标 = 书内分量 + 对冲腿。逐名止损按"持仓深度 ≤ −30% 连续 2 个终锚"判 —— BTC 下跌 30% 时,**对冲腿会被当作亏损仓位止损、并进入 7 天冷却**(冷却期对冲腿按 hard 暂停)。这是想要的吗?止损应只判书内分量吗?
3. **总杠杆**:对冲腿的 gross 加在 2×NAV 的书之上(典型 +0.2×NAV)。有没有哪条杠杆/保证金检查(cond4b、场所保证金、`sizing_gross` 相关断言)会因总 gross > 目标而触发?
4. **开关切换**:off→on 首锚、on→off(BTC 目标回到书内分量 ⇒ 执行器平掉对冲腿)、on 期间出现 HOLD 锚(外部书不可用 ⇒ 整锚不下单 ⇒ 对冲腿保持)—— 三种过渡是否都对?预注册 §2.5 "HOLD 锚保持上一锚的量" 在实现里是由"整锚不下单"自然实现,还是有显式处理?
5. **生产 β vs 评估 β 的数值差**:评估用认证原始价格表,生产用 f16 裁剪缓存。**差多少没有量化**。请要求(或自行做)在最近若干锚上对比两者的 β_i 与 β_exec。
6. `validate_field` 要求 `data_cutoff_ts == anchor_ts`:生产者在锚后若干分钟才运行(记录 A 约在 A+20 分钟算),缓存里是否确有"收盘于 A"的那一行?若生产者某次缓存末行晚于 A,β 是否仍只用 ≤A 的行(代码注释说是,测试是否覆盖了真实缓存形状)?
7. `release_btc`:合计值推翻书内碎单判定后,BTC 被移出 clamp 的四个名单 —— 若 BTC 同时因其他原因在这些名单里(例如 held-exit),是否会误放?(`hard_block` 应已先拦下,请核。)
8. **(实现代理自列,IMPL §7)首个 on 锚一次建满对冲**(约 0.08–0.19 gross):若没成交,§4-5e 持仓断裂的拆分在"说不出话"(覆盖 <90%)时回到每名 10% 规则,会把它读成断裂;场所量化规则锁(−4400,E-0910-A)也可能挡单。是否应该分几锚建仓?
9. **(IMPL §7-3)追单实验的中性判定**在生产里剔除对冲腿,认证模拟器(`exec_sim.py:632`)不剔除 ⇒ 评估与生产在这一点上不同。影响多大?
10. **(IMPL §7-9)计划层手数截断**:对冲小于约 2,200 USDT 时,计划层交付比可能低于 0.95(目标层恒为 1)。R3 在生产上的读法是否要改成目标层?
11. **(IMPL §7-1、§7-8)两种会平掉对冲的过渡**:生产者不再给 BTC 目标而我们持有对冲时(近 167 个 combo 文件里 0 次);运行中配置失效或切回 shadow 时。是否应该冻结而不是平掉?

---

## B. NEW_S —— 既有策略在正确口径下重训(P0)

**做什么**:在役**模型结构与组装**(King 78 特征 LGBM + F10 171→256→256→1 + 资金费腿 + 55/45 组装 + 席位/链/FTRIM/发布门)**不变**,训练输入改正确;**训练配方用研究员 NEW 的配方**(预注册 §1.4),与在役月度重训有两处已知不同,见 §E.2-1。**训练特征 = 生产者今天线上实际运行的特征代码,原样在历史上逐锚回放产生**(一份实现 ⇒ 训练与线上逐位一致);上线时生产者特征代码**零改动**,换模型文件与 `booster_sha_pin` / `f10_sha_pin`,生产者拉取名单 450 → 522;另有部署时的生产状态改动(资金费 EMA 重播种、新名历史回填),见 §E.2-6。

**预注册**:`docs/PREREG_new_servable_models_2026-09-23.md`(db0123df7)+ 修订 1(代理提交 63ca0d0bb,"本轮不修生产者服务时缺陷,训练向服务对齐")。装置:`multi_asset/exports/research/news_2026-09-23/devices/`。

### B.1 成员规则(`p1_members.py`,逐字复用生产者 `shadow_loop_v3.py` L497–509)

```python
def producer_members(CDf, ai, P):
    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]          # 过去 2016 行 = 7 天 5 分钟收益
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016                                 # 覆盖率
    m7 = np.where(fin5, r5seg, 0).sum(0); n7 = np.maximum(fin5.sum(0), 1)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))   # 7 日波动
    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]; finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)                     # 流动性均值
    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    m = np.where(ok)[0]
    if len(m) > P["NTOP"]:
        m = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])       # 流动性前 NTOP
    return m, ok, qvm
```
历史各锚的候选 = 当锚合法掩码(可交易 W24H ∧ 判活,x0918r `f752d8ae`)∧ 加密币类(`venue_class_20260908.json`:underlyingType∈{COIN, INDEX} ∧ PERPETUAL;排除 149 个 TRADIFI_PERPETUAL)。非候选名在回放缓存里置 NaN ⇒ 覆盖率不过 ⇒ 不入选。

### B.2 逐锚回放(`news_hist_features.py::replay_anchor`,节选)

```python
i0 = max(ia + 1 - CACHE_ROWS, 0)                       # CACHE_ROWS = 11520(shadow_loop_v3 L207,40 天)
RD = np.array(cd[i0:ia + 1], dtype=np.float16)          # 生产者在 A 时持有的滚动缓存(f16,原样)
RD[hole_rows, hole_cols, :] = np.nan                    # 研究缓存里的合成补洞 bar:线上从不摄入
RD[:, ~cand, :] = np.nan                                # 拉取名单 = 候选
# King:shadow_loop_v3 L486–L553 原文编译执行(_king_block)
out = king_block(st, A, P, cfg, row_of, list(st.live), _Diag(), logs.append)
m = out["m"]
# F10 迷你管线:combo_stage L147–L185 语义
ms_arr[i] = pm_l  for every E row                      # D2 按生产现状复现:历史各锚成员 = 当锚 pm
fe[-1, j] = ema[s]["acc"]; fn[-1, j] = ledger[s][-1].rate   # 资金费面板只填最后一行(生产现状)
subprocess dlw_features.py (29ae6a98) ; f8_higher_order_features.build (2c500c7a)   # 生产原码,同 F171_* 环境变量
assert m82["self_sha256"] == DLW_SHA and m89["self_sha256"] == F8_SHA   # 跑的就是生产那份代码
assert np.array_equal(scol, pm)                         # F10 行与成员顺序一致
```
资金费状态:`news_fund_replay.py` 把 `shadow_loop_v3.py` L451–L484 原文编译执行,在历史结算账本上逐锚回放(冷启动)。

### B.3 我最担心、请重点查的

1. ~~"只填最后一行"的资金费面板是否与生产相同~~ —— **lead 已核实(11:3xZ),相同**:生产 `~/wide_shadow/fea171/combo_stage.py`(fb5a9407)L162–L172 只写 `fe[-1, j]` / `fn[-1, j]`,历史行留 0;King 块(`shadow_loop_v3.py` 6080073964bf,L542–L543、L549 的 `led[-1]`)只读账本最后一条与 EMA acc。回放的"每名一条账本 + 最后一行面板"与之同构。复审员可复核,不必重做。
2. **冷启动**:资金费 EMA 状态从空开始回放(轴首 2022-01)。生产 EMA 半衰期 3 天(`shadow_loop_v3.py` L4 "fund_ema v1 normfix(HL3d)"),到 King 训练首折(2022H2)与判据窗(2023-06-30 起)已预热半年以上;组合状态自 2023-01-01 从零起(与 Stage 1 相同)。lead 判断影响可忽略;请复核有没有别的状态量(如席位 msharpe 回看 900 锚 ≈ 150 天)在判据窗前没有热透。
3. **缓存来源**:回放缓存 = 研究缓存 x0918r(`08bb2957…`,f16,裁剪 ±0.30)。它与生产者当时**实际**拉到的 5m 数据是否同源同口径(交易所 kline 字段、成交量通道 `lqv`、`tbf` 等)?合成补洞置 NaN 是对的,但**交易所真实缺口**在两边是否都为 NaN?
4. **成员选择残余**(收据 `news_2026-09-23/receipts/P1B_FETCHLIST.json`):生产者成员筛不含合法掩码 ⇒ 已不合法但仍有冻结行、过覆盖/波动门的名可能被选入。实测:拉取全部加密名(680)时 2025-07→2026-09 有 181/2671 锚(6.8%)与训练规则不同,**全部**来自当锚已不合法的名(其中 2026-08 占 74 锚);拉取 522 名(450 ∪ 9 月候选)时 **9 月 109 锚 0 差**,但此前几乎每锚都差 —— 固定名单复现不了历史,新上市名会逐月漂离训练规则。⇒ 拉取名单必须按月维护(随月度重训)。请判断这是否可接受,或是否应在生产者成员筛里加合法掩码(那是生产者特征代码改动,超出本轮"零改动"范围)。另:回放只在成员列上算特征(提速),`P1_COLRESTRICT_BITWISE.json` 在 5 个锚(2022-03 → 2026-09-18)上与全列计算逐位相等(X82/X89 ndiff 0)。
5. **标签**:训练标签必须是未裁剪原始价格收益、缺失不填 0(预注册 §1、修订 1 第 2 条)。请在 P3 训练收据出来后核标签构造。
6. **决策规则**:预注册 §3 S1–S5(两种子各自:合并点估计 > 0 对 OLD 与 OLD_HOLD;三段至少两段 > 0;回撤不差于 OLD_HOLD;−25% 触线路径不多于 OLD_HOLD;成本格同号),**区间照报不作门**(依据 E-0923-B:该仪器区间半宽约 10 bps/日)。这是用户要求的直接决策规则。请判断它是否足以支撑换装,**若不足,请在 16:30Z 判词之前提出**(判词之后改规则就是挪门柱)。

---

## C. M3 评估钩子(P1)

`multi_asset/exports/research/m3_2026-09-23/devices/m3_hook.py`:在认证模拟器的 `apply_withhold_and_reshape` 之后插钩,`w_exec,s = target_s / Gs`,`β_exec = Σ w_exec,s·β_s(A)`(β 公式沿用 M2 `m2_lib.betas_at`,认证原始价格表)。结果 `docs/RESULT_m3_beta_overlay_2026-09-23.md`(f7fab0642):R1、R2 两底座通过,**R3 投递未过**(D = 0.779 / 0.840),原因是从 M2 继承的"底座 BTC 是碎单 ⇒ 对冲跳过"。M3b(修订 912788743)排队中。

**请查**:① 钩子看到的 `target` 与生产执行器在同一锚看到的 w_exec 是否同一对象(代理用构造锚 + 一个真实锚对模拟器决策记录验过);② R3 的 D 定义(整体意图 β 移动之和的比)与中位数都合理吗;③ R4 显示 2026 主窗对冲使总收益 −9.3 / −13.3pp(主要来自价格:2026 年负 β 整体赚钱),辅助窗 NEW +29.5pp —— 这个解读对吗。

---

## D. 离线电池账本门(P2,已部署)

`ops/run_acceptance_offline.sh`(`b66257b`,副本 `multi_asset/exports/research/review_round10_2026-09-23/DEPLOYED_b66257b_run_acceptance_offline.sh`):进沙箱前,父进程**只列**实盘 `state/live/pilot_log` 的日目录名;检出缺任一已完成实盘日 ⇒ exit 78;实盘账本无日目录 ⇒ 拒绝(未知不是空)。测试 `ops/tests_acceptance_offline.py` ALL PASS 36(含基线绿先行、拆门变异变红);全电池 `ACCEPTANCE: ALL GREEN (162/162 suites exit 0)`。**已知遗留**:该测试与 `tests_acceptance_interpreter` 不在 `run_acceptance.sh` SUITES 里(原状)。

**请查**:测试缝 `_offline_ledger_production="$_offline_production"` 这一行在生产里是否可能被别的东西改写(它只是一个脚本内赋值);"最新一天允许缺"是否会被利用成"复制一份停在昨天的副本"。

---

## E. NEW_S 训练 / 组装 / 评估 / 上线导出(P0,11:40Z 追加)

**为什么追加**:A–D 写于 11:2xZ,当时只看了特征重建。核对时发现 pod2 上已有 10:41–10:59Z 新写的训练、组装、评估、导出代码,由 `news_chain.sh` 在特征重建(104 个分片,11:16Z 完成 45 个)结束后**自动串行运行**。复审对象 = 下表各哈希(已原样复制到 `multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/`,与 pod2 `/dev/shm/news_2026-09-23/devices/` 逐个哈希一致;特征重建三件与 A–D 引用的同哈希)。

| 阶段 | 文件(sha256 前 16 位) | 做什么 |
|---|---|---|
| 串联 | `news_chain.sh` 6a7240840717693c | 等 104 分片 → 合并 → King → 席位腿 → F10 两种子(GPU 并行)→ 组合 → 适配器 → 引擎 4 组运行 → R-P / R-P2 读数 → S1–S5 → 延伸段 |
| 特征合并 | `news_p2_build.py` 809c0c4afaa95baa | 分片合并,断言全部特征有限 |
| King | `news_train_king.py` f1f393f83e6ac516(折函数 `king_folds.py` 4886c278c12b0f51) | NEW 配方原样,只换输入 |
| 席位腿 | `news_legs.py` 2b890fe0d38cf71c | 生产 `xz_in_base` / `xz` / 腿收益递推 / msharpe 原码编译执行 |
| F10 | `news_train_f10.py` d4feabd1c6a1ff9d(可观测规则 `f10_observability.py` c6399d7ae4948250) | NEW 的 `train_f10.py`(07ac4c67)只换输入段(逐行 diff 已核) |
| 组合 | `news_combo.py` e2724e6bcf6ed9e1 + `continuous_combo.py` 1501c9f63641bf44 + `combo_target.py` d7577e824298fb90 + `book_universe.py` 90e332cc27cf8f34 | 研究员的组合装置原样 |
| 引擎配置 | `news_make_configs.py` 22910d966860e91b | 由 Stage 1 配置复制,**逐叶 diff 断言**只有标签 / 目标 / 输出根不同 |
| 判词 | `news_stats.py` 10cb1d9e56f63355 | S1–S5 |
| 上线导出 | `news_export_models.py` a1b9aa8496f2a8aa | King = `king_2026.txt` → `slow2026.txt`;F10 = s42 的 202609 月折 → 生产 numpy 格式 + 推理一致性门 |
| 平价取样 | `news_p5_extract.py` c9443fad676aabe0 | 取 2026-09-17T16Z → 09-19T00Z 共 9 个锚的训练构建行,供本机对生产者重跑做平价 |

### E.1 lead 已核实(附证据,复审员可抽查)

1. **标签覆盖**:King 和 F10 的标签都取自研究员 NEW 的 `dlw_targets.npz`(ca479fcc…)。只读核实(pod2,11:3xZ):标签 = 原始价格表 `price_full_raw_x0918r` 上 (E, E+48] 的复利收益,要求所有收盘价都观测到;**不只 NEW 成员有标签** —— NEW 成员之外有 756,675 个有限标签格,10,320 / 10,321 个锚都有。换了成员规则的 NEW_S 不会因为"名字不在 NEW 成员里"而没标签。
2. **发布门失败 = 持仓不动**:生产 `combo_stage.py`(fb5a9407)L316–L321、L341–L346、L423–L427 —— 门不过即中止发布,执行器对缺失 / 未过身份钉的目标持仓不动,"不回退交易 King"。评估的 `hold_contract`(发布失败 = 保持数量)与之相同。
3. **组合步骤与生产逐行对照**:`combo_target.step` 里的去 rev24 席位掩码与重归一、F10 秩、z_kc / z_fc、FTRIM(rn8 ≤ −0.0010 且 z<0 置零,结算间隔缺失按 8h)、0.55 / 0.45、三道门(F10 覆盖 / gross∈[0.4,1.2] / 名数,都作用于混合前的 `combo_raw`)与生产 L255–L300、L358–L363 相同;`chain` 与 `exec_reshape` 从生产源码按哈希编译执行。
4. **可持仓名单**:生产的 LIVE_MASK 取自当锚 King 文件的 `universe` 字段(`combo_stage.py` L73–L74),不是拉取名单;评估的 `book_legal` = 冻结的 U-PIT/加密宇宙代理(8 月后为冻结的生产名单)∧ 当锚合法 ∧ 加密。**拉取名单扩到 522 名只影响成员与截面排名,新增的名不能持仓,除非生产者的 universe 也改** —— 请复审员确认这与评估一致。
5. **判词实现与预注册逐条相同**:S1 对两对照的合并日差点估计 > 0;S2 三段至少两段 > 0;S3 回撤路径均值不差于 OLD_HOLD;S4 R-P 触线路径数 ≤ OLD_HOLD;S5 三个成本格同号;区间只报告。32 条路径按种子号配对(共用随机数)。OLD 路径文件逐字节对认证运行复核,不一致即 STOPPED。

### E.2 请复审员判断(按严重度)

1. **"既有策略重训"的准确含义**。NEW_S = 在役模型结构 + 在役组合装置 + 生产特征代码,但**训练配方用的是研究员 NEW 的配方**(预注册 §1.4 冻结的就是这个),与在役有两处已知不同:
   - **F10 选轮规则**:NEW 配方固定用第 7 轮(8 轮、余弦 T_max 15,即 FIX7);在役月度重训按验证集无约束挑最好的一轮(`pod_f10_refit_ext.py` ea3675b8 L115–116)。FIX7 在 09-06 有正向证据(对 CONST42 +0.267,区间 > 0),但从未上线。
   - **F10 训练窗口的可观测规则**:一个 120 锚训练窗里,只要任何"可能被持有"的名在任一锚缺标签,整窗丢弃(`f10_observability.span_admissible`)。这相当于**用未来的价格可得性筛训练样本**(含下市 / 停牌前的窗口会被丢),是一种轻度幸存者偏差。NEW 用的是同一条规则,评估对 NEW 与 NEW_S 一致。**请在各折 `ADMISSION.json` 出来后看丢弃比例**,比例高就要评估偏差。
   - King 参数(400 棵树、学习率 0.05、63 叶、行 / 列采样 0.8,目标 = 锚内对原始标签的秩,≥50 个标签)标注为 "Actual 78-column King recipe";**lead 没有逐字核对在役 King 训练脚本**,请复核。
2. **King 上线模型很旧**:导出的是 `king_2026` 折,训练标签截止约 2025-12-22(2026-01-01 前隔 60 锚)。9 月底上线时已过时约 9 个月,但这正是评估里 2026 年 OOF 用的模型,所以"上线的 = 评估过的"。把 King 重训到 8 月会更新,但那个模型没被评估过。选哪个?F10 导出的是 2026-09 月折(新)。
3. **评估用的发布门是"按比例"而不是生产的"字面 380 / 150"**:`news_stats.py` 的 CELLS 用 `scaled_rule_raw_UAFE`(门 = ceil(0.95n) / ceil(0.375n))。n = 400 时两者相同(2025-07 起每锚成员都是 400,见 `P1_MEMBERS.json` by_month);2023–24 成员只有约 185–260 名,字面门会让书全现金。所有臂(含 OLD、OLD_HOLD)用同一格,Stage 1 已声明。请确认可接受。
4. **串联脚本吞掉引擎失败**:`news_chain.sh` L47–L52 后台启动 4 组引擎后用不带参数的 `wait`,它恒返回 0,`set -e` 拦不住某组引擎失败。下游 `load_cell` 要求 32 条路径齐全且审计干净,缺了会以 UNAVAILABLE / KeyError 报错,所以不会出错误判词,只是报错晚。低严重度。
5. **平价只取 9 个锚**(2026-09-17T16Z → 09-19T00Z,s42)。预注册 §4.1 要求上线前平价通过。9 个锚里有没有发布失败锚、有没有席位极端锚?是否需要更多?
6. **部署时要改的生产状态**(NEW_S 代理 12:0xZ 报告,收据在 `~/cc_tmp/news_20260923/parity/`,待入库;数字为代理自报,lead 未复跑):
   - 已做的平价:用在役模型在 9 个实盘归档锚上重算生产者的 King 块,成员与 King / rev24 / fund 三腿 z 和生产者当时写的记录逐位相等;实盘滚动缓存(450 名 × 7 通道 × 11520 行)与训练用历史缓存 x0918r 逐位相等;资金费账本末行 522/522 相等。
   - **资金费 EMA 状态**:生产状态与训练回放差,中位 1e-10,最大 1.7%(起点不同)。计划在部署时把生产状态**重播种**成训练口径;08Z 只读干跑:522 名全部可推进、0 拒绝、最大改动 0.45%。资金费腿是书的主体,这是一次生产状态改动,只能和换模型同窗做。请判断:重播种是否正确,还是应该让训练去对齐生产的状态?
   - **资金费腿秩基**:生产比训练多 3 个研究轴(829 名)之外的名(DOS / MARSCOIN / PONS),只影响 fund 腿 z,列为具名残余。能接受吗?
   - **新名历史回填**:生产者每锚只抓 52 根 5 分钟 bar,不会自己补新增 72 名的 40 天历史;不补的话,覆盖率门会让这些名在约 7 天内进不了成员,成员集就和训练规则不一样。回填脚本已写好,未执行:限速 300 权重/分、每分钟记录、超过 1200 中止;09-19 及之前的行必须与 x0918r 逐位相等才写盘。它要调交易所接口(与实盘共用每 IP 权重,E-0919-V),只能在静默窗跑,写生产缓存属部署步骤。

## 边界

全部只读;不碰 `~/dl_quant_live`、`~/wide_shadow` 运行树与 `~/cc_tmp` 下各代理的工作目录(读可以,写不可以);不调交易所;本机重活只在静默窗 [N+1:00, N+3:40];**执行器的任何套件(含单个套件)只经 `ops/run_acceptance_offline.sh` 运行**(E-0923-D:`tests_acceptance_entrypoints` 单独运行会在沙箱外调起整套电池);pod2 禁止按名字杀进程;盲态:不读 CFG-04/06 逐臂数据。

## 交付格式

每条标 P1/P2/P3,附可复跑反例或证据路径。**A.4 与 B.3 请尽早分批回**(不必等全部审完):任何 P1 在对应线上线前必须解决。对五个对象(A–E)各给一个判语:**可以上线 / 修后上线 / 不可上线**。
