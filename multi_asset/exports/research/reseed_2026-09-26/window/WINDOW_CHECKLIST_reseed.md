> **Created:** 2026-09-26 02:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** window checklist, frozen before the window. Lead ruling: 09:00–11:40Z; fix-pkg-d keeps 04Z and 08Z to itself; 12Z is the first reseeded anchor; the M3 request comes after this acceptance | **Invalidated by:** a lead ruling; any change to the devices named here

# Window checklist — live seat-history reseed, W = [09:00, 11:40]Z (N = 08Z)
Scope: PRODUCER STATE only. Two files change: `~/wide_shadow/state/leg_returns_live.json`, and `generation.json` (re-issued by the producer's own functions). No code changes, and the executor is not touched.
The producer holds the series in memory, so the four producer services are stopped around the replacement and restarted afterwards (reseed_leg_returns.py docstring, facts 1–2).
**Every step is a fail-closed gate** through `nc_2026-09-23/devices/release_gates.py` (E-0926-A). A launch failure, any non-zero exit, a timeout, or a missing verdict line stops the run, and later gates never start.

Variables:
- `RD=quant_research/multi_asset/exports/research/reseed_2026-09-26`
- `STAMP=$(date -u +%Y%m%dT%H%MZ)` at the window
- `BUILD=~/cc_tmp/reseed_20260926/build_$STAMP`
- `AFTER_EPOCH` = the epoch just before W1

## Pre-window, from 09:00Z
- The lead's re-measure: the inputs have not changed since the dry run. Expected differences: snapshots 04Z/08Z, and the live file (+2 entries). The fresh build in W2 re-verifies everything, and install refuses if anything changes between build and install.
- 08Z producer anchor done; 08Z snapshot present; no producer anchor in flight; disk.
- Generate `gates_reseed_$STAMP.json` from `gates_reseed_template.json` by literal substitution of `<RD> <BUILD> <STAMP> <AFTER_EPOCH>`, then `grep -c '<'` must return 0.

## Run
`/usr/bin/python3 $QR/multi_asset/exports/research/nc_2026-09-23/devices/release_gates.py $RD/window/gates_reseed_$STAMP.json $RD/window/GATES_$STAMP.log`
Gates:
1. W0 quiet window open.
2. W0 producer code unchanged: shadow_loop_v3 52baf979…, combo_stage 12a76de8….
3. W1 stop the 4 services: wait for combosnap/comboparity, bootout, then assert no pid, no process, no .parity.lock, and a dead lock pid.
4. W2 fresh build.
5. W3 install:
   - backups `.pre_reseed_$STAMP` in state/;
   - the producer's atomic_write, with read-back compare;
   - generation re-issued with build_generation_record at the same anchor and verified with _read_verified_generation.
6. W4 start the services: bootstrap in the order comboparity, combosnap, combolive, shadowloop. Then:
   - shadowloop pid == shadow.lock;
   - `SHADOW_OFFSET_MIN=12`;
   - the process started after AFTER_EPOCH;
   - the loop.out `next` line was written after AFTER_EPOCH.

A clean start means the new ShadowState loaded the reseeded file and passed the generation check; its constructor raises otherwise.
Deadline: gates done by 11:25Z, else restore (below).

## First reseeded anchor 12Z (acceptance ≈ 12:55Z, after the executor's 12Z anchor)
- `reseed_first_anchor.py --anchor 1790409600 --build $BUILD --stamp $STAMP`, criteria frozen in d02c2c3cb:
  - file bitwise installed[1:] + 1;
  - w3_raw within 5e-5;
  - w3_masked exact;
  - target layer CONSISTENT.
- The standard `accept_anchor_v2.sh` runs as well.

## Restore (mirror order; the executor is not involved)
- Failed at W1: re-run `producer_services.py start <AFTER_EPOCH>`; nothing else changed.
- Failed at W2, or W3 exited with 3 (nothing written): `producer_services.py start`.
- W3 exited with 4 (partial write), or failed at W4 after install:
  1. `producer_services.py stop`;
  2. `reseed_leg_returns.py rollback --stamp $STAMP` (bitwise restore; generation verifies);
  3. `producer_services.py start`.
- After any rollback, run the seat comparison again at the next anchor: `reseed_first_anchor.py` with `--build` pointing at a dir whose `leg_returns_live.NEW.json` is the `.pre_reseed_$STAMP` backup ⇒ the file continues the OLD series and w3 returns to the old history. "Copied back" is not "back to the old state".
- The services must be running again before 12:12Z (the producer's 12Z slot).
