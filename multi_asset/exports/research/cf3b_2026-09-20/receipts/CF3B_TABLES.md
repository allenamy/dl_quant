# CF3-B 全表 · 反事实世界上的风格/β 分解(由 `cf_beta_read.py` 从收据渲染)

仪器 = **未改一个字节的** `at_beta.py`; 层 = **L2 纸面书**(price = 1e4·ΣW·RET), **不是** L1 已实现 g。

## 门

| 门 | 结果 |
|---|---|
| B5 控制复现(我的 BASE vs 已发布 §5) | **23 / 23 格逐位相同** |
| B-A1 延展 113 行不可读(变异实测) | 毒化后变动 **0** 个数(要 0); 零对照: 单个 in_run 行 ×1.001 变动 **121** 个数(要 >0) |
| §5.4 UNATTRIBUTED 上界 ≤ |Δ共同|/2 | **满足**(实测无 β 的 gross 份额 = 0.00000, 上界 = 0.0000) |

## 逐臂 · 逐时段(L2 纸面价格, bps/锚/目标 gross)

| 臂 | 时段 | n | 价格 | 共同风险+风格 | 逐名 | 事前净 β |
|---|---|---|---|---|---|---|
| `BASE` | HIST | 5495 | +0.8617 | **+0.3206** | **+0.5412** | -0.0233 |
| `BASE` | 2026 | 1453 | +4.1023 | **+1.8109** | **+2.2914** | -0.0854 |
| `NONE` | HIST | 5495 | +0.5176 | **+0.2747** | **+0.2429** | -0.0311 |
| `NONE` | 2026 | 1453 | +4.9490 | **+3.1514** | **+1.7976** | -0.0664 |
| `noFUND` | HIST | 5495 | +0.5254 | **+0.2190** | **+0.3064** | -0.0359 |
| `noFUND` | 2026 | 1453 | +0.0619 | **-0.5076** | **+0.5694** | -0.0282 |
| `noFUND_GF` | HIST | 5495 | +0.1818 | **-0.0601** | **+0.2418** | -0.0366 |
| `noFUND_GF` | 2026 | 1453 | +0.1328 | **-0.6369** | **+0.7697** | -0.0263 |

## HIST → 2026 的改善, 按成分(自举 p 来自 `at_beta.py` 自己的检验)

| 臂 | Δ价格 | Δ共同+风格 | p | Δ逐名 | p | 共同份额 s |
|---|---|---|---|---|---|---|
| `BASE` | +3.2405 | **+1.4903** | 0.0421 | **+1.7502** | 0.0093 | 46.0% |
| `NONE` | +4.4314 | **+2.8767** | 0.0002 | **+1.5547** | 0.0309 | 64.9% |
| `noFUND` | -0.4635 | **-0.7265** | 0.1790 | **+0.2630** | 0.7161 | 156.7% |
| `noFUND_GF` | -0.0489 | **-0.5768** | 0.2761 | **+0.5279** | 0.4728 | 1178.6% ⚠分母近零 |

## 预注册判据(在装置里算的, 不是看出来的)

- **5.1_lead_reading_tailwind_lifts_any_book** — 判据 `|s_NONE - s_BASE| <= 15pp AND p_common < 0.05` ⇒ ****不支持****
  - {"s_BASE": 45.99038768751785, "s_NONE": 64.91617804052898, "gap_pp": 18.925790353011124, "similar_within_15pp": false, "p_common_NONE": 0.00019998000199980003, "significant": true}
- **5.2_alternative_mostly_name_specific** — 判据 `1 - s_NONE >= 65% AND p_name < 0.05` ⇒ ****不支持****
  - {"name_specific_share": 35.083821959471024, "p_name_NONE": 0.030896910308969103}
- **最终判决: UNDECIDED (PREREG 5.3)**
- `noFUND` 与 `noFUND_GF` 的 s 相差 **1021.8** 个百分点 ⇒ 该对照 **受门口径支配, 只作描述**(§5.4)

> NOT part of the pre-registered test, stated because it is what the numbers show: NONE's improvement is MORE common/style-driven than BASE's (64.9% vs 46.0%), not less, and its d_common is the most significant of any arm (p = 0.0002). My 5.1 criterion tested SIMILARITY to BASE; the coordinator's substantive wording was a DIRECTIONAL claim. See the result document: the gap between the two is a defect in my own operationalisation, not a property of the data.
