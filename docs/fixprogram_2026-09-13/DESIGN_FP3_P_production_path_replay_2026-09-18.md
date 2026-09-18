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
