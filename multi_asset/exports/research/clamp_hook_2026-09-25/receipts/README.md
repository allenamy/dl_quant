> **Created:** 2026-09-25 15:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** hook cell result (run 2 `c4hook2` is the reported one; run 1 `c4hook` kept: same path and control, its launch receipt failed to write — receipts dir missing — after every check OK) | **Invalidated by:** a change of the engine pins / mirror, or of SER_EXT_NEWS2_s42X

# Read-only clamp hook, engine NC s42X (X axis 2022-06-30 → 2026-09-18T20Z), seed 0 of 32
Approval: lead ~15:2xZ ("只读钩子单格(基线, NC s42X)"), DECISION RULE step 1 rev 5 02a9fde80 mechanism control. Devices `../devices/` (1d9869b63, pipe rev 1 before run 2). Run gate: memgate OK with one other engine group running (this cell never takes the last slot); wall 94 s.
**PREREQUISITE CONTROL — PASS**: the hooked seed-00 series equals row 0 of the filed `SER_EXT_NEWS2_s42X.npz` (sha 074e8fb2…) **bitwise** for r / pnl / car / cst / unk / g / tau / hold / halt and the anchor axis ⇒ the hook had no behavioural effect. `BT_LAUNCH VERDICT=PASS label=smoke_c4hook2 runs=1 seeds=1`. Hook rows 6,508 = decided anchors (9,252 − 2,732 hold anchors … minus halts), distinct A 6,508, hook errors 0.

## Post-clamp book net / NAV in the engine (NAV = sizing_gross / 2.0), per decided anchor
| segment | n | mean | 5 % | 25 % | 50 % | 75 % | 95 % | median |net| | share with ≥1 clamped name |
|---|---|---|---|---|---|---|---|---|---|
| 2023H2 | 1,508 | +0.131 % | −0.068 | −0.000 | 0.000 | 0.000 | +0.157 | 0.000 % | 0.42 |
| 2024 | 1,933 | +0.026 % | −0.245 | −0.000 | 0.000 | +0.012 | +0.661 | 0.004 % | 0.65 |
| 2025 | 1,510 | −0.048 % | −1.412 | −0.028 | −0.000 | +0.005 | +1.134 | 0.011 % | 0.98 |
| 2026 (to 09-18T20Z) | 1,557 | −0.297 % | −1.920 | −0.053 | −0.000 | 0.000 | +0.625 | 0.006 % | 0.99 |
| all | 6,508 | −0.044 % | −1.421 | −0.009 | −0.000 | 0.000 | +0.846 | 0.003 % | 0.76 |
**Reading**: the engine carries the same mechanism (AST-identical code) and clamps on 76 % of decided anchors, but the post-clamp net is tiny and two-sided (median |net| ≤ 0.011 % of NAV in every year; 5–95 % band within ±2 %; 2026 mean −0.30 %, i.e. slightly SHORT). The live book's +2.2 % of NAV net long at EVERY NC-window anchor lies above the engine's 95th percentile in every year — the live effect comes from a specific, persistent live configuration (several stop-cooldown / exit names held as dust that the producer keeps wanting short), which the engine produces only occasionally. Not measured here: why the engine's held-untradable set differs from live (stop cooldown length, dust holdings, exit handling) — a named open question.

## Addendum 16:0xZ — hook v3 (c4hook4, control PASS): why the engine is net SHORT in the overlap
Per-name shift (post-clamp target − the reshape target, recomputed from the logged pre / post targets): the engine's net −0.4 … −2.6 % of NAV
in 09-16 12Z … 09-18 20Z is the SAME mechanism with the opposite sign — its stop-cooldown names IOST / TAC are held at a float residue
(≈ 0.0 USDT) while the producer targets them LONG (+1,650 / +9,690 USDT), so the clamp removes a long each anchor (IOST ≈ −2,000 … −2,500,
TAC ≈ −11,000 per anchor). Live's cooldown names (BCH / ENA / ZAMA) are shorts the producer keeps shorting ⇒ net long. Engine held exits
shift 0 (they are not in the reshape vector; closed within 1–2 anchors). Caveat: for force_flat (stopped) names the recompute over-states the
shift (they leave the reshape population in the executor); the cooldown numbers are unaffected. ⇒ the dust-pop rule would also move the
engine (its cooldown names are held at ≈ 0 < floor): the engine comparison cell is not expected to be "almost unchanged".
