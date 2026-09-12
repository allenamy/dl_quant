> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 r15) | **状态:** 冻结 — 本文在计算任何臂的收益之前写定; sha256 写入 `receipts/PREREG_FREEZE_sha.txt`, 每个装置运行前断言 | **作废条件:** 出现比 v4 更新且逐门验过的链; 或 GATE P 失败(那时本轮无结果) | **口径:** `CALIBER_PIN_v4_2026-09-11.md`(v4 链, 任何 v3 谱系数字作废)

# PREREG r15 · 两处结构缺陷的修法是否值钱: 位置层 FTRIM(FTPOS)与净额席位(SEATNET)在 v4 口径上的在书臂

## §0 问题与来源
独立研究员的平行报告点名在役书两处结构缺陷, 组长已从源码确认(其一另在实盘工件上量过):
1. **席位看不见 carry**: `~/wide_shadow/shadow_loop_v3.py` §7 席位输入 = 纯价格毛额腿收益(`st.LR[leg] = Σ zz/g·y4v`), 不含 carry 不含成本; fund 腿结构性付 carry。装置已有开关 `SEATNET=1`(`w10_sleeve.py` L168-169: 腿席位收益减去该腿单位 gross 秩书的 4h carry)。**唯一一次测量**(`docs/PREREG_seat_round2_dl_seat_and_net_2026-09-05.md` 臂 B2, REJECT −0.37; 高 σ_fund 档 −0.78; 席位推向 king 0.90)在 shadow_bundle_v3 / wide_fea_v2ext 上 = **禁用 v3 谱系**, 按本分支规则必须在 v4 重测。该轮同时记下反对意见: fund 腿秩书付的 carry ≈ 执行书的 2.2×(1.96 vs 0.88 bps/锚), 腿层 carry 高估惩罚; 书路径净额席位从未建过。
2. **FTRIM 的零是分数零不是持仓零, 且会漏**: 生产 `~/wide_shadow/fea171/combo_stage.py` L232-249 在 z<0 且 rn8≤−10bp/8h 处把 z 置 0("pre_zero"), 随后 `chain()` L81 在 sel 上去均值 ⇒ 被置零的名变成 −mean(w[sel])<0, 一个小空头**重新出现**, EMA 再把它带下去。组长在 2026-09-02 12Z..09-12 00Z 的 58 个实盘锚上量得: 双链被标记名均 9.2/锚, 其中 68% 生产目标仍为负; 漏出空头 gross 均 1.577%(p90 3.30%, max 5.29%); 它们付的 carry 均 0.2867 bps/锚/单位 gross = A0 全周期 carry_ex 的 59.8%。回放的 `FTRIM=zero`(L228-229/L276-277)是同一 pre-zero 设计, 所以 09-02 的 FTRIM 部署是在漏的形态上量的。装置另有一个**从未被判过**的开关 `FTPOS=1`(L306-310): 在平滑混合后的**书**权重上把 smb<0 且 rn8≤FTRIM_TH 的名置 0 并重标 gross; 置零名不进随后的执行器去均值(nz 掩码, L314-320)⇒ 真正的持仓零。
   **注意**: 0.2867 是**省下的 carry(毛)**, 不是净; trackA 量过 FTRIM 省下的 carry 大部分以放弃的价格 P&L 归还(该比值被审计标为无收据); 置零这些空头同时放弃它们的价格 alpha 并付出场换手。**净额才是问题。**

## §1 仪器(全部在跑前重算 sha; 任一不符即中止)
| 项 | 值 |
|---|---|
| 判决装置(不改) | `trackA/w10_sleeve.py` = pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py`, sha256 **b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650**(两处本轮已重算 VERIFIED) |
| 派生装置(只加仪表与 null 注入点, 主路径必须逐位同) | `devices/w10_sleeve_r15.py` = 判决装置 + `{R15_INSTR, R15_KILL_NPZ, R15_KILL_TH, R15_SEATC_NPZ, R15_SEATC_SCALE, R15_SB}`; 由 `devices/mk_r15_device.py` 从判决装置源码做字符串替换生成, diff 存 `devices/w10_sleeve_r15.diff`; 自报 self_sha256 |
| A0 归档臂 | pod2 `/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz` sha256 **352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339**(= 仓库 `r10_screen/CMUM_CARRY/pin/` 同名文件); `A0_PWR230k_s2027.npz` sha256 **aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b** |
| 成本 | `r3k/costb_PWR_G230k.json` sha256 **295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53**(K=0.17 α=0.87 POWER 拟合, λ=1.0) |
| A0 环境(在役形态, 逐字取自归档臂 config_json) | `LEGS=101 PHI=0.45 WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FTRIM_TH=-0.0010 UMASK_SCOPE=m1 CAL=log W3FIX 未设 FTPOS=0 SEATNET=0 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy FPRED=f10_A0_s{FSEED}.npy COSTB_JSON=r3k/costb_PWR_G230k.json`, FSEED ∈ {42, 2027}; 运行目录 = 与 `r3k/dev` 同构的符号链接树(pod_backup_2026-08-21/{wide_fea_hist_meta→meta_newprod_v4.npz, wide_panel_4h_hist_v2→wide_panel_4h_v2ext.npz, slow_pred_hist_oos→SLOW_v4.npy(被 SLOW_NPY 覆盖), nets_histv2_*}, dlw_2026-08-22→/workspace/dlw_v4raw, f8_2026-08-22→health_check/dev_v4/f8_2026-08-22), 每个输入 realpath + sha16 入收据 |
| regime 原语 | `r12_regime/receipts/causal_primitives_r12_v2.npz` sha256 **0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f**(仓库与 pod2 同) + 分区规则 `r12_regime/PREREG_r12_regime_partition_2026-09-12.md` sha256 **e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c** |
| 统计核 | UTC 日块自举 2000, `numpy.default_rng([20260905, k])`; Sharpe = mean/sd(ddof=1)·√2190, SE = √(2190/n) |

### §1.1 必须写进 RESULT 头部的基线事实(VERIFIED 2026-09-12 于 pod2)
- 归档 A0 臂**本身带 v3 谱系模型腿**: `build_dev_v4.py` 的 f10_A0 取自 f8_ext/preds, king 取自 `SLOW_v3_on_v4axis.npy`。这是被钉住的基线原样, **本轮不修它**, 只声明。
- king 腿在 W_ALPHA 前 **3300** 锚(至 2023-12-31 20Z)恒为 0(SLOW_v3_on_v4axis 2024-01-01 前全 NaN → L219 nan_to_num); F10 在前 **1110** 锚(至 2022-12-31)恒为 0(f10_A0_s* 2023-01-01 前全 NaN → L267)。W_ALPHA 内 king 在役子样本(ts ≥ 2024-01-01 00Z)**n=5838**。每个 headline 数字另在该子样本上报一遍。

## §2 臂(K = 5, 全部预先声明; 不加臂)
所有臂 = A0 环境 + 下列单一改动; 两个种子 s42 / s2027 都跑。

| 臂 | 改动 | 装置 | 机理 |
|---|---|---|---|
| **ARM-F** | `FTPOS=1`(FTRIM=zero 保留) | 判决装置 | 位置层 FTRIM: 在混合书上把 smb<0 ∧ rn8≤−10bp 置 0 并重标 gross; 置零名不进执行器去均值 |
| **ARM-S** | `SEATNET=1` | 判决装置 | 腿净额席位: 腿席位收益 − 该腿单位 gross 秩书 4h carry |
| **ARM-SB** | `R15_SB=1` | 派生装置 | **书路径净额席位**(定义见 §2.1) |
| **ARM-F05** | `FTPOS=1 FTRIM_TH=-0.0005` | 判决装置 | 敏感性: 阈值放宽(注意: FTRIM_TH 同时移动分数层 pre-zero 与位置层 kill 两处阈, 装置只有一个阈) |
| **ARM-F20** | `FTPOS=1 FTRIM_TH=-0.0020` | 判决装置 | 敏感性: 阈值收紧(同上说明) |

Bonferroni: K=5 ⇒ 每臂 α = 0.01 ⇒ 自举分位 0.5% / 99.5%(下称 CI99-K)。CI95 也报, 但录取看 CI99-K。

### §2.1 ARM-SB 的精确定义(新构造, 因果; 声明为「对执行书贡献」的代理而非其本身)
组长定义「每腿对**执行书**净额的滚动实现贡献」。混合书 sm 是各腿 z 的非线性函数(sel 去均值 / cap / EMA / 带 / 混合 / kill), 不能无假设地线性归因到腿。可干净定义的最近代理: **每腿各自走一遍与执行书同构的链, 用它自己那本平滑书的实现净额作席位输入**。
在 `legs()` 内, 对每腿 L ∈ {king, rev24, fund}, 锚 i(成员 m 经 umask, 面板行 j):
- `z_L` 同现装置(fund 在 m1 下用 FZB); `sel = isfinite(y4[i,m]) ∧ qv4h ≥ 2.5e5`(与 run() L234-235 同式); `sel.sum()<80` 或 gross<1e-9 ⇒ 该锚 LR_L = 0, 状态不动
- `w = where(sel, z_L, 0); w[sel] −= mean(w[sel]); w /= Σ|w|; capw = 2.5/nsel; clip(±capw); 再 L1 归一; tgt[m] = w`(= L242-249)
- `sm_L = H_L + 0.1·(tgt − H_L)`; 带 `|Δ|<2.5e-4 ⇒ 不动`; 非 sel 名强制 0(= L253-258)
- 执行器去均值: `nz = |sm_L|>1e-12; smr_L[nz] −= mean(smr_L[nz])`, 重标 gross(= L314-320); `trr = smr_L − HR_L`
- `net_L = [Σ_m smr_L·y4 − Σ_m smr_L·fnow·(4/iv) − Σ_tier |trr|·rate_tier]·1e4 / Σ|smr_L|`(bps/锚/单位 gross; CAL=log ⇒ y4 原值不 expm1; 成本档与 COST_B 同)
- `LR_L ← net_L; H_L ← sm_L; HR_L ← smr_L`。席位规则不变(msharpe, LOOK=900, 负归零, LEGS 掩码)。
若该构造在实施中被发现需要任何 i 之后的信息, 或超出 ~2 小时, **ARM-SB 报 NOT_RUN 并写明原因**, 不即兴改定义。

## §3 GATE P(先于一切)
- **P1**: 判决装置(不改), A0 环境, 两种子, 在 `env -i` 显式白名单下运行, 输出 `d30_n2_c42_rec` / `d30_n2_c42_W` 必须与归档 `A0_PWR230k_s{42,2027}.npz` 的 `rec`/`W` **逐位相等**(shape 同, NaN 模式同, maxabs 0.0)。任一失败 ⇒ **STOP, 只报 GATE P**。
- **P2**: 派生装置, `R15_INSTR=1`, 其余 R15_* 未设, A0 环境 ⇒ rec/W 与 P1 逐位相等(证明仪表不改主路径)。
- **P3**: 派生装置 `FTPOS=1` vs 判决装置 `FTPOS=1`; 派生装置 `SEATNET=1` vs 判决装置 `SEATNET=1`; 两种子 ⇒ 逐位相等(证明 null 注入点在默认值下无扰动)。
P2/P3 失败 ⇒ 派生装置的全部产出(机制门、null、ARM-SB)作废, 只报判决装置臂。

## §4 机制门(ARM-F, 先于任何 P&L 读数)
用派生装置 `R15_INSTR=1` 的逐锚仪表(标记掩码 flagK/flagF = 各链 pre-trim z<0 ∧ rn8≤FTRIM_TH; deep = rn8≤FTRIM_TH; kill = FTPOS 置零集; smr = 执行器权重; c4 = fnow·4/iv):
- **A0(FTPOS=0)在 W_ALPHA 上**: (a) 双链皆被标记(flagK∧flagF)的名数/锚; (b) 其中 smr<0 的比例(**主读**); (c) 这些漏出空头的 gross 占比 Σ|smr|/gross_total; (d) 它们付的 carry Σ smr·c4·1e4/gross_total(bps/锚/单位 gross, 正 = 付)。另报「任一链被标记」与「deep ∧ smr<0(= FTPOS 会杀的集合)」两个变体, 及 2026 年子窗(最接近实盘窗的 regime)。
- **门**: A0 的 (b) ≥ 25% 且 (d) ≥ 0.05 bps ⇒ 回放确有此漏, 继续; 否则 **STOP**(机制主张对回放不成立), 只报门。与实盘 68% / 0.2867 bps 的形状比较为**描述性**(窗口不同)。
- **ARM-F(FTPOS=1)**: 双链被标记且 smr<0 的名数在 W_ALPHA 上必须 **恰为 0**(deep ∧ smr<0 亦为 0); 否则 FTPOS 不是持仓零, 报 FAIL。

## §5 窗口(★ 不混用)
- `W_ALPHA` = 丢前 900 锚 ∩ ts ≤ 2026-08-30 20Z ⇒ **n=9138**(断言)。一切 mean/CI/Sharpe/换手/腿/分解 只用它。
- `W_TAIL` = ts ≤ 2026-08-30 20Z, 不丢暖机 ⇒ **n=10038**(断言)。一切 maxDD/最差日/HALT 只用它。
- `KING_LIVE` = ts ≥ 2024-01-01 00Z, 与上两窗各自求交(W_ALPHA∩ n=5838 断言)。每个 headline 另报一遍。

## §6 统计量(冻结)
- `g = net_ex/gross_total`(bps/锚/单位 gross); 恒等式 `net_ex = pnl_ex − carry_ex − cost_ex` 逐锚断言(atol 1e-9; carry 为**付出**)。
- **主统计量**: 配对 `Δg = mean_{W_ALPHA}(g_arm − g_A0)`(同种子配对)。CI95 / CI99-K: UTC 日块自举 2000 次, 每次抽日有放回, 统计量 = Σ_日 Σ_锚 d / Σ_日 n_锚(与 r12 同式)。**自举分辨率 0.23 bps/锚: 点估计低于它不是结果。**
- 分解: `Δpnl, Δcarry, Δcost`(各 /gt, W_ALPHA 均值)与 Δg 相加核对。ARM-F 的问题 = 省下的 carry 是否 > 放弃的价格 alpha + 出场成本。
- 换手: **只报匹配口径** `turnover/gross_total`(A0 = 0.0540270, 断言); 同时印 RAW 0.03032 与二者之比 1.78189(逐锚比的均值), 使读者无法误用。Δτ = 匹配口径均值之差, 相对 A0 的百分比。
- 成本存活: λ ∈ {1.0, 0.8096, 0.2545}: `g_λ = (pnl_ex − carry_ex − λ·cost_ex)/gt`; 报每臂 g_λ、Δg_λ、`survival(λ) = 1 − λ·mean(cost/gt)/mean((pnl−carry)/gt)`; 说明哪些臂的 Δg **符号**随 λ 变。**λ=1.0 是唯一的判决数; λ<1 只作报告, 不作裁定**(第十四轮: 便宜的成交价与 45.48% 的成交率是同一选择的两半, 不重定价)。
- Sharpe: 每臂 W_ALPHA 上 mean/sd·√2190 与 SE。
- 逐年表(2022..2026)每臂 g 均值(负年显式)。

## §7 席位路径(ARM-S / ARM-SB)
- `w3_king / w3_fund` 在 W_ALPHA 上的均值、分位(p10/p50/p90)、逐年均值, 与 A0 对照; `P(w3_king ≥ 0.85)`; 席位移动量 `mean|Δw3_king|`。回答: 是否如 09-05 所称推向 king ≈0.90。
- 按 **σ_fund 三分位**(SIGF, r12 原语, 切点在 A0 s42 W_ALPHA 上, 断言与 r12 收据的切点相等)报 Δg 与 CI95(09-05 高档读 −0.78)。
- **腿层 vs 书层 carry 比**(v4 实测): 派生装置在 legs() 内对每腿记录 SEATNET 会减去的量 `legs_carry_L = Σ z/g·fnow·4/iv·1e4`(bps/锚/单位 gross, 不论 SEATNET 是否开)。报 fund 腿 W_ALPHA 均值 vs A0 执行书 `carry_ex/gt` 均值及其比(09-05 称 2.2×: 1.96 vs 0.88)。
- 若 ARM-S 的 Δg 在 v4 上**变号**(相对 09-05 的 −0.37)⇒ 09-05 的 REJECT 是口径伪影; 若不变号 ⇒ 在正确口径上关闭。

## §8 NULL(逐锚置换 placebo 有缺陷, 不用; 用 `r3_attack_RESID_SHARPE/null.py` 两族)
### ARM-F
- 被随机化的量 = **FTPOS kill 条件里的 rn8 矩阵**(面板行 × 829, = 装置 L86 的 `_RN8`)。分数层 FTRIM pre-zero(A0 也有)保持真实 rn8 不动。
- **RELAB_d**(主, 信息性): 固定符号置换 `pi = default_rng([4242, d]).permutation(829)`, d=1..3, `KILL = _RN8[:, pi]`。
- **SHIFT_k**(弱, 持久量下 17 日移位仍得 76.5%): `KILL[k:] = _RN8[:-k]`, 前 k 行 0(不 kill), k ∈ {101, 503, 1009}。
- **剂量匹配**: 剂量 = null 的 kill 阈 `R15_KILL_TH ∈ [−0.0100, 0.0]`(连续, 仅 null 用); 目标 = ARM-F 的 **边际匹配换手** `Δτ_arm = mean_WA(τ/gt)_arm − mean_WA(τ/gt)_A0`; 二分至 `|Δτ_null − Δτ_arm| ≤ 1%·|Δτ_arm|`, 最多 13 次; 不收敛 ⇒ 报最接近者并标 UNMATCHED。同时报**发火数**(W_ALPHA 上 kill 名数合计)与相对误差。
### ARM-S
- 被随机化的量 = **SEATNET 减项里的 4h carry 矩阵** `C4 = nan_to_num(FN)·(4/IVf)`(= L169 的量)。RELAB_d: `C4[:, pi]`; SHIFT_k: 行移位, 前 k 行 0。
- 剂量 = `R15_SEATC_SCALE ∈ [0, 8]`(乘在被减的 carry 上); 目标 = ARM-S 的 Δτ_arm; 二分规则同上。「发火」= `mean_WA|w3_king,null − w3_king,A0|` 对照臂的同量。
### 读法
两种子都跑 null。臂「胜过 null」当且仅当 Δg_arm > max_d Δg_RELAB_d(同种子)。SHIFT 只报不判。null 只有 3 个, 报秩与 z 分, 不过度解读。ARM-SB 与 ARM-F05/F20 不跑 null(敏感性臂与代理臂, K 内已计)。

## §9 分 regime(复用 r12 的 34 格, 同定义同切点)
- 用 `r12_regime_table.py` 的格定义与 A0 s42 W_ALPHA 上的切点(BRD6/XSV30/MV30/SIGF 三分位, FMED d1, SPAY d10; 断言与 `RECEIPT_r12_regime_table.json` 的 `cuts` 相等, atol 1e-9); SPAY 与 DEEPNEG_SHORT 用 **A0 的**书态定义, 两臂看同一批锚。
- 每格每臂: n, Sharpe(与 A0 对照), 格内配对 Δg 与 CI95(格内日块自举)。**主读**: 点估计 Sharpe > 3.0 的格数 与 CI95 下界 > 3.0 的格数, **改前/改后**(r12: 2/34 与 0/34)。描述性, 不据此录取; 标出 Δg CI95 不含 0 的格。

## §10 尾部(W_TAIL, 2.0× NAV)
每臂与 A0: 锚复利权益(prepend 1.0, E-0909-C)maxDD; 日收益 `Π(1+2g·1e-4)−1`; 最差日与日期; HALT(≤ −4.00%)与 ALERT(≤ −2.68%)次数; 日 sd。另在 KING_LIVE∩W_TAIL 上报一遍。

## §11 读法(冻结; 全部在两种子上)
- **ADMIT**: 两种子 Δg 的 CI99-K 下界 > 0 **且** 两种子 Δg ≥ +0.23 **且** Δτ ≤ +15%(相对 A0)**且** W_TAIL maxDD_arm ≤ 1.10·maxDD_A0 且 HALT_arm ≤ HALT_A0 **且** 两种子皆胜过全部 RELAB null(ARM-F/S)**且** Δg 符号在三个 λ 下不变。
- **REJECT**: 任一种子 Δg 的 CI99-K 上界 < 0, 或 Δτ > +25%。
- **UNDECIDED**: 其余。
- **NOT_DEPLOYABLE(附注, 不替代上三者)**: 生产 FTRIM 是分数层(combo_stage.py), 位置层 FTRIM 与任何席位规则改动都是**书行为改动**, 需要预注册 + 用户裁定; 本轮**只测量**, 不提议部署, 不写生产 diff。
- 每个声明的臂都报, 包括失败/未跑的。

## §12 ENV 白名单(E-0826-D)
- pod2 装置运行: 由驱动器以**精确 env 字典**(不继承)启动 = `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3` ∪ §1 的 A0 旋钮 ∪ 该臂旋钮 ∪ `OUT_TAG`; 每次运行的完整 env 字典与白名单**逐项**写入收据(非空列表)。
- pod2 判官/机制门/null 驱动: `env -i PATH=... HOME=/root /workspace/venv/bin/python <device> <whitelist>`; 装置断言 `os.environ` 键集 == 白名单, 且无 `CAL* JUDGE* UPLIFT* PANEL* LOOK* WRULE* LEGS* PHI* FSEED* W3FIX* FTRIM* UMASK* SLOW* FPRED* MEMBERS_TOPN* COSTB* SLEEVE* KMOD* SEAT* RNSM* LTRIM* CDAMP* FUNDSCALE* FEMAT* TRADE_TOPN* REF_SKIP* PYTHON* OMP* MKL*`(判官不读任何口径旗标, 口径只从工件 config_json 读)。
- 每份收据: `self_sha256`, `prereg_sha256`(断言), `env_whitelist`(非空), 输入 realpath + sha16, `gpu_before/after`(期望 `0 %, 2 MiB`), 受保护 PID 333197/339489 状态(期望 T, 不触碰)。

## §13 实盘零接触
`~/dl_quant_live` / `~/wide_shadow` 只读(本轮只读过 `combo_stage.py` L60-100/L220-262 与 `shadow_loop_v3.py` 席位段, 未写、未重启、未下单、未调任何交易端点)。pod2 只 CPU; 不 SIGCONT 任何进程; 负载 > 6 时等待。

## §14 数字标签
§1 的 sha、§1.1 的 3300/1110/5838、§5 的 n 均为本轮 pod2 实测 **VERIFIED**; §0 引用的实盘 68%/0.2867/1.577% 与 09-05 的 −0.37/−0.78/0.90/2.2× 为组长简报与既有文档转述 ⇒ 对本轮 **INFERRED**(本轮在 v4 上重测其中可重测者)。
