> **创建:** 2026-09-27 11:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 执行计划(lead 11:0xZ 下令);用途与控制写于任何产物之前 | **作废条件:** lead 改写本计划;或冻结判词 6838a219a 被撤回

# 计划:把 D10 账本延长过切点,重建 D10 特征与 legs,供**描述性重读**

## 0. 用途(写死在前,不可改)
- 这是给用户裁定 UNDECIDED 发布用的**描述性重读**。冻结判词 UNDECIDED(6838a219a)**不改**,本计划的任何产物都不构成新判词。
- 起因(runbook §6 #7 备注):(ii) 的书层读数里,09-01T02Z 到 09-18 这一段,D10 资金费列没有新事件;实盘服务时则会有。
- 本计划让切点之后的特征与服务时一致,再由 dlarch 重新打分、重建三格,作为描述件交给用户。
- 优先级高于 rerun6。一次只起一件重活,每一件都过资源门、用 registry_edit 登记,输出一律写到新目录 `/workspace/d10_reread_2026-09-27/`。
- 十月 King OOF 不变:274ba08a…507296。

## 1. 步骤与控制(每一步的判据都写在这里,先于它的产物)
| # | 步骤 | 装置 | 控制(红即停,具名上报) |
|---|---|---|---|
| R1 | 九月 API 毫秒源拉取,窗口 2026-08-31T00:00Z → 2026-09-27T08:00Z,名单为 e179071d 的 829 个名,在 pod2 上跑 | `d10_pull_api_funding_ms.py`(测试 4/4) | 结果为 COMPLETE,失败的名为 0。空名单独列出(已下架或新上的名),不算失败 |
| R2 | 账本延长:`d10_build_ledger_ms.py` rev 2.2,参数 `--extra-api <R1> --prefix-ledger e179071d`,**不加 --extra-months** | rev 2.2(变异控制 3/3 红) | RECONCILED;PREFIX_BITWISE,且 src 升级数为 0(没有加新的归档月);api_overlap_unequal 为 0;rows_after_prefix > 0;最后一行 ≥ 2026-09-18T20:00Z |
| R3 | 第一阶段重建:`d10_rebuild_funding_features.py --source ledger_ms --ema-mode d10_iv`,用新账本 | 已修的 durable 版 | 平价门 `--anchor-max-utc 2026-09-01T02:00Z`,拿新产物对照旧的 2be2d7c8,比 fund_now、fund_ema、iv 三列:必须 PARITY_GREEN,即切点之前逐位相同 |
| R4 | fund_state 的 d10 模式,用新账本 | `d10_build_fund_state.py` | 新建装置 `d10_fund_state_prefix_identity.py`:每一列中 ft < 切点的事件,以及锚 ≤ 切点的 kidx,都必须与 f07e4ebd 逐位相同 |
| R5 | pass1 共 24 片,另加 merge1 | `nc_p2_build.py` p1(NC 复制件,代码不改),驱动带参数 | 每片 rc 为 0;merge1 DONE |
| R6 | 装配 | `d10_stage2_assemble.py`,`--r0` 用线 D 已有的恒等分片 R0,`--r2` 用 R5,`--rebuilt` 用 R3,`--cut 1788228000` | G1、G2 都过;切点之前的交叉核对为 0。另过平价门 `--anchor-max-utc` 切点,对照 f1cd3fa2 比三列:必须 PARITY_GREEN。切点之后的变化行数只作描述 |
| R7 | legs:`d10_stage2_legs_oct.sh` 改一版,特征路径与 R2 根改为参数传入 | King OOF 274ba08a | 锚 < 切点的每一行,在每个键上都与 383e3ddc 逐位相同。切点之后各键的变化只作描述 |
| R8 | 交付 dlarch | 路径、sha、收据 | 交付检查 L1–L4,与 legs_delivery_check 同一套 |

## 2. 不回答什么
- 不回答「修数据的好坏」,也不改判词。
- 切点之后那一段的特征,取的是 API 源(src = 1)。月度 zip 要到 10-01 才有,所以没有双源核对。这一限定写进每一件收据。
