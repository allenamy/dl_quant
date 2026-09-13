> **创建:** 2026-09-13 ~08:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T4, task T4b) | **状态:** 按 `PREREG_T4b_v2main_feature_skew_2026-09-13.md`(sha256 `8db1a965…e0db`, 冻结 2026-09-13T08:27:41Z, 先于任何结果数字)出结果; 数字后未改阈/锚/臂; 未经 lead 复跑 | **作废条件:** `combo_stage.py`(b5c698f9…)、`f10_live_s42_np.npz`(351ae26b…)、`dlw_features.py`(29ae6a98…)或 `f8_higher_order_features.py`(2c500c7a…)换代; 冻结输入 `private/snapshot_live/` 或 `private/producer_snapshot_1789200000/` 被改
> **口径:** 实盘窗只比较目标文件与模型输入/分数, **不报任何收益或盈亏差值**(本窗无记账 y4s, 不从 5m 缓存重算)。表格由 `devices/t4b_tables.py` 从收据渲染到 `receipts/TABLES_T4b.md`。
> **零接触(VERIFIED):** `~/wide_shadow` 与 `~/dl_quant_live` 只读; 平价目录未写; 未写 P2/T5b/T6/T7 目录; 无 API; pod2 三次运行均 `nice -n 19` + `taskset -c 0-15`、线程 ≤16, 前后 `nvidia-smi` 0 % / 2 MiB, PID 333197/339489 `Tl`; Mac 回放 08:28:25–08:36:4xZ, 在生产者 08Z 窗(08:21:34Z combo 收尾)之后、12Z 窗之前; **停机守卫实际未生效**(§7-1); 未提交。

# RESULT · T4b · V2MAIN(F10)资金费列的训练/服务口径错配

## §0 一页

**历史书层主读数: NOT MEASURED —— 没有判决, 也没有分辨率。** A0/NW 书的 V2MAIN 来自年折预测, 产出它们的训练脚本(运行时版本 sha 93cc2cdf…, pod2 `/workspace/pod_f10_train_ext.py`)每折计算 mu/sd 后只存预测与结果, 随即 `del mdl`, 从未保存折模型或 mu/sd; pod2 上找不到任何年折检查点。存在的月度配方(FIX7 等)不是这两本书的 V2MAIN、不覆盖 2024、检查点也不带 mu/sd; 按任务书不作替代。

**两个疑似缺陷的结论(代码 + 数据):**
| 缺陷 | 是否作用于在役 V2MAIN 的打分输入 | 依据 |
|---|---|---|
| (a) 第 80 列 v0 训练 / v1 服务 | **是** | 在役模型的 mu/sd 按「存储列(v0, 含零)」重算在 171 列上全部相符(第 80 列相对差 2.4e-7 / 6.3e-8), 换成 v1 则差 153% / 143%; 实盘窗 6 锚每锚 4h 名 served/v0 = 2.000000、8h 名 = 1.000000 |
| (b) 面板历史行回填 0 | **否, 构造上到不了被打分锚** | 82 列只取被打分锚自己的面板行, 89 列不读面板; GATE ZH: 历史行填非零后, 被打分锚的 400 行 × 171 列与原样逐位相同且等于 served 记录值, 同时 95,200 个历史行的资金费格确实变了 |
| (附带) 服务端无 12h 新鲜度掩码 | **本窗惰性** | 09-05 16Z..09-13 08Z 每锚 400 名成员中陈旧 0、非 450 名 0 |

**实盘窗(描述; 快照起步 6 锚 09-12 12Z → 09-13 08Z; served 臂先逐位复现线上, 6/6 锚 king、`target_live`、`target_combo` 全 0.0):** 只把 V2MAIN 面板第 80 列换成 v0 的臂相对 served:

| 量(6 锚) | 中位 | 最大 / 最小 |
|---|---|---|
| V2MAIN 分数 Spearman | 0.9990 | 最小 0.9983 |
| 分数十分位变动(全部 / 4h / 1h / 8h) | 4.9% / 5.4% / 8.3% / 3.0% | 格数 2,400 / 1,854 / 12 / 534 |
| fc 链状态 归一化 L1 | 0.0049 | 0.0064 |
| **combo `target_live` 归一化 L1** | **0.0022** | **0.0029**(首锚 0.0004, 随状态累积) |
| combo `target_live` L∞ | 2.4e-4 | 2.55e-4 |
| combo 权重相关 | 0.99998 | 最小 0.99997 |
| 掩码席位 w3m | 两臂逐锚相同 | — |

**09-05 席位播种对 V2MAIN 链: 在席位权重与目标文件层 MEASURED(描述), 盈亏 NOT MEASURED。** 席位历史里仍有 876 行播种行(04-05 00Z .. 08-30 20Z), 它们是 v0 打分的 king 腿收益。把这 876 行换成同 booster、第 80 列 = v1 的重算值后: 掩码 king 席位 = V2MAIN 分数在 fc 链里的系数, 从 0.3695(中位)**+0.0078**(+0.0072…+0.0089); combo `target_live` 归一化 L1 中位 **0.0066**(最大 0.0090), 比上一行 V2MAIN 第 80 列本身的差(0.0022)大。

**41 锚链式窗没用**: 从 09-05 16Z 链式起步时 served 臂的 combo `target_live` 只在 1.125e-4 内复现线上(T4 收据), 不满足「先逐位」; 快照起步模式才满足, 所以实盘窗只有 6 锚。

## §1 事实表(任务书 Step 0 的四问)
| 问 | 答 | 收据 | 标签 |
|---|---|---|---|
| 82 + 89 列里谁读 `f_fund_ema` / `f_fund_now` | 只有 82 列的第 80、81 列(`dlw_features.py` L73、L90–93); 89 列 `build()`(L98–387)不加载面板、不读资金费列 | 代码 | VERIFIED |
| 是否读被打分锚以外的行 | 否: `pw_row[E_ts[i]]` 只取该锚自己的面板行; 89 列的锚间特征(J:drank)只用 82 列的非资金费秩列。数据复核 GATE ZH 通过 | 代码; `receipts/RECEIPT_T4b_zh_gate.json` | VERIFIED(代码 + 数据) |
| 在役 F10(`f10_live_s42_np.npz`)训练侧口径 | 第 80 列 = 原始费率 EMA(v0), 450 名以外的名为 0(占训练格 26.8%, 450 名内 0.12%); 第 81 列 = 原始末次费率(mu/sd 与存储列相符); 每个训练锚用自己的真实面板行, 训练里没有「历史行回填 0」 | `receipts/RECEIPT_T4b_facts_v2main.json` | VERIFIED(数据级识别) |
| A0 用的研究 V2MAIN 预测口径 | `f10_A0_s{42,2027}` ← `f8_ext/preds/f10_V2MAIN_s{42,2027}.npy`(sha 42666fc7… / 57c3625c…), 结果 json 记录 fea82 9bc111a4…、fea89 bebf2720… = 与在役模型同一份特征文件 ⇒ 训练与打分都是 v0(含零) | pod2 结果 json(sha 245a0faa… / f30b1554…) | VERIFIED(文件 sha 链) |
| mu/sd 从哪来 | 在役: `pod_f10_refit_ext.py` L89–93 训练行子样本(前 85% 锚、每 7 锚、每 3 行), torch 均值与 N−1 标准差 + 1e-6, 存入检查点, `pod_f10_np_export.py` L56 拷出; 研究年折: 运行时脚本 L272 每折同法计算, 未保存 | 代码; 识别收据 | VERIFIED |

服务侧(对照): `combo_stage.py` L134–146 末行 `f_fund_ema` = 生产者 EMA 状态(v1), 末行 `f_fund_now` = 账本末行原始费率, 历史行全 0, 两列都无新鲜度掩码。T1 已测该面板 4h 名 served/v1 = 1.0000、served/v0 = 2.0000; 本轮 6 锚按间隔分层再现 2.000000 / 1.000000。

## §2 历史书层: NOT MEASURED(清单)
| 物件 | 路径 / sha | 能否用于重打 A0/NW 的 V2MAIN 历史 |
|---|---|---|
| 年折预测 s42 / s2027 | `/workspace/f8_ext/preds/f10_V2MAIN_s42.npy` 42666fc7… / `_s2027.npy` 57c3625c… | 只有分数, 没有模型 |
| 年折训练脚本(运行时版本) | `/workspace/pod_f10_train_ext.py` sha 93cc2cdf…: L272 每折 mu/sd, L361 存预测, L362 存结果, L363 `del mdl`; 无 `torch.save` | 证明折模型未存 |
| 全史重训(在役) | `/workspace/f8_ext/models/f10_live_s42.pt` c983b3e3… / `_np.npz` 351ae26b…; `f10_live_s2027.pt` e8a3193c… / `_np.npz` 2901769b… | 见过全部历史, 用于历史 = 样本内, 不可 |
| FIX7 月度早停 s42 / s2027 | `/workspace/review_scratch/allweather_trackB/earlystop/FIX7{,_s2027}/shard*/models/mE1cX7*_2025MM..2026MM.pt`(各 20 个)、合并预测 `f10_V2MAIN_mE1cX7_s42.npy` 3cf0aa67…、`merge.json` 17606957…、训练脚本 55ee8382…(targets sha 31d043e8… = dlw_ext 谱系); 检查点为裸 state_dict(键 `a, f.0.*, f.3.*, f.6.*`), 无 mu/sd | 不是 A0/NW 书的 V2MAIN, 不覆盖 2024, 缺 mu/sd ⇒ 不替代 |
| 其它 | `review_scratch/dl_monthly_wf/models/mE1_/mE60_2025MM..2026MM.pt`、`/workspace/f8_v4/models/f10_live_s{42,2027}.pt` | 同上 |

**要测需要什么(陈述, 不提议)**: (i) 用同一年折配方重训并保存每折检查点与 mu/sd(需 GPU, 由 lead 与用户定), 先逐位或在 CPU 容差内复现现有 `f10_V2MAIN_s*.npy`, 再在 v1 输入上重打; 或 (ii) 另立预注册以 FIX7 书为对象(窗口只有 2025-01 起, 且须先按训练规则重建每折 mu/sd 并对各折 `preds_fold` 复现)。

## §3 门(`receipts/TABLES_T4b.md` T3)
| 门 | 读数 | 判 |
|---|---|---|
| SL | 从 T4 的 K0 文件按导出器公式重算 king 腿收益, 与 v3 bundle 列 10,176 行逐位相等 | PASS |
| CACHE | 冻结缓存与 09-12 08Z 快照自带缓存, 11,232 行逐位相等 | PASS |
| SA | 快照席位历史 950 行映射: 旧 bundle 前缀 793 + score 日志 157; 播种行 876 行的存值 876/876 同时等于 bundle 与 K0 重算 | PASS |
| **PCB** | served 臂 6/6 锚: king 权重 L∞ 0.0 且内容 sha 相同、king 目标文件 0.0、combo rc 0、`target_live` 0.0、`target_combo` 0.0、w3m 相同 | **PASS(逐位)** |
| PC-INJ | 一行装置喂回放自己的 EMA acc: king X/pred/权重、combo 171 列行、V2MAIN 分数、面板末行、f10/kc/fc 状态、`target_live`、`target_combo` 全部逐位同 served | PASS |
| ONE-PLACE | diff 恰一行; v2v0 的 king 段逐位同 served; combo 输入第 80 列之外逐位同、名集同; 第 80 列相同的 534 行(恰为 8h 名)分数逐位同; 面板末行 `f_fund_now` 逐位同 | PASS |
| ZH | 见 §0 表 | PASS |
| V1R | 馈入乘 8/iv 对 served 面板末行 2,400 格: 相对差中位 9.1e-8, 99.75% ≤ 1e-3; 例外 ERAUSDT 6 格(T4 已见, 生产者 07-09..08-14 错记间隔的残余) | PASS |

## §4 实盘窗: V2MAIN 第 80 列(v2v0 − served; 逐锚见 `TABLES_T4b.md` T5)
量纲同 §0 表。逐锚归一化 L1: 0.0004 → 0.0010 → 0.0019 → 0.0025 → 0.0029 → 0.0026, fc 链状态 0.0008 → 0.0059(α≈0.1 的 EMA 链 6 锚未到稳态)。w3m 两臂逐锚相同(该改动不碰席位)。读法边界: 6 锚、单一 regime、无收益数据 —— 这是「输入差 → 目标差」的量纲, 不是盈亏。作为参照(不同窗、不同起点, 只作量级): T4 的 king 第 80 列在 41 锚链式窗里 combo 归一化 L1 中位 0.0081。

## §5 09-05 席位播种对 V2MAIN 链(seatK1 − served; 逐锚见 T6)
| 量(6 锚) | 中位 | 范围 |
|---|---|---|
| 掩码 king 席位(= fc 链中 V2MAIN 分数系数) served | 0.3695 | 0.3668…0.3820 |
| 同上 seatK1 − served | **+0.0078** | +0.0072…+0.0089 |
| king 段目标 归一化 L1 | 0.0062 | 0.0018…0.0087 |
| combo `target_live` 归一化 L1 | **0.0066** | 0.0023…0.0090 |
| combo `target_live` L∞ | 1.5e-4 | 1.4e-4…2.6e-4 |
| king 段 X/pred | 6/6 锚逐位同 served | — |
机制: `combo_stage.py` L228–231 两条链都用 `w3m[0]` 乘各自的模型分数(kc 链乘 king, fc 链乘 V2MAIN), `w3m` 来自席位历史的末 900 行; 播种行按 v0 打分, 换成 v1 打分后席位上移约 0.008。**标签**: 席位与目标层 MEASURED(描述, 6 锚); 盈亏 NOT MEASURED。

## §6 修复会是什么(事实陈述, 不是提议)
1. **给 V2MAIN 第 80 列服务 v0**: `combo_stage.py` L141 的来源改为一份原始费率 EMA 状态(与 king 的修法共用), 其余不变; 需要生产者与 combo 链的改动、状态播种与平价测试, 需用户字。
2. **用 v1 重训 V2MAIN**: DL 特征构建器 FUND 列换成 `f_fund_ema_v1`, 重建 dlw 特征、重训并重过 V1–V4 门。
3. 本轮没有证据说明任何一种能提升书(历史主读数 NOT MEASURED; 实盘窗无收益)。缺陷 (b) 不需要修(不作用于打分)。若只修 king 或只修 V2MAIN, 另一个的同形错配仍在; 席位历史的 v0/v1 打分口径是第三个耦合处(§5)。

## §7 偏离预注册与事后处理
1. **停机守卫没有生效**: 守卫在 zsh 里写成 `for P in $PIDS`, zsh 不分词, `kill -0 "61206 61209 61210 61212"` 恒失败, 守卫在 08:28:33Z 报告「不需要」后退出, 而四个驱动一直跑到 08:36:4xZ。没有暴露: 生产者下一窗是 12:15Z。与 T4 的 `$ANCH` 分词失败同一类; 今后用数组或 `${=VAR}`, 并在守卫启动时打印它看到的 PID 个数。
2. 两个识别装置与 SL 在预注册之前运行(口径/血统/输入, 无结果数字), 已写入预注册 F3/F4/F9。
3. 预注册的锚列表在输入冻结(08:27:23Z)后填入, 随即冻结预注册(08:27:41Z); 两者之间没有任何结果数字。
4. 生产者快照 1789200000 自带的 SHA256SUMS.txt 是 16 位前缀 + 仓库相对路径(不是 shasum 可校验格式), 本轮按前缀逐文件核对后另写全长 sha。
5. ONE-PLACE 里「第 80 列相同」的 534 行恰为 8h 名(数据)。推断机制: V2MAIN 面板值进特征矩阵时转 float16, 8h 名 v0 与 v1 之间约 1e-6 的相对差在该精度下消失(T4 的 king 走 float32, 同样的名只有少数逐位相同)。

## §8 核实不了 / 边界
1. 历史书层效果(§2)。
2. 实盘窗盈亏: 本窗没有记账收益, 按纪律不从缓存重算。
3. 训练侧识别依赖在役模型 mu/sd 与存储文件相符; 研究年折的 mu/sd 从未保存, 其口径由记录的文件 sha 推出。
4. 实盘窗只有 6 锚, 链状态未到稳态; 更长的逐位窗需要更多锚收尾快照(快照作业在 09-12 20Z 后未再落盘)。
5. 训练集中 450 名以外的名为零(26.8% 的格)对 V2MAIN 质量的影响未测; 在役打分不经过这些名。

## §9 复跑(逐字)
pod2(cwd `/workspace/uplift_r2_2026-09-13/T4b`; 先 `scp ~/wide_shadow/shadow_bundle/config.json pod2:…/T4b/private_inputs/bundle_config.json`):
```
nice -n 19 taskset -c 0-15 env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=16 MKL_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 /workspace/venv/bin/python devices/t4b_facts_v2main.py PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,MKL_NUM_THREADS,OPENBLAS_NUM_THREADS
nice -n 19 taskset -c 0-15 env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=16 MKL_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 /workspace/venv/bin/python devices/t4b_seat_lr.py PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,MKL_NUM_THREADS,OPENBLAS_NUM_THREADS
```
Mac(cwd `…/T4b`; 生产者窗外):
```
cd devices && env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B mk_t4b_v2col80_device.py && cd ..
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_freeze_inputs.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4b_v0_feed_fwd.py PATH,HOME,LC_CTYPE,CPATH,LIBRARY_PATH,MANPATH,SDKROOT,__CF_USER_TEXT_ENCODING
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_seat_override.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
cd devices && for ARM in served v2inj v2v0 seatK1; do env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B t4b_replay_driver.py --arm $ARM --snapshot /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T4b/private/producer_snapshot_1789200000 1789214400 1789228800 1789243200 1789257600 1789272000 1789286400 > ../private/logs/replay_$ARM.log 2>&1 & done; wait; cd ..
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_zh_gate.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_live_judge.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4b_tables.py
```
(实际运行时四个臂各自在后台子壳启动, 日志同名。)

## §10 数字标签与校验和
§0–§5 数字 **VERIFIED**(本轮计算, 收据可复算); 转引项: T1 服务侧比值、T4 链式窗 combo 残差与 king 读数、09-05 播种记录(PREREG_deploy_seat_seed_v3)。装置、收据与表格 sha256 见 `SHA256SUMS.txt`。
