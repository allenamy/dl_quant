> **创建:** 2026-07-02 10:38 +08 | **更新:** 2026-07-05 (FINAL VERDICT 定案) | **Session:** fable-regime-breakthrough | **状态:** final | **作废条件:** 被后续 breakthrough 里程碑文档取代

# Fable Regime Breakthrough — BTCUSDT perp y_600 全 regime Pearson ≥ 0.08 攻坚

## 0. User mandate (2026-07-02)

- 之前 (Opus 4.8) 的迭代陷入 local optimum;换 Fable 深挖根因、大幅提升。
- **目标: 各个 regime 上 per-month Pearson 稳定 > 0.08**(2025 H1 / 2025 年底 / 2026 全部)。
- 数据全量在手: spot + perp 的 book/trades;API dump 的 funding rate + OI(多粒度)。
- 机制预期: perp 是 spot 衍生品 —— perp 自身 + spot 自身 + basis 特征理应支撑更准的 perp 预测。
- 核心痛点: 现有模型无法跨 regime 自适应(2025 H1 vs 2025 年底 vs 2026 差异大)。
- 纪律: 代码改动在本地(此分支),server 只训练/测试;不轻易下结论、不轻易放弃、注重细节、经得起推敲;全程记录。

## 1. 起点(诚实基线,继承自 2026-06-28 定稿)

当前最佳 (dual_lob REG_arch, λ_q=0.1, 450d rolling, EMA no-peek), per-month honest Pearson:

| regime | 月 | per-day-CLEAN | DENSE |
|---|---|---|---|
| 强 | 2025-10 / 2025-11 | 0.081 / 0.068 | 0.079 / — |
| 普通 | 2025-08/09/12 | 0.04–0.06 | — |
| drift | 2026-01..05 | 0.012–0.031 | — |
| pooled | 10 mo | **0.0387** | 0.0318 |

→ 0.08 目标 = 强月再 +~15%,drift 月 **3–6×**。已知(待重审)的先前结论: choppy 静态 ceiling ~0.031–0.044、funding/OI 弱、regime 不可因果学习 —— **全部按"待推翻的假设"重新排查,不作为公理。**

---

## ★ arch+loss 迭代 (2026-07-06, 提升 Run1 尝试, Run1 冻结不污染)

用户质疑 → guard-first 迭代。Run1 全冻结, 新臂 configs/arch_iter/ + gated flag(关=逐比特, 双人验证), 判据 raw-y IC(P+S), β 诊断非门。
- **Lever A 永续 concat 融合(回应加法残差跨空间质疑) — KILL/CLOSED**: concat_2025_10 raw-y Δcd −0.0293 / ΔS −0.0225 vs Run1(P/S 同降无分歧, 非 σ 塌缩, bin-mono 0.68→0.48)。**验证了加法残差是对的**: concat 多的容量/扰动在低 SNR 强月过拟合/破坏现货骨干(anti-pattern #29 加通道惩罚)。DENSE 反升(+0.011)但 cd(交易口径)硬退 = 非可交易。fail-fast: concat drift 折不跑。
- **Lever B 尾部加权损失(w=clamp(1+γ|y|/σ,max3)) — KILL/CLOSED**: tailw_2025_10 raw-y Δcd −0.0285 / ΔS −0.0358 vs Run1(强月双退, S 退更多)。★分歧问题答案: **不是 P/S 分歧,是 clean 口径直接双退** —— val 看到的 P↓S↑ 是 DENSE 效应(tailw raw-y DENSE Pearson +0.030 但 Spearman 只 +0.008 = 尾部加权抬大幅度 MSE-fit)。**发现: 尾部加权是 dense-Pearson 海市蜃楼,不是可交易 rank alpha; 拿 clean alpha 换 dense 幅度拟合**(bin-mono 0.68→0.30)。
- **★★ arch_iter 迭代结论(NEGATIVE, 双人验证)**: concat(融合)+tailw(损失)两个 lever 都 KILL 强月(Δcd −0.029/−0.029)。**共同签名: dense/幅度指标升,但 canonical per-day-CLEAN(门+交易口径)退。Run1 的日内-clean alpha 是局部最优 —— 加容量(concat)和幅度重加权(tailw)都把模型推向 dense/幅度拟合、丢掉可交易 clean-rank alpha。** 验证 Run1 现设计(加法残差 + 均衡损失)是弱信号稳态最优。**Run1 仍 ship, 冻结不动。in-architecture 提升穷尽 → 真杠杆在盘外数据/事件时间采样。**

## ★ 核心质量指标方法论 — IC 是 alpha,β 是量纲 (2026-07-05, 辩证定案 → CLAUDE.md 已固化)

**触发**: 用户质疑"追 β 校准是否必要、β 是否真由模型质量决定"。辩证推导结论 = **β 水平主要是量纲,不是质量;优化只该追 IC。**

**代数支点**: β(y-on-ŷ 斜率) = cov(y,ŷ)/var(ŷ) = **r · (σy/σŷ)**,r=IC。β = IC × 纯尺度比。
- **证明 β 非质量**: ŷ×c → IC 不变(尺度无关)、β→β/c。**β=3 与 β=1 可为同一模型差一标量,IC/排序/交易相关量全同。** "好预测"不内在产生 β≈1,尺度产生的,而尺度事后随便标定 (β-rescale 健康修复之所以合法 = 它什么真东西都没改)。
- **禁止**: 把 β 水平当质量门;把 "β 改善" 当 alpha (IC 不动的 β 变化=分布/尺度移动)。实证: lambda_beta_calib 损失项 (Track R) 反向/NULL — 训 β→1 没帮有时伤 IC。
- **β 的合法角色**: (a) 塌缩/衰减监视 (真守卫是 σŷ/σy,β 是症状); (b) **跨-regime 稳定性** — β 逐月乱摆=σŷ/σy 漂=真鲁棒性信号,一次 rescale 修不了 (看方差非均值)。
- **部署幅度** (Kelly/净成本门): 事后校准层 (val isotonic/线性,IC 不变),不训进模型。
- **HFT/系统化实务**: 关注 IC·IC-IR·rank-IC·换手·半衰期·容量·净成本 Sharpe·回撤;原始信号 β 非 headline (优化器中性化尺度);β-校准只对 magnitude-sizing/净成本 taker-gate 相关。
- **自我纠正**: 之前把 basis 的 β 1.95→0.89 当利好 = 错 (IC 不动则那是尺度变化非 alpha);basis 价值只落在 deploy cd ΔP +0.0110 (噪声地板),β 不加分。且之前因 Run1-2025-10 β=3.13 叫它"不健康"也错 (它 IC 最高 0.1025,β 是 rescale 假象)。

**一句话: 信息(IC)难挣,量纲(β)是后处理一步。追 IC/rank-IC + σ-不塌 + IC 跨月稳定;β 水平交给事后 rescale。**

---

## ★ 净成本 taker/maker 回测 (2026-07-05, 强-preliminary 待 0B 审计)

**动机**: 用户质疑 deploy-demean 口径低估持续方向 alpha + 错误强制多空对称。改用净成本回测(尾部选择+决策层去bias+非对称+滞回+成本网格)。taker_backtest.py(0C, battery 全 6 PASS: 因果/shuffle-null/oracle/成本符号/滞回降换手/非重叠, 2 独立数据集验证)。
**头条(盈亏平衡单边成本, clip-target bug 已修用共同 raw y_true)**: **RUN1 0.760 bps vs 生产 0.424 bps = Run1 扛成本 1.8×(修正前 0.864/0.394/2.2×, clip-target bug; 结论 holds)**。RUN1 maker@0.5=+2117(正); PROD @0.5=−831(负)。⇒ **Run1 = maker-可交易(好费率档,break-even 0.76);生产 = 否;两者都非稳健 taker-可交易(pooled break-even≪1.7)**。逐月 Run1 赢多数可交易月(强/正常+晚drift;deep-drift 02/03 两弱)。hit 0.51-0.57。
**milestone 对账完成(无矛盾无 bug)**: pure-taker 2.8 = **强月+clip 口径构造**。引擎强月 clip 复现: 2025-10 taker Sharpe @1.7=6.17 / break-even 3.0bps → 强月真·taker-可交易;其余月 ~0/负,drift/choppy 死。clip±5σ 灌水 +0.6-1.1 Sharpe(纯口径)。**诚实全期 break-even 0.42-0.76 不矛盾,milestone 是强月+clip+有利年化。同 regime 指纹: 强月真赚(连 taker)/drift 死/pooled 被拖到 maker-only。**
**经济学结论**: **"Run1 vs 生产"提升是质变(不可 maker→可 maker),非 deploy-demean 的 +0.0047 小数** —— 用经济正确指标(break-even 成本)Run1 明显胜。日内自评层叠加胜者(drift +~0.009)。
**0B 双审计 CLEAN(引擎 5/5 + 数据prep, 2026-07-05 GATE CLEAR)**: 引擎因果(方向性泄漏测试)/非重叠/成本账本/滞回/oracle 全 PASS;数据prep node-identity(110,819 共同节点,同 ts+y_true,仅 pred 不同)/共同实现序列/denorm 正确。battery 全 6 PASS 双 CSV。**Run1 shuffle-null 真实毛 3023.6 vs 打乱 195.6 = 稳健显著(z=2.03 是生产,Run1 不 marginal)。** 破 break-even 精确复现 RUN1 0.760/PROD 0.424。**★经济结论(可信): Run1 经济上明显胜生产(break-even 0.760 vs 0.424,+80%),maker-可交易 vs 生产弱/边际,两者 pooled 非 taker。★★关键: deploy-demean(+0.0047)低估 Run1 —— 真实净成本 taker 回测给的边际大得多(0.760 vs 0.424)→ 口径之争 cd +0.0137 侧更近经济真相,用户质疑 deploy-demean 正确。逐月强月真赚(2025-10 BE 1.94)/drift 负(2026-03 −0.66),同 regime 指纹。Run1 edge 活在 maker 经济学。**
**★★ 尾部选择性扫描 DECISIVE(2026-07-05, taker 问题最终答案)**: RUN1@1.7 top-f{10/5/2/1/0.5%}: **无截断过 taker 1.7 per-side**(best top-1% per_side 1.233<1.7, net −251, boot frac>0=0.33 跨0);per_side 跨截断乱(0.40→1.04→−0.01→1.23→−0.10)=噪声非真尾部edge;因果 expanding-prior 更低。**+1725 海市蜃楼杀掉**(=生产 cost-aware 路径,boot CI[−675,+4641] 跨0 z=1.35,换 Run1 翻 −200,model-fragile+阈值artifact)。H1 短>长每截断证实(hit 0.55-0.58 vs 0.51-0.53)但太薄(唯一过线 top-1% 短尾 per_side 1.882 但 net+44/121笔/boot 0.53 掷硬币)。**maker 费率精确: Run1 仅 maker≤0.76 bps/side(高VIP/返佣)可交易,零售 maker 2bps 水下 ~1.24;milestone retail-maker 4.4/taker 2.8 = 强月+clip+低费构造,诚实 pooled 不成立。** RUN1 gross z=8.62(强显著,z=2.03 是生产)。★**最终经济定论: 单资产 y_600 = maker-only 信号且仅好费率档(≤0.76bps/side),非 taker-可交易(连最聪明尾部/短偏都不 robustly 过 1.7),非零售 maker。Run1 真实强显著、经济胜生产,但成本地板绑定。**
**已清 ✓**: (a) 0B 双审计 CLEAN; (b) 尾部扫描 DECISIVE; (c) milestone 对账完成
**强月-vs-pooled 尾部分解(2026-07-05, 收紧最终 taker 定论)**: 肥尾每笔边际**任何 regime 都不过 taker 1.7**(pooled max 1.233 / 强月 max 1.194 / drift 1.003,全 net-负)。**修正"强月 taker-可交易"**: 2025-10 BE 1.937>1.7 但 = ①一个月 ②靠 carrying(持有 winners 跨期)非每笔尾部edge ③raw 肥尾 net −62,milestone 6.17 是 clip±5σ 灌上。唯一过线逐月尾部格 = 2026-01(drift,n=167,不 generalize)。★**最终 taker 定论(收紧): 单资产 y_600 非 robustly taker-tradeable —— pooled/肥尾/强月每笔 均不过;唯一 taker-正足迹 = 2025-10 full-strategy-with-carrying(一月,BE 1.937)+ 2026-01 一月尾部 blip,皆不 generalize。maker-only(≤0.76bps)是真结论。**
**rank-body 论 FALSIFIED(2026-07-05, ship 决定)**: combo(state+rank) vs Run1(state-only), node-identity OK。§3b rank-body(判定用 body-IC 非 β): **combo rest80 −0.0236 vs Run1 rest80 +0.0078 → Δ −0.0314,combo 反而负**。排序 state-only +0.0078 > rank-alone +0.0035 > combo −0.0236。cd combo +0.0100 vs Run1 +0.0175(−0.0075 更差)。(β 1.95→0.29 塌但按铁律 β 是症状非判据,rank 被拒是 body-IC 转负。)⇒ **rank overlay 死重、叠 state 上有害(交互毁 body IC),rank 论(平稳 rank 输入抬 drift body 离 H1~0 地板)证伪。SHIP STATE-ONLY(Run1)。**(cost-aware 版 @1.7 曾 +1725,测 top-10/5/2/1% 是否稳过 taker + 显著性 + leave-one-month + 多空分开-H1 短尾); (c) milestone 对账(retail-maker 4.4/taker 2.8 疑似乐观 clip+demean 口径 vs 此诚实 raw)。

## ★ FINAL VERDICT (2026-07-05, 7-月 OOS 轨迹定案)

**目标(全 regime per-month Pearson ≥ 0.08)在盘上数据里不可达** —— 穷尽架构(仿射 FiLM / 低秩 LoRA)、特征(rank / combo)、目标(demean-align / aux)、优化(选择器)四条路,均证伪。核心机理: **"帮难月"与"保强月峰值"是数据里不可调和的 trade-off,没有冻结单模型能同时做到。**

**7-月样本外 deploy 口径(0B 确认):**
| 方案 | 7-OOS deploy 均值 | vs always-Run1 |
|---|---|---|
| **always-Run1 (bugfix)** | **+0.0339** | — (推荐) |
| 因果路由 {Run1 净多 / LoRA 净空} | +0.0358 | **+0.0019(可忽略)** |
| oracle (上界) | +0.0358 | — |
| 生产基线 | +0.0292 | (Run1 −生产 = +0.0047) |

**三条定案结论:**
1. **因果路由样本外不挣饭钱**: router − always-Run1 = **+0.0019 均值**(仅差在 2026-05 一个月,deploy LoRA−Run1=+0.0131÷7)。样本内去杠杆优势 +0.028 未迁移 OOS。
2. **诚实单模型 = always-Run1(bugfix substrate),无需路由**: 相对生产 +0.0047 deploy,但集中在单月 2025-08(leave-one-out 去 08 → net-long 半塌到 +0.0021),非稳健系统性提升。0/6 net-long 月达 0.08(2025-08 最近 0.080)。Run1 = bugfix(regime-FiLM 吃 post-RevIN + batch-z / mask 泄漏 / state 从未接入),**非新架构**。
3. **唯一正交真赢 = 日内自评部署层**(用模型自身上午实际命中因果调下午仓位): drift 下午 IC ~2.1×,自门控保强月零损,全天 deploy +0.009。叠加在 always-Run1 之上。

**全程无泄漏**(450d walk-forward + causal state + 预先 commit 路由地图防偷看 + state-permute null −31%)。**下一博(未验证,需用户拍板): 事件时间采样(volume/event bars)** —— 机理对症(信号住在成交爆发时刻),但需重建缓存管线。

### ★ 架构审计(2026-07-05, 代码核实): headroom 未穷尽 —— Run1 对 basis 基本"盲"
Run1(d1_*_run1)代码级核实: 88 通道 = 64 spot + 16 perp-trade + 8 cross;basis 仅 2 个瞬时通道(80 `mid_ratio_log`、81 `basis_bps`)**且 RevIN 每窗口把它们的 level de-mean 掉 → 均衡距离信号被中和,只剩窗内 wiggle**。funding/OI/premium/positioning **完全不是 Run1 输入**(regime_prior=6 个纯 vol 描述子,d_prior=6,state 全 off)。regime-FiLM 只吃 channel-0 + vol;ppnet_gate 在 multistage 下 dead;X_long 长上下文 built 但 dataset 从不返回。**⇒ 对一个衍生品(perp)预测问题,模型对其定价核心(basis)几乎不感知 —— 这是机理硬缺口,非穷尽。**
**机理正当 + 有证据 + 未落地的杠杆(排序):**
1. **basis-DYNAMICS block(最强)**: `add_basis_dynamics.py` 已建 8-10 特征(basis_z 均衡距离 / basis_ar1 反转 / 动量 / leadlag / arb_pressure)→ cache `npz_v2arch_aug`(X=98),但只在一次性 `dp32_aug_2026_05.json` 测过,**从未进 Run1 口径**。Ridge 已给 **+0.0076 clean(2026-05 choppy 0.036→0.044,过 +0.005 门)**。真实、量化、未 scale 测。
2. **RevIN-skip 保 basis level(近零成本)**: bypass hook(revin_skip_idx)已存在且在 rank 臂验证过接线,只是 run1 从没对 basis(80/81)用 → 开一下就能让均衡距离进骨干。
3. **funding/OI 作交互条件(非加性)**: 加性 Ridge 弱(+0.0012),但设计的 funding×microstructure 交互 + OI-regime FiLM 针对 drift 月 regime 反转(记录在案的失败模式),未过 Ridge 门进 run1。证据较薄但机理对症。
4. **长上下文 coarse 分支**: X_long(含 l_basis_bps)leak-safe 但结构上未消费;无先验 Ridge ΔP。
**修正: 不是"其余 IC 杠杆已穷尽" —— basis 机理线(lever 1/2)代码就绪、Ridge 已验证、便宜,headroom 真实存在。0C 正复现 basis-dynamics Ridge ΔP + 正交性。**

### ★ 0C 严格复现回泼冷水(2026-07-05): basis headroom 被高估
audit 的"+0.0076 = 强 headroom"过度乐观。0C 把 basis_cache(8 feat)作 Ridge-on-y_pred(post-hoc,walk-forward,per-day-CLEAN)测:
- drift pooled Δ=+0.0054 **但在 shuffle-null 噪声地板内(max|null|=0.0034)**,单月驱动(2026-01 +0.0236;2026-03 −0.011/2026-05 −0.005 负),**且伤强月 2025-10 −0.029、choppy 2025-12 −0.047**。
- **分解(杀 RevIN-skip 乐观): 每个特征单独在 y_pred 上加 ~0;basis_z 均衡距离(RevIN 中和的那个正是它)加 NOTHING**。standalone raw drift IC 小(basis_z +0.009/basis_bps +0.008/mom +0.016)= basis 有一丝 drift 信号但**已被 DL 的 book 通道捕获**。
- 与 c7e3c6c +0.0076 调和: 那是 vs **线性 Ridge**(弱 baseline);vs 部署的 DL **不存活**(2025-12 −0.047)。
- **唯一残余未知**: 线性 Ridge-on-y_pred **看不到骨干内的非线性 basis 交互**,无法完全 bound "RevIN-skip(80/81)+basis-block 的 DL 重训" → 那个 DL 杠杆**真正未测**,但 given standalone IC ~+0.008 + post-hoc 噪声地板邻 + 伤强/choppy,**清 +0.005 clean 的先验 LOW**。
- **短×funding 交叉(#2)**: real 但 sub-gate(~+0.002-0.003,H5 完美条件化上界),不值一个 channel(anti-#29)。**day-IC oracle(#3)**: dead,可利用部分(morning→afternoon)已被日内自评捕获,余 ~80% 采样噪声无跨日持续,irreducible。
**RANKED: basis(marginal,值一次便宜 RevIN-skip DL 测,低预期,预期伤强/choppy)> 短×funding(real,tiny,execution-only)> day-IC(dead)。净: 无 on-disk 因子在 DL 之上清稳健 +0.005 drift → 与 FINAL VERDICT 一致(on-disk 数据 cap < 0.08)。** 修正: 慢状态通路机理美但线性证据弱;唯一未 bound = 非线性 DL 重训(低先验便宜赌注)。

### ★ basis DL 测试 BLOCKER(2026-07-05, 验证抓到): 干净 basis 在测试月建不出
0B CPU 数据核查(用户"数据准确无误"硬要求): **处理后的 spot 缓存 npz_v4 到 2025-09-30 断,覆盖不到 2025-10/2026-01** → basis=perp−spot 在测试月无法干净构建(perp 缓存全,spot 缺半)。**这个赌注不再"便宜": 干净版(a)需从 Tardis 延 spot 缓存(真实工程,新月管线未验证);近似版(b)用 npz_v2arch 带±clip 瞬时 basis 重建=漂移伪影,违背严谨;(c)推迟。** ★重构: spot 缓存 2025-09-30 截断是**所有 spot-perp 联合工作的地基缺口**(不止这一测) → 决策变成 scope: 窄测(低先验,不值 build,defer)vs 承诺联合方向(延 spot 缓存=地基投资,一次解锁 basis+跨book lead-lag+clean level)。**RECONCILE 结论(2026-07-05): (ii) —— 有干净 spot 源,0C 低先验成立,"阻塞"是虚惊。** 我报的 2025-09-30 截断是看错**单资产** npz_v4/npzv4_dual;**多资产轨道有独立全量干净管线**: mid_cache(2023-08..2026-05,直接读 Tardis 原始 book_snapshot_25 现货/永续)、npz_spot(1247d 全量)、basis_cache(±50bps,2026 实值 −4~−7bps 量程内≈未 clip)。实值核查非退化(2026-01-15 −4.59/03 −5.26/05 −4.80)。**0C 测的就是干净数据 → 低先验成立(choppy 加性 +0.0074≈89% oracle 顶但伤/平强月;叠 DL 之上噪声地板)。且 basis DL 测试其实便宜可建(2025-10+2026-01 干净输入都在盘,add_basis_dynamics 只需 npz_v4→npz_spot 重指,无需 Tardis 重拉)。** ⇒ **决策: 不投地基;basis DL 确认测试便宜、低先验,值一次干净跑把 basis 线在 DL 层面(非仅线性)彻底关掉 —— 预注册 kill 门,过则意外之喜,不过则封顶结论坐实。(0B 无法定位确切"+0.0236"artifact,但凡能产 2026-01 数的 basis cache 都是上述干净链。)**

### ★ basis DL 测试 — 验证全 clear + 判据锁定(2026-07-05, 待 GPU)
**数据构建准确无误(用户硬要求)已达成**: 缓存 `npz_v2arch_augms`(98ch=base-88 逐字节一致 + X_basis 10 dynamics 追加,非破坏性写新目录);**fold 窗口 bit-identical 于 Run1(2024-05-01 起,两 test_start 严格同 train/val/test 天)= 数据/fold 级 apples-to-apples**;配置与 d1_*_run1 仅 4 处差(npz_dir/revin_skip_idx=[80,81,88..97]/output/comment)。**0C 泄漏审计 4 项全 CLEAN**(时间戳同秒对齐、每特征严格≤t 含 leadlag=trailing corr(perp_t,spot_{t−k})、raw 写入训练窗归一、shuffle-null 未超噪声地板)+ **0B future-corruption sentinel 在真实 X_basis 上证 ≤t**。**判据(收紧,因 #29 加通道惩罚+±0.01 init 方差,单 seed 不测 seed): 2026-01 drift ΔP≥+0.01(明确超噪声带)且 2025-10 强月 ΔP≥−0.005 → 过;带内/负 → basis 线 DL 层面关闭,收尾。** 待 0B 全量构建完 + 排 GPU(补全折后)。
**★ 预注册终锁(见结果前,2026-07-05): 基线 = run1 实际 cd(2026_01=0.0175 β1.95 / 2025_10=0.1025),非 statusline BASE。CLEAN PASS iff cd≥+0.0275(ΔP≥+0.01) 且 β≤1.95 且 σ≥0.02 且 DENSE>0;SUSPECT(flag 非 auto-win): cd 过但健康退化(β胀过1.95/σ<0.02/DENSE≤0)=校准假象风险#23/#24;LINE CLOSED: cd∈(0.0075,0.0275)带内。强月 basis_2025_10 not-worse iff cd≥0.0975。验证 100% CLEAN(0C 4 项代码审计+真实 X_basis(10)全 10 月 shuffle-null 111,064 行+base-88 逐字节;0B ≤t sentinel;4 路印证无异议)。预注册预期(0C 先验): MARGINAL — basis 叠 DL 上 ~+0.005 drift、单月驱动、伤强/choppy < +0.01 门 → 先验指向 WITHIN-BAND=线关闭。测试确认或推翻之。~3h 出。**
**★ basis_2026_01 落地(边界结果,2026-07-05): cd 0.0274 / ΔP +0.0099 vs run1 0.0175 / β 0.893(从 run1 的 1.95 大幅改善!)/ σ 0.051 / DENSE +0.0457(升)。按预注册规则: cd 0.0274 < 门槛 0.0275 = WITHIN-BAND → drift 未过 +0.01 干净门 → basis 线关闭(严格执行,不追 seed)。但诚实: 落带最顶端(+0.0099≈+0.01)+ β/校准真实改善(RevIN-skip 保 basis level 确实帮了健康,只是没转成 alpha)。单 seed ±0.01 方差下 +0.0099 本质不可判 = 预注册"带内=关闭"正当。裁决: 无干净 alpha 增益但有真实校准改善 = 弱正非决定性。强月 basis_2025_10(代价检查)训练中→ 决定 basis 是"无害弱正"(不伤强)还是"不值"(伤强)。0B/0C 出 deploy+headline_audit。**
**★ basis_2026_01 deploy audit(0B, 2026-07-05): RAW cd ΔP +0.0098(带内,门用此=关闭) vs DEPLOY cd ΔP +0.0110(勉强过 +0.01,决定性/免慢频带口径)。健康两口径都真实改善(β RAW 0.89/DEPLOY 0.47 均优于 run1;DENSE/σ 均升)=RevIN-skip 保 level 真实校准增益非灌水;但 BEST checkpoint 弱(RAW +0.0074/DEPLOY +0.0046)=EMA-specific/checkpoint 敏感。口径张力(诚实): finale 决定性口径一贯是 DEPLOY,basis 在 DEPLOY 过 +0.01;但预注册门设在 RAW cd,RAW 未过 → 坚持不 caliber-shop,RAW 带内=线关闭,但公开 deploy 过了。裁决(drift): 真实但边际弱正,正卡 +0.01 噪声地板,非零非干净胜。强月现在真决定处置: 不伤强=无害真实弱正(用户拍板 追/不追)vs 伤强=不值收尾。**
**★★ basis 最终裁决(2026-07-05, DL 层面彻底关闭): basis_2025_10 强月 cd 0.0656 vs run1 0.1025 = −0.0369(DENSE 同步 −0.0316,真 IC 损失非 β 假象)。预注册门 强月≥−0.005 → FAIL(−0.037≫门)。合并: basis drift 仅噪声地板弱正(+0.01)但强月重挫 −0.037 = 净负,不值。证实 0C 先验(basis 伤强/choppy)。最后一个机理杠杆 DL 测过失败 → basis 线关闭,不跑复现(复现是强月干净的条件分支,不成立)。FINAL VERDICT 更坚固: on-disk 数据 0.08 不可达,已 DL-测 basis。资源→Branch B(2025-H1 回补最终表)或收尾,待用户。**

### 两层"样本内/样本外"辨析(避免混淆)
- **层一 = 模型训练: 每一折(Run1/Run2/LoRA 全部)都严格样本外** —— 450d 训练 → 预测从没见过的未来 28d,test cd 在模型层面无泄漏。
- **层二 = 路由规则设计: 分叉在此**。tt-sign 规则是用 3 个月(2025-10/2026-01/2026-04)挑出来的 → 这 3 月是"对路由样本内"(规则在其上必好看);另 7 月(2025-08/09/11/12+2026-02/03/05)冻结规则后检验 = "对路由样本外"。**"样本内 2026-04 Run2 赢 +0.028"= 造路由的月;"样本外 2026-05 缩到 +0.005/+0.013"= held-out 月**。不是模型泄漏,是路由设计泄漏 → 7 held-out 月才是路由诚实成绩。
- **always-Run2 列(补全中)**: net-long 月 state 非每月拖 —— 2025-08 Run1 0.080>Run2 0.052,但 2025-09 Run2 0.058>Run1 0.049。精确说法: state 平均略拖 net-long、非每月拖;路由指向 Run1 会保守错过 2025-09 的小胜(不可因果预知)。

---

## 2. Phase 1 — 全面梳理 + 根因 (workflow `regime-breakthrough-p1`) — DONE 2026-07-02

完整原始产出: `docs/2026-07-02_phase1_findings_appendix.md`(14 agents, 全部对抗验证)。

### 2.1 根因 verdicts

| 假设 | verdict | 决定性数字 |
|---|---|---|
| **H1 崩塌形态** | **SUPPORTED (0 refutes)** | drift = **尾部-only 存活 + 严重 β 衰减**: top-20%-\|pred\| IC_conf +0.030,其余 80% IC **+0.0002(纯噪声)**;短侧尾部显著(bot-decile hit 53.2%, z=2.54)长侧死;cov(p,y) 掉 4-6× 而 σy 不变;**预测幅度反而涨(σp 最大在 2026-04)= 过度自信**;2026-04/05 gated 后也 ~0 |
| H2 日级 IC 门控 | REFUTED | 描述子→IC 关系 2025 ρ+0.35 → 2026 ρ−0.03(**门在需要它的 regime 里失明**);日 IC ~80% 采样噪声 |
| H3 动量/反转态 | REFUTED | **"动量-flavored 信号"叙事错了**: 最强月 2025-10 是最均值回复的(VR3 0.64);两态信号都正;翻转一致毁值 |
| H4 staleness | REFUTED | 月内零衰减(slope p=0.78);月界 vintage 刷新无跳变;**drift = 月度概念跳变,day-1 就在**;在线学习不是杠杆 |
| H5 funding/OI 日级条件化 | REFUTED(但见 2.2-③) | 完美条件化天花板仅 +0.002-0.003;**但 short-decile×funding 交互真实且更强(F3−F1=−3.59bps, 日聚类 t=−2.43, p=0.016)**;day-IC oracle **0.1246** vs 描述子解释 ~1% |
| H6 regime-匹配训练数据 | REFUTED(中高) | drift 月窗口内已有 2-3/5 最近邻;窗口构成不预测月度 P(oracle 描述子下 ρ≈0) |

### 2.2 关键新发现(改变全局的)

1. **★ 先前所有 regime-conditioning FAIL 均基于两个结构性 bug**: regime-FiLM extractor 吃的是 **post-RevIN** x_feat(绝对波动被抹掉)+ 描述子 **batch-z-score**(uniform regime shift 不可见)→ 机制对 regime level 全盲。"regime 不可学"结论从未在修复后重测。(`src/model/regime_film.py:64-101`)
2. **★ 模型输入里完全没有 funding/OI/positioning/premium**(数据全在盘上): X=88ch(64 spot 手工 + 16 perp-trade + 8 cross-venue),regime_prior 仅 6 个 spot 派生特征。positioning 家族从未作为**非线性模型输入**测过(只测过线性 Ridge 加通道 + 坏 FiLM)。
3. **short×funding 交互是真实、显著、未跟进的结构**(执行侧短门 ~3bps/笔 + 候选条件输入)。
4. **day-IC oracle = 0.1246**(vs 基线 0.0366): 巨大可利用 regime 方差存在,只是已测描述子解释 ~1% → 描述子搜索要换族(liquidation-proxy、跨资产 dispersion[13 alts 在盘未用]、order-flow persistence、session)。
5. drift 折 checkpoint 在 patience 耗尽处选中(best_epoch 15-18 vs 2025 的 4-11)→ val-selection 健康度未审计;β∈[0.19,1.82] 不稳未解释。
6. 未验证的 WIN: mh180(+0.0139 单折)、choppy-specialized training(0.0167→0.0311 OOS)—— 都没多折确认。
7. 口径 bug 小项: backtest CSV 有 82 行 y_true==0(mask 泄漏,非驱动因素,要修)。
8. npz_v2arch cache 从 2024-01 起;2023 年(2026 drift 月的最近邻 regime)不在 cache 里;回建 ~58GB/306d 可行。

### 2.3 被退役的叙事(设计不再基于)
"动量信号只在趋势市付钱"、"choppy 不可预测 = 在线重训才能解"、"funding/OI 已充分测过=弱"、"regime 不可因果学习"(基于坏机制)。

## 3. Phase 2 — 分阶段实验计划 (DONE 2026-07-02; 完整版 `docs/2026-07-02_phase2_design_appendix.md`)

用户加权(2026-07-02): **模型本身捕捉 alpha 优先** —— 架构 / 特征 / 因子构造 / 数据处理 + 高效训练;执行侧层为附属。

**评估协议(全阶段固定):** 同 10 月基线(post-mask-fix 重聚合)、per-day-CLEAN + DENSE 双赢才算、always-EMA no-peek、σŷ/σy≥0.02 + β∈[0.5,1.8] + bin-mono、配对 day-block bootstrap 排除 0、逐折 sign 一致、新特征 shuffle-future null + ≤t join + trailing-vol double-sort、zero-init 模块 bit-identity + batch-invariance 测试。

| Stage | 内容 | GPU-h | Kill gate |
|---|---|---|---|
| **0 (零 GPU)** | 0a mask 修复+β band 统一+基线重聚合;0b trainer 仪表化(per-epoch val 史/σ-fallback/ckpt 溯源);0c 因果再校准层(trailing-β̂+tail-rank+short×funding,部署侧);0d D1 CPU 预门(PreRevIN 描述子月间分离>1σ);0e D3 因子(**liquidation-cascade proxy from 盘上 perp trades** + basket-ECM/breadth + flow-persistence)Ridge 门 on 2026-01..05;0f state_prior overlay(18-d funding/pidx/OI/L-S 多尺度) | 0 | 0c: pooled lift<+0.004 kill;0e: cascade/ECM drift Δ<+0.005 kill, flow<+0.003 |
| **1** | D1 A/B: {2025-10 守卫, 2026-01, 2026-04} × {Run1 bugfix-only, Run2 +state d_prior=24+output-gain},born-instrumented | 12-20 | drift Δ<+0.003 且 β 未向 1 移 ≥0.15 → "regime-conditioning post-fix DEAD" 定案 |
| **2** | CPU 选择器扫描(4 个预注册 selector on Stage-1 epoch 菜单) | 0 | oracle-gap<+0.008 kill;需捕获 ≥50% gap |
| **3** | Ridge 过门因子的 DL 接入(zero-init aux head + state 拓宽)5 折;机会位: mh180 多折 + choppy-specialist 复制(兼 H6 干预试验) | 14-40 | drift Δ<+0.005 pooled |
| **4** | 集成 + 全 10 月确认 + **2023-09..12 cache 回建 + 2025-01..07 回补**(2025-H1 mandate + 零 GPU wins 的出-发现-期确认) | 20-50 | leave-one-out 归因矩阵 A0..A7 |

**预算:** ~6-9 build 天 + 46-110 GPU-h,全 kill-gated,首笔 GPU 在 ~4 天零 GPU 门之后。

**诚实底线(合成器,预期校准):** H1 封顶重校准/选择/加权类杠杆 —— 2026-01..03 可恢复至 ~0.02-0.045,2026-04/05 现有信息 ~0;唯一可能动 04/05 的是新信息(cascade proxy 全 drift 覆盖在盘、basket-ECM),诚实合并 best case drift ~0.035-0.06,**非 0.08**;若 D1 门 + D3 Ridge 门全灭,校准结论 = 盘上数据不可达稳定 0.08 → pivot Tardis liquidations feed。另: 2025-08/09 失败是统计功效(t<1)而非 drift,由 Run1/mh180/specialist 攻。

## 3.5 Loop 重构(2026-07-02,用户加速令)

**根因三瓶颈:** ① 信息(drift 80% 预测为噪声,conditioning 修不了零分子 → 改训练分布/目标);② 决策噪声(单 seed cd 方差 ~±0.005 与目标增益同量级 → seed 复跑 + 选择器);③ 速度(2.2h 串行 run)。

**Loop engineering:** 持久队列 runner(队列文件驱动,自动评分+kill 判定,GPU 不空转)+ batch 1024/sqrt-LR(等效性校验后全臂采用,~2×)+ epoch-5 早停止损(预注册)+ 2025-10 守卫延后只跑胜者。

**臂队列(证据背书,优先序):** 2026-04 对(Stage-1 收尾)→ b1024 校验(兼 Run1 复跑)→ **choppy-specialist**(唯一 drift 2× 证据 0.0167→0.0311)→ **mh180**(+0.0139 单折)→ Run1 seed-7(噪声尺度)→ **尾部加权训练**(H1 对策,k=2.0 预注册)→ 胜者守卫。并行零 GPU: Stage-2 选择器扫(2026-01 双菜单已在手)。全臂 kill gate: 双 drift 折均值 Δcd < +0.004 判死。

## 3.6 大-edge 优化点重排(2026-07-03,用户指令: 砍 mh180,深挖更大 edge)

数据事实 → 机理 → 杠杆(按 edge×成本×置信): ① **SWA epoch 权重平均**(零 GPU;V4-y600 历史已验证 +0.010;7 组 per-epoch ckpt 在盘)—— 杀单 seed 方差,可能替代/增强 S4;② **q-spread 置信加权**(零 GPU;DAQH 的 q10/q90 从未部署使用;H1 尾部-only ⇒ GLS 加权直接抬 Pearson);③ **训练-部署对齐(ALIGN 臂,loss/目标构造)**: 训练 raw、部署 demean 的错配 = artifact/β 乱摆的居所 → demeaned-target 训练(eval 仍 raw,守 #18)+ deploy 口径 gate;④ **特征漂移审计 → 因果 rolling-rank 变换**(数据处理): 静态 z + clip 在 drift 月喂出分布输入 = 80% 噪声体嫌疑,rank 变换按构造平稳。不做: 训练分布类(spec/tail 证伪)、加通道、day-gating、在线学习、多尺度(历史 NEG)。

## 4. 实验记录 (Stage 0 起,滚动更新)

- 2026-07-03 **spec_2026_01(choppy-specialist 首折)= ARTIFACT 判定**: raw cd +0.0544(4.4×)但 DENSE −0.0198/β −0.719(预注册反号警报);零 GPU 部署契约测试裁决 —— **1h 因果 demean 下 cd 塌 92%(0.0544→0.0044),而 Run1 对照只损 50% 且保持健康** → +0.0544 是 choppy-only 训练诱发的**多小时级 level 失准分量**,不是 10min alpha(1h demean 全灭、24h demean 几乎不动 = 信号住在 >1h 频带)。blend(0.5spec+0.5Run1)raw 口径好看(cd +0.047 健康)但 demean 后塌回 Run1 平价 = 同一慢频带信号换装。按天:79% 正但头部集中(去 top-3 → 0.038;有一天 −0.391)。**不计入 arm gate;D6 原"0.0167→0.0311 WIN"高度可疑(大概率同一 artifact,原测未过部署契约)。** spec_2026_04 跑完做同一四件套确认机理复现。
- 2026-07-03 **★ Stage-1 Run2 gate PASSES —— positioning conditioning 复活(D1 论题首个正面证据)**: d1_2026_04_run2(bugfix+18维positioning state+output gain)cd **+0.0715(Δ+0.0407 vs 基线 0.0308,2.3×)**、DENSE +0.0411 同号(Δ+0.0228)、**β 0.190→0.751 带内**、σ 0.055、无 fallback。Run2 双 drift 折均值 Δcd +0.0203 >> +0.003 门。**与 spec artifact 的反向签名(DENSE 同号 + β 带内)+ 机理吻合**: 增益恰好集中在 positioning 分离最强的月(2026-04 = tt_level 2.3× 去杠杆 regime,0B 的 CPU pre-gate 预测),分离弱的 2026-01 ≈ 基线 —— 条件化在"该起作用的地方起作用"。待办: 1h-demean 部署契约确认 + Run1-04 归因补跑(分解 bugfix vs state)+ 单 seed caveat。
- 2026-07-03 **2025-10 守卫(Run1)**: cd 0.1025(Δ+0.021,守卫 PASS)但 **β 3.13 出带 + σ 0.020 压线 + DENSE −0.017 = HEALTH-FAIL,且 cd↑/DENSE↓ 分歧方向与 spec artifact 相同 —— 0.1025 未过部署契约前不可 headline**(审计中)。
- 2026-07-04 **轨迹逐月(net-long backbone,诚实喜忧参半)**: Run1 bugfix cd vs 基线: 2025-08=0.0798/0.032(Δ+0.048 翻倍)、2025-09=0.0493/0.043(Δ+0.006 平)、2025-10=0.1025/0.084(强月)、2026-04=0.0417/0.031(去杠杆)。**net-long 月 bugfix ≠ 一致优于生产基线(诚实反转): 08=+0.048 大胜 / 09=+0.006 平 / 11=0.0485 vs 基线 0.067 = −0.019 负(强月反而更差)。** **6/6 backbone 齐(完整 net-long OOS 主线)** Δ={08:+0.048, 09:+0.006, 11:−0.019, 12:+0.009, 02:≈0, 03:+0.014} 均值≈+0.010,4/6 为正(08/03 翻倍)。**两条诚实结论同时成立: ① 相对基线 bugfix 有真实但小的平均增益(+0.010); ② 绝对水平 6 个 net-long 月只有 2025-08(0.080)接近 0.08,其余全在 0.018-0.058 → 即便路由到最好模型,大多数月份离 0.08 还很远。** ★★ **核心诚实结论: 0.08-全 regime 目标在盘上数据里未达成,大多数月份 cd 0.02-0.06,与 regime 无关。** 待 lora_2026_05(去杠杆 OOS)+ Run2 对照 → OOS 表(router vs always-baseline/oracle)。 **★ net-long 半 OOS 表定案(leave-one-out 稳健性一击): router(=Run1)均值 0.0468 vs 基线 0.0372=+0.0096,但去掉 2025-08 → 塌到 +0.0021 几乎持平;4/6 正是抛硬币,bootstrap CI 跨 0 → bugfix 在 net-long 未见月 ~等于生产水平,只 2025-08 一个真强月,非系统性提升。0/6 月达 0.08(2025-08 最近 0.0798)。可交易性(较好一面): deploy 保留 ~70%(短期信号非慢频带,过 deploy 合约),但只 2025-08(deploy 0.065)有意义可交易,09/11/12(0.033-0.044)净成本边缘,02/03 近死。** **干净 deploy-β 上修: 4/6 未见月 deploy-HEALTHY(β∈[0.5,1.8]+DENSE正+σ≥0.02,即 2025-09/11/12+2026-03)—— 净多信号不只相关,在 4/6 月是校准良好的,只是水平温和(deploy 0.03-0.06);2025-08 过放大 β2.2 可 rescale/cd 最强,2026-02 真死。精修裁决: 可交易且健康但温和,非薄且破。★CRUX 未决: 去杠杆 OOS 月 2026-05 LoRA vs Run1(d1_2026_05_run1 已提到 lora_05 之后,~3h)= 路由存在理由的唯一 OOS 检验。**  **方向预判(0B,手上证据): ~60-70% LoRA>Run1,幅度温和(+0.005~+0.02);但即便为正也是弱证据——路由尾部优势全压在这 1 个 22d 残折 OOS 月。** ★ **lora_2026_05 solo 落地(超预期强): cd 0.0586 vs 基线 0.0162 = +0.0424(基线 3.6 倍),β 0.90 健康,DENSE +0.043 正聚合 —— 所有 OOS 月里相对基线提升最大,且恰在路由指向 LoRA 的去杠杆月。★★ **CRUX 硬数定案(决定性负面): 2026-05 LoRA 0.0586 vs Run1 0.0540 = LoRA−Run1 仅 +0.0046(几乎打平)! Run1(无 state bugfix)在去杠杆月几乎和 LoRA 一样好(都基线 ~3.4 倍)。去杠杆优势没迁移到样本外(样本内 2026-04 +0.028 → 样本外 2026-05 +0.005,缩水)。⇒ 路由 vs always-Run1 OOS: 唯一差异在 2026-05(router 用 LoRA 0.0586 / always-Run1 用 Run1 0.0540),摊到 7 月 = +0.0007 均值,可忽略。** ★★★ **FINALE 定案: 因果路由样本外不挣饭钱(net-long 半≈生产 + 去杠杆开关 +0.0007) → 诚实单模型推荐 = always-Run1(bugfix)≈生产基线,真实但小的 edge 集中在单月 2025-08,0/6 net-long 达 0.08。唯一正交真赢 = 日内自评部署层。0.08-全 regime 盘上不可达。** ★★ **FINALE 核心结论(基本定稿,crux 仅补注脚): 冻结单模型稳定跨 regime 到 0.08 盘上不可达(穷尽架构/特征/目标/优化四路);最佳诚实方案 = 两专家模型 + 因果 positioning 开关 + 日内自评部署层;样本外拿到真实但小、大多不到 0.08 的信号(多数月 cd 0.02-0.06,仅个别强月近 0.08)。**08 对照 Run1 0.080>Run2 0.052 仍成立。 2025-08 对照: Run1 0.080 > Run2 0.052(state 在 net-long 月拖累,印证 tt-sign 路由方向)。11/12/26-02/03 待出定 6 月 OOS 主线强度。
- 2026-07-04 **canonical 10 月基线定格(0A 口径复现,验证 2025-10=0.0844≈0.0815 / 2026-04=0.0312≈0.0308)**: cd-CLEAN 逐月 = 08:0.0323 / 09:0.0434 / 10:0.0844 / 11:0.0671 / 12:0.0482 / 26-01:0.0304 / 02:0.0183 / 03:0.0139 / 04:0.0312 / 05:0.0162。**修正: 2026-01 canonical=0.0304(旧 runner 的 0.0123 是弱参考)** → 历史"Run2-01≈基线"是对弱参考,vs canonical 0.0304 Run2-01(0.012)其实低于基线(不改路由,2026-01 仍路由 Run1)。轨迹折与基线同口径(mask-fix+per-day-CLEAN),Δ 真实。**首折 d1_2025_08_run1 cd 0.0798 vs 基线 0.0323 = dCD +0.0475(bugfix 把普通月翻倍多)。**
- 2026-07-04 **lora_2026_01: LoRA 是更健康的 drift 侧模型**: cd +0.0211 vs Run2 +0.0121(+74%)、β 0.818 健康 vs Run2 0.37。**state-条件化 function-shift 在 drift 上比仿射 state 适应更好** → 路由的 drift 臂应是 LoRA(在 2 个净空月 2026-04/05 触发)。14 折 Run1+Run2 轨迹已自动开跑(d1_2025_08_run1);加跑 lora_2026_04/05 让 drift 臂用 LoRA。OOS headline = router{Run1 净多 / LoRA 净空} vs always-Run1 vs oracle。
- 2026-07-04 **预先 commit 10 月路由地图(防偷看)暴露关键弱点**: tt-sign 路由 = **8 Run1 / 2 Run2**,Run2 仅在去杠杆尾(2026-04/05)触发(positioning 2025-08..2026-03 全程净多)。**7 个未见月中 6 个路由 Run1、仅 2026-05(22d 残折)路由 Run2 → 净空→Run2 规则的 OOS 证据 = 1 个月,薄。** 路由退化为"几乎总 Run1 + 一个去杠杆开关",开关 OOS 证据近零。**提前锁定 FINALE 诚实结论上限: 最多验证 net-long→Run1(6 月 OOS 扎实)+ 证据单薄的去杠杆开关,不能声称稳健通用路由。** 这本身是诚实交付的一部分(跑前暴露,不事后自欺)。
- 2026-07-04 **因果路由离线门 PASS(但证据薄,标记 promising 非 proven)**: 因果 tt_level-sign(15d trailing,严格无 peek)在 3 月上: 2025-10 净多→Run1 ✓、2026-04 净空→Run2 ✓(两个决定性月正确)、2026-01 净多极值但 Run2 微好(miss,但 Δ 仅 0.0069,近 toss-up)。router mean deploy 0.0478 胜 always-Run1(0.0384,+24%)/always-Run2(0.0403,+19%),捕获 oracle 95%。**纪律: 3 月/2 决定点 = 薄,指标+阈值同期挑 = 过拟合风险 → 冻结 spec(tt-sign + trend-vs-chop 补 net-long 歧义,预注册 commit,禁调)→ 真判定 = 全 10 月轨迹上路由在未建它的 7 个月的 OOS 表现 vs always-Run1/Run2/oracle。** FINALE = 全 10 月 Run1+Run2 双轨迹(复用已跑折)+ 冻结路由 + 日内层 → 最终诚实表。lora_2026_01 定 drift 侧模型(Run2 vs LoRA 取健康者)。
- 2026-07-04 **★ LoRA 守卫 FAIL(raw cd 0.0574 « 0.075,β 1.116 完美健康)—— 单模型搜索闭合**: state-条件化换弹法也救不回强月峰值 alpha,且它是所有强月配置里校准最干净的(β 1.12)⇒ **不是校准问题,是 state 通路本身(仿射 or 低秩换弹都一样)在强月吃 alpha**。**结论定案: 没有任何冻结单模型能同 hold 强月+drift —— state 帮 drift 的代价就是强月峰值,这是数据里的真实 trade-off,不是没调好。** 诚实终局架构 = **因果 regime-路由(Run1-bugfix 强月 / state-Run2 drift,路由信号必须因果可预注册: 模型自身近期 IC 健康 or funding 态,非后验 regime 标签)+ 日内自评部署层**。lora_2026_01 跑完看 LoRA 在 drift 是否胜过 plain-state(定 drift 侧模型)→ 撤 lora_04/pcgrad → 进 FINALE(路由 spec + 全 10 月 + 2025-H1)。
- 2026-07-04 **combo 守卫 FAIL(deploy 0.0365 « 0.075)—— 特征级堆叠无法解跷跷板,但校准被修好了**: state+rank(raw 目标无 objective 冲突)deploy vs Run1 0.079 = −0.043,强月 alpha 仍远低于门。**关键 nuance: combo 是唯一健康的(β 0.831 带内、σ 0.023,vs state-alone β2.0 / Run1 β5.0 / align 全破)—— raw 目标设计确实修好了校准,但强月 alpha 还是不够。** 核心张力(state 帮难伤强 / Run1 赢强盲难)确认无法靠堆特征解 → **LoRA 是唯一机理候选(状态条件化换弹法: 强月近似恒等、难月真权重偏移,仿射杠杆做不到),提到队首,lora_2025_10 vs 0.075 守卫 = 成败在此**。combo_2026_01 跑完当盲区补丁数据点。
- 2026-07-04 **★ 前沿杠杆③ 命中: 日内自评(上午命中→下午命中)—— 免费、因果、正交、专攻盲区**: rank-corr POOLED +0.174(p=0.010,过门),**drift +0.228 / 强月 −0.10(指纹与其他杠杆相反)**;因果日内择时 drift 下午 per-day IC ~翻倍(+0.017→+0.037),去 top-3 天稳(+0.019);最死下午(2026-02/03)提升最大。诚实: 伤强月 → **条件部署(自门控)**。**关键定位: 这是部署/执行层杠杆(仓位择时),不是模型架构 —— 叠加在任何单模型之上、不与之竞争、无论 combo 判定如何都存活。** 用模型自身上午实际误差(H2 杀的是静态描述子,这是因果的不同信号)。**连续 trailing-window 形态证伪(真机理)**: 持续性是"同日 regime"效应(一天整体好/坏,上午下午共享),非滚动持续 → trailing 窗跨隔夜混不相关的天,洗没(每 regime 都伤)。所以操作形态 = **同日 split(下午按当日上午命中定仓位)**。**自门控(近 15d 均 IC<0.05 才开)保住强月(Δ0.000)+ 留 drift ~88% 增益**;残余 2026-05(该月上午预测不了下午)加 rho>0 门试补。intraday_scaler.py 定为部署层,叠加任意单模型。**日内自评层 DONE(a304f99)**: 双自门控(近15d 均IC<0.05 且 近30d 上午→下午 rho>0)。下午 per-day-CLEAN 逐月 deploy Δ: 2025-10/11 强月 +0.0000(0% 开,保护);2026-01 +0.0322 / 2026-03 +0.0370(救负下午)/ 2026-02 +0.0217 / 2026-04 +0.0061;残余 2025-12 −0.008、2026-05 −0.009(rho-门减半)。**drift 下午 ~2.1×(+0.0168→+0.0354),强月零损。诚实: 只作用下午半天(上午无条件,跨日方向已洗没)→ 全天 deploy 增益 ≈ 半数,drift 全天 ≈ +0.009 per-day-CLEAN、强月 ~0 —— 这 +0.009 加性叠加到单模型全轨迹之上、强月零成本。** compose-on-any-preds,单模型胜者落地即叠表。d1_2025_10_run2(state 强月): deploy per-day +0.0499 vs Run1 +0.0790(−0.029)= **state 本身也拖强月**。**核心张力定格: state 帮 drift/伤强月,Run1(纯 bugfix)赢强月/drift 盲 —— 当前杠杆下没有单一冻结模型处处最优。** ⇒ 诚实单模型要么是 regime-路由对(Run1-强月 + state-drift,但路由需因果可判、且 regime 后验不可切换 = 难),要么靠 **ARM L(state-LoRA 换弹法)让一个模型同时 hold 两端 —— L 因此是当前 pivotal 前沿臂**。combo_2025_10 守卫要在两组件(state 0.050 / rank 0.030)都低于 Run1 0.079 的情况下仍 hold ≥0.075,是硬门。
- 2026-07-04 **rank 独立双折 gate FAIL(mean +0.0015;fold-2 负)**: 2026-01 deploy Δ+0.0136(真值,补 state 盲区)/ 2026-04 Δ−0.0106(在 state 的月份反而伤)。独立杠杆判死;作为 combo 组件续命。**state+rank combo(两个尾部杠杆、不同机制、同 raw 目标无 objective 冲突)= 当前单模型头号候选**,combo_01/04 排队、combo_2025_10 守卫等 rank cache 回延 85 天(数据混淆防护)。run2-10(state 强月数)训练中。
- 2026-07-04 **rank_2026_01 判定: 真实但尾部集中,预注册 body 断言 FAIL**: raw RAW-B +0.0400 vs Run1 +0.0188(真 lift,β 1.72 带内、σ 0.0210 压线过);deploy +0.0188 vs +0.0052(+0.0136,但 deploy β 2.89 出带、deploy σ 0.015 低于门 = 部分慢频带)。**rest-80% body 没动(Δ≈0)—— 全部收益在尾部(top-20% cd 0.0946 vs Run1 0.0215)** ⇒ rank 不是 body/OOD 修复,而是又一个尾部杠杆(state=positioning-尾部、rank=输入归一-尾部)。**H1 的 80% body 至今没有任何杠杆能动 —— body 可能在 drift 月真的无信息,诚实上限或是尾部驱动的。** 2-fold gate 等 rank_2026_04。
- 2026-07-04 **aux_2026_01 机制点 PASS(且健康!)**: deploy +0.0306(≥0.025)、DENSE 同号 +0.0383、**β 0.838 带内** —— 0.3-aux 在非方向月干净地交付 align 收益的 ~63%(vs 纯 align 的 β 0.132 破损)。**定格: AUX 与它携带的杠杆同样 regime-分裂 —— 非方向月健康交付,方向月被共享 backbone 污染。** aux-0.1 变体 HOLD(rank 是同一盲区的更干净候选,input-side 无 trunk 冲突;rank 败才启用 aux-0.1)。rank_2026_01 训练中(RevIN-bypass 实跑验证激活,n=34)。
- 2026-07-04 **AUX 守卫 SEALED(deploy 0.0300 « 0.075,比 naive stack 还差)—— "raw 主头保 level"假设在 trunk 层被推翻**: 0.3 demeaned aux 的梯度穿过**共享 backbone**污染主头的强月信号 —— 干扰是共享表征问题,不是目标混合问题 ⇒ 降权重(0.1)大概率也救不了(机制随权重缩放但不消失)。aux_2026_01 机制点仍跑(≥0.025 deploy 才给 0.1 变体一次机会,否则 AUX 家族归档)。rank 臂 pre-flight 验证完毕(mask/cache/substrate 全就绪)排在其后。
- 2026-07-04 **AUX 守卫折 FAIL(预注册强月回退条件触发)**: aux_2025_10 raw cd +0.0751(vs 基线 0.0815 回退 −0.006、vs Run1 0.1025 −0.027)、DENSE −0.042、β 0.216 —— **0.3 权重的 demeaned 辅助头仍拖强月(干扰减轻但未消除,共享 backbone 被 aux 梯度拉向 demean 解)**。裁决: aux_2026_04/12 撤下;aux_2026_01 跑完(机制数据点: aux 在目标月是否 work,决定 0.1-权重变体有无一试价值);**rank-norm×2(建好未跑的 body 杠杆)+ d1_2025_10_run2(state-only 的强月数)上位**。单模型候选现状: state-only Run2 领跑 + 非方向月盲区待 rank/S4/SWA 补。
- 2026-07-04 **choppy 地图点(stack_2025_12)补全干扰机制**: stack deploy +0.0377 ≈ align 单独 +0.0354(**保留,无干扰**)vs 强月的 −0.041(摧毁)。**定律定格: 干扰 ⟺ trailing-mean 方向性**(方向月两杠杆争夺 level → 塌;非方向月无 level 可争 → 共存)。choppy 的 deploy 口径对所有模型退化(per-day+/DENSE−)照旧。**对 AUX 的含义: 非方向月两杠杆本就共存(AUX 应保持),方向月正是 raw 主目标要修的 —— 机理上 AUX 两头都该赢,守卫折(训练中,多 horizon 配置实跑确认)给最终答案。**
- 2026-07-04 **归因定格(run1-04)**: Run2-04 的 +0.0407 = bugfix +0.0109(27%)+ **state +0.0298(73%,主导)**,与 permute-null 闭环;Run1-04 β 0.178 仍坏 = gain 才是 β 修复者。**clean align gate on 2026-04(vs 自己的 bugfix 基线): Δ+0.0019 ≈ NULL** —— align 收益完全集中在非方向月(2026-01 +0.0437 / 2025-12 +0.0304),刷新后三折均值 +0.0253 仍过 gate。战略图: **STATE = 主导、健康、跨 regime 杠杆;ALIGN = 纯非方向-drift 特效药,naive 合体破坏性干扰。** state-only 的已知盲区: Run2-2026-01 ≈ 基线 → **AUX 是唯一可能同时覆盖两类月份的单模型候选(pivotal 实验)**。
- 2026-07-04 **★ naive STACK 被强月守卫决定性否决**: stack_2025_10 deploy 仅 +0.0378 / β 0.044(灾难)vs Run1-10 deploy +0.0790 —— 输给两个非-align 基线的所有 deploy 指标。**机理泛化: align 的 demean 会剥掉一切"trailing-mean 方向性"月份的 level alpha(强月+去杠杆月都中枪),只在非方向 drift/choppy 是纯增益。** 守卫先行设计立功(1 折杀掉省 3 折)。裁决: stack_2026_01/04 撤下、stack_2025_12 跑完(便宜地图点);**ALIGN-as-AUX×4 上位**(raw 主目标保 level + 0.3 demeaned 辅助头),守卫先行,pass 线预注册(10 月 deploy≥0.075 / 01 ≥0.025 / 04 ≥0.035 / 12 ≥基线+0.004);AUX 若也伤强月 → 单模型候选回落 state-only Run2。
- 2026-07-03 **ALIGN 三折判定: gate PASS(mean Δcd_deploy +0.0180,且被低估 —— 04 折对照用的是强 state 臂)但健康全破**: 2026-01 +0.0437 / 2026-04 −0.0201(vs state)/ 2025-12 **+0.0304(choppy,deploy +0.0354 vs 基线 +0.0051)**;β 三折全出带(0.13/0.01/−0.06)= 真方向 alpha 但系统性失准,as-is 不可部署(AUX 变体结构性修复)。2025-12 的 per-day+/DENSE− 分歧是 choppy regime 对 deploy 口径的共性(基线更差),非 align 特异。**regime 图案定格: align 与 state 互补(各覆盖对方盲区)—— 合体的理由成立,naive stack 的风险在 04 折的 level 争夺。stacks 留队,ALIGN-as-AUX 预案待 stack_2026_04 信号。**
- 2026-07-03 **ALIGN 第二折(2026-04)= 杠杆 regime-分裂**: ALIGN-04 deploy +0.0217 但 **β 0.012 灾难性塌陷**,输给 state 杠杆(Run2-04 deploy +0.0417, β 0.841)。机理: 去杠杆月的 trailing-mean 本身强方向性,state 杠杆变现的可能正是该持续分量 → align 目标恰好把它从目标里剥掉(干扰机制,非噪声)。**图案: align 帮 state 盲的月(2026-01),state 帮 align 弱的月(2026-04)** —— 正交但可能干扰。STACK×4 已建好排队(可零成本撤下);预案 fallback = ALIGN-as-AUX(raw 主目标 + demeaned 辅助头 0.3)。align_2025_12(choppy)跑着补第三折。
- 2026-07-03 **★ state-permute null PASS(审计 4/4 全过)—— Run2-04 定案**: 18 维 state 按天打乱(3 seeds)cd 0.0715→0.0495(**−31%,真因果条件化签名**;非"不变=无关"也非"上升=泄漏")。分解: +0.0407 = **~+0.022 positioning state** + ~+0.019 非-state(permuted 仍 > 基线;run1-04 归因跑定格)。**positioning conditioning WIN 经全套逻辑审计存活。**
- 2026-07-03 **★★ ALIGN 首折(2026-01,deploy-dead 月)artifact-free 判定 = 巨大且真实(provisional)**: val 0.28 确为机械膨胀(如预测),但 **RAW-B corr(σ·q50, raw y) = +0.0686 vs Run1 +0.0188(Δ+0.0498)**;σ(输出)/σ_m=0.40(非 −m 复读机);选择腐蚀未咬(选中 epoch 本身 RAW-B 高)。**若成立 = 训练-部署对齐把"死月"从 ~0 抬到 ~0.07 —— 慢频带病灶叙事的直接兑现。** Caveat: 单折;等 align_2026_04/2025_12 + headline_audit 全套。**deploy 口径补齐(01d8514): ALIGN 2026-01 deploy = +0.0489 vs Run1 deploy +0.0052(Δ+0.0437)** —— RAW-B 0.0686 里 ~0.02 慢频带被 demean 剥掉后的干净短期 alpha;机理自洽(目标与部署口径对齐后模型全部容量投向 10-min 频带)。deploy-dead 月 2026-01 的 deploy 口径: 基线 −0.001 → Run1 +0.005 → **ALIGN +0.049**。健康细化(24cf23f): deploy β 两模型都低(ALIGN 0.132 vs Run1 0.050,均出带)= **drift 月共有病理(H1 β-衰减)非 align 特异**;相对面 ALIGN 全优(deploy corr 9×、β 2.6×、demeaned 信号弥散 7×、per-day 一致性 2×);绝对 β 低可后验缩放。runner 修复: 自动过期 PAUSE(30min)堵 GPU 空转漏洞(此前空转 2h 的根因)。
- 2026-07-03 **机制分解数据点(0C 分层)**: Run2-04 的 positioning WIN 是**尾部集中的**(tail-20% IC +0.1073 vs 基线 +0.0221;rest-80% 不变 −0.0005)—— positioning 锐化置信尾部,**不修 body**;rank-norm 臂恰好打 body(基线 drift rest-80% 参考 pooled ≈+0.0072)。两机制正交可分 → 若都成立应可加性叠加。rank 臂建设推进(overlay 617 天建中、configs 落地 4fa0af0、RevIN-mask spec 已交 0B、rest-80% 评估入 headline_audit 9228729)。
- 2026-07-03 **★ 架构级洞察(0C 预建验证抓获): RevIN 结构性抹掉所有 X 通道的窗口级 level**(实测 corr(RevIN(raw),RevIN(rank)) 0.85-0.98)—— rank-as-X 按原规格是 null-by-construction;**回溯解释 #29 加通道惩罚的一部分(历史上加的 regime-level 内容全被 RevIN 洗掉)+ 为何 positioning 只能走 prior/FiLM 路径**。裁决: rank 臂改为 (A) RevIN-bypass 方案(34 个 rank 通道跳过 RevIN,mask 实现在 multi_asset 子类,src/ 只读;bit-identity 空 mask 测试 + batch-invariance 必过;省下一个必然空转的 GPU slot)。
- 2026-07-03 **headline_audit.py 固化(25cc2ab)+ 2025-10 守卫 β-rescale 修复验证**: 因果 trail-30d β-rescale 后 **cd +0.1019(仅 −0.0006,Pearson-不变)、β 0.632 带内、σ 0.089 健康 → 2025-10 headline-eligible**。条件修复规则编入 harness: raw 健康 → 原样;raw health-fail 但 deploy-survive → β-rescale(对已健康 run 会过矫,勿滥用)。与被杀的 0c pooled-IC-lever 的区别已在模块内文档化(此处 claim 零 IC 增益,纯健康修复)。
- 2026-07-03 **特征漂移审计(3.6-④,Phase-1 gap#7)完成**: drift 月 **~40% 通道分布 OOD**(13 个 PSI>0.25 major + 22 moderate);cross-venue basis 族慢性最重(PSI ~1-6),drift-特异签名 = spot_21/22/11/23/10/12-16;**clip 饱和 <0.2% = 伤害是形状漂移非截断** → rank 变换对症;x_mid_ratio_log 与 x_basis_bps 冗余(#29,砍一个);pt_* 族最平稳。机理链: OOD 联合流形 → 学到的映射失灵 → H1 的 80% 噪声体。**rank-norm 臂已批准建设**(35 个 PSI>0.1 通道因果 trailing-3d rolling-rank → overlay cache;Run1 底座、预注册可测断言: drift rest-IC 离开 +0.0002)。
- 2026-07-03 **q-spread 置信加权(3.6-②)= 判死(诚实负 + 机理)**: GLS 加权 pooled cd 0.0394→0.0299、drift 更差;置信门控方向反了(低-spread"高置信"IC +0.004,高-spread IC +0.060/drift +0.037)。**机理: DAQH spread 是 realized-vol/幅度 proxy(corr(spread,|y|) 0.32-0.59),非认知不确定度** —— 高 spread ≈ H1 尾部 = 信号所在,1/spread 恰好剥掉信号。复现并解释了 milestone 时代"quantile 不可作 filter"。唯一支持的方向(上权高 spread)= 已知的 |pred|-尾部 sizing,无新 edge。
- 2026-07-03 **审计定案(除 state-permute null 外全部完成,双 agent 交叉)**: ① 独立第二代码路径复算逐位一致(测量无 bug);② node-set 恒等(13,272 有效行完全同集)+ fold 边界与生产恒等;③ EMA no-peek 链干净。**修正我的预标: 2025-10 Run1 不是 artifact** —— 1h demean 保留 90%(优于基线 84%),12h/24h 也稳,deploy Δ+0.0238;之前的"DENSE↓"是 vs 基线的 Δ 非绝对反号(绝对 DENSE +0.0617 与 cd 同号)。**真实判定: real alpha + broken calibration(β 3.134 出带、σ 0.01969 压线)→ HEALTH-FAIL 标签,β-rescale(Pearson-不变)修复后可 headline。** 2026-04 Run2 由 0C 独立复验(demean 数学手工核对因果到 0 误差): clean WIN 定案。deploy 口径月度图: 2025-10 base 0.0681→Run1 0.0919;2026-04 base 0.0181→Run2 0.0460;2026-01 base −0.0013→Run1 +0.0087。audit harness 固化为可复用模块(每个 headline run 必过)。
- 2026-07-03 **用户令: 大幅提升全面审计**(结论可靠性 > 数字): ① 2025-10 Run1 部署契约诊断(慢频带嫌疑);② 3 个 headline run 的独立第二代码路径复算 + node-set 恒等 + fold 边界恒等;③ **state-permute null**(Run2-04 的 state 输入按天打乱推理 —— 若 cd 不降 = 归因存疑,若升 = 泄漏嫌疑);④ EMA no-peek 链核查;⑤ run1-04 归因 + seed7 复跑(已排队)。
- 2026-07-03 **★★ Run2-04 部署契约确认 = 真 10-min alpha**: deploy 口径(1h 因果 demean)**arm 0.0460 vs 基线 0.0181 → deploy Δcd +0.0279**;保留率 64% **优于**基线 59%;12h/24h demean 下仍存活(非慢频带);82% 天数正、去 top-5 仍 +0.0453(不靠 outlier)。与 spec artifact 精确反向。**结论: 修复后的 positioning-state conditioning 在最死的 drift 月给出真实可交易 +0.028 deploy-cd —— 本轮的 breakthrough,"regime 不可学"正式被推翻。** 剩余确认: run1-04 归因(bugfix vs state 分解)、seed7、2025-10 守卫(跑)。
- 2026-07-03 **tail 加权臂(ARM B)双折 KILLED**: tail_2026_01 cd −0.0008(Δ−0.0131)β −0.60;tail_2026_04 cd −0.0049(Δ−0.0357)。均值 Δ−0.024 << +0.004 → **尾部上加权(k=2.0)作为训练杠杆判死**(H1 的尾部集中是"信号住在哪"的事实,不等于"加权尾部能学得更好")。
- 2026-07-03 **spec_2025_12(定案折)= artifact 签名再现**: cd +0.0647 但 DENSE 0.0027(反向 vs 基线 0.0188)、β 0.042 出带 → 毕业规则(DENSE 同号 + β 带内)**不过**;待部署契约诊断正式确认。specialist 三折战绩 = 1 deploy-WIN(2026-04)/ 2 artifact → **不毕业**,记为"2026-04 特例"。seed7 复跑 OOM(误建为 b1024,重建 b512 重排)。
- 2026-07-03 **spec_2026_04 = 部署契约下真 WIN**: raw cd +0.0543(Δ+0.0235)、DENSE 同号 +、β 0.190→0.518 带内;**1h-demean 保留率 58% = 基线 59% 平价(真 10-min alpha),deploy 口径 Δ+0.0135**;按天 71% 正、无灾难日。**与首折 reconcile**: 2026-01 是"deploy-dead"月(生产基线 demean 后保留 −10% —— 谁都没有可交易 alpha),spec 在那里 deploy-中性而非有害。两折 deploy 均值 Δ+0.0096、逐折同号 → **过 +0.004 gate,但增量集中在 fold-2**。第三折 spec_2025_12(健康基线月,无歧义读数)已批准排队,毕业规则预注册: deploy Δcd≥+0.004 + DENSE 同号 + β 带内 → 进 base config。**新口径事实: raw-cd 与 deploy(1h-demean)口径逐月差异大,headline 需双报。**
- 2026-07-02 **Stage-2 选择器扫首折(2026-01 Run1)—— S4 捕获 97% oracle gap(零 GPU)**: oracle gap +0.0151(选择在此折是 binding);**S4(raw∪ema 联合 one-SE-earliest)选 ema ep6 → test cd +0.0322 vs shipped(always-EMA ep8)+0.0175 = Δ+0.0147**,且健康(DENSE +0.0226)。机理与 D5a 论题一致: drift 折爬向晚期过度自信 epoch(ep6→ep8 β 1.26→0.57、σ 升)。S1 伤、S2 不健康、S3≈shipped。**叠加栈(最差 drift 月 2026-01): 基线 0.0123 → bugfix 0.0175 → +S4 0.0322(~2.6×)。** Caveat: 单折;需 2026-04 + held-out ≥3/5 确认(预注册规则)。val_hist 修复(改增量式 per-epoch json)。臂接线完成并数据验证(153/450 kept, tailfrac 0.199),b1024 过门后放行。

- 2026-07-02: Stage-0 三线并行开建(A: 0a+0b+0c 卫生+仪表化+再校准;B: 0d+0f D1 substrate+state_prior;C: 0e D3 因子+Ridge 门)。
- 2026-07-02 **Stage-0A 完成**(commit 03ce098): ① mask 泄漏实为 **808 行 padded**(非 82;"y_true==0 过滤"本会反向误伤)→ 正确修复;**POST-FIX 基线 = pooled DENSE 0.0320 / cd-CLEAN 0.0380**,统一健康门下仅 5/10 月健康 —— 此表为全部后续对比的唯一分母。② trainer 仪表化落地(per-epoch val 史/σ-fallback/选择溯源/窗口截断 assert);D5a 审计确认:drift 折 best_epoch 晚(7-18)、val σ 尖峰(0.141/0.144 在 2026-02/04)与 H1 过度自信吻合、**oracle regret drift +0.0038/月(selector floor 真实,Stage-2 目标)**;2025-11 metrics 不可恢复(仅 preds 存活)。③ **0c 因果再校准 KILLED(4/4 门全灭)**: pooled lift +0.0002(需+0.004)、bootstrap P=0.49、trailing β̂ 在 drift 太噪(clip 到 0.2、翻负、4 月 σ<0.02)—— H1 的"重加权天花板"以低于悲观估计的方式坐实。④ **c3 funding 短门 KILLED**: 字面 PASS 是 artifact —— 2026 funding 均匀偏低,87% 短单落底部 tercile,门的边际贡献 −0.085bps(t=−2.76)反而伤害;expanding-tercile 规格缺陷,trailing 窗需另立预注册。**副产品(真)**: 2026 短册 pre-cost +0.44bps/笔,day-t=+3.48。
- 2026-07-02 **Stage-0B 完成**(commit e49c8cc): D1 substrate 全建成 + 4 项测试全过 —— **batch-invariance bug 在正品模型里实锤复现(旧 Δ=3.5e-4 → 修后 6e-8)**;state_prior overlay 872 天全建(coverage 1.000)。**Pre-gate 关键 nuance**: 6 个 vol 描述子不分离 regime(channel-0 退化 + "choppy≠高 vol"再证)——**但 state overlay 在 POSITIONING 轴分离(top-trader L/S spread 2.3×: 2025-10 净多 +0.41 vs 2026-04 净空 −0.12 = 去杠杆 regime)**,fund_last/fund_mean5d/pidx_mean_24h 也过。→ Run2 的预期增益来自 positioning state,非 vol 描述子;Run1 价值 = 正确性修复 + 健康。Stage-1 按计划跑。
- 2026-07-02 **Stage-0C(A/C/D 族)Ridge 门 KILLED**: A cascade drift Δ+0.0021(<+0.005,与 shuffle 噪声不可分,伤强月 −0.024);C flow Δ−0.0096;D settlement Δ−0.0037。零 GPU 排掉三条路。A 族复现显著短尾结构(cascade-net tercile −2.83bps, t=−2.80,与 H5 short×funding 同源)→ 归执行层。**B 族(basket-ECM/跨资产)gate 进行中。**
- 2026-07-02 **Stage-1 run-1 落地(2026-01 Run1 = 纯 bugfix,EMA no-peek,双 scorer 一致确认)**: cd-CLEAN **+0.0175 vs 基线 +0.0123(Δ+0.0052)**;DENSE **+0.0440 vs +0.0150(Δ+0.029,3×)**;两口径同升(非 day-demean artifact)。选择健康化:best_epoch=8(旧 drift 形态 15-18),无 σ-fallback。**健康旗:β 0.457→1.951 矫枉过正**(超带上界;σ 0.023 边缘)—— output-gain 修正器只在 Run2,故 Run2 的 β 是真检验。解读:纯机制修复(pre-RevIN + frozen-stat 归一 + batch-invariance)在最死 drift 月已有真实但克制的 cd 提升,与 pre-gate 预判一致(基础 6 维 prior 分离力有限 → 诚实小幅);**positioning state 的增量看 Run2**。Caveat: 单折单 seed;Run2 gate(+0.003 双 drift 折均值)才是判据。
- 2026-07-02 **Stage-1 GPU 开跑**: server 侧链式 runner(PID 1448390)自动序贯 6 run + verify-before-advance;status: `experiments/d1gate/chain_status.log`。**apples-to-apples 已核**: 三个 gate 月生产基线全为 npz_v2arch,d1gate 配置匹配 ✓(生产轨迹 cache 异构仅在 2025-08/09 = npzv4_dual 遗留,文档在案)。
- 2026-07-02 **0A 两项发现**(2023 cache 回建中): ① **committed build_v2arch_npz.py 与生产 cache 有漂移** —— efe0baf 给 x_rvol_ratio_log(ch86)加了 clip±4,生产 cache(早一天建)未 clip;已用验证过 bit-identical 的未 clip 版建 2023(保持与冻结 cache + 0.0380 基线一致);committed 版留档待议。② **wf_2025_01..07 旧配置口径错误**(npzv4_dual/700d)→ 已新建 `configs/wf450_backext/wf_2025_01..07.json`(npz_v2arch/450d/λq0.1,精确生产口径,commit 落地)。
- 2026-07-02 **2023 cache 回建完成(0A)**: 2023-08-19..12-31 = 135 天全链(mid→clean→v2arch→state overlay,~38GB,~16min 全速);npz_v2arch 现跨 **2023-08-19→2026-05-31(1007 天)**;7 个 wf450_backext 配置经真 _build_folds 验证**全部足额 450d**(2024 的 10 个缺口天压缩 lookback → 起点前移 13 天补齐,assert 抓住了 441d 截断)。**Stage-4(2025-H1 回补)数据+配置就绪。** ⚠ 磁盘 5.09GB free(98.8% 满)—— 再大建必须先 prune。
- 2026-07-02 **新发现: 生产 cache 自身 channel-86 不一致** —— x_rvol_ratio_log 在 2024-04-23→2025-05-07(373 天)是 clipped(±4),其余 621 天 unclipped(efe0baf 代码重建过中段)。生产基线的训练窗本就横跨混合数据;A/B 对比不受影响(各臂共享同一 cache),但 cache 理想应同质化(重建 373 天 ~59GB + 重定基线)—— **defer 到 Stage-1/2 之后再议**。2023 新建段用 unclipped 与多数段一致。
- 2026-07-02 **Stage-0C 完成**(commit 8fd1aa2): **D3 全部 4 族 Ridge 门 KILLED**(B basket-ECM Δ−0.0022、D −0.0037 补齐;所有真 Δ 低于各自 shuffle-null 地板 0.0026-0.0038)。**科学发现(transfer 诊断)**: casc_net_1h + ecm_resid_z 与 y_pred 近正交、standalone drift IC 符号一致(~−0.03/−0.04)—— **正交反转内容存在,但固定线性映射不可迁移**(oracle in-sample Δ=+0.0112 vs expanding-prior Δ=+0.0005;feature→y 映射随 regime 变 = H4 概念跳变在映射层的显形)。即便 oracle 天花板也只把 drift 0.024→0.035,远非 0.08。短×cascade 条件结构(−2.83bps, t=−2.80)→ 执行/短倾斜层。**结论: 盘上新信息路线关闭;2026-04/05 要动只剩外部 liquidations feed。** 拼接校验过(klines vs bar_data corr≥0.99)。contingent 备忘: 若 Stage-1 Run2 过门,casc_net/ecm_z 可作为 +2 state 特征的 Run2c 追加臂(条件化机制≠线性加法,需另行预注册)。
