# RUNBOOK: 宽书月度重训+换装 v2(2026-10 执行用; 定稿于 09-01 首跑收官)

> **创建:** 2026-09-01 | **Session:** 6737834a(重训战役)| **修订:** 2026-09-12(§0★ 唯一执行步骤单 = v4 口径; §2–§4 降为历史; 用户字 09-12)| **状态:** 待执行(10-01 前后), **执行只按 §0★** | **作废条件:** 被更新月版取代或 combo 方案退役
> 首跑全受据: `multi_asset/exports/research/retrain_2026-09/MANIFEST.md`(脚本×机器×门表+偏差D1-D5)+ `journal_2026-09-01_retrain_king_v3.md` + PREREG addendum(c24b8d2f)+ AMENDMENT A1(d2d20f5)。
> **脚本单一真相源 = `multi_asset/exports/research/retrain_2026-09/`(git); pod/jpline 上只放运行副本。**

## §0★ 唯一执行步骤单(v4 口径, 2026-09-12 定稿; 用户字 09-12「既然 v4 已经确定是正确口径, 10 月 runbook 为什么还不修」)

> **★ 修订 3(2026-09-12 W3, 见本节末「§0★ 修订 3」): 下表的逐步手工命令自本修订起由单一驱动 `chain_v4_monthly.sh <v4_month_<YYYY-MM>.env>` 接管**(装置目录 `v4_chain_2026-09-09/`; 月配置合同 `v4_month_2026-09.env` = 九月正控, `v4_month_2026-10.env.template` = 十月模板; 负控 `chain_v4_monthly_dryrun.sh`)。**十月重训只允许经驱动执行**; 下表保留为各阶段的「做什么/门」说明, 表中命令不再单独手抄(修订 2 已证手抄会漏 env)。设计与收据: `docs/DESIGN_v4_monthly_chain_2026-09-12.md`。**仍开(十月前必须裁定)**: STEP1/STEP2 门源码被合同冻结且写死九月比对对象, 十月需新门源码 + 合同批准(用户字); 见 DESIGN §6。
> **本节取代 §2–§4(那三节自 2026-09-12 起只作 09-01 v3 首跑的历史记录, 不再执行)。** 命令逐字抄装置目录 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`(git 单源; pod 上只放运行副本 `R=/workspace/review_scratch`), 每步先过门再下一步, 门红即停。装置 sha **一律现场实测**(修订 6 删除了原先冻在这里的六个值: 到 2026-09-16 已 6/6 不成立): `python3 v4_gate_common.py sha <file>`; 已提交的清单见装置目录 `SHA256SUMS*`(`make_sha_manifest.py` 生成)。

| 步 | 做什么 | 命令 / 装置(逐字) | 门(红即停) |
|---|---|---|---|
| 0 | pod 环境 + 装置同步 + 本月钉子 | `bash /workspace/pod_env_bootstrap.sh`; rsync 装置目录 → `$R`; **live_pins.json 每月重抄**自在役 `~/wide_shadow/shadow_bundle/config.json`(symbols_live / keep_names); 基线 json = 上月 own fold IC(`slow_scorer_v4base.json` 型) | 装置 sha 与 git 单源逐文件相等 |
| 1 | **5m 缓存** = holefix2 正典 + 滚动补月; 原始收益补丁 `raw_patch.npz` 随缓存走 | 补月后 `$PY $R/cache_coverage_gate_v2.py`(排除首末日) | **洞 0 / 宽缺口 0** 才过 |
| 2 | **数据层**(CPU ≈40 分): RAW 目标 → fea82 → fea89 → king v4 特征(clamp) | `bash $R/chain_v4_data.sh`(内: `DLWT_CACHE=<holefix2> DLWT_PANEL=<本月 v3splice> DLWT_OUT=/workspace/dlw_v4raw DLWT_RET_CH=0 DLWT_RAW_PATCH=$R/raw_patch.npz $PY pod_dlw_targets_raw.py` → `F171_CACHE=… F171_OUT=/workspace/dlw_hf3 $PY pod_dlw_features_ext.py` → `F8_DLW=/workspace/dlw_hf3 F8_CACHE=… F8_OUT=/workspace/f8_v4 $PY pod_f8_build_ext.py build` → `CACHE_IN=… PANEL_IN=/workspace/data/wide_panel_4h_v2ext.npz FEA_OUT=/workspace/data/wide_fea_v4.npy META_OUT=/workspace/data/wide_fea_v4_meta.npz $PY pod_fea_ext_clamp.py`); 每步 rc 与每次 cp 都被检查, 终点 `CHAIN_V4_DATA_DONE` | `v4_gate_step1.py`(RAW vs CLIP 差异只在补丁窗, **邻域外差异必须为 0**)+ `v4_gate_step2.py`(king 特征差异只在缓存改动邻域); 收据 `$R/v4_gates/step1.json` / `step2.json` 必须是本链 self_sha 的 PASS |
| 2b | (候选, 待用户字)fea89 稳定 trend: `pod_f8_build_stable.py` + `v4_gate_closure.py`(G2, 五输入含 hole_cells) | `bash $R/chain_v4s_gpu.sh` 型 | G2_closure PASS |
| 3 | **legs**: 在役训练 legs 行逐位原样 + 新锚同公式(**禁全行重算**, AMENDMENT 5) | `$PY $R/pod_legs_v4b.py` → `/workspace/f8_v4/data/f10v2_legs.npz` | 自检分年 WL: 2023 king ≈0.59 |
| 4 | **F10**(GPU ≈5.5h 四链; 生产只需 RAW × s42, 判官加 s2027): 月折 FIX7 `BEST_EP_FIX=7 EMBARGO=1` 20 折 202501.. 4 分片 → merge → refit | `bash $R/chain_v4_gpu3.sh`(内: `require_gate step1.json gate=STEP1 profile=v4 self_sha=$(gate_sha v4_gate_step1.py) …` + `require_gate step2.json gate=STEP2 …` + `pin_deps` + `run_shards launch_mwf_v4b.sh RAW 42` … + `merge_mwf_v4b.py` 要 `MERGE_DONE`)→ `$PY $R/pod_f10_refit_v4.py`(FIX7) | 门 V1 np≡torch(`jp_v4_np_check.py` ≤1e-5); V3′ 无未来峰 + 谱形 \|Δ\|≤0.03 参照 = 同配方上一代月折; 折外泄出 = 0 |
| 5 | **king 导出**: env **逐字** | `env BUNDLE_OUT=/workspace/shadow_bundle_v4_<月> BUNDLE_BASE=<上代 own fold IC json> BUNDLE_FEA=/workspace/data/wide_fea_v4.npy BUNDLE_META=/workspace/data/wide_fea_v4_meta.npz EXPORT_PANEL=<本月 splice> EMA_STATE_JSON=<canoncont> LIVE_PINS=/workspace/live_pins.json $PY $R/pod_export_bundle_v4.py`(要 `BUNDLE_DONE`); **`provenance.generation` 标签改本代**(v4_2026-10) | 门②折 IC / 门③ ic26 / 守卫带 2.27–2.57(`guard_reconcile_v4e.py` 先复现上代发表值 2.284); 红先复现基线再报 |
| 6 | **书层量化**(dev_v4 树, meta y4 原始记账): 臂 A1(新) vs A0(在役) dyn/fix × s42/s2027 | `bash $R/run_v4_arms.sh A1` → `JUDGE_OUT=$R/v4_gates/JUDGE_v4.json $PY $R/judge_v4.py`(要 `JUDGE_V4_DONE`; 判官先复现已发表 A0 数字) | (A) 双种子 CI 下界 >0 ⇒ 候选; (C)+门全绿 ⇒ 仍呈候选(措辞「未过否决线 + 口径正确」); (B) 或任一门红 ⇒ 不换 |
| 7 | **出口门**(资格合同 `BUNDLE_export`): v2 门 gate + require | `env … V4CHAIN_DIR=<冻结合同目录> EXPORT_ARM=A1 BUNDLE_OUT=<步 5 输出> JUDGE_HC=… $PY infra2/v4e_gate_export_v2.py` → `… require <receipt>`(r20 `run_pod2_positive.sh` 的 env 逐字) | PASS + REQUIRE_OK; 合同 `gates.BUNDLE_export.approved_source_sha256` 必须含 v2 门 sha(**2026-09-12 起应用 PROPOSED2, 见 STATE**) |
| 8 | **换装**(仅在用户对具体 bundle sha 给字后): 锚间静默窗; 备份旧 bundle(目录 + tar); 原子换; sidecar A2 平价; `acceptance.py` ALL_GREEN; 首锚验收写 journal; STATE 一行 | 同 §3-3 / §4-8 的动词 | 任一门红 ⇒ 不换, 影子继续旧 bundle |
| 9 | 入档: RESULT + receipts(`$R/v4_gates/*.json`, `deps_*.json`)+ MANIFEST sha; memory | — | — |

**易错项(全部咬过)**: NpzFile[key] 不进循环; pgrep 用 `[c]hain` 括号法; 一切 sha 由复跑实测; 过程状态只读过程收据; ssh 全内联(zsh 不分词); `pod_fea_ext.py`(未 clamp)/ `pod_export_bundle_v3.py` / `pod_legs_ext.py` 全行重算 **一律不再用**。

### §0★ 修订 2(2026-09-12 10:0xZ; 独立研究员复审 0dfc0d87 R1–R5 全部接受)
**修订 1 的步骤单不可照抄执行**(研究员实测): ① 第 4 步裸 `pod_f10_refit_v4.py` 的默认是 `F10_DLW=/workspace/dlw_ext` / `F10_OUT=/workspace/f8_ext` / `BEST_EP_FIX=-1`(argmax); launcher 子 shell 里的 `BEST_EP_FIX=7` **不会回传父 shell** ⇒ 裸调用会读旧输入、选 argmax、覆盖旧 `f8_ext/models/f10_live_s42.pt`。② 训练器 `pod_f10_train_monthly_v4.py` L298 `ALL_MONTHS = 202501..202608` 硬编码白名单, `merge_mwf_v4b.py` L13 同; 202609 被拒。③ 第 3 步 `pod_legs_v4b.py` 需 4 个必需 env(`LEGS_TG / LEGS_META / LEGS_PRED / LEGS_OUT`), 且 legs 要用**本月新 king PRED** ⇒ king 导出必须先于 legs。④ 导出器 `pod_export_bundle_v4.py` L241 `generation` 硬编码 "v3_2026-09"。⑤ 链脚本 `R=/workspace/review_scratch` 硬编码, 外层无法换根。⑥ refit 记录的 `trained_through` 是全池末锚, 不是模型真正看过的末条 loss 标签(R1 附)。

**因此 §0★ 表的第 3/4/5 步按下表执行(显式 env, 不依赖任何继承)**; 并且**下面三处代码改动在十月前必须先落地、各带自己的门与研究员复核**, 否则十月重训**不得开始**:

| 步 | 逐字命令(env 显式) |
|---|---|
| 5→3 顺序 | **先 king 导出(得到本月 SLOW PRED), 再 legs, 再 F10** |
| 3 legs | `LEGS_TG=/workspace/dlw_v4raw/data/dlw_targets.npz LEGS_META=/workspace/data/wide_fea_v4_meta.npz LEGS_PRED=<本月 king SLOW PRED .npy> LEGS_OUT=/workspace/f8_v4/data/f10v2_legs.npz $PY $R/pod_legs_v4b.py`(自检 2023 king WL ≈ 0.59 必须打印) |
| 4a F10 月折 | `bash $R/chain_v4_gpu3.sh`(launcher 内已显式 `F10_DLW=$DLW F10_OUT=/workspace/f8_v4 EMBARGO=1 BEST_EP_FIX=7 MONTHS=$M`; 四片 MONTHS 必须覆盖到**本月**, 见代码改动 (a)) |
| 4b F10 refit(部署件) | `F10_DLW=/workspace/dlw_v4raw F10_OUT=/workspace/f8_v4 SEED=42 BEST_EP_FIX=7 $PY $R/pod_f10_refit_v4.py`(**四个 env 逐字, 缺一不跑**); 产物 `f8_v4/models/f10_live_s42.pt` + 报告里 `best_ep_rule` 必须读 `fix7` |
| 5 king 导出 | 修订 1 的 env + `BUNDLE_GENERATION=v4_2026-10`(见代码改动 (b)) |

**十月前必做的代码改动(链装置目录, git 单源; 每项: 改动 + 正控(复现九月产物逐位)+ 负控(本月空目录 / 缺 env 必须 rc≠0)+ 研究员复核)**:
- (a) `pod_f10_train_monthly_v4.py` / `merge_mwf_v4b.py`: 月白名单改为 env `MONTHS_ALL`(缺省 = 数据轴内到上月末的全部月), 拒绝越过数据末锚的月; 四片 `SH0..SH3` 由 `MONTHS_ALL` 生成而不是手写。
- (b) `pod_export_bundle_v4.py`: `provenance.generation` 从 env `BUNDLE_GENERATION` 读(缺省拒绝导出, 不再写死 "v3_2026-09"); 同时把 king 训练数据末锚(真正的梯度截止)写进 provenance, 不以构建日代替。
- (c) `chain_lib.sh` / `chain_v4_data.sh` / `chain_v4_gpu3.sh` / `launch_mwf_v4b.sh`: 根目录 `R`、`dlw_v4raw`、`f8_v4` 等从一份**本月配置文件**读(`v4_month.env`, 内容 = 本月路径与月集合), 缺文件 rc≠0; 提供 `chain_v4_monthly_dryrun.sh`: 对空本月目录必须在第一道门停下(负控收据)。
- 完成前, 十月重训的正确姿势 = **不做**; 若届时未完成, 影子继续跑 09-01 bundle(在役模型腿在正确口径下 (C) 不可区分, 见 CALIBER_STATUS 09-09)。

### §0★ 修订 3(2026-09-12, W3; 修订 2 的三处代码改动 (a)(b)(c) 已落地, 研究员复核待做; 设计+收据 `docs/DESIGN_v4_monthly_chain_2026-09-12.md`)
**执行姿势(十月)**: 在 pod 上把装置目录整目录拷为 `D`(git 单源 `v4_chain_2026-09-09/` 逐文件 sha 相等), 准备本月根 `R`(与九月 `/workspace/review_scratch` 完全分离), 填好 `v4_month_2026-10.env`(从 `v4_month_2026-10.env.template` 复制, 每个 `TODO_` 都换成真实路径), 然后**只跑一条命令**:
```bash
bash $D/chain_v4_monthly.sh $D/v4_month_2026-10.env          # 阶段: preflight → cache → data → gates → king → legs → mwf → refit → arms → judge → export
```
- 每阶段 rc + 完成标记/收据都被检查; 任一失败写 `FAIL_<原因>` 到 `$R/v4_commands.txt` 并 rc≠0; **只有整链全绿才写 `$R/v4_gates/MONTHLY_DONE.json`**(子集运行写 `MONTHLY_STAGES_DONE.json`, DONE=false)。
- **顺序修正**(修订 2 ③): king 导出在 legs 之前, legs 的 `LEGS_PRED` = 本月 `$BUNDLE_OUT/slow_pred_pinned.npy`; refit 的四个 env 由驱动显式传(`F10_DLW F10_OUT SEED BEST_EP_FIX=7`, 另 `EMBARGO=1` 记档), 裸调用会被 `pod_f10_refit_v4.py` 拒绝(rc 2)。
- **月集合**: `MONTHS_ALL` 写在合同里; 驱动在 mwf 前用 `v4_months.py check` 对目标轴断言(越过数据末完整月 ⇒ 拒绝); 四片 `SH0..SH3` 由 `MONTHS_ALL` 轮转生成(九月常量 ⇒ 与手写四片逐位相同, 测试 [N])。
- **generation**: `BUNDLE_GENERATION` 必填(缺 ⇒ 导出器 rc 2); provenance 另记 `king_train_end_utc`(booster 真正的梯度截止 = 标签年 <2026 的最后锚, **月度导出不推进它**)与 `built_utc` 分离。
- **负控**(每次改装置后必跑): `bash $D/chain_v4_monthly_dryrun.sh $D/v4_month_2026-10.env` ⇒ 必须 `DRYRUN_PASS`(空根在 preflight 停, 0 训练启动)。
- **正控**: `V4_STAGES=preflight,gates bash $D/chain_v4_monthly.sh <九月合同(R 改隔离根)>` 在九月数据上复现 STEP1(PASS=false, 与 09-09 收据同数)/ STEP2(PASS=true 同数), 驱动因 STEP1 红而停 — 驱动不比门更绿。
- **判官第七轮(2026-09-12 lead, F9)**: `judge_v4.py` 自绑 `eligibility_contract` = 它自己读的合同(此前调用方给路径); 前身 `judge_v4.r4_7f1aa5d6.py`; 自检节 [Q]; 见 `docs/DESIGN_judge_floor_28_2026-09-12.md` §8。步 8 判官命令不变。
- **仍开, 十月前必裁**: (i) STEP1/STEP2 门源码被资格合同冻结(`278fdce6` / `db7ab356`), 内部写死九月路径与九月比对对象(hf3 vs hf2; v4 vs v2ext) ⇒ 十月需新门源码(env 定位 + 滚动参照)+ 复核 + 合同批准(用户字); 模板里 `GATE_STEP1/2=TODO_…` 使 preflight 拒绝, 属有意; **承接: W7 `docs/PREREG_v4_gates_monthly_2026-09-12.md`(`v4_gate_step1_m.py`/`v4_gate_step2_m.py`), 批准后填进月合同即接入驱动。**(ii) 十月 `SIGNAL_RECEIPT` 需先由 `gate_signal_parity_v2.py` 为本月臂产出。(iii) `HC` 隔离副本须含合同钉死的 A0 基线书四件。(iv) 九月数据上 STEP1 字面 FAIL(trend_288 全局累积和, AMENDMENT 3; 稳定 trend 候选待用户字)⇒ 全链正控在九月数据上到 gates 为止。

### §0★ 修订 4(2026-09-12, W7; 十月数据门源码已就位, **待研究员复核 + 用户字批准入合同**; 预注册+收据 `docs/PREREG_v4_gates_monthly_2026-09-12.md`)
修订 3「仍开 (i)」的门源码已写成: `v4_gate_step1_m.py`(sha `79950786271e…`)/ `v4_gate_step2_m.py`(sha `0fe5ec5573f3…`, 同日 AMENDMENT 1 后; 此前 `455e3df4c195…` 的九月正控见 w7_gates/pod2_root), 装置目录内, = 冻结门 `v4_gate_step1.py` 278fdce6 / `v4_gate_step2.py` db7ab356 **只改路径/参照/延伸尾的 15/14 行**(diff `receipts/monthly_chain_2026-09-12/w7_gates/v4_gate_step{1,2}_m.diff`, 每新行带 `# [M]`; 阈值/统计逐字, 自检 [R] 断言)。九月正控(pod2, CPU, 隔离目录 `/workspace/w7_gates_2026-09-12/`, 收据 `receipts/monthly_chain_2026-09-12/w7_gates/pod2_root/`): STEP1 **78 判决字段 0 差, PASS=false 两边**(AMENDMENT 3 字面 FAIL, 与 09-09 归档一致); STEP2 **31 字段 0 差, PASS=true**; GPU 0 %/2 MiB 前后。

**十月合同(`v4_month_2026-10.env`)必须设**(逐字; 前两行替换模板的 `TODO_` 门行, 后四行是**新键**, 门自身对缺键拒绝 rc 3):
```
GATE_STEP1=v4_gate_step1_m.py
GATE_STEP2=v4_gate_step2_m.py
PREV_DLW_CLIP=/workspace/dlw_hf3                              # 上月(九月合同 DLW_CLIP)的 CLIP 目标 + fea82 目录 = STEP1 B 参照
PREV_F8=/workspace/f8_v4                                      # 上月(九月合同 F8)的 fea89 = STEP1 B 参照
PREV_KING_FEA=/workspace/data/wide_fea_v4.npy                 # 上月(九月合同 KING_FEA)的 king 特征 = STEP2 参照(PREV_META 模板已指九月 wide_fea_v4_meta.npz)
PREV_KING_FEA_UNCLAMPED=NONE                                  # 十月没有共参照轴的未 clamp 构建 ⇒ 字面 NONE = 显式跳过 v4_vs_ext/clamp_vs_ext 两组 clamp 统计(收据记 clamp_checks=NOT_EVALUATED); 用户字, 条件 = 本月 deps_preflight_device.json 里 pod_fea_ext_clamp.py sha 与九月相同
PREV_CLAMP_BUILDER_SHA256=b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac   # AMENDMENT 1 (B-R4): 上一行的条件由门自己执行 — NONE 时门读本月 deps_preflight_device.json 的 pod_fea_ext_clamp.py 钉值与门旁文件现值, 三者须 == 此值, 否则 REFUSED clamp_builder_identity
```
(九月正控用的值: `PREV_DLW_CLIP=/workspace/dlw_hf2 PREV_F8=/workspace/f8_hf2 PREV_KING_FEA=/workspace/data/wide_fea_v2ext_clamp.npy PREV_KING_FEA_UNCLAMPED=/workspace/data/wide_fea_v2ext.npy`, 即冻结门写死的对象。)**已落地(lead 指示, 同日)**: 四键已入 `chain_lib.sh V4_MONTH_KEYS`(41→45, 缺键 ⇒ `load_month_env` rc 4)、`v4_month_2026-09.env`(九月值)、`v4_month_2026-10.env.template`(上面六行原样, TODO 待换真路径); 九月合同 `GATE_STEP1/2` 仍指冻结门(合同只批准它们)。驱动 preflight 的 `PF_INPUTS` 未加 PREV_*(`NONE` 不是路径), 缺失由门自己拒绝。

- **合同批准 = 用户字**: `ELIGIBILITY_CONTRACT.json` 的 `gates.STEP1.approved_source_sha256` 须增补 `79950786271e690a24c72bc189b20e65eab6271164c1e582dff72b799db00163`, `gates.STEP2.approved_source_sha256` 增补 `0fe5ec5573f346969d9d3448c3e424f2ebc8b7c192cefe4313a05cdf84c09007`(AMENDMENT 1 版; 不是先前的 455e3df4…), **在独立研究员复核 PREREG §1–§3 之后、由用户下字**; W7 未编辑合同。增补前: preflight 对十月合同报 `gate source NOT approved`(有意); `require` 对新门收据报 `not an APPROVED source`(pod2 实测 `require_real_step{1,2}.txt`); 增补后无需改驱动(pod2 上用合同副本模拟: STEP2 `REQUIRE_OK … registered floor STEP2=2`, `require_sim_step2.txt`; 自检 [R] 同型)。
- **同日研究员复核 B-R1/B-R3/B-R4/R5 的收口(W7, PREREG AMENDMENT 1 + §7.9)**: ① 驱动每阶段先 `prereq_*`(preflight 收据绑本合同 sha/根、上游收据/标记、pin_deps 身份、refit 侧车 fix7+输入同一、END 行数)再 guard/dispatch, 失败 `FAIL_<stage>_prereq_<name>` rc 3 — `V4_STAGES=refit` 之类子集再不能跳门; ② `load_month_env` 要求 46 键**出现在文件里**并先 `unset` 再 source, 数据阶段五个子进程 `env -i` + 白名单 + 逐变量显式(CLIP `DLWT_RAW_PATCH=` 空); ③ STEP2_m 的 `NONE` 绑构建器身份(上表 `PREV_CLAMP_BUILDER_SHA256`)且每个新尾锚成员格有限比例 ≥ 0.90(`tail_quality`, 进 PASS; 九月正控因 6 个尾锚多出该字段 ⇒ 对账预期 31 等 + 1 差); ④ 五个旧链脚本(`chain_v4_data.sh` `chain_v4_gpu3.sh` `chain_v4s_gpu.sh` `chain_king_e.sh` `chain_v4_post_export.sh`)首行守卫 `V4_LEGACY_OK=1`, 否则 rc 64 `LEGACY_REFUSED` 什么也不做。
- **研究员复核点**: ① §3.3 `NONE` 开关(clamp 检验在十月不可评, 只能靠构建器 sha 继承, 现由门核身份); ② §3.4 延伸尾定义(只在本月且晚于参照末锚的锚/对不计入邻域外计数; 早于参照起点者不豁免, 自检有反例); ③ §3.5 参照≠候选拒绝; ④ 输入名 `dlw_hf3_targets`/`dlw_hf2_targets`/`wide_fea_v2ext*` 是注册角色名, 十月指本月/上月文件(不改名, 否则 `REQUIRED_INPUTS` 地板失效)。
- **十月首跑已知风险**(PREREG §3.4): 参照轴末 ≤48 bar 的标签补全差异会让 STEP1 B / STEP2 meta 合法地红; 门不豁免; 若红, 差异须被证明全落在 `E_row > max(E_row_ref) − 48` 的锚, 再以 AMENDMENT 落墨。
- 自检: `tests_pipeline_gates.py` 新节 [R] 50 格 + [S] 45 格(全套 328 ALL PASS, `receipts/monthly_chain_2026-09-12/tests_pipeline_gates_w7.log` + `.SHA256SUMS`); 复跑正控命令逐字 = `receipts/monthly_chain_2026-09-12/w7_gates/run_w7_positive_control.sh`(r1: 两门, 455e3df4 版 STEP2)与 `run_w7_positive_control_r2.sh`(r2: STEP2_m 0fe5ec55, 收据 `w7_gates/pod2_root_r2/`, 对账 31 等 + 恰 1 差 `tail_quality` 如预注册)。

### §0★ 修订 5(2026-09-13, W7b; 独立研究员 `docs/REVIEW_code_and_research_2026-09-13.md` §3.D 四项定向收口; 设计 DESIGN §9 + PREREG AMENDMENT 2/§3.7 + 收据 `v4_chain_2026-09-09/receipts/round3_2026-09-13/`)

**对十月执行的净影响: 门更严, 步骤不变, 合同要多写一行也不用改。** 三处改码 + 一处只写字, 每处都有一个「跑归档旧源就会红」的自检格(新节 [T], 旧源以 `.r1_<sha8>` 存在装置目录)。

1. **refit 侧车前置(arms 之前)现在证明「这份 JSON 说的是谁」**: 旧版只要有一份 JSON 就放行 —— 删掉 `pt_sha256` 键、把四个输入缩成一个、把 **seed-42** 侧车放进 **seed-2027** 槽位, 三种坏状态都过。现在核: 期望种子(`seed` / `env_given.SEED` / `.pt` 路径 / 侧车文件名四者一致)、完整键集(缺一即拒, 永不「缺了就跳过」)、本月合同的期望路径(逐字节相同但放在别的树下的副本 ⇒ 拒)、`.pt` 与四个输入的**实际 sha 当场重算**, 外加侧车 `self_sha256` == 本次调度的 `pod_f10_refit_v4.py`。**边界(引用时必须带)**: arms 消费的是月度预测 `.npy`, 没有任何证据表明错误的 `.pt` 被用于真实预测 —— 这是一条没兑现的 resume-gate 承诺, 不是一次被证明的坏训练。**执行影响**: 若某月只重跑 `V4_STAGES=arms` 而 refit 是别的装置版本跑的, 现在会 rc 3 点名; 正确动作是重跑 refit, 不是放宽门。
2. **STEP2_m 新尾成员索引先验结构再验比例**: `members=[-1]` 曾被 numpy 当成末列、拿满分 PASS。现在先核「1-D / 整数 / 在 `[0, NW)` / 无重复」, 非法索引**绝不**用作下标(负值会静默环绕, 越界会崩成 rc 1 无收据)。收据多一个 `member_index_ok`(有尾即出现)与 `member_index_bad`(仅非空时)。**九月真数据正控(pod2)**: 6 个尾锚各 400 个成员全部合法 ⇒ `member_index_ok=true`, 其余 `tail_quality` 与上一轮逐位相同, PASS rc 0 不变 —— 新规则不误伤真数据。**0.90 的射程**: 它只是**有限格门**, 不是因果性、不是预测有效性、不是成员身份正确性(PREREG §3.7)。
3. **月合同的值现在也绑在文件里**: 46 键「出现在文件里」不等于值来自文件 —— `SEEDS=$UNLISTED_SEEDS` 是文件的一行, 但由父环境填入(实测旧版 rc 0、SEEDS=2027)。新规则: **值里的变量引用只许指向本文件更早定义过的合同键**, 其余(非合同名 / 前向引用 / `${外部名}` / 裸 `$`)rc 4 点名。**写十月合同时注意**: `$R/...` 照旧可用(R 必须在该行之前定义, 模板已如此); 不要引用任何不在 `V4_MONTH_KEYS` 里的名字。
4. **判官定位器(`JUDGE_ELIGIBILITY`)本轮不动行为**: caller 显式给出同字节备份路径时, 已变的原路径仍可能被跳过。**月度 export 路线不受影响**(驱动把收据自己的全量 `inputs_path` 原样交判官), 反例只在手写 caller 时成立。闭包条件与最小绑定提案见 DESIGN §9.4, **待用户/lead 裁定**; 在裁定之前, 不得声称「判官 ≡ standalone gate 的全闭包」。

**门源码 sha 变更(合同批准增补时用新值)**: `v4_gate_step2_m.py` `0fe5ec5573f3…` → **`b2f9cfd40b9e356536184a63e202aa9d2a48228be5145bcd81665fb5f7df24e9`**; `v4_gate_step1_m.py` **不变** `79950786271e…`。合同 `ELIGIBILITY_CONTRACT.json` 仍是 `1188267a…`(未编辑, 批准 = 用户字)。自检全套 **ALL PASS (354 checks)**; `make_sha_manifest.py` rc 0。

### §0★ 修订 6(2026-09-16, FX-TRAIN; AUDIT_TRAIN 7e1ecf9a TRN-27 / TRN-15 / TRN-16; 事实表 `docs/fixprogram_2026-09-13/FX_TRAIN/FACT_TABLE_TRN.md` §TRN-27)

**为什么有这一节**: 修订 4 让用户批准 `0fe5ec55…`, 修订 5 改成 `b2f9cfd4…`, 而磁盘上的件从 2026-09-13 起是 `d99a9109…` —— `grep d99a9109` 在本文件里 **0 命中**。按修订 5 的正文下字会批准一个**已被取代的红控快照**: `b2f9cfd4` 先把成员索引转型再校验, `[False, True]` 变 `[0, 1]` 拿 PASS, 而导出器 `pod_export_bundle_v4.py` 用**存储原样**的数组做下标 `y4[i, m]`, 对它会 IndexError。`d99a9109`(AMENDMENT 3)先看 dtype kind 再用, bool/float/object/str 一律拒。**批准对象只以本节的声明块为准**, 上面修订 4/5 的正文自本节起只作历史。

**声明块(机器可核; 门 `v4_doc_approval_gate.py` 逐行对装置目录实测值比对, 不符即 rc 3)**:

```
APPROVAL_OBJECT v4_gate_step1_m.py 79950786271e690a24c72bc189b20e65eab6271164c1e582dff72b799db00163
APPROVAL_OBJECT v4_gate_step2_m.py d99a910951e070f70ae3eede1533013e009a62fa617eda55dff546290864329d
SUPERSEDED_OBJECT v4_gate_step2_m.py 0fe5ec5573f346969d9d3448c3e424f2ebc8b7c192cefe4313a05cdf84c09007
SUPERSEDED_OBJECT v4_gate_step2_m.py b2f9cfd40b9e356536184a63e202aa9d2a48228be5145bcd81665fb5f7df24e9
```

- 上面两行 `APPROVAL_OBJECT` = **用户下字时要写进 `ELIGIBILITY_CONTRACT.json` 的全部对象**(`gates.STEP1.approved_source_sha256` 增补第一行的值; `gates.STEP2.approved_source_sha256` 增补第二行的值)。合同现状(实测 `1188267a…`): STEP1 只有 `278fdce6…`, STEP2 只有 `db7ab356…`, 两个月度门都未批准 ⇒ preflight 会拒, 方向是 fail-closed。
- 两行 `SUPERSEDED_OBJECT` = 红控快照, 装置目录内以 `v4_gate_step2_m.r1_0fe5ec55.py` / `v4_gate_step2_m.r2_b2f9cfd4.py` 存在, 门能对上档案件核实。**另有第三个更早的红控 `455e3df4c195…`(修订 4 正文提到, AMENDMENT 1 之前)在装置目录内没有档案件**, 门只能把它记为无法核实的 token —— 引用它时必须带这句话。
- `v4_gate_step1_m.py` 的值自修订 4 起**未变**(实测仍是 `79950786271e…`), 本节不动它。

**装置 sha 表(原 §0★ 引言行「装置 sha(2026-09-12 实测)」)已删除**。它把六个值冻在一篇比装置目录更新得慢的文档里, 到今天 **6/6 全部不成立**(原表声称的六个前缀 ffbb89b8 / ee0af0c0 / 29611dbc / 2563446d / db5839e4 / e1dec02b 现已全部不再对应任何在役件), 而同一行本来就写着「不凭本表」。**改法**: 装置 sha 一律现场实测, 命令见引言行; 已提交的清单见装置目录 `SHA256SUMS*`(由 `make_sha_manifest.py` 生成)。

**十月执行前仍需用户下字的其余对象**(与本节声明块一并交裁, 全表与证据见 AUDIT_TRAIN §1.3):
1. `PREV_KING_FEA_UNCLAMPED=NONE`(修订 4 的六行新键之一; 门把这次「不可评」绑在 clamp 构建器身份 `PREV_CLAMP_BUILDER_SHA256=b9f9c728…` 上, 三者不等即 `REFUSED clamp_builder_identity`)。
2. **十月出口基线(TRN-15, 此前不在任何待裁表上)**: 出口门 E2b 要求 `LIVE_PINS` / `BUNDLE_BASE` 与合同 `approved_baseline`(`fd27fe48…` / `dce6a228…`)**逐字节相同**, 而本 RUNBOOK §0★ 步 0 要求 pins 每月重抄、基线 json 每月重立 ⇒ **十月导出按构造必败 E2b**。方向(lead §2 已定): 按月合同参数化, 不放宽 —— 批准基线成为**月合同的批准对象**, 门仍要求显式批准的 sha, 不接受「盘上是什么就用什么」。九月的 pins 几乎不可能逐字节复用(宇宙 Phase A M1 已于 09-04 上线)。
3. **fea89 trend 构建器(TRN-16)**: 十月模板 `BUILDER_FEA89` 仍指全局累积和构建器 `pod_f8_build_ext.py`(pod2 实测 `f606bffa…`); 稳定局部 trend 构建器 `pod_f8_build_stable.py`(git 实测 `59a8127e…`)**在 pod2 上不存在**, 改用它须先上架并重新核验。**若维持全局构建器**, 则有两条随之而定的后果必须同时落墨: 月滚**只许追加**, 且 2026-08-31 那天由 holefix2 合成的 229,824 格**不得**用现已可取的 vendor 归档替换 —— 任一替换都会让 STEP1_m 在洞邻域之外红, 红因与十月数据质量无关。

**本节的可核性**: 新门 `v4_doc_approval_gate.py`(收据 `DOC_APPROVAL_IDENTITY`, env `DOC` / `DEVICE_DIR` / `CONTRACT` / `DOCGATE_OUT` 全必填)对本文件与装置目录实测比对四格 —— A1 声明的批准对象 == 实测件; A2 每个尚未进合同的月度门 `v4_gate_*_m.py` 恰有一行 `APPROVAL_OBJECT` 且值 == 实测; A3 文中出现的每个「档案快照 sha」都有对应 `SUPERSEDED_OBJECT` 声明(直接点名档案文件名的写法免声明, 因为它本身无歧义); A4 紧跟装置文件名后面的 sha 是对该件的**声明**, 必须是实测值的前缀。**修订 6 之前的本文件**: A2 / A3 / A4 三格全红(rc 3), 红因 = 两个月度门无声明 · 五处裸引已取代的 step2_m sha(L62 / L76 / L80 / L91×2)· 六个陈旧装置 sha。

## §0 原则(不变式)

1. 重训 = **两个分离的显式版本事件**: king bundle(RUNBOOK 主流程)与 f10(addendum §A), 各自静默窗换、各自首锚验收、单变量留痕; 宇宙刷新 = 第三事件(§B, ≥3 天间隔 + 用户字)。
2. 判据冻结先于数字; 任一门红 = 不换版, 红因走「对账→干预实验→修复或呈裁定」链(09-01 守卫红为模板); 判据修订只经 AMENDMENT 显式落墨。
3. 产物 `_ext/_v3splice` 命名不覆盖上代(D1 教训); 换装必备份旧件(bundle 目录+tar; f10 np 文件)。
4. 复跑/重启命令逐字抄本文, 不凭记忆; ssh 全内联(**zsh 不分词**: 禁 `$SSH` 缩写/`set -- $var`, E-0901 两咬)。
5. 验证只认输出增长与终态标记; 长任务 nohup + 落盘标记(CHAIN_DONE 类), 守望 grep 终态。

## §1 前置(pod 到手后 15 分钟)

```bash
# 环境引导(幂等): multi_asset/exports/research/retrain_2026-09/pod_env_bootstrap.sh
scp -P <PORT> -i ~/.ssh/id_ed25519 multi_asset/exports/research/retrain_2026-09/*.py \
    multi_asset/exports/research/retrain_2026-09/*.sh root@<POD>:/workspace/
ssh ... 'bash /workspace/pod_env_bootstrap.sh'   # pandas/sklearn/lightgbm + torch>=2.7 cu128(Blackwell sm_120), 全断言
```
- 卷上必在: `dlnative_5m_wide829_f16_ext.npz`(上月缓存)· `wide_panel_4h_v3splice.npz` + `fund_state_canoncont.json`(**滚动正典**: 本月平价基线=上月 splice 产物)· `wide_multisrc/funding/`(zip 库, 增量)· `panel_symbols_wide.txt` · `dlw_ext/` `f8_ext/`(上月 f10 输入, 作旧代对照)。
- **live_pins.json 每月重抄**自在役 bundle config(symbols_live/keep_names 可能因宇宙事件变更): mac `python3 -c "...wide_shadow/shadow_bundle/config.json..."` → scp。
- **基线 json 每月重立**(slow_scorer_v3base.json 模式): 门② = 上月记录折 IC; 门③ = 在役 bundle provenance.pinned_ic2026。**2026-10 用值: fold24 +0.0548 / fold25 +0.0630 / ic26 +0.0584**(09-01 v3 记录)。

## §2 数据层(~40 分钟, 全 CPU)

> **⛔ 作废(2026-09-12): 本节是 09-01 v3 首跑的历史记录(`pod_fea_ext` 未 clamp / `pod_export_bundle_v3` / `pod_legs_ext` 全行重算 / 裁剪目标), 不再执行; 执行按 §0★。**

| 步 | 命令(pod /workspace) | 门(冻结) | 09-01 实测 |
|---|---|---|---|
| 1 vision 增量 | `EXT_DAYS=<上月逐日> python3 pod_extend_vision.py` | 404=新币缺日正常 | err 0 |
| 2 funding zip 增量 | `python3 pod_fund_zips.py`(MONTHS 改含上月; 幂等跳过已有) | err=0(残留单文件由门①裁) | 19,608 zip |
| 3 AUG 尾巴 | `python3 fund_pull_pod.py`(≤3.5req/s, 锚窗外) | 对实盘账本抽查 | 0.00e+00 |
| 4 缓存合并 | `EXT_END=<月末+1> python3 pod_merge_cache_ext.py` | 重叠逐位 exact_eq≥0.999 | 1.000000 |
| 5 面板重算 | `bash pod_run_chain.sh`(panel_ext+fea_ext; PANEL 基线env指**上月 splice**) | 内建7列 + **pod_gate1_full.py 全列≥0.999** | 18/18(15列=1.0) |
| 6 splice 滚动 | `python3 pod_panel_splice.py`(CAN=上月splice, cut=其末锚) | cut行逐位==正典; 尾部kline==ext | 断言过 |

> 门①若 funding EMA 列红: 先查 zip 覆盖(D3), 再走 09-01 对账链; **corr≥0.999 过门≠够用**——splice 滚动是常规步不是应急步(D5)。

## §3 king 轨(~30 分钟)+ bundle 换装

> **⛔ 作废(2026-09-12): 本节是 09-01 v3 首跑的历史记录(`pod_fea_ext` 未 clamp / `pod_export_bundle_v3` / `pod_legs_ext` 全行重算 / 裁剪目标), 不再执行; 执行按 §0★。**

1. `python3 pod_export_bundle_v3.py`(env: `EXPORT_PANEL=<splice> EMA_STATE_JSON=<canoncont>`)。内建门:
   门② 2024/25 折 IC |Δ|≤0.004 · 门③ ic26 ±0.006 · 守卫 2.27..2.57(带心重标=裁定项; 红先归因: 窗口新尾 vs 仪器, 09-01 干预实验为模板)· keep/宇宙断言=pins。
2. **门V4-king**(jpline): `jp_king_v4.py <fea.npy> <meta.npz>`(基线改本月 pod 数)→ 三折 |Δ|≤0.004。09-01: Δ=±0.0000。
3. 换装(锚间静默窗, mac):
```bash
scp ...:/workspace/shadow_bundle_v3.tar.gz ~/wide_shadow/   # sha 两端比对
launchctl bootout gui/$(id -u)/com.hsy.shadowloop
cd ~/wide_shadow && mv shadow_bundle shadow_bundle.<代号>_backup && mv shadow_bundle.tar.gz shadow_bundle.tar.gz.<代号>_backup
tar xzf shadow_bundle_v3.tar.gz && venv/bin/python acceptance.py   # 必须 ALL_GREEN 4/4
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist
# 验: shadow.lock PID 命令行含 shadow_loop_v3.py run; launchctl print 含 SHADOW_OFFSET_MIN=16
```
4. 首锚验收: shadow_log booster_sha 翻版 + kc/fc own + 改写幅度无跳变>3pp(09-01: 15.98%, −0.45pp)。

## §4 f10 轨(~90 分钟)+ 换装

> **⛔ 作废(2026-09-12): 本节是 09-01 v3 首跑的历史记录(`pod_fea_ext` 未 clamp / `pod_export_bundle_v3` / `pod_legs_ext` 全行重算 / 裁剪目标), 不再执行; 执行按 §0★。**

1. 输入链: `bash pod_f10_inputs_chain.sh`(targets→**pod_gate_dlw_ext.py**→fea82→fea89; targets/fea82 env 指 splice 面板)。
   门: y4s/qvk corr≥0.999(实测 1.000000)· YRZ ≥0.999(0.999910)· members 全等或 TIE_EXEMPT(qvk 逐位相等的 NTOP 平位才豁免)。
2. legs: `python3 pod_legs_ext.py`(旧行逐字+新锚同公式; 自验证 Z24/ZFD exact≥0.999, 实测 1.0000)。
3. 部署重训: `SEED=42 python3 pod_f10_refit_ext.py`(+2027; GPU 各 ~7.5min)。配方硬编码=冻结(COST 3.52/LDD 0.25/15ep/3e-4)。
4. 门V1: `SEED=<s> python3 pod_f10_np_export.py` → Spearman≥0.99999 & maxabs≤1e-5(实测 1.0000000/1e-7)。
5. 门V2(**同装置双数据法**, 全史件不评历史): `ARM=V2MAIN V2=1 SEED=<s> F10_DLW=<旧|新> F10_OUT=<旧|新> python3 pod_f10_train_ext.py` ×4 → preds 中继 jpline `f8_2026-08-22/preds/` → `bash jp_w10_v2gate_runner.sh`(conda python; hardened 装置 9f15dea0131f 逐字)→ `jp_w10_v2gate_judge.py`: 双种子 ΔNet(2023+) CI 下界 ≥−0.10, >+0.30=SUSPECT。09-01: −0.009/−0.030。
6. 门V3′(AMENDMENT A1): `python3 pod_f10_v3_leakcheck_v2.py` → 未来侧无峰 + 谱形与在役代逐k |Δ|≤0.03 + 折外泄出=0。09-01: 0.019/0.024/0。
7. 门V4-np(jpline): `jp_v4_np_check.py` → maxabs≤1e-5(实测 2.78e-16)。
8. 换装(全门绿 + 静默窗; 消费者每锚新进程加载 ⇒ 原子 mv 即生效零重启):
```bash
cp <新np> ~/wide_shadow/fea171/f10_live_s42_np.npz.tmp
mv ~/wide_shadow/fea171/f10_live_s42_np.npz ~/wide_shadow/fea171/f10_live_s42_np.npz.<代号>_backup
mv ~/wide_shadow/fea171/f10_live_s42_np.npz.tmp ~/wide_shadow/fea171/f10_live_s42_np.npz
shasum -a 256 ...   # == pod 训练产物
```
9. 首锚验收(=换版锚): kc/fc own + n_f10 400 + 改写无跳变>3pp。

## §5 收口(30 分钟)

journal 追记(门表全数+换版锚+sha)→ STATE 横幅+§1 事实行 → MANIFEST 增补 → memory 更新 → 双仓 commit。上月 pod 大件(fea/panel/preds)留卷即可, 小件(models/results/config)git 归档。

## §6 提速账(09-01 实测 → 10 月预算)

DL refit 7.5min ×2 / walk-forward 4折 20min ×4(并发=25min)/ king+bundle 21min / w10 回放 5min / 数据层 40min ⇒ **关键路径 ~2.5h**。09-01 耗 12h 的三类一次性成本已治: 环境熵(→pod_env_bootstrap.sh)/ 脚本散落(→git 单源)/ 基线缺位(→splice+state 滚动留卷)。剩余人窗: 静默窗对齐(换装只能锚间)。

## §7 全损重建(pod/jpline 任一或双双被收走时; 2026-09-01 立)
**本机持久档** `~/quant_archive/pod_2026-09/`(2026-09-01 实际落袋): **v1 真正典面板**(247,363,525B, sha f14bc33d78b2, 14,329锚×21键含 fundfix 三键 — ★jpline w3lane 那份是 9,913锚×18键的 fundfix 前旧代, 非正典!)+ **107 份 jpline 判决收据 json**。splice/ext缓存/preds 因 pod 中途停机未落袋 — 在网络卷上(下次挂卷先验 sha)或按路径 B 重建。**git**: 全部装置脚本(retrain_2026-09/)+ models_2026-09(双种子 .pt+np)+ pod_env_bootstrap + jpline_hsy_v5push_freeze.txt + 各判据/RESULT 文档。
**重建路径 A(有档)**: 新 pod 挂空卷 → git clone → scp 档案回卷 → bootstrap → 直接进 §2 步骤5。
**重建路径 B(零档全重)**: vision 全量重拉(klines/premidx/funding zips, 脚本在 git, ~1h)→ 缓存/面板/特征链(§2)→ 与 git 记录的门数对表(exact_eq/corr 序列均在 MANIFEST)。jpline 替代: 任何 64 核 CPU 机 + pip install -r jpline_freeze。
**唯一不可再生物** = 实盘账本(mac pilot_log, 已有 notary 链)与在役 bundle(mac)— 均在本机, 与训练机无关。

## §8 待办(2026-09-02 立, E-0902-D): 回放 king 腿口径对齐实盘
w10 回放的 king 腿 = `slow_pred_hist_oos.npy`(逐年折外, 2026 由 ≤2025 模型给)⇒ 2026 msharpe 席位 king≈0.01, 实盘 0.21。月度重训链的自然副产品 = 每月 bundle 对次月的真 OOS 预测; 从 2026-10 起把每月 booster 对"下月锚"的预测拼成 `slow_pred_rolling_oos.npy`(严格因果: 训练截止 < 预测锚), 作为回放 king 腿的第二口径, 与 hist_oos 并报; 席位敏感臂以 rolling 口径为主判。

## §9 修订(2026-09-04, 第三版 11:5xZ, E-0904-F): 席位历史口径 = Σ 5 分钟简单收益(面板 y4 原样), **导出器与生产者都不改**
- **真相(代码+实证, 见 ERROR_LEDGER E-0904-F):** 面板 y4 = 行 [E, E+47] 的 Σ ret5(ret5 = c/pc − 1), 是交易所记账 Π(1+r)−1 的无偏代理(差 −0.04 bps/锚); 导出器 L108 用原始 y4、生产者 L439 用 Σ ret5 ⇒ **两处口径本来正确**。错的是回放装置 `w10_universe.py` 的 CAL=simple(expm1), 它给 king 腿加了 −2~−3 bps/锚伪拖累。
- **本日经过:** 08:53Z 我按错口径把 `state/leg_returns_live.json` 换成 expm1 版 OOS 种子(king 席位 0.21→0.000); 11:46Z 已恢复原文件(sha 172715ce, 生产者 kickstart PID 58281), 12Z 运行前完成。撤回本节前两版的全部改动要求(① 导出器 expm1 ② 生产者 expm1 ③ "样本内"断言)。
- **保留的改动(需预注册):** ③ 换装步骤禁止删除/重置 `state/leg_returns_live.json`; ⑤ 生产者 extra ≥900 行时忽略 bundle 序列(避免 2022–23 段生产 booster 样本内值在 extra 不足时进窗); 导出器 leg_returns 的 2022–23 段改用年折 OOS 预测(不入 900 窗, 只为"进席位的历史须 OOS"规则的完整性)。
- **测试 [10] 改为口径一致性:** 实盘 state king 900 窗 Sharpe/锚 须在 bundle 同窗 ±0.05 内(bundle 与生产者同口径; 若有人再引入 expm1/log 会跳到 −0.02/+0.21 被抓住)。
- **研究侧待办(另立预注册):** 装置 CAL 语义修正(默认不再 expm1)+ 重立复现收据; 所有 CAL=simple 结论用 CAL=log 复验(T3c/M1/阶梯/滚动 king/腿解剖)。

## §v4 · 2026-09-09 口径正典配方(2026-09-12 已展开为 §0★ 步骤单; 本节保留为配方原文)(用户令「记录下来免得以后搞完了」; 装置 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`, 受据 RESULT_v4_chain_retrain_quantify_2026-09-09)
下一次重训**按本节而不是上文旧步骤**; 每项都有门, 门红即停:
1. **5m 缓存** = holefix2 正典(`dlnative_5m_wide829_f16_holefix2.npz`, sha16 1d7f459d)+ 滚动补月; 建后跑 `cache_coverage_gate_v2.py`(排除首末日; 洞 0 / 宽缺口 0 才过)。原始收益补丁 `raw_patch.npz`(952 bar)随缓存走。
2. **king 特征** = `pod_fea_ext_clamp.py`(E−w clamp ≥ 0; 不再用 `pod_fea_ext.py`), PANEL_IN=当月 v2ext 谱系; **候选(09-09 G3 关闭, 待用户字): fea89 的 trend_288/trend_2016 改用稳定局部算法 `pod_f8_build_stable.py`(= 构建器逐字, 只换 trend 块; 全局累积和对死名 NaN 翻转的闭合缺陷 G1/G2 已证; 书层 A1s−A0/A1s−A1 四格 (C) 未检出差异 — 口径纠正非收益主张, `PREREG_fea89_stable_trend_and_closure_gate_2026-09-09.md`);** 门 = 与上代特征差异只在缓存改动邻域 [start−48, end+8640+288] 行(`v4_gate_step2.py` 型)。
3. **DL 目标/特征** = `pod_dlw_targets_raw.py`(记账 y4s 原始收益 RET_CH=0 + DLWT_RAW_PATCH; 训练标签 RAW 与 CLIP 的书层对照为 (C)(A1−A2 双种子反号, 装置分辨率内; 目标数组本身 RAW−CLIP 有 638 格有限值不同, **不是「无差」**; 复审 b0a573a1 R3), 默认 CLIP 即 `dlw_hf3` 型), fea82/fea89 同法重建; 门 = `v4_gate_step1.py` 型(RAW vs CLIP 差异恰为补丁窗; **邻域外差异必须为 0** — AMENDMENT 3 的「trend_288 残差」例外读法已被复审 c8e2fc13 撤回, 该 FAIL 的机制受据 = trend 全局累积和, 由稳定 trend 候选(上一步)修复; 门本身须 FAIL 即非零退出, 见复审 b0a573a1 P1-PIPE 待修)。
4. **legs** = `pod_legs_ext.py` 策略: **在役训练 legs 行逐位原样 + 新锚同公式**(禁止全行重算: king PRED 只从 2024 起, 全行重算会把 2023 king 席位算成 0 ⇒ DL 少学一半样本, AMENDMENT 5); 自检分年 WL(2023 king ≈0.59)。
5. **king 导出** = `pod_export_bundle_v4.py` 型, env **逐字**: `EXPORT_PANEL=<本月 splice> EMA_STATE_JSON=<canoncont> BUNDLE_BASE=<上代 own fold IC>`; 门②③/守卫带 2.27–2.57 原样; 守卫红先复现上代发表值(guard_book_lib 逐字基线书)再报。`provenance.generation` 标签改为本代。
6. **F10** = 月折 FIX7(`BEST_EP_FIX=7`, EMBARGO=1, 20 折 202501..)+ refit `pod_f10_refit_v4.py` FIX7; V1 np≡torch; V3′ 条款② 参照 = 同配方上一代月折(AMENDMENT 6), 对年折差另报。
7. **书层量化** = dev 树 meta y4 用原始收益(`meta_newprod_v4` 型), 判官先复现已发表数字(A0p 法: 同代输入逐位), 冻结窗主判 + 扩展窗次级, 双种子双席位, 逐年表负年显式。
8. 已知易错: NpzFile[key] 不进循环; pgrep 用 `[c]hain` 括号法; 一切 sha 由复跑实测; 过程状态只读过程收据。

### §0★ 修订 7(2026-09-17, FP2-3 / FP2-4; 独立研究员 PENDING_DECISIONS「月度重训启动时没有完整重新核验上个月的合同、记录和实际文件」「流程结束状态未区分通过/失败/无法验证」)
1. **合同新增两个可选键**(`chain_lib.V4_MONTH_OPTIONAL_KEYS`, 解析器接受、不强制; 冻结的九月合同**不改**、不受影响): `PREV_MONTH_ENV` = 上月合同路径; `PREV_SHA_JSON` = 上月八个 ROLLED 工件的 `{path: sha256}` 记录, 由 `mk_prev_sha_record.py <上月合同> <out.json>` 在上月链收官后生成并冻结。十月模板已带占位。
2. **preflight 对 2026-09 之后的月份**: 未声明这两键 ⇒ FAIL「previous contract not declared」; 声明了 ⇒ **现场重跑** `v4_gate_roll_paths.py`(收据 `v4_gates/ROLL_PATHS_preflight_live.json`, 日志 `roll_paths_preflight_live.log`), 三态 VERDICT 必须 PASS(FAIL / UNAVAILABLE 都停)。归档的 ROLL_PATHS 收据仍核, 但**不再单独足够**——它证明写它时为真, 不证明上月工件此刻仍是记录所说。
3. **三态判词**: `v4_gate_common_v2.finalize3`(PASS 0 / FAIL 3 / UNAVAILABLE 3, 收据 `VERDICT` 字段, 打印真实标签); roll gate 已切; 冻结 `v4_gate_common`(24e813f1)不动; 所有读者读 JSON `PASS`, UNAVAILABLE 永远 PASS=False。
4. dryrun 负控派生 env 按存在带入可选键; 负控仍以「preflight 诚实 FAIL 且零启动」为通过。
收据: `docs/fixprogram_2026-09-13/receipts/FP2_tests_20260917/`; 测试 `tests_month_env_optional_keys.py` / `tests_v4_gate_common_v2.py` / `tests_pipeline_gates.py`。

### §0★ 修订 8(2026-09-17, FP2-8 试跑发现; 待研究员复核)
- **缺陷**: dev 树内 `health_check/run_arm.sh` 第 9 行硬编码 `ROOT=/workspace/review_scratch/health_check`。驱动虽由 `chain_lib` 导出 `V4_HC/V4_KING_DIR`, 且 `run_v4_arms.sh` 会 `cd $H`, 但 `run_arm.sh` 用自己的 ROOT 定 `cwd=$ROOT/dev_v4` 与 `logs/commands.txt` ⇒ **任何非九月根(含本模板 `HC=$R/health_check`)跑臂都会写进九月树**(probe_artifacts / logs 被覆盖), 判官读的却是本月 HC —— 静默错树。
- **处置**: 每月复制 dev 树后必须把 `run_arm.sh` 第 9 行改为 `ROOT=$(cd "$(dirname "$0")" && pwd -P)`(FP2 副本已改, sha8 69e1e949 → f30b2c7c, 原件留 `run_arm.sh.orig_sept`), 并**重跑 preflight**(它把 `HC/run_arm.sh` 当输入哈希)。根治 = 把 `run_arm.sh` 收进研究仓装置目录并由驱动按 D 分发(待做, 登记 FP2-9 采纳项)。
- 同类隐患: `run_v4_arms.sh` 的 umask 与 costb 已按 `$H` 取; A0 的 `SLOW_v3_on_v4axis.npy` 与 `f10_A0_*` 预测在**九月轴**上, 本月轴若变(FP2 v2 king 轴 +30 锚)需按时间戳对齐而非按行(见 DESIGN_FP2-8 AMENDMENT 3)。

### §0★ 修订 9(2026-09-17, FP2-8 试跑; 容器内存上限)
- pod2 容器 cgroup **`memory.max = 61 GB`**(不是 `free` 看到的 247 GB); `pod_fea_ext_clamp*.py` 全缓存构建峰值 ≈50–58 GB。**king 特征构建必须单独跑**(数据层内它在 fea82/fea89 之后串行, 本身满足; 但不得与 controls / 其它构建并行), 否则 SIGKILL(rc −9)且日志无 traceback(`memory.events oom_kill` 计数是唯一证据)。步 2 前先 `cat /sys/fs/cgroup/memory.max memory.events`。

### §0★ 修订 10(2026-09-17 09:16Z, FP2-6 用户字: 钉 king 模型身份已部署 6e177c4)
> ⚠ **修订 11(2026-09-17 复审二轮 R10)**: FP2 运行器 `chain_fp2_run.sh` 默认阶段串现在以 `member_rule per_year decision` 结尾(此前止于 export ⇒ 默认一键跑不出数); 换装建议只读 `$R/v4_gates/DECISION_FP2.{json,md}`(formal profile, 身份闭包见 AMENDMENT 10), 判官 JUDGE_v4.json 只作信息。
- 步 8 换装新增硬条件: **换 bundle 与改 `~/dl_quant_live/config/book.json external_book.booster_sha_pin`(← 新 bundle 的 slow2026.txt sha256 = MANIFEST 项)必须在同一个锚间静默窗内完成**(顺序无关, 但都要赶在下一锚 N+24:00 前), 执行器提交仍走 safe_commit/电池 + push + `pull --ff-only`; 忘改钉 ⇒ 下锚起 HOLD + HIGH 直到改对(不交易、不平仓)。回滚 bundle 时同步把钉改回旧 sha。
- `universe_sha_pin` 保持 null(用户字: 宇宙月度滚动)。DL 腿身份钉(FP2-6b)待生产者 combo_stage 写 `f10_sha` 字段后另行部署。

### §0★ 修订 7(2026-09-18, FP3 J; 主研究员; 复审待做)—— 唯一执行清单的收口: 版本绑定的端到端负控已实测 + 干预台账 + 待用户下字对象一处列全

**为什么有这一节**: 修订 1–6 把步骤、门、批准对象分散在六段修订与三份设计里; 本节只做三件事: ① 把「十月执行前必须发生的事」列成一张表(每行带装置与实测 sha 的取法, 不再抄 sha); ② 把「版本绑定的端到端验收」定义为可重复的负控实跑并给出本次收据; ③ 立「生产干预台账」为十月链的前置(P-B 为钉住 FTRIM/M1/播种三次干预的锚位, 靠人工反推且错过两次; 台账避免再走这条路)。

**① 唯一执行清单(执行顺序 = 行序; 每行的 sha 用 `sha256sum <装置目录>/<件>` 现场实测, 与 `SHA256SUMS*` 对照)**
| # | 事 | 装置 / 入口 | 门 / 收据 | 状态(09-18) |
|---|---|---|---|---|
| 1 | 月合同 `v4_month_2026-10.env` 立档(MONTHS_ALL、LIVE_PINS、BUNDLE_BASE 按月参数化) | `devices_v4chain/v4_month_2026-09_fp2.env` 为模板 | preflight `PREFLIGHT PASS device_files/inputs/approvals` | 待十月 |
| 2 | 用户下字对象入合同(修订 6 声明块两行 APPROVAL_OBJECT; TRN-15 出口基线按月批准; TRN-16 fea89 构建器取舍; PREV_KING_FEA_UNCLAMPED=NONE) | `ELIGIBILITY_CONTRACT.json` | `v4_doc_approval_gate.py` DOC_APPROVAL_IDENTITY | **待用户字**(与 PROPOSED6 判活规则一并) |
| 3 | 干预台账检查: 上月所有生产干预(版本切换、状态换入、播种、掩码/参数)已按锚语义登记 | `docs/PRODUCTION_INTERVENTION_LEDGER.md`(本修订新立, 追加式) | 台账每条带「首个受影响锚」与受据 | **新立, 需回填 09 月**(FTRIM 09-02 12Z / M1 09-04 04Z / 播种 09-05 16Z / f10_sha 09-17 16Z / NOSLEEP 09-18 04Z) |
| 4 | 负控实跑(版本绑定的端到端验收): `V4_DRYRUN=1 bash chain_v4_monthly.sh <月 env>` 必须 preflight PASS 且在首个会启动的阶段前以 `FAIL_dryrun_guard_*` rc=9 停下 | 驱动 `chain_v4_monthly.sh` | 收据 `negctl.log` | **本次已过**: 09-18 07:30Z, 月 env sha cc9d9748…, PREFLIGHT PASS device_files=30 inputs=30 approvals=3/3, 随后 `FAIL_dryrun_guard_cache_would_launch` rc=9(`docs/fixprogram_2026-09-13/FP3_receipts/chain_negctl_2026-09-18/negctl.log`) |
| 5 | 正跑 `bash chain_v4_monthly.sh <月 env>`(每阶段 prereq 绑定合同与输入; 任一阶段 FAIL_* 即停) | 同上 | 各阶段完成标记 + `preflight → decision` 收据链 | 待十月 |
| 6 | 决策 = `fp2_gate_*` 三门 + AMENDMENT 7 δ 规则; NO_SWAP 也要出完整收据 | `DECISION_FP2_*` 装置 | 30 件 sha 与冻结源相符 | 待十月 |
| 7 | 换装(若过门): 席位播种同法(`seat_seed_v3` 装置)、`launchctl kickstart` 动词、干预台账登记、combosnap 首锚 PARITY | 见 `seat_seed_v3_deployed` 受据 | PARITY 收据 | 待十月 |

**② 端到端负控的判据**: 不是「跑完」, 是「在正确的地方停」——preflight 全过证明装置/输入/批准三者绑定于本月合同; `FAIL_dryrun_guard_*` 证明任何会启动训练/导出的阶段在启动前受同一份合同约束。正跑前**必须**有当月的这份收据。

**③ 干预台账**(`docs/PRODUCTION_INTERVENTION_LEDGER.md`): 每行 = {UTC 时刻, 对象(执行器树 / 生产者文件 / 状态文件 / 合同), 前后 sha, **首个受影响锚**(按「生产者在 A+20m 算锚 A」的语义), 受据}。P-B 的教训: 播种在 12:47Z 换入 ⇒ 首个受影响锚是 16Z 不是 12Z; M1 首见于标 09-04 04Z 的记录 ⇒ 04Z。
