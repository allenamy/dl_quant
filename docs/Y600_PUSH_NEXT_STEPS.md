# Y600 Push — Next Steps When You Return

**TL;DR.**  Pod FUSE (MooseFS) was degraded tonight; every attempt at 700-day training deadlocked at 99% worker CPU with 0% GPU util. Pivoted to post-hoc SWA which gave a PARTIAL pass: pooled clean P 0.056→0.066, S 0.074→0.079. All code for the planned training path is committed and ready on branch `siyu_v4_y600_push`. Here is what to do when you're back.

## 1. Verify pod I/O is healthy

```bash
# Cold-cache smoke test — run on pod
# Expect ≥ 80 MB/s cold, ≥ 300 MB/s warm
dd if=/workspace/quant_research/data/npz_v4/$(ls /workspace/quant_research/data/npz_v4 | shuf -n 1) of=/dev/null bs=1M

# Also sanity-check worker-concurrent I/O — THIS is what was failing tonight
cat > /tmp/io_smoke.py <<'PY'
import time, numpy as np, pathlib, concurrent.futures
days = sorted(pathlib.Path("/workspace/quant_research/data/npz_v4").glob("*.npz"))
sample = list(np.random.default_rng(0).choice(days, 30, replace=False))
t0 = time.time()
def read(p):
    d = np.load(str(p)); _ = d["X"]; return p.stat().st_size
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    sizes = list(ex.map(read, sample))
elapsed = time.time() - t0
mb = sum(sizes) / 1e6
print(f"4-way concurrent read: {mb:.1f} MB in {elapsed:.1f}s = {mb/elapsed:.0f} MB/s")
PY
python3 /tmp/io_smoke.py
```

**Decision:**
- If concurrent throughput ≥ 200 MB/s → pod is healthy, proceed to step 2.
- If < 200 MB/s → FUSE is still degraded. Restart pod via RunPod UI, repeat smoke test.

## 2. Run Block B (the original plan's training step)

Once I/O is verified:

```bash
# On pod
cd /workspace/quant_research
git fetch origin siyu_v4_y600_push && git checkout siyu_v4_y600_push && git pull
nohup bash /tmp/block_b_runner.sh > logs/y600_push/block_b_driver.log 2>&1 &
# Tail to watch epoch summaries:
tail -F /workspace/quant_research/logs/y600_push/block_b_f0.log | grep -E '^Epoch '
```

Block B trains 3 folds of `configs/y600_push/baseline_plus.json` (composite val metric + EMA). Expected time ~2h15m on healthy pod. Each epoch should print a line like:
```
Epoch   3/40 | train_loss=... | val_loss=... | P=+0.028 S=+0.038 C=+0.033 | r2=-0.003 | lr=3.62e-04 | EMA P=+0.031 S=+0.040 C=+0.036
```

Watch for `EMA` columns showing non-trivial values — that confirms E3 is active.

## 3. Apply SWA on top of Block B output

After Block B completes, stack SWA on the fresh checkpoints:

```bash
for F in 0 1 2; do
  python3 scripts/ensemble_topk.py --fold-dir experiments/y600_push/baseline_plus/fold_$F --mode weight --k 5 \
    --out experiments/y600_push/baseline_plus/fold_$F/swa_k5.pt
done
# Then eval each SWA checkpoint — see pattern in /tmp/eval_swa_all.sh on pod.
```

## 4. Optional: Block E (seed ensemble)

```bash
# On pod
VARIANT=seed7 bash /tmp/block_e_runner.sh
```

Another 2h15m for seed 7 folds. Then ensemble: median-average predictions across seeds.

## 5. Final eval + report

```bash
# Local
python3 scripts/y600_final_eval.py \
  --stack-dir experiments/y600_push/final_stack \
  --baseline-file experiments/y600_push/_baseline_frozen.json \
  --out-report docs/Y600_PUSH_REPORT_v2.md \
  --bootstrap-b 2000 --block-len 60

# Or use the simpler comparison tool:
python3 scripts/y600_postproc.py \
  --variants baseline=experiments/y600_push/baseline_run \
             swa_k5=experiments/y600_push/swa_run \
             block_b=experiments/y600_push/baseline_plus \
  --blend \
  --out-report docs/Y600_PUSH_POSTPROC.md
```

## What was achieved tonight (accepted baseline going forward)

| | Pearson | Spearman |
|---|---:|---:|
| Baseline frozen | +0.056 | +0.074 |
| **SWA-k5 (current best)** | **+0.066** | **+0.079** |

Local artefacts:
- `experiments/y600_push/swa_run/fold_{0,1,2}/test_preds.npz` — best current predictions.
- `docs/Y600_PUSH_REPORT.md` — full analysis + bootstrap CI + tail DirAcc.

## What did NOT help (rule out if you were considering them)

- **rank_blend of baseline + SWA** — pushes Pearson to 0.070 but kills DirAcc to 0.493 (ranks destroy sign). Unusable.
- **Per-fold z-normalize before pooling** — no change. Preds already well-centered per-fold.
- **Non-q50 quantile extractions** — mean(q10,q50,q90), mean(q50,q90), q50+0.3*(q90-q10)/2, spread — all inconsistent across folds.

## What will likely push past 0.08 on both (day 2 candidates)

1. **Multi-seed ensemble** (Block E in plan) — 2-3 seeds × SWA, median-aggregate. +0.01-0.02 IC typical.
2. **Composite-metric retraining** (Block B) — select checkpoints by 0.5·P+0.5·S rather than P alone. EMA + SWA stack on top.
3. **Multi-horizon aux loss** (Block D) — train y_180+y_300+y_600 jointly, horizon weights [0.2, 0.3, 0.5].
4. **Differentiable Spearman loss** via torchsort (Blondel 2020) — 4h build + 2h15m train.

## If pod stays broken

Fall back to `num_workers=0` configs (`configs/y600_push/baseline_plus_nw0.json`). Epoch time inflates 2-3× but training WILL progress. A full fold would take ~90 min instead of 45 min.

**Alternate workaround — try fork → spawn.** The deadlock signature (99% CPU workers, GPU idle, main in `futex_wait_queue`) matches known fork()+FUSE failure modes. Try setting the multiprocessing start method to `spawn` before DataLoader creation:

```python
# Add near the top of run_pipeline_v3.py's main()
import torch.multiprocessing as mp
if not mp.get_start_method(allow_none=True) == "spawn":
    mp.set_start_method("spawn", force=True)
```

With `spawn`, workers re-import modules freshly rather than inheriting fork-copied memory-maps. Slower to start up (~10 s overhead per fold) but may avoid the FUSE page-fault contention. If this works, training might complete in a single session without waiting for pod recovery.

## Anti-patterns logged in memory (next session's Claude will see these)

- `swa_y600_post_hoc_2026_04_20.md` — SWA as a free +0.010/+0.004 uplift recipe.
- `pod_fuse_deadlock_2026_04_20.md` — concurrent FUSE breaks DataLoader workers; smoke-test before long runs.
