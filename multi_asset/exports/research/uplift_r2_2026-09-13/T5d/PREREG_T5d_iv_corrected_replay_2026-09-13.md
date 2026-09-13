> **创建:** 2026-09-13 ~12:17Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5, 任务 T5d) | **状态:** 预注册; 冻结先于任何 T5d 结果数字(sha 与冻结时刻记 `receipts/PREREG_FREEZE_sha.txt`, 以显式路径提交; 每个装置运行前断言) | **作废条件:** 生产者账本快照、执行器 funding 记录或 x0910 延展产物被改写; T5c 臂或 KA 数组被替换; 用户改比较层
> **上游:** 独立复审第四轮 `…/codex-independent-20260907/docs/REVIEW_round4_code_and_research_2026-09-13.md` §4.1 与同 worktree `…/codex_round4_code_review_2026-09-13/research/RESULT.md` §2、§6(只读); `../T5c/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md`(sha `a669c627…6a48`)与其 RESULT; `../T5b/RESULT_T5b.md` §5.1

# PREREG · T5d · 用真实结算间隔重做九月同锚(重生成 FTRIM、状态与权重)

## §0 问题与地位
- T5c 的回放 king 链在九月 x0910 延展段读了错误的结算间隔。间隔进入回放的 FTRIM 触发(`FN × 8/IV ≤ −10bp`)、fund 腿 v1 EMA(`rate × 8/iv`)与 carry。所以 T5c「价格不受间隔影响」只对**固定权重再计价**成立。
- T5d 用真实间隔重建九月面板的受影响格, 重跑同一回放装置与桥, 并**同时**报告两个差: 固定权重再计价、重新生成权重。
- 修正标签谓词: 「亏损」标签必须有实际负收益。
- 比较层、窗、king 链范围、V2MAIN NOT MEASURED 全部沿用 T5c; **不以 FIX7 或任何其它 V2MAIN 替代**。执行器层与实现账本层不在范围内。会计分解, 不是因果宣称。约 11 个日块 ⇒ CI 只作描述。

## §1 写本文前已知的事实(申报)
**缺陷机制(读码, pod2 `/workspace/uplift_2026-09-11/r6/r6_panel_splice.py` sha `cccc5b6b…743d`)**: 九月 REST 行一律取 `SEP_IV[s]`(拉取时刻 09-11 15:04Z 的单一间隔), 八月 REST 行取 `AUG_IV[s]`; 去重后「有记录间隔」优先于时间戳间隔, 故改过间隔的名在延展段所有行被赋同一个间隔; `rate_nf = rate × 8/iv` 进 v1 与 v2 EMA 续算。
**结构扫描(`devices/t5d_prefreeze_scan.py`, 收据 `receipts/RECEIPT_T5d_prefreeze_scan.json`, 无收益数字)**: 以相邻结算时间戳间隔为准, 日历 08-30 04Z..09-10 00Z 上: 在位行(≤ 08-31 00Z)检查 4,056 格, **间隔不符 0**; 延展行检查 40,552 格, **不符 547 格, 23 个名**, 60 个延展行每行 7–14 名; 在位结算的费率与面板 `f_fund_now` 不符 **0**。受影响名: COTI、GLW、GOOGL、GS、HD、HK0700、HK1810、IOST、MINIMAX、NVDA、POPMART、PYPL、QCOM、SKR、SOPH、STRC、TENCENT、TER、T、WDC、WEN、ZHIPU、ZKC(多数为代币化股票, 回放 CRYPTO 掩码不含它们, 但它们进 829 基的 fund 秩)。
**独立来源**: T5b §5.1 在 SKR、SOPH、IOST 上核实生产者账本与执行器 fundingInfo 一致而 x0910 不一致; 执行器 `~/dl_quant_live/state/live/pilot_log/<day>/funding.jsonl` 08-30..09-11 有逐结算 `funding_interval_h`(只含持仓名)。
**已看过的数字**: T5c 全部结果(价格 部署 −5.96、回放 −4.76 / −5.07, 差 −1.20 [−4.19, +1.59] 等); 复审合成例(IV 8→1, 重生成权重价格 −2.00893 → 0); T5b §5.1 的逐名比值; r18 C0 W_ALPHA 净额 +0.6342 bps/锚。**没有看过**任何用修正间隔算出的价格、carry、净额或权重。

## §2 修正后的结算间隔与面板
- **事件流**: 逐名照抄 `r6_panel_splice.py` 的事件流构建(zip + `fund_aug.json.gz` + `r6_fund_sep.json.gz`, 同一去重)。
- **真实间隔 iv_true(逐结算)**: (a) 该名该结算在生产者账本(`aux_pre_m1_20260904.json` 与 `aux.json` 两个快照的 `ledger_tail`, 按结算秒对齐)中有记录 ⇒ 取账本 iv; (b) 否则取该结算与事件流中上一结算的时间戳间隔, 按生产者同一规则取整到 {1, 2, 4, 6, 8}(并列取较小者)。来源逐结算记入收据。
- **修正面板**: x0910 面板的延展行(> 2026-08-31 00Z)按 r6 原代数重算 `f_fund_now`、`f_fund_iv`、`f_fund_ema`、`f_fund_ema_v1`、`f_fund_ema_v2`, 只把 `iv_full` 换成 iv_true; 其它键与在位行逐位拷贝。文件放 pod2 `T5d/panel/`。
- **门**:
  - **G-R6(阻断)**: 同一代码用 r6 原 `iv_full` 重算的延展格与 x0910 面板逐位相等(五个键, 全部名)。不过 ⇒ 停下。
  - **G-IV-LEDGER(不阻断)**: 同时有账本记录与时间戳间隔的结算, 两者不符的计数与名单。
  - **G-IV-EXEC(不阻断)**: 执行器 fundingInfo 记录的结算上, iv_true 与 `funding_interval_h` 不符的计数与名单(改间隔的过渡结算单列)。
  - **G-SCOPE(阻断)**: 修正面板与 x0910 只在延展行的 `f_fund_iv`、`f_fund_ema_v1`、`f_fund_ema_v2` 上有差; `f_fund_now` 与 `f_fund_ema` 逐位不变; 其它键逐位不变。报告每键差格数与名单。

## §3 回放重跑
- 装置 = T5c 的 `w10_sleeve_t5c.py`(sha `23604230…a8c5`)原样; 旋钮、KA 与 KB 两条 king 谱系、延展掩码、F10 预测、记账元均与 T5c 相同(sha 断言); 唯一改动 = 面板链接指向修正面板。KA × {42, 2027}、KB × {42, 2027}。
- **G-X′(阻断)**: T5d 四个臂与对应 T5c 臂在锚 ≤ 2026-08-31 00Z 的行上全部数组逐位相等(T5c 已对 T1 臂 ≤ 08-30 20Z 逐位成立)。

## §4 两个差(对 T5c 表)
- **固定权重再计价**: T5c 的 R_K(两个种子)与 D_K 权重不动, carry 与净额改用修正面板的 `C4`; 价格与成本不读间隔, 必须与 T5c 逐位相同(**G-FIXW, 阻断**)。
- **重新生成权重**: T5d 的 R_K(修正面板重跑)用修正 `C4` 计价。
- 报告: 每个种子、每个结果量(价格、carry、成本、净额)的 T5c 值、固定权重修正值、重生成修正值; Δ_fixed = 固定 − T5c, Δ_regen = 重生成 − T5c, 两者之差 = 权重重生成效应; D_K 只有 Δ_fixed(存档权重不重生成; 部署 FTRIM 用账本费率, 不读 x0910)。另报窗内 FTRIM 触发状态改变的名 × 锚与其所在锚。
- **G-T5C(阻断)**: 桥从 T5c 臂重算的 T5c 口径读数与 T5c 收据逐位复现(≤ 1e-9)。

## §5 桥
T5c 桥原样(9 组 512 节点, Shapley 主、固定顺序次、单组与留一描述; 分段均值; 去 09-06 与 KB 敏感性; 多空透镜与名单), 输入换为 T5d 臂与修正面板的 `C4`、`RN8`; D 侧成分沿用 T5c(生产者来源, 不读 x0910)。门 G-RAW、G-SIM-R、G-ARCH-D、G-CLOSE 同 T5c; G-T1c 在 x0910 口径上复现 T1 D2(证明读取无误), 修正口径的部署书 carry 另报。

## §6 读法(先写死)
### §6.1 标签谓词(修正)
价格与净额(收益, 负 = 亏):
- LOSS_D ⇔ D_K 窗内均值 < 0; LOSS_R ⇔ R_K 窗内均值 < 0。SAME ⇔ R_K 均值在 D_K 均值 CI95 内(k 81); GAP ⇔ 配对差 CI95 不含 0(k 87)。
| LOSS_D ∧ LOSS_R | SAME | GAP | 标签 |
|---|---|---|---|
| 是 | 是 | 否 | STRATEGY'S OWN LOSS(king 链, 目标层) |
| 是 | 任意 | 是 | BOTH LOST, DEPLOYMENT GAP |
| 是 | 否 | 否 | BOTH LOST, UNDECIDABLE |
| 否 | 任意 | 任意 | NOT A SHARED LOSS(另记哪本亏、GAP 与否) |
carry 与成本(付出, 不用「亏损」措辞): SAME ∧ ¬GAP ⇒ SAME LEVEL; GAP ⇒ DEPLOYMENT GAP; 其余 UNDECIDABLE。
- **G-PRED(阻断, 先于真实数据运行)**: 合成序列(61 锚、11 日块): (a) 两本相同且每锚 +10..+20 ⇒ 必须 NOT A SHARED LOSS; (b) 两本相同且每锚 −10..−20 ⇒ STRATEGY'S OWN LOSS; (c) 部署每锚 −10..−20、回放 +10..+20 ⇒ NOT A SHARED LOSS 且 GAP; (d) 两本都 −10..−20 且部署恒比回放低 5 ⇒ BOTH LOST, DEPLOYMENT GAP。
### §6.2 能排除什么、不能排除什么
- **经济等价带** δ = 0.25 bps/锚(A0 全周期净额 +0.6342 的约 40%; 更大的差对这本书有经济意义)。
- 配对差 CI95 ⊂ [−δ, +δ] ⇒「部署/模型差异在经济上可忽略: 已排除」; CI 含 0 但越出 ±δ ⇒「未检出, 也未排除」, 并写出被排除的区间外侧值; GAP ⇒「检出」。
- **模型差异**单列: REM(分数差与未对上部分)的 Shapley 均值 CI 用同一规则读。
- **策略自身亏损**成立 ⇔ 价格与净额在两个种子上都是 STRATEGY'S OWN LOSS 或 BOTH LOST 类标签; 它**不排除**额外的部署或模型差异, 除非后者按上条「已排除」。
- V2MAIN 与执行器层没有测量 ⇒ 一律「不能排除」。
### §6.3 其余
- 两个差的读法(描述): 报告 Δ_fixed、Δ_regen 及 CI(k 89, 日块自举); 标签是否因修正而变, 逐项列出。
- 价格差最大分量、|REM 占比| 读法与 T5c 相同, 并注明占比在总差 CI 含 0 时不稳定。

## §7 门汇总
| 门 | 阻断 | 规则 |
|---|---|---|
| G-FREEZE / G-ENV / G-POD | 是 | sha 与 env 白名单断言; pod2 只用 CPU, `nice`, ≤ 16 核, 内存 ≤ 61 GB; GPU 前后 0 % / 2 MiB; PID 333197/339489 记录且不触碰 |
| G-R6 | 是 | §2 |
| G-IV-LEDGER / G-IV-EXEC | 否 | §2 |
| G-SCOPE | 是 | §2 |
| G-UM / G-KA | 是 | 延展掩码与 KA 数组 sha 等于 T5c 收据 |
| G-X′ | 是 | §3 |
| G-RAW / G-SIM-R / G-ARCH-D / G-CLOSE | 是 | 同 T5c |
| G-T1c | 是 | x0910 口径复现 T1 D2 与 T5 §6.2 |
| G-FIXW / G-T5C / G-PRED | 是 | §4、§6.1 |

## §8 统计
窗内锚等权; UTC 日块自举 2000 次, `np.random.default_rng([20260905, k])`, 百分位 CI95; k 同 T5c(81 标题, 82 价格 Shapley, 83 carry, 84 净额, 85 成本, 86 固定顺序, 87 配对差, 88 多空), 新增 89(两个差)。

## §9 装置、写入与提交
1. Mac `devices/t5d_interval_sources.py`: 生产者账本两个快照与执行器 funding 记录 → 逐结算间隔清单(大文件放 `/Users/haosiyu/cc_tmp/t5d_2026-09-13/`, 收据记 sha)。
2. pod2 `devices/t5d_ivfix_panel.py`: 修正面板与 G-R6、G-IV-LEDGER、G-IV-EXEC、G-SCOPE。
3. pod2 `devices/t5d_drive.py`: G-UM、G-KA、四个臂、G-X′。
4. pod2 `devices/t5d_bridge.py`: G-PRED、G-RAW、G-SIM-R、G-ARCH-D、G-T1c、G-FIXW、G-T5C、G-CLOSE; 两个差、桥、读法、敏感性、透镜。
5. Mac `devices/t5d_tables.py` → `receipts/TABLES_T5d.md`; RESULT 只引用该表。
- 校验和用 `../T6/devices/t6_sha_guard.py`。写入: `T5d/`、cc_tmp、pod2 `/workspace/uplift_r2_2026-09-13/T5d/`; 不改 T5c RESULT(完成后只加一行指向 T5d 的指针); 本预注册以显式路径提交, 其余不提交。
