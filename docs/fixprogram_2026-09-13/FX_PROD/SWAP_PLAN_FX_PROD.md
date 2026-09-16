> **创建:** 2026-09-13 16:2xZ | **Session:** FX-PROD (session b9646a9e) | **状态:** DRAFT — not executed; the swap needs independent review of P1/P2/P5/P6/P9 and the migrations, then the lead's and the user's go; §3 dry run on the frozen 09-13 12Z state pending (Mac after 16:50Z) | **作废条件:** any live file sha in §1 differs from b8917484 at swap time, or a cited fx_prod commit is rewritten

# SWAP PLAN — FX-PROD (P1 king col 80 v0, P2 V2MAIN col 80 v0, P5 seat king rows, P6 seed loader, P9 append labels + migrations)

Nothing here has been run against `~/wide_shadow`. Every command below is written for the operator who executes the swap after review. It is not a record of anything done.

## 1. Files

| live path (`~/wide_shadow/…`) | before = b8917484 (sha256) | after = b90f1b8 (sha256) |
|---|---|---|
| `shadow_loop_v3.py` | `e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e` | `55bd89c9adce39992d485e6a826dc85f9d2e8807ab14c84095f0259ca393a4c9` |
| `fea171/combo_stage.py` | `b5c698f9d1ee9acb73c9bf5f3a1e15843d3298e95a810ebf0107a7d68c6ee358` | `1c6a491d30606312edd27eb3457c02f7d805fd2318c0427f87c3c27fec1eeafa` |
| `fea171/sidecar_blend.py` | `6140790e55b70cffbaf180e8ed00145042c91611d556c267416207e2ae462a06` | `f25388e427d7418febb047c860e7959c8ff239244754fbc5d358a9330fd89cff` |
| `state/aux.json` | swap-time value (recorded in S1) | `STAGED/aux.json` from §2 |
| `state/leg_returns_live.json` | swap-time value (recorded in S1) | `STAGED/leg_returns_live.json` from §2 |

**Deployment cannot be a code-only swap (lead's ruling, from the independent review's limited acceptance).** With `FUND_COL80_V0` on, the new producer REFUSES TO START on a state without `ema_v0` — measured in the §3 dry run: `REFUSE_TO_START: FUND_COL80_V0 but state has no ema_v0 (build offline: migrations/p1_build_ema_v0.py)`. So the swap must install the **reviewed v0 state and a consistent bundle together with the three .py files**; replacing only the code brings the producer down at its next state load. The same applies to any later bundle re-export (see §6, "bundle reset is not a rollback path").

Checked 16:19Z 09-13, and re-checked 2026-09-16 after the 09-14 reboot: the three live code files are blob-equal to b8917484. Unchanged: the bundle and booster, the executor (`~/dl_quant_live`), the launchd plists, `combo_live_daemon.sh`, `sidecar_daemon.sh`, `fea171/state_H_f10_*`, the weights files.
combo_stage.py and sidecar_blend.py are started as fresh Python processes on every anchor by their daemons, so a replaced file is used from the next anchor on without restarting a daemon. The producer holds its state in memory and writes it only inside `run_anchor` (at slot N+16 min). It must be restarted after the state files are replaced.

## 2. State migrations (offline, on a copy; order fixed)

Copy layout `<C>` = `<C>/shadow_log.jsonl` + `<C>/state/{aux.json, leg_returns_live.json, leg_returns_live.json.pre_seatseed_v3_20260905, rolling.npz, weights/}`. About 85 MB; run `df -h /System/Volumes/Data` first.
Run with `env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu PYTHONDONTWRITEBYTECODE=1 ~/wide_shadow/venv/bin/python -B` from `/Users/haosiyu/cc_tmp/fx_prod`, with `CODE=work/code_b90f1b8` (a `git archive b90f1b8` export).

1. `migrations/p5_rescore_seat_king.py --code $CODE --state <C>/state --out <M>/p5`. Replays the producer from the first live-appended scoring anchor (08-31 00Z) to the state's last anchor, twice:
   - SERVED arm: the booster that scored each anchor (from the log's `booster_sha`), with `FUND_COL80_V0` and `FUND_IV_RERESOLVE` off. It must reproduce every recorded king leg-return row and `aux.prev_rec.legz.king` bitwise, otherwise rc 2 and no output.
   - V0 arm: the same boosters with column 80 = v0.
   Outputs `leg_returns_live.rescored.json` (only the live-appended king rows change) and `aux.p5.json` (only `prev_rec.legz.king` changes; this vector books the first post-swap step-6 row).
   It runs first because it replays with the stored labels and asserts that they agree across sources.
2. `migrations/p1_build_ema_v0.py --state <dir holding aux.p5.json as aux.json> --code $CODE --out <M>/p1` adds `ema_v0`. Gates: G1 `ema_v0_problems == []`; G2 an independent v1 rebuild reproduces every acc to 1e-12; G3 all state ledger rows are in the union.
3. `migrations/fund_label_ema_correction.py --state <dir holding aux.with_ema_v0.json as aux.json> --code $CODE --out <M>/corr --classes D17,P9 --zip-dir <every monthly zip dir pulled so far, e.g. work/pod2_inputs/zips_2026-08> --control --allow-out-of-tail`. This is the exact v1 EMA and tail-label correction. On the frozen 09-13 12Z state it corrects 534 D17 rows (5 names) and 65 P9 rows, and the positive control holds at 6.9e-18.
   **`--allow-out-of-tail` is required here and forbidden in §7** (FXR-PROD-1). Exactly one correction on this state (a P9 row) falls on a settlement that has already left the ledger tail. Such a row carries no label in the state, and a revision marker cannot help because the producer's `save()` writes a fixed key set and would drop it at the next anchor — so the tool cannot tell whether it was already applied, and refuses by default. The one-time migration is run once by an operator with this receipt; the recurring monthly job must never be given the flag, so it can only ever touch self-identifying in-tail rows.
   The tool publishes `aux.corrected.json` only after six gates pass (`out_of_tail_corrections_allowed_or_absent`, `no_frozen_vs_frozen_label_conflict`, `no_rate_conflict_between_sources`, `every_input_label_has_provenance`, `positive_control_within_1e12`, `no_applied_correction_implies_output_equals_input`); on any failure it removes its temp file and exits 2, leaving no usable state.
4. `migrations/swap_state_compose_check.py --orig <C>/state --p5 <M>/p5 --p1 <M>/p1 --corr <M>/corr --code $CODE --out <M>/compose`. It refuses unless all of these hold:
   - the receipt sha chain is closed;
   - the aux changes are exactly {ema acc = orig + receipt dacc on the listed names, APPLIED in-tail labels, ema_v0 added, prev_rec.legz.king};
   - ema_v0 passes the code's check;
   - only the rescored king rows differ in the leg returns.
   On PASS it writes `<M>/compose/STAGED/{aux.json, leg_returns_live.json, SHA256SUMS}`.

## 3. Dry run on the frozen live state 09-13 12Z (pending)
To be filled with receipts: P5 gates and seat before/after, P1/correction/compose PASS, runtimes, and the load test (the new code's `ShadowState` loads STAGED without REFUSE; the old code b8917484 loads STAGED too, which is the rollback compatibility check).

## 4. Swap procedure (operator; outside anchor windows; never `nohup`)
Window: start ≥ N+1:00 after anchor N, once the producer, combo_live and sidecar for N are done (combo_live.log `=== combo_live anchor=N rc=0`, sidecar_daemon.log `ran for N.json`). Finish S6 before N+3:30. The Mac must be idle during the other teams' anchor windows.
- **S0 record.** `launchctl list | grep com.hsy.shadowloop` (PID), last `next …` line of `~/wide_shadow/loop.out`, last `signal` anchor in `shadow_log.jsonl`, `heartbeat.json`, and the sha256 of the three code files. Any code sha ≠ §1 "before" ⇒ STOP.
- **S1 copy.** Copy the §2 layout to `<C>` (read-only source) and record the sha of `state/aux.json` and `state/leg_returns_live.json`.
- **S2 migrate.** Run §2 steps 1–4 and require PASS. Record runtimes (to be measured in §3).
- **S3 re-verify.** Recompute the sha of live `state/aux.json` and `state/leg_returns_live.json`. If they differ from S1 (the producer ran), go back to S1.
- **S4 backup.** `cp -p` each of the five files to `<file>.pre_fxprod_<UTC>` next to it and record the sha.
- **S5 install.** Copy each new file to `<file>.fxprod_tmp` in the same directory, verify its sha against §1/STAGED, then `mv -f` it over the target (atomic rename). Re-verify all five shas.
- **S6 restart.** `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`, then verify:
  - the new PID differs and `ps eww <pid>` shows `SHADOW_OFFSET_MIN=16`;
  - `shadow.lock` holds the new PID;
  - `loop.out` shows a new `next <N+4h+16min>` line and no `REFUSE_TO_START` (the new code refuses when `ema_v0` is missing or inconsistent);
  - `launchctl list` shows no respawn loop (runs count stable over 60 s).

## 5. First post-swap anchor A1 = N+4h: acceptance list
Producer (`shadow_log.jsonl`, `state/`):
1. `signal` row for A1 with status OK and the expected booster_sha; no `anchor_error`.
2. `fund_col80` for A1: `caliber` "v0", `v0_state` true, `n_members_missing_v0` 0. Any non-zero `n_fresh_missing_v0` is listed by name and explained.
3. `fund_iv_resolved` for A1 is present. Every relabelled row names its exact rule or `likely_forward_schedule`, and every unresolved row is listed with candidates.
4. `score` row for N is present. `leg_returns_live.json` has 950 rows, and its first 949 rows equal `STAGED/leg_returns_live.json` rows 1…949.
5. Seat: w3 recomputed from the post-A1 `leg_returns_live.json` with the combo_stage formula equals the A1 `signal` row w3 at 4 decimals. The masked king seat is close to the §3 "after" value (one row moved).
6. `aux.json` holds `ema_v0` with `ema_v0_problems(ema, ema_v0) == []`, checked read-only on a copy.

Combo and sidecar:

7. `combo_live.log` shows `rc=0` for A1 with no `COMBO_LIVE ABORT`, and target_live was rewritten before N+22:35.
8. `combo_live_status.json` and `target_combo/A1.json` show `fund_caliber.col80 == "v0"`, `fresh12h` true, `n_v0_missing` 0.
9. `sidecar_daemon.log` shows `ran for A1.json rc=0`, and `target_blend/A1.json` shows `fund_caliber.col80 == "v0"`.

Executor (unchanged code): 10. the normal per-anchor checks, i.e. orders rows for A1, no watchdog trip, no reject spike.

Replay: 11. a snapshot replay of A1, from the S1 copy with the STAGED files and code b90f1b8 on the Phase-1 device, reproduces the live king npz, target_live and target_combo at L∞ 0.0 with equal content sha. This proves the running code is the reviewed code on live data.

## 6. Rollback (verb: `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`; never `nohup`)
- **Before A1 has run:** restore all five files from `*.pre_fxprod_<UTC>` (tmp copy, sha check, `mv -f`), kickstart, then re-run the S6 checks with the old shas.
- **After A1 (or later) has run:** the backed-up aux lacks the post-swap ledger rows, prev_rec and heartbeat. Restore the three code files only, keep the current state, and kickstart.
  - The old code ignores `ema_v0`, and its `save()` drops it at the next anchor.
  - The corrected v1 EMA and labels stay; they are the declared values.
  - The rescored king rows stay in the seat. This is a caliber mismatch in the other direction; it is recorded, not undone.
  - combo_stage and sidecar_blend fall back at their next run.
- **Bundle reset is not a rollback path for the new code.** With `FUND_COL80_V0` on, a bootstrap from the current v3 bundle refuses: there is no `fund_ema_v0_state.json`, and P6 refuses the ONG 08-25 08Z seed label (EMA impact 6e-7 > 1e-9). Re-exporting the bundle is a separate item. Until then a bundle reset needs the old code.

## 7. Recurring: (c) monthly zip reconciliation
After data.binance.vision publishes month M (normally in the first days of M+1):
- pull on pod2 with `fx/p9_pull_monthly_funding_zips.py`;
- run §2 step 3 alone (`--classes P9 --zip-dir <all months>`) on a state copy, **without `--allow-out-of-tail`** (FXR-PROD-1: the flag is only for the one-time migration; here it must be absent so the job can only correct rows whose absorbed label is still in the state);
- a re-run on an already corrected state is a no-op by construction — the input's own tail labels are authoritative, so every already-absorbed row resolves to "no change" (measured: 598 of 598 on the 09-13 state). If anything is still applied the positive control fails and the job exits 2 without writing a state file;
- install `aux.corrected.json` with §4 S3–S6 (aux only).
The September zip resolves T 09-06 00Z and SKR 09-07 20Z, and confirms ZKC 09-02 20Z and SOPH 09-11 12Z.
