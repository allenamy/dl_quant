> **创建:** 2026-09-13 09:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 转交独立研究员的第四轮**合并**复审指令(用户转述用); **W9 一节待填, 填完并重跑四件叠加电池后才发出** | **作废条件:** 下文任一 sha 改变 ⇒ 须差异复核

# 致独立研究员: 第三轮复审(d1ce0ace)之后的全部修复与研究 —— 第四轮合并复审请求

## 1. 状态一句话
- **修复**: 你第三轮挡住的执行器与月链项**全部已在代码层修好**, 每处用你的反例或同形状反例做了「修前红 → 修后绿」; 另新增 **W9**(我方 T5b 审计新发现: 实盘逐名止损对多头不平仓)。四件叠加电池的读数见 §3.6。**全部未部署**: 实盘运行树仍 `918559f`, 书空仓 + 开仓停(09-12 12:47Z 起), 生产者 `~/wide_shadow` 未触。**用户要求修复优先: 本轮复审通过后才会请用户授权落地与手动恢复。**
- **研究**: 第三轮冻结点之后出了 T1–T5c 共八份结果(均未经 lead 复跑)与 P2 生产策略折外回放的 S0 与 S1 首两门; 其中一处是我在看到红门之后写的预注册修订(P2 AMENDMENT 3), **请你专门核它是否正当**(§6)。

## 2. 入口与范围
- 研究仓分支 `research/book-uplift-2026-09-11`, 复审范围 **`57e1a0fa..HEAD_AT_SEND`**(你第三轮冻结点之后; 发送时填 HEAD)。
- 状态账 `STATE.md` 顶部 09-13 各条; 纲领 `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md` 的 AMENDMENT 3–5 与全部结果指针。
- 执行器改动都在克隆里, 以 diff 形式入研究仓 `docs/receipts/`; 每份 diff 都能对 `918559f` 干净应用, lead 已从克隆重新生成并逐字节比对。

## 3. 执行器落地包(按风险排序)

### 3.1 W6(a)(b) —— 你的 R3-A1(容量冲突)与 R3-A2(整批缺失)
- 提交 `b90c87aa`; diff `docs/receipts/w6_reduce_only_clamp_ab.diff` sha **`259f50a6bad47518a4bc71e3f1b64b772e0b4978f972e90b8e35b718a6aa0003`**(= 克隆 `git diff 918559f 8113eed`, 26 文件); 设计 `docs/DESIGN_reduce_only_clamp_identity_2026-09-12.md` 新 §9。
- **R3-A1**: 同一请求的记录只要带 origQty 就必须一致; 不一致 ⇒ 保留发送量 Qs, 记具名 `capacity_conflict`(列出全部读数), **永不「证明终局」**, 执行器丢弃提交时盖的截量; 静态格钉死运行时没有改单动词。新 clamp 套件在 bf581eb 运行时 92/101(9 红恰为缺陷格, 含你的 6→8 假闭合: 旧链写「filled 6」, 对账再报 20 USDT 残差), 新代码 101/101; 真 12Z MEME/POPCAT 残差 0 不变; T9 cond5b CLEAN。
- **R3-A2**: 平仓完整性的人口先由看门狗事件侧定, 缺整批 = `LEDGER_BATCH_MISSING`(点名); 旧合取项逐字保留(AST 核未放宽), 66 → 68 项; 真账本 68/68(事件 10 批 = 账本 10 批); 删整批保留事件的突变: 新完整性格红并点名, bf581eb 文件仍绿。另一行自查修正: 批次键不再排序(缺 rebalance_id 的行不再崩, 落到点名的不可观测)。
- 你的探针(worker 复制去掉位置断言后跑, **lead 未复跑**): 冻结快照 87/87 exit 0; 新头 exit 1, 恰一格翻转(不同容量合并格, 现 origQty 10 + capacityConflict {8,6}); 「整批遗漏」格因探针自己从行重建批次表抛 NameError 不可评; 「多个 origQty 原因」格未翻(对账读者未改)。
- 未改、已登记: broker 直接重查截量同形但无人把它当容量读; 对账的多原因字符串读者未改; 冲突只记录不寻呼(DESIGN §9.6)。
- **W6(c) 比例响应**: diff `15d29d99…` 字节不变, **仍默认关、不落地**。

### 3.2 W2 —— NAV 为 0 / None / NaN(你第三轮点出的继承缺陷)
- 提交 `c7422d94`; diff `docs/receipts/w2_readers_three_bucket.diff` sha **`2ad1c27203b5726aecd0feb3add9ffb7b865168d5ebb674208e72d6ad3ce802c`**; 设计 `docs/DESIGN_readers_three_bucket_2026-09-12.md` §9c/§9d。
- 权益 0→100 且窗内入金 100 ⇒ 残差 0.0; None/NaN/inf NAV 拒算并点名行与原值; 同族位点 `ops/daily_summary.py` 4 处、`ops/first_anchor_review.py` 7 处(NaN 曾打印「★★ ABOVE 15%」)。
- **lead 独立复核**(两份新克隆, 前台, 真 state 副本; 收据 `docs/receipts/w2_readers_three_bucket/lead_verify_round4/`): 修后 `tests_daily_summary` rc=0 107 + 1 声明 SKIP / `tests_readers_three_bucket` rc=0 75; **修前读者 + 新测试 rc=1(29 / 12 FAIL, 全在第四轮小节)**。
- 你的探针(worker 报告, lead 未复跑): 修后「未改断言」在 L121(equity_nan 缺陷断言)exit 1 —— 钉的是缺陷, 修对了该翻红; 合同形式修后 exit 0、两个修前树 exit 1。
- 登记未改: 窗内无 nav 行时回退到账本最新行未声明出窗; target_w 为 None 时跳过。

### 3.3 W1 —— 告警事件
- diff `docs/receipts/w1_ic_monitor_contract.diff` sha `62a3032e…` **本轮未改**; 你第三轮已判可独立收口。W1 与 W2 共改 `ops/gate_coverage.py`, 落地顺序照旧(W6ab → W2 → W1 → W9)。

### 3.4 W9 —— 实盘逐名止损对多头不平仓(新, 我方发现)
- **来源**: T5b 审计(提交 `51b93969`, `uplift_r2_2026-09-13/T5b/RESULT_T5b.md` 新风险一节, 收据 `RECEIPT_T5b_exec_posthoc.json`): 止损把目标置零 → `signal/legs.py:124 reshape_after_withhold` 对**全体**(含被置零名)去均值, 给被止损名加 +a(净敞口为负时 +1.5..+62 USDT)→ `scheduler/anchor_loop.py:425 clamp_held_untradable` 把小于 a 的被止损多头钉成 add_blocked、较大的只减到 ≈a; 空头正常进 flatten_only。125 个「已止损且持有」实例: 多头钉住 94 / 多头仅减 23 / 空头 flatten_only 5 / 未上市 3; 拟合位移对记录桶 122/122。例: CYS/TRIA/MAGMA/RIVER 钉到 09-06 08Z 书级平仓, IOST 09-10 16Z..09-12 12Z。每名 6–50 USDT。条款自己的规格(`live/per_name_stop.py` 文件头, PREREG cf40ea21)是「并入 untradable 且 target 置 0 ⇒ 走既有 flatten_only」; `ops/gate_coverage.py` 早已把这个盲区写在 tests_per_name_stop 下。
- **修法与证据**: 〔待 W9 交付后填: 事实表位置 / diff sha / 修前红格 / 三个邻格 / 电池〕

### 3.5 已知不在包内
- 平仓费回填(只 09-12, 需凭据)、十月合同批准、落地与恢复 —— 均为用户字。

### 3.6 叠加电池
- **第四轮(未含 W9)**: 918559f + W6ab `259f50a6` → W2 `2ad1c272` → W1 `62a3032e`, 真 state 副本(08:55:56Z), 起止 diff sha 相同。**电池自判 `ACCEPTANCE: NOT GREEN`, rc=1: 130 个测试套件 129 过, 唯一红 `tests_env_loading`(14 项中 4 项「导入时填充 TELEGRAM_*」, 克隆按隔离不拷 .env), 5 个审计门(drift_gate / metrics_freeze / gate_coverage / income_callers / guard_reach)全过**; 新改五套件直跑全过(reduce_only_clamp / ic_monitor / readers 75 / daily_summary 107 + 1 SKIP / disposition_matrix 68)。收据 `docs/receipts/stacked_landing_battery_20260913T085514Z.log`、驱动 `stacked_landing_r4.sh` 与其日志(提交 `208b8cc9`)。**不能称全绿。**
- **第五轮(含 W9)**: 〔待填〕

## 4. 十月月链 —— 你的 D1 / D3 / D2 + dryrun 同类洞
- 提交 `e7bdd129`; 设计 `docs/DESIGN_v4_monthly_chain_2026-09-12.md` §10.5, 预注册 `docs/PREREG_v4_gates_monthly_2026-09-12.md` AMENDMENT 3 与 §7.11。
- **D1**: 每个边车定位字段必须是非空且指向本月路径的字符串; 预期输入文件无论定位写什么都做 sha; 只对真跑过的检查打印「已验证」。
- **D3**: 月合同由 Python 白名单文法解析, **永不 source**; 解析器 rc 与每个输出键值对都核; **`chain_v4_monthly_dryrun.sh` 同改**(之前仍 source: 前缀命令会建标记文件仍报 DRYRUN_PASS、未闭合引号报 EOF 仍通过、续行合同在两个父环境下导出不同 BUNDLE_OUT; 修后三者均 rc 2 `FAIL_month_env_malformed`)。两份已交付合同导出的环境与旧加载器逐项相同(mac + pod2)。
- **D2**: 成员索引先验整数 dtype, 再做一维 / 范围 / 唯一。九月 10,182 个成员数组实测均 int64, STEP2_m 仍 PASS 且 38 个判词字段同第三轮。
- 修前源码上新 [U] 节 22/32 格红; dryrun 修前 38 格 [U] 中 4 格红; 你的探针 26 个边界格翻为拒绝(D1 6 / D3 17 / D2 3), W7 与核心探针无行为翻转。
- **lead 前台复跑** `tests_pipeline_gates.py`: **ALL PASS 392 checks, rc=0, 起止 sha 相同**(tests a3af858d / chain_lib 4ee217e1 / driver e8e688d5 / dryrun 407aa438 / step2m d99a9109 / step1m 79950786; 收据 `receipts/round4_2026-09-13/tests_pipeline_gates_round4b_lead_verify.log`); round4 SHA256SUMS 60/60。
- **新 STEP2_m 批准对象** `d99a910951e070f70ae3eede1533013e009a62fa617eda55dff546290864329d`(合同批准仍待用户字)。新前提: 加载器需要 `$PY`(默认 `/workspace/venv/bin/python`)。
- 残留: 十月模板注释仍写旧 STEP2 sha `0fe5ec55`(模板字节被收据钉住, 未改; 批准 sha 以 PREREG 为准)。

## 5. 研究结果(均未经 lead 复跑; 请核读法)

### 5.1 「边在哪里没了」诊断链
| 线 | 提交 | 一句话 | 请你核 |
|---|---|---|---|
| T1 | `320396f1` + 附录 `ca9bdfcd`/`fc47ea69` | H2(结算间隔失真)证伪; 资金费拖累在三台仪器上显著; 实盘窗状态平常(同状态历史 g +3.58 [+1.61,+5.50]), 分位 INTERMEDIATE; 点估计线索 = fund 腿空头价格; **挖出 H2b**; 附录: 高 carry 与负价格**先后**发生 | 状态分类是否漏了让九月变坏的维度(见 T5c) |
| T2 | `1244dd14`(交付物在 `42a59c30`)+ 附录 `ce05f0c6` | 资金费腿按期望净额定仓三臂 UNDECIDED; κ* 随离散度变; σ 分档臂触发调查线且执行延迟下不可执行 | 你第三轮对 μ/a 与「天花板」的意见已按 AMENDMENT 4 处置, 请核 |
| T3 | `a2cb8e4d` + 附录 `e4d643d0` | 反转书被动执行成本在冻结判据下不可判(c_eff +1.13 [−15.87, +24.74]); 未成交比成交多走 +25 bps 属已知逆选择族 | 迁移偏乐观的读法 |
| T4 | `87f9f5c3` | **king 第 80 列训练 v0 / 服务 v1: NOT MATERIAL** —— 2024+ 书层 Δg +0.018 [−0.030, +0.063](s42)/ +0.016 [−0.033, +0.065], ΔIC −0.0001, 分辨率 ±0.05 bps/锚; 自 08-16 首锚即如此, 两代 booster 均 v0 训练(8d79186b `feature_infos` 78/78), 分叉在同一导出器; 研究回放 king 逐位复现为 v0; 影子验收 A2 比对共享 0.9×H 的平滑权重, 对这类错配几乎无检出力 | (a) booster 口径识别(29ffaf58 用近似成员集)是否充分; (b) 用 2024+ 研究回放替代实盘窗先后两个 booster 是否成立 |
| T4b | `c936ec01` | V2MAIN 同类: (a) v0 训练 / v1 服务**作用于**在役输入(mu/sd 171 列按 v0 重算全符); (b) 服务侧历史行回填 0 **构造上到不了**被打分锚(GATE ZH 逐位); 历史书层 **NOT MEASURED**(年折训练脚本从不存折模型与 mu/sd, 未以 FIX7 替代); 实盘窗快照起步 6 锚: v0 臂 combo L1 中位 0.0022; 09-05 席位播种 876 行 v0 重打分使掩码 king 席位 +0.0078、L1 0.0066 | 不替代 FIX7 的决定 |
| T5 | `39ec7c1e`(§7 来源一条在 `87f9f5c3`) | **八月部署书多付一倍 carry = 构造差**: FTRIM 窗内缺席 58% / 链状态从 king 形态书暖启动 27% / 回放目标层逐名止损 18.5% / 分数 −1%; 98.5% 在深负费率空头 | 构造组 Shapley 与 T×P 交互读法 |
| **T5c** | `c936ec01` | **九月同锚(61 锚, king 链, 目标层): 回放也亏, 亏在同一批空头 ⇒ 预注册读法「策略自身的亏损」** —— 价格 部署 −5.96 vs 回放 −4.76/−5.07, 差 −1.20 [−4.19, +1.59]; 差在多头侧; V2MAIN 臂 NOT MEASURED | 这是本轮最重要的研究结论, 请重点挑战 |
| T5b | `eaa08cd9`(规格先冻结)+ `51b93969` | Q1 FTRIM 残余确会冻结(每锚约 3 名, 0.33% gross), 冻结残余 carry −0.120 ⇒ NOT MATERIAL(PROVISIONAL); Q2 执行器止损在八月队列 0 次触发; Q3 执行器无带宽型冻结; **新风险 = W9**; 更正 T5 两处 | 见下条口径更正 |

### 5.1b T6 选择偏差审计(`c0ed46c8` 规则先冻结 / `516c5ad2` 结果; 未经 lead 复跑)
- F1 125 个全书配置 N_eff 1.57(几乎一本书); PBO 0.157 / 0.187 未触发, 但由事后预选线 XIB_LAG50 撑着; r8–T2 家族 F3 PBO 0.508 触发; 选择折价下界 −0.65(全周期)/ −1.56(冻结窗), CI 含 0; A0 冻结窗 2.94 的 P(真 SR > 3) = 0.30(N_eff)/ 0.0047(N = 300), 冻结窗高水平为全家族共有(regime 租金)。§11 提出录取规程。
- **请你核**: (a) 家族成员规则 R1–R9 是否把该排除的排除了、该纳入的纳入了; (b) N_eff 用参与比是否合适(替代: 聚类数); (c) 「低 PBO 由预选线撑着」的读法; (d) §11 录取规程是否应成为今后所有候选的门。

### 5.2 一处口径更正(T5b 发现, 纲领指针 `3fb02cfb`)
x0910 面板对 API 尾行套用单一拉取时的结算间隔: 九月间隔变化的名 SKR、SOPH 被记成 ¼, IOST 记成 8×; 执行器自己的 fundingInfo 行与生产者账本一致、与 x0910 不一致。⇒ **T1 D2 的九月 carry 与 T5c 的 carry / 净额数字标 PROVISIONAL; T5c 的价格读数不受影响。** 构建器行为的原因为推断, 未在 pod2 读码核实。

### 5.3 请挑战的合读
**「实盘对回测的落差, 模型分数差(H2b、V2MAIN 同形)都不是主因; 八月多付的 carry 是构造差且已由 09-02 FTRIM 等改掉; 九月初的亏损在研究规则下同样发生 ⇒ 是策略本身在普涨挤空行情下的问题。」** 若成立, 研究方向应转到策略对这类行情的响应能力, 而不是继续找部署差。

## 6. P2 生产策略折外历史回放(你第三轮说欠交付的基础仪器)
- 冻结预注册 `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md`: S0 计划 AMENDMENT 2 `4f92fe97`(先于任何门数字; PIT 宇宙为主臂; 偏差清单 D1–D16; 实测 1.03 s/锚)。
- **G2-B 原门 RED**(`de51cd82`): 41 锚 × 21,520 对, 最大 |Δacc| 2.603e-05 > 1e-9; 端口自检过(重建 = 生产公式, 窗内前推 4.77e-18); 违例全部继承自 09-05 16Z 之前(26 名末/首差比 = HL 3d 理论衰减到第 10 位); 两个来源: 7 名在役名 live 账本有「存储 iv ≠ 相邻时间差」行(PROMUSDT 79 行, 自 08-11), 66 名基名单扩展名从首抓窗冷启动。
- **lead AMENDMENT 3(`e1f341a7`, 写于看到红门之后, 先于其余门任何数字) —— 请你专门核是否正当**: G2-B 原门保留 NOT PASSED AS WRITTEN; 新具名子门 **G2-B″ 窗内递推平价**(41 锚全核, ≤1e-15, 只加严); 新偏差 **D17 = live 资金费 EMA 历史伪迹**(Phase 2 不复现); 必附 fund z 影响测量; 非阻断取证存储 iv 来源与在役链路能否再产生。理由: 原门把「公式对不对」与「live 状态有没有继承伪迹」绑在一个阈值上, 后者不是干净历史回放能也应该复现的。
- P2 AMENDMENT 4(`4362870a`): D18 执行器逐名止损按目标后叠加层建模(STOP 主臂 / NOSTOP 对照; lead 追加: 须注明 W9 前实盘对多头的钉住行为, 另设 STOP-PINNED 敏感性臂或列未建模)、D19 FTRIM + 带自动复现、资源约束(pod2 容器内存上限 61 GB, 禁多 GB 写)。
- **G2-B″ = PASS**(`2855e551`): 41 锚最大 8.67e-18; **D17 影响**: 逐锚 fund z Spearman 最小 0.99996, 前十分位 41 锚全不变, 后十分位仅 1 锚换 2 名, PROMUSDT 最大 |Δz| 0.050。其余门 G2-C / G2-C′ / G2-S / G2-D / G2-E 进行中, **全史书层数字尚未产生**。

## 7. 进行中(本轮不审, 列出以免误读)
T7 韩元溢价(可行性 `fbf36ffd`/`18f803de` 完成, 全量拉取进行中, 不出收益数字; 已下市韩元市场不可取、覆盖 53–65%)· P2 S1 其余门 · 抛物线前向日志只报计数(θ8 P 层已填 43, 距 200 门 157)。

## 8. 我方本轮错误(请一并核)
1. 交接里写「叠加电池已通过」(你第三轮已纠正; 更正 `7bca70c4`)。
2. `1244dd14` 宣称 T2 收口却没带任何交付物(git add 含不存在路径且压 stderr)⇒ `42a59c30` 补入; 此后提交后必 `git show --stat`。
3. STATE / 纲领时间标签写晚约 10 分钟, 两次更正(`f51cc0a0`、`195f1f06`)。
4. T5 的「生产没有逐名止损」措辞在提交时未先分层核对, 同一小时内更正(执行器止损在 target_live 之后)。
5. 为复核 X2 整份拷贝 667 MB 实盘 state 跨进 08Z 锚窗(只读; phase A 准点 08:24:03Z)⇒ 今后只拷子树并避开 HH:20–45。
6. 研究仓在 iCloud 桌面, 一次 ctime 批改让我的一个提交逐文件重哈希、持有 index.lock 11 分钟, 挡住所有工作者 ⇒ 仓内设 `core.trustctime=false`(可撤)。
7. 我的一个提交顺手扫进了 P2 已暂存的 25 个文件(错误的提交说明)⇒ 在无人基于它之前 `reset --soft` 撤回, 只提交自己的路径; 此后所有提交显式 pathspec。
8. X3 覆盖了 W7b 在 scratchpad 的第三轮探针输出副本 ⇒ 第三轮 `PROBE_W7_RESULTS.json` 记的 13 个输出收据中 12 个的 sha 无法再从 scratchpad 复验(已提交的 JSON 完好; 清单 `receipts/round4_2026-09-13/scratchpad_probes_pre_overwrite_inventory.json`)。
9. P2 在 pod2 写 5.7 GB 抽取撞 /workspace 配额约 2 分钟(已删; 同窗其他写入 lead 逐一核查无损)。
10. X1 曾因「等监视器」挂起约半小时(队友监视器不会唤醒)。T4b 的生产者窗停机守卫实际未生效(运行在窗外, 无暴露)。
11. 抛物线日跑读尾部时看到工具输出里两个非 P 层均值字段, 未使用未记录。

## 9. 约束(同前)
只读; 不调任何交易所 API; 不碰 pod2 GPU 与你的进程; 不在实盘树写任何文件; 复审产物写你自己的工作树。
