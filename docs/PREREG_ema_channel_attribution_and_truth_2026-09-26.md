> **创建:** 2026-09-26 18:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 判据冻结, **任何读数之前**(本文与装置同一提交;装置在提交后才第一次运行;此前唯一相关读数是 `838210c6a` 的探针, 它比较的是 NC `fund_state`, 不是本文的真值) | **作废条件:** 下列任一被钉 sha 改变

# 冻结:资金费 EMA 通道 —— ① 分歧逐格归因到跳过门 ② NC EMA 是否为真值(lead 裁定 (a), 只用 CPU)

## 0. 被钉输入

| 角色 | 路径(pod2) | sha256 前 12 |
|---|---|---|
| 研究 EMA(被审) | `/dev/shm/news_2026-09-23/work/fund_replay.npz` `ema_acc` / `last_ft` / `last_iv` | 8a73588f… |
| NEW_S 成员 | `/dev/shm/news_2026-09-23/work/legs.npz`(`isfinite(ZFD)`) | 18999e169c6b |
| NC 特征(被判真值者) | `/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz` `fe_v` / `m` / `off` | 3c886a2bc0ff |
| 重算 · 生产者间隔规则 | `/dev/shm/d10_2026-09-25/ms/rebuilt_features_snap.npz`(news2 装置 `--ema-mode producer_snap`, 来自 ledger_full_ms) | 209c8f5338d3 |
| 重算 · D10 间隔规则 | `/dev/shm/d10_2026-09-25/ms/rebuilt_features_d10.npz`(`--ema-mode d10_iv`) | 2be2d7c8959b |
| 真值账本 | `/dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz` | e179071d5955 |
| 回放自己的输入账本(签名用) | `/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz` | 装置运行时记录 |

重算产物由 news2 的装置(`3e9d72c10` / `611fc1907`)产出, **我只读、不重写**。

## 1. 人口与分母(先写明, 再出数)

- 窗 W:锚 ≤ **2026-09-01T02:00Z**(与 `611fc1907` 的共同窗相同)。
- `P_NC`:NC 特征的成员格(锚 i, 名 j)∩ W。
- `P_NS`:NEW_S 成员格 `isfinite(legs.ZFD)` ∩ W。**有真值的被审人口** = `P_NS ∩ P_NC`;`P_NS \ P_NC` 的格数单报为「无真值, 不判」。
- 每个比较都报三类, 不合并:两侧有限且按 |差| 分桶;左有限右 NaN;左 NaN 右有限。

## 2. ② NC 的 EMA 是否为真值

- **T1(生产者间隔规则)**:`P_NC` 上 NC `fe_v` 对 `rebuilt_snap.fe_v`, **容差 0**(逐位;NaN 对 NaN 算相同)。分四层报:{pre-2026, 2026} × {该名在 (A−4h, A] 内 ledger_full_ms 有结算 / 无结算}。
  判 `NC_TRUE_UNDER_PRODUCER_RULE` 当且仅当四层**差异都为 0 且每层 ≥ 1,000 格**;否则判 `NOT_ESTABLISHED`, 本文 ① 的读数一律降级为「对 NC 的分歧」。
- **T2(D10 间隔规则)**:同一人口上 NC `fe_v` 对 `rebuilt_d10.fe_v`, 按 |差| 分桶 + 四层报。**不作 ① 的门**:它量的是间隔规则的差异(已知 `fund_ema` 334,910 格由间隔规则传播而来), 与 `fund_replay` 污染是两件事;只是把两者的量级并排给出。
- 真值的含义照写:T1 成立 ⇒ 「NC EMA = 对档案核过的账本(ledger_full_ms)+ 生产者自己的 EMA 函数」;这两条链**共享 EMA 函数**, 所以 T1 证的是事件集与 as-of 边界一致, 不证 EMA 公式本身。

## 3. ① 分歧逐格归因

被审量:`Δ = |fund_replay.ema_acc − rebuilt_snap.fe_v|`, 人口 `P_NS ∩ P_NC`, 两侧有限。

签名(`fa_rn8census.py` 的定义逐字):`gate = last_ft > 0 ∧ isfinite(last_iv) ∧ (A − last_ft < last_iv·3600·0.9)`;
`missed = 回放输入账本在 (last_ft, A] 内的结算数`;`sig = gate ∧ missed > 0`。

对 Δ > 0 的格分四类(对每个 |差| 桶交叉报):

| 类 | 定义 |
|---|---|
| `GATE_NOW` | 该格 `sig` 为真 |
| `GATE_EPISODE` | 该格 `sig` 为假, 但在同一名的同一段「连续 Δ > 0 的锚」内, 此前某锚 `sig` 为真(EMA 是累积量, 过去漏取的结算会延续) |
| `NOT_GATE` | 上两者都不成立 |
| `UNDETERMINABLE` | `last_ft ≤ 0`, 或 `last_iv` 非有限, 或该名不在回放输入账本里 |

类的优先级:`GATE_NOW` > `UNDETERMINABLE` > `GATE_EPISODE` > `NOT_GATE`(一格只进一类)。

「归因到门」= `GATE_NOW + GATE_EPISODE`;「归不到门」= `NOT_GATE`;「无法判定」= `UNDETERMINABLE`。
读法:实质格(Δ > 1e-5)里 `NOT_GATE` 若超过 10%, 写「**存在第二机制**」并具名候选(`news_fund_replay.py` L38–39 在 limit 100 截断时保留最早行、丢最新行), **不**归因给它(本装置不测它)。

## 4. 控制(任一 FAIL ⇒ 该节读数 UNAVAILABLE)

- **K1 签名复现旧值**:在 RN8 通道上(NEW_S legs 对 NC legs, 两侧有限且不同的 404 格)用本装置的签名实现, 必须**恰好**复现在案 `FA_RN8CENSUS.json`:
  360 / 404 有签名, 20,000 个非差异抽样格(`default_rng(0)`, 同一抽样代码)中 0 个。
- **K2 已知答案**:在真值数组的 100 个随机格(`default_rng(1)`)上加 1e-6 后再分桶, 真值对「真值加扰动」的比较必须恰好 100 格落在 (1e-7, 1e-5] 桶、其余全在「恰为 0」桶;任何数组自比较全部落在「恰为 0」桶。
- **K3 轴**:所有数组的锚轴与名轴逐位相同(断言)。

## 5. 必报

归因四类 × 桶 × 年份;实质格(>1e-7 与 >1e-5)的四类分布;T1 四层计数;T2 桶与四层;`P_NS \ P_NC` 格数;
并与 `838210c6a` 的探针数(对 `fund_state`)并排, 说明两者比较对象不同。
