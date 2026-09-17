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
