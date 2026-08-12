#!/usr/bin/env python
"""Run a single V5 fold-0 screen with output_dir override.

run_pipeline_v3.py reads output_dir from config (no CLI flag) — this script writes
a temp config with the desired output_dir and invokes the pipeline.

Usage:
    python scripts/v5_run_one.py \
        --name v4base \
        --config configs/v5/screen/backbone_v4base.json \
        --out-base experiments/v5_screen/B1
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--out-base', default='experiments/v5_screen/B1')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--max-folds', type=int, default=1)
    p.add_argument('--start-fold', type=int, default=0)
    args = p.parse_args()

    out_dir = Path(args.out_base) / args.name
    fold_indices = range(args.start_fold, args.start_fold + args.max_folds)
    if out_dir.exists() and any((out_dir / f'fold_{f}' / 'test_preds.npz').exists() for f in fold_indices):
        print(f'[SKIP] {args.name}: outputs present at {out_dir}')
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.load(open(args.config))
    cfg['output_dir'] = str(out_dir)
    tmp_cfg = out_dir / '_used_config.json'
    json.dump(cfg, open(tmp_cfg, 'w'), indent=2)

    cmd = ['python', 'run_pipeline_v3.py',
           '--config', str(tmp_cfg),
           '--skip-features',
           '--seed', str(args.seed),
           '--start-fold', str(args.start_fold),
           '--max-folds', str(args.max_folds)]
    print(f'[RUN] {args.name}: ' + ' '.join(cmd))
    rc = subprocess.run(cmd).returncode
    print(f'[{"OK" if rc == 0 else "FAIL"}] {args.name} rc={rc}')
    return rc


if __name__ == '__main__':
    sys.exit(main())
