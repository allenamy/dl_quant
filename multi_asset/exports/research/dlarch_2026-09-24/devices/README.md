> **创建:** 2026-09-25 09:3xZ | **Session:** b9646a9e(dlarch) | **状态:** 在用 | **作废条件:** 下表任一环境字段改变(见 §1)

# dlarch devices — 使用前必读的两条限定

## 1. ★ 逐位可复现性是**测出来的,不是配出来的**

训练器 `dlarch_train_f10.py` 只设 `torch.manual_seed` / `np.random.seed`。它**没有**设:

- `torch.backends.cudnn.deterministic`(实测为 `False`)
- `torch.use_deterministic_algorithms(...)`
- TF32 控制(实测 `matmul.allow_tf32=False`,`cudnn.allow_tf32=True`)

参照配方 `news2_train_f10.py` 同样如此。所以 G1 / G1 delta / G1b、以及 2 路并行的确定性结论,**全部是在下面这个环境上观测到的经验事实**:

| 字段 | 值 |
|---|---|
| python | 3.11.10(`sys.prefix=/workspace/venv`) |
| torch | 2.11.0+cu128 |
| CUDA | 12.8 |
| cuDNN | 91900 |
| GPU | NVIDIA RTX PRO 4500 Blackwell,capability (12, 0) |
| driver | 580.159.03 |

**任一字段改变 ⇒ 先重跑 `probe_crosslevel.sh`(跨负载逐位检查)与 `probe_determinism.sh`(同负载 run-to-run),过了才能继续并行训练,也才能继续引用既有的逐位同一性结论。** 每个种子的产物旁有 `ENVIRONMENT.json` 记录当时的实测值,由 `dlarch_run_T0_lane.sh` 写入(不经训练器,所以不动它的 sha)。

受据:`docs/receipts/dlarch_gpu_parallel_determinism_2026-09-25.log`(含一段我自己的更正)。

## 2. ★ 交给别人的引用键必须是**内容 sha**

`TRAIN_RECEIPT.json` 的**文件 sha 不是**内容 sha:它记了 `elapsed_seconds` 与 `curve[*].seconds`,所以同一折重跑、预测逐位相同时,它也会变。实测 `(T0, s42, 202506)`:

- **相同**:`scores.npz` sha、`model.pt` sha、`train_loss`、`alpha`、`a_final`、`scored_pairs`
- **不同**:`elapsed_seconds` 135.33 → 133.93 ⇒ 折收据 sha `2a47f56d`→`524eafd0` ⇒ 训练收据 sha `21f94f90`→`178f2cbe`

这条已经造成过一次实际损失:我把旧的收据 sha 当引用键给了 fresh,重跑后它失效。

**正确做法**:引用 `dlarch_content_receipt.py` 产出的 `CONTENT_RECEIPT.json`:

- 整个种子 → `content_sha256`(只哈希内容量;计时/GPU 名/绝对路径都在**不参与哈希**的 `env` 段)
- 只要预测 → `content.oof_sha256`(= `F10_OOF.npz` 的 sha,跨重跑稳定)

**消息里必须写明是"内容 sha"还是"收据文件 sha"。** 前者重跑仍成立,后者一重跑就失效。

### 键稳定性分层(引用前先想清楚要哪一层)

| 键 | 什么时候会变 | 用途 |
|---|---|---|
| `content.oof_arrays.arrays_sha256` | **只在数组变时** | **预测的主键**,最稳;由数组字节算出,不依赖容器 schema |
| `content_sha256` | 数组变 **或** 本装置的 content 字段表变 | 整套产物同一性;**比较前必须先比 `content_schema_version`** |
| `content.oof_sha256`(容器 sha) | 数组变,**或** OOF 的 npz schema 变 | 第三重旁证;schema 变会**静默**移动它,故装置断言键恰为 `(E_ts, P, symbols)` |
| `TRAIN_RECEIPT.json` 文件 sha | **一重跑就变**(记了计时) | **永不可作跨运行令牌** |

为什么容器 sha 不够(fresh 2026-09-25 指出):`.npz` 文件 sha 不是数组同一性,本项目已有两条反例(其中一例是 npz 内夹了逐次变化的 `model_sha256`,容器 sha 每跑都变而预测矩阵逐位相同)。当前 OOF 的键恰好只有 `E_ts`/`P`/`symbols`,所以容器 sha 今天可用 —— 但那依赖 schema 不变,且失效**不报错**。红控制:给副本的 OOF 加一个 `written_utc`,装置抛 `OOF schema changed`。

**`content_sha256` 自己也有这个毛病**(加字段就会变),所以有 `CONTENT_SCHEMA_VERSION`:v1 无 `oof_arrays`,v2 有。自证:两版之间 `arrays_sha256` 完全不变而 `content_sha256` 变了 —— 哪个稳定由读数展示,不靠声明。

## 3. 进程计数:不要用 `pgrep -f`

本目录的装置一律用:

- 「几个进程在用 GPU」→ `nvidia-smi --query-compute-apps=pid,used_memory`(问设备,不问文本)
- 「几个某脚本的进程」→ `ps -eo pid,pgid,args` 过滤到**解释器调用行**
- 「是不是我的」→ `os.getpgid(0)` 按 **PGID** 归组,配置路径只作**标签**

理由(两次实测):`pgrep -f 'dlarch_train_f10.py --arm'` 数到 **0**(驱动器把 `--env-whitelist` 放在 `--arm` 前面,**参数顺序**不匹配);`pgrep -fc` 写在 `ssh host "..."` 里会**自匹配**,报 3/4 而真值 2。

### 3b. 长跑脚本**无条件自报 PGID**(news2 2026-09-25 提出,本目录采纳)

`dlarch_run_T0_lane.sh` 启动时把自己的 pgid 写进 `$EXP/lane_<lane>.pgid`(pgid/pid/lane/owner/起始时间/argv/装置路径)。两个已实测的失败模式:

1. **归属无法证明**。我报过一个「来源不明的第三个 `bt_launch` 组」(pgid 3062350);news2 说那大概是他们的 —— 手工 `ssh` 起的、没过他们的包装器,于是**他们自己也拿不出记录证明**。不可解的原因是**没有记录**,不是没有归属。
2. **信号目标**。唯一安全的 kill 目标是**我自己记下来的** pgid。另见 news2 的实测:`ssh host 'cmd'` 不分配 pty,**本地 kill 掉 ssh 驱动,远端命令仍在跑** —— 你以为停了,于是改输入或报告「已停止」,而远端还在写产物、还在吃共享主机的配额。所以「停掉」必须是在 pod2 上对**记录下来的 pgid** 发信号,并在发信号前确认那条命令行是我自己的装置路径。

在跑的那两条 lane 早于这个代码块,其 `.pgid` 已按 `/proc/<pid>/environ` 的实测值**事后补录**(文件里写明是补录)。**不改远端在跑的那份脚本** —— bash 按字节偏移边跑边读,原地改可能让正在执行的进程错位。

## 4. 已交付的树只读

任何重跑/探针在副本目录 `probe_<ts>/` 里做,比对时再读交付树(lead 裁定 2026-09-25)。若交付件仍被改动,**不要回改回去** —— 在交付目录旁留具名注记即可(范例:`T3/T0/f10_s42/NOTE_receipt_sha_changed_2026-09-25.md`)。

## 5. 主要装置

| 装置 | 作用 |
|---|---|
| `dlarch_train_f10.py` | T0/T3 训练器(派生自 `news2_train_f10.py`,REF_SHA 运行时断言) |
| `dlarch_run_T0_lane.sh` | **一条** lane;两条可并行,靠 `mkdir` 原子占坑取种子(工作窃取) |
| `dlarch_chain_run.py` | combo→engine 链;`--parity` / `--reference` / `--seed`;内含引擎运行门 |
| `dlarch_cell_retain.py` | 引擎格四条前置 + 小序列 + 按裁定腾空间 |
| `dlarch_identity_compare.py` | 两个运行逐位对比(差异必须定位定量) |
| `dlarch_cross_chain_check.py` | 两条**独立链**在同一对象上的互证 |
| `dlarch_readback_folds.py` | 折工件回读门(重算收据自记的内容统计量) |
| `dlarch_content_receipt.py` | 内容 sha 旁挂件(§2) |
| `dlarch_pairwise_constants.py` | 成对常量普查(declared / undeclared) |
| `dlarch_engine_gate_selftest.py` | 引擎门计数自测(PGID vs argv vs PID 三法并列) |
| `dlarch_safe_io.py` | 写完读回比对才取 sha(E-0925-A) |
| `probe_determinism.sh` / `probe_crosslevel.sh` | 并行确定性探针(§1) |

## 6. 具名记录:我做错顺序的一次(2026-09-25)

**先开了第二路并行训练,才算配额账。** lead 的上一条裁定是「GO 2 路」,我把它当作可执行就在 `09:16Z` 开了第二路;随后 lead 要求"开第二路之前先估算剩余写入量"。算完结论是**放得下**(需要约 780 MB,实测余量 `09:34:44Z` 1600 MiB),但**顺序错了**:资源账属于动手之前,不是动手之后。

同一次里还有两处我的措辞/读数问题,一并记在这里:

- 我报的「盘 947M」是**我自己的占用**,被读成"剩余余量"。此后报空间一律分开写:**占用** X / **实测余量** Y(带时间戳与探针量级)。
- 我先前说「每格净增约 11 MB」是错的:小序列 11 MB,但**格目录**留存后 102 MB(多出的 85 MB 是 `work/combo_s*` 58 + `targets/*.npz` 28)。已改为自动腾掉可再生部分 ⇒ 每格回到 17 MB。

教训与 [[re_measure_a_blocker_before_reporting_it]] 同族:**凡"我要动手了"的动作,前置条件必须在动手前测一次**,不能靠上一条裁定的余温。
