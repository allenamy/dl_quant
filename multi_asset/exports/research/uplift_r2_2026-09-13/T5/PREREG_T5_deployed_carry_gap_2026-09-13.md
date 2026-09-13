> **创建:** 2026-09-13 ~07:00Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5) | **状态:** 预注册; 冻结先于任何 T5 数字(sha 与冻结时刻记 `receipts/PREREG_FREEZE_sha.txt`, 每个装置运行前断言) | **作废条件:** 部署书存档(`~/wide_shadow/state/target_live`、`target_combo`、`fea171/state_H_{kc,fc,f10}_*`、`state/weights`)被改写; T1 回放臂 `C0_s42 / C0_s2027` 被替换; x0910 元/面板被更新
> **上游:** `../PROGRAM_uplift_r2_2026-09-13.md` AMENDMENT 3(T5 定义); `../T1/RESULT_T1_edge_diagnosis_2026-09-13.md` §15(2.218 vs 1.013 的来源); `../../uplift_2026-09-11/RESULT_r6_judge1_replay_vs_realized_2026-09-11.md` §1.3(差异全在哪些名拿到权重); `../../uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md`(A0 装置, GATE P)

# PREREG · T5 · 部署书为什么比回放书多付一倍 carry

## §0 地位
- **会计分解, 不是因果宣称。** 每个分量都是「把某个构造成分从回放书换成部署书时, 同锚建模 carry 变多少」, 分量之和逐锚闭合到部署−回放 carry 差。
- 可对齐的只有 5 个 UTC 日: **所有 CI 都是描述性的**(5 个日块自举, 不作检验)。
- 实盘零接触: `~/dl_quant_live`、`~/wide_shadow` 只读; 所需文件已拷到 `T5/private/`(gitignored, 清单 `private/COPY_SHA256.txt`); 无任何交易所/Telegram/网络 API 调用。

## §1 写本文之前已经读过或看过的(申报)
- **代码事实(无结果数字)**: A0 回放旋钮(`r18_drive.py` A0(): LEGS=101, PHI=0.45, msharpe LOOK 900, MEMBERS_TOPN 829, FTRIM=zero TH −0.0010, UMASK_SCOPE=m1, CAL=log, SLOW_NPY=`SLOW_v3_on_v4axis.npy`, FPRED=`f10_A0_s{seed}.npy`, COSTB); T1 派生装置 `w10_sleeve_t1.py`(sha `0a811439…00e3`)全部链条语句; 生产者 `shadow_loop_v3.py.pre_m1_20260904_backup` 与 `combo_stage.py.pre_ftrim_20260902_backup` 全文, 以及它们与当前版本的 diff。
- **按文件 mtime(UTC)定的窗内部署版本**: combo 写者首次写 target_live = 2026-08-26 04:21Z; `combo_stage.py` 加入 FTRIM 的版本 mtime 2026-09-02 08:59Z; `shadow_loop_v3.py` M1(fund 秩基扩到场所基)mtime 2026-09-04 00:53Z; V2MAIN 服务模型 `f10_live_s42_np.npz` 更换 mtime 2026-09-01 08:42Z; 窗内全部 target_live 的 booster_sha = `29ffaf58`; 8 月 bundle 备份 config 的 params / symbols_panel / symbols_live / keep_idx 与当前逐字相同。
- **逐锚元数据(无 carry 数)**: 08-26 00Z 的 target_live 由 `shadow_loop_v3` 写(king 形态; combo 只是干跑, 状态 warmstart); 08-29 20Z 无任何部署文件; 08-30 00Z 由 `shadow_loop_v3` 写(king 形态); 08-30 04Z combo 恢复, kc/fc 状态来源 = warmstart; 其余窗内锚 = combo 且状态来源 own; 窗内 target_combo 无 `ftrim` 键。
- **结果类数字(已看过)**: T1 RESULT 全文与 `TABLES_T1_ADDENDUM1.md` 全部(含 30 锚回放 carry 1.0127/1.0187、D2 29 锚 2.218、比 0.457–0.459、A30 逐锚 D2/账本 carry 行、同状态分位、E1/E2a 拆分、逐日价格); r6 JUDGE-1 全文; r18 RESULT §0–§7。
- **偶然看到的部署元数据数字**: `combo_live.log` 中 08-26 04Z/08Z/12Z/16Z 的 w3m = [0.238, 0, 0.762] / [0.2357, 0, 0.7643] / [0.2393, 0, 0.7607] / [0.2346, 0, 0.7654], 09-12..09-13 的 w3m 与 gross; `target_combo/1787716800.json` 摘要(gross 0.8671, kc_gross 0.861558, fc_gross 0.877443, rho_kc_fc 0.9925); `shadow_log.jsonl` 末尾 09-13 三锚的 king 形态书 carry_bps 1.097–1.196 与 w3 ≈ [0.33, 0.10, 0.56]。
- **没有看过**: 窗内回放席位 w3_R; 任何 T5 分量、任何按名/按腿/按费率档的 carry。

## §2 两本书与锚集
### §2.1 回放书 R
T1 臂 `C0_s42`(主)与 `C0_s2027`(复验)= A0(r18 GATE P 与存档 A0 逐位相同; T1 GATE P 与 r18 逐位相同)。书 = 执行器口径 `smr`(混合书 0.55·king 链 + 0.45·F10 链, 非零集去均值并恢复 L1)。种子只作用于 F10(V2MAIN)walk-forward 预测。

### §2.2 部署书 D
`target_live/<A>.json` 的 `weights`(combo_stage 写入的 `combo_raw` = 0.55·sm_kc + 0.45·sm_fc, **未 reshape**; 与 T1 D2 同一向量)。窗内生产者: `shadow_loop_v3` pre-M1(fund z 在 400 成员内求秩)+ `combo_stage` pre-FTRIM(**无 FTRIM**), booster 29ffaf58, V2MAIN 8 月模型文件。

### §2.3 主锚集 A_T5(27 锚)
条件(全部满足): (i) target_live 存在且 `producer` 含 `combo_stage`; (ii) `target_combo/<A>.json`、`state_H_kc_<A>.npz`、`state_H_fc_<A>.npz` 存在; (iii) 两个回放臂在该锚有 rec 行; (iv) x0910 面板有该锚行。
| UTC 日 | 锚 | epoch |
|---|---|---|
| 08-26 | 04Z 08Z 12Z 16Z 20Z | 1787716800 … 1787774400 |
| 08-27 | 00Z 04Z 08Z 12Z 16Z 20Z | 1787788800 … 1787860800 |
| 08-28 | 00Z 04Z 08Z 12Z 16Z 20Z | 1787875200 … 1787947200 |
| 08-29 | 00Z 04Z 08Z 12Z 16Z | 1787961600 … 1788019200 |
| 08-30 | 04Z 08Z 12Z 16Z 20Z | 1788062400 … 1788120000 |
**排除**: 08-26 00Z(部署 = king 形态)、08-29 20Z(无部署文件)、08-30 00Z(部署 = king 形态)。这两个 king 形态锚的 Δ 另表描述性列出, 不进分解。回放在 08-30 20Z 之后 F10 腿无预测(E-0911-B), 故窗止于 08-30 20Z。

### §2.4 复现集(只用于门 G-T1)
A30 = 08-26 00Z..08-30 20Z(T1 回放 30 锚); A29 = A30 去掉 08-29 20Z(T1 D2 29 锚, 含两个 king 形态锚)。

### §2.5 模拟日历
状态从 08-25 20Z 进入, 模拟 08-26 00Z..08-30 20Z 共 30 锚(回放日历); 分量只在 A_T5 上取值。

## §3 carry 定义(与 T1 相同)
- 名级费率: `c_n(A) = nan_to_num(f_fund_now[j(A), n]) × 4 / IVf × 1e4`, `IVf = f_fund_iv` 若有限且 > 0 否则 8; 面板 = `wide_panel_4h_v2ext_x0910.npz` 行 j(A)(门 G-PANEL 断言与主面板窗内逐位相同)。单位 bps / 4h 锚 / 单位权重; **正 = 付**(多头付正费率, 空头付负费率)。
- 书级: `C(w; A) = Σ_n w_n c_n / Σ_n |w_n|`(bps / 4h 锚 / 单位 gross)。
- `C_D(A)` = C(target_live 权重)。`C_R^full(A)` = C(smr, 全 829 名分子)。`C_R^T1(A)` = 装置 `carry_ex / gross_total`(`rec[:,20]/rec[:,5]`, 分子只含当前成员 m)。
- 8h 当量现费率: `rn8_n(A) = f_fund_now × 8 / IVf`(NaN = 无报价)。费率档: ≤−30bp, (−30,−10], (−10,0), [0,10), [10,30), ≥30bp, 无报价(同 r15 SLEEVE)。

## §4 分解(全部逐锚闭合, |残差| ≤ 1e-6 bps)
**恒等式**: `Δ(A) = C_D(A) − C_R^T1(A) = G0(A) + Σ_g φ_g(A) + REM(A)`。
- `G0 = C_R^T1 − C_R^full`(口径分量: 装置 carry 分子不含「已离开成员集但仍持仓」的名)。

### §4.1 L-N 名集透镜(任务 b、c)
单位 gross 权重 w̃ = w/Σ|w|。每名恰属一格: 只在 D(w_R = 0 ≠ w_D)多/空; 只在 R 多/空; 共同名同号多; 共同名同号空; 共同名异号。格贡献: 只在 D = Σ w̃_D c; 只在 R = −Σ w̃_R c; 共同 = Σ (w̃_D − w̃_R) c。加 G0 一格, 闭合到 Δ。另报共同名的 `Σ(w̃_D − w̃_R)c` 前 20 名。

### §4.2 L-S 方向 × 费率档透镜(目标检查用)
每本书按**自己的**权重符号与 rn8 档把 carry 分到 14 格(2 方向 × 7 档); 格 Δ = C_D(格) − C_R^full(格); 加 G0 闭合到 Δ。

### §4.3 L-C 链与腿透镜(任务 a)
- R: 用模拟器(与装置逐步同构, T1 腿账法)拆成 K-king、K-rev24、K-fund、F-f10、F-rev24、F-fund 六格(经 reshape 线性分摊), 腿态起点 = 装置 08-25 20Z 的逐腿态(HL / HFL)。
- D: **只能拆到链**: 0.55·sm_kc 与 0.45·sm_fc(存档精确)。链内腿拆分需要逐锚 king / V2MAIN 分数, 生产者不存档(aux.json 的 prev_rec 每锚覆盖; 仅 09-04 00Z 快照留存), **记「不可测」**。
- 另报: 两本书的席位(R: w3_R 逐锚; D: w3m 逐锚)与桥节点 B_N(见 §4.4, D 规则 + R 分数)的六格 + 「继承态」格拆分(标注为代理, 不是部署书本身)。

### §4.4 L-B 构造桥(任务 d、e)
在回放机制里逐组把成分从 R 换成 D; 节点 S ⊆ G 的书 = 链条按 S 中各组取 D 版、其余取 R 版运行 30 锚后在 A 上的书; `v(S)(A) = C(该书; A)`(全 829 名分子)。`v(∅) = C_R^full`(门 G-SIM-R)。
| 组 | R 版(A0 回放) | D 版(部署, 窗内) | D 来源 |
|---|---|---|---|
| **T** FTRIM | 两链 pre-z: z<0 ∧ rn8 ≤ −10bp ⇒ z=0(rn8 取面板, NaN→0) | 无 | pre_ftrim 版 combo_stage |
| **W** 席位 | w3_R(A)(回放 legs() 序列 msharpe 900, LEGS=101) | w3m(A) = target_combo `w3_masked` | target_combo |
| **B** fund 秩基 | 面板行全部有限 fund 值(829 基)求秩后取成员 | 只在当前成员集内求秩 | pre-M1 `shadow_loop_v3` L441 |
| **V** fund 值与新鲜度 | 面板 `f_fund_ema_v1[j(A)]` | 生产者 EMA acc(由 `aux_pre_m1_20260904.json` 的 ema 与 ledger_tail 逆推到 A), 仅 live 450 名且末次结算 ≤ 12h, 否则 NaN | aux 快照 |
| **M** 成员集 | m_R(A) = meta 成员 ∩ UMASK m1 行 | pm(A) = `weights/<A>.npz` members(400) | weights |
| **X** 出场规则 | 强平 = 成员 ∧ 非 sel | 强平 = 非(LIVE450 ∧ 成员 ∧ sel), 含已离开成员集的持仓 | `combo_stage.chain()` |
| **S** 可交易门 | 前向 y4 有限 ∧ qv4h(meta qvk) ≥ 2.5e5 | qv4h(生产者滚动缓存通道 3 的 2016 根均值) ≥ 2.5e5 | `rolling.npz` 副本 |
| **P** 止损层 | 回放实现路径的 d30_n2_c42 封锁掩码(外生) | 无 | — |
| **H** 状态路径 | 回放自身 H_K / H_F, 自 08-25 20Z 连续 | 08-26 00Z 暖启动 kc ← `weights/<08-25 20Z>`(float32), fc ← `state_H_f10_<08-25 20Z>`; 08-30 04Z 再暖启动 kc ← `weights/<08-30 00Z>`, fc ← `state_H_f10_<08-30 00Z>`; 08-29 20Z 与 08-30 00Z 不推进 | target_combo 状态来源字段 |
| **Z** 执行口径 | smr(reshape) | 不 reshape(combo_raw) | combo_stage 写 target_live 的向量 |
| **K** king 分数(条件纳入) | xz(SLOW_v3_on_v4axis[i, 成员]) | T4 服务值(29ffaf58, 第 80 列 = v1) | T4 |
- **约定 C1**: 在非 combo 锚(08-29 20Z、08-30 00Z)上所有 D 组退回 R 版; H=D 时这两锚不推进状态、08-30 04Z 重置。
- **约定 C2**: 分数一律在当前成员集内重新求秩(`xz(SLOW[i, M])`、`xz(F10P[i, M])`); V2MAIN 分数在所有节点都取 R(无部署存档)。
- **约定 C3**: P=R 时封锁掩码按回放实现路径外生给定, 不在桥节点重算止损深度。
- **约定 C4**: 链条语句顺序与回放装置逐字相同(去均值 → L1 → cap 2.5/nsel → L1 → [king 链: 止损封锁目标] → EMA α 0.1 → 带 2.5e-4 → 强平 → [F10 链: 止损封锁持仓]); D 机制差异只经上表各组进入。
- **约定 C5**: 某节点某锚 sel < 80 或 g < 1e-9 时与装置同样跳过该锚(不更新状态), 计数报告。
- **K 组纳入规则(先写死)**: 主运行时, 若 T4 目录下存在窗内 30 锚逐名的 king 预测(v1 服务值与 v0 反事实)且 T4 自报的实盘 king 平价门 PASS, 则 G = {T,W,B,V,M,X,S,P,H,Z,K}; 否则 G = {T,W,B,V,M,X,S,P,H,Z}, **(e) 记 NOT MEASURED**。主运行之后才出现的 T4 数组只作 ADDENDUM, 主表不改。
- **主读数 = Shapley 值**: `φ_g(A) = Σ_{S⊆G∖{g}} |S|!(|G|−|S|−1)!/|G|! · [v(S∪{g})(A) − v(S)(A)]`, 满足 `Σ_g φ_g = v(G) − v(∅)`。
- **次读数**: 固定顺序 T → B → W → V → M → S → X → P → H → Z →(K)的逐步差; 单组效应 `v({g}) − v(∅)` 与留一效应 `v(G) − v(G∖{g})`(描述, 用于看交互)。
- **REM = C_D − v(G)**: 桥节点 B_N = v(G) 的书(全部可测组取 D, V2MAIN 分数与未纳入的 king 分数取 R)与部署书之差, 含分数差与任何未对上的构造差。另报 B_N 与 D 的单位 gross 权重 L1 距离与相关系数。
- **诊断(描述)**: 节点 N′ = D 规则 + R 分数 + 每锚进入态直接取部署存档态(kc/fc 状态文件 A−4h), 把 REM 拆成「当锚流量」C_D − v(N′) 与「携带态」v(N′) − v(G)。
- **H2b(任务 e)**: 若 K 纳入, 报 `H2b(A) = v(G) − v(G; king = D_v0)` 与 `v({K}) − v({K}; king = D_v0)` 两个节点上的值及其占 Δ 的比例; 否则 NOT MEASURED。

## §5 目标检查(先写死)
- **TC1 高 carry 是否在部署书对深负费率名的空头上**: L-S 透镜中「空头 ∧ rn8 ≤ −10bp」两格(≤−30 与 (−30,−10])合计的 Δ 占比。读法: 两个种子都 ≥ 0.5 ⇒ **YES**; 都 ≤ 0.2 ⇒ **NO**; 其余 **PARTIAL**。并列报 D 书自身 carry 中该队列的占比与 R 书中该队列的占比。
- **TC2 是否与九月初空头价格亏损是同一批名**:
  - 八月队列 C_Aug = {n : 存在 A ∈ A_T5, w_D,n(A) < 0 ∧ rn8_n(A) ≤ −10bp}; 每名八月 carry = Σ_{满足条件的 A} w̃_D,n c_n。
  - 亏损窗 E2a = 有 target_live 文件的锚 2026-08-31 00Z..2026-09-10 00Z(T1 事后拆分同窗, 不分生产者)。每名空头价格 `L_n = Σ_{A∈E2a, w_D,n(A)<0} w̃_D,n(A) · y4_n(A) · 1e4`(x0910 记账元 y4, NaN 记 0; bps/单位 gross, 跨锚求和)。
  - `M1 = Σ_{n∈C_Aug, L_n<0} L_n / Σ_{n: L_n<0} L_n`; `M2` = 同式只取 UTC 日 09-06 的锚; `M3 = Σ_{n∈C_Aug, L_n<0} 八月carry_n / Σ_{n∈C_Aug} 八月carry_n`。
  - 读法: M1 ≥ 0.5 ⇒ **SAME NAMES**; M1 ≤ 0.2 ⇒ **DIFFERENT NAMES**; 其余 **PARTIAL**。并列: 空头亏损前 15 名及其是否属 C_Aug、八月 carry、E2a 内是否仍为空头 ∧ rn8 ≤ −10bp 的锚数。
  - 注: T1 附录的「空头 −8.7」是 2026-08 书层 fund 腿空头侧**价格/carry 比**(S3), 不是 bps 价格; T5 不复用该数。
- TC 只依赖 D, 与种子无关(TC1 的 R 侧除外)。

## §6 门(不过者按列出的后果处理)
| 门 | 规则 | 不过的后果 |
|---|---|---|
| G-FREEZE | 每个装置断言本文 sha | 不运行 |
| G-ENV | env 白名单(pod2 {PATH, HOME, LC_CTYPE}; Mac 由 argv 给出)逐项断言 | 不运行 |
| G-POD | pod2 前后 `nvidia-smi` 0 % / 2 MiB; PID 333197/339489 状态记录且不触碰 | GPU 忙则排队 |
| G-P | T5 派生装置(T1_INSTR=1, T5_DUMP=1)的 d30_n2_c42 {rec, W, T1AGG, T1ID, T1SMR, T1TRR, T1YV, T1C4, T1RN, T1RATE, T1MEM} 与 S0 {rec, W} 与 T1 臂逐位相同; 自报 sha = 派生 sha | 不报任何分量 |
| G-T1 | (i) R 在 A30 的 carry 均值与 T1 收据 carry_A30 相差 ≤ 1e-9; (ii) D 在 A29 的逐锚 carry 与 `T1_d2.npz`(08-26 00Z 行取附录收据)相差 ≤ 1e-9, 均值 2.218 同 | 停下对账 |
| G-PANEL | x0910 面板与主面板在 30 个窗内行、829 名上 f_fund_now 与 f_fund_iv 逐位(NaN 同位)相同 | 停下对账 |
| G-SIM-R | 模拟器全 R 节点: sm_K、sm_F、smr 与装置 dump 在 30 锚、两种子 max\|Δ\| ≤ 1e-12; T1 口径 carry 与 `rec[:,20]/rec[:,5]` 相差 ≤ 1e-9 | 不报 L-B、L-C |
| G-ARCH-D | A_T5 上 target_live 权重 = 0.55·state_H_kc + 0.45·state_H_fc(float64), 逐名 ≤ 1e-9; own 锚的状态文件锚字段连续 | D 的链拆分不报(L-N、L-S 仍用 target_live) |
| G-LEG | R 与 B_N 的逐腿分量逐名之和 = 书, ≤ 1e-12 | L-C 不报 |
| G-CLOSE | 每个透镜逐锚 \|Δ − Σ 分量\| ≤ 1e-6 | 不报该透镜 |
| G-ING-V(不阻断) | 逆推 EMA 方法从 09-13 快照推回 09-04 00Z, 在 09-04 00Z 400 成员上复现快照存的 legz["fund"], max\|Δz\| ≤ 1e-9 | V、B 两组标「重建未验证」, 照算 |
| G-ING-S(不阻断) | 每个 A: 存档 king 形态书(weights)非零名 ⊆ pm ∩ sel_D ∩ LIVE(违例计数); \|sel_D\| 与 shadow_log `signal.sel` 相同 | S 组标「重建未验证」, 照算 |

## §7 统计
- 所有分量在 A_T5 上等权取锚均值。占比 = 分量均值 / Δ 均值。
- UTC 日块自举: 5 个日块(08-26/27/28/29/30), 2000 次, `np.random.default_rng([20260905, k])`, 百分位 CI95; 比值用「重抽的日内求和之比」。k: 57 标题行(Δ 均值与比值), 51 Shapley, 52 顺序桥, 53 L-N, 54 L-S, 55 L-C, 56 TC1。两个种子用同一 k。
- 表头一律标注「5 日块, 描述性」。

## §8 读法(先写死)
- **R1 标题**: A_T5 上 C_D、C_R^T1、Δ、C_D/C_R^T1; 另报 A29/A30 复现与两个 king 形态锚。
- **R2 最大分量** = C0_s42 Shapley 下 {G0, φ_g, REM} 中 |均值占比| 最大者; **稳健** ⇔ C0_s2027 Shapley 与两个种子的顺序桥给出同一组。
- **R3** |REM 占比| ≤ 0.25(两种子)⇒「构造成分解释」; ≥ 0.5 ⇒「分数驱动」; 其余「混合」。
- **R4 可工程修复性(预先分类)**: T FTRIM、B 秩基 —— 生产已于 09-02 / 09-04 改为与回放同形(**可修, 已部署**); W 席位 —— 实盘席位输入序列与回放不同(可修: 席位输入); V、M、S、X —— 数据管线/宇宙/资格/出场规则(可修); H —— 暖启动暂态(运维, 自愈); P —— 回放独有的止损层(不是生产缺陷); Z、G0 —— 口径(不是书差异); REM —— 模型/特征分数(其中 H2b 可修, 模型差异不算工程缺陷)。
- **R5** 若最大分量可修: 写出预注册修复检验的样子(对照、窗、判据), **不提议部署任何东西**。
- **R6** (e) 按 §4.4 规则给数或 NOT MEASURED。
- **R7** TC1、TC2 按 §5 读。

## §9 装置与顺序
1. Mac `devices/t5_live_ingredients.py`: 从 `private/live/` 构建 D 成分(pm、LIVE、w3m、sel_D、fund EMA acc_D、暖启动态、kc/fc 状态、target_live 权重)与 G-ING-V / G-ING-S → `receipts/T5_live_ingredients.npz` + 收据。
2. `devices/mk_t5_device.py`: 由 T1 装置(sha `0a811439…00e3`)生成 `devices/w10_sleeve_t5.py`, 只加 T5_DUMP 窗内输出(rec/W 不变)。
3. pod2 `devices/t5_drive.py`: 跑 C0_s42 / C0_s2027 → G-P。
4. pod2 `devices/t5_bridge.py`: G-T1、G-PANEL、G-SIM-R、G-ARCH-D、G-LEG、G-CLOSE; 全部透镜、Shapley、顺序桥、自举、TC1/TC2 → `receipts/pod2/RECEIPT_T5_bridge.json` 与逐锚分量 npz。
5. Mac `devices/t5_tables.py`: 由收据渲染 `receipts/TABLES_T5.md`; RESULT 只引用该表。
pod2 只用 CPU, 工作目录 `/workspace/uplift_r2_2026-09-13/T5/`; 不提交。
