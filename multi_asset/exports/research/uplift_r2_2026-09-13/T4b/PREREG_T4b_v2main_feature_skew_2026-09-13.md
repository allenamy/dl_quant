> **创建:** 2026-09-13 08:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T4, task T4b) | **状态:** 预注册 — 判据冻结先于任何结果数字(冻结 sha 与时刻见 `receipts/PREREG_FREEZE_sha.txt`; 各装置运行前从该文件读 sha 并断言) | **作废条件:** `combo_stage.py`(b5c698f9…)、`f10_live_s42_np.npz`(351ae26b…)或 `dlw_features.py`/`f8_higher_order_features.py` 换代; 研究 V2MAIN 预测 `f10_V2MAIN_s{42,2027}.npy` 被替换
> **上游:** `../T4/RESULT_T4_king_feature_skew_2026-09-13.md`(king 第 80 列, 判 NOT MATERIAL); T1 H2b 服务侧实测 `../T1/receipts/RECEIPT_T1_h2b_serve.json`
> **零接触:** `~/wide_shadow` 与 `~/dl_quant_live` 只读(生产者 venv 只当解释器); 无 API; pod2 只用 CPU(`nice -n 19`、`taskset -c 0-15`、线程 ≤16), 前后 `nvidia-smi` 0 % / 2 MiB, 不碰 PID 333197/339489; Mac 回放避开生产者 N+15..N+24 分钟窗并设按 PID 停机守卫; 不写 P2(`parity_replay_2026-09-12/phase2`)、T5b、T6、T7 目录; 不提交。

# PREREG · T4b · V2MAIN(F10)资金费列的训练/服务口径错配

## §0 问题与范围
lead 指出 V2MAIN 服务面板 `xfer_panel_live.npz` 可能同时带两个缺陷: (a) 第 80 列 `fund_ema` 按 v1 服务、按 v0 训练(king 的同形错配); (b) 历史锚行一律回填 0, 若有特征读历史行则成缺陷。本文冻结: 事实表(§1)、历史书层臂的处置(§2)、实盘窗描述性检查的装置与门(§3–§5)、09-05 席位播种对 V2MAIN 链的描述性检查(§6)。**不提议任何上线**。

## §1 写作本文之前已核实的事实(口径/血统, 无结果数字)
| # | 事实 | 收据 | 标签 |
|---|---|---|---|
| F1 | 服务: `combo_stage.py` L134–146 建 V2MAIN 面板; 末行 `f_fund_ema` = `aux["ema"][s]["acc"]`(v1, **无 12h 新鲜度过滤**), 末行 `f_fund_now` = 账本末行原始费率(无新鲜度过滤), **其余历史行全 0**。T1 实测该面板在 410 个 4h 名上 served/v1 = 1.0000、served/v0 = 2.0000 | 代码; `T1/receipts/RECEIPT_T1_h2b_serve.json` | VERIFIED |
| F2 | 读资金费列的特征: `dlw_features.py` L73 `FUND = [f_fund_ema, f_fund_now]`, L90–93 只写第 80、81 列, 且只取**被打分锚自己**的面板行(`pw_row[E_ts[i]]`); `f8_higher_order_features.py` `build()`(L98–387)不读面板、不读资金费列(A–G/J 族读 5m 缓存, J 的锚间秩、H、I 只用非资金费秩列) ⇒ **按代码, 缺陷 (b) 到不了被打分锚的输入**; 由 GATE ZH 用数据验证 | 代码 | VERIFIED(代码) / 待 GATE ZH |
| F3 | 在役 V2MAIN = `f10_live_s42_np.npz`(= pod2 `f8_ext/models/` 同文件), `pod_f10_refit_ext.py` 在 `dlw_ext` fea82(9bc111a4…)+ `f8_ext` fea89(bebf2720…)上训练; 标准化 mu/sd 由 L89–93 的训练行子样本(前 85% 锚、每 7 锚、每 3 行)计算并存入检查点, `pod_f10_np_export.py` L56 拷出。**数据级识别**: 按该规则重算的 mu/sd 在 171 列上全部与模型相符(mu 最大相对差 6.0e-6, sd 1.1e-7), 第 80 列与存储列相符(2.4e-7 / 6.3e-8), 而 v1 重铸差 153% / 143% ⇒ **在役 V2MAIN 第 80 列按 v0(含零)训练** | `receipts/RECEIPT_T4b_facts_v2main.json` F1 | VERIFIED(数据) |
| F4 | 存储零: 训练第 80 列 26.8% 格为 0; 零格 99.67% 属于钉死 450 以外的名(构建面板没有其资金费, 该名面板 v0 非零占 98.8%); 450 名内零占 0.12% ⇒ 对服务打分的名(成员 ⊂ 450), 训练见到的是真实 v0 | 同上 F2 | VERIFIED(数据) |
| F5 | 新鲜度: 训练面板在末次结算早于锚 >12h 时置 NaN→0(`pod_panel_ext.py` L160–162), 服务 V2MAIN 面板无此掩码。09-05 16Z..09-13 04Z 每锚成员中「陈旧或无结算行」与「非 450 名」计数均为 **0**; 前向窗各锚由 `t4b_freeze_inputs.py` 再计(见 §3 冻结收据) | 事实检查; 冻结收据 | VERIFIED(0 格, 因子在窗内惰性) |
| F6 | 研究 V2MAIN(A0/NW 书的 FPRED): `f10_A0_s{42,2027}` = `f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` 对齐(`build_dev_v4.py` L42–45), 由 `pod_f10_train_ext.py` 年折 2023–2026(embargo 60)在同一 fea82/fea89 上训练并打分(结果 json 记录 fea82_sha256 9bc111a4…、fea89 bebf2720…) ⇒ 研究 V2MAIN 训练与打分都是 v0(含零); 回放 V2MAIN 与实盘 V2MAIN 在非 8h 名上不是同一输入 | pod2 结果 json + 代码 | VERIFIED |
| F7 | 折模型: `pod_f10_train_ext.py` 只存预测与结果(L384–385), 每折结束 `del mdl`, 不存检查点、不存每折 mu/sd。pod2 上 `f8_ext/models/` 只有全史重训 `f10_live_s{42,2027}`; 在 `/workspace/f10`、`f8_2026-08-22`、`f8_v4`、`review_scratch/health_check`、`dl_monthly_gate`、`dl_monthly_wf` 中未见年折检查点。存在的月度研究配方: `review_scratch/allweather_trackB/earlystop/FIX7`(与 `FIX7_s2027`)各 20 折 202501..202608(`pod_f10_train_monthly_earlystop.py` sha 55ee8382…, targets sha 31d043e8… = dlw_ext 谱系, 合并预测 `f10_V2MAIN_mE1cX7_s42.npy`)、`dl_monthly_wf` mE1/mE60 202501..202608、`f8_v4` 全史重训 —— **都不是 A0/NW 书的 V2MAIN, 也都不覆盖 2024** | pod2 目录清单与 json | VERIFIED |
| F8 | combo 平价: 从 09-05 16Z 链式起步的 served 臂 combo `target_live` 只在 1.125e-4 内复现线上(T4 PC1; Phase 1 G-P2 字面 FAIL, 机理未闭合); 从锚收尾快照起步(G-P3)3/3 锚 king、`target_live`、`target_combo` 全 0.0; 三个 4h 窗的缓存迟填探针 0 格 ⇒ 「served 必须先逐位复现线上」只能在**快照起步前向模式**下满足 | `T4/receipts/T4_REPLAY_served_*.json`; `parity_replay_2026-09-12/receipts/PARITY_GP3_snapshot_*` 与 `BACKFILL_probe_*` | VERIFIED |
| F9 | 09-05 席位播种: 917 行 king 腿收益 ← v3 bundle `leg_returns.npz` king 列(sha 6061af10…), 由 `pod_export_bundle_v3.py` L97–110 从 `slow_pred_pinned`(v0 打分)算出。**GATE SL**: 用该公式从 T4 的 K0 文件重算, 与 bundle 列 10,176 行逐位相等; K1(列 80 = v1)有 5,815 行不同。机制: `combo_stage.py` L228–231 `z_fc = w3m[0]·zf + w3m[2]·fund`, `z_kc = w3m[0]·king + w3m[2]·fund`; `w3m` = 生产者席位(末 900 行 msharpe, 掩 rev24)⇒ 播种行决定 V2MAIN 分数在它自己那条链里的权重 | `receipts/RECEIPT_T4b_seat_lr.json`; 代码 | VERIFIED |

## §2 历史书层臂(主读数)
**NOT MEASURED。** A0/NW 书的 V2MAIN 来自年折预测, 其折模型与每折 mu/sd 从未保存(F7), 无法在 v1 输入上重打历史分数。按任务书不做任何替代: 不用全史重训的在役模型打历史(样本内), 不用 FIX7 或其它月度配方冒充 A0/NW 的 V2MAIN(不同配方、不同书、不覆盖 2024)。因此本轮**没有 MATERIAL / NOT MATERIAL 判决**, 也没有分辨率。结果文件须原样写明这一点, 并列出若要测量所需的东西(保存年折检查点与 mu/sd 的重训, 或 lead 另立以 FIX7 书为对象的预注册)。

## §3 实盘窗输入(快照起步前向模式)
- **起点**: 生产者锚收尾快照 `multi_asset/exports/live/producer_state_snapshots/1789200000`(09-12 08Z close; float64 H、EMA、账本、prev_rec、席位历史), 拷入 `private/producer_snapshot_1789200000/` 并逐文件对原 SHA256SUMS(16 位前缀)。
- **冻结的线上副本** `private/snapshot_live/`(`devices/t4b_freeze_inputs.py`, 生产者窗外运行, 拷贝前后 `last_anchor` 与 mtime 不变): 缓存、账本(快照之后的结算行)、shadow_log、各锚不可变文件(weights / target_live_king / target_combo / target_live)、首锚 combo 状态种子。
- **GATE CACHE(必须过)**: 冻结缓存中 ≤ 09-12 08Z 的行与快照自带缓存逐位相等。
- **锚**: 09-12 12Z(1789214400)起, 至冻结时刻生产者已收尾的最后一锚, 以冻结收据 `forward_anchors` 为准: **1789214400, 1789228800, 1789243200, 1789257600, 1789272000, 1789286400(09-12 12Z → 09-13 08Z, 6 锚)**; 冻结收据 `receipts/RECEIPT_T4b_freeze_inputs.json` sha256 `4abe6d84bded9c4716c4b6233850b04bec088445f6381e3ac717e919b60ae1c9`(冻结 2026-09-13T08:27:23Z, GATE CACHE 逐位过 11,232 行; 6 锚成员「陈旧」与「非 450」均为 0 ⇒ 新鲜度单因子臂不设)。
- **v0 馈入**: `devices/t4b_v0_feed_fwd.py` = T4 的 `t4_v0_feed.py` 只换锚与账本副本(方法已在 T4 过 V0P/V1R)。本窗无独立面板, V0P 不可做(声明); V1R 在本窗重做(§4)。

## §4 装置、臂与门
**装置**(平价目录不改一字): king 段 = 平价装置逐字节拷贝 `shadow_loop_v3_replay.py`(4d3bc157…); combo 段 = 平价装置逐字节拷贝 `combo_stage_replay.py`(f5ba9a82…), 或 `combo_stage_replay_v2col80.py`(8d7e22df…)= 在其上**唯一一行**替换(`devices/combo_stage_replay_v2col80.diff`): 生产 `combo_stage.py` L141(平价装置第 144 行)`fe[-1, j] = float(est["acc"])` 在环境变量 `T4B_COL80_NPZ` 未设时计算原表达式, 设了则取该 npz 中本锚本列的值。驱动 `devices/t4b_replay_driver.py`(对平价驱动与对 T4 驱动的 diff 均存档)。
| 臂 | king 段 | combo 段 | 第 80 列(V2MAIN 面板末行) | 席位历史 |
|---|---|---|---|---|
| served | 平价 | 平价 | 服务值(v1) | 快照原件 |
| v2inj(注入路径对照) | 平价 | 一行装置 | 回放自己当锚的 EMA acc(= 服务值) | 快照原件 |
| v2v0(训练一致) | 平价 | 一行装置 | v0 馈入(本窗无陈旧成员时即训练口径) | 快照原件 |
| seatK1(§6) | 平价 | 平价 | 服务值 | 播种行换成 K1 重算值 |
**单因子臂**: (b) 零历史 —— 若 GATE ZH 过, 缺陷 (b) 对被打分输入惰性, 不设单因子臂; 若 ZH 不过, 先写 AMENDMENT 再建「v1 + 真实历史」「v0 + 零历史」两臂, 再看 v2v0 的数。新鲜度因子 —— 若冻结收据显示前向窗有陈旧成员, 先写 AMENDMENT 加「v1 + 新鲜度掩码」臂; 为 0 则不设。

**门**:
- **PCB(必须过, 否则实盘窗差值一律不报为读数)**: served 臂每锚 king 权重 L∞ = 0.0 且内容 sha 相同、king 目标文件 L∞ = 0.0、combo rc = 0、`target_live` L∞ = 0.0、`target_combo` L∞ = 0.0、w3m 相同。
- **PC-INJ(必须过)**: v2inj 与 served 在 king X/pred/权重、combo 的 171 列输入行、V2MAIN 分数、面板末行、f10/kc/fc 状态、`target_live` 与 `target_combo` 权重上逐位相等。
- **ONE-PLACE(必须过)**: diff 恰一行; v2v0 的 king 段逐位同 served; combo 输入行在第 80 列之外逐位同、名集同; 第 80 列相同的行 V2MAIN 分数逐位同; 面板末行 `f_fund_now` 逐位同。
- **ZH**: `devices/t4b_zh_gate.py` 用 served 臂末锚留下的输入, 以同一份特征代码重建两次: 面板原样 / 面板历史行填非零值。PASS ⇔ 被打分锚的 171 列行两次逐位相等 **且** 等于 served 臂记录值 **且** 历史行资金费列确实不同(红能力)。
- **V1R**: v0 馈入的同一重建乘 8/iv 对 served 面板末行(成员格): 相对差中位 ≤ 1e-4 且 ≥ 95% 格 ≤ 1e-3; 不过 ⇒ v2v0 差值标 FEED-UNVERIFIED。
- **SL / SA**: SL 已过(F9); SA = `devices/t4b_seat_override.py` 在快照席位历史上按 09-05 干跑的行-锚映射找出播种行, 这些行的存值必须同时逐位等于 v3 bundle 与 K0 重算值; 不过 ⇒ seatK1 臂不跑。

## §5 实盘窗读法(只描述, 无判决)
逐锚与汇总(中位/最大): V2MAIN 分数 Spearman(v2v0 vs served); 分数十分位变动份额(全部 / 4h / 1h / 8h, 间隔取生产者账本末行); 第 80 列 served/v0 中位比(按间隔); fc 与 f10 链状态差(L∞、归一 L1); combo `target_live` 的 L∞、Σ|Δw|、归一 L1 = Σ|w/G − w'/G'|、权重相关、gross、净额; w3m 是否相同(应相同)。**本窗没有记账 y4s(x0910 止于 09-10 20Z), 不从缓存重算收益 ⇒ 不报任何价格或盈亏差值。** 锚数少(≤ 7)、单一 regime, 数字只作量纲。

## §6 09-05 席位播种对 V2MAIN 链(描述)
- 机制见 F9。seatK1 臂只换席位历史文件中「播种行」的 king 值(K0 → K1), 其余逐位不动。
- 报告: 各锚 w3 与 w3m(掩码 king 席位 = V2MAIN 分数在 fc 链里的系数)served vs seatK1 的差; king 段目标与 combo `target_live` 的 L∞/归一 L1; kc/fc 状态差; king 段 X/pred 必须逐位同(只动席位)。
- 标签: **席位权重与目标文件层 = MEASURED(描述)**; 盈亏影响 = NOT MEASURED(无本窗记账收益)。

## §7 边界
1. 历史主读数 NOT MEASURED(§2), 没有判决; 实盘窗只描述。
2. 训练集里 450 名以外的名是零(F4): 这是训练分布的事实, 在役打分不经过这些名, 本轮不测它对模型质量的影响。
3. king 第 80 列错配已在 T4 判 NOT MATERIAL(研究回放口径); 本轮不重测。
4. 不提议修复上线; 结果文件只陈述修复形态与需要用户字。

## §8 修订规则
冻结后任何改动 = AMENDMENT 文件并先记 sha, 再看受影响的数字; 门失败按上文执行, 不临时改阈值、锚或臂。
