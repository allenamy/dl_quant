> **Created:** 2026-09-25 15:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator; drafted at the lead's request) | **Status:** DRAFT — NOT frozen, nothing run. Book-behaviour change ⇒ the final ruling is the user's. The decision thresholds in §5 are left BLANK on purpose: I found the effect and would implement the arm, so I must not author the criterion (memory rule "criterion author must have no stake"); the lead / an independent reviewer fills §5 and freezes the document (sha) before any number | **Invalidated by:** a change of apply_withhold_and_reshape / clamp_held_untradable / reshape_after_withhold, or of the engine mirror

# Pre-registration DRAFT: re-neutralise the tradable names after the clamp

## 1. The effect (measured, receipts `multi_asset/exports/research/lossdecomp_2026-09-25/receipts/r25_03_layered*`, a221bb946 / 98d935add)
The executor neutralises the book BEFORE the clamp (scheduler/anchor_loop.py `apply_withhold_and_reshape`: POP → RESHAPE → CLAMP). A name that
is HELD but untradable (per-name stop cooldown, held exit, venue zero cap…) is not popped, so it receives a reshape target; the clamp then pins
it at its held size and — by design, L366–L372 — does not re-absorb the difference into the other names. Live, NC window: the book's net after
the clamp is +2,463 … +2,538 USDT at every anchor (≈ +1.1 % of gross, the executor's own `clamped_after_reshape.net_shift_usdt`), and the held
book is net long +0.8 … +2.7 % of NAV. Old window (46 anchors): L2 net −570 … +2,708 (venue caps on longs pull the other way).

## 2. Does the research engine produce the same effect?
By construction yes: the engine (news2 `bt_hist_sim31.py` → `exec_sim.Sim.on_anchor`, sha 29679672) imports `scheduler.anchor_loop` from the
executor mirror of tree 409ea16, and `apply_withhold_and_reshape`, `clamp_held_untradable`, `withhold_pop` and `signal/legs.reshape_after_withhold`
are AST-identical in 409ea16 and the running 96acfdd (unparsed sha 67cc2010 / b9f096e9 / 43a5b860; checked 2026-09-25). **The engine does not
record the reshape report per anchor** (it keeps a digest), so the per-year distribution of the post-clamp net / NAV in the engine is NOT yet
measured. Measuring it needs a one-path engine run with a read-only hook that appends `rs["clamped_after_reshape"]` per anchor (≈ the
baseline arm of §3 with the hook on) — a pod2 job under the "one cell at a time" run gate; to be approved before it runs.

## 3. Arms (both on the same engine, config X s42 extended axis, 32 paths, same seeds)
- **Baseline**: current code (POP → RESHAPE → CLAMP; residual not absorbed).
- **Arm R (re-neutralise)**: after the clamp, the net `n = Σ target` is removed from the TRADABLE names only (not popped, not clamped, not
  force_flat): each tradable name i gets `− n · |t_i| / Σ_tradable |t_j|` (proportional to its own size, so no zero-target name gains a weight
  and signs cannot flip for n small relative to the book), then the tradable names are rescaled so the book's gross equals the sizing gross
  again; the clamped names stay pinned. Everything downstream (venue cap, min notional, planner) unchanged. One pass, reported like the
  existing reshape (net before / after, max name delta, floor crossings).
- The arm changes only the executor's target composition; producer targets and every other rule are identical.

## 4. Must-report (both arms, every year 2023H2 / 2024 / 2025 / 2026 and the whole axis; the 2026 segment = 2026-01-01 → 09-18T20Z per the
DECISION RULE revision 3, the frozen-SEG truncation reported beside it)
- book dbar (bps / anchor) with its SE, and the difference arm − baseline with its paired SE (same paths);
- gross (mean, and the 5 / 50 / 95 % of per-anchor gross / NAV);
- turnover (per anchor, mean and 95 %), and the fee / funding / slippage channels;
- post-clamp net / NAV per anchor: distribution (5 / 25 / 50 / 75 / 95 %) and the share of anchors with a clamp at all;
- max drawdown and the worst 9-day window;
- the number of anchors where the arm's re-neutralisation moved any single name by more than 1 % of its own target (a size-flip guard).

## 5. Decision rule — TO BE WRITTEN BY A NO-STAKE AUTHOR, FROZEN (sha) BEFORE ANY NUMBER
- primary quantity and threshold: ______
- per-year sign condition: ______
- turnover / gross guard: ______
- what "no difference" leads to (keep the current design, which is the documented choice at L366–L372): ______

## 6. Scope notes
- Book-behaviour change: nothing is deployed on a PASS; the result goes to the user.
- The live effect is ≈ +1 % of gross net long; with the book's measured daily BTC beta near zero the expected P&L effect is small and sign-
  uncertain — the pre-registration is about neutrality as a design property, and the criterion should say whether "neutral as designed" alone
  is enough reason or whether a dbar difference is required.
