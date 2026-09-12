> **创建:** 2026-09-12 | **Session:** W7(research-chain engineer, team-lead 派工; 承接 DESIGN_v4_monthly_chain_2026-09-12 §7 (i))| **状态:** PREREG 冻结(§0–§6 先于任何数字写成; §7 RESULT 事后追加, 追加前的本文 sha 记在 §7 首行)| **作废条件:** 冻结门源码 `v4_gate_step1.py` 278fdce6… / `v4_gate_step2.py` db7ab356… / `v4_gate_common.py` f8f4fc0e… 任一 sha 改变; 或合同 `ELIGIBILITY_CONTRACT.json` gates.STEP1/STEP2 的 approved 列表改为不含 278fdce6/db7ab356(参照对象随之失效); 或十月缓存不再是「九月 holefix2 正典 + 尾部追加」(§3.4 延伸尾定义失效)

# PREREG: v4 月度数据门(STEP1/STEP2)月通用化 — `v4_gate_step1_m.py` / `v4_gate_step2_m.py`

**一句话**: 九月冻结的两道数据门(合同批准 sha 278fdce6 / db7ab356)把九月路径与九月比对对象写死在源码里(DESIGN §7 (i)); 本文把每一处写死列成表, 给出**月通用定义**(路径来自月合同 env; 参照 = 上月合同钉死的产物; 新月尾部 = 延伸尾), **阈值与统计逐字不变**, 并在跑任何数字之前冻结验收判据 G1–G4。**不动**: 五个冻结文件一字不改(sha 事前事后实测); 合同不改(approved 列表增补 = 用户字, 见 §6 第 1 条); 驱动 `chain_v4_monthly.sh` / `chain_lib.sh` 不改(门经 `run_gate` 被调用时, `load_month_env` 已 `set -a` 导出全部合同键, 新门直接读 env)。

## §0 范围与不变式

| 项 | 内容 |
|---|---|
| 交付 | `v4_gate_step1_m.py`, `v4_gate_step2_m.py`(装置目录 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`); 对冻结源的 unified diff `receipts/monthly_chain_2026-09-12/w7_gates/v4_gate_step{1,2}_m.diff`; `tests_pipeline_gates.py` 新节 [R]; pod2 正控收据 `receipts/monthly_chain_2026-09-12/w7_gates/`; RUNBOOK §0★ 修订 4 |
| 冻结不动 | `v4_gate_step1.py` `v4_gate_step2.py` `v4_gate_common.py` `judge_v4.py` `ELIGIBILITY_CONTRACT.json`(sha 见 §7 事前/事后表) |
| 「逐字」的含义 | 新门 = 冻结源 + **只在 §1 表列出的行**做路径/参照通用化 + §3.4 延伸尾 + §3.5 参照≠候选拒绝 + §3.6 缺项拒绝; 其余每一行逐字相同(测试 [R] 用 difflib 断言: 被删的冻结行号集合 == 白名单; 阈值字面量出现次数相同) |
| 收据字段不变量 | **延伸尾豁免数为 0 时, 新门收据的判决字段集合与冻结门逐位相同**(九月正控即此情形 ⇒ G1 用 `compare_gate_receipts.py` 要求 0 差); 豁免数 > 0 时(十月)多出 §3.4 列出的条件字段, 记录豁免了多少 |
| 输入名 = 角色不是文件 | `finalize` 注册的输入名(`dlw_v4raw_targets` `dlw_hf3_targets` `dlw_hf2_targets` `fea82_hf3` `fea82_hf2` `fea82_v4raw` `fea89_f8v4` `fea89_f8hf2` `raw_patch` `hole_cells`; `wide_fea_v4` `wide_fea_v4_meta` `wide_fea_v2ext_clamp` `wide_fea_v2ext` `wide_fea_v2ext_meta` `hole_cells`)**逐字保留**: 它们是 `v4_gate_common.REQUIRED_INPUTS["STEP1@v4"/"STEP2"]` 的注册名, 驱动 `require_gate` 按这些名传路径; 改名 = 门的地板失效。十月时 `dlw_hf3_targets` 指 `$DLW_CLIP/data/dlw_targets.npz`(十月 CLIP), `dlw_hf2_targets` 指 `$PREV_DLW_CLIP/...`(九月 CLIP)。新增注册输入(`cache`, 见 §1)是 extras, `require` 允许 |

## §1 事实表: 冻结源里每一处写死(行号 = 冻结文件 `cat -n`)与月通用定义

### 1.1 `v4_gate_step1.py`(278fdce6)

| 行 | 写死内容 | 角色 | 月通用定义(env 键; 九月值 ⇒ 十月值) |
|---|---|---|---|
| L9 | `/workspace/review_scratch/holefix2_cells.npz` | 洞格/邻域(NEIGH, RUNS, CSYM) | `$HOLE_CELLS`(九月 `$R/holefix2_cells.npz` ⇒ 十月 `$R/TODO_holefix2_cells_2026-10.npz`) |
| L27 | `/workspace/dlw_v4raw/data/dlw_targets.npz`(A) | 本月 RAW 目标 | `$DLW_RAW/data/dlw_targets.npz` |
| L27 | `/workspace/dlw_hf3/data/dlw_targets.npz`(B) | 本月 CLIP 目标 | `$DLW_CLIP/data/dlw_targets.npz` |
| L32 | `/workspace/review_scratch/raw_patch.npz` | 本月原始收益补丁 | `$RAW_PATCH` |
| L53 | `/workspace/dlw_hf2/data/dlw_targets.npz`(C) | **参照** CLIP 目标(九月: holefix 上一代 hf2) | `$PREV_DLW_CLIP/data/dlw_targets.npz`(**新键**; 九月 `/workspace/dlw_hf2` ⇒ 十月 `/workspace/dlw_hf3` = 九月合同 `DLW_CLIP`) |
| L56 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz`(`ts[0]`) | 本月 5m 缓存(锚→缓存行) | `$CACHE`; 并**新增注册输入 `cache`**(冻结门只在轴不等分支读它却未登记) |
| L91 | `/workspace/dlw_hf3/data/dlw_fea82.npz` vs `/workspace/dlw_hf2/data/dlw_fea82.npz` | 本月 fea82 vs 参照 fea82 | `$DLW_CLIP/data/dlw_fea82.npz` vs `$PREV_DLW_CLIP/data/dlw_fea82.npz` |
| L92 | `/workspace/f8_v4/data/f8_fea89.npz` vs `/workspace/f8_hf2/data/f8_fea89.npz` | 本月 fea89 vs 参照 fea89 | `$F8/data/f8_fea89.npz` vs `$PREV_F8/data/f8_fea89.npz`(**新键**; 九月 `/workspace/f8_hf2` ⇒ 十月 `/workspace/f8_v4` = 九月合同 `F8`) |
| L99 | `/workspace/dlw_v4raw/data/dlw_fea82.npz` == `/workspace/dlw_hf3/data/dlw_fea82.npz`(sha) | RAW 树的 fea82 是 CLIP 树的逐位拷贝 | `$DLW_RAW/data/dlw_fea82.npz` vs `$DLW_CLIP/data/dlw_fea82.npz` |
| L104 | `os.environ.get("STEP1_OUT", "/workspace/review_scratch/v4_gates/step1.json")` | 收据路径 | `$STEP1_OUT` **必填, 无默认**(缺 ⇒ 打印 `STEP1_REFUSED` rc 3, 无收据) |
| L105–108 | 十个 inputs 的绝对路径 | 收据登记 | 同上各键; 另加 `cache=$CACHE` |
| L55–57 | 轴不等分支: `axis_only_hf3_outside_neigh` = 只在本月的锚落在邻域外的个数 | 比对对象 | **延伸尾豁免**(§3.4): 只在本月且 `E_ts > 参照末锚` 的锚不计入 `axis_only_hf3_outside_neigh`; 豁免数 > 0 时新增条件字段 `axis_only_hf3_tail_exempt`, `ref_axis_end_utc` |
| L76–78 | `pairs_only_a_outside_neigh`(只在本月的 (锚,币) 对落在邻域外) | 比对对象 | 延伸尾豁免: 对的锚 `E_row > 参照末 E_row` 者不计; 豁免数 > 0 时新增条件字段 `pairs_only_a_tail_exempt` |
| 无 | (无日期字面量) | — | — |

### 1.2 `v4_gate_step2.py`(db7ab356)

| 行 | 写死内容 | 角色 | 月通用定义 |
|---|---|---|---|
| L8 | `/workspace/review_scratch/holefix2_cells.npz` | 洞格/邻域 | `$HOLE_CELLS` |
| L14 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz`(`ts`) | 本月缓存(锚→行 `rows_of`) | `$CACHE`; 新增注册输入 `cache` |
| L15 | `/workspace/data/wide_fea_v4_meta.npz`(M4) | 本月 king meta | `$KING_META` |
| L15 | `/workspace/data/wide_fea_v2ext_meta.npz`(ME) | **参照** meta | `$PREV_META`(**既有键**; 九月 `/workspace/data/wide_fea_v2ext_meta.npz` ⇒ 十月 `/workspace/data/wide_fea_v4_meta.npz`, 模板已如此) |
| L27 | `/workspace/data/wide_fea_v4.npy`(F4) | 本月 king 特征(clamp) | `$KING_FEA` |
| L27 | `/workspace/data/wide_fea_v2ext_clamp.npy`(FC) | **参照** 特征(同构: clamp) | `$PREV_KING_FEA`(**新键**; 九月 `/workspace/data/wide_fea_v2ext_clamp.npy` ⇒ 十月 `/workspace/data/wide_fea_v4.npy` = 九月合同 `KING_FEA`) |
| L27 | `/workspace/data/wide_fea_v2ext.npy`(FE) | **参照未 clamp** 特征(E-0909-A clamp 检验的对照) | `$PREV_KING_FEA_UNCLAMPED`(**新键**; 九月 `/workspace/data/wide_fea_v2ext.npy` ⇒ 十月 **`NONE`**, 见 §3.3: 十月没有共参照轴的未 clamp 构建) |
| L20–22 | `anchors_only_v4_outside_neigh`(只在本月的锚落在邻域外) | 比对对象 | 延伸尾豁免(§3.4): `E_ts > 参照末锚` 者不计; 豁免数 > 0 时新增条件字段 `anchors_only_v4_tail_exempt`, `ref_axis_end_utc` |
| L23, L59 | `f138 = Erow < 8640`; `n_first138 == 138` | 公共轴上缓存行 < 8640 的锚恰 138 个(= 缓存起点不变 + 前 30 天锚数) | **逐字不变**。十月缓存若仍是同起点追加(§3.4 前提), 公共轴前段不变 ⇒ 仍 138; 若某月重建缓存改了起点, 本门合法地红, 须重新预注册而不是改数 |
| L48–50, L58 | `v4_vs_ext` / `clamp_vs_ext` 两组统计 | clamp 检验 | `PREV_KING_FEA_UNCLAMPED` 为路径时逐字不变; 为 `NONE` 时**不计算**, `features` 无这两组, 新增条件字段 `clamp_checks = "NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE"`, PASS 只由其余判据决定(§3.3) |
| L64 | `os.environ.get("STEP2_OUT", "/workspace/review_scratch/v4_gates/step2.json")` | 收据路径 | `$STEP2_OUT` 必填无默认 |
| L65–66 | 六个 inputs 绝对路径 | 收据登记 | 同上各键(`wide_fea_v2ext` 在 NONE 时登记为 None); 另加 `cache=$CACHE` |
| 无 | (无日期字面量) | — | — |

## §2 月合同键

**复用既有键**(已在 `chain_lib.sh V4_MONTH_KEYS` 41 键内, 驱动 `load_month_env` 已导出): `HOLE_CELLS` `RAW_PATCH` `CACHE` `DLW_RAW` `DLW_CLIP` `F8` `KING_FEA` `KING_META` `PREV_META`; 驱动传的 `STEP1_OUT` / `STEP2_OUT`。

**新键(4 个, 不可避免: 参照产物在合同里没有名字)**:

| 键 | 含义 | 九月值(正控) | 十月值(= 九月合同的对应键) |
|---|---|---|---|
| `PREV_DLW_CLIP` | 上月 CLIP 目标 + fea82 目录(STEP1 B 参照) | `/workspace/dlw_hf2` | `/workspace/dlw_hf3` |
| `PREV_F8` | 上月 fea89 目录(STEP1 B 参照) | `/workspace/f8_hf2` | `/workspace/f8_v4` |
| `PREV_KING_FEA` | 上月 king 特征 .npy(clamp 同构; STEP2 参照) | `/workspace/data/wide_fea_v2ext_clamp.npy` | `/workspace/data/wide_fea_v4.npy` |
| `PREV_KING_FEA_UNCLAMPED` | 与参照同轴的未 clamp 特征 .npy, 或字面 `NONE` | `/workspace/data/wide_fea_v2ext.npy` | `NONE`(§3.3; 用户字) |

- 冻结本文时这四个键**未**写入 `chain_lib.sh V4_MONTH_KEYS`、`v4_month_2026-09.env`、`v4_month_2026-10.env.template`(W3/lead 的文件); 新门自己对缺键拒绝(§3.6), 所以缺键不会静默。**事后(lead 指示, 2026-09-12, 见 §7.8)**: 四键已加入 `V4_MONTH_KEYS`(41→45)、九月合同(上表九月值)与十月模板(TODO 路径; `PREV_KING_FEA_UNCLAMPED=NONE` 带条件注释); 十月模板 `GATE_STEP1/2` 改指 `_m` 门; 九月合同 `GATE_STEP1/2` 仍指冻结门(合同只批准它们)。
- 为何不从 `PREV_BUNDLE`/`F8_EXT` 推导: bundle 不含全量特征矩阵; `DLW_EXT/F8_EXT` 语义是「年折在役代(merge 拼接源)」, 不是「上月」; 按文件名推导 = E-0825-H。

## §3 参照与延伸尾的定义(先于数字)

### 3.1 参照 = 上月合同钉死的产物
月 M 的 STEP1 B / STEP2 把月 M 的构建与**月 M−1 合同中同名键指向的文件**比对(十月: 九月 `DLW_CLIP`=/workspace/dlw_hf3, `F8`=/workspace/f8_v4, `KING_FEA`/`KING_META`=/workspace/data/wide_fea_v4*)。九月的参照是 holefix 上一代(hf2 / v2ext), 因为九月是首个 holefix2+clamp 月; 这一对参照就是冻结门写死的对象, 所以九月正控与冻结门读**同一组文件**。

### 3.2 公共轴上的判据逐字不变
在 `intersect1d(E_new, E_ref)` 上: members/y4s/y4old/qvk/YR4s/YRZ(STEP1)与 members/y4/qvk(STEP2 meta)差异只许落在洞邻域内, 值列差异只许在被填补的币; 特征对差异只许在洞邻域内(值列: 被填补币; 秩列: 任意币; AMENDMENT 1 item 3 的成员变动 NaN 形态例外照旧); 噪声带 1e-6 照旧。

### 3.3 clamp 检验(STEP2 `v4_vs_ext` / `clamp_vs_ext`)的月通用处理 — **研究员复核点 #1**
- 这两组统计验证 E-0909-A 的 clamp 修复只触及前 138 锚(E_row < 8640), 需要一份**与参照同轴的未 clamp 构建**。九月有(v2ext 未 clamp); 十月没有(链只产 clamp 构建, `pod_fea_ext_clamp.py` 无开关; 未 clamp 构建器 `pod_fea_ext_e.py` 不在链内)。
- 定义: `PREV_KING_FEA_UNCLAMPED` 为路径 ⇒ 两组统计逐字计算并进 PASS; 为字面 `NONE` ⇒ 不计算, 收据 `clamp_checks="NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE"`, `features` 只含 `v4_vs_clamp`, PASS 由其余判据决定。
- `NONE` 的可接受条件(写进 RUNBOOK 修订 4, 由用户字): 本月 `deps_preflight_device.json` 里 `pod_fea_ext_clamp.py` 的 sha 与九月正控相同(clamp 性质由构建器代码身份继承; 九月已用冻结门在真数据上验过 `clamp_vs_ext.outside_138 == 0`)。
- 替代方案(若研究员/用户要求每月真验): 数据阶段加一步用 `pod_fea_ext_e.py`(未 clamp)在本月缓存上再建一份, 作为本月的 `PREV_KING_FEA_UNCLAMPED`?? — **不成立**: 冻结门的 `clamp_vs_ext` 是「参照 clamp vs 参照未 clamp」(同一代数据), 换成「上月 clamp vs 本月未 clamp」会把数据变化混进 clamp 检验 ⇒ 若要每月真验, 需在**上月**留一份未 clamp 构建(十月做不到, 九月没留)。因此十月只有 `NONE` 一条路, 从十一月起可在合同里加「本月同时产未 clamp 构建」使下月可验; 是否这样做 = 用户裁定, 本文不预设。

### 3.4 延伸尾(extension tail)
- **前提**: 月 M 的 5m 缓存 = 月 M−1 缓存(holefix2 正典)+ 尾部追加(RUNBOOK §0★ 步 1「滚动补月」)⇒ 公共锚的 `E_row` 相同, 洞格 `neigh_rows` 的行号语义相同。前提破坏(重建缓存/改起点)⇒ 本门合法地红, 走重新预注册。
- **定义**: 只在本月出现且 `E_ts > max(E_ref)`(锚)/ `E_row > max(E_row_ref)`(特征对)的锚/对 = 延伸尾 = 本月的新数据。它们没有参照可比, 由 A 部分(RAW vs CLIP)与 `F10_GATE_{RAW,CLIP}.json` 身份收据把关, **不**由参照比对把关。
- **规则**: 延伸尾**不计入** `axis_only_hf3_outside_neigh` / `pairs_only_a_outside_neigh`(STEP1)与 `anchors_only_v4_outside_neigh`(STEP2); 其余只在本月的锚/对(早于参照起点, 或在参照跨度内却不在参照轴上)照旧必须落在邻域内。
- **只在参照的锚/对**(`axis_only_hf2` / `pairs_only_b` / `anchors_only_v2ext`)不豁免: 本月丢锚/丢对仍须在邻域内解释。
- **豁免数**(= 冻结规则会计入而本规则不计入的个数, 即「邻域外 ∧ 延伸尾」)**为 0 时收据字段集合与冻结门相同**; > 0 时新增条件字段(§1 表)。九月: STEP2 只在 v4 的 6 个锚(2026-08-31 00–20Z)位于邻域内 ⇒ 豁免 0; STEP1 B 轴相等 ⇒ 豁免 0; fea 对 `pairs_only_a_outside_neigh=0` ⇒ 豁免 0 ⇒ **G1 可用 0 差要求**。
- **已知风险(十月首跑可能合法地红, 先写下读法)**: 参照轴末端 ≤48 根 5m bar 内的锚, 其 y4s/y4/YR4s/YRZ 标签在上月可能因数据未到而 NaN/截断, 本月补齐后在公共轴上出现「参照尾部标签补全」差异, 邻域外 ⇒ FAIL。本门**不**为此豁免(阈值/统计不变); 若十月因此红, 差异必须被证明全部落在 `E_row > max(E_row_ref) − 48` 的锚上, 再以 AMENDMENT 显式落墨, 不在本轮预设。

### 3.5 参照 ≠ 候选(新增拒绝)
参照文件与候选文件内容相同(sha256 相等)⇒ 比对什么也不验证 ⇒ 拒绝(rc 3, 收据 PASS=false, `REFUSED.reference_is_candidate` 点名哪对)。检查的对: STEP1 `DLW_CLIP` vs `PREV_DLW_CLIP` 的 targets 与 fea82, `F8` vs `PREV_F8` 的 fea89; STEP2 `KING_FEA` vs `PREV_KING_FEA`, `KING_FEA` vs `PREV_KING_FEA_UNCLAMPED`, `PREV_KING_FEA` vs `PREV_KING_FEA_UNCLAMPED`(后两对在 NONE 时不查), `KING_META` vs `PREV_META`。**不**查 `DLW_RAW` vs `DLW_CLIP`(补丁为空的月两者合法相同, A 部分的统计会如实报 0)。

### 3.6 缺项拒绝(G2 的机制)
任何 np.load 之前: 解析全部键; 缺键/空值/文件不存在 ⇒ `finalize(<gate>, {"PASS": False, "REFUSED": {"missing_env": [...], "missing_files": {键: 路径}}}, $STEPx_OUT, inputs)` ⇒ rc 3, 收据 PASS=false, 缺失文件 sha 记 None(这样的收据永不能过 `require`)。`STEPx_OUT` 本身缺 ⇒ 无处写收据: 打印 `STEPx_REFUSED missing STEPx_OUT` rc 3。冻结源内部的 `assert`(符号表对不上、形状对不上)**继承为崩溃**: rc 1、无收据 — 也不是 PASS, 但不「干净」; 列入 §6 未做。

## §4 阈值与统计(逐字, 不变)
- 邻域: `holefix2_cells.npz` 的 `neigh_rows`(上游按 `[run_start−48, run_end+8640]` 生成)与 `fill_runs`/`row`/`col`(被填补币集合按 run)。
- STEP1 A: 补丁窗 `E_row ∈ [t−48, t−1]`; 大差 `> 1e-6`; 噪声 `≤ 1e-6`; `YR4s`/`YRZ` 行级差同 1e-6 带。PASS = 九个逐位字段全 True ∧ `y4s_finite_pattern_equal` ∧ `y4s_big_outside_patch_windows == 0` ∧ `y4s_noise_max_outside_patch ≤ 1e-6` ∧ `YR4s/YRZ_diff_rows_outside_patch_rows == 0`。
- STEP1 B targets: 差 `> 1e-6`(含有限性形态不同); PASS = `members_diff_rows_outside_neigh == 0` ∧ 五列 `*_diff_outside_neigh == 0` ∧ 三值列 `*_diff_symbol_not_filled == 0` ∧ (`E_ts_equal` ∨ `axis_only_hf3_outside_neigh == 0`)。
- STEP1 B fea82/fea89: `CH = 200000`; PASS = `pairs_only_a_outside_neigh == 0` ∧ `pairs_only_b_outside_neigh == 0` ∧ `diff_pairs_outside_neigh == 0` ∧ `valuecol_diff_symbol_not_filled == 0`。
- STEP1 总 PASS = A ∧ B targets ∧ B fea82 ∧ B fea89 ∧ `fea82_copy_identical`。
- STEP2: `CH = 128`; `f138 = E_row < 8640`; PASS = `v4_vs_clamp.outside == 0` ∧ `v4_vs_clamp.val_sym_bad == 0` ∧ [`v4_vs_ext.outside_138_and_neigh == 0` ∧ `clamp_vs_ext.outside_138 == 0`](NONE 时不评) ∧ `members_diff_rows_outside_neigh == 0` ∧ y4/qvk `*_diff_outside_neigh == 0` ∧ `*_diff_symbol_not_filled == 0` ∧ `n_first138 == 138` ∧ `anchors_only_v4_outside_neigh == 0` ∧ `anchors_only_v2ext_outside_neigh == 0`。
- 退出码: PASS ⇒ 0, 否则 3(`finalize` 不变)。

## §5 验收判据(冻结; 跑任何东西之前)

| 门 | 判据 | 装置 / 命令 | 通过条件 |
|---|---|---|---|
| **G1** 九月正控 | 新门在九月合同路径上复现归档收据的**判决字段** | pod2, CPU, 隔离目录 `/workspace/w7_gates_2026-09-12/`(device 副本 + root), 只读九月产物, `/workspace/review_scratch` 零写入; env 逐字见 §7 转录; 回传后 `compare_gate_receipts.py <归档> <新> <out.json>` 对 W3 的 `pod2_root/step{1,2}.json` **与** 09-09 原档 `receipts/step{1,2}.json` 各比一次 | STEP1: 78 个判决字段全等, 0 差, **PASS=false 两边**(AMENDMENT 3 trend_288 缺陷, 期望字面 FAIL, rc 3); STEP2: 31 个全等, 0 差, PASS=true 两边, rc 0。GPU 事前事后 `0 %, 2 MiB`; PID 333197/339489 `ps -o pid,stat` 事前事后同为 `Tl` |
| **G2** 十月模板拒绝 | 对十月模板的 TODO 路径 / 缺新键, 门干净拒绝 | 本地测试 [R](合成; env 按模板取值 + 四新键缺/TODO)+ 直接跑一次新门于模板 env | rc 3; 收据 `PASS=false` 且 `REFUSED` 点名每个缺键与不存在路径; 无任何收据声称 PASS; stdout 含 `STEP1_REFUSED`/`STEP2_REFUSED` |
| **G3** 突变 | 把某路径指向「错月」文件, 判决改变或被拒 | 本地测试 [R] 合成夹具(两个「月世界」: 世界 X 与其延伸月 X+1, 以及独立世界 Y) | 每个突变具名: (a) 参照指向候选自身 ⇒ REFUSED reference_is_candidate; (b) 参照指向世界 Y ⇒ PASS 变 false(邻域外差 > 0); (c) `HOLE_CELLS` 指向世界 Y 的洞格 ⇒ PASS 变 false; (d) `KING_FEA` 指向参照 ⇒ REFUSED; (e) 缺一键 ⇒ REFUSED 点名; (f) TODO 路径 ⇒ REFUSED 点名; (g) STEP2 `PREV_KING_FEA_UNCLAMPED=NONE` ⇒ PASS 可为 true 且收据带 `clamp_checks=NOT_EVALUATED…`、`features` 无 v4_vs_ext/clamp_vs_ext; (h) 延伸月夹具 ⇒ PASS true 且条件字段 `*_tail_exempt` 出现且等于尾锚/尾对数; (i) 无延伸夹具 ⇒ 收据判决字段集合 == 归档九月收据的字段集合(递归) |
| **G4** 身份与地板 | `self_sha256` 记录; 全部输入 sha 登记; `require` 在合同批准后即可接受 | 收据字段检查 + pod2 上用**临时副本合同**(隔离目录内 `device_sim/`, 把新门 sha 加入 approved 列表的副本, 真合同不动)跑 `v4_gate_common.py require` | 真合同下: `REQUIRE_FAIL … not an APPROVED source`(预期, 未批准); 副本合同下: STEP2 `REQUIRE_OK`(2 输入 + 注册地板 STEP2), STEP1 `REQUIRE_FAIL receipt says PASS=False`(门本身红, 与九月一致); 新门收据 `inputs_sha256` 覆盖 `REQUIRED_INPUTS["STEP1@v4"]` / `["STEP2"]` 全部名且非 None |
| **G0** 静态 | 冻结不动 + 差异只在白名单 | 测试 [R] 静态格 | 冻结门 sha == 278fdce6…/db7ab356…; `v4_gate_common` 的 `finalize` 签名与 `REQUIRED_INPUTS["STEP1@v4"/"STEP2"]` 名单不变; 合同 approved 含 278fdce6/db7ab356; 保存的 .diff == difflib 现算; 被删冻结行号集合 == §1 白名单; 阈值字面量(`1e-6`, `- 48`, `8640`, `== 138`, `200000`, `CH = 128`)在新门中出现次数 == 冻结门 |

全套 `tests_pipeline_gates.py`(/usr/bin/python3)须 ALL PASS(基线 228 格 + [R]); `make_sha_manifest.py` rc 0。

## §6 不做 / 未验 / 待裁(诚实清单)
1. **合同 approved 列表增补 = 用户字**(本任务不编辑 `ELIGIBILITY_CONTRACT.json`); 增补前 preflight 会以「NOT approved」拒绝十月合同 `GATE_STEP1=v4_gate_step1_m.py` — 属有意。
2. ~~四个新键未入 `V4_MONTH_KEYS` / 两份合同文件~~ — 已按 lead 指示加入(§7.8); 驱动 preflight 的 `PF_INPUTS` 固定名单未加 PREV_*(`NONE` 不是路径; 缺失由门自己拒绝), 属有意。
3. §3.3 `NONE` 是显式跳过两组 clamp 统计的开关, 只应由合同(用户字)写入; 研究员复核点 #1。
4. §3.4 参照尾部标签补全风险未在真数据上验(十月才有); 读法已写, 不预设豁免。
5. 冻结 `assert` 继承为 rc 1 崩溃(无收据): 符号表不等、特征形状不等、`names` 不等、公共轴 searchsorted 失配。干净化需改冻结行, 本轮不做。
6. 十月真数据未跑(不存在); G1 只能证「九月上与冻结门同判」, G3 只能在合成夹具上证「错月会红/被拒」。
7. 不检验 `PREV_*` 真是「上月」(门看不见日历); 由合同与 preflight 钉 sha 负责。
8. 新门注册的 `cache` 输入让收据多 hash 一个 2.09 GB 文件(实测秒级); 未纳入 `REQUIRED_INPUTS` 地板(那是 `v4_gate_common.py` 的改动, 冻结不动)。

## AMENDMENT 1(2026-09-12, W7; 独立研究员复核 B-R4 + B-R1/B-R3/R5 派工; **先于任何再跑写成**, 本文追加前 sha 见 §7.9)

**触发**: 研究员 `PROBE_W7_RESULTS.json` 两格: (a) `W7_NONE_positive_without_any_builder_or_preflight_identity` — `NONE` 只是 env 字串, §3.3 的「构建器 sha 相同」前提没有落到程序; (b) `W7_entire_new_tail_NaN_still_PASS_boundary` — 30 个新尾锚全 NaN 仍 PASS(尾部只被豁免、没有质量门)。

### A1.1 `NONE` 绑定构建器身份(STEP2_m)
- 新合同键 **`PREV_CLAMP_BUILDER_SHA256`**(46 键): 九月 = 冻结 STEP2 门在九月真数据上验过 clamp 性质时的 `pod_fea_ext_clamp.py` sha = `b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac`(`receipts/monthly_chain_2026-09-12/pod2_root/preflight.json` device_sha256 与 `device_sha256_pod2.txt` 同值); 十月 = 同值(构建器改了 = 新 PREREG, 不是改这个值)。
- `PREV_KING_FEA_UNCLAMPED=NONE` 时门**必须**: ① 读 `$R/v4_gates/deps_preflight_device.json`(本月 preflight 钉的装置 sha), 取键以 `/pod_fea_ext_clamp.py` 结尾的条目; ② 算门所在目录的 `pod_fea_ext_clamp.py` 现值 sha; ③ 三者(合同钉值 / preflight 钉值 / 现值)**全等**, 否则 `REFUSED.clamp_builder_identity` 点名哪个缺/哪个不等(rc 3, PASS=false 收据)。收据 `clamp_checks` 由字串改为 dict: `{mode: "NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE", builder, pinned_sha256, preflight_pinned_sha256, device_file_sha256, preflight_deps_receipt}`。非 NONE 时不读这些(九月正控路径不变)。
- 边界(明写): 这绑的是「构建器代码身份 = 九月验过的那份」, 不是重新验 clamp 性质; 重新验需要上月留未 clamp 构建(§3.3)。

### A1.2 新尾质量门(STEP2_m; 尾 = §3.4 定义: 只在本月且 `E_ts > max(E_ref)` 的锚)
- **统计**: 每个尾锚 a 的 **成员格有限比例** `ff(a) = mean(isfinite(F4[a][members(a), :]))`(members 来自本月 KING_META; 82 列全算)与 `n_members(a)`。
- **判据(冻结)**: 每个尾锚 `n_members(a) ≥ 1` ∧ `ff(a) ≥ 0.90`。收据字段 `tail_quality = {n_tail_anchors, member_finite_frac_min, member_finite_frac_median, n_members_min, floor: 0.90, ok}`; **有尾锚即出现**(不论豁免数), 进 PASS。
- **校准数据(九月参照, 只读 pod2 2026-09-12 14:4xZ, 未看任何十月数据)**: `wide_fea_v4.npy` (10182, 829, 82) 逐锚成员格有限比例: 分位 {0: 0.9756, 1: 0.9756, 5: 1.0, 50: 1.0, 95: 1.0, 100: 1.0}; 最低 0.9756 = 80/82(轴首 8 锚与轴末 5 锚各缺 2 列); 成员数 135–400; 全币格有限比例 0.16–0.48 随成员数变化, **不可作绝对地板**(故用成员格)。0.90 与实测最低值 0.9756 之间留 ≈6 个 NaN 列的余量; 全 NaN 尾(ff=0)、半死尾(ff=0.5)必红; 合成夹具 NF=10 时 1 列 NaN(0.90)过、2 列 NaN(0.80)红。
- **对 G1 的修订**: 九月 v4 相对 v2ext 有 6 个尾锚(2026-08-31 00–20Z)⇒ 九月正控的 STEP2 收据**多一个字段 `tail_quality`** ⇒ `compare_gate_receipts.py` 预期 **31 个判决字段全等 + 恰 1 差(`tail_quality` missing_in_archived)**, PASS=true 两边; STEP1 不变(78/0)。§0「豁免数 0 ⇒ 字段集合相同」的不变量据此修正为「除 `tail_quality` 外相同」。
- 预期九月值(先写后看): 6 尾锚 ff = 五个 0.9756 + 一个 1.0 或全 0.9756 ⇒ min ≈ 0.9756 ≥ 0.90 ⇒ ok。若实测不符, 按实测报, 不改地板。

### A1.3 同批(研究员 B-R1 / B-R3 / R5, 非门源码; 装置见 §7.9)
- B-R1: 驱动每阶段先 `prereq_*`(preflight 收据绑本合同 sha 与根; 上游收据/标记; pin_deps 身份; refit 侧车 fix7+输入同一; END 行数)再 guard/dispatch, 失败 `FAIL_<stage>_prereq_<name>` rc 3。
- B-R3: `load_month_env` 要求 46 键**出现在文件里**且先 `unset` 再 source; 数据阶段五个子进程 `env -i` + 白名单 + 逐变量显式(CLIP `DLWT_RAW_PATCH=` 空)。
- R5: 五个旧链脚本首行守卫 `V4_LEGACY_OK=1`, 否则 rc 64 `LEGACY_REFUSED`。
- 验收: 自检新节 [S]; 研究员 13+8 探针格中预期翻转: `W3_refit_subset_dispatches_without_upstream_receipts`、`W3_omitted_SEEDS_inherited_ACCEPTED`、`W3_CLIP_command_inherits_ambient_RAW_PATCH`、`W7_NONE_positive_without_any_builder_or_preflight_identity`、`W7_entire_new_tail_NaN_still_PASS_boundary`(5 格); F9/W4 七格与 `W7_*` 其余四格不变。

## §7 RESULT(2026-09-12 事后追加; 追加前(§0–§6 冻结时)本文 sha = `2290f191c59e11b33576d8cfe5b4b2bdef776c731f5dcea17914582a0b298f8f`, 先于任何门运行实测)

### 7.1 冻结文件 sha(事前 = 开工时 `shasum -a 256`; 事后 = 全部工作结束后再测, 见 7.7)
| 文件 | 事前 | 事后 |
|---|---|---|
| `v4_gate_step1.py` | 278fdce611e91571d24ec26c78ddc4620668bfd4598a01f577f1f6887dd62be4 | 同 |
| `v4_gate_step2.py` | db7ab3561f97423a8d5dd74251257adcedd743129d22a07d7cd186d102dd80d8 | 同 |
| `v4_gate_common.py` | f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12 | 同(W7 收工时); **随后 W4 同日并行改动 → 24e813f145c3…**(非 W7; pod2 两轮正控用的是 f8f4fc0e 副本) |
| `judge_v4.py` | f6850dc3215fc38624ea6152e96b248727b7c4ff1acec4b6bf6e642aa1873809 | 同(W7 收工时); **随后 W4 并行改动 → c2a81c48f037…**(非 W7) |
| `ELIGIBILITY_CONTRACT.json` | 1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732 | 同 |

### 7.2 新文件(装置目录 `v4_chain_2026-09-09/` 与 `receipts/monthly_chain_2026-09-12/w7_gates/`)
| 文件 | sha256(前 12) | 说明 |
|---|---|---|
| `v4_gate_step1_m.py` | 79950786271e | 由 `make_gates_m.py` 从冻结源逐行替换生成; 删 15 行(= §1.1 白名单 L9,27,32,53,56,57,78,91,92,99,104–108), 加 36 行(全带 `# [M]`) |
| `v4_gate_step2_m.py` | 455e3df4c195 → **0fe5ec5573f3**(AMENDMENT 1) | 删 14 行(= §1.2 白名单 L8,14,15,22,27,28,36,48,49,50,58,64,65,66), 加 37 → 61 行(NONE 身份绑定 + tail_quality) |
| `w7_gates/v4_gate_step{1,2}_m.diff` | — | `difflib.unified_diff(n=0)`; 自检 [R] 现算相等 |
| `w7_gates/make_gates_m.py` | — | 生成器(拒绝非冻结 sha 的源) |
| `w7_gates/run_w7_positive_control.sh` | bda109d84e75 | pod2 正控转录(逐字复跑用) |
| `tests_pipeline_gates.py` 新节 [R] | — | 49 格; 旧格未改 |

### 7.3 G0 静态(自检 [R] 实测)
删行集合 == 白名单(15 / 14); 加行 36 / 37 全带 `# [M]`; 阈值字面量出现次数相等(STEP1: `1e-6` `t - 48` `t - 1` `200000` `8640`; STEP2: `< 8640` `== 138` `CH = 128` `% 2048`); 新门内无 `/workspace/review_scratch|dlw_|f8_|data/` 字面路径, 无 `os.environ.get(<键>, <默认>)`; `v4_gate_common.finalize` 签名与 `REQUIRED_INPUTS["STEP1@v4"/"STEP2"]` 名单不变; 合同 approved 含 278fdce6/db7ab356 且不含新门 sha。

### 7.4 G1 九月正控(pod2, 2026-09-12T13:48:36Z → 13:49:47Z; 收据 `w7_gates/pod2_root/`; 转录 `w7_commands.txt`)
- 调用形态 = 驱动的: `chain_lib.sh load_month_env v4_month_2026-09.env` + 四新键 export + `run_gate STEP1 v4_gate_step1_m.py … STEP1_OUT=…` / `run_gate STEP2 …`(`CHAIN_DEVICE_DIR=/workspace/w7_gates_2026-09-12/device`, `L` 重指隔离根; `review_scratch` 三文件 ls 事前==事后)。装置副本 4 文件 sha 与本地逐位相等(`device_sha256_w7.txt`)。
- **STEP1: rc 3, PASS=false**(AMENDMENT 3 trend_288 字面 FAIL, 与 09-09 归档一致); `compare_gate_receipts.py` 对 W3 `pod2_root/step1.json`: **78 判决字段全等, 0 差**(`parity_STEP1_vs_W3_pod2root.json`); 对 09-09 原档 `receipts/step1.json`: **78 / 0**(`parity_STEP1_vs_archived_0909.json`)。
- **STEP2: rc 0, PASS=true**; 对 W3: **31 / 0**; 对 09-09 原档: **31 / 0**。
- 收据输入 sha 与归档逐位相同(STEP1 十个: d1976cf6 720f03a4 9495d128 40608701 62499db1 40608701 f7363889 e36cd545 adecf276 6156f97a; STEP2 六个: 268f6c9c 12ea42c4 0b1194f1 f88b0720 4b1b6047 6156f97a)+ 新注册 `cache` 1d7f459dee43(两门同); 无 None; `self_sha256` = 运行时文件 sha(79950786 / 455e3df4)。
- 收据字段集合与冻结门相同(无 `*_tail_exempt` / `clamp_checks`): 九月豁免数 0(§3.4 预言成立: STEP2 只在 v4 的 6 锚在邻域内; STEP1 B 轴相等)。
- GPU `0 %, 2 MiB` 事前/事后; PID 333197 / 339489 `Tl` 事前/事后(`nvidia_{before,after}.txt`, `paused_pids_{before,after}.txt`)。耗时 STEP1 32.4 s, STEP2 23.6 s(+ 输入 hash)。

### 7.5 G2 / G3(本地合成夹具, 自检 [R]; 全部 OK)
- G2: 十月模板 env(TODO 路径, 新键缺): STEP1 rc 3 `STEP1_REFUSED`, 收据 PASS=false, `REFUSED.missing_env == [PREV_DLW_CLIP, PREV_F8]`, `missing_files` 点名 TODO 路径(hole_cells/cache/…), 输入 sha 全 None; STEP2 同型 `[PREV_KING_FEA, PREV_KING_FEA_UNCLAMPED]`; 缺 `STEP1_OUT` ⇒ rc 3 无收据; 拒绝收据永不能过 `require`(rc 3)。
- G3(每项具名): (a) 参照=候选 ⇒ REFUSED `dlw_hf3_targets==dlw_hf2_targets, fea82_hf3==fea82_hf2`, 不比对; (b) `PREV_DLW_CLIP`→世界 Y ⇒ B targets/fea82 邻域外差 >0 ⇒ PASS false; (b′) `PREV_F8`→Y ⇒ 只 fea89 红; (b) STEP2 `PREV_KING_FEA`→Y ⇒ `v4_vs_clamp.outside>0` ∧ `clamp_vs_ext.outside_138>0`; (b″) `PREV_META`→Y ⇒ y4 邻域外差; (c) `HOLE_CELLS`→Y 的洞格 ⇒ 真差落邻域外 ⇒ FAIL; (d) STEP2 `KING_FEA`→参照 ⇒ REFUSED `wide_fea_v4==wide_fea_v2ext_clamp`; (d′) `PREV_META`→本月 meta ⇒ REFUSED; (e) 缺 `PREV_F8` ⇒ REFUSED 点名 + `fea89_f8hf2: None`; (e′) `PREV_KING_FEA_UNCLAMPED` 空(非 NONE)⇒ REFUSED; (f) TODO 路径 ⇒ REFUSED 只点名该对; (g) `NONE` ⇒ PASS 且 `clamp_checks=NOT_EVALUATED…`, `features` 只含 `v4_vs_clamp`, `wide_fea_v2ext` sha None; (g′) NONE + 参照→Y ⇒ PASS false(NONE 不遮数据检验); (h) 延伸月夹具(230 vs 200 锚)⇒ PASS, `axis_only_hf3_tail_exempt=30`, `pairs_only_a_tail_exempt=180`, `anchors_only_v4_tail_exempt=30`, `n_first138=138`; (i) 无延伸夹具 ⇒ 判决字段集合(递归)== 归档九月收据(78 / 31 字段名); 尾规则反例: 早于参照起点的新锚(行 1968)不豁免 ⇒ `anchors_only_v4_outside_neigh=1` ⇒ FAIL; 驱动 `run_gate` 形态下两门 rc 0。

### 7.6 G4 身份与地板
- 真合同(pod2 `require_real_step{1,2}.txt`): `REQUIRE_FAIL gate source 79950786271e / 455e3df4c195 is not an APPROVED source …`(预期; 批准 = 用户字)。
- 合同**副本**(pod2 `/workspace/w7_gates_2026-09-12/device_sim/`, approved 列表增两 sha, 状态字段标 SIMULATION COPY; 回传为 `pod2_root/ELIGIBILITY_CONTRACT.SIMULATION_COPY_do_not_use.json`, sha bc984c6bc4be): STEP2 `REQUIRE_OK PASS (… self 455e3df4c195 approved, 2 inputs verified, registered floor STEP2=2)`; STEP1 `REQUIRE_FAIL receipt says PASS=False`(门本身红)。真合同 sha 事后仍 1188267adf42(`contract_real_vs_sim_sha.txt`)。
- 自检 [R] 同型: 真合同拒 / 副本合同 STEP1@v4 地板 4 输入 `REQUIRE_OK`。

### 7.7 全套自检 + 清单
- `/usr/bin/python3 tests_pipeline_gates.py`: **ALL PASS (278 checks)** = 基线 228(开工实测 ALL PASS)+ [R] 50(§7.8 后再跑; §7.8 前为 277 = 228 + 49); 日志 `receipts/monthly_chain_2026-09-12/tests_pipeline_gates_w7.log`。
- `make_sha_manifest.py`: rc 0, n_files 97(含两新门), missing_sources/receipts 空, sha_verified 4。

### 7.8 事后追加(lead 指示 2026-09-12: 合同 schema 收口, 由 W7 执行)
- `chain_lib.sh` `V4_MONTH_KEYS` 41→45(+`PREV_DLW_CLIP PREV_F8 PREV_KING_FEA PREV_KING_FEA_UNCLAMPED`); `load_month_env` 因此对缺任一新键 rc 4。
- `v4_month_2026-09.env` +4 行 = §2 九月值(与 pod2 正控 export 的逐字相同); `GATE_STEP1/2` 仍 = 冻结门。
- `v4_month_2026-10.env.template`: `GATE_STEP1=v4_gate_step1_m.py` `GATE_STEP2=v4_gate_step2_m.py`(preflight 在合同批准前以 NOT approved 拒绝, 有意); `PREV_DLW_CLIP=/workspace/TODO_dlw_hf3` `PREV_F8=/workspace/TODO_f8_v4` `PREV_KING_FEA=/workspace/data/TODO_wide_fea_v4.npy` `PREV_KING_FEA_UNCLAMPED=NONE`(注释: 仅在修订 4 条件下、用户字)。
- 自检: [P] 键数格 41→45(+四键名), 模板格改断言 `GATE_STEP1=v4_gate_step1_m.py`, `_fake_root` 合同 +4 键; [R] +1 格「模板原样 ⇒ 两门因 TODO 路径拒绝, 无 missing_env, NONE 不算缺文件」。驱动 `chain_v4_monthly.sh` 未改。

### 7.9 AMENDMENT 1 + 研究员 B-R1/B-R3/B-R4/R5 收口(2026-09-12, W7; 追加前本文 sha `4a407f2bcd84d569…` = AMENDMENT 1 写成、任何再跑之前)
**改动(file:line, 装置目录 `v4_chain_2026-09-09/`)**:
- `v4_gate_step2_m.py` → sha `0fe5ec5573f346969d9d3448c3e424f2ebc8b7c192cefe4313a05cdf84c09007`(由 `w7_gates/make_gates_m.py` 再生; 删的冻结行仍是 14 行白名单, 加行 61 全带 `# [M]`, 阈值字面量计数不变, 自检 [R] G0 复验): 头块 NONE 身份绑定(读 `$R/v4_gates/deps_preflight_device.json` 的 `pod_fea_ext_clamp.py` 钉值 + 门旁文件现值 + `PREV_CLAMP_BUILDER_SHA256`, 三者不等 ⇒ `REFUSED.clamp_builder_identity`), 冻结 L52 后插入 `tail_quality`(每尾锚成员格有限比例 ≥ 0.90 ∧ 成员 ≥ 1), PASS 行并入。`v4_gate_step1_m.py` 不变(79950786…)。
- `chain_lib.sh`(sha `3cd82956833e…`): `V4_MONTH_KEYS` 45→46(+`PREV_CLAMP_BUILDER_SHA256`); `load_month_env` 要求每键**出现在文件里**(`grep -oE '^[A-Z_][A-Z0-9_]*='`)并 `unset $V4_MONTH_KEYS V4_MONTH_ENV` 后再 source(B-R3); 新增 `prereq_receipt / prereq_marker / prereq_file / prereq_json_eq / prereq_deps_identity / prereq_refit_sidecar / prereq_count`(失败 `FAIL_<stage>_prereq_<name>` rc 3, 理由同时写 say 日志与 stderr)与 `clean_env`(白名单 PATH HOME LANG LC_ALL TMPDIR VIRTUAL_ENV LD_LIBRARY_PATH OMP/MKL/OPENBLAS_NUM_THREADS PYTHONDONTWRITEBYTECODE CUDA_VISIBLE_DEVICES)。
- `chain_v4_monthly.sh`(sha `c6ea34fa0131…`): 每阶段 `if want X; then` 之后、`guard X` 之前加前置: cache←preflight; data←preflight+cache_coverage 收据+缓存 sha 同一; gates←preflight+F10_GATE_{RAW,CLIP} 存在+targets/fea89 sha 同一; king←preflight+step2; legs←preflight+step1(+require_gate 绑本月 RAW); mwf←preflight+step1+legs 标记; refit←preflight+step1(require)+legs 标记/文件+每种子 MERGE_DONE+`deps_v4_monthly_mwf.json` 身份(legs/fea89/RAW targets/CLIP targets/fea82/训练器); arms←preflight+step2(require)+BUNDLE_DONE/PRED+每种子 refit 侧车(fix7, env_given 绑本月 DLW_RAW/F8, inputs_sha256 与 pt_sha256 同一); judge←preflight+DEV_V4_DONE+ARMS_DONE(无 ARMS_FAIL)+END rc=0 行 ≥ 2×种子; export←preflight+JUDGE_V4_DONE+JUDGE_v4.json+ARMS/BUNDLE 标记。数据阶段五个子进程改 `env -i "${CLEAN_ENV[@]}" <逐变量显式> "$PY" …`, CLIP 行 `DLWT_RAW_PATCH=` 显式为空(子进程读的全部变量已枚举: DLWT_CACHE/PANEL/OUT/RET_CH/RAW_PATCH; F171_CACHE/PANEL/OUT; F8_DLW/CACHE/OUT; CACHE_IN/PANEL_IN/FEA_OUT/META_OUT)。
- 五个旧链脚本首行守卫(R5): `chain_v4_data.sh` L6 / `chain_v4_gpu3.sh` L9 / `chain_v4s_gpu.sh` L12 / `chain_king_e.sh` L4 / `chain_v4_post_export.sh` L9: `[ "${V4_LEGACY_OK:-}" = 1 ] || { echo LEGACY_REFUSED … >&2; exit 64; }`; `.rN_*.sh` 快照不动。
- 合同: `v4_month_2026-09.env` + `PREV_CLAMP_BUILDER_SHA256=b9f9c728…`; 模板同(注释写明 NONE 的条件由门执行); [P] 键数格 46, `_fake_root` +1 键。
**收据**:
- pod2 r2(CPU, 隔离 `root_r2`, 转录 `w7_gates/run_w7_positive_control_r2.sh` sha f41bd4b0…; 2026-09-12T15:00:38Z→15:01:11Z): STEP2_m 0fe5ec55 **PASS rc 0**; `compare_gate_receipts.py` vs W3 `pod2_root/step2.json`: **31 判决字段全等 + 恰 1 差 `tail_quality` missing_in_archived**(= AMENDMENT 1 预言, `parity_STEP2_r2_vs_W3_pod2root.json`); `tail_quality = {n_tail_anchors 6, member_finite_frac_min 0.9756, median 0.9756, n_members_min 400, floor 0.9, ok true}`(预言「五个 0.9756 + 一个 1.0 或全 0.9756」⇒ 实测全 0.9756); 收据 7 输入全有 sha; 真合同 `REQUIRE_FAIL … not an APPROVED source`(0fe5ec55 未批准, 预期); 合同副本 `REQUIRE_OK … registered floor STEP2=2`; 真合同 sha 仍 1188267a; GPU `0 %, 2 MiB` 前后; PID 333197/339489 `Tl` 前后; review_scratch ls 前==后。收据目录 `w7_gates/pod2_root_r2/`。STEP1_m 未再跑(源码未变)。
- 自检: `tests_pipeline_gates.py` **ALL PASS (328 checks)**(= 278 + [S] 45 + 并行 W3 新增的 [P] 格; W7 未改旧格, 仅 [J] 传 `V4_LEGACY_OK=1`、[P] 键数格 45→46 与 `_fake_root` +1 键、[R] 两格 NONE 改带身份、[R] 一格 regex 收窄为「非空默认」); 日志 `receipts/monthly_chain_2026-09-12/tests_pipeline_gates_w7.log` + 同名 `.SHA256SUMS`(运行时各文件 sha)。`make_sha_manifest.py` rc 0。
- 研究员探针复跑(`w7_gates/researcher_probes_live/`, 探针指向现装置, 夹具函数按名定位): **翻转 5 格**(W7): `W3_refit_subset_dispatches_without_upstream_receipts` True→False; `W3_omitted_SEEDS_inherited_ACCEPTED` 0→4; `W3_CLIP_command_inherits_ambient_RAW_PATCH` 'stale-inherited-patch'→(研究员 mock 在 env -i 下失去 PROBE_LOG 而无记录; W7 [S] 同型格实测 CLIP 子进程 `DLWT_RAW_PATCH=''`); `W7_NONE_positive_without_any_builder_or_preflight_identity` PASS→REFUSED; `W7_entire_new_tail_NaN_still_PASS_boundary` PASS→FAIL(研究员 env 无钉值故先被身份拒绝; 带钉值的尾质量红见 [S])。**另 1 格由 W4 并行改动翻转**(非 W7): `W4_changed_receipt_extra_omitted_by_caller_ACCEPTED` True→False。其余 15 格不变。
**未做/边界**: 驱动 preflight 的 `PF_INPUTS` 未加 PREV_*(NONE 非路径; 缺失由门拒绝); mwf/refit/arms/judge/export 五阶段的前置只在合成根上证「缺则停、齐则派」, 真数据全链仍未跑(DESIGN §7 (ii)); `env -i` 只施于数据阶段(GPU 阶段的 torch/CUDA 环境不敢清); 旧链 `.rN_*.sh` 快照与 `chain_fea89_stable.sh` / `chain_v4_gpu2.sh` 未加守卫(lead 未点名; 快照按纪律不动); 合同批准仍 = 用户字(0fe5ec55 取代 455e3df4)。
