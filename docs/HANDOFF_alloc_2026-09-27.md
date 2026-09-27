> **创建:** 2026-09-27 03:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(alloc) | **状态:** 交接说明(lead 暂停令:用户迁移到新电脑);alloc 转入空闲 | **作废条件:** 下文任一在飞作业到达终态后,以其收据为准

# 交接:alloc(组合层 → 资金费以外的收益源)

## 0. 暂停时的状态(03:0xZ)

- 本地会话 cron 已全部停掉(巡检 19d38757 已删,CronList 为空)。不再起任何新作业。
- **没有未提交的产物**。本条提交同时把 S1 的 pod2 收据副本和日志入库到 `multi_asset/exports/research/uplift_r3_2026-09-13/L2/receipts/pod2_l2n/`。
- 暂停令允许 pod2 上两个自带标记的进程继续跑完;它们都不依赖本机会话。

## 1. 在飞作业(按 INFLIGHT_REGISTRY)

| registry 名 | 主机 | PGID(文件) | 标记日志 | 终态标记 | 此刻 |
|---|---|---|---|---|---|
| `alloc_S1_l2n_net` | pod2 | 3360852(`/dev/shm/alloc_2026-09-26/l2n/PGID_net`) | `/dev/shm/alloc_2026-09-26/l2n/l2n_net.log` | 行首 `STOP ` / `DONE ` | GATE_OK REPULL(02:58Z);**全量 CHECKSUM 进行中**(183,912 个文件,约 20 req/s,预计 05:30–06:00Z 完成);阶段日志 `l2n_CHECKSUM.log` |
| `alloc_S1_l2n_stat` | pod2 | 3362766(`…/l2n/PGID_stat`) | `/dev/shm/alloc_2026-09-26/l2n/l2n_stat.log` | 行首 `STOP ` / `DONE ` | 等待网络进程的 DONE;之后 build → fit → judge RESOLUTION → judge MAIN,预计网络完成后再跑 2–4 小时 |
| `alloc_S3_xvenue_collector` | 本机 launchd `com.hsy.xvenuecollector` | 无(常驻) | `~/xvenue_collector/logs/collect_<UTC 日期>.log` | `DISK_LOW` | lead 02:42Z 安装;**迁移时由 lead 决定停掉或搬迁**;存活证据:`~/xvenue_collector/state/heartbeat.json` 不老于 3 分钟 |

- **巡检方法**(E-0926-I、E-0926-J):逐个读标记日志的最后一行,并核对 PGID 是否还活着。
  - 进程在且无终态 = 在跑;进程不在也无终态 = 无声死亡;有终态没人报 = 漏报。
  - 命令:`ssh pod2 'for x in net stat; do tail -2 /dev/shm/alloc_2026-09-26/l2n/l2n_$x.log; ps -eo pgid= | tr -d " " | grep -cx $(cat /dev/shm/alloc_2026-09-26/l2n/PGID_$x); done'`
- **注意 /dev/shm 是 tmpfs**:pod2 重启会清掉标记日志和 PGID 文件。收据落在 `/workspace/uplift_r3_2026-09-13/L2/receipts/`,不受影响。

## 2. S1 到终态之后该做什么

- **网络进程的 DONE**(GATE_OK CHECKSUM):读 `/workspace/uplift_r3_2026-09-13/L2/receipts/RECEIPT_L2N_CHECKSUM.json` 的 `files_by_result`。
  - 有 MISMATCH 或 UNVERIFIED 时,统计进程的 build 会按 G-IN 硬停(STOP build_rc)。这时要查 `out/checksum_full/<SYM>.json` 里具体是哪些文件。
- **统计进程的各个标记**:
  - `GATE_OK build`:收据 `RECEIPT_L2N_build.json`,里面有覆盖率、404 对账、标签期违例比例;
  - `GATE_OK fit`:收据 `RECEIPT_L2N_fit.json`,分辨力臂的种入强度 c 与实达 IC 在 `resolution` 字段;
  - `GATE_OK resolution` 或 `STOP RESOLUTION_FAIL_S1_stops`:收据 `RECEIPT_L2N_judge_RESOLUTION.json`,看 eligible_models;
  - `VERDICT_OK …`:收据 `RECEIPT_L2N_judge_MAIN.json`,判词为 VOID / FAIL / PASS。主判表按种子 × 模型 × 段给出 A 目标的 IC 与区间,另有两个泄漏门。
- **判据**:`docs/DECISION_RULE_nonfunding_sources_2026-09-27.md` §1(lead,54866038b),加 AMENDMENT `multi_asset/exports/research/uplift_r3_2026-09-13/L2/AMENDMENT_L2_NC_population_2026-09-27.md`(2838b830d)。三处定义性选择 lead 已采纳:NC 人口用「fund z < 0」;偏移谱取前向峰;主判只用在两种子两段上都检出的同一模型。
- **PASS 的唯一后果**:由 lead 写书层预注册。动作 = 同人口、beta 相近名替换,不得单边缩空头;判据形状为风险终点。
- 结果写进 `docs/RESULT_combination_layer_2026-09-26.md` 的后续节,或新建 S1 结果件;并在 registry 里关闭这两条。

## 3. 如果要在新环境续跑

- 全部装置已入库:
  - `multi_asset/exports/research/uplift_r3_2026-09-13/L2/devices/l2n_*.py`
  - `run_l2n_net.sh`、`run_l2n_stat.sh`
- pod2 上的副本与仓库逐字节相同(sha 已核)。
- **续跑**:`l2n_pull_verify.py` 可续跑。CHECKSUM 阶段已完成的符号,在 `out/checksum_full/<SYM>.json` 里标记为 complete,重跑会跳过;REPULL 阶段每个符号有 `.done` 文件。
  - 若网络进程中途死亡,先确认 PGID 不在,再按 `run_l2n_net.sh` 的写法重起:REPULL 会整体跳过,CHECKSUM 从断点接着做。
  - 统计进程也需要重起:它以网络日志出现 DONE 为起跑条件,如果旧日志里已经是 STOP,要先让网络进程写出新的 DONE。
- 环境白名单与限速沿用 L2 纪律:`env -i`、nice 10、8 核、l2_net 限速器。PID 333197 那两个进程继续保持不碰。

## 4. 本轮已结案(不需续跑)

| 线 | 结论 | 受据 |
|---|---|---|
| 组合层第一族(A1–A4) | 红控 R、R′ 在 pre-2026 都不过 ⇒ 按判据终止,不再修订;原因是在役书 pre-2026 自身的 t 只有 1.6–1.9 | `docs/DESIGN_combination_layer_2026-09-26.md` §6;`docs/RESULT_combination_layer_2026-09-26.md` §1–§2 |
| M 族(动量中性) | 停在机制门;门统计量的零信息地板高于阈值(E-0927-A) | RESULT §3 |
| S2 交易所事件 | 韩元上币、监控标签都判 FAIL;「上币生效早于下一锚后强反转」只作描述 | `multi_asset/exports/research/nonfunding_2026-09-27/s2_events/` |
| S3 跨所采集器 | 已装(lead),满 6 个月再评估 | 同目录 `s3_collector/INSTALL.md` |
| 错题 | E-0926-E(失败信号写在失败的卷上)、E-0926-J(等待器通知送不到空闲会话)、E-0927-A 的补记 | `docs/ERROR_LEDGER_2026-08-20.md` |

## 5. pod2 上可清理的东西(**需 lead 决定,我没有删**)

- `/workspace/alloc_2026-09-26/cells/`,约 650 MB 以上:
  - 其中恒等格 `inservice_shared_s42` 的 PATH 文件,lead 要求保留;
  - 其余是已判完的红控格 fundflip / negbook,以及 M 族的 combo 格。
- `/workspace/alloc_2026-09-26/work/mom_features.npz`,约 200 MB,是 M 族的输入,可重建。
