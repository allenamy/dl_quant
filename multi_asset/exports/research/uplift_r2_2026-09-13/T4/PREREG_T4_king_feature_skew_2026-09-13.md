> **创建:** 2026-09-13 06:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T4) | **状态:** 预注册 — 判据冻结先于任何结果数字(冻结 sha 与时刻见 `receipts/PREREG_FREEZE_sha.txt`; 每个装置运行前断言本文 sha) | **作废条件:** 生产者 `shadow_loop_v3.py`(e9c98374…)或在役 bundle(booster 8d79186b)换代; 研究 king 源 `SLOW_v3_on_v4axis.npy`(64767318…)或 r18 装置(9b8a6323…)被替换
> **纲领:** `../PROGRAM_uplift_r2_2026-09-13.md`(含 AMENDMENT 1/2 与 T2/T3 结果指针) | **上游事实:** `../T1/RESULT_T1_edge_diagnosis_2026-09-13.md` §5 H2b + `../T1/receipts/RECEIPT_T1_h2b_serve.json` + `../T1/receipts/pod2/RECEIPT_T1_h2b_train.json`
> **零接触:** `~/wide_shadow` 与 `~/dl_quant_live` 只读(生产者 venv 只当解释器用); 不调任何 API; pod2 只用 CPU, `nvidia-smi` 前后 0 % / 2 MiB, 不碰 PID 333197/339489; 不提交。

# PREREG · T4 · king 第 80 列训练/服务口径错配的影响

## §0 问题与范围
在役 king LGBM 的第 80 列(`fund_ema`, booster 特征 #76)**训练用 v0**(每次结算原始费率的墙钟 HL3d EMA), **服务用 v1**(`rate×8/iv` 后同式 EMA)。4h 结算名上服务值是训练口径的 2 倍, 1h 名上 8 倍。本文冻结: (A) 如何度量这一错配对 king 分数、king rank-IC 与 combo 书净额的影响; (B) 判为 MATERIAL / NOT MATERIAL 的规则; (C) 实盘窗 41 锚上用生产者平价装置做的单点差异检查。**本文不主张任何修复上线**; 修复是生产者改动, 需用户字。

## §1 写作本文之前已核实的前提(全部是口径/血统事实, 不含任何结果数字)
| # | 事实 | 收据 |
|---|---|---|
| P1 | 服务端: `~/wide_shadow/shadow_loop_v3.py`(sha e9c98374…)L341–349 对 `rn = rate×(8/iv)` 做墙钟 HL3d EMA; L405–412 按 ≤12h 新鲜度取 `fe_v = est["acc"]`、`fn_v = led[-1][1]`(原始费率); **L418** `FE_ANCH[:, 80] = nan_to_num(fe_v[m])`, **L419** `FE_ANCH[:, 81] = nan_to_num(fn_v[m])`。(任务书写的 L417/L418 差一行, 以文件为准) | 代码 |
| P2 | 生产者全部版本同一写法: `shadow_loop.py`(L234 rn / L302 列 80)、`shadow_loop_v2.py`(L278/L346)、`shadow_loop_v3.py.bak_predemeanfix`(L315/L383)、`.pre_m1_20260904_backup`(L321/L389)、现役 v3(L344/L418)、以及研究仓 `wide_live_staging_2026-08-22/shadow/shadow_loop.orig.py`(L234/L302) | grep |
| P3 | 训练端特征构建器全部把面板 `f_fund_ema`(v0)放进第 80 列、`f_fund_now`(原始费率)放进第 81 列: `pod_fea_wide.py` L64、`pod_fea_wide_hist.py` L66、`pod_fea_ext.py` L61(文件头「fund 列语义不变(v0+now)」)。面板 `pod_panel_ext.py` L124–143: `f_fund_ema` = 原始费率墙钟 HL3d, `f_fund_ema_v1` = `rate×8/iv` 同式; L153–162 结算时刻 ≤ 锚、>12h 置 NaN(与服务端新鲜度同) | 代码 |
| P4 | **第 81 列两侧口径相同(原始费率)**: 9-01 训练文件 `wide_fea_v2ext.npy` 第 81 列在 1,195,841 个「原始与归一化 float16 值不同」的成员格上 100% 等于 float16(原始), 0% 等于归一化; 全部 2,722,665 个成员格 100% 等于原始。服务端 L419 为原始费率 ⇒ **不设第 81 列敏感性臂**(任务书条件「若口径不同」不成立); 服务侧另由 §6 GATE C81 用数据复核 | `receipts/RECEIPT_T4_facts_caliber.json` F1 |
| P5 | **两代在役 booster 都是 v0 训练**: LightGBM 的 `feature_infos` 来自建箱抽样(200,000 行, 默认种子)。按导出器规则重建 9-01 训练矩阵、拟合一棵树: 与 8d79186b 的 78 列 `feature_infos` **78/78 逐字相同**; 只把第 80 列换成 v1 则第 76 项不同。08-16 booster 29ffaf58 的训练文件已于 09-01 被覆盖(MANIFEST D1), 用正典八月面板 `wide_panel_4h_v1.npz` 重铸第 80/81 列: v0 版本的第 76、77 项与 29ffaf58 **逐字相同**, v1 版本第 76 项不同; 其余 kline 列 75/76 相同(成员集为近似) | `receipts/RECEIPT_T4_facts_booster_sample.json` |
| P6 | 研究回放的 king 腿 = `/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy`(r18_drive.py L48、L53–55 `SLOW_NPY=K3`), 它由 `build_dev_v4.py` L40–41 把 `shadow_bundle_v3/slow_pred_pinned.npy`(sha 158cd4ac…, = 在役 bundle 同名文件)按 E_ts 对齐到 v4 轴; 后者由 `pod_export_bundle_v3.py` L26–82 在 `wide_fea_v2ext.npy` 上打分: 2024、2025 为按年扩张折(booster 未保存), 2026 为在役 booster 8d79186b。第 80 列 = v0(T1 逐位)。v4 谱系 `SLOW_v4.npy` 同(`wide_fea_v4.npy`, T1 逐位 v0) | 代码 + pod2 sha |
| P7 | 时间线: 影子首锚 2026-08-16 12Z(booster 29ffaf58); 首个 king `target_live` 2026-08-22 04Z(`shadow_loop_v2`); combo 覆写 `target_live` 自 2026-08-26(king 备份 `target_live_king/` 首个 00Z, 在役自 04Z 锚); booster 换为 8d79186b 自 2026-09-01 08Z 锚 | `~/wide_shadow/shadow_log.jsonl` signal/target_live 事件; `state/target_live*/` |
| P8 | 07-25..27 的 as_trained/corrected 裁定管的是执行器 140 名 DL 书: `dl_quant_live/live/factor_version_registry.py` L48–98(「frozen king/s2 heads」= `checkpoints/king_fold4.pt`/`s2_fold4.pt`, 训练面板 `wide_dl_full.npz`)与 `signal/assert_funding_dim.py`。宽书 slow-LGBM king 在 08-15/16 才出现; `~/wide_shadow` 与 `fea171` 的 .py 里对 `as_trained / funding_panel / assert_funding_dim` 零引用 | 代码 + grep |
| P9 | 影子验收 A2(`~/wide_shadow/acceptance.py` L38–168)比对的是 EMA 平滑后的权重, 且每锚把 H 重置为参考轨迹(L165 `H = ref`), 被比较的两个向量共享 0.9×H 成分; 判据 = 权重相关中位 ≥ 0.99 | 代码 |
| P10 | 平价装置: king 段 41/41 锚 L∞ ≤ 9.31e-10; combo 段从 09-05 16Z 链式起步 `target_live` L∞ 最大 1.125e-4(DL 腿残差, 机理未闭合); king 段每锚约 1.2 s, combo 段约 40 s | `parity_replay_2026-09-12/receipts/PARITY_phase1_chain_full_1788624000_1789200000.json` |

## §2 分数层的臂(pod2)
**行集**: 与 `slow_pred_pinned.npy`(下称 P3)完全相同 —— `wide_fea_v2ext_meta.npz` 的锚 i(年份 2024/2025/2026, 成员内有限 `y4` ≥ 50), 格 = `members[i][isfinite(y4[i, members[i]])]`。
**booster**: 2026 行 = 保存的 `slow2026.txt`(8d79186b); 2024/2025 行 = 用导出器配方(`pod_export_bundle_v3.py` L56–60: `n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1`, 训练集 `YRA < YV`, 同一行序与 float32/秩标签)重训的折 booster, 模型文本存档。

| 臂 | 第 76 列(= 第 80 列)输入 | 其余 77 列 |
|---|---|---|
| **K0** 训练一致 | 存储的 float16 v0(原样 `astype(float32)`) | 原样 |
| **K1** 按服务 | `float32(nan_to_num(f_fund_ema_v1[j, 格]))`, j = 同一 E_ts 的 `wide_panel_4h_v2ext.npz` 行 | 原样 |
| **K0f** 量化零对照 | `float32(nan_to_num(f_fund_ema[j, 格]))`(未经 float16 的 v0) | 原样 |

无面板行的格在三臂都保持 NaN(断言: 存储第 80 列为 NaN ⇔ 该锚无面板行)。

**GATE K26(必须过)**: 8d79186b 在 K0 输入上对全部 2026 格的预测(按导出器写入 float32)与 P3 逐位相等。不过 ⇒ 停止并报告。
**GATE KF(决定基线)**: 重训折在 K0 输入上的预测与 P3 的 2024/2025 格逐位相等 ⇒ K0 := P3。若不逐位: 记录 maxabs 与逐锚 Spearman 最小值, **K0 := 重训 booster 自己的 v0 预测**(K0r), 分数层与书层一律以 K0r 为基线(两臂共享 booster), P3 只作参照。
**GATE AL**: 分数数组按 `build_dev_v4.py` L34–41 同法对齐到 v4 轴; 对齐后的 P3 与 `SLOW_v3_on_v4axis.npy` 数组相等(NaN 位置相同)。
**GATE S0(必须过)**: 第 76 列逐位相同的格上, 两臂原始分数差必须恰为 0(LightGBM 逐行预测, 无截面耦合)。不过 ⇒ 停止。

## §3 分数层度量(K1 对 K0 为主; K0f 对 K0 为零对照)
**锚集**: r18 C0_s42 臂的 `ts` 轴与其掩码 —— WA = 行号 ≥ 900 且 ts ≤ 2026-08-30 20Z(n 9138); **KL = WA ∩ ts ≥ 2024-01-01 00Z(n 5838)**; Y26 = WA ∩ ts ≥ 2026-01-01 00Z。某锚两臂同时有限的格 < 50 则该锚不入分数度量。
**事先声明**: 研究 king 在 2024-01-01 之前没有有限分数(RESULT_r5_angle1 L61), 所以「全 W_ALPHA 上有 king 分数的锚」与 KL 是同一集合; 两个标签都报, 由装置核实二者相同。

1. **逐锚 Spearman(K0, K1)**: 均值 / 中位 / p1 / p5 / 最小, KL 与 Y26。
2. **king 秩十分位变动份额**: 每锚每臂 `dec = min(9, floor(10·(rank_avg − 0.5)/n))`; 份额 = Σ(dec0 ≠ dec1)/Σ格, 窗内合并; 分全部、4h、1h、8h、其它(结算间隔取该锚面板 `f_fund_iv`, NaN 归「其它」)。
3. **rank-IC 对记账收益 y4s**: y4s = `meta_newprod_v4.npz` 的 `y4`(= dlw_v4raw `y4s`, Π(1+r)−1 RAW, 按 E_ts 与符号对齐; 不从 5m 缓存重算任何收益)。IC_a,i = Spearman(分数_a[i], y4s[i]), 格 = K0/K1/y4s 同时有限且 ≥ 50; ΔIC_i = IC_K1,i − IC_K0,i。报告 IC_K0 / IC_K1 / ΔIC 在「全 W_ALPHA(有 king 分数锚)」、KL、Y26 上的均值与 CI95; 逐年只作描述。
4. **CI 算法**: UTC 日块自举 = r18_judge.py `boot()` 逐字(NB = 2000; 第 k 次抽样 `np.random.default_rng([20260905, k]).integers(0, nd, nd)`; 统计量 = 抽中日的逐锚值之和 / 锚数之和; CI95 = 2.5/97.5 分位)。

## §4 书层(pod2, r18 装置族)
**装置**: `/workspace/uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py`(sha 9b8a6323…, 不改一字; 自报 `UPLIFT.self_sha256` 断言相等)。开发树 `/workspace/uplift_r2_2026-09-13/T4/dev` 的符号链接与 r18_drive.py L39–47 目标相同(realpath 断言)。
**环境**: 逐字 = r18_drive.py `A0(seed)`(L53–55)∪ 臂开关 ∪ `{SLOW_NPY=<T4 king 文件>, OUT_TAG}`, 外加 `OMP/OPENBLAS/MKL_NUM_THREADS=3`; `env -i` 白名单断言; 校准旗标前缀禁用表同 r18_drive L10。
**基线**: C0 = `{R18_INSTR=1}`(≡ 归档 A0); NW = `{R18_ELIG=1, R18_WARM=1, R18_INSTR=1}`; 种子 42 / 2027(`FSEED`, `FPRED=f10_A0_s{seed}.npy`)。
**跑次**: K1 × {C0, NW} × {42, 2027}(4); K0f × {C0} × {42, 2027}(2); **GATE PB**: C0_s42 用 T4 对齐的 K0 文件, `rec` 与 `W` 必须与 r18 归档 `arms/C0_s42.npz`(d6298deb…)逐位相等。若 GATE KF 不逐位: 另跑 K0r × {C0, NW} × {42, 2027}(4)作基线, GATE PB 改用 `SLOW_v3_on_v4axis.npy` 原件。
**度量**: `g = net_ex / gross_total`(bps/锚/单位 gross); 配对 Δg_i = g_arm,i − g_base,i(同基线同种子); WA / KL / Y26 均值与 §3 同一 `boot` 的 CI95; Δpnl / Δcarry / Δcost; 匹配换手变化; g 不同的锚数与首末锚; 逐年描述。2024-01-01 前两臂 king 分数都为 NaN ⇒ Δg 构造上为 0(由首个差异锚核实)。

## §5 判决规则(冻结)
- **MATERIAL** ⇔ (A) **C0 基线、KL 窗**: Δg(K1 − K0)的 CI95 在种子 42 与种子 2027 上**都**不含 0 且同号; **或** (B) **KL 窗** ΔIC(K1 − K0)的 CI95 不含 0。
- 否则 **NOT MATERIAL(在本分辨率下)**, 并写出分辨率 = (A) 两种子 Δg 的 CI95 半宽、(B) ΔIC 的 CI95 半宽。
- 只报不入规则: NW 基线(同一检验; 若与 C0 在 (A) 上结论不同, 判词加标 **BASE-DEPENDENT**)、WA 与 Y26 窗、K0f 零对照。若 K0f 自己满足 (A) 或 (B)(即仪器把纯 float16 量化判为材料性), 判词加标 **INSTRUMENT-FLAG**, 读作不可靠。
- 方向: MATERIAL 时符号说明「按服务的 v1」相对「训练一致的 v0」是帮还是害; 两个方向都算 MATERIAL。
- 族错误率说明: (A) 或 (B) 的并, 名义假阳性上界约 0.10(Bonferroni); 规则按任务书原样冻结, 不另作校正。

## §6 实盘窗检查(Mac, 生产者平价装置; 只描述, 不入判决)
**装置**(平价目录 `parity_replay_2026-09-12/devices/` 不改一字, 不写其 `replay_home/`):
- `T4/devices/shadow_loop_v3_replay.py`、`combo_stage_replay.py`: 平价装置的逐字节拷贝(sha 断言 = 4d3bc157… / f5ba9a82…)。
- `T4/devices/mk_t4_v0col80_device.py` → `shadow_loop_v3_replay_v0col80.py`: 在平价装置上做**唯一一处**替换(断言出现次数 = 1)——
  `    FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)` →
  `    FE_ANCH[:, 80] = np.nan_to_num(np.where(np.isfinite(fe_v[m]), T4_COL80_ROW(st, anchor)[m], np.nan), nan=0)   # T4: the only change`;
  `T4_COL80_ROW` 由驱动注入(未注入即 NameError); 统一 diff 存为 `.diff`。
- `T4/devices/t4_replay_driver.py`: 由 `replay_driver.py` 派生(diff 存档), 只改: 每臂独立 replay_home(`T4/private/replay_home_<arm>`); 输入改读冻结快照 `T4/private/snapshot_1789272000/`(aux / leg_returns_live / rolling / shadow_log / 逐锚 weights 与 target 文件 / 首锚 state_H, 逐文件 SHA256SUMS); booster 代理逐锚记录喂入的 X 与 pred(不改装置); 逐锚输出存 npz; combo 子进程 env 加 `PYTHONDONTWRITEBYTECODE=1`(不改计算, 防止在 `~/dl_quant_live` 写字节码)。
- **臂**: `served`(平价装置); `v1inj`(v0col80 装置, `T4_COL80_ROW` 返回装置自己当锚的 EMA 状态, 只跑 king 段); `v0`(v0col80 装置, `T4_COL80_ROW` 返回下述 v0 馈入)。
- **v0 馈入**: 450 个 `symbols_live` 名, 结算行 = 在役 bundle `funding_ledger_seed.json`(sha 85f1a1db…, 约 07-23 起)∪ 快照 `aux.json` 的 `ledger_tail`, 以 (名, 结算时刻) 去重(两源同时有的行费率必须相等, 不等行数入收据); 首行 `acc = 原始费率`, 递推 `a = 1 − 0.5^(max(ft − last, 1)/(3·86400))`, 与生产者 L345–349 同式但不乘 8/iv; 锚 A 的值 = 所有 ft ≤ A 的行之后的状态。每名报告启动残余权重 0.5^((A − 首行)/3d)。
- **锚**: 链式 41 锚 1788624000(2026-09-05 16Z)… 1789200000(2026-09-12 08Z)。

**门**:
- **PC1(served 仍逐位复现线上)**: king 段 weights 每锚 L∞ ≤ 1e-6 且通过率 ≥ 95%(G-P1 原定义); combo `target_live` 对线上 L∞ 每锚 ≤ 2e-4(Phase 1 包络 1.125e-4)。不过 ⇒ 实盘窗差值标 NOT VERIFIED。
- **PC-INJ(必须过)**: `v1inj` 的 king 段 weights 与 king `target_live` 文件权重在 41 锚上与 `served` 逐位相等 ⇒ 注入路径本身惰性。不过 ⇒ 停止。
- **ONE-PLACE(必须过)**: (i) diff 恰一行不同; (ii) 每锚 `v0` 臂记录的 X 在第 76 列之外与 `served` 逐位相等, 成员集相同; (iii) 第 76 列相同的行上 pred 逐位相等。
- **V0P(v0 馈入 = 训练配方)**: 与 `wide_panel_4h_v2ext_x0910.npz` 的 `f_fund_ema`(九月资金费为独立 REST 拉取, EMA 由面板末行续算)在共同锚(≤ 2026-09-10 00Z)成员格上比较: 相对差中位 ≤ 1e-4 且 ≥ 95% 格 ≤ 1e-3(|面板值| < 1e-7 的格改用绝对差 ≤ 1e-9)。不过 ⇒ `v0` 臂差值标 FEED-UNVERIFIED(照报)。
- **V1R(同一重建代码乘 8/iv 复现服务值)**: 与 `served` 记录的 X[:,76] 在 41 锚成员格上比较, 阈值同 V0P; 不过 ⇒ FEED-UNVERIFIED。例外名单入收据。
- **C81**: `served` 记录的 X[:,77] 与 x0910 面板 `f_fund_now` 在共同锚成员格上 ≥ 99% 相对差 ≤ 1e-6 ⇒ 服务侧第 81 列为原始费率。

**逐锚报告**(无判决): king 原始分数 Spearman(v0 vs served, 成员内); 十分位变动份额(全部 / 4h / 1h / 8h, 间隔 = 该锚生产者账本末行 iv); king 段目标 `weights/{A}.npz` 的 L∞、Σ|Δw|、归一化 L1 = Σ|w₀/G₀ − w₁/G₁|; combo `target_live` 的 L∞、Σ|Δw|、归一化 L1、两侧 gross 与净额、名数、权重相关; 两侧掩码席位 w3m。另报**描述性价格 Δg**: Δg_A = 1e4·Σ(w₀/G₀ − w₁/G₁)·y4s(A), y4s 取 `meta_newprod_v4_x0910.npz`(≤ 2026-09-10 20Z 有行的锚), NaN 记 0 并报未覆盖 |Δw| 份额; 均值与 §3 同一 `boot` 的 CI95。**只作描述**: 无 carry、无成本、无执行钟, 链式两臂持仓会分叉, 6 个 UTC 日。

## §7 边界与声明的盲区(不是关闭)
1. V2MAIN(F10)的 `fund_ema` 输入同样是服务 v1(`combo_stage.py` L138–146 把 v1 EMA 写进 `xfer_panel_live.npz` 的 `f_fund_ema`)、训练 v0 或 0(T1 事后描述) —— 本轮**不改、不测**; §6 装置里 V2MAIN 两臂相同。
2. 在役席位的 king 腿收益历史自 09-05 12:47Z 起由 v3 样本外(v0 打分)行播种(STATE.md 记), 而实盘追加行是 v1 打分 —— 本轮不测, 只记。
3. 书层是研究回放口径(v4 钉 + costb_PWR_G230k), 与实盘的对应关系按 r6 斜率 0.835 读, 本轮不重估。
4. 不提出任何部署; 结果文件只陈述两种修复形态(服务 v0 给 king 列 / 用 v1 重训 king)及其需要用户字。

## §8 修订规则
冻结后任何改动 = 另立 AMENDMENT 文件并先记 sha, 再看受影响的数字; 门失败按上文登记的处理执行, 不临时改阈值或窗。
