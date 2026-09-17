# FP2 换装建议(F03 决策装置, AMENDMENT 7 规则; R04/R05/R06/R08 加固)— UNAVAILABLE

> profile formal · δ 0.05 · 席位 dyn · 种子 42,2027 · 窗 W_ALPHA,KING_LIVE · 候选臂 A1 · 本装置 sha 474c7969b1f2 · 2026-09-17T12:06:36Z

**UNAVAILABLE 原因**

- export receipt PASS=False failed=['E6_books_config', 'E8_books_content', 'E9_gross_band_vs_baseline']
- G1 cell not a finite measurement: A1-A0/dyn/s42 W_ALPHA dg=0.05714401998457054 ci=[-0.04313164441960712, 0.15717593331266422] n=9138 n_days=None
- G1 cell not a finite measurement: A1-A0/dyn/s42 KING_LIVE dg=0.08944536735508836 ci=[-0.061363346962513214, 0.25174011866758494] n=5838 n_days=None
- G1 cell not a finite measurement: A1-A0/dyn/s2027 W_ALPHA dg=0.03323899174451082 ci=[-0.060369199273935074, 0.13105668962750983] n=9138 n_days=None
- G1 cell not a finite measurement: A1-A0/dyn/s2027 KING_LIVE dg=0.052027733223936244 ci=[-0.09961008373710376, 0.21082536159099965] n=5838 n_days=None

**G1′ 非劣性: None**

| 格 | Δg | CI95 | n | 下界 > −δ | 下界 > 0 | 上界 < −δ |
|---|---|---|---|---|---|---|
| W_ALPHA/s42 | — | — | — | — | — | — |
| KING_LIVE/s42 | — | — | — | — | — | — |
| W_ALPHA/s2027 | — | — | — | — | — | — |
| KING_LIVE/s2027 | — | — | — | — | — | — |

**G2 逐年(点估计规则, 非逐年统计非劣证明; 差于 A0 超过 δ 的年数 ≤ 1 且不含 2026): True**

- s42: 劣年 无 ⇒ True · 2022 +0.000 · 2023 +0.000 · 2024 -0.007 · 2025 +0.204 · 2026 +0.062
- s2027: 劣年 无 ⇒ True · 2022 +0.000 · 2023 +0.000 · 2024 +0.002 · 2025 +0.117 · 2026 +0.030

**G3 出口门 v2(绑定同四书、合同、装置): False** (PASS=False, arm=A1)

**建议: UNAVAILABLE** — export receipt PASS=False failed=['E6_books_config', 'E8_books_content', 'E9_gross_band_vs_baseline']; G1 cell not a finite measurement: A1-A0/dyn/s42 W_ALPHA dg=0.05714401998457054 ci=[-0.04313164441960712, 0.15717593331266422] n=9138 n_days=None; G1 cell not a finite measurement: A1-A0/dyn/s42 KING_LIVE dg=0.08944536735508836 ci=[-0.061363346962513214, 0.25174011866758494] n=5838 n_days=None; G1 cell not a finite measurement: A1-A0/dyn/s2027 W_ALPHA dg=0.03323899174451082 ci=[-0.060369199273935074, 0.13105668962750983] n=9138 n_days=None; G1 cell not a finite measurement: A1-A0/dyn/s2027 KING_LIVE dg=0.052027733223936244 ci=[-0.09961008373710376, 0.21082536159099965] n=5838 n_days=None

判官 JUDGE_v4.json 只作信息记录。建议不是动作: 换装以用户对具体 bundle sha + F10 np sha 的字为准。
