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

## 补记 1(fresh2 接手,2026-09-27 00:0xZ;写于任何引擎序列之前 —— pod2 `series/` 目录此刻不存在)

**第一次运行(18:08Z 起)停在 A0_m0 准备,不是读数。** King(容器 2e42cabf)与 legs(9ee5886f,与在役逐位同)已完成;combo s42 在 18:35:32Z 报 `FileNotFoundError: /dev/shm/mretrain_2026-09-26/vendor_live/fea171/combo_stage.py`。日志留证 `receipts/run1_2026-09-26T1808Z_STOP/`。

**成因(类形状):同一个文件由两条规则各算一遍路径。** `combo_target.source_kernels()` 从 `ROOT = devices/..`(= 族根)读 combo_stage.py;`mr_prep.sh` 把它链接到臂根 `arms/<LBL>/vendor_live/`,`mr_combo.py` 的收据也记臂根那一份。在 news2 里两条规则恰好指向同一目录;MRETRAIN change 1(W = 臂根)把它们分开了,之后没有任何东西在训练前读这条路径。

**修法(不改 combo_target / continuous_combo,它们的 sha 被在役收据钉着):**
1. 一条规则:`mr_combo.STAGE = combo_target.ROOT/'vendor_live/fea171/combo_stage.py'`;`mr_prep.sh` 用 `mr_combo.py --stage-path` 问设备本身再链接;收据 `sources` 记 STAGE(即实际被读的那一份);臂根不再放副本。
2. 预检(训练之前):`mr_combo.py --preflight` 先调用 `combo_target.source_kernels()`(18:35Z 失败的那次读取本身),再按 `mr_combo` 自己的 `input_paths()/source_paths()`(主流程用的同一张表)逐项对照在役 NEWS2 combo 收据(该收据经在役 X 运行配置的字面 sha 钉住)。由 `mr_prep.sh` 在 King 训练之前执行;`mr_master.sh` 在任何训练前先跑 `mr_prep.sh A0 0 preflight` 与 `mr_preflight_refs.py`(臂外全部引用:门的参照、adapter 基础 spec 及其 price_meta/universe、引擎队列助手、读数装置的 news_stats 与 X 基线;清单从这些设备自己的字面常量解析出来,解析不到即失败)。
3. 红测 `test_mr_preflight.sh`(沙箱根,大文件只硬链接只读,变异一律用新副本):基线先绿,再 C1 = 18:35Z 的形状(副本只在臂根)⇒ FAIL,C2 字节改动 ⇒ FAIL,C3/C4 臂内静态输入改动/缺失 ⇒ FAIL,R1–R4 臂外引用缺失/sha 变/解析不到 ⇒ FAIL。收据 `receipts/TEST_MR_PREFLIGHT_2026-09-27.out`:10/10 与预期一致。

**同时改动(均在任何序列存在之前):**
- 顺序:按 lead 批准的优先级,A3 推迟到 A1 判词之后(`ORDER.txt` / `PREP_LIST.txt` 去掉 A3;引擎队列加共享优先级约定)。这是 fresh 18:14Z 留在工作区未提交的改动,fresh2 原样采用。
- 执行者(§10-f):红控 + 引擎复现控制改由 `mr_engine_queue.sh` 在 RED_m0 / A0_m0 四个序列齐备时立即执行 `mr_read.py red`,不过 ⇒ 队列 STOP(判据 §0:全族停止);队列结束时执行 `mr_read.py family`。引擎队列的 STOP 同时写入 `logs/master.log`(登记的日志)。
- `mr_read.py` family 模式原来要求 A1 **与 A3** 序列齐全,否则 INCOMPLETE;A3 推迟后它永远出不了 A1 的判词。改为只要求 A0 与 A1 齐全,A3 齐全时照读(判据 §2:两臂各自独立判定)。未改任何阈值或统计量。
- 复用:A0_m0 的 King、第二次训练(gate/A0_m0_dup)与 legs 沿用第一次运行的产物;装置门 G1/G2/G3 在数组逐位上核对它们(`mr_gates.arrays_equal`:文件集、dtype、shape、字节),容器 sha 另报。
