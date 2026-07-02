# run_infra — D1 Stage-1+ queue-runner

Persistent server-side runner for the D1 experiment arms (replaces the fixed
`d1_chain.sh`). Runs on jpline under conda env `hsy_v5push`.

## Files
- `d1_queue_runner.sh` — the orchestrator. Reads `experiments/d1gate/queue.txt`
  (one `<config_path> [seed]` per line; `#`=comment, `STOP`=stop), never idles
  the GPU, appends a `DONE`/`FAIL`/`ABORTED_EARLY` line per arm to
  `experiments/d1gate/chain_status.log`. Supports appending to the queue while
  running. Advances `experiments/d1gate/queue.cursor` before each run.
- `statusline_d1.py <run>` — one-line EMA no-peek cd-CLEAN + DENSE + Δ-vs-baseline
  + provenance. cd-CLEAN/DENSE match `honest_aggregate_causal.py` exactly.
- `verify_d1.py <run>` — metrics.json parses + epochs_ran>=5 + ema preds exist.
- `parse_ep5.py <log> <epoch>` — EMA composite + sigR at a given epoch (log parse).
- `mk_nopreload.py <cfg>` — preload=False copy to /tmp (OOM retry), preserves output_dir.

## Early-abort (pre-registered)
At epoch 5: kill if `EMA val-composite < 0.5 x that month's Run1 epoch-5 EMA
composite (floor 0.005 when no Run1 ref) AND val sigR < 0.015`.

## Throughput
batch-1024 / lr x sqrt2 (0.0012) variants; adopt for all new arms once the
b1024 equivalence check passes (final cd within +/-0.006 of the batch-512 Run1
and epoch time ~halves).

## Launch
    nohup bash run_infra/d1_queue_runner.sh > logs/d1_queue.log 2>&1 &
