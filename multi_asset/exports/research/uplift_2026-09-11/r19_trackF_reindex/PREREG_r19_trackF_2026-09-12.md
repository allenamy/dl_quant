> **创建:** 2026-09-12 | **Session:** r19 subagent (team-lead 派单, branch `research/book-uplift-2026-09-11`) | **状态:** 预注册 — 判据/消费者名册/读法冻结于任何更正后数字之前 | **作废条件:** §0 的两个复现数(0 → 10039 命中; 归档表逐位复现)任一不复现 ⇒ 全文作废并停工上报 | **实盘:** 零接触(`~/dl_quant_live` `~/wide_shadow` 只读; pod2 CPU only; PID 333197/339489 不碰)

# PREREG · r19 — Track F regime 表的掩码索引缺陷: 复现 → 修一行 → 重判全部消费者

## §0 缺陷与必须先复现的数(STOP 规则)
`trackF/build_regime.py`(sha256 `db80e66fb0620333b0b224a14b2184e27be345027941092078abf56fba9299b4`, 本机与 pod2 同)L17 建 `umap = {int(t): k ...}`(**时间戳** → 掩码行), L29 却以 **面板行号** 查它: `k = umap.get(j)` ⇒ 恒为 `None` ⇒ L30 的成员掩码 `m = m[UMM[k][m]]` **从未执行**。
复审收据 `codex_uplift_review_2026-09-12/contracts/RECEIPT_trackF.json`: 原码逐位复现归档 `regime_vars.npz`(sha `27e604f7…`), 掩码命中 **0**; 改为按时间戳查 ⇒ 命中 **10039**; 15 个字段中 11 个在 9758/10039 行改变(`fund_med` 2990 行), 标签 687/7849 改变。
**先复现这四个数; 任一不复现 ⇒ STOP 并上报, 不进入 §2 以后任何一步。**

## §1 修法(唯一允许的语义改动 = 一行)
- `k = umap.get(j)` → `k = umap.get(int(t))`。
- 非语义改动(必须, 因原码把输出路径写死在归档目录): 输出路径改到 `r19_trackF_reindex/`。**diff 只允许这两处 hunk**, 逐字存档 `devices/build_regime_fixed.diff`。
- 标签器 `label_and_arsenal.py` 的标签函数(expanding median, BURN=2190, 严格过去)**逐字不改**, 只换输入表。

## §2 消费者名册(冻结; 全树 grep `regime_vars` / `regime_labels` / `labels.npz` / `27e604f7` / 缺陷签名 `umap.get(j)` 的并集)
**T1 trackF 内(读归档表或其标签)**:
C1 `label_and_arsenal.py` → 格大小、军械库表(RESULT §2/§4) · C2 `arsenal2.py`/`loc_arsenal.py`(共同锚集军械库, 1-D 切分, A0 分解)· C3 回放装置 `w10_trackF.py`(sha `d3aa1ddc…`)经 `TF_REGIME_NPZ` 消费标签的臂: **TF_R1, TF_R1b, TF_R2, TF_R3, TF_F1R, TF_R5, TF_R6(s42); S27_R1, S27_R5, S27_R6(s2027)** —— 必须用更正标签**重跑**(命令逐字抄 `trackF/commands.txt`, 仅改 `TF_REGIME_NPZ` 与 `OUT_TAG`, cwd 改为 r19 镜像树)· C4 判官/诊断 `judgeF.py` `judge2.py` `composition.py` `diag1.py` `diag2.py` `ceiling.py`(RESULT §3/§4/§5/§6/§7)。
**T2 trackF 外, 直接读归档 `trackF/regime_labels.npz`**: C5 `r3_gates/devices/regcomp.py`(sha `30fee017…`)→ `regime_composition.json` → `PREREG_gateB` §2 表与 RULE W 受理判据(n≥5000 且两口径 L1≤0.15); C6 `r4p3/p3_an.py`(`528bcb73…`)→ `RESULT_P3.json` Q2_rho_by_cell / Q3 REGIME_CONDITIONAL; `r4p3/p3_b.py`(`e14042f5…`)→ `RESULT_P3B.json` C_percell_portfolio。
**T3 trackF 外, 逐字抄了缺陷行**(同一 bug 形态; 第七轮/审计已各自发现其中两处但未回溯到源头 trackF): C7 `judge1_r6/j1_regime_pod.py` = pod2 `r6j1_regime.py`(`79c28167…`; 另有九月 60 锚走 `UMM[-1]` 分支 ⇒ 轴内掩码不一致)→ `RESULT_r6_judge1` §5 窗表; C8 `r8_inbook/regime_gb.py`(`578c8b84…`)→ `REGIME_GIVEBACK.json` 分格 dg/ρ; C9 `r7f2/r7_fuel.py`(`aecc09c4…`, ERROR_LEDGER P1-32 已记「NOT PROPAGATED」)→ `R7_FUEL.npz` → `r7_screen.py` `r7_screen2.py` `r7_spec.py` `r7_withinyear.py` `r7_final.py`(其 L93 另含同一缺陷行)→ `RESULT_r7_fuel2` §1/§3/§3.1/§4/§5。
**非消费者(登记, 不重跑)**: `r7f1/r7_sigma2.py` 有意仿真该缺陷(R6 臂)并给出正确臂 R6M/LIVE —— 用作 §5 交叉仪器; `r12_regime` v1/v2、`r13*`/`r15`/`r16`/`r17`(读 v2)、`r12_smoothing`(读 v1 + 自建 REGIME12 无掩码)—— 只做 §7 索引审计, 不重判。
**重跑顺序 = T1 → T2 → T3。** 若时间/配额不允许完成 T3 的某项, 在 RESULT 中**逐项明写未跑**, 不得沉默。

## §3 统计量与口径(冻结)
- g = `net_ex/gross_total`, bps/锚/单位 gross(判官 `judge_v4.load` 同式)。
- 主窗 **W_ALPHA** = 丢前 900 个装置锚(E-0911-A)**且** ts ≤ 2026-08-30 20Z(E-0911-D), A0 轴 n=9138。trackF 原判官窗(冻结 2025-03-01→2026-08-10 20Z; 全史; hold-out 2025-01→)**同时保留**, 只为与原判决同口径对照。
- 条件表(每 regime 格 LL/LH/HL/HH + WARM + ALL): n, mean g, **CI95 = UTC 日块 bootstrap 2000, `default_rng([20260905, k])`**, Sharpe = mean/sd·√2190, **SE(Sharpe) = √(2190/n_cell)**。前(归档标签)/后(更正标签)并列, 同一 k。
- **k 分配(冻结)**: 条件表 k = 100·form_idx + 10·seed_idx + cell_idx; form_idx 按 [A0, KFnoDL, FUND, KING, REV, ALL3DL, ALL3, DLslot, noFTRIM, R1, R1b, R2, R3, F1, F1R, R5, R6] = 0..16; seed_idx s42=0/s2027=1; cell LL=0 LH=1 HL=2 HH=3 WARM=4 ALL=5。trackF 对照(候选−A0)沿用 `judgeF.py`/`judge2.py` 原 k 序(逐字复用其代码), 使「前」逐位复现原 RESULT。
- Bonferroni: 沿用 trackF 原 K=6(α=0.05/6, 99.17% 区间)。
- 两种子: 凡原轮有 s2027 臂者(A0/R1/F1/R5/R6)双报。
- 尾部数字一律下界(E-0908-B)。

## §4 读法(冻结, 先于数字)
1. **候选判决「反号」** = (候选−A0) 点估计在前/后之间变号。**「过门变化」** = G1(点估计 > +0.23)/ G2(Bonferroni CI 下界 > 0 双种子)/ G3(a–d)任一状态在前/后翻转。三者都不发生 ⇒ 「判决不变」。
2. **格内均值「翻号」** 只在: 前后点估计异号 **且** 更正后的 CI95 不含 0。否则写「两者皆与 0 不可分」。**不因 CI 含 0 而软化一个真实的翻转; 也不因点估计变号而宣称翻转。**
3. **GATE B**: 重算每窗两口径 L1; RULE W 受理集合前/后; `PREREG_gateB` 自设作废条件「L1 排序反转」逐对检验(FROZEN vs 2024-on vs F23 vs FULLCYCLE 的 L1 序)。
4. **r4p3**: 报每格 ρ(A0,AMI)/ρ(A0,XIB) 前后, 及 RESULT_r7_fuel2 §3.1 所引三数(+0.343/+0.438/+0.093)的更正值; Q3 `SR_cellwise_walkforward` 前后。
5. **r6 j1**: 各窗 HH 份额与 L1 前后; 「实盘窗 97.93% HH」(DOCKET_r7 L195)更正值。
6. **r8**: 每臂每格 dg/ρ 前后(G8 披露项本身 = 非条件 ρ, 与标签无关, 预期不变 —— 若变, 报告为装置异常)。
7. **r7**: 月中位(2026-02/07/08/09)、TODAY 分位、每候选 T0/T2 Sharpe 与 T2−T0 gap CI、§3.1 分格 ρ、机制相关(σ_fund vs basis 离散)、年内三分位, 前后。
8. **标签变化账**: 报 changed / labeled(预期 687/7849); 逐格迁移矩阵(前格 × 后格)。
9. 每个数字标 **VERIFIED**(本轮机器算出)或 **INFERRED**(推断/引用)。

## §5 控制(必须先绿)
- **G0 镜像平价**: r19 镜像树用同一 `w10_trackF.py`(sha 断言 `d3aa1ddc…`)跑 TFPARITY(TF_* 全不设)⇒ `d30_n2_c42_rec` 对 trackF 归档 `TFPARITY` **逐位相等**。
- **负控**: `TF_F1`(SEATF10=1, 不走标签路径)与 `S27_A0` 用**更正**标签重跑 ⇒ 必须对归档逐位相等; 不相等 ⇒ 标签进入了未声明的代码路径, STOP。
- **交叉仪器**: 更正后 `sig_fund` 对 `r7f1/out/sigma_variants.npz` 的 `R6M_sig`(= meta 成员 + m1 掩码, ddof=0, x0910 轴)在共同锚上逐位/1e-9 内相等。
- **归档等价**: 本机 `trackF/labels.npz`(`8184d6f1…`, `loc_arsenal.py` 产)与 pod2 `regime_labels.npz`(`18ee9e1a…`, `label_and_arsenal.py` 产)内容相等(ts/lab/lf/ld 逐位)。

## §6 复现纪律
- 分析脚本 env 白名单 = **空集**并断言(口径旗标键集 `CAL JUDGE UPLIFT PANEL LOOK WRULE LEGS PHI FSEED W3FIX FTRIM UMASK SLOW FPRED MEMBERS_TOPN COSTB SLEEVE KMOD SEAT RNSM LTRIM CDAMP FUNDSCALE FEMAT TRADE_TOPN REF_SKIP` 前缀均不得出现)。
- 装置重跑 env = `commands.txt` 逐字(键集: CAL WRULE LOOK MEMBERS_TOPN FTRIM UMASK_SCOPE UMASK_NPZ COSTB_JSON FSEED FPRED SLOW_NPY TF_SAVE_W TF_REGIME_NPZ LEGS PHI TF_SEATMODE TF_LOOK_R TF_EMA_HI TF_FUNDOFF SEATF10 REF_SKIP OUT_TAG + OMP/OPENBLAS/MKL_NUM_THREADS=4), 命令逐条写入 r19 `commands.txt`。
- 每个装置自报 sha 写进收据; 输入文件 sha 写进收据(meta `0e3c09ac…` / panel `5e67c055…` / umask `47d87b51…`)。
- pod2 前后 `nvidia-smi` 0%/2MiB, load 记录; 不写任何归档目录(trackF/、r3_gates/、r4p3/、r8_inbook/、r6j1/、r7f2/ 一律只读)。

## §7 跨轮 regime 表索引审计(表格式冻结)
每行: 轮次 → 建表脚本 sha → 产物 sha → 掩码命中数(**执行计数**, 非读码推断)→ 索引正确? → 成员规则 → 备注。覆盖: trackF 原/修; r6 j1(incumbent/x0910); r7f2 fuel(inc/x0910); r7f2 final L93; r8 regime_gb; r7f1 sigma2 三臂; r12 v1 `c74fd695`; r12 v2 `0510f456`; r12_smoothing REGIME12(无掩码, 按设计)与其 v1 消费; r13A/B、r13_deploy、r13b_nulls、r15、r16、r17(读 v2)。

## §8 产物
`PREREG_r19_trackF_2026-09-12.md`(本文, sha 先于数字写入 `receipts/PREREG_FREEZE_sha.txt`)· `RESULT_r19_trackF_reindex_2026-09-12.md` · `devices/`(全部脚本 + diff)· `receipts/`(JSON 收据、更正表/标签 npz、commands.txt)· `SHA256SUMS.txt`。
