> **创建:** 2026-09-29 02:52 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final | **作废条件:** 备份后原文件继续变化、网络卷被删除/换错、本机解密密钥丢失、归档哈希不符；恢复环境变化后须重验数值平价

# Pod暂停前保全与恢复入口

用户已要求暂停研究并准备停Pod。本件只做数据与环境保全，没有停止Pod、停止本机实盘、恢复交易、调用交易所或启动新实验。研究交接仍以 [HANDOFF_acting_lead_2026-09-29.md](HANDOFF_acting_lead_2026-09-29.md) 为准，heartbeat保持PAUSED。

**03:08:19Z加密后的最终门PASS：用户可以暂停Pod，须保留原网络卷和本机密钥。** 02:57:04Z文件完整性门已过，随后发现FUSE忽略chmod，已完成两份归档AES-256-GCM加密、完整解密认证和原SHA复核，并移除本次明文tar。24项解包检查、435条跨根链接覆盖与原生find交叉核、7项归档控制及4项加密控制全部通过；GPU计算进程0。最终原有文件变化/缺失均0，额外生成的87个可再生字节码缓存亦逐位保全。最终状态以`READY_TO_STOP.json`和`FINAL_SEAL.json`为准；`*_pre_encryption.json`只保留早先完整性证据，不能作最终停机凭证。

## 1. 保全位置和范围

**持久目录：`/workspace/pod_preservation_20260929T024300Z/`。** 目录标签是预选名称；实际启动时间为02:42:13Z，两份主归档完成校验时间为02:46:38Z。

实际挂载核实：`/workspace`为`fuse`网络卷，源为`mfs#eur-is-1.runpod.net:9421`；`/`为容器overlay，`/dev/shm`为tmpfs。不是根据路径名字推断持久性。网络卷ID存于该私有目录的`CONTAINER_ENV_ALLOWLIST.json`，重启/新建Pod须挂载同一卷。`df`显示的是共享后端容量，不能当800GB用户额度；本次先做256MiB写入、fsync、读回SHA验证，随后真实写完并校验全部归档。

原网络卷盘点604,269,326,336字节；主备份新增40,421,191,680字节，另外有少量清单及恢复抽测文件。原文件全部保留，没有为备份清理来源数据，也没有重复复制原本就在`/workspace`的大数据集。

| 归档 | 范围 | 大小（字节） | 条目数 | SHA-256 |
|---|---|---:|---:|---|
| `rootfs.tar`（解密后） | 容器文件系统的研究文件、`/root`环境/模型、`/tmp`旧NEW组合、`/usr`/`/opt`运行库及配置 | 17,629,644,800 | 87,681 | `8c6357dcfaa8b0596bcee31ec58eb587208b45f9fa2e625b8dec1acb77864676` |
| `shm.tar`（解密后） | `/dev/shm`全树，包括研究输入、模型、预测、现金回放、源码、日志与链接 | 22,791,546,880 | 48,159 | `fbd987d1070a53692995a40168280775f20475a4e08bd568a26fa38859333a22` |

网络盘最终保留的是`rootfs.tar.aes256gcm`与`shm.tar.aes256gcm`；密文SHA在`ENCRYPTION_VERIFIED.json`和`SHA256SUMS.txt`。两份分别以随机nonce进行AES-256-GCM流式加密，完整解密并校验原归档SHA后才清理**本次新建的明文tar**，不删除原研究文件。未经认证的解密输出不会发布为完成文件。

- `rootfs.tar.aes256gcm`：17,629,644,886字节；SHA `301b3dbcaff0286f9c8d272e233920223f0cd0603cbf76ce151f049c6d1738ff`。
- `shm.tar.aes256gcm`：22,791,546,966字节；SHA `ba8b96bd40da187d3e90d4a77d1c2d63da99c5684c9c7b396d60b6e0c1df4a1b`。

两份归档均逐成员读回，对每个普通文件核SHA，对链接核目标、对元数据核权限/所有者/大小/类型，并检查捕获期间及捕获后源文件有无变化。未把符号链接展开成另一份数据；硬链接关系保留。现成/tmpfs迁移目录`.../acting_lead_20260927/tmpfs_archive_20260927T2230Z/`仍在网络卷，原链接另有清单。

`rootfs_excluded.json`逐项列出61个排除入口：其它挂载、`/proc`/`/sys`/`/dev`/`/run`、系统日志/缓存、Jupyter运行时目录、运行时特殊文件等。GPU驱动的宿主机挂载由新Pod提供，不能拿旧文件覆盖。它是恢复文件的归档，**不是可启动镜像，不保存进程RAM、ACL或文件capabilities**。

环境盘点额外生成的17个Python字节码缓存（234,316字节）另存`source_additions/`，逐文件SHA写入`SOURCE_ADDITIONS.json`；加密工具导入库产生的另70个字节码缓存保存于`source_additions_after_crypto/`，见`SOURCE_POST_ENCRYPTION_SCAN.json`。主归档后原有普通文件/链接没有变化。这87个文件不是模型或研究结果，未伪装成主归档原有内容。

**权限更正：** 虽设置umask077、目录0700及文件0600，这块FUSE卷实际仍返回0777/0666；额外chmod正控也确认不生效。不能把设置命令当权限生效。本件早版的0700/0600断言撤回，因此对两份大归档实施认证加密。全容器归档可能包含原容器SSH/工具配置，**不得公开原始归档或密钥**。Git中只入库保全代码、脱敏收据、哈希和本说明。

**唯一解密密钥仅在本机：`/Users/haosiyu/.codex/pod_backup_keys/pod_preservation_20260929T024300Z.key`（32字节，实际权限0600；父目录0700）。** 没有写入Pod、网络卷、Git、命令参数或日志。不要删除该文件；丢失密钥就不能恢复加密归档。密钥通过SSH标准输入传输，仅在远端加解密进程内存短暂使用。

## 2. 运行环境与任务状态

| 实际Python路径 | Python | NumPy | LightGBM | Torch |
|---|---|---|---|---|
| `/usr/bin/python3.11` | 3.11.10 | 2.4.6 | 4.7.0 | 2.4.1+cu124 |
| `/workspace/venv/bin/python` | 3.11.10 | 2.4.6 | 4.7.0 | 2.11.0+cu128 |
| `/root/news_2026-09-23_env/venv314/bin/python` | 3.14.4 | 2.5.2 | 4.7.0 | 未安装 |

完整包版本、OS和GPU/驱动信息在`ENVIRONMENT.json`。GPU为RTX PRO4500 Blackwell，驱动580.159.03；保全开始时无GPU计算进程。训练时OMP/OpenBLAS/CPU特性设置仍须读取**各实验自己的运行收据**，不能把此次SSH环境中未设置的值冒充当时训练值。

本期训练与回放已终态，没有需要保存优化器内存的在飞训练。Pod仍有两组9月11日旧采集器：两个包装器睡眠、两个采集器进程处于T（stopped）；最后落盘进展均是09-11 16:24Z。其原始响应、进展、输出在网络卷上，源码对完成行显式flush。`LEGACY_PAUSED_COLLECTORS.json`保存状态说明。

**这两个旧采集器没有已验收的续跑入口，不能把进程存在解释成当前研究在跑，也不能宣称其未落盘RAM已保存。** 它们的脚本用`open('x')`创建输出，重新启动会冲突；不要SIGCONT、按名字kill、直接重跑或覆写原目录。主研究员若仍需要这些旧任务，先按已有逐请求原件核对缺项，再在新目录补齐。此次没有唤醒它们或发出交易所请求。

本机S3采集与生产服务不在Pod，未停；研究heartbeat已暂停，不会因Pod恢复而自动推进交易/发布。

## 3. 重启后的恢复顺序

1. **保留并挂载同一网络卷。** 可以由用户暂停Pod；不要删除网络卷，不要把“新Pod的空`/workspace`”当原卷。官方说明：[RunPod存储类型](https://docs.runpod.io/pods/storage/types)。重启后SSH地址/端口可能变化，先更新`pod2`连接。
2. 先读取本件、研究交接和`READY_TO_STOP.json`。确认原目录存在，核实网络卷身份。不要启动训练、采集器或任何生产服务。
3. 先在Pod核密文和元数据的校验清单；解密器需要Python3和`cryptography`（本次实际验证Python3.11.10、cryptography3.4.8）。不要把密钥复制到网络卷：

   ```bash
   cd /workspace/pod_preservation_20260929T024300Z
   sha256sum -c SHA256SUMS.txt
   ```

4. 哈希全过后逐份解密，临时明文放新Pod的内存盘，避免把含私有配置的完整明文tar重新留在FUSE上。先确认`/dev/shm`可用空间大于待解密文件大小（两份各约17.63GB、22.79GB）；**一次只解一份**。在本机运行以下命令；密钥经SSH stdin发送，不出现在argv中：

   ```bash
   ssh pod2 python3 /workspace/pod_preservation_20260929T024300Z/encrypted_archives.py decrypt --input /workspace/pod_preservation_20260929T024300Z/rootfs.tar.aes256gcm --output /dev/shm/rootfs_restore.tar < /Users/haosiyu/.codex/pod_backup_keys/pod_preservation_20260929T024300Z.key
   ```

   只有`authentication=PASS`且输出SHA与§1表相同才提取。先解到新建的**网络盘暂存目录**，不要覆盖`/`，也不要把旧SSH/密钥目录提取到FUSE。以下只是主要研究目录的选择式恢复示例，其余文件按清单补取；同名目录已存在时先核查，不能强删：

   ```bash
   mkdir -m 700 /workspace/pod_restore_20260929
   tar -xpf /dev/shm/rootfs_restore.tar -C /workspace/pod_restore_20260929 rootfs/tmp rootfs/root/news_2026-09-23_env rootfs/root/nc_2026-09-23_retained rootfs/root/m3c_2026-09-24
   rm /dev/shm/rootfs_restore.tar
   ```

   然后同样从本机stdin解密`shm.tar.aes256gcm`到`/dev/shm/shm_restore.tar`，核认证与SHA，执行`tar -xpf /dev/shm/shm_restore.tar -C /workspace/pod_restore_20260929`，最后删除本次临时明文`/dev/shm/shm_restore.tar`。不要在内存空间不足时强行同时保留两份明文。

5. 从暂存目录**逐路径**恢复需要的`/root`研究环境/模型和`/tmp`组合目录；原网络卷已有数据不覆盖。恢复`/dev/shm`有两种方式：足够内存时复制回tmpfs，或者让各顶层研究目录指向`/workspace/pod_restore_20260929/shm/`中的对应目录。后者可避免再次丢失内存盘产物，但路径映射必须记录。遇到新容器已有同名路径先比较，不能无条件覆盖。
6. 按`WORKSPACE_EXTERNAL_LINKS.json`和`LINK_COVERAGE.json`恢复跨根绝对链接；确认需要的文件`realpath`可达、SHA与清单一致。某些本来就断开的旧链接必须保留“原先已坏”的标签，不能在恢复时当成此次丢失或擅自从别的版本补一份。
7. **不要整棵覆盖`/etc`、`/usr`、SSH配置或宿主GPU驱动。** 先用同一容器模板/兼容系统恢复相同Python和CUDA运行条件，再按实际Python路径检查包版本与小规模推理平价。归档已保存运行文件不等于新模板数值平价已通过。
8. 主研究员明确接回后，从交接的失败/未决清单继续；先复核输入/装置SHA、跑低成本正负控和一格模型/组合平价，再恢复研究。没有新候选换装授权，D10未决/冷静期、GAP4/M3电池阻塞不因恢复Pod消失。

## 4. 校验凭证和局限

- `FILE_BACKUP_VERIFIED.json`：两份主归档逐成员完整验证。
- `rootfs_manifest.jsonl`、`shm_manifest.jsonl`：来源路径、逐文件SHA、链接与元数据；仅存在私有网络目录。
- `SOURCE_FINAL_SCAN.json`、`SOURCE_ADDITIONS.json`：捕获后的源集合与17个新增可再生缓存。
- `RESTORE_SMOKE.json`：24项实际解包检查、1,007,737,234字节，覆盖995MB原始特征面板以及代码/配置/链接；不声称启动了新容器或跑过推理。首个抽样方案限制20MB，未能在只有995MB单文件的`nc_retained`目录选出样本，在写出任何抽测文件前拒绝；随后按真实清单选最小文件重做并通过。
- `ENVIRONMENT.json`、`CONTAINER_ENV_ALLOWLIST.json`：只收集允许的环境身份/版本，不读取或输出密钥值。
- `WORKSPACE_EXTERNAL_LINKS.json`、`LINK_COVERAGE.json`：扫描1,102,142条网络卷条目，435个现存外部目标全部被备份覆盖，扫描错误0、漏保目标0；另用原生find取得链接集合交叉核查。
- `READY_TO_STOP.json`：完成加密后的最终汇总；`FINAL_SEAL.json`绑定全目录清单，供重启后先验身份。早先两个`*_pre_encryption.json`仅为历史完整性凭证。
- `ENCRYPTION_TESTS.json`、`ENCRYPTION_VERIFIED.json`：认证加密的正常解密、错误密钥拒绝、密文篡改拒绝、失败不发布明文等控制，以及两份真实大归档的完整解密SHA核验。
- 实际捕获器源码SHA `d1cb409275362e14a43401bd14a4ea38409be293fb3947edb2d076e7f5bb5851`，原件以`preserve_volatile_capture_source.py`保留。交付保全器`multi_asset/ops/pod_preservation/preserve_volatile.py`的SHA为`671aafaf93eacfba9150783a8fbf1a765239c5f1915c4013f295e8d1a7102c7e`：只追加“verify-only不得覆盖初次校验收据”的保护；归档字节不变。七个离线控制覆盖正常、内容篡改、来源变化/消失、无原路径恢复验证、截断拒绝、重验保留原收据。

本次是同一网络卷上的持久化保全，不是整个604GB网络卷的异地灾备。主归档另有独立`sha256sum`复核。本机已有的42份研究ZIP和Git交接继续保留，但不能冒充完整Pod副本。停止Pod不会停止网络卷本身的保留。
