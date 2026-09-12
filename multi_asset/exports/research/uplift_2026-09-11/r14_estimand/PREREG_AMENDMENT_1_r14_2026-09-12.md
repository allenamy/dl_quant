> **创建:** 2026-09-12 | **状态:** FROZEN BEFORE ANY NUMBER FROM `r14_gap.py` | **修订对象:** `PREREG_r14_cost_estimand_2026-09-12.md` sha256 `bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904`

# PREREG AMENDMENT 1 — GATE G1 IS NOT REPRODUCIBLE AS WRITTEN; IT IS REPLACED BY A STRICTLY
# TIER-FREE FORM, AND A SECOND COUNT GATE IS ADDED

## Why (found by opening the producer, before running anything)

`infra1_cost/calib3.py` L8-11 assigns each fill row to a liquidity tier using
`wide_panel_4h_v2ext.npz` and `meta_newprod_v4.npz` — **both live only on pod2**, and L18/L27 add a
carry-forward extrapolation for anchors after 2026-08-31 20Z. L37 additionally **drops every row
whose `qv4h` is None**. I cannot reproduce that tier partition on this machine, so a per-tier
equality gate would be testing the availability of a pod artifact, not the correctness of my
instrument.

## What changes (the gate gets HARDER to pass in the dimension that matters, and honest in the one it cannot test)

**G1 (replaced).** Restricted to fills whose `floor(anchor_ts/14400)*14400` lies in
`[2026-08-01T04Z, 2026-09-11T04Z]`, the device must reproduce the **tier-free, notional-weighted**
maker and taker slip-vs-`mid_at_anchor` implied by the archived `tier_stats.json["all"]`:

    target_tag = Σ_t ( tag_slip_bps[t] · tag_slip_cov[t] · tag_nz[t] ) / Σ_t ( tag_slip_cov[t] · tag_nz[t] )   for tag ∈ {mk, tk}

to within **0.25 bps** each. The widened tolerance is the price of the un-reproducible tier/row
filter and is declared here, before the number. The device reports the achieved difference.

**G1b (NEW, added — this is the part that gets stricter).** The device must additionally reproduce
the archived **dedupe arithmetic exactly**: over the same day set, `n_raw` and `n_dedup` must match
`tier_stats.json`'s `n_raw = 81161` / `n_dedup = 33886` **exactly** when the device's day set is
restricted to the days the archived run saw (`20260801`..`20260911`). An off-by-one in the
last-wins supersede collapse is the single defect most likely to invalidate every number here, and
it is now tested by equality rather than by tolerance.

**G1c (NEW).** The archived overall maker/taker slip must also be reproduced when my computation is
restricted to symbols present in the 829 panel axis — the closest available proxy for calib3's
`qv4h is not None` filter. Both readings are reported; neither is selected after the fact, the
PRIMARY remains the unrestricted one.

Nothing else in the prereg changes. In particular §2 (K=7), §3 (windows/units/CI), §5 (decision
rule) and §7 (empty env whitelist) are untouched.
