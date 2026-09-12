> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结 —— 本文在计算任何收益之前写定, 装置启动先断言本文 sha256 | **作废条件:** 出现比 v4 更新且逐门验过的链; 或 GATE P 不过(则下游全部作废)

# PREREG r13-B · T1 FORM B —— 半区内沿 beta 轴再加权(within-half beta-gap overlay)

## §0 一句话
第十二轮测出书带着一条**没人管过、会翻号的市场方向敞口**, 并证明广义涨势里 **97% 的亏损是两个半区之间的 beta 差**, 不是美元净敞口。
本文预注册一个**只在半区内部搬权重、逐半区美元和严格不变**的覆盖层, 目的只有一个: **把 beta_L − beta_S 推向零**, 然后看书的净额怎么动。

## §1 仪器(先于数字, 全部要在收据里重算 sha)

| 项 | 值 |
|---|---|
| 书(主) | `r3k/arms/A0_PWR230k_s42.npz` sha256 `352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339` |
| 书(复验种子) | `r3k/arms/A0_PWR230k_s2027.npz` sha16 `aa44e18fb6bcfa7e`(同形态, FSEED=2027) |
| 产它的装置 | `trackA/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` = CALIBER PIN v4 指定 |
| 形态 | `PHI=0.45 LEGS=101 WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 W3FIX=None CAL=log FTRIM=zero` |
| 记账元 | `meta_newprod_v4.npz` (realpath of `pod_backup_2026-08-21/wide_fea_hist_meta.npz`) sha16 `0e3c09ac86c727ac` |
| 面板 | `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz`(`f_fund_now` / `f_fund_iv`) |
| 宇宙掩码 | `health_check/masks/umask_UPIT_CRYPTO.npz` sha16 `47d87b5165b695a7` |
| 成本 | 逐字读自工件自己的 `config_json["COST_B"]`(= `costb_PWR_G230k.json`, K=0.17 FITTED / α=0.87 那一档), **不从环境读** |
| r12 因果原语 | `r12_regime/causal_primitives_r12_v2.npz` sha16 `0510f456f63f4963`(A_ew 逐位对账基准 + 34 格 regime) |
| r12 分区预注册 | `r12_regime/PREREG_r12_regime_partition_2026-09-12.md` sha256 `e239f8df…99ce3c` —— **逐格复用, 不新定义** |
| XIB 对照 | `seatladder/dev/probe_artifacts/w10_ablation_series_LAD_XIB_dyn_s42.npz` |
| y4 口径 | pod 5m 谱系 = **Σ 5 分钟简单收益**, **禁 expm1**(E-0904-F); 且 `CAL=log` ⇒ 记账链上不施 expm1 |

## §2 两个窗(不可混用, 沿用 r12/E-0911)
- `W_ALPHA` = 丢前 900 ∩ `ts ≤ 2026-08-30 20Z` ⇒ **n=9138**。所有 mean/CI/Sharpe/换手/腿/beta 数。
- `W_TAIL` = `ts ≤ 2026-08-30 20Z`, 不丢暖机 ⇒ **n=10038**。所有 maxDD/最差日/停机数。
- 装置内硬断言这两个数; 且断言 `mean g(W_ALPHA)=+0.6341957`, `Sharpe=1.2912234`, `turnover_raw=0.03032`, `turnover/gt=0.0540270`。

## §3 覆盖层的精确因果规则(FORM B)

### 3.1 作用位置(决定可部署性)
在役链: 生产者 `~/wide_shadow/fea171/combo_stage.py::chain()` L84-93 做 EMA(α=0.10)+ 不交易带(2.5e-4) → 写 `combo_raw`(**未 reshape**)→ 执行器 `~/dl_quant_live/signal/legs.py::reshape_after_withhold` 做 **全局 redemean + L1 复原**。
**主形态(PRIMARY)**: 覆盖层作用在**已 reshape 的书** `smr` 上。因为覆盖层**逐半区保美元和**, 所以 `sum(w)=0` 与 `L1(w)=gross_total` 都被逐位保住 ⇒ **执行器的 reshape 对覆盖层输出是恒等映射**。落地方式 = 生产者先调它自己已有的 `exec_reshape()`(L199-206, 现在只喂归档), 再调覆盖层, 再写盘。
**稳健形态(变体 R, 非录取候选)**: 覆盖层作用在 `sm`(未 reshape)上, 之后照样过执行器 reshape。用来证明结论不挂在 reshape 落在哪一侧。

### 3.2 基准与 beta 估计(逐字沿用上一阶段已判 GO 的估计器)
- 基准 `A_t` = 当锚成员集(MEMBERS_TOPN=829 按 qvk 重建, 再 UMASK m1 CRYPTO)上有限 `y4` 的**等权均值**。装置必须**重新导出**并与 `causal_primitives_r12_v2.npz` 的 `A_ew` 列断言 **maxabs = 0.0**。
- `beta_i(t;W) = cov(y_i, A)/var(A)`, 只用 **k ≤ i−1** 的 **W** 个锚(严格因果), pairwise-complete, 要求该名在窗内有限观测 ≥ 0.8·(A 有限的行数), 否则 beta = NaN(该名不参与倾斜, 乘子恒为 1)。
- 装置必须把滚动前缀和实现与逐锚直算在 ≥20 个随机锚上对账, maxabs < 1e-9。
- **收缩**: Vasicek `b~ = b̄_cs + ρ·(b − b̄_cs)`, 预注册 `ρ = 0.86`(= 上一阶段 W=250 的 split-half 可靠度)。
  **本文先声明一条代数事实, 并要求装置数值验证**: 在 §3.3 的"解 θ"参数化下, 任何一致的线性收缩对最终权重是**恒等的**(ρ 同时缩放 B̂、s、V, 三者在 θ* 里约掉)。装置必须跑 ρ=1.00 与 ρ=0.86 两次并断言权重 **maxabs = 0.0**。**所以收缩不是一个自由度, 不计入 K。**

### 3.3 覆盖层本体(一次求解, 无迭代)
设该锚成员集 `m`, 部署权重 `v = smr`(全 829 维), `gt = Σ|sm|`, 归一 `u = v/gt`(`L1(u)=1`, `Σu=0`)。
只在 `m` 内、且 beta 有限的名上动; `m` 外与 beta=NaN 的名**权重原封不动**。
- 多半区 `L = {i∈m_fin : u_i > 0}`, 空半区 `S = {i∈m_fin : u_i < 0}`。
- `s = popsd(b~)` over `m_fin`(截面尺度, 使 θ 无量纲)。
- `b̄_L = Σ_L u_i b~_i / Σ_L u_i`, `b̄_S = Σ_S u_i b~_i / Σ_S u_i`(美元加权半区 beta)。
- `B̂ = Σ_{m_fin} u_i b~_i` = **事前书 beta**(每单位 gross)。
- `V_L = Σ_L u_i (b~_i − b̄_L)²`, `V_S = Σ_S |u_i| (b~_i − b̄_S)²`。
- **解**: `θ* = KAPPA · B̂ · s / (V_L + V_S)`, 再 `θ = clip(θ*, −THETA_MAX, +THETA_MAX)`, `THETA_MAX = 1.0`(冻结)。
- **乘子**: `i∈L: mult_i = 1 − θ·(b~_i − b̄_L)/s`;`i∈S: mult_i = 1 + θ·(b~_i − b̄_S)/s`。
- **保号夹**: `mult = clip(mult, 0.25, 1.75)`(冻结)。
- **逐半区美元和精确复原**: `u'_H ← u'_H · (Σ_H u_i) / (Σ_H u'_i)`, 逐半区各做一次。
- 恒等式: 在无夹取时 `B̂' = (1−KAPPA)·B̂` 精确成立(装置断言无夹取锚上 maxabs < 1e-12)。
- **装置断言(每锚)**: `|Σ u' − Σ u| < 1e-12`、`|L1(u') − 1| < 1e-12`、`sign(u'_i) = sign(u_i)` 全体。

### 3.4 KAPPA = 0 ⇒ θ = 0 ⇒ mult ≡ 1 ⇒ `u' = u` **逐位相等**。这是 GATE P。

## §4 臂表与 K(冻结)
**K = 12** = `KAPPA ∈ {0.25, 0.50, 0.75, 1.00}` × `WBETA ∈ {60, 120, 250}`。
**PRIMARY ARM(看任何收益之前指定)**: `KAPPA=1.00, WBETA=250`。理由**只**引用上一阶段的可靠度证据(W=250: ρ_SB 0.856 / ρ_OOS 0.683 / 生存 0.763, 三项全为该窗最高), 与任何收益无关。
**主统计量**: `dg = mean(g_overlay) − mean(g_rebuild)`, `g = net_ex/gross_total`, bps/锚/单位 gross, 窗 `W_ALPHA`, 种子 s42。
非录取候选的稳健形态(不计入 K, 只报): 变体 R(§3.1)、变体 BAND(覆盖层输出再过 2.5e-4 不交易带后复原半区和)、ρ=1.00 不变性检验、第二种子 s2027。

## §5 判读标准(冻结)
- **GATE P(逐位)**: KAPPA=0 时 `maxabs|u' − u| = 0.0`, 两个种子都要过。
  同时报"我方重记账 vs 工件归档列"的 parity —— 工件的 `W` 以 **float32** 存, 逐位复现 float64 的 `rec` **不可能**;
  因此 **dg 一律是"覆盖层 vs 我方 KAPPA=0 重建"的配对差**(浮点误差精确抵消), 而 parity 数只用来证明重建装置是同一本书(门: pnl_ex maxabs < 1e-3 bps, carry_ex < 1e-4 bps, cost_ex < 1e-4 bps, 与 r12 同门)。
  **GATE P 不过 ⇒ 全部下游作废, 直接报 NOT_DEPLOYABLE。**
- **GATE M(机制, 先于收益)**: 池化 `|b̄_L − b̄_S|` 相对降幅 **≥ 50%**, **且** g-on-A 回归斜率在 2023(正)与 2026(负)两个子样本上**都向零移动**。
  不满足 ⇒ 覆盖层没做它声称的事 ⇒ **REJECT**, 不看收益。
- **ADMIT** 需同时满足: (i) `dg > 0` 且 **Bonferroni-12** CI95 下界 > 0; (ii) 3.2167× 成本重定价后 `dg` **符号不变**; (iii) `W_TAIL` 最差日不比在役深 0.25pp 以上, 且停机(≤−4.00%)次数不增加; (iv) 6/6 换手匹配+开火计数匹配零假设全胜。
- 点估计 > 0 但 CI 含零 ⇒ **UNDECIDED**。点估计 ≤ 0 或 (ii)(iii) 破 ⇒ **REJECT**。
- **±0.23 bps/锚以下的提升不是结果**(CALIBER_PIN v4 §4 自举分辨率)。

## §6 统计
- CI95: **UTC 日块自举 2000 次**, `numpy.default_rng([20260905, k])`, 抽日有放回, 估计量 `Σ tot[r] / Σ cnt[r]`(与 r12 `boot_ci` 逐字同式)。dg 用**配对差** `d_t = g'_t − g_t` 的同一自举。
- `Sharpe_ann = mean/sd(ddof=1)·sqrt(2190)`, `SE = sqrt(2190/n)`。
- 日收益(2.0×): `Π(1 + 2.0·g·1e-4) − 1`。HALT ≤ −4.00%, ALERT ≤ −2.68%。
- **换手匹配口径**: `turnover_ex/gross_total`。RAW 与匹配之比 1.4375 必须同时印出。边际换手 = `mean(turn'_matched) − mean(turn_matched)`。
- 成本存活 = `dg / (dpnl − dcarry)`; 3.2167× 重定价 = 两臂的 `cost_ex` 同乘 3.2167 后重算 dg。

## §7 零假设(换手匹配 + 开火计数匹配)
覆盖层不是一个分数矩阵, 所以零假设打的是 **beta 轴本身**:
- `NULL_RELAB_k`(k=1,2,3): 固定符号置换 `π_k` 作用于 beta 向量(每锚同一 π), 截面分布逐锚完全保留。
- `NULL_SHIFT_k`(k=101,503,1009): beta 矩阵整体时间前移 k 个锚, 时间对齐被破坏, 其余不变。
每个零假设的 `KAPPA` 用二分法**重标定**, 使其**匹配换手**(边际匹配换手相对差 ≤ 1%);同时报**开火计数**匹配
(`FIRE_i = 1{max_i|Δu| > 1e-5}` 的锚数, 以及 `|θ|` 的均值/中位数)。判读: 真臂 dg 必须严格大于 6 个零假设的**最大**值。

## §8 是不是"又一次 alpha 再加权"(直接回答用户的怀疑)
报三个相关系数, 窗 `W_ALPHA`:
`ρ(d, g_A0)`、`ρ(g', g_A0)`、`ρ(d, g_XIB − g_A0)`(XIB_LAG50 = 历史最好候选, 对 A0 的 ρ=0.889)。
**若 `|ρ(d, g_XIB−g_A0)| ≥ 0.60`, 本文自认覆盖层与既有 alpha 再加权同源, 并在结论里明写。**

## §9 ENV 白名单(E-0826-D)
pod2 侧启动方式逐字为:
`env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/root /workspace/venv/bin/python <device> PATH,HOME,PWD,SHLVL,_,LANG,LC_CTYPE,__CF_USER_TEXT_ENCODING`
装置把**实际** `os.environ` 全量枚举写进收据(`env_actual`), 断言白名单外为空集, 并断言以下前缀**一个都没有**:
`CAL JUDGE UPLIFT PANEL LOOK WRULE LEGS PHI FSEED W3FIX FTRIM UMASK SLOW FPRED MEMBERS_TOPN COSTB SLEEVE KMOD SEAT RNSM LTRIM CDAMP FUNDSCALE FEMAT TRADE_TOPN REF_SKIP PYTHON OMP MKL`。
**口径只从工件的 `config_json` 读。** 收据里 `env_whitelist` 字段**不得为空**(第十二轮留了四份空白, 本文明令不得重犯)。

## §10 实盘零接触 / GPU
`~/dl_quant_live` 与 `~/wide_shadow` 全程**只读源码与配置**, 未写、未重启、未下单、未调账户 API。
pod2 **只用 CPU**, 装置启动与结束各记一次 `nvidia-smi`, 必须 0% / 2MiB。GPU 与独立研究员共享, 不抢不杀。

## §11 可以杀掉它的事(先写下来)
1. GATE P 不过。2. GATE M 不过(beta 差没动)。3. dg ≤ 0。4. 边际换手把成本吃光, 3.2167× 下翻号。
5. 最差日变深 / 停机变多。6. 任一零假设赢过真臂。7. `ρ(d, XIB−A0) ≥ 0.60`(那它就是老东西换皮)。
**只要 2023 与 2026 双双变好而 beta 在两年符号相反, 就必须回头质疑构造** —— 预注册要求装置额外印出 2023/2026 的 θ 均值与符号, 用来判断到底是不是"两头都占"。
