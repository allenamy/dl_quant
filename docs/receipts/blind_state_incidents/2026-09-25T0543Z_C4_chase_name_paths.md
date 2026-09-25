> **Created:** 2026-09-25 05:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** blind-state incident record (self-reported; the lead has acknowledged it) | **Invalidated by:** none

# Blind-state incident: chase_experiment per-name paths printed by accident (C-4, 2026-09-25 ~05:43Z)

- **When / what was done:** while establishing fact A for anchor A1790267040 (2026-09-24T16:24Z), I ran a read-only script over that anchor's row in
  `~/dl_quant_live/state/live/pilot_log/20260924/anchors.jsonl`. It recursively searched every string field for "ETHUSDT" and printed the matching paths.
- **What was exposed:** the output contained two paths under `chase_experiment`: `/chase_experiment/randomised_over[0] = ETHUSDT` and
  `/chase_experiment/neutral_only/skip[0] = ETHUSDT`. That is, whether this one name was inside the experiment's randomisation / neutral list at
  that anchor. No arm outcome, fill or P&L-type field was printed. The per-arm fields in the order rows (chase_arm / chase_arm_assigned /
  placement_arm / placement_eps / requote_arm / requote_p) were explicitly excluded from printing in the same step.
- **Handling:** not used in any conclusion, not passed on, not written into any receipt (this record only states the paths and the one name).
- **Cause (class):** a "search the whole row by string" instrument has no blind-state whitelist; it walks into experiment sub-trees. Rule from now on: before recursively
  scanning a live execution record, exclude the `chase_experiment` sub-tree and every `*_arm*` key first.
