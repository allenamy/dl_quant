# Vendored from the production repo — do not edit here

> **创建:** 2026-07-27 02:40 UTC | **Session:** 0C | **状态:** final | **作废条件:** 两棵树合并为一, 或 team-lead 改判上游方向

## Direction: production → research

`dl_quant_live/live/` is the **upstream** for the files listed below; `multi_asset/engine/live/`
is a **vendored consumer**. This is the reverse of the default arrangement (research → server) and
it is deliberate: the pilot protocol freezes these implementations by hash, and the frozen record
lives with the production stack. Editing the copy here does not change the frozen implementation —
it only creates a second ruler.

| file | sha256 (first 16) | vendored |
|---|---|---|
| `pilot_metrics.py` | `9a033684be07bcd8` | 2026-07-27 |
| `reconcile.py` | `fd6b4b60b5fcf3a3` | 2026-07-27 |

Both are **byte-identical** to their upstream on purpose. A vendoring header would have been the
obvious thing to add and would have destroyed exactly the property that makes the copy checkable.

## Why these two, and why together

`pilot_metrics.py` was previously a **separate 329-line implementation** of the same M1–M6 names
(sha `cfd1de1b`). The two disagreed in two ways:

1. **No completeness accounting.** 24 keys — `measurement_complete`, `n_unmeasured_slippage`,
   `n_unmeasured_fee`, `n_excluded_unknown_fill`, the `protective_flatten_cost` block, … — simply
   did not exist in the research-side output. §2.5.7's eligibility rule names
   `measurement_complete`, so the protocol's criterion was **unevaluable** against the shadow's
   numbers. Not "different value" — absent.
2. **`m5_weight_fidelity`.** The upstream routes through `reconcile.signed_fills_by_anchor`, the
   shared signed-fills aggregation; the research copy hand-rolled the same walk. `reconcile.py`
   did not exist in this tree at all, so the vendoring scope is two files, not one.

## ⚠ The convention had to move FIRST

Vendoring alone would have produced silently wrong numbers. `orders.filled_notional` was written
here as an **unsigned magnitude** while the venue-real log writes it **signed** — measured, not
assumed (`exports/eda/assert_fill_sign_convention.py`). Each implementation was correct on its own
log and 16–33× wrong on the other, and the drop-in ran clean and schema-compatible while doing it.

Measured on a freshly-written **signed** tree:

| implementation | M5 `venue_vs_inferred_drift` | M1 `n_filled_orders` |
|---|---:|---:|
| upstream `9a033684` (vendored) | **0.00** | **2767** |
| old research copy `cfd1de1b` | 5092.06 | 1384 — **dropped every filled sell** |

Zero drift is the structurally correct answer for the simulator, whose position readback is derived
from its own fills. The old copy's `if f <= 0: continue` discards negative sells, halving the
sample. ⇒ **`shadow_pilot_log.py` now writes `sgn * filled` and asserts it at write time; the
vendoring lands in the same change.** Days written before 2026-07-27 keep the old convention and
are not rewritten — see `SHADOW_SIGN_CUTOVER_DAY`.

## Rule

Any change to these files is made **upstream** and re-vendored, and the re-vendoring updates both
the table above and the drift gate's fingerprints. Never patch the copy: the whole reason the
protocol can pin a hash is that exactly one implementation exists.
