> **创建:** 2026-09-13 ~08:05Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5, 任务 T5c) | **状态:** 预注册; 冻结先于任何 T5c 结果数字(sha 与冻结时刻记 `receipts/PREREG_FREEZE_sha.txt`, 每个装置运行前断言) | **作废条件:** 部署书存档(`target_live` / `target_combo` / `state_H_{kc,fc,f10}` / `weights`)被改写; x0910 延展产物或 T1 回放臂被替换; 用户改比较层
> **上游:** `../PROGRAM_uplift_r2_2026-09-13.md` 派工指针 T5c; `../T5/RESULT_T5_deployed_carry_gap_2026-09-13.md`(同一装置族与构造组); `../../uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md` §5/§6(x0910 延展覆盖什么、不覆盖什么)

# PREREG · T5c · 九月同锚: 回放书是否也亏

## §0 问题与地位
- **问题**: 2026-08-31..09-10 部署书空头价格亏损(T5 §6.2: 全部名 −4.53 bps/锚)是策略自身的亏损, 还是部署差异? 在同一批锚上比较「研究规则 + 回放分数」与部署书, 同时分解**价格与 carry**(及成本与净额)。
- **比较层 = 目标文件层**。执行器在 `target_live` 之后另有逐名止损(T5b 在查)与 09-06 的单日止损平仓; 这些都不在本文比较内。**实现账本层的比较不在范围内。**
- 会计分解, 不是因果宣称。约 11 个 UTC 日块 ⇒ **所有 CI 都是描述性的**。

## §1 写本文之前已知的事实(申报; 均无 T5c 结果数字)
**数据覆盖(pod2 实测)**:
- x0910 记账元 `meta_newprod_v4_x0910.npz`(sha `a8eb3597…7245`)轴 10242 锚, 止 2026-09-10 20:00Z; 每锚 y4 有限 798 名直到 09-10 20Z; qvk 829 名全有限。
- 该元的 y4 与 `dlw_v4raw_x0910/data/dlw_targets.npz` 的 `y4s` 在 08-30 00Z..09-10 20Z 的 72 行、57,456 个格上**逐位相等**, NaN 同位; 九月 3 根撞 ±0.3 裁剪线的 bar(AKE 09-02 21:45Z、BULLA 09-05 03:00Z、WOO 09-06 01:35Z)所在格两边相同 ⇒ 记账 y4 = RAW 补丁口径(r6 `r6_RECEIPT_raw_patch.json`), 不是从 ret5 缓存重算。
- x0910 面板 `wide_panel_4h_v2ext_x0910.npz` 止于 **2026-09-10 00:00Z**(面板要 E+288 ≤ TT, r6 §1.2)。
- 宇宙掩码 `umask_UPIT_CRYPTO.npz` 止于 2026-08-31 00:00Z。
- A0 回放 king 数组 `SLOW_v3_on_v4axis.npy`(sha `64767318…9009`, v4 轴 10182 锚)有限到 08-30 20Z, **08-31 00Z..20Z 六锚全 NaN**。
- V2MAIN(F10)月度 walk-forward 折只有 202501..202608(pod2 `/workspace/f8_v4/mwf/RAW_s42/shard*/preds_fold/` 20 个文件, 无 202609); r6 延展树的 `f10_A0_s42.npy`(sha `609b0379…a9f5`)与 `f10_A0_s2027.npy`(sha `2e88ca5e…40`)末个有限锚 2026-08-30 20:00Z(`r6_RECEIPT_dev_tree.json`); `r6/out/f8_v4_x0910/preds/` 为空。
- r6 延展的 king 预测 `SLOW_v4_x0910.npy`(sha `8136f922…575e`)是 **bundle v4 booster `f2365771…`** 的谱系(训练截止 2025-12-31), 不是 A0 所用 8d79186b 谱系。
**部署侧(只读副本, 逐锚元数据)**:
- 08-30 04Z..09-12 20Z 全部锚 `target_live` 由 combo_stage 写, target_combo 与 kc/fc 状态文件齐全; kc/fc 状态来源除 08-30 04Z(warmstart)外全为 own。
- booster: 至 09-01 04Z 为 29ffaf58, 09-01 08Z 起 8d79186b。FTRIM: target_combo 自 **09-02 12Z** 起带 `ftrim` 记录。M1(fund 秩基扩到场所基): shadow_log 自 **09-04 04Z** 起有 base_n / fund_base_n(528→530)。席位播种: w3m 的 king 份额 09-05 12Z 0.188 → **09-05 16Z 0.304**。
- 执行器 09-06 08:46Z 单日止损全书平仓, 信号侧照常产出(记忆 `live_stop_loss_2026_09_06_resume_and_flowday`)。09-12 12:47Z 假阳性全书平仓(E-0912-A)。
**已看过的结果类数字**: T5 全部结果(含 §6.2: 08-31..09-10 部署书空头价格 −4.53 bps/锚、亏损前列名单); T1 RESULT 与附录 1 全部(含 D2 E2a 价格 −5.36、逐日价格如 09-06 −39.3); T4 RESULT §0(NOT MATERIAL); 平价回放 Phase 1 §0–§3; 上表逐锚元数据中的 w3、n_kc、base_n。**没有看过**任何九月回放书的价格、carry、净额, 也没有看过部署 king 链在九月的价格或 carry。

## §2 锚集
- **窗**: 2026-08-31 00:00Z ≤ A ≤ 2026-09-10 00:00Z。终点由数据定: RAW y4 到 09-10 20Z, 但 carry、fund 值与现费率需要 x0910 面板行, 面板止于 09-10 00Z ⇒ 终点 09-10 00Z。候选 61 锚, 11 个 UTC 日块(08-31、09-01 … 09-09 各 6 锚, 09-10 为 1 锚)。
- **逐锚资格**(同 T5 §2.3, 全部满足才入): (i) target_live 由 combo_stage 写; (ii) target_combo、state_H_kc、state_H_fc 存在; (iii) 两个回放种子在该锚有装置行; (iv) x0910 面板有该锚行; (v) x0910 元 y4 在该锚有有限值。
- **09-06(执行器止损日)**: 目标层照常入主分析; 另报去掉 UTC 日 09-06 六锚的敏感性。
- **09-12 12:47Z 平仓**: 在窗外(窗止 09-10 00Z), 无锚受影响; 若用户将来要延窗, 该时刻之后的锚一律排除(部署书为空)。
- **模拟日历**: 状态从 08-30 00Z 进入, 模拟 08-30 04Z..09-10 00Z 共 66 锚; 分量只在窗内锚上取值。

## §3 分数来源(先定, 不看结果)
### §3.1 V2MAIN: **只比 king 链**
窗内不存在任何折外 V2MAIN 分数(§1)。不造、不替代 ⇒ **V2MAIN 臂 NOT MEASURED**。主比较 = 回放 king 链对部署 king 链。
### §3.2 回放 king 分数
- **主 (KA)**: x0910 轴数组 = 锚 ≤ 2026-08-30 20Z 的行逐位拷贝 `SLOW_v3_on_v4axis.npy`; 2026-08-31 00Z..09-10 20Z 的行 = booster **8d79186b**(`/workspace/shadow_bundle_v3/slow2026.txt`, sha `8d79186b…1282`)对 x0910 研究特征 `wide_fea_v4_x0910.npy`(第 80 列 = 存储的 v0)打分, 格规则逐字照 T4 `t4_kings.py`(成员中 y4 有限且 ≥ 50 名、存储 float16 → float32、78 个 keep 列)。8d79186b 只用 2026 年之前的行训练(T4 P5)⇒ 窗内全部锚为样本外。
- **门 G-KC(不阻断, 照报)**: 同一打分在 2026-01-01..08-30 20Z 上对 `SLOW_v3_on_v4axis` 的逐位相等份额、逐锚成员 Spearman 最小值与中位数。A0 的 2026 king 用的是 v2ext 特征文件, 该文件没有九月; 所以窗内是「同一 booster、换成 v4 研究特征」, 这一谱系切换由 G-KC 量化并在结果里标注。
- **敏感性 (KB, 描述)**: 全史回放改用 `SLOW_v4_x0910.npy`(bundle v4 booster 谱系), 只报 king 链读数。

## §4 两本书与结果量
- **回放 king 链 R_K**: A0 装置(T5 派生装置只改窗内 dump 区间)在 x0910 输入上运行, A0 旋钮不变(LEGS 101, PHI 0.45, msharpe 900, MEMBERS_TOPN 829, FTRIM zero −10bp, UMASK m1, CAL log, COSTB), SLOW_NPY = KA, FPRED = r6 延展树的 NaN 延展文件, UMASK = 原掩码 + 08-31 00Z 之后各行沿用末行(新文件, sha 入收据)。R_K = 装置 king 链持仓 `sm`(混合之前)。两个种子 42 / 2027(种子只经止损层的混合书深度影响 king 链)。
- **部署 king 链 D_K**: 存档 `state_H_kc_<A>.npz`。
- **只作描述(不下读法)**: 部署书 D_B = target_live 权重、部署 V2MAIN 链 D_F = state_H_fc; D_B 与 D_K 价格的逐锚相关与均差。
- **结果量**(每锚, bps / 4h 锚 / 该书单位 gross; 分子取全部 829 名):
  - 价格 `P = Σ w·nan_to_num(y4)·1e4 / Σ|w|`, y4 = x0910 记账元(RAW)。
  - carry `C = Σ w·C4·1e4 / Σ|w|`, `C4 = nan_to_num(f_fund_now)·4/IVf`(T1/T5 同式, x0910 面板)。
  - 成本 `K = Σ |w(A) − w(A−1)|·rate / Σ|w(A)|`, rate = `costb_PWR_G230k` 三档按 `qv4h = expm1(clip(qvk, 0, 30))·48`(x0910 元)取; w(A−1) 为同一本书上一模拟锚。
  - 净额 `N = P − C − K`(v4 口径: g = 净额 / gross, RAW y4, 不从 ret5 缓存重算收益)。

## §5 构造桥(king 链; 分量逐锚闭合 ≤ 1e-6)
| 组 | R 版(A0 回放) | D 版(部署) | D 来源 |
|---|---|---|---|
| **T** FTRIM | pre-z: z<0 ∧ 面板 rn8 ≤ −10bp ⇒ z=0 | **09-02 12Z 前无**; 自 09-02 12Z: z<0 ∧ 账本末行费率×8/iv ≤ −10bp ⇒ z=0(缺费率名不排除) | 生产者账本逆推到 A |
| **W** 席位 | 回放 w3(msharpe 900, LEGS 101) | 存档 w3m(含 09-04 席位修正与 **09-05 16Z 播种**) | target_combo |
| **B** fund 秩基 | 面板行全部有限 fund 值(829 基)求秩 | **09-04 04Z 前**: 只在当前成员内求秩; **自 09-04 04Z(M1)**: 在生产者基(基名单中末次结算 ≤ 12h 且有 EMA 的名, 含面板外名)的分布中求秩, 值来自 V 组所选来源(V=R 时只含面板上的基名) | 生产者代码 L100–112、L413–417; aux 快照 |
| **V** fund 值与新鲜度 | 面板 `f_fund_ema_v1` | 生产者 EMA(08-31..09-04 00Z 由 09-04 快照逆推, 09-04 04Z 起由 09-13 快照逆推), live 名且末次结算 ≤ 12h | aux 快照 |
| **M** 成员集 | meta 成员 ∩ 掩码 | `weights/<A>.npz` members | weights |
| **X** 出场 | 成员 ∧ 非 sel | 非(LIVE ∧ 成员 ∧ sel) | combo_stage chain() |
| **S** 可交易门 | 前向 y4 有限 ∧ qv4h(元) ≥ 2.5e5 | qv4h(生产者滚动缓存) ≥ 2.5e5 | rolling.npz 副本 |
| **P** 止损层 | 回放实现路径封锁掩码(外生) | 无 | — |
| **H** 状态路径 | 回放自身 king 链状态, 自 08-30 00Z 连续 | **08-30 04Z 暖启动** kc ← `weights/<08-30 00Z>`(float32), 其后连续 | target_combo 状态来源 |
- 分数(king)不设组, 进 **REM = D_K − v(G)**; REM 按 09-01 08Z(booster 切换)前后分段报告。
- 约定: 分数在当前成员集内重新求秩; 链语句顺序逐字同装置 king 链; sel < 80 或 g < 1e-9 与装置同样跳过并计数; 止损封锁按回放路径外生。
- **主读数 = Shapley**(9 组 512 节点, 对 P、C、K、N 各自计算; Shapley 线性 ⇒ φ_N = φ_P − φ_C − φ_K)。**次读数**: 固定顺序 T → B → W → V → M → S → X → P → H 的逐步差; 单组与留一效应(描述)。
- **分段均值(描述)**: φ_T 以 09-02 12Z、φ_B 以 09-04 04Z、φ_W 以 09-05 16Z、REM 以 09-01 08Z 为界的前后均值。

## §6 读法(先写死; 每个种子各算, 标签要求两个种子一致)
- **SAME-LOSS(价格)** ⇔ 窗内 R_K 价格均值落在 D_K 价格均值的 CI95 内。
- **DEPLOYMENT-GAP(价格)** ⇔ 配对差 mean(P_DK − P_RK) 的 CI95 不含 0。
| SAME-LOSS | DEPLOYMENT-GAP | 标签 |
|---|---|---|
| 是 | 否 | 策略自身的亏损(king 链) |
| 否 | 是 | 部署差异 |
| 是 | 是 | 同向但有差距 |
| 否 | 否 | 不可判 |
- 同一规则另对净额 N 与 carry C 各报一次(次读数)。
- 「回放 king 链也亏价格」⇔ R_K 价格均值 < 0(点估计, 描述)。
- 价格差的**最大分量** = Shapley |占比| 最大者(含 REM); 两个种子与固定顺序一致 ⇒ 稳健。|REM 占比| ≤ 0.25 ⇒「构造成分解释」; ≥ 0.5 ⇒「分数驱动」; 其余「混合」(价格与 carry 分别读)。
- **敏感性(描述)**: (a) 去掉 09-06 六锚重算全部读法; (b) KB 谱系下的 R_K 读法。
- **描述性透镜**: 按各自权重符号的多空价格拆分(D_K、R_K); 窗内 D_K 空头价格亏损前 15 名及其在 R_K 中的权重; 价格差的逐名 Shapley 前列。

## §7 门
| 门 | 规则 | 不过的后果 |
|---|---|---|
| G-FREEZE / G-ENV | 断言本文 sha; env 白名单逐项断言 | 不运行 |
| G-POD | pod2 只用 CPU, `nice`, 并行 ≤ 16 核; 前后 `nvidia-smi` 0 % / 2 MiB; PID 333197/339489 记录且不触碰 | 排队 |
| G-UM | 新掩码 ≤ 08-31 00Z 的行与原文件逐位相等; 之后各行 = 末行 | 不运行回放 |
| G-RAW | 装置内再断言: 窗内 x0910 元 y4 与 dlw y4s 逐位相等 | 停下对账 |
| G-KC(不阻断) | §3.2 | 照报并标注 |
| G-X | KA 两个种子的装置输出在锚 ≤ 08-30 20Z 的行上, rec / W / T1 逐腿数组 / legs 序列与 T1 臂 C0 **逐位相等** | 停下对账(连续性不成立) |
| G-SIM-R | 模拟器全 R 节点: king 链 sm 与逐腿态对装置 dump max\|Δ\| ≤ 1e-12, 66 锚, 两个种子 | 不报桥 |
| G-ARCH-D | 窗内 target_live = 0.55·kc + 0.45·fc ≤ 1e-9; kc 状态文件锚字段连续 | 不报 D_B 描述 |
| G-T1c | D_B 价格与 carry 在 T1 D2 的窗内锚上逐锚复现 `T1_d2.npz`(≤ 1e-9); T5 §6.2 空头价格 −4.5274 复现 | 停下对账 |
| G-CLOSE | 每个结果量的每个分解逐锚闭合 ≤ 1e-6 | 不报该分解 |
| G-ING-V(不阻断) | EMA 逆推方法: 09-13 快照推回 09-04 00Z 复现存储 fund z(T5 已过, 重跑) | V 组标「重建未验证」 |
| G-ING-B(不阻断) | (i) 09-13 04Z 用 aux.json 的 ema 与 base_syms 复现 prev_rec 的 M1 fund z; (ii) 每个 M1 锚重建的 fund_base_n 与 shadow_log 相同 | B 组标「重建未验证」 |
| G-ING-S(不阻断) | 每锚重建 sel 计数 = 日志 sel; 存档 king 形态书非零名 ⊆ pm∩sel∩LIVE | S 组标「重建未验证」 |
| G-ING-T(不阻断) | 自 09-02 12Z 每锚 target_combo `ftrim.names_kc` 所记 rn8 与账本重建值差 ≤ 1e-7 | T 组标「重建未验证」 |

## §8 统计
- 窗内锚等权取均值。UTC 日块自举 2000 次, `np.random.default_rng([20260905, k])`, 百分位 CI95; 比值用重抽日内求和之比。k: 81 标题, 82 价格 Shapley, 83 carry Shapley, 84 净额 Shapley, 85 成本 Shapley, 86 固定顺序, 87 读法配对差, 88 多空透镜。两个种子同 k。表头标注「约 11 个日块, 描述性」。

## §9 装置与顺序
1. Mac `devices/t5c_live_ingredients.py`: D 成分(pm、LIVE、w3m、sel_D、fund EMA、M1 基、账本 rn8、kc/fc/target_live、暖启动态)与 G-ING-*、G-ARCH-D。
2. pod2 `devices/t5c_king_extend.py`: KA 数组与 G-KC。
3. `devices/mk_t5c_device.py`: 由 T5 装置(sha `4c5b972e…5add`)生成 `w10_sleeve_t5c.py`, 只改 dump 区间。pod2 `devices/t5c_drive.py`: G-UM、KA × {42, 2027}、KB × {42, 2027}、G-X。
4. pod2 `devices/t5c_bridge.py`: G-RAW、G-SIM-R、G-T1c、G-CLOSE; 桥、读法、敏感性、透镜 → `receipts/pod2/RECEIPT_T5c_bridge.json`。
5. Mac `devices/t5c_tables.py` → `receipts/TABLES_T5c.md`; RESULT 只引用该表。
- 写入范围: `T5c/` 与 pod2 `/workspace/uplift_r2_2026-09-13/T5c/`; 不写 T4b / T5b / T6 / T7 / `parity_replay_2026-09-12/phase2`; 不提交。
