> **创建:** 2026-09-17 05:0xZ | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** 预注册 v1(判据先于数字; 未跑任何 GPU/CPU 正式步骤) | **作废条件:** 任一输入工件 sha 变化、判据修订(必须以 AMENDMENT 追加, 原字节保留)、或独立研究员复审推翻某条

# FP2-8 · 修复版全链重训 + 最可信回测 — 设计与预注册

## 0. 目标(用户字 09-17: 「完成所有环节的修复和规范…从离线的训练评估到线上…给出最可信的回测结果。有必要的话可以更新线上的模型」)
产出两张同口径表, 都在 **v4 RAW 记账 + 可交易掩码 + lifecycle 回放(FP2-5 认证的 CLOSE 归属)+ 固定 2× 逐锚复利 NAV** 下:
- **T-A0**: 在役形态(在役 king bundle 8d79186b + 在役 F10 351ae26b 的判官等价物 = `SLOW_v3_on_v4axis.npy` + `f10_A0_s{42,2027}.npy`)逐年表 —— 这是「实盘现在跑的东西, 最可信的历史表现」。
- **T-A1**: 候选(修复链重训: 轴修 + 可交易成员 + 训到 2026-08 末)逐年表 + 配对判官 A1−A0。
换装建议**只**在 §5 判据全部满足时提出; 换装本身仍是用户字(FP2-9)。

## 1. 输入基线(全部 VERIFIED 于本会话或 FX_DATA 收据)
| 输入 | 路径(pod2) | 身份 | 状态 |
|---|---|---|---|
| 5m 缓存 holefix2 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` | 09-09 02:27, 490,753×829×7 f16 | **不改**: C1/C3(BOB/BMT 2026-02, MTL 2026-04)与 C6(13 个 OPEN 代际边界)实测**不存在于本缓存**(§7 收据) |
| 原始收益补丁 | `/workspace/review_scratch/raw_patch.npz` | r6 索引 94e8e8c1 | 不改 |
| 4h 面板 | `wide_panel_4h_v3splice.npz`(DL) / `wide_panel_4h_v2ext.npz`(king) | 09-01 | 不改 |
| 可交易掩码(A0 重基输入) | `$H/masks/umask_UPIT_CRYPTO_tradable_W24H.npz` | 3badc4b6(FX_DATA TRD-D3 N2, 5/5 控制绿; 掩掉 33,386/2,761,057 = 1.21% 格) | **新注入**(§2.2) |
| 可交易性工件 | `/workspace/fx_data_2026-09-13/out/trd/tradability_v1.npz` | 54d409d0(run 2 rc=0, D8-D10) | 掩码来源 |
| 在役 king 判官等价物 | `$KD/SLOW_v3_on_v4axis.npy` | 09-09 | A0 臂 |
| 在役 F10 判官等价物 | `$H/dev_v4/f8_2026-08-22/preds/f10_A0_s{42,2027}.npy` | 09-09 | A0 臂 |
| 冻结回放引擎 | 研究仓 `FX_REPLAY/frozen_codex_engine_7a05b4f4/`(8 文件 SHA256.txt) | FP2-5 R1-R7 12/12 | 回放 |
| 月合同 | `v4_month_2026-09.env` 复用, **新根 `R=/workspace/fp2_2026-09`**(不覆盖 review_scratch 任一产物) | FP2-3 preflight 对 2026-09 不要求 PREV_* | 驱动 `chain_v4_monthly.sh` |

## 2. 修复项如何进入链(FP2-7 收口)
| 项 | 实测结论 | 进链动作 |
|---|---|---|
| C1 三月 raw 回填 / C3 519 标签 | **不适用**: 我方缓存 BOB/BMT 2026-02 各 9216 行、MTL 2026-04 9792 行全部有限、零冻结、`log_cnt` 无 0; RAW 目标 y4s 168/168/180 锚全有限且 qvk>0 | 无(受据 §7-1/2)。可采纳的是其**方法**(旧值逐位重放 + 支撑外硬 raise), 已是 `fx_fnd_hol_rebuild_v2` 的写法 |
| C6 代际/HOLD | 6ef59338 内容审毕: 是其自身产物的**溯源绑定门**(硬编码 3 档案/24,768 行)+ 诊断性资金费可交易掩码, 无可采纳数据机制; 主源 `build_funding.py`(53 行)/`build_targets.py`(18 行)在 pod2 未入库, 机制 = 逐名逐位复现原公式 + 代际外资金费零影响 null 测 + 知识 HOLD。**对我方数据**: 13 个 OPEN 边界首根新代 bar `ret5=NaN`、前一根 NaN ⇒ 不存在跨代假收益 | 无(受据 §7-3)。**记录**: 死期冻结行(ret5==0&cnt==0, 如 MAVIA 前 30 日 8437 行)由可交易掩码处置(下行) |
| A0 参照重基(死合约) | FX_DATA TRD-D3 已测: TF Δg −0.0603/−0.0519 bps(s42/s2027) INCONCLUSIVE@δ0.05, 效应几乎全在 2026(−0.32) | **A0 与 A1 都在可交易掩码下评估**(§2.2); 不再单独「重基」 |
| king 轴首 5 天 | `pod_fea_ext_clamp.py`: `grid>=576` 但窗 2016; E<2016 时 `E-2016` 负索引绕回 ⇒ `v7=0` ⇒ 30 锚被**静默删除**(非污染) | **`pod_fea_ext_clamp_v2.py`**: `grid >= 2016` 显式 + 断言; 正控: E≥2016 输出与 v1 **逐位相等**; v1 冻结 |
| C5 估值缺失点 | 属回放估值层(其表 2026-07-24 后缺 2,943 格) | 回放输入加**估值覆盖门**: 持仓名在每锚必须有有限估值, 缺 ⇒ UNAVAILABLE(不前推、不静默) |
| C7 E60 资金费先于 reduce-only 退出 | 只在 RiskEngine(停机政策)路径; `_on_close` 同族缺口未修 | 停机政策臂用 **v2 引擎副本**: 拉钩子 + 补 `_on_close` 覆盖检查 + 测试; 冻结副本不动 |

### 2.2 可交易掩码注入(A1 的训练成员 + 两臂的评估)
- 评估: `run_v4_arms.sh` 的 `UMASK_NPZ=$H/masks/umask_UPIT_CRYPTO_tradable_W24H.npz`(替换 `umask_UPIT_CRYPTO.npz`), A0/A1 同一 COMMON。
- 训练成员(仅 A1): king `pod_fea_ext_clamp_v2.py` 与 DL `pod_dlw_targets_raw.py` 成员规则各 ∧ `tradable_W24H[E, j]`, 经 env `MEMBER_MASK_NPZ` 注入; **正控**: 全 True 掩码 ⇒ 与 v1 逐位相等。
- 消融臂 **A1nt**(A1 不带训练掩码)仅在 GPU 允许时跑, 用于归因, **不参与换装判据**。

## 3. 步骤(= 十月 runbook §0★ 步 0-7 在 2026-09 合同上重跑, 新根 R)
| 步 | 内容 | 门(三态 finalize3) | 预算 |
|---|---|---|---|
| 0 | 装置同步到 `$R`; `live_pins.json` 自在役 bundle config 重抄; 记录全部输入 sha | preflight(FP2-3) PASS | 15 min |
| 1 | 缓存覆盖门 `cache_coverage_gate_v2.py`(洞 0/宽缺口 0) | PASS | 5 min |
| 2 | 数据层: RAW 目标(带 MEMBER_MASK)→ fea82 → fea89 → king v4 特征(v2 builder) | 每步 rc + 复制逐字节; **v2 正控**两条 | 40 min CPU |
| 3 | legs: 在役行逐位原样 + 新锚同公式(AMENDMENT 5) | 分年 WL 自检 | 10 min |
| 4 | F10 20 折 FIX7 EMBARGO=1, RAW, s42+s2027 → merge → refit | 折外泄出=0; σŷ/σy≥0.02 | ≈5.5 h GPU |
| 5 | king 导出 v4 轴(v2 特征) `BUNDLE_GENERATION=v4_2026-09fp2` | 出口自检 | 30 min |
| 6 | 判官: A0 vs A1(dyn/fix × s42/s2027), 掩码 §2.2; 估计量 r18_judge(g=net_ex/gross_total, UTC 日块 bootstrap 2000) | 见 §5 | 1 h |
| 7 | 出口门 v2(`v4e_*` EXPORT_ARM=A1) | PASS/FAIL/UNAVAILABLE | 10 min |
| 8 | lifecycle 回放: A0 与 A1 书 × {无停机, 停机政策 v2}; 估值覆盖门; 逐年表 | 门 UNAVAILABLE ⇒ 该臂不出数 | 1-2 h |
| 9 | 入档: RESULT + receipts + MANIFEST sha; 验收表 v2; 记忆 | — | — |

## 4. 逐年表口径(冻结)
每年一行(2022…2026YTD)+ 全期: 净 bps/锚/gross(RAW), 年化 Sharpe(按 UTC 日聚合), 最大回撤(固定 2× 逐锚复利 NAV), 换手/锚, 费用 bps/锚, 有效锚数, 可交易掩码剔除格数。**两臂同表同窗**; 不报任何 CAL=simple 数字; 不做训后调参。

## 5. 判据(先于任何数字; 修改只可 AMENDMENT)
- **G1 配对判官**: A1−A0 在 W_ALPHA 与 KING_LIVE(2024+) 两窗、s42 与 s2027 两种子、dyn 政策下 **CI95 下界 > 0**(四格全满足)⇒ BETTER; 任一格 CI 含 0 且点估计 ≥ −δ(δ=0.05 bps/锚/gross, 同 SPEC §7)⇒ UNDECIDED; 任一格上界 < 0 ⇒ WORSE。
- **G2 逐年非劣**: 回放逐年表中 A1 净额低于 A0 超过 δ 的年数 ≤ 1, 且 2026YTD 不在其中。
- **G3 出口门 v2 PASS**(资格合同, 含信号逐位收据)。
- **换装建议 = G1 BETTER ∧ G2 ∧ G3**; G1 UNDECIDED ⇒ 报「无换装理由」, 但 T-A0 表仍作为最可信回测交付; 任何 UNAVAILABLE ⇒ 该格不出数、不推断。
- 「点估计 ≥ −δ 且 CI 含 0」**不是**非劣证明(记忆 noninferiority_rule_is_not_noninferiority_proof); 只作 UNDECIDED 标签。

## 6. 不做的事(边界)
不改 F10 配方/早停规则/损失(另有 DNR 与轴); 不改 combo 权重 0.55/0.45 与席位规则; 不做多种子集成; 不在训练里用 2026-09 之后数据; 不动 review_scratch 既有产物; 不动实盘任何文件。

## 7. 受据(本会话, 只读探针, pod2 复跑写文件)
| # | 文件(`docs/fixprogram_2026-09-13/FP2_receipts/`) | 内容 |
|---|---|---|
| 7-1 | `probe_c1c3_ours.py` / `.out` | BOB/BMT [01-30,03-03) 9216 行 NaN 0 冻结 0; MTL [03-30,05-03) 9792 行同; max\|ret5\| 0.073/0.050/0.014 |
| 7-2 | `probe_c1c3_targets.py` / `.out` | y4s BOB/BMT 2026-02 168/168 有限、MTL 2026-04 180/180 有限, qvk>0 全部; holefix2_cells 键(fill_runs 4×2) |
| 7-3 | `probe_c6_open_bars.py` / `.out` | 13/13 OPEN 首根交易 bar ret5=NaN, prev NaN; 前 30 日冻结行数逐名 |
| 7-4 | `fp2-6_booster_pin_book_json.patch` | FP2-6 配置补丁(未应用) |

## AMENDMENT 1(2026-09-17 05:1xZ, 先于任何数字; 原文字节保留)
1. **king 轴修法改为「与 DL 同构的全窗 clamp」而非 `grid>=2016`**: 读源码后确认 v1 的缺陷不是起点错, 是成员统计块(n7/qvm/m7/v7)漏掉了逐特征窗已有的 E-0909-A clamp(负索引绕回缓存尾 ⇒ v7=0 ⇒ 30 锚静默删除), 且 covr 除常数 2016。v2 = `S7=max(E−2016,0)` + covr 按实际窗长归一 = `pod_dlw_targets_raw.py` 冻结约定 P.1 `[max(E−2016,0), E)`。**正控**: E≥2016 全部数组逐位等于 v1(S7≡E−2016; /2016 ≡ /max(E−S7,1)); 30 个 E<2016 锚以部分窗进入, 与 DL 轴同构。派生脚本 `derive_fp2_builders_v2.py` 以「恰一次」hunk 替换从冻结 v1 生成 v2, 脚本本身即受据(重跑必须字节相同)。
2. **成员掩码语义**: A1 训练成员掩码 = TRADABLE(W24H)@锚, 在缓存自身 4h 网格上(装置 `fp2_member_mask_build.py`), **不含** U-PIT/CRYPTO umask(那是宇宙政策, 不混入数据修正); 正控 P2 = (掩码 ∧ umask) 在 A0 轴上与 FX_DATA 认证注入件 3badc4b6 **逐位相等**。评估(两臂)用 3badc4b6 本件, 路径更正为 `/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz`(§1 表写的 `$H/masks/` 不存在)。
3. **接入路径**: 月度驱动 `chain_v4_monthly.sh` 以 basename 硬编码两构建器, 且 AMENDMENT-1 钉逻辑与 478 格套件的 mock 按 basename 识别 ⇒ v2 用**新文件名**, 由可选合同键 `BUILDER_TARGETS` / `BUILDER_KING_FEA`(缺省 = v1 名)选择, `MEMBER_MASK`(可选)经 `MEMBER_MASK_NPZ` 显式传入两构建器; mock/`_REAL_WRITERS`/钉逻辑同步扩到所选构建器; 套件加格。不用同名覆盖(latest-copy 族)。
4. **legs 局限(如实)**: `pod_legs_v4b.py` 按 AMENDMENT 5 逐位复制在役旧行(Z24/ZFD/WL), 只新算新锚 ⇒ A1 在 2026-08-30 前的 legs 行来自**未掩码**成员。不在本轮改(改了会重现 AMENDMENT 5 的 2023 king 席位问题); 记为 A1 的已声明局限, 消融臂 A1nt 可测其影响。

## AMENDMENT 2(2026-09-17 05:3xZ, 运行合同与已跑阶段; 先于任何书层数字; 原文字节保留)
1. **合同** `v4_month_2026-09_fp2.env`(sha256 `b7d0afa7…`, 40 键 = 九月合同 563efdef + 新根 `R=/workspace/fp2_2026-09` + `GATE_STEP1=fp2_gate_step1.py`(ae21f86f)/`GATE_STEP2=fp2_gate_step2.py`(db5b44d1) + 可选键 `BUILDER_TARGETS=pod_dlw_targets_raw_v2.py`(9e9dfd94) / `BUILDER_KING_FEA=pod_fea_ext_clamp_v2.py`(7b8b843d) / `MEMBER_MASK=$R/masks/member_mask_tradable_W24H_cachegrid.npz`(e0f67739; P2 与 3badc4b6 逐位相等)。`BUNDLE_GENERATION=v4_2026-09fp2`; `LIVE_PINS=$R/live_pins.json`(自在役 bundle config 09-17 重抄, 与九月 live_pins 逐字段相同)。
2. **门批准**: `ELIGIBILITY_CONTRACT.json` 1188267a → 69edc437(PROPOSED3): STEP1/STEP2 `approved_source_sha256` 各追加 FP2 变体, `approved_variants` 记录范围; 前身保留 `ELIGIBILITY_CONTRACT.r1_1188267a.json`; 套件自洽格改为「归档 sha 在列 ∧ 其余 sha 必须是已声明变体且盘上 sha 相符」。依用户常设规则(已知问题不等裁定, 事后独立复审)。
3. **驱动**: `chain_v4_monthly.sh` 顶层 `BT/BK` 选择(缺省 v1 名, 既有合同不变)+ `MEMBER_MASK_NPZ` 显式传入三次构建 + DEV_FILES/PF_INPUTS; `chain_lib.sh` 注册三可选键; `run_v4_arms.sh` `V4_UMASK_NPZ` 覆盖(两臂同掩码评估)。装置目录同步到 `$R/devices_v4chain`(D), `._*` AppleDouble 已清。
4. **原始收益补丁清单**: `v4_rawpatch_manifest.py` 以 `raw5m_kl`(月度 CSV)+ `klines5m_daily` 两源生成: candidates 953 / patch rows 952 / kept 952(逐位重导出 952)/ not_clipped 1 / clipped_missing 0 / unresolved 0。首跑仅日 zip 源时 unresolved 948 —— 该清单留档 `raw_patch.manifest.unresolved948_dailyonly.json`, 不消费。
5. **阶段顺序**: preflight(PASS 05:27:58Z, 23 装置/31 输入/3/3 批准)→ cache(coverage v2 PASS 05:32:38Z; RAW_PATCH_COVERAGE)→ **controls**(`fp2_controls.py`, 不在驱动内, 门前必跑; 收据 `$R/controls/CONTROLS.json`)→ data → gates(FP2 变体绑定 controls)→ king → legs → mwf(GPU)→ refit → np_export → **A0 重跑**(`V4_UMASK_NPZ=…tradable_W24H.npz bash run_v4_arms.sh A0`, 覆盖 `$R/health_check/dev_v4/probe_artifacts/…V4_A0_*`, 前后 sha 入收据)→ arms(A1, 同掩码)→ judge → export → 回放(§3 步 8)。
6. **已知局限登记**: 九月参照 king 构建 `wide_fea_v4.npy` 09-09 03:05、DL 目标 `dlw_v4raw/data/dlw_targets.npz` 09-12 15:17 —— 二者的构建器 sha 由 controls 的逐位比较间接核验(不等即红, 不推断)。

## AMENDMENT 3(2026-09-17 05:5xZ, 试跑中发现的两处装置缺陷与处置; 先于任何书层数字)
1. **`health_check/run_arm.sh` 硬编码 `ROOT=/workspace/review_scratch/health_check`**(dev 树内文件, 不在研究仓): 任何非九月根跑臂都会写进九月树。FP2 副本改为 `ROOT=$(cd "$(dirname "$0")" && pwd -P)`(sha8 69e1e949 → f30b2c7c, 原件留 `run_arm.sh.orig_sept`); preflight 重跑(它把 `HC/run_arm.sh` 当输入哈希), 现钉 driver 398fb4c5 / build_dev_v4 1bc846cf。十月 runbook §0★ 修订 8 登记; 根治(收进装置目录由 D 分发)列入 FP2-9 采纳项。
2. **`build_dev_v4.py` 自检 `members bitwise`** 对掩码构建按构造失败 ⇒ 改为掩码感知(env `DEV_MEMBER_MASK_NPZ`, 驱动 arms 阶段传 `${MEMBER_MASK:-}`): 掩码成员 ⊆ 参照 ∧ 被减者掩码为 False ∧ 每个共同锚有掩码行; 无 env 时逐字节同旧规则。`tests_build_dev_v4_mask.py` 5/5(M2/M4/M5 红能力)。
3. **A0 对齐确认**: `build_dev_v4.py` 按 E_ts 把 `PREV_BUNDLE/slow_pred_pinned.npy` 投到本根 king 轴(`SLOW_v3_on_v4axis.npy`)、把 `f8_ext/preds/f10_V2MAIN_s*` 投到本根 DL 轴(`f10_A0_s*`); `w10_health.py` 按 E_ts 对齐 FPRED; FP2 king 轴 = 10182+30 = 10212 = DL 轴。⇒ **不需要手工重投**; 但 A0 重跑必须在驱动 arms 阶段之后(dev 树已重链到本根)、judge 之前 —— 顺序改为 … np_export → arms(A1) → a0rerun → judge → export(`chain_fp2_run.sh`, 收据 `A0_RERUN_TRADABLE.json` 记四件工件前后 sha)。
4. 无人值守运行器 `chain_fp2_run.sh`: 逐阶段调用 `chain_v4_monthly.sh V4_STAGES=<stage>`, 首个非零 rc 即停; `controls_wait` 要求 CONTROLS.json VERDICT=PASS; `V4_UMASK_NPZ` 导出给两臂。

## AMENDMENT 4(2026-09-17 06:0xZ, 逐年表的主仪器; 先于任何书层数字; 原文字节保留)
1. **§3 步 8 / §4 的逐年表主仪器改为「臂记录」**(`w10_ablation_series_V4_{A0,A1}_{dyn,fix}_s{42,2027}.npz` 的 `*_rec`, 列 net/pnl/carry/cost/gross_total/turnover/…, RAW 记账, 与判官 `judge_v4.py` 同一输入、同一书变体), 而不是 lifecycle 引擎回放。理由: 冻结引擎(7a05b4f4)需要逐锚价格表、结算事件流(费率+标记价)与 PIT 生命周期日历+登记表作为输入, 我方链尚不存在这套市场输入(独立研究员的 `stream_market_repaired` 是其 canonical 档案上的产物, 日历 candidate2 非全 829 PIT 认证); 在数字出现前把主仪器换成已有受据、判官同源的臂记录, 比在时限内拼一套未经认证的市场输入更可信。r18 逐年表(`TABLE_per_year_v4_caliber_2026-09-12.md`)正是同一仪器。
2. **口径(冻结)**: g = net_ex / gross_total(bps/锚/单位 gross, 扣费扣 carry); 年 = UTC 年; 每年一行 + 全窗(W_ALPHA 2022-06-30 起, 与 r18 同); 年化 Sharpe 报两种并标注: (a) r18 约定 逐锚 mean/std·√2190, (b) 本设计 §4 UTC 日聚合 mean/std·√365; maxDD 按固定 2× 逐锚复利 NAV(NAV_t = Π(1 + 2·g_t·1e-4)); 换手/锚、费用 bps/锚、carry bps/锚、有效锚数、可交易掩码剔除格数(自 config_json UMASK_NPZ 与掩码文件)。两臂同表同窗; 配对 Δ(A1−A0)逐年点估计 + UTC 日块 bootstrap 2000 CI95(种子 [20260905, k], 与 r18_judge 同)。
3. **lifecycle 引擎降为交叉核对(范围声明)**: 若在 FP2-9 前能为一段窗口(候选 2025-01→2026-08)组装出有受据的价格/结算/日历输入, 则对 A1/A0 的同一权重做第二套记账(CLOSE 归属、现金恒等式), 作为附表; 做不到就在验收表标 **PENDING**, 不作声明、不影响 G1–G3。
4. 判据 G2 的「年」以本表为准; G1 仍以 `JUDGE_v4.json`(W_ALPHA / KING_LIVE, s42/s2027, dyn)为准。

## AMENDMENT 5(2026-09-17 06:3xZ, 首次 controls 被 OOM 杀; 处置 = 顺序而非改码)
- **事实**: pod2 容器 cgroup `memory.max = 61,0GB`(宿主 247 GB 无关); `memory.peak` 61.0 GB, `memory.events oom_kill 3`; controls 的 king 构建 rc **−9**(SIGKILL)于 `cumsum log_qv (1828s)`, DL 构建 rc 0 完成。当时数据层的 RAW/CLIP 目标构建并行在跑。king 构建器(v1/v2 同算术)保留 7 通道 float64 累计和 ≈34 GB + 瞬时 ≈13 GB + 缓存 5.7 GB ≈ 50–58 GB, **单独跑才在 61 GB 内**(九月 v1 构建即单独跑)。
- **处置**: 不改构建器(K2 要求与九月 v1 逐位相等, 算术不能动); 运行器加 `controls_run` 阶段, 在 `data_wait` 之后**单独**运行 `fp2_controls.py`(已有 PASS 收据则复用; 失败目录整体保留为受据 `controls_oomkilled_20260917T0625Z`)。规则: **任何 king 构建(数据层 king v2+掩码、controls king 无掩码)不得与其它大内存任务并行**。
- **影响**: ETA 顺延约 1 h(controls 在数据层完成后串行 ≈55 min); 判据不变。十月 runbook 登记为 §0★ 修订 9。

## AMENDMENT 4.3 补记(2026-09-17 06:4xZ, lifecycle 交叉核对可行性调查; 未开工)
- **可行**, 但需三件输入装置(估计 3–4 h 装置 + 1–2 h 运行), 本轮未开工, 状态 **PENDING**:
  1. 逐锚收盘价表 [T, 829]: 源 = `/workspace/wide_multisrc/klines5m/<SYM>/` 月度 zip(缓存本身的来源; 月度 CSV `raw5m_kl` 只覆盖补丁用到的 1,058 个(名, 月), **不是**全价格表; 日 zip 只有 08-22..31)。
  2. 结算事件流: `/workspace/wide_multisrc/funding/<SYM>/<YYYY-MM>.zip` 列 `calc_time, funding_interval_hours, last_funding_rate` —— **无结算标记价**; `premidx_daily` 仅 08-22..31。⇒ 历史事件的 mark 只能用锚收盘价代理, 引擎按 `proxy_mark_events` 计数, 现金记账为近似(必须在表头声明)。
  3. 生命周期日历 + 现金登记表: candidate2(5248d459, 166 名/168 CLOSE/13 OPEN, 非全 829 PIT 认证)+ `CASH_REGISTRY.json`(calendar_expanded1/2/3; 需核其 `calendar_sha256` 是否绑定 candidate2, 见本会话核查输出)。
- 若做: 对 A0/A1 同一权重(臂记录 `d30_n2_c42_W`, 10,039 锚轴)跑冻结引擎 7a05b4f4, 报 CLOSE 归属与现金恒等式误差, 作附表; **不参与 G1–G3**。
- **更正(同时段核查, 原行字节保留)**: (1) `/workspace/wide_multisrc/klines5m/<SYM>/` 在 pod2 上为**空目录**(缓存来源已不在盘上)⇒ 逐锚价格表需要**下载作业**(data.binance.vision 4h 月度 kline zip, 829 名 × 56 月 ≈ 4.6 万小文件)才能建; (2) 三份 `CASH_REGISTRY.json` 都**不**绑定 candidate2, 各绑定自己的扩展日历(expanded1 854bfde5 / expanded2 b09ccef1 / expanded3 d36598dc); 一致的输入对应取 `calendar_expanded3/CONTRACT_LIFECYCLE.json`(d36598dc)+ 其 `CASH_REGISTRY.json`(34456b53), candidate2 只是更早的证据版。⇒ 可行性降为「需下载作业 + 用 expanded3 对」, 状态仍 PENDING, 估计 5–6 h。

## AMENDMENT 6(2026-09-17 08:3xZ, controls 首次真实判词 FAIL 是判据错, 不是数据错)
- **真实数据结果(串行重跑, 08:19Z)**: K1 ✓(九月 10,182 锚全在 v2 的 10,212 中)· **K2 ✓ 共同 10,182 锚 FEA/members/y4/qvk 逐位相等** · K4 ✓ · **D1 ✓ DL 目标 12 数组逐位等于九月** · D2 ✓ · K3 ✗。
- **K3 为何红**: 我的判据要求 30 个新锚的成员特征全部有限, 但 king 构建器对 king 面板(`wide_panel_4h_v2ext`, 起 2022-01-31)首行之前的锚**不写 fund_ema/fund_now 两列**(留 NaN)——九月 v1 自己的首 ~138 锚同样如此(K2 已逐位证明)。合成套件的面板覆盖全部锚, 所以从未触发。⇒ 判据改为「非资金费列有限」, 资金费 NaN 行数记入收据; 合成套件加「面板晚于首锚」布局(G1/G1b)。
- **不重建**: 两次构建 rc 0 的产物原样, 新增 `VERIFY_ONLY=1` 只重算判词并记录 `previous_receipt`(G1c 证明不重建); FAIL 收据留档 `controls/CONTROLS_fail_K3criterion_20260917T0819Z.json`。
- 结论: v2 构建器与九月 v1 在真实数据上**逐位一致**(共同锚), 且恰多出 30 个 E<2016 锚 —— AMENDMENT 1.1 的机制声明在真实数据上成立。

## AMENDMENT 7(2026-09-17 08:5xZ, 用户字裁定 FP2-9 判据; 仍在任何书层数字之前)
用户字(09-17):「在更正确真实可靠的 pipeline 上重训的模型, 经过严格的因果回测, 如果有帮助或者不损害表现的情况下, 我建议换装。」⇒ §5 G1 改写为**非劣性判据**(不是「点估计 ≥ −δ 且 CI 含 0」那种假非劣, 见记忆 noninferiority_rule_is_not_noninferiority_proof):
- **G1′**: A1−A0 在 W_ALPHA 与 KING_LIVE 两窗、s42 与 s2027 两种子、dyn 政策下, 配对 Δg 的 **CI95 下界 > −δ**(δ = 0.05 bps/锚/gross, 同 SPEC §7)⇒ **非劣(可换)**; 四格下界均 > 0 ⇒ BETTER; 任一格上界 < −δ ⇒ WORSE(不换); 其余 ⇒ UNDECIDED(不换, 报「证据不足」)。
- G2(逐年非劣, 差于 A0 超过 δ 的年数 ≤ 1 且不含 2026)与 G3(出口门 v2 PASS)不变。
- **换装建议 = G1′ ∈ {非劣, BETTER} ∧ G2 ∧ G3**; 建议只是建议, 换装动作仍以用户对具体 bundle sha + F10 np sha 的字为准(runbook §0★ 步 8; 若 FP2-6 已钉则同窗改钉)。
- 「严格的因果回测」在本轮 = 同掩码配对回放 + 三门; lifecycle 二次记账 PENDING(4.3 补记), 出数时必须如实标注。

## AMENDMENT 8(2026-09-17 09:1xZ, FP2 门首次真实判词 FAIL: 成员规则漏了截断效应; 判据修正, 不看任何书层数字)
- **真实数据读数**(STEP1/STEP2 的 C 段, 10,212 锚同轴): 掩码构建相对无掩码控制 —— 锚只减不增 ✓(only_masked 0, dropped 0); 有减行 1,229 / 减格 2,231, **被减者全为掩码 False**(removed_not_masked_rows 0)✓; 但 **109 锚出现「掩码成员 ⊄ 控制成员」** ⇒ 我写的「masked ⊆ control」子集规则判 FAIL。
- **机制**: 两个构建器的成员规则都是「合格候选 → 若 > NTOP=400 按 qvm 取前 400」。掩码把前 400 中的名去掉后, 无掩码池里排 401+ 的名进入掩码后的前 400 —— 这是**新增**, 只在控制行被截断(len == 400)时发生。交接件 Q7 已预见截断会影响成员, 但我把它写成了子集(只减)。
- **修正后的规则**(`fp2_gate_lib.members_subset_check`): 减去的 ⊆ 掩码 False(不变); **新增只允许在控制行恰为 NTOP 的锚, 且新增者掩码为 True**; 其余新增 ⇒ FAIL。STEP2 值列逐位比较改在**交集成员**上(新增者在控制里没有格)。合成套件加 G8(430 名 > 400: 掩掉 20 名 ⇒ 新增出现且 PASS)与 G9(控制行 395 名时的新增 ⇒ FAIL)。
- 这是判据在结构上错(与 AMENDMENT 6 同类: 合成夹具没覆盖真实布局), 不是看数改判; 修正只放宽「截断行的新增」一种情形, 且要求新增者本身可交易。A1 的成员集因此与 A0 控制的差 = 掩码剔除 + 截断补位, 两者都会记入门收据。

## AMENDMENT 9(2026-09-17 10:4xZ, 独立研究员复审 a5a596fe F01–F10 的代码级修复; 全部先于任何书层数字, 判据只收紧不放宽)
- **F01(P1)** `run_v4_arms.sh`: 行尾注释吞掉 K3/K4/K4E ⇒ A0 用了新 king(SLOW_NPY 为空回退)。修: 注释独立成行 + 缺 SLOW_NPY 显式 `ARMS_FAIL` rc3; 冻结缺陷副本 `run_v4_arms.r1_de4ed666.sh`; `tests_run_v4_arms.py` 5/5(W4 红能力: 旧版 A0 SLOW_NPY 为空)。**无工件受影响**: 修复早于本根 arms 阶段(arms 尚未跑)。
- **F02/F07(P1)** 控制收据身份链: `VERIFY_ONLY` 绑定前次收据的输入/产物 sha(任一变 ⇒ UNAVAILABLE); `bind_controls` 校验盘上 `fp2_controls.py` sha == 收据 self_sha256、每项 check ok、runs=={king,dl} rc0; 门变体带 `scope{V4_MONTH,R}`(合同), 他根/他月拒跑; 控制输入 sha 对 preflight `external_sha256`。合同变体 sha 刷新(step1 47717230 / step2 984053e8, requires lib d93e44d2)。
- **F03(P1)** 决策装置 `fp2_decision.py`: AMENDMENT 7 逐字实现(G1′/G2/G3; 判官只作信息; 缺格 UNAVAILABLE); 运行器新增 `per_year` `decision` 阶段。**G2 机器规则**(复审 Q9 要求写明): 对每个种子分别算「dg < −δ 的年」集合, 两种子都须满足「年数 ≤ 1 且不含 2026」。
- **F05(P1, FP2-1)** 面板重建: 无源流的名 = `COPIED_NO_SOURCE`(计数+列名), 只在有源名上比较 REPRODUCED; 全无源 ⇒ UNAVAILABLE。
- **F06(P2)** 成员规则再收紧: 保留成员全为掩码 True(忽略掩码的构建 ⇒ FAIL); 被删锚必须可解释(控制行掩码 True 成员 < MIN_MEM=50; 无控制轴掩码行 ⇒ UNVERIFIED FAIL)。`build_dev_v4` 自检复用同一实现(其原子集规则会把真实 109 个截断补位行判 FAIL)。
- **F08(P2)** 代际 OPEN 边界暴露: 装置 `fp2_open_window_exposure.py`, 真实读数(收据 `FP2_receipts/OPEN_WINDOW_EXPOSURE_2026-09-17.json`): 13 事件, 48h 内成员锚 **0**, 7d 内 **40**, 30d 内 **1,771**(占 2,751,058 成员格 0.064%), 首次入成员 ≈161h(PUMPUSDT 104.5h); king 与 DL 成员集读数相同(同成员规则)。**经济影响 UNAVAILABLE**(未测; 不以合成反例代替)。§2.2「C6 无需进链」降级为「首根不跳价已证; 7d/30d 窗口暴露已量化; 影响未定价」。计划: 十月链成员掩码加 OPEN 后 30 天屏蔽(预注册, 另一次干预)。
- **F09(P2)** 逐年表 maxDD 主口径 = 逐锚复利 NAV(日末采样为次口径; 1→1.1→1 日内案例真 −9.09%)。
- **F10(P2)** 逐年表输入门: 两臂同 UMASK 路径与文件 sha(且 == 合同 umask sha)、gross_total 有限正、symbols 轴同、4h 无缝网格; W_ALPHA 起点钉 **2022-06-30 00Z**(不是「第 900 行」)。
- 套件: gates 17/17, decision 14/14, per-year 11/11, fnd_hol 20/20, exposure 5/5, arms 5/5; pipeline 套件见提交。真实数据: 重跑 preflight → controls(verify-only, 新装置)→ gates(F06/F07 绑定)——结果见 `REVIEW_RESPONSE_FP2_2026-09-17.md`。

## AMENDMENT 10(2026-09-17 11:5xZ, 独立研究员二轮复审 e0ddd4cc 的 R01–R11 修复; 仍先于任何书层数字)
- **R09(P2, 最重)** 成员规则精确核 `fp2_member_rule_check.py`: 从缓存按两构建器**各自**公式重算资格(覆盖率 ≥0.95、波动 ≥1e-4、目标有限)、qvm 与截断; **先**要求无掩码复刻逐锚等于控制构建(把复刻绑到真构建器), **再**要求掩码构建逐锚等于「规则 ∧ 掩码 → top-400 → ≥50」的精确集合与锚轴。合成 430 名夹具: 少 1 名 / 错 1 名 / 多 1 名 / 错删锚 / 控制被改 ⇒ 全 FAIL(旧规则均放行)。**真实数据(11:47Z)**: king 与 DL 各 10,212 锚 **PASS**(控制复刻精确; 掩码集精确; 截断行 2,887; 无删锚; 最小掩码池 135), 收据 `FP2_receipts/MEMBER_RULE_CHECK_2026-09-17.json`。⇒ 在飞链的训练成员集**就是**规则集, 复审的四类反例在真实数据上不存在。运行器新增 `member_rule` 阶段, 决策装置绑定其收据。
- **R04/R05/R06/R08(P1)** 决策装置: formal profile 冻结(种子/窗/席位/δ/臂/年; 覆盖 ⇒ REFUSED_PROFILE; exploratory 永不建议); 身份闭包(表在 R 下且由 D 内装置写出、umask == 期望、臂记录 sha == 盘上现值; 出口收据在 R 下、臂相符、PASS 无败项、由 D 内出口门写出且 sha 在合同批准表、哈希 D 内合同、book/base 与表四书同路径同 sha; 成员规则收据 PASS 且 king meta == 出口门哈希的 bundle meta、DL targets == STEP1 哈希); 数值有限、lo ≤ hi、n > 0; 年份自首年到当前年连续且表达冻结上界。逐年表: 任一收益列非有限 ⇒ 臂 UNAVAILABLE; FSEED == 文件名种子; 掩码符号轴有序相等且覆盖全部锚; coverage 记录, 未达 UB ⇒ UNAVAILABLE。**G2 仍是逐年点估计规则, 不是逐年统计非劣证明**(报告措辞按此)。
- **R03(P1)** `check_scope` 执行批准: 运行中的门 sha == 合同变体 sha; 合同 `requires` 的每个 helper 盘上 sha == 记录值(缺 requires 拒跑)。合同 requires lib 刷新至 e98b15b0。驱动 `require` 的 `recorded_extras=1` 未加(登记: 需改 chain_v4_monthly.sh, 在本链跑完后随 K3 细化一起做)。
- **R07(P2)** verify-only 比对前次收据登记的**全部**产物(含 control_dl_report)。**R10** 运行器默认阶段到 decision。**R11** A0 重跑收据改为「rc 0 + ARMS_DONE + 每件工件由本次运行写出且 cfg.UMASK_NPZ == 本掩码」, 幂等复跑合法; `tests_build_dev_v4_mask` M4/M5 改共享收据键(5/5)。
- **R01/R02(P1, FP2-1)** `build_funding` 返回 namedtuple 并修 p9 调用处(AST 普查格); 重建覆盖改为按名×列×行实写掩码(哨兵观测), 有源无 v1 种子 ⇒ 三列 EMA = COPIED_NO_SEED, C2 只比实写格; 30/30。真实重建仍 PENDING。
- **E-0917-B**(与复审无关, 运行中发现): np 导出器原子写临时名被 numpy 补后缀 ⇒ np_export s42 rc 1; 修 + 回归 3/3; 运行器 3 从 np_export 重启。
- 本轮**未关**(登记): FP2-1 真实重建; driver `require` recorded_extras; K3 细化; `run_arm.sh` 入装置; 生命周期现金独立核账; F08 经济影响。

## AMENDMENT 11(2026-09-17 12:1xZ, 出数后: 结果只按 AMENDMENT 7 冻结规则读, 不改判据)
**书层结果(逐年表 `PER_YEAR_TABLE_2026-09-17_final.{json,md}`, RAW 口径, d30_n2_c42, L=2, 两臂同 tradable W24H 掩码, 判官同源臂记录)**:
- 配对 Δg = A1−A0(bps/锚/gross, dyn): W_ALPHA s42 **+0.057 [−0.043, +0.157]**(n 9,138); KING_LIVE s42 **+0.089 [−0.061, +0.252]**(n 5,838); W_ALPHA s2027 **+0.033 [−0.060, +0.131]**; KING_LIVE s2027 **+0.052 [−0.100, +0.211]**。逐年 Δg: 2022/2023 = 0(两臂同模型), 2024 −0.007/+0.002, 2025 +0.204/+0.117, 2026 +0.062/+0.030。
- **G1′ = UNDECIDED**: 四格上界均 > −δ(非 WORSE), 四格下界均 ≤ 0(非 BETTER), 只有 W_ALPHA s42 下界 −0.043 > −0.05, 其余三格下界 −0.061/−0.060/−0.100 < −δ ⇒ 非劣不成立。**G2 = True**(无一年 dg < −δ; 2026 在内)。**G3 = FAIL**(下)。⇒ 决策装置 `DECISION_FP2_2026-09-17_final.json`: **UNAVAILABLE(G3), 且即使 G3 通过也是 NO_SWAP(UNDECIDED)**。
- 水平(A0 在役形态, 同口径): W_ALPHA g +0.62/+0.66, Sharpe 逐锚 1.36/1.43, maxDD 逐锚 −40.6%/−41.0%; KING_LIVE g +1.17/+1.21, Sharpe 2.27/2.32, maxDD −22.8%/−25.3%; 2023 全年为负(−0.61/−0.55, Sharpe −1.9/−1.7); 2026 YTD +2.83/+2.87, Sharpe 4.47/4.50。A1 各窗略高(W_ALPHA +0.68/+0.69; KING_LIVE +1.26/+1.26)。**用户目标「各 regime Sharpe 显著 > 3」两臂均未达到**(2026 YTD 除外)。
**出口门(G3)**: 首跑 12:00Z FAIL E6/E8/E9(收据 `BUNDLE_export_v2_A1_FAIL_E6E8E9`)。E6/E9 = 合同仍钉九月机制(m1 掩码 47d87b51、九月 A0 书), FP2 §2.2 预注册的 tradable 机制没有写进合同 ⇒ **PROPOSED4**(只改 umask sha → 3badc4b6 与 baseline_books → A0 重跑四书, thresholds 不动; r1 值保留; pipeline 482/482)。重跑后只剩 **E8 K6**: fix 席位两书 gross_total > 1.000001(28–41 锚, 最大 1.026/1.032), A0 重跑的 fix 书同样超 1 ⇒ 这是 tradable 掩码下回放的**机制性质**(见下), 不是 A1 缺陷; 冻结门(do-not-touch)不能改, `gross_max` 不能看数改 ⇒ G3 卡住。
**新发现(受据 `OUTSIDE_MASK_PNL_2026-09-17.json`)**: scope m1 只缩成员/秩基, 不清持仓 ⇒ 八本书在 9,256/10,039 锚持有掩码 False 名权重(dyn 均值 ≈4%, fix ≈5%, 最大 9–12% gross); 这些格 99.7% 是冻结行(4h 收益 = 0), P&L 份额 0.50–0.57%, 两臂相同 ⇒ 配对差与水平基本不受影响, 但 gross 分母含卡住权重(g 略低估, 两臂同)且 fix 席位 gross 可超 1。逐年表脚注原写「(must be 0)」而未执行 —— 已改为如实语义。
**处置(待用户/独立研究员)**: (a) 换装: 按冻结规则 **不换**(UNDECIDED; 点估计全正但证据不足); (b) G3 卡点: 三选一 —— 新出口门版本把 E8/E9 限定到在役席位 dyn(需审批新门 sha); 或以「A0/A1 同现象」登记机制性质并让决策装置显式接受 fix 席位 K6 例外(需裁定); 或先做卡住权重精确会计再定。本方建议 (c)→(a): 先会计, 本轮不换装。

## AMENDMENT 12(2026-09-17 13:1xZ, 复审三轮 F1/F2/F3 + 用户字「回测应只看动态席位」⇒ PROPOSED5)
- **F1/F2/F3 已修**(943887eb, caa74331): 决策 v4 执行链自己的 `v4_gate_common.require(recorded_extras)`(出口 + STEP1), 成员规则收据全部输入现盘复哈希并按语义键绑定, 冻结窗自书轴重导(9,138 / 5,838); 终端收据 `_final_v2` 用稳定源码重新形成; F1 补丁单独归档, 错题 E-0917-C。
- **PROPOSED5(出口门 dyn 变体)**: 用户字 2026-09-17「线上的策略都是动态席位, 回测应该也是动态的」。新文件 `v4e_gate_export_fp2dyn.py`(9a61420c, 对 v2 d63f4ec3 的 5 处最小补丁, diff 收据 `FP2_receipts/diff_v4e_gate_export_v2_to_fp2dyn.patch`): 八本书仍全部加载、哈希、E5/E6/E7 与 28 名输入底线不变; **只有 E8/E9 的书内容判词只折算在役席位 dyn**, fix 席位结果照算照记(`informational_seat=True`), 阈值一个不动。依据: fix 席位是九月对照(E-0902-D: 当时回放动态席位 ≠ 实盘); v4 链回放动态席位与实盘一致(2026 均值 0.36–0.37 vs 实盘 0.36–0.38, AMENDMENT 11); tradable 掩码下 fix 书的 gross>1 是 A0/A1 同现象的机制性质。合同: `BUNDLE_export.approved_source_sha256 += 9a61420c` + `approved_variants` 条目(scope 2026-09 @ /workspace/fp2_2026-09); 驱动新增可选键 `GATE_EXPORT`(默认 v2), 本月合同 env 选该变体(env sha b7d0afa7 → f008eb38, 前身保留); 决策记录 `EXPORT_GATE` 并经 require 验其批准。**事后身份合同更正**, 提请独立研究员复审, 未审批前不作换装许可。
- 真实数据(pod2 12:5xZ 冒烟): 变体 PASS, E8 dyn ok / fix informational, E9 四书 median 0.9995–1.0025 带外 0。正式重跑见本节末尾附记。
- 结论仍为 **不换装**(G1′ UNDECIDED); PROPOSED5 只影响 G3 的状态, 不影响本轮结论。
