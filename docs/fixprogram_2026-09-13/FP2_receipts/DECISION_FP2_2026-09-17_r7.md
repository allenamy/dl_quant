# FP2 换装建议(F03 决策装置 v4; AMENDMENT 7 规则; 闭包 F2 / 冻结窗 F3)— NO_SWAP

> profile formal · δ 0.05 · 席位 dyn · 种子 42,2027 · 窗 W_ALPHA,KING_LIVE · 冻结窗 2022-06-30T00:00:00Z → 2026-08-30T20:00:00Z(KING_LIVE 自 2024-01-01T00:00:00Z) · 候选臂 A1 · 本装置 sha 14fc96e550c5 · 2026-09-18T00:31:01Z

**G1′ 非劣性: UNDECIDED**

| 格 | Δg | CI95 | n | 下界 > −δ | 下界 > 0 | 上界 < −δ |
|---|---|---|---|---|---|---|
| W_ALPHA/s42 | +0.0571 | [-0.0431, +0.1572] | 9138 | True | False | False |
| KING_LIVE/s42 | +0.0894 | [-0.0614, +0.2517] | 5838 | False | False | False |
| W_ALPHA/s2027 | +0.0332 | [-0.0604, +0.1311] | 9138 | False | False | False |
| KING_LIVE/s2027 | +0.0520 | [-0.0996, +0.2108] | 5838 | False | False | False |

**G2 逐年(点估计规则, 非逐年统计非劣证明; 差于 A0 超过 δ 的年数 ≤ 1 且不含 2026): True**

- s42: 劣年 无 ⇒ True · 2022 +0.000 · 2023 +0.000 · 2024 -0.007 · 2025 +0.204 · 2026 +0.062
- s2027: 劣年 无 ⇒ True · 2022 +0.000 · 2023 +0.000 · 2024 +0.002 · 2025 +0.117 · 2026 +0.030

**G3 出口门 v2(chain require, recorded_extras; 同四书): True** (PASS=True, arm=A1, require=PASS (BUNDLE_export, 2026-09-17T14:40:09Z, self 16e9cc32369d approved, 28 inputs verified (0 recorded beyond the caller's declaration, located from the receipt')

**建议: NO_SWAP** — G1′ = UNDECIDED

判官 JUDGE_v4.json 只作信息记录。建议不是动作: 换装以用户对具体 bundle sha + F10 np sha 的字为准。
