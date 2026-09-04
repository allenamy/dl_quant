import sys, io
P="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/REVIEW_caliber_final_draft.md"
t=open(P,encoding="utf-8").read()
def ins_before(anchor, new):
    global t
    assert t.count(anchor)==1, ("anchor count", t.count(anchor), anchor[:60])
    t=t.replace(anchor, new+anchor)
def ins_after(anchor, new):
    global t
    assert t.count(anchor)==1, ("anchor count", t.count(anchor), anchor[:60])
    t=t.replace(anchor, anchor+new)

# ---- A. §5 preamble: year coverage facts (before ### 5.1)
A_anchor="### 5.1 固定席位 0.21/0/0.79(在役 combo 形态)\n"
A_new=("**年份覆盖(数据事实, gap_2 补证; 用户规则 ERROR_LEDGER L373 / memory `feedback_report_live_caliber_full_cycle` 要求逐年 2021–2026 且负年份显式)**: "
"pod 港装置的输入在 2024 前是残缺的——king `slow_pred_pinned.npy` 逐年有限占比 2022 0.0000 / 2023 0.0000 / 2024 0.3304 / 2025 0.4681 / 2026 0.4825; F10 `f10_V2MAIN_s42.npy`(s2027 同)按 dlw 年 2022 0.0000 / 2023 0.2260 / 2024 0.3304 [VERIFIED: gap_2 `pod_gap2_stats.py` → `gap2_stats.json` coverage; 与 R-C6.2 `REPORT.md` L45/L47 一致]。"
"装置里 king 分数 NaN → `xz` → 0(L129-133), 故 2022–23 每条序列的 `leg_king` 逐锚恒为 0(|max| = 0.0, 五条 port 序列 + 八条 R-C6.1 alt 序列全部如此, 同上收据), 席位仍按 W3FIX 0.21 或 msharpe 规则分配到一条零收益腿上 ⇒ **2022–23 的书 = 0.79×fund(2023 另混入 22.6% 覆盖率的 F10), 是 fund-only 书, 不是在役 combo 形态**。"
"因此下面两表加入 2022/2023 行(双口径)并标注; 它们回答\"在役书的 fund 腿 2022–23 会怎样\", 不回答\"在役 combo 2022–23 会怎样\"。"
"**实盘形态的 2024 前数字需要**: ① 年折外 king(jpline `/mnt/storage/private/work_hsy/pod_backup_2026-08-21/slow_pred_hist_oos.npy`, 装置 L86 的默认加载物; pod 上 18 处同名文件全是 → `slow_pred_pinned.npy` 的符号链接, 无一是年折外件 [VERIFIED: gap_2 coverage `slow_pred_files`]); ② F10 2022–23 的 walk-forward 折(dlw 2022 finite 0 / 2023 0.226, 今日不存在)。二者今日均不可得(jpline: `ssh -o ConnectTimeout=8 jpline` → `Operation timed out`, 本条也只试一次)。"
"**2020–2021: UNAVAILABLE**——pod 无任何 king/F10 预测覆盖该段(meta E_ts 起 2022-01-08, dlw E_ts 起 2022-01-03, king 起 2022 且全 NaN), 只有 `wide_panel_4h_v1.npz`(ts 2020-01-31 → 2026-08-15, 14,329 行)有面板而无模型分数 [VERIFIED 同上], 书回放无从构造; jpline 链上存在 2021 行(AUDIT §3 2021 −70%), 但那是 CAL=simple + jpline king 的单仪器数字(见 §5.3b), 今日不可复现。\n\n")
ins_before(A_anchor, A_new)

# ---- B. §5.1 rows
B1_anchor="| 2024 | 2196 | −0.6421 | −1.682 | 1814.9 | 0.847 | −0.709 | — | — | −0.633(=−0.642+0.009) | — |\n"
B1_new=("| 2020–2021 | — | **UNAVAILABLE**(无 king/F10 预测; pod 仅 v1 面板) | | | | UNAVAILABLE | | | | |\n"
"| 2022 **[king=0, F10 absent ⇒ fund-only 书, 非在役形态]** | 2010 | −0.1203 | −0.322 | 821.9 | 0.886 | −0.098 | −0.267 | 852.7 | −0.094 | −0.430 / S −1.11 / maxDD 1232.8 |\n"
"| 2023 **[king=0, F10 仅 22.6% 覆盖 ⇒ fund-only 书, 非在役形态]** | 2190 | −0.3807 | −1.203 | 1238.6 | 0.872 | −0.404 | −1.269 | 1273.8 | −0.360 | −0.284 / S −0.89 / maxDD 1158.1 |\n")
ins_before(B1_anchor, B1_new)
B2_anchor="| **2024→26** | 5838 | **+0.4566** | **1.017** | **2613.7**(峰 2024-03-31 → 谷 2025-02-06) | 0.791(0.608–0.975) | **+0.4065** | **0.899** | **2657** | +0.4665 / 1.036 / 2604.7 | **+1.4731 / 3.139** |\n"
B2_new=("| 2022→23(fund-only 段, 非在役形态) | 4200 | −0.2561 | −0.742 | 1249.4 | 0.879 | −0.2573 | −0.752 | 1273.8 | −0.2329 / −0.678 | −0.3539 / −1.002 / 1678.5 |\n"
"| 2022→26 全样本(2022–23 为 fund-only, 混合形态, 只作信息) | 10038 | +0.1584 | 0.387 | 3519.1 | — | +0.1287 | 0.314 | 3637.6 | +0.1739 / 0.425 | +0.7087 / 1.667 / 3144.4 |\n")
ins_after(B2_anchor, B2_new)
B3_anchor="来源: Σ-simple 列 R-C6.0 `recompute.log`、R-C6.1 `recompute_stats.out`、R-C6.2 `recompute.py`(三票一致); Π 列 R-C6.1 `alt_stats.out` + R-C6.2 `run_alt.sh`(两票逐位一致); 只换窗列 R-C6.1(逐年 Δ +0.009/+0.029/−0.019)+ R-C6.2; 2026≤08-10 行 `pod_port_followup_stats.json`(R-C6.0/R-C6.2)。"
B3_new=(" **2022/2023 行来源(gap_2)**: 均值 = 装置自报 `RECEIPT_EX d30_n2_c42 … \"by_year_ex\": {\"2022\": -0.12, \"2023\": -0.381, …}`(R-C6.1 `pod_outputs/run_alt.out` L3 `alt_sum_old_w3fix`; R-C6.2 `REPORT.md` L431 同一行逐字), Π 列 `run_alt.out` L9 `alt_true_new_w3fix` `{\"2022\": -0.098, \"2023\": -0.404}`, 只换窗 L7 `alt_sum_new_w3fix` `{\"2022\": -0.094, \"2023\": -0.36}`, 旧 expm1 R-C6.2 `REPORT.md` §9.14 `pod_live_w3fix_calsimple_s42` `{\"2022\": -0.43, \"2023\": -0.284}`; n / Sharpe / maxDD / gross / 合段行 = gap_2 `pod_gap2_stats.py` 对 port `w10_ablation_series_pod_live_w3fix_{callog,calsimple}_s42.npz` 与 R-C6.1 `dev/probe_artifacts/w10_ablation_series_alt_*.npz` 直算(`gap2_stats.json`; 同一脚本对 2024–26 复得 −0.6421/−1.682/1814.9 等, 与本表既有格逐位同)[VERIFIED, 单仪器 pod]。")
ins_after(B3_anchor, B3_new)
B4_anchor="- **最差月**: **UNRESOLVED——无任何 tracer/refuter 计算月度序列**; 只有年 maxDD 与峰谷日期。\n"
B4_new=("- gap_2 副产物(单位不同, 仅供参考, 不解除上条 UNRESOLVED): 按 AUDIT §3 的公式(`jp_live_caliber_tables.py` L19-21: 2.0×net_ex/1e4 逐锚复利, 月内乘积−1, 单位 = NAV, **不除 gross**)在 port 固定席位 CAL=log 序列上算的最差月: 2022 −9.1% / 2023 −9.8% / 2024 −13.6% / 2025 −12.1% / 2026 −5.2%; CAL=simple: −9.1 / −10.5 / −11.2 / −9.0 / +0.6% [VERIFIED: gap_2 `pod_gap2_auditformula.py` → `gap2_auditformula.json`]。\n")
ins_after(B4_anchor, B4_new)

# ---- C. §5.2 rows
C1_anchor="| 2024 | +0.1489 | 0.533 | 0.602 | +0.116 | — | — | — |\n"
C1_new=("| 2020–2021 | **UNAVAILABLE**(同 5.1) | | | UNAVAILABLE | | | |\n"
"| 2022 **[king 腿=0, F10 absent; 席位非 fund-only: 前 900 锚 = [⅓,⅓,⅓] 且 LEGS 掩码未施加(含 rev24, 装置 L152), 其后 fund 回看 Sharpe ≤0 时退化为 [0.5,0,0.5](L171); w3_king 年均 0.225, 最大 0.5]** | +0.3128 | 0.897 | 0.819 | +0.325 | 0.944 | 467.2(Σ-simple 469.2) | −0.100 / S −0.27 / maxDD 772.0 |\n"
"| 2023 **[king 腿=0, F10 仅 22.6% 覆盖; w3_king 年均 0.066 ⇒ ≈ fund-only 书]** | −0.3732 | −1.213 | 0.837 | −0.412 | −1.331 | 1180.4(Σ 1142.7) | −0.295 / S −0.98 / maxDD 1126.2 |\n")
ins_before(C1_anchor, C1_new)
C2_anchor="| **2024→26** | **+0.6914** | **1.884** | 0.620(0.290–0.903) | **+0.685** | **1.881** | **967**(Σ-simple 为 794.9) | **+1.5975 / 3.998** |\n"
C2_new=("| 2022→23(非在役形态) | −0.0449 | −0.137 | 0.828 | −0.0595 | −0.182 | 1180.4(Σ 1142.7) | −0.2014 / −0.605 / 1245.1 |\n"
"| 2022→26 全样本(混合形态, 只作信息) | +0.3833 | 1.091 | — | +0.3735 | 1.070 | 1875.2(Σ 1673.3) | +0.8448 / 2.262 / 1282.3 |\n")
ins_after(C2_anchor, C2_new)
C3_anchor="来源同 5.1; 动态 Π 列 R-C6.2(逐年)+ R-C6.1(2024→26 +0.6850/1.881); 只换窗 Σ (E,E+4h]: +0.7263 / 1.970(R-C6.1/R-C6.2); R-C6.0 同窗 Π: +0.6302 / 1.727 / maxDD 999。**注意 2024 值受装置伪影影响(§4 C6 第 6 点, INFERRED)。**\n"
C3_new=("2022/2023 行来源: 均值 = R-C6.1 `pod_outputs/run_alt.out` L4 `alt_sum_old_dyn` `{\"2022\": 0.313, \"2023\": -0.373}`(R-C6.2 `REPORT.md` L98 `pod_live_callog_s42` 同值), Π 列 L10 `alt_true_new_dyn` `{\"2022\": 0.325, \"2023\": -0.412}`, 只换窗 L8 `alt_sum_new_dyn` +0.314/−0.375, 旧 expm1 R-C6.2 `REPORT.md` L100 `pod_live_calsimple_s42` `{\"2022\": -0.1, \"2023\": -0.295}`; Sharpe / maxDD / gross / w3_king / 合段行 = gap_2 `gap2_stats.json`(port `w10_ablation_series_pod_live_{callog,calsimple}_s42.npz`, R-C6.1 alt npz)[VERIFIED, 单仪器 pod]。\n"
"**2022–23 读法(两表共用)**: ① 这两年在两表里都是**负年份**(固定席位 Σ-simple −0.12/−0.38 bps/锚 ⇒ 按 AUDIT 公式 2.0× 复利 −6.4%/−16.2% NAV, CAL=simple 反而是 −18.4%/−12.6%: 伪凸性在 2022 把 fund-only 书压低 0.31 bps/锚, 在 2023 抬高 0.10——方向不恒定, 与 §4 C2 \"fund 高估 0.3–0.9\" 的 2024–26 结论不能外推到 2022–23)[VERIFIED: `gap2_auditformula.json`]。② 动态席位 2022 的 +0.31 **不是** fund-only 书的读数: 前 900 锚等权三腿含 rev24(装置 L152 在 `p < LOOK` 分支返回 `[1/3]*3` 且不施 LEGS 掩码), 其后当 fund 回看 Sharpe ≤ 0 时 `msk / msk.sum()` 把 0.5 席位放在零收益 king 腿上(L169-171)——2022 年 w3_king 均 0.225/最大 0.5 是这两条机械路径的产物 [VERIFIED: 装置行 + `gap2_stats.json` w3_king]; 2023 w3_king 均 0.066, 基本是 fund-only。③ 在役 combo(king 0.21 + F10 链 + fund)的 2022–23 期望**今日无法给出**(需 jpline 年折外 king + F10 2022–23 折, 见 §5 首段); 用户规则要求的 2021–2026 逐年表在 pod 单仪器下只能给到本表形态, 2021 UNAVAILABLE。\n")
ins_after(C3_anchor, C3_new)

# ---- D. reconciliation section before 5.4
D_anchor="### 5.4 T3c 与孤立臂(CAL=log, Σ-simple; **未在 Π 口径下重跑, UNRESOLVED**)\n"
D_new=("### 5.3b 对账: `AUDIT_live_vs_replay_2026-09-04.md` §3 / `RESULT_allweather_2026-09-04.md` §1(2024 −8% @2×)vs 本节 §5.1/§5.3(2024 −33% @2×)\n\n"
"**来源判定(VERIFIED)**: AUDIT §3 臂 C = tag `uni2_F_M7F_fx_s42`(`retrain_2026-09/jp_live_caliber_tables.py` L23), 从 jpline `probe_artifacts/w10_uni2_F_M7F_fx_s42.npz` 读 `d30_n2_c42_rec` 的 `net_ex`(L6-7); 该 npz 由 06:31:59Z 的 ssh 命令产出、06:33Z 出表(旧 transcript `6737834a…jsonl` 第 211810/211811 行; git 7e5967f 14:34+08 = 06:34Z 入库), env 逐字: `env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy OUT_TAG=uni2_F_M7F_fx_s42 UMASK_NPZ=$PD/umask_F_M7.npz FTRIM=zero W3FIX=0.21,0,0.79 … w10_universe.py`(模板 = `jp_universe2_runner.sh` L13 / `jp_universe2_round2.sh` L7, 均写死 `CAL=simple LEGS=101`)。"
"`RESULT_allweather` §1 的 C/E 基臂行是同两个 npz 被 `jp_allweather.py` L32 再读一遍(L18-19 同公式), 07:00Z 是文档时间, 不是新批次。故: **① 口径 CAL=simple(expm1 伪凸性, §4 C2)**; **② LEGS=101 而非 111**(此前对账假设\"臂 C LEGS=111\"不成立; LEGS=111 只出现在 RESULT_allweather §1 的 H3 行); ③ king = 装置 L86 默认 `{B}/slow_pred_hist_oos.npy`(jpline 年折外件, 无 SLOW_NPY 覆盖)而本节 = pod `slow_pred_pinned.npy`; ④ 宇宙 = meta members(top-400 天花板)∩ `umask_F_M7.npz`(冻结 450 月刷 + 7 日门, 只缩不扩, 装置 L70-82; 该掩码不在 pod: `find /workspace -name 'umask_*.npz'` 只有 umask_U0/U1/U2)而本节 = MEMBERS_TOPN=829 TRADE_TOPN=400; ⑤ 面板 = jpline hist meta/panel(止 08-15, 含 2021)而本节 = v2ext(止 08-30, 起 2022); ⑥ 换算 = `jp_live_caliber_tables.py` L19 `x=L*r/1e4; eq=np.cumprod(1+x); ann=eq[-1]**(2190/n)-1`: 2.0× 直接乘在**每单位 NAV** 的 net_ex 上逐锚复利, 不除 gross_total(其 L2 docstring 写的\"单位 gross\"是信念, 与 §5.3/R-C6.2 的换算链矛盾), 而 §5.3 的 −33% = 每单位 gross(÷0.847)× 2 的单利年化。\n\n"
"**2024 的 4× 差距分解(pod 自跑, 全部 VERIFIED; gap_2 `pod_gap2_armB.sh` + `pod_gap2_auditformula.py`)**:\n\n"
"| 步 | 序列 | 2024 @ AUDIT 公式 2.0× 复利 | Sharpe(ddof=0, 同 AUDIT) | DD 2× | 最差月 2× | 均值 bps/锚 |\n|---|---|---|---|---|---|---|\n"
"| 0 | §5.3 报法: 固定席位 live 形态 CAL=log, 每 gross ×2 单利 | −33%(§5.3) | −1.68 | — | — | −0.6421 |\n"
"| 1 换算路径 | 同一序列, 改用 AUDIT 公式 | **−25.6%** | −1.68 | −31.1% | −13.6% | −0.6421 |\n"
"| 2 口径 | 同形态 CAL=simple(port `pod_live_w3fix_calsimple_s42`) | **−15.8%** | −0.92 | −26.4% | −11.2% | −0.3582 |\n"
"| 3 形态 | 臂 B 同构: `MEMBERS_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 CAL=simple LEGS=101`(runner env 逐字, king=pinned, 面板 v2ext; gap_2 `dev/logs/commands.txt`) | **−15.5%** | −0.91 | −26.3% | −10.9% | −0.3523 |\n"
"| 3′ | 同上 CAL=log | −26.1% | −1.74 | −31.3% | −13.2% | −0.6577 |\n"
"| 4 jpline 残差 | AUDIT §3 臂 B(jpline, 同 env 同口径, king=hist_oos, 面板 hist) | **−8%** | −0.42 | −25% | −7.6% | — |\n"
"| 4′ | AUDIT §3 臂 C(= 臂 B + umask_F_M7) | **−8%** | −0.44 | −28% | −9.7% | — |\n\n"
"读法: −33 → −25.6 是换算路径(每 gross 单利 vs 每 NAV 复利, ×0.78); −25.6 → −15.8 是 expm1 伪凸性(2024 固定席位书 +0.284 bps/锚, ×0.62); −15.8 → −15.5 是 M829/T400 vs N400(2024 几乎不绑定, 与 R-C6.2 §9.11 一致); **−15.5 → −8(Sharpe −0.91 → −0.42)是 jpline 与 pod 的残差**——同 env、同口径、同装置 sha 语义下只剩 king 来源(jpline 年折外 vs pod pinned 2024 折)与面板谱系(jpline hist vs v2ext)两个变量, 今日 jpline 不可达, **UNRESOLVED**; 臂 C 的 umask_F_M7 在 2024 几乎不改变结果(臂 B −8%/−0.42 vs 臂 C −8%/−0.44, AUDIT §3 自身)。同一残差在其他年份更大(2025: pod 臂 B 同构 CAL=simple +61.8%/S 2.39 vs jpline 臂 B +45%/S 2.09; 2022: −18.6%/−1.13 vs −22%/−1.40; 2023: −12.3%/−0.86 vs −1%/−0.04——jpline 2022–23 有 king 预测而 pod 没有, 方向不恒定)。\n\n"
"**裁定**: AUDIT §3 全表、RESULT_allweather §1 全表及其 §0 结论(H1 σ_fund 阶梯\"录取候选\"、\"2024 −8→+3\"、H2/H3 逐年)都建立在 **CAL=simple(伪凸性)+ jpline 单仪器 + 面板止 08-15** 之上, 本稿标为 **CAL=simple-stale**(§7 #20): 相对判决(臂 vs 臂)是否存活需在 CAL=log 下重判, 绝对数字不得再引作实盘口径期望; `jp_callog_revalidate.sh` L6 已把复跑固定为 `LEGS=101 CAL=log`, 但其 L8-12 只覆盖 canon / N829T400F / T3c 五个 tag, **不含** AUDIT §3 的 `uni2_{F_M7F,F_QF,N400rF,N829T400F}_fx`(W3FIX+FTRIM+umask)臂——jpline 恢复后需按 `jp_universe2_runner.sh` 模板加 `CAL=log` 重产这四个 npz 再跑 `jp_live_caliber_tables.py` / `jp_allweather.py`。用户规则(ERROR_LEDGER L373; memory `feedback_report_live_caliber_full_cycle` \"引用前先查 AUDIT §3 表\")所指向的那张表本身即是陈旧口径, 规则的\"引用前先查\"应改指本节 §5.1/§5.2(含 2022–23 标注行)直至 jpline 复跑。\n\n")
ins_before(D_anchor, D_new)

# ---- E. §7 rows
E_anchor="| 19 | 5m 缓存 base 段(2022→2026-08-24)ch0=pct_change | 样本日 2022/2023/2024/2025 逐位 VERIFIED(R-C1.2)+ 平价门 assert(L54); 全段 INFERRED | 接受 |\n"
E_new=("| 20 | `AUDIT_live_vs_replay` §3 全表 + `RESULT_allweather` §0/§1(含 H1 阶梯录取候选、\"2024 −8→+3\")| **CAL=simple-stale**: 来源 env `CAL=simple LEGS=101`(`jp_universe2_runner.sh` L13; transcript 06:31:59Z)VERIFIED; jpline 单仪器; 面板止 08-15; 2024 −8% vs 本稿 −15.5%(同 env 同口径 pod 复跑)残差 = king 来源 + 面板谱系, UNRESOLVED(§5.3b) | jpline 恢复后按 runner 模板加 `CAL=log` 重产 `uni2_{F_M7F,F_QF,N400rF,N829T400F}_fx_s42.npz`, 重跑 `jp_live_caliber_tables.py`/`jp_allweather.py`; 两文档横幅先标 stale; memory `feedback_report_live_caliber_full_cycle` 的\"先查 AUDIT §3\"改指本稿 §5 |\n"
"| 21 | 在役形态 2022–23 与 2020–21 逐年数字(用户规则要求 2021–2026 全表) | 2022–23 只有 fund-only 书(king 腿恒 0 / F10 0%·22.6% 覆盖, §5.1/§5.2 标注行, VERIFIED); 在役 combo 形态需 jpline `slow_pred_hist_oos.npy` + F10 2022–23 折, 今日 UNAVAILABLE; 2020–21 pod 无任何模型分数(仅 v1 面板), UNAVAILABLE | jpline 恢复: 用年折外 king 重跑 §5 两表 2022–23; F10 2022–23 折需训练 → 单独预注册; 2020–21 需 king/F10 训练覆盖, 否则永久标 UNAVAILABLE |\n"
"| 22 | pod 臂 B 同构 vs jpline 臂 B 的逐年残差(2024 −15.5% vs −8%, 2023 −12.3% vs −1%, Sharpe 差 0.4–0.8) | 观察到, 变量只剩 king 来源与面板谱系, 未分离 | jpline 恢复后: 同 env 在 jpline 跑 `SLOW_NPY=slow_pred_pinned.npy`(king 单变量), 再换面板 |\n")
ins_after(E_anchor, E_new)

open(P,"w",encoding="utf-8").write(t)
print("OK; new length", len(t))
