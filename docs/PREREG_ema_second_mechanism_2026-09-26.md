> **创建:** 2026-09-26 20:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh 分叉) | **状态:** 判据冻结, 读数之前(本文与装置同一提交;装置分两段跑:先 `--stage controls` 只出控制, 控制全过才跑 `--stage full`) | **作废条件:** 下列被钉 sha 改变

# 冻结:EMA 通道「第二机制」三个候选的最小判别实验(lead 裁定 4)

背景:`FA_EMA_ATTR.json` a3aa35da(`4d3a26dad`):研究 EMA(`fund_replay.ema_acc`)对真值(news2 producer_snap 重算 `fe_v`)|差| > 1e-5 的
30,359 格里 30,242 格(记为 **M**)不带跳过门签名。候选:(1) 间隔赋值规则不同;(2) limit-100 截断丢最新行;(3) 算术不逐位。

## 0. 被钉输入(pod2, 全部只读)

`fund_replay.npz` 8a73588f;回放输入账本 `ledger_spliced_p2_to_20260901T0200_streamD_after.npz` 073088e5;真值账本 `ledger_full_ms.npz` e179071d;
`rebuilt_features_snap.npz` 209c8f53;NC `NEWS_FEATURES.npz` 3c886a2b;NEW_S legs 18999e16;NC legs 9ee5886f;成员掩码 f752d8ae;`P1_members_2025H2on.npz` 2323623f;
`nc_contract.py` 316a0b9b(`ema_step` / `snap_interval` **调用, 不重写**);回放收据 `P2A_FUND_REPLAY.json` 75fd360a;`FA_EMA_ATTR.json` a3aa35da。

## 1. 两处代码的实际差别(读码, 先于读数)

| 项 | 研究回放(旧生产者块 L451–484) | 真值(nc_contract + news2 重算) |
|---|---|---|
| 事件集 | 回放输入账本(秒) | ledger_full_ms(毫秒, 按秒进 EMA) |
| 覆盖 | 冷启动于该名首次进基名单之锚的 40 天前;每锚只取到 `last_ft`(受跳过门、limit 100、基名单影响) | 全历史, as-of = 锚秒 + 999 ms |
| 间隔 | `min([1,2,4,6,8], key=|a−x|)`:平局取**小**;首事件 = 8;间距 ≤0 或 >24h ⇒ 按 8 | `snap_interval`:平局取**大**;首事件 = 未知 ⇒ 重置;>24h ⇒ 未知 ⇒ 重置 |
| 算术 | `rn = rate*(8.0/iv)`;`a = 1−0.5**(max(dt,1)/τ)`;`acc += a*(rn−acc)` | `rn = rate*8/iv`;`decay = 2**(−dt/τ)`;`acc = decay*acc + (1−decay)*rn` |

## 2. 实验

**控制 A(复现)**:按 `fa_ema_attr.py` 的定义重算人口 P、真值、签名、片段, 实质格三类必须恰为 GATE_NOW 96 / GATE_EPISODE 21 / NOT_GATE 30,242。

**实验 B —— 候选 (2) 截断(不需模拟)**:EMA 只依赖事件时间, 不依赖取到它的时刻 ⇒ 截断只在「当锚仍未追上」时起作用。逐格定义(i 锚, j 名):
`stale = last_ft[i,j] <` 回放账本里 ≤ A_i 的最后事件;`gate_pre` 用锚前状态(`last_ft[i−1]`, `last_iv[i−1]`);`fetched = 在基名单 ∧ ¬gate_pre`;
`truncated = fetched ∧ (last_ft[i−1], A_i] 内事件数 > 100`(空账本时窗为 (A_i − 40d, A_i])。stale 格按原因分:`TRUNCATED`(fetched)/ `GATE_SKIP` / `BASE_ABSENT`。
- 控制 B1:全表 `truncated` 之和必须**恰为 226**(回放收据自记的 `fetch_truncated_at_limit_100`)。
- 控制 B2:`fetched ∧ ¬truncated ∧ stale` 必须为 0。
- 读数:M 中 stale 的格按三原因计数。

**实验 C —— 候选 (1) 间隔、(3) 算术(模拟, 逐因子切换)**:逐名重放 EMA, 四个开关 L(事件集:回放账本 / ms 账本)、C(覆盖:回放 / 冷启动但追平 / 全历史)、I(间隔:旧 / 新)、R(算术:旧 / `ema_step`)。
I 为「新」而 iv 未知时一律重置(两种算术同一语义)。
- 锚定控制:全旧必须**逐位**复现 `fund_replay.ema_acc`(P 上);全新必须**逐位**复现 `rebuilt_features_snap.fe_v`(P 上)。任一不过 ⇒ 实验 C 全部 UNDETERMINED(只报 B)。
- 已知答案:间隔函数对 3h 旧给 2、新给 4;首事件旧给 8、新给未知;30h 旧给 8、新给未知。
- 读数:从全旧出发**只切一个**因子到新(L / S=覆盖回放→追平 / K=冷启动→全历史 / I / R), 以及从全新出发只切一个回旧;各报对真值的分桶、实质格数、M 中「降到 ≤1e-5」的格数(**已解决**)与 M 外新增的实质格。两两交集照报;**份额不可相加**。

## 3. 判词(每个候选)

记 x = M 中被该因子单独解决的格数 / 30,242(从全旧出发);y = 从全新出发把该因子切回旧所产生的实质格数 / 30,242。

- `EXPLAINS_x`:x ≥ 0.05 且 y ≥ 0.05;
- `DOES_NOT_EXPLAIN`:x < 0.01 且 y < 0.01;
- 其余 `UNDETERMINED`(部分或交互)。
- 候选 (2) 另用实验 B:M 中 `TRUNCATED` 格占比 < 0.01 ⇒ 支持 DOES_NOT_EXPLAIN;两条路不一致时写 UNDETERMINED 并并列。
- 候选 (3) 另报「残差」:P 中 (0, 1e-15] 格数, 全旧 对 全旧仅切 R;下降 ≥ 90% ⇒ `EXPLAINS_RESIDUE`。
- 若 L 或 K(非候选)满足 EXPLAINS, 具名写出为「候选之外的机制」。
