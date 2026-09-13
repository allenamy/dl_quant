> **创建:** 2026-09-13 ~08:05Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5b) | **状态:** 规格; 冻结先于任何 T5b 数字(sha 与冻结时刻记 `receipts/SPEC_FREEZE_sha.txt`, 每个计算装置运行前断言本文件 sha) | **作废条件:** 生产者存档(`~/wide_shadow/state/target_live`、`state/target_combo`、`fea171/state_H_{kc,fc}_*`、`state/aux*.json`)或执行器账本(`~/dl_quant_live/state/live/pilot_log/20260801..20260912`、`state/anchor_runs.log`、`state/notify_audit.jsonl`)在拷贝时刻之前的内容被改写; `T1/receipts/pod2/T1_d2.npz` 或 `T5/receipts/pod2/T5_bridge_components.npz` 被替换

# SPEC · T5b · 生产行为只读审计: FTRIM 残余冻结(Q1) / 执行器逐名止损对八月队列(Q2) / 执行器是否另加冻结(Q3)

## §0 范围与零接触
- 这是测量, 不是提案。三问由 lead 派工(消息「T5b FTRIM residual and live stop audit」; 纲领 `PROGRAM_uplift_r2_2026-09-13.md` L155)。背景出处: `T5/RESULT_T5_deployed_carry_gap_2026-09-13.md` §0 / §6.1 / §8(iii)。
- `~/wide_shadow`、`~/dl_quant_live` 一律不写。所需文件拷入 `T5b/private/`(gitignored), 清单 `private/COPY_SHA256.txt`(逐文件断言 源 sha == 副本 sha)。不拷 `.env` 与凭据; 拷入的文本文件做凭据模式扫描(`TELEGRAM_BOT_TOKEN`、`BINANCE_API`、`apiKey`、`secretKey`、`X-MBX-APIKEY`、`signature=`、`bot<数字>:<35 位>`), 命中 ⇒ 删副本, 清单记 `SKIPPED_SECRET`, 结果里说明。
- 执行器 git 只用只读命令(`git -C ~/dl_quant_live log` / `show <commit>:<path>`), 输出写入 `private/`。
- 无交易所 / 网络 / Telegram 调用; 不碰看门狗、launchctl、任何进程; 只用本机 CPU; `env -i` + 白名单 8 项(CPATH, HOME, LC_CTYPE, LIBRARY_PATH, MANPATH, PATH, SDKROOT, __CF_USER_TEXT_ENCODING; 同 T5 Mac 装置)逐项断言; `/usr/bin/python3`; 前台运行, rc 与汇总行写入 `receipts/`。
- 不触碰 T4 / T4b / T5c / T6 / T7 / P2(parity_replay phase2)目录。

## §1 继承口径(沿用 T5 / T1)
- **建模 carry**: `c4(A,i) = rate(A,i) × 4 / iv(A,i)`; 书层 `C = Σ_i w_i·c4(A,i) / Σ_j |w_j| × 1e4`, 单位 bps / 4h 锚 / 单位 gross, **正 = 付**(T5 RESULT 头注; `t5_bridge.py` L47–L48, L224)。
- **rn8**: `rate × 8 / iv`。
- **rate / iv 的来源**: T5 用 x0910 面板 `f_fund_now / f_fund_iv`(pod2, 末锚 09-10 00Z)。本任务只许本机 CPU, 且 W1 到 09-12 12Z ⇒ **按面板的同一定义在生产者资金费账本上重建**: 名 i 在锚 A 取 `ledger_tail[i]` 中 `ft ≤ A` 的最后一行 `(ft, rate, iv)`; `A − ft > 12h` ⇒ NaN ⇒ carry 记 0(面板 `retrain_2026-09/pod_panel_ext.py` L153–L162 陈旧规则; T5 `nan_to_num`); `iv` 非有限或 ≤ 0 ⇒ 8.0(`combo_stage.py` L242–L243 与 T5 L47 同)。
- **账本** = 拷贝时刻的 `state/aux.json` ∪ `state/aux_pre_m1_20260904.json`, 按 `(symbol, ft)` 合并, 重叠行 rate 与 iv 必须逐值相等(G-LEDGER)。
- 与 T5 口径的等价性**由 G-CARRY 实测**(§5), 不由论证。
- **锚地板**: 执行器记录的 `anchor_ts`(≈ N+23..24 分)一律 `G(t) = floor(t / 14400) × 14400` 映射到名义锚(T1 `t1_realized.py` L24)。
- **执行器账本读法**(T1 `t1_realized.py`): anchors.jsonl 同 G 取最后一行; position_readback 同 (G, symbol) 取最后一行; fills 按 trade_id 去重; funding 按 (symbol, settlement_ts) 去重。
- **日块自举**(T5 `t5_bridge.py` L281–L286 `boot_ratio` 原式): B = 2000, `rng = numpy.random.default_rng([20260905, k])`, 块 = UTC 日(`A // 86400`), 统计量 = Σ分子 / Σ分母, 百分位 [2.5, 97.5]。各量的 k 在 §4 / §7 写死。

## §2 锚集(端点写死)
| 名 | 首锚 | 末锚 | 锚数 | 用途 |
|---|---|---|---|---|
| W1 | 2026-09-02 12:00Z (1788350400) | 2026-09-12 12:00Z (1789214400) | 61 | Q1, Q3 |
| W1⁻ | 2026-09-02 08:00Z (1788336000) | — | 1 | 只作 W1 首锚的「上一锚」 |
| W2 | 2026-08-26 00:00Z (1787702400) | 2026-08-31 00:00Z (1788134400) | 31 | Q2 |
| W2⁺ | 2026-08-31 04:00Z (1788148800) | 2026-09-12 12:00Z (1789214400) | 75 | Q2 队列名窗外止损事件, 只列事件, 不进回答 |
| CT5 | T5 的 27 个 A_T5 锚(`T5/receipts/pod2/T5_bridge_components.npz` 键 `AT5`) | | 27 | G-CARRY 对照 |
| CD2 | `T1/receipts/pod2/T1_d2.npz` 中 A ∈ [1788350400, 1788998400 = 09-10 00Z] 的锚 | | ≤ 46 | G-CARRY 对照 |

- **首个 FTRIM 锚 = 2026-09-02 12:00Z**。出处: (a) `~/wide_shadow/state/target_combo/1788350400.json` 是 09-02 起第一个含 `ftrim` 键的记录, 09-02 00Z / 04Z / 08Z 三个记录无此键; (b) `~/wide_shadow/fea171/combo_live.log` 第 337 行块头 `anchor 09-02 12:00`, 其第 342 行是该日志第一行 `FTRIM 负费率空头排除`; (c) `combo_stage.py` mtime 2026-09-02 08:59Z。装置重新断言 (a)(b)。
- Q3 派工写「09-02 09Z..09-12 12Z」; 不早于 09-02 09Z 的第一个 4h 锚是 12Z ⇒ Q3 锚集 = W1。
- W1 共 11 个 UTC 日块: 09-02 3 锚(12/16/20Z), 09-03..09-11 各 6 锚, 09-12 4 锚(00/04/08/12Z)。

## §3 数据源(全部先拷入 `private/`)
- 生产者 `~/wide_shadow`: `state/target_live/<A>.json` 及 `.sha256`, `state/target_combo/<A>.json`, A ∈ [1787688000 (08-25 20Z), 1789214400]; `fea171/state_H_kc_<A>.npz`、`fea171/state_H_fc_<A>.npz`, A ∈ [1788336000, 1789214400]; `state/aux.json`、`state/aux_pre_m1_20260904.json`; `fea171/xfer_ref.npz`(829 名轴); `shadow_bundle/config.json`(params: alpha / band / cap_mult / qv4h_min); `fea171/combo_stage.py`、`fea171/combo_live.log`、`fea171/combo_live_daemon.sh`、`fea171/check_ftrim_anchor.py`。
- 执行器 `~/dl_quant_live`: `state/live/pilot_log/<day>/{_schema.json, anchors, orders, fills, position_readback, funding}.jsonl`, day ∈ [20260801, 20260912]; `state/anchor_runs.log`、`state/notify_audit.jsonl`、`state/launchd_out.log`; `state/live/per_name_stop.json`、`state/live/no_trade_band.json`、`state/no_trade_band.json`; 工作树 `config/book.json`、`live/per_name_stop.py`、`scheduler/anchor_loop.py`、`live/binance_executor.py`、`live/external_book.py`; 以及 §6.4 / §7.4 提交集的 `git show` 版本。
- 研究仓(只读): `T1/receipts/pod2/T1_d2.npz`、`T5/receipts/pod2/T5_bridge_components.npz`、`T5/receipts/pod2/RECEIPT_T5_bridge.json`。

## §4 Q1 · 目标层 FTRIM 残余冻结(W1)
### 4.1 记号
- 名轴: `xfer_ref.npz` 的 829 个 symbols, 断言等于 `shadow_bundle/config.json` 的 `symbols_panel`。
- `w_kc(A)`、`w_fc(A)`: `state_H_{kc,fc}_<A>.npz` 的 idx / val 展开到 829 轴, 断言文件内 `anchor == A`。
- `w_tl(A)`: `target_live/<A>.json` 的 weights 展开; 出现 829 轴外的名 ⇒ 装置红。
- `K(A) = ftrim.names_kc`, `Fc(A) = ftrim.names_fc`(`target_combo/<A>.json`); **`F_A = K(A) ∪ Fc(A)`**。
### 4.2 锚纳入(逐锚判定; 排除的锚列出原因)
- 链 c ∈ {kc, fc} 在 A 纳入, 当且仅当: target_combo(A) 含 `ftrim`; `{c}_state_source == "own"`; 状态文件 A 与 A−4h 都存在且 anchor 字段正确。W1 首锚的上一锚是 W1⁻。
- tl 在 A 纳入, 当且仅当两条链都纳入, 且 target_live(A) 与 target_live(A−4h) 的 `producer` 都含 `combo_stage`。
### 4.3 逐锚量(书 b ∈ {kc, fc, tl})
- 书的 F 集: `S_kc(A) = K(A)`, `S_fc(A) = Fc(A)`, `S_tl(A) = F_A`。
- `RES_b(A) = { i ∈ S_b(A) : |w_b(A)_i| > 1e-6 }`
- `FROZ_b(A) = { i ∈ RES_b(A) : w_b(A)_i == w_b(A−4h)_i }`(float64 逐位相等)
- 计数 `n_RES`, `n_FROZ`; gross 份额 `Σ_{i∈set} |w_b(A)_i| / Σ_j |w_b(A)_j|`。
- carry: `C_b^set(A) = Σ_{i∈set} w_b(A)_i · c4(A,i) / Σ_j |w_b(A)_j| × 1e4`, set ∈ {RES, FROZ}。
- tl 链分解变体(一名可只在一条链冻结): `C_tlchain^FROZ(A) = [0.55 · Σ_{i∈FROZ_kc(A)} w_kc(A)_i c4(A,i) + 0.45 · Σ_{i∈FROZ_fc(A)} w_fc(A)_i c4(A,i)] / Σ_j |w_tl(A)_j| × 1e4`。
- 年龄(连续冻结锚数): `age_b(A,i) = age_b(A−4h,i) + 1` 若 i ∈ FROZ_b(A), 否则 0; W1 首锚之前记 0(FTRIM 自 W1 首锚起才存在, 无左删失); 书在某锚未纳入 ⇒ 该锚记 0(断链)。报: 池化 (A, i) 的 min / p25 / p50 / p75 / p90 / max 与分箱 {1, 2, 3, 4–6, 7–12, 13–24, 25–48, ≥49}; 每名最长连续段与是否在 W1 末锚右删失; 曾冻结的不同名数。
- 累计: `cum_b^set(A) = Σ_{A' ≤ A} C_b^set(A')`; 窗均值 = 纳入锚上的算术均值。
- 描述(不入读法): 离开 F 后权重仍不变的 (A, i) 计数(i ∉ S_b(A), i ∈ S_b(A−4h), `|w| > 1e-6`, 权重逐位不变)。
### 4.4 读法(冻结; 阈值由 lead 给定)
- **主量 X̄ = tl 纳入锚上 `C_tl^FROZ(A)` 的均值**(bps / 锚 / 单位 gross, 正 = 付)。
- **FROZEN-RESIDUAL-MATERIAL ⇔ X̄ ≥ 0.05; 否则 NOT MATERIAL。**
- CI: 日块自举 k = 501; 只报告, 不参与读法。
- 次级读法(同一阈值, 标「次级」, 不得替代主读法): `C_tlchain^FROZ`(k = 502)、`C_tl^RES`(503)、`C_kc^FROZ`(504)、`C_fc^FROZ`(505)、`C_kc^RES`(506)、`C_fc^RES`(507)。gross 份额 CI: tl FROZ k = 511, tl RES k = 512。
- 主量取 tl 字面冻结的理由: 执行器读的是 target_live, 「与上一锚权重相同」按字面作用于这本书时最保守。链分解与全残余作为次级, 因为一名可能在一条链冻结、另一条仍在衰减。
- 若 G-CARRY(i) 不过 ⇒ 读法加注 PROVISIONAL(carry 装置与 T5 口径不一致), 数字照报, 由 lead 裁。

## §5 Q1 的门
- **G-ARCH**(不过 ⇒ 该锚 tl 不纳入): `max_i |w_tl(A)_i − (0.55 w_kc(A)_i + 0.45 w_fc(A)_i)| ≤ 1e-12`。
- **G-LEDGER**(阻断): 两份账本重叠 (symbol, ft) 行的 rate 与 iv 逐值相等; 任何在 W1 或 CT5 的某锚 `|w| > 1e-6` 的名, 若该名账本行数达 400 上限且首行 `ft > A − 12h`(= 尾巴被截, 不是未上市) ⇒ 红。
- **G-RN8**(不阻断, 诊断): 每个 W1 锚、F_A 中每名 `|rn8_ledger(A) − rn8_record| ≤ 6e-8`(记录按 7 位小数舍入)。不符者再测是否等于 `ft < A` 的前一结算行(= 生产者运行时该锚结算尚未入账), 分两类计数。
- **G-MECH**(只决定「机制确认」这句话能否写, 不阻断数字): 链 c、锚 A、`i ∈ S_c(A)` 且 `H_i = w_c(A−4h)_i ≠ 0`: EXIT = `w_c(A)_i == 0`; MOVED = `w_c(A)_i ≠ H_i` 且非 EXIT; 隐含目标 `t*_i = H_i + (w_c(A)_i − H_i) / α`; α、band 取 config(断言 α = 0.1, band = 2.5e-4)。(a) 同链同锚全部 MOVED 名的 `t*_i` 极差 ≤ 1e-12(z 置零后去均值 ⇒ 同一目标); (b) MOVED 名 `|w_i − H_i| ≥ band`; (c) t* 可识别的 (c, A) 上, 预测冻结 `|α (t* − H_i)| < band` 与观测冻结 `w_i == H_i` 对全部非 EXIT 名逐一相等。报可识别 / 不可识别的 (c, A) 数与不符名单。
- **G-CARRY**: (i) **CD2**(不过 ⇒ Q1 读法加 PROVISIONAL): 用本装置 c4 与 T1 D2 同式重算(`T1/devices/t1_d2.py` L46–L62: 权重映射 829 轴; carry = Σ w·c4 / Σ|w| × 1e4; coh = `w < 0 ∧ rn8 ≤ −0.0010`), 与 `T1_d2.npz` 的 `carry`、`coh_carry` 逐锚 `|Δ| ≤ 1e-3 bps`; (ii) **CT5**(不阻断, 报告): 27 锚逐锚书层 carry 对 `T5_bridge_components.npz` 的 `C_D` `|Δ| ≤ 1e-3`, 以及 TC1 两格部署书均值(`RECEIPT_T5_bridge.json` 的 `result.seeds["42"].LS.cells["short|<=-30bp"].D` 与 `["short|-30..-10bp"].D`)`|Δ| ≤ 1e-3`; 不过则列出 |Δ| 最大的锚与名。
- **G-DET**(阻断): 在内存副本上做突变: M1 取一个观测冻结实例, 令 `w(A)_i += 1e-9` ⇒ 检测器必须判非冻结; M2 取一个 MOVED 实例, 令 `w(A)_i := w(A−4h)_i` ⇒ 必须判冻结; M3 令 `c4 ≡ 0` ⇒ 全部 carry 恰为 0; M4 令 `c4 → −c4` ⇒ carry 恰取负。任一格不符 ⇒ 装置红, 不出数。
- **对侧尺子**: CT5 上部署书「空头 ∧ rn8 ≤ −10bp」队列 carry(T5 报 D ≈ 1.304 + 0.333)在 ≥ 0.05 一侧; M3 在 0 一侧。

## §6 Q2 · 执行器层: 八月队列(W2)
### 6.1 队列
ONGUSDT, ACEUSDT, TUTUSDT, COTIUSDT, HOMEUSDT, BICOUSDT, SANDUSDT, STORJUSDT(派工给定)。
### 6.2 执行器锚分类(每个名义锚 A)
- 解析 `anchor_runs.log` 的 `anchor start mode=LIVE` 块, 取块内 `phase_A`(`G(anchor_ts) == A`)与 `phase_C`; 同一 A 多块时取最后一个含 phase_C 的块, 并报块数。
- 类(按以下顺序取第一个命中者, 一锚一类; 另报全部命中标记): NO_LIVE_RUN(无 LIVE phase_A)/ NOT_TRADE(phase_A 无 `action` 或 `action ≠ "TRADE"`)/ EXT_UNAVAILABLE(`phase_A.external_book.ok` 非 True)/ HALTED(anchors 行 `opening_halted` 为真, 或该 G 有 `terminal_reason == blocked_by_halt` 的订单行)/ PROTECTIVE(该 G 有 `order_type == protective_flatten` 的订单行)/ NORMAL(其余, 且 anchors 行与 readback 行都存在; 缺任一 ⇒ INCOMPLETE)。
### 6.3 逐名逐锚列(W2 × 队列)
| 列 | 定义 |
|---|---|
| `tl_w`, `producer` | target_live(A) 权重(缺席 = 0)与 producer 串 |
| `json_sha_ok` | `phase_A.external_book.json_sha == sha256(private 副本 target_live/<A>.json)`(G-FILE) |
| `t_file`, `T_file` | `t_file = tl_w / phase_A.external_book.gross_in`; `T_file = t_file × S(A)`, `S(A) = phase_A.sizing.gross`(USDT) |
| `T_exec` | 该 (G, i) 中 attempt_idx 最小的 maker 行 `target_w × anchors.target_gross`; 无行 ⇒ NA, 原因取 `phase_A.untradable_disposition` 所在桶 / `external_filters.below_min_notional.names` / 不在 symbols |
| `H_pre` | 同一行 `prev_w × anchors.target_gross` |
| `H_post`, `q_post` | position_readback(G, i) 的 `venue_position_notional` / `venue_position_qty`; 无行 = NA |
| `filled` | 该 (G, i) 全部订单行 `filled_notional` 之和(含 None ⇒ NA) |
| `disposition` | 该 (G, i) 订单行的 `order_type:terminal_reason` 集合; untradable 桶; `phase_A.untradable_reason` 若提及该名 |
| `pns_counter`, `pns_stopped` | 该锚 LIVE `phase_C.per_name_stop.counters[i]`(缺 = 0); `i ∈ phase_C.per_name_stop.stopped` |
| `depth_rec` | §6.5 重建深度, 标 RECONSTRUCTED |
| `events` | `notify_audit.jsonl` 与 `launchd_out.log` 中含该名的 per_name_stop 文案(触发 / 已出场进入冷却 / 冷却期满), 带 ts |
### 6.4 回答规则(冻结)
- **配置**: 提交集 `C_cfg` = `git log --since=2026-08-22T04:58:00Z --until=2026-09-12T12:00:00Z -- config/book.json` 的全部提交 ∪ 工作树; 每个版本按 `per_name_stop.resolve_profile` 语义解析, 报 enabled / active_profile / depth_pct / consecutive_anchors / cooloff_days / min_notional_usdt 与 book_source, 断言各版本在这些键上相同(不同则逐版本列出与提交时间)。
- **FIRED** 仅当 W2 内存在记录: notify_audit 或 launchd_out 中「per_name_stop 触发: <SYM>」, 或某 LIVE phase_C 的 stopped 含该名; 报首次时刻、所在名义锚、文案中的深度。
- **NOT FIRED** 其余情形; 必须同时报: W2 的 31 锚中 LIVE phase_C 带 per_name_stop 字典的锚数(条款实际被评估的锚数), 与该名 counter ≥ 1 的锚。
- 重建深度只作描述, 不得用于判定 FIRED / NOT FIRED。
- **持仓对目标**: NORMAL 锚上逐名报 `H_post / T_file` 与 `H_post − T_file`(USDT 与 /S); 窗内中位与分位; 另报队列合计 `Σ_i (H_post/S − t_file) · c4 × 1e4`(描述)。
- **W2⁺**: 队列名在窗外的 per_name_stop 事件只列, 标「窗外」。
### 6.5 深度重建(描述性)
- 深度 = `sign(q) · (1 − entry / mark)`, 与 `live/per_name_stop.py` L122 `unrealized / |notional|` 同义; mark 用同锚 anchors.jsonl 的 `mid_at_anchor_vector`(交易前采样, 近似)。
- entry: 自 20260801 起按 `fill_ts` 顺序回放该名 fills(trade_id 去重; `qty = ±fill_notional / fill_px`, buy 为正): 从 0 开仓或穿越 0 ⇒ entry = 该笔价; 同向加仓 ⇒ 数量加权; 减仓 ⇒ entry 不变。
- **G-QTY**: 每个 readback(G, i)处, 回放数量(`fill_ts ≤ read_ts`)与 `venue_position_qty` 相对差 ≤ `1e-6 × max(1, |q|)`; 不符 ⇒ 自该锚起 `depth_rec = NOT RECONSTRUCTIBLE`, 直到某 readback 数量为 0 时重置回放。
- 一致性描述: `depth_rec ≤ −0.30` 与 `pns_counter ≥ 1 或 pns_stopped` 的一致 / 不一致计数。

## §7 Q3 · 执行器层: F_A 名在 W1
### 7.1 逐 (A, i ∈ F_A) 量
§6.3 各列(tl_w, t_file, T_file, T_exec, H_pre, H_post, q_post, filled, disposition), 另:
- `PROD_FROZEN_TL(A,i) = i ∈ FROZ_tl(A)`(§4.3; tl 未纳入的锚记 NA)。
- `EXEC_FROZEN(A,i)`: readback(G(A−4h), i) 与 readback(G(A), i) 两行都存在, `venue_position_qty` 逐位相等且 ≠ 0。
- **执行器加冻** `X(A) = { i ∈ F_A : EXEC_FROZEN ∧ ¬PROD_FROZEN_TL }`, 只在 A 与 A−4h 都是 NORMAL 时计入。原因按行标签、按此优先级取一: `halt`(blocked_by_halt)/ `add_blocked`(untradable_disposition.add_blocked)/ `min_notional_skip`(skipped_min_notional)/ `no_chase`(skipped_no_chase_arm)/ `unfilled`(有提交且 Σ filled == 0: partial_expired / venue_reject / abandoned_*)/ `no_row` / `other`。rule 类 = {add_blocked, min_notional_skip, no_chase}; fill 类 = {unfilled}。
### 7.2 carry
- `C_file^F(A) = Σ_{i∈F_A} t_file(A,i) · c4(A,i) × 1e4`
- `C_held^F(A) = Σ_{i∈F_A} (H_post(A,i) / S(A)) · c4(A,i) × 1e4`
- `GAP_ALL(A) = C_held^F(A) − C_file^F(A)`
- `GAP_EXECFREEZE(A) = Σ_{i∈X(A)} (H_post(A,i)/S(A) − t_file(A,i)) · c4(A,i) × 1e4`; 另报 rule 类与 fill 类的拆分。
### 7.3 读法(**T5b 自加, 不是派工给定**; 冻结)
- **Ȳ = W1 ∩ NORMAL 锚上 `GAP_EXECFREEZE(A)` 的均值。EXECUTOR-ADDED-FREEZE-MATERIAL ⇔ Ȳ ≥ 0.05 bps / 锚 / 单位 gross; 否则 NOT MATERIAL。** CI k = 601。
- 描述: `GAP_ALL`(k = 602)、`C_file^F`(603)、`C_held^F`(604)、`GAP_EXECFREEZE` rule 类(605)/ fill 类(606); X(A) 按原因的 (A, i) 计数与 |H_post − T_file| USDT; 执行器加冻连续段长度分布; `PROD_FROZEN_TL ∧ ¬EXEC_FROZEN` 计数(目标冻结而执行器仍交易)。
- 非 NORMAL 锚单列类别与计数, 不进 Ȳ。
### 7.4 no_trade_band 与执行器其他冻结机制(代码 + 数据)
- **G-CODE**: 提交集 `C_code` = `git log --since=2026-08-22T04:58:00Z --until=2026-09-12T12:00:00Z -- scheduler/anchor_loop.py live/binance_executor.py live/per_name_stop.py live/external_book.py` ∪ 工作树。每个版本断言并逐项报: `anchor_loop.py` 外部书分支含中性带跳过(`"skipped": "external_book"` 与 `"applied": False`)与 harvest EMA 跳过; `binance_executor.py` 含 `DEFAULT_BAND_BPS = 0.0`, 且非测试代码无 `band_bps=` 覆写; `plan()` 含 `skipped_min_notional` 跳过; `anchor_loop.py` 含 2×minNotional 撤下(`below_min_notional`)与 `apply_withhold_and_reshape`。限制: 提交时刻 ≠ 部署时刻(落盘即上线; 存在「分支未部署」提交)。
- **数据**: `state/live/no_trade_band.json` 的 `rebalance_id` / `written_at`(内部书分支每锚写, 外部书分支不写); W1 / W2 的 LIVE phase_A 中若出现 no_trade_band 记录则报其 applied。
### 7.5 门
- **G-FILE**(不过 ⇒ 该锚 t_file 为 NA): 执行器记录 json_sha == 副本 sha; 并用副本重算宇宙内 `Σ|w|` 与记录 `gross_in` 相对差 ≤ 1e-9。
- **G-PLAN**(不阻断): maker 行 `|(target_w − prev_w) · target_gross − intended_full| ≤ 1e-6 · target_gross`。
- **G-S**(不阻断): anchors 行 `reshape.sizing_gross`(若 reshape 为含该键的 dict)与 `phase_A.sizing.gross` 相对差 ≤ 1e-9; 09-05 12Z 至 09-08 06Z 的 reshape 字段被拒单率报告覆盖(执行器提交 64c4a16 所修的 E-0908-A), 该段缺失如实记。

## §8 产物
- 装置: `devices/t5b_copy.py`(拷贝 + 清单 + 凭据扫描 + git show 导出, 不计算)、`devices/t5b_q1.py`、`devices/t5b_exec.py`(Q2 + Q3)、`devices/t5b_tables.py`(从收据渲染表)。每个计算装置断言本规格 sha、`private/COPY_SHA256.txt` 的 sha 与 env 白名单; 收据 JSON 自报 self_sha256 / 输入 sha / env / 版本 / 时间。stdout 与 rc 写 `receipts/*_stdout.log` 与 `receipts/*_rc.txt`。
- `RESULT_T5b.md`(元信息头; 三问回答与读法; 门; 与 T5 或既有收据矛盾之处逐条引原文; 已核实与推断分栏; 一段标明的「修复检验的样子」)、`SHA256SUMS.txt`。

## §9 不测什么 / 边界
- 建模 carry 不是实付(T1: 同 78 锚实付 / 建模 0.892)。
- F_A 取自生产者自己的记录; 生产者不存档 z, 无法独立重算 FTRIM 名单。
- 深度重建依赖 fills 完整与 mid ≈ mark, 只作描述。
- 配置与代码按提交读; 运行树在提交之间可能有未提交状态。
- W1 中 09-10 04Z 之后的 15 锚没有 CD2 对照, 账本装置在这段的等价性是外推。
- 不测价格, 不测成交质量, 不提议任何书行为改动(RESULT 里只有一段标明的「修复检验的样子」)。

## §10 冻结前已看过的内容(如实)
- 读过: STATE.md 头部、TEAM_PROTOCOL、T5 RESULT / PREREG 片段 / `t5_live_ingredients.py` / `t5_bridge.py`、T1 `t1_d2.py` / `t1_realized.py` 与 T1 / T5 收据的键结构(数值只看过 T5 RESULT 已公开的 `C_D` 头条 2.186 与 TC1 两格 1.304 / 0.333)。
- 生产者: `combo_stage.py` 全文; config params(alpha 0.1, band 2.5e-4, cap_mult 2.5, qv4h_min 2.5e5, 829 / 450 名); W1⁻..09-13 00Z 共 65 锚的 target_live / target_combo / state_H_kc / state_H_fc / weights 文件均存在(只查存在); 首个含 ftrim 键的 target_combo; `combo_live.log` 第 342 / 351 / 360 行(09-02 12Z / 16Z / 20Z 的 FTRIM 计数 kc 11 / fc 11、9 / 9、8 / 8); aux.json 账本尾巴的覆盖范围(最早 07-07 08Z, 每名 42..400 行); `stop_overlay.py` 全文与其日志头部格式行。
- 执行器: `per_name_stop.py` 全文; `anchor_loop.py` L1440–L1990、L2040–L2110、L2500–L2700; `binance_executor.py` `plan()` 与订单行构造; `config/book.json` 的 per_name_stop 块(enabled, active_profile wide: −0.30 / 2 / 7 天 / 5 USDT)与 book.json 的提交历史(含提交信息里 08-26 12:47Z §4-5e 停机与之后的 gross_mult 爬坡); `state/live/per_name_stop.json` 当前内容(冷却 10 名: COLLECT, CYS, FLOCK, HEMI, IOST, LSK, MAGMA, RIVER, TRIA, XAN, 均不在队列内); 两份 `no_trade_band.json` 当前内容(live 那份写于 A1787371250 = 08-22 04:00Z); pilot_log 表结构; 08-26 anchors.jsonl 6 行的键与 rebalance_id / opening_halted(A1787761380 = 08-26 16:23Z 为 True); 08-27 orders 的 terminal_reason / order_type 全日计数; 08-25..09-13 订单类型与终态的全窗合计计数(含 protective_flatten 1100 行、blocked_by_halt 2379 行); anchor_runs.log 在 08-20 与 09-13 00Z / 04Z 的 phase_C 行(counters 空, cooldown_n 10)与 08-27 12Z LIVE 块的 phase_A / B / C 键名; notify_audit.jsonl 键结构。
- **没有计算**: 任何 Q1 / Q2 / Q3 的量(冻结与否、残余计数、carry、队列逐名执行器记录、止损事件)都没有看过或算过。
