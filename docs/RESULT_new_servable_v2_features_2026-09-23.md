> **创建:** 2026-09-24 00:2xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(news2) | **状态:** **未完成 —— 判词与任何书层数字尚未产出**; 本文此刻只是 §3-1 重跑与偏离清单的受据记录 | **作废条件:** `docs/FREEZE_new_servable_v2_2026-09-23.md`(b30e4afa5)或其修订 1 改变, 或本文 §3 写入判词后被新一轮重跑取代

# NEW_S2(完整修正版)结果: §3-1 重跑、偏离清单、下一轮清单

## 0. 此刻有什么、没有什么

**有**: King(run4)与腿已训完并绑定; F10 两个种子在训(00:05Z 起, 23 折); FREEZE §3-1 的全部重跑已出数(§2); 偏离清单完整(§5)。

**没有**: 组合、适配器、引擎(4 跑 × 32 路径)、R-P 读数、判词。**本文 §3 / §4 里凡写 `NOT PRESENT` 的格, 就是还没产出, 不是产出了零或产出了不显著。**

分数层诊断确实已存在(King 逐折 mean_cs_spearman), 它按装置自报标 `SIGNAL_DIAGNOSTIC_ONLY`, **不是书层数字**, 也不构成对任何判据的回答。

## 1. 对象与判据出处

| | |
|---|---|
| 冻结件 | `docs/FREEZE_new_servable_v2_2026-09-23.md`(b30e4afa5)+ 修订 1(`FREEZE_new_servable_v2_amendment1_2026-09-23.md`) |
| 判据 | 冻结件 §2, **由 lead 书写**(判据不得由被判对象的作者书写; news2 是 B 部分补丁的作者) |
| 设计 | `docs/DESIGN_producer_new_contract_2026-09-23.md`(§B 特征层为 news2 所写) |
| 预注册 | `docs/PREREG_new_servable_v2_features_2026-09-23.md` + `AMENDMENT_1_…` |
| 训练方案 | NEW_S 方案(FRESH 判 KEEP_NEWS, c1fb0bf0), 逐步照 `news_chain_resume.sh` 的解释器与环境 |
| 上线树 | `treeNC5`, `shadow_loop_v3.py` = `a68c7a5f0c6e8e0a` |
| 特征包 | `NC_FEATURES.npz` = `3c886a2bc0ff65c1…`(建自 `treeNC`, `shadow_loop_v3.py` = `9403dedd`) |

## 2. FREEZE §3-1 重跑: 全部已出数

> §3-1 原文: 「B 部分今天的收据只认证『旧输入上补丁做了该做的事』。A 部分新输入接上后, 28 格单测、射程门、D7 准入门、B8 逐位对照、G1-3 全部重跑, 不过即停。」

| 项 | 判词 | 退出码 | 收据 |
|---|---|---|---|
| 单测(26 格, D11/D13 交出后) | `NEWS2_PATCH_TESTS VERDICT=PASS cells=26 not_pass=0` | 0 | `TEST_NEWS2_PATCHES_treeNC5.json` |
| 射程门 | `VERDICT=FAIL`(唯一非 PASS 格 = floorD14 `NO-MEASUREMENT`) | 1 | `NC_REACH_GATE.json` |
| └ D14 分辨力(补测) | `VERDICT=NO_TIE_POSSIBLE at all 5 anchors` | 0 | `D14_RESOLUTION.json` |
| └ D14 分辨力红控 | `VERDICT=PASS mode=selftest cells=4 not_pass=0` | 0 | `D14_RESOLUTION_selftest.json` |
| D7 准入(条件 1: 行独立性) | 见 `D7_ROW_INDEPENDENCE.json` | — | `D7_ROW_INDEPENDENCE.json` |
| D7 准入(条件 2: 分辨力) | `VERDICT=PASS`(10/10 锚) | 0 | `NC_D7_RESOLUTION.json` |
| B8 逐位(上线树内核) | `VERDICT=PASS: tree kernel == window_stats bitwise`, 70 对照 / 58,030 格 / 0 不同, 红控 True | 0 | `B8_TREE_BITWISE.json` |
| 训练树 vs 上线树平价 | `VERDICT=PASS` 408,691 格 0 不同 | 0 | `TREE_PARITY_DEPLOY.json` |
| └ 该平价的红控 | `VERDICT=FAIL` 408,691 格 **183,277 不同** | 1 | `TREE_PARITY_RED.json` |
| 臂基线 vs 训练树平价 | `VERDICT=PASS` 408,691 格 0 不同 | 0 | `TREE_PARITY_ARMS_BASELINE.json` |
| G1-3 成员项 | 集成代理已实测(lead 2026-09-23 裁定不由 news2 重做) | — | 集成者收据 |

### 2.1 射程门为什么记 FAIL 而结论是「已解释」

射程门唯一的非 PASS 格是 `floorD14` 的 `NO-MEASUREMENT`: 该臂在 5 个锚上什么都没动。按纪律「动了零」不得判 PASS —— 它与「臂根本没接上」在计数上同形。

加更多锚也 settle 不了: D14 是 `argsort(-qvm[m], kind="stable")`(上线树 L580), 只有排序键在 NTOP 切口上**并列**时才可能改选择, 采样更多锚去碰运气不是对「并列是否发生」的测量。

所以改测臂测不了的那件事(`D14_RESOLUTION`):

| 锚 | n_cand | 成员 | 执行切口 | 切口键持有者(成员/超集) | 可能并列 |
|---|---|---|---|---|---|
| 1685520000 | 184 | 183 | 否 | — | 否 |
| 1718150400 | 263 | 261 | 否 | — | 否 |
| 1742428800 | 369 | 365 | 否 | — | 否 |
| 1779235200 | 528 | 400 | 是 | 1 / 1 | 否 |
| 1789660800 | 520 | 400 | 是 | 1 / 1 | 否 |

3 个锚候选数 < NTOP 400, 生产者不执行 `if len(m) > P["NTOP"]` 那一刀; 2 个锚执行了, 而第 400 个键在整个 `legal ∧ crypto` **超集**里只有一个名持有。超集计数**可能虚报**并列、**绝不会漏报**, 对门而言是安全方向。

**⇒ 射程门的 FAIL 是「这 5 个锚上 D14 没有可测效应」, 原因已由测量给出, 不是沉默。** 判词行照录, 不改判。

### 2.2 两条平价的作用与限度

特征包建自 `treeNC`(9403dedd), 上线用 `treeNC5`(a68c7a5f), 射程门的臂建自 `treeNC2` 那代(`tree_all` = a25a2981) —— 三棵树的 `shadow_loop_v3.py` 互不相同, 三个被打补丁的特征文件与 `feature_cache_identity.py` 逐字节相同。

若树差异够到服务列, 那就是「模型训练用的特征合同不是上线的那个」, 而**本轮任何后续门都抓不到**: 它们每次只在一棵树上跑, 在哪棵树上都自洽。两条平价补上这个洞:

- `treeNC` vs `treeNC5`: 0 / 408,691
- `treeNC` vs `tree_all`(臂基线): 0 / 408,691
- 红控(`treeNC` vs `tree_D5`, 同装置): **183,277 / 408,691** ⇒ 仪器看得见差异

**限度(必须随结论一起引用)**:
1. 每条平价只测了 **5 个锚**(2023-05 / 2024-06 / 2025-03 / 2026-05 / 2026-09), 不是全轴证明。
2. 只证**服务列在回放下**不动(`king_X78` / `X82` / `X89` / `m` / `qvm` / `fe_v` / `fn_v` / `iv_v` / `btcv_anchor`)。三棵树变的都是**实盘取数路径**(并行 K 线、批量 `fundingRate`、同锚新名回填、429/418 停止), 回放不执行那段 —— 那段的等价性本装置既没测也测不了, 归集成者自己的平价门与 lead。
3. 射程门/D7 两项的结论因此是**有条件的**: 它们在臂那一代的树上测得, 经由上面的等价链适用于上线树, 而这条链的基础是 5 锚。

## 3. 判词

**`NOT PRESENT`** —— 组合 / 引擎 / 读数尚未跑完。判词将由 `news2_stats.py`(统计量全部从钉住的 `news_stats.py` `7141ba42…` **import**, 不复制)按冻结件 §2 的 A ∧ B1 ∧ B2 产出, 判词原文与退出码逐字录入此节。

## 4. 必报项(冻结件 §2「必报(不作门)」)

| 项 | 状态 |
|---|---|
| 对 NEW_S 的 N1–N5 全表(分段、回撤、成本格) | `NOT PRESENT` |
| 对研究员 NEW 的差距 | `NOT PRESENT` |
| 30 日块区间(原样附「本规则是换装决策规则, 不是统计显著的声明」) | `NOT PRESENT` |
| 诊断 1: 三版本分数层 IC 同锚比较 | `NOT PRESENT` |
| 诊断 2: 逐修复项作用列数 | 部分已有(射程门的 `cells_out_of_reach` / `other_pass1_cells_changed` 逐臂计数) |

## 5. 偏离清单(全部, 含我自己的错)

| # | 偏离 | 处置 |
|---|---|---|
| 1 | **E-0923-F 静默窗破入**: 16:21–16:23:43Z 在生产 Mac 上跑全局门, 不在 [N+1:00, N+3:40] 内, 因为把钟看错一小时。按自己记录的 PGID 32535 杀掉; 核实 16Z 生产者(16:17:31Z)与 combo(16:18:34Z)已完成、执行器 16:24:00Z 才读。 | lead 记入台账。此后本机重活一律经 `devices/run_local_gated.sh` —— 第一件事调 `venue_quiet_window.py`, 不开就 `exit 9` 什么都不启动。本轮 treeNC5 单测的门收据 `GATE_treeNC5_suite.json` 记 `open=True remaining_min=7.0`。 |
| 2 | **「三种环境三个不同的 King OOF」是错的, 已撤回**: 我比的是 `.npz` **文件 sha**。比数组: 预测 `P` 8,566,057 格 **0 格不同**; 文件 sha 的差异全部来自同档另存的每锚 `model_sha256`(8143/10333 与 5953/10333 条不同)。抓到它的是重跑的 `legs.npz` 与第一遍**逐位相同**, 而 legs 的 KZ 由 `K["P"]` 的值算出。 | 改正三处: 收据顶部 CORRECTION 段 + 逐数组比较、`run_chain_corrected.sh` 头注释标 RETRACTED、给 lead 的更正消息。代价: 白扔一对已跑到 16/23 折的 F10(约 20 分钟)。重跑本身仍正确, 但理由是「方案这么写」不是「否则数字会变」。 |
| 3 | **第一遍 King/腿的训练环境不对**: 按装置名启链, 没读 `news_chain_resume.sh`(它钉 King 用 PV 且 `NPY_DISABLE_CPU_FEATURES` 已设、腿用 P314 + OMP=1、F10 用 PV 且该变量 unset)。 | 全部重跑到位。注: 本轮实测该环境**没有**改变 King 预测(见 #2), 所以这条是纪律偏离而非数字偏离。 |
| 4 | **`pre_king` 暂存收据没记 `argv`**: 复跑命令只能从源码反推。 | 装置已补 `argv`/`cwd`/`rerun_command`; 已出的那份 `STAGE_PRE_KING.json` 补不回去, 记在此。 |
| 5 | **暂存装置曾会删掉自己要暂存的输入**: `post_king` 源与目的可能同一 inode(腿按集成者给的调用方式写进 news2 根), 原码 `os.remove(dest)` 再 `os.link(source, dest)` = 删掉 `legs.npz` 再链一个不存在的路径。跑之前发现, **无损失**。 | 加 `samefile` → `in_place` 分支; 新增 `GREEN.in_place` 一格, 断言**文件仍在且 sha 不变**而非判词字符串; 变异实测该格报 `survived=False sha_now=FILE GONE`, 其余九格不动。 |
| 6 | **我给 `post_king` 写的「生产者还在跑就拒绝」守卫恒说通过**: 用 `pgrep -af`, 而 macOS 的 `pgrep` 没有 `-a` ⇒ 退非零、输出为空 ⇒ 空进程表被读成「已退出」。 | 改 `ps -Ao pid=,ppid=,args=` 自己匹配; **匹配脚本路径不匹配解释器名**(macOS 框架版 argv[0] 是 `.../MacOS/Python`, 原正则本机一个都匹配不到); 排除自身与祖先链(调起它的 shell 命令行必然含该模式); 测不到时报 `could_not_measure` 并拒绝。新增 `RED.producer_running` 真起一个匹配进程验证。套件 11 格 rc 0, 两台机器都绿。 |
| 7 | **B8 新装置先给出一个假 FAIL(79,248/116,060)**: 树的闭包只实现 `"sum"` 与「其它一律当 mean」, 问 `"count"` **不报错**而静默回均值, 于是我拿均值跟计数比; 且 D5 政策是 float64 累加后 round 回 float32, 参照必须先取 float32。 | 只比真实存在的两种 kind, 并**实测证明**该回退存在(问不存在的 kind 必须与 `"mean"` 逐位相同 ⇒ True); 参照取 float32。 |
| 8 | **该 B8 的红控自己也先失效过, 因此判 UNAVAILABLE 而非 PASS**: 我用 `np.array_equal(src, cd[:,:,1])` 认参照数组, 有 NaN 时恒 False, 扰动数组从未代入, 控制在拿自己跟自己比。 | 改成把参照数组作**显式参数**传入。现红控差 2 格 = 含被扰动行的 1 个窗 × 1 个名 × 2 种 kind, 自洽。 |
| 9 | **六个链装置一个都没入库**(`news2_train_king/train_f10/combo/make_configs/ext/adapter_specs`), 其中三个连 pod2 都没上传 —— 链走到引擎配置会缺装置; 且 King 已训完而产它的脚本不在库里。 | 补齐, 逐个按派生收据 `output_sha256` 核对 MATCH, 六份派生 diff 一并入库。 |
| 10 | **p2「卡住」误诊**(早前): 报出直接回收与 42 小时外推, 两条腿都错 —— `pgscan_direct` 是开机以来累计(当期增量 0, PSI 0.00), 且我取的是**父进程** `ps TIME`(不含 27 个子进程的 1186% CPU)。 | 数分钟内向集成者撤回, 对方确认未采取动作。正确做法: `/proc/<pid>/stat` 字段 14–17 含 `cutime/cstime`, 并按轴位置量进度。 |
| 11 | **我自己的 D7 信号预测器被我自己的门证伪**: 960 个锚被标记, 抽测 6/6 全是 `D7_moves_row=0`。 | 标 `FALSIFIED`, 通知集成者不要并入。漏检根因: `--selftest` 测的是计数器, 不是推导。 |
| 12 | **三处测试夹具假绿**(全是我的): 全 NaN 列被 `anchor_rank_block` 映成全零(有限格计数看不见, 改数非零格); 比较窗没真正落在被编辑的前缀之后; 修好上两处后基线不再红, 该格证不了任何事故删除。 | 已修/已删。 |
| 13 | **一份收据被 `rm` 先于 `cp` 丢失**(早前)。 | 自报, 记在此。 |
| 14 | `run_parity_pair.sh` 曾用 `setsid <script>` 直接执行, `/dev/shm` 是 `noexec` ⇒ `Permission denied`。 | 改经解释器 `bash <script>`。日志记下了它, 没有静默空转。 |
| 15 | 一次等待循环用 `until test -f <receipt>`, 而该收据是**前一次失败尝试**留下的 ⇒ 条件立刻满足, 我把陈旧的 ERROR 收据读成当次结果。 | 后续等待门改为同时要求「生产进程已退出」与「标记出现」; `run_p4_after_p3.sh` 的门是 `P3_CORRECTED_DONE`(它在 `set -e` 下排在两个种子退 0 之后), 不是「进程没了」。 |

## 6. 下一轮清单(本轮不动)

| 项 | 为什么留到下一轮 |
|---|---|
| **D2 / D3 / D10 / D12** | 冻结件确定的本轮范围之外 |
| **R1** | 同上 |
| D7 信号预测器的两个候选故障 | 已记 §B4 待办; 它被证伪, 本轮的 D7 准入不依赖它(依赖行独立性 + 分辨力两条) |
| 全轴平价 | 本轮两条平价各 5 锚。若要把「训练树 ≡ 上线树」当成无条件结论, 需要全轴或分层抽样 |
| 实盘取数路径的等价性 | 三棵树真正的差异所在, 回放测不到(§2.2 限度 2) |

## 7. 复跑

全部装置在 `multi_asset/exports/research/news2_2026-09-23/devices/`, 收据在同目录 `receipts/`。每份收据带 `self_sha256`、`utc`、`argv` 与 `rerun_command`(#4 所列那一份除外), 门类收据另带红控格与实测值。链的两个驱动: `run_p3_legs_f10.sh`(腿 → 暂存 → F10)与 `run_p4_chain.sh`(组合 → 适配器 → 配置 → 引擎 → 读数 → 判词 → ext), 两者逐步照 `news_chain_resume.sh` 派生, 只改根目录、装置名、臂名, 每步解释器与环境逐字保留。
