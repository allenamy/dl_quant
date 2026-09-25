> **Created:** 2026-09-25 07:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** DRAFT release handbook, for the lead to review; the window time is not set (the lead reports to the user first) | **Invalidated by:** any of the items in §0 changing (tree, package, candidate commits), or a lead / user ruling

# Release handbook: M3 v2 + executor fix package B + producer C (durable writes / snapshot retention / k1 archive) — a code-only release on top of the NC s42 book

Governing records: this release **changes no model and no state format**. The NC release's `VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4…` still governs the models (King 700d9e7b / F10 3d7d050f); this release does not touch them. **M3 stays in shadow**: turning it on is a separate user word, and needs 2 consecutive clean anchors under the B7 v2 rule (b80f52b39).

## 0. Components and gates (as measured before the window)
| Component | Object | Status (receipt) |
|---|---|---|
| Producer tree | treeNC7 = `nc_derive_producer --release --m3-v2 --durable` (shadow_loop 52baf979, combo_stage 12a76de8, durable_io 34da08f8, snap_retention 8833da2c, combo_state_snapshot.sh 0a0b8401, combo_parity_replay.sh 7fa0881a; others == treeNC6) | receipts c_durable_2026-09-25 |
| Producer package | `nc_package_files.py` → 10 files + 4 archive moves (k1 three + com.hsy.sidecar.plist) | rehearsal 4f4c2ce3a |
| Executor candidate | clone m3v2_exec_20260925: dd486af (v2) → a777f86 (B-2) → 742706c (B-5) → 263f782 (re-vendor) → 6cc11cc (B-1) | not pushed |
| Research-repo upstream | 8bde2f8dc (engine/live: three modules durable + durable_io.py) — **held back, reverted in 47494838e** | E-0925-D |
| Gate 3′ (NC5→v2, rev1) | items 1/2 PASS 6/6; item 3 (census) must be re-judged in the post-install layout (rev2) | 1cfc1e5f6, 47e6400f9 |
| β parity | PASS 6/6 (RED detected) | 431537ee9 |
| NC6 vs NC7 | gate PASS 6/6: outputs byte-identical | 4d3fdad41 |
| Durable tests | tests_durable_io (executor) ALL PASS; test_c_durable_producer 17/17; test_snap_retention 14/14 | a777f86 / c0dda3192 / 68847d059 |
| Battery (v2+B) | 160 suites; only the two drift suites red, caused by the held upstream patch (against the staged upstream: no drift across 6) | a9f0533ee |
| E3 timing | NC6 / NC7 both PASS; durable adds +0.26 s to the producer (p50), slack ≈ 107 s | 1070933ba |
| Files-only install rehearsal | TEST_NC_INSTALL_FILES 15/15 (state untouched / archive sha / rollback byte-for-byte) | 4f4c2ce3a |
| **Still to do before the window** | F-2 rollback rehearsal (test_c_rollback_rehearsal, 09:00Z window); gate 3′ + rev1 + T1 re-judged in the post-install layout (`--archive-k1`); candidate battery all green with the upstream applied (can only run inside the window) | — |

## 1. Window W = [N+1:00, N+3:40] (from lead approval to completion; every step reports its verdict line + real exit code)
**W0 pre-check**: `venue_quiet_window.py` rc 0 and ≥ 60 min left; `df` free ≥ 15 GiB; executor running tree = 5d3029c; producer shas = baselines in the package contract (`nc_install_files.py preflight <PKG>` → `PREFLIGHT_PASS`); `launchctl list` does not contain com.hsy.sidecar.

**W1 stop the producer-side services** (same as the NC handbook A0, minus the sidecar, which is already unloaded; wait for the periodic jobs to finish on their own, never kill by name):
`com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity` → bootout; `ps` shows none of their processes; no parity lock.

**W2 apply the upstream patch first** (E-0925-D order): in the research repo, `git cherry-pick 8bde2f8dc` (or `git revert 47494838e`) → drift guard of the running tree **turns red here, as expected**. That is the window's first change; from here until W4 the executor must not have an anchor start (the window already guarantees this).

**W3 executor candidate**: fresh clone of ~/dl_quant_live (HEAD 5d3029c) → `git fetch <m3v2 clone> m3-v2 && git merge --ff-only FETCH_HEAD` (6cc11cc) → rsync state (A4 excludes) → `ops/safe_commit.sh` (offline full battery; **must be all green**: with the upstream applied, drift_gate / tests_drift_gate turn green) commits the producer release archive `ops/producer_release/20260925_m3v2_durable/{INSTALL_CONTRACT.json,PATCH_RECEIPT.json}` and pushes → `ff_running_tree.py <NEWSHA>` under anchor.lock → the running tree, origin/main and NEWSHA all equal → `nc_version_probe` after-W3.

**W4 producer files-only install**: `~/wide_shadow/venv/bin/python nc_install_files.py apply <PKG> <BK>` → `installed_not_started`; the receipt's state_manifest_diff == [], every dest == candidate, the four archive moves verified.

**W5 start** the four services (sidecar not started); shadowloop / combolive / combosnap / comboparity running.

**W6 version checks**: producer module shas == treeNC7; target_live field version `m3_beta_v2` (first anchor); executor `live/beta_overlay.py` VERSION `m3_beta_v2`; drift guard `no drift across 6`.

## 2. Acceptance (the first two anchors after the switch; read-only)
- B0–B6 of the NC handbook (version / identity / timing / snapshot + parity / dashboard), plus:
  - `nc_m3_selfcheck.py` (default `--expect-version m3_beta_v2`) → `M3_SELFCHECK <A> OK n=0`;
  - **B7 v2**: `b7v2_copy_inputs.sh` → `b7v2_fetch.py` (quiet window, within the pre-approved envelope) → `b7v2_compare.py` → `STATUS=CLEAN|PENDING|FAIL|UNDECIDED`; **2 consecutive CLEAN** go to the lead, who reports to the user; turning on needs the user's word.
- The first snap_retention run: `state/snap/retention.log` and snap.log have no `rc≠0`; within 14 days nothing is deleted (today's snapshots are all < 14 days old; the first trim happens once the window is full).
- Forward-log freshness (`nc_forward_freshness.py`).

## 3. Rollback (reverse order)
1. Stop the producer services (as W1).
2. `nc_install_files.py rollback <PKG> <BK>` → `rolled_back_not_started` (every file back to the pre-release bytes, the four archive moves reversed, state untouched).
3. Executor: roll the running tree back to 5d3029c (the NC handbook §R executor path, revert commit via safe_commit).
4. Research repo: `git revert` the upstream patch (drift guard back to `no drift across 5`).
5. Start the services; the first anchor goes through B0–B6.
- **Version-pairing hazard**: the v2 executor refuses a v1 field (version_mismatch), so M3 shadow would read "field refused" (no trading impact, but it alerts). Keep the executor and producer versions paired on rollback (both roll back together, or neither does).
