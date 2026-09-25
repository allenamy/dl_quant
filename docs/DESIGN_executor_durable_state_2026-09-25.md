> **Created:** 2026-09-25 06:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** design draft, to be reviewed by the lead; the behaviour-changing parts of B-3 / B-4 need a **user ruling** before deployment | **Invalidated by:** a lead / user ruling that changes any item below

# Executor fix package B (candidate; batteried together with M3 v2; goes through the deploy protocol; no interim version)

Sources: the census `docs/receipts/write_point_census_2026-09-25/TABLE.md` (501d80737), `gc_close_probe.py` (measured), fact A (16Z halted anchor), and the drift_gate block (measured ~17 min).

## B-1 New ledger-fact class: "halted anchor + reduce-only reduction from the untradable-held disposition"
- `tests_disposition_matrix`: a halted anchor may carry submits **only if** every one of them satisfies all of:
  - (a) the order is `reduce_only`;
  - (b) the name is in phase_A `untradable_held.reduced ∪ flatten_only`, or is a flatten of a trip-named position;
  - (c) contract quantity ≤ the venue position read at the previous anchor, same side, and it does not cross zero (checked in contracts, with closure previous − fill = the post readback of this anchor);
  - (d) `n_live_opening == 0`.
- Source of the check: anchor_runs.log phase_A + position_readback.jsonl + orders.jsonl.
- Red controls: plant (i) a non-reduce_only submit, (ii) a reduce_only whose quantity exceeds the position, (iii) a submit that crosses zero, (iv) `n_live_opening = 1`. Each one must turn the assertion red.
- The existing HALTED-NO-SUBMIT assertion stays unchanged for halted anchors whose submit count is 0; the new class only covers halted anchors whose submit count is > 0.

## B-2 Durable writes (`live/durable_io.py`, a new module)
- `write_json_durable(path, obj, **dump_kw) -> sha256(memory bytes)`, in this order:
  1. serialise to bytes;
  2. write `.<name>.tmp.<pid>` inside `with`;
  3. flush + fsync;
  4. **read back and compare bitwise with the in-memory bytes**;
  5. `os.replace`;
  6. fsync the directory.
- Any OSError, or a read-back mismatch ⇒ `DurableWriteError` (loud); the tmp is removed; the old file is untouched.
- Replaced at: `anchor_loop._save` (L799–803, all callers: loop state / bands / no_trade_band / fee baseline); `watchdog.py` L3307 `state.json`, L3311 `last_eval.json`; `state_root.py` L148; `factor_version_registry.py` L174; `deliver_report.py` L99.
- The census tool gains a gate: the `json.dump(x, open(...))` idiom is banned in production code (tests_imports-style census red; the existing whitelist starts empty).
- Red controls, run through the real code path with a raw file whose every write fails with ENOSPC, with truncation to half, and with an empty write:
  - old `_save`: silent (no exception, and the target file gets replaced);
  - new: `DurableWriteError`, and the target file's bytes are unchanged.

## B-3 Strict read (**failure-path behaviour change; needs a user ruling**)
- `_load(path, default)` is split into two cases:
  - **absent** ⇒ return default (unchanged: first run, or a file that legitimately does not exist);
  - **present but empty / unparseable / wrong top-level type** ⇒ `StateCorrupt`.
- When `StateCorrupt` fires:
  - (1) the bad file is moved to `<path>.corrupt.<UTC>` (kept as evidence);
  - (2) the persistent marker `state/live/STATE_CORRUPT.json` is written with `write_json_durable`;
  - (3) HIGH page naming the file and the reason;
  - (4) **this anchor halts opening** (`broker.open_orders_halted = True`); reduce_only / stop-loss / trip-named flattens still go through (the existing broker L1564 design). Positions come from this anchor's venue readback (L1388), so they are not affected by the loop-state default;
  - (5) **while the marker exists, every anchor halts opening and pages HIGH**;
  - (6) clearing: `ops/clear_state_corrupt.py --check` (shows the marker, the quarantined copy and the current file) → `--clear --reason "..."` (explicit reason, audit line; mirrors resume_from_trip).
- The watchdog's `state.json` read (L3120: currently raises and crashes when the file is corrupt) gets the same treatment: halt opening + page, with no silent reset to `reduce_only: False`.
- Red controls: empty file / truncated JSON / wrong type ⇒ old code returns the default silently; new code raises StateCorrupt + writes the marker + sets `open_orders_halted`. A missing file ⇒ default in both old and new (control).

## B-4 Disk headroom guard (**failure-path behaviour change; needs a user ruling**)
Measured volume:
- executor: pilot_log about 7–8 MB/day; rate_timeline about 0.35 MB/anchor; state json about 0.2 MB.
- **producer snapshots: 84 MB/anchor, 46 anchors = 3.3 GB, no retention cap (+~0.5 GB/day)**.
- The Mac data volume currently has **12.8 GB free (98%)**.

Thresholds (checked at the start of each anchor, before any write; `shutil.disk_usage(state_root).free`):

| free space | action |
|---|---|
| < 1 GiB | **refuse this anchor** (HIGH page; no orders, no state writes except the alert itself). The reasoning: once writes can fail, half an anchor is worse than no anchor. |
| 1–5 GiB | **halt opening** + HIGH (reduce-only / stop-loss still go through) |
| 5–15 GiB | INFO page (once a day) |

About 1.8 / 9 / 27 days of runway respectively at ~0.55 GB/day. **At today's 12.8 GB this would already trigger INFO.**

Related suggestion, a producer change that goes into C: a retention cap for `state/snap` (e.g. keep 7 days = 42 anchors; archive the older ones to pod2 and delete them after checking sha). Parity and research only use the recent ones.

Red controls: patch `disk_usage` to return 0.5 / 3 / 10 / 20 GiB ⇒ assert refuse / halt / INFO / no action respectively; the old code takes no action at any value.

## B-5 drift_gate fail-fast (lead ruling)
- Before reading, check `os.stat(p).st_flags & SF_DATALESS` (0x40000000); the read runs in a subprocess with a timeout (10 s).
- Placeholder or timeout ⇒ the suite goes red with the named reason `UPSTREAM_UNREADABLE (iCloud placeholder): <path>` and prints the materialisation commands `brctl download "<path>"` and `cat "<path>" > /dev/null`, then exits non-zero.
- Red control: a stand-in stat returns the dataless flag / a reader that blocks ⇒ old code blocks (a timeout in the test harness counts as proof of blocking), new code goes red within a few seconds.

## Delivery
- New commits on the dd486af clone (not pushed); a separate test file per item plus a red-control self-check.
- The full battery runs together with v2 (and the baseline is compared in the same tree state).
- Deployment goes through safe_commit / the deploy protocol; the behaviour-changing parts of B-3 / B-4 need a user ruling first.
