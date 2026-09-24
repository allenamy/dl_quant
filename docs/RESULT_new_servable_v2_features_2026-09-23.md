> **创建:** 2026-09-24 00:2xZ | **更新:** 02:2xZ 判词落盘 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(news2) | **状态:** **判词 = `NO_DEPLOY`(交用户)**; 必报项尚欠三项, 见 §4 与 §6 | **作废条件:** `docs/FREEZE_new_servable_v2_2026-09-23.md`(b30e4afa5)或其修订 1 改变, 或本文 §3 写入判词后被新一轮重跑取代

# NEW_S2(完整修正版)结果: §3-1 重跑、偏离清单、下一轮清单

## 0. 此刻有什么、没有什么

**有**: 全链已跑完 —— King(run4)→ 腿 → F10 两种子 23/23(`f10 rc 0 0` @01:00:20Z)→ 组合 → 适配器 →
配置 → 引擎四臂(全 `BT_LAUNCH VERDICT=PASS`, 逐 PID rc=0)→ R-P 读数四份 → **判词 `NO_DEPLOY`**
(`STATS_RC=0`, `EXT_RC=0`)。FREEZE §3-1 全部重跑已出数(§2); 偏离清单完整(§5)。

**没有(欠账, 已具名)**: 对研究员 NEW 的差距; 诊断 1(三版本分数层 IC 同锚比较); 诊断 2 的必报形式。
**本文凡写 `NOT PRESENT` 的格, 都是渲染器主动打印的具名空位, 意思是「还没产出」, 不是「产出了零」也不是
「产出了不显著」。**

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
| 射程门 | `VERDICT=FAIL`(唯一非 PASS 格 = floorD14 `NO-MEASUREMENT`); 放行依据 = lead 裁定 b8b9a521a, 判词行不改判 | 1 | `NC_REACH_GATE.json` + `RULING_freeze_3-1_D14_reach_2026-09-24.md` |
| └ D14 分辨力(补测) | `VERDICT=NO_TIE_POSSIBLE at all 5 anchors` | 0 | `D14_RESOLUTION.json` |
| └ D14 分辨力红控 | `VERDICT=PASS mode=selftest cells=4 not_pass=0` | 0 | `D14_RESOLUTION_selftest.json` |
| D7 准入(条件 1: 行独立性) | `VERDICT=ROW_INDEPENDENT`(`F8_TREND_ROWS=last` 在被取的那一行上等于 `=all`) | 0 | `D7_ROW_INDEPENDENCE.json` |
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

上面这些都是**测量**。「§3-1 因此算不算满足、链能不能继续」是一个**放行决定**, 不由本文作出 ——
news2 是 D14 补丁的作者, 放行依据不能落在被判对象作者的文字里(记忆 `criterion_author_must_have_no_stake`)。

**放行依据 = lead 裁定 `docs/RULING_freeze_3-1_D14_reach_2026-09-24.md`(b8b9a521a, 写于任何 NC 书层数字之前)**:
> **§3-1 对 D14 视为满足, 链继续。射程门判词行保持 FAIL, 不改判。**

裁定给的理由是: §3-1 要证的性质(「接上了、会改并列时的选择」)已由上线树单测
`D14.stable_tiebreak` 直接实测(基线 58 名不同, 补丁后 0 名, 构造输入会变红); 射程门在这 5 个锚上
测不了该性质, 因为触发条件不存在; 且该裁定**不放宽任何书层判据**(冻结件 §2 的 A / B1 / B2 一字不动)。

裁定另附两条限定(照写, 不作门): 实盘首次出现切口并列时 D14 才第一次在真实数据上生效, 其行为由单测
覆盖但真实数据上从未测过; 月度报告逐锚记「切口是否执行」与「第 NTOP 个键的持有者数」, 大于 1 时具名报告。

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

**限度 2 的另一半由集成代理的平价门覆盖**(收据 `nc_2026-09-23/receipts/parity_formal_2026-09-23/`,
已打开核对而非转述): 服务端 `run_anchor` + `combo_stage` 与训练构建在轴末前 6 个锚上逐位比。
基线跑在 **treeNC5(a68c7a5f)**, 判词 `NC_PARITY_GATE PASS`, `baseline_green True`, **6 锚 × 11 个量 0 格不同**。
它跑的正是回放不执行的那条实盘取数路径。

该门的**非空转证据**(这是让「0 格不同」有意义的部分, 与我的 `cells_compared` 门同形):
- 变异臂(treeNC5 撤掉 A4 那一行 = treeNC4)判 `FAIL_PARITY`, 且与首跑在同一格上**逐位相同** ⇒ 确定性;
- 两个负控都测出: `NC_F` rate 加 1 ulp ⇒ `fn_v` 1 格; `NC_R` ch0 加一个 f16 步长 ⇒ `X78` 5 格 / `rev24` 1 格 / `X82` 7 格;
- 覆盖: 6 锚在两棵树上都 returned、combo rc 0, w24h 列 649 名, **覆盖率 1.0, 没有锚被跳过**, 每个量 n > 0,
  `_no_measurement` 为空 —— 即「门确实测了它声称测的那些格」。

| 路径 | 谁测的 | 树 / 输入 | 结果 |
|---|---|---|---|
| 回放(服务列) | news2 `TREE_PARITY_DEPLOY` | `treeNC` 9403dedd vs `treeNC5` a68c7a5f; 输入 `NC_FEATURES` 3c886a2b + `members_hist_all` | 5 锚 × 9 量, 0 / 408,691; 红控 183,277 不同 |
| 实盘取数 | 集成代理 `parity_formal_2026-09-23` | `treeNC5` a68c7a5f(PATCH_RECEIPT 3135cf8b); 输入平价包 **290ebcc9**, 门装置 deefe360 | 6 锚 × 11 量, 0 格不同; 变异臂 FAIL_PARITY 且与首跑逐位相同; 两个负控都测出; 覆盖率 1.0 无锚被跳过 |

两块**不重叠**, 合起来才盖住「训练用的合同 = 上线跑的合同」。单独任何一块都留着另一块的洞, 而那个洞的
特点是**后续所有门都抓不到** —— 每个门只在一条路径、一棵树上跑, 在哪边都自洽。

**树身份已核**: 上面三件(平价、26 格单测、B8)都在发布树上跑, 收据里的 `shadow_loop_v3.py` 均为
`a68c7a5f0c6e8e0a`, 我那份 pod2 副本的 `PATCH_RECEIPT.json` = `3135cf8bbfad4b27`, 与发布树一致
(`46c52d94` 是 treeNC4, 未使用)。树 sha 是装置自报进收据的固定字段, 不靠事后补注。
集成代理另逐文件比过我那份副本与发布树: **12 个源文件全部逐位相同**(shadow_loop a68c7a5f、
combo_stage 363dd8c8、dlw 874c1870、f8 98bc036d、fci e4ec55d1、nc_contract 316a0b9b、
tradability a9fad82c、beta_overlay b77c180d、stable_trend 01bf8b3d、xfer_ref 33eb713b、
xfer_syms d187042e、PATCH_RECEIPT 3135cf8b)。

唯一差别在 `__pycache__` 的 .pyc 文件数(我这边 7 个, 它那边 2 个, 因为两边用不同解释器导入过)。
**由此得到一条做法**: 「树在运行期间没被改动」这类主张要核**源文件的 sha**, 不能核整个目录的文件集 ——
`.pyc` 的存在恰好说明那个目录被写过, 按目录比会把正常的导入副产物读成改动。

## 2.3 环境启动门(lead 2026-09-24 要求的类形状修法)

照着链脚本手动跑对一次不算修好 —— 钉必须在入口被强制。`devices/news2_env_gate.py` 把
`news_chain_resume.sh` 的逐步钉转录成表(每条带出处行), 每步开跑前比对, 不符就 `exit 9` 具名拒绝。

**钉的是 `sys.prefix`, 不是路径也不是 realpath。** `/workspace/venv/bin/python` 是符号链接, 实测:

| 解释器 | realpath | `sys.prefix` | numpy | numpy 载入目录 |
|---|---|---|---|---|
| `/workspace/venv/bin/python` | `/usr/bin/python3.11` | `/workspace/venv` | 2.4.6 | `/workspace/venv/lib/python3.11/site-packages` |
| `/usr/bin/python3` | `/usr/bin/python3.11` | `/usr` | 2.4.6 | `/usr/local/lib/python3.11/dist-packages` |

realpath 相同, **numpy 版本号也相同**。若按 realpath 或版本字符串做门, 恰好会放过 lead 点名要拒的那个
变异 —— 一个不可能失败的门。

自测 `ENV_GATE_SELFTEST.json`, **8 格 rc 0**: 先 5 格基线绿(king/legs/f10/combo/engine 各自在自己的钉
环境下 PASS —— 基线已红的变异检查恒真), 再 3 格变异全 rc 9 被拒(`/usr/bin/python3` 跑 king ⇒ 判词点名
`sys_prefix=/usr`; f10 要求 unset 而给它设上; legs 钉 OMP=1 而给 8)。「不约束」写成 None 并**打印成
unconstrained**, 不静默跳过。

判词收据的 `env_per_step` **不重新键入环境**, 而是嵌入各步启动门当时测到的收据。门存在之前跑的三步
(King / 腿 / 暂存)写成 `NOT_GATED` 并指向 §5 —— 「没有条目」不许读成「查过没事」。

## 2.4 引擎步前的 /dev/shm 实测门

4.1 GiB 那个数是在 NEW_S 输入上测的; NC 输入(`NC_FEATURES` 2.96 GB)的引擎内存**没有人测过**。
`run_p4_chain.sh` 在引擎步之前实测并写 `SHM_HEADROOM_BEFORE_ENGINE.json`, 低于 6.00 GiB 目标即
`exit 8` 停下报 lead, 不放宽、不删任何别人的文件。

00:23Z 实测 **5.70 GiB** < 6.00, 会在此停, 于是把三个选项交 lead(降目标 / 删 `p1_merged.npz` /
先串行跑一条臂)。**lead 裁定三个都不选**: 由集成代理把 `p1_merged.npz`(950 MB)从 `/dev/shm`
**搬**到容器盘而不是删 —— 搬前扫 `/proc/*/fd` 确认无进程打开, 两边 sha 均 `d2afedb2…`, 核过才删原件。
00:34Z 实测 **6.59 GiB**, 门槛不放宽, 引擎步照常并行不串行化。

裁定另加两条, 已落进脚本:
- 引擎运行期间每 10 s 采样 `/dev/shm` 已用量与 cgroup `anon`/`shmem`, 峰值写进判词收据的 ENV 段
  (`ENGINE_MEMORY_MEASURED.json`; `n_samples < 3` 判 `NO-MEASUREMENT`, 零样本的「峰值」不是测量)。
  这样「NC 输入要多少」变成实测值, 不必多等一两小时。
- 任一臂因空间不足失败即停下报 lead, **不重试、不删别人的东西**。

注: 我暂存的 `work/NEWS_FEATURES.npz` 是对 nc 根 `NC_FEATURES.npz` 的**硬链接**, 删它腾不出空间;
容器盘现仅余 0.96 GiB, 不往那里写大文件。

### 2.4.1 引擎实测结果, 与一条我先前读错的量(限定; 属**研究链在 pod2 的运行手册**, 不进生产部署手册)

> lead 2026-09-24 明确: 生产不跑引擎, 这条风险归研究链的 pod2 运行手册与下一轮链脚本的注意事项,
> **不写进生产部署手册**。

`ENGINE_MEMORY_MEASURED.json`, `VERDICT=MEASURED`, `n_samples=333`, 间隔 10 s:

| 量 | 实测 |
|---|---|
| 引擎前 `/dev/shm` 空闲 | 6.39 GiB |
| 运行期间最低 | **2.35 GiB** |
| 引擎退出后 | **2.31 GiB**(没有回升) |
| `runs/` 产出 | **4.057 GiB**, 798 文件 |
| cgroup `anon` 峰值 | 12.75 GiB(**cgroup 与其它代理共享, 不可单独归因本链**) |

**我先前把这条读错了, 并已向 lead 与集成代理更正**: 我说那 4 GiB 是「峰值占用」且「退出后会还回去」。
实测退出后空闲仍是 2.31 GiB —— 那 4.06 GiB 是 `runs/` 里的**产出文件**, 落在 tmpfs 上, 永久占用。
连带撤回「与流传的 4.1 GiB 基本一致」: 那个数指的是持久占用还是瞬时峰值并无依据, 不是同量纲比较。

**给下一轮链脚本的注意事项**:
1. 引擎前的 `≥6.00` 门只防「一开始就不够」, **管不到产出累积**。要防就按「预计持久产出 + 余量」定门,
   本轮实测的持久产出是 4.06 GiB。
2. 余量要**每步开始前实测**, 不用上一步报的数(集成代理的 8 臂装置已照此做: 低于 1.0 GiB 即拒绝启动)。
3. 谈「谁占了多少」必须说清是哪一种 `du`: 单独 du 我的根得 7.5 GiB, `du -sh /dev/shm/*` 一次性扫得
   4.8 GiB —— 差的 2.8 GiB 是与 nc 根共享的硬链接, 每次 du 调用只算一次。

## 3. 判词 = `NO_DEPLOY`

**判词行原文**(`logs/chain_stats.log`, `STATS_RC=0`, `EXT_RC=0`):

```
NEWS2_STATS SEED s42: A=PASS(S1 vs OLD +5.671, vs OLD_HOLD +3.144 bps/d; S2 3/3, 2/3;
  S3 maxDD -0.2310 vs -0.2902; S4 halted 0 vs 10; S5 PASS)
  B1=FAIL(-0.477 bps/d vs NEW_S) B2=PASS(halted 0 vs 0) failing=['B1']

NEWS2_STATS SEED s2027: A=FAIL(S1 vs OLD +6.207, vs OLD_HOLD +3.680 bps/d; S2 3/3, 1/3;
  S3 maxDD -0.2253 vs -0.2902; S4 halted 0 vs 10; S5 PASS)
  B1=PASS(+1.403 bps/d vs NEW_S) B2=PASS(halted 0 vs 0) failing=['A:S2']

NEWS2_STATS VERDICT=NO_DEPLOY failing={'s42': ['B1'], 's2027': ['A:S2']} unavailable=0
  old_reproduction={base 32/32, fee_x1.25 32/32, slip_x1.5 32/32, fill_x0.9 32/32, lit 32/32}
  receipt_sha256=6d689c9a152e81f93bf52410ac29db1102bf6e30e1c7eab9f7dfc9addc5055c8
```

两个种子**各自**须满足每道门, 而**失败点不是同一个**: s42 是「A 过、B1 不过」(§2 ⇒ TO_USER),
s2027 是「A 不过」(§2 ⇒ NO_DEPLOY); 取并 ⇒ **NO_DEPLOY, 交用户**。装置按冻结件 §2 自判, news2 未介入。

两个种子对 OLD / OLD_HOLD 都为正(+5.671 / +6.207 与 +3.144 / +3.680 bps/日), 回撤都好于 OLD_HOLD
(−23.1% / −22.5% vs −29.0%), R-P 触线 0/32 vs 10/32。**卡住的是两处不同的东西**, 不是全线为负。
原因与处置归 lead 与用户 —— 判据由 lead 书写, 本文不解释原因、不给建议。

## 3.1 必报全表(由 `news2_render.py` **只从收据渲染**, 不重算任何数)

### 判词(FREEZE §2;判据由 lead 书写)

- **VERDICT = NO_DEPLOY** — FREEZE §2: A and B1 and B2 -> DEPLOY; A but not B -> TO_USER (no automatic fallback to NEW_S); not A -> NO_DEPLOY. Both seeds must satisfy each gate.
- 逐种子未过项:`{"s42": ["B1"], "s2027": ["A:S2"]}`
- 区间说明(原样):30 日块自举区间照报,不作门。依据 E-0923-B:这台仪器对此类比较的区间半宽约 10 bps/日,以"下界 > 0"为门等于要求效应 ≥ 约 10 bps/日。本规则是换装决策规则,不是"统计显著"的声明。

#### NEWS2_s42

**A 门 — 能否替换在役(对 OLD 与 OLD_HOLD,写法同 db0123df7 §3)**

| 规则 | 对 OLD | 对 OLD_HOLD | 判 |
|---|---|---|---|
| S1 判据窗日差点估计 > 0 | +5.671 bps/日 | +3.144 bps/日 | **PASS** |
| S2 分段中 ≥2 段 > 0 | 2023H2 +5.068 / 2024 +2.476 / 2025 +9.179(3/3) | 2023H2 -1.290 / 2024 +0.724 / 2025 +7.807(2/3) | **PASS** |
| S3 最大回撤(路径均值)不差于 OLD_HOLD | — | NEW_S2 -23.1% vs OLD_HOLD -29.0% | **PASS** |
| S4 R-P 触线路径数 ≤ OLD_HOLD | — | NEW_S2 0/32 vs OLD_HOLD 10/32 | **PASS** |
| S5 三成本格 S1 同号 | fee_x1.25 +5.998; slip_x1.5 +6.196; fill_x0.9 +5.521 | fee_x1.25 +3.269; slip_x1.5 +3.312; fill_x0.9 +3.131 | **PASS** |
| (只报)30 日块 97.5% 区间 vs OLD | [-2.281, +17.257] | | 不作门 |
| (只报)30 日块 97.5% 区间 vs OLD_HOLD | [-3.906, +12.250] | | 不作门 |

**A 合判**:PASS(未过:`[]`)

**B 门 — 修复有没有把书弄差(对 NEW_S 同种子)**

| 规则 | 值 | 判 |
|---|---|---|
| B1 判据窗合并日差点估计 ≥ 0 | -0.477 bps/日(915 天)| **FAIL** |
| B2 R-P 触线 ≤ NEW_S | NEW_S2 0/32 vs NEW_S 0/32 | **PASS** |

**对 NEW_S 的 N1–N5 全表(必报,不作门)**

| 项 | 值 |
|---|---|
| 判据窗日差点估计 | -0.477 bps/日 |
| 分段 | 2023H2 +0.884 / 2024 -0.550 / 2025 -1.090 / 2026 -0.295(1 段为正)|
| 三成本格 | fee_x1.25 -0.449; slip_x1.5 -0.438; fill_x0.9 -0.534 |
| 30 日块 97.5% 区间 | [-4.710, +2.984] |

#### NEWS2_s2027

**A 门 — 能否替换在役(对 OLD 与 OLD_HOLD,写法同 db0123df7 §3)**

| 规则 | 对 OLD | 对 OLD_HOLD | 判 |
|---|---|---|---|
| S1 判据窗日差点估计 > 0 | +6.207 bps/日 | +3.680 bps/日 | **PASS** |
| S2 分段中 ≥2 段 > 0 | 2023H2 +3.197 / 2024 +1.237 / 2025 +12.707(3/3) | 2023H2 -3.160 / 2024 -0.515 / 2025 +11.335(1/3) | **FAIL** |
| S3 最大回撤(路径均值)不差于 OLD_HOLD | — | NEW_S2 -22.5% vs OLD_HOLD -29.0% | **PASS** |
| S4 R-P 触线路径数 ≤ OLD_HOLD | — | NEW_S2 0/32 vs OLD_HOLD 10/32 | **PASS** |
| S5 三成本格 S1 同号 | fee_x1.25 +6.595; slip_x1.5 +6.830; fill_x0.9 +6.032 | fee_x1.25 +3.866; slip_x1.5 +3.946; fill_x0.9 +3.643 | **PASS** |
| (只报)30 日块 97.5% 区间 vs OLD | [-2.075, +18.397] | | 不作门 |
| (只报)30 日块 97.5% 区间 vs OLD_HOLD | [-3.166, +12.810] | | 不作门 |

**A 合判**:FAIL(未过:`["S2"]`)

**B 门 — 修复有没有把书弄差(对 NEW_S 同种子)**

| 规则 | 值 | 判 |
|---|---|---|
| B1 判据窗合并日差点估计 ≥ 0 | +1.403 bps/日(915 天)| **PASS** |
| B2 R-P 触线 ≤ NEW_S | NEW_S2 0/32 vs NEW_S 0/32 | **PASS** |

**对 NEW_S 的 N1–N5 全表(必报,不作门)**

| 项 | 值 |
|---|---|
| 判据窗日差点估计 | +1.403 bps/日 |
| 分段 | 2023H2 -1.881 / 2024 -1.006 / 2025 +5.474 / 2026 +0.418(1 段为正)|
| 三成本格 | fee_x1.25 +1.411; slip_x1.5 +1.378; fill_x0.9 +1.322 |
| 30 日块 97.5% 区间 | [-2.083, +6.099] |

### 对研究员 NEW 的差距(必报,不作门)

**NOT PRESENT**: 未提供 vs-NEW 收据(NEW_S2 对研究员 NEW 的差距)。FREEZE §2 把它列为必报,所以这里留一个具名空位,而不是省略这一节。

### 两项诊断(必报,不作门)

**NOT PRESENT**: 未提供诊断收据。必报两项:① 三版本分数层 IC 同锚比较;② 逐修复项作用列数。

### 延伸段(只描述)

<!-- from NEWS2_EXT.json sha256 8f5a011f38f8f066c8472d39e3b7e2e160fde8b2067f897f1f76f8040cb788b1 -->
```json
{
 "OLD": {
  "n_paths": 32,
  "n_windows": 113,
  "n_full_days": 18,
  "total_return": {
   "path_mean": -0.05418821738561297,
   "p2.5": -0.06500606112815972,
   "p97.5": -0.04323667118950483
  },
  "sharpe": {
   "path_mean": -2.425301040612432,
   "p2.5": -3.1567226499938523,
   "p97.5": -1.6549587428570223
  },
  "worst_day": {
   "path_mean": -0.037485552113068324,
   "p2.5": -0.04083026870275693,
   "p97.5": -0.0355790263461324
  },
  "maxdd_5m": {
   "path_mean": -0.10844641576392437,
   "p2.5": -0.12340717514341831,
   "p97.5": -0.09756204048714999
  },
  "g": {
   "path_mean": -2.294882734852402,
   "p2.5": -2.802216594848832,
   "p97.5": -1.7883972375493493
  },
  "price": {
   "path_mean": -1.4572660309404286,
   "p2.5": -1.9720138852478386,
   "p97.5": -0.9577105409428499
  },
  "funding_paid": {
   "path_mean": 0.6495569746280686,
   "p2.5": 0.6389985280119381,
   "p97.5": 0.6582391963292968
  },
  "fee": {
   "path_mean": 0.18805972928366593,
   "p2.5": 0.184377974094541,
   "p97.5": 0.1911794585560513
  },
  "turnover_over_gross": {
   "path_mean": 0.06679732163380601,
   "p2.5": 0.06590592018313829,
   "p97.5": 0.06749984423338205
  },
  "day_stop_flattens": {
   "path_mean": 1.0,
   "p2.5": 1.0,
   "p97.5": 1.0
  },
  "per_name_stops": {
   "path_mean": 29.0625,
   "p2.5": 26.775,
   "p97.5": 31.0
  }
 },
 "NEWS2_s42": {
  "n_paths": 32,
  "n_windows": 113,
  "n_full_days": 18,
  "total_return": {
   "path_mean": -0.05143707718211935,
   "p2.5": -0.062976007
```

### 前置条件

- OLD 复现复核:`{"base": {"n_identical": 32, "n": 32}, "fee_x1.25": {"n_identical": 32, "n": 32}, "slip_x1.5": {"n_identical": 32, "n": 32}, "fill_x0.9": {"n_identical": 32, "n": 32}, "lit": {"n_identical": 32, "n": 32}}`
- 四臂共用窗口轴:`{"first": "2022-06-30T00:00:00Z", "last": "2026-08-31T00:00:00Z", "n": 9139}`
- 不可用臂:0 个
- 统计量来自 `news_stats.py` sha256 `7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c`(import,非复制)



## 4. 必报项(冻结件 §2「必报(不作门)」)清点

| 项 | 状态 |
|---|---|
| 对 NEW_S 的 N1–N5 全表(分段、回撤、成本格) | **已出**, 见 §3.1 逐种子的 N1–N5 表 |
| 30 日块区间 + 原样附那句声明 | **已出**, 见 §3.1(每种子对 OLD / OLD_HOLD / NEW_S 三组区间, 并附区间说明原文) |
| 对研究员 NEW 的差距 | **`NOT PRESENT`** —— 渲染器留了具名空位。未提供 vs-NEW 收据 |
| 诊断 1: 三版本分数层 IC 同锚比较 | **`NOT PRESENT`** —— 同上具名空位 |
| 诊断 2: 逐修复项作用列数 | **部分已有**: 射程门的 `cells_out_of_reach` / `other_pass1_cells_changed` 逐臂计数(§2 表), 尚未整成必报形式 |

**两处 `NOT PRESENT` 是渲染器主动打印的具名空位, 不是省略。** 渲染器的规则是: 冻结件要求的每一节都有
固定槽位, 输入缺失就打印「缺什么」——「缺表」与「一张全零的表」在成文文档里读起来一样, 所以不允许静默
省略。这三项仍欠, 已列入 §6 下一轮清单的**本轮欠账**一栏。

## 5. 偏离清单(全部, 含我自己的错)

| # | 偏离 | 处置 |
|---|---|---|
| 1 | **E-0923-F 静默窗破入**: 16:21–16:23:43Z 在生产 Mac 上跑全局门, 不在 [N+1:00, N+3:40] 内, 因为把钟看错一小时。按自己记录的 PGID 32535 杀掉; 核实 16Z 生产者(16:17:31Z)与 combo(16:18:34Z)已完成、执行器 16:24:00Z 才读。 | lead 记入台账。此后本机重活一律经 `devices/run_local_gated.sh` —— 第一件事调 `venue_quiet_window.py`, 不开就 `exit 9` 什么都不启动。本轮 treeNC5 单测的门收据 `GATE_treeNC5_suite.json` 记 `open=True remaining_min=7.0`。 |
| 2 | **「三种环境三个不同的 King OOF」是错的, 已撤回**(lead 也独立要求暂停引用; 我的撤回在收到之前): 我比的是 `.npz` **文件 sha**。比数组: 预测 `P` 8,566,057 格 **0 格不同**; 文件 sha 的差异全部来自同档另存的每锚 `model_sha256`(8143/10333 与 5953/10333 条不同)。抓到它的是重跑的 `legs.npz` 与第一遍**逐位相同**, 而 legs 的 KZ 由 `K["P"]` 的值算出。 | 改正三处: 收据顶部 CORRECTION 段 + 逐数组比较、`run_chain_corrected.sh` 头注释标 RETRACTED、给 lead 的更正消息。代价: 白扔一对已跑到 16/23 折的 F10(约 20 分钟)。重跑本身仍正确, 但理由是「方案这么写」不是「否则数字会变」。<br>**lead 在批准重跑时曾要求把这三个 sha 写进本清单「作为这类钉必须存在的依据」—— 这条依据不成立**: 按判别法, 即使环境完全不起作用, 三个 sha 也照样各不相同。故此处记为**被撤回的主张**, 钉的理由改以 #3 的 (a)(b) 两条承担。lead 补充的机制(LightGBM 8 线程下叶子值在第 17 位有效数字上不确定 ⇒ 模型文本每跑都变)我未实测, 出处记为 lead。 |
| 3 | **第一遍 King/腿的训练环境不对**: 按装置名启链, 没读 `news_chain_resume.sh`(它钉 King 用 PV 且 `NPY_DISABLE_CPU_FEATURES` 已设、腿用 P314 + OMP=1、F10 用 PV 且该变量 unset)。 | 全部重跑到位, 解释器逐步与 lead 核实的清单(`ENV_F10_NEW_S.json`, fd38b892b)一致: King PV / 腿 P314 / F10 PV / 组合 P314。注: 本轮实测该环境**没有**改变 King 预测(见 #2), 所以这条是纪律偏离而非数字偏离。**钉必须存在的理由因此不是「否则数字会变」**, 而是: (a) 方案这么写, 且 B1/B2 是与 NEW_S 比, 同条件是判据的前提; (b) **腿这一步真的换了 Python 与 numpy 版本**(P314 = 3.14.4 / numpy 2.5.2 vs 系统 3.11.10 / 2.4.6), 这条不依赖任何 sha 比较。类形状修法见 §2.3。 |
| 4 | **`pre_king` 暂存收据没记 `argv`**: 复跑命令只能从源码反推。 | 装置已补 `argv`/`cwd`/`rerun_command`; 已出的那份 `STAGE_PRE_KING.json` 补不回去, 记在此。 |
| 5 | **暂存装置曾会删掉自己要暂存的输入**: `post_king` 源与目的可能同一 inode(腿按集成者给的调用方式写进 news2 根), 原码 `os.remove(dest)` 再 `os.link(source, dest)` = 删掉 `legs.npz` 再链一个不存在的路径。跑之前发现, **无损失**。 | 加 `samefile` → `in_place` 分支; 新增 `GREEN.in_place` 一格, 断言**文件仍在且 sha 不变**而非判词字符串; 变异实测该格报 `survived=False sha_now=FILE GONE`, 其余九格不动。 |
| 6 | **我给 `post_king` 写的「生产者还在跑就拒绝」守卫恒说通过**: 用 `pgrep -af`, 而 macOS 的 `pgrep` 没有 `-a` ⇒ 退非零、输出为空 ⇒ 空进程表被读成「已退出」。 | 改 `ps -Ao pid=,ppid=,args=` 自己匹配; **匹配脚本路径不匹配解释器名**(macOS 框架版 argv[0] 是 `.../MacOS/Python`, 原正则本机一个都匹配不到); 排除自身与祖先链(调起它的 shell 命令行必然含该模式); 测不到时报 `could_not_measure` 并拒绝。新增 `RED.producer_running` 真起一个匹配进程验证。套件 11 格 rc 0, 两台机器都绿。 |
| 7 | **B8 新装置先给出一个假 FAIL(79,248/116,060)** —— lead 记为「红控救了判词的一例」: 树的闭包只实现 `"sum"` 与「其它一律当 mean」, 问 `"count"` **不报错**而静默回均值, 于是我拿均值跟计数比; 且 D5 政策是 float64 累加后 round 回 float32, 参照必须先取 float32。 | 只比真实存在的两种 kind, 并**实测证明**该回退存在(问不存在的 kind 必须与 `"mean"` 逐位相同 ⇒ True); 参照取 float32。 |
| 8 | **该 B8 的红控自己也先失效过, 因此判 UNAVAILABLE 而非 PASS**: 我用 `np.array_equal(src, cd[:,:,1])` 认参照数组, 有 NaN 时恒 False, 扰动数组从未代入, 控制在拿自己跟自己比。 | 改成把参照数组作**显式参数**传入。现红控差 2 格 = 含被扰动行的 1 个窗 × 1 个名 × 2 种 kind, 自洽。<br>**这个洞只在装置侧, 生产路径上没有**: 集成代理只读核过上线树 treeNC5 —— 生产者调 `wstat` 的两处 kind 都是字面量(`"sum"` 与 `"sum" if nm == "ret5" else "mean"`), 「其它一律 mean」的回退在生产路径上走不到; 且 `F8_TREND_ROWS` 在 f8 第 214 行有 `_tr_rows in ("all","last")` 断言, 非法值一律报错。所以只有**外部按 kind 调用它的装置**(我的 B8)会碰到, 修法(先打一发非法值实测回退再写进收据)仍然照留。 |
| 9 | **六个链装置一个都没入库**(`news2_train_king/train_f10/combo/make_configs/ext/adapter_specs`), 其中三个连 pod2 都没上传 —— 链走到引擎配置会缺装置; 且 King 已训完而产它的脚本不在库里。 | 补齐, 逐个按派生收据 `output_sha256` 核对 MATCH, 六份派生 diff 一并入库。 |
| 10 | **p2「卡住」误诊**(早前): 报出直接回收与 42 小时外推, 两条腿都错 —— `pgscan_direct` 是开机以来累计(当期增量 0, PSI 0.00), 且我取的是**父进程** `ps TIME`(不含 27 个子进程的 1186% CPU)。 | 数分钟内向集成者撤回, 对方确认未采取动作。正确做法: `/proc/<pid>/stat` 字段 14–17 含 `cutime/cstime`, 并按轴位置量进度。 |
| 11 | **我自己的 D7 信号预测器被我自己的门证伪**: 960 个锚被标记, 抽测 6/6 全是 `D7_moves_row=0`。 | 标 `FALSIFIED`, 通知集成者不要并入。漏检根因: `--selftest` 测的是计数器, 不是推导。 |
| 12 | **三处测试夹具假绿**(全是我的): 全 NaN 列被 `anchor_rank_block` 映成全零(有限格计数看不见, 改数非零格); 比较窗没真正落在被编辑的前缀之后; 修好上两处后基线不再红, 该格证不了任何事故删除。 | 已修/已删。 |
| 13 | **一份收据被 `rm` 先于 `cp` 丢失**(早前)。 | 自报, 记在此。 |
| 14 | `run_parity_pair.sh` 曾用 `setsid <script>` 直接执行, `/dev/shm` 是 `noexec` ⇒ `Permission denied`。 | 改经解释器 `bash <script>`。日志记下了它, 没有静默空转。 |
| 15 | 一次等待循环用 `until test -f <receipt>`, 而该收据是**前一次失败尝试**留下的 ⇒ 条件立刻满足, 我把陈旧的 ERROR 收据读成当次结果。 | 后续等待门改为同时要求「生产进程已退出」与「标记出现」; `run_p4_after_p3.sh` 的门是 `P3_CORRECTED_DONE`(它在 `set -e` 下排在两个种子退 0 之后), 不是「进程没了」。 |

## 6. 下一轮清单(本轮不动)

**本轮欠账(不是「留到下一轮的研究轴」, 是这一轮该出而未出的必报项)**:

| 欠账 | 缺什么 |
|---|---|
| 对研究员 NEW 的差距 | 需要研究员 NEW 臂的同口径读数收据; 未提供, 渲染器留具名空位 |
| 诊断 1: 三版本分数层 IC 同锚比较 | 需要 NEW / NEW_S / NEW_S2 三份分数在同一批锚上的 IC; 未算 |
| 诊断 2: 逐修复项作用列数 | 射程门已有逐臂 `cells_out_of_reach` / `other_pass1_cells_changed`, 未整成必报形式 |

| 项 | 为什么留到下一轮 |
|---|---|
| **D2 / D3 / D10 / D12** | 冻结件确定的本轮范围之外 |
| **R1** | 同上 |
| D7 信号预测器的两个候选故障 | 已记 §B4 待办; 它被证伪, 本轮的 D7 准入不依赖它(依赖行独立性 + 分辨力两条) |
| 全轴平价 | 本轮两条平价各 5 锚。若要把「训练树 ≡ 上线树」当成无条件结论, 需要全轴或分层抽样 |
| 实盘取数路径的等价性 | 三棵树真正的差异所在, 回放测不到(§2.2 限度 2) |

## 7. 复跑

全部装置在 `multi_asset/exports/research/news2_2026-09-23/devices/`, 收据在同目录 `receipts/`。每份收据带 `self_sha256`、`utc`、`argv` 与 `rerun_command`(#4 所列那一份除外), 门类收据另带红控格与实测值。链的两个驱动: `run_p3_legs_f10.sh`(腿 → 暂存 → F10)与 `run_p4_chain.sh`(组合 → 适配器 → 配置 → 引擎 → 读数 → 判词 → ext), 两者逐步照 `news_chain_resume.sh` 派生, 只改根目录、装置名、臂名, 每步解释器与环境逐字保留。
