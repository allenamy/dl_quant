> **创建:** 2026-09-26 18:05Z | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 基建收据 | **作废条件:** 不作废

# pod2 /workspace 配额释放(2026-09-26 18:04Z)
- **触发**:dlarch 在 17:56Z 与 18:00Z 实测可写余量为 0(50/700/900 MB 探针都只写进 0 字节;df 看不出配额)。alloc 的红控格写到一半失败(4 个 0 字节文件,无读数)。
- **按 09-13 / 09-05 的先例**,只删已关闭研究线的运行产物,不碰固定资产(bookdepth_raw、lob_npz)和他人目录(codex_research 143G、review_scratch)。
  - `axis_0919/rehearsal_0917b`(5.25 GB):09-17/19 的数据轴演练,收据已入库 `axis_0919_2026-09-19/receipts/pod2/rehearsal_0917b/`;09-22 以来仓库无引用。
  - `cf3_2026-09-20/runs`(4.87 GB,14 个运行目录):CF3 三信号反事实的引擎输出,判词与收据已入库(RESULT / STY03_04_05 / STY_CLOSURE);09-22 以来仓库无引用。
- **引用扫描**:两处内部无符号链接;/workspace 深度 5 以内没有指向它们的链接;没有任何进程的 cwd 或打开的 fd 在其中。
- **删除前 sha 清单**:`POD2_QUOTA_RELIEF_manifest_20260926.sha256`,993 行,sha256sum 退出码 0,空文件哈希 0 条。
- **删除与探针**:rm 退出码 0;删除后写 2 GiB 探针(fsync),文件大小 2,147,483,648,完整写入(`POD2_QUOTA_RELIEF_run_20260926.log`)。
- **明确保留**:`baseline_tables_2026-09-19/work` 里有引擎在用的 `price_full_raw_x0918r.npy`;`axis_0919` 其余部分;全部 dlw_* / f8_* 特征缓存。
- **结构问题(报用户)**:配额反复触顶。大户是 bookdepth_raw 约 185G(固定资产)、codex_research 143G(另一研究员目录,不归本团队)、uplift_2026-09-11 49G。长期解法是扩容网络卷,或清理 codex_research,两者都由用户决定。
