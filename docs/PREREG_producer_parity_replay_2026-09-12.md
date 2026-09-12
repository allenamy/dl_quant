> **创建:** 2026-09-12 09:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 预注册(判据先于数字); 用户 09-12「实盘的效果预测不就是得按照实盘策略在正确口径来回放预估吗? 缺的仪器为什么不补?」 | **作废条件:** 生产者代码/bundle 换代(装置须从新版本重生成); 判据修订须以 AMENDMENT 记录, 不改原文

# PREREG — 生产者平价回放(把线上生产代码离线跑, 逐锚复现线上真实权重)

## §0 目的与边界(白话)
线上每锚的真实持仓目标是**两段生产代码**算出来的: `~/wide_shadow/shadow_loop_v3.py`(sha `e9c98374…`, 09-04)算 king 形态的书 → `~/wide_shadow/fea171/combo_stage.py`(sha `b5c698f9…`, 09-02)把它与 DL 腿混成 combo 并重写 `target_live`。至今没有一台装置能**离线**运行这两段代码复现线上权重; 研究回放是另写的近似。本预注册建这台装置。**阶段 1 只回答一个问题: 装置 = 线上吗?** 不产生任何收益数字。收益(线上策略在正确口径下的折外历史水平)是阶段 2, 另立预注册。

## §1 装置(派生, 不改生产文件一字节)
- `shadow_loop_v3_replay.py` = 生产文件经**逐处断言只命中一次**的字符串替换生成(`mk_replay_device.py`, 同 r18/r16 的 mk_* 纪律): ① `Fetcher.get` → 桩: `/fapi/v1/klines` 不再抓取(通道直接来自缓存, 见 §2), `/fapi/v1/exchangeInfo` 返回**记录的基名单**, `/fapi/v1/fundingRate` 从**记录的结算账本**切片; ② `TAIL_SCORE=False`(只影响 score 行, 不影响权重); ③ `STATE_DIR`/`BUNDLE`/`HEART`/`LOCK` 指向回放目录; ④ 步 2(增量 klines)替换为「把缓存中 (上锚, 本锚] 的通道行写入 st.cd」; ⑤ 步 6(上锚结账)保留但 LR 由记录文件截断供给(见 §2)。其余逐字节同生产。
- `combo_stage_replay.py` 同法: 只改路径常量(`WS`→回放目录), 模型/参考文件(`fea171/f10_live_s42.pt`, `xfer_ref.npz`, `state_H_*`)用线上同一份的**只读副本**。
- 装置自报: 生产文件 sha、替换清单与命中次数、bundle MANIFEST sha; env 白名单断言。

## §2 输入(全部是线上自己的产物, 只读副本)
| 量 | 来源 | 精确性 |
|---|---|---|
| 5m 通道缓存 | `state/rolling.npz`(ts 11,520 行 = 40 天 × 829 × 7, f16; 生产者自己算的通道) | **逐位** |
| 结算账本 | `state/aux.json.ledger_tail`(每名最近 400 次结算 ≈ 66 天) | 逐位 |
| 资金费 EMA | **递推重算**: 从 bundle `fund_ema_v1_state.json`(09-01 06:00Z 状态)按生产公式(半衰期 3 天)沿账本递推到起点 | 近似(初态差随时间指数衰减; 影响只经秩) |
| 基名单 | `aux.json.base_syms`(最新); 逐锚变化以 `shadow_log` 的 `base_n` 核对, 不符则该锚标「基名单不可复现」 | 近似 |
| 持仓 H(上锚) | `state/weights/{A−4h}.npz`(156 个锚在盘) | 逐位 |
| 腿收益 LR(席位用) | `state/leg_returns_live.json`(950 行/腿)按锚截断 | 逐位 |
| bundle | `shadow_bundle/`(MANIFEST 校验) | 逐位 |
| DL 腿状态 | `state/state_H_fc_*.npz` / `state_H_kc_*.npz`(上锚) | 逐位 |
**从本预注册起, 每锚收尾后把 `aux.json / leg_returns_live.json / rolling.npz / combo_live_status.json` 只读拷贝到 `multi_asset/exports/live/producer_state_snapshots/<anchor>/`**(首份 = 08Z 1789200000, 已落), 使今后的平价有逐锚精确初态。

## §3 判据(冻结; 先跑门再看任何数)
- **窗**: 起点 = 席位种子 v3 重启后的首锚 **2026-09-05 16:00Z**(现行生产代码从此不变), 终点 = 预注册冻结时最后一个已收尾锚 **2026-09-12 08:00Z**(40 锚)。
- **G-P1(king 段)**: 对每个锚 A, 回放 `weights/{A}.npz` 与线上同名文件 **L∞(逐名 |Δw|) ≤ 1e-6**; 通过率 ≥ 95%(≥ 38/40)才 PASS; 每个不过的锚必须给出机理归因(EMA 初态 / 基名单 / 其它), 不许归为「噪声」。
- **G-P2(combo 段)**: `target_combo/{A}.json` 与 `target_live/{A}.json`(线上为 combo 覆写后的文件)逐名 |Δw| ≤ 1e-6, 同样 ≥ 95%。
- **G-P3(签名)**: 回放的 `shadow_log` signal 行 `weights_sha` 与线上同锚行相等的锚数 = G-P1 通过的锚数(同一对象的两种读法必须一致)。
- **G-P4(反向控制, 红能力)**: 把 alpha 从 0.1 改为 0.11 重跑 3 个锚, G-P1 必须红(证明门不是空转)。
- 任一 G 红 ⇒ 装置不得用于任何收益结论; 修到过为止, 修改以 AMENDMENT 记录。
- **不报**: 任何 Sharpe / g / 换手比较。阶段 1 无收益读数。

## §4 阶段 2 预告(另立预注册, 本文不定判据)
阶段 1 过门后: (a) 把缓存换成 pod 全史 5m 缓存(`holefix2`)—— 先过**通道逐位平价门**(重叠 40 天窗上 rolling.npz vs pod 缓存逐格; r17 已发现 qv4h 中位 |Δlog| 0.52 的差异, 必须先解释); (b) king 预测换成逐年折外(`SLOW_v*` OOS)而不是训练到 08-31 的在役 booster(否则样本内); (c) 在生产代码路径上得到"线上策略的折外历史水平"与逐年表, 与研究回放 A0 逐年对照; (d) 此后所有席位/平滑/FTRIM 类候选在本装置上重测。

## §5 不主张
本文不主张线上策略的任何历史表现; 不主张研究回放错; 不改任何生产文件、不重启任何进程、不调任何 API。

## AMENDMENT 1(2026-09-12 09:4xZ, 定义性, 在窗口结果之前)
**G-P3 的比较对象改为内容 sha**: 生产者 signal 行的 `weights_sha` 是 `weights/{A}.npz` **文件字节**的 sha(`np.savez_compressed` 的 zip 条目带写入时间, 同内容不同字节), 首锚试跑(1789200000)已证: 权重 L∞ 4.7e-10、w3/turnover/gross 逐位同而字节 sha 不同。G-P3 改为: 回放与线上 `weights/{A}.npz` 的 `idx` 与 `val` 数组 sha256 相等的锚数 = G-P1 通过锚数。G-P1/P2/P4 不变。

## AMENDMENT 2(2026-09-12 09:5xZ, 结果说明 + 前向定义, 不改 G-P1/P2/P4)
窗口结果(`parity_replay_2026-09-12/receipts/PARITY_phase1_chain_*.json`): **G-P1 41/41**(L∞ 最大 9.3e-10, 门 1e-6); 链式模式下回放自己 step 6 生成的 40 条腿收益条目与线上 `leg_returns_live.json` **逐条相等(最大差 0.0)**; w3/sel/fund_updates 逐锚相同; **G-P4 红能力 3/3 红**(α 0.11 ⇒ L∞ 2.7e-4)。**G-P3(内容 sha)按 AMENDMENT 1 的定义 0/41 —— 判 FAIL 并给机理**: 线上把持仓 H 以 float32 存档(`weights/*.npz`), 回放从该存档起步, 与线上内存中的 float64 H 差 ≤2⁻²⁴ 相对, 经 EMA 平滑传播后使每锚 ≤51 个名字的 float32 存储值差 1 ulp(4.7e-10)。这是存档精度上限, 不是逻辑差。**前向定义**: 自 2026-09-12 08Z 起每锚落的 `producer_state_snapshots/<anchor>/aux.json` 含 float64 H, 从快照起步的锚上 G-P3 按原定义(内容 sha 相等)评判; 08Z 之前的锚 G-P3 以「L∞ ≤ 1e-9 且 LR 条目逐位相等」为替代读数(只报不判)。

## 结果指针(2026-09-12 10:5xZ)
`RESULT_parity_phase1_2026-09-12.md`: G-P1 PASS 41/41(≤9.3e-10; LR 40/40 差 0.0); G-P2 **FAIL 按字面**(0/41 ≤1e-6; 中位 1.05e-5, 最大 1.13e-4, 14 名; 快照起步 3/3 精确 0.0); G-P3 FAIL(float32 存档); G-P4 PASS。机理排查与前向门见 RESULT §3–§4。

## AMENDMENT 3(2026-09-12 13:0xZ, lead)—— G-P2 残差机理: 事后回填假说的第一手测量

**装置**: `devices/backfill_probe.py`(eafced4b; 两份生产者 `rolling.npz` 快照, 只看 ≤ 早锚的行, 「早 NaN 晚有限」= 回填, 「早有限晚 NaN」= 丢失, 有限对有限值变 = 改写)。快照: 08Z `producer_state_snapshots/1789200000`(08:2xZ 取)与 12Z `…/1789214400`(12:59:05Z 取, `SNAPSHOT_OK 4 files`)。

**读数**(收据 `parity_replay_2026-09-12/receipts/BACKFILL_probe_1789200000_vs_1789214400.json`): 比较行 **11,472**(≤ 08Z 锚的公共 5m 行)× 829 名; `cells_filled_later` **0**; `cells_lost` **0**; `cells_changed_finite` **0**; `symbols_with_fill` 0。

**判**: 在一个 4h 锚间隔内, 生产者缓存对过去行**零改动**。RESULT §3 的「锚后回填影响 DL 截面特征」假说在 **4h 尺度上不成立**; 它若成立只能在更长尺度(链回放从 09-05 16Z 起用的是 09-11 的缓存, 中间 6 天)。本修订**不下机理结论**; 机理由同锚的快照种子平价(`REPLAY_RECEIPT_TAG=GP3_snapshot_12Z`, 以 08Z 快照为种子前推到 12Z)与后续 ≥3 锚的连续快照对(08Z→12Z→16Z→20Z, 各自 backfill_probe)共同裁定: 若快照种子前推逐锚精确且连续快照对回填恒为 0, 则 G-P2 残差只能来自「链起点状态 ≠ 当日在役状态」这一项(即 09-05 起点的 EMA/mini-cache 历史), 与缓存无关。**预注册**: 连续 3 对快照 probe 均为 0 且快照种子平价 3/3 精确 ⇒ 判「起点状态差」; 任一对 probe > 0 ⇒ 回填假说复活并按名列出。
- **前向计数(AMENDMENT 3 预注册序列)**: 快照种子平价 **1/3** —— 12Z: 以 08Z 快照(1789200000)为种子前推到 1789214400: king L∞ **0.0**, 内容 sha 相等, ulp 名 0, combo rc 0, `target_combo` L∞ **0.0**, `target_live` L∞ **0.0**(收据 `receipts/PARITY_GP3_snapshot_12Z_1789214400_1789214400.json`); 快照对回填探针 **1/3**(08Z→12Z: 0/0/0)。下两对: 12Z→16Z(16:59Z 取快照后)与 16Z→20Z。
- **AMENDMENT 3 措辞更正(14:4xZ, 研究员 563e3470 `parity/RESULT.md` §4)**: 「若三对 probe 全 0 且三次快照种子平价精确 ⇒ 判起点状态差」**不成立为唯一识别**: (1) 测量窗不含 09-05→09-11 的历史回填/改写; (2) 当前 rolling 左边界、mini 特征历史长度、辅助文件代际未做互斥干预; (3) 每次重设为真实快照再前推一步会切断累积误差, 不能替代从足够早的完整快照连续前推整个旧窗。⇒ 序列结果只能写「支持『初态/历史输入差』候选, 尚未排除其他解释」; 历史 G-P2 FAIL 独立保留, 不因近期成功注销。研究员用七通道全量复算 08Z→12Z 11,472 行 mask 差 0 / 有限值变动 0, **加强**第一对零回填结论(我方探针只查 log_qv 支持 + ret5 变动)。
- **前向计数 2/3(16:4xZ)**: 16Z 快照种子平价(12Z 快照 1789214400 为种子 → 1789228800): king L∞ **0.0**, 内容 sha 相等, ulp 名 0, combo rc 0, `target_combo` / `target_live` L∞ **0.0**(收据 `receipts/PARITY_GP3_snapshot_16Z_1789228800_1789228800.json`); 快照对回填探针 12Z→16Z **0/0/0**。按 AMENDMENT 3 措辞更正: 结果只支持「初态/历史输入差」候选。剩 16Z→20Z 一对 + 20Z 快照种子平价(20:58Z 后)。
