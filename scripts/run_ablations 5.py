"""Run all V4 ablations sequentially, collecting summary metrics.

Each config in configs/v4_ablations/ is executed with --skip-features
on data/npz_v4/, using only FOLD 0 (caller should edit configs to
override train_days minimum to force 1 fold for speed). Results go
to experiments/v4_ablations/<name>/ and a summary is written to
experiments/v4_ablations/SUMMARY.json.

IMPORTANT: full V4 must have been run first so data/npz_v4/ exists.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run_one(config_path: str, fold_index: int = 0) -> dict:
    """Execute a single ablation config via run_pipeline_v3.py.

    Returns a summary dict with the key metrics from fold_{fold_index}/
    metrics.json and test_results.json if they exist.
    """
    start = time.time()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "run_pipeline_v3.py",
         "--config", config_path,
         "--skip-features",
         "--model", "V3"],
        capture_output=True, text=True, cwd=repo_root,
    )
    elapsed = time.time() - start

    cfg = json.loads(Path(config_path).read_text())
    fold_dir = Path(cfg["output_dir"]) / f"fold_{fold_index}"
    metrics: dict = {}
    m_path = fold_dir / "metrics.json"
    if m_path.exists():
        metrics = json.loads(m_path.read_text())
    t_path = fold_dir / "test_results.json"
    test_results: dict = {}
    if t_path.exists():
        test_results = json.loads(t_path.read_text())

    return {
        "config": config_path,
        "ablation": cfg.get("_ablation", "unknown"),
        "returncode": result.returncode,
        "elapsed_sec": round(elapsed, 1),
        "val_corr": metrics.get("val_corr"),
        "val_r2": metrics.get("val_r2"),
        "best_epoch": metrics.get("best_epoch"),
        "test_corr": test_results.get("correlation"),
        "test_sharpe": test_results.get("sharpe_annual"),
        "stdout_tail": result.stdout[-500:] if result.returncode != 0 else "",
        "stderr_tail": result.stderr[-500:] if result.returncode != 0 else "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs-dir", default="configs/v4_ablations",
                    help="Directory containing per-ablation config JSONs.")
    ap.add_argument("--out", default="experiments/v4_ablations/SUMMARY.json",
                    help="Summary output path (incrementally updated).")
    ap.add_argument("--fold-index", type=int, default=0,
                    help="Which fold's metrics to pull from each ablation.")
    args = ap.parse_args()

    configs = sorted(Path(args.configs_dir).glob("*.json"))
    if not configs:
        print(f"No configs found in {args.configs_dir}; aborting.", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(configs)} ablation configs in {args.configs_dir}")

    summary: list[dict] = []
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for cp in configs:
        print(f"\n=== Running {cp.name} ===")
        row = run_one(str(cp), fold_index=args.fold_index)
        summary.append(row)
        status = "OK" if row["returncode"] == 0 else f"FAIL({row['returncode']})"
        vc = row.get("val_corr")
        tc = row.get("test_corr")
        print(f"  {status:8s}  val_corr={vc}  test_corr={tc}  elapsed={row['elapsed_sec']}s")

        # Persist incrementally in case of crash
        out_path.write_text(json.dumps(summary, indent=2, default=str))

    print(f"\nSUMMARY complete: {out_path}")
    print(f"{'ablation':<30s} {'val_corr':>10s} {'test_corr':>10s} {'sharpe':>8s}")
    for row in summary:
        vc = row.get("val_corr")
        tc = row.get("test_corr")
        sh = row.get("test_sharpe")
        print(f"  {row['ablation']:<28s} {str(vc):>10s} {str(tc):>10s} {str(sh):>8s}")


if __name__ == "__main__":
    main()
