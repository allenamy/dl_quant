> **创建:** 2026-09-27 03:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh2) | **状态:** 交接说明(lead 暂停令:用户迁移到新电脑;本地 Mac 上 fresh2 的 cron / 等待器已全部停,pod2 作业按令自行跑完) | **作废条件:** 下列任一作业的终态标记已被读取并入库后,该节作废

# fresh2 交接:King 月度重训族(已停)/ King 根因 3b / King 改进族(KN、A1、A0 成员)

## 0. 一眼看状态(03:00Z 读数)
| 作业 | pod2 PGID | 日志(登记在 INFLIGHT_REGISTRY) | 终态标记(行首) | 03:00Z 状态 |
|---|---|---|---|---|
| King 月度重训族 run 3 | 3341317(已由 fresh2 停) | `/dev/shm/mretrain_2026-09-26/logs/master.log` | `STOP` / `MASTER_STOPPED` | **已终止**:红控 FAIL 01:31:59Z,按判据 §0 全族停(33abbad32);lead 已接受 |
| 根因 3b:SEAT_ONLY / COMP_ONLY × 2 种子 | **3360754**(`rc_hybrid.sh`) | `/dev/shm/mretrain_2026-09-26/logs/rootcause.log` | `^\S+ (STOP\|RC_HYBRID_DONE)` | 在跑:SEAT_ONLY s42 已完成,s2027 在引擎;后面还有 COMP_ONLY s42/s2027。每格约 15 分钟 ⇒ 预计约 03:35–03:45Z 出 `RC_HYBRID_DONE` |
| 改进族训练 KN + A1 | **3365381**(`kf_train_family.sh KN A1`) | `/workspace/kingfam_2026-09-27/logs/kingfam.log` | `^\S+ (STOP\|KF_TRAIN_DONE)` | 在跑:KN 8 + dup 已训完;A1 m0–m2 在训(每个约 13 分钟,3 路并发)⇒ 预计约 03:30Z 出 `KF_TRAIN_DONE arms=KN A1` |
| 改进族清单 + A0 成员 | **3366800**(`kf_manifest_ic3.sh`) | 同上 kingfam.log | `^\S+ (KF_MANIFEST_IC STOP\|KF_MANIFEST_IC_PAIRED_DONE)` | 在等 KN/A1 完成 → 训 A0 m0–m7 + dup(约 5 分钟)→ 写 `MANIFEST_IC.json` ⇒ 预计约 03:35–03:40Z |
| (dlarch 的)IC 读数执行者 | 3366884(`run_kic.sh`,dlarch 的,不归我) | dlarch 侧 | dlarch 侧 | 绑我的 3366800 与 `KF_MANIFEST_IC_PAIRED_DONE` 行 |

PGID 文件:`/dev/shm/mretrain_2026-09-26/logs/PGID_rootcause.json`,`/workspace/kingfam_2026-09-27/logs/PGID_train.json`,`/workspace/kingfam_2026-09-27/logs/PGID_manifest_ic.json`(A0 那次训练会另写 `PGID_train_A0.json`)。
**只许 kill 以上由 fresh2 记录的 PGID;不 pgrep / pkill。**

## 1. 恢复后第一步(按这个顺序)
1. 跑 `python3 multi_asset/exports/research/loop_2026-09-26/inflight_status.py`,看三条 fresh2 作业是 TERMINAL / RUNNING / SILENT_DEATH。
2. **根因 3b**(`RC_HYBRID_DONE` 之后):读数装置已由驱动自动执行,产物 `/dev/shm/mretrain_2026-09-26/receipts/RC_READ_hybrid.json`(`rc_read.py`,e16524796,先于读数入库;已知答案冒烟收据 `mretrain_2026-09-26/receipts/rootcause_2026-09-27/RC_READ_smoke_known_answer.json`)。要做:取回入库,把路径和要点发 dlarch(它在合成根因结果件)与 lead。报法:RED / SEAT_ONLY / COMP_ONLY 对 A0_m0 的 D̄(两段,MBB95,逐种子),2026 逐月「总差 / 价格」,通道(价格 / 付出资金费 car[+ = 付] / 费用),交互项 = RED − SEAT − COMP(单项替换不可相加,照报)。
   - 同时补入库 `rc_decomp.py` 的完整版(含席位部分):`python rc_decomp.py /workspace/mretrain_2026-09-26/redcause/legs_RED.npz <out>`(pod2,`/dev/shm/mretrain_2026-09-26/devices/`,用 `/workspace/venv/bin/python`),把提交号告诉 dlarch(它的结果件目前引用的是入库前那版的 sha 4971ebfd,那版残差列公式错,其余列不受影响)。
3. **改进族**(`KF_MANIFEST_IC_PAIRED_DONE` 之后):IC 读数由 dlarch 的 run_kic.sh 自动起。fresh2 要做:取回 `MANIFEST_KN_A1.json`、`MANIFEST_A0.json`、`MANIFEST_IC.json`、各 `{KN,A1,A0}_m0_dup/DUP_CHECK.json`、各成员 `KING_IDENTITY.json`(模型文本 sha + 分数 sha,判据修订 1 要求每格报)入库。IC 判词出来后,按判据 §3 书层:选 ΔIC 中位成员 × 2 个 F10 种子跑引擎(用 `mr_prep.sh` + `mr_engine_queue.sh <ORDER> rootcause` 形态的机器;需新写 ORDER 与读数,写于读数之前)。
4. 若出现 STOP:先读对应日志行,不改判据,报 lead。

## 2. 各作业怎么续跑(若进程在迁移中丢失)
- **根因 3b**:`rc_hybrid.sh` 可重入 —— 已有 `READY_s*` / `DONE_s*` 标记的格跳过,已存序列在 `/dev/shm/mretrain_2026-09-26/series/SER_{SEAT_ONLY,COMP_ONLY}_m0_s{42,2027}.npz`。续跑:`setsid nohup bash /dev/shm/mretrain_2026-09-26/devices/rc_hybrid.sh > /dev/shm/mretrain_2026-09-26/logs/rc_hybrid.out 2>&1 < /dev/null &`(先把 rootcause.log 里的旧 STOP 行归档,否则终态正则误判)。
- **KN / A1 训练**:`kf_train_family.sh` 对已有 `KING_OOF.npz` 的成员不重训(只重算 identity),可重入。续跑同上形态,参数 `KN A1`。
- **清单 + A0**:`kf_manifest_ic3.sh` 从头等 `KF_TRAIN_DONE arms=KN A1`;A0 成员同样可重入。它绑定的训练 PGID 从 `PGID_train.json` 读 —— 若训练进程已不在而 KF_TRAIN_DONE 已写,它直接往下走。
- 续跑后必须把新 PGID 同步给 dlarch(它的 run_kic.sh 绑的是 PGID 3366800,换了要它重起)。

## 3. 已入库的结论与收据(本会话)
- **月度重训族**:run 1 路径缺陷的类修法 + 预检 + 红测 fb2e08ee7;run 2 装置门 FAIL(仅 model_sha256 文本不同)b688a7303;lead 修订 1 后重判 PASS 1da5ea3d5;ulp 来源探针(描述)10d7dfabc;A1_m0 重复训练 PASS + run 3 红控 FAIL 33abbad32(pre-2026 −5.76 [−16.13, +4.18],2026 **+4.29 [+0.20, +13.11]**;引擎复现控制两种子 PASS)。
- **根因(描述)**:King 单模型分数层 IC 2026 逐月 +0.051..+0.083(t 6.6–11.4),全年 0.068;RED − A0 在 2026 全在价格通道,4 月一个月约占 93%;pre-2026 的 −5.80 中多付资金费 3.47。装置 e16524796,RED legs 按 run 3 sha 复现(7f40e476)。
- **改进族**:训练装置 kf_train_king.py(bf4594ff)与门 KF_GATE0 v2 PASS 95010d4c7;T_NET 钉 929ff9f6 e02638d75;清单等待器 v3 ae8611af0。

## 4. 已知装置缺陷(未修,不影响在飞作业)
- `mr_master.sh` 的准备循环在「并发名额等待」之后不复查停止标记:run 3 在 STOP 之后仍派了 A0_m3 的准备(已记 master.log)。月度重训族已停,修复留待该族重开时。

## 5. 追加(2026-09-27 14:1xZ;lead 额度用尽,预计 09-30 回来;期间由独立研究员接手,见 `docs/HANDOFF_independent_researcher_2026-09-27.md` §7)
> 本节取代 §0–§4 中与之冲突的状态描述。§4 的缺陷已按类修复:34285ccd7(mr_stop.sh 加红测 8/8)。

### 5.1 在飞:KSR 书层 36 格(唯一在飞作业;lead 令:照常跑完,并发 1,PAUSE 协议照旧,收据入库,**判词不归 fresh2**)
- **执行者**:pod2 上的 `ksr_master.sh run`,PGID **3479615**,12:54:55Z 起跑。装置 65df8b070,以及 PAUSE 让路 12e179c37;门 4 装置是 dlarch_ksr_splice.py,钉住 9557d128。判据 5b4fc6cda + 修订 1 c1f9571b5;清单 609f8ff3;预检 KSR_PREFLIGHT_OK 12:53:43Z。
- **登记**:INFLIGHT_REGISTRY 条目 `fresh2_ksr_book_cells`(006eaaec5)。日志 `/dev/shm/mretrain_2026-09-26/logs/ksr.log`,终态行首为 `^\S+ (STOP|KSR_DONE)`,成功行为 `KSR_DONE series=36`。引擎队列日志在 `logs/engine/queue.log`;每个引擎格的 PGID 在 `logs/engine/PGID_KSR_*_s*.json`。
- **进度(14:07Z)**:
  - 预检 OK;S0_m0 = A0_m0 已导出(legs 9ee5886f、targets 统计、series 硬链接);18 格的 King 已预放。
  - `KSR_S1_m0` 的 prep 于 13:29Z READY,**门 4 PASS**(first_window 2023-10-01,reached=True)。
  - 13:29Z 起两边都在 PAUSE 上等待。
- **PAUSE**:`/dev/shm/mretrain_2026-09-26/PAUSE` 由 dlarch 的 D10 重读执行者在 13:18:27Z 放置(文件内容「dlarch D10 reread 13:18Z pgid 3483262」),由它退出时的 trap 移除,预计约 14:10Z。已记 registry note 14fd9a4e1。
  - 移除后,驱动与引擎队列会在 60 秒内自动恢复。
  - **孤儿情形**:PAUSE 还在,而文件里的 pgid 已不在(例如 SIGKILL,trap 不会跑)⇒ 记一条 registry note,并通知 dlarch 与 lead(或接手人)。**不要自行删除别人放的文件**,由其放置者或接手人决定。
  - 每次暂停和恢复都用 `registry_edit.py note --name fresh2_ksr_book_cells --note '…' --by <你>` 当场记下。
- **工期**:prep 是关键路径,每个 30–45 分钟(run 3 实测),共 18 个;引擎格与之重叠。预计 **09-28 01:00–04:00Z** 完成(lead 已接受;并发保持 1,lead 裁定)。
- **会话侧等待器**(fresh2 的会话,会话结束就消失):终态等待器绑 PGID 3479615 与终态行;PAUSE 等待器区分已移除与孤儿两种结局。阶段监视器(Monitor)在 13:25–13:55Z 之间漏报了 READY 与 PAUSE 两行,原因未查明,已停用;**以日志为准**。

### 5.2 缺口(§10-f):收据入库没有进程执行者
KSR_DONE 之后,把收据取回研究仓并入库这一步只能由会话来做:pod2 上的进程不能向 Mac 的仓库提交,而 lead 令不开新作业,所以也不装 launchd。**若 fresh2 的会话在完成前结束,接手人按下面做**:
1. `python3 multi_asset/exports/research/loop_2026-09-26/inflight_status.py`:看 `fresh2_ksr_book_cells` 是 TERMINAL、RUNNING 还是 SILENT_DEATH。
2. 取回到 `multi_asset/exports/research/mretrain_2026-09-26/receipts/ksr_run_2026-09-27/`:
   - `/workspace/ksr_2026-09-27/gate4/*.json *.log`(约 1M);
   - `legs/SHA256SUMS`(npz 不入库,共 70M,只记 sha);
   - `targets_stats/*.json`(npz 只记 sha);
   - `/dev/shm/mretrain_2026-09-26/logs/ksr.log`、`logs/engine/queue.log`,以及每格的 `logs/KSR_*/prep.log` 与 `hook.log`;
   - 在 pod2 上执行 `sha256sum series/SER_KSR_*` 的输出(序列文件在 pod2 上供 dlarch 读取,不入库)。
   - 每一项都与 pod2 原件比对 sha。
3. `git add -f -- <路径>` 后 `git commit … -- <同样的路径>`,再用 `git show --stat HEAD` 核对只含这些路径。
4. `registry_edit.py close --name fresh2_ksr_book_cells --note '<终态行 + 提交号>' --by <你>`。
5. 书层判词由 dlarch 的 `dlarch_ksr_book.py`(277230008)按判据 §2 机械套用。两个混合格的格名(KSR_SEAT_ONLY_m0 / KSR_COMP_ONLY_m0)已告知 dlarch。判词最高只到 OPTION_FOR_USER。
- **若出现 STOP**:先读 ksr.log 里那一行。门 4 FAIL ⇒ 全族停(判据 §0),不改判据,报告。prep FAIL ⇒ 看 `logs/<格>/prep.log` 与 `hook.log`。
- **只许 kill** PGID 3479615,以及 `logs/engine/PGID_KSR_*` 里记的引擎格 PGID;不许 pgrep / pkill。

### 5.3 本会话(迁机后)已入库的结论与收据
- 收尾:(3b) 与改进族训练的收据 242c84797;RC_DECOMP_full(dd26b562)。
- KN / A1 的 IC 判词(dlarch d585e1792):两臂都 FAIL ⇒ 书层格不跑,KN1 不起。
- 十月 King:训练器 8dd1a0068,控制 5078fd402(全过);发布运行 e7181349d(G1–G3 PASS)。
  - **要钉的文件 `release/m0/king_2026.txt`,sha 8534e56b…**,MANIFEST_RELEASE 2d0fa3f9;已交 integ(integ 已核对研究仓副本)。
- 在 D10 延长特征上的重预测:43e43f31b(C0 == 274ba08a;新 OOF 6579bc4e;切点前差异 0,切点后 38,853 格)。已交 news2 与 dlarch。
- 在役服务模型出处:d8692ba67(700d9e7b 同一性链五处一致)。
- 类修复与工具:
  - mr_stop.sh(34285ccd7);
  - 三方部署核对 `common/pod2_deploy_verify.sh`(9043ea94e):mretrain 部署目录 106/106 OK(07921fedb),king_oct 部署目录 8/8 OK;
  - nc_legs / nc_hist_features 的 pod2 实跑字节已入库(9043ea94e);
  - news2 在 09-26 复制进来的 9 个旧文件已移入归档子目录(07921fedb)。
- 事故:07:18Z 前后,hook 测试把 pod2 的根 overlay(/tmp)写满约 1 分钟(65df8b070 说明;TEAM_PROTOCOL f0ee74b54)。

### 5.4 未决(不归 fresh2 执行)
- nc_2026-09-23 目录里的 nc_legs / nc_hist_features 与 pod2 实跑版本不一致:news2 报 lead。
- 无其他在飞作业。本地另外没有 cron。
