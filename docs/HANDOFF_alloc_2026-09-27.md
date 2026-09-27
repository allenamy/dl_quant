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

---
## 6. 追加:09-27 迁机后恢复至今的状态(alloc,`date -u` 14:07:41Z;lead 额度用尽,预计 09-30 接回,期间由独立研究员接手,见 `HANDOFF_independent_researcher_2026-09-27.md` §7,d889e647c)

### 6.1 已结案(结论与收据)
| 线 | 结论 | 收据 |
|---|---|---|
| S1 挤空状态门(NC) | **FAIL**:没有强到约 0.02 以上的残差信号。IC 在 0.005–0.010,8 个段点的下界全部 > 0;两个模型的 σ 比都低于 0.02。06:5xZ 恒等控制的 harness 暴露了一格 MAIN 读数,已具名写入结果件 | `docs/RESULT_S1_squeeze_gate_NC_2026-09-27.md`(af8d3b07e);判官换版 rev1 附恒等控制(66676d57c) |
| 第二批设计 | T7 → XIB(暂缓)→ S3 前向;回答了 σ 比问题(守卫对校准回归等于第二道 IC 门) | `docs/DESIGN_nonfunding_next_2026-09-27.md`(54cf2dea5) |
| T7 韩元溢价(NC) | **四个候选全部 FAIL** ⇒ 按冻结版 §8 关闭。经过 AMENDMENT 1 / 2 / 3、G2 诊断、判官正负控制(276d68e44)与 G3b | `T7/RESULT_T7_S1_NC_2026-09-27.md`(be6c1b633) |
| 综述 | 资金费以外暂无可靠来源:稀释代价 + 强基线 ⇒ 新源在全集上需要约 0.02 的低相关 IC;建议转向组合、执行与风险(§3b 的「多空偏斜」一项已撤回) | `docs/SYNTHESIS_nonfunding_2026-09-27.md`(b8233a187;更正 12a3bbaaf) |
| 代币解锁可行性 | 零收益:DefiLlama 数据集免费;事件 ≥ 1% 的每年 41–130 起;有三处硬限制;先做四个零收益步骤 | `docs/FEAS_token_unlock_2026-09-27.md`(bc7d022c3) |
| 净额中性修复 | 步 0 分解完成(组合层偏斜主要来自交易带);**该偏斜在下单前被 reshape 中性化 ⇒ 作用面约为零,任务 2 不做**(lead 裁定) | `docs/DESIGN_net_neutrality_fix_2026-09-27.md` 与文末更正;`neutrality/NEUTRAL_STEP0.json`(0b28d38a5) |
| 停机窗设计 | 只是分析,不是 v2 草稿;H1 挂起,等 integ 的 §4a / §4b;通用恢复手册已写 | `docs/DESIGN_post_flatten_halt_2026-09-27.md`(63e878407 / 8f1d6456a);`docs/RUNBOOK_post_trip_resume_generic_2026-09-27.md` |

### 6.2 等待中(没有执行者之前不起)
- **停机窗步 0**:零收益,只读执行器账本,只报合池,走属主读取函数(collapse_supersedes)。
  - **起跑条件**:独立研究员在 **16Z 首锚验收通过**之后通知 alloc(lead 裁定;见 d889e647c §7 第 2 条)。
  - 装置尚未编写;按「先入库再运行」执行,并用 registry_edit 登记。
  - **此步目前没有进程执行者,只靠本会话接收通知**(§10-f 第 1 条:缺口在此写明)。

### 6.3 常驻
- **S3 跨所采集器**(launchd `com.hsy.xvenuecollector`):
  - 会话 cron bc87c369 每 30 分钟看一次,只在 s3=BAD 时报 lead(lead 离线期间报独立研究员);
  - 至 13:58Z 一直 OK;迁移期间有两段具名空洞(registry 已记)。
  - 满 6 个月(约 2027-03-27)评估。

### 6.4 pod2 与本机上的残留(均为我的,都不大)
- pod2 `/dev/shm/alloc_2026-09-26/`:l2n 标记与日志,以及 neutral/ 的步 0 输出,约 1 MB 以内。t7nc 与 eta 目录已删。
- pod2 `/workspace/uplift_r3_2026-09-13/L2/out/L2N_*.npz`,约 300 MB:lead 裁定保留,作为判定运行的产物供复核。
- 本机 `~/cc_tmp/t7_nc/`(U_NC、legs 等副本)、`~/cc_tmp/krw_pull/s1/`(T7 候选,72 MB)、`~/cc_tmp/unlock_feas/`(DefiLlama 数据集,22 MB):sha 都已记入收据。

### 6.5 本轮我犯的错(均已在当时具名更正)
- `4d5cd3d79`:误把 fresh2 未提交的 registry 条目一并提交。原因是 commit 没有与写入用 && 串联;已通知 fresh2;此后改登记一律用 registry_edit。
- S1 恒等 harness 在真实数据上打印了一格读数;此后凡是在真实数据上跑全程的控制,stdout 一律重定向到文件。
- T7 设计里把 IC_B 写成了零收益步骤,已更正。
- AMENDMENT-2 §0 对 kc = 0 的解读错误,已追加更正。
- 文档首行的时刻靠估计,已改为用 `date -u`。
- feas_counts.py 先运行、后入库。
- 净额中性设计与综述只读了记忆的前半段,漏掉了更正节,已撤回。
