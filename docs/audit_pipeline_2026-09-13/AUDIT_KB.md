> **创建:** 2026-09-16T04:21:32Z | **Session:** aud-kb (team audit, read-only) | **状态:** 审计登记(只读; 不改任何源文件与记忆; 更正由 lead 复核后应用) | **作废条件:** 被登记的源文件或记忆条目改动后对应行需复核; 新收据推翻本登记的任一 superseding 证据

# AUDIT_KB · 评估装置与知识库陈旧结论审计(2026-09-13)

## §0 One page

**Scope.** Read-only audit of evaluation devices and the knowledge base (CLAUDE.md, STATE.md, MILESTONE/CANDIDATE/CHECKLIST 08-26, ERROR_LEDGER, uplift r2/r3 programmes and results, uplift CLOSEOUT 09-12, MEMORY.md and its 262 linked notes, judge_v4 and T/L/P2 label predicates, per-anchor deep-check template). No source document, memory note, device or live file was edited. Each row gives the exact quote with file:line, the superseding receipt quoted with file:line, the reading a future user could wrongly take, and exact replacement text for the lead to apply.
**What changed since those texts were written, in one paragraph.** The live book is no longer 77/13/10: the msharpe seat rolls every anchor and read king 0.3821 / fund 0.6179 at 2026-09-13 12Z and king 0.3780 / fund 0.6220 at 2026-09-16 00Z (durable receipt `~/regime_dash/regime_dash.jsonl`, keyed by `anchor_utc` — see DEV-14). The combo admission evidence (Δnet +0.29..+0.43, all significant, Sharpe 2.18→2.7–3.0, and the leverage table where 2.0× never touches −25%) was on the CAL=simple caliber. Re-tested on correct calibers, seed-42 significance is gone, the gain comes from dropping rev24 rather than from V2MAIN, and 2025 reverses. v4 compounded 2× NAV drawdown is −28.92% in 2023 and −42.12% over W_ALPHA. 'Fund leg = the book', 'model-leg seat ≤0.21' and '78% dominance premium' do not hold on the v4 device: the dynamic king seat averages 0.46 over the full cycle and 0.71 in 2024–25, the fund-only book has Sharpe 0.63 against 1.42 for the seat-timed book, and A0's correlation with the alt−BTC spread is +0.05. Whether deployment differences caused the live shortfall is neither shown nor excluded: T5d leaves −4.15..+1.71 bps/anchor open, and T4's NOT MATERIAL comes from a significance gate with no equivalence band. The combo rollback verb 'kill the daemon PID' has been ineffective since launchd KeepAlive was adopted on 08-30.
**Live-relevant first.** Three P0 rows share one defect family: the documented emergency rollback or incident procedure would not do what it says. KB-09 (STATE §1) and CRON-01 (deep-check ⑥) are the kill-PID rollback under launchd KeepAlive. The lead confirmed this on a same-shape dummy launchd job (drill2: kill → respawn within 1 s; bootout → no respawn) and already corrected STATE §1 in b63a0144; the template is not yet corrected. M3-35 is the memory note's stale revert-chain rollback onto a tree that has since received W6ab/W2/W1/W9. None of these changes live behaviour by itself; each would mislead an operator during an incident.
**The Sharpe citation rule (FXR-DOC-3, adopted 2026-09-16).** Every citation of "1.29" must carry its window: **W_ALPHA 2022-06-30 00Z → 2026-08-30 20Z, 9,138 anchors, 1.29122344, CI95 [0.3207, 2.2822]** — an *exploratory* 2,000-resample UTC day-block bootstrap that keeps intraday dependence and not cross-day, and is **not** a selection-corrected interval. T6's **W_FULL** (from 2022-01-31, 10,038 anchors, the same set CANONICAL_NUMBERS §5 calls `W_TAIL`) is **1.1062**. A third variant at 9,139 anchors / **1.2947** exists and must never be mixed in. The cost plane must be named too: the same book reads 0.6342 / 1.2912 on the fitted plane and 0.688853 / **1.4025** on the deployed fee-only plane. Two derived readings are withdrawn as settled quantities: **N_eff ≈ 1.57 is a participation ratio, not a count of effective independent trials**, and **0.30 is not a posterior probability that the true Sharpe exceeds 3** — it is one substitution among several spanning 0.30 → 0.005. Rows KB-63..KB-68 carry the per-citation corrections; the binding itself belongs at `CANONICAL_NUMBERS_2026-09-12.md` (KB-67).
**Id-namespace collisions (KB-69/70 APPLIED in `5642fbc2`; KB-74 / KB-75 still open).** `FIXPROGRAM` and the four audit registers share one id namespace — §13.1 proved it by cross-referencing "AUDIT_PROD PROD-28" by number. The lead renumbered **seven** PROD ids to PROD-41..47 (this register found five; the lead's own sweep added PROD-35 and PROD-36b from §14.2) and added a standing rule that new ids be checked against all four registers first. Sweeping the same ruler across every other id opened in §13–§17 leaves **one live collision, TRN-28 (KB-74)**: §15.2 opens it as a P1 owned by FX-TRAIN while §3.2 of the same document already routes AUDIT_TRAIN's TRN-28 to K4 — one id, two owners, two severities; TRN-30+ is free. Everything else opened there is clean (OPS-04, LED-09, RES-01, TEST-01, BAT-01, EXEC-RACE-01, DATA-COR-1, W6C-I6, MON-1..4, FXR-*). Two further collisions **predate the programme** and are not the lead's: **AUDIT_EXEC and AUDIT_DATA each define `LED-01` and `DOC-01`** for different findings (KB-75). Those should be cited with a register prefix rather than renumbered, because renumbering a published register dangles every existing citation.
**A register-level receipt repair (DEV-14).** Ten rows cited `~/regime_dash/REGIME_DASH.md` for the masked seat. That file is rewritten every anchor, so the quoted line was gone by assembly time. The same reading is re-verifiable in the append-only `~/regime_dash/regime_dash.jsonl`: **2026-09-13T12:00Z king 0.3821 / fund 0.6179** (= the quoted 0.382/0.618), and **2026-09-16T00:00Z king 0.3780 / fund 0.6220**. All ten receipts are repointed. The rule stands on its own: a rolling file is not a receipt.
**A caliber item on every battery count (KB-73).** 「逐套件 N/M」 receipts are comparable only under one interpreter. The runner pins `PY="${ACCEPT_PY:-/usr/bin/python3}"` (3.9.6, the only one with torch) against a bare `python3` that resolves to 3.14.4 with no torch — but the pin is an **overridable default**, the suite certifying it checks only that the *string* appears in the source, and **0 of 38,177 artefacts in `state/acceptance/` record which interpreter ran**. Before 2026-07-27 the two entry points disagreed, and the bare one manufactured two false 「known failures」. Rows KB-12, KB-13, KB-35, M3-35 and M5-02 cite such counts and now carry the caveat.

**Rows: 312.** Status: DOC_STALE 279 · OPEN_NOT_MEASURED 18 · PENDING_USER_DECISION 5 · VERIFIED_CURRENT 10. Severity: P0 3 · P1 63 · P2 151 · P3 95.

| area | rows | P0 | P1 | P2 | P3 |
|---|---|---|---|---|---|
| Core knowledge-base documents | 76 | 1 | 22 | 38 | 15 |
| Memory notes (MEMORY.md and linked notes) | 205 | 1 | 38 | 96 | 70 |
| Evaluation devices | 17 | 0 | 3 | 10 | 4 |
| Per-anchor deep-check template | 14 | 1 | 0 | 7 | 6 |

### Top 18 (severity first, then blast radius)

| # | id | sev | status | where | stale claim | proposed correction (abridged; full text in the row) |
|---|---|---|---|---|---|---|
| 1 | KB-09 | P0 | DOC_STALE | `STATE.md:146 (text before lead commit b63a0144)` | **回滚**: `kill $(cat ~/wide_shadow/fea171/combo_live_daemon.pid)` ⇒ 下一锚起 king 三腿形态 | **回滚**: combo 守护自 2026-08-30 起由 launchd `com.hsy.combolive` 管理(KeepAlive: 非 0 退出即拉起, 演练受据 30942→30977), 直接 `kill` PID 会被重启, **不构成回滚**。回滚动词 = `launchctl bootout gui/$(id -u)/com.hsy.combolive`(必要时先 `launchctl disable gui/$(id -u)/com.hsy.combolive` 防重登复活), 随后核  |
| 2 | CRON-01 | P0 | DOC_STALE | `docs/CRON_TEMPLATES_2026-09-04.md:16` | 整体回滚=kill combo_live_daemon.pid 内 PID | ⑥ 异常处置: 回滚缺省=king 形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`; **整体回滚(临时)= `launchctl bootout gui/$(id -u)/com.hsy.combolive`**(08-30 起 launchd KeepAlive, kill PID 会 1 s 内被拉起, 不是回滚; 同形哑任务演练收据 `docs/fixprogram_2026-09-13/receipts/OPS_ |
| 3 | M3-35 | P0 | DOC_STALE | `memory/review_b0a573a1_closure_and_merge_deploy_protocol_2026_09_09.md:11` | 运行树 = origin/main = **77d9baf**, 电池 **132/132**, safe_commit 门畅通(见 [[disposition_matrix_ruler_recalibration_and_names_truncation_2026_09_12]]); 52 行写回(RUNBOOK §4)另裁; 回滚 = §5 revert | [在第一个「状态」段之前插入] **状态 2026-09-13 12:0xZ(最新, 先读这段; 覆盖以下两段)**: 运行树 = origin/main = **ef60f85**(918559f + W6ab 259f50a6 → W2 2ad1c272 → W1 62a3032e → W9 f8beb082, 一次 safe_commit, 电池 ALL GREEN 135/135), 12Z 复场首锚验收通过(STATE.md 顶部)。下文 77d9baf/132 与「回滚 = §5 revert 链」均已 |
| 4 | KB-69 | P1 | DOC_STALE | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:258` | \| **PROD-30** \| G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定** | [§13.1 表内原编号字节保留, 在 §13.1 表下插入] ⚠ **2026-09-16 编号更正(aud-kb KB-69)**: 本表的 **PROD-30 / 31 / 32 / 33 / 34 与 `AUDIT_PROD`(ee2a8c4d)已占用的同号项冲突**, 而本表自身又按号引用「AUDIT_PROD PROD-28」⇒ 两表同命名空间。**AUDIT_PROD 已用到 PROD-40, 空号自 PROD-41 起**。按下表重编, 原号保留并标 SUPERSEDED-ID: **PROD-30 |
| 5 | KB-70 | P1 | DOC_STALE | `STATE.md:144` | 登记为 PROD-30, 待用户裁定, 属书行为 | [替换该句, 原句字节在 FIXPROGRAM §13.1 与本登记内保留] 登记为 **PROD-41**(原写 PROD-30; 与 `AUDIT_PROD` ee2a8c4d 的 PROD-30 = exec_n6 沙箱生产者 撞号, 2026-09-16 按 aud-kb KB-69 重编), 待用户裁定, 属书行为。 |
| 6 | KB-64 | P1 | DOC_STALE | `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97` | **A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。** | [在该行后插入] > ⚠ **2026-09-16 更正(独立复审 FXR-DOC-3 + CANONICAL_NUMBERS §0-5/§0-3)**: 本规划数的**窗与成本面必须同时写出** —— **W_ALPHA(2022-06-30 00Z → 2026-08-30 20Z, 9,138 锚)· 拟合成本面 `costb_PWR_G230k.json`(sha 295b4e7b…)**, 夏普 **1.29122344** CI95 **[0.3207, 2.2822]**(探索性 2,000 次 UT |
| 7 | KB-16 | P1 | DOC_STALE | `STATE.md:201` | 杠杆升级(候选 2.0× 历史不触 −25% 线) | 杠杆: 2.0× 已于 08-27 生效; v4 口径固定 2× 逐锚复利 NAV maxDD: 2023 −28.92%, 2024 −23.62%, W_ALPHA 全窗 −42.12%(r18 表勘误 3), 旧「2.0× 历史不触 −25% 线」为 CAL=simple 作废口径; 尾部为下界(E-0908-B) |
| 8 | KB-06 | P1 | DOC_STALE | `CLAUDE.md:42` | \| 在役书证据/杠杆/局限 \| `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` \| | \| 在役书证据/杠杆/局限 \| 在役形态水平与逐年/回撤 = `uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md`(含勘误: 固定 2× 复利 NAV maxDD); combo 选型在正确口径下的复测 = `retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md`; `docs/CANDIDATE_wide_v2main_norev24_20 |
| 9 | KB-37 | P1 | DOC_STALE | `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:6` | **部署差不是主因**(T4/T4b/T5/T5c) | **部署差未检出也未排除**(T4 NOT MATERIAL 仅显著性门、无等价带; T5 八月 carry 差 = 构造差; T5d 九月价格部署/模型差 −4.15..+1.71 bps/锚不可排除, 为 A0 全周期净额 1.6–3.2 倍; V2MAIN 与执行器层未测) |
| 10 | KB-05 | P1 | DOC_STALE | `CLAUDE.md:28` | 记账口径 = `pod_dlw_targets_ext.py` L93 的 y4s = Π(1+r)−1 | 记账口径 = RAW Π(1+r)−1(v4 记账元 `meta_newprod_v4.npz` / `pod_dlw_targets_raw.py`, 见 `uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`); `pod_dlw_targets_ext.py` L93 是对 ±0.30 裁剪缓存的复利(E-0908-B), 只作对照; 禁止从 5m 缓存 ret5 重算收益; 回撤按固定 2× 逐锚复利 NAV 报 |
| 11 | KB-01 | P1 | DOC_STALE | `CLAUDE.md:14` | 构成 ≈77% funding 动量 + 13% king LGBM + 10% V2MAIN 书损失 DL | 构成随 msharpe 席位逐锚滚动, 不是常数: 08-26 00Z 掩码席位 king 0.232 ⇒ ≈77% fund/13% king/10% V2MAIN; 09-05 播种后 0.300; 2026-09-13 12Z king 0.382 / fund 0.618 ⇒ ≈62% funding 动量 + 21% king LGBM + 17% V2MAIN(读数来源 ~/regime_dash/regime_dash.jsonl(追加式, 按 `anchor_utc` 取 `w3_masked_ki |
| 12 | KB-21 | P1 | DOC_STALE | `docs/MILESTONE_2026-08-26.md:29` | **fund 腿 = 书本体**(去掉 4/4 年由盈转亏 −3.04 CI[−3.86,−2.20]); **king = 组合内方差压制者**(仅king 单腿书 −2.74 亏钱; 去king ΔSharpe CI 全负) | (CAL=simple 口径, E-0904-F 作废, 腿层判决待重立)fund 腿 = 书本体 … king = 方差压制者。⚠ v4 口径席位阶梯(`uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md` §3): 动态 msharpe 席位 king 均权 2024 0.71 / 2025 0.71 / 2026 0.36 / 全周期 0.46; 固定 king 0(纯 fund)全周期 Sharpe 0.63 vs 动态 1.42 ⇒ 书的 |
| 13 | KB-23 | P1 | DOC_STALE | `docs/MILESTONE_2026-08-26.md:44` | 书=主导率保费(78%)+残差 alpha —— 对冲毁书 | 书=主导率保费(78%)+残差 alpha(08-21 在役书 S1 / 引擎 Y4 仪器)。⚠ T8 §6.1: A0 v4 书同期 corr(净额, 等权山寨−BTC 价差) = +0.05 / +0.04, 逐折 β 为正 ⇒「78%」不适用于在役 combo/v4 形态, 两仪器矛盾待对账; 对冲/中性化提案不得以此句否决。 |
| 14 | KB-45 | P1 | DOC_STALE | `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:121` | What must be lowered is any planning or target number built on a best-candidate backtest: subtract at least 0.65 SR (full cycle) / 1.56 SR (frozen window). | 在 §8 前插入: ⚠ 复审第四轮(REVIEW_round4 §4.2)与 STATE 2026-09-13 12:1xZ ③ 撤回三处读法: (1) N_eff 参与比是谱维数, 不是已校准的有效试验数; (2) −0.65/−1.56 是本家族在已实现选择路径上的描述, 不是今后任意候选的最低折价下界; (3) 0.30/0.0047 是不同 N 假设下的代入读数, 不是真 Sharpe>3 的概率。仍成立: 候选家族高度相关、冻结窗高水平为全家族共有、A0 冻结窗 CI95 [1.306, 4.565] 不 |
| 15 | KB-50 | P1 | DOC_STALE | `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:11` | 实盘变差的真因不是执行、不是延迟、不是平滑、不是模型陈旧 | 实盘变差的原因未识别: T1 五假设四条不可判(落差本身不显著, 实盘窗状态对全史不反常); 八月部署书 carry 为回放 2.19 倍 = 构造差(FTRIM 缺席 58% / 暖启动态 27% / 回放止损层 18.5%); 九月部署/模型差 −4.15..+1.71 bps/锚不可排除(T5d); 执行/延迟/平滑未单独排除 |
| 16 | KB-20 | P1 | DOC_STALE | `docs/MILESTONE_2026-08-26.md:12` | 回放证据: 三种子 Δnet +0.29~+0.43 bps/锚 全显著(基线夏普 2.18 → 2.7-3.0)。 | 回放证据(CAL=simple, 已作废口径): 三种子 Δnet +0.29~+0.43。⚠ 正确口径复测(`review_caliber_wf/combo_recheck/REPORT.md`, 09-04): 方向保住, s42 显著性不保(D−A 2024→26 +0.108 [−0.101,+0.312] CAL=log / +0.203 [−0.022,+0.439] 复利), 归因反转(V2MAIN 单独 ≈0, 唯一 CI 排零的是「去 rev24」), 2025 反转; 「基线 2.18 → 2. |
| 17 | DEV-01 | P1 | PENDING_USER_DECISION | `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:349` |             v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED") | 判官 (A) 追加两个条件(预注册修订, 用户裁定): ① 双种子 CI 下界 > δ(K2 D1 = 0.05 bps/锚/gross, 非 0); ② 全周期逐年(2023–2026)无一年 Δ 的 CI 上界 < −δ, 且 2023(弱年)点估计 ≥ −δ; 冻结窗之外的扩展/逐年读数写入 verdict 旁并在 (A) 时强制打印 |
| 18 | KB-31 | P1 | DOC_STALE | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:28` | **+0.374 [+0.15,+0.60] ★** | 在 §2 表头下插入: ⚠ 本表全部为 CAL=simple(对 Σ简单 y4 做 expm1 的伪凸性口径, E-0904-F), 数字作废。正确口径复测(combo_recheck/REPORT.md): D−A 2024→26 s42 +0.108 [−0.101,+0.312](CAL=log)/ +0.203 [−0.022,+0.439](复利), 仅 s2027 复利口径 CI 排零; V2MAIN 单独 ≈0; 唯一 CI 排零的是「在混 V2MAIN 前提下去 rev24」; 2025 候选劣于在 |

## §1 How to read a row

- **status**: DOC_STALE = a later receipt contradicts or qualifies the claim and the source does not carry that correction inline; OPEN_NOT_MEASURED = presented as settled but never measured on the current caliber/device; PENDING_USER_DECISION = the correction depends on a user ruling; VERIFIED_CURRENT = checked and still true (listed only where a reader might suspect it).
- **severity**: P0 = if followed, a wrong live action or a failed emergency procedure; P1 = misleads a book-behaviour, deployment, leverage, retrain or evaluation decision; P2 = misleads research planning or reported numbers; P3 = low risk, or already corrected elsewhere in the same file.
- **affects**: future_eval / future_retrain / reporting / live_trading.
- **Proposed correction** is exact text in the source's language, to insert or to replace the quoted span; the lead applies it after review. Where a row says INFERRED, the runtime behaviour was inferred from configuration and receipts, and nothing was executed.
- Every quote was re-located by exact substring against the file on disk when this register was assembled, so line numbers are current as of then. The lead is editing memory notes concurrently, so some rows may already be partly applied.

## §2 Core knowledge-base documents (76 rows)

Rows KB-01..KB-60. Composition, leverage, rollback and evidence claims are repeated across CLAUDE.md, STATE.md, MILESTONE, CANDIDATE and CHECKLIST. Each file gets its own row because the replacement text differs per file.

| id | sev | status | affects | source | claim (abridged) |
|---|---|---|---|---|---|
| KB-09 | P0 | DOC_STALE | live_trading | `STATE.md:146 (text before lead commit b63a0144)` | **回滚**: `kill $(cat ~/wide_shadow/fea171/combo_live_daemon.pid)` ⇒ 下一锚起 king 三腿形态 |
| KB-01 | P1 | DOC_STALE | reporting, future_eval | `CLAUDE.md:14` | 构成 ≈77% funding 动量 + 13% king LGBM + 10% V2MAIN 书损失 DL |
| KB-05 | P1 | DOC_STALE | future_eval, future_retrain | `CLAUDE.md:28` | 记账口径 = `pod_dlw_targets_ext.py` L93 的 y4s = Π(1+r)−1 |
| KB-06 | P1 | DOC_STALE | future_eval, live_trading, reporting | `CLAUDE.md:42` | \| 在役书证据/杠杆/局限 \| `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` \| |
| KB-07 | P1 | DOC_STALE | future_eval | `CLAUDE.md:44` | \| 恢复研究某条轴 / DNR \| `docs/MILESTONE_2026-08-26.md` §2/§5(08-11 前的查上期) \| |
| KB-10 | P1 | DOC_STALE | reporting, future_eval | `STATE.md:143` | 构成 ≈ 77% fund + 13% king(LGBM) + 10% V2MAIN(可微书损失 DL, 171 列) |
| KB-16 | P1 | DOC_STALE | live_trading, reporting | `STATE.md:201` | 杠杆升级(候选 2.0× 历史不触 −25% 线) |
| KB-20 | P1 | DOC_STALE | future_eval, reporting | `docs/MILESTONE_2026-08-26.md:12` | 回放证据: 三种子 Δnet +0.29~+0.43 bps/锚 全显著(基线夏普 2.18 → 2.7-3.0)。 |
| KB-21 | P1 | DOC_STALE | future_eval, reporting | `docs/MILESTONE_2026-08-26.md:29` | **fund 腿 = 书本体**(去掉 4/4 年由盈转亏 −3.04 CI[−3.86,−2.20]); **king = 组合内方差压制者**(仅king 单腿书 −2.74 亏钱; 去king ΔSharpe CI 全负) |
| KB-23 | P1 | DOC_STALE | future_eval, reporting | `docs/MILESTONE_2026-08-26.md:44` | 书=主导率保费(78%)+残差 alpha —— 对冲毁书 |
| KB-25 | P1 | DOC_STALE | future_eval | `docs/MILESTONE_2026-08-26.md:50` | **对数→简单收益总更正**(SR 57038bd): 9821 锚族绝对数全部重表; 可交易口径=简单持有收益。 |
| KB-26 | P1 | DOC_STALE | live_trading, reporting | `docs/MILESTONE_2026-08-26.md:71` | 杠杆升级(2.0× 历史不触线, 归用户) |
| KB-29 | P1 | DOC_STALE | future_eval, reporting | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:3` | **状态:** 回放证据完备, 前向影子已起跑, **未部署**(书行为改动归用户) |
| KB-31 | P1 | DOC_STALE | future_eval, reporting | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:28` | **+0.374 [+0.15,+0.60] ★** |
| KB-32 | P1 | DOC_STALE | live_trading, reporting | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:56` | **2.0× 在候选下历史不触 −25% 线** |
| KB-34 | P1 | DOC_STALE | live_trading | `docs/CHECKLIST_combo_switch_2026-08-26.md:22` | ③ 整体回滚 = kill 守护 PID(下一锚起自动 king 形态), 不动任何其他组件 |
| KB-37 | P1 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:6` | **部署差不是主因**(T4/T4b/T5/T5c) |
| KB-45 | P1 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:121` | What must be lowered is any planning or target number built on a best-candidate backtest: subtract at least 0.65 SR (full cycle) / 1.56 SR ( |
| KB-46 | P1 | PENDING_USER_DECISION | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:156` | at least −0.65 SR full cycle and −1.56 SR frozen window from T6, both lower bounds. |
| KB-50 | P1 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:11` | 实盘变差的真因不是执行、不是延迟、不是平滑、不是模型陈旧 |
| KB-64 | P1 | DOC_STALE | reporting, future_eval, live_trading | `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97` | **A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。** |
| KB-69 | P1 | DOC_STALE | reporting, future_eval, live_trading | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:258` | \| **PROD-30** \| G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定** |
| KB-70 | P1 | DOC_STALE | live_trading, reporting | `STATE.md:144` | 登记为 PROD-30, 待用户裁定, 属书行为 |
| KB-02 | P2 | DOC_STALE | reporting, future_eval | `CLAUDE.md:13` | maker-only, gross 2.0×NAV(2026-09-03 入金后 constant_leverage_2.00; 此前 1.5×) |
| KB-04 | P2 | DOC_STALE | future_eval, future_retrain | `CLAUDE.md:15` | 宽面板/判官在 jpline `/mnt/storage/private/work_hsy/` |
| KB-08 | P2 | DOC_STALE | future_retrain, reporting | `CLAUDE.md:47` | \| 月度重训 \| `docs/RUNBOOK_monthly_retrain_2026-09.md` \| |
| KB-13 | P2 | DOC_STALE | live_trading, reporting | `STATE.md:129` | σ_fund gross 阶梯已上线(执行器 4b8ca20 电池 124/124; 仪表盘作业 com.hsy.sigma_ladder N+52) |
| KB-14 | P2 | DOC_STALE | future_eval, future_retrain | `STATE.md:128` | 未换装前线上 = v3 旧链(书层已证不可区分) |
| KB-15 | P2 | DOC_STALE | reporting, future_eval | `STATE.md:23` | k 窗 180s 已据此上线 |
| KB-17 | P2 | DOC_STALE | future_eval | `STATE.md:250` | 回放装置 CAL=simple 分支作废, 一律 CAL=log 或复利目标 |
| KB-19 | P2 | DOC_STALE | reporting | `docs/MILESTONE_2026-08-26.md:8 (+1 more)` | 构成 ≈ 77% funding 动量 + 13% king LGBM + 10% V2MAIN, gross 1.5×NAV, maker-only, 4h 锚。 |
| KB-22 | P2 | OPEN_NOT_MEASURED | future_eval | `docs/MILESTONE_2026-08-26.md:34` | 2×2 终版: 目标效应 +0.488 / 弹药效应 +0.267 / 交互 +0.451; **换目标单独≈0, 换弹药单独判负, 合并才 +0.305**。 |
| KB-24 | P2 | DOC_STALE | live_trading, reporting | `docs/MILESTONE_2026-08-26.md:40` | 书自带隐式止损(在役止损≈免费保险) |
| KB-27 | P2 | DOC_STALE | reporting, future_eval | `docs/MILESTONE_2026-08-26.md:86` | ~~⑦ funding极端空头处理~~ **已判 DNR** |
| KB-28 | P2 | OPEN_NOT_MEASURED | future_eval | `docs/MILESTONE_2026-08-26.md:66` | **已判负 DNR**(2026-08-26 04:0xZ, 双种子同座替换门 FAIL |
| KB-30 | P2 | DOC_STALE | reporting | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:17` | 最终构成 ≈ **77% fund + 13% king + 10% V2MAIN** |
| KB-33 | P2 | PENDING_USER_DECISION | future_eval, live_trading | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:73` | DSR 折价适用 ⇒ **前向影子为终审** |
| KB-35 | P2 | DOC_STALE | live_trading, reporting | `docs/CHECKLIST_combo_switch_2026-08-26.md:34` | \| **combo_live_daemon(PID 72287)** \| |
| KB-39 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:24` | 零成本收入流 SR 12–44、ρ≈0, 但冻结换仓规则下净额为负(收入 +1.7 vs 换手成本 4.5 bps/锚), 2023 年 71% 锚无合格名; **滞回换仓未评估** |
| KB-40 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:193` | 问题在策略本身对普涨挤空 / 暴涨回调行情的响应, 不在部署差 |
| KB-41 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:172 (+1 more)` | 冻结规则下 NOT MATERIAL |
| KB-44 | P2 | DOC_STALE | reporting | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:92` | 据此 900s→180s 已上线 |
| KB-47 | P2 | DOC_STALE | future_eval, live_trading | `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:36` | 第三分量是设计差: 回放有逐名止损层, 生产没有 |
| KB-48 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:9` | **判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)。** |
| KB-51 | P2 | DOC_STALE | future_eval | `docs/ERROR_LEDGER_2026-08-20.md:416` | **装置 CAL=log 分支 = 原始 y4 = 无偏简单口径**(与真简单差 −0.04 bps/锚), 复验一律用 CAL=log |
| KB-52 | P2 | DOC_STALE | future_eval, future_retrain | `docs/ERROR_LEDGER_2026-08-20.md:302` | **规则**: 席位敏感臂必须附"实盘席位固定"回放(W3FIX)作稳健性; 引用 2026 回放数字时声明"fund 0.99 构成" |
| KB-53 | P2 | DOC_STALE | reporting, live_trading | `docs/ERROR_LEDGER_2026-08-20.md:24` | → 政策 A 全不追。**已闭环**。 |
| KB-54 | P2 | OPEN_NOT_MEASURED | future_eval | `docs/ERROR_LEDGER_2026-08-20.md:17` | 受据: 该保费=历史利润 34%, β中性化毁 1/3 书 → 五臂全负 DO-NOT-RETRY |
| KB-56 | P2 | DOC_STALE | reporting, future_eval | `STATE.md:159` | 动态席位(规则)2024→26 +1.21 bps/锚/gross, Sharpe 2.2, 2× 年化 +53% / 回撤 23%(2024 +24%, 2025 +28%, 2026 +140%) |
| KB-59 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:16` | 3. **重新加权到不了**: ~300 候选都进同一个席位, 与在役书 ρ≈0.9, 上限约 +0.8 夏普; 缺口需要**互不相关的书**。 |
| KB-60 | P2 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:47` | **它们全都是同一个下注的重新加权。** |
| KB-63 | P2 | DOC_STALE | reporting, future_eval | `docs/STATUS_three_questions_2026-09-12.md:28 (+1 more)` | 全周期 1.29 |
| KB-65 | P2 | DOC_STALE | reporting, future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12` | 2. **全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举) |
| KB-66 | P2 | DOC_STALE | future_eval, reporting | `docs/HANDOFF_round4_review_request_2026-09-13.md:77` | - F1 125 个全书配置 N_eff 1.57(几乎一本书); PBO 0.157 / 0.187 未触发, 但由事后预选线 XIB_LAG50 撑着; r8–T2 家族 F3 PBO 0.508 触发; 选择折价下界 −0.65(全周期)/ −1.56(冻结窗), CI 含 |
| KB-67 | P2 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:36` | 5. **Two windows, never mixed.** `W_ALPHA` n=**9138** (drop first 900 warm anchors, E-0911-A; ceiling 2026-08-30 20Z, E-0911-D) for every me |
| KB-68 | P2 | DOC_STALE | reporting, future_eval | `STATE.md:66` | A0 全周期 post-warm **1.4150** [0.449,2.381] n=9018; 加 E-0911-D 截断 **1.2912** [0.332,2.251] n=9138 |
| KB-72 | P2 | DOC_STALE | live_trading, reporting | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:267` | **PROD-31(无文件)不进该分裂, 一律 HIGH** |
| KB-73 | P2 | OPEN_NOT_MEASURED | reporting, future_eval | `CLAUDE.md:46` | \| 部署/回滚/电池 \| `~/dl_quant_live/ops/safe_commit.sh` + `run_acceptance.sh` \| |
| KB-74 | P2 | DOC_STALE | future_retrain, reporting | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:311` | \| **TRN-28** \| `pod_f10_np_export.py` 在**自己的 V1 门判词之前**就写出可部署 npz |
| KB-75 | P2 | DOC_STALE | reporting, future_eval | `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:88` | \| LED-01 \| ledger / fills.jsonl \| fills.jsonl holds every trade exactly twice; in-repo readers collapse the copies, a naive reader double co |
| KB-76 | P2 | DOC_STALE | future_eval, future_retrain | `docs/fixprogram_2026-09-13/FX_DATA/FACT_TABLE_DATA.md:129` | whose anchor state is **NODATA** (no 5m rows in the window) yet which carries `f_fund_now` = **−205.7 bps** 8h-equivalent on the panel row |
| KB-03 | P3 | DOC_STALE | reporting | `CLAUDE.md:14` | N+23 读取交易 |
| KB-11 | P3 | DOC_STALE | reporting | `STATE.md:142` | N+23 读并交易 |
| KB-12 | P3 | DOC_STALE | reporting | `STATE.md:149` | `~/dl_quant_live/ops/safe_commit.sh` + 电池 123/123 |
| KB-18 | P3 | DOC_STALE | future_eval | `STATE.md:255` | 无干净 CONST2027 |
| KB-36 | P3 | DOC_STALE | reporting | `docs/CHECKLIST_combo_switch_2026-08-26.md:45` | 3. fund 构成升至 ~77%(候选结构属性, 已在正典文档 §3 局限声明)。 |
| KB-38 | P3 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:17` | (未复跑; carry/净额数字 PROVISIONAL, 价格读数不受影响) |
| KB-42 | P3 | DOC_STALE | reporting, future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:8` | **实盘亏在资金费, 不在价格也不在执行** |
| KB-43 | P3 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:27` | 回放可用于定位, 幅度按 0.835 折算 |
| KB-49 | P3 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:12` | ⇒ **NOT MATERIAL**, 标 **PROVISIONAL** |
| KB-55 | P3 | DOC_STALE | reporting | `docs/ERROR_LEDGER_2026-08-20.md:6` | 任何 \|单锚\|>2σ(实测 σ≈39U, 即 \|Δ\|>78U)24h 内必须成 entry |
| KB-57 | P3 | DOC_STALE | reporting, live_trading | `STATE.md:166` | 会话 cron 重建(09-05 14:1xZ; /login 切换清空)**: 每锚深查 47686c87 · jpline 2h 538814c5 · combo 84 锚二读 48a8bb77(09-09) |
| KB-58 | P3 | DOC_STALE | reporting | `STATE.md:226` | @2× 2024→26 算术/CAGR |
| KB-62 | P3 | DOC_STALE | live_trading, reporting | `docs/ERROR_LEDGER_2026-08-20.md:266` | ③**修复项(待用户字)**: 生产者栈 launchd 化(RunAtLoad, shadow.lock 防双跑), 消灭"重启即断链"类。 |
| KB-71 | P3 | VERIFIED_CURRENT | reporting | `CLAUDE.md:14` | **N+24:00 读取交易** |
| KB-77 | P3 | DOC_STALE | reporting | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:507` | **G-1(整类设计否决)** |

### KB-09 · P0 · DOC_STALE
- **Source:** `STATE.md:146 (text before lead commit b63a0144)`
- **Resolution:** APPLIED by lead in b63a0144 (STATE §1 now: 「~~`kill $(cat ~/wide_shadow/fea171/combo_live_daemon.pid)`~~ **不是回滚**」; bootout / disable / enable+bootstrap verbs with drill2 receipt). Re-verify at assembly: new text present.
- **Quote:** 「**回滚**: `kill $(cat ~/wide_shadow/fea171/combo_live_daemon.pid)` ⇒ 下一锚起 king 三腿形态」
- **Superseding evidence:**
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/ERROR_LEDGER_2026-08-20.md:384` — 「4833 是 launchd `com.hsy.shadowloop`(KeepAlive)在 kill 后 ~1s 内重生的新进程」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:10` — 「  RESULT kill: RESPAWNED old=21206 new=21332 => kill is NOT a rollback」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:15` — 「  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback」
- **A reader could wrongly conclude:** Killing the PID stops combo rewrites and the next anchor trades the king form.
- **Affects:** live_trading · **Severity reason:** Emergency rollback path: since 2026-08-30 launchd restarts the combo daemon on any non-zero or signal exit, so this command does not roll the book back while the operator believes it did.
- **Proposed correction (exact text):** **回滚**: combo 守护自 2026-08-30 起由 launchd `com.hsy.combolive` 管理(KeepAlive: 非 0 退出即拉起, 演练受据 30942→30977), 直接 `kill` PID 会被重启, **不构成回滚**。回滚动词 = `launchctl bootout gui/$(id -u)/com.hsy.combolive`(必要时先 `launchctl disable gui/$(id -u)/com.hsy.combolive` 防重登复活), 随后核 `launchctl print gui/$(id -u)/com.hsy.combolive` 已不存在且下一锚 `target_live` producer 为 king 形态; 该动词须在非锚窗演练并留收据后才算有效。全停 = `~/dl_quant_live/ops/KILL.sh`。
- **Confidence:** VERIFIED on a dummy launchd job with the same plist shape (lead drill2 receipt, 2026-09-13T14:47:46Z: kill → respawn within 1 s; bootout → no process, no respawn for 15 s; bootstrap restores); not exercised on the live combolive job · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-01 · P1 · DOC_STALE
- **Source:** `CLAUDE.md:14`
- **Quote:** 「构成 ≈77% funding 动量 + 13% king LGBM + 10% V2MAIN 书损失 DL」
- **Superseding evidence:**
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:45` — 「min 0.1878 / p25 0.2110 / **中位 0.2242** / p75 0.3244 / max 0.3592 / 均 0.2572; 53% 的锚落在 0.21±0.02。」
- **A reader could wrongly conclude:** The model legs weigh 23% of the book; model-side changes are worth ≤0.23× at book level (today the king slot is 0.382, so ≈38%).
- **Affects:** reporting, future_eval · **Severity reason:** Composition sets the model-leg leverage used to size or kill model-side research and is quoted to the user as current.
- **Proposed correction (exact text):** 构成随 msharpe 席位逐锚滚动, 不是常数: 08-26 00Z 掩码席位 king 0.232 ⇒ ≈77% fund/13% king/10% V2MAIN; 09-05 播种后 0.300; 2026-09-13 12Z king 0.382 / fund 0.618 ⇒ ≈62% funding 动量 + 21% king LGBM + 17% V2MAIN(读数来源 ~/regime_dash/regime_dash.jsonl(追加式, 按 `anchor_utc` 取 `w3_masked_king`/`w3_masked_fund`; 滚动的 `REGIME_DASH.md` 每锚被整份重写, 不可作收据 —— DEV-14)「席位(掩码后)」行; 引用须带锚时刻) 【DEV-14 补注 2026-09-16】逐锚可复核值: 2026-09-13T12:00Z king 0.3821 / fund 0.6179 · 2026-09-16T00:00Z king 0.3780 / fund 0.6220; 日志覆盖 2026-09-02T08:00Z 起。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-05 · P1 · DOC_STALE
- **Source:** `CLAUDE.md:28`
- **Resolution:** XREF AUDIT_DATA RET-02 / EVL-01 — CROSS-REF: the accounting-caliber binding and the ban on recomputing returns from the clipped ret5 cache are owned by AUDIT_DATA RET-02; the 33 files defaulting CAL=simple are AUDIT_DATA EVL-01.
- **Quote:** 「记账口径 = `pod_dlw_targets_ext.py` L93 的 y4s = Π(1+r)−1」
- **Superseding evidence:**
  - `docs/REVIEW_caliber_final_2026-09-04.md:168` — 「故 **Π(1+r)−1 (N,N+4h] 是记账口径, Σ-simple 是有偏但小偏的代理**」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
  - `multi_asset/exports/research/retrain_2026-09/pod_dlw_targets_ext.py:93` — 「    y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t]).astype(np.float32)」
- **A reader could wrongly conclude:** Recomputing y4s from the 5m cache (pod_dlw_targets_ext.py L93) gives the accounting caliber.
- **Affects:** future_eval, future_retrain · **Severity reason:** This is the caliber rule every new device copies; the file line it names compounds the ±0.30-clipped 5m cache (E-0908-B), which the v4 pin replaced with RAW accounting.
- **Proposed correction (exact text):** 记账口径 = RAW Π(1+r)−1(v4 记账元 `meta_newprod_v4.npz` / `pod_dlw_targets_raw.py`, 见 `uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`); `pod_dlw_targets_ext.py` L93 是对 ±0.30 裁剪缓存的复利(E-0908-B), 只作对照; 禁止从 5m 缓存 ret5 重算收益; 回撤按固定 2× 逐锚复利 NAV 报
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-06 · P1 · DOC_STALE
- **Source:** `CLAUDE.md:42`
- **Quote:** 「| 在役书证据/杠杆/局限 | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` |」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The 08-26 yearly claim "candidate ≥ in-role in every year" reverses for 2025**」
  - `STATE.md:111` — 「④ combo 选型复测: 排序保住、不显著、增益来自去 rev24、V2MAIN ≈0、2025 反转。」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
- **A reader could wrongly conclude:** Combo is significantly better than the three-leg book in all seeds and years, and 2.0× never touches the −25% line.
- **Affects:** future_eval, live_trading, reporting · **Severity reason:** The routing table sends the leverage and evidence question to a document whose table and leverage map were both overturned on the correct caliber.
- **Proposed correction (exact text):** | 在役书证据/杠杆/局限 | 在役形态水平与逐年/回撤 = `uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md`(含勘误: 固定 2× 复利 NAV maxDD); combo 选型在正确口径下的复测 = `retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md`; `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` 只作定义与历史(其 §2 数字为 CAL=simple 作废口径) |
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-07 · P1 · DOC_STALE
- **Source:** `CLAUDE.md:44`
- **Quote:** 「| 恢复研究某条轴 / DNR | `docs/MILESTONE_2026-08-26.md` §2/§5(08-11 前的查上期) |」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `memory/fund_leg_is_the_book.md:8` — 「机制性结论保留, 数字与席位/腿层判决作废待重立。」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
- **A reader could wrongly conclude:** A DNR in MILESTONE §2/§5 is settled evidence; reopening needs new evidence.
- **Affects:** future_eval · **Severity reason:** DNR verdicts in MILESTONE §2/§5 were decided on the CAL=simple device (08-25 13:35Z onward); relative verdicts reversed at least once on the correct caliber.
- **Proposed correction (exact text):** | 恢复研究某条轴 / DNR | `docs/MILESTONE_2026-08-26.md` §2/§5 —— ⚠ 其中 08-25 13:35Z 之后以 w7/w8/w10 CAL=simple 装置判定的数字与腿/席位层判决全部待正确口径(v4 RAW)重判(E-0904-F); 重开这些轴不需要新证据, 需要同口径重判; 08-11 前的查上期 |
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-10 · P1 · DOC_STALE
- **Source:** `STATE.md:143`
- **Quote:** 「构成 ≈ 77% fund + 13% king(LGBM) + 10% V2MAIN(可微书损失 DL, 171 列)」
- **Superseding evidence:**
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:45` — 「min 0.1878 / p25 0.2110 / **中位 0.2242** / p75 0.3244 / max 0.3592 / 均 0.2572; 53% 的锚落在 0.21±0.02。」
- **A reader could wrongly conclude:** The live book is 77% fund leg.
- **Affects:** reporting, future_eval · **Severity reason:** STATE §1 is the declared single source of truth for the live book.
- **Proposed correction (exact text):** 构成随 msharpe 席位逐锚滚动(09-05 king 席位按装置规则播种): 2026-09-13 12Z 掩码席位 king 0.382 / fund 0.618 ⇒ ≈62% fund + 21% king(LGBM) + 17% V2MAIN(可微书损失 DL, 171 列); 最新值读 `~/regime_dash/regime_dash.jsonl(追加式, 按 `anchor_utc` 取 `w3_masked_king`/`w3_masked_fund`; 滚动的 `REGIME_DASH.md` 每锚被整份重写, 不可作收据 —— DEV-14)`「席位(掩码后)」行。同句「maker-only」改为「maker 优先 + chase 50/50 追单实验(09-01 起)」; 「NAV ≈ 20.4k, 08-27 入金后」改为「gross_mult 2.0 自 08-27 起; NAV 以 `~/guard_twin/state/latest.json` 为准(09-13 ≈117.6k)」 【DEV-14 补注 2026-09-16】逐锚可复核值: 2026-09-13T12:00Z king 0.3821 / fund 0.6179 · 2026-09-16T00:00Z king 0.3780 / fund 0.6220; 日志覆盖 2026-09-02T08:00Z 起。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 141->143)

### KB-16 · P1 · DOC_STALE
- **Source:** `STATE.md:201`
- **Quote:** 「杠杆升级(候选 2.0× 历史不触 −25% 线)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
- **A reader could wrongly conclude:** At 2.0× the in-service form has never breached a −25% drawdown.
- **Affects:** live_trading, reporting · **Severity reason:** Leverage rulings rest on this line; on the v4 caliber with compounded 2× NAV the in-service form drew down −28.92% in 2023 and −42.12% over W_ALPHA.
- **Proposed correction (exact text):** 杠杆: 2.0× 已于 08-27 生效; v4 口径固定 2× 逐锚复利 NAV maxDD: 2023 −28.92%, 2024 −23.62%, W_ALPHA 全窗 −42.12%(r18 表勘误 3), 旧「2.0× 历史不触 −25% 线」为 CAL=simple 作废口径; 尾部为下界(E-0908-B)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 199->201)

### KB-20 · P1 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:12`
- **Quote:** 「回放证据: 三种子 Δnet +0.29~+0.43 bps/锚 全显著(基线夏普 2.18 → 2.7-3.0)。」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The 08-26 yearly claim "candidate ≥ in-role in every year" reverses for 2025**」
  - `STATE.md:111` — 「④ combo 选型复测: 排序保住、不显著、增益来自去 rev24、V2MAIN ≈0、2025 反转。」
- **A reader could wrongly conclude:** The combo form is significantly better than the three-leg book, driven by V2MAIN, lifting Sharpe to 2.7–3.0.
- **Affects:** future_eval, reporting · **Severity reason:** The admission evidence for the in-service form; re-tested on the correct caliber it lost significance at seed 42 and its attribution reversed.
- **Proposed correction (exact text):** 回放证据(CAL=simple, 已作废口径): 三种子 Δnet +0.29~+0.43。⚠ 正确口径复测(`review_caliber_wf/combo_recheck/REPORT.md`, 09-04): 方向保住, s42 显著性不保(D−A 2024→26 +0.108 [−0.101,+0.312] CAL=log / +0.203 [−0.022,+0.439] 复利), 归因反转(V2MAIN 单独 ≈0, 唯一 CI 排零的是「去 rev24」), 2025 反转; 「基线 2.18 → 2.7–3.0」不得引用。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 9->12)

### KB-21 · P1 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:29`
- **Quote:** 「**fund 腿 = 书本体**(去掉 4/4 年由盈转亏 −3.04 CI[−3.86,−2.20]); **king = 组合内方差压制者**(仅king 单腿书 −2.74 亏钱; 去king ΔSharpe CI 全负)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:58` — 「| 全周期 post-warm | 9139 | **0.46171** | — | 0.21 | 2.20× | — |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:55` — 「| 2024 | 2196 | **0.7100** | 0.8108 | 0.21 | **3.38×** | 0.007 |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:79` — 「k=0.00 **0.629/0.629** | k=0.21 0.484/0.485 | k=0.2572 0.420/0.407 | k=0.3568 0.343/0.402 | k=0.4617 0.359/0.414 | k=0.5338 0.358/0.501 | **dyn 1.415/1.437**」
  - `docs/REVIEW_caliber_final_2026-09-04.md:134` — 「腿级偏差(同窗, bps/锚 2024/25/26): king −1.03/−2.44/−3.14; rev24 −0.75/−1.53/−1.98; fund +0.30/+0.74/+0.88」
- **A reader could wrongly conclude:** The fund leg alone is the book; model legs only dampen variance and a king-only book loses money.
- **Affects:** future_eval, reporting · **Severity reason:** Drives where research effort goes (fund-leg structure vs model legs); on v4 the dynamic seat gives king 0.71 in 2024–25 and a fund-only book reaches Sharpe 0.63 vs 1.42 for the seat-timed book.
- **Proposed correction (exact text):** (CAL=simple 口径, E-0904-F 作废, 腿层判决待重立)fund 腿 = 书本体 … king = 方差压制者。⚠ v4 口径席位阶梯(`uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md` §3): 动态 msharpe 席位 king 均权 2024 0.71 / 2025 0.71 / 2026 0.36 / 全周期 0.46; 固定 king 0(纯 fund)全周期 Sharpe 0.63 vs 动态 1.42 ⇒ 书的收益约一半以上来自两腿间的席位择时, 不是 fund 腿本身; expm1 口径曾把 king 腿压低 1–3 bps/锚。「仅 king 单腿书亏钱」未在 v4 复测。
- **Confidence:** VERIFIED for seat ladder and bias; king-only book OPEN_NOT_MEASURED on v4 · **Quote re-verified at assembly:** exact (line moved 23->29)

### KB-23 · P1 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:44`
- **Quote:** 「书=主导率保费(78%)+残差 alpha —— 对冲毁书」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。」
- **A reader could wrongly conclude:** 78% of the in-service book's return is alt−BTC dominance exposure, so hedging it destroys the book.
- **Affects:** future_eval, reporting · **Severity reason:** Used to reject any hedge or neutralisation proposal without testing; the only measurement on the current book gives the opposite sign.
- **Proposed correction (exact text):** 书=主导率保费(78%)+残差 alpha(08-21 在役书 S1 / 引擎 Y4 仪器)。⚠ T8 §6.1: A0 v4 书同期 corr(净额, 等权山寨−BTC 价差) = +0.05 / +0.04, 逐折 β 为正 ⇒「78%」不适用于在役 combo/v4 形态, 两仪器矛盾待对账; 对冲/中性化提案不得以此句否决。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 29->44)

### KB-25 · P1 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:50`
- **Quote:** 「**对数→简单收益总更正**(SR 57038bd): 9821 锚族绝对数全部重表; 可交易口径=简单持有收益。」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:421` — 「expm1 只能作用于对数收益; "简单收益口径"不等于"对 y4 做 expm1"。」
  - `docs/REVIEW_caliber_final_2026-09-04.md:168` — 「故 **Π(1+r)−1 (N,N+4h] 是记账口径, Σ-simple 是有偏但小偏的代理**」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
- **A reader could wrongly conclude:** Applying expm1 (CAL=simple) to panel y4 is the tradable caliber.
- **Affects:** future_eval · **Severity reason:** Read without E-0904-F this line endorses CAL=simple (expm1) on pod panels, the defect that inflated 08-25..09-04 numbers.
- **Proposed correction (exact text):** 对数→简单收益总更正(SR 57038bd)只对 wide_dl 对数面板族成立; ⚠ pod 面板族 y4 已是 Σ简单, 对其做 expm1(w10/w8 `CAL=simple`)是伪凸性(E-0904-F); 记账口径 = RAW Π(1+r)−1(CALIBER_PIN_v4)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 32->50)

### KB-26 · P1 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:71`
- **Quote:** 「杠杆升级(2.0× 历史不触线, 归用户)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
- **A reader could wrongly conclude:** 2.0× is historically safe against the −25% line.
- **Affects:** live_trading, reporting · **Severity reason:** Same leverage claim as KB-16, in the routed ledger.
- **Proposed correction (exact text):** 杠杆升级(已于 08-27 升至 2.0×)。⚠ v4 口径固定 2× 复利 NAV maxDD 2023 −28.92% / W_ALPHA −42.12%(r18 勘误 3), 「2.0× 历史不触线」为 CAL=simple 作废口径。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 47->71)

### KB-29 · P1 · DOC_STALE
- **Source:** `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:3`
- **Quote:** 「**状态:** 回放证据完备, 前向影子已起跑, **未部署**(书行为改动归用户)」
- **Superseding evidence:**
  - `STATE.md:154` — 「**★ combo 84 锚前向门二读(09-09 05:0xZ, `pilot_journal/journal_2026-09-09_forward_gate_84.md`): 判据① 不过(候选净累计 −192.3 bps gross=1 ≈ −3.85% NAV@2×), 判据② 过=未否决」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:129` — 「three days later the in-service form's admission document states only 「DSR 折价适用 ⇒ 前向影子为终审」 (CANDIDATE L61) without a DSR number.」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
- **A reader could wrongly conclude:** The candidate has complete replay evidence, is not yet live, and the forward shadow has not ruled.
- **Affects:** future_eval, reporting · **Severity reason:** The header says evidence complete and undeployed; the form has been live since 08-26, its replay evidence was re-tested and weakened, and the forward judge it names failed criterion ①.
- **Proposed correction (exact text):** **状态:** 已于 2026-08-26 04:00Z 上线(在役); §2 回放证据为 CAL=simple 作废口径, 正确口径复测见 combo_recheck(显著性不保、归因反转、2025 反转); §6 前向门 84 锚二读(09-09)判据① 不过、② 未否决, 下一读数窗归用户; 未做入选 DSR(T6 §9)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-31 · P1 · DOC_STALE
- **Source:** `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:28`
- **Quote:** 「**+0.374 [+0.15,+0.60] ★**」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The 08-26 yearly claim "candidate ≥ in-role in every year" reverses for 2025**」
  - `STATE.md:111` — 「④ combo 选型复测: 排序保住、不显著、增益来自去 rev24、V2MAIN ≈0、2025 反转。」
- **A reader could wrongly conclude:** Three seeds significant, V2MAIN carries the gain, candidate better every year.
- **Affects:** future_eval, reporting · **Severity reason:** Main evidence table; every row is CAL=simple and the re-test changed significance, attribution and the 2025 sign.
- **Proposed correction (exact text):** 在 §2 表头下插入: ⚠ 本表全部为 CAL=simple(对 Σ简单 y4 做 expm1 的伪凸性口径, E-0904-F), 数字作废。正确口径复测(combo_recheck/REPORT.md): D−A 2024→26 s42 +0.108 [−0.101,+0.312](CAL=log)/ +0.203 [−0.022,+0.439](复利), 仅 s2027 复利口径 CI 排零; V2MAIN 单独 ≈0; 唯一 CI 排零的是「在混 V2MAIN 前提下去 rev24」; 2025 候选劣于在役; 席位在正确口径下 king 0.52–0.54。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 22->28)

### KB-32 · P1 · DOC_STALE
- **Source:** `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:56`
- **Quote:** 「**2.0× 在候选下历史不触 −25% 线**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
- **A reader could wrongly conclude:** 2.0× never breaches −25%.
- **Affects:** live_trading, reporting · **Severity reason:** The leverage table is the live 2.0× justification; v4 compounded NAV shows −28.92% (2023) and −42.12% (W_ALPHA).
- **Proposed correction (exact text):** 在杠杆表下插入: ⚠ 本表为 CAL=simple 作废口径且回撤为算术×杠杆; v4 口径固定 2× 逐锚复利 NAV maxDD: 2023 −28.92%, 2024 −23.62%, W_ALPHA 全窗 −42.12%(r18 表勘误 3); 尾部为下界(E-0908-B)。「2.0× 在候选下历史不触 −25% 线」撤回。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 47->56)

### KB-34 · P1 · DOC_STALE
- **Source:** `docs/CHECKLIST_combo_switch_2026-08-26.md:22`
- **Quote:** 「③ 整体回滚 = kill 守护 PID(下一锚起自动 king 形态), 不动任何其他组件」
- **Superseding evidence:**
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/ERROR_LEDGER_2026-08-20.md:384` — 「4833 是 launchd `com.hsy.shadowloop`(KeepAlive)在 kill 后 ~1s 内重生的新进程」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:10` — 「  RESULT kill: RESPAWNED old=21206 new=21332 => kill is NOT a rollback」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:15` — 「  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback」
- **A reader could wrongly conclude:** Killing the daemon PID reverts to the king form.
- **Affects:** live_trading · **Severity reason:** Routed from CLAUDE.md for components and rollback; same silent-failure verb as KB-09 (P0 lives in STATE §1 and the deep-check template).
- **Proposed correction (exact text):** ③ 整体回滚 = `launchctl bootout gui/$(id -u)/com.hsy.combolive`(临时; 持久再加 `launchctl disable …`; 恢复 = `launchctl enable …` + `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`)。08-30 起 launchd KeepAlive, kill PID 会被 1 s 内拉起, 不再是回滚(哑任务演练收据 OPS_rollback_verb_drill2_20260913T144746Z.log; 见 STATE §1)。不动任何其他组件
- **Confidence:** VERIFIED on a dummy launchd job with the same plist shape (lead drill2 receipt, 2026-09-13T14:47:46Z: kill → respawn within 1 s; bootout → no process, no respawn for 15 s; bootstrap restores); not exercised on the live combolive job · **Quote re-verified at assembly:** exact

### KB-37 · P1 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:6`
- **Resolution:** XREF FIXPROGRAM K2 relabel — CROSS-REF: the '部署差不是主因' verdict is relabelled by FX-EVAL K2 (RELABEL_TABLE_K2.md); this register adopts K2's vocabulary rather than proposing its own.
- **Quote:** 「**部署差不是主因**(T4/T4b/T5/T5c)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md:35` — 「- **不能排除**: 价格上 −4.15 到 +1.71 之间的任何部署或模型差, 包括 −1、−2 bps/锚 这样的差。它们是 A0 全周期净额 +0.63 的 1.6 到 3.2 倍。±0.25 的经济等价在价格、carry、净额上都**没有**成立。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:112` — 「**未识别：** 模型/部署差已非主因、正确生产 combo 历史会同样亏、策略根因已排他定位。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「T4 在该历史尺子下未检出差异、所报区间较窄；其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带」
- **A reader could wrongly conclude:** Deployment and model differences are ruled out as causes of the live shortfall, so only new sources or structure changes matter.
- **Affects:** future_eval · **Severity reason:** Premise #1 of the third programme steers effort away from deployment/model fixes; T5d cannot exclude deployment or model gaps of 1.6–3.2× the book's full-cycle net.
- **Proposed correction (exact text):** **部署差未检出也未排除**(T4 NOT MATERIAL 仅显著性门、无等价带; T5 八月 carry 差 = 构造差; T5d 九月价格部署/模型差 −4.15..+1.71 bps/锚不可排除, 为 A0 全周期净额 1.6–3.2 倍; V2MAIN 与执行器层未测)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-45 · P1 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:121`
- **Quote:** 「What must be lowered is any planning or target number built on a best-candidate backtest: subtract at least 0.65 SR (full cycle) / 1.56 SR (frozen window).」
- **Superseding evidence:**
  - `STATE.md:6` — 「③ **T6 读法过强**: 参与比 N_eff 是谱维数、不是已校准的极值有效试验数; −0.65/−1.56 不是今后任意候选的最低折价下界; 0.30/0.0047 是不同 N 假设下的代入读数、不是真 Sharpe>3 的概率」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:129` — 「**−0.65/−1.56 不是未来任意候选必须至少扣除的数学下界。**」
- **A reader could wrongly conclude:** Every future best-candidate backtest must be cut by at least 0.65/1.56 Sharpe, and A0's frozen 2.94 has a 0.30/0.005 probability of exceeding 3.
- **Affects:** future_eval, reporting · **Severity reason:** T6 §8 is quoted as a calibrated haircut and probability; the lead withdrew both readings (STATE 12:1xZ ③) but the RESULT is unchanged.
- **Proposed correction (exact text):** 在 §8 前插入: ⚠ 复审第四轮(REVIEW_round4 §4.2)与 STATE 2026-09-13 12:1xZ ③ 撤回三处读法: (1) N_eff 参与比是谱维数, 不是已校准的有效试验数; (2) −0.65/−1.56 是本家族在已实现选择路径上的描述, 不是今后任意候选的最低折价下界; (3) 0.30/0.0047 是不同 N 假设下的代入读数, 不是真 Sharpe>3 的概率。仍成立: 候选家族高度相关、冻结窗高水平为全家族共有、A0 冻结窗 CI95 [1.306, 4.565] 不显著高于 3。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 118->121)

### KB-46 · P1 · PENDING_USER_DECISION
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:156`
- **Quote:** 「at least −0.65 SR full cycle and −1.56 SR frozen window from T6, both lower bounds.」
- **Superseding evidence:**
  - `STATE.md:6` — 「③ **T6 读法过强**: 参与比 N_eff 是谱维数、不是已校准的极值有效试验数; −0.65/−1.56 不是今后任意候选的最低折价下界; 0.30/0.0047 是不同 N 假设下的代入读数、不是真 Sharpe>3 的概率」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:129` — 「**−0.65/−1.56 不是未来任意候选必须至少扣除的数学下界。**」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:130` — 「**§11 的统计量与人口混了。**」
- **A reader could wrongly conclude:** Admission will require quoting a ≥0.65/1.56 haircut; the increment gate statistic is settled.
- **Affects:** future_eval · **Severity reason:** The §11 admission protocol is awaiting a user ruling and the third programme already evaluates candidates by it; rule 7 bakes in the withdrawn haircut.
- **Proposed correction (exact text):** 7. **Quoting rule.** 任何最佳候选回测夏普须同时引用其嵌套前推对应值与本家族实测差(W_FULL −0.652 [−1.735,+0.392] / FROZEN −1.555 [−3.347,+0.200], 描述性, 非普适下界); §11 录取门先冻结统计量(ΔSharpe 或差收益均值)、合法人口、选择时点、主窗、依赖块长与前向验证段后再提交用户裁定
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 150->156)

### KB-50 · P1 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:11`
- **Quote:** 「实盘变差的真因不是执行、不是延迟、不是平滑、不是模型陈旧」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:9` — 「**先说判不了的**: 五条假设里 **四条(H1、H3、H4、H5)按预注册读数「不可判」**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:19` — 「**构造分量(Shapley, 占 Δ 比例, s42 / s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md:35` — 「- **不能排除**: 价格上 −4.15 到 +1.71 之间的任何部署或模型差, 包括 −1、−2 bps/锚 这样的差。它们是 A0 全周期净额 +0.63 的 1.6 到 3.2 倍。±0.25 的经济等价在价格、carry、净额上都**没有**成立。」
- **A reader could wrongly conclude:** Execution, delay, smoothing and model staleness are ruled out; the only cause is the funding bet in this regime.
- **Affects:** future_eval, reporting · **Severity reason:** Decision document (DOCKET r7) asserting a cause the later T1/T5/T5d receipts could not establish; construction differences explain August carry and deployment/model gaps are not excluded for September.
- **Proposed correction (exact text):** 实盘变差的原因未识别: T1 五假设四条不可判(落差本身不显著, 实盘窗状态对全史不反常); 八月部署书 carry 为回放 2.19 倍 = 构造差(FTRIM 缺席 58% / 暖启动态 27% / 回放止损层 18.5%); 九月部署/模型差 −4.15..+1.71 bps/锚不可排除(T5d); 执行/延迟/平滑未单独排除
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-64 · P1 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97`
- **Quote:** 「**A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「Sharpe 1.29 引用必须带窗: **W_ALPHA 2022-06-30 00Z→2026-08-30 20Z, 9,138 锚, 1.29122344 [0.3207, 2.2822]**」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:36` — 「**Two windows, never mixed.** `W_ALPHA` n=**9138** (drop first 900 warm anchors, E-0911-A; ceiling 2026-08-30 20Z, E-0911-D) for every mean/CI/Sharpe/turnover/leg number.」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:32` — 「The same A0 book reads **0.6342 / SR 1.2912** on the fitted plane and **0.688853 / SR 1.4025** on the cheap plane.」
- **A reader could wrongly conclude:** A planning or leverage decision is taken on 1.2912 / +27.8% NAV as if it were the whole history on the costs the book actually pays; both substitutions move the number, in opposite directions, by more than the quantity being planned around.
- **Affects:** reporting, future_eval, live_trading · **Severity reason:** This is §7 '当前规划数' — the single line the whole programme points at for planning — and it names neither the window (W_ALPHA n=9138) nor the cost plane (fitted costb_PWR_G230k); on the deployed fee-only plane the same book reads 1.4025, and on the full anchor axis 1.1062.
- **Proposed correction (exact text):** [在该行后插入] > ⚠ **2026-09-16 更正(独立复审 FXR-DOC-3 + CANONICAL_NUMBERS §0-5/§0-3)**: 本规划数的**窗与成本面必须同时写出** —— **W_ALPHA(2022-06-30 00Z → 2026-08-30 20Z, 9,138 锚)· 拟合成本面 `costb_PWR_G230k.json`(sha 295b4e7b…)**, 夏普 **1.29122344** CI95 **[0.3207, 2.2822]**(探索性 2,000 次 UTC 日块自举, 保留日内不保留跨日, **非选择校正区间**)。同一本书在**在役纯费成本面**上读 **0.688853 / SR 1.4025**; 在**全锚轴 W_FULL(10,038 锚)**上读 **SR 1.1062**; 另有 9,139 锚 / 1.2947 版本。**四者不可混用**, 引用时窗与成本面缺一即作废。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 91->97)

### KB-69 · P1 · DOC_STALE
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:258`
- **Resolution:** APPLIED by lead 2026-09-16 05:0xZ, commit **5642fbc2** (FIXPROGRAM §17.5 「编号冲突更正(AUD-KB 发现, lead 自身错误)」). The lead re-verified independently rather than taking the row as read, and the scope was WIDER than this row found: **seven** collisions, not five. The two this row missed were in §14.2, which I had not scanned: PROD-35 (AUDIT_PROD: V2MAIN trained with fund columns zeroed for non-live450 names on the pre-holefix cache) → **PROD-46**, and PROD-36b (AUDIT_PROD: replay caches shorter than ~37 days put btcv back-fill into the 180-anchor z window) → **PROD-47**; the lead notes the `b` suffix was meant to signal 「related to PROD-36」 but reads as a sub-item of a different finding. All seven renumbered in place to PROD-41..47 with 「原登记为 PROD-3x, 与 AUDIT_PROD 撞号, 原号标 SUPERSEDED-ID」, original bytes retained, and a standing rule added: new ids must be checked against all four audit registers first. ⚠ The same ruler, applied to the rest of §13–§17, finds one more collision — TRN-28, see **KB-74** — and two that predate the programme — LED-01 / DOC-01 between AUDIT_EXEC and AUDIT_DATA, see **KB-75**.
- **Quote:** 「| **PROD-30** | G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定**」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_PROD.md:1` — 「**创建:** 2026-09-13」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:260` — 「AUDIT_PROD PROD-28(「运行中进程执行盘上代码/bundle/F10 模型」)是对 PID 10900 / 30944 / 30943 验的」
  - `STATE.md:144` — 「登记为 PROD-30, 待用户裁定, 属书行为」
- **A reader could wrongly conclude:** A reviewer or a later session resolves 'PROD-30' against AUDIT_PROD and gets the exec_n6 sandbox producer instead of the G1/G2 N+23 mis-calibration; 'PROD-33' resolves to the CLAUDE.md N+23 doc item instead of the single-slot combo_live_status.json defect. A book-behaviour ruling could be taken against the wrong evidence, and every cross-reference between the review package and the audit registers becomes ambiguous.
- **Affects:** reporting, future_eval, live_trading · **Severity reason:** FIXPROGRAM §13.1 opens five new registrations under ids that AUDIT_PROD (ee2a8c4d) already owns — PROD-30/31/32/33/34 — while the same table cross-references 'AUDIT_PROD PROD-28' by number, so the two registers are demonstrably in one namespace; STATE.md:144, the truth source, already cites the colliding PROD-30, and PROD-30 is one of the items routed to the user for a book-behaviour ruling.
- **Proposed correction (exact text):** [§13.1 表内原编号字节保留, 在 §13.1 表下插入] ⚠ **2026-09-16 编号更正(aud-kb KB-69)**: 本表的 **PROD-30 / 31 / 32 / 33 / 34 与 `AUDIT_PROD`(ee2a8c4d)已占用的同号项冲突**, 而本表自身又按号引用「AUDIT_PROD PROD-28」⇒ 两表同命名空间。**AUDIT_PROD 已用到 PROD-40, 空号自 PROD-41 起**。按下表重编, 原号保留并标 SUPERSEDED-ID: **PROD-30 → PROD-41**(G1/G2 仍按已退役 N+23 标定)· **PROD-31 → PROD-42**(08-29 20Z 生产者未出 king 文件)· **PROD-32 → PROD-43**(守护告警路径在生产中从未执行)· **PROD-33 → PROD-44**(`combo_live_status.json` 单槽可变)· **PROD-34 → PROD-45**(排练模式用 `WS` 备份写进实盘状态树)。冲突对象逐条: AUDIT_PROD PROD-30 = exec_n6 沙箱生产者 · PROD-31 = `fea171/f10_live_s42.pt` 是八月模型 · PROD-32 = `stop_overlay.py` 只是报告影子 · PROD-33 = CLAUDE.md 写 N+23 而执行器读 N+24 · PROD-34 = 在役 booster 8d79186b 训练于未 clamp 构建器。**同时更正 `STATE.md:144` 的「登记为 PROD-30」为「登记为 PROD-41」**(见 KB-70)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-70 · P1 · DOC_STALE
- **Source:** `STATE.md:144`
- **Resolution:** APPLIED by lead 2026-09-16, commit **5642fbc2**: STATE.md:144 now reads 「登记为 **PROD-41**(原写 PROD-30, 与 AUDIT_PROD 的 exec_n6 沙箱生产者项撞号, 09-16 改号), 待用户裁定, 属书行为」 — original id and the reason kept in the parenthetical.
- **Quote:** 「登记为 PROD-30, 待用户裁定, 属书行为」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:259` — 「G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定**」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:260` — 「AUDIT_PROD PROD-28(「运行中进程执行盘上代码/bundle/F10 模型」)是对 PID 10900 / 30944 / 30943 验的」
- **A reader could wrongly conclude:** The user or a later session looks up PROD-30 to decide the G1/G2 question and reads the exec_n6 sandbox item instead.
- **Affects:** live_trading, reporting · **Severity reason:** STATE is the single source of truth and this line routes a pending book-behaviour ruling to an id that resolves, in the audit register the same package cites, to an unrelated item (the exec_n6 sandbox producer).
- **Proposed correction (exact text):** [替换该句, 原句字节在 FIXPROGRAM §13.1 与本登记内保留] 登记为 **PROD-41**(原写 PROD-30; 与 `AUDIT_PROD` ee2a8c4d 的 PROD-30 = exec_n6 沙箱生产者 撞号, 2026-09-16 按 aud-kb KB-69 重编), 待用户裁定, 属书行为。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-02 · P2 · DOC_STALE
- **Source:** `CLAUDE.md:13`
- **Resolution:** XREF AUDIT_EXEC CFG-04 — CROSS-REF: chase 50/50 restart is owned by AUDIT_EXEC CFG-04; now also frozen by CFG-04 AMENDMENT 1 (docs/AMENDMENT_1_chase_restart_population_2026-09-16.md, 86c0227b).
- **Quote:** 「maker-only, gross 2.0×NAV(2026-09-03 入金后 constant_leverage_2.00; 此前 1.5×)」
- **Superseding evidence:**
  - `~/dl_quant_live/live/chase_policy.py:144` — 「ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.5, ARM_NO_CHASE: 0.5}」
  - `STATE.md:125` — 「ARM_WEIGHTS 0/1→**0.5/0.5** + salt v2 全量重随机」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:305` — 「Maker share by notional stayed above 0.90 through 09-02 and has run 0.56-0.89 per anchor since 09-08.」
  - `~/dl_quant_live git log e3e8685 (2026-08-27 13:06 +0800)` — 「ramp step3(收官重试): gross_mult 1.75→2.0 … 08:00Z生效」
- **A reader could wrongly conclude:** All fills are maker at 2.00 bps; taker share and chase cost can be ignored in replays and cost bridges; 2.0× began 09-03.
- **Affects:** reporting, future_eval · **Severity reason:** Cost and fill assumptions in new devices follow the identity line; the book has not been maker-only since the 09-01 chase restart.
- **Proposed correction (exact text):** maker 优先 + 追单实验(chase 50/50, 09-01 起; 逐名止损残差经 chase 臂 MARKET reduce-only), 09-08 起逐锚 maker 成交占比 0.56–0.89; gross 2.0×NAV(gross_mult 2.0 自 2026-08-27 08:00Z 生效, 此前 1.5→1.75 爬坡)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-04 · P2 · DOC_STALE
- **Source:** `CLAUDE.md:15`
- **Quote:** 「宽面板/判官在 jpline `/mnt/storage/private/work_hsy/`」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `STATE.md:182` — 「**jpline 重连定时已按用户字停止(09-06 05:4xZ)。**」
- **A reader could wrongly conclude:** Canonical panels and judges live on jpline.
- **Affects:** future_eval, future_retrain · **Severity reason:** Every judge in current use (v4 chain, T/L series, P2) runs on pod2; a new session following this line looks for panels on a host that has been unreachable since 09-04.
- **Proposed correction (exact text):** 宽面板/判官: 现役在 pod2 `/workspace/`(v4 链 `review_scratch/`、uplift 各线 `uplift_*`); jpline `/mnt/storage/private/work_hsy/` 自 2026-09-04 起不可达, 仅历史装置
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-08 · P2 · DOC_STALE
- **Source:** `CLAUDE.md:47` · xref TRN-28
- **Resolution:** XREF AUDIT_TRAIN TRN-28 — CROSS-REF: CLAUDE.md routing 月度重训 to the superseded September runbook is owned by AUDIT_TRAIN TRN-28; application is K4's (FIXPROGRAM §3.2).
- **Quote:** 「| 月度重训 | `docs/RUNBOOK_monthly_retrain_2026-09.md` |」
- **Superseding evidence:**
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:3` — 「**状态:** 待执行(10-01 前后), **执行只按 §0★**」
  - `docs/RUNBOOK_monthly_retrain_2026-09.md:3` — 「**状态:** 待执行(pod 资源到位后)」
- **A reader could wrongly conclude:** The September runbook is the executable procedure for the next retrain.
- **Affects:** future_retrain, reporting · **Severity reason:** October retrain is due around 10-01 and the routed runbook is the pre-v4 September one still marked 待执行.
- **Proposed correction (exact text):** | 月度重训 | `docs/RUNBOOK_monthly_retrain_2026-10.md` §0★(唯一执行步骤单, v4 口径); `RUNBOOK_monthly_retrain_2026-09.md` 已被取代, 仅作历史 |
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-13 · P2 · DOC_STALE
- **Source:** `STATE.md:129` · xref OPS-01
- **Resolution:** XREF AUDIT_EXEC OPS-01 — CROSS-REF: the σ_fund gross ladder re-arming is owned by AUDIT_EXEC OPS-01; the lead disabled and retired the plist 2026-09-13 14:00:50Z (6cc95943). ⚠ **口径(KB-73)**: 本行引用的「逐套件 N/M」只在同一解释器下可比 —— 电池 `run_acceptance.sh:28` 的 `PY="${ACCEPT_PY:-/usr/bin/python3}"` 是**可被环境变量覆盖的默认值**, 认证它的断言只对源码做子串检查, 且 `state/acceptance/` 38,177 份工件中 0 份记录解释器版本; 2026-07-27 前两入口一钉一裸, 裸 `python3` 制造过两个假红。引用计数时须写明解释器。
- **Quote:** 「σ_fund gross 阶梯已上线(执行器 4b8ca20 电池 124/124; 仪表盘作业 com.hsy.sigma_ladder N+52)」
- **Superseding evidence:**
  - `docs/PREREG_deploy_sigma_ladder_2026-09-04.md:29` — 「launchd `com.hsy.sigma_ladder` 卸载; 状态文件移为 `sigma_ladder.json.reserve_20260904`」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:56` — 「**lead 已应用 14:00:50Z**: `launchctl disable gui/501/com.hsy.sigma_ladder`(print-disabled 显示 disabled)+ plist 移至 `~/Library/LaunchAgents_retired/`」
  - `launchctl print-disabled gui/501 (2026-09-13 14:0xZ)` — 「"com.hsy.sigma_ladder" => disabled」
- **A reader could wrongly conclude:** A σ_fund gross ladder is active and can halve gross after 84 low-dispersion anchors.
- **Affects:** live_trading, reporting · **Severity reason:** A withdrawn gross modulator presented as live; the reader side still exists in the executor (OPS-01b), so a stale banner invites re-enabling it.
- **Proposed correction (exact text):** ~~★ 09-04 09:34Z σ_fund gross 阶梯已上线~~ **已撤回**: 09-04 当日卸载(PREREG_deploy_sigma_ladder §处置, 状态文件移为 `.reserve_20260904`, 执行器读端缺失 ⇒ g=1.0); 其录取受据为 CAL=simple 作废口径(REVIEW_caliber_final #20); 2026-09-13 14:00:50Z `launchctl disable` + plist 移至 `~/Library/LaunchAgents_retired/`(FIXPROGRAM OPS-01)。执行器读端仍在(OPS-01b 待修)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 127->129)

### KB-14 · P2 · DOC_STALE
- **Source:** `STATE.md:128` · xref K2-F21, RELABEL_TABLE_K2 v4 decision document
- **Resolution:** XREF FIXPROGRAM K2 relabel — CROSS-REF: 「(C) 不可区分」 → (C) INCONCLUSIVE per K2; K2's six-document list does not include STATE.md, which this row adds.
- **Quote:** 「未换装前线上 = v3 旧链(书层已证不可区分)」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:5` — 「(A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior').」
  - `STATE.md:256` — 「「点估计 ≥ −δ 且 CI 含 0」是**冻结决策规则**, **不是非劣性证明**」
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:46` — 「| PROSE-EQUIVALENCE |」
- **A reader could wrongly conclude:** The v4 chain has been shown equivalent to the live v3 chain at book level, so swapping is risk-free.
- **Affects:** future_eval, future_retrain · **Severity reason:** The v4 swap decision is framed as 'proven indistinguishable' although the judge only issued (C) UNDECIDED.
- **Proposed correction (exact text):** 未换装前线上 = v3 旧链(v4 对 v3 书层判决 (C) UNDECIDED; FX-EVAL K2 重标 = **(C) INCONCLUSIVE**(δ D1 = 0.05, 两席位 CI 越出带), 不是「已证不可区分」)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 126->128)

### KB-15 · P2 · DOC_STALE
- **Source:** `STATE.md:23` · xref CFG-03
- **Resolution:** XREF AUDIT_EXEC CFG-03 — CROSS-REF, not a duplicate: the fact (live maker window is 900 s, 180 s never ran) is owned by AUDIT_EXEC CFG-03; FIXPROGRAM §3.1 routes the STATE/CLAUDE.md-side correction to K4 = this register.
- **Quote:** 「k 窗 180s 已据此上线」
- **Superseding evidence:**
  - `~/dl_quant_live/config/book.json:43` — 「"k_seconds": 900,」
  - `~/dl_quant_live/config/book.json:121` — 「"_k_seconds_rollback_2026_08_10": "★★ 回滚 180→900, 2026-08-10 02:5xZ, 在任何锚点于 180 下运行【之前】。」
  - `~/dl_quant_live git log 7c7d4ae` — 「revert(exec): k 180→900 回滚 — 授权依据被实测推翻, 零锚运行于 180 之下」
- **A reader could wrongly conclude:** The live maker window is 180 s, chosen because unfilled orders run away.
- **Affects:** reporting, future_eval · **Severity reason:** The T3 reading and the adverse-selection family are interpreted against a window length that never ran.
- **Proposed correction (exact text):** k 窗曾于 08-10 授权 180s 但同日在任何锚运行前回滚, 在役 k_seconds = 900
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 21->23)

### KB-17 · P2 · DOC_STALE
- **Source:** `STATE.md:250`
- **Resolution:** XREF AUDIT_DATA EVL-01 — CROSS-REF: 'CAL=simple branch is void' vs the devices that still default to it — owned by AUDIT_DATA EVL-01.
- **Quote:** 「回放装置 CAL=simple 分支作废, 一律 CAL=log 或复利目标」
- **Superseding evidence:**
  - `docs/REVIEW_caliber_final_2026-09-04.md:168` — 「故 **Π(1+r)−1 (N,N+4h] 是记账口径, Σ-simple 是有偏但小偏的代理**」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
  - `multi_asset/exports/research/retrain_2026-09/pod_dlw_targets_ext.py:93` — 「    y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t]).astype(np.float32)」
- **A reader could wrongly conclude:** CAL=log is an acceptable accounting caliber for new replays.
- **Affects:** future_eval · **Severity reason:** CAL=log (Σ-simple) is a biased proxy (fund leg +0.10–0.27 bps/anchor); the v4 pin requires RAW accounting.
- **Proposed correction (exact text):** 回放装置 CAL=simple 分支作废; 记账一律 RAW Π(1+r)−1(v4 记账元 `meta_newprod_v4.npz`); CAL=log(Σ-simple)只作有偏代理对照(fund 腿偏 +0.10~+0.27 bps/锚, REVIEW_caliber_final §C2), 不得作判决口径
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 248->250)

### KB-19 · P2 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:8 (+1 more)`
- **Quote:** 「构成 ≈ 77% funding 动量 + 13% king LGBM + 10% V2MAIN, gross 1.5×NAV, maker-only, 4h 锚。」
- **Superseding evidence:**
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:45` — 「min 0.1878 / p25 0.2110 / **中位 0.2242** / p75 0.3244 / max 0.3592 / 均 0.2572; 53% 的锚落在 0.21±0.02。」
- **A reader could wrongly conclude:** Live book is 77/13/10 at 1.5×, maker-only.
- **Affects:** reporting · **Severity reason:** Routed ledger; the doc is declared non-rolling, but the §0 sentence reads as the live book.
- **Proposed correction (exact text):** (08-26 换装时读数)构成 ≈ 77% funding 动量 + 13% king LGBM + 10% V2MAIN, gross 1.5×NAV, maker-only, 4h 锚。⚠ 现状以 STATE.md 为准: 2026-09-13 12Z 席位 ≈62/21/17, gross 2.0×(08-27 起), maker 优先 + chase 50/50(09-01 起)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-22 · P2 · OPEN_NOT_MEASURED
- **Source:** `docs/MILESTONE_2026-08-26.md:34`
- **Quote:** 「2×2 终版: 目标效应 +0.488 / 弹药效应 +0.267 / 交互 +0.451; **换目标单独≈0, 换弹药单独判负, 合并才 +0.305**。」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `memory/fund_leg_is_the_book.md:8` — 「机制性结论保留, 数字与席位/腿层判决作废待重立。」
- **A reader could wrongly conclude:** Changing the objective alone is worthless and only the combined change helps.
- **Affects:** future_eval · **Severity reason:** Objective/ammunition interaction is the basis for the V2MAIN research line; it was measured only on CAL=simple and never re-run on v4.
- **Proposed correction (exact text):** 2×2 终版(CAL=simple 口径, 未在 v4 复测): 目标效应 +0.488 / 弹药效应 +0.267 / 交互 +0.451。⚠ 同期 combo 选型在正确口径下归因反转(combo_recheck), 本 2×2 读数不得作为录取或 DNR 依据, 需 v4 同装置重判。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 25->34)

### KB-24 · P2 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:40`
- **Quote:** 「书自带隐式止损(在役止损≈免费保险)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「**已停的多头仓位不会被平到 0**」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「2023 **−28.92%**(近似 −33.54, 误差 4.61pp)」
- **A reader could wrongly conclude:** Live stops are free insurance that already work as in the replay.
- **Affects:** live_trading, reporting · **Severity reason:** The live per-name stop did not flatten stopped longs until W9 (deployed 2026-09-13); the 'free insurance' reading is from the replay stop layer, not the live executor.
- **Proposed correction (exact text):** 书自带隐式止损(回放止损层读数)。⚠ 实盘执行器逐名止损在 2026-09-13 W9(ef60f85)前对多头不平仓(T5b §5.3: 125 例中 94 例钉住); W9 后 flatten_only 走 chase 框架(政策待用户裁定, FIXPROGRAM E4); 「≈免费保险」未在实盘层复核。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 28->40)

### KB-27 · P2 · DOC_STALE
- **Source:** `docs/MILESTONE_2026-08-26.md:86`
- **Quote:** 「~~⑦ funding极端空头处理~~ **已判 DNR**」
- **Superseding evidence:**
  - `STATE.md:143` — 「**+ FTRIM 负费率空头 z 层排除(rn8 ≤ −10bp/8h ∧ z<0 ⇒ z=0, kc/fc 同点; 2026-09-02 12:00Z 锚起, PREREG_deploy_ftrim §7-9, 用户字)**」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
- **A reader could wrongly conclude:** Funding-extreme short handling is closed and not in the live book.
- **Affects:** reporting, future_eval · **Severity reason:** The axis is recorded as DNR although the FTRIM exclusion has been live since 09-02 and its deployment basis was then voided on the unbiased caliber.
- **Proposed correction (exact text):** ⑦ funding 极端空头处理: 08-30 判 DNR 后, FTRIM(rn8 ≤ −10bp ∧ z<0 ⇒ z=0)经用户字于 2026-09-02 12Z 上线; 无偏口径下 FTRIM 单独效应中性偏负、部署依据作废(RESULT_caliber_revalidation); T5b: FTRIM 置零不强平, 残余在带内冻结(FIXPROGRAM P7)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 59->86)

### KB-28 · P2 · OPEN_NOT_MEASURED
- **Source:** `docs/MILESTONE_2026-08-26.md:66`
- **Quote:** 「**已判负 DNR**(2026-08-26 04:0xZ, 双种子同座替换门 FAIL」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `memory/fund_leg_is_the_book.md:8` — 「机制性结论保留, 数字与席位/腿层判决作废待重立。」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
- **A reader could wrongly conclude:** LOB price-band columns and tree scores are closed axes.
- **Affects:** future_eval · **Severity reason:** Model-side DNRs (V2L38, V2TREE, LGBM-171, F10 ladders) were judged on the CAL=simple device, where model legs were biased 1–3 bps/anchor low.
- **Proposed correction (exact text):** 已判负 DNR(CAL=simple 装置判定; E-0904-F 后未重判): 重开条件改为「v4 RAW 口径同装置重判」, 不需新证据
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 45->66)

### KB-30 · P2 · DOC_STALE
- **Source:** `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:17`
- **Quote:** 「最终构成 ≈ **77% fund + 13% king + 10% V2MAIN**」
- **Superseding evidence:**
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:45` — 「min 0.1878 / p25 0.2110 / **中位 0.2242** / p75 0.3244 / max 0.3592 / 均 0.2572; 53% 的锚落在 0.21±0.02。」
- **A reader could wrongly conclude:** Live book is 77/13/10.
- **Affects:** reporting · **Severity reason:** Same composition claim; this doc is routed for 'in-service evidence'.
- **Proposed correction (exact text):** 08-26 00:00Z 读数构成 ≈ 77% fund + 13% king + 10% V2MAIN(席位逐锚滚动; 2026-09-13 12Z ≈62/21/17)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 14->17)

### KB-33 · P2 · PENDING_USER_DECISION
- **Source:** `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:73`
- **Quote:** 「DSR 折价适用 ⇒ **前向影子为终审**」
- **Superseding evidence:**
  - `STATE.md:154` — 「判据① 不过(候选净累计 −192.3 bps gross=1 ≈ −3.85% NAV@2×)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:129` — 「T6's A0 FROZEN P(true SR > 0) at N_raw is 0.891, above that 0.75 line; P(true SR > 3.0) is not.」
- **A reader could wrongly conclude:** The forward shadow has not yet produced a verdict.
- **Affects:** future_eval, live_trading · **Severity reason:** The named final judge has reported (① FAIL, ② not vetoed); the next reading window and what ① FAIL means for the form are user decisions.
- **Proposed correction (exact text):** DSR 折价适用(入选时未算 DSR 数字; T6 事后读数仅描述性)⇒ 前向影子为终审: 84 锚二读(09-09)判据① 不过 / ② 未否决, 按 §6 只记录不改书; 下一读数窗(建议 168 锚)与对① 不过的处置待用户裁定
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 61->73)

### KB-35 · P2 · DOC_STALE
- **Source:** `docs/CHECKLIST_combo_switch_2026-08-26.md:34`
- **Resolution:** ⚠ **口径(KB-73)**: 本行引用的「逐套件 N/M」只在同一解释器下可比 —— 电池 `run_acceptance.sh:28` 的 `PY="${ACCEPT_PY:-/usr/bin/python3}"` 是**可被环境变量覆盖的默认值**, 认证它的断言只对源码做子串检查, 且 `state/acceptance/` 38,177 份工件中 0 份记录解释器版本; 2026-07-27 前两入口一钉一裸, 裸 `python3` 制造过两个假红。引用计数时须写明解释器。
- **Quote:** 「| **combo_live_daemon(PID 72287)** |」
- **Superseding evidence:**
  - `launchctl list (2026-09-13 14:0xZ)` — 「30944 0 com.hsy.combolive · 30943 0 com.hsy.sidecar · 10900 -15 com.hsy.shadowloop」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:34` — 「★ 2026-08-30 起三守护已 launchd 化(E-0829-B 修复, 重启+崩溃双自愈; 上行 nohup 命令仅作应急后备)」
- **A reader could wrongly conclude:** Components run as nohup processes with these PIDs.
- **Affects:** live_trading, reporting · **Severity reason:** Component table (PIDs 18998/72287/11380, 'executor zero changes', battery 122/122) is past its own invalidation condition but still routed.
- **Proposed correction (exact text):** 组件表(08-26 快照)。⚠ 现状: 三守护 08-30 起 launchd 管理(`com.hsy.shadowloop` / `com.hsy.combolive` / `com.hsy.sidecar`), PID 以 `launchctl print` 为准; 执行器自 08-26 后多次改动(当前 ef60f85, 电池 135/135); 本清单已超过自身作废条件(换装稳定一周), 仅作历史
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 31->34)

### KB-39 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:24`
- **Quote:** 「零成本收入流 SR 12–44、ρ≈0, 但冻结换仓规则下净额为负(收入 +1.7 vs 换手成本 4.5 bps/锚), 2023 年 71% 锚无合格名; **滞回换仓未评估**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4b/RESULT_L4b.md:10` — 「**No arm survives POST-HOC-FAMILY-2**」
- **A reader could wrongly conclude:** A delta-neutral carry sleeve is a high-Sharpe independent stream pending only a hysteresis rule.
- **Affects:** future_eval · **Severity reason:** Fact #8 still invites a carry sleeve; L4 then L4b evaluated hysteresis and found no arm survives executable exit marks.
- **Proposed correction (exact text):** delta 中性资金费 carry 袖: 滞回换仓已评估(L4 NOT PASS; L4b 原始 1m 可执行退出价下无臂存活, 2025 全臂为负; 强制退出=下架停牌处的标价决定符号); 「SR 12–44」为溢价指数标价的收入流读数, 不可作可交易性证据
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 18->24)

### KB-40 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:193`
- **Quote:** 「问题在策略本身对普涨挤空 / 暴涨回调行情的响应, 不在部署差」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md:35` — 「- **不能排除**: 价格上 −4.15 到 +1.71 之间的任何部署或模型差, 包括 −1、−2 bps/锚 这样的差。它们是 A0 全周期净额 +0.63 的 1.6 到 3.2 倍。±0.25 的经济等价在价格、carry、净额上都**没有**成立。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:112` — 「**未识别：** 模型/部署差已非主因、正确生产 combo 历史会同样亏、策略根因已排他定位。」
- **A reader could wrongly conclude:** T8 was justified because deployment differences were excluded.
- **Affects:** future_eval · **Severity reason:** AMENDMENT 6 rationale is not amended by the closing correction section, which only addresses T5c generically.
- **Proposed correction (exact text):** 问题至少部分在策略本身对普涨挤空 / 暴涨回调行情的响应(T5c/T5d: 回放同亏); 部署/模型差未排除(T5d −4.15..+1.71 bps/锚)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 175->193)

### KB-41 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:172 (+1 more)` · xref K2-F01, RELABEL_TABLE_K2 T4
- **Resolution:** XREF FIXPROGRAM K2 relabel — CROSS-REF: 'NOT MATERIAL under the frozen rule' → INCONCLUSIVE per K2.
- **Quote:** 「冻结规则下 NOT MATERIAL」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带，不能推广为两代部署 booster 全部窗口都无材料性影响」
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:26` — 「| F01 | T4 |」
- **A reader could wrongly conclude:** The king column-80 train/serve skew is shown immaterial.
- **Affects:** future_eval · **Severity reason:** The label steers the P1/P2 feature-skew fix priority; CI upper +0.0625 is ≈10% of A0 W_ALPHA net and above the K2 δ 0.05.
- **Proposed correction (exact text):** 冻结规则下 NOT MATERIAL(仅显著性门)⇒ FX-EVAL K2 重标 **INCONCLUSIVE**: 书层 Δg CI 上界 +0.0625 / +0.0645 越出 δ=0.05, 未排除经济意义差异; IC 轴 EQUIVALENT(ΔIC CI ⊂ ±0.003)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 157->172)

### KB-44 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:92` · xref CFG-03
- **Resolution:** XREF AUDIT_EXEC CFG-03 — CROSS-REF: same fact as KB-15, different file. Owner AUDIT_EXEC CFG-03; text application is K4's.
- **Quote:** 「据此 900s→180s 已上线」
- **Superseding evidence:**
  - `~/dl_quant_live/config/book.json:43` — 「"k_seconds": 900,」
  - `~/dl_quant_live git log 7c7d4ae` — 「revert(exec): k 180→900 回滚 — 授权依据被实测推翻, 零锚运行于 180 之下」
- **A reader could wrongly conclude:** 180 s is live.
- **Affects:** reporting · **Severity reason:** Same k-window error as KB-15 inside the T3 pointer reading.
- **Proposed correction (exact text):** 据此曾授权 900s→180s, 但同日在任何锚运行前回滚(在役 900s)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 80->92)

### KB-47 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:36`
- **Quote:** 「第三分量是设计差: 回放有逐名止损层, 生产没有」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:169` — 「「回放独有的逐名止损层, 生产没有」只在目标文件层成立 —— 执行器有自己的逐名止损」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:20` — 「**执行器逐名止损在役并被逐锚评估**」
- **A reader could wrongly conclude:** Production has no per-name stop layer.
- **Affects:** future_eval, live_trading · **Severity reason:** A reader of T5 alone concludes production has no stop, which would misdirect a stop-layer deployment proposal.
- **Proposed correction (exact text):** 第三分量是目标文件层的设计差: 回放在目标层有逐名止损, 生产的 target_live 没有; 执行器在 target_live 之后另有逐名止损(`live/per_name_stop.py` wide 档, T5b Q2), 2026-09-13 W9 修复前对多头不平仓
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-48 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:9` · xref K2-F01, RELABEL_TABLE_K2 T4
- **Resolution:** XREF FIXPROGRAM K2 relabel — CROSS-REF: T4 NOT MATERIAL → INCONCLUSIVE per K2.
- **Quote:** 「**判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)。**」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带」
  - `docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.md:50` — 「| D1 | book_dg | bps / 4h anchor / unit gross (g = net_ex / gross_total; paired Δg or a component of it: price, carry, cost) | 0.05 |」
- **A reader could wrongly conclude:** The column-80 skew is proven immaterial.
- **Affects:** future_eval · **Severity reason:** The label is significance-only; CI upper +0.0625 exceeds the frozen δ 0.05, so economic immateriality is not established.
- **Proposed correction (exact text):** **判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)** ⇒ **FX-EVAL K2 重标: INCONCLUSIVE**(RELABEL_TABLE_K2, δ D1 = 0.05 / D4 = 0.003): 书层 Δg +0.0181 [−0.0299, +0.0625](s42)/ +0.0161 [−0.0332, +0.0645](s2027) 越出 ±0.05, 未排除经济意义差异; IC 轴 ΔIC −0.000101 [−0.000272, +0.000070] ⊂ ±0.003 = EQUIVALENT。不构成「不重要」证明
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-51 · P2 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:416`
- **Quote:** 「**装置 CAL=log 分支 = 原始 y4 = 无偏简单口径**(与真简单差 −0.04 bps/锚), 复验一律用 CAL=log」
- **Superseding evidence:**
  - `docs/REVIEW_caliber_final_2026-09-04.md:168` — 「故 **Π(1+r)−1 (N,N+4h] 是记账口径, Σ-simple 是有偏但小偏的代理**」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
  - `docs/REVIEW_caliber_final_2026-09-04.md:130` — 「2. **"CAL=log 腿级 0.05 bps 内无偏"被驳**」
- **A reader could wrongly conclude:** Re-validations should use CAL=log.
- **Affects:** future_eval · **Severity reason:** The ledger's caliber canon still calls CAL=log unbiased; later reviews measured leg-level bias and pinned RAW accounting.
- **Proposed correction (exact text):** 装置 CAL=log 分支 = 原始 y4 = Σ-simple, 是有偏小偏代理(fund 腿 +0.10~+0.27 bps/锚, REVIEW_caliber_final §C2 更正 2); 复验一律用 RAW 记账 Π(1+r)−1(CALIBER_PIN_v4)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 398->416)

### KB-52 · P2 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:302`
- **Quote:** 「**规则**: 席位敏感臂必须附"实盘席位固定"回放(W3FIX)作稳健性; 引用 2026 回放数字时声明"fund 0.99 构成"」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:5` — 「**一句话**: 固定席位**不是"同一本书冻结权重"**, 它是**另一本书**」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:58` — 「| 全周期 post-warm | 9139 | **0.46171** | — | 0.21 | 2.20× | — |」
- **A reader could wrongly conclude:** A W3FIX 0.21 replay is a valid robustness check and 2026 replay is 99% fund.
- **Affects:** future_eval, future_retrain · **Severity reason:** The rule still drives the v4 judge's fixed-seat arms at 0.21, a ruler shown to be a different book with no discriminating power.
- **Proposed correction (exact text):** (⚠ 2026-09-11 r5 ANGLE 1 推翻) 固定席位 W3FIX 是另一本书(2024/25 与动态席位年度损益反号, 相关 0.22/0.36), 0.21 取自缺陷态单日快照; v4 A0 动态席位 king 2026 均 0.36、全周期 0.46 ⇒ 「fund 0.99 构成」不成立; 席位敏感臂应以动态席位为主, 固定席位只作描述
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 287->302)

### KB-53 · P2 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:24` · xref CFG-04
- **Resolution:** XREF AUDIT_EXEC CFG-04 — CROSS-REF: same fact, ERROR_LEDGER side. Owner AUDIT_EXEC CFG-04 + CFG-04 AMENDMENT 1.
- **Quote:** 「→ 政策 A 全不追。**已闭环**。」
- **Superseding evidence:**
  - `~/dl_quant_live/live/chase_policy.py:144` — 「ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.5, ARM_NO_CHASE: 0.5}」
  - `STATE.md:125` — 「★ 追单臂重启部署**(PREREG_chase_restart 1a3f433325ae, 用户裁定)」
- **A reader could wrongly conclude:** The executor never chases residuals.
- **Affects:** reporting, live_trading · **Severity reason:** The ledger index says never-chase is closed; a 50/50 chase experiment has run since 09-01.
- **Proposed correction (exact text):** → 政策 A 全不追(08-10 结案); ⚠ 2026-09-01 16Z 起追单实验重启 ARM_WEIGHTS 0.5/0.5(PREREG_chase_restart), 书不再 maker-only
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 18->24)

### KB-54 · P2 · OPEN_NOT_MEASURED
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:17`
- **Quote:** 「受据: 该保费=历史利润 34%, β中性化毁 1/3 书 → 五臂全负 DO-NOT-RETRY」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。」
- **A reader could wrongly conclude:** Beta or dominance hedges are closed for the current book.
- **Affects:** future_eval · **Severity reason:** The β-premium DNR is from the pre-combo 08-19/20 instrument; the only current-book measurement (T8) finds no negative dominance exposure.
- **Proposed correction (exact text):** 受据(08-19/20 在役书旧仪器): 该保费=历史利润 34% … DO-NOT-RETRY。⚠ 未在 combo/A0 v4 复测; T8 §6.1 A0 v4 同期 corr(净额, 山寨−BTC)=+0.05 与之方向相反, 对账前本 DNR 不适用于在役形态
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 14->17)

### KB-56 · P2 · DOC_STALE
- **Source:** `STATE.md:159`
- **Quote:** 「动态席位(规则)2024→26 +1.21 bps/锚/gross, Sharpe 2.2, 2× 年化 +53% / 回撤 23%(2024 +24%, 2025 +28%, 2026 +140%)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:29` — 「原钉 W_ALPHA **[0.3207, 2.2822]**(SE 0.4890)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
  - `STATE.md:241` — 「**「≤−4% 日 ≈1–2/年」「maxDD 23%」「最差月 −17%」一律改称下界, 不是估计**」
- **A reader could wrongly conclude:** The live form returns about +53%/yr at 2× with a 23% drawdown, and V2MAIN 2026 runs Sharpe 4.0 / +114%/yr.
- **Affects:** reporting, future_eval · **Severity reason:** Planning-type annualised returns and drawdowns from the pre-v4, clip-compounded, arithmetic-×2 health check are quoted without CI or selection caveat in the in-flight section.
- **Proposed correction (exact text):** 本行为 2026-09-05 体检读数, 属**前 v4 口径**(裁剪复利记账 E-0908-B + 算术 ×2, 无 CI), 已被取代。⚠ 现行参照 = r18 v4 表: A0 **W_ALPHA 全窗 Sharpe 1.29 [0.32, 2.28]**, 2026 年内 4.53 [2.21, 6.79](**年内数, 非跨 regime**), 固定 2× 逐锚复利 NAV maxDD 2023 −28.92% / W_ALPHA −42.12%(尾部为下界, E-0908-B); **年化百分比不得作规划数引用**。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 157->159)

### KB-59 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:16`
- **Quote:** 「3. **重新加权到不了**: ~300 候选都进同一个席位, 与在役书 ρ≈0.9, 上限约 +0.8 夏普; 缺口需要**互不相关的书**。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:9` — 「① **"~300 条候选全是同一下注的重新加权"这句话撤回** —— 门二实测: 污染与干净基线上都只有 **2/14** 候选 |ρ|≥0.60(中位 |ρ| 0.025 / 0.037)」
  - `multi_asset/exports/research/uplift_2026-09-11/RESPONSE_to_independent_review_2026-09-12.md:64` — 「4. "数学上关不上" → **撤回**; 改"已测候选尚未弥补缺口"。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:12` — 「The members are almost one book: **N_eff (participation ratio) = 1.57 on W_FULL, 1.51 on FROZEN**.」
- **A reader could wrongly conclude:** All ~300 tested candidates are the same bet (ρ≈0.9) and +0.8 Sharpe is a mathematical ceiling for reweighting.
- **Affects:** future_eval · **Severity reason:** The second programme's premise repeats a claim withdrawn the day before; T6 supports it only for the 125 A0-lineage configurations, while independent-source candidates were orthogonal but had no net.
- **Proposed correction (exact text):** 3. **已测候选尚未弥补缺口**: A0 谱系上的 125 个配置几乎是一本书(T6 参与比 1.57, 描述性); 从独立数据源建的候选与书近乎正交(门二 |ρ| 中位 0.025/0.037)但无净额; 「+0.8 夏普上限」是已测最大提升, 不是上界(09-12 撤回)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 10->16)

### KB-60 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:47`
- **Quote:** 「**它们全都是同一个下注的重新加权。**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:9` — 「① **"~300 条候选全是同一下注的重新加权"这句话撤回**」
  - `multi_asset/exports/research/uplift_2026-09-11/RESPONSE_to_independent_review_2026-09-12.md:20` — 「| 0.6 | "数学上关不上"无上界证明 | 我把"已测候选的最大提升 +0.8"当成了上界 | **成立** | 全文改为"已测候选尚未弥补缺口" |」
- **A reader could wrongly conclude:** Reweighting mathematically cannot reach the target because every candidate is the same bet.
- **Affects:** future_eval, reporting · **Severity reason:** The closeout still carries both withdrawn sentences although the response says the full text was changed.
- **Proposed correction (exact text):** 已测候选(A0 谱系配置)高度相关、独立来源候选正交但无净额; 已测候选尚未弥补缺口(「数学上到不了 +2.55」撤回, 见 RESPONSE_to_independent_review_2026-09-12 §0.6)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 44->47)

### KB-63 · P2 · DOC_STALE
- **Source:** `docs/STATUS_three_questions_2026-09-12.md:28 (+1 more)`
- **Quote:** 「全周期 1.29」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「Sharpe 1.29 引用必须带窗: **W_ALPHA 2022-06-30 00Z→2026-08-30 20Z, 9,138 锚, 1.29122344 [0.3207, 2.2822]**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:37` — 「A0 s42 W_ALPHA g 0.6341956722 (pub. 0.6341957, tol 5e-7) · SR 1.2912234 (1.2912) · W_FULL g 0.5607541 (0.5608) · SR 1.1061630 (1.1062)」
- **A reader could wrongly conclude:** A reader takes 1.29 as the Sharpe of the whole history and compares it against W_FULL numbers, or repeats '全周期 1.29' into a planning document where the 900 dropped warm anchors (which contain the worst day in the sample) are silently excluded.
- **Affects:** reporting, future_eval · **Severity reason:** The sentence contrasts a frozen-window Sharpe that carries its window and n against a bare '全周期 1.29' that carries neither; 1.29 is W_ALPHA (9,138 anchors, warm-start dropped), while the actual full anchor axis (W_FULL, 10,038) reads 1.1062.
- **Proposed correction (exact text):** [在该行末尾追加] ⚠ **2026-09-16 更正(独立复审 FXR-DOC-3, FIXPROGRAM §12.1)**: 「全周期 1.29」的窗必须写出 —— 该数 = **W_ALPHA(2022-06-30 00Z → 2026-08-30 20Z, 9,138 锚, 丢前 900 暖机锚)Sharpe 1.29122344, CI95 [0.3207, 2.2822]**(探索性 2,000 次 UTC 日块自举, 保留日内不保留跨日, **不是选择校正后的区间**)。真正的全锚轴 = **W_FULL / W_TAIL(2022-01-31 起, 10,038 锚)= 1.1062**(T6 GATE-0)。另有 08-31 00Z 多一锚的 **9,139 锚 / 1.2947** 版本, 三者**不可混用**。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-65 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12`
- **Quote:** 「2. **全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举)」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「T6 的 **W_FULL 2022-01-31 起 10,038 锚 = 1.1062**; 原表另含 08-31 00Z 一锚的 9,139/1.2947 **不可混用**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:37` — 「W_FULL g 0.5607541 (0.5608) · SR 1.1061630 (1.1062)」
- **A reader could wrongly conclude:** A reader treats [0.32, 2.28] as already deflated for selection (it is not), or compares '全周期 1.29' with a later W_FULL number and concludes the book changed.
- **Affects:** reporting, future_eval · **Severity reason:** The programme's own headline calls W_ALPHA '全周期', while the same programme's T6 publishes 1.1062 for the actual full axis; the CI is also an exploratory day-block bootstrap, not a selection-corrected interval, which matters because the next bullet in this very document is about selection.
- **Proposed correction (exact text):** [在该行末尾追加] ⚠ **2026-09-16 更正(FXR-DOC-3)**: 此处「全周期」= **W_ALPHA(2022-06-30 00Z → 2026-08-30 20Z, 9,138 锚, 丢 900 暖机锚)**, 点估计 **1.29122344**, CI95 **[0.3207, 2.2822]** 为**探索性** 2,000 次 UTC 日块自举(保留日内不保留跨日), **不是选择校正后的区间**。真全锚轴 W_FULL(2022-01-31 起, 10,038 锚)= **1.1062**; 另有 9,139 锚 / 1.2947 版本; 三者不可混用。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 9->12)

### KB-66 · P2 · DOC_STALE
- **Source:** `docs/HANDOFF_round4_review_request_2026-09-13.md:77`
- **Quote:** 「- F1 125 个全书配置 N_eff 1.57(几乎一本书); PBO 0.157 / 0.187 未触发, 但由事后预选线 XIB_LAG50 撑着; r8–T2 家族 F3 PBO 0.508 触发; 选择折价下界 −0.65(全周期)/ −1.56(冻结窗), CI 含 0; A0 冻结窗 2.94 的 P(真 SR > 3) = 0.30(N_eff)/ 0.0047(N = 300)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:217` — 「T6: 参与比 N_eff 不是已校准的有效试验数; −0.65/−1.56 不是今后候选的统一最低折价; DSR 的 0.30/0.0047 是代入读数不是概率; §11 不能原样成为硬门。」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「N_eff≈1.57 不是有效独立试验数, `.30` 不是「真 Sharpe>3」的后验概率」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:70` — 「The truth for "how many independent looks" lies between, which is exactly why the probabilities span 0.30 → 0.005 for A0's 2.94 exceeding 3.0.」
- **A reader could wrongly conclude:** A reviewer or a later planning document treats 0.30 as 'a 30% chance the true Sharpe exceeds 3', or applies −0.65 SR as a standing haircut to an unrelated candidate.
- **Affects:** future_eval, reporting · **Severity reason:** The review request passes three T6 quantities to an independent reviewer as settled readings, and all three were withdrawn as such: N_eff is a participation ratio not a calibrated trial count, the −0.65/−1.56 haircuts describe this family's realised selection path rather than a floor for future candidates, and 0.30/0.0047 are substitutions under two different N assumptions rather than a posterior.
- **Proposed correction (exact text):** [在该行末尾追加] ⚠ **2026-09-16 更正(独立复审 FXR-DOC-3 + PROGRAM_uplift_r2 §196 + REVIEW_round4 §4.2)**: 本行三个量**均已降为描述性读数**, 不得当判据: ① **N_eff 1.57 是相关矩阵特征值参与比, 不是已校准的有效独立试验数**(T6 §「How to read the N columns」自述真值介于 N_eff 与 N_raw/300 之间); ② **−0.65(W_ALPHA)/ −1.56(冻结窗)是本家族在已实现选择路径上的描述, 不是今后任意候选的最低折价下界**; ③ **0.30 / 0.0047 是不同 N 假设下的代入读数, 不是「真 Sharpe > 3」的后验概率**。仍成立的只有: 候选家族高度相关、冻结窗高水平为全家族共有、A0 冻结窗 CI95 [1.306, 4.565]。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-67 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:36`
- **Quote:** 「5. **Two windows, never mixed.** `W_ALPHA` n=**9138** (drop first 900 warm anchors, E-0911-A; ceiling 2026-08-30 20Z, E-0911-D) for every mean/CI/Sharpe/turnover/leg number. `W_TAIL` n=**10038** (no warm drop, same ceiling)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:37` — 「W_FULL g 0.5607541 (0.5608) · SR 1.1061630 (1.1062)」
  - `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:258` — 「W_FULL = A0 轴 ts ≤ 2026-08-30 20Z(n = 10,038); W_ALPHA = W_FULL ∧ 行 ≥ 900(n = 9,138, 首锚 2022-06-30 00Z)」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「T6 的 **W_FULL 2022-01-31 起 10,038 锚 = 1.1062**」
- **A reader could wrongly conclude:** Two names for one anchor set: a reader either rejects the W_FULL Sharpe as out-of-caliber, or assumes W_FULL is a fourth window and mixes it with the 9,139-anchor variant.
- **Affects:** future_eval, reporting · **Severity reason:** The canonical table names the 10,038-anchor axis `W_TAIL` and reserves it for maxDD/worst-day/halt numbers only, but T6 and the parity prereg call the identical set `W_FULL` and publish a Sharpe on it (1.1062); a reader obeying this rule literally would treat a published W_FULL Sharpe as a caliber violation rather than as the third legitimate window.
- **Proposed correction (exact text):** [§5 原字节保留, 在第 5 条末尾追加] ⚠ **2026-09-16 绑定(FXR-DOC-3; lead 裁定措辞)**: ① **`W_FULL`(T6 与 `PREREG_producer_parity_phase2_oos_2026-09-12.md` §258)与 `W_TAIL`(本表第 5 条)是同一个 10,038 锚集合的两个名字** —— 定义逐字相同(不丢暖启锚, 天花板 2026-08-30 20Z)。**规范名 = `W_FULL`, `W_TAIL` 为其别名**(不是反过来), 因为 T6 的 GATE-0 已经在该窗上发布了 Sharpe。② 本条「仅用于 maxDD / 最差日 / 停机数」是**本表自身的使用约定, 不是对在该窗上报告 Sharpe 的禁令**。T6 GATE-0 发布的 **W_FULL g 0.5607541 · SR 1.1061630(published 1.1062)是合法的第三个窗读数**, 条件是**同时写出窗名、锚数与成本面**。③ **四个在流通的数, 各自绑定, 互不可混用**: **W_ALPHA 9,138 锚 SR 1.29122344 CI95 [0.3207, 2.2822]**(探索性 2,000 次 UTC 日块自举, 保留日内不保留跨日, **非选择校正区间**; 拟合成本面 `costb_PWR_G230k.json` sha 295b4e7b…)· **W_FULL / W_TAIL 10,038 锚 SR 1.1062**(g 0.5608)· **9,139 锚 SR 1.2947**(多含 08-31 00Z 一锚)· **n=9018 SR 1.4150**(已被取代, 且**正是本表 §0-3 点名的那个陷阱** —— 拟合成本面在该窗读 0.689021 / 1.4150, 与在役纯费成本面在 W_ALPHA 上的 0.688853 / 1.4025 数值几乎相同但**是两回事**)。④ 引用任一夏普**必须写窗名 + 锚数 + 成本面**, 缺一即作废。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-68 · P2 · DOC_STALE
- **Source:** `STATE.md:66`
- **Quote:** 「A0 全周期 post-warm **1.4150** [0.449,2.381] n=9018; 加 E-0911-D 截断 **1.2912** [0.332,2.251] n=9138」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:32` — 「The trap: the cheap-plane number **0.6889** is numerically almost identical to the fitted-plane number at a *different window* (n=9018: **0.689021 / SR 1.4150**)」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:217` — 「Sharpe 1.29 引用必须带窗: **W_ALPHA 2022-06-30 00Z→2026-08-30 20Z, 9,138 锚, 1.29122344 [0.3207, 2.2822]**」
- **A reader could wrongly conclude:** A reader quotes 1.4150 as a full-cycle Sharpe, or sees 0.689/1.41 elsewhere and assumes it is the same reading when one is a different window and the other a different cost plane.
- **Affects:** reporting, future_eval · **Severity reason:** STATE is the truth source and this line puts a fifth number (1.4150 at n=9018) into circulation labelled '全周期 post-warm'; CANONICAL_NUMBERS §0-3 flags n=9018 as the specific trap where a fitted-plane number is numerically confusable with a cheap-plane number at the pinned window.
- **Proposed correction (exact text):** [在该行末尾追加] ⚠ **2026-09-16 更正(FXR-DOC-3 + CANONICAL_NUMBERS §0-3/§0-5)**: 两个数都不是「全周期」—— **n=9018 是 E-0911-D 截断前的 post-warm 窗(已作废)**, n=9138 = **W_ALPHA(2022-06-30 00Z → 2026-08-30 20Z)**; 真正的全锚轴是 **W_FULL / W_TAIL 10,038 锚 = SR 1.1062**。且 n=9018 是**已知陷阱格**: 拟合成本面在该窗读 0.689021 / 1.4150, 与在役纯费成本面在 W_ALPHA 上的 0.688853 / 1.4025 数值几乎相同但**是两回事**。引用任一夏普必须写窗名 + 锚数 + 成本面。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-72 · P2 · DOC_STALE
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:267`
- **Quote:** 「**PROD-31(无文件)不进该分裂, 一律 HIGH**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:402` — 「| PROD-31 | `fea171/f10_live_s42.pt` 是八月模型, 不是 351ae26b 背后的 checkpoint | 08-29 20Z 生产者根本没写 king 文件 | **PROD-42** |」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:257` — 「| **PROD-42**(原登记为 PROD-31, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | **08-29 20Z: 生产者根本没出 king 文件**」
- **A reader could wrongly conclude:** Whoever implements the PROD-27 severity split looks up PROD-31, finds an unrelated model-artefact item, and either implements the wrong exemption or cannot tell which condition is meant to bypass the late_producer / late_daemon_start split.
- **Affects:** live_trading, reporting · **Severity reason:** The 2026-09-16 renumbering fixed the §13.1 register table and STATE.md, but §13.2 ruling 1 — the PROD-27 severity split that FX-PROD is to implement — still refers to the item by its withdrawn number PROD-31, which now resolves in AUDIT_PROD to 'fea171/f10_live_s42.pt is the August model'.
- **Proposed correction (exact text):** [替换该短语, 原字节以括号保留] **PROD-42(无文件, 原登记为 PROD-31)不进该分裂, 一律 HIGH**
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 266->267)

### KB-73 · P2 · OPEN_NOT_MEASURED
- **Source:** `CLAUDE.md:46`
- **Resolution:** **PARTLY APPLIED + ESCALATED TO BLOCKING** 2026-09-16. (a) The `CLAUDE.md:46` half is applied by the lead in commit **e9876c3a**, as an in-place rewrite of the routing pointer rather than an appended annotation — defensible for a routing cell whose content was a path, and the pre-correction wording is preserved in this row's `quote` field, so nothing is lost. (b) The lead escalated the rest to a **blocking** item (FIXPROGRAM §20.6–20.9), accepting this register's 'proposal, not applied' as mandatory: **① every battery run this round must record the interpreter** (before and after: whether `ACCEPT_PY` was set, the resolved absolute `$PY`, `sys.version`, `torch.__version__`), recorded in each worker's own wrapper, **`run_acceptance.sh` itself unchanged** — issued to FX-EXEC (05:05Z), FX-PROD (04:50Z) and FX-EXEC2; **② FX-EXEC must make the runner write the resolved `$PY` and `sys.version` into the log header and JSON, and change `tests_acceptance_entrypoints` from a source-substring assertion to an assertion on the effective interpreter — and this must land BEFORE the three-branch stacked battery**, otherwise the stacked battery certifies nothing either. Red test = the shape this row gives: on the old code point `ACCEPT_PY` at 3.14 and run that suite; it still prints OK ⇒ red for the right reason.
- **Quote:** 「| 部署/回滚/电池 | `~/dl_quant_live/ops/safe_commit.sh` + `run_acceptance.sh` |」
- **Superseding evidence:**
  - `~/dl_quant_live/run_acceptance.sh:28` — 「PY="${ACCEPT_PY:-/usr/bin/python3}"」
  - `~/dl_quant_live/run_acceptance.sh:20` — 「# This machine has three: /usr/local/bin/python3 (3.14.4, NO torch — and torch has no 3.14 wheels」
  - `~/dl_quant_live/live/run_acceptance.sh:15` — 「# the freeze. The same split also manufactured two false "known failures": under bare python3」
  - `~/dl_quant_live/live/tests_acceptance_entrypoints.py:55` — 「"ACCEPT_PY:-/usr/bin/python3" in open(ROOT_SH).read(), "ACCEPT_PY pinned"」
- **A reader could wrongly conclude:** Two battery counts from different dates are compared as if they measured the same thing. A run launched with ACCEPT_PY set to the 3.14 interpreter loses torch/numpy, `tests_inference_parity` and `tests_panel_build` fail for want of them — and `tests_acceptance_entrypoints` still prints OK 「ACCEPT_PY pinned」, because the string is still in the file. The reader takes the red cells for real failures, which is exactly what happened before 2026-07-27.
- **Affects:** reporting, future_eval · **Severity reason:** Every 「逐套件 N/M」 receipt in the knowledge base is comparable only if the same interpreter produced it, and no acceptance artefact records which one did: the runner resolves `PY="${ACCEPT_PY:-/usr/bin/python3}"` and invokes each suite with "$PY" (L278) without ever echoing the resolved path, and the suite that certifies the pin checks only that the STRING `ACCEPT_PY:-/usr/bin/python3` appears in the file, not which interpreter the run used.
- **Proposed correction (exact text):** [在该行后插入] > ⚠ **口径项 KB-73(2026-09-16)**: 电池脚本在 **`~/dl_quant_live/run_acceptance.sh`(仓根, 不在 `ops/`)**; `ops/` 下的是 `safe_commit.sh`。**解释器钉在 L28 `PY="${ACCEPT_PY:-/usr/bin/python3}"`** —— 本机三个解释器: `/usr/bin/python3` **3.9.6**(torch 2.2.2 + numpy 1.26.4 + pandas 2.3.3, 唯一能跑推理的)· `/usr/local/bin/python3` **3.14.4**(裸 `python3` 解析到它, **无 torch**)· `/opt/anaconda3` 3.7.6(torch 1.4.0, 过旧)。**⇒ 任何「逐套件 N/M」数字只在同一解释器下可比。** 三条已测边界: ① 该钉是**默认值, 可被环境变量 `ACCEPT_PY` 覆盖**; ② 认证它的断言 (`live/tests_acceptance_entrypoints.py:55`) 是对**源码文本**做子串检查(`"ACCEPT_PY:-/usr/bin/python3" in open(ROOT_SH).read()`), **不断言本次运行实际用的是哪个解释器** ⇒ 覆盖运行时它照样打 OK; ③ `state/acceptance/` **38,177 份工件中 0 份记录解释器版本**(唯一 465 次 `/usr/bin/python3` 出现在 `gate_coverage` 的字节码缓存盲区说明里, 不是运行收据)。**2026-07-27 之前更不可比**: 当时两个入口一钉一裸, 裸 `python3` 让 `tests_inference_parity` 与 `tests_panel_build` 因缺 torch 变红, 二者在钉住的解释器下**全过** —— 源码自述这是「两个假的 known failures」。**引用任何电池计数时须写明解释器**; 建议(提案): 运行器把解析后的 `$PY` 与 `sys.version` 写进日志头与 JSON, 并把断言从子串改为断言**有效解释器**。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** absent

### KB-74 · P2 · DOC_STALE
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:311`
- **Resolution:** APPLIED by lead 2026-09-16, commit **b87ed509** (FIXPROGRAM §20.6): §15.2's TRN-28 renumbered to **TRN-30**, original marked SUPERSEDED-ID, §15.2/§15.3 references synchronised. The lead's own framing confirms why this was worse than the PROD case: 「同一份文件的 §3.2 第 100 行早已把 `TRN-28` 按 AUDIT_TRAIN 的原义路由给 K4 —— 一个号、两个主、两个严重度, 在同一个文件里」。 `PROD-28-STALE` retained on the distinction this register drew (§20.6): it is a status annotation on AUDIT_PROD's PROD-28 **record**, not a new finding hung on an existing id, so the reason for renumbering PROD-36b does not apply to it.
- **Quote:** 「| **TRN-28** | `pod_f10_np_export.py` 在**自己的 V1 门判词之前**就写出可部署 npz」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_TRAIN.md:3` — 「AUDIT_TRAIN」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:100` — 「| K4(lead) | TRN-13 · TRN-28 · TRN-29 |」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:409` — 「**规矩(新)**: 本纲领新开的登记号**必须先对四份审计登记」
- **A reader could wrongly conclude:** One document assigns TRN-28 to two owners (K4 at §3.2, FX-TRAIN at §15.2) with two severities (P2 doc-routing vs P1 live-artefact overwrite). Whoever works the queue by id either fixes a documentation pointer believing they closed a P1, or cannot tell which is meant.
- **Affects:** future_retrain, reporting · **Severity reason:** The PROD family was renumbered on 2026-09-16 but the same defect survives at TRN-28: §15.2 opens it as a P1 owned by FX-TRAIN (`pod_f10_np_export.py` writes a deployable npz before its own gate verdict), while AUDIT_TRAIN (7e1ecf9a) TRN-28 is 「CLAUDE.md routes 月度重训 to the superseded September runbook」 — and §3.2 of the SAME document already routes TRN-28 to K4 in the AUDIT_TRAIN sense.
- **Proposed correction (exact text):** [§15.2 表内原编号字节保留, 就地注明] ⚠ **2026-09-16 编号更正(aud-kb KB-74, 与 §17.5 同一把尺子)**: 本行的 **TRN-28 与 `AUDIT_TRAIN`(7e1ecf9a)已占用的 TRN-28 撞号**(原主 = 「CLAUDE.md 把月度重训指向已作废的九月 runbook」), 且**本纲领 §3.2 已按原主义把 TRN-28 派给 K4** ⇒ 同一文件内一号两主两级。**AUDIT_TRAIN 最高号 TRN-29, 空号自 TRN-30 起** ⇒ 本项改为 **TRN-30**(原号标 SUPERSEDED-ID)。§15.2 与 §15.3 内对本项的引用同步改。**其余 §13–§17 新号经逐一查重均不撞**: OPS-04(AUDIT_EXEC 只到 OPS-03)· LED-09(AUDIT_EXEC 只到 LED-08, AUDIT_DATA 只有 LED-01)· RES-01 · TEST-01 · BAT-01 · EXEC-RACE-01 · DATA-COR-1 · W6C-I6 · MON-1..4 · FXR-* 全部为空号。**`PROD-28-STALE` 保留**: 它是对 AUDIT_PROD PROD-28 这条记录的**状态标注**, 不是新发现, 后缀语义正确(与 PROD-36b 不同 —— 那是另一个发现被挂了子项后缀)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-75 · P2 · DOC_STALE
- **Source:** `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:88`
- **Resolution:** **RESOLVED-BY-CONVENTION** 2026-09-16, commit **b87ed509** (FIXPROGRAM §20.6, and the dedup rule in §17.5 extended). Ruling: the two pre-existing collisions are **not renumbered** — AUDIT_EXEC and AUDIT_DATA are two other auditors' committed registers and renumbering would dangle every existing citation, which is exactly the cost the lead avoided by renumbering their own new ids instead. **Cite with a register prefix: `EXEC:LED-01` / `DATA:LED-01` / `EXEC:DOC-01` / `DATA:DOC-01`.** §17.5's dedup rule now explicitly covers the four audits **against each other**, not only the programme against the audits.
- **Quote:** 「| LED-01 | ledger / fills.jsonl | fills.jsonl holds every trade exactly twice; in-repo readers collapse the copies, a naive reader double counts |」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_DATA.md:91` — 「| LED-01 | research readers of daily_nav (AUDIT_EXEC LED-04) | Research tools that read daily_nav.realised_by_type COMMISSION/REALIZED_PNL inside 07-29..09-12 print wrong fee columns; their conclusions do not use them |」
  - `docs/audit_pipeline_2026-09-13/AUDIT_DATA.md:75` — 「| DOC-01 | docs and memory | Caliber documents and memory notes miss or misstate several data-lineage facts |」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:96` — 「| DOC-01 | docs / STATE and CLAUDE.md | STATE §1 and CLAUDE.md carry stale executor facts |」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:86` — 「| FX-EXEC2 | LED-01 · LED-02 · LED-03 · LED-04 · LED-05 · LED-07 · LED-08」
- **A reader could wrongly conclude:** A bare citation of 「LED-01」 or 「DOC-01」 resolves to whichever register the reader opens first: the fills.jsonl double-write (P3, VERIFIED_IMMATERIAL, owner FX-EXEC2) or the daily_nav fee-column reader defect (P3, owner K4); 「DOC-01」 is either the executor facts in STATE/CLAUDE.md or the data-lineage facts in the caliber documents. The new rule in §17.5 prevents future collisions but does not resolve these two, which predate it.
- **Affects:** reporting, future_eval · **Severity reason:** Two of the four audit registers themselves double-book two ids for different findings — AUDIT_EXEC and AUDIT_DATA each define LED-01 and DOC-01 — and the fix programme routes them to different owners, disambiguating only by an optional parenthetical (§86 bare 「LED-01」 → FX-EXEC2 = the EXEC item; §126 「LED-01(研究工具打印错费列)」 → K4 = the DATA item).
- **Proposed correction (exact text):** [两份登记的原编号字节保留, **不建议重编已发布的审计登记**; 改为在引用侧加限定] ⚠ **2026-09-16 补注(aud-kb KB-75)**: **`LED-01` 与 `DOC-01` 在 `AUDIT_EXEC`(842bbffa)与 `AUDIT_DATA`(bb8a2806)中各有一个不同的发现**, 且两者**先于** §17.5 的新规矩存在, 不是本纲领开的号。四条原主: `EXEC:LED-01` = fills.jsonl 每笔成交写两次(P3, VERIFIED_IMMATERIAL)· `DATA:LED-01` = 研究工具读 daily_nav 的 COMMISSION/REALIZED_PNL 在 07-29..09-12 打印错费列(P3)· `EXEC:DOC-01` = STATE §1 与 CLAUDE.md 的执行器事实陈旧(P3)· `DATA:DOC-01` = 口径文档与记忆条目缺漏/写错数据谱系事实(P2)。**处置建议(不重编已发布登记, 因为它们是另两位审计者的已提交产物, 重编会让其全部既有引用悬空)**: 引用时一律带登记前缀 —— **`EXEC:LED-01` / `DATA:LED-01` / `EXEC:DOC-01` / `DATA:DOC-01`**; 纲领 §3.1 L86 的裸 `LED-01` 应读作 `EXEC:LED-01`, §4.3 L126 的两项应读作 `DATA:DOC-01` 与 `DATA:LED-01`, §3.1 L92 的 `DOC-01(STATE/CLAUDE.md 侧)` 应读作 `EXEC:DOC-01`。**§17.5 的新规矩建议补一句**: 查重范围包含四份审计**彼此之间**, 不只是纲领对审计。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-76 · P2 · DOC_STALE
- **Source:** `docs/fixprogram_2026-09-13/FX_DATA/FACT_TABLE_DATA.md:129`
- **Quote:** 「whose anchor state is **NODATA** (no 5m rows in the window) yet which carries `f_fund_now` = **−205.7 bps** 8h-equivalent on the panel row」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:518` — 「**−205.7 bps 是真实的场所费率**: zip 申报 `iv 8.0`, 两侧 8 小时间距干净 ⇒ **「间距被标错」这一假设对该格被证伪**」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4b/RESULT_L4b.md:47` — 「fund_aug keeps recording funding for some stopped perps (MDT 1,197 events after its last trade; AMB 23; LINA 5; BTTC 3; BNX 3), so the no-funding exit never fired.」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:9` — 「3 newly ineligible = BNXUSDT at its first anchor after a data gap」
- **A reader could wrongly conclude:** A reader takes −205.7 bps as an example of the x0910 / FND interval defect and either counts it toward that defect's size or expects the FND fix to remove it. It is a tradability / membership problem: the name passes the member rule on a NODATA anchor because its qvk is finite.
- **Affects:** future_eval, future_retrain · **Severity reason:** The F6 row presents the BNXUSDT −205.7 bps cell in a context that invites reading it as a funding-interval defect (it closes 「relevant to the FND items」), but FX-PROD checked the zip: it declares `iv 8.0` with clean 8-hour spacing on both sides, so the mislabelled-interval hypothesis is falsified for this cell.
- **Proposed correction (exact text):** [F6 行原字节保留, 在其后插入] > ⚠ **更正 KB-76(2026-09-16, FX-PROD 核; FIXPROGRAM §20.3)**: **−205.7 bps 是真实的场所费率, 不是间隔缺陷** —— zip 申报 `iv 8.0`, 该格两侧 8 小时间距干净 ⇒ **「间距被标错」这一假设对该格被证伪**, 本行末句「relevant to the FND items」**不适用于这个数**, **不得把 BNXUSDT 这个值当作资金费间隔缺陷的例子**。**F6 的另一半仍然成立**: 该锚 `NODATA`(窗内无 5m 行)而 `qvk` 有限故通过成员筛, 且审计的两个旗标都看不见它(`Z24` 要求窗内 `ret5` 有限; `DEAD` 要求该名此后再不交易, 而 BNXUSDT 交易至 2025-03-17)⇒ **只有可交易性旗标抓得住这一类**。即本条是**可交易性 / 成员资格**问题(TRD 族), 不是 FND 族。旁证同向: 该名在 `L4b` 里正是「合约停交易后 fund_aug 仍记 3 次资金费」的名单之一, 在 `r18` 里是「数据缺口后首锚资格改变」的 3 格之一。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-03 · P3 · DOC_STALE
- **Source:** `CLAUDE.md:14`
- **Resolution:** APPLIED by lead 2026-09-16: CLAUDE.md:14 now reads 「**N+24:00 读取交易**(… 2026-08-27 05:2xZ 由 N+23 改为 N+24 … 本行原写 N+23, 2026-09-16 按实盘配置更正)」 — original wording retained in the parenthetical per the 'original bytes stay' convention. Owner of the fact: AUDIT_PROD PROD-33. See KB-71.
- **Quote:** 「N+23 读取交易」
- **Superseding evidence:**
  - `~/dl_quant_live git log 37cd6cd (2026-08-27 13:40 +0800)` — 「timing: anchor_offset_min 23→24」
  - `STATE.md:153` — 「执行器 config 仍 `anchor_offset_min: 24`」
- **A reader could wrongly conclude:** The executor reads at N+23.
- **Affects:** reporting · **Severity reason:** Timing label only; execution-delay studies already use E+24 min.
- **Proposed correction (exact text):** N+24 读取交易(config anchor_offset_min 24, 2026-08-27 起)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-11 · P3 · DOC_STALE
- **Source:** `STATE.md:142`
- **Resolution:** APPLIED by lead 2026-09-16: STATE.md:144 now reads 「**N+24:00** 读并交易(`anchor_offset_min=24` / `poll_grace_min=5` … 本行原写 N+23, 09-16 更正)」. Owner of the fact: AUDIT_PROD PROD-33. ⚠ The same line's new annotation cites 「登记为 PROD-30」, which collides with AUDIT_PROD PROD-30 — see KB-70.
- **Quote:** 「N+23 读并交易」
- **Superseding evidence:**
  - `~/dl_quant_live git log 37cd6cd (2026-08-27)` — 「timing: anchor_offset_min 23→24」
- **A reader could wrongly conclude:** The executor reads at N+23.
- **Affects:** reporting · **Severity reason:** Timing label only.
- **Proposed correction (exact text):** N+24 读并交易(anchor_offset_min 24, 08-27 起)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### KB-12 · P3 · DOC_STALE
- **Source:** `STATE.md:149`
- **Resolution:** ⚠ **口径(KB-73)**: 本行引用的「逐套件 N/M」只在同一解释器下可比 —— 电池 `run_acceptance.sh:28` 的 `PY="${ACCEPT_PY:-/usr/bin/python3}"` 是**可被环境变量覆盖的默认值**, 认证它的断言只对源码做子串检查, 且 `state/acceptance/` 38,177 份工件中 0 份记录解释器版本; 2026-07-27 前两入口一钉一裸, 裸 `python3` 制造过两个假红。引用计数时须写明解释器。
- **Quote:** 「`~/dl_quant_live/ops/safe_commit.sh` + 电池 123/123」
- **Superseding evidence:**
  - `STATE.md:7` — 「**运行树电池 ACCEPTANCE: ALL GREEN 135/135(130 套件 + 5 审计门, tests_env_loading 14/14)**」
- **A reader could wrongly conclude:** The live battery has 123 suites.
- **Affects:** reporting · **Severity reason:** Count only; a reader comparing a new run to 123 would misjudge coverage.
- **Proposed correction (exact text):** `~/dl_quant_live/ops/safe_commit.sh` + 电池 ALL GREEN 135/135(130 套件 + 5 审计门, 2026-09-13 ef60f85); safe_commit 会 rebase 到 origin/main, 提交前核 `HEAD..origin/main` = 0
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 147->149)

### KB-18 · P3 · DOC_STALE
- **Source:** `STATE.md:255`
- **Quote:** 「无干净 CONST2027」
- **Superseding evidence:**
  - `STATE.md:210` — 「干净 CONST2027 参照研究员 09-07 已完成 20/20 + 两次回放 rc0」
- **A reader could wrongly conclude:** No clean second-seed CONST2027 reference exists.
- **Affects:** future_eval · **Severity reason:** Contradicted two sections earlier in the same file (§3).
- **Proposed correction (exact text):** (★ 09-09 更正: 干净 CONST2027 已由研究员 09-07 完成, 见 §3 待观察条)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 253->255)

### KB-36 · P3 · DOC_STALE
- **Source:** `docs/CHECKLIST_combo_switch_2026-08-26.md:45`
- **Quote:** 「3. fund 构成升至 ~77%(候选结构属性, 已在正典文档 §3 局限声明)。」
- **Superseding evidence:**
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:45` — 「min 0.1878 / p25 0.2110 / **中位 0.2242** / p75 0.3244 / max 0.3592 / 均 0.2572; 53% 的锚落在 0.21±0.02。」
- **A reader could wrongly conclude:** Fund share is ~77%.
- **Affects:** reporting · **Severity reason:** Historical residual list; composition moved.
- **Proposed correction (exact text):** 3. fund 构成 08-26 为 ~77%, 随席位滚动(2026-09-13 12Z fund 席位 0.618)。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 39->45)

### KB-38 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:17`
- **Quote:** 「(未复跑; carry/净额数字 PROVISIONAL, 价格读数不受影响)」
- **Superseding evidence:**
  - `STATE.md:6` — 「IV 经 FTRIM(FN×8/IV ≤ −10bp)改仓位进而改价格, 只有「固定旧 W 再计价」才不受影响」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:223` — 「T5d 以生产者账本间隔为真值, 而 FX-PROD(P9)证明账本在短→长切换行按时间差误标; 已派 T5d-R」
- **A reader could wrongly conclude:** Price readings of T5c are immune to the interval defect.
- **Affects:** future_eval · **Severity reason:** Corrected in the same file's 12:1xZ section, but the fact-table row still carries the withdrawn clause; T5d's own interval truth is now under T5d-R.
- **Proposed correction (exact text):** (未复跑; T5d 用真实间隔重生成权重后价格变化 −0.07/−0.09, 标签不变; carry 修正 +0.253 待 T5d-R 对账; 部署/模型差 −4.15..+1.71 不可排除)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 14->17)

### KB-42 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:8`
- **Quote:** 「**实盘亏在资金费, 不在价格也不在执行**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:124` — 「**更正 1: AMENDMENT 2 说「实盘窗是 carry 高于常态与价格边归零**同时**发生」—— 错, 是**先后**发生。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:27` — 「**但价格那一半对窗口端点极敏感**」
- **A reader could wrongly conclude:** Live losses are all funding, price edge is zero.
- **Affects:** reporting, future_eval · **Severity reason:** Corrected by AMENDMENT 2/3 in the same file, but §0 item 1 is unmarked and is the most quoted line.
- **Proposed correction (exact text):** 在 §0 第 1 条后加: (⚠ 见 AMENDMENT 2/3 与 T1: 高 carry 与价格转负先后发生; 「价格为零」对窗口端点敏感, 加 11 锚变为 +1.435 [−6.31, +8.41])
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-43 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:27`
- **Quote:** 「回放可用于定位, 幅度按 0.835 折算」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:143` — 「P2 读法改为「基线回放幅度偏大 15–27%, **不得**用于换算候选增量」」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:144` — 「P5 改名为「**量级启发**(非上界)」」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:71` — 「1. **P7 作废**」
- **A reader could wrongly conclude:** Candidate increments can be scaled by 0.835; ≤+0.2 Sharpe is a ceiling; slowing reversal is dead; markout makes all cost verdicts 41% cheap.
- **Affects:** future_eval · **Severity reason:** Fact-table rows P2/P5/P6/P7 carry no inline marker; corrections sit in AMENDMENT 1 and 4 further down.
- **Proposed correction (exact text):** 在 §1 表 P2/P5/P6/P7 各行末加: P2「(AMENDMENT 4: 只描述基线回放, 不得换算候选增量)」; P5「(AMENDMENT 4: 量级启发, 非上界)」; P6「(AMENDMENT 4: 只证 EMA 三剂量平滑杀反转 alpha, 其他低换手实现未测)」; P7「(AMENDMENT 1: 作废)」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 18->27)

### KB-49 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:12` · xref K2-F04, RELABEL_TABLE_K2 T5b Q1
- **Resolution:** XREF FIXPROGRAM K2 relabel — CROSS-REF: T5b primary NOT MATERIAL stands (established below the band); the secondary MATERIAL → INCONCLUSIVE per K2.
- **Quote:** 「⇒ **NOT MATERIAL**, 标 **PROVISIONAL**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:29` — 「| F04 | T5b Q1 |」
- **A reader could wrongly conclude:** Frozen FTRIM residuals have no material carry effect.
- **Affects:** future_eval · **Severity reason:** One-sided point-estimate line: −0.120 [−0.245, −0.021] is significant and 2.4× the line in the receive direction but prints NOT MATERIAL.
- **Proposed correction (exact text):** ⇒ **NOT MATERIAL (established below line)**(K2 重标: CI 上界 −0.021 < 0.05; 只判付出方向)—— 冻结残余净**收取** carry −0.120 [−0.245, −0.021](CI 排零), 不是「无影响」; 次级「全部 FTRIM 残余 +0.115 [−0.080, +0.334] ⇒ MATERIAL」K2 重标为 INCONCLUSIVE; 标 PROVISIONAL
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-55 · P3 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:6`
- **Quote:** 「任何 |单锚|>2σ(实测 σ≈39U, 即 |Δ|>78U)24h 内必须成 entry」
- **Superseding evidence:**
  - `STATE.md:203` — 「当前 regime 日σ ≈ **2.05%(±1,686 USDT @NAV 82k)**」
  - `~/guard_twin/state/latest.json (2026-09-13T13:46:30Z)` — 「"nav_latest": 117566.70399028」
- **A reader could wrongly conclude:** Anchors beyond ±78U are 2σ events.
- **Affects:** reporting · **Severity reason:** Trigger calibrated at NAV ≈15k; at NAV ≈117k the 78U line fires on ordinary noise.
- **Proposed correction (exact text):** 任何 |单锚| > 2σ(σ 按当前 NAV 与近 30 天逐锚净额实测重标, 写明标定日; 08-20 标定 σ≈39U@NAV≈15k 已过期)24h 内必须成 entry
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-57 · P3 · DOC_STALE
- **Source:** `STATE.md:166`
- **Quote:** 「会话 cron 重建(09-05 14:1xZ; /login 切换清空)**: 每锚深查 47686c87 · jpline 2h 538814c5 · combo 84 锚二读 48a8bb77(09-09)」
- **Superseding evidence:**
  - `lead transcript tool_result line 20040` — 「Scheduled recurring job 41df7caa (9 1,5,9,13,17,21 * * *). Session-only (not written to disk, dies when Claude exits). Auto-expires after 7 days.」
  - `STATE.md:182` — 「**jpline 重连定时已按用户字停止(09-06 05:4xZ)。**」
- **A reader could wrongly conclude:** Deep-check runs under 47686c87 alongside a jpline job.
- **Affects:** reporting, live_trading · **Severity reason:** Job ids and set are stale; the live deep-check job is 41df7caa (09-09) and expires about 09-16 00:24Z.
- **Proposed correction (exact text):** 现行会话 cron: 每锚深查 **a84f2bd4**(2026-09-16 重建, 排程 `9 1,5,9,13,17,21`, 含盲态附注; 前身 41df7caa → 46dd536b)· 抛物线起始前向日志(`52 14 * * *`)· 两者均会话级 **7 天自动过期 ≈2026-09-23**, 到期须按修订模板重建。jpline 2h 重连已于 09-06 按用户字停止(且 jpline 自 09-04 不可达); combo 84 锚二读 09-09 已完成。模板与「lead 更正附注」见 `docs/CRON_TEMPLATES_2026-09-04.md` 文末与 `docs/audit_pipeline_2026-09-13/AUDIT_KB.md` §5。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 164->166)

### KB-58 · P3 · DOC_STALE
- **Source:** `STATE.md:226`
- **Quote:** 「@2× 2024→26 算术/CAGR」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL)」
- **A reader could wrongly conclude:** The in-service form compounds 70–75%/yr at 2× over 2024–26.
- **Affects:** reporting · **Severity reason:** Pre-v4 CRYPTO-arm level table (CAGR 70–75% at 2×, 2026 Sharpe 5.3) sits in the caliber-discipline section without CI; its own later bullet calls the tails lower bounds.
- **Proposed correction (exact text):** 在该表下加: ⚠ 前 v4 口径(裁剪复利记账、算术/CAGR 未扣选择), 无 CI; 水平读数以 r18 v4 表为准(W_ALPHA Sharpe 1.29 [0.32, 2.28]), 回撤以固定 2× 复利 NAV 为准
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 224->226)

### KB-62 · P3 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:266`
- **Quote:** 「③**修复项(待用户字)**: 生产者栈 launchd 化(RunAtLoad, shadow.lock 防双跑), 消灭"重启即断链"类。」
- **Superseding evidence:**
  - `docs/RUNBOOK_wide_live_2026-08-22.md:34` — 「★ 2026-08-30 起三守护已 launchd 化(E-0829-B 修复, 重启+崩溃双自愈; 上行 nohup 命令仅作应急后备)」
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
- **A reader could wrongly conclude:** The daemons are still nohup processes, so kill-by-handle remains the stop and rollback verb.
- **Affects:** live_trading, reporting · **Severity reason:** The fix landed on 08-30, and it changed the combo rollback verb, but the ledger entry still lists it as pending and never records the consequence.
- **Proposed correction (exact text):** ③ 修复项: 已于 2026-08-30 落地(三守护 launchd 化, KeepAlive; RUNBOOK_wide_live L34–36)。**连带后果**: 停止/回滚 combo 不再是 kill 句柄 PID(1 s 内被拉起), 改为 `launchctl bootout gui/$(id -u)/com.hsy.combolive`(持久 + disable; 恢复 enable + bootstrap; 演练收据 OPS_rollback_verb_drill2_20260913T144746Z.log, STATE §1 已更正)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 254->266)

### KB-71 · P3 · VERIFIED_CURRENT
- **Source:** `CLAUDE.md:14`
- **Quote:** 「**N+24:00 读取交易**」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_PROD.md:1` — 「**创建:** 2026-09-13」
  - `STATE.md:144` — 「**N+24:00** 读并交易(`anchor_offset_min=24` / `poll_grace_min=5`, 重试到 N+29:00; 08-27 05:2xZ 起, 本行原写 N+23, 09-16 更正)」
- **A reader could wrongly conclude:** A reader of the partial register re-applies a correction that is already in place, or treats KB-03/KB-11 as still open.
- **Affects:** reporting · **Severity reason:** Recorded so the register does not re-propose an already-applied correction: KB-03 (CLAUDE.md) and KB-11 (STATE.md) proposed N+23 → N+24 and the lead applied both on 2026-09-16, keeping the original wording visible in the parenthetical.
- **Proposed correction (exact text):** (无需改动 —— KB-03 / KB-11 已于 2026-09-16 由 lead 应用, 原字节以「本行原写 N+23, 09-16 更正」形式保留; 受据 AUDIT_PROD PROD-33)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### KB-77 · P3 · DOC_STALE
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:507`
- **Quote:** 「**G-1(整类设计否决)**」
- **Superseding evidence:**
  - `docs/PREREG_combo_chain_residual_attribution_2026-09-13.md:6` — 「G2-C」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:40` — 「G2-C-BIND」
- **A reader could wrongly conclude:** A reader or a grep for 「G-2」 picks up the P2 replay gate `G2-*` results, or a citation of 「G2」 is taken for the new general item; the two families mean entirely different things (a coding rule vs a replay parity gate).
- **Affects:** reporting · **Severity reason:** `G-1` / `G-2` / `G-3` are one hyphen away from the P2 replay-certification gate family `G2-A/B/C/D/E/S` and `G-P2`, which together appear 200+ times across the docs; `G-2` and `G2-B` will be conflated in prose and in grep.
- **Proposed correction (exact text):** [原编号字节保留; 建议, 归 lead] ⚠ **命名建议 KB-77(2026-09-16)**: `G-1 / G-2 / G-3` 与 P2 回放认证的门族 **`G2-A/B/C/D/E/S` 与 `G-P2`** 只差一个连字符, 而后者在 docs 下出现 200+ 次(G2-C 77 · G2-B 37 · G-P2 30 · G2-A 29 · G2-D 17 · G2-C-BIND 15 · G2-E 12 · G2-S 11)。**建议把通用条目改前缀为 `GEN-1 / GEN-2 / GEN-3`**(原号就地保留标 SUPERSEDED-ID, 同 §17.5 规矩), 理由与 `PROD-36b` 后缀那条相同: **编号的可辨识性是引用可解析性的前提**。不是撞号, 是可混淆 —— 但两族语义毫无关系(编码规则 vs 回放平价门), 混淆代价与撞号相同。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 521->507)

## §3 Memory notes (MEMORY.md and linked notes) (205 rows)

Rows from five sub-auditor sweeps: M1/M2 = 当前在役与本期正典, M3 = 硬反馈 + 执行/成本/风控 + 泄漏/口径案卷, M4 = DNR/已关闭轴 + 基建, M5 = 装置/验证纪律. Each sub-auditor opened every note and each superseding receipt; the assembler re-verified all quotes against disk. The six notes the lead named (wide_book_candidate_v2main_norev24, fund_leg_is_the_book, model_leg_leverage_cap_by_seat, regime_driver_is_breadth_not_funding, book_is_dominance_premium, milestone_2026_08_26) are covered here as well.

| id | sev | status | affects | source | claim (abridged) |
|---|---|---|---|---|---|
| M3-35 | P0 | DOC_STALE | live_trading | `memory/review_b0a573a1_closure_and_merge_deploy_protocol_2026_09_09.md:11` | 运行树 = origin/main = **77d9baf**, 电池 **132/132**, safe_commit 门畅通(见 [[disposition_matrix_ruler_recalibration_and_names_truncation_2026_09_12] |
| M1-01 | P1 | DOC_STALE | future_eval, future_retrain | `memory/king_fund_ema_feature_train_v0_serve_v1_2026_09_13.md:22` | do not cite this skew as a cause of live underperformance — the measured effect is below ±0.05 bps/anchor and its point estimate favours the |
| M1-02 | P1 | DOC_STALE | future_retrain, future_eval | `memory/v4_chain_retrain_2026_09_09.md:15` | CALIBER_STATUS 更新: 线上模型腿不需为口径换装 |
| M1-03 | P1 | DOC_STALE | future_retrain | `memory/v4_monthly_chain_driver_2026_09_12.md:15` | (i) STEP1/STEP2 门源码被 ELIGIBILITY_CONTRACT 冻结(278fdce6/db7ab356)且写死九月比对对象 ⇒ 十月需新门源码+复核+合同批准(用户字) |
| M1-04 | P1 | DOC_STALE | future_retrain | `memory/retrain_2026_09_first_run.md:15` | **完整流程正典 = docs/RUNBOOK_monthly_retrain_2026-10.md**(逐字命令+本月基线 0.0548/0.0630/0.0584+splice滚动正典规则+pod_env_bootstrap) |
| M1-05 | P1 | DOC_STALE | future_eval, reporting | `memory/two_good_changes_dont_compose.md:3` | 干净口径下"去rev24∧混V2MAIN"三种子全显著 +0.29~+0.43, 优于任一单项; 先前"不可叠加"是 CAL=exec 口径伪影 |
| M1-06 | P1 | DOC_STALE | live_trading | `memory/leverage_killline_constgross.md:11` | ②宽书可接受 gross 2.0-2.5, 3.5 不可 |
| M1-07 | P1 | DOC_STALE | live_trading, future_eval | `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28` | +5.48 vs +3.66 — the 900s→180s change is already live |
| M2-01 | P1 | DOC_STALE | live_trading, future_eval | `memory/universe_phase_a_m1_deployed_20260904.md:3` | Phase B(M2+M3)最早 09-07 需用户字 |
| M2-08 | P1 | DOC_STALE | future_retrain, reporting | `memory/caliber_review_closure_2026_09_05.md:8` | ⑨ 模型训练窗: king booster `tr = YRA < 2026` ⇒ 2022–2025, 每月重训不学 2026(E-0905-B), 未按 §28 前伸 2020(E-0905-A, 缓存只在 jpline); DL refit 全量至 2026-08-30(末 |
| M2-15 | P1 | DOC_STALE | reporting, live_trading, future_eval | `memory/live_form_health_check_2026_09_05.md:3` | 2024→26 +1.21/+1.25 bps/anchor per gross CI>0 (2× ≈53-55%/yr, maxDD 23%), 2024 and 2025 alone CI include 0; live seat 0.19-0.22 vs device 0. |
| M2-22 | P1 | DOC_STALE | future_retrain, reporting | `memory/dl_monthly_refit_worse_than_yearly_two_seeds_2026_09_05.md:17` | **How to apply:** treat "return DL to the yearly-fold form" as a candidate PREREG (owner: lead/user), not as a deployment; the DL leg is ~0. |
| M2-30 | P1 | DOC_STALE | live_trading, future_retrain | `memory/seat_seed_v3_deployed_2026_09_05.md:3` | 09-05 12:47Z king 席位历史按装置规则播种上线(v3 样本外 king 行替换 917 行, 席位 0.19→0.30); 机制=状态文件末 900 行 msharpe, bundle 行永不进窗; 回滚=备份+kickstart; 换 bundle 时须同法播种 |
| M2-33 | P1 | VERIFIED_CURRENT | live_trading | `memory/live_stop_loss_2026_09_06_resume_and_flowday.md:11` | **★ 缺陷 2(未修, 活风险)**: 当日任一 `daily_nav` 行 `external_flow_usdt ≠ 0` ⇒ 该日记 **UNKNOWN(未定价)**。 |
| M2-40 | P1 | DOC_STALE | future_retrain, live_trading | `memory/allweather_campaign_2026_09_05_verdict.md:9` | **唯一有钱的项:** DL 月度全史重训劣于年折(两种子两窗 CI<0, −0.17~−0.24 bps/锚/gross ≈ 2× −7.5~−10% NAV/年; 机制 = 重训是高噪声抽样(种子间秩相关 0.53)而新数据无边际价值)⇒ PREREG_dl_freeze_y |
| M3-01 | P1 | DOC_STALE | live_trading, future_eval | `memory/k_window_180_live.md:3` | ★★★ 2026-08-10 上线: 挂单等待 900s→180s (commit 40c9e16)。逆向选择确证(未成交单的价格反而更朝我们方向走 +5.48 vs +3.66)⇒ 多等只加大漂移不改善筛选。改善 +0.56~0.69 bps/锚, 最保守漂移模型下下界是【不伤 |
| M3-02 | P1 | DOC_STALE | live_trading, future_eval | `memory/chase_closed_at_39.md:3` | ★★ chase 实验结案于 n=39(用户裁定 2026-08-10): E[H]−E[X] = +6.82−30.55 = −23.73 bps, CI[−48.89,+0.08] 擦 0。★ 判决只对 k=900 成立 —— k 已改 180, 追价变便宜, 不得外推 |
| M3-04 | P1 | DOC_STALE | live_trading, future_eval | `memory/opportunity_gross_is_not_capturable.md:12` | (3) requote/reprice 家族两代双否决(08-05 经济学算式 / 本案模拟), DO-NOT-RETRY; |
| M3-05 | P1 | DOC_STALE | live_trading, future_eval | `memory/slippage_is_a_selection_effect.md:39 (+2 more)` | **冻结未执行**: `PREREG_reject_maker_requote_2026-08-05`(台账 #50, ~0.35 夏普, 零 IC 代价) —— `-5022` 拒绝单以新鲜触价重挂一次 post-only, 失败才落 taker。**不可**把报价挂得更被动: |
| M3-10 | P1 | DOC_STALE | live_trading, reporting | `memory/deepsmooth_band_deployed.md:17` | **How to apply:** (a) 深平滑后一切"信号失效"判断以 ic_monitor 为准, 不看书的换手/仓位反应; |
| M3-18 | P1 | DOC_STALE | live_trading, future_eval | `memory/stop_response_reversible_pricing.md:14` | static 2×: ret +48%/yr, Sharpe 1.14, P(−25% from window start) 7.1%; one-step ladder −10%→half gross (recover −5%): +44%, Sharpe 1.13, P(tri |
| M3-21 | P1 | DOC_STALE | live_trading | `memory/deposit_option_c_ruled.md:3` | 用户裁定方案 C(2026-08-10): 今日入金 @2×, 84 锚为正 ⇒ 升 3× + 停机线 −50% 打包预授权; TRANSFER 不入盈亏使停机线自动重标定 |
| M3-23 | P1 | DOC_STALE | live_trading, future_eval | `memory/stress_campaign_2026_08_19.md:11` | - **尾部预算**: 3.5× 场景按 **−25~−30%** 计(×0.55 线性校准被批评者驳回且成立 — EMA 在因子反转日反而加害); 全七年最坏读数不破 −50% 线 ⇒ 3.5× 硬顶必须与 −50% 停机线打包。 |
| M3-30 | P1 | DOC_STALE | future_eval, reporting | `memory/ic_canon_table.md:19` | **书的正典质量指标 = 净额/锚(+1.68bps)与 Sharpe(2.7-3.0), 不是 IC**; IC 只是分数层诊断。 |
| M3-31 | P1 | DOC_STALE | reporting, future_eval | `memory/feedback_report_live_caliber_full_cycle.md:9` | **How to apply:** 引用前先查 `docs/AUDIT_live_vs_replay_2026-09-04.md` §3 表; |
| M3-34 | P1 | DOC_STALE | live_trading, reporting | `memory/regime_dash_usage.md:7` | 每锚深查模板加一节读 `multi_asset/exports/live/regime_dash/REGIME_DASH.md` 最新行 |
| M3-36 | P1 | DOC_STALE | future_retrain, future_eval | `memory/feedback_no_post_hoc_tricks.md:49` | That phase is mostly done — y_600 architectural exploration is exhausted (V5-LH ×4, multi_scale, pyramid all dead per anti-pattern #11). Now |
| M4-01 | P1 | DOC_STALE | future_retrain, future_eval | `memory/infra_server_jpline.md:8` | **重要 (compact 后必读):** training infrastructure 早已从 RunPod 切换到固定 server。绝对不要再称"pod"或用 RunPod-era 的 `ssh -p PORT -i KEY root@IP` 模式。 |
| M4-02 | P1 | DOC_STALE | live_trading, reporting | `memory/ma_v2_pilot_protocol_hardening.md:63` | **2026-08-20 逐名止损条款 ACTIVE(commit 0bcc089)**: 深度=unrealizedProfit/\|notional\| ≤−25% 连续 2 终锚 ⇒ 该名 flatten_only(maker 出场), 平后 7 天禁入; 其余名照常。机制=复 |
| M4-03 | P1 | OPEN_NOT_MEASURED | future_eval | `memory/ammunition_campaign_night1.md:20` | **腿级补卷(2026-09-01, PREREG e888007fd6ae)**: fund 腿分构造五臂(v2口径/HL1.5d/HL7d/动量微混/surprise微混)书层同座门全 REJECT — **HL3d rank 在腿分书净域也是充分统计**, 两测量域封顶。每 |
| M5-01 | P1 | DOC_STALE | live_trading | `memory/patch_on_disk_is_not_patch_running.md:15` | 重启长驻进程时**完整复制其环境变量**(本次 SHADOW_OFFSET_MIN=16 若丢失会让书每锚 stale 冻结), 且 macOS 无 `setsid`(用 `nohup ... & disown`)。 |
| M5-03 | P1 | DOC_STALE | live_trading | `memory/live_battery_gate_coverage_blind_spot.md:8` | **How to apply**: 给实盘仓加测试的三件套 = 测试文件 + `run_acceptance.sh` SUITES 注册 + `ops/gate_coverage.py` 盲区自述; 电池约 10 分钟; 执行器每锚新进程 ⇒ 提交在下一锚生效; |
| M5-04 | P1 | DOC_STALE | live_trading | `memory/bash_cwd_persists_use_absolute_paths.md:8` | ④ 实盘仓唯一通道 `ops/safe_commit.sh`, 连 docs 也不例外。 |
| M5-10 | P1 | DOC_STALE | future_eval, future_retrain | `memory/onboarding_doc_for_new_researcher.md:3` | docs/ONBOARDING_independent_researcher_2026-09-06.md = 面向独立研究同事的全环节+易错点总览(635 行); 易错点 16 族是主干; 新人问"这个项目怎么回事/哪里容易错"先给这份 |
| MK-01 | P1 | DOC_STALE | future_eval, reporting | `memory/wide_book_candidate_v2main_norev24.md:3` | 当前最佳回放形态(候选, 未部署) = 在役宽书 去掉rev24腿 + king腿45%混入V2MAIN深度模型; 三种子全显著 +0.29~+0.43 bps/锚 |
| MK-02 | P1 | DOC_STALE | live_trading | `memory/wide_book_candidate_v2main_norev24.md:52` | - 回滚 = kill 守护 PID(下一锚自动 king 形态)。切换代价实测 2.4% gross。 |
| MK-03 | P1 | DOC_STALE | live_trading, reporting | `memory/milestone_2026_08_26.md:12` | 回滚=kill combo daemon PID。 |
| MK-04 | P1 | DOC_STALE | future_eval, reporting | `memory/fund_leg_is_the_book.md:3` | 腿消融终审 —— 去 fund 书由 +1.31 变 −1.73(夏普 2.18→−2.49, 4/4年); king 在净额轴擦零但夏普轴显著 |
| MK-05 | P1 | DOC_STALE | future_eval, future_retrain | `memory/model_leg_leverage_cap_by_seat.md:3` | 书里模型腿席位≤0.21(实盘)/0.01(回放2026) ⇒ 模型侧任何改动对书层净额杠杆≤0.21× |
| M1-08 | P2 | DOC_STALE | future_eval | `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28` | requote/reprice family double-vetoed, DO-NOT-RETRY |
| M1-09 | P2 | DOC_STALE | future_eval, reporting | `memory/objective_ammunition_interaction.md:3` | 一切以 CAL=simple + V2=1 的干净装置为准 |
| M1-10 | P2 | OPEN_NOT_MEASURED | future_eval | `memory/king_skill_is_short_side_seat_multiplier_fails_turnover.md:3` | 空侧king席位×κ 在回放逐年全正但在实盘席位(0.21)下换手+15%~+128%破门 ⇒ 轴关闭 |
| M1-11 | P2 | DOC_STALE | future_retrain, future_eval | `memory/clip_compound_label_defect_2026_09_08.md:30` | 以及我方已测的传导上限(分数→权重保留 17.5%, 模型腿席位 ≤0.21), 「修标签换收益」从一开始就是错的期待方向。 |
| M1-12 | P2 | DOC_STALE | reporting, future_eval | `memory/clip_compound_label_defect_2026_09_08.md:36` | 全史 **+0.6474 / S 1.31 / maxDD 41.49% / 最差日 −6.04%** → **+0.6041 / 1.20 / 44.87% / 最差日 −11.21%** |
| M1-13 | P2 | DOC_STALE | reporting | `memory/caliber_program_three_tracks_2026_09_09.md:12` | 风险数字(最差日 −11.17%)不变 |
| M1-14 | P2 | DOC_STALE | reporting, future_retrain | `memory/wide_book_fullhist_oos_2020.md:3` | 2022熊市+0.70/2023+0.33 无亏损年(king是2022-24主引擎, funding是2025-26主引擎); §28 ADOPT_FOR_V2(+0.35夏普) |
| M1-15 | P2 | DOC_STALE | future_eval | `memory/universe_mechanism_frozen_cost_and_fund_rank_base.md:3` | fund 腿归一基对全市场排名 +0.06~+0.09(双种子双口径 CI>0); 推荐三件套 M1/M2/M3 |
| M1-16 | P2 | DOC_STALE | future_eval | `memory/young_listings_carry_fund_alpha.md:3` | 上市<90天的名 fund 腿 IC 是老名 3-4×(2026 +0.086 vs +0.024) |
| M1-17 | P2 | DOC_STALE | future_eval | `memory/live_giveback_root_cause_2026_09_09.md:3` | 机制 = 急涨里资金费动量多头半区跑输指数 + 单名崩(止损日全多头) + FTRIM 只砍信号不砍暴露(半衰期 5 锚, −1.7k); 执行非因 |
| M1-18 | P2 | DOC_STALE | future_eval | `memory/slow_book_alpha_low_dim.md:23` | **任何去集中/去风格/档中性提案引用即拒。** |
| M1-19 | P2 | DOC_STALE | reporting | `memory/universe_crypto_only_caliber_arm_2026_09_08.md:38` | @2× 算术 52.82/54.83 → **56.40/59.05**, CAGR 64.77/68.11 → **70.67/75.23** |
| M1-20 | P2 | DOC_STALE | reporting, future_eval | `memory/reweighting_cannot_close_the_sharpe_gap_2026_09_12.md:28` | 复测 r17–r21(2026-09-12)全部落地后规划数仍 A1x 0.6602 / 1.2857(历史读数非期望), 无新候选晋级。 |
| M1-21 | P2 | DOC_STALE | future_eval | `memory/seat_is_blind_to_the_funding_fuel_gauge_2026_09_12.md:22` | **已知的、未对冲的**弱点(会给正在亏的腿加权)。 |
| M1-22 | P2 | PENDING_USER_DECISION | future_eval | `memory/book_return_not_perceivable_t8_2026_09_13.md:18` | Any added feature or model is a new family (T6 rule). |
| M1-23 | P2 | DOC_STALE | reporting, future_eval | `memory/v4_chain_retrain_2026_09_09.md:12` | 冻结窗 +1.89, Sharpe 3.0, maxDD 820 bps gross |
| M1-24 | P2 | DOC_STALE | future_retrain | `memory/retrain_2026_09_first_run.md:11` | acceptance 4/4(A2 中位 0.9999) |
| M1-25 | P2 | DOC_STALE | future_eval, reporting | `memory/x0910_fund_iv_interval_mismatch_2026_09_13.md:10` | true interval = producer ledger iv (32,595 settlements) else snapped timestamp gap (5,837); ledger vs gap 0 disagreements. |
| M2-02 | P2 | DOC_STALE | live_trading, reporting | `memory/universe_phase_a_m1_deployed_20260904.md:13` | **Why:** 回放 M1 +0.066~+0.077 bps/锚(判官单位, 双种子双口径 CI>0, 尾部不变) |
| M2-04 | P2 | DOC_STALE | live_trading, future_eval | `memory/king_freshness_is_not_book_value.md:10` | (2) 不把更多席位交给 king |
| M2-05 | P2 | DOC_STALE | future_retrain, future_eval | `memory/king_incremental_retrain_undecided_2026_09_06.md:3` | continued boosting (+40 trees/month) vs the live monthly full regrowth K1 |
| M2-09 | P2 | DOC_STALE | future_eval, reporting | `memory/caliber_review_closure_2026_09_05.md:8` | ⑦ carry +1.21 差 = 窗内错配(实盘 09-02 才有 FTRIM +0.73; 回放止损 08-21 已停 ONG +0.44), 非结构性; 装置 carry 公式无错。 |
| M2-10 | P2 | DOC_STALE | future_eval, reporting | `memory/caliber_review_closure_2026_09_05.md:8` | ⑤ combo 复测(16 臂): 排序保住、不显著; 去 rev24 CI>0(+0.10~0.12); V2MAIN 净≈0(降 gross/回撤提 Sharpe); 2025 combo<换装前。 |
| M2-11 | P2 | DOC_STALE | reporting, future_eval | `memory/caliber_review_closure_2026_09_05.md:8` | ④ 在役固定席位形态(pod): 2024 −16.6%/gross, 2025 +8.3%, 2026 +67.9%(8 月年化), 2024→26 +12.6(比值均值)~+14.4%(逐锚比值均值)/gross, Sharpe 1.02, 跨年 maxDD 33% gros |
| M2-12 | P2 | DOC_STALE | reporting, future_eval | `memory/live_seat_seed_is_in_sample.md:3` | E-0904-F/G(终版) — 面板 y4 = Σ 5 分钟简单收益(逐位实证), 是交易所记账的无偏代理; 回放装置 CAL=simple 的 expm1 是伪凸性(king 腿 −2~−3 bps/锚伪拖累); bundle 种子与生产者口径本来正确, 实盘 king 席位 |
| M2-13 | P2 | DOC_STALE | reporting, live_trading | `memory/live_seat_seed_is_in_sample.md:9` | 正确口径终读(pod 仪器): 固定席位 0.21 形态 2024 −16.6%/gross, 2024→26 +12.6%/gross/年(2× ⇒ +25% NAV), Sharpe 1.02, 跨年 maxDD 33% gross(2× ⇒ 66% NAV); 动态席位 + |
| M2-14 | P2 | DOC_STALE | future_eval, reporting | `memory/live_seat_seed_is_in_sample.md:9` | **carry 差:** 实盘书正费率多头权重 0.48 vs 回放 0.43 ⇒ 同锚同费率暴露 2.23 vs 1.04 bps/锚(书构成, 非装置公式)。 |
| M2-16 | P2 | DOC_STALE | future_eval, reporting | `memory/live_form_health_check_2026_09_05.md:10` | Live fees VERIFIED (1.80/4.50 bps, ≈2.0 bps per unit turnover, ≈7 % NAV/yr at 2× at replay turnover 0.08) |
| M2-17 | P2 | DOC_STALE | future_retrain | `memory/live_dl_epoch_rule_is_unconstrained_argmax.md:8` | STATE records it as a candidate needing a clean CONST2027 second seed + ≥14-day forward shadow + the user's word. |
| M2-18 | P2 | DOC_STALE | future_retrain, reporting | `memory/dl_earlystop_replicated_two_seeds_2026_09_06.md:3` | so the second seed's deployment-equivalent confirmation is NOT complete — needs a true CONST2027. |
| M2-19 | P2 | DOC_STALE | future_retrain, reporting | `memory/dl_monthly_earlystop_is_main_cause_2026_09_06.md:3` | best-epoch floor 5 or fixed epoch 7 makes monthly folds ≥ yearly (FIX7 − yearly +0.151 [−0.048, +0.353], − CONST +0.267 CI>0, − seed-per-fol |
| M2-23 | P2 | DOC_STALE | future_retrain | `memory/dl_warmstart_finetune_2026_09_06.md:15` | treat "monthly refit = warm start (+ best-epoch floor, §12)" as the candidate recipe, deployable only after a ≥14-day shadow or second-instr |
| M2-24 | P2 | DOC_STALE | reporting, future_retrain | `memory/dl_recipe_arms_w1f5_p1_p0_all_fail_2026_09_06.md:13` | 本轮唯一过门的是 FLOOR5/FIX7(§12 + 种子 2027 复验: +0.243 [+0.066,+0.420] / +0.299 [+0.071,+0.523]) |
| M2-26 | P2 | DOC_STALE | future_retrain | `memory/live_model_legs_stopped_learning_end_2025.md:10` | That reopens "do recent labels add value" from *known-useless* to **untested with positive preliminary evidence** |
| M2-27 | P2 | DOC_STALE | future_retrain | `memory/f10_one_bar_window_and_dl_monthly_2026_09_05.md:9` | 月龄 IC 平坦 ⇒ DL 无月度重训价值, 保持年度(09-01 件)。 |
| M2-31 | P2 | DOC_STALE | future_eval | `memory/requote_randomised_experiment_live_2026_09_05.md:9` | 装置 = exec_requote_behind_2026-09-05/analyse_requote_behind.py 口径按 `requote_arm` 分臂(exempt 剔除) |
| M2-34 | P2 | DOC_STALE | future_eval, reporting | `memory/caliber_env_flag_trap.md:8` | 2026-08-25/26。w8/w10 回放的 `CAL`: "simple"=交易所简单收益(expm1), 其它任意值=对数。我连续 24h 传 **`CAL=exec`**(误记为"执行器口径"开关 —— 那是 w3 时代的语义), 脚本不报错, 13 个臂全落对数口径, |
| M2-35 | P2 | DOC_STALE | reporting, live_trading | `memory/giveback_baserate_replay_2026_09_06.md:3` | ≈6.5 days/yr ≤ −2.68%, 1–2 days/yr ≤ −4% (all 2025-04/05), worst 3-anchor −6.5…−7.1%, worst month −17% |
| M2-36 | P2 | DOC_STALE | reporting, live_trading | `memory/giveback_baserate_and_tail_levers_2026_09_06.md:3` | ≤−2.68% 日 ≈6.5/年, ≤−4% 1–2/年, 最差 3–6 锚窗 −6.5~−7.6% |
| M2-37 | P2 | DOC_STALE | future_eval, reporting | `memory/giveback_baserate_replay_2026_09_06.md:10` | anchor-level big losses are mostly the known "book is structurally short the alt premium" squeeze |
| M2-38 | P2 | DOC_STALE | reporting, live_trading | `memory/live_giveback_is_long_extreme_funding_blowups_2026_09_06.md:3` | execution ≈ 0.15 bps/anchor is not a cause |
| M2-41 | P2 | DOC_STALE | future_eval, reporting | `memory/allweather_campaign_2026_09_05_verdict.md:8` | 目标不可达且能量化: 2024/2025 单年 Sharpe 1.24/1.14, 中位季度 1.1 |
| M2-43 | P2 | DOC_STALE | future_eval | `memory/carry_sleeve_second_premium_diagnostic_2026_09_05.md:20` | carry sleeve 的决定量是换仓规则(滞回可降换手但未评估, 是新臂) |
| M2-44 | P2 | DOC_STALE | live_trading, reporting | `memory/funding_transfer_priced_in_settlement_window.md:10` | FTRIM(全 4h 排除, +0.21) |
| M3-03 | P2 | DOC_STALE | live_trading, reporting | `memory/two_rulings_deployed_20260810.md:3` | ②chase 政策A全不追(ARM_WEIGHTS chase=0)。 |
| M3-06 | P2 | DOC_STALE | future_eval, reporting | `memory/maker_slippage_is_negative.md:15` | **加上手续费后挂单的合计成本是 −0.254 bps —— 近乎免费, 甚至倒赚。** |
| M3-07 | P2 | OPEN_NOT_MEASURED | future_eval, future_retrain | `memory/turnover_cost_reaudit_2026_08_21.md:3` | all-in cost per unit INTENDED turnover 3.52 bps [0.32,6.64] = cash −1.28 (maker fee +1.75, rounding edge −2.03, top-up +0.14, reject drift − |
| M3-08 | P2 | DOC_STALE | live_trading, future_eval | `memory/execution_joint_curve_programme.md:11 (+1 more)` | 1. 挂单深度 — **已在学**: placement bandit 三臂实盘随机化(join 3703/behind 2081/exempt 550, ε=0.35), 每单带 `placement_arm` 标签。 2. 等待/追单 — **已在价**: chase 随机实 |
| M3-09 | P2 | DOC_STALE | future_eval, live_trading | `memory/capacity_two_calibers.md:15` | - **路线**: T1=9-10 入金150k(爬坡+逐档实测) → T2=300k(帽+回撤阶梯+流动性排序flatten 三前置) → T3=500k(T2曲线裁定)。 |
| M3-11 | P2 | DOC_STALE | future_eval | `memory/adaptive_turnover_family_closed.md:13` | 在役 (α=.05, b=.002, target) = 联合最优 —— argmax(.02,.002) Δ+0.099 CI[−.026,+.235] 噪声内; |
| M3-14 | P2 | DOC_STALE | future_eval, live_trading | `memory/vol_predictable_but_acting_loses.md:10` | ②P2动态gross必须非对称条件式, 通用vol-target已判负 ③在役RB形式正确无需升级。 |
| M3-15 | P2 | DOC_STALE | future_eval | `memory/engine_replay_is_not_the_live_book.md:3` | ★★★ 引擎正典回放与在役 legs.py 差两处结构(归一 + 风险预算) ⇒ 至今全部离线权重/腿决定测在一本不是实盘那本的书上 |
| M3-16 | P2 | DOC_STALE | live_trading, future_eval | `memory/book_has_implicit_stop.md:10` | **① 在役逐名止损书级通过**: 净额代价仅 −2.8%, 夏普 +0.02, 尾部 +4%, 逐年=从好年向磨损年转移(2024 +28%)。回放触发173/年 vs 实盘18/年(10×)⇒ 真实代价更小。 |
| M3-17 | P2 | DOC_STALE | live_trading, future_eval | `memory/graduated_stop_ooS_refuted.md:3` | 渐进/更深止损 OOS 判负 DO-NOT-RETRY; 在役-25%止损≈免费保险已在最优点; |
| M3-20 | P2 | DOC_STALE | live_trading, future_eval | `memory/drawdown_ladder_refuted_combo25.md:13` | **How to apply**: 2.5× 裁定=入金后重议, 本质是用户风险偏好(接受 ~1/3 年窗距峰 −25% 水下); |
| M3-22 | P2 | DOC_STALE | reporting, future_eval | `memory/deposit_leverage_assessment.md:33` | VIP 降费是入金的真实收益(每降 0.6 成本 ≈ +0.1 bps/锚) |
| M3-24 | P2 | OPEN_NOT_MEASURED | future_eval, live_trading | `memory/premium_sleeve_budget_refuted_fomc_drift.md:10` | Verdict: 可预注册上线候选 with conditions — restore form, stop-dilution listed separately and not counted, expectation +0.08~0.10 bps/anchor (+170–2 |
| M3-25 | P2 | OPEN_NOT_MEASURED | future_eval, reporting | `memory/shortside_beta_is_paid_premium.md:13` | **但全史 β 项 = +4,682 bps = 总利润 34%**(2022/2025/2026 下跌段大赚, 2023/24 上涨年小亏), 空头侧全史 +19,485 vs 多头侧 −5,705。 |
| M3-26 | P2 | DOC_STALE | live_trading, future_eval | `memory/funding_bucket_net_alpha.md:20` | **书级实验终判(2026-08-30, PREREG d580eb2042ef)**: 三臂无一过CI门 ⇒ DNR; A3(剔≤−10bp)近失(+0.08bps/锚双种子一致, CI含零); |
| M3-27 | P2 | DOC_STALE | future_retrain, future_eval | `memory/funding_settlement_interval_unit_bug.md:11` | The live splice reproduces the **AS-TRAINED (un-normalised)** caliber *deliberately* (`funding_derive.py:110`), because the frozen king/s2 h |
| M3-28 | P2 | DOC_STALE | future_eval | `memory/venue_feasibility_hyperliquid.md:31` | funding 腿别指望在 HL 复用 —— 但也别为此焦虑, [[ma_v2_factor_state_2026_07_08]] 之后的实测显示该腿 canonical 口径下全历史独立为负 (avg −1.34, 5 年 4 年负) |
| M3-32 | P2 | DOC_STALE | reporting | `memory/feedback_reference_window_must_match_regime.md:15` | (本项目里 `RESULT_live_form_health_check` §2 截至 08-10, `RESULT_giveback_baserate` §1 有 08-30 的同源行) |
| M3-33 | P2 | DOC_STALE | reporting | `memory/feedback_units_chain_and_caliber_binding.md:10` | (1) 汇报里的每个 %/NAV 数字只能从脚本(如 pod_units_table.py)复制, 并写出链: bps/锚 → ÷gross_total → ×2190/100 → ×杠杆; |
| M3-37 | P2 | DOC_STALE | future_eval | `memory/feedback_check_exhausted_first.md:11` | 1. `grep "明确不做\\|exhausted\\|null 路径" CLAUDE.md` — 看 "Current Priority" 章节 |
| M3-44 | P2 | DOC_STALE | live_trading | `memory/feedback_no_book_level_response_to_instrument_doubt.md:12` | ② 全书级响应(平仓/停机)必须过**比例门**(涉及名义占 gross 份额 + 名数; R-14 冻结 2%/5 名)并在 DESIGN 写出「假阳性最大代价」; |
| M4-04 | P2 | DOC_STALE | future_eval, reporting | `memory/ma_v2_wide_universe_revival.md:19` | **★ SURPRISE INVERSION: funding_ema does NOT revive on wide** (z+1.7, sign FLIPS per-fold) — the opposite of its 14-mega-cap strength (z−2.5 |
| M4-05 | P2 | OPEN_NOT_MEASURED | future_eval, reporting | `memory/ma_v2_wide_universe_revival.md:28` | **宇宙刷新A/B(2026-09-01 §B, double-check修正版)**: 全窗U1/U2负系**U0回套生存者偏差**(2026手选名单套历史; 分年Δ: 后见年−0.38/−0.37, 无后见2026=+0.03±0.17中性)。可靠结论=**前瞻加宽≈alph |
| M4-06 | P2 | DOC_STALE | future_eval, reporting | `memory/mapping_4arm_live_config_optimal.md:3` | ★★★ DO-NOT-RETRY: 仓位映射 2×2(α∈{.5,1}×λ∈{0,1})用实盘 compose_book 在 9821 锚上判 —— 在役 α=.5 λ=1 净额双档最优, 三候选全 FAIL |
| M4-07 | P2 | DOC_STALE | reporting, future_eval | `memory/king_cadence_8h_live.md:3` | ★★★ 2026-08-09 上线: king 腿 4h→8h 相位00/08/16Z (commit 1cfbf0c)。调仓仍 4h。 |
| M4-09 | P2 | DOC_STALE | reporting, future_eval | `memory/wide_book_carry_correction.md:15` | ① 任何宽书夏普引用 ≥2026-08-16 版本必须是 carry 修正后的(2.42/2.18 全史), 旧 3.4x 作废留档 |
| M4-11 | P2 | DOC_STALE | reporting, live_trading | `memory/pilot_journal_pointer.md:3` | Authoritative per-day journal for the live pilot lives in exports/live/pilot_journal/ — read the latest day's file before answering any 'wha |
| M4-15 | P2 | DOC_STALE | future_retrain, future_eval | `memory/champion_baseline_repro.md:3` | ★正典基线复现配方(2026-08-08 定盘) — 冠军配置完整命令+面板SHA+噪声标定; 一切升级从此出发 |
| M4-16 | P2 | DOC_STALE | future_eval | `memory/breadth_gate_zero_recruitment.md:3` | ★★ Commoditised price-volume factors do NOT constitute breadth: 14 revival factors → 8 survive orthogonality → collapse to 2 independent clu |
| M4-17 | P2 | DOC_STALE | future_eval | `memory/breadth_commoditised_factors_zero_admissions.md:3` | The 14 revived price-volume factors give ZERO admissions to the book: gate 3 kills 6, the 8 survivors collapse to only 2 independent cluster |
| M4-22 | P2 | OPEN_NOT_MEASURED | future_retrain, future_eval | `memory/target_span_single_peak_24h.md:23` | ⇒ **DO-NOT-RETRY: target-span search is closed.** Only 12h/36h remain untested and the peak is flat, so expected gain is negligible. Anythin |
| M4-27 | P2 | DOC_STALE | reporting, future_eval | `memory/wide_book_final_form_verdict.md:11` | **签名数: 全史(2024-26)3.2-3.4, 扣当日~20变体DSR税后 2.5-3.0, 实盘预期 1.8-2.4 = 在役 1.3-1.6 倍** |
| M4-28 | P2 | DOC_STALE | future_eval, reporting | `memory/ma_v2_funding_ema_GO.md:3` | funding_ema is the FIRST net-cost-tradeable multi-asset factor (1h L/S break-even 18.8 bps/side, all 5 factory gates PASS, latency-flat) |
| M4-29 | P2 | DOC_STALE | future_eval | `memory/ma_v2_maker_execution_reframe.md:16` | **★ 结论 (保守 headline = k=60)**: M0 有效成本/side ≈ **0** (2023 +0.05 / 2024 −0.07 / 2025 +0.17), **« taker 1.7 约 8-30×**。 |
| M4-32 | P2 | DOC_STALE | future_eval | `memory/book_family_retired_five_forms.md:31` | **⇒ book 族退役升级为无条件**(收益 5 形态 / 波动 / 频带 / **成交概率** 四类目标全数判负)。 |
| M4-33 | P2 | DOC_STALE | future_retrain, future_eval | `memory/raw_target_rejected_2026_08_04.md:22 (+1 more)` | - **Residual-label training is necessary** — the doc's §7.1-C hypothesis ("train on raw, neutralize   after, avoid the noisy residual label" |
| M4-34 | P2 | DOC_STALE | future_eval | `memory/breadth_round2_basis_orthogonalised.md:45` | 本条的"三关全过"只对 08-09 的对数/引擎口径成立 |
| M4-35 | P2 | OPEN_NOT_MEASURED | future_eval | `memory/orthogonal_mining_round1.md:20` | **挖矿第一夜终账: 3 候选 0 录取**; 书残差方法论保留, 首矿死于 S1。 |
| M4-37 | P2 | DOC_STALE | future_eval | `memory/dl_ceiling_solo_rho_catch22.md:24` | **残差(钱)口径平手**(树 0.0364·58% vs DL 0.0372·60%, "树保留率<60%"押注证伪)。⇒ 5m 残差 alpha ~0.036 是**模型无关量** |
| M4-38 | P2 | DOC_STALE | future_eval | `memory/direction1_tabular_gap.md:10` | **三方等价定理(钱口径)**: 面板 248 特征 + resid 目标下, resid-LGBM 0.0483 / 序列 king 0.0486 / 满配深表格(PLR+集成+时序调制+可微森林) 0.0467 — **三种模型类等价(±0.002), 约束是信息**。 |
| M4-39 | P2 | DOC_STALE | future_retrain, future_eval | `memory/direction1_tabular_gap.md:16` | ① K4 一体化关闭: 表格塔无法贡献超树部件; 深塔在工程特征上永远排 GBDT 之后。 |
| M4-43 | P2 | DOC_STALE | future_retrain, future_eval | `memory/benchmark_0466_was_dirty_panel.md:29` | - **干净基线 = 0.0475 resid / 0.067 raw**(冠军配置, 0731 等价面板, 年折, 双种子)。 |
| M4-47 | P2 | DOC_STALE | reporting | `memory/dl_quant_live_repo_path.md:21 (+1 more)` | `~/dl_quant_live` before concluding data loss. Do not create anything the scheduler must read under `~/Desktop`. |
| M4-53 | P2 | DOC_STALE | future_eval, future_retrain | `memory/project_principles.md:7` | **Where to find them:** `docs/PROJECT_PRINCIPLES.md` is the authoritative doc. |
| M5-02 | P2 | DOC_STALE | reporting | `memory/live_battery_gate_coverage_blind_spot.md:7` | 跑 `run_acceptance.sh` 全电池(123 套件, 解释器钉 /usr/bin/python3 3.9) |
| M5-05 | P2 | DOC_STALE | future_eval, reporting | `memory/replay_seat_path_is_not_live_seat_path.md:10` | **事实(2026-09-02)**: w10 hardened 回放 2026 年 msharpe 席位 king≈0.01/fund 0.99; 实盘同规则同 900 锚回看给 king 0.21/fund 0.79(掩码后)。规则相同, 差在 king 腿收益序列: 回放用 |
| M5-06 | P2 | DOC_STALE | reporting, future_eval | `memory/two_instruments_disagree_reconcile_first.md:11` | 修正后: **Δnet +0.19~0.22(CI 排零)、逐年八数全正、Δ夏普 +0.351 CI[+0.107,+0.592] 显著 ⇒ 可上线候选**。 |
| M5-07 | P2 | DOC_STALE | reporting | `memory/sigma_caliber_must_match_pnl.md:11` | 用执行器口径回放序列自身的波动(sd 22.69 bps/锚 ⇒ 日 sd 125U @NAV15k/1.5×)重算: **z=−2.51σ, 经验频率 0.84% 的 3 日窗**(2024 起) —— 坏但不异常。 |
| M5-08 | P2 | DOC_STALE | live_trading, reporting | `memory/error_ledger_practice.md:11` | 节律: \|单锚\|>2σ(≈78U)事件触发 24h 入账; |
| M5-09 | P2 | DOC_STALE | reporting, live_trading | `memory/team_protocol_and_state.md:13` | the single MUTABLE snapshot: live config, in-flight tasks *with named owners*, frozen-do-not-touch list, registered defects, and the caliber |
| M5-11 | P2 | DOC_STALE | future_retrain, future_eval | `memory/replication_must_replicate_same_contrast.md:12` | but CONSTspl27's monthly folds come from **seed-42** training (no true `mE1c_s2027` exists) ⇒ the second seed's deployment-equivalent confir |
| MK-06 | P2 | OPEN_NOT_MEASURED | future_eval, reporting | `memory/regime_driver_is_breadth_not_funding.md:3` | regime 真因=宇宙广度非funding水平(2026-08-28 实测): 月广度corr+0.56/宽档+2.97bps vs 窄档−2.00; funding水平corr反号−0.48; 当前双指标有利区 |
| KB-61 | P3 | DOC_STALE | future_retrain, reporting | `memory/export_gate_v2_falsifiability_closure_2026_09_12.md:3` | PROPOSED2 contract 01692565 (NOT APPLIED, user ruling pending) |
| M1-26 | P3 | OPEN_NOT_MEASURED | reporting, future_eval | `memory/september_losses_replay_also_lost_t5c_2026_09_13.md:3` | deployed carry was understated by 0.25 |
| M1-27 | P3 | DOC_STALE | reporting | `memory/t1_edge_diagnosis_2026_09_13.md:15` | deployed book carries 2.19x the replay book on the same 30 anchors 08-26..08-30, cause not traced |
| M1-28 | P3 | DOC_STALE | future_eval | `memory/t1_edge_diagnosis_2026_09_13.md:17` | H5: 2022-23 low-dispersion mechanism only half supported |
| M1-29 | P3 | DOC_STALE | reporting, future_eval | `memory/deployed_carry_gap_is_ftrim_warmstart_stop_t5_2026_09_13.md:3` | replay-only stop layer 18.5% |
| M1-30 | P3 | DOC_STALE | live_trading, reporting | `memory/stopped_longs_pinned_by_reshape_clamp_2026_09_13.md:3` | Live per_name_stop cannot flatten stopped LONG positions |
| M1-31 | P3 | DOC_STALE | live_trading | `memory/t5b_ftrim_residual_and_live_stop_audit_2026_09_13.md:15` | the executor stop exists but its exit for longs is impeded |
| M1-32 | P3 | DOC_STALE | reporting, future_eval | `memory/wide_book_needs_stop_layer.md:3` | 宽书零风控层; 止损在宽书降 maxDD 31-36%(在役书仅13.5%), 换装前必须移植 |
| M1-33 | P3 | DOC_STALE | reporting | `memory/income_ledger_dedupe_twin_rows_e0909h_2026_09_09.md:13` | 修复在 `review/b0a573a1-executor` 分支(未部署) |
| M1-34 | P3 | DOC_STALE | live_trading | `memory/venue_quant_rules_lock_e0910a_2026_09_10.md:15` | (2) 候选(需预注册+用户字): 执行器识别 -4400 后本阶段停发剩余开仓单 + HIGH 页含 plannedRecoverTime; 复场重建分两锚建仓 |
| M1-35 | P3 | DOC_STALE | live_trading | `memory/live_executor_transport_resilience_2026_09_09.md:24` | **候选修复 = 规划期按 symbolConfig 有限上限截断目标, 改变发单 ⇒ 需用户字**(STATE §3) |
| M1-36 | P3 | OPEN_NOT_MEASURED | future_eval | `memory/funding_alpha_is_state_variable_not_factor_proxy.md:8` | 书层 fund 腿贡献保留 71~91%(2026 78%) |
| M1-37 | P3 | DOC_STALE | future_eval | `memory/carry_net_fund_leg_sizing_t2_2026_09_13.md:3` | σ-state arm tripped the 0.165 ceiling and failed §7 (LEAK-SUSPECT, cause unresolved) |
| M2-03 | P3 | DOC_STALE | future_retrain, reporting | `memory/king_freshness_is_not_book_value.md:3` | 滚动季度 OOS king(2026-09-04): rank-IC 0.06→0.09 但 msharpe 书夏普 3.12→2.78(Δ −0.17~−0.20 CI<0, 双种子), 换手 +20% |
| M2-06 | P3 | DOC_STALE | future_retrain | `memory/king_incremental_refit_continue_undecided_2026_09_06.md:17` | 与 DL 侧 [[dl_monthly_refit_worse_than_yearly_two_seeds_2026_09_05]] §11(每月换模型 = 换初始化)同一族问题但答案相反方向: DL 缺的是初始化稳定, 树缺的不是。 |
| M2-07 | P3 | DOC_STALE | future_retrain, future_eval | `memory/second_instrument_rebuild_2026_09_05.md:8` | 打乱未来零检验 3/15 格超 2σ(零值 ≤0.010, 对称) ⇒ 冻结规则下重建 king 未录取; 10 种子诊断待 |
| M2-20 | P3 | DOC_STALE | reporting | `memory/dl_monthly_earlystop_is_the_cause_2026_09_06.md:15` | Effect vs yearly is +0.05..+0.15 bps/anchor/gross (≈ +2..+7 NAV %/yr @2×), same order as device resolution, so "parity with yearly" is the s |
| M2-21 | P3 | DOC_STALE | reporting, future_eval | `memory/dl_monthly_earlystop_is_the_cause_2026_09_06.md:11` | Levels frozen: yearly 1.557, R0 (seed per fold) 1.386, CONST 1.442, FLOOR5 1.610 (Sharpe 2.69, maxDD 870), FIX7 1.708 (S 2.87, maxDD 832) |
| M2-25 | P3 | DOC_STALE | future_retrain, reporting | `memory/full_gradient_window_buys_nothing_2026_09_07.md:3` | so neither "new data helps" nor "more training helps" survives. |
| M2-28 | P3 | DOC_STALE | future_retrain | `memory/f10_one_bar_window_and_dl_monthly_2026_09_05.md:8` | king 标签对齐候选 |
| M2-29 | P3 | DOC_STALE | future_eval | `memory/v2main_objective_arms_dro_l1ss_fail_2026_09_05.md:13` | the DL leg enters as φ 0.45 of a model leg that sits on the msharpe seat w_king ≈ 0.65 ⇒ book effect ≤ 0.29× leg effect |
| M2-32 | P3 | DOC_STALE | live_trading, reporting | `memory/alarm_text_is_not_alarm_source.md:7` | 生成代码 `scheduler/anchor_loop.py` L1549-1557 把 `_clamp` 三类(持仓不在目标=退出 / 目标<2×min_notional / 止损 flatten·冷却)一律写成该文案 |
| M2-39 | P3 | DOC_STALE | future_eval | `memory/live_giveback_is_long_extreme_funding_blowups_2026_09_06.md:12` | the one untested lever is a per-name vol-aware cap (PREREG_tail_aware_sizing_2026-09-06) |
| M2-42 | P3 | DOC_STALE | reporting | `memory/allweather_trackC_age_tilt_voltarget_refuted_2026_09_05.md:15` | 最差年 Sharpe 极值 1.70(φ.65 s2027)/1.69(B5)/1.60(U-FROZEN 前视), 在役 1.14/1.30, 无一 ≥2 |
| M2-45 | P3 | VERIFIED_CURRENT | live_trading | `memory/producer_is_launchd_managed_restart_verb.md:3` | 宽书生产者 shadow_loop_v3 由 launchd 代理 com.hsy.shadowloop(KeepAlive, env SHADOW_OFFSET_MIN=16, stdout→loop.out)托管; kill PID 即重生(PID 会变); 重启动词 = l |
| M3-12 | P3 | DOC_STALE | reporting | `memory/turnover_shaping_ema_revalidated.md:3` | 最优可采格 = harvest EMA α=0.3(被 T1 关掉的那个): 净 +0.378→+0.668, 夏普 +0.58→+1.09, 五年全正。恢复需用户重裁 T1 张力 |
| M3-13 | P3 | DOC_STALE | reporting | `memory/deposit_kills_implicit_band.md:17` | 提案 PROPOSAL_neutral_band_2026-08-10(8e499dac)待用户裁定; 时序上须在 84 锚窗口起点之前部署(窗口内书变更⇒重起)。 |
| M3-19 | P3 | DOC_STALE | live_trading | `memory/stop_line_read_a_different_quantity.md:8` | — still open (A2), needs the user's ruling on the baseline semantics (start equity after deposits / transfer rebase). |
| M3-29 | P3 | DOC_STALE | reporting | `memory/rank_centring_group_scale_trap.md:15` | Impact once fixed: funding leg went from net +0.72%/yr (solo Sharpe 0.07) to **+8.48%/yr (Sharpe 0.83)** — *weakly positive, not a winner*. |
| M3-38 | P3 | DOC_STALE | reporting | `memory/feedback_anchor_inspection_once.md:7` | 复核轮 cron(91c4defe, `23 1,5,9,13,17,21`)已于 09-02 删除, 主模板 cron(3af9cb0e)保留。 |
| M3-39 | P3 | DOC_STALE | future_retrain | `memory/feedback_no_side_gpu_jobs.md:10` | on the single jpline 3090, run NO side GPU jobs while a queue run is training. |
| M3-40 | P3 | DOC_STALE | live_trading | `memory/probe_flattened_book_positions.md:12` | **v2 started 2026-08-22 00:52Z** (launchd `com.hsy.execprobe2`, ~/exec_probe/v2: own-fills-only flatten, exclusion set 467 = live 140 ∪ wide |
| M3-41 | P3 | DOC_STALE | reporting | `memory/dirty_caliber_effects_reverse_when_clean.md:81` | **★ Open, and it is on the deployment path: does the clean model's stronger beta tilt get PAID?** |
| M3-42 | P3 | DOC_STALE | reporting | `memory/anchors_jsonl_is_not_a_clean_series.md:3` | state/pilot_log/*/anchors.jsonl mixes real scheduled anchors with off-schedule manual and test runs, and its anchor_ts is a completion time  |
| M3-43 | P3 | DOC_STALE | reporting | `memory/turnover_caliber_raw_vs_deployed.md:22` | **How to apply:** 报 Sharpe 用原口径无妨; 只要一句话涉及**绝对成交额**, 必须换成 1453/1659。 |
| M3-45 | P3 | DOC_STALE | future_eval, reporting | `memory/panel_lookahead_betaadj_ret24.md:28` | **Rulings:** the line is FROZEN with comment+assertion (a well-meaning causal fix must go red); only safe fix is retraining; live deployment |
| M3-46 | P3 | DOC_STALE | future_eval, future_retrain | `memory/feedback_no_multi_seed_2026_05_15.md:50` | - **Above ±0.01 → cross-fold evidence decides** (no seed reruns needed). |
| M4-08 | P3 | DOC_STALE | future_eval | `memory/cadence_8h_clears_cost_line.md:3` | king cadence 4h→8h makes EVERY k clear the cost line (gap −30% to −96%) for ~10% book IC — so the 43.5%-IC sacrifice of dropping to k=0.2 is |
| M4-10 | P3 | DOC_STALE | reporting | `memory/two_book_allocation_w2.md:14` | **Status:** 传闻级 (series single-source); direction "blend > wide swap > in-role" holds; |
| M4-12 | P3 | DOC_STALE | reporting | `memory/pilot_prereq_stack.md:95` | 任何 pilot 相关读数只能来自 `pilot_metrics.py` (改脚本=改协议; 当前 hash `e2f10848…`, 签署后冻结) |
| M4-13 | P3 | DOC_STALE | reporting | `memory/shadow_three_tracks_prereg.md:11` | **2026-07-25 (0B)。** `engine/live/` 下三条轨并行, 都是**加法 + run_daily.sh 非致命步骤**, 失败不影响 champion 主链。 |
| M4-14 | P3 | DOC_STALE | reporting | `memory/research_branch_protocol.md:16 (+2 more)` | 1. **No git worktree.** It isolates local repo files — the least likely thing to collide. What    actually collides is outside the repo: `~/ |
| M4-18 | P3 | DOC_STALE | future_eval | `memory/takerflow_family_zero_admissions.md:31` | **凡是抬毛额的改动都靠抬换手, 在这个信噪比下换手总是吃得更多。** |
| M4-19 | P3 | DOC_STALE | reporting | `memory/new_info_campaign_round1_2026_08_11.md:11` | **但 S2 净额剂量反向判死**(w.05 −0.010 / w.10 −0.033)。 |
| M4-20 | P3 | DOC_STALE | future_eval | `memory/tree_dl_division_of_labor.md:21` | ① king 在役配置不动(其价值=IC 住在慢稳成分, 可变现——这是定性结论+1.46 夏普受据) |
| M4-21 | P3 | DOC_STALE | future_retrain | `memory/regime_stability_is_horizon_property.md:28` | 在役部署头 = YR4(harness 硬断言 `h0 must stay YR4`)。 |
| M4-23 | P3 | DOC_STALE | reporting | `memory/sharpe_461_does_not_survive_clean.md:40` | **And the same number is the incumbent's own grade.** Live runs that dirty generation, so 0.93/−0.43 |
| M4-24 | P3 | DOC_STALE | reporting | `memory/sharpe5_has_no_clean_precedent.md:37` | **It does NOT argue against the model swap.** Live runs *that same dirty generation* |
| M4-25 | P3 | DOC_STALE | future_eval | `memory/hybrid_forest_admission.md:13` | **证据链**(可复现, 脚本 jpline w3lane/jp_hybrid.py + 特征缓存 hyb_fea47.npy) |
| M4-26 | P3 | DOC_STALE | reporting | `memory/metric_discipline_spearman_primary.md:13` | - CLAUDE.md "Metric Discipline" section mirrors it. |
| M4-30 | P3 | DOC_STALE | future_retrain, reporting | `memory/MEMORY.md:108` | - V4/V5/单资产时代(04..05): `v4_*` `v5*` `single_asset_*` `y600_*`; 结论已入 07-06 终版文档 |
| M4-31 | P3 | DOC_STALE | reporting | `memory/MEMORY.md:104` | [残差第四腿关](wide_book_carry_correction.md) |
| M4-36 | P3 | DOC_STALE | future_eval | `memory/dl_ceiling_solo_rho_catch22.md:18` | ③ 15 臂判官与预测件在 pod /workspace(exports_train/arm*_pred_*.npy), 装置与结论同寿命 |
| M4-40 | P3 | DOC_STALE | future_eval, reporting | `memory/residual_regime_survival_peaks_at_y12.md:40 (+1 more)` | **为什么重要**: 实盘坏掉的量**就是残差在坏窗里的增值**(STATE §0-octies: 残差全期 +0.091 / 最近 6 锚 −0.008, 而风格 +0.085 还活着)。**在役目标 y4 恰好是残差最脆的那个视界。** |
| M4-41 | P3 | DOC_STALE | future_eval | `memory/substratum_noise_needs_own_calibration.md:35` | 视界表(y12 vs y4 = +0.0060, 8.6 SE)不受影响。 |
| M4-42 | P3 | DOC_STALE | future_retrain | `memory/lam_orth_dose_response_flattened_horizon.md:33` | JSON 产物只记录 xattn 与 n_params, **不记录 lam_orth 与面板路径** ⇒ 必须回查启动脚本。 |
| M4-44 | P3 | VERIFIED_CURRENT | future_eval | `memory/benchmark_0466_was_dirty_panel.md:36` | engine/panel_source.py 默认 PANEL=wide_dl_full.npz(脏面板) |
| M4-45 | P3 | VERIFIED_CURRENT | future_eval | `memory/ma_v2_1h_ls_nogo.md:19` | **Implication:** escalating to 2h/4h with the SAME fast features won't help (mechanism #3) — the horizon isn't the bottleneck, feature decay |
| M4-46 | P3 | VERIFIED_CURRENT | reporting | `memory/infra_research_repo_on_icloud_desktop_trustctime.md:10` | **Fix applied (lead, 2026-09-13 08:50Z):** `git config --local core.trustctime false` in the research repo; the same commit then took 3.7 s. |
| M4-48 | P3 | DOC_STALE | future_eval | `memory/server_only_code_rsync_delete_risk.md:30` | - 已把 tarball 拉到**机外**(本地), 两侧 sha256 一致 ⇒ 两台机器两份。 |
| M4-49 | P3 | DOC_STALE | future_retrain | `memory/panel_ref_blind_to_ch31_axis.md:39` | fix = trainer writes the SHA at training time (`prodfold_panel_sha_at_train_time`). |
| M4-50 | P3 | DOC_STALE | future_eval | `memory/vs_infer_handrolled_forward_loop.md:19 (+1 more)` | The s2 leg carries ~80% of the book at k=0.2 — > the configuration the "clean book is net-positive" headline rests on. |
| M4-51 | P3 | DOC_STALE | future_retrain | `memory/perf_batch_1024_lr_sqrt.md:15` | VRAM at batch 1024 ≈ 15.7 GB of 24 GB (65%) with this architecture — still headroom, but a bump to 2048 would need a check. |
| M4-52 | P3 | DOC_STALE | future_retrain | `memory/feedback_verify_cudnn_not_just_cuda.md:22` | V5 push 训练在 jpline server (RTX 3090, 24GB) 上 1 epoch 41 min, 但 V5 production 同样硬件 3-5 min. 调查发现: |
| M5-12 | P3 | DOC_STALE | future_eval | `memory/judge_ci_depends_on_arm_set.md:11` | (1) 引用某个 CI 时, 连"那次判官运行有哪些臂"一起引; 跨运行比 CI 边界无效, 只能比点估计。(2) 新写判官一律**每个比较各自** `default_rng(SEED, spawn_key=(i,))` 或按比较名派生子流, 使 CI 对臂集不变。 |
| M5-13 | P3 | DOC_STALE | future_eval | `memory/correlational_count_vs_interventional_check.md:70 (+1 more)` | satisfies `σŷ = r · σy`, so **a correctly calibrated model with IC ≈ 0.046 should produce σŷ/σy ≈ 0.046** — measured 0.063 is *slightly over |
| M5-14 | P3 | DOC_STALE | live_trading | `memory/my_own_instruments_fail_at_the_extremes.md:37` | 复发堵漏=探针轮首清扫 probe* 遗留挂单(08-19 已上线)。 |
| M5-15 | P3 | DOC_STALE | future_eval, reporting | `memory/noninferiority_rule_is_not_noninferiority_proof.md:12` | ① Any "不劣 / 持平 / 追平 / not worse than" conclusion must be written as **CI lower > −δ**, printing δ and the lower bound together. |
| M5-16 | P3 | DOC_STALE | future_eval | `memory/alignment_gate_must_not_carry_book_property_prior.md:8` | The NET condition failed at +0.051 / +0.043, because the prior came from a different book, return source and universe. |
| MK-07 | P3 | DOC_STALE | reporting, future_eval | `memory/book_is_dominance_premium.md:3` | 该暴露≈书收益78%(截面alpha仅0.29bps/锚 夏普0.59); 对冲它=毁收益(h=1β夏普0.59) |

### M3-35 · P0 · DOC_STALE
- **Source:** `memory/review_b0a573a1_closure_and_merge_deploy_protocol_2026_09_09.md:11`
- **Resolution:** APPLIED by lead, CORRECTLY: the note carries the 2026-09-13 annotation (running tree ef60f85, R-13 no-rollback) and the original 「运行树 = 77d9baf」 bytes are deliberately retained per the 'original bytes stay' convention. An assembler label of 'applied-but-quote-still-present' is the expected state for an in-place annotation, not a failure. ⚠ **口径(KB-73)**: 本行引用的「逐套件 N/M」只在同一解释器下可比 —— 电池 `run_acceptance.sh:28` 的 `PY="${ACCEPT_PY:-/usr/bin/python3}"` 是**可被环境变量覆盖的默认值**, 认证它的断言只对源码做子串检查, 且 `state/acceptance/` 38,177 份工件中 0 份记录解释器版本; 2026-07-27 前两入口一钉一裸, 裸 `python3` 制造过两个假红。引用计数时须写明解释器。
- **Quote:** 「运行树 = origin/main = **77d9baf**, 电池 **132/132**, safe_commit 门畅通(见 [[disposition_matrix_ruler_recalibration_and_names_truncation_2026_09_12]]); 52 行写回(RUNBOOK §4)另裁; 回滚 = §5 revert 链(禁 reset/force)。」
- **Superseding evidence:**
  - `STATE.md:7` — 「⇒ **运行树电池 ACCEPTANCE: ALL GREEN 135/135(130 套件 + 5 审计门, tests_env_loading 14/14)** ⇒ 提交 **`ef60f85`** 并推送(origin/main = ef60f85)」
  - `STATE.md:56` — 「✅ 用户裁定 R-13 = A「肯定是彻底修复, 回滚的版本有其他问题」**: 不回滚 d040c74;」
  - `STATE.md:4` — 「✅ 复场首锚(12Z)验收通过** —— rid A1789302239 / ef60f85」
- **A reader could wrongly conclude:** In an incident, a reader follows the stale rollback (revert chain to pre-b681ca5) in ~/dl_quant_live and reintroduces the false-positive whole-book flatten and other defects fixed by W6ab/W2/W1/W9. Or the reader reports the wrong deployed commit.
- **Affects:** live_trading · **Severity reason:** In a section marked "latest, read first", the note gives the running tree as 77d9baf and a b681ca5-era revert chain as the rollback procedure. Applied to today's ef60f85 tree during an incident, that procedure would revert executor code under running anchors and bring back the fixed E-0912-A defects. The user has ruled fix-forward, not rollback.
- **Proposed correction (exact text):** [在第一个「状态」段之前插入] **状态 2026-09-13 12:0xZ(最新, 先读这段; 覆盖以下两段)**: 运行树 = origin/main = **ef60f85**(918559f + W6ab 259f50a6 → W2 2ad1c272 → W1 62a3032e → W9 f8beb082, 一次 safe_commit, 电池 ALL GREEN 135/135), 12Z 复场首锚验收通过(STATE.md 顶部)。下文 77d9baf/132 与「回滚 = §5 revert 链」均已过时: 用户 R-13 裁定「彻底修复, 不回滚」(09-12), 回滚会带回 E-0912-A 等已修缺陷; 事故处置按 feedback_no_book_level_response_to_instrument_doubt, 恢复只由用户手动。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied in place: original bytes retained by convention (exact)

### M1-01 · P1 · DOC_STALE
- **Source:** `memory/king_fund_ema_feature_train_v0_serve_v1_2026_09_13.md:22`
- **Resolution:** SOFTENED to the K2 vocabulary: T4's verdict is INCONCLUSIVE (significance gate, no pre-frozen equivalence band), not NOT MATERIAL; the note must not be corrected into a second settled claim in the opposite direction. XREF AUDIT_PROD PROD-04 / PROD-37 · AUDIT_TRAIN TRN-04 / TRN-05 — CROSS-REF: the column-80 train-v0 / serve-v1 split is owned by AUDIT_PROD PROD-04 (king) and PROD-37 (V2MAIN), with the October recurrence owned by AUDIT_TRAIN TRN-04 / TRN-05. This row's own finding is the LABEL (NOT MATERIAL from a significance gate) — kept, softened to the K2 vocabulary.
- **Quote:** 「do not cite this skew as a cause of live underperformance — the measured effect is below ±0.05 bps/anchor and its point estimate favours the as-served v1.」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带，不能推广为两代部署 booster 全部窗口都无材料性影响」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:16` — 「**+0.0181 [−0.0299, +0.0625]**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:19` — 「| 分辨率(CI95 半宽) | 书层 ±0.046 / ±0.049 bps/锚; ΔIC ±0.00017 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:90` — 「它不说在役 king 在实盘里没有吃亏, 实盘窗的差值见 §6。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:43` — 「W_ALPHA 基线复现: C0_s42 g +0.6342」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:39` — 「| K2 | 评估 | 「NOT MATERIAL」类标签只由显著性门生成, 无经济等价带 | 复审 R4 §4.3 | FX-EVAL |」
- **A reader could wrongly conclude:** A reader concludes the col-80 v0/v1 skew is proven economically immaterial (< ±0.05 bps/anchor) for the live book, while CI upper bounds +0.0625/+0.0645 bps/anchor (~10% of A0 W_ALPHA g 0.634) are not excluded, the verdict is replay-only and V2MAIN's historical effect is NOT MEASURED.
- **Affects:** future_eval, future_retrain · **Severity reason:** The How-to-apply turns a significance-only NOT MATERIAL label into a stated effect bound and tells readers not to treat an unfixed live train/serve skew as a cause, which can deprioritise the producer/bundle fix and bias live-vs-replay attribution.
- **Proposed correction (exact text):** Replace the first sentence of How to apply with: "Do not cite this skew as a proven cause of live underperformance, and do not cite it as proven immaterial either: T4's NOT MATERIAL is a significance-only label (CI excludes 0) with no economic-equivalence band (REV4 §4.3 L136; FIXPROGRAM K2). ±0.046/±0.049 bps/anchor is the CI half-width, not an effect bound; gaps up to +0.0625/+0.0645 bps/anchor (~10% of A0 W_ALPHA g 0.634) are not excluded. The verdict covers the research-replay king only (T4 RESULT L87: it does not say the live king did not lose) and V2MAIN's historical effect is NOT MEASURED (T4b). The split is still unfixed in production (FIXPROGRAM P1/P2)." In the description replace "T4: NOT MATERIAL at ±0.05 bps/anchor" with "T4: NOT MATERIAL by a significance-only rule; CI upper +0.063/+0.065 bps/anchor not excluded".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 3->22)

### M1-02 · P1 · DOC_STALE
- **Source:** `memory/v4_chain_retrain_2026_09_09.md:15`
- **Resolution:** XREF AUDIT_PROD PROD-01..PROD-06 · AUDIT_TRAIN TRN-04 / TRN-05 — CROSS-REF: 'the live model legs need no caliber swap' is bounded by the AUDIT_PROD train/serve parity family (PROD-01 clock, PROD-02 rank cross-section, PROD-03 Spearman 0.935, PROD-06 V2MAIN member universe).
- **Quote:** 「CALIBER_STATUS 更新: 线上模型腿不需为口径换装」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:23` — 「**回放 king 与实盘 king 在 4h/1h 名上确实不是同一个分数**」
  - `STATE.md:5` — 「生产者 king/V2MAIN 第 80 列训练 v0/服务 v1 未修; 面板 qv4h 与生产者定义差中位 |Δlog| 0.52 且全部 78+171 个模型特征从未逐列做训练/服务平价」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:48` — 「king 训练特征以 float16 存储(`pod_fea_ext.py` L66), 服务端 78 列为 float32 —— 精度层训练/服务差, 影响待测」
  - `docs/CALIBER_STATUS_2026-09-09.md:40` — 「与在役形态书层十格对照全 (C)(动态 +0.01~+0.08 bps/锚/gross, 固定 ±0.01, CI 全含 0)⇒ 线上模型腿在正确口径下**不需要**为口径原因换装」
- **A reader could wrongly conclude:** A reader concludes the in-service king/V2MAIN legs are caliber-correct as served; in fact col 80 is trained v0 but served v1 (4h names 2×, 1h 8×), 78+171 features were never parity-checked column-wise, and king training features are float16 vs float32 served.
- **Affects:** future_retrain, future_eval · **Severity reason:** The ruling rests on a replay-vs-replay A1−A0 comparison (both v0-scored) but is quoted as 'live model legs need no caliber change', while the served legs use a different col-80 unit and no per-column train/serve parity exists; it can block or deprioritise an export/retrain fix.
- **Proposed correction (exact text):** CALIBER_STATUS 更新: 线上模型腿不需为口径换装 ⚠(2026-09-13 限定: 该裁定只来自回放书对回放书的 A1−A0 (C), 回放 A0 的 king 为 v0 打分; 实盘 king/V2MAIN 第 80 列训练 v0/服务 v1(4h 名 2×、1h 名 8×; T1 H2b/T4/T4b), 其余 76+169 个模型特征从未逐列做训练/服务平价, king 训练特征 float16 vs 服务 float32(FIXPROGRAM P1/P2/P4/P10, STATE.md 2026-09-13 12:4xZ 审计派工条)⇒ 不能读作「线上模型腿与训练口径一致、无需修」; T4 的 NOT MATERIAL 仅为显著性标签, T4b 历史书层 NOT MEASURED)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-03 · P1 · DOC_STALE
- **Source:** `memory/v4_monthly_chain_driver_2026_09_12.md:15`
- **Resolution:** XREF AUDIT_TRAIN TRN-26 / TRN-27 — CROSS-REF: the October approval objects (STEP1_m 79950786…, STEP2_m d99a9109…) and the runbook's stale 0fe5ec55 / b2f9cfd4 are owned by AUDIT_TRAIN TRN-26 and TRN-27. EVIDENCE UPDATED 2026-09-16: the superseding quote 「v4_gate_step2_m.py 0fe5ec55…」 is no longer in `v4_month_2026-10.env.template` — line 50 now names 79950786… / d99a9109… and cites AUDIT_TRAIN TRN-27, i.e. the template side is FIXED UPSTREAM. The proposed correction still applies to the memory note, which has not been updated.
- **Quote:** 「(i) STEP1/STEP2 门源码被 ELIGIBILITY_CONTRACT 冻结(278fdce6/db7ab356)且写死九月比对对象 ⇒ 十月需新门源码+复核+合同批准(用户字)」
- **Superseding evidence:**
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:61` — 「十月数据门源码已就位, **待研究员复核 + 用户字批准入合同**」
  - `STATE.md:13` — 「新 STEP2_m 批准对象 d99a9109(十月合同批准仍待用户字)」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:98` — 「不能继续批准旧 `b2f9cfd4` 或模板注释里的 `0fe5ec55`」
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/v4_month_2026-10.env.template:50` — 「v4_gate_step2_m.py 0fe5ec55…」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:37` — 「十月链真实业务段从未跑通」
- **A reader could wrongly conclude:** A reader believes October gate source still has to be written, or approves template-comment STEP2 0fe5ec55 (or older b2f9cfd4) instead of the current approval objects STEP1 79950786… / STEP2 d99a9109….
- **Affects:** future_retrain · **Severity reason:** The open item predates the October gates and names no approval object; the next sha a reader meets (template comment 0fe5ec55) is the superseded one, so following the note risks approving the wrong STEP2 gate into the eligibility contract.
- **Proposed correction (exact text):** (i) ⚠ 已更新(2026-09-12 W7 → 09-13 X3 + 独立复审第四轮 §3): 十月门源码已就位(RUNBOOK_2026-10 §0★ 修订 4/5); 待用户字批准入合同的对象是 STEP1 `v4_gate_step1_m.py` 79950786… 与 STEP2 d99a9109…(X3 后版本); **不得批准旧 b2f9cfd4 或 `v4_month_2026-10.env.template` L50 注释里的 0fe5ec55**; 批准前合同正确拒绝新门; mwf/refit/arms/judge/export 真实业务段仍从未跑通(FIXPROGRAM R2)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-04 · P1 · DOC_STALE
- **Source:** `memory/retrain_2026_09_first_run.md:15`
- **Quote:** 「**完整流程正典 = docs/RUNBOOK_monthly_retrain_2026-10.md**(逐字命令+本月基线 0.0548/0.0630/0.0584+splice滚动正典规则+pod_env_bootstrap)」
- **Superseding evidence:**
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:3` — 「§0★ 唯一执行步骤单 = v4 口径; §2–§4 降为历史; 用户字 09-12」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:9` — 「**十月重训只允许经驱动执行**」
  - `STATE.md:60` — 「① 十月 RUNBOOK §0★ 不可照抄」
- **A reader could wrongly conclude:** A reader runs the October retrain by copying the RUNBOOK §2–§4 v3 commands/baselines instead of the v4 §0★ driver, reintroducing _ext caches, unconstrained argmax epochs and missing-env guard failures.
- **Affects:** future_retrain · **Severity reason:** The note's 'canonical full procedure' points at verbatim v3 commands and baselines that the RUNBOOK itself demoted to history on 09-12; copying them reproduces the R1–R5 defects (bare refit defaults, argmax epoch, missing env).
- **Proposed correction (exact text):** **完整流程正典 = docs/RUNBOOK_monthly_retrain_2026-10.md §0★ 唯一执行步骤单(v4 口径), 只经 `chain_v4_monthly.sh <v4_month_YYYY-MM.env>` 驱动执行、先跑 dryrun 负控**(修订 3; 用户字 09-12); 本条记录的 v3 逐字命令、本月基线 0.0548/0.0630/0.0584 与 RUNBOOK §2–§4 已降为历史, 不得照抄。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-05 · P1 · DOC_STALE
- **Source:** `memory/two_good_changes_dont_compose.md:3`
- **Quote:** 「干净口径下"去rev24∧混V2MAIN"三种子全显著 +0.29~+0.43, 优于任一单项; 先前"不可叠加"是 CAL=exec 口径伪影」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The significance claimed on 08-26 does not survive at seed 42**」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:44` — 「The 08-26 reading ("log is the artifact, simple is correct") had the direction backwards」
  - `docs/REVIEW_caliber_final_2026-09-04.md:482` — 「排序保住, 显著性不保, 归因反转(去 rev24 CI>0, V2MAIN≈0), 2025 反转」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「The August selection that produced A0 (leg ablation, φ, FTRIM, seat rule) is **not** in the family」
- **A reader could wrongly conclude:** A reader treats the live combo form as significantly better on all three seeds and credits the gain to the V2MAIN blend, when under correct calibers the only CI-excluding-0 delta is dropping rev24 given V2MAIN, seed-42 significance is gone and 2025 is negative.
- **Affects:** future_eval, reporting · **Severity reason:** The description still headlines the CAL=simple result as clean-caliber evidence for the live combo form although the correct-caliber re-measurement exists and removes seed-42 significance, reverses the attribution and flips 2025; the ⚠ banner only says 'pending re-validation'.
- **Proposed correction (exact text):** 描述行替换为: "⚠ E-0904-F 复验已出(combo_recheck 2026-09-04, CAL=log 与复利记账双正确口径): 组合形态排序保住(D 仍为四形态最强), 但 08-26 的显著性不保(s42 D−A 2024→26 +0.108 [−0.101,+0.312] log / +0.203 [−0.022,+0.439] 复利; 仅 s2027 复利排零), 归因反转(只混 V2MAIN ≈0; 唯一排零的是「有 V2MAIN 时去 rev24」D−C +0.103 [+0.006,+0.201] / +0.124 [+0.016,+0.238]), 2025 年反转(D−A −0.137 log / −0.079 复利); 原 CAL=simple 三种子 +0.29~+0.43★ 与「先前判负是 CAL=exec 伪影」读法作废(复验指 08-26 把口径方向读反)。A0 的 8 月选型(去腿/φ/FTRIM/席位)不在 T6 家族内, 选择膨胀未测。方法论规则不变: 组合必须单独测"; 正文 L11–15 前加一句「以下为 CAL=simple 历史数, 已被描述行复验取代」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-06 · P1 · DOC_STALE
- **Source:** `memory/leverage_killline_constgross.md:11`
- **Quote:** 「②宽书可接受 gross 2.0-2.5, 3.5 不可」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:94` — 「| 2.50 | 1.0 | −52.0 % (−52.6 %) | −7.99 % | 9 (11) | 47 (50) | 1.97 (2.40) | 41.7 % (42.0 %) |」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:171` — 「`constant_leverage_2.00` 自 2026-09-03 在役, 是按**冻结窗的 2.9357** 设的; 诚实夏普是 **1.2912**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」
- **A reader could wrongly conclude:** A reader treats raising gross from 2.0× to 2.5× as inside an accepted risk band or quotes ~11% probability of a −25% drawdown at 2.0×, while the v4 replay gives P(1y true maxDD ≥25%) 26.8%/33.1% at 2.0× and 41.7%/42.0% at 2.5×, with 5–6 vs 9–11 historical halts.
- **Affects:** live_trading · **Severity reason:** The standing guidance that 2.0–2.5× gross is acceptable (2.0× touches −25% 10.8%/24%) is an 08-21 single-instrument reading superseded by the v4 r18 ladder, and would mislead a leverage change.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本条 08-21 的「宽+止损 gross2.0 触线 10.8%/24%」与「宽书可接受 gross 2.0-2.5」已被 r18(2026-09-12, v4 口径, 修暖机/真 maxDD, 固定杠杆复利 NAV)取代: 2.0× 全史 maxDD −43.9%/−44.5%、停机(≤−4% 日)5/6 次(1.09/1.31 次/年)、P(1 年真 maxDD ≥25%) 26.8%/33.1%; 2.5× maxDD −52.0%/−52.6%、停机 9/11 次(1.97/2.40 次/年)、P 41.7%/42.0%。不得再用本条数字论证杠杆; 在役 constant_leverage_2.00 是按冻结窗夏普 2.9357 设定的, 诚实全周期夏普 1.2912(CLOSEOUT §7); 杠杆改动 = 用户裁定。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 3->11)

### M1-07 · P1 · DOC_STALE
- **Source:** `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28`
- **Resolution:** XREF AUDIT_EXEC CFG-03 — CROSS-REF: the 900 s fact is owned by AUDIT_EXEC CFG-03; this row is the citation inside the passive-reversal note.
- **Quote:** 「+5.48 vs +3.66 — the 900s→180s change is already live」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:43` — 「"k_seconds": 900,」
  - `/Users/haosiyu/dl_quant_live/config/book.json:121` — 「★★ 回滚 180→900, 2026-08-10 02:5xZ, 在任何锚点于 180 下运行【之前】。」
  - `/Users/haosiyu/dl_quant_live/scheduler/run_anchor.py:339` — 「k = cfg.get("k_seconds", 900)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:95` — 「在役 `config/book.json`(sha `f6fd6d0e…`): k_seconds **900**」
- **A reader could wrongly conclude:** A reader believes the live maker window is 180 s and that the unfilled-intent adverse selection has already been mitigated by shortening it, so no k-window work is needed; the live config is k_seconds 900.
- **Affects:** live_trading, future_eval · **Severity reason:** The lead reading states a live execution parameter (180 s maker window) that was rolled back to 900 s before any anchor ran at 180, and uses it to argue the adverse-selection effect is already handled in production.
- **Proposed correction (exact text):** Replace "(08-10: unfilled orders moved further our way, +5.48 vs +3.66 — the 900s→180s change is already live)" with "(08-10: unfilled orders moved further our way, +5.48 vs +3.66; the 900s→180s change was ROLLED BACK to 900 s on 2026-08-10 02:5xZ before any anchor ran at 180 because the simulation's maker slippage was wrong; live config is k_seconds 900 — config/book.json L43/L121, T3 RESULT T-A1)".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-01 · P1 · DOC_STALE
- **Source:** `memory/universe_phase_a_m1_deployed_20260904.md:3`
- **Quote:** 「Phase B(M2+M3)最早 09-07 需用户字」
- **Superseding evidence:**
  - `STATE.md:111` — 「⑤ FTRIM/M1/T400 噪声内; T3c 负; 阶梯双向作废(惰性); M2/M3 不得上线」
  - `docs/ERROR_LEDGER_2026-08-20.md:416` — 「宇宙 M1 的 +0.06~+0.09(已上线, 复验中)」
- **A reader could wrongly conclude:** A reader asks the user to approve Phase B (per-anchor universe rule + 7-day age gate) as if its evidence were current, although the universe campaign that recommended it ran on the pseudo-convex CAL=simple device and was never re-measured on the unbiased/v4 caliber.
- **Affects:** live_trading, future_eval · **Severity reason:** The description presents Phase B (M2+M3) as a candidate awaiting only the user's word, while the 09-05 caliber closure says M2/M3 must not go live; following it would put a universe book-behaviour change to the user on CAL=simple-era evidence.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): Phase B(M2+M3)不是「待用户字」的候选 —— 09-05 口径终审收口已写「M2/M3 不得上线」(STATE.md L109 ⑤)。其受据 RESULT_universe_dyn_2026-09-04 跑在 CAL=simple(E-0904-F)装置上, 本审计未找到在无偏/v4 口径下的复测收据。重开须先按 CALIBER_PIN_v4 重做预注册与判官, 再谈用户字。
- **Confidence:** VERIFIED (quote+receipt opened: STATE.md L108, ERROR_LEDGER L398); 'M2/M3 never re-measured on unbiased/v4' is INFERRED from a grep of docs dated 09-05..09-13 (only PREREG_live_form_health_check L10 mentions M2/M3, as 未部署); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-08 · P1 · DOC_STALE
- **Source:** `memory/caliber_review_closure_2026_09_05.md:8`
- **Quote:** 「⑨ 模型训练窗: king booster `tr = YRA < 2026` ⇒ 2022–2025, 每月重训不学 2026(E-0905-B), 未按 §28 前伸 2020(E-0905-A, 缓存只在 jpline); DL refit 全量至 2026-08-30(末 15% 早停)。」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:517` — 「- **我的原话(两处, 均作废)**: E-0905-B「DL(F10 refit)则确为**全量至 2026-08-30 20Z**(`pod_f10_refit_ext.py` **L89-90**, 末 15% 时段早停验证; 产物 trained_through 1788120000)」; `ONBOARDING_independent_researcher_2026-09-06` §5.2「全史至 2026-08-30, 末 15% 时段早停验证」。」
  - `docs/ERROR_LEDGER_2026-08-20.md:524` — 「- **结构性推论(此前无人写下)**: king 训练 `tr = YRA < 2026`(E-0905-B)止于 2025-12; DL 梯度亦止于 ≈2025-12 ⇒ **在役书两条模型腿都在 2025 年底停止学习**, 2026 全年(含最强的 regime)没有进入任何梯度。」
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/pod_f10_refit_v4.py:104` — 「cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]」
  - `docs/RESULT_second_instrument_rebuild_2026-09-05.md:64` — 「**全部含 0, 幅度 ≤0.04 bps/锚**; hist F2/log 2024 = −0.641 S−1.70 DD1789 vs pinned −0.642 S−1.68 DD1815 ⇒ 2020 起训练不改变 2024 亏损年。E-0905-A 结案为"非实质"。」
- **A reader could wrongly conclude:** A reader believes the live DL leg already learned the 2026 regime and misjudges model staleness when deciding on retraining or when attributing live underperformance.
- **Affects:** future_retrain, reporting · **Severity reason:** Says the live DL refit trained through 2026-08-30, but its gradients stop around 2025-12 (the last 15% is a time-ordered validation slice). Both model legs have therefore never learned any 2026 data, and the October v4 refit keeps the same 85% cut.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, E-0907-D): 「DL refit 全量至 2026-08-30」作废 —— `pod_f10_refit_ext.py` L90 `cut=int(len(tr_idx)*0.85)` 使末 15% 为时间序验证切片, 梯度止于 ≈2025-12-01(`trained_through` 记的是含验证段的索引末端, 差 252 天; ERROR_LEDGER L495–503)⇒ 在役两条模型腿(king `YRA<2026` 同)都未学过 2026。十月 v4 refit(`pod_f10_refit_v4.py` L104)仍是 85% 切分, FIX7 只改选 epoch。E-0905-A(未前伸 2020)已结案「非实质」(RESULT_second_instrument_rebuild L64)。description 的「DL 训至 T−1」同改。
- **Confidence:** VERIFIED (quote+receipt opened; October refit script line read) · **Quote re-verified at assembly:** exact

### M2-15 · P1 · DOC_STALE
- **Source:** `memory/live_form_health_check_2026_09_05.md:3`
- **Quote:** 「2024→26 +1.21/+1.25 bps/anchor per gross CI>0 (2× ≈53-55%/yr, maxDD 23%), 2024 and 2025 alone CI include 0; live seat 0.19-0.22 vs device 0.33 because the producer's king-leg rows are ≈half the pinned-king rows」
- **Superseding evidence:**
  - `docs/CALIBER_STATUS_2026-09-09.md:32` — 「2. **在 v4 上重发一张参考表**: 两种子、全周期逐年、负年份显式、尾部标"下界"、2026 F10 腿标旗; 取代 ADDENDUM 4/6 与健康体检的引用地位。」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:29` — 「5. **探索性日块自举 Sharpe CI95**(研究员新增, 2000 次, UTC 日块, 保留日内依赖不保留跨日; rng [20260905,k]): 原钉 W_ALPHA **[0.3207, 2.2822]**(SE 0.4890)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「3. **回撤尺子**: 表中 maxDD 是累计 g 的算术峰谷差(单位 gross), ×2 只是线性近似; 按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**; W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%。」
  - `docs/CALIBER_STATUS_2026-09-09.md:26` — 「- 尾部: **一律是下界**(全史最差日 −6.04% → −11.17%, maxDD 41.5% → 44.8%; 最差月 −17%、≤−4% 日 1–2/年 同此)。」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:27` — 「- 回放装置在实盘数据上**方向被验证**(逐锚 ρ **+0.83** [+0.710,+0.899]), 但**幅度是压缩的**: 斜率 0.835 [0.707,0.963], 四组检验的斜率 CI 上界**全部 <1** ⇒ 回放系统性**高估幅度 15–27%**。」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
- **A reader could wrongly conclude:** A reader sizes leverage or risk limits from 'maxDD 23%, +53%/yr at 2×', understating drawdown roughly two-fold, and reads the live king seat as ≈0.2 (so today's 0.38 looks abnormal).
- **Affects:** reporting, live_trading, future_eval · **Severity reason:** The headline planning numbers (≈53-55%/yr at 2×, maxDD 23%) come from a pre-v4 device on a 2024→26 window that leaves out the 2023 loss year, with lower-bound tails. CALIBER_STATUS moves the citation role to the v4 table (full-cycle Sharpe 1.29, compounded W_ALPHA NAV maxDD −42%), and replay overstates live magnitude by 15-27%; the leverage/risk rulings depend on these numbers.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): these levels are the pre-v4 health-check device on the 2024→26 window and are no longer the citation of record (docs/CALIBER_STATUS_2026-09-09.md L32: the v4 reference table replaces the health check). Quote the v4 A0 per-year table instead (uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md): full window 2022-06..2026-08 Sharpe 1.29 (day-block CI95 [0.32, 2.28]); 2023 −1.94, 2024 +1.09, 2025 +1.19, 2026 +4.53; compounded fixed-2× NAV maxDD W_ALPHA −42.12% (2023 alone −28.92%); tails are lower bounds (E-0908-B). Live realises about 0.835× the replay magnitude (CLOSEOUT L24). The 'live seat 0.19-0.22 vs device 0.33' gap was closed by the 09-05 seat seeding (0.1878 → 0.2999, STATE.md L161); the masked king seat was 0.382 on 09-13 12Z.
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-22 · P1 · DOC_STALE
- **Source:** `memory/dl_monthly_refit_worse_than_yearly_two_seeds_2026_09_05.md:17`
- **Quote:** 「**How to apply:** treat "return DL to the yearly-fold form" as a candidate PREREG (owner: lead/user), not as a deployment; the DL leg is ~0.3 of the book (φ 0.45 × model seat ~0.65) so the −0.17..−0.24 bps/anchor/gross (≈ −7..−10 NAV %/yr @2×) is already book-level.」
- **Superseding evidence:**
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:556` — 「1. **冻结读法 = (A) 早停是主因, 两个窗口都成立**(VERIFIED 表 AD3-3)。」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:562` — 「(A) ⇒ 冻结候选 `PREREG_dl_freeze_yearly_2026-09-05.md` 撤回, 改立"月度重训 + best-epoch 规则修正"候选」
  - `docs/PREREG_deploy_dl_recipe_2026-10.md:6` — 「**更正一处早前措辞**: 我曾把方案 B 写成「A(下限 5)+ 热启动」, 但复验过的热启动臂 **W1/W2 用的是逐字原早停规则(argmax), 不带下限**; 带下限的组合臂 W1F5 只有种子 42 且对两个单项都不加分(−0.034 / +0.072, CI 均含 0)。**⇒ 方案 B 的正确形态 = 只加热启动, 早停规则一字不改。**」
  - `docs/RULINGS_requested_2026-09-12.md:14` — 「| R-8 | **十月重训**(G3) | §0★ 修订 2: 三处代码改动完成前不得开始; W3 在做」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
- **A reader could wrongly conclude:** A reader proposes freezing DL at the yearly form (PREREG_dl_freeze_yearly) for the October retrain, or overstates how much a DL recipe change moves the live book.
- **Affects:** future_retrain, reporting · **Severity reason:** The 'return DL to yearly folds' candidate was withdrawn under the prereg once §12 found early stopping to be the main cause; current candidates are an epoch-rule fix (FIX7/FLOOR5) or warm start (方案 B). 'DL leg ~0.3 of the book' uses the replay device seat; the live V2MAIN weight is about 0.45 × 0.382 ≈ 0.17.
- **Proposed correction (exact text):** ⚠ Superseded (2026-09-13 audit): the candidate 'return DL to the yearly-fold form' (PREREG_dl_freeze_yearly_2026-09-05) was withdrawn per prereg after §12's reading (A), 'early stopping is the main cause' (docs/RESULT_dl_monthly_gate_2026-09-05.md L556/L562). Current recipe candidates are monthly refit plus an epoch-rule fix (FIX7/FLOOR5; FIX7 is in RUNBOOK_monthly_retrain_2026-10 step 4b) or warm start only (PREREG_deploy_dl_recipe_2026-10 方案 B); the October choice is pending ruling R-8. 'The DL leg is ~0.3 of the book' uses the replay device seat (~0.65). The live masked king seat was 0.382 on 09-13 12Z, so V2MAIN ≈ 0.45 × 0.382 ≈ 0.17 of the live book (REGIME_DASH L16).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-30 · P1 · DOC_STALE
- **Source:** `memory/seat_seed_v3_deployed_2026_09_05.md:3`
- **Quote:** 「09-05 12:47Z king 席位历史按装置规则播种上线(v3 样本外 king 行替换 917 行, 席位 0.19→0.30); 机制=状态文件末 900 行 msharpe, bundle 行永不进窗; 回滚=备份+kickstart; 换 bundle 时须同法播种」
- **Superseding evidence:**
  - `STATE.md:163` — 「**16Z 锚验收(巡检)**: 掩码 king ∈ [0.28, 0.32], combo_stage 五层安全通过, 执行器/readback 正常, sidecar 自平价 PASS, FTRIM/M1 PASS; 任一不成立 ⇒ 回滚(备份文件 + kickstart)。**关闭「线上 0.19 vs 装置 0.33」的缝; 此后席位随实盘行滚动; 下次换 bundle 时须按同法播种(否则新模型样本外行永不进窗)。**」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:43` — 「| 09-05 12:47Z | 在役席位的 king 腿收益历史 917 行由 v3 样本外(v0 打分)行播种, 此后追加行是 v1 打分 | STATE.md L146 | 转引(未测) |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4b/RESULT_T4b_v2main_feature_skew_2026-09-13.md:30` — 「**09-05 席位播种对 V2MAIN 链: 在席位权重与目标文件层 MEASURED(描述), 盈亏 NOT MEASURED。** 席位历史里仍有 876 行播种行(04-05 00Z .. 08-30 20Z), 它们是 v0 打分的 king 腿收益。把这 876 行换成同 booster、第 80 列 = v1 的重算值后: 掩码 king 席位 = V2MAIN 分数在 fc 链里的系数, 从 0.3695(中位)**+0.0078**(+0.0072…+0.0089);」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:213` — 「③ 换装步骤禁止删除/重置 `state/leg_returns_live.json`」
- **A reader could wrongly conclude:** A reader uses the note's rollback to revert a seat problem and silently rewinds the producer's seat history by 48 anchors, re-seating the obsolete 08-16 king rows; or re-seeds at the October swap without accounting for the v0/v1 scoring mix.
- **Affects:** live_trading, future_retrain · **Severity reason:** The rollback 'restore the .pre_seatseed_v3_20260905 backup + kickstart' was valid only for the 09-05 16Z acceptance window. Today the live state file's fund/rev24 columns equal the backup shifted by 48 rows, so restoring it would drop 8 days of live leg rows and put the pre-v3 king rows (the 0.19 seat artefact) back into the seat window.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 「回滚=备份+kickstart」只适用于 09-05 16Z 首锚验收窗(STATE.md L161)。截至 09-13 状态文件已追加 48 行实盘行(fund/rev24 列 = 备份平移 48 行; king 列已播种), 恢复 `.pre_seatseed_v3_20260905` 会丢掉 8 天实盘腿行并把 08-16 旧 booster 行放回席位窗 —— 禁止照做; 今后的席位回滚对象须按当日状态重新生成并先预注册。另: 播种行是 v0 特征打分、此后追加行是 v1 打分(uplift_r2 T4 RESULT L40), 把 876 行播种行按 v1 重打分使掩码 king +0.0078(T4b RESULT L30); 「同法播种」须声明该耦合。RUNBOOK_monthly_retrain_2026-10 未含播种步骤(仅 L187 禁止删除/重置状态文件), 十月换 bundle 前须补。
- **Confidence:** VERIFIED (quote+receipt opened; read-only comparison on 09-13 ~14:3xZ: ~/wide_shadow/state/leg_returns_live.json fund/rev24 columns equal .pre_seatseed_v3_20260905 shifted by 48 rows, king column matches at no shift); 'RUNBOOK/driver lacks the seeding step' INFERRED from grep of RUNBOOK_monthly_retrain_2026-10.md and v4_chain_2026-09-09/chain_v4_monthly.sh; STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-33 · P1 · VERIFIED_CURRENT
- **Source:** `memory/live_stop_loss_2026_09_06_resume_and_flowday.md:11`
- **Quote:** 「**★ 缺陷 2(未修, 活风险)**: 当日任一 `daily_nav` 行 `external_flow_usdt ≠ 0` ⇒ 该日记 **UNKNOWN(未定价)**。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/live/watchdog.py:1099` — 「an external transfer is UNKNOWN (nav delta is not P&L there) and is NAMED below,」
  - `/Users/haosiyu/dl_quant_live/live/watchdog.py:1110` — 「elif _flow_day:」
  - `/Users/haosiyu/dl_quant_live/live/watchdog.py:1111` — 「per_day_loss.append(None)」
  - `/Users/haosiyu/dl_quant_live/live/watchdog.py:1252` — 「_recent_i = next((i for i in range(len(per_day_loss) - 1, -1, -1) if per_day_loss[i] is not None), None)」
  - `STATE.md:7` — 「用户已被提醒今日勿划转。」
- **A reader could wrongly conclude:** A reader assumes the 09-09 'flowday guard' commit fixed the cond2 fallback and allows a wallet transfer on a resume day, re-tripping the day-loss stop on a stale losing day.
- **Affects:** live_trading · **Severity reason:** Still true in the running executor ef60f85: a transfer day is None (unpriced) and cond2 judges the most recent priced day with no staleness bound, so the resume-day transfer ban remains a required operating rule (applied again at the 09-13 resume).
- **Proposed correction (exact text):** (无需改正, 审计复核 2026-09-13) 补一行: 「09-13 复核: 运行树 ef60f85 `live/watchdog.py` L1110–1111(划转日记 None)与 L1252(recent = 最近已定价日, 无新旧上限)未变 ⇒ 缺陷 2 仍未修; 研究仓提交 74b2acb5 只改 pilot_journal 工具的说明行, 不是执行器修复。恢复日禁划转仍是必需操作规则(09-13 复场同样执行, STATE.md L5)。」
- **Confidence:** VERIFIED (read-only read of ~/dl_quant_live/live/watchdog.py at HEAD ef60f85; `git show --stat 74b2acb5` touches only multi_asset/exports/live/pilot_journal/tools/flowday_daylossguard.py); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-40 · P1 · DOC_STALE
- **Source:** `memory/allweather_campaign_2026_09_05_verdict.md:9`
- **Quote:** 「**唯一有钱的项:** DL 月度全史重训劣于年折(两种子两窗 CI<0, −0.17~−0.24 bps/锚/gross ≈ 2× −7.5~−10% NAV/年; 机制 = 重训是高噪声抽样(种子间秩相关 0.53)而新数据无边际价值)⇒ PREREG_dl_freeze_yearly(v3 冻结至 2027-01), 需用户字。」
- **Superseding evidence:**
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:556` — 「1. **冻结读法 = (A) 早停是主因, 两个窗口都成立**(VERIFIED 表 AD3-3)。」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:562` — 「(A) ⇒ 冻结候选 `PREREG_dl_freeze_yearly_2026-09-05.md` 撤回, 改立"月度重训 + best-epoch 规则修正"候选」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:561` — 「⇒ 逐月折的验证切片(训练锚末 15%, ≈1000 锚)偏爱训练不足的早 epoch, 与 test 月的书层表现反向 —— 这就是 §11 提出的机制本身, 不只是伴随现象。」
  - `docs/PREREG_deploy_dl_recipe_2026-10.md:6` — 「**更正一处早前措辞**: 我曾把方案 B 写成「A(下限 5)+ 热启动」, 但复验过的热启动臂 **W1/W2 用的是逐字原早停规则(argmax), 不带下限**; 带下限的组合臂 W1F5 只有种子 42 且对两个单项都不加分(−0.034 / +0.072, CI 均含 0)。**⇒ 方案 B 的正确形态 = 只加热启动, 早停规则一字不改。**」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:38` — 「| 4b F10 refit(部署件) | `F10_DLW=/workspace/dlw_v4raw F10_OUT=/workspace/f8_v4 SEED=42 BEST_EP_FIX=7 $PY $R/pod_f10_refit_v4.py`(**四个 env 逐字, 缺一不跑**); 产物 `f8_v4/models/f10_live_s42.pt` + 报告里 `best_ep_rule` 必须读 `fix7` |」
- **A reader could wrongly conclude:** A reader asks the user to freeze the DL leg until 2027-01, forgoing recipe fixes that beat the live recipe with CI>0, and repeats the withdrawn 'new data has no value' mechanism.
- **Affects:** future_retrain, live_trading · **Severity reason:** The campaign's 'only money item' (freeze DL to yearly until 2027-01) and its mechanism ('high-noise sampling; new data has no marginal value') were superseded the next day: §12 found early stopping to be the main cause and the freeze candidate was withdrawn, and current candidates are an epoch-rule fix or warm start.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 本条「唯一有钱的项」已被次日收据取代 —— §12 冻结读法 (A)「早停是主因」(月折验证切片偏爱欠训练 epoch), 冻结候选 PREREG_dl_freeze_yearly 撤回, 改立「月度重训 + best-epoch 规则修正」候选(docs/RESULT_dl_monthly_gate_2026-09-05.md L556/L561/L562); 机制「高噪声抽样 + 新数据无边际价值」作废。现行候选: 方案 B 只热启动(PREREG_deploy_dl_recipe_2026-10 L6)或 FIX7(RUNBOOK_monthly_retrain_2026-10 步 4b), 十月选择待裁定 R-8。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-01 · P1 · DOC_STALE
- **Source:** `memory/k_window_180_live.md:3`
- **Resolution:** APPLIED by lead (memory description now begins 「⚠ 更正 09-13(AUDIT_EXEC CFG-03): 180s 从未在任何锚上运行」; MEMORY.md index now 「挂单窗 ⚠在役仍 900s, 180 未上线」). XREF AUDIT_EXEC CFG-03 — CROSS-REF + APPLIED by lead (memory description now opens with the 09-13 correction; MEMORY.md index reads 「挂单窗 ⚠在役仍 900s, 180 未上线」).
- **Quote:** 「★★★ 2026-08-10 上线: 挂单等待 900s→180s (commit 40c9e16)。逆向选择确证(未成交单的价格反而更朝我们方向走 +5.48 vs +3.66)⇒ 多等只加大漂移不改善筛选。改善 +0.56~0.69 bps/锚, 最保守漂移模型下下界是【不伤】」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:43` — 「"k_seconds": 900,」
  - `/Users/haosiyu/dl_quant_live/config/book.json:121` — 「★★ 回滚 180→900, 2026-08-10 02:5xZ, 在任何锚点于 180 下运行【之前】。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:95` — 「在役 `config/book.json`(sha `f6fd6d0e…`): k_seconds **900**, placement ε **0.5**, 重挂实验 p **0.5**; ERA2 运行起点 E+23.0→24.0 min」
  - `/Users/haosiyu/dl_quant_live/scheduler/run_anchor.py:339` — 「k = cfg.get("k_seconds", 900)」
  - `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28` — 「+5.48 vs +3.66 — the 900s→180s change is already live」
- **A reader could wrongly conclude:** A reader believes maker orders rest 180 s. That shifts the drift, fill-rate and chase premises, gets execution costs attributed to the wrong regime, and invites re-proposing "restore 900 s".
- **Affects:** live_trading, future_eval · **Severity reason:** The note states a live execution parameter that was rolled back before any anchor ran (live k_seconds=900), and the error has already been copied into a 2026-09-13 lead reading as "already live".
- **Proposed correction (exact text):** [替换 description] "★ 已回滚(2026-08-10 02:5xZ, 7c7d4ae; 零个锚运行于 180): 08-10 提案 k 900s→180s 同日撤回 —— maker 滑点实测 −2.232 bps 使最保守漂移模型下由「不伤」变「伤」。在役 k_seconds=900(~/dl_quant_live/config/book.json L43; T3 T-A1 2026-09-13 复核)。逆向选择读数(未成交 +5.48 vs 成交 +3.66)仍有效。" [正文首行插入] **⚠ 状态更正(2026-09-13 aud-kb)**: 本条「上线」已作废 —— book.json L121「回滚 180→900 … 在任何锚点于 180 下运行【之前】」; 生效路径现为 scheduler/run_anchor.py:339(非 :298); 重开条件见 book.json L122。MEMORY 索引「挂单窗180s」改为「挂单窗180s(已回滚, 在役900)」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### M3-02 · P1 · DOC_STALE
- **Source:** `memory/chase_closed_at_39.md:3`
- **Resolution:** APPLIED by lead (memory description now begins 「⚠ 更正 09-13(AUDIT_EXEC CFG-04): …09-01 起用户裁定重启 50/50 追单随机实验」; MEMORY.md index now 「chase 08-10结案 ⚠09-01 起 50/50 重启」). XREF AUDIT_EXEC CFG-04 — CROSS-REF + APPLIED by lead (memory description now opens with the 09-13 correction; MEMORY.md index reads 「chase 08-10结案 ⚠09-01 起 50/50 重启」).
- **Quote:** 「★★ chase 实验结案于 n=39(用户裁定 2026-08-10): E[H]−E[X] = +6.82−30.55 = −23.73 bps, CI[−48.89,+0.08] 擦 0。★ 判决只对 k=900 成立 —— k 已改 180, 追价变便宜, 不得外推」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/live/chase_policy.py:142` — 「# 2026-09-01 重启(PREREG_chase_restart_2026-09-01, sha 1a3f433325ae, 用户裁定): combo 时代重算」
  - `/Users/haosiyu/dl_quant_live/live/chase_policy.py:144` — 「ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.5, ARM_NO_CHASE: 0.5}」
  - `docs/PREREG_chase_restart_2026-09-01.md:3` — 「RESULT_chase_2026-08-10(不追, 仅k=900旧书世界)作废条款自指不外推; combo时代重算 E[H]=+58~69 vs E[X]=+20~23(点估计反向, CI未认证, 治疗臂休眠无成对数据 — RESULT_exec_reads_2026-09-01)。」
  - `/Users/haosiyu/dl_quant_live/config/book.json:43` — 「"k_seconds": 900,」
  - `/Users/haosiyu/dl_quant_live/ops/chase_readout.py:332` — 「ok, msg = gate(len(ins), a.override, rows[-1]["anchor_ts"] if rows else None,」
- **A reader could wrongly conclude:** A reader treats chase as permanently closed and misreads the live chase arm's top-up spend as a defect or policy breach. Or the reader discounts the 08-10 verdict as belonging to a k=180 world that never existed.
- **Affects:** live_trading, future_eval · **Severity reason:** The note calls chase closed ("do not chase") and says k is now 180. In fact the chase arm has been a live 50/50 randomised experiment since 2026-09-01, and k is 900.
- **Proposed correction (exact text):** [替换 description] "★★ chase 实验 08-10 结案于 n=39(不追, −23.73 bps, CI[−48.89,+0.08] 擦 0, 未认证); ★ 2026-09-01 已重启(PREREG_chase_restart_2026-09-01 sha 1a3f4333, 用户裁定): combo 时代重算 E[H]=+58~69 vs E[X]=+20~23 点估计反向, 在役 ARM_WEIGHTS chase/no_chase=0.5/0.5, 收成对样本至 n*=100 锚。「k 已改 180」作废: 180 同日回滚(7c7d4ae), 在役 k=900。" [正文首行插入] **⚠ 状态更正(2026-09-13 aud-kb)**: ① k=180 从未有锚运行, 本判决所在的 k=900 仍是在役配置, 「k 已改 180 ⇒ 更不可外推」的理由不成立; ② 使本判决不外推的是 08-26 换 combo 书, 读数以 PREREG_chase_restart 判据为准(live/chase_policy.py L141–144); ③ 下文 chase_readout 不传 realised_mix 的缺陷在 ef60f85 仍在(ops/chase_readout.py L332–333), 重启实验读数时会同样报假偏差。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** applied: stale quote no longer present

### M3-04 · P1 · DOC_STALE
- **Source:** `memory/opportunity_gross_is_not_capturable.md:12`
- **Quote:** 「(3) requote/reprice 家族两代双否决(08-05 经济学算式 / 本案模拟), DO-NOT-RETRY;」
- **Superseding evidence:**
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:37` — 「治理发现: 该机制 08-05 被自身装置否决、08-06 仍上线(提交说明未引否决 RESULT, 未见用户字)、08-09 文档仍称"未执行"、08-11 模拟再否决"关闭归档", 但实盘每锚运行 185 锚从未被真实账本判决 ⇒ 登记 E-0905-I。」
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:6` — 「08-05 纸面否决所用的两项输入(未成交重挂成本 −40 bps、p* 85.6%)与实盘不符。**读法: 不有害, 期望为正但幅度在实盘数据上定不出来(±10 bps); 不建议撤回, 建议补一份追认(它从未有用户字与 RESULT)。**」
  - `docs/PREREG_requote_randomised_2026-09-05.md:27` — 「实盘仓提交: **`12aa2a1`**(2026-09-05 11:48Z, safe_commit, 128/128 套件绿, 已推送;」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:95` — 「在役 `config/book.json`(sha `f6fd6d0e…`): k_seconds **900**, placement ε **0.5**, 重挂实验 p **0.5**; ERA2 运行起点 E+23.0→24.0 min」
  - `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28` — 「requote/reprice family double-vetoed, DO-NOT-RETRY」
- **A reader could wrongly conclude:** A reader thinks requote is not live or must not be touched, misattributes −5022 costs, or blocks the frozen randomised readout (≥09-19). The 09-13 T3 lead reading already cited this DNR.
- **Affects:** live_trading, future_eval · **Severity reason:** Marks as DO-NOT-RETRY a mechanism that has run on every live anchor since 08-06 and has been a live randomised experiment since 09-05; the 09-05 ledger review found the veto inputs do not match the live ledger.
- **Proposed correction (exact text):** [替换 (3)] (3) ~~requote/reprice 家族两代双否决, DO-NOT-RETRY~~ **【2026-09-13 更正】该 DNR 作废**: 重挂(执行器 phase 1.5)08-06 起即在实盘每锚运行(无用户字/无 RESULT, E-0905-I); 09-05 实盘账本复核 UNDECIDED 但分支经济学远高于盈亏平衡(p .942 vs p* .507), 08-05 否决输入(−40 bps / 85.6%)与实盘不符(docs/RESULT_requote_and_behind_live_causal_2026-09-05.md §0/§2); 09-05 11:48Z 起随机实验在役(p_requote 0.5, 12aa2a1), 读数点 ≥09-19 且 direct ≥1500 计划, 恰一次。本案 +1.75 模拟只否决「按机会毛额论证执行改进」这一论证形式, 不构成机制 DNR。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-05 · P1 · DOC_STALE
- **Source:** `memory/slippage_is_a_selection_effect.md:39 (+2 more)`
- **Quote:** 「**冻结未执行**: `PREREG_reject_maker_requote_2026-08-05`(台账 #50, ~0.35 夏普, 零 IC 代价) ——
`-5022` 拒绝单以新鲜触价重挂一次 post-only, 失败才落 taker。**不可**把报价挂得更被动:
那会把成交量从 from_reject(−1.53)推向 from_partial(−40)—— **方向是反的**。」
- **Superseding evidence:**
  - `docs/PREREG_requote_and_behind_live_causal_2026-09-05.md:8` — 「`RESULT_cost_postswap_2026-08-09.md` §4 仍称该预注册"冻结未执行"」
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:6` — 「08-05 纸面否决所用的两项输入(未成交重挂成本 −40 bps、p* 85.6%)与实盘不符。**读法: 不有害, 期望为正但幅度在实盘数据上定不出来(±10 bps); 不建议撤回, 建议补一份追认(它从未有用户字与 RESULT)。**」
  - `STATE.md:124` — 「★ bandit 采纳部署**: 恰一次主判(f657efde 冻结配方, 21 日块)ΔV **+1.658 CI95[+1.102,+2.280]>0** + 死法①弹性证伪(Δ成交率+1.0pp<2pp)同触 + 不毒 ⇒ 用户字采纳 **eps 0.35→0.50**」
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:7` — 「**behind: 冻结判据 UNDECIDED, 且毒性线翻转**: 锚内配对全包成本 behind − join = −4.84 bps [−20.7, +1.9](未决), 成交价优 3.7 bps、首次拒单率 21.5% vs 29.9%; 但 **markout60(覆盖 95%)behind −7.69 vs join −2.40, Δ −5.28 [−14.19, −0.33]**」
  - `docs/STATUS_three_questions_2026-09-12.md:23` — 「**BNB 手续费抵扣断了 6 天(09-07 起)**: 每锚 maker 恰 2.0000 / taker 恰 5.0000 bps, commission 全 USDT, 账户在 VIP0 底档。」
  - `docs/MILESTONE_2026-08-26.md:48` — 「换手成本全审: 3.52 bps/单位意图 [0.32,6.64]; cad8/α/带维持。」
- **A reader could wrongly conclude:** A reader "deploys" requote as if new, cites −40 bps from_partial as the requote branch cost, blocks behind placement as "the wrong direction", or quotes 3.63 bps as the STATE-authoritative cost.
- **Affects:** live_trading, future_eval · **Severity reason:** Says requote is frozen and unexecuted and warns against more passive quoting. In fact requote has been live since 08-06 (randomised since 09-05), its −40 bps branch input was refuted on the live ledger, and the more passive "behind" arm is live at ε=0.50.
- **Proposed correction (exact text):** [替换 L39–41] **【2026-09-13 更正】** ~~冻结未执行~~: 该机制(执行器 phase 1.5 重挂)**08-06 起已在实盘运行**(E-0905-I, 无用户字); 09-05 实盘账本复核 UNDECIDED, 分支: 重挂落单成交 61% 名义 −9.59 bps / 未成交 3% +16.6 / 二次拒 35% +19.15, 08-05 否决输入(−40 bps、p* 85.6%)与实盘不符; 09-05 起随机实验 p_requote 0.5 在役(docs/PREREG_requote_randomised_2026-09-05.md)。「不可挂得更被动」亦被实盘改写: behind 臂 ε 0.35→0.50 已采纳(09-01), 09-05 全覆盖读数价优 3.7 bps 但 markout60 更毒 Δ −5.28 [−14.19,−0.33], 维持 0.50 不扩大。另: 成本口径 3.63(「STATE 唯一权威」)已被 08-21 复审 3.52 [0.32,6.64] 取代(且仅 ERA1 旧书单窗); BNB 抵扣 08-05 起启用、09-07 起中断(STATUS_three_questions_2026-09-12 L23)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M3-10 · P1 · DOC_STALE
- **Source:** `memory/deepsmooth_band_deployed.md:17`
- **Resolution:** XREF AUDIT_EXEC STA-03 / CFG-07 — CROSS-REF: external-book branch skips harvest EMA / neutral band; the live-config side is owned by AUDIT_EXEC STA-03 and CFG-07.
- **Quote:** 「**How to apply:** (a) 深平滑后一切"信号失效"判断以 ic_monitor 为准, 不看书的换手/仓位反应;」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/ops/ic_monitor.py:17` — 「★ 标定身份(2026-09-12 独立复核): 阈值标定于 α=0.05/band=0.002 的离线书; 在役书 α=0.1/」
  - `/Users/haosiyu/dl_quant_live/ops/ic_monitor.py:18` — 「band=0.00025 —— 阈值【未】按在役形态重标, 5%/1% 的概率含义对在役形态不成立。」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1664` — 「# ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:10` — 「EMA 0.1 + 带宽 2.5e-4 对 890 个名-锚预测「冻结 / 移动」, 与观测逐一相符, 不符 0。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:26` — 「外部书分支均跳过中性带与 harvest EMA, `DEFAULT_BAND_BPS = 0.0` 且非测试代码无覆写(G-CODE PASS); `state/live/no_trade_band.json` 最后写于 A1787371250 = 08-22 04:00Z(外部书切换前最后一个内部书锚), 之后未写。」
- **A reader could wrongly conclude:** A DECIDE/ALERT gets read as a calibrated 1%/5% signal-failure event and triggers a book-level response, against the no-book-level-response-to-instrument-doubt rule. A reader also believes α=0.05 EMA and b=0.002 band shape the live book.
- **Affects:** live_trading, reporting · **Severity reason:** Makes ic_monitor the judge of signal failure and reads its thresholds as 5%/1% events. Those thresholds were calibrated on an α=0.05/b=0.002 book, which has not been the live book since 08-22.
- **Proposed correction (exact text):** [description 末尾追加] 【2026-09-13: 08-22 起外部书(combo)分支不施 harvest EMA/中性带(anchor_loop.py L1664–1666), 在役平滑在生产者 α=0.1/band=0.00025; ic_monitor 阈值(L13 的 ALERT −0.0228 / DECIDE −0.0443)仍按 α=0.05/b=0.002 离线书标定, 5%/1% 概率含义对在役书不成立(ops/ic_monitor.py L17–19)】 [替换 How to apply (a)] (a) ~~深平滑后一切"信号失效"判断以 ic_monitor 为准~~ ic_monitor 只作未重标的描述性告警: 阈值未按在役形态(α=0.1/band=0.00025)重标, DECIDE/ALERT 不是 1%/5% 事件, 不得单独触发书级动作; 重标需生产者平价回放 Phase 2 在役书逐锚分布 + 重盖章。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-18 · P1 · DOC_STALE
- **Source:** `memory/stop_response_reversible_pricing.md:14`
- **Quote:** 「static 2×: ret +48%/yr, Sharpe 1.14, P(−25% from window start) 7.1%; one-step ladder −10%→half gross (recover −5%): +44%, Sharpe 1.13, P(trip) 0%, delevered 15% of time, cost 6.5 bps;」
- **Superseding evidence:**
  - `docs/PLAN_deposit_2026-09-10.md:14` — 「借用受据"−10%→半仓, 代价−4pp"**不迁移** —— 本书自己的三种子上该臂代价 = 2.0× −13.5~−14.9pp / 2.5× −22.6~−25.5pp」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「**Full-history tail of the fixed book at 2.0× (raw replay vol): maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.**」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:93` — 「| **2.00** | 1.0 | **−43.9 % (−44.5 %)** | **−6.41 %** | **5 (6)** | **23 (26)** | **1.09 (1.31)** | **26.8 % (33.1 %)** | 21.2 % (20.6 %) |」
  - `multi_asset/exports/eda/PREREG_stop_response_reversible_2026-08-21.md:1` — 「**状态:** 预注册草案(待用户一字; 未动书)」
  - `docs/PLAN_deposit_2026-09-10.md:49` — 「阶梯受据=stop_response_reversible_pricing(−10%→半仓, 触线→~0, 代价−4pp/年)」
- **A reader could wrongly conclude:** A reader sets leverage or stop-response policy believing a −25% loss from start is a ~7% risk and a −10%→half-gross ladder is nearly free with ~0 trips.
- **Affects:** live_trading, future_eval · **Severity reason:** The tail and stop frequencies and the ladder's "P(trip) 0%" come from the old in-role book. For the live combo book they were refuted or recomputed (ladder cost −13.5~−14.9pp at 2.0×; true 1y maxDD≥25% at 26.8–33.1%), yet PLAN_deposit still cites this note as the ladder receipt.
- **Proposed correction (exact text):** [append after the drawdown-ladder paragraph] **Superseded for the live book (2026-09-13 audit):** these numbers are from the old in-role book S1 (pre-combo, pre-E-0904-F/v4). For the live combo book the −10%→half-gross ladder does NOT transfer: on this book it costs −13.5~−14.9pp at 2.0× and was rejected (PLAN_deposit_2026-09-10 §1, 2026-08-28). Current full-history tail reference (v4 pin, r18 NW fixed book, 2.0×, raw replay vol): maxDD −43.9%/−44.5%, worst day −6.40%, −4% halts 5/6 (1.09/1.31 per yr), P(1y true maxDD ≥25%) 26.8%/33.1% (start-loss 21.2%/20.6%); under the ×1.4042 vol sensitivity, 18 halts. The reversible-response PREREG is still a draft (not wired); the live §4-2 response is still flatten (STATE §1).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-21 · P1 · DOC_STALE
- **Source:** `memory/deposit_option_c_ruled.md:3`
- **Quote:** 「用户裁定方案 C(2026-08-10): 今日入金 @2×, 84 锚为正 ⇒ 升 3× + 停机线 −50% 打包预授权; TRANSFER 不入盈亏使停机线自动重标定」
- **Superseding evidence:**
  - `multi_asset/exports/eda/PREREG_deposit_84anchor_escalation_2026-08-10.md:19` — 「- **W2 · 窗口内无 watchdog 硬停机触发**(任一硬停 ⇒ 当场自动 FAIL, 不等窗口走完)。」
  - `docs/ERROR_LEDGER_2026-08-20.md:108` — 「## ★★★ E-0821-A 停机线读错量: §4-2 双计前日未实现 ⇒ 误平整书(2026-08-21 12:16Z)」
  - `docs/ERROR_LEDGER_2026-08-20.md:101` — 「⇒ 第二次整书平仓(2026-08-21 20:16Z)」
  - `STATE.md:115` — 「★ 入金 +62,998 USDT(12:44:01Z 到账, 权益 84,036)· 用户裁定"一步到位"**: 16:00Z 锚按 constant_leverage_2.0 直接 sizing 至 gross ≈168k(现 41.7k, ×4.0), 不爬坡。」
  - `STATE.md:146` — 「- **止损/风控**: 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)⟺ book_source=external 耦合; 看门狗 cond2 日亏 −4% flatten(口径 0aa6586)/ cond4 −25% 起始权益口径(57cb180);」
- **A reader could wrongly conclude:** A reader treats 3× leverage plus a −50% kill line as already user-authorised and prepares to apply it without a new user word.
- **Affects:** live_trading · **Severity reason:** Records a 3×/−50% escalation as still "pre-authorised". The window's auto-FAIL condition (any hard stop) was met on 08-21, the book was swapped on 08-26, and the 09-03 deposit ruling fixed constant 2.0× with cond4 still at −25%.
- **Proposed correction (exact text):** [description 末尾追加] 【2026-09-13: 预授权已失效 —— 84 锚窗(08-10 12Z 起)内 08-21 12:16Z/20:16Z 两次看门狗整书平仓(E-0821-A/C), 按 PREREG W2「任一硬停 ⇒ 当场自动 FAIL」(正式读数文件未找到, 按规则推定); 08-26 换 combo 书; 09-03 入金裁定 constant_leverage_2.0; 在役 cond4 仍 −25%(STATE §1)。任何升杠杆/改停机线需新用户字, 并以 v4 口径尾部(r18: 2.0× 全史 maxDD −43.9%/−44.5%)为输入】
- **Confidence:** INFERRED (the frozen W2 rule, both 08-21 whole-book flattens, the 09-03 constant-2.0× ruling and the current −25% cond4 were all opened and quoted. The formal 84-anchor readout document was not located, so "the window auto-FAILed" is inferred from the frozen rule.) · **Quote re-verified at assembly:** exact

### M3-23 · P1 · DOC_STALE
- **Source:** `memory/stress_campaign_2026_08_19.md:11`
- **Quote:** 「- **尾部预算**: 3.5× 场景按 **−25~−30%** 计(×0.55 线性校准被批评者驳回且成立 — EMA 在因子反转日反而加害); 全七年最坏读数不破 −50% 线 ⇒ 3.5× 硬顶必须与 −50% 停机线打包。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「**Full-history tail of the fixed book at 2.0× (raw replay vol): maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.**」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「Under the ×1.4042 sensitivity (not a fact — the reviewer's same-period paired σ ratio is 0.656 [0.467, 1.008]) the 2.0× book has 18 halts, maxDD −65.7 % / −66.6 %」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%」
  - `STATE.md:115` — 「★ 入金 +62,998 USDT(12:44:01Z 到账, 权益 84,036)· 用户裁定"一步到位"**: 16:00Z 锚按 constant_leverage_2.0 直接 sizing 至 gross ≈168k(现 41.7k, ×4.0), 不爬坡。」
- **A reader could wrongly conclude:** A reader argues for 3–3.5× leverage with a −50% line, believing tail losses stay within −25~−30%.
- **Affects:** live_trading, future_eval · **Severity reason:** Frames 3.5× as survivable inside −50% with a −25~−30% tail budget. On the live book at only 2.0×, the v4 full-history maxDD is already −43.9~−46.9% (−65.7% under the vol sensitivity).
- **Proposed correction (exact text):** [L11 后插入] **【2026-09-13 更正】** 本条尾部预算属 08-19 旧内部书/代理事件口径(pre-E-0904-F)。在役 combo 书 v4 钉全史读数: 2.0× 固定书 maxDD −43.9%/−44.5%(r18 NW), W_FULL 复利 NAV −46.42%/−46.89%(A0 两种子), P(1y 真 maxDD≥25%) 26.8%/33.1%; ×1.4042 波动敏感性下 2.0× maxDD −65.7%。⇒「3.5× 宽≈2× 在役」「3.5× 按 −25~−30% 计、不破 −50%」均不得再用; 现行杠杆 constant 2.0×(09-03 裁定)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-30 · P1 · DOC_STALE
- **Source:** `memory/ic_canon_table.md:19`
- **Quote:** 「**书的正典质量指标 = 净额/锚(+1.68bps)与 Sharpe(2.7-3.0), 不是 IC**; IC 只是分数层诊断。」
- **Superseding evidence:**
  - `docs/PREREG_leg_ablation_2026-08-26.md:271` — 「## §T5 干净终表(全部 CAL=simple, 装置=加固后 w10, 基线=在役宽书 净1.3067/夏普2.18)」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:16` — 「**无偏口径下实盘形态并不优于正典**(+0.691 vs +0.730), 旧口径的优势(+1.597 vs +1.216)是伪凸性产物;」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:29` — 「原钉 W_ALPHA **[0.3207, 2.2822]**(SE 0.4890)」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
- **A reader could wrongly conclude:** Candidates get judged against an inflated baseline, or the user is told this is a ~3-Sharpe book; the 77% fund share is also quoted as current.
- **Affects:** future_eval, reporting · **Severity reason:** Labels CAL=simple book numbers (+1.68 bps, Sharpe 2.7–3.0) as the canonical quality baseline. Under the v4 pin the live-form A0 full cycle is g +0.636 bps/anchor with Sharpe 1.29 [0.32, 2.28].
- **Proposed correction (exact text):** [替换 L19 书层数字] **【2026-09-13 更正】** 书层正典数字改为 v4 钉(r18 归档 A0, g=net_ex/gross_total, RAW Π y4): 全窗 2022-06..2026-08 g **+0.636 bps/锚**(单位 gross), Sharpe **1.29**(日块自举 CI95 [0.32, 2.28]); 逐年 2022(06-30 起) +0.48 / 2023 −1.94 / 2024 +1.09 / 2025 +1.19 / 2026 +4.53(r18 receipts/TABLE_per_year_v4_caliber_2026-09-12.md, 含勘误)。原「+1.68 bps / 2.7–3.0」出自 PREREG_leg_ablation §T5(CAL=simple, E-0904-F 伪凸性)作废。L16「书的77%主腿」过时: 09-11 00Z 名义 fund 65.4% / king 19.0% / DL 15.6%。分数层 IC 各行未在 v4 面板上复核, 引用时标注面板谱系。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-31 · P1 · DOC_STALE
- **Source:** `memory/feedback_report_live_caliber_full_cycle.md:9`
- **Quote:** 「**How to apply:** 引用前先查 `docs/AUDIT_live_vs_replay_2026-09-04.md` §3 表;」
- **Superseding evidence:**
  - `docs/REVIEW_caliber_final_2026-09-04.md:281` — 「用户规则(ERROR_LEDGER L373; memory `feedback_report_live_caliber_full_cycle` "引用前先查 AUDIT §3 表")所指向的那张表本身即是陈旧口径, "引用前先查"应改指本节 §5.1/§5.2(含 2022–23 标注行)直至 jpline 复跑。」
  - `docs/REVIEW_caliber_final_2026-09-04.md:400` — 「| 20 | `AUDIT_live_vs_replay` §3 全表 + `RESULT_allweather` §0/§1(含 H1 阶梯录取候选、"2024 −8→+3")| **CAL=simple-stale**」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:1` — 「# 口径锁 · 本研究分支一律按 v4 链(2026-09-09)· 任何 v3 谱系数字作废」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:1` — 「**状态:** 收据(用户问「正确的回测结果是多少」; 反馈规则: 只报实盘口径全周期逐年表)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp)」
- **A reader could wrongly conclude:** Future reports to the user quote inflated CAL=simple per-year returns/Sharpe (the exact failure that created this rule) or arithmetic ×2 drawdowns.
- **Affects:** reporting, future_eval · **Severity reason:** A permanent user rule sends every reported backtest number to a table ruled CAL=simple-stale, and its "current live form" definition (W3FIX 0.21/0.79, frozen 450, 0.3 bps fidelity, data to 08-15) is out of date.
- **Proposed correction (exact text):** [替换 How to apply 首句] **How to apply(2026-09-13 更正):** ~~引用前先查 AUDIT_live_vs_replay §3 表~~(该表 CAL=simple-stale, REVIEW_caliber_final §5.3b/#20); 现行正典 = v4 钉逐年表 multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md(含勘误; A0 全窗 Sharpe 1.29 [0.32,2.28]), 口径锁 uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md; 回撤一律按固定 2× 每锚复利 NAV 报(非算术 ×2)。「当前实盘形态」以 STATE.md §1 为准(已含 M1 宇宙与动态席位播种, 非 W3FIX 0.21/0.79 冻结 450); 表必须写数据截止日。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-34 · P1 · DOC_STALE
- **Source:** `memory/regime_dash_usage.md:7`
- **Quote:** 「每锚深查模板加一节读 `multi_asset/exports/live/regime_dash/REGIME_DASH.md` 最新行」
- **Superseding evidence:**
  - `multi_asset/exports/live/regime_dash/REGIME_DASH.md:1` — 「# REGIME DASH(只读)— 最新锚 2026-09-02T08:00Z」
  - `/Users/haosiyu/regime_dash/REGIME_DASH.md:3` — 「采集器 regime_dash.py」
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.regime_dash.plist:5` — 「<string>/Users/haosiyu/regime_dash/regime_dash.py</string>」
- **A reader could wrongly conclude:** Anchor deep-checks report an 11-day-old σ_fund percentile, flags, seat and suggestions, which then feed de-leverage, FTRIM or seat discussions with stale regime state.
- **Affects:** live_trading, reporting · **Severity reason:** The per-anchor inspection rule points at a repo copy frozen at the 2026-09-02 08Z anchor. The live launchd collector writes ~/regime_dash/REGIME_DASH.md, whose latest anchor was 2026-09-13 12Z when read at 12:50Z.
- **Proposed correction (exact text):** [L7 路径替换并追加] **【2026-09-13 路径更正】** 仪表盘在役输出 = `~/regime_dash/regime_dash.jsonl(追加式, 按 `anchor_utc` 取 `w3_masked_king`/`w3_masked_fund`; 滚动的 `REGIME_DASH.md` 每锚被整份重写, 不可作收据 —— DEV-14)`(launchd com.hsy.regime_dash → ~/regime_dash/regime_dash.py; PENDING_RULINGS.md 同目录); 仓内 `multi_asset/exports/live/regime_dash/REGIME_DASH.md` 是 09-02 08Z 的冻结快照, 不得作「最新行」读。读前核首行「最新锚」= 当前锚。 【DEV-14 补注 2026-09-16】逐锚可复核值: 2026-09-13T12:00Z king 0.3821 / fund 0.6179 · 2026-09-16T00:00Z king 0.3780 / fund 0.6220; 日志覆盖 2026-09-02T08:00Z 起。
- **Confidence:** VERIFIED (quote+receipt opened; ~/regime_dash/REGIME_DASH.md header read at 2026-09-13T12:50Z showed 最新锚 2026-09-13T12:00Z; that file rewrites every anchor, so the quoted collector line is the stable anchor) · **Quote re-verified at assembly:** exact

### M3-36 · P1 · DOC_STALE
- **Source:** `memory/feedback_no_post_hoc_tricks.md:49`
- **Quote:** 「That phase is mostly done — y_600 architectural exploration is exhausted (V5-LH ×4, multi_scale, pyramid all dead per anti-pattern #11). Now in production-finalization phase, SWA/EMA/multi-seed are all on the table.」
- **Superseding evidence:**
  - `CLAUDE.md:33` — 「多种子集成/训后技巧(用户禁)」
  - `memory/feedback_no_multi_seed_2026_05_15.md:12` — 「"怎么又开始 multi seed 了, 强调了很多次了先从底层的模型特征损失上考虑, 不要 multi seed, 记录下来"」
- **A reader could wrongly conclude:** A retrain or evaluation proposal uses seed ensembling or checkpoint averaging and cites this note, violating a standing user ban.
- **Affects:** future_retrain, future_eval · **Severity reason:** A 2026-04-30 permission for multi-seed/SWA ensembles is contradicted by the later 2026-05-15 user rule and the project anti-pattern list ("多种子集成/训后技巧(用户禁)").
- **Proposed correction (exact text):** [insert at top of body] > **SUPERSEDED (2026-09-13 audit):** the later user rule of 2026-05-15 ([[feedback_no_multi_seed_2026_05_15]]: 「怎么又开始 multi seed 了 … 不要 multi seed」) and CLAUDE.md anti-patterns (「多种子集成/训后技巧(用户禁)」) override this 04-30 relaxation. Do NOT propose multi-seed ensembles, SWA/EMA-across-seeds blends or checkpoint averaging as uplift; multiple seeds are allowed only as replication checks (assert self_sha256 first, E-0826-B). The "3-seed value-blend in production CSV" refers to the retired single-asset era.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-01 · P1 · DOC_STALE
- **Source:** `memory/infra_server_jpline.md:8`
- **Quote:** 「**重要 (compact 后必读):** training infrastructure 早已从 RunPod 切换到固定 server。绝对不要再称"pod"或用 RunPod-era 的 `ssh -p PORT -i KEY root@IP` 模式。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `STATE.md:113` — 「jpline 11:47Z 起不可达。」
  - `STATE.md:182` — 「**jpline 重连定时已按用户字停止(09-06 05:4xZ)。**」
  - `docs/MILESTONE_2026-08-26.md:101` — 「| pod2(RTX PRO 4500) | GPU 训练 + LOB |」
  - `STATE.md:14` — 「pod2 容器内存上限 61 GB(非 free 显示的 247 GB)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:222` — 「### ALM-03 — factor_health still polls the retired jpline report every anchor」
- **A reader could wrongly conclude:** A future session tries to train or rerun judges on jpline, refuses to use pod2 as 'RunPod-era', or assumes jpline-only artefacts (probe_artifacts, pod_backup_2026-08-21, hist king) are retrievable.
- **Affects:** future_retrain, future_eval · **Severity reason:** The note calls itself mandatory reading before any server reference, yet it forbids naming the real GPU host (pod2) and routes training (L47: 'pod 无空闲 GPU 时先用 jpline') to a host unreachable since 2026-09-04, misdirecting retrain and judge reruns.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正(基建现状):** jpline 自 2026-09-04 11:47Z 起不可达(STATE.md「jpline 11:47Z 起不可达」条), 重连定时已于 09-06 05:4xZ 按用户字停止; 现役机器 = mac(生产者+执行器)+ pod2(RTX PRO 4500, GPU 训练 + LOB, `/workspace/`, 容器内存上限 61 GB)。本条「绝对不要再称 pod」与 L47「pod 无空闲 GPU 时先用 jpline」均已失效: pod2 是正式 GPU 主机, 训练与判官复跑不得路由到 jpline; 只存于 jpline 的件(probe_artifacts / pod_backup_2026-08-21 / hist king 等)按不可取处理, 引用前先查 git 或 pod2 副本。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-02 · P1 · DOC_STALE
- **Source:** `memory/ma_v2_pilot_protocol_hardening.md:63`
- **Quote:** 「**2026-08-20 逐名止损条款 ACTIVE(commit 0bcc089)**: 深度=unrealizedProfit/|notional| ≤−25% 连续 2 终锚 ⇒ 该名 flatten_only(maker 出场), 平后 7 天禁入; 其余名照常。机制=复用 untradable→pop/clamp 全通道」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:140` — 「"active_profile": "wide",」
  - `/Users/haosiyu/dl_quant_live/config/book.json:144` — 「"depth_pct": -0.3,」
  - `/Users/haosiyu/dl_quant_live/config/book.json:147` — 「"min_notional_usdt": 5.0,」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「**已停的多头仓位不会被平到 0**。」
  - `STATE.md:10` — 「**W9**(实盘逐名止损不把被止损名平到 0; 上线以来 157 例, 不限多头)最终版 `73d55602` diff f8beb082: force_flat 使持有止损名离开重整人口、恰 0.0 走 flatten_only」
  - `STATE.md:7` — 「提交 **`ef60f85`** 并推送」
  - `STATE.md:6` — 「flatten_only 可沿 chase 框架补单而条款写 maker-only 不追(W9 把原被钉住的止损多头接入此通道, 政策待用户裁定)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:132` — 「### EXE-02 — Stop and exit residuals are topped up with taker orders through the chase frame, while the stop clause says maker-only, no chase」
- **A reader could wrongly conclude:** A reader believes stops fire at -25% with maker-only exits and that every stop before 09-13 actually flattened the name, so pre-09-13 stop counterfactuals and insurance-premium estimates read as realised protection.
- **Affects:** live_trading, reporting · **Severity reason:** States the live per-name stop threshold and exit path as fact, but the live wide profile is -30%/5 USDT, the described pop/clamp path pinned 94 of 125 stopped longs until W9 landed 2026-09-13, and exits can now chase, so live-risk assessment and stop post-mortems would be wrong.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 自 2026-08-22 外部书上线起实盘生效的是 `per_name_stop.active_profile = wide`(`~/dl_quant_live/config/book.json` L140–147: 深度 ≤ −30%、连续 2 锚、冷却 7 天、min_notional 5 USDT), 不是本段的 −25% 基础值。本段「复用 untradable→pop/clamp 全通道」在 09-13 前**实际没有把被止损多头平掉**: reshape 去均值平移 + clamp 把 125 个已停且持仓实例中的 94 个多头钉在原仓(T5b RESULT L28); 修复 W9 于 2026-09-13 随 ef60f85 上线, 12Z 锚起生效(STATE.md 09-13 12:0xZ 条)。W9 后止损残余可经 chase 框架补单, 与条款「maker 出场不追」冲突, 政策待用户裁定(STATE.md 09-13 12:1xZ 条; AUDIT_EXEC EXE-02)。09-13 前的逐名止损触发与反事实回填不得读作「已平仓」的效果。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-03 · P1 · OPEN_NOT_MEASURED
- **Source:** `memory/ammunition_campaign_night1.md:20`
- **Quote:** 「**腿级补卷(2026-09-01, PREREG e888007fd6ae)**: fund 腿分构造五臂(v2口径/HL1.5d/HL7d/动量微混/surprise微混)书层同座门全 REJECT — **HL3d rank 在腿分书净域也是充分统计**, 两测量域封顶。每种扰动均伤 2026 富年 = 在役口径对主 regime 已调准。重开=新信息源或 regime 断裂。」
- **Superseding evidence:**
  - `docs/PREREG_fundleg_engineering_2026-09-01.md:14` — 「CAL=simple LEGS=101 PHI=0.45 LOOK=900」
  - `docs/REVIEW_caliber_final_2026-09-04.md:105` — 「`w10_universe.py` 及 w10_* 姊妹 | 同上 | Σ-simple | expm1 默认 | 否 |」
  - `docs/REVIEW_caliber_final_2026-09-04.md:134` — 「fund +0.30/+0.74/+0.88」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `docs/RESULT_xregime_2026-09-02.md:61` — 「REJECT(fund 腿构造轴 DNR 再确认)」
  - `docs/STATUS_three_questions_2026-09-12.md:141` — 「**全周期 Δg +0.41 [+0.18, +0.64] / ΔSharpe +0.81(SE 0.23)⇒ 约 2.2 —— "2+" 是这个**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:107` — 「2. **固定 carry 后, fund 腿分数自身没有可辨认的正价格边**」
  - `docs/audit_pipeline_2026-09-13/AUDIT_DATA.md:493` — 「### EVL-01 — w10 sleeve devices still default CAL to 'simple' (expm1 on an already simple return); every committed run since 09-09 sets CAL=log」
- **A reader could wrongly conclude:** Future proposals to change fund-leg construction (half-life, surprise mix, liquidity re-weighting) are rejected by citing 'HL3d rank is a sufficient statistic / tuned to the main regime', although this was never measured on CAL=log or v4 and XIB_LAG50 shows a CI>0 re-weighting on v4.
- **Affects:** future_eval · **Severity reason:** The fund leg is the book body; this DNR closes its construction axis on the CAL=simple caliber that carries a fund-leg pseudo-convexity bias and has flipped other relative verdicts, so it would block evaluation of book-behaviour changes.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 待复验(E-0904-F):** 本段五臂判决与 09-02 瞬时脉冲负权「DNR 再确认」(RESULT_xregime L61)都跑在 w10 家族 `CAL=simple`(PREREG_fundleg L14; REVIEW_caliber_final L105 expm1 默认), 该口径对 fund 腿有 +0.30/+0.74/+0.88 bps/锚 伪凸性(REVIEW_caliber_final L134), 且无偏复验已使在役相对判决失去显著性(RESULT_caliber_revalidation L52)。未在 CAL=log / v4 口径重判 ⇒「腿构造轴 DNR」「HL3d rank 为腿级充分统计」「在役口径对主 regime 已调准」一律降为**未测**。v4 口径已有线索: fund 腿 × Amihud 再加权 XIB_LAG50 全周期 Δg +0.41 [+0.18, +0.64](事后预选、未晋级, STATUS_three_questions L138); 固定 carry 后 fund 分数无可辨认正价格边(T2, PROGRAM_r2 L92)。重开 fund 腿构造须按预注册在 v4 口径重判, 不得引本段拒绝。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-01 · P1 · DOC_STALE
- **Source:** `memory/patch_on_disk_is_not_patch_running.md:15`
- **Quote:** 「重启长驻进程时**完整复制其环境变量**(本次 SHADOW_OFFSET_MIN=16 若丢失会让书每锚 stale 冻结), 且 macOS 无 `setsid`(用 `nohup ... & disown`)。」
- **Superseding evidence:**
  - `docs/RUNBOOK_wide_live_2026-08-22.md:34` — 「# ★ 2026-08-30 起三守护已 launchd 化(E-0829-B 修复, 重启+崩溃双自愈; 上行 nohup 命令仅作应急后备):」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「#   管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:37` — 「#   注意: 手动再起 nohup 实例会与 launchd 实例争锁(producer 自解, shell 守护无锁) —— 一律用 launchctl」
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.shadowloop.plist:10` — 「<key>EnvironmentVariables</key><dict><key>SHADOW_OFFSET_MIN</key><string>16</string></dict>」
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.combolive.plist:10` — 「<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>」
- **A reader could wrongly conclude:** A reader who hot-patches shadow_loop_v3 or combo_live_daemon restarts it with `nohup … & disown` and hand-copied env and reports the patch as running. launchd's KeepAlive instance keeps running the old code, or two combo daemons run side by side.
- **Affects:** live_trading · **Severity reason:** Following the nohup/disown restart for the launchd-managed producer or combo daemon either gets refused by the producer lock while the old code keeps trading, or starts a second, unlocked combo daemon, so a hotfix deploy is falsely declared live.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 2026-08-30 起 com.hsy.shadowloop / com.hsy.sidecar / com.hsy.combolive 均由 launchd 托管(KeepAlive SuccessfulExit=false; SHADOW_OFFSET_MIN=16 已固化在 plist EnvironmentVariables)。重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.<label>`, 不再手工复制环境变量, 禁用 `nohup … & disown`(生产者会被锁拒绝而旧进程继续跑; shell 守护无锁会双开)。生效证据 = 新 PID 的 `ps -o lstart` 晚于源码 mtime + `ps eww` 含 SHADOW_OFFSET_MIN=16 与 XPC_SERVICE_NAME。见 docs/RUNBOOK_wide_live_2026-08-22.md L34–37。
- **Confidence:** VERIFIED (quote+receipt opened; plists read and `launchctl list` shows com.hsy.shadowloop PID 10900 / com.hsy.combolive PID 30944 on 2026-09-13) · **Quote re-verified at assembly:** exact

### M5-03 · P1 · DOC_STALE
- **Source:** `memory/live_battery_gate_coverage_blind_spot.md:8`
- **Quote:** 「**How to apply**: 给实盘仓加测试的三件套 = 测试文件 + `run_acceptance.sh` SUITES 注册 + `ops/gate_coverage.py` 盲区自述; 电池约 10 分钟; 执行器每锚新进程 ⇒ 提交在下一锚生效;」
- **Superseding evidence:**
  - `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md:16` — 「⚠ **隐式部署陷阱(VERIFIED 读 `ops/safe_commit.sh` L23–28)**: safe_commit 在运行目录被调用时先 `git fetch origin main`, 落后就 `git rebase origin/main` ⇒ **下一次在 `~/dl_quant_live` 跑 safe_commit 会把 b681ca5 一并带入并推送 = 没人裁定的部署**。」
  - `docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md:143` — 「6. **合并 ≠ 部署**; 运行目录只经明做的 `pull --ff-only` 或 safe_commit 切换; safe_commit 自带 rebase = 隐式部署 ⇒ 部署未裁定期间禁在运行目录 safe_commit。」
  - `/Users/haosiyu/dl_quant_live/ops/safe_commit.sh:28` — 「git rebase origin/main」
- **A reader could wrongly conclude:** A reader believes a safe_commit in the run directory only activates their own change at the next anchor, while it also deploys every merged-but-undeployed origin/main commit.
- **Affects:** live_trading · **Severity reason:** Following the add-a-test procedure (safe_commit in ~/dl_quant_live) while origin/main is ahead silently rebases and pushes unruled executor commits, i.e. an undecided deploy.
- **Proposed correction (exact text):** ⚠ 补充(2026-09-11 起, 2026-09-13 审计): `ops/safe_commit.sh` 在运行目录 `~/dl_quant_live` 调用时先 `git fetch`, 落后即 `git rebase origin/main` 再推送 ⇒ 下一锚生效的不只是你的改动, 还有 origin/main 上全部未部署提交 = 隐式部署。跑之前先核 `git -C ~/dl_quant_live rev-list --count HEAD..origin/main` == 0; 非 0(合并 ≠ 部署、部署未裁定)时禁止在运行目录跑 safe_commit, 改在 worktree 分支提交; 部署按 docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md 走用户字 + 锚小时外 ff-only。
- **Confidence:** VERIFIED (quote+receipt opened; safe_commit.sh L23–29 read) · **Quote re-verified at assembly:** exact

### M5-04 · P1 · DOC_STALE
- **Source:** `memory/bash_cwd_persists_use_absolute_paths.md:8`
- **Quote:** 「④ 实盘仓唯一通道 `ops/safe_commit.sh`, 连 docs 也不例外。」
- **Superseding evidence:**
  - `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md:16` — 「⚠ **隐式部署陷阱(VERIFIED 读 `ops/safe_commit.sh` L23–28)**: safe_commit 在运行目录被调用时先 `git fetch origin main`, 落后就 `git rebase origin/main` ⇒ **下一次在 `~/dl_quant_live` 跑 safe_commit 会把 b681ca5 一并带入并推送 = 没人裁定的部署**。」
  - `docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md:143` — 「6. **合并 ≠ 部署**; 运行目录只经明做的 `pull --ff-only` 或 safe_commit 切换; safe_commit 自带 rebase = 隐式部署 ⇒ 部署未裁定期间禁在运行目录 safe_commit。」
- **A reader could wrongly conclude:** A reader commits a doc to ~/dl_quant_live via safe_commit, as the rule says, and unknowingly deploys pending executor commits into live trading.
- **Affects:** live_trading · **Severity reason:** A docs-only commit through safe_commit in the run directory during a merged-but-undeployed window rebases onto origin/main and deploys executor code nobody ruled on.
- **Proposed correction (exact text):** ⚠ 补充(2026-09-13 审计): ④ 仍成立, 但有前置条件 —— safe_commit 在运行目录会 fetch + `git rebase origin/main` 再推送(隐式部署, RUNBOOK_deploy_executor_b681ca5 L16)。跑之前先确认 `git -C ~/dl_quant_live rev-list --count HEAD..origin/main` 为 0; 否则(合并 ≠ 部署、部署未裁定)禁在运行目录 safe_commit, docs 也一样, 改在 worktree 分支提交。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-10 · P1 · DOC_STALE
- **Source:** `memory/onboarding_doc_for_new_researcher.md:3`
- **Quote:** 「docs/ONBOARDING_independent_researcher_2026-09-06.md = 面向独立研究同事的全环节+易错点总览(635 行); 易错点 16 族是主干; 新人问"这个项目怎么回事/哪里容易错"先给这份」
- **Superseding evidence:**
  - `docs/ONBOARDING_independent_researcher_2026-09-06.md:203` — 「- 复验一律用 `CAL=log`(= 原始 y4 = 无偏简单口径)。」
  - `docs/ONBOARDING_independent_researcher_2026-09-06.md:555` — 「## §9 当前已知缺陷清单(截至 2026-09-06)」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:196` — 「- **今后回放报数一律以 (iii) 交易所窗口口径为主口径**(记账窗 (N, N+4h], 复利), (i) 只作面板对照;」
  - `docs/REVIEW_caliber_final_2026-09-04.md:130` — 「2. **"CAL=log 腿级 0.05 bps 内无偏"被驳**: 同窗 fund 腿 raw−Π = +0.10/+0.11/+0.27(2024on +0.146, se 0.047, t≈3.1; R-C2.1/R-C2.2); rev24 −0.02/−0.07/−0.13; 只对 king(−0.08/−0.01/+0.09)与 F10(−0.00/−0.09/+0.09)成立。名级 Σ−Π 系统性为正(+0.23~+0.73 bps, 窗内负自相关), 腿级只靠零和权重抵消。」
  - `STATE.md:128` — 「> **★ 09-09 v4 口径正典已写入 RUNBOOK_2026-10 §v4(缓存 holefix2+覆盖门 v2 / king clamp 构建器 / 原始收益记账目标 / legs 在役策略禁全行重算 / 导出 env 逐字 / FIX7 / 判官先复现):**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:57` — 「- **口径**: 记账 y4s = Π(1+r)−1(禁从 5m 缓存重算收益, ret5 通道裁剪 ±0.30);」
- **A reader could wrongly conclude:** A new researcher handed this doc first validates on CAL=log (panel y4 Σ-simple [E,E+47]) and treats Σ-simple as an unbiased proxy. They miss the v4 RAW accounting canon, the ret5 ±0.30 clip trap, holefix2 and the defects logged since 09-08 (E-0908-B/D, E-0909-A..H, E-0910-A, E-0912-A/B).
- **Affects:** future_eval, future_retrain · **Severity reason:** The note routes every new researcher first to a doc last edited 09-07 whose caliber rule (validate on CAL=log; Σ-simple as unbiased proxy) was superseded by the (iii)/v4 RAW accounting canon, which would mislead evaluation and retrain work.
- **Proposed correction (exact text):** ⚠ 过期提示(2026-09-13 审计): 该文档最后修改于 2026-09-07(现 647 行), 未吸收 09-05 起的口径更正与 09-09 v4 正典: 其 §3「复验一律用 CAL=log」「Σ简单是 Π(1+r)−1 的无偏代理」已被 RESULT_f10_caliber_sensitivity L196((iii) 记账窗复利为主口径)、REVIEW_caliber_final L130(fund 腿偏差被驳)与 RUNBOOK_monthly_retrain_2026-10 §v4(记账 y4s = Π(1+r)−1, 禁从 5m 缓存 ret5 重算)取代; §9 缺陷清单截至 09-06。交给新人时必须同时给 STATE.md 最新横幅 + RUNBOOK_2026-10 §v4 + ERROR_LEDGER E-0908 起各条, 并注明本文 §3/§9 已过期, 直到该文档更新。
- **Confidence:** VERIFIED (quote+receipt opened; git log shows last doc commit 67ee8250 on 2026-09-07) · **Quote re-verified at assembly:** exact

### MK-01 · P1 · DOC_STALE
- **Source:** `memory/wide_book_candidate_v2main_norev24.md:3`
- **Quote:** 「当前最佳回放形态(候选, 未部署) = 在役宽书 去掉rev24腿 + king腿45%混入V2MAIN深度模型; 三种子全显著 +0.29~+0.43 bps/锚」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027).」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「**The 08-26 yearly claim "candidate ≥ in-role in every year" reverses for 2025**」
  - `STATE.md:111` — 「④ combo 选型复测: 排序保住、不显著、增益来自去 rev24、V2MAIN ≈0、2025 反转。」
- **A reader could wrongly conclude:** The live form is an undeployed candidate with significant gains in all three seeds, awaiting re-validation.
- **Affects:** future_eval, reporting · **Severity reason:** The index labels this note 在役书 and the banner says 待复验, but the re-validation happened on 09-04 (combo_recheck) and changed significance, attribution and the 2025 sign; the note never recorded the outcome.
- **Proposed correction (exact text):** description 改为: "在役书(08-26 04Z 上线)= 去 rev24 腿 + king 腿 45% 混入 V2MAIN; 08-26 回放「三种子全显著 +0.29~+0.43」为 CAL=simple 作废口径; 正确口径复测(retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md, 09-04): 排序保住, s42 显著性不保(D−A +0.108 [−0.101,+0.312] log / +0.203 [−0.022,+0.439] 复利), 归因反转(V2MAIN 单独 ≈0; 唯一 CI 排零 = 去 rev24), 2025 反转; 本条保留定义/复现命令/陷阱"; L8 横幅「待复验」改为「已复验(combo_recheck 09-04), 结果见 description」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### MK-02 · P1 · DOC_STALE
- **Source:** `memory/wide_book_candidate_v2main_norev24.md:52`
- **Quote:** 「- 回滚 = kill 守护 PID(下一锚自动 king 形态)。切换代价实测 2.4% gross。」
- **Superseding evidence:**
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/ERROR_LEDGER_2026-08-20.md:384` — 「4833 是 launchd `com.hsy.shadowloop`(KeepAlive)在 kill 后 ~1s 内重生的新进程」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:10` — 「  RESULT kill: RESPAWNED old=21206 new=21332 => kill is NOT a rollback」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:15` — 「  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback」
- **A reader could wrongly conclude:** Killing the combo daemon PID reverts to the king form.
- **Affects:** live_trading · **Severity reason:** Memory copy of the rollback verb that the lead's drill disproved; memory is read at session start before STATE.
- **Proposed correction (exact text):** - 回滚 = `launchctl bootout gui/$(id -u)/com.hsy.combolive`(临时; 持久再加 `launchctl disable …`; 恢复 = `launchctl enable …` + `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`)。08-30 起 launchd KeepAlive, kill PID 会 1 s 内被拉起, 不是回滚(演练收据 docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log; STATE §1)。切换代价实测 2.4% gross。
- **Confidence:** VERIFIED on a dummy launchd job with the same plist shape (lead drill2 receipt); not exercised on the live combolive job · **Quote re-verified at assembly:** exact

### MK-03 · P1 · DOC_STALE
- **Source:** `memory/milestone_2026_08_26.md:12`
- **Quote:** 「回滚=kill combo daemon PID。」
- **Superseding evidence:**
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/ERROR_LEDGER_2026-08-20.md:384` — 「4833 是 launchd `com.hsy.shadowloop`(KeepAlive)在 kill 后 ~1s 内重生的新进程」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:10` — 「  RESULT kill: RESPAWNED old=21206 new=21332 => kill is NOT a rollback」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:15` — 「  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback」
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
- **A reader could wrongly conclude:** Rollback is killing the daemon PID; the live book is 77/13/10.
- **Affects:** live_trading, reporting · **Severity reason:** Session-start memory for the live book carries the disproved rollback verb and the 77/13/10 composition.
- **Proposed correction (exact text):** 回滚 = `launchctl bootout gui/$(id -u)/com.hsy.combolive`(08-30 起 launchd KeepAlive, kill PID 不是回滚; 见 STATE §1)。description 中「(77%fund/13%king/10%DL)」改为「(08-26 构成 77/13/10; 席位逐锚滚动, 09-13 12Z ≈62/21/17)」; 「执行器 N+23 读」改为「N+24 读」
- **Confidence:** VERIFIED on a dummy launchd job with the same plist shape (lead drill2 receipt); composition from ~/regime_dash/REGIME_DASH.md · **Quote re-verified at assembly:** exact

### MK-04 · P1 · DOC_STALE
- **Source:** `memory/fund_leg_is_the_book.md:3`
- **Quote:** 「腿消融终审 —— 去 fund 书由 +1.31 变 −1.73(夏普 2.18→−2.49, 4/4年); king 在净额轴擦零但夏普轴显著」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:58` — 「| 全周期 post-warm | 9139 | **0.46171** | — | 0.21 | 2.20× | — |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:55` — 「| 2024 | 2196 | **0.7100** | 0.8108 | 0.21 | **3.38×** | 0.007 |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:79` — 「k=0.00 **0.629/0.629** | k=0.21 0.484/0.485 | k=0.2572 0.420/0.407 | k=0.3568 0.343/0.402 | k=0.4617 0.359/0.414 | k=0.5338 0.358/0.501 | **dyn 1.415/1.437**」
  - `docs/REVIEW_caliber_final_2026-09-04.md:134` — 「腿级偏差(同窗, bps/锚 2024/25/26): king −1.03/−2.44/−3.14; rev24 −0.75/−1.53/−1.98; fund +0.30/+0.74/+0.88」
- **A reader could wrongly conclude:** The book is essentially the fund leg; a fund-only book is nearly as good and model legs only dampen variance.
- **Affects:** future_eval, reporting · **Severity reason:** The seat ladder on the v4 device (r5 ANGLE 1) is the re-measurement the banner waits for: a fund-only book reaches Sharpe 0.63 against 1.42 for the dynamic two-leg book, and the 'fund-only Sharpe 2.02, could overtake the book' live lead is contradicted; the expm1 caliber had biased king 1–3 bps/anchor low.
- **Proposed correction (exact text):** description 改为: "腿消融(08-25, CAL=simple 作废口径)曾判「去 fund 由盈转亏、fund=书本体」; ⚠ v4 口径席位阶梯(uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md): 纯 fund 固定书全周期 Sharpe 0.63 vs 动态两腿 1.42, 动态席位 king 均权 2024/2025 0.71、全周期 0.46 ⇒ 书的收益一半以上来自两腿间席位择时; 2022–23 king 缺席时书才等于 fund 腿; 「仅 king 单腿亏钱」未在 v4 复测"; L16「副产品活口」加注「⚠ v4 纯 fund 书 Sharpe 0.63, 活口不成立」; L8 横幅改为「已部分复验(r5 ANGLE 1), 腿层消融本身未在 v4 重跑」
- **Confidence:** VERIFIED for the seat ladder; king-only and drop-fund ablations OPEN_NOT_MEASURED on v4 · **Quote re-verified at assembly:** exact

### MK-05 · P1 · DOC_STALE
- **Source:** `memory/model_leg_leverage_cap_by_seat.md:3`
- **Quote:** 「书里模型腿席位≤0.21(实盘)/0.01(回放2026) ⇒ 模型侧任何改动对书层净额杠杆≤0.21×」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:58` — 「| 全周期 post-warm | 9139 | **0.46171** | — | 0.21 | 2.20× | — |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:55` — 「| 2024 | 2196 | **0.7100** | 0.8108 | 0.21 | **3.38×** | 0.007 |」
  - `~/regime_dash/REGIME_DASH.md:16 (generated 2026-09-13T12:50:02Z)` — 「- 席位(掩码后) king 0.382 / fund 0.618」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:12` — 「| 2025 | **+0.359** | +1.223 | **1.15** / 3.37 | −294 (12) | 418 / 647 | 0.67 / 0.48 |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:42` — 「⇒ **0.21 是一个已知缺陷态下、单日测得的快照**; 同一规则修好后落在 0.30–0.36。」
- **A reader could wrongly conclude:** Model-side improvements move the book by at most 0.21×, so the F-10 objective/architecture DNR cannot reopen.
- **Affects:** future_eval, future_retrain · **Severity reason:** The cap is used to rule model-side research below resolution and to set the reopen precondition 'model-leg seat ≥0.4'; the live seat is 0.382 today, the v4 replay seat averages 0.46 (0.71 in 2024–25), and 0.21 was a defect-state snapshot.
- **Proposed correction (exact text):** description 改为: "模型腿席位随 msharpe 逐锚滚动, 不是 ≤0.21: 实盘 2026-09-13 12Z king 席位 0.382(09-05 播种前 0.19–0.22 属缺陷态快照); v4 回放动态席位 king 均权 2024 0.71 / 2025 0.71 / 2026 0.36 / 全周期 0.46(RESULT_r5_angle1_fixed_seat); 模型侧改动的书层机械杠杆 ≈ 席位(0.36–0.71), 不是 0.21×"; L15「重开前置 = 模型腿席位 ≥0.4」加注「⚠ v4 回放全周期 0.46、冻结窗 0.53 已满足; 实盘 0.38 接近 —— F-10 目标/架构层 DNR 的重开条件需按此重议(用户裁定)」; L8 横幅改为「已复验并推翻(r5 ANGLE 1 / regime_dash)」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### M1-08 · P2 · DOC_STALE
- **Source:** `memory/passive_reversal_book_cost_undecidable_fill_selection_gap_2026_09_13.md:28`
- **Quote:** 「requote/reprice family double-vetoed, DO-NOT-RETRY」
- **Superseding evidence:**
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:6` — 「08-05 纸面否决所用的两项输入(未成交重挂成本 −40 bps、p* 85.6%)与实盘不符。**读法: 不有害, 期望为正但幅度在实盘数据上定不出来(±10 bps); 不建议撤回」
  - `STATE.md:162` — 「重挂随机实验已上线(09-05 11:48Z」
  - `/Users/haosiyu/dl_quant_live/config/book.json:124` — 「"p_requote": 0.5,」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:95` — 「重挂实验 p **0.5**」
- **A reader could wrongly conclude:** A reader closes execution research on requoting/repricing as DNR and misreads the live requote/direct arms (which appear in T3's own ledger) as residue of a vetoed idea, pre-empting the 09-19 randomised readout.
- **Affects:** future_eval · **Severity reason:** The lead reading (written 'after checking the latest receipts') cites an 08-11 DO-NOT-RETRY for the requote family although requote has run live since 08-06, its 08-05 veto inputs were found not to match live, and a randomised requote experiment is live with a pending readout.
- **Proposed correction (exact text):** Replace "requote/reprice family double-vetoed, DO-NOT-RETRY" with "its 'requote/reprice double veto, DO-NOT-RETRY' is superseded for post-only-reject requotes: requote has run live since 08-06, the 09-05 live causal check found the 08-05 paper-veto inputs do not match live (UNDECIDED, expected positive, not withdrawn), and a randomised requote/direct experiment is live since 09-05 (p_requote 0.5, single readout ≥ 09-19) — RESULT_requote_and_behind_live_causal_2026-09-05 L6, STATE.md 09-05「重挂随机实验已上线」条".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-09 · P2 · DOC_STALE
- **Source:** `memory/objective_ammunition_interaction.md:3`
- **Quote:** 「一切以 CAL=simple + V2=1 的干净装置为准」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:3` — 「回放装置 CAL=log(=原始 y4=Σ5m简单收益) vs CAL=simple(expm1, 伪凸性)」
  - `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/REPORT.md:9` — 「Under the correct calibers V2MAIN alone is ≈0 (C−A +0.005 log / +0.079 compounded, P 0.50 / 0.79)」
  - `docs/RESULT_phi_grid_2026-09-05.md:9` — 「向下 φ 0.25 显著变差(-0.154 [-0.294,-0.013] / -0.186 [-0.328,-0.043], 双种子 CI<0)」
  - `docs/REVIEW_caliber_final_2026-09-04.md:482` — 「排序保住, 显著性不保, 归因反转(去 rev24 CI>0, V2MAIN≈0), 2025 反转」
- **A reader could wrongly conclude:** A reader cites 'V2MAIN φ.45 blend 3/4 significant', 'LGBM171 swap negative' or '2×2 interaction +0.451' as clean-caliber facts; under correct calibers the V2MAIN-only blend is ≈0 and LGBM171/2×2 have no unbiased or v4 re-measurement.
- **Affects:** future_eval, reporting · **Severity reason:** The note (no ⚠ flag) names CAL=simple — the biased expm1 caliber of E-0904-F — as the clean device, so all its V2MAIN/LGBM171/2×2 numbers read as authoritative although the V2MAIN-only effect re-measured ≈0 and the rest was never re-measured.
- **Proposed correction (exact text):** 描述行末「一切以 CAL=simple + V2=1 的干净装置为准」改为: "⚠ E-0904-F(2026-09-04): CAL=simple 是对 Σ简单 y4 再 expm1 的伪凸性口径, 不是干净口径, 本条全部数字为该口径历史数。已复验: 只混 V2MAIN(保留 rev24)在正确口径下 ≈0(combo_recheck: C−A +0.005 log / +0.079 复利, 不显著); 在役形态内 φ 剂量按记账口径复验 φ 0.45 保持(RESULT_phi_grid 09-05: φ 0.25 对 0.45 −0.154 [−0.294,−0.013] / −0.186 [−0.328,−0.043])。LGBM171 换 king 判负与 2×2 交互 +0.451 从未在无偏/v4 口径复测"
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-10 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/king_skill_is_short_side_seat_multiplier_fails_turnover.md:3`
- **Quote:** 「空侧king席位×κ 在回放逐年全正但在实盘席位(0.21)下换手+15%~+128%破门 ⇒ 轴关闭」
- **Superseding evidence:**
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:11` — 「| 2024 | **+0.149** | +0.220 | **0.53** / 0.75 | −363 (04) | 795 / 586 | 0.64 / 0.44 |」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:50` — 「2024 fund 腿为负时动态席位把 king 提到 0.64」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:83` — 「席位 king 均权 0.6241 → 0.6190」
- **A reader could wrongly conclude:** A reader treats the short-side king seat multiplier as closed and uses 'reopen only if king seat ≤0.1' as the gate, although the live masked king seat is 0.382 and the rule seat on correct calibers is 0.36–0.67, so the turnover arithmetic behind the closure was never redone.
- **Affects:** future_eval · **Severity reason:** The E-0904-F flag voids the seat/leg verdicts but the headline still closes the axis on a 'live seat 0.21' premise that no longer holds, and no unbiased/v4 re-measurement of the side-asymmetric κ arms exists (searched docs/ and uplift RESULTs after 09-04).
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本轴从未在无偏/v4 口径复测(docs 与 uplift 各轮 RESULT 无侧向席位 κ 臂)。前提「实盘席位 0.21」已不成立: 09-05 席位播种后实盘掩码 king 席位 09-13 12Z = 0.382(REGIME_DASH), 无偏口径规则席位 2024/25/26 king 0.64/0.67/0.36, v4 回放 A0 2024+ king 均权 0.62;「重开条件 = king 席位 ≤0.1」基于旧席位。在当前席位路径与 v4 口径重算换手门之前, 不得引用「轴关闭」或「换手 +15%~+128%」作结论。
- **Confidence:** VERIFIED (quote+receipt opened); not-measured status INFERRED from a search of docs/ and uplift RESULT .md files after 09-04 with no side-seat κ arm found · **Quote re-verified at assembly:** exact

### M1-11 · P2 · DOC_STALE
- **Source:** `memory/clip_compound_label_defect_2026_09_08.md:30`
- **Quote:** 「以及我方已测的传导上限(分数→权重保留 17.5%, 模型腿席位 ≤0.21), 「修标签换收益」从一开始就是错的期待方向。」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:50` — 「2024 fund 腿为负时动态席位把 king 提到 0.64」
  - `docs/RESULT_live_form_health_check_2026-09-05.md:41` — 「A 表的席位是规则算出来的:2024 下半年 king 占 0.92、2025 占 0.74、2026 占 0.38」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
- **A reader could wrongly conclude:** A reader dismisses model-leg label or feature fixes as unable to matter because the model leg is capped at a 0.21 seat, while the rule seat is 0.36–0.92 by year and the live masked king seat is 0.382.
- **Affects:** future_retrain, future_eval · **Severity reason:** The 'model-leg seat ≤0.21' cap was a live seat depressed by stale 08-16 bundle rows under the biased caliber; using it as a transmission ceiling understates what model-label fixes can move.
- **Proposed correction (exact text):** …以及我方已测的传导上限(分数→权重保留 17.5%; ⚠「模型腿席位 ≤0.21」已作废: 那是 09-04 前被 08-16 旧 bundle 行压低的实盘席位读数, 规则席位在无偏口径 2024/25/26 为 king 0.64/0.67/0.36(体检 A 表 0.92/0.74/0.38), 09-05 播种后实盘掩码 king 席位 09-13 为 0.382), 「修标签换收益」的期待不能再以 ≤0.21 为上限论证。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-12 · P2 · DOC_STALE
- **Source:** `memory/clip_compound_label_defect_2026_09_08.md:36`
- **Quote:** 「全史 **+0.6474 / S 1.31 / maxDD 41.49% / 最差日 −6.04%** → **+0.6041 / 1.20 / 44.87% / 最差日 −11.21%**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:10` — 「the first 900 anchors (2022-01-31 .. 2022-06-29) now run `w3 = [0.5, 0, 0.5]` instead of `[1/3, 1/3, 1/3]`」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:57` — 「day return at 2.0× **−11.17 % → −6.40 %**」
  - `multi_asset/exports/research/retrain_2026-09/health_check_2026-09-05/w10_health.py:164` — 「if p < LOOK: return np.array([1/3]*3)」
  - `multi_asset/exports/research/retrain_2026-09/clip_and_gap_2026-09-08/clip_risk.py:8` — 「health_check/dev_alt/probe_artifacts/w10_ablation_series_%s.npz」
- **A reader could wrongly conclude:** A reader quotes a −11% full-history worst day at 2× as the clip-corrected tail, when after the warm-up fix the same 2022-06-07 day is −6.40% on A0 and the full-history 2× tail is maxDD −43.9%/−44.5%.
- **Affects:** reporting, future_eval · **Severity reason:** The headline tail restatement (worst day −11.21%, 'the full-history worst day doubled from this anchor') sits in the warm-up segment where the device ran an equal-weight book including rev24, which r18 removed; it overstates the worst-day tail used in risk communication.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计(r18 WU 暖机修复, 2026-09-12): 回放前 900 锚(2022-01-31..06-29)装置在 LEGS 掩码前返回 [1/3,1/3,1/3], 跑的是含 rev24 的另一本书(本表所用 health_check `w10_health.py` L164 同一行); 修后 A0 在 2022-06-07 的 2.0× 日收益 −11.17% → −6.40%。故本节「最差日 −11.21%」与「全史最差日翻倍就来自这一锚」主要是暖机段伪影, 不再引用; 全史尾部改引 r18 NW 固定 2× 复利阶梯(maxDD −43.9%/−44.5%, 最差日 −6.40%); CRYPTO 体检臂未按该修复重跑。
- **Confidence:** VERIFIED (quote+receipt opened); transfer of the r18 fix magnitude to this CRYPTO health-check arm INFERRED (same w10_health warm-up line L164 and same 2022-06-07 anchor; arm not re-run) · **Quote re-verified at assembly:** exact

### M1-13 · P2 · DOC_STALE
- **Source:** `memory/caliber_program_three_tracks_2026_09_09.md:12`
- **Quote:** 「风险数字(最差日 −11.17%)不变」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:57` — 「day return at 2.0× **−11.17 % → −6.40 %**」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:10` — 「the first 900 anchors (2022-01-31 .. 2022-06-29) now run `w3 = [0.5, 0, 0.5]` instead of `[1/3, 1/3, 1/3]`」
- **A reader could wrongly conclude:** A reader keeps −11.17% as the canonical 2× worst day for risk, stop-line or leverage discussions.
- **Affects:** reporting · **Severity reason:** The note asserts the −11.17% worst day is unaffected, but r18 showed that exact figure is a warm-up-book artefact (−6.40% after the fix), so the 'unchanged risk number' is wrong.
- **Proposed correction (exact text):** 风险数字(最差日 −11.17%)不变 ⚠(2026-09-12 r18 更正: −11.17% 来自暖机段——前 900 锚在 LEGS 掩码前返回等权、含 rev24 的另一本书; 修后全史 2.0× 最差日 2022-06-07 为 −6.40%, W_TAIL 尾部阶梯作废, 尾部以 r18 NW 阶梯为准)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-14 · P2 · DOC_STALE
- **Source:** `memory/wide_book_fullhist_oos_2020.md:3`
- **Quote:** 「2022熊市+0.70/2023+0.33 无亏损年(king是2022-24主引擎, funding是2025-26主引擎); §28 ADOPT_FOR_V2(+0.35夏普)」
- **Superseding evidence:**
  - `docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md:8` — 「2022 +0.8% / **2023 −13.7%(负年)** / 2024 +12.3% / 2025 +16.7% / 2026→08-10 +81.7%」
  - `docs/ERROR_LEDGER_2026-08-20.md:430` — 「E-0905-A · 08-21 已判采纳的"king 训练集前伸至 2020"在 09-01 重训未执行, 无裁定记录(2026-09-05 发现)」
  - `docs/ERROR_LEDGER_2026-08-20.md:431` — 「在役 booster(8d79186b)训练集 = 2022-01→2025-12」
  - `docs/REVIEW_caliber_final_2026-09-04.md:484` — 「2024→ Sharpe 2.83 vs 2.01; 差在 king 来源(E-0905-A)」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:40` — 「| A0 post-warm + E-0911-D 截断(第八轮第一手) | 1.2912 | 9138 | 0.4895 | [0.332, 2.251] |」
- **A reader could wrongly conclude:** A reader believes the live wide book has had no losing year since 2022, a 2.77–3.06 book Sharpe, and a 2020-extended king in service; the live booster is trained 2022-01→2025-12, 2023 is −13.7%/gross on v4 and the honest full-cycle Sharpe is 1.29 [0.33, 2.25].
- **Affects:** reporting, future_retrain · **Severity reason:** The description presents an undeployed 08-21 three-leg instrument (2020-trained hist king, rev24) as the wide book's history and an adopted change, while the adoption was never executed and the in-service form has a negative 2023 and full-cycle Sharpe 1.29 on v4.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本条是 08-21 三腿宽书(含 rev24、2020 起训练的 hist king)的单仪器读数, 不是在役形态。§28 ADOPT_FOR_V2 在 09-01 重训**未执行**(E-0905-A: 在役 booster 8d79186b 训练集 2022-01→2025-12; 待 jpline 恢复后按正确口径重判); 同口径两仪器 2024→ Sharpe 2.83(hist king)vs 2.01(生产 king)。在役 combo 形态 v4 口径逐年 2023 为负年(−13.7%/gross), 全周期夏普 1.2912 CI95 [0.332, 2.251](CLOSEOUT §2/§7)。「无亏损年 / 书级夏普 2.77 / 止损后 3.06」不得作为在役书历史或规划数引用。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-15 · P2 · DOC_STALE
- **Source:** `memory/universe_mechanism_frozen_cost_and_fund_rank_base.md:3`
- **Quote:** 「fund 腿归一基对全市场排名 +0.06~+0.09(双种子双口径 CI>0); 推荐三件套 M1/M2/M3」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:47` — 「| M1+T400(秩基变宽+成交集 400) | −0.057/−0.16 | −0.086/−0.07 | +0.181/+0.34 | **−0.009/+0.09** | 整体中性, 只在 2026 正 |」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:125` — 「Redone at v4 and the fitted cost on the LIVE seat, 2024on: A0 1.0271 -> STALE1 0.7754」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:93` — 「My `NOYOUNG90` reads **dSharpe -0.390/-0.383**」
- **A reader could wrongly conclude:** A reader cites a significant +0.06–0.09 gain from the deployed rank-base widening or recommends M2/M3 on that basis; the unbiased 2024→26 M1+T400 effect is −0.009 (not significant), and the refresh case now rests on r5's v4 staleness curve.
- **Affects:** future_eval · **Severity reason:** The flagged note keeps the CAL=simple rank-base gain '+0.06~+0.09 CI>0' and the M1/M2/M3 recommendation in its headline although the unbiased re-measurement found M1(+T400) neutral and voided its deployment basis; only the frozen-list-cost direction is re-supported at v4.
- **Proposed correction (exact text):** ⚠ E-0904-F 复验已出: 秩基变宽 M1(+T400)在无偏口径 2024→26 Δ −0.009(Sharpe +0.09), 不显著, 部署依据作废(RESULT_caliber_revalidation L47/L52), 「+0.06~+0.09 CI>0」作废。冻结名单代价在 v4 口径由 r5 NEW DATA 3(09-11)复测, 方向相同且更大(W3FIX 固定席位 2024on Sharpe: 新鲜 1.027 → 陈旧 1 月 0.775 → 3 月 0.363 → 6 月 −0.050 → 12 月 −1.562); 排除上市<90 天名 v4 dSharpe −0.390/−0.383。M2/M3 仍需预注册+用户字, 依据改引 r5。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-16 · P2 · DOC_STALE
- **Source:** `memory/young_listings_carry_fund_alpha.md:3`
- **Quote:** 「上市<90天的名 fund 腿 IC 是老名 3-4×(2026 +0.086 vs +0.024)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:144` — 「## 3. New listings specifically — the receipt does not reproduce, and the sleeve dies」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:151` — 「| 2026 | <90d | 9.9 | $1.01M | 5.16% | **+0.0044** |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:152` — 「| 2026 | >2y | 117.1 | $1.24M | 3.32% | **+0.0163** |」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:156` — 「The **deep-negative funding concentration is real in 2025 (3.3x)** and weaker in 2026 (1.55x).」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_newdata3_universe_2026-09-11.md:157` — 「young names carry LOWER fund IC than mature ones in 2025 and 2026 on this grid」
- **A reader could wrongly conclude:** A reader prioritises a new-listing tilt or sleeve because 'the fund engine's best names are new listings'; on the device grid young names have lower fund IC (2026 +0.0044 vs +0.0163), the age sleeve lost to a time-shifted null, and deep-negative concentration is only 1.55× in 2026.
- **Affects:** future_eval · **Severity reason:** The headline mechanism (new listings carry 3–4× the fund-leg IC) was re-measured on the v4 device grid and did not reproduce, yet still steers universe/refresh priorities toward new listings.
- **Proposed correction (exact text):** ⚠ r5 NEW DATA 3(2026-09-11, v4 口径, 装置自身评估网格 + A0 成员 + 实盘流动性门)复测**未复现**: 2026 上市<90 天 fund 秩 IC +0.0044 vs >2 年 +0.0163(2025 +0.0080 vs +0.0130), 新名 IC 反而更低; 深负费率集中度 2025 为 3.3× 属实、2026 仅 1.55×; 新上市倾斜臂 SL_AGE50 dg CI 0/4 格排零且输给平移 101 锚零假设(静态暴露非预测)。本条 IC 数字出自 jpline B 面板与不同合格规则, 与装置网格不是同一量, 不再作为「fund 引擎最好的名是新上市」引用; 月度刷新的依据改引 r5 陈旧度曲线。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-17 · P2 · DOC_STALE
- **Source:** `memory/live_giveback_root_cause_2026_09_09.md:3`
- **Quote:** 「机制 = 急涨里资金费动量多头半区跑输指数 + 单名崩(止损日全多头) + FTRIM 只砍信号不砍暴露(半衰期 5 锚, −1.7k); 执行非因」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:9` — 「**连「价格边下降了」本身都不显著**, 所以任何「为什么下降」的判决都无从成立」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:13` — 「落差本身不显著: 2026-08 相对 2026-H1 价格 −4.85 bps, 判决区间 [−13.38, +3.67]」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:24` — 「**缺口在资金费腿的空头半区的价格上, 不在 carry, 不在 king/V2MAIN 腿。**」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:20` — 「| 价格 alpha | −0.022 | 4.018 | −0.01 | **统计上就是零** |」
  - `STATE.md:60` — 「#55: 测的是**持仓排序 vs 下锚价格排序**, 不是模型 IC、不是净收益」
  - `docs/PREREG_deploy_sigma_ladder_2026-09-04.md:27` — 「## 6. 撤回激活(2026-09-04 09:5xZ)— 阶梯转为备用, 执行器代码保留(惰性)」
- **A reader could wrongly conclude:** A reader treats 'funding-momentum long half lags the index in rallies' as the proven cause of the live giveback and designs C1/C3 book changes on it, or cites ic_monitor DECIDE as mechanism evidence, although the drop is statistically indistinguishable from noise and #55 measures holding rank vs next-anchor price rank.
- **Affects:** future_eval · **Severity reason:** The description still states a settled root-cause mechanism (and 'execution not a cause', withdrawn in the note's own L16) although the later pre-registered T1 found the price-edge drop itself not significant and every mechanism hypothesis undecidable; its candidate C1 modifies a σ_fund ladder that is not in service.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本条是事后分解, 不是已判根因。T1(09-13, v4 口径, 预注册)下「价格边下降」本身不显著(2026-08 对 2026-H1 −4.85 bps, 判决区间 [−13.38, +3.67]), H1/H3/H4/H5 全部不可判, 点估计线索是 fund 腿空头半区价格(线索, 未判决); combo 期价格 alpha −0.022(t −0.01), 唯一显著项是资金费拖累(CLOSEOUT §1)。描述行的「执行非因」已由本条 L16 撤回, FTRIM 半衰期应为 6.58 锚; ic_monitor #55 测的是持仓排序对下锚价格排序(非模型 IC、非净收益), 不能作机制证据; C1 所改的 σ_fund gross 阶梯已于 09-04 09:5xZ 撤回为备用(不在役)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-18 · P2 · DOC_STALE
- **Source:** `memory/slow_book_alpha_low_dim.md:23`
- **Quote:** 「**任何去集中/去风格/档中性提案引用即拒。**」
- **Superseding evidence:**
  - `multi_asset/exports/eda/RESULT_volstructure_family_2026-08-10.md:3` — 「> **作废条件:** 在役 risk_budget(α.5 λ1)变更 ⇒ 全文重测」
  - `multi_asset/exports/eda/RESULT_volstructure_family_2026-08-10.md:19` — 「## 2. M1 全史测量(9821 锚, 在役栈 EMA α.3 + 中性带 b.002 之上)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:83` — 「或做有符号/止损/上限约束的投影」
- **A reader could wrongly conclude:** A reader rejects cap / constraint-projection / de-concentration work on the current fund-momentum book (including the reviewer-suggested signed/stop/cap-constrained projection) by citing an instrument built on the retired smaller DL book.
- **Affects:** future_eval · **Severity reason:** A standing reject-on-sight DNR for de-concentration/de-style/bucket-neutral proposals rests on an 08-10 receipt whose own invalidation clause (in-service risk_budget change) fired with the 08-26 switch to the wide combo book and was never re-measured on A0 v4.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本 DNR 的受据 RESULT_volstructure_family_2026-08-10(9821 锚, 在役栈 EMA α.3 + 中性带 b.002 之上的旧 DL 书)自带作废条件「在役 risk_budget(α.5 λ1)变更 ⇒ 全文重测」; 在役书已于 08-26 换装为宽宇宙 combo(fund 动量主导), 条件已触发且从未在 A0 v4 上重测; 同属 9821 锚离线仪器的「78% 主导率保费」已被 T8 证明不能迁移到 A0 v4。故「引用即拒」只作历史; 对现书的去集中/上限/约束投影提案须在 A0 v4 上配对重测后再判(宇宙已扩至 450, #63 的前置条件已被部署事实越过)。
- **Confidence:** VERIFIED (quote+receipt opened); that the 08-10 9821-anchor instrument and the 08-21 net_S1 instrument are the same offline family is INFERRED from matching anchor counts · **Quote re-verified at assembly:** exact (line moved 19->23)

### M1-19 · P2 · DOC_STALE
- **Source:** `memory/universe_crypto_only_caliber_arm_2026_09_08.md:38`
- **Quote:** 「@2× 算术 52.82/54.83 → **56.40/59.05**, CAGR 64.77/68.11 → **70.67/75.23**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97` — 「**A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「maxDD −43.9 % / −44.5 %」
  - `docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md:8` — 「**2023 −13.7%(负年)**」
- **A reader could wrongly conclude:** A reader plans on ~70% CAGR / Sharpe ~2.4 at 2× for the live book; the current v4 planning number is +27.8% NAV/yr at 2.0× with CI95 [+7.1%, +48.6%] and full-cycle Sharpe 1.29.
- **Affects:** reporting · **Severity reason:** The CRYPTO-arm levels (2026 Sharpe 5.3, 2024→26 Sharpe 2.3–2.4, @2× arithmetic 56–59%/yr, CAGR 71–75%) are pre-v4 health-check readings (clipped labels, warm-up defect, pre-E-0911-D) quoted without CI and on arithmetic ×2, and read like planning numbers.
- **Proposed correction (exact text):** ⚠ 2026-09-13 审计: 本节 2026 / 2024→26 水平、Sharpe、@2× 算术年化与 CAGR 均为 09-08 体检臂旧链读数(裁剪复利标签 E-0908-B、暖机缺陷、E-0911-D 覆盖截断修复之前), 无 CI 且按算术 ×2, 不得作为规划或实盘期望引用。现行规划数(v4 口径): A0 全周期 +0.6342 bps/锚 CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× +27.8% NAV/年 CI95 [+7.1%, +48.6%](CLOSEOUT §7); 回撤按固定 2× 复利 NAV(r18 NW 全史 maxDD −43.9%/−44.5%); v4 在役形态 2023 为负年。「CRYPTO 为默认引用臂」的用户裁定不变。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 17->38)

### M1-20 · P2 · DOC_STALE
- **Source:** `memory/reweighting_cannot_close_the_sharpe_gap_2026_09_12.md:28`
- **Quote:** 「复测 r17–r21(2026-09-12)全部落地后规划数仍 A1x 0.6602 / 1.2857(历史读数非期望), 无新候选晋级。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:127` — 「延展后 **A1x: mean g +0.6602, CI95 [+0.1673,+1.1472], Sharpe 1.2857**」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:131` — 「A0 在**新增的 61 个锚**上读 **mean g −3.8739**, CI95 [−12.1883, +3.5265]」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:133` — 「**§7 引用规划数时必须带这一句。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL)」
- **A reader could wrongly conclude:** A reader plans on g 0.66 / Sharpe 1.29 as a stable expectation, missing its CI95 [+0.167, +1.147] and that the only true out-of-sample reading is −3.87 bps/anchor.
- **Affects:** reporting, future_eval · **Severity reason:** The planning number is quoted without its CI and without the mandatory companion sentence the CLOSEOUT requires (the only out-of-sample reading, on the 61 extension anchors, is negative).
- **Proposed correction (exact text):** 复测 r17–r21(2026-09-12)全部落地后规划数仍 A1x mean g +0.6602 CI95 [+0.1673, +1.1472] / 夏普 1.2857(历史读数非期望; 按 CLOSEOUT A-2 规则引用规划数必须同时报: 覆盖延展后唯一的样本外读数 = A0 在新增 61 锚上 mean g −3.8739 CI95 [−12.1883, +3.5265], 与规划数统计上不可分辨但为负; 冻结窗高水平为候选全家族共有, 见 T6), 无新候选晋级。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-21 · P2 · DOC_STALE
- **Source:** `memory/seat_is_blind_to_the_funding_fuel_gauge_2026_09_12.md:22`
- **Quote:** 「**已知的、未对冲的**弱点(会给正在亏的腿加权)。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:321` — 「M3 **形式成立但幅度可忽略**(低−高 +0.011 [+0.007, +0.014]: 那两年书在任何状态下都是 98–99% fund 腿, king 腿恒 0, 席位没有可加码的余地)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:321` — 「四臂一致 **DOES NOT FIT**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:319` — 「| 2024..2026-H1 · 低 / 中 / 高 | 1203 / 1798 / 2471 | 0.15 / 0.30 / 0.62 | −1.66 / +2.67 / +3.26 | 0.43 / 0.36 / 0.52 | 0.33 / 0.27 / 0.43 | +0.71 / +0.91 / +1.59 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:131` — 「但书在每个状态都是 98–99% fund 腿, 席位根本没有加码空间」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:131` — 「撤回该读法」
- **A reader could wrongly conclude:** A reader builds a low-dispersion drawdown hedge or seat-rule change around a seat over-weighting mechanism that the book layer does not show (DOES NOT FIT on all four arms).
- **Affects:** future_eval · **Severity reason:** The note files 'the seat overweights the losing fund leg when dispersion is low' as a known unhedged weakness, but the book-layer check (T1 H5) found the seat has no room to overweight in 2022–23 and the opposite seat pattern in 2024–26-H1; the mechanism reading was withdrawn.
- **Proposed correction (exact text):** **⚠ 更正(T1 H5 书层核对 + 纲领 r2 AMENDMENT 3 更正 2, 2026-09-13):** 「席位在低离散度给正在亏的腿加权」在书层不成立: 2022H2∪2023(低离散度常见的唯一时期)king 腿恒 0, 书在任何状态都是 98–99% fund 腿, 席位加码幅度可忽略(低−高 +0.011); 2024..2026-H1 低离散度锚名义 w3_fund 0.33 反而低于高档 0.43, 书 g +0.71; H5 四臂 DOES NOT FIT, 该机制读法已撤回。本条只保留「corr −0.036 的描述性事实 + 9/9 倾斜臂零录取」, 不作为风险登记册中的已知弱点引用。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 12->22)

### M1-22 · P2 · PENDING_USER_DECISION
- **Source:** `memory/book_return_not_perceivable_t8_2026_09_13.md:18`
- **Quote:** 「Any added feature or model is a new family (T6 rule).」
- **Superseding evidence:**
  - `STATE.md:8` — 「**待用户裁定 4 项**: T6 录取规程」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:61` — 「1. T6 §11 候选录取规程是否采纳为今后录取门(本纲领先按它评估)。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:130` — 「**§11 的统计量与人口混了。**」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:179` — 「3. T6 §11 先冻结统计量和资格人口；撤回统一最低折价与已校准真值概率的说法。」
- **A reader could wrongly conclude:** A reader gates or rejects new-information candidates (OI, KRW premium, intra-anchor flow) with T6 §11 statistics as if adopted, including the withdrawn uniform −0.65/−1.56 haircuts and DSR 'probabilities'.
- **Affects:** future_eval · **Severity reason:** The note (L18 'T6 rule', L21 'every such candidate goes through the T6 admission protocol') cites T6 §11 as an adopted admission rule, while it is a proposal awaiting the user's ruling and the independent reviewer rejected adopting it verbatim as a hard gate.
- **Proposed correction (exact text):** Replace "Any added feature or model is a new family (T6 rule)." with "Any added feature or model is a new family; T6 §11's admission protocol is a PROPOSAL pending the user's ruling (STATE.md 2026-09-13 10:5xZ 第三纲领条; PROGRAM r3 §4 item 1), and REV4 §4.2 rejects adopting §11 verbatim as a hard gate (statistic and population mixed; freeze the statistic and eligible population first; the uniform −0.65/−1.56 haircut and DSR probabilities are withdrawn)." and in the lead addendum replace "goes through the T6 admission protocol" with "is evaluated against the T6 §11 proposal (not an adopted gate)".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-23 · P2 · DOC_STALE
- **Source:** `memory/v4_chain_retrain_2026_09_09.md:12`
- **Quote:** 「冻结窗 +1.89, Sharpe 3.0, maxDD 820 bps gross」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:41` — 「| **冻结窗 2025-03..2026-08-10** | **2.9357** | 3168 | 0.8314 | **[1.306, 4.565]** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL)」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97` — 「**A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」
- **A reader could wrongly conclude:** A reader takes Sharpe ≈3 as the in-service book's backtest level (and sizes leverage or targets on it), when it is not significantly above 3, is shared by the whole candidate family, and the planning number is full-cycle Sharpe 1.29.
- **Affects:** reporting, future_eval · **Severity reason:** A frozen-window 'Sharpe 3.0' is quoted as the in-service form's reference without its CI95 [1.306, 4.565], without the family-wide/selection caveat, and next to a gross-bps maxDD, which is exactly the number the CLOSEOUT says not to plan on.
- **Proposed correction (exact text):** 冻结窗 +1.89, Sharpe 3.0(=2.9357, CI95 [1.306, 4.565], 不显著高于 3; 冻结窗高水平为候选全家族共有(T6), 不可作规划; 规划数 = A0 全周期 +0.6342 bps/锚 CI95 [+0.1653, +1.1071] / 夏普 1.2912, 见 CLOSEOUT §7), maxDD 820 bps gross(回撤须按固定 2× 复利 NAV 报)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-24 · P2 · DOC_STALE
- **Source:** `memory/retrain_2026_09_first_run.md:11`
- **Quote:** 「acceptance 4/4(A2 中位 0.9999)」
- **Superseding evidence:**
  - `STATE.md:60` — 「② 旧 A2 是单步平价(`acceptance.py` L165 `H=ref`), 合成翻倍反例仍过 ⇒ **接受**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:23` — 「两代在役 booster(08-16 的 29ffaf58、09-01 的 8d79186b)**都是 v0 训练**(数据级识别)。错配在**同一个 bundle 导出器里分叉**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:177` — 「影子验收 A2 比对共享 0.9×H 的平滑权重, 对这类错配几乎无检出力」
- **A reader could wrongly conclude:** A reader treats the RUNBOOK gate set that passed on 09-01 as proof of train/serve consistency and reuses it unchanged for the October export.
- **Affects:** future_retrain · **Severity reason:** The 09-01 swap is recorded as fully gated ('全门绿', acceptance 4/4), but the A2 acceptance gate is a single-step parity that passes a synthetic doubling and missed that this very bundle trains col 80 on v0 and exports a v1 state.
- **Proposed correction (exact text):** acceptance 4/4(A2 中位 0.9999; ⚠ 2026-09-12/13: A2 是单步平价(H 每锚重置为参照, 合成翻倍反例仍过), 没抓到本 bundle 训练 v0/导出 v1 的第 80 列错配(4h 名 2×、1h 名 8×; T4)⇒「全门绿」不是训练/服务一致的证据)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-25 · P2 · DOC_STALE
- **Source:** `memory/x0910_fund_iv_interval_mismatch_2026_09_13.md:10`
- **Quote:** 「true interval = producer ledger iv (32,595 settlements) else snapped timestamp gap (5,837); ledger vs gap 0 disagreements.」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5dR/PREREG_ADDENDUM_T5dR_declared_interval_reconciliation_2026-09-13.md:7` — 「T5d 以生产者账本间隔(= 相邻结算时间差取整)为真值。FX-PROD 以 data.binance.vision 资金费 zip 的逐结算申报列 `funding_interval_hours` 指出: 短→长切换时, 新周期的第一次结算申报为长间隔, 而向后时间差是短的。于是账本与时间差在这些切换行上同时标错; T5d 的「账本与时间差 0 不符」不是独立验证。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5dR/PREREG_ADDENDUM_T5dR_declared_interval_reconciliation_2026-09-13.md:10` — 「例证 GWEIUSDT 2026-07 zip 07-22 12:00Z 申报 4、向后间隔 1h、费率 5.000e-05」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:46` — 「资金费追加规则按「与上一行时间差」定结算间隔(`shadow_loop_v3.py` L341–342): 短→长间隔切换时, 新制度首次结算按长间隔申报而时间差是短, 被标成短 ⇒ rn = rate×8/iv 放大 2–4×(v1 EMA / fund 腿)」
  - `/Users/haosiyu/wide_shadow/shadow_loop_v3.py:341` — 「iv = (ft - led[-1][0]) / 3600.0 if led else 8.0」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:148` — 「“存储 interval 不等于相邻时间差”本身不能证明场所真实结算间隔错误」
- **A reader could wrongly conclude:** A reader uses the ivfix panel / ledger intervals as ground truth (and rejects executor fundingInfo at switches), carrying the up-switch mislabel into September carry, FTRIM triggers and the T5d '+0.253 deployed carry' correction, and believes the incumbent v1 EMA seed is interval-clean.
- **Affects:** future_eval, reporting · **Severity reason:** The note calls the producer-ledger interval the 'true interval' and its 0 disagreements with the timestamp gap a verification, but the ledger interval is the snapped gap by construction and declared-interval zip evidence shows it mislabels the first settlement after a short→long switch; T5d-R is re-deriving September numbers on declared intervals.
- **Proposed correction (exact text):** ⚠ 2026-09-13 13:4xZ 限定(FX-PROD P9 + T5d-R 预注册): 生产者账本 iv 本身就是「与上一结算的时间差取整」(`shadow_loop_v3.py` L341), 故「账本 vs 时间差 0 不符」不是独立验证; data.binance.vision 资金费 zip 的申报列 `funding_interval_hours` 显示短→长切换后的首次结算申报为长间隔而时间差为短(例 GWEIUSDT 07-22 12Z 申报 4、间隔 1h), 账本在这些行上标短 ⇒ rn 放大 2–4×(在役 6 例: ONG 08-25 08Z / COTI 08-31 20Z / ZKC 09-02 20Z / T 09-06 00Z / SKR 09-07 20Z / SOPH 09-11 12Z)。在 T5d-R 按申报间隔对账出结果之前: 本条「true interval」「在位行与 v1 EMA 种子无误」「切换时不要用执行器 fundingInfo」及 L14 的 +0.253(SKR +0.207)均为暂定, 不作真值引用。(注意复审 R4 §5.1: 存储间隔≠时间差本身不证明场所结算间隔错误, 须以申报列与事件完整性核。)
- **Confidence:** INFERRED (T5d-R prereg §0 and FIXPROGRAM P9 opened and the producer gap rule read at shadow_loop_v3.py L341; which interval is the true accrual interval at switch rows is not yet adjudicated — T5d-R has no result) · **Quote re-verified at assembly:** exact

### M2-02 · P2 · DOC_STALE
- **Source:** `memory/universe_phase_a_m1_deployed_20260904.md:13`
- **Quote:** 「**Why:** 回放 M1 +0.066~+0.077 bps/锚(判官单位, 双种子双口径 CI>0, 尾部不变)」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:47` — 「| M1+T400(秩基变宽+成交集 400) | −0.057/−0.16 | −0.086/−0.07 | +0.181/+0.34 | **−0.009/+0.09** | 整体中性, 只在 2026 正 |」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
- **A reader could wrongly conclude:** A reader cites M1 (fund-leg rank base widened to all venue names, live since 09-04) as a proven +0.07 bps/anchor gain when attributing live results or arguing to keep or extend the universe mechanism.
- **Affects:** live_trading, reporting · **Severity reason:** The inline E-0904-F flag (L8) still says 'pending re-validation', but the re-validation was done and found M1 not significant; the rationale line still reads as a CI>0 gain.
- **Proposed correction (exact text):** ⚠ 复验结果(2026-09-13 审计补, 替换 L8「待复验」): E-0904-F 复验已完成 —— 无偏口径(CAL=log)下 M1+T400 相对正典 2024→26 −0.009(逐年 −0.057/−0.086/+0.181, 只在 2026 为正), 「三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害」(docs/RESULT_caliber_revalidation_2026-09-04.md L47/L52)。本行 +0.066~+0.077 CI>0 是 CAL=simple 伪凸性读数, 不得再作 M1 收益依据; M1 在役是事实, 其价值 = 未检出。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-04 · P2 · DOC_STALE
- **Source:** `memory/king_freshness_is_not_book_value.md:10`
- **Quote:** 「(2) 不把更多席位交给 king」
- **Superseding evidence:**
  - `docs/RESULT_rolling_king_monthly_2026-09-05.md:42` — 「2. 这与上周(作废的)"IC↑书↓"结论方向不同: 正确口径下不是"更差", 是"没差"; 上周的"更差"来自动态席位把 king 推到 0.89 的机制, 本次动态席位 Δ 亦 ≈ 0(king 席位没有被推高, 因为滚动 king 的末 900 锚 Sharpe 反而更低)。」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:50` — 「| 动态 msharpe 席位 vs 固定 0.21 | +0.791/+2.21 | +0.075/+0.47 | −0.365/−0.37 | **+0.235/+0.87** | 2024 fund 腿为负时动态席位把 king 提到 0.64 |」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
- **A reader could wrongly conclude:** A reader vetoes seat-rule or seeding changes that raise king's weight, or treats today's masked king seat 0.382 as a breach of this rule.
- **Affects:** live_trading, future_eval · **Severity reason:** The rule rests on the voided CAL=simple rolling-king result. Under the unbiased caliber, the dynamic seat that gives king more weight beat the fixed 0.21 seat over 2024→26, and a user-approved seeding has already raised the live king seat.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): (2) 作废。依据是 09-04 CAL=simple 的「滚动 king 把席位推到 0.89 ⇒ 书变差」, 已被 E-0904-F 作废(docs/RESULT_rolling_king_monthly_2026-09-05.md L42)。无偏口径下动态 msharpe 席位(2024 把 king 提到 0.64)对固定 0.21 为 2024→26 +0.235(RESULT_caliber_revalidation L50; 2026 为负); 09-05 用户字已按装置规则播种 0.1878→0.2999(STATE.md L161), 09-13 12Z 掩码 king 0.382。king 席位由预注册席位规则决定, 本条不作否决依据。
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-05 · P2 · DOC_STALE
- **Source:** `memory/king_incremental_retrain_undecided_2026_09_06.md:3`
- **Quote:** 「continued boosting (+40 trees/month) vs the live monthly full regrowth K1」
- **Superseding evidence:**
  - `docs/RESULT_retrain_cadence_and_seat_rule_2026-09-05.md:75` — 「| K0 在役 pinned | **−14.1%**/gross S−1.68 | +6.2% S+0.67 | +52.1% S+4.21 | — | — | — |」
  - `docs/ERROR_LEDGER_2026-08-20.md:436` — 「导出器 L49 `tr = YRA < 2026; te = YRA == 2026` ⇒ 每月重训只是在同一 2022–2025 训练集上重训并对延长后的 2026 特征做预测; 此前向用户表述的"king 训到 T−1/T−2 月"不成立。」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:55` — 「provenance 另记 `king_train_end_utc`(booster 真正的梯度截止 = 标签年 <2026 的最后锚, **月度导出不推进它**)与 `built_utc` 分离。」
- **A reader could wrongly conclude:** A reader believes the live king already relearns monthly on new data, so 'fresher king' questions look already deployed, or benchmarks a candidate against K1 as if it were production.
- **Affects:** future_retrain, future_eval · **Severity reason:** Misidentifies the research arm K1 (monthly rolling retrain with a 60-anchor embargo) as the live king. The live king is K0 pinned, trained only on 2022-2025, and the monthly export does not advance its training window.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): K1 (rollm60) is a research arm, not the live king. The live king is K0 pinned (docs/RESULT_retrain_cadence_and_seat_rule_2026-09-05.md L75): a booster trained on `tr = YRA < 2026` (2022-2025) that each monthly export re-fits on the same training set without advancing it (E-0905-B, ERROR_LEDGER L415; RUNBOOK_monthly_retrain_2026-10 L55). Read 'the live monthly full regrowth K1' (L3) and 'king stays on monthly full regrowth (K1)' (L12) as 'K1 rollm60, the research proxy for monthly full regrowth'. The KR/KC verdicts are unchanged.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-09 · P2 · DOC_STALE
- **Source:** `memory/caliber_review_closure_2026_09_05.md:8`
- **Quote:** 「⑦ carry +1.21 差 = 窗内错配(实盘 09-02 才有 FTRIM +0.73; 回放止损 08-21 已停 ONG +0.44), 非结构性; 装置 carry 公式无错。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:22` — 「| **T 窗内部署书无 FTRIM**(回放有) | +0.694 [+0.556, +0.844] | **58.2% / 58.8%** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:23` — 「| **H 部署链状态从 king 形态书暖启动**(08-26 00Z 与 08-30 04Z 两次) | +0.321 [+0.147, +0.517] | **27.0% / 26.9%** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:24` — 「| **P 回放独有的逐名止损层** | +0.220 [+0.048, +0.426] | **18.5% / 18.6%** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:33` — 「- **高 carry 在部署书对深负费率名的空头上(TC1 = YES)**: 「空头 ∧ 8h 当量现费率 ≤ −10bp」两格占 Δ 的 **98.5% / 98.7%**。该队列是部署书 carry 的 74.8%、回放书的 46.5%; gross 份额 6.4% 对 2.2%。**ONGUSDT 一个名占 Δ 约 41%**(共同名透镜 +0.490 bps/锚)。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:22` — 「- **ONG 为什么没止**(记录 + 重建深度, 重建只作描述): 执行器 ONG 空头成本 0.07626, 重建深度 08-26 00Z / 04Z / 08Z 为 −21.7% / −24.9% / **−28.5%**(未到 −30%)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:22` — 「执行器的持仓路径与回放止损层(08-25 20Z 起封锁 ONG)不同。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「T5 的构造桥可描述重建书的差，但 Shapley 是指定干预集合的分摊，不是自然实验因果比例；T×P 交互独立复算非零。」
- **A reader could wrongly conclude:** A reader cites '+0.73 FTRIM / +0.44 stop' as the settled decomposition, overlooks the warm-start (chain-state inheritance) transient, or assumes the executor's per-name stop had removed ONG.
- **Affects:** future_eval, reporting · **Severity reason:** T5 (09-13) splits the August deployed-vs-replay carry gap into FTRIM absence 58%, warm start from the king-form book 27% and the replay-only stop layer 18.5%. The 09-05 split has no warm-start component, doubles the stop share and misdates the ONG stop (replay blocked it from 08-25 20Z; the executor never stopped it).
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, T5/T5b): 八月部署书对回放多付 carry(27 锚, +1.19)的构造分解 = FTRIM 窗内缺席 +0.694(58%)+ 换装/08-30 重启时链状态从无 FTRIM 的 king 形态书暖启动 +0.321(27%)+ 回放独有逐名止损层 +0.220(18.5%); 98.5% 在「空头 ∧ 8h 当量费率 ≤ −10bp」队列, ONG 约占 41%(uplift_r2 T5 RESULT L22–24/L33)。ONG 在回放中自 08-25 20Z 被止损层封锁(非 08-21), 执行器逐名止损未触发(深度 −28.5% 未到 −30%; T5b L19)。Shapley 是指定干预集合的分摊, 不是因果比例(REVIEW round4 L136)。「非结构性」改为「构造差: 规则差(FTRIM)+ 运维暂态(暖启动)+ 目标层设计差(止损层)」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-10 · P2 · DOC_STALE
- **Source:** `memory/caliber_review_closure_2026_09_05.md:8`
- **Quote:** 「⑤ combo 复测(16 臂): 排序保住、不显著; 去 rev24 CI>0(+0.10~0.12); V2MAIN 净≈0(降 gross/回撤提 Sharpe); 2025 combo<换装前。」
- **Superseding evidence:**
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「08-26/09-04 的"V2MAIN 净≈0"读数(combo_recheck: C−A log +0.005 / 复利 +0.079, P 0.50/0.79, 装置刻度 net_ex)属于装置刻度」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「每 gross 口径下 V2MAIN 贡献在三口径、双种子的 2024→26 全为 CI>0」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:24` — 「fund 腿价格边 H1 +4.23 → 8 月 −0.54(s42)/−0.09(s2027), 同期 fund 腿 carry 0.84 → 1.17; king 腿 +0.14 → +0.04, V2MAIN 腿 +0.39 → +0.40。」
- **A reader could wrongly conclude:** A reader concludes the V2MAIN (DL) leg adds nothing and argues for dropping it or deprioritising DL retraining.
- **Affects:** future_eval, reporting · **Severity reason:** 'V2MAIN net ≈0' holds only on the device scale (net_ex per unit NAV). Per unit gross, the scale that maps to NAV at fixed leverage, the V2MAIN contribution is CI>0 over 2024→26 under all three labels and both seeds (2025 alone undecided).
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 「V2MAIN 净≈0」只在装置刻度(net_ex, 每单位 NAV)成立(combo_recheck: C−A log +0.005 / 复利 +0.079)。按每 gross 口径(执行器按 gross=L×NAV 定尺寸, 才是 NAV 收益口径), V2MAIN 贡献在三种标签、双种子的 2024→26 全为 CI>0, 2025 单年各口径均未定(docs/RESULT_f10_caliber_sensitivity_2026-09-05.md L191)。引用须同时声明刻度与标签。v4 描述性腿分解(T1 RESULT L24): V2MAIN 腿 2026-H1 +0.39 → 8 月 +0.40, 八月落差不在 V2MAIN 腿。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-11 · P2 · DOC_STALE
- **Source:** `memory/caliber_review_closure_2026_09_05.md:8`
- **Quote:** 「④ 在役固定席位形态(pod): 2024 −16.6%/gross, 2025 +8.3%, 2026 +67.9%(8 月年化), 2024→26 +12.6(比值均值)~+14.4%(逐锚比值均值)/gross, Sharpe 1.02, 跨年 maxDD 33% gross;」
- **Superseding evidence:**
  - `STATE.md:163` — 「**16Z 锚验收(巡检)**: 掩码 king ∈ [0.28, 0.32], combo_stage 五层安全通过, 执行器/readback 正常, sidecar 自平价 PASS, FTRIM/M1 PASS; 任一不成立 ⇒ 回滚(备份文件 + kickstart)。**关闭「线上 0.19 vs 装置 0.33」的缝; 此后席位随实盘行滚动; 下次换 bundle 时须按同法播种(否则新模型样本外行永不进窗)。**」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:29` — 「5. **探索性日块自举 Sharpe CI95**(研究员新增, 2000 次, UTC 日块, 保留日内依赖不保留跨日; rng [20260905,k]): 原钉 W_ALPHA **[0.3207, 2.2822]**(SE 0.4890)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「3. **回撤尺子**: 表中 maxDD 是累计 g 的算术峰谷差(单位 gross), ×2 只是线性近似; 按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**; W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%。」
- **A reader could wrongly conclude:** A reader quotes Sharpe 1.02 / 2024 −16.6% / maxDD 33% gross as the live book's expected profile and omits the 2023 loss year (Sharpe −1.94) that the v4 full-cycle table shows.
- **Affects:** reporting, future_eval · **Severity reason:** Labels the fixed-seat-0.21 form as the live form. Since the 09-05 seeding the live seat is dynamic (masked king 0.382 on 09-13), and the numbers are pre-v4 with an arithmetic drawdown ruler; the v4 A0 per-year table supersedes them.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): ④「在役固定席位形态」自 09-05 12:47Z 席位播种后已不是在役形态(STATE.md L161: 此后席位随实盘行滚动; 09-13 12Z 掩码 king 0.382), 数字亦为 pre-v4 口径。在役形态参考数改引 v4 A0 逐年表(uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md): 全窗 2022-06..2026-08 Sharpe 1.29(日块 CI95 [0.32, 2.28]), 2023 −1.94 / 2024 +1.09 / 2025 +1.19 / 2026 +4.53; 回撤按固定 2× 复利 NAV(W_ALPHA −42.12%), 不用算术 ×2。
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-12 · P2 · DOC_STALE
- **Source:** `memory/live_seat_seed_is_in_sample.md:3`
- **Quote:** 「E-0904-F/G(终版) — 面板 y4 = Σ 5 分钟简单收益(逐位实证), 是交易所记账的无偏代理; 回放装置 CAL=simple 的 expm1 是伪凸性(king 腿 −2~−3 bps/锚伪拖累); bundle 种子与生产者口径本来正确, 实盘 king 席位 0.21 合法; 我 09-04 两次错归因(样本内→对数口径)并错换种子, 已回滚」
- **Superseding evidence:**
  - `STATE.md:163` — 「**16Z 锚验收(巡检)**: 掩码 king ∈ [0.28, 0.32], combo_stage 五层安全通过, 执行器/readback 正常, sidecar 自平价 PASS, FTRIM/M1 PASS; 任一不成立 ⇒ 回滚(备份文件 + kickstart)。**关闭「线上 0.19 vs 装置 0.33」的缝; 此后席位随实盘行滚动; 下次换 bundle 时须按同法播种(否则新模型样本外行永不进窗)。**」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:14` — 「the pinned 5m cache's `ret5` channel is **hard-clipped at ±0.300048828125 per 5-minute bar** (953 bars exactly at the bound, none beyond)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:14` — 「**397 cells on 2025-10 alone, 2025-10-10 20Z = the Oct-10 crash**; SOLVUSDT there: meta −48.4 %, clipped-compound +54.9 % — the E-0908-B signature)」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
- **A reader could wrongly conclude:** A reader treats 0.21 as the correct live king seat (and today's 0.38 as drift), or recomputes returns from the clipped Σ5m cache on extreme anchors believing it is an unbiased proxy.
- **Affects:** reporting, future_eval · **Severity reason:** Two headline claims were later qualified. The live 0.21 king seat was not the device-rule value (the producer's seat window still held pre-v3 king rows; the 09-05 seeding closed that gap). The Σ5m panel y4 comes from a ret5 channel hard-clipped at ±0.30 per bar, so it is not unbiased on crash cells.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): ①「实盘 king 席位 0.21 合法」只回答了 09-04 的口径问题; 09-05 查明席位窗仍是 08-16 旧 booster 的样本外行(线上 0.19 vs 装置 0.33), 已按装置规则播种 0.1878→0.2999(STATE.md L161), 09-13 12Z 掩码 king 0.382 —— 0.21 不是当前正确值。② 「Σ5m 是记账的无偏代理」只在均值层成立: ret5 通道硬裁 ±0.30/bar, 590 格(196 锚; 397 格在 2025-10-10 崩盘)与记账元 Π(1+r)−1 不符(SOLV −48.4% vs 裁剪复利 +54.9%, E-0908-B), 尾部数字一律是下界; 收益一律取记账元 y4(RAW), 不从缓存重算(r18 RESULT L14; CALIBER_PIN_v4 L30)。
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-13 · P2 · DOC_STALE
- **Source:** `memory/live_seat_seed_is_in_sample.md:9`
- **Quote:** 「正确口径终读(pod 仪器): 固定席位 0.21 形态 2024 −16.6%/gross, 2024→26 +12.6%/gross/年(2× ⇒ +25% NAV), Sharpe 1.02, 跨年 maxDD 33% gross(2× ⇒ 66% NAV); 动态席位 +24.4%/gross(2× ⇒ +49% NAV), maxDD 12.8%。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「3. **回撤尺子**: 表中 maxDD 是累计 g 的算术峰谷差(单位 gross), ×2 只是线性近似; 按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**; W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「| P3 | 逐年 v4 表与复利回撤(2023 NAV maxDD 28.92%) | `r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md` + 勘误 | 回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2 |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
- **A reader could wrongly conclude:** A reader sizes leverage or stop rules from '66% NAV' or '+49% NAV/yr, maxDD 12.8%' instead of the v4 compounded per-year table (2023 Sharpe −1.94; W_ALPHA compounded NAV maxDD −42.12%).
- **Affects:** reporting, live_trading · **Severity reason:** Converts drawdown to 2× NAV by arithmetic doubling (33% gross ⇒ 66% NAV), which the v4 program forbids (compounded fixed-2× NAV required), and quotes pre-v4 2024→26 levels that leave out the 2023 loss year.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 本段是 09-04 pod 仪器的 pre-v4 读数, 回撤按算术 ×2 换算; 现行规则「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」(uplift_r2 PROGRAM L19)。现行参考 = v4 A0 逐年表(TABLE_per_year_v4_caliber_2026-09-12.md): 全窗 Sharpe 1.29, 2023 −1.94(年内 2× 复利 NAV maxDD −28.92%), W_ALPHA 全窗复利 NAV maxDD −42.12%(勘误 3)。本段只作历史, 不作杠杆/止损依据。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-14 · P2 · DOC_STALE
- **Source:** `memory/live_seat_seed_is_in_sample.md:9`
- **Quote:** 「**carry 差:** 实盘书正费率多头权重 0.48 vs 回放 0.43 ⇒ 同锚同费率暴露 2.23 vs 1.04 bps/锚(书构成, 非装置公式)。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:33` — 「- **高 carry 在部署书对深负费率名的空头上(TC1 = YES)**: 「空头 ∧ 8h 当量现费率 ≤ −10bp」两格占 Δ 的 **98.5% / 98.7%**。该队列是部署书 carry 的 74.8%、回放书的 46.5%; gross 份额 6.4% 对 2.2%。**ONGUSDT 一个名占 Δ 约 41%**(共同名透镜 +0.490 bps/锚)。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:22` — 「| **T 窗内部署书无 FTRIM**(回放有) | +0.694 [+0.556, +0.844] | **58.2% / 58.8%** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:23` — 「| **H 部署链状态从 king 形态书暖启动**(08-26 00Z 与 08-30 04Z 两次) | +0.321 [+0.147, +0.517] | **27.0% / 26.9%** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:24` — 「| **P 回放独有的逐名止损层** | +0.220 [+0.048, +0.426] | **18.5% / 18.6%** |」
- **A reader could wrongly conclude:** A reader looks for the carry leak on the long side and designs positive-funding long caps, while the measured gap came from deep-negative-funding shorts.
- **Affects:** future_eval, reporting · **Severity reason:** Attributes the live-vs-replay carry gap to heavier positive-funding longs. T5 (09-13) finds 98.5% of the gap sits in shorts with an 8h-equivalent rate ≤ −10bp (ONG ≈41%), explained by FTRIM absence, warm start and the replay-only stop layer.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, T5): 「书构成差」成立, 但机制不是「正费率多头权重 0.48 vs 0.43」—— 部署书对回放多付的 carry 98.5% 落在「空头 ∧ 8h 当量现费率 ≤ −10bp」队列, ONGUSDT 一名约占 41%; 分解 = FTRIM 窗内缺席 58% + king 形态书暖启动 27% + 回放独有逐名止损层 18.5%(uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md L22–24, L33)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-16 · P2 · DOC_STALE
- **Source:** `memory/live_form_health_check_2026_09_05.md:10`
- **Quote:** 「Live fees VERIFIED (1.80/4.50 bps, ≈2.0 bps per unit turnover, ≈7 % NAV/yr at 2× at replay turnover 0.08)」
- **Superseding evidence:**
  - `docs/RULINGS_requested_2026-09-12.md:7` — 「09-07 起全 USDT 费, maker 恰 2.0 / taker 恰 5.0 bps, VIP0」
  - `STATE.md:63` — 「BNB 折扣断第 6 日(运维)」
- **A reader could wrongly conclude:** A reader calibrates replay costs or live fee expectations with 1.80/4.50 bps and under-charges turnover in evaluations.
- **Affects:** future_eval, reporting · **Severity reason:** Since 09-07 the BNB fee discount has lapsed: fees are exactly 2.0 bps maker / 5.0 bps taker (VIP0), still not restored on 09-12, so cost calibrations built on 1.80/4.50 under-charge fees by about 11%.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): the 1.80/4.50 bps tier assumed the BNB fee discount. Since 2026-09-07 all fees are paid in USDT at exactly 2.0 maker / 5.0 taker bps, VIP0 (docs/RULINGS_requested_2026-09-12.md R-1; STATE.md L61 on 09-12: 'BNB 折扣断第 6 日'). Re-read the current fee tier before using fees in a cost model; restoring the discount is pending ruling R-1.
- **Confidence:** VERIFIED (quote+receipt opened); fee tier after 09-12 not re-checked (no API calls); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-17 · P2 · DOC_STALE
- **Source:** `memory/live_dl_epoch_rule_is_unconstrained_argmax.md:8`
- **Quote:** 「STATE records it as a candidate needing a clean CONST2027 second seed + ≥14-day forward shadow + the user's word.」
- **Superseding evidence:**
  - `STATE.md:210` — 「**FIX7 / FLOOR5 = 候选, 未部署。** 欠: 前向影子 ≥14 天 + 用户字(★ 09-09 更正: 干净 CONST2027 参照研究员 09-07 已完成 20/20 + 两次回放 rc0, `codex_const2027_2026-09-07/training_complete.json` / `codex_const2027_replay_2026-09-07/root_completion_review.json`; 它是旧 constant2027/validation-best 的干净参照, 与 G3 稳定 FIX7 不同; 经济门与影子仍未过)。」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:16` — 「| FIX7 - CONST2027 | +0.248007 | [+0.055103, +0.439083] | [-0.000272, +0.540652] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:23` — 「FIX7和FLOOR5在主窗按原UTC日块规则均得到REPLICATED_WITH_CLEAN_REFERENCE；这个程序标签只指原历史规则复核。FIX7的30日块下界−0.000272，仍属跨零，不能四舍五入成正数，也不能追加bootstrap抽样直到变绿。FLOOR5两种块长均为正。对yearly的区间均跨零，不构成统计非劣或优越证明；原规则中的mean≥−0.05及CI跨零是一项历史判读约定，不能代替预设非劣界的正式检验。」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:38` — 「| 4b F10 refit(部署件) | `F10_DLW=/workspace/dlw_v4raw F10_OUT=/workspace/f8_v4 SEED=42 BEST_EP_FIX=7 $PY $R/pod_f10_refit_v4.py`(**四个 env 逐字, 缺一不跑**); 产物 `f8_v4/models/f10_live_s42.pt` + 报告里 `best_ep_rule` 必须读 `fix7` |」
  - `docs/RULINGS_requested_2026-09-12.md:14` — 「| R-8 | **十月重训**(G3) | §0★ 修订 2: 三处代码改动完成前不得开始; W3 在做」
- **A reader could wrongly conclude:** A reader thinks FIX7 still waits on a CONST2027 run and queues redundant GPU work, or assumes the next monthly refit will again use argmax.
- **Affects:** future_retrain · **Severity reason:** The clean CONST2027 reference was completed on 09-07 (FIX7 − CONST2027 +0.248 [+0.055, +0.439] on UTC-day blocks, though the 30-day-block lower bound is −0.0003), and the October v4 RUNBOOK already prescribes BEST_EP_FIX=7 for the deployment refit, pending ruling R-8.
- **Proposed correction (exact text):** ⚠ Update (2026-09-13 audit): the clean CONST2027 reference was completed by the independent researcher on 09-07 (codex_const2027_replay_2026-09-07/RESULT.md L16/L23: FIX7 − CONST2027 +0.248 [+0.055, +0.439] on UTC-day blocks, REPLICATED_WITH_CLEAN_REFERENCE, but the 30-day-block lower bound is −0.000272 and the 2026-only window crosses 0; STATE.md L208). Still outstanding: the economic gate, the ≥14-day forward shadow and the user's word. The October v4 RUNBOOK step 4b already prescribes `BEST_EP_FIX=7` for the deployment refit (RUNBOOK_monthly_retrain_2026-10 L38; retrain ruling R-8 pending). Until an October FIX7 refit is deployed, the live F10 remains argmax.
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-18 · P2 · DOC_STALE
- **Source:** `memory/dl_earlystop_replicated_two_seeds_2026_09_06.md:3`
- **Quote:** 「so the second seed's deployment-equivalent confirmation is NOT complete — needs a true CONST2027.」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:16` — 「| FIX7 - CONST2027 | +0.248007 | [+0.055103, +0.439083] | [-0.000272, +0.540652] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:18` — 「| FLOOR5 - CONST2027 | +0.192044 | [+0.026597, +0.353683] | [+0.052435, +0.344195] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:23` — 「FIX7和FLOOR5在主窗按原UTC日块规则均得到REPLICATED_WITH_CLEAN_REFERENCE；这个程序标签只指原历史规则复核。FIX7的30日块下界−0.000272，仍属跨零，不能四舍五入成正数，也不能追加bootstrap抽样直到变绿。FLOOR5两种块长均为正。对yearly的区间均跨零，不构成统计非劣或优越证明；原规则中的mean≥−0.05及CI跨零是一项历史判读约定，不能代替预设非劣界的正式检验。」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:40` — 「2026单独窗口中FIX7为UTC日块跨零、30日块为正，和主窗的敏感性方向相反。」
  - `STATE.md:210` — 「**FIX7 / FLOOR5 = 候选, 未部署。** 欠: 前向影子 ≥14 天 + 用户字(★ 09-09 更正: 干净 CONST2027 参照研究员 09-07 已完成 20/20 + 两次回放 rc0, `codex_const2027_2026-09-07/training_complete.json` / `codex_const2027_replay_2026-09-07/root_completion_review.json`; 它是旧 constant2027/validation-best 的干净参照, 与 G3 稳定 FIX7 不同; 经济门与影子仍未过)。」
- **A reader could wrongly conclude:** A reader either still treats the second seed as missing, or upgrades it to a clean two-seed pass without the block-length and 2026-window caveats.
- **Affects:** future_retrain, reporting · **Severity reason:** The true CONST2027 was run on 09-07. Both arms replicate against the clean reference on UTC-day blocks, but FIX7's 30-day-block lower bound crosses zero and the 2026-only FIX7 window is not significant.
- **Proposed correction (exact text):** ⚠ Update (2026-09-13 audit): the true CONST2027 now exists (codex_const2027_replay_2026-09-07/RESULT.md). Frozen window against it: FIX7 − CONST2027 +0.248 [+0.055, +0.439] (UTC-day blocks; 30-day blocks [−0.000272, +0.541]); FLOOR5 − CONST2027 +0.192 [+0.027, +0.354] (positive under both block lengths). Against yearly2027 both CIs cross 0 (not non-inferiority), and 2026-only FIX7 crosses 0 on UTC-day blocks. Reading: REPLICATED_WITH_CLEAN_REFERENCE under the original UTC-day rule. FLOOR5's second-seed result is the more robust; FIX7's is block-length sensitive.
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-19 · P2 · DOC_STALE
- **Source:** `memory/dl_monthly_earlystop_is_main_cause_2026_09_06.md:3`
- **Quote:** 「best-epoch floor 5 or fixed epoch 7 makes monthly folds ≥ yearly (FIX7 − yearly +0.151 [−0.048, +0.353], − CONST +0.267 CI>0, − seed-per-fold monthly +0.323 CI>0); live v3 model itself picked epoch 8 (s2027 twin 13); seed-2027 replication pending before any candidate prereg」
- **Superseding evidence:**
  - `STATE.md:256` — 「「点估计 ≥ −δ 且 CI 含 0」是**冻结决策规则**, **不是非劣性证明**(后者要求 **CI 下界 > −δ**)。全部归档判官冻结窗扫描(装置 `codex_review_2026-09-07_ni_check.py`): **32 个「不劣于年折」型对照, 我方规则通过 18, 真正非劣检验(δ=0.05)只通过 3(FIX7_s42 / W2_s42)**;」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:19` — 「| FIX7 - yearly2027 | +0.060456 | [-0.098857, +0.224644] | [-0.111494, +0.258367] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:20` — 「| FLOOR5 - yearly2027 | +0.004494 | [-0.111508, +0.124364] | [-0.085119, +0.081591] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:23` — 「FIX7和FLOOR5在主窗按原UTC日块规则均得到REPLICATED_WITH_CLEAN_REFERENCE；这个程序标签只指原历史规则复核。FIX7的30日块下界−0.000272，仍属跨零，不能四舍五入成正数，也不能追加bootstrap抽样直到变绿。FLOOR5两种块长均为正。对yearly的区间均跨零，不构成统计非劣或优越证明；原规则中的mean≥−0.05及CI跨零是一项历史判读约定，不能代替预设非劣界的正式检验。」
  - `STATE.md:210` — 「**FIX7 / FLOOR5 = 候选, 未部署。** 欠: 前向影子 ≥14 天 + 用户字(★ 09-09 更正: 干净 CONST2027 参照研究员 09-07 已完成 20/20 + 两次回放 rc0, `codex_const2027_2026-09-07/training_complete.json` / `codex_const2027_replay_2026-09-07/root_completion_review.json`; 它是旧 constant2027/validation-best 的干净参照, 与 G3 稳定 FIX7 不同; 经济门与影子仍未过)。」
- **A reader could wrongly conclude:** A reader states that the epoch fix makes monthly refits at least as good as yearly folds and uses it as a non-inferiority argument for a deployment.
- **Affects:** future_retrain, reporting · **Severity reason:** '≥ yearly' is not established: the CIs against yearly contain 0, and under the 09-07 discipline true non-inferiority (δ=0.05) passes only for FIX7_s42 (not FLOOR5, not against yearly2027). The seed-2027 replication and the clean CONST2027 have both since been done.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): replace 'makes monthly folds ≥ yearly' with 'beats CONST42 (CI>0); versus yearly the CIs contain 0 — true non-inferiority at δ=0.05 holds only for FIX7_s42 (lower −0.048), not for FLOOR5 (−0.133) and not against yearly2027 (FIX7 +0.060 [−0.099, +0.225], FLOOR5 +0.004 [−0.112, +0.124])' (STATE.md L254; codex_const2027_replay RESULT L19–L20/L23). 'Seed-2027 replication pending' is closed: run 09-06 against R0, and a clean CONST2027 was run 09-07 (FIX7 − CONST2027 +0.248 [+0.055, +0.439]; 30-day-block lower bound −0.0003).
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-23 · P2 · DOC_STALE
- **Source:** `memory/dl_warmstart_finetune_2026_09_06.md:15`
- **Quote:** 「treat "monthly refit = warm start (+ best-epoch floor, §12)" as the candidate recipe, deployable only after a ≥14-day shadow or second-instrument replication and the user's word (RUNBOOK change).」
- **Superseding evidence:**
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:884` — 「**W1F5 − W1 = −0.034 [−0.142, +0.083] P0.30**(**点估计为负**), W1F5 − FLOOR5 = +0.072 [−0.194, +0.332] P0.69, W1F5 − 年折 s42 = +0.125 [−0.162, +0.439] P0.80, W1F5 − CONST42 = +0.241 [−0.058, +0.519] P0.95。⇒ 「热启动」与「早停下限」**不叠加**: 热启动一旦把起点换成训好的模型, 早停就不再选到近初始化的 epoch(§13.4 已记), 下限规则因此无事可做。」
  - `docs/PREREG_deploy_dl_recipe_2026-10.md:6` — 「**更正一处早前措辞**: 我曾把方案 B 写成「A(下限 5)+ 热启动」, 但复验过的热启动臂 **W1/W2 用的是逐字原早停规则(argmax), 不带下限**; 带下限的组合臂 W1F5 只有种子 42 且对两个单项都不加分(−0.034 / +0.072, CI 均含 0)。**⇒ 方案 B 的正确形态 = 只加热启动, 早停规则一字不改。**」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:38` — 「| 4b F10 refit(部署件) | `F10_DLW=/workspace/dlw_v4raw F10_OUT=/workspace/f8_v4 SEED=42 BEST_EP_FIX=7 $PY $R/pod_f10_refit_v4.py`(**四个 env 逐字, 缺一不跑**); 产物 `f8_v4/models/f10_live_s42.pt` + 报告里 `best_ep_rule` 必须读 `fix7` |」
  - `docs/RULINGS_requested_2026-09-12.md:14` — 「| R-8 | **十月重训**(G3) | §0★ 修订 2: 三处代码改动完成前不得开始; W3 在做」
- **A reader could wrongly conclude:** A reader pre-registers or deploys the W1F5 combination as the October recipe, or believes the combination trainer still awaits its prereg.
- **Affects:** future_retrain · **Severity reason:** The warm-start + floor combination was tested in §14 and does not stack (W1F5 − W1 −0.034 [−0.142, +0.083]); the deployment prereg fixed 方案 B as warm start only with the argmax rule unchanged. The October RUNBOOK instead bakes FIX7, so the recipe choice is unresolved (R-8).
- **Proposed correction (exact text):** ⚠ Superseded (2026-09-13 audit): '(+ best-epoch floor)' is refuted. §14 W1F5 − W1 = −0.034 [−0.142, +0.083]: once warm start is on, the floor has nothing to do (docs/RESULT_dl_monthly_gate_2026-09-05.md L884); the W1F5 trainer has already run. The deployment prereg fixed 方案 B = warm start only, early-stopping rule unchanged (PREREG_deploy_dl_recipe_2026-10 L6). RUNBOOK_monthly_retrain_2026-10 step 4b prescribes FIX7 instead; the October recipe choice (方案 B vs FIX7) is pending user ruling R-8.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-24 · P2 · DOC_STALE
- **Source:** `memory/dl_recipe_arms_w1f5_p1_p0_all_fail_2026_09_06.md:13`
- **Quote:** 「本轮唯一过门的是 FLOOR5/FIX7(§12 + 种子 2027 复验: +0.243 [+0.066,+0.420] / +0.299 [+0.071,+0.523])」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:532` — 「- **seed 2027 的复验换了参照**: `judge_replication.py` L5 的读法是 `ARM_s2027 − **R0_s2027** CI lower > 0 ∧ …` ⇒ **复的不是 §12 那个对照**。已发表的 +0.243 / +0.299 是 vs R0 的值。」
  - `docs/ERROR_LEDGER_2026-08-20.md:533` — 「- **同型补算(每 gross bps/锚)**: FLOOR5_s2027 − CONSTspl27 **+0.185 [+0.052,+0.322]**, FIX7_s2027 − CONSTspl27 **+0.241 [+0.048,+0.426]** ⇒ **同型门仍通过**」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:16` — 「| FIX7 - CONST2027 | +0.248007 | [+0.055103, +0.439083] | [-0.000272, +0.540652] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:18` — 「| FLOOR5 - CONST2027 | +0.192044 | [+0.026597, +0.353683] | [+0.052435, +0.344195] |」
- **A reader could wrongly conclude:** A reader quotes +0.243/+0.299 as the second-seed deployment-equivalent effect, overstating the recipe gain and hiding FIX7's block-length sensitivity.
- **Affects:** reporting, future_retrain · **Severity reason:** +0.243/+0.299 are measured against R0_s2027, which is not the deployment-equivalent reference (E-0907-E). Against the clean CONST2027 the seed-2027 gains are +0.192 (FLOOR5) and +0.248 (FIX7, 30-day-block lower bound −0.0003).
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, E-0907-E): +0.243 / +0.299 是对 R0_s2027 的差(非部署等价参照), 引用必须带参照名(ERROR_LEDGER L511)。部署等价读数: 同型补算 FLOOR5_s2027 − CONSTspl27 +0.185 / FIX7 +0.241(参照含 seed 42 训练段, L512); 干净 CONST2027(研究员 09-07): FLOOR5 − CONST2027 +0.192 [+0.027, +0.354](两种块长均为正), FIX7 − CONST2027 +0.248 [+0.055, +0.439](30 日块下界 −0.000272 跨零)(codex_const2027_replay_2026-09-07/RESULT.md L16/L18)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-26 · P2 · DOC_STALE
- **Source:** `memory/live_model_legs_stopped_learning_end_2025.md:10`
- **Quote:** 「That reopens "do recent labels add value" from *known-useless* to **untested with positive preliminary evidence**」
- **Superseding evidence:**
  - `STATE.md:258` — 「- **★ 满窗梯度已判负, 不进候选(09-07, RESULT_dl_full_gradient_window b543e20)**: X7FULL − FIX7 冻结 **−0.058 [−0.212,+0.103]** / 2026 −0.103 ⇒ **(C) UNDECIDED**, 且四指标同向偏负(FIX7 +1.708/S2.87/maxDD832 vs 满窗 +1.651/2.75/919)。步数效应 +0.008 ⇒ 两条路都空。**「近期标签有价值」在书层无支持**; 梯度赤字(255 天, 每月 +4.57 天)是设计怪异但**今天填平它无价值**, 赤字远超 255 天时该结论不外推。**在役配方形态无改动动作。**」
  - `docs/RESULT_dl_full_gradient_window_2026-09-07.md:120` — 「| **X7FULL** | **+0.0269** [+0.0238, +0.0302] | **+0.00508 [+0.00315, +0.00702]** | **CI > 0** |」
  - `docs/RESULT_dl_full_gradient_window_2026-09-07.md:127` — 「**⇒ 「排序≠净额」第七例现在成立, 而且是同臂、同样本、同 mask 的最干净一例。**」
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/pod_f10_refit_v4.py:104` — 「cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:55` — 「provenance 另记 `king_train_end_utc`(booster 真正的梯度截止 = 标签年 <2026 的最后锚, **月度导出不推进它**)与 `built_utc` 分离。」
- **A reader could wrongly conclude:** A reader reopens a 'recent labels add value' GPU line as if it were untested, or reads the preliminary evidence as book-level support.
- **Affects:** future_retrain · **Severity reason:** The 'untested' question was tested on 09-07 (X7FULL puts all labels into gradients): book-layer Δ UNDECIDED, with STATE recording 'no book-layer support' while score-layer IC rose significantly. The note's structural fact (both legs stop learning at end-2025) still holds through the October v4 plan.
- **Proposed correction (exact text):** ⚠ Update (2026-09-13 audit): now tested. X7FULL (100% of the pool into gradients, FIX7) − FIX7 = −0.058 [−0.212, +0.103] frozen, (C) UNDECIDED, 'no book-layer support' (STATE.md L256); score-layer ΔIC +0.00508 [+0.00315, +0.00702], so ranking ≠ net (RESULT_dl_full_gradient_window_2026-09-07 L120/L127). The structural fact still stands: the October v4 refit keeps the 85% cut (pod_f10_refit_v4.py L104) and monthly export does not advance the king booster's training end (RUNBOOK_monthly_retrain_2026-10 L55).
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-27 · P2 · DOC_STALE
- **Source:** `memory/f10_one_bar_window_and_dl_monthly_2026_09_05.md:9`
- **Quote:** 「月龄 IC 平坦 ⇒ DL 无月度重训价值, 保持年度(09-01 件)。」
- **Superseding evidence:**
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:344` — 「**种子 2027 的 20 个 mE1 月折(禁运 1 锚, 同输入, 同折规则, 同回放装置, 同自举)复现了 §0.4 的读数: 月度换装(R0)在书层劣于年折, 两个种子、两个窗口都是 CI 上界 < 0。**」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:556` — 「1. **冻结读法 = (A) 早停是主因, 两个窗口都成立**(VERIFIED 表 AD3-3)。」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:562` — 「(A) ⇒ 冻结候选 `PREREG_dl_freeze_yearly_2026-09-05.md` 撤回, 改立"月度重训 + best-epoch 规则修正"候选」
- **A reader could wrongly conclude:** A reader answers DL-cadence questions from the f311321 table and recommends keeping yearly folds, ignoring the epoch-rule mechanism and the current FIX7 / warm-start candidates.
- **Affects:** future_retrain · **Severity reason:** The f311321 reading ('no value in monthly DL refits, keep yearly') was re-run and superseded: §10 found the monthly form worse than yearly on the frozen window with a second seed, and §12 traced it to early stopping and withdrew the freeze-to-yearly candidate. The note's instruction 'cite f311321, do not re-run' (L12) is contradicted.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): f311321 的「DL 无月度重训价值, 保持年度」已被重跑取代: §10(冻结窗 + 种子 2027)月度 R0 劣于年折 CI<0; §12 冻结读法 (A)「早停是主因」, 冻结到年折的候选撤回, 改立「月度重训 + epoch 规则修正(FIX7/FLOOR5)」(docs/RESULT_dl_monthly_gate_2026-09-05.md L344/L556/L562)。L12「报 DL 节奏问题直接引 f311321 表, 不重跑」作废, 改引 RESULT_dl_monthly_gate §10–§14 与 codex_const2027 复核。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-31 · P2 · DOC_STALE
- **Source:** `memory/requote_randomised_experiment_live_2026_09_05.md:9`
- **Quote:** 「装置 = exec_requote_behind_2026-09-05/analyse_requote_behind.py 口径按 `requote_arm` 分臂(exempt 剔除)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:187` — 「1. **装置缺陷, 首跑发现并修正:** 重挂实验的 `requote_arm = "direct"` 写在补单行上, 首版只从 maker 行读, 敏感性 205 什么都没剔。改为从计划内任意行读后重跑; 只有 205 变了, 主估计与其它格逐位不变。首跑产物保留为 `receipts/*_run1_before_rqarm_fix.*`。」
  - `docs/PREREG_requote_randomised_2026-09-05.md:14` — 「- 记账: 订单行新增 `requote_arm`(requote/direct/exempt; attempt-1 拒单行写于分臂之前为 null, 由 attempt-2 行/补单行/终态 maker 行携带)与 `requote_p`; 执行器 requote 报告新增 `n_direct / n_exempt / p_requote`(落 launchd 日志)。」
  - `multi_asset/exports/live/exec_requote_behind_2026-09-05/analyse_requote_behind.py:26` — 「if r.get("order_type") != "maker" or r.get("attempt_idx") != 1: continue」
  - `multi_asset/exports/live/exec_requote_behind_2026-09-05/analyse_requote_behind.py:33` — 「p["arm"] = p["arm"] or r.get("placement_arm")」
- **A reader could wrongly conclude:** At the one-shot readout a reader runs the named analyser (or an adaptation that reads requote_arm from maker rows) and gets an empty or mis-assigned direct arm, then rules on p_requote from a broken contrast.
- **Affects:** future_eval · **Severity reason:** The named analyser has no requote_arm split: it builds plans from attempt-1 maker rows and reads placement_arm. T3 found `requote_arm = direct` is written on the top-up row, so a reader that takes the arm from maker rows assigns no direct plans; the frozen readout (≥09-19, exactly once) would be corrupted.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 读数装置尚未就绪 —— 归档 `analyse_requote_behind.py` 只从 attempt-1 maker 行建计划并读 `placement_arm`(L26/L33), 没有 `requote_arm` 分臂; T3 实测 `requote_arm = "direct"` 写在补单行上, 只从 maker 行读一个 direct 都分不到(uplift_r2 T3 RESULT L187; PREREG_requote_randomised L14: attempt-1 拒单行为 null, 由 attempt-2/补单/终态 maker 行携带)。读数前须改为「从计划内任意行读臂」或按 sha1(requote:rid:sym) 末字节复算分臂, 用正负控核对两臂计数并冻结装置 sha, 再做唯一一次主判。
- **Confidence:** VERIFIED (quote+receipt opened; analyser grep shows no 'requote_arm') · **Quote re-verified at assembly:** exact

### M2-34 · P2 · DOC_STALE
- **Source:** `memory/caliber_env_flag_trap.md:8`
- **Quote:** 「2026-08-25/26。w8/w10 回放的 `CAL`: "simple"=交易所简单收益(expm1), 其它任意值=对数。我连续 24h 传 **`CAL=exec`**(误记为"执行器口径"开关 —— 那是 w3 时代的语义), 脚本不报错, 13 个臂全落对数口径, 与 simple 基线相减 ⇒ "2026 全是 −1.9"的假信号 ⇒ 叠加漏 `V2=1` 的假"平价复跑"(E-0826-D)⇒ **把正确的 +0.187 撤回并指控前视泄漏**。同一预测双口径对照终证: simple +0.187/2026+0.45, log −0.030/2026−2.04。」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:415` — 「- **含义:** 装置 `w10_universe.py` 的 `CAL=simple`(默认)把 y4 当对数收益做 expm1, 给每名加了 (Σr)²/2 ≈ σ²/2 的伪项; 对空高波动名的腿(king)= 每锚 −2~−3 bps 的**伪拖累**。」
  - `docs/ERROR_LEDGER_2026-08-20.md:416` — 「**装置 CAL=log 分支 = 原始 y4 = 无偏简单口径**(与真简单差 −0.04 bps/锚), 复验一律用 CAL=log;」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「08-26/09-04 的"V2MAIN 净≈0"读数(combo_recheck: C−A log +0.005 / 复利 +0.079, P 0.50/0.79, 装置刻度 net_ex)属于装置刻度」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「每 gross 口径下 V2MAIN 贡献在三口径、双种子的 2024→26 全为 CI>0」
- **A reader could wrongly conclude:** A reader passes CAL=simple as the 'exchange caliber' to w8/w10 replays, or cites +0.187 as the verified V2MAIN blend gain.
- **Affects:** future_eval, reporting · **Severity reason:** Calls CAL=simple (expm1) the exchange simple-return caliber and +0.187 the 'correct' number. E-0904-F showed expm1 on the Σ5m simple-return panel is pseudo-convex and CAL=log (raw y4) is the unbiased caliber; on it the V2MAIN blend gain is +0.005 on the device scale.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, E-0904-F): 本条对 CAL 语义的描述已过时 —— 对 pod 5m 面板(y4 = Σ5m 简单收益), `CAL=simple` 的 expm1 是伪凸性, 不是交易所简单收益; 无偏口径 = `CAL=log`(= 原始 y4)(ERROR_LEDGER L397–398)。「正确的 +0.187」是 CAL=simple 读数: 无偏口径复测 combo C−A 装置刻度 log +0.005 / 复利 +0.079, 每 gross 口径 V2MAIN 贡献 CI>0(docs/RESULT_f10_caliber_sensitivity_2026-09-05.md L191)。本条的防错规则(枚举白名单 / 自报 config / 逐字复跑)仍有效。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-35 · P2 · DOC_STALE
- **Source:** `memory/giveback_baserate_replay_2026_09_06.md:3`
- **Quote:** 「≈6.5 days/yr ≤ −2.68%, 1–2 days/yr ≤ −4% (all 2025-04/05), worst 3-anchor −6.5…−7.1%, worst month −17%」
- **Superseding evidence:**
  - `docs/CALIBER_STATUS_2026-09-09.md:26` — 「- 尾部: **一律是下界**(全史最差日 −6.04% → −11.17%, maxDD 41.5% → 44.8%; 最差月 −17%、≤−4% 日 1–2/年 同此)。」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「3. **回撤尺子**: 表中 maxDD 是累计 g 的算术峰谷差(单位 gross), ×2 只是线性近似; 按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**; W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%。」
  - `docs/RULINGS_requested_2026-09-12.md:8` — 「修后全史真 maxDD 阶梯 2.0×: 停机 1.09–1.31/年, maxDD −44%」
- **A reader could wrongly conclude:** A reader treats '1-2 days/yr ≤ −4%, worst month −17%' as the book's tail profile when setting leverage or stop expectations, understating tail frequency and depth.
- **Affects:** reporting, live_trading · **Severity reason:** These base rates come from the pre-v4 health-check replay on a 2024→26 window with clip-compounded labels. CALIBER_STATUS says tail figures are lower bounds (full-history worst day −6.04% → −11.17% after correction), and the window leaves out 2023 (compounded 2× NAV maxDD −28.92%).
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): these are lower bounds on a window that omits 2023. After the clip-compound fix (E-0908-B) the full-history worst day moved from −6.04% to −11.17% and maxDD from 41.5% to 44.8%; 'worst month −17%, ≤−4% days 1-2/yr' are likewise lower bounds (docs/CALIBER_STATUS_2026-09-09.md L26). The v4 per-year table adds 2023 (Sharpe −1.94, compounded 2× NAV maxDD −28.92%; W_ALPHA −42.12%; TABLE_per_year_v4 L11/L27). For leverage, use the full-history true-maxDD ladder in RULINGS_requested_2026-09-12 R-2 (at 2.0×: halts 1.09-1.31/yr, maxDD −44%).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-36 · P2 · DOC_STALE
- **Source:** `memory/giveback_baserate_and_tail_levers_2026_09_06.md:3`
- **Quote:** 「≤−2.68% 日 ≈6.5/年, ≤−4% 1–2/年, 最差 3–6 锚窗 −6.5~−7.6%」
- **Superseding evidence:**
  - `docs/CALIBER_STATUS_2026-09-09.md:26` — 「- 尾部: **一律是下界**(全史最差日 −6.04% → −11.17%, maxDD 41.5% → 44.8%; 最差月 −17%、≤−4% 日 1–2/年 同此)。」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:30` — 「| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「3. **回撤尺子**: 表中 maxDD 是累计 g 的算术峰谷差(单位 gross), ×2 只是线性近似; 按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**; W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%。」
  - `docs/RULINGS_requested_2026-09-12.md:8` — 「修后全史真 maxDD 阶梯 2.0×: 停机 1.09–1.31/年, maxDD −44%」
- **A reader could wrongly conclude:** A reader cites '≤−4% 日 1–2/年, 最差月 −17%' as the tail profile for leverage or stop settings, understating tail risk.
- **Affects:** reporting, live_trading · **Severity reason:** Same base rates as the English twin: pre-v4 health-check replay on 2024→26 with clip-compounded labels, so the tails are lower bounds and the 2023 loss year is excluded.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 本条基率是 pre-v4 体检回放 2024→26 窗口的读数, 标签为裁剪复利口径 ⇒ 尾部一律是下界(裁剪纠错后全史最差日 −6.04% → −11.17%, maxDD 41.5% → 44.8%;「最差月 −17%、≤−4% 日 1–2/年」同为下界, docs/CALIBER_STATUS_2026-09-09.md L26), 且不含 2023(v4 A0: Sharpe −1.94, 年内 2× 复利 NAV maxDD −28.92%; W_ALPHA −42.12%, TABLE_per_year_v4 L11/L27)。杠杆决策引 RULINGS_requested_2026-09-12 R-2 的全史真 maxDD 阶梯(2.0×: 停机 1.09–1.31/年, maxDD −44%)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-37 · P2 · DOC_STALE
- **Source:** `memory/giveback_baserate_replay_2026_09_06.md:10`
- **Quote:** 「anchor-level big losses are mostly the known "book is structurally short the alt premium" squeeze」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。」
  - `docs/DIAG_live_giveback_root_cause_2026-09-09.md:5` — 「③ 「β 中性反事实 = 原书」系我误读自己的表(逐年 β 部分 −0.264/+0.199/+0.080; 无成本残差 2024 0.56→0.82, 2025 0.76→0.56, maxDD 1254→989 — 诊断量, 非可交易对冲) ⇒ §3「β 对冲无物可对」撤回;」
- **A reader could wrongly conclude:** A reader attributes big-loss anchors to a structural short-alt-premium exposure and designs alt−BTC hedges or 'expected squeeze' narratives on an unverified premise.
- **Affects:** future_eval, reporting · **Severity reason:** 'Book structurally short the alt premium' rests on the 08-21 receipt (β −0.249, corr −0.767) from a different instrument. On the v4 A0 book T8 measures corr(NET, forward alt−BTC spread) at +0.05 and lists the 78% dominance-premium reading as not transferable and unreconciled.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): the '70% of ≤ −40 bps anchors are short-side dominated' count is this note's own measurement and stands, but 'book is structurally short the alt premium' is not established for the current book. On v4 A0, corr(NET, forward equal-weight alt−BTC spread) = +0.0506 / +0.0434, and the 08-21 '78% dominance premium' receipt comes from a different instrument, listed as unreconciled (uplift_r2 T8 RESULT L75). The 09-09 root-cause review also withdrew 'β hedge has nothing to hedge' (DIAG_live_giveback_root_cause_2026-09-09 L5 ③).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-38 · P2 · DOC_STALE
- **Source:** `memory/live_giveback_is_long_extreme_funding_blowups_2026_09_06.md:3`
- **Quote:** 「execution ≈ 0.15 bps/anchor is not a cause」
- **Superseding evidence:**
  - `docs/RESULT_giveback_attribution_live_2026-09-06.md:10` — 「5. **执行不是原因。** 费用 ≈ 2.8 bps × 换手 4–6% ≈ 0.15 bps/锚/gross, 相对 ±40–90 bps 的锚级波动可忽略;」
  - `docs/DIAG_live_giveback_root_cause_2026-09-09.md:5` — 「① 两个平仓锚(08-26 12Z / 09-06 08Z)的代理外推无效, 本地 fills 缺平仓成交(数量闭合缺口 29.8k / 163.5k USDT), 09-06 日残差 −671 USDT **未闭合** ⇒ 「账本逐日闭合 / 执行不是原因」撤回;」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md:38` — 「- **V2MAIN 与执行器层没有测量, 一律不能排除。**」
- **A reader could wrongly conclude:** A reader closes execution as a cause of the 08-22→09-06 giveback (and of September losses) and stops reconciling fills and flatten costs.
- **Affects:** reporting, live_trading · **Severity reason:** 0.15 bps/anchor counts only fees × turnover. The 09-09 review found local fills miss the flatten fills (29.8k of 163.5k USDT) and an unclosed −671 USDT residual on 09-06, and withdrew 'execution is not a cause'; T5d (09-13) leaves the executor layer unmeasured for September.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): 'execution ≈ 0.15 bps/anchor is not a cause' is withdrawn. The 0.15 counts only fees × turnover (RESULT_giveback_attribution_live_2026-09-06 L10). The 09-09 root-cause review accepted that the two flatten anchors' proxy extrapolation is invalid, local fills lack the flatten fills (quantity gap 29.8k / 163.5k USDT) and the 09-06 residual of −671 USDT is unclosed, so 'ledger closes daily / execution not a cause' is withdrawn (DIAG_live_giveback_root_cause_2026-09-09 L5 ①). For September, T5d states the V2MAIN and executor layers were not measured and cannot be excluded (uplift_r2 T5d RESULT L38).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-41 · P2 · DOC_STALE
- **Source:** `memory/allweather_campaign_2026_09_05_verdict.md:8`
- **Quote:** 「目标不可达且能量化: 2024/2025 单年 Sharpe 1.24/1.14, 中位季度 1.1」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:10` — 「| 2022(06-30 起) | 1110 | +0.159 | +0.48 | +0.48 | +0.36 | 5.6% | 11% |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:29` — 「5. **探索性日块自举 Sharpe CI95**(研究员新增, 2000 次, UTC 日块, 保留日内依赖不保留跨日; rng [20260905,k]): 原钉 W_ALPHA **[0.3207, 2.2822]**(SE 0.4890)」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:43` — 「(CI95 下界过 3.0)要求点估计 ≈ 3.966。** 距离当前书 **5.18 SE**。」
- **A reader could wrongly conclude:** A reader plans all-weather work assuming the worst live-form year is around Sharpe 1.1 and that a ×2.5 uplift in weak years reaches the target, when the full cycle contains a −1.94 year.
- **Affects:** future_eval, reporting · **Severity reason:** Frames 2024/2025 (Sharpe 1.24/1.14) as the weak years of the live form. The v4 full-cycle table has 2023 as a loss year (Sharpe −1.94) and full-cycle Sharpe 1.29 [0.32, 2.28], so the 'weak-year net ×2.4-2.6' arithmetic understates the gap; the later closeout gives the target arithmetic.
- **Proposed correction (exact text):** ⚠ 补(2026-09-13 审计): 「弱年 = 2024/2025(Sharpe 1.24/1.14)」只在 2024→26 窗成立。v4 A0 全周期逐年表: 2022(06-30 起)+0.48、2023 −1.94、全窗 Sharpe 1.29(日块 CI95 [0.32, 2.28])(TABLE_per_year_v4_caliber_2026-09-12.md L10–15/L29)⇒ 最差年是负年, 「弱年 μ ×2.4–2.6」的算术不适用于 2023。目标算术以 uplift_2026-09-11 CLOSEOUT §2 为准(CI95 下界过 3.0 需点估计 ≈3.966, 距现书 5.18 SE)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-43 · P2 · DOC_STALE
- **Source:** `memory/carry_sleeve_second_premium_diagnostic_2026_09_05.md:20`
- **Quote:** 「carry sleeve 的决定量是换仓规则(滞回可降换手但未评估, 是新臂)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md:10` — 「1. **Verdict under the frozen rule: NOT PASS (multiplicity).** No arm is PASS_adj; A05, A06, A08 are PASS_unadj; the nested selection passes. The label comes from the frozen trichotomy (PREREG §5.3). What actually blocks each group differs:」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md:14` — 「2. **Hysteresis removes the turnover problem.** Break-even all-in cost per unit notional turnover over W is **62.7–109.3 bps** across arms (A01 76.9, A02 96.3), against 13.92 assumed. The frozen top-K rule of 09-05 broke even at 5.4/8.7. Spot at 5 or 15 bps moves S2426 net by only ±0.008–0.020.」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md:22` — 「7. **The two basis markings disagree in sign.** On identical positions, marking with Binance perp/spot closes (B1) instead of the frozen premium index (B2) turns every arm negative. A01 S2426 goes from +0.266 to −0.696 (SR −1.43), W from +0.204 to −0.333.」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L4b/RESULT_L4b.md:10` — 「1. **No arm survives POST-HOC-FAMILY-2** (N_F2 = 8; cumulative ledger 12 + 8 = 20). Every arm fails **P1**, because 2025 is negative under the primary marks (−0.17…−0.38 bps/anchor).」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:79` — 「**⇒ 在按原始 1m K 线重建可执行退出价之前, 不得把 carry 袖提交用户裁定**」
- **A reader could wrongly conclude:** A reader queues the hysteresis carry sleeve as an untested new arm, or submits it for a user ruling on premium-index-marked P&L.
- **Affects:** future_eval · **Severity reason:** Hysteresis was evaluated on 09-13 (L4): it fixes turnover (break-even 62.7-109.3 bps per unit turnover), but the frozen verdict is NOT PASS, the sign flips with forced-exit marks, and under executable 1m exit marks no arm survives (L4b).
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 滞回换仓已评估(uplift_r3 L4): 换手问题解决(break-even 62.7–109.3 bps/单位换手), 冻结判词 NOT PASS(多重比较); 同一仓位改用永续/现货收盘价标价全部臂转负, 差距全在下架/停止结算的强制退出持仓(L4 RESULT L10/L14/L22)。L4b 用原始 1m 可执行退出价重算后「No arm survives」(L4b RESULT L10)。在按原始 1m K 线重建可执行退出价之前不得把 carry 袖提交用户裁定(uplift_r3 PROGRAM L70)。本条「零成本 Sharpe 12–44」只是忽略基差与强制退出标价的上界。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-44 · P2 · DOC_STALE
- **Source:** `memory/funding_transfer_priced_in_settlement_window.md:10`
- **Quote:** 「FTRIM(全 4h 排除, +0.21)」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:48` — 「| FTRIM 单独 | −0.044/−0.13 | +0.042/+0.04 | −0.070/−0.15 | **−0.018/−0.08** | 中性偏负; 旧口径 +0.21 是伪凸性 |」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
- **A reader could wrongly conclude:** A reader cites the live FTRIM layer as a proven +0.21 gain when reasoning about carry-reduction layers or FTRIM hard-exit variants.
- **Affects:** live_trading, reporting · **Severity reason:** +0.21 is the CAL=simple pseudo-convexity figure. Under the unbiased caliber FTRIM alone is −0.018 over 2024→26 (neutral to slightly negative), and its deployment basis was declared void.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计, E-0904-F): 「FTRIM +0.21」是 CAL=simple 伪凸性读数; 无偏口径下 FTRIM 单独 2024→26 −0.018(逐年 −0.044/+0.042/−0.070, 中性偏负), 「三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废」(docs/RESULT_caliber_revalidation_2026-09-04.md L48/L52)。并读时改为「FTRIM(全 4h 排除)书层效应未检出」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-03 · P2 · DOC_STALE
- **Source:** `memory/two_rulings_deployed_20260810.md:3`
- **Resolution:** XREF AUDIT_EXEC CFG-04 — CROSS-REF: same restart fact in a second note; owner AUDIT_EXEC CFG-04.
- **Quote:** 「②chase 政策A全不追(ARM_WEIGHTS chase=0)。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/live/chase_policy.py:144` — 「ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.5, ARM_NO_CHASE: 0.5}」
  - `/Users/haosiyu/dl_quant_live/live/chase_policy.py:142` — 「# 2026-09-01 重启(PREREG_chase_restart_2026-09-01, sha 1a3f433325ae, 用户裁定): combo 时代重算」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1664` — 「# ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
  - `/Users/haosiyu/dl_quant_live/ops/ic_monitor.py:17` — 「★ 标定身份(2026-09-12 独立复核): 阈值标定于 α=0.05/band=0.002 的离线书; 在役书 α=0.1/」
- **A reader could wrongly conclude:** A reader assumes chase=0 and executor-side α=0.3 EMA are live, which skews top-up/residual attribution and turnover expectations.
- **Affects:** live_trading, reporting · **Severity reason:** This deploy record reads like current policy, but both rulings were later replaced: α became 0.05 the same day and has not been applied to the external book since 08-22, and chase was restarted at 50/50 on 09-01.
- **Proposed correction (exact text):** [description 末尾追加] 【2026-09-13 状态: ① 同日再改 α 0.3→0.05(deepsmooth), 且 08-22 起外部书分支不施 harvest EMA/中性带(anchor_loop.py L1664–1666), 在役平滑在生产者(α=0.1/band=0.00025); ② 政策A 已于 09-01 被重启的 50/50 随机实验取代(chase_policy.py L144)】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-06 · P2 · DOC_STALE
- **Source:** `memory/maker_slippage_is_negative.md:15`
- **Resolution:** XREF AUDIT_DATA RET-02 — CROSS-REF caveat: r14 / r21 markout and cost readings quoted in the correction were computed from the ±0.30-clipped ret5 channel (AUDIT_DATA RET-02) ⇒ tail-sensitive quantities in them are lower bounds.
- **Quote:** 「**加上手续费后挂单的合计成本是 −0.254 bps —— 近乎免费, 甚至倒赚。**」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r14_estimand/RESULT_r14_cost_estimand_2026-09-12.md:13` — 「那面墙"贵了 2.20 bps/单位成交"里, **1.6457 bps 是 maker 成交价的优惠, 而那个优惠的另一半就是 45.48% 的成交率**。回放**按 100% 成交 |Δw| 并按模型价收费**。**只把价格调便宜、不同时给不成交的那一半定价, 是不允许的。**」
  - `multi_asset/exports/research/uplift_2026-09-11/r21_nulls_costbridge/RESULT_r21_nulls_costbridge_2026-09-12.md:129` — 「**这正是 r14 §6 那句话的第一手量化: maker 优惠与 taker 追价是同一次选择的两半, 回放按 100% 成交、模型价收费大致对冲了它们。**」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:15` — 「**未成交组价格朝交易方向跑 +29.2 bps [13.7,44.7]**(已成交 −4.1)—— 挂不到的恰是信号最对的那一半。」
  - `multi_asset/exports/research/uplift_2026-09-11/r14_estimand/RESULT_r14_cost_estimand_2026-09-12.md:11` — 「`mid_at_anchor` 不是锚时刻 E 的中价, 而是**执行器锚运行起点**的中价 —— 在役形态下那是 **E+24 分钟**。」
- **A reader could wrongly conclude:** A reader cuts the cost model or argues for more passive or slower execution using −0.254 bps alone, which r14 explicitly forbids.
- **Affects:** future_eval, reporting · **Severity reason:** "Maker is nearly free" counts only filled trades. Later same-fill receipts show the maker price edge is the other half of adverse selection on the intents that did not fill.
- **Proposed correction (exact text):** [L15 后插入] > **【2026-09-13 限定】** −0.254 只是**已成交** maker 的价格+费; 它与未成交是同一次选择的两半 —— r14: 「只把价格调便宜、不同时给不成交的那一半定价, 是不允许的」; r17(CANONICAL ⑦): 未成交组价格朝交易方向跑 +29.2 bps [13.7,44.7](已成交 −4.1); r21: maker 层模型多收 +6.17 与 taker 补单层少收 13.7 按名义混合 +2.96 含零。「挂单近乎免费」不得单独用于成本重定价或执行政策论证。参照价: 08-22 起 mid_at_anchor 取于执行器运行起点 E+23–24 分, 非 E(r14)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-07 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/turnover_cost_reaudit_2026_08_21.md:3`
- **Resolution:** XREF AUDIT_DATA RET-02 — CROSS-REF caveat: same clipped-ret5 provenance applies to the ERA2 re-measurement this row asks for; state the caliber when it is finally measured.
- **Quote:** 「all-in cost per unit INTENDED turnover 3.52 bps [0.32,6.64] = cash −1.28 (maker fee +1.75, rounding edge −2.03, top-up +0.14, reject drift −1.13) + opportunity +4.6×10% unfilled」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/PREREG_T3_markout_curve_2026-09-13.md:57` — 「**敏感性 ERA1:** 偏移 ≤ 3 分钟(2026-08-01..08-22 04Z, 140 名旧书), 单独报, 不参与判决。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:82` — 「| **212** | **ERA1 R1**(140 名旧书, 延迟 ≈1 min, 21 日) | 2,431 | **+4.97** | **[+2.18, +7.85]** | 0.747 | **落在 FAIL 区**; 子集毛额 +17.24 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:87` — 「两个时代的冻结读数一个偏低一个偏高, 方向都由窗口里实现的毛额决定, 不由执行决定。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:53` — 「| **c_eff** | **+1.13 [−15.87, +24.74]** | −4.78 [−10.84, +4.79] | −12.13 [−34.21, +16.17] |」
  - `multi_asset/exports/research/uplift_2026-09-11/r14_estimand/RESULT_r14_cost_estimand_2026-09-12.md:11` — 「`mid_at_anchor` 不是锚时刻 E 的中价, 而是**执行器锚运行起点**的中价 —— 在役形态下那是 **E+24 分钟**。」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:15` — 「已发组意图加权成交 **0.848**(ZERO_TARGET 0.911)」
- **A reader could wrongly conclude:** A reader treats 3.52 [0.32, 6.64] as the live combo book's execution cost (break-evens, κ penalties, seat/turnover gates), even though it was not measured on this book and is not stable across windows.
- **Affects:** future_eval, future_retrain · **Severity reason:** The only all-in per-intent cost number comes from one ERA1 window (old 140-name book, execution ≈E+1 min). The live combo book (ERA2: E+23–24 min, 450 names) was never re-measured on this estimand, and T3 shows the estimand's sign follows the window's realised returns.
- **Proposed correction (exact text):** [append at end] **Scope note (2026-09-13 audit):** 3.52 [0.32, 6.64] is an ERA1 reading (old 140-name in-role book, executor start ≈E+1 min, chase A, 08-10→08-21). It has NOT been re-measured on the live combo book (ERA2 from 2026-08-22 08Z: executor run start E+23–24 min; `mid_at_anchor` = run-start mid, not E, per r14; sent-intent fill 0.848 per r17). T3 (09-13) shows this per-intent estimand's sign follows the window's realised subset return, not execution (ERA1 R1 +4.97 [2.18, 7.85] vs ERA2 all plans −4.78 [−10.84, +4.79]). Quote it as "ERA1 single-window, not the live-book cost"; COST=3.52 in frozen DL recipes is a training constant, not a measured current cost.
- **Confidence:** INFERRED (every scope fact is VERIFIED from opened receipts; "never re-measured on ERA2 with the same all-in per-intent estimand" is inferred from searching docs/*.md, STATE.md and the U1/U2 cost RESULTs. The nearest ERA2 readings (T3 R0, r21 bridge, 09-05 ITT cost) use different estimands.) · **Quote re-verified at assembly:** exact

### M3-08 · P2 · DOC_STALE
- **Source:** `memory/execution_joint_curve_programme.md:11 (+1 more)`
- **Resolution:** XREF AUDIT_EXEC CFG-06 — CROSS-REF: the placement eps 0.50 basis is owned by AUDIT_EXEC CFG-06, now frozen as PREREG_placement_eps050_reread_2026-09-16 (2b94d71f → e51fbf2f). ⚠ This row's correction text reports per-arm markout (behind −7.69 vs join −2.40); that reading predates the blinding rule and must NOT be repeated forward — see CRON-13.
- **Quote:** 「1. 挂单深度 — **已在学**: placement bandit 三臂实盘随机化(join 3703/behind 2081/exempt 550, ε=0.35), 每单带 `placement_arm` 标签。
2. 等待/追单 — **已在价**: chase 随机实验, 三日随机化 1005/1401。」
- **Superseding evidence:**
  - `STATE.md:124` — 「★ bandit 采纳部署**: 恰一次主判(f657efde 冻结配方, 21 日块)ΔV **+1.658 CI95[+1.102,+2.280]>0** + 死法①弹性证伪(Δ成交率+1.0pp<2pp)同触 + 不毒 ⇒ 用户字采纳 **eps 0.35→0.50**」
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:7` — 「**behind: 冻结判据 UNDECIDED, 且毒性线翻转**: 锚内配对全包成本 behind − join = −4.84 bps [−20.7, +1.9](未决), 成交价优 3.7 bps、首次拒单率 21.5% vs 29.9%; 但 **markout60(覆盖 95%)behind −7.69 vs join −2.40, Δ −5.28 [−14.19, −0.33]**」
  - `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md:51` — 「成交后 markout 对纸面书与真实书同样发生, 不是相对纸面的执行成本; ITT 成本已完整计入成交价与补单。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:95` — 「在役 `config/book.json`(sha `f6fd6d0e…`): k_seconds **900**, placement ε **0.5**, 重挂实验 p **0.5**; ERA2 运行起点 E+23.0→24.0 min」
  - `/Users/haosiyu/dl_quant_live/live/chase_policy.py:142` — 「# 2026-09-01 重启(PREREG_chase_restart_2026-09-01, sha 1a3f433325ae, 用户裁定): combo 时代重算」
- **A reader could wrongly conclude:** A reader plans execution work assuming ε=0.35 and "behind is not toxic", or optimises per-arm markout as if it were a cost relative to the replay.
- **Affects:** live_trading, future_eval · **Severity reason:** The live execution parameters and axis status have changed: ε=0.50 adopted 09-01, behind found more toxic on full-coverage markout 09-05, chase restarted 09-01. Treating markout as an execution cost was also later ruled out.
- **Proposed correction (exact text):** [L12 后插入] **【2026-09-13 状态】** ① 深度轴: 09-01 bandit 主判 ΔV +1.658 CI>0 采纳 ε 0.35→0.50; 09-05 全覆盖(95%)markout: behind −7.69 vs join −2.40(Δ −5.28 [−14.19,−0.33])推翻 09-01「不毒」, 维持 0.50 不扩大; ② 追单轴: 08-10 政策A 之后于 09-01 重启 50/50 随机实验(PREREG_chase_restart_2026-09-01); ③ 口径: 成交后 markout 对纸面/真实书同样发生, 不是相对回放的执行成本(RESULT_requote_and_behind 09-05; r14: 成交后路径 100% 在 y4 内), 逐臂比较用计划级 ITT 全包成本 vs 决策价 + 未成交机会成本。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M3-09 · P2 · DOC_STALE
- **Source:** `memory/capacity_two_calibers.md:15`
- **Quote:** 「- **路线**: T1=9-10 入金150k(爬坡+逐档实测) → T2=300k(帽+回撤阶梯+流动性排序flatten 三前置) → T3=500k(T2曲线裁定)。」
- **Superseding evidence:**
  - `docs/PLAN_deposit_2026-09-10.md:3` — 「**作废条件:** 入金执行并裁定杠杆后并入 STATE.md」
  - `STATE.md:115` — 「★ 入金 +62,998 USDT(12:44:01Z 到账, 权益 84,036)· 用户裁定"一步到位"**: 16:00Z 锚按 constant_leverage_2.0 直接 sizing 至 gross ≈168k(现 41.7k, ×4.0), 不爬坡。」
  - `docs/PLAN_deposit_2026-09-10.md:15` — 「**阶梯家族在本书 2.5× 下判负**。」
  - `STATE.md:4` — 「NAV 117,566.70(−207U 含佣金)」
  - `STATE.md:202` — 「**★ 已知未修(09-07 登记, E-0907-B): combo 混合后未重新施逐名帽** —— king 形态 20/20 锚 0 名超帽, **combo 形态 20/20 锚都有 2–10 个名超帽, 中位超出 3.0%**」
- **A reader could wrongly conclude:** A reader plans capacity steps around a void 150k/300k/500k route with a refuted ladder as a prerequisite, or applies a liquidity cap before the combo blend, where E-0907-B would undo it.
- **Affects:** future_eval, live_trading · **Severity reason:** The deposit roadmap and its prerequisites are superseded: the 09-03 deposit of 63k went straight to constant 2.0× (NAV ≈117.6k), and the drawdown ladder was refuted on this book. Any per-name cap must also account for E-0907-B.
- **Proposed correction (exact text):** [L15 后插入] **【2026-09-13 状态】** 路线已被实际执行取代: 09-03 入金 +62,998 USDT, 用户裁定「一步到位」constant_leverage_2.0(非 9-10 150k 爬坡); 09-13 NAV ≈117.6k、目标 gross ≈235k; 受据 PLAN_deposit_2026-09-10 按其作废条件已失效。「T2 前置 = 回撤阶梯」不成立: 同文 §1 已判阶梯家族在本书判负(快崖)。逐名流动性帽若立项, 须在 combo 55/45 混合**之后**施加(E-0907-B: 混合后未重施逐名帽, 20/20 锚 2–10 名超帽)。500k×2.5 各读数是 08-27 书与 qv4h 的快照, 引用前按当日书重测。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-11 · P2 · DOC_STALE
- **Source:** `memory/adaptive_turnover_family_closed.md:13`
- **Resolution:** SOFTENED to the K2 vocabulary: the T8 reading is 'FAIL: failed to detect; usefulness not excluded', not a demonstration of absence.
- **Quote:** 「在役 (α=.05, b=.002, target) = 联合最优 —— argmax(.02,.002) Δ+0.099 CI[−.026,+.235] 噪声内;」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/ops/ic_monitor.py:17` — 「★ 标定身份(2026-09-12 独立复核): 阈值标定于 α=0.05/band=0.002 的离线书; 在役书 α=0.1/」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:137` — 「| (d) "slower is better" (b/α 0.005 beats the deployed 0.0025) | **survives as a POINT ESTIMATE only** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:79` — 「**与 `adaptive_turnover_family_closed`(08-11)一致并扩展**」
  - `memory/adaptive_turnover_family_closed.md:17` — 「作废条件: 信号栈/成本口径换代 ⇒ 重测」
- **A reader could wrongly conclude:** A reader treats the live smoothing corner as proven optimal and closes smoothing/band research, while the v4 grid keeps "slower is better" alive as a point estimate.
- **Affects:** future_eval · **Severity reason:** "In-service = joint optimum" was measured on the old 9821-anchor internal book. Live smoothing is now the producer's α=0.1/b=2.5e-4, so the note's own invalidation condition (signal-stack change) has fired.
- **Proposed correction (exact text):** [L13 后插入] **【2026-09-13 状态】** ①「在役 (α=.05, b=.002) = 联合最优」只属 08-11 旧内部书(9821 锚); 08-22 起在役为外部 combo 书, 执行器不施 EMA/带(anchor_loop.py L1664–1666), 平滑在生产者 α=0.1/band=0.00025 —— 本条作废条件「信号栈换代 ⇒ 重测」已触发; v4 钉上 r12/r18 平滑网格: 真 maxDD 门下 (0.05, 2.5e-4) 等「更慢更好」只以点估计存活(Δg CI 含零), 未录取。② 自适应换手「感知门」结论仍被 T8(09-13, A0 v4, 24 列多变量样本外 r≈0)支持并扩展。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-14 · P2 · DOC_STALE
- **Source:** `memory/vol_predictable_but_acting_loses.md:10`
- **Resolution:** XREF AUDIT_EXEC CFG-07 — CROSS-REF: risk-budget keys are inert in external mode — owned by AUDIT_EXEC CFG-07.
- **Quote:** 「②P2动态gross必须非对称条件式, 通用vol-target已判负 ③在役RB形式正确无需升级。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1664` — 「# ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,」
  - `/Users/haosiyu/dl_quant_live/live/external_book.py:23` — 「· it does not apply EMA / neutral band / risk budget — the producer's weights ARE the target」
  - `/Users/haosiyu/dl_quant_live/config/book.json:153` — 「"book_source": "external",」
- **A reader could wrongly conclude:** A reader assumes live sizing already down-weights high-σ names and dismisses vol-aware sizing as redundant, or builds replays with an RB the live book does not have.
- **Affects:** future_eval, live_trading · **Severity reason:** Says an in-service risk budget (RB) exists and needs no upgrade; the live external-book path applies no risk budget.
- **Proposed correction (exact text):** [替换 ③] ③ ~~在役RB形式正确无需升级~~ 【2026-09-13 更正】RB(book.json risk_budget α .5/λ 1.0)只属旧内部书; 08-22 起在役外部 combo 书不施风险预算(anchor_loop.py L1664「no compose_book, no risk budget」; live/external_book.py 模块说明)。本条 vol-targeting 判负(9821 锚旧书)未在 v4 在役书上复测。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-15 · P2 · DOC_STALE
- **Source:** `memory/engine_replay_is_not_the_live_book.md:3`
- **Resolution:** XREF AUDIT_EXEC CFG-07 — CROSS-REF: legs.py / risk budget belong to the retired internal book — owned by AUDIT_EXEC CFG-07.
- **Quote:** 「★★★ 引擎正典回放与在役 legs.py 差两处结构(归一 + 风险预算) ⇒ 至今全部离线权重/腿决定测在一本不是实盘那本的书上」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:153` — 「"book_source": "external",」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1664` — 「# ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,」
  - `docs/REPORT_code_and_research_2026-09-13.md:133` — 「**经济材料性裁定 = FIT**。41 锚上 replay 与在役书的 Δg(同一真实收益向量, 单位 gross)」
  - `STATE.md:6` — 「连续 combo 历史链仍 0/41, S2 全史数字须标「生产路径历史 combo 链未被 S1 认证」」
- **A reader could wrongly conclude:** A reader builds or trusts replays that reproduce legs.py normalisation and risk budget as "live-isomorphic" when the live path skips both.
- **Affects:** future_eval · **Severity reason:** Describes legs.py L1+RB as the live book. Since 08-22 the live book is the producer's external target, so replay-vs-live gaps must be framed against the combo producer.
- **Proposed correction (exact text):** [description 末尾追加] 【2026-09-13: 本条两处源码差属 08-22 前内部书(legs.py); 在役外部书不走 legs.py/RB(anchor_loop.py L1664–1666)。现行对账: R22 在 41 锚上 replay vs target_live 残差很小(基线残差测量, 非资格证, 见 replay_residual_is_economically_immaterial_2026_09_13); 生产路径历史 combo 链 0/41 未被 P2 S1 认证】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-16 · P2 · DOC_STALE
- **Source:** `memory/book_has_implicit_stop.md:10`
- **Quote:** 「**① 在役逐名止损书级通过**: 净额代价仅 −2.8%, 夏普 +0.02, 尾部 +4%, 逐年=从好年向磨损年转移(2024 +28%)。回放触发173/年 vs 实盘18/年(10×)⇒ 真实代价更小。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:21` — 「08-20..09-12 执行器止损共触发 25 次, 队列名 0 次;」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「**已停的多头仓位不会被平到 0**。执行器先把已停名目标置 0, 随后 reshape 的去均值给所有名同一个平移 a」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「W1 ∪ W2 共 125 个「已停且持仓」实例: 多头 add_blocked **94** / reduced **23**」
  - `STATE.md:6` — 「⑤ **W9「157 次止损没平掉」**应为 157 个「锚×名」实例(20 名、59 锚; 146 落非 flatten_only 桶、7 正常、4 未分类), 不是 157 次独立失败平仓」
  - `STATE.md:146` — 「- **止损/风控**: 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)⟺ book_source=external 耦合; 看门狗 cond2 日亏 −4% flatten(口径 0aa6586)/ cond4 −25% 起始权益口径(57cb180);」
- **A reader could wrongly conclude:** A reader assumes the live per-name stop behaves like the replay stop layer (flatten to zero, ~18 triggers/yr) when sizing tail risk or judging replay-vs-live gaps.
- **Affects:** live_trading, future_eval · **Severity reason:** "The live stop passes at book level and triggers 18×/yr" belongs to the old internal book. On the current wide book the executor stop fired 25 times in 08-20..09-12 and did not flatten stopped longs until the W9 fix (ef60f85).
- **Proposed correction (exact text):** [L10 后插入] **【2026-09-13 限定】** ①「在役逐名止损书级通过 / 实盘18/年」属 08-20 前旧内部书(9821 锚、−25% 档)。在役外部书执行器逐名止损 = wide 档 −30%×连续2锚×冷却7天(STATE §1); 08-20..09-12 共触发 25 次(T5b); 直到 W9(f8beb082, 09-13 随 ef60f85 部署)前, 被止损多头因去均值平移 + 钳制未平到 0(T5b §5.3: 125 例中 add_blocked 94 / reduced 23; 上线以来 157 个锚×名实例)。回放止损层与执行器持仓路径不同(T5: 18.5% carry 差分量)。隐式止损结构论点未在 v4 在役书上复测。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-17 · P2 · DOC_STALE
- **Source:** `memory/graduated_stop_ooS_refuted.md:3`
- **Quote:** 「渐进/更深止损 OOS 判负 DO-NOT-RETRY; 在役-25%止损≈免费保险已在最优点;」
- **Superseding evidence:**
  - `STATE.md:146` — 「- **止损/风控**: 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)⟺ book_source=external 耦合; 看门狗 cond2 日亏 −4% flatten(口径 0aa6586)/ cond4 −25% 起始权益口径(57cb180);」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:20` — 「config `per_name_stop` enabled, profile wide(−30% / 连续 2 锚 / 冷却 7 天 / 5 USDT)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「**已停的多头仓位不会被平到 0**。执行器先把已停名目标置 0, 随后 reshape 的去均值给所有名同一个平移 a」
- **A reader could wrongly conclude:** A reader closes stop-design questions on the belief that the live stop is the tested −25% "free insurance".
- **Affects:** live_trading, future_eval · **Severity reason:** Calls the "−25% in-service stop" already optimal. The live per-name stop is the wide −30% × 2 anchors × 7-day-cooldown profile, and it failed to flatten stopped longs until W9.
- **Proposed correction (exact text):** [description 末尾追加] 【2026-09-13: 「在役-25%止损」属旧内部书; 在役外部书逐名止损 = wide 档 d30_n2_c42(−30%×2锚×冷却7天, STATE §1), 且 W9 前被止损多头未平到 0(T5b §5.3)。「免费保险/最优点」未在在役档与 v4 口径上复测】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-20 · P2 · DOC_STALE
- **Source:** `memory/drawdown_ladder_refuted_combo25.md:13`
- **Quote:** 「**How to apply**: 2.5× 裁定=入金后重议, 本质是用户风险偏好(接受 ~1/3 年窗距峰 −25% 水下);」
- **Superseding evidence:**
  - `STATE.md:115` — 「★ 入金 +62,998 USDT(12:44:01Z 到账, 权益 84,036)· 用户裁定"一步到位"**: 16:00Z 锚按 constant_leverage_2.0 直接 sizing 至 gross ≈168k(现 41.7k, ×4.0), 不爬坡。」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「**Full-history tail of the fixed book at 2.0× (raw replay vol): maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.**」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「W_FULL(10038 锚) C0_s42 −46.42% / C0_s2027 −46.89% / NW −43.97%」
- **A reader could wrongly conclude:** A reader treats 2.5× as an open, pre-studied option backed by pre-v4 trip numbers.
- **Affects:** live_trading, future_eval · **Severity reason:** The pending 2.5× decision was settled at the 09-03 deposit (constant 2.0×), and the tail figures predate E-0904-F and the v4/r18 true-maxDD recomputation.
- **Proposed correction (exact text):** [L13 后插入] **【2026-09-13 状态】**「2.5× 裁定=入金后重议」已由 09-03 入金裁定取代: constant_leverage_2.0 一步到位(STATE 09-03 12:5xZ)。触线/回撤数字属 08-28 CAL=simple 旧口径; 引用尾部一律改读 v4 钉 r18 NW 固定书: 2.0× 全史 maxDD −43.9%/−44.5%, P(1y 真 maxDD≥25%) 26.8%/33.1%, 起点口径 21.2%/20.6%(r18 RESULT L12/L93); W_FULL 复利 NAV −46.42%/−46.89%(v4 逐年表勘误)。阶梯家族判负结论不变。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-22 · P2 · DOC_STALE
- **Source:** `memory/deposit_leverage_assessment.md:33`
- **Quote:** 「VIP 降费是入金的真实收益(每降 0.6 成本 ≈ +0.1 bps/锚)」
- **Superseding evidence:**
  - `multi_asset/exports/eda/ASSESSMENT_deposit_leverage_2026-08-10.md:81` — 「**§5.3 "VIP 档费率下降"不成立**: Binance 合约 VIP1 需 30 天成交量 ≥1500 万 USDT;」
  - `docs/PLAN_deposit_2026-09-10.md:75` — 「**VIP/费率**: @500k×2.5 月成交 ~$5.7M, 低于 VIP1($15M), 费率无档位红利;」
  - `docs/STATUS_three_questions_2026-09-12.md:23` — 「**BNB 手续费抵扣断了 6 天(09-07 起)**: 每锚 maker 恰 2.0000 / taker 恰 5.0000 bps, commission 全 USDT, 账户在 VIP0 底档。」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/RESULT_r18_foundation_2026-09-12.md:12` — 「**Full-history tail of the fixed book at 2.0× (raw replay vol): maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.**」
- **A reader could wrongly conclude:** A reader counts VIP fee cuts as a deposit benefit, or uses the 08-10 "2× median-year DD −24.8%" arithmetic for today's leverage decisions.
- **Affects:** reporting, future_eval · **Severity reason:** The VIP fee benefit was retracted in the same assessment's §7, and the leverage×drawdown arithmetic is an old-book offline splice since superseded by the v4 r18 tail.
- **Proposed correction (exact text):** [L33 后插入] **【2026-09-13 更正】**「VIP 降费是入金的真实收益」不成立(本评估 §7 已更正: VIP1 需 30 天成交 ≥1500 万 USDT; 500k×2.5 月量亦仅 ~$5.7M; 账户 09-12 仍 VIP0 底档)。③ 的杠杆×回撤算术属 08-10 旧内部书离线拼接; 在役书尾部改读 v4 钉 r18(2.0×: 全史 maxDD −43.9%/−44.5%, P(1y 真 maxDD≥25%) 26.8%/33.1%)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-24 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/premium_sleeve_budget_refuted_fomc_drift.md:10`
- **Quote:** 「Verdict: 可预注册上线候选 with conditions — restore form, stop-dilution listed separately and not counted, expectation +0.08~0.10 bps/anchor (+170–210 bps/yr, ΔS +0.05~0.06), FOMC only (no CPI), 2022-23 dominated / 2026 flipped ⇒ watch 09-16/10-28/12-09 forward.」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「该收据的书是 jpline `net_S1.npy`(08-21 在役书 S1, 9,821 锚)、收益是 `engine.replay_fullhist` 的 `src.Y4`」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。」
  - `STATE.md:201` — 「FOMC 16Z 预缩候选」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:16` — 「**无偏口径下实盘形态并不优于正典**(+0.691 vs +0.730), 旧口径的优势(+1.597 vs +1.216)是伪凸性产物;」
- **A reader could wrongly conclude:** A reader pre-registers or deploys the FOMC 16Z shrink on the live book using +170–210 bps/yr from a different book and caliber, or cites "72% sits in the premium sleeve" for today's book.
- **Affects:** future_eval, live_trading · **Severity reason:** The FOMC pre-shrink candidate and the premium-sleeve decomposition were measured only on the old 9821-anchor in-role book (with executor EMA/band) under the pre-E-0904-F caliber. T8 found the dominance-premium exposure does not transfer to the A0 v4 book, and the candidate is still listed as pending.
- **Proposed correction (exact text):** [append after Verdict] **Scope note (2026-09-13 audit):** every number here comes from the 08-21 in-role book S1 (jpline net_S1.npy, 9,821 anchors, engine src.Y4; EMA/band stack) under the pre-E-0904-F caliber. T8 (2026-09-13) measured corr(NET, forward alt−BTC spread) = +0.05 on the A0 v4 book (opposite sign to the −0.767 behind this reading) and states the premium reading does not transfer. The FOMC 16Z pre-shrink is still only a candidate (STATE §3) and has NOT been re-measured on the live combo book / v4 caliber; re-measure before any pre-registration, and read the 09-16 FOMC forward watch against a v4-caliber baseline.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-25 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/shortside_beta_is_paid_premium.md:13`
- **Quote:** 「**但全史 β 项 = +4,682 bps = 总利润 34%**(2022/2025/2026 下跌段大赚, 2023/24 上涨年小亏), 空头侧全史 +19,485 vs 多头侧 −5,705。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「该收据的书是 jpline `net_S1.npy`(08-21 在役书 S1, 9,821 锚)、收益是 `engine.replay_fullhist` 的 `src.Y4`」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。」
  - `docs/ERROR_LEDGER_2026-08-20.md:17` — 「**定性: 空头β保费的代价日**(受据: 该保费=历史利润 34%, β中性化毁 1/3 书 → 五臂全负 DO-NOT-RETRY)」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
- **A reader could wrongly conclude:** A reader explains current short-side losses as a paid β premium and closes β-related fixes as DO-NOT-RETRY without re-measuring on the live book (T1 places the September gap in the fund leg's short-side price); the ERROR_LEDGER already repeats the 34% figure.
- **Affects:** future_eval, reporting · **Severity reason:** The β-premium share (34%) and the −14.8% net-short-β exposure were measured on the old 9821-anchor internal book. The live book is now fund-leg dominant, and T8 found the related alt−BTC exposure has the opposite sign on A0 v4.
- **Proposed correction (exact text):** [L13 后插入] **【2026-09-13 适用域】** 全部读数属 08-10 旧内部书(9821 锚, 换装后 corrfund_causal_ac king 腿主导)。在役 combo 书(09-11 名义 fund 65% / king 19% / DL 16%)未复测 β 拆解; T8(09-13)在 A0 v4 上测得书净额与山寨−BTC 价差相关 +0.05(与 08-21 旧仪器 −0.767 反号), 明言旧「保费」读法不能迁移。引用「β 项 = 利润 34% / 五臂全负 DNR」前须在 v4 在役书上用 betaside 仪器重测; 九月空头亏损见 T1(fund 腿空头价格点估计)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-26 · P2 · DOC_STALE
- **Source:** `memory/funding_bucket_net_alpha.md:20`
- **Quote:** 「**书级实验终判(2026-08-30, PREREG d580eb2042ef)**: 三臂无一过CI门 ⇒ DNR; A3(剔≤−10bp)近失(+0.08bps/锚双种子一致, CI含零);」
- **Superseding evidence:**
  - `STATE.md:116` — 「★★★ 部署: FTRIM 负费率空头 z 层排除(用户字"确认无误可立即部署")」
  - `docs/RESULT_xregime_2026-09-02.md:95` — 「**候选① 部署**(书行为改动): 负费率空头 z 层排除 pre (−∞,−10] zero。」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:52` — 「**三项在役改动(M1/FTRIM/T400)在无偏口径下都不显著, 部署依据作废; 也未见可测伤害。**」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:13` — 「FTRIM 是分数级 pre_zero, 经 demean 泄漏为小空头, 58 锚均值 68% 标记名仍为负目标、付 A0 carry_ex 的 59.8%(毛节省)。」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:14` — 「仓位级 FTRIM 净 **+0.018**(省下 carry 的 77% 以放弃的价格还回; 2026 −0.20; 换手 +24%)⇒ **泄漏是真的, 修它是零和**」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:67` — 「FTRIM 之后, rn8 ≤ −10bp 的名只占 fund 腿空头 gross 的 **1–6%**(且是衰减中的旧仓)」
- **A reader could wrongly conclude:** A reader believes deep-negative-funding shorts are untreated in the live book (they are FTRIM-trimmed, with leakage), or re-opens or closes the family from 08-30 CAL=simple numbers.
- **Affects:** live_trading, future_eval · **Severity reason:** Records the ≤−10bp exclusion family as DNR, but a z-layer version (FTRIM) went live on 09-02. Its basis was later voided under the unbiased caliber, and v4 receipts show FTRIM leaks into small shorts and repairing it is zero-sum.
- **Proposed correction (exact text):** [L20 后插入] **【2026-09-13 后续】** DNR 之后 09-02 部署了同族 FTRIM(负费率空头 z 层排除 (−∞,−10bp], RESULT_xregime_2026-09-02 候选①)。其后: E-0904-F 无偏口径下 FTRIM 部署依据作废(不显著, 无可测伤害); v4 核查: FTRIM 为分数级 pre_zero, 经去均值泄漏为小空头(58 锚 68% 标记名仍为负目标), 仓位级 FTRIM 净 +0.018 零和(r15); U3: FTRIM 之后 rn8≤−10bp 名只占 fund 腿空头 gross 1–6%。本表名级/书级数字属 08-30 CAL=simple 旧口径, 引用前按 v4 重测; 「帽内≈3.2U/结算」按 08-30 书规模, 09-03 入金后须按当前 gross 重算。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-27 · P2 · DOC_STALE
- **Source:** `memory/funding_settlement_interval_unit_bug.md:11`
- **Resolution:** SOFTENED to the K2 vocabulary where the correction text issues a no-difference verdict. XREF AUDIT_TRAIN TRN-07 · AUDIT_DATA FND-01 / FND-02 — CROSS-REF: the funding settlement-interval unit family is owned by AUDIT_DATA FND-01/FND-02 (x0910 pull-time interval) and AUDIT_TRAIN TRN-07 (October recurrence); AUDIT_PROD PROD-40 holds the producer-side rn inflation.
- **Quote:** 「The live splice reproduces the **AS-TRAINED (un-normalised)** caliber *deliberately* (`funding_derive.py:110`), because the frozen king/s2 heads were trained on `wide_dl_full.npz`」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:106` — 「执行器 span 表(07-25 建)只被执行器自己的冻结 DL 面板读(`signal/funding_panel.py` L64–81), 在役外部书不经过它。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:122` — 「**king LGBM 那一半是逐位核实的**: 训练用原始每结算费率的 EMA, 服务用 8h 归一 EMA, 4h 名差 2 倍、1h 名差 8 倍。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:9` — 「**判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)。**」
  - `/Users/haosiyu/dl_quant_live/config/book.json:153` — 「"book_source": "external",」
- **A reader could wrongly conclude:** A reader assumes a per-artifact funding caliber gate protects the live models and skips funding-feature train/serve parity in retrains; the wide pipeline never had that gate.
- **Affects:** future_retrain, future_eval · **Severity reason:** Reads as "live funding features are served on the as-trained caliber, verified in production". That was true only for the retired executor DL heads; the live external book serves v1 (normalised) fund_ema to v0-trained king/V2MAIN column 80.
- **Proposed correction (exact text):** [append after L13] **Scope note (2026-09-13 audit):** everything above concerns the executor's internal DL book (king/s2 heads, wide_dl_full.npz, funding_span table), which has not been the live book since 2026-08-22 (book_source=external); T1 confirms the span table is read only by that frozen panel. The live wide producer has the OPPOSITE split and no per-artifact gate: fund_ema (col 80) is TRAINED v0 (per-settlement rate) but SERVED v1 (rate×8/iv) to both the king LGBM and V2MAIN, 2× on 4h names and 8× on 1h names (T1 §5, T4; T4 book effect NOT MATERIAL at ±0.05 bps/anchor; V2MAIN historical effect not measured). Do not cite "live splice PASS" for the current book.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-28 · P2 · DOC_STALE
- **Source:** `memory/venue_feasibility_hyperliquid.md:31`
- **Quote:** 「funding 腿别指望在 HL 复用 —— 但也别为此焦虑, [[ma_v2_factor_state_2026_07_08]] 之后的实测显示该腿 canonical 口径下全历史独立为负 (avg −1.34, 5 年 4 年负)」
- **Superseding evidence:**
  - `docs/PREREG_leg_ablation_2026-08-26.md:43` — 「**去掉它整本书从 +1.31 变 −1.73, 夏普从 2.18 变 −2.49。funding 腿就是这本书**」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
  - `STATE.md:8` — 「**待用户裁定 4 项**: T6 录取规程 / L4 现货腿 / L5 快频书实盘小实验 / L6 第二场所。」
- **A reader could wrongly conclude:** A second-venue evaluation assumes the non-transferable funding leg is expendable, when in fact it is most of the book.
- **Affects:** future_eval · **Severity reason:** Tells venue planning not to worry about losing the funding leg because it is negative. The funding leg became the book (removing it turns the book negative), and a second venue (L6) is awaiting a user decision.
- **Proposed correction (exact text):** [L31 后插入] **【2026-09-13 更正】**「funding 腿全历史独立为负, 别为 HL 不能复用而焦虑」作废: 同日 07-25 结算间隔量纲修复后该腿转正; 宽书时代 funding 腿就是这本书(PREREG_leg_ablation §4: 去 fund 净额 +1.31→−1.73, 夏普 2.18→−2.49; 09-11 在役名义 fund ≈65%)。HL funding 截面 rank corr 仅 0.47 ⇒ 任何第二场所方案(L6, 待用户裁定)须先证明 fund 腿可迁移, 否则等于换一本书。本条其余数字均属 07-25 110 名旧引擎。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-32 · P2 · DOC_STALE
- **Source:** `memory/feedback_reference_window_must_match_regime.md:15`
- **Quote:** 「(本项目里 `RESULT_live_form_health_check` §2 截至 08-10, `RESULT_giveback_baserate` §1 有 08-30 的同源行)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:1` — 「# 口径锁 · 本研究分支一律按 v4 链(2026-09-09)· 任何 v3 谱系数字作废」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:29` — 「`pod_fea_ext.py` | **E-0909-A**: 构建器 `E−w` 窗未 clamp, 回绕, 首 138 锚错」
  - `docs/RESULT_live_form_health_check_2026-09-05.md:62` — 「| 当前 v3 bundle(09-01 模型)的样本外行 |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:14` — 「| 2026(至 08-30) | 1453 | **+3.100** | **+4.53** | +4.54 | +4.53 | 8.6% | 17% |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp)」
- **A reader could wrongly conclude:** A reader judges live days against v3 Sharpe/maxDD/σ readings (e.g. 3.96 / 16.9%) instead of v4 figures.
- **Affects:** reporting · **Severity reason:** The rule names v3-lineage instruments, since voided by the v4 caliber pin, as the "same-source longer-window" references; the correct same-source table is now the v4 per-year receipt.
- **Proposed correction (exact text):** [L15 后插入] **【2026-09-13 更正】** (2) 中的同源参照(RESULT_live_form_health_check §2 / RESULT_giveback_baserate §1)属 v3 谱系, 按 CALIBER_PIN_v4「任何 v3 谱系数字作废」不再引用; 改读 v4 逐年表(r18 receipts/TABLE_per_year_v4_caliber_2026-09-12.md, 数据至 2026-08-31 00Z: 2026 Sharpe +4.53 [2.21,6.79], 2026 年内复利 NAV maxDD −15.98%@2×)与 r18 全史尾部。本条 4.96/3.96、8.4%/16.9% 为 v3 读数, 仅作案例保留。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-33 · P2 · DOC_STALE
- **Source:** `memory/feedback_units_chain_and_caliber_binding.md:10`
- **Quote:** 「(1) 汇报里的每个 %/NAV 数字只能从脚本(如 pod_units_table.py)复制, 并写出链: bps/锚 → ÷gross_total → ×2190/100 → ×杠杆;」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:57` — 「- **口径**: 记账 y4s = Π(1+r)−1(禁从 5m 缓存重算收益, ret5 通道裁剪 ±0.30)」
- **A reader could wrongly conclude:** A reader reports NAV drawdowns as arithmetic ×leverage, or recomputes returns from the clipped 5m cache while following this chain.
- **Affects:** reporting · **Severity reason:** The required units chain ends with a linear ×leverage step. Later receipts forbid that for drawdowns (use compounded fixed-2× NAV; ×2 overstated the 2023 maxDD by 4.61pp), and the named script is a pre-v4 device.
- **Proposed correction (exact text):** [(1) 末尾追加] 【2026-09-13】链中「×杠杆」只适用于均值/年化收益; 回撤、最差日、触线概率一律用逐锚复利 Π(1+L·g·1e−4) 的 NAV 路径计算(U2 PROGRAM P3; v4 逐年表勘误 3: 2023 算术 ×2 −33.54% vs 复利 −28.92%)。g 按 v4 钉 = net_ex/gross_total; 收益只从记账 meta y4(Π(1+r)−1, RAW)读, 禁从 5m 缓存 ret5 重算(裁剪 ±0.30)。pod_units_table.py 为 v3 期装置, 复用前核其输入谱系。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-37 · P2 · DOC_STALE
- **Source:** `memory/feedback_check_exhausted_first.md:11`
- **Quote:** 「1. `grep "明确不做\|exhausted\|null 路径" CLAUDE.md` — 看 "Current Priority" 章节」
- **Superseding evidence:**
  - `CLAUDE.md:44` — 「| 恢复研究某条轴 / DNR | `docs/MILESTONE_2026-08-26.md` §2/§5(08-11 前的查上期) |」
  - `CLAUDE.md:4` — 「引用"已关闭/DO-NOT-RETRY"必须带受据文档。」
- **A reader could wrongly conclude:** A reader re-runs a closed axis believing it was checked, or misses that a DNR was later overturned.
- **Affects:** future_eval · **Severity reason:** The required pre-experiment check greps CLAUDE.md for strings and a section that no longer exist (0 hits in the current 51-line file), so it silently returns "not in the exhausted list".
- **Proposed correction (exact text):** [替换规则第 1 步] 1. ~~grep CLAUDE.md "Current Priority"~~ 【2026-09-13 更正】CLAUDE.md 已无该章节与关键词(grep 0 命中); DNR/已关闭轴查 `docs/MILESTONE_2026-08-26.md` §2/§5(08-11 前查 `docs/MILESTONE_2026-08-11.md`)+ MEMORY.md「DNR / 已关闭轴」节 + `docs/ERROR_LEDGER_2026-08-20.md`; 引用关闭必须带受据文档, 并先核该关闭是否已被后续受据翻转(例: requote DNR 已被 09-05 实盘复核推翻)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-44 · P2 · DOC_STALE
- **Source:** `memory/feedback_no_book_level_response_to_instrument_doubt.md:12`
- **Resolution:** XREF AUDIT_EXEC EXE-01 — CROSS-REF: 'any watchdog trip still flattens the whole book' is owned by AUDIT_EXEC EXE-01; FX-W6C holds the fix (clone b3c5fc2, not deployed).
- **Quote:** 「② 全书级响应(平仓/停机)必须过**比例门**(涉及名义占 gross 份额 + 名数; R-14 冻结 2%/5 名)并在 DESIGN 写出「假阳性最大代价」;」
- **Superseding evidence:**
  - `STATE.md:7` — 「W6(c) 仍默认关未落地; 平仓费回填(09-12)仍待办。」
  - `STATE.md:56` — 「(c) 比例响应(默认 ON, 2%/5 名, 单独提交; 我方按「彻底修复」读作 R-14=A, 复审前可翻)」
- **A reader could wrongly conclude:** A reader assumes the live watchdog already limits whole-book flattens by proportion and under-weights false-positive flatten risk when reviewing reconciliation or watchdog changes.
- **Affects:** live_trading · **Severity reason:** The rule reads as if a 2%/5-name proportionality gate guards whole-book responses, but the implementation (W6(c)) is default-off and was not part of the ef60f85 landing.
- **Proposed correction (exact text):** [② 末尾追加] 【2026-09-13 实施状态: 该比例门的执行器实现 W6(c) 默认关、未随 ef60f85 落地(STATE 09-13 12:0xZ); 在役看门狗仍可因对账疑问整书平仓 —— 本条目前是设计/复审规则, 不是运行中的保护】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-04 · P2 · DOC_STALE
- **Source:** `memory/ma_v2_wide_universe_revival.md:19`
- **Quote:** 「**★ SURPRISE INVERSION: funding_ema does NOT revive on wide** (z+1.7, sign FLIPS per-fold) — the opposite of its 14-mega-cap strength (z−2.50, [[ma_v2_funding_lever_real_positioning_null]]). So the two universes carry DIFFERENT alpha: **mega-caps = funding-crowding-reversion; wide universe = the price-volume factor zoo.**」
- **Superseding evidence:**
  - `docs/MILESTONE_2026-08-26.md:29` — 「- **fund 腿 = 书本体**(去掉 4/4 年由盈转亏 −3.04 CI[−3.86,−2.20])」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:111` — 「140/400 宇宙 1h IC 反为 +0.003(延续), 4h ≈0; 全史非全天候(2024 −1.52) ⇒ 证书 = 有利窗口」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:113` — 「归一 v1 +0.0068(2024 −0.0068); 部署腿弱于证书; WA: 去 fund 腿夏普 1.67→0.66」
  - `docs/RESULT_xregime_2026-09-02.md:43` — 「2021 极端名十分位多空 −4.5bp/4h(反转), 2022 −3.3, 2023 ≈+1, 2024 +5.6, 2025 +8.2, 2026 +30.5 ⇒ 机制(状态量)持久, "→延续"映射不持久。」
- **A reader could wrongly conclude:** A reader concludes funding is a mega-cap-only reversal effect and deprioritises or mis-signs funding work on the 450/829-name universe.
- **Affects:** future_eval, reporting · **Severity reason:** A universe-level claim that funding has no wide-universe alpha is the opposite of later receipts where the funding EMA (continuation sign) is the wide book's body.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「funding_ema 在宽宇宙不复活 / 宽宇宙 = 价量 zoo」只对 07-08 的 110 币、549 天窗口成立。之后的宽宇宙(400/450 名, 2021–2026)上 funding EMA 以**延续号**成为书本体: 去 fund 腿 4/4 年由盈转亏(MILESTONE_2026-08-26 L23); 符号随年代翻转(2021/22 反转 → 2024–26 延续, RESULT_xregime L43); 证书强度含量纲伪影(未归一 +0.0237 → 归一 +0.0068, 2024 为负, RESULT_conclusion_reaudit_simple_caliber L113)。引用本段须带「110 币 / 2025 窗」范围, 不得用作「宽宇宙 funding 无 alpha」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-05 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/ma_v2_wide_universe_revival.md:28`
- **Quote:** 「**宇宙刷新A/B(2026-09-01 §B, double-check修正版)**: 全窗U1/U2负系**U0回套生存者偏差**(2026手选名单套历史; 分年Δ: 后见年−0.38/−0.37, 无后见2026=+0.03±0.17中性)。可靠结论=**前瞻加宽≈alpha中性+轻微尾部改善**, 未达录取线(CI>0)⇒维持450; 重开=09-10入金后2026-同步口径重测(中性起点, 门槛不远)。」
- **Superseding evidence:**
  - `docs/PREREG_retrain_addendum_v2main_2026-09-01.md:29` — 「装置: umask 三件 + w10_universe(UMASK 注入)+ §B 判官(ts 交集成对修正)」
  - `docs/REVIEW_caliber_final_2026-09-04.md:105` — 「`w10_universe.py` 及 w10_* 姊妹 | 同上 | Σ-simple | expm1 默认 | 否 |」
  - `docs/ERROR_LEDGER_2026-08-20.md:416` — 「宇宙 M1 的 +0.06~+0.09(已上线, 复验中)」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:47` — 「| M1+T400(秩基变宽+成交集 400) | −0.057/−0.16 | −0.086/−0.07 | +0.181/+0.34 | **−0.009/+0.09** | 整体中性, 只在 2026 正 |」
  - `STATE.md:159` — 「449 宇宙 U-PIT/U-FROZEN, M1 秩基 829」
- **A reader could wrongly conclude:** A reader treats 'forward widening is alpha-neutral, keep 450' as a measured unbiased result and as the complete live universe state, missing that M1 widened the fund rank base on 09-04 and that its own unbiased effect is neutral.
- **Affects:** future_eval, reporting · **Severity reason:** The universe-widening verdict was judged on the w10 CAL=simple device and has not been re-judged on CAL=log/v4, while the live fund rank base has since been widened (M1).
- **Proposed correction (exact text):** > ⚠ **2026-09-13 待复验(E-0904-F):** 本 A/B 用 `w10_universe`(UMASK 注入)于 09-01 跑出, 该装置当日默认 `CAL=simple`(expm1 伪凸性, REVIEW_caliber_final L105), 未在 CAL=log / v4 口径重判 ⇒「前瞻加宽 ≈ alpha 中性」是未测读数。另: 09-04 起实盘 fund 腿秩基已变宽到全场所新鲜结算名(M1; 在役形态「449 宇宙 + M1 秩基 829」, STATE.md 在役形态全史体检条), 「维持 450」只对交易成员集成立; M1+T400 在无偏口径下整体中性(−0.009, 只在 2026 正; RESULT_caliber_revalidation L47)。重开宇宙加宽须用时代同步名单 + v4 口径。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-06 · P2 · DOC_STALE
- **Source:** `memory/mapping_4arm_live_config_optimal.md:3`
- **Quote:** 「★★★ DO-NOT-RETRY: 仓位映射 2×2(α∈{.5,1}×λ∈{0,1})用实盘 compose_book 在 9821 锚上判 —— 在役 α=.5 λ=1 净额双档最优, 三候选全 FAIL」
- **Superseding evidence:**
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:70` — 「**翻转(栈依赖 + 口径)**: 在役栈下 α 压缩是代价(−0.09~−0.17 bps/锚); DO-NOT-RETRY 撤销 ⇒ 需预注册 α∈{.5,1}×λ∈{1,1.5,2} 简单口径重裁(优先级 1)」
  - `docs/DESIGN_optimization_path_2026-08-21.md:86` — 「"α/λ DNR"系无 EMA 栈判决, 撤销待重裁」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不经 compose_book/风险预算/EMA/中性带」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:449` — 「### CFG-07 — Internal-book keys are inert in external mode」
- **A reader could wrongly conclude:** A future proposal to change score-to-position mapping (α/λ, vol scaling) on the live combo book is rejected by citing this DNR, or a reader assumes the live book still uses sqrt-score × 1/σ via compose_book.
- **Affects:** future_eval, reporting · **Severity reason:** A ★★★ DO-NOT-RETRY on position mapping was withdrawn on 2026-08-22 (stack-dependent, α compression costs 0.09-0.17 bps/anchor on the EMA stack) and the in-role compose_book it describes is no longer the live mapping, but neither fact is in the note.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条 DO-NOT-RETRY 已于 2026-08-22 撤销: 在有深 EMA + 带 + 止损的在役栈上, M2(α1 λ1)反超 M3(SIM Δ+0.087 [−0.008,+0.179] 4/5; LOG Δ+0.169 三关全过), λ1.5 在简单口径过 G 族 ⇒「在役栈下 α 压缩是代价」, 需预注册重裁(RESULT_conclusion_reaudit_simple_caliber L70; DESIGN_optimization_path L86)。另: `compose_book` 所在的 in-role 内部书 2026-08-22 03:15Z 已退役, 现役 combo 外部书「不经 compose_book/风险预算/EMA/中性带」(`~/dl_quant_live/config/book.json` _book_source_note; AUDIT_EXEC CFG-07), 本条「现在实盘用的这个规则」不再是实盘映射。引用本条只可作「50 锚窗口排序与全史反转」的方法论教训。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-07 · P2 · DOC_STALE
- **Source:** `memory/king_cadence_8h_live.md:3`
- **Quote:** 「★★★ 2026-08-09 上线: king 腿 4h→8h 相位00/08/16Z (commit 1cfbf0c)。调仓仍 4h。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:452` — 「weights/signs, harvest_ema, no_trade_band_w, risk_budget and leg_cadence apply only to the retired internal composer.」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:83` — 「**翻转(栈依赖)**: 深 EMA 已吃光节奏红利, 4h 新鲜度反超(SIM 2022-24 +0.06~+0.15, 2025-26 ≈0)⇒ 需预注册复核(优先级 3)」
  - `docs/DESIGN_optimization_path_2026-08-21.md:86` — 「⑤ 在役栈下 king 4h>8h(SIM +0.074 5/5), cad8 红利只在无 EMA 栈。」
- **A reader could wrongly conclude:** A reader analysing the live king leg assumes it holds scores at 04/12/20Z, or proposes an 8h cadence for the combo king citing Δnet +0.825, which only existed on the no-EMA stack.
- **Affects:** reporting, future_eval · **Severity reason:** Presents an 8h king cadence as live, but it only applied to the internal in-role book retired 2026-08-22 (leg_cadence is inert in external mode) and its benefit reversed on the EMA stack.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条 8h 节奏只作用于 in-role 内部书(`compute_preds`/`compose_book`), 该书 2026-08-22 03:15Z 已退役; 现役 combo 外部书下 `leg_cadence` 等内部键惰性(`~/dl_quant_live/config/book.json` book_source=external; AUDIT_EXEC CFG-07), 生产者 `shadow_loop_v3.py` / `combo_stage.py` 中无 king 节奏保持逻辑(grep cadence/hold 无命中)。另 08-22 结论复审在深 EMA + 带的在役栈上测得 king 4h 反超 8h(SIM +0.074 [+0.009, +0.139] 5/5; RESULT_conclusion_reaudit_simple_caliber L83), cad8 红利只在无 EMA 的原装置栈 ⇒ 本条 Δ净 +0.825 不迁移到任何带 EMA 的书。「相位键 = 名义 4h 网格锚」的实现教训保留。
- **Confidence:** VERIFIED (quote+receipt opened); 'no cadence logic in the producer' is from a grep of shadow_loop_v3.py and fea171/combo_stage.py only · **Quote re-verified at assembly:** exact

### M4-09 · P2 · DOC_STALE
- **Source:** `memory/wide_book_carry_correction.md:15`
- **Quote:** 「① 任何宽书夏普引用 ≥2026-08-16 版本必须是 carry 修正后的(2.42/2.18 全史), 旧 3.4x 作废留档」
- **Superseding evidence:**
  - `docs/DESIGN_optimization_path_2026-08-21.md:92` — 「**此前引用的 ≈2.2–2.8 作废, 以 1.67 为准。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12` — 「**全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举); 逐年 2022 +0.48 / **2023 −1.94** / 2024 +1.09 / 2025 +1.19 / **2026 至 08-31 +4.53 [2.21, 6.79]**。」
- **A reader could wrongly conclude:** Planning or reporting quotes a full-history wide-book Sharpe of ~2.4 (live 1.3-1.6) instead of the v4 canonical 1.29 [0.32, 2.28] with a -1.94 2023 year.
- **Affects:** reporting, future_eval · **Severity reason:** The note instructs that wide-book Sharpe citations use 2.42/2.18 (and L11 expects 1.3-1.6 live), numbers voided on 08-22 and replaced by the v4 full-cycle 1.29.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 2.42/2.18(及 L11「实盘预期 1.3-1.6」)已被两次取代: 08-22 独立口径审计 WA 读宽书 d30 夏普 1.67 [0.73, 2.61], 并宣布「此前引用的 ≈2.2–2.8 作废」(DESIGN_optimization_path L92); 现行正典为 v4 口径 A0 全周期诚实夏普 1.29 [0.32, 2.28](2023 −1.94, 2026 至 08-31 +4.53; PROGRAM_uplift_r2 L9)。宽书夏普一律引 v4 口径并声明窗口与形态; 本条只保留「carry 记账 /2 bug」的机制与「复现验证实现不验证规格」的方法论教训。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-11 · P2 · DOC_STALE
- **Source:** `memory/pilot_journal_pointer.md:3`
- **Quote:** 「Authoritative per-day journal for the live pilot lives in exports/live/pilot_journal/ — read the latest day's file before answering any 'what is the current state' question」
- **Superseding evidence:**
  - `CLAUDE.md:7` — 「1. **`STATE.md`(仓库根)** — 当前状态唯一真相源(在役链路/在飞/待裁定/口径纪律)。」
  - `CLAUDE.md:10` — 「4. 历史脉络: `multi_asset/exports/live/pilot_journal/`(只追加)」
  - `multi_asset/exports/live/pilot_journal/journal_2026-09-13_anchors.md:3` — 「# 2026-09-13 逐锚日志(书自 09-12 12:47Z 起空仓 + 开仓停, 待用户恢复)」
  - `STATE.md:7` — 「**12:05:36Z `resume_from_trip.sh` 执行**」
- **A reader could wrongly conclude:** A session answers 'what is live / is the book halted' from the journal header or JOURNAL_<date> naming instead of STATE.md and reports a stale halt/position state.
- **Affects:** reporting, live_trading · **Severity reason:** Makes an append-only history journal the authority for current live state, contrary to CLAUDE.md, and its per-day header can lag STATE.md (09-13 header still says flat and halted after the 12:05Z resume).
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 当前状态唯一真相源是仓库根 `STATE.md`(CLAUDE.md 会话起步必读第 1 条); `multi_asset/exports/live/pilot_journal/` 是只追加的历史脉络, 不回答「现在是什么状态」。文件命名已改为 `journal_<date>_anchors.md`(逐锚日志), 日首标题可能落后于当日 STATE(例: 09-13 标题仍写「空仓 + 开仓停」, 而 STATE.md 记 12:05:36Z 已恢复)。先读 STATE.md, 再按需查日志细节。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-15 · P2 · DOC_STALE
- **Source:** `memory/champion_baseline_repro.md:3`
- **Quote:** 「★正典基线复现配方(2026-08-08 定盘) — 冠军配置完整命令+面板SHA+噪声标定; 一切升级从此出发」
- **Superseding evidence:**
  - `docs/MILESTONE_2026-08-26.md:38` — 「- F10 阶梯家族(R1/R1CTX/RECB/T/PLE/V3FULL/L3.2 conformer)全部不敌朴素 V2MAIN(REVIEW_f10_blend_deployment)。」
  - `docs/REVIEW_caliber_final_2026-09-04.md:55` — 「| DL 目标 y4s(`dlw_targets.npz`) |」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:38` — 「产物 `f8_v4/models/f10_live_s42.pt`」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
- **A reader could wrongly conclude:** A reader starts a DL upgrade or retrain from champion_run.sh (resid rank-IC 0.0475 baseline, wide_dl_full_corrfund_causal_0731) instead of the V2MAIN v4 chain.
- **Affects:** future_retrain, future_eval · **Severity reason:** The 08-08 conformer champion (train_wide_harness on the in-role log panel) is no longer the base of any live leg; live DL is V2MAIN F10 on dlw y4s targets retrained via the v4 chain.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本配方是 08-08 in-role conformer 冠军(`train_wide_harness.py`, 对数面板 `wide_dl_full_corrfund_causal_0731`)的复现基线, 该腿随 in-role 书于 2026-08-22 退役。现役 DL 腿 = V2MAIN(F10 书损失, 目标 y4s = Π(1+r5)−1, `dlw_targets.npz`; F10 阶梯家族全部不敌朴素 V2MAIN, MILESTONE_2026-08-26 L26), 重训按 `docs/RUNBOOK_monthly_retrain_2026-10.md` v4 链。「一切升级从此出发」不再适用; 「argv 与面板 SHA 必须入产物」的教训保留。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-16 · P2 · DOC_STALE
- **Source:** `memory/breadth_gate_zero_recruitment.md:3`
- **Quote:** 「★★ Commoditised price-volume factors do NOT constitute breadth: 14 revival factors → 8 survive orthogonality → collapse to 2 independent clusters → 10/10 fail the incremental gates.」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:125-126` — 「   `f_amihud_24h` 正是当年那批"商品化价量因子"之一, 正交化后作站立书 Sharpe 1.83 / 5 年全正 / Bonferroni 干净,
   在书混合双种子 (A)。**⇒ "商品化价量因子零录取"的前提在 v4 书层不成立, 该轴需要重开。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:203` — 「低 PBO 由一条**事后预选**的线(XIB_LAG50, 取自 78 臂筛选)撑着」
- **A reader could wrongly conclude:** Commoditised price-volume sleeves (e.g. Amihud illiquidity orthogonalised to the fund leg) are rejected by citing this DNR.
- **Affects:** future_eval · **Severity reason:** The 08-04 zero-admission verdict (in-role engine, ΔIC gate) is presented as a general closure, but the v4 book-level Track D receipt says its premise does not hold and the axis must be reopened.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本判决只对 08-04 in-role 引擎 × ΔIC 增量腿门成立。v4 口径书层(Track D, 09-11): `f_amihud_24h` 对 fund 腿截面正交化后站立书 Sharpe 1.83、5/5 年正、过 Bonferroni ⇒「商品化价量因子零录取的前提在 v4 书层不成立, 该轴需要重开」(RESULT_trackD_sleeves_v4 §8)。注意该线索与 XIB_LAG50 属事后预选(T6: 低 PBO 由其撑着), 未经录取门, 不可据此改书。另: s2 腿已随 in-role 书退役, 「波动族 sleeve = s2 回声」的约束对现役 combo 不再成立。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-17 · P2 · DOC_STALE
- **Source:** `memory/breadth_commoditised_factors_zero_admissions.md:3`
- **Quote:** 「The 14 revived price-volume factors give ZERO admissions to the book: gate 3 kills 6, the 8 survivors collapse to only 2 independent clusters, and all 10 gate-1/2 rows fail. Commoditised price-volume factors do not constitute breadth.」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:125-126` — 「   `f_amihud_24h` 正是当年那批"商品化价量因子"之一, 正交化后作站立书 Sharpe 1.83 / 5 年全正 / Bonferroni 干净,
   在书混合双种子 (A)。**⇒ "商品化价量因子零录取"的前提在 v4 书层不成立, 该轴需要重开。**」
  - `CLAUDE.md:14` — 「构成 ≈77% funding 动量 + 13% king LGBM + 10% V2MAIN 书损失 DL」
- **A reader could wrongly conclude:** A reader rejects price-volume sleeves or volatility-family sleeves citing zero admissions and the s2 echo.
- **Affects:** future_eval · **Severity reason:** Same verdict as breadth_gate_zero_recruitment; its premise was reopened at the v4 book level and its 's2 echo' constraint refers to a leg no longer in the book.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 见 breadth_gate_zero_recruitment 同日更正: v4 书层 Track D 认定「商品化价量因子零录取的前提不成立, 该轴需要重开」(`f_amihud_24h` 正交化站立书 Sharpe 1.83; 事后预选, 未录取)。s2 腿已不在现役 combo(fund + king LGBM + V2MAIN), 「任何波动族 sleeve 是 s2 回声」不再是约束。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-22 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/target_span_single_peak_24h.md:23`
- **Quote:** 「⇒ **DO-NOT-RETRY: target-span search is closed.** Only 12h/36h remain untested and the peak is flat, so expected gain is negligible. Anything claiming a target-side gain must beat 2.285 on this rig.」
- **Superseding evidence:**
  - `multi_asset/exports/eda/PREREG_horizon24_native_persistence_2026-08-06.md:84` — 「本判决是 dl_only 简装置, Δ 合法但绝对水平未证」
  - `docs/REVIEW_caliber_final_2026-09-04.md:90` — 「对交易所记账 **否**(08-22 SR 量化 −0.79 bps/锚)」
  - `docs/REVIEW_caliber_final_2026-09-04.md:31` — 「| king LGBM 标签 | rank(Σ-simple [E,E+47]) |」
  - `docs/REVIEW_caliber_final_2026-09-04.md:55` — 「| DL 目标 y4s(`dlw_targets.npz`) |」
- **A reader could wrongly conclude:** Target-horizon experiments for the live legs are refused by citing this DNR and its 2.285 bar from a retired rig.
- **Affects:** future_retrain, future_eval · **Severity reason:** The closure was judged on a retired dl_only in-role rig with log-return P&L (not exchange accounting) and never re-measured for the live king LGBM or V2MAIN targets.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 范围更正:** 本判决装置 = 08-07 in-role dl_only 简装置(自述「Δ 合法但绝对水平未证」), 盈亏为对数 Y4(对交易所记账偏 −0.79 bps/锚), 装置与 in-role 书均已退役; 「必须在本装置上超过 2.285」无法再执行。现役 king LGBM(标签 rank Σ-simple [E,E+47])与 V2MAIN(y4s)上从未测过目标跨度 ⇒ 对现役腿为**未测**, 重开须在 v4 口径书层按预注册判。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-27 · P2 · DOC_STALE
- **Source:** `memory/wide_book_final_form_verdict.md:11`
- **Quote:** 「**签名数: 全史(2024-26)3.2-3.4, 扣当日~20变体DSR税后 2.5-3.0, 实盘预期 1.8-2.4 = 在役 1.3-1.6 倍**」
- **Superseding evidence:**
  - `docs/DESIGN_optimization_path_2026-08-21.md:92` — 「**此前引用的 ≈2.2–2.8 作废, 以 1.67 为准。**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12` — 「**全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举)」
  - `STATE.md:6` — 「A0 冻结窗自身 CI95 [1.306, 4.565] 不显著高于 3」
- **A reader could wrongly conclude:** Planning quotes the wide book's 'final form' Sharpe 3-4 as the historical level of the live strategy.
- **Affects:** reporting, future_eval · **Severity reason:** Glob-family note (wide_book_*) not in any sweep list; its signed Sharpe (3.2-3.4 history, 1.8-2.4 live, description '4.3') was voided on 08-22 and the v4 canonical is 1.29.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条签名数(全史 3.2-3.4、实盘预期 1.8-2.4、description「4.3」)已作废: 08-22 WA 独立口径审计「此前引用的 ≈2.2–2.8 作废, 以 1.67 为准」(DESIGN_optimization_path L92); 现行正典 v4 口径 A0 全周期 1.29 [0.32, 2.28], 冻结窗 2.94 自身 CI95 [1.306, 4.565] 不显著高于 3(STATE.md 09-13 12:1xZ 条)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-28 · P2 · DOC_STALE
- **Source:** `memory/ma_v2_funding_ema_GO.md:3`
- **Quote:** 「funding_ema is the FIRST net-cost-tradeable multi-asset factor (1h L/S break-even 18.8 bps/side, all 5 factory gates PASS, latency-flat)」
- **Superseding evidence:**
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:111` — 「140/400 宇宙 1h IC 反为 +0.003(延续), 4h ≈0; 全史非全天候(2024 −1.52) ⇒ 证书 = 有利窗口」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:111` — 「重标注: 在役 funding 腿 = carry/分散 sleeve(价格夏普 0.06), 不是反转 alpha」
- **A reader could wrongly conclude:** A reader cites a net-cost-tradeable funding reversal factor with 18.8 bps break-even as a current fact.
- **Affects:** future_eval, reporting · **Severity reason:** Glob-family note (ma_v2_*) not in any sweep list; its GO certificate (crowding-reversion, BE 18.8) was re-labelled a favourable-window artefact whose sign is continuation on 140/400 names.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本 GO 证书(14 大币 2025 窗, 1h 反转)已被 08-22 复审重标: 140/400 宇宙 1h IC 反为 +0.003(延续), 4h ≈ 0, 全史非全天候(2024 −1.52)⇒「证书 = 有利窗口」; in-role funding 腿 = carry/分散 sleeve(价格夏普 0.06), 不是反转 alpha(RESULT_conclusion_reaudit_simple_caliber L111)。现役宽书 fund 腿用延续号, 见 MILESTONE_2026-08-26 §2。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-29 · P2 · DOC_STALE
- **Source:** `memory/ma_v2_maker_execution_reframe.md:16`
- **Quote:** 「**★ 结论 (保守 headline = k=60)**: M0 有效成本/side ≈ **0** (2023 +0.05 / 2024 −0.07 / 2025 +0.17), **« taker 1.7 约 8-30×**。」
- **Superseding evidence:**
  - `docs/MILESTONE_2026-08-26.md:48` — 「- 换手成本全审: 3.52 bps/单位意图 [0.32,6.64]」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:11` — 「有效成本 **c_eff = +1.13 bps/单位换手, CI95 [−15.87, +24.74]**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:15` — 「没成交的意图在本锚比成交了的意图多走 **+55.6 bps, CI95 [+11.0, +120.7]**」
- **A reader could wrongly conclude:** A reader re-opens cost-killed fast signals assuming maker execution is nearly free.
- **Affects:** future_eval · **Severity reason:** Glob-family note (ma_v2_*) not in any sweep list; a simulated ~0 bps maker cost that 'reprices cost-killed verdicts' is contradicted by live fills (3.52 bps/unit intent) and by the fill-selection gap in T3.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 模拟「maker 有效成本 ≈ 0」未被实盘成交支持: 在役书实测全口径换手成本 3.52 bps/单位意图 [0.32, 6.64](MILESTONE_2026-08-26 L30); 被动执行反转书有效成本 +1.13 [−15.87, +24.74] 不可判, 且未成交意图比成交意图多走 +55.6 bps [+11.0, +120.7](成交选择, T3 RESULT L11/L15)。不得据本条重开被成本判死的快信号。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-32 · P2 · DOC_STALE
- **Source:** `memory/book_family_retired_five_forms.md:31`
- **Quote:** 「**⇒ book 族退役升级为无条件**(收益 5 形态 / 波动 / 频带 / **成交概率** 四类目标全数判负)。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:112-113` — 「  ⇒ **盘口不平衡在 4h 截面上无 alpha**。LOB 唯一有用的列是**深度水平**(`LOBDEPTH__m` +1.159/+1.92, 但与
  amihud/asz 相关 0.79-0.83 = 同一个流动性因子, 且 **LOB 原始数据止于 2026-08-23 ⇒ ext 窗读数 −9.02 作废**)。」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:124` — 「那两次判的是 ΔIC ≥ +0.003 的**增量腿门**; 本轮判的是**站立书全周期净额**与**在书腿分混合**, 口径是 v4。」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:126` — 「**⇒ "商品化价量因子零录取"的前提在 v4 书层不成立, 该轴需要重开。**」
- **A reader could wrongly conclude:** A reader refuses any order-book-derived column (including depth level) for the wide book by citing an unconditional DNR, and also believes the only admissible restart is tick data.
- **Affects:** future_eval · **Severity reason:** The unconditional retirement was judged by incremental ΔIC/AUC gates on the in-role hourly rig, while the v4 book layer measures a LOB-derived column (LOBDEPTH) as a standing book with Sharpe +1.92.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(RESULT_trackD_sleeves_v4_2026-09-11 §7/§8):** 「无条件」只对本条自己的判据成立 —— in-role 引擎、小时分辨率、ΔIC/成交概率**增量门**。v4 口径**书层**(09-11, 78 臂)另有读数: 盘口不平衡族(LOBIMB1/LOBIMB5/LOBIMB1D)在 4h 截面确实无 alpha, 但 LOB 的**深度水平**列 `LOBDEPTH__m` 作站立书 **+1.159 bps/锚 / Sharpe +1.92**(与 amihud/asz 相关 0.79–0.83 = 同一个流动性因子, 故不构成独立录取; 且 LOB 原始数据止于 2026-08-23, ext 窗读数作废)。同文 §8 明写「判据不同 … 本轮判的是站立书全周期净额与在书腿分混合, 口径是 v4」⇒ 08-09 的四类目标全负**不构成对 v4 书层的关闭**。仍成立: 买卖对抗/盘口不平衡在小时与 4h 聚合上无 alpha; 亚分钟未测。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-33 · P2 · DOC_STALE
- **Source:** `memory/raw_target_rejected_2026_08_04.md:22 (+1 more)`
- **Quote:** 「- **Residual-label training is necessary** — the doc's §7.1-C hypothesis ("train on raw, neutralize
  after, avoid the noisy residual label") is dead in both readings (A and R both lose).」
- **Superseding evidence:**
  - `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:15` — 「**king 腿 55/45 混入 V2MAIN**: V2MAIN 是用"可微书损失"训练的深度网络(171 列特征, `V2=1` 模式 = 训练时直接优化"把它当 king 放进书里"之后整本书的净额与尾部, 而非拟合 IC)」
  - `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:95` — 「树拟合的是"预测得准"(IC), V2MAIN 优化的是"放进书里净额高、尾部浅、换手低"。同弹药下目标效应 +0.488」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:221` — 「**DL 目标/特征** = `pod_dlw_targets_raw.py`(记账 y4s 原始收益 RET_CH=0 + DLWT_RAW_PATCH」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:14` — 「| CLIP 对照臂 | `/workspace/dlw_hf3/` | ✓ 仅作对照, **记账口径是 RAW** |」
  - `docs/REVIEW_caliber_final_2026-09-04.md:30` — 「| DL(F10/V2MAIN)目标 y4s | Π(1+r5)−1, 窗 (N,N+4h] | **正确, 即交易所记账口径**」
  - `docs/REVIEW_caliber_final_2026-09-04.md:482` — 「16 臂三口径; 排序保住, 显著性不保, 归因反转(去 rev24 CI>0, V2MAIN≈0), 2025 反转。」
- **A reader could wrongly conclude:** A future target-side retrain proposal that trains on a raw/accounting return (which is what the live V2MAIN leg already does) is rejected by citing 'raw target rejected at -6.9 SE'.
- **Affects:** future_retrain, future_eval · **Severity reason:** The DNR was measured only inside the IC-fitting family (resid rank-IC vs YR4 on the in-role S1F recipe), while the live DL leg trains on the RAW accounting target y4s under a differentiable book loss and is the only positive arm at the book layer.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 scope correction (CANDIDATE_wide_v2main_norev24 §12/§T8 + RUNBOOK_monthly_retrain_2026-10 §221 + CALIBER_PIN_v4 §1):** this verdict holds only inside the IC-fitting family — the in-role S1F recipe scored as resid rank-IC against YR4, with post-hoc cross-sectional residualisation of the predictions. It does NOT cover the objective family that is live today: the deployed DL leg (V2MAIN, 45% of the king leg since 2026-08-26) is trained with a differentiable BOOK loss on the RAW accounting target (`pod_dlw_targets_raw.py`, y4s = Π(1+r)−1; the caliber is RAW, not a residual label), i.e. the neutralisation happens in the book construction, not in the label or after the prediction. Read the 08-26 magnitudes (+0.187 / +0.488) as CAL=simple-era: the 09-04 unbiased re-check of 16 arms in three calibers keeps the ordering but loses significance and puts the V2MAIN increment at ≈0, so they are not evidence that the book-loss objective is better — the load-bearing fact here is the DEFINITION (the live DL leg's training target is the raw exchange-accounting return, judged at the book layer), not the size of any 08-26 delta. Still standing: (a) post-hoc residualisation of PREDICTIONS damaged the raw-trained model (−21%); (b) the caliber trap (a metric NAME binds to the code path, not the quantity).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M4-34 · P2 · DOC_STALE
- **Source:** `memory/breadth_round2_basis_orthogonalised.md:45`
- **Quote:** 「本条的"三关全过"只对 08-09 的对数/引擎口径成立」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r8_basis_inbook_2026-09-12.md:9` — 「**13 条预注册臂全部 REJECTED**(0/13 过 G1)。」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r8_basis_inbook_2026-09-12.md:60` — 「换手 **0.089021** = A0 的 **2.930×**, rho to A0 **0.002551**, **成本吃掉 64.79%**(存活 **35.21%**)。」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r8_basis_inbook_2026-09-12.md:53` — 「**符号是 POST-HOC 的, 而且 round 5 自己这么写。**」
- **A reader could wrongly conclude:** A reader reopens basis⟂funding as a v4 candidate on the strength of '三关全过 + 机制' and the internal optimum w≈0.15, unaware that the v4 in-book form already rejected all 13 arms and that the sign of the round-5 construction was declared after seeing the data.
- **Affects:** future_eval · **Severity reason:** The note's latest inline correction stops at the 2026-08-22 F-2 leg verdict, but basis was re-judged twice in the v4 caliber (r5 standalone sleeve, r8 in-book) with 0/13 pre-registered arms admitted and the sign shown to be post-hoc.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 v4 复判(RESULT_r8_basis_inbook_2026-09-12, 承 r5):** basis 族已在 v4 口径被重判两次。① 独立 sleeve 形态: SR 1.22, 换手 = A0 的 2.93×, **成本吃掉 64.79%(存活 35.21%)**; ② 书内形态(改 fund 腿分数, 不加腿): 换手反而省 5.13%、成本存活 201%, 但**13 条预注册臂全部 REJECTED(0/13 过 G1)**, 书内边际毛 alpha 仅为独立毛 alpha 的 0.73%, 全部 CI 含零。③ 该族方向(FBSLOPE 的符号)在 round 5 是 **POST-HOC** 声明的, r8 已逐字记录 ⇒ 「机制预言命中」这一条不可再当作事前先验。本条的 08-09 读数与 08-22 F-2 更正一并归档为历史, 重开须带新机制与新预注册。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-35 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/orthogonal_mining_round1.md:20`
- **Quote:** 「**挖矿第一夜终账: 3 候选 0 录取**; 书残差方法论保留, 首矿死于 S1。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r2_sleeve/AUDIT_reopen_closed_axes_2026-09-11.md:18` — 「**未重开**(需要 GPU 训练 + 新的 king 残差, 超出本轮预算)。**活口**: 该方法论在 v4 口径下没被复验过, 是下一轮的候选」
  - `multi_asset/exports/research/uplift_2026-09-11/r2_sleeve/AUDIT_reopen_closed_axes_2026-09-11.md:25` — 「**本轮把"被关闭的轴"分成三类**: ①**层搞错了所以不算关闭**(ammunition / orthogonal_mining 是模型分数层,」
  - `multi_asset/exports/research/uplift_2026-09-11/r2_sleeve/AUDIT_reopen_closed_axes_2026-09-11.md:18` — 「跨所 funding = **DO-NOT-RETRY**(全史判负, 逐年翻号), 与口径无关」
- **A reader could wrongly conclude:** A reader treats '3 candidates, 0 admissions' as closing book-residual mining, although the v4 audit lists exactly this methodology as an un-replicated open lead (and only the cross-venue funding branch is a real DNR).
- **Affects:** future_eval · **Severity reason:** The 08-15 closure is a model-score-layer S1 verdict (ΔIC vs king on the in-role engine) and the 09-11 audit explicitly registers the book-residual mining methodology as never re-validated in the v4 caliber, i.e. an open lead rather than a closed axis.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 分层更正(AUDIT_reopen_closed_axes_2026-09-11 表 · orthogonal_mining_round1 行):** ① 「3 候选 0 录取」中的书残差挖矿判在**模型分数层**(S1 = vs king、resid 口径、ΔIC≥+0.003, in-role 引擎 110/450 币), 09-11 审计把本条与 ammunition 一并归为「层搞错了所以不算关闭」, 并写明「该方法论在 v4 口径下没被复验过, 是下一轮的候选」⇒ 书残差挖矿对 v4 书层是**未测**, 不是 DNR; ② 仍然成立的 DNR 只有**跨所 funding 差**(「全史判负, 逐年翻号, 与口径无关」), 该条的例外(跨所 basis / 第二场所)仍是活口; ③ 审计同时记: 09-11 在书层独立重测 8 个 bar 微结构量仍**零录取**, 与本条同向。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-37 · P2 · DOC_STALE
- **Source:** `memory/dl_ceiling_solo_rho_catch22.md:24`
- **Quote:** 「**残差(钱)口径平手**(树 0.0364·58% vs DL 0.0372·60%, "树保留率<60%"押注证伪)。⇒ 5m 残差 alpha ~0.036 是**模型无关量**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:110` — 「无差类判词(NOT MATERIAL / 不可区分 / SAME LEVEL / EQUIVALENT)**只由等价带发出**」
  - `multi_asset/exports/research/uplift_2026-09-11/r2_sleeve/AUDIT_reopen_closed_axes_2026-09-11.md:19` — 「**"排序≠净额"的第六例**」
- **A reader could wrongly conclude:** A reader closes the tree-vs-DL question ('5m residual alpha is model-independent') and skips a book-layer comparison, although neither arm was measured at the book layer and the score-layer tie was never band-tested.
- **Affects:** future_eval · **Severity reason:** '平手 / 模型无关量' is a no-difference verdict issued from two point estimates with no CI and no pre-frozen equivalence band, which K2 §0-8 now forbids, and the quantity is a score-layer residual IC that the note calls the 'money caliber'.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 重标(FIXPROGRAM §0 第 8 条 K2 + AUDIT_reopen_closed_axes 「排序≠净额」第六例):** 「残差(钱)口径平手」「5m 残差 alpha 是模型无关量」是**无差类判词**, 由两个点估计(0.0364 / 0.0372)发出, 既无 CI 也无预冻结等价带 ⇒ 按现行规程只能写 **INCONCLUSIVE / 未检出差异**, 不能写「平手 / 模型无关」。另: 这里的「钱口径」= 残差 rank-IC, 仍是**分数层**; 书层净额从未测过这一对, 而「排序有增量但书层净额为负」已累计到第六例。引用本段须同时声明层与判据。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-38 · P2 · DOC_STALE
- **Source:** `memory/direction1_tabular_gap.md:10`
- **Quote:** 「**三方等价定理(钱口径)**: 面板 248 特征 + resid 目标下, resid-LGBM 0.0483 / 序列 king 0.0486 / 满配深表格(PLR+集成+时序调制+可微森林) 0.0467 — **三种模型类等价(±0.002), 约束是信息**。」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:110` — 「无差类判词(NOT MATERIAL / 不可区分 / SAME LEVEL / EQUIVALENT)**只由等价带发出**」
  - `multi_asset/exports/research/uplift_2026-09-11/r2_sleeve/AUDIT_reopen_closed_axes_2026-09-11.md:19` — 「**"排序≠净额"的第六例**」
  - `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:95` — 「树拟合的是"预测得准"(IC), V2MAIN 优化的是"放进书里净额高、尾部浅、换手低"」
  - `docs/REVIEW_caliber_final_2026-09-04.md:482` — 「16 臂三口径; 排序保住, 显著性不保, 归因反转(去 rev24 CI>0, V2MAIN≈0), 2025 反转。」
- **A reader could wrongly conclude:** A reader concludes model class never matters ('the constraint is information'), and therefore that the live V2MAIN deep net could be swapped for a tree, or that no book-layer comparison is needed.
- **Affects:** future_eval · **Severity reason:** The equivalence theorem is a no-difference verdict read off a ±0.002 seed-noise resolution rather than a pre-frozen equivalence band, and it is a score-layer resid-IC statement labelled '钱口径' although the three model classes were never compared at the book layer.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 重标(FIXPROGRAM §0 第 8 条 K2 + CANDIDATE_wide_v2main_norev24 §T8):** ① 「三种模型类等价(±0.002)」是**无差类判词**, ±0.002 是种子噪声分辨率, 不是预冻结的经济等价带 ⇒ 正确标签是 **未检出差异 / INCONCLUSIVE**。② 「钱口径」在本条指 resid rank-IC, 仍属**分数层**; 这三类模型**从未在书层比较过**, 而「分数层排序有增量、书层净额为负」已累计到第六例 ⇒ 分数层打平不能证明书层等价。③ 同弹药换目标(IC 拟合 → 可微书损失)在书层确实是一个独立维度(CANDIDATE §4: 三条去重路全负、换目标臂为正), 但其幅度(+0.187/+0.488)出自 CAL=simple 口径, 09-04 无偏复测 16 臂三口径「排序保住, 显著性不保, V2MAIN≈0」⇒ 两个方向都不可当作定量受据。本定理只能读作「在 resid-IC 这把尺子上三类模型未检出差异」, 不能读作「模型类无关、约束只是信息」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-39 · P2 · DOC_STALE
- **Source:** `memory/direction1_tabular_gap.md:16`
- **Quote:** 「① K4 一体化关闭: 表格塔无法贡献超树部件; 深塔在工程特征上永远排 GBDT 之后。」
- **Superseding evidence:**
  - `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:93` — 「| **V2MAIN(同 171 弹药, 换目标)** | **+0.187 ★** | +0.305 | 唯一为正 |」
  - `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md:95` — 「**结论: 想升级 king, 走书损失目标, 不走特征去重**」
  - `docs/MILESTONE_2026-08-26.md:7` — 「king 腿 55/45 混入 V2MAIN(可微书损失 DL)」
  - `docs/REVIEW_caliber_final_2026-09-04.md:482` — 「16 臂三口径; 排序保住, 显著性不保, 归因反转(去 rev24 CI>0, V2MAIN≈0), 2025 反转。」
- **A reader could wrongly conclude:** A reader cites this to drop or de-prioritise the live V2MAIN deep leg, or to refuse any deep-model work on engineered features, instead of reading it as 'same objective, same ruler'.
- **Affects:** future_retrain, future_eval · **Severity reason:** 'A deep tower always ranks behind GBDT on engineered features' was measured at the score layer under an IC objective, yet a deep net on the same 171 engineered columns with a book-loss objective has been a live leg since 2026-08-26 and was the only positive arm in the book-layer dedup table (whose magnitude the unbiased re-check later put at ≈0).
- **Proposed correction (exact text):** > ⚠ **2026-09-16 范围更正(CANDIDATE_wide_v2main_norev24 §2/§T8 + MILESTONE_2026-08-26 §1):** 「深塔永远排 GBDT 之后」只在**同一个 IC 拟合目标 × 分数层尺子**下成立。换目标后结论反转: 同 171 列弹药、只把目标换成可微书损失的深网(V2MAIN)在书层 **+0.187 = 该对照里唯一为正**, 且自 2026-08-26 起以 45% 权重进入在役 king 腿; 同弹药下目标效应 +0.488, 文档结论逐字是「想升级 king, 走书损失目标, 不走特征去重」。**口径警示**: 该表为 CAL=simple 口径; 09-04 无偏复测(16 臂三口径)「排序保住, 显著性不保, V2MAIN≈0」⇒ 不可引 +0.187/+0.488 作 DL 优于树的定量证据。但「永远排 GBDT 之后」同样不被支持 —— 它测的是分数层 × IC 目标这一格, 而书层从未给出该排序。⇒ K4 关闭的是「表格塔 + IC 目标」这一格, 不是「深模型 vs GBDT」这条轴。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-43 · P2 · DOC_STALE
- **Source:** `memory/benchmark_0466_was_dirty_panel.md:29`
- **Quote:** 「- **干净基线 = 0.0475 resid / 0.067 raw**(冠军配置, 0731 等价面板, 年折, 双种子)。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/MILESTONE_2026-08-26.md:7` — 「king 腿 55/45 混入 V2MAIN(可微书损失 DL)」
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:13` — 「| DL 目标+特征 | `/workspace/dlw_v4raw/data/{dlw_targets.npz, dlw_fea82.npz}` | 184M / 447M ✓ RAW 臂」
  - `docs/MILESTONE_2026-08-26.md:38` — 「- F10 阶梯家族(R1/R1CTX/RECB/T/PLE/V3FULL/L3.2 conformer)全部不敌朴素 V2MAIN(REVIEW_f10_blend_deployment)。」
- **A reader could wrongly conclude:** A reader takes 0.0475 as the standing DL bar (or re-runs wide_harness with these flags) when planning a retrain or judging a new model, instead of the v4 chain's book-layer baselines.
- **Affects:** future_retrain, future_eval · **Severity reason:** The 0.0475 resid / 0.067 raw champion baseline and the '--xattn --lam_orth 0 --wide_dl_path' recipe belong to train_wide_harness on the log panel, a leg retired with the in-role book; the live DL leg is V2MAIN trained through the v4 chain on RAW y4s.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 范围更正(dl_quant_live/config/book.json + MILESTONE_2026-08-26 §1/§2 + CALIBER_PIN_v4 §1):** 「干净基线 0.0475 resid / 0.067 raw」与 `--xattn --lam_orth 0 --wide_dl_path` 是 `train_wide_harness` 冠军(对数面板)的复现口令, 该腿随 in-role 书 **2026-08-22 退役**; F10 阶梯家族其后亦全数不敌朴素 V2MAIN。现役 DL 腿 = V2MAIN, 走 v4 链(目标+特征 `dlw_v4raw/{dlw_targets,dlw_fea82}.npz`, **RAW 臂**), 基线与录取判据在**书层**(judge_v4 `g = net_ex/gross_total`), 不再是 resid rank-IC 0.0475。本条仍成立的部分见下一段(面板默认值陷阱)与「复现历史数字必须对齐完整 argv」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-47 · P2 · DOC_STALE
- **Source:** `memory/dl_quant_live_repo_path.md:21 (+1 more)`
- **Quote:** 「`~/dl_quant_live` before concluding data loss. Do not create anything the scheduler must read
under `~/Desktop`.」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/HANDOFF_PROGRESS_fixprogram_2026-09-13.md:106` — 「修后公证器在 launchd 下对桌面 iCloud 研究仓 git 被 TCC 拒绝且研究仓不在配置分支 ⇒ 部署后每日 HIGH 页报」
  - `STATE.md:1` — 「公证器自身 `git add` 被 launchd TCC 拒 16 天」
- **A reader could wrongly conclude:** A reader schedules a launchd job that writes or commits into the Desktop research repo (notary, cron receipts, journal appends) believing only reads are affected, and the failure stays silent.
- **Affects:** reporting · **Severity reason:** The same TCC mechanism bit again in the opposite direction — a launchd-run notary WRITING (git add) into the research repo on the iCloud Desktop was denied for 16 days and lost its third-party timestamps — and the note only warns about things the scheduler must READ.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 extension (HANDOFF_PROGRESS_fixprogram_2026-09-13 item 6 · E10 + STATE.md 2026-09-16 banner):** the rule covers WRITES too, and it has already bitten again. The ledger notary, run under launchd, had its `git add` into the research repo on the iCloud Desktop denied by TCC for 16 days — the 08-31..09-15 manifests were only committed on 09-16, so they no longer carry a same-day third-party timestamp. Status is open, with three options on the table: move the notary repo off the Desktop (lead's preference), grant Full Disk Access and put the research repo on the configured branch, or change the notary config. Practical form of the rule: nothing under `~/Desktop` may be READ **or WRITTEN** by a launchd-spawned process, and any such job must fail loudly rather than log-and-continue.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M4-53 · P2 · DOC_STALE
- **Source:** `memory/project_principles.md:7`
- **Quote:** 「**Where to find them:** `docs/PROJECT_PRINCIPLES.md` is the authoritative doc.」
- **Superseding evidence:**
  - `docs/PROJECT_PRINCIPLES.md:3` — 「Written 2026-04-18 after synthesizing external quant-practice critique + our own experiment logs.」
  - `docs/PROJECT_PRINCIPLES.md:14` — 「Our V4 Pearson ≈ 0.10 on a **single asset, single model**」
  - `docs/PROJECT_PRINCIPLES.md:48` — 「**Rule:** do not evaluate a model's "useful alpha" on `trade_rate=1.0`. Always report Sharpe(τ*) where τ* is the confidence-optimized threshold.」
  - `docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md:3` — 「**创建:** 2026-07-06 | **状态:** final (阶段性完成,收口)」
  - `CLAUDE.md:25` — 「**决策检查清单**(架构/特征/loss 改动必答): 机制? 前置门(Ridge/LGBM)? 复杂度预算? 泄漏(shuffle-future + 偏移谱峰@0 + 折外泄出=0)? OOS 逐折同号? σŷ/σy≥0.02?」
- **A reader could wrongly conclude:** A reader treats the 7 principles as the current gate list — e.g. demands a confidence gate |q50|/(q90-q10) and Sharpe(tau*) for the cross-sectional book, or re-validates at '700d' — instead of CLAUDE.md's Core Constraints and decision checklist.
- **Affects:** future_eval, future_retrain · **Severity reason:** The 'authoritative doc' was written 2026-04-18 for the single-asset LOB/V4 track (closed out 2026-07-06) and several principles are instrument-specific to it (single-asset Pearson 0.10, confidence-gated trade_rate, 100d/700d validation), while the governing constraints for the current wide cross-sectional book live in CLAUDE.md.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 scope correction (docs/PROJECT_PRINCIPLES.md header + 2026-07-06 single-asset closeout + CLAUDE.md Core Constraints):** `docs/PROJECT_PRINCIPLES.md` was written **2026-04-18** for the single-asset LOB/V4 track, which was closed out on 2026-07-06; it is history, not the current gate list. Principles that are instrument-bound and do NOT transfer as written: #1 (single-asset Pearson ≈0.10 as the reference IC), #3 (confidence gate `|q50|/(q90-q10) > τ`, Sharpe(τ*), trade_rate — the live book is a cross-sectional 4h maker-only book with no quantile head), #2's '100d smoke / re-validate at 700d' cadence. The governing list today is CLAUDE.md's Core Constraints plus the decision checklist (mechanism? Ridge/LGBM pre-gate? complexity budget? leakage triad? OOS same sign per fold? σŷ/σy ≥ 0.02?), and admission is judged at the **book layer** (judge_v4 `g = net_ex/gross_total`), not on score-layer IC. Still durable: breadth > precision, PBO as a real tax, attribute alpha against simple baselines, capacity matches signal, attribute P&L by regime.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-02 · P2 · DOC_STALE
- **Source:** `memory/live_battery_gate_coverage_blind_spot.md:7`
- **Resolution:** ⚠ **口径(KB-73)**: 本行引用的「逐套件 N/M」只在同一解释器下可比 —— 电池 `run_acceptance.sh:28` 的 `PY="${ACCEPT_PY:-/usr/bin/python3}"` 是**可被环境变量覆盖的默认值**, 认证它的断言只对源码做子串检查, 且 `state/acceptance/` 38,177 份工件中 0 份记录解释器版本; 2026-07-27 前两入口一钉一裸, 裸 `python3` 制造过两个假红。引用计数时须写明解释器。
- **Quote:** 「跑 `run_acceptance.sh` 全电池(123 套件, 解释器钉 /usr/bin/python3 3.9)」
- **Superseding evidence:**
  - `STATE.md:7` — 「**运行树电池 ACCEPTANCE: ALL GREEN 135/135(130 套件 + 5 审计门, tests_env_loading 14/14)**」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:42` — 「准确电池口径：**130 个测试套件，129 过；5 个审计门均过；1 个凭据加载套件失败，battery rc=1，NOT GREEN。**」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:199` — 「第三轮分代理曾将 130 测试+5 审计统称 135 套件，本轮更正且旧归档不改。」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:41` — 「"drift_gate:$_SELF/ops/check_upstream_drift.py"」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:73` — 「"metrics_freeze:$_SELF/ops/check_metrics_freeze.py"」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:74` — 「"gate_coverage:$_SELF/ops/gate_coverage.py"」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:206` — 「"income_callers:$_SELF/ops/income_callers.py"」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:207` — 「"guard_reach:$_SELF/ops/guard_reach.py"」
  - `/Users/haosiyu/dl_quant_live/run_acceptance.sh:285` — 「echo "ACCEPTANCE: ALL GREEN (${#SUITES[@]}/${#SUITES[@]} suites exit 0)"」
  - `STATE.md:59` — 「safe_commit 09:36:30→09:51:58Z, 电池 **132/132**」
- **A reader could wrongly conclude:** A reader accepts a '123/123' or ~10-minute run as the full acceptance battery, or reports the current run as '135 suites', mixing test suites with audit gates.
- **Affects:** reporting · **Severity reason:** Misleads battery verification and reporting: '123 suites / ~10 min' no longer describes a full run (now 130 test suites + 5 audit gates, ~15–17 min), and a clone without .env is NOT GREEN.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 电池现为 135 项 = 130 个 live/tests_* 套件 + 5 个 ops 审计门(drift_gate / metrics_freeze / gate_coverage / income_callers / guard_reach); 运行树 ef60f85 读数 `ACCEPTANCE: ALL GREEN (135/135 suites exit 0)`, 报数写「130 套件 + 5 审计门」, 不写「135 套件」(独立复审第四轮 §7)。整轮约 15–17 分钟(09-12 09:36:30→09:51:58Z; 09-13 11:47→12:04Z), 不是 10 分钟。无 .env 的克隆里 tests_env_loading 会红 ⇒ rc=1 NOT GREEN(REV4 §2.1), 不得改写为全绿。run_acceptance.sh 另有注册守卫: live/tests_*.py 未登记即拒跑。
- **Confidence:** VERIFIED (quote+receipt opened; SUITES array counted 135 entries, 5 under ops/; acceptance logs 20260913T114702Z_* span 11:47→12:04Z) · **Quote re-verified at assembly:** exact

### M5-05 · P2 · DOC_STALE
- **Source:** `memory/replay_seat_path_is_not_live_seat_path.md:10`
- **Quote:** 「**事实(2026-09-02)**: w10 hardened 回放 2026 年 msharpe 席位 king≈0.01/fund 0.99; 实盘同规则同 900 锚回看给 king 0.21/fund 0.79(掩码后)。规则相同, 差在 king 腿收益序列: 回放用 `slow_pred_hist_oos.npy`(逐年折外, 2026 由 ≤2025 模型给), 实盘 king 逐月重训。」
- **Superseding evidence:**
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:9` — 「| 年 | net_ex 无偏(CAL=log) | net_ex 旧口径(expm1) | Sharpe 无偏 / 旧 | 最坏月(无偏, bps gross) | 年内 maxDD 无偏 / 旧 | w3_king 无偏 / 旧 |」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:13` — 「| 2026(→08-30) | **+2.013** | +4.247 | **3.84** / 7.63 | −294 (08) | 771 / 689 | 0.36 / 0.05 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:83` — 「席位 king 均权 0.6241 → 0.6190。」
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `STATE.md:255` — 「**在役书两条模型腿的梯度都止于 2025 年底**(king `tr = YRA<2026` 同), 2026 全年未进入任何梯度。」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:196` — 「- **今后回放报数一律以 (iii) 交易所窗口口径为主口径**(记账窗 (N, N+4h], 复利), (i) 只作面板对照;」
- **A reader could wrongly conclude:** A reader keeps assuming the replay king seat is ≈0 (seat-sensitive arms look falsely low-turnover) and labels 2026 replay numbers 'fund 0.99'. The unbiased replay puts king at 0.36 (2026) and v4 A0 at 0.62 (2024+), above the live masked 0.382. 'Live king retrained monthly' also does not mean fresher gradients: both legs stop at end-2025.
- **Affects:** future_eval, reporting · **Severity reason:** The inline warning still says 待复验, but the re-measurement exists and reverses the seat bias direction, so seat-sensitive arm evaluations and 2026 replay reporting would use the wrong premise.
- **Proposed correction (exact text):** ⚠ 复验结果(2026-09-13 审计补): 「回放 king≈0.01/fund 0.99」只属 CAL=simple 伪凸性口径; 同日无偏复验 w3_king 2026 = 0.36(旧 0.05, RESULT_caliber_revalidation L13), v4 回放 A0 2024+ king 均权 0.62(T4 RESULT L80), 实盘掩码席位 09-13 = king 0.382(REGIME_DASH L16) ⇒ 回放席位已不是 ≈0, 且点值高于实盘(两者时段与掩码口径未逐项对齐), 偏差方向反转。机制(席位路径装置内生、与实盘分道)保留; ② 改为「引用回放数字时声明该回放的 king 均权, 并附 W3FIX=实盘当前掩码席位臂」; 「实盘 king 逐月重训」加注: 在役两腿梯度都止于 2025 年底(STATE §4), 差异来自折与席位历史, 不是更新鲜的梯度。本条旧警示里「正确口径 = CAL=log」已被 (iii) 记账窗复利 / v4 RAW 记账口径取代。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-06 · P2 · DOC_STALE
- **Source:** `memory/two_instruments_disagree_reconcile_first.md:11`
- **Quote:** 「修正后: **Δnet +0.19~0.22(CI 排零)、逐年八数全正、Δ夏普 +0.351 CI[+0.107,+0.592] 显著 ⇒ 可上线候选**。」
- **Superseding evidence:**
  - `docs/REVIEW_caliber_final_2026-09-04.md:100` — 「| 2026-08-25 14:47Z | transcript | `w8_blend_replay.py`(copy of w7) | 同上 | Σ-simple | expm1 | 否 |」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「08-26/09-04 的"V2MAIN 净≈0"读数(combo_recheck: C−A log +0.005 / 复利 +0.079, P 0.50/0.79, 装置刻度 net_ex)属于装置刻度: 本轮同刻度下三口径 2024→26 全部 CI 含 0(§4 次表)」
  - `docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:191` — 「2025 单年在每一种口径下都未定(CI 含 0: (i) [-0.323,+0.436] / (iii) [-0.116,+0.686], s42)。」
- **A reader could wrongly conclude:** A reader cites 'Δ Sharpe +0.351 CI[+0.107,+0.592] significant, all eight yearly numbers positive' as the standing evidence for the V2MAIN 45% mix. Under unbiased calibers 2025 is undecided on every caliber and the device-scale 2024→26 CI contains 0.
- **Affects:** reporting, future_eval · **Severity reason:** The only numbers in the note that look like current evidence for the V2MAIN mix are CAL=simple-stale, and the unbiased re-check no longer supports 'all eight yearly numbers positive'.
- **Proposed correction (exact text):** ⚠ 口径更正(2026-09-13 审计补): 上述「修正后」数字出自 `w8_blend_replay.py`, 该装置对 Σ-simple y4 做 expm1(REVIEW_caliber_final L100 判「否」, 即 E-0904-F 伪凸性), 属 CAL=simple-stale, 不得作为 V2MAIN 混合的现行证据。无偏复核(RESULT_f10_caliber_sensitivity §4–§5, 体检主臂形态, 非同一本书): 每 gross 口径 2024→26 双种子 CI>0, 但 2025 单年三口径全部未定(不再是「逐年八数全正」), 装置刻度 2024→26 三口径 CI 含 0。本条教训(新旧仪器反向先对账)不受影响。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-07 · P2 · DOC_STALE
- **Source:** `memory/sigma_caliber_must_match_pnl.md:11`
- **Quote:** 「用执行器口径回放序列自身的波动(sd 22.69 bps/锚 ⇒ 日 sd 125U @NAV15k/1.5×)重算: **z=−2.51σ, 经验频率 0.84% 的 3 日窗**(2024 起) —— 坏但不异常。」
- **Superseding evidence:**
  - `docs/REVIEW_f10_blend_deployment_2026-08-23.md:125` — 「**实盘 3 天 −497U 在此口径下 z=−1.91, 经验频率 2.83%**(≈每 35 个 3 日窗一次)⇒ 比我先前两版说法(−3.7σ / −2.51σ)都更"正常"。」
  - `docs/REVIEW_f10_blend_deployment_2026-08-23.md:128` — 「**结论口径纪律**: 自本节起, 宽书表现一律以 **simple/fixed/const-gross** 报, 引用旧数(1.173/2.42 或更早的 1.316/3.06、2.42、3.59、4.3)必须标注为历史口径。」
  - `docs/REVIEW_f10_blend_deployment_2026-08-23.md:114` — 「装置 jpline /tmp/w3_joint.py(audit-caliber-o 建, 我复核语义: cal=simple ⇒ y→expm1 贯穿盈亏与价格路径;」
  - `docs/RESULT_caliber_revalidation_2026-09-04.md:3` — 「# RESULT · 无偏口径复验(E-0904-F): 回放装置 CAL=log(=原始 y4=Σ5m简单收益) vs CAL=simple(expm1, 伪凸性)」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:97` — 「**A0 无条件: +0.6342 bps/锚, CI95 [+0.1653, +1.1071], 夏普 1.2912 ⇒ 2.0× gross 下 +27.8% NAV/年, CI95 [+7.1%, +48.6%]。**」
  - `STATE.md:4` — 「实现 gross 227,672U / 目标 235,111U = **96.8%**」
  - `STATE.md:4` — 「NAV 117,566.70(−207U 含佣金)」
- **A reader could wrongly conclude:** A reader judges a live loss against 'daily sd 125U', Sharpe 2.42 and the z −2.51σ precedent. Those numbers come from NAV 15k at 1.5× and g=1.0; the same document revised them to z −1.91 on an expm1 caliber that E-0904-F later voided. σ should instead come from the v4 per-gross series at NAV ≈117.6k / gross ≈228k.
- **Affects:** reporting · **Severity reason:** Loss-severity reporting would reuse a σ and Sharpe from NAV 15k at 1.5× on a pre-v4 caliber that were revised the same day and later voided, on a book now about 10× larger.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计补): ① 同一受据文档 §17(08-25 11:5xZ)已把本案改为 z=−1.91 / 经验 2.83%(REVIEW_f10_blend L125), 并规定旧数 1.173/2.42 一律标历史口径(L128); 但 §17 用的是 cal=simple(expm1)装置(L114), 已被 E-0904-F 判为伪凸性 ⇒ −2.51σ 与 −1.91σ 都不是现行口径读数, 只保留「σ 与净额同源、优先经验频率」这条方法。② 「日 sd 125U」是 NAV 15k × 1.5× 的绝对数; 现 NAV ≈117.6k、实现 gross ≈228k(STATE 09-13 12Z), 不可复用; σ 须按 v4 口径(g = net_ex/gross_total, 记账 y4 = Π(1+r)−1)从当期序列重算再换算到当期 gross。③ 现行参考夏普 = A0 无条件 1.2912(CLOSEOUT_uplift_program L91), 不是 2.42 / 4.3。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-08 · P2 · DOC_STALE
- **Source:** `memory/error_ledger_practice.md:11`
- **Quote:** 「节律: |单锚|>2σ(≈78U)事件触发 24h 入账;」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:6` — 「**复盘节律**: ① 事件触发 — 任何 |单锚|>2σ(实测 σ≈39U, 即 |Δ|>78U)24h 内必须成 entry;」
  - `STATE.md:115` — 「> **[2026-09-03 12:5xZ] ★ 入金 +62,998 USDT(12:44:01Z 到账, 权益 84,036)· 用户裁定"一步到位"**: 16:00Z 锚按 constant_leverage_2.0 直接 sizing 至 gross ≈168k(现 41.7k, ×4.0), 不爬坡。」
  - `STATE.md:4` — 「实现 gross 227,672U / 目标 235,111U = **96.8%**」
  - `STATE.md:4` — 「NAV 117,566.70(−207U 含佣金)」
  - `/Users/haosiyu/wide_shadow/intraanchor_depth_watch.py:25` — 「SHORTLEG_2H_USDT = -100.0」
- **A reader could wrongly conclude:** A reader applies the 78U (2σ) entry trigger, or reads a −100U short-leg depth alert, as marking an abnormal event on a book about 10× larger. Routine anchors then qualify, the trigger turns into always-on noise, and real outliers stop standing out.
- **Affects:** live_trading, reporting · **Severity reason:** The absolute-USDT incident trigger and depth-watch line were calibrated at ~15k NAV and 1.5× gross; on a ~228k-gross book they no longer separate abnormal anchors from routine noise.
- **Proposed correction (exact text):** ⚠ 尺度过期(2026-09-13 审计补): 「2σ≈78U」来自 08-20 实测 σ≈39U(当时 NAV≈15k、gross 1.5×)。09-03 入金后按 constant_leverage_2.0 运行, 09-13 12Z 实现 gross 227,672U / NAV 117,566.70, 书规模约为当时 10 倍 ⇒ 78U 与锚间巡检器 `SHORTLEG_2H_USDT = -100.0` 这类绝对 U 阈值已失去原含义。触发线应改写为相对量(按当期 v4 序列重估 σ, 以 bps of gross 表示)再换算; 重标前本条阈值只作历史记录, 不作入账判据。
- **Confidence:** INFERRED (NAV, gross and both threshold definitions VERIFIED from receipts/code; the ~10× miscalibration assumes per-anchor σ in USDT scales with gross and was not re-measured) · **Quote re-verified at assembly:** exact

### M5-09 · P2 · DOC_STALE
- **Source:** `memory/team_protocol_and_state.md:13`
- **Quote:** 「the single MUTABLE snapshot: live config, in-flight tasks *with named owners*, frozen-do-not-touch list, registered defects, and the caliber discipline for every number that gets quoted. **Rewritten, never appended.** Carries a "last verified at / by" line.」
- **Superseding evidence:**
  - `STATE.md:4` — 「> **[2026-09-13 13:0xZ] ✅ 复场首锚(12Z)验收通过**」
  - `STATE.md:127` — 「# STATE — 当前状态唯一真相源」
  - `STATE.md:129` — 「> **★ 09-04 09:34Z σ_fund gross 阶梯已上线(执行器 4b8ca20 电池 124/124; 仪表盘作业 com.hsy.sigma_ladder N+52):**」
  - `docs/PREREG_deploy_sigma_ladder_2026-09-04.md:29` — 「- **处置:** launchd `com.hsy.sigma_ladder` 卸载; 状态文件移为 `sigma_ladder.json.reserve_20260904`;」
  - `STATE.md:137` — 「> **重置于 2026-08-26 milestone(combo 换装)。** 此前全部历史横幅 → git 历史」
- **A reader could wrongly conclude:** A reader treats every STATE.md line as current because the file is 'rewritten, never appended' and acts on a superseded banner, e.g. '09-04 σ_fund gross 阶梯已上线', which was withdrawn the same day.
- **Affects:** reporting, live_trading · **Severity reason:** The note tells readers STATE.md is a rewritten, verified snapshot, so superseded banners that are still in the file (e.g. a withdrawn deployment) would be read as current live state.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): since the 2026-08-26 milestone reset, STATE.md is kept as dated banners prepended above the `# STATE` header (≈120 banner lines by 09-13), not rewritten in place, and it has no 'last verified at / by' line. Older banners are not retracted inline (e.g. L126 '09-04 σ_fund gross 阶梯已上线' was withdrawn by docs/PREREG_deploy_sigma_ladder_2026-09-04.md L29). Read the newest banners first, and verify any older banner against its receipt before acting on it.
- **Confidence:** VERIFIED (quote+receipt opened; grep found no 'last verified' line in STATE.md) · **Quote re-verified at assembly:** exact

### M5-11 · P2 · DOC_STALE
- **Source:** `memory/replication_must_replicate_same_contrast.md:12`
- **Quote:** 「but CONSTspl27's monthly folds come from **seed-42** training (no true `mE1c_s2027` exists) ⇒ the second seed's deployment-equivalent confirmation is **not** complete.」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:16` — 「| FIX7 - CONST2027 | +0.248007 | [+0.055103, +0.439083] | [-0.000272, +0.540652] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:18` — 「| FLOOR5 - CONST2027 | +0.192044 | [+0.026597, +0.353683] | [+0.052435, +0.344195] |」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:23` — 「FIX7和FLOOR5在主窗按原UTC日块规则均得到REPLICATED_WITH_CLEAN_REFERENCE；这个程序标签只指原历史规则复核。FIX7的30日块下界−0.000272，仍属跨零，不能四舍五入成正数，也不能追加bootstrap抽样直到变绿。」
  - `STATE.md:210` — 「★ 09-09 更正: 干净 CONST2027 参照研究员 09-07 已完成 20/20 + 两次回放 rc0,」
- **A reader could wrongly conclude:** A reader concludes FIX7/FLOOR5 still lack a clean second-seed confirmation and re-queues CONST2027 work or discounts FIX7, although the clean reference replicated both under the original UTC-day rule.
- **Affects:** future_retrain, future_eval · **Severity reason:** The note says the second-seed deployment-equivalent check is incomplete, but a clean CONST2027 reference was trained and replayed on 09-07; that bears on the FIX7 epoch rule adopted for the October retrain.
- **Proposed correction (exact text):** ⚠ Superseded (2026-09-13 audit): a clean CONST2027 (seed-2027 monthly folds, 20/20) was trained and replayed by the independent researcher on 2026-09-07 (`codex_const2027_replay_2026-09-07/RESULT.md`; acknowledged in STATE.md §3 on 09-09). Same-type contrasts on the frozen window: FIX7 − CONST2027 +0.248 [+0.055, +0.439] (UTC-day blocks; 30-day blocks [−0.0003, +0.541], crosses zero), FLOOR5 − CONST2027 +0.192 [+0.027, +0.354] ⇒ REPLICATED_WITH_CLEAN_REFERENCE under the original day-block rule. The second-seed confirmation is complete for that rule (it is the clean reference for the old constant-seed validation-best recipe, distinct from the G3 stable FIX7, per STATE.md §3). FIX7's 30-day-block sensitivity still crosses zero, and the forward shadow and user ruling are still outstanding.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### MK-06 · P2 · OPEN_NOT_MEASURED
- **Source:** `memory/regime_driver_is_breadth_not_funding.md:3`
- **Quote:** 「regime 真因=宇宙广度非funding水平(2026-08-28 实测): 月广度corr+0.56/宽档+2.97bps vs 窄档−2.00; funding水平corr反号−0.48; 当前双指标有利区」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:13` — 「| **H1** 离散度/广度 regime 移动 | **不可判** | 落差本身不显著: 2026-08 相对 2026-H1 价格 −4.85 bps, 判决区间 [−13.38, +3.67]; 实盘 D2 −6.32 [−17.25, +4.61]。点估计: 状态分布移动只解释落差的 −3%(DISP24)到 +13%(BREADTH72) |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:26` — 「3. **实盘窗的状态并不罕见**: DISP24 在历史 83 分位、SIGF 75、BREADTH72 55、BTC72 50、MUF 49、PUMP72 47。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T2/RESULT_T2_carry_net_sizing_2026-09-13.md:10` — 「falls steadily to **0.226 at the 2026-08-01 refit, CI95 [−0.008, +0.460]**」
  - `memory/regime_driver_is_breadth_not_funding.md:19` — 「W3FIX 正典按 nsel 分档 2025-26 夏普 <250: 6.5 | 250-300: 7.8 | 300-350: 5.4 | 350+: 2.6(窄反而更好)」
- **A reader could wrongly conclude:** Breadth, not funding, is the regime driver for the current book, and today's state is favourable.
- **Affects:** future_eval, reporting · **Severity reason:** Headline numbers come from a CAL=simple instrument and the note's own era caveat reverses them for 2025–26; on v4, breadth state explains ≤13% of the August drop, and funding dispersion drives how much carry price compensates (T2).
- **Proposed correction (exact text):** description 改为: "08-28 旧仪器(CAL=simple, 68 月)读数: 月广度 corr +0.56、funding 水平 corr −0.48; ⚠ 未在 v4 复测; 本条时代注: 2025–26 窄档反而更好; T1(v4): 广度状态移动只解释 2026-08 落差的 ≤13%, 亏损在状态内, 实盘窗广度 55 分位不反常; T2: 价格对 carry 的补偿随资金费离散度变(κ* 低→高离散 0.97/0.83/0.63) ⇒「regime 真因=广度」不得作现行机制标签"
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### KB-61 · P3 · DOC_STALE
- **Source:** `memory/export_gate_v2_falsifiability_closure_2026_09_12.md:3` · xref TRN-29
- **Resolution:** XREF AUDIT_TRAIN TRN-29 — CROSS-REF: the r20 export gate v2 is APPLIED (contract 1188267a, 2026-09-12T09:04:39Z) — owned by AUDIT_TRAIN TRN-29; the memory description still says PROPOSED/NOT APPLIED.
- **Quote:** 「PROPOSED2 contract 01692565 (NOT APPLIED, user ruling pending)」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/ELIGIBILITY_CONTRACT.json (sha256 1188267a…)` — 「"applied_utc": "2026-09-12T09:04:39Z"; gates.BUNDLE_export.approved_source_sha256 = ["d63f4ec3f9e657259c2d4826f95552007f34eb63eab1d67357d8ad5b54cd5c1e"]」
  - `STATE.md:61` — 「✅ 资格合同出口门已应用(用户字 09-12)**: `retrain_2026-09/v4_chain_2026-09-09/ELIGIBILITY_CONTRACT.json` `gates.BUNDLE_export` = `v4e_gate_export_v2.py`(d63f4ec3, r20 闭包门), 合同 sha 3299dc97 → **1188267a**」
  - `docs/audit_pipeline_2026-09-13/AUDIT_TRAIN.md:124` — 「| TRN-29 | P3 | DOC_STALE | reporting | DOC (memory) | Memory says the r20 v2 export gate is 'PROPOSED 未应用'; the chain contract shows it APPLIED on 2026-09-12T09:04:39Z |」
- **A reader could wrongly conclude:** The October export can still be judged by the old contract 3299dc97, and v2 needs a user word.
- **Affects:** future_retrain, reporting · **Severity reason:** The memory index and note still say the v2 export gate awaits a ruling; the chain contract applied it on 09-12, which changes what an October export must pass.
- **Proposed correction (exact text):** description 改为: "r20 (2026-09-12) — export gate v2 d63f4ec3 + signal gate abc45cad **APPLIED** 2026-09-12T09:04:39Z (contract 3299dc97 → 1188267a, commit 6316d72e, user word 09-12); original gate f814c728 was not falsifiable (6 probes); four exact device identities usable as content gates; what v2 still cannot catch"; 正文首段「状态(2026-09-12)」前插入「**已应用(2026-09-12T09:04:39Z, 合同 1188267a)**」; MEMORY 索引「(PROPOSED 未应用)」改为「(已应用 09-12)」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### M1-26 · P3 · OPEN_NOT_MEASURED
- **Source:** `memory/september_losses_replay_also_lost_t5c_2026_09_13.md:3`
- **Quote:** 「deployed carry was understated by 0.25」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5dR/PREREG_ADDENDUM_T5dR_declared_interval_reconciliation_2026-09-13.md:7` — 「T5d 的「账本与时间差 0 不符」不是独立验证。本附录对 T5d 窗内每个有分歧或处于切换的结算取申报间隔, 重算部署书与回放书的 carry、价格与净额的两个差, 回答: (a) 部署 king 链 carry 修正 +0.253(SKR +0.207)是否改变; (b) 任何标签是否改变。」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:46` — 「SKR 09-07 20Z」
- **A reader could wrongly conclude:** A reader quotes 'deployed September carry understated by 0.25 bps/anchor' and the widened net gap −1.56 as final before T5d-R reports whether declared intervals change them.
- **Affects:** reporting, future_eval · **Severity reason:** The description states the T5d carry correction (+0.25, mostly SKR) as settled although its interval ground truth is now under declared-interval reconciliation (T5d-R, no result) and SKR has an up-switch settlement in the flagged set.
- **Proposed correction (exact text):** deployed carry was understated by 0.25 (T5d, ledger-gap intervals; provisional — T5d-R is re-deriving it on data.binance.vision declared intervals because the ledger interval is the snapped timestamp gap, which mislabels short→long switch settlements incl. SKR 09-07 20Z)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-27 · P3 · DOC_STALE
- **Source:** `memory/t1_edge_diagnosis_2026_09_13.md:15`
- **Quote:** 「deployed book carries 2.19x the replay book on the same 30 anchors 08-26..08-30, cause not traced」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md:9` — 「T1 的 2.218 是 29 锚均值, 含那两个 king 形态锚。」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「T5 的构造桥可描述重建书的差，但 Shapley 是指定干预集合的分摊，不是自然实验因果比例；T×P 交互独立复算非零。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md:43` — 「T1 的 LIVE_D2 与本文部署书在这 61 个九月锚上逐位相同(G-T1c), 所以 T1 在这些锚上的部署书模型 carry 同样偏低 +0.248 [+0.043, +0.498]」
- **A reader could wrongly conclude:** A reader re-opens the deployed-vs-replay carry gap as unexplained or quotes T1's D2 carry and realized/modelled 0.89 ratio as corrected numbers.
- **Affects:** reporting · **Severity reason:** The addendum still says the 2.19× construction gap is untraced and leaves D2 September carry uncorrected, though T5 decomposed the gap and T5d found D2's modelled September carry understated; the linked notes carry the updates.
- **Proposed correction (exact text):** Replace "(deployed book carries 2.19x the replay book on the same 30 anchors 08-26..08-30, cause not traced)" with "(deployed book carries 2.19x the replay book on 08-26..08-30; decomposed by T5 on the 27 combo-form aligned anchors — the 29/30-anchor figure mixes two king-form anchors — as Shapley accounting shares FTRIM absent 58% / chain warm-start 27% / stop-path difference 18.5%, scores −1%; not causal shares, REV4 §4.3). T5d: T1 LIVE_D2 September modelled carry is understated by +0.248 [+0.043, +0.498] on the 61 September anchors (x0910 interval defect; provisional pending T5d-R), so D2 carry 1.502 and the paid/model ratio 0.89 are not corrected".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-28 · P3 · DOC_STALE
- **Source:** `memory/t1_edge_diagnosis_2026_09_13.md:17`
- **Quote:** 「H5: 2022-23 low-dispersion mechanism only half supported」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T1/RESULT_T1_edge_diagnosis_2026-09-13.md:321` — 「**M4 不成立**(每锚亏损高档 −0.86 > 低档 −0.44; 按锚数加权, 低档约占合计亏损的 55%, 高档约 42%)⇒ 四臂一致 **DOES NOT FIT**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:131` — 「撤回该读法」
- **A reader could wrongly conclude:** A reader treats the 2022–23 low-dispersion + seat mechanism as partially confirmed and uses it to motivate a low-dispersion drawdown hedge.
- **Affects:** future_eval · **Severity reason:** 'Only half supported' softens a pre-registered DOES NOT FIT verdict on all four arms whose mechanism reading the lead withdrew; the bullet's details are right but the label invites reopening a low-dispersion hedge.
- **Proposed correction (exact text):** Replace "H5: 2022-23 low-dispersion mechanism only half supported" with "H5: 2022-23 low-dispersion mechanism DOES NOT FIT on all four arms under the pre-registered reading (M2 holds — carry paid, uncompensated in low sigma; M3 negligible +0.011 because the book was 98-99% fund with king leg 0; M4 fails — per-anchor loss larger in high sigma); the lead withdrew the low-dispersion + seat-blindness mechanism (PROGRAM r2 AMENDMENT 3, correction 2)".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-29 · P3 · DOC_STALE
- **Source:** `memory/deployed_carry_gap_is_ftrim_warmstart_stop_t5_2026_09_13.md:3`
- **Quote:** 「replay-only stop layer 18.5%」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:20` — 「**执行器逐名止损在役并被逐锚评估**: config `per_name_stop` enabled, profile wide(−30% / 连续 2 锚 / 冷却 7 天 / 5 USDT)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:21` — 「**8 个队列名全部 NOT FIRED**」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「T5 的构造桥可描述重建书的差，但 Shapley 是指定干预集合的分摊，不是自然实验因果比例；T×P 交互独立复算非零。」
- **A reader could wrongly conclude:** A reader skimming the index or description concludes production had no per-name stop and that 58/27/18.5% are causal shares of the August carry gap.
- **Affects:** reporting, future_eval · **Severity reason:** The body carries the lead and T5b corrections, but the description and Why line still say 'replay-only stop layer' / 'production has no per-name stop' and present the Shapley shares as an equation.
- **Proposed correction (exact text):** Description: "Deployed combo book's 2x modelled carry vs the A0 replay (08-26..08-30) — Shapley accounting shares over a chosen intervention set, not causal (T×P interaction non-zero, REV4 §4.3): FTRIM absent 58% + chain warm-start from king-form book 27% + stop-path difference 18.5% (replay target-layer stop vs the executor's own per_name_stop, which was live but did not fire on the August cohort — T5b); scores ~0; all in shorts on rn8<=-10bp names, ONGUSDT ~41%"; in Why replace "production has no per-name stop (stop_overlay.py only records)" with "the target file has no per-name stop; the executor's per_name_stop acts after target_live (T5b)".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-30 · P3 · DOC_STALE
- **Source:** `memory/stopped_longs_pinned_by_reshape_clamp_2026_09_13.md:3`
- **Quote:** 「Live per_name_stop cannot flatten stopped LONG positions」
- **Superseding evidence:**
  - `STATE.md:7` — 「W9 f8beb082」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:60` — 「新路径把这些名移出重整人口，之后以精确零放回，由 `clamp_held_untradable` 归入 `flatten_only`」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:70` — 「| 空头 reduced | 2 |」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:77` — 「实际 maker/补单成交、最终仓位零和 7 天冷却的首锚链仍须验收；空仓首锚不会自然覆盖 held-and-stopped 新路径。」
  - `STATE.md:4` — 「全退出与持有止损名出场路径本锚未覆盖(从空仓重建), 待首次发生时验」
- **A reader could wrongly conclude:** A reader believes live stopped longs are still pinned, that shorts always exited correctly, or that the fix is already verified on live fills.
- **Affects:** live_trading, reporting · **Severity reason:** The headline is in the present tense although W9 f8beb082 is deployed in ef60f85 (L17 records the deployment), and L9 'Shorts land flatten_only' is contradicted by the independent census (2 short 'reduced').
- **Proposed correction (exact text):** Description: "Before ef60f85 (2026-09-13 12:04Z) live per_name_stop could not flatten stopped positions — mostly longs (add_blocked/reduced); census 08-20..09-12 = 157 anchor×name instances on 20 names / 59 anchors incl. 2 short 'reduced'. W9 f8beb082 (deployed in ef60f85) removes stopped names from the reshape population and returns them at exactly 0 ⇒ flatten_only; verified at the target/plan contract only — actual fills, final zero and 7-day cooldown await the first held-and-stopped anchor; flatten_only top-ups follow the chase framework contrary to the maker-only clause (REV4 §2.4)." In L9 replace "Shorts land flatten_only." with "Shorts usually land flatten_only (census: 5 flatten_only, 2 reduced)."
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-31 · P3 · DOC_STALE
- **Source:** `memory/t5b_ftrim_residual_and_live_stop_audit_2026_09_13.md:15`
- **Quote:** 「the executor stop exists but its exit for longs is impeded」
- **Superseding evidence:**
  - `STATE.md:7` — 「W9 f8beb082」
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:60` — 「新路径把这些名移出重整人口，之后以精确零放回，由 `clamp_held_untradable` 归入 `flatten_only`」
  - `STATE.md:4` — 「全退出与持有止损名出场路径本锚未覆盖(从空仓重建), 待首次发生时验」
- **A reader could wrongly conclude:** A reader assumes stopped longs are still pinned in production after 2026-09-13 12:04Z.
- **Affects:** live_trading · **Severity reason:** Present-tense statement of a defect fixed by W9 in the running tree; low risk because the linked note records the deployment.
- **Proposed correction (exact text):** Replace "the executor stop exists but its exit for longs is impeded" with "the executor stop exists; before ef60f85 its exit was impeded (mostly longs); W9 f8beb082, deployed 2026-09-13 12:04Z, fixes it at the target/plan contract — first held-and-stopped live anchor still to be verified".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M1-32 · P3 · DOC_STALE
- **Source:** `memory/wide_book_needs_stop_layer.md:3`
- **Quote:** 「宽书零风控层; 止损在宽书降 maxDD 31-36%(在役书仅13.5%), 换装前必须移植」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:20` — 「**执行器逐名止损在役并被逐锚评估**: config `per_name_stop` enabled, profile wide(−30% / 连续 2 锚 / 冷却 7 天 / 5 USDT)」
  - `STATE.md:7` — 「W9 f8beb082」
- **A reader could wrongly conclude:** A reader thinks the live wide book runs without any per-name stop, or quotes the 31–36% maxDD reduction as the current stop-layer value.
- **Affects:** reporting, future_eval · **Severity reason:** 'Wide book has zero risk layer' is an 08-20 shadow fact written as a present property; the executor's wide per_name_stop has been live since the switch, and the 31–36% maxDD benefit is an 08-20 pre-clip-fix, pre-warm-up-fix reading never re-measured on v4.
- **Proposed correction (exact text):** ⚠ 状态(2026-09-13): 已移植 —— 执行器 `per_name_stop` wide 档(−30%/连续 2 锚/冷却 7 天/5U)在役(T5b 实测 W2 31/31 锚评估), W9 f8beb082(运行树 ef60f85)修复被止损持仓不归零;「宽书零风控层」只描述 08-20 影子。「降 maxDD 31–36%」为 08-20 jpline 装置、裁剪复利标签(E-0908-B)与暖机修复(r18)之前的读数, 未在 v4 口径重测。
- **Confidence:** VERIFIED (quote+receipt opened); 'not re-measured on v4' INFERRED from absence of a v4 stop/no-stop maxDD comparison in the receipts read · **Quote re-verified at assembly:** exact

### M1-33 · P3 · DOC_STALE
- **Source:** `memory/income_ledger_dedupe_twin_rows_e0909h_2026_09_09.md:13`
- **Quote:** 「修复在 `review/b0a573a1-executor` 分支(未部署)」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/live/binance_broker.py:2010` — 「# ★ DEDUPE ON (tranId, incomeType, symbol, asset) — NOT on tranId alone.」
  - `/Users/haosiyu/dl_quant_live/live/tests_disposition_matrix.py:514` — 「b681ca5 (E-0909-E clamp) deployed 06:05:30Z」
  - `STATE.md:7` — 「并推送(origin/main = ef60f85)」
- **A reader could wrongly conclude:** A reader discounts current daily realized-PnL/commission breakdowns as still missing COMMISSION twin rows, or re-opens a fix that is already live.
- **Affects:** reporting · **Severity reason:** The twin-row dedupe fix is described as undeployed on a review branch, but commit e1c4c87 is an ancestor of the deployed b681ca5 and of the running tree ef60f85.
- **Proposed correction (exact text):** 修复(e1c4c87, 去重键改 (tranId, incomeType, symbol, asset))已随 b681ca5 合入 main 并于 2026-09-12 06:05Z 部署, 现运行树 ef60f85 含该修复(`live/binance_broker.py` L2010; 2026-09-13 审计以 git merge-base 核); 部署前已写入的 daily_nav 历史行是否回写未经本条核实。
- **Confidence:** VERIFIED (code line opened; `git merge-base --is-ancestor e1c4c87 b681ca5` and `… e1c4c87 HEAD(ef60f85)` both true, run read-only this session) · **Quote re-verified at assembly:** exact

### M1-34 · P3 · DOC_STALE
- **Source:** `memory/venue_quant_rules_lock_e0910a_2026_09_10.md:15`
- **Quote:** 「(2) 候选(需预注册+用户字): 执行器识别 -4400 后本阶段停发剩余开仓单 + HIGH 页含 plannedRecoverTime; 复场重建分两锚建仓」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/live/binance_executor.py:55` — 「# ★ E-0910-A: the venue's account-level quantitative-rules lock. One -4400 in a submit loop means」
  - `/Users/haosiyu/dl_quant_live/live/binance_executor.py:58` — 「#   first -4400 and records the rest as `skipped_venue_lock`.」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:2012` — 「张开仓单未发(skipped_venue_lock); 场所 apiTradingStatus: 」
  - `/Users/haosiyu/dl_quant_live/live/tests_disposition_matrix.py:514` — 「b681ca5 (E-0909-E clamp) deployed 06:05:30Z」
- **A reader could wrongly conclude:** A reader re-proposes or re-implements the -4400 breaker, or expects -4400 rejections to keep flooding the submit loop on a restart anchor.
- **Affects:** live_trading · **Severity reason:** The -4400 breaker and the apiTradingStatus page are listed as an unimplemented candidate needing prereg + user word, but both are in the running executor (commit 3ff5e00, deployed with b681ca5).
- **Proposed correction (exact text):** (2) ✅ 前半已实现并在运行树(3ff5e00 熔断, 随 b681ca5 于 2026-09-12 部署, 现 ef60f85): 同一提交循环首张 -4400 后, 后续开仓单不发、记 `skipped_venue_lock`, reduce-only 照发, HIGH 页附 apiTradingStatus 锁指标与预计解锁(`live/binance_executor.py` L55–59, `scheduler/anchor_loop.py` L2012);「复场重建分两锚建仓」未见实现, 仍为候选; 看门狗码表仍不识别 -4400(熔断在执行器层)。
- **Confidence:** VERIFIED (code lines opened; `git merge-base --is-ancestor 3ff5e00 b681ca5` true; watchdog.py / watchdog_inputs.py grep for 4400/venue_lock = 0 hits) · **Quote re-verified at assembly:** exact (line moved 3->15)

### M1-35 · P3 · DOC_STALE
- **Source:** `memory/live_executor_transport_resilience_2026_09_09.md:24`
- **Quote:** 「**候选修复 = 规划期按 symbolConfig 有限上限截断目标, 改变发单 ⇒ 需用户字**(STATE §3)」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1919` — 「# ★ E-0909-E: the venue's finite cap, on the final numbers, fail-closed (see clamp_venue_cap).」
  - `/Users/haosiyu/dl_quant_live/live/tests_disposition_matrix.py:514` — 「_CAP_CLAMP_DEPLOYED_TS = 1789201439.0   # ★ SET 2026-09-12: b681ca5 (E-0909-E clamp) deployed 06:05:30Z; first anchor it governed = 08Z rid A1789201439」
  - `STATE.md:7` — 「并推送(origin/main = ef60f85)」
- **A reader could wrongly conclude:** A reader expects repeated -2027 rejections of the same delta (the PIEVERSE pattern) and re-proposes a fix that is already live.
- **Affects:** live_trading · **Severity reason:** The finite-cap truncation is still listed as a candidate awaiting the user's word, but clamp_venue_cap has governed live anchors since 2026-09-12 08Z.
- **Proposed correction (exact text):** **已部署**: 有限上限截断 `clamp_venue_cap`(961a858)随 b681ca5 于 2026-09-12 06:05:30Z 上线, 首个受治理锚 09-12 08Z(rid A1789201439), 现运行树 ef60f85 仍含(`scheduler/anchor_loop.py` L1919; 缩不放, 失败不改目标 + HIGH 页); 此后 −2027 类残差按套件断言应为零。
- **Confidence:** VERIFIED (code lines opened; `git merge-base --is-ancestor 961a858 b681ca5` true) · **Quote re-verified at assembly:** exact

### M1-36 · P3 · OPEN_NOT_MEASURED
- **Source:** `memory/funding_alpha_is_state_variable_not_factor_proxy.md:8`
- **Quote:** 「书层 fund 腿贡献保留 71~91%(2026 78%)」
- **Superseding evidence:**
  - `docs/PREREG_xregime_2026-09-02.md:108` — 「**D1 书层**(fund 腿矩阵换成残差化分数, w10_fundleg FEMAT)」
  - `multi_asset/exports/research/retrain_2026-09/w10_fundleg.py:17` — 「CAL = os.environ.get("CAL", "simple")」
  - `docs/REVIEW_caliber_final_2026-09-04.md:134` — 「fund +0.30/+0.74/+0.88」
- **A reader could wrongly conclude:** A reader quotes 71–91% book-layer funding-alpha retention as caliber-clean when the level (and possibly the ratio) was computed with the biased expm1 caliber.
- **Affects:** future_eval · **Severity reason:** The book-layer retention figure came from the w10_fundleg device whose default caliber is CAL=simple (expm1), which E-0904-F showed overstates the fund leg; the note carries no ⚠ flag and the book layer was never re-run on an unbiased/v4 caliber.
- **Proposed correction (exact text):** 书层 fund 腿贡献保留 71~91%(2026 78%)⚠(2026-09-13 审计: 书层数字出自 `w10_fundleg.py` FEMAT 注入, 该装置默认 CAL=simple(expm1 伪凸性; E-0904-F 复审: 该口径 fund 腿高估 +0.30/+0.74/+0.88 bps/锚), 运行命令未记录 CAL, 09-04 后未在无偏/v4 口径复测 —— 书层保留率待复测; IC 层(秩 IC 对单调变换不变)结论可继续引用)
- **Confidence:** INFERRED (device default CAL=simple read at w10_fundleg.py L17; the D1 book-layer run's CAL env is not recorded in the prereg; no post-09-04 re-run found) · **Quote re-verified at assembly:** exact

### M1-37 · P3 · DOC_STALE
- **Source:** `memory/carry_net_fund_leg_sizing_t2_2026_09_13.md:3`
- **Quote:** 「σ-state arm tripped the 0.165 ceiling and failed §7 (LEAK-SUSPECT, cause unresolved)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:144` — 「我把一个**量级启发**写成了「天花板/上界」, 并据此设泄漏警戒线 —— 超线**不等于**泄漏。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:144` — 「P5 改名为「**量级启发**(非上界)」; 1.5× 线改为「**调查触发**」, 超线只要求因果/时点调查, 不预判为泄漏; T2 结果里 σ 臂的「LEAK-SUSPECT」保留其**调查结论**(时点敏感、不可执行), 撤回「超天花板即泄漏」的措辞」
- **A reader could wrongly conclude:** A reader treats ≤0.11 bps / ≤+0.2 Sharpe as a hard upper bound for carry-net sizing arms and reads any arm above 0.165 as leaking, instead of as requiring a causal/timing investigation.
- **Affects:** future_eval · **Severity reason:** The description keeps the 'ceiling' framing that PROGRAM r2 AMENDMENT 4 withdrew (a magnitude heuristic, not an upper bound; exceeding it is an investigation trigger, not a leak signature); the body's Why already half-reflects this, so risk is low.
- **Proposed correction (exact text):** In the description replace "σ-state arm tripped the 0.165 ceiling and failed §7 (LEAK-SUSPECT, cause unresolved)" with "σ-state arm exceeded the 0.165 investigation trigger (P5 is a magnitude heuristic, not an upper bound — PROGRAM r2 AMENDMENT 4 #2) and failed §7; LEAK-SUSPECT is kept as the investigation conclusion (timing-sensitive, not executable under execution delay), not as a proven leak"; in Why replace "the ceiling P5 (≤0.11)" with "the magnitude heuristic P5 (≤0.11, not an upper bound)".
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-03 · P3 · DOC_STALE
- **Source:** `memory/king_freshness_is_not_book_value.md:3`
- **Quote:** 「滚动季度 OOS king(2026-09-04): rank-IC 0.06→0.09 但 msharpe 书夏普 3.12→2.78(Δ −0.17~−0.20 CI<0, 双种子), 换手 +20%」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:416` — 「- **连带作废/待复验(全部建立在 CAL=simple 上):** E-0904-C 全文(含"对数口径"更正段)、E-0904-D 的阶梯复测、RESULT_rolling_king 的"IC↑书↓"」
  - `docs/RESULT_rolling_king_monthly_2026-09-05.md:6` — 「**月度滚动重训把 king 的折外 IC 提高约 9%(2024–25), 但在正确口径下对书的净额没有可测影响(固定席位 Δ ≈ 0, CI 含 0; 动态席位同), 换手不变。按冻结判据 UNDECIDED: 既不录取, 也不否定。** 新鲜度本身不是这本书的杠杆。」
- **A reader could wrongly conclude:** A reader skimming the index or description concludes that fresher king models significantly hurt the book and argues against king retraining on that basis.
- **Affects:** future_retrain, reporting · **Severity reason:** The body (L12) already corrects 'IC up, book down' to 'IC up, book unchanged', but the description line still states the voided CAL=simple result (book Sharpe down, CI<0).
- **Proposed correction (exact text):** description 改为: 「[09-05 正确口径重立] 月度滚动 king rank-IC↑ 但书层 Δ≈0(UNDECIDED, 固定/动态席位同); 09-04 的「书夏普 3.12→2.78, Δ −0.17~−0.20 CI<0」是 CAL=simple 伪凸性读数, 已作废(E-0904-F; docs/RESULT_rolling_king_monthly_2026-09-05.md); embargo>节奏」
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-06 · P3 · DOC_STALE
- **Source:** `memory/king_incremental_refit_continue_undecided_2026_09_06.md:17`
- **Quote:** 「与 DL 侧 [[dl_monthly_refit_worse_than_yearly_two_seeds_2026_09_05]] §11(每月换模型 = 换初始化)同一族问题但答案相反方向: DL 缺的是初始化稳定, 树缺的不是。」
- **Superseding evidence:**
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:438` — 「2. **固定种子收回了一部分、不是全部**: CONST − R0(mE1, s42, 每折新种子)冻结 **+0.056 [−0.087, +0.196]**, − R0(mE1, s2027) +0.058 [−0.078, +0.186](VERIFIED AD2-2)—— 点估计约收回 §0.4/§10 缺口(−0.17 / −0.24)的三分之一, CI 含 0;」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:556` — 「1. **冻结读法 = (A) 早停是主因, 两个窗口都成立**(VERIFIED 表 AD3-3)。」
  - `docs/RESULT_dl_monthly_gate_2026-09-05.md:561` — 「⇒ 逐月折的验证切片(训练锚末 15%, ≈1000 锚)偏爱训练不足的早 epoch, 与 test 月的书层表现反向 —— 这就是 §11 提出的机制本身, 不只是伴随现象。」
- **A reader could wrongly conclude:** A reader designs DL retrain fixes around seed or initialisation stability instead of the epoch-selection rule (FIX7/FLOOR5).
- **Affects:** future_retrain · **Severity reason:** States that the DL leg's monthly-refit problem is initialisation instability. §11 showed a fixed seed recovers only about a third of the deficit, and §12 attributed it mainly to validation-based early stopping.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 「DL 缺的是初始化稳定」已被后续收据取代 —— §11 固定种子只收回约 1/3 缺口(docs/RESULT_dl_monthly_gate_2026-09-05.md L438), §12 冻结读法 (A)「早停是主因」(同文 L556/L561: 月折验证切片偏爱欠训练 epoch)。对照应读作「DL 缺的是 epoch 选择规则(FIX7/FLOOR5), 树没有这个问题」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-07 · P3 · DOC_STALE
- **Source:** `memory/second_instrument_rebuild_2026_09_05.md:8`
- **Quote:** 「打乱未来零检验 3/15 格超 2σ(零值 ≤0.010, 对称) ⇒ 冻结规则下重建 king 未录取; 10 种子诊断待」
- **Superseding evidence:**
  - `docs/RESULT_second_instrument_rebuild_2026-09-05.md:61` — 「每折 10 种子, 零值 IC 的折均值 +0.0017~+0.0039(50 次合并 +0.0024, 为真 IC 0.055–0.064 的 4%; 泄漏会把零值推到真 IC 量级), 种子间经验标准差 0.0041–0.0048 = 解析 SE(锚级 std/√n)的 **1.5–1.9 倍** ⇒ 50 次中 14 次(28%)超过 2·SE, 名义应 4.6%; 15 格 2σ 检验在名义率下期望 0.68 次超出, 在经验离散度下约 4 次。**答案: 是 SE 低估(置换标签模型的预测跨锚仍有序列相依), 不是泄漏。**」
  - `docs/RESULT_second_instrument_rebuild_2026-09-05.md:61` — 「预注册规则按字面仍判 FAIL, 重建 king 的录取需重新裁定(E-0905-E 同类: 判据写法不匹配统计量的真实离散度)。」
  - `docs/RESULT_second_instrument_rebuild_2026-09-05.md:64` — 「**全部含 0, 幅度 ≤0.04 bps/锚**; hist F2/log 2024 = −0.641 S−1.70 DD1789 vs pinned −0.642 S−1.68 DD1815 ⇒ 2020 起训练不改变 2024 亏损年。E-0905-A 结案为"非实质"。」
- **A reader could wrongly conclude:** A reader treats the source-rebuilt king as leak-suspect, or thinks the diagnostic is still outstanding and re-runs it.
- **Affects:** future_retrain, future_eval · **Severity reason:** The 10-seed diagnostic listed as pending was completed the same day. It attributes the 3/15 shuffle-null exceedances to under-estimated SE, not leakage, while admission still needs a re-ruling.
- **Proposed correction (exact text):** ⚠ 补(2026-09-13 审计): 10 种子诊断已完成(docs/RESULT_second_instrument_rebuild_2026-09-05.md L61): 零值 IC 折均值 +0.0017~+0.0039(真 IC 的 4%), 种子间离散 = 解析 SE 的 1.5–1.9 倍 ⇒「是 SE 低估, 不是泄漏」; 冻结门字面仍 FAIL, 重建 king 的录取需重新裁定(E-0905-E 同类)。未录取 hist king 附表(L64)全部含 0, E-0905-A 结案「非实质」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-20 · P3 · DOC_STALE
- **Source:** `memory/dl_monthly_earlystop_is_the_cause_2026_09_06.md:15`
- **Quote:** 「Effect vs yearly is +0.05..+0.15 bps/anchor/gross (≈ +2..+7 NAV %/yr @2×), same order as device resolution, so "parity with yearly" is the safe claim.」
- **Superseding evidence:**
  - `STATE.md:256` — 「「点估计 ≥ −δ 且 CI 含 0」是**冻结决策规则**, **不是非劣性证明**(后者要求 **CI 下界 > −δ**)。全部归档判官冻结窗扫描(装置 `codex_review_2026-09-07_ni_check.py`): **32 个「不劣于年折」型对照, 我方规则通过 18, 真正非劣检验(δ=0.05)只通过 3(FIX7_s42 / W2_s42)**;」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:23` — 「FIX7和FLOOR5在主窗按原UTC日块规则均得到REPLICATED_WITH_CLEAN_REFERENCE；这个程序标签只指原历史规则复核。FIX7的30日块下界−0.000272，仍属跨零，不能四舍五入成正数，也不能追加bootstrap抽样直到变绿。FLOOR5两种块长均为正。对yearly的区间均跨零，不构成统计非劣或优越证明；原规则中的mean≥−0.05及CI跨零是一项历史判读约定，不能代替预设非劣界的正式检验。」
- **A reader could wrongly conclude:** A reader writes 'monthly FIX7/FLOOR5 is at parity with yearly' in a deployment argument, implying tested non-inferiority.
- **Affects:** reporting · **Severity reason:** Under the 09-07 non-inferiority discipline a CI that contains 0 is a decision rule, not parity; 'parity/持平' wording must print δ and the CI lower bound.
- **Proposed correction (exact text):** ⚠ Correction (2026-09-13 audit): 'parity with yearly' is not established. A CI containing 0 is a frozen decision rule, not non-inferiority, which needs CI lower > −δ (STATE.md L254). Write: 'vs yearly: Δ +0.05..+0.15 with CI containing 0; non-inferiority at δ=0.05 only for FIX7_s42 (lower −0.048), not FLOOR5 and not against yearly2027; vs CONST42: CI>0.'
- **Confidence:** VERIFIED (quote+receipt opened); STATE.md line numbers as of 2026-09-13 ~15:00Z (STATE is prepended continuously — locate by the quoted text) · **Quote re-verified at assembly:** exact

### M2-21 · P3 · DOC_STALE
- **Source:** `memory/dl_monthly_earlystop_is_the_cause_2026_09_06.md:11`
- **Quote:** 「Levels frozen: yearly 1.557, R0 (seed per fold) 1.386, CONST 1.442, FLOOR5 1.610 (Sharpe 2.69, maxDD 870), FIX7 1.708 (S 2.87, maxDD 832)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:11` — 「冻结窗的高夏普里有 **2.075×** 是 regime 租金」
  - `multi_asset/exports/research/uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md:41` — 「| **冻结窗 2025-03..2026-08-10** | **2.9357** | 3168 | 0.8314 | **[1.306, 4.565]** |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「- The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL)」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
- **A reader could wrongly conclude:** A reader quotes 'FIX7 Sharpe 2.87' as the recipe's expected Sharpe rather than a single-regime window level.
- **Affects:** reporting, future_eval · **Severity reason:** Frozen-window levels (Sharpe 2.69/2.87) are quoted without the later caveats: the frozen window's Sharpe is largely regime rent (2.075×), shared by the whole candidate family, with its own CI95 [1.306, 4.565], while the full-cycle A0 Sharpe is 1.29.
- **Proposed correction (exact text):** ⚠ Caveat (2026-09-13 audit): these are frozen-window (2025-03→2026-08-10) levels. That window's Sharpe is mostly regime rent ('冻结窗的高夏普里有 2.075× 是 regime 租金', CLOSEOUT L11), is shared by the whole candidate family (median member 2.673 on FROZEN vs 1.006 on W_FULL, T6 RESULT L21), and A0's own frozen Sharpe 2.9357 has CI95 [1.306, 4.565] (CLOSEOUT L38). Full-cycle v4 A0 is 1.29 (TABLE_per_year_v4 L15). Use the paired Δ, not the level, for recipe decisions.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-25 · P3 · DOC_STALE
- **Source:** `memory/full_gradient_window_buys_nothing_2026_09_07.md:3`
- **Quote:** 「so neither "new data helps" nor "more training helps" survives.」
- **Superseding evidence:**
  - `docs/RESULT_dl_full_gradient_window_2026-09-07.md:120` — 「| **X7FULL** | **+0.0269** [+0.0238, +0.0302] | **+0.00508 [+0.00315, +0.00702]** | **CI > 0** |」
  - `docs/RESULT_dl_full_gradient_window_2026-09-07.md:127` — 「**⇒ 「排序≠净额」第七例现在成立, 而且是同臂、同样本、同 mask 的最干净一例。**」
- **A reader could wrongly conclude:** A reader skimming the description concludes that recent labels carry no information at all and closes the score-layer question too.
- **Affects:** future_retrain, reporting · **Severity reason:** The body revision (L8) withdraws 'neither path works': the full gradient window significantly improves score-layer IC, it just does not reach the book. The description still states the withdrawn reading.
- **Proposed correction (exact text):** Replace the description ending with: 'book-layer Δ UNDECIDED (−0.058 [−0.212, +0.103], sign window-dependent) while score-layer IC rises significantly (ΔIC +0.00508 [+0.00315, +0.00702]) — ranking ≠ net case seven; "neither path works" is withdrawn (see the 09-08 revision).'
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-28 · P3 · DOC_STALE
- **Source:** `memory/f10_one_bar_window_and_dl_monthly_2026_09_05.md:8`
- **Quote:** 「king 标签对齐候选」
- **Superseding evidence:**
  - `docs/RESULT_king_label_alignment_2026-09-06.md:7` — 「2. **换标签(主臂 ALT_SUM, Σ ret5 起点 E)让 king 略差, 按冻结读法 (B) 否决**: 可执行窗(E+25m→E+4h)IC Δ −0.0010 [−0.0020, −0.0001](s42, CI 上界 < 0 触发 (B))/ −0.0006 [−0.0016, +0.0003](s2027); 书层 2024→26 Δ −0.096 [−0.238, +0.047] / −0.110 [−0.257, +0.041] bps/锚/gross(点估计 −8%, CI 含 0), 2024 与 2026 为负年, 2025 ≈ 0; 换手 +0.4% / −8.8%; king 席位 0.30 / 0.30(BASE 0.26 / 0.30)。」
  - `docs/RESULT_king_label_alignment_2026-09-06.md:9` — 「4. **部署含义(预注册先写)**: (B) ⇒ 面板目标保留, bundle 与实盘不动, E-0905-J 只约束族门。」
- **A reader could wrongly conclude:** A reader re-queues king label alignment as an open candidate.
- **Affects:** future_retrain · **Severity reason:** The king label-alignment candidate listed here was tested on 09-06 and rejected under reading (B); the panel target stays.
- **Proposed correction (exact text):** ⚠ 补(2026-09-13 审计): 「king 标签对齐候选」已测并否决 —— 主臂 ALT_SUM 按冻结读法 (B) 否决, 面板目标保留, bundle 与实盘不动(docs/RESULT_king_label_alignment_2026-09-06.md L7/L9)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-29 · P3 · DOC_STALE
- **Source:** `memory/v2main_objective_arms_dro_l1ss_fail_2026_09_05.md:13`
- **Quote:** 「the DL leg enters as φ 0.45 of a model leg that sits on the msharpe seat w_king ≈ 0.65 ⇒ book effect ≤ 0.29× leg effect」
- **Superseding evidence:**
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl (anchor_utc=2026-09-13T12:00Z)` — 「"anchor_utc": "2026-09-13T12:00Z" … "w3_masked_king": 0.3821, "w3_masked_fund": 0.6179」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md:83` — 「C0 s42 KING_LIVE 分解: Δpnl +0.0233 / Δcarry +0.0065 / Δcost −0.0013; 换手 −0.63%; 席位 king 均权 0.6241 → 0.6190。」
- **A reader could wrongly conclude:** A reader estimates the live-book impact of a V2MAIN change at 0.29× the leg effect, or reopens loss reweighting because the replay seat already exceeds 0.5.
- **Affects:** future_eval · **Severity reason:** w_king ≈ 0.65 is the replay device seat. The live masked king seat is 0.382 (09-13), so a V2MAIN objective change passes through at about 0.17× in the live book, and the reopen condition 'model-leg seat ≥ 0.5' does not say which seat it means (v4 replay 0.62, live 0.38).
- **Proposed correction (exact text):** ⚠ Clarification (2026-09-13 audit): 0.65 is the replay device's msharpe seat (v4 A0 KING_LIVE mean 0.624, T4 RESULT L80). The live masked king seat was 0.382 on 09-13 12Z (REGIME_DASH L16), so live pass-through is ≈0.45 × 0.382 ≈ 0.17×. State which seat (replay or live) the reopen condition 'model-leg seat ≥ 0.5' refers to.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-32 · P3 · DOC_STALE
- **Source:** `memory/alarm_text_is_not_alarm_source.md:7`
- **Quote:** 「生成代码 `scheduler/anchor_loop.py` L1549-1557 把 `_clamp` 三类(持仓不在目标=退出 / 目标<2×min_notional / 止损 flatten·冷却)一律写成该文案」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1868` — 「f"held name(s) are withheld by the venue (maxNotionalValue=0): "」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「W1 ∪ W2 共 125 个「已停且持仓」实例: 多头 add_blocked **94** / reduced **23**, 空头 flatten_only 5 / 未列出 3; 用平移 a 预测的桶与记录 **122/122 相符**。」
- **A reader could wrongly conclude:** A reader opens L1549-1557 in the current executor, finds unrelated code and concludes the mislabelled alarm was fixed.
- **Affects:** live_trading, reporting · **Severity reason:** The code pointer has drifted: in the running tree ef60f85 the mislabelled text is at anchor_loop.py L1868, in the reduced/add_blocked/flatten_only clamp alarm. The lesson stands, and T5b shows the same alarm covers stopped longs pinned as add_blocked.
- **Proposed correction (exact text):** ⚠ 更正(2026-09-13 审计): 行号已漂移 —— 运行树 ef60f85 中该文案在 `scheduler/anchor_loop.py` L1868(`apply_withhold_and_reshape` 之后, `_clamp` 的 reduced/add_blocked/flatten_only 任一非空即发 HIGH「withheld by the venue (maxNotionalValue=0)」), 文案仍不区分来源。T5b(09-13)实测已停多头 125 例中 94 例被记作 add_blocked(uplift_r2 T5b RESULT L28)。排查时 grep 文案定位, 不按行号。
- **Confidence:** VERIFIED (quote+receipt opened; read-only read of ~/dl_quant_live at HEAD ef60f85) · **Quote re-verified at assembly:** exact

### M2-39 · P3 · DOC_STALE
- **Source:** `memory/live_giveback_is_long_extreme_funding_blowups_2026_09_06.md:12`
- **Quote:** 「the one untested lever is a per-name vol-aware cap (PREREG_tail_aware_sizing_2026-09-06)」
- **Superseding evidence:**
  - `docs/RESULT_tail_aware_sizing_2026-09-06.md:6` — 「1. **逐名按实现波动缩上限, 按冻结读法 (B) 否决: 它砍的是 alpha。**」
- **A reader could wrongly conclude:** A reader queues the per-name vol-aware cap as an open tail lever.
- **Affects:** future_eval · **Severity reason:** The 'one untested lever' was tested the same day and rejected under reading (B).
- **Proposed correction (exact text):** ⚠ Update (2026-09-13 audit): now tested and rejected (B): the per-name vol-aware cap cuts alpha (Δg −0.18 to −0.32 bps/anchor/gross, CI upper < 0; docs/RESULT_tail_aware_sizing_2026-09-06.md L7). See [[tail_aware_sizing_rejected_2026_09_06]]; the remaining directed lead is post-onset continuation ([[parabolic_onset_continuation_lead_2026_09_06]]).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-42 · P3 · DOC_STALE
- **Source:** `memory/allweather_trackC_age_tilt_voltarget_refuted_2026_09_05.md:15`
- **Quote:** 「最差年 Sharpe 极值 1.70(φ.65 s2027)/1.69(B5)/1.60(U-FROZEN 前视), 在役 1.14/1.30, 无一 ≥2」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:11` — 「| 2023 | 2190 | **−0.649** | **−1.94** | −1.82 | −1.93 | **16.8%** | **34%** |」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:15` — 「| **全窗 2022-06..2026-08** | 9139 | **+0.636** | **1.29** | 1.33 | 1.29 | — | 全史 ≥44%(r18 lev 收据, 下界) |」
- **A reader could wrongly conclude:** A reader cites 'live worst-year Sharpe 1.14/1.30' as the live form's worst year.
- **Affects:** reporting · **Severity reason:** The 'worst-year Sharpe' frontier (live 1.14/1.30) is computed on a window starting in 2024 and excludes 2023, which in the v4 full-cycle table is a −1.94 Sharpe year; the relative frontier comparison stands.
- **Proposed correction (exact text):** ⚠ 补(2026-09-13 审计): 「最差年 Sharpe」取自 2024 起的窗, 不含 2023; v4 A0 全周期 2023 = −1.94(TABLE_per_year_v4_caliber_2026-09-12.md L11), 在役形态全周期最差年是负年。前沿比较结论(无一 ≥2)不变, 但「在役 1.14/1.30」不能当作在役最差年引用。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M2-45 · P3 · VERIFIED_CURRENT
- **Source:** `memory/producer_is_launchd_managed_restart_verb.md:3`
- **Quote:** 「宽书生产者 shadow_loop_v3 由 launchd 代理 com.hsy.shadowloop(KeepAlive, env SHADOW_OFFSET_MIN=16, stdout→loop.out)托管; kill PID 即重生(PID 会变); 重启动词 = launchctl kickstart -k; RUNBOOK L33 nohup 会被锁拒绝(E-0904-A)」
- **Superseding evidence:**
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.shadowloop.plist:10` — 「<key>EnvironmentVariables</key><dict><key>SHADOW_OFFSET_MIN</key><string>16</string></dict>」
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.shadowloop.plist:12` — 「<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>」
  - `/Users/haosiyu/Library/LaunchAgents/com.hsy.shadowloop.plist:13` — 「<key>StandardOutPath</key><string>/Users/haosiyu/wide_shadow/loop.out</string>」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:34` — 「# ★ 2026-08-30 起三守护已 launchd 化(E-0829-B 修复, 重启+崩溃双自愈; 上行 nohup 命令仅作应急后备):」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「#   管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:37` — 「#   注意: 手动再起 nohup 实例会与 launchd 实例争锁(producer 自解, shell 守护无锁) —— 一律用 launchctl」
- **A reader could wrongly conclude:** A reader who learns the combo kill-PID rollback is stale may also distrust this producer restart procedure and fall back to a manual nohup start that the lock refuses.
- **Affects:** live_trading · **Severity reason:** Checked because the sibling combo-daemon rollback ('kill the PID') is stale under launchd; for the producer, the note's KeepAlive facts and restart verb match the plist and the RUNBOOK.
- **Proposed correction (exact text):** (无需改正; 2026-09-13 审计复核: ~/Library/LaunchAgents/com.hsy.shadowloop.plist L10/L12/L13 与 docs/RUNBOOK_wide_live_2026-08-22.md L34–37 一致; `launchctl list` 显示 com.hsy.shadowloop PID 10900、上次退出状态 −15, 即被 SIGTERM 后已由 KeepAlive 重生。) 可补一句: 「SuccessfulExit=false: 进程若以状态 0 正常退出, launchd 不会拉起」。
- **Confidence:** VERIFIED (plist and RUNBOOK read; `launchctl list` read-only) · **Quote re-verified at assembly:** exact

### M3-12 · P3 · DOC_STALE
- **Source:** `memory/turnover_shaping_ema_revalidated.md:3`
- **Resolution:** XREF AUDIT_EXEC STA-03 / CFG-07 — CROSS-REF: same external-book branch fact.
- **Quote:** 「最优可采格 = harvest EMA α=0.3(被 T1 关掉的那个): 净 +0.378→+0.668, 夏普 +0.58→+1.09, 五年全正。恢复需用户重裁 T1 张力」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:99` — 「"alpha": 0.05,」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
- **A reader could wrongly conclude:** A reader re-opens a "pending T1 ruling" or quotes the 08-10 splice numbers as current turnover economics.
- **Affects:** reporting · **Severity reason:** Historical grid note still says restoring the EMA awaits a ruling. It was restored the same day, deepened to α=0.05, and the executor EMA is not applied to today's external book.
- **Proposed correction (exact text):** [description 末尾追加] 【已执行: 08-10 164285b 恢复 α=0.3, 同日再改 0.05(deepsmooth); 08-22 起外部书不经执行器 EMA(anchor_loop.py L1664–1666)。本条数字属 08-10 旧内部书离线拼接口径】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-13 · P3 · DOC_STALE
- **Source:** `memory/deposit_kills_implicit_band.md:17`
- **Resolution:** XREF AUDIT_EXEC STA-03 — CROSS-REF: no_trade_band.json has had no writer since 2026-08-22 04:00Z — owned by AUDIT_EXEC STA-03.
- **Quote:** 「提案 PROPOSAL_neutral_band_2026-08-10(8e499dac)待用户裁定; 时序上须在 84 锚窗口起点之前部署(窗口内书变更⇒重起)。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:105` — 「"no_trade_band_w": 0.002,」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:26` — 「外部书分支均跳过中性带与 harvest EMA, `DEFAULT_BAND_BPS = 0.0` 且非测试代码无覆写(G-CODE PASS); `state/live/no_trade_band.json` 最后写于 A1787371250 = 08-22 04:00Z(外部书切换前最后一个内部书锚), 之后未写。」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
- **A reader could wrongly conclude:** A reader thinks the explicit neutral band is undecided, or that it currently shapes live trades.
- **Affects:** reporting · **Severity reason:** "Pending ruling" is out of date: the band was deployed 08-10 and has not been applied since the external book started on 08-22.
- **Proposed correction (exact text):** [L17 末尾追加] 【2026-09-13 状态: 08-10 已部署(book.json no_trade_band_w=0.002); 08-22 起外部书分支跳过中性带(anchor_loop.py L1664–1666), no_trade_band.json 自 08-22 04:00Z 未再写(T5b §0 Q3)。「隐性带随 NAV 反比缩水」机理仍有效, 数值属 4.3k/24.3k gross 旧书】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-19 · P3 · DOC_STALE
- **Source:** `memory/stop_line_read_a_different_quantity.md:8`
- **Quote:** 「— still open (A2), needs the user's ruling on the baseline semantics (start equity after deposits / transfer rebase).」
- **Superseding evidence:**
  - `STATE.md:146` — 「- **止损/风控**: 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)⟺ book_source=external 耦合; 看门狗 cond2 日亏 −4% flatten(口径 0aa6586)/ cond4 −25% 起始权益口径(57cb180);」
  - `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py:1665` — 「#   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the」
  - `STATE.md:7` — 「state.json 隔离到 `quarantine/state_20260913T120536Z_resumed.json`」
- **A reader could wrongly conclude:** A reader believes the −25% cond4 kill line still double-counts, and mistrusts or re-fixes a line that is already corrected.
- **Affects:** live_trading · **Severity reason:** cond4 was fixed the same day (57cb180, start-equity semantics per user ruling). The "EMA reset on resume" remark no longer applies to the external book.
- **Proposed correction (exact text):** [append after L8] **Update (2026-09-13 audit):** cond4 was fixed on 2026-08-21 in 57cb180 (user ruling: time-weighted cumulative equity return from start equity; transfer days use P&L/prev-day NAV), so it is no longer open (STATE §1: "cond4 −25% 起始权益口径(57cb180)"). Since 08-22 the executor applies no harvest EMA to the external book (anchor_loop.py L1664–1666), so "rebuild with no EMA discount" is moot; resume still quarantines state.json (e.g. 2026-09-13 12:05Z).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-29 · P3 · DOC_STALE
- **Source:** `memory/rank_centring_group_scale_trap.md:15`
- **Quote:** 「Impact once fixed: funding leg went from net +0.72%/yr (solo Sharpe 0.07) to **+8.48%/yr (Sharpe 0.83)** — *weakly positive, not a winner*.」
- **Superseding evidence:**
  - `docs/PREREG_leg_ablation_2026-08-26.md:43` — 「**去掉它整本书从 +1.31 变 −1.73, 夏普从 2.18 变 −2.49。funding 腿就是这本书**」
  - `multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md:12` — 「④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**」
- **A reader could wrongly conclude:** A reader under-weights the funding leg's importance from "not a winner".
- **Affects:** reporting · **Severity reason:** An era-specific characterisation (110-name engine) that reads as a general verdict on the funding leg, which is now most of the live book.
- **Proposed correction (exact text):** [append after L15] **Update (2026-09-13 audit):** "weakly positive, not a winner" is a 07-25 110-name-engine reading. In the wide-book era the funding leg is the book (PREREG_leg_ablation §4: removing it takes the book from +1.31 to −1.73 bps/anchor, Sharpe 2.18 → −2.49; CAL=simple but the direction is robust) and ≈65% of live notional (09-11). The rank-centring lesson itself stands.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-38 · P3 · DOC_STALE
- **Source:** `memory/feedback_anchor_inspection_once.md:7`
- **Quote:** 「复核轮 cron(91c4defe, `23 1,5,9,13,17,21`)已于 09-02 删除, 主模板 cron(3af9cb0e)保留。」
- **Superseding evidence:**
  - `STATE.md:166` — 「**会话 cron 重建(09-05 14:1xZ; /login 切换清空)**: 每锚深查 47686c87 · jpline 2h 538814c5 · combo 84 锚二读 48a8bb77(09-09); 模板 `docs/CRON_TEMPLATES_2026-09-04.md`。」
- **A reader could wrongly conclude:** A reader looks for or deletes cron 3af9cb0e and concludes the per-anchor deep check is missing or duplicated.
- **Affects:** reporting · **Severity reason:** Cron IDs are session-scoped and were rebuilt on 09-05, so the named main template ID no longer exists.
- **Proposed correction (exact text):** [L7 末尾追加] 【2026-09-13: cron ID 为会话级, 09-05 /login 切换后已重建(每锚深查 47686c87, STATE.md 记录); 3af9cb0e 不再存在。核查以 CronList 实测 + docs/CRON_TEMPLATES_2026-09-04.md 为准, 不按本条 ID】
- **Confidence:** VERIFIED (quote+receipt opened; the live CronList was not queried) · **Quote re-verified at assembly:** exact

### M3-39 · P3 · DOC_STALE
- **Source:** `memory/feedback_no_side_gpu_jobs.md:10`
- **Quote:** 「on the single jpline 3090, run NO side GPU jobs while a queue run is training.」
- **Superseding evidence:**
  - `CLAUDE.md:15` — 「GPU/LOB 在 pod2 `/workspace/`」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:56` — 「- **pod2**: 只用 CPU; `nvidia-smi` 前后 0 % / 2 MiB; 研究员暂停进程 333197 / 339489 不得触碰; GPU 冲突排队不抢。」
- **A reader could wrongly conclude:** A reader thinks the rule does not apply on pod2 and contends with training or touches the researcher's paused processes.
- **Affects:** future_retrain · **Severity reason:** The rule is scoped to the jpline 3090; GPU work now runs on pod2 under extra constraints (the independent researcher's paused PIDs, CPU-only research lines).
- **Proposed correction (exact text):** [append after L10] **Scope update (2026-09-13 audit):** GPU work now runs on pod2 (/workspace), not only on the jpline 3090; the rule applies to every shared GPU host. On pod2 also check nvidia-smi before and after, never touch the independent researcher's paused PIDs (e.g. 333197/339489), and queue rather than contend. "Hand to 0B" refers to a retired team role.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-40 · P3 · DOC_STALE
- **Source:** `memory/probe_flattened_book_positions.md:12`
- **Resolution:** XREF AUDIT_EXEC OPS-02 — CROSS-REF: the killed execution probe's launchd job is owned by AUDIT_EXEC OPS-02; the lead retired it 2026-09-13 14:20:08Z (b63a0144).
- **Quote:** 「**v2 started 2026-08-22 00:52Z** (launchd `com.hsy.execprobe2`, ~/exec_probe/v2: own-fills-only flatten, exclusion set 467 = live 140 ∪ wide 450 ∪ held, receipts, 102 tests; stop = touch ~/exec_probe/v2/KILL).」
- **Superseding evidence:**
  - `/Users/haosiyu/exec_probe/v2/probe.out:6` — 「KILL file present (['/Users/haosiyu/exec_probe/KILL', '/Users/haosiyu/exec_probe/v2/KILL']) — refusing to start.」
  - `/Users/haosiyu/exec_probe/v2/events.jsonl:53` — 「{"e": "killed", "ts": 1787377896.70642}」
- **A reader could wrongly conclude:** When a watchdog residual matches some quantity, a reader suspects the exec probe (per this note's triage rule) even though no co-account probe is running.
- **Affects:** live_trading · **Severity reason:** Presents exec-probe v2 as running; it was killed at 2026-08-22 05:51Z after one skipped round and refuses to start while the KILL files exist.
- **Proposed correction (exact text):** [append after L12] **Status (2026-09-13 audit):** probe v2 ran one round (04:20Z, skipped: live halted) and was KILLed at 2026-08-22 05:51:36Z; ~/exec_probe/KILL and ~/exec_probe/v2/KILL are present and launchd com.hsy.execprobe2 refuses to start ("KILL file present … refusing to start"). No co-account probe is trading. Any restart needs the README checklist and the user's word, and its exclusion set must use the live wide universe (the in-role 140 book is retired).
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-41 · P3 · DOC_STALE
- **Source:** `memory/dirty_caliber_effects_reverse_when_clean.md:81`
- **Quote:** 「**★ Open, and it is on the deployment path: does the clean model's stronger beta tilt get PAID?**」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:17` — 「**定性: 空头β保费的代价日**(受据: 该保费=历史利润 34%, β中性化毁 1/3 书 → 五臂全负 DO-NOT-RETRY)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。」
- **A reader could wrongly conclude:** A reader treats beta-tilt payment as an unresolved deployment blocker, or reuses the old answer for the current book.
- **Affects:** reporting · **Severity reason:** An item still marked "open, on the deployment path" was answered on 08-10 for the retired internal book, and that answer does not transfer to the live book.
- **Proposed correction (exact text):** [append after L89] **Update (2026-09-13 audit):** this "open" item was answered for the 08-10 internal book by RESULT_shortside_beta (7067113): the β tilt is a paid premium (≈34% of historical profit; five neutralisation arms negative). Both the question and that answer belong to the retired executor DL book; T8 (09-13) shows the related alt−BTC exposure does not transfer to the live A0 v4 book, so re-measure on the live book before reusing either reading.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-42 · P3 · DOC_STALE
- **Source:** `memory/anchors_jsonl_is_not_a_clean_series.md:3`
- **Resolution:** XREF AUDIT_EXEC LED-07 — CROSS-REF + QUALIFIED: AUDIT_EXEC LED-07 finds the LIVE anchors.jsonl is one row per anchor but still mixes halted rows, internal-era fields and capture-time timestamps ⇒ the correction must not say the live tree is simply 'clean'; it is clean of the DRY_RUN mixing this note describes, and separately unclean per LED-07.
- **Quote:** 「state/pilot_log/*/anchors.jsonl mixes real scheduled anchors with off-schedule manual and test runs, and its anchor_ts is a completion time in SECONDS ~40min after the nominal anchor — statistics computed over it without filtering are garbage」
- **Superseding evidence:**
  - `memory/anchors_jsonl_is_not_a_clean_series.md:26` — 「**The LIVE ledger lives at `state/live/pilot_log/` and IS a clean per-anchor series**」
  - `/Users/haosiyu/dl_quant_live/state/live/pilot_log/20260913/daily_nav.jsonl:4` — 「"nav_ts": 1789303549.183233」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/PREREG_T3_markout_curve_2026-09-13.md:57` — 「实测对应 2026-08-22 08Z 起(该锚偏移 25.8 min, 其后 23.0 → 24.0)」
- **A reader could wrongly conclude:** A reader skims the description and distrusts the clean live tree, or filters daily_nav rows by a :18 timestamp that no longer matches.
- **Affects:** reporting · **Severity reason:** The description still states the DRY_RUN-tree problem without the inline correction's scope, and the correction's "daily_nav :18 after each slot" timing no longer holds (nav rows now land ≈:39–:46).
- **Proposed correction (exact text):** [替换 description] "DRY_RUN tree state/pilot_log/*/anchors.jsonl mixes scheduled, manual and test runs (anchor_ts = completion time in seconds), so unfiltered statistics are garbage; the LIVE tree state/live/pilot_log/ is a clean per-anchor series (see correction)" [append to CORRECTION] Since 2026-08-22 the executor starts at E+23–24 min, so daily_nav rows land ≈:39–:46 after each 4h slot, not :18.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-43 · P3 · DOC_STALE
- **Source:** `memory/turnover_caliber_raw_vs_deployed.md:22`
- **Quote:** 「**How to apply:** 报 Sharpe 用原口径无妨; 只要一句话涉及**绝对成交额**, 必须换成 1453/1659。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T3/RESULT_T3_markout_curve_2026-09-13.md:97` — 「反转书每锚换手 1.33 × gross, 约为在役书(0.109)的 12 倍」
  - `/Users/haosiyu/dl_quant_live/config/book.json:153` — 「"book_source": "external",」
  - `STATE.md:4` — 「fills 1,777 / 228,081U / maker 0.686 / 佣金 67U」
- **A reader could wrongly conclude:** A reader computes fee tiers, volume or capacity for the live book from 1453/1659 instead of measured ledger turnover.
- **Affects:** reporting · **Severity reason:** The correction factors (1453/1659 ×/yr) belong to the 07-25 canonical 110-name engine; the live external book's turnover is a different quantity (≈0.109 per unit gross per anchor in ERA2).
- **Proposed correction (exact text):** [How to apply 末尾追加] 【2026-09-13: 1453/1659 只属 07-25 canonical 110 名引擎书; 在役外部 combo 书的绝对成交额按账本实测(fills/orders)或按在役书逐锚单位 gross 换手(ERA2 约 0.109/锚, T3 T-A3)× 部署 gross 计算, 不得套用本系数】
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-45 · P3 · DOC_STALE
- **Source:** `memory/panel_lookahead_betaadj_ret24.md:28`
- **Quote:** 「**Rulings:** the line is FROZEN with comment+assertion (a well-meaning causal fix must go red); only safe fix is retraining; live deployments unaffected (live never received the future term).」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/signal/panel_build.py:206` — 「mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "full")[:len(market)]」
  - `multi_asset/data/build_wide_dl.py:124` — 「mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "same")」
  - `/Users/haosiyu/dl_quant_live/config/book.json:153` — 「"book_source": "external",」
  - `CLAUDE.md:15` — 「**★ 面板默认值陷阱: `engine/panel_source.py` 默认=as-trained 脏面板 — 特征类实验必须显式传因果面板。**」
- **A reader could wrongly conclude:** A reader assumes the executor panel still carries the centred ch31 convolution, or reads "live never received the future term" as a guarantee about the current wide models; or overlooks that research experiments still default to the dirty panel.
- **Affects:** future_eval, reporting · **Severity reason:** The "frozen line ≡ live panel_build" ruling is historical. The executor panel builder was switched to trailing (causal) with the clean retrain and that internal DL book is retired, while the research builder still carries the centred leak by default.
- **Proposed correction (exact text):** [append after the Rulings line] **Update (2026-09-13 audit):** the identity `build_wide_dl.py:124 ≡ signal/panel_build.py:187` no longer holds. The executor builder now uses the trailing form (`~/dl_quant_live/signal/panel_build.py:206` `np.convolve(..., "full")[:len]`, shipped with the clean corrfund_causal_ac retrain on 2026-08-05), and that internal DL book has not traded since 2026-08-22 (book_source=external). The research builder `multi_asset/data/build_wide_dl.py:124` still uses the centred `"same"` form, and `engine/panel_source.py` still defaults to the as-trained dirty panel (CLAUDE.md), so feature experiments must pass the causal panel explicitly. "Live unaffected" is a statement about the retired executor heads, not about the current king/V2MAIN models.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M3-46 · P3 · DOC_STALE
- **Source:** `memory/feedback_no_multi_seed_2026_05_15.md:50`
- **Quote:** 「- **Above ±0.01 → cross-fold evidence decides** (no seed reruns needed).」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:58` — 「- **判决**: 双种子; UTC 日块自举; 结果表先写判据再填数; 每条线交 RESULT + SHA256SUMS; lead 复跑关键数字后才入 STATE。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:131` — 「2023 单年按种子分裂(s42 PARTIAL / s2027 DOES NOT FIT)」
  - `CLAUDE.md:23` — 「多种子先断言 self_sha256 同」
- **A reader could wrongly conclude:** A reader skips the second seed on a large-looking multi-asset effect, citing this rule, and misses a seed split like T1 H5's 2023 cell.
- **Affects:** future_eval, future_retrain · **Severity reason:** The 07-03 guardrail ("above ±0.01 cd, no seed reruns") belongs to the single-asset cd metric. Current multi-asset verdicts are frozen as two-seed, and recent verdicts have split by seed.
- **Proposed correction (exact text):** [2026-07-03 UPDATE 小节末尾追加] 【2026-09-13 适用域】本守卫按单资产 cd 指标定, 只属 y600/单资产时代; 宽书/多资产研究的现行纪律是「判决: 双种子 + UTC 日块自举」(uplift_r2 PROGRAM §3), 且已有按种子分裂的判决(T1 H5 2023: s42 PARTIAL / s2027 DOES NOT FIT); 多种子只作复现检查, 先断言 self_sha256 同(CLAUDE.md 复现纪律), 仍禁作集成。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-08 · P3 · DOC_STALE
- **Source:** `memory/cadence_8h_clears_cost_line.md:3`
- **Quote:** 「king cadence 4h→8h makes EVERY k clear the cost line (gap −30% to −96%) for ~10% book IC — so the 43.5%-IC sacrifice of dropping to k=0.2 is unnecessary.」
- **Superseding evidence:**
  - `memory/king_cadence_8h_live.md:42` — 「★ **更正 `cadence_8h_clears_cost_line`**: 那条说"每个 k 都清成本线"是 **1.9 bps 成本假设**下的; 按实测 3.115 **不清线**。」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:83` — 「节奏红利只在无 EMA/无带的原装置栈存在」
  - `docs/REVIEW_caliber_final_2026-09-04.md:90` — 「对交易所记账 **否**(08-22 SR 量化 −0.79 bps/锚)」
- **A reader could wrongly conclude:** A reader cites 'every k clears the cost line at 8h' as a cost-feasibility fact, although at the measured 3.115 bps cost it does not clear and the cadence benefit vanishes once EMA smoothing is present.
- **Affects:** future_eval · **Severity reason:** The headline was corrected in a different note (not inline) and its rig is retired, so the risk is a stale citation rather than a live decision.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「每个 k 在 8h 都清成本线」只在 1.9 bps 成本假设下成立; 按实测 3.115 bps 不清线(king_cadence_8h_live L42)。08-22 结论复审: 节奏红利只存在于无 EMA/无带的原装置栈, 深 EMA 在役栈上 king 4h 反超 8h(RESULT_conclusion_reaudit_simple_caliber L83)。本条装置为 in-role 引擎对数口径(对交易所记账偏 −0.79 bps/锚, REVIEW_caliber_final L90), 引擎与 in-role 书均已退役; 只保留「cadence 作用在比整形层高一层」与「行 0 = 午夜才能对齐相位」两条机制教训。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-10 · P3 · DOC_STALE
- **Source:** `memory/two_book_allocation_w2.md:14`
- **Quote:** 「**Status:** 传闻级 (series single-source); direction "blend > wide swap > in-role" holds;」
- **Superseding evidence:**
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:116` — 「W2/WA 已按简单口径重读(在役 0.43 / 宽 1.67, 配权 ≈ 全宽)」
  - `docs/DESIGN_optimization_path_2026-08-21.md:92` — 「最优 w_wide 0.9」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
- **A reader could wrongly conclude:** A reader cites 'blend 0.7 Sharpe 2.45 > wide swap > in-role' as a still-valid allocation result.
- **Affects:** reporting · **Severity reason:** The blend direction did not survive the 08-22 simple-caliber reread and the in-role book no longer exists, so the note only misleads historical citations.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「blend > wide swap > in-role」未存活: 简单口径重读后在役 in-role 0.43 / 宽 1.67, 最优配权 ≈ 全宽(w_wide 0.9; RESULT_conclusion_reaudit_simple_caliber L116, DESIGN_optimization_path L92)。in-role 书 2026-08-22 03:15Z 已退役(`~/dl_quant_live/config/book.json` _book_source_note), 两书配权问题已不存在。本条 W2 数字(blend 2.45 等)是 08-21 仪器读数, 不是现行书水平; 现行水平见 v4 口径 A0。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-12 · P3 · DOC_STALE
- **Source:** `memory/pilot_prereq_stack.md:95`
- **Quote:** 「任何 pilot 相关读数只能来自 `pilot_metrics.py` (改脚本=改协议; 当前 hash `e2f10848…`, 签署后冻结)」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:369` — 「metrics_freeze: FROZEN_MATCH sha=5ac7b16d0f97f2f8」
  - `/Users/haosiyu/dl_quant_live/live/pilot_metrics.py:4` — 「its hash recorded: **editing this script after signing = editing the protocol.**」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
- **A reader could wrongly conclude:** A reader checks metrics integrity against e2f10848 and concludes the protocol was broken, or reads pilot gates from the research-repo engine/live copy.
- **Affects:** reporting · **Severity reason:** The pinned hash and the engine/live location belong to the 07-25 research-repo pilot; the live executor's frozen metrics file is ~/dl_quant_live/live/pilot_metrics.py with sha 5ac7b16d.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条路径与 hash 属 07-25 研究仓 `engine/live/` pilot。现行实盘执行器在 `~/dl_quant_live`, 冻结的指标脚本为 `~/dl_quant_live/live/pilot_metrics.py`, 当前冻结校验 `metrics_freeze: FROZEN_MATCH sha=5ac7b16d0f97f2f8`(AUDIT_EXEC EXE-08); `e2f10848…` 不再是比对基准。in-role 内部书已于 2026-08-22 03:15Z 退役, 本条三轨/shadow 相关读数只作历史。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-13 · P3 · DOC_STALE
- **Source:** `memory/shadow_three_tracks_prereg.md:11`
- **Quote:** 「**2026-07-25 (0B)。** `engine/live/` 下三条轨并行, 都是**加法 + run_daily.sh 非致命步骤**, 失败不影响 champion 主链。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不经 compose_book/风险预算/EMA/中性带」
- **A reader could wrongly conclude:** A reader looks for live challenger/fixfunding evidence or assumes these 60-day clocks are still running.
- **Affects:** reporting · **Severity reason:** Present-tense description of champion/challenger/fixfunding shadow tracks for the in-role book, which was retired on 2026-08-22.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 三条影子轨服务的 in-role 内部书(king/s2/funding/size)已于 2026-08-22 03:15Z 退役, 现役为 combo 外部书(`~/dl_quant_live/config/book.json` _book_source_note)。本条轨与判据只作历史; 「影子切片才是证据、冻结面板重述不是证据」的方法论保留。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-14 · P3 · DOC_STALE
- **Source:** `memory/research_branch_protocol.md:16 (+2 more)`
- **Quote:** 「1. **No git worktree.** It isolates local repo files — the least likely thing to collide. What
   actually collides is outside the repo: `~/dl_quant_live` (launchd run dir, 落盘即上线), the
   single server working copy (`sync_to_server.sh --delete` can wipe engine/), the single RTX 3090」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `docs/MILESTONE_2026-08-26.md:101` — 「| pod2(RTX PRO 4500) | GPU 训练 + LOB |」
  - `STATE.md:98` — 「worktree `/Users/haosiyu/Desktop/quant_research_wt/b0a573a1`」
  - `STATE.md:264` — 「协作协议(worktree/权限边界/建议切入点)」
- **A reader could wrongly conclude:** A reader refuses worktree isolation for a new research fork or assumes jpline sync/GPU contention constraints still apply.
- **Affects:** reporting · **Severity reason:** The infrastructure premises (single jpline working copy, single RTX 3090) are gone and the project now uses git worktrees for independent review.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条前提已变: jpline 自 09-04 起不可达, GPU 在 pod2(RTX PRO 4500); 独立复审已常规使用 git worktree(如 `quant_research_wt/b0a573a1`、`.claude/worktrees/codex-independent-20260907`, ONBOARDING 协作协议)。「worktree 不隔离仓外共享资源(`~/dl_quant_live` 落盘即上线、launchd、GPU)」的告诫仍成立, 但「不用 worktree」不是现行规则。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M4-18 · P3 · DOC_STALE
- **Source:** `memory/takerflow_family_zero_admissions.md:31`
- **Quote:** 「**凡是抬毛额的改动都靠抬换手, 在这个信噪比下换手总是吃得更多。**」
- **Superseding evidence:**
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:58` — 「不变(不录取; "换手吃光"在深 EMA 栈改写为"无显著增量")」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_trackD_sleeves_v4_2026-09-11.md:129` — 「**轴仍未关闭**(这是第二次 NULL-ish 读数, 不是第三次独立 NULL)」
- **A reader could wrongly conclude:** A reader rejects any gross-raising change a priori as turnover-killed, or treats the order-flow axis as closed (MEMORY index lists it under DNR).
- **Affects:** future_eval · **Severity reason:** The turnover-always-wins generalisation was measured on the no-EMA stack; on the deep-EMA stack the F3 penalty disappears, and the axis is still open per v4 Track D.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「换手总是吃得更多」是无 EMA 栈读数; 08-22 复审在深 EMA 在役栈上 F3 换手红利消失, 改写为「无显著增量」(RESULT_conclusion_reaudit_simple_caliber L58)。v4 Track D 中 `f_tbf_24h` 站立书 Sharpe 1.12、corr(A0) −0.007, 仍不录取, 「轴仍未关闭」(RESULT_trackD_sleeves_v4 §8)。成交流轴不是 DNR。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-19 · P3 · DOC_STALE
- **Source:** `memory/new_info_campaign_round1_2026_08_11.md:11`
- **Quote:** 「**但 S2 净额剂量反向判死**(w.05 −0.010 / w.10 −0.033)。」
- **Superseding evidence:**
  - `docs/DESIGN_optimization_path_2026-08-21.md:89` — 「**装置缺陷**: 旧 RM/W4 S2 把候选当 dvol30 传入 compose_book(size_dvol_factor −log 把 51.6% 值置零); 忠实路径方向不变, 旧数字作废标注。」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:57` — 「原数是变换过的腿, 见 §3.8」
- **A reader could wrongly conclude:** A reader quotes -0.010/-0.033 as the RM1 book effect.
- **Affects:** reporting · **Severity reason:** The verdict survives but the quoted S2 numbers came from a transformed leg and were voided.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** RM1 S2 原数(w.05 −0.010 / w.10 −0.033)来自装置缺陷: 候选被当 dvol30 传入 compose_book, size_dvol_factor 把 51.6% 值置零 ⇒ 旧数字作废; 忠实路径八格全 fail, 判决方向不变(DESIGN_optimization_path L89; RESULT_conclusion_reaudit_simple_caliber L57)。判官副本已在 git `multi_asset/exports/eda/probes/judges_2026-08-11/`(jpline 自 09-04 不可达)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-20 · P3 · DOC_STALE
- **Source:** `memory/tree_dl_division_of_labor.md:21`
- **Quote:** 「① king 在役配置不动(其价值=IC 住在慢稳成分, 可变现——这是定性结论+1.46 夏普受据)」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/MILESTONE_2026-08-26.md:38` — 「- F10 阶梯家族(R1/R1CTX/RECB/T/PLE/V3FULL/L3.2 conformer)全部不敌朴素 V2MAIN(REVIEW_f10_blend_deployment)。」
- **A reader could wrongly conclude:** A reader applies 'do not touch king config (Sharpe 1.46)' to the current wide LGBM king.
- **Affects:** future_eval · **Severity reason:** 'king' here is the retired in-role conformer and 1.46 is its book Sharpe; today 'king' means the wide LGBM leg, so the instruction is ambiguous.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 本条「king」「在役书夏普 1.46」指 in-role 110 名 conformer king 与其书(2026-08-22 已退役); 现役「king」= 宽宇宙 LGBM 腿, 另有 V2MAIN DL 腿。本条不约束现役 king 配置。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-21 · P3 · DOC_STALE
- **Source:** `memory/regime_stability_is_horizon_property.md:28`
- **Quote:** 「在役部署头 = YR4(harness 硬断言 `h0 must stay YR4`)。」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/REVIEW_caliber_final_2026-09-04.md:55` — 「| DL 目标 y4s(`dlw_targets.npz`) |」
  - `docs/MILESTONE_2026-08-26.md:38` — 「- F10 阶梯家族(R1/R1CTX/RECB/T/PLE/V3FULL/L3.2 conformer)全部不敌朴素 V2MAIN(REVIEW_f10_blend_deployment)。」
- **A reader could wrongly conclude:** A reader assumes the live DL head is YR4 when designing horizon or target experiments.
- **Affects:** future_retrain · **Severity reason:** Describes the deployed head of the retired in-role DL; the live DL leg is V2MAIN trained on y4s book loss.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「在役部署头 = YR4」属已退役 in-role DL(08-22)。现役 DL 腿 = V2MAIN(F10 书损失, 目标 y4s = Π(1+r5)−1, REVIEW_caliber_final L55); 视界结论须在现役目标上重测后才可迁移。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-23 · P3 · DOC_STALE
- **Source:** `memory/sharpe_461_does_not_survive_clean.md:40`
- **Quote:** 「**And the same number is the incumbent's own grade.** Live runs that dirty generation, so 0.93/−0.43」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:86` — 「| 引擎正典 0.93(干净替身) | 0.93 | 对数 engine | 同 pnl 行(Σw·Y4)未跑 engine | 重表 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12` — 「**全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举)」
- **A reader could wrongly conclude:** A reader treats 0.93/-0.43 as the grade of what is trading now.
- **Affects:** reporting · **Severity reason:** The live model named here was swapped and the in-role book retired; 0.93/-0.43 are log-caliber engine numbers marked for re-tabling. The headline (no clean Sharpe>=5 precedent) still holds against v4 1.29.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「Live runs that dirty generation」已过时: 08-05 换装后 in-role 书于 2026-08-22 退役, 现役为 combo。0.93/−0.43 为对数口径引擎读数, 08-22 复审标「重表」未重跑(RESULT_conclusion_reaudit_simple_caliber L86)。头条「Sharpe ≥ 5 无干净先例」对照现行正典仍成立: v4 口径 A0 全周期 1.29 [0.32, 2.28](PROGRAM_uplift_r2 L9)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-24 · P3 · DOC_STALE
- **Source:** `memory/sharpe5_has_no_clean_precedent.md:37`
- **Quote:** 「**It does NOT argue against the model swap.** Live runs *that same dirty generation*」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `multi_asset/exports/eda/RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md:86` — 「| 引擎正典 0.93(干净替身) | 0.93 | 对数 engine | 同 pnl 行(Σw·Y4)未跑 engine | 重表 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:12` — 「**全周期诚实夏普 1.29 [0.32, 2.28]**(v4 口径, 日块自举)」
- **A reader could wrongly conclude:** A reader believes the dirty in-role generation is still trading.
- **Affects:** reporting · **Severity reason:** Same stale present-tense live claim as sharpe_461_does_not_survive_clean.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 同 sharpe_461_does_not_survive_clean: in-role 书 2026-08-22 已退役, 0.93/−0.43 为对数口径引擎读数(复审标「重表」); 头条「Sharpe ≥ 5 无干净先例」对照 v4 A0 全周期 1.29 [0.32, 2.28] 仍成立。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-25 · P3 · DOC_STALE
- **Source:** `memory/hybrid_forest_admission.md:13`
- **Quote:** 「**证据链**(可复现, 脚本 jpline w3lane/jp_hybrid.py + 特征缓存 hyb_fea47.npy)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `multi_asset/exports/pod_archive_2026-08-15/MANIFEST.md:8` — 「- jpline w3lane 已另有副本: fast_film2 preds/k2_k2/k2_k3a preds/树 preds/矿分 preds(双备份)」
- **A reader could wrongly conclude:** A reader believes the admission can be re-derived today.
- **Affects:** future_eval · **Severity reason:** 'Reproducible' points to a script and feature cache that exist only on jpline, unreachable since 09-04.
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** 「可复现」依赖的 `jp_hybrid.py` 与 `hyb_fea47.npy` 只在 jpline(自 09-04 不可达), 本仓 git 无该脚本(git ls-files 无 jp_hybrid); 在 jpline 恢复或从 pod 撤离档找到副本前按「不可复现」引用。
- **Confidence:** INFERRED (jpline unreachability verified; absence of a copy checked only via git ls-files and the 08-15 pod archive manifest) · **Quote re-verified at assembly:** exact

### M4-26 · P3 · DOC_STALE
- **Source:** `memory/metric_discipline_spearman_primary.md:13`
- **Quote:** 「- CLAUDE.md "Metric Discipline" section mirrors it.」
- **Superseding evidence:**
  - `CLAUDE.md:27` — 「## Metric Discipline(全文 MILESTONE_2026-08-11 §2)」
  - `CLAUDE.md:28` — 「**收益口径绑定面板文件, 不绑定变量名(E-0904-F)**」
- **A reader could wrongly conclude:** A reader applies single-asset h=180 pass bars or ignores the panel-bound caliber rules because this note says CLAUDE.md mirrors the old doc.
- **Affects:** reporting · **Severity reason:** CLAUDE.md Metric Discipline now points to MILESTONE_2026-08-11 §2 and adds caliber-binding rules; docs/METRIC_DISCIPLINE.md is the single-asset V4 spec (Pearson ≥0.12 at h=180).
- **Proposed correction (exact text):** > ⚠ **2026-09-13 更正:** CLAUDE.md「Metric Discipline」现指向 MILESTONE_2026-08-11 §2, 并新增收益口径绑定面板文件(E-0904-F)、口径三层、排序≠净额; `docs/METRIC_DISCIPLINE.md` 只是单资产 V4(h=180, Pearson ≥ 0.12)规格, 不是多资产现行规则。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-30 · P3 · DOC_STALE
- **Source:** `memory/MEMORY.md:108`
- **Quote:** 「- V4/V5/单资产时代(04..05): `v4_*` `v5*` `single_asset_*` `y600_*`; 结论已入 07-06 终版文档」
- **Superseding evidence:**
  - `memory/MEMORY.md:22` — 「(v4_monthly_chain_driver_2026_09_12.md)」
  - `memory/MEMORY.md:34` — 「(v4_chain_retrain_2026_09_09.md)」
- **A reader could wrongly conclude:** A reader skips v4_chain_retrain_2026_09_09 / v4_monthly_chain_driver_2026_09_12 as closed single-asset history.
- **Affects:** future_retrain, reporting · **Severity reason:** The closed-era glob `v4_*` also matches the current September v4-caliber chain notes, so the index labels live retrain notes as a concluded single-asset era.
- **Proposed correction (exact text):** - V4/V5/单资产时代(04..05): `v4_3fold_*` `v4_design_reference` `v4_overnight_*` `v4_y300_*` `v5*` `single_asset_*` `y600_*`; 结论已入 07-06 终版文档(⚠ `v4_chain_retrain_2026_09_09` / `v4_monthly_chain_driver_2026_09_12` 是 9 月 v4 口径链, 属在役, 不在此列)
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 96->108)

### M4-31 · P3 · DOC_STALE
- **Source:** `memory/MEMORY.md:104`
- **Quote:** 「[残差第四腿关](wide_book_carry_correction.md)」
- **Superseding evidence:**
  - `memory/wide_book_carry_correction.md:3` — 「carry记账/2 bug隐藏0.53bps/锚资金费净支付」
  - `docs/DESIGN_optimization_path_2026-08-21.md:153` — 「残差第四腿」
- **A reader could wrongly conclude:** A reader looking for the residual-fourth-leg receipt lands on the carry note and either cites it wrongly or concludes the DNR has no receipt.
- **Affects:** reporting · **Severity reason:** The DNR index link text names a closure (residual fourth leg) that the linked note does not contain; the note is the carry-accounting correction.
- **Proposed correction (exact text):** [carry记账/2 修正(宽书头条 3.59→2.42, 已被 v4 1.29 取代)](wide_book_carry_correction.md) · 残差第四腿关: 受据见 MILESTONE_2026-08-26 §2 / DESIGN_optimization_path_2026-08-21 L153(需补独立记忆条)
- **Confidence:** INFERRED (link-text/content mismatch verified; the residual-fourth-leg receipt itself was not opened) · **Quote re-verified at assembly:** exact (line moved 92->104)

### M4-36 · P3 · DOC_STALE
- **Source:** `memory/dl_ceiling_solo_rho_catch22.md:18`
- **Quote:** 「③ 15 臂判官与预测件在 pod /workspace(exports_train/arm*_pred_*.npy), 装置与结论同寿命」
- **Superseding evidence:**
  - `STATE.md:120` — 「pod 撤离收口: 不可再生小件已双份」
  - `docs/MILESTONE_2026-08-26.md:102` — 「| 磁盘档 | 旧 pod 撤离 | `multi_asset/exports/pod_archive_2026-08-15/`(151MB, 不入 git, 有 SHA256SUMS) |」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
- **A reader could wrongly conclude:** A reader assumes the 15-arm judge and arm predictions can be re-read today to re-derive the ceiling numbers.
- **Affects:** future_eval · **Severity reason:** The judge and prediction artifacts this note pins live on the old pod, which was evacuated 2026-08-26 with only small items double-copied to jpline (unreachable since 09-04) and a 151 MB disk archive that is not in git.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(STATE 2026-08-26 09:4xZ pod 撤离 + MILESTONE §6):** 本条钉的「pod /workspace(exports_train/arm*_pred_*.npy)」是**旧 pod**; 该实例 08-26 已撤离(不可再生小件双份到 jpline `pod2_evac_2026-08-26/small/`, 其余入磁盘档 `multi_asset/exports/pod_archive_2026-08-15/` 151MB, **不入 git**), 而 jpline 自 09-04 起不可达。⇒ 「装置与结论同寿命」在本条上**未兑现**: 引用 15 臂读数前须先在磁盘档/pod2 找到副本, 否则按「不可复现」引用。现役 GPU 机是 pod2(`/workspace/`)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-40 · P3 · DOC_STALE
- **Source:** `memory/residual_regime_survival_peaks_at_y12.md:40 (+1 more)`
- **Quote:** 「**为什么重要**: 实盘坏掉的量**就是残差在坏窗里的增值**(STATE §0-octies: 残差全期 +0.091 /
最近 6 锚 −0.008, 而风格 +0.085 还活着)。**在役目标 y4 恰好是残差最脆的那个视界。**」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/MILESTONE_2026-08-26.md:7` — 「king 腿 55/45 混入 V2MAIN(可微书损失 DL)」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:131` — 「**但书在每个状态都是 98–99% fund 腿, 席位根本没有加码空间**」
- **A reader could wrongly conclude:** A reader believes the live book's P&L is driven by a DL residual that decays in bad regimes, and re-opens the y12 horizon as a live fix.
- **Affects:** future_eval, reporting · **Severity reason:** The 'what is broken in live' premise points at STATE §0-octies and at the in-role DL book's residual-vs-style decomposition; that book was retired 2026-08-22, the STATE section no longer exists, and today's book is 98-99% fund leg in every state.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(dl_quant_live/config/book.json `_book_source_note` + MILESTONE_2026-08-26 §1 + PROGRAM_uplift_r2 更正 2):** 本段的实盘诊断针对 in-role DL 书(king/s2/funding → compose_book), 该形态 **2026-08-22 03:15Z 已退役**, 引用的 `STATE §0-octies` 在现行 STATE.md 中已不存在。现役 combo 书 = fund 腿 + king LGBM + V2MAIN, 且实测「书在每个状态都是 98–99% fund 腿」⇒ 「残差在坏窗里的增值 = 实盘坏掉的量」不描述现役书, 「在役目标 y4」也不再指本条的 DL 头。y12 视界结论仍只在其自身记账口径内成立(见本文头条更正)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M4-41 · P3 · DOC_STALE
- **Source:** `memory/substratum_noise_needs_own_calibration.md:35`
- **Quote:** 「视界表(y12 vs y4 = +0.0060, 8.6 SE)不受影响。」
- **Superseding evidence:**
  - `memory/residual_regime_survival_peaks_at_y12.md:11` — 「> ## ★★★ 头条更正 (2026-08-09, 同日): **下表只在【每个视界自己的记账口径】内成立, 不可跨口径解读。**」
  - `memory/residual_regime_survival_peaks_at_y12.md:44` — 「- 按**总分 IC**: y12 的 +0.0060 优势 **85% 长在风格层**(风格 +0.0087 / 残差 +0.0017)」
  - `memory/residual_regime_survival_peaks_at_y12.md:17` — 「> **6.5 SE 的优势完全消失**(残Q4 三元组重叠), 残差反而低 −0.0043。」
- **A reader could wrongly conclude:** A reader cites 'y12 beats y4 by +0.0060 at 8.6 SE' as a surviving horizon effect and proposes a y12 target for the live 4h book.
- **Affects:** future_eval · **Severity reason:** The +0.0060 / 8.6 SE horizon advantage is exempted from the recalibration here, but the next-day receipt shows it is 85% style (duplicate capacity) and disappears once scored in the 4h realisation caliber.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(同族受据 residual_regime_survival_peaks_at_y12 头条更正, 2026-08-09):** 「视界表不受影响」只对**种子噪声再标定**这件事成立(该表确实不是被单种子噪声制造的)。它**不**免疫口径问题: 同族次日受据写明「下表只在【每个视界自己的记账口径】内成立, 不可跨口径解读」, 且 y12 的 +0.0060 优势 **85% 长在风格层**(风格 +0.0087 / 残差 +0.0017 = 重复容量), 换成书实际兑现的 YR4/CL4 尺子后 6.5 SE 的残差优势完全消失、残差反低 −0.0043。⇒ 引用该视界表必须同时声明记账口径。本条的三条标定规则不受影响。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-42 · P3 · DOC_STALE
- **Source:** `memory/lam_orth_dose_response_flattened_horizon.md:33`
- **Quote:** 「JSON 产物只记录 xattn 与 n_params, **不记录 lam_orth 与面板路径** ⇒ 必须回查启动脚本。」
- **Superseding evidence:**
  - `docs/DESIGN_v4_monthly_chain_2026-09-12.md:154` — 「② **完整键集**——`seed/best_ep_rule/best_ep_kept/env_given/inputs/inputs_sha256/pt/pt_sha256/self_sha256`」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:86` — 「外加侧车 `self_sha256` == 本次调度的 `pod_f10_refit_v4.py`」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
- **A reader could wrongly conclude:** A reader assumes current v4-chain artifacts also fail to record their config and goes hunting launch scripts, or concludes the 'artifact self-reports its config' discipline was never implemented.
- **Affects:** future_retrain · **Severity reason:** The 'artifacts do not record the config' debt describes the retired train_wide_harness JSON; the v4 monthly chain now writes a sidecar with env_given, input paths, recomputed input/weight shas and the trainer's own self_sha256, and a pre-gate refuses if any key is missing.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(DESIGN_v4_monthly_chain_2026-09-12 §refit 侧车 + RUNBOOK_monthly_retrain_2026-10 L86):** 「JSON 产物不记录 lam_orth 与面板路径」说的是已退役的 `train_wide_harness` 产物(in-role 书 2026-08-22 退役)。v4 月度链已补上这笔欠账: refit 侧车必须含 `seed/best_ep_rule/best_ep_kept/env_given/inputs/inputs_sha256/pt/pt_sha256/self_sha256` 完整键集(**缺一即拒**), 输入与权重的 sha **当场重算**, 且侧车 `self_sha256` 必须等于本次调度的训练脚本 ⇒ 对 v4 产物应直接读侧车而非回查启动脚本。本条「引用跨臂比较前先问 lam_orth / xattn / 面板 SHA」的纪律保留(对 harness 时代产物仍必须回查)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-44 · P3 · VERIFIED_CURRENT
- **Source:** `memory/benchmark_0466_was_dirty_panel.md:36`
- **Quote:** 「engine/panel_source.py 默认 PANEL=wide_dl_full.npz(脏面板)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md:33` — 「| `engine/panel_source.py` 的**默认**面板 | 是 as-trained **脏面板**; 特征类实验必须显式传因果面板 |」
  - `CLAUDE.md:15` — 「**★ 面板默认值陷阱: `engine/panel_source.py` 默认=as-trained 脏面板 — 特征类实验必须显式传因果面板。**」
- **A reader could wrongly conclude:** A reader assumes a 2026-08-11 default-value warning was long since fixed and runs a feature experiment on the default panel, re-importing the betaadj_ret24 11h lookahead.
- **Affects:** future_eval · **Severity reason:** Checked against the v4 caliber pin and the current CLAUDE.md banner: the default panel is still the as-trained dirty panel, so this 08-11 warning is live, not stale.
- **Proposed correction (exact text):** > ✅ **2026-09-16 复核(CALIBER_PIN_v4_2026-09-11 §2 + CLAUDE.md 项目身份):** 本段仍然成立且仍是在役规则 —— `engine/panel_source.py` 的**默认**面板至今仍是 as-trained **脏面板**(脏面板故意保留, 归因/复现需要), 「特征类实验必须显式传因果面板」已写进 v4 口径锁与 CLAUDE.md 横幅。无需修改。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-45 · P3 · VERIFIED_CURRENT
- **Source:** `memory/ma_v2_1h_ls_nogo.md:19`
- **Quote:** 「**Implication:** escalating to 2h/4h with the SAME fast features won't help (mechanism #3) — the horizon isn't the bottleneck, feature decay is.」
- **Superseding evidence:**
  - `CLAUDE.md:13` — 「**Binance USDT-perp 宽宇宙中频市场中性**: 宇宙 450 币, 4h 锚(00/04/08/12/16/20Z), maker-only」
  - `docs/MILESTONE_2026-08-26.md:29` — 「**fund 腿 = 书本体**」
  - `docs/MILESTONE_2026-08-26.md:7` — 「king 腿 55/45 混入 V2MAIN(可微书损失 DL)」
- **A reader could wrongly conclude:** A reader sees a profitable live 4h maker-only book and concludes the 1h/4h NO-GO was refuted, i.e. that fast 10-min features do become tradeable once the target horizon is stretched.
- **Affects:** future_eval · **Severity reason:** The live 4h book does not contradict this NO-GO: it is built on slow, persistent funding state (lever (a) of this very note), not on the 10-min microstructure features whose decay drove the verdict.
- **Proposed correction (exact text):** > ✅ **2026-09-16 scope check (CLAUDE.md 项目身份 + MILESTONE_2026-08-26 §1/§2):** still correct, and not refuted by the live book. The deployed book is a 4h maker-only cross-sectional book, but its body is the funding leg (a slow, persistent state variable) plus king LGBM / V2MAIN on slow features — that is lever (a) of this note ('SLOWER / more-persistent features'), not the 10-min microstructure stack whose ~50%/180s decay produced the NO-GO. Nothing here licenses re-testing the fast 10-min feature set at 2h/4h.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-46 · P3 · VERIFIED_CURRENT
- **Source:** `memory/infra_research_repo_on_icloud_desktop_trustctime.md:10`
- **Quote:** 「**Fix applied (lead, 2026-09-13 08:50Z):** `git config --local core.trustctime false` in the research repo; the same commit then took 3.7 s.」
- **Superseding evidence:**
  - `.git/config:8` — 「trustctime = false」
  - `STATE.md:14` — 「研究仓在 iCloud 桌面, 05:38Z 一次 ctime 批改使 git 提交逐文件重哈希卡锁 11 分钟 ⇒ 设 `core.trustctime=false`(仓内, 可撤), 提交 3.7 s」
- **A reader could wrongly conclude:** A reader assumes the setting was reverted (it is explicitly documented as reversible) and re-diagnoses a slow commit as an iCloud ctime storm, or re-applies the config.
- **Affects:** reporting · **Severity reason:** Re-checked on 2026-09-16: the repo-local setting is still present, so the note's fix and its caveats (mtime+size still detect content changes) remain in force.
- **Proposed correction (exact text):** > ✅ **2026-09-16 复核:** 仍在位 —— 研究仓 `.git/config` 第 8 行仍为 `trustctime = false`(与 STATE 2026-09-13 08:5xZ 基建条一致)。本条的三条附带规则(空哈希 e3b0c442… 无效、显式 pathspec 提交、锚窗 HH:20–45 不拷大树)同样仍然有效。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-48 · P3 · DOC_STALE
- **Source:** `memory/server_only_code_rsync_delete_risk.md:30`
- **Quote:** 「- 已把 tarball 拉到**机外**(本地), 两侧 sha256 一致 ⇒ 两台机器两份。」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `STATE.md:182` — 「**jpline 重连定时已按用户字停止(09-06 05:4xZ)。**」
- **A reader could wrongly conclude:** A reader counts the jpline backup (`_masv2_code_backup_2026-07-25/`) as a live second copy, or plans to restore pilot-stack code from it.
- **Affects:** future_eval · **Severity reason:** The second of the 'two machines, two copies' is jpline, unreachable since 2026-09-04 with reconnect attempts stopped by the user on 09-06, so the off-machine guarantee is now a single local copy.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(PROGRAM_uplift_r3_2026-09-13 §数据 + STATE 2026-09-06 05:4xZ):** 「两台机器两份」已不成立 —— jpline 自 **2026-09-04 起不可达**, 每 2 小时重连定时已按用户字于 09-06 停止 ⇒ 备份 `/mnt/storage/private/work_hsy/_masv2_code_backup_2026-07-25/` 与 jpline 上的一切目前**不可取**, 只剩本地一份 + git 历史。`sync_to_server.sh`(rsync --delete)仍在仓内且目标机不可达, 「别跑」继续有效。本条的治理原则(代码/规格在本地 git、server 只放产物、备份必须在被保护对象之外、测守卫不用真实爆炸)不受影响。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-49 · P3 · DOC_STALE
- **Source:** `memory/panel_ref_blind_to_ch31_axis.md:39`
- **Quote:** 「fix = trainer writes the SHA at training time (`prodfold_panel_sha_at_train_time`).」
- **Superseding evidence:**
  - `docs/DESIGN_v4_monthly_chain_2026-09-12.md:154` — 「④ **实际工件 sha**——`.pt` 与每个声明输入都**当场重算**并比对, 记录值为空本身就是拒绝理由」
  - `docs/RUNBOOK_monthly_retrain_2026-10.md:86` — 「外加侧车 `self_sha256` == 本次调度的 `pod_f10_refit_v4.py`」
- **A reader could wrongly conclude:** A reader believes run provenance is still path-based and retrospective everywhere, and either re-invents the fix or distrusts v4-chain provenance.
- **Affects:** future_retrain · **Severity reason:** The 'real fix' this note leaves open is implemented in the v4 monthly chain: the refit sidecar declares its inputs and the pre-gate recomputes each input's and the weight file's sha on the spot, plus the trainer's own self_sha256.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 update (DESIGN_v4_monthly_chain_2026-09-12 §refit sidecar + RUNBOOK_monthly_retrain_2026-10 L86):** the 'real fix' is now implemented on the live retrain path. The v4 monthly chain's refit sidecar declares its four inputs and the weight file, and the pre-gate (before arms dispatch) recomputes every declared input's and the `.pt`'s sha **on the spot** (an empty recorded value is itself a rejection), checks the expected month-contract paths (a byte-identical copy under another tree is rejected) and requires the sidecar's `self_sha256` to equal the dispatching trainer. The finding itself still stands for the in-role artifacts: `panel_ref.npz` discriminates funding but not the ch31 lookahead axis, so it can never answer 'was this model trained without lookahead'.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-50 · P3 · DOC_STALE
- **Source:** `memory/vs_infer_handrolled_forward_loop.md:19 (+1 more)`
- **Quote:** 「The s2 leg carries ~80% of the book at k=0.2 —
> the configuration the "clean book is net-positive" headline rests on.」
- **Superseding evidence:**
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「'internal' = 今天的书(king/s2/funding → compose_book → EMA → 带)」
  - `/Users/haosiyu/dl_quant_live/config/book.json:154` — 「不回 internal(在役已 08-22 03:15Z 退役)」
  - `docs/MILESTONE_2026-08-26.md:7` — 「king 腿 55/45 混入 V2MAIN(可微书损失 DL)」
- **A reader could wrongly conclude:** A reader treats the s2 densification fork (certified-and-sparse vs dense-and-uncertified) as a live book risk, or believes the 'clean book is net-positive' headline still rests on a leg that is in production.
- **Affects:** future_eval · **Severity reason:** The s2 leg only existed in the internal (in-role) book, which was retired 2026-08-22; the live combo book has no s2 leg, so the '80% of the book' framing and the uncertified 6x densification no longer describe anything deployed.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 scope correction (dl_quant_live/config/book.json `_book_source_note` + MILESTONE_2026-08-26 §1):** the s2 leg lived only in the **internal** book (king/s2/funding → compose_book → EMA → band), which was retired on 2026-08-22 03:15Z and is explicitly never rolled back to. The live book is the wide combo (fund leg + king LGBM + V2MAIN), so '~80% of the book at k=0.2' and the certified-sparse vs dense-uncertified fork are historical, not live exposures. What stays reusable: a second implementation is only right if something compares it to the first every run; a fidelity gate must run on the training device (CPU 3.5e-4 vs GPU 1.2e-7); and the mask is a model input, so densifying changes the scores.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M4-51 · P3 · DOC_STALE
- **Source:** `memory/perf_batch_1024_lr_sqrt.md:15`
- **Quote:** 「VRAM at batch 1024 ≈ 15.7 GB of 24 GB (65%) with this architecture — still headroom, but a bump to 2048 would need a check.」
- **Superseding evidence:**
  - `docs/ONBOARDING_independent_researcher_2026-09-06.md:75` — 「| **pod2**(RTX PRO 4500) | GPU 训练 + LOB |」
  - `STATE.md:14` — 「pod2 容器内存上限 61 GB(非 free 显示的 247 GB)」
  - `docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md:3` — 「**创建:** 2026-07-06 | **状态:** final (阶段性完成,收口)」
- **A reader could wrongly conclude:** A reader sizes a batch to '65% of 24 GB' or assumes the 2x throughput result transfers to current wide-universe training on pod2.
- **Affects:** future_retrain · **Severity reason:** The numbers are tied to the retired single-asset V4 model on an RTX 4090 with 24 GB; the current GPU host is pod2 (RTX PRO 4500) with a 61 GB container RAM cap, so the VRAM budget and the dataloader-bound premise must be re-measured there.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 scope correction (ONBOARDING_independent_researcher_2026-09-06 §machines + STATE 2026-09-13 08:5xZ + 2026-07-06 single-asset closeout):** these numbers were measured on the single-asset V4 model (66K params) on an RTX 4090 with 24 GB, a track closed out on 2026-07-06. The GPU host today is **pod2 (RTX PRO 4500)** with a **61 GB container RAM cap** (not the 247 GB `free` reports) and a /workspace quota that has hit its ceiling before. The rule (when dataloader-bound, bump batch first with sqrt LR scaling) is transferable; the '15.7 GB of 24 GB (65%)' budget and the ~2x figure are not — re-measure on pod2 before sizing.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M4-52 · P3 · DOC_STALE
- **Source:** `memory/feedback_verify_cudnn_not_just_cuda.md:22`
- **Quote:** 「V5 push 训练在 jpline server (RTX 3090, 24GB) 上 1 epoch 41 min, 但 V5 production 同样硬件 3-5 min. 调查发现:」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:69` — 「jpline 自 09-04 起不可达」
  - `docs/ONBOARDING_independent_researcher_2026-09-06.md:75` — 「| **pod2**(RTX PRO 4500) | GPU 训练 + LOB |」
  - `docs/ONBOARDING_independent_researcher_2026-09-06.md:75` — 「计算实例可停; 网络卷持久。重启自愈 `BOOTSTRAP.sh`」
- **A reader could wrongly conclude:** A reader applies the check only when 'switching to a new server' and skips it after a pod2 restart/BOOTSTRAP, or tries to reproduce the incident on jpline.
- **Affects:** future_retrain · **Severity reason:** The incident environment (jpline RTX 3090, shared ml conda env) is no longer reachable or in use; the rule now applies to pod2, whose compute instance can be stopped and re-bootstrapped, which is exactly when a cuDNN-less env can reappear.
- **Proposed correction (exact text):** > ⚠ **2026-09-16 更正(PROGRAM_uplift_r3_2026-09-13 §数据 + ONBOARDING_independent_researcher_2026-09-06 §机器表):** 事故环境(jpline, RTX 3090, 共享 ml conda env)已不适用 —— **jpline 自 2026-09-04 起不可达**。现役 GPU 机是 **pod2(RTX PRO 4500)**, 计算实例可停、重启自愈走 `BOOTSTRAP.sh` ⇒ 本规则的触发点应改为「新 env **或 pod2 每次重启/BOOTSTRAP 之后**, 跑训练前先断言 `torch.backends.cudnn.version() is not None`」。规则本身与症状识别(长时间无 epoch 输出 + GPU 满载 + 卡 `loss.backward()`, `py-spy dump` 确认)不变。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-12 · P3 · DOC_STALE
- **Source:** `memory/judge_ci_depends_on_arm_set.md:11`
- **Quote:** 「(1) 引用某个 CI 时, 连"那次判官运行有哪些臂"一起引; 跨运行比 CI 边界无效, 只能比点估计。(2) 新写判官一律**每个比较各自** `default_rng(SEED, spawn_key=(i,))` 或按比较名派生子流, 使 CI 对臂集不变。」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:4` — 「per-contrast sub-stream (judge_ci_depends_on_arm_set): rng = default_rng([20260905, contrast_index]).」
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:318` — 「for ci, (a, b) in enumerate(CON):」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T4/devices/t4_judge.py:58` — 「if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])」
- **A reader could wrongly conclude:** A reader treats every cross-run CI comparison as invalid, including r18-boot judges whose draws depend only on replicate k and day count. Or a reader assumes judge_v4's per-contrast stream is arm-set invariant, although its contrast_index is the position in CON.
- **Affects:** future_eval · **Severity reason:** Low risk: rule (2) has been adopted, and (1) is now overbroad for r18-boot judges but still needed for index-keyed streams.
- **Proposed correction (exact text):** ⚠ 现状补注(2026-09-13 审计): 规则 (2) 已被采用 —— judge_v4.py 用 `default_rng([20260905, contrast_index])`(L4); r18 boot() 系判官(T1–T6, 如 t4_judge.py L58)按重复序号 k 与日数 nd 取公共随机数, CI 对臂集不变。(1) 因此收窄为: 只对单一全局 RNG 顺序抽样的判官(如 judge_gate_addendum5.py)成立; 同装置、同日集合下 r18 boot() 系判官的 CI 可跨运行比较。注意 judge_v4 的 contrast_index 取自 `enumerate(CON)`(L315), 在 CON 中间插入对照会改变其后各对照的子流 —— 新对照只追加到末尾, 或按对照名派生子流。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-13 · P3 · DOC_STALE
- **Source:** `memory/correlational_count_vs_interventional_check.md:70 (+1 more)`
- **Quote:** 「satisfies `σŷ = r · σy`, so **a correctly calibrated model with IC ≈ 0.046 should produce σŷ/σy ≈
0.046** — measured 0.063 is *slightly over-spread*, not shrunk 16×.」
- **Superseding evidence:**
  - `docs/TEAM_PROTOCOL.md:54` — 「1. **(§8-b 补)** 判别基准若本身是统计量, **必须写明是哪一种**(Pearson? Spearman? 逐锚还是池化?) —— 基准也会掉进 §8-c(实例: rank-IC 0.046 被代入本应是 Pearson 0.010–0.018 的位置)。」
- **A reader could wrongly conclude:** A reader reuses 'IC ≈ 0.046 ⇒ expected σŷ/σy ≈ 0.046' as the calibration benchmark and reads 0.063 as only slightly over-spread. The MSE-optimal slope needs the Pearson IC (0.010–0.018), which makes 0.063 roughly 3.5–6× over-spread.
- **Affects:** future_eval · **Severity reason:** Low risk: it is a worked example in a closed research episode; the rule stands, but the benchmark number would mis-calibrate a future σŷ/σy reading.
- **Proposed correction (exact text):** ⚠ Benchmark correction (TEAM_PROTOCOL §1-c item 1, same night): 0.046 was a rank-IC, but `σŷ = r·σy` needs the Pearson IC, which was 0.010–0.018 here. The no-defect benchmark is therefore σŷ/σy ≈ 0.010–0.018, and the measured 0.063 is about 3.5–6× over-spread (still not shrunk). The rule stands; the worked example's benchmark number does not.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** segments

### M5-14 · P3 · DOC_STALE
- **Source:** `memory/my_own_instruments_fail_at_the_extremes.md:37`
- **Quote:** 「复发堵漏=探针轮首清扫 probe* 遗留挂单(08-19 已上线)。」
- **Superseding evidence:**
  - `docs/ERROR_LEDGER_2026-08-20.md:101` — 「## ★★★ E-0821-C 探针轮末"全平"平掉了书的仓 ⇒ 看门狗 5b/5e 真触发 ⇒ 第二次整书平仓(2026-08-21 20:16Z)」
  - `docs/ERROR_LEDGER_2026-08-20.md:105` — 「- **修复/制度**: 探针已停(KILL+PID); 重启三前置(只平自己成交 / 排除两书宇宙并集 140∪400 加持仓名 / 对账收据);」
  - `cmd:launchctl list (read-only, 2026-09-13):com.hsy.execprobe2` — 「-	3	com.hsy.execprobe2」
- **A reader could wrongly conclude:** A reader takes the 08-19 round-start sweep as having plugged probe harm and restarts a shared-account probe. Two days later (E-0821-C) the probe's round-end flatten closed book-held positions and forced a whole-book flatten.
- **Affects:** live_trading · **Severity reason:** The later probe incident is documented in ERROR_LEDGER and the probe is not running, but this line alone implies the probe-harm family was plugged.
- **Proposed correction (exact text):** ⚠ 补注(2026-09-13 审计): 08-19 的轮首清扫只堵了「遗留挂单」这一形; 08-21 E-0821-C 探针轮末全平不分仓位归属, 平掉书持有的 ATOM/SNX ⇒ 看门狗真触发、第二次整书平仓; 探针已停, 重启须满足三前置(只平自己成交 / 排除两书宇宙并集加持仓名 / 对账收据)与铁律「共账户辅助进程的平仓/下单集合与书宇宙不相交、只动自己建的仓」(ERROR_LEDGER L89–94)。
- **Confidence:** VERIFIED (quote+receipt opened; launchctl shows com.hsy.execprobe2 not running, last exit 3) · **Quote re-verified at assembly:** exact

### M5-15 · P3 · DOC_STALE
- **Source:** `memory/noninferiority_rule_is_not_noninferiority_proof.md:12`
- **Quote:** 「① Any "不劣 / 持平 / 追平 / not worse than" conclusion must be written as **CI lower > −δ**, printing δ and the lower bound together.」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带，不能推广为两代部署 booster 全部窗口都无材料性影响。」
  - `STATE.md:128` — 「未换装前线上 = v3 旧链(书层已证不可区分)。」
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:5` — 「(C) otherwise UNDECIDED (never 'non-inferior').」
  - `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_const2027_replay_2026-09-07/RESULT.md:15` — 「| FIX7_42 - CONST42 | +0.266927 | [+0.083418, +0.466965] | [+0.093313, +0.463138] |」
- **A reader could wrongly conclude:** A reader checks only 'not worse / parity' wording and lets equivalence labels from a CI-contains-zero gate ('NOT MATERIAL', '书层已证不可区分') pass as established, as in T4 and STATE's v3-chain line.
- **Affects:** future_eval, reporting · **Severity reason:** Low risk: the rule is correct and judge_v4 adopted it, but its wording scope misses the equivalence labels ('NOT MATERIAL', '不可区分') in which the same defect recurred on 09-13.
- **Proposed correction (exact text):** ⚠ Scope addendum (2026-09-13 audit): the same rule applies to equivalence labels. 'NOT MATERIAL', '不可区分' or '无材料性影响' produced by a CI-contains-zero / significance gate are not established without a pre-set economic band δ and a CI inside [−δ, +δ] (REV4 §4.3 on T4's NOT MATERIAL; STATE's 'v3 旧链(书层已证不可区分)' rests on (C) UNDECIDED cells). judge_v4 already emits '(C) UNDECIDED (never non-inferior)'. The superiority numbers above were re-replicated against CONST42 on 09-07 (FIX7_42 − CONST42 +0.267 [+0.083, +0.467]); a v4-caliber recompute of these pairs has not been run.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### M5-16 · P3 · DOC_STALE
- **Source:** `memory/alignment_gate_must_not_carry_book_property_prior.md:8`
- **Quote:** 「The NET condition failed at +0.051 / +0.043, because the prior came from a different book, return source and universe.」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:87` — 「- 与 08-21 主导率记录的方向相反: 事实已核, 原因未查。」
- **A reader could wrongly conclude:** A reader treats the sign conflict with the 08-21 dominance-premium receipt as explained ('different book/return source/universe') and dismisses one instrument. T8 recorded the cause as not investigated and which instrument is right as pending reconciliation.
- **Affects:** future_eval · **Severity reason:** Low risk: the note's gate-design lesson stands, but it states as the established cause what T8 recorded as an unreconciled inference.
- **Proposed correction (exact text):** ⚠ Qualifier (2026-09-13 audit): 'because' is an inference. RESULT_T8 §6.1 verified that the two instruments differ (08-21: S1 net_S1.npy, engine src.Y4, tradable set minus BTC/ETH; T8: A0 v4 RAW accounting, UPIT_CRYPTO minus BTC), but it recorded the cause of the opposite sign as not investigated and which instrument is right as pending reconciliation. Write: 'failed at +0.051 / +0.043; the prior came from a different instrument (book / return source / universe); which one is right is unreconciled'.
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### MK-07 · P3 · DOC_STALE
- **Source:** `memory/book_is_dominance_premium.md:3`
- **Quote:** 「该暴露≈书收益78%(截面alpha仅0.29bps/锚 夏普0.59); 对冲它=毁收益(h=1β夏普0.59)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:78` — 「**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。」
- **A reader could wrongly conclude:** 78% of the in-service book's return is dominance exposure.
- **Affects:** reporting, future_eval · **Severity reason:** The body already carries two T8 caveats (one Chinese, one English, duplicated), but the description line recalled at session start still states 78%.
- **Proposed correction (exact text):** description 改为: "08-21 在役书 S1 旧仪器: 净额对山寨−BTC 价差 β −0.249 / r −0.767, 暴露≈收益 78%; ⚠ A0 v4(在役 combo 形态)同期 corr +0.05、逐折 β 为正(T8 §6.1), 该结论不迁移, 两仪器待对账"; 删除 L17 重复的英文警示段(与 L14 同义)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

## §4 Evaluation devices (17 rows)

Devices in current use or whose labels are still quoted in decisions. The FX-EVAL K2 fact table (`docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md`, F01–F26) already enumerates the no-difference label family with a frozen δ table. Rows here cover the items K2 does not own or that bear on the answers below.

| id | sev | status | affects | source | claim (abridged) |
|---|---|---|---|---|---|
| DEV-01 | P1 | PENDING_USER_DECISION | future_retrain, future_eval | `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:349` |             v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r)  |
| DEV-15 | P1 | VERIFIED_CURRENT | future_eval, live_trading | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:507` | **G-1(整类设计否决)**: `ShadowState.save()` 写**固定键集** ⇒ 任何写进 `aux.json` 的额外键都会在**下一个锚**被丢掉 |
| DEV-17 | P1 | VERIFIED_CURRENT | live_trading, future_eval | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:509` | **G-3(新)**: **凡失败模式是返回码的调度, 该返回码必须被读取并写进记录。** |
| DEV-02 | P2 | DOC_STALE | reporting, future_retrain | `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:298` | print("\n== LEVELS (bps/anchor per gross; annual % per gross = mean*2190/1e4; at 2.0x gross multiply by 2) ==") |
| DEV-03 | P2 | DOC_STALE | future_retrain, future_eval | `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/run_v4_arms.sh:15` | W3FIX=0.21,0,0.79 |
| DEV-04 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T4/devices/t4_judge.py:150` | verdict = "MATERIAL" if (condA or condB) else "NOT MATERIAL (at this resolution)" |
| DEV-05 | P2 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py:207` |     label = {(True, False): "STRATEGY'S OWN LOSS (king chain)", (False, True): "DEPLOYMENT DIFFERENCE", (True, True): "SAME DIRECTION WITH A |
| DEV-06 | P2 | DOC_STALE | future_eval, reporting | `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py:73` |             label = "BOTH LOST, DEPLOYMENT GAP" if gap else ("STRATEGY'S OWN LOSS (king chain, target layer)" if same else "BOTH LOST, UNDEC |
| DEV-08 | P2 | OPEN_NOT_MEASURED | future_eval | `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py:12` | data (T, 829, 7) float16 with channels [ret5, rng, cpos, lqv, lcnt, lasz, tbf] and clips CHN_CLIPS — identical to the pod ext cache used by  |
| DEV-09 | P2 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:70` | **How to read the N columns:** N_eff is AMENDMENT 5's primary and says the 125 members are ≈1.6 independent trials |
| DEV-11 | P2 | OPEN_NOT_MEASURED | future_eval | `multi_asset/exports/research/parity_replay_2026-09-12/phase2/devices/p2_g2c_judge.py:41 (+2 more)` | combo_ok |
| DEV-14 | P2 | DOC_STALE | reporting, future_eval | `/Users/haosiyu/regime_dash/REGIME_DASH.md:1` | # REGIME DASH(只读)— 最新锚 |
| DEV-16 | P2 | VERIFIED_CURRENT | future_eval | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:508` | **G-2(检查表规则)**: **返回 dict 的函数必须返回恒定键集**, 源缺席处给 `None`。 |
| DEV-07 | P3 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/devices/t5b_q1.py:248` | reading=("FROZEN-RESIDUAL-MATERIAL" if x.mean() >= 0.05 else "NOT MATERIAL") |
| DEV-10 | P3 | DOC_STALE | future_eval | `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:22` | S2 不开; 无任何书行为提案。 |
| DEV-12 | P3 | DOC_STALE | reporting, live_trading | `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)` | guard_twin AGREE |
| DEV-13 | P3 | DOC_STALE | live_trading, reporting | `docs/ERROR_LEDGER_2026-08-20.md:71` | 空腿聚合 2h −100U+ → Telegram 预警 |

### DEV-01 · P1 · PENDING_USER_DECISION
- **Source:** `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:349` · xref TRN-24, K2-F21
- **Resolution:** XREF AUDIT_TRAIN TRN-24 — CROSS-REF: judge windows ending 2026-08-31 (October's new month never read) is owned by AUDIT_TRAIN TRN-24. This row's own finding — the (A) PROMOTE predicate lacking an equivalence band and per-year condition — remains aud-kb's and is PENDING_USER_DECISION.
- **Quote:** 「            v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED")」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:55` — 「FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1)」
  - `CLAUDE.md:19` — 「2. **非平稳性** — 结论必须多年 walk-forward + 跨 regime + 最坏五分位(Q4)。」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:21` — 「The 2.94 frozen-window level is mostly shared by the whole family (median member 2.673 on FROZEN vs 1.006 on W_FULL)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_TRAIN.md:119 (+1 more: 442)` — 「Judge windows end at 2026-08-31, so October's new month is never read」
- **A reader could wrongly conclude:** An (A) PROMOTE means the arm is better across regimes by an economically meaningful amount.
- **Affects:** future_retrain, future_eval · **Severity reason:** The October chain's judge stage (sha c2a81c48) promotes on significance in one 17-month window; there is no economic floor, no worst-year or regime condition, and yearly levels are print-only.
- **Proposed correction (exact text):** 判官 (A) 追加两个条件(预注册修订, 用户裁定): ① 双种子 CI 下界 > δ(K2 D1 = 0.05 bps/锚/gross, 非 0); ② 全周期逐年(2023–2026)无一年 Δ 的 CI 上界 < −δ, 且 2023(弱年)点估计 ≥ −δ; 冻结窗之外的扩展/逐年读数写入 verdict 旁并在 (A) 时强制打印
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 346->349)

### DEV-15 · P1 · VERIFIED_CURRENT
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:507`
- **Quote:** 「**G-1(整类设计否决)**: `ShadowState.save()` 写**固定键集** ⇒ 任何写进 `aux.json` 的额外键都会在**下一个锚**被丢掉」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:507` — 「**对任何未来的迁移工具都适用**, 不只 FXR-PROD-1。**由读 `save()` 得到, 不由行为推断。**」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:205` — 「`setdefault` 钉住旧标签、当前输入的标签冲突**只收集不拒绝**」
- **A reader could wrongly conclude:** A later session designs an idempotency marker, a schema-version field or an applied-fixes ledger inside producer state, tests it within one anchor where it appears to work, and ships a migration whose re-run protection silently evaporates at the next anchor.
- **Affects:** future_eval, live_trading · **Severity reason:** This vetoes a whole class of designs, not one tool: because `ShadowState.save()` writes a fixed key set, nothing written into `aux.json` survives the next anchor, so no marker, version field or applied-corrections list can record inside producer state which version that state has absorbed. Any future migration tool that relies on such a record is unsound before it is written.
- **Proposed correction (exact text):** (登记为通用条目, 无源文件需改 —— 受据 FX-PROD 6684895e, 纲领 §20.1-1) **G-1 = 整类设计否决**: 「把『本状态已吸收到哪一版 / 哪些行』记录在生产者状态内部」这一整类设计**都不成立** —— 不是标记, 不是版本字段, 不是已应用修正清单。机制: `ShadowState.save()` 写固定键集, 额外键在下一个锚被丢掉。**适用范围 = 任何未来的迁移工具**, 不限 FXR-PROD-1。**取证方式本身是本条的一半**: 该结论**由读 `save()` 源码得到, 不由行为推断** —— 单锚内观察会显示标记「有效」, 正是 [[defect_with_no_behavioural_signature]] 的形状。⇒ 幂等性必须记在**状态之外**(独立工件 + sha), 或由**输入的内容哈希**推出。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 521->507)

### DEV-17 · P1 · VERIFIED_CURRENT
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:509`
- **Quote:** 「**G-3(新)**: **凡失败模式是返回码的调度, 该返回码必须被读取并写进记录。**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:509` — 「Python: **`subprocess.run` 在非零退出时不抛异常** ⇒ 不读 `returncode` 等于没发」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:509` — 「FX-PROD 今天第三次撞到同一形态(PROD-46 的页报调度), **是从测试 stderr 看到子进程失败而格子仍绿才发现的**」
- **A reader could wrongly conclude:** An alert path is certified green by a test that proves the call was made, not that it succeeded — 「装置绿 ≠ 被测动作发生」. The same shape hides a failed page, a failed commit and a failed backfill.
- **Affects:** live_trading, future_eval · **Severity reason:** Third recurrence of one shape, and the failing dispatch was a HIGH page: `subprocess.run` does not raise on a non-zero exit, so an unread `returncode` means the alert was never delivered while the test cell stayed green; it was caught only because a human read the test's stderr.
- **Proposed correction (exact text):** (登记为通用条目, 受据 FX-PROD 6684895e, 纲领 §20.1-3) **G-3**: **凡失败模式是返回码的调度, 该返回码必须被读取并写进记录。** shell: `rc=$?` 不得与被测命令之间隔管道或 `tail`(有管道用 `PIPESTATUS` / zsh `pipestatus`); Python: **`subprocess.run` 非零退出不抛异常** ⇒ **不读 `returncode` 等于没发**。FX-PROD 2026-09-16 第三次撞到同一形态(PROD-46 的页报调度), **发现方式是从测试 stderr 看到子进程失败而格子仍绿** ⇒ 本条的真正教训是「**装置绿 ≠ 被测动作发生**」。同族: [[background_completion_is_not_the_test_result]] · [[defect_with_no_behavioural_signature]]。**给 K5 的推论**: 深查模板里凡「发页报 / 提交 / 回填」一类动作, 报的必须是**该动作的返回码**, 不是「已调用」。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 523->509)

### DEV-02 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:298`
- **Quote:** 「print("\n== LEVELS (bps/anchor per gross; annual % per gross = mean*2190/1e4; at 2.0x gross multiply by 2) ==")」
- **Superseding evidence:**
  - `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:111` — 「        v = g[m]; c = np.concatenate([[0.0], np.cumsum(v)]); dd = float(np.max(np.maximum.accumulate(c) - c))」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:31` — 「回撤一律按固定 2× 复利 NAV 报, 不用算术 ×2」
  - `multi_asset/exports/research/uplift_2026-09-11/r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md:27` — 「按同一收益流固定 2 倍每锚复利 Π(1+2g·1e−4) 的 NAV maxDD: 2022 **−10.70%**(×2 近似 −11.16) / 2023 **−28.92%**(近似 −33.54, 误差 4.61pp) / 2024 **−23.62%** / 2025 **−15.53%** / 2026 **−15.98%**; W_ALPHA 全窗 C0_s42 **−42.12%**」
- **A reader could wrongly conclude:** Judge maxDD ×2 is the NAV drawdown at 2.0×.
- **Affects:** reporting, future_retrain · **Severity reason:** Judge level tables report additive maxDD and tell the reader to double it; the programme rule and r18 errata require compounded fixed-2× NAV (×2 overstates 2023 by 4.61 pp, understates others).
- **Proposed correction (exact text):** levels() 增列 `maxdd_nav2x_compound = max 峰谷 of Π(1+2·g·1e−4)`, 打印行改为「annual % per gross = mean*2190/1e4; NAV 回撤按固定 2× 逐锚复利列, 勿用算术 ×2」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-03 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/run_v4_arms.sh:15`
- **Quote:** 「W3FIX=0.21,0,0.79」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:42` — 「⇒ **0.21 是一个已知缺陷态下、单日测得的快照**; 同一规则修好后落在 0.30–0.36。」
  - `multi_asset/exports/research/uplift_2026-09-11/RESULT_r5_angle1_fixed_seat_2026-09-11.md:75` — 「⇒ **2024 与 2025 两本书的年度损益符号相反**, 相关只 0.22/0.36(共享方差 5%/13%)。」
- **A reader could wrongly conclude:** Fixed-seat verdicts are a robustness check of the live book.
- **Affects:** future_retrain, future_eval · **Severity reason:** judge_v4 issues per-seat verdicts for a fixed-seat 0.21 book that r5 showed is a different book with no discriminating power; a (B) on the fix seat can read as a veto.
- **Proposed correction (exact text):** 固定席位臂仅作描述(不出 verdict), 或按预注册改为「被判窗动态席位均值」(A0 冻结窗 0.5338); verdict 以动态席位为准
- **Confidence:** VERIFIED (script line and r5 receipt) · **Quote re-verified at assembly:** exact

### DEV-04 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T4/devices/t4_judge.py:150` · xref K2-F01, RELABEL_TABLE_K2 T4
- **Quote:** 「verdict = "MATERIAL" if (condA or condB) else "NOT MATERIAL (at this resolution)"」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:136` — 「其 `NOT MATERIAL` 标签仍由显著性门生成，未设置经济等价带」
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:26` — 「| F01 | T4 |」
- **A reader could wrongly conclude:** NOT MATERIAL = economically negligible.
- **Affects:** future_eval · **Severity reason:** Significance-only no-difference label (SIG-ONLY-NULL).
- **Proposed correction (exact text):** 采用 FX-EVAL K2 规则 R-T4(δ D1 = 0.05 / D4 = 0.003)替换 L150 谓词; 本次存档读数重标 = INCONCLUSIVE(RELABEL_TABLE_K2 T4 行), 不另立标签
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-05 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py:207` · xref K1, K2-F02, RELABEL_TABLE_K2 T5c
- **Quote:** 「    label = {(True, False): "STRATEGY'S OWN LOSS (king chain)", (False, True): "DEPLOYMENT DIFFERENCE", (True, True): "SAME DIRECTION WITH A GAP", (False, False): "UNDECIDABLE"}[(same, gap)]」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:112` — 「原 `readings` 标签在“两本都盈利且相同”的合成输入上仍能写 `STRATEGY'S OWN」
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:27` — 「| F02 | T5c |」
- **A reader could wrongly conclude:** STRATEGY'S OWN LOSS means the loss was real, shared and deployment gaps are excluded.
- **Affects:** future_eval, reporting · **Severity reason:** CI-OVERLAP-SAME + LOSS-WITHOUT-SIGN: prints a loss label on all-profit input; T5d added the sign requirement but kept the same-without-band gate.
- **Proposed correction (exact text):** T5c 装置保留原样(存档); 引用其标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05): 价格与净额 = **SHARED LOSS, DIFFERENCE INCONCLUSIVE**, carry = INCONCLUSIVE(RELABEL_TABLE_K2 T5c 行); 新装置复用 R-LOSS, 不复用本谓词
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-06 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py:73` · xref K2-F03, RELABEL_TABLE_K2 T5d
- **Quote:** 「            label = "BOTH LOST, DEPLOYMENT GAP" if gap else ("STRATEGY'S OWN LOSS (king chain, target layer)" if same else "BOTH LOST, UNDECIDABLE")」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md:54` — 「- **经济等价带** δ = 0.25 bps/锚(A0 全周期净额 +0.6342 的约 40%; 更大的差对这本书有经济意义)。」
  - `docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.md:33` — 「"T5d_band_0p25": {」
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:28` — 「| F03 | T5d (in flight, K1 owner) |」
- **A reader could wrongly conclude:** OWN LOSS under T5d means deployment gaps are negligible; ±0.25 bps is an economically negligible difference.
- **Affects:** future_eval, reporting · **Severity reason:** BAND-NOT-GATING: the label ignores the computed equivalence flag; and δ=0.25 equals 39% of A0 net (≈10.95% NAV/yr at 2×), far wider than the K2 book δ 0.05.
- **Proposed correction (exact text):** 引用 T5d 标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05; RELABEL_TABLE_K2 T5d 行: 价格/净额 SHARED LOSS, DIFFERENCE INCONCLUSIVE); PREREG §6.2 的 δ = 0.25 只能写作「A0 全周期净额约 40% 的量级线(≈10.95% NAV/年 @2×)」, 不得称「经济上可忽略」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-08 · P2 · OPEN_NOT_MEASURED
- **Source:** `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py:12`
- **Quote:** 「data (T, 829, 7) float16 with channels [ret5, rng, cpos, lqv, lcnt, lasz, tbf] and clips CHN_CLIPS — identical to the pod ext cache used by the」
- **Superseding evidence:**
  - `~/wide_shadow/shadow_loop_v3.py:150` — 「CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]」
  - `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py:84` — 「    cum = np.expm1(LC[E + 1: E + 49][:, js] - LC[E, js])   # (48, n) cumulative return from the anchor close」
  - `memory/cache_ret5_channel_clipped_at_0p30_2026_09_12.md:3 (+1 more: 13)` — 「E-0908-B」
- **A reader could wrongly conclude:** The forward log's P-layer values are on the accounting caliber.
- **Affects:** future_eval · **Severity reason:** The daily forward log feeding the only surviving tail lead (re-judgement at ≥200 events) recomputes returns from the ±0.30-clipped float16 ret5 cache; the clip binds exactly on parabolic/crash bars.
- **Proposed correction (exact text):** 前向日志改读记账口径: 以原始 1m/5m 收盘价(未裁剪, float64)或 v4 记账元重算 onset 与 τ→下一锚收益; 在改之前, 日志与复判读数标注「裁剪缓存口径(E-0908-B 同族), 尾部为下界」并统计 |ret5|=0.30 饱和格数
- **Confidence:** VERIFIED for the code path; magnitude not measured · **Quote re-verified at assembly:** exact

### DEV-09 · P2 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T6/RESULT_T6.md:70`
- **Quote:** 「**How to read the N columns:** N_eff is AMENDMENT 5's primary and says the 125 members are ≈1.6 independent trials」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:128` — 「**参与比是谱维数，不是已校准的极值有效尝试数。**」
- **A reader could wrongly conclude:** P(true SR > 3.0) at N_eff is a calibrated probability.
- **Affects:** future_eval · **Severity reason:** t6_compute feeds the participation ratio into DSR as the trial count and labels the output P(true SR>3); the reviewer's equicorrelated counterexample puts the benchmark at ~20% of the exact expected maximum.
- **Proposed correction (exact text):** N 列读法: N_eff(参与比)是谱维数, 不是极值意义下的有效试验数; 各 N 列只是代入读数, 不是真夏普超过阈值的概率; 需用联合时间块重抽样或前向验证校准后才可作门
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-11 · P2 · OPEN_NOT_MEASURED
- **Source:** `multi_asset/exports/research/parity_replay_2026-09-12/phase2/devices/p2_g2c_judge.py:41 (+2 more)` · xref K3
- **Quote:** 「combo_ok」
- **Superseding evidence:**
  - `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md:167` — 「`phase2/devices/p2_g2c_judge.py:37` 只取每份 `anchors[0]`，`:41` 的 `combo_ok` 只看 rc 和 Linf，不验预定锚、长度或三锚不同。」
- **A reader could wrongly conclude:** G2-C PASS certifies three distinct pre-registered anchors.
- **Affects:** future_eval · **Severity reason:** Snapshot-parity gate can pass on one receipt copied into three slots or on wrong anchors; needed before any automatic G2-C eligibility.
- **Proposed correction (exact text):** G2-C 判官冻结 slot→anchor 映射, 断言每份收据恰一锚、集合无重漏, 并核 prep/输入身份与执行收据一致; 修前 G2-C PASS 只作「三份真实收据已人工核对」的描述
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-14 · P2 · DOC_STALE
- **Source:** `/Users/haosiyu/regime_dash/REGIME_DASH.md:1`
- **Quote:** 「# REGIME DASH(只读)— 最新锚」
- **Superseding evidence:**
  - `/Users/haosiyu/regime_dash/regime_dash.jsonl:1` — 「anchor_utc」
  - `docs/audit_pipeline_2026-09-13/AUDIT_KB_PARTIAL.md:3` — 「AUDIT_KB_PARTIAL」
- **A reader could wrongly conclude:** A reader who opens the cited receipt sees a different seat (king 0.378 / fund 0.622 at 2026-09-16 00:00Z) and concludes either that the register is wrong or that the composition changed materially, when the real fact is that the seat rolls every anchor and the receipt was volatile.
- **Affects:** reporting, future_eval · **Severity reason:** Ten rows of this register (M1-10, M1-11, M2-04, M2-11, M2-12, M2-15, M2-22, M2-29, M2-30, M5-05) cite `~/regime_dash/REGIME_DASH.md:16` 「席位(掩码后) king 0.382 / fund 0.618」 as their receipt, but that file is regenerated every anchor by the launchd collector, so the quoted line was gone the next anchor and none of those receipts could be re-located at assembly time.
- **Proposed correction (exact text):** [登记规则, 适用于本登记全部引用席位/regime 读数的行] **滚动文件不得作收据。** `~/regime_dash/REGIME_DASH.md` 每锚被采集器 `regime_dash.py` 整份重写(launchd, 只保留最新锚)⇒ 引用它等于引用一个会消失的字节。可复核的同源收据是**追加式** `~/regime_dash/regime_dash.jsonl`, 按 `anchor_utc` 取行, 字段 `w3_masked_king` / `w3_masked_fund`。逐锚核实: **2026-09-13T12:00Z king 0.3821 / fund 0.6179**(= 本登记各行引用的 0.382 / 0.618, 成立)· 2026-09-13T00Z 0.3692 · 04Z 0.3819 · 08Z 0.3782 · 16Z 0.3871 · 20Z 0.3837 · **2026-09-16T00:00Z king 0.3780 / fund 0.6220**。**⇒ 席位逐锚滚动, 任何构成/席位引用必须带锚时刻**; 本登记 10 行的收据路径一律改指 `regime_dash.jsonl` + `anchor_utc`。注意该日志现只覆盖 **2026-09-02T08:00Z → 2026-09-16T00:00Z(83 行)**, 更早的席位读数在此不可复核。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact

### DEV-16 · P2 · VERIFIED_CURRENT
- **Source:** `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:508`
- **Quote:** 「**G-2(检查表规则)**: **返回 dict 的函数必须返回恒定键集**, 源缺席处给 `None`。」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:508` — 「短字典会把 `if key in d` 变成**对「该函数存在的意义」那一项检查的静默跳过**」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:508` — 「PROD-28 装置找 `MANIFEST` 而文件名是 `MANIFEST.json`(⇒ `bundle_mismatch=None`); `h_source_of()` 在 `target_blend` 缺席时返回短字典」
- **A reader could wrongly conclude:** A green check is read as 'the property holds' when it means 'the key was not there, so nothing was checked' — the same family as 「字段缺了就跳过」.
- **Affects:** future_eval · **Severity reason:** Two instances inside one hour of the same shape: a function returns a short dict when a source is absent, so every `if key in d` guard downstream skips exactly the check the function exists to perform, and the skip is silent.
- **Proposed correction (exact text):** (登记为通用条目, 受据 FX-PROD 6684895e, 纲领 §20.1-2) **G-2 = 检查表规则**: **返回 dict 的函数必须返回恒定键集**, 源缺席处显式给 `None`, 由调用方区分「值为 None」与「键不存在」。短字典会把 `if key in d` 变成对**该函数存在的意义**那一项检查的**静默跳过**。两个实测实例(同一小时): PROD-28 装置找 `MANIFEST` 而实际文件名是 `MANIFEST.json` ⇒ `bundle_mismatch=None` 而无人察觉; `h_source_of()` 在 `target_blend` 缺席时返回短字典。同族: [[absent_key_means_skip_defect_family]]。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 522->508)

### DEV-07 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/devices/t5b_q1.py:248` · xref K2-F04, K2-F05, RELABEL_TABLE_K2 T5b
- **Quote:** 「reading=("FROZEN-RESIDUAL-MATERIAL" if x.mean() >= 0.05 else "NOT MATERIAL")」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:29` — 「| F04 | T5b Q1 |」
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/devices/t5b_exec.py:332` — 「READ3["PRIMARY_GAP_EXECFREEZE"]["reading"] = ("EXECUTOR-ADDED-FREEZE-MATERIAL" if (p["mean"] is not None and p["mean"] >= 0.05) else "NOT MATERIAL")」
- **A reader could wrongly conclude:** NOT MATERIAL = no effect.
- **Affects:** future_eval · **Severity reason:** POINT-ONLY-LINE (and ABSENT-AS-NULL in t5b_exec.py: mean None prints NOT MATERIAL).
- **Proposed correction (exact text):** 采用 FX-EVAL K2 R-T5B(δ D8 = 0.05, 上侧 = 付出): MATERIAL ⇔ CI 下界 ≥ 0.05; NOT MATERIAL (established below line) ⇔ CI 上界 < 0.05; 其余 INCONCLUSIVE; mean None ⇒ NOT MEASURED(RELABEL_TABLE_K2 T5b 行: 主读法不变, 三个次级 MATERIAL → INCONCLUSIVE)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-10 · P3 · DOC_STALE
- **Source:** `multi_asset/exports/research/uplift_r2_2026-09-13/T8/RESULT_T8.md:22` · xref K2-F16, RELABEL_TABLE_K2 T8
- **Quote:** 「S2 不开; 无任何书行为提案。」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FX_EVAL/FACT_TABLE_K2.md:41` — 「| F16 | T8 |」
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:6` — 「**在现有锚时状态上做监控 / 调节层没有预测基础**(T8)」
- **A reader could wrongly conclude:** Anchor-time state monitoring is proven useless.
- **Affects:** future_eval · **Severity reason:** FAILED-GATE-AS-ABSENCE: FAIL does not require the r CI upper < 0.03; the third programme restates it as 'blocked'.
- **Proposed correction (exact text):** (r3 §0 改) T8 = **FAIL: failed to detect; usefulness not excluded**(FX-EVAL K2 重标): 24 列锚时状态上净额格可用性(r ≥ 0.03)已被排除(CI 上界 < 0.03), LONG/SHORT 格未排除; 不能写作「监控/调节层没有预测基础」的普遍结论
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### DEV-12 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)` · xref CHK-02
- **Quote:** 「guard_twin AGREE」
- **Superseding evidence:**
  - `~/guard_twin/state/latest.json (2026-09-13T13:46:30Z)` — 「"status": "AGREE(ledger-only; nav row stale)", "comparable": false, "disagreements": []」
  - `grep -c 'guard_twin\|AGREE' ~/dl_quant_live/state/anchor_runs.log` — 「0」
- **A reader could wrongly conclude:** guard_twin compared ledger and NAV and agreed.
- **Affects:** reporting, live_trading · **Severity reason:** The twin's status string contains AGREE even when the NAV comparison did not run (comparable false); a check for the word AGREE passes on a non-comparison.
- **Proposed correction (exact text):** guard_twin: 读 `~/guard_twin/state/latest.json` 的 status / comparable / disagreements 与 alerts.log; 只有 comparable=true 且 disagreements 为空才记 AGREE, `AGREE(ledger-only…)` 记为「仅账本侧, NAV 未比」
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### DEV-13 · P3 · DOC_STALE
- **Source:** `docs/ERROR_LEDGER_2026-08-20.md:71`
- **Quote:** 「空腿聚合 2h −100U+ → Telegram 预警」
- **Superseding evidence:**
  - `~/wide_shadow/intraanchor_depth_watch.py:25` — 「SHORTLEG_2H_USDT = -100.0」
  - `launchctl print gui/501/com.hsy.depthwatch` — 「runs = 1067 … last exit code = 0」
- **A reader could wrongly conclude:** A short-leg 2h −100U alert marks an abnormal squeeze.
- **Affects:** live_trading, reporting · **Severity reason:** Alert threshold fixed at NAV ≈15k/1.5×; at gross ≈235k a −100U 2h short-leg move is ≈0.04% of gross, so the alert is either noise or deduplicated away.
- **Proposed correction (exact text):** 空腿聚合 2h 阈值按 gross 比例设定(如 −0.5% of short gross, 预注册标定日与 σ), 08-20 的 −100U 仅适用 NAV≈15k
- **Confidence:** VERIFIED for code and job state; alert rate not measured · **Quote re-verified at assembly:** exact (line moved 62->71)

**Q2(a) Verdict labels generated purely by significance, without an economic equivalence band** (current or still quoted):
- `uplift_r2_2026-09-13/T4/devices/t4_judge.py` NOT MATERIAL (DEV-04, KB-41/KB-48; K2 F01).
- `retrain_2026-09/v4_chain_2026-09-09/judge_v4.py` (C) UNDECIDED is honest in the device, but documents restate it as 「书层已证不可区分」 (KB-14; K2 F21 lists RESULT_v4_chain, STATUS_three_questions, RULINGS_requested, RUNBOOK_2026-10). Its (A) PROMOTE is also significance-only, with no δ floor, and rests on a single 17-month frozen window (DEV-01).
- `uplift_r2_2026-09-13/T1/devices/t1_judge.py` H1/H5 DOES-NOT-EXPLAIN / FALSIFIED partly from CI-contains-0 (K2 F09/F11).
- `parity_replay_2026-09-12/phase2/devices/p2_s2_lib.py` (C) indistinguishable on a point estimate |Δg|<0.23, evaluated before (A)/(B) (K2 F22, in flight).
- `uplift_r2_2026-09-13/T8/devices/t8_judge.py` FAIL read as absence of predictability (DEV-10; K2 F16).
**Q2(b) Devices in current use that read a superseded panel or caliber:**
- `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py` (daily job) recomputes forward returns from the producer's ±0.30-clipped float16 ret5 cache; this feeds the only surviving tail lead (DEV-08).
- `judge_v4.py` levels: additive maxDD with a ×2 instruction, whereas the programme rule is compounded fixed-2× NAV (DEV-02). Its fixed-seat arms use W3FIX 0.21, a defect-state constant (DEV-03 via `run_v4_arms.sh`). Its windows are hard-coded to 2026-08-31, so October data are never read (AUDIT_TRAIN TRN-24).
- Research king input `SLOW_v3_on_v4axis.npy` (A0 / all T-series replays) is v0-scored on column 80, while live serves v1 (T4). V2MAIN has the same skew, and its history is NOT MEASURED (T4b). Open as FIXPROGRAM P1/P2; replay-versus-live comparisons carry this difference.
- x0910 extension panel (`r6_panel_splice.py` SEP_IV) has a wrong settlement interval on 23 names. T1 D2 and T5c carry inherit it; T5d corrected it, but T5d's own truth source is under T5d-R because of FIXPROGRAM P9.
- `~/wide_shadow/intraanchor_depth_watch.py` short-leg alert −100 USDT is calibrated at NAV≈15k (DEV-13). `~/guard_twin` status prints AGREE when not comparable (DEV-12).
**Q2(c) Label predicates that can misfire:**
- T5c `readings()` prints STRATEGY'S OWN LOSS on all-profit identical books (CI-overlap, no sign), per the reviewer's synthetic case (DEV-05; K1).
- T5d fixed the sign, but OWN LOSS is still gated by CI overlap, not by the computed `equiv`, and its δ 0.25 is 39% of A0 net (≈10.95% NAV/yr at 2×) against K2's D1 0.05 (DEV-06; K2 F03).
- T5b Q1/Q3 give NOT MATERIAL from a one-sided point line: −0.120 [−0.245, −0.021], significant in the receive direction, prints NOT MATERIAL, and a None mean prints NOT MATERIAL (DEV-07; K2 F04/F05).
- P2 G2-C snapshot judge passes three copies of one receipt or wrong anchors (DEV-11; K3).
- T6 DSR labels plug-in readings at N_eff as P(true SR>3) (DEV-09).

## §5 Per-anchor deep-check template (14 rows)

Template = `docs/CRON_TEMPLATES_2026-09-04.md` line 13. The live job 41df7caa was created 2026-09-09T00:24:05Z and its prompt is byte-identical to that line (sha256 72868066f099ea29 both). The job is session-only and auto-expires after 7 days (≈2026-09-16T00:24Z), so it has to be re-created, which is the natural point to swap in the revised text. CronList from the teammate context returns no jobs, so liveness was established from the lead transcript, not from CronList.

| id | sev | status | affects | source | claim (abridged) |
|---|---|---|---|---|---|
| CRON-01 | P0 | DOC_STALE | live_trading | `docs/CRON_TEMPLATES_2026-09-04.md:16` | 整体回滚=kill combo_live_daemon.pid 内 PID |
| CRON-02 | P2 | DOC_STALE | live_trading, reporting | `docs/CRON_TEMPLATES_2026-09-04.md:16` | 反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级) |
| CRON-04 | P2 | DOC_STALE | reporting, future_eval | `docs/CRON_TEMPLATES_2026-09-04.md:16` | fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带) |
| CRON-06 | P2 | DOC_STALE | live_trading, reporting | `docs/CRON_TEMPLATES_2026-09-04.md:16` | phase_C anchors_row+readback+per_name_stop |
| CRON-11 | P2 | DOC_STALE | reporting, future_eval | `lead transcript b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0.jsonl:20043 (CronCreate 2026-09-09T00:24:21Z, job 4a2f33e3, `52 14 * * *` local, session-only, auto-expires ≈2026-09-16T00:24Z)` | 然后 git add/commit(无新增则不提交) |
| CRON-12 | P2 | OPEN_NOT_MEASURED | future_eval | `lead transcript b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0.jsonl:20043 (CronCreate 2026-09-09T00:24:21Z, job 4a2f33e3, `52 14 * * *` local, session-only, auto-expires ≈2026-09-16T00:24Z)` | 当 P 层 θ8 已填事件 ≥ 200 且距 2026-09-06 ≥ 14 天时, 向用户报"可复判", 复判按 PREREG_crash_continuation_parabolic_stratum §2 六条另起。 |
| CRON-13 | P2 | DOC_STALE | live_trading, future_eval | `docs/audit_pipeline_2026-09-13/AUDIT_KB_PARTIAL.md:3463` | **Replacement prompt 1 — 每锚深查 (exact; replaces `docs/CRON_TEMPLATES_2026-09-04.md` line 13 and live job 41df7caa at re-creation; cron `9 1,5 |
| CRON-14 | P2 | PENDING_USER_DECISION | live_trading, reporting | `docs/audit_pipeline_2026-09-13/AUDIT_KB_PARTIAL.json:revised_deep_check_prompt` | 以近 42 锚分布 p5–p95 为带 |
| CRON-03 | P3 | DOC_STALE | reporting | `docs/CRON_TEMPLATES_2026-09-04.md:16` | `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE |
| CRON-05 | P3 | DOC_STALE | live_trading | `docs/CRON_TEMPLATES_2026-09-04.md:16` | 三守护 PID 按内容验(shadow_loop_v3 run/sidecar_daemon.sh/combo_live_daemon.sh 进程在 + shadow.lock 与 fea171/combo_live_daemon.pid 句柄一致; E-0829-B 后 PID |
| CRON-07 | P3 | DOC_STALE | reporting | `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)` | net/gross 带内(±1%) |
| CRON-08 | P3 | VERIFIED_CURRENT | reporting | `docs/CRON_TEMPLATES_2026-09-04.md:16` | fund_updates 稳态: 4h整点~353 / 8h结算整点00·08·16Z~453 |
| CRON-09 | P3 | DOC_STALE | live_trading, reporting | `docs/CRON_TEMPLATES_2026-09-04.md:1` | **状态:** 在用 |
| CRON-10 | P3 | DOC_STALE | reporting, live_trading | `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)` | 实收 FUNDING_FEE(00/08/16Z 结算锚) |

### CRON-01 · P0 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16`
- **Quote:** 「整体回滚=kill combo_live_daemon.pid 内 PID」
- **Superseding evidence:**
  - `~/Library/LaunchAgents/com.hsy.combolive.plist (plutil -p)` — 「"KeepAlive" => { "SuccessfulExit" => false }」
  - `launchctl print gui/501/com.hsy.combolive (2026-09-13 14:0xZ)` — 「state = running … pid = 30944 … successful exit => 0」
  - `docs/RUNBOOK_wide_live_2026-08-22.md:36` — 「管理: launchctl {list|kickstart|unload} gui/$(id -u)/com.hsy.shadowloop 等; KeepAlive=异常退出自动拉起(演练受据 30942→30977)」
  - `docs/ERROR_LEDGER_2026-08-20.md:384` — 「4833 是 launchd `com.hsy.shadowloop`(KeepAlive)在 kill 后 ~1s 内重生的新进程」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:10` — 「  RESULT kill: RESPAWNED old=21206 new=21332 => kill is NOT a rollback」
  - `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log:15` — 「  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback」
  - `lead transcript b9646a9e….jsonl line 20039 (CronCreate 2026-09-09T00:24:05Z, job 41df7caa)` — 「prompt sha256 72868066f099ea29 = CRON_TEMPLATES line 13 sha256 72868066f099ea29 (byte-identical)」
- **A reader could wrongly conclude:** Killing the daemon PID rolls the book back to the king form.
- **Affects:** live_trading · **Severity reason:** The deep-check's anomaly-handling step names a rollback that launchd undoes; the operator following it during an incident leaves combo writing target_live.
- **Proposed correction (exact text):** ⑥ 异常处置: 回滚缺省=king 形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`; **整体回滚(临时)= `launchctl bootout gui/$(id -u)/com.hsy.combolive`**(08-30 起 launchd KeepAlive, kill PID 会 1 s 内被拉起, 不是回滚; 同形哑任务演练收据 `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log`)⇒ 下一锚起 king 三腿形态; 持久回滚(跨重登)再加 `launchctl disable gui/$(id -u)/com.hsy.combolive`; 恢复 = `launchctl enable gui/$(id -u)/com.hsy.combolive` + `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`; 执行后核 `launchctl print gui/$(id -u)/com.hsy.combolive` 与下一锚 target_live producer
- **Confidence:** VERIFIED on a dummy launchd job with the same plist shape (lead drill2 receipt, 2026-09-13T14:47:46Z: kill → respawn within 1 s; bootout → no process, no respawn for 15 s; bootstrap restores); not exercised on the live combolive job · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-02 · P2 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16` · xref CHK-01
- **Resolution:** XREF AUDIT_EXEC CHK-01 / AUDIT_PROD PROD-26 — CROSS-REF: the stale 19–20% rewrite baseline is owned by AUDIT_EXEC CHK-01; AUDIT_PROD PROD-26 confirms the level (11/11 values) and attributes the rise to the V2MAIN chain moving away from the king book. ⚠ This row's proposed 42-anchor p5–p95 band is NOT ADOPTED — see CRON-14.
- **Quote:** 「反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级)」
- **Superseding evidence:**
  - `STATE.md:29` — 「**反事实改写 27.46% 连升, 同期 rho_kc_fc 0.9349 → 0.9202 下行」
  - `STATE.md:47` — 「**反事实改写 26.58%: 连续第三锚 >+0.2pp = 达到升级判据, 但书空仓, 记待验证」
  - `STATE.md:163` — 「掩码 king 席位 0.1878 → **0.2999**(w3 [0.264, 0.1195, 0.6164])」
- **A reader could wrongly conclude:** Rewrite above 20% is an anomaly.
- **Affects:** live_trading, reporting · **Severity reason:** The baseline predates the 09-05 seat seeding that structurally raised the king slot; the escalation rule fired repeatedly with no defined action.
- **Proposed correction (exact text):** 反事实改写幅度(target_live_king vs target_live): 基线随 king 席位变化, 09-13 前后 ≈25–27%(席位 0.38); 判据 = 相对近 42 锚分布的 p95 越界或连续 3 锚增量 > +0.5pp; 触发即写 STATE 并归因到席位/FTRIM 名数/rho_kc_fc 三项之一
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-04 · P2 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16` · xref CHK-03
- **Resolution:** XREF AUDIT_EXEC CHK-03 — CROSS-REF: the stale maker ≥90% baseline is owned by AUDIT_EXEC CHK-03; X-COST fdee4894 supplies the current level. ⚠ This row's proposed per-arm split of maker share and fee bps is NOT ADOPTED (blinding) and its 42-anchor band is NOT ADOPTED — see CRON-13 / CRON-14.
- **Quote:** 「fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带)」
- **Superseding evidence:**
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:305` — 「Maker share by notional stayed above 0.90 through 09-02 and has run 0.56-0.89 per anchor since 09-08.」
  - `STATE.md:75` — 「maker 占比 0.816→**0.665**, 费 2.55→**3.01 bps**」
  - `STATE.md:78` — 「maker 占比 0.843 / 费 2.47 bps 回向带内但第七锚带外」
- **A reader could wrongly conclude:** Maker share below 90% or fees above 2.3 bps are anomalies.
- **Affects:** reporting, future_eval · **Severity reason:** Bands predate the chase restart (09-01) and requote direct arm (09-05); every anchor now reads out of band, so the check no longer separates normal from abnormal.
- **Proposed correction (exact text):** fills maker 占比与费用 bps: 按臂拆读(chase / no_chase, requote / direct), 以 09-08 起 42 锚分布 p5–p95 为带(09-13 前后 maker 0.56–0.89); 换手(稳态 2–5.5%); 带外连续 3 锚才升级
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-06 · P2 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16` · xref CHK-05
- **Resolution:** XREF AUDIT_EXEC CHK-05 — CROSS-REF: 'the template predates several live mechanisms' is owned by AUDIT_EXEC CHK-05. The added checks are carried forward as PROPOSALS (b)–(g) in the 2026-09-16 template, not as adopted policy.
- **Quote:** 「phase_C anchors_row+readback+per_name_stop」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md:31` — 「**已停的多头仓位不会被平到 0**」
  - `STATE.md:10` — 「**W9**(实盘逐名止损不把被止损名平到 0; 上线以来 157 例, 不限多头)」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:58` — 「| E4 ⊕ EXE-02 | 执行器 | 追加事实: 自 09-01 起止损 / 全退出残差经 chase 臂发 MARKET reduce-only(9 笔成交约 5,670 USDT); W9 扩大该通道 | P2 |」
  - `STATE.md:79` — 「**每锚深查固定加一项: 运行树 HEAD vs origin/main, 落后 = 未部署, 照常报不动作。**」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:95` — 「| CHK-05 | per-anchor deep check / coverage | The deep-check template predates several live mechanisms and misses their checks |」
- **A reader could wrongly conclude:** A deep check that passes all seven steps means the live stop and flatten paths are healthy.
- **Affects:** live_trading, reporting · **Severity reason:** The template checks per_name_stop presence but not that stopped names reach zero (the W9 defect ran 08-20..09-12 unseen), and omits precursors of both recent whole-book flattens (E-0909-G orders-row gap, E-0912-A reduce-only identity) plus the tree-vs-origin rule STATE added.
- **Proposed correction (exact text):** ④ 记账 追加: (a) per_name_stop: 列 stopped 名当锚 readback 数量, 已停且持仓 ≠ 0 的名逐一报桶(flatten_only / add_blocked / reduced)与是否走 chase MARKET reduce-only; (b) 本锚 request_ledger 四类标记与 capacity_conflict / reduce-only 截量 UNKNOWN 事件数(E-0912-A); (c) 本 rid orders.jsonl 行数 > 0(E-0909-G); (d) `git -C ~/dl_quant_live rev-list --count HEAD..origin/main` = 0 否则报「未部署」; (e) apiTradingStatus 与 −4400/−2027 计数(E-0910-A / E-0909-E); (f) 当日 daily_nav external_flow ≠ 0 时标注日损守卫盲区; (g) 读 `~/regime_dash/regime_dash.jsonl(追加式, 按 `anchor_utc` 取 `w3_masked_king`/`w3_masked_fund`; 滚动的 `REGIME_DASH.md` 每锚被整份重写, 不可作收据 —— DEV-14)` 席位/FTRIM 名单/旗标 【DEV-14 补注 2026-09-16】逐锚可复核值: 2026-09-13T12:00Z king 0.3821 / fund 0.6179 · 2026-09-16T00:00Z king 0.3780 / fund 0.6220; 日志覆盖 2026-09-02T08:00Z 起。
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-11 · P2 · DOC_STALE
- **Source:** `lead transcript b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0.jsonl:20043 (CronCreate 2026-09-09T00:24:21Z, job 4a2f33e3, `52 14 * * *` local, session-only, auto-expires ≈2026-09-16T00:24Z)`
- **Quote:** 「然后 git add/commit(无新增则不提交)」
- **Superseding evidence:**
  - `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md:56` — 「研究仓在 iCloud 桌面, 提交一律显式 pathspec。」
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:12` — 「提交显式 pathspec 并核 `git show --name-only`」
- **A reader could wrongly conclude:** A daily log commit only contains the forward-log files.
- **Affects:** reporting, future_eval · **Severity reason:** The daily job commits without an explicit pathspec in a repository where many agents stage files concurrently, so it can sweep unrelated staged changes into a 'parabolic_onset_forward' commit.
- **Proposed correction (exact text):** 见 §CRON 替换提示词(抛物线日志): 仅在有新增时 `git -C … add -- <events.jsonl> <run_log.jsonl>` 后 `git -C … commit -m "…" -- <events.jsonl> <run_log.jsonl>`, 提交后 `git show --name-only HEAD` 核只含这两个文件
- **Confidence:** VERIFIED (prompt text from the lead transcript tool_use input; job id and expiry from the tool_result) · **Quote re-verified at assembly:** exact (lead transcript tool_use input, extracted by script)

### CRON-12 · P2 · OPEN_NOT_MEASURED
- **Source:** `lead transcript b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0.jsonl:20043 (CronCreate 2026-09-09T00:24:21Z, job 4a2f33e3, `52 14 * * *` local, session-only, auto-expires ≈2026-09-16T00:24Z)` · xref DEV-08
- **Quote:** 「当 P 层 θ8 已填事件 ≥ 200 且距 2026-09-06 ≥ 14 天时, 向用户报"可复判", 复判按 PREREG_crash_continuation_parabolic_stratum §2 六条另起。」
- **Superseding evidence:**
  - `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py:12` — 「data (T, 829, 7) float16 with channels [ret5, rng, cpos, lqv, lcnt, lasz, tbf] and clips CHN_CLIPS — identical to the pod ext cache used by the」
  - `~/wide_shadow/shadow_loop_v3.py:150` — 「CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]」
- **A reader could wrongly conclude:** At 200 events the forward log is a valid accounting-caliber sample for the re-judgement.
- **Affects:** future_eval · **Severity reason:** The job will announce the only surviving tail lead as ready for re-judgement on forward values recomputed from the clipped float16 cache (DEV-08), with no caliber warning.
- **Proposed correction (exact text):** 当 P 层 θ8 已填事件 ≥ 200 且距 2026-09-06 ≥ 14 天时, 向用户报「计数已达复判门, 但前向值取自裁剪(±0.30)float16 缓存口径(AUDIT_KB DEV-08); 复判前须先按记账口径(未裁剪原始收盘价)重算 onset 与前向收益, 或预注册该口径偏差的处理」; 复判按 PREREG_crash_continuation_parabolic_stratum §2 六条另起。
- **Confidence:** VERIFIED for the prompt text and code path; magnitude of the clip effect not measured · **Quote re-verified at assembly:** exact (lead transcript tool_use input, extracted by script)

### CRON-13 · P2 · DOC_STALE
- **Source:** `docs/audit_pipeline_2026-09-13/AUDIT_KB_PARTIAL.md:3463`
- **Quote:** 「**Replacement prompt 1 — 每锚深查 (exact; replaces `docs/CRON_TEMPLATES_2026-09-04.md` line 13 and live job 41df7caa at re-creation; cron `9 1,5,9,13,17,21 * * *` local, recurring):**」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:219` — 「替换版深查提示词内含**未获批准的新监控/解盲政策**(42 锚阈值 · placement 分臂读数), 且须与 CFG-06「没有看过分臂结果」声明对齐」
  - `docs/fixprogram_2026-09-13/X_COST/PREREG_placement_eps050_reread_2026-09-16.md:101` — 「自本修订起至 §3 读数产出前, 每锚深查与飞行日志**只报臂平衡**(各臂计数、behind 占比、必要时逐臂残差名义作成本上界), **不报任何逐臂结果量**(拒单率 / 成交率 / markout / 成本 / 价差)。」
  - `docs/fixprogram_2026-09-13/X_COST/PREREG_placement_eps050_reread_2026-09-16.md:99` — 「用户的深查模板原文只要求「`chase_arm_assigned` 分臂计数, placement behind 占比≈0.50」= **臂平衡**, 原 PREREG(f657efde)明确允许「监控只看成本上界与臂平衡」。**逐臂拒单率是我方日志在模板之外自行加的**, 属越界。」
  - `docs/AMENDMENT_1_chase_restart_population_2026-09-16.md:26` — 「到停止点读数产出前, 每锚深查与飞行日志**只报臂平衡与成本上界**, **不得报任何逐臂结果量**(逐臂成交价差 / markout / 净成本 / H 或 X 的任何形式)。」
- **A reader could wrongly conclude:** The per-anchor log accumulates per-arm fill-rate and cost readings before the CFG-06 stop point, so the frozen readout is taken on a population the operator has already seen split by arm — the same over-reach that forced W0 to move to the freeze moment.
- **Affects:** live_trading, future_eval · **Severity reason:** This register's own replacement template instructs the deep check to read maker fill share and fee bps split by chase / requote / placement arm, which is exactly the per-arm outcome quantity that CFG-06 AMENDMENT 1 and CFG-04 AMENDMENT 1 forbid until the readout; adopting it would have written new unblinding into a recurring job.
- **Proposed correction (exact text):** [原字节保留; 本行判词改为] **NOT ADOPTED — 已由 2026-09-16 修订版取代**(受据: 独立复审 FXR-KB-1 · CFG-06 冻结版 AMENDMENT 1 §「收紧」· CFG-04 AMENDMENT 1 §前向盲态)。原草案 ③ 的「maker 成交占比与费用 bps **按臂拆读**(chase / no_chase, requote / direct, placement join / behind)」与 CRON-04 建议里的同句**逐臂结果量**一律删除; 前向只保留**臂平衡**: `chase_arm_assigned` 各臂计数 · placement behind 占比 ≈0.50 · 必要时逐臂**残差名义**作成本上界。maker 份额与费 bps **只报书级合计**(≈74–78% / ≈2.4–2.7 bps, X-COST fdee4894); −5022 首拒率**只报合计, 不分臂**。修订版全文见 AUDIT_KB §CRON「替换提示词 1(2026-09-16 修订版)」, 结构与在役 cron a84f2bd4 同(用户模板逐字 + 更正附注)。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** exact (line moved 3457->3463)

### CRON-14 · P2 · PENDING_USER_DECISION
- **Source:** `docs/audit_pipeline_2026-09-13/AUDIT_KB_PARTIAL.json:revised_deep_check_prompt`
- **Resolution:** Source is a JSON field, not a file line: `AUDIT_KB_PARTIAL.json::revised_deep_check_prompt` (committed 0e88892f). The quoted string 「以近 42 锚分布 p5–p95 为带」 occurs twice in that field (counterfactual-rewrite band and maker/fee band) and was verified present by substring at assembly.
- **Quote:** 「以近 42 锚分布 p5–p95 为带」
- **Superseding evidence:**
  - `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:219` — 「替换版深查提示词内含**未获批准的新监控/解盲政策**(42 锚阈值 · placement 分臂读数)」
  - `docs/CRON_TEMPLATES_2026-09-04.md:16` — 「判据=level 再升一档或连续3锚增量>+0.2pp 才升级」
- **A reader could wrongly conclude:** A self-referencing band: whatever the last 42 anchors did becomes normal, so a slow structural drift never escalates, and the user's own +0.2pp criterion disappears without a ruling.
- **Affects:** live_trading, reporting · **Severity reason:** The draft replaced the user's frozen escalation criterion (+0.2pp over 3 anchors, level step) with a rolling 42-anchor p5–p95 band and a +0.5pp step, in two places; that is a new monitoring policy authored by the auditor, not a correction of a wrong fact, and it silently widens what counts as normal.
- **Proposed correction (exact text):** [标为提案, 不进 cron] **PROPOSAL, NOT ADOPTED(FXR-KB-1)**。在 cron 内**只作事实更正**: ② 反事实改写基线由「09-03 08Z 起 19–20%」更正为「**≈25–27%**(09-13 16Z 实测 27.90%, 随 king 席位滚动)」, **判据仍用用户原文**(level 再升一档 或 连续 3 锚增量 > +0.2pp); ③ maker 份额 / 费 bps 由「≥90% / 1.80–2.3 bps」更正为「**≈74–78% / ≈2.4–2.7 bps**(X-COST fdee4894 分解: 93.1253% → 73.9049%)」, **不设新带、不设新升级规则**。另行随复审包上交用户的提案(**未获批准前不得写入 cron**): (a) 以近 42 锚 p5–p95 作动态带; (b) 升级步长 +0.2pp → +0.5pp; (c) 带外连续 3 锚才升级。三项均属书/监控行为改动, 须用户裁定。
- **Confidence:** VERIFIED (quote+receipt opened) · **Quote re-verified at assembly:** None

### CRON-03 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16` · xref CHK-02
- **Resolution:** XREF AUDIT_EXEC CHK-02 — CROSS-REF: 'guard_twin AGREE is looked up in the wrong file' is owned by AUDIT_EXEC CHK-02.
- **Quote:** 「`~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE」
- **Superseding evidence:**
  - `~/guard_twin/state/latest.json (2026-09-13T13:46:30Z)` — 「"status": "AGREE(ledger-only; nav row stale)", "comparable": false」
  - `grep -c 'guard_twin\|AGREE' ~/dl_quant_live/state/anchor_runs.log` — 「0」
- **A reader could wrongly conclude:** anchor_runs.log carries the guard_twin verdict.
- **Affects:** reporting · **Severity reason:** The verdict is not in the file the step reads.
- **Proposed correction (exact text):** `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0; guard_twin 读 `~/guard_twin/state/latest.json`(status / comparable / disagreements)+ alerts.log
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-05 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16`
- **Quote:** 「三守护 PID 按内容验(shadow_loop_v3 run/sidecar_daemon.sh/combo_live_daemon.sh 进程在 + shadow.lock 与 fea171/combo_live_daemon.pid 句柄一致; E-0829-B 后 PID 会变, 以句柄文件为准)」
- **Superseding evidence:**
  - `docs/RUNBOOK_wide_live_2026-08-22.md:34` — 「★ 2026-08-30 起三守护已 launchd 化(E-0829-B 修复, 重启+崩溃双自愈; 上行 nohup 命令仅作应急后备)」
  - `launchctl list (2026-09-13)` — 「10900 -15 com.hsy.shadowloop · 30944 0 com.hsy.combolive · 30943 0 com.hsy.sidecar」
- **A reader could wrongly conclude:** Process presence plus handle files proves the daemons are healthy.
- **Affects:** live_trading · **Severity reason:** Handles still match, but the authority is launchd; a respawn loop or a disabled job is invisible to a PID-handle check.
- **Proposed correction (exact text):** ① date -u + `launchctl print gui/$(id -u)/com.hsy.{shadowloop,combolive,sidecar}` 的 state / pid / runs / last exit code(runs 增长 = 被重启); 句柄文件只作交叉核对; 另核 `launchctl print-disabled` 中 com.hsy.sigma_ladder 仍 disabled
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-07 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)`
- **Quote:** 「net/gross 带内(±1%)」
- **Superseding evidence:**
  - `STATE.md:76` — 「**口径更正: 08Z 报的「net/gross 逼近 1.5% 动作带」有误 —— 该判据用补单前 book_net(本锚 −0.952%, 带内), 非 readback 后 net/gross(−1.30%)。**」
- **A reader could wrongly conclude:** Readback net/gross beyond ±1% approaches the executor's neutrality action.
- **Affects:** reporting · **Severity reason:** The template does not name the quantity; the executor's 1.5% band acts on pre-top-up book_net, and a 09-11 report compared the wrong one.
- **Proposed correction (exact text):** net/gross: 分列 (i) 补单前 book_net(执行器 1.5% 中性带的判据量)与 (ii) readback 后 net/gross(观察带 ±1%), 不得互换
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-08 · P3 · VERIFIED_CURRENT
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16` · xref CHK-04
- **Resolution:** XREF AUDIT_EXEC CHK-04 — CROSS-REF: fund_updates baselines still hold — AUDIT_EXEC CHK-04 agrees (VERIFIED_CURRENT in both registers).
- **Quote:** 「fund_updates 稳态: 4h整点~353 / 8h结算整点00·08·16Z~453」
- **Superseding evidence:**
  - `~/wide_shadow/shadow_log.jsonl last 30 signal rows (read 2026-09-13 14:0xZ)` — 「fund_updates alternates 354/454 (355/454, 358/457, 461 at most)」
  - `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:94` — 「| CHK-04 | per-anchor deep check / baseline | fund_updates baselines (~353 / ~453) still hold |」
- **A reader could wrongly conclude:** (none)
- **Affects:** reporting · **Severity reason:** Baseline still holds; recorded so a reader does not treat it as stale with the rest.
- **Proposed correction (exact text):** (无需改动)
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

### CRON-09 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:1`
- **Resolution:** XREF AUDIT_EXEC CHK-05 — CROSS-REF: template-document status line; owner AUDIT_EXEC CHK-05.
- **Quote:** 「**状态:** 在用」
- **Superseding evidence:**
  - `lead transcript tool_result line 20040` — 「Scheduled recurring job 41df7caa (9 1,5,9,13,17,21 * * *). Session-only (not written to disk, dies when Claude exits). Auto-expires after 7 days.」
  - `docs/CRON_TEMPLATES_2026-09-04.md:13` — 「| jpline 每 2 小时重连 | `23 */2 * * *` | true(用户 09-05 令恢复; prompt 逐字见本文末) |」
  - `STATE.md:182` — 「**jpline 重连定时已按用户字停止(09-06 05:4xZ)。**」
  - `docs/CRON_TEMPLATES_2026-09-04.md:11` — 「| combo 84 锚前向门二读 | `57 12 9 9 *` | false |」
- **A reader could wrongly conclude:** The deep-check template is current and the jpline and 84-anchor jobs should be recreated on the next restart.
- **Affects:** live_trading, reporting · **Severity reason:** The template text is unchanged since 09-05 (live job 41df7caa is byte-identical) and the job auto-expires 2026-09-16 ~00:24Z; the doc still lists the stopped jpline job and the completed 84-anchor read as in use.
- **Proposed correction (exact text):** **状态:** 每锚深查模板待按 CRON-01..07 修订后重建(现 job 41df7caa 自 2026-09-09T00:24Z 起, 会话级 7 天自动过期 ≈2026-09-16T00:24Z); jpline 2h 重连 = 09-06 按用户字停止; combo 84 锚二读 = 09-09 已完成(判据① 不过), 下一窗归用户; 口径复核工作流 = 09-05 已收口
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact

### CRON-10 · P3 · DOC_STALE
- **Source:** `docs/CRON_TEMPLATES_2026-09-04.md:16 (+1 more)`
- **Quote:** 「实收 FUNDING_FEE(00/08/16Z 结算锚)」
- **Superseding evidence:**
  - `STATE.md:55` — 「12Z 对 188 个 4h 结算名是结算锚」
  - `~/regime_dash/REGIME_DASH.md:9 (2026-09-13T12:50Z)` — 「| 短周期名占比 | 0.775 | >=p95 |」
- **A reader could wrongly conclude:** Funding is only paid on 00/08/16Z anchors.
- **Affects:** reporting, live_trading · **Severity reason:** Most book names now settle on 4h or 1h intervals; checking realised funding only on 00/08/16Z misses most settlements.
- **Proposed correction (exact text):** 实收 FUNDING_FEE: 每锚按名的当前结算间隔核(4h/1h 名每锚或锚内结算, 8h 名 00/08/16Z), 与 fundingInfo 间隔一并记录
- **Confidence:** VERIFIED (quote and receipt opened) · **Quote re-verified at assembly:** exact (line moved 13->16)

**K5 status (2026-09-16).** The 2026-09-13 draft replacement template is **NOT ADOPTED** (CRON-13 / CRON-14, receipt: independent review FXR-KB-1). Its original bytes are preserved in the committed `AUDIT_KB_PARTIAL.md` §CRON and are not reprinted here. Two things were wrong with it, and they are different kinds of wrong:
- **A blinding violation.** It told the deep check to read maker fill share and fee bps **split by chase / requote / placement arm**. CFG-06 frozen AMENDMENT 1 §「收紧」 and CFG-04 AMENDMENT 1 §前向盲态 both forbid any per-arm *outcome* quantity (reject rate, fill rate, markout, cost, spread) until the CFG-06 readout; only **arm balance** is allowed (per-arm counts, behind share ≈0.50, per-arm residual notional as a cost upper bound). The user's own template already asked for exactly the allowed quantities — the split was the auditor's addition, the same over-reach that put 8 historical per-arm readings into the anchor logs and moved W0 to the freeze moment.
- **Unapproved new monitoring policy.** It replaced the user's frozen escalation criterion (+0.2pp over 3 anchors, or a level step) with a rolling 42-anchor p5–p95 band and a +0.5pp step, in two places. That is not a correction of a wrong fact; it is a policy the user never ruled on, and a self-referencing band means a slow structural drift never escalates. It is carried below as a **proposal**, outside the cron.
**The 2026-09-16 replacement below therefore has the same shape as the live cron `a84f2bd4`: the user's template verbatim, plus a 「lead 更正附注」 block.** The annex only (a) corrects facts that are wrong and carries their receipt, (b) restates the blinding rule verbatim, (c) names known live false positives and the deployment status, and (d) parks everything that would be new policy in an explicit proposals item that the cron does not execute. Proposals (b)–(f) in item ⑩ each close a live blind spot that nothing currently guards, so they are the ones worth ruling on first.

**Replacement prompt 1 — 每锚深查 (exact; replaces `docs/CRON_TEMPLATES_2026-09-04.md` line 13 and live job 41df7caa at re-creation; cron `9 1,5,9,13,17,21 * * *` local, recurring):**

```text
**结构 = 在役 cron a84f2bd4 同构: 用户模板逐字(`docs/CRON_TEMPLATES_2026-09-04.md` L13, 一字不改)+ 下面这一块「lead 更正附注」。附注只更正事实与补盲态, 不改用户的任何判据。**

—— lead 更正附注(2026-09-13 / 2026-09-16 受据; 深查只读, 实盘书零接触)——

**〇 盲态条(最高优先, 逐字取自 CFG-06 冻结版 AMENDMENT 1 与 CFG-04 AMENDMENT 1)**: 到 CFG-06 §3 读数产出前, 分臂**只报臂平衡**(各臂计数 / behind 占比 / 必要时逐臂**残差名义**作成本上界), **不报任何逐臂结果量**(拒单率 / 成交率 / markout / 成本 / 价差 / H 或 X 的任何形式)。用户模板 ③ 原文要求的「`chase_arm_assigned` 分臂计数, placement behind 占比≈0.50」**就是**臂平衡, 照做; **不得**在其上自行追加逐臂拆读。maker 份额、费 bps、−5022 首拒率**一律只报书级合计**。安全线 SL1/SL3 照评, 但只输出布尔与触发日, 不附逐臂数值。

**① 守护进程的权威是 launchd, 不是 PID 句柄**(同 ⑥ 的 08-30 KeepAlive 事实): 用 `launchctl print gui/$(id -u)/com.hsy.{shadowloop,combolive,sidecar}` 读 state / pid / runs / last exit code —— **runs 较上锚增长 = 被重启过**, 报; 句柄文件(shadow.lock、fea171/combo_live_daemon.pid)降为交叉核对。另核 `launchctl print-disabled gui/$(id -u)` 中 `com.hsy.sigma_ladder` 仍 disabled(OPS-01 退役, 6cc95943)、`com.hsy.execprobe2` 仍 disabled(OPS-02 退役, b63a0144)。

**② 反事实改写幅度的基线数字更正**: 模板写「09-03 08Z 起新台阶 19–20%」已陈旧 —— 该幅度随 king 席位滚动, **现水平 ≈25–27%**(09-13 16Z 实测 **27.90%**; 归因 = V2MAIN 链离开 king 书, AUDIT_PROD PROD-26 11/11 值)。**判据不变, 仍用用户原文**: level 再升一档, 或连续 3 锚增量 > +0.2pp 才升级。越界时把归因写清(席位 / FTRIM 名数 / rho_kc_fc 三者之一)。

**③ maker 份额与费用带的基线数字更正**: 模板写「maker ≥90% / 费 1.80–2.3 bps」已陈旧 —— **现水平 maker ≈74–78%, 费 ≈2.4–2.7 bps**(X-COST fdee4894 桶恒等分解 93.1253% → 73.9049%, −19.2204 pp; 驱动 = requote 实验 direct 臂 + chase 实验臂 + 存款后 chase_forced + from_reject)。**只报合计**(见〇)。换手稳态 2–5.5% 不变。⚠ 引用 X-COST 时按 FXR-DOC-2: 「执行成本侧没有隐藏缺陷」一句**已作废**, 11.3831 pp 依赖可交换性假设(不作该假设时 [−0.4178, +15.5642] pp), chase 4.3531 / forced 2.4401 pp 是**已成交桶份额**非反事实, 首拒 −5022 由 14.3% → 23.0% 的原因**未测**。

**④ guard_twin 判词读对文件**: 模板的「guard_twin AGREE」不在它读的那个文件里 —— 判词读 `~/guard_twin/state/latest.json` 的 `status` / `comparable` / `disagreements`, 明细读 `~/guard_twin/state/compare.jsonl`, 告警读 `~/guard_twin/state/alerts.log`; **只有 `comparable=true` 且 `disagreements` 为空才记 AGREE**。

**⑤ 实收资金费按名的当前结算间隔核**: 模板的「实收 FUNDING_FEE(00/08/16Z 结算锚)」会漏掉大多数结算 —— 书内多数名现为 4h / 1h 间隔, 每锚(或锚内)结算, 只有 8h 名落在 00/08/16Z。逐锚按名的当前 `fundingInfo` 间隔核, 并把间隔一并记录(P9: 间隔切换行会把 rn 放大 2–4×)。

**⑥ net/gross 必须点名是哪个量**: 模板的「net/gross 带内(±1%)」没说是哪一个。分两列报, **不得互换**: (i) **补单前 `book_net`** = 执行器 1.5% 中性带的判据量; (ii) **readback 后 net/gross** = 观察带 ±1%。

**⑦ 回滚动词(P0, 与 STATE §1 同, b63a0144 已更正)**: 回滚缺省 = king 形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(E-0904-A, 禁 nohup 裸 env); **整体回滚(临时)= `launchctl bootout gui/$(id -u)/com.hsy.combolive`** —— 08-30 起 combo 守护由 launchd KeepAlive 管理, **`kill $(cat …/combo_live_daemon.pid)` 会在 1 s 内被拉起, 不构成回滚**(同形哑任务演练收据 `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log`; 第 1 次 3 s 演练读「未重生」是错的, 收据保留标错)。持久回滚(跨重登)再加 `launchctl disable gui/$(id -u)/com.hsy.combolive`; 恢复 = `launchctl enable …` + `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`; 执行后核 `launchctl print gui/$(id -u)/com.hsy.combolive` 与下一锚 target_live 的 producer 字段。

**⑧ 已知实盘假阳性(见到即按仪器处理, 不得触发全书级动作)**: E9 `NO_PRODUCER` 产物断言误报 · EXE-03 / PROD-25 reshape 去均值把小空头翻多(109 个 combo 锚中 99 个)后「撤名残差」告警归错因 · E-0912-A reduce-only 截量 × 身份核对 1e-6 假阳性 · E-0909-G 账本缺口触发的逐名门。**用户规则**: 仪器疑问不得触发全书级响应(`feedback_no_book_level_response_to_instrument_doubt`); 在役看门狗**任何触发仍整书平仓**(EXE-01, 比例响应在克隆未部署)。

**⑨ 部署状态(每次深查都要说)**: 本修复纲领**没有任何修复已部署**, 执行器运行树仍 `ef60f85`; 深查**只读**, 不动任何实盘文件、不改配置、不发信号给在役 PID。核 `git -C ~/dl_quant_live rev-parse --short HEAD` 并报, 与 origin/main 不一致时**照报不动作**。

**⑩ 观察并报告(lead 2026-09-16 裁定: 五条只读观察项, 不改任何判据、不触发任何动作, 故不属「未经批准的新政策」)**: (b) `per_name_stop` **已停名当锚 readback 是否归零** —— 已停且持仓 ≠ 0 的名逐一报桶(flatten_only / add_blocked / reduced)(W9 缺陷 2026-08-20..09-12 无人看见); (c) 本 rid `orders.jsonl` **行数 > 0**(E-0909-G: 缺行触发过逐名门); (d) `request_ledger` 四类不一致标记与 **capacity_conflict / reduce-only 截量 UNKNOWN 事件数**(E-0912-A 前兆); (e) `apiTradingStatus` 与 **−4400 / −2027 计数**(E-0910-A 场所量化规则锁 / E-0909-E 上限截断); (f) 当日 `daily_nav.external_flow ≠ 0` 时**标注日损守卫盲区**(提醒勿划转)。**五条只报数与名单, 不判、不动作、不升级。**

**⑪ 未获批准的提案(不在本 cron 内执行; 随复审包上交用户后才可加)**: (a) 反事实改写幅度改用近 42 锚 p5–p95 动态带; 升级步长 +0.2pp → +0.5pp; 带外连续 3 锚才升级 —— **三项都改的是判据, 属书/监控行为改动, 维持 NOT ADOPTED**(FXR-KB-1, CRON-14)。(g) 读 `~/regime_dash/REGIME_DASH.md` 的席位 / FTRIM 名单 / 旗标 —— 属新增读源, 待裁; **若采纳, 收据须取自追加式 `~/regime_dash/regime_dash.jsonl` 按 `anchor_utc`, 不取滚动的 .md**(DEV-14)。
```

**Replacement prompt 2 — 抛物线起始前向日志 (exact; replaces live job 4a2f33e3 at re-creation; cron `52 14 * * *` local, recurring):**

```text
**结构 = 在役 cron 同构: 用户文本逐字 + 下面这一块「lead 更正附注」。**

—— lead 更正附注(aud-kb CRON-11 / CRON-12; 只读研究, 实盘零接触, 不调 API)——

**① 提交必须带显式 pathspec(CRON-11)**: 用户文本的「然后 git add/commit(无新增则不提交)」在一个多代理并发暂存的仓库里会把别人的暂存改动扫进一次 `parabolic_onset_forward` 提交。改为: 仅在有新增时 `git -C /Users/haosiyu/Desktop/quant_research add -- multi_asset/exports/live/parabolic_onset_forward/events.jsonl multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl`, 然后 `git -C … commit -m "parabolic_onset_forward: 每日追加 <UTC 日期>" -- <同两个路径>`; 提交后 `git -C … show --name-only --format= HEAD` 核**只含这两个文件**, 否则报告不修; git 锁被占用则本日不提交并报告。**不得裸 `commit`, 不得静默 git stderr。**

**② 前向值的口径标注(CRON-12 / DEV-08)**: 本日志的 onset 与前向收益取自生产者 5m 缓存 `ret5` 通道(**float16, 硬裁 ±0.300048828125**, E-0908-B 同族), 一切读数标「**裁剪缓存口径, 尾部为下界**」。若本批新增事件的 onset 或前向窗内出现 |ret5| 顶到界的饱和格, 报其事件数(装置未输出则报「未测」)。**规则(r18)**: 任何装置不得从缓存 `ret5` 重算收益; 记账正典是未裁剪的 `meta_newprod_v4` y4 = Π(1+r)−1。

**③ 复判门: 原句逐字保留, 口径警告附在其后(CRON-12; lead 2026-09-16 裁定的形式要求 —— **不替换**, 只追加)**: 用户文本的「当 P 层 θ8 已填事件 ≥ 200 且距 2026-09-06 ≥ 14 天时, 向用户报『可复判』」**照原样报**, 紧接着**必须**附上: 「**但**前向值取自裁剪 ±0.30 的 float16 缓存口径(E-0908-B 同族), **尾部为下界**; 复判前须先按记账口径(未裁剪原始收盘价)重算 onset 与前向收益, 或预注册该口径偏差的处理」。读者先看到原判词, 再看到警告。复判仍按 `PREREG_crash_continuation_parabolic_stratum_2026-09-06` §2 六条另起。

**④ 盲态不变**: 累计读数**只报计数**(θ8 P 层已填前向事件数 / 距 200 门), **不看均值、不比 P 与 Q、不做 CI、不判**(门未到按设计保持盲态; r11_verdict §「唯一还活着、但门没开的 alpha 线索」)。运行失败(rc≠0 或断言)**只报不修**。
```

## §6 Cross-references to the other audits and the fix programme

**How de-duplication was done.** A finding that another register already owns stays in this register as a **cross-reference**, not a second copy: the row keeps its own quote and replacement text (which is what K4 applies), and its `resolution` field names the owning register and item. 40 rows are marked this way. Nothing was deleted — a reader arriving from the knowledge-base side must still find the row.
- **aud-exec (`AUDIT_EXEC`, 842bbffa)** — CFG-03 (live maker window is 900 s; 180 s never ran) owns KB-15, KB-44, M3-01, M1-07 · CFG-04 (chase 50/50 since 09-01, now frozen by `docs/AMENDMENT_1_chase_restart_population_2026-09-16.md`, 86c0227b) owns KB-02, KB-53, M3-02, M3-03 · CFG-06 (placement eps basis; now `PREREG_placement_eps050_reread_2026-09-16.md`) owns M3-08 · EXE-01 owns M3-44 · OPS-01 owns KB-13 · OPS-02 owns M3-40 · STA-03 / CFG-07 own M3-10, M3-12, M3-13, M3-14, M3-15 · LED-07 qualifies M3-42 · CHK-01 owns CRON-02 · CHK-02 owns CRON-03 · CHK-03 owns CRON-04 · CHK-04 agrees with CRON-08 · CHK-05 owns CRON-06, CRON-09. **AUDIT_EXEC DOC-01 is not a duplicate in the other direction**: FIXPROGRAM §3.1 routes its STATE / CLAUDE.md-side application to **K4 = this register**.
- **aud-train (`AUDIT_TRAIN`, 7e1ecf9a)** — TRN-24 (judge windows end 2026-08-31) owns DEV-01's window half; DEV-01's own finding, the (A) PROMOTE predicate with no equivalence band and no per-year condition, stays here and is PENDING_USER_DECISION · TRN-26 / TRN-27 (STEP1_m 79950786…, STEP2_m d99a9109…) own M1-03 · TRN-28 owns KB-08 · TRN-29 (export gate v2 APPLIED 2026-09-12T09:04:39Z, contract 1188267a) owns KB-61 · TRN-04 / TRN-05 (October recurrence of the column-80 split) own part of M1-01 and M1-02 · TRN-07 (October funding-interval recurrence) shares M3-27.
- **aud-data (`AUDIT_DATA`, bb8a2806)** — RET-02 (devices that still sum or compound the ±0.30-clipped ret5) owns KB-05's caliber half and adds the standing caveat to M3-06 and M3-07 · EVL-01 (33 files defaulting `CAL=simple`) owns KB-17 · FND-01 / FND-02 (x0910 pull-time settlement interval) own M3-27 with AUDIT_PROD PROD-40.
- **aud-prod (`AUDIT_PROD`, **ee2a8c4d** — not 57f7e2be; FIXPROGRAM §11 corrects that citation)** — PROD-04 / PROD-37 (column 80 trained v0, served v1) own the mechanism behind M1-01 · the train/serve parity family PROD-01/02/03/06 bounds M1-02 · PROD-26 confirms CRON-02's level (11/11 values) · PROD-33 (CLAUDE.md N+23 vs executor N+24) owns KB-03 / KB-11, both **applied by the lead on 2026-09-16** (KB-71) · PROD-40 shares M3-27. **⚠ Five of this register's ids are now double-booked by FIXPROGRAM §13.1 — see KB-69.**
- **FIXPROGRAM / FX-EVAL K2 (`RELABEL_TABLE_K2.md`, d0b087db / 99a6cd27, sha256 5bba5e75…)** — this register adopts K2's vocabulary instead of inventing labels: T4 NOT MATERIAL → INCONCLUSIVE (KB-41, KB-48, DEV-04, and M1-01 / M3-27 softened accordingly) · T5c / T5d → SHARED LOSS, DIFFERENCE INCONCLUSIVE (DEV-05, DEV-06) · T5b primary NOT MATERIAL stands, secondary MATERIAL → INCONCLUSIVE (KB-49, DEV-07) · T8 → FAIL: failed to detect, usefulness not excluded (DEV-10, and M3-11 softened) · 「(C) 不可区分」 → (C) INCONCLUSIVE (KB-14, which adds STATE.md to K2's six-document list) · KB-37 adopts K2 for 「部署差不是主因」.
- **Independent review (Codex QNT-2026-0907, `docs/REVIEW_fixprogram_progress_2026-09-14.md`, 9f6384fb)** — **FXR-KB-1** (the 2026-09-13 draft deep-check template carried an unapproved 42-anchor threshold and per-arm placement readings) is registered as CRON-13 and CRON-14, both NOT ADOPTED; the 2026-09-16 replacement below matches the live cron `a84f2bd4` and the blinding rule frozen with CFG-06 · **FXR-DOC-3** (the Sharpe window binding) is registered as KB-63..KB-68 · **FXR-DOC-2** (X-COST's 「执行成本侧没有隐藏缺陷」 withdrawn) is carried into the replacement template's ③.

## §7 Not checked

- ERROR_LEDGER: only §A–§E index and entries E-0902-D, E-0904-C/E/F were read line by line; the other ~60 entries (E-0821-A … E-0912-B) were not re-verified against later receipts.
- STATE.md dated entries at lines 13–122 (09-06 … 09-12) were keyword-searched (composition, seat, k window, ladder, rollback, rewrite, maker share, cron) but not read line by line; §2 in-flight items were skimmed. The 2026-09-16 entries added after the restart were read only where they touch a registered row (N+23→N+24, PROD-30).
- Memory notes not linked from MEMORY.md (~139 of 401 files). The M4 sweep now covers all 45 notes it was assigned plus 3 unlisted ones; the glob families named in MEMORY.md (`wide_book_*`, `ma_v2_*`, `factory_*`, `engine_*`, `v4_*`, `single_asset_*`, `y600_*`) are still only spot-checked.
- Documents routed from CLAUDE.md or STATE.md but outside the assigned list: docs/TEAM_PROTOCOL.md, docs/MILESTONE_2026-08-11.md, docs/PREREG_leg_ablation_2026-08-26.md (RECONCILIATION), docs/ONBOARDING_independent_researcher_2026-09-06.md (flagged via memory row M5-10 only), docs/CALIBER_STATUS_2026-09-09.md, uplift CANONICAL_NUMBERS / DOCKET_r7 / RULINGS_OUTSTANDING (read only where cited, plus §0-3/§0-5/§1.3 for FXR-DOC-3).
- T2/T3/T7/L2/L3/L4 results were read at their §0 summaries; FAMILY_T6.md beyond grep; the reviewer's round-4 sub-reports (`codex_round4_code_review_2026-09-13/{research,retrain,incident}/RESULT.md`).
- Gate libraries `v4_gate_common.py`, `v4_gate_step1_m.py`, `v4_gate_step2_m.py`, `v4_gate_closure.py`, `v4_leakcheck.py`, `v4e_gate_{export_v2,parity,quant}.py` were not read line by line; the predicate audit relies on judge_v4.py (read fully), the FX-EVAL K2 fact table and AUDIT_TRAIN.
- regime_dash historical percentile baseline `regime_hist_pct.json` (jpline B panel 2023+) was not traced to its panel or funding normalisation; ic_monitor, daily_summary, anchor_report and markout readers were left to aud-exec. `regime_dash.jsonl` covers only 2026-09-02T08:00Z → 2026-09-16T00:00Z (83 rows), so seat readings earlier than 09-02 have no durable receipt here (DEV-14).
- No live or research job was run to confirm INFERRED runtime behaviour, e.g. that launchd respawns the combo daemon after a kill (plist, launchctl state and the lead's 09-13 drill2 receipt only), or the depth-watch alert rate.
- The live deep-check cron could not be listed from this context (CronList returns no jobs here). The replacement template was written against the *committed* description of job `a84f2bd4` in FIXPROGRAM §12.5 and the blinding text in `PREREG_placement_eps050_reread_2026-09-16.md` §AMENDMENT 1, **not** against the running job's bytes — the lead must diff it against the live prompt before re-creating.
- Pilot journals and anchor inspection journals were not audited, except where CFG-06 AMENDMENT 1 names the 8 historical per-arm readings in journal_2026-09-1{0,1}_anchors.md.
- FXR-DOC-3 sweep coverage: 237 lines across ~60 files cite 1.29 / 1.2912 / 1.2947 / 1.1062 or the derived N_eff and DSR readings. Rows were written for the citations that leave their document (KB-63..KB-68). The ~60 in-document receipt lines under `uplift_2026-09-11/r9..r16` sit in documents whose header already pins W_ALPHA and the cost plane; they are internally consistent and were deliberately not annotated one by one — the binding is enforced at CANONICAL_NUMBERS (KB-67) instead. If the lead wants them annotated individually, the full inventory is reproducible with the script in §method.

## §8 Snapshot, method, reproduction

- Superseding receipts were opened and quoted before any claim was marked stale. The digest the sub-auditors worked from is `scratchpad/aud_kb/DIGEST_superseding_receipts.md`.
- Five memory sweeps (M1–M5) each read every note in their list and wrote JSONL rows. aud-kb spot-checked P0/P1 rows against receipts. Row builder `kb_rows_build.py` locates every quote by exact substring. Assembler `kb_assemble.py` re-verifies every source quote and every file-based evidence quote against disk at assembly and recomputes line numbers. Renderer `kb_render.py` writes this file and the JSON. All three live in `/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/aud_kb/`. Per the lead's instruction only the two output files are committed.
- Runtime facts (read-only): `~/regime_dash/REGIME_DASH.md` (12:50:02Z), `~/wide_shadow/shadow_log.jsonl`, `~/Library/LaunchAgents/com.hsy.combolive.plist`, `launchctl print` / `list` / `print-disabled`, `~/dl_quant_live/config/book.json`, `~/dl_quant_live/live/chase_policy.py`, `~/guard_twin/state/latest.json`, `~/wide_shadow/intraanchor_depth_watch.py`, `~/wide_shadow/shadow_loop_v3.py`, and the lead transcript (cron tool calls only). No API call, no process signal, no write outside the scratch directory and this directory.
- Reproduce: `cd <scratch>/aud_kb && python3 kb_rows_build.py && python3 kb_assemble.py && python3 kb_render.py`.
- **FXR-DOC-3 inventory (reproducible).** Scan `docs/`, `multi_asset/exports/research/`, `STATE.md`, `CLAUDE.md` and the memory directory for `1.29122344|1.2912|1.2947|1.1062|(?<![\d.])1\.29(?![\d])` on lines that also match `夏普|Sharpe|SR\b`; split into (A) lines that additionally carry `全周期|全史|full cycle|全窗` — the mislabel itself — and (B) lines carrying no window marker (`W_ALPHA|9,?138|9,?139|2022-06-30|窗`). A = 12 lines, B = 62 lines, 237 lines total across all patterns. Excludes `docs/audit_pipeline_2026-09-13/` to avoid the register matching itself.
- **Merge (M4).** Final register = `rows_KB` + `rows_NEW` (KB-63..KB-68, FXR-DOC-3) + `rows_NEW2` (KB-69..KB-71, the PROD id collision and the applied N+23 rows) + `rows_NEW3` (DEV-14) + `rows_CRON2` (CRON-13/14, FXR-KB-1) + `rows_M1..M5` including `rows_M4_part2` (M4-32..M4-53, the 20 remaining DNR / closed-axis / infrastructure notes). 303 rows, no duplicate ids. Every quote was re-located by exact substring against the file on disk at assembly; the 10 volatile `REGIME_DASH.md` receipts were repointed to the append-only `regime_dash.jsonl` (DEV-14).
- **K4 application state (2026-09-16, commit `5851c7cb`).** All **41** unapplied rows whose source is under `docs/` are now annotated in place across 9 files, +147 insertions / **0 deletions** — original bytes are retained without exception, each correction inserted as a `> ⚠ **更正 <id> · <sev> · AUD-KB K4 2026-09-16**` blockquote after the quoted line. Coverage of `docs/` is complete (42 rows, of which KB-69 the lead had already applied). `docs/CRON_TEMPLATES_2026-09-04.md` is handled differently on purpose: the user's verbatim template at L13 is **not touched**, a pointer is inserted after it, and the eleven corrections (CRON-01..CRON-10, DEV-12) are carried in a new annex at the end of the file, which is the 2026-09-16 replacement text reproduced in §5.
- **⚠ Correction to that commit's own message (`5851c7cb`).** Its subject says 「30 条更正」. The correct count is **41**, verified by counting the annotation markers per file (CANDIDATE 5 · CHECKLIST 3 · CRON_TEMPLATES 11 · ERROR_LEDGER 7 · HANDOFF_round4 1 · MILESTONE 10 · STATUS_three_questions 1 · AUDIT_KB_PARTIAL 2 · FIXPROGRAM 1). The message could not be amended: see the next item.
- **⚠ Process failure, recorded here because it changed another agent's commit sha (aud-kb, 2026-09-16 11:59Z).** Attempting to `git commit --amend` the count above, this auditor read HEAD before FX-MODEL's commit `44d1dadf` landed and did not re-check it, so the amend rewrote **FX-MODEL's** commit rather than its own. No content was lost — tree `f1e8a977…`, commit message and parent `5851c7cb` are identical on both objects and `git diff 44d1dadf 55c29170` is empty — but the sha moved to **`55c29170`** (committer timestamp only). No second rewrite was attempted, because rewriting history while several agents commit concurrently is how work is actually lost. **Rule: in this repo `git commit --amend` requires re-reading HEAD and confirming it is your own commit immediately beforehand; otherwise record the correction in a later commit, as done here.**

| file | sha256 at render |
|---|---|
| `CLAUDE.md` | `dcb478ec339e1f4f16ffb7c0616e521ff07e582a84f909346fb5e4d997222ea2` |
| `STATE.md` | `2479f94b13584ff9d23c9713c24317ed30d5158924f113252b39208feecea05f` |
| `docs/MILESTONE_2026-08-26.md` | `469d603bfc7d7fc462a19ae9423f2f22e57a59760c323f3a02281ba74bb0684b` |
| `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` | `da305570cfda0d733c4030003c6a1ff950df857fbd4ca674e9212d2b60905815` |
| `docs/CHECKLIST_combo_switch_2026-08-26.md` | `ef6a84572f0c39a5cc96f9dc13a824cfa09710666641e081d2bda4161223f3e6` |
| `docs/ERROR_LEDGER_2026-08-20.md` | `0406a634793268f47e0ae1b0d7653951a58ba29765b9d4266dc6d58b5b6be49c` |
| `docs/CRON_TEMPLATES_2026-09-04.md` | `d5baee2a37449ec399b27503976b18481f5476905b847a3826c0121e0da5d5b2` |
| `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md` | `0a94f9bcb4a9112a6837398f7e13b46927cffafbd439b5196d63c988e48beeb3` |
| `multi_asset/exports/research/uplift_r3_2026-09-13/PROGRAM_uplift_r3_2026-09-13.md` | `c8128d8505443f8468e0f62a5c040cd40f59bc8ab90ad0b205a9725f5c8877a0` |
| `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/judge_v4.py` | `3884e093ab91a8caab543c2b8dce568c5dc77fdc2e3fa8828c29d2aff6aa0d68` |
| `memory/MEMORY.md` | `fb37797a5eab647172e5cae7e10745652d86508216ce9a7cad47d2f62ee098b2` |

