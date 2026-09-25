> **Created:** 2026-09-25 10:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** window checklist, frozen before the window (user ruling relayed by the lead: release v2 + B + C in the 13:00–15:40Z quiet window) | **Invalidated by:** a lead ruling; any package / candidate change

# Window checklist — DEPLOY_v2_durable_2026-09-25, window W = [13:00, 15:40]Z (N = 12Z)
Lead rules (2026-09-25 ~10:0xZ): (1) re-measure before opening, with timestamps: quiet-window boundary (the 12Z executor anchor has finished trading, time ≥ N+1:00), disk, in-flight processes by PGID; (2) order: upstream patch → candidate battery W3 all green (only via ops/run_acceptance_offline.sh, interpreter sys.prefix reported) → safe_commit → isolated-checkout switch; **any red ⇒ stop, restore in the mirror order (upstream first, then executor), report; no code fixes inside the window**; (3) switch not complete by **15:25Z ⇒ abandon**, restore, report; (4) after the switch: running processes run the new tree (E-0825-F); 16Z anchor acceptance (inspect_anchor first) + B7 v2 first shadow anchor under the frozen rule; **M3 hedge stays off (shadow)**; (5) no exchangeInfo call; (6) **every abandon / rollback path ends with the four producer services restarted on the OLD tree and verified: after-w5 probe against the OLD package = OK n=0 and the running processes run the old tree — complete by 15:40Z** (the 16Z producer runs from N+0); (7) the pre-run battery: any red other than the two drift suites ⇒ the window is not opened.
One line to the lead after every step.

Variables: `QR=~/Desktop/quant_research; RC=$QR/multi_asset/exports/research/nc_2026-09-23; PKG=~/cc_tmp/nc_20260923/package_v2c_20260925 (contract 9af4b672); PKG_OLD=~/cc_tmp/nc_20260923/package_NC; XC=~/cc_tmp/deploy_v2c_20260925/exec; BK=~/cc_tmp/deploy_v2c_20260925/bk; RL=$RC/receipts/deploy_v2c_2026-09-25T1300Z; PROBE="/usr/bin/python3 $RC/devices/v2c_version_probe.py"; PYP=~/wide_shadow/venv/bin/python; U=8bde2f8dc`

## W0 re-measure (from 13:00Z; stop if any fails — nothing has changed yet)
- `date -u`; `/usr/bin/python3 $QR/multi_asset/exports/research/common/venue_quiet_window.py` → OPEN, ≥ 60 min left
- 12Z executor anchor finished: `grep '2026-09-25T12' ~/dl_quant_live/state/anchor_runs.log | tail -3` shows `anchor done rc=0`; no run_anchor process
- in-flight processes by PGID: `ps -A -o pid=,pgid=,lstart=,args= | egrep 'run_anchor|shadow_loop_v3|combo_stage|combo_state_snapshot|combo_parity|safe_commit|run_acceptance|sidecar' | grep -v egrep` (listed with PGIDs; nothing of mine running)
- `df -g /` free ≥ 15 GiB
- executor: `git -C ~/dl_quant_live rev-parse HEAD` == `git ls-remote …/dl_quant_live.git refs/heads/main` == 5d3029c0411b…
- producer: `$PYP $RC/devices/nc_install_files.py preflight $PKG` → PREFLIGHT_PASS
- sidecar: `launchctl list | grep com.hsy.sidecar` → empty
- baseline of the restore check: `$PROBE after-w5 $PKG_OLD $RL/receipt_pre.json --out $RL/VP_pre_after_w5_OLD.txt` (receipt_pre.json = {"completed_utc": "2026-09-24T05:00:00Z"}) → OK n=0

## W1 stop the four producer-side services (never kill by name; wait for periodic jobs to finish)
```
for L in com.hsy.combosnap com.hsy.comboparity; do for i in $(seq 1 60); do launchctl print gui/$(id -u)/$L 2>/dev/null | grep -q 'pid = ' || break; sleep 1; done; done
for L in com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity; do launchctl bootout gui/$(id -u)/$L; done
ps aux | egrep 'shadow_loop_v3|combo_stage|combo_live_daemon|combo_state_snapshot|combo_parity' | grep -v egrep ; echo "(must be empty)"
ls ~/wide_shadow/state/snap/.parity.lock 2>/dev/null ; echo "(must be empty)"
```
Record T_W1 = `date -u +%FT%TZ` into `$RL/receipt_W1.json` {"completed_utc": T_W1} (the restore check's reference time).

## W2 upstream patch first (E-0925-D)
`cd $QR && git cherry-pick 8bde2f8dc` → U2 = new sha; `git show --stat U2` = the 4 engine/live files. (iCloud: if `.git/index.lock` exists, check `lsof` for its holder and wait; never delete a live lock.)
Expected consequence: the RUNNING executor's guard `/usr/bin/python3 ~/dl_quant_live/ops/check_upstream_drift.py` now reports DRIFT (measured and recorded).

## W3 executor
```
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
/usr/bin/python3 -c 'import sys;print(sys.prefix)'        # the battery interpreter (/usr/bin/python3, ACCEPT_PY unset)
(cd $XC && bash ops/safe_commit.sh "v2 + B + C release: M3 beta_overlay v2 (rr channel), B-1 halted-anchor class H1, B-2 durable state writes (+ re-vendor, A-set 6), B-5 drift_gate fail-fast; producer release archive 20260925_m3v2_durable (contract 9af4b672); quant_research DEPLOY_v2_durable_2026-09-25 W3" ops/producer_release/20260925_m3v2_durable/INSTALL_CONTRACT.json ops/producer_release/20260925_m3v2_durable/PATCH_RECEIPT.json) ; echo "rc=$?"
NEWSHA=$(git -C $XC rev-parse HEAD)
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA ; echo "rc=$?"
$PROBE after-w3 $NEWSHA ops/producer_release/20260925_m3v2_durable/INSTALL_CONTRACT.json ops/producer_release/20260925_m3v2_durable/PATCH_RECEIPT.json --out $RL/VP_after_w3.txt
```
**Upstream pair check (lead 2026-09-25 ~10:1xZ; EXPECTED N = 6 written here before the window)**: after the battery, `/usr/bin/python3 $RC/devices/v2c_upstream_pair_check.py $XC --expect-n 6 --out $RL/PAIR_CHECK_after_battery.txt` and after the ff `… v2c_upstream_pair_check.py ~/dl_quant_live --expect-n 6 --out $RL/PAIR_CHECK_after_ff.txt` → `UPSTREAM_PAIR_CHECK PASS compared_equal=6 manifest_entries=6 expected=6 durable_io=COMPARED_EQUAL`; anything else = RED ⇒ restore. (drift_gate's own output cannot show this: it prints the manifest line count and skips a missing upstream file — measured: durable_io absent / present-equal ⇒ the identical line `no drift across 6 … all covered` rc 0.) Controls before the window: candidate vs unpatched upstream = RED (durable_io MISSING_RESEARCH, three DIFFERENT); running 5d3029c vs unpatched upstream = PASS n=5.
Pass: safe_commit rc 0 with the battery all green (`$XC/state/_safe_commit_acc.log` summary + failing suites none), FF_OK, after-w3 OK n=0.

## W4 producer files-only install
`$PYP $RC/devices/nc_install_files.py apply $PKG $BK/install` → `installed_not_started`; `$PROBE after-w4 $PKG $BK/install/NC_FILES_INSTALL_RECEIPT.json --out $RL/VP_after_w4.txt` → OK n=0

## W5 start + verify the new tree runs (E-0825-F)
```
for L in com.hsy.comboparity com.hsy.combosnap com.hsy.combolive com.hsy.shadowloop; do launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/$L.plist; done
ps eww -p $(cat ~/wide_shadow/shadow.lock) | tr ' ' '\n' | grep SHADOW_OFFSET_MIN      # SHADOW_OFFSET_MIN=12
tail -2 ~/wide_shadow/loop.out                                                           # "next" line
$PROBE after-w5 $PKG $BK/install/NC_FILES_INSTALL_RECEIPT.json --out $RL/VP_after_w5.txt  # OK n=0
```
**Deadline: W5 verified by 15:25Z, else abandon (R below).**

## R — restore (mirror order; every path ends with the OLD tree's services running and verified by 15:40Z)
Where it stopped → what to undo, in this order:
1. **Producer files** (only if W4 ran): `$PYP $RC/devices/nc_install_files.py rollback $PKG $BK/install` → `rolled_back_not_started`.
2. **Upstream** (only if W2 ran): `cd $QR && git revert --no-edit <U2>`; verify the 5d3029c guard: `/usr/bin/python3 ~/dl_quant_live/ops/check_upstream_drift.py` → `no drift across 5` (if the running tree is still 5d3029c) — or, if the running tree was already fast-forwarded, the guard of 5d3029c staged from git (`git -C ~/dl_quant_live show 5d3029c:ops/check_upstream_drift.py`).
3. **Executor** (only if pushed): new isolated checkout of GitHub main (= NEWSHA) → `git revert --no-commit 5d3029c..HEAD && git diff --stat 5d3029c` (must be empty) → rsync state → `safe_commit.sh "<revert msg>" <every file in git diff --name-only 5d3029c NEWSHA>` (battery on the 5d3029c code with the unpatched upstream) → `ff_running_tree.py <REVSHA>` → running tree code == 5d3029c. If there is not enough time for this battery before 15:40Z after step 4, step 4 comes first and the executor revert is done in the next quiet window (a pushed-but-not-fast-forwarded main does not change what the running executor does; an already fast-forwarded v2 executor with the v1 producer ⇒ M3 shadow field refused — no trading impact — reported).
4. **Services on the OLD tree**: `for L in com.hsy.comboparity com.hsy.combosnap com.hsy.combolive com.hsy.shadowloop; do launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/$L.plist; done` → `$PROBE after-w5 $PKG_OLD <receipt: $RL/receipt_W1.json, or the rollback receipt if step 1 ran> --out $RL/VP_restore_after_w5_OLD.txt` → **OK n=0** (shadow_loop a68c7a5f, combo_stage 363dd8c8 at the run paths, processes started after the reference time, sidecar off). Deadline 15:40Z.
