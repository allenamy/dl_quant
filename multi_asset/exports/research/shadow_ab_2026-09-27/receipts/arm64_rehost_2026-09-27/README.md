> **创建:** 2026-09-27 05:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 收据(新机 arm64 复验,GAP4 之前) | **作废条件:** 在役 combo_stage(12a76de8)或 combo_parity_replay.sh(7fa0881a)换版 ⇒ 须对新版重做(GAP4 预计会换)

# 影子 A/B 装置在 arm64 新机上的复验(GAP4 之前)

装置 = 仓库 `devices/`,14 个文件逐一对 `devices/SHA256SUMS` 核过(全 OK)。在役 combo_stage `12a76de8`、parity 回放 `7fa0881a`(`INSERVICE_SHA.txt`)。
主机、解释器版本与 sandbox-exec 见 `HOST.txt`。CPU 窗:04Z 锚的 [N+1:00, N+3:40],实际 05:03–05:05Z。

| 项 | 结果 | 收据 |
|---|---|---|
| `tests_shadow_ab.py` | 18/18,rc 0,生产者 venv(3.14.7)与 /usr/bin/python3(3.9.6)两个解释器都跑 | `TESTS_SUMMARY.txt`,`tests_*__*.log` |
| `tests_shadow_ab_read.py` | 4/4,rc 0,两个解释器 | 同上 |
| 真实锚干跑 09-26 20:00Z(1790452800) | rc 0,恒等控制 PASS:318/318 名,0 值不符,w3m 相同;三臂暖启动(无臂状态) | `REPLAY_1790452800.json` |
| 真实锚干跑 09-27 00:00Z(1790467200) | rc 0,恒等控制 PASS:319/319 名,0 值不符,w3m 相同;四臂 kc/fc 来源 `own`(接力成功) | `REPLAY_1790467200.json` |
| 定价 20Z(用 00Z 快照) | 追加 1 行,账本链 LEDGER_OK;00Z 为 NOT_YET(下一快照未到,预期) | `ledger_manual.jsonl` |
| **跨主机对照**(新 arm64 对旧 Intel 干跑 `../dryrun_2026-09-27/`) | 两锚各 15 个存档文件中,14 个(4 臂 × combo/kc/fc 的 npz、AB_META、HOOK)**sha 逐位相同**;只有 run.log 不同(沙箱路径与耗时两行)。20Z 账本行除 utc / 链字段外内容相同 | `CROSSHOST_COMPARE.txt` |
| agent 路径(launchd 同款 `env -i` 环境,START=END=1790452800) | 第 1 次:重放 rc 0 → 定价 → 写 DONE;第 2 次:`DONE (terminal)`。它的 20Z 状态文件与账本内容与手动干跑逐位相同 | `agent_path/` |

每锚耗时约 14 s(旧机约 41 s)。命令逐字见 `TRANSCRIPT.txt`。干跑产物在 `~/shadow_ab_dryrun_arm64`(不属于实验,可删)。
干跑账本里各臂收益数字没有读,也没有报;对照只比较了 sha 与「内容是否相等」。
