> **创建:** 2026-09-27 13:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 装置验收收据 | **作废条件:** d10_deploy_verify_chain.py 或 common/pod2_deploy_verify.sh 改动

# 十月链部署同一性检查(lead 事项 A)的验收

装置:`news2_2026-09-23/devices/d10_deploy_verify_chain.py`(提交 61432f487)。三方比较不重写,每个 pod2 目录都交给 fresh2 的 `common/pod2_deploy_verify.sh` 判;本装置只决定「哪些文件必须在、在哪」,读该工具的逐文件行。

- 核对清单:runbook 链 + Python import 闭包(与契约测试同一派生)+ 链内 shell 脚本经自身变量指向的共享 pod2 根(nc 根、news2 根、devices_arm)里的代码,及其同目录 import。
- 不上 pod2 的 7 个(有理由,写在装置里):四个历史拉取驱动、Mac 上的归档作业、Mac 上的契约测试、1d 的模板驱动 d10_reaudit_jan_to_aug_pod2.sh(它把 EXP 写死为 09-25 的部署目录;装置首次派生时以 UNMAPPED_ROOT 报红而发现)。
- 他人装置(dlarch F10、king_oct、nc_contract 研究快照)由各 owner 在自己目录起跑时核对,列在收据里,不在本检查的判定内。
- selftest 15/15(合成工具输出上的判定逻辑)。

| 收据 | 做了什么 | 结果 |
|---|---|---|
| C0_green_sync_20260927T132604Z.json | 从 HEAD `git archive` 同步到新的 /dev/shm 控制目录,然后核对 | PASS(21 个装置、4 个 common、7 个外部文件全 OK;news2 根的 nc_contract.py 不在那里,运行时从 PATCH_RECEIPT 钉住的生产者树 import,记为 ABSENT_IMPORT_RESOLVED_ELSEWHERE) |
| C0_pre_{missing,byte,stray}_*.json | 三个红控各自的基线(先绿) | 3/3 PASS |
| R_missing_* | 删掉 pod2 上的 p9_pull_verdict.py | 红:EXP_DEVICE p9_pull_verdict.py MISSING |
| R_byte_* | d10_build_fund_state.py 末尾加 1 字节 | 红:目录不 PASS + 该文件 MISMATCH |
| R_stray_* | devices/ 里放一份过期的 durable_write.py | 红:目录不 PASS + EXP_COMMON durable_write.py devices=MISMATCH(devices 里的副本先被 import) |

控制目录用完已删除(只删本次新建的 4 个 /dev/shm/news2_dvc_ctl_*)。

共享根里与链无关的文件不判,只记录在收据里:nc 根 bad=2(nc_gate_g1.py 不符,TEST_NC_CONTRACT.json 无源)、devices_arm bad=1、news2 根 bad=16(09-23 会话的旧文件)。

用法:每次 pod2 起跑前 `python3 -B d10_deploy_verify_chain.py --exp <新目录> --out <新收据> --sync`(只同步进新目录;已有 devices/ 或 common/ 的目录拒绝同步,只核对),末行 `CHAIN_DEPLOY_VERIFY PASS=True` 且 rc 0 才起跑,收据路径写进该步收据。
