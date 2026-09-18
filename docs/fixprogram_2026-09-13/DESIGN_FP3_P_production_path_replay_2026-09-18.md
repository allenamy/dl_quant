# FP3 P 设计: 生产路径历史回放(同码、连续状态、逐层比对)— 2026-09-18

> **创建:** 2026-09-18 00:5xZ | **Session:** b9646a9e(主研究员) | **状态:** 设计(事实已核; 装置未写) | **作废条件:** §1 任一事实被推翻; 复审否决 §3 判据
> **回答的问题:** 用户 Q1「在役策略不就是生产代码吗, 为什么回放不用 FTRIM/平滑/播种/reshape」与复审 C「完整生产策略连续回放」。现有回放引擎(pod2 `w10_health.py`)与生产(Mac `shadow_loop_v3.py` + `combo_stage.py` + 执行器)是**两套代码**; 本设计把生产代码本身放到历史数据上跑。

## 1. 事实(全部本会话核过)
| # | 事实 | 来源 |
|---|---|---|
| F1 | 生产者 `shadow_loop_v3.run_anchor(st, fx, cfg, booster, anchor)` = 取数(三处 `fx.get`: 5m klines 增量 / exchangeInfo / fundingRate 增量)+ 纯计算(成员筛、82 特征、booster.predict、上锚结账、席位、FTRIM、目标书)。取数只经 `Fetcher` 对象 | `~/wide_shadow/shadow_loop_v3.py` L259–565 |
| F2 | 生产者的 5m 滚动面板 `state/rolling.npz`(11,520 行 × 829 × 7, float16, 40 天)与研究 5m 缓存 `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz`(490,753 行 × 829 × 7, 2022-01-01 → 2026-09-01)**通道相同**([ret5, range, cpos, log_qv, log_cnt, log_avgsz, tbf])、符号轴同 829 名(`fea171/xfer_syms.npz`) | 本会话读 |
| F3 | 递推状态 = `aux.json`(prev_close, H 持仓, last_anchor, ema 资金费 EMA, ledger_tail 资金费账本, base_syms, prev_rec)+ `leg_returns_live.json`(三腿 950 锚收益序列, msharpe 席位回看 900)+ `state/weights/<A>.npz`(逐锚, 08-12 起 190 件)+ `fea171/state_H_{kc,fc,f10}_<A>.npz`(逐锚, 08-26 起)。前两者只有当前版本(09-17 起逐锚快照); 08-26 换装时 combo 由 king 形态暖启动 | 本会话读 |
| F4 | combo_stage 读 aux.prev_rec(members/legz/sm/sm_idx)、rolling、weights/<A−4h>、state_H_*_<A−4h>、target_live/<A>(king 形态) ⇒ 合成 f10 分数(mini 缓存 → dlw 特征 → f10 模型 `f10_live_s42_np.npz`)→ 混合、FTRIM、reshape → target_live | `combo_stage.py` |
| F5 | 执行器读 target_live 后: reshape(`live/spec_book_reshape.py`)、上限/最小名义、逐名止损(`per_name_stop`, −30%/2 锚)、chase 分臂 → 订单; 锚后回读 = 真值 | 执行器树 d858c36 |
| F6 | 资金费历史: `r6_fund_sep.json.gz` / `fund_aug.json.gz` / P9 声明间隔表(07-01…09-13) / `wide_multisrc/funding`; 宇宙历史: 生命周期日历 `CONTRACT_LIFECYCLE.json` + 可交易掩码(按成交 W24H) | FX_DATA 受据 |
| F7 | king booster = `shadow_bundle`(在役 slow2026 8d79186b); 历史折外 king 分数 = 研究链 `SLOW_v3_on_v4axis.npy`(逐年折外)。**全历史回放不能拿在役模型回灌早年**(复审 C 要求折外) | 复审件 §4 |

## 2. 装置(分三段, 每段有独立判据; 都在 pod2 跑, 生产树零接触)
**P-A 历史取数器(HistoricalFetcher)**: 实现 `Fetcher.get(path, params)` 的三个端点, 从研究缓存/资金费账本/宇宙日历回答; 因果: 只返回 close ≤ anchor 的 bar、fundingTime ≤ anchor 的结算、锚时点的 TRADING 名单。判据: 对 2026-08-26…09-17 的每个锚, 取数器给出的 5m bar 与生产者当时的 rolling 快照(09-17 起有快照; 之前用当前 rolling 的重叠段 08-09…09-18)**逐格相等**(float16 位相等或 |Δ| ≤ 1 ulp), 资金费行集合相等。
**P-B 生产者连续回放**: 把 `shadow_loop_v3.py` + `combo_stage.py` 原字节拷到 pod2 沙箱 HOME, 用 HistoricalFetcher 替换 `Fetcher`(唯一改动点 = 注入, 通过 monkeypatch 不改源), 从 08-26 00Z 的归档状态(weights/1787702400.npz = H; aux 的 ema/ledger_tail 由 P-A 从资金费账本按生产者同一公式重建, EMA 半衰期 3 d 只需 ≥30 d 历史; leg_returns 用 `.pre_seatseed_v3_20260905` 备份截断到 08-26, 09-05 后用播种版)起, **沿自己的状态**逐锚跑到 09-17 20Z, 每锚写 target(king 形态)与 combo target。判据: 与归档 `target_live_king/<A>`、`target_live/<A>` 逐名权重比较, 报 max|Δw| 与不等名数; 08-26…09-05 期望 ≈ 0 差异或可归因于播种/暖启动的**具名**差异; 任何不可归因差异 = 生产者有未记录状态输入(即真正的缺陷候选)。
**P-C 执行器书层**: 把执行器的 reshape/上限/最小名义/逐名止损模块作为纯函数施于 P-B 的 target(同码导入, 输入 = 目标 + 锚后回读持仓 + 中价), 输出「执行器意图持仓」, 与归档 `anchors.jsonl.weights`/回读比较。判据: 逐名意图仓位差 ≤ 最小名义; 差异归因(拒单/部分成交为执行层, 不属书层)。
**P-D 全历史(2022-06-30 起)**: P-A/B 在研究缓存全长上跑, king 分数用折外 `SLOW_v3_on_v4axis`(F7), DL 用逐月折外 f10 preds; 输出逐锚生产路径书 → 用现有 RAW 记账(y4 面板)出逐年表, 与 w10 回放并排 ⇒ **「生产书 vs 研究书」的差异分解**(FTRIM/平滑/播种/止损各自贡献, 用同一 Shapley 装置)。

## 3. 判据与交付
- P-A 位相等收据; P-B 逐锚差异表(0 不可归因差异才算「同码连续回放成立」); P-C 意图持仓差异表; P-D 逐年表 + 差异分解。每段独立复审。
- 不改生产任何字节; 生产者源码按 sha 冻结进收据(3520d363 等)。
- ETA: P-A 1 d(取数器 + 位相等), P-B 1–2 d(状态重建是主要工作), P-C 0.5 d, P-D 1 d(计算 27 s/锚 × 9,138 锚 ≈ 70 h 单线程 ⇒ 需并行分段, 或先做 2025-01 起)。

## 4. 与其它项的关系
D 的残差归因(成交价来源)、I 的取数、C 的两锚单步平价都不被本设计替代; L 最终表以 P-D 的生产路径书为准。

## 5. 进度 2026-09-18 01:1xZ(追加)
- **P-A 成立**: 生产者 5m 面板快照(09-17 12Z)与研究缓存在重叠 08-08 12:05Z…09-01 00Z 七通道有限格逐位相等(收据 `FP3_receipts/PA_PANEL_IDENTITY_2026-09-18.json`, 装置 `FP3_devices/preplay/pa_panel_identity.py`)。
- **P-B 装置成型**(`FP3_devices/preplay/preplay_driver.py`, pod2 `/workspace/fp2_2026-09/preplay/`): 生产者 `shadow_loop_v3.py`(e9c98374)与 `combo_stage.py`(3520d363)原字节拷入沙箱 HOME, 唯一注入 = `HistFetcher`(5m klines 由缓存预填、fundingRate 由生产者自己的账本(bundle 种子 ∪ 快照 ledger_tail)回答、exchangeInfo 由「24h 内有结算」推 TRADING); 初始状态 = bundle 自带引导(08-30 20Z)+ 三处因果修正: 非在役名 NaN、资金费账本/EMA 按生产者公式截断重建到起点(bundle 种子含 09-01 的未来行)、腿收益 extras 用生产 pre-seed 备份截去起点之后 34 条; H 用归档 `weights/1788120000.npz`; combo 递推状态用归档 `state_H_*_1788120000.npz`。
- **两锚冒烟(08-31 00Z/04Z, `PREPLAY_SMOKE_2anchors_2026-09-18.json`)**: 与生产 shadow_log 信号行**同值**: sel 242/242 与 244/244, fund_updates 457/457 与 360/360, members 400/400; 席位 w3 差 ≤ 0.006; king 目标 L1 0.64% / 1.04%, max|Δw| 0.0003 / 0.0006; combo rc 0, L1 3.5% / 6.8%。归因阶梯(同两锚): 引导 H(bundle 离线轨迹)→ 归档 H: king L1 18% → 1.7%; 再加三处因果修正 → 0.6%。剩余 king 差异候选 = 起点缺一条结算行(prev_rec None)与备份截断假设; combo 差异待全程曲线判断(收敛/漂移)。
- **全程运行**(08-31 00Z → 09-18 00Z, 108 锚)01:1xZ 起在 pod2 后台, 逐锚记录 `sb_full/PREPLAY_anchors.jsonl`。

## 6. 进度 2026-09-18 01:5xZ(追加): 同码连续回放**成立**(状态已知的窗)
- **精确状态起点**: 从 09-17 12Z 生产快照(rolling / aux / leg_returns / state_H)初始化, 用回放自己的取数器与状态推进, 16Z / 20Z / 09-18 00Z 三锚 king 与 combo 目标与归档**逐位相等**(L1 0.0, max|Δw| 0.0), 成员集对称差 0, 席位 w3 同值(收据 `PREPLAY_SNAPSHOT_INIT_continuous_3anchors_2026-09-18.json`)。⇒ 「同代码 + 同数据 + 同状态 ⇒ 同书」在有快照的全部锚上成立, 且随快照积累自动延伸。
- **单步误差**(逐锚从归档重置 H 与 combo 状态, 08-31 七锚): king L1 0.5–0.9%, max|Δw| ≤ 0.0005; combo 3.4–4.3%(`PREPLAY_ONESTEP_7anchors_0831_2026-09-18.json`)。这是「初始状态谱系」(bundle 引导态 ≠ 生产真实 08-30 态: EMA 谱系、腿收益 extras、基名单)的单步足迹, 不是代码差。
- **生产干预时间线**(已钉): combo_stage ff5de5d8(无 FTRIM)≤ 09-02 08Z → b5c698f9(FTRIM)09-02 12Z…09-17 12Z → 3520d363; shadow_loop db326162(pre-M1)≤ 09-04 00Z → e9c98374(M1); 席位播种 09-05 12:20Z(16Z 锚起)。当前代码版回放在 09-06 后 king L1 跳到 8–15% = 这些干预的足迹; 时间线钉住版(`--timeline`)首两锚 combo L1 已从 6.8%/9.2% 降到 2.7%/3.5%。两版全程(08-31 → 09-18)在 pod2 后台运行中, 收据出后写 P-B 结果件。
- **对复审 C 的回答**: 「增加单步样本不能补齐」——同意; 本段给的是自产状态连续推进(不是逐步重置)且包含 king 特征/推理重建; 剩余 = 执行器书层(P-C)与全历史折外(P-D)。

## 7. 进度 2026-09-18 02:0xZ(追加): 时间线钉住版驱动的两处缺陷与修正(v4)
- 45 锚运行(`sb_full_tl`)读数: 08-31→09-05 12Z king L1 均值 1.7%(中位 1.7%, 最大 2.6%), combo 3.4%(收敛到 2.0%), 成员集对称差全程 0; 09-02 12Z FTRIM 版切换后 combo 从 3.5% 单调降到 2.1%。但 **09-05 16Z 播种注入后席位 w3 差从 0.005 跳到 0.037**, king L1 升到 3.8%。
- **缺陷 1(播种行数)**: 注入用的是当前滚动文件去掉末 75 行 = 播种文件去掉**头** 75 行(状态文件只留末 950 行, 已实测 `current[:875] == seeded[75:]` 三腿全等), 席位窗因此少 75 行。**修正**: 改用播种当时换入的原文件 `multi_asset/exports/live/seat_seed_v3_2026-09-05/leg_returns_live.seeded_v3.json`(sha 4a3bfd9a9353, 与 `dryrun_receipt.json` staged_sha 一致), 驱动内断言 sha。
- **缺陷 2(播种锚与 M1 锚)**: 生产 shadow_log 标 09-05 08Z 的记录 logged 12:20:15Z(换入前), 标 12Z 的记录 logged 16:21Z(换入后, kickstart 之后) ⇒ **12Z 锚是第一个在播种文件上跑的锚**, 驱动原注入在 16Z(晚一锚); M1 字段(`base_n/fund_base_n/fund_updates_base/exinfo_ok`)首见于标 **09-04 04Z** 的记录, 驱动常量误写成 09-05 00Z(晚一天, 6 锚用了 pre-M1 代码)。**修正**: `SHADOW_VERSIONS` 截止 1788480000(09-04 00Z 为最后 pre-M1 锚), `SEAT_SEED_ANCHOR` = 1788609600(12Z)。
- 旧运行按记录的 PGID 1033414 停止(不按名扫杀), 修正版 `preplay_driver_v4.py`(3da96c12)在 `sb_full_tl2` 从 08-31 00Z 重跑到 09-18 00Z; 生产者语义已核: 腿收益历史 = bundle 全部行 + 状态文件行, 席位取末 900 行(`shadow_loop_v3.py` L226–228, L457–458)。
- **02:1xZ 更正(缺陷 2 的播种锚部分, 我在 v4 里改错了)**: v4 运行到 09-05 12Z 时席位差跳到 0.1025, 16Z 起回到 0.005。核生产记录: 标 12Z 的记录 w3 = [0.1623, 0.1361, 0.7017] = 播种干跑受据里的 **CURRENT(播种前)** 向量(逐位相同), 标 16Z 的记录 w3 = [0.2677, 0.1209, 0.6114] ≈ 播种后; 而每条记录的 logged_utc 都是标签 + 4h20m ⇒ **生产者在 A+20m 计算锚 A 的书与席位, 记录在结算时(A+4h20m)落盘**; 12:47Z 的换入落在 12Z 运行(12:20Z)与 16Z 运行(16:20Z)之间 ⇒ **首个用播种文件的锚是 16Z**, 原驱动的注入锚是对的, 只有行数错。M1 的 09-04 04Z 判定在这个读法下不变(标 04Z 的记录含 M1 字段 ⇒ 04:20Z 的运行已是 M1 代码)。修正版 `preplay_driver_v5.py`(注入锚 16Z + 原文件 950 行)在 `sb_full_tl3` 从 08-31 重跑; v4 运行按 PGID 1064944 停止。教训入错题集: **锚标签不是运行时刻; 判定干预落在哪个锚要用记录里的状态量(w3)对照干预前后的已知值, 不能只看 logged_utc**。

## 8. P-C 设计修正 2026-09-18 02:5xZ(复审 r7 §7: 「目标 + 锚后回读 → 意图」是循环)
- 原 §2 P-C 写「输入 = 目标 + 锚后回读持仓 + 中价」——**作废**: 锚后回读是执行的**结果**, 拿它初始化计划再声称复现执行是循环。
- 修正: 执行器书层纯函数的输入 = 该锚**决策前可见**的状态(上一锚锚后回读 = 本锚开盘持仓、本锚 target_live、本锚 mid_at_anchor_vector、逐名止损计数器与冷却状态、`per_name_stop.json` 的决策前快照、reshape 参数); 输出 = 「意图持仓 / 意图订单」; 本锚锚后回读**只用于验证输出**(意图 vs 实际的差 = 执行层: 拒单 / 部分成交 / 保护性平仓), 不回灌。多阶段锚(chase 臂、追单)每阶段只用该阶段计划之前的读数。
- 判据不变(逐名意图仓位差 ≤ 最小名义, 差异归因到执行层), 装置未写。
