> **创建:** 2026-09-25 05:0xZ | **Session:** b9646a9e(dlarch) | **状态:** 装置就绪, **平价门未过**(阻塞于 pod2 /workspace 配额 128 MiB) | **作废条件:** `dlarch_chain_run.py` / `dlarch_derive_chain.py` 的 sha 改变; 或上游 `news2_combo.py` / `news2_adapter_specs.py` 被钉的 sha 改变; 或 `/dev/shm/news2_2026-09-23` 被回收(见 §6)

# dlarch combo→engine 链 — 给 fresh 的使用说明

**用途**: 第 1 步融合层候选臂需要在**同一批 F10 抽样成员**上跑到书层。本链把「一个 F10 种子的 OOF」跑成「引擎 base 格的书」,与在役 NC 的组合→引擎路径**同码**(上游文件只经具名替换,不改写)。判据见 `docs/DECISION_RULE_step1_fusion_family_gate_2026-09-25.md`(lead 写,我不改)。

## 1. 现在能用到什么程度(先看这节, 别照 §3 就跑)

| 件 | 状态 |
|---|---|
| 派生装置 `dlarch_derive_chain.py` | 已跑通, sha 钉 + 具名替换表 + 出现次数断言 + 归档 unified diff |
| 链运行器 `dlarch_chain_run.py` | 代码就绪 |
| **平价门(必须先过)** | **未过**。收据 sha: **无**。原因见 §5 |
| T0 8 个种子的 F10 产物 | **未齐**(同一配额阻塞); 齐一个我按 sha 单独通知你 |

**在平价门出收据之前, 本链产出的任何书都不作数** —— 它只证明「我能跑」,没证明「我跑的是在役那条链」。

## 2. 布局

```
/workspace/dlarch_2026-09-24/
  chain/
    devices/                 派生件 + 被钉的兄弟模块(符号链接)
      news2_combo.py         ← 派生(2 处具名替换)
      news2_adapter_specs.py ← 派生(4 处具名替换)
      continuous_combo.py    → 符号链接到上游, sha 钉
      combo_target.py        → 同上(它自己还会断言自己的 sha)
      book_universe.py       → 同上
      *.diff                 每个派生件的 unified diff(归档)
    parity/                  平价门的运行根
    s<N>/                    每个家族成员一个运行根
      configs/RUN_CONFIG_DLARCH_T0_s<N>.json
      logs/{combo,spec,adapter,engine}.log
      runs/                  引擎产物
```

`runs/` 在 `/workspace` 下(经 `paths.pod_root`)。**本链任何一步都不往 `/dev/shm` 写**。

## 3. 入口命令(逐字)

派生(只需做一次;重复跑会重新校验所有 sha):

```
ssh pod2 "cd /workspace/dlarch_2026-09-24 && env -i PATH=/usr/bin:/bin HOME=/root \
  /workspace/venv/bin/python -B devices/dlarch_derive_chain.py PATH,HOME,LC_CTYPE \
  /workspace/dlarch_2026-09-24/chain/devices"
```

平价门:

```
ssh pod2 "cd /workspace/dlarch_2026-09-24 && env -i PATH=/usr/bin:/bin HOME=/root \
  /workspace/venv/bin/python -B dlarch_chain_run.py PATH,HOME,LC_CTYPE \
  /workspace/dlarch_2026-09-24/out_chain --parity"
```

一个家族成员(组合层, 不跑引擎):

```
... dlarch_chain_run.py PATH,HOME,LC_CTYPE <outdir> --seed <N>
```

加引擎格:

```
... dlarch_chain_run.py PATH,HOME,LC_CTYPE <outdir> --seed <N> --engine
```

第一个位置参数是 **env 白名单**(逗号分隔), 装置会断言白名单外没有多余 env —— 这是复现纪律 E-0826-D 的那条断言, 不是可省参数。

## 4. 每个成员你会拿到什么

`--engine` 跑完后 outdir 下的记录件含:

- `mode`(`PARITY_GATE` / `FAMILY_MEMBER`)、`seed`、`root`
- 每步 rc 与日志路径
- `mem_gate_at_start` / `mem_gate_before_engine` / `mem_gate_after_engine` —— 三个数(`memory.max`、`anon`、`shmem`),lead 要求每个引擎格都带(cgroup v2 可用内存 = max − anon − shmem)
- `base_config` + `base_config_sha256`
- 引擎目标件的路径与 sha

我按种子通知你的四件:产物路径、OOF sha、`TRAIN_RECEIPT` sha、完成折数,外加该格引擎状态。

## 5. 为什么平价门还没过(别当成"还没排到")

平价门要求组合层输出**逐位复现**归档的 `combo_s42/*.npz`。它跑过两次:

1. 第一次被 cgroup OOM 杀(`oom_kill` 计数 +1,无 traceback),产物删掉了。
2. 第二次(09-25 04:31:14Z)打完 `build root` 就死,**`combo.log` 根本没建出来**;`oom_kill` 计数**没变**(仍 9),日志 107 字节、0 个 NUL、结尾干净。⇒ 不是内存,是 **/workspace 配额**。

配额实测:`dd bs=1M count=512` 实际只写进 **134,217,728 字节(恰好 128 MiB)** 后报 `Disk quota exceeded`。32 MiB 的探针能过 —— 所以**"探针能写"不等于"够用"**,探针必须按真实需要的量级来量。

## 6. 一条你必须知道的外部依赖

链读两样东西在**别人的 `/dev/shm` 树**里:

- `BASE_CFG = /dev/shm/news2_2026-09-23/configs/RUN_CONFIG_NEWS2_s42_2026-09-23.json`
- 平价门的参照 F10 OOF: `/dev/shm/news2_2026-09-23/work/f10_s42`

`/dev/shm` 现在 27G/28G。**如果 `news2_2026-09-23` 被回收, 平价门就失去参照, 本链的基准配置也要重新定位。** 回收那棵树之前请先跟我说 —— 这不是"我占着它",是"我的判决装置的参照在里面"。

## 7. 具名限定(引用本链的书时必须一并引用)

1. T0 成员是**掩码 `WL` 重训**的 F10,与在役 F10 不完全相同;各成员对在役 F10 的逐年秩相关由 `dlarch_leg_readout.py` 必报。
2. 族只覆盖 **F10 抽样**,不覆盖 King 抽样。
3. 多种子**只作测量**,禁生产集成;部署一律用预先声明的种子 42。
4. 缺成员 ⇒ 该臂 n 相应减少并具名;**n < 8 不出判词**(`NO_VERDICT`)。
