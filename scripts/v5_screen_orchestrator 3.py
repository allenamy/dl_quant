"""V5 fold-0 screen orchestrator.

Usage (on pod after sync):
    python scripts/v5_screen_orchestrator.py \
        --phase B1 \
        --output_dir experiments/v5_screen \
        --skip-existing

Phases:
    B1: backbone screen (4 configs) — fold 0 only
    B2: loss screen (4 losses on B1 winner) — fold 0 only
    B3: data screen (single-train comparison) — 1 run

For each run, calls run_pipeline_v3.py with the config + outputs to subdir.
After all runs in phase, computes pooled-fold-0 metrics for comparison.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


PHASE_CONFIGS = {
    "B1": [
        ("v4base", "configs/v5/screen/backbone_v4base.json"),
        ("attention", "configs/v5/screen/backbone_attention.json"),
        ("mamba", "configs/v5/screen/backbone_mamba.json"),
        ("emapool", "configs/v5/screen/backbone_emapool.json"),
    ],
    "B2": [],  # filled after B1 winner identified
    "B3": [
        ("singletrain", "configs/v5/screen/data_singletrain.json"),
    ],
}


def run_one(name: str, config_path: str, out_dir: Path, seed: int, skip_existing: bool):
    """Run fold-0 only for one config."""
    sub_out = out_dir / name
    sub_out.mkdir(parents=True, exist_ok=True)
    if skip_existing and (sub_out / "fold_0" / "test_preds.npz").exists():
        print(f"[SKIP] {name}: already done")
        return
    cmd = [
        "python", "run_pipeline_v3.py",
        "--config", config_path,
        "--output_dir", str(sub_out),
        "--skip-features",
        "--seed", str(seed),
        "--start-fold", "0",
        "--max-folds", "1",
    ]
    print(f"[RUN] {name}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"[FAIL] {name}: returncode {result.returncode}")
    else:
        print(f"[OK] {name}: done")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["B1", "B2", "B3"], required=True)
    p.add_argument("--output_dir", default="experiments/v5_screen")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-existing", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.output_dir) / args.phase
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.phase not in PHASE_CONFIGS or not PHASE_CONFIGS[args.phase]:
        sys.exit(f"Phase {args.phase} not configured (B2 needs B1 winner first)")

    for name, config_path in PHASE_CONFIGS[args.phase]:
        if not Path(config_path).exists():
            print(f"[WARN] config missing: {config_path}; skip {name}")
            continue
        run_one(name, config_path, out_dir, args.seed, args.skip_existing)

    print(f"\nPhase {args.phase} complete. Run eval next:")
    print(f"  python scripts/v5_eval_comprehensive.py --exp-dir {out_dir}/<name> --n-folds 1 --out exports/{args.phase}_<name>.md")


if __name__ == "__main__":
    main()
