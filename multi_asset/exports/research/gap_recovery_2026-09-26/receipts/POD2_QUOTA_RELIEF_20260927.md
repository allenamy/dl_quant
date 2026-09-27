> **创建:** 2026-09-27 06:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 删除前收据(删除结果与探针见本文末尾追加) | **作废条件:** 无

# pod2 /workspace 配额释放(第二次,2026-09-27)
- **起因**:news2 的干跑 D3 在 05:42Z 遇到 EDQUOT。06:10Z 的写前探针实测可写余量只有 0.5–1 GiB(df 显示 514T,不可信)。
- **候选调查**:只读助手查了 21 个路径,全部判为 SAFE:
  - 18 个属于 uplift_2026-09-11 的已关闭子目录;该计划 09-12 零录取收尾,见 `uplift_2026-09-11/CLOSEOUT_uplift_program_2026-09-12.md`。
  - 另 3 个:baseline_tables_2026-09-19/work/tamper(门测试用的故意篡改价格副本,测试收据已入库);uplift_r2_2026-09-13/T2(已判,见 RESULT_T2);uplift_r2_2026-09-13/T1/arms(T1 的 devices 与 receipts 保留)。
  - 引用检查:1,076 个提交的 diff、HEAD 文件、十月 runbook 与 READINESS、INFLIGHT 在跑作业,以及 pod 与 Mac 上近期脚本,都没有把这些路径当输入读取。
  - 故意保留:r5_oi(S1 设计点名要读 r5_oi/sig)、r5_basis、r6、r3k、r8_inbook/r12_smoothing/r15_structural(在役逐年表 r18 的上游)、fp2/fp3、axis_0919、baseline 的 price_full_*、fallback_cf、f8_*/dlw_*、review_scratch、codex_research,以及 09-24 之后改过的任何东西。
- **lead 在 pod2 的删除前复核**(06:3xZ):
  - 21 个路径都存在;09-24 之后被修改的文件数 0;硬链接(links > 1)的文件数 0;
  - /proc 扫描:没有任何进程的 cwd 或打开的 fd 落在这些路径内。
- **删除前 sha 清单**:`POD2_QUOTA_RELIEF_manifest_20260927.sha256`,4,661 行,sha256sum 退出码 0;清单文件自身 sha ac22a75c…,pod2 与本地相同;其中空文件哈希 1 条(是一个真实存在的空文件)。总计 26,176,662 KiB(约 25.0 GiB)。
- **已知副作用**:删掉 r12_intervene、r4_p1、r2_learned、r8b2、r2_horizon 后,其他已关闭的 uplift 目录里(r21、seatladder、r3_*、r10_*)会留下悬空的符号链接。这无害,在此写明。
- **未处理**:约 09-11 起有 6 个陈旧的等待循环(PID 220770、223786、225412、227856、228443、230774,父进程为 1),它们等的完成标记永远不会出现。没有动它们:按规定不在 pod2 上 kill 不属于自己记录的进程组。
