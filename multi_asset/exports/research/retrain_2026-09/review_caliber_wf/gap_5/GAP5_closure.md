# GAP #5 closure — live components missing from REVIEW §2 / §7 #18 (2026-09-04, subagent gap_5)

Ground rule kept: read-only everywhere (no writes under ~/wide_shadow, ~/dl_quant_live, pod /workspace/data; launchctl only listed). jpline tried once: `ssh -o ConnectTimeout=8 jpline` → `ssh: connect to host 212.50.244.62 port 31999: Operation timed out`.

## A. Facts with receipts

### A1. σ_fund gross ladder — executor side (VERIFIED, executing lines read)
- `/Users/haosiyu/dl_quant_live/scheduler/anchor_loop.py`
  - L1472 `_g, _ginfo = _SLAD.load()` (inside `if _is_ext:` L1470; import L1471 `import sigma_ladder as _SLAD`)
  - L1477 `_bw["gross_ladder"] = _ginfo`
  - L1478-1480 `if _is_ext and _g < 1.0:` → `_sz = self._size_book(target_leverage=external["gross_mult"] * _g, leverage_source=f"external_book.gross_mult×ladder({_g})")`
  - L1482 default path `_sz = self._size_book(target_leverage=(external["gross_mult"] if _is_ext else None), …)`
  - L1041-1042 `tgt_lev = (… if target_leverage is None else float(target_leverage))`; L1063 `want = nav * tgt_lev`
- `/Users/haosiyu/dl_quant_live/live/sigma_ladder.py` L10 `ALLOWED_G = (0.5, 1.0)`; L11 `MAX_AGE_S = 6 * 3600`; L13 `DEFAULT_PATH = …/state/live/sigma_ladder.json`; L23-24 `if doc is None: info["reason"] = "missing"; return 1.0, info`; L40-41 stale/future → `return 1.0, info`.
- Executor commit: `git -C ~/dl_quant_live log` → `4b8ca20 2026-09-04 17:34:30 +0800` (= 09:34Z) "σ_fund gross 阶梯 … tests_sigma_ladder 13 项 … 今日行为零变化(g=1.0)".
- Current state (VERIFIED by execution): `ls ~/dl_quant_live/state/live/sigma_ladder.json*` → only `sigma_ladder.json.reserve_20260904` (g 1.0, p 0.6487, streak_high 62, anchor_ts 1788508800 = 2026-09-04 08:00Z, written_utc 09:35:03Z, sha valid). Read-only import of the executor module: `SL.load()` → `(1.0, {'src':'sigma_ladder','g':1.0,'accepted':False,'reason':'missing'})`; `SL.evaluate(reserve_doc, now)` → `stale_or_future:22446s` → 1.0.
- Running-process receipt (patch running, not just on disk): `state/live/pilot_log/20260904/anchors.jsonl` rows 00:24Z/04:24Z/08:24Z have no `weights.gross_ladder`; the 12:24Z row has `weights.gross_ladder = {'src':'sigma_ladder','g':1.0,'accepted':False,'reason':'missing'}`, `weights.gross_mult = 2.0`. Book-level zero effect: realized_gross/NAV (nav 82963.20 @12:43Z) = 1.996 / 1.982 / 1.971 / 1.942 across the four anchors — no step at 12Z.
- Dashboard writer: `launchctl list | grep hsy` → `com.hsy.sigma_ladder` ABSENT (com.hsy.regime_dash present, `-	0`); plist exists at `~/Library/LaunchAgents/com.hsy.sigma_ladder.plist` (Sep 4 17:35) → installed, not loaded. `~/regime_dash/sigma_ladder_state.json` updated 09:35:03Z: g 1.0, cl 0, ch 62, p_last 0.6487, sigma_last 10.05 bp, roll_last 14.8; history = 2023-02-04 00Z→0.5 (p .085), 2023-08-06 20Z→1.0 (.713), 2024-08-05 12Z→0.5 (.178), 2025-01-04 04Z→1.0 (.794).

### A2. σ_fund gross ladder — writer rule and its input caliber (VERIFIED read)
- `/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/regime_dash/sigma_ladder.py` L6 `OUT=… ~/dl_quant_live/state/live/sigma_ladder.json`; L7 `P_LOW, P_HIGH, STREAK, WIN, ROLL = 0.33, 0.50, 84, 4380, 30`; L15 series = `sig_fund_bp` from `~/regime_dash/*.jsonl` after seed `sigma_seed.json`; L25 `p=sum(1 for h in hist if h<=roll[i])/len(hist)`; L26-29 hysteresis `if g==1.0 and cl>=STREAK: g=0.5` / `if g<1.0 and ch>=STREAK: g=1.0`; L33-35 writes doc + sha.
- Input `sig_fund_bp` = `regime_dash.py` L33 `np.std(ff)*1e4` of `rn8` (L19 `rn8[j]=float(r[1])*(8.0/(iv if iv>0 else 8.0))`) → a funding-rate dispersion normalised to 8h, NOT a return. ⇒ the ladder's live STATE carries no return caliber; the whole caliber exposure is in its admission/withdrawal EVIDENCE (A3).

### A3. Ladder evidence caliber (VERIFIED for the judge; INFERRED for the artefact files)
- `docs/RESULT_allweather_2026-09-04.md` L2 装置 = `retrain_2026-09/jp_allweather.py` on w10 arm series; L5 H1 numbers (2023+ DD −37→−29, 2024 −8→+3, ΔNet +0.050 CI[−0.044,+0.148]).
- `retrain_2026-09/jp_allweather.py` L7 `z=np.load(f"{PD}/w10_{tag}.npz")… rec=z["d30_n2_c42_rec"]` (col `net_ex`); L32 `ARMS={"C":"uni2_F_M7F_fx_s42","E":"uni2_N829T400F_fx_s42"}`.
- Producer of those tags: `retrain_2026-09/jp_universe2_runner.sh` L12-13 / `jp_universe2_round2.sh` L6-7: `[ "$C" = fx ] && EXTRA="$EXTRA W3FIX=0.21,0,0.79"` … `env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s$S.npy OUT_TAG=$TAG $EXTRA $PY w10_universe.py`. `w10_universe.py` L17 default `CAL="simple"`, L135/L277 `if CAL == "simple": … expm1`. ⇒ H1 = CAL=simple (expm1 pseudo-convexity) + fixed seats 0.21/0/0.79. The arm npz files live on jpline (down) → their CONFIG self-report unopened → artefact CAL is INFERRED from the only runner in the repo that emits `uni2_*_fx_s42`.
- Withdrawal (PREREG_deploy_sigma_ladder §6 L28, E-0904-D ledger L408-411): rerun `jp_allweather_ms.py` L5 `ARMS={"M_ms":"canonpred_s42","EM_ms":"uni2_N829T400F_ms_s42","EM_ms2027":…,"E_fx":"uni2_N829T400F_fx_s42"}` — same CAL=simple runners (the `_ms` tags: jp_universe2_runner.sh L18 `run $A ms 42`), made 09:5xZ, i.e. BEFORE E-0904-F (11:4xZ). ERROR_LEDGER L398 explicitly voids "E-0904-D 的阶梯复测". ⇒ both the admission (H1) and the withdrawal verdict are on CAL=simple; the ladder has no valid evidence in either direction.
- No CAL=log/Π rerun of the ladder exists: pod `/workspace/port_w10/probe_artifacts/` has no allweather/ladder output (listing = canon/live/w3fix/ftrim/t400/m1t400/t3c only); `/workspace/port_w10/REPORT.md` no ladder mention; `retrain_2026-09/jp_callog_revalidate.sh` L8-18 reruns canon / N829T400F / T3c only, no `jp_allweather` step.

### A4. Regime dashboard (VERIFIED, executing lines read)
- `multi_asset/exports/live/regime_dash/regime_dash.py` L121 `r=float(m1[s_])/float(m0[s_])-1; price=n0*r; car=F1.get(s_,0.0)` with m0/m1 = executor `mid_at_anchor_vector` (L54-67 from `pilot_log/2026*/anchors.jsonl`), n0 = `venue_position_notional` (L106 from position_readback.jsonl), F1 = Σ `funding_paid` (L107-112 from funding.jsonl). ⇒ money caliber: mid-ratio simple return × venue notional + ledger funding; no expm1/log1p anywhere in the file's return path.
- `multi_asset/exports/live/regime_dash/beta_alpha_attrib.py` L11 `def btc_ret(Ta,Tb): r=ret5(btc)[row[Ta]+1:row[Tb]+1]; r=np.where(np.isfinite(r),r,0); return float(np.expm1(np.log1p(r).sum()))` on `~/wide_shadow/state/rolling.npz` channel 0 (L9-10; ch0 = `ret5 = (c / pc - 1)` per REVIEW §2 producer row) ⇒ Π(1+r5)−1 over (Ta,Tb] = exchange/compound caliber, correct.
- Neither script is in any test battery (grep of ~/dl_quant_live and ~/wide_shadow tests for `regime_dash|beta_alpha` → none).

### A5. Tests (VERIFIED by grep and by reading)
- Producer `/Users/haosiyu/wide_shadow/tests_target_live_output.py` L278-291 = suite [10]: 10a (L280) static grep `"ret5 = (c / pc - 1)" in _src`; 10b (L281-282) `_app = [ln … if "st.LR[leg].append(" in ln]` then asserts `"expm1" not in _app[0] and "log1p" not in _app[0] and "np.log(" not in _app[0]` — inspects ONLY the append line (`shadow_loop_v3.py` L439); a transform placed on L430-431 (`y4v = …`) or on `seg` L428 would pass; 10c (L286) row count ≥ 900; 10d (L288-289) informational `OK/WARN` only (`|Δmean| ≤ 3 bps` vs bundle last 900), never fails.
- Executor: `grep -rln -E "expm1|log1p" ~/dl_quant_live --include='*.py'` → empty (no occurrence in any executor file, tests included). `tests_sigma_ladder.py` L21-38 = 13 checks on evaluate/load (missing/schema/whitelist/sha/stale/future/corrupt) + arithmetic `2.0 x 0.5 = 1.0`, `2.0 x 1.0 = 2.0`; nothing about return caliber (by construction the executor never sees a return series). `ops/gate_coverage.py` SUITE_SCOPE L222 entry for `tests_sigma_ladder` states the contract "target_leverage = gross_mult x g" and declares NO blind spot (contrast L147 `tests_neutral_band` "Four blind spots"). `run_acceptance.sh` L51 registers the suite.
- Bundle exporter `/workspace/pod_export_bundle_v3.py` L109 `LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) …)`: `ls /workspace/*test* /workspace/tests*` → nothing; only other referrer `pod_guard_reconcile.py` (L2 "同代码" re-implementation, L40 same formula; a diagnostic corr/Δ report, not a gate). Mac tests referencing `export_bundle|pod_export` → none.
- combo_stage `/Users/haosiyu/wide_shadow/fea171/combo_stage.py` L29 `LR = json.load(open(f"{WS}/state/leg_returns_live.json"))`; L31-34 msharpe `shp = r.mean(1) / (r.std(1) + 1e-9)`; no test references combo_stage (wide_shadow tests: only [10] lines touch the file; dl_quant_live: none). L3 docstring "判据装置 = w10 LEGS=101 CAL=simple PHI=0.45" (belief, not evidence).

## B. Text to insert into REVIEW_caliber_final_draft.md

### B1. Three rows for §2 (append after the "执行器 NAV/盈亏/止损" row)

| 组件 | 定义(执行行) | 口径 | 下游变换 | 判定 | 收据 |
|---|---|---|---|---|---|
| σ_fund gross 阶梯(执行器 sizing 乘子, 09-04 09:34Z 上线 4b8ca20; 仪表盘作业 09:5xZ 卸载) | `_g, _ginfo = _SLAD.load()`; `_sz = self._size_book(target_leverage=external["gross_mult"] * _g, leverage_source=f"external_book.gross_mult×ladder({_g})")`; `want = nav * tgt_lev`; 读端 `ALLOWED_G = (0.5, 1.0)`, 缺失/陈旧/篡改 → `return 1.0, info` | 乘子 g∈{0.5,1.0}, 状态输入 = `sig_fund_bp = np.std(ff)*1e4`(8h 归一费率离散, 非收益) | 无(不触面板收益) | VERIFIED 行为: 状态文件缺失(仅 `.reserve_20260904`), 12:24Z anchors 行 `gross_ladder={'g':1.0,'accepted':False,'reason':'missing'}`, gross/NAV 1.996/1.982/1.971/1.942 无台阶 ⇒ g=1.0 零行为效应; **受据口径: 录取(RESULT_allweather H1)与撤回(E-0904-D)都建立在 `CAL=simple W3FIX=0.21,0,0.79` 臂序列上 ⇒ 双向作废, 待 CAL=log/Π 重判**(臂 npz 在 jpline, 未开, CAL 由 runner 推断 INFERRED) | `dl_quant_live/scheduler/anchor_loop.py` L1472/L1479-1480/L1482/L1063; `dl_quant_live/live/sigma_ladder.py` L10/L13/L23-24/L40-41; `regime_dash/sigma_ladder.py` L7/L25-29/L33-35; `regime_dash.py` L19/L33; `retrain_2026-09/jp_allweather.py` L7/L32; `jp_universe2_runner.sh` L12-13; `jp_universe2_round2.sh` L6-7; ERROR_LEDGER L398/L408-411; `launchctl list`(com.hsy.sigma_ladder 不在列) |
| regime 仪表盘 sleeve 归因(`~/regime_dash/regime_dash.jsonl`, launchd com.hsy.regime_dash) | `r=float(m1[s_])/float(m0[s_])-1; price=n0*r; car=F1.get(s_,0.0)`(m = 执行器 `mid_at_anchor_vector`, n0 = `venue_position_notional`, F1 = Σ `funding_paid`) | 钱口径: 锚间 mid 比值简单收益 × 场所名义 + 账本 funding | 无 expm1/log1p | VERIFIED(执行行); 不在任何电池 | `multi_asset/exports/live/regime_dash/regime_dash.py` L121, L54-67, L106-112 |
| β/α 拆分(`~/regime_dash/beta_alpha.jsonl`) | `def btc_ret(Ta,Tb): r=ret5(btc)[row[Ta]+1:row[Tb]+1]; r=np.where(np.isfinite(r),r,0); return float(np.expm1(np.log1p(r).sum()))`, ret5 = `rolling.npz` 通道 0 | Π(1+r5)−1, 窗 (Ta,Tb] = 交易所记账口径(BTC 4h) | 无 | VERIFIED(执行行; 通道 0 = `ret5 = (c / pc - 1)` 见生产者行); 不在任何电池 | `multi_asset/exports/live/regime_dash/beta_alpha_attrib.py` L9-11 |

### B2. §7 #18 amendment (replace the row)

| 18 | 在役书形态(combo/FTRIM/M1/PHI=0.45)是在 CAL=simple 上判定的; **同样: σ_fund gross 阶梯 = 实盘 sizing 乘子(`anchor_loop.py` L1479 `target_leverage = external["gross_mult"] * _g`), 其受据 RESULT_allweather H1 = CAL=simple + 固定席位 W3FIX 0.21/0/0.79(`jp_allweather.py` L32 臂 `uni2_F_M7F_fx_s42`/`uni2_N829T400F_fx_s42` ← `jp_universe2_runner.sh` L13 `CAL=simple … W3FIX=0.21,0,0.79`), 撤回受据(E-0904-D, `jp_allweather_ms.py`)亦为 CAL=simple; 当前 g=1.0(状态文件缺失, 12:24Z anchors 行 `reason: missing`; 仪表盘作业已卸载)⇒ 零行为效应; 受据状态: 双向作废, 直到在 CAL=log/Π 口径重判(pod port 与 `jp_callog_revalidate.sh` 均无阶梯复跑)** | VERIFIED 事实(`combo_stage.py` L3; 阶梯执行行 + anchors 行); 臂文件 CAL INFERRED(jpline 未开) | 用户裁定是否需在 Π 口径重判; 阶梯: 在 CAL=log 臂上重跑 `jp_allweather.py`(固定 + 动态两口径)后再决定复活/永久撤回 |

### B3. New §7 row (#20) — gate_coverage blind spots (caliber links no battery asserts)

| 20 | 口径链上无门的环节: (a) bundle 出口 `/workspace/pod_export_bundle_v3.py` L109 的 leg_returns 口径 — pod 无任何测试(`ls /workspace/*test*` 空), 仅 `pod_guard_reconcile.py` 同式重算作诊断; (b) `combo_stage.py` L29-34 msharpe 输入 `state/leg_returns_live.json` — 无测试断言其行口径或其 w3 == 生产者 w3(仅 tracer T-LIVE 一次性重算); (c) 生产者测试 [10b] 只 grep `st.LR[leg].append(` 一行(L439), 对 L428-431 的 `seg/y4v` 变换盲; [10d] 仅 WARN 不 FAIL; (d) 执行器 `tests_sigma_ladder` 13 项只证 evaluate/load 合约与 `2.0×0.5`, gate_coverage L222 未声明盲区 — 阶梯的受据口径(H1 是否在 Π 口径成立)不在任何电池可见范围; (e) `regime_dash.py` L121 / `beta_alpha_attrib.py` L11 无测试 | VERIFIED(grep 收据见 gap_5/GAP5_closure.md §A5) | 三件套登记(测试 + SUITES + 盲区字典): 出口/合并阶段加"从 5m 缓存重算 ≥30 行逐位 == leg_returns"断言; gate_coverage L222 补盲区句 |

### B4. Suggested one-line addition to §8 rule 8 (optional)
"…任一不过禁写 `state/leg_returns_live.json`。**同规则适用于 `combo_stage.py` L29 的读端与 `pod_export_bundle_v3.py` L109 的出口: 无逐位重算断言即为盲区(§7 #20)。**"

## C. Labels summary
- Ladder executing lines, state, running-process behaviour (g=1.0, zero effect): VERIFIED.
- Ladder writer rule and σ_fund input (funding dispersion, not a return): VERIFIED.
- Ladder evidence caliber = CAL=simple + fixed seats: judge script and runner lines VERIFIED; the arm npz CONFIG self-report on jpline UNOPENED → artefact CAL INFERRED.
- Withdrawal (E-0904-D) also on CAL=simple, voided by E-0904-F L398: VERIFIED (ledger text + script dates); no CAL=log rerun exists anywhere reachable: VERIFIED (pod listing, revalidate script).
- Dashboard L121 money caliber, β/α L11 compound caliber: VERIFIED.
- Test coverage gaps (exporter, combo_stage input, [10b] scope, executor no-caliber, gate_coverage no blind-spot clause): VERIFIED by grep.
