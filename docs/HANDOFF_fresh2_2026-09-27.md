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
