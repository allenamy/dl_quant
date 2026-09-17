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
