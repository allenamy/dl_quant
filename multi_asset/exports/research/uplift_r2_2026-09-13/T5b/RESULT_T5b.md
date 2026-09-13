> **创建:** 2026-09-13 ~08:55Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5b) | **状态:** 完成; 判据冻结于 `SPEC_T5b.md` sha256 `92d90103…5b87`(2026-09-13 08:08:15Z, 提交 eaa08cd9, 先于任何 T5b 数字); 冻结后未改窗 / 定义 / 读法; 三个事后装置(§5)均标 POST-HOC, 不改任何读法; 未经 lead 复跑 | **作废条件:** 生产者存档或执行器账本在拷贝时刻 2026-09-13T08:10:25Z 之前的内容被改写; `T1/receipts/pod2/T1_d2.npz` 或 `T5/receipts/pod2/T5_bridge_components.npz` 被替换
> **口径:** 建模 carry = 锚时 `rate × 4/iv`, bps / 4h 锚 / 单位 gross, 正 = 付(T5 公式); rate / iv 取生产者资金费账本中 ft ≤ A 的最后一行(>12h 陈旧记 0), 与 T5 面板定义同式但数据源不同, 等价性见 G-CARRY。**测量, 不是提案。** 全部数字出自 `receipts/TABLES_T5b.md`(由 `devices/t5b_tables.py` 从收据渲染)。
> **实盘零接触(VERIFIED):** `~/wide_shadow`、`~/dl_quant_live` 只读; 717 个文件拷入 `T5b/private/`(gitignored, 清单 `private/COPY_SHA256.txt` sha `a88f2135…`), 凭据扫描命中 0, 未拷 `.env`; 执行器 git 只用 `log` / `show` / `grep`; 无交易所 / 网络 / Telegram 调用; 未碰看门狗、launchctl 或任何进程; 仅本机 CPU; 所有装置前台运行, rc 与标准输出在 `receipts/`。

# RESULT · T5b · FTRIM 残余冻结 / 执行器逐名止损 / 执行器是否另加冻结

## §0 一页

**Q1 目标层 FTRIM 残余冻结(W1 = 09-02 12Z..09-12 12Z, 61 锚)**
- **机制按数据确认(G-MECH PASS)**: FTRIM 名在去均值前 z 置零, 同链同锚所有移动中的 FTRIM 名反推出同一个目标(极差 ≤ 9.5e-18); EMA 0.1 + 带宽 2.5e-4 对 890 个名-锚预测「冻结 / 移动」, 与观测逐一相符, 不符 0。T5 §8(iii) 的代码推断成立。
- **规模**: target_live 中 FTRIM 残余(|w| > 1e-6)每锚 7.6 名(最多 12), gross 份额 2.08%(最多 6.37%); 其中**冻结**(权重与上锚逐位相同)每锚 3.07 名(最多 6), gross 份额 **0.33%**(CI [0.24%, 0.40%], 最多 0.64%)。冻结年龄中位 7 锚, p90 25 锚, **最长 41 锚**(ONGUSDT 自 09-05 20Z 冻到窗末, 右删失; ACEUSDT 28 锚; IOSTUSDT 15 锚右删失)。冻结实例中 **30% 是多头残余**(z 转负的多头被置零后同样冻结)。
- **主读法(冻结规则)**: 冻结残余建模 carry 均值 **−0.120 bps/锚**, CI [−0.245, −0.021](k=501), 累计 −7.3 ⇒ **NOT MATERIAL**, 标 **PROVISIONAL**: G-CARRY-CD2 红(§1, §5.1)。
- 次级读法(同阈值, 不替代主读法): 全部 FTRIM 残余(冻结 + 衰减中)tl **+0.115** [−0.080, +0.334] ⇒ 次级读作 MATERIAL; kc 链 +0.129, fc 链 +0.095 同向。
- 事后拆分(§5.2, 不改读法): 冻结**空头**付 **+0.021** [+0.014, +0.029], 冻结**多头**收 −0.141(IOSTUSDT / SOPHUSDT 多头残余遇到 −438..−695 bps/4h 的极端负费率); 全部残余空头付 **+0.294** [+0.155, +0.478]。**付出的 carry 主要在衰减期, 不在冻结期**。

**Q2 执行器层: 八月队列(W2 = 08-26 00Z..08-31 00Z, 31 锚)**
- **执行器逐名止损在役并被逐锚评估**: config `per_name_stop` enabled, profile wide(−30% / 连续 2 锚 / 冷却 7 天 / 5 USDT), 11 个配置提交 + 工作树在这些键上 W2 内恒定; LIVE phase_C 带 per_name_stop 字典的锚 **31/31**。
- **8 个队列名全部 NOT FIRED**: counter ≥ 1 的锚 0; notify_audit / launchd_out 中队列名的 per_name_stop 事件在 W2 与窗外(至 09-12 12Z)均为 0。08-20..09-12 执行器止损共触发 25 次, 队列名 0 次; W2 内唯一一次是 SKRUSDT(08-30 16:43Z, −41.0%)。
- **ONG 为什么没止**(记录 + 重建深度, 重建只作描述): 执行器 ONG 空头成本 0.07626, 重建深度 08-26 00Z / 04Z / 08Z 为 −21.7% / −24.9% / **−28.5%**(未到 −30%); 12Z 锚本书被保护性平仓(08-26 12:47Z §4-5e 停机, 记录类 PROTECTIVE), ONG 归零; 08-27 00Z 以 **0.19152** 重建, 此后价格回落, 空头深度为 **+6%..+33%**(盈利)。执行器的持仓路径与回放止损层(08-25 20Z 起封锁 ONG)不同。
- **持仓对 target_live**: 28 个 NORMAL 锚上 H_post / T_file 中位 0.97..1.04(ONG 1.011, [p10, p90] = [0.996, 1.029]); 队列合计 carry: 目标文件 +1.319, 执行器持仓 +1.282, 差 −0.037 bps/锚。**执行器基本按 target_live 持有队列名。**

**Q3 执行器层: F_A 名在 W1**
- **没有带宽类冻结**: 25 个代码版本(W1/W2 期间改动过相关文件的全部提交 + 工作树)外部书分支均跳过中性带与 harvest EMA, `DEFAULT_BAND_BPS = 0.0` 且非测试代码无覆写(G-CODE PASS); `state/live/no_trade_band.json` 最后写于 A1787371250 = 08-22 04:00Z(外部书切换前最后一个内部书锚), 之后未写。
- **执行器跟得很紧**: 366 个 NORMAL 实例 |H_post − T_file| 中位 **35 USDT**, 权重差均值 −9e-5。
- **执行器加冻**(执行器数量不变而目标变了, 两锚均 NORMAL): 555 个实例中 **33 个**; 原因 add_blocked 24 / no_chase 5 / min_notional_skip 2 / unfilled 2。24 个 add_blocked 全部是逐名止损的后遗: SKRUSDT(16)、BTRUSDT(4)是冷却期内的尘埃仓(−0.1 / +3 USDT), CYSUSDT(1)、XANUSDT(3)是**仍处于 stopped 状态**的多头小仓(8 / 46..49 USDT)。
- **读法(T5b 自加规则, 非派工给定)**: 执行器加冻的 carry 差均值 **−0.030** [−0.080, +0.004](k=601, 52 个 NORMAL 锚)⇒ **NOT MATERIAL**; 符号为负 = 执行器因 SKR 冷却没有持有生产者要的 SKR 空头, 少付了 carry。

**事后核实的新风险(§5.3, 不在三问之内, 但直接关于实盘止损是否起作用)**: **已停的多头仓位不会被平到 0**。执行器先把已停名目标置 0, 随后 reshape 的去均值给所有名同一个平移 a(本期 +1.5..+62 USDT, 因撤名残差 net_before < 0), 再做 clamp: 已停多头小仓因「目标同号且更大」被判 add_blocked 钉在原仓位, 大仓被 reduced 到 ≈ a。W1 ∪ W2 共 125 个「已停且持仓」实例: 多头 add_blocked **94** / reduced **23**, 空头 flatten_only 5 / 未列出 3; 用平移 a 预测的桶与记录 **122/122 相符**。被钉住的: CYSUSDT、TRIAUSDT(09-02 12Z 起)、MAGMAUSDT、RIVERUSDT(09-03 16Z 起)至 09-06 08Z 保护性平仓; XANUSDT 09-09 00..08Z; IOSTUSDT 09-10 16Z..09-12 12Z。它们的冷却都要等书级平仓后才开始。金额小(每名 6..50 USDT), 但止损告警文案写的是「⇒ flatten_only(maker 出场, 不追)」, 而 `ops/gate_coverage.py` 对 tests_per_name_stop 已自述盲区 (b)「does not prove the stopped name actually lands in the flatten_only bucket」—— 本次在实盘账本上见到的正是这一格。

## §1 门(`receipts/TABLES_T5b.md` T0)
| 门 | 结果 | 读数 |
|---|---|---|
| COPY | rc 0 | 717 文件, 缺 5(08-25 20Z 无 combo 记录; 08-29 20Z 无部署文件; 08-30 00Z king 形态无 combo 记录), 凭据命中 0, 拷贝期间源不变 717 |
| 首个 FTRIM 锚 | PASS | target_combo 1788350400(09-02 12Z)首含 ftrim 键; combo_live.log 块头 L337, 首个 FTRIM 行 L342 |
| G-ARCH | PASS | 61 锚 max|w_tl − (0.55 kc + 0.45 fc)| = 0.0 |
| G-LEDGER | PASS | 两份账本重叠行冲突 0; 截断尾 0 |
| G-RN8(诊断) | 554 / 555 | 唯一不符: IOSTUSDT 09-10 04Z, 记录 rn8 −0.02 = 00Z 的 8h 行, 账本已有 01Z..04Z 的 1h 行(生产者跑时未入账) |
| G-MECH | PASS | 116 个可识别链-锚, 890 次名级核对不符 0, 从 0 新开 0 |
| **G-CARRY-CD2** | **FAIL** | 46 锚对 T1 D2: max|Δcarry| 2.42, max|Δcoh| 0.47; 同一批 target_live 文件(sha 与 T1 收据相同) ⇒ Q1 读法 PROVISIONAL |
| G-CARRY-CT5 | PASS | T5 27 锚 C_D 逐锚 max|Δ| 3.6e-8; TC1 两格 Δ 2e-9 / −1e-9 |
| G-DET | PASS | M1 冻结实例扰动 1e-9 判非冻结; M2 移动实例置等判冻结; M3 c4≡0 ⇒ 0; M4 c4 取负 ⇒ carry 取负 |
| G-FILE | PASS | 90 锚执行器 json_sha == 副本 sha, gross_in 重算一致 |
| G-PLAN | PASS | 743 个 maker 行 (target_w − prev_w)·target_gross == intended_full |
| G-S | 73 / 0 失败 | 17 锚 reshape 字段缺失 = 09-05 12Z..09-08 04Z(E-0908-A 段) |
| G-CODE | PASS | 25 个版本全部含外部书跳过中性带 / 跳过 harvest EMA / DEFAULT_BAND_BPS 0.0 / plan 最小名义额跳过 / 2×minNotional 撤下 / withhold+reshape |
| G-QTY(深度重建) | 描述 | 每名自 08-01 回放, 读回失配 3..8 次均在读回为 0 时重同步; W2 内 ONG 27 锚 RECONSTRUCTED |

## §2 Q1 细节(`TABLES_T5b.md` T1–T3)
| 书 | 残余名 均 / 最大 | 冻结名 均 / 最大 | 冻结实例 | 其中空头 | 年龄 p50 / p90 / max | 曾冻结名 | 冻结段(末锚仍冻) |
|---|---|---|---|---|---|---|---|
| kc | 7.38 / 12 | 3.00 / 6 | 183 | 68% | 7 / 26 / 41 | 13 | 24(3) |
| fc | 7.56 / 12 | 3.80 / 7 | 232 | 74% | 5 / 24 / 41 | 18 | 39(5) |
| tl | 7.56 / 12 | 3.07 / 6 | 187 | 70% | 7 / 25 / 41 | 14 | 28(3) |

| 量(W1 61 锚) | 均值 bps/锚 | CI95 | 累计 | 读法 |
|---|---|---|---|---|
| **tl 冻结残余(主)** | **−0.1199** | [−0.2448, −0.0206] | −7.316 | **NOT MATERIAL (PROVISIONAL)** |
| tl 链分解冻结 | −0.1146 | [−0.2428, −0.0084] | −6.988 | NOT MATERIAL(次级) |
| tl 全部 FTRIM 残余 | +0.1149 | [−0.0798, +0.3338] | +7.010 | MATERIAL(次级) |
| kc 冻结 / fc 冻结 | −0.1216 / −0.1036 | [−0.238, −0.031] / [−0.238, +0.020] | | NOT MATERIAL(次级) |
| kc 全部 / fc 全部 | +0.1290 / +0.0953 | [−0.059, +0.355] / [−0.106, +0.316] | | MATERIAL(次级) |

- 冻结 carry 被少数锚主导: |C_tl^FROZ| 最大的锚 09-10 04Z −2.39(IOSTUSDT 多头 w +0.00295, c4 −695 bps)、09-08 16Z −1.75(SOPHUSDT 多头 w +0.00334, c4 −438)、09-08 12Z −0.80; 去掉最大 3 锚后均值 −0.041。按名: IOST −0.075、SOPH −0.042、AKE −0.010、ONG +0.008、HEMI −0.007、LA +0.005、ACE +0.004。
- ONG 在 61 锚中 45 锚是冻结空头, 冻结期均贡献 +0.008 bps/锚, 全残余期 +0.031。

## §3 Q2 细节(`TABLES_T5b.md` T5, T5a)
| 名 | 回答 | 评估锚 | counter≥1 | 事件 W2 / 窗外 | H_post/T_file 中位 | 重建深度最小 |
|---|---|---|---|---|---|---|
| ONGUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.011 | −0.285(08-26 08Z, 平仓前) |
| ACEUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.008 | −0.007 |
| TUTUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 0.968 | −0.116 |
| COTIUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.017 | −0.086 |
| HOMEUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.020 | −0.028 |
| BICOUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.011 | −0.178 |
| SANDUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.005 | −0.030 |
| STORJUSDT | NOT FIRED | 31/31 | 0 | 0 / 0 | 1.041(n=3) | +0.016 |
- W2 执行器锚类: NORMAL 28; 08-26 12Z PROTECTIVE; 08-26 16Z HALTED(开仓停, 行 blocked_by_halt); 08-29 20Z NOT_TRADE(无部署文件)。gross_mult 按提交时刻: W2 起点 1.5 → 2.0(08-26 09:10Z)→ 1.5(13:10Z)→ 1.75(08-27 01:24Z)→ 2.0(05:06Z)。
- 重建深度与计数器一致性: 198 个可比名-锚全部「未越线 ∧ 无计数」, 0 个矛盾。
- 名义规模提示: W2 期间 sizing gross 约 2.26 万..3.3 万 USDT(09-03 入金前), ONG 执行器持仓 −155..−404 USDT。

## §4 Q3 细节(`TABLES_T5b.md` T6)
- W1 执行器锚类: NORMAL 52; 09-06 08Z PROTECTIVE; 09-06 12Z..09-07 00Z HALTED(4 锚); 09-09 12Z NO_LIVE_RUN; 09-09 16Z PROTECTIVE; 09-09 20Z HALTED; 09-12 12Z PROTECTIVE。非 NORMAL 锚不进读法。
| 量(52 NORMAL 锚) | 均值 | CI95 |
|---|---|---|
| **GAP_EXECFREEZE(主, T5b 自加)** | **−0.0305** | [−0.0800, +0.0043] ⇒ **NOT MATERIAL** |
| 其中 rule 类(add_blocked / min_notional / no_chase) | −0.0307 | [−0.0822, +0.0039] |
| 其中 fill 类(unfilled) | +0.0002 | [+0.0000, +0.0007] |
| GAP_ALL(执行器持仓 F 名 carry − 目标文件 F 名 carry) | −0.0244 | [−0.0826, +0.0329] |
| C_file^F / C_held^F | +0.1322 / +0.1078 | |
- 执行器冻结 110 个实例, 其中 77 个生产者同时冻结; 61 个实例生产者权重冻结而执行器仍在交易(NAV / gross_in 变动带来的名义调整)。
- 执行器加冻 33: add_blocked 24(|H_post − T_file| 合计 10,300 USDT, 全是止损后遗, 见 §0), no_chase 5(SAND / TUT×2 / CFG / MIRA, 多持 20..150 USDT 空头), min_notional_skip 2(MITO, SKR), unfilled 2(AKE, SOPH 09-11 08Z)。连续段长度: 1 锚 11 段, 2 锚 1, 3 锚 2, 5 锚 1, 9 锚 1。

## §5 事后项(均写于看到结果之后, 不改任何冻结读法)
### §5.1 G-CARRY-CD2 为什么红(`devices/t5b_diag_cd2.py`, `RECEIPT_T5b_diag_cd2.json`, TABLES T4)
- 46 锚本装置减 T1 D2 均值 +0.079, 中位 +0.007, 44 锚 |Δ| > 1e-3; 生产者账本的 iv 字段与该名相邻两次结算间隔不符的持仓名 0。
- 大差集中在结算间隔被两边判得不同的名, 且比值恰为间隔比:
  - 09-02 20Z SKRUSDT: 本装置贡献 +0.6226, D2 口径约 +0.144(比 0.23 ≈ 1/4); **执行器自己的 funding 行(`/fapi/v1/fundingInfo`)与账本一致: 09-02 08Z..09-03 09Z 每小时结算, iv_h = 1**。
  - 09-08 16Z SOPHUSDT: −1.7214 对 −0.417(比 0.24 ≈ 1/4); 执行器与账本 16:00Z 行 iv = 1, 13Z 起逐小时结算。
  - 09-10 00Z IOSTUSDT: −0.3451 对 −2.760(比 **8.00**); 账本 00:00Z 行 iv = 8, 执行器 funding 行在 09-10 01:00Z 才首次出现 iv_h = 1(此前 09-08 16Z / 09-09 00Z / 08Z 均为 8)。
- **已核实**: 三个最大差名上, 账本与执行器的第三方结算记录一致, D2(x0910 面板)口径与二者不一致。**推断(未核实)**: x0910 延展段对 API 尾巴行使用拉取时刻的单一结算间隔(同 `retrain_2026-09/pod_panel_ext.py` L105 `AUG_IV.get(s, np.nan)` 写法), 对拉取前改过间隔的名回填了错误的历史 iv; 延展构建器在 pod2 上, 本任务只许本机, 未读。
- 对 Q1 的含义: 本装置在 T5 窗对面板逐锚 3.6e-8 相符, 在 W1 与执行器结算记录相符, 所以主读法数字按账本口径是可信的; 但冻结规则写明 CD2 不过即 PROVISIONAL, 照此标注, 由 lead 裁。

### §5.2 Q1 按方向拆分(`devices/t5b_q1_posthoc.py`, `RECEIPT_T5b_q1_posthoc.json`, TABLES T3)
见 §0 与 §2。闭合 ≤ 4.4e-16。

### §5.3 已停名在 reshape + clamp 下的处置(`devices/t5b_exec_posthoc.py`, `RECEIPT_T5b_exec_posthoc.json`, TABLES T7)
- 方法: 对每个「上一锚 phase_C stopped 列表内且上一锚读回持仓 ≠ 0」的名, 在该锚用可交易名拟合 `T_exec = a + b·T_file`(大多数锚残差 0.00 USDT, 即 reshape 是精确仿射), 预测置零后的已停名目标 = a, 按 `anchor_loop.py` `clamp_held_untradable`(worktree 副本 L425–L449)预测桶, 对照记录桶(phase_A `untradable_names`)。
- 结果: 125 实例; 记录桶已知 122, 预测相符 **122/122**; 多头 add_blocked 94 / reduced 23, 空头 flatten_only 5 / 未列出 3。reduced 的实例把大仓砍到 ≈ a: HEMIUSDT 1424 → 57, XANUSDT 2292 → 54 → 50, IOSTUSDT 894 → 49; 之后 add_blocked 钉住。
- 冷却开始时刻(notify_audit 与 `state/live/per_name_stop.json`): CYS / TRIA / MAGMA / RIVER 09-06 12:39Z(09-06 08Z 保护性平仓之后), XAN 09-09 20:39Z(09-09 16Z 平仓之后), IOST 09-12 16:39Z(09-12 12:47Z E-0912-A 平仓之后)。SKR(空头)08-30 16:43Z 触发、20:42Z 即进冷却。
- 机制(代码阅读 + 记录吻合, 未执行执行器代码): `scheduler/anchor_loop.py` 先把 stop 名目标置 0, 再调用 `apply_withhold_and_reshape`: POP → `signal/legs.py` `reshape_after_withhold`(`w - w.mean()` 作用于包括已置零名在内的全部目标, 再 L1 重标)→ CLAMP。置零发生在 reshape 之前, 所以被 reshape 撤销。

## §6 与 T5 或既有收据矛盾之处
1. **T5 §0**: 「第三分量是设计差: 回放有逐名止损层, 生产没有(生产的 `stop_overlay.py` 只记录反事实, 它在 08-26 20Z 也标出了 ONG)」; **§8 表**: 「P 逐名止损层 | 回放独有, 不是生产缺陷」。
   **实测**: 生产执行器有在役逐名止损(自 08-22 wide 档), W2 每锚都在评估, 08-20..09-12 触发 25 次。它在 W2 没有对队列动作, 原因是执行器自己的持仓路径(08-26 12:47Z 书级平仓 + 08-27 高位重建), 不是「没有止损层」。T5 的比较层是目标文件, 那一层的分量归属不受影响(lead 在 STATE 已注「只在目标文件层成立」)。另外, 执行器止损对多头的出场本身被 reshape 抵消(§5.3)。
2. **T5 §8(iii)**: 「FTRIM 在去均值之前把 z 置零, 不强制平仓; EMA 每锚向目标走 10%, 当 |0.1·(目标 − 持仓)| < 2.5e-4 时持仓冻结, 所以约 0.25% gross 以内的残余空头可能长期留在书里。」
   **实测**: 机制与量级成立(冻结 gross 份额均 0.33%、最多 0.64%, 最长 41 锚); 但冻结残余有 30% 是多头, 冻结空头只付 +0.021 bps/锚, 冻结残余合计为收(−0.120)。派工背景「such residuals pay large carry」在 W1 不成立于冻结部分, 成立于衰减中的残余空头(+0.29)。
3. **T1 D2 九月 carry**(`T1/receipts/pod2/T1_d2.npz`, x0910 面板): 与生产者账本和执行器结算记录在改过结算间隔的名上不一致(§5.1), 逐锚最大差 2.42 bps, 46 锚均差 +0.079。**凡用 x0910 `f_fund_iv` 算九月 carry 的数都继承这一差异**, 包括纲领 L165 由 T5 装置延展到九月的 T5c。
4. **T5 §6.1**: 「生产的止损证据采集器在 08-26 20Z 对 ONG 记下深度 −46.1% 的触发, 但它不改书」。该采集器按 king 形态影子书自己的成本记账; 执行器 ONG 在平仓前重建深度最低 −28.5%, 重建后为盈利。−46.1% 不是执行器的深度(不矛盾, 但不可互换引用)。
5. **执行器止损告警文案**「⇒ flatten_only(maker 出场, 不追)」: 多头已停名的记录桶是 add_blocked / reduced(§5.3)。

## §7 已核实 vs 推断
**已核实(有收据)**: 首个 FTRIM 锚; FTRIM + EMA + 带宽冻结机制(G-MECH); Q1 全部计数、份额、年龄与账本口径 carry; target_live = 0.55 kc + 0.45 fc; 执行器读取的文件 = 所分析文件(G-FILE); per_name_stop 配置与逐锚评估; 队列 NOT FIRED 与零计数; 执行器锚类; ONG 持仓 / 目标 / 平仓 / 重建时刻; 外部书跳过中性带与 harvest EMA(25 个版本); no_trade_band 状态文件自 08-22 未写; 执行器加冻计数与原因标签; 已停名记录桶与平移预测 122/122; SKR / SOPH / IOST 结算间隔的三方记录。
**推断 / 描述(未核实)**: x0910 面板间隔错误的成因(§5.1); 重建深度(用交易前 mid 代替 mark, 成本由 fills 回放); 已停名被钉住的代码路径(读码与记录吻合, 未运行执行器代码); 提交时刻 ≠ 部署时刻; 建模 carry ≠ 实付(T1: 实付 / 建模 0.892)。

## §8 修复检验的样子(只写检验, 不提议部署任何东西)
- **Q1 残余冻结**: 在平价回放装置上预注册两臂 —— 现行 FTRIM 与「FTRIM 名目标强制为 0 且免带宽」—— 窗与终点先写死, 报书层价格 + carry 双分解与换手成本; 判据先于数字。本测量只说明冻结部分的 carry 不大, 衰减期的空头 carry 才大, 所以检验应同时覆盖「更快出场」与「冻结」两件事。
- **已停多头不出场**(执行器行为): 先写一个会红的纯函数测试 —— 已停多头持仓 h > 0, 目标置 0, reshape 平移 a > h ⇒ 期望 flatten_only; 现行代码应判 add_blocked(红)。再在 W1 真账本副本上重放 125 个实例, 期望全部 flatten_only 且空头不变。任何代码改动都走 safe_commit + 全电池 + 用户字; 本轮不提。
- **carry 仪器**: 用结算间隔逐行重派生 x0910 的 `f_fund_iv`, 对照执行器 funding 行, 然后重算 T1 D2 九月 carry 与所有引用它的数。

## §9 偏离规格与实现说明
- SPEC §6.3 / §7.1 写「untradable_disposition 所在桶」: 实际记录中该字段是**计数**, 名单在 `untradable_names`(每桶前 12 名, `anchor_loop.py` L2124–L2129)。装置改读 `untradable_names`, 超过 12 名的桶标「成员未知」; add_blocked 名单超长时原因记 `no_row(add_blocked_list_truncated)`(本期 0 例)。
- `t5b_exec.py` 首跑在打印任何 Q2 / Q3 数字前因上述类型问题崩溃(只打印了 CONFIG 行), 修补后重跑; `t5b_q1.py` 首跑前改了一行时间解析(calendar.timegm)。
- 配置恒定标志为 false, 只因 37186e6(08-22 04:58Z)的 min_notional 20.0, 1 小时后 82476ad 改为 5.0, 均在 W2 之前。
- `t5b_tables.py` 首次渲染后改了三处文字: gross_mult 历史漏了一步; CD2 定位措辞(原写「Δ_non8h ≈ Δ」对 IOST 锚不准, 改为逐名比值); W2 触发事件按日期过滤误含 08-31 04Z 之后的三次触发, 改为按锚时。数字未改。
- 三个事后装置(§5)不在规格内, 均在看到对应结果后写成, 标 POST-HOC。

## §10 边界
- 建模 carry, 不是实付。F_A 取自生产者记录, 生产者不存档 z。
- W1 最后 15 锚无 CD2 对照; CD2 本身红, 账本口径与面板口径在 W1 的等价性只由三名第三方记录支持。
- 深度重建只作描述, 未用于回答 FIRED。
- 队列止损问题只覆盖 W2 与窗外事件列表, 不含 T5 回放止损在部署规则下的反事实。
- 已停名分析覆盖 W1 ∪ W2, 未扩到 08-20..08-25。

## §11 复跑(逐字; T5b 目录)
```
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T5b
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_copy.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_copy_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_copy_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_q1.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_q1_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_q1_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_diag_cd2.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_diag_cd2_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_diag_cd2_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_q1_posthoc.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_q1_posthoc_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_q1_posthoc_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_exec.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_exec_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_exec_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_exec_posthoc.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_exec_posthoc_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_exec_posthoc_rc.txt
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_tables.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING > receipts/t5b_tables_stdout.log 2>&1; rc=$?; echo "rc=$rc" > receipts/t5b_tables_rc.txt
```
重跑 `t5b_copy.py` 会以新时刻重新拷贝(aux.json 与运行日志在变), 之后的装置断言新清单 sha; 要复现本文数字, 用现存 `private/` 从第二行起跑。

## §12 产物
- 规格: `SPEC_T5b.md`、`receipts/SPEC_FREEZE_sha.txt`
- 装置: `devices/t5b_copy.py`、`t5b_common.py`、`t5b_q1.py`、`t5b_exec.py`、`t5b_tables.py`; 事后: `t5b_diag_cd2.py`、`t5b_q1_posthoc.py`、`t5b_exec_posthoc.py`
- 收据: `receipts/RECEIPT_T5b_copy.json`、`RECEIPT_T5b_q1.json`、`T5b_q1_instances.json`、`RECEIPT_T5b_diag_cd2.json`、`RECEIPT_T5b_q1_posthoc.json`、`RECEIPT_T5b_exec.json`、`T5b_exec_rows.json`、`RECEIPT_T5b_exec_posthoc.json`、`TABLES_T5b.md`, 以及每个装置的 `*_stdout.log` / `*_rc.txt`
- 不入库: `private/`(184 MB 只读副本, 清单 `private/COPY_SHA256.txt`)
- 校验和: `SHA256SUMS.txt`
