> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结 — 本文在计算任何数字之前写定, 两台装置运行前断言本文 sha256 | **作废条件:** `signal/legs.py::reshape_after_withhold` 语义改变; 或出现比 v4 更新且逐门验过的链

# PREREG r13-A · T1 FORM A(半区美元缩放)—— **测量臂, 非候选臂**

## §0 本轮的定位(先说死, 免得结论被误读)

上游可部署性裁定 `r13_deploy/RESULT_r13_deployability_2026-09-12.md`
(sha256 `63d813b822fdf93829687deada112876d9a312907612558f0ecfc588461edbcb`)判 **FORM A = 不可表达(NO)**:
执行器每锚跑 `w ← (w − mean w)/‖w − mean w‖₁`, 对任何半区美元倾斜 `d` 的输出恒为 `gL−gS = 0`。

**因此本轮的最高可达裁定是 `NOT_DEPLOYABLE`, 不是 `ADMIT`。** 即使每一个门都过, FORM A 也不能被当作候选臂提交。
本文冻结的是**测量**: FORM A 到底有没有价值, 以及**执行器要改成什么样才可能拿到它**。

**同时冻结一条反证义务**: r13_deploy §3.3 指出, 一个建在**今天这条链**上的 FORM A 臂, 活下来的只有
`Δwᵢ = d(|wᵢ| − 1/N)` 这个**集中度倾斜**, 与 β 无关。所以本轮**必须同时建两条路径**并分别报告:

| 路径 | 定义 | 意义 |
|---|---|---|
| **AM_\*(A_MEAS)** | 叠加层作用在**已 reshape 的 `smr`** 上, 之后**不再** redemean(= 反事实执行器 `RESHAPE_REDEMEAN=False`) | FORM A 的**真身**。**不可部署。** |
| **AS_\*(A_SHIP)** | 叠加层作用在生产者写盘形态 `sm`(净额 −5.9%)上, 然后**照今天的执行器**跑一次 reshape | **今天真按下去会发生什么**。美元倾斜被湮灭, 只剩集中度倾斜。 |

**若 AS 与 AM 的 dg 同号同量级 ⇒ 本轮测到的不是 β 敞口, 是集中度倾斜, 必须据此推翻 β 解释。**
(错题集形态: `measuring_a_misunderstood_quantity.md`)

## §1 口径锁与仪器(全部在装置内断言)

| 项 | 值 / 断言 |
|---|---|
| 口径锁 | `CALIBER_PIN_v4_2026-09-11.md`。**禁** `_ext` 缓存 / `pod_fea_ext.py` / 裁剪复利记账 / `pod_legs_ext.py` / `shadow_bundle_v3` / `wide_fea_v2ext_meta` / `panel_source.py` 默认脏面板 / 对 pod 5m 谱系施 `expm1` |
| 书序列 | `r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz` sha256 断言 `352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339` |
| 产它的装置 | `trackA/w10_sleeve.py` sha256 断言 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` |
| 形态 | `PHI=0.45 LEGS=101 WRULE=msharpe LOOK=900 UMASK_SCOPE=m1 CAL=log FTRIM=zero`(装置从 `config_json` 读并断言, **不从环境读**) |
| 记账元 | pod `pod_backup_2026-08-21/wide_fea_hist_meta.npz` → realpath 断言 = `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` |
| 面板 | `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz`(`f_fund_now`, `f_fund_iv`) |
| 掩码 | `/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz` |
| 成本 | `r3k/costb_PWR_G230k.json` sha256 断言 `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53` |
| regime 原料 | `r12_regime/receipts/causal_primitives_r12_v2.npz` + `PREREG_r12_regime_partition_2026-09-12.md` sha256 断言 `e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c` |
| y4 口径 | pod 5m 谱系 **Σ 5 分钟简单收益, 无 expm1**(E-0904-F)。`CAL=log` ⇒ 装置内 `yv = y4`, 不施 `expm1` |

## §2 两个窗(不可混用)

- `W_ALPHA` = 丢前 900 锚(E-0911-A)∩ `ts ≤ 2026-08-30 20Z`(E-0911-D)⇒ **n = 9138**。
  **只有** mean g / dg / CI / Sharpe / 换手 / 成本 / 腿数 / 逐 regime alpha 用它。
- `W_TAIL` = `ts ≤ 2026-08-30 20Z`, **不丢暖机** ⇒ **n = 10038**。
  **所有** maxDD / 最差 UTC 日 / HALT·ALERT 频率 用它。
装置内硬断言 `W_ALPHA.sum()==9138 and W_TAIL.sum()==10038`。

**声明(限制, 不遮):** β̂ 需要 250 锚暖机 ⇒ `W_TAIL` 的前 250 个锚 `d ≡ 0`(臂 = A0)。这使 W_TAIL 上的尾部对比**偏保守地低估**叠加层的尾部影响, 必须在结果里重复这一句。

## §3 β 估计器(冻结)

- **基准** `A_t` = 在册成员的等权截面 4h 收益。成员规则 = `MEMBERS_TOPN=829` 按 `qvk` 逐锚重建(`w10_sleeve.py` L31-37)再过 `UMASK m1 (CRYPTO)`(L155-158/L211-214)。
  **装置断言**: 重算的 `A_ew` 与 `causal_primitives_r12_v2.npz` 的 `A_ew` 列**逐位相等(maxabs == 0.0)**。不发明第二个基准(r13_deploy §8 第 5 条)。
- **估计** `β̂ᵢ(t;W) = cov(yᵢ, A)/var(A)`, 尾随 `W = 250` 锚, 窗 `[t−W, t)` **严格在 t 之前**, 成对完整(pairwise-complete), 要求窗内有限观测 `n ≥ 0.8W = 200`, 否则 `β̂ᵢ = NaN`。
  实现 = 逐锚滚动累加器, **带 `I0` 卫兵**(只减这个循环真加过的行 —— r13_deploy §9.3 的 bug 形态)。
- **收缩** Vasicek/James-Stein, 系数 = r13_deploy §7.2 实测信度 **λ = 0.86**(W=250):
  `β_usedᵢ = β̄ + 0.86 (β̂ᵢ − β̄)`, `β̄` = 该锚全部有限 β̂ 的**等权截面均值**。NaN 名不参与、也不被赋值(与 r13 的 `okb` 约定一致), 装置报告每锚的 **β 覆盖率**(有限 β 名占半区毛额的比例)。
- **不重估 W**。W=250 由上游 GO 裁定选定(ρ_SB 0.856 / ρ_OOS 0.683 / 存活 0.763)。

## §4 FORM A 的代数(先于数字)

reshape 后 `Σ smr = 0` 且 `Σ|smr| = gross_total` ⇒ 半区毛额 `gL_abs = gS_abs = L1/2` **精确相等**(装置断言 ≤1e-12 相对)。
令 `w_ex = smr/gross_total`(`Σ|w_ex| = 1`), 定义

- `B_L = Σ_{i: smr>0} w_ex,i β_used,i`  ,  `B_S = Σ_{i: smr<0} w_ex,i β_used,i` (`B_S` 通常为负)
- 书 β `β_book = B_L + B_S`;  半区篮子 β `β_L = 2B_L`, `β_S = −2B_S` ⇒ **`β_book = (β_L − β_S)/2`**

FORM A: `w_L ← w_L(1+d)`, `w_S ← w_S(1−d)` ⇒
`‖w′‖₁ = 1`(毛额精确守恒), `Σw′ = d`(这就是要的美元倾斜), 且
**`β′_book = β_book + d(B_L − B_S)`**, 其中 `B_L − B_S = (β_L + β_S)/2 ≈ β̄ ≈ 1.07`。

⇒ 闭合剂量 `d* = −β_book / (B_L − B_S)`, 在 `|B_L − B_S| < 0.2` 时置 `d = 0`(退化保护, 预注册)。

**★ 必须写进结论的一句话:** FORM A **不改变** `β_L − β_S`(半区篮子 β 缺口)—— 它用**敞口项**去抵消**选择项**。
所以"beta_gap_closed" 这一问对 FORM A 有两个答案: `β_L − β_S` **按构造不动**(装置断言 |Δ| ≤ 1e-9), `β_book` 被推向 0。两者都要报。

## §5 臂集(K = 18, 冻结)

**剂量 `frac`** = 闭合比例, `d = frac × d*`。

| # | 臂 | 路径 | 定义 |
|---|---|---|---|
| 1 | `AM_f025` | A_MEAS | `frac=0.25` |
| 2 | `AM_f050` | A_MEAS | `frac=0.50` |
| 3 | **`AM_f100`** | A_MEAS | `frac=1.00` ← **主臂**(nulls 挂在它上面) |
| 4 | `AM_f100c10` | A_MEAS | `frac=1.00`, `|d| ≤ 0.10` |
| 5 | `AM_cond` | A_MEAS | `frac=1.00`, 仅当 `|d*| > 0.05` 开火, 否则 `d=0`。阈来源: r13_deploy §7.3 已发表的 `sd(β_ante)=0.0591` ÷ `β̄≈1.07` = 0.055, **取整为 0.05, 不看本轮数据定阈** |
| 6 | `AM_static` | A_MEAS | `d` = `d*` 的**扩张窗因果均值**(≥900 锚历史, 否则 0)。检验"时变是否有用" |
| 7 | `AM_flip` | A_MEAS | `d = −d*`(反臂)。机制为真 ⇒ 应对称为负 |
| 8 | `AS_f025` | A_SHIP | 同 1, 走今天的链 |
| 9 | `AS_f050` | A_SHIP | 同 2 |
| 10 | `AS_f100` | A_SHIP | 同 3 |
| 11 | `AS_f100c10` | A_SHIP | 同 4 |
| 12 | `AS_cond` | A_SHIP | 同 5 |
| 13-15 | `AM_SHIFT101/503/1009` | A_MEAS | 零假设: β 矩阵整体时移 k 锚(毁掉时间对齐, 保留截面分布与持续性) |
| 16-18 | `AM_RELAB1/2/3` | A_MEAS | 零假设: 逐锚**同一个固定**符号置换作用于 β 向量, `default_rng([4242, k]).permutation` |

**Bonferroni K = 18**(全部臂计入, 含零假设臂 —— 保守)。

**零假设的匹配(约束 7):** 每条 null 的 `d` 序列整体乘一个标量 `κ`, 使其 **W_ALPHA 上的边际换手(匹配口径)等于主臂 `AM_f100` 的边际换手, 相对误差 ≤ 1%**;并且**开火计数相同**(连续剂量臂 ⇒ 两者开火锚数都是全部有 β 的锚, 装置逐锚断言开火集合相等)。逐锚置换 placebo **已知有缺陷, 不用**。

## §6 统计量与判读(冻结)

- `g = net_ex / gross_total`, bps/锚/单位 gross(判官冻结定义)。
- **主统计量** `dg = mean(g_arm − g_A0)` on `W_ALPHA`, **逐锚配对**。
- `CI95(dg)` = **UTC 日块自举 2000 次**, `numpy.default_rng([20260905, k])`, 对单元覆盖的 UTC 日有放回抽样, 抽中日取该日全部锚, 统计量 = `Σ Δnet / Σ gross`(与 r12 `boot_ci` 同构, 只是作用在配对差上)。
- `Bonferroni-18` = 用 `α = 0.05/18` 的分位(百分位 `0.1389%` / `99.8611%`)。
- `Sharpe_ann = mean/sd(ddof=1)·sqrt(2190)`; `SE = sqrt(2190/n)`。
- 日收益(2.0×): `r_day = Π(1 + 2.0·g·1e-4) − 1`。**HALT ≤ −4.00%**, **ALERT ≤ −2.68%**。
- maxDD: 权益曲线已 prepend 起点(E-0909-C)。

**换手(约束 6):** 一律**匹配口径** `turnover/gross_total`。A0 基准 = **0.0540270**(RAW 字段 0.03032 **未归一**, 混用是 1.4375× 错误)。
本轮的边际换手 = `Σ|w′_ex,t − w′_ex,t−1| − Σ|w_ex,t − w_ex,t−1|`(`‖w_ex‖₁ = 1`, 与 0.0540270 同口径可直接相加)。

**成本双报(约束 6, 强制):** `dg` 在 **fitted** `costb_PWR_G230k.json` 下报一次, 并报 **×3.2167 重定价**下的
`dg_reprice = dg_fitted − 2.2167 × Δcost_g`。**「实现成本是否 ≈ 模型的 3.2167 倍, 在我方两台仪器之间有争议且未解决;r12 已证明它决定每个加换手臂的符号」—— 这句话必须出现在每一个含 dg 的表旁。**

**判读阈值(先于数字):**

| 门 | 要求 |
|---|---|
| GATE P(必过, 否则全轮作废) | (a) 由存档 `W` 重建的 `pnl_ex/carry_ex/cost_ex/net_ex` 对存档列 maxabs **≤ 1e-3 bps**(`W` 以 float32 存盘, 逐位不可得 —— 这一点先于数字声明);(b) 叠加层关掉(`d≡0`)必须与本装置自己的基线**逐位相等 maxabs == 0.0**;(c) 本装置基线在 W_ALPHA 上 `mean g` 与 `Sharpe` 对 r12 存档自检值 `+0.6341957 / 1.2912234` 的绝对差 ≤ 1e-5 |
| G1 机制门 | `|β_book|` 的均值必须下降 ≥ 50%(frac=1.00 臂);且 `β_L − β_S` 变动 ≤ 1e-9(构造自检) |
| G2 主门 | `dg` 的 CI95 下界 > 0 **且** Bonferroni-18 下界 > 0 **且** 点估计 > **+0.23**(自举分辨率) |
| G3 成本门 | `dg_reprice` > 0(符号在重定价下不翻) |
| G4 尾门(W_TAIL) | 最差 UTC 日不更差;HALT 次数不增加;全样本 maxDD 不加深 |
| G5 regime 门 | 2023(β 为正, `+0.0374`)与 2026(β 为负, `−0.0913`)**必须反向**。若两年**同向变好** ⇒ **对自己的构造起疑并写明为什么**(这不是加分项, 是警报) |
| G6 零假设门 | 6 条 null 的 `dg` CI95 **全部含 0** |
| **最终裁定上限** | 即使 G1–G6 全过, 裁定仍为 **`NOT_DEPLOYABLE`**(§0)。本轮不产出候选臂。 |

## §7 已由上游关闭, 本轮不重开(不 re-litigate)

- 「把书做快」已判负(有效滞后 11.64 锚 = 46.5h;绕过平滑 9/9 双种子为负, 零成本下仍负;崩后反转 `dg −0.9887 [−1.7178, −0.2552]` 排除 0)。
- 逐 regime: 34 格里 2 格点估计 > Sharpe 3.0, **CI 下界 0 格**;34×5 = 170 读数 0 格过 3.0。
- `CEM_99` 仍是十二轮最佳且仍 (C) UNDECIDED。

## §8 实盘零接触

`~/dl_quant_live` / `~/wide_shadow` 全程不写、不重启、不下单、不调任何账户 API。pod2 **只跑 CPU**, 作业前后各测一次 `nvidia-smi`, 不排队不抢占(GPU 与独立研究员共享)。产物只落
`multi_asset/exports/research/uplift_2026-09-11/r13_A_halfscale/` 与 pod2 的同名目录。

## §9 ENV 白名单(E-0826-D)—— 枚举 + 断言 + **写进产物**

**pod2 装置** 启动方式(逐字):
```
cd /workspace/uplift_2026-09-11/r13_A_halfscale/devices && env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LANG=C.UTF-8 \
  python3 r13A_build_pod.py PATH,HOME,PWD,SHLVL,_,LANG
```
白名单作为**参数传入并被装置断言** = `{PATH, HOME, PWD, SHLVL, _, LANG}`;`env_extra` 与 `env_banned` 必须为空集。
禁用前缀集 = `CAL JUDGE UPLIFT PANEL LOOK WRULE LEGS PHI FSEED W3FIX FTRIM UMASK SLOW FPRED MEMBERS_TOPN COSTB SLEEVE KMOD SEAT RNSM LTRIM CDAMP FUNDSCALE FEMAT TRADE_TOPN REF_SKIP PYTHON OMP MKL`。

**本机装置** 启动方式(逐字):
```
cd .../r13_A_halfscale/devices && env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu \
  /usr/local/bin/python3 r13A_judge.py
```
白名单 = `{PATH, HOME, PWD, SHLVL, _, LC_CTYPE, __CF_USER_TEXT_ENCODING}`(后两个 macOS 强制注入, 已枚举)。
**两台装置都把实测 `env_whitelist` / `env_actual` / `env_extra` / `env_banned` 写进自己的收据 JSON。**
(r12 曾留下四个空白名单字段的收据 —— 本轮不得重复。)

## §10 叠加层的已知结构性限制(声明, 不是缺陷)

1. 叠加层作用在**已平滑、已过免交易带**的书上, **不回馈 EMA/带 的状态**。这是**保守**假设: 它的逐锚变动全额计入换手, 带永远不会替它减速。真实生产者内的实现会与带交互, 换手**可能更低**, 效应也可能不同。
2. `AS_*` 把叠加层放在 `combo_raw`(净额 −5.9%)上, 与生产者今天写盘的那一份一致(`combo_stage.py` L331/L351)。
3. 本轮**不改**任何实盘代码, 也**不提议**改 `RESHAPE_REDEMEAN` —— 只报告「要拿到 AM 必须允许什么」。
