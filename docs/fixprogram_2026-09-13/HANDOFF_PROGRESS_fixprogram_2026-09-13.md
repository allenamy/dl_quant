> **创建:** 2026-09-13 15:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 活文档(随交付滚动更新; 每次更新单独提交); 修复纲领进行中, **未部署任何修复** | **作废条件:** 由最终合并复审包取代(FIXPROGRAM §5)

# 修复纲领进度与交接(给独立研究员接续 / 复审用)

**用途**: 用户字(2026-09-13 15:0xZ / 15:2xZ):「整体修复完之后, 发我完整文档和提交链, 我交独立研究员复审」;「用量达到 98% 的时候汇总进度, 提交链代码, 我让独立研究员届时继续工作」。lead 看不到账号用量百分比, 故本文件**持续保持可交接状态**: 任何时刻停下, 独立研究员从本文件 + 下列提交即可接续。
**唯一现状源仍是 `STATE.md`**; 规程、登记、裁定全文在 `FIXPROGRAM_2026-09-13.md` §0–§5。

## 0 实盘现状(只读核, 2026-09-13 15:23Z)
- 执行器运行树 `~/dl_quant_live` = **ef60f85**(= origin/main; 09-13 12:04Z 部署 W6ab+W2+W1+W9); 12Z 锚 rc=0(12:58:30Z), 看门狗 tripped=False; 三守护 combolive 30944 / sidecar 30943 / shadowloop 10900。
- **本纲领产生的代码修复一律未部署**(执行器改动在各克隆分支; 生产者改动在快照分支)。部署规程: 独立复审通过 → 执行器非锚窗 `ops/safe_commit.sh` + 电池全绿 / 生产者换装事件 + 首锚验收。
- lead 已直接应用、待复审的两项运维动作(均为已裁定撤回任务的持久关闭, 不触在役三守护): OPS-01 σ_fund 阶梯 launchd disable + plist 退役(6cc95943); OPS-02 已 KILL 执行探针 bootout + disable + plist 退役(b63a0144)。
- STATE §1 回滚动词已更正(b63a0144): `kill $(cat combo_live_daemon.pid)` 在 launchd KeepAlive 下**不是回滚**(哑任务正控: kill 1 s 内重生; bootout 卸载无重生; bootstrap 恢复)。深查模板 ⑥ 仍是旧动词(K5 待改)。

## 1 用户裁定索引(本纲领内)
1. 20:5x SGT: 所有已知问题不等裁定、最严谨修复、每项提交链 + 报告 + 独立复审, 第一优先。
2. 14:13:19Z: main(全部修复, 含 P2 生产路径回放认证)完成后才开始 secondary; secondary 以 L2 为首。
3. 15:0xZ: 复审 = main 完成后一次性合并包(覆盖实盘 / 全部管线 / 数据采集 / 评估 / 模型训练 / 未来研究 / 口径)。
4. 15:2xZ: 用量将尽时汇总进度与提交链, 交独立研究员接续。

## 2 逐项状态(按层; 提交均在研究仓 `research/book-uplift-2026-09-11`, 除非注明克隆分支)
图例: ✅ 已交付(待复审) · 🔧 进行中 · ⏸ 暂停(已提交到停点) · ⬜ 未开始

### 2.1 实盘执行器(克隆, 未部署)
| 项 | 状态 | 负责 | 提交 / 收据 | 说明 |
|---|---|---|---|---|
| E1 09-12 平仓批 fills 回填 | ✅(已应用于实盘账本, 只追加) | lead | 9f2e7968 · 33dee185 · 66de5b73 · b92e48c3; `REPORT_E1.md` | 副本演练 + 应用后新副本看门狗均未触发; 二次写入 0; 公证前缀一致 |
| EXE-01 W6(c) 比例响应(整书平仓须过比例门) | 🔧 | FX-W6C | 克隆 `cc_tmp/fx_w6c` 分支 `fix/exe01-proportional-response`: f0d4eac(逐字移植, 默认关)· f99dc80(门开 + 补 W6(c) 缺口); 电池 scan_f99dc80 运行中 | R-14 读作 A(默认 ON, 2%/5 名冻结); 后续 ALM-02 cond2.judged_on 写死、flow-day 缺陷(M2-33 对 STA-01 先对账) |
| E2 = EXE-05 broker 直接 GET 容量冲突合同 | ✅ | FX-EXEC | 克隆 `cc_tmp/fx_exec` 分支 `fix/known-issues-2026-09-13`: 6294534; 收据 3600d99e; diff sha de7a4dd7 | 旧码红 10/120(缺陷格), 新 120/120 |
| E3 = EXE-06 损坏事件日志具名 NOT OBSERVABLE | ✅ | FX-EXEC | c28c0a7 + 82fcc16; diff 29c1e7e1 | 12 突变旧码 8 崩溃 + 4 静默全绿 → 新 12/12 具名红 |
| E4 = EXE-02 已停名不进追单路径 | ✅ | FX-EXEC | 3a641c3; diff 529b588c | 裁定 R2′ + §4.2 前提更正: from_reject 转换是 MARKET reduce-only(保留, 裁定 (a)); 真 09-12 12Z LSKUSDT 追单被拦 |
| E9 = ALM-04 产物断言 NO_PRODUCER 误报 | 🔧(克隆已提交 a21797d, 收据未入研究仓) | FX-EXEC | a21797d | |
| E10 = LED-06 公证器 · ALM-03 · OPS-01b · E5 · E6(含止损文案 / EXE-03 告警归因)· E7 · 全电池 | ⬜ 队列 | FX-EXEC | — | **REPORT_FX_EXEC.md 未落盘**: FX-EXEC 工具策略阻止其写报告 .md, lead 未代写(待用户裁定); E2–E4 报告全文在 lead 会话记录中 |
| LED-02 平仓批按腿 mid 计 EXIT 成本 · LED-07 anchor_series · LED-08 逐锚报告读 cost_buckets · STA-02 冷却到期不推手机 | ⏸(克隆已提交) | FX-EXEC2 | 克隆 `cc_tmp/fx_exec2`(**分支名 main, 仅本地克隆**): c46fb83 · 7ca52ac · 469c3f3 · 8354c5a; 工作树另有未提交 `live/alarm_policy.py`、`ops/check_funding_span.py`(推断 ALM-01 进行中) | LED-01 裁定 B((symbol, trade_id) 键 + 写入守卫隔离不抛 + 唯一读者 + 44 日零违例正控 + 冻结指标逐位不变); 其余 LED-03/04/05 · ALM-01/05/06 · STA-03 · OPS-03 · CFG-02/07 · DOC-01 未做 |

### 2.2 生产者 / 模型服务(快照分支, 未部署)
| 项 | 状态 | 提交(克隆 `cc_tmp/fx_prod` 分支 `fix/train-serve-parity-2026-09-13`, 基 b891748 = 在役快照) | 说明 |
|---|---|---|---|
| P1 king 第 80 列按训练定义 v0 服务 | ✅ | e4a1e84(红)· 633d44b(修, 9/9 绿, 旧电池 65 全过) | fund 腿保持 v1 |
| P9 资金费间隔真值表 + 规则评估 | ✅ 证据 / 🔧 修复 | e0e34ea; 表 `work/p9/P9_declared_interval_table_2026-07-01_2026-09-13T12Z.csv.gz` sha b797c85f | 无一条仅用挂账时刻信息的规则逐行精确; 6 个在役切换行: ONG 真错、ZKC/SOPH 很可能错、COTI/T/SKR 未决; 八月 zip 拉取已批 |
| P6′ bundle 引导: 种子间隔按精确申报规则重推 + EMA 状态对齐 | ✅(待电池) | 4b996aa · 031707c(红)· d7df9a5(修) | |
| P2 V2MAIN 第 80 列 v0 + 12h 新鲜度 · P6-M 实盘 EMA 残差迁移 | 🔧 | 41f3deb(红)· 15921c0(P2 修)· c2cdfa7(平价回放驱动 + 判官 (a)(b)(c)); 回放 on/off 两臂运行中 | |
| P5 席位播种 · P7 FTRIM 残余 · P8⊕EXE-03 撤名等额平移翻号 | ⬜ | — | P7/P8 = 书行为, 须 P2 认证后生产路径回放配对 |
| P3 qv4h · P4 其余特征逐列平价 · P10 f16 训练 / f32 服务 | 🔧 审计 | AUDIT_PROD 装置: ebf1ceaa · a9c22ac4 · d9be5cb4 · 84e7aa56 · 6ce1b9d5 · fbab3d22 · 5243ae80 · c52af4ce · 962267a0 · 3e71e0de · d76ed216 · a0222c39 · 1127261e · b59fb791 · 1b02c837 · e9debe97 | `AUDIT_PROD.md` 未交付 |

### 2.3 生产路径回放认证(P2, 归入 main)
| 项 | 状态 | 提交 | 说明 |
|---|---|---|---|
| S1 七门(G2-B 原门 RED 保留; G2-B″/C/C′/S/D/E PASS) | ✅ 前轮 | 见 `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md` 收据 1–8 | |
| G2-C-BIND(槽位↔锚 / 人口绑定 / 6 突变全红) | ✅ 自报 PASS(第 3 跑; 前两跑为装置缺陷, 已修留档) | 5146689c(AMENDMENT 7)· 3bef2183 · c3a2c5f7 · 7a5e4f58 | **收据 `G2C_BIND.json` 尚未入研究仓, lead 未核** |
| 连续 combo 历史链残差(0/41 @1e-6, 最大 1.12547e-4, 只在 DL 腿) | ⬜ 机理未闭合 | — | 假说 H-a 数据版本 / H-b 生产者起点状态 / H-c F10 横截面输入(含死合约); 先冻结归因预注册 |
| S2 六链 | 🔧 链已跑 | 5ea2dff8(出表装置, 强制「未认证」标签)· f89f2fee(D20 探针) | 出表前须以 AMENDMENT 采纳 K2 等价带(A6.7 点估计 0.23 规则是 K2 红集之一) |

### 2.4 评估口径(K2, 研究仓)
| 项 | 状态 | 提交 | lead 复跑 |
|---|---|---|---|
| 等价带判词模块 + 冻结 δ(书层 0.05 bps/锚/gross; ΔIC 0.003 仅分数层) + 重标 347 行提案 | ✅ | adeda8e7 · efc2412a · f0cfe770 · d0b087db · 99a6cd27; `REPORT_FX_EVAL.md` | legacy rc=1 红集 == 声明 19 格 · module 84/84 · AST 保留 PASS · 变异 17/17 · 重标 gates_pass=True 347 行(与提交版仅构建时刻不同) |
| §0 第 8 条「无差类判词只由等价带发出」 | ✅ 采纳(FIXPROGRAM §4.1) | b63a0144 | 重标提案待复审后由 K4 应用 |

### 2.5 数据层(研究)
| 项 | 状态 | 提交 | 说明 |
|---|---|---|---|
| AUDIT_DATA 29 项(P1: TRD-01 死合约冻结行 / FEA-01 DL 资金费前视名单 / TIM-01 king 时钟错位) | ✅ 审计 | feb7747e · deb8a47b · 36633520 · 60461e1a · 47d5826a..8f23f2f4 · bb8a2806 | |
| TRD-01 按成交定义可交易: SPEC 冻结 + 共享模块 | ⏸ | 73b59ec0(SPEC)· 8ab0d769(`common/tradability.py` + 构建装置, 运行前) | 其余 TRD-02/04 · FND-01/02/03 · HOL-01 · LIN-01 · RET-02 · UNI-03 · EVL-01 未做 |

### 2.6 模型训练输入 / 十月重训链
| 项 | 状态 | 提交 | 说明 |
|---|---|---|---|
| AUDIT_TRAIN 29 项(P1: TRN-01 月滚输入在驱动外 / TRN-02 RAW 补丁覆盖无门 / TRN-03 F10 numpy 导出无门) | ✅ 审计 | 7e1ecf9a | 十月重训期限 ≈10-01 |
| TRN-19 解析器无 '=' 行导出为 R=R | ✅ | 1e6d6122(事实表)· d591d65e(修); `REPORT_FX_TRAIN.md` | |
| TRN-02 等其余 | ⏸ | — | |
| FEA-01 · TIM-01 · UNI-01 · TRD-05(模型输入) | ⏸ 事实表装置 | 74cb2e66 · a1c16b73 | 修复含预注册配对重训 |

### 2.7 执行成本与实验
| 项 | 状态 | 提交 | 说明 |
|---|---|---|---|
| X-COST maker 占比 93.1% → 73.9% 精确分解 | ✅ | 3eea1906 · 55aa2d3b · bcb3c0d5 · fdee4894; `X_COST/RESULT_X_COST.md` | requote direct 臂 ≈+11.4 pp(推断)· chase 臂 +4.4 · chase_forced +2.4(存款后尺度)· 其余 from_reject +1.0; 首次 −5022 率 14.3% → 23.0% 原因未测 |
| CFG-04 chase 实验人口修订草案 · CFG-06 placement eps 0.50 复读预注册草案 | ✅ 草案(未冻结) | 977962a4 · 977eb46e | 设计问题待裁定(见 §3) |

### 2.8 知识库 / 模板
| 项 | 状态 | 提交 |
|---|---|---|
| AUDIT_KB 248 行(PARTIAL; M4 另 31 行在草稿区未并入) | ⏸ | 721d1d44 · 0e88892f |
| lead 已应用: STATE §1 回滚动词; 记忆 review_b0a573a1(运行树与 revert 回滚作废)、k_window_180_live(在役 900 s)、chase_closed_at_39(09-01 起 50/50) | ✅ | b63a0144(STATE); 记忆文件不在仓内 |
| 深查模板 ⑥ 回滚动词 · 基线(改写率 27% / maker 占比 74–78% / guard_twin 结论在 latest.json)· 两个会话 cron 替换提示词(约 09-16 00:24Z 过期) | ⬜ | K5 |

### 2.9 运维 / 基建
- OPS-01(6cc95943)· OPS-02 + 回滚动词双演练(b63a0144; 第 1 次演练结论错误留档)· 盘满清理 23 个陈旧克隆(`receipts/INFRA_disk_cleanup_20260913T143228Z.log`)。

## 3 待用户裁定(阻塞或影响方案)
1. **FX-EXEC 报告文件写入被其工具策略阻止**: 是否允许 lead 以其消息原文代为提交 `REPORT_FX_EXEC.md`, 或调整该代理权限。
2. **CFG-04**: 重建锚上是否继续随机追单(no_chase 臂在从空到满重建锚留约 3% gross 未成交, 12Z 6,979 USDT; 分析又排除这些锚)—— (a) 重建锚全追 / (b) 维持随机 / (c) 只在复场锚全追。
3. **CFG-06**: D1 无定论时默认值(提案回退 0.35 / 或维持 0.50)· D2 窗 28 天或 14 天 · D3「停 behind」= eps 0 或 0.10。
4. 是否把 EXE-01 比例响应 + E4 止损出场 + OPS-01/02 作为小包提前复审部署(约 12 h 可备), 或按原计划随全部修复一次复审。

## 4 lead 自身错误与更正(本段)
- R2′ 裁定原文「from_reject 以原限价 IOC 转换」与代码不符(实为无价 MARKET reduce-only); 原句保留并标假, 裁定改据 08-20 批准的通道事实(FIXPROGRAM §4.2)。
- 回滚动词第 1 次哑任务演练 3 s 读「未重生」结论错误(launchd 对运行 <10 s 任务节流), 收据改名 `…attempt1_insufficient_wait_WRONG_CONCLUSION.log` 保留; 第 2 次演练结论入 STATE。
- 一次提交因与其他工作者并发撞 ref 锁失败(rc 128), 重试成功; 期间一次对 .git 驱逐文件的物化读取耗时过长被我中止(无副作用)。

## 5 secondary(挂起至 main 完成)
- L2 挤空方向: Stage A 全过, Stage B 未跑; 重启核对清单 11 项(fb180666; 含 P_neg 十分位须 AMENDMENT、CHECKSUM 抽样须补全、判官须采纳 K2 模块)。
- T7 韩元溢价: 永续 1h K 线拉取完成且收据核过; S1 装置已提交未运行(1aec37c0)。
- T5d-R(消费 P9 真值表)· L3 事件可行性 · L4 家族 3 · T6 §11 录取规程 · T1 LIVE_D2 九月 carry 更正。

## 6 复核指南(入口)
- K2: `REPORT_FX_EVAL.md` §10 逐字复跑命令(lead 已复跑一致)。
- 执行器各项: 克隆分支逐提交 + `docs/receipts/fx_exec_*.diff` sha; 旧码红 / 新码绿日志在 `docs/fixprogram_2026-09-13/FX_EXEC/receipts/`。
- 生产者: 克隆 `cc_tmp/fx_prod` 分支逐提交; 平价回放判官 c2cdfa7。
- P2: 预注册 AMENDMENT 1–7 + 收据 1–8; G2-C-BIND 收据待入库。
- 审计: `docs/audit_pipeline_2026-09-13/AUDIT_{EXEC,TRAIN,DATA}.md` + `AUDIT_KB_PARTIAL.md`(AUDIT_PROD 待交)。

## 7 剩余工作估时(工作者小时, 不含复审等待; 以约 5 个并发计)
执行器余项 6–10 h · 比例响应 2–3 h · 生产者 P2/P6-M/P9 8–12 h · P2 链残差 2–8 h · 账本告警余项 6–8 h · 知识库收尾 3 h · 数据层 1–2 天 · 十月链 2–3 天 · 模型输入(含 GPU 重训)2–3 天 · 书行为 P7/P8 1–2 天(P2 认证后)。**main 全部约 4–6 天。**
