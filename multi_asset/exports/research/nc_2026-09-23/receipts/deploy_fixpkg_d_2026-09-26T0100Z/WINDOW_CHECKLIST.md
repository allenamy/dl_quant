> **Created:** 2026-09-26 00:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** window checklist, frozen before the window (user ruling via the lead: release fix-pkg-d in 01:00–03:40Z; M3 opens only after the package, on a separate request) | **Invalidated by:** a lead ruling; any change to the candidate (fix-pkg-d ee455fa + release record)

# Window checklist — fix-pkg-d, window W = [01:00, 03:40]Z (N = 00Z)
**Scope: EXECUTOR ONLY.** The producer is not touched: no producer file install, and no producer service is stopped or restarted. So the previous release's W1 / W4 / W5 are not part of this window, by design.

Lead rules (2026-09-26 ~00:2xZ):
- The release comes first. Segment 1 of the counterfactual runs after the release only if ≥ 70 min remain, else in the 05:00Z window. No B7 anchor 3.
- Order: W0 re-measure → upstream patch R25-10 → candidate battery **ALL GREEN (expected 166/166)** → safe_commit → fast-forward → upstream pair check (durable_io COMPARED_EQUAL; candidate and running tree) → running processes run the new tree.
- **Any red ⇒ stop, restore in the mirror order (upstream first, then executor), report.** No code fixes inside the window.
- Not complete by **03:25Z ⇒ abandon**, leaving production as it was.
- One line to the lead after every step.

Variables:
- `QR=~/Desktop/quant_research`; `RC=$QR/multi_asset/exports/research/nc_2026-09-23`; `RL=$RC/receipts/deploy_fixpkg_d_2026-09-26T0100Z`
- `XC=~/cc_tmp/fixpkg_d_20260925/exec` (isolated clone of GitHub main; branch fix-pkg-d = 96acfdd + 9 commits, head ee455fa)
- `PAIR="/usr/bin/python3 $RC/devices/v2c_upstream_pair_check.py"`; `HELD=$RC/receipts/fixpkg_d_2026-09-25/HELD_UPSTREAM_durable_io_R25_10.diff`

Pre-window controls, done at 00:27Z:
- candidate vs unpatched upstream = RED, durable_io DIFFERENT (research 34da08f8, candidate d9b3cf04);
- running 96acfdd vs unpatched upstream = PASS, n=6;
- HELD applied to a temp copy of the research durable_io gives sha d9b3cf04… == the candidate's live/durable_io.py.

## W0 re-measure (from 01:00Z; stop if any fails — nothing has changed yet)
- `date -u`; `venue_quiet_window.py --json` → open, ≥ 60 min left.
- 00Z executor anchor: `anchor_runs.log` shows `anchor done rc=0`; no run_anchor process (`ps` by PGID).
- In-flight processes listed with PGIDs; nothing of mine running.
- `df -g /` free ≥ 15 GiB.
- `git -C ~/dl_quant_live rev-parse HEAD` == `git ls-remote … refs/heads/main` == 96acfddec11e….
- Research repo: engine/live clean; no `.git/index.lock`; `git apply --check $HELD` OK.

## W2 upstream first (E-0925-D)
- `cd $QR && git apply $HELD && git commit -- multi_asset/engine/live/durable_io.py` → U2.
- `git show --stat U2` = 1 file.
- Expected consequence, measured and recorded: the running 96acfdd guard now reports DRIFT on durable_io.

## W3 executor
```
cd $XC && git checkout main && git merge --ff-only fix-pkg-d      # main = ee455fa (96acfdd + 9)
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
/usr/bin/python3 -c 'import sys;print(sys.prefix)'; echo ACCEPT_PY=${ACCEPT_PY:-<unset>}
(cd $XC && bash ops/safe_commit.sh "fix-pkg-d release: dust pop before reshape (D), H1 finiteness gate, durable_io split (R25-10, upstream first), drift guard research-copy-missing (R25-12), R25-01 tier-1 unknown-is-not-zero (7 sites); executor only; quant_research deploy_fixpkg_d_2026-09-26T0100Z W3" docs/RELEASE_fixpkg_d_2026-09-26.md) ; echo "rc=$?"
NEWSHA=$(git -C $XC rev-parse HEAD)
$PAIR $XC --expect-n 6 --out $RL/PAIR_CHECK_after_battery.txt              # PASS compared_equal=6 durable_io=COMPARED_EQUAL
ps -A -o pid=,pgid=,args= | grep run_anchor | grep -v grep                   # must be empty
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA    # FF_OK (holds anchor.lock)
$PAIR ~/dl_quant_live --expect-n 6 --out $RL/PAIR_CHECK_after_ff.txt        # PASS compared_equal=6 durable_io=COMPARED_EQUAL
```
Pass conditions:
- safe_commit rc 0, with its battery **ALL GREEN 166/166** (`$XC/state/_safe_commit_acc.log`).
- Push 96acfdd..NEWSHA.
- Both pair checks PASS.
- FF_OK.

## W6 verification: the running tree is the new tree (E-0825-F)
- `git -C ~/dl_quant_live rev-parse HEAD` == origin/main == GitHub main == NEWSHA.
- Code area clean.
- `git diff --name-only 96acfdd NEWSHA` == the release's files.
- `config/book.json` bytes == 96acfdd (no book change).
- The running tree's drift guard → `no drift across 6`.
- Code markers present: `n_dust_popped` in scheduler/anchor_loop.py; `DurableWriteReplacedNotDurable` in live/durable_io.py.
- Executor jobs:
  - `com.dlquant.live.anchor` starts a fresh `/usr/bin/python3 scheduler/run_anchor.py` per anchor ⇒ no executor process holds old code (nosleep = caffeinate; icmonitor periodic, not running).
  - Verified again at 04Z: the run_anchor process started after the FF, and `inspect_anchor` shows the new fields.
- Producer untouched: `~/wide_shadow` combo_stage / shadow_loop shas unchanged across the window; combolive/shadowloop PIDs unchanged.

## 04Z first-anchor acceptance (lead additions)
Standard `accept_anchor_v2.sh`, plus:
- (a) `n_dust_popped` / `dust_popped_names` in the anchors record and the report;
- (b) post-clamp net / NAV back to ≈ 0, compared with the 08Z fixture expectation (tests_fixtures/dust_pop/reshape_A1790324640.json; the engine cell's post-clamp |net| p95 was 0.08%);
- (c) no order carrying a quantity for any popped name.

## R — restore (mirror order)
1. Executor, only if pushed:
   - new isolated checkout of GitHub main (= NEWSHA) → `git revert --no-commit 96acfdd..HEAD`, then `git diff --stat 96acfdd` must be empty;
   - rsync state → `safe_commit.sh "<revert msg>" <every file in git diff --name-only 96acfdd NEWSHA>`. Its battery runs on the 96acfdd code; the upstream must be reverted FIRST (step 2) for that battery to be green.
   - `ff_running_tree.py <REVSHA>` → running tree code == 96acfdd.
   - If pushed but not fast-forwarded, the running executor is unchanged; the revert can then be done in the next quiet window.
2. Upstream, only if W2 ran: `cd $QR && git revert --no-edit <U2>`; then the running 96acfdd guard → `no drift across 6`.
   **Order when both are needed:** upstream revert (2) first, then the executor revert (1), whose battery needs the unpatched upstream.
3. Abandon at 03:25Z if W6 is not verified. The producer needs no restore (untouched).
