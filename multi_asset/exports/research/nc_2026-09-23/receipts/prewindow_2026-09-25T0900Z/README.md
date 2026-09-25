> **Created:** 2026-09-25 09:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** pre-window gates for the v2 + B + C release, all PASS | **Invalidated by:** treeNC5 / treeNC7 / package change, or any gate device change

# Pre-window gates, 09:00Z quiet window, 2026-09-25 (sequential; runner `prewindow_0900Z.sh`; log `PREWINDOW_RUN.log`)
Trees: old = treeNC5 (== production: shadow_loop a68c7a5f, combo_stage 363dd8c8), new = treeNC7 (shadow_loop 52baf979, combo_stage 12a76de8).
Disk at start 39 GiB free; `venue_quiet_window` OPEN, 159.8 min left. Nothing calls the exchange; all writes under ~/cc_tmp/nc_20260923/prewindow_20260925T0900Z.

| # | Gate | Command (verbatim in PREWINDOW_RUN.log) | Verdict line | rc |
|---|---|---|---|---|
| 1 | F-2 rollback rehearsal, run 1 (device 79258735c) | `test_c_rollback_rehearsal.py treeNC5 treeNC7 1790280000 …/f2` | `C_ROLLBACK FAIL` — the 7 behaviour checks green, every compared file byte-identical; the ONLY red was the device's own version-pair assertion, which read the producer's king file `state/target_live/<A>` (measured `[None, None]`: that file carries no beta field) instead of the combo output `state/target_live_PARITY/<A>` (measured m3_beta_v2 new / m3_beta_v1 old). A device defect, not a finding about the trees | 1 |
| 1′ | F-2, run 2 (device revision 003575004, committed before the run) | `test_c_rollback_rehearsal.py treeNC5 treeNC7 1790280000 …/f2_run2` | `C_ROLLBACK PASS` {new/old producer A1, new/old combo A1, d_same_bytes, rollback: old producer A2 on new state + old combo A2, forward: new loads old state A2} all true | 0 |
| 2 | Gate 3′ in the POST-INSTALL layout (`--archive-k1`), 7 anchors 1790236800…1790323200 | `nc_v2_nonbeta_gate.py treeNC5 treeNC7 …/g3p --archive-k1` | `NC_V2_NONBETA_GATE FAIL anchors=7` (literal criterion; meta_json provenance fields of dlw_fea82 / f8_fea89 differ by construction, every array identical — same as run2 of 09-25 05:03Z) | 1 |
| 3 | rev1 judge on that run | `nc_v2_nonbeta_gate_rev1.py treeNC5 treeNC7 …/g3p …` | `NC_V2_NONBETA_GATE_REV1 PASS anchors=7 written_utc_ruling=w1`; item 3 census over 15 executed files (post-install layout): 12 channel-0 subscripts, non-whitelisted 0 | 0 |
| 4 | test_m3_v2_ret5 FULL (T1–T5), `--installed` = moved-layout copy of the installed code set (k1 three files in fea171/_archive_2026-09-25/; sums in installed_moved_layout_SHA256SUMS.txt) | `test_m3_v2_ret5.py treeNC7 treeNC5 --installed …/installed_moved` | `TEST_M3_V2_RET5 PASS`, 16/16; T1 census 12 channel-0 subscripts in 14 files | 0 |
| 5 | β parity (SERVED == DIRECT) on the gate run | `nc_v2_beta_parity.py treeNC7 …/g3p …` | `NC_V2_BETA_PARITY PASS anchors=7`; baseline GREEN every anchor; RED control (clipped input) 7 names differ ⇒ DETECTED | 0 |

Per-anchor sandbox outputs (target_combo, target_live_PARITY, state_H_*, mini data) are listed with sha256 in g3p_sandbox_outputs_SHA256SUMS.txt; the sandboxes are deleted after this commit.
