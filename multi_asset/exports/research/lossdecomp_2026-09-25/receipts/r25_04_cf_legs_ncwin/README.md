> **Created:** 2026-09-25 17:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-04 result, NC window (device cf_legs.py rev 0, d717852cf) | **Invalidated by:** a change of the snapshots / ledger / price snapshot

# Counterfactual leg contribution, NC window (7 anchors 09-24 08Z … 09-25 08Z, one chain from production's state at 09-24 04Z)
Baseline green first: the base arm (unmodified treeNC5 combo_stage in the parity-gate sandbox) reproduces production target_live **bitwise at all 7 anchors**.
Contribution = P&L(base book) − P&L(book with the leg removed), each through the executor's reshape and recorded clamps, priced with rr per readback interval (all 7 priced):
| leg | Σ USDT (7 anchors) | per anchor |
|---|---|---|
| funding momentum | **−734.8** | +24.7, −29.1, −213.5, +379.1, −478.4, +196.3, −613.9 |
| King | +96.3 | +9.1, −18.1, +34.1, −28.5, +95.9, −63.3, +67.1 |
| F10 | +20.8 | +7.7, −13.6, +32.6, −12.8, −0.5, +3.4, +4.0 |
Base book P&L Σ −3,183.0 (−12.3, −932.9, −73.7, +173.7, −786.9, −722.3, −828.8). Contributions are not additive (the reshape re-neutralises and the legs interact; memory: three signals are not additive). No significance claim on 7 anchors.
Compared with the regression PROJECTION (leg_attribution, R25-04 says: projection, not cash): funding −2,742 over 6 anchors there vs −734.8 over 7 here — the projection overstated the funding leg's cash contribution by several times.
