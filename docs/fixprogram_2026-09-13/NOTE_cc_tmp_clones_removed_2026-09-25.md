> **创建:** 2026-09-25 03:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 记录 | **作废条件:** 无

# 注:fixprogram 各文档里引用的 `~/cc_tmp/fx_exec` 等临时克隆已于 2026-09-25 删除

用户 09-25 裁定「清理旧临时副本」(研究仓在 iCloud 桌面,磁盘 97% 满导致 git pack 被逐出)。本目录下约 217 份 FX_EXEC 文档/收据与 60 份 FX_PROD 文档引用的路径 `~/cc_tmp/fx_exec` 是**当时跑测试的临时克隆**;收据本身都已提交在研究仓,结论不受影响。

| 已删目录 | 删前核实 | 复现方法 |
|---|---|---|
| `~/cc_tmp/fx_exec` | HEAD `4f9d439` 是实盘仓 `~/dl_quant_live` origin/main 的祖先;无已跟踪改动;未跟踪的只有 state 拷贝 | `git clone ~/dl_quant_live <新目录> && git checkout 4f9d439`,state 按当时手册从实盘只读复制 |
| `~/cc_tmp/lead_publish_20260923` | HEAD `b66257b` 在 origin/main;已跟踪改动只在 state/ | 同上,checkout `b66257b` |
| `~/cc_tmp/fx_exec2_state_20260913T1427Z`、`~/cc_tmp/fx_w6c_state_20260916` | 实盘 state 的测试拷贝,09-17 后无写入 | 从实盘只读重新复制 |

- 两个克隆的 `state/acceptance/` 电池日志已**逐字节**归档到 `~/cc_tmp/battery_logs_archive/{fx_exec_4f9d439,lead_publish_b66257b}/`(`diff -rq` 相同)。
- **未删**:`~/cc_tmp/fx_prod`(忽略目录 `work/` 1.8 GB 未证实可删;其分支 `fix/train-serve-parity-2026-09-13` 在任何远端都没有)、`~/cc_tmp/codex_release_20260921`(本地分支提交在远端找不到)。
