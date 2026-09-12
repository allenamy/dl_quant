# PREREG · r16 · 免交易带的**非对称**免除: 只让"去风险"的那一半交易绕过带(冻结于第一个数字之前)

> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(subagent r16-asym-band, team-lead 派工)| **分支:** research/book-uplift-2026-09-11 | **状态:** 冻结 — 本文写定后计算 sha256, 每台装置在跑之前断言该 sha | **作废条件:** 口径钉 `CALIBER_PIN_v4_2026-09-11.md` 被更新的链取代; 或装置 `w10_sleeve.py`(sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`)换代; 或在役生产者 `shadow_bundle/config.json` 的 `params.{alpha,band}` 被改动
> **实盘零接触:** `~/dl_quant_live` 与 `~/wide_shadow` 只读(只 `sed -n` 读了 `fea171/combo_stage.py` L78-100 与 `shadow_bundle/config.json`); 不写、不重启、不下单、不调任何交易端点; 无网络请求。pod2 只用 CPU; 不碰 PID 333197 / 339489(T 态); 不碰 `r15_structural/`。
> **只量, 不改书:** 带住在生产者 `combo_stage.py` 里, 任何改动 = 书行为改动 = 预注册 + 用户裁定。本轮**只测量**。

## §0 本轮问题(承 r12, 不重测对称加速)

r12(`r12_smoothing/RESULT_r12_smoothing_2026-09-12.md`)已在本口径上钉死: 在役整形(α=0.1, b=0.00025, SKIP 型)有效滞后 11.637 锚 = 46.5h(EMA 8.54 + 带 3.10); **整本书调快, 每个方向都亏**(9/9 bypass 臂双种子为负, 零增量成本下仍负); 最优角在**更慢**一侧; 崩后反转零滞后也捕不到。**这些不再测。**

独立研究员提出 r12 **没测**的那一臂, 且它是非对称的: **只对交易里"去风险"的那部分免除带**(把仓位推向零或穿过零), 加风险的交易一律按在役 α 与带。机制: 带挡住小额出场 —— 目标恒定小于权重 0.25% 的误差永不更新; 1% → 0 的目标停在 ≈0.229%(α·H < b ⇔ |H| < b/α = 0.0025; 0.9 × 0.00254 = 0.00229); 其实盘分解里有"写出的目标已归零但仓位仍在"与"写出的目标已反号但仓位仍是旧号"两组。r12 自己的"带贡献 3.10 锚滞后"是同一机制。**问题只有一个: 既然入场不值得加快, 出场单独加快值不值得。**

## §1 在役带的语义(先读源码, 再写旋钮)

| 消费者 | 式 | 文件:行 | 标签 |
|---|---|---|---|
| 在役 combo 书(两条链各自 EMA 态 H) | `smv = H + P["alpha"]*(tgt-H)`; `trade = smv-H`; `smv = where(|trade| < P["band"], H, smv)` | `~/wide_shadow/fea171/combo_stage.py` **L89-L91**(`chain()`) | VERIFIED(本机 `sed -n 78,100p`) |
| 参数 | `alpha=0.1`, `band=0.00025` | `~/wide_shadow/shadow_bundle/config.json` → `params` | VERIFIED(本机 json 直读) |
| 回放 king 链 | `sm = H + 0.1*(tgt-H); trade = sm-H`; `sm = where(|trade| < 2.5e-4, H, sm); trade = sm-H` | `trackA/w10_sleeve.py` **L253-L254** | VERIFIED(本机 cat -n) |
| 回放 F10 链 | `_smf = HF + 0.1*(_tgtf-HF)`; `_trf = _smf-HF`; `_smf = where(|_trf| < 2.5e-4, HF, _smf)` | 同文件 **L293-L295** | VERIFIED |
| 混合 | `smb = (1-PHI)*sm + PHI*_smf`(L303); 记账在 smb(L312) | 同文件 | VERIFIED |

带的形态是 **SKIP**(保持 H, 不摊残差), 逐链施加, 混合在带**之后**。**旋钮必须坐在两条链各自的带步之后、以该链自己的 `(tgt, H)` 判定去风险**, 与生产者 `chain()` 若改会改的位置同构。

## §2 装置

`w10_r16.py` = 钉住的 `w10_sleeve.py`(parent sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`, pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` 与仓内 `trackA/w10_sleeve.py` **两处重算**, 不等则停)+ 三个环境旋钮 `{XMODE, XNULL, AUX16}`, 由 `devices/mk_device16.py` 逐处替换并断言每处**只命中一次**。

- `XMODE ∈ {"", X0, X1, X2, X3, X4, X5}`; `""` = 在役(默认)。
- `XNULL ∈ {0,1,2,3}`; 0 = 处理; d≥1 = 匹配随机免除 null(§5), `numpy.random.default_rng([4242, d])`, **每次 `run()` 起始重播种**(S0 臂不污染 d30_n2_c42 臂的流)。`XNULL>0` 而 `XMODE==""` 断言拒绝。
- `AUX16 ∈ {0,1}`; 逐锚仪器(§7), **只追加列, 绝不被书读取**。
- 装置在 import 时**断言本预注册文件的 sha256**(`PREREG16_SHA` 写死在装置里; 路径 pod2 `/workspace/uplift_2026-09-11/r16_asym_band/PREREG_r16_asym_band_2026-09-12.md`)。
- 装置自报 `_CFG["R16"] = {parent_sha256, prereg_sha256, XMODE, XNULL, AUX16}` 进 `config_json`。

**逐链判定(在该链带步之后, 用该链的 tgt 与带步前的 H):**
```
gap    = tgt − H;  nz = gap ≠ 0
step   = 0.1·gap;  banded = nz ∧ |step| < 2.5e-4          # 在役带会把它按住的名
DR     = nz ∧ (tgt·H < 0  ∨  |tgt| < |H|)                  # 去风险: 推向零或穿过零(H=0 的新开仓不算)
RI     = nz ∧ ¬DR                                          # 加风险
FLIP   = nz ∧ tgt·H < 0                                    # 反号
ZT     = (tgt == 0) ∧ (H ≠ 0)                              # 写出的目标为零但仓位仍在
```

**GATE P(关门条件, 不过则停并如实报告):** `XMODE="" AUX16=0` 与 `XMODE="" AUX16=1`, 其余 env 与 r3k 归档臂逐字同(§8), 两个种子, 产出的 `d30_n2_c42_rec` / `d30_n2_c42_W` 必须与归档 `/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{42,2027}.npz`(sha256 `352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339` / `aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b`)的 `rec` / `W` **`np.array_equal` 为真, maxabs 0.0**(NaN 位置亦须一致)。`config_json` 允许不同(多了 R16 自报字段)。
`float("0.1")==0.1`, `float("2.5e-4")==2.5e-4`; `XMODE==""` 时 `_x16_apply` 原样返回在役 `sm`(不新建数组, 不改一个位), 只算计数器。

## §3 臂(K = 6, 先声明, 不加格)

| 臂 | 免除集 T | 免除后该名的 sm | 其余名 | 目的 |
|---|---|---|---|---|
| **X0** | `DR ∧ banded` | `H + 0.1·gap`(EMA 步照走, **只免带**) | 在役 | 研究员提案的最小形 |
| **X1** | `DR` | `tgt`(**免带 + 免 EMA**, 直接跳到目标) | 在役 | 去风险全速 |
| **X2** | `FLIP` | `tgt` | 在役 | 只救"目标反号仓位仍旧号"一组 |
| **X3** | `DR` | `H + 0.3·gap`(α_exit = 0.3, 免带) | 在役 | X0 与 X1 之间的剂量点 |
| **X4** | `RI ∧ banded` | `H + 0.1·gap`(只免带) | 在役 | **对照(镜像 X0)**: 给加风险交易免带。**必须比 X0 差**, 否则构造没有做它声称的事 |
| **X5** | `ZT` | `0`(= tgt) | 在役 | 只救"目标归零仓位仍在"一组; X2 + X5 + (部分减仓) 分解 X1 |

**不测**: 任何对全书对称的 α/b 变化(r12 已关); 任何按 regime/状态切换的形(r12 §6 已做且不合格); 任何 |H| 门槛扫描(不加格)。

## §4 窗口 · 统计量(冻结, 与 r12 / 口径钉逐字同)

- `g_t = net_ex_t / gross_total_t`(rec 列 18 / 列 5), bps/锚/单位 gross; `net_ex = pnl_ex − carry_ex − cost_ex` 恰好(列 19/20/21, 逐锚断言)。
- **W_ALPHA** = 丢前 900 锚 ∧ `ts ≤ 2026-08-30 20Z` ⇒ **n=9138**(断言): mean / CI / Sharpe / 换手 / 分解 / regime。
- **W_TAIL** = `ts ≤ 2026-08-30 20Z`, 不丢暖机 ⇒ **n=10038**(断言): maxDD / 最差 UTC 日 / 停机线频率 / 1 年窗。
- **king-live 子样本** = W_ALPHA ∧ `ts ≥ 2024-01-01 00Z`: 主表另报一遍(归档 A0 的 king 腿在 2024-01 前无预测, F10 前缀亦为空; 数量在结果里 VERIFIED 后写出)。
- CI95(mean / 配对差) = UTC 日块自举 **2000** 次, `numpy.random.default_rng([20260905, k])`, k=0 主 / k=9 复核; 装置 = `r8_inbook/fastboot.py` 的闭式等价(`r12_smoothing/devices/analyze12.py` 同函数逐字移植)。配对差 = 同一批日抽样下 `mean(g_arm) − mean(g_A0)`。
- **Bonferroni-K(K=6)**: 另报 `1 − 0.05/6` 水平的配对差区间(分位 `0.05/12` 与 `1 − 0.05/12`)。
- Sharpe = mean/sd(ddof=1)·√2190; SE(Sharpe) = √(2190/n)。
- **换手 = 匹配口径**: 主报 `mean_t(turnover_t / gross_total_t)`(rec 列 17 / 列 5; A0 = **0.0540270**), 另报执行器口径 `mean_t(Σ|trr|_t / gross_total_t)`(AUX16 列; A0 = 0.05563)。**绝不**把 RAW 0.03032 与 g 并列。边际换手 = 臂 − A0。
- **分解**: `dpnl = mean(pnl_ex/gt)_arm − A0`, `dcarry`, `dcost` 同; 断言 `dg = dpnl − dcarry − dcost`(1e-9)。
- **成本(约束 7)**: 主结论在 λ=1(拟合模型 `costb_PWR_G230k.json` sha256 `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`, pod2 与仓内两处重算)。另报 `dg(λ) = dpnl − dcarry − λ·dcost` 与 `survival(λ) = 1 − λ·c`(c = 该臂 cost/gross)于 λ ∈ {1.0, 0.8096, 0.2545}(r14 `RESULT_r14_cost_estimand` §6: R4 手续费下界 / R1 ERA2 稳态现金), 并明写**哪些符号依赖 λ**。**不重定价; λ<1 的数字不是判决。**
- 分辩率提醒: 口径钉 §4 的 ±0.23 bps/锚是冻结窗(n=3168)分辨率; 本窗 n=9138 的分辨率由配对差 CI 直接给出。|dg| < 0.23 另行标注。

## §5 null(约束 8): 换手匹配 + 计数匹配的随机免除

**不用**逐锚置换 placebo(已知缺陷)。对每臂、每种子、d ∈ {1,2,3}: 在**每锚每链**, 处理的免除集 T 落在池 pool 内(X0/X4: pool = banded, 量纲 = |step|; X1/X2/X3/X5: pool = nz, 量纲 = |gap|)。null 从 pool 里抽 **与 T 同数** 的名, **按量纲四分位分层**(池内 |·| 的 25/50/75 分位切 4 桶, 每桶抽与 T 在该桶内同数; 桶内全取时不抽), 用 `default_rng([4242, d])`(每次 run() 起始重播种, 逐锚逐链顺序消耗)。被抽中的名施加**与该臂相同**的免除动作。
⇒ null = "同一构造, 免除同样多、同样大小分布的交易, 但不看方向"。处理与 null 的差 = 方向(去风险)本身的价值。
**读法**: 处理的 dg 必须落在 3 个 null 的 dg **之外(更高), 3/3**; 另报配对自举 `mean(g_arm) − mean(g_null_d)` 的 CI95。null 数 = 6 臂 × 3 × 2 种子 = 36 次运行。

## §6 regime · 尾部(冻结)

- **34 单元**: 逐字复用 `r12_regime/PREREG_r12_regime_partition_2026-09-12.md`(sha256 `e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c`, 本机重算)§4 五族 + 事件窗 + R72 五分位 = YEAR 5 + BRD 3 + XSV 3 + MV 3 + SIGF 3 + R72 5 + 事件 6×2(含补集)= **34**; 标签构造函数 = `analyze12.py build_labels` 逐字移植。
- **原语文件 = v2**(`/workspace/uplift_2026-09-11/r12_regime/causal_primitives_r12_v2.npz` sha256 `0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f`, = 仓内 `r12_regime/receipts/causal_primitives_r12_v2.npz`, 收据 parity 8.09e-6 bps)。**注**: `r12_smoothing/analyze12.py` 指向的 `r12_smoothing/causal_primitives_r12.npz` sha256 `c74fd695…`(978500 B)与 v2 不同, 且与 r12_regime 已作废的 v1(`README_VOID_v1.md`)同 sha ⇒ r12_smoothing 的逐单元数字用的是 v1 原语; 本轮用 v2, 差异若影响单元归属会在结果里报出。
- 每单元: n, mean g, Sharpe, SE, dg vs A0 与 CI95。**必须具名报出** `POSTCRASH / BROADRALLY / ALTSURGE_BROAD / DEEPNEG_SHORT`(研究员的主张是"反转时的出场")。
- **W_TAIL**: 日收益 `r_day = Π(1 + 2.0·g·1e-4) − 1`; 两套口径: 回放原样 + 诚实实盘波动(保均值、偏差 × 1.4042, r11); HALT ≤ −4.00% / ALERT ≤ −2.68% / DD 线 −25%(`watchdog.py` L109/L117/L131); maxDD prepend 起点(E-0909-C); 1 年重叠窗中位 CAGR 与 P(1y DD ≥ 25%)(重叠窗, 非自举 CI)。**抬高最差日或增加停机次数的臂不算赢。**

## §7 机制仪器(AUX16, 逐锚逐链, 不入书)

每链 14 列: `n_gap, n_DR, n_DR_banded, n_RI_banded, n_exempt, n_exempt_moved, exempt_abs_dw, n_zt, sum_abs_sm_zt, n_zt_stalled, n_zt_m, sum_abs_sm_zt_m, n_flip, n_flip_banded`(zt = 目标为零仓位非零; `_m` = 只算当锚成员; stalled = sm==H); 加 `turn_ex_all = Σ|trr|`, `turn_ex_member = Σ|trr[m]|`。
报: **零目标后的平均残余仓位** `Σ sum_abs_sm_zt / Σ n_zt`(A0 应 ≈0.0023 权重口径, X0/X1/X5 应趋零), 停滞份额, **免除出场实际发生的锚数**(`n_exempt_moved > 0`)与总名数, 每锚被带按住的去风险名均数。

## §8 ENV 白名单(E-0826-D)· 复跑

pod2 每次运行 `env -i` 显式注入, **只有**: `PATH=/workspace/venv/bin:/usr/bin:/bin HOME=/root LANG=C.UTF-8 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4` + 书 env(与 r3k/r12 归档臂逐字同):
`LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json FSEED={42|2027} FPRED=f10_A0_s{42|2027}.npy` + `XMODE XNULL AUX16 OUT_TAG PREREG16_PATH`。W3FIX 不设。
cwd = `/workspace/uplift_2026-09-11/r16_asym_band/dev`(符号链接 `pod_backup_2026-08-21 → r8_inbook/dev/pod_backup_2026-08-21`, `dlw_2026-08-22 → /workspace/dlw_v4raw`, `f8_2026-08-22 → health_check/dev_v4/f8_2026-08-22`, 与 r12 逐字同); 解释器 `/workspace/venv/bin/python`(3.11.10, numpy 2.4.6)。每次运行的完整 env 列表 + cmd 落盘 `receipts/R16_RUN_ENV.json`。
复跑(逐字): `ssh pod2; cd /workspace/uplift_2026-09-11/r16_asym_band; /workspace/venv/bin/python gate16.py; /workspace/venv/bin/python drive16.py arms; /workspace/venv/bin/python drive16.py nulls; /workspace/venv/bin/python analyze16.py`。
启动前后 `nvidia-smi` 必须 0% / 2 MiB; 启动前 `/proc/loadavg` > 6 则等待。

## §9 判决规则(先于数字)

对每臂, 在两个种子上:
- **ADMIT(= 进入预注册 + 用户裁定的候选, 不是上线)** ⇔ 全部成立: (a) dg > 0 双种子; (b) s42 的 Bonferroni-6 配对差区间排 0 且 s2027 的 CI95 排 0; (c) 处理 dg 高于全部 3 个 null, 双种子; (d) W_TAIL 诚实波动口径下: 最差 UTC 日不比 A0 更差超过 0.5 pp **且** 停机/年 ≤ A0; (e) dg(λ) 在三个 λ 上同号; (f) 对照 X4 的 dg < X0 的 dg(构造检查, 对所有臂的录取都是前置)。
- **REJECT** ⇔ dg < 0 双种子, 或任一种子 dg 的 CI95 排 0 且为负。
- 其余 **UNDECIDED**。
- (f) 不成立 ⇒ 整轮标 **CONSTRUCTION-FAIL**, 不录取任何臂, 如实报告。
**每臂都报, 不因结果挑选。**

## §10 交付

`PREREG_r16_asym_band_2026-09-12.md`(本文 + sha)· `RESULT_r16_asym_band_2026-09-12.md` · `devices/{mk_device16.py, w10_r16.py, gate16.py, drive16.py, analyze16.py}` · `receipts/{PREREG_FREEZE_sha.txt, GATE_P.json, R16_RUN_ENV.json, RESULT_R16.json, logs}` · `SHA256SUMS.txt`。每个数字标 VERIFIED / INFERRED。
