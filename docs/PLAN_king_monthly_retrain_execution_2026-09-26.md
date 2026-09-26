> **创建:** 2026-09-26 18:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 执行计划(判据 = lead 冻结的 `DECISION_RULE_king_monthly_retrain_2026-09-26.md` 1f2f5c4e9;本文不含任何判据) | **作废条件:** 判据文件改变

# 执行计划:King 按月重训族(A0 / A1 / A3 × 8 成员 × 2 个 F10 种子 + 红控)

## 装置(`multi_asset/exports/research/mretrain_2026-09-26/devices/`,部署到 pod2 `/dev/shm/mretrain_2026-09-26/devices/`,其余装置从 news2 根逐字节复制)

| 装置 | 来源与改动 |
|---|---|
| `mr_train_king.py` | news2 `news2_train_king.py` b19459a5,只改:输出目录、random_state、按臂的折规格(A0 年折原样 / A1 月折 / A2 季折,扩张 / A3 年折 + 滚动 24 月训练窗)、收据字段、训后删模型文件(A0_m0 保留)。逐行差异 `mr_train_king.DIFF.txt` |
| `mr_combo.py` | news2 `news2_combo.py` 1cbccc98,只改两行:根目录取环境变量 `MR_W`;F10 固定从在役 news2 根读(判据 §5)。差异 `mr_combo.DIFF.txt` |
| `nc_legs.py` / `news2_adapter_specs.py` / `ovn_adapter.py` / `bt_launch.py` | news2 根原样(nc_legs 18387627) |
| `mr_shuffle_king.py` | 红控:A0_m0 的 King 分数在每锚内跨名打乱(种子 20260926),其余不变 |
| `mr_gates.py` | 判据 §0 第 1–3 项:确定性(A0 rs=0 训两遍)、A0 = 在役 KING_OOF(a10b8725)、A0 经 chain 复现 legs(9ee5886f)/ combo / 在役 X 目标。判在数组逐位上,容器 sha 另报 |
| `mr_prep.sh` / `mr_engine_queue.sh` / `mr_master.sh` | 驱动;见下 |

## 执行者(TEAM_PROTOCOL §10-f:每一步都有进程执行者)

| 步骤 | 执行者 |
|---|---|
| A0_m0 全链 + A0 rs=0 第二次训练 + 装置门 | `mr_master.sh`(pod2,setsid,PGID 记录在 `logs/master.log` 首行) |
| 装置门不过 ⇒ 全族停 | 同上(写 STOP,不起后续) |
| 其余 24 个(臂, 成员)的准备(3 路并发) | 同上(`mr_prep.sh` 子进程) |
| 50 个引擎格,一次一格;团队上限「全队最多两格」= 只在其他 bt_launch 组 ≤ 1 且共享运行门通过时起 | `mr_engine_queue.sh`(由 master 起) |
| 每格存逐路径序列后释放格子 | 同上 |
| **读数装置**(按判据 §1–§4 计算判词) | **目前无进程执行者,靠会话手动**(装置在引擎格跑完之前入库) |
| 换模型锚平价护栏(§3 第 3 条) | 同上,判定之后、推荐之前 |

## 顺序与格数

- 引擎顺序:红控 2 格 → A0_m0 2 格 → 按成员交替 A1 / A3 / A0。共 50 格(红控 2 + 3 臂 × 8 × 2)。
- 规划时长:每格约 11 分钟;一次一格 ⇒ 约 9.2 小时引擎时间。准备约 25 个任务,每个约 45 分钟,3 路并发 ⇒ 约 6 小时,与引擎重叠。
  **全族预计超过 12 小时**(与队内其他引擎排队后),已按 lead 要求报告。
- 存储:只在 `/dev/shm`(`/workspace` 配额已满);每个(臂, 成员)的中间产物在目标生成后删除(可按确定性重生成,sha 留在收据)。
